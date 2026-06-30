"""PLAN-099-FOLLOWUP Wave D.1 — /federation/audit-event/batch handler.

Staged at .claude/plans/PLAN-099-FOLLOWUP/wave-d-staging/handlers/audit_event_batch.py.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/handlers/audit_event_batch.py``
at Phase A2-post.

## Scope (ADR-135-AMEND-1 §2.1 / D.1)

- Method: POST /federation/audit-event/batch
- Scope name: ``audit_event_push_batch`` (NON-destructive — gate #10 N/A)
- Side-effect: append N remote events to local audit-log.jsonl
- HARD CAP: ≤100 events per request (parse-time reject 400 if exceeded)

## Atomicity contract

The batch is NOT transactional — partial failure is the documented
behaviour. The N events are validated upfront (FAIL FAST on the first
schema violation; nothing appended). Then events are appended one by
one. A mid-batch failure leaves events 0..k-1 durably appended, k..N-1
NOT — the caller's response carries (accepted_count, failed_index).

This avoids the implementation complexity of a multi-event atomic
journal while preserving forensic clarity: each event still emits its
own ``federation_audit_event_pushed`` AND the request emits a parent
``federation_audit_event_pushed_batch``.

## Audit emit fan-out

  - 1× ``federation_audit_event_pushed_batch`` (parent, request-level)
  - N× ``federation_audit_event_pushed`` (per-event, child-level)

Per-event allowlist enforcement is identical to the single-event
handler (audit_event_push.py).

## Append-only contract inheritance

This batch handler delegates per-event append to
``audit_event_push._append_event`` — which honours the
**audit-log append-only contract (PLAN-099 §audit-log) — atomic
single-line append guaranteed by O_APPEND on POSIX local filesystems**
(see ``audit_event_push.py`` module docstring for the full rationale).
No tmpfile+rename per event; each append is its own atomic POSIX write
under the PIPE_BUF=4096 guarantee. Partial-failure mid-batch leaves
events 0..k-1 durably appended without rollback (forensic clarity
preferred over multi-event transactionality).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple


__all__ = [
    "handle",
    "BatchError",
    "MAX_BATCH_SIZE",
]


# Hard cap per ADR-135-AMEND-1 §2.1 + D.5 — defense against
# storage-amplification DoS. Gate #9 (rate-limit) complements this in
# the temporal dimension; this is the per-request size cap.
MAX_BATCH_SIZE = 100

# Maximum body size — 100 events × 8 KiB + 4 KiB envelope.
MAX_BATCH_BYTES = MAX_BATCH_SIZE * 8 * 1024 + 4 * 1024


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
    # PLAN-112-FOLLOWUP C-4 fix (R-TD-1): fall back to emit_generic.
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
                "[handlers.audit_event_batch] audit emit '{0}' raised\n".format(
                    action
                )
            )
        except Exception:
            pass


class BatchError(ValueError):
    """Batch-level validation failure (size / shape / fail-fast schema)."""


# ----------------------------------------------------------------------------
# Single-event delegation
# ----------------------------------------------------------------------------


def _import_single_handler():
    """Lazy-import the single-event handler (shared validation + append).

    Resolution order (F-004 fix):
      1. Canonical package path ``_lib.federation.handlers.audit_event_push``
         (post-Owner-A2-post).
      2. Staging file-path fallback via ``importlib.util.spec_from_file_location``
         from the sibling ``audit_event_push.py`` (pre-Owner-A2-post,
         when this module is loaded directly from
         ``wave-d-staging/handlers/`` via spec_from_file_location and
         has no package context).
    """
    # 1. Canonical path (post-Owner-A2-post).
    try:
        from _lib.federation.handlers import audit_event_push as _push  # type: ignore
        return _push
    except ImportError:
        pass

    # 2. Staging fallback (pre-Owner-A2-post) — sibling file load via
    # spec_from_file_location. Required because when this module is
    # itself loaded via spec_from_file_location from the staging dir,
    # neither plain import nor relative import resolves the sibling
    # (no sys.path entry, no package context).
    import importlib.util
    from pathlib import Path as _Path
    push_path = _Path(__file__).parent / "audit_event_push.py"
    if push_path.exists():
        spec = importlib.util.spec_from_file_location(
            "audit_event_push_staging", str(push_path),
        )
        if spec is None or spec.loader is None:
            raise ImportError(
                "audit_event_push not available: spec_from_file_location failed"
            )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    raise ImportError(
        "audit_event_push not available in canonical or staging"
    )


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
    """Top-level handler for POST /federation/audit-event/batch.

    Gate #11. Gates #1-9 enforced by the dispatcher. Gate #10 N/A.

    Body shape::

        {"events": [<event>, <event>, ...]}

    Returns
    -------
    (status, reason, response_body)
        status:
          - 200 — all events appended.
          - 207 — partial success (accepted_count < total). Response
                  body carries {"accepted": K, "failed_at": k, "reason": "..."}.
          - 400 — batch shape error (size cap, schema fail-fast,
                  bad JSON).
          - 413 — body bytes exceed MAX_BATCH_BYTES.
          - 500 — IO failure on append.
    """
    if not isinstance(body, (bytes, bytearray)):
        return 400, "body_not_bytes", b'{"error":"bad_body"}'

    if len(body) > MAX_BATCH_BYTES:
        # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event/batch",
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
            route="/federation/audit-event/batch",
            gate_failed=11,
            reason_code="bad_body",
        )
        return 400, "bad_body", b'{"error":"bad_body"}'

    if not isinstance(parsed, Mapping):
        return 400, "envelope_not_object", b'{"error":"shape"}'

    events = parsed.get("events")
    if not isinstance(events, list):
        return 400, "events_not_list", b'{"error":"shape"}'

    if len(events) == 0:
        return 400, "empty_batch", b'{"error":"empty_batch"}'

    # HARD CAP enforcement — parse-time per the contract.
    if len(events) > MAX_BATCH_SIZE:
        # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/audit-event/batch",
            gate_failed=11,
            reason_code="batch_too_large",
        )
        return 400, "batch_too_large", b'{"error":"batch_too_large"}'

    push = _import_single_handler()
    if audit_log_path is None:
        audit_log_path = push._resolve_audit_log_path()  # type: ignore[attr-defined]

    # PASS 1 — fail-fast schema validation across the whole batch.
    canonicals: List[Mapping[str, Any]] = []
    for idx, evt in enumerate(events):
        if not isinstance(evt, Mapping):
            _safe_emit(
                "federation_write_endpoint_denied",
                peer_id=str(peer_row.get("peer_id", ""))[:64],
                route="/federation/audit-event/batch",
                gate_failed=11,
                reason_code="event_not_object",
            )
            return (
                400,
                "event_not_object:{0}".format(idx),
                b'{"error":"shape"}',
            )
        try:
            canonical = push._validate_event(evt, peer_row)  # type: ignore[attr-defined]
        except push.AuditEventError as exc:  # type: ignore[attr-defined]
            msg = str(exc)
            if msg.startswith("action_blocked:"):
                # F-001 R2 iter-2 fix: F.2 wrapper signature is
                # `emit_federation_event_action_blocked(peer_id,
                # event_action, reason_code)`. `batch_index` is NOT
                # in the F.2 allowlist; the response body carries the
                # idx for the caller.
                _safe_emit(
                    "federation_event_action_blocked",
                    peer_id=str(peer_row.get("peer_id", ""))[:64],
                    event_action=msg.split(":", 1)[1][:64],
                    reason_code="action_not_allowed",
                )
                return (
                    400,
                    "{0}:idx={1}".format(msg, idx),
                    b'{"error":"action_blocked"}',
                )
            _safe_emit(
                "federation_write_endpoint_denied",
                peer_id=str(peer_row.get("peer_id", ""))[:64],
                route="/federation/audit-event/batch",
                gate_failed=11,
                reason_code="schema:{0}".format(msg[:24]),
            )
            return (
                400,
                "schema:{0}:idx={1}".format(msg[:48], idx),
                b'{"error":"schema"}',
            )
        canonicals.append(canonical)

    # PASS 2 — atomic-append each (partial-success on IO error mid-pass).
    accepted = 0
    for idx, canonical in enumerate(canonicals):
        ok, reason = push._append_event(audit_log_path, canonical)  # type: ignore[attr-defined]
        if not ok:
            # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
            # Partial-success counts are surfaced in the response body
            # (status 207); not emitted via audit (would require a
            # dedicated F.2 wrapper).
            _safe_emit(
                "federation_write_endpoint_denied",
                peer_id=str(peer_row.get("peer_id", ""))[:64],
                route="/federation/audit-event/batch",
                gate_failed=11,
                reason_code="partial_io_error",
            )
            resp = json.dumps({
                "status": "partial",
                "accepted": accepted,
                "failed_at": idx,
                "reason": reason[:80],
            }).encode("utf-8")
            return 207, "partial:{0}/{1}".format(accepted, len(canonicals)), resp
        # F-001 R2 iter-2 fix: per-event child emit aligned with F.2
        # wrapper signature. `batch_index` + `federation_origin` are
        # NOT in the F.2 allowlist; preserved via the per-batch parent
        # `emit_federation_audit_event_pushed_batch` aggregate counts
        # + the appended log line itself.
        _safe_emit(
            "federation_audit_event_pushed",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            event_action=canonical["action"][:64],
            hmac_ok=True,
            origin_overwritten=True,
        )
        accepted += 1

    # PASS 3 — parent emit.
    # F-001 R2 iter-2 fix: F.2 wrapper signature is
    # `emit_federation_audit_event_pushed_batch(peer_id, batch_size,
    # accepted_count, rejected_count)`. Successful path: all events
    # accepted (rejected_count=0).
    _safe_emit(
        "federation_audit_event_pushed_batch",
        peer_id=str(peer_row.get("peer_id", ""))[:64],
        batch_size=int(len(canonicals)),
        accepted_count=int(accepted),
        rejected_count=int(len(canonicals) - accepted),
    )

    resp = json.dumps({"status": "appended", "accepted": accepted}).encode("utf-8")
    return 200, "ok", resp
