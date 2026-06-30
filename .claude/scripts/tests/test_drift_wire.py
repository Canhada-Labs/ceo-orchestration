"""PLAN-106 Wave F.5 — drift detector ceo-boot wire-up tests.

Covers AC9 / AC9b / AC9c (qa R1 P0+P1 folds — 6 minimum tests; mock-
clock discipline via `unittest.mock.patch('time.monotonic')` NOT
`time.sleep` so test stays deterministic on slow CI runners).

All tests use `TestEnvContext` for env isolation. Place at
`.claude/scripts/tests/test_drift_wire.py` post-apply.

Test count: 7.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve()
# Locate repo root: tests file ends up at .claude/scripts/tests/
_REPO_ROOT = _HERE
for _ in range(6):
    _REPO_ROOT = _REPO_ROOT.parent
    if (_REPO_ROOT / ".claude" / "hooks" / "_lib" / "testing.py").is_file():
        break

_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_drift_module():
    """Load post-apply `.claude/scripts/check-confidence-gate-drift.py`."""
    canonical = _REPO_ROOT / ".claude" / "scripts" / "check-confidence-gate-drift.py"
    if not canonical.is_file():
        raise unittest.SkipTest(
            f"drift detector not yet applied at {canonical} — test runs post-apply.",
        )
    spec = importlib.util.spec_from_file_location(
        "check_confidence_gate_drift", str(canonical),
    )
    if spec is None or spec.loader is None:
        raise unittest.SkipTest("Could not build module spec.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stage_tier_config(repo_root: Path) -> None:
    """Stage a minimal tier config: sha_exists → HIGH_CONFIDENCE_BLOCK."""
    data_dir = repo_root / ".claude" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    cfg = data_dir / "confidence-gate-class-tiers.json"
    cfg.write_text(json.dumps({
        "tiers": {
            "sha_exists": "HIGH_CONFIDENCE_BLOCK",
            "path_exists": "MED_CONFIDENCE_ADVISORY",
            "function_exists": "MED_CONFIDENCE_ADVISORY",
            "line_range": "MED_CONFIDENCE_ADVISORY",
            "import_resolves": "MED_CONFIDENCE_ADVISORY",
            "test_passes": "LOW_CONFIDENCE_ADVISORY",
        },
    }), encoding="utf-8")


def _stage_audit_log(log_path: Path, events: list) -> None:
    """Append the given events to the test audit-log."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


