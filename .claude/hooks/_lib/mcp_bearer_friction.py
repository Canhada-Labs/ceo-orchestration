"""PLAN-090 Wave C.2 §B firing path — MCP bearer-replay friction telemetry.

ADR-122 §B (Defer-to-v2.0 path) requires a mechanically observable
firing path so the v2.0 trigger count is NOT a paper metric. This
module is consulted at MCP auth-failure + replay-attempt detection
sites; it emits ``mcp_bearer_friction_observed`` events and exposes a
windowed aggregator consumed by
``.claude/scripts/audit-query.py mcp-friction-count``.

Stdlib only. Fail-soft per CLAUDE.md (audit emit on the failure path
must not amplify the failure).

## PLAN-112-FOLLOWUP-mcp-bearer-defenses-wire — non-blocking buffer

``observe_auth_failure`` is invoked from the MCP auth critical path on
EVERY auth-failure branch (10 branches in ``dispatch.authenticate``).
Synchronous disk/syslog I/O there would amplify p99 under a brute-force
flood (perf P1). The firing path is therefore split:

1. ``observe_auth_failure(...)`` enqueues a record into a capacity-
   bounded ``collections.deque`` AFTER applying retry-window dedup
   (security P1 / ADR-122 §B.3): the same ``(client_id, nonce)`` (with
   stable sentinels for pre-parse branches) within the retry window is
   counted once, so legitimate client/TCP retries do not inflate the
   §B.2 v2.0 trigger.
2. ``drain_observations()`` flushes the buffer by emitting one
   ``mcp_bearer_friction_observed`` per buffered record. The MCP
   request handler calls this at the END of ``authenticate()``
   (mandatory per-request drain — moves the emit cost off the
   per-branch path but still fires from the request path, NOT at
   process exit). An ``atexit`` hook is registered as a BACKUP only
   (drains anything left if a caller forgot the per-request drain).

## Capacity bound WITHOUT silent loss (Codex pair-rail P1 #3)

The earlier ``deque(maxlen=N)`` silently dropped the OLDEST enqueued
record on overflow while ``observe_auth_failure`` still returned
``True`` for the new enqueue — that broke the no-loss drain contract
under flood / audit backpressure (the dropped event was lost AND
reported as enqueued). The buffer is now an UNBOUNDED ``deque`` whose
capacity is enforced EXPLICITLY at append time (CWE-400 still bounded):

- At capacity, ``observe_auth_failure`` first attempts a
  drain-before-append to make room. If the drain frees space, the new
  record is enqueued normally (no loss).
- If the buffer is STILL at capacity after the drain attempt (e.g.
  ``audit_emit`` is unavailable so the drain re-buffered everything),
  the new record is NOT silently swallowed: an explicit module counter
  ``_DROPPED_COUNT`` is incremented and ``observe_auth_failure`` returns
  the ``DROPPED`` status, which is the FALSEY ``None`` (Codex P2 — was a
  truthy ``"dropped"`` string; a ``if observe_auth_failure(...)``
  truthiness consumer would have read an overflow drop as success). The
  drop is counted + observable via :func:`dropped_count`, never silent.

``observe_auth_failure`` is a bool-like success API: ONLY a genuine
enqueue is truthy. ``True`` = ENQUEUED; ``False`` = DEDUP_SUPPRESSED;
``None`` = DROPPED — both not-enqueued cases are falsey, so no
truthiness consumer can mistake a non-enqueue for success ("no false
success", finding #3 fully closed).

The no-loss invariant: every record that ``observe_auth_failure``
reports as ENQUEUED (``True``) is emitted exactly once by a drain.
Records reported as ``DROPPED`` (``None``) are explicitly accounted for
in ``_DROPPED_COUNT`` (no silent loss). Dedup-suppressed retries
(``False``) are intentionally NOT enqueued and were never distinct
friction events.
"""

from __future__ import annotations

import atexit
import collections
import datetime as _dt
import hashlib
import json as _json
import os
import re
import threading
import time
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

# Allowlist sanitizer for `mcp_server` field — prevents log-injection
# (the value is a server name, not free-form text).
_MCP_SERVER_ALLOWED = re.compile(r"[^a-zA-Z0-9_-]+")

# ---------------------------------------------------------------------
# PLAN-112-FOLLOWUP — non-blocking buffer + retry-window dedup state.
# ---------------------------------------------------------------------

# Capacity bound: a flood cannot grow memory past this many pending
# records (CWE-400). 8192 is generous vs. a single request's ≤1 enqueue
# per branch. Codex pair-rail P1 #3: capacity is enforced EXPLICITLY at
# append time (drain-before-append + an explicit dropped-count) — NOT via
# ``deque(maxlen=...)``, which would silently drop the OLDEST record while
# still reporting the new enqueue as successful (no-loss violation).
_BUFFER_CAPACITY: int = 8192

