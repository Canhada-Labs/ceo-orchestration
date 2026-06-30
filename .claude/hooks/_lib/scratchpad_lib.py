"""Shared scratchpad library — plan-scoped K/V for inter-agent handoff.

PLAN-011 Phase 7. Consumes Phase 0's :class:`SqliteStateStore`
(ADR-027) and adds two thin responsibilities on top:

1. **Plan-id derivation (consensus M2)** — the plan a scratchpad call
   belongs to is resolved from ``audit-log.jsonl`` via the current
   session's most recent ``plan_transition`` event. It is **never**
   taken from an env var (env vars are trivially spoofable by malicious
   agent output that manages to run ``export CEO_CURRENT_PLAN=PLAN-X``
   before a hook fires). If derivation fails, callers get
   :class:`PlanIdDerivationError` — we refuse to guess.

2. **Rollback clear (consensus M2)** — when a plan rolls back from
   ``executing`` to ``draft``, scratchpad keys for that plan are zeroed
   out via :meth:`SqliteStateStore.clear_plan`. The actual wiring into
   ``plan_transition`` events ships in Sprint 11+ (this library exposes
   the primitive).

## Public API

    from _lib.scratchpad_lib import (
        resolve_plan_id,
        open_scratchpad,
        clear_on_rollback,
        PlanIdDerivationError,
    )

    plan_id = resolve_plan_id()                      # raises if unresolvable
    with open_scratchpad() as pad:
        pad.set("phase-1-complete", "true", ttl_seconds=86400)
        v = pad.get("phase-1-complete")              # -> b"true"

    # plan rollback path
    cleared = clear_on_rollback("PLAN-011", "executing", "draft")

## Invariants (carried over from state_store)

- **Plan isolation** — a scratchpad for ``PLAN-011`` cannot see or
  touch ``PLAN-010`` keys (filesystem boundary).
- **64 KiB per-key cap** — inherited default from state_store
  (``DEFAULT_VALUE_MAX_BYTES``). Over-cap writes raise
  ``StateStoreValueTooLarge``.
- **Redacted strings** — str values pass through ``redact_secrets``
  before write (bytes values are trusted; caller asserted they know).
- **Audit-logged** — every set/get/clear emits a typed event. See
  SPEC/v1/state-stores.schema.md.

## Fail mode

Plan-id derivation either succeeds or raises. The library never falls
back silently. Callers (CLI, hooks) translate the exception into a
human-readable message + non-zero exit.

Audit emission *inside* the underlying state_store is fail-open per
ADR-005. This library does not add new fail-open paths.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_emit as _audit_emit  # noqa: E402
from _lib.state_store import (  # noqa: E402
    DEFAULT_VALUE_MAX_BYTES,
    SqliteStateStore,
    open_store,
)


# Scratchpad is a single logical store on the shared backend.
SCRATCHPAD_STORE_NAME = "scratchpad"


class PlanIdDerivationError(RuntimeError):
    """Raised when we cannot derive a plan-id from the current session.

    Callers should surface the message and exit non-zero. Falling back
    to an env var is **forbidden** — consensus M2 treats env vars as
    untrusted because an agent with subshell execution can set them.
    """


def _resolve_session_id(session_id: Optional[str]) -> str:
    """Return the effective session id, checking CLAUDE_SESSION_ID if arg is None.

    Empty / whitespace-only values are treated as missing.
    """
    if session_id is not None:
        val = str(session_id).strip()
        return val
    env_val = os.environ.get("CLAUDE_SESSION_ID", "")
    return env_val.strip()


def resolve_plan_id(session_id: Optional[str] = None) -> str:
    """Return the PLAN-NNN currently scoped to the given session.

    Scans ``audit-log.jsonl`` (via :func:`audit_emit.iter_events`) for
    ``plan_transition`` events whose ``session_id`` matches the argument
    (or ``CLAUDE_SESSION_ID`` env var if the argument is None). Returns
    the ``plan_id`` of the MOST RECENT matching event.

    Args:
        session_id: explicit session id; if None, pulled from env.

    Returns:
        The canonical ``PLAN-NNN`` string.

    Raises:
        PlanIdDerivationError: when no session id is available, when
            the audit log is empty or missing, or when no
            ``plan_transition`` event for the session exists.

    Notes:
        - **No env-var fallback.** Consensus M2 forbids deriving plan
          id from ``CEO_CURRENT_PLAN`` or similar — those are
          agent-spoofable.
        - "Most recent" is *log order*: the last matching event in
          linear file order wins. Timestamps are not re-sorted because
          audit-log writes are ordered by the shared filelock, and
          re-sorting by ts can tie-break wrong on same-second events.
        - A completed-plan session (``to_status=done``) still resolves
          to that plan; scratchpad clear is an explicit call, not an
          implicit consequence of a terminal transition.
    """
    sid = _resolve_session_id(session_id)
    if not sid:
        raise PlanIdDerivationError(
            "cannot derive plan_id: no session_id provided and "
            "CLAUDE_SESSION_ID env var is unset. Ensure the hook/CLI "
            "is running in a Claude Code session with a live session id."
        )

    last_plan_id: Optional[str] = None
    seen_any_transition = False
    for event in _audit_emit.iter_events(action_filter="plan_transition"):
        seen_any_transition = True
        event_sid = str(event.get("session_id") or "")
        if event_sid != sid:
            continue
        pid = event.get("plan_id")
        if isinstance(pid, str) and pid:
            last_plan_id = pid

    if last_plan_id is None:
        if not seen_any_transition:
            raise PlanIdDerivationError(
                f"cannot derive plan_id: no plan_transition events in "
                f"audit-log for session {sid!r}. Is the audit log empty "
                f"or pointed at the wrong path (CEO_AUDIT_LOG_PATH)?"
            )
        raise PlanIdDerivationError(
            f"cannot derive plan_id: audit-log has plan_transition "
            f"events but none for session {sid!r}. The session may not "
            f"have transitioned a plan yet."
        )
    return last_plan_id


def open_scratchpad(
    plan_id: Optional[str] = None,
    *,
    value_max_bytes: int = DEFAULT_VALUE_MAX_BYTES,
) -> SqliteStateStore:
    """Open a :class:`SqliteStateStore` for the scratchpad surface.

    Args:
        plan_id: explicit PLAN-NNN; if None, derived from the current
            session via :func:`resolve_plan_id`.
        value_max_bytes: per-key cap (default inherited from
            state_store; 64 KiB).

    Returns:
        An unopened store handle. Use as a context manager (``with``)
        or call ``close()`` explicitly.

    Raises:
        PlanIdDerivationError: when plan_id is None and derivation fails.
        StateStoreInvalidName: when plan_id is malformed.
    """
    resolved = plan_id if plan_id is not None else resolve_plan_id()
    return open_store(
        SCRATCHPAD_STORE_NAME,
        resolved,
        value_max_bytes=value_max_bytes,
    )


def clear_on_rollback(plan_id: str, from_status: str, to_status: str) -> int:
    """Clear scratchpad keys when a plan rolls back ``executing → draft``.

    Any transition that is NOT ``executing → draft`` is a no-op and
    returns 0. This is deliberate — completed (``executing → done``)
    and abandoned (``… → abandoned``) plans keep their scratchpad for
    post-mortem; only an actual rollback zeroes state.

    Args:
        plan_id: PLAN-NNN string.
        from_status: originating plan status (e.g. ``executing``).
        to_status: target plan status (e.g. ``draft``).

    Returns:
        The number of keys cleared (0 when transition does not match).
    """
    if from_status != "executing" or to_status != "draft":
        return 0
    with open_store(SCRATCHPAD_STORE_NAME, plan_id) as store:
        return store.clear_plan()


__all__ = [
    "PlanIdDerivationError",
    "SCRATCHPAD_STORE_NAME",
    "clear_on_rollback",
    "open_scratchpad",
    "resolve_plan_id",
]
