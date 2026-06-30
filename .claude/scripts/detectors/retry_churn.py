"""PLAN-047 Phase 1 — retry_churn detector.

Heuristic: when the CEO spawns the same ``(session_id, subagent_type,
skill, prompt_len_bucket)`` combination ≥3 times within a rolling
30-minute window, this often indicates blind-retry-on-failure instead
of root-causing what broke — the same sub-agent is asked the same
shape of question repeatedly. Advisory: investigate root cause.

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per offending group.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .schema import Finding, emit_findings, is_agent_spawn, iter_events, parse_ts


_DETECTOR = "retry_churn"
_DEFAULT_THRESHOLD = 3
_DEFAULT_WINDOW_MINUTES = 30


def _group_key(event: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(event.get("session_id") or ""),
        str(event.get("subagent_type") or ""),
        str(event.get("skill") or ""),
        str(event.get("prompt_len_bucket") or ""),
    )


def detect(
    log_path: Path,
    *,
    threshold: int = _DEFAULT_THRESHOLD,
    window_minutes: int = _DEFAULT_WINDOW_MINUTES,
) -> List[Finding]:
    window = timedelta(minutes=window_minutes)
    groups: Dict[Tuple[str, str, str, str], List[Tuple[datetime, Dict[str, Any]]]] = defaultdict(list)

    for event in iter_events(log_path):
        if not is_agent_spawn(event):
            continue
        ts = parse_ts(event)
        if ts is None:
            continue
        key = _group_key(event)
        if not key[0] or not key[1]:
            # session_id or subagent_type missing → cannot correlate
            continue
        groups[key].append((ts, event))

    findings: List[Finding] = []
    for key, entries in groups.items():
        entries.sort(key=lambda pair: pair[0])
        # sliding window over sorted entries
        best_window: List[Tuple[datetime, Dict[str, Any]]] = []
        left = 0
        for right in range(len(entries)):
            while entries[right][0] - entries[left][0] > window:
                left += 1
            span = entries[left : right + 1]
            if len(span) > len(best_window):
                best_window = span
        if len(best_window) < threshold:
            continue
        session_id, subagent_type, skill, bucket = key
        spans = [entry[1]["desc_hash"] for entry in best_window if entry[1].get("desc_hash")]
        finding = Finding(
            detector=_DETECTOR,
            severity="warning",
            session_id=session_id,
            evidence={
                "subagent_type": subagent_type,
                "skill": skill,
                "prompt_len_bucket": bucket,
                "window_minutes": window_minutes,
                "spawn_count": len(best_window),
                "first_ts": best_window[0][0].isoformat(),
                "last_ts": best_window[-1][0].isoformat(),
            },
            recommendation=(
                "≥{count} spawns of {subagent} on {skill} within {window}min "
                "— investigate root cause instead of retrying.".format(
                    count=len(best_window),
                    subagent=subagent_type,
                    skill=skill,
                    window=window_minutes,
                )
            ),
            audit_spans=spans,
        )
        findings.append(finding)
    return findings


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="retry_churn")
    parser.add_argument("--log", required=True, help="path to audit-log.jsonl")
    parser.add_argument("--output", default=None, help="optional JSONL output path")
    parser.add_argument("--threshold", type=int, default=_DEFAULT_THRESHOLD)
    parser.add_argument("--window-minutes", type=int, default=_DEFAULT_WINDOW_MINUTES)
    args = parser.parse_args()
    findings = detect(
        Path(args.log),
        threshold=args.threshold,
        window_minutes=args.window_minutes,
    )
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
