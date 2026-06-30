"""Unit tests for audit-tokens.py (PLAN-047 Phase 3).

Covers CLI wiring, window filter, render helpers, and fail-open
contracts.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "audit_tokens", _SCRIPTS_DIR / "audit-tokens.py"
)
assert spec is not None and spec.loader is not None
audit_tokens = importlib.util.module_from_spec(spec)
# Register in sys.modules so dataclasses introspection finds the module.
sys.modules["audit_tokens"] = audit_tokens
spec.loader.exec_module(audit_tokens)  # type: ignore[union-attr]


def _mk_finding(
    detector: str,
    *,
    severity: str = "warning",
    recommendation: str = "fix it",
    evidence: dict = None,
    wasted: int = 0,
) -> audit_tokens.Finding:
    return audit_tokens.Finding(
        detector=detector,
        severity=severity,
        recommendation=recommendation,
        evidence=dict(evidence or {}),
        estimated_wasted_tokens=wasted,
    )


class TestRunAll(unittest.TestCase):
    """run_all() aggregates all 6 detectors and is fail-open."""

    def test_run_all_calls_every_detector(self) -> None:
        calls: list = []
        for mod in audit_tokens._ALL_DETECTORS:
            original = mod.detect
            mod_ref = mod

            def make_stub(name: str, orig):
                def stub(log_path, **kwargs):  # noqa: ANN001
                    calls.append(name)
                    return []
                return stub, orig

            mod.detect, stashed = make_stub(mod.__name__, original)
            self.addCleanup(setattr, mod_ref, "detect", stashed)
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as h:
            log_path = Path(h.name)
        self.addCleanup(log_path.unlink)
        audit_tokens.run_all(log_path)
        expected = {m.__name__ for m in audit_tokens._ALL_DETECTORS}
        self.assertEqual(set(calls), expected)

    def test_run_all_swallows_detector_exception(self) -> None:
        target = audit_tokens._ALL_DETECTORS[0]
        original = target.detect

        def boom(log_path, **kwargs):  # noqa: ANN001
            raise RuntimeError("intentional")

        target.detect = boom
        self.addCleanup(setattr, target, "detect", original)
        buf = io.StringIO()
        with redirect_stderr(buf):
            result = audit_tokens.run_all(Path("/nonexistent/log.jsonl"))
        # Other detectors still ran and returned their empty list.
        self.assertIsInstance(result, list)
        self.assertIn("detect failed", buf.getvalue())


class TestFindingTs(unittest.TestCase):
    """_finding_ts parses multiple evidence timestamp shapes."""

    def test_iso_with_z_suffix(self) -> None:
        f = _mk_finding("x", evidence={"first_seen": "2026-04-21T12:00:00Z"})
        ts = audit_tokens._finding_ts(f)
        self.assertIsNotNone(ts)
        self.assertEqual(ts.year, 2026)
        self.assertEqual(ts.tzinfo, timezone.utc)

    def test_iso_with_offset(self) -> None:
        f = _mk_finding("x", evidence={"last_seen": "2026-04-21T09:00:00-03:00"})
        ts = audit_tokens._finding_ts(f)
        self.assertIsNotNone(ts)
        self.assertEqual(ts.hour, 9)  # offset-aware, not normalized to UTC

    def test_missing_ts_returns_none(self) -> None:
        f = _mk_finding("x", evidence={"unrelated": "value"})
        self.assertIsNone(audit_tokens._finding_ts(f))

    def test_garbage_ts_returns_none(self) -> None:
        f = _mk_finding("x", evidence={"first_seen": "not-a-date"})
        self.assertIsNone(audit_tokens._finding_ts(f))


class TestFilterWindow(unittest.TestCase):
    """filter_window keeps findings within N days + handles edge cases."""

    def setUp(self) -> None:
        self.now = datetime(2026, 4, 21, tzinfo=timezone.utc)

    def test_window_keeps_recent(self) -> None:
        recent_ts = (self.now - timedelta(days=3)).isoformat()
        f = _mk_finding("x", evidence={"first_seen": recent_ts})
        kept = audit_tokens.filter_window([f], window_days=7, now=self.now)
        self.assertEqual(len(kept), 1)

    def test_window_drops_old(self) -> None:
        old_ts = (self.now - timedelta(days=40)).isoformat()
        f = _mk_finding("x", evidence={"first_seen": old_ts})
        kept = audit_tokens.filter_window([f], window_days=7, now=self.now)
        self.assertEqual(kept, [])

    def test_window_zero_disables_filter(self) -> None:
        old_ts = (self.now - timedelta(days=9999)).isoformat()
        f = _mk_finding("x", evidence={"first_seen": old_ts})
        kept = audit_tokens.filter_window([f], window_days=0, now=self.now)
        self.assertEqual(len(kept), 1)

    def test_window_keeps_findings_without_ts(self) -> None:
        f = _mk_finding("x", evidence={"no_ts_field": 42})
        kept = audit_tokens.filter_window([f], window_days=7, now=self.now)
        self.assertEqual(len(kept), 1)


class TestGroupByDetector(unittest.TestCase):
    def test_stable_alphabetical(self) -> None:
        findings = [
            _mk_finding("zebra"),
            _mk_finding("alpha"),
            _mk_finding("alpha"),
            _mk_finding("middle"),
        ]
        groups = audit_tokens.group_by_detector(findings)
        self.assertEqual([name for name, _ in groups], ["alpha", "middle", "zebra"])
        self.assertEqual(len(groups[0][1]), 2)


class TestRenderMarkdown(unittest.TestCase):
    def test_empty_findings_note(self) -> None:
        out = audit_tokens.render_markdown(
            [], window_days=30, log_path=Path("/tmp/x.jsonl"), top_per_detector=20
        )
        self.assertIn("Total findings: **0**", out)
        self.assertIn("No findings in window", out)

    def test_per_detector_section_and_severity_tally(self) -> None:
        findings = [
            _mk_finding("retry_churn", severity="warning"),
            _mk_finding("retry_churn", severity="warning"),
            _mk_finding("retry_churn", severity="info"),
        ]
        out = audit_tokens.render_markdown(
            findings, window_days=7, log_path=Path("/tmp/x.jsonl"),
            top_per_detector=20,
        )
        self.assertIn("## retry_churn (3 findings)", out)
        self.assertIn("info=1, warning=2", out)

    def test_top_per_detector_cap(self) -> None:
        findings = [_mk_finding("tool_cascade") for _ in range(25)]
        out = audit_tokens.render_markdown(
            findings, window_days=7, log_path=Path("/tmp/x.jsonl"),
            top_per_detector=5,
        )
        self.assertIn("... 20 more", out)
        # 5 visible bullets (plus the "... N more" line).
        visible = sum(
            1 for line in out.splitlines()
            if line.startswith("- **[warning]**")
        )
        self.assertEqual(visible, 5)


class TestRenderJson(unittest.TestCase):
    def test_jsonl_one_per_line(self) -> None:
        findings = [_mk_finding("a"), _mk_finding("b"), _mk_finding("c")]
        out = audit_tokens.render_jsonl(findings)
        lines = out.splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            parsed = json.loads(line)
            self.assertIn("detector", parsed)

    def test_json_summary_shape(self) -> None:
        findings = [_mk_finding("a", wasted=7)]
        payload = json.loads(
            audit_tokens.render_json_summary(
                findings, window_days=30, log_path=Path("/tmp/x.jsonl"),
                now=datetime(2026, 4, 21, tzinfo=timezone.utc),
            )
        )
        self.assertEqual(payload["total_findings"], 1)
        self.assertEqual(payload["estimated_wasted_tokens"], 7)
        self.assertEqual(payload["window_days"], 30)
        self.assertEqual(len(payload["findings"]), 1)


class TestMainCLI(unittest.TestCase):
    def test_missing_log_exits_zero_with_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "does-not-exist.jsonl"
            out_buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(out_buf), redirect_stderr(err_buf):
                rc = audit_tokens.main(
                    ["--log", str(bogus), "--window", "30", "--format", "markdown"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("Total findings: **0**", out_buf.getvalue())
            self.assertIn("NOTE: log not found", err_buf.getvalue())

    def test_output_flag_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "empty.jsonl"
            log_path.write_text("", encoding="utf-8")
            out_path = Path(tmp) / "sub" / "report.md"
            rc = audit_tokens.main(
                [
                    "--log", str(log_path),
                    "--output", str(out_path),
                    "--window", "7",
                    "--format", "markdown",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.exists())
            self.assertIn("/audit-tokens report", out_path.read_text())

    def test_argparse_rejects_invalid_format(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            audit_tokens.main(["--format", "xml"])
        # argparse exits 2 on invalid choice.
        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
