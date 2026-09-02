# wave-fable51 — rail codex rodada 3 (sombra re-derivada pós-r2, base dc72bf1, 2026-09-01 S338)

Rail-Verdict: CHANGES-REQUESTED (1 P1 de PROCESSO — respondido, igual às r1/r2 — + 1 P1 REAL, curado ANTES da r4)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S338>/fable51-r3.txt` (7.992
linhas). Snapshot sha256 do diff da sombra antes/depois: TREE-INTACT.
As curas da r2 não foram reabertas (alias bare, `price_for`).

## Os achados

1. **[P1, PROCESSO — mesmo das r1/r2]** «o sentinel citado não está no
   checkout». Por desenho da sombra (finalize recusa path fora do EXPECTED);
   o sentinel + `.asc` são materiais commitados ANTES do SIGN e o G5 do LAND
   prova cada path canônico contra `_sentinel_grants_path` vivo. Sem cura.
2. **[P1, REAL] `success-receipt.py:_DEFAULT_PRICING` não tinha
   `claude-fable-5-1`** — e a inspeção mostrou o buraco MAIOR: o espelho era
   pré-gen-5 (opus-4-7, opus-4, sonnet-4-5, sonnet-4, haiku-4, gpt-5…),
   sem fable-5, opus-5, sonnet-5 nem opus-4-8. Em sessão MISTA, um modelo
   conhecido liga `cost_known=True` e `build_value_created` emite um total
   numérico `default-pricing-table` que DESCARTA em silêncio todo gasto da
   frota corrente (1M input de Fable = $10 sumidos). É a classe T1.5 no
   único espelho que o `test_model_fleet_presence.py` não amarrava. CURA:
   linhas da frota corrente (fable-5-1, fable-5, opus-5, opus-5-fast,
   sonnet-5 a $2/$10 padrão, opus-4-8, opus-4-8-fast, sonnet-4-6,
   haiku-4-5) nas taxas per-1k do `budget-summary.py`, históricas mantidas
   (ADR-142); classe `TestSuccessReceiptFleetPresence` no teste da frota
   (presença, taxas == budget-summary por modelo, históricas retidas, e o
   recibo MISTO sintético: sonnet-4-5 1k + fable-5-1 1M ⇒ $10.003 com
   `cost_source=default-pricing-table`). +1 path no patch (30).

## Varredura colateral (a classe, não só o achado)

`model-deprecations.json:223` lista os espelhos de preço/frota do repo:
`ceo-cost`, `cost-table.yaml`, `budget-summary`, `audit-telemetry`,
`success-receipt`, `value-dashboard`, `generate-dispatch`,
`spot-check-findings`, `detectors/*`, `optimizer/model_normalize`,
`_lib/adapters/live/claude.py`, `canonical_models.json`. Medido:
`generate-dispatch.py` e `spot-check-findings.py` não carregam tabela por
modelo (0 refs a fable-5); `_lib/adapters/live/claude.py:95`
`_ADAPTIVE_ONLY_MODELS` casa por PREFIXO (`claude-fable-5` cobre
`claude-fable-5-1`) — canônico e correto sem edição; `canonical_models.json`
é proveniência do Owner (r2). Nenhum outro espelho pendente.

## Verificação das claims

`_compute_cost_usd` (`success-receipt.py:363-378`: `pricing.get(model.lower())`
→ `None` quando ausente) e `build_value_created` (`:529-605`: `cost_known`
vira True em qualquer evento conhecido; `cost_source="default-pricing-table"`)
lidos — o mecanismo do P1 confere. Pós-cura: sombra re-derivada do zero,
bateria e rail r4 — ver r4.
