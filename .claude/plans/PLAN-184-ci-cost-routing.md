---
id: PLAN-184
title: "Corte de custo de CI: filtro de paths e saida do runner pago"
status: draft
created: 2026-08-21
owner: CEO
depends_on: []
level: L3
budget_tokens: 110-210k (W0 30-60k; W1 50-90k; W2 20-40k; W3 10-20k)
budget_sessions: 2
context_risk: low
external_wait: "W3/AC-6 apenas — janela de OBSERVACAO retrospectiva de dados de billing (7 dias-calendario de faturamento acumulado, no molde ratificado no PLAN-180: janela de dados, nao estimativa de esforco). W0-W2 nao esperam nada externo."
eta_calendar: "W0-W2 = mesmo-dia a D+1 (CEO-only, sem espera externa); AC-6 fecha em D+7, e a espera e de DADOS de billing acumulando, nao de trabalho"
tags: [ci, custo, github-actions, runner, paths-filter, governanca]
---

# PLAN-184 — Corte de custo de CI

## 1. De onde isto veio, e o que exatamente foi medido

O CI da org bateu no teto de billing durante a janela **2026-08-01 a
2026-08-21 (21 dias)**. Os números da medição que autorizou este plano
(fonte única de verdade; este plano não os recalcula):

| Métrica | Valor |
|---|---|
| Minutos no runner pago 8-core (`Ceo`) | **14.291 min** |
| Custo bruto desses minutos | **US$ 314,40** (a US$ 0,022/min) |
| Faturado de fato | **US$ 200** |
| Minutos em `ubuntu-latest` | 3.124 min — **US$ 0** |

O corte em US$ 200 tem assinatura aritmética: o budget de Actions da org
estava em **US$ 200 com `prevent_further_usage=true`**, e a quantidade
faturada — **9090,909090 min** — é exatamente `200 / 0,022`. Ou seja: a
diferença entre US$ 314,40 e US$ 200 **não é economia, é trabalho que não
rodou**. O budget foi elevado para **US$ 400**, o que compra tempo mas
não resolve o gasto.

### Onde o dinheiro está

| Workflow | Minutos | Custo | % |
|---|---|---|---|
| `validate.yml` | 13.428 | **US$ 295,42** | **94%** (167 runs) |
| `coverage.yml` (repo público) | 464 | US$ 10,21 | — |
| `coverage.yml` (repo privado) | 399 | US$ 8,78 | — |

`coverage.yml` **já foi curado** (movido para nightly na S220) e não é
alvo deste plano. Verificado no disco: `coverage.yml:10-18` tem
`pull_request.paths` restrito a `.claude/hooks/**` + `.claude/scripts/**`
+ o próprio workflow, mais `schedule: 0 7 * * *`. **É o precedente
in-repo do que a W1 vai fazer** — e também a fonte de uma armadilha que a
§4 nomeia.

### A atribuição que decide o plano

| Tipo de commit | Runs | Minutos | Custo | % do custo |
|---|---|---|---|---|
| **Só docs/plans/ADR** | 106 | 10.407 | **US$ 228,95** | **77,7%** |
| Toca código | 61 | 2.994 | US$ 65,87 | 22,3% |

Ressalva registrada na própria medição: **os 61 de código estão
SUBESTIMADOS** — parte deles morreu em `queued` durante a janela de corte
de billing e contabilizou 0 min. **Debate r1 falsificou essa ressalva
como explicação suficiente — ver a nota de reconciliação abaixo.**

E o denominador bate com o comportamento do repositório: **236 commits em
`main` no período, 153 só-docs (64,8%) e 83 tocando código.** Este
bucket "tocando código" **contém a classe MISTA** (docs *e* código no
mesmo commit) — censo independente rodado no debate r1, janela
`08-01..08-22`, `--first-parent main`, classificado por prefixo de path:
**239 commits = 152 só-docs + 67 MISTOS (28%) + 20 só-código**. A classe
mista não muda a economia, mas **é a fronteira que o instrumento de
aceite tem de exercer** (AC-2b).

**Leitura honesta: 77,7% do custo de um runner de 8 núcleos é gasto
rodando 4 suítes de teste pesadas contra commits que não mudaram uma
linha de código.**

### Por job, por run

| Job | min/run | Paraleliza? |
|---|---|---|
| `hook-tests-python-matrix` (4 versões, 3.9–3.12) | **41,8** | sim (`-n auto`) |
| `hook-tests-dual-rail` (2 shards) | **15,5** | sim (`-n auto`) |
| `Governance, health, contamination, shellcheck` | **15,0** | sim (`-n auto`) |
| `Formal verification mutation harness` | **4,7** | **NÃO** (sem `-n`) |
| `E2E integration tests` | **3,4** | **NÃO** (sem `-n`) |

Custo por run: **US$ 1,44** nos jobs pesados, **US$ 0,33** no job de
governança.

Os dois jobs seriais foram verificados linha a linha no disco: o E2E roda
`python3 -m pytest tests/integration/ -v --tb=short`
(`validate.yml:1095`), mais `tier_policy_cli/tests/` e `tournament/tests/`
— **nenhum com `-n`**; e o formal roda `python3 -m pytest
tests/formal_verification/ -v --tb=short` (`validate.yml:1163`), também
sem `-n`. Os dois instalam **só** `pytest==8.*`, sem `pytest-xdist`.
**São 8 núcleos alugados para rodar um processo.**

### Nota de reconciliação (debate r1, P0) — esta tabela NÃO decide bucket

Contas rodadas no debate, todos os insumos vindos deste plano:

```
tabela por-job acima:  41,8 + 15,5 + 15,0 + 4,7 + 3,4 = 80,4 min/run
167 x 80,4 = 13.426,8  vs 13.428 medido   -> bate no AGREGADO
106 x 80,4 =  8.522,4  vs 10.407 medido   -> delta +1.884,6  (= 23,4 runs)
 61 x 80,4 =  4.904,4  vs  2.994 medido   -> delta -1.910,4  (= 23,8 runs)
```

Duas consequências, as duas ruins:

1. **A tabela por-job é a média por run, não uma medição independente:**
   `13.428 / 167 = 80,4`. Ela portanto **não carrega informação alguma**
   sobre em qual bucket (só-docs × código) os minutos caíram.
2. **A ressalva de `queued` acima não explica os deltas.** Se runs de
   código tivessem perdido minutos morrendo em `queued`, o agregado
   ficaria **abaixo** de 13.426,8. Ele não fica. Os deltas são quase
   simétricos e opostos — isso é **redistribuição**, e a hipótese barata
   a testar primeiro é **erro de classificação** de ~23-24 runs, não dois
   efeitos independentes.

É a **W0-US5**, e ela gateia os números da §2.

## 2. O escopo, tal como o Owner decidiu

