"""PLAN-089 Wave C.2 — sentinel signers verification primitives.

See ADR-121 for policy. This module provides PURE primitives — it does
not perform GPG signature verification (delegated to upstream callers
via `_lib/gpg_verify.py`); it gates the list cardinality + signer
validity (expiry, revocation, key-type).

## Surface

- :class:`SignerRecord` — one row from the registry YAML.
- :class:`Signature` — one detached signature reference (already
  GPG-verified upstream); fed into :func:`quorum_verify` for cardinality
  + signer-validity gating.
- :func:`load_registry` — parses `sentinel-signers-registry.yaml`
  (manual subset-YAML parser, JSON fallback).
- :func:`is_valid_signer` — single-signer validity check (expiry,
  revocation, registry membership).
- :func:`quorum_verify` — N-of-M cold-key cardinality + distinct-signer
  + validity gate.

## Hot vs cold

- ``hot``: signs ordinary canonical-edit sentinels.
- ``cold``: signs REGISTRY MUTATIONS + EMERGENCY RECOVERY only.
  Cold-key quorum (M-of-N, typically 2-of-3) gates registry rotation.

:func:`quorum_verify` enforces:
  1. all signatures map to registry entries with ``key_type == "cold"``;
  2. each signer is valid at ``now`` (not expired, not revoked);
  3. signers are DISTINCT (duplicate-signer collusion test, R1 IDA P1
     fold — even though deferred to execution-time per plan §14, fold
     it inline NOW so the primitive is correct from day one);
  4. number of distinct valid cold-key signatures >= ``threshold``.

## Stdlib-only (ADR-002)

Uses :mod:`datetime`, :mod:`json`, :mod:`re`, :mod:`pathlib`. No PyYAML.
The YAML parser handles the documented registry shape (top-level
``signers:`` list of mappings with scalar fields + ``notes`` string).
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "SignerRecord",
    "Signature",
    "RegistryParseError",
    "load_registry",
    "is_valid_signer",
    "quorum_verify",
]


# --- Dataclasses -----------------------------------------------------------


@dataclass
class SignerRecord:
    """One registry row.

    Fields
    ------
    key_id
        40-hex-uppercase GPG primary-key fingerprint.
    key_type
        ``"hot"`` or ``"cold"``.
    created_at
        Timezone-aware datetime (UTC) when the key was registered.
    expires_at
        Timezone-aware datetime (UTC) of policy-driven expiry. STRICT
        ``>`` boundary — at exactly ``expires_at`` the key is expired.
    revoked_at
        ``None`` if the key has not been revoked. A timezone-aware
        datetime if revoked. Revocation takes precedence over expiry
        (revoked-AND-expired key reports ``reason="revoked"``).
    notes
        Free-form audit string. Default ``""``.
    """

    key_id: str
    key_type: str
    created_at: _dt.datetime
    expires_at: _dt.datetime
    revoked_at: Optional[_dt.datetime] = None
    notes: str = ""


@dataclass
class Signature:
    """One detached-signature reference.

    ``sig_bytes`` is opaque — actual GPG verification is delegated to
    :mod:`_lib.gpg_verify`. This dataclass just carries the bytes for
    forensic/audit purposes; :func:`quorum_verify` ignores them and
    gates only on ``key_id`` + registry validity.
    """

    key_id: str
    sig_bytes: bytes = b""


# --- Errors ----------------------------------------------------------------


class RegistryParseError(ValueError):
    """Raised when the registry file cannot be parsed (YAML + JSON both
    failed) OR when the parsed registry violates an integrity invariant
    (duplicate signers, missing required field, malformed timestamp)."""


# --- Internal helpers ------------------------------------------------------


_FPR_RE = re.compile(r"^[0-9A-F]{40}$")
_LIST_ITEM_RE = re.compile(r"^(\s*)-\s+(.*)$")
_KV_RE = re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$")


def _strip_comment(line: str) -> str:
    """Strip `# comment` trailing portion respecting simple quoted strings."""
    out: List[str] = []
    in_single = False
    in_double = False
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _unquote(value: str) -> str:
    """Unquote a YAML scalar; passthrough if not quoted."""
    v = value.strip()
    if len(v) >= 2 and (
        (v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")
    ):
        return v[1:-1]
    return v


def _parse_datetime(value: str) -> _dt.datetime:
    """Parse an ISO-8601 datetime string into a UTC-aware datetime.

    Accepts both ``2026-05-13T00:00:00+00:00`` and the bare ``Z`` suffix
    (``2026-05-13T00:00:00Z``). Naive input is rejected (raises
    :class:`RegistryParseError`).
    """
    raw = _unquote(value).strip()
    if not raw:
        raise RegistryParseError("empty datetime value")
    candidate = raw
    if candidate.endswith("Z") or candidate.endswith("z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = _dt.datetime.fromisoformat(candidate)
    except ValueError as e:
        raise RegistryParseError(
            "malformed datetime: {0!r} ({1})".format(raw, e)
        )
    if parsed.tzinfo is None:
        raise RegistryParseError(
            "naive datetime not allowed: {0!r}".format(raw)
        )
    return parsed.astimezone(_dt.timezone.utc)


def _normalize_key_id(value: str) -> str:
    """Canonicalize a fingerprint (strip whitespace, uppercase, validate)."""
    cleaned = re.sub(r"\s+", "", _unquote(value)).upper()
    if not _FPR_RE.match(cleaned):
        raise RegistryParseError(
            "invalid key_id (expect 40-hex): {0!r}".format(value)
        )
    return cleaned


def _parse_minimal_yaml(text: str) -> Any:
    """Parse the documented subset of YAML used by the signers registry.

    Supported shape::

        # comment
        signers:
          - key_id: ABC...
            key_type: hot
            created_at: 2026-05-13T00:00:00Z
            expires_at: 2027-05-13T00:00:00Z
            revoked_at: null
            notes: "Owner - original hot key"

    Limitations (documented):

    - Only one level of list nesting (``- key: value`` inside a
      ``signers:`` block).
    - No flow style (``[a, b, c]`` / ``{k: v}``).
    - No anchors / aliases / multi-doc.
    - Scalars are strings; ``null``/``~``/empty value -> ``None``;
      ``true``/``false`` case-insensitive -> bool.
    - Integers / floats stay as strings (caller converts where needed).

    Returns a Python object (typically ``dict`` with a ``"signers"``
    list of dicts). Raises :class:`RegistryParseError` on malformed
    input.
    """
    lines = text.splitlines()
    root: Dict[str, Any] = {}
    current_list_key: Optional[str] = None
    current_list: Optional[List[Dict[str, Any]]] = None
    current_item: Optional[Dict[str, Any]] = None
    list_item_indent: Optional[int] = None
    item_field_indent: Optional[int] = None

    def _coerce_scalar(raw: str) -> Any:
        s = _unquote(raw).strip()
        if s == "" or s.lower() in ("null", "~"):
            return None
        if s.lower() == "true":
            return True
        if s.lower() == "false":
            return False
        return s

    for lineno, raw_line in enumerate(lines, start=1):
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        # List item start: "  - key: value"
        m_item = _LIST_ITEM_RE.match(line)
        if m_item:
            if current_list is None:
                raise RegistryParseError(
                    "list item without enclosing key at line {0}".format(
                        lineno
                    )
                )
            indent = len(m_item.group(1))
            if list_item_indent is None:
                list_item_indent = indent
            elif indent != list_item_indent:
                if indent < list_item_indent:
                    raise RegistryParseError(
                        "list-item indent regression at line {0}".format(
                            lineno
                        )
                    )
            current_item = {}
            current_list.append(current_item)
            item_field_indent = None
            inner = m_item.group(2)
            # First field embedded on the "- key: value" line.
            if ":" in inner:
                k, _, v = inner.partition(":")
                k = k.strip()
                if not k:
                    raise RegistryParseError(
                        "empty key on list-item line {0}".format(lineno)
                    )
                current_item[k] = _coerce_scalar(v)
            elif inner.strip():
                raise RegistryParseError(
                    "scalar list items unsupported at line {0}".format(
                        lineno
                    )
                )
            continue

        # Top-level or item-field key: "key: value"
        m_kv = _KV_RE.match(line)
        if m_kv:
            key_indent = len(m_kv.group(1))
            key = m_kv.group(2)
            value = m_kv.group(3)

            # Field of the current list item?
            if (
                current_item is not None
                and list_item_indent is not None
                and key_indent > list_item_indent
            ):
                if item_field_indent is None:
                    item_field_indent = key_indent
                elif key_indent != item_field_indent:
                    raise RegistryParseError(
                        "field indent drift at line {0}".format(lineno)
                    )
                current_item[key] = _coerce_scalar(value)
                continue

            # Otherwise, top-level key.
            if key_indent != 0:
                raise RegistryParseError(
                    "unexpected indented key {0!r} at line {1}".format(
                        key, lineno
                    )
                )
            current_list_key = None
            current_list = None
            current_item = None
            list_item_indent = None
            item_field_indent = None
            if value == "":
                root[key] = []
                current_list_key = key
                current_list = root[key]
            else:
                root[key] = _coerce_scalar(value)
            continue

        raise RegistryParseError(
            "unparseable line {0}: {1!r}".format(lineno, raw_line)
        )

    return root


# --- Public API ------------------------------------------------------------


def load_registry(path: Path) -> Dict[str, SignerRecord]:
    """Parse the signer registry file into a ``{key_id: SignerRecord}`` map.

    The file MAY be YAML (manual subset parser) OR JSON (fallback used
    if YAML parsing fails). The JSON shape is::

        {"signers": [
            {"key_id": "...", "key_type": "hot",
             "created_at": "...", "expires_at": "...",
             "revoked_at": null, "notes": "..."},
            ...
        ]}

    Raises
    ------
    FileNotFoundError
        ``path`` does not exist.
    RegistryParseError
        File exists but parsing or invariant-check failed (malformed
        YAML/JSON, missing required field, duplicate signer, bad
        datetime).
    """
    if not path.exists():
        raise FileNotFoundError(str(path))
    text = path.read_text(encoding="utf-8")

    parsed: Any
    try:
        parsed = _parse_minimal_yaml(text)
    except RegistryParseError as yaml_err:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as json_err:
            raise RegistryParseError(
                "neither YAML nor JSON parsing succeeded "
                "(yaml: {0}; json: {1})".format(yaml_err, json_err)
            )

    if not isinstance(parsed, dict) or "signers" not in parsed:
        raise RegistryParseError("registry root missing 'signers' key")
    signers_raw = parsed["signers"]
    if not isinstance(signers_raw, list):
        raise RegistryParseError("'signers' must be a list")

    out: Dict[str, SignerRecord] = {}
    for idx, row in enumerate(signers_raw):
        if not isinstance(row, dict):
            raise RegistryParseError(
                "signers[{0}] not a mapping".format(idx)
            )
        required = ("key_id", "key_type", "created_at", "expires_at")
        for fld in required:
            if fld not in row or row[fld] in (None, ""):
                raise RegistryParseError(
                    "signers[{0}] missing required field {1!r}".format(
                        idx, fld
                    )
                )

        try:
            key_id = _normalize_key_id(str(row["key_id"]))
        except RegistryParseError as e:
            raise RegistryParseError(
                "signers[{0}].key_id: {1}".format(idx, e)
            )

        key_type = str(row["key_type"]).strip().lower()
        if key_type not in ("hot", "cold"):
            raise RegistryParseError(
                "signers[{0}].key_type must be hot|cold, got {1!r}".format(
                    idx, key_type
                )
            )

        try:
            created_at = _parse_datetime(str(row["created_at"]))
            expires_at = _parse_datetime(str(row["expires_at"]))
        except RegistryParseError as e:
            raise RegistryParseError(
                "signers[{0}]: {1}".format(idx, e)
            )

        revoked_at: Optional[_dt.datetime] = None
        rv = row.get("revoked_at")
        if rv not in (None, "", "null"):
            try:
                revoked_at = _parse_datetime(str(rv))
            except RegistryParseError as e:
                raise RegistryParseError(
                    "signers[{0}].revoked_at: {1}".format(idx, e)
                )

        notes = str(row.get("notes") or "")

        if key_id in out:
            raise RegistryParseError(
                "duplicate signer key_id {0} (signers[{1}])".format(
                    key_id, idx
                )
            )

        out[key_id] = SignerRecord(
            key_id=key_id,
            key_type=key_type,
            created_at=created_at,
            expires_at=expires_at,
            revoked_at=revoked_at,
            notes=notes,
        )

        # Forward-compat: any extra field on the row is silently ignored.
        # We intentionally do NOT raise so newer registry schemas degrade
        # gracefully on older parsers (PLAN-089 forward-compat).

    return out


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def is_valid_signer(
    key_id: str,
    now: Optional[_dt.datetime] = None,
    registry: Optional[Dict[str, SignerRecord]] = None,
) -> Tuple[bool, str]:
    """Validate a single signer.

    Parameters
    ----------
    key_id
        Fingerprint string (whitespace + case are normalised).
    now
        Injection seam (QA P1 fold). Default :func:`_utc_now`. MUST be
        timezone-aware; naive datetimes raise ``ValueError``.
    registry
        Pre-loaded registry dict. If ``None``, every key is unknown.
        (Callers normally pass a registry from :func:`load_registry`;
        the ``None`` branch is for tests + fail-CLOSED defaults.)

    Returns
    -------
    (valid, reason)
        ``reason`` is one of:

        - ``"valid"`` — key found, not expired, not revoked.
        - ``"unknown_key"`` — key absent from registry.
        - ``"revoked"`` — key has ``revoked_at`` set (precedence over
          expiry). Reason string embeds the ISO timestamp.
        - ``"expired"`` — ``now >= expires_at`` and not revoked.
          Reason string embeds the ISO timestamp.
    """
    if now is None:
        now = _utc_now()
    if now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware")

    try:
        norm = _normalize_key_id(key_id)
    except RegistryParseError:
        # Malformed fpr is "unknown" from the validity-gate perspective.
        return False, "unknown_key"

    reg = registry or {}
    rec = reg.get(norm)
    if rec is None:
        return False, "unknown_key"

    # Revocation takes precedence over expiry.
    if rec.revoked_at is not None:
        return False, "revoked:{0}".format(rec.revoked_at.isoformat())

    # STRICT > boundary: at exactly expires_at, key is expired.
    if now >= rec.expires_at:
        return False, "expired:{0}".format(rec.expires_at.isoformat())

    return True, "valid"


def quorum_verify(
    signatures: List[Signature],
    threshold: int,
    now: Optional[_dt.datetime] = None,
    registry: Optional[Dict[str, SignerRecord]] = None,
) -> Tuple[bool, str]:
    """Check N-of-M cold-key quorum.

    All signatures MUST come from registry entries with
    ``key_type == "cold"`` and pass :func:`is_valid_signer`. Signers
    MUST be distinct (duplicate-signer collusion case is rejected).

    Parameters
    ----------
    signatures
        List of :class:`Signature`. Empty list -> ``met=False``.
    threshold
        Minimum number of DISTINCT valid cold-key signatures required.
        Must be ``>= 1``.
    now
        Injection seam — same semantics as :func:`is_valid_signer`.
    registry
        Pre-loaded registry; ``None`` is empty registry (every key
        unknown).

    Returns
    -------
    (met, reason)
        ``reason`` is one of:

        - ``"quorum_met:N"`` — exactly N distinct valid cold-key
          signatures collected (N >= threshold).
        - ``"threshold_invalid"`` — ``threshold < 1``.
        - ``"empty_signatures"`` — no signatures provided.
        - ``"duplicate_signer:<key_id>"`` — at least two signatures
          carry the same ``key_id`` (collusion test).
        - ``"wrong_key_type:<key_id>"`` — at least one signature is
          from a ``hot`` key (cold quorum is for registry rotation +
          emergency recovery only).
        - ``"signer_invalid:<key_id>:<sub_reason>"`` — at least one
          signer failed :func:`is_valid_signer` (sub_reason embeds the
          specific failure).
        - ``"quorum_short:got=N;need=M"`` — fewer distinct valid
          cold-key signatures than the threshold.

    Validation order (strict, so callers can rely on the first-failing
    reason):

      1. ``threshold_invalid``
      2. ``empty_signatures``
      3. ``duplicate_signer`` (collusion catch — runs BEFORE individual
         signer validation so the collusion signal is preserved)
      4. ``wrong_key_type`` / ``unknown_key`` / ``revoked`` / ``expired``
         (per-signer; first failure wins, ordered by appearance)
      5. ``quorum_short`` / ``quorum_met``
    """
    if threshold < 1:
        return False, "threshold_invalid"
    if not signatures:
        return False, "empty_signatures"

    # Detect duplicate signers FIRST (collusion case must surface even
    # when one signature would otherwise be valid).
    seen: Dict[str, int] = {}
    for sig in signatures:
        try:
            norm = _normalize_key_id(sig.key_id)
        except RegistryParseError:
            # Non-normalisable key — leave raw so the per-signer loop
            # below produces the "unknown_key" signal on first failure.
            norm = sig.key_id
        seen[norm] = seen.get(norm, 0) + 1
        if seen[norm] > 1:
            return False, "duplicate_signer:{0}".format(norm)

    reg = registry or {}

    # Per-signer validation (strict order by appearance).
    distinct_valid = 0
    for sig in signatures:
        try:
            norm = _normalize_key_id(sig.key_id)
        except RegistryParseError:
            return False, "signer_invalid:{0}:unknown_key".format(
                sig.key_id
            )

        rec = reg.get(norm)
        if rec is None:
            return False, "signer_invalid:{0}:unknown_key".format(norm)
        if rec.key_type != "cold":
            return False, "wrong_key_type:{0}".format(norm)

        ok, reason = is_valid_signer(norm, now=now, registry=reg)
        if not ok:
            return False, "signer_invalid:{0}:{1}".format(norm, reason)

        distinct_valid += 1

    if distinct_valid < threshold:
        return False, "quorum_short:got={0};need={1}".format(
            distinct_valid, threshold
        )

    return True, "quorum_met:{0}".format(distinct_valid)

# ---------------------------------------------------------------------------
# PLAN-113 Phase B WIRE-AUDIT — Registry lifecycle emitter helpers.
#
# These functions are the canonical callsites for sentinel signer lifecycle
# audit events (rotated / revoked / expiry_warned). Callers (Owner ceremony
# scripts, CI registry validators) import and invoke them after a successful
# registry mutation; they are fail-open and never block the caller.
# ---------------------------------------------------------------------------

def _emit_signer_event(fn_name: str, **kwargs: object) -> None:
    """Best-effort import + emit for signer lifecycle events — never raises."""
    import sys as _sys
    from pathlib import Path as _Path
    _hooks_dir = str(_Path(__file__).resolve().parent.parent)
    if _hooks_dir not in _sys.path:
        _sys.path.insert(0, _hooks_dir)
    try:
        from _lib import audit_emit as _ae
        fn = getattr(_ae, fn_name, None)
        if fn is not None:
            fn(**kwargs)
    except Exception:  # pragma: no cover
        pass


def emit_rotation_landed(
    key_id: str,
    key_type: str = "",
    rotated_from_key_id: str = "",
    rotated_by: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit sentinel_signer_rotated audit event.

    Call this after a successful cold-quorum-gated key rotation has been
    written to the registry file and committed. Fail-open — never raises.

    Args:
        key_id: fingerprint of the NEW key that replaced the old one.
        key_type: ``"hot"`` or ``"cold"``.
        rotated_from_key_id: fingerprint of the key being replaced.
        rotated_by: identity or role that performed the rotation.
    """
    _emit_signer_event(
        "emit_sentinel_signer_rotated",
        key_id=key_id,
        key_type=key_type,
        rotated_from_key_id=rotated_from_key_id,
        rotated_by=rotated_by,
        session_id=session_id,
        project=project,
    )


