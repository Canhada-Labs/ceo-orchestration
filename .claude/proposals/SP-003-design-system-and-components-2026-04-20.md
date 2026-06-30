---

id: SP-003
skill_slug: design-system-and-components
archetype: frontend-designer
proposed_at: 2026-04-20T09:16:54Z
source_lessons:
  - session-38-cont-sp-003-design-system-and-components
scan_injection_pass: true
diff_size_added: 23
diff_size_removed: 0
sha256_of_diff: 63d2990c44bbeb3211d75ebb30fe9d294d39b70d1ea2c0c2fc97e32c4f319625
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T09:58:51Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-003 — skill patch proposal

**Target:** `.claude/skills/frontend/design-system-and-components/SKILL.md`  
**Archetype:** frontend-designer  
**Kind:** manual cross-link closure (Session 38 continuation)

## Rationale

PLAN-035 Wave B Phase 2 reference-data cross-link. The YAML files are shipped (commit f78b016, 2026-04-19) + 33 structural tests enforce integrity. This patch tells the agent to consult the reference before improvising palette / font suggestions. Closes ui-ux-pro-max-skill audit T2.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_proposals.py` as part of the Session 38 100%-closure sweep (Owner autorizou in-chat 2026-04-20). The diff is a pure addition — append-only — and applies cleanly via `skill-patch-apply.py` which collects `+`-prefixed lines from the ```diff fence below. No code execution / automated mutation; the amendment is a doc-only cross-link to already-shipped artifacts (PROTOCOL.md §Artifact Paradox, docs/OWASP-LLM-TOP-10.md + benchmark, reference/*.yaml under frontend skills).

## Proposed diff

```diff
--- a/.claude/skills/frontend/design-system-and-components/SKILL.md
+++ b/.claude/skills/frontend/design-system-and-components/SKILL.md
@@ -112,3 +112,26 @@
 - NEVER put business logic in widgets
 - Target: >90% of widgets at <=15 lines
 - Track outliers and refactor the ones that exceed the threshold
+## Reference Data (PLAN-035 imports)
+
+Curated reference data from `nextlevelbuilder/ui-ux-pro-max-skill`
+(MIT) lives alongside this skill under `reference/`:
+
+- `reference/palettes.yaml` — **161** WCAG-tuned color palettes by
+  product type (SaaS / Micro SaaS / fintech / edtech / etc.) with
+  `Primary`, `On Primary`, `Secondary`, `Accent`, `Background`,
+  `Foreground`, `Card`, `Border`, `Destructive`, `Ring`.
+- `reference/fonts.yaml` — **73** font pairings (heading + body) with
+  Google Fonts URL, CSS import, Tailwind config, mood/style keywords,
+  best-for-category.
+
+When a spawned agent with this skill loaded is asked to propose
+colors / fonts, it SHOULD consult the reference data (via Read /
+Grep on the file path) before improvising. The header of each YAML
+banner points at the license + regen script path.
+
+Attribution: `.claude/skills/frontend/NOTICE.md` (MIT © 2024 Next
+Level Builder).
+
+Regen: `python3 .claude/scripts/import_ui_ux_pro_max.py` (offline
+mode `--offline <dir>` for CI).
```

