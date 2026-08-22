# Crítica — DevOps / Platform Engineer

> Rodada 2 do debate do PLAN-184. Rótulo anonimizado na síntese: **Critic-A**
> (mapa em `anonymization-map.md`). Eixo desta crítica: engenharia de pipeline: mecanismo do filtro, required checks, semantica de gatilho, runner, reexecucao.
> Agente read-only (ADR-136-AMEND-1): não editou arquivo nenhum;
> toda claim foi verificada contra o disco antes de entrar aqui.

## Verdict

**ADJUST_PROCEED**

## Summary (≤ 3 bullets)

- A arquitetura central esta certa e sobrevive a minha critica: manter o job `Governance, health, contamination, shellcheck` FORA do filtro preserva, verificado passo a passo, TODOS os validadores de markdown normativo (validate-governance.sh, check-claude-md-claims, verify-counts, contamination, check-spec-drift, check-audit-registry-coverage). Um contribuidor externo NAO consegue escolher paths para escapar do gate de governanca.
- O que quebra e a DERIVACAO da denylist, nao a doutrina. O exemplar do proprio plano — `.claude/plans/**`, usado no AC-2 como o commit que DEVE pular — nao e inerte: `tests/integration/test_install_smoke.py:61-73` afirma a EXISTENCIA de `.claude/plans/PLAN-SCHEMA.md`, `AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md` e `.claude/adr/README.md`, e essa suite roda SO no job pesado `integration-tests` (validate.yml:1071,1095). A §4 parou em `docs/**` e nunca olhou a familia que paga a conta.
- Duas omissoes de FORMA fazem o fail-closed prometido virar fail-open: nenhum Check exige que a entrada da denylist seja ancorada em `*.md` (e `.claude/plans/` tem 272 .py, 102 .sh, 31 .yml, 27 .pyc no disco HOJE), e nada — nem actionlint, nem check-action-sha-drift.py — le `paths-ignore` depois de escrito, num repo cujo proprio F11 e a prova de que deteccao de path apodrece calada.

## Must-fix (blocking) — P0

### SEC-P0-1 — `.claude/plans/**` — o exemplar da denylist — NAO e inerte: contem tres schemas normativos cuja entrega e afirmada so por um job pesado

**Como falha.** Um commit que renomeia ou apaga `.claude/plans/PLAN-SCHEMA.md` (ou `AUDIT-LOG-SCHEMA.md`, ou `DEBATE-SCHEMA.md`) toca SOMENTE `.claude/plans/**`. Com esse prefixo na denylist, os 4 jobs pesados nao rodam, e `tests/integration/test_install_smoke.py:61-73` — que lista esses tres caminhos em `expected_paths` e faz `assert not missing` — nunca executa. Consequencia: `scripts/install.sh` para de entregar o schema normativo de planos/debates ao adopter e NADA fica vermelho. O gate nao e redundante: `scripts/tests/smoke-install.sh` nao contem nenhuma referencia a PLAN-SCHEMA/DEBATE-SCHEMA/plans (grep = 0 linhas), entao o `smoke-install.yml` disparar por causa das entradas :47-48/:113-114 nao substitui a asserção. Pior, o proprio AC-2 (plan:1022-1024) manda PROVAR o filtro usando exatamente `.claude/plans/**` como o commit que deve pular — o plano canoniza como caso de sucesso a familia que tem acoplamento de existencia.

