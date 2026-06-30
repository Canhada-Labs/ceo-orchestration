#!/usr/bin/env python3
"""PLAN-119 WS-C / WS-E E2c — static gate against test subprocess spawns that
could write to the LIVE audit log.

The durable protection is WS-A: the session-scoped autouse fixture redirects
``CEO_AUDIT_LOG_DIR`` (the primary audit-path resolver) to an isolated tmpdir,
so a child that INHERITS or SPREADS ``os.environ`` resolves the isolated dir.
The danger is a subprocess that spawns a framework process (a ``check_*`` hook
or anything importing ``audit_emit``) with a **hand-built minimal ``env=`` dict
that omits the audit carriers** — that child falls back to the real
``~/.claude`` and pollutes the live chain.

This checker walks each test file's AST and flags a ``subprocess.run`` /
``Popen`` / ``call`` / ``check_call`` / ``check_output`` call whose ``env=``
kwarg is a **dict literal that does NOT spread ``os.environ``** and is NOT built
by ``TestEnvContext.subprocess_env(...)`` / ``audit_carrier_overrides(...)``.
Such a call must instead spread ``os.environ`` (carrying the WS-A redirect) or
use ``self.subprocess_env()``.

Safe env forms (NOT flagged):
  - ``env=os.environ`` / ``dict(os.environ)`` / ``os.environ.copy()``
  - ``env={**os.environ, ...}``
  - ``env=self.subprocess_env(...)`` / ``env=...audit_carrier_overrides(...)``
  - ``env=<a Name>`` (a variable — too dynamic to judge statically; assumed the
    author derived it from os.environ; WS-A still protects in-process resolution)
  - no ``env=`` kwarg at all (inherits the redirected parent env)

Exit 0 = clean; exit 1 = at least one unsafe spawn (prints file:line).

Fail-OPEN on parse error of an individual file (skips it with a warning) so a
syntactically-novel test file never hard-blocks the gate.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import List, Optional, Tuple

_SPAWN_ATTRS = {"run", "Popen", "call", "check_call", "check_output"}


def _spreads_os_environ(dict_node: ast.Dict) -> bool:
    """True if the dict literal contains ``**os.environ`` (key is None for **)."""
    for k, v in zip(dict_node.keys, dict_node.values):
        if k is None:  # ** unpacking
            if _refs_os_environ(v):
                return True
    return False


def _dict_sets_audit_anchor(dict_node: ast.Dict) -> bool:
    """True if a dict literal explicitly sets ``HOME`` or ``CEO_AUDIT_LOG_DIR`` —
    a deliberate audit-dir anchor (e.g. an install-sandbox test that sets
    ``HOME=<tmp sandbox>``). Static analysis cannot verify the VALUE is non-live,
    but setting an anchor IS the author's explicit isolation choice. A dict that
    sets NEITHER and does not spread os.environ falls back to the real ``~/`` and
    is the genuine live-pollution vector."""
    for k in dict_node.keys:
        if isinstance(k, ast.Constant) and k.value in ("HOME", "CEO_AUDIT_LOG_DIR"):
            return True
    return False


def _refs_os_environ(node: ast.AST) -> bool:
    """True if the expression references os.environ (Attribute or Subscript)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute) and sub.attr == "environ":
            return True
        if isinstance(sub, ast.Name) and sub.id == "environ":
            return True
    return False


# env-builder call names that are known-safe by construction.
_SAFE_BUILDER_NAMES = {"subprocess_env", "audit_carrier_overrides", "copy", "dict"}


def _is_subprocess_spawn(call: ast.Call) -> bool:
    fn = call.func
    if not isinstance(fn, ast.Attribute) or fn.attr not in _SPAWN_ATTRS:
        return False
    # require the receiver to be `subprocess` (subprocess.run/Popen/...) — avoids
    # flagging unrelated .run()/.call() methods on other objects.
    recv = fn.value
    if isinstance(recv, ast.Name) and recv.id == "subprocess":
        return True
    if isinstance(recv, ast.Attribute) and recv.attr == "subprocess":
        return True
    return False


