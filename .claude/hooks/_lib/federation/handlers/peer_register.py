"""PLAN-099-FOLLOWUP Wave D.1 — /federation/peer-register handler.

PLAN-112-FOLLOWUP-federation-wire-or-delete:
  - W5: 90-day cert-validity-window enforcement (F-5.8). On peer-add the
    handler now parses not_valid_before/not_valid_after and rejects a
    window > MAX_CERT_VALIDITY_DAYS (90), emitting
    ``federation_cert_validity_window_too_large``. The ghost action gets a
    real producer.
  - C-4: ``_safe_emit`` falls back to ``emit_generic`` so the Wave-F.2
    actions (which have no named emit_* wrapper) are actually written.

## Scope (ADR-135-AMEND-1 §2.1 / D.1)

- Method: POST /federation/peer-register
- Scope name: ``peer_register`` (destructive — gate #10 Owner co-sign)
- Side-effect: append entry to peers.yaml
- Required peer body field: ``peer_id_spki_fingerprint`` (v2.0)

## Trust assumptions

This handler runs ONLY after the server dispatcher's 10 pre-gates
all passed. Handler MUST NOT re-verify those gates. Handler validates
ONLY the request body schema + executes the persistence side-effect.

## Atomic write protocol (Wave B Codex P0 lesson)

peers.yaml mutations follow the same-directory tmpfile + fsync +
os.rename pattern. Cross-filesystem rename is NOT atomic on POSIX.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple


__all__ = [
    "handle",
    "PeerRegisterError",
    "_validate_peer_body",
    "_atomic_append_peer",
    "MAX_CERT_VALIDITY_DAYS",
]


# PLAN-112-FOLLOWUP W5 — F-5.8 90-day cert-validity-window cap. Mirrors
# federation/__init__.MAX_CERT_VALIDITY_DAYS; duplicated here to keep the
# handler import-light (no federation package import at module init).
MAX_CERT_VALIDITY_DAYS = 90


# ----------------------------------------------------------------------------
# Audit emit shim (mirrors federation/server.py _safe_emit pattern)
# ----------------------------------------------------------------------------


def _safe_emit(action: str, **fields: Any) -> None:
    """Call ``audit_emit.emit_<action>(...)`` if registered; else fall
    back to ``audit_emit.emit_generic(action, ...)``; else no-op.

    PLAN-112-FOLLOWUP C-4 fix (R-TD-1): the Wave-F.2 federation actions
    are in ``_KNOWN_ACTIONS`` but have NO named ``emit_<action>`` wrapper,
    so the prior shim no-oped them. Falling back to ``emit_generic`` writes
    the event through the same filelock + HMAC chain. Unknown actions still
    no-op (emit_generic breadcrumbs).
    """
    try:
        try:
            from _lib import audit_emit  # type: ignore[import]
        except ImportError:
            import importlib
            audit_emit = importlib.import_module(".audit_emit", package="_lib")
    except ImportError:
        return
    fn_name = "emit_{0}".format(action)
    fn = getattr(audit_emit, fn_name, None)
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
                "[handlers.peer_register] audit emit '{0}' raised; ignored\n".format(
                    action
                )
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


_PEER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FPR_RE = re.compile(r"^[0-9A-Fa-f]{64}$")


class PeerRegisterError(ValueError):
    """Raised by ``_validate_peer_body`` on schema failure."""


class CertValidityWindowError(PeerRegisterError):
    """PLAN-112-FOLLOWUP W5 — cert validity window exceeds the 90-day cap.

    Distinct subclass so ``handle`` can emit the dedicated
    ``federation_cert_validity_window_too_large`` action (F-5.8) rather
    than the generic schema-fail path. Carries the offending window length.
    """

    def __init__(self, window_days: int) -> None:
        self.window_days = int(window_days)
        super().__init__(
            "cert_validity_window_too_large:{0}d".format(self.window_days)
        )


def _parse_iso_utc_loose(value: str) -> Optional[_dt.datetime]:
    """Parse an ISO-8601 UTC timestamp; trailing Z accepted. None on fail."""
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z") or raw.endswith("z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = _dt.datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        # Treat naive as UTC (the handler only validates a delta, not an
        # absolute instant, so tz-normalisation is sufficient).
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _validate_peer_body(body: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the new-peer request body. Returns the canonicalised row.

    Raises
    ------
    CertValidityWindowError
        (W5/F-5.8) when not_valid_after - not_valid_before > 90 days.
    PeerRegisterError
        On any other schema failure.
    """
    if not isinstance(body, Mapping):
        raise PeerRegisterError("body_not_object")

    required = (
        "peer_id",
        "peer_id_spki_fingerprint",
        "ca_pin_sha256",
        "not_valid_after",
        "not_valid_before",
        "hmac_secret_hex",
    )
    for fld in required:
        if fld not in body or body[fld] in (None, ""):
            raise PeerRegisterError("missing_field:{0}".format(fld))

    peer_id = str(body["peer_id"])
    if not _PEER_ID_RE.match(peer_id):
        raise PeerRegisterError("peer_id_charset")

    spki = str(body["peer_id_spki_fingerprint"]).lower()
    if not _FPR_RE.match(spki):
        raise PeerRegisterError("peer_id_spki_fingerprint_charset")

    ca_pin = str(body["ca_pin_sha256"]).lower()
    if not _FPR_RE.match(ca_pin):
        raise PeerRegisterError("ca_pin_sha256_charset")

    hmac_secret = str(body["hmac_secret_hex"]).lower()
    if not _FPR_RE.match(hmac_secret):
        raise PeerRegisterError("hmac_secret_hex_charset")

    nva = str(body["not_valid_after"])
    nvb = str(body["not_valid_before"])
    for label, candidate in (("not_valid_after", nva), ("not_valid_before", nvb)):
        if "\n" in candidate or "\r" in candidate or "\x00" in candidate:
            raise PeerRegisterError("{0}_charset".format(label))
        if len(candidate) < 19 or len(candidate) > 40:
            raise PeerRegisterError("{0}_length".format(label))

    # PLAN-112-FOLLOWUP W5 (F-5.8) — enforce the 90-day validity-window cap.
    # Parse BOTH timestamps; reject if not_valid_after <= not_valid_before
    # (mirrors load_peers) OR the window exceeds MAX_CERT_VALIDITY_DAYS.
    nva_dt = _parse_iso_utc_loose(nva)
    nvb_dt = _parse_iso_utc_loose(nvb)
    if nva_dt is None:
        raise PeerRegisterError("not_valid_after_unparseable")
    if nvb_dt is None:
        raise PeerRegisterError("not_valid_before_unparseable")
    if nva_dt <= nvb_dt:
        raise PeerRegisterError("not_valid_after_le_before")
    window_seconds = (nva_dt - nvb_dt).total_seconds()
    window_days = window_seconds / 86400.0
    if window_days > MAX_CERT_VALIDITY_DAYS:
        # The dedicated subclass triggers the F-5.8 emit in ``handle``.
        raise CertValidityWindowError(int(window_days))

    scopes_raw = body.get("scopes", [])
    if scopes_raw is None:
        scopes_raw = []
    if not isinstance(scopes_raw, (list, tuple)):
        raise PeerRegisterError("scopes_not_list")
    canonical_scopes: list = []
    seen_scope: set = set()
    for s in scopes_raw:
        if not isinstance(s, str):
            raise PeerRegisterError("scope_not_str")
        if not re.match(r"^[A-Za-z0-9_]{1,64}$", s):
            raise PeerRegisterError("scope_charset:{0}".format(s[:32]))
        if s not in seen_scope:
            seen_scope.add(s)
            canonical_scopes.append(s)

    row: Dict[str, Any] = {
        "peer_id": peer_id,
        "peer_id_spki_fingerprint": spki,
        "ca_pin_sha256": ca_pin,
        "not_valid_after": nva,
        "not_valid_before": nvb,
        "hmac_secret_hex": hmac_secret,
        "scopes": canonical_scopes,
        "revoked": False,
    }

    legacy_der = body.get("peer_id_cert_fingerprint")
    if legacy_der not in (None, ""):
        legacy_der_norm = str(legacy_der).lower()
        if not _FPR_RE.match(legacy_der_norm):
            raise PeerRegisterError("peer_id_cert_fingerprint_charset")
        row["peer_id_cert_fingerprint"] = legacy_der_norm

    kfva = body.get("key_floor_verified_at")
    if kfva not in (None, ""):
        kfva_s = str(kfva)
        if "\n" in kfva_s or "\r" in kfva_s or "\x00" in kfva_s:
            raise PeerRegisterError("key_floor_verified_at_charset")
        row["key_floor_verified_at"] = kfva_s

    return row


