# PLAN-186 W4 — amostra S363 dos runs de `push` do Validate e do Smoke (AC-6 / AC-11)

> Medição bruta, sem previsão, alvo ou claim de velocidade (`AGENTS.md:9-11`).
> Amostra ADICIONAL para as metades ◐ dos AC-6 e AC-11, no mesmo formato de
> `validate-push-runs-S348.md`. **Não flipa nenhum AC.** O fato novo desta amostra é
> a classe de runner: desde 2026-10-11 o `push` do `main` roda o Validate num
> runner self-hosted, e a série deixa de ser comparável à de S344/S348.

## 0. Inputs (a medição lista seus inputs)

- Repositório: o mesmo em que este arquivo vive (`gh repo view --json nameWithOwner`).
- Medido em 2026-10-12, por volta de 13:40Z, com `origin/main` = `c76b61c1`.
- Comandos:
  - `gh run list --workflow=validate.yml --branch=main --event=push --status=success --limit 8 --json databaseId,headSha,startedAt,updatedAt,conclusion`;
  - o mesmo com `--workflow=smoke-install.yml`;
  - por run: `gh api repos/<owner>/<repo>/actions/runs/<id>` (`run_attempt`, `run_started_at`, `updated_at`) e
    `gh api repos/<owner>/<repo>/actions/runs/<id>/jobs?per_page=100` (`labels`, `runner_group_name`, `started_at`, `completed_at`).
- Wall do RUN = `run_started_at → updated_at`, a mesma convenção das amostras S344 e S348.
- Só runs `success` de 1.ª tentativa (`run_attempt` = 1). Um run re-executado tem
  `run_started_at` da nova tentativa e a soma de jobs da última: fica fora
  (caso visto: `37949682452`, tentativa 2, wall aparente de 1m59s).

## 1. AC-6, metade Validate — 6 runs verdes de `push` (≤ 14 min: 6/6, todos em `canhada-ci`)

| run id | sha | started (Z) | updated (Z) | wall | runner |
|---|---|---|---|---|---|
| 38254592868 | `c76b61c1` | 2026-10-12 13:16:57 | 13:25:45 | 8m48s | self-hosted `canhada-ci` |
| 38238421750 | `3e32a1ff` | 2026-10-12 10:46:27 | 10:55:17 | 8m50s | self-hosted `canhada-ci` |
| 38196822161 | `5743e565` | 2026-10-12 02:42:11 | 02:50:34 | 8m23s | self-hosted `canhada-ci` |
| 38194807891 | `dc805ed5` | 2026-10-12 02:11:22 | 02:19:52 | 8m30s | self-hosted `canhada-ci` |
| 38155240029 | `2a815a16` | 2026-10-11 16:23:14 | 16:30:48 | 7m34s | self-hosted `canhada-ci` |
| 38144760679 | `95ba98c4` | 2026-10-11 13:50:14 | 13:58:00 | 7m46s | self-hosted `canhada-ci` |

**A troca de classe.** `runs-on` do `validate.yml` passou a ser condicionado por
`vars.VM_CI_ENABLED` no `push`/`schedule`/`workflow_dispatch` do `main` (commit
`29e9e2a`, 2026-10-09): com a variável em `1`, os jobs vão para
`["self-hosted","Linux","X64","canhada-ci"]`; sem ela, para `ubuntu-latest`. O último
run de `push` em `Ceo` é `38052044220` (2026-10-10 12:27Z). O primeiro em
`canhada-ci` é `38099038933` (2026-10-11 01:00Z). Nos 3 runs detalhados em §3, os 9 jobs
reportam `runner_group_name` = `vm-trusted-ci`.

**Antes da troca** (verdes de 1.ª tentativa, `Ceo` + `ubuntu-24.04` + `ubuntu-latest`):

| run id | sha | started (Z) | wall |
|---|---|---|---|
| 38052044220 | `bc803a7a` | 2026-10-10 12:27:54 | 16m58s |
| 37944657608 | `c8ae0bab` | 2026-10-09 14:30:16 | 13m47s |
| 37930995454 | `6ccde6b0` | 2026-10-09 12:35:04 | 15m56s |
| 37924183139 | `6710a9d5` | 2026-10-09 11:30:45 | 14m16s |
| 37916505685 | `6e5fafe4` | 2026-10-09 10:15:44 | 16m09s |

