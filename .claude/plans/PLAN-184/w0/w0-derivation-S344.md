# PLAN-184 W0 — derivação dos números (S344, 2026-09-04)

> **O que este arquivo é:** a medição que fecha **W0-US0b**, **W0-US1** e
> **W0-US5** do PLAN-184. Todo número abaixo veio de um comando rodado
> nesta sessão, e o comando está ao lado. Nada aqui decide: **N** e **M**
> do pré-registro (US0) continuam sendo decisão do Owner.
>
> **Read-only.** Nenhuma chamada `gh` mutante; nenhum workflow editado.

## 0. Janela, unidade e base

| dimensão | valor | como |
|---|---|---|
| Janela | `2026-08-01..2026-08-21` — runs reais de `2026-08-02T15:00:51Z` a `2026-08-21T14:22:02Z` | `gh api .../actions/workflows/304390339/runs -f event=push -f branch=main -f created=2026-08-01..2026-08-21` |
| Runs | **167**, `run_number` **119..285 contíguos** (zero buracos) | contagem do TSV acima |
| Unidade | **PUSH** (`before...after`), nunca commit — **US0b** | `git diff --name-only head[i-1] head[i]` sobre os 167 heads |
| Classe de runner | do `runs-on` do `validate.yml` **no sha daquele run** | `git show <sha>:.github/workflows/validate.yml` + `yaml.safe_load` |
| Preço | US$ 0,022/min no runner pago `Ceo`; `ubuntu-latest` = US$ 0 em repo público | §1 do plano |
| Base de custo | minutos pagos com **cada JOB arredondado para cima ao minuto** (regra de faturamento do Actions); a leitura de *wall* cru aparece ao lado | — |
| Base de tempo | **US$/dia-calendário** (W0-US4), `US$/dia × dias-da-janela` | — |

**Os 167 heads são todos alcançáveis localmente e todos estão em
`--first-parent main`** (`on_first_parent=167 off=0`), logo
`head[i-1]..head[i]` é exatamente a união do push.

### Positive controls do instrumento

| controle | resultado |
|---|---|
| nomes de job que não casam nenhum `runs-on` | **0** |
| jobs sem `started_at`/`completed_at` | **0** |
| durações negativas | **0** |
| classe derivada do YAML **vs** `labels` da API de jobs | **0 divergências** em 1.838 jobs |
| distribuição por classe | `Ceo` 1.500 jobs, `ubuntu-latest` 338 |

### Duas armadilhas do instrumento, medidas e curadas

1. **`filter=all` na API de jobs conta duas vezes.** Um re-run cria um
   registro NOVO para *todo* job da tentativa anterior, inclusive os que
   não foram re-executados — mesmos `started_at`/`completed_at`. **13
   runs** têm mais de uma tentativa; sem dedup, **109 registros**
   duplicados entrariam na soma. Dedup: um `(name, started_at,
   completed_at)` = uma execução física. Re-execuções REAIS (timestamps
   distintos) ficam: são **34**, valendo **132 min pagos (US$ 2,90)**.
2. **`/actions/runs/<id>/timing` não arbitra nada aqui.** Ele responde
   `{"billable":{"UBUNTU":{"total_ms":0,...}}}` para estes runs — repo
   público, minutos de runner grande não aparecem. **Lacuna nomeada:** o
   único instrumento por-run que existe é o wall-clock por job. Isto é a
   mesma classe da OQ-12 (o endpoint de billing não atribui por workflow
   nem por repositório).

---

## 1. W0-US0b — a unidade é o PUSH

```
pushes com mais de um commit: 21 de 167 (máximo: 21 commits num push)
pushes com diff VAZIO (force-push / no-op): 0
```

**Correção ao texto atual da US0b: são 21, não 20.** O resto do enunciado
sobrevive: o maior push carrega 21 commits, e a contagem por commit
(236/239 commits da §1) não é a contagem que o `paths-ignore` avalia.

---

## 2. W0-US5 — reconciliação por JOB, e a causa do resíduo

### 2.1 Minutos por JOB por run (n = 167)

