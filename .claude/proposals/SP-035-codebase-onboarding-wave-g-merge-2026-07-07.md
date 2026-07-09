---
id: SP-035
skill_slug: codebase-onboarding
archetype: codebase-onboarding
proposed_at: 2026-07-07T06:11:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 96
diff_size_removed: 4
sha256_of_diff: null
sha256_of_staged: 003ac9aba31d4151303c1c90ac776710ed0d0186a044c34e9ea9d174c9671a4a
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:29Z
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
already prizes convention-conformance). Additive-with-2-integration-seams (reading-order renumbering 6->7 + expanded Phase 7 acceptance criterion; 95 ins / 3 del — reviewed, no content lost); staged file is 605 lines vs. the
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
| `fe61d1a3e10f0af4235e17f6a3975d0d7e6590944e22e2e3da869582603cc0da` | `SKILL.md` (merged, 607L) |

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


> **Contagens finais S262 (pós-review, autoritativas):** staged = 607 linhas; diff vs live = +96/−4; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