def _def_refs_os_environ(def_map: dict, name: str, _seen=None) -> bool:
    """True if the function/method ``name`` (resolved in ``def_map``) derives from
    os.environ — i.e. its body references os.environ anywhere (e.g. an ``_env``
    helper doing ``e = os.environ.copy(); ...; return e``). One level of helper
    delegation is followed. A helper that NEVER touches os.environ (returns a
    minimal dict) is NOT safe and is flagged at the call site."""
    if _seen is None:
        _seen = set()
    if name in _seen or name not in def_map:
        return False
    _seen.add(name)
    fn = def_map[name]
    for sub in ast.walk(fn):
        if _refs_os_environ(sub):
            return True
        # follow one level of delegation: return helper() / return self.helper()
        if isinstance(sub, ast.Call):
            f = sub.func
            n = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if n in _SAFE_BUILDER_NAMES:
                return True
            if n and n != name and _def_refs_os_environ(def_map, n, _seen):
                return True
    return False


def _call_env_is_safe(call: ast.Call, def_map: dict) -> bool:
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    if name in _SAFE_BUILDER_NAMES:
        return True
    # author-defined env builder (self._env(), make_env(), ...): safe ONLY if its
    # body derives from os.environ. Unresolvable name → conservatively flag.
    return _def_refs_os_environ(def_map, name)


def _name_env_is_safe(name: str, scope: ast.AST, def_map: dict) -> bool:
    """A variable passed as env=: safe if SOME assignment to it within the
    enclosing scope derives from os.environ (or a safe builder). Unassigned /
    minimal-dict assignment → flag."""
    safe = False
    found_assign = False
    for sub in ast.walk(scope):
        if isinstance(sub, ast.Assign):
            targets = [t.id for t in sub.targets if isinstance(t, ast.Name)]
            if name in targets:
                found_assign = True
                v = sub.value
                if _refs_os_environ(v):
                    return True
                if isinstance(v, ast.Call) and _call_env_is_safe(v, def_map):
                    return True
                if isinstance(v, ast.Dict) and (
                    _spreads_os_environ(v) or _dict_sets_audit_anchor(v)
                ):
                    return True
    # No assignment found in this scope (param / closure / import) → can't judge;
    # conservatively treat as safe to avoid false positives on env vars threaded
    # in from a fixture. A minimal-dict assignment we DID find returns False.
    return safe if found_assign else True


def _env_is_safe(env_node: ast.AST, scope: ast.AST, def_map: dict) -> bool:
    # env=os.environ / dict(os.environ) / os.environ.copy() / {**os.environ}
    if _refs_os_environ(env_node):
        return True
    if isinstance(env_node, ast.Dict):
        return _spreads_os_environ(env_node) or _dict_sets_audit_anchor(env_node)
    if isinstance(env_node, ast.Call):
        return _call_env_is_safe(env_node, def_map)
    if isinstance(env_node, ast.Name):
        return _name_env_is_safe(env_node.id, scope, def_map)
    # BinOp merge / comprehension referencing os.environ is caught above; a bare
    # form that does not reference os.environ is conservatively flagged.
    return False


