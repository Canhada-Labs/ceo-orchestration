# wave-adrgate — rail de MATERIAIS rodada 6 (S334)

Rail-Verdict: CHANGES-REQUESTED (1 achado micro — curado)

As 3 curas da r5 confirmadas presentes (T22 real com anti-vácuo; stderr
do restore visível; captura fail-CLOSED). Achado único: no caminho de
FALHA-DA-CAPTURA, `_fin_bak` já existia mas `_fin_restore` ainda não
tinha sido definida — o trap emitiria `command not found`. Cura: gate do
trap trocado para a flag `_fin_captured`, ligada só APÓS captura+função.
Saída bruta: `<scratchpad S334>/adrgate-materials-r6.txt`.
