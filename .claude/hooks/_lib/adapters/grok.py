"""Grok Build hook adapter — HOST adapter (PLAN-156 Wave 2, SENT-GK-A).

## Role

Single-role, unlike ``codex.py``: xAI's Grok Build CLI (binary ``grok``,
pinned exactly in ``.claude/governance/grok-cli-pin.txt`` — a 0.x product
on a DAILY release cadence) runs OUR governance hooks via its lifecycle
hooks, and this adapter translates its wire. There is no
grok-as-reviewer role (the inverted pair-rail keeps Claude as the
reviewer — see PLAN-156 Wave 5), so nothing here is dual-contract.

## The wire (recorded live, grok 0.2.93 — fixtures:
``PLAN-156/artifacts/grok-wire-fixtures-0.2.93.ndjson``)

Ingress (stdin JSON, **camelCase keys**, snake_case event VALUES)::

    {"hookEventName": "pre_tool_use",       # ← the host-wire marker
     "sessionId": "...", "cwd": "...", "workspaceRoot": "...",
     "toolName": "run_terminal_command",     # ← NATIVE tool vocabulary
     "toolInput": {"command": "npm test"},
     "toolInputTruncated": false, "toolUseId": "call-...",
     "permissionMode": "...", "transcriptPath": "...",
     "timestamp": "2026-07-12T..."}

Egress (PreToolUse is the ONLY blocking event)::

    {"decision": "deny", "reason": "..."}    # blocks the tool call
    {"decision": "allow"}                    # or exit 0 with no output

## Three semantics that differ from every other host (S269 probes)

1. **``block`` is not a word grok knows.** Our internal Claude/codex
   vocabulary emits ``{"decision": "block"}``; on grok that is
   *unrecognized output* → hook-failure → **fail-OPEN**, and — the
   load-bearing finding — **exit 2 does NOT rescue it** (probe P5:
   ``{"decision":"block"}`` + exit 2 ⇒ the tool RAN). So egress
   normalization (``block`` → ``deny``) is the enforcement mechanism
   here, not the exit code. ``write_decision`` below is the only place
   that mapping lives.
2. **A clean stdout deny blocks on its own** (probe P2: deny + exit 0 ⇒
   blocked). Exit 2 with clean/empty stdout also denies (probe P7). Both
   channels work; a MALFORMED stdout beats a correct exit code. Hence
   the shim chokepoint (``_python-hook.sh``) maps emitted-deny → exit 2
   as belt-and-suspenders while THIS module guarantees the stdout half.
3. **Crash / timeout / any other exit = fail-OPEN** (probe P6), which is
   native grok behavior and coincides with the CLAUDE.md §4 infra half.
   An INPUT-class failure (a payload a security matcher cannot parse)
   must therefore still EMIT a structured deny — never merely raise —
   which is why the coherence gate below mirrors ``codex.py``'s.

## Tool-name vocabulary (matcher + wire, both NATIVE)

Grok evaluates the hook ``matcher`` regex BEFORE spawning our process,
against the NATIVE tool name — but it also accepts Claude names as
aliases (``^Bash$`` fires for ``run_terminal_command``; a matcher keeps
its original name too). The stdin ``toolName`` is ALWAYS native. So:

- templates must match on **both** vocabularies (a native-only matcher
  is fine, a Claude-only matcher works via aliasing, but our positive
  control drives the NATIVE name — a mapped-name-only test proves
  nothing, PLAN-156 debate C3 / S254 dead-gate class);
- ``read_event`` normalizes the native name to our internal vocabulary
  so every downstream guard (canonical-edit, bash-safety, plan-edit,
  arbitration-kernel) sees the shape it already knows.

NOTE the S266 research said the shell tool is ``run_terminal_cmd``. It
is **``run_terminal_command``** on the hooks wire (0.2.93, recorded).
The product's own headless doc still says ``run_terminal_cmd`` for
``--tools`` — the two surfaces disagree upstream; the fixtures pin the
hooks truth and ``_TOOL_ALIASES`` accepts both so a future rename
degrades to a no-op rather than a dead gate.

ABI compliance: SPEC/v1/adapters.schema.md §3 (read_event /
read_post_event / write_decision / emit_decision), plus the PLAN-156
exit-ABI amendment (emitted-deny → exit 2 at the shim). Fail-open
invariant preserved for INFRASTRUCTURE (parse_error → allow);
fail-CLOSED for INPUT at security matchers (coherence gate).
"""

