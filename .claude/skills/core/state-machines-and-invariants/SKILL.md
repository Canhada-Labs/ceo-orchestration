---
name: state-machines-and-invariants
description: Governing correctness through explicit state machines and enforced
  invariants. Defines when the system is READY vs DEGRADED vs STALE vs INVALID,
  what is allowed in each state, and when to fail fast. Use when designing or
  reviewing real-time data systems, streaming pipelines, upstream adapters,
  aggregated feeds, health checks, or any logic that can silently degrade
  data quality. Prevents optimistic outputs. Also use when the user mentions
  "state machine", "system state", "fail fast", "invariant violation", "when to
  stop", or when reviewing any code that decides whether to serve or reject data.
owner: Real-Time Systems Engineer (archetype)
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: []
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 6}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)state.?machine|invariant|tla"}
---

# State Machines and Invariants

## Cardinal Rule

State is the source of truth. If state is not READY, the system must not
behave as if it is. Never compute, merge, or present results that imply
correctness when state indicates degradation, staleness, or invalidity.

When any mandatory invariant fails: **fail fast** with a structured reason.

## No Policy, No Answer

If the system depends on thresholds (staleness ms, consecutive events N,
failure count K, cooldown period T) and those values are not provided
or configured, **refuse to make state decisions**. Return:

> "Missing policy values — cannot decide state transitions. Provide thresholds."

Never invent or guess threshold values.

## Core Concepts

### Event vs State

- **Events** are inputs: WS messages, REST responses, timeouts, validation
  failures.
- **State** is the maintained truth of what the system currently believes.
- A single good event does NOT erase a bad state unless the state machine
  rules explicitly allow it.

### No Silent Recovery

Recovery must be explicit. Document:
- What changed?
- Why is it safe now?
- Which invariants are passing again?

## State Models

### System State (Global)

```typescript
type SystemState =
  | 'BOOTING'     // starting up, loading config
  | 'WARMING'     // acquiring initial data
  | 'READY'       // fully operational
  | 'DEGRADED'    // some sources unavailable
  | 'UNHEALTHY'   // critical invariants failing
  | 'DISABLED';   // manually turned off
```

### Source State (Per-Upstream-Integration)

```typescript
type SourceState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'SUBSCRIBED'
  | 'DEGRADED'
  | 'CIRCUIT_OPEN'
  | 'DISABLED';
```

### Feed State (Per-Dataset Per-Source)

```typescript
type FeedState =
  | 'EMPTY'      // no usable data
  | 'WARMING'    // acquiring snapshot / building consistency
  | 'READY'      // valid + fresh + sequenced
  | 'DELAYED'    // valid but late updates
  | 'STALE'      // age beyond threshold
  | 'INVALID'    // invariant violated
  | 'DISABLED';  // intentionally off
```

### Response State (What the API Returns)

```typescript
type ResponseState =
  | 'OK'
  | 'DEGRADED'
  | 'STALE_DATA'
  | 'INVALID_INPUT'
  | 'INVARIANT_VIOLATION'
  | 'INSUFFICIENT_DATA';
```

**Every response picks exactly one ResponseState.**

## Mandatory Invariants

The specific invariants are domain-dependent. The pattern below applies
universally: define the rules that MUST hold, enforce them on every event,
fail fast on violation.

### Structural Invariants (examples)

1. Sorted: primary key sorted as expected (ascending or descending per side/partition).
2. No contradictions: upper-bound fields stay above lower-bound fields; no self-referential loops.
3. No zero/negative quantity on fields that must be positive.
4. No duplicate key per side/partition.

### Identity / Semantics

5. Canonical entity consistency: foreign keys match declared identity.
   Never auto-flip a mislabeled record.
6. Partition isolation: aggregations merge only matching partition keys.
   Any mismatch → reject that source.

### Freshness

8. Freshness computed from `receivedAt` (not `upstreamTimestamp`).
9. Freshness threshold is state-dependent: WS tighter than REST fallback.
   Exceeding threshold → STALE (not "OK with warning").

### Sequencing

10. Sequence monotonicity: updates apply in order, no gaps.
11. On gap: discard local book, re-fetch snapshot, enter WARMING.

## State Transitions

### FeedState Transitions

**EMPTY → WARMING**
- On subscribe or snapshot request initiated.

**WARMING → READY**
- Only when ALL conditions met:
  - Snapshot applied successfully
  - All invariants pass
  - Sequence is consistent (if sequenced)
  - Freshness within threshold
  - Recommended: N consecutive good updates received

