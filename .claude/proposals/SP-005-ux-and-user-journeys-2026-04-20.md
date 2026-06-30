---

id: SP-005
skill_slug: ux-and-user-journeys
archetype: ux-engineer
proposed_at: 2026-04-20T09:16:54Z
source_lessons:
  - session-38-cont-sp-005-ux-and-user-journeys
scan_injection_pass: true
diff_size_added: 19
diff_size_removed: 0
sha256_of_diff: b326b1475012a53e5cdea83b2c04d77c6d2d039a52a5a3b9ebb65d5d45a00842
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T09:58:51Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-005 — skill patch proposal

**Target:** `.claude/skills/frontend/ux-and-user-journeys/SKILL.md`  
**Archetype:** ux-engineer  
**Kind:** manual cross-link closure (Session 38 continuation)

## Rationale

PLAN-035 Wave B Phase 2 reference-data cross-link. 99 guidelines across 15 categories with Do/Don't + good/bad code examples + severity. This patch wires the agent to grep guidelines during review instead of improvising rules. Closes ui-ux-pro-max-skill audit T2 reverse link.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_proposals.py` as part of the Session 38 100%-closure sweep (Owner autorizou in-chat 2026-04-20). The diff is a pure addition — append-only — and applies cleanly via `skill-patch-apply.py` which collects `+`-prefixed lines from the ```diff fence below. No code execution / automated mutation; the amendment is a doc-only cross-link to already-shipped artifacts (PROTOCOL.md §Artifact Paradox, docs/OWASP-LLM-TOP-10.md + benchmark, reference/*.yaml under frontend skills).

## Proposed diff

```diff
--- a/.claude/skills/frontend/ux-and-user-journeys/SKILL.md
+++ b/.claude/skills/frontend/ux-and-user-journeys/SKILL.md
@@ -108,3 +108,22 @@
 - EXAMPLE (fintech domain): Should Traditional/FX/Macro/News be separate pages or tabs?
 - EXAMPLE (fintech domain): Should Derivatives be a standalone page or part of a Markets super-page?
 - EXAMPLE (fintech domain): Is the PRO Terminal discoverable enough?
+## Reference Data — UX Guidelines (PLAN-035)
+
+Curated UX-review guidelines under `reference/guidelines.yaml`:
+
+- **99 guidelines** across categories: Navigation, Forms, Loading
+  States, Empty States, Errors, Feedback, Modals, Progress,
+  Accessibility, Mobile, Animations, Typography, Colors, Spacing,
+  Branding.
+- Each carries: `Platform` (Web / Mobile / Both), `Description`,
+  `Do` + `Don't` rules, `Code Example Good` + `Code Example Bad`,
+  `Severity` (Critical / High / Medium / Low).
+
+When reviewing a page or flow with this skill loaded, the UX
+specialist MUST grep the guidelines file for the feature category
+(e.g. "Forms" when reviewing a signup screen) and surface any
+Critical / High guidelines the implementation violates.
+
+License: MIT © 2024 Next Level Builder. See
+`.claude/skills/frontend/NOTICE.md`.
```

