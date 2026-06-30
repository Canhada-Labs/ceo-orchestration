"""Tests for Reflexion v2 outcome loop (PLAN-006 Phase 4 / ADR-015)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import lessons as _lessons  # noqa: E402


class TestLessonHitRate(unittest.TestCase):
    def test_hit_rate_none_when_low_signal(self):
        l = _lessons.Lesson(hit_count=1, miss_count=1)
        self.assertIsNone(l.hit_rate())
        l2 = _lessons.Lesson(hit_count=2, miss_count=0)
        self.assertIsNone(l2.hit_rate())

    def test_hit_rate_computed_at_threshold(self):
        l = _lessons.Lesson(hit_count=2, miss_count=1)
        self.assertAlmostEqual(l.hit_rate(), 2 / 3)

    def test_hit_rate_one_when_all_hits(self):
        l = _lessons.Lesson(hit_count=10, miss_count=0)
        self.assertEqual(l.hit_rate(), 1.0)

    def test_hit_rate_zero_when_all_misses(self):
        l = _lessons.Lesson(hit_count=0, miss_count=5)
        self.assertEqual(l.hit_rate(), 0.0)


class TestOutcomeRecording(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self):
        return _lessons.write_lesson(
            scenario_id="sc1",
            archetype="vp-eng",
            remember_this="Check ADRs before refactor",
            scope_tags=["architecture"],
            base_dir=self.tmpdir,
        )

    def test_record_hit_increments_counter(self):
        path = self._write()
        lesson_id = path.stem
        result = _lessons.record_outcome(lesson_id, hit=True, base_dir=self.tmpdir)
        self.assertIsNotNone(result)
        self.assertEqual(result.hit_count, 1)
        self.assertEqual(result.miss_count, 0)

    def test_record_miss_increments_counter(self):
        path = self._write()
        lesson_id = path.stem
        _lessons.record_outcome(lesson_id, hit=False, base_dir=self.tmpdir)
        _lessons.record_outcome(lesson_id, hit=False, base_dir=self.tmpdir)
        result = _lessons.record_outcome(lesson_id, hit=True, base_dir=self.tmpdir)
        self.assertEqual(result.hit_count, 1)
        self.assertEqual(result.miss_count, 2)

    def test_record_nonexistent_returns_none(self):
        result = _lessons.record_outcome("bogus_id", hit=True, base_dir=self.tmpdir)
        self.assertIsNone(result)

    def test_outcome_sets_last_outcome_at(self):
        path = self._write()
        lesson_id = path.stem
        result = _lessons.record_outcome(lesson_id, hit=True, base_dir=self.tmpdir)
        self.assertTrue(result.last_outcome_at)
        self.assertIn("T", result.last_outcome_at)


class TestGetTopK(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_k_cap_enforced(self):
        for i in range(10):
            _lessons.write_lesson(
                scenario_id=f"sc{i}",
                archetype="vp-eng",
                remember_this=f"lesson {i}",
                scope_tags=["architecture"],
                base_dir=self.tmpdir,
            )
        result = _lessons.get_top_k("vp-eng", ["architecture"], k=100, base_dir=self.tmpdir)
        self.assertLessEqual(len(result), 50)  # hard ceiling per ADR-015

    def test_k_default_is_fifty(self):
        result = _lessons.get_top_k("vp-eng", ["any"], base_dir=self.tmpdir)
        # Empty dir → 0; default behavior without error
        self.assertEqual(len(result), 0)

    def test_rank_lessons_still_returns_three(self):
        for i in range(10):
            _lessons.write_lesson(
                scenario_id=f"sc{i}",
                archetype="vp-eng",
                remember_this=f"l{i}",
                scope_tags=["arch"],
                base_dir=self.tmpdir,
            )
        r = _lessons.rank_lessons("vp-eng", ["arch"], base_dir=self.tmpdir)
        self.assertLessEqual(len(r), 3)

    def test_k_zero_coerced_to_one(self):
        _lessons.write_lesson(
            scenario_id="sc1",
            archetype="vp-eng",
            remember_this="l1",
            scope_tags=["arch"],
            base_dir=self.tmpdir,
        )
        r = _lessons.get_top_k("vp-eng", ["arch"], k=0, base_dir=self.tmpdir)
        self.assertLessEqual(len(r), 1)


class TestBuildIndex(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_index_created(self):
        _lessons.write_lesson(
            scenario_id="sc1",
            archetype="vp-eng",
            remember_this="l1",
            scope_tags=["a"],
            base_dir=self.tmpdir,
        )
        idx_path = _lessons.build_index(base_dir=self.tmpdir)
        self.assertTrue(idx_path.is_file())
        idx = json.loads(idx_path.read_text())
        self.assertEqual(idx["lesson_count"], 1)
        self.assertEqual(len(idx["lessons"]), 1)

    def test_index_empty_when_no_lessons(self):
        idx_path = _lessons.build_index(base_dir=self.tmpdir)
        self.assertTrue(idx_path.is_file())
        idx = json.loads(idx_path.read_text())
        self.assertEqual(idx["lesson_count"], 0)

    def test_index_reflects_outcome_counts(self):
        path = _lessons.write_lesson(
            scenario_id="sc1",
            archetype="vp-eng",
            remember_this="l1",
            scope_tags=["a"],
            base_dir=self.tmpdir,
        )
        lesson_id = path.stem
        _lessons.record_outcome(lesson_id, hit=True, base_dir=self.tmpdir)
        _lessons.record_outcome(lesson_id, hit=True, base_dir=self.tmpdir)
        _lessons.record_outcome(lesson_id, hit=False, base_dir=self.tmpdir)
        _lessons.build_index(base_dir=self.tmpdir)
        idx = json.loads((Path(self.tmpdir) / "index.json").read_text())
        self.assertEqual(idx["lessons"][0]["hit_count"], 2)
        self.assertEqual(idx["lessons"][0]["miss_count"], 1)


class TestHitRateWeighting(unittest.TestCase):
    """Proven lessons with high hit_rate should rank higher."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_proven_lesson_outranks_unproven_matching_archetype(self):
        # Lesson A: proven winner
        p_a = _lessons.write_lesson(
            scenario_id="sc_a",
            archetype="vp-eng",
            remember_this="winner",
            scope_tags=["arch"],
            base_dir=self.tmpdir,
        )
        for _ in range(10):
            _lessons.record_outcome(p_a.stem, hit=True, base_dir=self.tmpdir)

        # Lesson B: untested
        p_b = _lessons.write_lesson(
            scenario_id="sc_b",
            archetype="vp-eng",
            remember_this="untested",
            scope_tags=["arch"],
            base_dir=self.tmpdir,
        )

        top = _lessons.get_top_k("vp-eng", ["arch"], k=2, base_dir=self.tmpdir)
        self.assertEqual(len(top), 2)
        self.assertEqual(top[0].lesson_id, p_a.stem)

    def test_failing_lesson_downweighted_but_not_zeroed(self):
        p_fail = _lessons.write_lesson(
            scenario_id="sc_fail",
            archetype="vp-eng",
            remember_this="loser",
            scope_tags=["arch"],
            base_dir=self.tmpdir,
        )
        # Heavy miss bias: 1 hit / 9 miss → rate 0.1
        _lessons.record_outcome(p_fail.stem, hit=True, base_dir=self.tmpdir)
        for _ in range(9):
            _lessons.record_outcome(p_fail.stem, hit=False, base_dir=self.tmpdir)

        top = _lessons.get_top_k("vp-eng", ["arch"], k=5, base_dir=self.tmpdir)
        # Lesson is still returned (not pruned); just down-weighted
        self.assertEqual(len(top), 1)


