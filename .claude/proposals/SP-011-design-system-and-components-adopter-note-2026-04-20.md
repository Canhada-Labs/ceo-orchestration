---


id: SP-011
skill_slug: design-system-and-components
archetype: frontend-designer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-design-system-and-components
scan_injection_pass: true
diff_size_added: 24
diff_size_removed: 0
sha256_of_diff: 12954ec56e707b6f3dbcc9a6a85601ae6c6995ae186e2c03eba37aac2928596d
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T16:07:46Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-011 — skill patch proposal

**Target:** `.claude/skills/frontend/design-system-and-components/SKILL.md`
**Archetype:** frontend-designer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `design-system-and-components/SKILL.md` carries §Current State (2026-03-23 Audit) with seven numeric scores plus hard-coded file paths `design-tokens.ts` / `src/styles/globals.css`. Fresh adopter would either mis-attribute the 6/10 scores to their own codebase or follow prescriptive paths they do not have. This proposal appends a disclaimer + adopter-workflow direction. The §Empty / §Loading / §Error / §Responsive subsections below are already universal (they name pattern-level contracts, not source-project specifics), so the disclaimer scope is bounded to the top block.

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
--- a/.claude/skills/frontend/design-system-and-components/SKILL.md
+++ b/.claude/skills/frontend/design-system-and-components/SKILL.md
@@ -112,3 +112,27 @@
 - NEVER put business logic in widgets
 - Target: >90% of widgets at <=15 lines
 - Track outliers and refactor the ones that exceed the threshold
+## Adopter Note — Current-State Snapshot is Originating-Project (PLAN-044 P0-12)
+
+The §Current State (2026-03-23 Audit) subsection contains
+concrete `X/10` scores (Component Architecture 6/10, Design
+System 6.5/10, Empty States 2/10, Loading 8/10, Error 7/10,
+Responsive 4/10, PRO Widgets 9/10) and a `47 tokens per theme
+(94 total)` metric. These figures come from the originating
+`ceo-orchestration` dogfood frontend audit of a specific
+fintech-console React + Tailwind codebase and should **not**
+be read as your adopter baseline.
+
+Likewise, the §Design Token System references `design-tokens.ts`
+and `src/styles/globals.css` — those paths are illustrative of
+the pattern ("single source of truth → CSS vars → Tailwind
+bridge"), not prescriptions for your file layout.
+
+For your adopter project:
+
+- Run your own design-system audit; override the 7 scores in
+  §Current State with your numbers before component work.
+- Replace the file paths in §Design Token System with your own
+  equivalents (or keep the pattern if they happen to match).
+- The §Empty / Loading / Error States contract below the
+  current-state block is universal and applies as-is.
```