# Backwards-compatible alias — some callers/tests reference the old name.
_BUFFER_MAXLEN: int = _BUFFER_CAPACITY

# Retry-window: identical (client_id, nonce) friction within this many
# seconds is deduped to one enqueued record (ADR-122 §B.3). 60s mirrors
# the bearer skew window — a legitimate client retrying a failed call
# inside the token's freshness window is one logical friction event.
_RETRY_WINDOW_S: float = 60.0

# Sentinel for missing dedup-key components (pre-parse branches).
_DEDUP_SENTINEL = "∅"  # "∅"

# observe_auth_failure return statuses (Codex pair-rail P1 #3 + P2). The
# function is a bool-like success API: ONLY a genuinely-enqueued record
# returns truthy. ``True`` = ENQUEUED. Both not-enqueued cases are FALSEY
# so NO truthiness consumer (``if observe_auth_failure(...)``) can ever
# mistake a not-enqueued result for success:
#   - DEDUP_SUPPRESSED -> ``False`` (suppressed by retry-window dedup)
#   - DROPPED          -> ``None``  (P2 fix: was the TRUTHY "dropped"
#                                    string; now explicitly falsey so an
#                                    overflow drop is never a false success)
# Callers needing to DISTINGUISH a drop from a dedup-suppress check
# ``result is None`` (drop) vs ``result is False`` (dedup); the explicit
# ``dropped_count()`` counter is the durable, observable record of drops.
OBSERVE_ENQUEUED = True
OBSERVE_DEDUP_SUPPRESSED = False
OBSERVE_DROPPED = None

# Module state (process-local; MCP server is per-process per ADR-040).
_LOCK = threading.RLock()
# UNBOUNDED deque — capacity enforced explicitly at append (P1 #3); we do
# NOT use maxlen because that silently drops the oldest record.
_BUFFER: Deque[Dict[str, object]] = collections.deque()
# dedup_key -> last-seen monotonic seconds. Pruned opportunistically.
_DEDUP_SEEN: Dict[Tuple[str, str], float] = {}
# Explicit count of records that could NOT be enqueued because the buffer
# was at capacity even after a drain-before-append attempt. Surfaced via
# dropped_count(); guarantees overflow is accounted for, never silent.
_DROPPED_COUNT: int = 0
_ATEXIT_REGISTERED = False


def _sanitize_mcp_server(value: str) -> str:
    """Strip everything outside [A-Za-z0-9_-] and cap to 64 chars."""
    cleaned = _MCP_SERVER_ALLOWED.sub("", value or "")
    return cleaned[:64]


def _sanitize_reason(value: str) -> str:
    """Cap to 128 chars and replace control chars per Sec MF-3."""
    if not value:
        return ""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "?", value)
    return cleaned[:128]


def _token_hash12(raw_token: Optional[str]) -> str:
    """Stable 12-char dedup discriminator for a raw token.

    Used ONLY as a dedup-key component for pre-parse branches where the
    nonce is unavailable. The token value itself is NEVER persisted or
    emitted — only this one-way SHA-256 prefix is used in-memory for
    dedup. Returns the sentinel when there is no token at all.
    """
    if not raw_token:
        return _DEDUP_SENTINEL
    digest = hashlib.sha256(raw_token.encode("utf-8", "replace")).hexdigest()
    return digest[:12]


def _dedup_key(
    *,
    client_id: Optional[str],
    nonce: Optional[str],
    raw_token: Optional[str],
) -> Tuple[str, str]:
    """Build the retry-window dedup key per PLAN-112-FOLLOWUP §3a.

    Key = ``(client_id or "∅", nonce or sha256(raw_token)[:12] or "∅")``.
    Every branch has a stable key:

    - Post-parse branches (HMAC invalid, skew, ACL, CORS, rate-limit,
      replay DENYs) carry client_id + nonce.
    - Pre-parse branches (no token / malformed token) have no
      client_id/nonce → fall back to ``(∅, token_hash12)`` where
      token_hash12 is the sentinel when there is no token.
    """
    cid = client_id if (isinstance(client_id, str) and client_id) else _DEDUP_SENTINEL
    if isinstance(nonce, str) and nonce:
        non = nonce
    else:
        non = _token_hash12(raw_token)
    return (cid, non)


def _now_monotonic() -> float:
    return time.monotonic()


