# wave-fable51 — rail codex rodada 2 (sombra re-derivada, base dc72bf1, 2026-09-02 S338)

Rail-Verdict: CHANGES-REQUESTED (1 P1 de PROCESSO — respondido, igual à r1 — + 2 P2 REAIS, curados ANTES da r3)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S338>/fable51-r2.txt` (10.567
linhas). Snapshot sha256 do diff da sombra antes/depois: TREE-INTACT.
A r1 está TODA curada (o rail não reabriu `_tier_rank` nem o multiplicador
de cache-read).

## Os achados

1. **[P1, PROCESSO — mesmo da r1]** «o sentinel citado não está no checkout».
   Verdadeiro para a SOMBRA por desenho (o finalize recusa path fora do
   EXPECTED); o sentinel e o `.asc` viajam com os materiais commitados
   ANTES do SIGN (P0-d) e cada path canônico é provado concedido pelo G5 do
   LAND (`_sentinel_grants_path` vivo). Sem cura no patch.
2. **[P2, REAL] `budget-summary._normalize_model_id("fable")` virou `None`** —
   com dois ids Fable no registro, `_family_candidates("fable")` devolve 2 e a
   doutrina «nunca adivinhar versão» resolve NADA. Consequência medida no
   fluxo: `_read_native_spawn` prefere `meta.model` (e metas nativas REAIS
   carregam o alias bare `fable`) e ignora o `message.model` EXATO do
   transcript ⇒ custo TBD para todo spawn com esse meta. Eu tinha previsto a
   ambiguidade e deixado passar «por doutrina» — o codex mostrou o custo
   real. CURA: quando o meta resolve `None` e o transcript tem um
   `message.model` diferente, cai para o transcript (evidência exata, não
   palpite); docstring atualizada; 2 testes em `test_model_fleet_presence.py`
   (alias bare → None; `fable-5-1`/`fable-5`/`[1m]` resolvem; e um spawn
   nativo sintético com meta `fable` + transcript `claude-fable-5-1` sai
   precificado a $10.25 = 1M input + 1M cache-read a 0.025×).
3. **[P2, REAL] `build-canonical-models.price_for("claude-fable-5-1")`
   colapsava no row de `claude-fable-5`** pelo resolvedor de prefixo
   (`startswith(mid + "-")`), devolvendo `cache_read_per_mtok=1.0` como
   «known» — a regra existe para pins DATADOS (`-20260101`), não para uma
   versão minor. Adicionar um row à mão contradiria a proveniência do arquivo
   (Owner fetch de models.dev, checksum sobre `models`). CURA pela doutrina
   S220: o prefixo só resolve sufixo `^\d{8}$`; `claude-fable-5-1` resolve
   UNKNOWN (zero + flag, nunca palpite) até o Owner re-fetchar a tabela; teste
   `test_minor_version_does_not_collapse_onto_base_row` (amostra + arquivo
   shipado). +2 paths no patch (29). **FYI ao Owner:** `staleness.valid_until`
   da tabela canônica é 2026-09-01 — a partir de amanhã ela é STALE
   (advisory); um re-fetch de models.dev traria o row do 5.1 com cache 0.25.

## Verificação das claims

`_family_candidates`/`_normalize_model_id` lidos (`budget-summary.py:493-560`);
precedência `model_raw = meta_model or transcript_model` (`:1095`);
`price_for` (`build-canonical-models.py:183-224`) e os testes de prefixo
existentes (`test_sibling_prefix_does_not_false_match`) — a cura preserva o
caso datado e o caso sibling. Consumidor do `price_for`: só o próprio script
(`canonical_price_source_enabled` é default-OFF) — impacto vivo mínimo, mas
a resposta errada com `known=True` era real.
