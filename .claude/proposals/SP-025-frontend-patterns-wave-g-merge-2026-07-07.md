---
id: SP-025
skill_slug: frontend-patterns
archetype: frontend-engineer
proposed_at: 2026-07-07T06:01:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 144
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: 1c1c68ec0edcbd75523eeb029bc541493ab8a7e2230a668bdff74b2dfdc5fe4e
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:27Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/react-patterns/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-patterns/
---

# SP-025 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/frontend/frontend-patterns/SKILL.md`
**Archetype:** frontend-engineer
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 2**: fold the dense React 18–19 patterns from
`affaan-m/ecc@81af4076` `skills/react-patterns/` (matrix quality **q4**) into
`frontend-patterns` — hooks discipline, RSC/server-component boundaries, form and
action patterns. Additive merge; staged file is 913 lines vs. the 771-line live
skill (net +142 lines of merged material). No pre-existing content rewritten.

## Provenance note

Clean-room ADAPT (upstream informed scope only; prose/examples original, zero ECC
strings). Provenance recorded in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/react-patterns/`, MIT) and an `inspired_by:`-style
frontmatter row. Carries upstream-derived content → rides the **import gate**
(`check-imported-skill.py`) plus `/skill-review`. `scan-injection.py` over all
staged Wave G files (2026-07-07): no non-zero exit; the enforcing checks run at
the ceremony (Landing mechanics step 1).

Rollback-safe: promote replaces exactly one file (SKILL.md); reverting restores
the prior SKILL.md.

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-patterns/`:

| sha256 | file |
|---|---|
| `835c8ab17461c1b1cfcffb2f62955184d0c4212fb2549789e09800c3d2360b45` | `SKILL.md` (merged, 915L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/frontend/frontend-patterns/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/frontend/frontend-patterns/SKILL.md
```

Not embedded as a ```diff fence (`skill-patch-apply.py` refuses removal lines;
whole-file replacement is not an append-only patch). Landing is the ceremony below.

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP. Verify the sha256 pin.
2. **Approve (shadow apply)** — after review + detached GPG signature, copy staged
   SKILL.md → `.claude/skills/frontend/frontend-patterns/SKILL.md.shadow.md`; set
   `status: shadow`, `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-025`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- No frontmatter diff-line counts (whole-file replacement); the reproduction
  command is the review instrument.
- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +142 lines paid per activation (not a Wave C pilot); acceptable for q4, revisit
  if it enters the context-budget top-3.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 915 linhas; diff vs live = +144/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
