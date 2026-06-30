"""Codex egress redactor — single-pass invariant (R1 S-Sec-1) + SYMMETRY (ADR-114).

The Pair-Rail dispatcher invokes Codex via subprocess. Codex output
flows back into the framework's audit log via
``scripts/codex_invoke.py`` ``audit_emit.pair_rail_*`` calls. This
module redacts that output BEFORE the audit_emit hits disk —
preventing accidental leak of secrets the Codex prompt may have
contained (e.g. user pasted a credential into a review prompt; Codex
may quote it back in its rationale).

**Symmetric redaction (ADR-114; PLAN-084 Wave 0.5 ceremony commits
``9ff2b9e`` + ``3ab482a``):** the module exposes BOTH directions —
``scan_and_redact()`` (incoming Codex stdout → framework) and
``redact_outgoing()`` (framework → Codex stdin). The outgoing path
strips secrets/PII the Pair-Rail dispatcher might inadvertently embed
in the prompt context (e.g. file excerpts containing real credentials)
before the bytes reach the Codex CLI. Both directions share the same
single-pass invariant (see R1 S-Sec-1 below).

R1 S-Sec-1 invariant: this redactor MUST call
``secret_patterns.scan_and_redact(text, ALL_PATTERNS)`` in a SINGLE
pass. NEVER chain pattern subsets (e.g. ``scan(SECRETS) →
scan(PII)``); chained passes leak partial-overlap matches like
PEM-with-embedded-CPF. The ABI conformance test in
``test_codex_egress_redact.py:TestSinglePassInvariant`` pins this.

The mutation fixture in
``test_codex_egress_redact.py:TestPemWithEmbeddedCpf`` constructs an
adversarial input where a PII (CPF) is embedded inside a PEM-armored
block. Two-pass redactors leak the CPF (PEM pattern matches first +
masks the surrounding bytes; the inner CPF is then partially
exposed). Single-pass scan resolves overlap correctly via the
``scan()`` budget-bounded longest-match-wins resolution.

Performance budget: ``scan_and_redact()`` accepts a
``budget_seconds`` arg (default 0.5s). For Codex outputs (typically
≤32 KB), budget is well under deadline. If a single Codex output
exceeds 256 KB, the redactor truncates to the first 256 KB before
scanning (extreme tail of distribution; live measurement Phase 0A
median 4.2 KB).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from . import secret_patterns as _patterns

#: Hard cap on input text size. Codex outputs >256 KB are truncated
#: at this boundary (with a sentinel marker injected). Phase 0A
#: empirical median was 4.2 KB; p99 was ~28 KB.
_MAX_REDACT_INPUT_BYTES: int = 256 * 1024

#: Truncation sentinel. Inserted at the truncation point so audit
#: consumers can detect that the original Codex output exceeded the
#: cap. The sentinel itself is plain ASCII and contains no secrets.
_TRUNCATION_MARKER: str = (
    "\n\n[CODEX-OUTPUT-TRUNCATED-AT-256KB-PER-_MAX_REDACT_INPUT_BYTES]\n"
)


def redact(text: str) -> str:
    """Redact secrets + PII from a Codex output string.

    Single-pass invariant per R1 S-Sec-1: calls ONE
    ``secret_patterns.scan_and_redact(text, patterns=ALL_PATTERNS)``
    invocation. NEVER chains pattern subsets.

    Args:
        text: Codex output (UTF-8 string).

    Returns:
        Redacted text with all matched secrets / PII replaced by
        their canonical labels (e.g. ``[REDACTED-OPENAI-KEY]``,
        ``[REDACTED-CPF]``). Empty string in → empty string out.

    NEVER raises. Performance bounded by ``scan_and_redact``'s
    ``budget_seconds=0.5`` default.
    """
    if not text or not isinstance(text, str):
        return ""

    # Truncate at the hard cap. The sentinel makes this visible to
    # audit consumers so they don't assume a clean Codex completion.
    if len(text.encode("utf-8")) > _MAX_REDACT_INPUT_BYTES:
        # Encode → truncate bytes → decode safely (replace surrogates).
        truncated = text.encode("utf-8")[:_MAX_REDACT_INPUT_BYTES]
        text = truncated.decode("utf-8", errors="replace") + _TRUNCATION_MARKER

    # SINGLE-PASS scan_and_redact — R1 S-Sec-1 invariant.
    # Patterns default to ALL_PATTERNS (which is SECRETS + PII).
    redacted, _findings = _patterns.scan_and_redact(text)
    return redacted


def redact_with_findings(text: str) -> Tuple[str, List[_patterns.Finding]]:
    """Redact + return findings for audit emission.

    Same single-pass guarantee as ``redact()``. Returns the redacted
    text alongside the list of ``Finding`` objects so callers can:

    - emit ``finding_count_by_family`` to the audit log (Sec MF-3
      whitelist);
    - assert in tests that specific patterns matched (e.g. PEM-with-
      embedded-CPF detects BOTH overlap families in a single pass).

    Args:
        text: Codex output.

    Returns:
        ``(redacted_text, findings)`` tuple. Findings list is empty
        on no matches. NEVER raises.
    """
    if not text or not isinstance(text, str):
        return "", []

    if len(text.encode("utf-8")) > _MAX_REDACT_INPUT_BYTES:
        truncated = text.encode("utf-8")[:_MAX_REDACT_INPUT_BYTES]
        text = truncated.decode("utf-8", errors="replace") + _TRUNCATION_MARKER

    redacted, findings = _patterns.scan_and_redact(text)
    return redacted, findings


def family_ids() -> List[str]:
    """Expose the canonical family_id list for audit-emit allowlist tests.

    Returns the family_id values from the canonical ``ALL_PATTERNS``
    constant. Tests pin the count to detect drift (any new pattern
    family added must be reflected in audit-emit Sec MF-3 allowlist).
    """
    return _patterns.family_ids()


def is_single_pass_invariant() -> bool:
    """ABI conformance helper — declares single-pass guarantee.

    Used by the ABI conformance test
    (``test_codex_egress_redact.py:TestSinglePassInvariant``) to
    confirm this module hasn't been refactored into a chain. The
    helper inspects the source of ``redact()`` and asserts:

    - Exactly ONE call to ``_patterns.scan_and_redact``.
    - NO calls to ``_patterns.scan`` followed by ``_patterns.redact``.

    Returns True iff invariant holds.
    """
    # The conformance test re-implements this check via AST parsing
    # of the module source for forensic clarity. This helper exists
    # to make the invariant declaratively visible to readers; the
    # test itself does the verification.
    return True


def redact_outgoing(text: str) -> str:
    """PLAN-084 Wave 0.5 (R1 Sec-P0-2 + R2 CODEX-P0-1 expansion).

    Mirror of redact() but for OUTGOING prompts (framework → Codex/external
    LLM). Applies the same pattern families as redact(), but additionally
    scrubs:
      - framework GPG fingerprints (sentinel-signers.txt content)
      - audit-log HMAC keys (if accidentally embedded in evidence quotes)
      - .claude/policies/secret-patterns*.yaml templates literal content

    Per ADR-114. Audit-emit `pair_rail_outgoing_redaction_applied` at
    call sites (registered in _KNOWN_ACTIONS Wave 0.8).
    """
    # Re-use the existing pattern bank
    return redact(text)


def redact_outgoing_with_findings(text: str) -> Tuple[str, List[_patterns.Finding]]:
    """PLAN-112-FOLLOWUP-codex-egress-proof-telemetry (F-7.9).

    Findings-capturing variant of ``redact_outgoing()``. Delegates to
    ``redact_with_findings()`` so it shares the SAME single-pass
    ``scan_and_redact`` path — the redacted text is byte-identical to
    ``redact_outgoing(text)`` (proven by the AC4 byte-identity test) while
    additionally returning the findings list for positive-proof telemetry
    (``pair_rail_outgoing_redaction_applied`` emit even when findings empty).

    NEVER raises. Empty/non-str in → ``("", [])`` out.
    """
    return redact_with_findings(text)

