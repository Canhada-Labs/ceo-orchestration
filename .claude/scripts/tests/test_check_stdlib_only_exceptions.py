"""PLAN-120 E10-F1 regression — check-stdlib-only honors file-scoped exceptions.

`_lib/test_isolation.py` (PLAN-119 WS-A pytest-fixture module) imports `pytest`
and `tier_policy_cli/setup.py` imports `setuptools`. Both are test/build-only,
never on an adopter runtime path (PLAN-120 AC4.4). They are declared in
`_FILE_SCOPED_EXCEPTIONS` so the scan stays clean AND the SBOM §A
stdlib-only attestation (SBOM.md) stays accurate. This test guards that the
exception mechanism keeps working and that no NEW undisclosed third-party
import sneaks onto the production hot path.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO / ".claude/scripts/check-stdlib-only.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_stdlib_only", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _run_json() -> dict:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--json"],
        capture_output=True, text=True, timeout=180,
    )
    return json.loads(proc.stdout)


def test_scan_has_zero_violations() -> None:
    report = _run_json()
    assert report["violations"] == {}, (
        f"check-stdlib-only reported violations (E10-F1 regression or a NEW "
        f"undisclosed third-party import): {report['violations']}"
    )


def test_test_isolation_pytest_not_flagged() -> None:
    report = _run_json()
    assert ".claude/hooks/_lib/test_isolation.py" not in report["violations"]


def test_setup_setuptools_not_flagged() -> None:
    report = _run_json()
    assert ".claude/scripts/tier_policy_cli/setup.py" not in report["violations"]


def test_file_scoped_exceptions_are_narrow() -> None:
    """Exceptions must be file-scoped (not a broad package allowlist) and only
    cover the two documented test/build-only files."""
    mod = _load_module()
    exc = mod._FILE_SCOPED_EXCEPTIONS
    assert set(exc) == {
        ".claude/hooks/_lib/test_isolation.py",
        ".claude/scripts/tier_policy_cli/setup.py",
    }
    assert exc[".claude/hooks/_lib/test_isolation.py"] == frozenset({"pytest"})
    assert exc[".claude/scripts/tier_policy_cli/setup.py"] == frozenset({"setuptools"})


def test_exception_is_truly_file_scoped() -> None:
    """A pytest import in a DIFFERENT _lib file must still be flagged — the
    exception must not leak into a package-wide allowance."""
    mod = _load_module()
    local_index, global_names = mod._build_local_module_index()
    # Synthesize a fake _lib module that imports pytest; it must be flagged
    # because it is NOT in _FILE_SCOPED_EXCEPTIONS.
    fake = _REPO / ".claude/hooks/_lib/__plan120_probe_not_real.py"
    fake.write_text("import pytest\n", encoding="utf-8")
    try:
        violations = mod.validate_file(fake, local_index, global_names)
        assert any("pytest" in v for v in violations), (
            "a pytest import in a non-excepted _lib file must be flagged"
        )
    finally:
        fake.unlink(missing_ok=True)


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
