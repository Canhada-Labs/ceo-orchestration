---
name: observability-and-ops
description: Designing observability into systems from the start, including
  metrics, health checks, staleness detection, quality signals,
  admin dashboards, and operational alerts. Use when designing admin panels,
  health monitoring, quality enforcement, system diagnostics, adding metrics
  to existing code, setting up alerts, building status pages, or debugging
  production issues. Also use when the user mentions "health check",
  "monitoring", "alerting", "metrics", "dashboard", or "staleness".
owner: VP Operations (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-sre.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/support/support-infrastructure-maintainer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: []
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)observ|metric|logging|tracing"}
---

# Observability and Ops

## Fail-Fast Rule

If any mandatory invariant, validation, or precondition fails, **stop and
return a structured failure**. Never guess, infer, smooth, approximate,
or "fix" business-critical data.

## Cardinal Rule

If you can't observe it, you can't operate it. Every critical path must
emit metrics, every failure must be logged with context, and every
assumption must have a health check that validates it.

## Three Pillars

### Metrics (What is happening?)

Prometheus-style metrics. Required for any production system:

```typescript
// Counters
metrics.counter('feed.events_received', { source, dataset });
metrics.counter('feed.events_rejected', { source, dataset, reason });
metrics.counter('feed.processing_errors', { dataset, error_type });
metrics.counter('ws.reconnects', { source, attempt });
metrics.counter('api.requests', { endpoint, status_code });
metrics.counter('entity.normalization_failures', { source, raw_id });
metrics.counter('state.transitions', { entity, from, to, reason });

// Gauges
metrics.gauge('feed.data_age_ms', age, { source, dataset });
metrics.gauge('feed.active_sessions', count, { source });
metrics.gauge('worker_queue_depth', count, { queue });
metrics.gauge('ws.active_connections', count, { source });
metrics.gauge('cache.entries', count);

// Histograms
metrics.histogram('feed.processing_latency_ms', duration, { source });
metrics.histogram('api.response_time_ms', duration, { endpoint });
```

Naming: `<domain>.<metric_name>` with labels. Snake_case. Consistent.

### Logs (What happened?)

Structured JSON logs:

```typescript
interface LogEntry {
  timestamp: string;     // ISO 8601
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  context: {
    source?: string;     // upstream integration name
    dataset?: string;    // entity or data scope
    component?: string;
    correlationId?: string;  // trace across components
    [key: string]: any;
  };
  error?: { name: string; message: string; stack?: string; };
}
```

Rules:
- Log at boundaries: data enters/exits a component.
- Include enough context to reproduce without reading code.
- Never log API keys or secrets.
- **Every log must have a correlationId** when tracing across components.
- Levels used consistently:
  - `debug`: Development only.
  - `info`: Normal ops (startup, connection, config).
  - `warn`: Unexpected but handled (stale, fallback, retry).
  - `error`: Unexpected and harmful (corruption, unhandled exception).

### Health Checks (Is it working?)

Active validation that the system operates correctly.

## Health Check Design

### Endpoint: `GET /health`

```typescript
interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  checks: HealthCheck[];
  impact: HealthImpact;
}

interface HealthCheck {
  name: string;
  status: 'pass' | 'warn' | 'fail';
  message: string;
  lastChecked: string;
  metadata?: Record<string, any>;
}
```

### Health Impact

Health is not just green/red. It must declare **what functionality is
affected**:

```typescript
type HealthImpact =
  | 'NONE'              // all systems go
  | 'READ_DEGRADED'     // reads work but stale/partial
  | 'READ_ONLY'         // can read data, cannot write
  | 'WRITES_DISABLED'   // no mutations possible
  | 'FULL_OUTAGE';      // nothing works
```

Every health response must answer: **"What should be disabled right now?"**

### Required Health Checks

| Check | Pass | Warn | Fail |
|---|---|---|---|
| Upstream connectivity | All connected | 1+ disconnected | All disconnected |
| Data freshness | All < threshold | 1+ stale | All stale |
| Schema consistency | No drift | — | Mixed schemas found |
| Cache integrity | All keys valid | — | Invalid keys |
| Rate limit headroom | > 30% remaining | < 30% | Exhausted |
| Sequence gaps | None | Recovering | Persistent |
| Memory usage | < 70% | 70-90% | > 90% |

