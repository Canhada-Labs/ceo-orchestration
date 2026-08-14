# PLAN-173 W1-A — Censo do MCP server existente

> **Data:** 2026-08-14 · **Método:** censo READ-ONLY derivado do CÓDIGO
> (enumeração viva de `dispatch.HANDLERS`, AST-scan de imports, greps com
> inputs impressos abaixo). Nenhum número copiado de docs sem re-derivação.
> **Veredito em uma linha:** o servidor que o W1 manda criar JÁ EXISTE,
> é stdlib-only, tem 40 métodos (39 em classes read-only) e cobre 2 das 3
> queries do AC — o delta real é (1) um método de saúde da cadeia HMAC,
> (2) o wiring Warp (protocolo + provisioning de cliente read-only).

---

## 0. Localização e forma

| Item | Valor medido | Como medi |
|---|---|---|
| Servidor | `.claude/scripts/mcp-server/` | `find -iname "*mcp*"` |
| Módulos (não-teste) | 20 arquivos `.py` | AST-scan (`files_checked: 20`) |
| Núcleo | `server.py`, `dispatch.py` (854 linhas), `auth.py`, `rate_limit.py`, `cost.py`, `http_transport.py`, `stdio_transport.py`, `handlers/` (12 módulos) | `ls` + Read |
| Launcher | `start-mcp-server.sh` (resolve Python ≥3.9, exec server.py) | Read |
| Transportes | **stdio** (JSON-RPC newline-delimited) e **HTTP** (default `127.0.0.1:9000`, loopback) — seleção via `CEO_MCP_TRANSPORT`; kill-switch `CEO_SOTA_DISABLE=1` | Read stdio_transport.py + start-mcp-server.sh |
| Runtime | **stdlib-only CONFIRMADO** — AST-scan dos 20 módulos: imports = `argparse, dataclasses, hashlib, hmac, http, importlib, json, os, pathlib, re, ssl, sys, threading, time, traceback, types, typing, uuid` + módulos internos. Zero third-party. | `python3 -B` AST walk nesta execução |
| CI | `.github/workflows/mcp-smoke.yml` (job "MCP introspection smoke") existe e roda o servidor em Python 3.12 pinado | grep no workflow |
| Contrato | ADR-042 + **ADR-042-AMEND-1** (33 métodos novos; 7 baseline + 33 = 40 entradas ACL — §Auth, linha 131 do ADR) + ADR-102 (introspecção) + ADR-122 (replay defense) | Read ADR |
| Testes de invariante | `tests/integration/test_mcp_readonly_invariant.py` (probe de escrita forjada) + `test_mcp_audit_query.py::test_method_count_matches_source` (contrato de contagem) | find + docstring do handler |

**Nota de proveniência da claim "v1.29.0":** o `target_tag: v1.29.0` está no
frontmatter do ADR-042-AMEND-1 (aceito 2026-05-20, S147) — é o versionamento
INTERNO pré-público. O repo público não tem essa tag (`git tag | sort -V`
termina em `v1.3.0-rc.3`; `VERSION` = `1.3.0`). O código está presente desde
o corte público v1.0.0 (arquivos datados de 2026-07-01).

## 1. Inventário completo de métodos (derivado de `dispatch.HANDLERS`)

Enumeração viva nesta execução: `python3 -B -c "import dispatch; ..."` →
**`TOTAL: 40`** (13 registrados explicitamente + 27 gerados de
`handlers/audit_query.HANDLERS`). Distribuição por classe (contada da mesma
saída): `readonly`=9, `audit_read`=28, `debate_read`=1, `cost_budget`=1,
`spawn`=1.

### 1.1 Métodos discretos (13)

