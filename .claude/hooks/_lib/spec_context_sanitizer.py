"""Spec-context sanitizer (PLAN-059 SEC-P0-01).

Sanitization library for `## SPEC CONTEXT` payload before it lands in
the spawn-prompt body. Defends against:

- NFKC homoglyph attacks (`Α` Greek alpha vs `A` Latin)
- Control characters (NUL, BEL, BS, ESC, RTL bidi overrides)
- Frame-escape via literal sentinel markers in payload
- Markdown-header escape (`\n# Heading` early-terminates skill blocks)
- Oversized payloads (8 KiB cap; truncate + emit advisory)

API:
    from _lib.spec_context_sanitizer import sanitize, SanitizeResult

    result = sanitize(spec_text)
    if result.truncated:
        ...
    cleaned = result.text
    sha = result.sha256

Stdlib-only. Pure function. Never raises (returns empty SanitizeResult
on any internal failure).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import List

# 8 KiB cap per spec — payload longer than this is truncated.
_MAX_BYTES = 8 * 1024

# Sentinel markers reserved for framing the spec context block in
# spawn-prompts. If they appear in the payload, the payload is trying
# to break out of the frame.
_RESERVED_SENTINELS = (
    "<<<SPEC-CONTEXT-BEGIN>>>",
    "<<<SPEC-CONTEXT-END>>>",
)

# Control-char strip range. Keep \t (\x09), \n (\x0A), \r (\x0D).
# Reject everything else in C0 + DEL + C1 control space.
_CONTROL_RE = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F\x80-\x9F]"
)

# Bidi override + zero-width characters that homoglyph attacks abuse.
# RLO U+202E, LRO U+202D, BOM U+FEFF, ZWJ U+200D, ZWNJ U+200C, etc.
# PLAN-133 A2 (Goose-harvest) — ALSO cover the Unicode Tags block
# U+E0000–E007F (glyph-less ASCII-shadow alphabet abused for invisible-text
# prompt smuggling). Astral range added as an explicit alternation so it
# matches on both wide and narrow CPython builds. ONE filter (no fork).
_BIDI_ZW_RE = re.compile(
    r"[​-‏‪-‮⁠-⁯﻿]"
    r"|[\U000E0000-\U000E007F]"
)

# PLAN-133 A2 — Tag-block-only probe (attribution count; the STRIP is done by
# the unified _BIDI_ZW_RE above). bidi_zw_chars_stripped therefore counts the
# bidi/zero-width half only; tag_chars_stripped counts this half. The hard-block
# predicate sums BOTH (+ control_chars).
_TAG_BLOCK_RE = re.compile(r"[\U000E0000-\U000E007F]")

# Markdown headers at line start that could break out of the SKILL
# CONTENT block in the spawn prompt. We don't STRIP — that breaks
# legitimate quoted markdown — but we count for advisory.
_MD_HEADER_RE = re.compile(r"^\s*#{1,6}\s+", re.MULTILINE)


@dataclass(frozen=True)
class SanitizeResult:
    """Outcome of a sanitize() call."""

    text: str
    sha256: str
    original_bytes: int
    cleaned_bytes: int
    truncated: bool
    sentinel_violations: List[str]
    control_chars_stripped: int
    bidi_zw_chars_stripped: int
    # PLAN-133 A2 — count of U+E0000–E007F Tag-block chars stripped. Counted
    # SEPARATELY from bidi_zw so the audit can attribute the Tag-block class,
    # but BOTH feed the single invisible-unicode hard-block predicate.
    tag_chars_stripped: int
    header_escape_count: int

    def to_dict(self) -> dict:
        return {
            "sha256": self.sha256,
            "original_bytes": self.original_bytes,
            "cleaned_bytes": self.cleaned_bytes,
            "truncated": self.truncated,
            "sentinel_violations": list(self.sentinel_violations),
            "control_chars_stripped": self.control_chars_stripped,
            "bidi_zw_chars_stripped": self.bidi_zw_chars_stripped,
            "tag_chars_stripped": self.tag_chars_stripped,
            "header_escape_count": self.header_escape_count,
        }


def _empty_result() -> SanitizeResult:
    return SanitizeResult(
        text="",
        sha256=hashlib.sha256(b"").hexdigest(),
        original_bytes=0,
        cleaned_bytes=0,
        truncated=False,
        sentinel_violations=[],
        control_chars_stripped=0,
        bidi_zw_chars_stripped=0,
        tag_chars_stripped=0,
        header_escape_count=0,
    )


def sanitize(text, *, max_bytes: int = _MAX_BYTES) -> SanitizeResult:
    """Sanitize ``text`` for use as `## SPEC CONTEXT` payload.

    Steps (in order):
      1. Coerce to str (None / bytes / other → str via decode-or-repr).
      2. NFKC normalize.
      3. Strip control chars (preserve \\t \\n \\r).
      4. Strip bidi + zero-width chars.
      5. Detect sentinel violations (record but do not modify).
      6. Detect markdown header escape (record advisory count).
      7. Truncate to max_bytes (UTF-8).
      8. Compute SHA-256 of cleaned bytes.

    Never raises. On any internal exception, returns empty result.
    """
    try:
        if text is None:
            return _empty_result()
        if isinstance(text, (bytes, bytearray)):
            try:
                text = bytes(text).decode("utf-8", errors="replace")
            except Exception:
                return _empty_result()
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return _empty_result()

        original = text
        original_bytes = len(original.encode("utf-8", errors="replace"))

        # Step 2: NFKC normalize
        normalized = unicodedata.normalize("NFKC", original)

        # Step 3: control-char strip
        control_count = len(_CONTROL_RE.findall(normalized))
        cleaned = _CONTROL_RE.sub("", normalized)

        # Step 4: bidi + zero-width strip
        # PLAN-133 A2 — count Tag-block chars separately (same single filter).
        tag_count = len(_TAG_BLOCK_RE.findall(cleaned))
        # Subtract the Tag chars so bidi_zw_chars_stripped stays "bidi/zero-width
        # only" (the unified _BIDI_ZW_RE now also matches the Tag-block).
        bidi_count = len(_BIDI_ZW_RE.findall(cleaned)) - tag_count
        cleaned = _BIDI_ZW_RE.sub("", cleaned)

        # Step 5: sentinel detection (record only)
        violations: List[str] = []
        for sentinel in _RESERVED_SENTINELS:
            if sentinel in cleaned:
                violations.append(sentinel)

        # Step 6: header escape advisory
        header_count = len(_MD_HEADER_RE.findall(cleaned))

        # Step 7: byte cap (UTF-8)
        encoded = cleaned.encode("utf-8", errors="replace")
        truncated = False
        if len(encoded) > max_bytes:
            # Decode safely back to char boundary
            cleaned = encoded[:max_bytes].decode("utf-8", errors="ignore")
            truncated = True
            encoded = cleaned.encode("utf-8", errors="replace")

        # Step 8: hash
        sha = hashlib.sha256(encoded).hexdigest()

        return SanitizeResult(
            text=cleaned,
            sha256=sha,
            original_bytes=original_bytes,
            cleaned_bytes=len(encoded),
            truncated=truncated,
            sentinel_violations=violations,
            control_chars_stripped=control_count,
            bidi_zw_chars_stripped=bidi_count,
            tag_chars_stripped=tag_count,
            header_escape_count=header_count,
        )
    except Exception:
        return _empty_result()


def invisible_unicode_count(result: SanitizeResult) -> int:
    """Total invisible/smuggling chars a hard-block cares about (PLAN-133 A2).

    Sums the three stripped-char counters that represent INVISIBLE or
    direction-spoofing characters: control chars + bidi/zero-width + Tag-block.
    Header-escape count and sentinel violations are NOT included here (they are
    visible-text framing concerns handled by the existing advisory path).
    Pure; never raises.
    """
    try:
        return (
            int(result.control_chars_stripped)
            + int(result.bidi_zw_chars_stripped)
            + int(result.tag_chars_stripped)
        )
    except Exception:  # pragma: no cover — defensive
        return 0


def has_invisible_unicode(text) -> bool:
    """True iff ``text`` contains any invisible/smuggling char (PLAN-133 A2).

    The FORCE-BLOCK SCORE used at spawn + skill-LOAD: runs the existing
    ``sanitize()`` and returns whether any control / bidi / zero-width / Tag-block
    char was present. Pure; never raises (sanitize() is total).
    """
    return invisible_unicode_count(sanitize(text)) > 0


def classify_invisible_unicode(result: SanitizeResult) -> str:
    """Closed-enum dominant class for the audit breadcrumb (PLAN-133 A2).

    Returns one of: "tag_block" | "bidi_zw" | "control" | "none". Priority order
    tag_block > bidi_zw > control (most-novel/most-suspicious first). NEVER returns
    a value outside :data:`INVISIBLE_UNICODE_CLASSES`. Pure.
    """
    if result.tag_chars_stripped:
        return "tag_block"
    if result.bidi_zw_chars_stripped:
        return "bidi_zw"
    if result.control_chars_stripped:
        return "control"
    return "none"


# Closed-enum unicode_class tokens. Mirrored as a literal frozenset in
# _lib/audit_emit.py (_INVISIBLE_UNICODE_CLASSES) — audit_emit keeps no import-time
# dependency on this module; a drift is caught by a dedicated test (the two MUST be
# equal). A value outside this set is coerced to "control" before emit.
INVISIBLE_UNICODE_CLASSES = frozenset({"tag_block", "bidi_zw", "control", "none"})


def sanitize_for_audit(text) -> dict:
    """Convenience wrapper: returns the to_dict() shape for audit emit."""
    return sanitize(text).to_dict()