> ### ⚠️ Base de tempo canônica: **US$/dia-calendário** (debate r1, P0)
>
> A medição cobre **21 dias**; as projeções abaixo vinham rotuladas
> "/mês"; a confirmação da W3 é uma janela de **7 dias**. Três bases, e
> nenhuma regra de conversão — o gate ">20% de divergência reabre o
> plano" (AC-6) dispararia **pelas unidades**, antes de qualquer efeito
> real do corte. Contas que mostram o tamanho do erro:
>
> ```
> custo só-docs  228,95 (21d)  ->  327,07 por 30 dias
> A1             193,97 (21d)  ->  277,10 por 30 dias
> janela W3 de 7d contra "/mês": razão 4,29x
> fatura esperada em 7 dias se o corte for 224/mês com residual 90/mês:
>   90/30*7 = US$ 21,00   (contra "US$ 224/mês" — 91% de "divergência")
> ```
>
> **Regra congelada (W0-US4):** todo número de custo deste plano é
> expresso em **US$/dia-calendário**; a conversão para qualquer janela é
> `US$/dia × dias-da-janela`. Rótulos "/mês" abaixo ficam entre
> parênteses como *leitura de 30 dias*, nunca como o número que fecha um
> AC.
>
> ### ⚠️ As magnitudes abaixo são **NÃO-DERIVADAS** até a W0-US5
>
> Elas repousam em **duas bases de custo por-run mutuamente
> inconsistentes** (nota de reconciliação da §1):
>
> ```
> A1 base MEDIDA  (228,95 - governança 15*106*0,022) = 193,97  <- "US$ 194"
> A1 base TABELA  (heavy 65,4 * 106 * 0,022)         = 152,51  <- 21% a menos
> A2 base TABELA  (8,1 * 167 * 0,022)                =  29,76  <- "US$ 30"
> sobreposição    (8,1 * 106 * 0,022)                =  18,89  <- "US$ 19"
> ```
>
> **O que sobrevive às duas bases, e é o que autoriza o plano:** a
> *direção*. A A1 é o termo dominante em qualquer leitura (US$ 194 ou
> US$ 153), e 77,7% do custo cai em commits que não tocam código.
> **O que não sobrevive:** a precisão da manchete. Ver **OQ-6**.

**A1 — filtro de paths nos 4 jobs pesados.**
`hook-tests-python-matrix`, `hook-tests-dual-rail`, `E2E integration
tests` e `Formal verification mutation harness` passam a rodar **somente
quando o código muda**. O job `Governance, health, contamination,
shellcheck` **continua rodando em TODO commit** — é ele que valida os
`.md` (`check-claude-md-claims.py`, `verify-counts.sh`, staleness,
contamination). Economia estimada: **US$ 9,24/dia** (`193,97 / 21`;
leitura de 30 dias: US$ 277) na base MEDIDA, ou **US$ 7,26/dia**
(`152,51 / 21`; 30 dias: US$ 218) na base TABELA. **NÃO-DERIVADA** até a
W0-US5.

**A2 — os 2 jobs que não paralelizam saem do runner pago.**
`E2E integration tests` e `Formal verification mutation harness` trocam
`runs-on: Ceo` por `runs-on: ubuntu-latest`. Economia estimada:
**US$ 1,42/dia** (`29,76 / 21`; leitura de 30 dias: US$ 43) — base
TABELA, **NÃO-DERIVADA**.

**Projeção declarada na medição: US$ 224 na janela de 21 dias =
US$ 10,67/dia de corte (71%); custo residual US$ 90/21d =
US$ 4,29/dia.** *(Os rótulos "/mês" do texto original eram totais de 21
dias mal-rotulados; a conversão correta para 30 dias é 224/21×30 =
US$ 320 e 90/21×30 = US$ 129.)*

**Pressuposto que a projeção carrega e que o AC-6 tem de preservar:** a
baseline de 13.428 min **já reflete** 47% de runs cancelados
(`concurrency.cancel-in-progress: true`, F6). Se a rota escolhida perder
o cancelamento, a baseline deixa de ser comparável e o AC-6 mede outra
coisa — é Check da W1 nos dois ramos.

### Ressalva de composição: A1 e A2 se sobrepõem (DERIVADA, a confirmar)

Os dois números foram estimados **independentemente**, e os dois jobs da
A2 estão **dentro** do conjunto que a A1 filtra. Compondo os componentes
da própria medição: a A2 economiza `(3,4 + 4,7) min × 167 runs × 0,022 =
US$ 29,8` **se a A1 não existir**; depois da A1 esses dois jobs só rodam
nos ~61 runs de código, e a economia marginal da A2 cai para
`8,1 × 61 × 0,022 ≈ US$ 11`. A sobreposição contada duas vezes é
`8,1 × 106 × 0,022 ≈ US$ 19`.

Isto é **derivação a partir dos componentes da medição, não uma medição
nova** — está aqui como claim a confirmar na W3, não como fato. A
consequência prática é de **ordem e expectativa**, não de escopo: a A1
entrega a quase totalidade do valor; a A2 vale **US$ 0,52/dia**
(`11 / 21`; leitura de 30 dias: US$ 16) marginais e **compra um risco de
timeout** (§5). O AC-6 fecha isso com a fatura real, que é o único número
que o Owner vai conferir — **na base US$/dia**.

## 3. O risco central: filtro que não vê o alvo

O modo de falha que importa **não é gastar demais — é um commit de código
passar sem teste**. É a classe dominante deste repositório: *guard verde
porque não vê o alvo* (S315: `check_contamination.py` deu
`✓ No contamination` sobre arquivos untracked que, para ele, não
existiam; um `grep` direto achou 14 ocorrências). Verde de escopo-vazio é
**indistinguível** de verde de conformidade na saída.

Um filtro de CI é exatamente esse instrumento: um guard cuja resposta
default decide se o teste roda. Daí a decisão de arquitetura desta wave:

> **Denylist (`paths-ignore`), nunca allowlist (`paths`).**
>
> - **Allowlist** — "rode só quando estes caminhos mudarem". Um diretório
>   de código NOVO, não previsto na lista, é **silenciosamente excluído**:
>   os testes pesados param de rodar sobre ele e ninguém vê. Falha na
>   direção perigosa.
> - **Denylist** — "pule só quando **todos** os caminhos alterados
>   estiverem na lista". Um diretório novo não está na lista de ignorados,
>   logo **roda**. O default para o desconhecido é *testar*.

Isso não substitui a prova. O AC-1/AC-2/AC-2b exigem **controle positivo
em TRÊS pontos** — só-código, só-docs e a fronteira MISTA —, e o AC-4
exige prova de inércia **por entrada** da denylist, porque a lista curta
que "parece óbvia" já está errada, como a §4 mostra.

### O que esta doutrina diz sobre o próprio repositório (debate r1)

A doutrina acima **indicta o estado atual do repo**, e isso fica escrito
em vez de silencioso. Medido:

```
$ grep -rn "paths-ignore" .github/ templates/     ->  zero ocorrências
workflows com `paths:` (allowlist): 13
  actionlint, adapter-live, benchmarks, chaos, coverage, formal-verify,
  mcp-smoke, otel-smoke, perf-profile, red-team, shadow-ci,
  smoke-install, translations-drift
desses, combinando `push:` + `paths:` corretamente: 11
  (todos acima menos coverage.yml e shadow-ci.yml, que são PR-only)
```

Duas leituras, as duas honestas:

1. **`paths-ignore` não tem UM precedente in-repo.** O mecanismo que esta
   wave escolhe é o único que nenhum gate deste repositório exercita
   hoje. Isso não o torna errado — torna a W1 a primeira execução dele
   aqui, e é razão para o controle positivo ser mecânico, não visual.
