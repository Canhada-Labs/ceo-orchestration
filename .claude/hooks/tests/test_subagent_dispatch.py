"""Unit tests for `_lib.subagent_dispatch.aggregate_findings`.

PLAN-106 Wave G.1 / AC10b (qa R1 P1 fold — 5+ behavioural cases):
- full-return (k=N): no emit
- partial-return (k<N, timeout): emit fires
- total-drop (k=0): emit fires with `findings_total=0`
- agent_error path: emit fires with drop_reason=agent_error
- retry-exhaust path: emit fires with drop_reason=retry_exhaust
- allowlist guard (extra field smuggled in archetype is truncated)
- classify_drop_from_outcome semantics

Uses `TestEnvContext` from `_lib.testing` for env isolation; the
audit-emit module writes to the isolated `audit-log.jsonl` under
`self.audit_dir` so assertions can read the written events back.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

# Bootstrap import path so we can `from _lib import ...` regardless of
# where pytest is invoked.
_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# Module under test
from _lib import subagent_dispatch  # noqa: E402
from _lib.subagent_dispatch import (  # noqa: E402
    DropReason,
    aggregate_findings,
    classify_drop_from_outcome,
)


def _read_emitted_events(audit_log_path: Path) -> list:
    """Parse the JSONL audit log into a list of event dicts."""
    if not audit_log_path.is_file():
        return []
    out = []
    for line in audit_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _partial_drop_events(events: list) -> list:
    return [e for e in events if e.get("action") == "subagent_findings_partial_drop"]


class TestAggregateFindings(TestEnvContext):
    """Behavioural tests on aggregate_findings."""

    def setUp(self) -> None:
        super().setUp()
        # S141 lesson [[feedback-test-set-ceo-audit-sync-mode]]: audit
        # writes spool asynchronously by default; force sync mode so the
        # JSONL log file exists for inline read-back assertions.
        import os
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

    def _audit_path(self) -> Path:
        return self.audit_dir / "audit-log.jsonl"

    # ---------- AC10b case 1: full-return (k == N) ----------
    def test_full_return_no_emit(self) -> None:
        findings = [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}]
        result = aggregate_findings(
            expected_n=4,
            completed_findings=findings,
            archetype="security-engineer",
        )
        self.assertFalse(result["partial_drop"])
        self.assertEqual(result["completed_n"], 4)
        self.assertEqual(result["expected_n"], 4)
        self.assertEqual(result["dropped_n"], 0)
        self.assertFalse(result["emit_attempted"])
        events = _read_emitted_events(self._audit_path())
        self.assertEqual(len(_partial_drop_events(events)), 0)

    # ---------- AC10b case 2: partial-return (k < N, timeout) ----------
    def test_partial_return_emit_fires(self) -> None:
        findings = [{"a": 1}, {"a": 2}]  # k=2 of N=4
        result = aggregate_findings(
            expected_n=4,
            completed_findings=findings,
            drop_reason=DropReason.TIMEOUT,
            archetype="qa-architect",
        )
        self.assertTrue(result["partial_drop"])
        self.assertEqual(result["completed_n"], 2)
        self.assertEqual(result["dropped_n"], 2)
        self.assertEqual(result["drop_reason"], "timeout")
        self.assertTrue(result["emit_attempted"])
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        e = partial[0]
        self.assertEqual(e.get("findings_total"), 2)
        self.assertEqual(e.get("findings_dropped"), 2)
        self.assertEqual(e.get("drop_reason"), "timeout")
        self.assertEqual(e.get("archetype"), "qa-architect")

    # ---------- AC10b case 3: total-drop (k == 0) ----------
    def test_total_drop_emit_fires(self) -> None:
        result = aggregate_findings(
            expected_n=3,
            completed_findings=[],
            drop_reason=DropReason.TIMEOUT,
            archetype="performance-engineer",
        )
        self.assertTrue(result["partial_drop"])
        self.assertEqual(result["completed_n"], 0)
        self.assertEqual(result["dropped_n"], 3)
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].get("findings_total"), 0)
        self.assertEqual(partial[0].get("findings_dropped"), 3)

    # ---------- AC10b case 4: agent_error path ----------
    def test_agent_error_path(self) -> None:
        result = aggregate_findings(
            expected_n=2,
            completed_findings=[{"a": 1}],
            drop_reason=DropReason.AGENT_ERROR,
            archetype="code-reviewer",
        )
        self.assertTrue(result["partial_drop"])
        self.assertEqual(result["drop_reason"], "agent_error")
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].get("drop_reason"), "agent_error")

    # ---------- AC10b case 5: retry-exhaust path ----------
    def test_retry_exhaust_path(self) -> None:
        result = aggregate_findings(
            expected_n=5,
            completed_findings=[{"a": 1}, {"a": 2}, {"a": 3}],
            dropped_count=2,
            drop_reason=DropReason.RETRY_EXHAUST,
            archetype="security-engineer",
        )
        self.assertTrue(result["partial_drop"])
        self.assertEqual(result["dropped_n"], 2)
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].get("drop_reason"), "retry_exhaust")

    # ---------- Allowlist guard: archetype overlong is truncated ----------
    def test_allowlist_truncation(self) -> None:
        long_archetype = "a" * 500
        result = aggregate_findings(
            expected_n=1,
            completed_findings=[],
            drop_reason=DropReason.TIMEOUT,
            archetype=long_archetype,
        )
        # Module-level truncation: 64 chars max per emit_subagent_findings_partial_drop
        self.assertLessEqual(len(result["archetype"]), 64)
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        # Audit emit further truncates if needed; in any case <= 64 chars.
        emitted_archetype = partial[0].get("archetype", "")
        self.assertLessEqual(len(emitted_archetype), 64)
        # Ensure no forbidden field smuggled into the event (Sec MF-3
        # allowlist enforcement).
        for forbidden in ("prompt", "tool_response", "secret", "raw"):
            self.assertNotIn(forbidden, partial[0])

    # ---------- Unknown reason falls back to UNKNOWN, still emits ----------
    def test_unknown_drop_reason_falls_back(self) -> None:
        result = aggregate_findings(
            expected_n=2,
            completed_findings=[{"a": 1}],
            drop_reason="garbage_reason",
            archetype="qa-architect",
        )
        self.assertTrue(result["partial_drop"])
        self.assertEqual(result["drop_reason"], "unknown")
        events = _read_emitted_events(self._audit_path())
        partial = _partial_drop_events(events)
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].get("drop_reason"), "unknown")

    # ---------- classify_drop_from_outcome precedence ----------
    def test_classify_drop_precedence(self) -> None:
        # Precedence: timeout > raised > retries_exhausted > unknown
        self.assertEqual(
            classify_drop_from_outcome(timed_out=True, raised=True),
            DropReason.TIMEOUT,
        )
        self.assertEqual(
            classify_drop_from_outcome(raised=True, retries_exhausted=True),
            DropReason.AGENT_ERROR,
        )
        self.assertEqual(
            classify_drop_from_outcome(retries_exhausted=True),
            DropReason.RETRY_EXHAUST,
        )
        self.assertEqual(
            classify_drop_from_outcome(),
            DropReason.UNKNOWN,
        )

    # ---------- Defensive: negative expected_n is coerced to 0 ----------
    def test_negative_expected_n_coerced(self) -> None:
        result = aggregate_findings(
            expected_n=-5,
            completed_findings=[],
            drop_reason=DropReason.TIMEOUT,
            archetype="qa-architect",
        )
        self.assertEqual(result["expected_n"], 0)
        # k=0, expected=0 → not partial; no emit
        self.assertFalse(result["partial_drop"])
        events = _read_emitted_events(self._audit_path())
        self.assertEqual(len(_partial_drop_events(events)), 0)


class TestDropReason(unittest.TestCase):
    """Pure-function tests on the DropReason enum class."""

    def test_is_valid_accepts_constants(self) -> None:
        for r in (DropReason.TIMEOUT, DropReason.AGENT_ERROR,
                  DropReason.RETRY_EXHAUST, DropReason.UNKNOWN):
            self.assertTrue(DropReason.is_valid(r))

    def test_is_valid_rejects_unknown(self) -> None:
        for r in ("", "TIMEOUT", "fail", "TIMEOUT ", "agent-error"):
            self.assertFalse(DropReason.is_valid(r))


if __name__ == "__main__":
    unittest.main()
