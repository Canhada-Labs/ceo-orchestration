# W1.2-0 — Probe da fonte nativa de custo + memos de budget

> PLAN-178 W1.2 (probe live-fire, read-only). Executado em 2026-08-14, sessão
> `4f050a6a-17c4-423b-a418-1da5b55742f0`, harness `claude 2.1.232` (medido com
> `claude --version`). Toda claim numérica abaixo foi re-derivada NESTA execução;
> comandos impressos junto de cada medição. O corpus é vivo (sessões concorrentes
> apendam) — números são o snapshot do instante da medição.

---

## 1. Censo da fonte nativa (live-fire)

### 1.1 O path real — e a correção ao plano

O path REAL da fonte nativa é:

```
~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/agent-a<...>.{jsonl,meta.json}          (rail Task)
~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/workflows/wf_<id>/agent-a<hash17>.{jsonl,meta.json}  (rail Workflow)
~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/workflows/wf_<id>/journal.jsonl          (journal por workflow, SEM meta)
```

com `<cwd-slug>` = path absoluto do repo com `/`→`-`
(`-Users-joaocanhada-canhada-labs-ceo-orchestration`). Verificação de que NÃO
existe nível `subagents/` direto sob o cwd-slug (sem SESSION-UUID):

```
$ ls ~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/subagents
NAO EXISTE
```

**Correção ao PLAN-178** (`.claude/plans/PLAN-178-mast-audit-substrate-adoption.md`,
item W1.2 = W1 item 2, linhas 92–101; o fingerprint errado está nas linhas 93–95):

> linhas 93–95: `fonte nativa CONFIRMADA em disco — fingerprint:`
> `` `subagents/agent-a<name>-<hash>.jsonl` (blocos `usage` por turno: input/cache_creation/cache_read) + `.meta.json` ({model, name, spawnDepth, taskKind}) ``

Três imprecisões, todas medidas:

1. **Falta o prefixo `<SESSION-UUID>/`** (e tudo acima dele). O glob do plano,
   aplicado literalmente sob o cwd-slug, retorna 0 arquivos.
2. **Falta a subárvore `subagents/workflows/wf_*/` inteira** — que é 81,3% do
   corpus (338 de 416 meta.json; medição em 1.2). O shape do nome também difere:
   no rail Workflow é `agent-a<hash17>` sem `<name>`.
3. **O schema `{model, name, spawnDepth, taskKind}` só descreve o shape
   teammate** (70/416 = 16,8%). `model` existe em 154/416; `name` e `taskKind`
   em 70/416; o shape Workflow é mínimo: `{agentType, spawnDepth}` (medição 1.4).

### 1.2 Contagens (comandos + resultados)

```
P=~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration
find "$P" -path '*/subagents/*.meta.json' | wc -l                 # → 416
find "$P" -type d -name subagents | wc -l                         # → 24  (sessões com subagents/)
find "$P" -maxdepth 1 -type d | tail -n +2 | wc -l                # → 26  (sessões com dir; 15 têm meta.json no rail Task)
find "$P" -type d -name 'wf_*' | wc -l                            # → 58  (workflows distintos)
# profundidade (componentes relativos ao cwd-slug):
find "$P" -path '*/subagents/*.meta.json' | sed "s|$P/||" | awk -F/ '{print NF}' | sort | uniq -c
#  78 3   → <SESS>/subagents/agent-a*.meta.json               (rail Task)
# 338 5   → <SESS>/subagents/workflows/wf_*/agent-a*.meta.json (rail Workflow)
```

| Métrica | Valor medido |
|---|---|
| `.meta.json` totais | **416** |
| — rail Task (`subagents/agent-a*`) | 78 |
| — rail Workflow (`subagents/workflows/wf_*/`) | 338 |
| Sessões (dirs) sob o cwd-slug | 26 (24 com `subagents/`) |
| Workflows distintos (`wf_*`) | 58 |
| Transcripts `agent-a*.jsonl` | 417 (79 Task + 338 Workflow) |
| `journal.jsonl` (1 por wf, sem meta) | 58 |
| meta.json SEM `.jsonl` pareado | 0 |
| `.jsonl` (agent-a*) SEM meta pareado | 1 (rail Task — edge case p/ o puller, §6) |
| Janela do corpus (mtime min/max dos meta) | 2026-07-13 → 2026-08-14 |

