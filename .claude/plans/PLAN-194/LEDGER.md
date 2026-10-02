# PLAN-194 — LEDGER (diário de identificadores e medições)

Registro datado de comandos, identificadores e resultados das medições e dos lands do PLAN-194
(trem de manutenção até a v1.4.3). Uma entrada por fato; o que é medição diz o comando, a data e o
substrato. Este arquivo é LIVRE (oráculo de canonicidade = 0).

## T0 do trabalho longo — 2026-10-01 (S361)

- Owner aceitou em bloco as decisões Q1–Q14 (ver `PLAN-194-maintenance-train-v1-4-3.md`, seção
  «Decisões do Owner — S361»). Primeiro commit do trabalho longo: `6a9abb10` (emendas de texto).
- Substrato no T0: macOS 27.0.1; Claude Code 2.1.287 (auto-atualizado de 2.1.286 às
  2026-10-01T18:21:01Z, segundo `~/.claude/.last-update-result.json`); Codex CLI 0.156.1 pinado
  (`check_pair_rail.py --verify-codex-pin` = `verified`); Codex 0.160.0 publicado no npm em
  2026-10-01T20:26:19Z (não instalado; o Owner decidiu em 2026-10-01 atualizar pela W3, sem re-pin
  manual).
- Cadeia de auditoria no T0: `audit-log-2026-10.jsonl` com 1.ª quebra na linha 7726 (mesma da linha
  de base S360) e `audit-log.jsonl` vivo íntegro (372 elos) antes do primeiro spawn paralelo; as
  quebras posteriores em `agent_spawn` são a corrida no produtor descrita no risco 11.
- Backup da cadeia (W6.1, primeiro): `~/.ceo-backups/<slug>/ceo-backup-2026-10-01T195004Z.tar.gz`,
  30.111.116 bytes, sha256 `2217cafb1554e640183d087c182d20e4b8dd9399429d2fbce2ec06cd4f3ffe78`
  (15 arquivos `.jsonl` + `audit-log.errors` + `memory/`; sem `audit-key`, `.salt`,
  `audit-log.rotation-manifest.json`, `audit-log.last-hmac` e `audit-log.chain-length`).

## Unidade atual — S361 (2026-10-02; HEAD `f49bb6e7`)

- w-auditrace (W2.0, KERNEL): materiais landados em `26362b53`; aguardam o SIGN do Owner.
  verifier: `git merge-base --is-ancestor 26362b53 HEAD && test ! -e .claude/plans/PLAN-194/wave-auditrace-approved.md.asc` exit=0
- W1 (CI para o Ubuntu 26.04): materiais landados em `80e95fa7`; aguardam o SIGN do Owner.
  verifier: `git merge-base --is-ancestor 80e95fa7 HEAD && test ! -e .claude/plans/PLAN-194/wave-w1-approved.md.asc` exit=0
- W3b.1, metades livres: `803d7b5e` (assunto: W3b.3, linhas `o3-mini`/`o4-mini`) e `399efbaa`.
  verifier: `git merge-base --is-ancestor 803d7b5e HEAD && git merge-base --is-ancestor 399efbaa HEAD` exit=0
- W3b.1, metade canônica: em rail final (declarado pelo CEO em 2026-10-02; SEM verificador, estado
  não conferido neste registro).
- Debate L3 do PLAN-194: encerrado em `304ec478`; ajustes do consenso final em `f829b29a`.
  verifier: `git merge-base --is-ancestor 304ec478 HEAD && git merge-base --is-ancestor f829b29a HEAD` exit=0

## Bloqueios em aberto

- SIGN do Owner pendente: w-auditrace (`26362b53`) e W1 (`80e95fa7`).
- Arquivar T0/W0.1/W0.2 depois do SIGN da W1 (o sentinel cita o LEDGER); exige atualizar as citações
  em `debate/round-1/security-engineer.md:263` e `qa-architect.md:40`. Até lá o teto de 8.000 bytes
  segue estourado (aviso do hook PLAN-179 W2, não bloqueio).
- Decisão 3 do Owner (verificador de procedência: módulo interno do npm vs. `sigstore` fixado)
  condiciona o início da W3; pendente segundo o assunto de `f829b29a`; seção W0.6, abaixo.
- Backlog declarado: refresh completo do ledger da OpenAI; seção W3b.3, abaixo.

## W0.2 — manifesto do setup-python (controle vermelho da W1)

