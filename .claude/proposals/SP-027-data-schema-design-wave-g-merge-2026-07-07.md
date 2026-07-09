---
id: SP-027
skill_slug: data-schema-design
archetype: data-engineer
proposed_at: 2026-07-07T06:03:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 514
diff_size_removed: 8
sha256_of_diff: null
sha256_of_staged: 439f2336599ca8ada2249f28384d866dde05ec795ee61dcd97f102e80e99d384
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:27Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/database-migrations/
  - affaan-m/ecc@81af4076 skills/postgres-patterns/
  - affaan-m/ecc@81af4076 skills/mysql-patterns/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/data-schema-design/
---

# SP-027 — skill patch proposal (Wave G ADAPT merge — 3 sources folded)

**Target:** `.claude/skills/core/data-schema-design/SKILL.md`
**Archetype:** data-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (THREE upstream skills folded
into one existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **rows 4, 5, 6** — a plan-named/debate-ratified
three-way pile-up onto `data-schema-design`:

- **row 4 — database-migrations** (q5): zero-downtime migration checklist +
  good/bad SQL per ORM, deeper than current coverage.
- **row 5 — postgres-patterns** (q4): index/type/RLS cheat-sheets.
- **row 6 — mysql-patterns** (q4): concrete SQL + MySQL/MariaDB divergences for a
  currently PG-leaning schema skill.

All three fold into ONE SP (per the integrator doctrine: a target getting N merges
= one proposal folding all N). Staged file is 1431 lines vs. the 933-line live
skill (net +498 lines). Per the materialized-list pile-up rule, the three merges
are sequenced as **ordered sub-edits within this one SP** so the patches do not
self-conflict; the staged SKILL.md is the already-reconciled result.

## Provenance note

Clean-room ADAPT for all three sources (upstream informed scope; prose/examples
original, zero ECC strings). Provenance recorded as **three** rows in the root
`NOTICE` Wave G section (one per upstream source dir) plus `inspired_by:`
frontmatter rows. Carries upstream-derived content → rides the **import gate**
(`check-imported-skill.py`) plus `/skill-review`. The merged SKILL.md already
carries `version: 1.1.0`. `scan-injection.py` over all staged Wave G files
(2026-07-07): no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md.

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/data-schema-design/`:

| sha256 | file |
|---|---|
| `702045c2a1b730fe8184e11fa458fc726891b36379c513e9e55cac643187a2c6` | `SKILL.md` (merged, 1439L, v1.1.0) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/core/data-schema-design/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/data-schema-design/SKILL.md
```

Not embedded as a ```diff fence (removal-line contract; whole-file replacement).
Landing is the ceremony below.

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — run `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`; expect the provenance check to resolve against ALL
   THREE Wave G NOTICE rows for this target. Human review ON TOP; pay attention to
   the fenced SQL examples (the `CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route
   applies — verify no example is a live-executing footgun). Verify the sha256 pin.
2. **Approve (shadow apply)** — after review + GPG signature, copy staged SKILL.md
   → `.claude/skills/core/data-schema-design/SKILL.md.shadow.md`; set `status:
   shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-027`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- Three sources fold into one file; the NOTICE ledger carries three rows so the
  per-source attribution is not lost in the single-SP fold.
- No frontmatter diff-line counts (whole-file replacement); reproduction command
  is the review instrument.
- +498 lines is the largest single-target merge in Wave G and is paid per
  activation (`data-schema-design` is not a Wave C pilot). Flag for a future
  progressive-disclosure pass if it enters the context-budget top-3.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 1439 linhas; diff vs live = +514/−8; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
