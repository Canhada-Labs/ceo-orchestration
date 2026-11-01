from __future__ import annotations

__all__ = ('main',)

def main() -> int:
    """Hook entry point: read stdin, decide, write stdout, exit 0.

    PLAN-006 Phase 1 migration (ADR-014): Adapter Layer I/O.
    Fail-open on any exception.
    """
    try:
        if _SPAWN_COMPONENT_IMPORT_ERROR is not None:
            print("[check_agent_spawn] component import unavailable (" +
                  _SPAWN_COMPONENT_IMPORT_ERROR + ")", file=sys.stderr)
            _claude_adapter.emit_decision(_contract.allow())
            return 0
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_agent_spawn] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            names_regex = _team.load_names(project_dir)
        except Exception as e:  # pragma: no cover
            print(
                f"[check_agent_spawn] WARN: team load failed: {e}",
                file=sys.stderr,
            )
            names_regex = None

        decision = decide(
            description=event.description,
            prompt=event.prompt,
            names_regex=names_regex,
            subagent_type=event.subagent_type,
        )

        # Side-effect: emit veto_triggered event on block path (v2 stream).
        # Session 75 Codex re-pass: reason_code derived from decision.reason
        # via _classify_block_reason() so the audit trail correctly
        # discriminates secret_in_spawn_prompt / effort_token_in_spawn /
        # architect_role_not_delegable / veto_floor_demoted / etc.
        # Previously hardcoded "missing_skill_content" misclassified all blocks.
        if not decision.allow and _AUDIT_EMIT_AVAILABLE:
            try:
                _audit_emit.emit_veto_triggered(
                    hook="check_agent_spawn",
                    reason_code=_classify_block_reason(decision.reason or ""),
                    reason_preview=decision.reason or "",
                    blocked_tool="Agent",
                    project=project_dir,
                )
            except Exception:
                pass

        _claude_adapter.emit_decision(_to_contract_decision(decision))
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_agent_spawn] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0
