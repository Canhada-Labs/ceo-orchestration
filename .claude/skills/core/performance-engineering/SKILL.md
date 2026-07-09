---
name: performance-engineering
description: Performance engineering for Node.js real-time systems. Covers V8 internals
  (hidden classes, inline caches, deoptimization), GC tuning (Scavenge/Mark-Sweep/Compact),
  event loop forensics (stall diagnosis, tick profiling), memory leak detection, hot
  path optimization, IPC throughput, worker_threads performance, SharedArrayBuffer
  patterns, and production profiling. Use when analyzing event loop latency, diagnosing
  memory growth, optimizing hot paths, profiling IPC throughput, or reviewing any code
  that runs on the critical data path.
owner: Principal Performance Engineer (archetype)
inspired_by:
  - source: affaan-m/ecc/skills/benchmark-optimization-loop/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 4
risk_class: medium
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 4}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)performance|latency|p95|p99"}
source: affaan-m/ecc@81af4076 skills/benchmark-optimization-loop/
license: MIT
---

# Performance Engineering

Note: This skill is Node.js-focused. The mental model (V8 internals, GC tuning, event loop forensics) applies broadly, but specific commands and profilers differ on Python/Go/Rust runtimes.

## Fail-Fast Rule

If a performance metric exceeds its budget, **stop and investigate**. Never
accept "it's fast enough" without numbers. Never optimize without profiling
first. Never profile with small data sets and claim production readiness.

## {{PROJECT_NAME}} Performance Budgets

| Metric | Budget | Current | Alert At |
|--------|--------|---------|----------|
| Event loop p50 | < 5ms | 1.26ms | > 10ms |
| Event loop p99 | < 100ms | ~100ms | > 200ms |
| Heap used | < 2GB | ~604MB | > 1.5GB |
| RSS (main) | < 4GB | ~2-4GB | > 6GB |
| RSS (adapter) | < 24GB | ~16-24GB | > 28GB |
| IPC latency | < 50ms | ~50ms coalesce | > 100ms |
| Event throughput | > 200 events/s | ~400+ events/s | < 150 events/s |

## V8 Internals That Matter

### Hidden Classes (Shapes)
- Objects with same property order share hidden classes → fast property access
- Adding properties in different orders creates new hidden classes → SLOW
- **Pattern**: Hot-path state objects must always have the same property shape
- In a `storeFastRecord()`-style function: in-place mutation preserves hidden class (good)
- Creating new objects per event would thrash hidden classes (bad)

### Inline Caches (ICs)
- V8 caches property lookup locations per call site
- Polymorphic ICs (>4 shapes at one call site) → megamorphic → deopt → SLOW
- **Risk**: Processing events from N upstream integrations that each have a different shape

