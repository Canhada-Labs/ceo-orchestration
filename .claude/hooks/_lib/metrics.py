"""Framework health metrics — derived from audit-log event stream.

PLAN-004 Phase 6. Computes counters, gauges, and histograms from the
append-only JSONL log. No separate metric store — everything derives
from `iter_events()` at query time. This keeps the stream as single
source of truth and lets any consumer re-derive without drift.

Usage:

    from _lib import metrics
    snapshot = metrics.compute(iter_events_fn)
    # Returns Dict[str, Union[int, float, Dict[str, int]]]

The snapshot is a flat dict of named metrics. Labels are encoded as
nested dicts per-metric. Consumers (dashboard, `audit-query.py metrics`)
render or serialize as they like.

## Stdlib-only

No numpy, no pandas. Counters are `int`, gauges are `float`,
histograms are pre-bucketed `Dict[str, int]`.
"""

from __future__ import annotations

import statistics
from typing import Any, Callable, Dict, Iterable, List, Optional

_EventsFn = Callable[[], Iterable[Dict[str, Any]]]


def compute(events_fn: _EventsFn) -> Dict[str, Any]:
    """Compute the canonical metric snapshot from a stream of events.

    Args:
        events_fn: zero-arg callable that returns an iterable of event
            dicts. Typically `lambda: audit_emit.iter_events()`.

    Returns:
        Flat dict of named metrics. Per-label metrics are nested dicts.
    """
    events = list(events_fn())

    # Counters
    spawn_total = 0
    veto_total = 0
    debate_total = 0
    plan_transition_total = 0
    benchmark_total = 0
    lesson_total = 0

    # Labeled counters
    veto_by_hook: Dict[str, int] = {}
    veto_by_reason: Dict[str, int] = {}
    plan_by_status: Dict[str, int] = {}  # "from→to"
    spawn_by_skill: Dict[str, int] = {}
    # PLAN-025 F-obs-003 — ADR-052 multi-model dispatch forensic trail.
    # audit_log v2.8 adds `model` field per agent_spawn; metrics must
    # aggregate it alongside skill so cost + policy audits can compute
    # per-model spawn counts without re-scanning the log.
    spawn_by_model: Dict[str, int] = {}
    bench_by_skill: Dict[str, int] = {}
    lesson_by_archetype: Dict[str, int] = {}

    # Histograms / distributions
    bench_pass_rates: List[float] = []
    spawn_compliance: Dict[str, int] = {"compliant": 0, "missing_profile": 0, "missing_file_assignment": 0}
    hook_durations: List[int] = []

    for ev in events:
        action = ev.get("action")

        if action == "agent_spawn":
            spawn_total += 1
            skill = ev.get("skill") or "unknown"
            spawn_by_skill[skill] = spawn_by_skill.get(skill, 0) + 1
            # PLAN-025 F-obs-003: aggregate model field (ADR-052; audit_log v2.8).
            # Entries from pre-v2.8 logs have no `model` key; treat as "unknown_model".
            model = ev.get("model") or "unknown_model"
            spawn_by_model[model] = spawn_by_model.get(model, 0) + 1
            if ev.get("has_profile") and ev.get("has_file_assignment"):
                spawn_compliance["compliant"] += 1
            elif not ev.get("has_profile"):
                spawn_compliance["missing_profile"] += 1
            elif not ev.get("has_file_assignment"):
                spawn_compliance["missing_file_assignment"] += 1
            dur = ev.get("hook_duration_ms")
            if isinstance(dur, int):
                hook_durations.append(dur)

        elif action == "veto_triggered":
            veto_total += 1
            hook = ev.get("hook") or "unknown"
            reason = ev.get("reason_code") or "unknown"
            veto_by_hook[hook] = veto_by_hook.get(hook, 0) + 1
            veto_by_reason[reason] = veto_by_reason.get(reason, 0) + 1

        elif action == "debate_event":
            debate_total += 1

        elif action == "plan_transition":
            plan_transition_total += 1
            transition = f"{ev.get('from_status', '?')}→{ev.get('to_status', '?')}"
            plan_by_status[transition] = plan_by_status.get(transition, 0) + 1

        elif action == "benchmark_run":
            benchmark_total += 1
            skill = ev.get("skill") or "unknown"
            bench_by_skill[skill] = bench_by_skill.get(skill, 0) + 1
            # Prefer new int-encoded field (bps ÷ 1000 → float); fall back
            # to legacy float field for logs predating the migration.
            bps = ev.get("pass_rate_bps")
            if bps is not None:
                bench_pass_rates.append(int(bps) / 1000.0)
            else:
                pr = ev.get("pass_rate")
                if isinstance(pr, (int, float)):
                    bench_pass_rates.append(float(pr))

        elif action == "lesson_write":
            lesson_total += 1
            archetype = ev.get("archetype") or "unknown"
            lesson_by_archetype[archetype] = lesson_by_archetype.get(archetype, 0) + 1

    # Derived gauges
    spawn_compliance_rate = 0.0
    if spawn_total > 0:
        spawn_compliance_rate = spawn_compliance["compliant"] / spawn_total

    hook_duration_p95 = 0
    if hook_durations:
        hook_durations_sorted = sorted(hook_durations)
        idx = max(0, int(len(hook_durations_sorted) * 0.95) - 1)
        hook_duration_p95 = hook_durations_sorted[idx]

    benchmark_pass_rate_mean = 0.0
    if bench_pass_rates:
        benchmark_pass_rate_mean = statistics.mean(bench_pass_rates)
    benchmark_pass_rate_min = 0.0
    if bench_pass_rates:
        benchmark_pass_rate_min = min(bench_pass_rates)

    return {
        # Counters
        "spawn_total": spawn_total,
        "veto_total": veto_total,
        "debate_event_total": debate_total,
        "plan_transition_total": plan_transition_total,
        "benchmark_run_total": benchmark_total,
        "lesson_write_total": lesson_total,
        # Labeled counters
        "veto_by_hook": veto_by_hook,
        "veto_by_reason_code": veto_by_reason,
        "plan_transitions_by_status": plan_by_status,
        "spawn_by_skill": spawn_by_skill,
        "spawn_by_model": spawn_by_model,
        "benchmark_by_skill": bench_by_skill,
        "lesson_by_archetype": lesson_by_archetype,
        # Gauges
        "spawn_compliance_rate": round(spawn_compliance_rate, 4),
        "spawn_compliance_breakdown": spawn_compliance,
        "hook_duration_ms_p95": hook_duration_p95,
        "benchmark_pass_rate_mean": round(benchmark_pass_rate_mean, 4),
        "benchmark_pass_rate_min": round(benchmark_pass_rate_min, 4),
        # Totals
        "events_total": len(events),
    }


