"""PLAN-047 Phase 1 — tool_cascade detector.

NOTE: audit-log.jsonl records ``Agent`` spawns (``action="agent_spawn"``);
it does NOT record Read/Grep/Bash directly from the CEO turn. So the
classic "tool cascade" pattern is re-interpreted here as a long chain
of spawns with short object responses — a common shape when the CEO
is doing exploratory research via sub-agents instead of using direct
tools or a single wider-scope spawn.

Heuristic: within a single ``session_id``, find a run of ≥5
consecutive (time-ordered) ``agent_spawn`` events where
``response_kind == "object"`` AND ``tokens_out < 500``. Advisory:
"multiple exploratory spawns — consider batching or direct-tool use".

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per offending run.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .schema import Finding, emit_findings, is_agent_spawn, iter_events, parse_ts


_DETECTOR = "tool_cascade"
_DEFAULT_RUN_LEN = 5
_DEFAULT_TOKEN_CAP = 500


def _is_short_object(event: Dict[str, Any], token_cap: int) -> bool:
    if event.get("response_kind") != "object":
        return False
    tokens_out = event.get("tokens_out")
    if tokens_out is None:
        # missing telemetry is treated as "unknown" → not eligible (fail-safe)
        return False
    try:
        return int(tokens_out) < token_cap
    except (TypeError, ValueError):
        return False


def detect(
    log_path: Path,
    *,
    run_len: int = _DEFAULT_RUN_LEN,
    token_cap: int = _DEFAULT_TOKEN_CAP,
) -> List[Finding]:
    by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in iter_events(log_path):
        if not is_agent_spawn(event):
            continue
        if parse_ts(event) is None:
            continue
        sid = str(event.get("session_id") or "")
        if not sid:
            continue
        by_session[sid].append(event)

    findings: List[Finding] = []
    for sid, events in by_session.items():
        events.sort(key=lambda e: parse_ts(e))
        run: List[Dict[str, Any]] = []
        for event in events:
            if _is_short_object(event, token_cap):
                run.append(event)
                continue
            if len(run) >= run_len:
                findings.append(_build_finding(sid, run, run_len, token_cap))
            run = []
        if len(run) >= run_len:
            findings.append(_build_finding(sid, run, run_len, token_cap))
    return findings


def _build_finding(
    session_id: str,
    run: List[Dict[str, Any]],
    run_len: int,
    token_cap: int,
) -> Finding:
    spans = [event["desc_hash"] for event in run if event.get("desc_hash")]
    estimated_wasted = sum(int(event.get("tokens_total") or 0) for event in run)
    return Finding(
        detector=_DETECTOR,
        severity="warning",
        session_id=session_id,
        evidence={
            "run_length": len(run),
            "run_len_threshold": run_len,
            "token_cap_per_event": token_cap,
            "first_ts": run[0]["ts"],
            "last_ts": run[-1]["ts"],
        },
        recommendation=(
            "{n} consecutive short-response spawns in session {sid} — "
            "consider batching into a wider-scope spawn or using direct "
            "tools (Grep/Read) from the CEO turn.".format(
                n=len(run), sid=session_id
            )
        ),
        audit_spans=spans,
        estimated_wasted_tokens=estimated_wasted,
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="tool_cascade")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--run-len", type=int, default=_DEFAULT_RUN_LEN)
    parser.add_argument("--token-cap", type=int, default=_DEFAULT_TOKEN_CAP)
    args = parser.parse_args()
    findings = detect(
        Path(args.log),
        run_len=args.run_len,
        token_cap=args.token_cap,
    )
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
