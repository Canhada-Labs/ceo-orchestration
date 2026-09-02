# Drift do substrato Claude Code 2.1.258 vs a doutrina do repo

**Data:** 2026-09-02 (S339). **Escopo:** só leitura — `check-substrate-watch.py`,
WebFetch do CHANGELOG upstream, `Skill(workflow-authoring)`, grep/Read no
repo. Nenhum spawn, Workflow ou Agent Team foi executado.

---

## 1. O que o instrumento `check-substrate-watch.py` já sabe — e o que está velho

`.claude/scripts/check-substrate-watch.py --json`/`--check` (lê
`.claude/scripts/substrate-watch.json`, path confirmado) reportou
`status: "current"` para os 8 componentes rastreados, todos `drift: false`.
**Essa resposta é estruturalmente vazia hoje**: cada linha do `--check`
mostra `installed=(not probed) (not probed (--probe-installed off))` — o
instrumento comparou o ledger só consigo mesmo, não com o Claude Code
2.1.258 recém-instalado. `last_seen` de `claude_code` é **2.1.198**
(2026-07-01) — **60 versões atrás** do binário de hoje — e o `_meta` do
ledger (`.claude/scripts/substrate-watch.json:17-21`) documenta que o
refresh é **PENDING-OWNER by design** (`WebFetch` manual, sem gasto de
tokens de agente, ADR-136-AMEND-1 no-network). Ninguém rodou o refresh
desde 01/07. `cc_workflow_rail` (2.1.237, 2026-08-20) e `cc_native_usage`
(2.1.232, 2026-08-14) são os componentes mais recentes — atualizados por
PROBE dedicada, não pelo mecanismo de refresh do ledger.

Isto é exatamente a classe **"instrumento verde cuja PERGUNTA envelheceu"**
(memória `feedback-instrument-green-with-stale-question.md`): `status:
current` é verdade sobre o ledger, não sobre o substrato instalado.
Recomendação mecânica: rodar `check-substrate-watch.py --probe-installed`
(se a flag existir) ou o refresh recipe do `_meta`, e então comparar contra
2.1.258 explicitamente — isso NÃO foi feito aqui (fora do escopo desta
tarefa, que é só-leitura).

---

## 2. CHANGELOG upstream, 2.1.220 → 2.1.258

Fonte: `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`
(2 fetches, 2026-09-02). **Não há entradas publicadas entre 2.1.220 e
2.1.231** no CHANGELOG (gap de numeração ou builds internos — não
verificado qual). A partir de 2.1.232 o changelog é denso; itens
relevantes a orquestração, por versão:

