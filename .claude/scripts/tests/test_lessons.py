"""Unit tests for lessons.py (Reflexion lessons CRUD + ranking)."""

from __future__ import annotations

import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import lessons.py from .claude/scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lessons  # noqa: E402


class LessonsTestBase(unittest.TestCase):
    """Isolates the lessons directory per test."""

    def setUp(self) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="ceo-lessons-test-"))
        # Override env so lessons.py uses our tmp dir by default
        self._old_env = os.environ.get("CEO_LESSONS_DIR")
        os.environ["CEO_LESSONS_DIR"] = str(self._tmp)

    def tearDown(self) -> None:
        if self._old_env is None:
            os.environ.pop("CEO_LESSONS_DIR", None)
        else:
            os.environ["CEO_LESSONS_DIR"] = self._old_env
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_raw_lesson(self, data: dict) -> Path:
        """Write a lesson JSON directly (bypass write_lesson for fixture setup)."""
        lid = data.get("lesson_id") or "fixture"
        path = self._tmp / f"{lid}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path


class TestWriteLesson(LessonsTestBase):

    def test_write_creates_file(self):
        path = lessons.write_lesson(
            scenario_id="owasp-a01",
            archetype="Security Engineer",
            remember_this="Always check CSRF token on state-changing requests",
            scope_tags=["csrf", "auth"],
            agent_response="some response",
            expected_response="correct response",
        )
        self.assertTrue(path.exists())
        data = json.loads(path.read_text())
        self.assertEqual(data["scenario_id"], "owasp-a01")
        self.assertEqual(data["archetype"], "Security Engineer")
        self.assertIn("csrf", data["scope_tags"])
        self.assertTrue(data["created_at"])
        self.assertTrue(data["lesson_id"])

    def test_write_truncates_remember_to_200(self):
        long_text = "x" * 500
        path = lessons.write_lesson(
            scenario_id="s1",
            archetype="VP Engineering",
            remember_this=long_text,
            scope_tags=["x"],
        )
        data = json.loads(path.read_text())
        self.assertEqual(len(data["remember_this"]), 200)

    def test_write_runs_redaction(self):
        """agent_response should pass through redact_secrets."""
        # Use a known secret pattern — AWS key format
        secret = "AKIAIOSFODNN7EXAMPLE"
        path = lessons.write_lesson(
            scenario_id="s1",
            archetype="Security Engineer",
            remember_this="test",
            scope_tags=["x"],
            agent_response=f"my key is {secret}",
        )
        data = json.loads(path.read_text())
        # Redacted version should NOT contain the literal secret
        self.assertNotIn(secret, data["agent_response"])


class TestListLessons(LessonsTestBase):

    def test_empty_dir_returns_empty_list(self):
        self.assertEqual(lessons.list_lessons(), [])

    def test_nonexistent_dir_returns_empty(self):
        nonexistent = str(self._tmp / "does-not-exist")
        self.assertEqual(lessons.list_lessons(nonexistent), [])

    def test_ignores_non_json_files(self):
        (self._tmp / "not-a-lesson.txt").write_text("hello")
        self.assertEqual(lessons.list_lessons(), [])

    def test_returns_stored_lessons(self):
        lessons.write_lesson(
            scenario_id="s1", archetype="VP Engineering",
            remember_this="lesson 1", scope_tags=["a"],
        )
        lessons.write_lesson(
            scenario_id="s2", archetype="VP Engineering",
            remember_this="lesson 2", scope_tags=["b"],
        )
        result = lessons.list_lessons()
        self.assertEqual(len(result), 2)


