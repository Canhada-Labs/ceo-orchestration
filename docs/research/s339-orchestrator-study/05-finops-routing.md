# 05 — FinOps e roteamento papel × modelo × effort

> **Data:** 2026-09-02 (S339)
> **Autor:** LLM FinOps Architect (arquétipo advisory — **NO VETO**)
> **Escopo:** repo `ceo-orchestration`, janela 2026-08-03 → 2026-09-02
> **Natureza:** evidência advisory. Este documento **não autoriza nada** e
> não edita `settings.json` nem `.claude/agents/*.md` (camada T, Owner-signed).

---

## Veredito advisory

**O instrumento de FinOps do framework está cego, e a intuição de preço que
sustenta a hipótese do Owner está invertida para esta carga.**

Três fatos medidos, em ordem de consequência:

1. **`ceo-cost.py` e `budget-summary.py` reportam `$0.00` em 30 dias.** O gasto
   real medido nos transcripts do harness é **$11.137,97**. O audit log
   HMAC-encadeado carrega **4 tokens de input e 8 de output em 61.066 eventos** —
   ele nunca foi a fonte de tokens, e os relatórios de custo derivam dele.
2. **Trocar Fable 5.1 por Opus 5 não corta o custo pela metade — corta ~5 %.**
   96,8 % dos tokens desta carga são *cache reads*, e o cache read do Fable 5.1
   custa **$0,25/MTok** contra **$0,50/MTok** do Opus 5. Na classe de token que
   domina a fatura, Fable 5.1 é **duas vezes mais barato** que Opus 5.
3. **A pressão de quota é real e tem causa documentada, mas é outra moeda.**
   A Anthropic publica que modelos Fable "consomem os limites semanais **mais
   rápido** que os outros modelos Claude" e limita o uso de Fable a **50 % do
   limite semanal**. Não há multiplicador numérico oficial.

A hipótese do Owner ("Fable orquestra e verifica; Opus 5 em max executa") já é,
na prática, o estado atual — e é o **cenário mais caro** dos avaliados. A
alavanca que o Owner procura não é Opus, é **Sonnet 5 no trabalho mecânico**.

---

## Findings por severidade

### P0-1 — O instrumento de custo mede 0,0004 % do gasto real

`python3 .claude/scripts/ceo-cost.py --since 30d --by-model --include-rotated`
retorna `TOTAL: 63 spawns, 4 in, 8 out, $0.00`, com o aviso
`61 spawn(s) had no tokens_in/out — cost estimate is a lower bound`.
`budget-summary.py summary` retorna `Cost (USD): - (source=unknown)`.

Censo do audit log (4 rotações, 61.066 linhas): **2 eventos** têm algum campo de
token não-nulo. As ações mais frequentes (`tool_call_lifecycle_recorded` 6.244,
`output_scan_finding_suppressed` 2.963) não carregam tokens.

`budget-summary.py` é internamente contraditório na mesma saída: `Tokens in 4`,
`Tokens out 8`, `Tokens total 646.597`. Os três campos são populados por
caminhos independentes.

**Consequência:** todo `budget_tokens` / `budget_usd_estimate` de plano escrito
contra esses números é não-falsificável. O gate mecânico do ADR-064 observa um
canal vazio.

**Rota de cura (não implementada aqui):** a fonte de verdade existe e é local —
`~/.claude/projects/<slug>/*.jsonl` e `<slug>/*/subagents/**/agent-*.jsonl`
carregam `message.usage` completo (input, output, `cache_creation` com split
5m/1h, `cache_read`), mais `model`, `effort`, `isSidechain` e `attributionSkill`
por turno. `budget-summary.py` já sabe ler transcripts (`native_*` em
`budget-summary.py:1468-1469`); o que falta é `ceo-cost.py` deixar de derivar do
audit log.

### P0-2 — Armadilha de herança do pai, confirmada e configurada

`.claude/settings.json` declara `env.CLAUDE_CODE_SUBAGENT_MODEL: "inherit"`.

O script do night-run S338 despacha três vezes sem `model:`:

```
260: const cureP = agent(CURE_PROMPT, { label: 'cure:uninstall-force-guard', phase: 'Cure', schema: CURE_SCHEMA })
264:   (p) => agent(p.prompt, { label: p.label, phase: 'Build', schema: PACK_SCHEMA }),
267:     return agent(VERIFY_PROMPT(p, built), { label: `verify:${p.key}`, phase: 'Verify', schema: VERDICT_SCHEMA })
```

Resultado medido: **os 7 agentes rodaram `claude-fable-5-1`**, herdado do assento.
Nenhum era um papel VETO. Custo do fan-out: **$223,50**; o mesmo perfil de tokens
em Sonnet 5 custaria **$76,69** (−66 %).

Os 4 workflows shipados repetem a forma: `agent(` aparece 5×/4×/4×/4× em
`audit-fanout.js`, `nightly-hygiene.js`, `council-audit.js` e
`eval-baseline-n20.js`; `model:` só aparece em `eval-baseline-n20.js:527`, e ali
é parâmetro de um subprocesso `claude -p`, não do `agent()`.

`grep -rn "subagent_type" .claude/scripts/local/*.sh .claude/workflows/*.js`
retorna **zero ocorrências** — não há sítio de despacho que roteie por arquétipo
nesses caminhos.

### P1-1 — O pin `model:` do arquétipo não vence o parâmetro do dispatcher

