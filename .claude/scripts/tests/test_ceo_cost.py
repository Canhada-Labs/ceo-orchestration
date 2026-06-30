"""Unit tests for ceo-cost.py.

Stdlib-only via unittest.discover compatible. Builds a temp audit log
fixture in-memory, runs aggregate(), asserts $ math + warning cases.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _load_module():
    """Load ceo-cost.py as a module despite the dash in the filename."""
    here = Path(__file__).resolve().parent.parent
    src = here / "ceo-cost.py"
    spec = importlib.util.spec_from_file_location("ceo_cost", src)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


cc = _load_module()


def _ts(offset_hours: float = 0) -> str:
    """ISO ts at now + offset (negative = past)."""
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


def _entry(**fields):
    base = {
        "action": "agent_spawn",
        "ts": _ts(),
        "session_id": "test-session-1",
        "skill": "code-review-checklist",
        "subagent_type": "code-reviewer",
        "model": "claude-opus-4-7",
        "tokens_in": 10000,
        "tokens_out": 2000,
    }
    base.update(fields)
    return base


def _write_log(path: Path, entries):
    with path.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


class CostMathTests(unittest.TestCase):
    """Cost calculations match ADR-052 pricing exactly."""

    def test_opus_cost(self):
        # 1M input + 1M output of Opus = $15 + $75 = $90
        c = cc.cost_usd(cc._DEFAULT_PRICING, "claude-opus-4-7", 1_000_000, 1_000_000)
        self.assertAlmostEqual(c, 90.0, places=4)

    def test_sonnet_cost(self):
        # 1M input + 1M output of Sonnet = $3 + $15 = $18
        c = cc.cost_usd(cc._DEFAULT_PRICING, "claude-sonnet-4-6", 1_000_000, 1_000_000)
        self.assertAlmostEqual(c, 18.0, places=4)

    def test_haiku_cost(self):
        # 1M input + 1M output of Haiku = $1.00 + $5.00 = $6.00
        # (Wave B 2026-04-27 rate alignment per audit-v2 C3-P0-06.)
        c = cc.cost_usd(cc._DEFAULT_PRICING, "claude-haiku-4-5-20251001", 1_000_000, 1_000_000)
        self.assertAlmostEqual(c, 6.00, places=4)

    def test_unknown_model_zero(self):
        c = cc.cost_usd(cc._DEFAULT_PRICING, "some-future-model", 1_000_000, 1_000_000)
        self.assertEqual(c, 0.0)


class AggregateTests(unittest.TestCase):
    """End-to-end aggregation against a temp audit log."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-cost-test-")).resolve()
        self.log = self.tmp / "audit-log.jsonl"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_aggregates_per_model(self):
        _write_log(self.log, [
            _entry(model="claude-opus-4-7", tokens_in=10000, tokens_out=2000),
            _entry(model="claude-sonnet-4-6", tokens_in=20000, tokens_out=5000),
            _entry(model="claude-haiku-4-5-20251001", tokens_in=8000, tokens_out=2000),
            _entry(model="claude-opus-4-7", tokens_in=5000, tokens_out=1000),
        ])
        entries = cc.read_entries([self.log])
        agg = cc.aggregate(entries, since=None, pricing=cc._DEFAULT_PRICING)

        self.assertEqual(agg["totals"]["spawns"], 4)
        # Opus: (15k * $15/M) + (3k * $75/M) = $0.225 + $0.225 = $0.45
        opus = agg["by_model"]["claude-opus-4-7"]
        self.assertEqual(opus["spawns"], 2)
        self.assertEqual(opus["tokens_in"], 15000)
        self.assertEqual(opus["tokens_out"], 3000)
        self.assertAlmostEqual(opus["cost_usd"], 0.45, places=4)

        # Sonnet: (20k * $3/M) + (5k * $15/M) = $0.060 + $0.075 = $0.135
        son = agg["by_model"]["claude-sonnet-4-6"]
        self.assertAlmostEqual(son["cost_usd"], 0.135, places=4)

        # Haiku: (8k * $1/M) + (2k * $5/M) = $0.008 + $0.010 = $0.018
        # (Wave B 2026-04-27 rate alignment per audit-v2 C3-P0-06.)
        hai = agg["by_model"]["claude-haiku-4-5-20251001"]
        self.assertAlmostEqual(hai["cost_usd"], 0.018, places=5)

    def test_warns_on_missing_tokens(self):
        _write_log(self.log, [
            _entry(model="claude-opus-4-7", tokens_in=None, tokens_out=None),
            _entry(model="claude-opus-4-7"),
        ])
        agg = cc.aggregate(cc.read_entries([self.log]), since=None, pricing=cc._DEFAULT_PRICING)
        self.assertEqual(agg["totals"]["spawns"], 2)
        self.assertEqual(agg["totals"]["spawns_without_tokens"], 1)

    def test_warns_on_missing_model(self):
        e1 = _entry()
        del e1["model"]
        e2 = _entry(model="")
        _write_log(self.log, [e1, e2])
        agg = cc.aggregate(cc.read_entries([self.log]), since=None, pricing=cc._DEFAULT_PRICING)
        self.assertEqual(agg["totals"]["spawns"], 2)
        self.assertEqual(agg["totals"]["spawns_without_model"], 2)
        # Both bucketed under unknown_model
        self.assertEqual(agg["by_model"][cc._UNKNOWN_MODEL]["spawns"], 2)

    def test_since_filter_drops_old(self):
        old = _entry(model="claude-opus-4-7", ts=_ts(-72))   # 3 days ago
        new = _entry(model="claude-opus-4-7", ts=_ts(-1))    # 1 hour ago
        _write_log(self.log, [old, new])
        agg = cc.aggregate(
            cc.read_entries([self.log]),
            since=cc.parse_since("24h"),
            pricing=cc._DEFAULT_PRICING,
        )
        self.assertEqual(agg["totals"]["spawns"], 1)

    def test_skips_non_agent_spawn_entries(self):
        _write_log(self.log, [
            _entry(model="claude-opus-4-7"),
            {"action": "veto_triggered", "ts": _ts(), "reason_code": "x"},
            {"action": "debate_event", "ts": _ts()},
        ])
        agg = cc.aggregate(cc.read_entries([self.log]), since=None, pricing=cc._DEFAULT_PRICING)
        self.assertEqual(agg["totals"]["spawns"], 1)


