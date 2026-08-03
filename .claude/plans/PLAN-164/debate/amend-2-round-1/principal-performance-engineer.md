---
round: 1
archetype: Principal Performance Engineer
skill: performance-engineering
agent_persona: Principal Performance Engineer (core archetype)
generated_at: 2026-08-03T19:40:00Z
---

## Verdict

ADJUST — a escalada upward é correta e está sub-argumentada, mas os números da
proposta estão desatualizados, o p95 é estatisticamente inválido (censurado), e
o alvo 180 fica ABAIXO do p95 populacional estimado.

## Summary (≤ 3 bullets)

- **O que a proposta tenta fazer:** aplicar o gatilho de recalibração do
  AMEND-1 §3 (≥10 casos saudáveis) para subir o par de timeout 120/150 →
  180/210, via nova emenda com cerimônia.
- **Onde é forte:** a direção está certa e o diagnóstico de censura à direita
  está correto — a proposta identificou o mecanismo. A rejeição das
  alternativas (b) env-knob e (c) esperar mais amostras é bem argumentada:
  (c) em particular está exatamente certa, e pelo motivo certo.
- **Onde é fraca:** três falhas independentes, cada uma bloqueante. (1) Os
  números estão errados AGORA — refiz a medição e obtenho n=20, não 14; 7
  case-F, não 3. (2) O p95 de 121.2s é o p95 dos SOBREVIVENTES; usá-lo como
  base de "1.5× folga" reaplica o viés que a própria proposta diagnosticou.
  (3) A proposta afirma que `test_pair_rail_timeout_invariant.py` "passa sem
  edição" — é falso, o teste tem os valores 120/150 hard-coded e vai vermelho
  em 4 asserções.

## Risks

Ordenados por severidade.

---

**R-PERF1 — CRITICAL — Os números da proposta não reproduzem; o dataset se
moveu durante o próprio debate.**

Rodei a query normativa do §3 sobre a união dos logs
(`audit-log-2026-0*.jsonl` + `audit-log.jsonl`), em duas ordens de arquivo, e
obtive:

| Métrica | Proposta | Medido por mim |
|---|---|---|
| n saudáveis | 14 (A:10, B:4) | **20** (A:14, B:6) |
| case-F no período | 3 | **7** (6 pós-uplift + 1 pré) |
| mediana | 65.5s | **75.0s** (sobreviventes) / **92s** (populacional) |
| máximo observado | 120.0s | 119.917s (via `wall_ns`) |
| p95 "interpolado" | 121.2s | 119.8s (`quantiles` exclusive, n=20) |

A causa é diagnosticável e é o achado mais interessante da minha verificação:
as 6 amostras extras e 4 dos F's são da sessão `d2c626bc` entre
19:00:31Z e 19:16:53Z de hoje — **a sessão deste debate**. Os agentes deste
round, ao escreverem seus arquivos de critique, dispararam o rail vivo e
geraram amostras. O instrumento de medição é a coisa medida.

Isso não invalida a proposta, mas torna o número não-auditável: qualquer
pessoa que reproduza a query depois da cerimônia obterá um terceiro número, e
a emenda estará citando um valor que nunca mais se reproduz.

*Mitigação:* a emenda deve citar um SNAPSHOT CONGELADO — as latências brutas
inline no texto do ADR mais o sha256 do arquivo de snapshot — e não apenas a
receita da query. Um número derivado de um dataset vivo não é um número
decidido; é uma leitura de relógio.

---

**R-PERF2 — CRITICAL — O p95 de 121.2s é o p95 dos sobreviventes. Multiplicar
por 1.5 não corrige o viés; o 1.5 já foi gasto pela censura.**

Esta é a falha estatística central e ela inverte a conclusão da proposta.

O fator 1.5 do AMEND-1 foi calibrado sobre um dataset **não-censurado**: o
probe N=9 do §2 mediu `codex exec` diretamente, sem cap, então aquele p95 de
~75s era um p95 populacional honesto e 1.5× era folga real. O dataset de
agora é censurado em 120s por construção — todo review mais lento vira F e
some. O p95 calculado sobre os que sobreviveram é um **limite inferior
severamente enviesado** do p95 verdadeiro. Aplicar 1.5× a um limite inferior
produz um número que não tem a semântica de folga que o AMEND-1 pretendia.

