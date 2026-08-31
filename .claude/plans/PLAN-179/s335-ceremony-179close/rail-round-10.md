# wave-179close — rail codex rodada 10 (sombra pós-curas r9, S336 2026-08-31)

Rail-Verdict: CHANGES-REQUESTED (4 P2 — TODOS verificados REAIS; curados ANTES da r11)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r10.txt` (9.411
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P2] Decode estrito explode com filename não-UTF-8** — VERIFICADO:
   `-z` emite bytes crus; `text=True` sem policy levanta
   `UnicodeDecodeError` que nenhum except do `_git` pegava — o snapshot
   INTEIRO morria por causa do índice OPCIONAL. CURA: `errors="replace"`
   (path vira U+FFFD, não casa shape nenhum, degradação honesta).
2. **[P2] O índice opcional podia comer o budget do snapshot** —
   VERIFICADO: o `git log` do índice roda ANTES do `_write_snapshot` e
   os passos seguintes do gate têm timeouts fixos próprios. CURA: fatia
   local `_LEDGER_INDEX_MAX_SHARE_S=1.0` clampa o deadline do índice —
   repositório lento degrada o ÍNDICE, nunca o snapshot.
3. **[P2] Materialização sem cap pré-dedupe** — VERIFICADO: split+dedupe
   materializava TODOS os paths (e `-m` repete por parent). CURA: slice
   `_LEDGER_GIT_PATHS_MAX=2000` ANTES do dedupe. Controles de 1 e 3:
   `test_ledger_git_bounded_discipline_source` (source-level DECLARADO:
   filename não-UTF-8 não é construível em APFS/HFS+ e teste de commit
   >2000 paths dependeria da ordem do git — as metades comportamentais
   não são construíveis honestamente; a disciplina de deadline JÁ tem
   controle comportamental na r9).
4. **[P2] `stat()` seguia symlink no scan de memória** — VERIFICADO:
   symlink antigo no dir de memória + alvo EXTERNO editado na sessão ⇒
   falso `written` (a pior classe do contrato). CURA: `lstat` — o link
   não é tópico de memória; `S_ISREG` do modo do LINK é False e a
   entrada é pulada sem contar. Controle:
   `test_symlink_target_edit_is_not_memory_written`; os 3 testes que
   usavam o mecanismo `stat` (slow-final, incomplete-scan ×2) migraram
   para `lstat` — a migração em si provou a cura (o teste de symlink
   quebrado da r7 parou de disparar por raise e foi reescrito com
   lstat-raise explícito).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **325/0** (8.01s) —
`EXPECTED_UNIT_PYTEST_PASSED` 323→325 (+2 controles; 4 testes migrados de
mecanismo, nada removido). Curas confinadas a 4 paths do EXPECTED.
Refinalize + r11 na sequência.
