# wave-adrgate — rail de MATERIAIS rodada 7 (S334)

Rail-Verdict: CHANGES-REQUESTED (1 achado micro — curado)

`_fin_captured` não era inicializada — um `export _fin_captured=1` do
ambiente re-abriria o exato caminho que a r6 fechou (a MESMA classe do
`_fin_ok` da r4, que eu deveria ter espelhado por simetria na hora).
Cura: `_fin_captured=0` no init, ao lado do `_fin_ok=0`. Nenhum outro
achado em LAND, harness ou SIGN.
Saída bruta: `<scratchpad S334>/adrgate-materials-r7.txt`.
