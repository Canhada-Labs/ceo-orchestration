---


id: SP-006
skill_slug: chaos-and-resilience
archetype: chaos-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-chaos-and-resilience
scan_injection_pass: true
diff_size_added: 24
diff_size_removed: 0
sha256_of_diff: aa4b51a1a3177f10c4a39ebe38b8afd1e14ef4d5334c9b040b768e476710d168
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-006 — skill patch proposal

**Target:** `.claude/skills/core/chaos-and-resilience/SKILL.md`
**Archetype:** chaos-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `chaos-and-resilience/SKILL.md` carries hard-coded source-project artifacts (TypeScript file:line citations `adapter-process.ts:330-351` / `gateway-wiring.ts` / `supabase-persistence.ts:877` / `index.ts:2557`, a concrete `6.5/10` audit score dated 2026-03-23, and Supabase-specific architecture assumptions) which a fresh-install adopter cannot trace. Rather than an intrusive rewrite — which would blow past the 200-line diff cap, touch stable content, and lose the worked-example value — this proposal appends a disclaimer that names the artifacts as originating-project worked-examples and points the adopter at the generalisation path. Non-additive clean-up is flagged separately for CEO (see SUMMARY).

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
--- a/.claude/skills/core/chaos-and-resilience/SKILL.md
+++ b/.claude/skills/core/chaos-and-resilience/SKILL.md
@@ -524,3 +524,27 @@
 - **Worker threads resourceLimits is HARD KILL** — don't use it; let workers inherit the parent's soft limit. Otherwise workers die without graceful shutdown.
 - **Multiple WS connections sharing one event loop:** setInterval heartbeats get starved by message processing. Use per-connection timeout tracking instead.
 - **Reconnect MUST clear per-connection state:** cleanupConnection() must clear any cached state bound to the connection. Leaving stale state around after a reconnect leads to subtle invariant violations downstream.
+## Adopter Note — Source-Project Artifacts (PLAN-044 P0-12)
+
+The sections above (§Current Resilience Posture, §What Does NOT
+Work, §Top 5 Failure Scenarios) reference TypeScript file paths
+with line numbers (`adapter-process.ts:330-351`, `gateway-
+wiring.ts`, `supabase-persistence.ts:877`, `index.ts:2557`),
+Supabase-specific infrastructure, and a concrete `6.5/10` audit
+score. These are artifacts of the originating `ceo-orchestration`
+dogfood project (a Node.js + Supabase ingestion engine) and are
+intentionally kept as a **worked example** rather than
+prescriptive rules.
+
+When this skill loads in your own project, treat those sections
+as archetype illustrations of failure modes — not as facts about
+your codebase. The underlying patterns (unbounded IPC buffers,
+missing circuit breakers, disabled watchdogs, unshift() bypass,
+non-fatal unhandledRejection) generalise to any long-running
+backend; the file:line citations do not.
+
+For your project, produce your own chaos posture audit and cite
+it in a follow-up amendment (SP-NNN per ADR-031) or a project-
+local override under `.claude/skills/core/chaos-and-resilience-
+<projectslug>.md` if divergence is large enough to warrant a
+fork.
```
