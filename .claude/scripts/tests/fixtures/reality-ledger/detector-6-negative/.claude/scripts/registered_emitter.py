"""Fixture: emits an action that IS registered in fixture _KNOWN_ACTIONS."""

from __future__ import annotations


def emit_ok() -> None:
    from _lib import audit_emit  # type: ignore[import-not-found]
    audit_emit.emit_generic(action="agent_spawn", subagent_type="qa")
