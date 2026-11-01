# M15-22 — Validação do backlog v1.4.4

Data: 2026-11-01. Branch: `tracks/m15-ceo-orchestration-v144`.
Base inspecionada: `eb7b6f19254f3662309e036a85f71ca268199dbc`.

## Escopo e método

O roteiro pede inspeção do commit, execução da suíte completa e levantamento
das pendências da v1.4.4. O commit altera quatro arquivos de planejamento;
acrescenta os itens 28–30 ao backlog e registra o fechamento da v1.4.3-rc.1.
Este trabalho produz o relatório de validação, sem implementar as curas do backlog.

Ambiente isolado em `/var/tmp/pista-22/venv`: Python 3.12.3, pytest 8.4.2,
pytest-xdist 3.8.0, PyYAML 6.0.3, hypothesis 6.100.0 e jsonschema 4.21.1.
`PATH=/var/tmp/pista-22/venv/bin:$PATH` e
`TMPDIR=/dev/shm/pista-22/m15-22-run` (tmpfs verificado, fora de árvore Git).
A primeira tentativa em cópia sem `.git` foi interrompida: três módulos exigem
metadados Git para coletar. A execução válida usa a worktree solicitada e todos
os 16 diretórios de `pytest.ini:39`, em duas parcelas complementares conforme
o tratamento de `serial` em `conftest.py` e no CI. Não foram removidos caches
de bytecode antes dos testes.

## Resultados

`python3 -m pytest -n 8 -m 'not serial' --strict-markers --tb=short -q`
terminou com código 1. Linha final literal:

```text
4 failed, 16034 passed, 144 skipped, 9 xfailed, 1 xpassed, 41 warnings in 332.94s (0:05:32)
```

As três falhas de `tests/integration/test_install_npm_smoke.py` ocorreram em
`TestTarballBuild::test_build_succeeds_and_produces_tgz`,
`TestTarballBuild::test_tarball_contains_expected_files` e
`TestSmokeInvoke::test_smoke_install_and_shim_help_invocation`.
O npm 12.2.1 da máquina retorna um objeto indexado pelo nome do pacote em
`npm pack --dry-run --json`; `scripts/install-npm.sh:157` espera `files` no
objeto externo e lança `KeyError`. O CI fixa npm 11.20.0 em
`.github/workflows/npm-publish.yml:113`; essa versão foi instalada em
`/var/tmp/pista-22/npm-toolchain` para repetir os casos.

A outra falha é
`.claude/scripts/tests/test_check_staleness.py::TestRealRepo::test_real_repo_no_unhealthy_today`:
PLAN-194 e PLAN-195 são classificados como `unhealthy`, com idade de 32 dias,
`status: executing` e ausência de `related_commits` no frontmatter. A regra é
`plan_executing_abandoned_candidate` em `check-staleness.py:207–221`; ela mede
o frontmatter, não a existência de commits no histórico. O relatório medido
tem 19 achados. A data e o estado dos planos foram preservados.

`python3 -m pytest -m serial --strict-markers --tb=short -q`
terminou com código 0. Linha final literal:

```text
683 passed, 9 skipped, 16191 deselected, 4 xfailed, 2 xpassed in 147.95s (0:02:27)
```

Repetição com
`PATH=/var/tmp/pista-22/npm-toolchain/node_modules/.bin:$PATH` e comando
`python3 -m pytest tests/integration/test_install_npm_smoke.py .claude/scripts/tests/test_check_staleness.py::TestRealRepo::test_real_repo_no_unhealthy_today --strict-markers --tb=short -q`:

```text
1 failed, 6 passed in 23.28s
```

Código 1: os seis testes npm passaram; o mesmo nodeid de staleness continuou
vermelho. **Não foi comprovado 100% verde.** Os resultados anteriores não
são substituídos por essa repetição. `skipped`, `xfailed` e `xpassed` estão
explicitados nas linhas originais; não representam fechamento do backlog.

`bash .claude/scripts/validate-governance.sh`, na cópia isolada, retornou 0:

```text
  Errors:   0
  Warnings: 65
PASS: Governance files validated.
```

## Pendências da v1.4.4

- O [backlog](.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md) está em `draft`,
  contém 30 títulos de itens e 28 critérios de sucesso desmarcados. Contagens
  derivadas do conteúdo, sem inferir fechamento pelo resultado de testes antigos.
- `python3 -m pytest --collect-only -q -k fu144` retornou **5**, com a linha
  literal `no tests collected (16888 deselected) in 6.18s`. A convenção do plano
  (linhas 71–74) exige `fu144` nas novas regressões: nenhuma está coletável.
- Seis arquivos citados nos critérios ainda estão ausentes:
  `.claude/hooks/tests/test_spool_state_amend4.py`,
  `.claude/hooks/tests/test_claude_md_excludes.py`,
  `.claude/hooks/tests/test_spool_writer_signal_chain.py`,
  `.claude/scripts/tests/test_ceo_restore.py`,
  `.claude/scripts/tests/test_python_subprocess_rc_census.py` e
  `.claude/scripts/tests/test_subprocess_timeout_group_census.py`.
- As dez refs `refs/s363/*` citadas no plano estão ausentes. Há dois branches
  locais; o critério do item 20 pede pelo menos 76. Esses pré-requisitos não
  foram fabricados para tornar o check verde.
- Item 28, P1: `diagnose-output-hook.py:44–50` preserva `CEO_AUDIT_LOG_PATH`
  herdado ao montar o ambiente do filho. Constatação por leitura; o diagnóstico
  não foi executado contra auditoria real. O teste do canário permanece pendente.
- Item 29, P2: a chamada isolada a `record_ids([b'{"record_id":[]}\n'], True,
  {'0' * 32})` reproduziu `TypeError: unhashable type: 'list'` em
  `check-audit-real-loss.py:108`.
- Item 30, P2: ambos os verificadores, executados com `--help`, sem
  `PYTHONDONTWRITEBYTECODE` e com cache redirecionado a pasta descartável,
  retornaram 0 e produziram `.pyc` de auxiliares locais. Foram observados
  `runtime_paths` e `_lib/__init__` em ambos, mais `audit_spool_state` no
  `check-audit-real-loss.py`. Logo, o sucesso de `--help` não prova ausência
  de escrita. Os três itens ainda não têm nomes de testes definidos no plano.

## Entrega

O relatório é entregue também em `/dev/shm/pista-22/RELATORIO-M15-22.md`.
Nenhum caso de teste foi adicionado; mutantes novos não se aplicam a esta
validação documental. A matriz completa de versões Python, os adapters live,
os cortes de release e as medições pagas do item 22 não são certificados por
esta execução local.

Pré-checagem documental: números acompanhados das linhas medidas, pendências
explicitadas e alteração limitada a este relatório. A aprovação da suíte
permanece bloqueada pelo nodeid de staleness; a v1.4.4 mantém os checks
pendentes descritos acima. A correção do frontmatter exige reconciliar os
planos com seu histórico real; este relatório não altera seus estados nem
reduz os critérios de teste.
