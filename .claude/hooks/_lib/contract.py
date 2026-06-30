"""Hook Adapter Layer — neutral `NormalizedEvent` + `Decision` dataclasses.

PLAN-004 Phase 4 (refactor-only scope per consensus C4). Introduces a
stable, IDE-agnostic contract between hook business logic and IDE
payload shape. Today the only adapter is `adapters.claude` (matching
Claude Code's stdin/stdout convention identically). Future IDEs
(Gemini CLI, Codex CLI) plug in by adding a module under `adapters/`
that translates their shape to/from these types.

## Migration path (deferred)

Today each hook (`check_agent_spawn.py`, `check_plan_edit.py`,
`check_bash_safety.py`, `audit_log.py`) reads `_lib.payload.parse_stdin`
directly. Those hooks keep working unchanged.

A future refactor (Sprint 5) migrates each hook's `main()` to:

```python
from _lib import contract
from _lib.adapters import claude as claude_adapter

def main():
    event = claude_adapter.read_event(sys.stdin)
    decision = decide_normalized(event)   # renamed, now takes NormalizedEvent
    sys.stdout.write(claude_adapter.write_decision(decision))
    return 0
```

This contract ships now so the shape is locked before more hooks or
adapters arrive. The actual rewire is purely refactor and will be
behavior-identical — all 168 existing tests must pass unchanged after
the swap.

## Why a neutral event?

- Gemini CLI posts `{"tool": "...", "args": {...}}` (different field names)
- Codex CLI posts `{"op": "...", "params": {...}}` (different structure)
- The decide() logic doesn't care — it wants a dataclass with stable fields

By funneling everything through `NormalizedEvent`, the governance logic
stays portable and the adapter surface stays boring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NormalizedEvent:
    """IDE-agnostic representation of a hook invocation.

    Field names are chosen to match Claude Code's current JSON payload
    field names exactly, so the Claude adapter is a near-identity map.
    Other IDEs will translate into this shape.
    """

    # Core identifiers
    session_id: str = ""
    project: str = ""
    phase: str = "PreToolUse"  # PreToolUse | PostToolUse | PostToolUseFailure

    # Tool being invoked
    tool_name: str = ""

    # Tool-specific input (PreToolUse payload)
    tool_input: Dict[str, Any] = field(default_factory=dict)

    # Tool response (PostToolUse payload; empty dict for PreToolUse)
    tool_response: Dict[str, Any] = field(default_factory=dict)

    # Convenience accessors populated from tool_input for common tools.
    # Empty string if field absent.
    description: str = ""
    prompt: str = ""
    subagent_type: str = ""
    file_path: str = ""
    old_string: str = ""
    new_string: str = ""
    replace_all: bool = False
    command: str = ""

    # PLAN-125 WS-1 — per-tool-call lifecycle telemetry. Named scalar
    # fields surfaced from the top-level Claude Code hook payload (siblings
    # of `tool_name` / `tool_response`). They are exposed as *named*
    # attributes, NOT by re-opening the bulk `raw_payload` dict (which stays
    # empty — see adapters/claude.py). `tool_use_id` is the per-call pairing
    # key (present + identical across Pre/Post/Failure); `duration_ms` is the
    # native wall-clock on Post/Failure (None on Pre / when absent).
    tool_use_id: str = ""
    duration_ms: Optional[int] = None

    # Raw payload preserved for adapters that need access to fields
    # not exposed as named attributes.
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    # Non-fatal parse errors (e.g. malformed JSON); decide() fails open.
    parse_error: Optional[str] = None

    def is_pretooluse(self) -> bool:
        """True iff this event was emitted before the tool invocation.

        PreToolUse events carry ``tool_input`` (the arguments Claude will
        pass to the tool) and let the hook decide allow / block / etc.
        Decisions here can cancel the tool call.
        """
        return self.phase == "PreToolUse"

    def is_posttooluse(self) -> bool:
        """True iff this event was emitted after the tool completed.

        PostToolUse events carry ``tool_output`` (the tool's result) and
        are observer-only — hooks can log, audit, or emit systemMessages,
        but cannot retroactively cancel a completed tool call. Use
        PostToolUse for forensic / post-hoc verification (e.g.
        check_skill_reference_read.py TOCTOU observer).
        """
        return self.phase == "PostToolUse"

    def is_posttooluse_failure(self) -> bool:
        """True iff this event was emitted after the tool FAILED.

        PLAN-125 WS-1 — `PostToolUseFailure` is a *distinct* Claude Code
        phase (the tool ran and errored). Kept separate from
        ``is_posttooluse`` so success/failure stay distinguishable: the
        failure phase MUST NOT satisfy ``is_posttooluse()``. Lifecycle
        telemetry maps ``success = not is_posttooluse_failure()``.
        """
        return self.phase == "PostToolUseFailure"


@dataclass
class Decision:
    """IDE-agnostic decision produced by a hook.

    Adapters translate this to the IDE's expected stdout shape. For
    Claude Code this is a one-line JSON object with `decision` +
    optional `reason` / `systemMessage` / `message`.
    """

    allow: bool = True
    reason: Optional[str] = None
    system_message: Optional[str] = None
    message: Optional[str] = None
    # Adapters may stash extra vendor-specific fields here without
    # changing the neutral contract.
    extra: Dict[str, Any] = field(default_factory=dict)

    def with_reason(self, reason: str) -> "Decision":
        """Return a copy marked as block with the given reason."""
        return Decision(
            allow=False,
            reason=reason,
            system_message=self.system_message,
            message=self.message,
            extra=dict(self.extra),
        )

    def as_allow(self) -> "Decision":
        """Return a copy marked as allow (reason dropped)."""
        return Decision(
            allow=True,
            reason=None,
            system_message=self.system_message,
            message=self.message,
            extra=dict(self.extra),
        )


# -----------------------------------------------------------------------------
# Decision builders (used by hook logic that doesn't touch adapters directly)
# -----------------------------------------------------------------------------


def allow(system_message: Optional[str] = None, message: Optional[str] = None) -> Decision:
    """Return an allow `Decision` (no reason, optional system_message + message).

    Hooks use this to build a PreToolUse/PostToolUse response that lets the
    tool call proceed. Adapters translate the Decision to the IDE's stdout
    shape (e.g. `{"decision": "allow"}` for Claude Code).
    """
    return Decision(allow=True, reason=None, system_message=system_message, message=message)


def block(reason: str, system_message: Optional[str] = None) -> Decision:
    """Return a block `Decision` with the given reason (required).

    Hooks use this to refuse a tool call — the `reason` string surfaces to
    the user. A governance hook MUST supply a human-readable reason so
    the user can act on the refusal. Adapters translate this to the IDE's
    stdout shape (e.g. `{"decision": "block", "reason": "..."}` for Claude).
    """
    return Decision(allow=False, reason=reason, system_message=system_message)


# -----------------------------------------------------------------------------
# Adapter registry (for runtime adapter resolution)
# -----------------------------------------------------------------------------

# Maps adapter name → module name under `_lib.adapters`.
# As of PLAN-081 Phase 1-full (v1.13.0), `claude` + `codex` are
# implemented. Add new adapters by:
#   1. Creating `_lib/adapters/<name>.py` with `read_event(stream) -> NormalizedEvent`
#      and `write_decision(d: Decision) -> str` functions
#   2. Adding the name here AND in `_lib/adapters/__init__.py:ADAPTER_REGISTRY`
#      (the two MUST stay in sync — drift detector flags divergence)
#   3. Shipping golden fixtures under
#      `.claude/hooks/tests/fixtures/adapters/<name>/{in,out}/*.json`
#   4. Documenting the dispatch via `CEO_HOOK_ADAPTER=<name>`
#
# Phase 1-full extension: ["claude"] → ["claude", "codex"] for
# Pair-Rail Multi-LLM cross-review. KERNEL_OVERRIDE consumed
# (PLAN-081-PHASE-1-CODEX-ADAPTER + I-ACCEPT) per check_arbitration_
# kernel.py:90 _KERNEL_PATHS HARD-DENY enforcement on this file.
KNOWN_ADAPTERS: List[str] = ["claude", "codex"]

DEFAULT_ADAPTER: str = "claude"

# Env-var override (Sprint 5 Phase 4). When set to a known adapter name,
# `resolve_adapter()` returns that adapter; otherwise it returns DEFAULT_ADAPTER.
ADAPTER_ENV_VAR: str = "CEO_HOOK_ADAPTER"


def resolve_adapter(env: Optional[Dict[str, str]] = None) -> str:
    """Return the adapter name to use for this invocation.

    Reads `CEO_HOOK_ADAPTER` from the given env (or `os.environ` if None).
    Unknown / empty values fall back to DEFAULT_ADAPTER and emit nothing
    (silent fallback — observability is via audit_emit, not stderr).
    """
    import os as _os

    src = env if env is not None else _os.environ
    requested = (src.get(ADAPTER_ENV_VAR) or "").strip()
    if not requested:
        return DEFAULT_ADAPTER
    if requested in KNOWN_ADAPTERS:
        return requested
    return DEFAULT_ADAPTER


def load_adapter(name: Optional[str] = None) -> Any:
    """Import and return the adapter module for the resolved name.

    Returns the loaded module (with `read_event` + `write_decision`
    callables). Raises ImportError if the adapter module is missing
    despite being in KNOWN_ADAPTERS (a packaging bug).
    """
    import importlib

    adapter_name = name or resolve_adapter()
    module_path = f"_lib.adapters.{adapter_name}"
    return importlib.import_module(module_path)
