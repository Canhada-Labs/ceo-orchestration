#!/usr/bin/env python3
"""check_mcp_response — PostToolUse hook scanning MCP tool results (PLAN-052 / ADR-083).

Reads PostToolUse hook input on stdin, identifies MCP tool calls
(``mcp__<server>__<tool>``), scans the response content for harness-
mimicry / directive-prose patterns via ``_lib/mcp_injection_scan``,
and emits an ``mcp_injection_finding`` audit event when a match fires.

Modes (Session 73 — STRICT promotion shipped):

- ADVISORY (default): always returns ``{"decision":"allow"}``; emits
  forensic record. Fail-open on every error.
- STRICT: returns ``{"decision":"block","reason":...}`` when finding
  severity is ``high`` (directive_prose or synthetic_tool_call).
  Medium / low severities still allow + emit. Opt-in via env var.

Mode resolution (highest precedence first):

1. ``CEO_MCP_SCANNER_DISABLE=1``   → kill-switch; always allow, no scan.
2. ``CEO_MCP_SCANNER_MODE=strict`` → STRICT mode for high-severity hits.
3. ``CEO_MCP_SCANNER_MODE=advisory`` (or unset) → ADVISORY default.

Per ADR-083 §3 + PLAN-052 closure ADR (2026-04-29): STRICT mode is
opt-in even after Day 2 baseline accept (98%/0%/100% across 100
fixtures + 1 FN closed via determiner-tolerance Session 73). Default
remains ADVISORY to preserve adopter blast-radius safety; adopters
flip after their own soak observation.

Kill-switch: ``CEO_MCP_SCANNER_DISABLE=1`` short-circuits to allow.

Performance budget (per ADR-083 §6): p95 ≤50ms PostToolUse latency.
Stdlib-only; no third-party deps.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure _lib import works when invoked via the standard hook shim.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import mcp_injection_scan as _scan
    from _lib import audit_emit as _audit
except Exception:  # pragma: no cover — fail-open on import errors
    _scan = None  # type: ignore
    _audit = None  # type: ignore


def _emit_allow() -> int:
    # Allow: emit empty JSON (top-level "allow" fails Claude Code hook schema).
    sys.stdout.write(json.dumps({}, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def _emit_block(reason: str) -> int:
    sys.stdout.write(
        json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)
    )
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0


def _kill_switch_active() -> bool:
    return os.environ.get("CEO_MCP_SCANNER_DISABLE", "") == "1"


def _resolve_mode() -> str:
    """Return ``"strict"`` or ``"advisory"`` (default).

    Resolution order: kill-switch (caller checks separately) > env var
    ``CEO_MCP_SCANNER_MODE`` > advisory default. Unknown values fall
    back to advisory (fail-safe — never escalate on garbage).
    """
    raw = (os.environ.get("CEO_MCP_SCANNER_MODE", "") or "").strip().lower()
    return "strict" if raw == "strict" else "advisory"


def _coerce_to_text(value) -> str:
    """Convert MCP tool response shape to plain text for scanning."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            return bytes(value).decode("utf-8", errors="replace")
        except Exception:
            return ""
    if isinstance(value, list):
        # MCP tool responses commonly use [{"type":"text","text":"..."}, ...]
        parts = []
        for item in value:
            if isinstance(item, dict):
                t = item.get("text") or item.get("content")
                if isinstance(t, str):
                    parts.append(t)
                elif t is not None:
                    parts.append(str(t))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    if isinstance(value, dict):
        # Single-content shape
        for key in ("text", "content", "result", "data"):
            v = value.get(key)
            if isinstance(v, str):
                return v
            if isinstance(v, list):
                return _coerce_to_text(v)
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return ""
    try:
        return str(value)
    except Exception:
        return ""


def _extract_mcp_response(payload: dict) -> str:
    """Pull the response body from a PostToolUse payload."""
    candidates = [
        payload.get("tool_response"),
        payload.get("toolResult"),
        payload.get("result"),
        payload.get("output"),
    ]
    for c in candidates:
        text = _coerce_to_text(c)
        if text:
            return text
    return ""


def main() -> int:
    if _kill_switch_active():
        return _emit_allow()
    if _scan is None or _audit is None:
        # Import failed; fail-open silently.
        return _emit_allow()

    # Read stdin payload — never block on malformed.
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        return _emit_allow()
    if not raw.strip():
        return _emit_allow()

    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return _emit_allow()

    tool_name = payload.get("tool_name") or payload.get("toolName") or ""
    if not _scan.is_mcp_tool_name(tool_name):
        return _emit_allow()

    parsed = _scan.parse_mcp_tool_name(tool_name) or {"server_id": "", "tool_name": tool_name}
    response_text = _extract_mcp_response(payload)
    if not response_text:
        return _emit_allow()

    try:
        finding = _scan.scan_tool_result(
            response_text,
            server_id=parsed["server_id"],
            tool_name=parsed["tool_name"],
        )
    except Exception:
        return _emit_allow()

    # PLAN-044 audit-v2 C1-P0-03 fix (Wave B): hasattr guard removed.
    # emit_mcp_injection_finding is now registered in audit_emit.py
    # `_KNOWN_ACTIONS` and the function is shipped — the pre-Wave-B
    # guard short-circuited to silent no-op, breaking 5 cross-validating
    # audit-v2 findings (dim 04, 06, 07, 16, 18). Advisory contract
    # preserved via try/except — emission failure never blocks user.
    mode = _resolve_mode()
    will_block = mode == "strict" and finding.matched and finding.severity == "high"
    # SPEC v1 audit-log.schema.md §mcp_injection_finding declares
    # scanner_action enum {advisory, stripped, blocked}. Session 73 wired
    # `"block"` (verb form) instead of `"blocked"` (state form) AND let the
    # non-block branch fall through to `mode` which can be "strict" — also
    # not in the SPEC enum. Session 75 Codex Finding 6 closure aligns code
    # to SPEC. "stripped" is reserved for Phase 2 transformation and is
    # not emitted today; non-blocking scans always log as "advisory".
    scanner_action = "blocked" if will_block else "advisory"

    if finding.matched:
        try:
            _audit.emit_mcp_injection_finding(
                server_id=finding.source.server_id,
                mcp_tool_name=finding.source.tool_name,
                source_kind=finding.source.source_kind,
                family_counts=finding.family_counts,
                match_count=finding.match_count,
                bytes_scanned=finding.bytes_scanned,
                severity=finding.severity,
                snippet_preview=finding.snippet_preview,
                scanner_action=scanner_action,
                session_id=payload.get("session_id", ""),
                project=payload.get("project", ""),
            )
        except Exception:
            pass  # emission failure never blocks user

    if will_block:
        reason = (
            "MCP-INJECTION-BLOCKED: high-severity directive detected in "
            f"{finding.source.tool_name!r} response "
            f"(families={sorted(finding.family_counts.keys())!r}, "
            f"severity={finding.severity!r}). STRICT mode active "
            "(CEO_MCP_SCANNER_MODE=strict). To bypass once: "
            "CEO_MCP_SCANNER_DISABLE=1; to revert globally: "
            "unset CEO_MCP_SCANNER_MODE."
        )
        return _emit_block(reason)

    return _emit_allow()


if __name__ == "__main__":
    sys.exit(main())
