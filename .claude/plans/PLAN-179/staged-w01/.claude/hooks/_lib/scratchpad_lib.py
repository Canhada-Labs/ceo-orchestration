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

3. **Session-scope fallback (PLAN-179 W1 US3, amendments r1-C1/r1-C2)** —
   when :func:`resolve_plan_id` refuses (the DOMINANT path measured in
   S309: 2 ``plan_transition`` events in 12.515 audit lines), the
   continuity write is no longer SKIPPED. It lands in a SEPARATE store
   (:data:`SESSION_SCRATCHPAD_STORE_NAME`) under a scope id of the form
   ``session-<uuid>``. Three things this deliberately does NOT do:
   it does not overload the ``plan_id`` field with a session value, it
   does not widen :func:`resolve_plan_id` (its refusal-to-guess is
   untouched), and it does not read ``CLAUDE_SESSION_ID`` — see
   :func:`session_id_from_event`.

## Public API

    from _lib.scratchpad_lib import (
        resolve_plan_id,
        open_scratchpad,
        clear_on_rollback,
        PlanIdDerivationError,
        # PLAN-179 W1 US3
        session_id_from_event,
        open_session_scratchpad,
        set_session_value,
        gc_orphan_session_stores,
        SESSION_SCOPE_TTL_SECONDS,
        SCOPE_KIND_PLAN,
        SCOPE_KIND_SESSION,
    )

    plan_id = resolve_plan_id()                      # raises if unresolvable
    with open_scratchpad() as pad:
        pad.set("phase-1-complete", "true", ttl_seconds=86400)
        v = pad.get("phase-1-complete")              # -> b"true"

    # plan rollback path
    cleared = clear_on_rollback("PLAN-011", "executing", "draft")

    # PLAN-179 session-scope fallback (only after resolve_plan_id raised)
    sid = session_id_from_event(hook_event)          # None => REFUSE fallback
    if sid is not None:
        with open_session_scratchpad(sid) as pad:
            set_session_value(pad, "snapshot", blob_json)   # TTL is mandatory

## Invariants (carried over from state_store)

- **Plan isolation** — a scratchpad for ``PLAN-011`` cannot see or
  touch ``PLAN-010`` keys (filesystem boundary). The session-scope
  fallback preserves this by construction: it is a DIFFERENT
  ``store_name``, i.e. a different directory, so a ``session-*`` scope
  is not merely an unusual plan_id inside the plan store — it never
  enters the plan store at all.
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

The session-scope fallback is EXPLICIT, never implicit: a caller has to
ask for it after catching :class:`PlanIdDerivationError`, and has to
have a session id that came from the hook input dict. The one helper
that IS fail-open is :func:`gc_orphan_session_stores` — housekeeping,
not correctness (ADR-005 shape).

