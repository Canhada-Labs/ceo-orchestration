# wave-179close — rail codex rodada 1 (sombra base cfab980, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (2 P1 + 5 P2 — TODOS verificados REAIS; curados ANTES da r2)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
rodado DO diretório da sombra, stdin `</dev/null`. Saída bruta:
`<scratchpad S335>/179close-r1.txt` (10.288 linhas). Snapshot sha256 dos 5
canônicos antes/depois: TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1] NFKC-bypass na sanitização de basename** (`SessionEnd.py`) —
   U+FF40 (fullwidth grave) passa o check cru e o NFKC o converte EM
   backtick depois do gate; U+2028/29 sobrevivem intactos. CURA: o check de
   delimitadores roda sobre o nome NORMALIZADO + gate `isprintable()`;
   a ordem da spec §6 (raw→NFKC) está falsificada e o desvio documentado.
   Controle novo: `test_nfkc_compat_char_dropped_from_render`.
2. **[P1] Âncora fallback não é início de sessão** — o record file do
   tool_lifecycle é REESCRITO a cada Pre/Post (`_save_records`), então
   st_mtime ≈ último tool call ⇒ janela encolhida ⇒ falso `absent`. CURA:
   só `st_birthtime` (imutável; macOS/BSD) serve de âncora; plataforma sem
   birthtime ⇒ fallback honestamente INUTILIZÁVEL (breadcrumb + `none`),
   nunca o mtime. A premissa da spec §2 («creation mtime») está
   falsificada; desvio documentado. Controle novo:
   `test_state_file_anchor_uses_birthtime_not_mtime`.
3. **[P2] Leitor da chain ignorava `CEO_AUDIT_LOG_PATH/DIR`** — o emissor
   honra a precedência (PLAN-182 family-atomicity) e o scan lia só o
   default. CURA: probe de `audit_emit._log_path()` + espelho da
   precedência como fallback de partial-upgrade. O seed do TESTE tinha o
   MESMO bug (escrevia no default sob isolamento) — reproduzido e curado.
4. **[P2] Scan incompleto virava `absent`** — `is_file()` engole OSError;
   entrada ilegível some da passada. CURA: UM `stat()` explícito por
   entrada + flag `scan_incomplete`; incompleto sem observação positiva ⇒
   `error`, nunca classe-ausência. Controle novo:
   `test_incomplete_scan_never_reports_absent`.
5. **[P2] `_ledger_index` estourava o deadline compartilhado** — o 2º
   `_git` rodava incondicional (timeout fixo 2s) após o budget. CURA:
   re-check do deadline antes da leitura de seções E antes do last-commit;
   índice degradado é honesto, atrasado não.
6. **[P2] setUp com `os.environ[...]` direto** — abort pós-mutação vazaria
   steering vars (tearDown não roda quando setUp levanta). CURA:
   `mock.patch.dict` + `addCleanup` ("" = mesmo semântico de unset).
7. **[P2] `--with-slow` era no-op** — bug do GERADOR do clone: o bloco 4k
   foi dropado na substituição da bateria; `WITH_SLOW` era parseado e
   nunca lido. CURA: bloco 4k restaurado no gerador e no script
   (claims + verify-counts no WT sob a flag); bijeção T0 volta a fechar.

## Verificação das claims (receiving-review §3 — contra o código, não a fé)

Cada achado foi reproduzido antes da cura: U+FF40 atravessava o gate
(REPL); `_save_records` reescreve o arquivo (tool_lifecycle.py, lido);
`_log_path()` honra os dois envs (audit_emit:2340-2359); `is_file()`
documenta o swallow (pathlib); o 2º `_git` não relia deadline (diff);
`grep -c WITH_SLOW` no gerado = 2 (parse+init, zero leitores). Suites
pós-cura: 214 passed / 0 skipped nas 8 declaradas.