Quantificando (MLE censurado, stdlib-only, tipo-I em T=120.14s; usei
`wall_ns` dos eventos, que dá resolução de nanossegundos e existe nos 27
pares — a query normativa usa `ts` e joga fora essa precisão):

População pós-uplift: **n=26, 20 observados, 6 censurados → taxa de censura
23.1%.**

Quantis não-paramétricos corrigidos por censura:

| quantil | valor | nota |
|---|---|---|
| p50 | 92s | estimável |
| **p75** | **120s** | **estimável — já ESTÁ no budget** |
| p90 / p95 / p99 | >120s | **NÃO estimável** (além do horizonte) |

O enquadramento da proposta — "p95 se aproxima do budget" — subestima o
problema por dois quantis inteiros. Não é o p95 que encosta em 120s: é o
**p75**. Quase um quarto dos reviews já não cabe.

Ajuste paramétrico da cauda:

| modelo | p95 | p99 | P(timeout @180) |
|---|---|---|---|
| lognormal | **196.6s** | 275.7s | **7.1%** |
| Weibull | 159.9s | 188.6s | 1.7% |

**180 fica abaixo do p95 estimado pelo modelo lognormal.** Um budget que fica
sob o p95 não é "1.5× de folga sobre o p95" — é aproximadamente o p93. E se
aplicássemos a regra do AMEND-1 honestamente ao p95 populacional, 1.5× daria
240s (Weibull) a 295s (lognormal) — não 180.

*Mitigação:* trocar o critério. Ver Must-fix 3.

---

**R-PERF3 — HIGH — A alegação de que o teste do invariante passa sem edição é
falsa; o escopo do sentinel está incompleto.**

