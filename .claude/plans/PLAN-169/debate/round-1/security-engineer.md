---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (core archetype, team.md:202,532 — VETO em auth/token/input handling)
generated_at: 2026-08-08T13:11:53Z
---

## Verdict

ADJUST — o desenho de segurança está na direção certa (refuse default, lado
de envio interceptável, live-fire antes de doc), mas quatro superfícies novas
gateiam decisão autônoma em estado local não autenticado e o veículo de
execução do próprio plano (Workflow) é a superfície menos verificada da janela.

## Summary (≤ 3 bullets)

- O plano fecha o passado com evidência boa e escolhe as alavancas certas no
  cross-session (`crossSessionInbound: "refuse"` é de fato a única alavanca
  fail-closed soberana ao repo; o lado de ENVIO é de fato o interceptável).
- A fraqueza é sistemática, não pontual: **quatro** mecanismos novos
  (quota-resume, gate de night-mode, ack de overhead, allowlist de peers)
  tomam decisão a partir de estado local **não assinado e gravável pelo
  próprio agente guardado** — a mesma classe, quatro vezes.
- O ponto cego mais caro é de sequenciamento: o Owner mandou executar via
  Workflow (plano `:24`), e o probe que descobre se `agent()` de Workflow
  passa pelo gate de spawn está no **W4** — depois de W0/W1/W2/W3 já terem
  rodado por esse caminho.

## Risks

**R-SEC1 — CRITICAL — Workflow é o veículo de execução E a superfície não
verificada; o probe que a testa vem depois do uso.**
`research-claude-updates.md:195-197` registra que **não está documentado** que
`agent()` de Workflow dispare `SubagentStart`, e `:199` que subagents de
workflow rodam **sempre em `acceptEdits` com edits auto-aprovados**,
independentemente do modo da sessão. `:201` lista duas fugas de sandbox de
workflow em três semanas (2.1.223 `import()`, 2.1.216 symlink em `.claude`).
Verifiquei que `check_agent_spawn.py` não lê `isolation` (grep `isolation` →
0 hits) — spawn remoto também não é modelado. O plano coloca esse probe em
`W4.2.0(b)` e a execução autônoma via Workflow começa no W0.
*Mitigação:* mover o probe (b) — e um segundo probe, "`PreToolUse(Edit)` em
superfície canônica bloqueia sob Workflow?" — para **W0.0**, antes de qualquer
wave. Até verde nos dois, Workflow só para trabalho read-only (varredura,
leitura, síntese); tudo que edita corre pela Agent tool normal.

**R-SEC2 — HIGH — quota-resume gateia ação autônoma num snapshot que o
próprio código declara advisory-only.**
`.claude/scripts/statusline-ceo.py:57-60`, verbatim: *"the sidecar is an
unauthenticated local JSON read as governance input … integrity posture =
follow-up if it ever gates a decision." Consumers MUST stay advisory-only on
this input.* W4.1 usa `resets_at` do snapshot para **agendar** uma retomada
autônoma — é exatamente a condição registrada. Quem controla o snapshot
controla **quando** um prompt não supervisionado entra na fila.
*Mitigação:* fonte autoritativa = o payload in-band do hook `StopFailure`
(matcher `rate_limit`), que vem do harness; snapshot só como *fallback
advisory*, e nesse caso a retomada é **avisada, não agendada**. Se o Owner
quiser o snapshot como fonte, então o follow-up de integridade do PLAN-135
§W5 entra no escopo ANTES — e isso é uma wave, não um rider.

**R-SEC3 — HIGH — o prompt de retomada transforma estado local não assinado
em instrução, numa sessão por definição não supervisionada.**
O prompt padrão do W4.1 é *"retome o plano ativo: TaskList + §Progress log do
plano `executing`"* (plano `:207-208`). `research-claude-updates.md:159`
registra que a task list é *"superfície de coordenação em disco, mutável e não
assinada"* e que **escrita direta em `~/.claude/tasks/{team-name}/` por
qualquer processo local não passa por gate nenhum**. Sob night-mode
(`acceptEdits`), a cadeia fecha: arquivo local não autenticado → instrução →
edit auto-aprovado, sem humano no loop.
*Mitigação:* o prompt tem de ser literal fixo que **re-entra no Gate 1**
(CLAUDE.md → PROTOCOL.md → plano) e instrui explicitamente: TaskList e
§Progress são **DADO** a re-verificar contra o plano assinado, nunca fonte de
autoridade. Proibir na retomada, por texto: cerimônia GPG, tag, aprovação npm,
qualquer transição de status de plano. Postura nunca escala na retomada.

