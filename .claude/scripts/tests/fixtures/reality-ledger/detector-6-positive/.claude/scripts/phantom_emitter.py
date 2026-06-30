"""Fixture: emits a phantom action 'fixture_phantom_action_xyz'.

Detector #6 must catch this when scanned against an _audit_emit.py
that does NOT register 'fixture_phantom_action_xyz' in _KNOWN_ACTIONS.
"""

from __future__ import annotations


def emit_phantom() -> None:
    # Late import for fixture isolation
    from _lib import audit_emit  # type: ignore[import-not-found]
    audit_emit.emit_generic(action="fixture_phantom_action_xyz", foo=1)
