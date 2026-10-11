# REVIEW dos PRs #2 e #3 — `runs-on` condicional para os runners da VM (PLAN-194, ratificação VM-CI)

> Revisão técnica MEDIDA, não opinião, dos bytes que os merges dos PRs #2 e #3 puseram nos 2 workflows.
> Medições de 2026-10-11, de ~00:25Z a ~02:15Z (UTC).
> Sujeito: `.github/workflows/validate.yml` e `.github/workflows/coverage.yml` em
> `e21196817b299fe0557ae9c8dcf9e73b9dd4c10c` (merge do PR #3; antes dele, o merge do PR #2 `d7309efae537`;
> pai de ambos na primeira linha, `bc803a7ac0a0`). O `main` está em `e0c5ffc23dc2`, com 6 commits de
> plano depois de `e2119681`, e nenhum deles toca `.github/` (medido: `git diff --stat e2119681 e0c5ffc2 --
> .github/` vazio).
> Registro do que entrou: `vmci/vmci.patch` = `git diff --full-index bc803a7a e2119681 --
> .github/workflows/` (128 linhas, 7098 bytes, sha256
> `e6f5d1f9ecd7586567212d110f200bd4310bcc147f8dfdb7848a8b141f10a37a`; o mesmo com `--no-renames` e com a
> config global do git desligada). O diff de `bc803a7a` a `e2119681` na árvore INTEIRA muda só esses 2
> arquivos.
> O corpo dos PRs e as mensagens dos commits foram lidos como DADO; nenhuma afirmação deles entra aqui
> sem medição própria.

## 0. Como os bytes entraram no `main`

- PR #2, mergeado pelo GitHub em 2026-10-11T00:37:04Z: `bc803a7ac0a0` → `d7309efae537` (pais
  `bc803a7a` + `29e9e2a2`; autor a conta do Owner, committer `GitHub`). Põe o `runs-on` por expressão nos
  8 jobs (§1).
- PR #3, mergeado pelo GitHub em 2026-10-11T01:44:41Z: `d7309efa` → `e21196817b29` (pais `d7309efa` +
  `fc4bf83cf3e8`; autor a conta do Owner, committer `GitHub`). Troca o recuo `'Ceo'` por `'ubuntu-latest'`
  nas 6 expressões que terminavam em `'Ceo'` (`validate.yml` +5 −5, `coverage.yml` +1 −1); nada mais.
- Resultado em `e2119681` (igual em `e0c5ffc2`): `.github/workflows/validate.yml` sha256
  `412a51d9d92d7a7948ea6c920184770386b6214452332fbe6a56642d9cc45f72` (96.546 bytes, blob `a1b8d1124bd6…`) e
  `.github/workflows/coverage.yml` sha256 `bfb751b9d17c9daf087044261438112bd0fbb75c5f43c4b77a3dd6540dfd1f2f`
  (13.925 bytes, blob `4e4919be8063…`). Os 2 são canônicos (oráculo `--is-canonical` = 1 para os dois,
  medido): entraram no `main` sem sentinel assinado, duas vezes.
- A variável de repositório `VM_CI_ENABLED` vale `"1"` desde 2026-10-11T00:37:01Z — 3 s antes do merge do
  PR #2 (API `actions/variables`). Nenhuma variável de organização.
- 1.ª corrida na VM — Validate do push `d7309efa` (run `38099038933`), 2 runners: tentativa 1 `failure`
  às 00:49:48Z, 8 jobs verdes e 1 vermelho (`hook-tests-dual-rail (0)`, por AMBIENTE: `/tmp` dividido
  entre os runners, §4.1); o job `validate` esperou 456 s na FILA (§5). A tentativa 2, só do job vermelho
  (pedida às 01:00:27Z), esperou 154 s com os 4 runners do grupo online e ociosos na leitura das ~01:02Z,
  rodou sozinha de 01:03:03Z a 01:04:35Z e passou (7122 passed, 36 skipped; série serial 496 passed, 2
  skipped) — o run ficou `success`. Passar sozinho é consistente com o diagnóstico, não o prova.
- 2.ª corrida na VM — Validate do push `e2119681` (run `38102851467`), 4 runners: `failure` às 01:50:23Z,
  com 2 jobs vermelhos de novo por AMBIENTE, agora nos runners novos (§4.6): a matriz 3.12 no runner 03
  (4 testes, subprocesso morto por sinal 11) e a matriz 3.9 no runner 04 (100 testes, `libpython3.9.so.1.0:
  cannot open shared object file`, rc 127). O arquivo de ambiente dos runners passou a dar
  `PYTEST_XDIST_AUTO_NUM_WORKERS: 8` (era 24 na 1.ª corrida).
- 3.ª corrida na VM — Validate do push `e0c5ffc2` (run `38103716736`), 4 runners: `failure` às 02:06:35Z,
  só a matriz 3.12, agora no runner 04, com os MESMOS 4 testes mortos por sinal 11 da 2.ª corrida; a 3.9,
  de volta ao runner 01, passou (§4.6).
- O Validate e o Coverage do próprio PR #3 (runs `38100541909` e `38100541954`, `pull_request`) rodaram
  nos runners hospedados padrão — são a medida do risco do PR #3 (§5.1).
- Nada foi alterado no GitHub por esta revisão (variáveis, runners, PRs e configurações só foram LIDOS).

## 1. O que entrou

- 8 jobs passam de `runs-on` literal (ou da expressão da matriz) para uma expressão: 7 no `validate.yml`
  (`validate`, `integration-tests`, `formal-verification-mutation-harness`, `opus-4-7-profiler-smoke`,
  `hook-tests-dual-rail`, `hook-tests-python-matrix`, `hook-stdout-schema-oracle`) e o único job do
  `coverage.yml` (`coverage`). São TODOS os jobs dos 2 arquivos.
