"""Canonical pattern library for output-safety scanning (ADR-036 / Sprint 11 P9).

Counterpart to ``scan-injection.py``: same pipeline architecture, but scans
**agent outputs** instead of **agent inputs**. Where ``scan-injection.py``
looks for patterns trying to subvert the LLM's instructions,
``pii_patterns.SCANNER_PIPELINE`` looks for PII / secrets / credentials
leaking OUT via model responses.

## Scanner pipeline (H14, MANDATORY ORDER)

Consensus round-1 §H14 is explicit: pattern-based detection alone is
trivially bypassed by Unicode normalization attacks. The pipeline runs in
order:

1. ``unicodedata.normalize('NFKC', text)`` — collapses full-width glyphs,
   compatibility chars, combining marks. Without this, ``ｓｋ－abcdef...``
   (full-width) bypasses a literal ``sk-`` regex.
2. Strip zero-width / bidi / control chars — U+200B–U+200F, U+202A–U+202E,
   and C0/C1 control chars except ``\\n\\t\\r``. Without this,
   ``s\\u200bk-...`` bypasses a literal ``sk-`` regex.
3. Base64 decode ONE level (bounded) — if a contiguous token has Shannon
   entropy > 4.0 AND length > 40 AND is a valid base64 payload, decode
   and append to the scanned text. Depth cap = 1 (no recursion). Length
   cap = decoded output must not exceed 4× the encoded input (defeats
   decompression-bomb style abuse, though base64 itself inflates by 4/3
   so 4× is a generous safety margin).
4. Shannon entropy > 4.5 over any 24+ char contiguous token →
   credential-shape candidate. Computed via ``shannon_entropy()`` using
   ``math.log2``. Surfaces in ``ScanResult.family_counts`` under the
   ``entropy`` family.
5. Regex against canonical patterns (this module's ``_FAMILIES``).

Each step logs per-step detection counts to the returned ``ScanResult``
(see ``pipeline_step_counts``).

## Families (canonical)

- ``api_key`` — sk-*, ghp_*, github_pat_*, AKIA*, aws_secret_key=...
- ``jwt`` — three base64url segments: ``eyJ[...].[...].[...]``
- ``bearer`` — ``Bearer <token>``
- ``cpf_cnpj`` — Brazilian tax IDs. Raw digits require context keyword
  within 40 chars (``CPF:`` / ``cpf`` / ``cnpj``) to avoid false-positives
  on arbitrary 11/14 digit sequences.
- ``credit_card_pan`` — Luhn-validated, matching Visa/Mastercard/Amex/Discover
  prefixes.
- ``email_in_log`` — email shape AND nearby context keyword (``user`` /
  ``email`` / ``login`` within 20 chars). This context-gating avoids
  docs/code that reference emails without leaking PII.
- ``entropy`` — high-entropy 24+ char token (pipeline step 4).

## Modes

- ``flag`` mode — return ``ScanResult`` with ``redacted_text == original``.
  Consumer emits audit event, output preserved.
- ``redact`` mode — replace each match with ``[REDACTED:FAMILY]``. Audit
  event still emitted. Sprint 11 default is ``flag``; Sprint 12 flip to
  ``redact`` criterion: ≤1 false-positive per 1000 outputs over 30 days
  (see ADR-036).

## Non-goals

- **Does NOT scan inputs.** That's ``scan-injection.py``'s job.
- **Does NOT block.** Always advisory. ``check_output_safety.py`` always
  returns ``decision: allow``.
- **Does NOT normalize control chars ``\\n`` / ``\\t``** — those stay
  intact so regex line anchors + embedded whitespace still work.

## Stdlib-only
"""

from __future__ import annotations

import base64
import binascii
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Tuple


# Maximum input size (1 MiB) — bounds CPU on adversarial inputs.
_MAX_BYTES = 1024 * 1024

# Snippet radius for preview around a match
_SNIPPET_RADIUS = 60

# Step 3 (base64 decode) — gates
_B64_MIN_LEN = 40
_B64_MIN_ENTROPY = 4.0
_B64_INFLATION_CAP = 4  # decoded len must be <= encoded len * 4

