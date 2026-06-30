"""Chaos-test conftest (PLAN-011 Phase 10).

Fixtures that together construct a chaos environment:

- `chaos_env` — isolated TestEnvContext with CEO_CHAOS_ALLOWED=1.
- `isolated_audit_log` — returns the audit log path under the
  isolated tree; guaranteed empty at fixture entry.
- `chaos_wrapper_factory` — builds a chaos wrapper via
  `.claude/scripts/chaos-inject.py`'s internal `generate_wrapper`
  helper (no 3-gate check in-test — we trust the fixture scope).

Environment mandate (ADR-037 §Decision §2): NO raw `monkeypatch.setenv`
for `HOME`/`CEO_*`/`CLAUDE_*`. Every override flows through
TestEnvContext's snapshot/restore.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# Load the chaos-inject module via importlib (dash in filename).
_CI_SCRIPT = _SCRIPTS_DIR / "chaos-inject.py"
_ci_spec = importlib.util.spec_from_file_location("chaos_inject", _CI_SCRIPT)
ci = importlib.util.module_from_spec(_ci_spec)
assert _ci_spec.loader is not None
_ci_spec.loader.exec_module(ci)


_FIXTURES = _HOOKS_DIR / "tests" / "fixtures" / "hooks"


class _ChaosEnv(TestEnvContext):
    """TestEnvContext with CEO_CHAOS_ALLOWED=1 layered on."""

    __test__ = False  # don't collect as test class

    def runTest(self):  # pragma: no cover
        pass


@pytest.fixture
def chaos_env() -> Iterator[_ChaosEnv]:
    """Isolated env for chaos tests.

    Sets CEO_CHAOS_ALLOWED=1 so chaos-inject's gate-1 opens for any
    in-process helper. The other 2 gates (parent cmdline + cwd) are
    out-of-band — chaos-inject gate-checking is unit-tested in
    `.claude/scripts/tests/test_chaos_inject_lockdown.py`; these
    fixture-based tests use the generate_wrapper helper directly
    (which has NO gate check — gates live at the CLI entry point).
    """
    ctx = _ChaosEnv()
    ctx.setUp()
    try:
        # CEO_CHAOS_ALLOWED gets captured by TestEnvContext's env
        # snapshot because it starts with CEO_. setUp/tearDown handle
        # restoration.
        os.environ["CEO_CHAOS_ALLOWED"] = "1"
        yield ctx
    finally:
        ctx.tearDown()


@pytest.fixture
def isolated_audit_log(chaos_env: _ChaosEnv) -> Path:
    """Path to the isolated audit-log.jsonl (guaranteed clean)."""
    p = chaos_env.audit_dir / "audit-log.jsonl"
    if p.exists():
        p.unlink()
    return p


@pytest.fixture
def chaos_wrapper_factory(chaos_env: _ChaosEnv):
    """Factory that generates a chaos wrapper into the chaos_env tmpdir.

    Returns a callable `(hook_name, mode, timeout_seconds=0.5) -> Path`
    where the returned Path is the generated wrapper script.
    """
    def _factory(hook_name: str, mode: str, timeout_seconds: float = 0.5) -> Path:
        out = chaos_env.project_dir / "wrappers" / f"{hook_name}-{mode}.py"
        ci.generate_wrapper(
            hook_name=hook_name,
            mode=mode,
            output_path=out,
            timeout_seconds=timeout_seconds,
        )
        return out

    return _factory


@pytest.fixture
def hook_fixture_loader():
    """Read the canonical fixture payload for a hook."""
    def _loader(hook_name: str) -> str:
        return (_FIXTURES / hook_name / "in.json").read_text(encoding="utf-8")
    return _loader


@pytest.fixture
def run_hook_subprocess(chaos_env: _ChaosEnv):
    """Run a hook (or any Python script) as a subprocess.

    Returns a callable
    `(script_path, stdin_payload, timeout=5.0, extra_env=None) ->
     (rc, stdout, stderr)`.

    The subprocess inherits chaos_env's isolated environment (HOME,
    CLAUDE_PROJECT_DIR, CEO_AUDIT_LOG_*).
    """
    def _run(
        script_path: Path,
        stdin_payload: str,
        timeout: float = 5.0,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str]:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        try:
            r = subprocess.run(
                [sys.executable, str(script_path)],
                input=stdin_payload,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout,
            )
            return (r.returncode, r.stdout, r.stderr)
        except subprocess.TimeoutExpired as e:
            return (-1, (e.stdout or b"").decode("utf-8", errors="replace")
                    if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or ""),
                    "TIMEOUT")

    return _run


# -----------------------------------------------------------------------------
# Env-isolation invariant test (runs as part of conftest via explicit test)
# -----------------------------------------------------------------------------


def assert_chaos_env_uses_tmpdir(chaos_env: _ChaosEnv) -> None:
    """Helper: validate the chaos env never points at real $HOME.

    Called from individual tests that want to assert this invariant.
    Not a fixture itself (fixtures are not asserts).
    """
    home = os.environ.get("HOME", "")
    assert "ceo-hook-test-" in home or "/var/" in home or "/tmp" in home, (
        f"chaos fixture leaked real HOME: {home!r}"
    )
    assert os.environ.get("CEO_CHAOS_ALLOWED") == "1"
