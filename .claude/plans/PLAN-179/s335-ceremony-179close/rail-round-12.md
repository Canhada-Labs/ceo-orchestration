# wave-179close — rail codex rodada 12 (sombra pós-curas r11, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (3 P2 — TODOS verificados REAIS; curados ANTES da r13)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r12.txt` (11.210
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico. Os
refutados anteriores NÃO voltaram (a instrução de nomear atacante no
threat model foi respeitada pela 3ª rodada seguida).

## Os achados (verificação + cura)

1. **[P2] Janela invertida fabricava `absent`** — VERIFICADO: rollback de
   relógio / VM restore DEPOIS do `session_start` põe o start acima do
   teto da r11; todo mtime falha o range e um dir gravável caía em
   `absent` (claim falso de omissão). CURA: `start_ts > scan_upper` ⇒
   janela é "não sei" (`start_unknown`/`none`), consistente com o
   contrato terminal-unknown. Controle:
   `test_inverted_window_is_start_unknown`.
2. **[P2] O ciclo de vida legado tinha mudado de precedência de id** —
   VERIFICADO REAL e é correção DE CURA ANTERIOR (r3): payload-first no
   `main` fazia `session_end`/closeouts/cleanup descorrelacionarem do
   `session_start` env-first quando os ids divergem — contradizendo a
   declaração v2.60 de que NENHUMA action existente muda. CURA: o legado
   volta a env-first (espelho literal do `SessionStart.py:559-561`); a
   doutrina payload-only da r3/r4 fica INTEIRA no rail novo
   (`payload_sid` sem fallback, trava de consumo já testada). Controle:
   `test_lifecycle_id_mirrors_sessionstart_env_first` (source-level
   DECLARADO — `main()` é dirigido pelo adapter de stdin e não é
   construível honestamente; a metade do delta é comportamental nos
   testes existentes).
3. **[P2] Slug vazio virava `dir_missing`** — VERIFICADO: falha de INFRA
   (runtime_paths ausente/raise em upgrade parcial) era emitida como
   claim de diretório ausente, escondendo a falha real. CURA: slug vazio
   ⇒ `error` (default) + breadcrumb nomeando a causa (regra fail-open de
   infra). Controle: `test_unresolved_slug_is_error_not_dir_missing`.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **330/0** (7.49s) —
`EXPECTED_UNIT_PYTEST_PASSED` 327→330 (+3 controles, nada removido).
Curas confinadas a 2 paths do EXPECTED (SessionEnd + a suíte do delta).
Refinalize + r13 na sequência.
