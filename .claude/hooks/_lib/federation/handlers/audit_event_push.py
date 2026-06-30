"""PLAN-099-FOLLOWUP Wave D.1 — /federation/audit-event handler.

Staged at .claude/plans/PLAN-099-FOLLOWUP/wave-d-staging/handlers/audit_event_push.py.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/handlers/audit_event_push.py``
at Phase A2-post.

## Scope (ADR-135-AMEND-1 §2.1 / D.1)

- Method: POST /federation/audit-event
- Scope name: ``audit_event_push`` (NON-destructive — gate #10 N/A)
- Side-effect: append remote event to local audit-log.jsonl
- Per-action allowlist: peer_row['audit_event_push_allowlist'] (list)

## Action allowlist (defense-in-depth)

Each peer carries an ``audit_event_push_allowlist: [<action>, ...]``
list in its peers.yaml row. Default empty → ALL pushes rejected with
``federation_event_action_blocked``. This forces the federation
operator to EXPLICITLY enumerate which remote events that peer is
authorised to push. Mirrors the scope-grant default-empty doctrine
from ADR-135-AMEND-1 §2.1.

## Audit-chain stitching

The remote event is wrapped with a local ``federation_audit_event_pushed``
audit emit AND the event payload is appended verbatim to
audit-log.jsonl with ``federation_origin = <peer_id_spki_fpr>`` for
forensic traceability. Wave E will add chain-break detection (prev_hash
mismatch → ``federation_tamper_detected``); here we wire the field
without strict enforcement.

STDLIB-ONLY per ADR-126 §Part 6.

## Audit-log append-only contract (PLAN-099 §audit-log)

Unlike peers.yaml mutations (which use the same-directory tmpfile +
fsync + os.rename atomic-replace pattern), audit-log writes follow the
**append-only contract** — single-line atomic append via
``O_APPEND + os.write + os.fsync``. The POSIX append guarantee for
writes under ``PIPE_BUF`` (4096 bytes on Linux/macOS, payload cap is
enforced upstream at 4 KiB) provides byte-level atomicity for the
record write without requiring a rename ceremony.

This contract MIRRORS the existing PLAN-099 MVP audit emit path
(``federation/server.py`` / ``federation/audit_chain.py``) — Wave D's
``_append_event`` and ``audit_event_batch._append_event`` (delegated)
inherit this contract. No tmpfile + rename is needed for audit events.

Rationale: append-only forensic logs have an ORDER invariant
(events are linearised by wall-clock); tmpfile+rename would either
truncate the log or require a complex append-merge that defeats the
forensic chain (``prev_hash`` linkage).

Reference: ``audit-log append-only contract (PLAN-099 §audit-log) —
atomic single-line append guaranteed by O_APPEND on POSIX local
filesystems``.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple


__all__ = [
    "handle",
    "AuditEventError",
    "_validate_event",
    "_append_event",
]


# ----------------------------------------------------------------------------
# Audit emit shim
# ----------------------------------------------------------------------------


def _safe_emit(action: str, **fields: Any) -> None:
    """Call audit_emit.emit_<action>(...) if registered. WAVE-F-PENDING."""
    try:
        try:
            from _lib import audit_emit  # type: ignore[import]
        except ImportError:
            import importlib
            audit_emit = importlib.import_module(".audit_emit", package="_lib")
    except ImportError:
        return
    # PLAN-112-FOLLOWUP C-4 fix (R-TD-1): fall back to emit_generic so
    # federation_audit_event_pushed / _event_action_blocked are written.
    fn = getattr(audit_emit, "emit_{0}".format(action), None)
    try:
        if fn is not None:
            fn(**fields)
            return
        generic = getattr(audit_emit, "emit_generic", None)
        if generic is not None:
            generic(action, **fields)
    except Exception:
        try:
            sys.stderr.write(
                "[handlers.audit_event_push] audit emit '{0}' raised\n".format(
                    action
                )
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


# Audit action charset — alphanumeric + underscore.
_ACTION_RE = re.compile(r"^[a-z][a-z0-9_]{0,127}$")

# Maximum body size to accept (8 KiB per event — well under default
# stdlib http.server LimitedReader; redundant but explicit).
MAX_EVENT_BYTES = 8 * 1024


class AuditEventError(ValueError):
    """Schema validation failure. Caller maps to HTTP 400."""


def _validate_event(
    event: Mapping[str, Any],
    peer_row: Mapping[str, Any],
    *,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Validate a single audit event from a remote peer. Returns canonicalised.

    Required fields per audit-log.schema.md v2.x:
      - action      str, _ACTION_RE
      - ts          ISO-8601 (or epoch-ms int)
      - schema_version  str (rejected if missing — strict forward-compat)

    Optional:
      - prev_hash   sha256 hex (forensic chain; Wave E enforces)
      - nonce       str (replay; Wave E enforces vs sliding window)

    Enforces peer's ``audit_event_push_allowlist`` — action NOT in list
    raises AuditEventError("action_blocked:<action>") and the caller
    emits ``federation_event_action_blocked``.
    """
    if not isinstance(event, Mapping):
        raise AuditEventError("event_not_object")

    action = event.get("action")
    if not isinstance(action, str):
        raise AuditEventError("action_not_str")
    if not _ACTION_RE.match(action):
        raise AuditEventError("action_charset:{0}".format(action[:32]))

    if "ts" not in event or event["ts"] in (None, ""):
        raise AuditEventError("missing_field:ts")
    if "schema_version" not in event:
        raise AuditEventError("missing_field:schema_version")

    # Per-peer action allowlist gate.
    allowlist = peer_row.get("audit_event_push_allowlist", [])
    if not isinstance(allowlist, (list, tuple)):
        raise AuditEventError("peer_allowlist_malformed")
    if action not in allowlist:
        raise AuditEventError("action_blocked:{0}".format(action))

    # Canonical row — we trust the dispatcher's HMAC + nonce gates;
    # this handler does NOT re-verify them (defense-in-depth would
    # mask a gate-chain bug).
    canonical: Dict[str, Any] = {
        "action": action,
        "ts": event["ts"],
        "schema_version": event["schema_version"],
        "federation_origin": peer_row.get(
            "peer_id_spki_fingerprint",
            peer_row.get("peer_id_cert_fingerprint", ""),
        ),
        "federation_origin_peer_id": peer_row.get("peer_id", ""),
    }

    # Pass-through forensic fields (whitelisted to prevent peer
    # smuggling arbitrary structures into the local log).
    for fld in ("prev_hash", "nonce", "correlation_id", "schema_version"):
        if fld in event and event[fld] not in (None, ""):
            v = event[fld]
            if not isinstance(v, (str, int)):
                raise AuditEventError("forensic_field_type:{0}".format(fld))
            canonical[fld] = v

    # Pass-through payload field — opaque to us, but capped at 4 KiB
    # serialised. Anything bigger → reject (prevent storage-exhaustion
    # DoS; Wave E circuit-breaker complements this).
    payload = event.get("payload")
    if payload is not None:
        try:
            payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise AuditEventError(
                "payload_serialise:{0}".format(type(exc).__name__)
            )
        if len(payload_bytes) > 4096:
            raise AuditEventError("payload_too_large")
        canonical["payload"] = payload

    return canonical