A proposta afirma: *"Mantém o invariante TESTADO `registration >= internal +
30` (`test_pair_rail_timeout_invariant.py` passa sem edição — o teste
verifica a desigualdade, não literais)."*

O teste verifica **ambos**. Ele tem quatro invariantes, não um. Os
invariantes 1-3 são estruturais (kernel==template, margem ≥30, statusMessage
presente), mas o invariante 4 —
`test_ratified_absolute_values`, `.claude/hooks/tests/test_pair_rail_timeout_invariant.py:236` —
assere igualdade exata contra constantes hard-coded no arquivo:

```python
_RATIFIED_INTERNAL_S = 120        # linha 103
_RATIFIED_REGISTRATION_S = 150    # linha 104
```

Com 180/210 o teste falha em quatro asserções: o seam do default (180≠120), os
dois literais de fallback (`['180','180']≠['120','120']`), e o timeout de
registro nos dois arquivos (210.0≠150.0). Confirmei que ele está verde hoje
(`4 passed`), o que prova que é sensível aos literais e não vacuamente verde.

E o docstring do teste (linhas 24-28) antecipou exatamente esta situação:

> *"A deliberate recalibration (ADR-110-AMEND-1 trigger: >=10 healthy cases ->
> p95 revisit) must edit THIS test in the same change — that is the contract,
> not an inconvenience."*

O autor do AMEND-1 desenhou o teste para forçar esta emenda a tocá-lo. A
proposta leu o invariante 2 e parou.

O impacto operacional é concreto: o escopo do sentinel da cerimônia está
faltando um arquivo. Ou o land falha em `touched − scope ≠ ∅`, ou pior — se o
escopo for frouxo, a suíte vai vermelha pós-land.

*Mitigação:* incluir `.claude/hooks/tests/test_pair_rail_timeout_invariant.py`
no escopo do sentinel e atualizar as duas constantes mais o docstring §14.4.
Verifiquei que as cópias em `staged/rail-pack/` e `worktrees/plan165/` são
byte-idênticas à viva — decidir explicitamente se entram no escopo (a staged é
histórica pós-land do rail-pack; a de worktree pode conflitar no merge do
PLAN-165).

---

**R-PERF4 — HIGH — Existe uma terceira camada de timeout que nenhum dos dois
AMENDs considera, e ela já ratificou 240s para esta mesma classe de trabalho.**

`.claude/hooks/_lib/adapters/codex.py:151-155` define:

```python
DEFAULT_TIMEOUT_SIMPLE_S: int = 75
DEFAULT_TIMEOUT_AUDIT_S: int = 240
```

com `_resolve_timeout_s()` roteando entre elas por classe de prompt. O
framework **já decidiu**, em outra superfície, que um dispatch codex de classe
audit precisa de 240s. Um review de pair-rail sobre um diff canônico é
inequivocamente classe audit.

Há duas consequências. A primeira é de consistência: a proposta está pedindo
180 para uma operação que o próprio repositório já dimensionou em 240 noutro
lugar, sem citar nem reconciliar esse precedente. A segunda é documental —
o docstring de `_resolve_timeout_s` (linhas 212-214) afirma:

> *"Used by ``scripts/codex_invoke.py`` and ``check_pair_rail.py`` so the
> routing logic lives ONLY here."*

Isso é **falso**. Grep em `check_pair_rail.py` por `_resolve_timeout_s`,
`_classify_prompt_complexity` e `DEFAULT_TIMEOUT` retorna vazio; o hook lê seu
próprio env seam (L1716-1722) e passa `timeout_s` direto ao
`subprocess(..., timeout=timeout_s)` na L1038. É a mesma classe de stale-claim
que o pair-rail já pegou no SPEC em S282. Benigno hoje — se fosse verdade,
prompts curtos capariam em 75s e o cap de 120 do hook nunca dispararia — mas é
uma armadilha ativa para o próximo leitor, que pode concluir que mexer em
`CEO_PAIR_RAIL_TIMEOUT_S` é suficiente ou inócuo.

*Mitigação:* a emenda cita `DEFAULT_TIMEOUT_AUDIT_S = 240` como precedente
interno, corrige o docstring stale (ou registra a correção como residual
nomeado), e nomeia a unificação das duas superfícies como dívida futura.

---

**R-PERF5 — MEDIUM — As duas subpopulações têm distribuições materialmente
diferentes, e a que importa é a mais lenta.**

Estratificando por sessão:

| sessão | n | mediana | taxa de F | regime |
|---|---|---|---|---|
| `aef441ac` (31/07) | 13 | 61s | 2/15 = 13% | sessão mais leve |
| `d2c626bc` (03/08) | 6 | 105s | 4/10 = **40%** | multi-agente sob carga |

A mediana quase dobra e a taxa de fail-open triplica. Isso reproduz o achado
do AMEND-1 §2 (a amostra "UNDER LOAD" foi a mais lenta do probe N=9: 75.1s
contra ~35s idle), agora com evidência de produção.

O ponto que decide: o regime multi-agente sob carga é exatamente quando um
edit canônico pesado acontece e é exatamente quando o rail mais importa. Um
budget calibrado sobre a mistura das duas populações sub-serve o regime
crítico. Ajustando só à população sob carga, P(timeout@180) sobe para 9.0%
(lognormal).

*Mitigação:* declarar na emenda que a calibração usa a população sob carga
como referência conservadora, não a mistura.

---

**R-PERF6 — MEDIUM — A query normativa tem duas rotas de perda silenciosa
que a correção "união de logs" não fecha.**

A proposta corrige a rotação, o que é necessário mas insuficiente.

*(a) Ordenação por nome ≠ ordenação por tempo.* O glob lexicográfico ordena
`audit-log-2026-08-1.jsonl` **antes** de `audit-log-2026-08.jsonl`, mas por
mtime a ordem é inversa (02/08 vs 03/08). O algoritmo do §3 é
ordem-dependente: `expected.pop(key)` só casa se o `expected` já foi visto.
Um par que cruze essa fronteira tem o `case` silenciosamente descartado.
Rodei as duas ordens e hoje ambas dão n=20 — o bug está armado, não disparado.
A correção robusta não é ordenar melhor: é tornar o algoritmo
ordem-independente (colher todos os `expected` num dict, depois casar), o que
mata a classe inteira.

*(b) Eventos sem `review_id` somem.* O filtro `if not key[1] ... continue`
descarta silenciosamente. Encontrei **11 case-F sem `review_id`** (todos de
27/07, pré-uplift, portanto corretamente fora da análise). Benigno hoje, mas
significa que a query **não consegue calcular a taxa de fail-open** — ela só
conta sobreviventes. Como a decisão de escalada depende criticamente dessa
taxa (R-PERF2), é um buraco no instrumento que decide.

*Mitigação:* ver Must-fix 4 e a resposta a AQ2.

---

**R-PERF7 — LOW — O statusMessage "~3 min" descreve o budget, não a
experiência.**

Com internal 180, a espera típica continua sendo ~92s (p50 populacional).
"may take up to ~3 min" é honesto sobre o teto e pessimista sobre o caso
comum. Não é errado, mas se o número final subir para 240 a mensagem vira
"~4 min", o que soa a travamento. Preferível ancorar no caso típico e nomear o
teto: algo como "cross-model review (typ. ~1.5 min, up to N min)".

## Must-fix (blocking)

1. **Refazer a medição e congelar o snapshot.** Os números da proposta (n=14,
   3 F's, p95 121.2, mediana 65.5) não reproduzem contra o log de hoje. A
   emenda deve citar as latências brutas inline, o n, a contagem de F, o
   ponto de censura e o sha256 do arquivo de snapshot — e declarar que o
   snapshot foi tirado antes da cerimônia. Sem isso, o número da emenda é
   irreproduzível por construção (R-PERF1).

2. **Corrigir o escopo do sentinel: `test_pair_rail_timeout_invariant.py`
   entra.** A afirmação de que o teste passa sem edição é falsa; ele falha em
   4 asserções. Atualizar `_RATIFIED_INTERNAL_S`, `_RATIFIED_REGISTRATION_S` e
   o docstring §14.4 no mesmo commit, e decidir explicitamente sobre as cópias
   em `staged/rail-pack/` e `worktrees/plan165/` (R-PERF3).

3. **Trocar o critério de decisão de "1.5× p95" para "P(timeout) ≤ 5% sob
   estimativa censurada", e subir o número.** A regra 1.5× é indefensável
   sobre uma amostra censurada — o fator já foi consumido pelo viés. O
   critério de taxa de fail-open é diretamente interpretável, verificável
   ex-post (basta contar F/(F+saudáveis) no log) e não depende de escolher p95
   versus p99 nem de um multiplicador arbitrário.

   Sob esse critério, com os dados de hoje:

   | budget | P(timeout) lognormal | Weibull | veredito |
   |---|---|---|---|
   | 150 | 13.6% | 7.9% | reprovado |
   | **180 (proposto)** | **7.1%** | 1.7% | **reprovado** |
   | 210 | 3.8% | 0.2% | aprovado, margem fina |
   | **240** | **2.0%** | **0.0%** | **aprovado** |

   **Recomendo internal 240 / registration 270.** Três linhas independentes
   convergem: P(timeout) = 2.0% no pior modelo; 1.5× o p95 Weibull = 240
   exato; e `DEFAULT_TIMEOUT_AUDIT_S = 240` já é o valor ratificado no
   repositório para esta mesma classe de dispatch (R-PERF4). Aceito
   **210/240** como fallback se a UX de 4 minutos for julgada inaceitável —
   mas então a emenda deve registrar que 210 foi escolhido contra a evidência
   estatística por razão de UX, e não fingir que 210 é o número que a medição
   indicou.

   Rejeito 180 em qualquer forma: fica sob o p95 estimado e deixa 7% de
   fail-open, que é o ciclo near-miss→F que a própria proposta diz querer
   evitar em (a).

4. **Substituir a query do §3 por um script versionado que trate censura.**
   Ver AQ2 — mas o requisito bloqueante é que o script emita a taxa de censura
   e os quantis marcados como estimáveis/não-estimáveis. Uma query que reporta
   "p95 = 121.2s" sobre uma amostra 23% censurada, sem qualificar, vai
   produzir a mesma decisão errada na próxima recalibração (R-PERF2, R-PERF6).

5. **Registrar a taxa de fail-open observada como o gatilho da próxima
   recalibração, junto com o p95.** O AMEND-1 §3 dispara em "≥10 casos
   saudáveis", o que é uma condição sobre os SOBREVIVENTES — por construção
   ela nunca observa a cauda. O gatilho correto é sobre a taxa: se
   F/(F+saudáveis) > 10% numa janela de ≥20 tentativas, escalar. Isso fecha o
   defeito estrutural do gatilho atual.

## Nice-to-have (advisory)

1. **Usar `wall_ns` em vez de `ts` no cálculo de latência.** Os eventos
   `pair_rail_review_expected` e `pair_rail_case` carregam ambos `wall_ns`
   (epoch em nanossegundos) — confirmei presença nos 27 pares. A query
   normativa usa `ts`, que tem resolução de 1 segundo. A diferença é
   materialmente informativa: o máximo observado não é "120.0s = o budget",
   é **119.917s — 83 milissegundos abaixo do cap**. O caso mais lento que
   sobreviveu passou por menos de um décimo de segundo.

2. **Registrar os tempos de censura observados.** Os 6 F's pós-uplift batem em
   120.140-120.165s: o overhead entre o cap disparar e o evento ser escrito é
   ~150ms, estável. Útil para dimensionar a margem das camadas.

3. **Estratificar o snapshot por sessão** na emenda, para que a próxima
   recalibração veja a heterogeneidade de carga (R-PERF5) em vez de reduzir
   tudo a um número agregado.

4. **Reconciliar o statusMessage com o p50 populacional** (R-PERF7).

5. **Nomear a unificação das superfícies de timeout como dívida.** Se o rail
   passasse a chamar `_resolve_timeout_s()`, o docstring de `codex.py` viraria
   verdade e haveria uma fonte única. Fora de escopo aqui; vale um
   `# CEO-DEBT:`.

