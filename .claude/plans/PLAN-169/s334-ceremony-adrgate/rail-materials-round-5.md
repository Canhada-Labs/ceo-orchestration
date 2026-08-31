# wave-adrgate — rail de MATERIAIS rodada 5 (verificação do redesenho r4)

Rail-Verdict: CHANGES-REQUESTED (3 achados sobre o T22 e bordas fail-open
do redesenho — curados; verificação final na r6)

Saída bruta: `<scratchpad S334>/adrgate-materials-r5.txt`. A r5 confirmou
o wiring do LAND (init + pre-loop) e pegou três coisas que importavam:

1. **T22 era FALSO-VERDE por vácuo duplo.** O `$SRC` do harness é um
   clone de HEAD — os materiais uncommitted nem existiam no clone, o
   finalize abortava no passo 0 (pré-gerador) e o marcador "sobrevivia"
   por nunca ter sido ameaçado; e `--no-commit` nem passa pelo guard
   pre-add. É a lição do PRÓPRIO gate T-S329-2 do harness, cobrada de
   quem o contornou com o escape. Cura: T22 refeito — roda o finalize
   REAL sem `--no-commit`, com asserções ANTI-VÁCUO (o banner do gerador
   TEM de estar no log; o abort TEM de ser o guard pre-add), e o harness
   oficial roda SEM escape sobre a árvore commitada.
2. **O aviso de recovery era engolido** (`_fin_restore 2>/dev/null` no
   trap). Cura: stderr do restore chega ao operador.
3. **A captura do index era fail-open** (falha ⇒ patch vazio silencioso
   ⇒ rollback destruiria staging pré-existente). Cura fail-CLOSED: sem
   pré-estado capturado, o finalize RECUSA mutar os materiais, com o
   stderr da captura no abort.

Harness pós-cura, SEM escape, na árvore commitada (`ceee17d`):
`PASS=22 FAIL=0 SKIP=0` — T22 com abort real pós-gerador preservando
index-only content + worktree byte a byte.
