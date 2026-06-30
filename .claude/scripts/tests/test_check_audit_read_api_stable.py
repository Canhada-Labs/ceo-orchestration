"""Tests for check-audit-read-api-stable.py (PLAN-014 Phase F.0).

Covers:
- Happy-path: baseline intact against real repo
- Missing baseline function → exit 1
- File missing → exit 2
- Syntax error → exit 2
- Additive-only functions allowed (no false-fail)
- Private functions ignored (_ prefix)
- Verbose vs non-verbose output shapes
- JSON mode output structure

Imports the script via importlib.util (hyphens in filename).
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "check-audit-read-api-stable.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("check_audit_read_api_stable", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCheckAuditReadApiStable(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_mod()
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-read-api-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    # ---- helpers --------------------------------------------------

    def _write(self, rel: str, content: str) -> Path:
        p = self.tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def _public_fns(self, path: Path):
        return self.mod.public_function_names(path)

    # ---- tests ----------------------------------------------------

    def test_01_baseline_constant_is_nonempty(self):
        """BASELINE has entries for both files."""
        self.assertIn(".claude/hooks/_lib/audit_emit.py", self.mod.BASELINE)
        self.assertIn(".claude/scripts/audit-query.py", self.mod.BASELINE)
        self.assertGreaterEqual(len(self.mod.BASELINE[".claude/scripts/audit-query.py"]), 10)
        self.assertIn("iter_events", self.mod.BASELINE[".claude/hooks/_lib/audit_emit.py"])

    def test_02_real_repo_baseline_intact(self):
        """Running against the real repo returns exit 0 (no drift)."""
        exit_code, report = self.mod.check_baseline(REPO_ROOT)
        self.assertEqual(exit_code, 0, f"unexpected drift: {report}")
        # Every file in baseline should have no missing and no error.
        for path_key, info in report.items():
            self.assertEqual(info.get("missing", []), [],
                             f"missing in {path_key}: {info}")
            self.assertNotIn("error", info)

    def test_03_missing_baseline_function_reports_exit_1(self):
        """Simulate a file that LACKS a required function."""
        # Create a fake 'audit-query.py' stub missing all cmd_* functions
        fake_aq = self._write(".claude/scripts/audit-query.py",
                              "def iter_events():\n    return []\n")
        # Use a custom baseline pointing at our tmp tree
        custom = {
            str(Path(".claude/scripts/audit-query.py")): {"read_entries", "cmd_summary"},
        }
        exit_code, report = self.mod.check_baseline(self.tmp, baseline=custom)
        self.assertEqual(exit_code, 1)
        self.assertIn(str(Path(".claude/scripts/audit-query.py")), report)
        missing = report[str(Path(".claude/scripts/audit-query.py"))]["missing"]
        self.assertIn("read_entries", missing)
        self.assertIn("cmd_summary", missing)

    def test_04_missing_file_reports_exit_2(self):
        """Missing source file triggers exit 2."""
        custom = {"does-not-exist.py": {"foo"}}
        exit_code, report = self.mod.check_baseline(self.tmp, baseline=custom)
        self.assertEqual(exit_code, 2)
        self.assertIn("does-not-exist.py", report)
        self.assertIn("error", report["does-not-exist.py"])

    def test_05_syntax_error_reports_exit_2(self):
        """Syntax error in a baseline file triggers exit 2."""
        self._write("bad.py", "def :::\n   invalid\n")
        custom = {"bad.py": {"foo"}}
        exit_code, report = self.mod.check_baseline(self.tmp, baseline=custom)
        self.assertEqual(exit_code, 2)
        self.assertIn("error", report["bad.py"])

    def test_06_additive_functions_do_not_fail(self):
        """Adding new public functions beyond baseline is OK (additive-only)."""
        self._write("extras.py", (
            "def foo():\n    pass\n"
            "def bar():\n    pass\n"
            "def baz():\n    pass\n"
        ))
        custom = {"extras.py": {"foo"}}
        exit_code, report = self.mod.check_baseline(self.tmp, baseline=custom)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["extras.py"]["missing"], [])
        self.assertIn("bar", report["extras.py"]["extras"])
        self.assertIn("baz", report["extras.py"]["extras"])

    def test_07_private_functions_ignored(self):
        """Underscore-prefixed functions don't satisfy the baseline."""
        self._write("priv.py", "def _private():\n    pass\n"
                               "def public():\n    pass\n")
        fns = self._public_fns(self.tmp / "priv.py")
        self.assertIn("public", fns)
        self.assertNotIn("_private", fns)

    def test_08_format_report_highlights_missing(self):
        """format_report shows [FAIL] + MISSING for drift."""
        report = {
            "a.py": {"missing": ["foo", "bar"], "extras": []},
        }
        out = self.mod.format_report(report, verbose=False)
        self.assertIn("[FAIL]", out)
        self.assertIn("foo", out)
        self.assertIn("bar", out)

    def test_09_json_main_output_structure(self):
        """main --json emits exit + report fields."""
        # Use repo root for a pass case
        saved = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = self.mod.main(["--json", "--repo-root", str(REPO_ROOT)])
        finally:
            sys.stdout = saved
        self.assertIn(rc, (0, 1, 2))
        payload = json.loads(buf.getvalue())
        self.assertIn("exit", payload)
        self.assertIn("report", payload)

    def test_10_verbose_non_json_mentions_ok(self):
        """Verbose output on pass case mentions [OK] or baseline sizes."""
        saved = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            rc = self.mod.main(["--verbose", "--repo-root", str(REPO_ROOT)])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("OK", out)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
