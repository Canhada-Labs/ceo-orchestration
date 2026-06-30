"""PLAN-102 Wave B.4-B.6 — swarm circuit-breaker primitives.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/swarm_circuit_breaker.py`.

## Doctrine

Three pure detectors over the audit-log:

- :meth:`SwarmCircuitBreaker.should_pause_reverse_tripwire` — B.4:
  >N=1000 `swarm_iteration` events in 24h without any
  `session_start` event in the same window → return True (caller
  emits `swarm_runaway_suspected`). `session_start` is the
  Owner-physical proxy per P1 #2 fold (the phantom
  `swarm_owner_physical_event` action is NOT in `_KNOWN_ACTIONS`).
- :meth:`SwarmCircuitBreaker.should_pause_weekend_burn` — B.5:
  swarm-loop running >12h without any `session_start` event in the
  rolling window → return True (caller emits
  `swarm_paused_owner_absent`). Same Owner-physical proxy.
- :meth:`SwarmCircuitBreaker.recovery_latency_p99` — B.6: p99
  kill-event-to-halted latency over a sample list of halt timestamps;
  SLO ≤60s.

Audit-log reads stream JSONL line-by-line (no full-file load) — try/
except per line, breadcrumb + skip on malformed JSON (fail-OPEN
infra discipline per PLAN-091-followup S116).

Stdlib only. Python >= 3.9. ``CEO_EXECUTION_CONTEXT_HOOKS_DISABLE=1``
short-circuits all detectors to return False / 0.0 (kill-switch
posture).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List

_SECONDS_PER_HOUR = 3600
# P1 #2 fold — proxy "Owner physically present" via `session_start`
# (real action in `_KNOWN_ACTIONS` since Sprint 11 SessionStart hook).
# A new `session_start` event in the rolling window means the Owner
# booted a session — a strong proxy for "physical operator activity".
# Previously this module referenced `user_message` /
# `read_called_by_owner` / `swarm_owner_physical_event` which are NOT
# in `_KNOWN_ACTIONS` (phantom audit actions; the audit-log will
# never carry them, so the detector always over-fires).
_OWNER_READ_ACTIONS = frozenset({"session_start"})


def is_disabled() -> bool:
    return os.environ.get("CEO_EXECUTION_CONTEXT_HOOKS_DISABLE", "") == "1"


def _stream_events(audit_log_path: Path) -> Iterator[dict]:
    if not audit_log_path.is_file():
        return
    try:
        with audit_log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError:
        return


def _event_ts(event: dict) -> float:
    """Extract Unix-seconds timestamp from event; fail-OPEN to 0.0.

    Handles the formats audit_emit actually writes: ISO-8601
    "%Y-%m-%dT%H:%M:%SZ" (the canonical ts field), legacy numeric
    seconds/ms strings, and the wall_ns nanosecond-epoch fallback.
    PLAN-113 Codex pair-rail P1: before this, ISO strings fell through to
    0.0, so every real event read as ancient and the breaker never fired.
    """
    ts = event.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts) / 1000.0 if ts > 1e11 else float(ts)
    if isinstance(ts, str):
        try:
            return float(ts)
        except ValueError:
            pass
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except (ValueError, AttributeError):
            pass
    wall_ns = event.get("wall_ns")
    if isinstance(wall_ns, int):
        return wall_ns / 1_000_000_000.0
    return 0.0


class SwarmCircuitBreaker:
    """Stateless detectors over audit-log streams (Wave B.4-B.6)."""

    @staticmethod
    def should_pause_reverse_tripwire(
        audit_log_path: Path,
        threshold: int = 1000,
        window_hours: int = 24,
    ) -> bool:
        """B.4 — runaway iteration count without Owner-physical proxy.

        Returns True if >``threshold`` ``swarm_iteration`` events
        observed in the trailing ``window_hours`` window AND no
        ``session_start`` event in the same window. ``session_start``
        is the Owner-physical proxy per P1 #2 fold — the SessionStart
        hook fires every time the Owner boots a Claude Code session,
        which is a strong proxy for "human present".
        """
        if is_disabled():
            return False
        cutoff = time.time() - (window_hours * _SECONDS_PER_HOUR)
        iter_count = 0
        owner_seen = False
        for event in _stream_events(audit_log_path):
            ts = _event_ts(event)
            if ts < cutoff:
                continue
            action = event.get("action", "")
            if action == "swarm_iteration":
                iter_count += 1
            elif action in _OWNER_READ_ACTIONS:
                owner_seen = True
        return iter_count > threshold and not owner_seen

    @staticmethod
    def should_pause_weekend_burn(
        audit_log_path: Path,
        max_hours: int = 12,
    ) -> bool:
        """B.5 — swarm running >max_hours without an Owner Read-family event.

        We approximate "swarm running" by the earliest unmatched
        ``swarm_started`` event whose timestamp predates the latest
        Owner Read by more than ``max_hours``. If no Owner Read event
        in the window AND a swarm has been running > max_hours, pause.
        """
        if is_disabled():
            return False
        max_seconds = max_hours * _SECONDS_PER_HOUR
        now = time.time()
        latest_owner_read = 0.0
        earliest_running_swarm = 0.0
        active_swarms: dict = {}
        for event in _stream_events(audit_log_path):
            ts = _event_ts(event)
            action = event.get("action", "")
            if action in _OWNER_READ_ACTIONS and ts > latest_owner_read:
                latest_owner_read = ts
            elif action == "swarm_started":
                sid = event.get("swarm_id") or event.get("session_id") or ts
                active_swarms[sid] = ts
            elif action in ("swarm_halted_budget", "swarm_halted_kill", "swarm_halted_convergence", "swarm_killed", "swarm_aborted_error"):
                sid = event.get("swarm_id") or event.get("session_id")
                if sid in active_swarms:
                    active_swarms.pop(sid, None)
        if not active_swarms:
            return False
        earliest_running_swarm = min(active_swarms.values())
        age = now - earliest_running_swarm
        if age <= max_seconds:
            return False
        if latest_owner_read >= earliest_running_swarm:
            return False
        return True

    @staticmethod
    def recovery_latency_p99(
        kill_event_ts: float,
        halt_observations: List[float],
    ) -> float:
        """B.6 — p99 latency in seconds from kill event to halt observations.

        ``halt_observations`` is a list of Unix-seconds timestamps when
        each individual loop observed kill propagation. Returns p99
        deltaT in seconds. SLO target: ≤60.0.
        """
        if not halt_observations:
            return 0.0
        deltas = [max(0.0, t - kill_event_ts) for t in halt_observations]
        deltas.sort()
        n = len(deltas)
        if n == 1:
            return deltas[0]
        # P99 via nearest-rank with ceiling — matches standard SLO calc
        # (Prometheus histogram_quantile / Datadog p99). For N≥100 this
        # gives the 99th-percentile observation; for N<100 it returns
        # the worst observation (max), which is conservative.
        idx = int(-(-99 * n // 100)) - 1  # ceil(0.99*n) - 1
        idx = max(0, min(idx, n - 1))
        return deltas[idx]
