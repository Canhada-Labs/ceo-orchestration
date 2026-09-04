# W0-US4 — precedência `inherit` × pin de arquétipo (AC-10), medida na S340 (2026-09-03)

> Pergunta fixada (PLAN-186 W0-US4): quando um spawn NÃO passa `model:`, o modelo SERVIDO é o do assento (herança) ou o pin de `.claude/agents/<tipo>.md`? Decide se o piso VETO é enforcement de runtime.

## Método

- Assento da sessão: `claude-fable-5-1` (escolha do Owner na S340; herança = fable-5-1).
- 8 spawns com tarefa trivial («devolva OK»), nenhum leu arquivo: 5 pela via **Workflow** (`agent()` com/sem `agentType`, com/sem `model`) e 3 pela via **direta** (`Agent` tool: `subagent_type` nativo + prompt gerado por `inject-agent-context.sh`, SEM `model`).
- O modelo SERVIDO foi lido do campo `message.model` das mensagens do assistente em cada transcript (`<session-dir>/subagents/**/agent-*.jsonl`), não do auto-relato do agente.

## Resultado

| via | agentType / subagent_type | pin em `agents/*.md` | `model:` passado | modelo SERVIDO |
|---|---|---|---|---|
| Workflow agentType=code-reviewer | `code-reviewer` | `claude-fable-5` | `opus` | `claude-opus-5` |
| Workflow agentType=code-reviewer | `code-reviewer` | `claude-fable-5` | — | `claude-fable-5` |
| Workflow agentType=general-purpose | `general-purpose` | `(sem pin)` | — | `claude-fable-5-1` |
| Workflow agentType=qa-architect | `qa-architect` | `claude-sonnet-4-6` | — | `claude-sonnet-4-6` |
| Workflow sem agentType | `workflow-default` | `(sem agentType)` | — | `claude-fable-5-1` |
| code-reviewer (nativo, Agent tool) | `code-reviewer` | `claude-fable-5` | — | `claude-fable-5` |
| qa-architect (nativo, Agent tool) | `qa-architect` | `claude-sonnet-4-6` | — | `claude-sonnet-4-6` |
| general-purpose (Agent tool) | `general-purpose` | `(sem pin)` | — | `claude-fable-5-1` |

## Leitura

1. **No rail nativo, o PIN vence a herança** — nas DUAS vias (Workflow com `agentType` e `Agent` tool com `subagent_type`): `code-reviewer` foi servido em `claude-fable-5` e `qa-architect` em `claude-sonnet-4-6`, ambos diferentes do assento.
2. **Sem arquétipo, vale a herança**: `general-purpose` e o agente default do Workflow foram servidos no modelo do assento (`claude-fable-5-1`). É o caso do rail MITIGADO (persona injetada em `general-purpose`), que por construção ignora o pin — confirma a nota da S339.
3. **`model:` explícito vence o pin**: `agentType=code-reviewer` + `model: "opus"` foi servido em `claude-opus-5` (o agente auto-relatou `claude-opus-5[1m]`; o transcript registra `claude-opus-5`), DENTRO do piso VETO: `claude-opus-5` é membro de `VETO_FLOOR_ALLOWED` (`.claude/hooks/_lib/agent_frontmatter.py:135-141`, ADR-149/ADR-181). A sonda prova que o override por chamada vence o pin EXATO/preferido (`claude-fable-5`), não que rodou abaixo do piso; provar um furo do piso exigiria um override para tier NÃO permitido (Sonnet/Haiku) — sonda não executada esta noite (rail S340 r1 P2).
4. **Consequência de governança (o que a US4 devia decidir) — REESCRITA pelos rails r12/r13:** a camada T (pins de `agents/*.md`) é o modelo SERVIDO por DEFAULT no rail nativo (vence a herança), mas **NÃO é enforcement**: o item 3 mostra que `model:` explícito vence o pin, e `check_agent_spawn.py:372-381` documenta que o payload do Agent hook não expõe o modelo despachado — o gate não PODE inspecioná-lo («a block would be theater»). Um `model: sonnet`/`haiku` num spawn VETO nativo passaria com gate verde; essa célula NÃO foi medida (:29) e é o que falta para o AC-10. Chamar o pin de «enforcement» criaria falsa garantia de segurança — o piso VETO hoje é convenção de frontmatter + detector post-hoc (AC-13). A alavanca de CUSTO permanece: migrar os pins muda o default servido, logo migrá-la (5 pins VETO `claude-fable-5` → `claude-fable-5-1`, 4 pins IC → `claude-sonnet-5`) é alavanca real de custo e de piso — não higiene. Ao mesmo tempo, o piso VETO não protege o rail MITIGADO (herança do assento): um `code-reviewer` despachado como `general-purpose` a partir de um assento Sonnet roda Sonnet com o gate verde. Contra `model:` explícito a sonda desta noite NÃO decide (o override testado, `claude-opus-5`, está dentro do piso); o hook valida o ARQUIVO, e se ele valida também o modelo PEDIDO fica como item aberto da W1 (teste: override para Sonnet num arquétipo VETO). Os dois fatos entram na W1 (OQ-9: camada T + herança explícita numa cerimônia).
5. Detalhe: o auto-relato do agente (`claude-opus-5[1m]`) divergiu do campo servido (`claude-opus-5`) — mais um motivo para o detector permanente da W1 ler o TRANSCRIPT, nunca o que o agente diz de si.

