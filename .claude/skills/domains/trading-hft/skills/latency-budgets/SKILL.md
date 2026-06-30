---
name: Latency Budgets
description: Latency budget engineering for HFT systems — wire-to-wire targets, hot-path discipline (no allocations / no syscalls / no locks), GC pause analysis, NUMA placement, and continuous-measurement contracts.
trigger: Any change to a latency-sensitive code path (order send / market-data ingest / strategy hot loop), or any time the Latency Architect VETO flags a budget concern. Pair with `order-routing` for wire-path edits.
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: trading-hft
priority: 3
risk_class: medium
stack: [python, cpp]
context_budget_tokens: 700
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: true, priority: 2}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)latency|p99|jitter|tick.?to.?trade"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/latency/**"
  - "**/hot-path/**"
  - "**/benchmarks/**"
---

# Latency Budgets — Trading-HFT skill

> Owned by **Marcelo Andrade** (Latency Architect). VETO holder on
> any change that affects budgets without analysis.

## When to load this skill

- Adding code to a hot path
- Changing data structures the hot path traverses
- Reviewing a perf regression alert
- Designing a new strategy whose latency sensitivity is unknown
- Onboarding a new venue with stricter latency SLAs

## Latency budget contract

Every code path that participates in the wire-to-wire path MUST have:

1. A **documented target** (p50, p99, p99.9 in microseconds).
2. A **measurement plan** (how the budget is verified continuously).
3. An **owner** (the persona who is paged when the budget is breached).
4. A **regression alert** (the threshold at which CI / monitoring fires).

Budgets are enforced **measurement-first**. Saying "this should be
fast enough" without numbers is a VETO trigger.

### Reference budgets (illustrative — adjust per venue / strategy)

| Code path | p50 | p99 | p99.9 |
|---|---|---|---|
| Market-data tick → strategy decision | 5 µs | 12 µs | 35 µs |
| Strategy decision → wire send | 3 µs | 8 µs | 25 µs |
| Wire ack → strategy state update | 2 µs | 5 µs | 18 µs |
| Cancel hot path (kill switch) | 8 µs | 20 µs | 60 µs |

## Hot-path discipline

The "hot path" is any code that runs once per market-data tick or once
per order. Hot-path code MUST NOT:

- Allocate heap memory (use object pools / arenas / stack)
- Take a GC-tracked allocation (in managed runtimes, use value types
  / structs / unsafe arenas)
- Make a syscall (no `clock_gettime`, no `read`, no `write`, no
  `mutex_lock` that may contend)
- Acquire a contended lock (use lock-free queues / atomics; if a
  lock is unavoidable, it MUST be fully owned by the hot-path thread)
- Do string formatting (defer to a sidecar / off-path formatter)
- Call a virtual / interface method without devirtualization
  evidence (assembly inspection or profile-guided opt)

## Anti-patterns to detect

- **Logger.info() in the hot path.** Even if the level is OFF, the
  format-arg evaluation costs allocations.
- **Map/dict lookups by string in the hot path.** Use integer / enum
  keys + array indexing.
- **JSON / FIX serialization on the hot path.** Pre-build templates
  with fillable slots; the hot path memcpy-fills them.
- **`new` / `make` / heap allocation per order.** Pool the objects.
- **Recursive logging on shared loggers.** Log into a per-thread
  ring; the writer is a sidecar.
- **NUMA-unaware data placement.** Hot data MUST live on the same
  socket as the hot-path thread.

## Measurement requirements

Every hot-path change MUST ship with:

1. A **before / after histogram** at p50 / p99 / p99.9.
2. A **CPU budget breakdown** (perf top / vmlinux / cycles).
3. A **GC report** (managed runtimes only — pause histogram).
4. A **sample workload definition** so the measurement is reproducible.

If any of the four is missing → Latency Architect VETO until provided.

## Output checklist (every hot-path PR)

- [ ] Documented p50/p99/p99.9 target for the touched path
- [ ] Before / after histogram attached to PR
- [ ] No new heap allocations in the hot path (or pool-justified)
- [ ] No new syscalls in the hot path
- [ ] No new locks contended by hot-path thread
- [ ] Regression alert threshold set in monitoring
- [ ] NUMA / CPU affinity unchanged or explicitly justified

## References

- ADR-013 (this squad)
- `order-routing` skill (always paired on wire-path edits)
- `kill-switches` skill (cancel-path latency budget is special)
- Universal `performance-engineering` skill
