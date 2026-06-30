"""PLAN-113 Phase B WIRE-AUDIT — shape-asserting invocation tests.

TEST-MISSING-CRITICAL (6): mcp_cross_tenant_denied, federation_cert_revoked,
federation_lan_bind_denied, federation_autonomous_call_blocked,
federation_write_attempt_blocked, confidence_gate_blocked.

Each test verifies:
1. The event is written to the audit log.
2. The `action` field matches the expected action name.
3. Key domain fields are present with the correct type / value.
4. No unexpected fields leak through (Sec MF-3 compliance spot-check).

Also covers the new PLAN-113 typed wrappers: escalation cluster (4),
swarm finalize cluster (2), task_route_key_dropped, reality_ledger_key_dropped,
tournament cluster (8) — invocation + shape assertions.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_emit  # noqa: E402


# ---------------------------------------------------------------------------
# Helper mixin — shared across all test classes.
# ---------------------------------------------------------------------------

class _LogReader:
    """Reads the audit log written during a TestEnvContext session."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    def _last_event(self):
        events = self._read_log()
        self.assertGreater(len(events), 0, "Audit log must have at least one event")
        return events[-1]


# ---------------------------------------------------------------------------
# TEST-MISSING-CRITICAL (6): MF-3 shape-asserting invocation tests.
# ---------------------------------------------------------------------------