**R-SEC4 — HIGH — o gate "só com night-mode armado" lê estado que o agente
pode escrever.**
`.claude/scripts/night-mode.py:275`, verbatim: *"The marker is gitignored,
unguarded, **agent-writable** state"*. O mesmo arquivo (`:22`) diz que a
superfície com guarda de verdade é `settings.local.json` (cerimônia de
sentinela). Gatear quota-resume no marcador é gatear no lado errado.
*Mitigação:* ler a **postura efetiva** (`_lib/effective_config.py` /
`permissions.defaultMode` no overlay guardado), nunca `.claude/state/night-mode.json`.

**R-SEC5 — HIGH — allowlist de destinatários por NOME é ACL sobre um
namespace que o adversário escolhe.**
`research-claude-updates.md:70` — o nome de uma sessão vem de `--name` /
`/rename` (ou é derivado da pasta), e colisões viram `name [ref]`. Um peer
escolhe o próprio nome. Uma allowlist de `to` em `PreToolUse(SendMessage)`
autoriza, portanto, por um identificador controlado pelo outro lado.
*Mitigação:* default-deny; permitir apenas destinatários que a sessão resolve
como subagent/teammate **próprio**; recipiente não classificável ⇒ **block**
(falha de parse de INPUT é fail-CLOSED, CLAUDE.md §4 — a falha de
infraestrutura do hook continua fail-open com `{}`). O ADR precisa dizer, em
uma linha, que **nome não é autenticação**.

**R-SEC6 — HIGH — W2.4 troca um ack efêmero por um interruptor persistido que
o próprio guardado pode acionar.**
Hoje `CEO_OVERHEAD_ACK` só existe como prefixo de um comando Bash: escopo de
um subprocess, sem persistência (`check_anti_ceo_overhead.py:733`,
`:657-660`). A proposta cria sentinela em disco com TTL — um arquivo que
desarma um guard de governança e que o modelo escreve com uma chamada Bash,
valendo depois para Edit/Write. Isso inverte a relação guard/guardado.
*Mitigação (preferida):* consertar o **predicado**, não criar canal — o
defeito real do ledger (C.3) é o guard disparar em fan-out de investigação
read-only; `PostToolBatch` (já no W4.4) faz um batch de 5 Reads contar como
um evento. *Se* o sentinela ficar: TTL ≤ a janela atual, **single-use**
(consumido na primeira supressão), ligado ao `session_id`, checagem de
symlink/traversal espelhando `_sidecar_override_safe`
(`statusline-ceo.py:139-170`), e evento de auditoria **na escrita e no
consumo** — não só no consumo.

**R-SEC7 — MEDIUM — o gate de envio precisa valer em profundidade.**
`research-claude-updates.md:133`: `SendMessage` e as tools de task estão
**sempre** disponíveis a um teammate, mesmo com `tools` restrito na definição.
Um arquétipo `Read, Grep, Glob, Bash` mantém canal de mensageria.
*Mitigação:* o hook tem de disparar para envio originado por subagent/teammate
(probe), e o evento HMAC registra o **agente originador**, não só a sessão.

**R-SEC8 — MEDIUM — a sanitização do `PROTOCOL_SOURCE` está desenhada como
blocklist, e a rejeição é silenciosa.**
O filtro atual (`scripts/upgrade.sh:1565-1577`) aceita qualquer string
não-vazia sem `{{`. O plano acrescenta rejeição de control chars — ainda
blocklist. E o efeito de rejeitar é cair no D3, que termina em
`_ptr_psource="$SOURCE_DIR"` (`:1592-1594`): um install-state envenenado
passa a **re-apontar o pointer para o checkout de hoje a cada upgrade**, sem
ninguém saber.
*Mitigação:* allowlist positiva (ASCII imprimível, sem control chars, sem
newline, charset de path) + **WARNING nomeando a chave rejeitada** no stdout
do upgrade + caso novo no `test-protocol-pointer-render.sh` que asserta o
WARNING, não só o fallback. A postura fail-toward-preservation da atribuição
guardada (`:1598-1599` → `if ! _ptr_full=…`) está certa e deve ficar.