Audit emission *inside* the underlying state_store is fail-open per
ADR-005. This library does not add new fail-open paths.
"""

from __future__ import annotations

import os
import re
import sys
import time
import zlib
from collections.abc import Mapping as _ABCMapping
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import audit_emit as _audit_emit  # noqa: E402
from _lib.state_store import (  # noqa: E402
    DEFAULT_VALUE_MAX_BYTES,
    SqliteStateStore,
    StateStoreInvalidName,
    open_store,
)

# PLAN-179 W1 US3 (r1-C2): the GC helper needs the SAME state root the
# stores are created under. Borrowing state_store's own accessor keeps ONE
# source of truth for the path convention — re-deriving it here would
# drift the day CEO_STATE_ROOT semantics change. Held as a module
# reference (not a `from ... import`) so the lookup stays late-bound.
from _lib import state_store as _state_store  # noqa: E402


# Scratchpad is a single logical store on the shared backend.
SCRATCHPAD_STORE_NAME = "scratchpad"

# PLAN-179 W1 US3 (amendment r1-C1): the session fallback lives in its
# OWN store, not in a funny-looking plan_id inside the plan store. The
# separate store_name IS the isolation mechanism — state_store maps
# store_name to a directory, so plan data and session data cannot see
# each other even in principle. Name must satisfy state_store's
# _validate_store_name: [A-Za-z0-9_-], <= 32 chars (this is 18).
SESSION_SCRATCHPAD_STORE_NAME = "scratchpad-session"

# Closed enum stamped into the stored blob so a reader can tell which
# scope produced a snapshot without inspecting the file path.
SCOPE_KIND_PLAN = "plan"
SCOPE_KIND_SESSION = "session"
_SCOPE_KINDS = (SCOPE_KIND_PLAN, SCOPE_KIND_SESSION)

# PLAN-179 W1 US3 (r1-C1): the ONLY accepted shape for a session scope
# id. Explicit, anchored, and deliberately narrow — hex + dashes only.
# Consequences that matter: "PLAN-179" cannot match (no `session-`
# prefix), "../escape" cannot match (no `.` or `/` in the class), and
# nothing that reaches the filesystem can contain a path separator.
_SESSION_SCOPE_ID_RE = re.compile(r"^session-[0-9a-fA-F-]{8,60}$")

# PLAN-179 W1 US3 (amendment r1-C2): session-scope writes are ALWAYS
# TTL'd. 72h = long enough to survive a weekend of compactions in one
# session lineage, short enough that an abandoned session's snapshot is
# not still on disk next sprint. Plan-scope writes keep their existing
# caller-chosen TTL semantics; this constant is session-scope only.
SESSION_SCOPE_TTL_SECONDS = 259200  # 72h

# Ceiling on unlinks per GC invocation (r1-C2). A hook runs GC inline,
# so the work has to be bounded regardless of how much junk accumulated;
# the leftovers are collected by the next run.
MAX_GC_FILES_PER_RUN = 64

# PLAN-179 rail round-4 [P2]: the sweep is bounded by TIME, not by a slice of
# the directory — a slice starves whatever sits behind it. 0.25s is a small
# fraction of the hook's 5s registration timeout, and the sweep is fail-open,
# so exceeding it costs nothing but a later reclaim.
_GC_WALL_BUDGET_S = 0.25

# Suffixes state_store creates per scope. The db and its filelock sibling
# are the obvious two; ``-wal`` / ``-shm`` are created by sqlite because
# _ensure_open sets ``PRAGMA journal_mode=WAL`` (state_store.py), and were
# OBSERVED on disk while verifying this change. Omitting them would leave
# two orphan files per session behind — the exact unbounded accumulation
# r1-C2 exists to stop.
_SESSION_STORE_SUFFIXES = (
    ".sqlite",
    ".sqlite.lock",
    ".sqlite-wal",
    ".sqlite-shm",
)


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
        - **PLAN-179 W1 US3 leaves this function unchanged.** The
          session-scope fallback is a NEW path taken by the CALLER after
          this raises — it is not a loosening of the refusal here. This
          function still never guesses a plan id and still never accepts
          one from the environment.
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


# --- session-scope fallback (PLAN-179 W1 US3, r1-C1 + r1-C2) -------------


def session_id_from_event(event: Optional[Mapping[str, Any]]) -> Optional[str]:
    """Return the session id carried by a hook INPUT dict, or None.

    PLAN-179 amendment r1-C1 — the refusal. This reads the hook event and
    NOTHING else. In particular it never consults
    ``os.environ['CLAUDE_SESSION_ID']``, and it is deliberately NOT
    routed through :func:`_resolve_session_id` (which does read the env
    as a convenience for the plan path).

    Why: an env var is agent-spoofable. Any agent that can run a subshell
    can ``export CLAUDE_SESSION_ID=<other-session>`` before a hook fires
    and steer the continuity write into a scope it chose — the same
    threat consensus M2 cited when it banned ``CEO_CURRENT_PLAN``. The
    hook input dict is supplied by the harness on stdin and is not
    writable from inside the agent's shell, so it is the only acceptable
    source here.

    The contract for callers is therefore: **None means REFUSE the
    fallback**, not "go look somewhere else". A caller that reacts to
    None by reading the env has reintroduced the spoof.

    Args:
        event: parsed hook input. Accepts both the snake_case
            (``session_id``) and camelCase (``sessionId``) spellings the
            harness has used, matching the continuity hooks.

    Returns:
        The stripped session id, or None when absent / blank / not a
        string / not a mapping.
    """
    # isinstance against collections.abc (typing.Mapping is annotation-only
    # in the idiom this repo targets: py>=3.9, stdlib-only).
    if not isinstance(event, _ABCMapping):
        return None
    for field in ("session_id", "sessionId"):
        raw = event.get(field)
        if isinstance(raw, str):
            val = raw.strip()
            if val:
                return val
    return None


def session_scope_id(session_id: str) -> str:
    """Build and validate the ``session-<uuid>`` scope id (r1-C1).

    This is the ONLY place a session id becomes a filesystem-facing
    identifier. Validation is explicit rather than inherited from
    state_store's ``_validate_plan_id``: that validator allows ``.`` and
    would happily accept ``PLAN-179`` — neither is acceptable for a
    scope that must be unmistakably session-shaped.

    Args:
        session_id: raw session id (already sourced from the hook input
            via :func:`session_id_from_event`).

    Returns:
        The scope id, e.g. ``session-9f1c0f6e-...``.

    Raises:
        StateStoreInvalidName: when the resulting id does not match
            :data:`_SESSION_SCOPE_ID_RE`.
    """
    raw = str(session_id or "").strip()
    scope = raw if raw.startswith("session-") else "session-" + raw
    if not _SESSION_SCOPE_ID_RE.match(scope):
        raise StateStoreInvalidName(
            "session scope id %r is not of the form session-<uuid> "
            "(allowed after the prefix: [0-9a-fA-F-]{8,60})" % scope
        )
    return scope


def open_session_scratchpad(
    session_id: str,
    *,
    value_max_bytes: int = DEFAULT_VALUE_MAX_BYTES,
) -> SqliteStateStore:
    """Open the SESSION-scoped scratchpad store (r1-C1).

    Returns the same handle type :func:`open_store` returns, so callers
    use it exactly like :func:`open_scratchpad` (``with`` block, then
    ``set`` / ``get``). The difference is invisible at the call site and
    total on disk: a different ``store_name`` means a different
    directory, so this write can never collide with, shadow, or leak
    into any plan's scratchpad.

    The ``session-<uuid>`` value is passed as the store's SCOPE id, which
    state_store happens to call ``plan_id`` in its own signature. That is
    a positional-argument name inside another module, not a claim that
    this is a plan: no plan store is ever opened with a ``session-*``
    value, and no ``plan_id`` field in the blob or in any audit event is
    overloaded with it (see :func:`stamp_scope_kind`).

    Args:
        session_id: session id sourced from the hook input dict.
        value_max_bytes: per-key cap (default 64 KiB, as for plan scope).

    Returns:
        An unopened :class:`SqliteStateStore` handle.

    Raises:
        StateStoreInvalidName: when ``session_id`` does not produce a
            valid ``session-<uuid>`` scope id.
    """
    scope = session_scope_id(session_id)
    return open_store(
        SESSION_SCRATCHPAD_STORE_NAME,
        scope,
        value_max_bytes=value_max_bytes,
    )


def stamp_scope_kind(blob: Dict[str, Any], scope_kind: str) -> Dict[str, Any]:
    """Stamp ``scope_kind`` into a snapshot blob before it is stored (r1-C1).

    The stored blob carries which scope produced it so the PostCompact
    reader can report honestly ("this came from the session fallback,
    there was no resolved plan") instead of inferring it from where the
    file happened to be.

    Args:
        blob: the snapshot dict, mutated in place and returned.
        scope_kind: one of :data:`SCOPE_KIND_PLAN` /
            :data:`SCOPE_KIND_SESSION` — a closed enum, like every other
            governance-visible field in this family.

    Returns:
        The same dict, with ``scope_kind`` set.

    Raises:
        ValueError: when ``scope_kind`` is outside the enum.
    """
    if scope_kind not in _SCOPE_KINDS:
        raise ValueError(
            "scope_kind must be one of %r, got %r" % (list(_SCOPE_KINDS), scope_kind)
        )
    blob["scope_kind"] = scope_kind
    return blob


def set_session_value(
    store: SqliteStateStore,
    key: str,
    value: Union[str, bytes],
    ttl_seconds: int = SESSION_SCOPE_TTL_SECONDS,
) -> None:
    """Write into a session-scoped store with a MANDATORY positive TTL (r1-C2).

    ``SqliteStateStore.set`` defaults ``ttl_seconds`` to None (no
    expiry), which for the plan scope is correct — a plan's scratchpad
    outlives a session on purpose. For the session scope it is the bug
    r1-C2 named: unbounded accumulation of one store per session, in
    ``$HOME``, outside the repo, that nothing ever reclaims. Routing
    session writes through this helper makes the TTL mechanical rather
    than a thing every caller must remember.

    Args:
        store: an open handle from :func:`open_session_scratchpad`.
        key: scratchpad key.
        value: str (redacted by state_store) or bytes (trusted).
        ttl_seconds: positive seconds-from-now; defaults to 72h.

    Raises:
        ValueError: when ``ttl_seconds`` is None or non-positive.
    """
    if ttl_seconds is None or int(ttl_seconds) <= 0:
        raise ValueError(
            "session-scope writes require an explicit positive ttl_seconds "
            "(PLAN-179 r1-C2), got %r" % (ttl_seconds,)
        )
    store.set(key, value, ttl_seconds=int(ttl_seconds))


# PLAN-179 rail round-5 [P2] — cobertura GARANTIDA sem cursor persistido.
# As quatro tentativas anteriores definiam a fatia do turno por POSICAO na
# iteracao (prefixo, offset, deadline), e toda fatia por posicao deixa uma
# cauda inalcancavel. Esta define por IDENTIDADE: o shard sai do nome do
# arquivo. Em K turnos cada arquivo cai na sua fatia exatamente uma vez, e o
# trabalho caro (stat) por turno e ~n/K. Ler nomes com scandir e barato.
_GC_SHARDS = 8


def _gc_shard_of_name(name):
    """Shard estavel derivado do NOME (nunca da ordem de leitura)."""
    try:
        return zlib.crc32(name.encode("utf-8", "replace")) % _GC_SHARDS
    except Exception:
        return 0


def _gc_shard_of_turn():
    """Fatia deste turno. Avanca a cada 60s, entao K turnos cobrem tudo."""
    try:
        return int(time.time() // 60) % _GC_SHARDS
    except Exception:
        return 0

def gc_orphan_session_stores(
    *,
    ttl_seconds: int = SESSION_SCOPE_TTL_SECONDS,
    max_files: int = MAX_GC_FILES_PER_RUN,
    now: Optional[float] = None,
) -> int:
    """Unlink aged-out session store FILES. Bounded, fail-open (r1-C2).

    ``prune_expired`` deletes expired ROWS; it cannot delete the file
    that holds them, so a TTL alone still leaves one empty
    ``session-<uuid>.sqlite`` per session forever. This collects the
    files themselves.

    A file is collectable when its mtime is older than ``ttl_seconds``:
    since every session write carries the same TTL, an untouched store
    past that age holds nothing but expired rows.

    Safety: only the session store directory is scanned, and only names
    whose stem matches :data:`_SESSION_SCOPE_ID_RE` with a known suffix
    are unlinked — an unrelated file dropped in that directory is left
    alone rather than deleted by a loose glob.

    Fail mode: fail-OPEN. This is housekeeping, not correctness (ADR-005
    shape). Any :class:`OSError` — missing dir, unreadable entry, racing
    unlink, read-only filesystem — ends or skips the sweep and returns
    the count achieved so far; it never propagates into the hook.

    Args:
        ttl_seconds: age threshold in seconds (default 72h).
        max_files: hard ceiling on unlinks this run.
        now: epoch seconds override for tests; defaults to wall clock.

    Returns:
        Number of files unlinked (0 when the directory does not exist).
    """
    removed = 0
    try:
        store_dir = _state_store._state_root() / SESSION_SCRATCHPAD_STORE_NAME
        if not store_dir.is_dir():
            return 0
        cutoff = (time.time() if now is None else float(now)) - float(ttl_seconds)
        # PLAN-179 rail rounds 2/3/4 [P2] — three attempts, and only this one
        # is right. The history is the point:
        #   r2: `sorted(iterdir())` materialised and SORTED the whole directory
        #       before the cap could break — the "bounded" cleanup was the part
        #       that could blow the hook's budget.
        #   r3: a fixed prefix window fixed the cost but STARVED the tail: an
        #       expired store behind a fresh prefix was never reached. (The
        #       comment I wrote then also claimed a cursor that did not exist.)
        #   r4: the rotating offset was still `% _scan_cap`, so nothing beyond
        #       ~2x _scan_cap was reachable — starvation with extra steps.
        #
        # What is actually true: the expensive parts were the SORT and the
        # materialised list, not the walk. `os.scandir()` is lazy and its
        # DirEntry carries the stat the readdir already paid for, so a full
        # pass is cheap. So: walk EVERYTHING (no starvation, no cursor to get
        # wrong), skip the sort entirely (order does not matter for a TTL
        # sweep), stop at `max_files` deletions, and bound the whole thing with
        # a wall-clock DEADLINE so a pathological directory can never eat the
        # hook budget. Cost is bounded by TIME, correctness by coverage.
        _deadline = time.time() + _GC_WALL_BUDGET_S
        _shard = _gc_shard_of_turn()
        _scanned = 0
        _it = os.scandir(str(store_dir))
        try:
            for _de in _it:
                _scanned += 1
                if removed >= int(max_files):
                    break
                # Check the clock every 64 entries — cheap, and enough to keep
                # the worst case near the budget rather than at a multiple.
                if (_scanned & 63) == 0 and time.time() >= _deadline:
                    break
                entry = Path(_de.path)
                name = entry.name
                # Fatia do turno (round-5 [P2]): o shard vem do NOME, nunca da
                # posicao — e por isso que a cauda deixa de ser inalcancavel.
                if _gc_shard_of_name(name) != _shard:
                    continue
                stem = None
                for suffix in _SESSION_STORE_SUFFIXES:
                    if name.endswith(suffix):
                        stem = name[: -len(suffix)]
                        break
                if stem is None or not _SESSION_SCOPE_ID_RE.match(stem):
                    continue
                try:
                    if entry.stat().st_mtime >= cutoff:
                        continue
                    entry.unlink()
                    removed += 1
                except OSError:
                    # Per-entry fail-open: a racing unlink or a permission
                    # problem on ONE file must not abort the whole sweep.
                    continue
        finally:
            try:
                _it.close()
            except Exception:
                pass
    except OSError:
        # Sweep-level fail-open (unreadable dir, vanished state root).
        return removed
    return removed


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
    # PLAN-179 W1 US3 (r1-C1 + r1-C2) — session-scope fallback
    "MAX_GC_FILES_PER_RUN",
    "SCOPE_KIND_PLAN",
    "SCOPE_KIND_SESSION",
    "SESSION_SCOPE_TTL_SECONDS",
    "SESSION_SCRATCHPAD_STORE_NAME",
    "gc_orphan_session_stores",
    "open_session_scratchpad",
    "session_id_from_event",
    "session_scope_id",
    "set_session_value",
    "stamp_scope_kind",
]
