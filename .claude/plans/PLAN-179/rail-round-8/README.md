# Rail round 8 — 4 achados (1×P1, 3×P2), TODOS curados na S314

Sequência do rail: 9 → 4 → 2 → 3 → 2 → 3 → 4 → **4**. Primeira rodada em
que o GC saiu LIMPO (a cura round-7 — expiração por store sob o lock do
próprio store — segurou, com 8 testes novos em
`test_scratchpad_gc_store_unit.py`). O processo também mudou nesta rodada:
o clone do rail **preserva** `rail-round-*` (cura do achado 4 do round 7 —
fim das referências órfãs no HANDOFF).

## Achados e curas (todas no pack `staged-w01`)

1. **[P1] Redação corrompia o JSON do snapshot.** O kv-pattern do
   `redact_secrets` (JSON-cego) comia a aspa/vírgula de fechamento quando
   um campo terminava em `token=abc` — snapshot ilegível, continuidade
   morta para exatamente os segredos que ela deve sobreviver.
   **Cura:** redação por CAMPO antes da serialização (`max_chars=0`) +
   bytes ao store (rota documentada "caller owns the content"); fallback
   str se o redactor faltar (degrada para a corrupção, nunca para segredo
   em disco). Regressão: `test_assignment_shaped_secret_keeps_snapshot_parseable`
   (exige `json.loads` + marcador).
2. **[P2] Identidade do sidecar: cwd vs project root.** O escritor grava o
   ROOT; cwd de subdiretório era rejeitado e o evento de pressão ficava
   mudo. **Cura:** aceita cwd == root ou DENTRO dele; outro repo segue
   rejeitado. Testes: `test_subdirectory_cwd_matches_project_root`,
   `test_foreign_project_root_is_still_rejected`.
3. **[P2] `constraint_count` reportava o SET com render degradado.**
   **Cura:** o contador reporta o RENDERIZADO — zero a menos que o bloco
   tenha saído. Teste: `test_degraded_constraint_render_reports_zero`.
4. **[P2] CLAUDE.md do pack dizia PLAN-179 `draft`.** Reescrito para a
   verdade pós-land (reviewed; W0/W1/W1-b landados; W2/W4 staged; sonda
   shipada com veredito de canal pendente).

## Verificação

- Dirigidos: 82 passed (compaction-continuity + integração + parity +
  GC + sonda), exit real lido de arquivo.
- Suíte completa em clone com o pack round-8 aplicado + round 9 do rail:
  em execução ao escrever este README; resultado no RETOMAR-AQUI.

## Critério de parada pré-registrado para o round 9

Se o round 9 devolver NOVO achado no guard de pressão (4 rodadas seguidas
renderam um), o guard SAI do pack (redução de escopo, lição S296) — não
haverá round 10 sobre o pack cheio.
