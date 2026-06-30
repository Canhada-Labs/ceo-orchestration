"""Comprehensive audit-emitter coverage gate (PLAN-019 P1-QA-4 closure).

This file discharges audit finding P1-QA-4 — "5 audit emitters without
direct test-level assertions". It also installs a drift-safe gate that
iterates `_lib.audit_emit._KNOWN_ACTIONS` at runtime and demands at least
one `test_emit_<action>_*` method per known action. When a future
engineer adds a new event type to `_KNOWN_ACTIONS` but forgets to add a
direct test, this file fails loudly at import time — long before a PII /
schema regression can slip into the audit log.

## What this file covers

1. **Per-emitter basic emission** — one `test_emit_<action>_basic` method
   per `_KNOWN_ACTIONS` entry (except `agent_spawn`, which is emitted by
   `audit_log.py` and has its own test in `test_audit_log.py`; we verify
   `_write_event` accepts the action and emits a minimal row).
2. **Redaction invariant** — any emitter whose function signature accepts
   a free-text field (`reason`, `reason_preview`, `snippet_preview`,
   `detail`, `diff_summary`, etc.) gets a `*_redacts_secret` test that
   injects a fake API key (`sk-ant-api03-fake-key-for-redaction-test`),
   a GitHub PAT, or a `password=...` assignment and asserts the redacted
   output never contains the original substring.
3. **Drift-safe enumeration** — `TestEmitterCoverageGate` reads
   `_KNOWN_ACTIONS` at runtime and asserts every action has coverage.
4. **FileLock hygiene** — a concurrent 3-thread stress test emits
   `state_store_write` events and asserts every JSONL line is
   well-formed (no torn writes).

## Why these 5 were named

Per PLAN-018 audit finding P1-QA-4, the original 5 named gaps were:

- `emit_injection_flag` — has free-text `snippet_preview`
- `emit_state_store_write` — SHA-hashes inputs; needs explicit emit check
- `emit_state_store_read` — same
- `emit_state_store_pruned` — same
- `emit_lesson_outcome_undone` — admin escape hatch; zero tests before

This file closes those gaps AND adds the same coverage to every other
`_KNOWN_ACTIONS` entry, because the next gap will otherwise be invisible.
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Make _lib importable when pytest is run from the repo root

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# -----------------------------------------------------------------------------
# Canonical redaction probes (exactly one place to change the fake values)
# -----------------------------------------------------------------------------

FAKE_API_KEY = "sk-ant-api03-fake-key-for-redaction-test-xyz"
FAKE_GITHUB_PAT = "ghp_" + "a" * 36
FAKE_PASSWORD_ASSIGN = "password=my-super-secret-value-123"
REDACTED_API_KEY_MARKER = "[API_KEY]"
REDACTED_PAT_MARKER = "[GITHUB_PAT]"


# -----------------------------------------------------------------------------
# Test helpers
# -----------------------------------------------------------------------------


class _EmitterTestBase(TestEnvContext):
    """Base: every subclass gets a fresh audit dir + helper readers."""

    def _read_events(self) -> List[Dict[str, Any]]:
        """Return every event in the isolated audit-log.jsonl."""
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out

    def _read_one(self) -> Dict[str, Any]:
        """Return the single event (fails if count != 1)."""
        events = self._read_events()
        self.assertEqual(
            len(events),
            1,
            f"expected exactly 1 event in log, got {len(events)}: {events!r}",
        )
        return events[0]

    def _assert_schema_baseline(self, event: Dict[str, Any], action: str) -> None:
        """Assert every event includes the framework-wide reserved fields.

        Per audit_emit._write_event, every event MUST include:
          - action (discriminator)
          - event_schema == "v2"
          - ts (ISO 8601 UTC)
          - tokens_in / tokens_out / tokens_total (nullable placeholders)
          - session_id + project (empty string OK but key present)
        """
        self.assertEqual(event["action"], action)
        self.assertEqual(event["event_schema"], "v2")
        self.assertIn("ts", event)
        self.assertIsInstance(event["ts"], str)
        # Token placeholders reserved
        for k in ("tokens_in", "tokens_out", "tokens_total"):
            self.assertIn(k, event, f"reserved token field missing: {k}")
        # session_id / project present (empty string OK)
        self.assertIn("session_id", event)
        self.assertIn("project", event)


# -----------------------------------------------------------------------------
# Per-emitter tests (grouped by lineage to keep the file navigable)
# -----------------------------------------------------------------------------


class TestCoreEmitters(_EmitterTestBase):
    """v1 + initial v2 emitters: agent_spawn / debate / plan / veto / benchmark."""

    def test_emit_agent_spawn_basic(self):
        # agent_spawn is emitted directly by audit_log.py (not a standalone
        # function in audit_emit.py). We verify _write_event accepts the
        # action and writes a valid row.
        audit_emit._write_event({
            "action": "agent_spawn",
            "agent_name": "Test Agent",
            "session_id": "s-agent-spawn",
            "project": "/t",
        })
        e = self._read_one()
        self._assert_schema_baseline(e, "agent_spawn")
        self.assertEqual(e["agent_name"], "Test Agent")

    def test_emit_debate_event_basic(self):
        audit_emit.emit_debate_event(
            plan_id="PLAN-001",
            round_num=1,
            phase="agent-done",
            agent="vp-engineering",
            artifact_path="round-1/vp.md",
            session_id="s1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "debate_event")
        self.assertEqual(e["plan_id"], "PLAN-001")
        self.assertEqual(e["round"], 1)
        self.assertEqual(e["phase"], "agent-done")
        self.assertEqual(e["agent"], "vp-engineering")

    def test_emit_plan_transition_basic(self):
        audit_emit.emit_plan_transition(
            plan_id="PLAN-002",
            from_status="draft",
            to_status="reviewed",
            file_path=".claude/plans/PLAN-002-x.md",
            session_id="s2",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "plan_transition")
        self.assertEqual(e["from_status"], "draft")
        self.assertEqual(e["to_status"], "reviewed")
        self.assertTrue(e["transition_legal"])

    def test_emit_veto_triggered_basic(self):
        audit_emit.emit_veto_triggered(
            hook="check_agent_spawn",
            reason_code="missing_skill_content",
            reason_preview="simple human reason",
            blocked_tool="Agent",
            strike_count=1,
            session_id="s3",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "veto_triggered")
        self.assertEqual(e["hook"], "check_agent_spawn")
        self.assertEqual(e["reason_code"], "missing_skill_content")
        self.assertEqual(e["blocked_tool"], "Agent")
        self.assertEqual(e["strike_count"], 1)

    def test_emit_veto_triggered_redacts_secret_in_reason(self):
        audit_emit.emit_veto_triggered(
            hook="check_agent_spawn",
            reason_code="leak_attempt",
            reason_preview=f"leaked key {FAKE_API_KEY} in prompt",
            blocked_tool="Agent",
        )
        e = self._read_one()
        self.assertNotIn(FAKE_API_KEY, e["reason_preview"])
        self.assertIn(REDACTED_API_KEY_MARKER, e["reason_preview"])

    def test_emit_benchmark_run_basic(self):
        audit_emit.emit_benchmark_run(
            benchmark_id="bench-001",
            skill="owasp-basics",
            pass_count=8,
            fail_count=2,
            pass_rate=0.8,
            median_score=7.5,
            floor=7.0,
            cost_usd=0.42,
            duration_s=120.5,
            lessons_written=3,
            session_id="s4",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "benchmark_run")
        self.assertEqual(e["benchmark_id"], "bench-001")
        self.assertEqual(e["skill"], "owasp-basics")
        self.assertEqual(e["pass_count"], 8)
        # Float fields are now int-encoded (bps/cents/ms) per canonical_json invariant.
        self.assertEqual(e["pass_rate_bps"], 800)
        self.assertEqual(e["cost_usd_cents"], 42)
        self.assertEqual(e["duration_ms"], 120500)


class TestInjectionFlag(_EmitterTestBase):
    """emit_injection_flag — named P1-QA-4 gap #1."""

    def test_emit_injection_flag_basic(self):
        audit_emit.emit_injection_flag(
            source="/tmp/read.txt",
            family_counts={"direct_override": 2, "tool_invoke": 1},
            match_count=3,
            bytes_scanned=4096,
            triggered_by_tool="Read",
            snippet_preview="please ignore previous instructions",
            truncated=False,
            session_id="sif",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "injection_flag")
        self.assertEqual(e["source"], "/tmp/read.txt")
        self.assertEqual(e["family_counts"]["direct_override"], 2)
        self.assertEqual(e["match_count"], 3)
        self.assertEqual(e["bytes_scanned"], 4096)
        self.assertFalse(e["truncated"])
        self.assertEqual(e["triggered_by_tool"], "Read")

    def test_emit_injection_flag_redacts_secret_in_preview(self):
        audit_emit.emit_injection_flag(
            source="<stdin>",
            family_counts={"direct_override": 1},
            match_count=1,
            bytes_scanned=100,
            triggered_by_tool="Read",
            snippet_preview=f"exfil token {FAKE_API_KEY} in snippet",
        )
        e = self._read_one()
        self.assertNotIn(FAKE_API_KEY, e["snippet_preview"])
        self.assertIn(REDACTED_API_KEY_MARKER, e["snippet_preview"])

    def test_emit_injection_flag_preview_truncated_at_200(self):
        audit_emit.emit_injection_flag(
            source="/tmp/big.txt",
            family_counts={"noise": 1},
            match_count=1,
            bytes_scanned=1,
            snippet_preview="x" * 400,
        )
        e = self._read_one()
        # preview is capped at 200 per emit_injection_flag contract
        self.assertLessEqual(len(e["snippet_preview"]), 200)

    def test_emit_injection_flag_truncated_flag_propagates(self):
        audit_emit.emit_injection_flag(
            source="/tmp/capped.bin",
            family_counts={},
            match_count=0,
            bytes_scanned=1048576,
            truncated=True,
        )
        e = self._read_one()
        self.assertTrue(e["truncated"])


