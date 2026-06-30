"""PLAN-125 WS-1 — in-process lifecycle perf microbench (ADVISORY).

MF-PERF-4 / MF-QA-A: measures the IN-PROCESS logic only (record_pre +
record_post: per-session file read-modify-write under the cheap lock + enum
mapping), with the audit-chain emit MOCKED to a no-op so we isolate the
hot-path logic from HMAC / spool / fsync. N>=200 iterations; asserts p99 < 2ms.

This is ADVISORY (``xfail(strict=False, run=True)``) per the existing
latency-gate pattern (``test_hook_latency.py``) and
``[[feedback-xpass-strict-flake-trap]]`` — under heavy concurrent pytest load
the budget can be missed; solo it XPASSes. We do NOT introduce a strict gate.

The orphan sweeper uses an INJECTABLE clock (MF-QA-B) — no ``time.sleep``.

Stdlib-only + pytest marker, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import statistics
import time
import unittest

import pytest

from _lib import audit_emit  # noqa: E402
from _lib import tool_lifecycle  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


N_ITERS = 250  # ≥200 per ADR-071 percentile-stability minimum
P99_BUDGET_MS = 2.0


class _PreEvent:
    def __init__(self, *, session_id, tool_use_id, tool_name):
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name


class _PostEvent:
    def __init__(self, *, session_id, tool_use_id, tool_name, duration_ms):
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.duration_ms = duration_ms


class TestLifecyclePerf(TestEnvContext):
    @pytest.mark.advisory
    @pytest.mark.xfail(
        strict=False,  # ADVISORY — XPASS never fails CI ([[feedback-xpass-strict-flake-trap]]).
        run=True,
        reason=(
            "ADVISORY in-process perf budget (PLAN-125 WS-1 / MF-PERF-4). "
            "The record_pre+record_post hot-path logic (per-session JSON "
            "read-modify-write under the cheap filelock + enum mapping, emit "
            "MOCKED) targets p99 < 2ms. Under heavy concurrent pytest load "
            "(4000+ tests + integration/formal subprocess churn) the wall-clock "
            "budget can be missed; solo it XPASSes. strict=False so an XPASS is "
            "reported but NEVER fails CI. NOT a strict gate by design."
        ),
    )
    def test_in_process_pair_logic_under_2ms_p99(self):
        # Mock the audit-chain emit to a no-op: we measure ONLY the in-process
        # pairing/file logic, not the HMAC/spool/fsync write path.
        orig = audit_emit.emit_tool_call_lifecycle_recorded
        audit_emit.emit_tool_call_lifecycle_recorded = lambda **k: None  # type: ignore[assignment]
        samples_ms = []
        try:
            # Warm up the lock-parent mkdir cache + import paths (discard).
            warm_pre = _PreEvent(session_id="perf-warm", tool_use_id="w", tool_name="Bash")
            tool_lifecycle.record_pre(warm_pre)
            tool_lifecycle.record_post(
                _PostEvent(session_id="perf-warm", tool_use_id="w",
                           tool_name="Bash", duration_ms=10),
                failure=False,
            )
            for i in range(N_ITERS):
                tuid = "u%d" % i
                pre = _PreEvent(session_id="perf", tool_use_id=tuid, tool_name="Bash")
                post = _PostEvent(session_id="perf", tool_use_id=tuid,
                                  tool_name="Bash", duration_ms=2500)
                t0 = time.perf_counter()
                tool_lifecycle.record_pre(pre)
                tool_lifecycle.record_post(post, failure=False)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                samples_ms.append(dt_ms)
        finally:
            audit_emit.emit_tool_call_lifecycle_recorded = orig  # type: ignore[assignment]

        samples_ms.sort()
        # p99 via nearest-rank.
        idx = max(0, int(round(0.99 * len(samples_ms))) - 1)
        p99 = samples_ms[idx]
        p50 = statistics.median(samples_ms)
        # Print so the advisory result is visible in CI output.
        print(
            "\n[tool_lifecycle perf] N=%d  p50=%.3fms  p99=%.3fms (budget %.1fms)"
            % (len(samples_ms), p50, p99, P99_BUDGET_MS)
        )
        self.assertLess(
            p99, P99_BUDGET_MS,
            "in-process pair logic p99=%.3fms exceeds %.1fms budget" % (p99, P99_BUDGET_MS),
        )


if __name__ == "__main__":
    unittest.main()