**R-SEC9 — MEDIUM — eventos HMAC novos entram fail-closed-vazios se só
"whitelistarem campos".**
`.claude/hooks/_lib/audit_emit.py:1689-1693` fixa a invariante: todo membro de
`_KNOWN_ACTIONS` é **exatamente um** de (a) branch de dispatch com scrub, (b)
`_RESERVED_ACTIONS`, (c) `_EMIT_GENERIC_PASSTHROUGH`; quem não é nenhum cai no
default-deny e **todos os kwargs são descartados**. Um evento registrado que
emite vazio é a família registered-vacuous da S292.
*Mitigação:* checklist explícito por evento novo — `_KNOWN_ACTIONS` + branch
de scrub próprio + linha em `SPEC/v1/audit-log.schema.md` com ADR governante
+ teste que asserta **os campos no evento gravado** (não que `emit` foi
chamado). E: nome de peer é texto livre escolhido pelo adversário indo para o
log que `skill-health`/`audit-tokens` renderizam — cap de tamanho + charset
antes de emitir. Int com unidade no nome (float descarta o evento) já está
correto no plano.

**R-SEC10 — MEDIUM — o protocolo do W5 monta, de propósito, a cadeia de
laundering completa.**
O plano prevê fleet com `--settings` sobrepondo a postura para aceitar inbound
(`:250-251`). Aceitar inbound **e** `acceptEdits` na mesma sessão é
exatamente o que o resto do W4.2 existe para impedir.
*Mitigação:* sessões de experimento em worktrees dedicados, sem superfície
canônica no escopo, sem acesso a chave GPG, e proibição escrita de
`inbound=accept` simultâneo a `acceptEdits`/`bypassPermissions`/night-mode.

**R-SEC11 — LOW/MEDIUM — `Agent(param:value)` é fail-closed real, mas não é
soberano.** `CLAUDE_CODE_SUBAGENT_MODEL` sobrepõe roteamento de modelo em
workflow (`research-claude-updates.md:191`), e o substrato está movendo config
sensível de escopo repo → user/managed (`:300`).
*Mitigação:* registrar a env no inventário + check, e declarar a limitação de
soberania de escopo no ADR do W4.3 em vez de vender enforcement absoluto.

**R-SEC12 — LOW — env nova sem inventário vira drift.** `CEO_QUOTA_RESUME` não
existe em `.claude/scripts/env-inventory.json` (onde `CEO_OVERHEAD_ACK:1872` e
`CEO_SOTA_DISABLE:2613` estão) ⇒ a dimensão (vi) do `nightly-hygiene` acusa.

## Must-fix (blocking)

1. **Mover para W0.0, antes de qualquer execução via Workflow:** probe
   `SubagentStart` dispara para `agent()` de Workflow? + probe "canonical-edit
   é bloqueado sob Workflow?". Enquanto os dois não estiverem verdes por
   evidência registrada, Workflow fica restrito a trabalho read-only.
   (R-SEC1)
2. **quota-resume não pode gatear em `statusline-snapshot.json`.** Fonte
   autoritativa = payload do hook `StopFailure(rate_limit)`; snapshot só
   fallback advisory e, nesse modo, avisa em vez de agendar. (R-SEC2)
3. **Prompt de retomada literal, re-entrando no Gate 1**, tratando
   TaskList/§Progress como DADO, com proibição textual de cerimônia/tag/npm/
   transição de status e sem escalada de postura. (R-SEC3)
4. **Gate de postura lê a postura efetiva**, não `.claude/state/night-mode.json`
   (agent-writable por declaração do próprio script, `night-mode.py:275`).
   (R-SEC4)
5. **Allowlist do `PreToolUse(SendMessage)` é default-deny e não confia em
   nome:** só destinatários resolvidos como subagent/teammate próprio;
   não-classificável ⇒ block (input fail-closed); infra do hook falhando ⇒
   `{}` fail-open. ADR registra que nome não autentica. (R-SEC5, R-SEC7)
