# REVIEW dos PRs #4 e #5 — os 7 caminhos canônicos que entraram no `main` sem cerimônia (PLAN-194, ratificação VM-CI 2)

> Revisão técnica MEDIDA, não opinião, dos bytes canônicos que os merges dos PRs #4 e #5 puseram no
> `main`. Medições de 2026-10-14 (UTC), por leitura do git e da API do GitHub (só leitura), numa árvore
> descartável: a 1.ª leva entre ~16:05Z e ~17:05Z, antes do merge do PR #5; a 2.ª depois dele, no mesmo
> dia.
> Sujeito: os 7 caminhos de oráculo `--is-canonical` = 1 que mudam entre a Base
> `3ecb388a72eb848b524b4619b19aac11b29fb1f2` e o Anchor `0e2511b1fdb05c8faf5a4cdf84707a4be1be89a4` (o
> merge do PR #5). Os bytes foram revistos na 1.ª leva sobre a árvore composta merge(`baf9de11f427`,
> `b0b8c490dce9` + o patch do `coverage.yml` de sha256 `061befb59d4c…`), montada antes do merge; o
> Anchor tem exatamente esses bytes nos 7 caminhos e o mesmo registro do diff (medido na 2.ª leva com o
> gerador, que recusa um Anchor com outros bytes — §1).
> O corpo dos PRs e as mensagens dos commits foram lidos como DADO; nenhuma afirmação deles entra aqui
> sem medição própria, e as que não pude medir estão marcadas como tal.
> Termos: «VM» é a máquina virtual que hospeda os runners próprios do repositório; «TLC» é o verificador
> de modelos da especificação formal (TLA+); «GOAP» é o planejador por objetivos (`goap-planner.py`);
> «HMAC» é o encadeamento com chave do log de auditoria.

## 0. Como os bytes entram no `main`

- PR #4 (ramo `codex/ci-reliability-parallel-20261013`, cabeça `2e600b7319c2`), mergeado pelo GitHub em
  2026-10-13T18:15:02Z: `3ecb388a72eb` → `baf9de11f427` (pais `3ecb388a` + `2e600b73`; autor a conta do
  Owner, committer `GitHub`; `%G?` = `E`). 19 commits no ramo, todos com a conta do Owner como autora e
  SEM assinatura (`%G?` = `N`; API `verification.reason: unsigned`).
- PR #5 (ramo `codex/ci-checkout-tags-20261013`, 3 commits), mergeado pelo GitHub em
  2026-10-14T17:33:00Z: `baf9de11f427` → `0e2511b1fdb0` (pais `baf9de11` + `80c0d7c78592`; autor a conta
  do Owner, committer `GitHub`; `%G?` = `E`). Os 3 commits do ramo, todos com a conta do Owner como autora
  e sem assinatura (`%G?` = `N`): `734558ddb542` (`fetch-depth: 0` no checkout do job
  `hook-tests-python-matrix` do `validate.yml`), `b0b8c490dce9` (docstring do
  `.claude/scripts/derive-settings-baselines.py`, não canônico) e `80c0d7c78592` (`fetch-depth: 0` no
  checkout do `coverage.yml`; as linhas dele são as do patch acima).
- A API mostra a conta do Owner como quem abriu e quem mergeou os 2 PRs. A organização não tem app do
  GitHub instalado (API `orgs/…/installations`: 0).