### Per-Source Health

```typescript
interface SourceHealth {
  source: string;       // upstream integration name
  connectionState: ConnectionState;
  lastMessageAt: number | null;
  staleDatasets: string[];
  reconnectCount: number;
  rateLimit: { used: number; limit: number; resetAt: number; };
}
```

## Staleness Detection

```typescript
class StalenessMonitor {
  private lastUpdate: Map<string, number> = new Map();

  onUpdate(key: string): void {
    this.lastUpdate.set(key, Date.now());
  }

  getStaleEntries(thresholdMs: number): StaleEntry[] {
    const now = Date.now();
    const stale: StaleEntry[] = [];
    for (const [key, lastSeen] of this.lastUpdate) {
      const age = now - lastSeen;
      if (age > thresholdMs) {
        stale.push({ key, ageMs: age, lastSeen });
      }
    }
    return stale;
  }

  check(): void {
    const stale = this.getStaleEntries(STALENESS_THRESHOLD);
    metrics.gauge('feed.stale_datasets', stale.length);
    for (const entry of stale) {
      metrics.gauge('feed.data_age_ms', entry.ageMs, { key: entry.key });
    }
    if (stale.length > 0) {
      logger.warn('stale_data_detected', {
        count: stale.length,
        datasets: stale.map(s => s.key),
        oldest_age_ms: Math.max(...stale.map(s => s.ageMs)),
      });
    }
  }
}
```

### Per-Source Thresholds

Different upstream integrations have different expected latencies — slow
providers need wider thresholds than fast ones.

```typescript
const STALENESS_THRESHOLDS: Record<string, number> = {
  upstream_fast_a: 5_000,
  upstream_fast_b: 5_000,
  upstream_fast_c: 5_000,
  upstream_slow_a: 30_000,
  upstream_slow_b: 30_000,
  default: 10_000,
};
```

## Alerting Rules

### Critical (Page immediately)

- All upstream integrations disconnected
- All datasets stale > 2× threshold
- Schema drift detected
- Corrupt aggregate detected
- Unhandled exception in data plane

### Warning (Notify, don't page)

- Single upstream integration disconnected > 60s
- Reconnect attempts > 5 without success
- Rate limit budget < 20%
- Single dataset stale > 3× threshold

### Info (Log only)

- Upstream reconnected successfully
- Config reloaded
- Shadow mode mismatch detected

### Alert Quality Rule

**Every alert must be understandable by someone who did not write the code.**
Alerts must include: what happened, what's affected, suggested action.

```typescript
// BAD
alert('aggregation_error', { code: 'E_SCHEMA' });

// GOOD
alert('aggregation_error', {
  summary: 'Schema mismatch in PRODUCT-A aggregated view',
  affected: 'PRODUCT-A dashboard',
  detail: 'Upstream integration B returned a renamed column that mixed into PRODUCT-A aggregation',
  action: 'Check integration B adapter config. Source excluded automatically.',
});
```

## Admin Dashboard Panels

### System Overview

- Status indicator (healthy / degraded / unhealthy)
- Current health impact level
- Uptime, active sources, total/stale datasets

### Per-Source

- Connection state + last message age
- Reconnect count in last hour
- Rate limit usage bar
- Active subscriptions

### Per-Dataset

- Data age (green < 5s, yellow < 30s, red > 30s)
- Current aggregate values
- Row/record counts per source
- Sources contributing to aggregated view

### Data Quality

- Schema consistency pass/fail per entity
- Sequence gap events in last hour
- Normalization failure rate
- Validation rejection rate + top reasons

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `console.log` in production | Unstructured, no context | Structured logger with levels |
| Health check always returns 200 | Hides failures | Check real invariants |
| Alerting on every error | Alert fatigue | Threshold-based with severity |
| Metrics without labels | Can't drill down | Include source, dataset, component |
| Monitoring added after launch | Misses early issues | Built into initial implementation |
| Single staleness threshold | Ignores source differences | Per-source thresholds |
| Green dashboard, broken data | Wrong metric is worse than no metric | Validate what you measure |
| Alert without suggested action | Noise for operators | Every alert includes action |
| Logs without correlationId | Debug impossible across components | Trace ID on every log |

