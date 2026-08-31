# wave-adrgate — rail de MATERIAIS rodada 2 (pós-curas r1, S334)

Rail-Verdict: CHANGES-REQUESTED (4 P1 + 4 P2 — TODOS reais; curados nesta
rodada, com 2 controles novos no harness)

Saída bruta: `<scratchpad S334>/adrgate-materials-r2.txt`. A rodada provou
a doutrina de novo: **três dos oito achados foram INTRODUZIDOS pela minha
cura r1** (a classe "cura que gera o achado seguinte").

## Os oito, e as curas

1. **P1 — override INVÁLIDO pelo contrato do hook.** O revisor AVALIOU
   `_override_granted()` real: reason com espaços + ACK=1 = False
   (concessão negada em silêncio). Cura: slug
   `PLAN-169-wave-adrgate-validate-yml-wire.sentinel-wave-adrgate-approved`
   + ACK literal `I-ACCEPT` (contrato `check_arbitration_kernel.py:390-396`).
   O harness T20e agora avalia o par exportado CONTRA o hook, vivo.
2. **P1 — refuse-if-armed MORTO.** O meu "disarm pós-commit" da r1 caiu
   no INIT do script (ancoragem por primeira-ocorrência — erro meu) e
   unsetava as vars ANTES do teste de recusa. Cura: unset do init
   removido; o refuse volta a morder (e ele deve ABORTAR — limpar o filho
   não limpa o shell do Owner).
3. **P1 — disarm pós-commit ausente de verdade.** Mesma causa do #2.
   Cura: unset imediatamente após `RESTORE_ON_EXIT=0` do pós-commit — o
   push já roda sem a chave no ambiente.
4. **P1 — `--no-commit` virava no-op DESTRUTIVO.** `_fin_ok` só era
   setado no ramo commit; o EXIT de um `--no-commit` bem-sucedido
   RESTAURAVA os materiais que acabara de gerar. Cura: `_fin_ok=1` no
   ramo no-commit (o produto do modo É a mutação). Harness T20a.
5. **P2 — `_fin_ok` herdável do ambiente.** Init `_fin_ok=0`. T20b.
6. **P2 — transação sem o BASE-SHA.txt + index misto no commit-fail.**
   Os QUATRO materiais entram no backup/restore, e o restore também
   des-stageia (reset scoped) — commit-fail não deixa index misto.
7. **P2 — reset scoped não cobria sentinel+.asc do passo S.** Incluídos.
8. **P2 — `_land_rc=$?` capturado após um unset ⇒ sempre 0 ⇒ logs de
   abort NUNCA preservados** (a lição S329-manhã regredida pela cura r1).
   Cura: captura na PRIMEIRA linha do `_restore`. Harness T21 prova com
   abort REAL: `land-adrgate-*.log` aparece no ceremony dir do clone.

## Harness

19 → **21 casos** (T20 contrato-executável das 5 curas com a perna viva
do override; T21 log preservado em abort real). `PASS=21 FAIL=0 SKIP=0`.