### Deoptimization Triggers
- `try/catch` in hot functions (V8 can't optimize well)
- `arguments` object usage
- `delete` operator on objects
- Changing object shape after creation
- `eval` or `with`

## Event Loop Forensics

### Canonical Case: Distributed EL Stall

A real incident saw EL p50 at ~1500ms. No single operation caused the
stall — it was the SUM of:
- PubSub publish per event (×N topics) → JSON.stringify per publish
- SSE broadcast per event → another JSON.stringify
- Date.now() per call → hundreds of syscalls per batch
- Map.set per event → allocation + GC pressure
- All multiplied by 200+ events per batch × 20 batches/s

**Fixes applied (in order of impact):**
1. `topicSubscriberCount` check — skip JSON.stringify when 0 subscribers
2. `Date.now()` cached per batch — hundreds of syscalls → 1
3. SSE `activeClientCount` — skip broadcast when 0 clients
4. `processFastChunk()` — cap at 80 events/tick, defer rest via setImmediate
5. Handler defers SSE + persistent writer to setImmediate
6. `storeProcessedRecord()` returns boolean — skip broadcast for merge-only
7. `storeFastRecord()` in-place mutation — reuse existing state objects
8. Fast path skips low-priority entities

**Result**: EL p50 ~1500ms → ~1.26ms (roughly 1200x improvement)

**Lesson**: Hot path problems are DISTRIBUTED. No single fix is enough.
You must reduce ALL sources simultaneously.

## Memory Optimization Patterns

### Closure Leaks
```typescript
// BAD: closure captures entire array
setImmediate(() => processChunk(largeArray));
// After N iterations, N copies of largeArray exist

// GOOD: slice creates new small array, original can be GC'd
const chunk = largeArray.slice(start, end);
setImmediate(() => processChunk(chunk));
```

### In-Place Mutation vs Object Creation
```typescript
// BAD: creates new object per update (GC pressure)
records.set(key, { ...existing, fieldA: newA, fieldB: newB });

// GOOD: mutate existing (preserves hidden class, zero allocation)
existing.fieldA = newA;
existing.fieldB = newB;
existing.ts_ingest = now;
```

### Map vs Object for Hot Paths
- `Map` is better for frequent add/delete (no hidden class thrash)
- Plain object is better for fixed keys (V8 optimizes property access)
- Use `Map<string, RecordState>` for mutable keyed collections on the hot path

## IPC Performance

### MessagePack vs JSON
- MessagePack: ~2x faster encode, ~3x faster decode, ~30% smaller
- Used for: high-frequency event data (adapter→main)
- JSON: used for control messages (start, stop, config)
- **Never mix**: don't JSON.stringify a MessagePack-decoded object then MessagePack it again

### Coalescing
- Coalesce IPC at ~50ms intervals for bulk events
- A HOT lane can bypass coalescing for time-sensitive events
- Without coalescing: thousands of IPC messages/sec → EL overwhelmed
- With coalescing: ~20 batches/sec of ~200 events each

### Backpressure
- If the receiver can't keep up, the sender must detect and slow down
- PubSub should enforce size limits (e.g. 1MB skip, 4MB force-close)
- `worker_threads` `port.postMessage` can queue unboundedly → OOM risk
- Always check queue depth before posting

## Worker Threads Performance

### Structured Clone Cost
- worker_threads IPC uses V8 structured clone (serialization + deserialization)
- Cost scales with object size, not complexity
- ~1-5ms for a typical batch
- SharedArrayBuffer AVOIDS this cost entirely (zero-copy)

### SharedArrayBuffer Patterns
- Suitable for: small fixed-size numeric state, pre-allocated slots
- Lock-free via Atomics.store/load
- Display ONLY — never for business-critical math (no precision guarantee)

## Profiling Checklist

Before any optimization:
1. **Measure baseline**: EL latency, heap, RSS, throughput
2. **Identify hot path**: Where does the most time go?
3. **Profile under load**: Not idle, not synthetic — real data volume
4. **Set target**: What number are we trying to hit?
5. **Change ONE thing**: Measure again. Attribute improvement.
6. **Repeat**: Until target is met or diminishing returns

## Bounded Optimization Loop

The Profiling Checklist tells you how to make *one* measured change. This section
scales that to "make it 20x faster" or "try 50 variants" without turning into an
unbounded, unfalsifiable search. The discipline is: never optimize without a
baseline and a budget, and never promote a variant that has not beaten the prior
*accepted* winner on a repeatable measurement with correctness still green.

### Required baseline (do not start without all five)

1. **The operation** being optimized, isolated enough to run repeatedly.
2. **The correctness gate** that must stay green — the test/assertion set a faster
   variant is not allowed to break. Speed that fails correctness is a regression,
   not a win (this is the Fail-Fast Rule applied to the search).
3. **The metric**, chosen explicitly: wall time, p95/p99 latency, throughput
   (events/s, rows/s), cost/run, heap, RSS, or error rate. Optimizing the wrong
   metric is an anti-pattern (RSS is not heap; p50 is not p99).
4. **The current baseline** — the measured number today, under real load, not a
   warm-up log (steady-state 5min+ per the Known Pitfalls note).
5. **The search budget** — max variants, max wall-clock, max spend, max data
   impact. An unrealistic target ("20x") is fine as ambition; the *loop* stays
   bounded and measurable.

### The loop

1. Measure the baseline.
2. Identify the bottleneck **from evidence** (a profile), not a hunch.
3. Generate variants that each test **one** hypothesis.
4. Run every variant against the **same input shape** as the baseline.
5. Reject any variant that fails correctness, safety, or reproducibility.
6. Promote the fastest surviving variant.
7. Codify the winner in a script, command, test, config, or doc — a number you
   cannot reproduce on demand is not a result.
8. Rerun baseline and winner back-to-back to confirm the delta is real.

### Variant ledger

Track every variant so improvement is attributable and reproducible:

```text
Variant     | Hypothesis            | Command                       | Metric | Correct? | Notes
baseline    | current path          | npm run job                   | 120s   | yes      | stable
batch-500   | fewer round trips     | npm run job -- --batch 500    | 42s    | yes      | winner
parallel-8  | more workers          | npm run job -- --workers 8    | 31s    | NO       | rate-limited, rejected
```

The `Correct?` column is load-bearing: `parallel-8` is faster and still loses,
because a faster-but-wrong variant never promotes.

### Recursive / hyperparameter search

For a long or recursive search:

- Persist every run to the ledger, not just the current best.
- Compare each candidate against the **prior accepted winner**, not merely the
  previous run — otherwise a noisy sequence drifts.
- Keep a holdout or replay check so you are not overfitting to one input.
- **Stop** when improvement is within measurement noise, correctness fails, cost
  exceeds the budget, or the search starts changing more variables than it can
  explain. Say "best measured safe variant," not "global optimum," unless the
  space was actually exhausted.

### Promotion gate

A variant becomes the new default only when ALL hold:

- correctness tests pass;
- the performance delta is repeated or explained (not a single lucky run);
- rollback is obvious (one revert restores the prior default);
- the change is encoded in source control or a durable runbook;
- the final summary carries the **exact commands and measurements** — so the
  next engineer reproduces the number instead of trusting it.

## Anti-Patterns

1. **Premature optimization**: Optimizing code that runs 1x/min
2. **Micro-benchmarks**: Measuring isolated function, not system under load
3. **Optimizing the wrong metric**: RSS is not heap, p50 is not p99
4. **Closure captures**: setImmediate/setTimeout callbacks referencing large objects
5. **Date.now() in loops**: Syscall per call, cache per batch instead
6. **JSON.stringify per message**: Batch or skip when no consumers
7. **Map operations on read-only data**: Use in-place mutation
8. **Chunking with closures**: setImmediate chunks that capture parent scope arrays

## Known Pitfalls (Lessons From Real Incidents)

- **setTimeout(0) is NOT setImmediate()** — use setImmediate for yielding event loop
- **V8 max-old-space-size:** Reducing does NOT always help. Example: 2048MB once caused p50 1.46 → 4.92ms; 4096MB was optimal. Tune against your workload.
- **Worker threads have ISOLATED module scope** — a Map populated in a worker is NOT visible from main
- **resourceLimits is HARD KILL** — don't use it; let workers inherit parent's soft limit
- **--trace-gc INVALID for worker threads** — use PerformanceObserver('gc') instead
- **Array.reduce() is 3-5x slower than for loops** — closure allocation overhead. Use for loops on hot paths.
- **JSON.parse scales super-linearly for >1MB** — prefer many small batches
- **setImmediate chunking can cause heap bloat:** if deferred chunks capture large arrays in their closures, each pending chunk retains the whole array. Use `slice()` to create small independent chunks.
- **EL stall root cause is often DISTRIBUTED:** no single op causes the stall. It's the SUM of: PubSub × N topics, SSE broadcast, JSON.stringify, Date.now, Map ops — all multiplied by event count per batch. You must reduce ALL sources simultaneously.
- **NEVER trust warm-up logs for perf validation** — steady-state workload (5min+) creates much larger batches
## Adopter Note — Language + Metric Portability (PLAN-044 P0-12)

This skill is **Node.js-focused** — the portability note near
the top is honest about that. The §Performance Budgets table
(Event loop p50/p99, Heap used, RSS main/adapter, IPC latency,
Event throughput) carries numeric columns (e.g. `~604MB`,
`~2-4GB`, `~16-24GB`, `~50ms coalesce`, `~400+ events/s`) that
are **snapshots of the originating `ceo-orchestration` dogfood
project** — a Node.js real-time adapter on specific hardware.

For your own adopter:

- Establish your own budgets against your own baseline. Keep
  the column headers (budget / current / alert-at) but replace
  the numbers before acting on them.
- On non-Node runtimes (Python, Go, Rust, JVM), the V8 /
  hidden-class / IC subsections do not apply directly — the
  *mental model* of "monomorphic hot path" / "avoid megamorphic
  dispatch" / "profile before optimising" transfers, but the
  concrete techniques and tools do not.
- The IPC and worker_threads subsections assume Node's cluster/
  worker IPC model. Python `multiprocessing` / Go goroutines /
  Rust async runtimes have very different trade-offs.

Treat the text as an illustrated archetype; run your own
profiling first, and cite your own baseline in any follow-up
amendment.

## Changelog

- **2026-07-07 (PLAN-153 Wave G, SP-041)**: added "Bounded Optimization Loop"
  (required baseline, the measured loop, the variant ledger, recursive-search
  stopping conditions, and the promotion gate) — porting benchmark-optimization-
  loop practice so "make it 20x faster" becomes a bounded, reproducible search
  instead of an open-ended one. Clean-room ADAPT merge; additive only. The loop
  is deliberately runtime-agnostic and extends the existing Node-specific
  Profiling Checklist rather than replacing it, so the portability caveat at the
  top still holds. No section renumbered.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=95a2bd336b00f6b3a45d4c851acd77f9fddb544b618f97d2216669b9ecd14a49