# Step 4 (entropy) — gates
_ENTROPY_MIN_RUN = 24
_ENTROPY_THRESHOLD = 4.5

# Context window for CPF/CNPJ + email-in-log gating
_CONTEXT_WINDOW = 40
_EMAIL_CONTEXT_WINDOW = 20


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


@dataclass
class Match:
    """One pattern hit."""

    family: str
    start: int
    end: int
    snippet: str  # redacted / preview-safe


@dataclass
class ScanResult:
    """Scanner output across all pipeline steps."""

    matched: bool
    family_counts: Dict[str, int] = field(default_factory=dict)
    match_count: int = 0
    bytes_scanned: int = 0
    truncated: bool = False
    redacted_text: str = ""  # if mode='redact', the post-redaction text
    # Per-pipeline-step diagnostic counts (H14 observability requirement)
    pipeline_step_counts: Dict[str, int] = field(default_factory=dict)
    matches: List[Match] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline step 1 — NFKC normalization
# ---------------------------------------------------------------------------


def _nfkc(text: str) -> str:
    """NFKC-normalize to collapse full-width / compatibility glyphs."""
    return unicodedata.normalize("NFKC", text)


# ---------------------------------------------------------------------------
# Pipeline step 2 — strip zero-width / bidi / control chars
# ---------------------------------------------------------------------------


# Zero-width: U+200B ZERO WIDTH SPACE .. U+200F RIGHT-TO-LEFT MARK
# Bidi overrides: U+202A .. U+202E, plus U+2066..U+2069 (isolates)
# Also U+FEFF ZERO WIDTH NO-BREAK SPACE (BOM) and U+180E MONGOLIAN VOWEL SEPARATOR
_STRIP_CHARS = set(
    list(range(0x200B, 0x2010))  # 200B-200F
    + list(range(0x202A, 0x202F))  # 202A-202E + 202F (narrow nbsp is also invisible)
    + list(range(0x2066, 0x206A))  # 2066-2069
    + [0xFEFF, 0x180E]
)


def _strip_invisibles(text: str) -> Tuple[str, int]:
    """Drop zero-width / bidi chars; strip C0/C1 controls except \\n\\t\\r.

    Returns ``(clean_text, dropped_count)``.
    """
    out_chars = []
    dropped = 0
    for ch in text:
        cp = ord(ch)
        if cp in _STRIP_CHARS:
            dropped += 1
            continue
        # C0 / C1 control chars: keep only \n (0x0A), \t (0x09), \r (0x0D)
        if cp < 0x20 and cp not in (0x09, 0x0A, 0x0D):
            dropped += 1
            continue
        if 0x7F <= cp <= 0x9F:  # DEL + C1
            dropped += 1
            continue
        out_chars.append(ch)
    return "".join(out_chars), dropped


# ---------------------------------------------------------------------------
# Pipeline step 3 — bounded base64 decode (depth 1)
# ---------------------------------------------------------------------------


_B64_TOKEN_RE = re.compile(r"[A-Za-z0-9+/=_\-]{40,}")


def _looks_b64(candidate: str) -> bool:
    """Quick heuristic — base64 alphabet only, length >= 40, entropy >= 4.0."""
    if len(candidate) < _B64_MIN_LEN:
        return False
    # Trim trailing '=' padding for entropy calc (padding deflates it)
    if shannon_entropy(candidate.rstrip("=")) < _B64_MIN_ENTROPY:
        return False
    return True


