"""Tests for prune-lessons.py dry-run CLI (ADR-017)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_PRUNE_PATH = _SCRIPTS_DIR / "prune-lessons.py"

sys.path.insert(0, str(_SCRIPTS_DIR))
import lessons as _lessons  # noqa: E402

# Load prune-lessons.py as module
_spec = importlib.util.spec_from_file_location("prune_lessons", _PRUNE_PATH)
_prune = importlib.util.module_from_spec(_spec)
sys.modules["prune_lessons"] = _prune
_spec.loader.exec_module(_prune)


class TestFindCandidates(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add(self, hits, misses, tag="a"):
        p = _lessons.write_lesson(
            scenario_id=f"s-{hits}-{misses}-{tag}",
            archetype="vp-eng",
            remember_this=f"h{hits}m{misses}",
            scope_tags=[tag],
            base_dir=self.tmpdir,
        )
        for _ in range(hits):
            _lessons.record_outcome(p.stem, hit=True, base_dir=self.tmpdir)
        for _ in range(misses):
            _lessons.record_outcome(p.stem, hit=False, base_dir=self.tmpdir)
        return p

    def test_below_sample_size_not_flagged(self):
        self._add(hits=0, misses=4)  # n=4 < 5
        self.assertEqual(len(_prune.find_candidates(self.tmpdir)), 0)

    def test_high_hit_rate_not_flagged(self):
        self._add(hits=8, misses=2)  # rate=0.8
        self.assertEqual(len(_prune.find_candidates(self.tmpdir)), 0)

    def test_low_hit_rate_flagged(self):
        self._add(hits=1, misses=9)  # rate=0.1
        candidates = _prune.find_candidates(self.tmpdir)
        self.assertEqual(len(candidates), 1)

    def test_edge_exactly_at_threshold(self):
        # n=5, hit_rate=0.2 → below 0.3, flagged
        self._add(hits=1, misses=4)
        self.assertEqual(len(_prune.find_candidates(self.tmpdir)), 1)

    def test_edge_n_exactly_5_rate_exactly_0_3(self):
        # hit=2, miss=3 → 2/5=0.4 NOT flagged (above 0.3)
        self._add(hits=2, misses=3)
        self.assertEqual(len(_prune.find_candidates(self.tmpdir)), 0)


class TestPruneCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_execute_requires_env_var(self):
        # No env var set → refuse
        os.environ.pop("CEO_PRUNE_EXECUTE", None)
        rc = _prune.main(["--execute", "--base-dir", self.tmpdir])
        self.assertEqual(rc, 10)

    def test_dry_run_success(self):
        rc = _prune.main(["--dry-run", "--base-dir", self.tmpdir])
        self.assertEqual(rc, 0)

    def test_json_output(self):
        p = _lessons.write_lesson(
            scenario_id="weak",
            archetype="vp-eng",
            remember_this="l",
            scope_tags=["a"],
            base_dir=self.tmpdir,
        )
        for _ in range(8):
            _lessons.record_outcome(p.stem, hit=False, base_dir=self.tmpdir)
        _lessons.record_outcome(p.stem, hit=True, base_dir=self.tmpdir)
        # Use subprocess so we capture stdout
        result = subprocess.run(
            [sys.executable, str(_PRUNE_PATH), "--json", "--base-dir", self.tmpdir],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        out = json.loads(result.stdout)
        self.assertEqual(out["mode"], "dry-run")
        self.assertEqual(out["candidate_count"], 1)


class TestPruneExecute(unittest.TestCase):
    """Sprint 8 Phase 4: --execute path with env-gate + archive + cap."""

    def setUp(self):
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmpdir = tempfile.mkdtemp()
        # Seed N weak lessons
        self.lesson_ids = []
        for i in range(5):
            p = _lessons.write_lesson(
                scenario_id=f"weak-{i}",
                archetype="vp-eng",
                remember_this=f"l{i}",
                scope_tags=["a"],
                base_dir=self.tmpdir,
            )
            self.lesson_ids.append(p.stem)
            for _ in range(9):
                _lessons.record_outcome(p.stem, hit=False, base_dir=self.tmpdir)
            _lessons.record_outcome(p.stem, hit=True, base_dir=self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        os.environ.pop("CEO_PRUNE_EXECUTE", None)

    def test_execute_with_env_archives_up_to_cap(self):
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        rc = _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "2"])
        self.assertEqual(rc, 0)
        # 2 lessons archived, 3 remain in live lessons/
        live = list(Path(self.tmpdir).glob("*.json"))
        self.assertEqual(len(live), 3)
        # archive dir has today's subdir with 2 files + receipt
        archive_root = Path(self.tmpdir) / "archive"
        self.assertTrue(archive_root.is_dir())
        date_dirs = [d for d in archive_root.iterdir() if d.is_dir()]
        self.assertEqual(len(date_dirs), 1)
        archived_files = [f for f in date_dirs[0].iterdir() if f.suffix == ".json" and not f.name.startswith("prune-receipt")]
        self.assertEqual(len(archived_files), 2)
        receipts = list(date_dirs[0].glob("prune-receipt-*.json"))
        self.assertEqual(len(receipts), 1)

    def test_execute_plan_only_no_side_effects(self):
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        rc = _prune.main(["--execute", "--plan-only", "--base-dir", self.tmpdir, "--max-archive", "3"])
        self.assertEqual(rc, 0)
        # All 5 still present
        live = list(Path(self.tmpdir).glob("*.json"))
        self.assertEqual(len(live), 5)
        # No archive dir
        archive_root = Path(self.tmpdir) / "archive"
        self.assertFalse(archive_root.exists())

    def test_execute_archived_has_metadata(self):
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "1"])
        date_dirs = list((Path(self.tmpdir) / "archive").iterdir())
        archived = [f for f in date_dirs[0].iterdir() if f.suffix == ".json" and not f.name.startswith("prune-receipt")]
        data = json.loads(archived[0].read_text())
        self.assertIn("archived_at", data)
        self.assertIn("original_path", data)

    def test_execute_idempotent_when_nothing_left(self):
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        # First run archives 5
        _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "10"])
        # Second run: no candidates, exits 0 cleanly
        rc = _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "10"])
        self.assertEqual(rc, 0)
        live = list(Path(self.tmpdir).glob("*.json"))
        self.assertEqual(len(live), 0)

    def test_execute_negative_max_archive_rejected(self):
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        rc = _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "-1"])
        self.assertEqual(rc, 2)

    def test_execute_emits_lesson_archived_audit_events(self):
        """Sprint 8: one lesson_archived event per archival."""
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        # Need to isolate audit log to a temp location
        audit_log = Path(self.tmpdir) / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = self.tmpdir
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(Path(self.tmpdir) / "audit.lock")
        try:
            _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "3"])
            self.assertTrue(audit_log.exists())
            entries = [json.loads(l) for l in audit_log.read_text().splitlines() if l.strip()]
            archived_events = [e for e in entries if e.get("action") == "lesson_archived"]
            self.assertEqual(len(archived_events), 3)
            for e in archived_events:
                self.assertEqual(e["reason"], "low_hit_rate")
                self.assertIn("archive_path", e)
        finally:
            for key in ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_LOCK"):
                os.environ.pop(key, None)


# ---------------------------------------------------------------------------
# PLAN-009 P2.1 (ADR-020) — threshold flags + AND semantics + safety guard
# ---------------------------------------------------------------------------


class TestADR020Thresholds(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add(self, hits, misses, tag="a"):
        p = _lessons.write_lesson(
            scenario_id=f"s-{hits}-{misses}-{tag}",
            archetype="vp-eng",
            remember_this=f"h{hits}m{misses}",
            scope_tags=[tag],
            base_dir=self.tmpdir,
        )
        for _ in range(hits):
            _lessons.record_outcome(p.stem, hit=True, base_dir=self.tmpdir)
        for _ in range(misses):
            _lessons.record_outcome(p.stem, hit=False, base_dir=self.tmpdir)
        return p

    def test_default_preserves_v1_behavior(self):
        """Default flags must equal the ADR-017 v1 behavior."""
        self._add(hits=1, misses=9)  # v1 prunes this (rate=0.1 < 0.3)
        self.assertEqual(len(_prune.find_candidates(self.tmpdir)), 1)

    def test_loose_miss_ratio_finds_more(self):
        """--min-miss-ratio 0.5 should catch borderline cases."""
        self._add(hits=3, misses=3)  # miss_ratio=0.5
        # Default 0.7 skips this; 0.5 catches it
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_miss_ratio=0.7)), 0
        )
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_miss_ratio=0.5)), 1
        )

    def test_strict_miss_ratio_filters_out(self):
        """Higher --min-miss-ratio must filter out mid-rate lessons."""
        self._add(hits=3, misses=7)  # miss_ratio=0.7 (default match)
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_miss_ratio=0.7)), 1
        )
        # Stricter threshold excludes it
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_miss_ratio=0.9)), 0
        )

    def test_min_age_days_excludes_recent(self):
        """--min-age-days should exclude lessons created after the cutoff."""
        # Lesson is brand-new (created_at=now)
        self._add(hits=1, misses=9)
        # Requesting age > 7 days should exclude it
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_age_days=7)), 0
        )
        # age 0 keeps the default behavior
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_age_days=0)), 1
        )

    def test_and_semantics_conjunction(self):
        """All filters must vote yes; one filter's no rejects the candidate."""
        self._add(hits=1, misses=9)
        # miss_ratio default 0.7 → match; but min_age_days=30 → fail (brand new)
        self.assertEqual(
            len(_prune.find_candidates(
                self.tmpdir, min_miss_ratio=0.7, min_age_days=30,
            )),
            0,
        )

    def test_unparseable_created_at_fails_safe(self):
        """Lessons with garbage created_at are kept when min_age_days > 0."""
        p = self._add(hits=1, misses=9)
        # Corrupt the timestamp
        data = json.loads(p.read_text(encoding="utf-8"))
        data["created_at"] = "NOT-A-TIMESTAMP"
        p.write_text(json.dumps(data), encoding="utf-8")
        # Filter votes "unknown age" → exclude (fail-safe: don't prune)
        self.assertEqual(
            len(_prune.find_candidates(self.tmpdir, min_age_days=1)), 0
        )


class TestADR020SafetyGuard(unittest.TestCase):
    """Dangerous threshold guard — requires --force-dangerous-threshold."""

    def test_cli_rejects_below_0_1(self):
        env = os.environ.copy()
        result = subprocess.run(
            [sys.executable, str(_PRUNE_PATH), "--min-miss-ratio", "0.05"],
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(result.returncode, 11)
        self.assertIn("safety guard", result.stderr)
        self.assertIn("ADR-020", result.stderr)

    def test_cli_allows_below_0_1_with_force(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [
                    sys.executable, str(_PRUNE_PATH),
                    "--min-miss-ratio", "0.05",
                    "--force-dangerous-threshold",
                    "--base-dir", td,
                ],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)

    def test_cli_allows_default(self):
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [sys.executable, str(_PRUNE_PATH), "--base-dir", td],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
