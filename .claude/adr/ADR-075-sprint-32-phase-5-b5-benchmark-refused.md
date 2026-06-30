---
id: ADR-075
title: Sprint 32 Phase 5 B5 (head-to-head benchmarks) — REFUSED via technical-infeasibility
status: ACCEPTED
created: 2026-04-24
accepted_at: 2026-04-24
accepted_via: Round-20 sentinel (19102f1 promote) + Round-22 backfill
proposed_by: CEO (Session 59 execution)
co_signers: [VP Engineering (architecture validity), Principal Security Engineer (no-regression)]
related_plans: [PLAN-051, PLAN-017]
related_adrs: [ADR-063, ADR-071]
blast_radius: L3 (closure artifact)
supersedes: none
superseded_by: none
closes_item: PLAN-051 §2 B5 (head-to-head benchmarks vs ecosystem)
refused_taxonomy: (a) technical-infeasibility
enforcement_commit: 19102f1
---

# ADR-075 — Sprint 32 Phase 5 B5 REFUSED via technical-infeasibility

## Context

PLAN-051 §2 item B5 proposes head-to-head empirical comparison of
the `ceo-orchestration` swarm-coordinator against ecosystem tools
(Devin, Codex, SWE-bench-lite subset) gated on ADR-071 (benchmark
comparison methodology).

Scaffold **already shipped** across Session 54 + 57:
- `.claude/scripts/swarm/_benchmark_replay.py` (~250 LoC, JSON manifest)
- `docs/benchmarks/swarm-replay-example.json`
- `.claude/scripts/swarm/_replay_tournament.py` (NaN/Inf defensive zero)
- `docs/benchmarks/sprint-32-fairness-protocol.md` (pre-registration)
- `docs/benchmarks/manifest.schema.json` (JSON Schema pin)
- 16 tests (schema validation + pre-registration harness)

**Scaffold is INFRASTRUCTURE**, not result collection. ADR-075
addresses whether to **execute benchmarks** against external
ecosystem tools, producing published head-to-head numbers.

## Decision

**REFUSED** per PLAN-051 §3.1 taxonomy reason
**(a) technical-infeasibility**.

## Reasoning

### No comparable public harness for swarm-coordinator workload

The `ceo-orchestration` swarm-coordinator is an **intra-repo
autonomous-loop parallelism tool** (per ADR-063). It spawns N=8
parallel Claude sessions against an explorable solution space
(e.g. test-speed optimization, bundle-size reduction, prompt
iteration), scores results via a tournament function, and promotes
the best-of-N.

Ecosystem tools measured by SWE-bench / SWE-bench-lite solve a
**different category of task**: end-to-end agent solving a GitHub
issue in a pre-defined repository, with the agent executing shell
+ code edits sequentially toward a unit-test-passing state.

**Workload mismatch:**
- SWE-bench task = "fix this bug, pass the failing test"
- swarm-coordinator task = "explore N variants of fix X, best-of-N
  wins the tournament"

A fair head-to-head would require:
1. Reformulating SWE-bench tasks as tournament-scorable variants
   (e.g. N attempts per task, then scoring via code review or
   test-passing-rate among variants) — this is **NOT how SWE-bench
   measures**.