2. **13 gates vivos são allowlists**, incluindo `red-team.yml` e
   `coverage.yml`. Ou eles são risco aceito, ou são follow-up. **Não é
   suposição deste plano: é a OQ-9.**

## 4. Contraexemplo verificado: `docs/**` NÃO é inerte

A denylist que qualquer um escreveria de memória seria
`.claude/plans/**`, `.claude/adr/**`, `docs/**`, `*.md`. **`docs/**` está
errado, e a prova está no disco.**

`tests/integration/test_threat_model_coverage.py` — que roda no job
**`E2E integration tests`**, um dos quatro que a A1 filtra — lê o
**arquivo real** `docs/threat-model.md` do repositório
(`_REPO_ROOT = Path(__file__).resolve().parents[2]`, `THREAT_MODEL_REL =
Path("docs/threat-model.md")`, `:25-36`) e afirma sobre ele:

- `TestThreatModelStructure` (`:309-370`): status `accepted`, linha
  `Accepted-By:`, ≥8 riscos residuais, ≥33 cenários STRIDE, ≥5 cenários
  por categoria, linhas por-ADR para ADR-045..048;
- `TestThreatModelFileReferences` (`:373+`) — cujo próprio docstring diz
  *"Dead-reference = hard fail. Every cited file must exist."*

Consequências, as duas ruins:

1. **Um commit só-docs pode legitimamente ficar vermelho num job
   pesado.** Editar `docs/threat-model.md` quebra o E2E.
2. **Pior, e é a direção perigosa:** renomear ou apagar um ADR
   (`.claude/adr/**` — "só docs" por qualquer classificação ingênua)
   quebra `TestThreatModelFileReferences` por referência morta. Se
   `.claude/adr/**` entrar na denylist sem prova, esse vermelho **deixa
   de existir** e a referência morta entra em `main` calada.

**Portanto o conjunto da denylist é DERIVADO, nunca lembrado** (a
doutrina de conjunto-fechado deste repo: derive comportamentalmente,
não por padrão de texto). É a W0-US2.

### O mecanismo é EXISTÊNCIA, não conteúdo — e isso quebra a prova ingênua (debate r1, P0)

O detector é `validate_file_ref` (`test_threat_model_coverage.py:199-215`):
`target.is_file() or target.is_dir()`, mais um fallback de **prefixo**
(`for child in parent.iterdir(): if child.name.startswith(name)`).
**Nenhuma leitura de conteúdo.** Probe rodado no debate, contra o código
real, num diretório descartável:

```
baseline      full: True   bare: True
após MUTAÇÃO  full: True   bare: True    <- conteúdo destruído, VERDE
após RENAME   full: False  bare: True    <- o fallback startswith salva o `bare`
após DELETE   full: False  bare: False
```

(`full` = `.claude/adr/ADR-045-policy-as-code-engine.md`; `bare` =
`.claude/adr/ADR-045`. O `docs/threat-model.md` cita **36** caminhos de
ADR, nas duas formas.)

**Consequência direta sobre a W0-US2:** a prova (b) escrita como "mutar
um arquivo sob o caminho e rodar as suítes; verde ⇒ inerte"
**declararia `.claude/adr/** ` INERTE** — e a regressão que esta §4 foi
escrita para impedir passaria a ser invisível. A prova (b) tem de rodar
**DELETE e RENAME**, e o `Check:` tem de exigir o **VERMELHO**, não o
verde. A armadilha do prefixo é restrição na escolha do alvo: renomear
`ADR-045-x.md` → `ADR-045-x-v2.md` mantém a referência `bare` verde, logo
o alvo do teste tem de ser um cujo sumiço seja de fato observável.

**Mesmo mecanismo, outra vítima:** `.github/**` também **passaria** na
prova (b) — mutar um YAML deixa as quatro suítes verdes. Por isso
`.github/**` é exclusão dura da denylist (AC-4), e não candidato.

### O que a governança continua cobrindo (e por que isso encolhe o risco)

Verificado nos steps do job de governança, que **não** é filtrado: ele já
roda, em Python **3.12** (`validate.yml:327`), com `-n auto`:

- `.claude/hooks/tests/` (`validate.yml:334-342`);
- `.claude/scripts/tests/` + `.claude/scripts/optimizer/tests/`
  (`validate.yml:419-425`);
- `tests/unit`, `.claude/hooks/_lib/tests`, `swarm`, `replay`,
  `tests/test_federation`, `mcp-server`, `detectors`, `predict-budget`,
  `tests/forensic`, `tests/synthetic` (`validate.yml:440-466`).

Logo, o que um commit só-docs **perde** ao pular os 4 pesados é, e só é:
(i) as outras três versões de Python (3.9/3.10/3.11); (ii) as duas pernas
`CEO_NATIVE_SUBAGENTS=0|1`; (iii) `tests/integration/`,
`tests/formal_verification/`, `tier_policy_cli/tests/`,
`tournament/tests/`. O item (iii) é onde mora o contraexemplo do
`docs/threat-model.md` — o que confirma que a análise é necessária, não
decorativa.

Este parágrafo é **leitura de YAML**, e a W0-US2 tem de confirmá-lo
comportamentalmente antes de qualquer entrada entrar na denylist.

## 5. Fatos de infraestrutura verificados nesta sessão

Cada um foi conferido com comando; o comando está citado.

**F1 — `main` não tem branch protection nem rulesets.**

```
$ gh api repos/Canhada-Labs/ceo-orchestration/branches/main/protection
{"message":"Branch not protected", ... "status":"404"}
$ gh api repos/Canhada-Labs/ceo-orchestration/rulesets
[]
$ gh api repos/Canhada-Labs/ceo-orchestration/rules/branches/main
[]
```

**Por que isto importa:** a armadilha clássica de filtro de paths é o
*required status check* que nunca reporta. Um job pulado por `paths:` não
emite check nenhum; se ele for exigido pela branch protection, o PR fica
travado para sempre. **Aqui isso NÃO se aplica** — não há proteção nem
regra a satisfazer.

**Ressalva durável, para quem ler este plano depois:** o dia em que
alguém ligar branch protection com required checks, este filtro vira
deadlock. Quem ligar tem de escolher entre não exigir os 4 jobs pesados
ou usar a Rota B (§6), onde o job aparece como `skipped` em vez de
ausente. Está escrito aqui porque a decisão de hoje é segura **por causa
de um estado do repositório que pode mudar sem aviso**.

**F2 — 100% dos runs de `validate.yml` na janela vieram de `push` em
`main`. Zero de `pull_request`.**

```
$ gh run list --workflow=validate.yml --limit 200 --json event,createdAt,headBranch,conclusion
  total listados: 200 | na janela 08-01..08-21: 167
  por evento: {'push': 167}
  por branch: [('main', 167)]
  por conclusao: {'failure': 31, 'cancelled': 79, 'success': 57}
```

Os 167 batem exatamente com os 167 runs da medição. **Consequência de
projeto, e é a mais importante da §5:** um filtro que cubra só
`pull_request` — que é a forma exata do `coverage.yml:11-15`, o
precedente in-repo — seria **100% morto** neste repositório. O filtro
tem de cobrir o gatilho `push`.