| Método | Classe | O que faz (do código) | Read-only? |
|---|---|---|---|
| `list_skills` | readonly | Enumera skills varrendo `.claude/skills/<tier>/<slug>/SKILL.md` | ✅ |
| `get_skill` | readonly | Lê um SKILL.md por (tier, slug); defesa path-traversal explícita | ✅ |
| `list_agents` | readonly | Enumera **arquétipos** backend/frontend/staff de team.md (roster estático — NÃO é fleet vivo) | ✅ |
| `list_pitfalls` | readonly | Enumera pitfalls universais + por domínio | ✅ |
| `get_audit_log` | audit_read | Lê o audit log (cap 1000 eventos, filtros action/since) | ✅ |
| `server.capabilities` | readonly | Introspecção: protocol_version + handlers habilitados no ACL do caller | ✅ |
| `list_plans` | readonly | Lista `.claude/plans/PLAN-NNN-*.md` (frontmatter) | ✅ |
| `get_plan` | readonly | Frontmatter/corpo de um plan | ✅ |
| `get_plan_acs` | readonly | ACs de um plan | ✅ |
| `get_plan_dependencies` | readonly | Grafo depends_on de um plan | ✅ |
| `get_debate_state` | debate_read | Snapshot de debate SÓ pós-sentinel assinado; mid-debate retorna `{"state":"in_flight","round":N}` sem verditos | ✅ |
| `get_cost_budget` | cost_budget | **STUB** — retorna `status:"unwired"` (3 return sites, linhas 83/105/117; pré-PLAN-102) | ✅ (stub) |
| `spawn_agent` | spawn | **Passthrough de governança, SEM spawn real** ("No real spawn — Sprint 13 scope"): re-entra `check_agent_spawn.decide()` byte-idêntico + budget check e retorna `spawn_queued`. Não read-only por intenção (classe spawn, custo), mas hoje não muta nada no repo | ⚠️ passthrough |

### 1.2 Namespace `audit_query.*` (27 — todos `audit_read`, todos read-only)

Whitelist única `ALLOWED_SUBCOMMANDS` (AC-R-1); o sub-comando `label`
(o ÚNICO que escreve — labels store) é **excluído por design**.

`summary` (agregados single-pass) · `by_skill` · `by_day` · `by_domain` ·
`search` (regex) · `since` (corte por data) · `errors` (triage de erros) ·
`stats` (contagem por action) · `export` (slices json/csv) · `compliance`
(evidence pack SOC2/LGPD) · `debate` (rows por plan/round) · `plans`
(transições de status) · `vetoes` (por hook/reason) · `benchmarks` ·
`lessons` · `lessons_effectiveness` · `metrics` (derivadas) · `health`
(**gates comportamentais** — ver §3a) · `tokens` (agregados de spawn) ·
`claims` (confidence-gate) · `fp_rate` · `case_summary` · `spawn_stats`
(distribuição por modelo/skill) · `architect_outcomes` ·
`prune_restore_ratio` · `weekly_summary` · `codex_writeguard_summary`.

### 1.3 Auth/segurança já shipada (relevante para wiring externo)

- Bearer HMAC `v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>`, skew **±60s**, constant-time compare.
- Replay defense pós-HMAC (`BearerReplayStore`, ADR-122), loopback-only.
- ACL por cliente: `mcp_client_registry.<id>.handlers` — **match exato, fail-closed, wildcard `*` REJEITADO**.
- Secret por cliente em `state/mcp_client_secrets/<id>.key` (0600, 16–4096 bytes, anti-symlink/traversal).
- Rate limits por classe (`rate_limit.DEFAULT_LIMITS`, lido do código): readonly (60 rpm/burst 10), audit_read (30/5), spawn (6/2), debate_read (10/3), cost_budget (30/5).
- CORS default-deny (HTTP); auditoria `mcp_handler_invoked`/`mcp_handler_denied` em toda chamada.

## 2. W1 (PLAN-173 §1, linhas 39–49) item a item — JÁ-EXISTE vs DELTA-REAL