| bucket (job) | jobs | min totais (wall) | **min/run medido** | plano §1 | delta | `runs-on` |
|---|---|---|---|---|---|---|
| `hook-tests-python-matrix` | 669 | 7.391,2 | **44,26** | 41,8 | **+5,9 %** | `Ceo` |
| `hook-tests-dual-rail` | 333 | 2.790,4 | **16,71** | 15,5 | **+7,8 %** | `Ceo` |
| `Governance, health, contamination, shellcheck` | 166 | 2.619,6 | **15,69** | 15,0 | **+4,6 %** | `Ceo` |
| `Formal verification mutation harness` | 166 | 827,6 | **4,96** | 4,7 | **+5,4 %** | `Ceo` |
| `E2E integration tests` | 166 | 637,0 | **3,81** | 3,4 | **+12,2 %** | `Ceo` |
| `opus-4-7-profiler-smoke` | 173 | 450,6 | 2,70 | — | — | `ubuntu-latest` |
| `Hook stdout/exit-code contract oracle` | 165 | 31,4 | 0,19 | — | — | `ubuntu-latest` |
| **soma dos 5 pagos** | | | **85,42** | **80,40** | **+6,2 %** | |

**Totais da janela:** `Ceo` **14.265,7 min** de wall cru, **15.045,0 min**
com o arredondamento de faturamento (**US$ 330,99** = **US$ 15,761/dia**);
`ubuntu-latest` **482,1 min** (US$ 0).

### 2.2 O delta de 6,2 % — causa NOMEADA (o Check pede < 5 % **ou** a causa)

O plano afirma **13.428 min**. Nenhuma base construível por-job reproduz
esse número:

```
H0 wall cru, todo job Ceo, todas as tentativas   = 14.265,7   (+6,2 % vs 13.428)
H1 arredondado por job (faturamento)             = 15.045,0
H2 wall cru, só registros da tentativa 1         = 14.150,8
H3 wall cru, excluindo jobs cancelled/skipped    =  6.412,4
H4 tentativa 1 E não-cancelados                  =  6.297,4
```

**Causa nomeada: o `13.428` é uma agregação por WORKFLOW que esta
derivação não consegue reproduzir a partir dos jobs; a base que
sobrevive é a por-JOB, porque é a única com comando.** O resíduo é
**+6,2 %** e está declarado, não escondido.

### 2.3 A hipótese pré-registrada da US5 está REFUTADA

A US5 aposta em «erro de classificação de ~23-24 dos 106 runs só-docs».
**Não é isso.** Reproduzindo a classificação original (regra por PREFIXO,
cega à extensão — §3 abaixo), a atribuição bate:

| | plano | medido | delta |
|---|---|---|---|
| runs só-docs | 106 | **98** | −7,5 % |
| minutos só-docs | 10.407 | **10.035** | −3,6 % |

O que falha é **a premissa de custo por run UNIFORME**:

| classe do push | runs | min pagos | **min/run (arred.)** | min/run (wall) | jobs `cancelled` | runs `cancelled` |
|---|---|---|---|---|---|---|
| só-docs | 98 | 10.035,0 | **102,40** | 97,62 | 29,3 % | 52,0 % |
| toca código | 69 | 5.010,0 | **72,61** | 68,09 | 19,3 % | 40,6 % |
| todos | 167 | 15.045,0 | 90,09 | 85,42 | 25,1 % | 47,3 % |

**Um push só-docs custa 43 % MAIS que um push de código** (97,62 vs 68,09
min de wall). O `80,4` da §1 é média global e, aplicado por bucket,
produz exatamente o `+1.884,6 / −1.910,4` que a nota de reconciliação
achou — o delta é artefato da média, não de classificação errada.

### 2.4 Fato colateral que a reconciliação expõe

**431 jobs `Ceo` terminaram `cancelled`, carregando 7.853,4 min de wall
(US$ 172,77) — 55 % de todos os minutos pagos da janela.** Não é escopo
deste plano (é a OQ-4), mas é o termo dominante do gasto, maior que
qualquer economia que A1 ou A2 possam entregar. Registrado com número.

---

## 3. W0-US1 — a denylist DERIVADA, ordenada por fração de custo

### 3.1 Censo de prefixos `.md` observados nos diffs dos 167 pushes

