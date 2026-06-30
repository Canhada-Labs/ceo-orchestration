"""Fixture audit_emit.py — _KNOWN_ACTIONS DOES include the action."""

_KNOWN_ACTIONS = {
    "agent_spawn",
    "debate_event",
}


def emit_generic(action: str, **kwargs) -> None:
    if action not in _KNOWN_ACTIONS:
        return