- Quando a expressão não manda para a VM, o recuo é o runner de `bc803a7a` com `Ceo` trocado por
  `ubuntu-latest` (o PR #3): `ubuntu-latest` para os 7 jobs que eram `Ceo` ou `ubuntu-latest`;
  na matriz, `ubuntu-24.04` para a 3.9, `ubuntu-26.04` para a 3.14 e `ubuntu-latest` para 3.10–3.12.
  Nenhum job dos 2 arquivos usa mais o `Ceo`. Isso vale para TODO `pull_request` e também para `push` e
  `schedule` com a variável desligada: desligar a variável não devolve ao `Ceo`.
- Fora do `runs-on`, nada muda na semântica: com PyYAML, o YAML dos 2 arquivos antes e depois é igual em
  todas as chaves de topo e em todas as chaves de cada job, exceto `runs-on` (`fallback_eq.py`,
  Apêndice B). O resto do diff são 2 linhas de comentário por job.
- Comentários que os bytes ratificados carregam e que ficaram FALSOS: `validate.yml:1646` («3.10-3.12
  seguem no `Ceo`») e `:1656` («Runner padrao (4 vCPU) = 45 min; `Ceo` (8 nucleos) segue 25») — as pernas
  3.10–3.12 rodam hoje na VM (`push`/`schedule`) ou no `ubuntu-latest` de 4 vCPU (`pull_request`), com
  `timeout-minutes` 25 (§5.1).
- 24 linhas adicionadas têm espaço no fim (as 3 primeiras linhas de cada expressão). `git apply` avisa
  («24 lines add whitespace errors») e aplica; `git apply --whitespace=fix` produz OUTROS blobs
  (`red-control.txt`, R2).
- O `actionlint` deixa de checar o rótulo do runner desses 8 jobs: dentro de expressão ele não confere
  rótulo (o próprio comentário do `validate.yml` sobre o 1.7.7 já registra isso). Medido com o actionlint
  1.7.12 local, nas duas formas do CI (a do job `validate` com `-shellcheck="-S error -e
  SC2002,SC2012,SC2016,SC2129"` e a do `actionlint.yml`), com `-config-file .github/actionlint.yaml`: 0
  achados em `bc803a7a`, em `d7309efa` e em `e2119681`. O CI pina o 1.7.7 (não rodado aqui); os Validate
  dos PRs (runs `38000376122` e `38100541909`) passaram com ele sobre os arquivos de cada PR.

## 2. (a) Tabela-verdade: quando o job vai para a VM

Método: avaliador mínimo do subconjunto de expressões usado (literais, contextos por ponto, `==`/`!=`,
`!`, `&&`, `||`, parênteses, `fromJSON`), com a semântica documentada do GitHub — comparação de strings
SEM caixa, coerção numérica só entre tipos diferentes, `&&`/`||` devolvendo o operando, variável ausente
= `''`. O parser recusa o que não conhece. Auto-teste da semântica: 10/10 (Apêndice B). Entrada: os 2
arquivos de `e2119681`, lidos com PyYAML; cada `runs-on` precisa ser expressão PURA (`${{ … }}` sem texto
em volta — é, nos 8). Espaço avaliado: 6 eventos × 5 refs × 9 valores da variável (× 5 versões na
matriz) = 10.800 combinações.

Job `validate` (os outros 6 jobs sem matriz e o `coverage` dão a MESMA tabela; na matriz, a 3.9 recua
para `ubuntu-24.04` e a 3.14 nunca sai do `ubuntu-26.04`):

| evento | ref | ausente | `"0"` | `"1"` | `"true"` |
|---|---|---|---|---|---|
| `pull_request` | `refs/pull/2/merge` | ubuntu-latest | ubuntu-latest | ubuntu-latest | ubuntu-latest |
| `pull_request` | `refs/heads/main` | ubuntu-latest | ubuntu-latest | ubuntu-latest | ubuntu-latest |
| `push` | `refs/heads/main` | ubuntu-latest | ubuntu-latest | **VM** | ubuntu-latest |
| `push` | `refs/heads/feature-x` | ubuntu-latest | ubuntu-latest | ubuntu-latest | ubuntu-latest |
| `push` | `refs/heads/MAIN` | ubuntu-latest | ubuntu-latest | **VM** | ubuntu-latest |
| `schedule` | `refs/heads/main` | ubuntu-latest | ubuntu-latest | **VM** | ubuntu-latest |
| `workflow_dispatch` | `refs/heads/main` | ubuntu-latest | ubuntu-latest | **VM** | ubuntu-latest |
| `workflow_dispatch` | `refs/heads/feature-x` | ubuntu-latest | ubuntu-latest | ubuntu-latest | ubuntu-latest |
| `pull_request_target` | `refs/heads/main` | ubuntu-latest | ubuntu-latest | ubuntu-latest | ubuntu-latest |

Resultados (saída de `ghexpr_truth.py`, `fallback_eq.py` e `vm_cells.py`):

- O conjunto de células que vai para a VM é EXATAMENTE {`push`, `schedule`, `workflow_dispatch`} ×
  {`refs/heads/main` sem caixa} × {`"1"`}, nos 8 jobs (na matriz, × {3.9, 3.10, 3.11, 3.12}; a 3.14 nunca
  vai para a VM). Valores `"true"`, `"TRUE"`, `" 1"`, `"1 "`, `"01"`, `"1.0"` e ausente NÃO ligam. O
  conjunto é o mesmo em `d7309efa` e em `e2119681`: o PR #3 não mexeu no roteamento para a VM.
- Fora da VM, o valor é o `runs-on` de `bc803a7a` com `Ceo` → `ubuntu-latest` e nada mais: 10.800
  combinações, 7.392 trocadas por esse mapa, 0 diferentes do esperado. Controle: sem o mapa, as mesmas
  7.392 aparecem como diferença; em `d7309efa`, sem mapa, 0 diferenças.
- Controle vermelho do avaliador: 5 mutantes da expressão (sem a cláusula do ref; sem a do evento;
  `!= '0'` no lugar de `== '1'`; `pull_request` na lista; recuo trocado) — os 5 mudam o conjunto ou o
  recuo, em `d7309efa` e em `e2119681` (`red-control.txt`, R5).
- Medido no GitHub, as três pontas: o Validate do PR #2 (run `38000376122`, `pull_request`, variável
  ausente) rodou os 11 jobs nos runners de antes (`Ceo` ×8 jobs, `ubuntu-latest` ×2, `ubuntu-24.04` na
  3.9); o do PR #3 (run `38100541909`, `pull_request`) rodou 10 jobs no `ubuntu-latest` e a 3.9 no
  `ubuntu-24.04`; os pushes de `d7309efa` e `e2119681` (variável `"1"`) rodaram os 9 jobs na VM.
- Caixa: o GitHub compara strings sem caixa, então `refs/heads/MAIN` (um branch de outro nome no git)
  também roteia para a VM pela expressão. Quem impede o job de rodar lá é o GRUPO de runners
  (`restricted_to_workflows: true`, lista com `…/validate.yml@refs/heads/main` e
  `…/coverage.yml@refs/heads/main`), não a expressão. Se a checagem do grupo distingue caixa NÃO foi
  medido. Nos dois casos não há fronteira nova: quem cria `MAIN` já pode empurrar no `main` (§6).
- `workflow_dispatch` é cláusula morta no `validate.yml` (o arquivo não tem esse gatilho); vale só para o
  `coverage.yml`.
- Sem recuo automático: com a variável `"1"` e os runners ocupados ou fora do ar, o job FICA NA FILA — não
  volta ao runner hospedado. Medido: o job `validate` do run `38099038933` ficou 456 s na fila com os 2
  runners ocupados. Desligar = variável ausente ou ≠ `"1"` e re-rodar — e o destino passa a ser o
  `ubuntu-latest` de 4 vCPU, não mais o `Ceo` (§5.1).

## 3. (b) O que cada job precisa do runner

Fatos da VM medidos no log do run `38099038933`: runner `2.338.0`, grupo `vm-trusted-ci`; o arquivo de
ambiente do runner injeta `PYTEST_XDIST_AUTO_NUM_WORKERS=24` e `GOMAXPROCS=32` em todo passo (na 2.ª
corrida, run `38102851467`, `PYTEST_XDIST_AUTO_NUM_WORKERS` já era 8); cada runner tem o seu tool cache,
fora de `/opt/hostedtoolcache` (o `pythonLocation` do log é um diretório por runner); o
`setup-python` achou a 3.11.17 já no tool cache; a perna 3.9 passou o `setup-python` (pelo manifesto,
§3.1, isso exclui Ubuntu 26.04, salvo uma 3.9 posta à mão no tool cache). A versão do sistema
operacional da VM não aparece no log e não foi medida.

| job | dependências do runner (fora do `checkout`/`setup-python`) | na VM (run `38099038933`) |
|---|---|---|
| `validate` | os 19 passos antes do `setup-python` (vários com `python3`: `validate-governance.sh`, `verify-counts.sh`, contaminação, censo do instalador…) usam o `python3` DO SISTEMA; `shellcheck` (se ausente, `sudo apt-get update/install` — exige sudo sem senha); `jq`; `rsync` e `npm`/node (`scripts/npm-rebuild.sh`, `npm pack --dry-run` do gate de packlist); `curl` + `tar` + `sha256sum` e rede até github.com (actionlint 1.7.7 `linux_amd64` conferido por sha256); `git`; PyPI | success, 304 s (371 s) depois de 456 s de fila; 47 skips, como no hospedado |
| `integration-tests` | Python 3.11; PyPI (`pytest==8.*`); `tests/integration` roda o `install.sh` (bash, git) | success, 86 s (hospedado 101 s) |
| `formal-verification-mutation-harness` | Python 3.11; PyPI | success, 17 s (16 s) |
| `opus-4-7-profiler-smoke` | Python 3.11; coreutils `timeout`; caminhos FIXOS em `/tmp` (§4) | success, 68 s (117 s) |
| `hook-tests-dual-rail` ×2 | Python 3.11; PyPI (`pytest==8.*`, `pytest-xdist` sem versão); `-n auto` | (1) success 109 s (116 s); (0) **failure** 49 s |
| `hook-tests-python-matrix` (push: 3.9, 3.12; schedule: + 3.10, 3.11) | Python da matriz (§3.1); PyPI (+ `PyYAML>=6.0`); `-n auto` | 3.9 success 362 s (1016 s no `ubuntu-24.04`); 3.12 success 319 s (438 s) |
| `hook-stdout-schema-oracle` | Python 3.11 | success, 7 s (12 s) |
| `coverage` (só `schedule`/`workflow_dispatch` em `main`) | Python 3.11; PyPI (`coverage==7.6.*`, `pyyaml` sem versão, `pytest==8.*`, `hypothesis==6.100.0`, `jsonschema==4.21.1`); `actions/upload-artifact` | não rodou na VM ainda |