6. **W2.4: cura pelo predicado/`PostToolBatch` como caminho primário.** Se o
   sentinela persistido for mantido, ele nasce com TTL ≤ janela atual,
   single-use, ligado ao `session_id`, com guarda de symlink/traversal e
   evento na escrita **e** no consumo. (R-SEC6)
7. **Sanitizador de `PROTOCOL_SOURCE` = allowlist positiva + WARNING nomeando
   a chave rejeitada**, com o WARNING assertado em teste (silêncio aqui é
   mudança silenciosa de propriedade do pointer). (R-SEC8)
8. **Checklist de evento HMAC novo** (`_KNOWN_ACTIONS` + scrub branch + linha
   no SPEC + teste que asserta campos gravados) e **cap/charset no nome de
   peer** antes da emissão. (R-SEC9)
9. **Protocolo do W5 proíbe `inbound=accept` junto com acceptEdits/bypass/
   night-mode**, e isola as sessões do experimento (worktree dedicado, sem
   superfície canônica, sem GPG). (R-SEC10)
10. **Registrar `CEO_QUOTA_RESUME` (e qualquer env nova do W4) em
    `.claude/scripts/env-inventory.json`** no mesmo commit que a introduz.
    (R-SEC12)

## Nice-to-have (advisory)

1. `sandbox.network.allowUnixSockets` / `allowAllUnixSockets`
   (`research-claude-updates.md:247`) como defesa em profundidade sobre o
   inbox socket para Bash sandboxed — barato, e ataca o vetor own-child pelo
   lado do SO em vez do lado da política.
2. Teto de cadeia de retomadas (contador com máximo por plano + evento de
   auditoria ao atingir), para que "estourou → retoma → estoura" não vire loop
   não supervisionado que queima quota.
3. Mensagem de erro do injector fail-closed (W2.3) **listando os nomes
   válidos do SKILL MAP**: hoje operadores já contornam montando prompt à mão
   (ledger C.1); um erro sem a lista empurra para o bypass em vez do conserto.
4. Deny declarativo para `Agent(isolation:remote)` enquanto o gate de spawn
   não modelar a classe (`check_agent_spawn.py` não lê `isolation`).
5. Doutrina do peer no ADR nomeando explicitamente: nenhum peer pode
   satisfazer o predicado "aprovação do Owner", e campos de proveniência do
   sentinel (`CEO_SENTINEL_UNLOCK`, anchor SHA) nunca são populados a partir
   de texto de peer.
6. **OQ-2, do assento de segurança:** night-mode armado **+** opt-in
   explícito; nunca sempre-on. E se o live-fire do AC-4 não acontecer na
   janela, o default é **off** com rótulo experimental — não "on com doc
   cautelosa".
7. **OQ-4:** guard canônico, não checksum. Um checksum verificado pelo próprio
   script que decide o gate é a mesma família do registered-vacuous.

## Unseen by the original plan

1. **Falta o probe que decide se a tese do W4.2 se sustenta:
   `crossSessionInbound: "refuse"` também recusa own-child?**
   `research-claude-updates.md:80` diz que a exceção own-child vale *"quando
   nenhum `crossSessionInbound` se aplica"* — a leitura natural é que `refuse`
   fecha também o own-child, mas isso não está afirmado e o plano depende
   disso nos dois sentidos. Se **fechar**: some a oportunidade de hook postar
   resultado estruturado no próprio socket (o plano não registra essa perda).
   Se **não fechar**: `refuse` não é a alavanca soberana que o plano assume, e
   `echo <conteúdo lido de arquivo> | socket` vira um turno novo — escalação
   clássica de prompt-injection, com verificação que **só vale enquanto o
   processo postador vive no macOS e nunca vale em container com PID 1**
   (`:80`). Probe de dois minutos, alavancagem igual à do probe (a).
2. **Falta o probe de proveniência:** o que o log HMAC registra **hoje** de um
   turno nascido de inbound. O plano descreve o buraco em prosa mas não mede o
   estado atual — e essa medição é o que permite a frase honesta no ADR.
   Corolário que o plano não tira: **com `inbound != refuse`, a claim de
   auditabilidade do README fica DEGRADADA** (o log registra o efeito, não a
   origem) e precisa de escopo explícito, exatamente como o "no speed claim".