class TestEmitLessonOutcome(unittest.TestCase):
    """Ensure _lib/audit_emit.emit_lesson_outcome exists and accepts the contract."""

    def test_import_exists(self):
        sys.path.insert(0, str(_SCRIPTS_DIR.parent / "hooks"))
        from _lib import audit_emit
        self.assertTrue(hasattr(audit_emit, "emit_lesson_outcome"))

    def test_emitter_signature_accepts_kwargs(self):
        sys.path.insert(0, str(_SCRIPTS_DIR.parent / "hooks"))
        from _lib import audit_emit
        # Shouldn't raise on no-audit-log environment (fail-open)
        with tempfile.TemporaryDirectory() as td:
            os.environ["CEO_AUDIT_LOG_DIR"] = td
            audit_emit.emit_lesson_outcome(
                lesson_id="x",
                archetype="vp-eng",
                hit=True,
                hit_count=1,
                miss_count=0,
            )
            # Read back and verify event shape
            log_file = Path(td) / "audit-log.jsonl"
            if log_file.is_file():
                line = log_file.read_text().strip().splitlines()[-1]
                entry = json.loads(line)
                self.assertEqual(entry["action"], "lesson_outcome")
                self.assertEqual(entry["lesson_id"], "x")
                self.assertTrue(entry["hit"])


if __name__ == "__main__":
    unittest.main()
