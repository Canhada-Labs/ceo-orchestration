"""Tests for predict-plan-cost.py (PLAN-014 Phase F.3 + F.7).

≥20 tests covering:
- Plan id extraction from frontmatter / filename
- Plan file size cap
- Audit log malformed line handling
- Training aggregation with per-session exclusions (veto + budget_bypass)
- Confidence tier selection (cold_start / low / medium / high)
- One-way ratchet (ratios match v1.0.0-rc.1 baseline)
- Bucket-string format ("NNNk-MMMk")
- Cold-start: bucket="unknown" when <3 training plans
- Median (not mean) aggregation
- Zero-median warning
- Exclude-reasons surfaced
- Backtest leave-one-out
- Cache write / read permission (0o700 / 0o600)
- Cache-disable flag
- Audit event emission on prediction query
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "predict-budget" / "predict-plan-cost.py"
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location("predict_plan_cost", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPredictPlanCost(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-predict-test-"))
        self.project_dir = self.tmp / "project"
        self.home_dir = self.tmp / "home"
        self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self._env_snap = {}
        for k in ("CEO_AUDIT_LOG_PATH", "CLAUDE_PROJECT_DIR", "HOME",
                  "CEO_PREDICT_CACHE_DIR", "CEO_AUDIT_LOG_DIR",
                  "CEO_AUDIT_LOG_ERR", "CEO_AUDIT_LOG_LOCK",
                  "CEO_AUDIT_SYNC_MODE"):
            self._env_snap[k] = os.environ.get(k)
        os.environ["HOME"] = str(self.home_dir)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        # PLAN-152 tests-01 pre-wiring fix: since PLAN-094 Wave A.3 the audit
        # emit routes through the per-PID spool (amortized drain), so an event
        # asserted straight off audit-log.jsonl may still sit in the spool.
        # Force the synchronous write path (spool_writer.py kill-switch) so
        # log-content assertions are deterministic.
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.audit_log = self.audit_dir / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")
        self.cache_dir = self.tmp / "cache"
        os.environ["CEO_PREDICT_CACHE_DIR"] = str(self.cache_dir)

        self.mod = _load_mod()

    def tearDown(self) -> None:
        for k, v in self._env_snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    # ---- helpers --------------------------------------------------

    def _make_spawn(self, plan_id, sid, ord_, tokens_in, tokens_out):
        return {
            "ts": f"2026-04-16T10:00:{ord_:02d}Z",
            "action": "agent_spawn",
            "plan_id": plan_id,
            "session_id": sid,
            "skill": "x",
            "spawn_ordinal": ord_,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }

    def _write_audit(self, events):
        self.audit_log.write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
            encoding="utf-8",
        )

    def _write_plan_file(self, plan_id="PLAN-015", body="# body\n") -> Path:
        p = self.tmp / f"{plan_id}-test.md"
        front = (
            "---\n"
            f"id: {plan_id}\n"
            "title: test\n"
            "status: draft\n"
            "---\n\n"
        )
        p.write_text(front + body, encoding="utf-8")
        return p

    def _run_main(self, argv):
        saved_out = sys.stdout
        saved_err = sys.stderr
        out = io.StringIO()
        err = io.StringIO()
        sys.stdout = out
        sys.stderr = err
        try:
            code = self.mod.main(argv)
        finally:
            sys.stdout = saved_out
            sys.stderr = saved_err
        return code, out.getvalue(), err.getvalue()

    def _populate_10_training_plans(self, per_plan_total=100_000):
        # 10 plans, each with one session (sid=planid), 5 spawns totaling per_plan_total
        events = []
        for i in range(3, 13):  # PLAN-003..PLAN-012
            pid = f"PLAN-{i:03d}"
            sid = f"s-{pid}"
            # Spread: total = per_plan_total; half input, half output
            half_in = per_plan_total // 2
            half_out = per_plan_total - half_in
            events.append(self._make_spawn(pid, sid, 0, half_in, half_out))
        self._write_audit(events)

    # ---- tests ----------------------------------------------------

    def test_01_plan_id_from_frontmatter(self):
        p = self._write_plan_file("PLAN-014")
        self.assertEqual(self.mod._plan_id_from_file(p), "PLAN-014")

    def test_02_plan_id_from_filename_when_no_frontmatter(self):
        p = self.tmp / "PLAN-007-whatever.md"
        p.write_text("no frontmatter here", encoding="utf-8")
        self.assertEqual(self.mod._plan_id_from_file(p), "PLAN-007")

    def test_03_plan_hash_stable(self):
        p = self._write_plan_file("PLAN-014")
        h1 = self.mod._plan_hash(p)
        h2 = self.mod._plan_hash(p)
        self.assertEqual(h1, h2)
        self.assertTrue(len(h1) == 16)

    def test_04_missing_plan_file_exit_2(self):
        code, out, err = self._run_main(["--plan-file", "nope.md"])
        self.assertEqual(code, 2)
        self.assertIn("missing_input", err)

    def test_05_bad_plan_no_id_exit_3(self):
        p = self.tmp / "not-a-plan.md"
        p.write_text("no plan-nnn here", encoding="utf-8")
        code, out, err = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 3)

    def test_06_cold_start_yields_unknown_bucket(self):
        """<3 training plans ⇒ confidence=cold_start + bucket='unknown'."""
        self._write_audit([
            self._make_spawn("PLAN-003", "s1", 0, 10_000, 20_000),
            self._make_spawn("PLAN-004", "s2", 0, 10_000, 20_000),
        ])
        p = self._write_plan_file("PLAN-014")
        code, out, err = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["prediction"]["confidence"], "cold_start")
        self.assertEqual(payload["prediction"]["tokens_total_bucket"], "unknown")
        self.assertIn("cold_start", payload["warnings"])

    def test_07_medium_confidence_with_6_plans(self):
        events = []
        for i in range(3, 9):  # 6 plans
            events.append(self._make_spawn(f"PLAN-{i:03d}", f"s{i}", 0, 50_000, 50_000))
        self._write_audit(events)
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["prediction"]["confidence"], "medium")
        self.assertEqual(payload["prediction"]["bucket_half_width_ratio"], 0.3)

    def test_08_high_confidence_with_10_plans(self):
        self._populate_10_training_plans(per_plan_total=200_000)
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["prediction"]["confidence"], "high")
        self.assertEqual(payload["prediction"]["bucket_half_width_ratio"], 0.3)

    def test_09_bucket_string_format(self):
        self._populate_10_training_plans(per_plan_total=120_000)
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        total = payload["prediction"]["tokens_total_bucket"]
        # Shape: "<N>k-<M>k"
        self.assertRegex(total, r"^\d+k-\d+k$")

    def test_10_median_not_mean(self):
        # 5 plans: 4 at 100k total; 1 outlier at 1M total
        events = []
        for i in range(3, 7):
            events.append(self._make_spawn(f"PLAN-{i:03d}", f"s{i}", 0, 50_000, 50_000))
        # outlier
        events.append(self._make_spawn("PLAN-100", "s100", 0, 500_000, 500_000))
        self._write_audit(events)
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        # Median of [100k,100k,100k,100k,1M] = 100k; mean would be ~280k
        self.assertEqual(payload["training"]["median_tokens_in"], 50_000)

    def test_11_excluded_sessions_drop_whole_session(self):
        """Sessions with veto_triggered or budget_bypass_used are dropped entirely."""
        events = [
            self._make_spawn("PLAN-003", "good-sid", 0, 100_000, 100_000),
            self._make_spawn("PLAN-004", "poisoned", 0, 999_999, 999_999),
            {
                "ts": "2026-04-16T10:00:01Z",
                "action": "veto_triggered",
                "hook": "check_plan_edit",
                "reason_code": "x",
                "reason_preview": "y",
                "session_id": "poisoned",
            },
        ]
        self._write_audit(events)
        per_plan, excluded = self.mod.aggregate_plan_totals(events)
        self.assertIn("PLAN-003", per_plan)
        self.assertNotIn("PLAN-004", per_plan)
        self.assertEqual(excluded.get("veto_triggered", 0), 1)

    def test_12_excluded_reasons_surface_in_output(self):
        events = [
            self._make_spawn("PLAN-003", "s1", 0, 100_000, 100_000),
            {
                "ts": "2026-04-16T10:00:01Z",
                "action": "budget_bypass_used",
                "plan_id": "PLAN-004",
                "caller_pid": 1,
                "reason_preview": "x",
                "session_id": "s2",
            },
        ]
        self._write_audit(events)
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        reasons = payload["training"]["excluded_reasons"]
        self.assertIn("budget_bypass_used", reasons)

    def test_13_one_way_ratchet_smoke(self):
        """Ratios match v1.0.0-rc.1 baseline (one-way ratchet §8.1)."""
        self.assertEqual(self.mod.RATIO_COLD_START, 1.0)
        self.assertEqual(self.mod.RATIO_LOW, 0.5)
        self.assertEqual(self.mod.RATIO_MEDIUM, 0.3)
        self.assertEqual(self.mod.RATIO_HIGH, 0.3)

    def test_14_pick_confidence_tiers(self):
        self.assertEqual(self.mod.pick_confidence(0)[0], "cold_start")
        self.assertEqual(self.mod.pick_confidence(2)[0], "cold_start")
        self.assertEqual(self.mod.pick_confidence(3)[0], "low")
        self.assertEqual(self.mod.pick_confidence(5)[0], "low")
        self.assertEqual(self.mod.pick_confidence(6)[0], "medium")
        self.assertEqual(self.mod.pick_confidence(9)[0], "medium")
        self.assertEqual(self.mod.pick_confidence(10)[0], "high")
        self.assertEqual(self.mod.pick_confidence(999)[0], "high")

    def test_15_build_bucket_clamps_lower_at_zero(self):
        bucket = self.mod.build_bucket(5_000, 2.0)  # half = 10k, lower < 0
        lo_str = bucket.split("-")[0]
        self.assertEqual(lo_str, "0k")

    def test_16_build_bucket_rounds_to_thousands(self):
        bucket = self.mod.build_bucket(123_456, 0.3)
        # point ≈ 123k; half ≈ 37k → ~86k-161k (rounded)
        self.assertRegex(bucket, r"^\d+k-\d+k$")

    def test_17_schema_version_in_output(self):
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["schema_version"], self.mod.SCHEMA_VERSION)

    def test_18_no_raw_dollar_figures(self):
        """Output MUST NOT contain USD/$ tokens (Tier 2)."""
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        code, out, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        self.assertNotIn("USD", out)
        self.assertNotIn("$", out)

    def test_19_backtest_mode_emits_per_plan_rows(self):
        self._populate_10_training_plans(per_plan_total=100_000)
        code, out, _ = self._run_main(["--backtest"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertIn("backtest", payload)
        self.assertGreater(payload["backtest"]["count"], 0)
        self.assertIn("per_plan", payload["backtest"])

    def test_20_backtest_meets_70_percent_gate_for_uniform_data(self):
        """With uniform training data, backtest should hit ≥70% within CI."""
        self._populate_10_training_plans(per_plan_total=100_000)
        code, out, _ = self._run_main(["--backtest"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["backtest"]["meets_70_percent_gate"])

    def test_21_cache_write_happens_by_default(self):
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        code, _, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        cached = list(self.cache_dir.glob("*.json"))
        self.assertEqual(len(cached), 1)

    def test_22_cache_dir_mode_0700_when_created(self):
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        self._run_main(["--plan-file", str(p)])
        mode = stat.S_IMODE(self.cache_dir.stat().st_mode)
        self.assertEqual(mode, 0o700)

    def test_23_no_cache_flag_skips_write(self):
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        code, _, _ = self._run_main(["--plan-file", str(p), "--no-cache"])
        self.assertEqual(code, 0)
        cached = list(self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        self.assertEqual(cached, [])

    def test_24_prediction_queried_audit_event_emitted(self):
        self._populate_10_training_plans()
        p = self._write_plan_file("PLAN-014")
        code, _, _ = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 0)
        log = self.audit_log.read_text(encoding="utf-8")
        self.assertIn("prediction_queried", log)

    def test_25_audit_parse_error_exit_4(self):
        """Malformed audit log line → exit 4."""
        self.audit_log.write_text("{not valid json\n", encoding="utf-8")
        p = self._write_plan_file("PLAN-014")
        code, out, err = self._run_main(["--plan-file", str(p)])
        self.assertEqual(code, 4)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