3. **A auditoria P0 do W4.4 é muito mais barata do que o plano sugere — e por
   isso não deve ser adiada.** Das 48 registrações em `.claude/settings.json`,
   apenas **duas** têm matcher hifenizado (`:291` e `:472`, ambas
   `mcp__codex__codex|mcp__codex__codex-reply`) e há **zero** condições `if:`
   no arquivo. O universo real da mudança 2.1.195 é 2 registrações — e são
   justamente as do rail de review cross-model. O que precisa de desenho não é
   a varredura, é o **controle positivo recorrente em CI**: a semântica de
   matcher mudou 3× em 6 semanas, então auditoria one-shot re-apodrece.
4. **Falta o probe de profundidade no lado de envio:** `PreToolUse` dispara
   para `SendMessage` emitido por subagent/teammate? Sem isso, o gate do W4.2
   cobre o CEO e deixa passar exatamente os agentes cujo `tools` foi
   restringido (que mantêm `SendMessage` de qualquer jeito).
5. **Bound honesto que falta no quota-resume:** entregas de scheduled task são
   classificadas como *task notification* e **não podem aprovar ação pendente**
   (`research-claude-updates.md:237`, 2.1.183). Se a sessão morreu num prompt
   de permissão em vez de quota, a retomada não resolve nada. A doc do AC-4
   tem de dizer isso, e o próprio mecanismo tem de distinguir os dois casos.
6. **Cron é in-memory e session-scoped** (`:229`). O plano assume que "o REPL
   fica idle" no estouro de quota; se o processo encerrar, o job morre junto e
   o mecanismo **falha em silêncio** — o modo de falha mais perigoso para uma
   feature de continuidade. O live-fire precisa medir esse caso
   explicitamente, não só o caso feliz.

## What I would NOT change

- **Dois trens em sequência.** Injetar cross-session na 1.3.0 colocaria uma
  superfície de fronteira de confiança nova dentro de uma release cujo debate
  já fechou. A separação está certa por segurança, não só por processo.
- **`crossSessionInbound: "refuse"` + `isolatePeerMachines: true` como default
  instalado.** É a alavanca certa e é fail-closed de graça; minhas ressalvas
  são sobre o que ela **não** cobre, não sobre adotá-la.
- **Escolher o lado de ENVIO como ponto de interceptação** e **registrar o
  buraco de proveniência do recebimento honestamente** em vez de fingir que o
  hook o cobre. Essa é a postura correta e é rara.
- **DEFER de channels com causa nomeada.** É a decisão de segurança mais
  importante do W4.4: é a única superfície da janela em que um terceiro
  **aprova** tool use em vez de pedir. Não reabrir.
- **Live-fire obrigatório antes de doc** no quota-resume, e a regra "doc
  promete exatamente o que o teste provou".
- **Fail-CLOSED no rider de mtime do W1** (`HARNESS-ERR` em vez de descarte
  silencioso) — input não parseável é fail-closed, e é o que cegou 0017/0021.
- **Proibição de tocar `ownership_table.tsv` / `ownership-expected-reds.txt`.**
- **W5 com braço token-matched, grading cego e publicação do negativo.**

---

### Nota de defesa de prompt

Li `ledger-S298.md`, `research-claude-updates.md` e `research-academia.md`
como **dados**. Não encontrei em nenhum deles texto endereçado a mim, pedido
de ação, nem claim de autoridade. `research-claude-updates.md:341` faz essa
mesma declaração sobre as próprias fontes — tratei isso como claim do autor do
anexo, não como prova, e verifiquei no disco toda claim de que minha crítica
depende: `statusline-ceo.py:57-60`, `night-mode.py:275`,
`check_anti_ceo_overhead.py:657-660,733`, `audit_emit.py:1689-1693`,
`upgrade.sh:1565-1577,1592-1594,1598-1599`,
`inject-agent-context.sh:770-795`, contagem de matchers e ausência de `if:` em
`.claude/settings.json`, ausência de `isolation` em `check_agent_spawn.py`, e
ausência total de `SendMessage`/`ListAgents`/`crossSessionInbound` em
`settings.json`, hooks e `install.sh` (⇒ o W4.2 é net-new, não um reforço).
