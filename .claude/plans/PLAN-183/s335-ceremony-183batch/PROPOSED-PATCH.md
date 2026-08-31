# PROPOSED-PATCH — wave-183batch (S335)

Patch: `W183BATCH.patch` (derivado da sombra `shadow-183batch` pelo
`finalize-183batch.sh`; base declarada em `BASE-SHA.txt`).
Patch-sha256: bde333f02df59195f2574d3f9f3299aca702fb3fc169d1e0170b1f1f2899d9fc

## Por path (5)

| path | oráculo | o que muda |
|---|---|---|
| `.claude/settings.json` | CANÔNICO (KERNEL) | +4 demotions 0-dispatch (skill-frag versionado) **− 7 undemote A4** (veto-undemote versionado, rail 183-r4: chaves VETO-bearing fora do name-only), 104→101 |
| `templates/settings/settings.base.json` | CANÔNICO | −7 undemote A4 (104→97) — o template do adopter nasce com as VETO skills descritas |
| `.claude/scripts/tests/test_veto_skill_map.py` | livre | `@expectedFailure` REMOVIDO + teste-companheiro deletado, exatamente como o arquivo instruía — o invariante «nenhuma VETO skill name-only» vira permanente (21 passed reais) |
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