from __future__ import annotations

import json
import sys
from typing import IO, Any, Dict, Optional, Tuple

from .. import contract as _contract
from .. import payload as _payload

# ---------------------------------------------------------------------------
# Module-level constants per SPEC/v1/adapters.schema.md §2
# ---------------------------------------------------------------------------

#: SemVer for the adapter implementation. Bump per SPEC §2.1.
ADAPTER_VERSION: str = "1.0.0"

#: Provider capabilities per SPEC §2.2.
CAPABILITIES: Dict[str, Any] = {
    "streaming_tool_use": False,
    "json_mode": "advisory",
    "function_calling": True,
    "system_prompt_slot": True,
}

#: Audit-emit field allowlist per Sec MF-3.
AUDIT_EMIT_KEYS: Tuple[str, ...] = (
    "agent_provider",
    "session_id",
    "tool_name",
    "decision",
)

#: Top-level key whose presence identifies the grok HOST wire.
_HOST_WIRE_KEY: str = "hookEventName"

#: raw_payload marker: this NormalizedEvent came from the grok host wire.
HOST_WIRE_FLAG_KEY: str = "ceo_host_wire_grok"

#: raw_payload key carrying a coherence-gate violation reason. Presence
#: makes the emitters fail-CLOSED (deny) regardless of the Decision the
#: hook computed. INPUT-class per PLAN-152 C4.
COHERENCE_ERROR_KEY: str = "ceo_coherence_error"

#: Grok-wire scalars preserved verbatim into raw_payload.
_HOST_PASSTHROUGH_KEYS: Tuple[str, ...] = (
    "hookEventName",
    "cwd",
    "workspaceRoot",
    "transcriptPath",
    "permissionMode",
    "timestamp",
    "toolInputTruncated",
    "toolResultTruncated",
    "isBackgrounded",
    "source",
    "reason",
    "promptId",
)

#: Native grok tool name → our internal (Claude) vocabulary. Recorded
#: from the bundled 0.2.93 alias table + live fixtures. BOTH spellings of
#: the shell tool are accepted: the hooks wire says ``run_terminal_command``
#: (recorded), the headless ``--tools`` doc says ``run_terminal_cmd``.
#: Mapping an unknown-but-plausible future rename to Bash is strictly
#: safer than leaving it unmapped (an unmapped edit/shell tool would sail
#: past every matcher-shaped guard — the dead-gate class).
_TOOL_ALIASES: Dict[str, str] = {
    "run_terminal_command": "Bash",
    "run_terminal_cmd": "Bash",
    "read_file": "Read",
    "search_replace": "Edit",
    "write_file": "Write",
    "grep": "Grep",
    "list_dir": "Glob",
    "web_search": "WebSearch",
    "web_fetch": "WebFetch",
    "spawn_subagent": "Task",
}

#: Grok event names (snake_case VALUES on the wire) → our phase strings.
#: Only ``pre_tool_use`` is BLOCKING on grok; everything else is passive
#: (the honest-ADVISORY rows in the capability matrix).
_EVENT_PHASES: Dict[str, str] = {
    "pre_tool_use": "PreToolUse",
    "post_tool_use": "PostToolUse",
    "post_tool_use_failure": "PostToolUseFailure",
    "session_start": "SessionStart",
    "session_end": "SessionEnd",
    "user_prompt_submit": "UserPromptSubmit",
    "stop": "Stop",
    "stop_failure": "StopFailure",
    "notification": "Notification",
    "subagent_start": "SubagentStart",
    "subagent_stop": "SubagentStop",
    "permission_denied": "PermissionDenied",
    "pre_compact": "PreCompact",
    "post_compact": "PostCompact",
}

