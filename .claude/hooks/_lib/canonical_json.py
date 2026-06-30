"""Canonical JSON encoder — single-source for HMAC-covered serialization.

PLAN-023 Phase B (security-engineer review required mitigation #1).

The audit-log HMAC chain (ADR-055) computes
``hmac_sha256(key, prev_hmac || canonical_json(entry))``. For the chain
to remain verifiable across Python versions, machines, and future
schema changes, the JSON canonicalization MUST be deterministic
byte-for-byte.

This module provides the one blessed encoder. Any code writing HMAC-
covered audit entries (or verifying them) MUST route through
:func:`encode`. A future ``check-canonical-json-drift.py`` lint will
grep for ``json.dumps(`` in ``_lib/`` + ``audit-verify-chain.py`` and
fail if the call is outside this module.

## Contract (frozen at v1.6.0)

1. ``json.dumps(obj, sort_keys=True, separators=(",", ":"),
   ensure_ascii=False, allow_nan=False)``. These kwargs are pinned.
2. String values are NFC-normalized before serialization.
3. No floats permitted in HMAC-covered fields. Raise
   :class:`CanonicalJsonError` if one is detected. Rationale: Python
   ``repr`` for edge floats is non-deterministic across versions (e.g.
   ``repr(0.1 + 0.2)``), which would produce verifier-encoder drift.
   Adopters wanting a fractional field encode it as integer basis-points
   or a fixed-precision string.
4. No NaN / Infinity / -Infinity (enforced via ``allow_nan=False``).
5. No tuples, sets, custom ``__repr__`` objects, or non-JSON scalars.
6. Output is ``bytes`` (UTF-8), not ``str``. HMAC takes bytes.

## Non-goals

* Not RFC 8785 (JSON Canonicalization Scheme) compliant. JCS is out of
  scope for v1.6.0 (stdlib-only constraint; JCS normalization rules
  for numbers require a full parser). Framework-internal
  canonicalization is sufficient because both writer and verifier use
  this same encoder.
* Not cryptographic. HMAC takes the canonical form as input; this
  module only ensures determinism.
"""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Mapping


class CanonicalJsonError(ValueError):
    """Raised when the input contains a value type forbidden by the
    canonical contract (float, NaN, Infinity, tuple, set, etc.).
    """


def _nfc_normalize(obj: Any) -> Any:
    """Recursively NFC-normalize all string values.

    NFC (Normalization Form Canonical Composition) guarantees that
    ``"é"`` (precomposed U+00E9) and ``"e" + "◌́"`` (combining U+0301)
    produce the same byte sequence. Without this pass, a user writing
    a skill with a combining-char filename would produce a different
    HMAC on the verifier's machine if the verifier's filesystem
    decomposed on read.

    PLAN-087 Wave C.6: ASCII fast-path. Strings containing only ASCII
    bytes (U+0000..U+007F) cannot carry combining-character sequences
    that NFC would re-compose; they are already in NFC form by
    construction. ``str.isascii()`` is a C-level CPython primitive
    (PEP 616, available since 3.7) — O(N) amortized and effectively
    free for short audit-event fields. Skipping
    ``unicodedata.normalize("NFC", x)`` on the ASCII-dominant audit
    payload avoids a per-event allocation + table lookup cycle.
    """
    if isinstance(obj, str):
        if obj.isascii():
            return obj
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, Mapping):
        return {k: _nfc_normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_nfc_normalize(x) for x in obj]
    return obj


def _validate_no_floats(obj: Any, path: str = "$") -> None:
    """Walk the structure, raising CanonicalJsonError on float/NaN/Inf.

    Booleans are fine (``json.dumps`` emits ``true``/``false``
    deterministically). Ints are fine. Strings, dicts, lists, None are
    fine. Floats are not.
    """
    # bool is a subclass of int, so this catches bool first.
    if isinstance(obj, bool) or obj is None or isinstance(obj, int):
        return
    if isinstance(obj, float):
        raise CanonicalJsonError(
            "float at {path!r} forbidden in HMAC-covered JSON "
            "(value={value!r}); encode as integer basis-points or "
            "fixed-precision string".format(path=path, value=obj)
        )
    if isinstance(obj, str):
        return
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            _validate_no_floats(v, "{p}.{k}".format(p=path, k=k))
        return
    if isinstance(obj, list):
        for i, x in enumerate(obj):
            _validate_no_floats(x, "{p}[{i}]".format(p=path, i=i))
        return
    raise CanonicalJsonError(
        "unsupported type {t} at {path!r} "
        "(only dict/list/str/int/bool/None permitted)".format(
            t=type(obj).__name__, path=path
        )
    )


def encode(obj: Any) -> bytes:
    """Encode ``obj`` to canonical JSON bytes.

    Pinned kwargs: ``sort_keys=True`` (recursive) +
    ``separators=(",", ":")`` (no whitespace) +
    ``ensure_ascii=False`` (UTF-8 strings preserved) +
    ``allow_nan=False`` (NaN/Inf rejected).

    Pre-pass: NFC-normalize all strings; reject floats.

    :raises CanonicalJsonError: if the input contains floats or
        non-JSON-native types.
    :raises ValueError: from ``json.dumps`` on NaN/Inf (should not
        occur due to our pre-check; defense in depth).
    :return: UTF-8 bytes suitable for HMAC input.
    """
    _validate_no_floats(obj)
    normalized = _nfc_normalize(obj)
    text = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return text.encode("utf-8")
