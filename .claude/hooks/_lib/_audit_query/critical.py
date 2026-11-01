"""critical audit-query declarations."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

__all__ = ('_CRITICAL_SECURITY_ACTIONS', '_CRITICAL_ACTION_DOMAIN', '_CRITICAL_SAFE_SUMMARY_KEYS', 'cmd_critical', '_CRITICAL_SECURITY_ACTION_SET', '_critical_safe_summary')


_CRITICAL_SECURITY_ACTIONS: Tuple[str, ...] = (
    # --- federation (cross-machine peer trust / write-mode) ---
    "federation_autonomous_call_blocked",
    "federation_cert_revoked",
    "federation_event_action_blocked",
    "federation_hmac_secret_rotated",
    "federation_key_floor_rejected",
    "federation_lan_bind_denied",
    "federation_peer_revoked_remote",
    "federation_scope_denied",
    "federation_spki_fingerprint_mismatch",
    "federation_tamper_detected",
    "federation_write_attempt_blocked",
    "federation_write_endpoint_denied",
    # --- mcp (bearer-token / tenant isolation) ---
    "mcp_bearer_replay_rejected",
    "mcp_cross_tenant_denied",
    "mcp_non_loopback_rejected",
    # --- sentinel-signer (GPG quorum / rotation / revocation) ---
    "gpg_signed",
    "gpg_verified",
    "sentinel_signer_expiry_warned",
    "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed",
    "sentinel_signer_revoked",
    "sentinel_signer_rotated",
    # --- trading (kill-switch / write-override) ---
    "trading_kill_switch_disabled",
    "trading_kill_switch_invoked",
    "trading_write_override_used",
    # --- credential (age / emergency override) ---
    "credential_blocked_due_to_age",
    "credential_emergency_override_used",
    # --- audit-spool (tamper detection) ---
    "audit_spool_tamper_detected",
    # --- governance (kernel / kill-switch / overrides / pair-rail / swarm) ---
    "anti_ceo_overhead_override_used",
    "bash_canonical_bypass_invoked",
    "confidence_gate_blocked",
    "kernel_extension_landed",
    "kill_switch_invoked",
    "live_adapter_blocked",
    "pair_rail_codex_injection_detected",
    "pair_rail_outgoing_redaction_applied",
    "phase_c_enforcing_flipped",
    "swarm_layer_3_4_blocked",
)

# Map each critical action to its domain group (for the table/json output).
# Domains mirror the comment blocks in _CRITICAL_SECURITY_ACTIONS above.
_CRITICAL_ACTION_DOMAIN: Dict[str, str] = {
    # federation
    "federation_autonomous_call_blocked": "federation",
    "federation_cert_revoked": "federation",
    "federation_event_action_blocked": "federation",
    "federation_hmac_secret_rotated": "federation",
    "federation_key_floor_rejected": "federation",
    "federation_lan_bind_denied": "federation",
    "federation_peer_revoked_remote": "federation",
    "federation_scope_denied": "federation",
    "federation_spki_fingerprint_mismatch": "federation",
    "federation_tamper_detected": "federation",
    "federation_write_attempt_blocked": "federation",
    "federation_write_endpoint_denied": "federation",
    # mcp
    "mcp_bearer_replay_rejected": "mcp",
    "mcp_cross_tenant_denied": "mcp",
    "mcp_non_loopback_rejected": "mcp",
    # sentinel-signer
    "gpg_signed": "sentinel-signer",
    "gpg_verified": "sentinel-signer",
    "sentinel_signer_expiry_warned": "sentinel-signer",
    "sentinel_signer_quorum_attempted": "sentinel-signer",
    "sentinel_signer_quorum_failed": "sentinel-signer",
    "sentinel_signer_revoked": "sentinel-signer",
    "sentinel_signer_rotated": "sentinel-signer",
    # trading
    "trading_kill_switch_disabled": "trading",
    "trading_kill_switch_invoked": "trading",
    "trading_write_override_used": "trading",
    # credential
    "credential_blocked_due_to_age": "credential",
    "credential_emergency_override_used": "credential",
    # audit-spool
    "audit_spool_tamper_detected": "audit-spool",
    # governance
    "anti_ceo_overhead_override_used": "governance",
    "bash_canonical_bypass_invoked": "governance",
    "confidence_gate_blocked": "governance",
    "kernel_extension_landed": "governance",
    "kill_switch_invoked": "governance",
    "live_adapter_blocked": "governance",
    "pair_rail_codex_injection_detected": "governance",
    "pair_rail_outgoing_redaction_applied": "governance",
    "phase_c_enforcing_flipped": "governance",
    "swarm_layer_3_4_blocked": "governance",
}

# Allowlist of SAFE, schema-stable scalar summary keys to echo when present
# on a critical event. We never echo arbitrary fields (avoids surfacing
# large/unexpected payloads) and never INVENT a field — only keys in this set
# that actually exist on the event dict are surfaced, and only scalar values
# (str/int/float/bool). These keys are all part of audit_emit's per-action
# allowlists (already scrubbed at emit time) so echoing them is safe.
_CRITICAL_SAFE_SUMMARY_KEYS: Tuple[str, ...] = (
    "session_id",
    "project",
    "reason",
    "reason_code",
    "scope",
    "phase",
    "migration_phase",
    "env_value",
    "mode",
    "outcome",
    "decision",
    "peer_id",
    "endpoint",
    "tenant",
    "signer",
    "key_id",
    "fingerprint",
    "loop_id",
    "redaction_count",
    "field_count",
)


def cmd_critical(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query critical` — surface the 38 critical-security actions.

    PLAN-113 Phase B, Wave W1 (audit-reader-coverage). Each action in
    ``_CRITICAL_SECURITY_ACTIONS`` is emitted by a hook but had no reader
    handler, so an operator could not query it. This command aggregates,
    per critical action that appears in the log: ``count``, first/last ISO
    timestamp, and a compact set of SAFE summary fields drawn from the
    LATEST matching event (only keys in ``_CRITICAL_SAFE_SUMMARY_KEYS`` that
    are actually present + scalar — no invented fields).

    Actions with ZERO occurrences are STILL emitted with ``count=0`` so a
    missing-but-expected critical event is visible (surfacing absence is the
    whole point of the reader-coverage gap PLAN-112 found).

    ``--action <name>`` drills into one action; the name must be in the
    registry (else error). Output is a table (default) or JSON (``--json``).

    Output envelope (mirrors the other v-era commands):
        {"query": "critical", "version": "1",
         "data": {"action_filter": ..., "total_critical_events": N,
                  "present_action_count": M, "registry_size": 38,
                  "actions": [{action, domain, count, first_ts, last_ts,
                               last_summary: {...}}, ...]}}
    """
    action_filter = getattr(args, "action", None)
    if action_filter is not None:
        if action_filter not in _CRITICAL_SECURITY_ACTION_SET:
            print(
                f"[audit-query] ERROR: critical: unknown --action "
                f"{action_filter!r}; must be one of the "
                f"{len(_CRITICAL_SECURITY_ACTIONS)} registry actions",
                file=sys.stderr,
            )
            sys.exit(1)
        registry: Tuple[str, ...] = (action_filter,)
    else:
        registry = _CRITICAL_SECURITY_ACTIONS

    # Single pass: accumulate count / first_ts / last_ts / latest-event
    # safe-summary per critical action. We only track actions in `registry`.
    registry_set = set(registry)
    agg: Dict[str, Dict[str, Any]] = {
        a: {"count": 0, "first_ts": "", "last_ts": "", "last_summary": {}}
        for a in registry
    }
    total_critical_events = 0

    for e in entries:
        action = e.get("action")
        if action not in registry_set:
            continue
        a = agg[action]
        a["count"] += 1
        total_critical_events += 1
        ts = str(e.get("ts") or "")
        if ts:
            if not a["first_ts"] or ts < a["first_ts"]:
                a["first_ts"] = ts
            if ts >= a["last_ts"]:
                a["last_ts"] = ts
                a["last_summary"] = _critical_safe_summary(e)

    actions: List[Dict[str, Any]] = []
    present_action_count = 0
    # Stable order: by domain, then action name (registry is the universe).
    for action in sorted(
        registry,
        key=lambda x: (_CRITICAL_ACTION_DOMAIN.get(x, "zzz"), x),
    ):
        a = agg[action]
        if a["count"] > 0:
            present_action_count += 1
        actions.append(
            {
                "action": action,
                "domain": _CRITICAL_ACTION_DOMAIN.get(action, "unknown"),
                "count": a["count"],
                "first_ts": a["first_ts"],
                "last_ts": a["last_ts"],
                "last_summary": a["last_summary"],
            }
        )

    data = {
        "action_filter": action_filter,
        "registry_size": len(_CRITICAL_SECURITY_ACTIONS),
        "total_critical_events": total_critical_events,
        "present_action_count": present_action_count,
        "absent_action_count": len(registry) - present_action_count,
        "actions": actions,
    }
    return {
        "query": "critical",
        "version": "1",
        "data": data,
    }


# Set form for O(1) membership tests (validation + per-entry filter).
_CRITICAL_SECURITY_ACTION_SET = frozenset(_CRITICAL_SECURITY_ACTIONS)


def _critical_safe_summary(event: Dict[str, Any]) -> Dict[str, Any]:
    """Echo only the SAFE, scalar summary keys present on a critical event.

    Never invents a field: iterates ``_CRITICAL_SAFE_SUMMARY_KEYS`` and copies
    a key only when it exists on the event AND its value is a scalar
    (str/int/float/bool). This keeps the per-action summary compact and avoids
    surfacing large/unexpected payloads.
    """
    out: Dict[str, Any] = {}
    for key in _CRITICAL_SAFE_SUMMARY_KEYS:
        if key not in event:
            continue
        val = event[key]
        if isinstance(val, bool) or isinstance(val, (str, int, float)):
            out[key] = val
    return out


