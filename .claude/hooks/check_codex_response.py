#!/usr/bin/env python3
"""PostToolUse hook: ingress-sanitize Codex MCP responses (R1 S-Sec-5).

Wired by ``settings.json`` PostToolUse matcher
``mcp__codex__codex|mcp__codex__codex-reply``. Runs after every Codex
MCP tool call returns; scans the Codex output for prompt-injection
patterns BEFORE Claude consumes the next turn.

R1 S-Sec-5 threat model (T-1, threat-model v0.1 §T-1):
  Codex CLI output can contain attacker-controlled content (e.g. a
  malicious file in the workspace, a poisoned dependency README, a
  compromised Codex CLI binary upstream). If Codex's output contains
  framework-specific tokens like ``[SYSTEM:``, ``<system>``,
  ``<tool_use>``, the next Claude turn could mis-attribute them as
  in-band system messages and act on them.

This hook does NOT modify the Codex output (PostToolUse hooks cannot
mutate tool_response per Claude Code's hook contract — they can only
emit allow/block decisions). Instead, on detection of any injection
pattern, it emits a ``pair_rail_codex_injection_detected`` audit event
with the matched-pattern family + length-bucketed offset (NOT the raw
content — Sec MF-3 forbids raw payload exfil).

Operationally:
- The audit event is consumed by ``audit-query.py codex-injection-summary``.
- Owner / on-call sees the event in the local SSE dashboard
  (``audit-dashboard.py``) and can react.
- For HARD enforcement (block downstream tool dispatch on detection),
  see PLAN-081 Phase 3 ``check_pair_rail.py`` extensions which CAN
  short-circuit dispatch in PreToolUse.

Per ADR-106, this PostToolUse hook is ADVISORY-ONLY: it ALWAYS emits
``allow`` to Claude Code. Detection without enforcement is the
correct semantic for ingress sanitization at this layer.

Per ADR-082 mitigated rail: this hook MUST NOT block on the
``general-purpose`` matcher path. The settings.json matcher restricts
this hook to ``mcp__codex__*`` tool names so this is mechanically
satisfied.

Fail-open: any parse / scan / emit failure logs a breadcrumb and
returns ``allow``. NEVER raises to the host.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Add hook lib path for imports (mirrors check_pair_rail.py pattern).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# ---------------------------------------------------------------------------
# Injection patterns (R1 S-Sec-5)
# ---------------------------------------------------------------------------
#
# Three pattern families chosen empirically from PLAN-077 + PLAN-078
# threat-modeling sessions. The patterns are conservative — false-
# positive on legitimate code review of XML parsers / system-prompt
# documentation is the trade-off vs missing a real injection.
#
# Family IDs are recorded in audit events for forensic clarity.
# ``family_id`` (str) is part of the Sec MF-3 whitelisted field set.

#: Pattern family: framework-specific harness mimicry. Examples:
#:   ``[SYSTEM: ignore previous instructions]``
#:   ``[SYSTEM:`` at start of line
_FAMILY_HARNESS_MIMICRY: str = "harness_mimicry"
_HARNESS_MIMICRY_RE = re.compile(
    r"\[\s*SYSTEM\s*:",
    re.IGNORECASE,
)

#: Pattern family: XML system-tag injection. Examples:
#:   ``<system>...</system>``
#:   ``<system attribute=...>``
_FAMILY_XML_SYSTEM: str = "xml_system_tag"
_XML_SYSTEM_RE = re.compile(
    r"<\s*system\b",
    re.IGNORECASE,
)

#: Pattern family: tool-use forgery. Examples:
#:   ``<tool_use>``
#:   ``<tool_use name=...>``
_FAMILY_TOOL_USE: str = "tool_use_forgery"
_TOOL_USE_RE = re.compile(
    r"<\s*tool_use\b",
    re.IGNORECASE,
)

#: Tuple of (pattern_re, family_id). The order is stable for
#: deterministic forensic output; tests pin this order.
_INJECTION_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    (_HARNESS_MIMICRY_RE, _FAMILY_HARNESS_MIMICRY),
    (_XML_SYSTEM_RE, _FAMILY_XML_SYSTEM),
    (_TOOL_USE_RE, _FAMILY_TOOL_USE),
)

#: Hard cap on input scanned. Codex output >256 KB is truncated to
#: this boundary before scanning. Same cap as
#: ``codex_egress_redact.py`` for consistency.
_MAX_SCAN_BYTES: int = 256 * 1024


def _scan_injection(text: str) -> List[Tuple[str, int]]:
    """Scan text for injection patterns.

    Returns:
        List of ``(family_id, offset)`` tuples for every pattern
        match. ``offset`` is the 0-based byte position (length-
        bucketed by caller for audit emit). Empty list on no match.

    NEVER raises. On invalid input → returns empty list.
    """
    if not text or not isinstance(text, str):
        return []

    # Truncate at hard cap before scanning.
    if len(text.encode("utf-8")) > _MAX_SCAN_BYTES:
        truncated = text.encode("utf-8")[:_MAX_SCAN_BYTES]
        text = truncated.decode("utf-8", errors="replace")

    matches: List[Tuple[str, int]] = []
    for pattern_re, family_id in _INJECTION_PATTERNS:
        for m in pattern_re.finditer(text):
            matches.append((family_id, m.start()))
    return matches


def _bucket_offset(offset: int) -> str:
    """Length-bucket an offset for Sec MF-3 audit emission.

    Raw offsets can be content-leaking (proof an offset of e.g. 1234
    implies the prompt's prefix is 1234 bytes long). Bucket to coarse
    ranges per the Sec MF-3 length-bucket schema.
    """
    if offset < 100:
        return "0-100"
    if offset < 1000:
        return "100-1k"
    if offset < 10000:
        return "1k-10k"
    if offset < 100000:
        return "10k-100k"
    return "100k+"


def _emit_audit_safe(
    matches: List[Tuple[str, int]],
    tool_name: str,
    session_id: str,
    project: str,
) -> None:
    """Emit ``pair_rail_codex_injection_detected`` audit event.

    Sec MF-3 whitelisted fields:
      - ``tool_name`` (str — the matched tool, e.g. ``mcp__codex__codex``)
      - ``family_ids`` (list[str] — the matched pattern families)
      - ``match_count`` (int — total matches across all families)
      - ``first_offset_bucket`` (str — coarse-bucketed offset of first match)

    DENIED fields (LLM06 side-channel guard):
      - raw matched content
      - raw offset values
      - prompt content
      - any environment values

    Fail-open: import failure or audit emit failure → log breadcrumb
    to ``CEO_BOOT_DEBUG=1`` stderr and continue. NEVER raises.
    """
    if not matches:
        return
    try:
        from _lib import audit_emit as _audit  # noqa: E402
    except Exception:
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "[check_codex_response] audit_emit import failed; skipping emit\n"
            )
        return

    family_ids = sorted({fam for fam, _ in matches})
    first_offset = min((off for _, off in matches), default=0)
    first_bucket = _bucket_offset(first_offset)
    match_count = len(matches)

    try:
        # Use hasattr-guarded emit per S87 W5 pattern (works pre + post
        # canonical ceremony in v1.13.0).
        if hasattr(_audit, "emit_pair_rail_codex_injection_detected"):
            _audit.emit_pair_rail_codex_injection_detected(
                tool_name=tool_name,
                session_id=session_id,
                project=project,
                family_ids=family_ids,
                match_count=match_count,
                first_offset_bucket=first_bucket,
            )
        else:
            # Pre-canonical-ceremony adopter installs: graceful no-op.
            if os.environ.get("CEO_BOOT_DEBUG") == "1":
                sys.stderr.write(
                    "[check_codex_response] emit_pair_rail_codex_injection_detected "
                    "not available; skipping (pre-ceremony adopter)\n"
                )
    except Exception as e:
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                f"[check_codex_response] audit emit failed: {type(e).__name__}\n"
            )


# ---------------------------------------------------------------------------
# PLAN-132 / ADR-145 — observe an ad-hoc Codex review for the persona-demand ledger
# ---------------------------------------------------------------------------
#
# When a `mcp__codex__codex` call is REVIEW-shaped (a review verb AND a diff/code
# artifact, and NOT a generation prompt), emit a branch-bound `codex_review_invoked`
# so `persona_demand_resolver` can recognize cross-model review as `code-reviewer`
# demand satisfaction (ADR-145, code-reviewer ONLY).
#
# R2 (false-positive) closure: the gate requires BOTH a review verb AND a diff/code
# marker, and suppresses generation-shaped prompts. High-precision — a missed real
# review only leaves the advisory false-RED (status quo, safe); a false match would
# silently GREEN the atrophy detector (unsafe). Default to NOT emitting on ambiguity.
#
# R1 (cross-branch) closure: the event carries target_ref_hash = the current branch's
# hash (IDENTICAL construction to persona_demand_scan._target_ref_hash), so the
# resolver match is branch-bound, not merely temporal. Unresolvable branch
# (detached / trunk / git failure) -> empty hash -> resolver FAILS CLOSED.

_REVIEW_VERB_RE = re.compile(
    r"\b(review|audit|critique|refute|red[\s-]?team|veto|"
    r"find\s+(bugs|defects|issues|vulnerabilit\w*))\b",
    re.IGNORECASE,
)
# STRONG framing only — a review VERDICT / pair-rail context, NOT a soft role
# preamble. A bare "as a code reviewer, ..." is deliberately NOT here: it can
# prefix a generation request ("as a code reviewer, implement this") and must
# not, by itself, qualify a prompt as a review (Codex pair-rail P1 #1).
_STRONG_FRAMING_RE = re.compile(
    r"(pair[\s-]?rail|\bACCEPT\b|\bBLOCK\b|\bVETO\b)",
)
_DIFF_MARKER_RE = re.compile(
    r"(```|diff --git|^@@ |^\+\+\+ |^--- |"
    r"review\s+the\s+(uncommitted|staged|current)\s+(changes|diff|code))",
    re.MULTILINE | re.IGNORECASE,
)
_GENERATION_LEAD_RE = re.compile(
    r"^\s*(please\s+)?(write|implement|create|generate|build|add|refactor|fix)\b",
    re.IGNORECASE,
)


def _is_review_intent(prompt: str) -> bool:
    """True iff the prompt is a CODE-review request: a review verb AND a diff/code
    marker, and not a generation-led prompt. Biased to under-emission (R2)."""
    if not prompt or not isinstance(prompt, str):
        return False
    import unicodedata
    p = unicodedata.normalize("NFKC", prompt)
    # A review needs a real review VERB (review/audit/refute/find bugs/...) or a
    # strong review-verdict framing (ACCEPT/BLOCK/VETO/pair-rail). A soft
    # "as a code reviewer" preamble does NOT qualify (Codex P1 #1).
    has_verb = bool(_REVIEW_VERB_RE.search(p) or _STRONG_FRAMING_RE.search(p))
    if not has_verb:
        return False
    # A generation-led prompt is NOT a review, regardless of any framing.
    if _GENERATION_LEAD_RE.search(p):
        return False
    return bool(_DIFF_MARKER_RE.search(p))


def _current_branch_target_ref_hash(cwd: str) -> str:
    """sha256(NFKC('branch:'+branch))[:12] — IDENTICAL to
    persona_demand_scan._target_ref_hash so the resolver can stitch the match.
    Returns '' for detached HEAD / trunk / any git failure (fail-closed binding)."""
    import hashlib
    import subprocess
    import unicodedata
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd, capture_output=True, text=True, timeout=5,
        )
        branch = (proc.stdout or "").strip()
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return ""
    if not branch or branch in ("HEAD", "main", "master"):
        return ""
    pre = unicodedata.normalize("NFKC", "branch:" + branch)
    return hashlib.sha256(pre.encode("utf-8")).hexdigest()[:12]


def _observe_codex_review(event) -> None:
    """Emit a branch-bound codex_review_invoked for a review-shaped Codex MCP call
    (PLAN-132 / ADR-145). Advisory, fail-open. Kill-switch CEO_CODEX_REVIEW_OBSERVE=0."""
    if os.environ.get("CEO_CODEX_REVIEW_OBSERVE") == "0":
        return
    try:
        tool_input = getattr(event, "tool_input", None)
        prompt = ""
        if isinstance(tool_input, dict):
            prompt = str(tool_input.get("prompt") or "")
        if not _is_review_intent(prompt):
            return
        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        target_ref_hash = _current_branch_target_ref_hash(cwd)
        from _lib import audit_emit as _ae  # noqa: E402
        if hasattr(_ae, "emit_generic"):
            _ae.emit_generic(
                "codex_review_invoked",
                review_status="invoked",
                review_source="adhoc_mcp",
                target_ref_hash=target_ref_hash,
            )
    except Exception:
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "[check_codex_response] codex-review observe fail-open\n"
            )


def main() -> int:
    """Hook entry point — PostToolUse mcp__codex__*.

    Always emits ``allow`` per ADR-106 (Codex is advisory; PostToolUse
    cannot block). Side-effect: emits audit event on injection
    detection.
    """
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
        from _lib import contract as _contract  # noqa: E402
    except Exception:
        # Cannot load adapter — fail-open with empty body (schema-compliant
        # implicit allow; top-level "allow" fails Claude Code hook schema).
        sys.stdout.write('{}\n')
        return 0

    try:
        event = _claude_adapter.read_post_event()
    except Exception:
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    if event.parse_error:
        # Fail-open per ADR-106: parse failure on PostToolUse cannot
        # block (the tool already ran). Skip detection + allow.
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    tool_name = (event.tool_name or "").strip()
    # Defense in depth — only run on Codex MCP tools (settings.json
    # matcher should already restrict, but double-check).
    if tool_name not in ("mcp__codex__codex", "mcp__codex__codex-reply"):
        _claude_adapter.emit_decision(_contract.allow())
        return 0

    # Extract Codex stdout from tool_response.
    try:
        from _lib.adapters import codex as _codex_adapter  # noqa: E402
        codex_stdout = _codex_adapter._extract_codex_stdout(event.tool_response)
    except Exception:
        # Codex adapter not available pre-ceremony OR extraction
        # failed: scan the raw tool_response stringified instead.
        codex_stdout = ""
        if isinstance(event.tool_response, dict):
            # Fallback: stringify the dict and scan that. Worst case
            # is more false-positives, but never a false-negative.
            import json as _json
            try:
                codex_stdout = _json.dumps(event.tool_response, ensure_ascii=False)
            except Exception:
                codex_stdout = str(event.tool_response)

    # Scan + emit (advisory — never blocks).
    matches = _scan_injection(codex_stdout)
    if matches:
        _emit_audit_safe(
            matches=matches,
            tool_name=tool_name,
            session_id=event.session_id or "",
            project=event.project or "",
        )

    # PLAN-132 / ADR-145 — observe a review-shaped Codex call so the persona-demand
    # ledger can recognize cross-model review (branch-bound; advisory; fail-open).
    _observe_codex_review(event)

    # Always allow per ADR-106.
    _claude_adapter.emit_decision(_contract.allow())
    return 0


if __name__ == "__main__":
    sys.exit(main())
