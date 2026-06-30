"""PLAN-047 Phase 1 — looping detector.

Heuristic: the same ``subagent_type`` is spawned ≥3 times within a
30-minute rolling window, all with ``has_file_assignment=True``, and
all sharing the same ``desc_hash`` prefix (first 8 hex chars). The
prefix match is a fuzzy proxy for "overlapping file_assignment or
similar task" — independent tasks would have different task
descriptions and therefore different hashes.

When this fires, the CEO's task description is likely not specific
enough and the sub-agent is being asked to do essentially the same
thing multiple times. Advisory: "Sub-agent looping detected; check
CEO prompt specificity".

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per offending (subagent, hash-prefix)
group.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .schema import Finding, emit_findings, is_agent_spawn, iter_events, parse_ts


_DETECTOR = "looping"
_DEFAULT_THRESHOLD = 3
_DEFAULT_WINDOW_MINUTES = 30
_DEFAULT_PREFIX_LEN = 8


def _desc_prefix(event: Dict[str, Any], length: int) -> str:
    raw = event.get("desc_hash") or ""
    return str(raw)[:length]


def detect(
    log_path: Path,
    *,
    threshold: int = _DEFAULT_THRESHOLD,
    window_minutes: int = _DEFAULT_WINDOW_MINUTES,
    prefix_len: int = _DEFAULT_PREFIX_LEN,
) -> List[Finding]:
    window = timedelta(minutes=window_minutes)
    groups: Dict[Tuple[str, str], List[Any]] = defaultdict(list)

    for event in iter_events(log_path):
        if not is_agent_spawn(event):
            continue
        if not event.get("has_file_assignment"):
            continue
        ts = parse_ts(event)
        if ts is None:
            continue
        prefix = _desc_prefix(event, prefix_len)
        if not prefix:
            continue
        subagent = str(event.get("subagent_type") or "")
        if not subagent:
            continue
        groups[(subagent, prefix)].append((ts, event))

    findings: List[Finding] = []
    for (subagent, prefix), entries in groups.items():
        entries.sort(key=lambda pair: pair[0])
        best: List[Any] = []
        left = 0
        for right in range(len(entries)):
            while entries[right][0] - entries[left][0] > window:
                left += 1
            span = entries[left : right + 1]
            if len(span) > len(best):
                best = span
        if len(best) < threshold:
            continue
        session_ids = sorted({str(entry[1].get("session_id") or "") for entry in best})
        findings.append(
            Finding(
                detector=_DETECTOR,
                severity="warning",
                session_id=session_ids[0] if len(session_ids) == 1 else None,
                evidence={
                    "subagent_type": subagent,
                    "desc_hash_prefix": prefix,
                    "window_minutes": window_minutes,
                    "spawn_count": len(best),
                    "session_ids": session_ids,
                    "first_ts": best[0][0].isoformat(),
                    "last_ts": best[-1][0].isoformat(),
                },
                recommendation=(
                    "{n} spawns of {subagent} with the same desc-hash prefix "
                    "({prefix}) — tighten CEO prompt specificity or split into "
                    "disjoint file assignments.".format(
                        n=len(best), subagent=subagent, prefix=prefix
                    )
                ),
                audit_spans=[entry[1]["desc_hash"] for entry in best if entry[1].get("desc_hash")],
            )
        )
    return findings


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="looping")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", default=None)
    parser.add_argument("--threshold", type=int, default=_DEFAULT_THRESHOLD)
    parser.add_argument("--window-minutes", type=int, default=_DEFAULT_WINDOW_MINUTES)
    parser.add_argument("--prefix-len", type=int, default=_DEFAULT_PREFIX_LEN)
    args = parser.parse_args()
    findings = detect(
        Path(args.log),
        threshold=args.threshold,
        window_minutes=args.window_minutes,
        prefix_len=args.prefix_len,
    )
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
