# PLAN-163 — misc probes (G6, G9, field-drop drift S284)

Date: 2026-07-28 · Probe: MISC (read-only; no canonical edits)

## 1. G6 — Task tool `mode` ignorado desde 2.1.212

Verdict: **assunção morta — guard NÃO referencia o parâmetro `mode` do Task tool.**

- `grep -n 'mode' .claude/hooks/check_agent_spawn.py`: todas as ~40 ocorrências são
  internas ao roteamento de modelo — "god-mode matrix" (linhas 86-96, 362-500),
  `get_mode()/_consult_model_routing_mode` (linhas 396-486), `_PRIMITIVE_DEFAULT_MODE`
  (linha 92), e modos ADVISORY/ENFORCING de rails (linhas 1794-1796).
- Grep word-boundary por leitura do input do Task tool
  (`(tool_input|params|input).*\bmode\b` e `"mode"`): **0 hits**.
- Conclusão: nenhum código dependia do parâmetro `mode` do Task; sua remoção/ignore
  em 2.1.212 não afeta o spawn guard. Assunção descartada com prova.

## 2. G9 — MCP >2min auto-background (2.1.212) vs pair-rail

Verdict: **dormente — pair-rail não usa MCP; auto-background não muda a semântica.**

- `.claude/settings.json` referencia `mcp__codex__*` em 3 pontos:
  - linha 180: comentário do sentinel canônico (Layer A: MCP write-shaped params);
  - linhas 287 e 468: matcher `mcp__codex__codex|mcp__codex__codex-reply`
    (guards PreToolUse — só disparariam SE alguém invocasse codex via MCP).
- O pair-rail real invoca codex como **subprocess CLI** (`codex exec`), não MCP:
  `check_pair_rail.py:571` emite `codex_invoke_dispatched` com `proc.returncode`
  de um subprocess; docs/memória confirmam `codex exec --output-last-message`
  (reviews 10-15min em nohup). O auto-background de MCP >2min portanto nunca
  entra no caminho do pair-rail.
- Registro mesmo dormente (exigência do plano): os matchers MCP permanecem como
  defesa Layer A contra uso futuro de codex-via-MCP; se o pair-rail migrar para
  MCP, o auto-background de 2min quebraria a suposição síncrona do hook e este
  item deve ser re-triado (guard-rail anotado, sem ação agora).

## 3. FIELD-DROP DRIFT (breadcrumbs S284)

Breadcrumbs no sidecar (`~/.claude/projects/ceo-orchestration/audit-log.errors`
linhas 37-38, ambos `2026-07-27T15:28:52Z`):

- `emit_generic codex_review_verdict dropped: ['verdict_text']`
- `emit_generic pair_rail_review_expected dropped: ['file_path']`

### Whitelists (scrub deny-by-default — funcionando COMO PROJETADO)
- `.claude/hooks/_lib/audit_emit.py:7134-7146` — branch `codex_review_verdict`;
  allowlist em `:7483` = `_CODEX_AUDIT_ENVELOPE | {outcome, diff_sha256}`.
- `.claude/hooks/_lib/audit_emit.py:7154-7170` — branch `pair_rail_review_expected`;
  allowlist em `:7516` = `_CODEX_AUDIT_ENVELOPE | {tool_name, file_path_hash_prefix, review_id}`.

### Call sites vivos (todos COMPLIANT — nenhum passa os campos dropados)
- `check_pair_rail.py:1466-1549` (`_emit_pair_rail_review_expected`): já converte
  `file_path` → `file_path_hash_prefix` via `_hash_file_path_prefix(file_path)`
  (linha 1537) antes de chamar o typed wrapper. NÃO passa `file_path` cru.
- `codex_review_user_code.py:213-235` (`_emit_verdict_telemetry`): passa somente
  `outcome`, `diff_sha256`, `session_id` (linha 235). NÃO passa `verdict_text`.
- Typed wrappers `audit_emit.py:8680` (`emit_codex_review_verdict`) e `:8741`
  (`emit_pair_rail_review_expected`) constroem o evento só com campos permitidos.
- Grep repo-wide (`.claude/`, `scripts/`, `~/.claude/hooks/`, tests): **zero**
  código vivo passa `verdict_text` ou `file_path` a `emit_generic` para essas
  actions.

### Diagnóstico
O drop veio de um **caller direto de `emit_generic`** fora dos call sites
rastreados — os dois breadcrumbs no MESMO segundo sugerem uma sonda/execução
in-process ad-hoc (janela S283, 07-27 15:28 UTC) rodada sem isolamento de env,
gravando no sidecar REAL (classe já documentada: teste/probe sem
`TestEnvContext`). Não é drift de whitelist: o docstring de
`emit_codex_review_verdict` (audit_emit.py:8687+) proíbe explicitamente persistir
o TEXTO do verdict (pode citar segredos do diff) e o de
`emit_pair_rail_review_expected` proíbe path cru (só o hash de 16-hex).

### Fix mínimo proposto (NÃO aplicado — paths canônicos)
**Lado CALLER, não whitelist.** NÃO adicionar `verdict_text`/`file_path` às
allowlists — ambos são exatamente as classes que o contrato MF-3/deny-by-default
existe para barrar (verdict pode quotar segredos; path cru vaza estrutura do
repo na cadeia assinada). Ação: (a) qualquer produtor futuro deve usar os typed
wrappers (`emit_codex_review_verdict` / `emit_pair_rail_review_expected`), que
já hasheiam/omitem esses campos; (b) se a sonda de origem for identificada em
W-execução, corrigi-la para env-isolado (`TestEnvContext`) — o guard em si está
saudável e o breadcrumb é prova-de-trabalho do scrub, não bug.
