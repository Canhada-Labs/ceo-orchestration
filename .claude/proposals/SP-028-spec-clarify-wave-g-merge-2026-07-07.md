---
id: SP-028
skill_slug: spec-clarify
archetype: qa-domain-expert
proposed_at: 2026-07-07T06:04:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 71
diff_size_removed: 0
sha256_of_diff: d1e35ed58b715d9c9c17cdf40adb30d8fb732b71c618afb8e493c4bf54631801
sha256_of_staged: 35ad48fd061656255b54bc568e73049cd0c7b23690e3005d9732faf66a45481a
claims_declared: false
status: promoted
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:27Z
promoted_at: 2026-07-09T15:49:44Z
shadow_mode: false
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/intent-driven-development/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/spec-clarify/
---

# SP-028 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/core/spec-clarify/SKILL.md`
**Archetype:** qa-domain-expert (cross-cut)
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 7**: fold `affaan-m/ecc@81af4076`
`skills/intent-driven-development/` (matrix quality **q5**) into `spec-clarify` —
observable `AC-NNN` acceptance criteria with explicit **must-not** clauses,
verification steps, and a review hook. Additive; staged file is 189 lines vs. the
120-line live skill (net +69 lines).

## ⚠ DELTA flag (from the materialized list — carry into review)

The matrix overlap for `intent-driven-development` names **two** skills
(`core/spec-clarify` **+** `core/requirement-quality-checklist`); the plan/debate
resolved the merge target to **`core/spec-clarify`** (rows 1–18 are verbatim
plan-named). The overlap is not singular — the reviewer should confirm no
duplication is created against `requirement-quality-checklist`, and that the
AC-NNN material lands where spec-clarification (not requirement-quality scoring)
is the job.

## Provenance note

Clean-room ADAPT (upstream informed scope; prose original, zero ECC strings).
Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/intent-driven-development/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. `scan-injection.py` over all staged Wave G files (2026-07-07):
no non-zero exit; enforcing checks at the ceremony.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/spec-clarify/`:

| sha256 | file |
|---|---|
| `d07d53177092dbfe268af2443829c10f6054fb8fbeedb9ab5ae3dc7592f3acc5` | `SKILL.md` (merged, 191L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/core/spec-clarify/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/core/spec-clarify/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP; resolve the DELTA flag
   (no `requirement-quality-checklist` duplication). Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.claude/skills/core/spec-clarify/SKILL.md.shadow.md`; set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-028`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- DELTA (dual-overlap target) is a review-time judgement, recorded here so the
  reviewer inherits it rather than re-deriving it.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +69 lines paid per activation (not a Wave C pilot); small, acceptable for q5.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 191 linhas; diff vs live = +71/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.

> **Soak waiver S263 (2026-07-09):** 7-day parallel-shadow window waived by explicit Owner decision (single-user dogfood; pre-authorized skip semantics of --promote --force-recover). SP-026/SP-034 (AFTER-C) excluded — they keep the full soak.