| Versão | Data (se citada) | Mudança relevante a orquestração |
|---|---|---|
| 2.1.232 | — | `subagent_type: 'fork'` (forking) vira **default ON** — herda conversa+cache completos. `defaultMode: 'bypassPermissions'` passa a ser tratado como `'auto'` (era honrado literalmente antes). `/code-review` em high/xhigh/max effort passa a rodar em agente de background. |
| 2.1.233 | — | Cgroup de memória opt-in para Bash (`CLAUDE_CODE_TOOL_MEMORY_LIMIT`). Todo/task tools removidos de modelos mais novos por padrão (`CLAUDE_CODE_ENABLE_TODO_TOOLS=1` restaura). |
| 2.1.234 | — | Novo env var `CLAUDE_CODE_PROJECT_DIR_NAME` para nomear o diretório de config. |
| 2.1.236 | — | Novo env var `ANTHROPIC_DEFAULT_MODEL`. `notify_when_idle` chega ao `SendMessage` cross-session (alerta one-shot de ociosidade). `Monitor`: allow-rules ficam de lado enquanto auto mode está ativo. |
| 2.1.237 | — | (last_seen do componente `cc_workflow_rail` no ledger.) Estilo de saída "Concise" nativo. |
| 2.1.238 | — | `keybindingFlavor`; `claude self-hosted-runner --defer-shutdown-max-min`. |
| 2.1.239 | — | `/model`, `/fast`, `/effort` passam a rodar imediatamente em Bedrock/Vertex/Foundry. |
| 2.1.243 | — | `modelPicker`, `promptCacheTtl`/`subagentPromptCacheTtl`, `modelPricing` (rates org-contratadas). `/code-review` pode iniciar sozinho em Bedrock/Vertex/Foundry. |
| 2.1.246 | — | Aba "Auto mode" em `/permissions` para regras do classificador. `/loop` disponível em todas as plataformas. |
| 2.1.247 | — | `SendFeedback` tool. `/claude-api cost-optimize`. Setting "Default teammate model" **removido** de `/config` — teammates de Agent Teams agora usam o modelo do líder. `/schedule` explica que MCP servers locais não anexam a rotinas cloud. |
| 2.1.248 | — | `--restricted` flag. `experimental.cacheTtl` por agente no frontmatter. Cross-session messaging chega a Bedrock/Vertex/Foundry quando telemetria desligada. Fix: `ScheduleWakeup` mudava de shape entre sessão e `--resume`, quebrando o cache. |
| 2.1.250 | — | `subagent_type` omitido agora lista os agentes disponíveis no erro. `notify_when_idle` (2ª entrada no changelog — feature reforçada/corrigida). |
| 2.1.251 | — | **`PreModelSwitch`/`PostModelSwitch`** — 2 hook events NOVOS. `SessionStart` de resume agora recebe staleness + custo de re-cache estimado. Streaming ao vivo de tool calls de subagentes foreground para clientes Remote Control. Footprint de prompt do **Workflow tool cai de ~5,7k para ~1k tokens**. Fixes em Agent Teams: teammate travado em tmux/iTerm2 após shutdown; resposta final de teammate não chegando ao team lead; subagente de background incapaz de responder mensagem de sibling/parent sem nome. Fix: `/schedule` rotina salva sem role de mensagem rodava sem ter o que fazer. |
| 2.1.257 | — | **Claude Fable 5.1 vira modelo default**, com pricing atualizado (bate com a cerimônia `wave-fable51` já montada, `f0e98de`). `/effort s` (efeito só na sessão atual). Auto mode ganha regra "Containment Escape" (credenciais de metadado de nuvem, evasão de egress, cross-tenant reach deixam de ser auto-aprovados). Sessões via agent view respeitam `defaultMode` do diretório-alvo. |
| 2.1.258 | — | Agent tool: subagentes que paravam por corte de resposta agora **continuam automaticamente**. `Monitor`: fix de monitors órfãos quando o subagente de bg é parado. `/loop`: wake-ups consecutivos sem trabalho colapsam numa linha. |

**Achado extra (fetch dedicado ao doc de hooks, não ao changelog):**
`https://code.claude.com/docs/en/hooks` lista **33 hook events** hoje —
incluindo `TaskCreated`, `TaskCompleted`, `TeammateIdle`,
`PreModelSwitch`/`PostModelSwitch`, `WorktreeCreate`/`WorktreeRemove`,
`PermissionRequest`/`PermissionDenied`, `PostToolBatch`, `MessageDisplay`,
`UserPromptExpansion`, `InstructionsLoaded`, `CwdChanged`, `FileChanged`,
`Elicitation`/`ElicitationResult`, `StopFailure`, além dos 13-15 já
conhecidos. Isto colide diretamente com o critério de drift do próprio
ledger (`cc_workflow_rail.watch_for`, `substrate-watch.json:98`): "*a
enum de hook events mudando (hoje 31 events — controle recorrente da
PLAN-169 W4)*" — a contagem documentada hoje (33) já não bate com o
"31" da última medição comportamental (probe `wf_d7af49d9`, 2.1.237,
S315). Isso **dispara** o gatilho de re-rodar a sonda comportamental e
re-decidir o ramo vermelho do ADR-191 §4 — não foi feito aqui (fora de
escopo, exige spawn).

Verifiquei quantos desses 33 tipos estão de fato religados em
`.claude/settings.json` (`hooks` top-level keys): **15** —
`ConfigChange`, `DirectoryAdded`, `Notification`, `PostCompact`,
`PostToolUse`, `PostToolUseFailure`, `PreCompact`, `PreToolUse`,
`SessionEnd`, `SessionStart`, `Setup`, `Stop`, `SubagentStart`,
`SubagentStop`, `UserPromptSubmit`. Os outros **18 tipos documentados —
incluindo `TaskCompleted`, `TeammateIdle`, `PreModelSwitch`,
`PostModelSwitch`, `WorktreeCreate`/`WorktreeRemove`,
`PermissionRequest`/`PermissionDenied` — não têm NENHUM hook religado**;
logo, zero visibilidade de audit-log ou de `check_agent_spawn.py` sobre
eles hoje.

**[NÃO VERIFICADA]** A introdução de Agent Teams em ~v2.1.32
(2026-02-05) como research preview vem de um agregador de terceiros
(gradually.ai/releasebot.io via WebSearch), não do CHANGELOG oficial —
não confirmei a data na fonte primária.

---

## 3. `agent(prompt, {model})` num Workflow — HONRADO hoje, não mais INERTE

