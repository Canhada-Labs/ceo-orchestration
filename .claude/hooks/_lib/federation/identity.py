"""PLAN-099 Wave A.3 — peer identity primitives (stdlib only).

PLAN-099-FOLLOWUP Wave C extension — SPKI fingerprint primary pin
support added per peers-yaml-schema-migration.md §3 dispatcher
contract. Three new functions:

  - compute_spki_fingerprint(pem_bytes) — SHA-256 of SubjectPublicKeyInfo
    DER. Rotation-survives: key-preserving rotations preserve SPKI.
    Delegates to cert_inspector.inspect(...)['spki_sha256'].
  - compute_der_fingerprint_from_pem(pem_bytes) — SHA-256 of full DER
    cert. Convenience wrapper around the existing
    compute_der_fingerprint() (which takes already-decoded DER bytes).
    Delegates to cert_inspector.inspect(...)['der_sha256'] when the
    bridge is importable; falls back to ssl.PEM_cert_to_DER_cert
    when not (preserves stdlib-only invariant).
  - select_pin_for_peer(peer_row) — returns (pin_type, pin_value)
    where pin_type ∈ {"spki", "der"}. SPKI wins when present + non-
    empty; DER fallback when SPKI empty + DER non-empty; raises
    PinSelectionError when neither is set (parse-time invalid row).

The existing surfaces (compute_der_fingerprint, compute_cert_fingerprint,
compare_fingerprints, load_peers, verify_enable_sentinel_pair) are
preserved for backward-compat with PLAN-099 v1.32.0, with two
non-breaking extensions:

  1. ``PeerRecord`` now carries an OPTIONAL
     ``peer_id_spki_fingerprint`` field (default empty string). This
     resolves Codex Wave-C P0 F-001 (SPKI preservation through the
     real loaded registry — no more parallel `federation_peers_extra`
     dict required for SPKI dispatch). Constructors using positional
     args are unaffected because the new field has a default; keyword-
     arg constructors gain access by name. The field is documented
     under :class:`PeerRecord`.
  2. ``load_peers`` now accepts an v2.0 row with EITHER pin (the
     loader-side at-least-one invariant — Codex Wave-C P0 F-002). A
     row with NEITHER pin raises the specific subclass
     :class:`PeerHasNoFingerprintError` so the server-side wrapper
     can emit ``federation_peer_invalid_no_fingerprint`` (Codex
     Wave-C P0 F-003) before re-raising; generic schema violations
     continue to raise the parent :class:`PeersFileError` and route
     through the existing ``federation_connection_rejected`` path.

Implements the full-cert DER fingerprint identity primitive (AC4) +
peers.yaml loader + 2-stage Owner-GPG sentinel verification (AC22).

Identity primitive (S129 Codex R2 iter-3 fold — SPKI extraction is not
stdlib-feasible; full-cert DER fingerprint used instead. SPKI extraction
+ programmatic key-floor verification deferred to C1 crypto sidecar via
PLAN-099-FOLLOWUP):

    pem = ssl.get_server_certificate((host, port))
    der = ssl.PEM_cert_to_DER_cert(pem)   # bytes, NOT str
    fingerprint = hashlib.sha256(der).hexdigest()

Compared via :func:`hmac.compare_digest` against
``peers.yaml[peer].peer_id_cert_fingerprint``.

Sentinel verification is a TWO-STAGE composition per ADR-135 §Enable
protocol:

    ok, fpr, reason = verify_detached(signed, sig, allowlist_fprs=[OWNER_FPR])
    if not ok:
        return False  # fail-CLOSED with Stage-1 reason
    signer_ok, signer_reason = is_valid_signer(fpr, ...)
    if not signer_ok:
        return False  # fail-CLOSED with Stage-2 reason

Both stages fail-CLOSED on any error path.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import re
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = [
    "PeerRecord",
    "PeersFileError",
    "PeerHasNoFingerprintError",
    "compute_cert_fingerprint",
    "compute_der_fingerprint",
    "compute_der_fingerprint_from_pem",
    "compute_spki_fingerprint",
    "select_pin_for_peer",
    "PinSelectionError",
    "compare_fingerprints",
    "load_peers",
    "parse_peers_text",
    "serialise_peers_payload",
    "verify_enable_sentinel_pair",
    "SentinelVerifyError",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PeerRecord:
    """One row from ``peers.yaml``.

    Fields
    ------
    peer_id
        Short opaque identifier (e.g. ``"peer-east-01"``). Used for
        rate-limit keying + audit-chain tagging.
    peer_id_cert_fingerprint
        SHA-256 hex of the full-cert DER (lowercase, 64-hex). LEGACY
        v1.x pin. May be empty string when the row is a clean v2.0
        SPKI-only install. When non-empty, compared via
        :func:`hmac.compare_digest`.
    ca_pin_sha256
        SHA-256 hex of the issuing CA cert (lowercase, 64-hex). AC11
        cert-rotation discipline — CA pin survives cert rotation.
    not_valid_after
        UTC-aware datetime. The peer's certificate ``Not After`` field.
        Enforced ≤ ``MAX_CERT_VALIDITY_DAYS`` from ``not_valid_before``
        at peer-add time (AC11).
    not_valid_before
        UTC-aware datetime. The peer's certificate ``Not Before``.
    revoked
        ``True`` if peer is in the blocklist. Loaded fail-CLOSED on
        parse error (AC11 revocation channel).
    hmac_secret_hex
        Per-peer HMAC-SHA256 shared secret (32-byte = 64-hex). Used by
        :mod:`federation.replay` for request-binding signatures.
        Rotated alongside the cert.
    peer_id_spki_fingerprint
        Wave C (PLAN-099-FOLLOWUP) — SHA-256 hex of the cert's
        SubjectPublicKeyInfo DER (lowercase, 64-hex). PRIMARY v2.0 pin
        per ADR-129-AMEND-1 §3. May be empty string when the row is
        legacy v1.x (DER-only). When non-empty, dispatcher takes the
        SPKI path with NO downgrade to DER (Codex Wave-C P0 F-001).

        Schema invariant enforced by :func:`load_peers`: at least one
        of ``peer_id_spki_fingerprint`` or ``peer_id_cert_fingerprint``
        MUST be non-empty. A row violating that invariant raises
        :class:`PeerHasNoFingerprintError` at parse time.
    """

    peer_id: str
    peer_id_cert_fingerprint: str
    ca_pin_sha256: str
    not_valid_after: _dt.datetime
    not_valid_before: _dt.datetime
    revoked: bool = False
    hmac_secret_hex: str = ""
    # Wave C (PLAN-099-FOLLOWUP F-001/F-002) — SPKI primary pin, added
    # as the LAST keyword-with-default field to preserve positional-call
    # compatibility with PLAN-099 v1.32.0 baseline PeerRecord(...) sites.
    peer_id_spki_fingerprint: str = ""
    # PLAN-112-FOLLOWUP-federation-wire (PHASE2, F-1.7) — RBAC scopes +
    # per-action audit-push allowlist. Parsed by load_peers from peers.yaml
    # (inline flow-list "[a, b]" OR comma-separated "a,b" OR single scalar).
    # Empty default = read-only (natural default-OFF per ADR-135 Part 7;
    # Gate #6 peer_has_scope default-DENIES). Added as the LAST fields to
    # preserve positional PeerRecord(...) call-site compatibility.
    scopes: Tuple[str, ...] = ()
    audit_event_push_allowlist: Tuple[str, ...] = ()


class PeersFileError(ValueError):
    """Raised when peers.yaml cannot be parsed OR violates an invariant."""


class PeerHasNoFingerprintError(PeersFileError):
    """Subclass raised by :func:`load_peers` when a peer row has neither
    a SPKI nor a DER fingerprint pin.

    Wave C (PLAN-099-FOLLOWUP Codex P0 F-003) — distinguishable from
    the generic :class:`PeersFileError` so the server-side wrapper
    (``_load_peers_or_raise``) can emit
    ``federation_peer_invalid_no_fingerprint`` BEFORE re-raising. The
    generic ``PeersFileError`` continues to emit
    ``federation_connection_rejected``.

    Attributes
    ----------
    peer_id
        The offending row's ``peer_id`` (may be empty if the row also
        lacked a ``peer_id`` field).
    index
        Zero-based index of the row within ``peers.yaml[peers]``.
    """

    def __init__(self, message: str, peer_id: str = "", index: int = -1) -> None:
        super().__init__(message)
        self.peer_id = peer_id
        self.index = index


class SentinelVerifyError(Exception):
    """Internal helper — sentinel verification surface error.

    Callers should catch and convert to ``(False, reason)`` tuples; the
    public surface (:func:`verify_enable_sentinel_pair`) never raises.
    """


# Wave C (PLAN-099-FOLLOWUP) — Pin-selection surface
class PinSelectionError(ValueError):
    """Raised by :func:`select_pin_for_peer` when a peer row has neither
    a SPKI nor a DER fingerprint pin.

    Per ``peers-yaml-schema-migration.md`` §2.1 the v2.0 invariant
    requires AT LEAST ONE of {peer_id_spki_fingerprint,
    peer_id_cert_fingerprint} to be non-empty. A row violating that
    invariant should be rejected at parse time with
    ``federation_peer_invalid_no_fingerprint``; this exception is the
    runtime guard if the row somehow reaches the dispatcher.
    """


# ---------------------------------------------------------------------------
# Fingerprint primitives (AC4 stdlib downgrade per S129 iter-2/3 fold)
# ---------------------------------------------------------------------------


def compute_der_fingerprint(der_bytes: bytes) -> str:
    """SHA-256 hex of an already-decoded DER cert byte string.

    Returns 64-hex lowercase. The caller passes bytes from
    :func:`ssl.PEM_cert_to_DER_cert` (which returns ``bytes`` already —
    do NOT call ``.encode()`` on it).
    """
    if not isinstance(der_bytes, (bytes, bytearray)):
        raise TypeError(
            "compute_der_fingerprint expects bytes, got {0}".format(
                type(der_bytes).__name__
            )
        )
    return hashlib.sha256(bytes(der_bytes)).hexdigest()


def compute_cert_fingerprint(pem_text: str) -> str:
    """Compute the full-cert DER fingerprint from a PEM-encoded string.

    ``pem_text`` is a string returned by
    :func:`ssl.get_server_certificate` or read from a ``.pem`` file.
    The PEM → DER conversion uses :func:`ssl.PEM_cert_to_DER_cert`
    which returns ``bytes`` (NOT ``str``).
    """
    if not isinstance(pem_text, str):
        raise TypeError(
            "compute_cert_fingerprint expects str (PEM), got {0}".format(
                type(pem_text).__name__
            )
        )
    der_bytes = ssl.PEM_cert_to_DER_cert(pem_text)
    return compute_der_fingerprint(der_bytes)


def compare_fingerprints(a: str, b: str) -> bool:
    """Constant-time comparison of two fingerprint strings.

    Empty / mismatched-length inputs → ``False``. Comparison is via
    :func:`hmac.compare_digest` to defeat timing side-channels.
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    if not a or not b:
        return False
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a.lower(), b.lower())


