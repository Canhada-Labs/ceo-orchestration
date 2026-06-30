#!/usr/bin/env python3
"""check-version-drift.py — PLAN-108 Wave B.3 governance probe.

Reads VERSION + pyproject.toml + npm/package.json. Exits 1 if any of the
three diverge from the canonical VERSION file. Exits 0 if all aligned.

Stdlib-only, Python >= 3.9. Wired into .claude/scripts/validate-governance.sh
by PLAN-108 Wave B.3.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_pyproject_version(text: str) -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if m is None:
        raise SystemExit("check-version-drift: pyproject.toml has no version line")
    return m.group(1)


def _extract_package_json_version(text: str) -> str:
    m = re.search(r'"version"\s*:\s*"([^"]+)"', text)
    if m is None:
        raise SystemExit("check-version-drift: package.json has no version line")
    return m.group(1)


def main() -> int:
    version_file = _REPO_ROOT / "VERSION"
    pyproject = _REPO_ROOT / "pyproject.toml"
    npm_pkg = _REPO_ROOT / "npm/package.json"

    if not version_file.exists():
        print(f"FAIL: missing VERSION file: {version_file}")
        return 1
    canonical = _read(version_file).strip()
    print(f"VERSION (canonical): {canonical}")

    drifts = []

    if not pyproject.exists():
        print(f"WARN: pyproject.toml missing at {pyproject}")
    else:
        py_ver = _extract_pyproject_version(_read(pyproject))
        print(f"pyproject.toml:     {py_ver}")
        if py_ver != canonical:
            drifts.append(f"pyproject.toml ({py_ver}) != VERSION ({canonical})")

    if not npm_pkg.exists():
        print(f"WARN: npm/package.json missing at {npm_pkg}")
    else:
        npm_ver = _extract_package_json_version(_read(npm_pkg))
        print(f"npm/package.json:   {npm_ver}")
        if npm_ver != canonical:
            drifts.append(f"npm/package.json ({npm_ver}) != VERSION ({canonical})")

    if drifts:
        print("")
        print("FAIL: version drift detected:")
        for d in drifts:
            print(f"  - {d}")
        return 1

    print("")
    print("PASS: all versions aligned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
