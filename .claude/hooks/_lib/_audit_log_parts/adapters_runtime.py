"""Host adapter and hook entry-point declarations."""
from __future__ import annotations

def _codex_tool_enum(tool_name: str) -> str:
    """Map a normalized codex tool name to the closed audit enum. Never raises."""
    if not isinstance(tool_name, str) or not tool_name:
        return "other"
    if tool_name.startswith("mcp__"):
        return "mcp_other"
    return tool_name


def _codex_audit_main(t0: float) -> int:
    """Codex host-wire audit append (PLAN-155 Wave 4). Exits 0 on every path.

    Reads the codex host envelope via the codex adapter and appends the
    matching metadata-only action to the shared HMAC chain through
    `_lib.audit_emit`. Fail-open per SPEC/v1 §4 — the audit hook is
    observability, not an enforcement gate, so an unresolved adapter / parse
    error / import failure breadcrumbs and returns 0 (the completeness bound is
    already the named residual; a security matcher would fail CLOSED instead,
    but this is not one).
    """
    try:
        from _lib.adapters import codex as _codex_adapter
        from _lib import audit_emit as _audit_emit
    except Exception as e:  # pragma: no cover — infrastructure import failure
        try:
            write_breadcrumb(
                audit_paths()["err"],
                f"codex audit import failed (fail-open): {type(e).__name__}",
            )
        except Exception:
            pass
        return 0

    try:
        event = _codex_adapter.read_post_event()
    except Exception as e:  # pragma: no cover — adapter never raises by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"codex read_post_event raised (fail-open): {type(e).__name__}",
        )
        return 0

    if getattr(event, "parse_error", None):
        write_breadcrumb(
            audit_paths()["err"],
            f"codex stdin parse error: {event.parse_error}",
        )
        return 0

    # The codex wire's event name WINS over the phase arg (host adapter sets
    # NormalizedEvent.phase = hook_event_name). raw_payload carries the raw
    # codex scalars (stop_hook_active, etc.).
    hook_event = str(getattr(event, "phase", "") or "")
    raw_payload = getattr(event, "raw_payload", {}) or {}
    session_id = str(getattr(event, "session_id", "") or "")
    project_dir = str(getattr(event, "project", "") or "") or (
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )

    try:
        if hook_event == "PostToolUse":
            tool_enum = _codex_tool_enum(str(getattr(event, "tool_name", "") or ""))
            _audit_emit.emit_codex_tool_recorded(
                session_id=session_id,
                tool_name_enum=tool_enum,
                hook_event_name="PostToolUse",
                project=project_dir,
            )
        elif hook_event in ("Stop", "SubagentStop"):
            # source: derive from the event, unless the headless wrapper
            # overrode it (CEO_CODEX_TURN_SOURCE) to mark a wrapper bracket.
            derived = "subagent_stop" if hook_event == "SubagentStop" else "stop"
            source = os.environ.get("CEO_CODEX_TURN_SOURCE") or derived
            stop_active = bool(raw_payload.get("stop_hook_active"))
            _audit_emit.emit_codex_turn_ended(
                session_id=session_id,
                source=source,
                stop_hook_active=stop_active,
                project=project_dir,
            )
        elif hook_event == "SessionStart":
            # Boot bracket — only reached when the wrapper pipes a SessionStart
            # envelope here (production routes SessionStart -> SessionStart.py).
            emit_ss = getattr(_audit_emit, "emit_session_start", None)
            if emit_ss is not None:
                emit_ss(session_id=session_id, project=project_dir)
        # else: UserPromptSubmit / SubagentStart / PreToolUse are not this
        # hook's job under codex — return 0 (no append).
    except Exception as e:  # pragma: no cover — emit is fail-open by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"codex audit emit failed (fail-open): {type(e).__name__}",
        )
    return 0


def _grok_tool_enum(tool_name: str) -> str:
    """Map a normalized grok tool name to the closed audit enum. Never raises.

    The grok adapter has already aliased run_terminal_command -> Bash,
    search_replace -> Edit, spawn_subagent -> Task, etc. before we see the
    event; here we only fold mcp__* down to `mcp_other` (MF-SEC-1) and leave
    the emitter to coerce any residual miss to `other`.
    """
    if not isinstance(tool_name, str) or not tool_name:
        return "other"
    if tool_name.startswith("mcp__"):
        return "mcp_other"
    return tool_name