# ---------------------------------------------------------------------------
# Wave C (PLAN-099-FOLLOWUP) — SPKI fingerprint primitives (delegates
# to cert_inspector bridge — stdlib-only contract preserved since the
# bridge fences the cryptography import behind a subprocess sidecar).
# ---------------------------------------------------------------------------


def _load_cert_inspector():
    """Lazy-import cert_inspector with dual-path resolution.

    Mirrors the idiom used in ``tools/migrate-peers-yaml.py`` —
    prefer the canonical landing path
    (``.claude/hooks/_lib/federation/cert_inspector.py``), fall back to
    the PLAN-099-FOLLOWUP staging path when the canonical file isn't
    in place yet (pre-Owner-Phase-A2-post `git mv`).

    Returns the imported module, or raises ImportError when neither
    location is available (the caller can degrade to PEM-only DER
    fingerprinting via ssl.PEM_cert_to_DER_cert).
    """
    # First try: relative-import sibling (post-canonical-mv).
    try:
        from . import cert_inspector as _ci  # type: ignore[import]
        return _ci
    except ImportError:
        pass
    # Second try: top-level federation namespace (test/draft context).
    try:
        from federation import cert_inspector as _ci  # type: ignore[import]
        return _ci
    except ImportError:
        pass
    # Third try: staging file under PLAN-099-FOLLOWUP/.
    import importlib.util
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    # When mv'd to _lib/federation/, parents: [federation, _lib, hooks,
    # .claude, <repo_root>].
    repo_root = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    staging = os.path.join(
        repo_root,
        ".claude", "plans", "PLAN-099-FOLLOWUP", "cert_inspector.py",
    )
    if os.path.isfile(staging):
        spec = importlib.util.spec_from_file_location(
            "cert_inspector_staging", staging
        )
        if spec is not None and spec.loader is not None:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise ImportError(
        "cert_inspector unavailable at canonical or staging path"
    )