def _try_decode_b64(candidate: str) -> Optional[str]:
    """Attempt one-level base64 decode. Returns decoded utf-8 or None.

    Also tries urlsafe_b64 (``-``/``_`` substitutions) since that's what
    most JWTs / API tokens use.
    """
    for decoder_name in ("standard", "urlsafe"):
        try:
            # Pad to multiple of 4 for urlsafe inputs that dropped padding
            padded = candidate + "=" * (-len(candidate) % 4)
            if decoder_name == "standard":
                raw = base64.b64decode(padded, validate=False)
            else:
                raw = base64.urlsafe_b64decode(padded)
        except (binascii.Error, ValueError):
            continue
        # Inflation guard: decoded must not balloon beyond 4x encoded
        if len(raw) > len(candidate) * _B64_INFLATION_CAP:
            continue
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Binary payload — still useful if it contains printable secrets,
            # but we only care about text patterns. Fall back to replace.
            decoded = raw.decode("utf-8", errors="replace")
        # Skip if decoded is shorter than a likely secret (noise)
        if len(decoded) < 8:
            continue
        return decoded
    return None


def _decode_b64_tokens(text: str) -> Tuple[str, int]:
    """Append one-level base64 decodings of high-entropy long tokens.

    Returns ``(augmented_text, decoded_count)``. The original text is
    preserved at the front; decodings are appended with ``\\n``
    separators so subsequent regex passes can match them. Depth = 1
    strictly (decoded fragments are NOT re-scanned for further b64).
    """
    augmented_parts = [text]
    decoded_count = 0
    for m in _B64_TOKEN_RE.finditer(text):
        candidate = m.group(0)
        if not _looks_b64(candidate):
            continue
        decoded = _try_decode_b64(candidate)
        if decoded is None:
            continue
        augmented_parts.append(decoded)
        decoded_count += 1
    if decoded_count == 0:
        return text, 0
    return "\n".join(augmented_parts), decoded_count


# ---------------------------------------------------------------------------
# Pipeline step 4 — Shannon entropy over 24+ char tokens
# ---------------------------------------------------------------------------


def shannon_entropy(s: str) -> float:
    """Compute Shannon entropy (bits/char) of a string.

    Empty → 0.0. Uses ``math.log2``; stdlib-only.
    """
    if not s:
        return 0.0
    counts: Dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    h = 0.0
    for c in counts.values():
        p = c / n
        h -= p * math.log2(p)
    return h


# A "token" for entropy purposes = run of printable non-whitespace
# base64-like characters. We don't include '=' in runs (padding messes up
# entropy) and we keep the run conservative to avoid matching English prose.
_ENTROPY_TOKEN_RE = re.compile(r"[A-Za-z0-9+/_\-]{%d,}" % _ENTROPY_MIN_RUN)


def _find_entropy_hits(text: str) -> List[Tuple[int, int, str]]:
    """Return list of (start, end, token) for entropy-flagged runs."""
    hits = []
    for m in _ENTROPY_TOKEN_RE.finditer(text):
        token = m.group(0)
        if shannon_entropy(token) >= _ENTROPY_THRESHOLD:
            hits.append((m.start(), m.end(), token))
    return hits


# ---------------------------------------------------------------------------
# Pipeline step 5 — canonical regex families
# ---------------------------------------------------------------------------


_API_KEY_PATTERNS: List[str] = [
    # Anthropic / OpenAI style
    r"sk-[A-Za-z0-9\-]{20,}",
    # GitHub PAT (classic)
    r"ghp_[A-Za-z0-9]{20,}",
    # GitHub fine-grained PAT
    r"github_pat_[A-Za-z0-9_]{20,}",
    # AWS access key
    r"AKIA[0-9A-Z]{16}",
    # AWS secret / session keys in assignment form
    r"aws[_\-]?(?:secret|session)[_\-]?key\s*[=:]\s*[A-Za-z0-9/+]{30,}",
]

_JWT_PATTERN = r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"

_BEARER_PATTERN = r"[Bb]earer\s+[A-Za-z0-9._\-]+"

# Brazilian national IDs (LGPD). Raw-digit regexes; the scanner applies
# a context-keyword gate AFTER matching to avoid false-positives.
_CPF_PATTERN = r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"
_CNPJ_PATTERN = r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"

