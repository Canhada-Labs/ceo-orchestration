# PROPOSED-PATCH — wave-183batch (S335)

Patch: `W183BATCH.patch` (derivado da sombra `shadow-183batch` pelo
`finalize-183batch.sh`; base declarada em `BASE-SHA.txt`).
Patch-sha256: TO-FILL-AT-FINAL-PATCH

## Por path (3)

| path | oráculo | o que muda |
|---|---|---|
| `.claude/settings.json` | CANÔNICO (KERNEL) | `skillOverrides` regenerado pelo `skill-budget-generator --jq-fragment`: +4 name-only 0-dispatch (`cpp-testing`, `frontend-slides`, `prisma-patterns`, `ui-demo`), 104→108; zero remoções/alterações |
| `templates/.github/workflows/validate.yml.template` | livre | header «INERT AS SHIPPED» (molde `benchmarks.yml.template:3-7`; comentário puro — frozen-subset intacto) |
| `.claude/plans/PLAN-183-adopter-fitness.md` | livre | REGISTRO do AC-5 (evidência: `smoke-install.yml:485` → `smoke-install.sh:180`) **sem flip** — o rail 183-r1 barrou o `[x]`: a execução real do workflow é W0-US3/OQ-2 |

## O que este patch NÃO faz

- Não remove nem altera override existente (delta medido = só adds).
- Não toca o frozen-subset do template (11 steps + pins byte-idênticos —
  `test_validate_template_frozen_subset.py` 7/7 é a régua).
- Não faz o W3-P1 (de-embed p/ settings.base.json) — follow-up por regra
  do runbook (coordenação com `_derivation` da wave-F).
- Não executa o workflow ativado no CI do adopter (AC-2, gateado na OQ-2).

## Evidência pré-assinatura (S335, sombra base 8f01202)

- Derivação: `base + skill-frag-s335.jq` (fragment VERSIONADO — o gerador
  é incremental e re-gerar sobre a árvore atualizada emite 0 chaves) ⇒
  settings do patch BYTE A BYTE; não-vácuo nomeado: `prisma-patterns`
  ABSENT no base → name-only no derivado.
- `check_harness_config.py` rc 0 sobre o settings pós-patch (<1s).
- frozen-subset: **7 passed / 0 skipped**. jq parse ok; overrides 108.
- ceremony-lint: 0 blockings. Rail codex r1: 1 P1 + 1 P2, ambos REAIS e
  curados (flip do AC-5 revertido a registro; header com `mv`);
  `rail-round-1.md` registrado.
