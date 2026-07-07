---
id: SP-035
skill_slug: codebase-onboarding
archetype: codebase-onboarding
proposed_at: 2026-07-07T06:11:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: null
diff_size_removed: null
sha256_of_diff: null
sha256_of_staged: 5967aa287695c235fee98514f13b6fb535eebe73f816cb079f712f5469502806
claims_declared: false
status: draft
approved_by: null
applied_at: null
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/inherit-legacy-style/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/codebase-onboarding/
---

# SP-035 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/core/codebase-onboarding/SKILL.md`
**Archetype:** codebase-onboarding
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 19** (one of only two clean q5 `+7` selections):
fold `affaan-m/ecc@81af4076` `skills/inherit-legacy-style/` (matrix quality
**q5**) into `codebase-onboarding` — an **anti style-drift** protocol: grill the
existing codebase for its conventions before writing, plus an enforcement hook to
keep new code in the incumbent style. Strong governance fit (this framework
already prizes convention-conformance). Additive; staged file is 605 lines vs. the
515-line live skill (net +90 lines).

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/inherit-legacy-style/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. `scan-injection.py` over all staged Wave G files (2026-07-07):
no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/codebase-onboarding/`:

| sha256 | file |
|---|---|
| `5967aa287695c235fee98514f13b6fb535eebe73f816cb079f712f5469502806` | `SKILL.md` (merged, 605L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/core/codebase-onboarding/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/codebase-onboarding/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP. If the "enforcement hook"
   material implies a real hook script, confirm it is described, not shipped as an
   executable (import-gate check (d)). Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.claude/skills/core/codebase-onboarding/SKILL.md.shadow.md`; set `status:
   shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-035`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- If the enforcement-hook idea should become a real hook, that is a SEPARATE
  settings.json/hook change (its own ceremony) — this SP merges the *guidance*
  only.
- +90 lines paid per activation (not a Wave C pilot); acceptable for q5.
