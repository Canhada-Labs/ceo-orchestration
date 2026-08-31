# wave-adrgate — rail de MATERIAIS rodada 3 (verificação das curas r2, S334)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 3 P2 de borda — curados nesta rodada)

Saída bruta: `<scratchpad S334>/adrgate-materials-r3.txt`.

## Cure-trace do revisor (verbatim, resumido)

| Cura r2 | Veredito r3 |
|---|---|
| 1. Par de override VÁLIDO | **PASS** — `_override_granted()` vivo devolveu `True` |
| 2. Refuse-if-armed | **PASS** — recusa executa antes de qualquer unset |
| 3. Disarm pós-commit | **PASS** — unset antes do push |
| 4. `--no-commit` `_fin_ok` | **PASS** |
| 5. Init `_fin_ok=0` | **PASS** |
| 6. Transação 4-materiais | INCOMPLETE — P2-i/P2-j abaixo |
| 7. Reset sentinel/.asc | WIRED mas não-preservante — P2-k abaixo |
| 8. `_land_rc=$?` primeiro | **PASS** — logs de abort veem o status original |

## Os 3 P2 de borda, e as curas

- **P2-i — ausência não preservada:** material que NÃO existia antes do
  gerador ficava órfão na árvore num abort. Cura: `.absent-before` no
  backup; o rollback REMOVE o parcial criado.
- **P2-j — "byte-idênticos, nada a fazer" tratado como abort:** o EXIT
  imprimia RESTAURADOS depois do PRONTO. Cura: `_fin_ok=1` também nesse
  caminho de sucesso.
- **P2-k — reset incondicional de sentinel/.asc no `_restore`:** um
  dry-run que nunca chegou ao passo S destruiria staged pré-existente que
  o G0 tolera. Cura: flag `STAGED_BY_LAND` setada no passo S; o
  des-stage do `_restore` é condicional a ela.

Nota de método: 3ª rodada com achado na família transacional — as três
são BORDAS da mesma arquitetura (ausência / caminho-feliz-alternativo /
condicionalidade), não a arquitetura furando. Critério declarado: se a
r4 achar NESSA família de novo, a cura é redesenhada, não remendada.

Harness pós-cura: `PASS=21 FAIL=0 SKIP=0`.
