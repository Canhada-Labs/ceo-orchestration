"""Fixture audit_emit.py — _KNOWN_ACTIONS does NOT include the phantom."""

_KNOWN_ACTIONS = {
    "agent_spawn",
    "debate_event",
    "skill_bootstrap_used",  # historical Codex S76 precedent (registered)
}


def emit_generic(action: str, **kwargs) -> None:
    if action not in _KNOWN_ACTIONS:
        return  # silent drop — exactly what reality-ledger detects