#: The ONLY grok event that can block a tool call. Every other event's
#: deny is cosmetic — the adapter still emits a well-formed decision (so
#: transcripts show WHY), but the capability matrix must never claim
#: enforcement outside this set.
BLOCKING_EVENTS: Tuple[str, ...] = ("PreToolUse",)

#: Claude-native tool names grok NEVER emits on the wire (its tools are
#: the native names above). Seeing one WITH Claude-native tool_input keys
#: under the grok host adapter is a recognizably cross-harness envelope
#: (the debate-A2 coherence class, ported from codex.py).
_CLAUDE_NATIVE_TOOLS: Tuple[str, ...] = (
    "Edit",
    "Write",
    "MultiEdit",
    "NotebookEdit",
    "Task",
)

_CLAUDE_NATIVE_INPUT_KEYS: Tuple[str, ...] = (
    "file_path",
    "old_string",
    "new_string",
    "subagent_type",
)


def _cross_harness_reason(
    raw_tool_name: str,
    tool_input: Dict[str, Any],
) -> Optional[str]:
    """Detect a Claude-native envelope arriving under the grok adapter.

    Mirrors ``codex._cross_harness_reason``. A mis-set
    ``CEO_HOOK_ADAPTER=grok`` under Claude Code would otherwise let a
    guard normalize a Claude event with grok assumptions and emit a
    decision in the wrong vocabulary — a silent allow (S254 dead-gate).
    Fail-CLOSED per PLAN-152 C4: INPUT the guard cannot trust is denied.

    CRITICAL — checks the RAW wire tool name, NOT the normalized one
    (S269 live-fire bug): grok's native edit tool is ``search_replace``,
    never ``Edit``. Checking the NORMALIZED name would flag EVERY
    legitimate grok edit as cross-harness (search_replace → Edit → in
    _CLAUDE_NATIVE_TOOLS → false deny). A genuine cross-harness envelope
    carries a Claude-native name ON THE WIRE (``Edit``/``Write``/``Task``)
    — which grok never emits — so the raw check is both correct and
    sufficient.
    """
    if not raw_tool_name:
        return None
    if raw_tool_name in _CLAUDE_NATIVE_TOOLS and any(
        k in tool_input for k in _CLAUDE_NATIVE_INPUT_KEYS
    ):
        return (
            "Claude-native tool envelope ({0!r} on the grok wire — grok emits "
            "search_replace/run_terminal_command/spawn_subagent, never this) "
            "with {1}; cross-harness envelope, INPUT-class failure fails "
            "CLOSED per PLAN-152 C4".format(
                raw_tool_name,
                sorted(k for k in _CLAUDE_NATIVE_INPUT_KEYS if k in tool_input),
            )
        )
    return None


def normalize_tool_name(native: str) -> str:
    """Map a native grok tool name to our internal vocabulary.

    Unknown names pass through unchanged (a guard that matches on the
    internal vocabulary simply will not fire — the SAME posture as an
    unknown tool under Claude Code, and strictly better than guessing).
    """
    return _TOOL_ALIASES.get(native, native)


def coherence_error(event: Any) -> Optional[str]:
    """Return the coherence violation carried by an event, if any. NEVER raises."""
    try:
        rp = getattr(event, "raw_payload", None)
        if isinstance(rp, dict):
            val = rp.get(COHERENCE_ERROR_KEY)
            return str(val) if val else None
    except Exception:  # pragma: no cover (defensive)
        pass
    return None


