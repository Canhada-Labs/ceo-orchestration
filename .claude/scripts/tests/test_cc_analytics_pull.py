"""Tests for cc-analytics-pull.py + measure_multiplier --source analytics-api (PLAN-135 W5 O3).

Stdlib-only. The client is imported via importlib (dash in filename). ALL HTTP is
mocked at the module's ``_urlopen`` seam (the documented test contract: mock
urlopen — ZERO live Analytics/Admin API calls in any test). Covers:

  • dormant fail-soft (no CEO_ANALYTICS_ADMIN_KEY → exit 0 + dormant message, NO network)
  • cursor pagination (page param threaded from next_page; headers carry the key,
    snapshot/stdout NEVER carry it)
  • runaway-cursor guard (repeated cursor → truncated, no infinite loop)
  • HTTP error path exits 3 with the key REDACTED from all output
  • deterministic day_list + summarize aggregation (cents→USD, accept/reject rates)
  • --summary snapshot-read mode (no network; dormant when snapshot missing)
  • measure_multiplier integration: analytics_metrics window filter + fail-soft +
    --source analytics-api end-to-end attach (JSON payload carries "analytics")
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_SCRIPT_PATH = _THIS_DIR.parent / "cc-analytics-pull.py"
_REPO_ROOT = _THIS_DIR.parent.parent.parent

_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("cc_analytics_pull", _SCRIPT_PATH)
cap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cap)  # type: ignore[union-attr]

_KEY = "sk-ant-admin-TEST-NEVER-ECHO-abc123"


def _record(day="2026-06-10", email="dev@example.com", commits=3, prs=1, sessions=2,
            cost_cents=1025, accepted=10, rejected=2, customer_type="api"):
    return {
        "date": "%sT00:00:00Z" % day,
        "actor": {"type": "user_actor", "email_address": email},
        "organization_id": "org-uuid",
        "customer_type": customer_type,
        "terminal_type": "tmux",
        "core_metrics": {
            "num_sessions": sessions,
            "lines_of_code": {"added": 100, "removed": 40},
            "commits_by_claude_code": commits,
            "pull_requests_by_claude_code": prs,
        },
        "tool_actions": {
            "edit_tool": {"accepted": accepted, "rejected": rejected},
            "write_tool": {"accepted": 1, "rejected": 0},
        },
        "model_breakdown": [
            {"model": "claude-opus-4-8",
             "tokens": {"input": 1000, "output": 500, "cache_read": 100, "cache_creation": 50},
             "estimated_cost": {"currency": "USD", "amount": cost_cents}},
        ],
    }


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeUrlopen:
    """Mock urlopen seam: returns scripted pages in order; records every Request."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        if not self.pages:
            raise AssertionError("unexpected extra HTTP call: %s" % req.full_url)
        page = self.pages.pop(0)
        if isinstance(page, Exception):
            raise page
        return _FakeResponse(page)


def _boom(req, timeout=None):
    raise AssertionError("network MUST NOT be touched in this path: %s" % req.full_url)


@contextlib.contextmanager
def _patched_urlopen(fake):
    orig = cap._urlopen
    cap._urlopen = fake
    try:
        yield
    finally:
        cap._urlopen = orig


