"""Token extraction helper for audit-log `tokens_in` / `tokens_out` fields.

PLAN-006 Phase 5a (ADR-016). Parses spawn response / PostToolUse
`tool_response` to extract input/output token counts. Handles multiple
shapes across adapters:

- **Claude Code**: `tool_response.usage.{input_tokens, output_tokens}`
  (per Anthropic SDK conventions)
- **Claude Code alt**: `tool_response.totalTokens` (legacy field)
- **Gemini CLI** (stub): probes `promptTokenCount` / `candidatesTokenCount`
  inside `tool_response.usageMetadata` or `tool_response.usage`
- **Unknown / absent**: returns `(None, None)` — callers emit null.

## Contract

Per SPEC/v1/audit-log.schema.md (as amended by ADR-016):
- `tokens_in` / `tokens_out` / `tokens_total` are **optional, nullable,
  always-present when emitter supports it**.
- Absent from a record = "older emitter version" — consumers treat
  as null.
- Null = "emitter supports the field but couldn't extract a count"
  (e.g. malformed response).
- Integer = extracted count.

## Fail-open

Any exception during extraction → (None, None). Never raises.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _to_int_or_none(value: Any) -> Optional[int]:
    """Coerce a value to int if possible, else None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None  # bool is int subclass; reject accidentally-truthy
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value != value:  # NaN
            return None
        n = int(value)
        return n if n >= 0 else None
    if isinstance(value, str):
        try:
            n = int(value)
            return n if n >= 0 else None
        except (TypeError, ValueError):
            return None
    return None


def _extract_from_usage_block(usage: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """Probe common field names inside a usage/metadata block."""
    if not isinstance(usage, dict):
        return (None, None)
    # Claude / Anthropic SDK
    tin = _to_int_or_none(usage.get("input_tokens"))
    tout = _to_int_or_none(usage.get("output_tokens"))
    if tin is not None or tout is not None:
        return (tin, tout)
    # Gemini / VertexAI
    tin = _to_int_or_none(usage.get("promptTokenCount") or usage.get("prompt_token_count"))
    tout = _to_int_or_none(
        usage.get("candidatesTokenCount")
        or usage.get("candidates_token_count")
        or usage.get("completionTokenCount")
        or usage.get("completion_token_count")
    )
    if tin is not None or tout is not None:
        return (tin, tout)
    # OpenAI-ish
    tin = _to_int_or_none(usage.get("prompt_tokens"))
    tout = _to_int_or_none(usage.get("completion_tokens"))
    return (tin, tout)


def extract_tokens(tool_response: Any) -> Tuple[Optional[int], Optional[int]]:
    """Extract (input_tokens, output_tokens) from a tool_response dict.

    Returns a tuple of `(Optional[int], Optional[int])`. Either or both
    may be None when the shape is unknown.

    Safe on None, non-dict, empty dict.
    """
    if not isinstance(tool_response, dict) or not tool_response:
        return (None, None)

    try:
        # Primary: nested `usage` block
        if isinstance(tool_response.get("usage"), dict):
            tin, tout = _extract_from_usage_block(tool_response["usage"])
            if tin is not None or tout is not None:
                return (tin, tout)

        # Gemini: `usageMetadata` block
        if isinstance(tool_response.get("usageMetadata"), dict):
            tin, tout = _extract_from_usage_block(tool_response["usageMetadata"])
            if tin is not None or tout is not None:
                return (tin, tout)

        # Legacy Claude Code: totalTokens at top level (output only, can't split)
        total = _to_int_or_none(tool_response.get("totalTokens"))
        if total is not None:
            return (None, total)

        return (None, None)
    except Exception:  # pragma: no cover — absolute fail-open
        return (None, None)


def total_tokens(tool_response: Any) -> Optional[int]:
    """Convenience: extract tokens_total from tool_response.

    Prefers explicit sums; falls back to `in + out` if both present.
    """
    if not isinstance(tool_response, dict) or not tool_response:
        return None
    try:
        for key in ("totalTokens", "total_tokens", "total_token_count"):
            v = _to_int_or_none(tool_response.get(key))
            if v is not None:
                return v
        # Sum of in + out
        tin, tout = extract_tokens(tool_response)
        if tin is not None and tout is not None:
            return tin + tout
        if tout is not None:
            return tout
        return None
    except Exception:  # pragma: no cover
        return None
