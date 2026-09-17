# Estudo S354 — consumo de tokens do Claude Code sob o framework

**Data:** 2026-09-16 → 17 · **Sessão:** S354 · **Autor:** CEO (Fable 5.1) · **Status:** lanes 01 (insumo), 02 (parecer Codex) e 03 (auditoria do coletor, v2 após REJECT do revisor cruzado) concluídas; estudo NÃO ratificado como plano
**Insumo:** `01-work-order-2026-09-16.md` — ordem de trabalho do Owner, v2.0, salva verbatim.
**Lane 02:** `02-codex-opinion.md` — parecer independente do Codex (17/09), a partir de `prompts/02-codex-brief.md`; avaliado em §5.
**Lane 03:** `03-collector-audit.md` + `tools/audit_collector.py` — o coletor é APTO; regra exata do `/stats`; escritas grandes decompostas.
**Forma pedida pelo Owner:** «estudar na academia» = o molde do estudo S339
(`docs/research/s339-orchestrator-study/`: lanes `01-academia`, `02-claude-api`,
`03-claude-code-substrate`, `04-parallelism`, `05-finops-routing`, depois uma síntese).

> **Nota de moeda (herdada do S339):** todo dólar é API-equivalente, proxy de magnitude.
> O Owner opera por assinatura (janela de 5 h + semanal); a decisão real é de QUOTA, e quota
> se mede. Toda claim medida neste estudo carrega data + substrato (CLI, modelo, repo) e janela
> ABSOLUTA com limite superior no passado.

---

## 1. O que a ordem de trabalho pede

Meta: manter ou aumentar o output/semana reduzindo o total processado em ≥ 1/3, zero lockouts
da janela de 5 h, sair da rotação de 7 contas. Oito perguntas (P1–P8), dez alavancas (L1–L10),
cinco restrições (R1 piso de correção financeira em Opus/Fable; R2 gate de revisão; R3 sem
rotação automática de contas; R4 sem perda de throughput útil; R5 sem compartilhar credenciais).
Baseline e metas em §8 do insumo.

## 2. Fatos verificados contra ESTE repo (S354, CLI 2.1.274, HEAD `ffb4ff1c` → `efe4c609`)

Cada fato aponta o arquivo. Três linhas (F1, F2, F5) foram CORRIGIDAS pela lane 02 — a
correção está inline e o detalhe em §5; a versão original fica no histórico git.