class CLITests(unittest.TestCase):
    """Smoke test the CLI entry point."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-cost-cli-")).resolve()
        self.log = self.tmp / "audit-log.jsonl"
        _write_log(self.log, [_entry()])

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_capture(self, argv):
        """Run main() and capture stdout."""
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            rc = cc.main(argv)
        finally:
            stdout = sys.stdout.getvalue()
            stderr = sys.stderr.getvalue()
            sys.stdout, sys.stderr = old_stdout, old_stderr
        return rc, stdout, stderr

    def test_cli_text(self):
        rc, out, err = self._run_capture(["--log", str(self.log), "--since", "all"])
        self.assertEqual(rc, 0)
        self.assertIn("by=by-model", out)
        self.assertIn("TOTAL", out)

    def test_cli_json(self):
        rc, out, err = self._run_capture(["--log", str(self.log), "--since", "all", "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["totals"]["spawns"], 1)
        self.assertIn("claude-opus-4-7", payload["by_model"])

    def test_cli_missing_log(self):
        rc, out, err = self._run_capture(["--log", str(self.tmp / "nope.jsonl"), "--since", "all"])
        self.assertEqual(rc, 1)
        self.assertIn("not found", err)

    def test_pricing_override_via_env(self):
        custom_pricing = {
            "claude-opus-4-7": {"input_per_mtok": 100.0, "output_per_mtok": 100.0},
        }
        pricing_path = self.tmp / "pricing.json"
        pricing_path.write_text(json.dumps(custom_pricing), encoding="utf-8")
        os.environ["CEO_COST_PRICING_JSON"] = str(pricing_path)
        try:
            p = cc.load_pricing()
            self.assertEqual(p["claude-opus-4-7"]["input_per_mtok"], 100.0)
        finally:
            del os.environ["CEO_COST_PRICING_JSON"]


if __name__ == "__main__":
    unittest.main()
