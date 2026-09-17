# Estudo S354 — consumo de tokens do Claude Code sob o framework

**Data:** 2026-09-16 → 17 · **Sessão:** S354 · **Autor:** CEO (Fable 5.1) · **Status:** lane 01 (insumo) e lane 02 (parecer Codex) salvas; primeira leitura do ledger feita (§2b); estudo NÃO ratificado
**Insumo:** `01-work-order-2026-09-16.md` — ordem de trabalho do Owner, v2.0, salva verbatim.
**Lane 02:** `02-codex-opinion.md` — parecer independente do Codex (17/09), produzido a partir de `prompts/02-codex-brief.md`; avaliado em §5.
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

## 2. Fatos verificados contra ESTE repo (S354, CLI 2.1.274, HEAD `ffb4ff1c` → `3647e643`)

Cada fato aponta o arquivo. Três linhas (F1, F2, F5) foram CORRIGIDAS pela lane 02 — a
correção está inline e o detalhe em §5; a versão original fica no histórico git.

| # | Fato | Onde | Toca |
|---|---|---|---|
| F1 | A superfície de boot Gate-1/2 é um prefixo fixo relido em TODO turno. Bytes: `CLAUDE.md` 39.984 · `PROTOCOL.md` 27.021 · `.claude/team.md` 48.765 · `.claude/frontend-team.md` 11.687 · skill `ceo-orchestration` 63.725 = **191.182 bytes**; mais `MEMORY.md` 17.807. O piso re-pago por compactação medido na S322 (**F ≈ 97,3k**, spread 51,7 %, n=41 sessões mas **n=1 por compactação**) é um bloco OPACO: a decomposição system prompt × tool defs × `CLAUDE.md` está ABERTA (§F.8), e **F NÃO subiu quando o `CLAUDE.md` cresceu 48,8 %** (§F.6, n=13). *(corrigido S354: os bytes são reais; a parcela deles no piso é hipótese a medir, não causa demonstrada.)* | `.claude/plans/PLAN-179/w0-measurement.md` §F.6, §F.8; instrumento `PLAN-179/w0/gateboot_repay.py` | D1, L1, L3 |
| F2 | `CLAUDE_CODE_SUBAGENT_MODEL=inherit` é fixado DE PROPÓSITO por `route.py` para que o frontmatter governe — um valor concreto sobreporia `model:` explícito. Desde a CLI 2.1.251 a precedência documentada é: modelo por chamada > frontmatter > env; `inherit` equivale a indefinido. O veredito «`opts.model` do Workflow inerte» (W0a, PLAN-134) está marcado **RE-VERIFY** em PLAN-163 G16 e continua aberto. O modelo REALMENTE executado se lê no JSONL (`message.model`) — ver M1. *(corrigido S354: mecanismo; a conclusão «subagentes rodam no modelo mais caro» segue verdadeira, mas por POLÍTICA S339, não por herança.)* | `.claude/hooks/route.py:24-28`; `PLAN-163-substrate-uplift.md:101` | D5, L2 |
| F3 | Já existe um derivador que torna `model:` explícito em todo `agent()` das 4 skills Workflow — **artefato de estudo, NÃO aplicado** (S339). | `.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py` | L2 |
| F4 | `.claude/agents/`: 9 de 13 definições têm `model:` — 5 em `claude-fable-5` (geração anterior), 4 em `claude-sonnet-4-6` (duas gerações atrás), 4 sem `model:`. Nenhuma em Haiku 4.5 ou Sonnet 5. | `ls .claude/agents/*.md`; fonte única de IDs = ADR-149 | D5, L2, L8 |
| F5 | O ledger a partir dos JSONL JÁ EXISTE: `ceo-cost-transcripts.py` (02/09, PLAN-186 W0) lê `message.usage` de assento e subagentes, deduplica por `message.id`, separa papéis, aplica `cost-table.yaml`; integrado a `ceo-cost.py` e `budget-summary.py`. A statusline já lê a quota nativa `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`. Os demais instrumentos (`/audit-tokens`, `/agent-budget`, `cost_envelope.py`, `tier_policy`) leem o audit-log e são advisory. **Continua verdadeiro:** nenhum liga consumo a quota, nenhum fecha loop (bloqueia, roteia ou agenda). *(corrigido S354: a v1 dizia que nada lia o JSONL — errado.)* | `.claude/scripts/ceo-cost-transcripts.py`; `.claude/scripts/statusline-ceo.py:21-40` | P1, P2 |
| F6 | ~100 registrações `"command"` em `.claude/settings.json` (48 hooks wired / 50 registrações de evento, CLAUDE.md §1). Cada PreToolUse/PostToolUse pode injetar stdout/`additionalContext` no histórico; **o custo em tokens por turno dos hooks nunca foi medido**. | `.claude/settings.json`; `_lib/tokens.py` (estimador) | P1, P2, L3 |
| F7 | O loop `HEARTBEAT da esteira noturna (PLAN-01…)` NÃO é deste repo (planos aqui são `PLAN-1NN`); pertence a outro projeto no mesmo `CLAUDE_CONFIG_DIR`. L7 aplica-se lá; o PADRÃO (arquivo de estado + acordar-por-mudança + sessão nova + modelo barato) pode nascer aqui como template. | — | D4, L7, P4 |
| F8 | D2/L5 já tiveram estudo: PLAN-172 (`reviewed`) mediu **59 % de tempo morto** no run que desfinanciou a velocidade; PLAN-187 (teto de paralelismo) foi ABANDONADO em 06/09. O S339 `01-academia.md` §1.1 registra a doutrina Anthropic (≈ 4× para agentes, ≈ 15× para multi-agente, ambos versus chat simples; «quando NÃO usar») e marca como `[LACUNA]` a heurística «a tarefa vale o multiplicador?». | `PLAN-172-…md`; `PLAN-187-…md`; `docs/research/s339-orchestrator-study/01-academia.md` | D2, L5, L6 |