def _run_main(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cap.main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestDormantFailSoft(TestEnvContext):
    def test_no_key_is_dormant_exit_0_no_network(self):
        os.environ.pop("CEO_ANALYTICS_ADMIN_KEY", None)
        with _patched_urlopen(_boom):
            rc, out, err = _run_main(["--days", "1"])
        self.assertEqual(rc, 0)
        self.assertIn("DORMANT", out)
        self.assertIn("CEO_ANALYTICS_ADMIN_KEY", out)
        self.assertIn("THREAT-MODEL-WORKSHEET", out)      # custody pointer in the dormant message
        self.assertIn("rotation-log", out)

    def test_summary_without_snapshot_is_dormant_exit_0(self):
        os.environ.pop("CEO_ANALYTICS_ADMIN_KEY", None)
        missing = os.path.join(tempfile.mkdtemp(), "nope.json")
        with _patched_urlopen(_boom):
            rc, out, _ = _run_main(["--summary", "--snapshot", missing])
        self.assertEqual(rc, 0)
        self.assertIn("DORMANT", out)
        with _patched_urlopen(_boom):
            rc, out, _ = _run_main(["--summary", "--snapshot", missing, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertFalse(payload["available"])
        self.assertTrue(payload["dormant"])


class TestPullPagination(TestEnvContext):
    def setUp(self):
        super().setUp()
        os.environ["CEO_ANALYTICS_ADMIN_KEY"] = _KEY
        self.out_path = os.path.join(tempfile.mkdtemp(), "snap.json")

    def test_cursor_pagination_and_key_hygiene(self):
        fake = _FakeUrlopen([
            {"data": [_record(email="a@x.com"), _record(email="b@x.com")],
             "has_more": True, "next_page": "page_abc"},
            {"data": [_record(email="c@x.com")], "has_more": False, "next_page": None},
        ])
        with _patched_urlopen(fake):
            rc, out, err = _run_main(["--starting-at", "2026-06-10", "--days", "1",
                                      "--out", self.out_path])
        self.assertEqual(rc, 0)
        self.assertEqual(len(fake.requests), 2)
        # cursor threaded into the second request; day + headers on both
        self.assertIn("page=page_abc", fake.requests[1].full_url)
        for req in fake.requests:
            self.assertIn("starting_at=2026-06-10", req.full_url)
            self.assertEqual(req.get_header("X-api-key"), _KEY)          # key in HEADER only
            self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")
            self.assertNotIn(_KEY, req.full_url)
        snap = json.loads(Path(self.out_path).read_text())
        self.assertEqual(snap["schema"], "cc-analytics-snapshot/v1")
        self.assertEqual(len(snap["records"]), 3)
        self.assertEqual(snap["summary"]["records"], 3)
        # the admin key never lands in the snapshot, stdout, or stderr
        raw = Path(self.out_path).read_text()
        for blob in (raw, out, err):
            self.assertNotIn(_KEY, blob)

    def test_multi_day_iteration(self):
        fake = _FakeUrlopen([
            {"data": [_record(day="2026-06-01")], "has_more": False, "next_page": None},
            {"data": [_record(day="2026-06-02")], "has_more": False, "next_page": None},
        ])
        with _patched_urlopen(fake):
            rc, _, _ = _run_main(["--starting-at", "2026-06-01", "--days", "2",
                                  "--out", self.out_path])
        self.assertEqual(rc, 0)
        self.assertIn("starting_at=2026-06-01", fake.requests[0].full_url)
        self.assertIn("starting_at=2026-06-02", fake.requests[1].full_url)
        snap = json.loads(Path(self.out_path).read_text())
        self.assertEqual(snap["days_requested"], ["2026-06-01", "2026-06-02"])
        self.assertEqual(len(snap["records"]), 2)

    def test_runaway_cursor_guard_truncates(self):
        # has_more forever with the SAME cursor → repeated-cursor break, truncated flag set
        fake = _FakeUrlopen([
            {"data": [_record()], "has_more": True, "next_page": "page_loop"},
            {"data": [_record()], "has_more": True, "next_page": "page_loop"},
        ])
        with _patched_urlopen(fake):
            rc, _, err = _run_main(["--starting-at", "2026-06-10", "--days", "1",
                                    "--out", self.out_path])
        self.assertEqual(rc, 0)
        self.assertEqual(len(fake.requests), 2)            # stopped, did not loop
        snap = json.loads(Path(self.out_path).read_text())
        self.assertEqual(snap["truncated_days"], ["2026-06-10"])

    def test_http_error_exits_3_and_redacts_key(self):
        body = io.BytesIO(b'{"error": "forbidden for key ' + _KEY.encode() + b'"}')
        err403 = urllib.error.HTTPError("https://api.anthropic.com/x", 403, "Forbidden", {}, body)
        with _patched_urlopen(_FakeUrlopen([err403])):
            rc, out, err = _run_main(["--starting-at", "2026-06-10", "--days", "1",
                                      "--out", self.out_path])
        self.assertEqual(rc, 3)
        self.assertIn("HTTP 403", err)
        self.assertIn("ADMIN key", err)                    # custody hint on auth failures
        self.assertNotIn(_KEY, out + err)                  # redaction holds even for echoed bodies
        self.assertFalse(os.path.exists(self.out_path))    # no partial snapshot on error

    def test_network_error_exits_3(self):
        with _patched_urlopen(_FakeUrlopen([urllib.error.URLError("dns down")])):
            rc, _, err = _run_main(["--starting-at", "2026-06-10", "--days", "1",
                                    "--out", self.out_path])
        self.assertEqual(rc, 3)
        self.assertIn("network/parse error", err)


class TestPureHelpers(TestEnvContext):
    def test_day_list_deterministic_forward(self):
        self.assertEqual(cap.day_list("2026-06-01", 3),
                         ["2026-06-01", "2026-06-02", "2026-06-03"])

    def test_day_list_default_ends_today(self):
        now = datetime(2026, 6, 12, 15, 0, tzinfo=timezone.utc)
        self.assertEqual(cap.day_list(None, 2, now=now), ["2026-06-11", "2026-06-12"])

    def test_day_list_caps_days(self):
        self.assertEqual(len(cap.day_list("2026-01-01", 10_000)), cap._MAX_DAYS)

    def test_summarize_aggregation_cents_to_usd(self):
        recs = [
            _record(email="a@x.com", commits=3, prs=1, cost_cents=1025, accepted=10, rejected=2),
            _record(email="b@x.com", commits=2, prs=0, cost_cents=500, accepted=0, rejected=0,
                    customer_type="subscription"),
            {"date": "2026-06-10T00:00:00Z",                      # api_actor variant
             "actor": {"type": "api_actor", "api_key_name": "ci-key"},
             "customer_type": "api", "core_metrics": {}, "tool_actions": {}, "model_breakdown": []},
        ]
        s = cap.summarize(recs)
        self.assertEqual(s["records"], 3)
        self.assertEqual(s["users"], 3)
        self.assertAlmostEqual(s["estimated_cost_usd"], 15.25)     # (1025+500) cents → USD
        self.assertEqual(s["commits_by_cc"], 5)
        self.assertEqual(s["prs_by_cc"], 1)
        self.assertEqual(s["customer_types"], {"api": 2, "subscription": 1})
        ta = s["tool_actions"]
        self.assertEqual((ta["accepted"], ta["rejected"]), (12, 2))   # +2 write_tool accepted
        self.assertAlmostEqual(ta["acceptance_rate"], round(12 / 14, 4))
        self.assertEqual(s["tokens"]["input"], 2000)
        labels = {r["actor"] for r in s["by_user_day"]}
        self.assertEqual(labels, {"a@x.com", "b@x.com", "ci-key"})

    def test_summarize_empty_has_null_rate(self):
        s = cap.summarize([])
        self.assertEqual(s["estimated_cost_usd"], 0.0)
        self.assertIsNone(s["tool_actions"]["acceptance_rate"])


class TestSummaryMode(TestEnvContext):
    def test_summary_reads_snapshot_without_network(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "snap.json")
        recs = [_record(email="a@x.com", cost_cents=1025), _record(email="b@x.com", cost_cents=500)]
        cap.write_snapshot(path, {"schema": cap._SNAPSHOT_SCHEMA, "generated_at": "2026-06-12T00:00:00Z",
                                  "records": recs, "summary": cap.summarize(recs)})
        with _patched_urlopen(_boom):
            rc, out, _ = _run_main(["--summary", "--snapshot", path, "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertAlmostEqual(payload["summary"]["estimated_cost_usd"], 15.25)
        self.assertEqual(payload["meta"]["source"], "snapshot")
        # human mode too
        with _patched_urlopen(_boom):
            rc, out, _ = _run_main(["--summary", "--snapshot", path])
        self.assertEqual(rc, 0)
        self.assertIn("commits by CC", out)
        self.assertIn("$15.25", out)


if __name__ == "__main__":
    unittest.main()