## Unseen by the original plan

1. **O p75 já está no budget, não o p95.** A proposta enquadra como "p95 se
   aproxima do budget". Corrigido por censura, o p75 populacional É 120s. A
   escalada é mais urgente do que a proposta argumenta — mas o alvo escolhido
   é baixo demais precisamente porque o enquadramento subestimou o problema.
   A proposta se prejudicou por não levar a própria análise de censura até o
   fim.

2. **A sessão de debate contaminou o dataset da decisão.** Seis das vinte
   amostras saudáveis e quatro dos sete F's foram gerados pelos agentes deste
   round enquanto o debate corria (R-PERF1). Isso é uma propriedade estrutural
   deste rail — qualquer sessão que edite arquivos canônicos gera amostras — e
   deveria ser um parágrafo de método na emenda, não uma surpresa.

3. **Prova positiva de que a margem de 30s entre camadas nunca foi violada.**
   27 eventos `expected` e 27 `case` correspondentes: todo review que começou
   terminou com um evento de caso registrado. **Zero kills do harness.** Isso
   valida empiricamente a escolha do AMEND-1 e é evidência direta para AQ3 —
   ver abaixo. A proposta não usa esse dado, que é o mais forte que tem em
   mãos para defender a arquitetura em camadas.

4. **Kills do harness seriam invisíveis no log.** Corolário do item 3: se o
   harness matar o hook, não há `pair_rail_case` — nem F. A taxa de censura de
   23% é um limite inferior sob a hipótese de que a margem segura. Hoje o
   pareamento 27/27 prova que segurou; mas se a margem de 30s um dia for
   insuficiente, o fail-open resultante é **silencioso** — não aparece nem
   como F. Vale um residual nomeado no §4 da emenda.

