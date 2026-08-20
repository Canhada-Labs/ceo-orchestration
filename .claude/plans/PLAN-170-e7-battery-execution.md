---
id: PLAN-170
title: Bateria E7 — execução de E4 (fidelidade de handoff) e E3 (paralelismo só na verificação)
status: draft
created: 2026-08-18
owner: CEO
depends_on: [PLAN-169]
budget_tokens: "CEO-context 700k-1.2M (ADR-081: EXCLUI contexto de sub-agente) — W0 60-120k; W1 200-350k; W2 150-250k; W3 200-350k; W4 100-200k. FLEET (sub-agentes; orçamento SEPARADO, não é contexto do CEO): piloto 4.5-9M; N pleno 11-22M; TETO DURO 14M — acima disso o plano PARA e volta ao Owner. Re-derivado nesta autoria: a estimativa 6-20M do PLAN-169 cobria E1-E4 e está STALE (§2.3)."
budget_sessions: 8-12
context_risk: high
external_wait: "corte da v1.4.0-rc.1 — gatilho nomeado pelo PLAN-169 W5 (`PLAN-169:809`). ESTADO REAL (emenda S316, decisão do Owner): a tag `v1.4.0-rc.1` NÃO existe (git tag --list vazio) e não há data; o corte depende de PLAN-169 W4 + W4-C + W6.2, todos abertos. Plano CONGELADO em draft por decisão S315/S316 — abre quando `git tag --list v1.4.0-rc.1` deixar de ser vazio, nunca antes."
eta_calendar: "governado pelo external_wait (regra ADR-081/PLAN-180: eta = max(external_waits)) — abre em D+0 do corte da v1.4.0-rc.1; depois, multi-sessão CEO-only ⇒ mesmo-dia a D+1 por wave, exceto o que a QUOTA impuser (§5.4)"
tags: [experiments, pre-registration, handoff, review, fleet, no-speed-claim]
---

# PLAN-170 — Bateria E7: executar E4 e E3 sob o pré-registro assinado

> **Este plano EXECUTA, não re-assina e não emenda.** O desenho é o
> conteúdo de `.claude/plans/PLAN-169/W5-preregistration.md`
> (Anchor-SHA `c0295e15a9d2ef869e44c4cab8b56022acd7b4b7`, assinatura
> destacada em `W5-preregistration.md.asc`, ambos landados em
> `fcac12d`). Aquele arquivo é **IMUTÁVEL**: "emenda = novo
> pré-registro versionado, nunca edição"
> (`PLAN-169/W5-preregistration.md:6`). Nada neste plano altera uma
> regra de decisão do experimento; onde o pré-registro é silencioso,
> este plano **fixa o parâmetro ANTES do 1º run** e diz que fixou
> (§2.4).

## Context

- **AC-6 do PLAN-169 exige este arquivo.** O AC pede "PLAN-170 criado
  com orçamento próprio declarado e gatilho nomeado (pós-corte
  v1.4.0-rc.1)" (`PLAN-169:984-989`). A metade do AC que já fechou é o
  pré-registro assinado; esta é a outra metade. O número 170 é um
  buraco deliberado reservado pelo PLAN-169 — 171-181 já existem.
- **E0 já rodou (S300) e mudou o escopo.** Sobre a amostra PINADA de
  14 planos (M=155→168), 723,0h de wall-clock: máquina 155,4h · humano
  137,9h · morto 429,6h; **S conservador = 1,000**; fração não-máquina
  = 0,785 (descritiva, não decide nada). Pela regra pré-registrada
  `S ≥ 0,40 ⇒ E1/E2 NÃO financiados`
  (`PLAN-169/W5-preregistration.md:52`), **E1 e E2 estão mortos**.
  Evidência: `.claude/plans/PLAN-169/e0-report-s300.txt` (agregado nas
  linhas 76-86), sha256 `d07935b3fc67d48dd0101a989b64b1ee04e071c3ac8c2550160baf68672e4f34`
  — o mesmo registrado em `PLAN-179/LEDGER.md:68-70`. O arquivo nasceu
  fora da árvore (`~/.rc2-backup/`) e entra por **resíduo do AC-6 do
  PLAN-169, não deste plano**; leitura já propagada em `PLAN-172:28-38`.