class TestMcpCrossTenantDenied(TestEnvContext, _LogReader):
    """mcp_cross_tenant_denied — Sec MF-3 shape + invocation test."""

    def test_event_written_with_correct_action(self):
        audit_emit.emit_mcp_cross_tenant_denied(
            handler="get_cost_budget",
            caller_client_id_hash="abc123",
            target_client_id_hash="xyz789",
            transport="stdio",
            session_id="s-test",
            project="test-proj",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "mcp_cross_tenant_denied")

    def test_domain_fields_present(self):
        audit_emit.emit_mcp_cross_tenant_denied(
            handler="list_tools",
            caller_client_id_hash="caller_hash",
            target_client_id_hash="target_hash",
            transport="http",
        )
        e = self._last_event()
        self.assertEqual(e["handler"], "list_tools")
        self.assertEqual(e["caller_client_id_hash"], "caller_hash")
        self.assertEqual(e["target_client_id_hash"], "target_hash")
        self.assertEqual(e["transport"], "http")

    def test_no_raw_pii_fields(self):
        """Sec MF-3: client_id values must be pre-hashed by caller; raw ids
        must NOT appear as keys in the event."""
        audit_emit.emit_mcp_cross_tenant_denied(
            handler="h",
            caller_client_id_hash="h1",
            target_client_id_hash="h2",
            transport="stdio",
        )
        e = self._last_event()
        for key in e:
            self.assertNotIn("client_id", key.replace("client_id_hash", ""))

    def test_event_schema_v2(self):
        audit_emit.emit_mcp_cross_tenant_denied(
            handler="h",
            caller_client_id_hash="h1",
            target_client_id_hash="h2",
            transport="stdio",
        )
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestFederationCertRevoked(TestEnvContext, _LogReader):
    """federation_cert_revoked — shape + invocation test."""

    def test_event_written(self):
        audit_emit.emit_federation_cert_revoked(
            peer_id="peer-abc",
            reason="compromise",
            session_id="s-fed",
            project="fed-proj",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "federation_cert_revoked")

    def test_domain_fields(self):
        audit_emit.emit_federation_cert_revoked(
            peer_id="peer-xyz",
            reason="expiry",
        )
        e = self._last_event()
        self.assertEqual(e["peer_id"], "peer-xyz")
        self.assertEqual(e["reason"], "expiry")

    def test_peer_id_truncated_at_64(self):
        long_id = "p" * 100
        audit_emit.emit_federation_cert_revoked(peer_id=long_id)
        e = self._last_event()
        self.assertLessEqual(len(e["peer_id"]), 64)

    def test_event_schema_v2(self):
        audit_emit.emit_federation_cert_revoked(peer_id="p")
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestFederationLanBindDenied(TestEnvContext, _LogReader):
    """federation_lan_bind_denied — shape + invocation test."""

    def test_event_written(self):
        audit_emit.emit_federation_lan_bind_denied(
            bind_host="192.168.1.100",
            resolved_ip="192.168.1.100",
            reason="non_loopback_bind",
            session_id="s-lan",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "federation_lan_bind_denied")

    def test_domain_fields(self):
        audit_emit.emit_federation_lan_bind_denied(
            bind_host="10.0.0.1",
            resolved_ip="10.0.0.1",
            reason="private_range",
        )
        e = self._last_event()
        self.assertEqual(e["bind_host"], "10.0.0.1")
        self.assertEqual(e["resolved_ip"], "10.0.0.1")
        self.assertEqual(e["reason"], "private_range")

    def test_bind_host_truncated(self):
        audit_emit.emit_federation_lan_bind_denied(
            bind_host="b" * 100,
            resolved_ip="1.2.3.4",
        )
        e = self._last_event()
        self.assertLessEqual(len(e["bind_host"]), 64)

    def test_event_schema_v2(self):
        audit_emit.emit_federation_lan_bind_denied(bind_host="127.0.0.1")
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestFederationAutonomousCallBlocked(TestEnvContext, _LogReader):
    """federation_autonomous_call_blocked — shape + invocation test.

    Note: this action is in _RESERVED_ACTIONS (ADR-135 default-OFF). The
    typed wrapper exists and writes via _write_event when called; the
    default-OFF gate is enforced at the CALLER level (import-graph denylist),
    not inside the wrapper itself. This test exercises the wrapper directly.
    """

    def test_event_written(self):
        audit_emit.emit_federation_autonomous_call_blocked(
            call_site="federation.peer_register",
            session_id="s-auto",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "federation_autonomous_call_blocked")

    def test_call_site_field(self):
        audit_emit.emit_federation_autonomous_call_blocked(
            call_site="federation.write_endpoint",
        )
        e = self._last_event()
        self.assertEqual(e["call_site"], "federation.write_endpoint")

    def test_call_site_truncated(self):
        audit_emit.emit_federation_autonomous_call_blocked(
            call_site="c" * 200,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["call_site"]), 128)

    def test_event_schema_v2(self):
        audit_emit.emit_federation_autonomous_call_blocked(call_site="cs")
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestFederationWriteAttemptBlocked(TestEnvContext, _LogReader):
    """federation_write_attempt_blocked — shape + invocation test."""

    def test_event_written(self):
        audit_emit.emit_federation_write_attempt_blocked(
            method="POST",
            path="/api/federation/write",
            peer_id_cert_fingerprint="fp-abc",
            client_ip="127.0.0.1",
            fed_correlation_id="corr-123",
            session_id="s-write",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "federation_write_attempt_blocked")

    def test_domain_fields(self):
        audit_emit.emit_federation_write_attempt_blocked(
            method="DELETE",
            path="/api/federation/peer",
        )
        e = self._last_event()
        self.assertEqual(e["method"], "DELETE")
        self.assertEqual(e["path"], "/api/federation/peer")

    def test_method_truncated_at_16(self):
        audit_emit.emit_federation_write_attempt_blocked(
            method="X" * 50,
            path="/",
        )
        e = self._last_event()
        self.assertLessEqual(len(e["method"]), 16)

    def test_path_truncated_at_128(self):
        audit_emit.emit_federation_write_attempt_blocked(
            method="POST",
            path="/" + "p" * 200,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["path"]), 128)

    def test_event_schema_v2(self):
        audit_emit.emit_federation_write_attempt_blocked(method="GET", path="/")
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestConfidenceGateBlocked(TestEnvContext, _LogReader):
    """confidence_gate_blocked — shape + invocation test (PLAN-100 ADR-019-AMEND-1)."""

    def test_event_written(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["sha_exists"],
            fail_count=2,
            agent_name="Staff Backend Engineer",
            source="stdin",
            session_id="s-cg",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "confidence_gate_blocked")

    def test_domain_fields(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["sha_exists", "function_exists"],
            fail_count=3,
            agent_name="Senior Engineer",
            source="file",
        )
        e = self._last_event()
        self.assertEqual(e["blocking_classes"], ["sha_exists", "function_exists"])
        self.assertEqual(e["fail_count"], 3)
        self.assertEqual(e["agent_name"], "Senior Engineer")
        self.assertEqual(e["source"], "file")

    def test_invalid_fail_count_defaults_to_zero(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["sha_exists"],
            fail_count="not-an-int",
        )
        e = self._last_event()
        self.assertEqual(e["fail_count"], 0)

    def test_oversized_class_name_dropped(self):
        """Classes longer than 64 chars are dropped (MF-3 allowlist enforcement)."""
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["ok_class", "x" * 65],
            fail_count=1,
        )
        e = self._last_event()
        self.assertIn("ok_class", e["blocking_classes"])
        for c in e["blocking_classes"]:
            self.assertLessEqual(len(c), 64)

    def test_non_list_blocking_classes_yields_empty(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes="sha_exists",  # str, not list
            fail_count=1,
        )
        e = self._last_event()
        self.assertEqual(e["blocking_classes"], [])

    def test_agent_name_truncated(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["sha_exists"],
            fail_count=1,
            agent_name="a" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["agent_name"]), 64)

    def test_event_schema_v2(self):
        audit_emit.emit_confidence_gate_blocked(
            blocking_classes=["sha_exists"],
            fail_count=1,
        )
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


