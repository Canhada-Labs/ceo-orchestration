"""Tests for `audit-query.py critical` sub-command (PLAN-113 Phase B Wave W1).

Covers the audit-reader-coverage gap: 38 critical-security actions are
emitted by hooks but had NO reader handler. cmd_critical surfaces them with
count + first/last ts + safe summary; zero-occurrence actions are listed with
count=0 so a missing-but-expected critical event is visible.

Asserts: (a) present actions show correct counts + last-seen, (b) absent
critical actions appear with count=0, (c) --action filter works + rejects
unknown, (d) --json shape, plus registry completeness + safe-summary scoping.

Uses the same file-load test harness style as the existing audit-query tests
(test_audit_query_claims.py / test_audit_query_by_domain.py).
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any, Dict, List

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_AQ_PATH = _SCRIPTS_DIR / "audit-query.py"
_spec = importlib.util.spec_from_file_location("audit_query", _AQ_PATH)
_aq = importlib.util.module_from_spec(_spec)
sys.modules["audit_query"] = _aq
_spec.loader.exec_module(_aq)


# The 38 critical actions PLAN-113 W1 must surface (from the task spec).
_EXPECTED_38 = frozenset({
    "anti_ceo_overhead_override_used", "audit_spool_tamper_detected",
    "bash_canonical_bypass_invoked", "confidence_gate_blocked",
    "credential_blocked_due_to_age", "credential_emergency_override_used",
    "federation_autonomous_call_blocked", "federation_cert_revoked",
    "federation_event_action_blocked", "federation_hmac_secret_rotated",
    "federation_key_floor_rejected", "federation_lan_bind_denied",
    "federation_peer_revoked_remote", "federation_scope_denied",
    "federation_spki_fingerprint_mismatch", "federation_tamper_detected",
    "federation_write_attempt_blocked", "federation_write_endpoint_denied",
    "gpg_signed", "gpg_verified", "kernel_extension_landed",
    "kill_switch_invoked", "live_adapter_blocked",
    "mcp_bearer_replay_rejected", "mcp_cross_tenant_denied",
    "mcp_non_loopback_rejected", "pair_rail_codex_injection_detected",
    "pair_rail_outgoing_redaction_applied", "phase_c_enforcing_flipped",
    "sentinel_signer_expiry_warned", "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed", "sentinel_signer_revoked",
    "sentinel_signer_rotated", "swarm_layer_3_4_blocked",
    "trading_kill_switch_disabled", "trading_kill_switch_invoked",
    "trading_write_override_used",
})


def _args(**overrides) -> types.SimpleNamespace:
    args = types.SimpleNamespace(action=None)
    for k, v in overrides.items():
        setattr(args, k, v)
    return args


def _make_entries() -> List[Dict[str, Any]]:
    """A few of the 38 present (some multiple times), most absent."""
    return [
        # kill_switch_invoked x3 — last-seen at 12:00, env_value scalar safe field
        {"action": "kill_switch_invoked", "ts": "2026-05-20T09:00:00Z",
         "session_id": "s1", "env_value": "0"},
        {"action": "kill_switch_invoked", "ts": "2026-05-20T10:00:00Z",
         "session_id": "s2", "env_value": "1"},
        {"action": "kill_switch_invoked", "ts": "2026-05-20T12:00:00Z",
         "session_id": "s3", "env_value": "1",
         # a non-allowlisted + a non-scalar key must NOT leak into the summary
         "secret_token": "DO-NOT-ECHO",
         "verifier_kind_counts": {"path_exists": 2}},
        # federation_scope_denied x1
        {"action": "federation_scope_denied", "ts": "2026-05-21T08:30:00Z",
         "scope": "write:peers", "peer_id": "peer-7"},
        # gpg_signed x2
        {"action": "gpg_signed", "ts": "2026-05-19T01:00:00Z", "signer": "owner"},
        {"action": "gpg_signed", "ts": "2026-05-22T01:00:00Z", "signer": "owner"},
        # a non-critical action must be ignored entirely
        {"action": "agent_spawn", "ts": "2026-05-22T02:00:00Z", "skill": "x"},
        # a critical action with NO ts — counted, but does not set last_ts
        {"action": "trading_write_override_used"},
    ]


class TestCmdCriticalRegistry(unittest.TestCase):
    def test_registry_is_exactly_the_38(self):
        self.assertEqual(set(_aq._CRITICAL_SECURITY_ACTIONS), _EXPECTED_38)
        self.assertEqual(len(_aq._CRITICAL_SECURITY_ACTIONS), 38)

    def test_registry_has_no_duplicates(self):
        self.assertEqual(
            len(_aq._CRITICAL_SECURITY_ACTIONS),
            len(set(_aq._CRITICAL_SECURITY_ACTIONS)),
        )

    def test_every_action_has_a_domain(self):
        for a in _aq._CRITICAL_SECURITY_ACTIONS:
            self.assertIn(a, _aq._CRITICAL_ACTION_DOMAIN)
            self.assertTrue(_aq._CRITICAL_ACTION_DOMAIN[a])


class TestCmdCritical(unittest.TestCase):
    def _by_action(self, out: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        return {row["action"]: row for row in out["data"]["actions"]}

    def test_envelope_shape(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        self.assertEqual(out["query"], "critical")
        self.assertEqual(out["version"], "1")
        data = out["data"]
        self.assertEqual(data["registry_size"], 38)
        self.assertIsNone(data["action_filter"])
        # all 38 listed by default (present + absent)
        self.assertEqual(len(data["actions"]), 38)

    def test_present_actions_counts_and_last_seen(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rows = self._by_action(out)
        self.assertEqual(rows["kill_switch_invoked"]["count"], 3)
        self.assertEqual(rows["kill_switch_invoked"]["last_ts"], "2026-05-20T12:00:00Z")
        self.assertEqual(rows["kill_switch_invoked"]["first_ts"], "2026-05-20T09:00:00Z")
        self.assertEqual(rows["federation_scope_denied"]["count"], 1)
        self.assertEqual(rows["gpg_signed"]["count"], 2)
        self.assertEqual(rows["gpg_signed"]["last_ts"], "2026-05-22T01:00:00Z")

    def test_total_and_present_counts(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        data = out["data"]
        # 3 + 1 + 2 + 1 (trading_write_override_used, no ts) = 7 critical events
        self.assertEqual(data["total_critical_events"], 7)
        # present: kill_switch_invoked, federation_scope_denied, gpg_signed,
        # trading_write_override_used = 4
        self.assertEqual(data["present_action_count"], 4)
        self.assertEqual(data["absent_action_count"], 34)

    def test_absent_actions_listed_with_count_zero(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rows = self._by_action(out)
        # an action never emitted must still appear, count=0, empty ts/summary
        self.assertIn("federation_tamper_detected", rows)
        self.assertEqual(rows["federation_tamper_detected"]["count"], 0)
        self.assertEqual(rows["federation_tamper_detected"]["first_ts"], "")
        self.assertEqual(rows["federation_tamper_detected"]["last_ts"], "")
        self.assertEqual(rows["federation_tamper_detected"]["last_summary"], {})

    def test_count_without_ts_does_not_set_last_ts(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rows = self._by_action(out)
        self.assertEqual(rows["trading_write_override_used"]["count"], 1)
        self.assertEqual(rows["trading_write_override_used"]["last_ts"], "")

    def test_safe_summary_echoes_only_allowlisted_scalars(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rows = self._by_action(out)
        summ = rows["kill_switch_invoked"]["last_summary"]
        # last event (12:00) had session_id + env_value (allowlisted scalars)
        self.assertEqual(summ.get("session_id"), "s3")
        self.assertEqual(summ.get("env_value"), "1")
        # a non-allowlisted field must NOT be echoed (no invented/leaked fields)
        self.assertNotIn("secret_token", summ)
        # a non-scalar allowlisted-or-not field must NOT be echoed
        self.assertNotIn("verifier_kind_counts", summ)

    def test_safe_summary_picks_latest_event(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rows = self._by_action(out)
        # latest kill_switch_invoked is s3 (12:00), not s1/s2
        self.assertEqual(rows["kill_switch_invoked"]["last_summary"]["session_id"], "s3")

    def test_action_filter_returns_only_that_action(self):
        out = _aq.cmd_critical(_make_entries(), _args(action="gpg_signed"))
        data = out["data"]
        self.assertEqual(data["action_filter"], "gpg_signed")
        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["action"], "gpg_signed")
        self.assertEqual(data["actions"][0]["count"], 2)
        # registry_size stays the full 38 even when filtered to one
        self.assertEqual(data["registry_size"], 38)

    def test_action_filter_absent_action_count_zero(self):
        out = _aq.cmd_critical(_make_entries(), _args(action="federation_tamper_detected"))
        data = out["data"]
        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["actions"][0]["count"], 0)
        self.assertEqual(data["present_action_count"], 0)
        self.assertEqual(data["absent_action_count"], 1)

    def test_action_filter_rejects_unknown(self):
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, redirect_stderr(buf):
            _aq.cmd_critical(_make_entries(), _args(action="not_a_real_action"))
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("unknown --action", buf.getvalue())

    def test_empty_log_lists_all_38_with_zero(self):
        out = _aq.cmd_critical([], _args())
        data = out["data"]
        self.assertEqual(data["total_critical_events"], 0)
        self.assertEqual(data["present_action_count"], 0)
        self.assertEqual(data["absent_action_count"], 38)
        self.assertEqual(len(data["actions"]), 38)
        self.assertTrue(all(r["count"] == 0 for r in data["actions"]))

    def test_actions_sorted_by_domain_then_name(self):
        out = _aq.cmd_critical([], _args())
        rows = out["data"]["actions"]
        keys = [(r["domain"], r["action"]) for r in rows]
        self.assertEqual(keys, sorted(keys))


class TestCmdCriticalJson(unittest.TestCase):
    def test_json_render_is_machine_readable(self):
        out = _aq.cmd_critical(_make_entries(), _args())
        rendered = _aq.render(out, as_json=True, as_csv=False)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["query"], "critical")
        self.assertEqual(parsed["data"]["registry_size"], 38)
        self.assertEqual(len(parsed["data"]["actions"]), 38)
        # a present row round-trips through JSON intact
        ksi = next(
            r for r in parsed["data"]["actions"]
            if r["action"] == "kill_switch_invoked"
        )
        self.assertEqual(ksi["count"], 3)
        self.assertEqual(ksi["domain"], "governance")


class TestCmdCriticalParserWiring(unittest.TestCase):
    def test_parser_accepts_critical_subcommand(self):
        parser = _aq.build_parser()
        args = parser.parse_args(["critical"])
        self.assertEqual(args.cmd, "critical")
        self.assertIsNone(args.action)

    def test_parser_accepts_action_flag(self):
        parser = _aq.build_parser()
        args = parser.parse_args(["critical", "--action", "kill_switch_invoked"])
        self.assertEqual(args.action, "kill_switch_invoked")

    def test_parser_critical_supports_shared_json_flag(self):
        parser = _aq.build_parser()
        args = parser.parse_args(["critical", "--json"])
        self.assertTrue(args.as_json)

    def test_dispatch_wired_via_main(self):
        # critical must be reachable through main()'s dispatch map (no log file
        # → empty entries → all 38 listed with count=0). main() prints + returns 0.
        buf_out = io.StringIO()
        from contextlib import redirect_stdout
        with redirect_stdout(buf_out):
            rc = _aq.main(["critical", "--json", "--log", "/nonexistent/audit.jsonl"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf_out.getvalue())
        self.assertEqual(parsed["query"], "critical")
        self.assertEqual(len(parsed["data"]["actions"]), 38)


if __name__ == "__main__":
    unittest.main()