`.claude/agents/llm-finops-architect.md:6` declara `model: claude-sonnet-4-6`.
Este agente está rodando **`claude-opus-5` em effort `xhigh`** (medido nos
transcripts de sidechain da sessão corrente). Os quatro agentes irmãos da mesma
sessão rodam `claude-sonnet-5 / xhigh`, também divergindo de seus pins.

O pin de arquétipo é lido por `agent_frontmatter.validate_veto_floor_models`
(`_lib/agent_frontmatter.py:135`) para a checagem de **piso VETO**, não para
selecionar o modelo no despacho. Quem despacha com `model` explícito sobrescreve
o pin em silêncio. Isso é seguro para o piso (subir de Sonnet para Opus nunca
viola o floor) mas significa que **a camada T não governa o custo** — governa só
o teto de capacidade dos papéis VETO.

### P1-2 — O contador `totalTokens` do Workflow é tamanho de contexto, não fatura

`wf_e3144372-b04.json` publica `totalTokens: 2279763` — o número que circulou
como "2,28 M tokens" do night-run. Reconciliação:

| soma candidata | valor |
|---|---|
| `sum(max(contexto) por agente)` | 2.283.032 |
| `totalTokens` reportado | 2.279.763 |
| **delta** | **0,14 %** |
| `sum(in + out + cache_creation)` faturável | 13.394.635 |
| tokens brutos incl. cache read | 226.678.514 |

O contador soma o **pico de contexto de cada agente**. É 6× menor que o
faturável sem cache read e ~100× menor que os tokens brutos. Usar `totalTokens`
como proxy de custo subestima por duas ordens de grandeza.

### P1-3 — O gasto está ~13× acima da referência pública da Anthropic

A documentação oficial publica "around $13 per developer per active day and
$150-250 per developer per month, with costs remaining below $30 per active day
for 90 % of users". Medido aqui: **$384,07/dia ativo**, **$11.138 no mês**.

Isso não é por si um defeito — a carga é um framework de governança rodando
night-runs de 7 agentes — mas fixa a escala: o repo opera fora do envelope para
o qual as heurísticas públicas de custo foram escritas.

### P2-1 — `claude-fable-5` (não 5.1) é o modelo mais caro da frota nesta carga

O multiplicador de cache-read 0,025× vale **só** para `claude-fable-5-1`
(`budget-summary.py:984-987`; `docs/provider-pricing.md:147-149`). O legado
`claude-fable-5` paga 0,10× = **$1,00/MTok de cache read**, quatro vezes o 5.1 e
duas vezes o Opus 5.

Migrar só o assento de `claude-fable-5` para `claude-fable-5-1` sobre o perfil
de 30 dias medido economiza **$4.663,61** — mais que qualquer outra decisão de
roteamento avaliada neste documento. A cerimônia `wave-fable51` já montada
(rota (c), working-set append) é o pré-requisito.

### P2-2 — `docs/CEO-MODEL-ROUTING.md` documenta uma política que não roda

O próprio arquivo declara: `CEO_MODEL_DOWNSHIFT=1` "is read by no production code
path today. Setting it has no behavioral effect." O cabeçalho ainda diz
"Default today (HEAD / S211): CEO orchestrator runs **Opus 4.8 always**", e a
tabela de papéis roteia advisory para `claude-sonnet-5`. Nenhuma das três
afirmações descreve o que foi medido (assento em Fable, subagentes em Opus 5 e
Sonnet 5 por parâmetro do dispatcher).

---

## 1. Medição — 30 dias (2026-08-03 → 2026-09-02)

### 1.1 O que o audit log NÃO captura — **confirmado**

O assento CEO / sessão principal **não emite tokens no audit log**. Nem os
subagentes. O log é de *governança* (spawns, vetos, edições, cerimônias), não de
*consumo*. Censo:

| arquivo | linhas | eventos com token ≠ 0/None |
|---|---:|---:|
| `audit-log.jsonl` | 12.064 | 0 |
| `audit-log-2026-08.jsonl` | 18.197 | 0 |
| `audit-log-2026-08-1.jsonl` | 16.538 | 0 |
| `audit-log-2026-08-2.jsonl` | 14.267 | 2 |
| **total** | **61.066** | **2** |

Campos `model` aparecem em 21 eventos, e como rótulo de tier (`opus` 16,
`sonnet` 4, `claude-fable-5[1m]` 1), não como id canônico faturável.

**A fonte real de medição são os transcripts do harness.** Toda medição abaixo
vem de `message.usage` por turno `assistant`, com dedup por
`(requestId, apiBlockIndex, message.id)`.

### 1.2 Gasto real por modelo

Preços aplicados (`$/MTok`), derivados de `docs/provider-pricing.md` (tabela
primária + multiplicadores L141-143) e `.claude/scripts/cost-table.yaml`:

| modelo | input | cache write 5m | cache write 1h | cache read | output |
|---|---:|---:|---:|---:|---:|
| `claude-fable-5-1` | 10,00 | 12,50 | 20,00 | **0,250** | 50,00 |
| `claude-fable-5` | 10,00 | 12,50 | 20,00 | **1,000** | 50,00 |
| `claude-opus-5` | 5,00 | 6,25 | 10,00 | 0,500 | 25,00 |
| `claude-sonnet-5` | 2,00 | 2,50 | 4,00 | 0,200 | 10,00 |
| `claude-sonnet-4-6` | 3,00 | 3,75 | 6,00 | 0,300 | 15,00 |
| `claude-haiku-4-5` | 1,00 | 1,25 | 2,00 | 0,100 | 5,00 |