## Fontes

- Transcripts: `<session-dir>/subagents/workflows/wf_02b720e1-cfa/agent-*.jsonl` (via Workflow) e `<session-dir>/subagents/agent-aus4-*.jsonl` (via direta).
- Pins: `.claude/agents/{code-reviewer,qa-architect}.md`; herança: `CLAUDE_CODE_SUBAGENT_MODEL=inherit` (PLAN-186 §1 fato 6).

## Célula below-floor (S343, 2026-09-04)

> Pergunta que faltava (AC-10, reaberto pelos rails r10/r12/r24 da S340): um
> `model:` EXPLÍCITO **abaixo** do piso VETO num spawn de arquétipo VETO é
> servido como pedido, ou o pin de `.claude/agents/code-reviewer.md`
> (`claude-fable-5`) o segura? A S340 só mediu um override DENTRO do piso
> (`opus` → `claude-opus-5` ∈ `VETO_FLOOR_ALLOWED`) — :28-29 desta página.

### Método (rail Workflow)

- 2 spawns pelo rail do Workflow com `agentType: 'code-reviewer'` (o arquétipo
  VETO: `veto_floor: true`, `model: claude-fable-5`) e `model:` explícito
  abaixo do piso — `sonnet` e `haiku`. Tarefa trivial de sonda (devolver um
  canário; nenhum arquivo lido, nenhum comando corrido).
- **O `model:` PEDIDO não está no `.jsonl`** (o transcript registra o servido,
  não o solicitado) — mas ele **É PERSISTIDO**, um-para-um, no sidecar
  `<agent-id>.meta.json` ao lado de cada transcript. O rail r4 corrigiu aqui
  uma afirmação FALSA de substrato: a versão anterior desta página dizia que o
  pedido só existia no sítio efêmero. O repo já reconhece esse par
  transcript/metadata em `.claude/scripts/cc-native-usage-pull.py:153-180`.
  Conteúdo VERBATIM dos dois sidecars — a prova um-para-um mais forte de que
  cada célula pediu o que diz ter pedido:

```json
// <session-dir>/subagents/workflows/wf_dc95ca8a-fc2/agent-af1621b0e2266543e.meta.json
{"agentType":"code-reviewer","spawnDepth":1,"model":"sonnet"}
// <session-dir>/subagents/workflows/wf_dc95ca8a-fc2/agent-a7ef0363d48a1bd99.meta.json
{"agentType":"code-reviewer","spawnDepth":1,"model":"haiku"}
```

  **Consequência para a AC-13:** o insumo do detector JÁ EXISTE no disco, por
  spawn e sem mudança de harness — `agentType` (⇒ o arquétipo é VETO?) e o
  `model` PEDIDO, ao lado do servido. O 2º predicado de piso é implementável
  hoje; falta o instrumento, não o dado.

- Corroboração no sítio do spawn (efêmero, mas mostra a FORMA da chamada), de
  `<session-dir>/workflows/scripts/night-s343-plan186-wf_dc95ca8a-fc2.js:481-482,575`:

```js
const PROBES = [
  { key: 'sonnet', model: 'sonnet', canary: 'US4-BELOWFLOOR-CANARY-s343-sonnet' },
  { key: 'haiku', model: 'haiku', canary: 'US4-BELOWFLOOR-CANARY-s343-haiku' },
]
// ...
agent(probePrompt(c), { label: `probe:ac10-${c.key}`, phase: 'Build',
  agentType: 'code-reviewer', model: c.model, effort: 'low', schema: PROBE_SCHEMA })
```
- O modelo SERVIDO foi lido do campo `message.model` das entradas
  `type: "assistant"` de cada transcript. O auto-relato do agente NÃO é
  evidência (a S340 já pegara a divergência `claude-opus-5[1m]` vs
  `claude-opus-5`); aqui os dois bateram, o que não muda a regra.

### Resultado (rail Workflow)

| célula | `model:` declarado | pin do arquétipo | dentro do piso? | modelo SERVIDO (transcript) | veredito |
|---|---|---|---|---|---|
| below-floor A | `sonnet` | `claude-fable-5` | **NÃO** | `claude-sonnet-5` | override VENCE o pin e o piso |
| below-floor B | `haiku` | `claude-fable-5` | **NÃO** | `claude-haiku-4-5-20251001` | override VENCE o pin e o piso |

Fragmentos crus (primeira entrada de assistente de cada transcript, campos
não relevantes elididos):

