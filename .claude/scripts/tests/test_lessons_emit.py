"""Tests that lessons.write_lesson emits a lesson_write audit event.

Sprint 5 A.1 wire-up.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))
import lessons  # noqa: E402


class LessonsEmitTest(unittest.TestCase):

    def setUp(self):
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmp = Path(tempfile.mkdtemp(prefix="lessons-emit-test-"))
        self.lessons_dir = self.tmp / "lessons"
        self.log_path = self.tmp / "audit-log.jsonl"
        self._snap = {
            k: os.environ.get(k)
            for k in (
                "CEO_LESSONS_DIR",
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_LOG_LOCK",
                "CEO_AUDIT_LOG_ERR",
                "CEO_AUDIT_LOG_DIR",
                "CEO_AUDIT_SYNC_MODE",
            )
        }
        os.environ["CEO_LESSONS_DIR"] = str(self.lessons_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log_path)
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.tmp / "audit.lock")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.tmp / "audit.err")
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.tmp)

    def tearDown(self):
        for k, v in self._snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_events(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_write_lesson_emits_lesson_write_event(self):
        path = lessons.write_lesson(
            scenario_id="scen-01",
            archetype="security-engineer",
            remember_this="JWT validation must happen at boundary",
            scope_tags=["security", "auth"],
            agent_response="ignored",
            expected_response="ignored",
            base_dir=str(self.lessons_dir),
        )
        self.assertTrue(path.exists(), "lesson file not written")
        events = self._read_events()
        self.assertEqual(len(events), 1, f"expected 1 event, got {events}")
        ev = events[0]
        self.assertEqual(ev["action"], "lesson_write")
        self.assertEqual(ev["archetype"], "security-engineer")
        self.assertEqual(ev["scope_tags"], ["security", "auth"])
        self.assertEqual(ev["trigger"], "benchmark_fail")
        self.assertEqual(ev["source_event_id"], "scen-01")

    def test_custom_trigger_kwarg(self):
        lessons.write_lesson(
            scenario_id="s-a",
            archetype="qa",
            remember_this="x",
            scope_tags=["t"],
            trigger="manual",
            base_dir=str(self.lessons_dir),
        )
        events = self._read_events()
        self.assertEqual(events[0]["trigger"], "manual")

    def test_write_is_fail_open_on_emit_error(self):
        """If the audit log path is unwritable, write_lesson still succeeds."""
        readonly = self.tmp / "ro"
        readonly.mkdir(mode=0o500)
        try:
            os.environ["CEO_AUDIT_LOG_PATH"] = str(readonly / "x.jsonl")
            path = lessons.write_lesson(
                scenario_id="s-b",
                archetype="qa",
                remember_this="still works",
                scope_tags=["t"],
                base_dir=str(self.lessons_dir),
            )
            self.assertTrue(path.exists())
        finally:
            readonly.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