def _grok_audit_main(t0: float) -> int:
    """Grok host-wire audit append (PLAN-156 Wave 4). Exits 0 on every path.

    Mirror of `_codex_audit_main`: reads the grok host envelope via the grok
    adapter and appends the matching metadata-only action to the shared HMAC
    chain through `_lib.audit_emit`. Fail-open per SPEC/v1 §4 — the audit hook
    is observability, not enforcement, so an unresolved adapter / parse error
    / import failure breadcrumbs and returns 0.

    Grok specifics: PostToolUse is passive (a deny cannot block), but the
    append still lands. SessionEnd is unreliable in headless runs, so
    turn-ended accounting hangs off Stop / SubagentStop (completeness caveat,
    ADR-162).
    """
    try:
        from _lib.adapters import grok as _grok_adapter
        from _lib import audit_emit as _audit_emit
    except Exception as e:  # pragma: no cover — infrastructure import failure
        try:
            write_breadcrumb(
                audit_paths()["err"],
                f"grok audit import failed (fail-open): {type(e).__name__}",
            )
        except Exception:
            pass
        return 0

    try:
        event = _grok_adapter.read_post_event()
    except Exception as e:  # pragma: no cover — adapter never raises by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"grok read_post_event raised (fail-open): {type(e).__name__}",
        )
        return 0

    if getattr(event, "parse_error", None):
        write_breadcrumb(
            audit_paths()["err"],
            f"grok stdin parse error: {event.parse_error}",
        )
        return 0

    hook_event = str(getattr(event, "phase", "") or "")
    session_id = str(getattr(event, "session_id", "") or "")
    project_dir = str(getattr(event, "project", "") or "") or (
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )

    try:
        if hook_event == "PostToolUse":
            tool_enum = _grok_tool_enum(str(getattr(event, "tool_name", "") or ""))
            _audit_emit.emit_grok_tool_recorded(
                session_id=session_id,
                tool_name_enum=tool_enum,
                hook_event_name="PostToolUse",
                project=project_dir,
            )
        elif hook_event in ("Stop", "SubagentStop"):
            derived = "subagent_stop" if hook_event == "SubagentStop" else "stop"
            source = os.environ.get("CEO_GROK_TURN_SOURCE") or derived
            _audit_emit.emit_grok_turn_ended(
                session_id=session_id,
                source=source,
                project=project_dir,
            )
        # else: SessionStart / UserPromptSubmit / SubagentStart / PreToolUse
        # are not this hook's job under grok — return 0 (no append).
    except Exception as e:  # pragma: no cover — emit is fail-open by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"grok audit emit failed (fail-open): {type(e).__name__}",
        )
    return 0


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------


def main() -> int:
    """PostToolUse hook entry point.

    PLAN-006 Phase 1 final migration (ADR-014): uses
    `claude_adapter.read_post_event()` with explicit PostToolUse phase
    (R-SB1 fix). Reads stdin, extracts fields, redacts, writes one
    JSONL line to the audit log under lock. Silent on stdout. Exits 0
    on all paths (fail-open governance contract).

    PLAN-155 Wave 4: under CEO_HOOK_ADAPTER=codex the codex host-wire path
    (`_codex_audit_main`) handles the append via `_lib.audit_emit`; the claude
    path below is byte-identical when the env var is unset/`claude`.
    """
    t0 = time.monotonic()
    _adapter = os.environ.get("CEO_HOOK_ADAPTER")
    if _adapter == "codex":
        return _codex_audit_main(t0)
    if _adapter == "grok":
        return _grok_audit_main(t0)
    try:
        event = _claude_adapter.read_post_event()
        if event.parse_error:
            paths = audit_paths()
            write_breadcrumb(
                paths["err"],
                f"stdin parse error: {event.parse_error}",
            )
            return 0

        # Filter: only care about Agent spawns
        if event.tool_name and event.tool_name not in ("Agent", "unknown"):
            return 0

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            project_dir = str(Path(project_dir).resolve())
        except OSError:
            pass

        duration_ms = int((time.monotonic() - t0) * 1000)
        entry = build_entry(
            event=event, project_dir=project_dir, hook_duration_ms=duration_ms
        )
        if entry is None:
            return 0

        paths = audit_paths()
        append_entry(
            entry,
            paths=paths,
            threshold_bytes=rotate_threshold(),
        )
        return 0
    except Exception as e:  # pragma: no cover — catastrophic
        try:
            paths = audit_paths()
            write_breadcrumb(paths["err"], f"fatal: {e.__class__.__name__}: {e}")
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
