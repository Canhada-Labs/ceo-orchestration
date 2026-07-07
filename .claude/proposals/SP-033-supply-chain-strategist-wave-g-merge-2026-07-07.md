---
id: SP-033
skill_slug: supply-chain-strategist
archetype: supply-chain-strategist
proposed_at: 2026-07-07T06:09:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: b38a1776ea3d4c29fd20c931f7157901379b7a18edccfd612be78e16b6958d57
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/carrier-relationship-management/
  - affaan-m/ecc@81af4076 skills/customs-trade-compliance/
  - affaan-m/ecc@81af4076 skills/logistics-exception-management/
  - affaan-m/ecc@81af4076 skills/inventory-demand-planning/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/supply-chain/skills/supply-chain-strategist/
---

# SP-033 — skill patch proposal (Wave G ADAPT merge — 4 sources folded)

**Target:** `.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md`
**Archetype:** supply-chain-strategist
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (FOUR upstream skills — the
"supply-chain quartet" — folded into one existing catalog skill; no new skill
file; catalog count unchanged)

## Rationale

Wave G materialized-merge **rows 12, 13, 14, 15** — a plan-named/debate-ratified
four-way pile-up onto `supply-chain-strategist`:

- **row 12 — carrier-relationship-management** (q5): dense freight knowledge (RFP,
  carrier scorecard, FMCSA).
- **row 13 — customs-trade-compliance** (q4): GRI/HS classification, FTA, denied-
  party screening.
- **row 14 — logistics-exception-management** (q4): detention/claims/exception
  windows.
- **row 15 — inventory-demand-planning** (q4): dense demand-planning knowledge.

All four fold into ONE SP (a target getting N merges = one proposal folding all
N). Staged file is 702 lines vs. the 340-line live skill (net +362 lines). Per
the pile-up rule, the four merges are sequenced as **ordered sub-edits within this
one SP** so the patches do not self-conflict; the staged `SKILL.md.staged` is the
already-reconciled result.

## Provenance note

Clean-room ADAPT for all four sources (upstream informed scope; prose original,
zero ECC strings). Provenance recorded as **four** rows in the root `NOTICE` Wave
G section (one per upstream source dir) plus `inspired_by:` frontmatter rows.
Carries upstream content → rides the **import gate** plus `/skill-review`.
`scan-injection.py` over all staged Wave G files (2026-07-07): no non-zero exit;
enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md.

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/supply-chain/skills/supply-chain-strategist/`:

| sha256 | file |
|---|---|
| `b38a1776ea3d4c29fd20c931f7157901379b7a18edccfd612be78e16b6958d57` | `SKILL.md.staged` (merged, 702L) |

Note: the staged file carries the `.staged` suffix; the shadow/promote target is
the un-suffixed live `SKILL.md`.

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md.staged
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md.staged> --notice NOTICE`; expect the provenance check to resolve
   against ALL FOUR Wave G NOTICE rows for this target. Human review ON TOP.
   Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged `SKILL.md.staged` →
   `.../supply-chain-strategist/SKILL.md.shadow.md`; set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-033`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- Four sources fold into one file; the NOTICE ledger carries four rows so the
  per-source attribution is not lost in the single-SP fold.
- +362 lines is the second-largest Wave G merge and is paid per activation
  (`supply-chain-strategist` is not a Wave C pilot). Flag for a future
  progressive-disclosure pass if the domain sees real dogfood traffic.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
