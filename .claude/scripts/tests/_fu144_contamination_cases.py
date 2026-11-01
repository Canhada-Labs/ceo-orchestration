"""Regression cases imported by the Rule 2 test module for Onda 2B."""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import check_contamination as cc
import _contamination_inventory as inventory
from _lib.testing import TestEnvContext
from _subprocess_helpers import run_in_process_group


class TestRuleOneInventoryFu144(TestEnvContext):
    """Rule 1 must read index subjects, never their symlink targets."""

    def setUp(self) -> None:
        super().setUp()
        self.root = Path(tempfile.mkdtemp(prefix="fu144-contam-")).resolve()
        run_in_process_group(
            ["git", "init", "-q"], timeout=10, cwd=str(self.root),
            check=True, capture_output=True,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        super().tearDown()

    def _add(self, rel: str) -> None:
        run_in_process_group(
            ["git", "add", "--", rel], timeout=10, cwd=str(self.root),
            check=True, capture_output=True,
        )

    def test_fu144_symlink_payload_is_scanned_not_clean_target(self) -> None:
        target = self.root / "clean-target"
        target.write_text("clean", encoding="utf-8")
        (self.root / "link.md").symlink_to("example owner")
        self._add("clean-target")
        self._add("link.md")
        violations = cc.scan(self.root)
        self.assertEqual([item.name for item in violations], ["link.md"])

    def test_fu144_invalid_index_name_is_fatal_before_allowlist(self) -> None:
        (self.root / "docs").mkdir()
        raw = os.fsencode(self.root) + b"/docs/a\xff.md"
        fd = os.open(raw, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        self._add("docs")
        with self.assertRaises(inventory.RuleOneInputError) as raised:
            inventory._index(self.root)
        self.assertIn("not valid UTF-8", str(raised.exception))
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = cc.main(["--root", str(self.root)])
        self.assertEqual(rc, 2)
        self.assertNotIn("No contamination", stdout.getvalue())
        self.assertIn("FATAL", stderr.getvalue())

    def test_fu144_index_failure_cannot_return_clean(self) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        result = mock.Mock(returncode=1, stdout=b"")
        with mock.patch.object(cc, "report_personal_paths", return_value=0), \
                mock.patch("_contamination_inventory.subprocess.run", return_value=result), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = cc.main(["--root", str(self.root)])
        self.assertEqual(rc, 2)
        self.assertNotIn("No contamination", stdout.getvalue())
        self.assertIn("FATAL", stderr.getvalue())

    def test_fu144_unreadable_blob_cannot_return_clean(self) -> None:
        (self.root / "blocked.md").write_text("clean", encoding="utf-8")
        self._add("blocked.md")
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch("_contamination_inventory._read_regular",
                        side_effect=PermissionError("blocked")), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            rc = cc.main(["--root", str(self.root)])
        self.assertEqual(rc, 2)
        self.assertNotIn("No contamination", stdout.getvalue())
        self.assertIn("FATAL", stderr.getvalue())

    def test_fu144_only_gitlink_is_not_a_blob_subject(self) -> None:
        sha = "1" * 40
        run_in_process_group(
            ["git", "update-index", "--add", "--cacheinfo", "160000,%s,vendor" % sha],
            timeout=10, cwd=str(self.root), check=True, capture_output=True,
        )
        self.assertEqual(cc.scan(self.root), [])
