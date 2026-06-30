#!/usr/bin/env python3
"""check-test-env-hygiene.py — PLAN-019 P1-QA-3.

TestEnvContext mandate enforcer for ``.claude/hooks/tests``,
``.claude/scripts/tests``, and ``tests/``.

Flags two classes of violations:

1. **Direct env mutation** — any ``os.environ[KEY] = VALUE`` /
   ``os.environ[KEY] += ...`` / ``del os.environ[KEY]`` at module level
   OR inside a test method for the tracked keys (``HOME``,
   ``CLAUDE_PROJECT_DIR``, anything starting with ``CEO_`` / ``CLAUDE_``).
   Tests MUST use ``TestEnvContext._env_snapshot`` plumbing or
   ``unittest.mock.patch.dict`` so teardown restores state.

2. **Bare ``unittest.TestCase`` inheritance** — every test class in the
   target trees MUST subclass ``TestEnvContext`` (directly or
   transitively) so sys.path / HOME / CEO_* are snapshot-restored
   between tests. Bare ``unittest.TestCase`` leaks.

An allowlist at ``.claude/scripts/test-env-hygiene-allowlist.yaml``
(simple line-based YAML-ish format) records the current violator
population so the check can be wired as an **advisory** step today and
later tightened to **hard-fail** once the allowlist is drained.

Exit codes:
  0 — no new violations (allowlisted + clean files).
  1 — at least one non-allowlisted violation.
  2 — usage / IO error.

CLI:
  check-test-env-hygiene.py                 — lint mode (default).
  check-test-env-hygiene.py --init          — regenerate allowlist from scratch.
  check-test-env-hygiene.py --verbose       — print per-file findings.
  check-test-env-hygiene.py --paths P1 P2   — override scan roots.

Stdlib only. No YAML parser — we use a line-oriented format (``# ``
comments, ``file: <rel>`` headers, ``- <violation-kind>`` entries)
parsed in ``_load_allowlist``.

Written for Python >= 3.9 per ADR-002 (no PEP 604 runtime, no match).
"""
from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Third canonical path root = repo root (discovered via this script's
# own location — ``.claude/scripts/check-test-env-hygiene.py`` is 2 dirs
# below repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_DEFAULT_SCAN_ROOTS = (
    ".claude/hooks/tests",
    ".claude/scripts/tests",
    ".claude/scripts/tier_policy_cli/tests",     # PLAN-045 F-03-06 (PLAN-076 fork (f) rename)
    ".claude/scripts/tournament/tests",      # PLAN-045 F-03-06
    ".claude/scripts/predict-budget/tests",  # PLAN-045 F-03-06
    "tests",
)

_ALLOWLIST_REL = ".claude/scripts/test-env-hygiene-allowlist.yaml"

# Env keys whose mutation is most leak-prone and therefore tracked.
# We also flag any ``CEO_*`` / ``CLAUDE_*`` prefix since those are
# framework-owned.
_TRACKED_KEYS = {"HOME", "CLAUDE_PROJECT_DIR"}
_TRACKED_PREFIXES = ("CEO_", "CLAUDE_")

# Violation kinds emitted into the allowlist entries.
VIOL_ENV_WRITE = "env-write"      # os.environ[KEY] = ...
VIOL_ENV_DEL = "env-del"          # del os.environ[KEY]
VIOL_BARE_TESTCASE = "bare-testcase"  # class Foo(unittest.TestCase)

_ALL_KINDS = frozenset({VIOL_ENV_WRITE, VIOL_ENV_DEL, VIOL_BARE_TESTCASE})


# ---------------------------------------------------------------------------
# AST visitors
# ---------------------------------------------------------------------------


