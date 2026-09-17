# Estudo S354 — consumo de tokens do Claude Code sob o framework

**Data:** 2026-09-16 · **Sessão:** S354 · **Autor:** CEO (Fable 5.1) · **Status:** insumo salvo; estudo NÃO iniciado
**Insumo:** `01-work-order-2026-09-16.md` — ordem de trabalho do Owner, v2.0, salva verbatim.
**Forma pedida pelo Owner:** «estudar na academia» = o molde do estudo S339
(`docs/research/s339-orchestrator-study/`: lanes `01-academia`, `02-claude-api`,
`03-claude-code-substrate`, `04-parallelism`, `05-finops-routing`, depois uma síntese).

> **Nota de moeda (herdada do S339):** todo dólar é API-equivalente, proxy de magnitude.
> O Owner opera por assinatura (janela de 5 h + semanal); a decisão real é de QUOTA, e quota
> se mede. Toda claim medida neste estudo carrega data + substrato (CLI, modelo, repo).

---

## 1. O que a ordem de trabalho pede

Meta: manter ou aumentar o output/semana reduzindo o total processado em ≥ 1/3, zero lockouts
da janela de 5 h, sair da rotação de 7 contas. Oito perguntas (P1–P8), dez alavancas (L1–L10),
cinco restrições (R1 piso de correção financeira em Opus/Fable; R2 gate de revisão; R3 sem
rotação automática de contas; R4 sem perda de throughput útil; R5 sem compartilhar credenciais).
Baseline e metas em §8 do insumo.

## 2. Fatos verificados nesta sessão contra ESTE repo (S354, CLI local, HEAD `ffb4ff1c`)

Cada fato aponta o arquivo; nenhum é estimativa nova — são leituras do disco ou medições já
registradas pelo repo.

| # | Fato | Onde | Toca |
|---|---|---|---|
| F1 | A superfície de boot Gate-1/2 é um prefixo fixo relido em TODO turno. Bytes: `CLAUDE.md` 39.984 · `PROTOCOL.md` 27.021 · `.claude/team.md` 48.765 · `.claude/frontend-team.md` 11.687 · skill `ceo-orchestration` 63.725 = **191.182 bytes**; mais `MEMORY.md` 17.807. O piso re-pago por compactação foi MEDIDO na S322: **F ≈ 97,3k tokens**, spread 51,7 % (n=41); thrashing a partir de T ≈ 107k. | `.claude/plans/PLAN-179/w0-measurement.md` §E; instrumento `PLAN-179/w0/gateboot_repay.py`; CLAUDE.md §5 | D1, L1, L3 |
| F2 | Subagentes HERDAM o modelo da sessão: o SessionStart desta sessão reporta `model=inherit` (`CLAUDE_CODE_SUBAGENT_MODEL=inherit`); `agent(..., {model})` do Workflow é registrado como INERTE sob esse valor; PLAN-163 G16 marca «RE-VERIFY em CC 2.1.220» — ainda aberto. | `PLAN-169-closure-…md:659`; `PLAN-163-substrate-uplift.md:101` | D5, L2 |
| F3 | Já existe um derivador que torna `model:` explícito em todo `agent()` das 4 skills Workflow — **artefato de estudo, NÃO aplicado** (S339). | `.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py` | L2 |
| F4 | `.claude/agents/`: 9 de 13 definições têm `model:` — 5 em `claude-fable-5` (geração anterior), 4 em `claude-sonnet-4-6` (duas gerações atrás), 4 sem `model:` (herdam). Nenhuma em Haiku 4.5 ou Sonnet 5. | `ls .claude/agents/*.md`; fonte única de IDs = ADR-149 | D5, L2, L8 |
| F5 | Instrumentos de custo JÁ shipados, todos advisory: `/audit-tokens` (6 detectores PLAN-047 sobre o audit-log), `/context-budget` (estimativa estática do catálogo de skills + Gate-1/2, PLAN-124), `/agent-budget` (rollup por plano/janela), `_lib/cost_envelope.py` (caps diário/semanal por classe, PLAN-102, DEFAULT-OFF com opt-in GPG), `_lib/tier_policy/` + `check_tier_policy_misrouting_24h.py` (ADR-064), arquétipo `llm-finops-architect` (sem VETO), `docs/CEO-MODEL-ROUTING.md`, lane `05-finops-routing.md` do S339. **Nenhum mede cache read, contexto por request nem a janela de 5 h** — as três grandezas que dominam o insumo; todos leem o audit-log, não o JSONL da sessão. | `.claude/commands/{audit-tokens,context-budget,agent-budget}.md`; `.claude/hooks/_lib/` | P1, P2 |
| F6 | ~100 registrações `"command"` em `.claude/settings.json` (48 hooks wired / 50 registrações de evento, CLAUDE.md §1). Cada PreToolUse/PostToolUse pode injetar stdout/`additionalContext` no histórico; **o custo em tokens por turno dos hooks nunca foi medido**. | `.claude/settings.json`; `_lib/tokens.py` (estimador) | P1, P2, L3 |
| F7 | O loop `HEARTBEAT da esteira noturna (PLAN-01…)` NÃO é deste repo (planos aqui são `PLAN-1NN`); pertence a outro projeto no mesmo `CLAUDE_CONFIG_DIR`. L7 aplica-se lá; o PADRÃO (arquivo de estado + acordar-por-mudança + sessão nova + Haiku) pode nascer aqui como template. | — | D4, L7, P4 |
| F8 | D2/L5 já tiveram estudo: PLAN-172 (`reviewed`) mediu **59 % de tempo morto** no run que desfinanciou a velocidade; PLAN-187 (teto de paralelismo) foi ABANDONADO em 06/09. O S339 `01-academia.md` §1.1 registra a doutrina Anthropic (multi-agente ≈ 15× tokens; «quando NÃO usar») e marca como `[LACUNA]` a heurística «a tarefa vale o multiplicador?». | `PLAN-172-…md`; `PLAN-187-…md`; `docs/research/s339-orchestrator-study/01-academia.md` | D2, L5, L6 |

