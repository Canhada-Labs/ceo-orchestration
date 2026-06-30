"""Concurrent-write test for lessons.write_lesson.

Sprint 5 A.3 acceptance: 4 processes × 25 lessons = 100 valid JSONL
lines in audit-log, no partial writes. Covers the filelock around the
lesson file write + the audit emitter's internal lock.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import unittest

import pytest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))


def _worker(worker_id: int, count: int, lessons_dir: str, log_path: str) -> int:
    """Run in a child process. Returns number of lessons successfully written."""
    os.environ["CEO_AUDIT_SYNC_MODE"] = "1"   # S220: force sync writes so the spool flushes before asserts (CI)
    os.environ["CEO_LESSONS_DIR"] = lessons_dir
    os.environ["CEO_AUDIT_LOG_PATH"] = log_path
    os.environ["CEO_AUDIT_LOG_LOCK"] = log_path + ".lock"
    os.environ["CEO_AUDIT_LOG_ERR"] = log_path + ".err"
    os.environ["CEO_AUDIT_LOG_DIR"] = str(Path(log_path).parent)

    # Import inside the worker to pick up the env
    if str(Path(_SCRIPTS)) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    import lessons  # noqa: E402

    ok = 0
    for i in range(count):
        try:
            lessons.write_lesson(
                scenario_id=f"w{worker_id}-scen-{i:03d}",
                archetype=f"archetype-{worker_id}",
                remember_this=f"lesson from worker {worker_id} iter {i}",
                scope_tags=[f"tag{worker_id}", f"iter{i}"],
            )
            ok += 1
        except Exception:
            pass
    return ok


class LessonsConcurrencyTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lessons-conc-test-"))
        self.lessons_dir = self.tmp / "lessons"
        self.log_path = self.tmp / "audit-log.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @pytest.mark.serial
    def test_four_workers_twentyfive_lessons_each(self):
        """4 × 25 = 100 concurrent writes. All audit JSONL lines must
        be valid (no partial writes) and count must match."""
        n_workers = 4
        per_worker = 25

        ctx = mp.get_context("spawn")
        with ctx.Pool(n_workers) as pool:
            results = pool.starmap(
                _worker,
                [
                    (w, per_worker, str(self.lessons_dir), str(self.log_path))
                    for w in range(n_workers)
                ],
            )

        total_written = sum(results)
        self.assertEqual(
            total_written,
            n_workers * per_worker,
            f"some workers failed: per-worker {results}",
        )

        # Verify every audit log line parses as valid JSON
        self.assertTrue(self.log_path.exists(), "audit log was never created")
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        non_blank = [l for l in lines if l.strip()]

        self.assertEqual(
            len(non_blank),
            n_workers * per_worker,
            "audit log line count does not match written lesson count",
        )

        # Every line must parse as JSON with action=lesson_write
        for i, raw in enumerate(non_blank):
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as e:
                self.fail(f"line {i} is not valid JSON (partial write?): {e}")
            self.assertEqual(event.get("action"), "lesson_write")

        # Lesson files on disk: exactly 100, each a valid JSON
        json_files = sorted(self.lessons_dir.glob("*.json"))
        self.assertEqual(len(json_files), n_workers * per_worker)
        for p in json_files:
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                self.fail(f"lesson file {p.name} not valid JSON: {e}")


if __name__ == "__main__":
    unittest.main()
