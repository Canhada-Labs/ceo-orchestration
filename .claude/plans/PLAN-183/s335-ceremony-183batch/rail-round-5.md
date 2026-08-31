# wave-183batch — rail codex rodada 5 (sombra A4-completa, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P1 — verificado REAL; curado ANTES da r6)

Forma prompt-only. Saída: `<scratchpad S335>/183batch-r5.txt` (2.830
linhas), TREE-INTACT.

## O achado (e a cura)

**[P1] O invariante promovido era falso-verde para grafias loaded-name** —
o gerador grava overrides TAMBÉM na grafia do frontmatter `name` quando
difere do slug; «Kill Switches» e «Latency Budgets» seguiam name-only nos
DOIS alvos e `_offenders()` comparava a chave CRUA contra `bound`
(slugs) — cego. CURA em duas pernas, com controle red→green: (1) o teste
normaliza a chave via o INVENTÁRIO (name→dir_name; nunca transformação
textual) — rodado ANTES do undemote ele ACUSOU as 2 (vermelho legítimo);
(2) o `veto-undemote-s335.jq` ganhou as 2 grafias (9 del no total) e os
alvos re-derivados: settings 101→99, base 97→95; pós-cura 28/28 verdes.
Medição prévia: só essas 2 das 7 têm `name` ≠ slug.

## Verificação

Grafias órfãs enumeradas por normalização contra o conjunto dos 7 nos
dois alvos (2 hits idênticos); `bind_to_inventory` lido (:215-233 —
`keys` tem name+dir, `bound` é slug-only); red→green registrado acima.