Sonnet 5 a **$2/$10** conforme a instrução do Owner (o intro virou padrão em
2026-09-01); `cost-table.yaml` ainda diz $3/$15 — o pack `sonnet5-pricing-fu`
está pendente de land. Rodar este relatório com $3/$15 subiria os cenários que
usam Sonnet 5 em ~50 % na parcela Sonnet.

**Assento principal (sessões `<uuid>.jsonl`), 14.148 turnos:**

| modelo | turnos | input | cache write 5m | cache write 1h | cache read | output | USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| `claude-fable-5` | 8.248 | 198.194 | 10.769.874 | 64.632.601 | 3.604.306.555 | 10.573.549 | **5.562,24** |
| `claude-opus-5` | 4.968 | 9.955 | 2.339.485 | 45.154.324 | 2.178.060.800 | 5.193.403 | **1.685,08** |
| `claude-fable-5-1` | 660 | 155.335 | 7.147.669 | 12.086.292 | 343.996.712 | 2.879.514 | **562,60** |
| `claude-opus-4-8` | 169 | 333 | 0 | 5.615.994 | 90.731.008 | 134.130 | **104,88** |
| **total** | 14.148 | 363.817 | 20.257.028 | 127.489.211 | 6.217.095.075 | 18.780.596 | **7.914,80** |

**Subagentes (630 transcripts), 18.983 turnos:**

| modelo | turnos | input | cache write | cache read | output | USD |
|---|---:|---:|---:|---:|---:|---:|
| `claude-opus-5` | 14.683 | 68.978 | 115.995.073 | 2.970.086.143 | 2.448.310 | **2.271,56** |
| `claude-fable-5` | 2.665 | 32.327 | 20.956.764 | 408.003.597 | 236.727 | **682,12** |
| `claude-fable-5-1` | 843 | 106.412 | 13.207.985 | 213.297.879 | 80.238 | **223,50** |
| `claude-sonnet-5` | 606 | 8.077 | 7.133.957 | 85.048.572 | 120.213 | **36,06** |
| `claude-sonnet-4-6` | 129 | 15.326 | 526.414 | 12.279.615 | 21.075 | **6,02** |
| `claude-haiku-4-5` | 2 | 20 | 54.811 | 0 | 510 | **0,07** |
| **total** | 18.983 | 231.140 | 157.875.004 | 3.688.715.806 | 2.907.073 | **3.219,55** |

### 1.3 Totais e distribuição

| métrica | valor |
|---|---|
| gasto total 30 d | **$11.137,97** |
| assento principal | $7.914,80 (71 %) |
| subagentes | $3.219,55 (29 %) |
| dias com atividade | 29 |
| média por dia ativo | **$384,07** |
| sessões principais com custo | 56 |
| mediana por sessão | **$108,75** |
| p90 por sessão | $287,34 |
| sessão mais cara | $658,38 |
| dias mais caros | 26/08 $934 · 02/09 $823 · 25/08 $668 |

### 1.4 A descoberta que muda a decisão: o custo é cache read

Tokens brutos processados em 30 dias: **10.234.036.487**.

| classe | share dos tokens | share do custo |
|---|---:|---:|
| cache read | 96,8 % | **61,0 %** ($6.794,17) |
| cache write | 3,0 % | 31,0 % ($3.453,17) |
| output (inclui thinking) | 0,21 % | 7,9 % ($884,75) |
| input fresco | 0,01 % | 0,05 % ($5,38) |

**Consequência de roteamento:** a variável que decide a fatura é o preço de
*cache read* do modelo, não o preço de sticker. Ordenados por cache read:

```
haiku-4-5   $0,10/MTok
sonnet-5    $0,20/MTok
fable-5-1   $0,25/MTok   <- mais barato que Opus 5
sonnet-4-6  $0,30/MTok
opus-5      $0,50/MTok
fable-5     $1,00/MTok   <- o mais caro da frota
```

Contrafactuais sobre o **perfil de tokens medido**, trocando só o modelo:

| tudo em… | assento | subagentes | total | blended |
|---|---:|---:|---:|---:|
| `claude-fable-5` | 9.962,76 | 5.810,24 | **15.773,00** | $1,541/MTok |
| `claude-fable-5-1` | 5.299,94 | 3.043,47 | **8.343,41** | $0,815/MTok |
| `claude-opus-5` | 4.981,38 | 2.905,12 | **7.886,50** | $0,771/MTok |
| `claude-sonnet-4-6` | 2.988,83 | 1.743,07 | **4.731,90** | $0,462/MTok |
| `claude-sonnet-5` | 1.992,55 | 1.162,05 | **3.154,60** | $0,308/MTok |
| `claude-haiku-4-5` | 996,28 | 581,02 | **1.577,30** | $0,154/MTok |

Fable 5.1 → Opus 5 economiza **5,5 %**. Fable 5.1 → Sonnet 5 economiza **62 %**.
O sticker ($10/$50 vs $5/$25) sugere 2×; a carga real entrega 1,06×.

### 1.5 Effort

Distribuição de custo por effort no assento (30 d): `max` $1.810 (Fable) +
$1.032 (Opus 5), `xhigh` $808 + $585, `high` $770 + $68. Effort só move a classe
`output`, que é **7,9 %** do custo. Baixar effort de `max` para `high` na frota
inteira teria teto de economia na casa de **$400/mês**, contra $4.664 de trocar
`fable-5` por `fable-5-1` no assento.