5. **O gatilho "≥10 casos saudáveis" é estruturalmente cego à cauda.** Ele
   condiciona em sobreviver. Um rail que piorasse até 90% de timeout demoraria
   *mais* para disparar a recalibração, não menos, porque os saudáveis
   acumulam mais devagar. A proposta chega perto disso ao rejeitar a
   alternativa (c) — "esperar não melhora a estimativa" está exatamente certo
   — mas não conecta o argumento ao gatilho que o produziu (Must-fix 5).

6. **`precondition_met=False` em todos os 27 eventos**, inclusive nos casos A
   e B que completaram. Não sei o que esse campo deveria significar e não
   investiguei — fora do meu escopo. Registro porque um campo booleano
   constante ou é morto ou está errado, e ambos importam para quem lê esses
   eventos como evidência de governança.

## What I would NOT change

1. **A decisão de escalar upward.** Está correta e a evidência é mais forte do
   que a proposta alega. Não deixe minha crítica ao número virar argumento
   para não mexer.

2. **A rejeição da alternativa (c) "esperar mais amostras", e o raciocínio.**
   "A censura à direita garante que amostras saudáveis futuras não revelam a
   cauda" é a frase estatisticamente mais correta do documento. É exatamente o
   motivo pelo qual esperar não ajuda — e, ironicamente, é o mesmo raciocínio
   que invalida o p95 de 121.2s que a proposta usou.

