# wave-s343-w4a — rail codex rodada 5 (texto das curas da r4, S343 2026-09-04)

Rail-Verdict: CHANGES-REQUESTED (2 P3 REAIS, os dois DENTRO das curas da r4)

Comando: `codex exec review` em modo PROMPT, com os cinco fatos já
estabelecidos dados como GIVEN e pedindo especificamente a revisão do TEXTO
das duas curas da r4. Saída bruta: `evidence/rail-r5-raw.txt`.

## O que o codex disse

«Both cure comments retain factual inconsistencies: one still attributes
runtime variation to the runner, and the other incorrectly identifies the npm
packlist gate as a pytest consumer. The workflow syntax and stated coverage
changes otherwise appear sound.»

## [P3] Remove the remaining runner attribution — REAL, e é auto-contradição

A r4 corrigiu o PARÁGRAFO da tabela, e eu deixei o **lede** do mesmo bloco
dizendo «the samples below say the RUNNER, not the step list, is what moves
this job» (`smoke-install.yml:299`, verificado por `grep`). O bloco passava a
se contradizer: a abertura atribuía causa, o corpo dizia que atribuição
exigiria runs repetidos no mesmo sha.

**É literalmente a classe que esta wave existe para curar, cometida DENTRO da
cura anterior.** O lede agora diz o que as amostras dão — uma FAIXA observada
que a aritmética não tinha — e remete à nota sob a tabela para a questão de
causa.

## [P3] Distinguish Python use from pytest use — REAL, verificado por medição

Eu escrevi que TRÊS steps posteriores rodam pytest. Medição própria antes de
aceitar (o instrumento também é revisado): dos 3 steps posteriores cujo `run`
contém a palavra `pytest`, só **DOIS** o INVOCAM —

| step posterior | contém a palavra | invoca `python3 -m pytest` |
|---|---|---|
| PLAN-155 Wave 6 pair-rail + advisory teeth | sim | **sim** |
| Run v1.0.1 test roots (PLAN-152 tests-01) | sim | **sim** |
| npm packlist gate | sim | **não** — usa o interpretador `python3`, não o pytest |

O comentário passa a dizer DOIS, e a nomear a distinção entre «usa o
interpretador selecionado» e «consome o pacote pytest instalado».

## Estado

Patch re-derivado: `35e26cdc47e606d1…` (11 edições; 10 hunks no patch, 11 sob
`-U0`; `83 insertions(+), 40 deletions(-)`). `actionlint` rc=0; 7 jobs;
`validate` 48 steps; `smoke` timeout 150; menções à matriz = 8; nenhuma
ocorrência residual de «RUNNER, not the step list» ou «all run pytest».

As duas curas são de UMA frase cada, ambas sobre texto que eu mesmo escrevi, e
ambas verificadas mecanicamente. A **r6** fecha a série.