# ---------------------------------------------------------------------------
# PLAN-119-FOLLOWUP WS-2 — ``_lib.audit_emit`` shadow-loader restore gate.
#
# A test that INSTALLS a non-canonical ``_lib.audit_emit`` into the canonical
# import slot — ``sys.modules["_lib.audit_emit"] = <module>`` (or a variable bound
# to that literal), ``sys.modules.update({"_lib.audit_emit": …})`` /
# ``.setdefault("_lib.audit_emit", …)``, or
# ``importlib.util.spec_from_file_location("_lib.audit_emit", path)`` — must also
# RESTORE the canonical module IN ITS TEARDOWN, else a LATER test's
# ``mock.patch("_lib.audit_emit.emit_*")`` raises ``AttributeError: module '_lib'
# has no attribute 'audit_emit'`` — the cross-suite shadow leak that reddened CI
# on ``19ab91d`` (the combined ``pytest hooks/ scripts/`` matrix step). PLAN-119's
# hotfix ``b5ccfca`` fixed the one real loader; this is the STATIC, detection-only
# tripwire that prevents a FUTURE loader from regressing. It can only RED ci,
# never SUPPRESS at runtime (the suppression-vector reason the PLAN-119 WS-B
# kernel-guard was dropped).
#
# Scope (best-effort tripwire, NOT an adversarial-complete proof): the gate
# catches the realistic install forms — ``sys.modules[<slot-literal-or-var>] = …``,
# ``sys.modules.update``/``.setdefault`` (dict-literal, items-list, or ``**`` forms),
# and ``spec_from_file_location(<slot-literal-or-var>, …)``. Genuinely exotic
# forms (aliasing ``d = sys.modules; d[k] = …``, ``getattr``/``exec`` indirection)
# are out of static scope; the RUNTIME backstop is the W2-AC1 combined
# ``pytest hooks/ scripts/`` proof, which catches actual cross-suite breakage
# regardless of how the shadow was installed.
#
# Design (CLASS-SCOPED + TEARDOWN-SCOPED restore — Codex `019e73ab` P1-A + S184
# adversarial-verify P0): the restore MUST appear in the installing class's
# teardown surface (``tearDown`` / a method registered via ``self.addCleanup``) —
# NOT module-wide. A module-top ``from _lib import audit_emit`` (a CONSUMER import
# present in dozens of test files) is NOT in a teardown and does NOT count, so it
# cannot mask an un-restored loader. Two legitimate teardown restores are
# recognised: (1) **re-import canonical** (``importlib.import_module("_lib.audit_emit")``
# or ``from _lib import audit_emit`` inside the teardown), and (2)
# **save-and-restore** (the slot literal saved in a collection + ``sys.modules.get``
# + a VARIABLE-keyed ``sys.modules[var] = saved`` write inside the teardown — the
# ``test_federation`` pattern). ``mock.patch.dict(sys.modules, …)`` auto-restores
# and is neither an Assign nor a tracked install call, so it is never flagged.
# ---------------------------------------------------------------------------
_AUDIT_EMIT_SLOT = "_lib.audit_emit"
_SHADOW_MSG = (
    "installs a `_lib.audit_emit` shadow into the canonical import slot "
    "(sys.modules assignment / update / setdefault, or spec_from_file_location) "
    "but the installing class never RESTORES canonical `_lib.audit_emit` in its "
    "teardown (importlib.import_module(\"_lib.audit_emit\") / `from _lib import "
    "audit_emit`, or a save-and-restore of the slot). A LATER test's "
    "mock.patch(\"_lib.audit_emit.*\") will AttributeError in the combined "
    "hooks+scripts suite — the 19ab91d regression (PLAN-119-FOLLOWUP WS-2). "
    "Add a canonical re-import (or slot save-and-restore) in tearDown/addCleanup."
)