1/5 ≤ 14 min antes da troca; 6/6 depois. O `validate.yml` também mudou entre as duas
séries (`c54934d8`, `29e9e2a`, `fc4bf83`), logo a amostra não separa o efeito do
runner do efeito do conteúdo.

## 2. AC-6, metade Smoke — 6 runs verdes de `push` (≤ 45 min: 0/6)

| run id | sha | started (Z) | wall do RUN | job `smoke` (min) |
|---|---|---|---|---|
| 38052044188 | `bc803a7a` | 2026-10-10 12:27:54 | 109m43s | 109,65 |
| 37018370561 | `a0a6df06` | 2026-10-02 14:13:34 | 115m47s | 108,92 |
| 36960931735 | `48f03b3a` | 2026-10-02 03:36:42 | 109m18s | 109,25 |
| 36502140251 | `9b5b1b40` | 2026-09-29 00:14:57 | 96m09s | 96,08 |
| 36494468042 | `3a9a41f0` | 2026-09-28 22:47:47 | 73m45s | 73,68 |
| 35391833905 | `9e9840b2` | 2026-09-18 20:30:34 | 111m13s | 111,17 |

Todos em `ubuntu-latest` (job único `smoke`), todos de 1.ª tentativa. Mediana do wall ≈
109,5 min contra ≈ 91,5 min nos 6 runs da amostra S348 (82m58s–92m48s). O
`smoke-install.yml` não mudou desde `99c9108` (`git log 99c9108..origin/main --
.github/workflows/smoke-install.yml` vazio). Os scripts que ele executa mudaram: `git
diff --shortstat 99c9108 origin/main -- scripts/` = 35 arquivos, +3.418/−325. A amostra
não atribui a subida a runner nem a conteúdo. Folga do maior job (111,17 min) sob o
`timeout-minutes: 150` do job (`smoke-install.yml:337`): 38,8 min. No run `37018370561`
o RUN durou 6,9 min a mais que o job.

## 3. AC-11 — runner-minutos por CLASSE nos 3 runs verdes mais recentes do Validate

| run id | sha | self-hosted `canhada-ci` | `Ceo` | `ubuntu-latest` | wall |
|---|---|---|---|---|---|
| 38254592868 | `c76b61c1` | 26,60 | 0 | 0 | 8,80 |
| 38238421750 | `3e32a1ff` | 24,58 | 0 | 0 | 8,83 |
| 38196822161 | `5743e565` | 25,07 | 0 | 0 | 8,38 |

Jobs (minutos, na ordem dos 3 runs): `hook-tests-python-matrix (3.9)` 7,00 / 7,53 / 7,47;
`(3.12)` 7,37 / 5,92 / 6,68; `Governance, health, contamination, shellcheck` 5,78 / 5,32 /
5,17; `hook-tests-dual-rail (0)` 1,75 / 1,55 / 1,57; `(1)` 1,68 / 1,55 / 1,55; `E2E
integration tests (pytest)` 1,55 / 1,38 / 1,38; `opus-4-7-profiler-smoke` 1,27 / 1,15 /
1,08; `Formal verification mutation harness (pytest)` 0,10 / 0,08 / 0,08; `Hook
stdout/exit-code contract oracle (PLAN-163 T2)` 0,10 / 0,10 / 0,08.

Último verde antes da troca, para referência: `38052044220` (`bc803a7a`) somou `Ceo` 19,42,
`ubuntu-24.04` 16,93 e `ubuntu-latest` 2,15. A classe `ubuntu-24.04` entrou com a perna
3.9 da W1 do PLAN-194 (`c54934d8`).

## 4. O que esta amostra NÃO diz

- Não prova o AC-6 inteiro (Smoke aberta) nem o AC-11, que ainda não tem matriz para comparar.
- O AC-11 nomeia `Ceo` (pago) e `ubuntu-latest` (grátis). Os 3 runs de §3 não usam
  nenhuma das duas. Que classe e que baseline a W4b deve usar é decisão da W4b
  (cerimônia), não desta amostra.
- Não converte minutos em dólares: o custo do runner self-hosted não está neste repo.
- `updated_at` do run pode incluir segundos de pós-processamento depois do último job;
  a convenção é a mesma das amostras S344 e S348.
