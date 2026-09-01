# wave-179close — rail codex rodada 16 (sombra pós-curas r15, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (3 P2 — TODOS verificados REAIS; curados ANTES da r17)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r16.txt` (9.589
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P2] Cap do espelho contava CHARS, não bytes** — VERIFICADO:
   `TextIO.read(n)` limita caracteres decodificados; ~270 KiB de chars
   de 2 bytes passavam inteiros com `complete=True` além do cap
   PROMETIDO em bytes (e um AC além do cap elegia plano). CURA: leitura
   BINÁRIA de cap+1 bytes, corte byte-a-byte, decode depois (char
   partido na borda vira U+FFFD, inofensivo ao regex). Controle:
   `test_ac_scan_cap_is_bytes_not_chars` (plano de 270 KiB em 'á' com o
   AC no fim: pré-cura elegia, pós-cura recusa incompleto).
2. **[P2] `splitlines()` fragmentava linha assinada com U+2028** —
   VERIFICADO: produção grava `ensure_ascii=False` e U+2028/U+2029
   literais são JSON válido em string; `str.splitlines()` os trata como
   quebra ⇒ a PRÓPRIA linha do `session_start` virava fragmentos
   imparseáveis (âncora perdida) e a janela de 200 linhas inflava. CURA:
   split nos BYTES `b"\n"` com decode por registro (newline final
   descartado como não-registro). Controle:
   `test_u2028_in_signed_row_does_not_fragment` (linha assinada à mão
   com U+2028 literal no campo project: pós-cura ancora; pré-cura
   start_unknown).
3. **[P2] Traversal de null DEPOIS de linha assinada** — VERIFICADO:
   null entre linhas assinadas é LACUNA fail-open que o `verify_chain`
   acusa como violação de transição — atravessá-la consumia âncora de
   cadeia QUEBRADA. CURA: traversal de nulls é SÓ-prefixo
   (`crossed_null` + linha assinada acima ⇒ recusa); o caminho legado
   genuíno (nulls só no início do arquivo) segue ancorando. Controle:
   `test_null_gap_after_signed_row_refuses_anchor` (assinada→null→
   candidata assinada com prev da primeira: pré-cura ancorava, pós-cura
   start_unknown); os controles r5/r8 do prefixo legado seguem verdes.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **338/0** (11.17s) —
`EXPECTED_UNIT_PYTEST_PASSED` 335→338 (+3 controles). Curas confinadas a
4 paths do EXPECTED. Refinalize + r17 na sequência.