def compute_spki_fingerprint(pem_bytes: bytes) -> str:
    """Compute SHA-256 of SPKI (SubjectPublicKeyInfo) DER of the cert.

    Wave C (PLAN-099-FOLLOWUP) — SPKI is the v2.0 primary pin per
    ``peers-yaml-schema-migration.md`` §3 + ADR-129-AMEND-1 §3.

    Rotation-survives invariant: when a peer rotates its certificate
    WITHOUT changing the underlying public key (the common case for
    expiry-driven re-signing), the SPKI SHA-256 is preserved. The
    full-cert DER fingerprint, by contrast, changes with every
    rotation (different serial / validity window / signature). SPKI
    pinning therefore avoids forced peers.yaml edits on every cert
    rotation.

    Delegates to :func:`cert_inspector.inspect` and reads the
    ``spki_sha256`` field of its 12-field report. The bridge handles
    sidecar-vs-openssl-fallback dispatch internally; this function
    stays stdlib-only by importing only the bridge (which is itself
    stdlib-only per ADR-126 §Part 2).

    Parameters
    ----------
    pem_bytes
        PEM-encoded certificate as ``bytes`` (e.g. file contents read
        in binary mode, or `pem_str.encode("ascii")`).

    Returns
    -------
    str
        64-hex lowercase SHA-256 of the SPKI DER.

    Raises
    ------
    TypeError
        If ``pem_bytes`` is not ``bytes`` or ``bytearray``.
    ValueError
        If the cert_inspector report's ``spki_sha256`` is empty (the
        openssl fallback path on older libressl <3.5 can fail SPKI
        extraction — caller MUST handle this branch when the bridge
        is in openssl-fallback mode without a sidecar). The error
        message includes the bridge's ``error`` field for diagnosis.
    ImportError
        If neither the canonical nor staging cert_inspector is
        available. Callers in adopter installs that haven't run the
        v1.39.1 ceremony yet will see this — the dispatcher should
        treat it as a fail-CLOSED condition.
    """
    if not isinstance(pem_bytes, (bytes, bytearray)):
        raise TypeError(
            "compute_spki_fingerprint expects bytes, got {0}".format(
                type(pem_bytes).__name__
            )
        )
    ci = _load_cert_inspector()
    rep = ci.inspect(cert_pem_bytes=bytes(pem_bytes))
    spki = rep.get("spki_sha256", "") or ""
    if not (isinstance(spki, str) and len(spki) == 64):
        err = rep.get("error") or "spki extraction returned empty"
        raise ValueError(
            "compute_spki_fingerprint: bridge returned malformed "
            "spki_sha256 (len={0}); bridge error={1!r}".format(
                len(spki), err,
            )
        )
    return spki.lower()