### 1.3 Distribuição de `taskKind` e `spawnDepth` (por shape de path)

```
find "$P" -path '*/subagents/*.meta.json' -print0 | xargs -0 python3 -c '<counter por (shape, taskKind) e (shape, spawnDepth)>'
```

| shape | taskKind | N |
|---|---|---|
| task-path | `in_process_teammate` | 70 |
| task-path | *ausente* | 8 |
| workflow-path | *ausente* | **338** |

| shape | spawnDepth | N |
|---|---|---|
| task-path | 0 | 70 |
| task-path | 1 | 8 |
| workflow-path | 1 | 338 |

`agentType` (por shape): task-path = 70 nomeados + 8 `general-purpose`;
workflow-path = 331 `workflow-subagent` + 4 `general-purpose` + 3 nomeados.
`customAgentType` existe em 7 arquivos, todos task-path (ex.:
`agentType:"sec-r1"` + `customAgentType:"security-engineer"`).

`model` (N=416): ausente **262**; `opus` 104; `claude-opus-5` 19; `sonnet` 9;
`claude-fable-5[1m]` 9; `claude-sonnet-4-6` 4; `claude-opus-4-8` 3;
`claude-fable-5` 3; `fable` 2; `haiku` 1 — **vocabulário misto (alias + id
completo), e TODO meta workflow-path vem sem `model`** (custo por agente
Workflow exige ler o model do transcript; ver §6).

### 1.4 Schema real — 3 exemplares (colados na íntegra)

**Exemplar A — rail Task, teammate nomeado** (`d2c626bc-…/subagents/agent-asec164-1487736821d841f9.meta.json`):

```json
{"agentType":"sec164","description":"Security debate AMEND-2","name":"sec164",
 "spawnDepth":0,"model":"claude-opus-5","taskKind":"in_process_teammate",
 "teamName":"session-d2c626bc","color":"pink","planModeRequired":false,
 "permissionMode":"auto"}
```

**Exemplar B — rail Task, Task-tool clássico** (`060354de-…/subagents/agent-abaf0869d028118b4.meta.json`):

```json
{"agentType":"general-purpose","description":"Load WebFetch via ToolSearch?",
 "toolUseId":"toolu_01Kan8ySJgQtnbUjmsMh2j5G","spawnDepth":1}
```

**Exemplar C — rail Workflow** (`9ef115b2-…/subagents/workflows/wf_db170209-bfa/agent-a06303f4e62938051.meta.json`):

```json
{"agentType":"workflow-subagent","spawnDepth":1}
```

União de campos nos 416 (contagem de presença): `agentType` 416, `spawnDepth`
416, `model` 154, `description` 77, `name`/`taskKind`/`teamName`/`color`/
`planModeRequired`/`permissionMode` 70 cada, `customAgentType`/`toolUseId` 7
cada. **Invariantes duras: só `agentType` e `spawnDepth` (416/416).**

### 1.5 Blocos `usage` no sidecar `.jsonl`

Cada meta tem transcript pareado. No transcript, tokens vivem em
`message.usage` por turno. Chaves observadas (transcript exemplar com 45
linhas-usage): `input_tokens`, `output_tokens`, `cache_creation_input_tokens`,
`cache_read_input_tokens`, `cache_creation` (aninhado), `service_tier`,
`speed`, `inference_geo`, `iterations`, `server_tool_use`.

---

## 2. Fingerprint de reversibilidade (AC-2c — entrada p/ substrate-watch)

Registrado como "versão+shape" (template do próprio W1.2, plano linha 113):