```json
// <session-dir>/subagents/workflows/wf_dc95ca8a-fc2/agent-af1621b0e2266543e.jsonl
{"timestamp": "2026-09-04T02:42:26.156Z", "message": {"id": "msg_011CehdRirayJa8zZLDD2VtZ", "type": "message", "role": "assistant", "model": "claude-sonnet-5"}}
// <session-dir>/subagents/workflows/wf_dc95ca8a-fc2/agent-a7ef0363d48a1bd99.jsonl
{"timestamp": "2026-09-04T02:42:28.070Z", "message": {"id": "msg_011CehdRiKb7J8Zvvpr3iA8e", "type": "message", "role": "assistant", "model": "claude-haiku-4-5-20251001"}}
```

Em cada transcript o conjunto de `message.model` sobre TODAS as entradas de
assistente tem exatamente um elemento (não houve troca de modelo no meio da
sonda). **A atribuição transcript → célula repousa no sidecar
`<agent-id>.meta.json`, não no canário** (correção S343: o canário NÃO é
chave injetiva — no workflow ele aparece também nos transcripts de agentes que
o CITAM ao relatar a sonda; nenhum número acompanha esta frase de propósito,
porque o workflow seguia vivo e o conjunto de arquivos que casam o canário
cresceu entre duas medições). A chave que É injetiva é o censo por
`agentType` dos sidecares do workflow `wf_dc95ca8a-fc2`, **medido em
2026-09-04T07:44:02Z**: os únicos com
`agentType == "code-reviewer"` são **dois** — um
com `model: "sonnet"` (`agent-af1621b0e2266543e`) e um com `model: "haiku"`
(`agent-a7ef0363d48a1bd99`) — e o transcript homônimo de cada um tem conjunto
de `message.model` singleton, respectivamente `claude-sonnet-5` e
`claude-haiku-4-5-20251001`. (O TOTAL de sidecares do workflow não é citado
de propósito: ele cresceu a cada re-medição enquanto o workflow seguia vivo,
e um número datado num documento permanente apodrece. A metade load-bearing
— dois sidecares `code-reviewer`, um por célula — foi re-derivada em cada
medição, inclusive na derivação final deste texto.)

### A resposta escrita (o que o AC-10 pedia)

**O modelo servido seguiu o OVERRIDE, não o pin — e não o piso.** Um spawn
de arquétipo VETO (`code-reviewer`, `veto_floor: true`) com `model: sonnet`
foi servido em `claude-sonnet-5`, e com `model: haiku` em
`claude-haiku-4-5-20251001`; nenhum dos dois é membro de
`VETO_FLOOR_ALLOWED` (`{claude-opus-4-8, claude-fable-5, claude-opus-5}` —
`.claude/hooks/_lib/agent_frontmatter.py`, ADR-149/ADR-181). A precedência é:

> `model:` explícito ≻ pin de `agents/<tipo>.md` ≻ herança do assento

sem nenhuma trava de piso em nenhum dos degraus. **Escopo da evidência**
(rail r3 P2, ampliado na v4): o degrau `pin ≻ herança` foi medido na S340 nos
DOIS rails (Workflow com `agentType` e `Agent` tool com `subagent_type`); o
degrau `override ≻ pin` ABAIXO DO PISO foi medido **nos dois rails também** —
no Workflow acima, e no rail NATIVO do `Agent` tool na subseção «Célula Agent
tool» adiante (2026-09-04T07:36Z). Nenhum dos dois é inferência.

Portanto, com o escopo EXATO (rail de cura r1 v4, P2): **o piso VETO TEM
gate de runtime sobre o ARQUIVO do arquétipo, e NÃO tem gate sobre o
`model:` de cada chamada.** A metade que existe está em
`check_agent_spawn.py:2425-2455`: para cada papel de `VETO_FLOOR_ROLES`
nomeado no spawn, `check_veto_floor_for_role()` verifica que
`.claude/agents/<papel>.md` ainda liga a um membro de `VETO_FLOOR_ALLOWED` e,
se não liga, o hook BLOQUEIA (`GOVERNANCE: veto_floor_demoted`) — é a defesa
contra demoção-via-frontmatter (PLAN-045 W1 P0-03, F-01-03). **Duas ressalvas,
as duas verificadas no código** (rail do land r1, P2): (a) a lista de papéis a
checar é derivada por SUBSTRING sobre `description` + `prompt` e **IGNORA o
`subagent_type`** (`check_agent_spawn.py:2435-2440`: o `haystack_lower` é
`description.lower()` + `prompt.lower()`, e o laço faz `continue` quando o slug
do papel não aparece ali) — logo um spawn DIRETO cujo `subagent_type` seja um
papel VETO mas cujo texto livre não cite o slug nunca chega a essa comparação;
é um SEGUNDO contorno, agora do lado do arquivo, e a rota que falta é o lookup
autoritativo por `subagent_type`. Nestas células o `description` (verbatim no
sidecar acima) NÃO carrega o slug, portanto se o ramo rodou dependeu do texto
livre do prompt, não do arquétipo declarado. (b) Mesmo tendo rodado, ele não
teria bloqueado: `code-reviewer.md` seguia pinado em `claude-fable-5`, que é
membro. O que elas mostram é que essa defesa é **contornável por fora**:
um `model:` por chamada vence o pin sem passar por nenhuma comparação. Dizer
«o piso é só convenção» esconderia o ramo que existe; dizer «o piso é
enforçado» criaria falsa garantia. O verdadeiro é o par: **arquivo gateado
QUANDO o papel é nomeado no texto livre do spawn, chamada nunca.**