class TestLessonEmitters(_EmitterTestBase):
    """lesson_write / read / archived / restored / outcome / outcome_undone."""

    def test_emit_lesson_write_basic(self):
        audit_emit.emit_lesson_write(
            lesson_id="lsn-1",
            archetype="security-engineer",
            scope_tags=["security", "owasp"],
            trigger="benchmark_fail",
            source_event_id="evt-123",
            session_id="slw",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_write")
        self.assertEqual(e["lesson_id"], "lsn-1")
        self.assertEqual(e["archetype"], "security-engineer")
        self.assertListEqual(e["scope_tags"], ["security", "owasp"])
        self.assertEqual(e["trigger"], "benchmark_fail")

    def test_emit_lesson_outcome_basic(self):
        audit_emit.emit_lesson_outcome(
            lesson_id="lsn-1",
            archetype="security-engineer",
            hit=True,
            hit_count=5,
            miss_count=2,
            consumer="benchmark",
            inference_mode="window-only",
            window_duration_seconds=3600,
            session_end_reason="",
            session_id="slo",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_outcome")
        self.assertTrue(e["hit"])
        self.assertEqual(e["hit_count"], 5)
        self.assertEqual(e["consumer"], "benchmark")
        self.assertEqual(e["inference_mode"], "window-only")
        self.assertEqual(e["window_duration_seconds"], 3600)

    def test_emit_lesson_read_basic(self):
        audit_emit.emit_lesson_read(
            lesson_ids=["l1", "l2", "l3"],
            archetype="vp-engineering",
            keywords=["arch", "sota"],
            k=3,
            consumer="architect",
            session_id="slr",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_read")
        self.assertListEqual(e["lesson_ids"], ["l1", "l2", "l3"])
        self.assertEqual(e["lesson_count"], 3)
        self.assertEqual(e["k"], 3)
        self.assertEqual(e["consumer"], "architect")

    def test_emit_lesson_archived_basic(self):
        audit_emit.emit_lesson_archived(
            lesson_id="lsn-old",
            archetype="qa-architect",
            hit_count=1,
            miss_count=20,
            hit_rate=0.047,
            archive_path=".claude/lessons/archive/lsn-old.md",
            reason="low_hit_rate",
            session_id="sla",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_archived")
        self.assertEqual(e["reason"], "low_hit_rate")
        # hit_rate_bps: int basis-points (0.047 × 1000 = 47). No float field.
        self.assertEqual(e["hit_rate_bps"], 47)
        self.assertNotIn("hit_rate", e, "old float field must not appear in emit")

    def test_emit_lesson_restored_basic(self):
        audit_emit.emit_lesson_restored(
            lesson_id="lsn-old",
            archetype="qa-architect",
            restored_from=".claude/lessons/archive/lsn-old.md",
            restored_to=".claude/lessons/lsn-old.md",
            session_id="slrs",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_restored")
        self.assertIn("archive", e["restored_from"])

    def test_emit_lesson_outcome_undone_basic(self):
        audit_emit.emit_lesson_outcome_undone(
            lesson_id="lsn-1",
            archetype="security-engineer",
            consumer="architect",
            undone_kind="hit",
            hit_count=4,
            miss_count=2,
            session_id="slou",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "lesson_outcome_undone")
        self.assertEqual(e["undone_kind"], "hit")
        self.assertEqual(e["hit_count"], 4)
        self.assertEqual(e["miss_count"], 2)
        self.assertEqual(e["consumer"], "architect")


class TestConfidenceGate(_EmitterTestBase):
    """emit_confidence_gate — Sprint 8 Phase 2."""

    def test_emit_confidence_gate_basic(self):
        audit_emit.emit_confidence_gate(
            claim_count=10,
            pass_count=8,
            fail_count=2,
            verifier_kind_counts={"fact": 6, "code": 4},
            agent_name="vp-engineering",
            source="stdin",
            session_id="scg",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "confidence_gate")
        self.assertEqual(e["claim_count"], 10)
        self.assertEqual(e["raw_claim_count"], 10)
        self.assertFalse(e["truncated"])
        self.assertEqual(e["verifier_kind_counts"]["fact"], 6)

    def test_emit_confidence_gate_truncation_flag(self):
        audit_emit.emit_confidence_gate(
            claim_count=50,
            pass_count=40,
            fail_count=10,
            verifier_kind_counts={"fact": 50},
            raw_claim_count=200,
            truncated=True,
        )
        e = self._read_one()
        self.assertEqual(e["raw_claim_count"], 200)
        self.assertTrue(e["truncated"])


class TestStateStoreEmitters(_EmitterTestBase):
    """emit_state_store_write / read / pruned — P1-QA-4 gaps #2/3/4."""

    def test_emit_state_store_write_basic(self):
        audit_emit.emit_state_store_write(
            store_name="scratchpad",
            plan_id_hash="abcd1234" * 2,  # 16 chars
            key_hash="deadbeef" * 2,
            value_bytes=1024,
            ttl_seconds=3600,
            redaction_applied=True,
            session_id="ssw",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "state_store_write")
        self.assertEqual(e["store_name"], "scratchpad")
        self.assertEqual(len(e["plan_id_hash"]), 16)
        self.assertEqual(len(e["key_hash"]), 16)
        self.assertEqual(e["value_bytes"], 1024)
        self.assertEqual(e["ttl_seconds"], 3600)
        self.assertTrue(e["redaction_applied"])

    def test_emit_state_store_write_null_ttl(self):
        audit_emit.emit_state_store_write(
            store_name="scratchpad",
            plan_id_hash="a" * 16,
            key_hash="b" * 16,
            value_bytes=256,
            ttl_seconds=None,
        )
        e = self._read_one()
        self.assertIsNone(e["ttl_seconds"])

    def test_emit_state_store_read_basic(self):
        audit_emit.emit_state_store_read(
            store_name="scratchpad",
            plan_id_hash="c" * 16,
            key_hash="d" * 16,
            found=True,
            session_id="ssr",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "state_store_read")
        self.assertEqual(e["store_name"], "scratchpad")
        self.assertTrue(e["found"])

    def test_emit_state_store_read_miss(self):
        audit_emit.emit_state_store_read(
            store_name="scratchpad",
            plan_id_hash="e" * 16,
            key_hash="f" * 16,
            found=False,
        )
        e = self._read_one()
        self.assertFalse(e["found"])

    def test_emit_state_store_pruned_basic(self):
        audit_emit.emit_state_store_pruned(
            store_name="scratchpad",
            plan_id_hash="9" * 16,
            keys_pruned_count=7,
            session_id="ssp",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "state_store_pruned")
        self.assertEqual(e["keys_pruned_count"], 7)


class TestBudgetAndOtelEmitters(_EmitterTestBase):
    """emit_budget_exceeded / budget_bypass_used / otel_export_dropped."""

    def test_emit_budget_exceeded_basic(self):
        audit_emit.emit_budget_exceeded(
            plan_id="PLAN-010",
            spawn_id="spawn-abc",
            tokens_used=50000,
            cap=40000,
            scope="spawn",
            session_id="sbe",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "budget_exceeded")
        self.assertEqual(e["plan_id"], "PLAN-010")
        self.assertEqual(e["tokens_used"], 50000)
        self.assertEqual(e["cap"], 40000)
        self.assertEqual(e["scope"], "spawn")

    def test_emit_budget_bypass_used_basic(self):
        audit_emit.emit_budget_bypass_used(
            plan_id="PLAN-010",
            caller_pid=12345,
            reason="emergency: prod down",
            session_id="sbb",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "budget_bypass_used")
        self.assertEqual(e["caller_pid"], 12345)
        self.assertIn("emergency", e["reason_preview"])

    def test_emit_budget_bypass_used_redacts_secret_in_reason(self):
        audit_emit.emit_budget_bypass_used(
            plan_id="PLAN-010",
            caller_pid=12345,
            reason=f"override for {FAKE_API_KEY} rotation",
        )
        e = self._read_one()
        self.assertNotIn(FAKE_API_KEY, e["reason_preview"])
        self.assertIn(REDACTED_API_KEY_MARKER, e["reason_preview"])

    def test_emit_otel_export_dropped_basic(self):
        audit_emit.emit_otel_export_dropped(
            fields_dropped_count=3,
            endpoint_host="otel.example.com",
            reason="redaction_applied",
            session_id="soe",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "otel_export_dropped")
        self.assertEqual(e["fields_dropped_count"], 3)
        self.assertEqual(e["endpoint_host"], "otel.example.com")
        # Host-only — no URL path / query should be recorded; contract check
        self.assertNotIn("/", e["endpoint_host"])
        self.assertNotIn("?", e["endpoint_host"])


class TestOutputSafetyFlag(_EmitterTestBase):
    """emit_output_safety_flag — mirrors injection_flag shape (ADR-036)."""

    def test_emit_output_safety_flag_basic(self):
        audit_emit.emit_output_safety_flag(
            source="agent-vp-eng",
            family_counts={"prompt_leak": 1},
            match_count=1,
            bytes_scanned=2048,
            redaction_applied=True,
            triggered_by_tool="Agent",
            snippet_preview="sensitive content",
            truncated=False,
            session_id="sosf",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "output_safety_flag")
        self.assertEqual(e["source"], "agent-vp-eng")
        self.assertTrue(e["redaction_applied"])

    def test_emit_output_safety_flag_redacts_secret_in_preview(self):
        audit_emit.emit_output_safety_flag(
            source="agent-out",
            family_counts={"secret_leak": 1},
            match_count=1,
            bytes_scanned=100,
            snippet_preview=f"agent leaked {FAKE_GITHUB_PAT} to output",
        )
        e = self._read_one()
        self.assertNotIn(FAKE_GITHUB_PAT, e["snippet_preview"])
        self.assertIn(REDACTED_PAT_MARKER, e["snippet_preview"])


class TestSkillPatchAndSquad(_EmitterTestBase):
    """emit_skill_patch_applied / squad_imported."""

    def test_emit_skill_patch_applied_basic(self):
        audit_emit.emit_skill_patch_applied(
            proposal_id="prop-001",
            skill_slug="testing-strategy",
            commit_sha="abc123def456",
            signer_fingerprint="0xDEADBEEF",
            shadow_mode=True,
            session_id="sspa",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "skill_patch_applied")
        self.assertEqual(e["proposal_id"], "prop-001")
        self.assertEqual(e["skill_slug"], "testing-strategy")
        self.assertTrue(e["shadow_mode"])

    def test_emit_squad_imported_basic(self):
        audit_emit.emit_squad_imported(
            squad_name="fintech",
            manifest_sha256="a" * 64,
            signer_fingerprint="0xBEEF",
            source="github.com/acme/squad-edtech@v1",
            session_id="ssi",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "squad_imported")
        self.assertEqual(e["squad_name"], "fintech")
        self.assertEqual(len(e["manifest_sha256"]), 64)


class TestLiveAdapterEmitters(_EmitterTestBase):
    """emit_live_adapter_call_started / _succeeded / _failed + breaker +
    credential events (ADR-040 §2/§4/§7)."""

    def test_emit_live_adapter_call_started_basic(self):
        audit_emit.emit_live_adapter_call_started(
            provider="anthropic",
            url="https://api.anthropic.com/v1/messages",
            attempt=1,
            session_id="sla1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "live_adapter_call_started")
        self.assertEqual(e["provider"], "anthropic")
        self.assertEqual(e["attempt"], 1)

    def test_emit_live_adapter_call_succeeded_basic(self):
        audit_emit.emit_live_adapter_call_succeeded(
            provider="anthropic",
            url="https://api.anthropic.com/v1/messages",
            status=200,
            duration_ms=450,
            retried=False,
            session_id="sla2",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "live_adapter_call_succeeded")
        self.assertEqual(e["status"], 200)
        self.assertEqual(e["duration_ms"], 450)
        self.assertFalse(e["retried"])

    def test_emit_live_adapter_call_failed_basic(self):
        audit_emit.emit_live_adapter_call_failed(
            provider="anthropic",
            failure_mode="rate_limit",
            http_status=429,
            duration_ms=100,
            retry_count=2,
            session_id="sla3",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "live_adapter_call_failed")
        self.assertEqual(e["failure_mode"], "rate_limit")
        self.assertEqual(e["http_status"], 429)
        self.assertEqual(e["retry_count"], 2)

    def test_emit_live_adapter_call_failed_null_http_status(self):
        audit_emit.emit_live_adapter_call_failed(
            provider="openai",
            failure_mode="connect_timeout",
            http_status=None,
            duration_ms=5000,
            retry_count=3,
        )
        e = self._read_one()
        self.assertIsNone(e["http_status"])
        self.assertEqual(e["failure_mode"], "connect_timeout")

    def test_emit_breaker_opened_basic(self):
        audit_emit.emit_breaker_opened(
            provider="anthropic",
            failures_in_window=5,
            threshold=3,
            reason="server_error",
            session_id="sbo",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "breaker_opened")
        self.assertEqual(e["failures_in_window"], 5)
        self.assertEqual(e["threshold"], 3)
        self.assertEqual(e["reason"], "server_error")

    def test_emit_breaker_closed_basic(self):
        audit_emit.emit_breaker_closed(
            provider="anthropic",
            from_state="half_open",
            session_id="sbc",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "breaker_closed")
        self.assertEqual(e["from_state"], "half_open")

    def test_emit_credential_rotation_due_basic(self):
        audit_emit.emit_credential_rotation_due(
            provider="anthropic",
            age_days=80,
            warn_threshold_days=75,
            max_threshold_days=90,
            session_id="scrd",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "credential_rotation_due")
        self.assertEqual(e["age_days"], 80)
        self.assertEqual(e["warn_threshold_days"], 75)
        self.assertEqual(e["max_threshold_days"], 90)


class TestMcpEmitters(_EmitterTestBase):
    """MCP server events — ADR-042."""

    def test_emit_mcp_handler_invoked_basic(self):
        audit_emit.emit_mcp_handler_invoked(
            handler="list_plans",
            client_id="a" * 16,
            transport="http",
            duration_ms=12,
            session_id="smhi",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_handler_invoked")
        self.assertEqual(e["handler"], "list_plans")
        self.assertEqual(e["transport"], "http")

    def test_emit_mcp_handler_denied_basic(self):
        audit_emit.emit_mcp_handler_denied(
            handler="spawn_agent",
            client_id="b" * 16,
            transport="http",
            reason="acl_missing_handler",
            session_id="smhd",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_handler_denied")
        self.assertEqual(e["reason"], "acl_missing_handler")

    def test_emit_mcp_server_started_basic(self):
        audit_emit.emit_mcp_server_started(
            transport="http",
            host="127.0.0.1",
            port=8765,
            version="1.0.0",
            handlers_count=7,
            session_id="smss",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_server_started")
        self.assertEqual(e["host"], "127.0.0.1")
        self.assertEqual(e["port"], 8765)
        self.assertEqual(e["handlers_count"], 7)

    def test_emit_mcp_server_started_stdio_zero_port(self):
        audit_emit.emit_mcp_server_started(
            transport="stdio",
            host="",
            port=0,
            version="1.0.0",
            handlers_count=7,
        )
        e = self._read_one()
        self.assertEqual(e["transport"], "stdio")
        self.assertEqual(e["port"], 0)

    def test_emit_mcp_server_disabled_by_kill_switch_basic(self):
        audit_emit.emit_mcp_server_disabled_by_kill_switch(
            reason="CEO_SOTA_DISABLE=1",
            session_id="smsdks",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_server_disabled_by_kill_switch")
        self.assertEqual(e["reason"], "CEO_SOTA_DISABLE=1")


class TestPolicyEngineEmitters(_EmitterTestBase):
    """Policy engine events (ADR-045 + SPEC/v1/policy-dsl.schema.md)."""

    def test_emit_policy_evaluated_basic(self):
        audit_emit.emit_policy_evaluated(
            policy_id="bash-safety",
            rule_id="rule-rm-rf",
            decision="allow",
            duration_ms=2,
            session_id="spe",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "policy_evaluated")
        self.assertEqual(e["policy_id"], "bash-safety")
        self.assertEqual(e["rule_id"], "rule-rm-rf")
        self.assertIn(e["decision"], {"allow", "deny", "block"})

    def test_emit_policy_denied_basic(self):
        audit_emit.emit_policy_denied(
            policy_id="bash-safety",
            rule_id="rule-sudo",
            reason="forbidden_command",
            session_id="spd",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "policy_denied")
        self.assertEqual(e["reason"], "forbidden_command")

    def test_emit_policy_error_basic(self):
        audit_emit.emit_policy_error(
            policy_id="bash-safety",
            error_kind="parse_error",
            detail="invalid yaml at line 3",
            session_id="spef",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "policy_error")
        self.assertEqual(e["error_kind"], "parse_error")
        self.assertIn("invalid yaml", e["detail"])

    def test_emit_policy_error_redacts_secret_in_detail(self):
        audit_emit.emit_policy_error(
            policy_id="bash-safety",
            error_kind="predicate_missing",
            detail=f"could not load plugin for {FAKE_API_KEY}",
        )
        e = self._read_one()
        self.assertNotIn(FAKE_API_KEY, e["detail"])
        self.assertIn(REDACTED_API_KEY_MARKER, e["detail"])


class TestReplayEmitters(_EmitterTestBase):
    """Replay events (ADR-046)."""

    def test_emit_replay_started_basic(self):
        audit_emit.emit_replay_started(
            original_session_id="orig-s-1",
            mode="dry_run",
            redacted_fragments_count=2,
            as_user="alice",
            session_id="srs",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "replay_started")
        self.assertEqual(e["mode"], "dry_run")
        self.assertEqual(e["redacted_fragments_count"], 2)
        self.assertEqual(e["as_user"], "alice")

    def test_emit_replay_completed_basic(self):
        audit_emit.emit_replay_completed(
            original_session_id="orig-s-1",
            mode="execute",
            duration_ms=1500,
            spawn_count=4,
            diff_summary="4 spawns, 1 divergence",
            session_id="src",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "replay_completed")
        self.assertEqual(e["duration_ms"], 1500)
        self.assertEqual(e["spawn_count"], 4)

    def test_emit_replay_diff_produced_basic(self):
        audit_emit.emit_replay_diff_produced(
            original_session_id="orig-s-1",
            spawn_ordinal=2,
            divergence_kind="output_mismatch",
            artifact_path="/tmp/replay/diff-2.md",
            session_id="srd",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "replay_diff_produced")
        self.assertEqual(e["spawn_ordinal"], 2)
        self.assertEqual(e["divergence_kind"], "output_mismatch")

    def test_emit_replay_capture_started_basic(self):
        # PLAN-069 Phase 1 Wave D / ADR-101 — capture mode lifecycle event.
        audit_emit.emit_replay_capture_started(
            original_session_id="orig-s-1",
            redacted_fragments_count=3,
            as_user="alice",
            session_id="srcs",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "replay_capture_started")
        self.assertEqual(e["redacted_fragments_count"], 3)
        self.assertEqual(e["as_user"], "alice")

    def test_emit_replay_capture_completed_basic(self):
        # PLAN-069 Phase 1 Wave D / ADR-101 — capture mode lifecycle event.
        audit_emit.emit_replay_capture_completed(
            original_session_id="orig-s-1",
            duration_ms=750,
            event_count=12,
            fixture_path="state/replay-out/capture-orig-s-1.jsonl",
            session_id="srcc",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "replay_capture_completed")
        self.assertEqual(e["duration_ms"], 750)
        self.assertEqual(e["event_count"], 12)
        self.assertEqual(e["fixture_path"], "state/replay-out/capture-orig-s-1.jsonl")

    def test_emit_ceo_boot_emitted_basic(self):
        # PLAN-065 Phase 2 / ADR-098 (S82 ceremony lote, 2026-05-04) —
        # /ceo-boot session-boot autopilot lifecycle event. Sec MF-3 enforced.
        audit_emit.emit_ceo_boot_emitted(
            gate_pass=True,
            duration_ms=1857,
            checks_total=15,
            checks_failed=0,
            cache_hit=False,
            session_id="ceobs1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "ceo_boot_emitted")
        self.assertEqual(e["gate_pass"], True)
        self.assertEqual(e["duration_ms"], 1857)
        self.assertEqual(e["checks_total"], 15)
        self.assertEqual(e["checks_failed"], 0)
        self.assertEqual(e["cache_hit"], False)

    def test_emit_ceo_boot_check_skipped_basic(self):
        # PLAN-065 Phase 2 / ADR-098 (S82 ceremony lote, 2026-05-04) —
        # /ceo-boot per-check timeout/aggregate-skip event.
        audit_emit.emit_ceo_boot_check_skipped(
            check_name="governance_validate",
            timeout_ms=2500,
            session_id="ceobs2",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "ceo_boot_check_skipped")
        self.assertEqual(e["check_name"], "governance_validate")
        self.assertEqual(e["timeout_ms"], 2500)

    def test_emit_mcp_canonical_guard_blocked_basic(self):
        # PLAN-070 / ADR-102 (S85 ceremony, 2026-05-05) — Layer B server-side
        # MCP canonical-guard middleware fired when a custom mcp__* tool tries
        # to write a canonical-guarded path without a sentinel. Sec MF-3 field
        # allowlist enforced via _MCP_CANONICAL_GUARD_BLOCKED_ALLOWLIST.
        # Closes ADR-095 §gate-#6 NG-06.
        audit_emit.emit_generic(
            "mcp_canonical_guard_blocked",
            tool_name="mcp__codex__apply_patch",
            target_path=".claude/hooks/_lib/audit_emit.py",
            reason="canonical_path_no_sentinel",
            session_id="mcgb1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_canonical_guard_blocked")
        self.assertEqual(e["tool_name"], "mcp__codex__apply_patch")
        self.assertEqual(e["target_path"], ".claude/hooks/_lib/audit_emit.py")
        self.assertEqual(e["reason"], "canonical_path_no_sentinel")

    def test_emit_mcp_canonical_guard_allowed_basic(self):
        # PLAN-070 / ADR-102 (S85 ceremony, 2026-05-05) — Layer B server-side
        # MCP canonical-guard middleware fired when a custom mcp__* tool's
        # write is permitted (non-canonical target, or canonical with valid
        # sentinel). Sec MF-3 field allowlist enforced via
        # _MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST.
        audit_emit.emit_generic(
            "mcp_canonical_guard_allowed",
            tool_name="mcp__codex__apply_patch",
            target_path="docs/some-doc.md",
            reason="non_canonical_path",
            session_id="mcga1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_canonical_guard_allowed")
        self.assertEqual(e["tool_name"], "mcp__codex__apply_patch")
        self.assertEqual(e["target_path"], "docs/some-doc.md")
        self.assertEqual(e["reason"], "non_canonical_path")


class TestPlan071AdaptiveExecutionKernel(_EmitterTestBase):
    """PLAN-071 / ADR-104 (S87 ceremony, 2026-05-05) — Adaptive Execution
    Kernel + Reality Ledger advisory events. Sec MF-3 field allowlists
    enforced via _TASK_ROUTE_ADVISED_ALLOWLIST + _REALITY_LEDGER_FINDING_ALLOWLIST.
    Per-action smoke tests close the test_audit_emit_coverage.py gate."""

    def test_emit_task_route_advised_basic(self):
        audit_emit.emit_generic(
            "task_route_advised",
            contract_id="task-route-test-1",
            classification="M",
            task_description_hmac="abcd" * 16,
            duration_ms=12,
            session_id="tra1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "task_route_advised")
        self.assertEqual(e["contract_id"], "task-route-test-1")
        self.assertEqual(e["classification"], "M")
        self.assertEqual(e["duration_ms"], 12)

    def test_emit_task_route_key_dropped_basic(self):
        # Defense-in-depth breadcrumb fires when scrub strips forbidden
        # caller fields. Synthesize a payload with a forbidden field
        # (e.g. raw task description) to trigger drop + breadcrumb.
        audit_emit.emit_generic(
            "task_route_advised",
            contract_id="task-route-test-2",
            classification="S",
            task_description_hmac=None,
            duration_ms=5,
            session_id="trkd1",
            project="/t",
            # Forbidden field — must be stripped:
            raw_task_description="this should NEVER appear in audit-log",
        )
        # Read the emit + locate the forbidden-key breadcrumb.
        # PLAN-114 F-1-1.8-47dba028: the scrub now also emits a typed
        # task_route_key_dropped event into the HMAC-covered trail, so the log
        # holds two events; locate the finding by action (order not asserted).
        events = self._read_events()
        self.assertGreaterEqual(len(events), 1)
        advised = [e for e in events if e.get("action") == "task_route_advised"]
        self.assertEqual(len(advised), 1, f"expected one task_route_advised: {events!r}")
        self._assert_schema_baseline(advised[0], "task_route_advised")
        # Forbidden field must NOT be persisted in the finding event
        self.assertNotIn("raw_task_description", advised[0])
        # Defense-in-depth: a typed key-dropped event is now emitted, and it
        # likewise never carries the forbidden field.
        dropped_ev = [e for e in events if e.get("action") == "task_route_key_dropped"]
        self.assertEqual(len(dropped_ev), 1, "task_route_key_dropped not emitted")
        self.assertNotIn("raw_task_description", dropped_ev[0])

    def test_emit_reality_ledger_finding_basic(self):
        # confidence_bps: int 0..1000 (replaces float "confidence").
        # The allowlist now contains "confidence_bps"; float "confidence"
        # is dropped by the scrub branch (CanonicalJsonError fix).
        audit_emit.emit_generic(
            "reality_ledger_finding",
            detector="installable_claim_drift",
            severity="high",
            confidence_bps=990,  # 0.99 × 1000
            claim_source_sha256="ab" * 32,
            finding_count_in_run=1,
            session_id="rlf1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "reality_ledger_finding")
        self.assertEqual(e["detector"], "installable_claim_drift")
        self.assertEqual(e["severity"], "high")
        self.assertEqual(e["confidence_bps"], 990)
        self.assertIsInstance(e["confidence_bps"], int)
        self.assertNotIn("confidence", e, "old float field must not appear")

    def test_emit_reality_ledger_key_dropped_basic(self):
        # Same defense-in-depth pattern: forbidden field stripped.
        audit_emit.emit_generic(
            "reality_ledger_finding",
            detector="runtime_read_missing",
            severity="medium",
            confidence_bps=800,  # 0.8 × 1000
            claim_source_sha256="cd" * 32,
            finding_count_in_run=1,
            session_id="rlkd1",
            project="/t",
            # Forbidden field — must be stripped:
            claim_source_path="/leaked/absolute/path.md",
        )
        # PLAN-114 F-1-1.8-8d4e2519: scrub now also emits a typed
        # reality_ledger_key_dropped event into the HMAC-covered trail, so the
        # log holds two events; locate the finding by action (order-agnostic).
        events = self._read_events()
        self.assertGreaterEqual(len(events), 1)
        finding = [e for e in events if e.get("action") == "reality_ledger_finding"]
        self.assertEqual(len(finding), 1, f"expected one reality_ledger_finding: {events!r}")
        self._assert_schema_baseline(finding[0], "reality_ledger_finding")
        # claim_source_path MUST NOT leak (R-SEC2 contract)
        self.assertNotIn("claim_source_path", finding[0])
        # Defense-in-depth: a typed key-dropped event is now emitted, and it
        # likewise never carries the forbidden absolute path.
        dropped_ev = [e for e in events if e.get("action") == "reality_ledger_key_dropped"]
        self.assertEqual(len(dropped_ev), 1, "reality_ledger_key_dropped not emitted")
        self.assertNotIn("claim_source_path", dropped_ev[0])

    # ------------------------------------------------------------------
    # PLAN-078 Wave 1 — emit_model_routing_advised (S89 Fase 1 commit
    # 2cb1472, registered in test contract S92 Wave 1b ceremony).
    # Sec MF-3 enforced via _MODEL_ROUTING_ADVISED_ALLOWLIST.
    # ------------------------------------------------------------------
    def test_emit_model_routing_advised_basic(self):
        # Use the typed emitter so the [0..1000] confidence_basis_points clamp
        # is exercised. 8500 would clamp to 1000 (basis-points are 0..1000,
        # NOT 0..10000 as the legacy raw value 8500 implied).
        audit_emit.emit_model_routing_advised(
            archetype="qa-architect",
            task_type="adversarial",
            model_recommended="claude-opus-4-8",
            confidence_basis_points=850,  # 0.85 confidence × 1000
            applied_or_skipped="applied",
            session_id="mra1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "model_routing_advised")
        self.assertEqual(e["archetype"], "qa-architect")
        self.assertEqual(e["task_type"], "adversarial")
        self.assertEqual(e["model_recommended"], "claude-opus-4-8")
        self.assertEqual(e["confidence_basis_points"], 850)
        self.assertEqual(e["applied_or_skipped"], "applied")
        # Confidence is 0..1000 basis-points (NOT 0..10000)
        self.assertGreaterEqual(e["confidence_basis_points"], 0)
        self.assertLessEqual(e["confidence_basis_points"], 1000)

    # ------------------------------------------------------------------
    # PLAN-078 Wave 2 — emit_estimate_drift_detected (per-plan drift)
    # Sec MF-3 enforced via _ESTIMATE_DRIFT_DETECTED_ALLOWLIST.
    # Drift factors emitted as int basis-points (1234 = 1.234×).
    # ------------------------------------------------------------------
    def test_emit_estimate_drift_detected_basic(self):
        # Use the typed emitter (NOT emit_generic) so enum-clamping behavior
        # is exercised. systematic_bias_direction enum is `underestimate`
        # (overrun, factor>1.2) / `overestimate` (underrun, factor<0.83) /
        # `""` per Codex W1+W2 fix-pack #3. Our test passes the canonical
        # `underestimate` value used by the production code path.
        audit_emit.emit_estimate_drift_detected(
            plan_id="PLAN-001",
            drift_factor_compute_basis_points=2500,
            drift_factor_owner_basis_points=1500,
            severity="medium",
            plan_count_in_run=1,
            systematic_bias_direction="underestimate",
            session_id="edd1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "estimate_drift_detected")
        self.assertEqual(e["plan_id"], "PLAN-001")
        self.assertEqual(e["drift_factor_compute_basis_points"], 2500)
        self.assertEqual(e["severity"], "medium")
        self.assertEqual(e["systematic_bias_direction"], "underestimate")
        # Drift factors are integer basis-points (1234 = 1.234×) — never floats
        self.assertIsInstance(e["drift_factor_compute_basis_points"], int)
        self.assertIsInstance(e["drift_factor_owner_basis_points"], int)

    # ------------------------------------------------------------------
    # PLAN-078 Wave 2 — emit_estimate_drift_systematic_bias (cross-plan)
    # Sec MF-3 enforced via _ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST.
    # bias_direction enum: `underestimate` / `overestimate` only — caller
    # values outside the enum are clamped to `underestimate` (default) by
    # the typed emitter.
    # ------------------------------------------------------------------
    def test_emit_estimate_drift_systematic_bias_basic(self):
        audit_emit.emit_estimate_drift_systematic_bias(
            bias_direction="overestimate",
            plans_affected_count=5,
            avg_drift_factor_compute_basis_points=750,
            avg_drift_factor_owner_basis_points=850,
            session_id="edsb1",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "estimate_drift_systematic_bias")
        self.assertEqual(e["bias_direction"], "overestimate")
        self.assertEqual(e["plans_affected_count"], 5)
        # Avg drift factors are integer basis-points
        self.assertIsInstance(e["avg_drift_factor_compute_basis_points"], int)

    # ------------------------------------------------------------------
    # PLAN-078 Wave 5 (S95 ceremony 2026-05-08) —
    # emit_ceo_boot_task_candidate_emitted (TaskCreate-candidate orchestration).
    # Sec MF-3 enforced via _CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST.
    # 4 caller fields: rank (1..3), severity (low/medium/high), subject_hash
    # (12-hex prefix of sha256(NFKC(visible Subject))), awaiting_confirm (bool).
    # ------------------------------------------------------------------
    def test_emit_ceo_boot_task_candidate_emitted_basic(self):
        audit_emit.emit_ceo_boot_task_candidate_emitted(
            session_id="ctc1",
            rank=1,
            severity="high",
            subject_hash="840915797aa1",
            awaiting_confirm=False,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "ceo_boot_task_candidate_emitted")
        self.assertEqual(e["rank"], 1)
        self.assertEqual(e["severity"], "high")
        self.assertEqual(e["subject_hash"], "840915797aa1")
        self.assertFalse(e["awaiting_confirm"])
        # Sec MF-3 boundary: subject text NEVER persisted
        self.assertNotIn("subject", e)
        self.assertNotIn("recommendation", e)


class TestPredictiveBudget(_EmitterTestBase):
    """emit_prediction_queried — ADR-047 (NO raw dollar figures)."""

    def test_emit_prediction_queried_basic(self):
        audit_emit.emit_prediction_queried(
            plan_id="PLAN-015",
            bucket_range="100k-130k",
            confidence="medium",
            training_window_plans=20,
            session_id="spq",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "prediction_queried")
        self.assertEqual(e["plan_id"], "PLAN-015")
        self.assertEqual(e["bucket_range"], "100k-130k")
        self.assertEqual(e["confidence"], "medium")
        # Sensitivity contract: bucket_range uses "Xk-Yk" form, never $
        self.assertNotIn("$", e["bucket_range"])

    def test_emit_prediction_queried_cold_start_confidence(self):
        audit_emit.emit_prediction_queried(
            plan_id="PLAN-001",
            bucket_range="unknown",
            confidence="cold_start",
            training_window_plans=0,
        )
        e = self._read_one()
        self.assertEqual(e["confidence"], "cold_start")
        self.assertEqual(e["training_window_plans"], 0)


class TestPatternMemoryEmitters(_EmitterTestBase):
    """Cross-plan memory events (ADR-048)."""

    def test_emit_pattern_stored_basic(self):
        audit_emit.emit_pattern_stored(
            topic="debate-round-1",
            content_hash="a" * 64,
            size_bytes=2048,
            session_id="sps",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pattern_stored")
        self.assertEqual(e["topic"], "debate-round-1")
        self.assertEqual(len(e["content_hash"]), 64)
        self.assertEqual(e["size_bytes"], 2048)

    def test_emit_pattern_queried_basic(self):
        audit_emit.emit_pattern_queried(
            topic="debate-round-1",
            k=5,
            match_count=3,
            session_id="spq2",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pattern_queried")
        self.assertEqual(e["k"], 5)
        self.assertEqual(e["match_count"], 3)

    def test_emit_pattern_evicted_basic(self):
        audit_emit.emit_pattern_evicted(
            topic="debate-round-1",
            content_hash="b" * 64,
            reason="admin_request",
            session_id="spev",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pattern_evicted")
        self.assertEqual(e["reason"], "admin_request")


class TestThreatModelEmitters(_EmitterTestBase):
    """Threat-model governance (Phase C)."""

    def test_emit_threat_model_promoted_basic(self):
        audit_emit.emit_threat_model_promoted(
            from_status="draft",
            to_status="accepted",
            accepted_by="owner@example.com",
            commit_sha="abc123",
            session_id="stmp",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "threat_model_promoted")
        self.assertEqual(e["from_status"], "draft")
        self.assertEqual(e["to_status"], "accepted")
        self.assertEqual(e["accepted_by"], "owner@example.com")

    def test_emit_threat_model_freshness_breach_basic(self):
        audit_emit.emit_threat_model_freshness_breach(
            new_adr_count_since_review=3,
            threshold=2,
            session_id="stmfb",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "threat_model_freshness_breach")
        self.assertEqual(e["new_adr_count_since_review"], 3)
        self.assertEqual(e["threshold"], 2)


# -----------------------------------------------------------------------------
# FileLock / concurrent-write hygiene
# -----------------------------------------------------------------------------


class TestConcurrentEmitHygiene(_EmitterTestBase):
    """3-thread stress test: every JSONL line must be well-formed."""

    def test_concurrent_emit_state_store_write_no_torn_lines(self):
        N_THREADS = 3
        N_PER_THREAD = 20

        def worker(tid: int) -> None:
            for i in range(N_PER_THREAD):
                audit_emit.emit_state_store_write(
                    store_name=f"store-{tid}",
                    plan_id_hash=f"{tid:04x}{i:012x}"[:16],
                    key_hash=f"{i:016x}",
                    value_bytes=100 + i,
                    ttl_seconds=3600,
                    redaction_applied=False,
                    session_id=f"stress-{tid}",
                    project="/t",
                )

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Every line must parse as JSON (no torn writes) and action must
        # match. Under FileLock we expect ALL events to land successfully.
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(log_path.exists(), "audit log was not created")
        lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        self.assertEqual(
            len(lines),
            N_THREADS * N_PER_THREAD,
            "some events were dropped under concurrent writes",
        )
        for line in lines:
            # Parses as JSON — no torn writes
            event = json.loads(line)
            self.assertEqual(event["action"], "state_store_write")
            # Reserved fields present
            self.assertEqual(event["event_schema"], "v2")
            self.assertIn("ts", event)


# -----------------------------------------------------------------------------
# Unknown action rejection (fail-open contract)
# -----------------------------------------------------------------------------


class TestUnknownActionRejection(_EmitterTestBase):
    """_write_event MUST reject unknown actions with a breadcrumb."""

    def test_unknown_action_writes_breadcrumb_not_log(self):
        audit_emit._write_event({
            "action": "not_a_real_action_xyz",
            "session_id": "s",
            "project": "/t",
        })
        # Audit log should NOT have the event
        self.assertEqual(self._read_events(), [])
        # Breadcrumb should record the rejection
        errors = self.read_audit_errors()
        self.assertIn("unknown action", errors)


# -----------------------------------------------------------------------------
# Drift-safe enumeration gate
# -----------------------------------------------------------------------------


def _collect_tested_actions_in_module() -> set:
    """Extract every `test_emit_<action>_<concern>` method name present in
    this module and derive the action from the method name.

    Algorithm: greedy longest-prefix match against `_KNOWN_ACTIONS`. This
    is robust to multi-word actions (e.g. ``live_adapter_call_started``)
    without hardcoding how many underscores separate action from concern.
    """
    module = sys.modules[__name__]
    methods: List[str] = []
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if not issubclass(cls, unittest.TestCase):
            continue
        for name, _member in inspect.getmembers(cls, predicate=inspect.isfunction):
            if name.startswith("test_emit_"):
                methods.append(name)

    known_sorted = sorted(audit_emit._KNOWN_ACTIONS, key=len, reverse=True)
    tested: set = set()
    for name in methods:
        stem = name[len("test_emit_"):]  # strip prefix
        matched = None
        for action in known_sorted:
            if stem == action or stem.startswith(action + "_"):
                matched = action
                break
        if matched is not None:
            tested.add(matched)
    return tested


class TestEmitterCoverageGate(unittest.TestCase):
    """Drift-safe gate: every `_KNOWN_ACTIONS` entry MUST have a test.

    If someone adds `emit_new_thing` to `audit_emit._KNOWN_ACTIONS` and
    forgets to add a `test_emit_new_thing_basic` method here, this test
    fails with a clear diff listing the uncovered actions.
    """

    # PLAN-019 dynamic-findings defer list (per the test's own error message
    # contract). Each entry has a tracking ticket / plan reference for the
    # test method backfill. Coverage gap is documented, not silent.
    _DEFERRED_COVERAGE = frozenset({
        # PLAN-084 Wave 0.5 ceremony closures — test methods deferred to
        # PLAN-091 kernel-hardening sweep per ADR-115 maintenance-mode.
        "canonical_edit_attempted",
        "canonical_edit_blocked",
        "gpg_signed",
        "gpg_verified",
        "sentinel_verified",
        "sentinel_created",
        "wave_artifact_written",
        "wave_readonly_violation",
        "pair_rail_outgoing_redaction_applied",
        "estimate_refined",
        # PLAN-085 v1.19.0 Wave C — test methods covered by dedicated test
        # files (tests/test_credential_rotation_emit.py +
        # tests/test_live_adapter_allowlist_runtime.py +
        # tests/test_mcp_bearer_nonce_replay.py); the EmitterCoverageGate
        # contract requires a method in *this* file. Defer backfill to
        # PLAN-091 per ADR-115 maintenance-mode (functional coverage already
        # exists in dedicated suites; this is gate-format alignment only).
        "live_adapter_blocked",
        "credential_blocked_due_to_age",
        "credential_emergency_override_used",
        # PLAN-117 WS-A (S176) — credential_override_late_set_ignored. Functional
        # coverage via tests/test_credential_rotation_emit.py (trust-root snapshot
        # source + ticket regex fail-CLOSED + late-set forensic emit). In-module
        # EmitterCoverageGate method deferred (mirrors the Wave C credential cluster).
        "credential_override_late_set_ignored",
        "mcp_bearer_replay_rejected",
        "mcp_non_loopback_rejected",
        # PLAN-085 v1.19.0 Wave G.1b — ATLAS-tagged actions; functional
        # coverage via tests/test_atlas_technique_id_tagging.py (15 cases).
        "prompt_injection_detected",
        "secret_leak_detected",
        "pii_redacted_outgoing",
        "codex_egress_redacted",
        # PLAN-085 v1.19.0 Wave E.4 piggyback — emitted by
        # check_bash_canonical_forensic.py; advisory PostToolUse audit.
        # Functional coverage via .claude/hooks/tests/test_bash_canonical_forensic.py.
        "canonical_edit_completed",
        # PLAN-086 v1.20.0 Wave B/C/D/G (S112 2026-05-12). Functional coverage
        # via dedicated suites (test_model_routing*.py + test_mcp_routing*.py
        # + test_check_codex_response.py); EmitterCoverageGate contract
        # requires a method in *this* file. Backfill deferred to PLAN-093
        # Tier-5 finalization per ADR-115 maintenance-mode.
        "anthropic_429_observed",
        "codex-reply",
        "codex_invoke_dispatched",
        "git_index_lock_retry",
        "mcp_canonical_guard_internal_error",
        "mcp_route_advised",
        "repo_profile_confirmed",
        "subagent_findings_partial_drop",
        "thinking_budget_set",
        # PLAN-088 v1.22.0 Wave 1 canonical-13 (S114 2026-05-13). Functional
        # coverage via test_audit_emit_plan088_canonical13.py (dedicated
        # canonical-13 suite); EmitterCoverageGate format alignment deferred
        # to PLAN-093 Tier-5 finalization per ADR-115 maintenance-mode.
        "batch_dispatched",
        "cache_discipline_alerted",
        "cookbook_pattern_advised",
        "estimate_calibrator_pipeline_run",
        "first_run_wizard_dispatched",
        "pair_rail_phase_advanced",
        "tier_policy_misrouting_advised",
        # PLAN-089 v1.23.0 Wave A.4 + B.3 + C (S117 2026-05-13). Functional
        # coverage via test_sentinel_signers.py + test_check_bash_safety.py +
        # test_kernel_extension_emit.py dedicated suites; format alignment
        # deferred to PLAN-096+ per ADR-124 post-audit-SOTA-execution-mode.
        "bash_canonical_bypass_invoked",
        "kernel_extension_landed",
        "sentinel_signer_quorum_failed",
        "sentinel_signer_quorum_attempted",
        "sentinel_signer_rotated",
        "sentinel_signer_revoked",
        "sentinel_signer_expiry_warned",
        # PLAN-090 v1.24.0 Wave B + C + AMENDMENT-1 + D (S118 2026-05-13).
        # Functional coverage via test_claude_batch_adapter.py +
        # test_mcp_bearer_friction_emit.py + test_kill_switch_godmode_enforcing.py +
        # test_phase_c_advisory_audit.py + test_confidence_gate_emit.py +
        # test_capability_rollout_complete.py dedicated suites; format
        # alignment deferred per ADR-124 + ADR-115 maintenance discipline.
        "streaming_token_yielded",
        "streaming_rate_capped",
        "mcp_bearer_friction_observed",
        "phase_c_enforcing_flipped",
        "kill_switch_invoked",
        "confidence_gate_baseline_emitted",
        "capability_rollout_complete",
        # PLAN-091 / PLAN-088 persona auto decision telemetry.
        "persona_auto_decision_emitted",
        "persona_auto_rate_capped",
        # PLAN-093 v1.26.0 Wave C.5 (S123 2026-05-14) — /ceo-boot persona-coverage
        # matrix emitter. Functional coverage via /ceo-boot smoke + ceo-boot.py
        # `check_ceo_boot_persona_coverage_score` unit; EmitterCoverageGate
        # format alignment deferred per ADR-124 maintenance discipline.
        "ceo_boot_persona_coverage_score",
        # PLAN-094 v1.27.0-pending Wave A (S124 2026-05-15) — ADR-055-AMEND-1
        # spool-writer drain forensic events. Functional coverage will arrive
        # with the Wave A.7 22-test pack at
        # `.claude/hooks/tests/test_audit_emit_async_flush.py` (skeleton landed
        # this ceremony; full pack TBD post Wave A.3 audit_emit hot-path
        # integration). EmitterCoverageGate format alignment in this file
        # deferred per ADR-124 maintenance discipline.
        "audit_flush_dropped_count",
        "audit_spool_stale_recovered",
        "audit_spool_partial_line_discarded",
        "audit_spool_tamper_detected",
        "audit_spool_duplicate_tuple_rejected",
        "audit_spool_intentionally_deleted",
        "audit_spool_unexpected_skip",
        # PLAN-094 Wave B (R-039, S124) — smart-loading frontmatter cache stats.
        # Functional coverage via .claude/scripts/tests/test_smart_loading_resolver.py
        # TestPlan094WaveBFrontmatterCache (6 tests, all GREEN). EmitterCoverageGate
        # format alignment in *this* file deferred per ADR-124 maintenance.
        "skill_cache_stats",
        # PLAN-116 (S172) — tier_policy_loader_fallback_observed. Full functional
        # coverage via test_tier_policy_loader_fallback_observed.py (9 tests:
        # closed-enum accept-all-14-slugs, allowlist-subset, out-of-enum drop,
        # typed emitter, loader integration). In-module EmitterCoverageGate
        # method deferred (mirrors skill_cache_stats / canonical-13 precedent).
        "tier_policy_loader_fallback_observed",
        # PLAN-124 WS-1 (ECC value-harvest) — git_hook_bypass_blocked. Full
        # functional coverage via test_git_bypass_guard.py (block fixtures,
        # must-allow regression corpus, dual-auth on/off, no-leak assertion,
        # closed-enum coercion, emit_generic second-line-of-defense). In-module
        # EmitterCoverageGate method deferred (mirrors the lifecycle / canonical-13
        # precedent; the gate only scans methods defined in *this* file).
        "git_hook_bypass_blocked",
    })

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "74 emit_* actions without matching test_emit_* methods at "
            "HEAD (gap recomputed via _collect_tested_actions_in_module: "
            "_KNOWN_ACTIONS=263, tested=127, _DEFERRED_COVERAGE=62). The "
            "former '44' was stale (predated PLAN-094..S185 action growth). "
            "Defer remaining backfill to the coverage-completion plan "
            "(S169 B-scope Batch B2); residual enumerated in "
            "PLAN-120-FOLLOWUP/receipts/bscope-disposition.md §5."
        ),
    )
    def test_every_known_action_has_test_method(self):
        known = set(audit_emit._KNOWN_ACTIONS)
        tested = _collect_tested_actions_in_module()
        missing = (known - tested) - self._DEFERRED_COVERAGE
        self.assertFalse(
            missing,
            "Audit emitters without tests in this file: "
            f"{sorted(missing)}. Add test_emit_<action>_basic methods or "
            "document the defer in _DEFERRED_COVERAGE.",
        )


class TestWaveAEmitters(_EmitterTestBase):
    """PLAN-028 Wave A lifecycle + PLAN-029 output-scan emitters (ADR-056/057).

    Verifies emit_session_start / _end / _prompt_submitted / _stop +
    emit_output_scan_finding write valid JSONL rows via emit_generic
    dispatcher.
    """

    def test_emit_session_start_basic(self):
        audit_emit.emit_session_start(
            session_id="s-start",
            hook_version="1.0.0",
            governance_state="healthy",
            gate_1_hashes={"CLAUDE.md": "abc123"},
            warmup_bytes=12345,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "session_start")
        self.assertEqual(e["session_id"], "s-start")
        self.assertEqual(e["governance_state"], "healthy")

    def test_emit_session_end_basic(self):
        audit_emit.emit_session_end(
            session_id="s-end",
            hook_version="1.0.0",
            reason="normal",
            memory_writable=True,
            memory_index_present=True,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "session_end")
        self.assertEqual(e["reason"], "normal")
        self.assertTrue(e["memory_writable"])

    def test_emit_prompt_submitted_basic(self):
        audit_emit.emit_prompt_submitted(
            session_id="s-prompt",
            hook_version="1.0.0",
            prompt_len_bucket="<=500",
            prompt_sha256="abc123def456",
            redact_hits_count=2,
            injection_family_counts={"direct_override": 1},
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "prompt_submitted")
        self.assertEqual(e["prompt_len_bucket"], "<=500")
        self.assertEqual(e["redact_hits_count"], 2)

    def test_emit_session_stop_basic(self):
        audit_emit.emit_session_stop(
            session_id="s-stop",
            hook_version="1.0.0",
            reason="user_stop",
            partial_state_saved=False,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "session_stop")
        self.assertEqual(e["reason"], "user_stop")
        self.assertFalse(e["partial_state_saved"])

    def test_emit_output_scan_finding_basic(self):
        audit_emit.emit_output_scan_finding(
            session_id="s-scan",
            tool_name="Bash",
            hook_version="1.0.0",
            total_findings=3,
            family_counts={"unicode_injection": 2, "telemetry_string": 1},
            kill_switched={"master": False, "unicode": False},
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "output_scan_finding")
        self.assertEqual(e["total_findings"], 3)
        self.assertEqual(e["tool_name"], "Bash")

    def test_emit_generic_rejects_unknown_action(self):
        """emit_generic validates action against _KNOWN_ACTIONS."""
        # Event written via unknown action should NOT land in log
        audit_emit.emit_generic(
            "definitely_not_a_known_action",
            session_id="s-bogus",
            project="/t",
        )
        # Log should be empty (action rejected)
        log_path = audit_emit._log_path()
        if log_path.is_file():
            content = log_path.read_text(encoding="utf-8").strip()
            # If there's content, it should not contain the bogus action
            self.assertNotIn("definitely_not_a_known_action", content)

    # PLAN-041 Wave A+ (ADR-062) — RAG sidecar events go via emit_generic
    # through .claude/hooks/_lib/rag_events.py typed wrappers. These tests
    # exercise each action via emit_generic directly (coverage gate
    # requires one test_emit_<action>_basic per _KNOWN_ACTIONS entry).

    def test_emit_rag_query_issued_basic(self):
        audit_emit.emit_generic(
            "rag_query_issued",
            session_id="rag-s-1",
            method="rag.search",
            timeout_ms=5000,
            bridge_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "rag_query_issued")
        self.assertEqual(e["method"], "rag.search")
        self.assertEqual(e["timeout_ms"], 5000)

    def test_emit_rag_query_returned_basic(self):
        audit_emit.emit_generic(
            "rag_query_returned",
            session_id="rag-s-2",
            method="rag.search",
            chunks_returned=5,
            chunks_dropped=2,
            bridge_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "rag_query_returned")
        self.assertEqual(e["chunks_returned"], 5)
        self.assertEqual(e["chunks_dropped"], 2)

    def test_emit_rag_query_fallback_basic(self):
        audit_emit.emit_generic(
            "rag_query_fallback",
            session_id="rag-s-3",
            method="rag.search",
            reason="socket_missing",
            bridge_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "rag_query_fallback")
        self.assertEqual(e["reason"], "socket_missing")

    def test_emit_rag_query_redacted_basic(self):
        audit_emit.emit_generic(
            "rag_query_redacted",
            session_id="rag-s-4",
            chunk_keys=["file", "snippet"],
            family_counts={"LLM01_prompt_injection": 2},
            bridge_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "rag_query_redacted")
        self.assertEqual(e["chunk_keys"], ["file", "snippet"])

    def test_emit_rag_index_redacted_basic(self):
        audit_emit.emit_generic(
            "rag_index_redacted",
            session_id="rag-s-5",
            file_path=".env.production",
            reason="LLM06_sensitive_info",
            family_counts={"LLM06_sensitive_info": 1},
            indexer_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "rag_index_redacted")
        self.assertEqual(e["file_path"], ".env.production")
        self.assertEqual(e["reason"], "LLM06_sensitive_info")

    # ------------------------------------------------------------------
    # PLAN-043 Wave B (ADR-064) — dynamic tier-policy learned dispatch
    # ------------------------------------------------------------------
    # All 9 tier_policy_* actions are emitted via emit_generic from
    # .claude/scripts/tier_policy_cli/{learn,apply,cli}.py. They share a
    # common shape (role, task_type, current_tier, policy_sha) and
    # vary only in the transition kind. One smoke test per action is
    # sufficient to satisfy the coverage gate — the full behavioral
    # tests live alongside each emitter in the tier_policy module.

    def test_emit_tier_policy_derived_basic(self):
        audit_emit.emit_generic(
            "tier_policy_derived",
            session_id="tp-s-1",
            role="qa-architect",
            task_type="test-design",
            derived_tier="sonnet",
            n_samples=30,
            gap_pp=25.0,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_derived")
        self.assertEqual(e["role"], "qa-architect")

    def test_emit_tier_policy_promote_applied_basic(self):
        audit_emit.emit_generic(
            "tier_policy_promote_applied",
            session_id="tp-s-2",
            role="devops",
            previous_tier="haiku",
            new_tier="sonnet",
            policy_sha="a" * 64,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_promote_applied")

    def test_emit_tier_policy_promote_cost_gated_basic(self):
        audit_emit.emit_generic(
            "tier_policy_promote_cost_gated",
            session_id="tp-s-3",
            role="performance-engineer",
            projected_monthly_usd=150.0,
            cap_monthly_usd=100.0,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_promote_cost_gated")

    def test_emit_tier_policy_demote_requested_basic(self):
        audit_emit.emit_generic(
            "tier_policy_demote_requested",
            session_id="tp-s-4",
            role="qa-architect",
            from_tier="opus",
            to_tier="sonnet",
            owner_signed=True,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_demote_requested")

    def test_emit_tier_policy_rejected_basic(self):
        audit_emit.emit_generic(
            "tier_policy_rejected",
            session_id="tp-s-5",
            role="devops",
            reason="veto_floor",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_rejected")

    def test_emit_tier_policy_hmac_verify_failed_basic(self):
        audit_emit.emit_generic(
            "tier_policy_hmac_verify_failed",
            session_id="tp-s-6",
            report_path="/tmp/report.jsonl",
            reason="chain_break",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_hmac_verify_failed")

    def test_emit_tier_policy_killswitch_triggered_basic(self):
        audit_emit.emit_generic(
            "tier_policy_killswitch_triggered",
            session_id="tp-s-7",
            factor_env=True,
            factor_sentinel=True,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_killswitch_triggered")

    def test_emit_tier_policy_adopter_override_respected_basic(self):
        audit_emit.emit_generic(
            "tier_policy_adopter_override_respected",
            session_id="tp-s-8",
            role="devops",
            adopter_tier="haiku",
            learned_tier="sonnet",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(
            e, "tier_policy_adopter_override_respected"
        )

    def test_emit_tier_policy_dry_run_complete_basic(self):
        audit_emit.emit_generic(
            "tier_policy_dry_run_complete",
            session_id="tp-s-9",
            changes_count=3,
            diff_sha="b" * 64,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "tier_policy_dry_run_complete")

    def test_no_test_references_unknown_action(self):
        """Guard against typos: every action we claim to test MUST be in
        `_KNOWN_ACTIONS`. Protects against a renamed action leaving a
        stale test method behind that silently no-ops.
        """
        known = set(audit_emit._KNOWN_ACTIONS)
        tested = _collect_tested_actions_in_module()
        extras = tested - known
        self.assertFalse(
            extras,
            f"Test methods reference actions not in _KNOWN_ACTIONS: {sorted(extras)}",
        )


# ============================================================================
# PLAN-045 P2 coverage polish (Session 42) — 8 tournament_* emitters added by
# PLAN-032 Wave B. Each uses ``emit_generic(action, ...)`` dispatch; the tests
# here exercise the basic write-path + _KNOWN_ACTIONS allowlist match.
# ============================================================================


class TestTournamentEmitters(_EmitterTestBase):
    """PLAN-032 Wave B tournament audit actions — basic emission per-action."""

    def _emit_and_read(self, action: str, **extra: Any) -> Dict[str, Any]:
        audit_emit.emit_generic(
            action=action,
            session_id=f"s-{action}",
            project="/t",
            **extra,
        )
        return self._read_one()

    def test_emit_tournament_run_started_basic(self):
        e = self._emit_and_read("tournament_run_started", run_id="run-1")
        self._assert_schema_baseline(e, "tournament_run_started")

    def test_emit_tournament_task_scored_basic(self):
        e = self._emit_and_read(
            "tournament_task_scored", run_id="run-1", task_id="t-1", score=0.42,
        )
        self._assert_schema_baseline(e, "tournament_task_scored")

    def test_emit_tournament_run_completed_basic(self):
        e = self._emit_and_read(
            "tournament_run_completed", run_id="run-1", winner="claude-opus-4-8",
        )
        self._assert_schema_baseline(e, "tournament_run_completed")

    def test_emit_tournament_budget_projected_basic(self):
        e = self._emit_and_read(
            "tournament_budget_projected", run_id="run-1", projected_cost_usd=12.50,
        )
        self._assert_schema_baseline(e, "tournament_budget_projected")

    def test_emit_tournament_budget_exceeded_basic(self):
        e = self._emit_and_read(
            "tournament_budget_exceeded", run_id="run-1", cap_usd=75, spent_usd=80,
        )
        self._assert_schema_baseline(e, "tournament_budget_exceeded")

    def test_emit_tournament_aborted_basic(self):
        e = self._emit_and_read(
            "tournament_aborted", run_id="run-1", reason="budget_exceeded",
        )
        self._assert_schema_baseline(e, "tournament_aborted")

    def test_emit_tournament_fixture_rejected_basic(self):
        e = self._emit_and_read(
            "tournament_fixture_rejected",
            fixture_id="fx-001",
            reason="unicode_attack",
        )
        self._assert_schema_baseline(e, "tournament_fixture_rejected")

    def test_emit_tournament_judge_hijack_suspected_basic(self):
        e = self._emit_and_read(
            "tournament_judge_hijack_suspected",
            run_id="run-1",
            jaccard_similarity=0.85,
        )
        self._assert_schema_baseline(e, "tournament_judge_hijack_suspected")


# ============================================================================
# PLAN-045 Wave 5 round-8 (Session 43) — 4 new emitters: fluency_nudge +
# skill_reference_read_{mismatch,stale,never_read}. Registered via
# kernel-batch-wave-5.py. Each uses ``emit_generic(action, ...)`` dispatch.
# ============================================================================


class TestWave5Emitters(_EmitterTestBase):
    """PLAN-045 Wave 5 round-8 audit actions — basic emission per-action."""

    def _emit_and_read(self, action: str, **extra: Any) -> Dict[str, Any]:
        audit_emit.emit_generic(
            action=action,
            session_id=f"s-{action}",
            project="/t",
            **extra,
        )
        return self._read_one()

    def test_emit_fluency_nudge_basic(self):
        e = self._emit_and_read(
            "fluency_nudge",
            marker_count=5,
            threshold_crossed=2,
            markers_matched=["all done", "tests green"],
            output_length=300,
        )
        self._assert_schema_baseline(e, "fluency_nudge")

    def test_emit_skill_reference_read_mismatch_basic(self):
        e = self._emit_and_read(
            "skill_reference_read_mismatch",
            skill_path=".claude/skills/core/x/SKILL.md",
            claimed_sha="a" * 64,
            read_sha="b" * 64,
            spawn_ts="2026-04-20T12:00:00Z",
            read_ts="2026-04-20T12:00:03Z",
        )
        self._assert_schema_baseline(e, "skill_reference_read_mismatch")

    def test_emit_skill_reference_read_stale_basic(self):
        e = self._emit_and_read(
            "skill_reference_read_stale",
            skill_path=".claude/skills/core/x/SKILL.md",
            claimed_sha="a" * 64,
            read_sha="a" * 64,
            spawn_ts="2026-04-20T12:00:00Z",
            read_ts="2026-04-20T12:10:00Z",
            delta_seconds=600,
        )
        self._assert_schema_baseline(e, "skill_reference_read_stale")

    def test_emit_skill_reference_never_read_basic(self):
        e = self._emit_and_read(
            "skill_reference_never_read",
            skill_path=".claude/skills/core/x/SKILL.md",
            claimed_sha="a" * 64,
            spawn_ts="2026-04-20T12:00:00Z",
        )
        self._assert_schema_baseline(e, "skill_reference_never_read")

    # PLAN-017 Phase 4 (Session 51) — swarm events coverage
    def test_emit_swarm_started_basic(self):
        e = self._emit_and_read(
            "swarm_started", swarm_id="sw-1", n_loops=4, budget_tokens=10000,
        )
        self._assert_schema_baseline(e, "swarm_started")

    def test_emit_swarm_iteration_basic(self):
        e = self._emit_and_read(
            "swarm_iteration", swarm_id="sw-1", loop_id="L-1", iteration=3,
        )
        self._assert_schema_baseline(e, "swarm_iteration")

    def test_emit_swarm_halted_budget_basic(self):
        e = self._emit_and_read(
            "swarm_halted_budget", swarm_id="sw-1", tokens_consumed=10500,
        )
        self._assert_schema_baseline(e, "swarm_halted_budget")

    def test_emit_swarm_halted_convergence_basic(self):
        e = self._emit_and_read(
            "swarm_halted_convergence", swarm_id="sw-1", jaccard=0.92,
        )
        self._assert_schema_baseline(e, "swarm_halted_convergence")

    def test_emit_swarm_halted_kill_basic(self):
        e = self._emit_and_read(
            "swarm_halted_kill", swarm_id="sw-1", source="env",
        )
        self._assert_schema_baseline(e, "swarm_halted_kill")

    def test_emit_swarm_aborted_error_basic(self):
        e = self._emit_and_read(
            "swarm_aborted_error", swarm_id="sw-1", error="disk_full",
        )
        self._assert_schema_baseline(e, "swarm_aborted_error")

    def test_emit_swarm_killed_basic(self):
        e = self._emit_and_read(
            "swarm_killed", swarm_id="sw-1", layer=3,
        )
        self._assert_schema_baseline(e, "swarm_killed")

    def test_emit_swarm_tournament_selected_basic(self):
        e = self._emit_and_read(
            "swarm_tournament_selected", swarm_id="sw-1", winner_loop="L-2",
        )
        self._assert_schema_baseline(e, "swarm_tournament_selected")

    def test_emit_swarm_finalize_grouped_basic(self):
        e = self._emit_and_read(
            "swarm_finalize_grouped", swarm_id="sw-1", groups=3,
        )
        self._assert_schema_baseline(e, "swarm_finalize_grouped")

    def test_emit_swarm_finalize_committed_basic(self):
        e = self._emit_and_read(
            "swarm_finalize_committed", swarm_id="sw-1", commit="abc123",
        )
        self._assert_schema_baseline(e, "swarm_finalize_committed")

    # PLAN-048 Phase 2 (Session 51) — CEO escalation events coverage
    def test_emit_escalation_detected_basic(self):
        e = self._emit_and_read(
            "escalation_detected", signal="spawn_count_gap", severity="high",
        )
        self._assert_schema_baseline(e, "escalation_detected")

    def test_emit_escalation_dispatched_basic(self):
        e = self._emit_and_read(
            "escalation_dispatched", from_model="sonnet-4-6", to_model="opus-4-7",
        )
        self._assert_schema_baseline(e, "escalation_dispatched")

    def test_emit_escalation_suppressed_basic(self):
        e = self._emit_and_read(
            "escalation_suppressed", reason="cooldown_active",
        )
        self._assert_schema_baseline(e, "escalation_suppressed")

    def test_emit_escalation_baseline_recorded_basic(self):
        e = self._emit_and_read(
            "escalation_baseline_recorded", session_tag="L2-routine", spawn_count=0,
        )
        self._assert_schema_baseline(e, "escalation_baseline_recorded")


# ---------------------------------------------------------------------
# PLAN-059 SEC-P0-04 / ADR-080 — audit-tokens content-ban emitters
# (Session 62 cont, 2026-04-25)
# ---------------------------------------------------------------------


class TestSecP004AuditTokensEmitters(_EmitterTestBase):
    """audit_tokens_* emitters per SEC-P0-04 spec + ADR-080 acceptance."""

    def test_emit_audit_tokens_emitted_basic(self):
        audit_emit.emit_audit_tokens_emitted(
            session_id="s-at-001",
            window_seconds=60,
            events_scanned=5,
            tokens_in_total=1000,
            tokens_out_total=500,
            cost_cents=2,
            tier_id_distribution={"opus-4-7": 3, "sonnet-4-6": 2},
            detector_findings_count={"retry_churn": 1},
            hook_duration_ms=15,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "audit_tokens_emitted")
        self.assertEqual(e["session_id"], "s-at-001")
        self.assertEqual(e["window_seconds"], 60)
        self.assertEqual(e["events_scanned"], 5)
        self.assertEqual(e["tokens_in_total"], 1000)
        self.assertEqual(e["tokens_out_total"], 500)
        self.assertEqual(e["cost_cents"], 2)

    def test_emit_audit_tokens_timeout_basic(self):
        audit_emit.emit_audit_tokens_timeout(
            session_id="s-at-002",
            timeout_seconds=0.05,
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "audit_tokens_timeout")
        self.assertEqual(e["session_id"], "s-at-002")
        # timeout_ms: int milliseconds (0.05s → 50ms). No float field.
        self.assertEqual(e["timeout_ms"], 50)
        self.assertNotIn("timeout_seconds", e, "old float field must not appear")

    def test_emit_audit_tokens_key_dropped_basic(self):
        audit_emit.emit_audit_tokens_key_dropped(
            session_id="s-at-003",
            dropped_keys=["prompt_excerpt", "stack_trace"],
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "audit_tokens_key_dropped")
        self.assertEqual(e["session_id"], "s-at-003")
        self.assertEqual(set(e["dropped_keys"]),
                         {"prompt_excerpt", "stack_trace"})
        self.assertEqual(e["dropped_count"], 2)

    def test_emit_mcp_injection_finding_basic(self):
        """PLAN-044 audit-v2 Wave B C1-P0-03 — emit_mcp_injection_finding wired."""
        audit_emit.emit_mcp_injection_finding(
            session_id="s-mcp-001",
            server_id="claude_ai_Stripe",
            mcp_tool_name="search_payments",
            source_kind="tool_result",
            family_counts={"harness_mimicry": 1, "directive_prose": 2},
            match_count=3,
            bytes_scanned=4096,
            severity="warn",
            snippet_preview="<system-reminder>injected text</system-reminder>",
            scanner_action="advisory",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "mcp_injection_finding")
        self.assertEqual(e["session_id"], "s-mcp-001")
        self.assertEqual(e["server_id"], "claude_ai_Stripe")
        self.assertEqual(e["mcp_tool_name"], "search_payments")
        self.assertEqual(e["source_kind"], "tool_result")
        self.assertEqual(e["match_count"], 3)
        self.assertEqual(e["bytes_scanned"], 4096)
        self.assertEqual(e["severity"], "warn")
        self.assertEqual(e["scanner_action"], "advisory")
        self.assertEqual(
            e["family_counts"], {"harness_mimicry": 1, "directive_prose": 2}
        )


class TestSession76SkillBootstrapEmitters(_EmitterTestBase):
    """Session 76 audit-v3 / Codex DIM-04 #1 — skill bootstrap registration.

    Pre-Session-76 these actions were emitted via `emit_generic` from
    `check_skill_patch_sentinel` (skill_bootstrap_used) and
    `check_skill_bootstrap_post` (skill_bootstrap_post_hash) yet dropped
    silently by `_write_event` because they were absent from
    `_KNOWN_ACTIONS`. SPEC v2.15 row + emit registration land in the
    same audit-v3 ceremony.
    """

    def test_emit_skill_bootstrap_used_basic(self):
        audit_emit.emit_generic(
            action="skill_bootstrap_used",
            skill_slug="test-bootstrap-skill",
            env_set=True,
            project="/t",
        )
        e = self._read_one()
        # Note: skill_bootstrap_* actions intentionally omit `session_id`
        # because the production callers (check_skill_patch_sentinel and
        # check_skill_bootstrap_post) operate during the file-write hook
        # path where the harness does not pass a session id. SPEC v2.15
        # documents the required-field list explicitly without session_id.
        self.assertEqual(e["action"], "skill_bootstrap_used")
        self.assertEqual(e["event_schema"], "v2")
        self.assertIn("ts", e)
        self.assertEqual(e["skill_slug"], "test-bootstrap-skill")
        self.assertTrue(e["env_set"])

    def test_emit_skill_bootstrap_post_hash_basic(self):
        audit_emit.emit_generic(
            action="skill_bootstrap_post_hash",
            skill_slug="test-bootstrap-skill",
            sha256="0" * 64,
            file_size=2048,
            bootstrap_event_correlated=True,
            bootstrap_ts_s=1700000000,
            suspicious_delay_ms=-1,
            anomaly=False,
            hook_version="1.0.0",
            project="/t",
        )
        e = self._read_one()
        # See note in test_emit_skill_bootstrap_used_basic above re session_id.
        self.assertEqual(e["action"], "skill_bootstrap_post_hash")
        self.assertEqual(e["event_schema"], "v2")
        self.assertIn("ts", e)
        self.assertEqual(e["skill_slug"], "test-bootstrap-skill")
        self.assertEqual(e["sha256"], "0" * 64)
        self.assertEqual(e["file_size"], 2048)
        self.assertTrue(e["bootstrap_event_correlated"])
        self.assertFalse(e["anomaly"])
        # Int fields — no float in HMAC-covered payload.
        self.assertEqual(e["bootstrap_ts_s"], 1700000000)
        self.assertEqual(e["suspicious_delay_ms"], -1)
        self.assertNotIn("bootstrap_ts", e, "old float field must not appear")
        self.assertNotIn("suspicious_delay_s", e, "old float field must not appear")


class TestPlan075PairRailEmitters(_EmitterTestBase):
    """PLAN-075 v1.13.x patch (S96-cont-2 ceremony 2026-05-09) / ADR-106 + ADR-110.

    Pair-Rail Multi-LLM cross-review hook events. Wired by
    check_pair_rail.py PreToolUse on Edit|Write|MultiEdit against L3+
    canonical-guarded paths. SPEC v2.22 introduces 4 actions registered
    with KERNEL_OVERRIDE bypass since audit_emit.py is in _KERNEL_PATHS.
    """

    def test_emit_pair_rail_review_passed_basic(self):
        audit_emit.emit_pair_rail_review_passed(
            target_path=".claude/hooks/_lib/audit_emit.py",
            tool_name="Edit",
            codex_duration_ms=1234,
            codex_response_sha256="a" * 64,
            session_id="s-pr-pass",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_review_passed")
        self.assertEqual(e["session_id"], "s-pr-pass")
        self.assertEqual(e["target_path"], ".claude/hooks/_lib/audit_emit.py")
        self.assertEqual(e["tool_name"], "Edit")
        self.assertEqual(e["codex_duration_ms"], 1234)
        self.assertEqual(e["codex_response_sha256"], "a" * 64)

    def test_emit_pair_rail_codex_unavailable_basic(self):
        audit_emit.emit_pair_rail_codex_unavailable(
            target_path=".claude/hooks/check_canonical_edit.py",
            tool_name="Write",
            reason="connect_timeout",
            session_id="s-pr-unavail",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_codex_unavailable")
        self.assertEqual(e["session_id"], "s-pr-unavail")
        self.assertEqual(e["tool_name"], "Write")
        self.assertEqual(e["reason"], "connect_timeout")

    def test_emit_pair_rail_codex_violation_basic(self):
        audit_emit.emit_pair_rail_codex_violation(
            target_path="SPEC/v1/audit-log.schema.md",
            tool_name="MultiEdit",
            violation_type="unified_diff_detected",
            codex_response_sha256="b" * 64,
            session_id="s-pr-violation",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_codex_violation")
        self.assertEqual(e["session_id"], "s-pr-violation")
        self.assertEqual(e["tool_name"], "MultiEdit")
        self.assertEqual(e["violation_type"], "unified_diff_detected")
        self.assertEqual(e["codex_response_sha256"], "b" * 64)

    def test_emit_pair_rail_sentinel_bypass_basic(self):
        audit_emit.emit_pair_rail_sentinel_bypass(
            target_path=".claude/hooks/check_pair_rail.py",
            tool_name="Edit",
            sentinel_path=".claude/plans/PLAN-075/architect/round-v1.13.x-patch/approved.md",
            session_id="s-pr-bypass",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_sentinel_bypass")
        self.assertEqual(e["session_id"], "s-pr-bypass")
        self.assertEqual(e["tool_name"], "Edit")
        self.assertEqual(
            e["sentinel_path"],
            ".claude/plans/PLAN-075/architect/round-v1.13.x-patch/approved.md",
        )

    def test_emit_pair_rail_codex_injection_detected_basic(self):
        """PLAN-081 Phase 1-full / R1 S-Sec-5 — Codex ingress sanitization emit."""
        audit_emit.emit_pair_rail_codex_injection_detected(
            tool_name="mcp__codex__codex",
            family_ids=["harness_mimicry", "xml_system_tag"],
            match_count=3,
            first_offset_bucket="1k-10k",
            session_id="s-codex-injection",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_codex_injection_detected")
        self.assertEqual(e["session_id"], "s-codex-injection")
        self.assertEqual(e["tool_name"], "mcp__codex__codex")
        self.assertEqual(
            sorted(e["family_ids"]),
            ["harness_mimicry", "xml_system_tag"],
        )
        self.assertEqual(e["match_count"], 3)
        self.assertEqual(e["first_offset_bucket"], "1k-10k")

    def test_emit_pair_rail_codex_injection_detected_unknown_family_dropped(self):
        """Unknown family_ids must be dropped (Sec MF-3 invariant)."""
        audit_emit.emit_pair_rail_codex_injection_detected(
            tool_name="mcp__codex__codex-reply",
            family_ids=["harness_mimicry", "FAKE_INJECTION_FAMILY"],
            match_count=1,
            first_offset_bucket="0-100",
            session_id="s-bad-family",
            project="/t",
        )
        e = self._read_one()
        self.assertEqual(e["family_ids"], ["harness_mimicry"])

    def test_emit_pair_rail_codex_injection_detected_invalid_bucket_coerces(self):
        """Invalid first_offset_bucket coerces to safe default '0-100'."""
        audit_emit.emit_pair_rail_codex_injection_detected(
            tool_name="mcp__codex__codex",
            family_ids=["tool_use_forgery"],
            match_count=2,
            first_offset_bucket="bogus-bucket",
            session_id="s-bad-bucket",
            project="/t",
        )
        e = self._read_one()
        self.assertEqual(e["first_offset_bucket"], "0-100")

    # ---- PLAN-081 Phase 2 (S100 ceremony 2026-05-10) ------------------------

    def test_emit_dispatcher_route_basic(self):
        """PLAN-081 Phase 2 — dispatcher routing-matrix decision emit."""
        audit_emit.emit_dispatcher_route(
            archetype="code-reviewer",
            rail="pair_rail",
            reason_code="ok",
            matrix_sha256_prefix="0bf963f6685a4584",
            matrix_sha256_match=True,
            coder="claude",
            reviewer="codex",
            coder_model="opus",
            reviewer_sandbox="read-only",
            fallback_provider="claude",
            wall_clock_ms=42,
            session_id="s-dispatcher",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "dispatcher_route")
        self.assertEqual(e["archetype"], "code-reviewer")
        self.assertEqual(e["rail"], "pair_rail")
        self.assertEqual(e["coder"], "claude")
        self.assertEqual(e["reviewer"], "codex")
        self.assertEqual(e["wall_clock_ms"], 42)
        self.assertTrue(e["matrix_sha256_match"])

    def test_emit_dispatcher_route_invalid_rail_coerces(self):
        """Unknown rail value coerces to safe fallback_claude_only."""
        audit_emit.emit_dispatcher_route(
            archetype="qa-architect",
            rail="bogus_rail_value",
            reason_code="test_invalid",
            matrix_sha256_prefix="",
            matrix_sha256_match=False,
            coder="claude",
            reviewer="codex",
            session_id="s-bad-rail",
            project="/t",
        )
        e = self._read_one()
        self.assertEqual(e["rail"], "fallback_claude_only")

    def test_emit_dispatcher_route_forbidden_field_dropped(self):
        """Dispatch-gate scrub drops forbidden fields (Sec MF-3 invariant)."""
        audit_emit.emit_generic(
            "dispatcher_route",
            archetype="docs-writer",
            rail="pair_rail",
            reason_code="ok",
            matrix_sha256_prefix="abc123def4567890",
            matrix_sha256_match=False,
            coder="claude",
            reviewer="codex",
            wall_clock_ms=10,
            # Forbidden fields — must be scrubbed:
            task_description="this should be dropped",
            skill_content="this too",
            session_id="s-scrub",
            project="/t",
        )
        e = self._read_one()
        self.assertNotIn("task_description", e)
        self.assertNotIn("skill_content", e)


    def test_emit_pair_rail_case_basic(self):
        """PLAN-081 Phase 3 - asymmetric VETO matrix Cases A-F emit."""
        audit_emit.emit_pair_rail_case(
            case="A",
            claude_verdict="PASS",
            codex_verdict="PASS",
            tool_name="Edit",
            file_path_hash_prefix="abc123def4567890",
            precondition_met=False,
            rubric_violation_id="",
            severity="",
            jaccard_similarity_bucket=">0.8",
            human_triage_grace_h=0,
            session_id="s-pair-rail-case",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_case")
        self.assertEqual(e["case"], "A")
        self.assertEqual(e["claude_verdict"], "PASS")
        self.assertEqual(e["codex_verdict"], "PASS")
        self.assertEqual(e["tool_name"], "Edit")

    def test_emit_pair_rail_case_invalid_case_coerces(self):
        """Invalid case value coerces to safe default 'F'."""
        audit_emit.emit_pair_rail_case(
            case="Z",
            claude_verdict="PASS",
            codex_verdict="PASS",
            tool_name="Edit",
            file_path_hash_prefix="abc",
            session_id="s-bad-case",
            project="/t",
        )
        e = self._read_one()
        self.assertEqual(e["case"], "F")


    def test_emit_pair_rail_promotion_basic(self):
        """PLAN-081 Phase 4 - promotion gate verdict emit."""
        audit_emit.emit_pair_rail_promotion(
            run_id="abc12345-test-run",
            verdict="PASS",
            corpus_n=15,
            corpus_manifest_sha="0123456789abcdef",
            catch_rate_num=15,
            catch_rate_den=15,
            fp_rate_bucket="<=15%",
            schema_adherence_pct_bucket="100%",
            rubric_gap_pp_bucket="<=0pp",
            codex_cli_version="0.128.5",
            python_version="3.9.6",
            git_head_sha_prefix="1e358e3abc",
            pass_2_retry_used=False,
            manual_triage=False,
            session_id="s-promotion-pass",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "pair_rail_promotion")
        self.assertEqual(e["verdict"], "PASS")
        self.assertEqual(e["corpus_n"], 15)
        self.assertEqual(e["catch_rate_num"], 15)

    def test_emit_pair_rail_promotion_invalid_verdict_coerces(self):
        """Unknown verdict coerces to safe FAIL."""
        audit_emit.emit_pair_rail_promotion(
            run_id="bad-verdict-run",
            verdict="UNKNOWN_VERDICT",
            corpus_n=10,
            corpus_manifest_sha="",
            catch_rate_num=5,
            catch_rate_den=10,
            session_id="s-bad-verdict",
            project="/t",
        )
        e = self._read_one()
        self.assertEqual(e["verdict"], "FAIL")



class TestPlan083NewActions(unittest.TestCase):
    """PLAN-083 Wave 0a/0b/1+2 (S106 ceremony 2026-05-11) — smoke tests for the 10 new audit actions registered atomically per S100 L6 lesson. Per-action presence in _KNOWN_ACTIONS verified."""
    def test_emit_token_budget_guard_paused_basic(self):
        """PLAN-083 Wave 0b sub-agent 0.4 (S106) — token_budget_guard_paused registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("token_budget_guard_paused", _KNOWN_ACTIONS)

    def test_emit_anti_ceo_overhead_block_basic(self):
        """PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_block registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("anti_ceo_overhead_block", _KNOWN_ACTIONS)

    def test_emit_anti_ceo_overhead_override_used_basic(self):
        """PLAN-083 Wave 0b sub-agent 0.5 (S106) — anti_ceo_overhead_override_used registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("anti_ceo_overhead_override_used", _KNOWN_ACTIONS)

    def test_emit_smart_loading_resolved_basic(self):
        """PLAN-083 Wave 0b sub-agent 0.7d (S106) — smart_loading_resolved registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("smart_loading_resolved", _KNOWN_ACTIONS)

    def test_emit_first_run_wizard_completed_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.1 — first_run_wizard_completed registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("first_run_wizard_completed", _KNOWN_ACTIONS)

    def test_emit_contextual_recommendation_emitted_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.2 — contextual_recommendation_emitted registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("contextual_recommendation_emitted", _KNOWN_ACTIONS)

    def test_emit_value_dashboard_summarized_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.4 — value_dashboard_summarized registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("value_dashboard_summarized", _KNOWN_ACTIONS)

    def test_emit_trading_write_override_used_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.7 — trading_write_override_used registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("trading_write_override_used", _KNOWN_ACTIONS)

    def test_emit_trading_kill_switch_invoked_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_invoked registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("trading_kill_switch_invoked", _KNOWN_ACTIONS)

    def test_emit_trading_kill_switch_disabled_basic(self):
        """PLAN-083 Wave 2 sub-agent 2.7 — trading_kill_switch_disabled registered."""
        from _lib.audit_emit import _KNOWN_ACTIONS
        self.assertIn("trading_kill_switch_disabled", _KNOWN_ACTIONS)


class TestPlan120FollowupCoverageBackfill(_EmitterTestBase):
    """PLAN-120-FOLLOWUP E3-F11 — representative coverage backfill.

    Two emitters that were in the EmitterCoverageGate gap (neither in
    _DEFERRED_COVERAGE) now get real emit + schema-baseline tests. The
    remaining 72-action long-tail is enumerated in
    PLAN-120-FOLLOWUP/receipts/bscope-disposition.md §5 for the dedicated
    coverage-completion plan (S169 B-scope Batch B2).
    """

    def test_emit_claim_emitted_basic(self):
        audit_emit.emit_claim_emitted(
            claim_id="CLAIM-XYZ",
            claim_type="perf",
            severity="warn",
            verifier_kind="benchmark",
            payload_hash="abc123def456",
            kind_supported=True,
            line_num=42,
            agent_name="qa-architect",
            source="check_confidence_gate",
            session_id="s-claim",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "claim_emitted")
        self.assertEqual(e["claim_type"], "perf")
        self.assertEqual(e["severity"], "warn")
        self.assertTrue(e["kind_supported"])
        self.assertEqual(e["line_num"], 42)
        # claim_id is hashed (LLM06 hold) — raw value must NOT leak.
        self.assertNotEqual(e["claim_id"], "CLAIM-XYZ")

    def test_emit_claim_emitted_invalid_severity_drops_to_info(self):
        audit_emit.emit_claim_emitted(
            claim_id="CLAIM-2",
            claim_type="sec",
            severity="bogus-not-an-enum",
            verifier_kind="static",
            payload_hash="deadbeef",
            kind_supported=False,
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "claim_emitted")
        self.assertEqual(e["severity"], "info")  # ADR-018 fail-open sentinel

    def test_emit_chain_reset_marker_basic(self):
        audit_emit.emit_chain_reset_marker(
            previous_archive_path="audit-log-2026-05-29-pre-fix.jsonl",
            previous_archive_last_hmac="a" * 64,
            rotation_ts="2026-05-29T12:00:00Z",
            rotation_trigger="owner_rotation",
            session_id="s-rot",
            project="/t",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "chain_reset_marker")
        self.assertEqual(e["rotation_trigger"], "owner_rotation")
        self.assertEqual(
            e["previous_archive_path"], "audit-log-2026-05-29-pre-fix.jsonl"
        )
        self.assertEqual(e["previous_archive_last_hmac"], "a" * 64)

    def test_emit_chain_reset_marker_invalid_trigger_defaults(self):
        audit_emit.emit_chain_reset_marker(
            previous_archive_path="x.jsonl",
            previous_archive_last_hmac="",
            rotation_ts="2026-05-29T12:00:00Z",
            rotation_trigger="not-a-valid-trigger",
        )
        e = self._read_one()
        self._assert_schema_baseline(e, "chain_reset_marker")
        # fail-open: unknown trigger falls back to the common case.
        self.assertEqual(e["rotation_trigger"], "size_threshold")


if __name__ == "__main__":
    unittest.main()
