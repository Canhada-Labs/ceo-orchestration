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

> ## ⛔ ROUND 2 DO DEBATE (S321) — OS NÚMEROS DESTA SEÇÃO ESTÃO REFUTADOS
>
> Três críticos independentes (29 achados, `debate/round-2/consensus.md`)
> e a verificação do CEO contra a API de billing derrubaram a base de
> custo. **Nada abaixo desta caixa foi apagado** — fica como registro do
> que o plano afirmava — mas nenhum número da §1 ou da §2 pode autorizar
> execução até a W0 reconstruí-los.
>
> **O que o billing vivo diz** (`gh api /organizations/Canhada-Labs/settings/billing/usage`, agosto/2026):
>
> | linha | qty | gross |
> |---|---|---|
> | `Actions Linux 8-core` | **9.254,909 min** | **US$ 203,61** |
> | `Actions Linux` | 4.025 min | US$ 24,15 |
>
> O plano declara **14.291 min / US$ 314,40** — superestimativa de ~54%.
>
> **E o problema que quebra o AC-6:** esses minutos de 8-core são
> faturados sob `repositoryName: ceo-orchestration-**private**`, não sob
> o repositório público que este plano quer otimizar. Não é rótulo:
> medi o volume de agosto nos dois — **privado 73 runs, público 400+
> (167 só de `validate.yml`)**. O privado não gera 9.255 min sozinho,
> logo a atribuição está errada. **O único instrumento de billing que
> existe não atribui por workflow NEM por repositório** (o endpoint
> clássico responde HTTP 410). Ver OQ-12.
>
> **Três correções aritméticas independentes, todas medidas:**
> 1. **85 de 167 pushes** são puláveis com denylist compatível com a §4
>    — não 106. A unidade é o PUSH (o filtro avalia a união do diff do
>    push), e 20 dos 167 pushes carregam mais de um commit.
> 2. **~48 min pesados por run**, não os 80,4 de média que a §2 usa.
> 3. A projeção combinada da §2 (**US$ 10,67/dia**) é MAIOR que o gasto
>    total medido do `validate.yml` no runner pago (**US$ 8,91/dia**) —
>    aritmeticamente impossível. O teto REAL da A1 é **~US$ 4,04/dia**.
>
> **Consequência de escopo, não só de texto:** com a A1 valendo
> ~US$ 4,04/dia de teto, a alternativa **A0** (§6) — reduzir a matriz de
> Python de 4 para 2 versões no `push` — rende **~US$ 3,15/dia** sem
> filtro, sem workflow novo, sem cerimônia e sem classe nova de
> falso-verde. **A ordem A0-vs-A1 é decisão do Owner (OQ-11)**, e é a
> razão de o round 2 terminar em `ESCALATE-TO-OWNER` em vez de
> `ADJUST_PROCEED`.

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
> ### ✅ DERIVADAS na S344 (2026-09-04) — W0-US5 fechada, e a manchete caiu
>
> As duas bases inconsistentes foram substituídas por **uma**: minutos por
> **JOB** por run, `Ceo` apenas, cada job arredondado para cima ao minuto,
> sobre os **167** runs de `push` em `main` da janela. Derivação completa,
> com todos os comandos, em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.
>
> **A base que sobreviveu é a por-JOB** — é a única com comando. A base
> "TABELA" da §1 era a média global `13.428 / 167 = 80,4`, e a base
> "MEDIDA" era uma agregação por workflow que esta derivação **não
> reproduz**.
>
> ```
> minutos pagos na janela   14.265,7 wall  |  15.045,0 faturáveis  (US$ 330,99)
> por-run medido (5 jobs pagos)     85,42  vs  80,40 da tabela  ->  +6,2 %
> ```
>
> **Resíduo de +6,2 % com causa NOMEADA** (o Check da US5 pede <5 % *ou* a
> causa): o `13.428` do plano não é reproduzível por nenhuma base
> construível a partir dos jobs — nem wall cru (14.265,7), nem só
> tentativa 1 (14.150,8), nem excluindo cancelados (6.412,4).
>
> **E a hipótese pré-registrada da US5 está REFUTADA.** Não houve erro de
> classificação de ~23-24 runs: reproduzindo a regra original, a
> atribuição bate (98 runs / 10.035 min contra 106 / 10.407). O que falha
> é a premissa de **custo por run uniforme** — um push só-docs custa
> **97,62 min** de wall contra **68,09** de um push de código (**+43 %**).
> O `±1.884` da nota de reconciliação é artefato da média.
>
> **O que a derivação MUDA na direção, e não só na magnitude:** sob a
> gramática que a própria W1 adotou (`<prefixo>/**/*.md`), a A1 pula
> **48 de 167 pushes**, não 98 — a âncora de extensão remove **75 % do
> prêmio**, porque `.claude/plans/**` hospeda `.py`/`.sh`/`.patch`
> encenados. Somado ao fato de a **A0 já ter landado** (`5ff06c9`), o
> teto da A1 é **US$ 1,443/dia**. Ver **OQ-6** e **OQ-11**.

**A1 — filtro de paths nos 4 jobs pesados.**
`hook-tests-python-matrix`, `hook-tests-dual-rail`, `E2E integration
tests` e `Formal verification mutation harness` passam a rodar **somente
quando o código muda**. O job `Governance, health, contamination,
shellcheck` **continua rodando em TODO commit** — é ele que valida os
`.md` (`check-claude-md-claims.py`, `verify-counts.sh`, staleness,
contamination). Economia **DERIVADA (S344)**, na base por-JOB e sob a
gramática de denylist da própria W1 (`<prefixo>/**/*.md`, sem `docs/` e
sem `.github/`), que pula **48 dos 167 pushes**:

| leitura | minutos A1 | US$ na janela | **US$/dia** | leitura de 30 dias |
|---|---|---|---|---|
| **pós-A0** (o que ainda há para ganhar) | 1.377,0 | US$ 30,29 | **US$ 1,443** | US$ 43 |
| pré-A0 (janela como medida) | 2.095,0 | US$ 46,09 | US$ 2,195 | US$ 66 |
| contrafactual sem a âncora `*.md` (regra por prefixo cru) | 8.301,0 | US$ 182,62 | US$ 8,696 | US$ 261 |

A **A0 landou em `5ff06c9` (2026-08-23), depois da janela**; ler a A1 na
linha pré-A0 conta duas vezes o mesmo minuto de matriz. Os antigos
**US$ 9,24/dia** e **US$ 7,26/dia** estão **substituídos**. Comando e
tabelas em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.

**A2 — os 2 jobs que não paralelizam saem do runner pago.**
`E2E integration tests` e `Formal verification mutation harness` trocam
`runs-on: Ceo` por `runs-on: ubuntu-latest`. Economia **DERIVADA
(S344)**, base por-JOB: **US$ 1,756/dia** isolada
(1.676,0 min = US$ 36,87 na janela; leitura de 30 dias: US$ 53) e
**US$ 1,578/dia** marginal depois da A1 (1.506,0 min = US$ 33,13).
**A sobreposição A1 ∩ A2 é US$ 3,74 na janela (US$ 0,178/dia)** — e não
os US$ 19 estimados, porque a A1 real pula 48 pushes e não 106. A A2
não toca a matriz, logo a A0 não a altera. Derivação em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.

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


## 6-A. A0 — a alternativa que nenhuma redação anterior enumerou

> Achado do round 2. Ela não estava aqui porque o plano nasceu perguntando
> "como filtrar?", nunca "o que é caro?".

`hook-tests-python-matrix` roda 4 versões de Python (`validate.yml:1445-1477`)
e consome **~34 min wall dos ~48 min pesados por run** — **75% do custo
que a A1 ataca**. As pernas medidas: 7,8 / 9,2 / 9,3 / 7,7 min.

Rodar só as versões de **fronteira** (3.9 e 3.12) no gatilho `push`, e
manter as 4 no `pull_request` e no nightly, economiza
`ceil(7,7) + ceil(9,2) = 18 min/run × 167 runs × US$ 0,022` =
**US$ 66 na janela de 21 dias ≈ US$ 3,15/dia**.

Compare com o teto REAL da A1 (**~US$ 4,04/dia**, caixa da §1). Mesma
ordem de grandeza, e a A0 chega lá:

- sem filtro de path (nenhuma classe de "guard verde porque não vê o alvo");
- sem workflow novo (nenhuma das 4 superfícies derivadas muda);
- sem cerimônia canônica (a matriz vive dentro do `validate.yml`, que já
  é editado sob sentinel de qualquer forma — mas é UM path guardado, não
  quatro);
- sem gramática de denylist para manter viva ao longo do tempo.

O risco que ela carrega é declarado e menor: um defeito específico de
3.10 ou 3.11 deixa de ser pego no `push` e passa a ser pego no PR ou no
nightly — atraso de detecção, não perda de cobertura. **A A1 troca
cobertura por dinheiro; a A0 troca latência de detecção por dinheiro.**

**OQ-11: a ordem.** Se a A0 entrar primeiro, o prêmio residual da A1
encolhe e "vale gastar cerimônia + workflow novo por ~US$ 1-2/dia?"
passa a ter outra resposta. Decisão do Owner.

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

### ✅ W-A0 — A0 LANDADA (2026-08-23, S322): `5ff06c9`