def _read_host_event(data: Dict[str, Any], phase_arg: str) -> _contract.NormalizedEvent:
    """Normalize a grok host-wire payload into a NormalizedEvent."""
    import os as _os

    wire_event = str(data.get(_HOST_WIRE_KEY) or "")
    phase = _EVENT_PHASES.get(wire_event, phase_arg)

    native_tool = str(data.get("toolName") or "")
    wire_tool_input = data.get("toolInput")
    tool_input: Dict[str, Any] = (
        dict(wire_tool_input) if isinstance(wire_tool_input, dict) else {}
    )

    resp = data.get("toolResult")
    if isinstance(resp, dict):
        tool_response: Dict[str, Any] = resp
    elif isinstance(resp, str):
        # Grok delivers tool results as a plain string (same shape class
        # as codex 0.139) — wrap so the contract field stays Dict-typed.
        tool_response = {"output": resp}
    else:
        tool_response = {}

    raw_payload: Dict[str, Any] = {HOST_WIRE_FLAG_KEY: True}
    for key in _HOST_PASSTHROUGH_KEYS:
        if key in data:
            raw_payload[key] = data[key]
    if native_tool:
        raw_payload["tool_name_raw"] = native_tool

    tool_name = normalize_tool_name(native_tool)

    # Coherence check runs on the RAW wire name (native_tool), NOT the
    # normalized one — see _cross_harness_reason (S269 live-fire fix): a
    # legitimate grok `search_replace` normalizes to `Edit` and would
    # otherwise self-trip the gate.
    coherence = _cross_harness_reason(native_tool, tool_input)
    if coherence is not None:
        raw_payload[COHERENCE_ERROR_KEY] = coherence

    # `search_replace` (Edit) carries its path under one of several keys
    # depending on the tool variant; take the first present. `file_path`
    # is what every downstream guard reads.
    file_path = ""
    for key in ("file_path", "filePath", "path", "target_file"):
        val = tool_input.get(key)
        if isinstance(val, str) and val:
            file_path = val
            break
    if file_path:
        tool_input.setdefault("file_path", file_path)

    prompt = str(data.get("prompt") or tool_input.get("prompt") or "")
    subagent_type = str(
        tool_input.get("subagent_type") or tool_input.get("agent_type") or ""
    )
    if subagent_type:
        tool_input.setdefault("subagent_type", subagent_type)

    return _contract.NormalizedEvent(
        session_id=str(data.get("sessionId") or ""),
        project=str(
            data.get("workspaceRoot")
            or data.get("cwd")
            or _os.environ.get("CLAUDE_PROJECT_DIR")
            or ""
        ),
        phase=phase,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        description="",
        prompt=prompt,
        subagent_type=subagent_type,
        file_path=file_path,
        old_string=str(tool_input.get("old_string") or ""),
        new_string=str(tool_input.get("new_string") or ""),
        replace_all=bool(tool_input.get("replace_all") or False),
        command=str(tool_input.get("command") or ""),
        tool_use_id=str(data.get("toolUseId") or ""),
        duration_ms=None,
        raw_payload=raw_payload,
    )


# ---------------------------------------------------------------------------
# Hook ABI per SPEC §3
# ---------------------------------------------------------------------------


def read_event(
    stream: "Optional[IO[str]]" = None,
    phase: str = "PreToolUse",
) -> _contract.NormalizedEvent:
    """Parse a grok hook payload into a NormalizedEvent. SPEC §3.1.

    The wire's ``hookEventName`` WINS over the ``phase`` argument (the
    wire is ground truth). Fail-open: any parse failure returns
    ``NormalizedEvent(parse_error=...)`` — INFRASTRUCTURE per SPEC §4 —
    and NEVER raises to the hook caller.
    """
    if stream is None:
        stream = sys.stdin

    try:
        p = _payload.parse_stdin(stream=stream)
    except Exception as e:  # pragma: no cover (defensive)
        return _contract.NormalizedEvent(
            parse_error="[grok] stdin read failed: {0}".format(type(e).__name__),
            phase=phase,
        )

    if p.raw_error:
        return _contract.NormalizedEvent(
            parse_error="[grok] {0}".format(p.raw_error),
            session_id=p.session_id or "",
            phase=phase,
            raw_payload={},
        )

    try:
        data = json.loads(p.raw) if p.raw and p.raw.strip() else None
    except Exception:  # pragma: no cover (parse_stdin already validated)
        data = None

    if isinstance(data, dict) and _HOST_WIRE_KEY in data:
        return _read_host_event(data, phase)

    # Not the grok wire. Under CEO_HOOK_ADAPTER=grok this is a
    # cross-harness envelope: fail-CLOSED at INPUT (C4) rather than
    # silently normalizing a foreign shape with grok assumptions.
    return _contract.NormalizedEvent(
        session_id=p.session_id or "",
        phase=phase,
        tool_name=p.tool_name or "",
        tool_input=p.tool_input if isinstance(p.tool_input, dict) else {},
        raw_payload={
            COHERENCE_ERROR_KEY: (
                "payload carries no 'hookEventName' — not the grok host wire; "
                "refusing to normalize a foreign envelope under "
                "CEO_HOOK_ADAPTER=grok (PLAN-152 C4 fail-CLOSED on INPUT)"
            ),
            HOST_WIRE_FLAG_KEY: True,
        },
    )