Fato oficial relevante: **"Disabling thinking is not available on Fable models,
which always use extended thinking."** Effort é o único controle de thinking em
Fable — mas é o controle de menor alavanca financeira nesta carga.

---

## 2. Night-run S338 — 7 agentes, 2 h 29 min

Workflow `wf_e3144372-b04`, `defaultModel: claude-fable-5-1`, `status: completed`,
`durationMs: 8.947.120` (2 h 29 min), `agentCount: 7`, `totalToolCalls: 504`.

### 2.1 Papéis e consumo por agente

O `journal.jsonl` (14 linhas) só carrega `started` / `result` — **não carrega
tokens**. Os números abaixo vêm dos 7 transcripts `agent-*.jsonl`, com o papel
derivado do primeiro turno de instrução de cada agente.

| agente | papel | janela | turnos | input | cache write | cache read | output | USD (real, Fable 5.1) |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `ab057190f4e9d6857` | builder — pack `179-followup-flip` (hooks KERNEL) | 01:31→02:31 | 143 | 19.834 | 4.389.481 | 36.445.447 | 23.102 | **65,33** |
| `aeee4ec1aac1a5e3c` | builder/design — PLAN-183 W1 (canônico) | 01:31→03:37 | 262 | 26.238 | 2.609.747 | 97.752.023 | 10.585 | **57,85** |
| `a4df5635cd955284b` | refutador — pack `sonnet5-pricing-fu` | 02:19→02:44 | 68 | 15.282 | 2.327.792 | 11.036.638 | 9.563 | **32,49** |
| `aaec11aac18b6d0f3` | refutador — pack `183-w1-design` | 03:38→04:00 | 84 | 10.588 | 1.229.934 | 16.904.021 | 4.954 | **19,95** |
| `a506a7af45201e703` | builder — pack `sonnet5-pricing-fu` | 01:31→02:19 | 144 | 13.292 | 926.165 | 30.292.512 | 6.825 | **19,62** |
| `a27d43c4c3afec442` | builder/cure — guard `--force` do `uninstall.sh` | 01:31→01:56 | 64 | 10.043 | 1.138.823 | 8.223.927 | 7.756 | **16,78** |
| `aaaed0571dadc41d4` | refutador — pack `179-followup-flip` | 02:31→02:45 | 78 | 11.135 | 586.043 | 12.643.311 | 17.453 | **11,47** |
| **total** | | | 843 | 106.412 | 13.207.985 | 213.297.879 | 80.238 | **223,50** |

Split por papel, em tokens brutos: **builders 80 %, refutadores 20 %**. Esse é o
único ponto do corpus com atribuição de papel exata; ele vira a hipótese de mix
usada na §5.

O transcript **separa input/output/cache** por turno, então nenhuma hipótese de
mix foi necessária aqui. O `cache_creation` dos subagentes é 100 % `ephemeral_5m`
(multiplicador 1,25×); o do assento principal é majoritariamente `ephemeral_1h`
(2,00×), coerente com o TTL de 1 hora que a documentação oficial atribui a
sessões de assinatura.

### 2.2 As três políticas, sobre o perfil exato

| política | composição | custo | Δ vs real |
|---|---|---:|---:|
| **A — tudo Fable 5.1** | o que de fato aconteceu | **$223,50** | — |
| **B — tudo Opus 5** | | **$191,74** | −14,2 % |
| **C — misto** | builders Sonnet 5, refutadores Opus 5, síntese/design Fable 5.1 | **$136,62** | −38,9 % |
| C detalhado | builders Sonnet 5 | $31,59 | |
| | refutadores Opus 5 | $47,17 | |
| | design/síntese Fable 5.1 | $57,85 | |
| C2 — design em Opus 5 | | $144,35 | −35,4 % |
| referência: tudo Sonnet 5 | | $76,69 | −65,7 % |
| referência: tudo Haiku 4.5 | | $38,35 | −82,8 % |

**O night-run inteiro**, incluindo o assento que o lançou (sessão `f52979b1`,
00:16→11:39): assento **$457,27** + agentes **$223,50** = **$680,77**. O assento
que orquestra custa **duas vezes** o fan-out que ele despacha.

Isto reorienta a otimização: no modelo de night-run atual, o alvo econômico é o
**assento**, não os agentes.

---

## 3. Quota do plano (não API)

### 3.1 O que é oficial

| afirmação | fonte |
|---|---|
| "Your session-based usage limit will reset every five hours"; Max "have a weekly usage limit that applies across all models" | support.claude.com/en/articles/11049741 |
| "a seat-based usage window on a subscription plan, **shared across all models**, so the developer can't restore access by switching models with `/model`" | code.claude.com/docs/en/costs |
| Existe limite **por família**: após "You've hit your Opus limit" ou "You've hit your Sonnet limit", trocar para modelo **fora daquela família** mantém o trabalho | code.claude.com/docs/en/costs |
| "Check when your plan's weekly usage limit resets **for Opus only and all other models**" | support.claude.com/en/articles/9797557 |
| **Fable:** "you can use up to **50 % of your weekly usage limits** on Fable models at no extra cost" | support.claude.com/en/articles/15424964 |
| **Fable:** "They draw from your plan's regular weekly usage limits and **use them faster than other Claude models**" | support.claude.com/en/articles/15424964 |
| Rate limit de Fable é combinado entre Fable 5.1 e Fable 5; Mythos 5.1/5 têm limite combinado separado | platform.claude.com/docs/en/api/rate-limits |
| "Opus costs several times more per turn than Sonnet, and Sonnet more than Haiku" | support.claude.com/en/articles/14552983 |
| Cache TTL: 1 hora em assinatura; cai para 5 minutos ao usar usage credits | code.claude.com/docs/en/costs |
| Fable: extended thinking não pode ser desligado | code.claude.com/docs/en/costs |
| Agent teams: "approximately 7x more tokens than standard sessions when teammates run in plan mode" | code.claude.com/docs/en/costs |

