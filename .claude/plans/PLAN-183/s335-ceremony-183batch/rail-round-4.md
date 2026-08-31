# wave-183batch — rail codex rodada 4 (sombra + curas r1-r3, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P1 — verificado REAL e de ALTO VALOR; curado ANTES da r5)

Comando: forma prompt-only (r3b) com contexto de protocolo + resumo das
rodadas. Saída: `<scratchpad S335>/183batch-r4.txt` (4.056 linhas),
TREE-INTACT.

## O achado (o A4 de verdade) e a cura

**[P1] O regen aditivo não removia as demotions de skills VETO-bearing —
que são exatamente o defeito A4.** O runbook («o A4 segue VIVO em
:884-885») fora lido pelo CEO como constatação; a leitura CORRETA — do
rail — é que as chaves name-only sobre skills que carregam VETO derivado
são o BUG (a skill fica sem descrição no discovery automático da sessão),
e o batch existia para curá-lo. Prova pré-existente no repo:
`test_veto_skill_map.py` carregava
`test_no_veto_skill_is_shipped_name_only` sob `@unittest.expectedFailure`
+ um teste-companheiro instruindo LITERALMENTE «quando nenhuma VETO skill
for name-only, a cerimônia landou — delete o decorator e delete este
teste; o invariante é permanente». A cerimônia estava pré-escrita
esperando este patch.

CURA (medida, não inferida):
- Lista dos ofensores extraída da AUTORIDADE (bound ∩ overrides, via o
  próprio teste): `equity-research`, `financial-correctness-and-math`,
  `financial-display`, `kill-switches`, `latency-budgets`,
  `prediction-markets`, `trading-execution` — **7, nos DOIS alvos**
  (`.claude/settings.json` E `templates/settings/settings.base.json`; o
  segundo entra no patch — CANÔNICO, oráculo 1).
- Como o gerador não remove chaves, o undemote é o SEGUNDO material
  versionado (`veto-undemote-s335.jq`, `del()` explícito das 7 —
  idempotente por construção). Cadeias provadas byte a byte
  (finalize 4a / LAND V3a): `base|frag|undemote == settings` e
  `base|undemote == settings.base`. Não-vácuo NOMEADO dos dois materiais
  (frag ESCREVE `prisma-patterns`; undemote APAGA `kill-switches` nos
  dois derivados).
- O teste perde o `@expectedFailure` e o companheiro é DELETADO, como
  instruído: **21 passed reais** — invariante permanente. Overrides:
  104→101 (settings) e 104→97 (base); unit declarado 7→28.

## Verificação

Ofensores medidos por execução do próprio teste (setUpClass +
`_offenders` por alvo); xfail lido no arquivo (:290-309); gerador
confirmado sem remoção (`emit_jq_fragment` só merge). Pós-cura:
`test_veto_skill_map` 21/21 sem xfail na sombra; frozen-subset 7/7;
cadeias byte-idênticas verificadas em pre-flight.
