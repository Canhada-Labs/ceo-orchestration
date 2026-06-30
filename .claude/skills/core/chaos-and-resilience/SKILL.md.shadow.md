---
name: chaos-and-resilience
description: Chaos engineering, resilience patterns, failure recovery, and fault
  tolerance for the {{PROJECT_NAME}}. Covers circuit breaker patterns (HTTP, WS,
  per-venue), reconnect gate design, graceful shutdown protocol, backpressure
  strategies (PubSub 1MB/4MB, persistence queues), worker lifecycle management, IPC
  channel health detection, failure scenario matrix, bounded queue design, and event
  loop stall recovery. Use when reviewing or writing any code that touches error
  handling, retry logic, reconnection, circuit breakers, worker management, IPC
  channels, queue management, backpressure, graceful shutdown, health checks, or
  any failure-adjacent code path.
owner: Chaos & Resilience Engineer (archetype)
---

# Chaos and Resilience

## Fail-Fast Rule

If a system component enters an unrecoverable state, **fail fast and loud**.
Never silently swallow errors in resilience-critical paths. Never assume
a retry will fix a structural problem. Never disable safety mechanisms
(watchdogs, circuit breakers) without a replacement.

## Current Resilience Posture (Audit 2026-03-23: 6.5/10)

### What Works

- Circuit breakers: 3 layers (HTTP, WS, per-venue)
- Reconnect gate: max 3 connections per 10s with jitter backoff
- Graceful shutdown: SIGINT/SIGTERM with 10s hard kill
- Adapter process auto-restart: 10x with exponential backoff
- PubSub backpressure: 1MB skip, 4MB force-close, slow-client detection
- EL monitoring: stall detector, iteration tracker, per-operation profiler

### What Does NOT Work

| Issue | Impact | File |
|-------|--------|------|
| IPC batch buffers UNBOUNDED | OOM then restart cascade then permanent death | adapter-process.ts:330-351 |
| BP watchdog DISABLED | Worker can hang indefinitely | adapter-process.ts:71 |
| Max restarts without recovery | After 10 crashes, dies permanently | gateway-wiring.ts |
| Supabase without circuit breaker | Flush workers waste CPU when Supabase is down | supabase-persistence.ts |
| unshift bypass in backpressure | Queues grow beyond cap | supabase-persistence.ts:877 |
| unhandledRejection not fatal | System in inconsistent state continues running | index.ts:2557 |

## Top 5 Failure Scenarios

### 1. IPC Silent Failure (CRITICAL)

```
IPC channel breaks silently
  → adapter-process keeps buffering events (UNBOUNDED)
  → buffer grows without limit
  → OOM kill after minutes/hours
  → auto-restart (up to 10x)
  → all 10 restarts fail (same root cause)
  → permanent death: zero events flowing, /healthz still returns 200
```

**Mitigation required:**
- Bounded IPC buffer (max N messages or M bytes)
- IPC heartbeat with health detection
- Buffer overflow: drop oldest, log, metric
- Restart counter reset after sustained healthy period

### 2. Supabase Outage (HIGH)

```
Supabase becomes unreachable
  → supabase-persistence flush fails
  → unshift() puts failed items back at queue front (bypasses cap)
  → queue grows without bound
  → memory growth over hours
  → eventual OOM
```

**Mitigation required:**
- Circuit breaker on Supabase flush workers
- Bounded queue with drop-oldest on overflow
- Never use unshift() to bypass queue cap
- Exponential backoff on consecutive failures

### 3. Adapter Max Restarts Exhausted (HIGH)

```
Adapter process crashes 10 times
  → max restarts reached
  → no more restart attempts
  → zero events flowing
  → system appears alive to your PaaS (e.g. Fly.io, Railway, Render, Heroku, AWS) (/healthz returns 200)
  → users see stale/empty data indefinitely
```

**Mitigation required:**
- Restart counter reset after N minutes of stability
- /healthz MUST check adapter process liveness and data freshness
- Alert on restart count approaching max
- Manual recovery endpoint for admin

### 4. Background Worker Permanent Stall (HIGH)

```
Background worker enters infinite loop or deadlock
  → watchdog is DISABLED (was killing worker during legitimate long stalls)
  → downstream aggregates, quality scores, derived metrics stop updating
  → fast path still delivers raw data (system appears partly functional)
  → quality scores frozen at last value
```