def _const_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_sys_modules(node: ast.AST) -> bool:
    """True only for ``sys.modules`` (``Attribute(value=Name('sys'), attr='modules')``)
    — not any arbitrary ``.modules`` attribute (Codex P1-A precision fix)."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "modules"
        and isinstance(node.value, ast.Name)
        and node.value.id == "sys"
    )


def _slot_names(tree: ast.AST) -> set:
    """Local names bound to the literal ``"_lib.audit_emit"`` (``slot = "_lib.audit_emit"``)
    so a variable-keyed install is still detected (Codex P1-A evasion fix)."""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and _const_str(n.value) == _AUDIT_EMIT_SLOT:
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def _arg_is_slot(node: ast.AST, names: set) -> bool:
    if _const_str(node) == _AUDIT_EMIT_SLOT:
        return True
    return isinstance(node, ast.Name) and node.id in names


def _subscript_key_is_slot(slice_node: ast.AST, names: set) -> bool:
    key = slice_node
    if isinstance(key, ast.Index):  # type: ignore[attr-defined]  # py<3.9
        key = key.value  # type: ignore[attr-defined]
    return _arg_is_slot(key, names)


def _call_refs_slot(call: ast.Call, names: set) -> bool:
    """True if ``call`` references the slot, covering the realistic ``dict.update`` /
    ``dict.setdefault`` install forms: ``setdefault(slot, …)``,
    ``update({slot: …})``, ``update([(slot, …)])`` (items form),
    ``update(**{slot: …})``, and a keyword value bound to the slot."""
    def _refs_in_collection_items(node: ast.AST) -> bool:
        # update([(slot, val), …]) / update({slot: …}) / a set/tuple of pairs
        if isinstance(node, ast.Dict):
            return any(k is not None and _arg_is_slot(k, names) for k in node.keys)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for elt in node.elts:
                if _arg_is_slot(elt, names):
                    return True
                if isinstance(elt, (ast.Tuple, ast.List)) and elt.elts and _arg_is_slot(elt.elts[0], names):
                    return True
        return False

    for a in call.args:
        if _arg_is_slot(a, names):  # setdefault("_lib.audit_emit", …)
            return True
        if _refs_in_collection_items(a):  # update({...}) / update([(...)])
            return True
    for kw in call.keywords:
        if _arg_is_slot(kw.value, names):
            return True
        if kw.arg is None and _refs_in_collection_items(kw.value):  # update(**{slot: …})
            return True
    return False


def _install_lines_in(scope: ast.AST, names: set) -> List[int]:
    """Linenos within ``scope`` that INSTALL a ``_lib.audit_emit`` shadow."""
    lines: List[int] = []
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if (isinstance(tgt, ast.Subscript) and _is_sys_modules(tgt.value)
                        and _subscript_key_is_slot(tgt.slice, names)):
                    lines.append(n.lineno)
        elif isinstance(n, ast.Call):
            fn = n.func
            fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if fname == "spec_from_file_location" and n.args and _arg_is_slot(n.args[0], names):
                lines.append(n.lineno)
            elif (fname in ("update", "setdefault") and isinstance(fn, ast.Attribute)
                    and _is_sys_modules(fn.value) and _call_refs_slot(n, names)):
                lines.append(n.lineno)
    return sorted(set(lines))


def _scope_reimports_slot(scope: ast.AST, names: set) -> bool:
    """True if ``scope`` re-imports the CANONICAL ``_lib.audit_emit``."""
    for n in ast.walk(scope):
        if isinstance(n, ast.Call):
            fn = n.func
            fname = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if fname == "import_module" and n.args and _arg_is_slot(n.args[0], names):
                return True
        if isinstance(n, ast.ImportFrom) and n.module == "_lib":
            if any(alias.name == "audit_emit" for alias in n.names):
                return True
    return False


def _teardown_method_names(cls: ast.ClassDef) -> set:
    names = {"tearDown", "tearDownClass", "asyncTearDown", "doCleanups"}
    for n in ast.walk(cls):
        if isinstance(n, ast.Call):
            fn = n.func
            if isinstance(fn, ast.Attribute) and fn.attr == "addCleanup" and n.args:
                a0 = n.args[0]
                if isinstance(a0, ast.Attribute):
                    names.add(a0.attr)
                elif isinstance(a0, ast.Name):
                    names.add(a0.id)
    return names


def _teardown_methods(cls: ast.ClassDef) -> List[ast.AST]:
    td_names = _teardown_method_names(cls)
    return [
        m for m in cls.body
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name in td_names
    ]


def _slot_in_collection(scope: ast.AST) -> bool:
    """True if the slot literal appears as a list/tuple/set/dict-key ELEMENT (the
    saved-keys collection) — distinct from the install subscript KEY."""
    for n in ast.walk(scope):
        if isinstance(n, (ast.List, ast.Tuple, ast.Set)):
            if any(_const_str(e) == _AUDIT_EMIT_SLOT for e in n.elts):
                return True
        if isinstance(n, ast.Dict):
            if any(_const_str(k) == _AUDIT_EMIT_SLOT for k in n.keys if k is not None):
                return True
    return False


def _is_sys_modules_get(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and _is_sys_modules(node.func.value)
    )


def _has_var_keyed_sysmodules_write(scope: ast.AST) -> bool:
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign):
            for tgt in n.targets:
                if isinstance(tgt, ast.Subscript) and _is_sys_modules(tgt.value):
                    key = tgt.slice
                    if isinstance(key, ast.Index):  # type: ignore[attr-defined]
                        key = key.value  # type: ignore[attr-defined]
                    if not isinstance(key, ast.Constant):  # variable key → restore loop
                        return True
    return False


def _class_restores_slot(cls: ast.ClassDef, names: set) -> bool:
    """A class restores canonical ``_lib.audit_emit`` IFF its teardown surface
    (``tearDown`` or an ``addCleanup`` target) EITHER re-imports canonical OR
    performs a save-and-restore of the slot. Restore must be in TEARDOWN — a
    module-top consumer import does not count."""
    tds = _teardown_methods(cls)
    if any(_scope_reimports_slot(td, names) for td in tds):
        return True
    # save-and-restore: slot saved in a collection + sys.modules.get (anywhere in
    # the class, e.g. setUp) + a variable-keyed sys.modules write in a teardown.
    if (_slot_in_collection(cls)
            and any(_is_sys_modules_get(n) for n in ast.walk(cls))
            and any(_has_var_keyed_sysmodules_write(td) for td in tds)):
        return True
    return False


def _module_functions(tree: ast.AST) -> List[ast.AST]:
    return [
        n for n in getattr(tree, "body", [])
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _calls_any(scope: ast.AST, fnames: set) -> bool:
    if not fnames:
        return False
    for n in ast.walk(scope):
        if isinstance(n, ast.Call):
            fn = n.func
            nm = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if nm in fnames:
                return True
    return False


def check_audit_emit_shadow_loaders(tree: ast.AST) -> List[Tuple[int, str]]:
    """Findings (lineno, msg) for a file that INSTALLS a ``_lib.audit_emit`` shadow
    without a TEARDOWN-scoped canonical restore IN THE INSTALLING CLASS.

    The install is bound to the class that owns it — either lexically (the install
    is inside the class body) or via a module-level installer helper the class
    CALLS (e.g. ``self.x = _load_staged_audit_emit()`` whose body assigns the
    slot). EACH installing class must restore: a safe restoring class elsewhere in
    the file does NOT cover an unrelated un-restoring installer (Codex `019e73ab`
    R2 nested-P0). Installs reachable from no class (module-body, or a helper no
    class calls) have no teardown to restore them and are flagged unconditionally."""
    if not isinstance(tree, ast.Module):
        return []
    names = _slot_names(tree)
    all_installs = set(_install_lines_in(tree, names))
    if not all_installs:
        return []
    # Module-level installer helpers: name -> install linenos inside the helper.
    helper_lines = {}
    for f in _module_functions(tree):
        hl = set(_install_lines_in(f, names))
        if hl:
            helper_lines[f.name] = hl
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    findings: List[Tuple[int, str]] = []
    attributed = set()
    for cls in classes:
        lex = set(_install_lines_in(cls, names))
        called = {h for h in helper_lines if _calls_any(cls, {h})}
        via_helper = set()
        for h in called:
            via_helper |= helper_lines[h]
        if not lex and not called:
            continue  # this class does not install a shadow
        attributed |= lex | via_helper
        if not _class_restores_slot(cls, names):
            report = sorted(lex) or sorted(via_helper) or [cls.lineno]
            for ln in report:
                findings.append((ln, _SHADOW_MSG))
    # Orphan installs: module-body, or a helper no class calls — no class teardown
    # can restore them, so a shadow set up there leaks. Flag unconditionally.
    for ln in sorted(all_installs - attributed):
        findings.append((ln, _SHADOW_MSG))
    # Dedup by lineno, stable ascending order.
    seen = set()
    out: List[Tuple[int, str]] = []
    for ln, msg in sorted(findings):
        if ln not in seen:
            seen.add(ln)
            out.append((ln, msg))
    return out


def check_file(path: Path) -> List[Tuple[int, str]]:
    findings: List[Tuple[int, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as e:  # fail-OPEN per file
        sys.stderr.write(f"  WARN: skipped unparsable {path}: {e}\n")
        return findings
    # Module-wide map of function/method defs (for resolving env-builder helpers).
    def_map = {
        n.name: n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    # Resolve each spawn's enclosing function (scope for env-var assignment trace).
    func_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    def _enclosing(call_node):
        best = tree
        for fn in func_nodes:
            for sub in ast.walk(fn):
                if sub is call_node:
                    best = fn
                    break
        return best

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_subprocess_spawn(node):
            continue
        env_kw = next((kw for kw in node.keywords if kw.arg == "env"), None)
        if env_kw is None:
            continue  # inherits the redirected parent env — safe
        scope = _enclosing(node)
        if not _env_is_safe(env_kw.value, scope, def_map):
            findings.append((
                node.lineno,
                "subprocess spawn with a minimal env= that omits os.environ — "
                "spread {**os.environ, ...} or use self.subprocess_env() so the "
                "child cannot resolve the LIVE audit dir (PLAN-119 WS-C)",
            ))

    # PLAN-119-FOLLOWUP WS-2 — _lib.audit_emit shadow-loader restore gate.
    findings.extend(check_audit_emit_shadow_loaders(tree))
    return findings


# PLAN-119 WS-D2 — carve-out allowlist for non-archived stale ``audit_emit.py``
# copies in the MAIN tree that are NOT import-pollution vectors:
#   - the ACTIVE PLAN-078 staging fixture (deliberately loaded as a
#     ``_lib.audit_emit`` shadow by test_check_agent_spawn / test_reality_ledger);
#   - the reality-ledger detector-6 DATA fixtures (SCANNED as files by the
#     detector, never imported as ``_lib.audit_emit``).
_STALE_AUDIT_EMIT_ALLOWLIST = (
    "plans/PLAN-078/staging/wave-1/audit_emit.py",
    "fixtures/reality-ledger/detector-6",
)
_RECENT_ACTION_MARKER = "output_scan_finding_suppressed"  # a post-PLAN-106 action


def check_stale_audit_emit_copies(repo_root: Path) -> List[str]:
    """PLAN-119 WS-D2 — flag any NON-archived, importable, STALE ``audit_emit.py``
    copy in the MAIN ``.claude/`` tree outside the carve-out allowlist.

    Such a copy (lacking a post-PLAN-106 action, not under ``_lib_archived/``,
    not in the allowlist) is a latent ``sys.path`` import-pollution vector — the
    recurring ``unknown action`` breadcrumb class. Archived copies hard-raise on
    import (PLAN-118 AC-B6) and are excluded; the ``npm/`` distribution bundle is
    excluded (not on any test sys.path; ``.npmignore``'d per PLAN-118 AC-B8).
    """
    findings: List[str] = []
    base = repo_root / ".claude"
    if not base.exists():
        return findings
    for path in sorted(base.rglob("audit_emit.py")):
        rel = str(path.relative_to(repo_root))
        if "_lib_archived" in rel or rel.startswith("npm/") or "/npm/" in rel:
            continue
        if any(allow in rel for allow in _STALE_AUDIT_EMIT_ALLOWLIST):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _RECENT_ACTION_MARKER not in text:
            findings.append(
                f"{rel}: non-archived importable STALE audit_emit.py (missing "
                f"{_RECENT_ACTION_MARKER!r}) outside the carve-out allowlist — a "
                f"sys.path import-pollution vector. Move it under _lib_archived/ "
                f"(hard-raise) or add it to the allowlist if it is inert data "
                f"(PLAN-119 WS-D2)."
            )
    return findings


def _testpaths_from_ini(repo_root: Path) -> List[Path]:
    """Derive the pytest collection roots from ``pytest.ini`` ``testpaths`` so the
    gate scans EVERY tree pytest collects (Codex P1: the static gate must not
    cover fewer roots than pytest — e.g. .claude/scripts/{replay,tier_policy_cli,
    tournament}/tests). Falls back to the three core roots if the ini is absent."""
    ini = repo_root / "pytest.ini"
    fallback = [Path(".claude/hooks/tests"), Path(".claude/scripts/tests"), Path("tests")]
    try:
        lines = ini.read_text(encoding="utf-8").splitlines()
    except OSError:
        return fallback
    roots: List[Path] = []
    in_block = False
    for raw in lines:
        s = raw.strip()
        if not in_block:
            if s.startswith("testpaths") and "=" in s:
                in_block = True
            continue
        # In the testpaths block: collect INDENTED, non-comment path lines.
        # A non-indented line (a col-0 comment or the next `key =`) ends it.
        if raw[:1].isspace() and s and not s.startswith("#"):
            roots.append(Path(s))
        elif s == "":
            continue  # tolerate a blank line inside the block
        else:
            break
    return roots or fallback


def main(argv: List[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or _testpaths_from_ini(Path("."))
    total = 0
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("test_*.py")):
            for line, msg in check_file(path):
                print(f"{path}:{line}: {msg}")
                total += 1
    # WS-D2 — stale audit_emit import-vector guard (repo-root relative).
    for msg in check_stale_audit_emit_copies(Path(".")):
        print(msg)
        total += 1
    if total:
        print(f"\nFAIL: {total} audit-isolation finding(s) (PLAN-119 WS-C/WS-D2).")
        return 1
    print("OK: no unsafe subprocess spawn + no stray stale audit_emit copy "
          "(PLAN-119 WS-C/WS-D2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
