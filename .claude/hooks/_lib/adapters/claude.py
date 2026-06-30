"""Claude Code hook adapter.

Translates Claude Code's PreToolUse / PostToolUse JSON payload
(stdin) → NormalizedEvent, and Decision → stdout JSON line.

Behavior identical to the current hooks' direct use of `_lib.payload`.
This adapter wraps that logic so the hooks can migrate to the neutral
contract without changing observable output.
"""

from __future__ import annotations

import json
import sys
from typing import IO, Any, Dict

from .. import contract as _contract
from .. import payload as _payload


def read_event(
    stream: "IO[str] | None" = None,
    phase: str = "PreToolUse",
) -> _contract.NormalizedEvent:
    """Parse Claude Code hook payload from stdin into a NormalizedEvent.

    Args:
        stream: stdin stream (defaults to sys.stdin)
        phase: `"PreToolUse"` (default) or `"PostToolUse"`. Hooks know
            their own phase via settings.json matcher routing; this
            parameter lets a hook declare its phase so consumers of the
            NormalizedEvent (e.g. audit_log writers) record the correct
            phase tag. ADR-014 + R-SB1 (PLAN-006 debate round 1).

    Fail-open: on any parse error, returns an event with `parse_error`
    set and empty fields. Callers decide what to do (typically: log
    breadcrumb + allow).
    """
    if phase not in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
        # Fail-open: genuinely-unknown phase → default to PreToolUse. This
        # keeps hook bodies free of defensive checks; a mis-configured
        # settings.json entry still produces a valid event.
        #
        # PLAN-125 WS-1 — `PostToolUseFailure` is now an ACCEPTED distinct
        # phase (the tool ran and errored). Before this change it was
        # silently collapsed to `PreToolUse`, which erased the fact that a
        # tool failed. We preserve fail-open for truly-bogus phase strings
        # (e.g. a typo) but no longer rewrite the failure phase. NOTE: other
        # lifecycle phases like `SessionEnd` (used by SessionEnd.py purely to
        # tag the event) intentionally still fold to `PreToolUse` here — they
        # do not consume the phase tag, so the fold is behavior-neutral.
        phase = "PreToolUse"

    # Resolve stream at CALL time (not at definition time) so that tests
    # which swap `sys.stdin = io.StringIO(...)` work correctly. Matches
    # `_lib.payload.parse_stdin` behavior.
    if stream is None:
        stream = sys.stdin

    # Use the existing stdin parser to stay behavior-identical.
    # It tolerates malformed JSON and surfaces errors via raw_error.
    try:
        p = _payload.parse_stdin(stream=stream)
    except Exception as e:  # pragma: no cover
        return _contract.NormalizedEvent(parse_error=f"stdin read failed: {e}", phase=phase)

    import os as _os

    if p.raw_error:
        return _contract.NormalizedEvent(
            parse_error=p.raw_error,
            session_id=p.session_id or "",
            tool_name=p.tool_name or "",
            phase=phase,
            raw_payload={},
        )

    tool_input = p.tool_input if isinstance(p.tool_input, dict) else {}
    tool_response = p.tool_response if isinstance(p.tool_response, dict) else {}

    return _contract.NormalizedEvent(
        session_id=p.session_id or "",
        project=_os.environ.get("CLAUDE_PROJECT_DIR") or "",
        phase=phase,
        tool_name=p.tool_name or "",
        tool_input=tool_input,
        tool_response=tool_response if isinstance(tool_response, dict) else {},
        description=p.description or "",
        prompt=p.prompt or "",
        subagent_type=str(tool_input.get("subagent_type") or p.subagent_type or ""),
        file_path=str(tool_input.get("file_path") or ""),
        old_string=str(tool_input.get("old_string") or ""),
        new_string=str(tool_input.get("new_string") or ""),
        replace_all=bool(tool_input.get("replace_all") or False),
        command=str(tool_input.get("command") or ""),
        # PLAN-125 WS-1 — surface the 2 named lifecycle scalars. We do NOT
        # re-open the bulk raw_payload (that would reintroduce the bulk-data
        # side-channel the deny-by-default discipline forbids); raw_payload
        # stays {} and only these named scalars cross the contract boundary.
        tool_use_id=p.tool_use_id or "",
        duration_ms=(
            int(p.duration_ms) if isinstance(p.duration_ms, int) else None
        ),
        raw_payload={},
    )


def read_post_event(stream: "IO[str] | None" = None) -> _contract.NormalizedEvent:
    """Convenience wrapper for PostToolUse hooks.

    Equivalent to `read_event(stream, phase="PostToolUse")`. Added per
    PLAN-006 Phase 1 pre-work (ADR-014) so PostToolUse hooks do not
    need to remember the phase string.
    """
    return read_event(stream=stream, phase="PostToolUse")


def read_post_failure_event(stream: "IO[str] | None" = None) -> _contract.NormalizedEvent:
    """Convenience wrapper for PostToolUseFailure hooks (PLAN-125 WS-1).

    Equivalent to `read_event(stream, phase="PostToolUseFailure")`. The
    distinct phase lets a lifecycle consumer set `success=false` without a
    marker scan (the event type IS the success signal). Mirrors
    `read_post_event` (Post) so the failure-matcher hook need not remember
    the phase string.
    """
    return read_event(stream=stream, phase="PostToolUseFailure")


def write_decision(decision: _contract.Decision) -> str:
    """Serialize a Decision to Claude Code's expected stdout JSON line.

    Matches the existing hooks' output contract exactly:
    - `{"decision":"allow"}` when allow=True and no optional fields
    - `{"decision":"block","reason":"..."}` when blocking
    - Optional `systemMessage` / `message` fields preserved
    - Single line, no trailing newline (caller adds via print())
    """
    # Claude Code hook schema: top-level `decision` enum is "approve"|"block"
    # (NOT "allow"). On allow, emit empty {} (or {"systemMessage": ...}).
    out: Dict[str, Any] = {}
    if not decision.allow:
        out["decision"] = "block"
        if decision.reason:
            out["reason"] = decision.reason
    if decision.system_message:
        out["systemMessage"] = decision.system_message
    if decision.message:
        out["message"] = decision.message
    # Allow adapter-specific extras (but standard Claude shape never uses these)
    for k, v in decision.extra.items():
        # Drop legacy {"decision":"allow"} leaked via extras (schema-invalid).
        if k == "decision" and v == "allow":
            continue
        if k not in out:
            out[k] = v
    return json.dumps(out, ensure_ascii=False)


def emit_decision(decision: _contract.Decision, stream: "IO[str] | None" = None) -> None:
    """Convenience: write the decision as a single line + newline.

    Resolves stream at call time so tests that swap `sys.stdout` work.
    """
    if stream is None:
        stream = sys.stdout
    stream.write(write_decision(decision) + "\n")
