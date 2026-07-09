---
id: SP-039
skill_slug: executive-summary
archetype: executive-summary
proposed_at: 2026-07-07T06:15:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 50
diff_size_removed: 0
sha256_of_diff: 122abd04a06e48ca56f1859d56f08e5222938481829fdbdeea31653b5aa76ee0
sha256_of_staged: 71c29fc2bdf9cd7c203e211ad65713137b24ea16901027e8c8faa70b43ca0c3c
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:30Z
promoted_at: 2026-07-09T15:49:45Z
shadow_mode: false
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
| `0e69d05f23abb6b12b1b9c2fc94d402a8feb04e21d17ea6101d0d18344ba31aa` | `SKILL.md` (merged, 318L) |

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


> **Contagens finais S262 (pós-review, autoritativas):** staged = 318 linhas; diff vs live = +50/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.

> **Soak waiver S263 (2026-07-09):** 7-day parallel-shadow window waived by explicit Owner decision (single-user dogfood; pre-authorized skip semantics of --promote --force-recover). SP-026/SP-034 (AFTER-C) excluded — they keep the full soak.
