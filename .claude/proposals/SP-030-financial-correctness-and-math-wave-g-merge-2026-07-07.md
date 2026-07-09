---
id: SP-030
skill_slug: financial-correctness-and-math
archetype: fintech-quant
proposed_at: 2026-07-07T06:06:00Z
source_lessons:
  - plan-153-wave-g-adapt-merge
scan_injection_pass: true
diff_size_added: 105
diff_size_removed: 0
sha256_of_diff: null
sha256_of_staged: 831c01c295c1a8e82b473c4031b8524c18e8a95a534fb8d647c1b79c9ce6df46
claims_declared: false
status: shadow
approved_by: AE9B236FDAF0462874060C6BCFCFACF00335DC74
applied_at: 2026-07-09T11:33:28Z
promoted_at: null
shadow_mode: true
proposal_type: adapt-merge-enrichment
after_wave_c: false
upstream_sources:
  - affaan-m/ecc@81af4076 skills/evm-token-decimals/
patch_source: .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/financial-correctness-and-math/
---

# SP-030 — skill patch proposal (Wave G ADAPT merge)

**Target:** `.claude/skills/domains/fintech/skills/financial-correctness-and-math/SKILL.md`
**Archetype:** fintech-quant
**Kind:** PLAN-153 Wave G ADAPT-merge enrichment (1 upstream skill folded into an
existing catalog skill; no new skill file; catalog count unchanged)

## Rationale

Wave G materialized-merge **row 9**: fold `affaan-m/ecc@81af4076`
`skills/evm-token-decimals/` (matrix quality **q4**) into
`financial-correctness-and-math` — the sharp **decimals-per-chain / bridge**
mismatch bug class (wrong `10**decimals` scaling across chains and bridges).
Additive; staged file is 441 lines vs. the 340-line live skill (net +101 lines).
Strong fit: our fintech skill already owns money-math correctness; this adds the
EVM-specific decimals footgun.

## Provenance note

Clean-room ADAPT (upstream informed scope; prose/examples original, zero ECC
strings). Provenance in the root `NOTICE` Wave G section
(`affaan-m/ecc@81af4076 skills/evm-token-decimals/`, MIT) + `inspired_by:`
frontmatter. Carries upstream content → rides the **import gate** plus
`/skill-review`. `scan-injection.py` over all staged Wave G files (2026-07-07):
no non-zero exit; enforcing checks at the ceremony. Any fenced arithmetic example
inherits the `CEO_SKILL_PATCH_ALLOW_CODE=1` human-review route.

Rollback-safe: promote replaces exactly one file (SKILL.md).

## Patch source (staged tree, sha256-pinned)

`.claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/financial-correctness-and-math/`:

| sha256 | file |
|---|---|
| `dc8ed004c61c650475ec4241377e1758e5c836f5c5b54ca61e722f0ae48f8cf1` | `SKILL.md` (merged, 445L) |

## Proposed diff (summary — the full diff is NOT embedded)

```
git diff --no-index .claude/skills/domains/fintech/skills/financial-correctness-and-math/SKILL.md \
  .claude/plans/PLAN-153/staged/wave-G/.claude/skills/domains/fintech/skills/financial-correctness-and-math/SKILL.md
```

## Landing mechanics (wake-up ceremony — /skill-review + import gate)

1. **Import gate + /skill-review** — `check-imported-skill.py --skill <staged
   SKILL.md> --notice NOTICE`, then human review ON TOP. Verify the sha256 pin.
2. **Approve (shadow apply)** — copy staged SKILL.md →
   `.../financial-correctness-and-math/SKILL.md.shadow.md`; set `status: shadow`,
   `applied_at`, `approved_by`.
3. **Soak — parallel-shadow, NOT skip (OQ3=c)** — live SKILL.md keeps serving;
   `skill-health.py` telemetry is the regression signal.
4. **Promote** — `mv SKILL.md.shadow.md SKILL.md` under the SKILL.md sentinel gate;
   replace `SP-NNN` in the merged changelog with `SP-030`; set `status: promoted`,
   `promoted_at`.

## Honest residuals

- `scan_injection_pass: true` = advisory exit-0, not a full injection audit.
- +101 lines paid per activation (not a Wave C pilot); acceptable for a
  correctness-critical fintech enrichment.

> **Emenda S262 (review):** o staged nao carrega token literal `SP-NNN`; no promote, GRAVE o id deste SP na linha de changelog do arquivo promovido (adicionando a linha se o skill nao tiver changelog), em vez de substituir um token.


> **Contagens finais S262 (pós-review, autoritativas):** staged = 445 linhas; diff vs live = +105/−0; frontmatter diff_size_added/removed sincronizados. Rail de integridade = pin sha256_of_staged, re-pinado após cada fix.