**F3 — o template do adopter usa `ubuntu-latest`; esta mudança não o
afeta.** `templates/.github/workflows/validate.yml.template:22` diz
`runs-on: ubuntu-latest` e `:23` `timeout-minutes: 5`. Os únicos
`runs-on: Ceo` do repositório são seis, todos em arquivos vivos:

```
$ grep -rn "runs-on: Ceo" .github/workflows/
.github/workflows/coverage.yml:30
.github/workflows/validate.yml:27    (governanca)
.github/workflows/validate.yml:1078  (E2E integration tests)
.github/workflows/validate.yml:1139  (formal verification)
.github/workflows/validate.yml:1412  (hook-tests-dual-rail)
.github/workflows/validate.yml:1447  (hook-tests-python-matrix)
```

O runner pago é infraestrutura **nossa**, nunca entregue. A W1/W2 não
tocam `templates/`, e o AC-7 assere isso.

**F4 — adicionar um arquivo de workflow REDDA o job de governança se a
contagem não for atualizada no mesmo commit.** `verify-counts.sh`
deriva `workflows` como contagem **exata** de `*.yml` em
`.github/workflows/` (`:324-326`) e a compara, com **tolerância 0**,
contra a célula de tabela `("workflows", "exact", r'^Workflows\b')`
(`:724`). A claim viva é `docs/CTO-GUIDE.md:46`:
`| Workflows | 22 | ls .github/workflows/*.yml | wc -l |`.

Isto **não é um bloqueio**, é uma edição de uma linha — e é uma boa
notícia: "esqueci de atualizar o doc" vira **build vermelho**, não drift
silencioso. Está registrado porque decide o custo real da Rota C (§6).

**F5 — os timeouts atuais, por job** (`timeout-minutes` no
`validate.yml`): governança **25** (`:34`), `integration-tests` **8**
(`:1079`), `formal-verification-mutation-harness` **10** (`:1142`),
`hook-tests-dual-rail` **20** (`:1413`), `hook-tests-python-matrix` **25**
(`:1448`).

**F6 — 79 dos 167 runs (47%) terminaram `cancelled`.** O rótulo é
ambíguo por construção: `concurrency.cancel-in-progress: true`
(`validate.yml:11-13`), estouro de `timeout-minutes` e o corte de billing
**compartilham o mesmo rótulo** (a lição do repo é explícita: timeout de
job aparece como `cancelled`, não `failure`). Minutos queimados antes de
um cancelamento **são cobrados**. Não desagreguei as causas e **não estou
afirmando** que isso seja desperdício — está registrado como OQ-4, fora
do escopo deste plano.

---

> Os fatos **F7..F11** entraram no debate round-1. Mesma regra: cada um
> foi conferido com comando, e o comando está citado.

**F7 — `integration-tests` é o único dos 4 pesados SEM bloco
`permissions:` próprio: ele herda do nível do workflow.**

```
$ grep -n "permissions:" .github/workflows/validate.yml
16:permissions:          <- nível do workflow (:16-17 = contents: read)
1143:    permissions:     <- formal-verification
1187:    permissions:     <- opus-4-7-profiler-smoke
1414:    permissions:     <- hook-tests-dual-rail
1449:    permissions:     <- hook-tests-python-matrix
1514:    permissions:     <- hook-stdout-schema-oracle
```

`integration-tests` começa em `:1071` e vai de `timeout-minutes: 8`
(`:1079`) **direto para `steps:`**. Num arquivo novo sem `permissions:`
no nível do workflow, esse job passaria a rodar com o escopo **DEFAULT**
do repositório para o `GITHUB_TOKEN` — um alargamento silencioso de
privilégio, no meio de um plano de custo. E **nada vigia isso**:
`grep -n permissions .claude/scripts/check-action-sha-drift.py` não
devolve nada, e `actionlint` não exige presença de `permissions`.

**Cura adotada (custo zero, e independe da rota):** dar ao
`integration-tests` um bloco `permissions: contents: read` **próprio,
ANTES do split**, para que ele não dependa de herança ao mudar de
arquivo. Mais `permissions:` no nível do workflow novo, com Check.

**F8 — `validate.yml` tem SETE jobs, não cinco.**

```
$ grep -n "^  [a-z0-9-]*:" .github/workflows/validate.yml
20: validate | 1071: integration-tests | 1121: formal-verification-mutation-harness
1178: opus-4-7-profiler-smoke | 1410: hook-tests-dual-rail
1445: hook-tests-python-matrix | 1505: hook-stdout-schema-oracle
```

Os dois não citados até aqui — `opus-4-7-profiler-smoke` (`:1180`
`runs-on: ubuntu-latest`, `timeout-minutes: 28`) e
`hook-stdout-schema-oracle` (`:1509` `ubuntu-latest`, `timeout: 10`) —
já rodam de graça e **FICAM onde estão**. O split move quatro jobs e
deixa três. Está escrito porque um inventário errado é como um job some
sem ninguém notar.

**F9 — o precedente de filtro deste repo é `push:` + `paths:`, e
`paths-ignore` não tem nenhum.** Números na §3. O molde a copiar para o
gatilho é qualquer um dos 11 (`smoke-install.yml` e `red-team.yml` são os
mais próximos em forma); o molde a copiar para **concorrência** é
`coverage.yml:21-23` (`group: coverage-${{ github.ref }}` +
`cancel-in-progress: true`); o molde para **recuperação** é
`coverage.yml:18` (`workflow_dispatch:`); o molde para **auto-disparo** é
`coverage.yml:11-14`, que inclui **o próprio arquivo** no `paths:`.

**F10 — as superfícies derivadas que a Rota C move são QUATRO, e três
delas não são vigiadas.** A afirmação anterior deste plano — "o único
custo novo (F4) é uma linha, e é mecanicamente vigiado" — era falsa.

| Superfície | O que quebra | Vigiado? |
|---|---|---|
| `docs/CTO-GUIDE.md:46` (`Workflows 22`) | contagem 22→23 | **SIM** — `verify-counts.sh:324-326,724`, tolerância 0 ⇒ build vermelho |
| `README.md:8` (badge de CI → `validate.yml`) | o badge deixa de representar os 4 pesados: **fica verde com o pesado vermelho** | **NÃO** |
| `.claude/adr/ADR-021:132` ("`validate.yml` with an 8-minute timeout") + `ADR-050:73-74` ("`validate.yml` adds `hook-tests-dual-rail`") | arquivo e (na W2) o próprio timeout mudam | **NÃO** |
| `.github/workflows/GOVERNANCE-MAP.md` | precisa de linha nova | **NÃO** |

E o GOVERNANCE-MAP **já está stale antes desta mudança**:

```
yml files: 22 | linhas de inventário no MAP: 20
faltando no MAP: ['ownership-nightly.yml', 'supply-chain-watch.yml']
```

O badge é o item que dói: é exatamente a classe que este plano diz
combater — *instrumento verde cuja pergunta envelheceu*. Cura na W1 (item
`[P0]`, mesmo commit) e AC-10; o stale pré-existente do MAP é a **OQ-10**.