# ---------------------------------------------------------------------------
# PLAN-113 WIRE-AUDIT — new typed wrappers: invocation + shape tests.
# ---------------------------------------------------------------------------

class TestEscalationCluster(TestEnvContext, _LogReader):
    """Escalation cluster (4): detected / dispatched / suppressed / baseline_recorded."""

    def test_escalation_detected(self):
        audit_emit.emit_escalation_detected(
            signal="gate_skip",
            severity="high",
            plan_id="PLAN-001",
            session_id="s-esc",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "escalation_detected")
        self.assertEqual(e["signal"], "gate_skip")
        self.assertEqual(e["severity"], "high")
        self.assertEqual(e["plan_id"], "PLAN-001")

    def test_escalation_detected_truncation(self):
        audit_emit.emit_escalation_detected(
            signal="x" * 100,
            severity="y" * 100,
            plan_id="z" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["signal"]), 64)
        self.assertLessEqual(len(e["severity"]), 32)
        self.assertLessEqual(len(e["plan_id"]), 32)

    def test_escalation_dispatched(self):
        audit_emit.emit_escalation_dispatched(
            signal="canonical_edit_block",
            target_model="claude-opus-4-8",
            plan_id="PLAN-002",
            session_id="s-esc",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "escalation_dispatched")
        self.assertEqual(e["signal"], "canonical_edit_block")
        self.assertEqual(e["target_model"], "claude-opus-4-8")

    def test_escalation_dispatched_truncation(self):
        audit_emit.emit_escalation_dispatched(
            signal="x" * 100,
            target_model="y" * 100,
            plan_id="z" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["signal"]), 64)
        self.assertLessEqual(len(e["target_model"]), 64)
        self.assertLessEqual(len(e["plan_id"]), 32)

    def test_escalation_suppressed(self):
        audit_emit.emit_escalation_suppressed(
            signal="veto_non_opus",
            reason_code="no_incidents_detected",
            session_id="s-esc",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "escalation_suppressed")
        self.assertEqual(e["signal"], "veto_non_opus")
        self.assertEqual(e["reason_code"], "no_incidents_detected")

    def test_escalation_baseline_recorded(self):
        audit_emit.emit_escalation_baseline_recorded(
            signals_count=5,
            session_id="s-esc",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "escalation_baseline_recorded")
        self.assertEqual(e["signals_count"], 5)

    def test_escalation_baseline_recorded_non_negative(self):
        audit_emit.emit_escalation_baseline_recorded(signals_count=0)
        e = self._last_event()
        self.assertGreaterEqual(e["signals_count"], 0)

    def test_all_four_have_event_schema_v2(self):
        for fn, kwargs in [
            (audit_emit.emit_escalation_detected, {"signal": "s", "severity": "low", "plan_id": "p"}),
            (audit_emit.emit_escalation_dispatched, {"signal": "s", "target_model": "m", "plan_id": "p"}),
            (audit_emit.emit_escalation_suppressed, {"signal": "s", "reason_code": "r"}),
            (audit_emit.emit_escalation_baseline_recorded, {"signals_count": 0}),
        ]:
            with self.subTest(fn=fn.__name__):
                fn(**kwargs)
                e = self._last_event()
                self.assertEqual(e.get("event_schema"), "v2")


class TestSwarmFinalizeCluster(TestEnvContext, _LogReader):
    """Swarm finalize cluster (2): grouped / committed."""

    def test_swarm_finalize_grouped(self):
        audit_emit.emit_swarm_finalize_grouped(
            swarm_id="swarm-001",
            groups=3,
            session_id="s-sw",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "swarm_finalize_grouped")
        self.assertEqual(e["swarm_id"], "swarm-001")
        self.assertEqual(e["groups"], 3)

    def test_swarm_finalize_grouped_swarm_id_truncated(self):
        audit_emit.emit_swarm_finalize_grouped(
            swarm_id="s" * 100,
            groups=1,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["swarm_id"]), 64)

    def test_swarm_finalize_committed(self):
        audit_emit.emit_swarm_finalize_committed(
            swarm_id="swarm-002",
            commit="abc1234",
            session_id="s-sw",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "swarm_finalize_committed")
        self.assertEqual(e["swarm_id"], "swarm-002")
        self.assertEqual(e["commit"], "abc1234")

    def test_swarm_finalize_committed_commit_truncated(self):
        audit_emit.emit_swarm_finalize_committed(
            swarm_id="swarm-003",
            commit="c" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["commit"]), 40)

    def test_both_have_event_schema_v2(self):
        for fn, kwargs in [
            (audit_emit.emit_swarm_finalize_grouped, {"swarm_id": "s", "groups": 0}),
            (audit_emit.emit_swarm_finalize_committed, {"swarm_id": "s", "commit": "c"}),
        ]:
            with self.subTest(fn=fn.__name__):
                fn(**kwargs)
                e = self._last_event()
                self.assertEqual(e.get("event_schema"), "v2")


