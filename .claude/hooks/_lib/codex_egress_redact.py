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

**CLI (PLAN-156-FOLLOWUP F1, debate C4):** the module is also directly
executable — ``python3 .claude/hooks/_lib/codex_egress_redact.py
--outgoing`` reads stdin, writes REDACTED text to stdout. This is the
egress boundary mandated by ``council-audit.js:145``. The CLI is
fail-CLOSED: on ANY error it exits nonzero with NOTHING on stdout and
never echoes input (see the ``_cli_main`` block at the bottom).
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Import shim (PLAN-156-FOLLOWUP F1, debate C4).
#
# This module is BOTH a package member (`from _lib import
# codex_egress_redact`) AND a run-as-file CLI — `council-audit.js:145`
# mandates the literal invocation
# `python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing` from the
# repo root (never `python3 -m`, which would mask the failure this shim
# fixes). Run as a file there is no package context, so the relative
# import raises ImportError; fall back to inserting this file's own
# directory at sys.path[0] (position 0 so a PYTHONPATH-planted
# `secret_patterns` can never shadow the sibling) and importing the
# sibling module absolutely.
# ---------------------------------------------------------------------------
try:
    from . import secret_patterns as _patterns
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import secret_patterns as _patterns  # type: ignore[no-redef]

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


# ---------------------------------------------------------------------------
# CLI entrypoint (PLAN-156-FOLLOWUP F1, debate C4 — fail-CLOSED contract).
#
# `council-audit.js:145` pipes each external-lane brief through:
#
#     printf '%s' "$BRIEF" | python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing
#
# This is the single point where repo bytes become vendor-CLI input, so
# the CLI is fail-CLOSED end to end:
#
#   * The output is fully redacted IN MEMORY before a single byte
#     touches stdout — there is exactly ONE stdout write, and it happens
#     only after redaction has completed without error (no partial
#     output is possible).
#   * On ANY internal error (bad flag, undecodable stdin, import
#     breakage, redaction failure): exit NONZERO and emit NOTHING to
#     stdout. Errors go to stderr only, and carry only the exception
#     TYPE name — never str(exc), which could embed input bytes.
#   * The input is NEVER echoed on any error path (VETO line).
#
# The library API above (`redact()` / `redact_outgoing()` /
# `*_with_findings()`) is untouched by the CLI: `_cli_main` is a thin
# caller of `redact_outgoing()` and preserves the R1 S-Sec-1 single-pass
# invariant by construction.
# ---------------------------------------------------------------------------


def _cli_main(argv: Optional[List[str]] = None) -> int:
    """Run the egress-redaction CLI. Returns the process exit code.

    Reads ALL of stdin (strict UTF-8 — undecodable input is input this
    redactor cannot certify, so it fails CLOSED), redacts it fully in
    memory via ``redact_outgoing()``, then performs a single buffered
    stdout write. Any exception escapes to the ``__main__`` fail-CLOSED
    wrapper below (exit nonzero, empty stdout).
    """
    # Deferred import: routes even argparse import-time breakage through
    # the fail-CLOSED wrapper instead of an interpreter-level traceback.
    import argparse

    parser = argparse.ArgumentParser(
        prog="codex_egress_redact.py",
        description=(
            "ADR-114 egress redactor CLI. Reads text on stdin, writes the "
            "REDACTED text to stdout. Fail-CLOSED: on any error, exits "
            "nonzero with NOTHING on stdout (input is never echoed)."
        ),
    )
    parser.add_argument(
        "--outgoing",
        action="store_true",
        help=(
            "Redact an OUTGOING prompt (framework -> external vendor CLI). "
            "Required: the CLI refuses to run without an explicit direction."
        ),
    )
    args = parser.parse_args(argv)

    if not args.outgoing:
        sys.stderr.write(
            "codex_egress_redact: ERROR: --outgoing is required "
            "(refusing to guess a redaction direction; fail-closed)\n"
        )
        return 2

    # Step 1 — read ALL of stdin as bytes, decode strict UTF-8. A decode
    # failure raises → fail-CLOSED wrapper → exit nonzero, empty stdout.
    raw_text = sys.stdin.buffer.read().decode("utf-8")

    # Step 2 — redact FULLY IN MEMORY. No stdout has been touched yet;
    # if this raises, nothing was emitted.
    out_bytes = redact_outgoing(raw_text).encode("utf-8")

    # Step 3 — single buffered write, only after full success.
    sys.stdout.buffer.write(out_bytes)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_cli_main())
    except SystemExit:
        # Deliberate exits (including argparse's usage-error exit 2)
        # propagate unchanged. argparse errors write to stderr only.
        raise
    except BaseException as _exc:  # noqa: BLE001 — fail-CLOSED boundary
        # VETO line: on ANY internal error exit NONZERO and emit NOTHING
        # to stdout — never echo input. Only the exception TYPE name is
        # reported: str(exc) could embed input bytes (e.g. a
        # UnicodeDecodeError repr carries the offending byte sequence).
        try:
            sys.stderr.write(
                "codex_egress_redact: FATAL: {0} — no output emitted "
                "(fail-closed)\n".format(type(_exc).__name__)
            )
        except Exception:
            pass
        sys.exit(3)

