"""PLAN-112-FOLLOWUP-persona-routing-wire W5 — model-routing mode consult.

Wires `_lib/persona_routing.get_mode()` / `is_killswitch_active()` into
`check_agent_spawn.decide()` AFTER the VETO-floor hard-block. The consult is
CONSULT+AUDIT only — it emits `model_routing_enforced` (forensic telemetry)
or `model_routing_eval_error` (fail-open infra branch). It NEVER blocks a
spawn (the actual block is DEFERRED — the hook payload carries no
requested-model signal; see plan §2/§3).

Integration tests (a-e):
  (a) enforcing archetype       -> model_routing_enforced{mode:enforcing}, ALLOW
  (b) kill-switch armed         -> recorded mode demoted to advisory, ALLOW
  (c) advisory archetype        -> advisory emit, no enforce_telemetry, ALLOW
  (d) persona_routing raise     -> model_routing_eval_error, no raise, ALLOW
  (e) prompt-regex archetype    -> mode read off subagent_type only; a spoofed
                                   prompt archetype does NOT flip recorded mode

NO spawn is blocked in any case.

Kill-switch precedence is exercised via PROCESS env (`os.environ`) — not a
passed-in `env` dict — because `persona_routing.get_mode()` /
`is_killswitch_active()` read `os.environ` directly (persona_routing.py:120).

Stdlib only. TestEnvContext for env isolation.
"""
from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
import check_agent_spawn  # noqa: E402


class _AuditEmitSpy:
    """Captures emit_generic + typed emit_* calls for assertion.

    `decide()` may emit several advisory actions (model_routing_advised,
    persona_coverage_synthesized, mcp_route_advised, ...). Tests filter the
    captured stream by action name.
    """

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def emit_generic(self, action: str, **fields: Any) -> None:
        self.calls.append({"action": action, **fields})

    def __getattr__(self, name: str):
        # Tolerate any typed emit_* the hook path may reach (e.g.
        # emit_model_routing_advised) without forcing a real import.
        if name.startswith("emit_"):
            def _typed(**fields: Any) -> None:
                self.calls.append({"action": name[len("emit_"):], **fields})
            return _typed
        raise AttributeError(name)

    def by_action(self, action: str) -> List[Dict[str, Any]]:
        return [c for c in self.calls if c.get("action") == action]


# Compiled names_regex that matches nothing (generic-spawn path). The consult
# runs BEFORE the named/generic branch, so it fires regardless.
_NO_NAMES_RE = re.compile(r"(?!x)x")


