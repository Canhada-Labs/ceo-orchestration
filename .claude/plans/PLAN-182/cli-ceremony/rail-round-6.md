# Pair-rail — wave-cli, rodada 6 (S326, 2026-08-24 16:3x–16:4xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–5 e os materiais atualizados (passo S de staging). `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The landing workflow can include files outside the signed and
reviewed patch, while collection isolation loses supported custom live-log paths in workers. The new
CLI also accepts malformed missing-value invocations as valid state-directory requests."*

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | O passo S faz `git add -u` (repo inteiro): um path rastreado sujo FORA do patch, tolerado no G0, entra no commit do land sem revisão/assinatura; a única pós-condição checava só o `.asc`. | **CONFIRMADO.** | **CURADO r7:** stage por path explícito = `touched(patch) ∪ {sentinel, .asc}`; o conjunto staged é comparado byte a byte com o esperado (`cmp`) e diverge ⇒ ABORTA nas duas direções. |
| 2 | P2 | `_snapshot_is_wellformed` exige basename `audit-log.jsonl`; sob o override suportado `CEO_AUDIT_LOG_PATH` com outro nome, o worker rejeita o snapshot herdado (correto) e re-resolve o DEFAULT — WS-D1 vigia o arquivo errado. | **CONFIRMADO** (o override é suportado; `_log_path()` o honra). | **CURADO r7:** aceita qualquer path absoluto `.jsonl` fora de árvore de isolamento. Teste novo: basename customizado herdado é preservado. |
| 3 | P2 | `runtime_paths.py --project --slug` consome `--slug` como PATH e imprime um state dir "válido" para um projeto chamado `--slug`; automação de shell iria para a árvore errada. | **CONFIRMADO.** | **CURADO r7:** valor de `--project` começando com `--` ⇒ erro de uso (exit 2, stdout vazio). Teste de uso estendido (`--project --slug`, `--project --help`). |

Severidades em queda (P1 de fluxo + 2 P2 de borda); conteúdo do patch: 2 linhas em `_lib`. Rodada 7 para confirmar.