> **Registrado na S325.** Até aqui este plano tinha 12 menções a "A0",
> todas de PREVISÃO ou de decisão, e **zero** menção ao land, ao sha ou ao
> cron. O único trabalho que shipou era invisível no plano que o governa.
>
> **Entregue** (`git show --stat 5ff06c9` — 5 arquivos, +155/−4):
> `hook-tests-python-matrix` passa a rodar as versões de FRONTEIRA (3.9 e
> 3.12) no gatilho `push`; as QUATRO seguem no `pull_request` e no
> `schedule: - cron: "37 7 * * *"`, que entrou JUNTO — sem ele a A0 seria
> PERDA de cobertura em vez de troca de latência por dinheiro (medido
> antes de cortar: `{'push': 167}` e zero `schedule:` no arquivo).
> Landado sob sentinel Owner-signed (`PLAN-184/wave-a0-approved.md` +
> `.asc`, chave EDDSA AE9B236F…0335DC74, Anchor-SHA `d8ee055`).
>
> **PROVADA EM PRODUÇÃO, não em YAML:** a matriz do `push` do próprio
> commit rendeu **2 entradas** — 3.9 e 3.12. Isso é observação do run, não
> leitura do arquivo.
>
> **Ação humana com prazo, ainda aberta:** o cron novo aterrissou
> 2026-08-23 12:31 UTC, depois das 07:37, logo o PRIMEIRO fire é
> **2026-08-24 07:37 UTC**. Inspecionar à mão: uma matriz vazia no
> `schedule` passaria **vacuamente** — confirmar que são 4 entradas.

- [x] `[P0]` matriz de fronteira no `push` — `validate.yml` (+19 linhas)
      Check: `git show 5ff06c9 -- .github/workflows/validate.yml` mostra a
      expressão condicional entregando `["3.9","3.12"]` no `push` e as
      quatro versões fora dele; e o run do PRÓPRIO commit rendeu 2
      entradas de matriz — observação do run, não leitura do YAML.
- [x] `[P0]` backstop nightly `37 7 * * *` (minuto off-mark por desenho)
      Check: `grep -c 'cron: "37 7 \* \* \*"' .github/workflows/validate.yml`
      == 1, e o `schedule:` do arquivo lista as QUATRO versões (sem isso a
      A0 seria perda de cobertura, não troca de latência por dinheiro).
- [x] `[P0]` cerimônia canônica: sentinel + `.asc`, gates de dry-run e
      V1-V6 no land, todos verdes
      Check: `gpg --verify .claude/plans/PLAN-184/wave-a0-approved.md.asc`
      sai "Good signature" com a chave EDDSA AE9B236F…0335DC74, e o
      Anchor-SHA do sentinel é `d8ee055`.
- [x] `[P1]` confirmar o PRIMEIRO fire do cron (2026-08-24 07:37 UTC) com
      4 entradas na matriz — matriz vazia passa vacuamente
      Check: no run agendado, a matriz de `hook-tests-python-matrix` tem
      **4** entradas (3.9/3.10/3.11/3.12). Contagem 0 ou 2 REPROVA: uma
      matriz vazia passaria vacuamente e é exatamente o modo de falha
      que este item existe para pegar.
      **APROVADO (S325, verificado no run `32703818841`).** O fire real saiu
      em `2026-08-24T07:56:22Z` — ~19 min depois do `37 7`, atraso normal do
      scheduler do Actions, não defeito. `event=schedule`,
      `conclusion=success`, e a CONTAGEM é **4**:
      `hook-tests-python-matrix (3.9)`, `(3.10)`, `(3.11)`, `(3.12)`, todas
      `success`. A verificação foi a contagem, não o verde: um run verde com
      matriz vazia era exatamente o modo de falha que este item existia para
      pegar, e ele não ocorreu. ⇒ o backstop nightly da A0 está **provado em
      produção**, e a troca de latência por dinheiro (fronteira no `push`,
      quatro versões no `schedule`) é real e não claim de YAML.

### W0 — Medir e derivar antes de filtrar (read-only)