2. Matching compute budgets across tools (ceo-orchestration's N=8
   spawns vs Devin/Codex's single-agent-with-reflection).
3. Publishing under fairness constraints that may bias against one
   side ("swarm-coordinator consumes 8× budget for same task" OR
   "SWE-bench doesn't allow parallel attempts, disadvantaging
   swarm").

### Pre-registration requirement + ADR-071 fairness gate

ADR-071 (benchmark comparison methodology) specifies:

> Names decision drivers (hook-consumer contract stability,
> canonical-edit discipline, auto-revert behavior). Lists fairness
> protocol (seed / compute budget / prompt / scoring). Picks
> mechanism (API-adapter vs public-baseline — Phase 0.5
> open-question #2 resolution).

**Phase 0.5 open-question #2 unanswered by Owner:** "API access to
Devin/Codex live, OR public baselines only?" — unresolved in
Session 57+58+59. Without Owner direction on mechanism, Phase 5
cannot proceed under ADR-071 protocol.

**Default mechanism (public baselines):** SWE-bench-lite's public
leaderboard cites aggregate numbers (median pass-rate) without
per-task distributions. Comparing a swarm run (with explicit
per-task distributions) to aggregate public numbers fails the
"N≥10 per task, median+p50/p95/p99/stddev" methodology gate (Phase
5 Acceptance, QA Risk #3).

**Alternative mechanism (API-adapter to live tools):** requires
paid API access to Devin + Codex, outside the framework's "no new
paid dependencies" constraint (PLAN-051 §Anti-goals). Also
authorization budget constraint: Owner has not authorized new paid
services for benchmark runs.

### Attempts would not produce Sprint-32-closure-eligible results

Under the stricter ADR-071 methodology requirements (N≥10 per
task per adapter, published per-cell with median/p50/p95/p99/stddev,
sandboxed `--network=none` Docker, digest-pinned images, NO `pip
install` at runtime, independent verifier step at ±5% tolerance),
producing publishable numbers within the Sprint 32 window
(≤2-3 dev-days + 2026-04-29 soft deadline) would require:

- **External tool access** (not available)
- **Workload reformulation** (scope expansion, violates
  §Anti-goals)
- **10×-20× compute runs** per task per adapter (cost unbounded
  without Owner budget authorization)

Plan §Phase 5 explicitly removed the "internal-disclaimer fallback"
(Code Rev Risk #4): "either public benchmark (SWE-bench-lite
subset, 3-5 tasks, pinned seeds) OR Phase 5 closes `refused via
ADR` taxonomy reason (a) 'no comparable public harness for
swarm-coordinator workload'."

**This ADR executes that explicit refusal path.**

## Options considered

### Option 1 — Run benchmarks anyway under looser methodology

Publish swarm-coordinator results on a reduced subset (1-2 tasks,
N=5 runs) with cherry-picked vs-Devin comparison.

**Why refused:** violates ADR-071 §Measurement Methodology (N≥10
per cell, NO "best of 3", omit cells with N<10). Publishing weaker
numbers under-represents methodology rigor the framework otherwise
maintains, and would be cited against the framework if adopters
later compare to actual SWE-bench results.

### Option 2 — Generate synthetic tasks matching swarm workload

Create new benchmark harness that measures swarm-coordinator's
specific strengths (N-parallel exploration of solution space).
Publish as "internal benchmark".

**Why refused:** plan explicitly removed internal-disclaimer
fallback (§Phase 5 — "Internal-disclaimer fallback REMOVED").
Scope would also expand beyond closure (§Anti-goals: "NÃO adicionar
novos itens").

### Option 3 — Defer to post-Sprint-32

Sprint 33 could explore external tool API access + workload-matched
harness.

**Why refused:** PLAN-051 §Anti-goals explicitly forbid planning
Sprint 33. If post-closure adopter demand justifies benchmark
exploration, it enters as a reactive ADR (framework's "done +
reactive maintenance" mode), not a scheduled sprint.

## Consequences

### Positive

- Sprint 32 closure unblocked: Phase 5 closes definitively.
- `docs/benchmarks/sprint-32-fairness-protocol.md` + manifest
  schema retained as **infrastructure** for future retry. If
  adopter demand materializes post-Sprint-32, the pre-registration
  + sandbox + percentile-reporting scaffolding accelerates re-open.
- 16 tests shipped with scaffold stay green (`baf4cfc`
  pre-registration scaffold commit).
- `ADR-063 tournament framework` cited as foundation for internal
  swarm tournaments (retained, not affected by refusal).

### Negative / Accepted

- **No published head-to-head numbers** for Sprint 32 release.
  Framework cannot cite "X% faster than Devin" or similar.
  Adopters reading the v1.9.x or v1.10.0 release notes will NOT
  see external comparison data. Accepted — framework's value
  proposition is orchestration discipline, not benchmark-topping.
- **ADR-071 status remains PROPOSED**. ACCEPT gate (which requires
  Phase 5 execution) unmet. ADR-071 preserved in current state for
  future retry.
- **Post-sunset declaration CANCELLED**: PLAN-051 §6.1 listed no
  specific invariant sunset for B5; no invariant posture change.

## Invariant posture

**Preserved (§6 invariants):**
- Scaffold artifacts at `.claude/scripts/swarm/_benchmark_replay.py`,
  `_replay_tournament.py`, `manifest.schema.json`,
  `fairness-protocol.md`, 16 tests
- `tournament.py` (ADR-063) intact
- No new benchmark dependencies introduced

**Unmet commitments (accepted):**
- ADR-071 PROPOSED → ACCEPTED never flipped (blocked on Phase 5
  execution which is now refused)
- Head-to-head numbers not published

## Dual co-sign (§3.1 — refused-ADR hard requirement)

- **VP Engineering** (architecture validity): ✅ Head-to-head
  benchmark execution requires external tool access (not available)
  OR workload reformulation (scope expansion violating §Anti-goals).
  Scaffold preserved for future retry. Co-sign granted.
- **Principal Security Engineer** (no-regression): ✅ No security
  surface change. Scaffold's sandbox requirements
  (`--network=none`, digest-pinned Docker, no runtime `pip
  install`) remain documented as prerequisites for future
  execution. No new attack surface introduced by refusal. Co-sign
  granted.

## Refused-ADR ceiling check (§3.1 cap)

After ADR-075 lands:

- Refused count: 2/11 (A1/A2/A3/B2/B3/B4/B6/C1 done; B1 refused
  ADR-074; **B5 refused this ADR**; C2 pending 2026-04-29)
- Cap 3/11: under cap by 1
- If C2 also refuses (soak breaks): count → 3/11 (exactly at cap)
- No taxonomy reason monopoly concern (ADR-074 + ADR-075 both
  cite (a) technical-infeasibility, but root causes distinct:
  state-mutation coupling for B1, workload mismatch for B5)

## References

- PLAN-051 §2 B5
- PLAN-051 §Phase 5 Acceptance (pre-registration + sandbox +
  methodology gates)
- PLAN-051 §Anti-goals (no new paid deps, no scope expansion)
- PLAN-051 §3.1 Refused-ADR taxonomy
- PLAN-051 Phase 0.5 open-question #2 (Owner direction unanswered)
- ADR-063 (tournament framework, foundation)
- ADR-071 (benchmark comparison methodology, PROPOSED — remains
  so post-refusal)
- `.claude/scripts/swarm/_benchmark_replay.py` (scaffold, retained)
- `.claude/scripts/swarm/_replay_tournament.py` (scaffold, retained)
- `docs/benchmarks/sprint-32-fairness-protocol.md` (pre-registration)
- `docs/benchmarks/manifest.schema.json` (JSON Schema pin)
- commit `baf4cfc` (scaffold + 16 tests)

## Enforcement commit

**Enforcement commit:** to be populated by the commit that lands
this ADR + updates PLAN-051 `ledger.md` row B5 = refused.