| # | Fato | Onde | Toca |
|---|---|---|---|
| F1 | A superfície de boot Gate-1/2 é um prefixo fixo relido em TODO turno. Bytes: `CLAUDE.md` 39.984 · `PROTOCOL.md` 27.021 · `.claude/team.md` 48.765 · `.claude/frontend-team.md` 11.687 · skill `ceo-orchestration` 63.725 = **191.182 bytes**; mais `MEMORY.md` 17.807. O piso re-pago por compactação medido na S322 (**F ≈ 97,3k**, spread 51,7 %, n=41 sessões mas **n=1 por compactação**) é um bloco OPACO: a decomposição system prompt × tool defs × `CLAUDE.md` está ABERTA (§F.8), e **F NÃO subiu quando o `CLAUDE.md` cresceu 48,8 %** (§F.6, n=13). *(corrigido S354: os bytes são reais; a parcela deles no piso é hipótese a medir, não causa demonstrada.)* | `.claude/plans/PLAN-179/w0-measurement.md` §F.6, §F.8; instrumento `PLAN-179/w0/gateboot_repay.py` | D1, L1, L3 |
| F2 | `CLAUDE_CODE_SUBAGENT_MODEL=inherit` é fixado DE PROPÓSITO por `route.py` para que o frontmatter governe — um valor concreto sobreporia `model:` explícito. Desde a CLI 2.1.251 a precedência documentada é: modelo por chamada > frontmatter > env; `inherit` equivale a indefinido. O veredito «`opts.model` do Workflow inerte» (W0a, PLAN-134) está marcado **RE-VERIFY** em PLAN-163 G16 e continua aberto. O modelo REALMENTE executado se lê no JSONL (`message.model`) — ver M1. *(corrigido S354: mecanismo; a conclusão «subagentes rodam no modelo mais caro» segue verdadeira, mas por POLÍTICA S339, não por herança.)* | `.claude/hooks/route.py:24-28`; `PLAN-163-substrate-uplift.md:101` | D5, L2 |
| F3 | Já existe um derivador que torna `model:` explícito em todo `agent()` das 4 skills Workflow — **artefato de estudo, NÃO aplicado** (S339). | `.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py` | L2 |
| F4 | `.claude/agents/`: 9 de 13 definições têm `model:` — 5 em `claude-fable-5` (geração anterior), 4 em `claude-sonnet-4-6` (duas gerações atrás), 4 sem `model:`. Nenhuma em Haiku 4.5 ou Sonnet 5. | `ls .claude/agents/*.md`; fonte única de IDs = ADR-149 | D5, L2, L8 |
| F5 | O ledger a partir dos JSONL JÁ EXISTE: `ceo-cost-transcripts.py` (02/09, PLAN-186 W0) lê `message.usage` de assento e subagentes, deduplica por `message.id` (máximo por campo), separa papéis, aplica `cost-table.yaml`; integrado a `ceo-cost.py` e `budget-summary.py`. A statusline já lê a quota nativa `rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}`. Os demais instrumentos (`/audit-tokens`, `/agent-budget`, `cost_envelope.py`, `tier_policy`) leem o audit-log e são advisory. **Continua verdadeiro:** nenhum liga consumo a quota, nenhum fecha loop (bloqueia, roteia ou agenda). *(corrigido S354: a v1 dizia que nada lia o JSONL — errado.)* | `.claude/scripts/ceo-cost-transcripts.py`; `.claude/scripts/statusline-ceo.py:21-40` | P1, P2 |
| F6 | ~100 registrações `"command"` em `.claude/settings.json` (48 hooks wired / 50 registrações de evento, CLAUDE.md §1). Cada PreToolUse/PostToolUse pode injetar stdout/`additionalContext` no histórico; **o custo em tokens por turno dos hooks nunca foi medido**. Não há matcher para a tool `Workflow` — a chamada de lançamento é invisível à governança. | `.claude/settings.json`; `_lib/tokens.py` (estimador) | P1, P2, L3 |
| F7 | O loop `HEARTBEAT da esteira noturna (PLAN-01…)` NÃO é deste repo (planos aqui são `PLAN-1NN`); pertence a outro projeto no mesmo `CLAUDE_CONFIG_DIR`. L7 aplica-se lá; o PADRÃO (arquivo de estado + acordar-por-mudança + sessão nova + modelo barato) pode nascer aqui como template. | — | D4, L7, P4 |
| F8 | D2/L5 já tiveram estudo: PLAN-172 (`reviewed`) mediu **59 % de tempo morto** no run que desfinanciou a velocidade; PLAN-187 (teto de paralelismo) foi ABANDONADO em 06/09. O S339 `01-academia.md` §1.1 registra a doutrina Anthropic (≈ 4× para agentes, ≈ 15× para multi-agente, ambos versus chat simples; «quando NÃO usar») e marca como `[LACUNA]` a heurística «a tarefa vale o multiplicador?». | `PLAN-172-…md`; `PLAN-187-…md`; `docs/research/s339-orchestrator-study/01-academia.md` | D2, L5, L6 |

## 2b. Primeira leitura do ledger (S354, 17/09, coletor existente; janela ABSOLUTA 2026-09-03T00:00Z → 2026-09-17T12:00Z)

Instrumento: `python3 .claude/scripts/ceo-cost-transcripts.py --since-at … --until … --by role,model`
(98 transcripts de assento + 1.638 de subagente; 64.445 turnos únicos após dedup; 364 turnos
`<synthetic>` sem preço). Validado pela lane 03 (M11). Números API-equivalentes pela `cost-table.yaml`.

| papel | turnos | cache read | cache write | output | USD | contexto médio/turno |
|---|---|---|---|---|---|---|
| assento (sessão principal) | 4.907 | 2,55 bi (TTL 1 h) | 47,6 mi | 8,8 mi | 2.036 | **≈ 520k** |
| subagentes | 59.538 | 15,68 bi (TTL 5 min) | 392,3 mi | 10,1 mi | 10.510 | **≈ 263k** |
| total | 64.445 | 18,23 bi | 440 mi | 18,8 mi | 12.547 | 283k |