**Existe um detector post-hoc do piso, e o que estas células mostram é uma
lacuna de COBERTURA, não a ausência dele** (correção S343: a versão anterior
desta página negava a existência de qualquer detector do piso — afirmação
que eu verifiquei FALSA no disco antes de reescrever esta passagem).
`detect_veto_non_opus()` está implementado em
`.claude/scripts/ceo-escalation-detector.py:382-410` («Signal 5 — VETO-role
spawn with non-Opus model», `severity: "high"`) e REGISTRADO na tupla
`_DETECTORS` (`:449-455`, portanto rodado por `detect_all`). Seu predicado
CASA exatamente esta célula: papel ∈ `_VETO_ROLES` (`:92` —
`{code-reviewer, security-engineer}`) e o **campo `model` do evento
`agent_spawn`** fora de `_FLOOR_TIER_PREFIXES` (`:97` — `claude-opus-`,
`claude-fable-`). Atenção ao que esse campo É (rail de cura r1 v4, P2): ele
NÃO é lido do transcript — nas células nativas ele traz o **alias DECLARADO**
(`sonnet`, `haiku`), medido adiante; o id SERVIDO só existe no transcript.
Sobre uma linha `role=code-reviewer, model=claude-sonnet-5` ou
`model=sonnet` ele ACUSARIA, com severidade alta — mas o que ele julga é a
DECLARAÇÃO registrada na telemetria, não o modelo servido. Quem fechar a
AC-13 não pode contar esta perna como cobertura do piso SERVIDO.

**Mas ele NÃO é o predicado do piso — são DUAS lacunas, não uma** (rail de
cura r1, P1; verificado no disco). O `_VETO_ROLES` do detector cobre **2 dos
5** papéis de `VETO_FLOOR_ROLES` (`agent_frontmatter.py:118-124` —
`incident-commander`, `identity-trust-architect` e `threat-detection-engineer`
ficam de fora; o próprio código declara a lacuna, `_lib/escalation_signals.py:61-66`,
«acknowledged drift», decisão separada do Owner), e o teste de modelo é de
PREFIXO (`claude-opus-`/`claude-fable-`, escolha deliberada porque ids de
audit vêm sufixados — `escalation_signals.py:69-71`), não MEMBRESIA em
`VETO_FLOOR_ALLOWED`: por isso ele aceita `claude-fable-5-1`, que **não** é
membro do piso. A divergência já está no censo desta mesma W0
(`us5-routing-surfaces-census-S340.md:76-83`, que classifica
`escalation_signals.py` como DONA local, não leitora dos pins). Consequência
para quem fechar a AC-13: ligar telemetria SEM equalizar o predicado fecharia
o AC sobre um detector que não implementa o piso que ele diz cobrir.

A SEGUNDA lacuna é a TELEMETRIA. A entrada do detector são eventos
`action: "agent_spawn"`, emitidos por `.claude/hooks/audit_log.py:668` — hook
registrado em `.claude/settings.json` no evento **`PostToolUse` com matcher
`Agent`**, isto é, apenas no rail direto do `Agent` tool. O rail do Workflow
não passa por ali, e portanto não produz a linha que o detector leria.
Medição (janela FECHADA no passado, para não citar total que decai): no
corpus de audit deste projeto, entre `2026-09-04T02:00:00Z` e
`2026-09-04T03:00:00Z` — janela que contém os dois spawns desta célula
(02:42:26.156Z e 02:42:28.070Z) — há **0 eventos `agent_spawn`**, contra
**942 eventos de outras ações** na MESMA janela (`tool_call_lifecycle_recorded`,
`output_scan_finding*`, `prompt_submitted`, `session_stop`, …): o log estava
vivo e recebendo, logo o zero é ausência de emissão, não log parado.
Controle positivo no OUTRO rail: as três sondas DIRETAS da S340 (`Agent`
tool), cujo despacho é o mesmo arquétipo, emitiram três linhas —
`2026-09-03T02:38:10Z` `code-reviewer`/`claude-fable-5`, `02:38:44Z`
`qa-architect`/`claude-sonnet-4-6`, `02:38:49Z`
`general-purpose`/`claude-fable-5-1[1m]` — com o campo `model` PREENCHIDO.
Ou seja: existe um detector que ACUSARIA estas duas células, e ele tem insumo
no rail que emite telemetria; estas duas células — as do **Workflow** —
caíram fora dela. (As duas células do rail NATIVO, medidas na subseção
seguinte, caíram DENTRO: emitiram `agent_spawn` e o detector, rodado sobre
elas, acusa as duas.) Cobrir o
piso de verdade pede as duas coisas — a telemetria E a paridade de predicado
(5 papéis, membresia em `VETO_FLOOR_ALLOWED`).