**F11 — este repositório JÁ tem um `if:` de detecção de path que falha em
silêncio, dentro do próprio arquivo que a W1 editaria.**
`validate.yml:736-739`, no step `D1 pricing TBD guard`:

```yaml
        if: |
          github.event_name == 'push' ||
          (github.event_name == 'pull_request' &&
           (contains(github.event.pull_request.changed_files, 'docs/provider-pricing.md') ||
            contains(github.event.pull_request.changed_files, '.github/workflows/validate.yml')))
```

Leitura precisa (o debate corrigiu um exagero aqui): o primeiro termo é
`github.event_name == 'push'`, então o step **roda em todo push** — ele
não é um `if:` morto, é um `if:` morto **apenas na perna
`pull_request`**. Nessa perna, `github.event.pull_request.changed_files`
é a **contagem** de arquivos (um inteiro), não uma lista de caminhos, e o
`contains()` nunca casa. *(Essa última parte é semântica do payload do
GitHub e está NÃO-VERIFICADA por comando aqui — sem rede.)* Verificado
por comando, e é o que fecha o argumento:

```
$ grep -rn "changed_files" .github/workflows/   -> só :738 e :739
$ grep -rn "adapter-matrix" .github/workflows/  -> só a própria linha de comentário :730
```

O comentário `:729-731` diz "Mirrors adapter-matrix job's inline
`contains()` approach" — **o job espelhado não existe mais**. Era
invisível porque o F2 mede **zero** runs de `pull_request`.

**Por que isto decide a §6:** é evidência in-repo, no arquivo-alvo, de
que lógica de detecção de path escrita por nós apodrece em silêncio. É o
argumento mais forte a favor da Rota C, e ele veio do próprio repositório
— não de doutrina.


## 6. As duas rotas para a A1, com o custo verificado de cada uma

O GitHub **não tem `paths:` por job**. Ou o filtro sobe para o nível do
workflow, ou desce para um `if:` de job alimentado por detecção. Filtro
no nível do `validate.yml` inteiro está **eliminado de saída**: mataria
também o job de governança, que o escopo manda preservar.

**Rota B — job detector + `if:` nos 4 pesados, tudo dentro do
`validate.yml`.** Um job barato calcula o diff, publica uma saída, e os
4 pesados ganham `needs:` + `if:`.
- A favor: um arquivo só; **não mexe na contagem de workflows** (F4); os
  jobs aparecem como `skipped` (observabilidade, e é a rota compatível
  com um futuro required-check, F1).
- Contra: **código nosso na exata superfície que o plano quer proteger**.
  A lógica de diff precisa acertar `push` (167/167 dos runs, F2) e
  `pull_request` ao mesmo tempo; no `push`, o par é
  `github.event.before...github.sha`, e `before` vem zerado em criação de
  branch e force-push — casos que **têm de** cair em "rode tudo". O
  precedente in-repo (`shadow-ci.yml:65-75`) usa
  `git diff --name-only "origin/${{ github.base_ref }}...HEAD"`, que é
  **PR-only**: `base_ref` é vazio em `push`. Copiar esse molde sem
  emenda produz exatamente o falso-verde que o AC-2 existe para pegar.
- O detector tem de rodar em `ubuntu-latest` (grátis); rodá-lo no `Ceo`
  reintroduz custo por run.
- **Contra, e é o achado P0 do debate r1 — `paths` × `concurrency`.** Sob
  a Rota B, todo push (inclusive só-docs) **ainda cria** um run de
  `validate.yml`, entra no **mesmo** grupo (`validate-${{ github.ref }}`,
  `:11-13`, e 167/167 dos runs vêm de `push` em `main`, F2) e **cancela o
  run em voo** do push de código anterior — e então pula os 4 pesados.
  Resultado: os jobs pesados do commit de código **nunca terminam e nada
  fica vermelho**. Não é hipotético: 47% dos runs da janela terminaram
  `cancelled` (F6). **Cura obrigatória no ramo B:** ou
  `cancel-in-progress: false`, ou os 4 pesados ganham
  `concurrency:` de **job**, com grupo próprio, para que um push filtrado
  não possa cancelar um run pesado em voo. É Check da W1.
- **Contra — a semântica tem de ser `all()`, não `any()`.** A classe
  MISTA é 28% dos commits da janela (§1). Um detector que pule quando
  *algum* path casa a denylist salta os 4 pesados em mais de um quarto
  dos commits e passa em AC-1 e AC-2, que só exercem os polos puros. É
  Check da W1 e o AC-2b.

**Rota C — mover os 4 pesados para um workflow novo com
`on: {push, pull_request}` + `paths-ignore:` nativo.**
- A favor: o filtro é do **substrato**, não nosso — a semântica de diff
  de push vem de graça e correta; quando o GitHub não consegue computar
  o diff, ele **roda** (fail-closed na direção certa). Precedente
  doutrinário no próprio repo: o `ownership-nightly.yml:5-9` registra que
  o split virou **workflow separado, não entrada de filtro**.
- Contra, e agora quantificado: **+1 arquivo ⇒ `docs/CTO-GUIDE.md:46`
  22→23 no mesmo commit** (F4); boilerplate duplicado (checkout
  SHA-pinado, `setup-python` pinado, pin do pytest, kill-switch
  `if: vars.CEO_SOTA_DISABLE != '1'`, **e `permissions:` no nível do
  workflow** — F7, o item que faltava nesta lista e que o `integration-tests`
  hoje só tem por herança); e **o `concurrency.group` tem de
  ser DISTINTO** de `validate-${{ github.ref }}` — grupos de concorrência
  são globais entre workflows, e reusar o nome faria os dois workflows
  cancelarem um ao outro.
- **Contra — `cancel-in-progress` não vem de graça (debate r1).** O
  default é `false`. Um arquivo novo que declare só `group:` faz **todo
  run pesado superado rodar até o fim**: os minutos **sobem** exatamente
  nos pushes de código, que são os que o filtro preserva, e a baseline de
  13.428 min (que já reflete 47% de cancelamento, F6) deixa de ser
  comparável com o pós-corte do AC-6. Molde in-repo pronto:
  `coverage.yml:21-23`.
- **Contra — o arquivo novo tem de disparar sobre SI MESMO.** Uma
  mudança que estreite o próprio filtro, ou quebre a invocação de pytest,
  entraria em `main` sem que o workflow pesado jamais rodasse. Molde
  in-repo: `coverage.yml:11-14` já inclui
  `".github/workflows/coverage.yml"` no seu próprio `paths:`.
- **Contra — as superfícies derivadas são QUATRO, não uma** (F10):
  `CTO-GUIDE:46` (vigiada), mais `README.md:8` (badge), `ADR-021:132` +
  `ADR-050:73-74`, e `GOVERNANCE-MAP.md` — **as três últimas não são
  vigiadas por nada**, logo o drift ali é silencioso.
- O boilerplate duplicado **é parcialmente vigiado**: o step
  `Action SHA-pin compliance` roda `check-action-sha-drift.py --offline`
  (`validate.yml:413`) e o step `actionlint` cobrem `.github/workflows/`
  inteiro, logo o arquivo novo nasce sob esses gates. **Mas nenhum dos
  dois verifica presença de `permissions:`** (F7) — conferido por grep.

