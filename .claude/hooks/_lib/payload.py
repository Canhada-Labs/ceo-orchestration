"""Parse Claude Code hook stdin JSON payloads.

Both PreToolUse (for check_agent_spawn.py) and PostToolUse (for audit_log.py)
deliver a JSON object on stdin with the following shape (Claude Code contract):

    {
      "session_id": "...",
      "tool_name": "Agent",
      "tool_input": {
        "description": "...",
        "prompt": "...",
        "subagent_type": "..."       # optional
      },
      "tool_response": {...}          # PostToolUse only
    }

This module parses the JSON safely and returns a typed dataclass. Failures
are explicit (never silent): a malformed payload returns a payload with
`raw_error` set so the caller can decide whether to fail-open or block.

## Safety properties

1. Reads stdin exactly once (subsequent calls return empty; matches the
   bash `INPUT=$(cat)` pattern).
2. Tolerates missing fields (all fields default to empty string / empty dict).
3. Never raises on bad JSON — sets `raw_error` instead.
4. No network, no file I/O, no subprocess.

## Testing

See `tests/test_payload.py` for the full coverage matrix.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class HookPayload:
    """Typed view of a Claude Code hook stdin payload."""

    # Always-present fields (may be empty strings if missing)
    session_id: str = ""
    tool_name: str = ""
    description: str = ""
    prompt: str = ""
    subagent_type: str = ""

    # Structured sub-objects (PostToolUse only)
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_response: Any = None

    # PLAN-125 WS-1 — per-tool-call lifecycle scalars. Top-level payload
    # keys (siblings of tool_name / tool_response per the Claude Code hook
    # docs). `tool_use_id` is the per-call pairing key; `duration_ms` is the
    # native tool wall-clock on PostToolUse / PostToolUseFailure. Kept numeric
    # (int-or-None) — NOT coerced to str — so the bucketing mapper sees a number.
    tool_use_id: str = ""
    duration_ms: Optional[int] = None

    # Error state — set if stdin could not be parsed
    raw_error: Optional[str] = None

    # Raw stdin (for debugging / breadcrumbs)
    raw: str = ""


def parse_stdin(stream: Optional[Any] = None) -> HookPayload:
    """Parse stdin JSON into a HookPayload. Never raises.

    Args:
        stream: A file-like object with a .read() method. If None (default),
            uses `sys.stdin`. Tests pass a StringIO.

    Returns:
        HookPayload. On parse failure, `raw_error` is set to the exception
        message and all other fields remain at defaults.
    """
    if stream is None:
        stream = sys.stdin

    try:
        raw = stream.read()
    except Exception as e:  # pragma: no cover — stdin.read() failure is exotic
        return HookPayload(raw_error=f"stdin read failed: {e}")

    return parse_text(raw)


def parse_text(text: str) -> HookPayload:
    """Parse a JSON text into a HookPayload. Used by tests and parse_stdin.

    Empty input is treated as a valid empty payload (not an error) — matches
    the bash behavior where `cat` with no input yields ""  and `jq // ""`
    defaults to empty.
    """
    payload = HookPayload(raw=text)

    if not text or not text.strip():
        return payload

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        payload.raw_error = f"JSON parse error: {e.msg} at line {e.lineno} col {e.colno}"
        return payload

    if not isinstance(data, dict):
        payload.raw_error = f"payload must be a JSON object, got {type(data).__name__}"
        return payload

    # Top-level fields
    payload.session_id = _str(data.get("session_id"))
    payload.tool_name = _str(data.get("tool_name"))

    # PLAN-125 WS-1 — top-level lifecycle scalars. `tool_use_id` is a string
    # pairing key; `duration_ms` stays numeric (int-or-None) so the duration
    # bucketing mapper receives a number, never a stringified value.
    payload.tool_use_id = _str(data.get("tool_use_id"))
    payload.duration_ms = _int_or_none(data.get("duration_ms"))

    # tool_input sub-object
    tool_input = data.get("tool_input") or {}
    if isinstance(tool_input, dict):
        payload.tool_input = tool_input
        payload.description = _str(tool_input.get("description"))
        payload.prompt = _str(tool_input.get("prompt"))
        payload.subagent_type = _str(tool_input.get("subagent_type"))
    # If tool_input is not a dict, the fields above stay empty — don't error,
    # fail-open is the protocol.

    # tool_response — may be dict, str, or absent (PostToolUse variants differ)
    payload.tool_response = data.get("tool_response")

    return payload


def _str(value: Any) -> str:
    """Coerce a JSON value to a string, tolerating None/missing."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    # For numeric or bool, stringify — this is a display/log artifact
    return str(value)


def _int_or_none(value: Any) -> Optional[int]:
    """Coerce a JSON value to an int, or None when absent / non-numeric.

    PLAN-125 WS-1 — used for `duration_ms`. A bool is NOT a duration (bool is
    a subclass of int in Python) so it is rejected. Strings that look numeric
    are tolerated (defensive — the docs ship an int, but adopters' harnesses
    vary); anything else returns None.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def response_kind(tool_response: Any) -> str:
    """Classify a PostToolUse tool_response for the audit schema.

    Returns one of: "object", "string", "absent", or a specific subtype.

    Mirrors the bash audit-log.sh jq expression:
        if .tool_response is object → .tool_response.type // "object"
        elif string → "string"
        else → "absent"
    """
    if tool_response is None:
        return "absent"
    if isinstance(tool_response, dict):
        # If the response has its own 'type' field, use it; else "object"
        subtype = tool_response.get("type")
        if isinstance(subtype, str) and subtype:
            return subtype
        return "object"
    if isinstance(tool_response, str):
        return "string"
    # Arrays, numbers, bools — unusual but not an error
    return type(tool_response).__name__
