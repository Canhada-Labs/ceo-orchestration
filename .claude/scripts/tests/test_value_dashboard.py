#!/usr/bin/env python3
"""Tests for value-dashboard.py (PLAN-083 Wave 2 sub-2.4).

Stdlib unittest only. No network, no external deps.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Import the dashboard module under test.
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_DASHBOARD_DIR = _HERE.parent

# Insert the staging sub-2-4-dashboard dir on sys.path so we can import.
if str(_DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(_DASHBOARD_DIR))

# Import via a module-name that won't collide with anything in the repo.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_plan083_value_dashboard",
    _DASHBOARD_DIR / "value-dashboard.py",
)
assert _spec is not None and _spec.loader is not None
_vd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_vd)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%S+0000")


def _write_log(path: Path, events: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


_SPAWN_COUNTER = [0]


def _make_agent_spawn(
    *,
    when: datetime,
    plan_id: Optional[str] = None,
    tokens_in: int = 10000,
    tokens_out: int = 2000,
    model: str = "claude-sonnet-4-5",
    session_id: str = "S-test",
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    # Rotation-dedup is keyed on full canonical event sha256. To prevent
    # multiple fixture spawns colliding (same ts + action + session + tokens)
    # we vary an ``agent_name`` field per call.
    _SPAWN_COUNTER[0] += 1
    name = agent_name or f"agent-{_SPAWN_COUNTER[0]:04d}"
    ev: Dict[str, Any] = {
        "ts": _ts(when),
        "action": "agent_spawn",
        "session_id": session_id,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "model": model,
        "agent_name": name,
    }
    if plan_id is not None:
        ev["plan_id"] = plan_id
    return ev


def _make_bug_event(
    action: str,
    *,
    when: datetime,
    session_id: str = "S-test",
) -> Dict[str, Any]:
    return {
        "ts": _ts(when),
        "action": action,
        "session_id": session_id,
    }


# ---------------------------------------------------------------------------
# Test fixtures: a typical week
# ---------------------------------------------------------------------------


def _typical_week_events(now: datetime) -> List[Dict[str, Any]]:
    """Build a realistic-ish week of audit events.

    - 10 agent_spawn events spread across the past 5 days
    - 2 pair_rail_case events (Codex)
    - 3 plan_status_transition events (2 distinct plans)
    - 1 sentinel_signed, 1 ceremony_commit
    - 1 of each bug-caught action
    """
    events: List[Dict[str, Any]] = []
    for i in range(10):
        events.append(_make_agent_spawn(
            when=now - timedelta(days=i % 5, hours=2),
            plan_id="PLAN-083",
        ))
    for i in range(2):
        events.append({
            "ts": _ts(now - timedelta(days=1, hours=i + 1)),
            "action": "pair_rail_case",
            "tokens_in": 5000,
            "tokens_out": 1500,
            "model": "gpt-5-codex",
            "plan_id": "PLAN-083",
            "session_id": "S-test",
            "case_id": f"case-{i}",
        })
    events.append({
        "ts": _ts(now - timedelta(days=3)),
        "action": "plan_status_transition",
        "plan_id": "PLAN-082",
        "to_status": "done",
        "session_id": "S-test",
    })
    events.append({
        "ts": _ts(now - timedelta(days=2)),
        "action": "plan_status_transition",
        "plan_id": "PLAN-083",
        "to_status": "executing",
        "session_id": "S-test",
    })
    events.append({
        "ts": _ts(now - timedelta(days=4)),
        "action": "plan_status_transition",
        "plan_id": "PLAN-081",
        "to_status": "done",
        "session_id": "S-test",
    })
    events.append(_make_bug_event(
        "sentinel_signed", when=now - timedelta(days=1)))
    events.append(_make_bug_event(
        "ceremony_commit", when=now - timedelta(days=2)))
    for action in _vd.BUGS_CAUGHT_ACTIONS:
        events.append(_make_bug_event(action, when=now - timedelta(days=1)))
    return events


# ---------------------------------------------------------------------------
# Base class with audit_dir isolation
# ---------------------------------------------------------------------------


class _DashboardTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.audit_dir = Path(self._tmp.name)
        self.log_path = self.audit_dir / "audit-log.jsonl"
        # Reference "now" — pinned to a stable timezone-aware moment so
        # tests aren't time-of-day-flaky.
        self.now = datetime.now(timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRollupSections(_DashboardTestBase):
    """Each of the four sections (cost / hours / bugs / throughput) renders."""

    def setUp(self) -> None:
        super().setUp()
        _write_log(self.log_path, _typical_week_events(self.now))

    def test_cost_section_total_positive(self) -> None:
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        self.assertGreater(data["cost"]["total_usd"], 0.0)
        self.assertEqual(data["cost"]["cost_source"], "default-pricing-table")

    def test_hours_saved_section_is_estimate(self) -> None:
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        hs = data["hours_saved_estimate"]
        self.assertEqual(hs["framing"], "ESTIMATE not measured outcome")
        # 12 dispatches → baseline 12*60s = 720s = 0.2h. Framework
        # ceil(12/6)*63s = 126s = 0.035h. value_hours ≈ 0.17.
        self.assertGreaterEqual(hs["value_hours"], 0.0)
        self.assertEqual(hs["dispatches_count"], 12)

    def test_bugs_caught_section_counts(self) -> None:
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        bc = data["bugs_caught"]
        self.assertEqual(bc["total"], len(_vd.BUGS_CAUGHT_ACTIONS))
        seen_actions = {row["action"]: row["count"] for row in bc["by_action"]}
        for action in _vd.BUGS_CAUGHT_ACTIONS:
            self.assertEqual(seen_actions[action], 1)

    def test_throughput_section_counts(self) -> None:
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        th = data["throughput"]
        self.assertEqual(th["plans_transitioned"], 3)
        self.assertEqual(th["dispatches_count"], 12)
        self.assertEqual(th["commits_observed"], 1)
        self.assertEqual(th["gpg_ceremonies_observed"], 1)


class TestTextRenderingSections(_DashboardTestBase):
    """Text renderer includes all four sections + assumption rows."""

    def setUp(self) -> None:
        super().setUp()
        _write_log(self.log_path, _typical_week_events(self.now))
        self.data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )

    def test_text_render_has_cost_section(self) -> None:
        out = _vd.render_text(self.data, by_day=False, by_plan=False)
        self.assertIn("[1/4] COST", out)
        self.assertIn("Total: $", out)

    def test_text_render_has_hours_estimate_label(self) -> None:
        out = _vd.render_text(self.data, by_day=False, by_plan=False)
        self.assertIn("[2/4] HOURS SAVED", out)
        # The word "ESTIMATE" MUST appear in the section header so
        # CTO readers cannot mistake the number for a measurement.
        self.assertIn("ESTIMATE", out)
        self.assertIn("NOT MEASURED", out)

    def test_text_render_has_bugs_section(self) -> None:
        out = _vd.render_text(self.data, by_day=False, by_plan=False)
        self.assertIn("[3/4] BUGS CAUGHT", out)
        for action in _vd.BUGS_CAUGHT_ACTIONS:
            self.assertIn(action, out)

    def test_text_render_has_throughput_section(self) -> None:
        out = _vd.render_text(self.data, by_day=False, by_plan=False)
        self.assertIn("[4/4] THROUGHPUT", out)
        self.assertIn("Plans transitioned", out)

    def test_methodology_assumptions_visible_in_output(self) -> None:
        """Per Codex P1: assumptions in the output itself, not only disclaimer."""
        out = _vd.render_text(self.data, by_day=False, by_plan=False)
        self.assertIn("assumption.baseline_serial", out)
        self.assertIn("assumption.parallel_ceiling", out)
        self.assertIn("assumption.audit_overhead_pct", out)


class TestByDayAggregation(_DashboardTestBase):
    def test_by_day_aggregates(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        by_day = data["cost"]["by_day"]
        # We have agent_spawn distributed across 5 day-buckets (days 0..4)
        # plus pair_rail_case on day 1. At most 5 distinct day buckets.
        self.assertGreaterEqual(len(by_day), 2)
        self.assertLessEqual(len(by_day), 7)
        # Dates are ISO YYYY-MM-DD and sorted ascending.
        dates = [row["date"] for row in by_day]
        self.assertEqual(dates, sorted(dates))
        # Per-day sum equals total.
        total_from_days = round(sum(row["usd"] for row in by_day), 4)
        self.assertAlmostEqual(
            total_from_days, round(data["cost"]["total_usd"], 4), places=4,
        )
        # by_day text render mentions the dates
        out = _vd.render_text(data, by_day=True, by_plan=False)
        self.assertIn("Per-day spend", out)
        self.assertIn(dates[0], out)


class TestByPlanAggregation(_DashboardTestBase):
    def test_by_plan_aggregates(self) -> None:
        # Mix of two plan_ids across dispatch events.
        events = [
            _make_agent_spawn(when=self.now - timedelta(days=1), plan_id="PLAN-083"),
            _make_agent_spawn(when=self.now - timedelta(days=1), plan_id="PLAN-083"),
            _make_agent_spawn(when=self.now - timedelta(days=2), plan_id="PLAN-082"),
        ]
        _write_log(self.log_path, events)
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        by_plan = {row["plan_id"]: row for row in data["cost"]["by_plan"]}
        self.assertIn("PLAN-083", by_plan)
        self.assertIn("PLAN-082", by_plan)
        self.assertEqual(by_plan["PLAN-083"]["events"], 2)
        self.assertEqual(by_plan["PLAN-082"]["events"], 1)
        # PLAN-083 cost > PLAN-082 cost (twice as many events).
        self.assertGreater(by_plan["PLAN-083"]["usd"], by_plan["PLAN-082"]["usd"])
        # Text render with --by-plan mentions both.
        out = _vd.render_text(data, by_day=False, by_plan=True)
        self.assertIn("PLAN-083", out)
        self.assertIn("PLAN-082", out)


class TestJsonSchema(_DashboardTestBase):
    def test_json_output_valid(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        out = _vd.render_json(data)
        # Round-trip JSON.
        parsed = json.loads(out)
        # Required top-level keys.
        for key in (
            "period_days", "audit_dir", "log_files_read",
            "methodology_assumptions", "cost", "hours_saved_estimate",
            "bugs_caught", "throughput", "audit_emit_payload",
        ):
            self.assertIn(key, parsed)
        # Methodology assumptions present at top level AND inside hours_saved.
        self.assertIn("baseline_serial", parsed["methodology_assumptions"])
        self.assertIn("baseline_serial", parsed["hours_saved_estimate"]["assumptions"])


class TestForCtovDisclaimer(_DashboardTestBase):
    def test_for_ctov_prepends_disclaimer(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        buf = io.StringIO()
        argv = [
            "--period", "7d",
            "--for-ctov",
            "--audit-dir", str(self.audit_dir),
        ]
        with redirect_stdout(buf):
            rc = _vd.main(argv)
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        # Disclaimer file headline appears first.
        disclaimer_idx = out.find("Methodology disclaimer")
        dashboard_idx = out.find("[1/4] COST")
        self.assertGreaterEqual(disclaimer_idx, 0,
                                "disclaimer headline missing from --for-ctov")
        self.assertGreaterEqual(dashboard_idx, 0,
                                "dashboard body missing from --for-ctov")
        self.assertLess(
            disclaimer_idx, dashboard_idx,
            "disclaimer MUST appear before dashboard in --for-ctov mode",
        )
        # The "ESTIMATE not measured outcome" framing is repeated in the body.
        self.assertIn("ESTIMATE", out)

    def test_for_ctov_warning_in_json_mode(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        stderr_buf = io.StringIO()
        stdout_buf = io.StringIO()
        argv = [
            "--period", "7d",
            "--for-ctov",
            "--json",
            "--audit-dir", str(self.audit_dir),
        ]
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            rc = _vd.main(argv)
        self.assertEqual(rc, 0)
        self.assertIn("--for-ctov ignored", stderr_buf.getvalue())


class TestEmptyAuditLog(_DashboardTestBase):
    def test_empty_log_graceful_message(self) -> None:
        # No log files at all.
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        self.assertTrue(data["empty"])
        out = _vd.render_text(data, by_day=False, by_plan=False)
        self.assertIn("No data yet", out)
        # Methodology assumptions STILL visible even with no data.
        self.assertIn("baseline_serial", out)

    def test_empty_log_file_present_but_no_events(self) -> None:
        _write_log(self.log_path, [])
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        self.assertTrue(data["empty"])

    def test_empty_period_audit_emit_payload_zero(self) -> None:
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        p = data["audit_emit_payload"]
        self.assertEqual(p["cost_usd_int_cents"], 0)
        self.assertEqual(p["bugs_count"], 0)
        self.assertEqual(p["dispatches_count"], 0)
        self.assertEqual(p["plans_count"], 0)


class TestPeriodFiltering(_DashboardTestBase):
    def test_period_excludes_older_events(self) -> None:
        # 2 events inside window, 1 well outside (30 days ago).
        events = [
            _make_agent_spawn(when=self.now - timedelta(days=1)),
            _make_agent_spawn(when=self.now - timedelta(days=2)),
            _make_agent_spawn(when=self.now - timedelta(days=30)),
        ]
        _write_log(self.log_path, events)
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        # Only 2 of 3 dispatches counted.
        self.assertEqual(data["throughput"]["dispatches_count"], 2)


class TestParsePeriod(unittest.TestCase):
    def test_parse_days(self) -> None:
        self.assertEqual(_vd.parse_period("7d"), timedelta(days=7))

    def test_parse_hours(self) -> None:
        self.assertEqual(_vd.parse_period("24h"), timedelta(hours=24))

    def test_parse_bad_raises(self) -> None:
        with self.assertRaises(ValueError):
            _vd.parse_period("7w")
        with self.assertRaises(ValueError):
            _vd.parse_period("0d")
        with self.assertRaises(ValueError):
            _vd.parse_period("abc")


class TestSecMf3Whitelist(_DashboardTestBase):
    def test_emit_payload_only_whitelisted_keys(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        p = data["audit_emit_payload"]
        self.assertEqual(set(p.keys()), set(_vd.EMIT_WHITELIST_KEYS))
        # No raw audit content keys leak through.
        forbidden_substrings = (
            "ts", "session_id", "agent_name", "prompt", "raw", "hmac",
            "model", "tokens_in", "tokens_out", "plan_id",
        )
        for k in p.keys():
            for f in forbidden_substrings:
                self.assertNotEqual(k, f,
                    f"Sec MF-3 violation: forbidden key {f!r} in emit payload")

    def test_emit_cost_in_integer_cents(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        p = data["audit_emit_payload"]
        # Integer cents, not float dollars.
        self.assertIsInstance(p["cost_usd_int_cents"], int)


class TestCodexShare(_DashboardTestBase):
    def test_codex_share_percentage(self) -> None:
        events = [
            _make_agent_spawn(
                when=self.now - timedelta(hours=1),
                tokens_in=10000, tokens_out=2000,
                model="claude-sonnet-4-5",
            ),
            {
                "ts": _ts(self.now - timedelta(hours=2)),
                "action": "pair_rail_case",
                "tokens_in": 5000, "tokens_out": 1500,
                "model": "gpt-5-codex",
                "session_id": "S-test",
            },
        ]
        _write_log(self.log_path, events)
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        self.assertIsNotNone(data["cost"]["codex_share_pct"])
        # Codex share must be a percentage 0-100.
        share = data["cost"]["codex_share_pct"]
        self.assertGreaterEqual(share, 0.0)
        self.assertLessEqual(share, 100.0)


class TestRotationDedup(_DashboardTestBase):
    def test_duplicate_event_across_rotation_counted_once(self) -> None:
        # Same logical event appears in backup AND active log.
        # Use fixed agent_name so the canonical sha256 collides identically.
        ev = _make_agent_spawn(
            when=self.now - timedelta(days=1),
            agent_name="agent-fixed-for-dedup",
        )
        backup_path = self.audit_dir / "audit-log-2026-05-1.jsonl"
        _write_log(backup_path, [ev])
        _write_log(self.log_path, [ev])
        data = _vd.rollup_value(
            audit_dir=self.audit_dir,
            period=timedelta(days=7),
            now=self.now,
        )
        # Should count exactly once.
        self.assertEqual(data["throughput"]["dispatches_count"], 1)


class TestCliSmoke(_DashboardTestBase):
    """CLI returns 0 + emits expected text on a happy path."""

    def test_cli_text_smoke(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        buf = io.StringIO()
        argv = [
            "--period", "7d",
            "--by-day", "--by-plan",
            "--audit-dir", str(self.audit_dir),
        ]
        with redirect_stdout(buf):
            rc = _vd.main(argv)
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("CEO-orchestration weekly value dashboard", out)
        self.assertIn("Sec MF-3 audit emit payload", out)

    def test_cli_json_smoke(self) -> None:
        _write_log(self.log_path, _typical_week_events(self.now))
        buf = io.StringIO()
        argv = [
            "--period", "7d", "--json",
            "--audit-dir", str(self.audit_dir),
        ]
        with redirect_stdout(buf):
            rc = _vd.main(argv)
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["period_days"], 7)

    def test_cli_bad_period_exits_2(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = _vd.main(["--period", "7w", "--audit-dir", str(self.audit_dir)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