class _HygieneVisitor(ast.NodeVisitor):
    """Collect hygiene violations for a single file."""

    def __init__(self, rel_path: str) -> None:
        self.rel_path = rel_path
        # list of (kind, lineno, detail)
        self.violations: List[Tuple[str, int, str]] = []

    # -- os.environ assignments -----------------------------------------

    def _env_key_from_subscript(self, node: ast.Subscript) -> Optional[str]:
        """Return the env key if ``node`` is ``os.environ[<constant>]``.

        Supports both ast.Index (Py3.8-legacy) and bare Constant (Py3.9+).
        Returns None for non-constant subscripts (e.g.
        ``os.environ[some_var]``) — those are not flagged because we
        can't know statically which key is touched.
        """
        target = node.value
        if not (
            isinstance(target, ast.Attribute)
            and target.attr == "environ"
            and isinstance(target.value, ast.Name)
            and target.value.id == "os"
        ):
            return None
        # Unwrap Index for Py3.8 compat (harmless on 3.9+).
        slice_node = node.slice
        if isinstance(slice_node, ast.Index):  # pragma: no cover
            slice_node = slice_node.value  # type: ignore[attr-defined]
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            return slice_node.value
        return None

    def _is_tracked(self, key: Optional[str]) -> bool:
        if key is None:
            # Non-constant keys: flag conservatively (any dynamic write
            # to os.environ is a potential leak).
            return True
        if key in _TRACKED_KEYS:
            return True
        return any(key.startswith(p) for p in _TRACKED_PREFIXES)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: D401
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                key = self._env_key_from_subscript(target)
                if key is not None or self._contains_environ_subscript(target):
                    if self._is_tracked(key):
                        self.violations.append(
                            (VIOL_ENV_WRITE, node.lineno, f"os.environ[{key!r}]")
                        )
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if isinstance(node.target, ast.Subscript):
            key = self._env_key_from_subscript(node.target)
            if key is not None or self._contains_environ_subscript(node.target):
                if self._is_tracked(key):
                    self.violations.append(
                        (VIOL_ENV_WRITE, node.lineno, f"os.environ[{key!r}] +=/...")
                    )
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        for t in node.targets:
            if isinstance(t, ast.Subscript):
                key = self._env_key_from_subscript(t)
                if key is not None or self._contains_environ_subscript(t):
                    if self._is_tracked(key):
                        self.violations.append(
                            (VIOL_ENV_DEL, node.lineno, f"del os.environ[{key!r}]")
                        )
        self.generic_visit(node)

    def _contains_environ_subscript(self, node: ast.Subscript) -> bool:
        """True if the subscript is against os.environ (regardless of key shape)."""
        target = node.value
        return (
            isinstance(target, ast.Attribute)
            and target.attr == "environ"
            and isinstance(target.value, ast.Name)
            and target.value.id == "os"
        )

    # -- class inheritance ---------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # Only test classes (named Test*) are interesting. Helper mixins
        # like ``_SharedMixin(unittest.TestCase)`` are uncommon in this
        # tree; if they appear they'll get flagged and can be allowlisted.
        if self._is_bare_unittest_testcase(node.bases):
            self.violations.append(
                (
                    VIOL_BARE_TESTCASE,
                    node.lineno,
                    f"class {node.name}(unittest.TestCase)",
                )
            )
        self.generic_visit(node)

    def _is_bare_unittest_testcase(self, bases: List[ast.expr]) -> bool:
        """True iff class has exactly one base and it's unittest.TestCase / TestCase.

        We don't flag multi-base classes (too easy to have a diamond with
        TestEnvContext) nor classes whose base names we can't resolve
        statically.
        """
        if len(bases) != 1:
            return False
        b = bases[0]
        if isinstance(b, ast.Attribute) and b.attr == "TestCase":
            if isinstance(b.value, ast.Name) and b.value.id == "unittest":
                return True
        if isinstance(b, ast.Name) and b.id == "TestCase":
            # ``from unittest import TestCase; class Foo(TestCase)`` —
            # also a bare leak.
            return True
        return False


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------