- Autoria, pela forma: o campo de autor do git é declarado por quem faz o commit e não prova quem o
  escreveu. Pelos registros locais da sessão do CEO que preparou esta revisão: o patch do `coverage.yml`
  foi redigido nessa sessão; o `80c0d7c78592`, que leva esse patch, saiu de um script preparado nessa
  sessão e executado pelo Owner nela (o registro da sessão traz a execução e a saída do script, com esse
  SHA); e o `b0b8c490dce9` foi feito e empurrado a partir de um clone dela (reflog do clone: o commit e,
  em seguida, «update by push» no ramo do PR #5). Quem escreveu os demais commits não foi medido. Esta
  revisão não atesta a autoria de nenhum commit. Para as 4 linhas do patch do `coverage.yml`, quem
  redigiu o patch e quem redigiu esta revisão trabalham na mesma sessão.
- Fronteira medida (API, 2026-10-14): `main` sem proteção de branch (`404 Branch not protected`), sem
  ruleset no repositório (`[]`) nem na organização (`[]`); permissão padrão do token dos workflows `read`.
  O guard de edição canônica só vê o que um agente edita numa sessão; o merge pelo GitHub não passa por
  ele.
- A CLASSE, pela forma: caminho canônico entrando no `main` por merge no GitHub sem cerimônia. Ela já
  tinha ocorrido antes destes 2 merges (o `vmci-approved.md` ratificou outra leva depois do fato). Esta
  revisão não fecha a classe; ela registra que a repetição já pedia cura estrutural e que nada medido
  impede a próxima ocorrência.

## 1. O que entra — os bytes revistos

Árvore inteira entre a Base e o Anchor: 28 caminhos mudam. O oráculo da Base dá 1 para exatamente estes
7 e 0 para os outros 21; o oráculo do Anchor, rodado à parte numa árvore descartável, dá as mesmas
respostas. Entre os 21 há código e scripts que os workflows canônicos executam (§3, §4.3, §4.6, §4.8). O
classificador do kernel de arbitragem da Base (`_is_kernel_path` do `check_arbitration_kernel.py`) dá 1
só para `validate.yml` e `coverage.yml` entre os 28, e 0 para os 21. O gerador refaz essas contas sobre o
Anchor, com o código da Base, e recusa o Anchor se o conjunto dos caminhos que mudam não for exatamente
estes 28.

| caminho | sha256 no Anchor | bytes | blob | modo | blob na Base | +/− |
|---|---|---|---|---|---|---|
| `.claude/hooks/_lib/spool_writer.py` | `1f0104a9f0794b9f025ae6f7614aa356be5308c8d75ad3e0636a765c4217cd88` | 115.572 | `2fbae393b895` | 100644 | `d65cf55bacc9` | +18 −4 |
| `.claude/hooks/_lib/tests/test_goap_planner.py` | `658d77d176d70994f08424d7814e2ad78956ed67c082de3d48278eb4928e4b6c` | 17.223 | `8789326d6553` | 100644 | `2b60d3bb02c5` | +35 −0 |
| `.github/workflows/coverage.yml` | `e41dc4047068122eb06e1f6208897ea2a25e8e4707e960218765ae1aafcd27f2` | 14.124 | `2c5210b2bba3` | 100644 | `4e4919be8063` | +4 −0 |
| `.github/workflows/formal-verify.yml` | `7fe9ee54f2e55e6f403914527dfad77e26d5afe8a1860a04472bdc7d747e8463` | 4.156 | `dc471e97e8e7` | 100644 | `3c51b5823ec8` | +40 −47 |
| `.github/workflows/ownership-nightly.yml` | `92342b8ce69f4269a1f4eb905ac9e14eec3cbc4194076d603fa1f130815e4d87` | 14.976 | `3547f97cb06f` | 100644 | `00386077af22` | +186 −66 |
| `.github/workflows/smoke-install.yml` | `431ca942a9e60fbf2f5d49c1df133a68628e8b78acd04d8401450a056ba6a5b4` | 63.294 | `d562d0407194` | 100644 | `e298a5871877` | +548 −71 |
| `.github/workflows/validate.yml` | `ada86947fc4404a2a66a81c1126d332f8ea040818515915fcc3a67b9a59845ef` | 97.043 | `7dbbf634432b` | 100644 | `a1b8d1124bd6` | +10 −0 |

- Na Base, `validate.yml` e `coverage.yml` estão exatamente nos blobs que o `vmci-approved.md` ratificou
  (`a1b8d1124bd6…`, `4e4919be8063…`). Esses 2 também estão na lista do kernel de arbitragem
  (`check_arbitration_kernel.py`, medido); os outros 5, não.
- Registro: `git diff --full-index <Base> <Anchor> --` nos 7 caminhos = 7 arquivos, +841 −188, 1.323
  linhas, 61.665 bytes, sha256 `4817e9cdde0eef6c633a3b68ec0afcff51f85c435c98cb2148c25fddfc4f3ddd`. O
  gerador recalcula e recusa um registro que não seja byte a byte este (a configuração local do
  repositório ou outra versão do git que mude a forma do diff também caem aí).
- O que muda, por arquivo: §2 (`spool_writer.py`), §3 (`test_goap_planner.py`), §4 (os 5 workflows).

## 2. `spool_writer.py` — o primeiro evento de um spool novo passa a pagar 1 fsync em vez de 2

- O que mudou: `_ensure_spool_header` ganha `sync_header=True` (padrão); `spool_append` chama com
  `sync_header=False`. O cabeçalho de um spool novo é escrito sem fsync; o evento é escrito em seguida no
  MESMO arquivo e o fsync do evento é o único. Quem chama `_ensure_spool_header` fora do `spool_append`
  mantém o fsync do cabeçalho.
- Durabilidade — CORRETA, por 3 fatos lidos no código:
  1. o fsync é do arquivo (inode), não do descritor: o fsync do corpo grava também os bytes do cabeçalho
     que ainda estão no cache do sistema, porque é o mesmo arquivo;
  2. é o mesmo inode: `spool_append` segura o lock por PID do spool do cabeçalho até o fim do fsync, e o
     dreno só renomeia o spool ativo segurando esse mesmo lock (`spool_writer.py`, Phase 2 do dreno), então
     ninguém troca o arquivo no meio;
  3. nada é confirmado antes do fsync: o envelope `commit` do diário e o sinal de sucesso
     (`last_append_succeeded`) só vêm depois dele; se o fsync falha, a função sai antes de ambos.
  Alinha com o ADR-055-AMEND-1 (1 fsync por emissão, só o spool no caminho quente). Nenhum evento
  confirmado fica menos durável do que antes.
- Severidade baixa — evento DUPLICADO quando o primeiro fsync falha. Antes, uma falha no fsync do
  cabeçalho abortava ANTES de escrever o evento. Agora o evento já está no arquivo quando o fsync falha; o
  `audit_emit` vê o sinal de falha e grava o evento direto no log canônico (o recuo síncrono); mais tarde o
  dreno lê a linha que ficou no spool (o dreno não exige o envelope `commit` — é o que o teste de queda
  depois do fsync usa para recuperar o evento) e a grava de novo. A forma já existia para os eventos
  seguintes de um spool (falha no fsync do corpo); a mudança a estende ao primeiro. Exige falha de fsync,
  e o resultado é duplicata visível, não perda.
- Os testes novos (`.claude/hooks/tests/test_spool_first_append_durability.py`, NÃO canônico, fora desta
  assinatura): dos 6, 4 prendem a OTIMIZAÇÃO, não a propriedade — contam chamadas de fsync (1 no primeiro
  evento, n+1 em n eventos, 1 no cabeçalho avulso), comparam o inode, ou exigem o envelope `begin` antes
  do fsync que falha (o que só vale para a forma nova). Os 2 restantes medem a propriedade que um teste em
  processo consegue medir: depois de uma saída abrupta logo após o fsync (e logo após a confirmação), o
  dreno entrega o evento exatamente uma vez e a cadeia HMAC verifica. Nenhum teste em processo mede queda
  de energia; a durabilidade acima é argumento sobre a semântica do fsync, não medição. Nenhum dos 6
  observa a duplicata descrita acima.

## 3. `test_goap_planner.py` — testes do cache de descoberta do GOAP

- O arquivo canônico só ganha a classe `TestAuditDiscoveryCache` (+35). O código que ela testa,
  `.claude/scripts/goap-planner.py`, é código de produção NÃO canônico (oráculo 0), que também muda entre
  a Base e o Anchor: guarda em `_audit_hooks_path` o diretório `.claude/hooks` achado subindo a partir de
  `__file__`, só quando a busca acha; reinsere o caminho em `sys.path` se alguém o tirou; e executa o
  import de `_lib.audit_emit` a cada evento (já era assim na Base).
- CORRETO: a âncora é `__file__` (não HOME, cwd nem projeto), então o valor não muda no processo; uma busca
  sem sucesso não é guardada e é refeita; cada evento chega ao emissor atual (o teste troca o emissor entre
  chamadas e confere). Os 2 testes cobrem o acerto, a busca repetida proibida, a falha não guardada e a
  restauração do `sys.path`.

## 4. Os 5 workflows

### 4.1 Roteamento: nenhum PR nem fork chega à VM

- Os 12 jobs que podem ir para a VM (4 no `ownership-nightly.yml`, 8 no `smoke-install.yml`; 10 deles
  novos — o `smoke` e o `ownership-e2e` já existiam e eram `ubuntu-latest` na Base) usam a expressão dos
  8 jobs que o `vmci` ratificou, com uma cláusula a mais (`github.repository ==
  'Canhada-Labs/ceo-orchestration'`): VM só com `VM_CI_ENABLED == '1'` E `github.ref == 'refs/heads/main'`
  E evento `push`, `schedule` ou `workflow_dispatch`; senão `ubuntu-latest`. O `formal-verify.yml` fica
  sempre no `ubuntu-latest` (literal).
- Barreira do lado do servidor, medida (API, 2026-10-14): o grupo de runners da VM tem
  `restricted_to_workflows: true` e 6 workflows permitidos — os 4 deste repositório que roteiam para a VM
  (`validate`, `coverage`, `ownership-nightly`, `smoke-install`), todos em `@refs/heads/main`, e 2 de outros
  repositórios; `allows_public_repositories: true`; 3 repositórios no grupo (este, público, e 2 privados);
  4 runners online, rótulos `self-hosted,Linux,X64,canhada-ci`. `VM_CI_ENABLED` = `"1"` (desde
  2026-10-11T00:37:01Z).
- Medido em runs: os `workflow_dispatch` do Ownership no ramo do PR #4 rodaram no hospedado (run
  `38440148264`, 4 jobs em runners `GitHub Actions …`); os do `main` rodaram na VM (dispatch
  `38445282939`, schedule `38525608925`); os `pull_request` do PR #5 rodaram no hospedado
  (`38479098640`).
