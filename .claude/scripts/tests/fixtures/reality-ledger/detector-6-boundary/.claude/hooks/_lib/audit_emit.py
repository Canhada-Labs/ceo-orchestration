"""Fixture audit_emit.py — minimal."""

_KNOWN_ACTIONS = {"agent_spawn"}


def emit_generic(action: str, **kwargs) -> None:
    if action not in _KNOWN_ACTIONS:
        return