```yaml
fingerprint:
  harness: "claude 2.1.232"            # medido nesta execução
  raiz: "~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/"
  globs:
    task:      "subagents/agent-a*.meta.json"                       # + .jsonl pareado
    workflow:  "subagents/workflows/wf_*/agent-a*.meta.json"        # + .jsonl pareado
    journal:   "subagents/workflows/wf_*/journal.jsonl"             # sem meta, excluir do rollup
  meta_invariantes: [agentType, spawnDepth]                         # 416/416 hoje
  meta_shape_teammate: [name, taskKind=in_process_teammate, teamName, model, permissionMode]
  meta_shape_workflow: {agentType: workflow-subagent, spawnDepth: 1}  # e NADA mais
  usage_path: "message.usage"
  usage_chaves: [input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens]
sondas_de_drift:                       # qualquer uma dispara fallback p/ audit-log
  - glob task+workflow retorna 0 numa sessão que comprovadamente spawnou agentes
  - meta.json sem agentType OU sem spawnDepth
  - message.usage sem input_tokens/output_tokens
  - surgimento de nível novo entre subagents/ e o meta (shape de path mudou)
fallback: fonte audit-log existente do agent-budget (rota reversível; nunca substituição silenciosa)
```

---

## 3. Critério de switch (W1.2-6) — e o BLOCKER medido

Critério do AC-3 (plano linhas 228–235): janela fecha com **N≥50 eventos
COBRINDO os dois caminhos** (Task e Workflow) e switch só com **divergência
MÁXIMA POR CATEGORIA ≤10%** entre fonte nativa e audit-log (agregado não basta
— erros compensatórios passam no agregado).

**Volume nativo medido** (comando: soma de linhas com `message.usage` contendo
`input_tokens|output_tokens`, sobre os globs `agent-a*.jsonl`):

| Categoria (por SHAPE DE PATH) | transcripts | eventos-usage |
|---|---|---|
| Task | 79 | 6.563 |
| Workflow | 338 | 19.633 |

**BLOCKER registrado (medido nesta execução):**

1. **O eixo Task-vs-Workflow NÃO existe como CAMPO no corpus**: `taskKind` só
   assume `in_process_teammate` (70) ou ausente (346) — nenhum valor distingue
   Workflow (§1.3). Um categorizador por campo, como o plano sugere ao citar
   `taskKind` no schema, é INFECHÁVEL sobre este corpus.
2. **Nuance material (anomalia vs. a premissa da tarefa): o eixo EXISTE como
   shape de path** — `subagents/workflows/wf_*/` separa os dois rails com
   volume sobrado nos dois lados (6.563 / 19.633 ≥ 50). O lado NATIVO da
   comparação, portanto, fecha a janela HOJE, desde que a categoria venha do
   path, não do campo.
3. **Onde o AC-3 continua infechável é no COMPARADOR (audit-log)**: no log
   atual (`~/.claude/projects/ceo-orchestration/audit-log.jsonl`, rotação de
   2026-08-12T01:14:29Z até 2026-08-14T13:22:44Z, 9.140 linhas), os 86 eventos
   `subagent_lifecycle_observed` têm TODOS `tokens_in/out/total: null` (só
   `token_bucket` grosseiro) e **0 linhas do log inteiro mencionam `wf_`** —
   ou seja, o lado audit-log não tem número por spawn NEM categoria Workflow.
   Divergência "nativa vs audit-log por categoria" não tem o segundo operando.

**Conclusão W1.2-6:** switch AC-3 permanece INFECHÁVEL até que (a) o
comparador audit-log emita tokens numéricos por spawn com categoria, ou (b) o
critério seja re-baseado (decisão de plano, não deste probe). O dual-print do
AC-3 (as duas fontes lado a lado) segue viável e é o entregável de W1.2-1..5.

---

## 4. BUDGET-0 — o allow-precoce do emissor (`check_budget.py`)

Arquivo: `/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/hooks/check_budget.py`
(linhas citadas = as que EU li nesta execução).

Caminho exato do allow-precoce:

