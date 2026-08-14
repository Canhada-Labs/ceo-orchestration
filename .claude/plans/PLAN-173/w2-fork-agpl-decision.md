# PLAN-173 W2-A — Decisão: fork do Warp (AGPL) como base de cockpit

| Campo | Valor |
|---|---|
| Plano | PLAN-173 (`.claude/plans/PLAN-173-ceo-cockpit-warp-study.md`) |
| Item | W2 — "Fork AGPL: documentar como viável-mas-ADIADO" |
| Data da decisão | 2026-08-14 |
| Veredito | **VIÁVEL-MAS-ADIADO** (default do plano confirmado; ver §3) |
| Durabilidade | Este registro vale MESMO se o kill-gate E0b (PLAN-172) matar o PLAN-173 inteiro — ele documenta *por que não forkamos*, e as razões de custo/licença independem do destino do cockpit (ver §3.4) |
| AC do plano (§5) | "um leitor externo consegue reproduzir a decisão sem esta conversa" — este documento é autocontido; toda proveniência está em §5 |

---

## 1. A pergunta

**Fork do cliente open-source do Warp (AGPL v3) como base de um "CEO
cockpit" — superfície visual para o estado de governança do framework
(plans, fila de aprovação, verditos, saúde do audit log HMAC, fleet
view) — é viável?**

Contexto mínimo: o Warp abriu o código do cliente em 2026-04-30
(repo `warpdotdev/warp`), sob licença **dupla** — MIT para o framework
de UI (`warpui_core`/`warpui`) e **AGPL v3 para o resto** do cliente.
A nuvem de IA deles (agentes, Warp Drive) permanece proprietária e não
self-hostável. *(Proveniência: PLAN-173 §0 "Fatos de base — verificados
S302". Não re-verificado externamente nesta execução — este item é
decisão documental pura, sem leitura de código de terceiros; a
re-verificação do estado upstream é pré-condição de reabertura R4,
§3.3.)*

A alternativa concorrente — e o motivo de a pergunta ser respondível
hoje sem experimento — é a **rota MCP-primeiro (W1)**, cujo degrau de
infraestrutura **já está shipado neste repo** (ver §2.4).

## 2. Análise de licença

### 2.1 Obrigações do AGPL v3: fork interno vs distribuído

O AGPL v3 é o GPL v3 mais a cláusula de rede (§13). As obrigações
dependem inteiramente de *como* o fork é usado:

**(a) Fork interno, não distribuído, sem serviço de rede a terceiros
(o cenário realista aqui: o Owner rodando o cockpit na própria
máquina).** Modificação privada não é "convey" nos termos do GPL/AGPL
— as obrigações de disponibilizar fonte (§6) só disparam na
transmissão a terceiros, e a cláusula de rede (§13) só dispara quando
**usuários remotos interagem com a versão modificada através de uma
rede**. Um cockpit local, single-user, não aciona nenhuma das duas.
Obrigação prática residual: preservar avisos de licença/copyright no
código e não usar a marca (2.3).

**(b) Fork distribuído (publicar o cockpit como parte da proposta
open-source do projeto — o cenário provável, dado que o framework é
público).** Aí o copyleft integral aplica: o trabalho derivado inteiro
permanece AGPL v3, com Corresponding Source disponível a todo
recipiente (e, via §13, a todo usuário remoto se alguém hospedar o
cockpit como serviço); avisos preservados; Installation Information
quando aplicável. Para um projeto free/open sem intenção de vender ou
hospedar (PLAN-173 §2, não-escopo), isso é **compatível** — oneroso em
processo, não em princípio.

### 2.2 Compatibilidade com este repo (licença VERIFICADA nesta execução)

**O `ceo-orchestration` é MIT** — verificado nesta execução: `head -30
LICENSE` ⇒ "MIT License / Copyright (c) 2026 Canhada Labs". Isso fixa
a direção da compatibilidade:

- **MIT → AGPL: permitido.** Código MIT deste repo pode ser
  incorporado num fork AGPL (a compatibilidade é unidirecional; o
  combinado fica AGPL).