Entre parênteses: o mesmo job no push hospedado de `bc803a7a` (run `38052044220`). Nenhum dos 8 jobs usa
`docker`.

### 3.1 `setup-python` na VM

- No SHA pinado (`a309ff8b`), o `setup-python` descobre o Linux por `lsb_release -i -r -s`
  (`src/utils.ts`, `getLinuxInfo`) e baixa do manifesto do `actions/python-versions`, que só tem builds
  Ubuntu. O instalador Linux do manifesto (`installers/nix-setup-template.sh`) não usa `sudo`; precisa de
  tool cache gravável pelo usuário do runner (`docs/advanced-usage.md`, seção de self-hosted).
- Cobertura do manifesto, linux/x64 (baixado 2026-10-11 ~00:36Z, sha256 `3bffef7a0fdd…`, último commit do
  arquivo `49858b91c92d` 2026-10-10T19:22Z): 3.9 → 16.04 a **24.04** (nada para 26.04); 3.10 → 18.04 a
  26.04; 3.11 e 3.12 → 20.04 a 26.04; 3.14 → 22.04 a 26.04. O PR leva a perna 3.9 do rótulo FIXO `ubuntu-24.04`
  (escolhido pela W1 exatamente porque 26.04 não tem 3.9) para a VM: a VM precisa ser Ubuntu 22.04 ou
  24.04 x64 com `lsb_release` (ou ter a 3.9 posta à mão no tool cache). Hoje a perna passou; um upgrade
  da VM para 26.04 sem a 3.9 no tool cache quebra a 3.9 no `main`.

### 3.2 Testes que PULAM sem uma ferramenta (o gate enfraquece em silêncio)

Pela forma `shutil.which(...)` + skip nos caminhos que esses jobs rodam: `gpg`/`gpg2`
(`test_gpg_verify.py` e `test_session_graph.py` com `skipTest`; a fixture `gpg-keyring-fixture.py` levanta
`GpgUnavailable`), `jq` (2 arquivos), `git` (5 marcas de skip), `shasum` (1). Medido no run `38099038933`: os jobs completos têm o MESMO número
de skips que o hospedado (dual-rail 36 e 2; matriz 3.9 64 e 4; matriz 3.12 62 e 4; E2E 4) — a contagem
igual não prova o MESMO conjunto; a condição de ativação pede o conjunto (§8).

## 4. (c) Gates sensíveis ao runner

### 4.1 Primeira falha medida na VM: `/tmp` compartilhado

`hook-tests-dual-rail (0)`, run `38099038933`: `FAILED
.claude/hooks/tests/test_adequacy_gate.py::test_no_sandbox_leak - AssertionError: ('sandbox dirs must be
cleaned up', ['ceo-adequacy-jwb3ez7a'])` (1 failed, 7121 passed, 36 skipped). O teste lista o diretório
temporário INTEIRO (`tempfile.gettempdir()`, `:85`) atrás de `ceo-adequacy-*`. O job rodou de 00:38:57 a
00:39:46 no runner R2 enquanto a matriz 3.9 (que roda os mesmos testes de hooks) rodava de 00:38:41 a
00:44:43 no runner R1: os 2 runners da mesma VM compartilham `/tmp`. Num runner hospedado o `/tmp` é da VM
efêmera do job. Classe: «teste supõe `/tmp` privado do job». A tentativa 2 do mesmo job, sozinha, passou
(§0).

Condição de infraestrutura (§8, item 1): `TMPDIR` próprio por runner, no `.env` de cada runner (o
`tempfile` do Python e o `mktemp` respeitam `TMPDIR`), OU runners descartáveis (um job por runner,
máquina ou contêiner novo). O `TMPDIR` por runner separa runners simultâneos, mas NÃO cobre: a sobra de
um job morto no mesmo runner (pede limpeza no início de cada job — o hook de início de job do runner),
nem os caminhos `/tmp/...` escritos por extenso no `validate.yml` (§4.2), que ignoram `TMPDIR`.

### 4.2 Caminhos fixos em `/tmp` no próprio `validate.yml`

`/tmp/docs-freshness.out` (job `validate`), `/tmp/hook-latency-attempt-N.json` e `/tmp/floor.json` (job
`opus-4-7-profiler-smoke`). Com 2+ runners no mesmo `/tmp`, dois runs simultâneos deste repositório
(`push` e `schedule` têm grupos de concorrência distintos) disputam o mesmo arquivo: com o mesmo usuário
Unix, um sobrescreve o outro; com usuários diferentes, o `fs.protected_regular` (padrão do systemd)
recusa o `>` sobre arquivo alheio num diretório com sticky bit — não medido na VM. O grupo de runners
também serve workflows de mesmo nome (`validate.yml`, `coverage.yml`) de um repositório privado da
organização; se forem cópias deste, disputam os mesmos caminhos (conteúdo deles não lido). O conteúdo de
`/tmp/docs-freshness.out` vai para o log e o resumo do job, que são PÚBLICOS neste repositório.

### 4.3 Gate de latência dos hooks (ADR-163)

O `--hook-latency` reprova por teto ABSOLUTO de p95 (180 ms, duro); a chave relativa
(`--relative-advisory`) é só aviso na fase 1. O teto foi calibrado no `ubuntu-latest` (4 vCPU), que é
onde o job rodava. Medido: piso de subprocesso p50 = 10,32 ms no hospedado (run `38052044220`) e 6,67 ms na
VM (run `38099038933`). Numa VM mais rápida o mesmo teto absoluto fica MAIS FROUXO (uma regressão que
reprovaria no hospedado passa); com jobs vizinhos usando todos os núcleos, a contenção derruba o gate
por infraestrutura (rótulo CONTENDED). Os percentis por hook vão para o resumo do passo, não para o log, e
não foram comparados aqui.

### 4.4 `-n auto` e núcleos

Pela fonte do `pytest-xdist` (3.8.0, local), `-n auto` respeita `PYTEST_XDIST_AUTO_NUM_WORKERS` antes de
tudo; senão usa `psutil` se instalado, senão `len(os.sched_getaffinity(0))` (respeita cpuset/afinidade,
não a cota de CPU de cgroup). Na VM a variável valia 24 na 1.ª corrida e 8 na 2.ª (medido): cada job sobe
esse número de workers qualquer que seja o número de núcleos. Com 24: 2 runners = 48 workers, 6 a 8
runners = 144 a 192 workers (2,25× a 3× numa VM de 64 vCPU). Com 8 e 4 runners: 32 workers.

### 4.5 Testes com orçamento de tempo absoluto

Censo por regex (indicador, teto — não prova flake): arquivos `test_*.py` com `timeout=<número>` de
subprocesso / com asserção sobre tempo decorrido (`perf_counter()`/`monotonic()` + `assertLess` ou
`assert <elapsed> <`): `.claude/hooks/tests` 64 / 29; `.claude/scripts/tests` 82 / 9;
`.claude/scripts/optimizer/tests` 0 / 1; `tests/integration` 5 / 0. Conhecido: `test_install_smoke.py`
(`_run_install`, 90 s por chamada). Esses testes foram afinados nos runners hospedados; sobreinscrição
(§4.4) os torna flake de runner.