3. **A rejeição da alternativa (b) env-knob como mecanismo de calibração.**
   Institucionalizar o knob converteria uma decisão de governança em estado
   per-máquina invisível. O AMEND-1 §4(i) já aceitou o knob como residual de
   fail-open; promovê-lo a mecanismo inverteria o contrato.

4. **Manter o clamp `>600` intocado.** Mesmo com internal 240, 600 deixa fator
   2.5× de espaço. Não há razão para tocá-lo nesta emenda, e a semântica de
   reset-para-default (§4(ii)) é uma verruga conhecida que não piora aqui.

5. **A margem de 30s entre camadas.** Empiricamente validada em 27/27 (Unseen
   3). Ela deve ser preservada como diferença absoluta, não convertida em
   percentual — o overhead que ela cobre (startup do Python, redaction,
   validação do verdict) é aproximadamente constante, não proporcional ao
   budget.

6. **A arquitetura em camadas em si** (hook detém o arm do timeout, harness
   sobrevive ao hook). É o que faz o timeout ser diagnosticável como case-F em
   vez de um kill silencioso, e é a razão pela qual eu tenho dados para
   escrever este critique.

---

## Respostas diretas às perguntas do debate

**AQ1 — 180/210 vs 150/180: algum critério que eu não pesei?**

Sim, quatro.

*(i) O p95 que você usou é dos sobreviventes.* O critério "1.5× p95" tinha
semântica válida no AMEND-1 porque aquele dataset não era censurado. Aqui o
1.5 já foi gasto pelo viés. 180 não é 1.5× o p95 — é aproximadamente o p93.

*(ii) Nenhuma das duas opções passa num critério de taxa de fail-open.* 150 dá
13.6%, 180 dá 7.1% (lognormal, população agregada; 9.0% na população sob
carga). A pergunta "180 ou 150" é a pergunta errada: ambos ficam sob o p95
estimado. A resposta é 240, com 210 como fallback declaradamente movido por
UX.

*(iii) Consistência interna.* `DEFAULT_TIMEOUT_AUDIT_S = 240` já existe no
repositório para dispatch codex de classe audit. Você está pedindo 180 para
uma operação que o framework já dimensionou em 240.

*(iv) Heterogeneidade de carga.* Calibrar sobre a mistura sub-serve o regime
multi-agente, que é onde a taxa de F é 40% e onde o rail mais importa.

Sobre o custo de errar para baixo, que a proposta pesa corretamente em (a): o
custo de uma re-emenda é uma cerimônia inteira. Mas o custo real de 180 não é
a re-emenda — é os ~7% de edits canônicos que passam sem review no intervalo,
silenciosamente, cada um deles um fail-open que o rail existe para impedir.

**AQ2 — texto basta, ou o §3 precisa de um script versionado?**

Script versionado, e o argumento a favor é mais forte do que você formulou —
mas o script sozinho não resolve o problema que você tem.

A rotação é a menor das três falhas do instrumento. As outras duas são a
ordem-dependência do glob (R-PERF6a) e o descarte silencioso de eventos sem
`review_id` (R-PERF6b, que impede calcular a taxa de censura — o número que
mais importa). E acima de todas está R-PERF1: **um script versionado ainda
produz um número diferente a cada execução**, porque o log é vivo e cresce
enquanto se debate.