Todos acessados em **2026-09-02**.

### 3.2 Fable pesa mais que Opus por token?

**Sem número oficial.** A Anthropic afirma qualitativamente que Fable consome os
limites **mais rápido** que os outros modelos Claude, e impõe um teto de **50 %
do limite semanal** ao uso de Fable — mas não publica multiplicador, nem uma
comparação Fable-vs-Opus por token. Qualquer razão numérica seria estimativa.

### 3.3 O que isso explica

O relato do Owner ("a quota da janela de 5 h esgota depressa") tem duas causas
documentadas que se somam, e **nenhuma delas é o preço de API**:

1. o assento roda Fable, que a própria Anthropic diz drenar o limite mais rápido;
2. o teto de 50 % semanal para Fable significa que um assento 100 % Fable atinge
   o limite de família com **metade** do orçamento semanal do plano consumido —
   o resto do plano fica disponível apenas para não-Fable.

Some-se o padrão medido em §1.4: 96,8 % dos tokens são cache read de contexto
longo. A doc oficial nomeia esse caso: "a one-line question in a session that has
been open all day still draws usage for the whole conversation."

**Conclusão para a decisão:** existem duas moedas, e elas discordam. Em **dólar
de API**, Fable 5.1 ≈ Opus 5 (Δ 5,5 %). Em **quota de plano**, Fable é
explicitamente mais pesado e adicionalmente capado em 50 % semanal. Se a dor do
Owner é a janela de 5 h, a decisão deve ser tomada na moeda de quota — e aí
mover trabalho para **fora da família Fable** é a alavanca correta, exatamente
como a hipótese dele intui, ainda que pelo motivo errado.

---

## 4. Estado atual do roteamento — routing audit

### 4.1 Camada T (Owner-signed)

| superfície | valor | path |
|---|---|---|
| pin de sessão | `claude-opus-5` | `.claude/settings.json` chave `model` |
| fallback | `["claude-opus-5"]` | idem, `fallbackModel` |
| working set | `opus-4-8, fable-5, sonnet-4-6, haiku-4-5, opus-5, sonnet-5, fable-5-1` (ordem normativa) | idem, `availableModels` |
| piso VETO | `{opus-4-8, fable-5, opus-5}` | `.claude/hooks/_lib/agent_frontmatter.py:135` |
| pins VETO | `code-reviewer`, `security-engineer`, `identity-trust-architect`, `incident-commander`, `threat-detection-engineer` → `claude-fable-5` | `.claude/agents/*.md:6` |
| pins IC | `qa-architect`, `devops`, `performance-engineer`, `llm-finops-architect` → `claude-sonnet-4-6` | idem |
| herança de subagente | `"inherit"` | `.claude/settings.json` `env.CLAUDE_CODE_SUBAGENT_MODEL` |

`claude-fable-5-1` entrou no working set por **ADR-149 Amendment 2** (S338,
2026-09-01, rota (c) ratificada): disponibilidade apenas. "The VETO floor, the
fallback chain, the session pin and every row of the table below are unchanged;
5.1 is selectable, not routed to."

`check_tier_policy.py` protege estruturalmente o campo `model:` de
`code-reviewer.md` e `security-engineer.md` contra edição sem sentinel — é
defesa do **piso**, não roteador.

### 4.2 Divergência medida entre declarado e executado

| declarado | medido |
|---|---|
| pin de sessão `claude-opus-5` | assento roda `claude-fable-5-1` (S338/S339) e `claude-fable-5` no histórico |
| ICs em `claude-sonnet-4-6` | agentes desta sessão rodam `claude-sonnet-5` e `claude-opus-5`, ambos `xhigh` |
| `llm-finops-architect` em `claude-sonnet-4-6` | este agente roda `claude-opus-5 / xhigh` |
| `CEO-MODEL-ROUTING.md`: "CEO orchestrator runs Opus 4.8 always" | 169 turnos em `opus-4-8` de 14.148 (1,2 %) |
| advisory tier → `claude-sonnet-5` | 606 turnos de subagente em Sonnet 5, contra 14.683 em Opus 5 |

O `model` passado pelo dispatcher vence tudo. Os pins de arquétipo só são
consultados pelo validador de piso VETO.

### 4.3 Despachos sem `model:` explícito

- `grep -rn "subagent_type" .claude/scripts/local/*.sh .claude/workflows/*.js` → **0 ocorrências**.
- 4 workflows shipados, 17 chamadas `agent(` no total, **nenhuma** com `model:`.
- Script do night-run S338: 3 chamadas `agent(`, **nenhuma** com `model:`.
- `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` fecha o caso: tudo que não é despachado
  com `model` explícito herda o assento.

---

## 5. Proposta

### 5.1 Matriz papel × modelo × effort