**Recomendação do CEO: Rota C — mantida, e o debate a reforçou.** O
filtro *é* a superfície de risco, e a implementação do substrato bate a
nossa. A evidência decisiva veio do próprio arquivo-alvo: o **F11** mostra
um `if:` de detecção de path escrito por nós que já falha em silêncio na
perna `pull_request`, dentro do `validate.yml`, com um comentário que cita
um job que não existe mais. E a Rota B acumulou no debate o achado de
cancelamento cruzado (`paths` × `concurrency`), que a Rota C não tem.

O que mudou na contabilidade da recomendação: **o custo novo não é "uma
linha mecanicamente vigiada"** — são quatro superfícies, três delas não
vigiadas (F10). A recomendação sobrevive porque esse custo é de
*documentação*, pago uma vez e no mesmo commit, contra um risco de
*correção* que se paga a cada push.

A Rota B fica como rota nomeada para o dia em que alguém ligar required
checks (F1) — **e agora com o preço na etiqueta**: migrar C→B exige
resolver `paths` × `concurrency` antes (OQ-5).

**A W1 escolhe UM ramo na abertura e registra qual.** Os `Check:` das
unidades estão escritos de modo que os **dois** ramos sejam executáveis —
um `Check:` que só um ramo consegue satisfazer torna o outro ramo
inexecutável e é defeito de plano, não de execução.

### Claims de substrato ainda NÃO verificadas por comando

Tudo que a §5 numera (F1..F6) saiu de comando rodado, com a saída citada.
Estas três, não — são comportamento **documentado do GitHub Actions**,
lidas de conhecimento e não confirmadas neste repositório:

1. o GitHub não oferece `paths:` **por job** (é o que força a escolha
   entre Rota B e Rota C);
2. `concurrency.group` é compartilhado **entre workflows** do mesmo
   repositório — daí a exigência de nome distinto na Rota C (a
   recomendação é segura em qualquer caso: nome distinto não custa nada);
3. filtros de path **não se aplicam** a `workflow_dispatch` — a base da
   rota de recuperação da W1. **Corrigida no debate r1:** isto vale
   **só no ramo C**, onde o gate é um filtro do substrato. **No ramo B a
   claim é irrelevante**, porque lá o gate é o *nosso* `if:`, e um re-run
   ou um dispatch reavaliam essa expressão e pulam de novo, a menos que
   ela nomeie `github.event_name == 'workflow_dispatch'`;
4. **`workflow_dispatch` despacha em um `ref` (branch/tag), não num SHA
   arbitrário** — logo ele roda a PONTA do branch, não o commit que o
   filtro pulou. Uma vez que `main` avance, o commit pulado fica
   inalcançável por dispatch. Consequência de projeto: a rota de
   recuperação é "re-executar os pesados sobre um estado", não "re-testar
   aquele commit". Isso **tem de estar escrito no comentário do YAML**,
   senão a rota promete o que não entrega;
5. um push filtrado por `paths-ignore` **não cria run algum** — daí ele
   não poder cancelar nada (é o que separa a Rota C da Rota B no achado
   de concorrência).

A W1 confirma **(1), (2) e (5)** na execução — elas caem de graça ao
montar a rota escolhida — e exercita **(3)** uma vez pelo próprio
`Check:` da unidade de recuperação. A **(4)** é a única que a W1 não
consegue falsificar barato: ela fica registrada como limitação declarada
no comentário do YAML, e o `Check:` exige que o texto esteja lá. Se
alguma delas for falsa, a rota muda — por isso estão listadas aqui e não
enterradas no meio do texto.

## 7. O que este plano NÃO faz

- **Não mexe no `coverage.yml`** — já curado na S220.
- **Não adiciona `-n auto` aos dois jobs seriais.** Seria a economia
  óbvia, e é justamente por isso que está fora: `tests/integration/`
  toca estado compartilhado, o repo já tem classe de flake registrada
  nessa vizinhança (isolamento de auditoria sob sessão concorrente), e
  `pytest-xdist` nem está instalado nesses dois jobs. Paralelizar suíte
  de integração é um plano com bateria própria, não um item de corte de
  custo.
- **Não toca o job de governança.** Ele continua em todo commit, a 15
  min e US$ 0,33 por run. Que ele próprio rode suítes completas de teste
  é resíduo declarado na §9, com número — não escopo.
- **Não mexe em `templates/`** (F3) nem em nada que o adopter receba.
- **Não altera o budget de billing** — isso é ação de conta do Owner.

## 8. Nível e gate de debate

Declarado **L3**, e a razão é honesta: pelo critério mecânico do
`PROTOCOL.md` §"When to skip debate" isto é L2 — cabe em 1-2 arquivos,
blast radius contido. Mas a mudança é **no gate**, não sob o gate: mexe
na superfície V1 da cascata de verificação (o CI determinístico que
autoriza o merge), e o modo de falha é "código entra sem teste". Um
plano que enfraquece o próprio verificador paga debate.

O Owner pode rebaixar para L2 com um critério explícito — o candidato
natural é "a A1 é reversível em um commit e o AC-2 tem controle positivo
mecânico". A decisão é dele; o plano não a antecipa.

## Waves

### W0 — Medir e derivar antes de filtrar (read-only)

> **Read-only sobre `main`** (corrigido no debate r1 — a redação anterior
> dizia "read-only sobre `.github/`" e tornava a US3 insatisfazível: não
> existe caminho para rodar um job em `ubuntu-latest` sem alterar
> `runs-on:`, e a W2 estava gateada por essa medição — gate circular).
> Nada aqui edita workflow **em `main`**; a US3 nomeia seu mecanismo. A
> saída são números e uma lista derivada.

- [ ] `[P0][US1]` **Derivar** a denylist candidata a partir da atribuição
      real dos **106** runs só-docs por prefixo de path — nunca de
      memória. Saída: lista ordenada de prefixos com a fração do custo
      só-docs que cada um explica, para que a denylist seja curta e
      cubra o que de fato paga a conta.
      Check: a lista de prefixos e publicada no plano com o comando que a produziu ao lado e a soma das fracoes declarada; enumeracao escrita de memoria e rejeitada
