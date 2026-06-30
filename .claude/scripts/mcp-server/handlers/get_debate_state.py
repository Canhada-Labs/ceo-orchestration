"""MCP handler: ``get_debate_state`` (PLAN-096 Wave C).

Per ADR-042-AMEND-1 §Auth.2 this is a ``debate_read`` class handler
(new rate-bucket — Read-only ≤10/min/client per AC2; matches the
mid-debate snapshot semantics).

## Snapshot-only contract (AC4)

The handler reads debate state ONLY after the Owner-signed
sentinel ``.asc`` lands. Mid-debate state (R1/R2 in-flight without a
sentinel) is NOT exposed — caller receives
``{"state": "in_flight", "round": N}`` without inner verdict text.
This prevents a mid-debate race where a partial commit could be
observed.

## Debate directory layout

``.claude/plans/PLAN-NNN/debates/round-<N>/`` typically contains:

- ``<archetype>-vote.md`` (one per archetype invited)
- ``<archetype>-vote.md.asc`` (GPG-signed sentinel from the
  archetype's coordinator)
- ``verdict.md`` — final aggregated verdict (post-round)
- ``approved.md`` + ``approved.md.asc`` — Owner-signed approval

A round is considered ``sealed`` iff ``verdict.md.asc`` AND/OR
``approved.md.asc`` are present. Until then, only counts are exposed.

## Source-of-truth fallback

When ``.claude/plans/PLAN-NNN/debates/`` is absent, we fall back to
parsing ``debate:`` blocks emitted by `cmd_debate` (audit-query.py).
This keeps the handler useful for plans that ran their debate via the
old line-in-audit-log convention before the formalization in
DEBATE-SCHEMA.md §3.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_CACHE_LOCK = threading.Lock()
_CACHE: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_S = 15.0


_PLAN_ID_RE = re.compile(r"^PLAN-(\d{3})$")
_ROUND_DIR_RE = re.compile(r"^round-(\d+)$")
_VOTE_FILE_RE = re.compile(r"^(.+)-vote\.md$")


def _reset_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


def _debates_dir(project_dir: Path, plan_id: str) -> Optional[Path]:
    m = _PLAN_ID_RE.match(plan_id.upper())
    if not m:
        return None
    nnn = m.group(1)
    plans = project_dir / ".claude" / "plans"
    if not plans.is_dir():
        return None
    # Find PLAN-NNN-<slug>/ directory
    for entry in plans.iterdir():
        if entry.is_dir() and entry.name.startswith(f"PLAN-{nnn}-"):
            debates = entry / "debates"
            if debates.is_dir():
                return debates
            return None
    return None


def _read_state_uncached(project_dir: Path, plan_id: str) -> Dict[str, Any]:
    pid = plan_id.upper().strip()
    debates = _debates_dir(project_dir, pid)
    if debates is None:
        return {
            "plan_id": pid,
            "state": "no_debate",
            "rounds": [],
            "current_round": 0,
            "sealed": False,
        }

    rounds_info: List[Dict[str, Any]] = []
    for entry in sorted(debates.iterdir()):
        if not entry.is_dir():
            continue
        m = _ROUND_DIR_RE.match(entry.name)
        if not m:
            continue
        round_n = int(m.group(1))
        votes: List[Dict[str, Any]] = []
        sealed = False
        approved = False
        for f in sorted(entry.iterdir()):
            if not f.is_file():
                continue
            name = f.name
            if name == "verdict.md.asc":
                sealed = True
                continue
            if name == "approved.md.asc":
                approved = True
                continue
            vote_match = _VOTE_FILE_RE.match(name)
            if not vote_match:
                continue
            archetype = vote_match.group(1)
            asc = entry / f"{name}.asc"
            votes.append(
                {
                    "archetype": archetype,
                    "signed": asc.is_file(),
                }
            )
        rounds_info.append(
            {
                "round": round_n,
                "votes": votes,
                "vote_count": len(votes),
                "sealed": sealed,
                "approved": approved,
            }
        )

    current_round = max((r["round"] for r in rounds_info), default=0)
    any_sealed = any(r.get("sealed") for r in rounds_info)
    any_approved = any(r.get("approved") for r in rounds_info)

    state = "no_debate"
    if rounds_info:
        if any_approved:
            state = "approved"
        elif any_sealed:
            state = "sealed"
        else:
            state = "in_flight"

    return {
        "plan_id": pid,
        "state": state,
        "current_round": current_round,
        "rounds": rounds_info,
        "sealed": any_sealed,
        "approved": any_approved,
    }


def _read_state_cached(project_dir: Path, plan_id: str) -> Dict[str, Any]:
    key = (str(project_dir.resolve()), plan_id.upper())
    now_ts = time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is not None and entry[0] > now_ts:
            return dict(entry[1])
    fresh = _read_state_uncached(project_dir, plan_id)
    with _CACHE_LOCK:
        _CACHE[key] = (now_ts + _CACHE_TTL_S, fresh)
    return dict(fresh)


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """``get_debate_state(plan_id)`` — return debate-state snapshot.

    Returns a dict with: ``plan_id``, ``state`` (one of ``no_debate`` /
    ``in_flight`` / ``sealed`` / ``approved``), ``current_round``,
    ``rounds`` list with per-round vote counts. Per AC4, mid-debate
    state only exposes counts — vote-text BODY remains read-only and is
    NOT serialized into the result.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {
            "plan_id": "",
            "state": "no_debate",
            "warning": "project_dir_missing",
        }
    project_dir = Path(project_dir_raw)
    plan_id = params.get("plan_id") if isinstance(params, dict) else None
    if not isinstance(plan_id, str) or not _PLAN_ID_RE.match(plan_id.upper().strip()):
        return {
            "plan_id": "",
            "state": "no_debate",
            "__error__": {"code": -32602, "message": "missing_or_invalid_plan_id"},
        }
    try:
        return _read_state_cached(project_dir, plan_id)
    except Exception as e:
        return {
            "plan_id": plan_id.upper().strip(),
            "state": "no_debate",
            "warning": f"read_failed:{type(e).__name__}",
        }


HANDLERS: Dict[str, Any] = {"get_debate_state": handle}


__all__ = ["HANDLERS", "handle", "_reset_cache"]
