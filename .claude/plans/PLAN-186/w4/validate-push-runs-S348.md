# PLAN-186 W4 — amostra S348 dos runs de `push` do Validate (AC-6 / AC-11)

> Medição bruta, sem previsão, alvo ou claim de velocidade (`AGENTS.md:9-11`).
> Serve de amostra ADICIONAL para as duas metades ◐ dos AC-6 e AC-11; **não
> flipa nenhum AC** — a metade Smoke do AC-6 segue aberta e o critério do AC-11
> (≤ 1,3× do baseline) é julgado sobre a matriz da W4b, que ainda não existe.

## 0. Inputs (a medição lista seus inputs)

- Repositório: o mesmo em que este arquivo vive (`gh repo view --json nameWithOwner`).
- Comandos: `gh run list --workflow validate.yml --event push --branch main --limit 14 --json databaseId,headSha,conclusion,startedAt,updatedAt`;
  para cada run verde: `gh api repos/<owner>/<repo>/actions/runs/<id>` (`run_started_at`, `updated_at`) e
  `gh api repos/<owner>/<repo>/actions/runs/<id>/jobs?per_page=100` (`labels`, `started_at`, `completed_at`, `conclusion`).
- Janela: runs de `push` em `main` entre 2026-09-07 02:40Z e 07:31Z (madrugada S348; **todos os commits são docs/censo/ledgers** — o diff não altera o que o CI executa, logo a variação entre runs é carga de runner, não conteúdo).
- Wall do RUN = `run_started_at → updated_at` (o AC-6 pede `startedAt→completedAt` do RUN; `updated_at` é o carimbo de conclusão que a API expõe — mesma convenção da amostra S344).
- Runs cancelados pelo `concurrency.cancel-in-progress` (push seguinte) ficam FORA da amostra por desenho: só runs `success`.

## 1. AC-6, metade Validate — 6 runs verdes consecutivos de `push` (≤ 14 min: 6/6)

| run id | sha | started (Z) | updated (Z) | wall |
|---|---|---|---|---|
| 34077082310 | `45877e4` | 02:40:48 | 02:52:23 | 11m35s |
| 34079509380 | `26cf9c1` | 03:23:58 | 03:33:53 | 9m55s |
| 34081786949 | `7379379` | 04:04:41 | 04:14:42 | 10m01s |
| 34084393614 | `7c331b4` | 04:47:09 | 04:59:14 | 12m05s |
| 34093210128 | `d00c73a` | 06:58:16 | 07:09:13 | 10m57s |
| 34094829891 | `99c9108` | 07:18:25 | 07:30:15 | 11m50s |

Piso (job-bound) nos três runs detalhados abaixo: `hook-tests-python-matrix (3.9)` 10m50s / 8m55s / 10m22s e `(3.12)` 10m49s / 9m39s / 8m38s — o mesmo job que o AC-6 nomeia como fora do escopo da wave.

## 2. AC-6, metade Smoke — sem run nesta janela; últimos 6 runs verdes de `push` (≤ 45 min: 0/6)

O `smoke-install.yml` não disparou nos commits da noite (filtro de paths). Os últimos seis runs verdes de `push` (ids `34006148257`, `33918569234`, `33874751633`, `33809424817`, `33743649231`, `33630753302`) mediram 92m20s, 88m36s, 92m48s, 92m35s, 90m44s, 82m58s — todos acima de 45 min. A metade Smoke do AC-6 permanece aberta para a matriz da W4b (pack `w4b-gates-v2`, rodadas pendentes).

## 3. AC-11 — runner-minutos por CLASSE de runner nos 3 runs verdes mais recentes

| run id | sha | `Ceo` (pago) | `ubuntu-latest` (grátis) | wall |
|---|---|---|---|---|
| 34084393614 | `7c331b4` | 36,35 | 2,18 | 12,08 |
| 34093210128 | `d00c73a` | 32,78 | 2,18 | 10,95 |
| 34094829891 | `99c9108` | 32,65 | 2,18 | 11,83 |
| **média** | | **33,93** | **2,18** | 11,62 |

Jobs em `Ceo` (por run, minutos): `hook-tests-python-matrix (3.9)` 10,83 / 8,92 / 10,37; `(3.12)` 10,82 / 9,65 / 8,63; `Governance, health, contamination, shellcheck…` 6,90 / 6,60 / 6,57; `hook-tests-dual-rail (0)` 2,53 / 2,75 / 2,63; `(1)` 2,72 / 2,75 / 2,27; `E2E integration tests` 2,25 / 1,92 / 1,90; `Formal verification mutation harness` 0,30 / 0,20 / 0,28. Em `ubuntu-latest`: `opus-4-7-profiler-smoke` ≈ 2,0 e `Hook stdout/exit-code contract oracle` ≈ 0,17.

**Contra o baseline S344 (candidato do AC-11: `Ceo` 42,88 / 36,67 / 45,33, média 41,63; `ubuntu-latest` ≈ 2,1):** a amostra S348 dá `Ceo` 0,82× da média S344 com o MESMO shape de jobs (nenhum workflow mudou entre `8003b65` e `99c9108` — `git log 8003b65..99c9108 -- .github/workflows/validate.yml` vazio). A diferença é variância de runner/carga, não ganho: os dois conjuntos são «baseline LOCAL pré-matriz» e a régua do AC-11 (≤ 1,3×) só se aplica quando a matriz da W4b existir. Registrado para que o julgamento use SEIS amostras e não três.

## 4. O que esta amostra NÃO diz

- Não prova o AC-6 inteiro (Smoke aberta) nem o AC-11 (sem matriz para comparar).
- Não converte runner-minutos em dólares (o AC-11 pede a conversão no julgamento; a tarifa do runner `Ceo` não está neste repo).
- `updated_at` do run pode incluir segundos de pós-processamento depois do último job; a convenção é a mesma da amostra S344, logo as séries são comparáveis entre si.
