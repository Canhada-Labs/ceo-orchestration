"""PLAN-047 Phase 1 — wasteful_thinking detector.

Heuristic: any ``agent_spawn`` on Opus (``claude-opus-4-8`` / ``-4-7``) AND
``prompt_len_bucket`` in the small buckets (``"<256"`` or ``"<1024"``)
AND ``subagent_type`` NOT in the hardcoded VETO floor
(``code-reviewer`` / ``security-engineer``). Opus on a short task that
does not need VETO authority is typically over-provisioned — Sonnet
would have been sufficient.

Aggregates by ``session_id``; each session with ≥1 offending event
produces a single Finding with a per-subagent breakdown in evidence.

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per session with offending spawns.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .schema import Finding, emit_findings, is_agent_spawn, iter_events


_DETECTOR = "wasteful_thinking"
_TARGET_MODELS = frozenset({"claude-opus-4-8", "claude-opus-4-7"})  # 4-7 kept for historical-log replay (ADR-142)
_SHORT_BUCKETS = frozenset({"<256", "<1024"})
_VETO_SUBAGENTS = frozenset({"code-reviewer", "security-engineer"})


def _is_offending(event: Dict[str, Any]) -> bool:
    if event.get("model") not in _TARGET_MODELS:
        return False
    if event.get("prompt_len_bucket") not in _SHORT_BUCKETS:
        return False
    subagent = str(event.get("subagent_type") or "")
    if subagent in _VETO_SUBAGENTS:
        return False
    if not subagent:
        return False
    return True


def detect(log_path: Path) -> List[Finding]:
    by_session: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in iter_events(log_path):
        if not is_agent_spawn(event):
            continue
        if not _is_offending(event):
            continue
        sid = str(event.get("session_id") or "")
        by_session[sid].append(event)

    findings: List[Finding] = []
    for sid, events in sorted(by_session.items()):
        subagent_counts: Counter = Counter(
            str(event.get("subagent_type") or "") for event in events
        )
        bucket_counts: Counter = Counter(
            str(event.get("prompt_len_bucket") or "") for event in events
        )
        wasted = sum(int(event.get("tokens_total") or 0) for event in events)
        findings.append(
            Finding(
                detector=_DETECTOR,
                severity="info",
                session_id=sid or None,
                evidence={
                    "spawn_count": len(events),
                    "subagent_counts": dict(subagent_counts),
                    "bucket_counts": dict(bucket_counts),
                },
                recommendation=(
                    "{n} Opus spawns on short non-VETO tasks in session "
                    "{sid} — consider downshifting to Sonnet for "
                    "non-critical subagents.".format(
                        n=len(events), sid=sid or "<unknown>"
                    )
                ),
                audit_spans=[event["desc_hash"] for event in events if event.get("desc_hash")],
                estimated_wasted_tokens=wasted,
            )
        )
    return findings


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="wasteful_thinking")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    findings = detect(Path(args.log))
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
