#!/usr/bin/env python3
"""check-stdlib-only.py — ADR-126 §Part 6 core stdlib-only enforcement.

AST-parses every `.py` file under `.claude/hooks/` + `.claude/scripts/` +
`SPEC/python/` (if any). Asserts every `import X` resolves to:

  - Python stdlib (per `sys.stdlib_module_names` on Python 3.10+, or
    hardcoded list for 3.9 fallback), OR
  - A sibling-module name (same package as the importing file, including
    intra-package imports like `from handlers import ...` from
    `dispatch.py` in the same directory), OR
  - A name in the local-modules allowlist (deliberate framework
    exceptions documented in `_LOCAL_PACKAGE_ALLOWLIST`).

Default mode is ADVISORY (exit 0 with violation count printed). Use
`--strict` to fail-CLOSED in CI. Fail-CLOSED enforcement is gated for
PLAN-097-FOLLOWUP after baseline cleanup.

Stdlib-only (ADR-002, recursively). Python 3.9+ runtime supported.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent

_SCAN_ROOTS = (
    _REPO_ROOT / ".claude" / "hooks",
    _REPO_ROOT / ".claude" / "scripts",
    _REPO_ROOT / "SPEC" / "python",
)

# Additional roots scanned ONLY to populate `global_names` (so framework
# scripts can cross-import from these locations without false positives).
# We do NOT validate files under these roots themselves.
_GLOBAL_NAME_ROOTS = (
    _REPO_ROOT / ".claude" / "swarm",
    _REPO_ROOT / ".claude" / "detectors",
    _REPO_ROOT / ".claude" / "rag",
)

# Hardcoded stdlib list for Python 3.9 (sys.stdlib_module_names is 3.10+).
_STDLIB_FALLBACK = frozenset(
    [
        "__future__", "_ast", "_thread", "abc", "aifc", "antigravity", "argparse",
        "array", "ast", "asynchat", "asyncio", "asyncore", "atexit", "audioop",
        "base64", "bdb", "binascii", "binhex", "bisect", "builtins", "bz2",
        "cProfile", "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code",
        "codecs", "codeop", "collections", "colorsys", "compileall", "concurrent",
        "configparser", "contextlib", "contextvars", "copy", "copyreg", "crypt",
        "csv", "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
        "difflib", "dis", "distutils", "doctest", "email", "encodings", "ensurepip",
        "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "fractions", "ftplib", "functools", "gc", "genericpath", "getopt", "getpass",
        "gettext", "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr", "imp", "importlib",
        "inspect", "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
        "linecache", "locale", "logging", "lzma", "mailbox", "mailcap", "marshal",
        "math", "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt",
        "multiprocessing", "netrc", "nis", "nntplib", "ntpath", "numbers",
        "opcode", "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb",
        "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
        "poplib", "posix", "posixpath", "pprint", "profile", "pstats", "pty",
        "pwd", "py_compile", "pyclbr", "pydoc", "pydoc_data", "pyexpat", "queue",
        "quopri", "random", "re", "readline", "reprlib", "resource", "rlcompleter",
        "runpy", "sched", "secrets", "select", "selectors", "shelve", "shlex",
        "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr", "socket",
        "socketserver", "spwd", "sqlite3", "sre_compile", "sre_constants",
        "sre_parse", "ssl", "stat", "statistics", "string", "stringprep", "struct",
        "subprocess", "sunau", "symbol", "symtable", "sys", "sysconfig", "syslog",
        "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
        "textwrap", "this", "threading", "time", "timeit", "tkinter", "token",
        "tokenize", "tomllib", "trace", "traceback", "tracemalloc", "tty",
        "turtle", "turtledemo", "types", "typing", "unicodedata", "unittest",
        "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref", "webbrowser",
        "winreg", "winsound", "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
        "zipfile", "zipimport", "zlib", "zoneinfo",
    ]
)

# Deliberate non-stdlib usage exceptions — these are governance-permitted
# integration points (NOT a general allowance to add new non-stdlib deps).
# Each entry has a tracked-ADR justification.
_LOCAL_PACKAGE_ALLOWLIST = frozenset(
    [
        # ADR-040 live adapter — Anthropic SDK at the live-call site only.
        "anthropic",
        # PLAN-073 / ADR-058 — YAML skill benchmark fixtures.
        "yaml",
        # PLAN-080 §MCP code-nav bridge — tree-sitter for cross-language AST.
        "tree_sitter",
    ]
)

# File-scoped non-stdlib exceptions (PLAN-120 E10-F1). Unlike the package
# allowlist above (which permits a module ANYWHERE), these permit a specific
# non-stdlib import ONLY in the named file. Each file is a test-harness or
# build-time artifact that is NEVER on an adopter runtime / hook path — the
# install.sh structural assertion (PLAN-120 AC4.4) confirms neither reaches the
# adopter runtime. Keeping the entries here (rather than the broad allowlist)
# preserves the genuinely-stdlib-only guarantee for the production hot path AND
# keeps the SBOM §A attestation accurate (SBOM.md discloses both).
_FILE_SCOPED_EXCEPTIONS = {
    # PLAN-119 WS-A pytest-fixture audit-isolation module. Lives under _lib/ so
    # the three conftests can import it by a stable path; imported ONLY in a
    # pytest collection/run context; excluded from the adopter runtime.
    ".claude/hooks/_lib/test_isolation.py": frozenset({"pytest"}),
    # setuptools is the canonical build backend; setup.py is a packaging file,
    # never a runtime or hook path.
    ".claude/scripts/tier_policy_cli/setup.py": frozenset({"setuptools"}),
}


def _is_stdlib_module(name: str) -> bool:
    if hasattr(sys, "stdlib_module_names"):
        return name in sys.stdlib_module_names  # type: ignore[attr-defined]
    return name in _STDLIB_FALLBACK


def _build_local_module_index() -> Tuple[Dict[Path, Set[str]], Set[str]]:
    """Build two indices:

    - Per-directory sibling set (intra-package resolution).
    - Global module-name set across all scan roots (cross-package framework
      imports via sys.path injection — e.g., scripts importing lib code from
      `.claude/hooks/_lib/`).

    A `name` is treated as local when:
      - There is a `<name>.py` file in the same directory as the importing file,
      - There is a `<name>/` subdir in the same directory containing `__init__.py`,
      - There is a `<name>/` subdir in the same directory containing any `.py`
        (implicit-namespace-package callsites used by mini-modules under
        `.claude/scripts/`).
      - There is a `<name>.py` file ANYWHERE under scan roots (cross-package
        framework import via sys.path injection; covers patterns like
        `from check_agent_spawn import ...` from `.claude/scripts/mcp-server/`).
    """
    index: Dict[Path, Set[str]] = {}
    global_names: Set[str] = set()
    # Populate global_names from auxiliary roots (no per-dir index needed).
    for aux in _GLOBAL_NAME_ROOTS:
        if not aux.exists():
            continue
        for py in aux.rglob("*.py"):
            rel = py.relative_to(_REPO_ROOT)
            if "fixtures" in rel.parts or py.name == "__init__.py":
                continue
            global_names.add(py.stem)
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        for entry in root.rglob("*"):
            if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
                rel = entry.relative_to(_REPO_ROOT)
                # Skip fixtures dirs — they intentionally have non-stdlib imports.
                if "fixtures" in rel.parts or "fixtures-expansion-recipe" in rel.parts:
                    continue
                global_names.add(entry.stem)
            if not entry.is_dir():
                continue
            # If this dir contains any .py file, it can be imported as a package
            # — register its NAME (not just children's names) globally.
            has_own_py = False
            try:
                for sub in entry.iterdir():
                    if sub.is_file() and sub.suffix == ".py":
                        has_own_py = True
                        break
            except OSError:
                continue
            if has_own_py:
                global_names.add(entry.name)
            siblings: Set[str] = set()
            try:
                children = list(entry.iterdir())
            except OSError:
                continue
            for child in children:
                if child.is_file() and child.suffix == ".py":
                    if child.name == "__init__.py":
                        continue
                    siblings.add(child.stem)
                elif child.is_dir():
                    has_py = False
                    try:
                        for sub in child.iterdir():
                            if sub.is_file() and sub.suffix == ".py":
                                has_py = True
                                break
                    except OSError:
                        continue
                    if has_py:
                        siblings.add(child.name)
            if siblings:
                index[entry] = siblings
                global_names.update(siblings)
    return index, global_names


def _is_internal_lib(
    name: str,
    file_path: Path,
    local_index: Dict[Path, Set[str]],
    global_names: Set[str],
) -> bool:
    """`name` is an internal module if it resolves within the same package as
    the importing file, OR explicit `_lib.`/`_lib`/`_constants`/`_types`
    relative-package shorthand, OR matches the global module-name set
    (cross-package framework import via sys.path injection).
    """
    if name.startswith("_lib.") or name == "_lib":
        return True
    if name in {"_constants", "_types", "_agent_frontmatter"}:
        return True
    parent = file_path.parent
    siblings = local_index.get(parent, set())
    if name in siblings:
        return True
    for up in (1, 2, 3):
        try:
            ancestor = file_path.parents[up]
        except IndexError:
            break
        anc_sibs = local_index.get(ancestor, set())
        if name in anc_sibs:
            return True
    # Cross-package framework import — any .py basename under scan roots.
    if name in global_names:
        return True
    return False


def _is_governance_exception(name: str) -> bool:
    """ADR-tracked non-stdlib exceptions (see `_LOCAL_PACKAGE_ALLOWLIST`)."""
    return name in _LOCAL_PACKAGE_ALLOWLIST


def _collect_imports(text: str, file_path: Path) -> List[Tuple[int, str]]:
    """Return list of (lineno, top-level module name) from a file's imports."""
    out: List[Tuple[int, str]] = []
    try:
        tree = ast.parse(text, filename=str(file_path))
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                out.append((node.lineno, top))
        elif isinstance(node, ast.ImportFrom):
            if (node.level or 0) > 0:
                # relative import — same package, always allowed
                continue
            if node.module:
                top = node.module.split(".")[0]
                out.append((node.lineno, top))
    return out