- 2026-10-01 (S361): no `versions-manifest.json` do ramo `main` de `actions/python-versions`, o
  Python 3.9 NÃO tem nenhum build linux para Ubuntu 26.04 (só até 24.04); 3.10 e 3.14 têm.

## W0.1 — Docker `ubuntu:26.04` (parcial)

- 2026-10-01T20:41Z–20:42Z (S361), colima 4 CPU / 6 GB nesta máquina:
  `docker pull ubuntu:26.04` ⇒ imagem `sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78`
  (criada em 2026-09-12T10:26:00Z); `/etc/os-release` = «Ubuntu 26.04.1 LTS (Resolute Raccoon)»;
  depois de `apt-get update`, `apt-cache policy python3` ⇒ candidato `3.14.3-0ubuntu2`, nada
  instalado; `apt-cache search --names-only '^python3\.[0-9]+$'` ⇒ só `python3.14`.
- Itens (a)–(d) da W0.1: MEDIDOS pelo builder da W1 (S361, 2026-10-01T23:35Z–2026-10-02T03:30Z);
  resultado abaixo. Conclusão: nenhuma quebra atribuível ao Ubuntu 26.04 nem ao Python 3.14; W1.4 e
  W1.5 sem pacote.

### Substrato

- 2026-10-01T23:35Z–2026-10-02T03:30Z (S361), colima `default` aarch64, 4 CPU / 6 GiB, docker 29.2.1
  (linux/arm64). Binários x86-64 rodam nessa VM (o `actionlint_1.7.7_linux_amd64` executou; não
  conferi se é Rosetta ou qemu — não mexi na configuração).
- Imagens (já presentes; nada baixado além das camadas que existiam): `ubuntu:26.04` =
  `sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78` («Ubuntu 26.04.1 LTS»);
  `ubuntu:24.04` = `sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517`
  («Ubuntu 24.04.4 LTS»), como linha de base.
- Preparo «parecido com o runner» (`setup-runner-like.sh`, um contêiner por imagem, removidos no
  fim): `apt-get update` + `python3 python3-pip python3-venv git jq shellcheck curl ca-certificates
  sudo xz-utils file` e usuário NÃO-root `runner` com sudo sem senha (o runner hospedado roda assim).
  NÃO instalei `python3-yaml`. Versões instaladas:
  - 26.04: `python3` **3.14.4** (o candidato que o CEO leu às 20:41Z era 3.14.3: o arquivo da distro
    atualizou nas ~3 h seguintes), pip 25.1.1, git 2.53.0, jq 1.8.1, shellcheck 0.11.0,
    bash 5.3.9(1); **PyYAML do sistema: AUSENTE**; `/usr/lib/python3.14/EXTERNALLY-MANAGED` presente
    (`python3 -m pip install PyYAML` no sistema ⇒ rc 1, PEP 668).
  - 24.04: `python3` 3.12.3, pip 24.0, git 2.43.0, jq 1.7, shellcheck 0.9.0, bash 5.2.21(1);
    PyYAML do sistema AUSENTE na imagem docker — **mas presente na imagem do runner 24.04**, porque o
    step `Validate settings.json and YAML catalogs` do `validate.yml` passa hoje no `Ceo`: o docker não
    reproduz esse detalhe da imagem do runner.
- Imagem do RUNNER (leitura dos READMEs de `actions/runner-images`, 2026-10-02, por WebFetch):
  Ubuntu 26.04 `20260920.143.1` — Python padrão 3.14.4; toolcache 3.10.21, 3.11.16, 3.12.14, 3.13.15,
  3.14.7; shellcheck 0.11.0-2; jq 1.8.1; git 2.55.0; bash 5.3.9. Ubuntu 24.04 `20260920.314.1` —
  Python padrão 3.12.3; toolcache 3.10–3.14 (sem 3.9); shellcheck 0.9.0; jq 1.7. Nenhum dos dois
  README lista PyYAML/`python3-yaml`. O issue actions/runner-images#14748 dá o 26.04 como GA desde
  2026-09-17 e a migração do `ubuntu-latest` de 2026-10-19 a 2026-11-19; mitigação oficial: rótulo
  `ubuntu-24.04`, e `ubuntu-26.04` para testar explicitamente.

### (a) Template do adopter ativado e EXECUTADO

