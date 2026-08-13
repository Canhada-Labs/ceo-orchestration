# PLAN-178 W1.4 — Memo: nested subagents + agent teams (go/no-go)

> Estudo read-only (S305). Evidência primária desta sessão + código;
> referências externas em `research-S305.md` linhas 2 e 15.

## Nested subagents (até 3 níveis)

**Evidência local:** o campo `spawnDepth` JÁ existe no `.meta.json` de
cada agente (probe W1.2 desta sessão: `{model, name, spawnDepth,
taskKind}`) — a telemetria de profundidade vem de graça. O controle
correspondente do framework, porém, está desarmado:
`CEO_SPAWN_DEPTH_GUARD` (rail 2, check_agent_spawn.py:1822-1833) é
advisory e estava FORA da lista original do C5 (achado Critic-B,
unseen 3 — corrigido: entrou na tabela C5).

**Veredito: NO-GO para uso, GO para instrumentação.** Condições de
reabertura: (a) `CEO_SPAWN_DEPTH_GUARD` armado com taxa-base medida
(gate measure-first do C5); (b) um caso de uso real que fan-out de
1 nível não resolva — hoje não existe nenhum no repo (fan-outs são
rasos por desenho, e o MAST diz que coordenação é onde quebra);
(c) o protocolo de spawn definido para o nível 2+ (quem injeta
AGENT PROFILE/SKILL/FILE ASSIGNMENT no spawn do spawn? O gap do rail
Workflow mostra o custo de deixar isso implícito); (d) **wiring
metadata→guard como pré-requisito EXPLÍCITO (codex r2 P2-2):** o
`_spawn_depth` do guard lê só o marcador cooperativo de prompt +
`CEO_SPAWN_DEPTH` — nesting NATIVO não carrega nenhum dos dois sinais,
então armar o guard, sozinho, NÃO controla depth-2 nativo; antes de
(a) contar como controle, o guard precisa consumir o `spawnDepth` do
`.meta.json` (ou o harness precisa propagar o sinal cooperativo).

## Agent teams / SendMessage full-mesh

**Evidência local desta própria sessão (S305):** o padrão
spawn→idle→SendMessage→entrega funcionou, mas com fricção
documentável: 3 dos 4 auditores W0 sinalizaram idle SEM entregar o
relatório — a entrega só veio após cobrança explícita por SendMessage.
Num mesh sem orquestrador central, essa classe (idle-sem-entrega)
vira perda silenciosa de resultado — exatamente FM-2.4 (retenção de
informação) da taxonomia que acabamos de auditar. Somam-se: lição
S284 (SendMessage ressuscita 2ª instância ⇒ clobber) e MAST
(coordenação desestruturada = classe dominante de falha).

**Veredito: NO-GO (reafirma a exclusão de escopo).** O padrão
hub-and-spoke atual (CEO orquestra, agentes entregam por arquivo
próprio + FILE ASSIGNMENT) é estritamente mais auditável. Reabertura
só se surgir necessidade real de coordenação peer-to-peer que o hub
não atenda — nenhuma identificada.

## Disposição (AC-5)

- Nested: instrumentar (C5: depth-guard na tabela) e parar.
- Teams: exclusão mantida; nenhuma ação.
- Ambos re-avaliáveis via substrate-watch quando o harness mudar o
  shape dessas features (mesma vigilância do W3/dreaming).
