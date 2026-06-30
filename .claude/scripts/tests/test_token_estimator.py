"""Tests for token-estimator.py — PLAN-083 Wave 0a sub-0.2.

Stdlib-only unittest. Imports the staging script directly (no install).
Run from staging dir::

    python3 -m unittest tests.test_token_estimator -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import textwrap
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

# Load the staging script via importlib (its filename has a dash → not importable
# as a module via normal `import token-estimator`).
import importlib.util

_THIS_DIR = Path(__file__).resolve().parent
_SCRIPT_PATH = _THIS_DIR.parent / "token-estimator.py"
_COST_TABLE_PATH = _THIS_DIR.parent / "cost-table.yaml"

_spec = importlib.util.spec_from_file_location("token_estimator", _SCRIPT_PATH)
te = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(te)  # type: ignore[union-attr]


SAMPLE_PLAN = textwrap.dedent("""\
    # PLAN-999 — sample for tests

    Some prose.

    ### §5.1 Wave 0a — Velocity primitives (parallel ≤6 sub-agents)

    Some intro text.

    | # | Sub-agent | Tier | Deliverable | Files affected | Est tokens |
    |---|---|---|---|---|---|
    | 0.1 | general-purpose | Sonnet | foo | a.py | 80k |
    | 0.2 | general-purpose | Sonnet | bar | b.py | 90k |
    | 0.3 | general-purpose | Sonnet | baz | c.py | 60k |
    | 0.4 | general-purpose | Sonnet | qux | d.py | 120k |
    | 0.5 | general-purpose | Sonnet | quux | e.py | 90k |
    | 0.6 | general-purpose | Sonnet | corge | f.py | 70k |

    Some outro.

    ### §5.2 Wave 0b — Smart-loading completion

    | # | Sub-agent | Tier | Deliverable | Files affected | Est tokens |
    |---|---|---|---|---|---|
    | 0.7b | general-purpose | Sonnet | x | y.py | 60k |
    | 0.7c | general-purpose | Sonnet | y | z.py | 100k |

    ### §5.99 Wave Misc — without table

    Just prose, no estimate table.