- Comando (no contêiner, como `runner`, na árvore `6a9abb10`):
  `CEO_SMOKE_EXECUTE_CI=1 bash scripts/tests/smoke-install.sh /home/runner/smoke-target`
  (instala, ativa `validate.yml.template`, commita a árvore e roda os `run:` com
  `scripts/tests/run-activated-workflow.py`).
- 26.04, 2026-10-02T00:05:19Z: **10/10 steps `run:` verdes**, 1 `uses:` pulado por nome,
  «smoke install OK», rc 0. 24.04 (mesma hora): 10/10 verdes, rc 0.
- Ressalva do step 7 (catálogos YAML): passou no 26.04 pelo FALLBACK do próprio template — o
  `pip install` no `python3` do sistema é recusado (PEP 668) e o `sudo apt-get install -y -qq
  python3-yaml` funcionou porque o contêiner tinha listas do apt (o preparo rodou `apt-get update`).
  No runner real o step depende de a imagem trazer PyYAML OU de esse `apt-get install` sem `update`
  funcionar; se nenhum dos dois, o step falha FECHADO (mensagem própria), nunca verde-vácuo. Não
  medível sem um run do GitHub.
- Ressalva do step 10 (actionlint): o asset `linux_amd64` rodou na VM arm64 (emulação da VM).
- Conclusão para a W1.4: **sem mudança** no template (verde no 26.04, com a ressalva acima).

### (b) Steps do job `validate` que usam o `python3` do sistema (antes do `setup-python`)

- Extraídos VERBATIM do `validate.yml` (`6a9abb10`): os 20 `run:` antes do `actions/setup-python`;
  cada um rodado como o runner (`bash --noprofile --norc -eo pipefail`, cwd = clone, `CI=true`), SEM
  parar no primeiro vermelho.
- 26.04 (`python3` 3.14.4) e 24.04 (3.12.3): **mesmo resultado nas duas imagens** — 18 rc 0;
  step 15 «Validate settings.json and YAML catalogs» rc 1 (`ModuleNotFoundError: No module named
  'yaml'`, nos dois — o docker não tem PyYAML no sistema); step 20 `check-installer-write-safety.py
  --strict` rc 1 (advisory, `continue-on-error`, rc 1 por desenho). `validate-governance.sh`
  «Errors: 0» nos dois; shellcheck 0.11.0 limpo nos 26 scripts; `SyntaxWarning` de escape inválido
  em `_lib/team.py:5`, `architect-bundle-validate.py:23` e um script de plano — os mesmos três no
  3.12 (só o texto da mensagem muda no 3.14).
- Conclusão para a W1.2: o único step do job que depende de algo que o 26.04 pode não ter é o dos
  `import yaml` — confirmado (o resto passa no `python3` 3.14 do sistema).

### (c) Suíte do job `hook-tests-python-matrix` no `python3` da imagem

- Comandos do job (iguais, com `PYTHONPATH=.`), num venv criado do `python3` do sistema com
  `pytest 8.4.2`, `PyYAML 6.0.3`, `pytest-xdist`:
  `python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/
  -n auto -m 'not serial' --strict-markers --tb=no -q` e a passada `-m 'serial'`.
- 26.04 / **3.14.4**, 2026-10-01T23:42:24Z–23:51:44Z: paralela **13.398 passed, 89 skipped,
  4 xfailed** (rc 0, 269 s); serial **1 failed, 936 passed**, 11 skipped (rc 1, 291 s).
- 24.04 / 3.12.3 (linha de base), 2026-10-01T23:52:03Z–2026-10-02T00:04:13Z: paralela 13.398 passed,
  89 skipped (rc 0, 450 s); serial **3 failed**, 934 passed (rc 1, 280 s).
- As falhas são todas da classe «orçamento de tempo absoluto» (CLAUDE.md, S357):
  - 3.14: `test_check_pair_rail_matrix.py::TestDecideWithMatrixPerformance::test_case_a_p99_under_5ms`
    (p99 15,8 ms > 5 ms; falha também isolado 3/3);
  - 3.12: o MESMO teste (p99 59,7 ms) + `test_lifecycle_edge_cases.py::TestOutputScanPerfRigorous::
    test_p99_10kb` + `perf/test_optimizer_complexity_gate_p99.py::...::test_classify_latency_under_ceiling_per_probe`;
  - o mesmo `test_case_a_p99_under_5ms` falha também no Mac (python 3.9.6) na árvore `6a9abb10`.
  Conjunto de falhas do 3.14 ⊂ conjunto da linha de base ⇒ **nenhuma quebra atribuível ao 3.14 /
  26.04**. Os 89 skipped (contra 62–64 no CI) são ferramentas ausentes no contêiner.
