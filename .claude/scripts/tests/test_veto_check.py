"""Unit tests for veto-check.py (PLAN-010 Phase 5).

Covers:
- No vetoes triggered → exit 0, report structure
- Each canonical pattern triggers (parseFloat, dangerouslySetInnerHTML,
  eval, rm -rf, hardcoded secret)
- Report JSON schema shape (file / triggered_count / vetoes[])
- Multiple hits across lines
- Missing file → exit 2
- text format rendering
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _SCRIPTS_DIR / "veto-check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("veto_check", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


vc = _load_module()


def _write(text: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, suffix=".txt"
    )
    tmp.write(text)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


class TestScanText(unittest.TestCase):
    def test_clean_text_no_hits(self) -> None:
        hits = vc.scan_text("const x = 1;\nconst y = x + 2;\n")
        self.assertEqual(hits, [])

    def test_parsefloat_triggers(self) -> None:
        hits = vc.scan_text("const v = parseFloat(raw);\n")
        ids = [h["id"] for h in hits]
        self.assertIn("CR-001-parseFloat", ids)

    def test_dangerously_set_html_triggers(self) -> None:
        hits = vc.scan_text('<div dangerouslySetInnerHTML={...} />\n')
        ids = [h["id"] for h in hits]
        self.assertIn("SEC-001-dangerously-set-html", ids)

    def test_eval_triggers(self) -> None:
        hits = vc.scan_text("return eval(userInput);\n")
        ids = [h["id"] for h in hits]
        self.assertIn("SEC-002-eval", ids)

    def test_rm_rf_triggers(self) -> None:
        hits = vc.scan_text("# cleanup\nrm -rf /tmp/cache\n")
        ids = [h["id"] for h in hits]
        self.assertIn("SEC-003-rm-rf", ids)

    def test_hardcoded_secret_triggers(self) -> None:
        hits = vc.scan_text('ANTHROPIC_API_KEY=sk_live_abc123xyz456defgh789\n')
        ids = [h["id"] for h in hits]
        self.assertIn("SEC-004-env-leak", ids)

    def test_multiple_hits_on_distinct_lines(self) -> None:
        text = "parseFloat(a);\neval(b);\nparseFloat(c);\n"
        hits = vc.scan_text(text)
        self.assertEqual(len(hits), 3)
        lines = sorted(h["line"] for h in hits)
        self.assertEqual(lines, [1, 2, 3])


class TestReportSchema(unittest.TestCase):
    def test_empty_report_has_all_known_domains(self) -> None:
        rep = vc.build_report("foo.ts", [])
        self.assertEqual(rep["file"], "foo.ts")
        self.assertEqual(rep["triggered_count"], 0)
        domains = sorted(b["domain"] for b in rep["vetoes"])
        self.assertEqual(domains, ["code-review", "security"])
        for b in rep["vetoes"]:
            self.assertEqual(b["rules"], [])

    def test_report_groups_by_domain(self) -> None:
        hits = vc.scan_text("parseFloat(x); eval(y);\n")
        rep = vc.build_report("bar.ts", hits)
        self.assertEqual(rep["triggered_count"], len(hits))
        by = {b["domain"]: b["rules"] for b in rep["vetoes"]}
        self.assertTrue(any(r["id"] == "CR-001-parseFloat" for r in by["code-review"]))
        self.assertTrue(any(r["id"] == "SEC-002-eval" for r in by["security"]))
        # Rule entries carry required keys
        for block in rep["vetoes"]:
            for r in block["rules"]:
                for key in ("id", "pattern", "triggered", "line", "match", "message"):
                    self.assertIn(key, r)


class TestCli(unittest.TestCase):
    def test_missing_file_exits_2(self) -> None:
        err = io.StringIO()
        with patch("sys.stderr", err):
            rc = vc.main(["--file", "/nonexistent/path/xyz.zzz"])
        self.assertEqual(rc, 2)
        self.assertIn("file not found", err.getvalue())

    def test_clean_file_exits_0_json(self) -> None:
        p = _write("const x = 1;\n")
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = vc.main(["--file", str(p), "--format", "json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["triggered_count"], 0)
        finally:
            p.unlink(missing_ok=True)

    def test_dirty_file_exits_1_json(self) -> None:
        p = _write("const v = parseFloat(x);\n")
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = vc.main(["--file", str(p), "--format", "json"])
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertGreaterEqual(payload["triggered_count"], 1)
            self.assertEqual(payload["file"], str(p))
        finally:
            p.unlink(missing_ok=True)

    def test_text_format_renders_clean(self) -> None:
        p = _write("const x = 1;\n")
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = vc.main(["--file", str(p), "--format", "text"])
            self.assertEqual(rc, 0)
            self.assertIn("no vetoes triggered", buf.getvalue())
        finally:
            p.unlink(missing_ok=True)

    def test_text_format_renders_dirty(self) -> None:
        p = _write("eval(x);\n")
        try:
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = vc.main(["--file", str(p), "--format", "text"])
            self.assertEqual(rc, 1)
            out = buf.getvalue()
            self.assertIn("veto hit", out)
            self.assertIn("SEC-002-eval", out)
        finally:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
