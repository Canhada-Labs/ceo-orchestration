---


id: SP-010
skill_slug: accessibility-and-wcag
archetype: accessibility-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-accessibility-and-wcag
scan_injection_pass: true
diff_size_added: 22
diff_size_removed: 0
sha256_of_diff: 9c1f931bedf34b4fbab2c1c84da7f4e1beaac98301fc07a366cf611b51a6c738
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T16:07:46Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-010 — skill patch proposal

**Target:** `.claude/skills/frontend/accessibility-and-wcag/SKILL.md`
**Archetype:** accessibility-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `accessibility-and-wcag/SKILL.md` carries originating-project audit numbers dated 2026-03-23 in §Current State (WCAG score ~15-20%, 71 charts, specific design-token names `text3` / `accent` / `positive`). A fresh adopter reading the skill would either follow prescriptive "fix color contrast for text3" instructions that reference tokens they do not own, or mis-interpret the 15-20% score as their baseline. This proposal appends a disclaimer that names the audit as an originating-project worked-example and points the adopter at the §Audit Reference workflow already defined. In-place rewrite of §Current State to blank placeholders was considered — rejected because it destroys the worked-example value of seeing what a first-pass audit output looks like. Non-additive clean-up (renaming token refs to generic placeholders) flagged for CEO (SUMMARY).

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
--- a/.claude/skills/frontend/accessibility-and-wcag/SKILL.md
+++ b/.claude/skills/frontend/accessibility-and-wcag/SKILL.md
@@ -157,3 +157,25 @@
 5. Fix color contrast for text3, accent (light), positive (light)
 6. Add aria-describedby + aria-required to ALL forms
 7. Add keyboard handlers to ALL custom interactive components
+## Adopter Note — Current-State Snapshot is Originating-Project (PLAN-044 P0-12)
+
+The §Current State (2026-03-23 Audit) subsection and the
+§Immediate Actions list carry concrete numbers and named tokens
+(`text3`, `accent (light)`, `positive (light)`, `71 charts`,
+`WCAG 2.1 AA Score: ~15-20%`) that come from the originating
+`ceo-orchestration` dogfood frontend audit — a specific
+fintech-console React + Tailwind codebase snapshotted on
+2026-03-23. Those numbers do **not** describe your adopter
+codebase.
+
+When this skill loads in a fresh adopter project, treat the
+current-state block and the action list as a **worked example**
+of what a first-pass accessibility audit output looks like, not
+as a diagnosis of your product.
+
+Your own accessibility audit should produce
+`FRONTEND_AUDIT_<date>.md` (as the §Audit Reference subsection
+already suggests) and override the current-state figures before
+any component work proceeds. The §Patterns / §WCAG 2.1 AA
+Requirements sections above the current-state snapshot are
+universal and apply as-is.
```