def validate_file(
    file_path: Path,
    local_index: Dict[Path, Set[str]],
    global_names: Set[str],
) -> List[str]:
    """Return list of violation strings for a single file."""
    violations: List[str] = []
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations
    rel = file_path.relative_to(_REPO_ROOT)
    file_scoped = _FILE_SCOPED_EXCEPTIONS.get(rel.as_posix(), frozenset())
    for lineno, top in _collect_imports(text, file_path):
        if _is_stdlib_module(top):
            continue
        if _is_internal_lib(top, file_path, local_index, global_names):
            continue
        if _is_governance_exception(top):
            continue
        if top in file_scoped:  # PLAN-120 E10-F1 — documented test/build-only import
            continue
        violations.append(f"{rel}:{lineno} imports non-stdlib '{top}'")
    return violations


def _emit_audit(violations: List[str]) -> None:
    """Emit stdlib_violation audit event (fail-open on hook errors)."""
    try:
        hooks_dir = _REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib import audit_emit  # type: ignore
        if hasattr(audit_emit, "emit_generic"):
            audit_emit.emit_generic(
                "stdlib_violation",
                violation_count=len(violations),
            )
    except Exception:
        pass  # fail-open per framework discipline


def _enumerate_files() -> List[Path]:
    files: List[Path] = []
    for root in _SCAN_ROOTS:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            rel = py.relative_to(_REPO_ROOT)
            parts = rel.parts
            if any(p in {"tests", ".pytest_cache", "__pycache__", "venv", ".venv"} for p in parts):
                continue
            if any(p.startswith("worktree") or p == "worktrees" for p in parts):
                continue
            if ".claude/sidecars/" in rel.as_posix():
                continue
            # Skip test/repo-profile fixtures (deliberate non-stdlib payloads).
            if "fixtures" in parts:
                continue
            files.append(py)
    return sorted(files)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce stdlib-only invariant for .claude/hooks/ + .claude/scripts/ + SPEC/python/ (ADR-126 §Part 6)"
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report on stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail-CLOSED on any violation (PLAN-097-FOLLOWUP target; advisory by default)",
    )
    args = parser.parse_args(argv)

    files = _enumerate_files()
    local_index, global_names = _build_local_module_index()
    all_violations: List[str] = []
    per_file: dict = {}
    for f in files:
        v = validate_file(f, local_index, global_names)
        if v:
            per_file[str(f.relative_to(_REPO_ROOT))] = v
            all_violations.extend(v)

    if all_violations:
        _emit_audit(all_violations)

    if args.json:
        print(json.dumps({"files_scanned": len(files), "violations": per_file}, indent=2, sort_keys=True))
    else:
        if all_violations:
            sys.stderr.write(
                f"check-stdlib-only: {len(all_violations)} violation(s) in {len(per_file)} file(s)"
                f" {'(STRICT — fail-CLOSED)' if args.strict else '(advisory — exit 0; use --strict for CI gate)'}\n"
            )
            for v in all_violations:
                sys.stderr.write(f"  {v}\n")
        else:
            print(f"check-stdlib-only: {len(files)} file(s) OK")

    if all_violations and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
