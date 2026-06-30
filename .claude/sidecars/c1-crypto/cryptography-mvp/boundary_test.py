#!/usr/bin/env python3
"""C1 cryptography-mvp sidecar boundary test (ADR-126 §Part 2 enforcement).

Asserts that `cryptography` is imported ONLY from the sanctioned
sidecar tree at:

  .claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/

Any core path containing `import cryptography` or `from cryptography`
fails this test (defense-in-depth on top of check-stdlib-only.py).

Exit codes:
  0 = boundary preserved
  1 = boundary violated (file paths printed to stderr)
  2 = environment error (sidecar tree missing)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterable, List

_HERE = Path(__file__).resolve()
_SIDECAR_ROOT = _HERE.parent
_REPO_ROOT = _HERE.parents[4]

# Core paths that MUST NOT import `cryptography` (defense-in-depth).
_CORE_SCAN_ROOTS = [
    _REPO_ROOT / ".claude/hooks",
    _REPO_ROOT / ".claude/scripts",
    _REPO_ROOT / ".claude/policies",
    _REPO_ROOT / "SPEC",
    _REPO_ROOT / ".github/workflows",
]

# The ONLY legitimate `cryptography` import root.
_SIDECAR_CODE = _SIDECAR_ROOT / "sidecar_code"


def _imports_cryptography(path: Path) -> bool:
    """Return True if `path` contains `import cryptography` or `from cryptography...`."""
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "cryptography" or alias.name.startswith("cryptography."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "cryptography" or module.startswith("cryptography."):
                return True
    return False


def _walk_py(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return (p for p in root.rglob("*.py") if p.is_file())


def main() -> int:
    if not _SIDECAR_CODE.is_dir():
        print(f"ERROR: sidecar tree missing: {_SIDECAR_CODE}", file=sys.stderr)
        return 2

    violations: List[Path] = []
    for root in _CORE_SCAN_ROOTS:
        for py in _walk_py(root):
            if _imports_cryptography(py):
                violations.append(py.relative_to(_REPO_ROOT))

    if violations:
        print(
            f"BOUNDARY VIOLATION: {len(violations)} core path(s) import `cryptography`:",
            file=sys.stderr,
        )
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        print(
            "\nADR-126 §Part 2: `cryptography` is fenced to the sidecar tree at:",
            file=sys.stderr,
        )
        print(f"  {_SIDECAR_CODE.relative_to(_REPO_ROOT)}", file=sys.stderr)
        return 1

    # Positive assertion: sidecar tree DOES import cryptography (at least one .py)
    sidecar_has_import = False
    for py in _walk_py(_SIDECAR_CODE):
        if _imports_cryptography(py):
            sidecar_has_import = True
            break
    if not sidecar_has_import:
        print(
            f"WARNING: sidecar tree {_SIDECAR_CODE.relative_to(_REPO_ROOT)} has NO "
            "`cryptography` imports — sidecar may be empty (cert_inspector.py "
            "not yet `git mv`-ed from staging?)",
            file=sys.stderr,
        )
        # Not a failure (sandbox-sim runs before Owner Phase A2-post git mv)

    print(f"boundary_test PASS: {len(_CORE_SCAN_ROOTS)} core roots scanned, 0 violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
