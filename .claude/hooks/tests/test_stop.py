"""Tests for Stop lifecycle hook (PLAN-028 / ADR-056)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]

import Stop  # type: ignore  # noqa: E402


class TestStopKillSwitch(unittest.TestCase):
    def test_kill_switch_honored(self) -> None:
        with patch.dict(os.environ, {"CEO_EXTENDED_LIFECYCLE": "0"}, clear=False):
            out = Stop.decide(
                repo_root=Path("/"),
                session_id="t",
                reason="user_stop",
                end_already_ran=False,
            )
        payload = json.loads(out)
        self.assertIn("kill-switch", payload.get("systemMessage", ""))


class TestStopDecide(unittest.TestCase):
    def test_decide_returns_allow(self) -> None:
        out = Stop.decide(
            repo_root=Path.cwd(),
            session_id="t",
            reason="user_stop",
            end_already_ran=False,
        )
        payload = json.loads(out)
        self.assertTrue(payload.get("continue") is True)

    def test_decide_with_reason_variants(self) -> None:
        for reason in ("SIGINT", "SIGTERM", "timeout", "user_stop", "error"):
            with self.subTest(reason=reason):
                out = Stop.decide(
                    repo_root=Path.cwd(),
                    session_id="t",
                    reason=reason,
                    end_already_ran=False,
                )
                payload = json.loads(out)
                self.assertTrue(payload.get("continue") is True)
                self.assertIn(reason, payload.get("systemMessage", ""))

    def test_decide_partial_saved_surfaces(self) -> None:
        out = Stop.decide(
            repo_root=Path.cwd(),
            session_id="t",
            reason="user_stop",
            end_already_ran=True,
        )
        payload = json.loads(out)
        msg = payload.get("systemMessage", "")
        self.assertIn("partial_saved=True", msg)


class TestStopStaleLocks(unittest.TestCase):
    def test_release_stale_locks_returns_count(self) -> None:
        result = Stop._release_stale_locks(Path("/nonexistent"))
        self.assertEqual(result, 0)

    def test_release_stale_locks_releases_old(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            scratch = repo_root / ".claude" / "scratch"
            scratch.mkdir(parents=True)
            # Create a fake stale lock (age > 60s)
            stale = scratch / "old.lock"
            stale.write_text("")
            old_time = time.time() - 120
            os.utime(stale, (old_time, old_time))
            # Create a fresh lock
            fresh = scratch / "fresh.lock"
            fresh.write_text("")
            released = Stop._release_stale_locks(repo_root)
            self.assertEqual(released, 1)
            self.assertFalse(stale.exists(), "Stale lock should be released")
            self.assertTrue(fresh.exists(), "Fresh lock should survive")

    def test_release_stale_locks_handles_no_scratch_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = Stop._release_stale_locks(Path(tmp))
            self.assertEqual(result, 0)


class TestStopFlush(unittest.TestCase):
    def test_flush_never_raises(self) -> None:
        try:
            Stop._flush_audit_log_filelock()
        except Exception as e:
            self.fail(f"raised: {type(e).__name__}: {e}")


class TestStopEmit(unittest.TestCase):
    def test_emit_never_raises(self) -> None:
        try:
            Stop._emit_session_stop(
                session_id="t",
                reason="SIGINT",
                partial_state_saved=False,
                repo_root=Path("/tmp"),
            )
        except Exception as e:
            self.fail(f"raised: {type(e).__name__}: {e}")


class TestStopMain(unittest.TestCase):
    def test_main_fails_open(self) -> None:
        import io
        orig_stdin = sys.stdin
        orig_stdout = sys.stdout
        try:
            sys.stdin = io.StringIO("")
            sys.stdout = io.StringIO()
            rc = Stop.main()
            self.assertEqual(rc, 0)
        finally:
            sys.stdin = orig_stdin
            sys.stdout = orig_stdout


if __name__ == "__main__":
    unittest.main()