## Known Pitfalls (Lessons From Real Incidents)

- **NEVER trust warm-up logs to validate perf changes** — steady-state workload (5min+) creates much larger batches than startup.
- **Time-bucketed trackers are often minute-aligned** — a getHistory(hours: X) cutoff MUST be > 60s (hours > 0.017) or it will return an empty window.
- **`--no-tail` log commands often return only ~100 lines** — use streaming logs or grep for real debugging.
- **SLO freshness breaches are normal for the first 5-10min after deploy** — cold start fills caches gradually. Don't page on startup staleness.
- **Health endpoints can lie:** a trivial `/healthz` may return OK while the main process HTTP is unresponsive. Fix: `/healthz` must check real metrics (active sessions, event loop latency, memory).
## Adopter Note — Metric Names + Architecture Bias (PLAN-044 P0-12)

The §Three Pillars / §Metrics block enumerates concrete
Prometheus metric names (`feed.events_received`, `feed.events_
rejected`, `feed.processing_errors`, `ws.reconnects`, `entity.
normalization_failures`, `state.transitions`, `feed.data_age_
ms`, `feed.active_sessions`, `ws.active_connections`) drawn
from the originating `ceo-orchestration` dogfood ingestion
engine — a WebSocket-fed entity-normalisation pipeline.

Those metric names are **illustrative**. The patterns they
exemplify (counter for every observable event, gauge for every
observable level, histogram for every observable latency-like
value, labels for cardinality you care about) transfer to any
service. The specific names (`feed.*` / `ws.*` / `entity.*`)
should be renamed to fit your domain (e.g. `http.*` / `db.*` /
`job.*` for a web API, or `mq.*` / `batch.*` for a worker).

Likewise, the §Pitfalls section's `--no-tail` / `/healthz`
examples come from the dogfood project's operational log
culture — substitute your own log-tool invocations and your
own health-endpoint path when spawning this skill in an
adopter context. The observations (log commands can truncate
silently; health endpoints can be trivial and lie) are
universal; the tool names are not.

## SRE Error Budgets and SLO Mechanics

### What SLOs Are For

An SLO is a contractual statement that a specific SLI (Service Level
Indicator) will remain above a target value over a rolling window.
An error budget is the complement: the allowable quantity of bad
minutes, bad requests, or bad measurements before the target is
breached. These two quantities, not gut feeling, are the correct
basis for reliability investment decisions.

**NEVER define an SLO without specifying**: the SLI expression, the
measurement window, and the error-budget policy that activates when
the budget is exhausted.

### SLO Definition Rubric

Define at least one SLO per user-visible critical path. Four categories
cover most services:

| Category | SLI expression | Typical target | Notes |
|---|---|---|---|
| Availability | `count(non-5xx) / count(total)` | 99.9 – 99.99% | Exclude health-check probes from numerator and denominator |
| Latency | `count(duration < threshold) / count(total)` | 99% at p99 | Set threshold at the business-meaningful value, not a percentile of current distribution |
| Freshness | `count(data_age < max_age) / count(total_checks)` | 99.5% | Applies to any pipeline that must deliver data within a deadline |
| Quality | `count(valid_outputs) / count(total_outputs)` | 99% | Reject rate, schema-conformance rate, or normalization-success rate |

```yaml
# Minimal SLO declaration — extend as needed
slo:
  service: payment-processor
  name: Availability
  sli: count(status < 500) / count(total)
  target: 99.95
  window: 30d
  error_budget_policy: freeze_features
```

### Error-Budget Burn-Rate Alerts

A single threshold alert on the SLO percentage fires too late — a
service burning through budget slowly will page only after the month
is wasted. Pair a fast-burn alert (detects sudden drops) with a
slow-burn alert (detects gradual erosion):

