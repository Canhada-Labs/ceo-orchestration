"""Unit tests for emit_architect_outcome.py (PLAN-009 P3.1)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402

import emit_architect_outcome as eao  # noqa: E402


class TestInferOutcome(unittest.TestCase):
    """Inference rule: session + window both required."""

    def _ts(self, offset_min: int) -> str:
        dt = datetime.now(timezone.utc) + timedelta(minutes=offset_min)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_no_events_in_window_is_hit(self):
        spawn_end = datetime.now(timezone.utc)
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=[]), "hit"
        )

    def test_veto_in_session_and_window_is_miss(self):
        spawn_end = datetime.now(timezone.utc)
        events = [
            {"action": "veto_triggered", "session_id": "sess-A",
             "ts": self._ts(3)},
        ]
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=events), "miss"
        )

    def test_veto_different_session_no_miss(self):
        """Session_id mismatch → not attributed (resists attribution attack)."""
        spawn_end = datetime.now(timezone.utc)
        events = [
            {"action": "veto_triggered", "session_id": "OTHER",
             "ts": self._ts(3)},
        ]
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=events), "hit"
        )

    def test_veto_outside_window_no_miss(self):
        """Event 30 min after spawn_end → outside 10min window → hit."""
        spawn_end = datetime.now(timezone.utc)
        events = [
            {"action": "veto_triggered", "session_id": "sess-A",
             "ts": self._ts(30)},
        ]
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=events), "hit"
        )

    def test_confidence_gate_fail_is_miss(self):
        spawn_end = datetime.now(timezone.utc)
        events = [
            {"action": "confidence_gate", "session_id": "sess-A",
             "ts": self._ts(1), "fail_count": 2},
        ]
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=events), "miss"
        )

    def test_confidence_gate_zero_fails_is_hit(self):
        spawn_end = datetime.now(timezone.utc)
        events = [
            {"action": "confidence_gate", "session_id": "sess-A",
             "ts": self._ts(1), "fail_count": 0},
        ]
        self.assertEqual(
            eao.infer_outcome("sess-A", spawn_end, events=events), "hit"
        )


class TestConsumerValidation(TestEnvContext):
    """PLAN-009 P3.2 — closed consumer enum."""

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(_HOOKS_DIR.parent / "scripts"))
        import lessons as _l
        self._lessons = _l
        self.tmp = tempfile.mkdtemp()
        self.lesson_path = _l.write_lesson(
            scenario_id="t1", archetype="vp-eng",
            remember_this="x", scope_tags=["a"],
            base_dir=self.tmp,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_benchmark_consumer_allowed(self):
        out = self._lessons.record_outcome(
            self.lesson_path.stem, hit=True,
            base_dir=self.tmp, consumer="benchmark",
        )
        self.assertIsNotNone(out)

    def test_architect_consumer_allowed(self):
        out = self._lessons.record_outcome(
            self.lesson_path.stem, hit=False,
            base_dir=self.tmp, consumer="architect",
        )
        self.assertIsNotNone(out)

    def test_unknown_consumer_raises(self):
        with self.assertRaises(ValueError) as cm:
            self._lessons.record_outcome(
                self.lesson_path.stem, hit=True,
                base_dir=self.tmp, consumer="hacker",
            )
        self.assertIn("hacker", str(cm.exception))
        self.assertIn("SPEC v1 amendment", str(cm.exception))


class TestUndoOutcome(TestEnvContext):
    """PLAN-009 P3.3 — admin CLI to reverse a bad attribution."""

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(_HOOKS_DIR.parent / "scripts"))
        import lessons as _l
        self._lessons = _l
        self.tmp = tempfile.mkdtemp()
        self.lesson_path = _l.write_lesson(
            scenario_id="u1", archetype="vp-eng",
            remember_this="u", scope_tags=["a"],
            base_dir=self.tmp,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    def test_undo_decrements_hit(self):
        self._lessons.record_outcome(
            self.lesson_path.stem, hit=True,
            base_dir=self.tmp, consumer="architect",
        )
        result = self._lessons.undo_outcome(
            self.lesson_path.stem, consumer="architect", base_dir=self.tmp,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.hit_count, 0)

    def test_undo_at_zero_returns_none(self):
        result = self._lessons.undo_outcome(
            self.lesson_path.stem, consumer="architect", base_dir=self.tmp,
        )
        self.assertIsNone(result)

    def test_undo_rejects_unknown_consumer(self):
        with self.assertRaises(ValueError):
            self._lessons.undo_outcome(
                self.lesson_path.stem, consumer="hacker", base_dir=self.tmp,
            )


if __name__ == "__main__":
    unittest.main()
