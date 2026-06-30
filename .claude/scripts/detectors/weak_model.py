"""PLAN-047 Phase 1 — weak_model detector.

Heuristic: any ``agent_spawn`` where ``model == "claude-haiku-4-5"``
AND ``subagent_type`` ∈ the hardcoded VETO floor (``code-reviewer`` /
``security-engineer``). This is a governance-floor violation attempt:
ADR-052 hardcodes Opus-4-7 for VETO roles regardless of tier-policy
learning. ``check_tier_policy.py`` + the kernel-layer VETO wiring
should make this case impossible, but the detector exists as
defense-in-depth to catch any slip at the audit layer.

Advisory: "Haiku on VETO role — governance violation or schema
misclassification".

Severity is "warning" (higher than wasteful_thinking) — this is
not a cost signal, it is a governance signal.

Input: path to audit-log JSONL.
Output: ``List[Finding]`` — one per session with offending spawns.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from .schema import Finding, emit_findings, is_agent_spawn, iter_events


_DETECTOR = "weak_model"
_WEAK_MODEL = "claude-haiku-4-5"
_VETO_SUBAGENTS = frozenset({"code-reviewer", "security-engineer"})


def _is_offending(event: Dict[str, Any]) -> bool:
    if event.get("model") != _WEAK_MODEL:
        return False
    subagent = str(event.get("subagent_type") or "")
    return subagent in _VETO_SUBAGENTS


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
        findings.append(
            Finding(
                detector=_DETECTOR,
                severity="warning",
                session_id=sid or None,
                evidence={
                    "spawn_count": len(events),
                    "subagent_counts": dict(subagent_counts),
                    "weak_model": _WEAK_MODEL,
                },
                recommendation=(
                    "{n} Haiku spawn(s) on VETO role(s) in session {sid} — "
                    "investigate: governance-floor violation or schema "
                    "misclassification. Expected Opus 4.8 on "
                    "code-reviewer/security-engineer.".format(
                        n=len(events), sid=sid or "<unknown>"
                    )
                ),
                audit_spans=[event["desc_hash"] for event in events if event.get("desc_hash")],
            )
        )
    return findings


def _cli() -> int:
    parser = argparse.ArgumentParser(prog="weak_model")
    parser.add_argument("--log", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    findings = detect(Path(args.log))
    emit_findings(findings, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