- Nenhum dos 5 arquivos tem `pull_request_target`, `workflow_run`, `issue_comment` ou
  `repository_dispatch` (medido). Seguem valendo, pela forma, os resíduos já declarados no
  `REVIEW-pr2.md`: a comparação de strings do GitHub ignora caixa, e um gatilho que roda o arquivo do
  `main` com dados de fork seria aceito pelo grupo.

### 4.2 Credencial persistida no checkout, num host persistente compartilhado

- `ownership-nightly.yml` (4 de 4 checkouts) e `smoke-install.yml` (8 de 8) desligam
  `persist-credentials`; `validate.yml` (0 de 7) e `coverage.yml` (0 de 1) não. Com a credencial
  persistida (o padrão), o `actions/checkout` pinado (`de0fac2e…`, v6.0.2) grava o token do job num
  arquivo de credenciais no diretório temporário do runner (`_work/_temp/git-credentials-*.config`), que o
  `.git/config` do workspace inclui por `includeIf`; o passo de limpeza do fim do job tira as entradas
  `includeIf` e apaga o arquivo (medido no log do job `115461682678`, run `38445209033`, na VM). Os bytes
  desses 2 arquivos já eram assim na Base (o `vmci` ratificou-os assim); o que mudou é o contexto: o host
  da VM é persistente e atende jobs de 3 repositórios, e o token fica em disco nesse host enquanto o job
  roda. O token é `contents: read` (medido no topo dos 2 arquivos e na permissão padrão do repositório).
  Mudar isso é mudança canônica, pacote próprio.

