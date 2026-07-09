---
id: SP-037
skill_slug: mobile-app-builder
archetype: mobile-app-builder
proposed_at: 2026-07-07T06:13:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 115
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: 1d644f9b5bd8db652ba886822cbf757c84e14de43bbe5c42641a24c8584b4b09
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:30Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/android-clean-architecture/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/mobile/skills/mobile-app-builder/
---

# SP-037 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/mobile/skills/mobile-app-builder/SKILL.md`
**Archetype:** mobile-app-builder
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 22** (`+7` selection — first mobile candidate
alphabetically; dart-flutter, kotlin-*, react-native, swift* pile on the same
target and were skipped): fold `affaan-m/ecc@81af4076`
`skills/android-clean-architecture/` (matrix quality **q4**) into
`mobile-app-builder` — modules / DI / Room / Ktor with real code, deepening the
skill past the generic builder. Additive; staged file is 555 lines vs. the
446-line live skill (net +109 lines).

## Provenance note

Clean-room ADAPT (upstream informed scope; prose/examples original, zero ECC
strings). Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/android-clean-architecture/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. Any Kotlin/Room/Ktor fence inherits the
`CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route. `scan-injection.py` over all
staged Wave G files (2026-07-07): no non-zero exit; enforcing checks at the
ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/mobile/skills/mobile-app-builder/`:

| sha256 | file |
|---|---|
| `00ff5c83ae52e269b5121ff86de4b1e1003f3d157998053e669bf06d773e128d` | `SKILL.md` (merged, 561L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/mobile/skills/mobile-app-builder/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/mobile/skills/mobile-app-builder/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP; confirm code fences are
   illustrative (no upstream fetch/exec, import-gate check (d)). Verify the sha256
   pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../mobile-app-builder/SKILL.md.shadow.md`; set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-037`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- The other mobile ADAPTs (dart-flutter, kotlin-*, react-native, swift*) roll into
  §Deferred to keep this a single-target merge; revisit after `/skill-health`.
- +109 lines paid per activation (not a Wave C pilot); acceptable for q4.

> **Emenda S262 (review):** o staged nao carrega token literal `SP-NNN`; no promote, GRAVE o id deste SP na linha de changelog do arquivo promovido (adicionando a linha se o skill nao tiver changelog), em vez de substituir um token.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 561 linhas; diff vs live = +115/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
