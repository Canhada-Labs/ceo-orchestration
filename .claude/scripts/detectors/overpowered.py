"""PLAN-047 Phase 1 — overpowered detector.

Heuristic: ``agent_spawn`` with ``model`` ∈ {Opus 4.8/4.7, Sonnet 4.6} AND
``subagent_type == "devops"`` AND ``prompt_len_bucket`` ∈ {"<256",
"<1024"}. Boilerplate devops (pipeline tweak, workflow SHA-pin,
yamllint fix) rarely needs Opus-class reasoning; Haiku is typically
sufficient and ~10-20× cheaper.

Advisory: "Sonnet/Opus on short devops spawn — Haiku would likely
have sufficed".

Aggregates by session_id with per-model breakdown in evidence.
Severity "info" (cost optimization, not governance).

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per session with offending spawns.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .schema import Finding, emit_findings, is_agent_spawn, iter_events


_DETECTOR = "overpowered"
_LARGE_MODELS = frozenset({"claude-opus-4-8", "claude-opus-4-7", "claude-sonnet-4-6"})
_TARGET_SUBAGENT = "devops"
_SHORT_BUCKETS = frozenset({"<256", "<1024"})


def _is_offending(event: Dict[str, Any]) -> bool:
    if event.get("model") not in _LARGE_MODELS:
        return False
    if event.get("subagent_type") != _TARGET_SUBAGENT:
        return False
    return event.get("prompt_len_bucket") in _SHORT_BUCKETS


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
        model_counts: Counter = Counter(
            str(event.get("model") or "") for event in events
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
                    "model_counts": dict(model_counts),
                    "bucket_counts": dict(bucket_counts),
                },
                recommendation=(
                    "{n} large-model devops spawn(s) on short prompts in "
                    "session {sid} — boilerplate devops rarely needs "
                    "Opus/Sonnet; Haiku would typically suffice.".format(
                        n=len(events), sid=sid or "<unknown>"
                    )
                ),
                audit_spans=[event["desc_hash"] for event in events if event.get("desc_hash")],
                estimated_wasted_tokens=wasted,
            )
        )
    return findings


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="overpowered")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    findings = detect(Path(args.log))
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
