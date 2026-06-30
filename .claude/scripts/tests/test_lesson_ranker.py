"""Tests for lesson_ranker.py (PLAN-009 Phase 5)."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import lesson_ranker as lr  # noqa: E402


@dataclass
class FakeLesson:
    hit_count: int = 0
    miss_count: int = 0
    last_outcome_at: str = ""
    last_inference_mode: str = ""


class TestEffectiveness(unittest.TestCase):
    def test_zero_outcomes_is_none(self):
        self.assertIsNone(lr.effectiveness(0, 0))

    def test_only_hits_is_one(self):
        self.assertEqual(lr.effectiveness(5, 0), 1.0)

    def test_only_misses_is_zero(self):
        self.assertEqual(lr.effectiveness(0, 5), 0.0)

    def test_mixed(self):
        self.assertAlmostEqual(lr.effectiveness(2, 3), 0.4)


class TestRankByEffectiveness(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(lr.rank_by_effectiveness([]), [])

    def test_sorts_descending_by_effectiveness(self):
        lessons = [
            FakeLesson(hit_count=1, miss_count=9),  # 0.1
            FakeLesson(hit_count=9, miss_count=1),  # 0.9
            FakeLesson(hit_count=5, miss_count=5),  # 0.5
        ]
        ranked = lr.rank_by_effectiveness(lessons)
        self.assertAlmostEqual(ranked[0][1], 0.9)
        self.assertAlmostEqual(ranked[1][1], 0.5)
        self.assertAlmostEqual(ranked[2][1], 0.1)

    def test_none_sorts_last(self):
        lessons = [
            FakeLesson(hit_count=0, miss_count=0),  # None
            FakeLesson(hit_count=5, miss_count=5),  # 0.5
        ]
        ranked = lr.rank_by_effectiveness(lessons)
        self.assertIsNotNone(ranked[0][1])
        self.assertIsNone(ranked[1][1])

    def test_inference_mode_filter_excludes(self):
        lessons = [
            FakeLesson(hit_count=5, miss_count=0, last_inference_mode="window-only"),
            FakeLesson(hit_count=1, miss_count=0, last_inference_mode="session-correlated"),
        ]
        ranked = lr.rank_by_effectiveness(
            lessons, inference_mode_filter={"session-correlated"},
        )
        self.assertEqual(len(ranked), 1)

    def test_inference_mode_filter_none_allows_all(self):
        lessons = [
            FakeLesson(hit_count=1, miss_count=0, last_inference_mode="window-only"),
            FakeLesson(hit_count=1, miss_count=0, last_inference_mode=""),
        ]
        ranked = lr.rank_by_effectiveness(lessons, inference_mode_filter=None)
        self.assertEqual(len(ranked), 2)


if __name__ == "__main__":
    unittest.main()