**READY → DELAYED**
- Latency spikes or intermittent fallback, but invariants still pass.
- Hysteresis: require DELAYED for N events or T ms before declaring.

**READY | DELAYED → STALE**
- Age exceeds threshold.
- STALE is sticky: requires fresh snapshot OR M consecutive good updates.

**ANY → INVALID**
- Any mandatory invariant fails.
- INVALID is sticky: recovery requires discard + snapshot refresh
  OR circuit break + cooldown.

**ANY → DISABLED**
- Manual operator action or policy rule.

## Hysteresis / Anti-Flap

Mandatory anti-flap policies:

- Entering DELAYED requires N events OR T ms before transition.
- Returning from STALE/INVALID requires snapshot refresh OR M
  consecutive good updates.
- Circuit breaker opens after K consecutive failures, closes after
  cooldown period + successful snapshot.

These values (N, M, K, T) must be provided as configuration.
See "No Policy, No Answer" rule.

## Aggregation Eligibility

A source can contribute to the aggregated view only if:

- `feedState === 'READY'`
- `sourceState` in `['SUBSCRIBED', 'CONNECTED']`
- Freshness passes
- Partition / schema matches

### Aggregated ResponseState

- 2+ eligible sources → `OK`
- 1 eligible source → `DEGRADED`
- 0 eligible sources:
  - Entity exists but no data → `INSUFFICIENT_DATA`
  - Entity is invalid → `INVALID_INPUT`

**Never fill in missing sources with stale data to look complete.**

## Failure Output Contract

When rejecting, always return structured failure:

```typescript
interface Failure {
  responseState: ResponseState;
  reasonCode:
    | 'INVARIANT_VIOLATION'
    | 'STALE'
    | 'PARTITION_MISMATCH'
    | 'SEQUENCE_GAP'
    | 'ZERO_QTY'
    | 'DUPLICATE_KEY'
    | 'INVALID_ENTITY'
    | 'NO_ELIGIBLE_SOURCES'
    | 'CIRCUIT_OPEN'
    | 'MISSING_POLICY'
    | 'UNKNOWN';
  message: string;
  context: {
    entity?: string;
    source?: string;
    ageMs?: number;
    thresholdMs?: number;
    lastGoodAt?: number;
    lastBadReason?: string;
  };
  nextAction?: string;  // e.g. 'refetch_snapshot', 'exclude_source'
}
```

**Never return a numeric business metric if responseState is not OK or DEGRADED.**

## Observability Hooks

Every state transition must emit:

- Metric: `state.transition { entity, from, to, reason }`
- Structured log: `state_transition` with full context
- Health check surfaces: top degraded entities + reasons

State machine is not complete without telemetry.

## Test Matrix (Must Exist)

1. Invariant violation → INVALID state
2. Partition mismatch in aggregation → source excluded + metric
3. Sequence gap → WARMING + snapshot refresh
4. Staleness → STALE + excluded from aggregated view
5. Flapping scenario → hysteresis prevents READY↔DELAYED oscillation
6. Single-source aggregation → DEGRADED response
7. Missing threshold config → MISSING_POLICY error, not a guess
8. Recovery from INVALID → requires explicit snapshot + invariant pass

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| "One good update = we're fine" | Ignores sticky failures | Explicit recovery criteria |
| Serving stale "with warning" | Users still act on it | Exclude stale from aggregates |
| Auto-fixing violated invariants | Masks corruption | Mark INVALID + remediate |
| Using upstream timestamp for staleness | Clock drift | Use receivedAt |
| Recovery without snapshot after gap | Silent wrong state | Discard + re-fetch |
| Guessing threshold values | Wrong policy = wrong state | No policy, no answer |
| State transition without telemetry | Invisible to operators | Metric + log on every transition |
| READY without invariant check | Optimistic state | All invariants must pass |

## Known Pitfalls (Lessons From Real Incidents)

- **Delta drift:** incremental merges grow indefinitely if not capped. Always truncate after merge; cap each source's per-entity output size.
- **Delta + throttle drift:** when throttling emissions, store-previous-state must be inside the if(shouldEmit) branch. Delta base must match consumer's last received.
- **Warm-up dedup:** buffered partial data must not overwrite a full snapshot; wiring must not store an empty state on a null delta; the aggregator must reject deltas that violate invariants.
- **Row-count limits solved by Delta IPC** — only send changed rows in batch updates.
- **Time-bucketed trackers are minute-aligned** — a getHistory(hours: X) cutoff MUST be > 60s or it will return an empty window.
