"""Output-scan redaction library (PLAN-029 / ADR-057).

Three sub-scanners for detecting harmful content in tool-call outputs
BEFORE they reach the Claude model's next turn:

1. **UnicodeInjectionScanner** — bidi overrides, zero-width chars,
   invisible separators, normalization-attack precursors.
2. **TelemetryStringScanner** — 24 known telemetry vendor strings
   (supabase.co, segment.io, mixpanel, posthog, sentry.io, etc.)
   surfaced in output that references deps or config. Addresses
   the n8n-mcp lesson (18.4k-star MIT repo ships default-ON
   telemetry with a hardcoded 10-year JWT).
3. **LLMTop10Scanner** — OWASP LLM Top 10 (2025) subset rubrica:
   LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure,
   LLM03 Supply Chain (PLAN-095 Wave B S128), LLM04 Data and Model
   Poisoning, LLM05 Improper Output Handling, LLM06 Excessive Agency,
   LLM07 System Prompt Leakage, LLM08 Vector and Embedding Weaknesses,
   LLM09 Misinformation, LLM10 Unbounded Consumption.
   2024→2025 renumbering crosswalk in `.claude/plans/PLAN-086/llm03-supplement.md`.

## Design contract

- **Stdlib-only** (ADR-002). Uses `unicodedata`, `re`, `typing`.
- **Fail-open.** Any scanner exception returns an empty finding
  list — the hook never blocks on its own bug.
- **Performance.** Each sub-scanner p99 ≤2ms on typical 1-10KB
  output; combined p99 ≤5ms. Regex-only, no heavy NLP.
- **Advisory.** Findings are emitted to audit-log as events;
  the scanner itself never redacts or blocks. Users see banner
  systemMessage when hits found.
- **Sub-scanner kill-switches.** Per-scanner `CEO_OUTPUT_SCAN_*=0`
  env vars let operators disable individual scanners.

## Public API

    scan(text: str) -> ScanResult
    scan_unicode(text: str) -> List[Finding]
    scan_telemetry(text: str) -> List[Finding]
    scan_llm_top_10(text: str) -> List[Finding]

ScanResult is a dict with counts per family + list of `Finding`
dicts for forensic evidence (family, vector, context-line-preview).
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Optional

# PLAN-086 Wave J J.1 + PLAN-095 Wave B (S128) — output_scan family count
# 9 → 10 with LLM03_2025_supply_chain family addition.
_FAMILY_COUNT = 10

# ---------------------------------------------------------------------
# Unicode injection detection
# ---------------------------------------------------------------------

# PLAN-042 ITEM 5 (FINDING-8 retrospective, security-engineer P1):
# Add 2024 attack-class codepoints:
#   - U+061C ARABIC LETTER MARK (RTL trigger, bidi attack 2023-2024)
#   - U+180E MONGOLIAN VOWEL SEPARATOR (invisible, Unicode 6.3 reclassified
#     from whitespace to format)
#   - U+E0000-U+E007F TAG CHARACTERS (Riley Goodside 2024 "ASCII smuggling"
#     attack class — invisible Unicode Tag block can encode arbitrary
#     ASCII inside a single grapheme)
_BIDI_CODEPOINTS = frozenset({
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
    0x061C,  # ARABIC LETTER MARK (ITEM 5)
})
_ZERO_WIDTH_CODEPOINTS = frozenset({
    0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0xFEFF, 0x2060, 0x2063,
    0x180E,  # MONGOLIAN VOWEL SEPARATOR (ITEM 5)
})
_INVISIBLE_SEPARATORS = frozenset({0x2063, 0x2061, 0x2062, 0x2064})
# Unicode Tag block (E0000..E007F) — ITEM 5, Goodside 2024 ASCII smuggling.
# U+E0001 LANGUAGE TAG is the entry point; U+E0020..U+E007E are the
# tagged ASCII printables; U+E007F CANCEL TAG closes the sequence.
_TAG_CODEPOINT_RANGE = range(0xE0000, 0xE0080)


def _char_name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return f"U+{cp:04X}"


def scan_unicode(text: str) -> List[Dict[str, object]]:
    """Detect bidi + zero-width + invisible-separator + tag characters.

    Returns list of Finding dicts with fields: family, vector, context.
    Empty list if none found. Never raises.
    """
    findings: List[Dict[str, object]] = []
    try:
        for idx, ch in enumerate(text):
            cp = ord(ch)
            vector: Optional[str] = None
            if cp in _BIDI_CODEPOINTS:
                vector = "bidi_override"
            elif cp in _ZERO_WIDTH_CODEPOINTS:
                vector = "zero_width"
            elif cp in _INVISIBLE_SEPARATORS:
                vector = "invisible_separator"
            elif cp in _TAG_CODEPOINT_RANGE:
                # PLAN-042 ITEM 5: Goodside 2024 ASCII-smuggling class.
                vector = "tag_character"
            if vector is None:
                continue
            # Context: ±20 chars around the hit
            start = max(0, idx - 20)
            end = min(len(text), idx + 20)
            context = text[start:end].replace("\n", " ")
            findings.append({
                "family": "unicode_injection",
                "vector": vector,
                "codepoint": f"U+{cp:04X}",
                "name": _char_name(cp),
                "offset": idx,
                "context_preview": context,
            })
            # Cap at 100 findings to avoid pathological input blowup
            if len(findings) >= 100:
                break
    except Exception:
        return []
    return findings


# ---------------------------------------------------------------------
# Homoglyph / script-mixing detection (PLAN-042 ITEM 5)
# ---------------------------------------------------------------------

# Latin-lookalike ranges per Unicode script. We stage the most common
# confusable scripts; FPR is controlled by requiring the token to
# contain at least one ASCII Latin letter alongside a confusable from
# a different script (script-mixing attack).
_CYRILLIC_LOOKALIKE_RANGE = (0x0400, 0x04FF)  # Cyrillic block
_GREEK_LOOKALIKE_RANGE = (0x0370, 0x03FF)     # Greek block
_ARMENIAN_LOOKALIKE_RANGE = (0x0530, 0x058F)  # Armenian block

# Common homoglyph pairs — Cyrillic / Greek / Armenian chars visually
# identical or near-identical to ASCII Latin. Not exhaustive; focus on
# the highest-value confusables for governance paths and auth content.
_HOMOGLYPH_LATIN_LOOKALIKES = frozenset({
    # Cyrillic
    0x0430,  # а (a)
    0x0435,  # е (e)
    0x043E,  # о (o)
    0x0440,  # р (p)
    0x0441,  # с (c)
    0x0445,  # х (x)
    0x0443,  # у (y)
    0x04CF,  # ӏ (l)
    0x0410,  # А (A)
    0x0415,  # Е (E)
    0x041E,  # О (O)
    0x0420,  # Р (P)
    0x0421,  # С (C)
    0x0425,  # Х (X)
    # Greek
    0x03B1,  # α (a)
    0x03BF,  # ο (o)
    0x03C1,  # ρ (p)
    0x0391,  # Α (A)
    0x0392,  # Β (B)
    0x0395,  # Ε (E)
    0x039F,  # Ο (O)
    0x03A1,  # Ρ (P)
})


def scan_homoglyph(text: str) -> List[Dict[str, object]]:
    """Detect Latin/Cyrillic/Greek script-mixing (ITEM 5 FINDING-8).

    Heuristic: walk the text char by char. If the current "token"
    (consecutive alphabetic chars) contains both ASCII-Latin letters
    AND at least one known Latin-lookalike from a different script,
    emit a homoglyph finding for the token.

    FPR controlled by:
    - Only alphabetic-token context (digits / whitespace bail out)
    - Token length ≥ 2 (ignore single foreign letters — legit in prose)
    - Lookalike must match the curated list (not every foreign letter)

    Returns list of Finding dicts. Never raises.
    """
    findings: List[Dict[str, object]] = []
    try:
        token_start: Optional[int] = None
        has_ascii_latin = False
        has_lookalike_foreign = False
        foreign_cp: Optional[int] = None
        foreign_offset: Optional[int] = None

        def _flush(end_idx: int) -> None:
            """Emit a finding if the token was mixed-script."""
            nonlocal token_start, has_ascii_latin, has_lookalike_foreign
            nonlocal foreign_cp, foreign_offset
            if (
                token_start is not None
                and has_ascii_latin
                and has_lookalike_foreign
                and foreign_cp is not None
                and foreign_offset is not None
                and (end_idx - token_start) >= 2
            ):
                start = max(0, token_start - 10)
                end = min(len(text), end_idx + 10)
                context = text[start:end].replace("\n", " ")
                findings.append({
                    "family": "unicode_injection",
                    "vector": "homoglyph",
                    "codepoint": f"U+{foreign_cp:04X}",
                    "name": _char_name(foreign_cp),
                    "offset": foreign_offset,
                    "context_preview": context,
                })
            token_start = None
            has_ascii_latin = False
            has_lookalike_foreign = False
            foreign_cp = None
            foreign_offset = None

        for idx, ch in enumerate(text):
            cp = ord(ch)
            # ASCII-Latin letter
            if (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A):
                if token_start is None:
                    token_start = idx
                has_ascii_latin = True
                continue
            # Lookalike foreign letter
            if cp in _HOMOGLYPH_LATIN_LOOKALIKES:
                if token_start is None:
                    token_start = idx
                has_lookalike_foreign = True
                if foreign_cp is None:
                    foreign_cp = cp
                    foreign_offset = idx
                continue
            # Non-letter or unrelated letter — end of token
            _flush(idx)
            if len(findings) >= 100:
                break

        # Flush any trailing token
        _flush(len(text))
    except Exception:
        return []
    return findings


# ---------------------------------------------------------------------
# Telemetry-string detection
# ---------------------------------------------------------------------

# Known telemetry vendor strings. Not all are malicious on their own;
# the detection is advisory ("this output references a telemetry
# vendor — double-check if the caller intended that").
_TELEMETRY_VENDORS: Dict[str, List[str]] = {
    "supabase": ["supabase.co", "supabase.com", ".supabase."],
    "segment": ["segment.io", "segment.com", "api.segment.io"],
    "mixpanel": ["mixpanel.com", "api.mixpanel.com"],
    "posthog": ["posthog.com", "app.posthog.com", ".posthog."],
    "amplitude": ["amplitude.com", "api.amplitude.com"],
    "sentry": ["sentry.io", ".sentry.io", "api.sentry.io"],
    "datadog": ["datadoghq.com", "api.datadoghq.eu", "datadoghq.eu"],
    "rollbar": ["rollbar.com", "api.rollbar.com"],
    "fullstory": ["fullstory.com", "rs.fullstory.com"],
    "hotjar": ["hotjar.com", "script.hotjar.com"],
    "heap": ["heap.io", "heapanalytics.com"],
    "new_relic": ["newrelic.com", "nr-data.net"],
}

# Pre-compile patterns for performance
_TELEMETRY_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    vendor: [re.compile(re.escape(s), re.IGNORECASE) for s in strings]
    for vendor, strings in _TELEMETRY_VENDORS.items()
}

# PLAN-042 ITEM 4 (FINDING-7, security-engineer P1):
# The 12-vendor allowlist above misses n8n-mcp-class custom telemetry
# on attacker-chosen domains (`telemetry.acme-corp.io`,
# `events.vendor.net`). This generic heuristic matches a narrow shape:
# `<signal-word>.<label>.<tld>` where the tld is a short commercial TLD.
# FPR is kept low by requiring an exact signal word on the left and
# a 2-32 char second-level label. Hits are emitted with a distinct
# `vector="telemetry_generic"` so operators can measure FPR separately
# before promoting the heuristic to blocking.
_TELEMETRY_GENERIC_RE = re.compile(
    r"(?i)\b(telemetry|analytics|tracking|metrics|events|collector|beacon)\."
    r"[a-z0-9][a-z0-9-]{1,32}\.(?:com|io|net|co|app|dev|cloud)\b"
)


def scan_telemetry(text: str) -> List[Dict[str, object]]:
    """Detect references to known telemetry vendors + generic shapes.

    Two phases:
    1. Named-vendor allowlist (12 vendors) — high precision.
    2. Generic heuristic (ITEM 4) — catches custom telemetry on
       attacker-chosen domains, advisory-only.

    Returns list of Finding dicts. Never raises.
    """
    findings: List[Dict[str, object]] = []
    try:
        for vendor, patterns in _TELEMETRY_PATTERNS.items():
            for pat in patterns:
                for match in pat.finditer(text):
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].replace("\n", " ")
                    findings.append({
                        "family": "telemetry_string",
                        "vector": vendor,
                        "matched": match.group(0),
                        "offset": match.start(),
                        "context_preview": context,
                    })
                    # Cap per-vendor at 10 hits
                    if len([f for f in findings if f.get("vector") == vendor]) >= 10:
                        break

        # ITEM 4 — generic heuristic, evaluated after the named-vendor
        # sweep so known-vendor hits win the attribution race.
        for match in _TELEMETRY_GENERIC_RE.finditer(text):
            # De-dup: if the same offset was already claimed by a named
            # vendor, skip (avoid double-counting supabase.co / sentry.io
            # style matches that also fit the generic shape).
            if any(
                f.get("offset") == match.start()
                and f.get("family") == "telemetry_string"
                for f in findings
            ):
                continue
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].replace("\n", " ")
            findings.append({
                "family": "telemetry_string",
                "vector": "telemetry_generic",
                "matched": match.group(0),
                "offset": match.start(),
                "context_preview": context,
            })
            # Cap generic hits at 10
            if sum(
                1 for f in findings
                if f.get("vector") == "telemetry_generic"
            ) >= 10:
                break
    except Exception:
        return []
    return findings


# ---------------------------------------------------------------------
# OWASP LLM Top 10 (2024) subset scanner
# ---------------------------------------------------------------------

# LLM01 Prompt Injection residue (agent echoing an instruction it was told to ignore)
# PLAN-050 Phase 3 (C7 matrix): extended with role-override sigils + jailbreak persona.
_LLM01_PATTERNS: List[re.Pattern[str]] = [
    # prompt_injection_ignore_previous
    re.compile(r"(?is)\b(ignor(?:e|ing) (?:all )?previous instruction(?:s)?)\b"),
    re.compile(r"(?is)\b(disregard (?:all )?(?:previous|prior) instruction(?:s)?)\b"),
    re.compile(r"(?is)\bforget\s+everything\s+(?:before|above|so\s+far)\b"),
    # prompt_injection_sigil_system — role-override tokens
    re.compile(r"(?is)<\s*system[-_ ]reminder\b[^>]*>"),
    re.compile(r"<\|(?:system|user|assistant|im_start|im_end)\|>", re.IGNORECASE),
    # prompt_injection_sigil_instruction — markdown/BEGIN-PROMPT markers
    re.compile(r"(?:^|\n)\s*###\s+(?:Instruction|System\s+Prompt|Role)\b", re.IGNORECASE),
    re.compile(r"-{3,}\s*BEGIN\s+(?:SYSTEM\s+)?PROMPT\s*-{3,}", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]"),
    # prompt_injection_jailbreak_persona — DAN/dev-mode/unrestricted tropes
    re.compile(
        r"\byou\s+are\s+now\s+(?:DAN|an?\s+unrestricted|in\s+developer\s+mode)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bpretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+unrestricted|a\s+jailbroken)\b",
        re.IGNORECASE,
    ),
]

# LLM02 Insecure Output Handling — hints of exec-capable content in output
# PLAN-050 Phase 3 (C7 matrix): extended with encoded exfil + data/file URLs.
_LLM02_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"(?is)<script[^>]*>"),
    re.compile(r"(?is)javascript:"),
    # data_url_reference — general data: URLs (any mime)
    re.compile(r"\bdata:[a-zA-Z0-9/.+-]+;(?:base64|charset)[^\s]{10,}"),
    re.compile(r"(?is)data:text/html"),
    # Shell command substitution
    re.compile(r"\$\([^)]*(?:rm|curl|wget|nc|bash|sh) "),
    # file_url_reference — local file loader
    re.compile(r"\bfile://(?:[A-Za-z]:)?/[^\s<>\"]{3,}"),
    # encoded_exfil_base64 — ≥200 contiguous base64 chars (outside code fence
    # honored by strip-fence preprocessing in scan_llm_top_10 helper).
    re.compile(r"[A-Za-z0-9+/]{200,}={0,2}"),
    # encoded_exfil_hex — ≥160 contiguous hex chars (80+ bytes of data)
    re.compile(r"\b[0-9a-fA-F]{160,}\b"),
    # encoded_exfil_url_encoded — ≥10 consecutive %XX sequences
    re.compile(r"(?:%[0-9A-Fa-f]{2}){10,}"),
]

# LLM06 Sensitive Info Disclosure — raw secret-like tokens
# Note: this is advisory overlap with `_lib/redact` — the output-scan
# flags secrets that SHOULD have been redacted upstream. Divergence
# signal.
#
# PLAN-042 ITEM 9 (FINDING-12 retrospective, security-engineer):
# Baseline covered 5 shapes. Missing major issuers that commonly
# land in tool outputs (git remotes, env dumps, stack traces). The
# 12 additions below cover the major vendors the framework governs.
_LLM06_PATTERNS: List[re.Pattern[str]] = [
    # --- Original 5 ---
    # OpenAI-style
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    # GitHub user/server
    re.compile(r"\bghp_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}"),
    # AWS access key
    re.compile(r"\bAKIA[0-9A-Z]{16}"),
    # JWT-ish (three b64 segments)
    re.compile(
        r"\beyJ[A-Za-z0-9+/=_-]{10,}\.[A-Za-z0-9+/=_-]{10,}\.[A-Za-z0-9+/=_-]{10,}"
    ),
    # --- PLAN-042 ITEM 9 additions (12) ---
    # Anthropic API keys — sk-ant-* (THIS framework's vendor — critical)
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"),
    # GitHub user-to-server + server-to-server + GitHub app refresh
    re.compile(r"\bghu_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghs_[A-Za-z0-9]{20,}"),
    re.compile(r"\bghr_[A-Za-z0-9]{20,}"),
    # GitLab personal access tokens
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"),
    # Slack (bot / user / app-level)
    re.compile(r"\bxox[bpoa]-[A-Za-z0-9-]{10,}"),
    # Google API keys (AIza*)
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),
    # Stripe live keys (publishable + secret)
    re.compile(r"\b(?:pk|sk)_live_[A-Za-z0-9]{20,}"),
    # Stripe restricted keys (rk_live_)
    re.compile(r"\brk_live_[A-Za-z0-9]{20,}"),
    # Square (sq0atp-)
    re.compile(r"\bsq0atp-[A-Za-z0-9_-]{20,}"),
    # SendGrid (SG.*)
    re.compile(r"\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    # Bearer token header (generic)
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9+/=_.-]{20,}"),
]

# LLM08 Excessive Agency — agent proposing actions outside scope
# PLAN-050 Phase 3 (C7 matrix): extended with tool-invocation sigils
# (output trying to re-enter the agent loop).
_LLM08_PATTERNS: List[re.Pattern[str]] = [
    # Raw shell rm -rf / destructive commands in output
    re.compile(r"(?is)\brm\s+-rf\s+(?:/|~|\$HOME)"),
    # Force-push
    re.compile(r"(?is)\bgit push (?:--force|-f)\b(?!-with-lease)"),
    # Disable hooks
    re.compile(r"(?is)--no-verify\b"),
    # tool_invocation_sigil — output attempts to re-enter agent loop
    re.compile(r"<\s*(?:tool_use|function_calls?|invoke)\b", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*function_call\s*:\s*[{\"]", re.IGNORECASE),
]

# LLM10 Model Theft — patterns indicating system-prompt exfiltration attempts
_LLM10_PATTERNS: List[re.Pattern[str]] = [
    re.compile(r"(?is)\b(print (?:your|the) system prompt)\b"),
    re.compile(r"(?is)\b(reveal (?:your|the) instructions)\b"),
    re.compile(r"(?is)\bSYSTEM PROMPT:\s*\w+"),
]

# ---------------------------------------------------------------------------
# PLAN-045 P0-10 expansion — 4 new OWASP LLM families.
# Advisory-by-default per ADR-057 FPR window. Each family has a dedicated
# env kill-switch ``CEO_OUTPUT_SCAN_LLM0X=0`` to disable; default-on once
# each family's 7-day observation period confirms low FPR on framework
# traffic. Staged code + 30-test suite landed at
# ``.claude/plans/PLAN-045/staged-code/`` before this merge.
# ---------------------------------------------------------------------------

# LLM04 Data & Model Poisoning — bidirectional (poison/training) + backdoor
# trigger tokens + watermark tamper + trojan model references.
_LLM04_PATTERNS: List[re.Pattern[str]] = [
    re.compile(
        r"\b(backdoor|trigger[\s_-]?token|magic[\s_-]?phrase)\b.{0,60}"
        r"\b(activate|inject|embed|poison)\b"
        r"|"
        r"\b(activate|inject|embed|poison)\b.{0,60}"
        r"\b(backdoor|trigger[\s_-]?token|magic[\s_-]?phrase)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(training[\s_-]?data|fine[\s_-]?tune[\s_-]?corpus|dataset|"
        r"training[\s_-]?(?:set|corpus))\b.{0,40}"
        r"\b(poison|corrupt|taint|adversarial[\s_-]?sample)\b"
        r"|"
        r"\b(poison|corrupt|taint|adversarial[\s_-]?sample)\b.{0,40}"
        r"\b(training[\s_-]?data|fine[\s_-]?tune[\s_-]?corpus|dataset|"
        r"training[\s_-]?(?:set|corpus))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(gradient[\s_-]?inversion|membership[\s_-]?inference|"
        r"model[\s_-]?extraction[\s_-]?attack)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(remove|strip|bypass|defeat)\b.{0,30}\b(watermark|"
        r"provenance[\s_-]?tag|signature[\s_-]?fingerprint)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(label[\s_-]?flip(ping)?|noise[\s_-]?inject(ion)?|"
        r"adversarial[\s_-]?label)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btrojan\b.{0,30}\b(model|weights|checkpoint|finetune)\b",
        re.IGNORECASE,
    ),
]

# LLM05 Improper Output Handling — un-sanitised downstream use
# (shell/SQL/HTML/path/eval/SSRF).
_LLM05_PATTERNS: List[re.Pattern[str]] = [
    # Shell command-chain injection (tightened: requires chained cmd /
    # pipe-to-interpreter / backtick-with-destructive-verb / redirect).
    re.compile(
        r"\b(?:run|execute|exec|system|shell|bash|zsh|sh)\b"
        r"[^\n]{0,60}"
        r"(?:"
        r"[;&]\s*(?:rm|mv|cp|dd|curl|wget|nc|bash|sh|python)\b"
        r"|\|\s*(?:bash|sh|python|curl)\b"
        r"|`[^`\n]*\b(?:rm|curl|wget|nc)\b"
        r"|>\s*/(?!dev/null)[a-z]"
        r")",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:'|\")\s*(?:OR|AND)\s+(?:1\s*=\s*1|'[a-z]'\s*=\s*'[a-z]')|"
        r"\bUNION\s+SELECT\b|\bDROP\s+TABLE\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\.\./\.\./\.\./|\\\.\.\\\.\.\\|%2e%2e%2f|%2e%2e/",
        re.IGNORECASE,
    ),
    re.compile(
        r"<\s*script\b[^>]*>|javascript:\s*[a-z]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(eval|exec)\s*\(\s*[\"'].*?[\"']\s*\)",
        re.IGNORECASE,
    ),
    re.compile(
        r"https?://(?:127\.0\.0\.1|localhost|0\.0\.0\.0|"
        r"169\.254\.169\.254|metadata\.google\.internal|"
        r"metadata\.azure\.com)",
        re.IGNORECASE,
    ),
]

# LLM07 Insecure Plugin Design / System Prompt Leakage (OWASP 2024 renamed
# from Insecure Plugin Design to include System Prompt Leakage).
_LLM07_PATTERNS: List[re.Pattern[str]] = [
    re.compile(
        r"\b(my[\s_-]?system[\s_-]?prompt|initial[\s_-]?instructions|"
        r"developer[\s_-]?message|system[\s_-]?message\s+says?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|\n)\s*(?:<\|im_(?:start|end)\|>|###\s*(?:System|Assistant|User)|"
        r"\[INST\]|\[/INST\])",
    ),
    re.compile(
        r"\b(?:API_KEY|SECRET|PRIVATE_KEY|TOKEN|PASSWORD|"
        r"BEARER_TOKEN|AWS_SECRET)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-+=/]{16,}",
    ),
    re.compile(
        r"\b(my[\s_-]?(?:instructions?|guidelines?|rules?)\s+"
        r"(?:say|state|are|include))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(plugin[\s_-]?manifest|tool[\s_-]?definition|"
        r"function[\s_-]?schema)\b.{0,30}\b(reveal|show|display|echo|expose|dump|leak)\b"
        r"|"
        r"\b(reveal|show|display|echo|expose|dump|leak)\b.{0,30}"
        r"\b(plugin[\s_-]?manifest|tool[\s_-]?definition|"
        r"function[\s_-]?schema)\b",
        re.IGNORECASE,
    ),
]

# LLM09 Overreliance / Misinformation — hallucination red flags.
# Most FP-prone family; conservative set.
_LLM09_PATTERNS: List[re.Pattern[str]] = [
    re.compile(
        r"\b(?:definitely|certainly|without[\s_-]?doubt|"
        r"it[\s']?s[\s_-]?a[\s_-]?fact[\s_-]?that)\b.{0,60}"
        r"\b\d{2,3}(?:\.\d+)?%",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b[A-Z][a-z]+\s+et\s+al\.?\s*\(?(?:19|20)\d{2}\)?",
    ),
    re.compile(
        r"\b(built[\s_-]?in|standard|official)\s+\w+(?:\.\w+){1,3}\s*"
        r"\(\s*\)\s+function",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bI'?m\s+(?:100\s*%|completely|absolutely|totally)\s+"
        r"(?:sure|certain|confident)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"https?://(?:example|docs|api|www)\.(?:com|org|net)/"
        r"(?:docs|reference|api)/[a-z-]+/(?:[a-z-]+/)*[a-z-]+",
        re.IGNORECASE,
    ),
]


# PLAN-095 Wave B.2 (S128) — OWASP LLM03:2025 Supply Chain detection patterns.
# Source: .claude/plans/PLAN-086/llm03-supplement.md §Detection regex set.
# Covers OWASP 2025 risk categories #1 (Third-party Package), #2 (Licensing),
# #3 (Outdated/Deprecated Models), #4 (Vulnerable Pre-Trained Model),
# #5 (Weak Provenance), #6 (Vulnerable LoRA adapters), and #7 (Exploit
# Collaborative Development Processes).
# Fixtures: tests/fixtures/atlas/LLM03-2025-supply-chain-{should-fire,should-not-fire}.ndjson
# Red-team corpus: tests/fixtures/red-team-corpus/llm03-legitimate-{installs,fetches}-25.ndjson
# Pre-deploy gate (S128 R2 iter-3 P0): runtime mode + tests/fixtures/ umbrella
# python3 .claude/scripts/check_atlas_fpr.py --pattern-class LLM03_2025_supply_chain \
#     --scan-payload-preview --corpus tests/fixtures/ --threshold 0.15 --min-tpr 0.80
_LLM03_2025_SUPPLY_CHAIN_PATTERNS: List[re.Pattern[str]] = [
    # Risk #1 (Traditional package) + #2 (Licensing) — S128 R2 iter-3 P0:
    # horizontal whitespace [^\S\n] excludes newlines; flag-with-value
    # consumes --index-url <url> etc.
    re.compile(
        r"\b(pip|pip3)[^\S\n]+install\b"
        r"(?![^\n]*(?:--requirement\b|--require-hashes\b|-r\b))"
        r"(?:[^\S\n]+--?[A-Za-z][A-Za-z0-9-]*(?:=\S+|[^\S\n]+\S+)?)*"
        r"[^\S\n]+([A-Za-z0-9][A-Za-z0-9_.-]*)"
    ),
    # S128 R2 iter-3 P0: horizontal whitespace + lockfile neg lookahead.
    re.compile(
        r"\b(npm|pnpm|yarn)[^\S\n]+(?:add|install)\b"
        r"(?![^\n]*(?:--save-dev\b|--save\b|-D\b|--frozen-lockfile\b"
        r"|[^\S\n]ci\b))"
        r"(?:[^\S\n]+--?[A-Za-z][A-Za-z0-9-]*(?:=\S+|[^\S\n]+\S+)?)*"
        r"[^\S\n]+([A-Za-z0-9@][A-Za-z0-9@/_.-]*)"
    ),
    # S128 R2 iter-3 P0: --git <url> URL absorbed by flag-with-value.
    re.compile(
        r"\bcargo[^\S\n]+install\b"
        r"(?![^\n]*(?:--locked\b|--registry\b))"
        r"(?:[^\S\n]+--?[A-Za-z][A-Za-z0-9-]*(?:=\S+|[^\S\n]+\S+)?)*"
        r"[^\S\n]+([A-Za-z0-9][A-Za-z0-9_-]*)"
    ),
    # **S128 R2 iter-3 P0**: mcp_unrecognized_server pattern DEFERRED
    # to PLAN-095-FOLLOWUP (runtime allowlist check needed; naive
    # regex was 18% FP on shipped corpus).
    # Risk #1 + #5 — External fetch without integrity checksum.
    # S128 R2 iter-3 P0: --cacert /path/to/ca.pem absorbed by flag-w-value.
    re.compile(
        r"\b(curl|wget)\b"
        r"(?![^\n]*(?:--checksum\b|--hash\b|--cacert\b|--verify\b"
        r"|--ca-cert\b|--ca-certificate\b))"
        r"(?:[^\S\n]+--?[A-Za-z][A-Za-z0-9-]*(?:=\S+|[^\S\n]+\S+)?)*"
        r"[^\S\n]+(https?://[^\s]+)"
    ),
    # Risk #4 (Vulnerable Pre-Trained Model) + #5 (Weak Provenance).
    # SSH form `git@github.com:...` is a known FN (defer to FOLLOWUP).
    re.compile(
        r"\bgit[^\S\n]+clone\b"
        r"(?:[^\S\n]+--?[A-Za-z][A-Za-z0-9-]*(?:=\S+|[^\S\n]+\S+)?)*"
        r"[^\S\n]+(https?://(?!github\.com/anthropics/)"
        r"(?!github\.com/Canhada-Labs/)[^\s]+)"
    ),
    # Risk #4 + #6 (Vulnerable LoRA adapter) — Hugging Face direct
    # model/adapter download via /resolve/ or /raw/ endpoints only.
    re.compile(
        r"(?:huggingface\.co/|hf://)"
        r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"
        r"(?:/resolve/|/raw/)",
        re.IGNORECASE,
    ),
    # Risk #3 (Outdated/Deprecated Models) — explicit deprecation
    # markers in model reference. Conservative — only flags 5 specific
    # markers, not generic "deprecation" prose.
    re.compile(
        r"\b(?:model[-_]deprecated|deprecated[-_]model|legacy[-_]model"
        r"|sunset[-_]model|EOL[-_]model)\b",
        re.IGNORECASE,
    ),
]


# PLAN-106 Wave H.1 (absorbing PLAN-095-FOLLOWUP §B.5) — closed-enum
# of stable pattern_ids. Sec MF-3 emit gate at
# `_lib.audit_emit._OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST` rejects
# any value outside this set (defense-in-depth: pattern_id is part of
# the composite-dedup-key and must NEVER be derived from runtime
# finding content).
#
# Naming convention: `<FAMILY>_<intent>` where FAMILY matches the
# LLM_PATTERN_GROUPS key prefix and `intent` is a stable hand-curated
# identifier for the regex *intent*, not the regex source.
_PATTERN_IDS = frozenset({
    # LLM01 prompt injection
    "LLM01_ignore_previous_instructions",
    "LLM01_system_role_override",
    "LLM01_jailbreak_dan",
    # LLM02 insecure output handling
    "LLM02_html_script_tag",
    "LLM02_data_url_html",
    "LLM02_javascript_url",
    # LLM03 supply chain (2025 renumber)
    "LLM03_pip_install_uncited",
    "LLM03_npm_install_uncited",
    "LLM03_curl_bash_pipe",
    "LLM03_typosquat_candidate",
    # LLM04 data + model poisoning
    "LLM04_training_data_request",
    "LLM04_fine_tune_endpoint",
    # LLM05 improper output handling
    "LLM05_shell_command_substitution",
    "LLM05_file_url_local_loader",
    "LLM05_base64_exfil_long",
    "LLM05_hex_exfil_long",
    "LLM05_url_encoded_exfil_long",
    # LLM06 sensitive info disclosure (raw secrets)
    "LLM06_openai_sk_prefix",
    "LLM06_anthropic_api_key",
    "LLM06_github_classic_pat",
    "LLM06_github_user_to_server",
    "LLM06_github_server_to_server",
    "LLM06_github_oauth_app_refresh",
    "LLM06_github_app_refresh",
    "LLM06_gitlab_pat",
    "LLM06_aws_access_key",
    "LLM06_slack_token",
    "LLM06_google_api_key",
    "LLM06_stripe_live_key",
    "LLM06_stripe_restricted_key",
    "LLM06_square_token",
    "LLM06_sendgrid_token",
    "LLM06_bearer_header",
    "LLM06_jwt_three_segment",
    # LLM07 system prompt leakage
    "LLM07_system_prompt_label",
    "LLM07_reveal_instructions",
    "LLM07_print_system_prompt",
    # LLM08 excessive agency
    "LLM08_rm_rf_destructive",
    "LLM08_git_force_push",
    "LLM08_disable_hooks",
    "LLM08_tool_invocation_sigil",
    "LLM08_function_call_sigil",
    # LLM09 misinformation
    "LLM09_hallucinated_citation",
    "LLM09_confident_unsupported",
    # LLM10 model theft / unbounded consumption
    "LLM10_system_prompt_exfil",
    "LLM10_model_deprecation_marker",
    # Generic fallback — unknown vector within a known family
    "LLM_unknown_vector",
})


def is_known_pattern_id(pattern_id: str) -> bool:
    """Sec MF-3 helper — check if pattern_id is in the closed enum."""
    return isinstance(pattern_id, str) and pattern_id in _PATTERN_IDS


# Family closed-enum (LLM01..LLM10 + 2025 variant).
# Used by `_lib.audit_emit._OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST`
# producer-side validation (PLAN-106 §3 Wave H.1.b security R1 P1).
_KNOWN_FAMILIES = frozenset({
    "LLM01", "LLM02", "LLM03", "LLM03_2025", "LLM04", "LLM05",
    "LLM06", "LLM07", "LLM08", "LLM09", "LLM10",
    # Full-form variants used in pattern-group keys
    "LLM01_prompt_injection",
    "LLM02_insecure_output",
    "LLM03_2025_supply_chain",
    "LLM04_data_model_poisoning",
    "LLM05_improper_output_handling",
    "LLM06_sensitive_info",
    "LLM07_system_prompt_leakage",
    "LLM08_excessive_agency",
    "LLM09_overreliance",
    "LLM10_model_theft",
})


def is_known_family(family: str) -> bool:
    return isinstance(family, str) and family in _KNOWN_FAMILIES


# Mapping from (family, regex.pattern) -> stable pattern_id. Derived by
# the framework; out-of-band entries fall back to `LLM_unknown_vector`.
# The mapping intentionally lives next to the pattern group definitions
# so a regex addition triggers a corresponding `_PATTERN_IDS` entry
# (review-time gate).
_PATTERN_ID_FOR_REGEX: Dict[str, str] = {
    # Populated lazily in `_resolve_pattern_id` so adding a new regex
    # without a paired ID falls back to the generic ID + breadcrumb
    # rather than hard-erroring. Production callers should add the
    # mapping when they add the regex.
}


def _resolve_pattern_id(family: str, regex_src: str) -> str:
    """Best-effort lookup of pattern_id for a (family, regex) pair.

    The mapping is intentionally sparse (the framework adds entries
    as patterns stabilize). Unmapped regexes return `LLM_unknown_vector`
    so the emit allowlist still admits the event.
    """
    pid = _PATTERN_ID_FOR_REGEX.get(regex_src)
    if pid and pid in _PATTERN_IDS:
        return pid
    # Heuristic fallback: derive from family prefix.
    family_short = (family or "").split("_", 1)[0] or "LLM"
    candidate = f"{family_short}_unknown_vector"
    if candidate in _PATTERN_IDS:
        return candidate
    return "LLM_unknown_vector"


_LLM_PATTERN_GROUPS: Dict[str, List[re.Pattern[str]]] = {
    "LLM01_prompt_injection": _LLM01_PATTERNS,
    "LLM02_insecure_output": _LLM02_PATTERNS,
    "LLM03_2025_supply_chain": _LLM03_2025_SUPPLY_CHAIN_PATTERNS,  # PLAN-095 Wave B S128
    "LLM04_data_model_poisoning": _LLM04_PATTERNS,
    "LLM05_improper_output_handling": _LLM05_PATTERNS,
    "LLM06_sensitive_info": _LLM06_PATTERNS,
    "LLM07_system_prompt_leakage": _LLM07_PATTERNS,
    "LLM08_excessive_agency": _LLM08_PATTERNS,
    "LLM09_overreliance": _LLM09_PATTERNS,
    "LLM10_model_theft": _LLM10_PATTERNS,
}

# PLAN-045 P0-10 + PLAN-095 Wave B.8 (S128) — per-family env kill-switches
# for ADR-057 FPR window. Setting any of these to "0" disables that
# family silently. LLM03 added per PLAN-095 AC LLM03.6.
_LLM_FAMILY_KILLSWITCH_ENV: Dict[str, str] = {
    "LLM03_2025_supply_chain": "CEO_OUTPUT_SCAN_LLM03",  # PLAN-095 Wave B.8 S128
    "LLM04_data_model_poisoning": "CEO_OUTPUT_SCAN_LLM04",
    "LLM05_improper_output_handling": "CEO_OUTPUT_SCAN_LLM05",
    "LLM07_system_prompt_leakage": "CEO_OUTPUT_SCAN_LLM07",
    "LLM09_overreliance": "CEO_OUTPUT_SCAN_LLM09",
}


def scan_llm_top_10(text: str) -> List[Dict[str, object]]:
    """Detect OWASP LLM Top 10 (2024) subset patterns in output.

    Returns list of Finding dicts. Never raises.
    """
    findings: List[Dict[str, object]] = []
    try:
        for family, patterns in _LLM_PATTERN_GROUPS.items():
            # PLAN-045 P0-10 — per-family kill-switch (ADR-057 FPR window).
            ks_env = _LLM_FAMILY_KILLSWITCH_ENV.get(family)
            if ks_env is not None and os.environ.get(ks_env) == "0":
                continue
            for pat in patterns:
                for match in pat.finditer(text):
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].replace("\n", " ")
                    findings.append({
                        "family": family,
                        "vector": pat.pattern[:50],
                        # PLAN-106 Wave H.1 — stable pattern_id for dedup.
                        # Derived from the (family, regex.pattern) mapping;
                        # unknown regexes fall back to `LLM_unknown_vector`.
                        "pattern_id": _resolve_pattern_id(family, pat.pattern),
                        "matched_len": len(match.group(0)),
                        "offset": match.start(),
                        "context_preview": context,
                    })
                    if len([f for f in findings if f.get("family") == family]) >= 10:
                        break
    except Exception:
        return []
    return findings


# ---------------------------------------------------------------------
# NFKC normalization-delta detector (PLAN-050 Phase 3 / C7 matrix)
#
# Catches homoglyph attacks that are invisible to the script-mixing
# heuristic but produce a character change under Unicode NFKC
# normalization (e.g. fullwidth Latin → halfwidth, compat ligatures,
# compat Arabic presentation forms). A single call to
# unicodedata.normalize() is ~microseconds on typical inputs; we cap
# findings at 50 to keep audit-log size bounded.
# ---------------------------------------------------------------------


def scan_nfkc_homoglyph(text: str) -> List[Dict[str, object]]:
    """Detect codepoints with **compatibility-only** NFKC deltas.

    Semantic: we compare NFC(text) vs NFKC(text). A diff means at least
    one codepoint carries a *compatibility* decomposition (fullwidth,
    superscript, ligature, compat Arabic presentation, etc.) — the
    homoglyph-adjacent class of attacks. Pure canonical composition
    (e.g. "a"+U+0301 → "á") is excluded because NFC(text) == NFKC(text)
    in that case.

    Returns list of Finding dicts (first 50). Never raises.
    """
    findings: List[Dict[str, object]] = []
    try:
        if not text:
            return findings
        nfc = unicodedata.normalize("NFC", text)
        nfkc = unicodedata.normalize("NFKC", text)
        if nfc == nfkc:
            # Only canonical-form changes — not a compat homoglyph.
            return findings
        # Walk original vs NFKC char-by-char. Index against the original
        # text so offsets are meaningful to the reader.
        norm_text = unicodedata.normalize("NFKC", text)
        max_len = min(len(text), len(norm_text))
        for i in range(max_len):
            a = text[i]
            b = norm_text[i]
            if a == b:
                continue
            # Skip combining-mark artifacts — only flag when the ORIGINAL
            # character has a compat decomposition itself (i.e. it is the
            # compat codepoint, not a neighbour affected by reordering).
            decomp = unicodedata.decomposition(a)
            if not decomp.startswith("<"):
                continue
            start = max(0, i - 10)
            end = min(len(text), i + 10)
            findings.append({
                "family": "unicode_injection",
                "vector": "nfkc_delta",
                "offset": i,
                "codepoint": f"U+{ord(a):04X}",
                "normalized_to": f"U+{ord(b):04X}",
                "name": _char_name(ord(a)),
                "context_preview": text[start:end].replace("\n", " "),
            })
            if len(findings) >= 50:
                break
        # Length mismatch with no char-level find: probably a ligature
        # that expanded. Record a single summary finding if any char has
        # a compat decomposition.
        if not findings and len(text) != len(norm_text):
            for i, ch in enumerate(text):
                if unicodedata.decomposition(ch).startswith("<"):
                    findings.append({
                        "family": "unicode_injection",
                        "vector": "nfkc_delta",
                        "offset": i,
                        "codepoint": f"U+{ord(ch):04X}",
                        "name": _char_name(ord(ch)),
                        "context_preview": text[:40].replace("\n", " "),
                    })
                    break
    except Exception:
        return []
    return findings


# ---------------------------------------------------------------------
# Top-level scan()
# ---------------------------------------------------------------------

_KILL_SWITCH_ENV = "CEO_OUTPUT_SCAN"
_SUB_KILL_UNICODE = "CEO_OUTPUT_SCAN_UNICODE"
_SUB_KILL_TELEMETRY = "CEO_OUTPUT_SCAN_TELEMETRY"
_SUB_KILL_LLM10 = "CEO_OUTPUT_SCAN_LLM10"
# PLAN-042 ITEM 5: homoglyph has higher cost than codepoint lookup
# (token walking); kept behind its own kill-switch so operators can
# disable if FPR turns out too high in dogfood.
_SUB_KILL_HOMOGLYPH = "CEO_OUTPUT_SCAN_HOMOGLYPH"
# PLAN-050 Phase 3 (C7 matrix): NFKC-delta detector. Independent
# kill-switch for FPR-tuning during 7-day observation window.
_SUB_KILL_NFKC = "CEO_OUTPUT_SCAN_NFKC"


def _kill_switch_active(var: str) -> bool:
    val = os.environ.get(var, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def scan(text: str) -> Dict[str, object]:
    """Combined scan entry point — runs all sub-scanners.

    Returns dict:
        {
          "total_findings": N,
          "family_counts": {family: count, ...},
          "findings": [finding, ...],  # up to 100 first findings
          "kill_switched": {master/unicode/telemetry/llm10/homoglyph: bool},
        }

    Never raises; individual sub-scanner exceptions degrade to
    empty findings for that family.
    """
    result: Dict[str, object] = {
        "total_findings": 0,
        "family_counts": {},
        "findings": [],
        "kill_switched": {
            "master": _kill_switch_active(_KILL_SWITCH_ENV),
            "unicode": _kill_switch_active(_SUB_KILL_UNICODE),
            "telemetry": _kill_switch_active(_SUB_KILL_TELEMETRY),
            "llm10": _kill_switch_active(_SUB_KILL_LLM10),
            "homoglyph": _kill_switch_active(_SUB_KILL_HOMOGLYPH),
            "nfkc": _kill_switch_active(_SUB_KILL_NFKC),
        },
    }

    # Master kill-switch short-circuits
    if result["kill_switched"]["master"]:
        return result

    all_findings: List[Dict[str, object]] = []

    if not result["kill_switched"]["unicode"]:
        all_findings.extend(scan_unicode(text or ""))
    if not result["kill_switched"]["telemetry"]:
        all_findings.extend(scan_telemetry(text or ""))
    if not result["kill_switched"]["llm10"]:
        all_findings.extend(scan_llm_top_10(text or ""))
    # PLAN-042 ITEM 5: homoglyph evaluated last, independent kill-switch.
    if not result["kill_switched"]["homoglyph"]:
        all_findings.extend(scan_homoglyph(text or ""))
    # PLAN-050 Phase 3 (C7 matrix): NFKC-delta detector.
    if not result["kill_switched"]["nfkc"]:
        all_findings.extend(scan_nfkc_homoglyph(text or ""))

    # Family counts
    family_counts: Dict[str, int] = {}
    for f in all_findings:
        key = str(f.get("family", "unknown"))
        family_counts[key] = family_counts.get(key, 0) + 1

    result["total_findings"] = len(all_findings)
    result["family_counts"] = family_counts
    # Cap at 100 for audit-log size discipline
    result["findings"] = all_findings[:100]
    return result
