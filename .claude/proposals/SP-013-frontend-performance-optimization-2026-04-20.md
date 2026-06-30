---


id: SP-013
skill_slug: frontend-performance-optimization
archetype: frontend-performance-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-frontend-performance-optimization
scan_injection_pass: true
diff_size_added: 27
diff_size_removed: 0
sha256_of_diff: a47d964272e0dd1d3ec82a8fcd65af18194311fcf2863901180378045fbfc0e5
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-013 — skill patch proposal

**Target:** `.claude/skills/frontend/frontend-performance-optimization/SKILL.md`
**Archetype:** frontend-performance-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `frontend-performance-optimization/SKILL.md` carries a dense §Current Metrics (V2 Audit 2026-03-24) table and a named-vendor-chunk list from the originating dogfood project. Fresh adopter would either assume `vendor-pdf 1.5MB` is their baseline or inherit the named chunks as prescriptive. This proposal appends a disclaimer enumerating exactly which blocks are snapshot vs universal, and points the adopter at their own bundle-audit workflow.

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
--- a/.claude/skills/frontend/frontend-performance-optimization/SKILL.md
+++ b/.claude/skills/frontend/frontend-performance-optimization/SKILL.md
@@ -184,3 +184,30 @@
 - [ ] Images have `loading="lazy"`
 - [ ] Queries have appropriate `staleTime`
 - [ ] No `Date.now()` or `Math.random()` in render path
+## Adopter Note — Metrics Snapshot is Originating-Project (PLAN-044 P0-12)
+
+The §Current Metrics (V2 Audit 2026-03-24) table and the
+§Bundle Strategy / §Manual Chunks block contain values tied
+to the originating `ceo-orchestration` dogfood frontend — a
+React + Vite + Tailwind fintech console on a specific
+dependency set. Concrete numbers include:
+
+- `Initial gzip ~218KB`, `Main chunk (raw) 793KB`,
+  `vendor-pdf 1.5MB (lazy)`, `Lazy-loaded routes 38/38`,
+  `memo() 445 files`, `useMemo 877`, `useCallback 374 in 119`,
+  `Virtualized lists ~4`, `Inline style={{}} ~1,297`.
+- Named vendor chunks `vendor-charts` / `vendor-supabase` /
+  `vendor-pdf` / `vendor-grid` / `vendor-query` / `vendor-router`
+  / `vendor-i18n` / `vendor-zustand` / `vendor-sonner` /
+  `vendor-radix` / `vendor-helmet` with specific gzip / brotli
+  sizes.
+- The §Lighthouse CI banner (`performance > 0.7, LCP < 4s, CLS
+  < 0.1`) and its targets.
+
+For your adopter project, run your own bundle audit (e.g.
+`vite build --mode=analyse`, `webpack-bundle-analyzer`, or the
+equivalent for your toolchain) and replace the current-metrics
+table with your numbers before optimisation work. The rules
+and patterns (never import heavy libs at top level, lazy-load
+routes, memoise correctly, virtualise lists > 50 items) are
+universal; the numbers and vendor-chunk names are not.
```
