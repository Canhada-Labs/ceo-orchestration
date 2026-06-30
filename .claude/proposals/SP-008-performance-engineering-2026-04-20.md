---


id: SP-008
skill_slug: performance-engineering
archetype: performance-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-performance-engineering
scan_injection_pass: true
diff_size_added: 27
diff_size_removed: 0
sha256_of_diff: 964fb2a2aa1c3565026053b97d2156d8ab24103146a86d8e4f072b48380866bd
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-008 — skill patch proposal

**Target:** `.claude/skills/core/performance-engineering/SKILL.md`
**Archetype:** performance-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `performance-engineering/SKILL.md` already carries a language-portability note, but the concrete §Performance Budgets numeric column is a snapshot of the originating ingestion-engine. Adopters running Python/Go/Rust/JVM workloads would otherwise inherit Node-shaped budgets. This proposal appends a second disclaimer covering both the numeric budget snapshot and the language-specific technique depth (V8, IPC, worker_threads). Pure-addition at end-of-file. Table rewrite is out of scope (would exceed diff cap and invalidate worked-example).

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_006_015.py` as part of
the PLAN-044 Phase 5 / P0-12 SKILL.md generalisation sweep (PLAN-045
Wave 4 equivalent, Session 41 handoff). The diff is a **pure addition**
— append-only — and applies cleanly via `skill-patch-apply.py` which
collects `+`-prefixed lines from the ```diff fence below. No code
execution, no automated mutation; the amendment is a doc-only adopter-
note section appended to the end of the target `SKILL.md`. Stdlib-only
generator; no network; no third-party deps.

Rollback-safe: if promote fails, reverting removes ONLY the added
lines. No other file is touched. No state change. This is what shadow
mode guarantees per ADR-031.

## Proposed diff

```diff
--- a/.claude/skills/core/performance-engineering/SKILL.md
+++ b/.claude/skills/core/performance-engineering/SKILL.md
@@ -175,3 +175,30 @@
 - **setImmediate chunking can cause heap bloat:** if deferred chunks capture large arrays in their closures, each pending chunk retains the whole array. Use `slice()` to create small independent chunks.
 - **EL stall root cause is often DISTRIBUTED:** no single op causes the stall. It's the SUM of: PubSub × N topics, SSE broadcast, JSON.stringify, Date.now, Map ops — all multiplied by event count per batch. You must reduce ALL sources simultaneously.
 - **NEVER trust warm-up logs for perf validation** — steady-state workload (5min+) creates much larger batches
+## Adopter Note — Language + Metric Portability (PLAN-044 P0-12)
+
+This skill is **Node.js-focused** — the portability note near
+the top is honest about that. The §Performance Budgets table
+(Event loop p50/p99, Heap used, RSS main/adapter, IPC latency,
+Event throughput) carries numeric columns (e.g. `~604MB`,
+`~2-4GB`, `~16-24GB`, `~50ms coalesce`, `~400+ events/s`) that
+are **snapshots of the originating `ceo-orchestration` dogfood
+project** — a Node.js real-time adapter on specific hardware.
+
+For your own adopter:
+
+- Establish your own budgets against your own baseline. Keep
+  the column headers (budget / current / alert-at) but replace
+  the numbers before acting on them.
+- On non-Node runtimes (Python, Go, Rust, JVM), the V8 /
+  hidden-class / IC subsections do not apply directly — the
+  *mental model* of "monomorphic hot path" / "avoid megamorphic
+  dispatch" / "profile before optimising" transfers, but the
+  concrete techniques and tools do not.
+- The IPC and worker_threads subsections assume Node's cluster/
+  worker IPC model. Python `multiprocessing` / Go goroutines /
+  Rust async runtimes have very different trade-offs.
+
+Treat the text as an illustrated archetype; run your own
+profiling first, and cite your own baseline in any follow-up
+amendment.
```
