# Pacote F — rail codex rodada 8 (shadow-F com a decisão do Owner aplicada, 2026-08-30 ~17:00 -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 — de SINCRONIZAÇÃO de materiais, não de
código; a cura é estrutural e precede a rodada 9, ver Disposição)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh` (snapshot sha256 de cada path staged antes/depois).
Substrato: codex-cli 0.147.0. Saída bruta: `<scratchpad 889bc1bd>/r8.txt`.
Wrapper: **TREE INTACT**.

## O que esta rodada revisou

A sombra rebaseada em `9cd29af` com a cura da decisão do Owner (r7 P2-a)
aplicada: exclusão de `check_scratchpad_access.py` como DADO no spec
(`_derivation.exclude_hooks` classe `bloqueia-edicao`, com razão e evidência;
`blocking_inclusions` 5 → 4), template regenerado (roster 30 → **29
registrações / 28 basenames**, 37.819 B), `RULED_IN` 10 → 9 no mesmo patch,
piso do guard anti-vácuo 5 → 4 com a fonte, ADR-197 emendado e DESIGN-F §7.12.
Verificação da sombra no momento da rodada: bateria **267 passed / 2 skipped**;
paridade `--check` rc 0; `verify-counts.sh` rc 0; `check-claude-md-claims.py`
rc 0; índice de ADR rc 0; guard do plugin 7/7; plugin composto 29 registrações
/ 0 duplicatas.

## [P1] «Rebaseline the ceremony after removing the scratchpad hook» — verdadeiro na árvore revisada; a cura é estrutural

O revisor apontou: o `EXPECTED-BASELINE.txt` da árvore revisada ainda esperava
30/29/30 (registrações / basenames / plugin), e sentinel + README ainda
prometiam «30 registrações, 10 hooks novos» — com isso o `finalize-F.sh`
abortaria por desenho e a evidência assinada pelo Owner nasceria imprecisa.

O achado é correto SOBRE A ÁRVORE QUE ELE VIU — e expõe um fato de método: os
materiais de cerimônia (EXPECTED-BASELINE, sentinel, README-F, COMMIT-MSG,
PROPOSED, adendo da classificação, mensagens do LAND) já tinham sido curados
NO CHECKOUT VIVO antes da rodada, mas a sombra é um clone de HEAD (`9cd29af`)
e carrega as versões commitadas — o revisor não enxerga o working tree do
vivo. As rodadas 1–7 nunca tropeçaram nisso porque os materiais ainda não
estavam commitados quando elas rodaram: esta foi a primeira rodada em que a
sombra CONTINHA materiais de cerimônia, e o rail flagrou a inconsistência
interna imediatamente — comportamento correto do gate, não ruído.

**Cura (esta disposição):** os materiais curados são COMMITADOS no vivo e a
sombra é REBASEADA para esse commit; a rodada 9 revisa a árvore CONSISTENTE, e
é ela que precisa sair APPROVE. Nenhuma linha de código do patch mudou por
este achado — o único delta nos 20 paths entre r8 e r9 é o título da §7.12 do
DESIGN-F (ajustado para não prometer rodadas futuras no material que a rodada
seguinte revisa).

## Nota de substrato

O codex 0.147.0 executou a suíte da sombra com `python -m unittest` direto em
um dos passos do transcript (`FAILED (errors=1, skipped=2)` no meio da saída):
runner que este repositório declara não-suportado (conftest pytest-only, por
construção — `CLAUDE.md` e memória de CI). O revisor NÃO transformou isso em
achado; registrado aqui para a próxima noite não confundir transcript com
veredito. O veredito real está no FIM da saída, como sempre.

## Disposição

CHANGES-REQUESTED. A cura é o commit de materiais + rebase que precede a
rodada 9; o `SIGN` continua recusando até existir um registro `APPROVE` como
último — por desenho.
