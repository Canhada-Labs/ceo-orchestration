---
name: observability-and-ops
description: Designing observability into systems from the start, including
  metrics, health checks, staleness detection, quality signals,
  admin dashboards, and operational alerts. Use when designing admin panels,
  health monitoring, quality enforcement, system diagnostics, adding metrics
  to existing code, setting up alerts, building status pages, or debugging
  production issues. Also use when the user mentions "health check",
  "monitoring", "alerting", "metrics", "dashboard", or "staleness".
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