- Referência no CI real (`Ceo`, 2026-10-01): perna 3.9 paralela 430–646 s + serial 211–232 s (runs
  36932014761, 36832647294); perna 3.12 paralela 260–529 s + serial 130–208 s.

### (d) Censo: jobs em `ubuntu-latest` e `Ceo`, e o que usam do sistema

- Censo por YAML (PyYAML no Mac) dos 23 workflows de `.github/workflows/`: **21 workflows com
  `ubuntu-latest` (28 jobs)** e **6 jobs `Ceo`** (`coverage.yml:coverage` e, no `validate.yml`,
  `validate`, `integration-tests`, `formal-verification-mutation-harness`, `hook-tests-dual-rail`,
  `hook-tests-python-matrix`); `tier-policy.yml` em `ubuntu-22.04`. Tabela completa em `census.md`
  fora do repositório (checkpoint da sessão S361).
- Python dos jobs com `setup-python`: só 3.11 e 3.12 (fora a matriz) — todos têm build para 26.04. A
  única versão sem build para 26.04 (3.9) só aparece na matriz do `validate.yml` (`Ceo`).
- Jobs em `ubuntu-latest` que usam o `python3`, o `shellcheck` ou o `jq` do SISTEMA (sem
  `setup-python`, direto ou por script `.sh`) — e o que rodou no 26.04:
  - `ceremony-lint.yml:ceremony-lint` (`check-ceremony-script.py` + `--list`): **verde** no 26.04 e
    no 24.04 (0 blocking; mesmos números advisory).
  - `ceremony-lint.yml:shellcheck-ceremony` (shellcheck do sistema, advisory): roda no 26.04 com o
    0.11.0 (157 arquivos; mesma contagem de linhas de saída que o 0.9.0 do 24.04).
  - `translations-drift.yml:drift-check` (bash): **verde** nos dois.
  - `ownership-nightly.yml:ownership-e2e` (o `python3` do sistema pelo `install.sh`/`upgrade.sh`;
    `jq`; `shasum` — presente, do pacote `perl`): ver o resultado abaixo.
  - `npm-publish.yml:await-release-gate` (`shasum`, `gh`, `jq`) e `npm-publish.yml:publish` (o
    `python3` do sistema num trecho só com `json`/`re`/`sys`, Node do `setup-node`): **não
    executados** (precisam de tag/API do GitHub; o `publish` é território da W4).
  - `mutation-gate.yml:aggregate`, `tournament.yml:notify-on-regression`: só bash/echo.
  - `formal-verify.yml:tlc-model-check`: Java do `setup-java` + `curl`; sem Python (W8).
  - `actionlint.yml:actionlint`: o binário do actionlint é vendorado (sha256 fixado), mas o job roda
    `actionlint -color .github/workflows/*.yml` SEM `-shellcheck` e usa o shellcheck da IMAGEM (0.11.0
    no 26.04). Medido (S361, 2026-10-02): actionlint 1.7.12 com shellcheck 0.11.0 sobre os 23
    workflows ⇒ rc 0; reconferido ao registrar, no macOS:
    verifier: `actionlint .github/workflows/*.yml` exit=0
    `validate.yml:opus-4-7-profiler-smoke` e
    `validate.yml:hook-stdout-schema-oracle`: `setup-python` 3.11 (tem build 26.04).
- `ownership-nightly.yml`, os 9 `run:` VERBATIM no 26.04 (`run-steps.sh`, árvore `6a9abb10`,
  2026-10-02T00:14Z–01:29:52Z), com o 24.04 em paralelo até o step 06 (parado depois para liberar a VM):
  - steps 01–08 **verdes no 26.04 (01–06 também no 24.04)** (gate-scripts `shasum -c`, tag `legacy_pristine`, `jq`,
    oráculo unitário, replay do install-state 1041 s, baseline-manifest 1024 s, INV-4 396 s,
    controle positivo do gate);
  - step 09 (e2e completo, 2085 s): `GREEN=54 RED=11`, gate vermelho por **8 células TIMEOUT**
    (`OWN-0021`, `0022`, `0023`, `0030`, `0031`, `0070`, `0073`, `0080`; `CELL_TIMEOUT` padrão 60 s)
    + os 3 vermelhos por desenho (`OWN-0016`, `0024`, `0027` = `ownership-expected-reds.txt`);
  - as 8 células rerrodadas UMA A UMA no mesmo contêiner 26.04, sem disputa de CPU
    (`CELL_TIMEOUT=300 test-ownership-table.sh --only <id>`, terminado em 2026-10-02T03:29:05Z): **as 8 GREEN**, em
    33–52 s cada ⇒ os TIMEOUT eram a VM disputada (2 contêineres + o ensaio no Mac), não o 26.04.
    Conjunto vermelho efetivo no 26.04 = o esperado por desenho.
  - Ressalva: no runner real a margem dessas células contra os 60 s não foi medida (aqui, isoladas,
    ficaram em 55–87 % do timeout).