def compute_der_fingerprint_from_pem(pem_bytes: bytes) -> str:
    """Compute SHA-256 of the full DER-encoded cert (legacy v1.x pin).

    Wave C (PLAN-099-FOLLOWUP) — convenience wrapper for symmetry with
    :func:`compute_spki_fingerprint`. Functionally equivalent to
    ``compute_der_fingerprint(ssl.PEM_cert_to_DER_cert(pem_str))`` but
    operates on ``bytes`` input (matching the cert_inspector bridge
    contract) and delegates to the bridge when available for parity
    with the v2.0 dispatcher path (so SPKI + DER fingerprints come
    from the SAME parse — important for the rotation-survives
    invariant test where SPKI is shared across cert versions but DER
    differs).

    Falls back to ``ssl.PEM_cert_to_DER_cert`` when the bridge is
    unavailable (preserves stdlib-only invariant; same byte-stable
    output as the bridge's ``der_sha256``).

    Parameters
    ----------
    pem_bytes
        PEM-encoded certificate as ``bytes``.

    Returns
    -------
    str
        64-hex lowercase SHA-256 of the full DER cert.

    Raises
    ------
    TypeError
        If ``pem_bytes`` is not ``bytes`` or ``bytearray``.
    ValueError
        If the PEM cannot be decoded to DER (malformed input).
    """
    if not isinstance(pem_bytes, (bytes, bytearray)):
        raise TypeError(
            "compute_der_fingerprint_from_pem expects bytes, got {0}".format(
                type(pem_bytes).__name__
            )
        )
    # Try bridge first for parity with SPKI computation path.
    try:
        ci = _load_cert_inspector()
        rep = ci.inspect(cert_pem_bytes=bytes(pem_bytes))
        der = rep.get("der_sha256", "") or ""
        if isinstance(der, str) and len(der) == 64:
            return der.lower()
    except ImportError:
        pass
    except Exception:
        # Any bridge failure → fall through to ssl-only path. The
        # ssl path is byte-stable and identical to the bridge's
        # der_sha256 (both hash the same DER bytes).
        pass
    # Stdlib fallback (PLAN-099 v1.32.0 baseline behaviour).
    try:
        pem_str = bytes(pem_bytes).decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "compute_der_fingerprint_from_pem: PEM bytes must be ASCII: {0}".format(exc)
        )
    try:
        der_bytes = ssl.PEM_cert_to_DER_cert(pem_str)
    except (ValueError, ssl.SSLError) as exc:
        raise ValueError(
            "compute_der_fingerprint_from_pem: malformed PEM: {0}".format(exc)
        )
    return compute_der_fingerprint(der_bytes)


def select_pin_for_peer(peer_row: Dict[str, str]) -> Tuple[str, str]:
    """Return ``(pin_type, pin_value)`` from a peers.yaml v2.0 row.

    Wave C (PLAN-099-FOLLOWUP) — dispatcher helper. Implements the
    pin-priority contract from ``peers-yaml-schema-migration.md`` §3:

    1. ``peer_id_spki_fingerprint`` non-empty → ``("spki", value)``
       (primary pin; DER NOT consulted — no downgrade).
    2. ``peer_id_cert_fingerprint`` non-empty → ``("der", value)``
       (legacy v1.x fallback; emits ``federation_pin_legacy_used``
       on every handshake — see server.py dispatcher).
    3. Neither → raise :class:`PinSelectionError`.

    The caller (server.py / client.py dispatcher) compares the
    returned ``pin_value`` against the presented cert's
    corresponding fingerprint via :func:`compare_fingerprints`.

    Empty-string and whitespace-only values are treated as missing
    (the v2.0 schema allows an empty-string SPKI field during
    migration; that MUST NOT match an empty presented fingerprint).

    Parameters
    ----------
    peer_row
        A dict shaped like a ``peers.yaml`` row (e.g. a
        :class:`PeerRecord` converted via ``dataclasses.asdict`` OR a
        raw row from the schema-migration tool). Reads
        ``peer_id_spki_fingerprint`` and ``peer_id_cert_fingerprint``
        keys.

    Returns
    -------
    (pin_type, pin_value)
        ``pin_type`` is ``"spki"`` or ``"der"``. ``pin_value`` is the
        normalised lowercase 64-hex fingerprint.

    Raises
    ------
    PinSelectionError
        Neither pin is present + non-empty.
    """
    if not isinstance(peer_row, dict):
        raise PinSelectionError(
            "select_pin_for_peer: peer_row must be dict, got {0}".format(
                type(peer_row).__name__
            )
        )
    spki_raw = peer_row.get("peer_id_spki_fingerprint", "") or ""
    if not isinstance(spki_raw, str):
        spki_raw = ""
    spki = spki_raw.strip().lower()
    if spki:
        return ("spki", spki)
    der_raw = peer_row.get("peer_id_cert_fingerprint", "") or ""
    if not isinstance(der_raw, str):
        der_raw = ""
    der = der_raw.strip().lower()
    if der:
        return ("der", der)
    raise PinSelectionError(
        "select_pin_for_peer: peer row has neither peer_id_spki_fingerprint "
        "nor peer_id_cert_fingerprint set (peer_id={0!r})".format(
            peer_row.get("peer_id", "<missing>"),
        )
    )