```yaml
# Fast burn: at this rate, 2% of the 30d budget is consumed every hour
- name: availability_fast_burn
  condition: burn_rate_1h > 14.4 AND burn_rate_5m > 14.4
  severity: critical
  annotation: "Consuming 2% of 30d budget per hour (sustained ⇒ exhaust in ~50h); page on-call now"

# Medium burn: at this rate, 5% of the 30d budget is consumed in 6h
- name: availability_medium_burn
  condition: burn_rate_6h > 6.0 AND burn_rate_30m > 6.0
  severity: warning
  annotation: "Consuming 5% of 30d budget in 6h (sustained ⇒ exhaust in ~5d); investigate within 30min"

# Slow burn: at this rate, 10% of the 30d budget is consumed in 3d
- name: availability_slow_burn
  condition: burn_rate_3d > 1.0
  severity: info
  annotation: "Consuming 10% of 30d budget in 3d; review by next business day"
```

Burn rate is the multiplier on the tolerable error rate. At a 99.95%
target the budgeted error rate is 0.05% of requests; a burn rate of
14.4 means actual errors are running at 14.4 × 0.05% = 0.72% of
requests. Over a 1h window, that consumes (1h / 720h) × 14.4 ≈ 2% of
the 30-day budget; sustained, the full budget exhausts in roughly
50 hours. The multi-window thresholds (Google SRE Workbook ch.5)
are calibrated to consume 2% / 5% / 10% of the budget per
short / medium / long window — not to exhaust it inside the alert
window itself.

**DO NOT** alert only on the raw SLO percentage crossing the target.
By the time that fires, the budget for the rolling window is already
gone.

### Feature-Freeze Policy

When the error budget for a tier-1 SLO drops below **10% of the
monthly allocation** before the halfway point of the month, the
following rules apply until the budget recovers to 50% or the
month resets:

1. No new feature deployments to the affected service or its
   critical dependencies.
2. Changes classified as reliability work (instrumentation, circuit
   breakers, rollback improvements, retry hardening) are exempt.
3. Hotfixes to open SEV1/SEV2 incidents are always exempt.
4. The freeze is a policy, not a bureaucratic gate — the engineering
   team implements it; the SLO dashboard is the source of truth.

```
# CORRECT — applying the freeze
error_budget_consumed: 92% at day 14 of 30
action: freeze features; reliability sprint starts immediately

# WRONG — ignoring budget state
error_budget_consumed: 92% at day 14 of 30
action: ship the scheduled feature release anyway
```

### Toil vs Engineering Ratio

Toil is repetitive, automatable, tactical operational work that scales
linearly with service load. A team whose toil exceeds 50% of weekly
work is spending engineering capacity to stay still.

Targets:
- Toil below **50% of work** per engineer per week (floor, not goal)
- Active goal: toil below **30%** in steady state
- Anything above 50% for two consecutive weeks triggers a toil
  reduction sprint; no new feature work until the toil source is
  addressed

Track toil explicitly: log every repetitive operation performed
during on-call. If the same manual step appears more than twice
in a week across the team, it is a candidate for automation in the
next sprint.

## Operational Runbook Discipline

### What a Runbook Is (and Isn't)

A runbook is a **per-service, per-failure-mode** document that tells
an on-call engineer — who may be unfamiliar with this service —
exactly what to check, what to do, and when to escalate. It is NOT
a general guide to the service, NOT a design document, and NOT a
summary of past incidents.

Doctrine for the runbook process lives here. The runbooks themselves
live next to the service they cover (e.g. `services/payment-processor/
runbooks/`). A runbook that lives in a wiki and drifts from the deployed
code is worse than no runbook: it creates false confidence.

### Required Runbook Structure

Every runbook covers exactly one failure mode. If a single document
covers three failure modes, it is three runbooks improperly merged.

````markdown
# Runbook: <service> — <failure-mode-slug>

## Symptoms
<!-- Observable signals that trigger this runbook. -->
<!-- Match alert names verbatim so the on-call can find this via the page. -->
- Alert: `<alert-name>` fires when `<condition>`
- User-visible: <what the user sees>
- Dashboard: <panel name, what it looks like when wrong>

