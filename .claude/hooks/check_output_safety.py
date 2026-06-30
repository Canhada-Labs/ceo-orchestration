#!/usr/bin/env python3
"""PostToolUse Agent hook: scan agent output for PII / credential leaks.

Sprint 11 Phase 9 (ADR-036). Advisory counterpart to
``check_read_injection.py``:

- ``check_read_injection.py`` = scan **inputs** (files being Read) for
  prompt-injection patterns.
- ``check_output_safety.py`` = scan **outputs** (agent responses) for PII
  / credential / secret leaks.

Both are advisory, both fail-open, both emit v2 audit events.

## Wire-up (Phase 13 closeout, NOT in Phase 9)

    {
      "matcher": "Agent",
      "hooks": [
        {
          "type": "command",
          "command": "bash \\"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\\" check_output_safety.py",
          "timeout": 10,
          "statusMessage": "Scanning output for secrets..."
        }
      ]
    }

## Modes

Environment variable ``CEO_OUTPUT_SAFETY_MODE`` selects:

- ``flag`` (default, Sprint 11) — emit audit event, output PRESERVED.
- ``redact`` — replace each match with ``[REDACTED:FAMILY]`` in the
  audit snippet_preview; full output is NOT mutated (this hook cannot
  mutate tool_response, only emit observations).

Sprint 12 flip criterion: ≤1 false-positive per 1000 outputs over 30d.

## Kill switch

``CEO_SOTA_DISABLE=1`` → hook short-circuits to
``{"decision":"allow"}`` with no event emitted. Full no-op per
consensus S4 / ADR-036.

## Decision contract

ALWAYS ``decision: allow``. This hook can never block. Advisory Sprint
11 per ADR-036.

## Fail-open contract

Per CLAUDE.md §Critical Rules: hooks NEVER block the user session on
infrastructure bugs. Parse errors, missing files, subprocess failures,
unexpected exceptions → breadcrumb + allow.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Make local _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _emit_allow() -> str:
    """Return the canonical allow JSON (single-line, no trailing newline).

    Emit empty {} — top-level {"decision":"allow"} fails the Claude Code
    hook schema (decision enum is "approve"|"block").
    """
    return json.dumps({}, ensure_ascii=False)


def _extract_output_text(tool_response: Dict[str, Any]) -> str:
    """Pull textual output from a PostToolUse Agent tool_response.

    Shape varies between adapter versions and tool types. We concatenate
    commonly-populated text fields. Returns empty string if nothing
    meaningful is present (hook allows silently in that case).
    """
    if not isinstance(tool_response, dict):
        return ""

    parts = []
    # Common top-level text fields
    for key in ("message", "text_output", "text", "response", "output", "content"):
        val = tool_response.get(key)
        if isinstance(val, str) and val:
            parts.append(val)

    # content may be a list of blocks (Anthropic-style)
    content = tool_response.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                t = block.get("text") or block.get("content")
                if isinstance(t, str):
                    parts.append(t)
            elif isinstance(block, str):
                parts.append(block)

    if parts:
        return "\n".join(parts)

    # As a final fallback, stringify the whole response so the scanner
    # at least has something to analyze. Bounded by pii_patterns _MAX_BYTES.
    try:
        return json.dumps(tool_response, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def _try_emit_audit(
    *,
    source: str,
    family_counts: Dict[str, int],
    match_count: int,
    bytes_scanned: int,
    redaction_applied: bool,
    snippet: str,
    truncated: bool,
    triggered_by_tool: str,
    session_id: str,
) -> None:
    """Best-effort audit emit. Never raises (fail-open observability)."""
    try:
        from _lib.audit_emit import emit_output_safety_flag
        emit_output_safety_flag(
            source=source,
            family_counts=family_counts,
            match_count=match_count,
            bytes_scanned=bytes_scanned,
            redaction_applied=redaction_applied,
            triggered_by_tool=triggered_by_tool,
            snippet_preview=snippet,
            truncated=truncated,
            session_id=session_id,
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return


def main() -> int:
    """PostToolUse Agent hook entrypoint.

    Contract:
    - Always exit 0
    - Always print ``{"decision":"allow"}``
    - Emit ``output_safety_flag`` audit event iff scanner found matches
    - ``CEO_SOTA_DISABLE=1`` → no-op (allow + zero audit side effects)
    - Fail-open on any infra error
    """
    # Kill switch (consensus S4)
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Adapter I/O (ADR-008)
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
        event = _claude_adapter.read_post_event()
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    if event.parse_error:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    tool_name = event.tool_name or ""
    session_id = event.session_id or ""

    # Extract output text
    text = _extract_output_text(event.tool_response or {})
    if not text:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Mode gate
    mode = os.environ.get("CEO_OUTPUT_SAFETY_MODE", "flag").strip().lower()
    if mode not in ("flag", "redact"):
        mode = "flag"

    # Scanner (lazy import — if packaging bug, fail-open)
    try:
        from _lib.pii_patterns import scan as _scan
    except Exception:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    try:
        result = _scan(text, mode=mode)
    except Exception:
        # Any scanner exception → fail-open, no event
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    if not result.matched:
        sys.stdout.write(_emit_allow() + "\n")
        return 0

    # Build audit snippet — show the first match region + family context
    snippet_source = (
        result.matches[0].snippet
        if result.matches
        else (result.redacted_text if mode == "redact" else text[:200])
    )

    source_label = f"agent:{tool_name}" if tool_name else "agent"

    _try_emit_audit(
        source=source_label,
        family_counts=result.family_counts,
        match_count=result.match_count,
        bytes_scanned=result.bytes_scanned,
        redaction_applied=(mode == "redact"),
        snippet=snippet_source,
        truncated=result.truncated,
        triggered_by_tool=tool_name or "Agent",
        session_id=session_id,
    )

    sys.stdout.write(_emit_allow() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
