"""STDLIB-ONLY — T1565 audit-chain hash continuity check.

Staged at ``.claude/plans/PLAN-099-FOLLOWUP/wave-e-staging/audit_chain_ext.py``.
Owner ``git mv`` to ``.claude/hooks/_lib/federation/audit_chain_ext.py``
at Phase A2-post (canonical-edit guard blocks direct writes to
``federation/``).

Per plan §4 Wave E.3 + attack-rebinding.md §2.3 §3.3:

  - Verifies the SHA-256 ``prev_hash`` chain on ``audit-log.jsonl``.
  - Walks events sequentially; each event's ``audit_chain_prev_hash``
    MUST equal the chain-hash of the previous event computed over its
    canonical-JSON form (per attack-rebinding.md §2.3 doctrine).
  - First (genesis) event's ``audit_chain_prev_hash`` MUST be the
    sentinel ``"0" * 64`` — 64 zero hex chars.
  - On break → returns ``(False, break_info)`` so the dispatcher can
    emit ``federation_tamper_detected`` + refuse to serve the corrupted
    segment.

ATT&CK bindings:
  - T1565 (Data Manipulation) — primary detection
  - T1556 (Modify Authentication Process) — peer-injected events with
    forged HMAC trigger chain-break secondary signal

CRITICAL S147 lesson [[feedback-bash-sha-must-match-python-contract]]:
the canonical form here MUST match the federation peer's compute side
BYTE-FOR-BYTE. We use ``json.dumps(event, sort_keys=True,
ensure_ascii=False, separators=(",", ":"), allow_nan=False)`` — the
same recipe as ``.claude/hooks/_lib/canonical_json.encode``. Locale +
Unicode edge cases are covered by ``ensure_ascii=False`` (UTF-8
output) + ``sort_keys=True`` (deterministic key ordering).

Sibling module: ``.claude/hooks/_lib/federation/audit_chain.py`` (PLAN-099
v1.32.0 — correlation-id tagging). This module is the *hash-chain*
companion; they are intentionally split because correlation tagging is
a producer-side concern (federation client) and chain hashing is a
verifier-side concern (server + auditor).

WAVE-F-PENDING markers:
  - ``federation_tamper_detected`` emit is a no-op pre-registration.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


__all__ = [
    "GENESIS_PREV_HASH",
    "PREV_HASH_FIELD",
    "EXCLUDED_FIELDS",
    "compute_canonical_hash",
    "check_chain",
]


# Per attack-rebinding.md §2.3 "Genesis event prev-hash" — 64 zero hex
# chars as the chain anchor sentinel.
GENESIS_PREV_HASH: str = "0" * 64

# The canonical field name on every audit-log line.
PREV_HASH_FIELD: str = "audit_chain_prev_hash"

# Fields excluded from the canonical-hash input. See attack-rebinding.md
# §2.3 "Excluded fields" — self-referential or wall-clock-non-stable.
EXCLUDED_FIELDS: frozenset = frozenset({
    "audit_chain_hash",        # the chain hash of THIS event (self-ref)
    "audit_chain_prev_hash",   # pointer to previous event (NOT included)
    "_timestamp_emitted",      # wall-clock at emit (added post-hash)
})


# ----------------------------------------------------------------------------
# Audit emit shim (WAVE-F-PENDING)
# ----------------------------------------------------------------------------


def _safe_emit(action: str, **fields: Any) -> None:
    """Mirrors :func:`rate_limit._safe_emit`. WAVE-F-PENDING."""
    try:
        try:
            from _lib import audit_emit  # type: ignore[import]
        except ImportError:
            import importlib

            audit_emit = importlib.import_module(".audit_emit", package="_lib")
    except ImportError:
        return
    # PLAN-112-FOLLOWUP C-4 fix (R-TD-1): fall back to emit_generic so
    # federation_tamper_detected (T1565) is actually written — the
    # Wave-F.2 action has no named emit_<action> wrapper.
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
                "[federation.audit_chain_ext] audit emit '{0}' raised\n".format(action)
            )
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Canonical hashing
# ----------------------------------------------------------------------------


def compute_canonical_hash(event: Mapping[str, Any]) -> str:
    """Return SHA-256 hex of the canonical-JSON form of ``event``.

    Canonical form recipe (attack-rebinding.md §2.3):

      json.dumps(
          {k: v for k, v in event.items() if k not in EXCLUDED_FIELDS},
          sort_keys=True,
          ensure_ascii=False,
          separators=(",", ":"),
          allow_nan=False,
      )

    Returns the hex digest (lowercase, 64 chars). The output MUST be
    byte-identical to the peer-side compute (S147 lesson — both sides
    must call the same encoder).

    Raises ``TypeError`` / ``ValueError`` on non-serialisable input
    (caller MUST catch — chain-break decisions are made by
    :func:`check_chain`, not here).
    """
    if not isinstance(event, Mapping):
        raise TypeError("event must be a mapping")
    filtered = {k: v for k, v in event.items() if k not in EXCLUDED_FIELDS}
    canonical = json.dumps(
        filtered,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    h = hashlib.sha256(canonical.encode("utf-8"))
    return h.hexdigest()


# ----------------------------------------------------------------------------
# Chain walker
# ----------------------------------------------------------------------------


def _iter_audit_log_lines(audit_log_path: Path) -> Iterable[Tuple[int, Dict[str, Any]]]:
    """Yield ``(line_no, parsed_event)`` for each non-empty JSONL line.

    Line-number is 1-indexed (matches typical editor convention; makes
    break-info reports easier to read). Malformed lines yield a sentinel
    dict ``{"_parse_error": "<msg>", "_raw": "<truncated>"}`` so the
    caller can decide whether to treat them as chain breaks.
    """
    if not audit_log_path.exists():
        return
    try:
        with audit_log_path.open("r", encoding="utf-8", errors="replace") as fh:
            for idx, raw in enumerate(fh, start=1):
                line = raw.rstrip("\n").rstrip("\r")
                if not line.strip():
                    continue
                try:
                    parsed = json.loads(line)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    yield idx, {
                        "_parse_error": "{0}:{1}".format(type(exc).__name__, str(exc)[:128]),
                        "_raw": line[:256],
                    }
                    continue
                if not isinstance(parsed, dict):
                    yield idx, {
                        "_parse_error": "non_object_line",
                        "_raw": line[:256],
                    }
                    continue
                yield idx, parsed
    except OSError as exc:
        # Bubble out as an empty iteration; caller checks file existence
        # separately for the "log_missing" branch.
        sys.stderr.write(
            "[federation.audit_chain_ext] read failed: {0}\n".format(exc)
        )
        return


def check_chain(
    audit_log_path: Path,
    *,
    max_events: Optional[int] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Walk the audit-log and verify the SHA-256 prev-hash chain.

    Parameters
    ----------
    audit_log_path
        Path to an ``audit-log.jsonl``-style file. Missing file is
        treated as an EMPTY-but-VALID chain (returns ``(True, None)``);
        the dispatcher would refuse to serve audit-summary on a missing
        log anyway.
    max_events
        Optional cap for the walk. None → walk the entire file. Set
        for streaming endpoints that want bounded latency.

    Returns
    -------
    (True, None)
        Chain intact.
    (False, break_info)
        Chain break detected. ``break_info`` schema::

            {
              "line_no":              int,   # 1-indexed
              "reason":               str,   # one of:
                                              #   "parse_error",
                                              #   "missing_prev_hash",
                                              #   "non_string_prev_hash",
                                              #   "genesis_not_zero",
                                              #   "prev_hash_mismatch",
                                              #   "hash_compute_failed"
              "expected_prev_hash":   str,   # what THIS line should carry
              "actual_prev_hash":     str,   # what it actually carries
            }

        Also emits ``federation_tamper_detected`` (WAVE-F-PENDING).
    """
    if not isinstance(audit_log_path, Path):
        audit_log_path = Path(audit_log_path)
    if not audit_log_path.exists():
        return True, None

    expected_prev: str = GENESIS_PREV_HASH
    seen_any: bool = False
    walked: int = 0

    for line_no, event in _iter_audit_log_lines(audit_log_path):
        walked += 1
        if max_events is not None and walked > max_events:
            break

        if "_parse_error" in event:
            info = {
                "line_no": line_no,
                "reason": "parse_error",
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": "",
                "detail": event.get("_parse_error", ""),
            }
            # F-001 R2 iter-2 fix: F.2 wrapper signature is
            # `emit_federation_tamper_detected(peer_id, route,
            # tamper_type, prev_hash_prefix)`. `line_no` /
            # `expected_prev_hash` / `actual_prev_hash` / `reason`
            # not in F.2 allowlist; we map ``reason`` → ``tamper_type``
            # (closed enum) and surface the expected prev-hash prefix
            # (16 hex). Per-event line number is forensically
            # preserved in the returned ``info`` dict for the caller.
            _safe_emit(
                "federation_tamper_detected",
                peer_id="",
                route="audit_chain_walk",
                tamper_type="canonical_form_drift",
                prev_hash_prefix=str(expected_prev)[:16],
            )
            return False, info

        actual_prev = event.get(PREV_HASH_FIELD)
        if actual_prev is None:
            # No chain field at all. On the FIRST event we tolerate
            # legacy logs (genesis without chain field) — they get a
            # synthetic prev = GENESIS. On subsequent events the
            # missing field IS the break.
            if not seen_any:
                seen_any = True
                try:
                    expected_prev = compute_canonical_hash(event)
                except (TypeError, ValueError) as exc:
                    info = {
                        "line_no": line_no,
                        "reason": "hash_compute_failed",
                        "expected_prev_hash": expected_prev,
                        "actual_prev_hash": "",
                        "detail": "{0}:{1}".format(type(exc).__name__, str(exc)[:128]),
                    }
                    # F-001 R2 iter-2 fix: aligned with F.2 wrapper
                    # `emit_federation_tamper_detected(peer_id, route,
                    # tamper_type, prev_hash_prefix)`. tamper_type
                    # closed enum: hmac_mismatch / origin_tag_replay /
                    # chain_hash_break / canonical_form_drift.
                    # Hash-compute failures map to canonical_form_drift
                    # (the event payload couldn't be canonicalised).
                    _safe_emit(
                        "federation_tamper_detected",
                        peer_id="",
                        route="audit_chain_walk",
                        tamper_type="canonical_form_drift",
                        prev_hash_prefix="",
                    )
                    return False, info
                continue
            info = {
                "line_no": line_no,
                "reason": "missing_prev_hash",
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": "",
            }
            # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
            # Missing prev_hash → chain_hash_break.
            _safe_emit(
                "federation_tamper_detected",
                peer_id="",
                route="audit_chain_walk",
                tamper_type="chain_hash_break",
                prev_hash_prefix=str(expected_prev)[:16],
            )
            return False, info

        if not isinstance(actual_prev, str):
            info = {
                "line_no": line_no,
                "reason": "non_string_prev_hash",
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": "<{0}>".format(type(actual_prev).__name__),
            }
            # F-001 R2 iter-2 fix: aligned with F.2 wrapper signature.
            # Non-string prev_hash → canonical_form_drift (wire-format
            # violation rather than chain break).
            _safe_emit(
                "federation_tamper_detected",
                peer_id="",
                route="audit_chain_walk",
                tamper_type="canonical_form_drift",
                prev_hash_prefix=str(expected_prev)[:16],
            )
            return False, info

        # Genesis check (first event with chain field present).
        if not seen_any:
            if actual_prev != GENESIS_PREV_HASH:
                info = {
                    "line_no": line_no,
                    "reason": "genesis_not_zero",
                    "expected_prev_hash": GENESIS_PREV_HASH,
                    "actual_prev_hash": actual_prev,
                }
                # F-001 R2 iter-2 fix: aligned with F.2 wrapper.
                # Genesis hash mismatch → chain_hash_break.
                _safe_emit(
                    "federation_tamper_detected",
                    peer_id="",
                    route="audit_chain_walk",
                    tamper_type="chain_hash_break",
                    prev_hash_prefix=str(actual_prev)[:16],
                )
                return False, info
            seen_any = True
        else:
            if actual_prev != expected_prev:
                info = {
                    "line_no": line_no,
                    "reason": "prev_hash_mismatch",
                    "expected_prev_hash": expected_prev,
                    "actual_prev_hash": actual_prev,
                }
                # F-001 R2 iter-2 fix: aligned with F.2 wrapper.
                # Mid-chain mismatch → chain_hash_break.
                _safe_emit(
                    "federation_tamper_detected",
                    peer_id="",
                    route="audit_chain_walk",
                    tamper_type="chain_hash_break",
                    prev_hash_prefix=str(actual_prev)[:16],
                )
                return False, info

        # Advance — compute the hash THIS event contributes to the next link.
        try:
            expected_prev = compute_canonical_hash(event)
        except (TypeError, ValueError) as exc:
            info = {
                "line_no": line_no,
                "reason": "hash_compute_failed",
                "expected_prev_hash": expected_prev,
                "actual_prev_hash": actual_prev,
                "detail": "{0}:{1}".format(type(exc).__name__, str(exc)[:128]),
            }
            # F-001 R2 iter-2 fix: aligned with F.2 wrapper.
            _safe_emit(
                "federation_tamper_detected",
                peer_id="",
                route="audit_chain_walk",
                tamper_type="canonical_form_drift",
                prev_hash_prefix=str(expected_prev)[:16],
            )
            return False, info

    return True, None
