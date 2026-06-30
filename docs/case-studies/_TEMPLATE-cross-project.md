# Cross-adopter case study — {{SUMMARY_TITLE}}

> **Status:** `draft` | `complete`
> **Sprint:** PLAN-{{NNN}} (Sprint 16 cross-adopter analysis)
> **Adopters compared:** {{csv_of_adopter_names}}
> **Owner verdict:** Y (promote to next sprint / public) | N (iterate) | `pending`

## 1. Scope

Este case study agrega evidência de ≥2 adopters instalados em sprints
consecutivos (ex: adopter-1 em Sprint 15 + adopter-2 em Sprint 16) pra
responder duas perguntas:

1. **Generalização:** o framework funciona fora do domínio original ou
   está over-fitted pra fintech-trading?
2. **Gate pra Sprint 17 público:** há evidência suficiente pra abrir
   repo + publicar npm + Discussions, ou precisamos mais um adopter
   interno antes?

**Prerequisite:** ≥2 single-project case studies já existem em
`docs/case-studies/<adopter>-case-study.md`.

## 2. Adopters included

| Adopter | Domain | Sprint | Case study | Verdict |
|---------|--------|--------|------------|---------|
| {{name_A}} | {{domain_A}} | PLAN-{{NNN_A}} | [`{{name_A}}-case-study.md`]({{name_A}}-case-study.md) | Y/N |
| {{name_B}} | {{domain_B}} | PLAN-{{NNN_B}} | [`{{name_B}}-case-study.md`]({{name_B}}-case-study.md) | Y/N |
| ... | ... | ... | ... | ... |

## 3. Cross-adopter metrics comparison

Gerado via `.claude/scripts/compare-adopters.py` feeding weekly JSON
reports de cada adopter. Raw output abaixo (cole o markdown inteiro
preservando tabela + seções):

```
python3 .claude/scripts/compare-adopters.py \
  --input {{name_A}}=.claude/plans/PLAN-{{NNN_A}}/metrics/week-2.json \
  --input {{name_B}}=.claude/plans/PLAN-{{NNN_B}}/metrics/week-2.json \
  --baseline {{name_A}}
```

{{paste_compare_adopters_output_here}}

## 4. Patterns que generalizam

Itens que funcionaram similarmente em ambos adopters — evidência de que
o framework tem estrutura universal, não cosmético.

- **{{pattern_1}}** — {{evidence: e.g. "both adopters converged to <5% veto rate by week 2"}}
- **{{pattern_2}}** — {{evidence}}
- **{{pattern_3}}** — {{evidence}}

## 5. Divergências por domínio

Itens que apareceram em um adopter mas não no outro — sinalizam onde o
framework precisa de domain profiles ou é legitimamente domain-agnóstico
por design.

- **{{divergence_1}}** — {{e.g. "trading-hft needed 3 custom skills around
  order routing; lgpd-heavy-saas needed 0 custom skills"}}
- **{{divergence_2}}** — {{analysis: ship new domain profile? document as
  known gap? accept?}}

## 6. Framework changes shipped cross-sprint

| Sprint | PRs | Net LOC | Type |
|--------|-----|---------|------|
| PLAN-{{NNN_A}} | {{N}} | {{+/-N}} | {{fixes / features / docs}} |
| PLAN-{{NNN_B}} | {{N}} | {{+/-N}} | {{fixes / features / docs}} |
| **Total** | {{N}} | {{+/-N}} | — |

Framework foi **mostly stable / evolved significantly** during validação.

## 7. Maturity assessment

### Ready-for-public signals

- [ ] Both adopters completed 14d+ without blocking P0 unfixed
- [ ] Veto rate <10% sustained across adopters week 2+
- [ ] Framework fixes during sprint converged (late-sprint PR count
      lower than early-sprint)
- [ ] Case studies reviewed and signed off by Owner for both adopters
- [ ] No domain-specific critical gaps blocking generic adopters

### Not-ready-for-public signals

- [ ] P0 fixes shipped in final week (means there's still a core bug)
- [ ] Veto rate trending UP in either adopter
- [ ] Custom skills count >10 — framework baseline is too narrow
- [ ] One adopter abandoned mid-window
- [ ] Owner subjective "still feels brittle" gut check

## 8. Owner verdict

**Decision:** `Y` (go public via Sprint 17) | `N` (one more internal sprint)

**Rationale (3-5 sentences):**

{{honest_reasoning_including_non_numeric_factors}}

**If Y:** Sprint 17 kicks off with public launch checklist. Case study
published to `docs/case-studies/` in public repo.

**If N:** identify missing adopter (third adopter? different domain?)
or specific framework gap to close before re-attempting.

---

**Generated from:** `docs/case-studies/_TEMPLATE-cross-project.md` (PLAN-015 Phase 0.2).
Do not hand-edit the template file — copy it first.
