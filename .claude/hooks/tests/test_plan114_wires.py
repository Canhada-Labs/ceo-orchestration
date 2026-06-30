"""PLAN-114 wire invocation tests — items 1-4 from the regression-test spec.

Each class proves one wire fires end-to-end (emit into the HMAC-covered
audit trail), NOT just that the typed wrapper exists.

Requirements:
- TestEnvContext for env isolation (never touch real $HOME)
- CEO_AUDIT_SYNC_MODE=1 (inherited from TestEnvContext SYNC_MODE_DEFAULT=True)
  so audit log is synchronously flushed before assertion reads.
- stdlib + unittest only (no hypothesis, no pytest).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# --- sys.path bootstrap -------------------------------------------------------
# Ensure `.claude/hooks/` is on sys.path regardless of CWD so `_lib.*` and
# `audit_emit` are importable.  Mirrors the pattern used by every other test
# in this directory that lacks conftest.py coverage.
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
import _lib.audit_emit as audit_emit  # noqa: E402


# =============================================================================
# Helper — read all events from the per-test isolated audit log.
# =============================================================================

def _read_audit_events(audit_log_path: Path) -> list:
    """Return a list of parsed JSON objects from the audit log file.

    Skips lines that are not valid JSON (should be none under sync mode).
    """
    events = []
    if not audit_log_path.exists():
        return events
    for line in audit_log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def _events_with_action(events: list, action: str) -> list:
    return [e for e in events if e.get("action") == action]


# =============================================================================
# Item 1 — task_route_key_dropped wire
#
# Wire: emit_generic(action="task_route_advised", ...) with a forbidden field
# injected → _scrub_ceo_boot_event drops it → emit_task_route_key_dropped
# is called → a task_route_key_dropped event appears in the audit log.
#
# Evidence path:
#   audit_emit.py:4299-4320 (task_route_advised branch)
#   commit message: PLAN-114 F-1-1.8-47dba028
# =============================================================================

class TestTaskRouteKeyDroppedWire(TestEnvContext):
    """PLAN-114 F-1-1.8-47dba028 — emit_task_route_key_dropped fires on drop."""

    def test_task_route_key_dropped_event_written_on_forbidden_field(self):
        """emit_generic('task_route_advised') with forbidden field 'raw_prompt'
        must produce a task_route_key_dropped event in the audit log.
        """
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        audit_emit.emit_generic(
            "task_route_advised",
            session_id="sess-trkd-1",
            project="test_project",
            contract_id="ct-1",
            classification="L2",
            duration_ms=42,
            # forbidden field — not in _TASK_ROUTE_ADVISED_ALLOWLIST
            raw_prompt="secret task description that must be stripped",
        )

        events = _read_audit_events(audit_log_path)
        dropped_events = _events_with_action(events, "task_route_key_dropped")
        self.assertGreater(
            len(dropped_events), 0,
            "Expected at least one task_route_key_dropped event in the audit log "
            "after emit_generic('task_route_advised') with forbidden field. "
            "Wire at audit_emit.py task_route_advised branch may not have fired.",
        )
        # The emitted event should carry the key name (truncated to 64 chars)
        # and reason_code="allowlist_strip".
        ev = dropped_events[0]
        self.assertEqual(ev.get("action"), "task_route_key_dropped")
        self.assertEqual(ev.get("reason_code"), "allowlist_strip")
        self.assertIn("raw_prompt", ev.get("key", ""))

    def test_task_route_no_drop_when_only_allowed_fields(self):
        """emit_generic('task_route_advised') with only allowed fields must NOT
        produce a task_route_key_dropped event.
        """
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        audit_emit.emit_generic(
            "task_route_advised",
            session_id="sess-trkd-2",
            project="test_project",
            contract_id="ct-2",
            classification="L1",
            duration_ms=10,
            # no forbidden fields
        )

        events = _read_audit_events(audit_log_path)
        dropped_events = _events_with_action(events, "task_route_key_dropped")
        self.assertEqual(
            len(dropped_events), 0,
            "No task_route_key_dropped event should be emitted when all fields "
            "are in the allowlist.",
        )


# =============================================================================
# Item 2 — reality_ledger_key_dropped wire
#
# Wire: emit_generic(action="reality_ledger_finding", ...) with a forbidden
# field injected → _scrub_ceo_boot_event drops it →
# emit_reality_ledger_key_dropped is called → event written to audit log.
#
# Evidence path:
#   audit_emit.py:4391-4410 (reality_ledger_finding branch)
#   commit message: PLAN-114 F-1-1.8-8d4e2519
# =============================================================================

class TestRealityLedgerKeyDroppedWire(TestEnvContext):
    """PLAN-114 F-1-1.8-8d4e2519 — emit_reality_ledger_key_dropped fires on drop."""

    def test_reality_ledger_key_dropped_event_written_on_forbidden_field(self):
        """emit_generic('reality_ledger_finding') with forbidden field 'raw_claim'
        must produce a reality_ledger_key_dropped event in the audit log.
        """
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        audit_emit.emit_generic(
            "reality_ledger_finding",
            session_id="sess-rlkd-1",
            project="test_project",
            detector="test_detector",
            severity="medium",
            confidence_bps=750,
            claim_source_sha256="abc123",
            finding_count_in_run=1,
            # forbidden field — not in _REALITY_LEDGER_FINDING_ALLOWLIST
            raw_claim="verbatim claim content that must be stripped",
        )

        events = _read_audit_events(audit_log_path)
        dropped_events = _events_with_action(events, "reality_ledger_key_dropped")
        self.assertGreater(
            len(dropped_events), 0,
            "Expected at least one reality_ledger_key_dropped event in the audit "
            "log after emit_generic('reality_ledger_finding') with forbidden field. "
            "Wire at audit_emit.py reality_ledger_finding branch may not have fired.",
        )
        ev = dropped_events[0]
        self.assertEqual(ev.get("action"), "reality_ledger_key_dropped")
        # detector is forwarded to the typed emit call
        self.assertEqual(ev.get("detector"), "test_detector")
        self.assertIn("raw_claim", ev.get("key", ""))

    def test_reality_ledger_no_drop_when_only_allowed_fields(self):
        """emit_generic('reality_ledger_finding') with only allowed fields must
        NOT produce a reality_ledger_key_dropped event.
        """
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        audit_emit.emit_generic(
            "reality_ledger_finding",
            session_id="sess-rlkd-2",
            project="test_project",
            detector="clean_detector",
            severity="low",
            confidence_bps=900,
            claim_source_sha256="def456",
            finding_count_in_run=0,
            # no forbidden fields
        )

        events = _read_audit_events(audit_log_path)
        dropped_events = _events_with_action(events, "reality_ledger_key_dropped")
        self.assertEqual(
            len(dropped_events), 0,
            "No reality_ledger_key_dropped event should be emitted when all "
            "fields are in the allowlist.",
        )


# =============================================================================
# Item 3 — breaker_closed wire
#
# Wire: CircuitBreaker.record_success() (HALF_OPEN→CLOSED path) calls
# audit_emit.emit_breaker_closed(provider, from_state="half_open").
#
# Evidence path:
#   _breaker.py:217-234 (record_success HALF_OPEN path)
#   _breaker.py:241-252 (record_success OPEN race path)
#   commit message: PLAN-114 F-1-1.8-c6fe879b
#
# NOTE: reset() does NOT yet call emit_breaker_closed at HEAD
# (grep shows no emit_breaker_closed call in reset()). That path is
# pending. Only record_success paths are tested here.
# =============================================================================

class TestBreakerClosedWire(TestEnvContext):
    """PLAN-114 F-1-1.8-c6fe879b — emit_breaker_closed fires on record_success."""

    def _import_breaker(self):
        """Import _breaker lazily after sys.path is set by TestEnvContext."""
        from _lib.adapters.live._breaker import BreakerState, CircuitBreaker
        return BreakerState, CircuitBreaker

    def _make_clock(self, start: float = 0.0):
        """Return a simple callable clock that supports `.advance(s)`."""
        class _Clock:
            def __init__(self, t):
                self.now = t
            def __call__(self):
                return self.now
            def advance(self, s):
                self.now += s
        return _Clock(start)

    def test_record_success_half_open_emits_breaker_closed(self):
        """HALF_OPEN + record_success() → breaker_closed event with
        from_state='half_open' in the audit log.
        """
        BreakerState, CircuitBreaker = self._import_breaker()
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        clock = self._make_clock()
        b = CircuitBreaker(
            provider="test_provider",
            threshold=2,
            window_s=30,
            half_open_s=60,
            clock=clock,
        )

        # Trip the breaker to OPEN
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)

        # Advance past half_open_s → HALF_OPEN
        clock.advance(61)
        self.assertTrue(b.should_allow())  # consume the probe, triggers HALF_OPEN
        self.assertEqual(b.state, BreakerState.HALF_OPEN)

        # Success probe → CLOSED + emit
        b.record_success()
        self.assertEqual(b.state, BreakerState.CLOSED)

        events = _read_audit_events(audit_log_path)
        closed_events = _events_with_action(events, "breaker_closed")
        self.assertGreater(
            len(closed_events), 0,
            "Expected a breaker_closed audit event after HALF_OPEN→CLOSED "
            "via record_success(). Wire at _breaker.py:228-234 may not have fired.",
        )
        ev = closed_events[0]
        self.assertEqual(ev.get("from_state"), "half_open")
        self.assertEqual(ev.get("provider"), "test_provider")

    def test_record_success_open_race_emits_breaker_closed(self):
        """OPEN + record_success() (race path) → breaker_closed event with
        from_state='open' in the audit log.
        """
        BreakerState, CircuitBreaker = self._import_breaker()
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        clock = self._make_clock()
        b = CircuitBreaker(
            provider="race_provider",
            threshold=2,
            window_s=30,
            half_open_s=60,
            clock=clock,
        )

        # Trip to OPEN
        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)

        # Force record_success directly while OPEN (race path — no probe consumed)
        # This exercises the final else-branch in record_success().
        with b._lock:
            # Manually reset probe_available=False so the OPEN race path is taken
            # (should_allow() was never called, so _probe_available stays False)
            pass
        # Call record_success while breaker is OPEN (no preceding should_allow)
        b.record_success()
        self.assertEqual(b.state, BreakerState.CLOSED)

        events = _read_audit_events(audit_log_path)
        closed_events = _events_with_action(events, "breaker_closed")
        self.assertGreater(
            len(closed_events), 0,
            "Expected a breaker_closed audit event after OPEN race path via "
            "record_success(). Wire at _breaker.py:247-252 may not have fired.",
        )
        # The most recent closed event should be from_state="open"
        # (earlier events from test_record_success_half_open_emits_breaker_closed
        # won't appear here because TestEnvContext gives us a fresh audit log)
        ev = closed_events[-1]
        self.assertEqual(ev.get("from_state"), "open")
        self.assertEqual(ev.get("provider"), "race_provider")

    def test_reset_does_not_yet_emit_breaker_closed(self):
        """reset() does NOT yet call emit_breaker_closed at HEAD.

        This test documents the pending wire (reset path). When the reset
        path is wired, update this test to assert the event IS written.
        """
        BreakerState, CircuitBreaker = self._import_breaker()
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        clock = self._make_clock()
        b = CircuitBreaker(
            provider="reset_provider",
            threshold=2,
            window_s=30,
            half_open_s=60,
            clock=clock,
        )

        b.record_failure("server_error")
        b.record_failure("server_error")
        self.assertEqual(b.state, BreakerState.OPEN)

        b.reset()
        self.assertEqual(b.state, BreakerState.CLOSED)

        # Check _breaker.py reset() for emit_breaker_closed call
        import inspect
        from _lib.adapters.live import _breaker as breaker_mod
        reset_src = inspect.getsource(breaker_mod.CircuitBreaker.reset)
        reset_has_wire = "emit_breaker_closed" in reset_src

        events = _read_audit_events(audit_log_path)
        closed_events = _events_with_action(events, "breaker_closed")

        if reset_has_wire:
            # Wire applied — assert event present with from_state="reset"
            self.assertGreater(len(closed_events), 0,
                "reset() wire detected but no breaker_closed event emitted.")
            self.assertEqual(closed_events[-1].get("from_state"), "reset")
        else:
            # Wire NOT yet applied — document as pending
            self.assertEqual(
                len(closed_events), 0,
                "reset() is not yet wired (emit_breaker_closed absent in reset()). "
                "No breaker_closed event expected from reset() alone. "
                "PENDING: wire reset() path in _breaker.py.",
            )


# =============================================================================
# Item 4 — swarm_layer_3_4_blocked invocation test
#
# Wire: loop_runner._emit_swarm_layer_3_4_blocked() calls
# audit_emit.emit_generic("swarm_layer_3_4_blocked", ...).
#
# Evidence path:
#   loop_runner.py:63-94 (_emit_swarm_layer_3_4_blocked)
#   loop_runner.py:336-340 (_gate_step_check calls it on gate-block)
#   spec_EMIT.md §e0a8eedf: action IS wired; test gap is the only finding
#
# This test imports _emit_swarm_layer_3_4_blocked directly and asserts
# a swarm_layer_3_4_blocked event is written to the audit log.
# =============================================================================

class TestSwarmLayer34BlockedInvocation(TestEnvContext):
    """PLAN-114 spec_EMIT §e0a8eedf — swarm_layer_3_4_blocked invocation test."""

    def setUp(self):
        super().setUp()
        # Add .claude/scripts to sys.path so `swarm.loop_runner` is importable.
        _repo_root = Path(__file__).resolve().parents[3]
        _scripts = str(_repo_root / ".claude" / "scripts")
        if _scripts not in sys.path:
            sys.path.insert(0, _scripts)

    def test_emit_swarm_layer_3_4_blocked_writes_audit_event(self):
        """_emit_swarm_layer_3_4_blocked with valid args must write a
        swarm_layer_3_4_blocked event to the HMAC-covered audit log.
        """
        from swarm.loop_runner import _emit_swarm_layer_3_4_blocked
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        _emit_swarm_layer_3_4_blocked(
            class_tier="vibecoder",
            reason_code="layer_3_unavailable",
            loop_id="PLAN114-smoke-test",
        )

        events = _read_audit_events(audit_log_path)
        blocked_events = _events_with_action(events, "swarm_layer_3_4_blocked")
        self.assertGreater(
            len(blocked_events), 0,
            "Expected a swarm_layer_3_4_blocked event in the audit log after "
            "_emit_swarm_layer_3_4_blocked() was called. "
            "The function at loop_runner.py:63 must invoke emit_generic.",
        )
        ev = blocked_events[0]
        self.assertEqual(ev.get("class_tier"), "vibecoder")
        self.assertEqual(ev.get("reason_code"), "layer_3_unavailable")
        self.assertEqual(ev.get("loop_id"), "PLAN114-smoke-test")

    def test_emit_swarm_layer_3_4_blocked_invalid_loop_id_fails_open(self):
        """Invalid loop_id (empty / too long / bad chars) → fail-open drop.

        The function silently returns without emitting (LLM06 producer-
        boundary hygiene per ADR-133).
        """
        from swarm.loop_runner import _emit_swarm_layer_3_4_blocked
        audit_log_path = Path(os.environ["CEO_AUDIT_LOG_DIR"]) / "audit-log.jsonl"

        # Empty loop_id → drop
        _emit_swarm_layer_3_4_blocked(
            class_tier="vibecoder",
            reason_code="test",
            loop_id="",
        )
        # Too-long loop_id → drop
        _emit_swarm_layer_3_4_blocked(
            class_tier="vibecoder",
            reason_code="test",
            loop_id="x" * 65,
        )
        # Bad chars → drop
        _emit_swarm_layer_3_4_blocked(
            class_tier="vibecoder",
            reason_code="test",
            loop_id="invalid loop id with spaces!",
        )

        events = _read_audit_events(audit_log_path)
        blocked_events = _events_with_action(events, "swarm_layer_3_4_blocked")
        self.assertEqual(
            len(blocked_events), 0,
            "No swarm_layer_3_4_blocked event should be emitted for invalid loop_id. "
            "Fail-open drop at loop_runner.py:79 must be in effect.",
        )


if __name__ == "__main__":
    unittest.main()