**Nas duas células do Workflow o gate de spawn não RODOU — e dizer que ele
«passou verde» seria falso**
(rail r1 P2). Estas duas sondas foram despachadas por `agent()` de Workflow, o
rail que `CLAUDE.md:99` documenta como fora do `check_agent_spawn`
(«`agent()` de Workflow segue NÃO passando pelo `check_agent_spawn`», probe
`wf_d7af49d9`). Portanto o que esta célula mede é um rail SEM gate nenhum, o
que é uma afirmação MAIS forte sobre o piso, não menos: o override abaixo do
piso nem sequer encontrou uma superfície de decisão.

> **Uma inferência que este documento NÃO faz** (rail do land, P2 — a versão
> anterior desta seção a fazia): «o transcript da sonda não tem `PreToolUse`,
> logo o gate não rodou» é **inválido**. O `PreToolUse:Agent` dispara no
> transcript do CHAMADOR, antes de o filho existir; o transcript do FILHO
> nunca o contém. Controle positivo medido no land, sobre os três filhos da
> sonda DIRETA da S340 (via `Agent` tool, cujo gate comprovadamente roda):
> `agent-aus4-gp-*`, `agent-aus4-ic-qa-*` e `agent-aus4-veto-cr-*` têm todos
> `PreToolUse == 0` e `SubagentStart == 2` — **a mesma forma** dos dois
> transcripts desta célula. A forma do transcript do filho não distingue
> spawn gateado de spawn não-gateado, e por isso não é evidência de nada
> aqui. O que sustenta a frase acima é `CLAUDE.md:99` e o probe
> `wf_d7af49d9`, não os transcripts destas sondas.

### Célula Agent tool (rail nativo, S343 2026-09-04T07:36Z)

A mesma pergunta pela OUTRA via — e é aqui que o `check_agent_spawn` RODA.
Dois spawns pelo `Agent` tool com `subagent_type: code-reviewer` (o mesmo
arquétipo VETO) e `model:` explícito abaixo do piso, despachados pelo assento
CEO desta sessão. Tarefa trivial de sonda.

| célula | `model:` declarado | pin do arquétipo | dentro do piso? | modelo SERVIDO (`message.model`) | o gate PreToolUse rodou? |
|---|---|---|---|---|---|
| nativa A | `sonnet` | `claude-fable-5` | **NÃO** | `claude-sonnet-5` | **SIM** — e não bloqueou |
| nativa B | `haiku` | `claude-fable-5` | **NÃO** | `claude-haiku-4-5-20251001` | **SIM** — e não bloqueou |

Servido, cru (primeira entrada de assistente de cada transcript, campos
elididos):

```json
// <session-dir>/subagents/agent-aus4-agenttool-sonnet-ae01f11a06201d7e.jsonl
{"timestamp": "2026-09-04T07:36:05.461Z", "message": {"id": "msg_011Cei1ojUDrcVkkH4WPgJnz", "type": "message", "role": "assistant", "model": "claude-sonnet-5"}}
// <session-dir>/subagents/agent-aus4-agenttool-haiku-708e44268f6bfb5a.jsonl
{"timestamp": "2026-09-04T07:36:20.380Z", "message": {"id": "msg_011Cei1qRmf7Y1mnhaujSHWC", "type": "message", "role": "assistant", "model": "claude-haiku-4-5-20251001"}}
```

Em cada transcript o conjunto de `message.model` sobre TODAS as entradas de
assistente é singleton (3 e 2 entradas de assistente, respectivamente). O
PEDIDO está no sidecar homônimo — e note que nesta via o arquétipo viaja em
`customAgentType`, não em `agentType` (que aqui é o NOME do spawn):

```json
// <session-dir>/subagents/agent-aus4-agenttool-sonnet-ae01f11a06201d7e.meta.json
{"agentType":"us4-agenttool-sonnet","spawnDepth":0,"model":"sonnet","customAgentType":"code-reviewer", ...}
// <session-dir>/subagents/agent-aus4-agenttool-haiku-708e44268f6bfb5a.meta.json
{"agentType":"us4-agenttool-haiku","spawnDepth":0,"model":"haiku","customAgentType":"code-reviewer", ...}
```

