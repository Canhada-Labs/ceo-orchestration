# wave-fable51 — rail codex rodada 1 (sombra base dc72bf1, 2026-09-01 S338)

Rail-Verdict: CHANGES-REQUESTED (2 P1 + 1 P2 — 1 P1 + 1 P2 REAIS e curados ANTES da r2; 1 P1 é de PROCESSO, respondido)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S338>/fable51-r1.txt` (7.174
linhas). Snapshot sha256 do diff da sombra antes/depois: TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1, REAL] `learn._tier_rank()` não conhecia o id novo** — admitido em
   `VALID_MODEL_IDS`, o `claude-fable-5-1` ranqueava `-1`; uma recomendação
   Fable 5.1 → Opus/Sonnet sairia como `promote` e passaria pelo gate de
   demote assinado (a MESMA classe do W2.10 F2 do PLAN-169, agora no
   sentido inverso). CURA: `"claude-fable-5-1": 7` no ladder (acima de
   `claude-fable-5`, 6) + dois testes em `test_learn_mutation.py`:
   `test_every_valid_model_id_has_a_rank` (paridade allowlist ↔ ladder —
   fecha a CLASSE para o próximo append) e
   `test_kill_fable51_ranks_above_fable5` (5.1→opus-5 = demote;
   fable-5→5.1 = promote). +2 paths no patch (27).
2. **[P1, PROCESSO] «o sentinel que a Amendment cita não existe no
   checkout»** — correto para a SOMBRA: o sentinel e os materiais vivem em
   `.claude/plans/PLAN-169/` da árvore viva e são commitados ANTES do SIGN
   (P0-d); o finalize RECUSA sombra com path fora do EXPECTED, então nunca
   estarão na sombra que o rail revisa. A autorização de cada path canônico
   é provada pelo G5 do LAND (`_sentinel_grants_path` vivo) contra o `.asc`
   do Owner — não pelo texto do ADR. CURA de forma: «Landed by» → «Lands
   through» (o ADR não afirma mais um passado que ainda não aconteceu).
3. **[P2, REAL — e a premissa estava ERRADA]** o `budget-summary.py` É uma
   superfície que precifica cache-read (multiplicador FIXO 0.10× em
   `_read_native_spawn`); a linha nova ativava esse preço para o 5.1 com
   uma taxa que a própria doc dizia não resolvida. Busquei a página oficial
   de pricing (2026-09-01): **cache hits do Fable 5.1/Mythos 5.1 = 0.025×
   do input base = $0.25/MTok; todos os outros modelos 0.1×**. Com 0.10×
   fixo o repo SUPERestimaria o cache-read do 5.1 em 4× (o codex supôs o
   sentido oposto porque leu «75% off» como 25% do input — o número
   verdadeiro é $0.25). CURA: `_CACHE_READ_MULTIPLIER_OVERRIDES` +
   `_cache_read_multiplier()` no budget-summary (0.10 default; 0.025 para
   5.1), usado na equivalência de input e no texto do relatório; teste
   `test_fable51_cache_read_multiplier`; ADR A2.1, `cost-table.yaml`,
   `provider-pricing.md` (linha + parágrafo do Source da tabela de cache)
   reescritos com o fato RESOLVIDO.

## Achado colateral da mesma consulta (FORA do patch — follow-up)

A página de pricing registra que o preço intro do Sonnet 5 ($2/$10)
**virou o preço padrão** — o aumento para $3/$15 em 2026-09-01 «will not
occur». As `_DATED_PRICING` de `audit-telemetry.py`, `ceo-cost.py` e
`budget-summary.py`, o sticker do `cost-table.yaml` e a linha de
`docs/cost-of-operation.md` SUPERestimam o Sonnet 5 em 50 % a partir de
HOJE. Superfícies livres; registrado na A2.3 como FOLLOW-UP nomeado, fora
desta wave por disciplina de escopo.

## Correção de claim minha (antes da r2)

O PROPOSED/ADR/upgrade.sh afirmavam que, sem a lista `superseded`, «a
parity e2e ficaria vermelha». Medido na própria e2e (Route B, pin v1.2.0,
`RESULT: PASS` em 2,5 min): `.claude/settings.json` é **divergência
ACEITA** («converge on keys, not on bytes») — a CI **não** pegaria a
ausência do 7º id. A cura do `upgrade.sh` é mais necessária, não menos: sem
ela todo adopter v1.2.0/v1.3.0 ficaria em silêncio com 6 ids e um WARNING
enganoso de ADOPTER-CUSTOMIZED. Texto corrigido nos três lugares.

## Verificação das claims

`_tier_rank` lido (`learn.py:535-558`: `order.get(model_id, -1)`);
`_direction` lido (`:561-566`); `_read_native_spawn` lido
(`budget-summary.py:1099-1113`: `0.10 * cache_read_input_tokens`);
página de pricing lida (tabela de modelos + nota 1 + tabela de
multiplicadores). Pós-cura: `apply-fable51-edits.py` re-derivado do zero
sobre HEAD (worktree novo), bateria curta re-medida — ver r2.