class TestKeyDroppedWrappers(TestEnvContext, _LogReader):
    """MULTI-DIM-ORPHAN: task_route_key_dropped / reality_ledger_key_dropped."""

    def test_task_route_key_dropped(self):
        audit_emit.emit_task_route_key_dropped(
            key="complexity",
            reason_code="unknown_field",
            session_id="s-tr",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "task_route_key_dropped")
        self.assertEqual(e["key"], "complexity")
        self.assertEqual(e["reason_code"], "unknown_field")

    def test_task_route_key_dropped_truncation(self):
        audit_emit.emit_task_route_key_dropped(
            key="k" * 100,
            reason_code="r" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["key"]), 64)
        self.assertLessEqual(len(e["reason_code"]), 32)

    def test_reality_ledger_key_dropped(self):
        audit_emit.emit_reality_ledger_key_dropped(
            key="plan_id",
            detector="ledger_parser_v2",
            session_id="s-rl",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "reality_ledger_key_dropped")
        self.assertEqual(e["key"], "plan_id")
        self.assertEqual(e["detector"], "ledger_parser_v2")

    def test_reality_ledger_key_dropped_truncation(self):
        audit_emit.emit_reality_ledger_key_dropped(
            key="k" * 100,
            detector="d" * 100,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["key"]), 64)
        self.assertLessEqual(len(e["detector"]), 64)

    def test_both_have_event_schema_v2(self):
        for fn, kwargs in [
            (audit_emit.emit_task_route_key_dropped, {"key": "k", "reason_code": "r"}),
            (audit_emit.emit_reality_ledger_key_dropped, {"key": "k", "detector": "d"}),
        ]:
            with self.subTest(fn=fn.__name__):
                fn(**kwargs)
                e = self._last_event()
                self.assertEqual(e.get("event_schema"), "v2")


class TestSkillReferenceNeverRead(TestEnvContext, _LogReader):
    """skill_reference_never_read typed wrapper — shape + invocation."""

    def test_event_written(self):
        audit_emit.emit_skill_reference_never_read(
            skill_path=".claude/skills/core/ceo-orchestration/SKILL.md",
            session_id="s-sk",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "skill_reference_never_read")

    def test_skill_path_is_hashed_not_raw(self):
        """Sec MF-3: raw path must NOT appear; 12-hex sha256 digest instead."""
        raw_path = ".claude/skills/core/ceo-orchestration/SKILL.md"
        audit_emit.emit_skill_reference_never_read(skill_path=raw_path)
        e = self._last_event()
        # The raw path must not appear as a field value.
        self.assertNotIn(raw_path, e.values())
        # The event must carry skill_path_hash (12-hex).
        self.assertIn("skill_path_hash", e)
        self.assertRegex(e["skill_path_hash"], r"^[0-9a-f]{12}$")

    def test_event_schema_v2(self):
        audit_emit.emit_skill_reference_never_read(skill_path="some/path")
        e = self._last_event()
        self.assertEqual(e.get("event_schema"), "v2")