# --- PLAN-113 W4-SEC: additional Brazilian LGPD identifier families. -------
#
# Design rules (avoid over-broad false-positives):
#   * Ambiguous bare-digit identifiers (RG, CNH, PIS/PASEP, passport) carry a
#     context-keyword gate AFTER the regex match — same discipline as CPF/CNPJ.
#   * Structurally-distinctive identifiers (IBAN-BR) are matched directly: the
#     `BR` prefix + fixed length is specific enough to NOT need a context gate.
#   * All regexes are \b-anchored AND length-bounded so a longer digit run
#     does not produce a spurious sub-match.

# RG (Registro Geral) — state-issued ID. Format varies by state; the most
# common (SP) grouped form is NN.NNN.NNN-X where X is a check digit/char that
# may be a digit or 'X'/'x'. We accept 8-9 leading digits in grouped or bare
# form with the trailing check char. Context-gated (collides with other
# 8-9 digit runs).
_RG_PATTERN = r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dxX]\b"

# CNH (Carteira Nacional de Habilitação) — 11 digits, no canonical separators
# (collides with bare CPF). Context-gated on CNH / habilitação keywords.
_CNH_PATTERN = r"\b\d{11}\b"

# PIS / PASEP / NIT — 11 digits, canonical grouped form NNN.NNNNN.NN-N.
# Bare 11-digit form collides with CPF/CNH, so the family is context-gated.
_PIS_PASEP_PATTERN = r"\b\d{3}\.?\d{5}\.?\d{2}-?\d{1}\b"

# Passport (Brazil) — 2 uppercase letters followed by 6 digits (e.g. AB123456).
# Generic shape → context-gated on passaporte / passport keywords.
_PASSPORT_BR_PATTERN = r"\b[A-Z]{2}\d{6}\b"

# IBAN-BR — Brazilian IBAN per ISO 13616: 29 chars total =
#   'BR' + 2 check digits + 25-char BBAN
# (BBAN = 8 bank + 5 branch + 10 account digits + 1 account-type char +
#  1 owner-type char; the last two positions are alphanumeric in practice).
# Structurally distinctive (the 'BR' prefix + fixed 29-char shape) so it is
# matched WITHOUT a context gate. Optional single spaces between the 4-char
# print groups are tolerated. Anchored + length-bounded so a longer
# alphanumeric run cannot produce a spurious sub-match.
#   BR kk  BBBB BBBB SSSS S(acct...) -> 'BR' + \d{2} + 25-char alnum BBAN.
# The BBAN is allowed to be any [A-Z0-9] (the trailing account/owner-type
# positions are letters) with optional single spaces between print groups.
# `(?!...)` is not needed; the exact 25-significant-char bound plus the \b
# anchors keep it from over-matching a longer alphanumeric run.
_IBAN_BR_PATTERN = (
    r"\bBR\d{2}"                              # BR + 2 check digits
    r"(?:\s?[A-Z0-9]){25}\b"                 # 25 BBAN chars, optional spaces
)

# Credit card shape — Luhn validation is applied post-match.
# Visa 13/16/19, Mastercard 16, Amex 15, Discover 16.
_CC_PATTERN = (
    r"\b(?:4\d{3}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}"      # Visa 16
    r"|4\d{12}"                                         # Visa 13
    r"|5[1-5]\d{2}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}"       # Mastercard
    r"|3[47]\d{2}[- ]?\d{6}[- ]?\d{5}"                  # Amex
    r"|6(?:011|5\d{2})[- ]?\d{4}[- ]?\d{4}[- ]?\d{4})\b"  # Discover
)

# Email local + domain length caps (RFC 5321 allows 64 local / 255 domain).
# Upper bounds on the quantifiers prevent catastrophic backtracking when the
# input has a long alphabet-matching run with no '@'.
_EMAIL_PATTERN = r"[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,255}\.[a-zA-Z]{2,24}"

_CPF_CONTEXT_RE = re.compile(r"\b(?:cpf|CPF)\b")
_CNPJ_CONTEXT_RE = re.compile(r"\b(?:cnpj|CNPJ)\b")
_EMAIL_CONTEXT_RE = re.compile(r"\b(?:user|email|login|mail)\b", re.IGNORECASE)