- **M1 — o custo está nos subagentes Opus 5.** 83 % do custo (US$ 10.418; 58.001 turnos) é
  `subagent | claude-opus-5`; o assento em Fable 5.1 é 16 %. Consequência direta da regra
  S339 «Fable verifica, Opus 5 executa» — não de herança de modelo. Inverte o 71 %-no-assento
  que o S339 mediu para 03/08 → 02/09: são dois regimes, não uma contradição.
- **M2 — subagente não é trabalhador de contexto pequeno.** Contexto médio por turno ≈ 263k;
  ≈ 36 turnos por transcript (59.538 / 1.638). O assento roda a ≈ 520k por turno — confirma a
  ordem de grandeza «≈ 600k» do insumo por outra via.
- **M3 — output é 2 % do custo dos subagentes.** Decomposição Opus 5 subagente: cache read
  ≈ 75 % (15,6 bi × 0,50/M), cache write de 5 min ≈ 23 % (392 mi × 6,25/M), output ≈ 2 %.
- **M4 — 75 % dos 14 dias caiu em 3 dias.** 04, 05 e 06/09 somam ≈ US$ 9,3k (noites
  autônomas S345–S347: lands livres, 504 achados de rail, 11 % produto, zero canônicos
  assináveis). Depois das regras v2.1 da S348 (codex só em bytes canônicos, WIP ≤ 3) e do
  freeze de release, o custo diário caiu para US$ 300–430 (08–10/09) e US$ 17–107 (13–17/09):
  **a mudança de modelo de operação já cortou o consumo em ~10× antes de qualquer mudança
  no framework.**
- **M5 — máquina inteira, mesma janela de 14 d:** este repo 18,5 bi tokens (output 0,10 %, 284k por
  turno); o outro projeto grande do Owner 22,7 bi (output 0,33 %, 250k por turno); o terceiro
  é desprezível. **O framework em dogfood é o pior em output por token: ≈ 1.000 tokens
  processados por token gerado**, contra ≈ 300 no projeto vizinho.
- **M6 — nada configurado, defaults do harness em vigor:** nenhum `promptCacheTtl`,
  `subagentPromptCacheTtl`, `autoCompactWindow`, `omitClaudeMd` ou `bashOutputMaxChars` nas
  settings do projeto ou do usuário (idem no consumidor do incidente). Bate com o medido:
  subagentes escrevem cache de 5 min, assento de 1 h.
