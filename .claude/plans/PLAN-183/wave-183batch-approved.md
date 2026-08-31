# wave-183batch — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S335-183BATCH-SIGN.sh` no momento da assinatura; o
> `OWNER-S335-183BATCH-LAND.sh` aborta no G1 se não casar. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-183
Wave: wave-183batch (PLAN-183 — «Batch menor + começar W1», ratificação do Owner de 2026-08-31: settings.json regenerado pelo skill-budget-generator com +4 skills 0-dispatch demoted, header «INERT AS SHIPPED» no validate.yml.template no molde do benchmarks, e AC-5 fechado por REGISTRO — a metade «canônica» que a nota ◐ declarava faltante já existia no wiring do CI)
Patch: .claude/plans/PLAN-183/s335-ceremony-183batch/W183BATCH.patch
Patch-sha256: TO-FILL-AT-FINAL-PATCH
Patch-base: TO-FILL-AT-FINAL-PATCH
Anchor-SHA: ANCHOR-PLACEHOLDER
Data: DATA-PLACEHOLDER

## O que esta wave entrega

**Um arquivo canônico** (`.claude/settings.json` — KERNEL) e **dois
não-canônicos** que só são verdadeiros juntos:

1. **`.claude/settings.json`** (canônico, KERNEL — ADR-116 vetor 1+2) — o
   bloco `skillOverrides` regenerado por
   `python3 .claude/scripts/skill-budget-generator.py --jq-fragment`:
   **+4 chaves** name-only para skills domain-tier com 0 dispatches na
   janela (`cpp-testing`, `frontend-slides`, `prisma-patterns`,
   `ui-demo`), 104 → 108. O settings shipado é o DERIVADO do gerador —
   idempotência provada no finalize (4a) e no LAND (V3a), com controle
   NEGATIVO em cópia descartável (chave apagada é recuperada pelo
   fragment — 4e/V3b: um fragment que nada escreve seria idempotente por
   vacuidade). O gate real (`check_harness_config.py`) roda verde sobre o
   settings pós-patch (4g/V4).
2. **`templates/.github/workflows/validate.yml.template`** (livre) — o
   header «INERT AS SHIPPED» no molde EXATO de
   `benchmarks.yml.template:3-7`: comentário puro, a ativação é o `git mv`
   explícito do adopter. O contrato frozen-subset (11 steps + pins) fica
   INTACTO — `test_validate_template_frozen_subset.py` 7/7 (4c/V2).
3. **`.claude/plans/PLAN-183-adopter-fitness.md`** (livre) — AC-5 [P0]
   flipado **por REGISTRO, com evidência nomeada**: a «metade canônica»
   que a nota ◐ da S334 declarava faltante JÁ EXISTE —
   `.github/workflows/smoke-install.yml:485` invoca
   `bash scripts/tests/smoke-install.sh` por inteiro e a perna de ativação
   vive em `scripts/tests/smoke-install.sh:180`. Zero edição de yml. A
   «EXECUÇÃO real do workflow ativado» fica deliberadamente FORA: é a
   prova do AC-2, gateada na OQ-2 (decisão do Owner).

## Kernel

`.claude/settings.json` ∈ `_KERNEL_PATHS`. O LAND arma
`CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo (export antes do apply,
unset após o commit, backstop no trap), com o par reason-SLUG + `I-ACCEPT`
validado VIVO contra o contrato do hook — mecanismo idêntico ao adrgate
(`cfab980`) e ao 179close.

## Residuais declarados

- O regen NÃO remove nem altera chave existente (medido: diff = +4 adds);
  as duas entradas fintech name-only citadas no runbook (`:884-885`)
  permanecem — são domain-tier 0-dispatch, demotion legítima do gerador.
- W3-P1 (de-embed dos overrides para `settings.base.json`) ficou FORA por
  decisão do runbook: exige coordenação com a arquitetura `_derivation` da
  wave-F; se a rota não fosse óbvia em 30 min, virava follow-up.
- A EXECUÇÃO do workflow ativado no CI do adopter (AC-2/OQ-2) segue aberta
  — decisão do Owner, não item deste batch.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: APPROVED-BY-PLACEHOLDER
Plans: PLAN-183
Scope:
  - placeholder
<!-- END SIGNED SCOPE -->