### 4.3 TLC: o pino é sha256 sobre um asset mutável, e quem decide é um arquivo NÃO canônico

- O endereço do arquivo do TLC é o asset `tla2tools.jar` da release `v1.8.0` no GitHub do upstream —
  asset de release pode ser trocado sem mudar o endereço. Dentro do próprio PR #4 o pino passou por 3
  valores (`baf125a6…` em `c2f34fac`, `c0d2f72a…` em `ef96cf08`, `0f56d6a8…` em `f465bb50`), partindo de
  `4c1d62e0…` na Base; o corpo do PR diz que o asset mudou durante a validação (afirmação NÃO verificada
  aqui: ler o upstream está fora do que esta revisão podia consultar). O pino detecta a troca; não a impede
  e não diz qual valor é o legítimo.
- No Anchor, o job baixa e confere o arquivo chamando `docs/formal-verification/run-tlc.sh download`. O
  script REATRIBUI `TLA_TOOLS_SHA256` e `TLA_TOOLS_URL` sem herdar do ambiente; os valores homônimos no
  `env:` do workflow canônico não decidem nada (hoje iguais, medido). O valor que decide mora num arquivo
  com oráculo 0. Pela forma: um workflow canônico que entrega a um arquivo não canônico um pino de
  integridade tira esse pino da cerimônia.