**Mitigation required:**
- Re-enable watchdog with longer timeout (120s instead of 30s)
- Heartbeat-based detection (worker sends periodic heartbeat)
- Graceful restart: drain in-flight work before kill
- Alert on stall detection

### 5. Event Loop Stall Positive Feedback Loop (MEDIUM)

```
Main thread EL stalls during IPC batch processing
  → IPC messages queue up during stall
  → next tick processes larger batch
  → larger batch causes longer stall
  → positive feedback loop
  → health checks timeout (CRITICAL)
```

**Mitigations (ACTIVE):**
- processFastChunk: max 80 events/tick, defer rest via setImmediate
- PubSub publish guarded by topicSubscriberCount (skip when 0)
- SSE broadcast guarded by activeClientCount (skip when 0)
- Date.now() cached per batch (not per event)
- Handler defers SSE + persistent writer to setImmediate
- Low-priority entities skipped on fast path (~60-75% IPC reduction)

## Circuit Breaker Patterns

### Layer 1: HTTP Circuit Breaker (module archetype)

Reusable for any HTTP client (data providers, third-party REST APIs).

```
State machine: CLOSED → OPEN → HALF_OPEN → CLOSED

CLOSED: requests flow normally
  → N consecutive failures → OPEN

OPEN: all requests rejected (shouldSkip() returns true)
  → cooldown expires → HALF_OPEN

HALF_OPEN: single probe request allowed
  → success → CLOSED (reset counter)
  → failure → OPEN (restart cooldown)

Special: 401/403 → PERMANENT MUTE (until restart)
```

Configuration:
- `threshold`: consecutive failures before trip (default: 5)
- `cooldownMs`: time in OPEN state (default: 300,000ms / 5min)

Current usage: CMC, CoinGecko, TwelveData, AlphaVantage, FRED,
LunarCrush, Unusual Whales, TRUF, Finnhub, BCB.

**Missing:** FinancialJuice, Chainlink, Pyth, Supabase flush workers.

### Layer 2: WebSocket Resilience (module archetype)

Per-source WebSocket connection management.

```
Connection lifecycle:
  CONNECTING → CONNECTED → SUBSCRIBED
    ↓ (error/close)                ↓ (error/close)
  RECONNECTING ←───────────────────┘
    ↓ (max retries)
  CIRCUIT_OPEN → (cooldown) → RECONNECTING
    ↓ (max circuit trips)
  DEAD
```

Reconnect gate: max 3 reconnections per 10s window with jitter.
Prevents reconnect storm when an upstream source has a systemic issue.

### Layer 3: Per-Source Monitor (module archetype)

Tracks per-source health across all connections.

```
Metrics tracked:
  - Connection count (active / total / failed)
  - Message rate (msgs/sec, events/sec)
  - Error rate (errors/min)
  - Latency p50/p95/p99
  - Last successful event timestamp

Health states:
  HEALTHY: all metrics nominal
  DEGRADED: >20% connections failed OR error rate >5/min
  UNHEALTHY: >50% connections failed OR zero events for 60s
  DEAD: all connections failed
```

### Circuit Breaker Rules

1. **Every external HTTP call MUST use a CircuitBreaker instance.**
2. **Circuit breakers MUST be per-service, not global.**
3. **OPEN state MUST be logged and metricked.**
4. **Permanent mute on 401/403 is correct** (prevents burning rate limits).
5. **Never disable a circuit breaker to "fix" a connectivity issue.**
6. **Probe requests in HALF_OPEN MUST be lightweight** (health endpoint, not full data fetch).

## Reconnect Gate Design

### Purpose

Prevent reconnect storms when an upstream source has a systemic issue.
Without a gate, N connections all reconnect simultaneously, causing
rate limit violations and cascading failures.

### Current Implementation

```typescript
// Max 3 reconnections per 10s window
// Jitter: random 0-2s added to backoff
// Exponential backoff: base * 2^attempt (capped at 60s)

interface ReconnectGate {
  maxReconnectsPerWindow: number;  // 3
  windowMs: number;                // 10,000
  baseBackoffMs: number;           // 1,000
  maxBackoffMs: number;            // 60,000
  jitterMs: number;                // 2,000
}
```

