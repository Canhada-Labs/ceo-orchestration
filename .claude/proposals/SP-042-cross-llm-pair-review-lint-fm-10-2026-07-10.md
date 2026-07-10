---
id: SP-042
skill_slug: cross-llm-pair-review
archetype: none   # core governance skill — SP-018 precedent (no owning archetype)
proposed_at: 2026-07-10T21:30:00Z
source_lessons:
  - plan-153-closeout-residual-lint-fm-10
scan_injection_pass: true
diff_size_added: 0
diff_size_removed: 1
sha256_of_diff: 3dbc5bd637f7b40d044d1c46cc3ad52988d078735705b1ef8e40cc5fbec49ca3
sha256_of_staged: b86ed601c6a03a1800e02c4e86fb992c7f02e60c1351d6fd7b1e2b8e02ebd750
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-10T22:59:59Z
promoted_at: 2026-07-10T22:59:59Z
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # S264/OQ4 precedent; frontmatter-only, zero doctrine delta
proposal_type: lint-hygiene-frontmatter-removal
patch_source: inline diff fence (below)
---

# SP-042 — drop empty `inspired_by: []` from cross-llm-pair-review (LINT-FM-10)

**Target:** `.claude/skills/core/cross-llm-pair-review/SKILL.md`
**Kind:** lint-hygiene frontmatter removal — one line, zero doctrine change.

## Rationale

`lint-skills.py` LINT-FM-10 ERRORs on an `inspired_by:` key with no list
entries. `cross-llm-pair-review/SKILL.md` carries `inspired_by: []` — the
only skill in the 166-skill catalog with the empty-inline-list form. The
skill has no upstream inspiration source, so the truthful fix is to remove
the key (key-absent is the linter-accepted form for skills with no
upstream), not to invent entries. Pre-existing error, named as a residual
in PLAN-153's closeout ("pre-existing cross-llm-pair-review lint error
(needs an SP)"); this SP retires it.

## Soak waiver

The 7-day shadow soak exists for doctrine-bearing SKILL.md content changes.
This diff removes one empty frontmatter key: no section, bullet, or
instruction text changes; `sha256_of_staged` above pins the exact post-apply
file. Owner ratifies the waiver by detach-signing this proposal
(S264/OQ4 waiver precedent). Applied Owner-shell, same route as the Wave
C/D restructure SPs (pipeline `_apply_unified_diff` is append-only by
design and cannot express a removal).

## Diff

```diff
--- a/.claude/skills/core/cross-llm-pair-review/SKILL.md
+++ b/.claude/skills/core/cross-llm-pair-review/SKILL.md
@@ -8,7 +8,6 @@
   - Checking promotion gate eligibility before v1.x.0 GA tag
 plan_refs: [PLAN-075, PLAN-081]
 adr_refs: [ADR-052, ADR-105, ADR-106, ADR-107, ADR-108, ADR-111]
-inspired_by: []
 # --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
 domain: core
 priority: 3
```

## Verification

- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines after apply
  (LINT-FM-10 retired; pre-existing WARNs unaffected).
- `sha256(SKILL.md post-apply) == sha256_of_staged` (asserted by the
  landing script before commit).