### 4.4 TLC: vermelho contínuo escondido pelo `continue-on-error` do job

- Medido na API: o workflow tem 57 runs na história. Os 37 anteriores ao PR #4 (de 2026-07-01, o mais
  antigo, a 2026-10-12) terminaram com o RUN em `success` e o JOB em `failure`, todos no passo
  «Download + verify tla2tools.jar» — o TLC nunca rodou em CI nesse período. (O registro anterior dizia
  2026-09-21..10-12; a janela medida é maior.) A causa da cor do run é o `continue-on-error: true` no
  nível do JOB: o run fica verde com o job vermelho.
- No PR #4, os commits `c2f34fac`..`35bcbec4` tiraram esse `continue-on-error` (4 runs `failure`
  visíveis) e `ef96cf08` («retain advisory contract») o devolveu. No Anchor ele está lá: a forma que
  escondeu 3 meses de vermelho segue, e um vermelho futuro também fica escondido por ela. Os 3 modelos
  passaram em matriz no `main` depois do merge do PR #4 (run `38445208876`, os 3 jobs `success`).

### 4.5 Teto de 150 min em 12 jobs da VM

- Os 12 jobs que podem ir para a VM têm `timeout-minutes: 150` (antes: 2 jobs com 150, o `smoke` e o
  `ownership-e2e`; a divisão em jobs copiou o teto). Medido na VM: Ownership de 3 min 31 s a 9 min 26 s
  (run `38525608925`); Smoke de 2 min 58 s a 13 min 44 s (run `38445209122`). No hospedado, o mais lento
  foi o `ownership-e2e`, 28 min 55 s (run `38440148264`). Um job travado segura 1 dos 4 runners por até 150
  min, ~11 vezes o mais lento dos 12 jobs medidos na VM. Re-apertar no p95 medido é mudança canônica.
- Fila, medida no push do merge do PR #4: os 9 jobs do Validate (run `38445209033`, criado às 18:15:05Z),
  todos na VM, começaram entre 6 min 41 s e 18 min 50 s depois da criação do run (18:21:46Z a 18:33:55Z).
  De 18:15:07Z a 18:33:55Z, os 4 runners estiveram ocupados o tempo todo por jobs de 3 runs — o próprio
  Validate, o Smoke do mesmo push (run `38445209122`) e o Ownership de um `workflow_dispatch` criado 32 s
  depois (run `38445282939`): pelos horários da API, nenhum runner ficou mais de 1 s entre o fim de um job
  e o início do seguinte. O run do Validate levou 23 min 25 s de parede, da criação ao fim do último job,
  contra 506 s medidos no `REVIEW-pr2.md` (run `38104634181`).

### 4.6 Ownership: o gate segue exato, mas consome um adaptador fora do manifesto