# ----------------------------------------------------------------------------
# Audit-log append
# ----------------------------------------------------------------------------


def _resolve_audit_log_path() -> Path:
    """Resolve the local audit-log.jsonl path.

    Adopter installs typically use ``$CLAUDE_PROJECT_DIR/.claude/state/
    audit-log.jsonl`` or the platform default. We honour
    ``CEO_AUDIT_LOG_PATH`` override for tests.
    """
    override = os.environ.get("CEO_AUDIT_LOG_PATH")
    if override:
        return Path(override)
    project_dir = os.environ.get(
        "CLAUDE_PROJECT_DIR", os.getcwd()
    )
    return Path(project_dir) / ".claude" / "state" / "audit-log.jsonl"


def _append_event(audit_log_path: Path, canonical_event: Mapping[str, Any]) -> Tuple[bool, str]:
    """Append a single canonical event to audit-log.jsonl. Atomic append.

    **Append-only contract** — see module docstring for the full
    contract reference (``audit-log append-only contract
    (PLAN-099 §audit-log) — atomic single-line append guaranteed by
    O_APPEND on POSIX local filesystems``). This intentionally does
    NOT use the tmpfile+rename pattern that peers.yaml mutations use:
    audit events are linearised by wall-clock and have a forensic
    ``prev_hash`` chain, which a rename ceremony would break.

    For events under PIPE_BUF (4 KiB on Linux/macOS, payload cap is
    enforced upstream at 4 KiB), O_APPEND + write is atomic per POSIX;
    we add fsync for durability. Larger events are rejected at
    validation.

    Returns
    -------
    (True, "appended") or (False, "io_error:<...>")
    """
    parent = audit_log_path.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, "io_error:mkdir:{0}".format(exc.errno or "unknown")

    line = json.dumps(canonical_event, sort_keys=True) + "\n"
    line_bytes = line.encode("utf-8")

    fd = None
    try:
        fd = os.open(
            str(audit_log_path),
            os.O_WRONLY | os.O_APPEND | os.O_CREAT,
            0o600,
        )
        os.write(fd, line_bytes)
        os.fsync(fd)
    except OSError as exc:
        return False, "io_error:write:{0}".format(exc.errno or "unknown")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    return True, "appended"