class TestRankLessons(LessonsTestBase):

    def test_exact_archetype_match_scores_higher(self):
        # Lesson A: exact match
        self._write_raw_lesson({
            "lesson_id": "a",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scenario_id": "s1",
            "archetype": "Security Engineer",
            "remember_this": "auth rule",
            "scope_tags": ["csrf"],
            "agent_response": "",
            "expected_response": "",
        })
        # Lesson B: no archetype overlap
        self._write_raw_lesson({
            "lesson_id": "b",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scenario_id": "s2",
            "archetype": "Frontend Developer",
            "remember_this": "css rule",
            "scope_tags": ["csrf"],
            "agent_response": "",
            "expected_response": "",
        })
        top = lessons.rank_lessons("Security Engineer", ["csrf"])
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].lesson_id, "a")

    def test_recency_decay_reduces_old_lessons(self):
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=365)).isoformat()
        recent = now.isoformat()
        self._write_raw_lesson({
            "lesson_id": "old",
            "created_at": old,
            "scenario_id": "s1",
            "archetype": "X",
            "remember_this": "old",
            "scope_tags": ["a"],
            "agent_response": "",
            "expected_response": "",
        })
        self._write_raw_lesson({
            "lesson_id": "new",
            "created_at": recent,
            "scenario_id": "s2",
            "archetype": "X",
            "remember_this": "new",
            "scope_tags": ["a"],
            "agent_response": "",
            "expected_response": "",
        })
        top = lessons.rank_lessons("X", ["a"])
        self.assertEqual(top[0].lesson_id, "new")

    def test_returns_at_most_3(self):
        for i in range(10):
            self._write_raw_lesson({
                "lesson_id": f"l{i}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "scenario_id": f"s{i}",
                "archetype": "X",
                "remember_this": f"lesson {i}",
                "scope_tags": ["a"],
                "agent_response": "",
                "expected_response": "",
            })
        top = lessons.rank_lessons("X", ["a"])
        self.assertLessEqual(len(top), 3)

    def test_zero_score_lessons_excluded(self):
        """Lesson with no archetype + no keyword overlap should not appear."""
        self._write_raw_lesson({
            "lesson_id": "unrelated",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scenario_id": "s1",
            "archetype": "Frontend Developer",
            "remember_this": "css",
            "scope_tags": ["style"],
            "agent_response": "",
            "expected_response": "",
        })
        top = lessons.rank_lessons("Security Engineer", ["csrf"])
        self.assertEqual(top, [])


class TestFormatForInjection(LessonsTestBase):

    def test_empty_returns_empty_string(self):
        self.assertEqual(lessons.format_for_injection([]), "")

    def test_includes_past_lessons_header(self):
        lesson = lessons.Lesson(
            lesson_id="l1", scenario_id="s1", archetype="X",
            remember_this="thing", scope_tags=["a"],
        )
        result = lessons.format_for_injection([lesson])
        self.assertIn("## PAST LESSONS", result)
        self.assertIn("thing", result)
        self.assertIn("s1", result)

    def test_respects_token_budget(self):
        """With huge lessons, format should truncate rather than blow budget."""
        big_text = "x" * 20000
        big_lessons = [
            lessons.Lesson(
                lesson_id=f"l{i}", scenario_id=f"s{i}", archetype="X",
                remember_this=big_text, scope_tags=["a"],
            )
            for i in range(5)
        ]
        result = lessons.format_for_injection(big_lessons)
        # 2K tokens * 4 chars = 8000 chars budget (plus header overhead)
        self.assertLess(len(result), 10000)


class TestArchetypeMatch(unittest.TestCase):

    def test_exact_match_is_1(self):
        self.assertEqual(lessons._archetype_match("VP Engineering", "VP Engineering"), 1.0)

    def test_partial_overlap_is_point3(self):
        # "Security Engineer" vs "Staff Engineer" — share "engineer"
        score = lessons._archetype_match("Security Engineer", "Staff Engineer")
        self.assertEqual(score, 0.3)

    def test_no_overlap_is_0(self):
        self.assertEqual(lessons._archetype_match("Frontend", "Backend"), 0.0)

    def test_case_insensitive(self):
        self.assertEqual(lessons._archetype_match("VP eng", "vp ENG"), 1.0)


class TestScopeOverlap(unittest.TestCase):

    def test_identical_tags_jaccard_is_1(self):
        self.assertEqual(lessons._scope_overlap(["a", "b"], ["a", "b"]), 1.0)

    def test_half_overlap(self):
        self.assertEqual(lessons._scope_overlap(["a", "b"], ["a", "c"]), 1 / 3)

    def test_no_overlap(self):
        self.assertEqual(lessons._scope_overlap(["a"], ["b"]), 0.0)

    def test_empty_lists(self):
        self.assertEqual(lessons._scope_overlap([], ["a"]), 0.0)


class TestRecencyDecay(unittest.TestCase):

    def test_now_is_close_to_1(self):
        now = datetime.now(timezone.utc).isoformat()
        self.assertGreater(lessons._recency_decay(now), 0.99)

    def test_90_days_is_about_half(self):
        past = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        decay = lessons._recency_decay(past)
        self.assertAlmostEqual(decay, math.exp(-1), delta=0.01)

    def test_unparseable_is_neutral(self):
        self.assertEqual(lessons._recency_decay("not a date"), 0.5)