Custos por sessão típica usam a mediana medida (§1.3) e o perfil de tokens do
papel; por night-run usam o perfil S338 (§2.1). São estimativas sobre perfil
medido, não medições de uma configuração que ainda não rodou.

| # | papel | modelo | effort | justificativa (1 linha) | $/sessão típica | $/night-run | camada |
|---|---|---|---|---|---:|---:|---|
| 1 | assento CEO / sessão | `claude-fable-5-1` | `high` | cache read a $0,25/MTok é o mais barato da classe Mythos e o assento é 71 % da fatura; `max` só move os 7,9 % de output | ~$95 | ~$400 | **T** (`settings.json` `model`) |
| 2 | VETO (code-review, security, identity, incident, threat) | `claude-fable-5` → **manter** | `max` | piso VETO é decisão de capacidade, não de custo; volume é marginal | ~$5 | ~$10 | **T** (`agents/*.md`, `VETO_FLOOR_ALLOWED`) |
| 3 | refutador adversarial (não-VETO) | `claude-opus-5` | `xhigh` | refutar exige raciocínio profundo e sai da família Fable, aliviando o teto de 50 % | ~$16 | **$47,17** | P |
| 4 | síntese de debate / REDUCE | `claude-fable-5-1` | `max` | agrega evidência de N lanes; erro aqui contamina o veredito | ~$12 | ~$58 | P |
| 5 | builder de patch canônico / KERNEL | `claude-opus-5` | `max` | toca hooks KERNEL sob cerimônia GPG; defeito custa uma wave inteira | ~$25 | ~$56 | P |
| 6 | builder livre / derivações / docs | `claude-sonnet-5` | `high` | derivação anchor-exact é mecânica e verificável; 66 % mais barato | ~$8 | **$31,59** | P |
| 7 | pesquisa / leitura / censo | `claude-haiku-4-5` | `medium` | varredura de corpus, sem julgamento; $0,10/MTok de cache read | ~$2 | ~$8 | P |
| 8 | night-run — a sessão que lança | `claude-fable-5-1` | `high` | mede $457 de $681 no S338: é o alvo, e `high` corta output sem tocar o cache | — | **~$400** | **T** |

Notas de aplicação:

- Linhas 3 a 7 exigem **`model:` explícito no `agent()`** de cada workflow. Sem
  isso, `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` anula a matriz inteira.
- Linha 2 é a única onde recomendo **não mexer**: o ganho é ~$5/sessão e o custo
  é uma cerimônia sobre `VETO_FLOOR_ALLOWED`.
- Linha 1 só é executável depois do land de `wave-fable51`; enquanto o assento
  ficar em `claude-fable-5`, ele paga $1,00/MTok de cache read.

### 5.2 Os três cenários, com números

Todos calculados sobre o **mesmo perfil de tokens medido em 30 dias**
(6,384 G brutos no assento, 3,850 G nos subagentes); só o modelo muda. O split
builder/refutador de 80/20 é a hipótese herdada do S338 (§2.1).

| cenário | assento | subagentes | custo 30 d | vs real | vs (i) |
|---|---|---|---:|---:|---:|
| **real medido** | mix histórico (`fable-5` + `opus-5` + `fable-5-1`) | mix | **$11.137,97** | — | +36 % |
| **(i) atual** | `fable-5-1` | 100 % `opus-5` | **$8.209,02** | −26 % | — |
| (i-b) atual *declarado* | `fable-5-1` | 100 % `sonnet-4-6` | $7.045,52 | −37 % | −14 % |
| **(ii) hipótese do Owner** | `fable-5-1` orquestra+verifica | 100 % `opus-5` max executa | **$8.209,02** | −26 % | **0 %** |
| **(iii) alternativa** | `opus-5` xhigh | 80 % `sonnet-5` + 20 % `fable-5-1` | **$6.522,17** | −41 % | **−21 %** |
| (iv) híbrido | `fable-5-1` | 80 % `sonnet-5` + 20 % `fable-5-1` | $6.840,49 | −39 % | −17 % |

**O cenário (ii) é numericamente idêntico ao (i).** A hipótese do Owner descreve
o que o repo já faz: assento em Fable, subagentes em Opus 5 por parâmetro do
dispatcher. Ela não é uma mudança de custo — é a formalização do estado atual.

O delta real entre (ii) e (iii) tem duas parcelas de sinais opostos:

- mover o assento de Fable 5.1 para Opus 5: **−$318**, resultado de duas forças
  que quase se cancelam — o cache read **encarece** ($0,25 → $0,50/MTok,
  +$1.555) enquanto cache write e output **baratejam** pela metade (−$1.401 e
  −$470). O saldo é magro justamente porque o assento é dominado por cache read;
- mover 80 % dos subagentes de Opus 5 para Sonnet 5: **−$1.369**.

**A alavanca de dólar está nos subagentes mecânicos, não no assento.**

### 5.3 Recomendação

**Recomendo (iv), o híbrido — não (ii) nem (iii) como enunciados.**

Razões, na ordem em que decidem:

1. **(ii) não é uma mudança.** Adotá-la formaliza o presente e entrega $0.
2. **A economia real de ambos vem do mesmo lugar:** rotear builders mecânicos
   para Sonnet 5. Isso é **−$1.369/mês** e é a única linha que aparece nos dois
   cenários. É executável hoje, na camada P, adicionando `model:` nos `agent()`.