# ----------------------------------------------------------------------------
# Handler entry point
# ----------------------------------------------------------------------------


def handle(
    peer_row: Mapping[str, Any],
    headers: Mapping[str, str],
    body: bytes,
    *,
    audit_log_path: Optional[Path] = None,
) -> Tuple[int, str, bytes]:
    """Top-level handler for POST /federation/audit-event.

    Gate #11. Gates #1-9 + #11-fragment (rate limit) enforced upstream
    by the dispatcher. Gate #10 (Owner co-sign) is NOT required for
    audit_event_push (NON-destructive per ADR-135-AMEND-1 §2.5).

    Returns
    -------
    (status, reason, response_body)
    """
    if audit_log_path is None:
        audit_log_path = _resolve_audit_log_path()

    if not isinstance(body, (bytes, bytearray)):
        return 400, "body_not_bytes", b'{"error":"bad_body"}'

    if len(body) > MAX_EVENT_BYTES:
        # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
        # `size` field dropped — wrapper does not accept it.
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event",
            gate_failed=11,
            reason_code="body_too_large",
        )
        return 413, "body_too_large", b'{"error":"too_large"}'

    try:
        parsed = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event",
            gate_failed=11,
            reason_code="bad_body",
        )
        return 400, "bad_body", b'{"error":"bad_body"}'

    try:
        canonical = _validate_event(parsed, peer_row)
    except AuditEventError as exc:
        msg = str(exc)
        if msg.startswith("action_blocked:"):
            # F-001 R2 iter-2 fix: F.2 wrapper signature is
            # `emit_federation_event_action_blocked(peer_id,
            # event_action, reason_code)`. ``audit_action`` collides
            # with `_safe_emit`'s positional `action`, so we use
            # `event_action` (the F.2 field name) directly.
            # reason_code is a closed enum:
            # action_not_allowed / action_unknown / action_kernel_only.
            _safe_emit(
                "federation_event_action_blocked",
                peer_id=str(peer_row.get("peer_id", ""))[:64],
                event_action=msg.split(":", 1)[1][:64],
                reason_code="action_not_allowed",
            )
            return 400, msg, b'{"error":"action_blocked"}'
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event",
            gate_failed=11,
            reason_code="schema:{0}".format(msg[:24]),
        )
        return 400, msg, b'{"error":"schema"}'

    ok, reason = _append_event(audit_log_path, canonical)
    if not ok:
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event",
            gate_failed=11,
            reason_code="io_error:{0}".format(reason[:21]),
        )
        return 500, reason, b'{"error":"io"}'

    # F-001 R2 iter-2 fix: F.2 wrapper signature is
    # `emit_federation_audit_event_pushed(peer_id, event_action,
    # hmac_ok, origin_overwritten)`. We map:
    #   - remote_action -> event_action
    #   - hmac_ok=True (HMAC verified by dispatcher gate #3)
    #   - origin_overwritten=True (server rewrote federation_origin
    #     in _validate_event lines 177-181)
    # `federation_origin` is preserved in the appended log line; it
    # is not echoed in the audit emit since it would duplicate the
    # peer_id signal.
    _safe_emit(
        "federation_audit_event_pushed",
        peer_id=str(peer_row.get("peer_id", ""))[:64],
        event_action=canonical["action"][:64],
        hmac_ok=True,
        origin_overwritten=True,
    )
    return 200, "ok", b'{"status":"appended"}'