## 2b. Primeira leitura do ledger (S354, 17/09, coletor existente, janela `--since 14d` ≈ 2026-09-03 → 09-17 UTC)

Instrumento: `python3 .claude/scripts/ceo-cost-transcripts.py --since 14d --by role,model`
(6,4 s; 98 transcripts de assento + 1.638 de subagente; 63.470 turnos únicos após dedup de
51.992 duplicatas; 217 turnos `<synthetic>` sem preço). Saída bruta no scratchpad da sessão;
números abaixo são API-equivalentes pela `cost-table.yaml` do repo.

| papel | turnos | cache read | cache write | output | USD | contexto médio/turno |
|---|---|---|---|---|---|---|
| assento (sessão principal) | 4.755 | 2,48 bi (TTL 1 h) | 46 mi | 8,3 mi | 1.964 | **≈ 521k** |
| subagentes | 58.715 | 15,55 bi (TTL 5 min) | 387 mi | 9,4 mi | 10.396 | **≈ 265k** |
| total | 63.470 | 18,03 bi | 433 mi | 17,8 mi | 12.360 | 284k |

- **M1 — o custo está nos subagentes Opus 5.** 82,6 % do custo (US$ 10.206; 56.959 turnos) é
  `subagent | claude-opus-5`; o assento em Fable 5.1 é 15,0 %. Consequência direta da regra
  S339 «Fable verifica, Opus 5 executa» — não de herança de modelo. Inverte o 71 %-no-assento
  que o S339 mediu para 03/08 → 02/09: são dois regimes, não uma contradição.
- **M2 — subagente não é trabalhador de contexto pequeno.** Contexto médio por turno ≈ 265k;
  ≈ 36 turnos por transcript (58.715 / 1.638). O assento roda a ≈ 521k por turno — confirma a
  ordem de grandeza «≈ 600k» do insumo por outra via.
- **M3 — output é 2 % do custo dos subagentes.** Decomposição Opus 5 subagente: cache read
  ≈ 75 % (15,5 bi × 0,50/M), cache write de 5 min ≈ 23 % (387 mi × 6,25/M), output ≈ 2 %.