### Rules

1. **Gate is per-upstream, not global.** One upstream's reconnect does not block the others.
2. **Backoff MUST include jitter.** Without jitter, all connections retry at the same instant.
3. **Max backoff MUST be capped.** Unbounded backoff = never reconnects.
4. **Gate state MUST be observable** (admin endpoint, metrics).
5. **Manual override** for admin to force-reconnect past the gate.

## Graceful Shutdown Protocol

### Current Implementation

```
SIGINT or SIGTERM received
  → Set shutting_down flag
  → Stop accepting new connections
  → Close WS connections with 1001 (Going Away)
  → Drain in-flight HTTP requests (5s timeout)
  → Flush pending Supabase writes
  → Send IPC shutdown to adapter process
  → Wait for adapter process exit (5s timeout)
  → Hard kill after 10s total
```

### Rules

1. **In-flight business-critical mutations MUST complete before shutdown.**
2. **Never drop pending Supabase writes silently.** Flush or log what was lost.
3. **Health endpoint MUST return 503 during shutdown.**
4. **PaaS stop_signal: SIGINT, kill_timeout: 10s** (configure in whatever your PaaS uses — Fly.io `fly.toml`, Railway, Render, Heroku, AWS, etc.).
5. **Worker threads MUST handle shutdown signal** (not just main process).

## Backpressure Strategies

### PubSub Backpressure (module archetype)

```
Per-client buffer tracking:
  buffer < 1MB: normal publish
  buffer >= 1MB: SKIP this message (log, metric)
  buffer >= 4MB: FORCE-CLOSE the client (slow consumer detected)

Slow-client detection:
  If client accumulates >1MB backlog, it cannot keep up.
  Skipping messages is preferable to OOM.
  Force-close at 4MB prevents unbounded memory growth.
```

### Supabase Persistence Queue

```
Current (BROKEN):
  Flush fails → unshift() puts items back at front → bypasses queue cap
  → unbounded queue growth → OOM

Correct pattern:
  Flush fails → increment failure counter
  If consecutive failures < threshold:
    → exponential backoff retry
    → items stay at queue front (bounded retry buffer)
  If consecutive failures >= threshold:
    → circuit breaker OPEN
    → DROP items with logging (data loss > OOM)
    → alert admin
  Queue cap: hard MAX enforced on ALL paths (including unshift)
```

### IPC Backpressure

```
Current (BROKEN):
  adapter-process buffers IPC messages without bound
  If main process is slow, buffer grows to OOM

Correct pattern:
  Bounded buffer: MAX_IPC_BUFFER_SIZE (e.g., 10,000 messages or 100MB)
  When buffer full:
    → Drop low-priority events first
    → Then drop WARM records (keep latest per entity)
    → HOT records: always send (never drop)
  Metric: ipc_buffer_size, ipc_drops_total
  Alert: buffer > 80% capacity
```

### Backpressure Rules

1. **Every queue MUST have a hard maximum size.**
2. **Queue overflow MUST drop with logging, never block the producer.**
3. **Drop policy MUST be explicit:** oldest-first, lowest-tier-first, or random.
4. **unshift() and similar front-insert MUST respect the same cap.**
5. **Queue size MUST be observable** (metric, admin endpoint).

## Worker Lifecycle Management

### Worker Types

| Worker | Type | Location | Restart Policy |
|--------|------|----------|---------------|
| Adapter Process | child_process.fork or worker_threads | adapter-process.ts | 10x exponential backoff |
| State Worker | worker_threads | state-worker.ts | Restart on crash |
| Batch Worker | worker_threads (in adapter) | batch-worker.ts | Watchdog (DISABLED) |
| Pool Workers (N) | worker_threads (in adapter) | pool workers | Restart on crash |
| Mutation Worker | PaaS machine (e.g. Fly.io) | mutation-worker.ts | PaaS auto-restart |

### Lifecycle State Machine

```
INITIALIZING → READY → RUNNING
  ↓ (error)              ↓ (error/crash)
RESTARTING ←──────────────┘
  ↓ (max restarts)
DEAD → (manual intervention required)
```

### Rules