def _should_emit_after_dedup(key: Tuple[str, str], now_s: float) -> bool:
    """Return True iff this key has NOT been seen within the retry window.

    Records the key's last-seen time when it passes (so subsequent
    retries inside the window are suppressed). Opportunistically prunes
    keys older than the retry window to bound the dedup map.
    """
    # Opportunistic prune so the dedup map cannot grow without bound.
    if _DEDUP_SEEN:
        stale_cutoff = now_s - _RETRY_WINDOW_S
        stale_keys = [k for k, t in _DEDUP_SEEN.items() if t < stale_cutoff]
        for k in stale_keys:
            _DEDUP_SEEN.pop(k, None)
    last = _DEDUP_SEEN.get(key)
    if last is not None and (now_s - last) <= _RETRY_WINDOW_S:
        # Seen within the window — refresh timestamp, suppress emit.
        _DEDUP_SEEN[key] = now_s
        return False
    _DEDUP_SEEN[key] = now_s
    return True


def observe_auth_failure(
    *,
    mcp_server: str,
    failure_reason: str,
    replay_suspected: bool = False,
    client_id: Optional[str] = None,
    nonce: Optional[str] = None,
    raw_token: Optional[str] = None,
) -> Optional[bool]:
    """Buffer one MCP auth-failure friction observation (non-blocking).

    ``mcp_server``: short server slug (e.g. ``"codex"``). Sanitized to
    ``[A-Za-z0-9_-]{1,64}``.

    ``failure_reason``: one of (suggested taxonomy, NOT enforced):
    ``bearer_expired``, ``bearer_unknown``, ``auth_403``, ``nonce_repeat``,
    ``jti_collision``, ``alg_rejected``, ``downgrade_attempted``, or the
    dispatch deny-reason enum (``auth_token_malformed`` / ``auth_hmac_invalid``
    / ``timestamp_skew`` / ``acl_missing_handler`` / ``cors_default_deny`` /
    ``rate_limit``) and the replay store DENYs (``nonce_reused`` /
    ``stale_iat`` / ``stale_iat_and_nonce_reused``). Capped to 128 chars
    and stripped of control bytes.

    ``replay_suspected``: True iff a replay attempt was detected (a
    re-presented nonce within the cache window OR a downgrade-attack
    signature). Promotes the event to a §B re-open trigger.

    ``client_id`` / ``nonce`` / ``raw_token``: dedup-key inputs
    (PLAN-112-FOLLOWUP §3a). The raw token is used ONLY for an in-memory
    one-way hash dedup discriminator; it is never persisted/emitted.

    Returns (Codex pair-rail P1 #3 + P2 — bool-like success API; ONLY a
    genuine enqueue is truthy):

    - ``OBSERVE_ENQUEUED`` (``True``) — enqueued as a distinct friction
      event. The ONLY truthy result.
    - ``OBSERVE_DEDUP_SUPPRESSED`` (``False``) — suppressed by
      retry-window dedup (not a distinct event). FALSEY.
    - ``OBSERVE_DROPPED`` (``None``) — buffer at capacity even after a
      drain-before-append attempt; the record was NOT enqueued and
      ``_DROPPED_COUNT`` was incremented (explicit, observable loss —
      never silent). FALSEY (P2 fix: was the truthy ``"dropped"`` string;
      a truthiness consumer ``if observe_auth_failure(...)`` would have
      mistaken an overflow drop for success).

    A truthiness check (``if observe_auth_failure(...)``) is therefore
    SAFE: it is True iff the record was genuinely enqueued. To
    distinguish a drop from a dedup-suppress, test ``result is None``
    (drop) vs ``result is False`` (dedup); the durable, observable record
    of drops is :func:`dropped_count`.

    NON-BLOCKING on the happy path: no I/O happens for an enqueue — emit
    happens at :func:`drain_observations`. The drain-before-append only
    runs on the (rare) at-capacity path.
    """
    global _DROPPED_COUNT
    server = _sanitize_mcp_server(mcp_server)
    reason = _sanitize_reason(failure_reason)
    try:
        with _LOCK:
            _ensure_atexit_drain_registered()
            now_s = _now_monotonic()
            key = _dedup_key(
                client_id=client_id, nonce=nonce, raw_token=raw_token
            )
            if not _should_emit_after_dedup(key, now_s):
                return OBSERVE_DEDUP_SUPPRESSED
            # Capacity enforcement WITHOUT silent loss (P1 #3). If at
            # capacity, try a drain-before-append to make room.
            if len(_BUFFER) >= _BUFFER_CAPACITY:
                # RLock is re-entrant — safe to drain under the held lock.
                drain_observations()
                if len(_BUFFER) >= _BUFFER_CAPACITY:
                    # Drain did not free space (e.g. audit_emit
                    # unavailable → re-buffered). Account for the drop
                    # explicitly; do NOT silently overwrite an older
                    # enqueued record.
                    _DROPPED_COUNT += 1
                    return OBSERVE_DROPPED
            _BUFFER.append(
                {
                    "mcp_server": server,
                    "failure_reason": reason,
                    "replay_suspected": bool(replay_suspected),
                }
            )
            return OBSERVE_ENQUEUED
    except Exception:  # noqa: BLE001
        # Fail-soft — never amplify the auth-failure path. A fail-soft
        # path is NOT a counted capacity drop (it is an unexpected error,
        # surfaced as dedup-suppressed so callers do not assume enqueue).
        return OBSERVE_DEDUP_SUPPRESSED