- **M4 — 75 % dos 14 dias caiu em 3 dias.** 04, 05 e 06/09 somam US$ 9.333 (noites
  autônomas S345–S347: lands livres, 504 achados de rail, 11 % produto, zero canônicos
  assináveis). Depois das regras v2.1 da S348 (codex só em bytes canônicos, WIP ≤ 3) e do
  freeze de release, o custo diário caiu para US$ 300–430 (08–10/09) e US$ 17–107 (13–17/09):
  **a mudança de modelo de operação já cortou o consumo em ~10× antes de qualquer mudança
  no framework.**
- **M5 — máquina inteira, mesma janela:** este repo 18,5 bi tokens (output 0,10 %, 284k por
  turno); o outro projeto grande do Owner 22,7 bi (output 0,33 %, 250k por turno); o terceiro
  é desprezível. **O framework em dogfood é o pior em output por token: ≈ 1.000 tokens
  processados por token gerado**, contra ≈ 300 no projeto vizinho e ≈ 283 na média do insumo.
- **M6 — nada configurado, defaults do harness em vigor:** nenhum `promptCacheTtl`,
  `subagentPromptCacheTtl`, `autoCompactWindow`, `omitClaudeMd` ou `bashOutputMaxChars` nas
  settings do projeto ou do usuário. Bate com o medido: subagentes escrevem cache de 5 min,
  assento de 1 h.
