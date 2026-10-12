---
id: PLAN-171-FOLLOWUP-lote2-generated-figures
parent: PLAN-171
title: Resíduos do instrumento do censo W0 — figuras literais do lote 2 e censo W0-delta do check_workflow_launch
status: done
created: 2026-10-10
executing_at: 2026-10-12
completed_at: 2026-10-12
related_commits: [572d3fbd9844, 54717eac021d]   # 572d3fbd9844 W1 (marcas no lote 2); 54717eac021d W2 (relatório W0-delta)
reviewed_at: 2026-10-12
reviewed_by: "Owner (S363, AskUserQuestion de 2026-10-12 ~12:50Z — resposta «Sim, fechar hoje (Recommended)» à pergunta «Posso marcar o plano das figuras do lote 2 (PLAN-171-FOLLOWUP-lote2) como revisado e fechá-lo hoje? As figuras cujo gerador se perdeu ficariam anotadas como “números copiados de 07/09, sem script para refazer”, e eu rodaria hoje a medição do guarda de retomada de Workflow num clone descartável.»; texto transcrito pelo CEO no despacho do builder)"
owner: CEO
depends_on: [PLAN-171]
tags: [audit, census, instrument, followup]
---

## Context

O PLAN-171 fechou na W0 em 2026-10-10, com 52 de 52 linhas de gate providas
de controle positivo (adendo no §6 de `PLAN-171/w0/W0-consolidated-verdict-S348.md`).
Ficaram dois resíduos do instrumento do censo, nenhum deles critério da W0.

1. **Figuras literais do lote 2.** A cura pós-land do lote 2 converteu para
   geração por instrumento só a contagem do §2 e o Apêndice C. As figuras de
   §1, §4, §5 e dos Apêndices A, B e D de `PLAN-171/w0/lote-2-S347.md`
   continuam vindo do `gen-report.py` do pack do lote 2, como literais
   (`PLAN-171/w0/s345-p171-w0-lote2-fix/rail-land-round-1.md:54-57`).
   **Achado do fechamento:** nenhum gerador do pack está no repositório. Em
   2026-10-10, `git ls-files` não lista `gen-report.py`, `gen-count.py`,
   `measure-optin.py` nem `partition.py`. Re-derivar exige reconstruir o
   instrumento, ou declarar as figuras como literais datadas.
2. **Censo W0-delta do `check_workflow_launch.py` (opcional).** O hook entrou
   no `.claude/settings.json` em 2026-09-17 (`075beed9`), depois do censo. Tem
   suíte própria, mas não foi medido pelo método das três metades: verde como
   está, vermelho com o enforcement removido numa worktree descartável, verde
   de novo depois do `git restore`.

## Goal

Toda figura dos relatórios da W0 tem fonte reproduzível ou é declarada literal
com data, e o roster vivo de hooks tem censo completo.

## Items

### W1 — figuras do lote 2  [P3]  (livre: relatórios de plano)
- Reconstruir o gerador e commitá-lo junto do relatório, OU anotar cada figura
  como literal datada, com a fonte.

### W2 — censo W0-delta  [P3, opcional]  (livre: relatório novo em `PLAN-171/w0/`)
- Três metades sobre o `check_workflow_launch.py`, em worktree descartável
  com limpeza confinada.
- A síntese de fechamento da S363 estima 60–120k tokens, 1 sessão.

## Execução (S363, 2026-10-12)

- **W1 — rota escolhida: anotar, não reconstruir** (decisão do Owner no
  `reviewed_by`). Commit `572d3fbd9844`, só acréscimos em
  `PLAN-171/w0/lote-2-S347.md`. Em 2026-10-12, `git ls-files` não lista
  nenhum dos cinco instrumentos do pack (`gen-report.py`, `gen-count.py`,
  `partition.py`, `remainder.py`, `measure-optin.py`); o `remainder.py`,
  citado no §5 do relatório, não estava na lista do Context.
- **Data das figuras.** A pergunta ao Owner falava em «números copiados de
  07/09». O disco data a medição de 2026-09-06: é a data do cabeçalho do
  relatório, e os dois commits que o escreveram (`184a1a2fe60f` e
  `14892ab04be3`) são de 2026-09-06 (-0300). As marcas usam 2026-09-06.
- **Além das seções listadas no Context.** Para o critério valer para TODA
  figura do arquivo, também ganharam marca as células da tabela do §2, o
  cabeçalho e os Apêndices E e F (F é saída do `measure-optin.py`,
  acrescentado pela cura `14892ab04be3`).
- **W2 — feita.** Commit `54717eac021d`: relatório novo
  `PLAN-171/w0/W0-delta-check_workflow_launch-S363.md`, com o driver
  embutido byte a byte, e a «dívida nomeada» do §6 de
  `W0-consolidated-verdict-S348.md` apontando para ele.

## Success criteria

- [x] Nenhuma figura de `lote-2-S347.md` sem fonte reproduzível ou sem a marca de literal datado.
  Check: none (doc-only)
  Evidência (2026-10-12, `572d3fbd9844`): a frase «literal datado: saída do
  gen-report.py do pack S347; gerador não preservado» abre o §1, o §4, o §5
  e os Apêndices A, B e D (`grep -c` da frase = 6); o §2, os Apêndices E e F
  e o cabeçalho têm marca própria. O Apêndice C está marcado como
  reproduzível: os cinco greps dele devolvem 10, 10, 0, 0 e 10 depois da
  anotação, iguais aos `# N`; o grep análogo de `sem-controle-por-design`
  devolve 0.
- [x] (opcional) Relatório W0-delta com as três metades do `check_workflow_launch.py`.
  Check: `ls .claude/plans/PLAN-171/w0/` mostra o relatório novo
  Evidência (2026-10-12, `54717eac021d`): `ls` mostra
  `W0-delta-check_workflow_launch-S363.md`. Verde nas três metades, um
  processo pytest por arquivo: como está, 107 + 29 passam (rc 0); com o
  mutante em `decide_pre` (`_lib/launch_ledger.py:968`), 25 de 107 e 3 de 29
  falham (rc 1); depois do `git restore`, 107 + 29 passam (rc 0).
