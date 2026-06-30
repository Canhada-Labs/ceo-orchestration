#!/usr/bin/env python3
"""C1 crypto / stdlib-ssl-mvp sidecar boundary test.

Enforces a SUBSET of the ADR-126 §Part 5 triad + PLAN-099-specific
checks (Codex R2 iter-2 P2#1 fold — honest scope description; full
§Part 5 triad workflow-pattern validation is reserved for
PLAN-099-FOLLOWUP Wave A.4):

1. **ADR-126 §Part 5 step 2a** — no core path imports any entry in
   `manifest.json[isolation.import_roots]` (here: `cryptography`).
   The C1 sidecar owns this namespace; until PLAN-099-FOLLOWUP ships
   the real `cryptography-mvp` sidecar, NOTHING in
   `.claude/hooks/` or `.claude/scripts/` legitimately imports it.
2. **PLAN-099 §Part 6 SBOM invariant** — the federation Python package
   itself imports ONLY stdlib + governance helpers (`_lib.audit_emit`,
   `_lib.gpg_verify`, `_lib.sentinel_signers`, `_lib.redact`,
   `_lib.pii_patterns`). Anything else in `_lib/federation/**/*.py` is
   a boundary breach.
3. **PLAN-099 workflow auto-start** — no CI workflow auto-deploys the
   federation server without referencing the Owner-GPG enable sentinel.
   This is a PLAN-099-specific check, NOT the full ADR-126 §Part 5 2b
   workflow-pattern triad (which validates the manifest's
   `allowed_workflow_invocation_patterns` regex set).
4. **PLAN-099 AC18 import-graph denial** — autonomous-loop code paths
   must NOT import `federation.*` / `_lib.federation.*`. Federation
   calls require Owner ack, not autonomous dispatch.

The remaining ADR-126 §Part 5 surfaces (`core_paths_allowlisted_workflow_invokers`
allowlist enforcement + `allowed_workflow_invocation_patterns` regex
validation against actual workflow invocations) are reserved for
PLAN-099-FOLLOWUP Wave A.4 when the real `cryptography-mvp` sidecar
ships and starts to need CI invocation. The MVP `stdlib-ssl-mvp`
sidecar has NO CI invocation (boundary_test.py is the only CI
entrypoint, and it self-validates).

Stdlib-only. Exits 0 on clean boundary, 1 on any violation.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent.parent
_MANIFEST = _HERE / "manifest.json"

FEDERATION_DIR = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "federation"
WORKFLOWS_DIR = _REPO_ROOT / ".github" / "workflows"


# --- Standard ADR-126 §Part 5 — sidecar isolation -----------------------------


def _load_manifest() -> dict:
    with _MANIFEST.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _scan_python_imports_for_roots(
    scan_root: Path,
    import_roots: List[str],
) -> List[Tuple[Path, int, str]]:
    """Find imports of any ``import_roots`` entry under ``scan_root``."""
    violations: List[Tuple[Path, int, str]] = []
    if not scan_root.exists():
        return violations
    roots_set = set(import_roots)
    for py_path in sorted(scan_root.rglob("*.py")):
        try:
            text = py_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text, filename=str(py_path))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".", 1)[0]
                    if top in roots_set:
                        violations.append(
                            (py_path, getattr(node, "lineno", 0), alias.name)
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".", 1)[0]
                    if top in roots_set:
                        violations.append(
                            (py_path, getattr(node, "lineno", 0), node.module)
                        )
    return violations


def check_import_roots_blocked() -> List[str]:
    """ADR-126 §Part 5 standard check — core paths must NOT import
    any entry in `manifest.json[isolation.import_roots]`."""
    failures: List[str] = []
    manifest = _load_manifest()
    iso = manifest.get("isolation", {})
    import_roots = iso.get("import_roots", [])
    blocked = iso.get("core_paths_blocked", [])
    for path_rel in blocked:
        scan_root = _REPO_ROOT / path_rel
        for viol_path, lineno, mod in _scan_python_imports_for_roots(
            scan_root, import_roots,
        ):
            failures.append(
                "{0}:{1}: imports {2!r} (in import_roots; sidecar-owned)".format(
                    viol_path.relative_to(_REPO_ROOT), lineno, mod,
                )
            )
    return failures


# --- Stdlib-only invariant for federation/*.py (ADR-129 §Part 1 + §Part 6) -----


ALLOWED_STDLIB = frozenset({
    "ssl", "hmac", "hashlib", "secrets",
    "http", "http.server", "http.client", "urllib", "urllib.parse",
    "ipaddress", "socket",
    "threading", "collections", "queue",
    "time", "datetime",
    "pathlib", "os", "io",
    "json", "re", "sys", "typing", "dataclasses", "enum",
    "importlib", "importlib.util",
    # ADR-126: federation core uses subprocess bridge to call C1 sidecar;
    # shutil+tempfile are helpers for the subprocess cert-parse path.
    "shutil", "subprocess", "tempfile",
    "__future__",
})

ALLOWED_INTERNAL = frozenset({
    "_lib", "_lib.audit_emit", "_lib.gpg_verify",
    "_lib.sentinel_signers", "_lib.redact", "_lib.pii_patterns",
})

ALLOWED_PACKAGE_PREFIXES = (
    "identity", "client", "server", "audit_chain", "replay",
    "handlers",   # server.py lazy-imports federation handler modules
    "scopes",     # server.py lazy-imports federation scope module
    "federation", # identity.py: top-level namespace fallback for cert_inspector
)


def _module_root(name: str) -> str:
    return name.split(".", 1)[0] if name else ""


def _scan_module_imports(path: Path) -> Set[Tuple[str, int]]:
    out: Set[Tuple[str, int]] = set()
    try:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
    except (OSError, SyntaxError):
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add((alias.name, getattr(node, "lineno", 0)))
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            mod = node.module or ""
            out.add((mod, getattr(node, "lineno", 0)))
    return out


def _is_allowed_import(name: str) -> bool:
    if not name:
        return True
    if name in ALLOWED_INTERNAL or _module_root(name) in {"_lib"}:
        return True
    if name.startswith(ALLOWED_PACKAGE_PREFIXES):
        return True
    root = _module_root(name)
    return root in ALLOWED_STDLIB or name in ALLOWED_STDLIB


def check_federation_pkg_stdlib_only() -> List[str]:
    """Federation Python package must only import stdlib + governance helpers."""
    failures: List[str] = []
    if not FEDERATION_DIR.exists():
        return failures
    for py_file in sorted(FEDERATION_DIR.rglob("*.py")):
        for module, lineno in _scan_module_imports(py_file):
            if not _is_allowed_import(module):
                failures.append(
                    "{0}:{1}: disallowed import {2!r}".format(
                        py_file.relative_to(_REPO_ROOT), lineno, module,
                    )
                )
    return failures


# --- Workflow autostart check (no CI auto-deploys federation w/o sentinel) ----


def check_workflows_no_autostart() -> List[str]:
    failures: List[str] = []
    if not WORKFLOWS_DIR.exists():
        return failures
    suspicious = re.compile(
        r"(CEO_FEDERATION_ENABLED\s*[:=]\s*[\"']?1|federation\.server|federation/server)",
        flags=re.IGNORECASE,
    )
    for wf in sorted(WORKFLOWS_DIR.glob("*.yml")):
        try:
            txt = wf.read_text(encoding="utf-8")
        except OSError:
            continue
        if suspicious.search(txt):
            if "enabled.md.asc" not in txt:
                failures.append(
                    "{0}: federation invocation without sentinel reference".format(
                        wf.relative_to(_REPO_ROOT),
                    )
                )
    return failures


# --- AC18 — autonomous-loop must not import federation -----------------------


_AUTONOMOUS_LOOP_FILES = (
    "swarm.py", "swarm_runner.py", "swarm_dispatch.py",
    "autonomous_loop.py", "autonomous-loop.py",
)


def _imports_federation_via_ast(py_file: Path) -> List[Tuple[str, int]]:
    matches: List[Tuple[str, int]] = []
    try:
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_file))
    except (OSError, SyntaxError):
        return matches
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_federation_import(alias.name):
                    matches.append((alias.name, getattr(node, "lineno", 0)))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if _is_federation_import(mod):
                matches.append((mod, getattr(node, "lineno", 0)))
    return matches


def _is_federation_import(name: str) -> bool:
    if not name:
        return False
    parts = name.split(".")
    if parts and parts[0] == "federation":
        return True
    if len(parts) >= 2 and parts[0] == "_lib" and parts[1] == "federation":
        return True
    return False


def check_autonomous_loop_no_federation() -> List[str]:
    failures: List[str] = []
    scan_roots = [
        _REPO_ROOT / ".claude" / "hooks",
        _REPO_ROOT / ".claude" / "scripts",
    ]
    keyword_re = re.compile(r"\b(autonomous_loop|swarm|swarm_iteration)\b")
    for root in scan_roots:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            rel = py_file.relative_to(_REPO_ROOT).as_posix()
            if "/federation/" in rel:
                continue
            if rel.endswith("check_arbitration_kernel.py"):
                continue
            if rel.endswith("boundary_test.py"):
                continue
            try:
                txt = py_file.read_text(encoding="utf-8")
            except OSError:
                continue
            basename = py_file.name
            is_loop_file = basename in _AUTONOMOUS_LOOP_FILES
            mentions_loop = bool(keyword_re.search(txt))
            if not (is_loop_file or mentions_loop):
                continue
            for mod, lineno in _imports_federation_via_ast(py_file):
                failures.append(
                    "{0}:{1}: autonomous-loop path imports {2!r}".format(
                        rel, lineno, mod,
                    )
                )
    return failures


def main(argv: List[str]) -> int:
    all_failures: List[str] = []
    all_failures += check_import_roots_blocked()
    all_failures += check_federation_pkg_stdlib_only()
    all_failures += check_workflows_no_autostart()
    all_failures += check_autonomous_loop_no_federation()
    if all_failures:
        sys.stderr.write(
            "[boundary_test] C1 crypto sidecar boundary VIOLATED:\n"
        )
        for f in all_failures:
            sys.stderr.write("  - {0}\n".format(f))
        return 1
    sys.stdout.write("[boundary_test] C1 crypto sidecar boundary INTACT\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
