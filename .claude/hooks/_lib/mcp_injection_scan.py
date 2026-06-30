"""MCP-source injection scanner (PLAN-052 / ADR-083).

Wraps ``_lib/injection_patterns.scan_harness_mimicry`` to scan content
returned by MCP (Model Context Protocol) tool calls + resource fetches.
Provides MCP-specific source tagging + provenance metadata for audit
log enrichment.

Threat model (analogous to ADR-077 WebFetch surface, broader scope):

1. **MCP tool result**: server returns text containing `<system-reminder>`,
   `<important>`, `<function_calls>`, role-preamble or directive-prose
   markup that the model interprets as harness directives.
2. **MCP resource fetch**: read-only-by-contract endpoint returns
   attacker-controlled content (e.g. fetched URL, file contents).
3. **MCP server instructions** (server-level concatenation): out-of-scope
   for runtime PostToolUse scan; see ADR-083 §Future for proposed
   PreToolUse settings.json scanner (Phase 2).

API:
    from _lib.mcp_injection_scan import McpSource, scan, classify

    finding = scan(
        content=tool_result_text,
        source=McpSource(server_id="local-files", tool_name="read_file"),
    )
    if finding.matched:
        ...  # emit advisory; never block

Stdlib-only. Fail-open on every error (advisory, never raise).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from _lib import injection_patterns as _ip

# ---------------------------------------------------------------------------
# Source tagging
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class McpSource:
    """Provenance tag attached to every scan call."""

    server_id: str = ""
    tool_name: str = ""
    source_kind: str = "tool_result"  # "tool_result" | "resource_fetch" | "instructions"
    resource_uri: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "server_id": self.server_id,
            "tool_name": self.tool_name,
            "source_kind": self.source_kind,
            "resource_uri": self.resource_uri,
        }


@dataclass(frozen=True)
class McpFinding:
    """Outcome of a single scan call."""

    matched: bool
    source: McpSource
    family_counts: Dict[str, int]
    match_count: int
    bytes_scanned: int
    truncated: bool
    severity: str  # "low" | "medium" | "high"
    snippet_preview: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matched": self.matched,
            "source": self.source.to_dict(),
            "family_counts": dict(self.family_counts),
            "match_count": self.match_count,
            "bytes_scanned": self.bytes_scanned,
            "truncated": self.truncated,
            "severity": self.severity,
            "snippet_preview": self.snippet_preview,
        }


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

# Family → severity mapping. Tunable as patterns evolve. High = directive
# attempts at hijacking model behavior; Medium = role-preamble + harness
# mimicry markers + provider tokens; Low = unrecognized signal.
# Catalog source: _lib/injection_patterns.py (4 active families today).
# Synthetic-tool-call patterns (`<function_calls>`, `<tool_use>`) are
# Phase 2 — documented in ADR-080 §H4 as fabrication formats observed.
_SEVERITY_BY_FAMILY: Dict[str, str] = {
    "directive_prose": "high",
    "synthetic_tool_call": "high",  # reserved for Phase 2 catalog expansion
    "role_preamble": "medium",
    "harness_mimicry": "medium",
    "provider_tokens": "medium",
}


def classify(family_counts: Dict[str, int]) -> str:
    """Highest severity across families present. ``low`` if only weak signals."""
    if not family_counts:
        return "low"
    severities = [
        _SEVERITY_BY_FAMILY.get(family, "low")
        for family, count in family_counts.items()
        if count > 0
    ]
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Public scanner
# ---------------------------------------------------------------------------


def scan(
    content: Any,
    *,
    source: McpSource,
    max_bytes: int = 1_048_576,
    snippet_max_len: int = 200,
) -> McpFinding:
    """Scan ``content`` from an MCP source. Never raises.

    Returns ``McpFinding`` with ``matched`` True iff any harness-mimicry
    or directive-prose pattern hit. Severity escalates per
    ``_SEVERITY_BY_FAMILY``.
    """
    if not isinstance(content, str):
        # Accept bytes-like → decode safely. Anything else → empty advisory.
        try:
            if isinstance(content, (bytes, bytearray)):
                content = bytes(content).decode("utf-8", errors="replace")
            else:
                content = str(content) if content is not None else ""
        except Exception:
            return McpFinding(
                matched=False,
                source=source,
                family_counts={},
                match_count=0,
                bytes_scanned=0,
                truncated=False,
                severity="low",
                snippet_preview="",
            )

    try:
        result = _ip.scan_harness_mimicry(content, max_bytes=max_bytes)
    except Exception:
        return McpFinding(
            matched=False,
            source=source,
            family_counts={},
            match_count=0,
            bytes_scanned=0,
            truncated=False,
            severity="low",
            snippet_preview="",
        )

    severity = classify(result.family_counts) if result.matched else "low"
    snippet = ""
    if result.matched and result.matches:
        m = result.matches[0]
        snippet = m.snippet[:snippet_max_len] if m.snippet else ""

    return McpFinding(
        matched=result.matched,
        source=source,
        family_counts=dict(result.family_counts),
        match_count=len(result.matches),
        bytes_scanned=result.bytes_scanned,
        truncated=result.truncated,
        severity=severity,
        snippet_preview=snippet,
    )


def scan_tool_result(
    content: Any,
    *,
    server_id: str,
    tool_name: str,
    max_bytes: int = 1_048_576,
) -> McpFinding:
    """Convenience wrapper for PostToolUse hook scanning MCP tool results."""
    return scan(
        content,
        source=McpSource(
            server_id=server_id,
            tool_name=tool_name,
            source_kind="tool_result",
        ),
        max_bytes=max_bytes,
    )


def scan_resource_fetch(
    content: Any,
    *,
    server_id: str,
    resource_uri: str,
    max_bytes: int = 1_048_576,
) -> McpFinding:
    """Convenience wrapper for resource-fetch return scanning."""
    return scan(
        content,
        source=McpSource(
            server_id=server_id,
            tool_name="",
            source_kind="resource_fetch",
            resource_uri=resource_uri,
        ),
        max_bytes=max_bytes,
    )


def is_mcp_tool_name(tool_name: str) -> bool:
    """Heuristic: Claude Code MCP tools are namespaced ``mcp__<server>__<tool>``."""
    if not isinstance(tool_name, str) or not tool_name:
        return False
    return tool_name.startswith("mcp__")


def parse_mcp_tool_name(tool_name: str) -> Optional[Dict[str, str]]:
    """Extract ``server_id`` and ``tool_name`` from a Claude Code MCP tool ref.

    ``mcp__foo_server__list_files`` → ``{"server_id": "foo_server", "tool_name": "list_files"}``.
    Returns None if format does not match.
    """
    if not is_mcp_tool_name(tool_name):
        return None
    rest = tool_name[len("mcp__"):]
    parts = rest.split("__", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    return {"server_id": parts[0], "tool_name": parts[1]}