# ----------------------------------------------------------------------------
# Peers.yaml atomic mutation
# ----------------------------------------------------------------------------


def _load_peers_yaml(peers_path: Path) -> Dict[str, Any]:
    """Parse peers.yaml via the federation/identity load_peers path."""
    if not peers_path.exists():
        return {"peers": []}
    try:
        try:
            from _lib.federation import identity as _identity  # type: ignore
        except ImportError:
            import importlib
            _identity = importlib.import_module(
                "_lib.federation.identity"
            )
        raw_text = peers_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return {"peers": []}
        parser = getattr(_identity, "parse_peers_text", None)
        if parser is None:
            return json.loads(raw_text)
        return parser(raw_text)
    except Exception as exc:
        raise PeerRegisterError(
            "parse_error:{0}:{1}".format(type(exc).__name__, str(exc)[:96])
        )


def _serialise_peers_yaml(payload: Mapping[str, Any]) -> bytes:
    """Serialise ``{"peers": [...]}`` back to peers.yaml bytes."""
    try:
        try:
            from _lib.federation import identity as _identity  # type: ignore
        except ImportError:
            import importlib
            _identity = importlib.import_module(
                "_lib.federation.identity"
            )
        serialiser = getattr(_identity, "serialise_peers_payload", None)
        if serialiser is not None:
            return serialiser(payload)
    except ImportError:
        pass
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")


