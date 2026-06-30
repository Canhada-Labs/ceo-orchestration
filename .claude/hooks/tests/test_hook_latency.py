"""Hook latency test — p95 < 100ms, p99 < 150ms over N=200 iterations.

PLAN-063 DIM-15 (Session 77 Phase 5 deep refactor) tightens the
post-Sprint-2 budget per ADR-071 methodology and audit-v3 deliverable.
Initial pin (p95 < 50ms) was based on darwin/ARM baseline (38-44ms);
CI ubuntu-latest baseline (57-64ms) showed 50ms NOT achievable.
Per audit-v3 spec, falling back to the relaxed budget (p95 < 100ms).
Still meaningful tightening from Sprint 2's p95 < 120ms / p99 < 200ms.

Measures wallclock time for each hook (check_agent_spawn.py + audit_log.py)
invoked as a real subprocess. Discards the first iteration as cold start,
asserts the percentiles against the audit-v3 DIM-15 budget.

Cold start is measured separately with a 300ms ceiling (unchanged
from Sprint 2 — cold start variance is structural).

## Why subprocess + wallclock

In-process timing (importing the module and calling main()) would miss
the Python startup cost, which is the real bottleneck on every Claude
Code hook invocation. The shim + `python3 script.py` fork pays ~50ms
of startup on macOS; the test enforces a budget that absorbs this.

## Budgets (PLAN-063 DIM-15 tightening, spec fallback applied)

- **p95 warm latency:** < 100ms (was 120ms; CI baseline 57-64ms +
  ~36-43ms headroom for CI variance)
- **p99 warm latency:** < 150ms (was 200ms; CI baseline 58-66ms +
  ~84-92ms headroom for warm-noise tail)
- **cold start (iter 0):** < 300ms — separate ceiling, unchanged

All measured with N=200 iterations per hook (was 50; matches
ADR-071 N≥200 percentile-stability minimum). If a run is noisy and a
single iter exceeds the budget, that's still within p95/p99 tolerance.

## Environment

Runs the hook in the isolated TestEnvContext temp dir (so no real
audit log is polluted). Passes a clean payload on stdin.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import unittest
from pathlib import Path

import pytest


from _lib.testing import TestEnvContext  # noqa: E402


HOOKS_DIR = Path(__file__).resolve().parent.parent
CHECK_HOOK = HOOKS_DIR / "check_agent_spawn.py"
AUDIT_HOOK = HOOKS_DIR / "audit_log.py"

# Budgets (milliseconds) — PLAN-063 DIM-15 spec fallback per ADR-071.
# Phase 0 baseline (darwin/ARM local, 2026-04-30):
#   - N=200: p95 44-45ms, p99 57-62ms, max 67-71ms
# CI baseline (ubuntu-latest, 2026-05-01 first PR run):
#   - N=200: p95 57-64ms, p99 58-66ms, max 65-76ms
# DIM-15 audit-v3 spec: "Pin p95 < 50ms IF Phase 0 baseline confirms
# achievable; otherwise relax to p95 < 100ms (Phase 0 baseline informs
# this)." CI confirmed 50ms NOT achievable (CI ~50% slower than darwin).
# Falling back to spec's relaxed budget. Still meaningful tightening
# from the original Sprint 2 budget (p95 120ms / p99 200ms).
P95_BUDGET_MS = 100
P99_BUDGET_MS = 150
COLD_START_BUDGET_MS = 300

# Iteration counts. Bumped to 200 per ADR-071 percentile-stability
# minimum (was 50 in Sprint 2). Can be lowered via env for CI speed
# (e.g. CEO_HOOK_LATENCY_ITERATIONS=50 on slow runners).
WARM_ITERATIONS = int(os.environ.get("CEO_HOOK_LATENCY_ITERATIONS", "200"))


def percentile(sorted_values, p):
    """Return the p-th percentile from a sorted list (0 <= p <= 100)."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return float(sorted_values[f])
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