# ---------------------------------------------------------------------------
# peers.yaml loader (minimal subset YAML — mirrors sentinel_signers pattern)
# ---------------------------------------------------------------------------


_PEER_FPR_RE = re.compile(r"^[0-9a-f]{64}$")
_PEER_ID_RE = re.compile(r"^[A-Za-z0-9_\-.]{1,64}$")
_HMAC_SECRET_RE = re.compile(r"^[0-9a-f]{64}$")
# PLAN-112-FOLLOWUP-federation-wire (PHASE2) — RBAC scope-name + allowlist
# charset. Strict alnum+underscore (mirrors scopes._SCOPE_NAME_RE) so a
# CR/LF/NUL/path-traversal token can never smuggle into the RBAC layer at
# parse time. Allowlist entries (audit action names) may be longer.
_SCOPE_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_ALLOWLIST_ENTRY_RE = re.compile(r"^[A-Za-z0-9_]{1,128}$")


def _normalise_hex_lower(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value).lower()
    return cleaned


def _parse_iso_utc(value: str) -> _dt.datetime:
    """Parse an ISO-8601 datetime into UTC-aware. Naive input rejected."""
    raw = value.strip().strip('"').strip("'")
    if not raw:
        raise PeersFileError("empty datetime value")
    candidate = raw
    if candidate.endswith("Z") or candidate.endswith("z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = _dt.datetime.fromisoformat(candidate)
    except ValueError as e:
        raise PeersFileError(
            "malformed datetime: {0!r} ({1})".format(raw, e)
        )
    if parsed.tzinfo is None:
        raise PeersFileError(
            "naive datetime not allowed: {0!r}".format(raw)
        )
    return parsed.astimezone(_dt.timezone.utc)


def _strip_comment(line: str) -> str:
    out: List[str] = []
    in_s = False
    in_d = False
    for ch in line:
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and (
        (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")
    ):
        return v[1:-1]
    return v


def _parse_inline_str_list(raw, field, idx, entry_re):
    """Parse a peers.yaml inline list field into a validated tuple.

    The minimal line-parser captures the value as one scalar string;
    this accepts flow-style ``[a, b, c]`` OR comma-separated ``a,b,c``
    OR a single scalar ``a``. Empty / absent -> ``()``. Order-preserving
    with de-duplication. Every token MUST match ``entry_re`` — a
    malformed RBAC grant raises :class:`PeersFileError` (fail-CLOSED: the
    server refuses to start rather than silently dropping a scope, which
    would be a silent authz weakening).
    """
    s = (raw or "").strip()
    if not s:
        return ()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    out = []
    seen = set()
    for tok in s.split(","):
        tok = tok.strip().strip('"').strip("'").strip()
        if not tok:
            continue
        if not entry_re.match(tok):
            raise PeersFileError(
                "peers[{0}].{1} invalid token {2!r} (must match {3})".format(
                    idx, field, tok, entry_re.pattern
                )
            )
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return tuple(out)


def _parse_peers_raw(text):
    """Parse peers.yaml text into a list of raw row dicts (NO validation).

    Shared by :func:`load_peers` (which then validates + builds
    :class:`PeerRecord`) and :func:`parse_peers_text` (the write-handler
    round-trip bridge). Minimal line-based YAML subset: top-level
    ``peers:`` then ``- key: value`` list items with ``  key: value``
    continuation fields. Raises :class:`PeersFileError` on a malformed line.
    """
    peers_raw: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    in_peers = False
    list_item_indent: Optional[int] = None

    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        if line.startswith("peers:") and not line.strip().startswith("- "):
            in_peers = True
            continue

        if not in_peers:
            # Anything before `peers:` is ignored (allows top-level
            # comments / version pin / metadata).
            continue

        item_match = re.match(r"^(\s*)-\s+(.*)$", line)
        if item_match:
            indent = len(item_match.group(1))
            if list_item_indent is None:
                list_item_indent = indent
            elif indent != list_item_indent:
                raise PeersFileError(
                    "list-item indent drift at line {0}".format(lineno)
                )
            current = {}
            peers_raw.append(current)
            inner = item_match.group(2)
            if ":" in inner:
                k, _, v = inner.partition(":")
                k = k.strip()
                if not k:
                    raise PeersFileError(
                        "empty key on list-item line {0}".format(lineno)
                    )
                current[k] = _unquote(v.strip())
            continue

        # Field of current list item ("  key: value" indented past list_item).
        kv_match = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$", line)
        if kv_match and current is not None and list_item_indent is not None:
            key_indent = len(kv_match.group(1))
            if key_indent <= list_item_indent:
                raise PeersFileError(
                    "list-item field at line {0} not indented past list marker".format(
                        lineno
                    )
                )
            key = kv_match.group(2)
            value = _unquote(kv_match.group(3))
            current[key] = value
            continue

        raise PeersFileError(
            "unparseable line {0}: {1!r}".format(lineno, raw_line)
        )
    return peers_raw


def load_peers(path: Path) -> Dict[str, PeerRecord]:
    """Parse peers.yaml into ``{peer_id: PeerRecord}``.

    Fail-CLOSED contract:

    - File missing → :class:`FileNotFoundError` (caller blocks server start).
    - Parse error / invariant violation → :class:`PeersFileError`.

    Supported YAML shape::

        peers:
          - peer_id: peer-east-01
            peer_id_cert_fingerprint: "abc...64hex"
            ca_pin_sha256: "def...64hex"
            not_valid_after: "2027-01-01T00:00:00Z"
            not_valid_before: "2026-01-01T00:00:00Z"
            revoked: false
            hmac_secret_hex: "012...64hex"
    """
    if not path.exists():
        raise FileNotFoundError(str(path))
    text = path.read_text(encoding="utf-8")

    peers_raw = _parse_peers_raw(text)

    out: Dict[str, PeerRecord] = {}
    for idx, row in enumerate(peers_raw):
        # Wave C (PLAN-099-FOLLOWUP F-001/F-002): peer_id_cert_fingerprint
        # is NO LONGER unconditionally required. The new invariant is
        # "at least one of {peer_id_spki_fingerprint, peer_id_cert_fingerprint}
        # MUST be non-empty" — enforced below after the structural
        # fields are validated.
        required = ("peer_id", "ca_pin_sha256",
                    "not_valid_after", "not_valid_before")
        for fld in required:
            if fld not in row or not row[fld]:
                raise PeersFileError(
                    "peers[{0}] missing required field {1!r}".format(idx, fld)
                )

        peer_id = row["peer_id"].strip()
        if not _PEER_ID_RE.match(peer_id):
            raise PeersFileError(
                "peers[{0}].peer_id invalid: {1!r}".format(idx, peer_id)
            )

        # Wave C: read BOTH pins; either or both may be present.
        spki_raw = (row.get("peer_id_spki_fingerprint", "") or "").strip()
        der_raw = (row.get("peer_id_cert_fingerprint", "") or "").strip()

        # At-least-one invariant (F-002 / F-003). A row with neither
        # raises the SPECIFIC subclass so the server can emit
        # federation_peer_invalid_no_fingerprint before re-raising.
        if not spki_raw and not der_raw:
            raise PeerHasNoFingerprintError(
                "peers[{0}] missing fingerprints: at least one of "
                "peer_id_spki_fingerprint or peer_id_cert_fingerprint "
                "MUST be non-empty (peer_id={1!r})".format(idx, peer_id),
                peer_id=peer_id,
                index=idx,
            )

        # Validate whichever pin(s) are present.
        spki_fpr = ""
        if spki_raw:
            spki_fpr = _normalise_hex_lower(spki_raw)
            if not _PEER_FPR_RE.match(spki_fpr):
                raise PeersFileError(
                    "peers[{0}].peer_id_spki_fingerprint not 64-hex: {1!r}".format(
                        idx, spki_raw
                    )
                )

        der_fpr = ""
        if der_raw:
            der_fpr = _normalise_hex_lower(der_raw)
            if not _PEER_FPR_RE.match(der_fpr):
                raise PeersFileError(
                    "peers[{0}].peer_id_cert_fingerprint not 64-hex: {1!r}".format(
                        idx, der_raw
                    )
                )

        ca_pin = _normalise_hex_lower(row["ca_pin_sha256"])
        if not _PEER_FPR_RE.match(ca_pin):
            raise PeersFileError(
                "peers[{0}].ca_pin_sha256 not 64-hex: {1!r}".format(
                    idx, row["ca_pin_sha256"]
                )
            )

        try:
            not_after = _parse_iso_utc(row["not_valid_after"])
            not_before = _parse_iso_utc(row["not_valid_before"])
        except PeersFileError as e:
            raise PeersFileError("peers[{0}]: {1}".format(idx, e))

        if not_after <= not_before:
            raise PeersFileError(
                "peers[{0}] not_valid_after <= not_valid_before".format(idx)
            )

        revoked_raw = row.get("revoked", "false")
        revoked = str(revoked_raw).strip().lower() in ("true", "1", "yes")

        hmac_raw = row.get("hmac_secret_hex", "").strip()
        if hmac_raw:
            hmac_hex = _normalise_hex_lower(hmac_raw)
            if not _HMAC_SECRET_RE.match(hmac_hex):
                raise PeersFileError(
                    "peers[{0}].hmac_secret_hex not 64-hex".format(idx)
                )
        else:
            hmac_hex = ""

        # PLAN-112-FOLLOWUP-federation-wire (PHASE2, F-1.7) — RBAC scopes +
        # per-action audit-push allowlist. Without this Gate #6
        # (scopes.peer_has_scope) default-DENIES every peer because the
        # reloaded peer_row["scopes"] was always [].
        scopes = _parse_inline_str_list(
            row.get("scopes", ""), "scopes", idx, _SCOPE_NAME_RE
        )
        audit_allowlist = _parse_inline_str_list(
            row.get("audit_event_push_allowlist", ""),
            "audit_event_push_allowlist", idx, _ALLOWLIST_ENTRY_RE,
        )

        if peer_id in out:
            raise PeersFileError(
                "duplicate peer_id {0!r} (peers[{1}])".format(peer_id, idx)
            )

        # Wave C F-001: PeerRecord now carries BOTH pins. Downstream
        # dispatch reads peer.peer_id_spki_fingerprint directly — no
        # parallel federation_peers_extra dict lookup required for SPKI
        # match. (federation_peers_extra still exists in server_full.py
        # as the carry for v2.0-only fields like scopes / RBAC, set by
        # Wave D.)
        out[peer_id] = PeerRecord(
            peer_id=peer_id,
            peer_id_cert_fingerprint=der_fpr,
            ca_pin_sha256=ca_pin,
            not_valid_after=not_after,
            not_valid_before=not_before,
            revoked=revoked,
            hmac_secret_hex=hmac_hex,
            peer_id_spki_fingerprint=spki_fpr,
            scopes=scopes,
            audit_event_push_allowlist=audit_allowlist,
        )

    return out


def parse_peers_text(text):
    """Parse peers.yaml text into a mutable ``{"peers": [row_dict, ...]}``.

    PLAN-112-FOLLOWUP-federation-wire (PHASE2, F-1.7) — the write handlers
    (``peer_register`` / ``peer_revoke``) need to round-trip the on-disk
    peers.yaml: parse -> mutate -> :func:`serialise_peers_payload`. Before
    this existed the handlers fell back to ``json.loads`` (which fails on the
    real YAML format :func:`load_peers` reads), so the destructive write
    endpoints were not adopter-functional against a deployed peers.yaml.
    Returns the RAW row dicts (string values; NO PeerRecord validation) so a
    caller can flip ``revoked`` / append a row and re-serialise; the server's
    :func:`load_peers` re-validates on the next reload.
    """
    return {"peers": _parse_peers_raw(text or "")}


def _render_peers_scalar(value):
    """Render one peers.yaml scalar for :func:`serialise_peers_payload`.

    ``None`` -> skip (returns None). bool -> ``true``/``false`` (unquoted, so
    :func:`load_peers` reads it via the truthy set). list/tuple -> flow
    ``[a, b]`` (read back by ``_parse_inline_str_list``). int/float -> bare.
    str -> double-quoted (ISO timestamps carry ``:`` so MUST be quoted; quotes
    are stripped by ``_unquote`` on parse-back). Embedded quotes are dropped
    (controlled values: ids / 64-hex / ISO ts / alnum_ scope-names).
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(x) for x in value) + "]"
    if isinstance(value, (int, float)):
        return str(value)
    return '"{0}"'.format(str(value).replace('"', ""))


def serialise_peers_payload(payload):
    """Serialise ``{"peers": [row_dict, ...]}`` to peers.yaml BYTES.

    Round-trips through :func:`load_peers`: each row emits ``peer_id`` first on
    the ``  - `` list-item line (the loader keys off the first field), then the
    remaining fields as ``    key: value`` continuations. Unknown keys (e.g.
    ``revoked_at`` written by peer_revoke) are preserved verbatim. The output
    is parseable by both :func:`load_peers` and :func:`parse_peers_text`.
    """
    peers = []
    if isinstance(payload, dict):
        raw = payload.get("peers", [])
        if isinstance(raw, list):
            peers = raw
    lines = ["peers:"]
    for row in peers:
        if not isinstance(row, dict):
            continue
        ordered = (["peer_id"] if "peer_id" in row else []) + [
            k for k in row.keys() if k != "peer_id"
        ]
        first = True
        for k in ordered:
            rendered = _render_peers_scalar(row[k])
            if rendered is None:
                continue
            lines.append(
                "{0}{1}: {2}".format("  - " if first else "    ", k, rendered)
            )
            first = False
    return ("\n".join(lines) + "\n").encode("utf-8")



def lookup_peer_by_fingerprint(
    peers: Dict[str, PeerRecord],
    fingerprint: str,
) -> Optional[PeerRecord]:
    """Find a (non-revoked) peer by full-cert DER fingerprint.

    Returns ``None`` if no peer matches OR the matching peer is
    ``revoked=True``. Uses :func:`compare_fingerprints` for constant-time
    comparison.

    Wave C note: SPKI-only peers (v2.0 clean install) have an empty
    ``peer_id_cert_fingerprint`` and are intentionally NOT matchable by
    this legacy lookup. The SPKI-aware dispatcher in
    ``server._resolve_peer`` covers them; this function remains the
    DER-only legacy lookup for back-compat with PLAN-099 v1.32.0
    callers (none of which need SPKI semantics).
    """
    if not fingerprint:
        return None
    target = _normalise_hex_lower(fingerprint)
    for peer in peers.values():
        if peer.revoked:
            continue
        # Skip SPKI-only peers (empty DER pin) — they cannot match the
        # DER fingerprint being queried by definition.
        if not peer.peer_id_cert_fingerprint:
            continue
        if compare_fingerprints(peer.peer_id_cert_fingerprint, target):
            return peer
    return None


# ---------------------------------------------------------------------------
# Owner-GPG sentinel pair verification (AC22 two-stage composition)
# ---------------------------------------------------------------------------


def verify_enable_sentinel_pair(
    signed_path: Path,
    signature_path: Path,
    allowlist_fprs: List[str],
    signer_registry_path: Optional[Path] = None,
    now: Optional[_dt.datetime] = None,
) -> Tuple[bool, str]:
    """Verify a detached-signature Owner-GPG sentinel pair (2-stage).

    Stage 1 — :func:`_lib.gpg_verify.verify_detached`:
        Cryptographic GOODSIG + VALIDSIG check via ``gpg --verify``.
        Cross-checks the recovered signer fpr against ``allowlist_fprs``
        (which MUST contain at least the Owner fingerprint
        ``00000000...``).

    Stage 2 — :func:`_lib.sentinel_signers.is_valid_signer`:
        Registry-driven expiry / revocation check for the recovered
        fpr per ADR-121.

    Returns
    -------
    (ok, reason)
        ``ok=True`` only if BOTH stages pass.
        ``reason`` is empty on success, otherwise either the Stage-1
        ``verify_detached`` reason verbatim, OR
        ``signer_invalid:<stage-2 reason>`` for Stage 2 failures.

    Never raises. All error paths return ``(False, reason)``.

    The caller is expected to emit ``federation_enable_sentinel_invalid``
    audit on a False return.
    """
    # Lazy imports — works pre + post canonical ceremony (HMAC libs may
    # not be wired in adopter installs that haven't run install.sh yet).
    try:
        # Both modules live in `_lib/`. We deliberately import via the
        # package qualifier so this module is portable to test contexts
        # that import the helpers under a different namespace.
        try:
            from _lib import gpg_verify as _gpg_verify  # type: ignore[import]
            from _lib import sentinel_signers as _signers  # type: ignore[import]
        except ImportError:
            # Fall back to the dotted name for pytest invocations from repo root.
            import importlib
            _gpg_verify = importlib.import_module(".gpg_verify", package="_lib")
            _signers = importlib.import_module(".sentinel_signers", package="_lib")
    except ImportError as e:
        return False, "gpg_verify_unavailable:{0}".format(type(e).__name__)

    try:
        ok, fpr, reason = _gpg_verify.verify_detached(
            signed_path,
            signature_path,
            allowlist_fprs=allowlist_fprs,
        )
    except Exception as e:  # noqa: BLE001 — defense-in-depth
        return False, "verify_detached_exception:{0}".format(type(e).__name__)

    if not ok:
        return False, reason or "verify_detached_failed"

    # Stage 2 — registry validity check. If a registry path is provided,
    # load it and consult is_valid_signer; otherwise pass an empty
    # registry which means "every key unknown" — fail-CLOSED.
    registry: Dict[str, "_signers.SignerRecord"] = {}
    if signer_registry_path is not None:
        try:
            registry = _signers.load_registry(signer_registry_path)
        except FileNotFoundError:
            return False, "signer_invalid:registry_missing"
        except Exception as e:  # noqa: BLE001
            return False, "signer_invalid:registry_parse_error:{0}".format(
                type(e).__name__
            )

    try:
        signer_ok, signer_reason = _signers.is_valid_signer(
            fpr, now=now, registry=registry,
        )
    except Exception as e:  # noqa: BLE001
        return False, "signer_invalid:is_valid_signer_exception:{0}".format(
            type(e).__name__
        )

    if not signer_ok:
        return False, "signer_invalid:{0}".format(signer_reason)

    return True, ""
