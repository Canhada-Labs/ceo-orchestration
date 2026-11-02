"""Fail-open, per-session observability for explicitly disabled GuardFall rails.

The hook checks trusted switch values before calling :func:`disabled_once`.
This module receives only a closed switch *name*, never its environment value
or the rejected command. A marker written with O_EXCL arbitrates concurrent
hook processes; a crash after marker creation may lose telemetry, consistent
with the existing learning-rail breadcrumb contract.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional


_SWITCHES = frozenset({
    "CEO_BASH_INDIRECT_GUARD",
    "CEO_BASH_INDIRECT_HEURISTICS",
})
_MARKER_DIR = "bash-indirect-disabled"


def _marker_path(audit_dir: Path, session_id: str, switch: str) -> Path:
    """Opaque, bounded marker name; raw session bytes never become a path."""
    session_hash = hashlib.sha256(
        session_id.encode("utf-8", "replace")
    ).hexdigest()[:24]
    switch_tag = "guard" if switch == "CEO_BASH_INDIRECT_GUARD" else "heuristics"
    return audit_dir / _MARKER_DIR / (session_hash + "." + switch_tag)


def disabled_once(switch: str, session_id: Optional[str] = None) -> None:
    """Emit one ``learning_rail_disabled`` per session and recognized switch.

    Caller must invoke this ONLY when trusted configuration explicitly turns
    the rail off. Unset/default configuration must never reach this function.
    Missing session identity suppresses emission to avoid false deduplication
    across unrelated sessions. Every failure is deliberately fail-open.
    """
    if switch not in _SWITCHES:
        return
    try:
        sid = session_id if session_id is not None else os.environ.get("CLAUDE_SESSION_ID", "")
        if not isinstance(sid, str) or not sid:
            return
        # Import at call time: test suites and hooks may rebind the facade.
        from _lib import audit_emit

        audit_dir = audit_emit._log_family_dir()
        marker = _marker_path(audit_dir, sid, switch)
        marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            fd = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            return
        os.close(fd)
        audit_emit.emit_learning_rail_disabled(
            rail="bash_indirect",
            switch=switch,
            hook="check_bash_safety",
            session_id=sid,
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:
        # Telemetry failure must never alter the safety hook's decision.
        return
