"""Unit tests for check-staleness.py."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "check-staleness.py"
_spec = importlib.util.spec_from_file_location("check_staleness", _SCRIPT)
check_staleness_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_staleness_mod)


class TestStaleness(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="stale-test-"))
        (self.tmp / ".claude" / "plans").mkdir(parents=True)
        (self.tmp / ".claude" / "adr").mkdir(parents=True)

    def _write_plan(self, slug: str, status: str, created: str, related_commits: str = "[]"):
        p = self.tmp / ".claude" / "plans" / f"PLAN-999-{slug}.md"
        p.write_text(
            f"---\nid: PLAN-999\ntitle: T\nstatus: {status}\ncreated: {created}\nowner: CEO\nrelated_commits: {related_commits}\n---\nbody"
        )
        return p

    def _write_adr(self, num: int, status: str, age_days: int):
        p = self.tmp / ".claude" / "adr" / f"ADR-{num:03d}-t.md"
        p.write_text(f"# ADR-{num:03d}\n\n## Status: {status}\n\nbody")
        # Set mtime in the past
        old = (datetime.now(timezone.utc) - timedelta(days=age_days)).timestamp()
        os.utime(p, (old, old))
        return p

    def test_no_findings_on_fresh_plan(self):
        self._write_plan("new", "draft", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "healthy")

    def test_plan_executing_stalled_over_14d(self):
        old = (datetime.now(timezone.utc) - timedelta(days=20)).strftime("%Y-%m-%d")
        self._write_plan("old-exec", "executing", old, related_commits="[abc123]")
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["rule"], "plan_executing_stalled")
        self.assertEqual(report["status"], "degraded")

    def test_plan_executing_abandoned_candidate_over_30d_no_commits(self):
        old = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%d")
        self._write_plan("dead", "executing", old, related_commits="[]")
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["rule"], "plan_executing_abandoned_candidate")
        self.assertEqual(report["status"], "unhealthy")

    def test_plan_draft_stale_over_30d(self):
        old = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
        self._write_plan("old-draft", "draft", old)
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["rule"], "plan_draft_stale")

    def test_done_plan_not_flagged(self):
        old = (datetime.now(timezone.utc) - timedelta(days=200)).strftime("%Y-%m-%d")
        self._write_plan("done", "done", old)
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(report["findings"], [])

    def test_adr_proposed_stale(self):
        self._write_adr(99, "PROPOSED", age_days=60)
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(len(report["findings"]), 1)
        self.assertEqual(report["findings"][0]["rule"], "adr_proposed_stale")

    def test_adr_accepted_not_flagged(self):
        self._write_adr(98, "ACCEPTED", age_days=500)
        report = check_staleness_mod.check_staleness(self.tmp)
        self.assertEqual(report["findings"], [])

    def test_cli_json_mode(self):
        import io
        import contextlib
        old = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
        self._write_plan("stale", "draft", old)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = check_staleness_mod._cli(["--json", "--repo-root", str(self.tmp)])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "degraded")

    def test_cli_strict_exits_1_on_unhealthy(self):
        import io
        import contextlib
        old = (datetime.now(timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%d")
        self._write_plan("dead", "executing", old, related_commits="[]")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = check_staleness_mod._cli(["--strict", "--json", "--repo-root", str(self.tmp)])
        self.assertEqual(rc, 1)


class TestRealRepo(unittest.TestCase):
    def test_real_repo_no_unhealthy_today(self):
        repo = Path(__file__).resolve().parents[3]
        report = check_staleness_mod.check_staleness(repo)
        # PLAN-065 §4.4.B (S83): "stranded" is now a valid real-world status
        # when an executing plan has no commits in last 24h (mode 8.2) OR a
        # reviewed plan has no transition in last 7d (mode 8.1). Accept
        # stranded as a healthy signal of the new mode-8 detector working;
        # the CLI is what matters here (does not crash + returns valid
        # status). Only "unhealthy" represents an actionable regression.
        self.assertIn(
            report["status"],
            ("healthy", "degraded", "stranded"),
            f"Real repo unexpectedly unhealthy: {report}",
        )


if __name__ == "__main__":
    unittest.main()