| # | O que o W1 pede | JÁ-EXISTE | DELTA-REAL |
|---|---|---|---|
| 1 | "Expor um MCP server de governança read-only" | ✅ Server completo, 39/40 métodos em classes read-only, CI-smoked | **Nenhum** — não criar nada |
| 2 | "consumível pelo Warp" | ⚠️ stdio existe, MAS o dialeto é JSON-RPC **customizado**: grep por `initialize\|tools/` em server.py + http_transport.py + stdio_transport.py = **0 matches** (exit 1). Não há handshake MCP padrão (`initialize`/`tools/list`/`tools/call`); auth viaja em `params.authorization` com token de ±60s | **O spike real**: shim/adaptador de protocolo MCP-padrão (stdlib) traduzindo `initialize`/`tools/list`/`tools/call` → os 40 métodos, gerando token fresco por request a partir do secret local |
| 3 | "estado dos plans" | ✅ `list_plans`/`get_plan`/`get_plan_acs`/`get_plan_dependencies` + `audit_query.plans` | Nenhum |
| 4 | "fila de aprovação" | ❌ Nenhum método expõe proposals pendentes (`.claude/proposals/`) nem debates aguardando sentinel; `get_debate_state` só dá `in_flight` opaco | Definir o que é a fila; compor client-side primeiro; método novo SÓ com evidência de gap (e passa por debate — §3 do plano congela o escopo por schema) |
| 5 | "últimos verditos" | ✅ (quase) `get_debate_state` (pós-sentinel) + `audit_query.debate`/`vetoes`/`claims` | Nenhum obrigatório; rollup de conveniência é opcional |
| 6 | "saúde do audit log (via check-audit-hmac-null.py)" | ❌ **Confirmado ausente** (ver §3a) | **1 método novo** `audit_chain_health` (wrapper read-only) |
| 7 | "fleet view" | ❌ vivo; retrospectiva existe (`audit_query.spawn_stats`/`by_domain`/`tokens`) | Decidir fonte de verdade (não existe fonte viva no server); NÃO é pré-requisito do AC |
| 8 | "Read-only por construção — NUNCA caminho de mutação" | ✅ AC-R-1 whitelist + probe de escrita forjada em teste; `label` excluído; ACL fail-closed sem wildcard; `spawn_agent` é passthrough sem spawn real e fica FORA do ACL do cliente Warp | Nenhum — só não listar `spawn_agent` no perfil |
| 9 | "Runtime: avaliar se stdlib-only aguenta" | ✅ **Pergunta já respondida**: servidor shipado É stdlib-only (AST-scan §0) | Nenhum — o kill "stdlib inviável em 2 sessões" está morto |
| 10 | AC: "3 queries (plans, verditos, saúde HMAC) em demo local, ≤2 sessões" | 2/3 existem hoje (plans ✅, verditos ✅, saúde HMAC ❌) | 1 método + wiring |
| 11 | "Entregável: spike + ADR de viabilidade" | ✅ Viabilidade PROVADA por código shipado + ADR-042/AMEND-1/102/122 | ADR só para o delta (método novo + perfil Warp) |

## 3. Os dois deltas conhecidos — verificados

### (a) Método de saúde da cadeia HMAC: **NÃO EXISTE** (confirmado)

- `grep -c -i hmac dispatch.py` = **19 linhas** — TODAS são auth de request
  (pipeline `verify_hmac`/`auth_hmac_invalid` do bearer token, passos 6–7b do
  docstring; lido linha a linha em §Branch 6/7b). Zero relação com a cadeia
  do audit log.
- `grep "hmac\|verify_chain" handlers/*.py` → 2 menções, ambas docstring de
  `audit_query.py` explicando a EXCLUSÃO do sub-comando `label`.
- `audit_query.health` (`cmd_health`, audit-query.py:1465–1531, lido): rola
  gates **comportamentais** (compliance ≥0.95, veto rate <0.15, debate
  completion ≥0.8) — **não chama `verify_chain()` nem toca integridade da
  cadeia**.
- Fontes prontas para embrulhar: `.claude/scripts/check-audit-hmac-null.py`
  (gate do defeito-de-nascença `hmac=null`, exit 0/1, tem `--json`; é o que
  o W1 nomeia) e `.claude/scripts/audit-verify-chain.py` (verificação
  criptográfica completa) — os dois existem e são complementares (docstring
  do próprio gate).

### (b) Perfil read-only para wiring externo (Warp): **mecanismo existe, perfil não**

O que EXISTE por construção:
- O ACL por cliente (`handlers` allowlist exata, fail-closed, sem wildcard)
  **É** o mecanismo de escopo read-only: um cliente cujo ACL lista só métodos
  read-only não consegue chamar `spawn_agent` (deny `acl_missing_handler`).
- `server.capabilities` reporta `spawn_agent_enabled: false` para esse perfil.
- Rate-buckets por classe + secret 0600 por cliente + replay defense.

O que NÃO existe hoje:
- **Nenhum cliente registrado**: `grep mcp_client_registry .claude/settings.json`
  → exit 1 (chave ausente). Todo request externo hoje morre no ACL.
- **Nenhum preset/gerador de perfil "readonly-full"**: sem wildcard nem alias
  de classe, o perfil completo exige listar os 39 métodos à mão;
  `docs/mcp-cursor-setup.md` (§3.2) manda o operador escrever o bloco
  manualmente — e cobre Cursor, não Warp, com hedges explícitos
  "(verify against Cursor 0.42+ docs)" na entrega do token.
