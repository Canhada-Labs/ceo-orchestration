"""PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (F-7.9) — positive-proof
egress telemetry tests.

Covers:
  AC3 — every Codex egress callsite emits its mapped action (source + AST).
  AC4 — redact_outgoing_with_findings()[0] == redact_outgoing() byte-for-byte
        (clean + secret-laden); redact_with_findings()[0] == redact().
  AC5 — fail-OPEN: the emit is wrapped in try/except; the redact is NEVER in
        the same try (so a redactor failure stays fail-CLOSED).
  AC6 — pair_rail_outgoing_redaction_applied allowlist is content-field-free;
        _KNOWN_ACTIONS count stays 258.
  AC8 — the dispatch-gate scrub accepts match_count=0 (empty-findings proof).
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS = _REPO_ROOT / ".claude" / "scripts"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))
if str(_HOOKS / "_lib") not in sys.path:
    sys.path.insert(0, str(_HOOKS / "_lib"))

_SECRET = "AWS key: AKIAIOSFODNN7EXAMPLE inline"
_CLEAN = "just a plain code review prompt with no secrets at all\n" * 3


class TestByteIdentity(unittest.TestCase):
    """AC4 — the findings-capturing variants share the single-pass scan path."""

    def test_outgoing_variant_byte_identical(self):
        from _lib import codex_egress_redact as R
        for text in (_CLEAN, _SECRET, "", "x"):
            self.assertEqual(
                R.redact_outgoing_with_findings(text)[0],
                R.redact_outgoing(text),
                f"redact_outgoing_with_findings text diverges for {text!r}",
            )

    def test_inbound_variant_byte_identical(self):
        from _lib import codex_egress_redact as R
        for text in (_CLEAN, _SECRET, "", "x"):
            self.assertEqual(
                R.redact_with_findings(text)[0],
                R.redact(text),
                f"redact_with_findings text diverges for {text!r}",
            )

    def test_secret_input_produces_findings(self):
        from _lib import codex_egress_redact as R
        _txt, findings = R.redact_outgoing_with_findings(_SECRET)
        self.assertTrue(findings, "secret-laden input must yield >=1 finding")
        # and the empty case yields zero (positive proof still emits match_count=0)
        _t2, f2 = R.redact_outgoing_with_findings(_CLEAN)
        self.assertEqual(len(f2), 0, "clean input yields 0 findings (empty case)")


class TestAllowlistAndContract(unittest.TestCase):
    """AC6 / AC8 — content-field-free allowlist; empty-findings accepted."""

    def test_allowlist_excludes_content_fields(self):
        import audit_emit
        al = audit_emit._PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST
        for forbidden in ("text", "prompt", "match_value", "rationale", "patch"):
            self.assertNotIn(forbidden, al, f"{forbidden} must NOT be in the allowlist")
        for needed in ("match_count", "bytes_scanned", "callsite", "signal", "hmac"):
            self.assertIn(needed, al)

    def test_known_actions_count_unchanged(self):
        import audit_emit
        # Baseline 258 (S161 pair_rail_outgoing_redaction_applied) +2 PLAN-113
        # Phase B WIRE-DEADMOD actions (spec_context_sanitized +
        # spawn_confidence_advisory) = 260, +1 PLAN-116 (S172)
        # tier_policy_loader_fallback_observed = 261, +1 PLAN-117 WS-A (S176)
        # credential_override_late_set_ignored = 262, +1 PLAN-118 AC-B5 (S179)
        # audit_producer_path_pollution_detected = 263. +1 PLAN-125 WS-1
        # (kooky-harvest) tool_call_lifecycle_recorded = 270 (the 263→269 gap
        # is from intervening plans absorbed into the api-contract baseline).
        # +1 PLAN-124 WS-1 (ECC value-harvest) git_hook_bypass_blocked = 271.
        # +2 PLAN-128 §7 (S217) verify_after_edit_finding + adequacy_gate_flag = 273.
        # +19 PLAN-133 (Goose-harvest SOTA evolution) net-new closed-enum actions = 292.
        # +1 PLAN-135 W1 S3 settings_tamper_detected (/ceo-boot tamper tripwires) = 293.
        # +6 PLAN-135 W2 (config_change_observed + config_change_forbidden_key [H2]
        #    + compaction_continuity_snapshot + compaction_context_reinjected [H1]
        #    + bash_input_rewritten [H5/ADR-154]
        #    + subagent_lifecycle_observed [H3]) = 299.
        # +3 PLAN-135 ARC W5 (admin_key_lifecycle_event [o9] + statusline_sidecar_write
        #    [o4] + model_refusal_observed [o7], all trusted-producer emit_generic
        #    passthrough) = 302. CONSOLIDATION: this is the FINAL arc-consolidated
        #    count, re-derived vs the final arc audit_emit.py (staged/w5/actions-added.md).
        # +1 PLAN-153 Wave E / ADR-159 (spawn_prompt_defense_gate) = 303.
        # +11 PLAN-154 (Gated Learning Loop / ADR-160, SENT-F ceremony) net-new
        #    metadata-only actions = 314: lesson_candidate_written +
        #    lesson_approved + lesson_quarantined + lesson_expired +
        #    lesson_integrity_flag + lesson_boot_render_dropped +
        #    learning_rail_disabled + fact_gate_activation_changed +
        #    advisory_dampened + distiller_run_completed + lesson_evolve_run.
        #    All route through dedicated Sec MF-3 dispatch branches +
        #    per-action allowlists (_LEARNING_ENVELOPE family), NEVER
        #    _EMIT_GENERIC_PASSTHROUGH. This telemetry test is unguarded
        #    (hooks/tests/) and rides the SENT-F commit WITH audit_emit.py so
        #    the egress-pin does not red the landing (MANIFEST-A open issue #1).
        self.assertEqual(len(audit_emit._KNOWN_ACTIONS), 316)
        self.assertIn("pair_rail_outgoing_redaction_applied", audit_emit._KNOWN_ACTIONS)

    def test_dispatch_scrub_accepts_empty_findings(self):
        import audit_emit
        for action, al in (
            ("pair_rail_outgoing_redaction_applied",
             audit_emit._PAIR_RAIL_OUTGOING_REDACTION_APPLIED_ALLOWLIST),
            ("codex_egress_redacted", audit_emit._CODEX_EGRESS_REDACTED_ALLOWLIST),
        ):
            ev = {"action": action, "match_count": 0, "callsite": "x", "signal": "outbound"}
            scrubbed, dropped = audit_emit._scrub_ceo_boot_event(ev, al)
            self.assertEqual(scrubbed.get("match_count"), 0,
                             "match_count=0 (empty-findings positive proof) must survive")
            self.assertNotIn("match_count", dropped)

    def test_typed_helper_exists(self):
        import audit_emit
        self.assertTrue(hasattr(audit_emit, "emit_pair_rail_outgoing_redaction_applied"))


def _tries_in(path: Path):
    """Yield (call_attr_names_in_body, handler_is_open, handler_raises) per Try."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        names = set()
        for n in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
                names.add(n.func.attr)
        is_open = any(
            (h.type is None) or (isinstance(h.type, ast.Name) and h.type.id == "Exception")
            for h in node.handlers
        )
        raises = any(
            isinstance(n, ast.Raise)
            for h in node.handlers for n in ast.walk(ast.Module(body=h.body, type_ignores=[]))
        )
        out.append((names, is_open, raises))
    return out


