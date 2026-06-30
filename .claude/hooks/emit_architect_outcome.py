#!/usr/bin/env python3
"""Emit Architect outcome events from post-spawn audit data (Sprint 9 P3.1).

Not a PreToolUse/PostToolUse hook — this is a helper invoked by
`/architect` command wrapping to infer whether the lessons it injected
"helped" the spawn, and record the outcome via `lessons.record_outcome`.

Separate file (not a widening of `check_agent_spawn.py`) per PLAN-009
C4/A7. Single responsibility, easier to reason about, no entanglement
with the spawn-governance path.

## Inference rule (PLAN-009 P3.1)

After a spawn completes with `CEO_ARCHITECT_ACTIVE=1`, scan audit
events bounded by:

1. **Temporal window:** 10 minutes after the Architect spawn end.
2. **Session equality:** `session_id` must match the Architect spawn.

Both must hold — session_id match alone OR window alone does NOT
attribute. This resists "veto in another tab within 10min" attribution
attacks (C4/A7).

## Outcome rule

- `hit` — zero `veto_triggered` AND zero `confidence_gate` with
  `fail_count > 0` in the session+window.
- `miss` — at least one veto OR at least one confidence_gate fail in
  the same session+window.

## Usage

```
python3 .claude/hooks/emit_architect_outcome.py \
    --session-id <sid> \
    --lesson-ids "L1,L2,L3" \
    --spawn-end-ts 2026-04-14T12:00:00Z \
    [--window-sec 600] \
    [--base-dir <lessons-dir>]
```

Exit codes:
- 0 — outcomes recorded (or no lessons to record)
- 2 — arg error
- 3 — session_id not found in audit log (nothing to correlate)

## Production status (M6) — UNWIRED, advisory only

This module is built + unit-tested but has **no production trigger**: the
`/architect` wrapper does not currently invoke it on a live spawn, so the
Reflexion-style outcome loop it implements does not run in normal operation.
It is invoked only by its own tests and on explicit manual CLI use. Do NOT
read the presence of this file (or any ADR that calls the Reflexion loop
"live") as evidence the loop is on the live path. Wiring it is deferred as a
deliberate, separately-reviewed change (the auto-trigger is risky to enable
blindly); the corresponding ADR/doc "live" claims are downgraded to
"built/tested, not wired" via the documentation wave. (The sibling
policy engine — `_lib/policy.py`, referenced as `policy_dispatch.py` in older
ADR prose — is in the same built-but-not-on-live-path state.)

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_SCRIPTS_DIR = _HOOKS_DIR.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _lib import audit_emit  # noqa: E402
import lessons as _lessons  # noqa: E402


DEFAULT_WINDOW_SEC = 600  # 10 minutes


def _parse_iso(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def infer_outcome(
    session_id: str,
    spawn_end: datetime,
    *,
    window_sec: int = DEFAULT_WINDOW_SEC,
    events: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Return "hit" or "miss" based on session+window events.

    Caller provides `events` iterable (typically read via
    `audit_emit.iter_events()`); this pure function lets tests inject
    synthetic events without touching a real audit log.
    """
    if events is None:
        try:
            events = list(audit_emit.iter_events())
        except Exception:
            return "hit"  # fail-safe: no data → no miss attribution

    cutoff = spawn_end + timedelta(seconds=window_sec)

    for e in events:
        if e.get("session_id") != session_id:
            continue
        ts = _parse_iso(e.get("ts", ""))
        if ts is None or ts < spawn_end or ts > cutoff:
            continue
        action = e.get("action")
        if action == "veto_triggered":
            return "miss"
        if action == "confidence_gate" and int(e.get("fail_count") or 0) > 0:
            return "miss"
    return "hit"


def record_outcomes(
    lesson_ids: List[str],
    hit: bool,
    *,
    base_dir: Optional[str] = None,
) -> int:
    """Record outcome for each lesson_id. Returns count of successful writes."""
    success = 0
    for lid in lesson_ids:
        if not lid:
            continue
        try:
            result = _lessons.record_outcome(
                lid, hit=hit, base_dir=base_dir, consumer="architect",
            )
            if result is not None:
                success += 1
        except (ValueError, OSError):
            continue
    return success


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Record Architect outcome per PLAN-009 P3.1 inference rule.",
    )
    p.add_argument("--session-id", required=True, help="Architect session_id")
    p.add_argument(
        "--lesson-ids", required=True,
        help="Comma-separated list of lesson IDs injected by Architect",
    )
    p.add_argument(
        "--spawn-end-ts", required=True,
        help="ISO 8601 UTC timestamp when the Architect spawn ended",
    )
    p.add_argument(
        "--window-sec", type=int, default=DEFAULT_WINDOW_SEC,
        help=f"Temporal window in seconds (default {DEFAULT_WINDOW_SEC})",
    )
    p.add_argument("--base-dir", default=None, help="Override lessons dir (testing)")
    args = p.parse_args(argv)

    spawn_end = _parse_iso(args.spawn_end_ts)
    if spawn_end is None:
        print(f"ERROR: unparseable --spawn-end-ts: {args.spawn_end_ts!r}",
              file=sys.stderr)
        return 2

    lesson_ids = [x.strip() for x in args.lesson_ids.split(",") if x.strip()]
    if not lesson_ids:
        return 0  # nothing to record

    try:
        events = list(audit_emit.iter_events())
    except Exception:
        events = []

    # Require at least one event with this session_id — otherwise we
    # have no ground to attribute anything.
    has_session = any(e.get("session_id") == args.session_id for e in events)
    if not has_session:
        print(f"INFO: no events found for session_id={args.session_id}",
              file=sys.stderr)
        return 3

    outcome = infer_outcome(
        args.session_id, spawn_end,
        window_sec=args.window_sec, events=events,
    )

    # Bookkeeping emit: record each lesson + session-level lesson_outcome
    # event with inference_mode="session-correlated" per ADR-015 amendment.
    recorded = record_outcomes(lesson_ids, hit=(outcome == "hit"), base_dir=args.base_dir)

    try:
        audit_emit.emit_lesson_outcome(
            lesson_id=",".join(lesson_ids),
            archetype="architect",
            hit=(outcome == "hit"),
            hit_count=0,  # aggregate emit; per-lesson counts inside record_outcome
            miss_count=0,
            session_id=args.session_id,
            consumer="architect",
            inference_mode="session-correlated",
            window_duration_seconds=args.window_sec,
            session_end_reason="explicit",
        )
    except Exception:
        pass

    print(f"outcome={outcome} recorded={recorded}/{len(lesson_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
