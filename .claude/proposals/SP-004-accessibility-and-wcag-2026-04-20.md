---

id: SP-004
skill_slug: accessibility-and-wcag
archetype: accessibility-engineer
proposed_at: 2026-04-20T09:16:54Z
source_lessons:
  - session-38-cont-sp-004-accessibility-and-wcag
scan_injection_pass: true
diff_size_added: 24
diff_size_removed: 0
sha256_of_diff: 5e7732258e5da8d53e8b12ca054f7715b96f1e3628062fa940b0a0cfa881baa8
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T09:58:51Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-004 — skill patch proposal

**Target:** `.claude/skills/frontend/accessibility-and-wcag/SKILL.md`  
**Archetype:** accessibility-engineer  
**Kind:** manual cross-link closure (Session 38 continuation)

## Rationale

PLAN-035 Wave B Phase 2 reference-data cross-link. The charts-accessibility.yaml ships 25 chart types with A/B/C/D/AA/AAA grades + mandatory A11y Fallback rubric — genuinely unique in the Claude Code skills ecosystem per PLAN-026 audit finding 02. This patch makes the rubric part of the reviewer's inference path.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_proposals.py` as part of the Session 38 100%-closure sweep (Owner autorizou in-chat 2026-04-20). The diff is a pure addition — append-only — and applies cleanly via `skill-patch-apply.py` which collects `+`-prefixed lines from the ```diff fence below. No code execution / automated mutation; the amendment is a doc-only cross-link to already-shipped artifacts (PROTOCOL.md §Artifact Paradox, docs/OWASP-LLM-TOP-10.md + benchmark, reference/*.yaml under frontend skills).

## Proposed diff

```diff
--- a/.claude/skills/frontend/accessibility-and-wcag/SKILL.md
+++ b/.claude/skills/frontend/accessibility-and-wcag/SKILL.md
@@ -157,3 +157,27 @@
 5. Fix color contrast for text3, accent (light), positive (light)
 6. Add aria-describedby + aria-required to ALL forms
 7. Add keyboard handlers to ALL custom interactive components
+## Reference Data — Chart Accessibility Grading (PLAN-035)
+
+Curated chart-type → accessibility-grade rubric under
+`reference/charts-accessibility.yaml`:
+
+- **25 chart types** (line, bar, pie, scatter, heatmap, sankey, radar,
+  waterfall, box, treemap, etc.)
+- Each carries `Accessibility Grade` in the rubric `{A, AA, AAA, B, C,
+  D}` — AA/AAA = WCAG conformance proven; A = general pattern, not
+  WCAG-verified; B/C/D = structural accessibility risk with
+  documented fallback.
+- Mandatory `A11y Fallback` field per chart type (e.g. "dashed/dotted
+  lines per series + togglable data table with timestamps and values"
+  for Line Chart).
+- `Color Guidance` + `Data Volume Threshold` + `Library Recommendation`
+  + `Interactive Level` fields guide implementation.
+
+When reviewing a new chart component, the accessibility specialist
+MUST look up the chart's row in this reference before approving —
+any chart graded B / C / D requires an explicit A11y Fallback ticket
+linked to the PR.
+
+License: MIT © 2024 Next Level Builder. See
+`.claude/skills/frontend/NOTICE.md`.
```

