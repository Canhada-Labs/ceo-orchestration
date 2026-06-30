"""PLAN-099-FOLLOWUP Wave D.1 — /federation/peer-revoke handler.

Staged at .claude/plans/PLAN-099-FOLLOWUP/wave-d-staging/handlers/peer_revoke.py.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/handlers/peer_revoke.py``
at Phase A2-post.

## Scope (ADR-135-AMEND-1 §2.1 / D.1)

- Method: POST /federation/peer-revoke
- Scope name: ``peer_revoke`` (DESTRUCTIVE — gate #10 Owner co-sign required)
- Side-effect: mark ``peers.yaml[peer].revoked: true`` atomically

## Why destructive

A peer-revoke mutates the federation TRUST ROOT (peers.yaml). MITRE
ATT&CK T1485 (Data Destruction) — an attacker who acquires write
authority for the ``peer_revoke`` scope can incapacitate the entire
federation by revoking every peer. Hence the gate #10 Owner co-sign
sentinel requirement (per ADR-135-AMEND-1 §2.5).

## Idempotency

Revoking an already-revoked peer is treated as success (200) — the
state matches the intent. Audit emit fires regardless to preserve
forensic record of the revocation attempt.

## Atomic-write protocol

Same as peer_register.py — tmpfile in same directory + fsync + rename.
Cross-FS rename is NOT atomic on POSIX; same-directory IS atomic.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple


__all__ = [
    "handle",
    "PeerRevokeError",
]


# peer_id charset — must match peer_register.py.
_PEER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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
                "[handlers.peer_revoke] audit emit '{0}' raised\n".format(action)
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


class PeerRevokeError(ValueError):
    """Body validation failure."""


def _validate_revoke_body(body: Mapping[str, Any]) -> str:
    """Return the target peer_id. Raises PeerRevokeError on schema fail.

    Body shape::

        {"target_peer_id": "<id>", "reason": "<optional>"}
    """
    if not isinstance(body, Mapping):
        raise PeerRevokeError("body_not_object")
    target = body.get("target_peer_id")
    if not isinstance(target, str) or not target:
        raise PeerRevokeError("missing_field:target_peer_id")
    if not _PEER_ID_RE.match(target):
        raise PeerRevokeError("target_peer_id_charset")
    return target


# ----------------------------------------------------------------------------
# Peers.yaml atomic mutation — mark revoked
# ----------------------------------------------------------------------------


def _atomic_revoke_peer(
    peers_path: Path,
    target_peer_id: str,
) -> Tuple[bool, str, bool]:
    """Set ``peers.yaml[<target_peer_id>].revoked = True`` atomically.

    Returns
    -------
    (ok, reason, was_already_revoked)
        ok=True on success.
        was_already_revoked=True if the peer was already revoked
        (idempotency signal — caller still returns 200 but emit
        carries the marker).
    """
    # Lazy-import the same loader/serialiser used by peer_register
    # (canonical bridge with parse_peers_text / serialise_peers_payload).
    try:
        try:
            from _lib.federation import identity as _identity  # type: ignore
        except ImportError:
            import importlib
            _identity = importlib.import_module(
                "_lib.federation.identity"
            )
    except ImportError:
        return False, "identity_module_missing", False

    if not peers_path.exists():
        return False, "peers_yaml_missing", False

    try:
        text = peers_path.read_text(encoding="utf-8")
        parser = getattr(_identity, "parse_peers_text", None)
        if parser is None:
            payload = json.loads(text) if text.strip() else {"peers": []}
        else:
            payload = parser(text)
    except Exception as exc:
        return False, "parse_error:{0}".format(type(exc).__name__), False

    peers = payload.get("peers", [])
    if not isinstance(peers, list):
        return False, "peers_not_list", False

    found = False
    was_already_revoked = False
    for row in peers:
        if isinstance(row, dict) and row.get("peer_id") == target_peer_id:
            found = True
            # PLAN-112-FOLLOWUP-federation-wire (PHASE2, Codex AC18) — accept
            # BOTH a Python bool (JSON payload) AND the raw scalar string the
            # canonical identity.parse_peers_text yields ("true"/"1"/"yes"),
            # mirroring load_peers' revoked semantics. Otherwise a repeat
            # revoke of a YAML-loaded peer mis-classifies the audit reason
            # (owner_directive vs owner_directive_repeat). State is correct
            # either way; this is forensic-accuracy only.
            _rev = row.get("revoked")
            if _rev is True or str(_rev).strip().lower() in ("true", "1", "yes"):
                was_already_revoked = True
            row["revoked"] = True
            row["revoked_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            break

    if not found:
        return False, "peer_not_found", False

    payload["peers"] = peers

    try:
        serialiser = getattr(_identity, "serialise_peers_payload", None)
        if serialiser is not None:
            out_bytes = serialiser(payload)
        else:
            out_bytes = json.dumps(
                payload, sort_keys=True, indent=2
            ).encode("utf-8")
    except Exception as exc:
        return False, "io_error:serialise:{0}".format(
            type(exc).__name__
        ), False

    # Same-directory tmpfile + fsync + rename (Wave B Codex P0 lesson).
    parent = peers_path.parent
    tmp_name = ".{0}.tmp.{1}.{2}".format(
        peers_path.name, os.getpid(), int(time.time() * 1e6)
    )
    tmp_path = parent / tmp_name

    fd = None
    try:
        fd = os.open(
            str(tmp_path),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC,
            0o600,
        )
        os.write(fd, out_bytes)
        os.fsync(fd)
    except OSError as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return False, "io_error:write:{0}".format(
            exc.errno or "unknown"
        ), False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    # F-002 fix: correct POSIX durability ordering is
    # tmpfile-write → tmpfile-fsync → close → os.rename → parent-dir-fsync.
    try:
        os.rename(str(tmp_path), str(peers_path))
    except OSError as exc:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return False, "io_error:rename:{0}".format(
            exc.errno or "unknown"
        ), False

    # Parent-directory fsync AFTER rename — persists the rename for
    # crash durability on POSIX.
    try:
        dir_fd = os.open(str(parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass

    return True, "revoked", was_already_revoked


# ----------------------------------------------------------------------------
# Handler entry point
# ----------------------------------------------------------------------------


def handle(
    peer_row: Mapping[str, Any],
    headers: Mapping[str, str],
    body: bytes,
    *,
    peers_path: Optional[Path] = None,
) -> Tuple[int, str, bytes]:
    """Top-level handler for POST /federation/peer-revoke.

    Gate #11. Gates #1-10 enforced by dispatcher. Gate #10 (Owner
    co-sign sentinel) is MANDATORY here — caller must verify before
    reaching this handler. Defense-in-depth: this handler does NOT
    re-check gate #10 (would mask a dispatcher gate-chain bug).
    """
    if peers_path is None:
        try:
            try:
                from _lib.federation import PEERS_FILE_DEFAULT  # type: ignore
            except ImportError:
                import importlib
                PEERS_FILE_DEFAULT = importlib.import_module(
                    "_lib.federation"
                ).PEERS_FILE_DEFAULT
            peers_path = Path(PEERS_FILE_DEFAULT)
        except Exception:
            peers_path = Path(".claude/data/federation/peers.yaml")

    try:
        parsed = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-revoke",
            gate_failed=11,
            reason_code="bad_body",
        )
        return 400, "bad_body", b'{"error":"bad_body"}'

    try:
        target = _validate_revoke_body(parsed)
    except PeerRevokeError as exc:
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-revoke",
            gate_failed=11,
            reason_code="schema:{0}".format(str(exc)[:24]),
        )
        return 400, "schema:{0}".format(str(exc)[:64]), b'{"error":"schema"}'

    ok, reason, was_already = _atomic_revoke_peer(peers_path, target)
    if not ok:
        if reason == "peer_not_found":
            _safe_emit(
                "federation_write_endpoint_denied",
                peer_id=str(peer_row.get("peer_id", ""))[:64],
                route="/federation/peer-revoke",
                gate_failed=11,
                reason_code="target_not_found",
            )
            return 404, reason, b'{"error":"peer_not_found"}'
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-revoke",
            gate_failed=11,
            reason_code="io_error:{0}".format(reason[:21]),
        )
        return 500, reason, b'{"error":"io"}'

    # F-001 R2 iter-2 fix: F.2 wrapper signature is
    # `emit_federation_peer_revoked_remote(peer_id,
    # revoked_by_origin_peer_id, reason_code)`. The TARGET peer is
    # what gets passed as `peer_id` (the revoked entity); the CALLER
    # who initiated the revocation is `revoked_by_origin_peer_id`.
    # `was_already_revoked` is dropped — repeated revocations are
    # idempotent forensic events, not failure cases.
    _safe_emit(
        "federation_peer_revoked_remote",
        peer_id=target[:64],
        revoked_by_origin_peer_id=str(peer_row.get("peer_id", ""))[:64],
        reason_code=(
            "owner_directive_repeat" if was_already else "owner_directive"
        ),
    )
    return 200, "ok", b'{"status":"revoked"}'
