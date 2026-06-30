"""PLAN-088 canonical-13 god-mode auto-activation typed-emitter tests.

15 test cases per qa-architect verdict ACCEPT-WITH-FIXES (S114 dispatch):
covers the 11 net-new emitters + 1 new wrapper for the pre-existing
`mcp_route_advised` stub + rate-cap (M-12) + payload-cap (M-12 utf-8 safe)
+ emit_generic gate (Sec MF-3 defense-in-depth) + null-ATLAS invariants.

Closes PLAN-088 W1.1 / W1.2 / W1.3 / W1.4 / W2.1 / W3.1 / W3.2 / W4.1 / W4.2
test-surface obligations.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class _Plan088EmitterBase(TestEnvContext):
    """Base: fresh audit dir + rate-state reset per test (P0-2 fix)."""

    def setUp(self) -> None:
        super().setUp()
        # Reset PLAN-088 rate-cap module-level singleton per qa-architect P0-2
        audit_emit._plan088_rate_state_clear()

    def _read_events(self) -> List[Dict[str, Any]]:
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
        events = self._read_events()
        self.assertEqual(len(events), 1, f"expected 1 event, got {len(events)}: {events!r}")
        return events[0]

    def _assert_baseline(self, e: Dict[str, Any], action: str) -> None:
        self.assertEqual(e["action"], action)
        self.assertEqual(e["event_schema"], "v2")
        self.assertIn("ts", e)
        for k in ("tokens_in", "tokens_out", "tokens_total"):
            self.assertIn(k, e)


class TestPlan088Canonical13Emitters(_Plan088EmitterBase):
    """Cases 1-7: typed emitters fire + schema baselines + ATLAS bindings."""

    def test_cache_discipline_alerted_basic(self):
        """Case 1: cache_discipline_alerted fires + null ATLAS (telemetry-only)."""
        audit_emit.emit_cache_discipline_alerted(
            session_id="s1",
            hit_rate_basis_points=650,
            floor_basis_points=700,
            session_count_24h=12,
            below_floor=True,
            opted_out=False,
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "cache_discipline_alerted")
        self.assertEqual(e["hit_rate_basis_points"], 650)
        self.assertEqual(e["floor_basis_points"], 700)
        self.assertTrue(e["below_floor"])
        # null-ATLAS action: no atlas_technique key in persisted event
        self.assertNotIn("atlas_technique", e)

    def test_first_run_wizard_dispatched_basic(self):
        """Case 2: first_run_wizard_dispatched fires + null ATLAS (UX trigger)."""
        audit_emit.emit_first_run_wizard_dispatched(
            session_id="s2",
            trigger_source="session_start",
            wizard_phase="dispatched",
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "first_run_wizard_dispatched")
        self.assertEqual(e["trigger_source"], "session_start")
        self.assertNotIn("atlas_technique", e)

    def test_subagent_findings_partial_drop_atlas_bound(self):
        """Case 3: subagent_findings_partial_drop carries AML.T0048."""
        audit_emit.emit_subagent_findings_partial_drop(
            session_id="s3",
            findings_total=10,
            findings_dropped=3,
            drop_reason="context_window_cut",
            archetype="security-engineer",
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "subagent_findings_partial_drop")
        self.assertEqual(e["atlas_technique"], "AML.T0048")
        self.assertEqual(e["findings_dropped"], 3)

    def test_anthropic_429_observed_atlas_bound(self):
        """Case 4: anthropic_429_observed carries AML.T0029."""
        audit_emit.emit_anthropic_429_observed(
            session_id="s4",
            retry_after_ms=5000,
            endpoint_class="/v1/messages",
            consecutive_count=2,
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "anthropic_429_observed")
        self.assertEqual(e["atlas_technique"], "AML.T0029")
        self.assertEqual(e["retry_after_ms"], 5000)

    def test_codex_invoke_dispatched_atlas_bound(self):
        """Case 5: codex_invoke_dispatched carries AML.T0050 (dual-rail)."""
        audit_emit.emit_codex_invoke_dispatched(
            session_id="s5",
            invocation_class="pair_rail",
            thread_id_prefix="019e1d22",
            redacted_outgoing=True,
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "codex_invoke_dispatched")
        self.assertEqual(e["atlas_technique"], "AML.T0050")
        self.assertTrue(e["redacted_outgoing"])

    def test_tier_policy_misrouting_advised_atlas_bound(self):
        """Case 6: tier_policy_misrouting_advised carries AML.T0048."""
        audit_emit.emit_tier_policy_misrouting_advised(
            session_id="s6",
            empty_model_rate_basis_points=820,
            window_hours=24,
            top_gap_archetype="security-engineer",
            above_threshold=True,
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "tier_policy_misrouting_advised")
        self.assertEqual(e["atlas_technique"], "AML.T0048")
        self.assertTrue(e["above_threshold"])

    def test_pair_rail_phase_advanced_atlas_bound(self):
        """Case 7: pair_rail_phase_advanced carries AML.T0050."""
        audit_emit.emit_pair_rail_phase_advanced(
            session_id="s7",
            from_phase="SHADOW",
            to_phase="DRY_RUN",
            samples_observed=105,
            signal_source="env-var",
            time_elapsed_seconds=604800,
            project="/t",
        )
        e = self._read_one()
        self._assert_baseline(e, "pair_rail_phase_advanced")
        self.assertEqual(e["atlas_technique"], "AML.T0050")
        self.assertEqual(e["from_phase"], "SHADOW")
        self.assertEqual(e["to_phase"], "DRY_RUN")


class TestPlan088RateCap(_Plan088EmitterBase):
    """Cases 8-10: M-12 rate-cap 100/min/action + drop counter + window reset."""

    def test_rate_cap_blocks_at_101st_event(self):
        """Case 8: 100 events admit, 101st dropped (sliding 60s window)."""
        for _ in range(100):
            self.assertTrue(audit_emit._plan088_rate_admit("cache_discipline_alerted"))
        # 101st fails
        self.assertFalse(audit_emit._plan088_rate_admit("cache_discipline_alerted"))

    def test_rate_cap_drop_counter_does_not_re_emit(self):
        """Case 9: dropped emits do NOT re-fire write_event (anti-recursive)."""
        # Saturate cap
        for _ in range(100):
            audit_emit.emit_cache_discipline_alerted(session_id="s", project="/t")
        events_before = len(self._read_events())
        # 101st emit returns silently (no write_event, no breadcrumb-emit recursion)
        audit_emit.emit_cache_discipline_alerted(session_id="s", project="/t")
        events_after = len(self._read_events())
        self.assertEqual(events_before, events_after,
                         "101st emit must NOT increment event count (M-12 anti-flood)")
        self.assertEqual(events_before, 100)

    def test_rate_cap_window_resets_after_60s(self):
        """Case 10: injectable clock advance > 60s resets cap."""
        # Use injectable _clock to fast-forward time without time.sleep
        t = [1000.0]
        clock = lambda: t[0]
        # Saturate cap at t=1000
        for _ in range(100):
            self.assertTrue(audit_emit._plan088_rate_admit("test_action", _clock=clock))
        self.assertFalse(audit_emit._plan088_rate_admit("test_action", _clock=clock))
        # Advance clock 61s
        t[0] += 61.0
        # 101st now admits because window rolled over
        self.assertTrue(audit_emit._plan088_rate_admit("test_action", _clock=clock))


class TestPlan088PayloadCap(_Plan088EmitterBase):
    """Cases 11-12: M-12 payload-cap utf-8 mid-codepoint safe."""

    def test_payload_cap_truncates_at_4096_bytes_ascii(self):
        """Case 11: 5000-byte ASCII string truncated to ≤4096 bytes."""
        big = "a" * 5000
        result = audit_emit._plan088_payload_cap(big)
        self.assertLessEqual(len(result.encode("utf-8")), 4096)

    def test_payload_cap_non_ascii_no_mid_codepoint_cut(self):
        """Case 12: 4097-byte multibyte input cuts on valid utf-8 boundary."""
        # 'á' is 2 bytes in utf-8. Construct: 4097 = 2046 'á' (4092 bytes) + 5 'a' bytes
        # Actually let's do: 2049 'á' = 4098 bytes (just over cap)
        s = "á" * 2049  # 4098 bytes
        result = audit_emit._plan088_payload_cap(s)
        encoded = result.encode("utf-8")
        # Must be <= 4096 bytes (strict; no replacement-char overflow)
        self.assertLessEqual(len(encoded), 4096,
                             f"truncation must stay within 4096 bytes; got {len(encoded)}")
        # No replacement character at the boundary
        self.assertNotIn("�", result, "no replacement character at codepoint boundary")
        # All decoded codepoints intact
        self.assertEqual(result, "á" * (len(encoded) // 2))


class TestPlan088EmitGenericDispatchGate(_Plan088EmitterBase):
    """Case 13: emit_generic dispatch gate drops forbidden fields."""

    def test_emit_generic_subagent_findings_partial_drop_drops_forbidden(self):
        """Case 13: emit_generic call with forbidden field is scrubbed (P0-3)."""
        audit_emit.emit_generic(
            "subagent_findings_partial_drop",
            session_id="s",
            project="/t",
            findings_total=5,
            findings_dropped=1,
            archetype="qa-architect",
            raw_prompt="SECRET PROMPT CONTENT THAT SHOULD NEVER PERSIST",
            atlas_technique="AML.T0048",
        )
        e = self._read_one()
        self._assert_baseline(e, "subagent_findings_partial_drop")
        # Forbidden field stripped
        self.assertNotIn("raw_prompt", e)
        # Allowed fields persisted
        self.assertEqual(e["findings_total"], 5)
        self.assertEqual(e["atlas_technique"], "AML.T0048")


class TestPlan088NullAtlasNoTechniqueField(_Plan088EmitterBase):
    """Case 14: null-ATLAS canonical-13 actions emit WITHOUT atlas_technique field."""

    def test_null_atlas_actions_omit_atlas_technique(self):
        """For 6 canonical-13 actions with atlas_technique=null per W0 table."""
        null_atlas_emits = [
            ("cache_discipline_alerted", audit_emit.emit_cache_discipline_alerted),
            ("first_run_wizard_dispatched", audit_emit.emit_first_run_wizard_dispatched),
            ("estimate_calibrator_pipeline_run",
                audit_emit.emit_estimate_calibrator_pipeline_run),
            ("git_index_lock_retry", audit_emit.emit_git_index_lock_retry),
            ("cookbook_pattern_advised", audit_emit.emit_cookbook_pattern_advised),
            ("batch_dispatched", audit_emit.emit_batch_dispatched),
        ]
        for action, emit_fn in null_atlas_emits:
            emit_fn(session_id="s", project="/t")
        events = self._read_events()
        self.assertEqual(len(events), 6)
        for e in events:
            self.assertNotIn("atlas_technique", e,
                             f"null-ATLAS action {e['action']} must not carry atlas_technique key")


class TestPlan088CanonicalRegistrySetMembership(_Plan088EmitterBase):
    """Case 15: all 13 canonical-13 actions registered in _KNOWN_ACTIONS."""

    def test_all_canonical13_registered_in_known_actions(self):
        canonical_13 = {
            "cache_discipline_alerted",
            "first_run_wizard_dispatched",
            "estimate_calibrator_pipeline_run",
            "subagent_findings_partial_drop",
            "anthropic_429_observed",
            "git_index_lock_retry",
            "codex_invoke_dispatched",
            "tier_policy_misrouting_advised",
            "model_routing_advised",
            "mcp_route_advised",
            "cookbook_pattern_advised",
            "pair_rail_phase_advanced",
            "batch_dispatched",
        }
        missing = canonical_13 - audit_emit._KNOWN_ACTIONS
        self.assertEqual(missing, set(),
                         f"canonical-13 missing from _KNOWN_ACTIONS: {missing}")

    def test_atlas_registry_has_6_canonical13_bindings(self):
        """6 of 13 canonical actions have non-null ATLAS mapping."""
        expected_atlas = {
            "subagent_findings_partial_drop": "AML.T0048",
            "anthropic_429_observed": "AML.T0029",
            "codex_invoke_dispatched": "AML.T0050",
            "tier_policy_misrouting_advised": "AML.T0048",
            "mcp_route_advised": "AML.T0050",
            "pair_rail_phase_advanced": "AML.T0050",
        }
        for action, technique in expected_atlas.items():
            self.assertEqual(audit_emit._ATLAS_REGISTRY.get(action), technique,
                             f"{action}: expected ATLAS={technique}, got "
                             f"{audit_emit._ATLAS_REGISTRY.get(action)}")


if __name__ == "__main__":
    unittest.main()