def health_from_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate health thresholds and return {status, impact, findings}.

    Mirrors the observability-and-ops skill's health check contract:
    `{status: healthy|degraded|unhealthy, impact: ..., findings: [...]}`.
    """
    findings: List[Dict[str, Any]] = []

    # Spawn compliance SLO
    compliance = snapshot.get("spawn_compliance_rate", 1.0)
    if snapshot.get("spawn_total", 0) > 0:
        if compliance < 0.9:
            findings.append({
                "name": "spawn_compliance_rate_low",
                "status": "fail",
                "value": compliance,
                "threshold": 0.9,
                "impact": "governance erosion — persona/file-assignment not loaded",
                "remediation": "review agent spawn prompts; ensure ## AGENT PROFILE and ## FILE ASSIGNMENT present",
            })
        elif compliance < 0.95:
            findings.append({
                "name": "spawn_compliance_rate_below_slo",
                "status": "warn",
                "value": compliance,
                "threshold": 0.95,
                "impact": "some spawns are generic (missing skill context)",
                "remediation": "audit latest non-compliant spawns via audit-query.py",
            })

    # Hook latency SLO
    p95 = snapshot.get("hook_duration_ms_p95", 0)
    if p95 > 50:
        findings.append({
            "name": "hook_duration_p95_high",
            "status": "warn",
            "value": p95,
            "threshold": 50,
            "impact": "lock contention or slow hook — user perceives lag",
            "remediation": "check audit-log.errors for lock timeouts; run benchmark on hooks",
        })

    # Benchmark floor
    min_pass = snapshot.get("benchmark_pass_rate_min", 1.0)
    if snapshot.get("benchmark_run_total", 0) > 0 and min_pass < 0.6:
        findings.append({
            "name": "benchmark_below_floor",
            "status": "fail",
            "value": min_pass,
            "threshold": 0.6,
            "impact": "skill regression — benchmark below absolute floor",
            "remediation": "inspect failing benchmark; write Reflexion lesson; consider skill content update",
        })

    # Overall status
    status = "healthy"
    if any(f["status"] == "fail" for f in findings):
        status = "unhealthy"
    elif any(f["status"] == "warn" for f in findings):
        status = "degraded"

    impact = "NONE"
    if status == "unhealthy":
        impact = "governance or quality degraded — investigate findings"
    elif status == "degraded":
        impact = "advisory warnings present — review when convenient"

    return {
        "status": status,
        "impact": impact,
        "findings": findings,
    }