**O gate RODOU — e isso é medido, não inferido.** Na janela FECHADA
`2026-09-04T07:30:00Z–07:37:00Z` (fechada no passado de propósito: nenhuma
contagem deste documento pode crescer depois de escrita) o audit deste
projeto tem **56 eventos**, entre eles **OITO emitidos pelo próprio
`check_agent_spawn.py`**, dois de cada uma de quatro ações:
`model_routing_advised` (:746), `model_routing_enforced` (:483),
`spawn_confidence_advisory` (:956) e `spawn_file_assignment_recorded`
(:2196). Os dois `model_routing_enforced`, às `07:35:50Z` e `07:36:13Z`
(2 s ANTES de cada spawn), dizem verbatim
`{"archetype": "code-reviewer", "mode": "enforcing", "recommended_model": "claude-fable-5", "killswitch_armed": false, "decision": "enforce_telemetry"}`:
o gate recomendou o PISO e emitiu telemetria, enquanto o servido foi
`claude-sonnet-5`. **O que a célula PROVA é que nenhum caminho do hook
compara o modelo PEDIDO contra `VETO_FLOOR_ALLOWED`** — e não que o harness
tenha sonegado o campo (rail de cura r1 v4, P2: a distinção é load-bearing).
O que se lê no código: `main()` repassa a `decide()` apenas
`description`, `prompt`, `subagent_type` e `names_regex`
(`check_agent_spawn.py:3124-3148`), embora o adaptador preserve o
`tool_input` INTEIRO (`_lib/adapters/claude.py:78-87`);
`metadata.get("model")` dentro de `decide()` é o frontmatter; e o próprio
hook registra o bloco de tier como DEFERIDO
(`check_agent_spawn.py:372-381`, «with no requested-model input, a block
would be theater»). Se o `model:` chega ou não ao `tool_input` do PreToolUse
segue NÃO MEDIDO (residual nomeado) — a implementação ausente está
estabelecida sem essa medição.

**No PostToolUse o modelo PEDIDO chega — e o detector do piso acusa as duas.**
Os dois `agent_spawn` (emissor `.claude/hooks/audit_log.py:668`) saíram com
`"rail": "native"`, `"subagent_type": "code-reviewer"`, `"dispatch_mode": "native"` e
`"model": "sonnet"` / `"model": "haiku"` — o ALIAS PEDIDO. Que ele veio
OBSERVADO do `tool_response` (`_extract_model`, `audit_log.py:641`) e não da
tabela de política é demonstrável: o fallback de política para `code-reviewer`
é `claude-opus-5` (`audit_log.py:924`), que não é o que a linha traz.
Rodando `detect_veto_non_opus()` sobre exatamente esses dois eventos, ele
devolve DOIS achados `severity: "high"` —
`{"role": "code-reviewer", "model": "sonnet", "expected_prefix": "claude-opus-|claude-fable-"}`
e o mesmo com `"haiku"`. Duas notas sobre o que isso significa: (a) o
predicado julgou o ALIAS DECLARADO, não o id SERVIDO — acertou aqui, mas o
que ele cobre é a declaração; (b) por ser teste de PREFIXO
(`ceo-escalation-detector.py:97`), um override benigno declarado como alias
(`model: opus`) também não casaria `claude-opus-` — leitura do predicado no
código, não medição desta noite.

**A resposta de governança, nas duas vias:** o modelo servido seguiu o
override explícito abaixo do piso nos DOIS rails. No rail nativo o gate
PreToolUse RODOU e nenhum caminho dele comparou o modelo PEDIDO; no rail do
Workflow não há gate nenhum (`CLAUDE.md:99`). O piso VETO tem TRÊS pernas, e
nenhuma delas para um override por chamada: (i) o arquivo do arquétipo —
`veto_floor: true` + `model:` em `.claude/agents/<tipo>.md`, com a lista
`VETO_FLOOR_ALLOWED` em `_lib/agent_frontmatter.py:135-141`; (ii) o BLOQUEIO
em runtime da INTEGRIDADE desse arquivo (`check_agent_spawn.py:2425-2455`),
que é gate de verdade mas guarda a demoção do frontmatter, não a chamada; e
(iii) `detect_veto_non_opus()` POST-HOC sobre telemetria `agent_spawn`
(`ceo-escalation-detector.py:382-410`, registrado em `:449-455`). A cobertura
da perna (iii), MEDIDA: **nula no rail Workflow** (0 eventos
`agent_spawn` na janela fechada 02:00–03:00Z, abaixo) e **presente no rail
nativo** — as duas linhas existem e o detector acusa as duas, julgando o
alias DECLARADO. Bloqueio em runtime do modelo SERVIDO: nenhum, em nenhuma
das vias.

