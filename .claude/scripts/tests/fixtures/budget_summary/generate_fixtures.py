#!/usr/bin/env python3
"""Synthetic audit-log fixture generator (PLAN-083 Wave 0b sub-0.8).

Generates 5 ``audit-log-NNN.jsonl`` fixture files plus an active
``audit-log.jsonl`` covering the realistic event mix the tests assert
against:

  - ``agent_spawn`` with claude-opus-4-7 + tokens_in/out
  - ``pair_rail_case`` with gpt-5-codex + tokens_in/out (POST-WIRE)
  - ``plan_status_transition`` to seed plan_id inference
  - ``wallclock_milestone``
  - ``token_budget_guard_paused``
  - A handful of overlap events repeated across rotation boundaries
    (the dedup target)

Designed to sum to ~$1100 cumulative cost so the memory-claim band
[$1003, $1543] passes via ``validate_memory_claim``.

Run from the fixtures dir:

    python3 generate_fixtures.py /tmp/audit-fixtures

The output dir layout matches what ``budget-summary.py`` expects when
pointed at it via ``--audit-dir``.

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _ts(base: datetime, offset_minutes: int) -> str:
    t = base + timedelta(minutes=offset_minutes)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hmac_for(event: Dict[str, Any], chain_idx: int) -> str:
    # Deterministic but per-rotation: hash event + chain idx so the
    # *same* logical event in two rotations gets DIFFERENT hmacs (which
    # is exactly the dedup challenge `canonical_event_sha256` solves
    # by stripping `hmac` before hashing).
    blob = json.dumps(event, sort_keys=True) + f"#{chain_idx}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _make_agent_spawn(
    *,
    base_ts: datetime,
    offset_minutes: int,
    session_id: str,
    plan_id: str,
    archetype: str = "general-purpose",
    tokens_in: int = 800,
    tokens_out: int = 1200,
    tokens_total: int = 45000,  # cache-heavy total
    desc: str = "sub-agent task",
    wave: str = "",
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "ts": _ts(base_ts, offset_minutes),
        "action": "agent_spawn",
        "session_id": session_id,
        "project": "/Users/test/ceo-orchestration",
        "tool": "Agent",
        "subagent_type": archetype,
        "desc_preview": desc,
        "skill": "unknown",
        "has_profile": True,
        "has_file_assignment": True,
        "prompt_len_bucket": "<16384",
        "response_kind": "object",
        "hook_duration_ms": 0,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_total,
        "model": "claude-opus-4-7",
        "archetype": archetype,
        "plan_id": plan_id,
    }
    if wave:
        event["wave_id"] = wave
    return event


def _make_pair_rail_case(
    *,
    base_ts: datetime,
    offset_minutes: int,
    session_id: str,
    plan_id: str = "",
    case: str = "A",
    claude_verdict: str = "PASS",
    codex_verdict: str = "PASS",
    tokens_in: int = 1500,
    tokens_out: int = 800,
    tokens_total: int = 2300,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "ts": _ts(base_ts, offset_minutes),
        "action": "pair_rail_case",
        "session_id": session_id,
        "case": case,
        "claude_verdict": claude_verdict,
        "codex_verdict": codex_verdict,
        "tool_name": "Edit",
        "file_path_hash_prefix": "deadbeef12345678",
        "precondition_met": False,
        "rubric_violation_id": "",
        "severity": "",
        "jaccard_similarity_bucket": "",
        "human_triage_grace_h": 0,
        "project": "",
        "event_schema": "v2",
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_total": tokens_total,
        "model": "gpt-5-codex",
    }
    if plan_id:
        event["plan_id"] = plan_id
    return event


def _make_plan_transition(
    *,
    base_ts: datetime,
    offset_minutes: int,
    session_id: str,
    plan_id: str,
    to_status: str = "executing",
) -> Dict[str, Any]:
    return {
        "ts": _ts(base_ts, offset_minutes),
        "action": "plan_status_transition",
        "session_id": session_id,
        "plan_id": plan_id,
        "to_status": to_status,
    }


def _make_wallclock(
    *, base_ts: datetime, offset_minutes: int, session_id: str, milestone: str = "wave-0a-done"
) -> Dict[str, Any]:
    return {
        "ts": _ts(base_ts, offset_minutes),
        "action": "wallclock_milestone",
        "session_id": session_id,
        "milestone": milestone,
    }


def _make_budget_pause(
    *, base_ts: datetime, offset_minutes: int, session_id: str
) -> Dict[str, Any]:
    return {
        "ts": _ts(base_ts, offset_minutes),
        "action": "token_budget_guard_paused",
        "session_id": session_id,
        "reason": "estimate-exceeded",
    }


def write_file(path: Path, events: List[Dict[str, Any]], chain_offset: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for i, ev in enumerate(events):
            ev_copy = dict(ev)
            ev_copy["hmac"] = _hmac_for(ev, chain_offset + i)
            ev_copy["hmac_error"] = None
            f.write(json.dumps(ev_copy, sort_keys=True) + "\n")


def build_fixture_set(out_dir: Path) -> Dict[str, Any]:
    """Generate the 5-rotation + active fixture set.

    Returns a metadata dict with sums + plan attribution counts so the
    tests can assert against known-good totals.
    """
    base = datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc)
    files: List[Tuple[str, List[Dict[str, Any]], int]] = []

    # ----- Rotation 001 — PLAN-080 executing window (S100)
    sess_a = "11111111-1111-1111-1111-111111111111"
    r001: List[Dict[str, Any]] = [
        _make_plan_transition(
            base_ts=base, offset_minutes=0, session_id=sess_a,
            plan_id="PLAN-080", to_status="executing",
        ),
    ]
    # 20 PLAN-080 spawns, each ~$3.50 (cache-amortized)
    # tokens_in=800 * 0.015/k + tokens_out=1200 * 0.075/k = 0.012 + 0.090 = $0.102/spawn
    # Use heavier tokens to hit $200 across rotation 001:
    for i in range(20):
        r001.append(_make_agent_spawn(
            base_ts=base, offset_minutes=5 + i,
            session_id=sess_a, plan_id="PLAN-080",
            tokens_in=400000, tokens_out=120000, tokens_total=520000,
            desc=f"PLAN-080 spawn #{i+1} wave-0a",
            wave="wave-0a",
        ))
    # 5 Codex MCP pair_rail_case events
    for i in range(5):
        r001.append(_make_pair_rail_case(
            base_ts=base, offset_minutes=30 + i,
            session_id=sess_a, plan_id="PLAN-080",
            tokens_in=80000, tokens_out=30000, tokens_total=110000,
        ))
    files.append(("audit-log-001.jsonl", r001, 0))

    # ----- Rotation 002 — PLAN-081 executing window (S99)
    sess_b = "22222222-2222-2222-2222-222222222222"
    r002: List[Dict[str, Any]] = [
        _make_plan_transition(
            base_ts=base, offset_minutes=100, session_id=sess_b,
            plan_id="PLAN-081", to_status="executing",
        ),
    ]
    for i in range(25):
        r002.append(_make_agent_spawn(
            base_ts=base, offset_minutes=110 + i,
            session_id=sess_b, plan_id="PLAN-081",
            tokens_in=300000, tokens_out=140000, tokens_total=440000,
            desc=f"PLAN-081 spawn #{i+1} wave-1",
            wave="wave-1",
        ))
    for i in range(8):
        r002.append(_make_pair_rail_case(
            base_ts=base, offset_minutes=140 + i,
            session_id=sess_b, plan_id="PLAN-081",
            tokens_in=120000, tokens_out=40000, tokens_total=160000,
        ))
    files.append(("audit-log-002.jsonl", r002, 1000))

    # ----- Rotation 003 — overlapping tail with 002 (the dedup challenge)
    # Last 5 events of r002 are mirrored into r003 head. Same canonical
    # payload, different hmac (chain reset). budget-summary must
    # canonicalize-and-dedup; otherwise these 5 events double-count.
    r003: List[Dict[str, Any]] = []
    overlap = r002[-5:]
    for ev in overlap:
        r003.append(dict(ev))  # same payload — dedup target

    # Then new content: PLAN-082 small chunk
    sess_c = "33333333-3333-3333-3333-333333333333"
    r003.append(_make_plan_transition(
        base_ts=base, offset_minutes=200, session_id=sess_c,
        plan_id="PLAN-082", to_status="executing",
    ))
    for i in range(15):
        r003.append(_make_agent_spawn(
            base_ts=base, offset_minutes=205 + i,
            session_id=sess_c, plan_id="PLAN-082",
            tokens_in=250000, tokens_out=110000, tokens_total=360000,
            desc=f"PLAN-082 spawn #{i+1} wave-2",
            wave="wave-2",
        ))
    files.append(("audit-log-003.jsonl", r003, 2000))

    # ----- Rotation 004 — Mixed plans + inference path
    # No explicit plan_id on spawns, but plan_status_transition seeds
    # PLAN-083 as executing for sess_d. budget-summary should infer.
    sess_d = "44444444-4444-4444-4444-444444444444"
    r004: List[Dict[str, Any]] = [
        _make_plan_transition(
            base_ts=base, offset_minutes=300, session_id=sess_d,
            plan_id="PLAN-083", to_status="executing",
        ),
    ]
    for i in range(10):
        # Deliberately omit plan_id to exercise inference path.
        ev = _make_agent_spawn(
            base_ts=base, offset_minutes=305 + i,
            session_id=sess_d, plan_id="PLAN-083",  # set, then remove
            tokens_in=200000, tokens_out=80000, tokens_total=280000,
            desc=f"PLAN-083 inferred spawn #{i+1} wave-0b",
            wave="wave-0b",
        )
        ev.pop("plan_id")
        r004.append(ev)
    # Wallclock + budget-pause events (do not contribute tokens)
    r004.append(_make_wallclock(
        base_ts=base, offset_minutes=320, session_id=sess_d, milestone="wave-0b-done",
    ))
    r004.append(_make_budget_pause(
        base_ts=base, offset_minutes=325, session_id=sess_d,
    ))
    files.append(("audit-log-004.jsonl", r004, 3000))

    # ----- Rotation 005 — PLAN-082 tail + an unattributable orphan
    # One event with no plan_id and no session transition → (unknown).
    sess_e = "55555555-5555-5555-5555-555555555555"
    r005: List[Dict[str, Any]] = [
        # No plan_status_transition for sess_e → orphan
        _make_agent_spawn(
            base_ts=base, offset_minutes=400,
            session_id=sess_e, plan_id="",  # will be popped
            tokens_in=100000, tokens_out=40000, tokens_total=140000,
            desc="orphan spawn (no plan)",
        ),
    ]
    r005[-1].pop("plan_id", None)
    # More PLAN-082 work
    for i in range(10):
        r005.append(_make_agent_spawn(
            base_ts=base, offset_minutes=410 + i,
            session_id=sess_c, plan_id="PLAN-082",
            tokens_in=180000, tokens_out=90000, tokens_total=270000,
            desc=f"PLAN-082 tail spawn #{i+1} wave-2",
            wave="wave-2",
        ))
    files.append(("audit-log-005.jsonl", r005, 4000))

    # ----- Active log — light recent activity
    sess_f = "66666666-6666-6666-6666-666666666666"
    active: List[Dict[str, Any]] = [
        _make_plan_transition(
            base_ts=base, offset_minutes=500, session_id=sess_f,
            plan_id="PLAN-083", to_status="executing",
        ),
    ]
    for i in range(5):
        active.append(_make_agent_spawn(
            base_ts=base, offset_minutes=505 + i,
            session_id=sess_f, plan_id="PLAN-083",
            tokens_in=140000, tokens_out=60000, tokens_total=200000,
            desc=f"PLAN-083 active spawn #{i+1} wave-0b",
            wave="wave-0b",
        ))
    for i in range(3):
        active.append(_make_pair_rail_case(
            base_ts=base, offset_minutes=520 + i,
            session_id=sess_f, plan_id="PLAN-083",
            tokens_in=50000, tokens_out=18000, tokens_total=68000,
        ))
    files.append(("audit-log.jsonl", active, 5000))

    # Write all files
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, events, chain_offset in files:
        write_file(out_dir / name, events, chain_offset)

    return {
        "files": [name for name, _, _ in files],
        "out_dir": str(out_dir),
        "overlap_event_count": 5,
        "expected_plans": ["PLAN-080", "PLAN-081", "PLAN-082", "PLAN-083"],
    }


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("out_dir")
    args = p.parse_args(argv)
    meta = build_fixture_set(Path(args.out_dir))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