- **AGPL → MIT: NÃO.** Uma linha de código AGPL dentro do
  `ceo-orchestration` contaminaria o trabalho combinado — o repo não
  poderia mais ser oferecido sob MIT puro. Daí a condição (c) do
  PLAN-173 §0: **repo separado, sempre** — o fork nunca entra na
  árvore do framework.
- **Fronteira limpa por construção:** a integração entre um eventual
  cockpit AGPL e o framework MIT se dá por **protocolo** (MCP
  JSON-RPC sobre stdio/HTTP, processos separados) — interoperabilidade
  arm's-length, não obra derivada. A arquitetura MCP-primeiro já
  implementa exatamente essa fronteira (§2.4), o que significa que a
  separação de licenças sai de graça se o fork um dia acontecer.

### 2.3 Marca

A licença AGPL não concede direito algum sobre a marca "Warp".
Condição (b) do PLAN-173 §0: **zero uso da marca** — nome, logo e
trade dress próprios em qualquer fork, desde o commit 1.

### 2.4 Custo real de manutenção do fork (medições desta execução)

Este é o argumento decisivo — a licença é administrável; o custo, não:

1. **Linguagem/toolchain alheios ao repo:** o cliente do Warp é um
   terminal GUI em Rust. Este repo tem **0 arquivos `.rs` em 4.079
   arquivos rastreados** (medido: `git ls-files | grep -c '\.rs$'` ⇒ 0;
   `git ls-files | wc -l` ⇒ 4079, nesta execução) e um contrato de
   runtime **Python ≥3.9 stdlib-only** (CLAUDE.md §4, enforçado por
   `.claude/scripts/check-stdlib-only.py`). Um fork introduziria uma
   segunda base de código numa linguagem que o projeto não usa em
   lugar nenhum.
2. **Bus factor 1:** limitação honesta declarada (CLAUDE.md §5,
   "Single primary maintainer"). Manter um terminal GUI contra um
   upstream ativo significa carga perpétua de rebase/merge — o pior
   tipo de dívida para um mantenedor único.
3. **O fork não traria a parte valiosa:** a nuvem de IA do Warp é
   proprietária (§1). Forkar entrega o *shell*; tudo que interessa ao
   cockpit (estado de plans, verditos, HMAC) teria de ser construído
   do nosso lado de qualquer forma — e é exatamente o que a rota MCP
   já entrega sem fork.
4. **A rota barata já existe em árvore:** o framework **já shipou** um
   MCP server stdlib (ADR-042, status ACCEPTED, "MCP server stdlib
   shipped"; código em `.claude/scripts/mcp-server/` — `server.py`,
   transportes stdio e HTTP, `auth.py`, `dispatch.py` e **11 módulos
   de handler** contados nesta execução em
   `.claude/scripts/mcp-server/handlers/`, incluindo `plan_status`,
   `get_debate_state`, `audit_query`, `get_audit_log` — precisamente
   as consultas de governança que o W1 pede). O ADR-042-AMEND-1
   declara 33 métodos read-only adicionais com invariante
   `read_only=True` (claim do próprio ADR, não re-contada aqui). O W1
   é, portanto, apontar o Warp *como cliente MCP* para uma superfície
   existente — não construir servidor do zero.

## 3. Decisão: VIÁVEL-MAS-ADIADO

### 3.1 Por que VIÁVEL

- AGPL v3 é compatível com um projeto free/open que não vende nem
  hospeda (PLAN-173 §2); fork interno tem obrigação ~zero, fork
  distribuído tem obrigações conhecidas e cumpríveis (§2.1).
- A contaminação de licença é evitável por construção: repo separado
  (AGPL) + fronteira por protocolo MCP com o framework (MIT) (§2.2).
- Marca é contornável com renome total (§2.3).

### 3.2 Por que ADIADO

- Custo de manutenção desproporcional ao valor incremental: Rust GUI
  vs repo 100% Python stdlib-only, sob bus factor 1 (§2.4, itens 1-2).
- O valor de cockpit é alcançável pelo degrau barato: a superfície MCP
  read-only já shipada (§2.4, item 4) — decisão default do próprio
  PLAN-173 W2: "NÃO forkar enquanto a integração MCP (W1) não esgotar
  o valor".