- O gate `scripts/tests/ownership-nightly-gate.sh` (membro do manifesto de integridade do ADR-192,
  conferido por sha256 no próprio workflow) segue comparando o conjunto EXATO de vermelhos com
  `ownership-expected-reds.txt` (3 ids, sem mudança) e o conjunto completo de células com o `--list` da
  tabela. Medido na VM (run `38525608925`): `GREEN=62 RED=3 AMBIG=0 HARNESS-ERR=0` e «RED set stable».
- Mas o workflow agora passa `OWNERSHIP_GATE_HARNESS: python3 scripts/tests/ownership-parallel.py …`, e o
  cabeçalho do próprio gate documenta essa variável como «Test seams (positive control only — CI uses the
  defaults)». O adaptador (`ownership-parallel.py`, oráculo 0) não está no manifesto. Quem produz o mapa
  célula → status que o gate julga passa a ser um arquivo fora da integridade que o ADR-192 pôs no gate —
  pela forma, a mesma classe do §4.3. O adaptador tem teste próprio de controles positivos e negativos
  (`test_ownership_parallel.py`, rodado no workflow), também fora do manifesto.

### 4.7 O vermelho de 13–14/10: tags vazando entre jobs no workspace reaproveitado — e a cura

- Medido: o Validate do `main` estava verde na VM nos 10 runs antes do merge do PR #4 e ficou vermelho
  nos 2 depois (push `38445209033`, schedule `38530617338`); o Coverage, verde na VM nos schedules de 11 a
  13/10 (`38121212088`, `38219761470`, `38363261966`) e vermelho em 14/10 (`38528002572`). Nas pernas 3.9,
  3.10, 3.11 e 3.12 da matriz (VM) e no Coverage (VM),
  os mesmos 2 testes, e só eles: `SupersededLiveRepoTest::test_live_block_is_paste_ready_for_the_literal`
  e `::test_live_upgrade_sh_superseded_matches_ga_tags`, com «no GA tag (vX.Y.Z) carrying
  templates/settings/settings.base.json is visible … a shallow or tagless clone?». A perna 3.14
  (hospedado) passou.
- Mecanismo, pela forma: o teste PULA quando a tag `v1.4.0` não existe no checkout e roda quando existe.
  Os jobs novos do Smoke e do Ownership, agora na VM, buscam tags de release com `--depth 1` no workspace
  do repositório; o runner reaproveita o `.git` desse workspace no job seguinte do mesmo repositório (o
  `actions/checkout` limpa a árvore de trabalho; as tags que já estavam no `.git` ficam — pela forma, e o
  vermelho medido é consistente com isso). O job da matriz e o do Coverage, com checkout raso, passam a ver
  a tag sem a história dela: o teste deixa de pular e falha. No hospedado, cada job começa limpo, sem
  tags, e o teste pula.
- A cura no Anchor: `fetch-depth: 0` no checkout desses 2 jobs (histórico completo e tags). Medido no
  hospedado, perna a perna da matriz: no PR #4 (run `38440081847`, checkout raso) 13.656–13.658 passed e
  62–64 skipped; no PR #5 (run `38479098640`, `fetch-depth: 0`) 13.660–13.662 passed e 58–60 skipped —
  passed +4, skipped −4, a soma igual, as 4 pernas verdes. Ou seja, 4 testes por perna deixam de pular e
  passam; o pulo dos 2 do `SupersededLiveRepoTest` depende da tag `v1.4.0`, que o histórico completo traz;
  quais são os outros 2 não foi identificado. Antes, no hospedado, esses testes pulavam sempre: a derivação
  `--check` não era exercida em CI.
- Medido na VM depois do merge do PR #5 (2.ª leva): o Validate do push do Anchor (run `38607595774`)
  terminou `success`, com os 9 jobs `success`, todos em runners com o rótulo `canhada-ci`; o Coverage
  disparado no `main` sobre o Anchor (run `38607713134`, `workflow_dispatch`) terminou `success`, num
  runner com o mesmo rótulo. A classe — job que lê o estado de git que outro job deixou no workspace —
  segue aberta para os outros jobs da VM; a cura é por job.

### 4.8 `validate.yml`: um passo de diagnóstico que só roda depois de falha