def emit_revocation_landed(
    key_id: str,
    key_type: str = "",
    revoked_by: str = "",
    reason: str = "",
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit sentinel_signer_revoked audit event.

    Call this after a cold-quorum-gated revocation has been committed to
    the registry. Fail-open — never raises.

    Args:
        key_id: fingerprint of the key being revoked.
        key_type: ``"hot"`` or ``"cold"``.
        revoked_by: identity or role that performed the revocation.
        reason: human-readable revocation justification (e.g. "compromise").
    """
    _emit_signer_event(
        "emit_sentinel_signer_revoked",
        key_id=key_id,
        key_type=key_type,
        revoked_by=revoked_by,
        reason=reason,
        session_id=session_id,
        project=project,
    )


def warn_expiring_signers(
    registry: "Dict[str, SignerRecord]",
    warn_within_days: int = 60,
    now: "_dt.datetime | None" = None,
    session_id: str = "",
    project: str = "",
) -> int:
    """Scan the registry for keys expiring within ``warn_within_days`` and
    emit ``sentinel_signer_expiry_warned`` for each. Fail-open — never raises.

    Returns the count of expiry warnings emitted.

    Call from a scheduled CI check or ceo-health.py scan. Rate-cap is
    enforced inside ``emit_sentinel_signer_expiry_warned`` (1x/hour per key).
    """
    if now is None:
        now = _utc_now()
    warned = 0
    try:
        import datetime as _dt_mod
        horizon = now + _dt_mod.timedelta(days=warn_within_days)
        for key_id, rec in registry.items():
            # Skip revoked keys -- they have no meaningful expiry warning.
            if rec.revoked_at is not None:
                continue
            if now < rec.expires_at <= horizon:
                days_remaining = (rec.expires_at - now).days
                _emit_signer_event(
                    "emit_sentinel_signer_expiry_warned",
                    key_id=key_id,
                    days_remaining=days_remaining,
                    expires_at_iso=rec.expires_at.isoformat(),
                    session_id=session_id,
                    project=project,
                )
                warned += 1
    except Exception:  # pragma: no cover
        pass
    return warned