# PLAN-113 W4-SEC context gates for the ambiguous Brazilian families.
_RG_CONTEXT_RE = re.compile(r"\b(?:rg|RG|identidade|registro\s+geral)\b", re.IGNORECASE)
_CNH_CONTEXT_RE = re.compile(
    r"\b(?:cnh|CNH|habilita(?:ç|c)(?:ã|a)o|carteira\s+de\s+motorista)\b",
    re.IGNORECASE,
)
_PIS_PASEP_CONTEXT_RE = re.compile(
    r"\b(?:pis|PIS|pasep|PASEP|nit|NIT|pis/pasep)\b", re.IGNORECASE
)
_PASSPORT_CONTEXT_RE = re.compile(
    r"\b(?:passaporte|passport)\b", re.IGNORECASE
)


def _compile(pat: str, flags: int = 0) -> Pattern[str]:
    return re.compile(pat, flags)


_API_KEY_RE = [_compile(p, re.MULTILINE) for p in _API_KEY_PATTERNS]
_JWT_RE = _compile(_JWT_PATTERN)
_BEARER_RE = _compile(_BEARER_PATTERN)
_CPF_RE = _compile(_CPF_PATTERN)
_CNPJ_RE = _compile(_CNPJ_PATTERN)
_CC_RE = _compile(_CC_PATTERN)
_EMAIL_RE = _compile(_EMAIL_PATTERN)
# PLAN-113 W4-SEC — additional Brazilian LGPD identifier families.
_RG_RE = _compile(_RG_PATTERN)
_CNH_RE = _compile(_CNH_PATTERN)
_PIS_PASEP_RE = _compile(_PIS_PASEP_PATTERN)
_PASSPORT_BR_RE = _compile(_PASSPORT_BR_PATTERN)
_IBAN_BR_RE = _compile(_IBAN_BR_PATTERN)


# ---------------------------------------------------------------------------
# Luhn validator (credit_card_pan gate)
# ---------------------------------------------------------------------------


def luhn_valid(card_number: str) -> bool:
    """True if the digits-only form of card_number satisfies the Luhn checksum.

    Strips spaces and dashes before validation.
    """
    digits_only = "".join(ch for ch in card_number if ch.isdigit())
    if len(digits_only) < 13 or len(digits_only) > 19:
        return False
    total = 0
    # Process digits from rightmost to leftmost
    for i, ch in enumerate(reversed(digits_only)):
        d = int(ch)
        if i % 2 == 1:  # every second digit from the right
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ---------------------------------------------------------------------------
# Context gating for CPF/CNPJ/email
# ---------------------------------------------------------------------------


def _has_context(
    text: str,
    span_start: int,
    span_end: int,
    context_re: Pattern[str],
    window: int,
) -> bool:
    """True if context_re matches within ``window`` chars of the span."""
    left = max(0, span_start - window)
    right = min(len(text), span_end + window)
    return bool(context_re.search(text[left:right]))


# ---------------------------------------------------------------------------
# Core scan function
# ---------------------------------------------------------------------------


# Recursion guard for _snippet's context re-redaction: the family/entropy
# finders invoked during that pass construct Match objects whose own
# _snippet calls must NOT re-enter the redaction sweep. Hooks execute as
# single-threaded subprocesses, so a module global is race-free here.
_IN_SNIPPET_REDACT = False