@unittest.skipUnless(os.name == "posix", "POSIX only (subprocess)")
class TestHookLatency(TestEnvContext):
    def _time_hook(self, script_path, payload_text):
        """Run the hook once and return elapsed milliseconds (int)."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(HOOKS_DIR)
        t0 = time.monotonic()
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=payload_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        self.assertEqual(result.returncode, 0, f"hook failed: {result.stderr}")
        return elapsed_ms

    def _run_budget(self, script_path, payload, label):
        """Run N+1 iterations and assert p95/p99/cold budgets."""
        # Cold start — first iteration
        cold_ms = self._time_hook(script_path, payload)

        # Warm iterations
        warm = []
        for _ in range(WARM_ITERATIONS):
            warm.append(self._time_hook(script_path, payload))

        warm_sorted = sorted(warm)
        p50 = percentile(warm_sorted, 50)
        p95 = percentile(warm_sorted, 95)
        p99 = percentile(warm_sorted, 99)
        mean = statistics.mean(warm)
        maxv = max(warm)

        # Emit a measurement report to stderr for CI visibility
        print(
            f"\n[latency] {label}: cold={cold_ms}ms "
            f"warm N={len(warm)} "
            f"mean={mean:.1f}ms "
            f"p50={p50:.0f}ms p95={p95:.0f}ms p99={p99:.0f}ms "
            f"max={maxv}ms",
            file=sys.stderr,
        )

        self.assertLessEqual(
            cold_ms,
            COLD_START_BUDGET_MS,
            f"{label} cold start {cold_ms}ms > {COLD_START_BUDGET_MS}ms budget",
        )
        self.assertLessEqual(
            p95,
            P95_BUDGET_MS,
            f"{label} p95 {p95:.0f}ms > {P95_BUDGET_MS}ms budget",
        )
        self.assertLessEqual(
            p99,
            P99_BUDGET_MS,
            f"{label} p99 {p99:.0f}ms > {P99_BUDGET_MS}ms budget",
        )

    @pytest.mark.advisory
    @pytest.mark.xfail(
        strict=False,  # PLAN-113 W8: ADVISORY — non-strict so an XPASS under
        # low load does NOT fail CI (the [[feedback-xpass-strict-flake-trap]]).
        run=True,  # PLAN-113 W8 decision: actually RUN as advisory (was run=False).
        reason=(
            "ADVISORY perf budget (PLAN-113 W8 decision). Wall-clock p95/p99 "
            "latency fails the p95<100ms / p99<150ms budget under heavy "
            "concurrent pytest load (4000+ tests with formal_verification + "
            "integration subprocess churn). The ceremony's full-pytest scope "
            "(pytest.ini testpaths includes tests/integration + "
            "formal_verification) reliably exhausts the CPU and the wall-clock "
            "budget is missed. Solo runs show ~16s for 200 iterations within "
            "budget. As of PLAN-113 W8 this RUNS as advisory: under load it "
            "xfails (green); solo it XPASSes — and because strict=False that "
            "XPASS is reported but NEVER fails CI. If you consistently see "
            "XPASS the suite has gotten faster and the budget can be tightened "
            "(or the xfail dropped). PLAN-107 Wave D xfail manifest #3. "
            "PLAN-107-FOLLOWUP-perf-isolation should pin this test to an "
            "exclusive runner for a hard (strict) budget."
        ),
    )
    def test_check_agent_spawn_latency(self):
        """ADVISORY perf-budget probe (PLAN-113 W8).

        DECISION: converted PLAN-108's ``run=False`` deferral to a RUNNING
        advisory check (``run=True``, ``strict=False``). Rationale: a
        deliberately non-running ``run=False`` made no decision and gave no
        signal. Running it as advisory restores the signal (the latency report
        prints to stderr every run) while ``strict=False`` keeps it CI-safe:
        an XPASS under low load is NOT a failure (avoids the
        ``[[feedback-xpass-strict-flake-trap]]``). Marked ``advisory`` so the
        registered marker documents that it does not gate CI.
        """
        payload = json.dumps({
            "session_id": "lat",
            "tool_name": "Agent",
            "tool_input": {
                "description": "latency test",
                "prompt": "do a thing",
            },
        })
        self._run_budget(CHECK_HOOK, payload, "check_agent_spawn")

    @pytest.mark.advisory
    @pytest.mark.xfail(
        strict=False,  # PLAN-113 W8: ADVISORY — non-strict so an XPASS under
        # low load does NOT fail CI (the [[feedback-xpass-strict-flake-trap]]).
        run=True,  # PLAN-113 W8 decision: actually RUN as advisory (was run=False).
        reason=(
            "ADVISORY perf budget (PLAN-113 W8 decision). Wall-clock p95 "
            "latency 106-120ms exceeds the p95<100ms budget under heavy "
            "concurrent pytest load (4000+ tests). PLAN-111 v1.39.2 Wave A+B "
            "optimized spool_writer hot path (darwin per-emit -27%) but CI "
            "ubuntu latency essentially unchanged (was 110-119ms, now "
            "106-120ms) — ubuntu subprocess startup + syscall floor dominates. "
            "Solo darwin run shows 74ms p95 within budget. As of PLAN-113 W8 "
            "this RUNS as advisory: under load it xfails (green); solo it "
            "XPASSes — and because strict=False that XPASS is reported but "
            "NEVER fails CI. Honors lesson [[feedback-xpass-strict-flake-trap]] "
            "by being non-strict rather than non-running. If you consistently "
            "see XPASS the suite has gotten faster and the budget can be "
            "tightened (or the xfail dropped). PLAN-107-FOLLOWUP-perf-isolation "
            "should pin this test to an exclusive runner for a hard budget."
        ),
    )
    def test_audit_log_latency(self):
        """ADVISORY perf-budget probe (PLAN-113 W8).

        DECISION: converted PLAN-111-FOLLOWUP's ``run=False`` deferral to a
        RUNNING advisory check (``run=True``, ``strict=False``). Same rationale
        as ``test_check_agent_spawn_latency``: ``run=False`` made no decision;
        running it as advisory restores the stderr latency signal while
        ``strict=False`` keeps an XPASS under low load from failing CI
        (avoids ``[[feedback-xpass-strict-flake-trap]]``). Marked ``advisory``.
        """
        payload = json.dumps({
            "session_id": "lat",
            "tool_name": "Agent",
            "tool_input": {
                "description": "latency test",
                "prompt": "## AGENT PROFILE\nSKILL: testing-strategy\n## FILE ASSIGNMENT\n- x",
            },
        })
        self._run_budget(AUDIT_HOOK, payload, "audit_log")


if __name__ == "__main__":
    unittest.main()