- Conclusão para a W1.5: **nenhum workflow marcado como quebrando** no 26.04 pelo que é medível fora
  do GitHub ⇒ a W1.5 não abre pacote (sem `ubuntu-24.04` em outros workflows). Não medidos: os dois
  jobs do `npm-publish.yml` (tag + API) e o TLC do `formal-verify.yml` (Java; W8).

### Ferramenta e limpeza

- Scripts do builder (fora do repositório): `census.py`, `extract-steps.py`, `run-steps.sh`,
  `run-matrix-suite.sh`, `setup-runner-like.sh`, `lint-copies.sh` — cópias fora do repositório (checkpoint da sessão S361).
- Contêineres `b1w1-u2604` e `b1w1-u2404` removidos no fim; nenhuma imagem nova; nenhuma configuração
  do docker/colima alterada.


## W3b.3 — verificação em fonte primária (ids da OpenAI)

- 2026-10-02 ~00:30Z (S361), fonte: página oficial de deprecações da OpenAI
  (`https://platform.openai.com/docs/deprecations`, que redireciona com 301 para
  `https://developers.openai.com/api/docs/deprecations`), lida por WebFetch (extração por modelo
  auxiliar; as linhas abaixo foram pedidas verbatim):
  - seção «2026-06-11: GPT-5 and o3 model deprecations»: desligamento em **Dec 11, 2026** de
    `gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`, `gpt-5-nano-2025-08-07`, `gpt-5-pro-2025-10-06`,
    `o3-2025-04-16` e `o3-pro-2025-06-10` (substitutos `gpt-5.6-sol`/`-terra`/`-luna`);
  - seção «2026-04-22: Legacy GPT model snapshots (July 2026 shutdown)»: desligamento em
    **July 23, 2026** (já passado) de `gpt-5-codex`, `gpt-5-chat-latest`, `gpt-5.1-codex`,
    `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`, `gpt-5.2-codex`, `gpt-5.1-chat-latest` e
    `o3-deep-research-2025-06-26`;
  - **`gpt-5.5` NÃO aparece na página** ⇒ a aposentadoria em 2026-10-14 NÃO se confirma; pelo texto
    da W3b.3 o item fecha sem a linha no `model-deprecations.json` (Check: none, resultado aqui).
  - `o3-mini`: uma primeira extração resumida citou «October 23, 2026», mas a extração verbatim não
    trouxe linha de `o3-mini` ⇒ NÃO confirmado; re-conferir à mão antes da W3b.1.
- Consequência para a W3b (achado do builder da W3b.0 + esta leitura): com a cura do detector, uma
  variante só casa se o ledger a listar; `gpt-5-codex` (desligado em 2026-07-23) e os demais ids da
  seção de julho precisam entrar no `model-deprecations.json` para não ficarem escondidos (hoje o
  `gpt-5-codex` aparece em `codex_invoke.py` e `codex_phase_gate.py`). Entra no refresh do ledger
  junto da W3b.3 (mesmo arquivo; a regra INERT do `check-model-currency.py:64`, opção A do builder,
  vai no mesmo land).