```
*.md                          .claude/adr/**/*.md        .claude/commands/**/*.md
.claude/governance/**/*.md    .claude/plans/**/*.md      .github/**/*.md
SPEC/**/*.md                  docs/**/*.md               npm/**/*.md
templates/**/*.md             .claude/**/*.md
```

Nenhum foi escrito de memória: são os prefixos que **aparecem** nos
diffs. `docs/**` e `.github/**` são **exclusão dura** (§4 do plano / AC-4).

### 3.2 Lista ordenada — gramática da W1 (`<prefixo>/**/*.md`), sem `docs/` e sem `.github/`

Ordem = ganho marginal em minutos pagos atribuíveis à A1 (os 4 jobs
pesados), por cobertura gulosa.

| # | entrada | min A1 acumulados | marginal | pushes puláveis | fração acumulada |
|---|---|---|---|---|---|
| 1 | `.claude/plans/**/*.md` | 1.715,0 | 1.715,0 | 40 | 13,9 % |
| 2 | `*.md` (raiz) | 1.899,0 | 184,0 | 44 | 15,4 % |
| 3 | `npm/**/*.md` | 1.986,0 | 87,0 | 46 | 16,1 % |
| 4 | `.claude/governance/**/*.md` | 2.041,0 | 55,0 | 47 | 16,5 % |
| 5 | `.claude/commands/**/*.md` | 2.095,0 | 54,0 | **48** | **17,0 %** |

**Soma declarada: 5 entradas explicam 2.095,0 de 12.341,0 minutos pagos
atribuíveis à A1 = 17,0 % (US$ 46,09 de US$ 271,50); 48 de 167 pushes.**

`.claude/adr/**/*.md`, `SPEC/**/*.md` e `templates/**/*.md` **não
entraram**: ganho marginal **zero** — todo push que os toca também toca
algo fora da lista. (`.claude/adr/**` continua suspeito pela porta da §4;
aqui ele nem paga a própria entrada.)

Com `docs/**` e `.github/**` no pool (contrafactual, **não** é a
recomendação): 6 entradas, 2.193,0 min = 17,8 %, 50 pushes.

### 3.3 O que a GRAMÁTICA custa — o achado que decide a OQ-11

A regra da W1 exige âncora de extensão (`/**/*.md`) justamente para não
pré-aprovar o código encenado que vive sob `.claude/plans/`. **O preço
disso, medido:**

| regra de classificação | pushes puláveis | minutos A1 | US$/dia (A1) |
|---|---|---|---|
| **B** — prefixo docs-ish, **cega à extensão** (a regra da medição original) | **98**/167 | 8.301,0 | **8,696** |
| **C** — gramática da W1 `<prefixo>/**/*.md`, `docs/` e `.github/` fora | **48**/167 | 2.095,0 | **2,195** |

**A âncora `/**/*.md` remove 50 pushes e 6.206 minutos — 75 % do prêmio.**
As extensões que causam a rejeição, contadas dentro desses 50 pushes:

```
.py 174 | .sha256 46 | .sh 44 | .txt 41 | .patch 30 | .yml 17 | .log 8 | .asc 6 | .json 4
```

Isto não é defeito da gramática: é o repositório dizendo que
`.claude/plans/**` **não é** um diretório de documentos. A gramática está
certa e o prêmio é pequeno — as duas coisas ao mesmo tempo.

---

## 4. As magnitudes, DERIVADAS — e o efeito da A0 já landada

A **A0 landou em `5ff06c9` (2026-08-23), DEPOIS da janela**: no `push` a
matriz roda só as versões de fronteira. Toda projeção da A1 tem de ser
lida **depois** da A0, senão conta duas vezes o mesmo minuto.