> **O piso ficar fora do gate é OMISSÃO DE IMPLEMENTAÇÃO, não uma pergunta
> aberta sobre o harness** (correção S343: a versão anterior desta página
> tratava o ponto inteiro como questão de substrato em aberto, o que
> sub-declarava o achado). O `model` do `Agent` tool é superfície de seleção
> **documentada por este repo**: `ADR-149:107-110` arrola «the Agent tool
> `model` parameter» entre as superfícies em que o harness pode selecionar
> um id, e `PLAN-186:55` (fato 7) registra o override do `Agent` tool como
> **honrado desde 2.1.237**. Sobre uma superfície declarada e honrada, o que
> o gate faz hoje é validar o ARQUIVO do arquétipo — `metadata.get("model")`
> é o frontmatter, pela própria nota do hook — e NENHUM caminho de
> `check_agent_spawn` compara o modelo despachado contra `VETO_FLOOR_ALLOWED`.
> O piso simplesmente não é verificado ali. Some-se que a tabela de campos
> citada como base do deferimento (`SPEC/v1/hook-io.schema.md:55`) se rotula
> **«non-exhaustive»** e que o adaptador não descarta campo algum —
> `.claude/hooks/_lib/adapters/claude.py` guarda o `tool_input` INTEIRO em
> `NormalizedEvent.tool_input`, derivando `subagent_type`/`file_path`/etc.
> apenas como conveniências: **se** o harness puser `model` no `tool_input`,
> o hook já o tem em mãos. O que segue NÃO medido é estreito e está nos
> residuais — se aquele campo chega ao PreToolUse (sonda: spawn direto com
> `model:` explícito imprimindo as CHAVES do `tool_input`; nenhum spawn foi
> feito por este land). O que a sonda decide é ONDE a cura mora — comparação
> de uma linha no código deste repo, se o campo chega; insumo novo do harness
> (ou o validador do lado do Workflow, que não depende dele), se não chega —,
> **não SE o piso está desguarnecido**: isso está estabelecido e não depende
> dela. Enquanto a sonda não roda, «omissão de implementação» é afirmação
> sobre a COBERTURA do piso pelo gate, não sobre a camada em que o conserto
> vai cair (rail de cura r1, P2).

**Abertura que o rail achou e que fica NOMEADA:** no sítio do Workflow o
`agentType` e o `model` estão AMBOS presentes ANTES do despacho (ver o trecho
transcrito acima). Um validador do lado do Workflow — na mesma camada em que
as 4 skills já validam a gramática ADR-191 pré-despacho — é possível e não
depende do harness expor nada. Do lado do `Agent` tool o que existe é uma
pergunta ABERTA, não uma impossibilidade (rail do land r1, P2): se o `model:`
chega ao `tool_input` do PreToolUse segue NÃO MEDIDO nesta página, e o
adaptador preserva o dict inteiro — chamar o caminho nativo de inviável
afirmaria justamente o que aqui está declarado como não medido, e poderia
desviar a cura do hook nativo sem razão. A diferença entre os dois rails é
que no Workflow a pergunta nem se coloca.

**E o detector post-hoc da AC-13, COMO ESPECIFICADO, também não cobre o piso**
(rail r2 P1 — achado que derruba a versão anterior desta página). O invariante
que a AC-13 declarava é «modelo SERVIDO por label == modelo DECLARADO no
sítio». Aplicado a estas duas células, ele é **mal-definido, e as duas leituras
possíveis são ambas defeito** (rail r3 P2):

- **Literal, sem canonicalização:** o sítio declara o ALIAS (`sonnet`,
  `haiku`) e o transcript registra o ID (`claude-sonnet-5`,
  `claude-haiku-4-5-20251001`). `servido == declarado` é **FALSO** — o
  detector acusaria, mas pela razão ERRADA (uso de alias), e acusaria
  igualmente todo spawn benigno que declare alias. Ruído, não sinal.
- **Com canonicalização alias→id** (a leitura útil): `servido == declarado`
  é **VERDADEIRO** nas duas células — o detector sai VERDE exatamente sobre o
  furo que esta página documenta.

Ou seja: sem normalização o predicado é inútil por falso-positivo; com
normalização ele é cego a este furo. Chamar esta célula de «caso positivo do
detector» seria falso nas duas leituras.

Cobrir o piso exige, na AC-13, **normalização alias→id declarada** MAIS um
**SEGUNDO predicado**: *arquétipo com `veto_floor: true` ⇒ modelo servido ∈
`VETO_FLOOR_ALLOWED`*. Os dois predicados respondem perguntas distintas e
precisam de vereditos distintos: «roteamento inesperado» (servido ≠ declarado,
pós-normalização) e «override abaixo do piso» (servido == declarado, mas
servido ∉ piso num arquétipo VETO). Como a conclusão de um plano é gatilhada
pelos seus critérios formais (`PLAN-SCHEMA.md:410-411`), fechar a AC-13 com o
predicado ÚNICO permitiria aceitar exatamente estas células. **Este pack NÃO
edita o texto da AC-13** (S343, cura C1): aquela linha é superfície do pack da
própria AC-13, e dois patches ancorando a mesma linha colidem no land — a
exigência fica registrada aqui e na nota da AC-10, como requisito NOMEADO
para quem fechar a AC-13. Enquanto esse predicado não existir, o piso VETO
não tem GATE nenhum; e o detector que mais perto chega —
`detect_veto_non_opus` (Signal 5) — acusaria estas células, mas só enxerga o
rail que emite `agent_spawn` e cobre 2 dos 5 papéis VETO por prefixo, não o
piso por membresia.

Consequência operacional que fica, com o escopo CERTO (rail r1 P2): migrar os
pins continua sendo alavanca real de custo E de postura de segurança **no caso
DEFAULT** — sem `model:` explícito, o pin É o modelo servido (medido na S340),
logo trocá-lo troca o que um arquétipo VETO efetivamente roda. O que esta
célula prova é mais estreito e mais duro: o pin **não é suficiente** como
enforcement, porque quem passa `model:` o contorna. Default forte, garantia
nenhuma. E o rail MITIGADO (persona VETO injetada em `general-purpose`) segue
fora do piso por construção, agora acompanhado do rail com override explícito.