- 2026-10-02T00:55Z (S361), re-conferência pedida acima («re-conferir à mão antes da W3b.1»), feita
  pelo builder da W3b.1 sobre o HTML CRU da mesma página (`curl -sSL
  https://developers.openai.com/api/docs/deprecations`, 482.750 bytes, sha256
  `d7f797e77e57c9b05c6b2e569499a60ece6a6917c934cdb779c4149a631d552d`; texto extraído por script,
  sem modelo auxiliar). A página tem DUAS seções com data 2026-04-22: a de julho (lida acima) e
  «2026-04-22: Legacy GPT model snapshots», SEM o parêntese, cujas linhas têm desligamento em
  **October 23, 2026** — 12 snapshots na tabela principal e 5 modelos com ajuste fino. Entre elas:
  - `o3-mini-2025-01-31 | o3-mini`, substituto `gpt-5.6-sol` ⇒ `o3-mini` CONFIRMADO (supera a linha
    «NÃO confirmado» acima; a primeira extração resumida acertou a data);
  - `o4-mini-2025-04-16 | o4-mini`, substituto `gpt-5.6-terra` ⇒ `o4-mini` também se aposenta (não
    estava na leitura de 2026-10-02 ~00:30Z).
  - `gpt-5.5` segue AUSENTE da página (0 ocorrências no HTML cru).
- Consequência (land livre, antes do SIGN da W3b.1): `o3-mini` e `o4-mini` ganham linha no
  `model-deprecations.json` (substituto `gpt-5.6-sol` pela política de alvo único do `_meta`; a
  página dá `gpt-5.6-terra` para o `o4-mini`, registrado na nota da linha), e o mapa de dívida
  `W3B1_DECLARED_DEBT` cresce de 12 para 14 acertos (os dois em `codex_cli_shape.py`). As outras 15
  linhas da seção de outubro (`gpt-3.5-turbo*`, `gpt-4*`, `o1*`, `gpt-image-1`, ajuste fino) e as 6
  linhas da seção de julho que o ledger não tem (`computer-use-preview*`, as duas `*-search-preview`,
  `gpt-audio-mini-*`, `gpt-realtime-mini-*`, `o4-mini-deep-research*`) NÃO entram: medido com um
  ledger de sonda contendo todas elas, nenhuma tem referência viva (não-INERT) nesta árvore
  (`check-model-deprecations.py --ledger <sonda> --json --today 2026-10-13` = só os 14 acertos acima).
  Ficam como backlog declarado (refresh completo do ledger da OpenAI, com substitutos por faixa
  depois que a W3b.1 põe a família `gpt-5.6-*` em `_VALID_MODELS`). A linha `o3-deep-research-2025-06-26`
  do ledger diz que nenhum alias sem data foi inferido, mas a página lista `o3-deep-research` como
  alias — mesmo backlog.

## W0.6 — verificador de procedência do Codex (S361, 2026-10-02)

- Medição completa (comandos, versões, células, saídas): fora do repositório, no checkpoint
  `s361-packs/b11-w06/W0.6-medicao.md` da sessão S361 (npm 11.16.0; `sigstore` 4.1.1 interno do npm;
  versões 0.160.0 e 0.156.1 do Codex; registro oficial e CDN do TUF do Sigstore).
- `npm audit signatures` NÃO serve para a W3: verifica só o que o REGISTRO declara (assinatura do
  registro e bundle do atestado), não os bytes locais, não fixa identidade, não exige o atestado e fica
  verde sem rede com cache quente. Células medidas: payload adulterado instalado ⇒ exit 0 «verified»;
  atestado removido ⇒ exit 0; atestado de outro repositório ⇒ verde.
- O `sigstore` interno do npm chamado com política de identidade (`certificateIdentityURI` +
  `certificateIssuer`) + vínculo em stdlib (sha512 do tarball = `subject` do atestado; sha256 do
  `bin/codex` lido em fluxo) dá verde no íntegro e vermelho em toda adulteração e identidade divergente.
  Decisão de desenho pendente do Owner: módulo interno do npm vs. `sigstore` fixado no staging.
- Identidade literal do construtor (0.160.0 e 0.156.1): repositório `https://github.com/openai/codex`,
  workflow `.github/workflows/rust-release.yml`, ref `refs/tags/rust-v<X.Y.Z>`, emissor OIDC
  `https://token.actions.githubusercontent.com`, `predicateType` `https://slsa.dev/provenance/v1`,
  purl de plataforma `pkg:npm/%40openai/codex@<X.Y.Z>-darwin-arm64`.
- Tamanhos 0.160.0: tarball de plataforma 134.311.083 bytes (332.972.398 descomprimido; `bin/codex`
  241.555.024). O pacote de plataforma traz outros executáveis fora do sha256 pinado (`rg`, `zsh`,
  `codex-voice-host`, dylibs) — entra no «escopo honesto» do ADR-182-AMEND-1.
- Controle: o sha256 do `bin/codex` da 0.156.1 lido do tarball = o do manifesto assinado (`0196e89f…`).