def read_post_event(stream: "Optional[IO[str]]" = None) -> _contract.NormalizedEvent:
    """Convenience: PostToolUse parse. SPEC §3.2."""
    return read_event(stream=stream, phase="PostToolUse")


def write_decision(
    decision: _contract.Decision,
    event: Any = None,
) -> str:
    """Serialize a Decision to the grok decision wire. SPEC §3.3.

    **This is the enforcement point on grok** (see module docstring §2):
    the emitted vocabulary is ``deny``/``allow`` — NEVER ``block``, which
    grok treats as malformed output and fail-OPENs on, *even with exit 2*
    (probe P5). Any hook that hands us a Claude-vocabulary Decision gets
    it translated here; nothing downstream needs to know.

    Coherence override: an event carrying ``ceo_coherence_error`` FORCES
    a deny regardless of the Decision the hook computed (fail-CLOSED on
    INPUT, PLAN-152 C4).

    Reason strings are emitted verbatim from the guard (they are already
    operator-facing) — the shim, not this function, owns the exit code.
    """
    allow = decision.allow
    reason = decision.reason or ""

    coherence = coherence_error(event)
    if coherence:
        allow = False
        reason = "[grok-host coherence gate] " + coherence + (
            " | " + reason if reason else ""
        )

    out: Dict[str, Any] = {"decision": "allow" if allow else "deny"}
    if not allow:
        out["reason"] = reason or "blocked by governance hook"

    # Grok ignores unknown top-level keys on PreToolUse; carry the
    # operator-facing extras that our own transcript tooling reads, but
    # NEVER a second decision-shaped key (a `block` here would be the
    # very malformed-output class this adapter exists to prevent).
    if decision.system_message:
        out.setdefault("systemMessage", decision.system_message)
    if decision.message:
        out.setdefault("message", decision.message)
    for k, v in decision.extra.items():
        if k in ("decision", "reason", "hookEventName"):
            continue
        if k not in out:
            out[k] = v
    return json.dumps(out, ensure_ascii=False)


def emit_decision(
    decision: _contract.Decision,
    stream: "Optional[IO[str]]" = None,
    event: Any = None,
) -> None:
    """Convenience: write decision + newline. SPEC §3.4.

    The shim (``_python-hook.sh``) reads this stdout and maps an emitted
    deny to **exit 2** (the PLAN-156 exit-ABI amendment). Emitting the
    decision is sufficient for grok to block (probe P2) — the exit code
    is belt-and-suspenders for hosts that key on it (Codex PreToolUse,
    and grok itself if a future 0.x tightens the rule back to the
    docs.x.ai wording).
    """
    if stream is None:
        stream = sys.stdout
    stream.write(write_decision(decision, event=event) + "\n")


def is_blocking_event(event: Any) -> bool:
    """True when a deny on this event actually stops the tool call.

    Honest-labeling helper for the capability matrix + transcripts: on
    grok ONLY ``pre_tool_use`` blocks. Stop / SubagentStart / everything
    else is passive, so a deny there is ADVISORY by construction and the
    docs must say so (PLAN-156 §Honest limitations).
    """
    phase = getattr(event, "phase", "") or ""
    return phase in BLOCKING_EVENTS