- [ ] `[P0][US0]` **PRÉ-REGISTRO — o resultado que MATA o plano.**
      (Achado do round 2: nenhum dos cinco Checks da W0 interrompia o
      plano; as duas bases da US5 eram aceitáveis por construção, e a
      US1 não tinha fração mínima. Um pré-registro que não nomeia o
      resultado que o mata não é pré-registro.)
      O Owner fixa **N** (US$/dia) e **M** (%) ANTES de a US1 rodar:
      se o teto derivado da A1 ficar abaixo de N, ou a fração de custo
      só-docs abaixo de M, **a W1 não abre** e o plano fecha como
      residual registrado. Valores medidos hoje para calibrar a escolha,
      não para substituí-la: teto da A1 ≈ US$ 4,04/dia, fração ≈ 58,8%.
      Check: N e M estao escritos aqui com a data e a assinatura da decisao ANTES do primeiro numero da US1; um resultado abaixo do piso fecha o plano em vez de reabrir a discussao
      **CALIBRAÇÃO DERIVADA (S344, 2026-09-04) — N e M são decisão do
      Owner.** Os valores que este item citava (teto ≈ US$ 4,04/dia,
      fração ≈ 58,8%) **não sobrevivem** à gramática `<prefixo>/**/*.md`
      que a W1 adotou no round 2 nem à A0 já landada. Medido, na base
      por-JOB e sob essa gramática (derivação em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`):

      | grandeza | valor derivado |
      |---|---|
      | teto da A1, **pós-A0** | **US$ 1,443/dia** |
      | fração de custo só-docs, pós-A0 | **17,8 %** |
      | teto da A1, pré-A0 (para comparar com o texto antigo) | US$ 2,195/dia |
      | fração só-docs, pré-A0 | 18,1 % |
      | contrafactual sem a âncora de extensão (regra por prefixo cru) | US$ 6,063/dia · 66,8 % |
      | A0 já entregue, medida por replay da janela | US$ 3,963/dia |
      | gasto total remanescente do `validate.yml` no runner pago | US$ 11,798/dia |

      Leitura honesta do que foi medido, e não uma recomendação: com
      **N ≥ US$ 1,50/dia** o pré-registro fecha o plano. **N e M são
      decisão do Owner** — esta nota calibra a escolha, não a substitui.
- [ ] `[P0][US0b]` **A unidade é o PUSH, não o commit.** `paths-ignore`
      no gatilho `push` avalia o diff `before...after` — a UNIÃO de
      todos os commits do push. **Re-derivado (S344): são 21 dos 167
      pushes** que carregam mais de um commit (o maior carrega 21
      commits), e **zero** pushes têm diff vazio. Os 167 heads estão
      todos em `--first-parent main` (`on_first_parent=167 off=0`), logo
      `head[i-1]..head[i]` é exatamente a união do push. Toda contagem da
      §1 e todo controle positivo passam a ser por push. Comando e
      saída em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.
      Check: a §1 nao contem a palavra "commit" como unidade de contagem; a derivacao da US1 usa `git diff --name-only head[i-1] head[i]` sobre os 167 heads reais

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
      **DERIVADA (S344, 2026-09-04).** Censo dos prefixos `.md` que
      **aparecem** nos diffs dos 167 pushes (nada de memória), ordenado
      por ganho marginal em minutos pagos atribuíveis à A1, cobertura
      gulosa, gramática da W1, com `docs/**` e `.github/**` fora (§4/AC-4):

      | # | entrada | min A1 acum. | marginal | pushes | fração acum. |
      |---|---|---|---|---|---|
      | 1 | `.claude/plans/**/*.md` | 1.715,0 | 1.715,0 | 40 | 13,9 % |
      | 2 | `*.md` (raiz) | 1.899,0 | 184,0 | 44 | 15,4 % |
      | 3 | `npm/**/*.md` | 1.986,0 | 87,0 | 46 | 16,1 % |
      | 4 | `.claude/governance/**/*.md` | 2.041,0 | 55,0 | 47 | 16,5 % |
      | 5 | `.claude/commands/**/*.md` | 2.095,0 | 54,0 | **48** | **17,0 %** |

      **Soma declarada: 5 entradas explicam 2.095,0 de 12.341,0 minutos
      pagos atribuíveis à A1 = 17,0 % (US$ 46,09 de US$ 271,50), pulando
      48 de 167 pushes.** `.claude/adr/**/*.md`, `SPEC/**/*.md` e
      `templates/**/*.md` **não entram**: ganho marginal ZERO — todo push
      que os toca também toca algo fora da lista.

      **Custo da gramática, medido:** a regra cega à extensão (a que a
      medição original usou) pularia **98** pushes e 8.301,0 min; a âncora
      `/**/*.md` derruba para **48** pushes e 2.095,0 min — **75 % do
      prêmio some**, porque dentro dos 50 pushes perdidos vivem 174 `.py`,
      46 `.sha256`, 44 `.sh`, 41 `.txt`, 30 `.patch` e 17 `.yml`. A
      gramática está certa E o prêmio é pequeno, ao mesmo tempo. Comandos
      e censo completo em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.
- [ ] `[P0][US2]` **Provar inércia, por entrada.** Para cada candidato da
      US1, duas provas: (a) **estática** — buscar leituras do caminho
      real do repositório (`_REPO_ROOT` / `Path(__file__).parents[...]`)
      dentro dos quatro escopos pesados (`.claude/hooks/tests/`,
      `.claude/scripts/tests/`, `.claude/scripts/optimizer/tests/`,
      `tests/integration/`, `tests/formal_verification/`,
      `tier_policy_cli/tests/`, `tournament/tests/`); (b)
      **comportamental** — num clone descartável, aplicar ao caminho as
      **TRÊS** operações e rodar as quatro suítes: **MUTAR conteúdo,
      RENOMEAR e APAGAR**. Verde nas três ⇒ inerte.
      **Corrigido no debate r1 (P0):** a redação anterior pedia só
      mutação de conteúdo, e o mecanismo do contraexemplo da §4 é
      **EXISTÊNCIA** (`validate_file_ref:199-215` nunca lê conteúdo) —
      logo mutar um ADR deixa a suíte verde e `.claude/adr/**` entraria
      na denylist pela própria regra deste plano, apagando o vermelho que
      a §4 existe para preservar. Restrição na escolha do alvo: o
      fallback de prefixo (`startswith`) faz `ADR-045-x.md` →
      `ADR-045-x-v2.md` continuar verde para referências `bare`, então o
      alvo tem de ser um cujo sumiço seja de fato observável.
      Uma versão de Python basta: a pergunta é acoplamento de LEITURA de
      arquivo, que não varia por versão — e a razão fica escrita.
      **Contraexemplos já verificados (§4): `docs/**` NÃO é inerte**;
      `.claude/adr/**` é suspeito pela mesma porta; e `.github/**`
      **passaria** na prova de conteúdo e por isso é exclusão dura, não
      candidato. Entrada sem as duas provas não entra.
      Check: cada entrada da denylist final tem as duas provas registradas, e a prova (b) inclui as tres operacoes (mutar/renomear/apagar) com a saida colada; para .claude/adr/** o registro exige o VERMELHO em rename ou delete, nao o verde — um verde nas tres so e aceito com o comando que mostra que NENHUM teste le aquele caminho; docs/** e .github/** aparecem explicitamente REJEITADOS ou com excecao nomeada; qualquer entrada cuja prova (b) fique vermelha e removida da lista
- [ ] `[P0][US3]` **Medir os 2 jobs seriais em `ubuntu-latest` ANTES de
      flipar.** Hoje: E2E 3,4 min contra `timeout-minutes: 8`
      (`validate.yml:1079`) e formal 4,7 min contra `10` (`:1142`). Num
      runner 2-core a duração cresce, e o próprio repo já registra a
      ordem de grandeza (`ownership-nightly.yml:4-6` declara que uma
      bateria de ~25 min local roda "2-3x isso num runner 2-core"). Com
      fator 2-3x, E2E vai a 6,8-10,2 min contra teto **8** e formal a
      9,4-14,1 contra teto **10** — **os dois estouram**. A lição do repo
      é explícita: estouro de `timeout-minutes` aparece como `cancelled`
      matando o passo *inocente* que estiver rodando na hora. Medir de
      verdade, não aplicar o fator 2-3x como se fosse medição.
      **MECANISMO, nomeado no debate r1 (o gate era circular sem ele).**
      Rota primária, **custo US$ 0**: `validate.yml:5-6` é
      `push: branches: [main]`, logo um **push em branch, sem PR aberto,
      não dispara `validate.yml`**. Um workflow de medição efêmero com
      `on: push:` nesse branch, replicando os steps dos dois jobs em
      `runs-on: ubuntu-latest`, entrega as duas durações sem tocar
      `validate.yml` e sem queimar um minuto pago (`ubuntu-latest` é
      grátis em repo público). Rota alternativa, **paga**: um PR que
      flipe os dois `runs-on` — `validate.yml:4` tem `pull_request:` sem
      filtro de branch, então o PR produz a medição, mas também dispara o
      job de governança + `hook-tests-dual-rail` + `hook-tests-python-matrix`
      no runner `Ceo`: `15,0 + 15,5 + 41,8 = 72,3 min ≈ US$ 1,59` por run
      de medição. Efeito colateral a registrar em qualquer das duas: a
      rota de PR seria a **primeira** execução do gatilho `pull_request`
      na janela (F2 mede 167/167 vindos de `push`, zero de PR) — a rota
      de medição é ela própria não-exercitada. **Ver OQ-8.**
      **DIMENSIONAMENTO (corrigido no debate r1):** a regra
      `medido/timeout <= 0,80` com N=2 é mais fraca que o método que este
      repo já pratica no job análogo. `smoke-install.yml:150-172` registra
      5→8→20→25→32, todos "MEASURED, not guessed", todos com o fator
      2-3x, e o comentário `:159-161` diz textualmente que 15 "would sit
      inside the noise band, and the perf-gate N=20 flake (PLAN-159) was
      exactly that mistake". O outro precedente in-repo
      (`validate.yml:1181-1186`, `opus-4-7-profiler-smoke`) dimensiona por
      **pior caso aritmético**. Portanto: dimensionar por **composição de
      pior caso** — para o E2E, checkout + `setup-python` + `pip install`
      + as **TRÊS** invocações de pytest do job (`tests/integration/`,
      `.claude/scripts/tier_policy_cli/tests/`,
      `.claude/scripts/tournament/tests/`) — e conferir contra o envelope
      2-3x, não contra 20% de margem sobre o máximo de N=3. N=3 não
      produz p95; se o dimensionamento ficar estatístico, a base (p95) e o
      N necessário ficam declarados.
      Check: o mecanismo de medicao escolhido (branch efemero ou PR) esta nomeado com seu custo em dolares ao lado; duracao real de cada um dos dois jobs em ubuntu-latest, de pelo menos 2 execucoes, publicada no plano; o timeout proposto vem de composicao de pior caso com as parcelas somadas por escrito, e satisfaz TAMBEM medido/timeout <= 0,80; o fator 2-3x aparece so como expectativa previa, nunca como o numero que fecha o AC
- [ ] `[P0][US4]` Congelar o **baseline de confirmação** — e não é uma
      coisa, são **TRÊS** (corrigido no debate r1, P0): (a) o
      comando/endpoint de billing; (b) a **base de tempo canônica**, que
      é **US$/dia-calendário** — a única que sobrevive a uma janela
      medida de 21 dias e a uma janela de confirmação de 7; (c) a
      **fórmula de conversão** explícita (`US$/dia × dias-da-janela`).
      Sem (b) e (c), o gate ">20% reabre" do AC-6 dispara pelas UNIDADES
      antes de qualquer efeito real do corte (contas na §2). Decidido
      **antes** do corte, para que o número de depois seja comparável ao
      de antes. **Ver OQ-7.**
      Check: as tres coisas estao registradas no plano — comando, base US$/dia-calendario e formula de conversao; e a §2 inteira aparece reexpressa nessa base, sem nenhum numero de custo que feche AC em rotulo "/mes"
- [ ] `[P0][US5]` **Reconciliar as duas bases de custo por-run ANTES de
      qualquer número da §2 ser usado** (achado P0 do debate r1). Derivar
      minutos **por JOB por run** (`gh run view <id> --json jobs` sobre os
      167 runs da janela) em vez de minutos por workflow, e fechar o
      delta de `+1.884,6` min no bucket só-docs contra `-1.910,4` no de
      código. Hipótese barata a testar primeiro, porque os deltas são
      quase simétricos e opostos: **erro de classificação** de ~23-24 dos
      106 runs "só-docs" que seriam de código. Se for isso, a A1 cai
      ~US$ 34 na janela (≈ US$ 1,62/dia).
      **RECONCILIADA (S344, 2026-09-04) — e a hipótese está REFUTADA.**
      Não houve erro de classificação: reproduzindo a regra original
      (prefixo, cega à extensão), a atribuição bate — **98 runs /
      10.035 min** contra os 106 / 10.407 do plano (−7,5 % e −3,6 %). O
      que falha é a premissa de **custo por run uniforme**: um push
      só-docs custa **97,62 min** de wall contra **68,09** de um push de
      código (**+43 %**), e o `±1.884` é artefato de aplicar a média
      global 80,4 por bucket. Tabela por JOB (167 runs), resíduo de
      **+6,2 %** contra a tabela da §1 **com a causa nomeada** (o 13.428
      é uma agregação por workflow que nenhuma base por-job reproduz), e
      a base sobrevivente registrada na §2 — tudo em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`.
      Colateral que a reconciliação expõe, com número: **431 jobs `Ceo`
      terminaram `cancelled` carregando 7.853,4 min (US$ 172,77) = 55 %
      de todos os minutos pagos da janela** — termo maior que A1 e A2
      somadas, e que é a OQ-4, não escopo deste plano.
      Check: a saida do gh run view por job esta agregada por bucket e publicada; o delta residual contra a tabela por-job da §1 esta abaixo de 5% OU a causa esta nomeada; a §2 registra qual das duas bases sobreviveu e reexpressa A1/A2/sobreposicao nela

### W1 — A1: os 4 jobs pesados atrás de filtro fail-closed

- [ ] `[P0]` **CERIMÔNIA CANÔNICA — abre a wave, antes de qualquer
      edição.** (Achado do round 2, e o plano não mencionava a palavra
      uma única vez: `grep -ci "cerim\|sentinel\|canonical\|gpg"` = 0.)
      `check_canonical_edit.py:184-185` guarda `.github/workflows/*.yml`
      e `:178` guarda `.claude/adr/ADR-*.md`. O commit de split toca no
      MÍNIMO quatro paths guardados: `validate.yml`, o workflow novo,
      `ADR-021` e `ADR-050`. Sem sentinel assinado cujo `Scope:` enumere
      os quatro, o primeiro Edit é BLOQUEADO — e a rota de medição da
      W0-US3 (workflow efêmero) cai no mesmo guard.
      Check: existe approved.md Owner-signed cujo bloco Scope enumera TODOS os paths guardados do commit de split, e `touched − scope = ∅` antes do land
- [ ] `[P0]` **Gramática da entrada da denylist** (round 2): toda entrada
      é `<prefixo-aprovado>/**/*.md`. Entrada sem âncora de extensão
      (prefixo cru) é REJEITADA por construção — `.claude/plans/**` como
      prefixo cru pré-aprovaria os 272 `.py`, 102 `.sh` e 31 `.yml` que
      já vivem lá hoje, incluindo `PLAN-179/staged-w24/` e
      `OWNER-W179-LAND.sh`, que são código encenado para land.
      Check: nenhuma entrada da denylist final termina em `/**` ou `**`; toda entrada casa `\*\.md$`; um `.py` novo sob qualquer prefixo da denylist NAO casa (provado por glob-match real, nao por leitura)
- [ ] `[P0]` **Guard de fork** (round 2): seis workflows irmãos
      condicionam jobs alcançáveis por fork com
      `github.event.pull_request.head.repo.full_name == github.repository`;
      `validate.yml` não tem nenhum, e esta wave ACENDE `pull_request`
      pela primeira vez na janela medida (167/167 vieram de `push`).
      Check: o arquivo novo declara a postura de fork copiando um dos dois precedentes in-repo, com a razao no comentario; o AC-9 registra que o PR de teste e intra-repo
- [ ] `[P0]` **Backstop `schedule:`** (round 2): o `coverage.yml`, que
      este plano cita como precedente do filtro, tem `cron: 0 7 * * *` —
      e `ownership-nightly.yml:6-8` registra que `schedule` IGNORA
      filtros de path. O plano copiou o filtro e deixou a rede. Sem cron,
      uma entrada de denylist que envelheça produz silêncio permanente.
      Check: o workflow novo tem `schedule:`, e UM run agendado verde e pre-requisito de fechar a wave
- [ ] `[P0]` **Teste do próprio filtro, no job NÃO filtrado** (round 2):
      o `Check` "o arquivo novo dispara sobre si mesmo" é uma propriedade
      do conteúdo no momento em que ele é escrito, não um invariante — um
      PR de uma linha pode acrescentar um padrão que case o próprio
      arquivo, e `actionlint` aprova `paths-ignore` sintaticamente válido
      sem opinar sobre o que ele cobre.
      Check: teste em .claude/scripts/tests/ (roda no job de governanca, nunca filtrado) que parseia o bloco `on:` do workflow novo e assere: toda entrada obedece a gramatica acima, e NENHUMA casa `.github/**` — por glob-match real contra o proprio caminho do arquivo

- [ ] `[P0]` **Registrar a rota escolhida na abertura** (Rota B ou Rota
      C da §6), com a razão. Recomendação do CEO é a C; a escolha é da
      execução e fica escrita antes de qualquer edição.
      Check: a wave abre com uma linha nomeando o ramo escolhido. Ramo C — existe workflow novo com paths-ignore, concurrency com group DISTINTO de validate-${{ github.ref }} E cancel-in-progress: true, permissions no nivel do workflow, kill-switch CEO_SOTA_DISABLE replicado, o proprio arquivo incluido no gatilho, e as QUATRO superficies derivadas atualizadas no MESMO commit. Ramo B — existe job detector rodando em ubuntu-latest cujo diff cobre push (github.event.before...github.sha) E pull_request, com before zerado ou diff indisponivel caindo em "roda tudo", semantica all() e nao any(), e os 4 pesados fora do grupo de concorrencia que um push filtrado cancela
- [ ] `[P0]` **Denylist, não allowlist** (§3), com o conteúdo saído da
      W0-US1/US2 e nada além. **Paridade de gatilho é DERIVADA, não
      lembrada** (corrigido no debate r1): `validate.yml:3-6` cobre
      `pull_request:` **sem filtro de branch** *e* `push: branches:
      [main]`. Exigir só o `push` — como a redação anterior fazia —
      deixaria o `pull_request` sumir no split sem que nenhum AC pegasse,
      invisível justamente porque o F2 mede zero runs de PR. E
      `.github/workflows/**` **não pode** casar a denylist: o filtro
      precisa ser capaz de testar a própria mudança (molde:
      `coverage.yml:11-14` inclui o próprio arquivo).
      Check: o bloco `on:` do arquivo novo cobre o MESMO conjunto de eventos que validate.yml:3-6 cobria para esses jobs — pull_request (sem filtro de branch) E push: branches:[main] — provado por diff dos dois blocos on:, nao por leitura; a configuracao usa paths-ignore (ou, no ramo B, um default "roda" para caminho desconhecido); nenhuma entrada da denylist esta fora da lista provada na W0-US2; nenhuma entrada casa .github/workflows/**; e o arquivo novo dispara sobre si mesmo
- [ ] `[P0]` **Concorrência amarrada, no ramo que for** (achado P0/P1 do
      debate r1). O `cancel-in-progress` é `false` por default: no ramo C,
      um arquivo que declare só `group:` faz todo run pesado superado
      rodar até o fim e os minutos **sobem**. No ramo B, o inverso —
      todo push só-docs entra no grupo `validate-${{ github.ref }}` e
      **cancela** o run pesado em voo do push de código anterior, e nada
      fica vermelho. Os dois casos invalidam a comparação do AC-6, cuja
      baseline já reflete 47% de cancelamento (F6).
      Check: ramo C — o arquivo novo declara concurrency com group de prefixo distinto E cancel-in-progress: true (molde coverage.yml:21-23). Ramo B — ou cancel-in-progress: false no workflow, ou os 4 pesados carregam concurrency de JOB com grupo proprio; e a evidencia e um par de pushes (codigo, depois so-docs, em sequencia rapida) mostrando no gh run view que o run pesado do primeiro NAO foi cancelado pelo segundo
- [ ] `[P0]` **`permissions:` explícito, e a herança curada antes do
      split** (F7). `integration-tests` é o único dos 4 sem bloco próprio
      — num arquivo novo sem `permissions:` ele passaria a rodar com o
      escopo DEFAULT do repositório para o `GITHUB_TOKEN`. Nem
      `actionlint` nem `check-action-sha-drift.py` verificam presença de
      `permissions`, então isto não tem rede embaixo.
      Check: integration-tests ganha permissions: contents: read PROPRIO antes ou no mesmo commit do split; o arquivo novo declara permissions no nivel do workflow; e o efetivo de cada um dos 4 jobs e identico ao de hoje, mostrado lado a lado no registro da wave
- [ ] `[P0]` **As QUATRO superfícies derivadas, no MESMO commit do
      split** (F10 — a frase "o único custo novo é uma linha" era falsa).
      (a) `docs/CTO-GUIDE.md:46` 22→23 (esta é vigiada, build vermelho);
      (b) `README.md:8` — segundo badge apontando para o workflow novo,
      ou badge agregado: hoje o badge fica **verde com o workflow pesado
      vermelho**, que é a classe que este plano diz combater;
      (c) `.claude/adr/ADR-021-e2e-harness-contract.md:132` (arquivo **e**
      o timeout, que a W2 muda) e
      `.claude/adr/ADR-050-native-subagents-dual-rail.md:73-74` (arquivo);
      (d) `.github/workflows/GOVERNANCE-MAP.md` — linha nova. Só (a) é
      mecanicamente vigiada; (b), (c) e (d) driftariam em silêncio.
      Check: as quatro edicoes estao no diff do commit de split; `bash .claude/scripts/local/verify-counts.sh --no-tests --quiet` verde; `python3 .claude/scripts/check-staleness.py` rodado e a saida registrada; e um grep por "workflows/validate.yml" em README.md + .claude/adr/ nao devolve nenhuma afirmacao que a mudanca tornou falsa
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
- [ ] `[P0]` **Controle positivo direção C — a FRONTEIRA MISTA tem de
      DISPARAR** (achado P0 do debate r1). Um **único** commit tocando
      `.claude/plans/**` **e** um arquivo sob `.claude/hooks/**` faz os 4
      pesados executarem. Sem este controle, um detector com semântica
      `any()` em vez de `all()` passa em AC-1 e AC-2 e pula os 4 pesados
      em **28% dos commits** (67/239 na janela medida, §1) — o falso-verde
      exato que este plano existe para impedir. No ramo C a semântica
      `all()` vem do substrato; no ramo B é código nosso, e por isso o
      Check é o mesmo nos dois: prova comportamental, não leitura.
      Check: gh run view --json jobs do commit MISTO mostra os 4 pesados EXECUTADOS; e, no ramo B, a expressao do detector e citada no registro da wave com a demonstracao de que ela pula somente se TODOS os paths alterados casarem
- [ ] `[P0]` **Controle positivo direção D — o gatilho `pull_request`
      existe e roteia** (achado P1 do debate r1). Um PR de teste tocando
      `.claude/hooks/**` mostra os 4 pesados executados no run de
      `pull_request` do workflow novo. É a única prova de que a paridade
      de gatilho sobreviveu ao split — e o F2 garante que ninguém
      descobriria isso por acidente, já que a janela inteira tem zero
      runs de PR.
      Check: gh run view --json jobs,event do run de pull_request mostra event=pull_request e os 4 pesados executados
- [ ] `[P0]` **O job de governança roda em TODO commit**, inclusive no
      commit só-plans do controle B. É ele que valida os `.md`.
      Check: o mesmo gh run view --json jobs do controle B mostra "Governance, health, contamination, shellcheck" com conclusion success
- [ ] `[P1]` **Rota de recuperação nomeada — POR RAMO** (a redação
      anterior não funcionava em nenhum dos dois; achado convergente do
      debate r1). No **ramo C**, "re-run" é vacuo: um push filtrado não
      produz run algum, logo não há o que re-rodar — a rota é
      `workflow_dispatch: {}` no arquivo novo (molde in-repo pronto:
      `coverage.yml:18`), e `validate.yml` hoje **não tem**
      `workflow_dispatch` (`grep` = zero). No **ramo B**, "re-run all
      jobs" **reavalia** o `if:` e pula de novo: a expressão tem de
      conter `github.event_name == 'workflow_dispatch' ||` como primeiro
      termo, senão o dispatch também pula. E nos dois: `workflow_dispatch`
      despacha em um **`ref`** (branch/tag), **não num SHA** — ele roda a
      ponta do branch, não o commit que o filtro pulou, e uma vez que
      `main` avance esse commit fica inalcançável por dispatch. Essa
      limitação vai **escrita no comentário do YAML**, senão a rota
      promete o que não entrega.
      Check: o comentario no proprio YAML nomeia a rota do ramo escolhido E registra a limitacao ref-nao-SHA; no ramo B, grep na expressao do if: encontra github.event_name == 'workflow_dispatch'; e a rota e exercitada uma vez com sucesso, com a saida do gh run view colada
- [ ] `[P1]` **A ressalva durável de required-checks** (F1) fica escrita
      **no YAML**, ao lado do filtro: hoje é seguro porque `main` não tem
      protection nem rulesets; ligar required checks sobre os 4 pesados
      trava PR.
      Check: grep no arquivo alterado encontra a ressalva citando branch protection ausente

### W2 — A2: os 2 jobs seriais saem do runner pago

> Gateada pela W0-US3. Não flipar `runs-on` antes de ter a medição.
>
> **⛔ Round 2 — a premissa desta wave caiu.** Medido no run
> `32431818032` (steps com `started_at`/`completed_at` por job):
> `Formal verification mutation harness` = **15 segundos** (teto 10 min);
> `E2E integration tests` = **1 m 43 s** (teto 8 min). A W0-US3 previa
> que "com fator 2-3× os dois estouram" — eles não estouram nem perto:
> as razões medido/teto são **0,025 e 0,24**, contra o gate de 0,80.
> E a premissa que sustentava o AC-5 — "`Ceo` é self-hosted, inventário
> de binários desconhecido" — é **falsa**:
> `gh api .../actions/runners` devolve `total_count: 0`, e os jobs
> reportam `runner_name: ceo-1000004236` (larger runner **hospedado**,
> mesma família de imagem). A A2 vale **~US$ 0,2/dia** medidos, não
> US$ 0,52. Esta wave vira item barato SEM medição própria — ou é
> cortada e registrada como resíduo. O AC-5 sobrevive pelo motivo
> CERTO (variação de tool-cache/pip entre imagens), não pelo falso.

- [ ] `[P0]` **Bump de `timeout-minutes` no MESMO commit do flip de
      `runs-on`** (ou antes dele), com o valor derivado da medição da
      W0-US3 por **composição de pior caso**, e conferido *também* contra
      `medido / timeout <= 0,80`. Flipar primeiro e ajustar depois produz
      `cancelled` — que este repo já aprendeu a diagnosticar errado,
      porque o machado cai no passo inocente. A regra de margem sozinha é
      mais fraca que os dois precedentes in-repo (`smoke-install.yml:150-172`
      com o fator 2-3x e a nota anti-noise-band; `validate.yml:1181-1186`
      com soma de pior caso), e o E2E tem **três** invocações de pytest,
      não uma.
      Check: no diff, nenhum job muda runs-on sem que timeout-minutes esteja no valor derivado da W0-US3; o comentario do YAML mostra as PARCELAS somadas (checkout + setup-python + pip + cada invocacao de pytest) alem da conta medido/timeout, no molde de validate.yml:1181-1186
- [ ] `[P0]` `E2E integration tests` (`validate.yml:1078`) e
      `Formal verification mutation harness` (`:1139`) passam a
      `runs-on: ubuntu-latest`. Nenhum outro job muda de runner.
      Check: grep -rn "runs-on: Ceo" .github/workflows/ devolve exatamente 4 linhas — coverage.yml:30 e as tres do validate.yml (governanca, dual-rail, python-matrix) — contra as 6 de hoje
- [ ] `[P0]` **Três runs verdes consecutivos** nos dois jobs, com margem
      ≥20% em todos, antes de considerar a wave fechada. Um run verde é
      amostra, não margem.
      Check: as 3 duracoes de cada job estao registradas e a pior delas satisfaz medido/timeout <= 0,80
- [ ] `[P0]` **"Verde" não é prova quando o runner muda: delta de SKIP =
      0** (achado P1 do debate r1). O `Ceo` é self-hosted (inventário de
      binários desconhecido) e `ubuntu-latest` é outra imagem. A suíte
      E2E tem gates de ambiente reais — `tests/integration/test_install_sh_rollback.py:78-80`
      (`shutil.which` → `pytest.skip`),
      `test_peers_yaml_migration.py:228,424,490,816`
      (`shutil.which("openssl")`), `test_live_adapter_smoke.py:64,66`. Um
      run verde com N skips **novos** é indistinguível de um run verde sem
      nenhum: é a classe dominante deste repo (*guard verde porque não vê
      o alvo*) chegando na única wave onde a doutrina da §3 não tinha
      sido aplicada.
      Check: a linha-resumo do pytest (X passed, Y skipped, Z deselected) do ULTIMO run em Ceo e do PRIMEIRO run em ubuntu-latest esta colada lado a lado para os DOIS jobs; delta de skipped = 0 e delta de passed = 0; delta nao-zero BLOQUEIA o flip de runs-on
- [ ] `[P1]` **Sem `-n auto`** (§7). Se a medição mostrar que o teto
      aperta, a resposta é subir o teto, não paralelizar suíte de
      integração dentro de um plano de custo.
      Check: o diff nao introduz -n nem pytest-xdist nesses dois jobs

### W3 — Confirmar com dinheiro real, não com projeção

- [ ] `[P0]` Após uma **janela de observação retrospectiva de 7
      dias-calendário de dados de billing** (janela de DADOS acumulando,
      no molde ratificado no PLAN-180 — não estimativa de esforço),
      comparar custo medido contra a projeção da §2 pelo método
      congelado na W0-US4 — **em US$/dia-calendário nos dois lados**.
      Comparar uma janela de 7 dias contra um rótulo "/mês" produz 4,29x
      de "divergência" só pelas unidades (§2).
      Check: o custo medido pos-corte e publicado no plano em US$/dia ao lado da projecao em US$/dia, com o comando de billing citado e a formula de conversao aplicada por escrito
- [ ] `[P0]` **Resolver a ressalva de composição da §2**: a economia
      combinada real ficou perto de **US$ 10,67/dia** (projeção cheia,
      `224/21`) ou perto de **US$ 9,76/dia** (`205/21`, com a sobreposição
      A1∩A2)? O número que vale é o da fatura. E a comparação só é
      legítima se a W0-US5 já reconciliou as bases — senão a projeção
      contra a qual se mede é ela própria NÃO-DERIVADA. **Pré-condição
      SATISFEITA (S344): a US5 reconciliou, a base sobrevivente é a
      por-JOB, e as duas leituras a comparar deixam de ser US$ 10,67 e
      US$ 9,76/dia — na base derivada e pós-A0 a projeção combinada é
      A1 US$ 1,443/dia + A2 marginal US$ 1,578/dia = US$ 3,021/dia**
      (`.claude/plans/PLAN-184/w0/w0-derivation-S344.md`).
      Check: o plano registra qual das duas leituras a fatura confirmou, com o delta em US$/dia; divergencia acima de 20% contra a projecao — medida na MESMA base de tempo — reabre o plano em vez de fecha-lo; e o registro cita o resultado da W0-US5 como pre-condicao da comparacao
- [ ] `[P1]` Registrar o resíduo com número (§9) para quem for decidir
      um eventual A3.
      Check: none (registro — a saida e o custo residual medido por job)

## 9. Resíduo declarado (não é escopo)

Depois da A1+A2, o que continua rodando em **todo** commit é o job de
governança: **15 min e US$ 0,33 por run**, e ele **não** é só validação
de `.md` — executa `.claude/hooks/tests/`, `.claude/scripts/tests/`,
`.claude/scripts/optimizer/tests/` e mais dez raízes de teste (§4). Sobre
106 runs só-docs, isso é da ordem de `15 × 106 × 0,022 ≈ US$ 34,98` na
janela de 21 dias = **US$ 1,67/dia** (leitura de 30 dias: US$ 50) —
número **derivado dos componentes da medição**, a confirmar na W3, não
medido de forma independente, e na base congelada da W0-US4.
**⚠️ CORRIGIDO na S325:** este derivado foi depois REFUTADO por medição —
o resíduo real sobre pushes só-docs na janela limpa é **US$ 1,20/dia**,
não US$ 1,67/dia (ver a nota de higiene em §Open questions e a OQ-3b).
O parágrafo acima fica como registro de COMO o número foi derivado e de
por que um derivado não substitui uma medição; o valor a usar é 1,20.

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
- [ ] **AC-2b [P0]** Controle positivo **da FRONTEIRA**: um **único**
      commit tocando `.claude/plans/**` **e** um arquivo sob
      `.claude/hooks/**` faz os 4 pesados **executarem**
      (`gh run view --json jobs`). Sem este AC, um detector com semântica
      `any()` passa em AC-1 e AC-2 e pula os pesados em 28% dos commits
      (67/239 na janela, §1). *(Debate r1, P0.)*
- [ ] **AC-3 [P0]** O job `Governance, health, contamination,
      shellcheck` executa em **100%** dos commits da janela de validação,
      incluindo o commit só-docs do AC-2.
- [ ] **AC-4 [P0]** Toda entrada da denylist tem prova de inércia
      (estática **e** comportamental, W0-US2), e a comportamental cobre
      **mutar, renomear e apagar** — não só mutar, porque o detector do
      contraexemplo é de EXISTÊNCIA (§4). `docs/**` **e `.github/**`**
      estão fora da denylist ou têm exceção nomeada; o contraexemplo do
      `test_threat_model_coverage.py` está fechado de um jeito ou de
      outro. *(Debate r1, P0 — `.github/**` é exclusão dura porque
      passaria na prova de conteúdo e o filtro precisa poder testar a
      própria mudança.)*
- [ ] **AC-2c [P0]** Controle positivo **da UNIDADE**: um único
      **PUSH** com dois commits — um só-docs e um tocando
      `.claude/hooks/**` — executa os 4 pesados
      (`gh run view --json jobs`). `paths-ignore` avalia a UNIÃO do diff
      do push, e 20 dos 167 pushes da janela carregam mais de um commit;
      sem este AC, um detector que só olhe o último commit passa em
      AC-1/AC-2/AC-2b. *(Round 2, P0.)*
- [ ] **AC-5 [P0]** Nenhum dos 2 jobs movidos para `ubuntu-latest` roda
      com margem de timeout < 20% em 3 runs consecutivos, **e** o delta
      contra o último run em `Ceo` é **assinado**:
      `skipped(ubuntu-latest) <= skipped(Ceo)` **E**
      `passed(ubuntu-latest) >= passed(Ceo)`. Teste que passa a ser
      PULADO bloqueia; teste que passa a RODAR não bloqueia.
      *(Round 2: o critério simétrico `delta = 0` bloqueava o flip
      quando a cobertura MELHORASSE.)* A comparação é pinada no MESMO
      SHA — os dois jobs rodam no commit de flip, um deles por dispatch
      no runner antigo.
- [ ] **AC-6 [P1]** A projeção de economia é confirmada contra billing
      real após a janela de observação; divergência > 20% **reabre** o
      plano em vez de fechá-lo. A comparação só é legítima depois da
      W0-US5.
      **⛔ Reescrito no round 2, porque como estava era INEXEQUÍVEL.**
      A base não pode ser US$/dia-calendário: o endpoint clássico de
      billing responde **HTTP 410**, e o que existe
      (`/organizations/{org}/settings/billing/usage`) devolve **9 itens
      agregados por MÊS**, sem eixo de workflow — e atribui os minutos de
      8-core ao repositório **errado** (`-private`; medido: privado 73
      runs em agosto, público 400+). A base passa a ser **US$ por PUSH**
      (ou por run de `validate.yml`), derivável do mesmo dado e imune à
      granularidade mensal: comparar o custo médio de um push só-docs
      ANTES contra DEPOIS. Enquanto a OQ-12 não fechar, nenhum número de
      billing atribui custo a este repositório.
- [ ] **AC-7 [P1]** `templates/.github/workflows/*.template` permanece
      byte-idêntico — a mudança não viaja para adopter (F3).
- [ ] **AC-8 [P1]** `python3 .claude/scripts/validate_governance_fast.py`
      e o job de governança seguem verdes no commit de corte, incluindo a
      contagem de workflows (F4).
- [ ] **AC-9 [P1]** Um PR de teste tocando `.claude/hooks/**` mostra os 4
      pesados executados no run de **`pull_request`** do workflow novo —
      a paridade de gatilho sobreviveu ao split. *(Debate r1, P1: nenhum
      AC exercia `pull_request`, e o F2 garante que ninguém descobriria
      por acidente.)*
- [ ] **AC-10 [P1]** As superfícies derivadas **não vigiadas** estão
      atualizadas no mesmo commit do split: `README.md:8` (badge),
      `.claude/adr/ADR-021:132` + `.claude/adr/ADR-050:73-74`, e
      `.github/workflows/GOVERNANCE-MAP.md`. Prova: `check-staleness.py`
      rodado com a saída registrada, e nenhum grep por
      `workflows/validate.yml` em `README.md`/`.claude/adr/` devolvendo
      afirmação que a mudança tornou falsa. *(Debate r1, P1 — só a
      contagem do CTO-GUIDE é mecanicamente vigiada; as outras três
      driftariam em silêncio.)*

## Open questions

> **Round 2 — nota de higiene desta lista.** A sequência impressa abaixo
> é `1, 2, 3, 4, 3b, 5` e depois `6..10` após uma régua: o item `3b`
> aparece DEPOIS do `4`, e há **duas entradas concorrentes para o mesmo
> resíduo** (a OQ-3 diz "~US$ 35/mês", a OQ-3b reexpressa em US$/dia).
> Como o flip para `reviewed` depende explicitamente destas questões,
> a lista é load-bearing e a numeração quebrada é defeito, não estética.
> **A OQ-3 fica MORTA em favor da OQ-3b**, e o número dela também estava
> errado: o resíduo medido da governança sobre pushes só-docs na janela
> limpa é **US$ 1,20/dia**, não US$ 1,67/dia.
>
> As duas questões que o Owner precisa responder **antes** de qualquer
> execução são as novas, no fim da lista.
>
> **RECONCILIADO na S325:** as três resoluções que este cabeçalho declarava
> agora estão refletidas na lista — a OQ-3 está marcada MORTA em posição
> (não renumerada, porque o id é referenciado adiante), a OQ-3b subiu para
> logo depois dela, e o `US$ 1,67/dia` foi corrigido para **US$ 1,20/dia**.
> Antes disso o cabeçalho e a lista se contradiziam, e a lista é
> load-bearing para o flip.

### ✅ OQ-11 — RESPONDIDA pelo Owner (2026-08-22, S321): **A0 PRIMEIRO**

> **Decisão registrada:** executar a **A0** (reduzir a matriz de Python de
> 4 para 2 versões no gatilho `push`, mantendo as 4 no `pull_request` e no
> nightly) e **reavaliar a A1 depois**, com o prêmio residual medido em vez
> de projetado.
>
> **Consequência para este plano, escrita para não ser re-litigada:** a W1
> e a W2 **não abrem** enquanto a A0 não tiver rodado e o novo teto da A1
> não for derivado da fatura. O item `[P0][US0]` da W0 (o pré-registro do
> resultado que mata) passa a ter um insumo concreto: o **N** que o Owner
> fixar deve ser comparado ao prêmio **residual** pós-A0, não ao teto de
> US$ 4,04/dia medido antes dela. Se o residual ficar abaixo de N, este
> plano fecha como resíduo registrado — e isso é um desfecho previsto,
> não um fracasso.
>
> **Escopo da A0, para quem executar:** `validate.yml:1445-1477`
> (`hook-tests-python-matrix`). Pernas medidas: 7,8 / 9,2 / 9,3 / 7,7 min.
> Manter **3.9** (piso de compatibilidade declarado no CLAUDE.md) e
> **3.12** (topo); economia derivada
> `ceil(7,7) + ceil(9,2) = 18 min/run × 167 runs × US$ 0,022 ≈ US$ 66/21d`.
> `validate.yml` é canonical-guarded — a A0 é UMA linha de YAML, mas ainda
> exige sentinel.

<details>
<summary>Texto original da OQ-11, preservado como registro da decisão</summary>

### OQ-11 — A ORDEM: A0 antes de A1? *(a escalação do round 2)*

Com a base de custo refutada, o teto REAL da A1 é ~US$ 4,04/dia e a
**A0** (§6-A, reduzir a matriz de Python de 4 para 2 versões no `push`)
rende ~US$ 3,15/dia — mesma ordem de grandeza, **sem** filtro de path,
**sem** workflow novo, **sem** cerimônia canônica sobre 4 paths
guardados, **sem** gramática de denylist para manter viva.

Se a A0 entrar primeiro, o prêmio residual da A1 encolhe e a pergunta
"vale gastar cerimônia + workflow novo por ~US$ 1-2/dia?" muda de
resposta. Três opções: **(a)** A0 primeiro, e reavaliar a A1 depois;
**(b)** A1 como planejado, tratando a A0 como resíduo; **(c)** as duas,
A0 primeiro por ser mais barata de reverter.
**Recomendação do CEO: (a).** Decisão do Owner — é o que faz o round 2
terminar em `ESCALATE-TO-OWNER`.

</details>

### ⭐ OQ-12 — A quem o billing atribui este custo?

Os minutos de `Actions Linux 8-core` de agosto (**9.254,909 min /
US$ 203,61**) aparecem sob `repositoryName: ceo-orchestration-private`,
mas o volume vem do público (privado: 73 runs em agosto; público: 400+,
sendo 167 de `validate.yml`). Enquanto isso não for resolvido, **nenhum
número de billing atribui custo a este repositório**, e o AC-6 não tem
como fechar.

Três leituras: **(a)** peculiaridade de como o GitHub fatura larger
runners de um grupo da org (o repo privado seria o "billing owner");
**(b)** o repo privado consome mais do que o volume de runs sugere;
**(c)** bug de agregação. **(a)** é a mais provável e a mais fácil de
confirmar — se for, a base de custo do plano nunca poderá ser derivada
por repositório, e o AC-6 tem de medir por PUSH, como já reescrito.

---


1. **W1** — Rota B (detector + `if:`) ou Rota C (workflow separado)? A
   recomendação do CEO é a C (§6); a escolha e sua razão são registradas
   na abertura da wave.
2. **W3** — a economia combinada real é a projetada (US$ 10,67/dia,
   `224/21`) ou a composta com a sobreposição A1∩A2 (US$ 9,76/dia,
   `205/21`)? Só a fatura decide, e a §2 marca isto como derivação, não
   medição.
3. ~~**§9** — o resíduo do job de governança (~US$ 35/mês sobre commits
   só-docs) vira um A3, ou fica declarado como custo aceito de
   governança?~~ **MORTA — respondida como duplicata; use a 3b abaixo.**
   Mantida em posição (não renumerada) porque o id é referenciado em
   outros pontos do plano; apagá-la trocaria uma referência quebrada por
   várias. Reconciliada na S325.
3b. **§9 — a versão VIVA desta questão.** O resíduo do job de governança,
   reexpresso na base canônica: o resíduo medido sobre pushes só-docs na
   janela limpa é **US$ 1,20/dia**. O `US$ 1,67/dia` que esta entrada
   trazia (de `15 × 106 × 0,022 = US$ 34,98` em 21 dias) está **REFUTADO**
   pelo próprio cabeçalho desta seção, e foi corrigido aqui na S325 — a
   lista é load-bearing, então deixá-lo faria o Owner responder uma
   questão morta com um número errado. **A pergunta:** esse resíduo vira
   um A3, ou fica declarado como custo aceito de governança?
4. **F6** — 79 dos 167 runs (47%) terminaram `cancelled`, e minutos
   queimados antes do cancelamento são cobrados. Vale desagregar as
   causas (concorrência × timeout × corte de billing), ou é ruído?
   Fora do escopo deste plano.
5. **F1** — vale ligar branch protection em `main` depois deste corte?
   Se sim, a Rota C precisa virar Rota B antes, porque job ausente e job
   `skipped` se comportam de forma oposta diante de required checks.
   **Debate r1 acrescentou o preço:** essa migração também tem de
   resolver `paths` × `concurrency` (um push só-docs sob Rota B cancela o
   run pesado em voo do push de código anterior) — não é só trocar o
   mecanismo do filtro.

---

> As **OQ-6..OQ-10** saíram do debate round-1
> (`.claude/plans/PLAN-184/debate/round-1/synthesis.md`). Nenhuma virou
> suposição no corpo do plano.

6. **§2 / W0-US5 — a manchete é NÃO-DERIVADA. A W1 abre ou espera?** A
   economia US$ 194/US$ 224 não é reproduzível a partir da tabela por-job
   deste plano: sobram ~1.884 min entre os buckets, e A1 vale US$ 194 na
   base MEDIDA contra US$ 153 na base TABELA (21% a menos). A **direção**
   sobrevive às duas bases (A1 é o termo dominante em qualquer leitura),
   a **magnitude** não. Duas opções: **(a)** a W1 abre com a direção e a
   W0-US5 roda em paralelo, com os números marcados NÃO-DERIVADOS até
   fechar; **(b)** a W1 fica gateada pela W0-US5. A recomendação do CEO é
   **(a)** — a US5 depende de `gh` sobre 167 runs e não muda a decisão de
   filtrar, só o tamanho do prêmio. **A decisão é do Owner.**
7. **W0-US4 — ratificar `US$/dia-calendário` como base de tempo canônica
   deste plano.** É a única que sobrevive a uma janela medida de 21 dias
   e a uma de confirmação de 7. A alternativa seria alongar a janela do
   AC-6 para 30 dias e manter "/mês" — mais simples de ler, mas atrasa a
   confirmação em três semanas.
8. **W0-US3 — qual rota de medição?** **(a)** branch efêmero com workflow
   de medição próprio: **US$ 0**, porque `validate.yml` só dispara em
   `push` para `main` e em eventos de PR; **(b)** PR que flipa os dois
   `runs-on`: **≈ US$ 1,59 por run** (governança + dual-rail +
   python-matrix continuam no `Ceo`), mas exercita de quebra o gatilho
   `pull_request`, que hoje tem zero runs na janela. Recomendação do CEO:
   **(a)**, com **(b)** como plano B.
9. **§3 — as 13 allowlists vivas deste repo são risco aceito ou
   follow-up?** A doutrina da §3 diz que allowlist "falha na direção
   perigosa", e 13 workflows deste repositório — incluindo `red-team.yml`
   e `coverage.yml` — são allowlists. Ou isso é risco aceito e fica
   escrito, ou é plano próprio. O PLAN-184 **não** o absorve.
10. **F10 — o `GOVERNANCE-MAP.md` já está stale por dois
    (`ownership-nightly.yml`, `supply-chain-watch.yml`) e nada o vigia.**
    A cura entra no commit de split do PLAN-184 (barato, o arquivo já é
    tocado), ou vira item separado junto com um gate que o mantenha
    honesto? O PLAN-184 assume só a **sua** linha; o stale pré-existente
    é decisão do Owner.

## Debate

**Round 2 — 2026-08-22. Veredito: ESCALATE-TO-OWNER.** Artefatos em
`.claude/plans/PLAN-184/debate/round-2/` (`consensus.md`, três críticas,
`anonymization-map.md`). **29 achados de 3 críticos, ingest COMPLETO** —
a condição que faltou no round 1.

Três críticos com eixos disjuntos e declarados (pipeline / governança /
medição), read-only sob ADR-136-AMEND-1, cada um instruído a NÃO cobrir
os eixos dos outros. Cinco consensos (2+ críticos), nove achados de um
crítico só mantidos, dois rejeitados com o comando que sustenta o
pushback, e um achado do próprio CEO na verificação (a atribuição de
repositório no billing, OQ-12).

**A doutrina do plano sobrevive inteira** — os três disseram
independentemente que manter o job de governança fora do filtro preserva
os validadores de markdown normativo, e que denylist-sobre-allowlist é a
direção de falha certa. O que caiu foi a **aritmética** e, com ela, a
**prioridade**: ver a caixa no topo da §1 e a OQ-11.

**Nota de método, registrada porque é a lição do round 1.** A síntese
automática deste round também recebeu payload truncado (11 de 29) e
**recusou-se a emitir veredito**, marcando `RUN-ANOTHER-ROUND` — o
instrumento corrigido (JSON compacto + truncamento que envenena o
veredito da dimensão dona) fez exatamente o que deveria. A síntese
canônica é a do CEO, sobre os três retornos íntegros lidos do journal do
run `wf_f2943bd9-c0a`.

---

**Round 1 — 2026-08-21. Veredito: ADJUST_PROCEED.** Síntese completa em
`.claude/plans/PLAN-184/debate/round-1/synthesis.md`, anonimizados por
`Critic-A`/`Critic-B` conforme DEBATE-SCHEMA §13.2. Toda claim foi
reverificada contra o disco antes de entrar no plano.

**Limitação declarada do input da síntese:** o material que chegou ao
sintetizador carregava **dois** rótulos (8 itens cada) e **terminou
truncado no meio do último item do `Critic-B`**. Esse item foi
reconstruído por verificação independente contra o disco — convergiu com
o P2 do `Critic-A` e virou o achado C1 — e a síntese declara seu escopo
real (**16 itens, 2 rótulos, um parcial**) em vez de reivindicar
cobertura completa. Se houve um terceiro crítico a montante, ele não
chegou à síntese.

**Seis achados P0**, todos com cura óbvia e todos já incorporados acima —
por isso o veredito não é BLOCK:

1. **Três bases de tempo sem regra de conversão** (21d medido / "/mês"
   projetado / 7d confirmado). O gate ">20% reabre" do AC-6 disparava
   pelas unidades. → §2 e AC-6 em **US$/dia-calendário**; W0-US4 congela
   base e fórmula, não só o comando.
2. **A manchete US$ 194 não é derivável da tabela por-job deste plano**
   (deltas de ±1.884 min entre buckets; duas bases de custo
   inconsistentes). → nota de reconciliação na §1, marcação
   **NÃO-DERIVADA** na §2, nova **W0-US5**.
3. **W0-US3 era um gate circular** (read-only sobre `.github/` × medição
   que exige alterar `runs-on`). → wave é read-only sobre **`main`**, e a
   US3 nomeia o mecanismo, com rota de **US$ 0** (branch efêmero).
4. **A prova de inércia não detectava o modo de falha da §4**: o detector
   é de **existência**, mutação de conteúdo deixa verde. → W0-US2(b)
   passa a exigir **mutar + renomear + apagar**, e o `Check:` exige o
   **vermelho**.
5. **A classe MISTA (28% dos commits) não era exercida por nenhum AC** —
   um detector `any()` passava em AC-1 e AC-2. → **AC-2b** e Check
   explícito de semântica `all()`.
6. **`paths` × `concurrency`**: na Rota B um push só-docs cancela o run
   pesado em voo do push de código anterior e nada fica vermelho. → item
   `[P0]` próprio na W1, e a interação entrou nos contras das duas rotas.

**P1 incorporados:** paridade de gatilho derivada (o `pull_request` podia
sumir no split — **AC-9**); `permissions:` e a herança do
`integration-tests` (**F7**); as quatro superfícies derivadas, três não
vigiadas (**F10**, **AC-10**); `cancel-in-progress` na Rota C;
dimensionamento de timeout por pior caso; delta de `skipped` = 0 na W2;
`paths-ignore` sem precedente in-repo vs 13 allowlists vivas (**§3**,
OQ-9); auto-disparo do workflow novo; inventário de sete jobs (**F8**).

**Três pushbacks registrados — a crítica estava errada e o plano não a
absorveu como escrita:**

- **"`if:` estruturalmente morto" (F11)** — exagerado. O primeiro termo
  de `validate.yml:736` é `github.event_name == 'push'`, então o step
  roda em todo push; ele é morto **apenas na perna `pull_request`**. As
  sub-claims (o `contains()` nunca casa; o job "espelhado" não existe
  mais) estão corretas e entraram como F11 com o enquadramento corrigido.
- **"GOVERNANCE-MAP tem 22 linhas, uma por workflow"** — número errado:
  são **20** linhas para 22 workflows, e o mapa **já está stale por
  dois**. O achado ficou mais forte que a crítica; virou OQ-10.
- **"O plano modela commit como binário e nunca nomeia a classe mista"** —
  enquadramento errado: o bucket "83 tocando código" da §1 **já contém** a
  classe mista, logo a economia não muda. O que estava errado é o
  **instrumento de aceite**, e esse achado foi mantido em P0 (AC-2b).

**O que o debate NÃO mudou, e defendo:** a doutrina denylist-sobre-allowlist
da §3; a recomendação pela **Rota C**, que saiu mais forte (o F11 é
evidência in-repo, no arquivo-alvo, de que detecção de path escrita por
nós apodrece calada, e a Rota B acumulou o achado de cancelamento
cruzado); a recusa de `-n auto` (§7); e a honestidade da §9.

**Sem round 2.** Os dois críticos convergiram sem se contradizer, e o
próximo instrumento útil não é outro round do mesmo vendor — é o
pair-rail cross-vendor sobre o plano ajustado (*debate revisa o MODELO,
rail revisa o TEXTO*; o modelo já foi revisado).

**O plano permanece `status: draft`.** O flip para `reviewed` é do Owner,
e depende das **OQ-6..OQ-10** — das quais só a **OQ-6** muda a ordem de
execução.

## How to continue

Sessão nova: Gate 1-2, ler este plano inteiro (a §4 e a §5 carregam os
contraexemplos que impedem a versão ingênua do filtro; a §"Debate" diz o
que mudou e por quê) e confirmar a autorização do Owner. **O debate L3
rodou duas vezes** — round 1 (2026-08-21, ADJUST_PROCEED sobre ingest
truncado) e round 2 (2026-08-22, **ESCALATE-TO-OWNER**, 29 achados,
ingest completo), artefatos em `debate/round-2/`.

**A primeira coisa a ler é a caixa no topo da §1**, não a §1: os números
que autorizavam o plano estão REFUTADOS por medição contra a API de
billing, e a §1 fica como registro do que se afirmava.

O plano continua em `status: draft`. O flip para `reviewed` é do Owner e
agora depende de **duas** decisões, não de dez: **OQ-11** (a ordem
A0-vs-A1) e **OQ-12** (a quem o billing atribui o custo). As OQ-6..OQ-10
continuam abertas mas deixaram de ser bloqueantes — a W0 reescrita
absorve o que elas perguntavam.

**Se o Owner responder "A1 assim mesmo" na OQ-11, o plano está pronto
para executar**: nada mais precisa ser escrito, é marcar `reviewed` e
abrir a W0 pelo item US0 (o pré-registro do resultado que mata).

Ordem: **W0 inteira antes de qualquer edição de `.github/` em `main`** —
sem a denylist derivada (US1/US2), sem a medição do 2-core (US3) e sem a
base de tempo congelada (US4), a W1, a W2 e o AC-6 não têm insumo. A
**US5** (reconciliação) roda em paralelo, salvo decisão contrária do
Owner na OQ-6. Depois W1 (A1) e W2 (A2), commits por wave com hint
`feat(PLAN-184 W<n>): ...`. A W3 fecha em D+7, quando houver dados de
billing acumulados — e compara em **US$/dia**, nos dois lados.

Antes do commit de corte: `python3
.claude/scripts/validate_governance_fast.py`,
`bash .claude/scripts/local/verify-counts.sh --no-tests --quiet` — o
segundo é quem pega a contagem de workflows do F4 — e
`python3 .claude/scripts/check-staleness.py`, que é o mais próximo que
existe de uma rede para as superfícies **não vigiadas** do F10 (badge do
README, ADR-021/ADR-050, GOVERNANCE-MAP). Nenhum dos três cobre o badge:
esse é conferido à mão, pelo AC-10.

## Reference links

- `.github/workflows/validate.yml` — **SETE** jobs (F8), não cinco:
  `:20`, `:1071`, `:1121`, `:1178`, `:1410`, `:1445`, `:1505`. Os cinco
  em `runs-on: Ceo` estão em `:27`, `:1078`, `:1139`, `:1412`, `:1447`,
  com `timeout-minutes` em `:34`, `:1079`, `:1142`, `:1413`, `:1448`. Os
  dois em `ubuntu-latest` — `opus-4-7-profiler-smoke` (`:1180`) e
  `hook-stdout-schema-oracle` (`:1509`) — **ficam onde estão**: o split
  move quatro e deixa três.
- `.github/workflows/validate.yml:3-6` — o bloco `on:` que o split tem de
  reproduzir: `pull_request:` **sem filtro de branch** *e*
  `push: branches: [main]`.
- `.github/workflows/validate.yml:736-739` — o `if:` de detecção de path
  que já falha em silêncio na perna `pull_request`, com um comentário que
  cita um job inexistente (F11). É o argumento in-repo pela Rota C.
- `.github/workflows/coverage.yml` — o molde in-repo para **três** coisas
  da Rota C: `:11-14` auto-inclusão do próprio arquivo no `paths:`;
  `:18` `workflow_dispatch:` (rota de recuperação); `:21-23`
  `concurrency` com `cancel-in-progress: true`. **E** a armadilha: o
  gatilho dele é só `pull_request`, que aqui seria morto (F2).
- Os **11** workflows que combinam `push:` + `paths:` corretamente
  (`actionlint`, `adapter-live`, `benchmarks`, `chaos`, `formal-verify`,
  `mcp-smoke`, `otel-smoke`, `perf-profile`, `red-team`, `smoke-install`,
  `translations-drift`) — o conjunto real de precedentes de filtro deste
  repo (F9). `paths-ignore` não tem nenhum.
- `.github/workflows/smoke-install.yml:150-172` — o método de
  dimensionamento de timeout que este repo pratica (5→8→20→25→32, fator
  2-3x, nota anti-noise-band); `.github/workflows/validate.yml:1181-1186`
  — o dimensionamento por soma de pior caso.
- `README.md:8`, `.claude/adr/ADR-021-e2e-harness-contract.md:132`,
  `.claude/adr/ADR-050-native-subagents-dual-rail.md:73-74`,
  `.github/workflows/GOVERNANCE-MAP.md` — as três superfícies derivadas
  **não vigiadas** que a Rota C move (F10).
- `.github/workflows/ownership-nightly.yml:4-9` — o precedente de "split
  vira WORKFLOW separado, não entrada de filtro", e a declaração de que
  um runner 2-core roda 2-3x mais devagar.
- `.github/workflows/shadow-ci.yml:65-75` — o molde de detecção por
  `git diff` que a Rota B copiaria, **e** o motivo de não copiá-lo cru:
  é PR-only.
- `tests/integration/test_threat_model_coverage.py:25-36,309-380` — o
  contraexemplo que mata `docs/**` na denylist; e `:199-215`
  (`validate_file_ref`) — a razão de a prova de inércia ter de rodar
  **rename/delete**, não mutação de conteúdo (§4).
- `.claude/scripts/local/verify-counts.sh:324-326,724` +
  `docs/CTO-GUIDE.md:46` — a contagem exata de workflows (F4).
- `templates/.github/workflows/validate.yml.template:22-23` — o adopter
  em `ubuntu-latest`; fora do alcance desta mudança (F3).

## Progress log

- 2026-09-04 (S344, Owner presente, land combinado): `p184-derive-ci-cost` landado — W0 DERIVADA (US5/US1/US0b) sobre os 167 runs de push em `main` da janela 01-21/08 numa unica base por-JOB (`Ceo`, cada job arredondado ao minuto): a manchete caiu, a hipotese pre-registrada da US5 esta REFUTADA (o que falha e a premissa de custo por run uniforme — docs-only 97,62 min contra 68,09 de codigo) e o residuo de +6,2 % fica com a causa NOMEADA. Derivacao completa em `.claude/plans/PLAN-184/w0/w0-derivation-S344.md`; W0-US0 (N e M) segue decisao do Owner. Rail r1 (duas lanes codex em paralelo): 2 P2 declarados neste pack — a linha de metodo omite o `PRED_HEAD` (a aritmetica dos 167 intervalos foi REFUTADA em disco: o instrumento parte de um predecessor explicito) e a subsecao «Ressalva de composicao» fica sem marcador de substituicao, com o numero novo nomeando o velho dois paragrafos acima. Registro em `.claude/plans/PLAN-184/w0/s344-p184-derive-ci-cost/rail-land-round-1.md`. Bateria: 62 passed / 2 skipped nos testes de plano dos hooks, suite `.claude/scripts/tests/` completa e 6 gates de corpus rc 0 sobre a arvore STAGED; oraculo `--is-canonical` = 0 nos 2 paths.
