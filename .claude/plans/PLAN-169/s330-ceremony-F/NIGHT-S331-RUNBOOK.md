# NIGHT-S331 — runbook da sessão autônoma de 2026-08-30

> Sessão iniciada 09:48 -03, Owner fora até ~19:48. Escopo ratificado ANTES da
> saída: **só a wave-s330-F, até o ponto de assinatura**. Nenhum segundo pacote.

## As quatro decisões do Owner (AskUserQuestion, 09:5x)

1. **Escopo** — «Só a wave F, até a assinatura».
2. **FU-F-ACCEL** — «Reconciliar no MESMO patch».
3. **OQ-F1 / OQ-F3** — «Congelar F1 + incluir o step F3».
4. **ADR** — «Decida pela §6 do DESIGN-F» ⇒ a §6 da *classificação* recomenda
   **ADR NOVO, não AMEND**, com argumento medido (nenhum ADR-pai decide o
   roster). Executado: **ADR-197**.

Depois, por chat: «se precisar assinar algo prepara pra quando eu voltar, tenta
codar o maximo pra adiantar os planos pendentes» e «se bater na quota de 5
horas aguarde e continue assim que ela resetar».

## Continuidade de quota

`CronCreate` recorrente `13 * * * *` (job `59aa9a24`), session-only. Dispara
quando o REPL está ocioso — se a sessão parar por corte de quota, o job a
retoma na hora seguinte. O prompt do job carrega as quatro decisões acima e o
ponteiro para este runbook, para que a retomada não re-pergunte nada.

**Limite declarado:** isso cobre o corte de SESSÃO (5 h). Não cobre o corte de
*org monthly spend*, que na S330 exigiu `/login` em conta alternativa —
presencial. Se bater esse, a noite para onde estiver, com o estado commitado.

## O que foi feito, em ordem

1. **Sombra recuperada** do snapshot commitado (`F-wip.patch` sobre `1c34eb5`),
   verificada pelo ARTEFATO (`gen --check` rc 0; 164 passed / 2 skipped), e
   **rebaseada para o HEAD vivo** (`7ffcdeb` — medido: nenhum dos 6 paths
   derivou entre as duas bases).
2. **FU-F-ACCEL curado.** Medição que resolveu a ambiguidade dos timeouts: o
   `.claude/settings.json` VIVO deste repositório roda `review_loop.py` em 15 s
   e `turbo_sessionstart.py` em 5 s — iguais à base, diferentes dos 60/10 da
   tabela `ACCEL`. Duas fontes contra uma ⇒ o ACCEL era cópia defasada, não
   escolha. A tabela some, a composição vira função pura, e o marcador de
   dívida é **INVERTIDO** em guard permanente.
3. **OQ-F3**: step no `validate.yml`, verificado nos dois sentidos.
4. **ADR-197** escrito; índice de ADRs regenerado; 15 sítios de contagem
   atualizados em 9 arquivos + o numeral do `CLAUDE.md`.
5. **Pair-rail rodada 1** — 2 P2 reais, ambos curados com controle vermelho
   (ver `rail-round-1.md` e DESIGN-F §7.6).
6. **Pacote montado**: `finalize-F.sh`, `EXPECTED-BASELINE.txt`,
   `COMMIT-MSG-F.txt`, `README-F.md`, `PROPOSED-PATCH.md`, sentinel-draft,
   `OWNER-S331-F-SIGN.sh`, `OWNER-S331-F-LAND.sh`, `test-ceremony-scripts-F.sh`.

## Achados de substrato desta noite (para a próxima)

* **`codex exec review --uncommitted` não aceita PROMPT.** A forma com
  instruções sai `error: the argument '--uncommitted' cannot be used with
  '[PROMPT]'`. A revisão é do diff, sem direcionamento.
* **Sob `sandbox_mode="read-only"` a rodada MORRE** quando o revisor tenta
  rodar a suíte: `FileNotFoundError: No usable temporary directory found`. A
  forma que funciona é `-c sandbox_mode="workspace-write"` — o que dá ao
  revisor escrita na árvore que ele revisa. Por isso as rodadas rodam sob
  `rail_round.sh`, que hasheia cada path staged antes e depois e RECUSA
  reportar uma rodada cuja árvore mudou.
* **Dois jobs escrevendo no mesmo arquivo de saída produzem um transcript
  misto** que parece um veredito e não é. Um arquivo por rodada.
* **Detector de "rodada limpa" por `grep 'Full review comments'` dá
  falso-positivo**: o `CLAUDE.md` deste repositório cita essa string ao
  explicar a regra, e o codex ecoa o `CLAUDE.md` no contexto. Leia o FIM da
  saída, não um grep global.
* **`shellcheck` sobre um script DERIVADO de outro pega o que o grep não pega.**
  A derivação do LAND deixou `$UPGRADE_FN`, `$E2E_TEST` e `$_obs_passed`
  referenciados sem constante — os três falhariam sob `set -u` no terminal do
  Owner, não aqui. E o sinal `SC2034 DRY_RUN appears unused` era o rastro de um
  defeito maior: o bloco que **interrompe** o `--dry-run` tinha sido removido
  junto com o V-block antigo, então um `--dry-run` teria seguido até o commit.

## Estado ao fim

Ver `README-F.md` (o guia de três comandos para o Owner) e o resumo da sessão.
Nada foi assinado — a assinatura GPG é do Owner, por desenho.
