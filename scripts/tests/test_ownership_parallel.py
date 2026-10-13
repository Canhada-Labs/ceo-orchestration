"""Positive and negative controls for the parallel ownership adapter."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("ownership_parallel", Path(__file__).with_name("ownership-parallel.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class TestOwnershipParallel(unittest.TestCase):
    def result(self, rows, summary="GREEN=1  RED=1  AMBIG=0  HARNESS-ERR=0", rc=1):
        return subprocess.CompletedProcess([], rc, rows + "\n" + summary + "\n", "")

    def test_preserves_expected_red(self):
        rows = "OWN-0001 GREEN details\nOWN-0002 RED details"
        self.assertEqual(adapter.checked_rows(["OWN-0001", "OWN-0002"], self.result(rows)), rows.splitlines())

    def test_rejects_missing_duplicate_and_foreign_cells(self):
        for rows in ["OWN-0001 GREEN", "OWN-0001 GREEN\nOWN-0001 RED", "OWN-0001 GREEN\nOWN-0003 RED"]:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                adapter.checked_rows(["OWN-0001", "OWN-0002"], self.result(rows))

    def test_rejects_bad_summary_and_incoherent_exit(self):
        rows = "OWN-0001 GREEN\nOWN-0002 RED"
        for summary, rc in [("", 1), ("GREEN=2  RED=0  AMBIG=0  HARNESS-ERR=0", 1),
                            ("GREEN=1  RED=1  AMBIG=0  HARNESS-ERR=1", 1),
                            ("GREEN=1  RED=1  AMBIG=0  HARNESS-ERR=0", 0),
                            ("GREEN=1  RED=1  AMBIG=0  HARNESS-ERR=0", 2)]:
            with self.subTest(summary=summary, rc=rc), self.assertRaises(ValueError):
                adapter.checked_rows(["OWN-0001", "OWN-0002"], self.result(rows, summary, rc))

    def test_rejects_unexpected_status_even_on_expected_red_cell(self):
        for status in ["TIMEOUT", "ESCAPE", "AMBIG"]:
            with self.subTest(status=status), self.assertRaises(ValueError):
                adapter.checked_rows(["OWN-0001", "OWN-0002"], self.result("OWN-0001 GREEN\nOWN-0002 " + status))

    def test_real_subprocess_and_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "harness.sh"
            harness.write_text('echo "OWN-0001 GREEN"; echo "GREEN=1  RED=0  AMBIG=0  HARNESS-ERR=0"\n')
            self.assertEqual(adapter.run_chunk(harness, ["OWN-0001"], 3), ["OWN-0001 GREEN"])
            harness.write_text("sleep 30\n")
            with self.assertRaisesRegex(ValueError, "timed out"):
                adapter.run_chunk(harness, ["OWN-0001"], 1)


if __name__ == "__main__":
    unittest.main()
