"""Integration-suite conftest — shared fixtures for PLAN-010 Phase 1 e2e tests.

All env isolation MUST go through `_lib.testing.TestEnvContext`. This
file is the SINGLE place where a raw environment is touched; every
scenario uses the `ceo_env` fixture which constructs a fresh
TestEnvContext per test (xdist-safe: each worker gets its own tmpdir).

NO raw `monkeypatch.setenv` anywhere. See ADR-021.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

import pytest

# Make `.claude/hooks/` importable so tests can reuse `_lib.testing`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


REPO_ROOT = _REPO_ROOT


class _IntegrationEnv(TestEnvContext):
    """Thin subclass so we can instantiate TestEnvContext outside unittest."""

    # TestEnvContext subclasses unittest.TestCase — pytest can drive its
    # setUp/tearDown manually as long as we provide a dummy method for
    # the test-runner introspection.
    def runTest(self):  # pragma: no cover - never executed
        pass


@pytest.fixture
def ceo_env() -> Iterator[_IntegrationEnv]:
    """Fresh isolated env per test: tmp $HOME, tmp CLAUDE_PROJECT_DIR, tmp audit dir.

    Wraps `_lib.testing.TestEnvContext`. Asserts that the env points at
    tmpdirs (never real `$HOME`) — see test_full_session.py for a direct
    assertion of this invariant.
    """
    ctx = _IntegrationEnv()
    ctx.setUp()
    try:
        # Seed a minimal .claude/ layout the hooks expect.
        (ctx.project_dir / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
        (ctx.project_dir / ".claude" / "skills" / "core").mkdir(
            parents=True, exist_ok=True
        )
        yield ctx
    finally:
        ctx.tearDown()


def run_hook(
    hook_name: str,
    payload: Dict[str, Any],
    env_overrides: Optional[Dict[str, str]] = None,
    timeout: float = 5.0,
) -> "subprocess.CompletedProcess[str]":
    """Invoke a hook as a subprocess with the given JSON payload on stdin.

    Hooks are single-file scripts with argv/stdin contract — we never
    import them. This matches production: Claude Code spawns hooks as
    subprocesses with a JSON blob on stdin.
    """
    import json

    hook_path = _HOOKS_DIR / hook_name
    assert hook_path.is_file(), f"hook not found: {hook_path}"

    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def parse_decision(stdout: str) -> Dict[str, Any]:
    """Parse the JSON decision line a hook writes to stdout.

    Per Claude Code hook schema (PLAN-091-followup S116 fail-open contract):
    a bare ``{}`` envelope means "allow" — the schema enum is only
    {"approve","block"}, and absence of a decision key implies allow.
    To preserve the legacy test idiom ``d["decision"] == "allow"``,
    we normalize the parsed envelope by injecting ``decision: allow``
    when the key is missing.
    """
    import json

    line = (stdout or "").strip().splitlines()[-1] if stdout.strip() else "{}"
    d = json.loads(line)
    if isinstance(d, dict) and "decision" not in d:
        d["decision"] = "allow"
    return d