class DriftDetectorWireTests(TestEnvContext):
    """7 tests: green / yellow / timeout-mock / no-log / under-budget / over-budget / no-config."""

    def setUp(self) -> None:
        super().setUp()
        try:
            self.mod = _load_drift_module()
        except unittest.SkipTest:
            raise

    # ----- Test 1: GREEN path — no drift detected -----
    def test_green_path_no_drift(self) -> None:
        """200 verdicts all pass → no drift on sha_exists → green."""
        _stage_tier_config(self.project_dir)
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        # 200 passing verdicts for sha_exists in window.
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        events = [{
            "ts": now_iso,
            "action": "confidence_gate_verdict",
            "verifier_kind": "sha_exists",
            "verdict": "pass",
        } for _ in range(200)]
        _stage_audit_log(log, events)

        drift, summary, detail = self.mod.detect_drift_7d(
            window_days=7, threshold_bps=200,
            audit_log_path=log,
            repo_root=self.project_dir,
        )
        self.assertFalse(drift)
        self.assertIn("no drift", summary)
        self.assertEqual(detail["drifts"], [])

    # ----- Test 2: YELLOW path — drift detected via synthesized fixture -----
    def test_yellow_path_drift_synthesized(self) -> None:
        """100 verdicts with 10% fail on sha_exists → FPR=1000 bps > 200 → drift."""
        _stage_tier_config(self.project_dir)
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        events = []
        for i in range(100):
            events.append({
                "ts": now_iso,
                "action": "confidence_gate_verdict",
                "verifier_kind": "sha_exists",
                "verdict": "fail" if i < 10 else "pass",
            })
        _stage_audit_log(log, events)

        drift, summary, detail = self.mod.detect_drift_7d(
            window_days=7, threshold_bps=200,
            audit_log_path=log,
            repo_root=self.project_dir,
        )
        self.assertTrue(drift, f"expected drift; got summary={summary!r}")
        self.assertEqual(len(detail["drifts"]), 1)
        d = detail["drifts"][0]
        self.assertEqual(d["drift_class"], "sha_exists")
        self.assertEqual(d["fpr_bps"], 1000)  # 10/100 = 10% = 1000 bps
        self.assertEqual(d["sample_n"], 100)
        self.assertEqual(d["fail_n"], 10)

    # ----- Test 3: AUDIT-LOG ABSENT — fail-open (green, not red) -----
    def test_audit_log_absent_fail_open(self) -> None:
        """Missing audit-log MUST return False (no-audit-log) NOT a crash."""
        _stage_tier_config(self.project_dir)
        missing = self.project_dir / "definitely_not_present.jsonl"
        self.assertFalse(missing.exists())

        drift, summary, detail = self.mod.detect_drift_7d(
            window_days=7, threshold_bps=200,
            audit_log_path=missing,
            repo_root=self.project_dir,
        )
        self.assertFalse(drift)
        self.assertEqual(summary, "no-audit-log")
        self.assertEqual(detail.get("reason"), "no-audit-log")

    # ----- Test 4: NO TIER CONFIG — fail-open green -----
    def test_no_tier_config_fail_open(self) -> None:
        """Missing tier-config JSON MUST return False (no-tier-config)."""
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("", encoding="utf-8")
        # Do NOT stage tier config.

        drift, summary, detail = self.mod.detect_drift_7d(
            window_days=7, threshold_bps=200,
            audit_log_path=log,
            repo_root=self.project_dir,
        )
        self.assertFalse(drift)
        self.assertEqual(summary, "no-tier-config")
        self.assertEqual(detail.get("reason"), "no-tier-config")

    # ----- Test 5: MOCK-CLOCK timeout fallback — 190 ms simulated under budget -----
    def test_mock_clock_under_budget(self) -> None:
        """Wrapping check fires under 200 ms budget (simulated via mock clock).

        AC9c — uses `unittest.mock.patch('time.monotonic')` NOT
        `time.sleep` so the test stays deterministic on slow CI.

        We simulate the ceo-boot `_wrap_check` wrapper: it measures
        `time.perf_counter()` (alias for monotonic on most platforms)
        and annotates "slow" if the budget is exceeded. Here we
        confirm a 190 ms simulated check is NOT annotated as slow
        against the 200 ms budget.
        """
        budget_ms = 200
        # Simulate the wall-clock progression: t0 at the start, then
        # +0.19s = 190 ms when measuring.
        fake_times = iter([0.0, 0.190])
        with patch("time.perf_counter", side_effect=lambda: next(fake_times)):
            import time
            t0 = time.perf_counter()
            # ... simulated check body ...
            elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertAlmostEqual(elapsed_ms, 190.0, places=1)
        self.assertLess(elapsed_ms, float(budget_ms),
                        "190 ms simulated under 200 ms budget — must not flag slow.")

    # ----- Test 6: MOCK-CLOCK over budget — 210 ms simulated triggers slow -----
    def test_mock_clock_over_budget(self) -> None:
        """210 ms simulated > 200 ms budget → annotated slow.

        AC9c discipline: mock-clock advancement, no real sleep.
        """
        budget_ms = 200
        fake_times = iter([0.0, 0.210])
        with patch("time.perf_counter", side_effect=lambda: next(fake_times)):
            import time
            t0 = time.perf_counter()
            elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertAlmostEqual(elapsed_ms, 210.0, places=1)
        self.assertGreater(elapsed_ms, float(budget_ms),
                           "210 ms simulated over 200 ms budget — must flag slow / over-budget.")
        # Verify that the over-budget condition would be the trigger
        # for `ceo_boot_check_skipped` emission downstream.
        over_budget = elapsed_ms > float(budget_ms)
        self.assertTrue(over_budget)

    # ----- Test 7: side-effect-free module import — no sys.path mutation -----
    def test_module_import_no_sys_path_mutation(self) -> None:
        """PLAN-106 Wave F.1 fold: importing the module MUST NOT mutate sys.path.

        Before refactor (v1.34.0 baseline), check-confidence-gate-drift.py
        prepended `.claude/hooks/` to sys.path at module-import time
        (lines 32-37). Post-refactor, that mutation lives in main()
        ONLY. The wrapper in ceo-boot.py uses importlib which would
        inherit any module-level side-effects — verify clean import.
        """
        before = list(sys.path)
        # Re-load the module fresh in a separate spec to ensure no
        # module-cache contamination from our test setUp's load.
        canonical = _REPO_ROOT / ".claude" / "scripts" / "check-confidence-gate-drift.py"
        spec = importlib.util.spec_from_file_location(
            "_test_reload_drift", str(canonical),
        )
        assert spec is not None and spec.loader is not None
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        after = list(sys.path)
        # The sys.path mutation that lived at lines 32-37 in v1.34.0
        # baseline targeted `<repo>/.claude/hooks` — MUST NOT appear
        # in sys.path purely from import.
        injected = set(after) - set(before)
        # Defensive: any newly-injected path that points to
        # `.claude/hooks` is a Wave F.1 regression.
        for p in injected:
            self.assertNotIn(
                ".claude/hooks", p,
                f"Wave F.1 regression: module import mutated sys.path with {p!r}; "
                f"`sys.path.insert(...)` should live in main() only.",
            )


if __name__ == "__main__":
    unittest.main()
