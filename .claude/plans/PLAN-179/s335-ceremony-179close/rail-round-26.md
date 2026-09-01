# wave-179close — rail codex rodada 26 (sombra pós-curas r25, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (1 P1 — verificado REAL; curado ANTES da r27)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r26.txt` (8.913
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico. A
instrução dura sobre o FOLLOWUP foi respeitada (não voltou); "the
changed-test battery otherwise passed" no próprio veredito.

## O achado (verificação + cura)

1. **[P1] `-m` unia os diffs de TODOS os parents** — VERIFICADO: num
   merge, `git log -1 -m` devolve o diff contra CADA parent — mudanças
   que já estavam na MAINLINE (PLAN-010) entravam no tie-break e venciam
   por menor id o PLAN-042 que o merge de fato INTRODUZIU ⇒ PostCompact
   reinjetaria o ledger errado. CURA: `--first-parent` (o delta vs
   primeiro parent É o que o merge trouxe à mainline); o teste r9 do
   merge simples segue verde. Controle:
   `test_merge_union_does_not_leak_mainline_plan` (mainline avança
   PLAN-010, side introduz PLAN-042, merge: pré-cura elegia PLAN-010,
   pós-cura PLAN-042).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **351/0** (7.57s) —
`EXPECTED_UNIT_PYTEST_PASSED` 350→351 (+1 controle). Cura confinada a
2 paths do EXPECTED. Refinalize + r27 na sequência.
