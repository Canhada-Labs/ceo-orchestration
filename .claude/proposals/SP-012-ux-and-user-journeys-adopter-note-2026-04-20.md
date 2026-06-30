---


id: SP-012
skill_slug: ux-and-user-journeys
archetype: ux-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-ux-and-user-journeys
scan_injection_pass: true
diff_size_added: 28
diff_size_removed: 0
sha256_of_diff: 555348d10f7e9e0821acddc8419feef3d2d453d0f9802aada3585aa4aba49419
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T16:07:46Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-012 — skill patch proposal

**Target:** `.claude/skills/frontend/ux-and-user-journeys/SKILL.md`
**Archetype:** ux-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `ux-and-user-journeys/SKILL.md` is already mostly `EXAMPLE (fintech domain)`-labelled in its questions section — but the §Current State, §UX Principles for Financial Data Platforms heading, and §Navigation Architecture tree still carry unlabelled fintech specifics (17-step tour, src/onboarding/, Markets/PRO Terminal). This proposal appends a consolidated mapping table so the fresh adopter can do a mental substitute-rename pass on the full skill rather than trip on `Financial Data Platforms` and assume the skill does not apply to them.

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
--- a/.claude/skills/frontend/ux-and-user-journeys/SKILL.md
+++ b/.claude/skills/frontend/ux-and-user-journeys/SKILL.md
@@ -108,3 +108,31 @@
 - EXAMPLE (fintech domain): Should Traditional/FX/Macro/News be separate pages or tabs?
 - EXAMPLE (fintech domain): Should Derivatives be a standalone page or part of a Markets super-page?
 - EXAMPLE (fintech domain): Is the PRO Terminal discoverable enough?
+## Adopter Note — Fintech Framing is Example-Only (PLAN-044 P0-12)
+
+This skill is **universal UX** despite heavy fintech illustration.
+Concrete elements drawn from the originating `ceo-orchestration`
+dogfood project include:
+
+- §Current State ("17-step guided tour", "6 files in
+  src/onboarding/", "Phase 4 page-by-page product audit") —
+  project-specific numbers, not prescriptive.
+- §UX Principles for Financial Data Platforms section heading —
+  the principles (progressive disclosure, data density, first-
+  time experience) are universal; the `Financial Data Platforms`
+  qualifier is example-only.
+- §Navigation Architecture tree (`Markets / Exchanges / Arbitrage
+  / OrderBook / Analytics / Trading / Portfolio / PRO Terminal`)
+  is the dogfood fintech-console's IA — already labelled
+  `EXAMPLE: fintech domain`.
+- §Key UX Questions section (the final block above) — all
+  labelled `EXAMPLE (fintech domain)`, kept for worked-example
+  value.
+
+Adopter-side mapping: replace "Markets / PRO Terminal /
+Portfolio" with your own domain's IA, replace "17-step tour /
+6 files in src/onboarding" with your own onboarding numbers,
+and drop the "Financial Data Platforms" qualifier from the
+UX Principles heading when spawning a non-fintech archetype.
+The section structure (Current State → Principles → IA →
+Real-Time UX → Key Questions) transfers as a template.
```