def _snippet(text: str, start: int, end: int) -> str:
    """Short surrounding snippet for the audit preview, honoring the
    ``Match.snippet`` "redacted / preview-safe" contract (PLAN-152
    error-handling-02).

    Two masking layers:
    1. THIS match's span is replaced by ``[MASKED:n]``.
    2. The surrounding context is swept with the module's own family
       finders + entropy step and every hit is ``[REDACTED:FAMILY]``-ed
       (Codex pair-rail P1: an ADJACENT secret inside the snippet radius
       previously leaked in cleartext context).
    Fail-safe: if the context sweep raises, the snippet degrades to the
    bare mask — never the raw context.
    """
    global _IN_SNIPPET_REDACT
    s = max(0, start - _SNIPPET_RADIUS)
    e = min(len(text), end + _SNIPPET_RADIUS)
    masked = "[MASKED:%d]" % max(0, end - start)
    chunk = text[s:start] + masked + text[end:e]
    if not _IN_SNIPPET_REDACT:
        _IN_SNIPPET_REDACT = True
        try:
            others: List[Match] = []
            for finder in (
                _find_api_key_matches, _find_jwt_matches,
                _find_bearer_matches, _find_cpf_cnpj_matches,
                _find_rg_matches, _find_cnh_matches,
                _find_pis_pasep_matches, _find_passport_br_matches,
                _find_iban_br_matches, _find_credit_card_matches,
                _find_email_matches,
            ):
                others.extend(finder(chunk))
            others.extend(_find_entropy_matches(chunk, others))
            chunk = _apply_redactions(chunk, others)
        except Exception:
            chunk = masked
        finally:
            _IN_SNIPPET_REDACT = False
    chunk = chunk.replace("\n", " ").replace("\r", " ")
    return chunk.strip()[:200]