Então: `.claude/scripts/local/pair-rail-latency.py`, com contrato mínimo de
(1) união de logs por descoberta, não por caminho literal; (2) join
ordem-independente em duas passadas; (3) contagem explícita de F e da taxa de
censura; (4) quantis marcados como estimáveis ou não-estimáveis contra o
horizonte de censura; (5) uso de `wall_ns` quando presente; (6) emissão de um
**snapshot com sha256** que a emenda cita. É o (6) que fecha a classe — o
script torna a receita reprodutível, o snapshot torna o *número* auditável.

Um detalhe de governança: o script é uma superfície nova de decisão. Se ele
tiver um bug de quantil, a próxima recalibração herda o bug com aparência de
rigor. Vale um teste-espelho em `.claude/hooks/tests/` com um dataset
sintético de censura conhecida — dado que o repo já exige teste-espelho para
código Tier-1, e este script vai alimentar decisões de ADR.

**AQ3 — o registro a 210s fica abaixo de algum teto duro do Claude Code?
Precisa de sonda antes da cerimônia?**

Tenho evidência empírica forte e um limite que não consigo fechar sozinho.

*O que os dados provam:* 27 eventos `expected` e 27 `case` correspondentes —
**pareamento perfeito, zero kills do harness** com registro a 150s. Isso
prova que o harness honrou 150s em todas as invocações reais e que a margem
de 30s cobriu o overhead. Também é evidência indireta de que o campo `timeout`
é respeitado, não silenciosamente clampado para baixo — se o harness clampasse
para, digamos, 60s, veríamos `expected` órfãos.

*O que os dados não provam:* que 210 ou 270 também são honrados. O precedente
mais alto que encontrei no kernel é o próprio pair-rail a 150s, seguido de
`codex_review_user_code.py` a 130s. **Nenhum hook registrado acima de 150s
existe hoje** — 210 e 270 são território não-testado, e não achei
documentação local de um teto duro.

*Recomendação: sim, sonda, e ela é barata.* Registre temporariamente um hook
trivial que dorme N segundos e emite um evento ao terminar, com N acima do
alvo; se o evento aparecer, o teto está acima de N. O sinal de falha é
inequívoco e não custa nada: `sleep 250 && emit`. Uma sonda de dois minutos
antes da cerimônia é infinitamente mais barata que descobrir o teto depois do
land — porque um kill do harness é **silencioso** (Unseen 4): não gera case-F,
não gera nada. O modo de falha exato que a arquitetura em camadas do AMEND-1
foi desenhada para tornar impossível voltaria pela porta dos fundos, e você
só descobriria contando reviews que não aconteceram.

---

## Nota de honestidade estatística

n=26 com 6 censurados é uma amostra pequena, e devo declarar a incerteza em
vez de escondê-la atrás de três casas decimais.

O intervalo entre as estimativas de p95 — 160s (Weibull) e 197s (lognormal) —
é **incerteza de modelo, não ruído de medição**: eu não sei qual família de
cauda descreve a latência do Codex, e n=26 não distingue (as
log-verossimilhanças são praticamente empatadas: −105.6 contra −106.0). Um
ajuste com cauda mais pesada daria um número maior; um mais leve, menor.

Ancorei a recomendação no lognormal, o mais conservador, deliberadamente. A
razão é assimetria de custo, não preferência estatística: errar para cima
custa segundos de espera numa sessão que o protocolo já desencoraja; errar
para baixo custa um fail-open silencioso num gate de governança pré-write. Sob
custo assimétrico, calibrar contra o modelo pessimista é a decisão correta
mesmo quando ele provavelmente exagera.

O que eu afirmo com confiança alta, e que não depende de escolher modelo, são
os fatos não-paramétricos: a taxa de censura é 23.1%, o p75 populacional está
em 120s, e o p95 **não é estimável** a partir desta amostra sem um modelo. É
por isso que Must-fix 3 troca o critério de "1.5× p95" — um número que a
amostra não sustenta — por uma taxa de fail-open alvo, que ela sustenta e que
qualquer pessoa pode auditar contando eventos no log.
