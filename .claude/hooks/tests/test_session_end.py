"""Tests for SessionEnd lifecycle hook (PLAN-028 / ADR-056)."""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]

import SessionEnd  # type: ignore  # noqa: E402


class TestSessionEndKillSwitch(unittest.TestCase):
    def test_kill_switch_honored(self) -> None:
        with patch.dict(os.environ, {"CEO_EXTENDED_LIFECYCLE": "0"}, clear=False):
            out = SessionEnd.decide(
                repo_root=Path("/"), session_id="t", reason="normal"
            )
        payload = json.loads(out)
        self.assertTrue(payload.get("continue") is True)
        self.assertIn("kill-switch", payload.get("systemMessage", ""))


class TestSessionEndMemoryState(unittest.TestCase):
    def test_memory_state_returns_dict(self) -> None:
        result = SessionEnd._memory_dir_state(Path.cwd())
        self.assertIsInstance(result, dict)
        for key in ("writable", "memory_md_present", "slug"):
            with self.subTest(key=key):
                self.assertIn(key, result)

    def test_memory_state_writable_is_bool(self) -> None:
        result = SessionEnd._memory_dir_state(Path.cwd())
        self.assertIsInstance(result["writable"], bool)

    def test_memory_state_handles_weird_path(self) -> None:
        """Non-existent repo_root returns all False (no exception)."""
        result = SessionEnd._memory_dir_state(Path("/nonexistent/xyz"))
        self.assertIsInstance(result, dict)
        self.assertFalse(result["writable"])


class TestSessionEndDecide(unittest.TestCase):
    def test_decide_returns_allow_normal(self) -> None:
        out = SessionEnd.decide(
            repo_root=Path.cwd(), session_id="t", reason="normal"
        )
        payload = json.loads(out)
        self.assertTrue(payload.get("continue") is True)

    def test_decide_returns_allow_interrupted(self) -> None:
        out = SessionEnd.decide(
            repo_root=Path.cwd(), session_id="t", reason="interrupted"
        )
        payload = json.loads(out)
        self.assertTrue(payload.get("continue") is True)
        self.assertIn("interrupted", payload.get("systemMessage", ""))

    def test_decide_never_raises(self) -> None:
        for weird in ("/nonexistent/xyz", "/"):
            with self.subTest(root=weird):
                try:
                    out = SessionEnd.decide(
                        repo_root=Path(weird), session_id="x", reason="r"
                    )
                    payload = json.loads(out)
                    self.assertTrue(payload.get("continue") is True)
                except Exception as e:
                    self.fail(f"raised: {type(e).__name__}: {e}")


class TestSessionEndFlush(unittest.TestCase):
    def test_flush_never_raises(self) -> None:
        """Filelock flush is best-effort; missing lock file is OK."""
        try:
            SessionEnd._flush_audit_log_filelock(Path("/nonexistent"))
        except Exception as e:
            self.fail(f"flush raised: {type(e).__name__}: {e}")


class TestSessionEndEmit(unittest.TestCase):
    def test_emit_never_raises(self) -> None:
        try:
            SessionEnd._emit_session_end(
                session_id="t",
                reason="normal",
                memory_state={"writable": True, "memory_md_present": True, "slug": ""},
                repo_root=Path("/tmp"),
            )
        except Exception as e:
            self.fail(f"emit raised: {type(e).__name__}: {e}")


class TestSessionEndMain(unittest.TestCase):
    def test_main_fails_open(self) -> None:
        import io
        orig_stdin = sys.stdin
        orig_stdout = sys.stdout
        try:
            sys.stdin = io.StringIO("")
            sys.stdout = io.StringIO()
            rc = SessionEnd.main()
            self.assertEqual(rc, 0)
        finally:
            sys.stdin = orig_stdin
            sys.stdout = orig_stdout


if __name__ == "__main__":
    unittest.main()
