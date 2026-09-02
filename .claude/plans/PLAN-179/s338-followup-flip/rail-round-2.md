# wave 179-followup-flip — rail codex rodada 2 (sombra RE-DERIVADA, base f0e98de, 2026-09-02 S338)

Rail-Verdict: CHANGES-REQUESTED (1 P1 de PROCESSO — respondido, sem cura no patch; o P1 FUNCIONAL da r1 NAO foi reaberto)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretorio da sombra `shadow-179fu`
re-derivada do zero com o script FINAL (5 paths: SessionStart.py,
UserPromptSubmit.py, Stop.py, SessionEnd.py, test_session_end_memory_delta.py;
HEAD movera de dc72bf1 para f0e98de durante a construcao — os 5 paths sao
byte-identicos entre os dois), stdin `</dev/null`. Saida bruta: `codex-r2.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-followup-flip/`]
(7.992 linhas; rc 0). Snapshot sha256 de `git diff` antes/depois:
`ba5efe981865076e132f688b6b52741f8eb55ede877601cf6bb8ddc212dc021b` nos dois
lados ⇒ **TREE-INTACT**.

## O que a r2 NAO reabriu (a cura da r1 ficou de pe)

O rail nao voltou a «Flip every lifecycle producer atomically»: com os 4
produtores no patch, a fragmentacao do ciclo de vida sob divergencia deixou de
ser achado. O proprio texto do veredito abre com «The functional tests pass».

## O achado

1. **[P1, PROCESSO] «Add sentinel coverage for all four hook edits»**
   (`Stop.py:197-200` na sombra). Claim: nenhum dos 4 hooks tem, no checkout
   revisado, um sentinel Owner-signed com escopo que conceda a edicao; o gate
   canonico rejeitaria o land; `AGENTS.md:84-91`/`:103` exigem evidencia de
   sentinel para `.claude/hooks/`, e o proprio FOLLOWUP (`:139-145`) exige GPG
   do Owner.

   **Verificacao:** VERDADEIRO para a SOMBRA, por desenho — e identico ao
   achado #2 das rodadas r1/r2 da wave-fable51 (`PLAN-169/s338-ceremony-fable51/
   rail-round-{1,2}.md`). O sentinel (`wave-179fu-flip-approved.md`, nome a
   fixar pelo orquestrador) e o `.asc` sao materiais do OWNER, criados no SIGN
   na arvore VIVA e commitados ANTES do LAND; o finalize RECUSA sombra com path
   fora do EXPECTED, entao eles nunca estarao na sombra que o rail revisa. A
   autorizacao de cada path canonico e provada pelo gate do LAND
   (`_sentinel_grants_path` vivo contra o `.asc`), nao pelo texto do patch. Este
   pack, por brief, entrega script + design + evidencia + rail e NAO escreve
   SIGN/LAND. **Sem cura no patch.** O que o achado ACRESCENTA, e vale
   registrar para quem escrever o SIGN: o escopo do sentinel tem de listar os
   QUATRO hooks (nao so os dois do AC original) + o teste — e os 4 sao KERNEL
   (`_KERNEL_PATHS:218-221`), logo o LAND arma `CEO_KERNEL_OVERRIDE`/`_ACK` no
   menor escopo.

## Por que nao ha r3

Nenhuma edicao de patch saiu da r2; re-rodar o rail sobre a MESMA sombra so
reproduziria o achado de processo (o rail nao enxerga o sentinel por
construcao). A ultima rodada REGISTRADA e esta: CHANGES-REQUESTED por
processo, com o entregavel funcional limpo nas duas rodadas que o revisaram
apos a cura da r1. Reportado assim, sem maquiagem, no retorno estruturado.

## Verificacao das claims

`AGENTS.md:84-91` e `:103` (contrato do revisor — evidencia de sentinel para
hooks) e `PLAN-179-FOLLOWUP-sessionstart-anchor-id.md:139-145` (restricoes:
hook canonico exige sentinel + GPG do Owner) lidos; o molde do achado
conferido em `PLAN-169/s338-ceremony-fable51/rail-round-1.md` §2 e
`rail-round-2.md` §1. Bateria FINAL na sombra re-derivada (DEPOIS da ultima
edicao): 551 passed / 2 xfailed nos 21 arquivos declarados; gates todos rc 0
— `EVIDENCE.md` §3.