- **M7 — os 13 controles nativos da tabela do Codex existem como strings no binário 2.1.274**
  (`omitClaudeMd`, `autoCompactWindow`, `promptCacheTtl`, `subagentPromptCacheTtl`,
  `bashOutputMaxChars`, `workflowSizeGuideline`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`,
  `updatedToolOutput`, `maxTurns`…). Existência confirmada; comportamento a testar.
- **M8 — o prefixo que o framework injeta por spawn é PEQUENO.** `inject-agent-context.sh
  --mode=inline "Code Reviewer"` devolve 9.793 bytes (≈ 2,5k tokens) com `## SKILL CONTENT`;
  com o slug em vez do nome de exibição, 4.625 bytes (persona genérica). Logo os ≈ 265k por
  turno dos subagentes NÃO vêm do spawn: vêm do prefixo do harness (system prompt + tool
  defs + `CLAUDE.md`, o bloco opaco de F1) e das leituras acumuladas ao longo de ≈ 36 turnos.
  Decompor isso é o item 3 do §3.

## 3. Como o estudo deve ser montado (proposta v2, pendente do Owner)

Ordem revista após a lane 02 (§5). Literatura ORIENTA cada experimento; não é etapa separada.

1. **Validar o coletor e definir a métrica-alvo.** Auditar amostra do ledger (dedup, papéis,
   `<synthetic>`, modelos, TTL); definir «entrega aprovada» (land/PR aceito, teste verde,
   veredito de rail) e medir **quota por entrega aprovada**, não output/total.
2. **Reconciliar coletor × preços × quota observada.** Correlacionar passivamente
   `rate_limits.{five_hour,seven_day}` da statusline com o ledger; se insuficiente, o
   experimento de uma conta / blocos comparáveis descrito pelo Codex em D.1.
3. **Testar contexto** (P1): controles nativos de M7 em 2.1.274, um a um, com controle;
   saídas de tools (`bashOutputMaxChars`, `updatedToolOutput`), continuidade por tarefa
   (handoff em arquivo), `subagentPromptCacheTtl` 5 min → 1 h (M3: 23 % do custo dos
   subagentes é escrita de cache de 5 min — o TTL de 1 h custa 2× por escrita mas evita
   reescrever a cada espera > 5 min; só o teste decide).
4. **Comparar roteamento e concorrência** (P3, P5): 1/3/7 agentes e modelos permitidos no
   MESMO conjunto de tarefas, mesmo orçamento, mesmos testes e revisão; escolher por
   entrega aceita e tempo total. R1 fixa o perímetro financeiro.
5. **Dimensionar scheduler e capacidade paga** (P5, P6, P7) com a demanda que sobrar.

Formato de entrega: um arquivo por lane neste diretório + síntese `00-synthesis.md`, no molde do
`orchestrator-operating-model-S339.md`. Waves que APLICAM algo (agents `model:`, TTL, hooks,
boot menor) viram plano próprio com debate L3 — o estudo em si é livre (zero canônico).

## 4. Regras que já valem para este estudo

- Claim medida = data + substrato; medições de junho/2026 são de outra geração de modelo.
- Cure a CLASSE: o insumo enumera 7 diagnósticos; o estudo nomeia a classe de cada um.
- Nada de rotação automática de contas em nenhuma lane (R3); nada que toque dinheiro sai de Opus/Fable (R1).
- O estudo NÃO edita Gate-1 (`CLAUDE.md`, `PROTOCOL.md`, `team.md`, skill CEO) — proposta de
  encolhimento vai para a síntese e passa por cerimônia.
- Nomes de outros projetos da máquina NÃO entram neste diretório público; agregados só.

## 5. Lane 02 — parecer do Codex (17/09): o que muda na leitura

Codex leu o repositório e fontes primárias; cada afirmação factual sobre o repo foi
re-verificada pelo CEO nesta sessão (arquivo + linha em §2). Saldo: **3 correções aceitas,
4 refinamentos aceitos, 2 pontos mantidos, 1 divergência declarada.**

**Correções aceitas (mudam §2):**
- **F5 estava errada em parte** — o coletor de JSONL existe desde 02/09 e a statusline já lê a
  quota nativa. Meu «nenhum lê o JSONL» era desatualizado.
- **F1 superestimava** — 97k é um piso opaco, n=1 por compactação, e F não subiu com o
  `CLAUDE.md` +48,8 %. «O framework fixa ~100k» excede a evidência.
- **F2 errava o mecanismo** — `inherit` é a escolha deliberada do `route.py` para o frontmatter
  governar; a precedência documentada desde 2.1.251 é por chamada > frontmatter > env.

**Refinamentos aceitos:**
- «15×» é versus chat simples (4× para agentes), não versus agente único, nem medição deste
  framework. «96,3 % cache read» não é «96,3 % desperdício»; `input_tokens` não mede todo o
  conteúdo novo (parte entra em `cache_creation`).
- «2 a 3 agentes» é HIPÓTESE a testar (Kim et al. 2026: depende da estrutura da tarefa), não
  regra. Cortar 1/3 do consumo não garante zero bloqueio: sob consumo constante, 1 h de
  saldo vira 1,5 h. A relação quota × tokens não tem fórmula pública — só medição.
- Métrica-alvo correta: **trabalho aprovado por unidade de quota**, não output/total.
- Ordem das lanes: coletor e métrica primeiro; literatura orienta, não encerra.

**Mantidos (com a evidência de §2b):**
- Sessões longas com ≈ 521k por turno e loop de fundo em sessão viva seguem as alavancas de
  menor esforço; M4 mostra que mudar o MODO DE OPERAÇÃO (v2.1) foi a maior economia até aqui.
- Os 191 KB de boot são bytes reais e relidos em todo turno; o que fica aberto é a parcela
  deles no piso — item 3 do §3, não causa afirmada.

**Divergência declarada:** Codex prefere «continuidade delimitada por tarefa» a «sessão nova
sempre». Neste repo a continuidade já vive em arquivo (memória, planos, ledgers), então a regra
operacional «uma sessão por tarefa» é a forma concreta da mesma ideia; a diferença é de
redação, e o teste do item 3 decide se algum handoff se perde.

**O que o Codex trouxe e ninguém tinha:** a tabela de controles nativos com nome exato e fonte
(M7 confirmou existência no binário); a estatística de admissão de trabalho (VTC, HiveMind)
como base do scheduler; a observação de que compressão por consulta pode DESTRUIR reuso de
cache (CAPC) — um hook local de sumarização pode custar mais do que economiza.
