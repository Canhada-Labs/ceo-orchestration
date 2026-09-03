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
