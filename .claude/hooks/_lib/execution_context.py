"""PLAN-102 Wave B.2b — execution_context HMAC tamper-evidence.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/execution_context.py`. The ceremony apply-patches.py
performs the copy with Owner-signed sentinel (approved.md.asc) covering
the canonical destination per ADR-010.

## Doctrine

Coordinator-process-owned HMAC key (in-memory only; NEVER persisted to
disk) signs every spawn handoff payload. Hook validators reject
unsigned / replayed / stale-nonce / tampered-payload contexts and emit
``execution_context_validation_failed``.

This is INTENTIONALLY decoupled from ADR-121 sentinel-signers-registry:
ADR-121 is still PROPOSED at S134 and PLAN-102 cannot block on it.
A coordinator-bounded key is sufficient because:

- key lifecycle == coordinator process lifecycle (regenerated at start);
- child spawns inherit no read access (process isolation);
- replay protection comes from monotonic nonce + 60s freshness window,
  not from rotation.

Stdlib only. Python >= 3.9. ``CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1``
short-circuits ``validate()`` to ``(False, "disabled")`` as a kill-
switch (Sec MF-3 fail-OPEN posture is preserved by the audit_log
hook layer; this module never emits — it only returns reasons).

## Canonical serialization

``json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()``
is deterministic and HMAC-friendly. Floats forbidden (canonical_json
rule; cents/ints only). All HMAC compares use ``hmac.compare_digest``
for constant-time semantics.

## Cross-process limitation (PLAN-112-FOLLOWUP-execution-context-wire, S154)

The sign/validate handshake works **intra-process only**. Cross-process use
(a coordinator process signs a spawn handoff; a fresh PreToolUse hook process
validates it) is **blocked by construction**: ``_coordinator_key`` is an
in-memory, per-process value (NEVER persisted), so in a fresh hook process it
is ``None`` and ``validate()`` short-circuits to ``(False, "no_key")`` before
any HMAC comparison. Do NOT describe the spawn path as a "replay-protected
handoff" — the nonce-LRU is a per-process replay defense and gives no
cross-process protection.

The cross-process wire is DEFERRED (finding F-1.2-execution_context,
decision RESCOPE-DEFER) until BOTH: (a) the coordinator exits scaffold AND
(b) a cross-process key design lands via ADR-133-AMEND-1. Until then the audit
actions ``execution_context_signed`` / ``execution_context_validation_failed``
are RESERVED (registered, zero producers). See
``_lib/EXECUTION-CONTEXT-DEFERRED.md``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Dict, Optional, Tuple

_NONCE_FRESHNESS_SECONDS = 60
_NONCE_LRU_MAX = 1000
_REQUIRED_FIELDS = (
    "swarm_id",
    "plan_id",
    "class_tier",
    "parent_session_id",
    "nonce",
    "issued_ts",
)


def is_disabled() -> bool:
    """Hook-level kill-switch: env flag short-circuits validation."""
    return os.environ.get("CEO_EXECUTION_CONTEXT_HOOKS_DISABLE", "") == "1"


def _canonical(payload: Dict[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class ExecutionContext:
    """Coordinator-signed handoff payload + replay-protected validator."""

    _coordinator_key: Optional[bytes] = None
    _nonce_counter: int = 0
    _seen_nonces: Dict[int, float] = {}

    def __init__(
        self,
        swarm_id: str,
        plan_id: str,
        class_tier: str,
        parent_session_id: str,
    ) -> None:
        self.swarm_id = swarm_id
        self.plan_id = plan_id
        self.class_tier = class_tier
        self.parent_session_id = parent_session_id
        ExecutionContext._nonce_counter += 1
        self._nonce = ExecutionContext._nonce_counter
        self._issued_ts = time.time()

    @classmethod
    def regenerate_key(cls) -> None:
        """Generate fresh 32-byte HMAC key + clear nonce-replay state.

        Called at coordinator process start. Invalidates every previously
        signed context (intentional — old signatures cannot outlive
        coordinator restarts).
        """
        cls._coordinator_key = secrets.token_bytes(32)
        cls._nonce_counter = 0
        cls._seen_nonces = {}

    @classmethod
    def is_key_initialized(cls) -> bool:
        return cls._coordinator_key is not None

    def to_payload(self) -> Dict[str, object]:
        return {
            "swarm_id": self.swarm_id,
            "plan_id": self.plan_id,
            "class_tier": self.class_tier,
            "parent_session_id": self.parent_session_id,
            "nonce": self._nonce,
            "issued_ts": int(self._issued_ts * 1000),
        }

    def sign(self) -> str:
        """Return hex-encoded HMAC-SHA256 over canonical payload."""
        if ExecutionContext._coordinator_key is None:
            raise RuntimeError(
                "coordinator key not initialized — call regenerate_key() first"
            )
        msg = _canonical(self.to_payload())
        mac = hmac.new(ExecutionContext._coordinator_key, msg, hashlib.sha256)
        return mac.hexdigest()

    @classmethod
    def _prune_nonce_lru(cls) -> None:
        if len(cls._seen_nonces) <= _NONCE_LRU_MAX:
            return
        overflow = len(cls._seen_nonces) - _NONCE_LRU_MAX
        oldest = sorted(cls._seen_nonces.items(), key=lambda kv: kv[1])[:overflow]
        for nonce, _ts in oldest:
            cls._seen_nonces.pop(nonce, None)

    @classmethod
    def validate(
        cls,
        payload: Dict[str, object],
        signature: str,
        max_age_seconds: int = _NONCE_FRESHNESS_SECONDS,
    ) -> Tuple[bool, str]:
        """Verify signature + nonce freshness + replay-not-seen.

        Returns ``(valid, reason)``. Reasons:

        - ``ok``               — fully verified
        - ``disabled``         — ``CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1``
        - ``no_key``           — coordinator key not initialized
        - ``missing_field``    — required payload field absent / wrong type
        - ``stale_nonce``      — issued_ts older than ``max_age_seconds``
        - ``nonce_replay``     — nonce already observed in window
        - ``bad_signature``    — HMAC mismatch (constant-time)
        """
        if is_disabled():
            return (False, "disabled")
        if cls._coordinator_key is None:
            return (False, "no_key")
        if not isinstance(payload, dict):
            return (False, "missing_field")
        for field_name in _REQUIRED_FIELDS:
            if field_name not in payload:
                return (False, "missing_field")
        try:
            issued_ts_ms = int(payload["issued_ts"])
        except (TypeError, ValueError):
            return (False, "missing_field")
        now = time.time()
        age = now - (issued_ts_ms / 1000.0)
        if age > max_age_seconds or age < -max_age_seconds:
            return (False, "stale_nonce")
        try:
            nonce = int(payload["nonce"])
        except (TypeError, ValueError):
            return (False, "missing_field")
        cutoff = now - max_age_seconds
        cls._seen_nonces = {n: t for n, t in cls._seen_nonces.items() if t >= cutoff}
        if nonce in cls._seen_nonces:
            return (False, "nonce_replay")
        msg = _canonical(payload)
        expected = hmac.new(cls._coordinator_key, msg, hashlib.sha256).hexdigest()
        try:
            sig_bytes = signature.encode("ascii")
            exp_bytes = expected.encode("ascii")
        except (AttributeError, UnicodeEncodeError):
            return (False, "bad_signature")
        if not hmac.compare_digest(sig_bytes, exp_bytes):
            return (False, "bad_signature")
        cls._seen_nonces[nonce] = now
        cls._prune_nonce_lru()
        return (True, "ok")