- **M7 — os 13 controles nativos da tabela do Codex existem como strings no binário 2.1.274**
  (`omitClaudeMd`, `autoCompactWindow`, `promptCacheTtl`, `subagentPromptCacheTtl`,
  `bashOutputMaxChars`, `workflowSizeGuideline`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`,
  `updatedToolOutput`, `maxTurns`…). Existência confirmada; comportamento a testar.
- **M8 — o prompt que o framework injeta por spawn é PEQUENO; o prefixo de abertura do agente
  NÃO é.** `inject-agent-context.sh --mode=inline "Code Reviewer"` devolve 9,8 KB (≈ 2,5k tokens).
  Mas o 1.º turno de um subagente (input + cache) mede, neste repo, **p50 92k / p90 156k** (n=909,
  lane 03 §G): system prompt + tool defs + `CLAUDE.md` + memória + skill + prompt. A sonda de 56k
  do relato de campo (M12) é um ponto, não uma constante: a medida é a distribuição.
- **M9 — escritas de cache acima de 100k tokens = 17,4 % do custo dos 14 d (≈ US$ 2.180),
  decompostas pelo turno vizinho** (lane 03 §E): reescrita de prefixo (cache read caiu > 80 %)
  10,3 %; crescimento (conteúdo novo volumoso, p.ex. saída de ferramenta) 6,2 %; carga inicial
  0,8 %. **Expectativa CORRIGIDA para `subagentPromptCacheTtl` 5 min → 1 h:** toda escrita passa
  de 1,25× para 2× o preço-base; no melhor cenário (toda reescrita = expiração) o saldo é ≈ 0
  (−US$ 3/14 d), no pior (invalidação) +US$ 1,5k. **Não economiza neste perfil; descartado.** A
  alavanca é a CAUSA das reescritas e do crescimento (o que invalida o prefixo; saídas grandes).
- **M10 — o `/stats` tem regra exata e dois vieses OPOSTOS** (lane 03 §D, reproduzível com
  `tools/audit_collector.py --raw-by-location --stats-cache`, razão 1,000 nos 7 modelos): soma SEM
  dedup os `<session>.jsonl` e só o 1.º nível de `subagents/agent-*.jsonl`, e EXCLUI os agentes da
  Workflow tool (`subagents/workflows/<wf>/…`). Duplica o topo (×2,06 nesta máquina) e omite
  Workflow — sobre ou subconta conforme o perfil, **não é piso garantido**. Nesta máquina, janela
  contra janela (28/07 → 15/09): `/stats` 56,80 bi vs coletor **88,31 bi** (assento 18,21 +
  subagentes 70,11 = 79 %); Opus 5 = 62,8 bi = 71 % dos tokens reais (44,8 % no `/stats`);
  ≈ US$ 76 mil API-eq em 50 dias pela tabela do repo. Não substitui os 57,5 bi da ordem de
  trabalho (outro intervalo) — o instrumento do estudo é o coletor.
- **M11 — o coletor está VALIDADO por derivação independente em corpus ESTÁVEL** (lane 03 §C):
  turnos, input, output, cache read, escritas 5 min e 1 h e USD sem arredondar — **delta zero nos 8
  modelos**, tabela completa (só `<synthetic>` sem preço, 0 tokens). A divergência da v1 era a
  sessão em curso escrevendo no transcript entre as duas rodadas: comparação só com `--until` no
  passado. Preços: leitura 0,10; **Fable 5.1 0,025 = US$ 0,25/M (referência oficial da API)** —
  metade da leitura do Opus 5, escrita e output o dobro; Fable 5 lê a 0,10. Dedup: 16,6 % dos
  grupos duplicados têm `output_tokens` progressivo — «primeiro vence» subcontaria 41 %.
- **M12 — relato de campo do projeto vizinho (17/09, 34 h de esteira autônoma com 12–24
  workflows; verbatim no archive PRIVADO do framework, sem nome aqui), RECONCILIADO com o
  coletor na janela do incidente (2026-09-15T23:00Z → 09-17T13:10Z):** o consumidor está no
  framework **1.4.0** (o relato dizia rc.4), sem matcher `Workflow`, sem TTL/omit; 126 transcripts
  de assento + 4.475 de subagente; 35 runs de Workflow com turnos; **US$ 4,3k API-eq em 38 h**
  (subagentes US$ 3,96k, 6,10 bi de cache read, 24.639 turnos, ≈ 248k por turno). **Prefixo de
  abertura por subagente: p50 154k / p90 166k (n=495)** — não 56k; **pico de contexto por
  subagente p50 280k / p90 358k**; soma dos picos 136 mi contra 6,10 bi de leitura acumulada
  (45×). Logo os «250–650k tokens por fase» do runner são da ordem da soma dos PICOS dos agentes
  executados (o S339 já apontara para `Workflow.totalTokens`), não consumo — e as estimativas
  por hora feitas nessa unidade não convertem. Escritas grandes lá são iniciais (41) e
  crescimento (44); reescritas raras (5): o custo está no prefixo de abertura e na releitura, não
  em expiração. Mediana de 205 mi de cache read e 13 agentes por run. O que o relato mede sem
  precisar de unidade: 10 mortes por quota em 34 h, cada uma perdendo a fase inteira (sem
  checkpoint dentro de `agent()`); editar o TEXTO do prompt com runs em voo invalidou 17 fatias;
  4 merges de 23 fatias. Forma concreta de L5: **teto por FASE pesada, não por fatia**; de L2/L3:
  `omitClaudeMd` com contrato mínimo por papel e spec por fase em vez do spec inteiro.

## 3. Como o estudo deve ser montado (proposta v2, pendente do Owner)

Ordem revista após a lane 02 (§5). Literatura ORIENTA cada experimento; não é etapa separada.

1. **Validar o coletor e definir a métrica-alvo.** ~~Auditar o ledger~~ FEITO (lane 03, 17/09, v2
   após REJECT). Falta definir «entrega aprovada» (land/PR aceito, teste verde, veredito de
   rail) e medir **quota por entrega aprovada**, não output/total.
2. **Reconciliar coletor × preços × quota observada.** Correlacionar passivamente
   `rate_limits.{five_hour,seven_day}` da statusline com o ledger; se insuficiente, o
   experimento de uma conta / blocos comparáveis descrito pelo Codex em D.1.
3. **Testar contexto** (P1): controles nativos de M7 em 2.1.274, um a um, com controle;
   saídas de tools (`bashOutputMaxChars`, `updatedToolOutput` — o relato de M12 mostra pytest
   entrando dezenas de vezes no contexto de uma fase; «crescimento» = 6,2 % do custo aqui),
   continuidade por tarefa (handoff em arquivo), `omitClaudeMd` com contrato mínimo por papel
   (M8/M12: prefixo de abertura p50 92k aqui, 154k no consumidor), e a CAUSA das reescritas
   (10,3 %): o que invalida o prefixo entre turnos. **TTL de 1 h para subagentes: descartado por
   expectativa (M9) — não testar.**
4. **Comparar roteamento e concorrência** (P3, P5): 1/3/7 agentes e modelos permitidos no
   MESMO conjunto de tarefas, mesmo orçamento, mesmos testes e revisão; escolher por
   entrega aceita e tempo total. R1 fixa o perímetro financeiro. Hipótese a testar (M11), em
   DÓLAR API — quota é outra medida: para agentes dominados por leitura de cache (75 % do
   custo dos subagentes), **Fable 5.1 sairia ≈ 12 % mais barato que Opus 5** (leitura 0,25 vs
   0,50; escrita e output 2×) — inverte a justificativa de custo da regra S339 «Opus 5 executa»;
   em quota, o bucket semanal do Fable estava em 4 % contra 16 % do geral (insumo §2.5). Teto de
   concorrência por FASE PESADA (3–4), não por tarefa (M12) — contenção inicial a medir, não ótimo.
5. **Dimensionar scheduler e capacidade paga** (P5, P6, P7) com a demanda que sobrar. Requisitos
   vindos do campo (M12): distinguir `five_hour` (esperar o reset) de spend cap/session limit
   (parar tudo e avisar); detectar troca de conta em vez de esperar o `resetsAt` da conta antiga
   (3,6 h paradas); guardar os args literais de cada `agent()` (o runner guarda só o hash);
   checkpoint por fase — retomar pelo transcript em vez de refazer o prompt (agentes nomeados já
   retomam por `SendMessage`, S328; agentes de Workflow não).

Formato de entrega: um arquivo por lane neste diretório + síntese `00-synthesis.md`, no molde do
`orchestrator-operating-model-S339.md`. Waves que APLICAM algo (agents `model:`, hooks, boot
menor) viram plano próprio com debate L3 — o estudo em si é livre (zero canônico). **A ordem do
Owner de 17/09 (corrigir a execução autônoma nos consumidores) segue em plano próprio, PLAN-190.**

## 4. Regras que já valem para este estudo

- Claim medida = data + substrato + janela ABSOLUTA com limite superior no passado (o transcript da
  sessão em curso cresce durante a medição); medições de junho/2026 são de outra geração de modelo.
- Cure a CLASSE: o insumo enumera 7 diagnósticos; o estudo nomeia a classe de cada um.
- Nada de rotação automática de contas em nenhuma lane (R3); nada que toque dinheiro sai de Opus/Fable (R1).
- O estudo NÃO edita Gate-1 (`CLAUDE.md`, `PROTOCOL.md`, `team.md`, skill CEO) — proposta de
  encolhimento vai para a síntese e passa por cerimônia.
- Nomes de outros projetos da máquina NÃO entram neste diretório público; agregados só. Materiais
  que nomeiam projetos vizinhos (o relato de campo de M12) vivem no archive privado do framework.
- O instrumento do estudo é o coletor deduplicado (`ceo-cost-transcripts.py`), validado em M11;
  `/stats` tem dois vieses opostos (M10). Dólar API-equivalente e quota são medidas distintas.

## 5. Lane 02 — parecer do Codex (17/09): o que muda na leitura

Codex leu o repositório e fontes primárias; cada afirmação factual sobre o repo foi
re-verificada pelo CEO nesta sessão (arquivo + linha em §2). Saldo: **3 correções aceitas,
4 refinamentos aceitos, 2 pontos mantidos, 1 divergência declarada.** Um segundo retorno do
revisor cruzado (REJECT sobre a lane 03 v1, seis pontos) foi incorporado por inteiro na v2 —
lista em `03-collector-audit.md` §3.

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
- Sessões longas com ≈ 520k por turno e loop de fundo em sessão viva seguem as alavancas de
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
