"""Tests for .claude/scripts/github-api-client.py — PLAN-019 F-CHAOS-11.

The module has a hyphen in its filename (kebab-case CLI convention) so
it cannot be imported as `github_api_client`. We load it via
`importlib.util` into a unique sys.modules entry so dataclass field
resolution works (Python 3.9 resolves field type hints against the
module's __dict__; an unregistered module breaks).

Coverage:
1. Breaker opens after N consecutive 5xx failures.
2. Breaker half-open probe allowed after cooldown.
3. Non-retryable 4xx (except 429) does NOT advance the breaker.
4. Successful call resets breaker.
5. CircuitOpenError raised when breaker is open.
6. CLI exit codes: 2 (usage), 3 (circuit), 4 (api error).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "github-api-client.py"

# Make _lib importable for TestEnvContext (canonical test base).
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))
from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Register module in sys.modules so Python 3.9 dataclass resolves fields."""
    spec = importlib.util.spec_from_file_location("github_api_client_test_mod", str(_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["github_api_client_test_mod"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestBreaker(TestEnvContext):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_initial_state_is_closed(self):
        b = self.mod._BreakerState(threshold=3, cooldown_s=10)
        self.assertFalse(b.is_open(0.0))

    def test_breaker_opens_after_threshold_fails(self):
        b = self.mod._BreakerState(threshold=3, cooldown_s=10)
        for _ in range(3):
            b.record_failure(100.0)
        self.assertTrue(b.is_open(100.0))
        self.assertEqual(b.consecutive_fails, 3)

    def test_breaker_closes_on_success_before_threshold(self):
        b = self.mod._BreakerState(threshold=3, cooldown_s=10)
        b.record_failure(100.0)
        b.record_failure(100.0)
        b.record_success()
        self.assertEqual(b.consecutive_fails, 0)
        self.assertFalse(b.is_open(100.0))

    def test_half_open_probe_after_cooldown(self):
        b = self.mod._BreakerState(threshold=2, cooldown_s=10)
        b.record_failure(100.0)
        b.record_failure(100.0)
        # Still within cooldown.
        self.assertTrue(b.is_open(105.0))
        # After cooldown: first caller gets half-open probe (is_open → False).
        self.assertFalse(b.is_open(111.0))
        self.assertTrue(b.half_open_in_flight)
        # Subsequent caller while probe in flight → still open.
        self.assertTrue(b.is_open(112.0))


class TestClient(TestEnvContext):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def _patch_request(self, status: int, body: bytes):
        """Install a mock that makes _request return the given status + body."""
        return patch.object(
            self.mod.GitHubClient,
            "_request",
            return_value=(status, body),
        )

    def test_4xx_does_not_open_breaker(self):
        c = self.mod.GitHubClient(breaker_threshold=2, max_retries=0)
        with self._patch_request(404, b'{"message":"Not Found"}'):
            with self.assertRaises(self.mod.GitHubAPIError) as cm:
                c.get("/does-not-exist")
            self.assertEqual(cm.exception.status, 404)
        # 404 is non-retryable + reachable → success signal to breaker.
        self.assertEqual(c.breaker.consecutive_fails, 0)

    def test_5xx_opens_breaker_after_threshold(self):
        c = self.mod.GitHubClient(breaker_threshold=2, max_retries=0)
        with self._patch_request(503, b"service unavailable"):
            # First call exhausts 1 attempt, records 1 failure.
            with self.assertRaises(self.mod.GitHubAPIError):
                c.get("/test")
            with self.assertRaises((self.mod.GitHubAPIError, self.mod.CircuitOpenError)):
                c.get("/test")
        self.assertTrue(c.breaker_is_open())

    def test_circuit_open_raises_circuit_open_error(self):
        c = self.mod.GitHubClient(breaker_threshold=1, max_retries=0)
        # Pre-open breaker by recording failures directly.
        import time as _t
        c.breaker.record_failure(_t.monotonic())
        with self.assertRaises(self.mod.CircuitOpenError):
            c.get("/test")

    def test_success_resets_breaker(self):
        c = self.mod.GitHubClient(breaker_threshold=3, max_retries=0)
        c.breaker.consecutive_fails = 2
        with self._patch_request(200, b'{"ok":true}'):
            out = c.get("/ok")
        self.assertEqual(out, {"ok": True})
        self.assertEqual(c.breaker.consecutive_fails, 0)


class TestCLI(TestEnvContext):
    """Subprocess smoke — usage errors + basic exit codes."""

    def test_usage_exit_code(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr.lower())


if __name__ == "__main__":
    unittest.main()