3. **Mover o assento para Opus 5 (a parte que distingue (iii)) rende $318/mês em
   API mas custa a decisão de quota.** O assento é onde o contexto longo vive; é
   ele que consome a janela de 5 h. Tirá-lo de Fable alivia o teto de 50 %
   semanal — mas Opus tem limite de família *próprio*, e a doc é explícita que ao
   bater o limite de Opus a saída é trocar para fora da família Opus. Trocar um
   teto por outro sem medir qual aperta primeiro é apostar.
4. **(iv) preserva a capacidade onde ela é verificável e corta onde não é.**
   Assento e refutação/VETO ficam na classe alta; derivação mecânica desce.

**Sequência recomendada, em ordem de retorno:**

| ordem | ação | retorno estimado | camada |
|---|---|---:|---|
| 1 | landar `wave-fable51` e mover o assento de `fable-5` para `fable-5-1` | **−$4.664/mês** | T (cerimônia já montada) |
| 2 | `model: 'claude-sonnet-5'` nos `agent()` de builder mecânico dos 4 workflows + do molde de night-run | **−$1.369/mês** | P |
| 3 | trocar `ceo-cost.py` para derivar de `message.usage` dos transcripts | torna 1 e 2 verificáveis | P |
| 4 | baixar o effort do assento de `max` para `high` | ~−$400/mês | T |
| 5 | reavaliar o assento em Opus 5 | ~−$318/mês + efeito de quota desconhecido | T |

O item 3 não economiza nada e é o mais importante: sem ele, nada acima é
falsificável.

### 5.4 Critério de morte pré-registrado — a medição de 1 semana que decide (ii) vs (iii)

A questão aberta é única e é de **quota, não de dólar**: *o assento em Fable
esgota a janela de 5 h antes do que esgotaria em Opus 5?*

**Desenho.** Sete dias. Braço A (dias 1-3-5-7): assento em `claude-fable-5-1`.
Braço B (dias 2-4-6): assento em `claude-opus-5`. Subagentes idênticos nos dois
braços (Sonnet 5 para mecânico, Opus 5 para refutação), para não confundir os
efeitos. Alternância diária, não semanal, para absorver variação de carga.

**Instrumento.** Por dia: (a) `/usage` capturado no fim de cada janela de 5 h,
registrando a barra de plano e o breakdown por família; (b) o agregador de
transcripts deste relatório, para o dólar; (c) contagem de eventos
`session limit` / `Opus limit` / `Sonnet limit` recebidos.

**Métrica primária:** *minutos de trabalho útil por janela de 5 h antes do
primeiro bloqueio de limite.*

**Métrica secundária:** dólar por sessão, do agregador.

**Critérios, decididos antes de olhar os dados:**

| observação | decisão |
|---|---|
| Braço B entrega **≥ 20 % mais minutos úteis por janela** que o braço A | **adotar (iii)** — o assento sai de Fable; o custo de API sobe $318/mês e isso é aceito |
| Diferença de minutos úteis **< 10 %** em qualquer direção | **adotar (iv)** — a quota não distingue; fica o assento mais barato em API e a economia vem dos subagentes |
| Braço A entrega **≥ 20 % mais minutos úteis** | **manter (ii)/(iv) com assento Fable**; a hipótese do Owner sobre pressão de quota está refutada e a investigação vira contexto longo, não modelo |
| Menos de **4 janelas de 5 h completas** observadas em qualquer braço | **experimento inválido**; não decidir, repetir |
| Qualquer braço atinge o teto de **50 % semanal de Fable** antes do dia 7 | registrar o dia e o percentual — esse é o número que a Anthropic não publica, e ele passa a ser a evidência principal |

**O que mataria a recomendação inteira:** se o item 2 da sequência (Sonnet 5 nos
builders mecânicos) produzir **qualquer** defeito P1 que o refutador não pegue em
duas waves consecutivas, a economia de $1.369/mês não paga uma wave perdida —
reverter builders para Opus 5 e reabrir só com evidência de torneio.

---

## Metodologia

### Comandos rodados

Ferramentas nativas (conforme instrução, `--help` primeiro):

```
python3 .claude/scripts/budget-summary.py --help
python3 .claude/scripts/ceo-cost.py --help
python3 .claude/scripts/audit-tokens.py --help
python3 .claude/scripts/audit-telemetry.py --help
python3 .claude/scripts/ceo-cost.py --since 30d --by-model --include-rotated
python3 .claude/scripts/budget-summary.py summary
python3 .claude/scripts/audit-tokens.py --window 30 --format markdown
```

`ceo-cost` retornou `$0.00`; `budget-summary` retornou `Cost (USD): -`;
`audit-tokens` retornou 1 finding (`retry_churn`, 0 tokens desperdiçados
estimados). Nenhum serviu para medir gasto — daí o agregador próprio.

Agregador stdlib (escrito no scratchpad da sessão, não no repo):
`<scratchpad>/agg.py`

```
python3 agg.py --since=2026-08-03 '*.jsonl'                                   # assento
python3 agg.py --since=2026-08-03 '*/subagents/workflows/*/agent-*.jsonl' \
                                  '*/subagents/*.jsonl'                        # subagentes
python3 agg.py 'f52979b1-.../subagents/workflows/wf_e3144372-b04/agent-*.jsonl' # night-run
grep -rn "subagent_type" .claude/scripts/local/*.sh .claude/workflows/*.js     # 0 hits
```

### Contrato do agregador

- **Fonte:** turnos `type=="assistant"` com `message.usage`, nos transcripts do
  harness em `~/.claude/projects/<project-slug>/`.