- **O gap de protocolo do item 2 da tabela**: token ±60s + auth em `params`
  não é o que um cliente MCP-padrão faz; sem shim, o Warp enviaria
  `initialize` e receberia `-32601 Method not found`.

## 4. Recomendação — re-escopo do W1 para W1-B (delta real)

**Matar do escopo:** "criar o MCP server" (existe, CI-smoked, contrato em
ADR) e "avaliar se stdlib-only aguenta" (medido: aguenta — o servidor
shipado já é stdlib-only). O time-box de spike ≤2 sessões migra INTEIRO para
o wiring.

**W1-B proposto (3 unidades, na ordem):**

1. **W1-B.1 — `audit_chain_health` (o 1 método que falta).** Handler
   read-only classe `audit_read` embrulhando `check-audit-hmac-null.py
   --json` (+ sumário opcional de `audit-verify-chain.py`). Custo conhecido:
   handler + registro em `HANDLERS` + bump do contrato de contagem
   (`test_mcp_audit_query.py::test_method_count_matches_source` — 40→41) +
   entrada no ACL. **Governança obrigatória:** PLAN-173 §3 congela o escopo
   por schema — "qualquer método novo passa por debate"; formalizar como
   amendment do ADR-042 (read-only, então NÃO dispara a barreira de
   AMEND-2/VETO que o AMEND-1 reserva para superfícies de ESCRITA).
2. **W1-B.2 — Spike de wiring Warp (o time-box de ≤2 sessões vive aqui).**
   Passo 1: sondar o dialeto MCP do Warp contra o servidor cru (expectativa:
   incompatível — handshake padrão ausente por medição). Passo 2: shim
   stdlib fino, fora do core opcional se preciso, traduzindo
   `initialize`/`tools/list`/`tools/call` → dispatch e gerando bearer fresco
   por request do secret local. O shim entra como CLIENTE read-only (ACL sem
   `spawn_agent`) — a invariante "MCP nunca é caminho de mutação" fica
   preservada por construção, não por disciplina. **Kill atualizado:** Warp
   não fala com o shim em ≤2 sessões ⇒ componente morre (o kill antigo,
   "stdlib inviável", já caiu por medição).
3. **W1-B.3 — Provisioning do perfil read-only.** Bloco documentado (ou
   gerador) que cria a entrada `mcp_client_registry` com os 39 métodos
   read-only + secret 0600; espelhar o formato do
   `docs/mcp-cursor-setup.md` §3 com uma seção Warp.

**AC do W1-B (inalterado em espírito, agora crível):** as 3 queries do §1 —
`list_plans` (existe), `get_debate_state` (existe), `audit_chain_health`
(novo) — respondendo num demo local via Warp. "Fila de aprovação" e "fleet
view" saem do AC: compor client-side com os 40 métodos existentes primeiro;
método novo só com evidência de gap, cada um por debate.

**Não fazer:** habilitar `spawn_agent` no perfil Warp (é classe spawn +
custo, e mesmo sendo passthrough hoje, o Sprint-14+ pode ligar o dispatch
real); tocar no sub-comando `label`; qualquer rota de escrita via MCP
(não-escopo §2 do plano).

---

## Apêndice — inputs das medições (reprodutibilidade)

- Enumeração de métodos: `cd .claude/scripts/mcp-server && python3 -B -c "import dispatch; print(len(dispatch.HANDLERS)); ..."` → `TOTAL: 40` (2026-08-14, HEAD `1505bb6`).
- Handshake MCP padrão: `grep -n "initialize\|tools/" server.py http_transport.py stdio_transport.py` → exit 1 (0 matches).
- HMAC em dispatch: `grep -c -i hmac dispatch.py` → 19; leitura confirmou todas em auth de bearer (passos 6–7b).
- Registry ausente: `grep -n mcp_client_registry .claude/settings.json` → exit 1.
- stdlib-only: AST walk sobre 20 módulos não-teste; conjunto completo de imports impresso em §0.
- Tags: `git tag | sort -V | tail` → máximo `v1.3.0-rc.3`; `cat VERSION` → `1.3.0`.
- Rate limits: `rate_limit.py` linhas 54–64 (`DEFAULT_LIMITS`).
- Stub de custo: `grep -n unwired handlers/get_cost_budget.py` → linhas 83/105/117.
- `cmd_health`: `audit-query.py` linhas 1465–1531 (lidas integralmente).