| | pré-A0 (janela como medida) | **pós-A0 (o que ainda há para ganhar)** |
|---|---|---|
| gasto total no runner pago | 15.045,0 min · US$ 330,99 · **US$ 15,761/dia** | 11.262,0 min · US$ 247,76 · **US$ 11,798/dia** |
| **A1** (gramática W1, 48 pushes) | 2.095,0 min · US$ 46,09 · **US$ 2,195/dia** | 1.377,0 min · US$ 30,29 · **US$ 1,443/dia** |
| A1 sob a regra B (contrafactual) | 8.301,0 min · US$ 182,62 · US$ 8,696/dia | 5.787,0 min · US$ 127,31 · US$ 6,063/dia |
| **A2** isolada | 1.676,0 min · US$ 36,87 · **US$ 1,756/dia** | idem (A2 não toca a matriz) |
| **A2** marginal depois da A1 | 1.506,0 min · US$ 33,13 · **US$ 1,578/dia** | idem |
| sobreposição A1 ∩ A2 | **US$ 3,74** na janela | idem |
| fração só-docs do custo total | **18,1 %** (regra C) / 66,7 % (regra B) | 17,8 % / 66,8 % |

**A própria A0, medida por replay da janela: US$ 83,23 em 21 dias =
US$ 3,963/dia.** O debate r2 previu ~US$ 3,15/dia — derivação
independente, mesma ordem, e a A0 é maior do que se pensava.

### Ressalva de composição que o AC-6 tem de preservar

47 % dos runs da janela terminaram `cancelled` por
`concurrency.cancel-in-progress: true` (F6). Um push filtrado por
`paths-ignore` **não cria run**, logo **não cancela** o run pesado em
voo do push de código anterior — que então roda até o fim. Parte da
economia acima é devolvida por esse caminho. **Não está quantificada
aqui**, e a baseline pós-corte do AC-6 tem de medir isso ou declarar que
não mede.

---

## 5. Comandos (todos read-only)

```bash
# 1. os 167 runs
gh api --paginate -X GET \
  "repos/Canhada-Labs/ceo-orchestration/actions/workflows/304390339/runs" \
  -f event=push -f branch=main -f created="2026-08-01..2026-08-21" -f per_page=100 \
  --jq '.workflow_runs[] | [.id,.run_number,.head_sha,.created_at,.run_started_at,.updated_at,.status,.conclusion,.event,.head_branch] | @tsv'

# 2. jobs de cada run (startedAt/completedAt/labels), um arquivo por run
gh api -X GET "repos/Canhada-Labs/ceo-orchestration/actions/runs/<id>/jobs" \
  -f per_page=100 -f filter=all

# 3. classe de runner no sha daquele run
git show <head_sha>:.github/workflows/validate.yml   # + yaml.safe_load -> jobs[].runs-on

# 4. a unidade PUSH
git diff --name-only <head[i-1]> <head[i]>

# 5. o endpoint que NÃO serve (lacuna nomeada)
gh api "repos/Canhada-Labs/ceo-orchestration/actions/runs/<id>/timing"
#   -> {"billable":{"UBUNTU":{"total_ms":0,...}}}
```

Os scripts de derivação e as saídas brutas ficam no pacote da sessão
(`<PK>/p184-derive-ci-cost/`), fora do repositório: `derive.py`
(agregação por job + cobertura gulosa), `derive2.py` (tentativas,
regras A/B/C), `derive3.py` (hipóteses do resíduo, replay pós-A0),
`derive4.py` (tabela consolidada), `derive5.py` (causa do resíduo).

---

## 6. Calibração para o pré-registro (W0-US0) — **não** é a decisão

O Owner fixa **N** (US$/dia) e **M** (%). Os valores derivados que
calibram a escolha, na base que a W1 de fato vai implementar
(gramática `<prefixo>/**/*.md`, **pós-A0**):

| grandeza | valor derivado |
|---|---|
| teto da A1 | **US$ 1,443/dia** |
| fração de custo só-docs | **17,8 %** |
| (leitura pré-A0, para comparar com o texto antigo) | US$ 2,195/dia · 18,1 % |
| (contrafactual regra B, sem a âncora de extensão) | US$ 6,063/dia · 66,8 % |
| A0 já entregue (referência de ordem) | US$ 3,963/dia |
| gasto total remanescente do `validate.yml` | US$ 11,798/dia |

O texto anterior da US0 calibrava com «teto ≈ US$ 4,04/dia, fração ≈
58,8 %». **Os dois números não sobrevivem à gramática que a própria W1
adotou no round 2.** Se **N** ficar em qualquer valor ≥ US$ 1,50/dia, o
pré-registro fecha o plano — e essa é a leitura honesta do que foi
medido, não uma recomendação.

**N e M são decisão do Owner.**
