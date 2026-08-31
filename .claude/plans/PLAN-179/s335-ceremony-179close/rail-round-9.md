# wave-179close — rail codex rodada 9 (sombra pós-curas r8, S336 2026-08-31)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — ambos verificados REAIS na perna plan_ac adicionada pela r6; curados ANTES da r10)

Forma prompt-only (resumo r8 no prompt; a instrução de não re-levantar os
refutados seguiu respeitada — nenhum voltou). Saída:
`<scratchpad S336>/179close-r9.txt` (9.210 linhas), exit 0. TREE-INTACT:
manifest sha256 pré/pós byte-idêntico. O próprio veredito registra: "The
remaining reviewed changes and targeted tests were otherwise consistent"
— a superfície residual é só o índice do ledger.

## Os achados (verificação + cura)

1. **[P2] Merge e paths quotados no git do índice** — VERIFICADO: commit
   de MERGE sob combined-diff (`git log -1 --name-only`) devolve lista
   VAZIA, e nome não-ASCII vem C-quotado (`"src/\303\251.py"` nunca casa
   shape nem AC) ⇒ pointer omitido em commit plan-scoped válido. CURA:
   `-m` (per-parent) + `-z` (raw, NUL-delimited) + dedupe preservando
   ordem. Controle: `test_merge_commit_still_derives_plan` (merge
   `--no-ff` real no harness do teste).
2. **[P2] Matching plan_ac sem cap nem deadline** — VERIFICADO: o loop é
   O(paths × ACs), o mirror pode retornar JÁ no deadline, e o
   `_ledger_index` roda ANTES do `_write_snapshot` — estourar o budget
   trocaria o snapshot por um pointer (inversão de prioridade do hook).
   CURA: cap `_LEDGER_AC_MATCH_MAX_PATHS=500` + re-check de deadline por
   path com break (degradação honesta: segue com o que já contou).
   Controle: `test_ac_matching_stops_at_the_deadline` (clock sequenciado;
   vermelho pré-cura — sem o check por path a 5ª leitura nunca ocorre e o
   matching completa).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **323/0** (8.29s) —
`EXPECTED_UNIT_PYTEST_PASSED` 321→323 (+2 controles, nada removido).
Curas confinadas a 2 paths do EXPECTED (check_precompact + a suíte de
continuidade). Refinalize + r10 na sequência.
