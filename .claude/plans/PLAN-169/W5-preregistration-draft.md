# Pré-registro da bateria E7 — DRAFT para assinatura (PLAN-169 W5)

> **Como assinar:** `cp` para `W5-preregistration.md`, preencher data +
> Anchor-SHA (`git rev-parse HEAD`), `gpg --armor --detach-sign`, commitar
> AMBOS (md + .asc). **O aceite exige o pré-registro assinado (hash
> commitado) ANTES do 1º run — inclusive do E0.** Após a assinatura este
> conteúdo é IMUTÁVEL; emenda = novo pré-registro versionado, nunca edição.
>
> A execução E1-E4 é o **PLAN-170** (gatilho: abre imediatamente após o
> corte da v1.4.0-rc.1; o 170 NÃO re-assina — só roda). Neste plano (169)
> executa-se apenas o **E0** (retrospectivo, custo ~zero), que gateia
> E1/E2.

Plan: PLAN-169 W5 (execução: PLAN-170)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Postura do experimento (R-SEC10 + r2-R-SEC15 + R-5)

PROIBIDO `inbound=accept` combinado com acceptEdits/bypass/night-mode.
Sessões de experimento ISOLADAS — sem GPG, sem remote, sem credenciais,
guards ATIVOS, nenhum caminho de cerimônia (clone dedicado). As
constantes medidas valem para a POSTURA DO EXPERIMENTO, não a entregue.

## Bloco metodológico comum (imutável)

3 braços sempre — (A) solo otimizado, (B) paralelo cross-session,
(C) solo token-matched com B (sem C, resultado positivo é
indistinguível de "gastamos 15× mais tokens" — ~80% da variância em
benchmarks é compute); percentis p50/p95, nunca média sozinha; ≥3 runs
por célula para variância run-to-run ANTES de comparar braços (σ(A)
cobre Δ ⇒ morto na largada, reporta e para); grading cego; ground truth
semeado por nós (nunca issues públicas — search-time contamination);
ordem randomizada, mesmo SHA base em worktrees separados; registrar
modelo/versão/flags/settings efetivos; negativo publica igual.

## Sequência (cada um gateia o próximo)

### E0 — gate-zero (retrospectivo, custo ~zero): fração serial

Sobre o audit log HMAC dos **14 planos M=155→168** (amostra PINADA),
decompor wall-clock em tempo-máquina / tempo-humano (review,
cerimônias, decisões) / tempo-morto (CI, quota). A fração serial S
INCLUI o tempo-morto não-paralelizável E a máquina serial do caminho
crítico:

`S = (humano + morto_não_paralelizável + máquina_serial_crítica) / total`

com máquina_serial derivada do grafo de dependência dos passos (ou,
onde irrecuperável do log, o corte conservador: máquina 100% serial
naquele plano, reportado por plano).

**Regra pré-registrada:** S ≥ 0,40 ⇒ E1/E2 NÃO são financiados;
S ≤ 0,20 ⇒ E1/E2 liberados; banda 0,20 < S < 0,40 ⇒ resultado
PRÉ-DEFINIDO: E1 liberado APENAS como piloto (metade do N, mesmo
critério de kill) e E2 NÃO financiado — nenhuma faixa medível fica
para juízo post-hoc.

### E4 — fidelidade de handoff (barato, mecânico, roda SEMPRE)

Cadeias de k hops com spec de 20 restrições atômicas
máquina-verificáveis; prosa-livre via SendMessage vs artefato tipado
(shards ADR-141 / memory-scratchpad). Saída: meia-vida de restrições
em hops — constante de design ("nenhuma cadeia >X hops sem
re-ancoragem em artefato").

### E3 — paralelismo SÓ na verificação

Geração solo; review com k∈{1,3,5} revisores cross-session mutuamente
cegos + braço token-matched (k=1 × 3 rodadas) + braço k=3 COM
comunicação (predição pré-registrada da deliberative illusion:
comunicação REDUZ findings únicos). Critério: recall monotônico em k E
razão FP/TP ≤ 1,0 em k=5.

### E1 — audit fan-out read-only vs solo (só se E0 liberar)

Recall de defeitos semeados; DOIS estimandos separados: (i) B vs A a
WALL-CLOCK FIXO (mesma deadline, compute livre) e (ii) B vs C a
COMPUTE IGUAL (mesmos tokens agregados, tempo livre) — cada um com sua
hipótese; McNemar pareado, kill após 15 snapshots se B−C ≤ 0 no
estimando (ii).

### E2 — batch de itens de baixo acoplamento (só se E0 liberar)

Estratificação pré-registrada por acoplamento (Jaccard de arquivos +
grafo de import); hipótese pré-registrada como INTERAÇÃO — pergunta
experimental, NÃO claim: prever que qualquer vantagem de B, se
existir, apareça só no estrato low, e que B degrade qualidade no high;
kill se CI-green de B ficar >10pp abaixo de A.

### Kill geral de substrato

Mensagem cross-session perdida/duplicada = defeito registrado
(substrate-watch) e pausa; defeito ≠ resultado.

## Claim máxima sustentável (doutrina)

O único resultado que o experimento poderia sustentar é sobre
**QUALIDADE DE AUDITORIA** (recall de defeitos semeados, medido a
orçamento de tempo igualado entre braços) — NUNCA um claim de
velocidade/throughput do framework (AGENTS.md no-speed-claim);
"a orçamento de tempo igualado" é condição de controle do experimento,
não afirmação de desempenho. v1.4.0 publica com "experimental: fleet
patterns (bateria pré-registrada; E0 executado)" — nunca claim sem
evidência.

Assinado por: __________________ (Owner, GPG)
