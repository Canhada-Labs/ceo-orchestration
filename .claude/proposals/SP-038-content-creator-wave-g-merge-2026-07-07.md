---
id: SP-038
skill_slug: content-creator
archetype: content-creator
proposed_at: 2026-07-07T06:14:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: 3e877c67c6171f1bac16f63c727eec213a26cdbd87e07c6240707149b9c62ee4
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/brand-voice/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/marketing-global/skills/content-creator/
---

# SP-038 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/marketing-global/skills/content-creator/SKILL.md`
**Archetype:** content-creator
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 24** (`+7` selection — distinct marketing target):
fold `affaan-m/ecc@81af4076` `skills/brand-voice/` (matrix quality **q4**) into
`content-creator` — a reusable **voice-profile** procedure derived from real
brand sources (tone axes, do/don't lexicon, sample rewrites). Additive; staged
file is 493 lines vs. the 416-line live skill (net +77 lines).

## ⚠ Port note (from the materialized list)

The materialized list flags `brand-voice` explicitly: **"strip ECC refs on port."**
The upstream skill was voice-profiled against ECC's own brand sources; the merged
content must carry ZERO ECC brand references, example names, or product strings —
only the reusable *method*. The reviewer must grep the merged body for residual
ECC/employer-class strings (this is exactly the class the Codex pair-rail catches
that a name-only scan misses — see memory `feedback-codex-pair-rail-catches-employer-class`).

## Provenance note

Clean-room ADAPT (upstream informed method only; all example content original,
zero ECC strings by construction). Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/brand-voice/`, MIT) + `inspired_by:` frontmatter.
Carries upstream-derived content → rides the **import gate** plus `/skill-review`.
`scan-injection.py` over all staged Wave G files (2026-07-07): no non-zero exit;
the `check-contamination.sh` employer-class gate is an ADDITIONAL enforcing check
here (Landing mechanics step 1).

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/marketing-global/skills/content-creator/`:

| sha256 | file |
|---|---|
| `3e877c67c6171f1bac16f63c727eec213a26cdbd87e07c6240707149b9c62ee4` | `SKILL.md` (merged, 493L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/marketing-global/skills/content-creator/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/marketing-global/skills/content-creator/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review + contamination gate** — run
   `check-imported-skill.py --skill <staged SKILL.md> --notice NOTICE` AND
   `check-contamination.sh` (the strip-ECC-refs precondition), then human review
   ON TOP; grep for residual ECC/employer-class strings. Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../content-creator/SKILL.md.shadow.md`; set `status: shadow`, `applied_at`,
   `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-038`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- The strip-ECC-refs requirement makes `check-contamination.sh` a hard gate, not a
  courtesy — a residual ECC brand string would also fail the public-repo CI
  contamination gate on push.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +77 lines paid per activation (not a Wave C pilot); acceptable for q4.