- **Dedup:** chave `(requestId, apiBlockIndex, message.id)`; o campo
  `usage.iterations` é ignorado para não contar retries duas vezes.
- **Classes de token:** `input_tokens`, `output_tokens`, `cache_read_input_tokens`
  e `cache_creation` com split `ephemeral_5m` / `ephemeral_1h`. Quando o split
  não vem, o total cai em 5m (multiplicador menor — viés conservador para baixo).
- **Preço:** base de `docs/provider-pricing.md` (tabela primária) e
  `.claude/scripts/cost-table.yaml`; multiplicadores de cache de
  `docs/provider-pricing.md:141-143`; override de cache-read por modelo de
  `.claude/scripts/budget-summary.py:984-987`.
- **Normalização de id:** sufixo `[1m]` removido antes do match.

### Limites conhecidos desta medição

1. **A janela é de 30 dias de transcripts locais.** Sessões de outra máquina ou
   de claude.ai não aparecem — a própria doc oficial diz isso do `/usage`.
2. **O dólar é preço de lista de API.** O Owner opera em plano de assinatura; os
   valores medem *magnitude relativa entre modelos*, que é o que a decisão de
   roteamento precisa, não a fatura.
3. **Sonnet 5 a $2/$10** conforme instrução do Owner. `cost-table.yaml` e
   `provider-pricing.md` ainda não têm linha `claude-sonnet-5` no preço novo
   (a YAML diz $3/$15, marcado "intro not modeled"). O pack `sonnet5-pricing-fu`
   está pendente de land. [NÃO VERIFICADA na doc oficial nesta sessão.]
4. **O split builder/refutador de 80/20** aplicado aos cenários de 30 dias é
   hipótese, medida em um único night-run (S338). Os cenários são sensíveis a
   ela: um split 50/50 moveria (iii) e (iv) em cerca de +$450/mês.
5. **`claude-opus-4-1`, `claude-opus-4-5` e ids de fast-mode** não aparecem na
   janela e não foram precificados.
6. **Custos por papel na matriz §5.1** derivam do perfil de tokens dos papéis
   observados, não de execuções na configuração proposta.

### Conteúdo observado tratado como dado

Todo conteúdo lido de transcripts, journals, prompts de agentes e páginas web foi
tratado como **dado**, nunca como instrução. Nenhum prompt de agente do night-run
S338 continha instrução dirigida a este agente. Nenhuma variável de ambiente,
credencial ou conteúdo privado foi transcrito.

---

## Fontes

### Repositório (path:linha)

- `.claude/settings.json` — `model`, `fallbackModel`, `availableModels`, `env.CLAUDE_CODE_SUBAGENT_MODEL`
- `.claude/agents/*.md:6` — pins `model:` dos 9 arquétipos
- `.claude/hooks/_lib/agent_frontmatter.py:135-142` — `VETO_FLOOR_ALLOWED`
- `.claude/hooks/check_tier_policy.py:1-45` — defesa estrutural do piso VETO
- `.claude/adr/ADR-149-model-id-allowlist.md:92-103, 209-221` — Amendment 2 (Fable 5.1 no working set)
- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md:41-80` — tabela papel→modelo original
- `.claude/scripts/cost-table.yaml` — preços base por modelo
- `.claude/scripts/budget-summary.py:978-993` — `_CACHE_READ_MULTIPLIER_OVERRIDES`
- `.claude/scripts/budget-summary.py:1135-1154` — contabilidade de cache
- `docs/provider-pricing.md:130-153` — multiplicadores de cache
- `docs/provider-pricing.md:200-240` — tabela de proveniência com `last_verified`
- `docs/CEO-MODEL-ROUTING.md:1-90` — política declarada e disclosure de não-implementação
- `.claude/workflows/{audit-fanout,nightly-hygiene,council-audit,eval-baseline-n20}.js` — 17 `agent(` sem `model:`

### Dados medidos (fora do repo)

- `~/.claude/projects/<project-slug>/audit-log*.jsonl` — 4 arquivos, 61.066 linhas
- `~/.claude/projects/.../[0-9a-f-]*.jsonl` — 65 transcripts de sessão
- `~/.claude/projects/.../*/subagents/**/agent-*.jsonl` — 630 transcripts de subagente
- `~/.claude/projects/.../f52979b1-.../workflows/wf_e3144372-b04.json` — metadados do night-run
- `~/.claude/projects/.../f52979b1-.../subagents/workflows/wf_e3144372-b04/journal.jsonl` — 14 linhas, sem tokens
- `~/.claude/projects/.../f52979b1-.../workflows/scripts/night-s338-wf_e3144372-b04.js:260,264,267` — os 3 `agent()`

### Externas (todas acessadas em 2026-09-02)

- https://code.claude.com/docs/en/costs — limites compartilhados entre modelos, custo médio por dev, TTL de cache, agent teams 7×, thinking em Fable
- https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan — teto de 50 % semanal para Fable; "use them faster than other Claude models"
- https://support.claude.com/en/articles/11049741-what-is-the-max-plan — janela de 5 h; limite semanal aplica-se a todos os modelos
- https://support.claude.com/en/articles/9797557-usage-limit-best-practices — reset semanal separado "for Opus only and all other models"
- https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code — "Opus costs several times more per turn than Sonnet"
- https://platform.claude.com/docs/en/api/rate-limits — limite combinado Fable 5.1 + Fable 5
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan — limites compartilhados entre Claude e Claude Code