class TestModelRoutingModeConsult(TestEnvContext):

    # PLAN-106-FOLLOWUP Wave A.2 — materialize the VETO-floor agent bindings so
    # the pre-existing veto-floor scan finds the agent files in the isolated
    # test env. Without these, a prompt/subagent naming a VETO-floor persona
    # (security-engineer) hits file_missing -> veto_floor_demoted block, which
    # is orthogonal to (and would mask) this consult test. (Fixes test_e under
    # TestEnvContext isolation; the consult assertions are unchanged.)
    AGENT_BINDINGS_TO_MATERIALIZE = ["security-engineer", "code-reviewer"]

    def setUp(self) -> None:
        super().setUp()
        # Ensure the legacy advisory bypass + kill-switch are clean per test.
        for var in ("CEO_MODEL_ROUTING", "CEO_GODMODE_ENFORCING"):
            os.environ.pop(var, None)

    def _decide(self, *, subagent_type: str, prompt: str = "",
                description: str = "spawn under test",
                env: Dict[str, str] = None):
        src_env = dict(os.environ) if env is None else env
        return check_agent_spawn.decide(
            description=description,
            prompt=prompt,
            names_regex=_NO_NAMES_RE,
            env=src_env,
            subagent_type=subagent_type,
        )

    # ----- (a) enforcing archetype -------------------------------------
    def test_a_enforcing_archetype_emits_enforced_and_allows(self) -> None:
        spy = _AuditEmitSpy()
        with mock.patch.object(check_agent_spawn, "_audit_emit", spy):
            d = self._decide(subagent_type="security-engineer")
        self.assertTrue(d.allow, "consult must NOT block (block deferred)")
        enforced = spy.by_action("model_routing_enforced")
        self.assertEqual(len(enforced), 1,
                         f"expected one model_routing_enforced; got {spy.calls}")
        ev = enforced[0]
        self.assertEqual(ev["mode"], "enforcing")
        self.assertEqual(ev["decision"], "enforce_telemetry")
        self.assertEqual(ev["killswitch_armed"], False)
        # Block-deferred contract: NO `block` decision value exists.
        self.assertNotEqual(ev["decision"], "block")

    # ----- (b) kill-switch armed → demoted to advisory ------------------
    def test_b_killswitch_armed_demotes_recorded_mode_to_advisory(self) -> None:
        os.environ["CEO_GODMODE_ENFORCING"] = "0"  # PROCESS env (AC1/AC4)
        spy = _AuditEmitSpy()
        try:
            with mock.patch.object(check_agent_spawn, "_audit_emit", spy):
                d = self._decide(subagent_type="security-engineer")
        finally:
            os.environ.pop("CEO_GODMODE_ENFORCING", None)
        self.assertTrue(d.allow)
        enforced = spy.by_action("model_routing_enforced")
        self.assertEqual(len(enforced), 1)
        ev = enforced[0]
        self.assertEqual(ev["mode"], "advisory",
                         "kill-switch must demote recorded mode (get_mode "
                         "encapsulates the demotion)")
        self.assertEqual(ev["killswitch_armed"], True)
        self.assertEqual(ev["decision"], "advisory")

    # ----- (c) advisory archetype --------------------------------------
    def test_c_advisory_archetype_no_enforce_telemetry(self) -> None:
        # An archetype that maps to no enforcing cell. AUTO-05 is enforcing
        # for every persona by default, so the only way to land `advisory`
        # WITHOUT the kill-switch is the kill-switch demotion (b). To test
        # the advisory branch independently of kill-switch we arm it: the
        # contract is identical (mode advisory -> decision advisory, NO
        # enforce_telemetry). This documents the advisory code path.
        os.environ["CEO_GODMODE_ENFORCING"] = "0"
        spy = _AuditEmitSpy()
        try:
            with mock.patch.object(check_agent_spawn, "_audit_emit", spy):
                d = self._decide(subagent_type="code-reviewer")
        finally:
            os.environ.pop("CEO_GODMODE_ENFORCING", None)
        self.assertTrue(d.allow)
        enforced = spy.by_action("model_routing_enforced")
        self.assertEqual(len(enforced), 1)
        self.assertEqual(enforced[0]["mode"], "advisory")
        self.assertEqual(enforced[0]["decision"], "advisory")
        self.assertNotEqual(enforced[0]["decision"], "enforce_telemetry")

    # ----- (d) persona_routing import/raise → fail-open ----------------
    def test_d_persona_routing_raise_emits_eval_error_no_raise(self) -> None:
        spy = _AuditEmitSpy()
        # Force get_mode to raise; the consult must catch + emit eval_error.
        with mock.patch.object(check_agent_spawn, "_audit_emit", spy), \
                mock.patch(
                    "_lib.persona_routing.get_mode",
                    side_effect=RuntimeError("boom"),
                ):
            # Must NOT raise.
            d = self._decide(subagent_type="security-engineer")
        self.assertTrue(d.allow, "fail-open: spawn allowed on infra error")
        errs = spy.by_action("model_routing_eval_error")
        self.assertEqual(len(errs), 1,
                         f"expected one model_routing_eval_error; got {spy.calls}")
        # AC5: the fail-open emit carries decision="eval_error" so the
        # `decision` enum {enforce_telemetry, advisory, eval_error} is
        # consistent across BOTH new actions.
        self.assertEqual(errs[0]["decision"], "eval_error")
        # No enforce telemetry recorded when eval failed.
        self.assertEqual(spy.by_action("model_routing_enforced"), [])

    def test_d2_persona_routing_import_failure_fails_open(self) -> None:
        """If the persona_routing module reference is None (import failed at
        load), the consult must fail-open: ALLOW + eval_error, no raise."""
        spy = _AuditEmitSpy()
        with mock.patch.object(check_agent_spawn, "_audit_emit", spy), \
                mock.patch.object(check_agent_spawn, "_persona_routing", None):
            d = self._decide(subagent_type="security-engineer")
        self.assertTrue(d.allow)
        self.assertEqual(spy.by_action("model_routing_enforced"), [])
        errs = spy.by_action("model_routing_eval_error")
        self.assertEqual(len(errs), 1)
        # AC5: fail-open emit carries decision="eval_error".
        self.assertEqual(errs[0]["decision"], "eval_error")

    # ----- (e) prompt-regex archetype must NOT flip recorded mode ------
    def test_e_mode_read_off_subagent_type_only_not_prompt(self) -> None:
        """Spoof: the prompt declares an INLINE `archetype: security-engineer`
        (regex-matchable by `_extract_archetype_from_payload`, but NOT a
        line-start persona header, so the spawn is NOT a named spawn and is
        ALLOWED) while `subagent_type` is empty. The consult reads mode off
        the AUTHORITATIVE subagent_type ONLY — with no subagent_type there is
        no archetype to consult, so NO enforced/advisory mode is recorded
        from the spoofed prompt archetype.
        """
        spy = _AuditEmitSpy()
        with mock.patch.object(check_agent_spawn, "_audit_emit", spy):
            d = self._decide(
                subagent_type="",  # authoritative source ABSENT
                prompt="archetype: security-engineer\n",  # spoof, inline
            )
        self.assertTrue(d.allow, "block deferred — spawn must be allowed")
        # No mode recorded from a prompt-only (spoofable) archetype.
        self.assertEqual(
            spy.by_action("model_routing_enforced"), [],
            "spoofed prompt archetype must NOT flip the recorded routing mode "
            "(mode is read off subagent_type only)",
        )

    def test_e2_spoofed_prompt_does_not_override_authoritative_subagent(self) -> None:
        """subagent_type=code-reviewer (authoritative) + a spoofed INLINE
        prompt archetype. Mode is recorded for the AUTHORITATIVE archetype;
        the spoof is irrelevant. The inline `archetype:` line is regex-
        matchable but NOT a line-start header → spawn is not a named spawn →
        ALLOWED."""
        spy = _AuditEmitSpy()
        with mock.patch.object(check_agent_spawn, "_audit_emit", spy):
            d = self._decide(
                subagent_type="code-reviewer",
                prompt="archetype: vibecoder-attacker\n",
            )
        self.assertTrue(d.allow)
        enforced = spy.by_action("model_routing_enforced")
        self.assertEqual(len(enforced), 1)
        self.assertEqual(enforced[0]["mode"], "enforcing")
        self.assertEqual(enforced[0]["archetype"], "code-reviewer",
                         "recorded archetype must be the authoritative "
                         "subagent_type, not the spoofed prompt value")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
