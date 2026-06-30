"""PLAN-090 Wave A — persona × primitive routing policy.

Tracks the post-AMEND-1 default mode (`advisory|enforcing|disabled`) for
each (persona, primitive) cell in the 4 × 13 god-mode matrix. Consumed
by spawn-hook callsites (and future per-primitive enforcement gates) to
decide whether to BLOCK a contradicting decision (`enforcing`) or merely
OBSERVE and `audit emit` it (`advisory`).

Public API:

- ``get_mode(persona, primitive) -> "advisory" | "enforcing" | "disabled"``
- ``is_enforcing(persona, primitive) -> bool``
- ``is_killswitch_active() -> bool``  (emits ``kill_switch_invoked`` once per
  session when ARMED)
- ``maybe_emit_phase_c_flipped() -> bool``  (one-shot per session via
  marker file; pre-flip emit so a crash mid-flip preserves audit trail)
- ``known_personas() -> Tuple[str, ...]``
- ``known_primitives() -> Tuple[str, ...]``

Per ADR-118-AMEND-1 §3 the kill-switch fires ONLY on EXACT MATCH
``CEO_GODMODE_ENFORCING=0`` — any other value (``=false``, ``=no``,
``=""``, ``=FALSE``, ``=``, unset, ``=1``) keeps ENFORCING active.

Stdlib only. Fail-soft on every audit-emit consult (no infrastructure
bug can block the user session).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------
# 13 canonical primitives + 4 personas (PLAN-088 W5 fixture topology).
# ---------------------------------------------------------------------

_PERSONAS: Tuple[str, ...] = (
    "vibecoder",
    "junior_dev",
    "skeptical_cto",
    "team_member",
)

_AUTO_PRIMITIVES: Tuple[str, ...] = (
    "AUTO-01", "AUTO-02", "AUTO-03", "AUTO-04", "AUTO-05",
    "AUTO-06", "AUTO-07", "AUTO-08", "AUTO-09", "AUTO-10",
)
_SEMI_PRIMITIVES: Tuple[str, ...] = ("SEMI-11", "SEMI-12", "SEMI-13")
_PRIMITIVES: Tuple[str, ...] = _AUTO_PRIMITIVES + _SEMI_PRIMITIVES


# Per-primitive default mode (uniform across personas; per-persona
# overrides held empty for v1.24.0 and deferred to PLAN-094+ once
# 5-repo soak surfaces friction patterns).
#
# Wave A.3b (LAST sub-wave in Wave A) flipped AUTO-01..AUTO-10 to
# ``enforcing`` here. SEMI-11..SEMI-13 stay ADVISORY per ADR-118-AMEND-1
# §2 (SEMI = user-confirm class; flipping would invert the contract).
#
# Kill-switch ``CEO_GODMODE_ENFORCING=0`` (EXACT MATCH) overrides this
# back to ADVISORY at consult time — see ``is_killswitch_active`` /
# ``get_mode`` below.
_PRIMITIVE_DEFAULT_MODE: Dict[str, str] = {
    "AUTO-01": "enforcing",  # cache_discipline_alerted
    "AUTO-02": "enforcing",  # first_run_wizard_dispatched
    "AUTO-03": "enforcing",  # estimate_calibrator_pipeline_run
    "AUTO-04": "enforcing",  # tier_policy_misrouting_advised
    "AUTO-05": "enforcing",  # model_routing_advised
    "AUTO-06": "enforcing",  # mcp_route_advised
    "AUTO-07": "enforcing",  # pair_rail_phase_advanced
    "AUTO-08": "enforcing",  # batch_dispatched
    "AUTO-09": "enforcing",  # thinking_budget_set
    "AUTO-10": "enforcing",  # specialization_promoted (signal discriminator)
    "SEMI-11": "advisory",   # cookbook_pattern_advised
    "SEMI-12": "advisory",   # SOTA research (deferred to PLAN-092)
    "SEMI-13": "advisory",   # subagent_findings_partial_drop family
}


# Per-persona override map. Currently empty (uniform per-primitive).
# Keys are (persona, primitive) tuples; values override
# ``_PRIMITIVE_DEFAULT_MODE`` for that one cell.
_PERSONA_OVERRIDES: Dict[Tuple[str, str], str] = {}


_KILL_SWITCH_ENV = "CEO_GODMODE_ENFORCING"
_KILL_SWITCH_ARMED_VALUE = "0"  # EXACT MATCH per ADR-118-AMEND-1 §3
_PHASE_C_MARKER_NAME = "phase_c_seen.marker"


# ---------------------------------------------------------------------
# Session-scoped state for one-shot audit emits.
# ---------------------------------------------------------------------
#
# Both flags are RESET on module-reload (per-test isolation via
# ``importlib.reload`` if a test needs to exercise the one-shot gate
# twice). Production code never reloads the module within a single
# session, so the in-memory gate is sufficient.

_killswitch_emitted_this_session: bool = False


# ---------------------------------------------------------------------
# Public surface.
# ---------------------------------------------------------------------


def known_personas() -> Tuple[str, ...]:
    """Return the 4 canonical persona ids in stable order."""
    return _PERSONAS


def known_primitives() -> Tuple[str, ...]:
    """Return the 13 canonical primitive ids in stable order."""
    return _PRIMITIVES


def is_killswitch_active() -> bool:
    """Return True iff ``CEO_GODMODE_ENFORCING=0`` is set in the parent shell.

    Side effect (idempotent within session): when the kill-switch is
    ARMED, emit a single ``kill_switch_invoked`` audit event for the
    session (FPR-budget tracking per R1 TDE P0 fold).
    """
    global _killswitch_emitted_this_session
    raw = os.environ.get(_KILL_SWITCH_ENV)
    armed = raw == _KILL_SWITCH_ARMED_VALUE
    if armed and not _killswitch_emitted_this_session:
        _killswitch_emitted_this_session = True
        try:
            from _lib import audit_emit
            audit_emit.emit_kill_switch_invoked(
                env_value=_KILL_SWITCH_ARMED_VALUE,
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
            )
        except Exception:  # noqa: BLE001 — fail-soft per CLAUDE.md
            pass
    return armed


def get_mode(persona: str, primitive: str) -> str:
    """Return the effective mode for (persona, primitive).

    Returns one of ``"advisory" | "enforcing" | "disabled"``.

    Unknown primitives → ``"disabled"`` (no enforcement on unknown
    surfaces). Unknown personas fall through to per-primitive defaults
    (no per-persona override yet).

    The kill-switch (``CEO_GODMODE_ENFORCING=0``) overrides BOTH
    per-primitive defaults AND per-persona overrides — any cell that
    would otherwise be ``enforcing`` falls back to ``advisory``.
    """
    if primitive not in _PRIMITIVE_DEFAULT_MODE:
        return "disabled"
    # Per-persona override (empty in v1.24.0).
    override = _PERSONA_OVERRIDES.get((persona, primitive))
    mode = override if override is not None else _PRIMITIVE_DEFAULT_MODE[primitive]
    if mode == "enforcing" and is_killswitch_active():
        return "advisory"
    return mode


def is_enforcing(persona: str, primitive: str) -> bool:
    """Convenience helper. Equivalent to ``get_mode(...) == "enforcing"``."""
    return get_mode(persona, primitive) == "enforcing"


# ---------------------------------------------------------------------
# Phase C migration emit (ADR-118-AMEND-1 §4).
# ---------------------------------------------------------------------


def _state_dir() -> Path:
    """Per-session marker directory under the audit-log home tree.

    Honors ``CEO_AUDIT_LOG_DIR`` (TestEnvContext isolation), then falls
    back to ``$HOME/.claude/projects/<project>/state/``.
    """
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        return Path(audit_dir) / "state"
    home = Path(os.environ.get("HOME") or Path.home())
    project = os.environ.get("CLAUDE_PROJECT_DIR", "ceo-orchestration")
    # Use the basename of the project as the directory leaf so we don't
    # collide across multiple installs on the same user.
    leaf = Path(project).name or "ceo-orchestration"
    return home / ".claude" / "projects" / leaf / "state"


def maybe_emit_phase_c_flipped() -> bool:
    """One-shot per-session emit of ``phase_c_enforcing_flipped``.

    Returns True if the emit fired (first-session marker absent),
    False otherwise (marker exists — emit already fired in a prior
    session OR the marker file was hand-rolled by an adopter migrating
    from a fork).

    Idempotency invariant: even a corrupt marker file (junk content,
    zero bytes, permissions blocked) counts as "phase C already seen"
    — we err on the side of NOT re-emitting because crash-mid-flip
    must preserve a single audit row, not amplify into duplicates.
    """
    state_dir = _state_dir()
    marker = state_dir / _PHASE_C_MARKER_NAME
    if marker.is_file():
        return False
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    # Pre-flip emit so a crash between emit and marker-write preserves
    # the audit row (R1 security-engineer P1 fold).
    try:
        from _lib import audit_emit
        audit_emit.emit_phase_c_enforcing_flipped(
            migration_phase="first_session",
            ts_unix=int(time.time()),
            session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # noqa: BLE001
        return False
    try:
        marker.write_text(str(int(time.time())), encoding="utf-8")
    except OSError:
        # Audit row already landed; failure to write the marker is
        # non-fatal but means we may re-emit on the next session. That
        # is recoverable; the duplicate is a known fail-soft cost.
        pass
    return True


__all__ = [
    "get_mode",
    "is_enforcing",
    "is_killswitch_active",
    "maybe_emit_phase_c_flipped",
    "known_personas",
    "known_primitives",
]