## Triage Checklist
<!-- Ordered steps. Run in order. Stop at the first step that identifies the cause. -->
1. <check command or link>; expected: <value>; if wrong: go to step N
2. ...

## Mitigations
<!-- One entry per mitigation. Include the exact command. -->
### Option A — Restart the worker
```shell
kubectl rollout restart deployment/<name> -n <namespace>
```
Expected recovery: <N> seconds. If not recovered in <2N> seconds, escalate.

### Option B — Roll back the last deploy
```shell
<rollback command with exact flags>
```
Expected recovery: <N> minutes.

## Rollback Procedure
<!-- If mitigation fails entirely, how do you revert to last-known-good? -->

## Escalation Path
<!-- Who to call, in order, after <N> minutes without recovery. -->
1. On-call secondary — after 15 min without mitigation progress
2. Service owner — after 30 min or if rollback fails
3. Incident Commander — if impact is SEV1 and growing

## Last Validated
Date: YYYY-MM-DD
Validated by: <name or role>
Next required validation: YYYY-MM-DD
````

**DO NOT omit any section.** A runbook with "Escalation Path: TBD"
will be used during a 3am incident. "TBD" is not an escalation path.

### Runbook-as-Test: Quarterly Chaos Drills

A runbook that has never been executed against a real system is a
hypothesis, not a procedure. Each runbook must be validated at least
once per quarter in a controlled chaos drill:

1. Inject the failure mode the runbook covers (use a chaos tool, or
   manually apply the failure in a staging environment).
2. Have an engineer unfamiliar with the service follow the runbook
   step by step without assistance.
3. Measure: did the engineer identify the failure mode within the
   triage checklist? Did the mitigation work? Was the recovery time
   within the stated estimate?
4. Update the runbook immediately after the drill. If any step was
   wrong or missing, that is a finding — log it as an action item
   with an owner and a due date.

A runbook that fails its quarterly drill is quarantined (marked
`status: UNVALIDATED`) until the defects are corrected and a new
drill passes. An `UNVALIDATED` runbook must not be linked from
alert annotations.

### Runbook Drift Detection

The most common failure mode for runbooks is drift: the service
changes, the runbook does not. Mechanical drift detection:

- **Staleness gate:** Each runbook carries `Last Validated` and
  `Next required validation` dates. A CI job or cron check
  asserts `next_validation > today`. Failure blocks the release
  of the service, not the runbook.
- **Command validation:** Triage commands that reference specific
  resource names (deployment names, namespace names, metric labels)
  are validated in integration tests against the live cluster.
  A command pointing at a renamed deployment fails the check before
  a real incident surfaces the drift.
- **Alert-name matching:** The `Symptoms` section must list alert
  names verbatim. A script compares the runbook alert names against
  the active Prometheus/Alertmanager rule set. Orphaned alert names
  (in the runbook but absent from rules) are reported as findings.

```
# WRONG — vague symptom description that drifts silently
Symptoms: The service might be slow or returning errors.

# CORRECT — exact alert name + observable signal
Symptoms:
  Alert: `payment_api_error_rate_high` fires when error rate > 5% for 90s
  User-visible: checkout fails with "Service unavailable"
  Dashboard: "Payment API / Error Rate" panel shows rate > 0.05
```

### Change-Freeze Windows

Runbooks must document the change-freeze rules for the service.
A deployment during an implicit high-risk window (end-of-quarter
batch settlements, peak trading hours, regulatory reporting deadlines)
that causes an incident is an avoidable failure.

For each service, define:

| Window type | Example | Default policy |
|---|---|---|
| Business-critical batch | Month-end settlement, payroll run | No deployments 4h before → 4h after |
| Peak load period | Market open/close, sale events | No deployments; auto-rollback if error rate spikes within 15min of last deploy |
| Regulatory deadline | Daily reporting submission | No deployments 2h before → submission confirmed |
| Post-incident freeze | Following any SEV1 | No feature deploys until post-incident action items scoped |

These windows are documented in the runbook's metadata block and
enforced either by a CI gate or by the on-call rotation's handoff
checklist. Enforcement mechanism MUST be named — "we don't deploy
during peak" with no gate is not enforcement.
