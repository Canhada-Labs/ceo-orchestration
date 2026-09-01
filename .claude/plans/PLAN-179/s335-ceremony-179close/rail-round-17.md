# wave-179close — rail codex rodada 17 (sombra pós-curas r16, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (4 P2 — TODOS verificados REAIS; curados ANTES da r18)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r17.txt` (10.792
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P2] Segmento em branco quebrava o walk** — VERIFICADO: linha em
   branco interna / CRLF-only / newlines finais múltiplos contavam no
   cap de 200 e derrubavam o `json.loads` do predecessor numa cadeia que
   o `verify_chain` aceita (ele pula registros vazios). CURA: TODO
   segmento whitespace-only cai ANTES do cap e do walk. Controle:
   `test_blank_lines_do_not_break_the_chain_walk`.
2. **[P2] Registro não-objeto tratado como legacy-null** — VERIFICADO:
   lista/escalar JSON dava `prev_hex=None` e era ATRAVESSADO — um
   candidato genesis-assinado ancorava numa cadeia que o oráculo rejeita
   (`line_not_object`). CURA: não-dict ⇒ fail-closed no walk. Controle:
   `test_non_object_record_is_not_legacy_null`.
3. **[P2] Rename/delete invisível fabricava `absent`** — VERIFICADO:
   rename preserva o mtime sob o nome novo e delete some — o scan de
   end-state não vê, mas as três operações de namespace bumpam o mtime
   do DIRETÓRIO. CURA: `structural_seen` (dir mtime na janela) entra na
   MESMA álgebra do skew/incompleto — bloqueia classe-ausência (⇒
   `error`) e a exclusividade do `index_only`; o enum fechado não
   expressa delta estrutural e a recusa é o honesto (cláusula no SPEC).
   Efeito colateral verificado: os testes de `absent`/`index_only`
   criavam arquivos no setup e bumpavam o dir — helper `_age_dir`
   simula o dir intocado de produção (3 testes ajustados, o mecanismo
   documentado no helper). Controle:
   `test_rename_only_session_never_claims_absent`.
4. **[P2] Cap do LEDGER em CHARS** — VERIFICADO: mesma classe r16-P2-a
   no SEGUNDO sítio. CENSO DA CLASSE varrido desta vez (grep de todos os
   `read(` capados nos dois hooks): este era o último em modo texto.
   CURA: leitura binária + decode. Controle:
   `test_ledger_section_cap_is_bytes_not_chars` (heading além do teto de
   bytes não entra no snapshot; heading antes entra).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **342/0** (7.81s) —
`EXPECTED_UNIT_PYTEST_PASSED` 338→342 (+4 controles; 3 testes ajustados
com `_age_dir`, mecanismo declarado). Curas confinadas a 4 paths do
EXPECTED. Refinalize + r18 na sequência.
