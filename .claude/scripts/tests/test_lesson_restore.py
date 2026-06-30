"""Tests for lesson-restore.py companion (PLAN-008 Phase 4b)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_RESTORE_PATH = _SCRIPTS_DIR / "lesson-restore.py"
_PRUNE_PATH = _SCRIPTS_DIR / "prune-lessons.py"

sys.path.insert(0, str(_SCRIPTS_DIR))
import lessons as _lessons  # noqa: E402

_spec = importlib.util.spec_from_file_location("lesson_restore", _RESTORE_PATH)
_restore = importlib.util.module_from_spec(_spec)
sys.modules["lesson_restore"] = _restore
_spec.loader.exec_module(_restore)

_pspec = importlib.util.spec_from_file_location("prune_lessons", _PRUNE_PATH)
_prune = importlib.util.module_from_spec(_pspec)
sys.modules["prune_lessons"] = _prune
_pspec.loader.exec_module(_prune)


class TestLessonRestore(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Seed 1 weak lesson + archive it
        p = _lessons.write_lesson(
            scenario_id="weak",
            archetype="vp-eng",
            remember_this="l",
            scope_tags=["tag"],
            base_dir=self.tmpdir,
        )
        self.lesson_id = p.stem
        for _ in range(9):
            _lessons.record_outcome(p.stem, hit=False, base_dir=self.tmpdir)
        _lessons.record_outcome(p.stem, hit=True, base_dir=self.tmpdir)
        os.environ["CEO_PRUNE_EXECUTE"] = "1"
        _prune.main(["--execute", "--base-dir", self.tmpdir, "--max-archive", "5"])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        os.environ.pop("CEO_PRUNE_EXECUTE", None)

    def test_restore_moves_file_back_and_strips_metadata(self):
        rc = _restore.main([self.lesson_id, "--base-dir", self.tmpdir])
        self.assertEqual(rc, 0)
        live = Path(self.tmpdir) / f"{self.lesson_id}.json"
        self.assertTrue(live.is_file())
        data = json.loads(live.read_text())
        self.assertNotIn("archived_at", data)
        self.assertNotIn("original_path", data)

    def test_restore_refuses_when_live_copy_exists(self):
        # Put a colliding live copy
        (Path(self.tmpdir) / f"{self.lesson_id}.json").write_text('{"x":1}\n')
        rc = _restore.main([self.lesson_id, "--base-dir", self.tmpdir])
        self.assertEqual(rc, 4)

    def test_restore_unknown_id(self):
        rc = _restore.main(["nonexistent", "--base-dir", self.tmpdir])
        self.assertEqual(rc, 3)

    def test_list_shows_archived(self):
        entries = _restore.list_archived(self.tmpdir)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["lesson_id"], self.lesson_id)

    def test_list_skips_receipt_files(self):
        entries = _restore.list_archived(self.tmpdir)
        for e in entries:
            self.assertFalse(e["lesson_id"].startswith("prune-receipt"))

    def test_restore_removes_archive_file(self):
        archive_root = Path(self.tmpdir) / "archive"
        self.assertTrue(any(archive_root.rglob(f"{self.lesson_id}.json")))
        _restore.main([self.lesson_id, "--base-dir", self.tmpdir])
        self.assertFalse(any(archive_root.rglob(f"{self.lesson_id}.json")))


if __name__ == "__main__":
    unittest.main()
