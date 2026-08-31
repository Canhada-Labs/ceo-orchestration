# wave-179close — rail codex rodada 7 (sombra pós-curas r6, S336 2026-08-31)

Rail-Verdict: CHANGES-REQUESTED (6 P2 — 4 verificados REAIS e curados ANTES da r8; 2 REFUTADOS no threat model com pushback fundamentado + cura de honestidade de claim no wording)

Forma prompt-only (contexto de protocolo + resumo das curas r6 no prompt).
Saída: `<scratchpad S336>/179close-r7.txt` (9.921 linhas), exit 0.
TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + destino de cada um)

1. **[P2] Predecessor não re-verificado no `_anchor_verified`** —
   VERIFICADO no código (o candidato verifica contra o digest DECLARADO
   do prev; o prev em si não): o splice descrito existe MAS exige escrita
   no audit log, e **não existe configuração onde o atacante escreve o
   log sem ler a chave**: mesmo UID ⇒ chave 0600 legível ⇒ forja a cadeia
   INTEIRA (verificação de segmento não pararia nada); UID distinto ⇒ dir
   0700 ilegível. É a fronteira same-UID declarada no CLAUDE.md §5, fora
   de escopo por decisão. REFUTADO como ganho real; verificação de
   segmento seria claim decorativo (classe que este repo caça). CURA de
   honestidade: escopo PER-ENTRY declarado no comentário do
   `_anchor_verified` e no SPEC row (whole-chain = `verify_chain`
   offline).
2. **[P2] Identity fields (`session_id`/`project`) só type-check no
   emit_generic** — VERIFICADO, mas é a classe do EMITTER INTEIRO
   (baseline de TODAS as actions desde sempre), não introduzida por este
   patch; curá-la só nesta branch seria inconsistência, curá-la global
   está fora do conjunto revisado. O produtor sancionado desta action é o
   wrapper tipado, pinado por `test_no_paths_on_the_wire`. PUSHBACK
   fundamentado + CURA de wording no SPEC (o scrub é por NOME de campo;
   values de identity são contrato baseline do emitter). Hardening global
   de identity-values = candidato a wave própria se o Owner quiser.
3. **[P2] O ÚLTIMO sanitize pode estourar o budget** — REAL (o check r6
   era pré-chamada; nada re-checava antes do outcome otimista). CURA:
   re-check pós-loop antes do bloco de outcome; exaustão ⇒ `error` com
   counts finalizados. Controle: `test_final_sanitize_exhaustion_is_error`.
4. **[P2] `index_only` com scan incompleto** — REAL (claim EXCLUSIVO que
   uma entrada ilegível pode falsificar). CURA: `index_only` exige
   `not scan_incomplete`; degrada para `written` (evidência positiva
   fica, exclusividade cai). Controle:
   `test_incomplete_scan_never_claims_index_only`.
5. **[P2] Branch `-` do `_plan_id_from_path` aceitava qualquer 9º hífen**
   — REAL (doc diz `PLAN-NNN-*.md`; `PLAN-042-not-a-plan` e diretório
   com hífen derivavam id e podiam vencer o tie-break com pointer
   errado). CURA: branch `-` exige `.md` e ausência de `/`. Controle:
   asserts novos em `test_plan_file_shape_also_matches`.
6. **[P2] `ts` numérico não-finito** — REAL (`json.loads` aceita
   NaN/Infinity; NaN ⇒ toda comparação False ⇒ falso `absent` de âncora
   malformada — a classe "unparseable laundered into a claim"). CURA:
   `math.isfinite` gate no `_parse_wire_ts`. Controle:
   `test_nonfinite_wire_ts_is_unparseable`.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **316/0** (9.49s) —
`EXPECTED_UNIT_PYTEST_PASSED` 313→316 atualizado conscientemente
(+3 controles novos, nada removido; o F5 entrou como asserts em teste
existente). Curas confinadas a 4 paths, todos dentro do EXPECTED.
Refinalize + r8 na sequência.