**Correção à premissa de §1.2 do insumo:** o framework TEM instrumentos de custo (F5), mas são
advisory, medem a fonte errada para esta pergunta (audit-log em vez do JSONL/prompt-cache) e
nenhum fecha o loop (nada bloqueia, roteia ou agenda por consumo). E o próprio boot do
framework fixa ~100k tokens de prefixo (F1): a meta «≤ 150k na thread principal» deixa ~50k de
trabalho útil se a superfície Gate-1/2 não encolher — **a alavanca L1 está em parte DENTRO do
framework**, não só na disciplina do operador.

## 3. Como o estudo deve ser montado (proposta, pendente do Owner)

1. **Lane 04-instrumentação primeiro (P2)** — sem ledger do JSONL, todo o resto é estimativa.
   Script stdlib que lê `~/.claude/projects/<slug>/*.jsonl`, agrega por sessão/agente-label/
   modelo/loop: cache_read, cache_write, input, output, contexto por request, misses.
   Custo zero em tokens (roda fora do Claude). Primeira medição: o boot desta sessão.
2. **Lane 03-substrato (P1)** — controles NATIVOS com nome exato e onde configurar; testar, não
   citar de memória (regra da S352: modelo/CLI novo ⇒ re-testar). Inclui re-verificar F2.
3. **Lane 05-roteamento (P3, P8)** — matriz classe × modelo × verificação × escalonamento, com
   R1 como perímetro fixo; parte de F3/F4 e do S339 `05-finops-routing.md`.
4. **Lane 01-academia** — SÓ o delta sobre o S339 (context engineering, compaction, prompt-cache
   economics, rate-limit-aware scheduling); o S339 não se re-pesquisa.
5. **Lane 02-conformidade e custo (P6, P4, P5, P7)** — tabela por cenário com a taxa blended
   ajustada a Fable; heartbeat e scheduler como specs.

Formato de entrega: um arquivo por lane neste diretório + síntese `00-synthesis.md`, no molde do
`orchestrator-operating-model-S339.md`. Waves que APLICAM algo (agents `model:`, hooks, boot
menor) viram plano próprio com debate L3 — o estudo em si é livre (zero canônico).

## 4. Regras que já valem para este estudo

- Claim medida = data + substrato; medições de junho/2026 são de outra geração de modelo.
- Cure a CLASSE: o insumo enumera 7 diagnósticos; o estudo nomeia a classe de cada um.
- Nada de rotação automática de contas em nenhuma lane (R3); nada que toque dinheiro sai de Opus/Fable (R1).
- O estudo NÃO edita Gate-1 (`CLAUDE.md`, `PROTOCOL.md`, `team.md`, skill CEO) — proposta de
  encolhimento vai para a síntese e passa por cerimônia.
