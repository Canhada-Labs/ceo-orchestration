"""Hook adapter package.

Each adapter module in this package translates a provider-specific hook
wire shape into the canonical `NormalizedEvent` from
`.claude/hooks/_lib/contract.py`, and serializes `Decision` back to
the provider's expected stdout shape.

Adapter ABI: `SPEC/v1/adapters.schema.md`.
Canonical envelope: `SPEC/v1/normalized_envelope.schema.md`.

## Registered adapters

- `claude` — Claude Code (production).
- `codex` — Codex MCP (PLAN-081 Phase 1-full, v1.13.0). Used by the
  Pair-Rail dispatcher for cross-LLM review.

ADR-084 §Decision item 1 (Claude-only thesis, 2026-04-27) deferred
multi-adapter support pending demand. PLAN-075 (v5, 2026-05-09) +
PLAN-081 (R1 5/5 ADJUST PROCEED, 2026-05-09 S98) escalated demand:
the Pair-Rail Multi-LLM architecture requires a Codex adapter for
cross-review. Phase 1-full of PLAN-081 ships the Codex adapter +
egress redactor + ingress sanitization PostToolUse hook. Future
provider adapters (Gemini, local-LLM via Ollama) require their own
PLAN-NNN with explicit ADAPTER_REGISTRY extension via this file.

## Registry

`ADAPTER_REGISTRY` is the authoritative list of shipped adapter names,
mirrored by `_lib.contract.KNOWN_ADAPTERS`. The env var
`CEO_HOOK_ADAPTER` selects at runtime (default `claude`); unknown
values silently fall back.
"""

from __future__ import annotations

from typing import List

# Mirror of _lib.contract.KNOWN_ADAPTERS. Duplicated intentionally so
# that downstream tools can import the list without pulling in the
# contract module. Keep in sync with KNOWN_ADAPTERS; drift detector
# will flag if they diverge.
#
# PLAN-081 Phase 1-full extension: ["claude"] → ["claude", "codex"].
# Codex adapter implements SPEC/v1/adapters.schema.md ABI in full
# (read_event / read_post_event / write_decision / emit_decision)
# plus Pair-Rail-specific helpers (_classify_prompt_complexity,
# parse_verdict, make_invoke_command, compute_redaction_inputs).
ADAPTER_REGISTRY: List[str] = ["claude", "codex"]

# PLAN-090 Wave B — BatchClaudeLiveAdapter re-export (ADR-123).
# PERF: import is LAZY to avoid paying the ~44ms ssl/socket/urllib.request
# import tax on every hook subprocess that only needs `_lib.adapters.claude`.
# The live transport chain (live/__init__.py → _transport.py) eagerly imports
# ssl + socket + urllib.request; those modules add ~32ms to subprocess startup
# on macOS/ubuntu over the python3 baseline (~12ms). This lazy wrapper defers
# the import to the first call-site that actually instantiates BatchClaudeLiveAdapter
# (always a CEO_LIVE_CLAUDE=1 live-adapter path, never a governance hook path).
# See PLAN-120 WS-J check_agent_spawn p99 regression diagnosis.
_BatchClaudeLiveAdapter = None  # type: ignore[assignment]


def _get_batch_claude_live_adapter():
    """Lazy accessor for BatchClaudeLiveAdapter — defers ssl/socket import.

    Call-sites that previously imported BatchClaudeLiveAdapter at module level
    MUST migrate to calling _get_batch_claude_live_adapter() instead.  The
    returned class is identical; the deferred import is the only difference.
    Returns None if the live adapter package is unavailable (fail-open).
    """
    global _BatchClaudeLiveAdapter
    if _BatchClaudeLiveAdapter is None:
        try:
            from .live.claude_batch import BatchClaudeLiveAdapter  # noqa: PLC0415
            _BatchClaudeLiveAdapter = BatchClaudeLiveAdapter
        except Exception:  # pragma: no cover — defensive
            pass
    return _BatchClaudeLiveAdapter


# Backward-compat attribute access via __getattr__ so existing
# `from _lib.adapters import BatchClaudeLiveAdapter` call-sites continue to
# work without modification (they just pay the import cost at their own call
# time rather than at package init time).
def __getattr__(name: str):
    if name == "BatchClaudeLiveAdapter":
        return _get_batch_claude_live_adapter()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