### Residuais desta célula

- As DUAS vias têm célula medida (Workflow acima, `Agent` tool na subseção
  própria). O que segue não medido é o COMPORTAMENTO do gate sob um pedido
  que ele pudesse ver: nas células nativas ele rodou, recomendou o piso
  (`claude-fable-5`) e emitiu telemetria, mas nenhum caminho dele comparou
  despachado contra `VETO_FLOOR_ALLOWED` — não existe execução observada de
  um bloco de piso porque esse bloco não existe.
- O 2º predicado da AC-13 (VETO ⇒ servido ∈ `VETO_FLOOR_ALLOWED`) e a
  normalização alias→id ficam NOMEADOS aqui e na nota da AC-10, **mas o texto
  formal da AC-13 não foi emendado por este pack** (C1: linha de outro pack) e
  o INSTRUMENTO não existe: enquanto nenhum dos dois chegar, o instrumento da
  AC-13 segue cego a este furo. Estas duas células são o caso de teste que o
  predicado novo tem de acusar.
- **DUAS lacunas do lado do detector, e nenhuma foi fechada aqui** (S343):
  (i) TELEMETRIA — `detect_veto_non_opus` lê `agent_spawn`, que só o rail do
  `Agent` tool emite (medição acima; no rail nativo a perna post-hoc
  FUNCIONA — o detector rodado sobre as duas linhas acusa as duas —, o que
  torna a lacuna especificamente do rail Workflow); o lado barato é emitir a mesma
  telemetria no rail do Workflow, onde `agentType` e `model` estão ambos no
  sítio da chamada, ou validar ali, na camada em que as skills de Workflow já
  checam a gramática ADR-191 pré-despacho. (ii) PARIDADE DE PREDICADO — 2 dos
  5 papéis VETO e teste por prefixo em vez de membresia em
  `VETO_FLOOR_ALLOWED` (aceita `claude-fable-5-1`). NÃO foi medido o que o
  detector faria sobre uma linha emitida pelo rail do Workflow, e este pack
  não altera nem o detector nem a emissão.
- **Não foi medido se o `tool_input` do PreToolUse de um spawn `Agent` com
  `model:` explícito CONTÉM esse campo.** A tabela do SPEC que o código cita
  é declaradamente não-exaustiva e o adaptador preserva o dict inteiro, logo
  «o payload não carrega o modelo» é premissa herdada, não medição — e o
  PostToolUse do MESMO spawn carrega o alias pedido (medido na subseção
  nativa), o que torna a premissa menos plausível sem derrubá-la: são
  payloads distintos. Sonda que falta: um spawn direto com `model:` abaixo do
  piso imprimindo as CHAVES do `tool_input`. Ela decide ONDE a cura mora —
  uma comparação de uma linha neste repo se o campo chega, insumo novo do
  harness se não —, **não SE o piso está desguarnecido**, que já está
  estabelecido pelo parágrafo de escopo acima e não depende dela.
- Não foi medido se um `model:` INVÁLIDO (fora de `AVAILABLE_MODELS`) cai
  silenciosamente na herança (a nota da ADR-149 afirma essa semântica; segue
  não verificada aqui).

### Fontes desta célula

- Transcripts (rail Workflow): `<session-dir>/subagents/workflows/wf_dc95ca8a-fc2/agent-af1621b0e2266543e.jsonl`
  (célula `sonnet`) e `.../agent-a7ef0363d48a1bd99.jsonl` (célula `haiku`);
  sidecares `<agent-id>.meta.json` homônimos (chave de atribuição).
- Transcripts (rail nativo `Agent` tool): `<session-dir>/subagents/agent-aus4-agenttool-sonnet-ae01f11a06201d7e.jsonl`
  e `<session-dir>/subagents/agent-aus4-agenttool-haiku-708e44268f6bfb5a.jsonl`,
  com os sidecares `.meta.json` homônimos (`customAgentType: code-reviewer`).
- Telemetria: eventos `agent_spawn`, `model_routing_advised`,
  `model_routing_enforced`, `spawn_confidence_advisory` e
  `spawn_file_assignment_recorded` do audit deste projeto na janela
  `2026-09-04T07:30:00Z–07:37:00Z` (fechada).
- Piso: `.claude/hooks/_lib/agent_frontmatter.py` (`VETO_FLOOR_ALLOWED`,
  `:135-141`); pin: `.claude/agents/code-reviewer.md`;
  gate: `.claude/hooks/check_agent_spawn.py:372-381`, `:483`, `:956`, `:2196`;
  emissor da telemetria: `.claude/hooks/audit_log.py:641`, `:668`, `:924`;
  detector: `.claude/scripts/ceo-escalation-detector.py:92`, `:97`,
  `:382-410`, `:449-455`.