**Evidência.** tests/integration/test_install_smoke.py:66-70 (expected_paths: skills/core, plans/PLAN-SCHEMA.md, plans/AUDIT-LOG-SCHEMA.md, plans/DEBATE-SCHEMA.md, adr/README.md) + :73-74 (assert not missing); .github/workflows/validate.yml:1071,1078,1095 (job integration-tests, runs-on Ceo, roda tests/integration/); `grep -n 'PLAN-SCHEMA|DEBATE-SCHEMA|plans/' scripts/tests/smoke-install.sh` -> vazio; PLAN-184:1022-1024 (AC-2), :265-295 (§4 so examina docs/**)

**Cura proposta.** Nomear este contraexemplo na §4 ao lado do `docs/threat-model.md` — mesmo mecanismo (EXISTENCIA), familia diferente. Na W0-US2(b), o alvo de rename/delete para `.claude/plans/**` tem de ser um dos tres *SCHEMA*.md, e o `Check:` exige o VERMELHO. Como remover `.claude/plans/**` inteiro mataria a economia, a entrada tem de ser recortada, nao descartada: `.claude/plans/PLAN-*.md` + `.claude/plans/PLAN-*/**/*.md`, com `.claude/plans/*SCHEMA*.md` explicitamente FORA da denylist e essa exclusao citada em comentario no YAML.

### SEC-P0-2 — A FORMA da entrada da denylist nao tem restricao — o fail-closed vale acima dos prefixos, nunca dentro deles

**Como falha.** O plano especifica de onde a lista vem (W0-US1, por prefixo) e como provar cada entrada (W0-US2), mas nenhum `Check:` restringe a SINTAXE da entrada. Duas malformacoes opostas passam por todos os ACs. (a) Prefixo cru: `.claude/plans/**` pre-aprova, de uma vez e para sempre, os 272 `.py`, 102 `.sh`, 31 `.yml` e 27 `.pyc` que ja existem sob esse prefixo hoje, mais tudo que for adicionado amanha — incluindo `.claude/plans/PLAN-179/staged-w24/` e `OWNER-W179-LAND.sh`, codigo que o repo explicitamente encena para depois copiar para `.claude/hooks/_lib/`. A doutrina da §3 ('um diretorio novo nao esta na lista, logo roda') e verdadeira ACIMA dos prefixos e FALSA dentro de cada um: la o default para o desconhecido e PULAR. (b) Entrada por extensao: a derivacao da US1 sobre 64,8% de commits so-docs produz naturalmente algo como `**/*.md`, que engole `docs/threat-model.md` e `.github/workflows/GOVERNANCE-MAP.md` — violando o AC-4 — enquanto passa no Check da W1 como literalmente escrito ('nenhuma entrada casa .github/workflows/**' e uma afirmacao sobre intersecao de globs que ninguem sabe checar a olho).

**Evidência.** `find .claude/plans -type f ! -name '*.md'` -> 272 py / 241 txt / 125 patch / 102 sh / 76 json / 31 yml / 27 pyc (2008 arquivos no total); `ls -R .claude/plans/PLAN-179` -> staged-w24/, staged-w01/, assemble_pack.py, OWNER-W179-LAND.sh; PLAN-184:229-233 (doutrina denylist), :739 (Check US1), :850 (Check W1), :1034-1042 (AC-4)

**Cura proposta.** Congelar a gramatica da entrada num item [P0] da W0-US1: toda entrada e `<prefixo-aprovado>/**/*.md`; entrada sem ancora de prefixo (`*.md`, `**/*.md`) e entrada sem ancora de extensao (prefixo cru) sao ambas REJEITADAS por construcao. Assim, um `.py`/`.sh`/`.yml` novo sob qualquer prefixo da denylist nao casa, e o run acontece — que e a propriedade que a §3 diz querer.

## Riscos — P1

### SEC-P1-3 — O filtro vira artefato normativo sem guard mecanico — e pode desligar a si mesmo em um commit de uma linha

**Como falha.** O `Check:` da W1 ('o arquivo novo dispara sobre si mesmo', plan:850) e uma propriedade do conteudo do arquivo NO MOMENTO em que ele e escrito, nao um invariante. Depois disso: um PR de uma linha que acrescente `'**'` (ou qualquer padrao que case `.github/workflows/<novo>.yml`) ao `paths-ignore` do proprio arquivo faz com que TODOS os paths alterados por esse PR estejam ignorados — o workflow pesado nao roda sobre o proprio enfraquecimento, e nada mais o valida: `actionlint` aprova um `paths-ignore` sintaticamente valido, `check-action-sha-drift.py` nao parseia `on:`/`paths` (grep vazio), e `paths-ignore` nao aparece em nenhum script/hook/workflow do repo — so no texto deste plano. O repo ja tem o precedente exato dessa podridao dentro do arquivo-alvo: o F11 (`validate.yml:736-739`) e logica de deteccao de path morta na perna `pull_request` com um comentario citando um job que nao existe mais.

**Evidência.** `grep -rn 'paths-ignore' .github .claude scripts templates docs` -> unicas ocorrencias sao PLAN-184 (:225,246,257,490,598,682,839,850,1186,1271); `grep -n '"on"|paths' .claude/scripts/check-action-sha-drift.py` -> vazio; PLAN-184:520-553 (F11), :850 (Check W1)

**Cura proposta.** Adicionar um item [P0] a W1: um teste em `.claude/scripts/tests/` (que roda no job de governanca PRESERVADO, portanto em todo commit) que parseia o bloco `on:` do workflow novo e afirma, mecanicamente: (i) toda entrada de `paths-ignore` esta na lista aprovada da W0-US2 e obedece a gramatica do SEC-P0-2; (ii) nenhuma entrada casa `.github/**` — testado por glob-match real contra o proprio caminho do arquivo, nao por leitura; (iii) `docs/**` e `.claude/plans/*SCHEMA*.md` ausentes; (iv) paridade de gatilho com `validate.yml:3-6`. Sem isso, todo AC do plano e um snapshot de um dia.

### SEC-P1-4 — O split nasce sem o guard de fork-PR que 6 workflows irmaos carregam — e o plano manda ACENDER, pela primeira vez, o gatilho `pull_request` sobre runner self-hosted

**Como falha.** O `Check:` da W1 (plan:850) exige paridade de gatilho provada por diff dos blocos `on:` — o que reproduz fielmente `pull_request:` SEM filtro de branch no arquivo novo, com `hook-tests-dual-rail` e `hook-tests-python-matrix` permanecendo em `runs-on: Ceo` (self-hosted; a A2 so tira os dois seriais). Seis workflows deste repo condicionam jobs alcancaveis por fork com `github.event.pull_request.head.repo.full_name == github.repository`; `validate.yml` nao tem nenhum, e o F2 mede zero runs de `pull_request` na janela — ou seja, a exposicao existe mas esta DORMENTE. O plano acorda: o AC-9 (plan:1058) exige um PR de teste que faca os 4 pesados executarem, e a OQ-8(b) oferece um PR como rota de medicao. Resultado concreto: a partir daqui um PR de fork tocando `.claude/hooks/**` executa codigo do contribuidor no runner self-hosted da org, e o arquivo novo nasce sem a decisao explicita que os irmaos tomaram — e nada verifica isso (mesma cegueira que o proprio plano documenta para `permissions:`, F7).

**Evidência.** `grep -rn 'head.repo' .github/workflows/*.yml` -> adapter-live.yml:44, benchmarks.yml:51, mcp-smoke.yml:99, red-team.yml:61, shadow-ci.yml:50, tournament.yml:68 (validate.yml AUSENTE); .github/workflows/validate.yml:4 (`pull_request:` sem filtro), :1412, :1447 (runs-on: Ceo); .github/workflows/red-team.yml:6-8 (politica de fork escrita em PROSA); PLAN-184:1058-1062 (AC-9), :1121-1127 (OQ-8)

**Cura proposta.** Item [P0] na W1: o arquivo novo declara a postura de fork EXPLICITAMENTE, copiando um dos dois precedentes in-repo (guard duro `head.repo.full_name == github.repository`, como adapter-live/shadow-ci, OU `IS_FORK_PR` com degradacao visivel, como red-team/tournament), com a razao no comentario. E o AC-9 registra que o PR de teste e intra-repo — um PR de fork nao serve como prova de paridade sem que a decisao de fork esteja tomada.

### SEC-P1-5 — A §4 examinou `.claude/adr/**` pela porta errada: ha um segundo acoplamento de existencia que a regra de escolha de alvo da W0-US2 nao encontra

**Como falha.** A §4 amarra `.claude/adr/**` ao `test_threat_model_coverage.py` e, por causa do fallback `startswith`, instrui o executor a escolher um alvo 'cujo sumico seja de fato observavel' — o que leva a um `ADR-NNN-*.md` citado pelo threat-model. Existe um segundo acoplamento, independente e mais bruto: `tests/integration/test_install_smoke.py:70` afirma a existencia de `.claude/adr/README.md` no target instalado. Um commit que apague ou mova `.claude/adr/README.md` (ou reorganize os ADRs em subdiretorios) toca so `.claude/adr/**`, pula os 4 pesados, e o adopter passa a receber uma arvore de ADR sem indice — sem vermelho em lugar nenhum, porque a suite que afirmaria isso e a mesma que so roda no job pesado. A regra de escolha de alvo do plano, calibrada para o `startswith`, aponta para longe deste arquivo.

**Evidência.** tests/integration/test_install_smoke.py:70 (`target_claude / "adr" / "README.md"` em expected_paths) + :73-74; PLAN-184:286-295 (§4, so o threat-model), :755-758 (restricao de escolha do alvo na W0-US2)

**Cura proposta.** A prova (b) da W0-US2 deixa de ser 'aplicar as tres operacoes AO caminho' e passa a ser 'derivar a lista de arquivos sob o prefixo que aparecem literalmente em qualquer suite pesada, e aplicar as tres operacoes a CADA UM'. Um comando so ja resolve: grep dos literais de caminho nos quatro escopos pesados. Amostrar um prefixo heterogeneo e generalizar e a classe 'guard verde porque nao ve o alvo' que este mesmo plano invoca na §3.

### SEC-P1-6 — Nenhum AC amarra o conjunto de validadores de governanca ao job NAO filtrado — e a §9 ja aponta para desmonta-lo

**Como falha.** A resposta 'contribuidor externo nao escapa da governanca escolhendo paths' e verdadeira HOJE por uma coincidencia de layout: todos os validadores normativos moram no job `validate`, que o escopo preserva. Nenhum AC declara isso como invariante — o AC-3 so exige que o job execute no commit so-docs do AC-2, o que e uma observacao de UM run, nao um contrato sobre o CONTEUDO do job. E a §9 do proprio plano nomeia o A3: 'separar validacao de .md da execucao de suites dentro do job de governanca'. No dia em que alguem mover, digamos, o passo de contamination (`validate.yml:191-192`) ou o `check-spec-drift.py` (`:653`) para o workflow filtrado atras de `paths-ignore`, a escolha de paths por um contribuidor externo VIRA bypass — e nenhum AC deste plano dispara.

**Evidência.** .github/workflows/validate.yml:44 (validate-governance.sh), :64 (check-claude-md-claims), :109 (verify-counts), :191-192 (check-contamination.sh), :479-480 (check-audit-registry-coverage), :652-653 (check-spec-drift); PLAN-184:1031-1033 (AC-3), :1009-1014 (§9/A3); molde in-repo de manifesto: .github/workflows/smoke-install.yml:185,193 (`.claude/governance/gate-scripts-manifest.txt`)

**Cura proposta.** AC novo: um manifesto RASTREADO enumera os passos de validacao de governanca que tem de viver no job nao filtrado, e um teste no job de governanca compara o manifesto contra os `name:` de passo do `validate.yml` — falha se qualquer um migrar para o arquivo filtrado. O repo ja pratica esse padrao (`gate-scripts-manifest.txt`). Sem isso o plano deixa uma armadilha armada para o A3.

## Nice-to-have (advisory) — P2

### SEC-P2-7 — `.claude/skills/**` e a terceira familia com acoplamento de existencia, e nao aparece em lugar nenhum da §4

**Como falha.** `tests/integration/test_install_smoke.py:66` afirma que `.claude/skills/core` existe no target instalado. E acoplamento de diretorio (mais fraco que os de arquivo), mas e do mesmo mecanismo: um commit que reorganize a arvore de skills tocando so `.claude/skills/**` — familia dominada por SKILL.md, portanto candidata natural da derivacao 'so-docs' da W0-US1 — pula os 4 pesados e a unica asserção sobre a entrega de skills ao adopter nao roda. O restante da cobertura de skills (lint, inventory idempotency, placeholder lint, validate-governance.sh) esta no job preservado, entao o dano e limitado — mas a §4 declara ter enumerado os contraexemplos e nao cita esta familia.

**Evidência.** tests/integration/test_install_smoke.py:66 (`target_claude / "skills" / "core"`); .claude/scripts/validate-governance.sh:43-92,177-193 (cobertura preservada de skills no job de governanca); PLAN-184:265-295 (§4)

**Cura proposta.** Incluir `.claude/skills/**` na varredura derivada proposta no SEC-P1-5 e registrar o resultado na §4 — REJEITADO ou com excecao nomeada, como o plano ja faz para `docs/**` e `.github/**`.

## What I would NOT change

- Manter o job `Governance, health, contamination, shellcheck` FORA do filtro, rodando em todo commit. Verifiquei passo a passo: e ali que moram TODOS os validadores de markdown normativo — validate-governance.sh (:44, que varre `.claude/skills/**/SKILL.md` + team.md/frontend-team.md), check-claude-md-claims (:64), verify-counts (:109), check-contamination.sh (:191-192), check-spec-drift (:653), check-audit-registry-coverage (:479). Essa decisao e o que faz o plano inteiro sobreviver a minha critica; nao a otimize.
- A doutrina denylist-sobre-allowlist da §3. A direcao de falha esta certa, e a evidencia in-repo e mais forte do que o plano diz: o `smoke-install.yml` e uma allowlist que, pelos proprios comentarios (:88 'a filter that fires on the PR and not on the merge is a gate with a hole in it', :12-14 e :20-22 sobre 'red gate nobody runs'), ja precisou de tres remendos por omissao de entrada.
- A exclusao dura de `.github/**` da denylist e a exigencia de o arquivo novo disparar sobre si mesmo (Check da W1, plan:850). Corretas como escritas; meu SEC-P1-3 apenas acrescenta o guard que as torna invariantes em vez de snapshot.
- A A2 (tirar os 2 jobs seriais do `Ceo` para `ubuntu-latest`). Do meu ponto de vista e melhoria de superficie de ataque — menos execucao alcancavel por PR em runner self-hosted — e nao ha troca de seguranca escondida: `grep -n 'secrets\.' .github/workflows/validate.yml` devolve zero, entao nenhum dos jobs movidos consome segredo.

## Cobertura declarada

Li o PLAN-184 inteiro (1293 linhas) e verifiquei contra o disco: `.github/workflows/validate.yml` (bloco `on:`, concurrency, permissions e os 7 jobs — confirmei runs-on/timeout/`if:` de cada um e o escopo real de cada passo do job de governanca), `coverage.yml`, `smoke-install.yml`, `red-team.yml`, e as suites exclusivas dos jobs pesados (`tests/integration/`, `tests/formal_verification/`, `tier_policy_cli/tests`, `tournament/tests`). Enumerei o acoplamento por-caminho dessas suites por grep de literais + leitura de `tests/integration/conftest.py` (que confirma isolamento em tmpdir, portanto a maior parte das familias PASSARIA na prova de inercia do plano). Fiz censo de tipos de arquivo sob `.claude/plans`, `.claude/skills`, `.claude/adr` e `SPEC/`. Confirmei ausencia de guard de fork em `validate.yml` e presenca em 6 irmaos, ausencia de segredos em `validate.yml`, e que `paths-ignore` nao aparece em nenhum artefato do repo fora deste plano. NAO cobri (fora da minha faixa, por instrucao): a aritmetica de custo/atribuicao das §1-§2, a reconciliacao da W0-US5, o dimensionamento de timeout da W0-US3/W2, e a escolha Rota B x Rota C do ponto de vista de pipeline. TRES claims do plano permanecem NAO verificaveis por mim sem rede e nao as endossei: a semantica exata de `paths-ignore` do GitHub, o escopo global de `concurrency.group` entre workflows, e a nao-aplicacao de filtros a `workflow_dispatch` — o proprio plano ja as declara como nao verificadas (:658-692). Nao encontrei nenhuma instrucao embutida dirigida a mim nos arquivos lidos.