def _find_api_key_matches(text: str) -> List[Match]:
    out: List[Match] = []
    for regex in _API_KEY_RE:
        for m in regex.finditer(text):
            out.append(
                Match(
                    family="api_key",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_jwt_matches(text: str) -> List[Match]:
    out: List[Match] = []
    for m in _JWT_RE.finditer(text):
        # Require all three segments present (regex guarantees this)
        out.append(
            Match(
                family="jwt",
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
            )
        )
    return out


def _find_bearer_matches(text: str) -> List[Match]:
    out: List[Match] = []
    for m in _BEARER_RE.finditer(text):
        out.append(
            Match(
                family="bearer",
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
            )
        )
    return out


def _find_cpf_cnpj_matches(text: str) -> List[Match]:
    out: List[Match] = []
    for m in _CPF_RE.finditer(text):
        if _has_context(text, m.start(), m.end(), _CPF_CONTEXT_RE, _CONTEXT_WINDOW):
            out.append(
                Match(
                    family="cpf_cnpj",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    for m in _CNPJ_RE.finditer(text):
        if _has_context(text, m.start(), m.end(), _CNPJ_CONTEXT_RE, _CONTEXT_WINDOW):
            out.append(
                Match(
                    family="cpf_cnpj",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_rg_matches(text: str) -> List[Match]:
    """RG (Registro Geral) — context-gated state ID (PLAN-113 W4-SEC)."""
    out: List[Match] = []
    for m in _RG_RE.finditer(text):
        if _has_context(text, m.start(), m.end(), _RG_CONTEXT_RE, _CONTEXT_WINDOW):
            out.append(
                Match(
                    family="rg",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_cnh_matches(text: str) -> List[Match]:
    """CNH (driver's license) — 11 digits, context-gated (PLAN-113 W4-SEC)."""
    out: List[Match] = []
    for m in _CNH_RE.finditer(text):
        if _has_context(text, m.start(), m.end(), _CNH_CONTEXT_RE, _CONTEXT_WINDOW):
            out.append(
                Match(
                    family="cnh",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_pis_pasep_matches(text: str) -> List[Match]:
    """PIS/PASEP/NIT — context-gated (PLAN-113 W4-SEC)."""
    out: List[Match] = []
    for m in _PIS_PASEP_RE.finditer(text):
        if _has_context(
            text, m.start(), m.end(), _PIS_PASEP_CONTEXT_RE, _CONTEXT_WINDOW
        ):
            out.append(
                Match(
                    family="pis_pasep",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_passport_br_matches(text: str) -> List[Match]:
    """Brazilian passport (2 letters + 6 digits) — context-gated
    (PLAN-113 W4-SEC)."""
    out: List[Match] = []
    for m in _PASSPORT_BR_RE.finditer(text):
        if _has_context(
            text, m.start(), m.end(), _PASSPORT_CONTEXT_RE, _CONTEXT_WINDOW
        ):
            out.append(
                Match(
                    family="passport_br",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_iban_br_matches(text: str) -> List[Match]:
    """IBAN-BR — 'BR' + 2 check digits + 25-char BBAN (29 chars total).
    Structurally distinctive, so NOT context-gated (PLAN-113 W4-SEC)."""
    out: List[Match] = []
    for m in _IBAN_BR_RE.finditer(text):
        out.append(
            Match(
                family="iban_br",
                start=m.start(),
                end=m.end(),
                snippet=_snippet(text, m.start(), m.end()),
            )
        )
    return out


def _find_credit_card_matches(text: str) -> List[Match]:
    out: List[Match] = []
    for m in _CC_RE.finditer(text):
        if luhn_valid(m.group(0)):
            out.append(
                Match(
                    family="credit_card_pan",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_email_matches(text: str) -> List[Match]:
    # Short-circuit — the email regex can backtrack pathologically on
    # long no-'@' strings; skip the whole step if there's no '@' anywhere.
    if "@" not in text:
        return []
    out: List[Match] = []
    for m in _EMAIL_RE.finditer(text):
        if _has_context(text, m.start(), m.end(), _EMAIL_CONTEXT_RE, _EMAIL_CONTEXT_WINDOW):
            out.append(
                Match(
                    family="email_in_log",
                    start=m.start(),
                    end=m.end(),
                    snippet=_snippet(text, m.start(), m.end()),
                )
            )
    return out


def _find_entropy_matches(text: str, existing: List[Match]) -> List[Match]:
    """Entropy-family hits. Deduplicated against spans already covered
    by stronger (regex) families to avoid double-counting.
    """
    covered: List[Tuple[int, int]] = sorted((m.start, m.end) for m in existing)
    out: List[Match] = []
    for start, end, _token in _find_entropy_hits(text):
        # Skip if overlaps any existing match
        overlaps = False
        for cs, ce in covered:
            if not (end <= cs or start >= ce):
                overlaps = True
                break
        if overlaps:
            continue
        out.append(
            Match(
                family="entropy",
                start=start,
                end=end,
                snippet=_snippet(text, start, end),
            )
        )
    return out


def _apply_redactions(text: str, matches: List[Match]) -> str:
    """Produce redacted text replacing each match span with [REDACTED:FAMILY].

    Overlapping matches are resolved by processing right-to-left so earlier
    spans' offsets remain valid during replacement.
    """
    if not matches:
        return text
    # Sort descending by start so replacements don't shift later offsets
    spans = sorted(matches, key=lambda m: m.start, reverse=True)
    buf = text
    covered_end = len(text) + 1
    for m in spans:
        # Skip if nested inside a higher-priority span already redacted
        if m.end > covered_end:
            continue
        token = f"[REDACTED:{m.family.upper()}]"
        buf = buf[: m.start] + token + buf[m.end :]
        covered_end = m.start
    return buf


def scan(text: str, mode: str = "flag") -> ScanResult:
    """Run the full 5-step pipeline against ``text``.

    Args:
        text: Raw input (pre-normalization).
        mode: ``"flag"`` preserves original text; ``"redact"`` produces
            a redacted copy in ``ScanResult.redacted_text``.

    Returns:
        ``ScanResult`` with ``family_counts``, ``match_count``,
        ``bytes_scanned``, ``redacted_text``, ``truncated``, and
        ``pipeline_step_counts`` diagnostic map.
    """
    if mode not in ("flag", "redact"):
        mode = "flag"
    if text is None:
        text = ""

    # Bound input size to 1 MiB
    raw_bytes = text.encode("utf-8", errors="replace")
    truncated = False
    if len(raw_bytes) > _MAX_BYTES:
        truncated = True
        text = raw_bytes[:_MAX_BYTES].decode("utf-8", errors="replace")
    bytes_scanned = min(len(raw_bytes), _MAX_BYTES)

    step_counts: Dict[str, int] = {
        "nfkc_changed_chars": 0,
        "invisibles_stripped": 0,
        "b64_tokens_decoded": 0,
        "entropy_tokens_flagged": 0,
        "regex_matches": 0,
    }

    # Step 1 — NFKC
    normalized = _nfkc(text)
    step_counts["nfkc_changed_chars"] = sum(1 for a, b in zip(text, normalized) if a != b) + abs(
        len(text) - len(normalized)
    )

    # Step 2 — strip invisibles / bidi / controls
    cleaned, dropped = _strip_invisibles(normalized)
    step_counts["invisibles_stripped"] = dropped

    # Step 3 — bounded base64 decode depth=1
    augmented, decoded_count = _decode_b64_tokens(cleaned)
    step_counts["b64_tokens_decoded"] = decoded_count

    # Step 4 — entropy pre-scan (record counts; actual Match list joins after regex)
    entropy_hits = _find_entropy_hits(augmented)
    step_counts["entropy_tokens_flagged"] = len(entropy_hits)

    # Step 5 — canonical regex families
    matches: List[Match] = []
    matches.extend(_find_api_key_matches(augmented))
    matches.extend(_find_jwt_matches(augmented))
    matches.extend(_find_bearer_matches(augmented))
    matches.extend(_find_cpf_cnpj_matches(augmented))
    matches.extend(_find_rg_matches(augmented))
    matches.extend(_find_cnh_matches(augmented))
    matches.extend(_find_pis_pasep_matches(augmented))
    matches.extend(_find_passport_br_matches(augmented))
    matches.extend(_find_iban_br_matches(augmented))
    matches.extend(_find_credit_card_matches(augmented))
    matches.extend(_find_email_matches(augmented))
    step_counts["regex_matches"] = len(matches)

    # Append entropy-only matches (dedup against regex-covered spans)
    entropy_matches = _find_entropy_matches(augmented, matches)
    matches.extend(entropy_matches)

    # Aggregate
    family_counts: Dict[str, int] = {}
    for m in matches:
        family_counts[m.family] = family_counts.get(m.family, 0) + 1

    # Redaction (mode='redact') applies to the original (non-augmented)
    # text so the consumer's output shape is preserved. Spans from the
    # augmented-text scan may not line up perfectly if base64 decode
    # grew the buffer, so redaction operates on the `cleaned` (step 2)
    # view when possible, else the original.
    if mode == "redact":
        # Re-scan the non-augmented cleaned text for span fidelity
        rescan_matches: List[Match] = []
        rescan_matches.extend(_find_api_key_matches(cleaned))
        rescan_matches.extend(_find_jwt_matches(cleaned))
        rescan_matches.extend(_find_bearer_matches(cleaned))
        rescan_matches.extend(_find_cpf_cnpj_matches(cleaned))
        rescan_matches.extend(_find_rg_matches(cleaned))
        rescan_matches.extend(_find_cnh_matches(cleaned))
        rescan_matches.extend(_find_pis_pasep_matches(cleaned))
        rescan_matches.extend(_find_passport_br_matches(cleaned))
        rescan_matches.extend(_find_iban_br_matches(cleaned))
        rescan_matches.extend(_find_credit_card_matches(cleaned))
        rescan_matches.extend(_find_email_matches(cleaned))
        redacted = _apply_redactions(cleaned, rescan_matches)
    else:
        redacted = text

    return ScanResult(
        matched=bool(matches),
        family_counts=family_counts,
        match_count=len(matches),
        bytes_scanned=bytes_scanned,
        truncated=truncated,
        redacted_text=redacted,
        pipeline_step_counts=step_counts,
        matches=matches,
    )


# Public pipeline alias per task spec (SCANNER_PIPELINE)
SCANNER_PIPELINE = scan


# ---------------------------------------------------------------------------
# Public introspection helpers (tests + downstream consumers)
# ---------------------------------------------------------------------------


def families() -> List[str]:
    """Ordered list of family slugs this module can emit."""
    return [
        "api_key",
        "jwt",
        "bearer",
        "cpf_cnpj",
        # PLAN-113 W4-SEC — additional Brazilian LGPD identifier families.
        "rg",
        "cnh",
        "pis_pasep",
        "passport_br",
        "iban_br",
        "credit_card_pan",
        "email_in_log",
        "entropy",
    ]