1. **Every worker MUST have a health heartbeat** (periodic "I'm alive" message).
2. **Heartbeat timeout = worker assumed dead.** Kill and restart.
3. **Restart counter MUST reset** after sustained healthy period (e.g., 30min).
4. **Max restarts MUST NOT be the final state.** After cooldown, try again.
5. **Worker crash MUST NOT crash the parent.** Isolate via IPC boundaries.
6. **Worker MUST drain in-flight work** before accepting shutdown signal.

## IPC Channel Health Detection

### The Problem

IPC channels (MessagePort, process.send) can fail silently. The sender
thinks messages are delivered, but the receiver never gets them. This
causes the sender to buffer indefinitely.

### Detection Pattern

```typescript
// Heartbeat protocol
const IPC_HEARTBEAT_INTERVAL = 5000;  // 5s
const IPC_HEARTBEAT_TIMEOUT = 15000;  // 3 missed = dead

// Sender side
setInterval(() => {
  ipc.send({ type: "heartbeat", ts: Date.now() });
}, IPC_HEARTBEAT_INTERVAL);

// Receiver side
let lastHeartbeat = Date.now();
ipc.on("message", (msg) => {
  if (msg.type === "heartbeat") {
    lastHeartbeat = Date.now();
    ipc.send({ type: "heartbeat_ack", ts: msg.ts });
    return;
  }
  // ... handle other messages
});

// Health check
function isIPCHealthy(): boolean {
  return Date.now() - lastHeartbeat < IPC_HEARTBEAT_TIMEOUT;
}
```

### Rules

1. **IPC channels MUST have bidirectional heartbeats.**
2. **Heartbeat timeout triggers restart** (not just logging).
3. **IPC errors MUST NOT be caught and silently ignored** (current: `catch {}` in wiring.ts).
4. **IPC send failures MUST trigger channel health re-evaluation.**

## Bounded Queue Design

### Template

```typescript
class BoundedQueue<T> {
  private items: T[] = [];
  private readonly maxSize: number;
  private readonly dropPolicy: "oldest" | "newest" | "lowest_tier";
  private droppedCount = 0;

  constructor(maxSize: number, dropPolicy: "oldest" | "newest" | "lowest_tier") {
    this.maxSize = maxSize;
    this.dropPolicy = dropPolicy;
  }

  push(item: T): boolean {
    if (this.items.length >= this.maxSize) {
      this.drop();
      return false; // indicates a drop occurred
    }
    this.items.push(item);
    return true;
  }

  // unshift ALSO respects maxSize (unlike current supabase-persistence)
  unshift(item: T): boolean {
    if (this.items.length >= this.maxSize) {
      this.drop();
      return false;
    }
    this.items.unshift(item);
    return true;
  }

  private drop(): void {
    switch (this.dropPolicy) {
      case "oldest": this.items.shift(); break;
      case "newest": this.items.pop(); break;
      // lowest_tier requires T to have a tier field
    }
    this.droppedCount++;
  }

  get size(): number { return this.items.length; }
  get dropped(): number { return this.droppedCount; }
}
```

### Rules

1. **EVERY queue in the system MUST be bounded.**
2. **Queue size MUST be chosen based on memory budget** (not arbitrary).
3. **Drop policy MUST be documented** in the code where the queue is created.
4. **Dropped items MUST be counted** and exposed as a metric.
5. **Queue depth alerts:** warn at 80%, critical at 95%.

## Event Loop Stall Recovery

### Detection (Already Implemented)

```typescript
// EL stall detector: measures time between setImmediate callbacks
// If delta > threshold (e.g., 100ms), log stall with duration
// Tracks p50, p95, p99 of EL iteration time
```

### Recovery Protocol (Active)

1. **Chunk processing:** Max 80 events per tick, defer rest via setImmediate.
2. **Skip when no consumers:** PubSub publish only if topicSubscriberCount > 0.
3. **Skip when no clients:** SSE broadcast only if activeClientCount > 0.
4. **Batch Date.now():** One syscall per batch, not per event.
5. **Defer non-critical work:** Handler defers SSE + Supabase writes.
6. **Tier filtering:** Low-priority entities skip fast path entirely.
7. **In-place mutation:** storeFastRecord reuses existing state objects.

### Post-Stall Recovery

If a stall is detected (>500ms):
1. Log with full context (batch size, operation breakdown).
2. Reduce chunk size temporarily (80 to 40).
3. If sustained (>3 stalls in 1min): alert admin.
4. If health check affected: /healthz returns degraded, not OK.