- **Logo o escopo aqui é E3 + E4, e só.** E4 "roda SEMPRE"
  (`W5-preregistration.md:58`); E3 não é gateado pelo E0 — o
  pré-registro condiciona ao E0 apenas E1 (`:74`) e E2 (`:82`).
- **PLAN-172 já herdou o verdito e não re-litiga:** "E1/E2 (autoria
  paralela): mortos pela regra pré-registrada do E0"
  (`PLAN-172:141-144`); e "E3 — INTOCADO (pré-registro W5 assinado é
  IMUTÁVEL; execução = PLAN-170)" (`PLAN-172:129`).

## Goal

Executar E4 e depois E3 exatamente como pré-registrados, em clone
dedicado, e publicar um relatório com inputs impressos cuja claim
máxima seja sobre **qualidade de auditoria** — inclusive se o
resultado for negativo.

## Thesis

Três afirmações sustentam este plano, e nenhuma delas é de velocidade.

1. **O que sobrou da bateria é a parte que a literatura considera
   promissora.** E1/E2 eram autoria paralela — desfinanciados por
   medição própria. E3 testa paralelismo **só na verificação** e E4
   mede **quanto de uma spec sobrevive a k hops** de handoff. Saída do
   E4 é uma constante de design ("nenhuma cadeia >X hops sem
   re-ancoragem em artefato", `W5-preregistration.md:62-64`), que o
   framework consome mesmo que o E3 dê negativo.
2. **A ordem é pré-registrada: E4 antes de E3.** O pré-registro diz
   "Sequência (cada um gateia o próximo)" (`:36`). Portanto W2 (E4)
   precede W3 (E3). **Nenhuma regra numérica de gate E4→E3 foi
   assinada** — inventar uma agora seria regra post-hoc (a mesma classe
   que o pair-rail S300 removeu do E0, `e0-report-s300.txt:84-86`).
   Logo: E3 procede após E4 salvo kill de substrato ou de orçamento;
   isso está declarado, não deduzido.
3. **Piloto-first é a única defesa de orçamento honesta.** A primeira
   saída do piloto do E4 é o **custo real por invocação**, que
   re-deriva o orçamento antes de qualquer autorização de N pleno
   (§2.3). Estimativa que não se corrige com a primeira medição é
   chute com casas decimais.

## 2. Orçamento — re-derivado nesta autoria (a estimativa antiga está STALE)

### 2.1 Por que a antiga não serve

O PLAN-169 declarou "estimativa honesta 6-20M tokens" para a bateria
(`PLAN-169:75, :808`). Ela está **STALE por duas razões independentes**:

- **Cobria E1-E4.** E1 e E2 saíram por regra pré-registrada; o conjunto
  medido mudou.
- **Era orçamento de FLEET escrito num campo de CEO.** ADR-081 define
  `budget_tokens` como tokens de contexto do CEO e **exclui contextos de
  sub-agente** (`PLAN-SCHEMA.md:325-327`). Os 6-20M são tokens de
  sub-agente. Este plano declara os dois separadamente, com nomes
  diferentes.

### 2.2 A conta (inputs impressos)

**E4 — fidelidade de handoff.** N fixado neste plano (§2.4): 30 cadeias
× 2 condições (prosa-livre via SendMessage vs artefato tipado) × 3
repetições = **180 cadeias**; hops `k ∈ {1,2,3,4,5}`.

| grandeza | valor | origem |
|---|---|---|
| teto de invocações | 180 × 5 = **900** | derivação do debate, `PLAN-169/debate/round-1/vp-engineering.md:34` |
| esperado (k médio = 3) | 180 × 3 = **540** | derivado aqui |
| custo por hop | **10-20k tokens** | `…/vp-engineering.md:115` ("piso otimista") — **estimativa, medida no piloto** |
| E4 pleno (esperado) | **5,4-10,8M** | 540 × 10-20k |
| E4 pleno (teto) | **9-18M** | 900 × 10-20k |
| E4 piloto (N/3) | **1,8-3,6M** | 180 invocações esperadas |

**E3 — paralelismo só na verificação.** Braços do pré-registro (`:66-72`):
`k=1`, `k=3`, `k=5` (cegos) + `k=3` COM comunicação + token-matched
(`k=1` × 3 rodadas) = **15 invocações de revisor por run**; ≥3 runs por
célula ⇒ **45 por alvo semeado**.

| grandeza | valor | origem |
|---|---|---|
| alvos semeados | piloto 2 → pleno 4 | fixado aqui (§2.4) |
| invocações (pleno) | 4 × 45 = **180** | derivado aqui |
| custo por revisor | **30-60k tokens** | derivado aqui — **unverified**, medido no piloto |
| E3 pleno | **5,4-10,8M** | 180 × 30-60k |
| E3 piloto (2 alvos) | **2,7-5,4M** | 90 × 30-60k |
| adjudicação/refuters | **+10-20%** | ground truth semeado é mecânico; sobra só o não-semeado |

### 2.3 O número honesto, e o que ele revela

- **Fleet, piloto das duas: 4,5-9M.** **Fleet, N pleno das duas:
  11-22M.** **Teto duro declarado: 14M** — atingido o teto, o plano
  PARA e a decisão volta ao Owner.
- **A consequência desconfortável, dita em voz alta:** tirar E1 e E2
  cortou o ESCOPO pela metade e **não cortou o custo** — E4 e E3 sempre
  foram os caros. Com teto de 14M, o N pleno das duas baterias só cabe
  na **banda otimista** de custo por invocação. Se o piloto medir a
  banda alta, as rotas são (a) Owner eleva o teto, (b) E4 pleno + E3
  piloto, (c) parar e publicar o piloto. **Essa escolha é orçamento, não
  regra de decisão** — não toca hipótese, kill, nem estimando.
- **Tensão declarada, não resolvida por mim:** o pré-registro assinado
  chama o E4 de "barato, mecânico" (`W5-preregistration.md:58`),
  enquanto a aritmética do próprio debate põe o E4 em 9-18M
  ("15-40× o orçamento declarado do plano inteiro",
  `…/vp-engineering.md:117`). A leitura que este plano adota — sem
  emendar o texto assinado — é que "barato" ali qualifica a
  **graduação** (mecânica, ground truth verificável por máquina, sem
  rotulagem humana), não o consumo de tokens.

### 2.4 O que o pré-registro NÃO fixou (e este plano fixa antes do 1º run)

O texto assinado fixa `k ∈ {1,3,5}`, os braços, "≥3 runs por célula" e
os critérios de kill. Ele **não** fixa: (i) o N de cadeias/repetições do
E4, (ii) o número de alvos semeados do E3, (iii) o custo por invocação.
Este plano os fixa em `.claude/plans/PLAN-170/N-PINNING.md` **antes do
primeiro run**, com a disciplina que o resto do repo já usa: proibido
estender N "até dar certo" (a mesma proibição escrita para o E5 em
`PLAN-172:98-99`). Fixar parâmetro que a assinatura não cobre é legal;
mudar parâmetro depois de ver dado, não é.

## 3. Postura de fleet — VERBATIM do PLAN-169 (obrigatória, não negociável)

Reproduzido literalmente de `PLAN-169:812-818`:

> Protocolo de fleet do 170 (R-SEC10 + r2-R-SEC15): PROIBIDO
> `inbound=accept` combinado com acceptEdits/bypass/night-mode;
> sessões de experimento isoladas — **sem GPG, sem remote, sem
> credenciais, guards ATIVOS, nenhum caminho de cerimônia** (clone
> dedicado); o
> pré-registro declara que as constantes medidas valem para a POSTURA
> DO EXPERIMENTO, não a entregue (R-5).

E de `PLAN-169/W5-preregistration.md:17-22` (assinado):

> PROIBIDO `inbound=accept` combinado com acceptEdits/bypass/night-mode.
> Sessões de experimento ISOLADAS — sem GPG, sem remote, sem credenciais,
> guards ATIVOS, nenhum caminho de cerimônia (clone dedicado). As
> constantes medidas valem para a POSTURA DO EXPERIMENTO, não a entregue.

Operacionalização (o "como", que a assinatura não fixa):

- **Clone dedicado, descartável**, fora da árvore canônica. Sem chave
  GPG disponível ao processo; sem direito de push no remote (remote
  removido ou apontado para nada); nenhum script de cerimônia no caminho.
- **`crossSessionInbound` NÃO EXISTE hoje** — `grep -c crossSessionInbound
  .claude/settings.json` = 0; a linha é entregável do W4-C do PLAN-169,
  ainda aberto (`PLAN-179/LEDGER.md:73-88`). Consequência: se o corte da
  rc.1 acontecer com a alavanca já landada, o clone substitui o valor
  **no clone, nunca no repo canônico** (rota registrada em
  `PLAN-169:548-552`); se não, a proibição vale por construção — nenhuma
  sessão de experimento roda com acceptEdits/bypass/night-mode, e o W0
  registra qual dos dois mundos valeu.
- As constantes que saírem daqui (meia-vida de restrições, recall por k)
  são **da postura do experimento**. Citá-las como propriedade do produto
  entregue é erro de escopo.

## 4. Waves

### W0 — Abertura: gatilho, clone e verificação do pré-registro (L2, 1 sessão)
Check: `git tag --list 'v1.4.0-rc.1'` não-vazio; `gpg --verify .claude/plans/PLAN-169/W5-preregistration.md.asc .claude/plans/PLAN-169/W5-preregistration.md`; `shasum -a 256 .claude/plans/PLAN-169/W5-preregistration.md` conferido contra o registro do W0.
- [ ] Confirmar o gatilho: a tag `v1.4.0-rc.1` existe. Antes disso este
      plano permanece fechado — abrir cedo é violar o `external_wait`.
- [ ] Verificar assinatura + hash do pré-registro e registrar ambos.
      **Não re-assinar, não copiar, não editar.**
- [ ] Montar o clone dedicado e provar a postura: sem GPG utilizável,
      sem remote com push, guards ativos, nenhum script de cerimônia
      alcançável. Registrar o resultado do probe, não a intenção.
- [ ] Registrar qual mundo de `crossSessionInbound` valeu (§3) e, se a
      alavanca existir, que a substituição foi feita SÓ no clone.
- [ ] Fixar N em `N-PINNING.md` (§2.4) e commitá-lo ANTES do 1º run.

### W1 — Instrumento comum: ground truth, juiz e pré-checagem de variância (L2-L3, 2-3 sessões)
Check: suíte do harness verde com exit verdadeiro (`pytest … > out; echo $?`, nunca `| tail`); relatório de validação do juiz com N labels e concordância impressa; pré-checagem de variância imprimindo σ(A) e Δ.
- [ ] Semear o ground truth **nós mesmos** — nunca issues públicas
      (contaminação de search-time, `W5-preregistration.md:31-32`).
- [ ] Escrever a spec do E4: **20 restrições atômicas
      máquina-verificáveis** (`W5-preregistration.md:60-61`), cada uma
      com verificador determinístico.
- [ ] **Validação do juiz (U-4).** Ground truth mecânico onde possível;
      LLM-judge validado em N labels ANTES de contar qualquer resultado
      (`PLAN-169/debate/round-1/consensus.md:113-115`). **Registro
      honesto: U-4 foi aceita no debate mas NÃO entrou no texto
      assinado** — logo ela vive aqui, como requisito de execução, e não
      como emenda ao pré-registro.
- [ ] Harness: ordem randomizada, mesmo SHA base em worktrees separados,
      grading cego, registro de modelo/versão/flags/settings efetivos
      (`W5-preregistration.md:29-34`).
- [ ] **Pré-checagem de variância**: ≥3 runs por célula ANTES de comparar
      braços; se σ(A) cobrir Δ, reporta e PARA (regra assinada, `:29-31`).

### W2 — E4 (roda SEMPRE): piloto → N pleno (L3, 2-3 sessões)
Check: `e4-report.md` presente com inputs impressos (N, hops, custo medido por hop, seeds, sha do harness) e a meia-vida de restrições por condição; re-derivação de orçamento §2.3 refeita com o custo MEDIDO antes de autorizar N pleno.
- [ ] Rodar o piloto (N/3) nas duas condições — prosa-livre via
      SendMessage vs artefato tipado (shards ADR-141 / memory-scratchpad).
- [ ] **Medir o custo real por invocação** e re-derivar o orçamento.
      Se o piloto projetar estouro do teto de 14M, PARAR e levar as
      rotas (a)/(b)/(c) do §2.3 ao Owner — não seguir "para ver".
- [ ] Rodar o N pleno **somente** se o teto couber.
- [ ] Emitir a constante de design: meia-vida de restrições em hops
      ("nenhuma cadeia >X hops sem re-ancoragem em artefato").

### W3 — E3: paralelismo só na verificação (L3, 2-3 sessões)
Check: `e3-report.md` com recall por k e razão FP/TP por k, p50/p95 (nunca média sozinha), braço token-matched e braço COM comunicação reportados lado a lado; critério assinado (recall monotônico em k E FP/TP ≤ 1,0 em k=5) avaliado explicitamente, com verdito escrito mesmo se negativo.
- [ ] Geração solo; review com `k ∈ {1,3,5}` revisores cross-session
      **mutuamente cegos**.
- [ ] Braço token-matched (`k=1` × 3 rodadas) — sem ele, resultado
      positivo é indistinguível de "gastamos mais compute".
- [ ] Braço `k=3` **COM** comunicação, contra a predição pré-registrada
      da deliberative illusion (comunicação REDUZ findings únicos).
- [ ] Avaliar o critério assinado e escrever o verdito. **Negativo
      publica igual** (`W5-preregistration.md:34`).

### W4 — Relatório, publicação e fechamento (L2, 1-2 sessões)
Check: `E7-REPORT.md` commitado com todos os inputs impressos; `grep -n "no speed claim" AGENTS.md` inalterado salvo decisão explícita do Owner registrada no relatório; PLAN-169 AC-6 referenciado como fechado.
- [ ] Consolidar E4 + E3 num relatório único com inputs impressos.
- [ ] Registrar a decisão de claim: a claim máxima sustentável é sobre
      **QUALIDADE DE AUDITORIA**, nunca velocidade/throughput
      (`W5-preregistration.md:95-104`). Mudar o "no speed claim" do
      AGENTS.md é decisão do Owner sobre evidência, e só.
- [ ] Registrar E3b (refinamentos que a pesquisa sugeriu) como
      follow-on com **pré-registro e assinatura próprios**, NÃO
      financiado aqui (`PLAN-172:129-137`).
- [ ] Devolver o clone: destruir ou congelar, e dizer qual.

## Acceptance criteria

- [ ] AC-1 [P0][US1][.claude/plans/PLAN-170/OPEN-GATE.md] Gatilho provado
      (tag `v1.4.0-rc.1` existe), assinatura + hash do pré-registro
      verificados sem re-assinar, e postura de fleet do §3 provada por
      probe no clone (GPG indisponível, sem push, guards ativos,
      nenhum caminho de cerimônia) — evidência, não intenção.
- [ ] AC-2 [P0][US1][.claude/plans/PLAN-170/N-PINNING.md] N do E4 e
      alvos do E3 fixados e commitados **antes do 1º run**, com a
      proibição explícita de estender N após ver dado.
- [ ] AC-3 [P0][US2][.claude/plans/PLAN-170/instrument/judge-validation.md]
      Juiz validado (U-4) antes de qualquer contagem; ground truth
      semeado por nós; pré-checagem de variância executada com σ(A) e Δ
      impressos, e parada honesta se σ(A) cobrir Δ.
- [ ] AC-4 [P1][US3][.claude/plans/PLAN-170/e4-report.md] E4 executado
      nas duas condições com inputs impressos; custo real por invocação
      medido no piloto e orçamento re-derivado ANTES do N pleno;
      meia-vida de restrições em hops emitida como constante de design.
- [ ] AC-5 [P1][US4][.claude/plans/PLAN-170/e3-report.md] E3 executado
      com os 5 braços (k=1/3/5 cegos + token-matched + k=3 com
      comunicação), p50/p95, e verdito explícito contra o critério
      assinado — escrito também se negativo.
- [ ] AC-6 [P1][US5][.claude/plans/PLAN-170/E7-REPORT.md] Relatório único
      publicado com todos os inputs; decisão de claim registrada; nenhuma
      afirmação de velocidade/throughput emitida.
- [ ] AC-7 [P2][US5][.claude/plans/PLAN-169-closure-and-cross-session-evolution.md]
      AC-6 do PLAN-169 referenciado como fechado por este plano (a
      metade "PLAN-170 criado"), sem editar o pré-registro assinado.

## Fronteiras honestas

- **Não há claim de velocidade, e este plano não pode produzir um.** A
  claim máxima sustentável é qualidade de auditoria a orçamento de tempo
  igualado — e "a orçamento igualado" é condição de controle, não
  afirmação de desempenho (`W5-preregistration.md:95-104`).
- **E1/E2 estão mortos por medição própria**, não por opinião. Ressuscitá-los
  exige dado NOVO de fração serial (`PLAN-172:141-144`).
- **Validade externa baixa por construção:** um repo, um mantenedor, um
  vendor primário, uma postura de experimento. As constantes valem para
  a postura medida (R-5), não para adotantes.
- **O E0 é retrospectivo e enviesado PARA CIMA de S** por corte
  conservador declarado (máquina 100% serial onde o grafo é
  irrecuperável do log v2, `e0-serial-fraction.py:16-21`). Isso é viés
  contra financiar E1/E2 — direção segura, mas viés.
- **A fração não-máquina 0,785 é DESCRITIVA.** O pair-rail removeu
  qualquer regra de decisão sobre esse piso por ser post-hoc e
  não-assinada (`e0-report-s300.txt:84-86`). Não reintroduzir.
- **Substrato:** `agent()` de Workflow não passa pelo `check_agent_spawn`
  (CLAUDE.md §5, PLAN-178 Lote B). Fan-out que ESCREVE fica fora de
  Workflow; os braços deste plano são de leitura/review e handoff, com o
  bloco COMMON de validação pré-despacho quando usarem Workflow.
- **O relatório do E0 chega por outra mão.** Ele nasceu fora da árvore
  (`~/.rc2-backup/e0-report-s300.txt`) e entra em
  `.claude/plans/PLAN-169/e0-report-s300.txt` como resíduo do AC-6 do
  PLAN-169 — **não deste plano**. Se, ao abrir o W0, o arquivo não
  estiver RASTREADO com sha `d07935b3…`, a citação do §Context está
  pendurada: conferir antes de usar o número.
- **Custo por invocação é estimativa até o piloto medir.** Os 10-20k/hop
  vêm do debate; os 30-60k/revisor foram derivados aqui e estão
  marcados **unverified**.

## Kill switches

**Assinados (imutáveis — reproduzir, nunca reescrever):**

- **Variância mata na largada:** ≥3 runs por célula ANTES de comparar
  braços; se σ(A) cobrir Δ, reporta e para (`W5-preregistration.md:29-31`).
- **Kill geral de substrato:** mensagem cross-session perdida ou
  duplicada = defeito registrado (substrate-watch) e **pausa**; defeito
  ≠ resultado (`:90-93`).
- **Critério do E3:** recall monotônico em k **E** razão FP/TP ≤ 1,0 em
  k=5 (`:71-72`). Falhar o critério é resultado publicável, não motivo
  para estender N.

**Operacionais (deste plano — orçamento e higiene, NÃO regras de decisão):**

- **Teto de fleet 14M:** atingido, o plano PARA e volta ao Owner (§2.3).
- **Estouro projetado no piloto:** se a medição de custo projetar o teto
  antes do N pleno, PARAR no piloto e escolher entre as rotas (a)/(b)/(c)
  — a escolha é do Owner.
- **Contaminação do clone:** qualquer evidência de que o clone alcançou
  superfície canônica, GPG ou remote com push ⇒ abortar a bateria,
  destruir o clone, reabrir o W0.
- **Quota:** o E0 mediu tempo-morto em 429,6h de 723,0h. Uma bateria de
  milhões de tokens compete com a própria vazão do repo; exaustão de
  quota é pausa esperada, registrada, e **nunca** motivo para reduzir N
  silenciosamente.

Nenhum destes altera hipótese, estimando ou critério. Qualquer mudança
que altere um deles exige **novo pré-registro versionado e assinado**.

## Governança

- **Este plano é L3+** (bateria experimental, fan-out de fleet, postura
  de sessão especial, orçamento de milhões de tokens). Portanto:
  **`/debate start PLAN-170 "<proposta>"` é OBRIGATÓRIO antes de
  qualquer execução** (CLAUDE.md §4, PROTOCOL.md). O debate deve
  ratificar, no mínimo: o N fixado no §2.4, o teto de 14M, e a leitura
  de "barato" do §2.3.
- **`status: draft` — só o Owner promove para `reviewed`.** O CEO não
  se auto-aprova.
- **Nenhuma superfície canônica é tocada por este plano.** Os artefatos
  vivem em `.claude/plans/PLAN-170/`. Se algum resultado motivar
  mudança de doutrina (AGENTS.md, README, `/debate`), isso vira ADR +
  cerimônia própria, fora daqui.
- **Dependência dura:** `depends_on: [PLAN-169]`. O gatilho é o corte da
  v1.4.0-rc.1, que depende de W4 + W4-C + W6.2 do PLAN-169 — todos
  abertos hoje (`PLAN-179/LEDGER.md:73-88`).

## Open questions

- **OQ-1 (Owner):** o teto de 14M de fleet é aceitável, ou o plano nasce
  com teto menor e piloto-only? A resposta muda o §2.3, não o desenho.
- **OQ-2 (Owner):** se o corte da rc.1 acontecer **sem** a alavanca
  `crossSessionInbound` landada (W4-C), a bateria roda com a proibição
  garantida por construção/disciplina, ou espera a alavanca? O §3
  suporta os dois; a escolha é do Owner.
- **OQ-3 (CEO, para o debate):** o E4 usa Workflow (validador
  pré-despacho, sem gate de substrato) ou spawns nomeados (gate real,
  mais caro)? Afeta custo por hop e a força do registro de auditoria.

## How to continue

Primeira mensagem de uma sessão futura:

> Gate 1-3 do CLAUDE.md. Ler `.claude/plans/PLAN-170-e7-battery-execution.md`
> e `.claude/plans/PLAN-169/W5-preregistration.md` (IMUTÁVEL — nunca
> editar). Confirmar o gatilho: `git tag --list 'v1.4.0-rc.1'`. Se
> vazio, o plano continua fechado — não abrir. Se existir e o status
> ainda for `draft`, o próximo passo é `/debate start PLAN-170` e a
> promoção `draft → reviewed` pelo Owner. Só depois o W0.

## Success criteria

- [ ] AC-1..AC-7 fechados com evidência (path:line, sha ou saída de
      comando — nunca paráfrase).
- [ ] Relatório publicado com inputs impressos, positivo ou negativo.
- [ ] `AGENTS.md` "no speed claim" intacto, salvo decisão explícita do
      Owner registrada.
- [ ] Pré-registro assinado byte-idêntico ao do início (verificável por
      sha256 + `gpg --verify`).
- [ ] Clone destruído ou congelado, com o destino registrado.

## Progress log

Check: none (doc-only)
- [ ] 2026-08-18 (S313) — plano autorado em `status: draft` fechando a
      metade restante do AC-6 do PLAN-169. Escopo reduzido a E3+E4 pelo
      verdito do E0; orçamento re-derivado do zero (§2). Aguardando
      gatilho (corte v1.4.0-rc.1), debate L3 e promoção do Owner.