def scan_file(path: Path, repo_root: Path) -> List[Tuple[str, int, str]]:
    """Return list of (kind, lineno, detail) for a single file.

    On parse error returns an empty list and prints a warning. We
    intentionally fail-soft — the purpose of the check is not to gate
    on syntax errors (other CI steps catch those).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        print(f"  WARN: cannot read {path}: {exc}", file=sys.stderr)
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - defensive
        print(f"  WARN: syntax error in {path}: {exc}", file=sys.stderr)
        return []

    rel = str(path.relative_to(repo_root)) if path.is_absolute() else str(path)
    v = _HygieneVisitor(rel)
    v.visit(tree)
    return v.violations


def scan_roots(
    roots: Iterable[str], repo_root: Path
) -> Dict[str, List[Tuple[str, int, str]]]:
    """Return mapping ``relpath -> list[violations]`` (only files with >=1 viol).

    We skip files whose name starts with ``testing.py`` (the shim) and
    ``_lib/testing.py`` (canonical source of TestEnvContext).
    """
    results: Dict[str, List[Tuple[str, int, str]]] = {}
    for root in roots:
        root_abs = (repo_root / root).resolve()
        if not root_abs.exists():
            continue
        for py in sorted(root_abs.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            rel = str(py.relative_to(repo_root))
            # Skip the canonical shim and anything named exactly testing.py.
            if rel.endswith("_lib/testing.py") or py.name == "testing.py":
                continue
            violations = scan_file(py, repo_root)
            if violations:
                results[rel] = violations
    return results


# ---------------------------------------------------------------------------
# Allowlist (line-oriented YAML-ish format)
# ---------------------------------------------------------------------------

# Format (stdlib only — no YAML dep):
#
#   # Header comments start with '#'
#   # Blank lines are allowed.
#
#   file: <relpath>
#     - env-write
#     - bare-testcase
#
# Each ``file:`` line starts a new section. Entries under it list the
# violation kinds pre-approved for that file. Unknown kinds are
# rejected (exit 2). Files not mentioned are treated as "clean" —
# any violation in them is a new violator.


def _load_allowlist(path: Path) -> Dict[str, Set[str]]:
    """Parse the allowlist file. Returns ``{rel: {kind, ...}}``.

    Raises ``ValueError`` on malformed content.
    """
    if not path.exists():
        return {}
    out: Dict[str, Set[str]] = {}
    current: Optional[str] = None
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("file:"):
            rel = line[len("file:"):].strip()
            if not rel:
                raise ValueError(f"{path}:{lineno}: empty file: header")
            current = rel
            out.setdefault(current, set())
            continue
        if line.lstrip().startswith("-"):
            if current is None:
                raise ValueError(
                    f"{path}:{lineno}: entry '{line}' before any file: header"
                )
            kind = line.lstrip()[1:].strip()
            if kind not in _ALL_KINDS:
                raise ValueError(
                    f"{path}:{lineno}: unknown violation kind {kind!r} "
                    f"(expected one of {sorted(_ALL_KINDS)})"
                )
            out[current].add(kind)
            continue
        raise ValueError(f"{path}:{lineno}: unrecognized line: {line!r}")
    return out


def _write_allowlist(
    path: Path, entries: Dict[str, Set[str]], header_lines: Optional[List[str]] = None
) -> None:
    """Write entries in a stable, human-reviewable order.

    Files sorted lexicographically; kinds sorted alphabetically within
    each file section.
    """
    lines: List[str] = []
    if header_lines:
        lines.extend(header_lines)
        if lines and lines[-1] != "":
            lines.append("")
    for rel in sorted(entries):
        kinds = sorted(entries[rel])
        if not kinds:
            continue
        lines.append(f"file: {rel}")
        for k in kinds:
            lines.append(f"  - {k}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _default_header() -> List[str]:
    return [
        "# test-env-hygiene-allowlist.yaml — PLAN-019 P1-QA-3",
        "#",
        "# Pre-approved violators of the TestEnvContext mandate. Generated",
        "# by `check-test-env-hygiene.py --init` and then hand-tended as",
        "# violators are drained. New violations in unlisted files fail",
        "# the check.",
        "#",
        "# Violation kinds:",
        f"#   - {VIOL_ENV_WRITE}       (os.environ[KEY] = ...)",
        f"#   - {VIOL_ENV_DEL}         (del os.environ[KEY])",
        f"#   - {VIOL_BARE_TESTCASE}   (class Foo(unittest.TestCase))",
        "#",
        "# Format (line-oriented; stdlib-parseable, NOT real YAML):",
        "#   file: <relpath>",
        "#     - <kind>",
        "#     - <kind>",
        "",
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_new_violations(
    scan_results: Dict[str, List[Tuple[str, int, str]]],
    allowlist: Dict[str, Set[str]],
) -> Dict[str, List[Tuple[str, int, str]]]:
    """Return violations that are NOT allowlisted.

    A file with N violations of kind K is considered allowlisted iff
    kind K is listed for that file. If a file is in the allowlist with
    kinds {A} but also emits a violation of kind B, that B entry is
    reported as new.
    """
    new: Dict[str, List[Tuple[str, int, str]]] = {}
    for rel, vs in scan_results.items():
        allowed = allowlist.get(rel, set())
        unlisted = [(k, ln, det) for (k, ln, det) in vs if k not in allowed]
        if unlisted:
            new[rel] = unlisted
    return new


def _reduce_to_kinds(
    scan_results: Dict[str, List[Tuple[str, int, str]]]
) -> Dict[str, Set[str]]:
    """Collapse per-line violations to ``{rel: {kind, ...}}`` for allowlist I/O."""
    out: Dict[str, Set[str]] = {}
    for rel, vs in scan_results.items():
        out[rel] = {k for (k, _ln, _det) in vs}
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — scan test suites for env-var leaks outside TestEnvContext."""
    ap = argparse.ArgumentParser(
        description="TestEnvContext mandate enforcer (PLAN-019 P1-QA-3)."
    )
    ap.add_argument(
        "--init",
        action="store_true",
        help="Regenerate the allowlist from current scan state.",
    )
    ap.add_argument(
        "--verbose",
        action="store_true",
        help="Print every flagged file with line numbers.",
    )
    ap.add_argument(
        "--paths",
        nargs="*",
        default=None,
        help="Scan roots (relative to repo root). Default: .claude/hooks/tests, "
        ".claude/scripts/tests, tests",
    )
    ap.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (for tests).",
    )
    ap.add_argument(
        "--allowlist",
        default=None,
        help=f"Override allowlist path (default: {_ALLOWLIST_REL}).",
    )
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else _REPO_ROOT
    allowlist_path = (
        Path(args.allowlist).resolve()
        if args.allowlist
        else (repo_root / _ALLOWLIST_REL)
    )
    scan_roots_list = args.paths if args.paths else list(_DEFAULT_SCAN_ROOTS)

    scan = scan_roots(scan_roots_list, repo_root)

    if args.init:
        reduced = _reduce_to_kinds(scan)
        _write_allowlist(allowlist_path, reduced, header_lines=_default_header())
        total_files = len(reduced)
        total_violations = sum(len(v) for v in scan.values())
        print(
            f"OK: wrote {allowlist_path.relative_to(repo_root) if allowlist_path.is_absolute() else allowlist_path} "
            f"({total_files} files, {total_violations} violation occurrences)."
        )
        return 0

    try:
        allowlist = _load_allowlist(allowlist_path)
    except ValueError as exc:
        print(f"FAIL: malformed allowlist: {exc}", file=sys.stderr)
        return 2

    new = _find_new_violations(scan, allowlist)

    # Emit summary.
    total_scanned_files = sum(1 for _ in scan)
    total_allowlisted_files = sum(1 for rel in scan if rel in allowlist)
    total_new_violations = sum(len(v) for v in new.values())

    if args.verbose or new:
        print("=== test-env-hygiene scan ===")
        print(f"  scan roots: {', '.join(scan_roots_list)}")
        print(f"  allowlist:  {allowlist_path}")
        print(
            f"  files with violations: {total_scanned_files} "
            f"(allowlisted: {total_allowlisted_files})"
        )
        print(f"  NEW violations: {total_new_violations}")

    if args.verbose:
        for rel in sorted(scan):
            vs = scan[rel]
            tag = "ALLOW" if rel in allowlist else "VIOL"
            print(f"  [{tag}] {rel}")
            for (k, ln, det) in vs:
                print(f"      L{ln}: {k} — {det}")

    if new:
        print("")
        print("FAIL: new test-env hygiene violations (not in allowlist):")
        for rel in sorted(new):
            for (k, ln, det) in new[rel]:
                print(f"  {rel}:{ln}: {k} — {det}")
        print("")
        print("Fix options:")
        print("  1. Subclass TestEnvContext instead of unittest.TestCase.")
        print("  2. Use the _env_snapshot/_restore pattern or mock.patch.dict.")
        print("  3. (Last resort) add to the allowlist in")
        print(f"     {_ALLOWLIST_REL}")
        return 1

    print(
        f"OK: test-env hygiene clean "
        f"({total_scanned_files} flagged files, all allowlisted)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
