---
id: SP-039
skill_slug: executive-summary
archetype: executive-summary
proposed_at: 2026-07-07T06:15:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: 16ad96dc16f45891e25a61dd33e35237b277db1ba87417afd2adc9aed7e9b116
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/competitive-report-structure/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/business-support/skills/executive-summary/
---

# SP-039 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/business-support/skills/executive-summary/SKILL.md`
**Archetype:** executive-summary
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 25** (`+7` selection — distinct business-support
target; the cut is at exactly 7): fold `affaan-m/ecc@81af4076`
`skills/competitive-report-structure/` (matrix quality **q4**) into
`executive-summary` — a decision-grade report structure with white-space
discipline (lead with the decision, evidence density, scannable layout). Additive;
staged file is 312 lines vs. the 268-line live skill (net +44 lines).

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/competitive-report-structure/`, MIT) +
`inspired_by:` frontmatter. Carries upstream content → rides the **import gate**
plus `/skill-review`. `scan-injection.py` over all staged Wave G files
(2026-07-07): no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/business-support/skills/executive-summary/`:

| sha256 | file |
|---|---|
| `16ad96dc16f45891e25a61dd33e35237b277db1ba87417afd2adc9aed7e9b116` | `SKILL.md` (merged, 312L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/business-support/skills/executive-summary/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/business-support/skills/executive-summary/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP. Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../executive-summary/SKILL.md.shadow.md`; set `status: shadow`, `applied_at`,
   `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-039`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +44 lines paid per activation (not a Wave C pilot); small, acceptable for q4.
- The next eligible q4 rows (`customer-billing-ops`, `gan-style-harness`,
  `iterative-retrieval`, `kubernetes-patterns`, `prompt-optimizer`,
  `regex-vs-llm-structured-text`, `returns-reverse-logistics`) fall below this cut
  and roll into §Deferred.