- **l.833** — `plan_path, active_plan_count = _resolve_active_plan(project_dir)`.
- **l.220–262** — `_resolve_active_plan`: "ativo" = filename casa
  `^PLAN-\d{3}-[a-z0-9-]+\.md$` (**l.128**) **e** `status` ∈
  `_ACTIVE_PLAN_STATUSES = {"executing","reviewed","draft"}` (**l.125**) **e**
  frontmatter `id` começa com `PLAN-`. Exatamente 1 match → `(path, 1)`;
  0 ou ≥2 → `(None, N)` (**l.260–262**).
- **l.854** — `if plan_id is None:` (com `plan_path=None`, `plan_id` nunca foi
  preenchido).
- **l.862–866** — com `active_plan_count >= 2`, breadcrumb forense
  `"indeterminate plan_id — N active plans; skipping budget check"`.
- **l.867–868** — `_claude_adapter.emit_decision(_contract.allow())` e
  `return 0`. **O rollup de tokens (l.870–876) e o cap (l.878+) nunca são
  alcançados.**

**Medição de hoje** (reproduzi o critério EXATO — regex l.128 + statuses l.125 +
`id:` — sobre `.claude/plans/`): **12 planos ativos** (3 `executing`:
PLAN-166/169/178; 9 `reviewed`: PLAN-167/168/171/172/173/174/175/176/177;
`PLAN-SCHEMA.md` é `accepted` E falha o regex de filename — fora). Logo
`_resolve_active_plan → (None, 12)` ⇒ **o cap de tokens por plano está INERTE
neste repo hoje**: todo tool-call cai no allow da l.867. O emissor W1.2 herda
esse comportamento se reusar `_resolve_active_plan` sem tratar o caso N≥2.

---

## 5. BUDGET-2 — divergência dos 5 resolvedores de plan-id

Cada linha verificada por leitura direta nesta execução (file:line reais).
Mesmo estado de repo (12 ativos / 3 executing) ⇒ **cinco respostas diferentes**.

| # | Resolvedor (file:line real) | Critério de "ativo" | Semântica em ambiguidade | Resultado HOJE |
|---|---|---|---|---|
| 1 | `.claude/hooks/check_budget.py:220` `_resolve_active_plan` | status ∈ {executing, reviewed, draft} (l.125) + filename `^PLAN-\d{3}-[a-z0-9-]+\.md$` (l.128) + `id:` PLAN-* | 0 ou ≥2 → `(None, N)`; consumidor faz allow-precoce | `(None, 12)` → cap inerte |
| 2 | `.claude/hooks/turbo_sessionstart.py:49` `_active_plan_id` | SÓ `status: executing` exato (`_EXECUTING_RE`, l.46), frontmatter nos 1ºs 4096 bytes, id via `^(PLAN-\d{3})` (l.44) | 0 ou >1 → `None` (sessão fica sem título; l.79–81) | `None` (3 executing) |
| 3 | `.claude/scripts/statusline-ceo.py:277` `active_plan_id` | `^status:\s*['"]?executing\b` (l.297) nos 1ºs 4096 bytes (`_PLAN_HEAD_BYTES`, l.105), cap 200 arquivos (`_MAX_PLAN_FILES`, l.104), filtro por prefixo `PLAN-`+`.md` (sem regex estrito de slug) | >1 → PRIMEIRO em ordem lexicográfica + marcador `+N` (l.303–305) | `PLAN-166+2` |
| 4 | `.claude/scripts/session-graph-build.py:604` `_active_plan_ids` | qualquer `status` não-vazio **≠ "done"** (l.620–622) + `^PLAN-(\d{3})(?:-[a-z0-9-]+)?\.md$` (l.75; slug OPCIONAL, diferente do #1) | retorna LISTA ordenada — não existe conceito de "único" | lista de 12 ids |
| 5 | `.claude/scripts/status.py:71` `_find_active_plan` | glob `PLAN-*.md` em ordem REVERSA; 1º `status: executing` vence; fallback = `done` mais recente (l.104–108) | ambiguidade IGNORADA silenciosamente — maior NNN executing ganha | `PLAN-178` |

Divergências semânticas que importam para o W1.2:

- **Conjunto "ativo" diverge**: #1 = {executing, reviewed, draft}; #2/#3/#5 =
  {executing}; #4 = tudo-menos-done (contaria `accepted`, `abandoned`,
  `superseded`, `archived` se aparecessem em arquivo `PLAN-NNN*`).
