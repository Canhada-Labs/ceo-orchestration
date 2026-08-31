# wave-179close — rail codex rodada 3 (sombra base cfab980 + curas r1+r2, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2 — TODOS verificados REAIS; curados ANTES da r4)

Comando: idêntico às r1/r2. Primeira tentativa (r3) foi MORTA externamente a
~10k linhas SEM veredito (TREE-INTACT verificado; sem órfãos; o hit de
«Full review comments» no parcial era a CITAÇÃO da regra dentro da linha de
memória do CLAUDE.md ecoada no stream — falso positivo de grep). Re-despachada
como r3b: `<scratchpad S335>/179close-r3b.txt` (9.342 linhas), TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1] Controle negativo do anchor quebrava o CI Ubuntu** — o teste da
   ordem (r1) esperava `state_file` incondicionalmente; no Linux não há
   `st_birthtime` e o fallback é INUTILIZÁVEL por desenho (r1 P1-2) ⇒
   vermelho no job que coleta todos os hook tests. CURA: expectativa por
   PLATAFORMA (com birthtime ⇒ `state_file`; sem ⇒ `none`); a metade
   pós-delete (⇒ `none`) vale nas duas.
2. **[P2] `main()` preferia `CLAUDE_SESSION_ID` (spoofable) ao payload** —
   contra o consensus M2 do próprio repo e contra o SPEC row novo
   («threaded from the harness event»); env divergente ancoraria o scan na
   sessão ERRADA. CURA: PAYLOAD-first, env só como fallback de harness sem
   id — comentário nomeia a doutrina.
3. **[P2] Segundo truncado do `ts`** — o wire serializa em segundos
   INTEIROS; um arquivo da sessão ANTERIOR escrito no mesmo segundo do
   start satisfaria `>= start_ts` (falso `written`). CURA: quando a âncora
   vem do CHAIN, a janela exclui o segundo não-resolvido (`start_ts + 1`);
   undercount de borda documentado — o desenho já prefere perder a
   inventar. birthtime carrega subsegundo e não precisa do ajuste.

## Verificação das claims

`os.stat_result` sem `st_birthtime` no Linux (docs + o guard do teste
irmão); `main()` lido em SessionEnd.py:839-842 pré-cura; truncamento do ts
confirmado no serializer (`audit_emit`, whole-seconds). Suites pós-cura:
**72 passed** nas 3 tocadas; declarado 9-suítes segue **304/0** (nenhum
teste adicionado — só guard de plataforma e 2 curas de produção).
