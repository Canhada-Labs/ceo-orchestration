"""Tests for PLAN-008 Phase 3 — lessons CLI: task-desc keyword
extraction + --emit-consumer lesson_read audit event.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import lessons  # noqa: E402

_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


class TestLessonsTop3WithEmit(TestEnvContext):
    def setUp(self):
        super().setUp()
        # Use a dedicated lessons dir under the test HOME
        self.lessons_dir = Path(os.environ["HOME"]) / ".claude" / "projects" / "ceo-orchestration" / "lessons"
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
        # Seed 3 lessons that will match an "Agent Architect" top-K query
        for i in range(3):
            lessons.write_lesson(
                scenario_id=f"scn-{i}",
                archetype="Agent Architect",
                remember_this=f"Lesson {i}: reflect on spawn outcomes.",
                scope_tags=["agent", "architect", f"tag-{i}"],
                agent_response="",
                expected_response="",
                base_dir=str(self.lessons_dir),
            )

    def _audit_entries(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(l) for l in log.read_text().splitlines() if l.strip()]

    def test_top3_without_consumer_skips_emit(self):
        argv = [
            "top3", "--archetype", "Agent Architect",
            "--keywords", "agent",
            "--dir", str(self.lessons_dir),
        ]
        with patch.object(sys, "argv", ["lessons.py"] + argv):
            rc = lessons.main()
        self.assertEqual(rc, 0)
        reads = [e for e in self._audit_entries() if e.get("action") == "lesson_read"]
        self.assertEqual(reads, [])

    def test_top3_with_consumer_emits_event(self):
        argv = [
            "top3", "--archetype", "Agent Architect",
            "--keywords", "agent",
            "--dir", str(self.lessons_dir),
            "--emit-consumer", "architect",
        ]
        with patch.object(sys, "argv", ["lessons.py"] + argv):
            rc = lessons.main()
        self.assertEqual(rc, 0)
        reads = [e for e in self._audit_entries() if e.get("action") == "lesson_read"]
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0]["consumer"], "architect")
        self.assertEqual(reads[0]["archetype"], "Agent Architect")
        self.assertGreater(reads[0]["lesson_count"], 0)
        self.assertEqual(reads[0]["k"], 3)

    def test_task_desc_extends_keywords(self):
        # Seed a lesson tagged with 'latency' — should only surface if
        # 'latency' enters keywords via task-desc extraction.
        lessons.write_lesson(
            scenario_id="scn-latency",
            archetype="Agent Architect",
            remember_this="Watch p99 under load.",
            scope_tags=["latency", "perf"],
            agent_response="",
            expected_response="",
            base_dir=str(self.lessons_dir),
        )
        argv = [
            "top3", "--archetype", "Agent Architect",
            "--keywords", "misc",  # won't match latency tag directly
            "--task-desc", "Design a latency-bounded order routing flow",
            "--dir", str(self.lessons_dir),
            "--emit-consumer", "architect",
        ]
        buf = io.StringIO()
        with patch.object(sys, "argv", ["lessons.py"] + argv), \
             patch.object(sys, "stdout", buf):
            rc = lessons.main()
        self.assertEqual(rc, 0)
        # The emitted event's keywords include task-desc-extracted tokens
        reads = [e for e in self._audit_entries() if e.get("action") == "lesson_read"]
        self.assertEqual(len(reads), 1)
        kws = reads[0]["keywords"]
        self.assertIn("latency", kws)
        self.assertIn("order", kws)
        self.assertIn("routing", kws)
        # Short words (<4 chars) are excluded
        self.assertNotIn("a", kws)

    def test_top3_zero_lessons_still_emits_when_consumer_set(self):
        # Different archetype → no matches
        argv = [
            "top3", "--archetype", "NonexistentArchetype",
            "--keywords", "irrelevant",
            "--dir", str(self.lessons_dir),
            "--emit-consumer", "architect",
        ]
        with patch.object(sys, "argv", ["lessons.py"] + argv):
            rc = lessons.main()
        self.assertEqual(rc, 0)
        reads = [e for e in self._audit_entries() if e.get("action") == "lesson_read"]
        self.assertEqual(len(reads), 1)
        self.assertEqual(reads[0]["lesson_count"], 0)

    def test_custom_k_respected(self):
        argv = [
            "top3", "--archetype", "Agent Architect",
            "--keywords", "agent",
            "--dir", str(self.lessons_dir),
            "--emit-consumer", "spawn",
            "--k", "2",
        ]
        with patch.object(sys, "argv", ["lessons.py"] + argv):
            lessons.main()
        reads = [e for e in self._audit_entries() if e.get("action") == "lesson_read"]
        self.assertEqual(reads[0]["k"], 2)
        self.assertLessEqual(reads[0]["lesson_count"], 2)


if __name__ == "__main__":
    unittest.main()