- Além do `fetch-depth: 0`, o `validate.yml` ganha um `print(text)` na função `note()` de um passo
  existente e, no job `opus-4-7-profiler-smoke`, um passo novo, «Diagnose output hook startup and audit
  drain», com `if: ${{ failure() && !cancelled() }}`, que executa `timeout 180 python3
  .claude/scripts/diagnose-output-hook.py` — um script novo, de oráculo 0. Esse job vai para a VM nas
  condições do §4.1 e tem a credencial persistida do §4.2. Pela forma: um workflow canônico passa a
  executar, só depois de uma falha, um script não canônico. O passo só roda com o job já em falha, e um
  passo posterior não desfaz a falha do job.

## 5. O que a assinatura ratifica, e nada além

- Os bytes dos 7 arquivos no Anchor, iguais aos do §1 (o gerador recusa outros), e o registro do diff
  entre a Base e o Anchor nesses 7 caminhos.
- NÃO ratifica: arquivos não canônicos (mesmo os que os workflows executam e que decidem um resultado —
  §4.3, §4.6, §4.8); commits depois do Anchor; o estado do GitHub (variáveis, grupo de runners, proteção
  de branch); a VM (runners, usuários, disco, isolamento); nem as condições do `REVIEW-pr2.md` §8.

## 6. O que fica fora deste pacote (cada item é um pacote próprio do Owner, canônico ou do lado do GitHub/VM)

1. A classe dos merges sem cerimônia (§0): proteção de branch ou ruleset no `main` que exija o caminho da
   cerimônia para os caminhos canônicos, e uma identidade própria para os agentes que escrevem nos ramos
   — decisão do Owner.
2. `persist-credentials: false` nos 8 checkouts do `validate.yml` e do `coverage.yml` (§4.2).
3. Pino do TLC de volta a um arquivo canônico, ou o script do TLC sob cerimônia (§4.3); fonte do arquivo
   que não mude sob o mesmo endereço.
4. `continue-on-error` do TLC fora do nível do job, ou um alerta que leia a conclusão do JOB (§4.4).
5. Tetos de 150 min re-apertados no p95 medido (§4.5).
6. Adaptador do Ownership no manifesto do ADR-192, ou o gate sem depender da porta de controle (§4.6).
7. Isolamento do workspace por job na VM, ou `fetch-depth`/limpeza de tags explícita em todo job que lê
   tags (§4.7).
8. O script de diagnóstico do §4.8 sob cerimônia, ou fora do workflow canônico.

## Apêndice A — dados brutos (2026-10-14)

- Runs lidos: Formal Verification — os 57 da história (`38445208876` é o 1.º do `main` depois do merge do
  PR #4); Validate `38445209033` (push `baf9de11`, VM), `38530617338` (schedule `baf9de11`, VM),
  `38479098640` (PR #5, hospedado), `38365735193` e os 9 anteriores do `main` (verdes; os jobs roteados
  para a VM, em runners com o rótulo `canhada-ci`), `38607595774` (push do Anchor, VM); Coverage
  `38528002572` (schedule `baf9de11`, VM), `38121212088`, `38219761470` e `38363261966` (schedules de
  11 a 13/10, verdes, VM), `38607713134` (dispatch no `main` sobre o Anchor, VM); Ownership `38525608925` (schedule, VM),
  `38445282939` (dispatch no `main`, VM), `38440148264` (dispatch no ramo do PR #4, hospedado); Smoke
  `38445209122` (push `baf9de11`, VM).
- Configuração lida (API, só leitura): grupos de runners da organização e o da VM (workflows permitidos,
  repositórios, runners); variáveis do repositório; proteção do `main`; rulesets do repositório e da
  organização; instalações de app da organização; permissão padrão do token; autor e quem mergeou os PRs.
- Oráculo `--is-canonical` sobre os 28 caminhos que mudam (7 = 1, 21 = 0), o da Base e o do Anchor;
  classificador do kernel de arbitragem da Base sobre os 28 (2 = 1, ambos no Scope). Árvores montadas em
  cópias descartáveis do repositório; nada foi escrito no checkout compartilhado nem no GitHub.