### 4.6 Segunda corrida na VM: o Python do tool cache fora do lugar de build

Run `38102851467` (push `e2119681`, 4 runners), por AMBIENTE de novo, nos 2 runners novos:

- matriz 3.9, runner 04: 100 testes vermelhos; 87 trazem na própria linha `rc 127` e
  `…/tools/Python/3.9.25/x64/bin/python3: error while loading shared libraries: libpython3.9.so.1.0: cannot
  open shared object file`, e os outros 13 são hooks sem saída (`'{}' not found in ''`) ou oráculos que
  acusam `exit 127` — a mesma família (ex.:
  `test_check_adversary_live.py`, `test_check_workflow_launch.py`, e o
  `test_check_harness_config.py::TestReplay::test_live_positive_controls_all_block`, que acusa «rail NOT
  certified alive» porque os hooks não sobem). Esses testes rodam `sys.executable` num subprocesso com
  ambiente ENXUTO (ex.: `test_check_adversary_live.py:65-76`: só `CLAUDE_PROJECT_DIR`, `HOME`,
  `CEO_AUDIT_LOG_DIR`, `PATH=/usr/bin:/bin`) — sem o `LD_LIBRARY_PATH` que o `setup-python` põe no job.
- matriz 3.12, runner 03: 4 testes vermelhos com o subprocesso morto por sinal 11 (`-11 != 0`), em
  `test_check_adversary_live.py`, `test_check_workflow_launch.py` e
  `test_subagent_model_override_removed.py` — 3 arquivos que, na 3.9 do runner 04, deram `rc 127`. Na 3.ª
  corrida (run `38103716736`, push `e0c5ffc2`) a 3.12 caiu no runner 04 e os MESMOS 4 testes morreram por
  sinal 11: repete, em 2 runners novos; na 1.ª corrida a 3.12 passou no runner 02. Causa NÃO
  diagnosticada.
- Mecanismo, pela fonte: o `actions/python-versions` compila o Python de Linux com `--enable-shared`,
  `--prefix` = o tool cache do runner de BUILD e `-Wl,--rpath=<prefix>/lib`
  (`builders/ubuntu-python-builder.psm1:34-37`; o prefixo vem do `RUNNER_TOOL_CACHE` do builder,
  `builders/python-builder.psm1:50`). Fora desse caminho, o interpretador só acha a `libpython` pelo
  `LD_LIBRARY_PATH` do job; um subprocesso de ambiente enxuto não a acha. Na 1.ª corrida a mesma perna
  3.9 passou no runner 01, também com tool cache próprio — por que lá a `libpython` foi achada NÃO foi
  medido. Os runners não são homogêneos.
- Num runner hospedado o tool cache É o caminho de build, e os mesmos testes passam (runs `38052044220` e
  `38100541909`).

## 5. (d) Concorrência e tempo — a 1.ª corrida na VM contra o hospedado

Jobs que caem na VM: `push` em `main` = 9 (`validate`, `integration-tests`, `formal…`,
`opus-4-7-profiler-smoke`, `dual-rail` ×2, matriz ×2 [3.9, 3.12], `hook-stdout-schema-oracle`);
`schedule` = 11 (matriz ×4; a 3.14 fica no `ubuntu-26.04`) + o `coverage` do cron das 07:00 UTC (o
`coverage` nunca roda em `push`).

Por job, push de `bc803a7a` no hospedado (run `38052044220`, criado 12:27:54Z, todos os jobs começaram às
12:27:56Z) contra o push de `d7309efa` na VM (run `38099038933`, tentativa 1, criado 00:37:07Z; fila =
início do job − criação do run; runner R1/R2 = os 2 runners do grupo naquele run):

| job | hospedado: runner, duração | VM: fila | VM: duração | VM: runner |
|---|---|---|---|---|
| `formal-verification-mutation-harness` | `Ceo`, 16 s | 1 s | 17 s | R1 |
| `hook-tests-dual-rail (1)` | `Ceo`, 116 s | 1 s | 109 s | R2 |
| `hook-stdout-schema-oracle` | `ubuntu-latest`, 12 s | 19 s | 7 s | R1 |
| `opus-4-7-profiler-smoke` | `ubuntu-latest`, 117 s | 26 s | 68 s | R1 |
| `hook-tests-python-matrix (3.9)` | `ubuntu-24.04`, 1016 s | 94 s | 362 s | R1 |
| `hook-tests-dual-rail (0)` | `Ceo`, 123 s | 110 s | 49 s (**failure**, parou no 1.º pytest) | R2 |
| `integration-tests` (E2E) | `Ceo`, 101 s | 160 s | 86 s | R2 |
| `hook-tests-python-matrix (3.12)` | `Ceo`, 438 s | 247 s | 319 s | R2 |
| `validate` (Governance…) | `Ceo`, 371 s | 456 s | 304 s | R1 |
| **run** | soma 2310 s, parede 1016 s | — | soma 1321 s, parede 759 s | 2 runners |

- Leitura: cada job é igual ou mais rápido na VM (a 3.9 cai de 1016 s para 362 s), mas com 2 runners os 9
  jobs passam em FILA — o último (`validate`) só começou 456 s (7,6 min) depois do push, atrás da 3.9 no
  mesmo runner.
  A parede de 759 s é menor que os 1016 s do hospedado só porque o caminho crítico de hoje (a 3.9 no
  `ubuntu-24.04` de 4 vCPU) encolheu mais do que a fila cresceu. O `dual-rail (0)` vermelho parou cedo;
  verde, o irmão levou 109 s.
- Simulação da fila (lista gulosa; ordem do YAML / LPT / piso `max(maior, soma/k)`), com as durações da
  VM acima (o `dual-rail (0)` estimado pelo irmão verde, 109 s; soma 1381 s, maior 362 s):

| runners | push na VM |
|---|---|
| 2 | 708 / 691 / 691 s |
| 3 | 556 / 481 / 460 s |
| 4 | 448 / 372 / 362 s |
| 6 | 387 / 362 / 362 s |
| 8 | 362 / 362 / 362 s |

  E com as durações do hospedado (hipótese pessimista de que a VM não acelera nada): push com 2 runners
  1387 / 1160 / 1155 s, com 4 runners 1133 / 1016 / 1016 s; schedule (11 jobs, soma 3214 s; 3 das 11
  durações são da tentativa 2 do run `38035614867`) com 2 runners 1769 / 1616 / 1607 s, com 4 runners
  1107 / 989 / 989 s.
- Fora da simulação: o grupo `vm-trusted-ci` atende 3 repositórios (este e 2 privados da organização, 5
  workflows), cuja carga não foi medida; o `push` e o `schedule` deste repositório têm grupos de
  concorrência distintos e podem rodar juntos; o `coverage` noturno (1258 s no `Ceo`, run `38034174442`)
  ocupa 1 runner. Um run não é amostra: a decisão de capacidade pede N runs (§8).
- 2.ª corrida, 4 runners (run `38102851467`, push `e2119681`, criado 01:44:43Z): fila de 2 a 8 s para os
  5 primeiros jobs, 82 a 177 s para os 4 seguintes (a 3.9 começou 177 s depois do push); parede 338 s, mas
  com 2 jobs vermelhos que pararam cedo (3.12 272 s, 3.9 163 s) — não serve como medida de tempo verde.

### 5.1 Risco do PR #3: os PRs (e o recuo) caem no `ubuntu-latest` de 4 vCPU

