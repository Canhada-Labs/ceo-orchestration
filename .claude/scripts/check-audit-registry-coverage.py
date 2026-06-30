#!/usr/bin/env python3
"""check-audit-registry-coverage — audit event registry drift guard.

PLAN-013 Phase A.6 + ADJ-021 (QA Architect §S10 HIGH consensus). Prevents
silent drift between the two sources of truth for audit events:

  1. CODE  : ``.claude/hooks/_lib/audit_emit.py`` — the ``_KNOWN_ACTIONS``
             set literal (emitter-side declaration)
  2. SCHEMA: ``SPEC/v1/audit-log.schema.md`` — the "Required fields per
             v2 action" table (consumer-facing contract per ADR-043)

The registry MUST stay in sync with the schema. When it drifts:

  - Action emitted in code but not in schema  → consumers cannot reliably
    parse the event; ADR-043 SOC2 coverage is false.
  - Action in schema but not in code          → SOC2 audit references
    vaporware; consumer expectations go unmet.
  - ``emit_<name>()`` call site with no matching ``<name>`` in the
    registry → the ``_write_event`` fail-open path silently drops the
    event via ``_breadcrumb("unknown action: ...")``.

Session 20 surfaced the exact failure this check prevents (Gap #3):
``live_adapter_call_*`` + ``breaker_*`` + ``credential_rotation_due``
were emitted by ``_lib/adapters/live/_transport.py`` yet unregistered
in ``_KNOWN_ACTIONS``. The Wave 0 fix registered those 6 + added 4 MCP
events. This CI check locks the invariant so a future commit cannot
regress without turning the PR red.

## Golden-registry drift guard (PLAN-133 E8 — generated SPEC inventory)

In addition to the live cross-check, the script can emit a deterministic
**audit-action registry golden** generated FROM the typed helpers
(``_KNOWN_ACTIONS`` + every ``def emit_<name>``) and assert that a
checked-in golden file (``.claude/data/audit-registry.golden.txt``)
matches it byte-for-byte.

The motivation (rite §3.1): the live ``_KNOWN_ACTIONS`` ⇆ schema-table
cross-check can pass while BOTH sources drift together (e.g. a global
rename that touches the set literal and the table in lockstep but breaks
a downstream consumer). A checked-in golden gives a reviewer ONE small
reviewable artifact whose diff is forced to appear in every PR that adds,
removes, or renames an action — a drift gate that is a CI step, not
advisory theater.

  - ``--write-golden`` regenerates the golden file from the code. Run it
    in the same commit that bumps ``_KNOWN_ACTIONS`` (or via closeout).
  - ``--check`` (the CI mode) regenerates the golden IN MEMORY and
    compares against the on-disk file; any mismatch → exit 1 with a
    unified-diff-style report so the fix is ``--write-golden`` + commit.
  - When ``--check`` is NOT passed the script behaves exactly as before
    (live cross-check only), so this augmentation is **default-OFF**: the
    golden gate only runs when a caller opts in with ``--check``.

The golden is intentionally a flat sorted newline-delimited list (NOT a
re-serialization of the schema table) so it stays diff-friendly and free
of the schema's per-action required-field prose. It is the *inventory*
contract, complementary to (not a replacement for) the schema table.

## Exit codes

  0 — all sub-checks pass (and golden matches under ``--check``)
  1 — drift detected (registered/schema/orphan mismatch, OR golden drift)
  2 — internal error (missing source file, malformed input, golden
      unreadable under ``--check``)

## Output format

On FAIL, emits a structured report on stdout with file:line references
for every drift item so maintainers can jump straight to the offending
line. On PASS (or ``--verbose``), emits a one-line OK summary plus the
set sizes.

## Design decisions

  - **AST for code-side extraction** (NOT regex). ``ast`` gives precise
    set-literal membership and call-node discovery; regex would match
    commented-out code + docstrings.
  - **AST for orphan-call discovery**. Every call to ``emit_<name>``
    surfaces as a ``Call`` AST node only when the source actually
    executes that call — docstring mentions + comments never parse to
    ``Call`` nodes.
  - **Normative function-def coverage**. Every ``def emit_<name>`` in
    ``audit_emit.py`` MUST have ``<name>`` in ``_KNOWN_ACTIONS`` — this
    cross-check is lightweight and catches copy-paste regressions.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUDIT_EMIT_REL = Path(".claude/hooks/_lib/audit_emit.py")
SCHEMA_REL = Path("SPEC/v1/audit-log.schema.md")

# PLAN-133 E8 — checked-in golden inventory of the audit-action registry,
# generated FROM the typed helpers. ``--write-golden`` (re)writes it;
# ``--check`` asserts the on-disk file matches the freshly generated one.
GOLDEN_REL = Path(".claude/data/audit-registry.golden.txt")

# Stable header for the generated golden. The version token lets a future
# format change invalidate stale goldens without a silent false-match.
_GOLDEN_HEADER = "# audit-action registry golden (generated — do not hand-edit)"
_GOLDEN_FORMAT_LINE = "# format: v1  source: .claude/hooks/_lib/audit_emit.py::_KNOWN_ACTIONS"
_GOLDEN_REGEN_HINT = (
    "# regenerate: python3 .claude/scripts/check-audit-registry-coverage.py --write-golden"
)

# Directories that are legitimately searched for emit_* call sites.
# Tests are excluded — they contain fixtures that intentionally use
# non-registered names, and they never run in production.
SCAN_DIRS_REL: Tuple[Path, ...] = (
    Path(".claude/scripts"),
    Path(".claude/hooks"),
)

# Subpath fragments that exclude a file from scan (tests, fixtures).
EXCLUDE_PATH_FRAGMENTS: Tuple[str, ...] = (
    "/tests/",
    "/fixtures/",
    "/__pycache__/",
)

# The audit_emit module itself contains every ``def emit_<name>`` and
# internal ``_write_event`` plumbing — it is the source of truth and is
# not scanned as a caller. Resolved to absolute at check time.
EXCLUDE_FILES_REL: Tuple[Path, ...] = (
    AUDIT_EMIT_REL,
)

# Match a row in the schema table: ``| `<action_name>` (v2.X) | ...``
# Lead-column regex only — we tolerate ``(v2)``, ``(v2.1)``, ``(v2.4)`` etc.
# Action must be lowercase snake_case per convention.
_SCHEMA_ROW_RE = re.compile(
    r"^\|\s*`([a-z][a-z0-9_\-]*)`\s*(?:\([^)]+\))?\s*\|",
)

# Action names accepted by the registry: lowercase snake_case (with
# optional hyphens for grandfathered names like ``codex-reply``),
# leading letter, no digits at start. Enforced case-sensitivity —
# ``Emit_Foo`` or ``emit_FOO`` are NOT valid.
# PLAN-091 v1.22.1 (S115 2026-05-13) — allow hyphen for `codex-reply`
# legacy name from PLAN-086 Wave C; net-new actions should still
# prefer snake_case per the rest of the canonical action surface.
_ACTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_\-]*$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class CallSite:
    """One ``emit_<name>(...)`` call site discovered by AST walk."""

    __slots__ = ("name", "file", "line")

    def __init__(self, name: str, file: Path, line: int) -> None:
        self.name = name
        self.file = file
        self.line = line

    def ref(self, repo_root: Path) -> str:
        try:
            rel = self.file.relative_to(repo_root)
        except ValueError:
            rel = self.file
        return f"{rel}:{self.line}"


class FunctionDef:
    """One ``def emit_<name>(...)`` discovered in audit_emit.py."""

    __slots__ = ("name", "line")

    def __init__(self, name: str, line: int) -> None:
        self.name = name
        self.line = line


# ---------------------------------------------------------------------------
# Extractors — code side
# ---------------------------------------------------------------------------


def extract_known_actions(audit_emit_path: Path) -> Tuple[Set[str], List[FunctionDef]]:
    """Parse audit_emit.py and return (registered_actions, emit_function_defs).

    Uses AST to find the ``_KNOWN_ACTIONS`` assignment (Set literal) and
    every top-level ``def emit_<name>`` function.
    """
    source = audit_emit_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(audit_emit_path))
    except SyntaxError as exc:
        raise RuntimeError(
            f"audit_emit.py parse error at line {exc.lineno}: {exc.msg}"
        ) from exc

    known: Optional[Set[str]] = None
    emit_defs: List[FunctionDef] = []

    for node in ast.walk(tree):
        # _KNOWN_ACTIONS = {...}  — single-target Assign to a Set literal
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "_KNOWN_ACTIONS":
                value = node.value
                if not isinstance(value, ast.Set):
                    raise RuntimeError(
                        f"_KNOWN_ACTIONS at line {node.lineno} is not a set literal "
                        f"(found {type(value).__name__})"
                    )
                collected: Set[str] = set()
                for elt in value.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        collected.add(elt.value)
                    else:
                        raise RuntimeError(
                            f"_KNOWN_ACTIONS at line {node.lineno} contains non-str "
                            f"element: {ast.dump(elt)}"
                        )
                known = collected

        # def emit_<name>(...)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("emit_"):
            action = node.name[len("emit_"):]
            if _ACTION_NAME_RE.match(action):
                emit_defs.append(FunctionDef(action, node.lineno))

    if known is None:
        raise RuntimeError(
            "_KNOWN_ACTIONS set literal not found in audit_emit.py"
        )
    return known, emit_defs


# ---------------------------------------------------------------------------
# Extractors — schema side
# ---------------------------------------------------------------------------


def extract_schema_actions(schema_path: Path) -> Set[str]:
    """Return set of action names in the Required-fields table."""
    try:
        text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"schema unreadable: {exc}") from exc

    actions: Set[str] = set()
    in_table = False
    header_marker = "Required fields per v2 action"

    for raw in text.splitlines():
        line = raw.rstrip()
        if header_marker in line:
            in_table = True
            continue
        if in_table:
            match = _SCHEMA_ROW_RE.match(line)
            if match:
                name = match.group(1)
                # Header row has "action" as the column name — skip it.
                if name == "action":
                    continue
                if _ACTION_NAME_RE.match(name):
                    actions.add(name)
            else:
                # Table ends at first non-table line AFTER we saw at
                # least one real row — tolerate leading header/separator
                # markup before real rows.
                if actions and line.strip() and not line.startswith("|"):
                    break

    if not actions:
        raise RuntimeError(
            f"no action rows found in {schema_path} (looked for "
            f"'{header_marker}' table)"
        )
    return actions


# ---------------------------------------------------------------------------
# Extractors — call sites
# ---------------------------------------------------------------------------


def _iter_python_files(repo_root: Path) -> Iterable[Path]:
    """Yield every .py file under SCAN_DIRS, excluding tests/fixtures/self."""
    exclude_abs: Set[Path] = set()
    for rel in EXCLUDE_FILES_REL:
        exclude_abs.add((repo_root / rel).resolve())

    for scan_rel in SCAN_DIRS_REL:
        scan_dir = repo_root / scan_rel
        if not scan_dir.is_dir():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            abs_path = path.resolve()
            if abs_path in exclude_abs:
                continue
            # Posix-style suffix match (portable across OS).
            rel_posix = "/" + str(path.relative_to(repo_root)).replace(os.sep, "/")
            if any(frag in rel_posix for frag in EXCLUDE_PATH_FRAGMENTS):
                continue
            yield path


def _collect_audit_imports(tree: ast.AST) -> Tuple[Set[str], Dict[str, str]]:
    """Return (module_aliases, from_import_bindings) for this file.

    ``module_aliases`` is the set of local names that reference the
    ``_lib.audit_emit`` module (e.g. ``{"audit_emit", "_audit_emit", "_audit"}``).
    Accepts ``from _lib import audit_emit [as <alias>]`` patterns.

    ``from_import_bindings`` maps a locally-bound name to the original
    ``emit_<name>`` identifier imported from audit_emit. For example,
    ``from _lib.audit_emit import emit_foo as _foo`` yields
    ``{"_foo": "emit_foo"}``; a plain ``import emit_foo`` (no alias)
    yields ``{"emit_foo": "emit_foo"}``.
    """
    module_aliases: Set[str] = set()
    from_bindings: Dict[str, str] = {}

    for node in ast.walk(tree):
        # Pattern A:  from _lib import audit_emit [as X]
        #             from _lib.audit_emit import emit_foo [as Y]
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "_lib" or module.endswith("._lib"):
                # from _lib import audit_emit [as X]
                for alias in node.names:
                    if alias.name == "audit_emit":
                        local = alias.asname or alias.name
                        module_aliases.add(local)
            elif module == "_lib.audit_emit" or module.endswith("._lib.audit_emit"):
                # from _lib.audit_emit import emit_foo [as Y]
                for alias in node.names:
                    original = alias.name
                    if original.startswith("emit_") and _ACTION_NAME_RE.match(
                        original[len("emit_"):]
                    ):
                        local = alias.asname or alias.name
                        from_bindings[local] = original
        # Pattern B:  import _lib.audit_emit [as X]  (rare but possible)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.endswith("_lib.audit_emit") or alias.name == "audit_emit":
                    # Import names are dotted; the binding is the first dotted
                    # component unless aliased. `import a.b` binds `a`; we'd
                    # need `a.b` access. For `as X`, binding is `X`.
                    if alias.asname:
                        module_aliases.add(alias.asname)
                    # Without asname, bare `import _lib.audit_emit` binds `_lib`
                    # at module scope — we'd only see `_lib.audit_emit.emit_foo`
                    # access. Model that via nested Attribute below.
    return module_aliases, from_bindings


def _collect_getattr_aliases(
    tree: ast.AST, module_aliases: Set[str]
) -> Dict[str, str]:
    """Detect ``X = getattr(audit_emit, "emit_<name>", ...)`` patterns and
    return a binding map ``{local_name: original_emit_<name>}``. Reused by
    the call-site walker via the existing ``from_bindings`` lookup path.

    Codex audit-v3 (Session 76, DIM-04 finding 2 follow-up): the prior
    AST walker only saw direct attribute access (``audit_emit.emit_foo``)
    and ``from _lib.audit_emit import emit_foo``. ``check_skill_bootstrap_post``
    intentionally uses ``getattr(audit_emit, "emit_generic", None)`` for a
    soft-fallback if the symbol is unavailable; that pattern was invisible
    to the registry checker, so ``skill_bootstrap_post_hash`` slipped past
    the orphan check.
    """
    aliases: Dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            continue
        if not isinstance(value.func, ast.Name) or value.func.id != "getattr":
            continue
        if len(value.args) < 2:
            continue
        obj_arg = value.args[0]
        attr_arg = value.args[1]
        # Object must reference the audit_emit module (or one of its aliases).
        if not isinstance(obj_arg, ast.Name) or obj_arg.id not in module_aliases:
            continue
        # Attribute name must be a string-literal beginning with ``emit_``.
        if not isinstance(attr_arg, ast.Constant) or not isinstance(attr_arg.value, str):
            continue
        attr_name = attr_arg.value
        if not attr_name.startswith("emit_"):
            continue
        suffix = attr_name[len("emit_"):]
        if not _ACTION_NAME_RE.match(suffix):
            continue
        aliases[target.id] = attr_name
    return aliases


def _extract_emit_suffix(call_func: ast.AST, module_aliases: Set[str],
                         from_bindings: Dict[str, str]) -> Optional[str]:
    """Return the ``<suffix>`` for a Call.func resolvable to
    ``audit_emit.emit_<suffix>`` in this file's import context; None otherwise.

    Cases:

      1. ``audit_emit.emit_foo(...)`` / ``_audit_emit.emit_foo(...)`` —
         Attribute with value=Name(id in module_aliases) and attr starting
         with ``emit_``.
      2. ``emit_foo(...)`` after ``from _lib.audit_emit import emit_foo`` —
         Name(id in from_bindings). The registered action is the suffix of
         the *original* import name, NOT the alias.
      3. ``_lib.audit_emit.emit_foo(...)`` — nested Attribute. Tolerate via
         walk of the Attribute chain.
    """
    # Case 2: bare Name that resolves to a from-import binding.
    if isinstance(call_func, ast.Name):
        original = from_bindings.get(call_func.id)
        if original and original.startswith("emit_"):
            suffix = original[len("emit_"):]
            if _ACTION_NAME_RE.match(suffix):
                return suffix
        return None

    # Cases 1 + 3: Attribute access. Walk the attribute chain to its root.
    if isinstance(call_func, ast.Attribute):
        attr = call_func.attr
        if not attr.startswith("emit_"):
            return None
        suffix = attr[len("emit_"):]
        if not _ACTION_NAME_RE.match(suffix):
            return None

        # Drill down the .value chain: for `audit_emit.emit_foo`, the
        # value is Name("audit_emit"). For `_lib.audit_emit.emit_foo`,
        # the value is Attribute(value=Name("_lib"), attr="audit_emit").
        value = call_func.value
        if isinstance(value, ast.Name):
            if value.id in module_aliases:
                return suffix
            return None
        if isinstance(value, ast.Attribute):
            if value.attr == "audit_emit":
                return suffix
            return None
    return None


def _resolve_generic_action_literal(call_node: ast.Call) -> Optional[str]:
    """For an ``emit_generic(...)`` call, return the action name iff it is
    a string literal. Returns None for dynamic dispatch
    (``emit_generic(some_var, ...)``) which cannot be statically verified.

    Accepts both positional form ``emit_generic("name", ...)`` and keyword
    form ``emit_generic(action="name", ...)``. Codex audit-v3 (Session 76,
    DIM-04 finding 2): the prior implementation ignored ``emit_generic``
    literals entirely, so unregistered actions like ``skill_bootstrap_used``
    were silently dropped at runtime while CI reported clean.
    """
    if call_node.args:
        arg0 = call_node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            return arg0.value
        return None
    for kw in call_node.keywords:
        if kw.arg == "action":
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
            return None
    return None


def extract_call_sites(repo_root: Path) -> List[CallSite]:
    """Walk every .py under scan dirs and collect audit_emit call sites.

    AST-based with per-file import resolution: a call site is recorded
    only when it resolves to ``_lib.audit_emit.emit_<name>`` via the
    file's import context. This eliminates false-positive collisions
    with unrelated helpers that happen to use the ``emit_`` prefix
    (``emit_decision`` in hooks, ``emit_json``/``emit_markdown`` in
    benchmark formatters, locally-scoped ``emit_deny``/``emit_invoke``
    wrappers, etc.).

    ``emit_generic("name", ...)`` is resolved one level deeper: the
    string-literal action is recorded as the call site name so the orphan
    check can verify it against ``_KNOWN_ACTIONS`` + schema. Dynamic
    dispatch (``emit_generic(var, ...)``) is silently skipped because it
    cannot be statically verified. (Session 76 DIM-04 finding 2 closure.)
    """
    sites: List[CallSite] = []
    for path in _iter_python_files(repo_root):
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            # Tolerate un-parseable files (e.g. partial scripts under
            # development). A syntax error in a production .py file is
            # a bigger problem than the registry check — a different
            # CI step should surface it.
            continue

        module_aliases, from_bindings = _collect_audit_imports(tree)
        if not module_aliases and not from_bindings:
            # File never imports audit_emit in any form — nothing to check.
            continue

        # Codex audit-v3 closure: also resolve ``X = getattr(audit_emit,
        # "emit_<name>", ...)`` aliases so indirect dispatch sites like
        # ``check_skill_bootstrap_post._emit_post_hash`` are covered.
        getattr_aliases = _collect_getattr_aliases(tree, module_aliases)
        if getattr_aliases:
            combined_bindings: Dict[str, str] = dict(from_bindings)
            combined_bindings.update(getattr_aliases)
        else:
            combined_bindings = from_bindings

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                suffix = _extract_emit_suffix(
                    node.func, module_aliases, combined_bindings
                )
                if suffix is None:
                    continue
                if suffix == "generic":
                    literal = _resolve_generic_action_literal(node)
                    if literal is not None and _ACTION_NAME_RE.match(literal):
                        sites.append(CallSite(literal, path, node.lineno))
                    continue
                sites.append(CallSite(suffix, path, node.lineno))
    return sites


# ---------------------------------------------------------------------------
# Check orchestrator
# ---------------------------------------------------------------------------


def _load_inputs(repo_root: Path) -> "tuple[Any, Any, Any, Any]":
    """PLAN-023 closeout helper 1/3 — existence gate + parse three sources.

    Returns ``(known_actions, emit_defs, schema_actions, call_sites)`` on
    success; raises ``_InternalError`` (exit 2) on any gating failure.
    """
    audit_emit_path = repo_root / AUDIT_EMIT_REL
    schema_path = repo_root / SCHEMA_REL

    if not audit_emit_path.is_file():
        raise _InternalError(f"audit_emit.py not found at {audit_emit_path}")
    if not schema_path.is_file():
        raise _InternalError(f"schema not found at {schema_path}")

    try:
        known_actions, emit_defs = extract_known_actions(audit_emit_path)
    except RuntimeError as exc:
        raise _InternalError(str(exc))

    try:
        schema_actions = extract_schema_actions(schema_path)
    except RuntimeError as exc:
        raise _InternalError(str(exc))

    call_sites = extract_call_sites(repo_root)
    return known_actions, emit_defs, schema_actions, call_sites


def _compute_drift(known_actions, emit_defs, schema_actions, call_sites) -> "tuple[Any, Any, Any, Any]":
    """PLAN-023 closeout helper 2/3 — cross-check the three sources.

    Returns ``(missing_in_schema, missing_in_code, unregistered_defs,
    orphan_calls)``. Pure function — no I/O, no side effects.

    Note on `emit_generic`: this is a dispatcher-style emitter that
    accepts the action name as its first positional argument, enabling
    late-registration paths (PLAN-041 RAG sidecar + PLAN-043 tier-policy
    use it to avoid hard-coding per-action helpers during the
    staged-canonical window). It is NOT itself a named action; the
    action it emits is the argument, and each such argument must
    independently appear in `_KNOWN_ACTIONS` + schema.

    Session 76 (DIM-04 finding 2) tightened the call-site walker to
    resolve ``emit_generic("name", ...)`` literals as ``CallSite(name=...,
    ...)`` so the orphan check covers them. ``def emit_generic`` itself is
    still excluded from the unregistered-def check (it is a dispatcher
    that does not name an action).
    """
    _DISPATCH_EMITTERS = frozenset({"generic"})

    missing_in_schema: List[str] = sorted(known_actions - schema_actions)
    missing_in_code: List[str] = sorted(schema_actions - known_actions)
    unregistered_defs: List[FunctionDef] = [
        d
        for d in emit_defs
        if d.name not in known_actions and d.name not in _DISPATCH_EMITTERS
    ]
    # Note: extract_call_sites() now resolves emit_generic("name", ...) into
    # CallSite(name="name", ...), so the orphan check naturally covers
    # generic-dispatched actions. Dynamic dispatch (variable, not literal)
    # is silently skipped at extraction time and therefore never appears here.
    orphan_calls: List[CallSite] = [
        site
        for site in call_sites
        if site.name not in known_actions
    ]
    return missing_in_schema, missing_in_code, unregistered_defs, orphan_calls


def _emit_drift_report(
    missing_in_schema,
    missing_in_code,
    unregistered_defs,
    orphan_calls,
    emit_defs,
    repo_root: Path,
) -> None:
    """PLAN-023 closeout helper 3/3 — render structured drift report to stderr."""
    out = sys.stderr
    print("AUDIT REGISTRY DRIFT DETECTED", file=out)
    print("", file=out)

    if missing_in_schema:
        print(
            "Missing from SPEC/v1/audit-log.schema.md (registered in "
            "_KNOWN_ACTIONS but no schema row):",
            file=out,
        )
        for name in missing_in_schema:
            hint_def = next((d for d in emit_defs if d.name == name), None)
            if hint_def is not None:
                print(
                    f"  - {name} (registered; see "
                    f"{AUDIT_EMIT_REL}:{hint_def.line})",
                    file=out,
                )
            else:
                print(f"  - {name} (registered in _KNOWN_ACTIONS)", file=out)
        print("", file=out)

    if missing_in_code:
        print(
            "Missing from _KNOWN_ACTIONS (_lib/audit_emit.py) (documented "
            "in schema but not registered):",
            file=out,
        )
        for name in missing_in_code:
            print(f"  - {name} (documented in {SCHEMA_REL})", file=out)
        print("", file=out)

    if unregistered_defs:
        print(
            "emit_<name>() function defined but <name> not in "
            "_KNOWN_ACTIONS:",
            file=out,
        )
        for d in unregistered_defs:
            print(
                f"  - emit_{d.name} at {AUDIT_EMIT_REL}:{d.line}; "
                f"add '{d.name}' to _KNOWN_ACTIONS",
                file=out,
            )
        print("", file=out)

    if orphan_calls:
        print(
            "Orphan emit_<name>() calls (no matching action in "
            "_KNOWN_ACTIONS):",
            file=out,
        )
        for site in orphan_calls:
            print(
                f"  - emit_{site.name} called at {site.ref(repo_root)}; "
                f"register '{site.name}' first",
                file=out,
            )
        print("", file=out)

    print(
        "Remediation: add missing entries to BOTH sources "
        "(_KNOWN_ACTIONS + schema table) and bump the schema version "
        "(v2.X) per SPEC/v1 additivity rules. See ADR-043 §SOC2 audit "
        "mapping for the schema-versioning procedure.",
        file=out,
    )


# ---------------------------------------------------------------------------
# Golden inventory (PLAN-133 E8) — generate SPEC inventory FROM typed helpers
# ---------------------------------------------------------------------------


def build_registry_golden(known_actions: Set[str], emit_defs: List[FunctionDef]) -> str:
    """Render the deterministic golden inventory text from the typed helpers.

    The golden is the SORTED UNION of:

      - every member of ``_KNOWN_ACTIONS`` (the registered-action set), and
      - every ``def emit_<name>`` action whose ``<name>`` is in
        ``_KNOWN_ACTIONS`` (the dispatcher ``emit_generic`` is excluded —
        it names no action, mirroring ``_DISPATCH_EMITTERS``).

    A ``def emit_<name>`` whose ``<name>`` is NOT registered is intentionally
    EXCLUDED from the golden: that is an *unregistered-def* drift the live
    cross-check already fails on (exit 1), so it must never silently appear
    in the golden inventory.

    The output is newline-terminated, header-prefixed, and stable across
    runs (pure ``sorted`` over a ``set``) so the on-disk golden diff is
    minimal and review-friendly. Pure function — no I/O.
    """
    _DISPATCH_EMITTERS = frozenset({"generic"})
    # The golden inventory is exactly the registered-action set. emit_defs
    # is accepted so callers can (cheaply) assert the def/registry agreement
    # invariant, but a registered action without a def is still a real,
    # emit_generic-dispatched action and MUST appear in the inventory.
    registered_def_names = {
        d.name
        for d in emit_defs
        if d.name in known_actions and d.name not in _DISPATCH_EMITTERS
    }
    # Union keeps a def-only edge case impossible by construction (a def
    # whose name is unregistered is excluded above), so the union equals
    # known_actions; we compute it explicitly for clarity/robustness.
    inventory = sorted(set(known_actions) | registered_def_names)

    lines = [_GOLDEN_HEADER, _GOLDEN_FORMAT_LINE, _GOLDEN_REGEN_HINT, f"# count: {len(inventory)}"]
    lines.extend(inventory)
    return "\n".join(lines) + "\n"


def _read_golden(golden_path: Path) -> Optional[str]:
    """Read the on-disk golden, or None if absent. Raises on unreadable."""
    if not golden_path.is_file():
        return None
    try:
        return golden_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _InternalError(f"golden unreadable at {golden_path}: {exc}")


def _golden_diff(expected: str, actual: str) -> List[str]:
    """Return a compact unified diff (expected = generated, actual = on-disk).

    ``expected`` is the freshly generated golden (the correct content);
    ``actual`` is what is committed. Lines prefixed ``-`` are stale lines
    present on disk that should be removed; ``+`` are lines the generator
    now produces that are missing on disk.
    """
    import difflib

    diff = difflib.unified_diff(
        actual.splitlines(),
        expected.splitlines(),
        fromfile="on-disk golden",
        tofile="generated (expected)",
        lineterm="",
        n=1,
    )
    return list(diff)


def write_golden(repo_root: Path) -> int:
    """``--write-golden`` — regenerate the golden file from the typed helpers.

    Returns 0 on success, 2 on internal error (missing/parse-failing source).
    Creates ``.claude/data/`` if absent.
    """
    try:
        known_actions, emit_defs, _schema_actions, _call_sites = _load_inputs(repo_root)
    except _InternalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    golden_text = build_registry_golden(known_actions, emit_defs)
    golden_path = repo_root / GOLDEN_REL
    try:
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(golden_text, encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot write golden at {golden_path}: {exc}", file=sys.stderr)
        return 2
    print(
        f"wrote golden ({len(known_actions)} actions) to {GOLDEN_REL}",
        file=sys.stderr,
    )
    return 0


def check_golden(repo_root: Path, verbose: bool = False) -> int:
    """``--check`` — assert the on-disk golden matches the generated one.

    Generates the golden IN MEMORY from the typed helpers and compares
    byte-for-byte against ``.claude/data/audit-registry.golden.txt``.

    Returns:
      0 — golden present and matches
      1 — golden drift (mismatch OR absent — both require ``--write-golden``)
      2 — internal error (source unreadable/parse-failing, golden unreadable)

    Note: an ABSENT golden under ``--check`` is treated as drift (exit 1),
    not infra failure — the fix is the same ``--write-golden`` + commit.
    """
    try:
        known_actions, emit_defs, _schema_actions, _call_sites = _load_inputs(repo_root)
    except _InternalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    expected = build_registry_golden(known_actions, emit_defs)
    golden_path = repo_root / GOLDEN_REL

    try:
        actual = _read_golden(golden_path)
    except _InternalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if actual is None:
        print(
            f"AUDIT REGISTRY GOLDEN MISSING: {GOLDEN_REL} does not exist.\n"
            f"Generate it with:\n"
            f"  python3 .claude/scripts/check-audit-registry-coverage.py --write-golden\n"
            f"then commit the file.",
            file=sys.stderr,
        )
        return 1

    if actual == expected:
        if verbose:
            print(
                f"OK: audit registry golden in sync "
                f"({len(known_actions)} actions, {GOLDEN_REL})"
            )
        else:
            print("OK: audit registry golden in sync")
        return 0

    print("AUDIT REGISTRY GOLDEN DRIFT DETECTED", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        f"The checked-in golden ({GOLDEN_REL}) does not match the registry "
        f"generated from _KNOWN_ACTIONS. Diff (on-disk vs generated):",
        file=sys.stderr,
    )
    for line in _golden_diff(expected, actual):
        print(f"  {line}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Remediation: regenerate + commit the golden —\n"
        "  python3 .claude/scripts/check-audit-registry-coverage.py --write-golden\n"
        "(run this in the SAME commit that changes _KNOWN_ACTIONS).",
        file=sys.stderr,
    )
    return 1


class _InternalError(Exception):
    """Raised for fatal input-gate failures; maps to exit code 2."""


def check(
    repo_root: Path,
    verbose: bool = False,
) -> int:
    """Run all three sub-checks. Return 0 (pass) / 1 (drift) / 2 (internal).

    PLAN-023 closeout decomposition: thin orchestrator over three
    helpers (``_load_inputs``, ``_compute_drift``, ``_emit_drift_report``).
    Behavior byte-identical to the pre-decomposition 150-LoC monolith.
    """
    try:
        known_actions, emit_defs, schema_actions, call_sites = _load_inputs(
            repo_root
        )
    except _InternalError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    missing_in_schema, missing_in_code, unregistered_defs, orphan_calls = (
        _compute_drift(known_actions, emit_defs, schema_actions, call_sites)
    )

    any_drift = bool(
        missing_in_schema or missing_in_code or unregistered_defs or orphan_calls
    )

    if not any_drift:
        if verbose:
            print(
                f"OK: audit registry in sync "
                f"(known={len(known_actions)}, schema={len(schema_actions)}, "
                f"emit_defs={len(emit_defs)}, call_sites={len(call_sites)})"
            )
        else:
            print("OK: audit registry in sync")
        return 0

    _emit_drift_report(
        missing_in_schema,
        missing_in_code,
        unregistered_defs,
        orphan_calls,
        emit_defs,
        repo_root,
    )
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_repo_root() -> Path:
    """Derive repo root from the script's own location (scripts/..)."""
    script_dir = Path(__file__).resolve().parent  # .claude/scripts
    return script_dir.parent.parent  # repo root


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert every _KNOWN_ACTIONS entry is covered in SPEC."""
    parser = argparse.ArgumentParser(
        description=(
            "Assert the audit event registry (_KNOWN_ACTIONS) is in sync "
            "with SPEC/v1/audit-log.schema.md and every emit_<name>() "
            "call site resolves to a registered action."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help=(
            "Repo root path (default: derive from script location)"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit OK summary with set sizes on pass",
    )
    # PLAN-133 E8 — golden-inventory modes. These are mutually exclusive
    # with each other; either can be combined with --verbose. When neither
    # is passed the script runs the legacy live cross-check (default-OFF
    # for the golden gate).
    golden_group = parser.add_mutually_exclusive_group()
    golden_group.add_argument(
        "--check",
        action="store_true",
        help=(
            "Golden-drift mode: regenerate the audit-action inventory from "
            "the typed helpers and assert it matches the checked-in "
            f"{GOLDEN_REL} (CI step). Exit 1 on drift or absence."
        ),
    )
    golden_group.add_argument(
        "--write-golden",
        action="store_true",
        help=(
            f"Regenerate {GOLDEN_REL} from _KNOWN_ACTIONS + emit defs and "
            "write it to disk (run in the commit that changes the registry)."
        ),
    )
    args = parser.parse_args(argv)

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        root = _default_repo_root()

    if args.write_golden:
        return write_golden(root)
    if args.check:
        return check_golden(root, verbose=args.verbose)

    return check(root, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