- O fork não destrava nada que o MCP não destrave hoje, e não traz a
  nuvem de IA do Warp de qualquer forma (§2.4, item 3).

### 3.3 Critérios objetivos de reabertura (TODOS necessários, salvo nota)

A decisão só é revisitada se **R1-R4 forem verdadeiros simultaneamente**,
e a reabertura em si é gated por R5:

- **R1 — Demanda que o MCP comprovadamente não cobre.** O spike W1
  shipou, foi usado em operação real por ≥30 dias, e existem **≥3
  casos de uso registrados** (como findings/issues versionados) que a
  rota MCP não cobre por **limitação de superfície do protocolo** (não
  por handler faltante — handler novo é evolução do MCP, não motivo de
  fork). Enquanto o W1 não esgotar o valor, R1 é falso por definição.
- **R2 — E0b apontou fricção de superfície, não quota.** Ver §3.4.
  Se o E0b (PLAN-172) mostrar tempo-morto dominado por
  quota/capacidade, o PLAN-173 inteiro morre e este item morre junto;
  reabrir o fork exige o resultado complementar — fricção de
  superfície como classe dominante do tempo-morto medido.
- **R3 — Capacidade de manutenção comprovada.** Bus factor >1 para a
  base Rust: um segundo mantenedor ativo com histórico de commits em
  Rust num horizonte de ≥90 dias, OU orçamento explícito e aprovado
  pelo Owner dedicado ao fork. Sem isso, o item 2 de §2.4 permanece
  dispositivo.
- **R4 — Estado upstream re-verificado na data da reabertura.** Os
  fatos de licença deste documento datam de S302 (2026-08-11, PLAN-173
  §0). Reabrir exige re-verificar: (a) o repo `warpdotdev/warp` segue
  público e mantido; (b) o esquema dual MIT/AGPL segue em vigor (uma
  mudança de licença upstream — p.ex. relicenciamento restritivo —
  refaz toda a análise de §2).