O PR #3 tirou o `Ceo` (8 núcleos) de todo `pull_request` e de todo `push`/`schedule` com a variável
desligada. O `timeout-minutes` não mudou: a matriz dá 45 min só à 3.9 e à 3.14 e 25 min às outras; o
comentário dos bytes ratificados (`validate.yml:1656`) estima «Runner padrao (4 vCPU) = 45 min» — e
declara que é estimativa («nenhuma perna rodou num runner padrao»). Medido agora, 1 run de cada (os do
próprio PR #3, `pull_request`, 01:03:41Z):

| job (timeout) | `ubuntu-latest` (run `38100541909`/`38100541954`) | fração do timeout | `Ceo` (run `38052044220`/`38034174442`) |
|---|---|---|---|
| matriz 3.10 (25 min) | 648 s | 43 % | 405 s (schedule `38035614867`) |
| matriz 3.11 (25 min) | 824 s | 55 % | 397 s (idem, tentativa 2) |
| matriz 3.12 (25 min) | 696 s | 46 % | 438 s |
| matriz 3.9 (45 min, `ubuntu-24.04`) | 854 s | 32 % | 1016 s (também `ubuntu-24.04`) |
| `validate` (25 min) | 350 s | 23 % | 371 s |
| `hook-tests-dual-rail` (20 min) | 145 s / 172 s | 12 % / 14 % | 123 s / 116 s |
| `integration-tests` (8 min) | 127 s | 26 % | 101 s |
| **`coverage` (35 min)** | **1925 s** | **92 %** | 1258 s (schedule) |

- A estimativa de ~45 min por perna NÃO se confirmou nesta amostra: a perna mais lenta da matriz no
  `ubuntu-latest` levou 824 s (13,7 min), 55 % dos 25 min.
- O risco real medido é o `coverage`: 1925 s (32,1 min) contra 35 min — 175 s de folga (8 %). Ele roda em
  `pull_request` quando o PR toca `.claude/hooks/**`, `.claude/scripts/**` ou o próprio `coverage.yml`, e
  no cron noturno quando a variável estiver desligada; o comentário do `coverage.yml` registra que o
  timeout anterior de 15 min já estourou («the captured run overran → cancel»). A folga medida é de 175 s,
  numa amostra.
- O `ubuntu-latest` vira Ubuntu 26.04 entre 2026-10-19 e 2026-11-19 (comentário do `validate.yml`, issue
  `actions/runner-images#14748`); as pernas 3.10–3.12 têm build para 26.04 (§3.1), mas os tempos acima são
  da imagem de hoje.
- O recuo da VM (variável desligada) passa a ser este runner: desligar a VM em incidente leva o `push` e o
  `schedule` para os tempos desta tabela, inclusive o `coverage` a 92 % do teto.


## 6. (e) Segurança de repositório público

- `pull_request` (inclusive de fork): `github.ref` = `refs/pull/N/merge` ⇒ runner hospedado (§2, e medido
  nos runs `38000376122` e `38100541909`). Um fork que edite o `runs-on` para o rótulo da VM no próprio PR roda um workflow com
  ref `refs/pull/N/merge`, que não está na lista do grupo (`restricted_to_workflows: true`, só
  `@refs/heads/main`) — a documentação do grupo diz que o job não é entregue ao runner; ensaio real NÃO
  feito. Aprovação de PR de fork: `first_time_contributors` (medido); um contribuidor recorrente roda sem
  aprovação, ainda nos runners hospedados.
- `workflow_dispatch` em branch ≠ `main`: runner hospedado pela expressão, e fora da lista do grupo.
- `pull_request_target`: nenhum nos 2 arquivos; no repositório inteiro só aparece em comentários que o
  proíbem. Atenção pela FORMA: um run de `pull_request_target`, `workflow_run` ou outro gatilho que
  executa o arquivo do `main` tem `job_workflow_ref` `…@refs/heads/main` — o grupo ACEITARIA esse run; a
  expressão o manda para o runner hospedado, mas um `runs-on` literal para a VM num job assim rodaria lá com
  dados vindos de fork.
- Fronteira de confiança = quem escreve no `main`. Medido (API, 2026-10-11): `main` sem proteção de branch
  e sem ruleset; 1 colaborador com escrita (admin) e 1 só-leitura; mais qualquer app ou token com
  `contents: write` (os próprios merges dos PRs #2 e #3 no §0 são o exemplo: o código do `main` passou a
  rodar na VM sem cerimônia).
- Cadeia de suprimento: todos os jobs fazem `pip install` do PyPI com versões ABERTAS (`pytest==8.*`,
  `PyYAML>=6.0`, `pytest-xdist`, `pyyaml`, `coverage==7.6.*`). No hospedado o raio de uma versão maliciosa
  é uma VM efêmera; na VM persistente é a máquina que atende 2 repositórios privados. As actions estão
  pinadas por SHA (`checkout`, `setup-python`, `upload-artifact`) e o binário do actionlint é conferido por
  sha256.
- Credenciais do runner: o passo roda como o usuário Unix do runner e lê o diretório do runner (registro
  e credenciais do agente). Num runner persistente, um passo malicioso pode se passar pelo runner e
  receber jobs dos outros repositórios do grupo, com os tokens e segredos deles. A defesa conhecida são
  runners efêmeros (`--ephemeral` ou JIT).
- O log de um job deste repositório é público: o «Set up job» publica o nome do runner e o nome da máquina
  (medido); qualquer sobra de outro repositório que um passo imprima (ex.: §4.2) também vira pública.

## 7. (f) Runner persistente × descartável

- Persistente, medido: arquivo de ambiente do runner com `PYTEST_XDIST_AUTO_NUM_WORKERS`/`GOMAXPROCS`
  (o valor mudou de 24 para 8 entre as 2 corridas); tool cache próprio por runner;
  workspace reaproveitado (`git checkout --force -B main`; o `actions/checkout` limpa por padrão);
  Python 3.11.17 já no tool cache.
- O que vaza entre jobs, pela forma:
  - `/tmp` (falha medida, §4.1; caminhos fixos, §4.2);
  - o `site-packages` do Python do TOOL CACHE: o `pip install` de um job instala no Python que o
    `setup-python` pôs no tool cache, e esse Python é reaproveitado pelo job seguinte do mesmo runner —
    inclusive de outro repositório (o tool cache é por runner, então 2 runners não dividem o
    `site-packages`; jobs sucessivos do mesmo runner, sim). Exemplo pela forma: o `coverage` instala `coverage`, `hypothesis`,
    `jsonschema`; o `dual-rail` seguinte acha esses pacotes (e um `pyyaml` de outro job) sem tê-los pedido.
    O ambiente do job passa a depender da HISTÓRIA do runner (não medido em skips ainda: os números do
    §3.2 bateram);
  - `$HOME`: `~/.claude/projects/<slug do caminho do workspace>` (cadeia de auditoria, chave HMAC, salt)
    persiste entre runs do mesmo runner; o slug difere por runner e por repositório, mas o usuário Unix
    pode ser o mesmo (não medido);
  - disco: workspaces, tool cache, logs e a cadeia em `$HOME` só crescem.
- Testes que leem o `$HOME` real (indicador `Path.home()`/`expanduser("~")`): 3 arquivos em
  `.claude/hooks/tests`, 3 em `.claude/scripts/tests`, 1 em `tests/integration`; o resto passa pelo
  `TestEnvContext` (HOME temporário).

## 8. Condições para manter a variável ligada (ou religá-la)

A variável está ligada desde 00:37:01Z (§0). A ratificação cobre os bytes de YAML; estas condições são
do lado do GitHub e da VM, ficam com o Owner, e nenhuma delas está medida como cumprida hoje, salvo onde
o item diz.

1. **`/tmp` por runner (a falha da 1.ª corrida):** `TMPDIR` próprio por runner, no `.env` de cada runner,
   OU runners descartáveis (um job por runner, máquina ou contêiner novo). Com `TMPDIR` por runner,
   somar limpeza desse diretório no hook de início de job do runner (sobra de job morto no mesmo runner)
   — e os caminhos `/tmp/...` escritos por extenso no `validate.yml` seguem fora (item 9).
2. **Python do tool cache no caminho de build (a falha da 2.ª corrida):** o interpretador que o
   `setup-python` põe é compilado com `-Wl,--rpath=<tool cache de build>/lib` pelo
   `actions/python-versions`; com tool cache próprio por runner, subprocesso de ambiente enxuto não acha a `libpython` (§4.6). Ou o tool cache de
   cada runner fica no caminho de build — o que, com vários runners na mesma máquina, faz os runners
   dividirem o `site-packages` (§7) —, ou cada runner é um contêiner/máquina com o seu próprio caminho de
   build. Os runners têm de ser homogêneos: a mesma perna passou num runner e caiu noutro.
3. **Isolamento do ambiente Python por job:** venv por job, ou tool cache só-leitura com os pacotes
   pinados — hoje o `pip install` de um job fica para o seguinte do mesmo runner (§7).
4. **Usuário e credenciais:** um usuário Unix por runner; a VM sem credenciais (nada de `gh` autenticado,
   chave SSH, `~/.claude` de sessão humana); o uso por SSH planejado para baterias pesadas num usuário à
   parte.
5. **Grupo dedicado ao repositório público:** não compartilhar o grupo (nem a máquina) com os 2
   repositórios privados, ou só com runners efêmeros.
6. **Capacidade:** com as durações da VM, 4 runners bastam para o push do `validate.yml` (simulação:
   362–448 s contra 759 s medidos com 2, §5); a única corrida com 4 runners (§5) teve 2 jobs vermelhos e não
   mede tempo verde; a carga dos outros repositórios e do nightly não entra na conta — decidir por N runs
   medidos; `PYTEST_XDIST_AUTO_NUM_WORKERS × runners ≤ vCPU` (8 × 4 = 32 na 2.ª corrida; ou afinidade de
   CPU por runner).
7. **Sistema e ferramentas:** Ubuntu 22.04/24.04 x64 com `lsb_release` (sem 3.9 no 26.04); tool cache
   gravável; `shellcheck`, `jq`, `rsync`, node/`npm`, `gpg`, `git`, `curl`, `sha256sum`, `shasum`
   pré-instalados (ou sudo sem senha para o `apt-get` do shellcheck); disco ≥ 200 GB com piso e limpeza.
8. **Recalibrar** o gate de latência (ADR-163) e o piso p50 no substrato da VM, sob a carga real de jobs
   vizinhos.
9. **Caminhos fixos em `/tmp`** do `validate.yml` (§4.2) trocados por `$RUNNER_TEMP` — mudança canônica,
   pacote próprio.
10. **Medição comparativa:** N runs na VM com o conjunto EXATO de falhas E de skips igual ao do runner
    hospedado no mesmo SHA — as 3 corridas medidas divergiram (1 falha na 1.ª, 104 na 2.ª, 4 na 3.ª, todas
    de ambiente).
11. **Recuo:** procedimento escrito (variável ≠ `"1"` + re-run) e alerta de runner fora do ar, porque o
    job fica na fila em vez de recuar (§2); o destino do recuo é o `ubuntu-latest` (§5.1).
12. **`coverage` no `ubuntu-latest`:** 1925 s contra o teto de 35 min (92 %, §5.1) em `pull_request` e no
    recuo — subir o `timeout-minutes` ou devolver o `coverage` a um runner maior é mudança canônica,
    pacote próprio; idem corrigir os comentários que ficaram falsos (`validate.yml:1646`, `:1656`, §1).
13. **Gatilhos:** nenhum `pull_request_target`/`workflow_run` nos 2 arquivos enquanto o grupo aceitar
    `@refs/heads/main` (§6).

## Apêndice A — dados brutos (sessão S363)

- Runs lidos: `38052044220` (push `bc803a7a`, hospedado), `38035614867` (schedule `142f01cd`, tentativa
  2), `38034174442` (Coverage schedule), `38000376122`/`38000375970` (PR #2, `pull_request`),
  `38099038933` (push `d7309efa`, VM; tentativa 2 do job vermelho pedida às 01:00:27Z), `38100541909` e
  `38100541954` (PR #3, `pull_request`, `ubuntu-latest`), `38102851467` (push `e2119681`, VM, 4 runners),
  `38103716736` (push `e0c5ffc2`, VM, 4 runners).
- Grupos de runner (API da organização): `vm-trusted-ci` `visibility: selected`,
  `allows_public_repositories: true`, `restricted_to_workflows: true`, 5 workflows (`validate.yml` e
  `coverage.yml` deste repositório em `@refs/heads/main`, mais 3 de 2 repositórios privados); 2 runners no
  run `38099038933` e 4 online às ~01:00Z, todos `Linux`, rótulos `self-hosted,Linux,X64,canhada-ci`. Permissões de Actions do repositório: `allowed_actions:
  all`, `sha_pinning_required: false`, token padrão `read`.
- actionlint 1.7.12 (local), shellcheck do Homebrew; PyYAML 6.0.3; pytest-xdist 3.8.0 (local).

## Apêndice B — fontes do avaliador (reproduzíveis)

Rodados a partir de um diretório de trabalho com `pre/.github/workflows/{validate,coverage}.yml` (blobs do
HEAD `bc803a7a`), `post/…` (os blobs de `d7309efa`) e `post2/…` (os de `e2119681` = `bc803a7a` + `git
apply vmci.patch`): `python3 ghexpr_truth.py post2`, `python3 fallback_eq.py . pre post2
Ceo=ubuntu-latest` (e sem o mapa, o controle), `python3 vm_cells.py . post2 ubuntu-latest` (e `. post
Ceo`). sha256: `ghexpr_truth.py` `609c8e155f93…`, `fallback_eq.py` `4a070c5ea15d…`, `vm_cells.py`
`a27fd516b602…`. Os outros dois
instrumentos, não reproduzidos aqui: `queue_sim.py` (`76a0adc4900f…`, a simulação do §5 com as durações do hospedado; a com as
durações da VM usa a mesma lista gulosa) e
`manifest_cov.py` (`bcc327c753f4…`, o §3.1).

### `ghexpr_truth.py`

```python
"""Avaliador mínimo do subconjunto de expressões do GitHub Actions usado nos
`runs-on` do PR #2, aplicado aos workflows PÓS-patch, mais a tabela-verdade.

Semântica implementada (docs.github.com, "Evaluate expressions in workflows
and actions" — operadores e coerção):
  * literais 'str' (com '' como escape), números, true/false/null;
  * acesso por ponto a contextos (vars.X ausente => '');
  * `==`/`!=`: tipos iguais => compara; strings comparadas SEM caixa
    (GitHub "ignores case when comparing strings"); tipos diferentes =>
    coerção numérica (null->0, bool->1/0, str->número ou NaN);
  * `!`, `&&`, `||` devolvem o operando (não um booleano), com falsy =
    false, 0, -0, '', null, NaN; array/objeto são truthy;
  * precedência: `!` > `==`/`!=` > `&&` > `||`; parênteses;
  * fromJSON(str).
Não implementa o resto da linguagem (funções além de fromJSON, índices,
comparações < >) — o parser recusa o que não conhece (falha FECHADA).

Uso: python3 -I ghexpr_truth.py <dir-pos-patch>
"""
from __future__ import annotations

import itertools
import json
import math
import re
import sys
from pathlib import Path

import yaml

TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<str>'(?:[^']|'')*')
  | (?P<num>-?\d+(?:\.\d+)?)
  | (?P<op>==|!=|&&|\|\||!|\(|\)|,)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_\-]*(?:\.[A-Za-z_][A-Za-z0-9_\-]*)*)
""", re.X)


class ParseError(Exception):
    pass


def tokenize(src):
    pos = 0
    out = []
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise ParseError("token desconhecido em %r" % src[pos:pos + 20])
        pos = m.end()
        kind = m.lastgroup
        if kind == "ws":
            continue
        out.append((kind, m.group(kind)))
    return out


class Parser:
    def __init__(self, toks):
        self.t = toks
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def eat(self, val=None):
        tok = self.peek()
        if val is not None and tok[1] != val:
            raise ParseError("esperava %r, veio %r" % (val, tok))
        self.i += 1
        return tok

    def parse(self):
        node = self.or_()
        if self.i != len(self.t):
            raise ParseError("sobra de tokens: %r" % (self.t[self.i:],))
        return node

    def or_(self):
        node = self.and_()
        while self.peek()[1] == "||":
            self.eat()
            node = ("||", node, self.and_())
        return node

    def and_(self):
        node = self.eq()
        while self.peek()[1] == "&&":
            self.eat()
            node = ("&&", node, self.eq())
        return node

    def eq(self):
        node = self.unary()
        while self.peek()[1] in ("==", "!="):
            op = self.eat()[1]
            node = (op, node, self.unary())
        return node

    def unary(self):
        if self.peek()[1] == "!":
            self.eat()
            return ("!", self.unary())
        return self.primary()

    def primary(self):
        kind, val = self.peek()
        if val == "(":
            self.eat()
            node = self.or_()
            self.eat(")")
            return node
        if kind == "str":
            self.eat()
            return ("lit", val[1:-1].replace("''", "'"))
        if kind == "num":
            self.eat()
            return ("lit", float(val))
        if kind == "ident":
            self.eat()
            if val in ("true", "false"):
                return ("lit", val == "true")
            if val == "null":
                return ("lit", None)
            if self.peek()[1] == "(":
                if val.lower() != "fromjson":
                    raise ParseError("função não suportada: %s" % val)
                self.eat("(")
                arg = self.or_()
                self.eat(")")
                return ("fromJSON", arg)
            return ("ctx", val)
        raise ParseError("primário inesperado: %r" % ((kind, val),))


def to_num(v):
    if v is None:
        return 0.0
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return 0.0
        try:
            return float(s)
        except ValueError:
            return math.nan
    return math.nan


def truthy(v):
    if v is None or v is False:
        return False
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return not (v == 0 or math.isnan(v))
    if isinstance(v, str):
        return v != ""
    return True


def eq(a, b):
    if type(a) is type(b) or (isinstance(a, (int, float)) and isinstance(b, (int, float))
                              and not isinstance(a, bool) and not isinstance(b, bool)):
        if isinstance(a, str):
            return a.lower() == b.lower()
        return a == b
    na, nb = to_num(a), to_num(b)
    if math.isnan(na) or math.isnan(nb):
        return False
    return na == nb


def ev(node, ctx):
    op = node[0]
    if op == "lit":
        return node[1]
    if op == "ctx":
        cur = ctx
        for part in node[1].split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return "" if node[1].startswith("vars.") else None
        return cur
    if op == "fromJSON":
        return json.loads(ev(node[1], ctx))
    if op == "!":
        return not truthy(ev(node[1], ctx))
    if op == "&&":
        left = ev(node[1], ctx)
        return left if not truthy(left) else ev(node[2], ctx)
    if op == "||":
        left = ev(node[1], ctx)
        return left if truthy(left) else ev(node[2], ctx)
    if op in ("==", "!="):
        r = eq(ev(node[1], ctx), ev(node[2], ctx))
        return r if op == "==" else not r
    raise ParseError("nó desconhecido %r" % (op,))


def pure_expr(s):
    if not (isinstance(s, str) and s.startswith("${{") and s.endswith("}}")):
        return None
    inner = s[3:-2]
    if "${{" in inner or "}}" in inner:
        return None
    return inner


# --- auto-teste da semântica (controles do avaliador) -----------------------
SELF = [
    ("'1' == '1'", {}, True),
    ("'TRUE' == 'true'", {}, True),          # caixa ignorada
    ("vars.X == '1'", {"vars": {}}, False),  # ausente => ''
    ("vars.X == ''", {"vars": {}}, True),
    ("'1' == 1", {}, True),                  # coerção numérica
    ("'01' == '1'", {}, False),              # mesmas strings: sem coerção
    ("'a' && 'b' || 'c'", {}, "b"),
    ("'' && 'b' || 'c'", {}, "c"),
    ("fromJSON('[1]') || 'x'", {}, [1]),
    ("!('a' == 'a')", {}, False),
]


def selftest():
    for src, ctx, want in SELF:
        got = ev(Parser(tokenize(src)).parse(), ctx)
        if got != want:
            raise SystemExit("AUTO-TESTE FALHOU: %s => %r (esperado %r)" % (src, got, want))
    print("auto-teste do avaliador: %d/%d" % (len(SELF), len(SELF)))


VM = ["self-hosted", "Linux", "X64", "canhada-ci"]


def main(root):
    selftest()
    root = Path(root)
    jobs = []
    for wf in ("validate.yml", "coverage.yml"):
        doc = yaml.safe_load((root / ".github" / "workflows" / wf).read_text(encoding="utf-8"))
        for jid, job in doc["jobs"].items():
            ro = job.get("runs-on")
            inner = pure_expr(ro)
            if inner is None:
                print("%s:%s runs-on NÃO é expressão pura: %r" % (wf, jid, ro))
                continue
            jobs.append((wf, jid, Parser(tokenize(inner)).parse()))
    print("jobs com runs-on por expressão: %d" % len(jobs))

    events = ["push", "schedule", "workflow_dispatch", "pull_request",
              "pull_request_target", "merge_group"]
    refs = ["refs/heads/main", "refs/heads/feature-x", "refs/pull/2/merge",
            "refs/heads/MAIN", "refs/tags/v1.4.3"]
    varvals = [None, "0", "1", "true", "TRUE", " 1", "1 ", "01", "1.0"]
    pyv = ["3.9", "3.10", "3.11", "3.12", "3.14"]

    rows = []
    for wf, jid, ast in jobs:
        uses_matrix = "matrix.python-version" in repr(ast)
        for event, ref, var in itertools.product(events, refs, varvals):
            for py in (pyv if uses_matrix else [None]):
                ctx = {"github": {"event_name": event, "ref": ref},
                       "vars": {} if var is None else {"VM_CI_ENABLED": var},
                       "matrix": {"python-version": py} if py else {}}
                out = ev(ast, ctx)
                rows.append((wf, jid, event, ref, var, py, out))

    # 1) onde cai na VM
    vm_rows = [r for r in rows if r[6] == VM]
    print("\n== combinações que caem na VM (de %d avaliadas) ==" % len(rows))
    seen = set()
    for wf, jid, event, ref, var, py, out in vm_rows:
        key = (event, ref, var)
        seen.add(key)
    for key in sorted(seen):
        print("  event=%-18s ref=%-18s VM_CI_ENABLED=%r" % key)
    # 2) por job: valor fora da VM é sempre o runner antigo?
    print("\n== por job: saídas possíveis ==")
    by_job = {}
    for wf, jid, event, ref, var, py, out in rows:
        by_job.setdefault((wf, jid, py), set()).add(json.dumps(out))
    for (wf, jid, py), outs in sorted(by_job.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "")):
        print("  %-13s %-42s py=%-5s -> %s" % (wf, jid, py or "-", " | ".join(sorted(outs))))
    # 3) a tabela pedida (job validate como representante; matriz à parte)
    print("\n== tabela-verdade (job `validate`; idem para os jobs sem matriz) ==")
    rep = [r for r in rows if r[1] == "validate"]
    for event in ["pull_request", "push", "schedule", "workflow_dispatch", "pull_request_target"]:
        for ref in ["refs/heads/main", "refs/heads/feature-x", "refs/pull/2/merge", "refs/heads/MAIN"]:
            cells = []
            for var in [None, "0", "1", "true"]:
                out = [r[6] for r in rep if r[2] == event and r[3] == ref and r[4] == var][0]
                cells.append("VM" if out == VM else out)
            print("  %-19s %-20s ausente=%-5s '0'=%-5s '1'=%-5s 'true'=%s" % ((event, ref) + tuple(cells)))


if __name__ == "__main__":
    main(sys.argv[1])
```

### `fallback_eq.py`

```python
"""Prova: fora da VM, o runs-on pós-merge é o runs-on de bc803a7a com, no máximo, os rótulos trocados
pelo mapa dado (ex.: Ceo=ubuntu-latest, o PR #3), em toda combinação; e o YAML não muda fora do runs-on.

Uso: python3 fallback_eq.py <dir do ghexpr_truth.py> <dir pré> <dir pós> [ROTULO=ROTULO ...]
"""
import itertools, json, sys
from pathlib import Path
import yaml
sys.path.insert(0, sys.argv[1])
import ghexpr_truth as g
pre_root, post_root = Path(sys.argv[2]), Path(sys.argv[3])
mapping = dict(a.split("=", 1) for a in sys.argv[4:])
events = ["push", "schedule", "workflow_dispatch", "pull_request", "pull_request_target", "merge_group"]
refs = ["refs/heads/main", "refs/heads/feature-x", "refs/pull/2/merge", "refs/heads/MAIN", "refs/tags/v1.4.3"]
varvals = [None, "0", "1", "true", "TRUE", " 1", "1 ", "01", "1.0"]
pyv = ["3.9", "3.10", "3.11", "3.12", "3.14"]
def val(ro, ctx):
    inner = g.pure_expr(ro)
    return ro if inner is None else g.ev(g.Parser(g.tokenize(inner)).parse(), ctx)
n = diff_non_vm = vm = remapped = 0
changed_jobs = []
for wf in ("validate.yml", "coverage.yml"):
    pre = yaml.safe_load((pre_root/".github/workflows"/wf).read_text())["jobs"]
    post = yaml.safe_load((post_root/".github/workflows"/wf).read_text())["jobs"]
    assert set(pre) == set(post), "conjunto de jobs mudou"
    for jid in pre:
        a, b = dict(pre[jid]), dict(post[jid])
        ra, rb = a.pop("runs-on"), b.pop("runs-on")
        assert a == b, "job %s mudou fora do runs-on" % jid
        if ra != rb:
            changed_jobs.append("%s:%s" % (wf, jid))
        for e, r, v, p in itertools.product(events, refs, varvals, pyv):
            ctx = {"github": {"event_name": e, "ref": r}, "vars": {} if v is None else {"VM_CI_ENABLED": v}, "matrix": {"python-version": p}}
            x, y = val(ra, ctx), val(rb, ctx)
            n += 1
            if y == g.VM:
                vm += 1
                continue
            want = mapping.get(x, x) if isinstance(x, str) else x
            if want != x and y == want:
                remapped += 1
            if y != want:
                diff_non_vm += 1
                print("DIFERENÇA fora da VM:", wf, jid, e, r, v, p, x, y)
    dpre = yaml.safe_load((pre_root/".github/workflows"/wf).read_text()); dpost = yaml.safe_load((post_root/".github/workflows"/wf).read_text())
    for k in set(dpre) | set(dpost):
        if k != "jobs":
            assert dpre.get(k) == dpost.get(k), "chave de topo %r mudou em %s" % (k, wf)
print("mapa de rótulos aplicado ao pré:", json.dumps(mapping, ensure_ascii=False))
print("jobs com runs-on alterado: %d -> %s" % (len(changed_jobs), ", ".join(changed_jobs)))
print("combinações avaliadas: %d; na VM: %d; fora da VM trocadas pelo mapa: %d; fora da VM com valor diferente do esperado: %d" % (n, vm, remapped, diff_non_vm))
print("fora do runs-on, YAML dos 2 arquivos idêntico (chaves de topo e de job): OK")
```

### `vm_cells.py`

```python
"""Conjunto EXATO de células (evento, ref, valor da variável, versão) que vão para a VM, por job,
e mutantes da expressão que devem mudar esse conjunto ou o fallback (controle vermelho).

Uso: python3 vm_cells.py <dir do ghexpr_truth.py> <dir pós> [fallback esperado do job validate num PR]
"""
import itertools, sys
from pathlib import Path
import yaml
sys.path.insert(0, sys.argv[1])
import ghexpr_truth as g
root = Path(sys.argv[2])
FB = sys.argv[3] if len(sys.argv) > 3 else "Ceo"
events = ["push", "schedule", "workflow_dispatch", "pull_request", "pull_request_target", "merge_group"]
refs = ["refs/heads/main", "refs/heads/feature-x", "refs/pull/2/merge", "refs/heads/MAIN", "refs/tags/v1.4.3"]
varvals = [None, "0", "1", "true", "TRUE", " 1", "1 ", "01", "1.0"]
pyv = ["3.9", "3.10", "3.11", "3.12", "3.14"]
EXPECTED = {(e, r, "1") for e in ("push", "schedule", "workflow_dispatch") for r in ("refs/heads/main", "refs/heads/MAIN")}
PR_CTX = {"github": {"event_name": "pull_request", "ref": "refs/pull/2/merge"}, "vars": {}, "matrix": {}}
def cells(expr, matrix_job):
    ast = g.Parser(g.tokenize(expr)).parse(); out = set()
    for e, r, v, p in itertools.product(events, refs, varvals, pyv if matrix_job else [None]):
        ctx = {"github": {"event_name": e, "ref": r}, "vars": {} if v is None else {"VM_CI_ENABLED": v}, "matrix": {"python-version": p} if p else {}}
        if g.ev(ast, ctx) == g.VM:
            out.add((e, r, v) if not matrix_job else (e, r, v, p))
    return out
ok = True
for wf in ("validate.yml", "coverage.yml"):
    for jid, job in yaml.safe_load((root/".github/workflows"/wf).read_text())["jobs"].items():
        expr = g.pure_expr(job["runs-on"]); mj = "matrix.python-version" in expr
        c = cells(expr, mj)
        exp = EXPECTED if not mj else {x + (p,) for x in EXPECTED for p in ("3.9", "3.10", "3.11", "3.12")}
        status = "OK" if c == exp else "DIVERGE"
        ok &= c == exp
        print("%-13s %-40s células na VM=%3d esperado=%3d %s" % (wf, jid, len(c), len(exp), status))
expr = g.pure_expr(yaml.safe_load((root/".github/workflows/validate.yml").read_text())["jobs"]["validate"]["runs-on"])
fb_real = g.ev(g.Parser(g.tokenize(expr)).parse(), PR_CTX)
print("\nfallback do job validate num pull_request: %r (esperado %r) -> %s" % (fb_real, FB, "OK" if fb_real == FB else "DIVERGE"))
ok &= fb_real == FB
MUT = [
    ("sem a cláusula do ref", expr.replace("&& github.ref == 'refs/heads/main'", "")),
    ("sem a cláusula do evento", expr.replace("&& (github.event_name == 'push' || github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')", "")),
    ("variável != '0' em vez de == '1'", expr.replace("vars.VM_CI_ENABLED == '1'", "vars.VM_CI_ENABLED != '0'")),
    ("+ pull_request na lista de eventos", expr.replace("github.event_name == 'push' ||", "github.event_name == 'push' || github.event_name == 'pull_request' ||")),
    ("fallback trocado (%r -> 'MUTANTE')" % FB, expr.replace("|| '%s'" % FB, "|| 'MUTANTE'")),
]
print("\nmutantes (job validate): o conjunto de células na VM, ou o fallback, tem de mudar")
for name, m in MUT:
    assert m != expr, "mutante não aplicou: " + name
    c = cells(m, False)
    fb = {g.ev(g.Parser(g.tokenize(m)).parse(), PR_CTX)}
    red = c != EXPECTED or fb != {FB}
    print("  %-42s células=%3d fallback(PR)=%s -> %s" % (name, len(c), sorted(fb, key=str), "VERMELHO (pego)" if red else "VERDE (escapou!)"))
print("\nRESULTADO:", "todos os jobs no conjunto esperado" if ok else "DIVERGÊNCIA")
```