""")


def _write_sample_plan(tmpdir: Path) -> Path:
    p = tmpdir / "PLAN-999-test.md"
    p.write_text(SAMPLE_PLAN, encoding="utf-8")
    return p


class TestParseTokenCell(unittest.TestCase):
    def test_simple_k(self) -> None:
        self.assertEqual(te.parse_token_cell("90k"), (90000.0, 90000.0))

    def test_range_with_unit(self) -> None:
        self.assertEqual(te.parse_token_cell("1.3-2M"), (1_300_000.0, 2_000_000.0))

    def test_na_returns_none(self) -> None:
        self.assertIsNone(te.parse_token_cell("n/a"))
        self.assertIsNone(te.parse_token_cell(""))
        self.assertIsNone(te.parse_token_cell("tbd"))


class TestCoerceScalar(unittest.TestCase):
    def test_int_float_bool_date(self) -> None:
        self.assertEqual(te._coerce_scalar("42"), 42)
        self.assertEqual(te._coerce_scalar("3.14"), 3.14)
        self.assertEqual(te._coerce_scalar("true"), True)
        self.assertEqual(te._coerce_scalar("2026-08-11"), date(2026, 8, 11))

    def test_quoted_string(self) -> None:
        self.assertEqual(te._coerce_scalar('"hello"'), "hello")
        self.assertEqual(te._coerce_scalar("'world'"), "world")


class TestLoadCostTable(unittest.TestCase):
    def test_loads_default_table(self) -> None:
        table = te.load_cost_table(_COST_TABLE_PATH)
        self.assertIn("models", table)
        self.assertIn("claude-sonnet-4-6", table["models"])
        self.assertEqual(table["default_model"], "claude-sonnet-4-6")
        self.assertIsInstance(table["cost_table_valid_until"], date)

    def test_rejects_anchor_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.yaml"
            bad.write_text("foo: &anchor 1\nbar: *anchor\n", encoding="utf-8")
            with self.assertRaises(te.CostTableError):
                te.load_cost_table(bad)

    def test_missing_table(self) -> None:
        with self.assertRaises(te.CostTableError):
            te.load_cost_table(Path("/nonexistent/cost-table.yaml"))


class TestPricingStaleness(unittest.TestCase):
    def test_not_stale_when_today_before_valid_until(self) -> None:
        table = {"cost_table_valid_until": date(2099, 1, 1)}
        stale, msg = te.check_cost_table_staleness(table, today=date(2026, 5, 11))
        self.assertFalse(stale)
        self.assertEqual(msg, "")

    def test_stale_when_today_after_valid_until(self) -> None:
        table = {"cost_table_valid_until": date(2026, 1, 1)}
        stale, msg = te.check_cost_table_staleness(table, today=date(2026, 5, 11))
        self.assertTrue(stale)
        self.assertIn("expired", msg)
        self.assertIn("130", msg)  # ~130 days over

    def test_stale_message_includes_iso_date(self) -> None:
        table = {"cost_table_valid_until": date(2026, 1, 1)}
        _, msg = te.check_cost_table_staleness(table, today=date(2026, 5, 11))
        self.assertIn("2026-01-01", msg)


class TestParsePlanEstimates(unittest.TestCase):
    def test_extracts_six_sub_agents_from_wave_0a(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = _write_sample_plan(Path(td))
            parsed = te.parse_plan_estimates(plan_path)
            wave_0a = next(w for w in parsed["waves"] if "0a" in w["wave"])
            self.assertEqual(len(wave_0a["sub_agents"]), 6)
            # 80+90+60+120+90+70 = 510k
            self.assertEqual(wave_0a["tokens_low"], 510_000)
            self.assertEqual(wave_0a["tokens_high"], 510_000)

    def test_total_across_waves(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = _write_sample_plan(Path(td))
            parsed = te.parse_plan_estimates(plan_path)
            # 510k (0a) + 160k (0b) = 670k
            self.assertEqual(parsed["total_tokens_low"], 670_000)
            self.assertEqual(parsed["total_sub_agents"], 8)

    def test_skips_wave_without_table(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = _write_sample_plan(Path(td))
            parsed = te.parse_plan_estimates(plan_path)
            wave_labels = [w["wave"] for w in parsed["waves"]]
            self.assertTrue(any("Misc" not in w for w in wave_labels))
            self.assertEqual(len(parsed["waves"]), 2)  # only 0a + 0b


class TestComputeEstimate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.plan_path = _write_sample_plan(Path(self.tmpdir.name))
        self.table = te.load_cost_table(_COST_TABLE_PATH)

    def test_sonnet_pricing(self) -> None:
        parsed = te.parse_plan_estimates(self.plan_path)
        est = te.compute_estimate(parsed, self.table, model="claude-sonnet-4-6")
        # Sonnet $3/$15 per MTok blended 80/20:
        # 670_000 tokens → in=536k @ $3 = $1.608 + out=134k @ $15 = $2.010 = $3.618
        self.assertAlmostEqual(est["total_usd_low"], 3.618, places=3)
        self.assertEqual(est["model"], "claude-sonnet-4-6")

    def test_opus_more_expensive_than_haiku(self) -> None:
        parsed = te.parse_plan_estimates(self.plan_path)
        opus = te.compute_estimate(parsed, self.table, model="claude-opus-4-7")
        haiku = te.compute_estimate(parsed, self.table, model="claude-haiku-4-5")
        self.assertGreater(opus["total_usd_low"], haiku["total_usd_low"])
        self.assertGreater(opus["total_usd_low"], 4.0)  # rough sanity (opus $5/$25 per ratified 2026-06-10 rate card; was 15.0 under the stale $15/$75 row)

    def test_paralelizado_ceiling_applied(self) -> None:
        parsed = te.parse_plan_estimates(self.plan_path)
        est = te.compute_estimate(parsed, self.table)
        wave_0a = next(w for w in est["per_wave"] if "0a" in w["wave"])
        # Wave 0a has 6 sub-agents → effective_workers = min(6, 6) = 6
        self.assertEqual(wave_0a["effective_workers"], 6)
        # Sequential / parallel ratio = 6
        self.assertAlmostEqual(
            wave_0a["wallclock_sequential_seconds_low"]
            / wave_0a["wallclock_paralelizado_seconds_low"],
            6.0,
            places=2,
        )

    def test_unknown_model_raises(self) -> None:
        parsed = te.parse_plan_estimates(self.plan_path)
        with self.assertRaises(ValueError):
            te.compute_estimate(parsed, self.table, model="gpt-9000")


class TestWallclockMilestones(unittest.TestCase):
    def _write_log(self, tmpdir: Path, events: list) -> Path:
        log = tmpdir / "audit-log.jsonl"
        with log.open("w", encoding="utf-8") as fh:
            for e in events:
                fh.write(json.dumps(e) + "\n")
        return log

    def test_empty_when_log_missing(self) -> None:
        report = te.read_wallclock_milestones(
            "PLAN-083",
            log_path=Path("/nonexistent/audit-log.jsonl"),
        )
        self.assertEqual(report["milestones"], [])
        self.assertIsNone(report["started_at"])
        self.assertTrue(any("not found" in w for w in report["warnings"]))

    def test_sums_elapsed_across_milestones(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            t0 = datetime(2026, 5, 11, 10, 0, 0, tzinfo=timezone.utc)
            events = [
                {"action": "wallclock_milestone_started",
                 "plan_id": "PLAN-083", "ts": t0.isoformat()},
                {"action": "wallclock_milestone",
                 "plan_id": "PLAN-083",
                 "wave": "0a",
                 "ts": (t0 + timedelta(hours=1)).isoformat()},
                {"action": "wallclock_milestone",
                 "plan_id": "PLAN-083",
                 "wave": "0b",
                 "ts": (t0 + timedelta(hours=2)).isoformat()},
                {"action": "wallclock_milestone_finished",
                 "plan_id": "PLAN-083",
                 "ts": (t0 + timedelta(hours=3)).isoformat()},
                # Noise — different plan_id, ignored
                {"action": "wallclock_milestone",
                 "plan_id": "PLAN-001",
                 "wave": "0a",
                 "ts": (t0 + timedelta(hours=99)).isoformat()},
            ]
            log = self._write_log(Path(td), events)
            report = te.read_wallclock_milestones("PLAN-083", log_path=log)
            self.assertEqual(report["plan_id"], "PLAN-083")
            self.assertEqual(len(report["milestones"]), 2)
            self.assertEqual(report["milestones"][0]["wave"], "0a")
            self.assertEqual(report["milestones"][0]["elapsed_since_start_seconds"], 3600.0)
            self.assertEqual(report["elapsed_seconds"], 10800.0)
            # per_wave intervals: start→0a, 0a→0b
            self.assertEqual(len(report["per_wave"]), 2)
            self.assertEqual(report["per_wave"][0]["elapsed_seconds"], 3600.0)

    def test_invalid_plan_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            te.read_wallclock_milestones("BAD-FORMAT")
        with self.assertRaises(ValueError):
            te.read_wallclock_milestones("PLAN-XX")

    def test_malformed_lines_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit-log.jsonl"
            log.write_text(
                "not-json-at-all\n"
                + json.dumps({"action": "wallclock_milestone_started",
                              "plan_id": "PLAN-083",
                              "ts": "2026-05-11T10:00:00+00:00"}) + "\n"
                + "{\"truncated\":\n",
                encoding="utf-8",
            )
            report = te.read_wallclock_milestones("PLAN-083", log_path=log)
            self.assertEqual(report["started_at"], "2026-05-11T10:00:00+00:00")


class TestJsonOutputSchema(unittest.TestCase):
    def test_estimate_json_has_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            plan_path = _write_sample_plan(Path(td))
            argv = ["estimate", "--input-file", str(plan_path), "--json"]
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = te.main(argv)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            for required in (
                "plan_path", "model", "total_sub_agents",
                "total_tokens_low", "total_tokens_high",
                "total_usd_low", "total_usd_high",
                "total_wallclock_paralelizado_seconds_low",
                "cost_table_valid_until", "per_wave",
            ):
                self.assertIn(required, payload)

    def test_wallclock_json_has_expected_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            argv = [
                "wallclock", "--plan-id", "PLAN-083",
                "--log-path", str(Path(td) / "missing.jsonl"),
                "--json",
            ]
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = te.main(argv)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            for required in (
                "plan_id", "log_path", "started_at", "finished_at",
                "elapsed_seconds", "milestones", "per_wave", "warnings",
            ):
                self.assertIn(required, payload)


class TestCheckPricingStaleness(unittest.TestCase):
    def test_subcommand_exits_zero_when_fresh(self) -> None:
        # Build a synthetic far-future cost table.
        with tempfile.TemporaryDirectory() as td:
            tbl = Path(td) / "cost-table.yaml"
            tbl.write_text(textwrap.dedent("""\
                cost_table_valid_until: 2099-01-01
                last_verified_at: 2026-05-11
                default_model: claude-sonnet-4-6
                blended_input_share: 0.80
                blended_output_share: 0.20
                seconds_per_ktok: 4.0
                models:
                  claude-sonnet-4-6:
                    input_per_mtok: 3.00
                    output_per_mtok: 15.00
                    tier: sonnet
                    source_url: "x"
            """), encoding="utf-8")
            argv = ["check-pricing-staleness", "--cost-table", str(tbl), "--json"]
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = te.main(argv)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["stale"])

    def test_subcommand_exits_nonzero_when_stale(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tbl = Path(td) / "cost-table.yaml"
            tbl.write_text(textwrap.dedent("""\
                cost_table_valid_until: 2020-01-01
                last_verified_at: 2019-10-01
                default_model: claude-sonnet-4-6
                blended_input_share: 0.80
                blended_output_share: 0.20
                seconds_per_ktok: 4.0
                models:
                  claude-sonnet-4-6:
                    input_per_mtok: 3.00
                    output_per_mtok: 15.00
                    tier: sonnet
                    source_url: "x"
            """), encoding="utf-8")
            argv = ["check-pricing-staleness", "--cost-table", str(tbl), "--json"]
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = te.main(argv)
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["stale"])


class TestWaveTokenSanitization(unittest.TestCase):
    def test_log_derived_wave_string_sanitized(self) -> None:
        # Injected control char + path traversal sequence → must collapse to 'unknown'.
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "audit-log.jsonl"
            log.write_text(
                json.dumps({
                    "action": "wallclock_milestone_started",
                    "plan_id": "PLAN-083",
                    "ts": "2026-05-11T10:00:00+00:00",
                }) + "\n"
                + json.dumps({
                    "action": "wallclock_milestone",
                    "plan_id": "PLAN-083",
                    "wave": "../../../etc/passwd\n",
                    "ts": "2026-05-11T11:00:00+00:00",
                }) + "\n",
                encoding="utf-8",
            )
            report = te.read_wallclock_milestones("PLAN-083", log_path=log)
            self.assertEqual(report["milestones"][0]["wave"], "unknown")


if __name__ == "__main__":
    unittest.main()
