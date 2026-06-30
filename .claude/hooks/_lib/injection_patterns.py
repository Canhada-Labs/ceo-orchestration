"""Harness-mimicry injection patterns catalog.

PLAN-058 Phase A2 (incident response 2026-04-24): stdlib catalog of
payloads crafted to IMITATE the harness's system-message / user-input
tagging conventions. Distinct from `scan-injection.py`'s 6 general
families (direct_override, role_injection, etc.) — harness mimicry is
a **primer behavioral attack**: payload doesn't directly command
the LLM, it lowers the LLM's guard for subsequent instructions by
looking like authoritative framework infrastructure.

## Why a separate catalog

`scan-injection.py` families target general LLM prompt injection:
- `direct_override` → "ignore previous instructions"
- `role_injection` → "you are now X"
- `instruction_disclosure` → "print your system prompt"
- `action_override` → direct exec/deploy commands
- `tool_smuggling` → fake function-call markers
- `encoded_payload` → base64/hex blobs

Harness mimicry is orthogonal — it impersonates THIS framework's
specific tag conventions (`<system-reminder>`,
`<user-prompt-submit-hook>`, etc.) OR common model-provider tokens
(`</s>`, `<|im_start|>`, `[INST]`). Detection of these tags in
WebFetch/WebSearch/MCP/sub-agent output signals the upstream
source intentionally tried to imitate harness infrastructure.

## Fail-open

All scanner functions return empty list on exception. Never raise.
Never block. Advisory observability only (ADR-010 fail-open
invariant).

## Stdlib-only

Per hook discipline (ADR-002): `re` only. No third-party
regex/aho-corasick. O(n) per pattern compile.

## Retirement criteria (PLAN-087 Wave E.4 / F-A-TDE-T-0010)

A pattern entry in ``_PATTERNS`` (4 families: harness_mimicry,
provider_tokens, role_preamble, directive_prose) becomes a
candidate for retirement when EITHER of:

(a) **Upstream fix documented.** The source attack vector is
    explicitly documented as fixed / mitigated in upstream
    Anthropic SDK release notes (or equivalent model-provider
    advisory for ``provider_tokens`` entries). Link the
    release-notes reference in the pattern's inline comment
    before retirement.

(b) **90-day zero-fire window.** The pattern has produced ZERO
    matches in the production audit log over a rolling 90-day
    window. Verify via ``audit-query.py fp-rate --pattern-family X``
    (PLAN-081 Phase 6-bis fp-rate aggregator). Pre-retirement
    requires explicit pre-deploy FPR measurement per SKILL
    Detection-as-Code budget (FPR <= 15% rolling 30-day) - silence
    can be either zero adversary activity OR a broken rule;
    investigate before retiring.

Retirement is a KERNEL edit (this file is ``_KERNEL_PATHS`` entry
per ADR-116); requires ``CEO_KERNEL_OVERRIDE`` +
"_ACK=\"I-ACCEPT\"" env vars in the parent shell at commit time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Pattern, Tuple


# -----------------------------------------------------------------
# Pattern catalog (grouped by family)
# -----------------------------------------------------------------
#
# Each entry: (family, regex). Regex is case-sensitive by default because
# harness tags are exact-string (`<system-reminder>` specifically, not
# `<System-Reminder>` as rendered). Model-provider tokens are also
# exact-form. The "Ignore previous" style heuristics are case-insensitive
# because those are loose prose attacks.
#
# Families:
#   harness_mimicry   — framework-specific tag impersonation
#   provider_tokens   — vendor chat-template markers (HF/OpenAI/Claude/etc.)
#   role_preamble     — "### System:", "You are now X", etc.
#   directive_prose   — "Ignore previous instructions", "Forget everything"


_PATTERNS: List[Tuple[str, str, int]] = [
    # -- harness_mimicry ---------------------------------------------
    # Framework infrastructure tags that MUST never appear in
    # external content. Patterns widened 2026-04-24 per PLAN-058
    # audit C-P0-02 (F-SEC-02): accept `[-_ ]?` between tokens to
    # catch bypass variants (`<system_reminder>`, `<systemreminder>`,
    # `<system reminder>`). Case-insensitive for defense-in-depth.
    ("harness_mimicry", r"<\s*system[-_ ]?reminder\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*/\s*system[-_ ]?reminder\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*user[-_ ]?prompt[-_ ]?submit[-_ ]?hook\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*/\s*user[-_ ]?prompt[-_ ]?submit[-_ ]?hook\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*command[-_ ]?name\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*local[-_ ]?command[-_ ]?stdout\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*task[-_ ]?notification\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*task[-_ ]?id\s*>", re.IGNORECASE),
    ("harness_mimicry", r"<\s*tool[-_ ]?use[-_ ]?id\s*>", re.IGNORECASE),
    # -- provider_tokens --------------------------------------------
    # Exact-case: these are model chat-template markers used across
    # major providers. Seeing them in WebFetch/WebSearch content is a
    # strong signal the upstream source was crafted to imitate
    # prompt-template infrastructure.
    ("provider_tokens", r"</s>", 0),
    ("provider_tokens", r"<\|im_start\|>", 0),
    ("provider_tokens", r"<\|im_end\|>", 0),
    ("provider_tokens", r"<\|endoftext\|>", 0),
    ("provider_tokens", r"\[INST\]", 0),
    ("provider_tokens", r"\[/INST\]", 0),
    ("provider_tokens", r"<<SYS>>", 0),
    ("provider_tokens", r"<<\/SYS>>", 0),
    ("provider_tokens", r"<\|start_header_id\|>", 0),
    ("provider_tokens", r"<\|eot_id\|>", 0),
    # -- role_preamble ----------------------------------------------
    # Loose matches for role/persona preambles. Case-insensitive.
    ("role_preamble", r"^\s*###\s+System:", re.IGNORECASE | re.MULTILINE),
    ("role_preamble", r"^\s*###\s+Instruction:", re.IGNORECASE | re.MULTILINE),
    ("role_preamble", r"^\s*Human:\s", re.IGNORECASE | re.MULTILINE),
    ("role_preamble", r"^\s*Assistant:\s", re.IGNORECASE | re.MULTILINE),
    ("role_preamble", r"\bYou are now\b", re.IGNORECASE),
    ("role_preamble", r"\bYou are a\b", re.IGNORECASE),
    # -- directive_prose --------------------------------------------
    # Prose attacks asking the model to change behavior. Case-insensitive.
    ("directive_prose", r"\bIgnore\s+(?:(?:all|the|any|your|all\s+the)\s+)?previous\s+(?:instructions|messages|directives)\b", re.IGNORECASE),
    ("directive_prose", r"\bForget\s+(?:(?:all|the|any|your|all\s+the)\s+)?(?:previous|prior|earlier|preceding)\b", re.IGNORECASE),
    ("directive_prose", r"\bDisregard\s+(?:(?:all|the|any|your|all\s+the)\s+)?(?:previous|prior|above|earlier|preceding)\b", re.IGNORECASE),
    ("directive_prose", r"\bOverride\s+(?:(?:the|a|any|your)\s+)?(?:system|default|safety)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class Match:
    family: str
    pattern: str
    start: int
    end: int
    text: str
    snippet: str


@dataclass(frozen=True)
class ScanResult:
    matched: bool
    matches: List[Match]
    family_counts: Dict[str, int]
    bytes_scanned: int
    truncated: bool


# Module-level compiled patterns for repeated scans. Lazy-init so
# import stays cheap if hook doesn't scan in this invocation.
_COMPILED: Optional[List[Tuple[str, Pattern[str]]]] = None


def _compiled_patterns() -> List[Tuple[str, Pattern[str]]]:
    """Return cached family-tagged compiled pattern list."""
    global _COMPILED
    if _COMPILED is None:
        out: List[Tuple[str, Pattern[str]]] = []
        for family, pat, flags in _PATTERNS:
            try:
                out.append((family, re.compile(pat, flags)))
            except re.error:
                continue  # skip bad pattern (shouldn't happen with stdlib re)
        _COMPILED = out
    return _COMPILED


def _make_snippet(text: str, start: int, end: int, *, context: int = 40) -> str:
    """Extract `±context` bytes around the match for human review."""
    a = max(0, start - context)
    b = min(len(text), end + context)
    snippet = text[a:b].replace("\n", "⏎")
    if a > 0:
        snippet = "…" + snippet
    if b < len(text):
        snippet = snippet + "…"
    return snippet


def scan_harness_mimicry(
    text: str,
    *,
    max_bytes: int = 1_048_576,  # 1 MiB safety cap
) -> ScanResult:
    """Scan `text` for harness-mimicry patterns. Never raises.

    Returns `ScanResult` with `.matched` True iff any pattern hit.
    """
    if not isinstance(text, str):
        return ScanResult(False, [], {}, 0, False)

    original_len = len(text.encode("utf-8", errors="replace"))
    truncated = False
    if original_len > max_bytes:
        # Truncate to max_bytes worth of chars (utf-8 safe slicing is
        # expensive; we take approximate byte slice by reducing char count)
        text = text[: max_bytes]
        truncated = True

    matches: List[Match] = []
    family_counts: Dict[str, int] = {}

    try:
        compiled = _compiled_patterns()
    except Exception:
        return ScanResult(False, [], {}, original_len, truncated)

    for family, pat in compiled:
        try:
            for m in pat.finditer(text):
                matches.append(
                    Match(
                        family=family,
                        pattern=pat.pattern,
                        start=m.start(),
                        end=m.end(),
                        text=m.group(0),
                        snippet=_make_snippet(text, m.start(), m.end()),
                    )
                )
                family_counts[family] = family_counts.get(family, 0) + 1
        except Exception:
            continue  # skip failing pattern, don't fail the scan

    return ScanResult(
        matched=len(matches) > 0,
        matches=matches,
        family_counts=family_counts,
        bytes_scanned=min(original_len, max_bytes),
        truncated=truncated,
    )


# Convenience: exported pattern summary for documentation/tests.
def family_names() -> List[str]:
    """Return sorted list of unique family names in the catalog."""
    return sorted({family for family, _, _ in _PATTERNS})


def patterns_by_family() -> Dict[str, int]:
    """Return {family: count} map for inspection."""
    counts: Dict[str, int] = {}
    for family, _, _ in _PATTERNS:
        counts[family] = counts.get(family, 0) + 1
    return counts