## Failure Scenario Matrix

| Scenario | Detection | Current Recovery | Required Recovery |
|----------|-----------|-----------------|-------------------|
| IPC channel dead | NONE | Buffer grows to OOM | Heartbeat + bounded buffer |
| Adapter OOM kill | Process exit event | 10x restart | Restart + buffer cap |
| Batch Worker hang | NONE (watchdog off) | Nothing | Re-enable watchdog (120s) |
| Supabase down | Flush errors | unshift (unbounded) | Circuit breaker + bounded queue |
| Upstream WS disconnect | close event | Reconnect with backoff | Current is correct |
| Upstream rate limit | 429 response | Backoff + circuit breaker | Current is correct |
| Main EL stall | Stall detector | Chunked processing | Current is correct |
| Mutation Worker crash | PaaS health (e.g. Fly.io) | PaaS auto-restart | Current is correct |
| DNS resolution failure | Fetch timeout | Retry 3x | Need circuit breaker |
| TLS certificate expiry | Handshake failure | None | Alert + auto-renewal check |
| Memory leak (slow) | RSS monitoring | None (detected late) | Heap snapshot trigger at threshold |
| Full disk | Write failure | None | Disk usage metric + alert |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `catch {}` on IPC errors | Hides channel death | Log, metric, trigger health check |
| Unbounded buffer/queue | OOM guaranteed | BoundedQueue with explicit cap |
| Disabling watchdog permanently | Worker can hang forever | Tune timeout, don't disable |
| unshift bypassing queue cap | Defeats backpressure | Respect cap on all insert paths |
| Restart counter never resets | System permanently dead after N crashes | Reset after sustained health |
| /healthz always returns 200 | Orchestrator thinks dead system is alive | Check adapter, data freshness, EL |
| "It'll retry" without backoff | Hammers failed service | Exponential backoff + circuit breaker |
| Global circuit breaker | One source down kills all | Per-service, per-source |
| Swallowing unhandledRejection | System in unknown state | Log, metric, consider fatal |
| Optimistic IPC (fire-and-forget) | No delivery guarantee | Heartbeat + ack protocol |

## Known Pitfalls (Lessons From Real Incidents)

- **Logger→captureError infinite recursion:** When wiring a logger into captureError(), always add a recursion guard. captureError→log→console.error→captureError is an infinite loop.
- **Dockerfile may have a SEPARATE esbuild entrypoint list from the package.json build script.** When adding workers, update BOTH. Worker crashes with code:1 if .js missing from dist/.
- **Worker threads resourceLimits is HARD KILL** — don't use it; let workers inherit the parent's soft limit. Otherwise workers die without graceful shutdown.
- **Multiple WS connections sharing one event loop:** setInterval heartbeats get starved by message processing. Use per-connection timeout tracking instead.
- **Reconnect MUST clear per-connection state:** cleanupConnection() must clear any cached state bound to the connection. Leaving stale state around after a reconnect leads to subtle invariant violations downstream.

### Adopter observability cross-link (PLAN-045 F-15-05 supplement)

When evaluating a framework installation's resilience posture,
ground the assessment in the PLAN-045 chaos-scenarios catalog:
`.claude/plans/PLAN-045/re-audit/chaos-scenarios.md` (if present
— staged Session 44 phase 6). The catalog enumerates:

- 12 shipped invariants (hook fail-open, filelock timeout, audit-
  log sidecar rotation, kill-switch precedence, ...)
- 8 observed-but-not-tested scenarios (rotation-window file
  deletion, concurrent sigchain append, ...)
- 3 explicit ADR-055 §Out-of-scope gaps (key theft, rollback
  restore, tail truncation)

Adopter recipe when the skill is spawned for a resilience review:

1. Read the shipped-invariants list; match against the adopter's
   target project's documented invariants (if any).
2. Flag gaps in the observed-but-not-tested list as P1 work for
   the adopter's hardening sprint (not a ship blocker).
3. Explicitly call out the 3 ADR-055 gaps if the adopter has
   regulatory requirements for tamper-evidence beyond the per-
   file chain.

Cross-ref: SP-006 (primary adopter note) + `docs/HONEST-
LIMITATIONS.md` §residual risks.