- **R5 — Gate procedimental (não é evidência, é processo):** qualquer
  build que mude a identidade do framework ("não é um produto, não tem
  UI" — CLAUDE.md §2) exige **ADR + debate L3+** (PLAN-173, preâmbulo).
  A reabertura entra como plano novo com ADR de visão próprio; nunca
  como emenda silenciosa deste registro.

### 3.4 Amarração ao kill-gate E0b (PLAN-172)

O PLAN-172 define o **E0b** (decomposição do tempo-morto por classe:
`{ci-wait, hold-24h, quota, lag-de-retomada, outro}`) como gate de
financiamento com tabela de decisão pré-registrada — na célula
relevante: *"quota > 40% do morto ⇒ E5 NÃO financiado como desenhado"*
(PLAN-172 §1, tabela E0b). O PLAN-173 §4 herda esse gate como
critério de kill do plano inteiro: *"se o E0b mostrar que o tempo-morto
dominante é quota/capacidade (não fricção de superfície), este plano é
DESCARTADO sem build"*.

Consequência para ESTE registro, nos dois desfechos:

- **E0b mata o PLAN-173** (quota/capacidade dominante): o fork fica
  morto *a fortiori* — se nem o cockpit barato (MCP view) se justifica,
  o caminho caro (fork Rust) muito menos. Este documento permanece
  como o registro de por que a rota fork nunca foi tomada.
- **E0b libera o PLAN-173** (fricção de superfície relevante): a rota
  continua sendo MCP-primeiro (W1, superfície já shipada); o fork só
  reabre por §3.3 completo. R2 fica satisfeito, R1/R3/R4 continuam
  pendentes.

## 4. Registro ADR-style

**Contexto.** O Owner pediu uma visão de cockpit para o estado de
governança do framework (PLAN-173, semente S302). O Warp abriu o
cliente em 2026-04-30 sob dual MIT (`warpui*`) / AGPL v3 (resto), com
a nuvem de IA proprietária. O framework é MIT (verificado no LICENSE),
Python ≥3.9 stdlib-only, bus factor 1, e já shipou um MCP server
stdlib read-only-por-contrato (ADR-042 + AMEND-1) cujos handlers cobrem
as consultas de governança que um cockpit precisa. O PLAN-172 E0b pode
matar o PLAN-173 inteiro se o tempo-morto for dominado por quota.

**Decisão.** Fork do Warp: **VIÁVEL-MAS-ADIADO.** Viável porque o
AGPL v3 é compatível com este projeto free/open desde que (a) o fork
viva em repo separado sob AGPL (nunca dentro do repo MIT), (b) zero
marca "Warp", (c) a integração com o framework se dê por fronteira de
protocolo (MCP). Adiado porque o custo de manter um terminal GUI Rust
(0 arquivos Rust em 4.079 rastreados; mantenedor único) é
desproporcional enquanto a rota MCP-primeiro — já shipada em árvore —
não tiver esgotado o valor. Reabertura somente por R1-R4 (§3.3) sob o
gate procedimental R5 (ADR + debate L3+).

**Consequências.** (1) Nenhum código AGPL entra no `ceo-orchestration`
— a licença MIT do framework fica protegida por regra estrutural, não
por vigilância. (2) O esforço de cockpit se concentra no W1
(cliente MCP sobre superfície existente), com degradação para CLI pura
garantida (PLAN-173 §3). (3) O projeto carrega um registro reproduzível
de por que não forkou — imune ao desfecho do E0b. (4) Se o upstream do
Warp relicenciar ou morrer, nada aqui quebra (dependência zero).

**Revisão.** Este registro é revisado apenas em: (i) veredito do E0b
(qualquer célula da tabela do PLAN-172 §1), (ii) satisfação alegada de
R1-R4, ou (iii) mudança material no licenciamento upstream detectada
por R4. Qualquer revisão que reabra o fork exige plano novo + ADR de
visão + debate L3+ (R5); a revisão que apenas confirma o kill do
PLAN-173 é uma anotação de uma linha neste arquivo, sem cerimônia.

## 5. Proveniência e medições (inputs desta execução, 2026-08-14)

Medições feitas AGORA, nesta execução (read-only, repo em
`/Users/joaocanhada/canhada-labs/ceo-orchestration`):

| Claim | Comando/fonte | Resultado |
|---|---|---|
| Licença do repo é MIT | `head -30 LICENSE` | "MIT License / Copyright (c) 2026 Canhada Labs" |
| Zero Rust no repo | `git ls-files \| grep -c '\.rs$'` | 0 |
| Total de arquivos rastreados | `git ls-files \| wc -l` | 4079 |
| MCP server shipado em árvore | `ls .claude/scripts/mcp-server/` | `server.py`, `stdio_transport.py`, `http_transport.py`, `auth.py`, `dispatch.py`, `rate_limit.py`, `cost.py`, `handlers/`, `tests/`, `start-mcp-server.sh` |
| Handlers de governança | `ls .claude/scripts/mcp-server/handlers/` | 11 módulos além de `__init__.py`: `audit_query`, `get_audit_log`, `get_cost_budget`, `get_debate_state`, `get_skill`, `list_agents`, `list_pitfalls`, `list_skills`, `plan_status`, `server_capabilities`, `spawn_agent` |

Claims citadas de documentos do repo (com fonte; NÃO re-medidas):

- Fatos Warp (data 2026-04-30, dual MIT/AGPL, nuvem proprietária):
  PLAN-173 §0, "verificados S302". Re-verificação externa é a
  pré-condição R4 de reabertura.
- Tabela de decisão E0b (célula "quota > 40%"): PLAN-172
  (`.claude/plans/PLAN-172-honest-speed-e0b-e5-e6.md`, §1).
- Kill do PLAN-173 por quota-dominante: PLAN-173 §4.
- "33 métodos read-only", invariante `read_only=True`:
  ADR-042-AMEND-1 (claim do ADR, v1.29.0).
- Bus factor 1 e "não é um produto, não tem UI": CLAUDE.md §5 e §2.
- Contrato stdlib-only Python ≥3.9: CLAUDE.md §4 +
  `.claude/scripts/check-stdlib-only.py` (existência verificada).