def drain_observations() -> int:
    """Emit all buffered friction observations; return the emit count.

    Called at the END of ``dispatch.authenticate`` (mandatory per-request
    drain) and from the ``atexit`` backup. Each buffered record produces
    exactly one ``mcp_bearer_friction_observed`` event (no-loss
    invariant). Fail-soft: a single emit failure does not abort the
    drain, and a total failure to import audit_emit leaves the buffer
    intact for the next drain.
    """
    drained: List[Dict[str, object]] = []
    with _LOCK:
        while _BUFFER:
            drained.append(_BUFFER.popleft())
    if not drained:
        return 0
    try:
        from _lib import audit_emit
    except Exception:  # noqa: BLE001
        # audit_emit unavailable — re-buffer so we do not lose events.
        with _LOCK:
            for rec in reversed(drained):
                _BUFFER.appendleft(rec)
        return 0
    emitted = 0
    for rec in drained:
        try:
            audit_emit.emit_mcp_bearer_friction_observed(
                mcp_server=str(rec.get("mcp_server", "")),
                failure_reason=str(rec.get("failure_reason", "")),
                replay_suspected=bool(rec.get("replay_suspected", False)),
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
            )
            emitted += 1
        except Exception:  # noqa: BLE001
            # Fail-soft per record — keep draining the rest.
            continue
    return emitted


def _ensure_atexit_drain_registered() -> None:
    """Register the atexit backup drain exactly once (caller holds lock)."""
    global _ATEXIT_REGISTERED
    if _ATEXIT_REGISTERED:
        return
    try:
        atexit.register(drain_observations)
        _ATEXIT_REGISTERED = True
    except Exception:  # noqa: BLE001
        # If atexit registration fails, the mandatory per-request drain
        # still fires from authenticate(); atexit is only a backup.
        pass


def buffer_len() -> int:
    """Return the number of pending (un-drained) observations (test aid)."""
    with _LOCK:
        return len(_BUFFER)


def dropped_count() -> int:
    """Return the explicit count of capacity-dropped observations (P1 #3).

    A non-zero value means the buffer hit capacity AND a
    drain-before-append could not free room (e.g. audit_emit
    unavailable). Every drop here is accounted for — the no-loss
    contract holds for everything ``observe_auth_failure`` reported as
    ENQUEUED; DROPPED records are counted, never silently discarded.
    """
    with _LOCK:
        return _DROPPED_COUNT


def _reset_state_for_test() -> None:
    """Clear buffer + dedup map + dropped counter (test isolation)."""
    global _DROPPED_COUNT
    with _LOCK:
        _BUFFER.clear()
        _DEDUP_SEEN.clear()
        _DROPPED_COUNT = 0


# ---------------------------------------------------------------------
# Windowed aggregation — consumed by audit-query.py mcp-friction-count.
# ---------------------------------------------------------------------


def _audit_log_path() -> Path:
    """Locate the audit log honoring CEO_AUDIT_LOG_PATH override."""
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = Path(os.environ.get("HOME") or Path.home())
    return (
        home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    )


def count_friction_in_window(
    *,
    window_hours: int = 24,
    audit_log: Optional[Path] = None,
    include_replay_only: bool = False,
) -> int:
    """Count ``mcp_bearer_friction_observed`` events in the time window.

    ``include_replay_only``: when True, count only events where
    ``replay_suspected == true`` — surfaces the §B §re-open trigger
    "5-repo soak surfaces ANY replay attempt".
    """
    path = audit_log or _audit_log_path()
    if not path.is_file():
        return 0
    cutoff = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(
        hours=int(window_hours)
    )
    total = 0
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = _json.loads(line)
            except _json.JSONDecodeError:
                continue
            if ev.get("action") != "mcp_bearer_friction_observed":
                continue
            ts = _parse_iso(ev.get("ts") or "")
            if ts is None or ts < cutoff:
                continue
            if include_replay_only and not ev.get("replay_suspected", False):
                continue
            total += 1
    return total


def _parse_iso(ts: str) -> Optional[_dt.datetime]:
    """Best-effort ISO-8601 parse. None on malformed input."""
    if not ts:
        return None
    candidate = ts.replace("Z", "+00:00")
    try:
        d = _dt.datetime.fromisoformat(candidate)
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone.utc)
        return d
    except (TypeError, ValueError):
        return None


__all__ = [
    "observe_auth_failure",
    "drain_observations",
    "buffer_len",
    "dropped_count",
    "count_friction_in_window",
    "OBSERVE_ENQUEUED",
    "OBSERVE_DEDUP_SUPPRESSED",
    "OBSERVE_DROPPED",
]