- **Regex de filename diverge**: #1 exige slug; #4 aceita `PLAN-NNN.md` sem
  slug; #3/#5 aceitam qualquer `PLAN-*.md` no scan.
- **Ambiguidade diverge nos 4 sentidos possíveis**: None-fail-open (#1, #2),
  primeiro+marcador (#3), lista (#4), último-vence-silencioso (#5).
- Consequência para atribuição de custo: um rollup por plano que escolher o
  resolvedor errado atribui os mesmos tokens a planos diferentes conforme a
  superfície consultada. O puller do W1.2 NÃO deve criar o 6º resolvedor —
  deve receber o plan-id como parâmetro ou reusar #1 documentando o caso N≥2.

---

## 6. Handoff para W1.2-1..5 (`cc-native-usage-pull.py`)

Contrato do puller, derivado do que foi medido:

1. **Raiz e dormência (fail-soft):** raiz =
   `~/.claude/projects/<cwd-slug>/` com `<cwd-slug>` derivado de
   `$CLAUDE_PROJECT_DIR` (`/`→`-`). Se NENHUMA sessão tiver `subagents/`
   (hoje: 24 de 26 têm), o puller fica **dormant**: rollup vazio, exit 0,
   nunca exception — mesma doutrina fail-open-em-infra do CLAUDE.md §4.
2. **Dois globs, categoria pelo PATH** (nunca por `taskKind` — §3 blocker):
   `*/subagents/agent-a*.jsonl` = Task;
   `*/subagents/workflows/wf_*/agent-a*.jsonl` = Workflow.
   **Excluir `journal.jsonl`** (58 hoje, sem meta, não é transcript de agente).
3. **Pareamento tolerante:** meta = mesmo basename com `.meta.json`. Corpus
   atual tem 1 transcript Task sem meta → atribuir `name=<desconhecido>`,
   categoria pelo path, e seguir; jamais crashar. Linha JSON malformada ou
   truncada (sessão viva apendando) → skip da linha.
4. **Extração:** somar `message.usage.{input_tokens, output_tokens,
   cache_creation_input_tokens, cache_read_input_tokens}` por transcript;
   volume hoje = 26.196 eventos-usage (6.563 Task + 19.633 Workflow).
5. **Custo exige model — e o meta NÃO basta:** `model` ausente em 262/416
   metas (TODOS os Workflow) e em vocabulário misto (`opus` vs
   `claude-opus-5` vs `fable` vs `claude-fable-5[1m]`). W1.2-1 deve (a)
   normalizar aliases via registry existente do repo, (b) para Workflow, cair
   para o `message.model` das linhas do próprio transcript; sem model
   resolvível → reportar tokens SEM custo (nunca inventar preço).
6. **Atribuição:** SESSION-UUID vem do path; **plan-id NÃO existe na fonte
   nativa** (nenhum campo em 416 metas) — o join sessão→plano é externo; usar
   resolvedor #1 (§5) parametrizado, documentando que com N≥2 ativos o rollup
   é por-sessão, não por-plano.
7. **Dual-print AC-3:** imprimir nativa vs audit-log por spawn e por categoria,
   com a coluna audit-log marcada `sem-número` enquanto
   `subagent_lifecycle_observed` emitir `tokens_*: null` (86/86 na rotação
   atual) — deixando visível ao Owner POR QUE o switch não fecha.
8. **Sonda de drift no arranque:** validar o fingerprint do §2; em drift,
   degradar para a fonte audit-log e reportar — reversibilidade AC-2c.
