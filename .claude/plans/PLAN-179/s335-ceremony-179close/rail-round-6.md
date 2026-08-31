# wave-179close — rail codex rodada 6 (re-despacho S336 da rodada morta na S335, 2026-08-31)

Rail-Verdict: CHANGES-REQUESTED (5 P2 — TODOS verificados REAIS contra o código; 4 curados ANTES da r7, 1 travado + residual declarado em followup)

Forma prompt-only, prompt VERBATIM do despacho da S335 (recuperado do echo
do parcial `<scratchpad S335>/179close-r6.txt`, morto por kill externo sem
veredito). Rodado de dentro da sombra (`shadow-179close`, 18 paths),
gpt-5.6-sol effort xhigh. Saída: `<scratchpad S336>/179close-r6b.txt`
(10.766 linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós
byte-idêntico; verificado antes do despacho que a última escrita da sombra
(17:34) precede a derivação do W179CLOSE.patch (17:35).

## Os achados (verificação + o que cada cura fez)

1. **[P2] Atribuição de escrita concorrente** — o dir de memória é POR
   PROJETO e compartilhado; overlap de sessões é caso suportado (ADR-005).
   Escrita da sessão B dentro da janela de A satisfaz o predicado de mtime
   de A. VERIFICADO: stat não carrega autor — insanável em produtor
   stat-only. CURA pela 3ª rota que o próprio revisor ofereceu (contract
   wording): docstring + comentário no predicado + SPEC row reescritos —
   a observação é ATIVIDADE NA JANELA sobre o dir do projeto, nunca claim
   de autoria. Controle:
   `test_overlap_write_is_window_activity_not_authorship`.
2. **[P2] Produtor env-first × consumidor payload-gated** — VERIFICADO
   REAL: `SessionStart.py:559-561` grava `session_start` com precedência
   `CLAUDE_SESSION_ID` > payload; o scan do US8 é payload-gated por
   decisão de SEGURANÇA (r3/r4: env é agent-spoofable e nunca ancora —
   relaxar re-entra o gate de VETO). Ids divergentes ⇒ `start_unknown`
   (degradação SEGURA: preferir não saber a janela errada). A cura
   correta é no PRODUTOR — `SessionStart.py` está FORA do conjunto
   EXPECTED revisado; alargar escopo pós-rail assinaria código
   não-revisado. Nesta wave: trava de consumo
   `test_divergent_env_id_never_anchors` + residual declarado em
   `PLAN-179-FOLLOWUP-sessionstart-anchor-id.md` (payload-first no
   produtor, cerimônia própria).
3. **[P2] Espelho do derive_scope só tinha a perna plan_dir** —
   VERIFICADO: `check_ledger_checkpoint.derive_scope` tem plan_dir E
   plan_ac (paths de implementação declarados por AC `[P?][USn][path]`);
   `_ledger_index` espelhava só a primeira ⇒ commit só-implementação
   derivava índice vazio e o US7 omitia o pointer exatamente no commit
   que o checkpoint-rail associa a um plano. CURA: `_ac_path_index_mirror`
   (espelho LITERAL da perna b — mesmos caps/regex/tie-break; import
   hook-a-hook segue proibido), rodando só para paths não-casados, sob o
   mesmo deadline. Controle:
   `test_ac_declared_implementation_path_resolves_plan`; o guard AST
   anti-`resolve_plan_id` passa a cobrir as 3 funções.
4. **[P2] Loop de sanitização fora do wall-cap** — VERIFICADO: a NOTE
   capa a função INTEIRA; N nomes rejeitados nunca disparam o cap de
   aceitos e os scans semânticos rodariam além do budget com outcome
   otimista. CURA: deadline re-checado por nome; exaustão retorna
   `error` com counts finalizados. Controle:
   `test_name_scan_respects_wall_deadline`.
5. **[P2] Timeout descartava counts parciais** — VERIFICADO: os dois
   early-returns copiavam só `files_count`, zerando `modified_count`/
   `index_modified` já observados ("partial counts" do contrato é
   PLURAL). CURA: os dois returns finalizam os três campos. Controle:
   `test_budget_exhaustion_preserves_partial_counts`.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **313/0** (8.97s) —
`EXPECTED_UNIT_PYTEST_PASSED` 308→313 atualizado CONSCIENTEMENTE com
fonte (+5 controles novos, nada removido). Curas confinadas a 5 paths,
todos dentro do EXPECTED. Refinalize + r7 na sequência.