**Resposta direta à pergunta do CEO:** na versão medida mais recente do
substrato (harness **2.1.237**), o override `opts.model` de `agent()`
dentro de um Workflow **É HONRADO** — deixou de ser inerte. Isso reverte
o veredito antigo W0a (`PLAN-134/W0a-VERDICT.md`, S227) citado como vivo
em `.claude/plans/PLAN-163-substrate-uplift.md:101` (G16, "RE-VERIFY em
2.1.220 — T4.4") e em `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md:1512-1513`.

**Fonte canônica:** `.claude/adr/ADR-144-subagent-model-tiering-frontmatter.md`,
seção "Amendment (PLAN-169 W4.3 / S328, 2026-08-25)". Citação: *"o rail
Workflow ROTEIA modelo na versão corrente."* Medição: probe
`wf_9ddadaab-12f`, harness **2.1.237**, n=2 — um agente despachado com
`opts.model='haiku'` **serviu** `claude-haiku-4-5-20251001` (lido do campo
`model` da resposta, "servido, não pedido"); o controle sem override
herdou `claude-fable-5`. A própria ADR se declara **escopo estreito**: "*a
timeless property and carries no forward guarantee — the Workflow rail
routed opts.model on the version measured, and a later harness may stop
doing so without announcing it*" — ou seja, **não há re-medição
publicada especificamente em 2.1.258**; a doutrina pede verificar via o
campo `model` da resposta, não assumir.

**Corroboração ao vivo nesta sessão:** invoquei `Skill(workflow-authoring)`
(reflete o substrato realmente em execução agora) e o texto da skill
descreve `opts.model` como uma opção funcional sem qualquer ressalva de
inércia: *"opts.model overrides the model for this agent call. Default to
omitting it — the agent inherits the main-loop model (the resolved
session model), which is almost always correct."* Isso é consistente com
HONRADO, não com INERTE.

**Consequência prática para um night-run via Workflow lançado de uma
sessão Fable 5.1:** por omissão (nenhum `opts.model` no script), TODOS os
agentes de um Workflow herdam o modelo da sessão — hoje Fable 5.1 — então
"roda tudo em Fable" **é verdade por omissão**. Mas como o override agora
É honrado, qualquer script de workflow que fixe `opts.model` explicitamente
para algum estágio (ex.: `haiku` para uma etapa barata) vai de fato
rotear e FATURAR nesse tier — o pressuposto antigo ("não importa o que o
script peça, tudo roda no modelo da sessão") não vale mais. Isso é
relevante para dois dos quatro workflows shipados
(`.claude/workflows/eval-baseline-n20.js`, `nightly-hygiene.js`) e para
qualquer script futuro que tente tiering de custo via `opts.model`.

**Dois sítios canônicos ainda carregam a claim refutada** (nomeados,
não silenciosamente deixados, per ADR-144 e `PLAN-169:1515-1528` OQ-11):
1. `.claude/plans/PLAN-178-mast-audit-substrate-adoption.md:402-403` (AC-3)
   — "opts.model é INERTE no Workflow".
2. `.claude/workflows/eval-baseline-n20.js:3,284,547` — description ainda
   cita "Because Workflow opts.model is INERT (W0a verdict...)". O
   MECANISMO (subprocess `claude -p --model`) continua correto por
   DESENHO (isolamento de config + billing ground-truth), não por
   inércia — só o texto está desatualizado. `.claude/workflows/README.md`
   §"The W0a caveat" já foi curado (S334) e é a fonte viva correta hoje.
   A cura desses dois sítios ficou para uma "carona" numa cerimônia
   futura (decisão OQ-11 do Owner) — ainda não landada no disco a partir
   desta leitura.

---

## 4. Feature do substrato × doutrina do repo

| Feature (versão) | Estado no repo | Cobertura de governança | Recomendação | Esforço |
|---|---|---|---|---|
| Agent tool `isolation: worktree\|remote`, `subagent_type: fork` (fork default-ON desde 2.1.232) | Doutrina de spawn é FLAT (`.claude/team.md:493-510`); nada no repo referencia `isolation:` ou fork explicitamente | `check_agent_spawn.py` vê o Task/Agent dispatch nativo; não há evidência de que ele distinga `isolation:worktree` como classe própria | Avaliar com sonda: `isolation:"worktree"` muda o modelo de ameaça de canonical-edit (agente escreve fora do checkout supervisionado)? | ~30-60k tokens, 1 sessão |
| Nesting até 5 níveis (doutrina cita "5 levels" — ADR-082/team.md:494) | Doutrina FLAT trata nesting como perigo, não adota; `CEO_MAX_SPAWN_DEPTH` é RESERVED, não ligado (H11 DEFERRED) | Rail 2 depth-fence existe mas é advisory + cooperativo (`check_agent_spawn.py:1822-1833`, per PLAN-163 G5); cobertura em depth≥2 DESCONHECIDA | Manter fora — doutrina já nomeia o risco e o harvest item (H11); não há fato novo que mude o cálculo | n/a (já decidido) |
| Workflow tool `agent(prompt,{model})` — HONRADO desde ≥2.1.237 (era INERT no W0a) | ADR-144 emendado (S328); 2 sítios legados (`PLAN-178` AC-3, `eval-baseline-n20.js`) ainda citam INERT | Nenhuma — é uma propriedade do runtime, invisível ao audit log até o agente rodar e emitir uso | Adotar a doutrina emendada como viva; landar a cura textual dos 2 sítios na próxima cerimônia que já toque esses arquivos (per OQ-11) | ~5-10k tokens, carona (não pack próprio) |
| Workflow tool footprint 5,7k→1k tokens (2.1.251) | Nenhuma referência no repo | n/a | Observar só — reduz custo fixo de qualquer workflow existente, sem mudança de comportamento | 0 (nenhuma ação) |
| Agent Teams (peer-teammate, `TeammateIdle`/`TaskCompleted`) | "Research-preview, NOT adopted" (`.claude/team.md:512-527`); pilot hipotético descrito como algo a desenhar no futuro | `TeammateIdle` e `TaskCompleted` **já existem como hook events reais hoje** (doc oficial) mas **não estão religados** em `.claude/settings.json` (15/33 tipos religados) | Avaliar com sonda antes de escrever o pilot: a doutrina do team.md fala desses hooks como se fossem hipotéticos — na verdade o MECANISMO já existe, só falta a decisão de adoção + religar. Corrigir o texto do team.md para não implicar que o hook não existe | ~20-40k tokens, 1 sessão para a sonda + emenda textual |
| `PreModelSwitch`/`PostModelSwitch` hooks (2.1.251, NOVOS) | Zero menção no repo | Não religados; zero visibilidade | Avaliar com sonda: um `/model`/`/fast` no meio de sessão de cerimônia muda o modelo sem o rail perceber? Isso é uma superfície de tamper de tier (LLM-finops) | ~15-25k tokens |
| Cross-session `notify_when_idle` (SendMessage, 2.1.236/2.1.250) | Zero menção; SendMessage cross-session usado ad-hoc em night-runs (per memórias S328/S329) | n/a | Avaliar: pode substituir o polling manual usado nas night-runs para saber quando um agente-por-quota terminou | ~10-15k tokens |
| `defaultMode: 'bypassPermissions'` tratado como `'auto'` (2.1.232) | `night-mode` skill arma acceptEdits explicitamente para a PRÓXIMA sessão | Nenhuma quebra óbvia (acceptEdits ≠ bypassPermissions), mas vale checar se algum template usa `bypassPermissions` esperando o comportamento literal antigo | Verificação rápida em `templates/settings/*.json` | ~5k tokens |
| `CLAUDE_CODE_PROJECT_DIR_NAME` (2.1.234, novo env var) | `runtime_paths.py`/ADR-001 resolve o slug do projeto por path nativo (`CLAUDE_PROJECT_DIR_NATIVE`), família de carriers neutralizados em `WHOLE_DIR_OVERRIDE_CARRIERS` (S322) | Se este env var influenciar o nome do diretório de config do jeito que `CLAUDE_PROJECT_DIR_NATIVE` influencia hoje, é um carrier NÃO neutralizado | Avaliar com sonda — mesma classe que motivou a wave `wave-cli`/S322 (mistura de cadeia HMAC entre projetos) | ~15-20k tokens |
| Auto mode "Containment Escape" rule (2.1.257) | Repo não usa `defaultMode: auto` como padrão (dispatch é native/mitigated) | n/a diretamente, mas relevante se algum sub-fluxo futuro adotar auto mode | Manter fora por ora — nenhum fluxo do repo roda em auto mode hoje | n/a |
| `/fast`, `ToolSearch`/`ENABLE_TOOL_SEARCH` | "Já absorvido" per `PLAN-163-substrate-uplift.md:79` | Fora do escopo desta tarefa (doutrina já marca como adotado) | Nenhuma ação | n/a |
| `RemoteTrigger`/rotinas cloud (`/schedule`) | Zero menção no repo; night-runs hoje são sessões locais longas | n/a | Manter fora — rotina cloud tira a sessão do controle direto do Owner (GPG, TTY, cerimônia local) que a doutrina de cerimônia exige | n/a |

---

## 5. Cinco features perdidas que valem sonda

1. **`opts.model` honrado no Workflow (ADR-144 emenda) não foi propagado
   aos 2 sítios legados** (`PLAN-178` AC-3, `eval-baseline-n20.js`) — não
   é bem uma "sonda", é uma cura textual pendente e já nomeada (OQ-11);
   incluo aqui porque é a maior discrepância entre doutrina escrita e
   substrato medido encontrada nesta leitura.
2. **`TeammateIdle`/`TaskCompleted` já existem como hook events reais** —
   o pilot hipotético do `team.md:520-527` pode ser desenhado com dados
   reais (nomes de evento confirmados), não mais como especulação.
3. **`PreModelSwitch`/`PostModelSwitch`** — superfície de tamper de tier
   não coberta por nenhum hook nem teste hoje; toca diretamente o domínio
   VETO do `llm-finops-architect` e do ADR-144.
4. **Contagem de hook events documentados subiu de 31 (medido, 2.1.237)
   para 33 (documentado, hoje)** — dispara o próprio gatilho de drift do
   ADR-191 §4 que o ledger já nomeia; a sonda comportamental
   (`wf_d7af49d9`-like) deveria re-rodar.
5. **`CLAUDE_CODE_PROJECT_DIR_NAME`** — mesma classe de risco que motivou
   a wave `wave-cli` (carrier de nome de diretório fora do resolvedor
   único); vale confirmar que não é mais um carrier não neutralizado.

## Três que devem continuar fora — e por quê

1. **Agent Teams como topologia adotada.** Mesmo com `TeammateIdle`/
   `TaskCompleted` confirmados como hooks reais, o CHANGELOG mostra a
   feature ainda recebendo fixes de comportamento básico até 2.1.251
   (resposta final não chegando ao team lead, teammate preso em
   tmux/iTerm2) — não é maduro o bastante para uma topologia peer que já
   é doutrinariamente reconhecida como bypass do roteamento CEO→specialist.
2. **`RemoteTrigger`/rotinas cloud (`/schedule` cloud agents).** Tira a
   sessão do TTY/GPG local que toda cerimônia deste repo assume
   (`feedback-harness-green-without-tty-does-not-prove-owner-ceremony.md`);
   adotar exigiria redesenhar a cerimônia inteira, não só religar um hook.
3. **Nesting de subagentes além de depth 1.** A doutrina FLAT já é uma
   decisão deliberada com harvest item nomeado (H11, DEFERRED) — nada
   nesta leitura do CHANGELOG muda esse cálculo; o rail de profundidade
   segue advisory por desenho, não por lacuna nova.

---

## Fontes

- `.claude/scripts/check-substrate-watch.py --json`/`--check` (rodado
  2026-09-02).
- `.claude/scripts/substrate-watch.json` (ledger, `_meta.fetched:
  2026-07-01`).
- `.claude/settings.json` (`hooks` top-level keys, lido 2026-09-02).
- `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`
  (2 WebFetch, 2026-09-02, janelas 2.1.220-2.1.231 e 2.1.232-2.1.258).
- `https://code.claude.com/docs/en/hooks` (WebFetch 2026-09-02, lista de
  33 hook events).
- `https://code.claude.com/docs/en/changelog` (WebFetch 2026-09-02,
  fallback — sem entradas adicionais além do CHANGELOG.md bruto).
- WebSearch "Claude Code Agent Teams research preview 2026" (2026-09-02)
  — fontes terciárias gradually.ai/releasebot.io, **[NÃO VERIFICADA]**
  contra a fonte primária.
- `Skill(workflow-authoring)` — texto vivo da skill, invocado nesta
  sessão em 2026-09-02.
- `.claude/adr/ADR-144-subagent-model-tiering-frontmatter.md` (emenda
  S328, PLAN-169 W4.3, probe `wf_9ddadaab-12f`).
- `.claude/plans/PLAN-163-substrate-uplift.md:60-189` (gap-matrix G1-G17).
- `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md:1495-1534`
  (OQ-11/OQ-12).
- `.claude/team.md:470-540` (spawn-depth doctrine, Agent Teams
  pre-positioning, routing table).
- `.claude/workflows/README.md:35-51` (§"The W0a caveat, AMENDED").
- `.claude/adr/ADR-136-AMEND-1*.md`, `.claude/adr/ADR-191*.md` (headers).