- [ ] `[P0][US2]` **Provar inércia, por entrada.** Para cada candidato da
      US1, duas provas: (a) **estática** — buscar leituras do caminho
      real do repositório (`_REPO_ROOT` / `Path(__file__).parents[...]`)
      dentro dos quatro escopos pesados (`.claude/hooks/tests/`,
      `.claude/scripts/tests/`, `.claude/scripts/optimizer/tests/`,
      `tests/integration/`, `tests/formal_verification/`,
      `tier_policy_cli/tests/`, `tournament/tests/`); (b)
      **comportamental** — mutar um arquivo sob o caminho num clone
      descartável e rodar as quatro suítes; verde ⇒ inerte. Uma versão de
      Python basta para (b): a pergunta é acoplamento de LEITURA de
      arquivo, que não varia por versão — e a razão fica escrita.
      **Contraexemplo já verificado (§4): `docs/**` NÃO é inerte** e
      `.claude/adr/**` é suspeito pela mesma porta (referência morta em
      `docs/threat-model.md`). Entrada sem as duas provas não entra.
      Check: cada entrada da denylist final tem as duas provas registradas; docs/** aparece explicitamente REJEITADO ou com excecao nomeada; qualquer entrada cuja prova (b) fique vermelha e removida da lista
- [ ] `[P0][US3]` **Medir os 2 jobs seriais em `ubuntu-latest` ANTES de
      flipar.** Hoje: E2E 3,4 min contra `timeout-minutes: 8`
      (`validate.yml:1079`) e formal 4,7 min contra `10` (`:1142`). Num
      runner 2-core a duração cresce, e o próprio repo já registra a
      ordem de grandeza (`ownership-nightly.yml:4-6` declara que uma
      bateria de ~25 min local roda "2-3x isso num runner 2-core"). Com
      fator 2-3x, E2E vai a 6,8-10,2 min contra teto **8** e formal a
      9,4-14,1 contra teto **10** — **os dois estouram**. A lição do repo
      é explícita: **margem < ~20% exige bump**, e estouro de
      `timeout-minutes` aparece como `cancelled` matando o passo
      *inocente* que estiver rodando na hora. Medir de verdade, não
      aplicar o fator 2-3x como se fosse medição.
      Check: duracao real de cada um dos dois jobs em ubuntu-latest, de pelo menos 2 execucoes, publicada no plano; o timeout proposto satisfaz medido/timeout <= 0,80; o fator 2-3x aparece so como expectativa previa, nunca como o numero que fecha o AC
- [ ] `[P1][US4]` Congelar o **baseline de confirmação**: o método exato
      (comando/endpoint de billing) com que a W3 vai comparar custo
      medido contra projeção, decidido **antes** do corte para que o
      número de depois seja comparável ao de antes.
      Check: none (levantamento — a saida e o comando de billing e a data de corte do baseline, registrados no plano)

### W1 — A1: os 4 jobs pesados atrás de filtro fail-closed

- [ ] `[P0]` **Registrar a rota escolhida na abertura** (Rota B ou Rota
      C da §6), com a razão. Recomendação do CEO é a C; a escolha é da
      execução e fica escrita antes de qualquer edição.
      Check: a wave abre com uma linha nomeando o ramo escolhido. Ramo C — existe workflow novo com paths-ignore, concurrency.group DISTINTO de validate-${{ github.ref }}, kill-switch CEO_SOTA_DISABLE replicado, e docs/CTO-GUIDE.md:46 atualizado no MESMO commit. Ramo B — existe job detector rodando em ubuntu-latest cujo diff cobre push (github.event.before...github.sha) E pull_request, com before zerado ou diff indisponivel caindo em "roda tudo"
- [ ] `[P0]` **Denylist, não allowlist** (§3), com o conteúdo saído da
      W0-US1/US2 e nada além. O gatilho **`push`** é obrigatório: um
      filtro só de `pull_request` é morto aqui (F2, 167/167 dos runs vêm
      de `push` em `main`).
      Check: a configuracao usa paths-ignore (ou, no ramo B, um default "roda" para caminho desconhecido); o gatilho push esta presente; nenhuma entrada da denylist esta fora da lista provada na W0-US2
- [ ] `[P0]` **Controle positivo direção A — tem de DISPARAR.** Commit
      tocando `.claude/hooks/**` faz os 4 pesados **executarem**. A forma
      forte, e é a exigida: um **plant** que só um job pesado pega — o
      job de governança roda Python **3.12** (`validate.yml:327`), então
      uma construção que quebra **apenas em 3.9** (anotação PEP 604 em
      posição avaliada em runtime, proibida pelo `CLAUDE.md` §4) fica
      verde na governança e **vermelha** só na perna 3.9 do
      `hook-tests-python-matrix`. Isso prova as duas coisas de uma vez: o
      filtro roteou, e o job pesado é o único que pegaria.
      Check: o run do commit com plant mostra os 4 jobs pesados EXECUTADOS e o CI VERMELHO na perna 3.9; controle de reversao — removido o plant, o mesmo caminho fica verde
- [ ] `[P0]` **Controle positivo direção B — NÃO pode disparar.** Commit
      tocando **só** `.claude/plans/**` produz um run em que nenhum dos 4
      pesados executa, verificado no JSON do run (ausentes no ramo C,
      `skipped` no ramo B) — nunca por leitura do YAML.
      Check: gh run view --json jobs do commit so-plans nao lista nenhum dos 4 jobs pesados como executado; a evidencia e a saida do comando, colada no registro da wave
- [ ] `[P0]` **O job de governança roda em TODO commit**, inclusive no
      commit só-plans do controle B. É ele que valida os `.md`.
      Check: o mesmo gh run view --json jobs do controle B mostra "Governance, health, contamination, shellcheck" com conclusion success
- [ ] `[P1]` **Rota de recuperação nomeada**: como forçar os 4 pesados
      num commit que o filtro pulou (`workflow_dispatch` — filtros de
      path não se aplicam a ele — ou re-run), escrito no cabeçalho do
      arquivo alterado, não só no plano.
      Check: o comentario no proprio YAML nomeia a rota de recuperacao e ela e exercitada uma vez com sucesso
- [ ] `[P1]` **A ressalva durável de required-checks** (F1) fica escrita
      **no YAML**, ao lado do filtro: hoje é seguro porque `main` não tem
      protection nem rulesets; ligar required checks sobre os 4 pesados
      trava PR.
      Check: grep no arquivo alterado encontra a ressalva citando branch protection ausente

### W2 — A2: os 2 jobs seriais saem do runner pago

> Gateada pela W0-US3. Não flipar `runs-on` antes de ter a medição.

- [ ] `[P0]` **Bump de `timeout-minutes` no MESMO commit do flip de
      `runs-on`** (ou antes dele), com o valor derivado da medição da
      W0-US3 pela regra `medido / timeout <= 0,80`. Flipar primeiro e
      ajustar depois produz `cancelled` — que este repo já aprendeu a
      diagnosticar errado, porque o machado cai no passo inocente.
      Check: no diff, nenhum job muda runs-on sem que timeout-minutes esteja no valor derivado da W0-US3; a conta medido/timeout aparece no comentario do YAML
- [ ] `[P0]` `E2E integration tests` (`validate.yml:1078`) e
      `Formal verification mutation harness` (`:1139`) passam a
      `runs-on: ubuntu-latest`. Nenhum outro job muda de runner.
      Check: grep -rn "runs-on: Ceo" .github/workflows/ devolve exatamente 4 linhas — coverage.yml:30 e as tres do validate.yml (governanca, dual-rail, python-matrix) — contra as 6 de hoje
- [ ] `[P0]` **Três runs verdes consecutivos** nos dois jobs, com margem
      ≥20% em todos, antes de considerar a wave fechada. Um run verde é
      amostra, não margem.
      Check: as 3 duracoes de cada job estao registradas e a pior delas satisfaz medido/timeout <= 0,80
- [ ] `[P1]` **Sem `-n auto`** (§7). Se a medição mostrar que o teto
      aperta, a resposta é subir o teto, não paralelizar suíte de
      integração dentro de um plano de custo.
      Check: o diff nao introduz -n nem pytest-xdist nesses dois jobs

### W3 — Confirmar com dinheiro real, não com projeção

- [ ] `[P0]` Após uma **janela de observação retrospectiva de 7
      dias-calendário de dados de billing** (janela de DADOS acumulando,
      no molde ratificado no PLAN-180 — não estimativa de esforço),
      comparar custo medido contra a projeção da §2 pelo método
      congelado na W0-US4.
      Check: o custo medido pos-corte e publicado no plano ao lado da projecao, com o comando de billing citado
- [ ] `[P0]` **Resolver a ressalva de composição da §2**: a economia
      combinada real ficou perto de US$ 224/mês ou perto de US$ 205/mês
      (sobreposição A1∩A2)? O número que vale é o da fatura.
      Check: o plano registra qual das duas leituras a fatura confirmou, com o delta em dolares; divergencia acima de 20% contra a projecao reabre o plano em vez de fecha-lo
- [ ] `[P1]` Registrar o resíduo com número (§9) para quem for decidir
      um eventual A3.
      Check: none (registro — a saida e o custo residual medido por job)

## 9. Resíduo declarado (não é escopo)

Depois da A1+A2, o que continua rodando em **todo** commit é o job de
governança: **15 min e US$ 0,33 por run**, e ele **não** é só validação
de `.md` — executa `.claude/hooks/tests/`, `.claude/scripts/tests/`,
`.claude/scripts/optimizer/tests/` e mais dez raízes de teste (§4). Sobre
106 runs só-docs, isso é da ordem de `15 × 106 × 0,022 ≈ US$ 35/mês` —
número **derivado dos componentes da medição**, a confirmar na W3, não
medido de forma independente.

Está aqui por honestidade de escopo: o corte que este plano entrega **não
zera** o custo de um commit só-docs, e quem ler "71%" precisa saber o que
sobra e por quê. Um eventual A3 — separar validação de `.md` da execução
de suítes dentro do job de governança — é plano próprio, e é
estruturalmente mais arriscado que A1, porque desmonta um job que hoje é
a rede de segurança que torna a A1 aceitável.

## Acceptance criteria

- [ ] **AC-1 [P0]** Controle positivo **direção A**: commit tocando
      `.claude/hooks/**` faz os 4 jobs pesados executarem, provado por um
      plant que **só** um job pesado pega (quebra exclusiva de Python
      3.9) — CI vermelho na perna 3.9, verde na governança.
- [ ] **AC-2 [P0]** Controle positivo **direção B**: commit tocando só
      `.claude/plans/**` não executa nenhum dos 4 pesados, provado pela
      saída de `gh run view --json jobs`, não por leitura de YAML.
- [ ] **AC-3 [P0]** O job `Governance, health, contamination,
      shellcheck` executa em **100%** dos commits da janela de validação,
      incluindo o commit só-docs do AC-2.
- [ ] **AC-4 [P0]** Toda entrada da denylist tem prova de inércia
      (estática **e** comportamental, W0-US2). `docs/**` está fora da
      denylist ou tem exceção nomeada — o contraexemplo do
      `test_threat_model_coverage.py` está fechado de um jeito ou de
      outro.
- [ ] **AC-5 [P0]** Nenhum dos 2 jobs movidos para `ubuntu-latest` roda
      com margem de timeout < 20% em 3 runs consecutivos.
- [ ] **AC-6 [P1]** A projeção de economia é confirmada contra billing
      real após a janela de observação; divergência > 20% **reabre** o
      plano em vez de fechá-lo.
- [ ] **AC-7 [P1]** `templates/.github/workflows/*.template` permanece
      byte-idêntico — a mudança não viaja para adopter (F3).
- [ ] **AC-8 [P1]** `python3 .claude/scripts/validate_governance_fast.py`
      e o job de governança seguem verdes no commit de corte, incluindo a
      contagem de workflows (F4).

## Open questions

1. **W1** — Rota B (detector + `if:`) ou Rota C (workflow separado)? A
   recomendação do CEO é a C (§6); a escolha e sua razão são registradas
   na abertura da wave.
2. **W3** — a economia combinada real é a projetada (US$ 224/mês) ou a
   composta com a sobreposição A1∩A2 (~US$ 205/mês)? Só a fatura decide,
   e a §2 marca isto como derivação, não medição.
3. **§9** — o resíduo do job de governança (~US$ 35/mês sobre commits
   só-docs) vira um A3, ou fica declarado como custo aceito de
   governança?
4. **F6** — 79 dos 167 runs (47%) terminaram `cancelled`, e minutos
   queimados antes do cancelamento são cobrados. Vale desagregar as
   causas (concorrência × timeout × corte de billing), ou é ruído?
   Fora do escopo deste plano.
5. **F1** — vale ligar branch protection em `main` depois deste corte?
   Se sim, a Rota C precisa virar Rota B antes, porque job ausente e job
   `skipped` se comportam de forma oposta diante de required checks.

## How to continue

Sessão nova: Gate 1-2, ler este plano inteiro (a §4 e a §5 carregam os
contraexemplos que impedem a versão ingênua do filtro) e confirmar a
autorização do Owner — o plano está em `status: draft` e é **L3**, então
o `/debate start PLAN-184 "<proposta>"` vem antes da execução, a menos
que o Owner rebaixe para L2 com critério explícito (§8).

Ordem: **W0 inteira antes de qualquer edição de `.github/`** — sem a
denylist derivada (US1/US2) e sem a medição do 2-core (US3), a W1 e a W2
não têm insumo. Depois W1 (A1) e W2 (A2), commits por wave com hint
`feat(PLAN-184 W<n>): ...`. A W3 fecha em D+7, quando houver dados de
billing acumulados.

Antes do commit de corte: `python3
.claude/scripts/validate_governance_fast.py` e
`bash .claude/scripts/local/verify-counts.sh --no-tests --quiet` — o
segundo é quem pega a contagem de workflows do F4.

## Reference links

- `.github/workflows/validate.yml` — os 5 jobs; `runs-on` em `:27`,
  `:1078`, `:1139`, `:1412`, `:1447`; `timeout-minutes` em `:34`,
  `:1079`, `:1142`, `:1413`, `:1448`.
- `.github/workflows/coverage.yml:10-18` — o precedente de filtro de
  paths in-repo, **e** a armadilha: só `pull_request`, que aqui seria
  morto (F2).
- `.github/workflows/ownership-nightly.yml:4-9` — o precedente de "split
  vira WORKFLOW separado, não entrada de filtro", e a declaração de que
  um runner 2-core roda 2-3x mais devagar.
- `.github/workflows/shadow-ci.yml:65-75` — o molde de detecção por
  `git diff` que a Rota B copiaria, **e** o motivo de não copiá-lo cru:
  é PR-only.
- `tests/integration/test_threat_model_coverage.py:25-36,309-380` — o
  contraexemplo que mata `docs/**` na denylist.
- `.claude/scripts/local/verify-counts.sh:324-326,724` +
  `docs/CTO-GUIDE.md:46` — a contagem exata de workflows (F4).
- `templates/.github/workflows/validate.yml.template:22-23` — o adopter
  em `ubuntu-latest`; fora do alcance desta mudança (F3).
