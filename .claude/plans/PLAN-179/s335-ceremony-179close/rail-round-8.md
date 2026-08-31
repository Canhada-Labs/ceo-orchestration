# wave-179close — rail codex rodada 8 (sombra pós-curas r7, S336 2026-08-31)

Rail-Verdict: CHANGES-REQUESTED (5 P2 — TODOS verificados REAIS; 4 curados ANTES da r9, 1 é defeito de ENTREGA fora do conjunto revisado ⇒ followup com residual declarado)

Forma prompt-only (resumo r7 + instrução de não re-levantar os 2 refutados
sem nomear atacante dentro do threat model — respeitada: nenhum voltou).
Saída: `<scratchpad S336>/179close-r8.txt` (10.109 linhas), exit 0.
TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + destino)

1. **[P2] `harness-noop-allowlist.txt` não viaja ao adopter** —
   VERIFICADO: `install_hooks_selective()` copia só `*.sh`/`*.py`; o
   consumidor `check_harness_config.py` viaja, o txt não ⇒ adopter com
   kill-switch `off` teria a rota de waiver (b) indisponível
   (vermelho-falso no preflight). `scripts/install.sh` está FORA do
   EXPECTED revisado (alargar pós-rail assinaria superfície
   não-revisada), e entrega é domínio do delivery-routes (PLAN-183,
   próximo do trem). DESTINO: item 2 do
   `PLAN-179-FOLLOWUP-sessionstart-anchor-id.md` com residual declarado
   e workaround (rota (a) do gate: marker `_comment`).
2. **[P2] `_git` esticava budget sub-floor** — VERIFICADO:
   `max(0.05, timeout_s)` dava 50ms a um resto de 10ms, furando o wall
   deadline compartilhado do PreCompact. CURA: resto < 0.05s ⇒ `""`
   imediato, sem subprocess (fail-open honesto). Controle:
   `test_git_refuses_sub_floor_budget`.
3. **[P2] Corte por LINHAS não desligava `window_covers_file`** —
   VERIFICADO: arquivo <256KiB com >200 linhas dropava prefixo mantendo
   a flag ⇒ linha genesis-assinada na 1ª posição retida verificava
   GENESIS com o acima-da-janela INVERIFICÁVEL (SPEC: genesis só quando
   a janela cobre o arquivo INTEIRO — os DOIS caps). CURA: a flag
   reflete o cap de linhas também. Controles:
   `test_line_capped_window_never_claims_genesis` + companheiro positivo
   `test_line_uncapped_genesis_path_still_anchors` (o caminho legítimo
   genesis-sobre-prefixo-null continua ancorando sob 200 linhas).
4. **[P2] Deadline não re-checado após a verificação HMAC** —
   VERIFICADO: `return ts, "chain"` direto; a verificação (parse de
   predecessores + HMAC) pode cruzar o budget de 100ms e o contrato
   assinado exige exaustão ⇒ None (mesma doutrina do stat lento, r5).
   CURA: re-check pós-verificação. Controle:
   `test_anchor_deadline_rechecked_after_verification`.
5. **[P2] Renderer dobrava o index** — VERIFICADO: MEMORY.md já está em
   `modified_count` E em `names`; o sufixo `+ index` somava de novo
   (`index_only` renderizava "1 topic(s) + index" com zero tópicos).
   CURA display-only (o wire não muda): tópicos = count − index; names
   renderizados sem MEMORY.md; caso index-only vira
   "0 topic(s) + index (index only)". Controle:
   `test_render_does_not_double_report_index`.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **321/0** (8.12s) —
`EXPECTED_UNIT_PYTEST_PASSED` 316→321 atualizado conscientemente
(+5 controles, nada removido). Curas confinadas a 3 paths do EXPECTED
(SessionEnd, check_precompact, 2 suítes). Refinalize + r9 na sequência.