def _atomic_append_peer(
    peers_path: Path,
    new_row: Mapping[str, Any],
) -> Tuple[bool, str]:
    """Append new_row to peers.yaml atomically. Returns (ok, reason)."""
    peer_id = str(new_row.get("peer_id", ""))
    try:
        payload = _load_peers_yaml(peers_path)
    except PeerRegisterError as exc:
        return False, str(exc)

    peers = payload.get("peers", [])
    if not isinstance(peers, list):
        return False, "parse_error:peers_not_list"

    for existing in peers:
        if isinstance(existing, Mapping):
            if existing.get("peer_id") == peer_id:
                return False, "collision:{0}".format(peer_id)

    peers.append(dict(new_row))
    payload["peers"] = peers

    try:
        out_bytes = _serialise_peers_yaml(payload)
    except Exception as exc:
        return False, "io_error:serialise:{0}".format(type(exc).__name__)

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
        return False, "io_error:write:{0}".format(exc.errno or "unknown")
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass

    try:
        os.rename(str(tmp_path), str(peers_path))
    except OSError as exc:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        return False, "io_error:rename:{0}".format(exc.errno or "unknown")

    try:
        dir_fd = os.open(str(parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
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
    peers_path: Optional[Path] = None,
) -> Tuple[int, str, bytes]:
    """Top-level handler for POST /federation/peer-register (Gate #11)."""
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

    # 1. Parse JSON body.
    try:
        parsed = json.loads(body.decode("utf-8") if body else "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-register",
            gate_failed=11,
            reason_code="bad_body",
        )
        return 400, "bad_body", b'{"error":"bad_body"}'

    # 2. Validate schema (incl. W5 90d cert-window check).
    try:
        new_row = _validate_peer_body(parsed)
    except CertValidityWindowError as exc:
        # PLAN-112-FOLLOWUP W5 / F-5.8 — dedicated emit for the over-long
        # cert validity window. The ghost action now has a real producer.
        _safe_emit(
            "federation_cert_validity_window_too_large",
            peer_id=str(parsed.get("peer_id", ""))[:64]
            if isinstance(parsed, Mapping) else "",
            route="/federation/peer-register",
            window_days=int(exc.window_days),
            max_days=int(MAX_CERT_VALIDITY_DAYS),
        )
        return (
            400,
            "cert_validity_window_too_large:{0}d".format(exc.window_days),
            b'{"error":"cert_validity_window_too_large"}',
        )
    except PeerRegisterError as exc:
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-register",
            gate_failed=11,
            reason_code="schema:{0}".format(str(exc)[:24]),
        )
        return 400, "schema:{0}".format(str(exc)[:64]), b'{"error":"schema"}'

    # 3. Atomic append.
    ok, reason = _atomic_append_peer(peers_path, new_row)
    if not ok:
        if reason.startswith("collision:"):
            _safe_emit(
                "federation_peer_registered_collision",
                peer_id=new_row["peer_id"][:64],
                attempted_by_origin_peer_id=str(
                    peer_row.get("peer_id", "")
                )[:64],
            )
            return 409, reason, b'{"error":"peer_id_collision"}'
        _safe_emit(
            "federation_write_endpoint_denied",
            peer_id=str(peer_row.get("peer_id", ""))[:64],
            route="/federation/peer-register",
            gate_failed=11,
            reason_code="io_error:{0}".format(reason[:21]),
        )
        return 500, reason, b'{"error":"io"}'

    # 4. Success emit.
    _safe_emit(
        "federation_peer_registered",
        peer_id=new_row["peer_id"][:64],
        route="/federation/peer-register",
        scopes_count=int(len(new_row.get("scopes", []) or [])),
        spki_fingerprint_prefix=new_row["peer_id_spki_fingerprint"][:16],
    )
    return 200, "ok", b'{"status":"registered"}'