class TestFailOpenStructure(unittest.TestCase):
    """AC5 — the emit is wrapped fail-OPEN; the redact is never in that try."""

    EMITS = ("emit_pair_rail_outgoing_redaction_applied", "emit_codex_egress_redacted")
    REDACTS = ("redact_outgoing_with_findings", "redact_with_findings")

    def _assert_file(self, path: Path):
        tries = _tries_in(path)
        # every emit call lives in a try whose handler catches Exception (fail-OPEN)
        emit_tries = [t for t in tries if t[0] & set(self.EMITS)]
        self.assertTrue(emit_tries, f"{path.name}: no emit found inside a try (fail-OPEN)")
        for names, is_open, _raises in emit_tries:
            self.assertTrue(is_open, f"{path.name}: emit try is not fail-OPEN (except Exception): {names}")
            # the SAME try must NOT also wrap a redact_* call (AC5 separation)
            self.assertFalse(
                names & set(self.REDACTS),
                f"{path.name}: a single try wraps BOTH emit and redact — "
                f"violates 'wraps ONLY the emit' (AC5)",
            )

    def test_codex_invoke_fail_open(self):
        self._assert_file(_SCRIPTS / "codex_invoke.py")

    def test_check_pair_rail_fail_open(self):
        self._assert_file(_HOOKS / "check_pair_rail.py")

    def test_check_pair_rail_redact_stays_fail_closed(self):
        """The redact in check_pair_rail must be in a try that RAISES (fail-CLOSED)."""
        tries = _tries_in(_HOOKS / "check_pair_rail.py")
        redact_tries = [t for t in tries if t[0] & set(self.REDACTS)]
        self.assertTrue(redact_tries, "check_pair_rail: redact call not found in a try")
        self.assertTrue(
            any(raises for (_n, _o, raises) in redact_tries),
            "check_pair_rail: redact try must fail-CLOSED (raise CodexUnavailable)",
        )


class TestCallsiteEmitCoverage(unittest.TestCase):
    """AC3 — each of the 3 egress callsites emits its mapped action."""

    def test_codex_invoke_emits_both(self):
        src = (_SCRIPTS / "codex_invoke.py").read_text(encoding="utf-8")
        self.assertIn("emit_pair_rail_outgoing_redaction_applied", src)
        self.assertIn("emit_codex_egress_redacted", src)
        # PLAN-142: callsite labels are now function-stable (not line numbers,
        # which drift on every edit). Outbound + inbound both present.
        self.assertIn("codex_invoke.py:invoke_codex:outbound", src)
        self.assertIn("codex_invoke.py:invoke_codex:inbound", src)

    def test_check_pair_rail_emits_outbound(self):
        src = (_HOOKS / "check_pair_rail.py").read_text(encoding="utf-8")
        self.assertIn("emit_pair_rail_outgoing_redaction_applied", src)
        # PLAN-142: function-stable callsite label.
        self.assertIn("check_pair_rail.py:_invoke_codex_review", src)

    def test_one_emit_per_findings_callsite(self):
        """A future 4th egress site that captures findings without an emit fails CI."""
        for path in (_SCRIPTS / "codex_invoke.py", _HOOKS / "check_pair_rail.py"):
            src = path.read_text(encoding="utf-8")
            n_capture = src.count("redact_outgoing_with_findings(") + src.count("redact_with_findings(")
            n_emit = (src.count("emit_pair_rail_outgoing_redaction_applied(")
                      + src.count("emit_codex_egress_redacted("))
            # codex_egress_redact.py defines the funcs; here we only count call
            # sites in the two egress modules. Each capturing call pairs with
            # exactly one emit.
            self.assertEqual(
                n_capture, n_emit,
                f"{path.name}: {n_capture} findings-capturing redaction call(s) but "
                f"{n_emit} emit(s) — every egress callsite must emit exactly once",
            )


if __name__ == "__main__":
    unittest.main()
