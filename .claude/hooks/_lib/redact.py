"""Regex-based secret redaction + SHA-256 hashing.

Port of the Python block in `.claude/scripts/audit-log.sh` with three
enhancements required by the PLAN-002 debate:

1. **No-leak invariant** — verified by property-based tests with seeded
   stdlib corpora. `redact(s)` contains no substring matching the original
   secret patterns.
2. **Idempotent** — `redact(redact(x)) == redact(x)`. Running the redactor
   twice produces the same output.
3. **Bounded growth** — `len(redact(s)) <= len(s) * 2`. DoS guard against
   pathological inputs.

## Usage

    from _lib.redact import redact_secrets, hash_description

    preview = redact_secrets(description)  # safe to log
    digest = hash_description(description)  # SHA-256 hex of raw plaintext

## What gets redacted

- JWT tokens (three base64url segments)
- Anthropic-style `sk-` keys (20+ chars)
- GitHub PATs (`ghp_...`)
- AWS access keys (`AKIA...`)
- Bearer tokens
- Hex secrets ≥ 32 chars
- URLs with embedded credentials
- `password=`, `token=`, `api_key=`, `secret=` assignments

## Why not a single catch-all pattern?

Each pattern is a separate invariant — if one regex has a bug, only that
class of secret leaks. A single "match everything that looks secret-ish"
regex is both higher-risk (missed classes) and higher-false-positive.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Pattern, Tuple

# Per-pattern (compiled regex, replacement) pairs.
# Order matters: more specific patterns first so they aren't consumed by
# broader ones downstream.
_PATTERNS: List[Tuple[Pattern[str], str]] = [
    # JWT — three base64url segments separated by dots, first segment
    # starts with "eyJ" (the base64 of `{"`)
    (re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "[JWT]"),
    # Anthropic / OpenAI style API keys (sk-...) — 20+ chars
    (re.compile(r"\bsk-[A-Za-z0-9\-]{20,}\b"), "[API_KEY]"),
    # GitHub personal access token
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "[GITHUB_PAT]"),
    # GitHub fine-grained / installation tokens
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "[GITHUB_PAT]"),
    # AWS access key ID
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS_KEY]"),
    # Bearer tokens
    (re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._\-]+"), "Bearer [TOKEN]"),
    # URL with embedded credentials (scheme://user:pass@host)
    (re.compile(r"[a-z][a-z0-9+.\-]*://[^\s:@/]+:[^\s@]+@\S+"), "[URL_WITH_CREDS]"),
    # Hex secrets ≥ 32 chars (md5 / sha256 / hex-encoded keys)
    # Keep this AFTER AWS / JWT so those patterns get their specific labels.
    (re.compile(r"\b[A-Fa-f0-9]{32,}\b"), "[HEX_SECRET]"),
    # key=value style secrets. Capture the key name so the output preserves
    # the assignment shape for readability, but blanks the value.
    # PLAN-023 Phase H (DYN-REDACT-1): replace unbounded `\S+` with a
    # bounded-width quantifier `\S{1,2048}` so a 50KB pathological input
    # with no whitespace after `password=` no longer triggers ~2.9s
    # backtracking. 2KB is 4x the longest real secret we protect (JWT/
    # AWS/GitHub PAT all fit under 512 bytes); beyond 2KB the input is
    # demonstrably adversarial and non-matching tail is left as-is
    # (harmless — subsequent patterns sweep it if they apply).
    (
        re.compile(
            r"(?i)(password|passwd|pwd|secret|token|api[_\-]?key|client[_\-]?secret)"
            r"\s*[=:]\s*\S{1,2048}"
        ),
        r"\1=[REDACTED]",
    ),
    # P2-SEC-G (PLAN-019): Slack bot token (xoxb-<10+>-<10+>-<24+>)
    (re.compile(r"xoxb-\d{10,}-\d{10,}-[A-Za-z0-9]{24,}"), "[SLACK_BOT]"),
    # P2-SEC-G: Stripe API key (sk_live_ / sk_test_)
    (re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{24,}"), "[STRIPE_KEY]"),
    # P2-SEC-G: Google OAuth refresh token (1//0...)
    (re.compile(r"1//0[A-Za-z0-9_\-]{40,}"), "[GOOGLE_REFRESH]"),
    # P2-SEC-G: SSH / PGP private key header marker
    (
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA |)PRIVATE KEY-----"),
        "[SSH_PRIVATE_KEY_HEADER]",
    ),
    # P2-SEC-G: AWS secret access key (40-char base64, context-gated to
    # aws-secret-like marker or AKIA neighborhood to reduce false-positives).
    (
        re.compile(
            r"(?is)(aws[_\s\-]*secret[_\s\-]*access[_\s\-]*key"
            r"|AKIA[0-9A-Z]{16}[^\n]{0,200}?)"
            r"([A-Za-z0-9/+]{40})(?![A-Za-z0-9/+])"
        ),
        r"\1[AWS_SECRET]",
    ),
]

# Safety cap: input strings longer than this are truncated before
# redaction. Protects against adversarial DoS via pathological backtracking.
_MAX_INPUT_CHARS = 64 * 1024  # 64 KB

# PLAN-025 F-sec-004: tighter input cap for preview-mode callers that
# only need a short output (audit-log desc_preview etc.). Reduces ReDoS
# blast radius on the hot path (audit-log write) by 16x vs the 64KB cap.
# Callers wanting full content redaction still call redact_secrets().
_MAX_PREVIEW_INPUT_CHARS = 4 * 1024  # 4 KB

# After redaction, the preview is truncated to this length.
DEFAULT_PREVIEW_CHARS = 120


def redact_secrets(text: str, *, max_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Redact known secret patterns from text and return a bounded preview.

    Args:
        text: Input text (typically a Claude Code agent description).
        max_chars: Truncate the redacted output to this many chars. The
            tail is replaced with "..." to signal truncation. Pass 0 for
            no truncation (used by fixture anonymization tests).

    Returns:
        Redacted, whitespace-collapsed, truncated string. Safe to log.

    Invariants (tested in test_redact.py):
        - No original secret substring survives
        - Idempotent: redact_secrets(redact_secrets(x)) == redact_secrets(x)
        - Bounded growth: len(out) <= len(in) * 2  (ignoring truncation).
          If the cap is exceeded the output is TRUNCATED (fail-safe), never
          raises. A breadcrumb is emitted to stderr.
    """
    if text is None:
        return ""

    # DoS guard: clamp input size before regex
    original_len = len(text)
    if original_len > _MAX_INPUT_CHARS:
        text = text[:_MAX_INPUT_CHARS]
        original_len = _MAX_INPUT_CHARS

    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)

    # -------------------------------------------------------------------------
    # F-7.6-bounded-growth safety cap (PLAN-113 W4-SEC):
    # Verify the redaction output has not grown beyond 2× the (post-clamp)
    # input length. Whitespace collapsing below can only shrink the text, so
    # we check here (before collapse) at the widest point.
    #
    # IMPORTANT: This is a FAIL-SAFE cap, NOT an assertion. Raising
    # AssertionError in the redaction path is itself a DoS/crash surface —
    # e.g., repeated short kv secrets like `token=a token=b token=c` each
    # expand `token=x` (7 chars) → `token=[REDACTED]` (16 chars), exceeding
    # 2× before any truncation. Rather than crashing, we truncate to the
    # bound (appending a redaction-marker tail) and emit a breadcrumb so the
    # condition is observable. Redaction still succeeds; no secrets leak.
    # -------------------------------------------------------------------------
    post_redact_len = len(text)
    _BOUNDED_GROWTH_FACTOR = 2
    _growth_cap = max(original_len * _BOUNDED_GROWTH_FACTOR, 64)
    if post_redact_len > _growth_cap:
        # Truncate to the cap with a marker tail so downstream readers know
        # the output was capped. "[REDACTED:overflow]" is 20 chars; reserve
        # that from the cap so we never exceed _growth_cap total.
        _OVERFLOW_TAIL = "[REDACTED:overflow]"
        _tail_len = len(_OVERFLOW_TAIL)
        _truncate_to = max(_growth_cap - _tail_len, 0)
        text = text[:_truncate_to] + _OVERFLOW_TAIL
        # Breadcrumb: use sys.stderr at DEBUG-equivalent level; never raises.
        import sys as _sys
        print(
            f"redact_secrets: bounded-growth cap triggered — "
            f"output {post_redact_len} chars exceeded {_BOUNDED_GROWTH_FACTOR}× "
            f"input {original_len} chars; truncated to {_growth_cap}. "
            f"breadcrumb=redact_overflow",
            file=_sys.stderr,
        )

    # Collapse whitespace for a tidy one-line preview
    text = " ".join(text.split())

    if max_chars > 0 and len(text) > max_chars:
        # "..." takes 3 chars, so truncate to max_chars - 3
        if max_chars > 3:
            text = text[: max_chars - 3] + "..."
        else:
            text = text[:max_chars]

    return text


def hash_description(text: str) -> str:
    """Return the SHA-256 hex digest of the raw (pre-redaction) text.

    Stored in the audit log alongside the redacted preview so downstream
    analytics can correlate / dedupe without holding plaintext.
    """
    if text is None:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def redact_preview(text: str, *, max_chars: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Redact-then-truncate with TIGHTER input cap for preview-mode callers.

    Behaviour matches ``redact_secrets`` except the input is pre-truncated
    to ``_MAX_PREVIEW_INPUT_CHARS`` (4 KiB) instead of 64 KiB before the
    regex scan. Use this wrapper on the audit-log hot path where a short
    preview is all that downstream consumers need anyway; the 4 KiB cap
    narrows ReDoS blast radius to at most 4 KiB of adversarial input per
    call.

    PLAN-025 Batch A (F-sec-004) introduces this wrapper without changing
    ``redact_secrets`` semantics (backward-compat for any adopter or
    downstream caller that imports the legacy symbol).
    """
    if text is None:
        return ""
    if len(text) > _MAX_PREVIEW_INPUT_CHARS:
        text = text[:_MAX_PREVIEW_INPUT_CHARS]
    return redact_secrets(text, max_chars=max_chars)