class TestTournamentCluster(TestEnvContext, _LogReader):
    """Tournament cluster (8): run_started / task_scored / run_completed /
    budget_projected / budget_exceeded / aborted / fixture_rejected /
    judge_hijack_suspected."""

    def test_tournament_run_started(self):
        audit_emit.emit_tournament_run_started(
            swarm_id="swarm-t1",
            candidate_count=5,
            direction="minimize",
            session_id="s-tour",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_run_started")
        self.assertEqual(e["swarm_id"], "swarm-t1")
        self.assertEqual(e["candidate_count"], 5)
        self.assertEqual(e["direction"], "minimize")

    def test_tournament_task_scored(self):
        audit_emit.emit_tournament_task_scored(
            swarm_id="swarm-t1",
            loop_id="loop-1",
            score_bps=8500,
            tests_passed=10,
            tests_failed=0,
            session_id="s-tour",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_task_scored")
        self.assertEqual(e["loop_id"], "loop-1")
        self.assertEqual(e["score_bps"], 8500)
        self.assertIsInstance(e["score_bps"], int, "score_bps must be int (no floats in HMAC log)")
        self.assertEqual(e["tests_passed"], 10)
        self.assertEqual(e["tests_failed"], 0)

    def test_tournament_run_completed(self):
        audit_emit.emit_tournament_run_completed(
            swarm_id="swarm-t1",
            winner_loop_id="loop-1",
            rejected_count=4,
            decisive=True,
            session_id="s-tour",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_run_completed")
        self.assertEqual(e["winner_loop_id"], "loop-1")
        self.assertEqual(e["rejected_count"], 4)
        self.assertTrue(e["decisive"])

    def test_tournament_budget_projected(self):
        audit_emit.emit_tournament_budget_projected(
            swarm_id="swarm-t1",
            projected_cost_cents=250,
            candidate_count=5,
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_budget_projected")
        self.assertEqual(e["projected_cost_cents"], 250)
        self.assertIsInstance(e["projected_cost_cents"], int)

    def test_tournament_budget_exceeded(self):
        audit_emit.emit_tournament_budget_exceeded(
            swarm_id="swarm-t1",
            actual_cost_cents=300,
            cap_cents=250,
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_budget_exceeded")
        self.assertEqual(e["actual_cost_cents"], 300)
        self.assertEqual(e["cap_cents"], 250)

    def test_tournament_aborted(self):
        audit_emit.emit_tournament_aborted(
            swarm_id="swarm-t1",
            reason="no_candidates",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_aborted")
        self.assertEqual(e["reason"], "no_candidates")

    def test_tournament_fixture_rejected(self):
        audit_emit.emit_tournament_fixture_rejected(
            swarm_id="swarm-t1",
            loop_id="loop-bad",
            reason="duplicate_loop_id",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_fixture_rejected")
        self.assertEqual(e["loop_id"], "loop-bad")
        self.assertEqual(e["reason"], "duplicate_loop_id")

    def test_tournament_judge_hijack_suspected(self):
        audit_emit.emit_tournament_judge_hijack_suspected(
            swarm_id="swarm-t1",
            loop_id="loop-suspect",
            indicator="metric_impossible_zero",
        )
        e = self._last_event()
        self.assertEqual(e["action"], "tournament_judge_hijack_suspected")
        self.assertEqual(e["loop_id"], "loop-suspect")
        self.assertEqual(e["indicator"], "metric_impossible_zero")

    def test_all_eight_have_event_schema_v2(self):
        cases = [
            (audit_emit.emit_tournament_run_started,
             {"swarm_id": "s", "candidate_count": 1, "direction": "minimize"}),
            (audit_emit.emit_tournament_task_scored,
             {"swarm_id": "s", "loop_id": "l", "score_bps": 0, "tests_passed": 0, "tests_failed": 0}),
            (audit_emit.emit_tournament_run_completed,
             {"swarm_id": "s", "winner_loop_id": "l", "rejected_count": 0, "decisive": True}),
            (audit_emit.emit_tournament_budget_projected,
             {"swarm_id": "s", "projected_cost_cents": 0, "candidate_count": 0}),
            (audit_emit.emit_tournament_budget_exceeded,
             {"swarm_id": "s", "actual_cost_cents": 1, "cap_cents": 0}),
            (audit_emit.emit_tournament_aborted,
             {"swarm_id": "s", "reason": "r"}),
            (audit_emit.emit_tournament_fixture_rejected,
             {"swarm_id": "s", "loop_id": "l", "reason": "r"}),
            (audit_emit.emit_tournament_judge_hijack_suspected,
             {"swarm_id": "s", "loop_id": "l", "indicator": "i"}),
        ]
        for fn, kwargs in cases:
            with self.subTest(fn=fn.__name__):
                fn(**kwargs)
                e = self._last_event()
                self.assertEqual(e.get("event_schema"), "v2")

    def test_swarm_id_and_loop_id_truncation(self):
        audit_emit.emit_tournament_task_scored(
            swarm_id="s" * 100,
            loop_id="l" * 100,
            score_bps=0,
            tests_passed=0,
            tests_failed=0,
        )
        e = self._last_event()
        self.assertLessEqual(len(e["swarm_id"]), 64)
        self.assertLessEqual(len(e["loop_id"]), 64)


if __name__ == "__main__":
    unittest.main()
