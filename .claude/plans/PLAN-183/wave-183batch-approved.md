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
Wave: wave-183batch (PLAN-183 — «Batch menor + começar W1», ratificação do Owner de 2026-08-31: settings regenerado nos DOIS alvos — +4 demotions 0-dispatch E o undemote A4 das 7 chaves VETO-bearing (o invariante «nenhuma VETO skill name-only» vira permanente, teste sem xfail), header «INERT AS SHIPPED» no validate.yml.template, e o REGISTRO do AC-5 — a metade «canônica» que a nota ◐ declarava faltante já existia no wiring do CI; o CHECKBOX segue aberto porque a execução real do workflow é W0-US3/OQ-2, e o rail 183-r1 barrou o flip, corretamente)
Patch: .claude/plans/PLAN-183/s335-ceremony-183batch/W183BATCH.patch
Patch-sha256: 620053a28a99dc463bdd05e499142b10538557dce33eeacd7f558eb2b4a55ab7
Patch-base: bc8265157ca2f9821a2544ef3123eb05ffbfd764
Anchor-SHA: ec7e8253d30087f1f39d197c84d8ddfb26b9e0b5
Data: 2026-09-01

## O que esta wave entrega

**Dois arquivos canônicos** (`.claude/settings.json` — KERNEL — e
`templates/settings/settings.base.json`) e **três não-canônicos** que só
são verdadeiros juntos:

1. **`.claude/settings.json`** (canônico, KERNEL — ADR-116 vetor 1+2) — o
   bloco `skillOverrides` regenerado por
   `python3 .claude/scripts/skill-budget-generator.py --jq-fragment`:
   **+4 chaves** name-only para skills domain-tier com 0 dispatches na
   janela (`cpp-testing`, `frontend-slides`, `prisma-patterns`,
   `ui-demo`), 104 → 108. O settings shipado é o DERIVADO —
   e como o gerador é INCREMENTAL, o fragment exato da mudança é MATERIAL
   VERSIONADO (`skill-frag-s335.jq`): `base + fragment` reproduz o
   settings do patch byte a byte (4a/V3a) com não-vácuo nomeado na mesma
   prova (`prisma-patterns` ABSENT→name-only — 4e/V3b). O gate real (`check_harness_config.py`) roda verde sobre o
   settings pós-patch (4g/V4).
2. **`templates/.github/workflows/validate.yml.template`** (livre) — o
   header «INERT AS SHIPPED» no molde EXATO de
   `benchmarks.yml.template:3-7`: comentário puro, a ativação é o `git mv`
   explícito do adopter. O contrato frozen-subset (11 steps + pins) fica
   INTACTO — `test_validate_template_frozen_subset.py` 7/7 (4c/V2).
3. **`.claude/plans/PLAN-183-adopter-fitness.md`** (livre) — o REGISTRO
   do AC-5 **sem flip** (rail 183-r1 barrou o `[x]`, corretamente): a
   «metade canônica» que a nota ◐ da S334 declarava faltante JÁ EXISTE —
   `.github/workflows/smoke-install.yml:485` invoca
   `bash scripts/tests/smoke-install.sh` por inteiro e a perna de ativação
   vive em `scripts/tests/smoke-install.sh:180`. Zero edição de yml. O
   checkbox permanece aberto porque o texto do AC exige «EXECUTAR o CI
   entregue» e a execução REAL é exatamente W0-US3 + OQ-2 (decisão do
   Owner) — um `[x]` seria registro falso. O V5 do LAND prova as DUAS
   metades: nota presente E checkbox intacto.

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
- A EXECUÇÃO do workflow ativado no CI do adopter (AC-2/W0-US3/OQ-2) segue
  aberta — decisão do Owner; por isso o AC-5 NÃO flipou nesta wave.
- O header de ativação usa `mv` (não `git mv`): num install fresco o
  template nasce UNTRACKED e `git mv` falha (rail 183-r1). MOLD-FINDING:
  `benchmarks.yml.template:5-7` carrega o MESMO `git mv` latente — fora
  deste patch (3 paths), registrado para cura futura.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-183
Scope:
  - .claude/plans/PLAN-183-adopter-fitness.md
  - .claude/scripts/tests/test_veto_skill_map.py
  - .claude/settings.json
  - templates/.github/workflows/validate.yml.template
  - templates/settings/settings.base.json
<!-- END SIGNED SCOPE -->
