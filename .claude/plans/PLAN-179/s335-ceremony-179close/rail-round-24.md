# wave-179close — rail codex rodada 24 (sombra pós-curas r23, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (1 P2 — verificado REAL; curado ANTES da r25)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r24.txt` (14.763
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.
**Primeira rodada com UM único achado** — nenhuma família anterior
voltou; refutações e resíduos declarados respeitados.

## O achado (verificação + cura)

1. **[P2] Falha de enumeração engolida como completa** — VERIFICADO:
   `.claude/plans` pesquisável mas NÃO-listável (0111/ACL/erro de I/O)
   faz `glob.iglob` render zero matches SEM levantar — `complete=True`
   vazio, e o path plan_dir direto elegeria SEM a perna AC (pointer
   errado, a classe r15 por outra porta). CURA: sonda explícita de
   listabilidade (`os.scandir` + `next`) antes do glob; OSError ⇒
   `(index, False)` ⇒ recusa. Controle:
   `test_unlistable_plans_dir_refuses_election` (chmod 0111 no dir de
   planos + commit misto: pré-cura elegia PLAN-042, pós-cura `{}`;
   chmod restaurado em `finally` para o cleanup do tempdir).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **350/0** (7.47s) —
`EXPECTED_UNIT_PYTEST_PASSED` 349→350 (+1 controle). Cura confinada a
2 paths do EXPECTED. Refinalize + r25 na sequência.
