# vmci2-approved — ratificação pós-fato do PLAN-194 VM-CI, 2.ª leva (os bytes canônicos que os merges dos PRs #4 e #5 puseram no `main`)

> Este arquivo nasce do rascunho `vmci2-approved.md.draft` pelo gerador `vmci2/gen-ratify.py`; não se
> edita à mão. Antes de assinar, a partir da raiz do repositório, com o `main` local igual a
> `refs/remotes/origin/main` depois de `git fetch origin`:
> `python3 -I -B .claude/plans/PLAN-194/vmci2/gen-ratify.py --check --anchor 0e2511b1fdb05c8faf5a4cdf84707a4be1be89a4
> --main-ref refs/remotes/origin/main`
> tem de terminar com `OK` e código 0 — ele confere, entre outras coisas, que nenhum dos 7 caminhos do
> Scope mudou entre o Anchor e `refs/remotes/origin/main`; se recusar, não assine.
> Assinatura, 1 pedido de senha: `gpg --local-user <a impressão digital de .claude/sentinel-signers.txt>
> --detach-sign --armor .claude/plans/PLAN-194/vmci2-approved.md` (gera `vmci2-approved.md.asc` ao lado).
> Conferência contra o allowlist (GOODSIG e VALIDSIG ligados, impressão digital no allowlist):
> `python3 -I -c 'import sys; sys.path.insert(0, ".claude/hooks"); from pathlib import Path; from
> _lib.gpg_verify import verify_detached; print(verify_detached(Path(sys.argv[1]), Path(sys.argv[1] +
> ".asc"), allowlist_path=Path(".claude/sentinel-signers.txt")))' .claude/plans/PLAN-194/vmci2-approved.md`
> tem de imprimir `(True, '<impressão digital>', '')`. O commit do sentinel com a `.asc` é livre (oráculo
> `--is-canonical` = 0 para os dois). Push é decisão sua.

Plan: PLAN-194
Wave: VM-CI 2 — ratificação pós-fato dos merges dos PRs #4 e #5 (jobs de Ownership e Smoke na máquina virtual dos runners, verificação de modelos formais em matriz, primeiro fsync do spool, cache de descoberta do planejador por objetivos (`goap-planner.py`), histórico completo no checkout da matriz e do coverage)
Anchor-SHA: 0e2511b1fdb05c8faf5a4cdf84707a4be1be89a4
Base-SHA: 3ecb388a72eb848b524b4619b19aac11b29fb1f2
File-sha256: .claude/hooks/_lib/spool_writer.py 1f0104a9f0794b9f025ae6f7614aa356be5308c8d75ad3e0636a765c4217cd88
File-sha256: .claude/hooks/_lib/tests/test_goap_planner.py 658d77d176d70994f08424d7814e2ad78956ed67c082de3d48278eb4928e4b6c
File-sha256: .github/workflows/coverage.yml e41dc4047068122eb06e1f6208897ea2a25e8e4707e960218765ae1aafcd27f2
File-sha256: .github/workflows/formal-verify.yml 7fe9ee54f2e55e6f403914527dfad77e26d5afe8a1860a04472bdc7d747e8463
File-sha256: .github/workflows/ownership-nightly.yml 92342b8ce69f4269a1f4eb905ac9e14eec3cbc4194076d603fa1f130815e4d87
File-sha256: .github/workflows/smoke-install.yml 431ca942a9e60fbf2f5d49c1df133a68628e8b78acd04d8401450a056ba6a5b4
File-sha256: .github/workflows/validate.yml ada86947fc4404a2a66a81c1126d332f8ea040818515915fcc3a67b9a59845ef
Record: .claude/plans/PLAN-194/vmci2/pr4-pr5.patch
Record-sha256: 4817e9cdde0eef6c633a3b68ec0afcff51f85c435c98cb2148c25fddfc4f3ddd
Review: .claude/plans/PLAN-194/vmci2/REVIEW-pr4-pr5.md
Review-sha256: 45b39ee20fdaeb1568a9b0c91afb6df950f440dd9ad0de7156f9c65557ab2aa2
Control: .claude/plans/PLAN-194/vmci2/red-control.txt
Control-sha256: efd681d768cc3dcf0d9a2c7e3096c23d7e4c403670377ae07cbf62be5395115a
Generator: .claude/plans/PLAN-194/vmci2/gen-ratify.py
Generator-sha256: 8a2a35cf70188001bb3988e0876566ac0d064ffe99c5c2baeaed64d5d33206f7
Data: a da assinatura, registrada na `.asc`

## O que esta assinatura ratifica, e nada além

- Os bytes exatos dos 7 arquivos no Anchor-SHA, pelos sha256 acima:
  - `.claude/hooks/_lib/spool_writer.py`: 115.572 bytes, blob `2fbae393b895…`
  - `.claude/hooks/_lib/tests/test_goap_planner.py`: 17.223 bytes, blob `8789326d6553…`
  - `.github/workflows/coverage.yml`: 14.124 bytes, blob `2c5210b2bba3…`
  - `.github/workflows/formal-verify.yml`: 4.156 bytes, blob `dc471e97e8e7…`
  - `.github/workflows/ownership-nightly.yml`: 14.976 bytes, blob `3547f97cb06f…`
  - `.github/workflows/smoke-install.yml`: 63.294 bytes, blob `d562d0407194…`
  - `.github/workflows/validate.yml`: 97.043 bytes, blob `7dbbf634432b…`
  Os 7 são canônicos (oráculo `--is-canonical` = 1, medido); 2 deles, `validate.yml` e `coverage.yml`,
  também estão na lista do kernel de arbitragem (medido). Na Base, esses 2 estão exatamente nos blobs que
  o `vmci-approved.md` ratificou (`a1b8d1124bd6…` e `4e4919be8063…`): a cadeia de bytes ratificados
  desses 2 arquivos fica contínua até o Anchor.
- Os bytes são os REVISTOS: o gerador recusa um Anchor cujos 7 arquivos não tenham os sha256, tamanhos,
  blobs e modos que o `REVIEW-pr4-pr5.md` §1 lista. Um PR posterior que toque qualquer um dos 7 não
  entra nesta assinatura — nem pelo Anchor, nem depois dele.
- O registro do que entrou é o `Record`: `git diff --full-index <Base> <Anchor> --` nos 7 caminhos:
  7 arquivos, +841 −188; 1.323 linhas, 61.665 bytes.
  O gerador recusa um Record que não seja, byte a byte, o revisto.
  Entre a Base e o Anchor mudam também outros caminhos, inclusive código e scripts que os workflows
  canônicos executam. Para todos eles o oráculo da Base dá 0 e o classificador do kernel de arbitragem da
  Base também dá 0 (medido). O gerador recusa o Anchor se o conjunto dos caminhos que mudam não for
  exatamente o medido, ou se algum caminho canônico ou do kernel fora do Scope tiver mudado. Esta
  assinatura não ratifica esses outros caminhos.
- A assinatura não ratifica commits depois do Anchor-SHA: qualquer mudança posterior nesses 7 arquivos é
  mudança canônica nova.

## Como os bytes entraram (pela forma)

- Entraram no `main` por merges de PR no GitHub, sem sentinel assinado: o PR #4 em 2026-10-13T18:15:02Z
  (`baf9de11f427`, pais `3ecb388a72eb` + `2e600b7319c2`, ramo `codex/ci-reliability-parallel-20261013`) e
  o PR #5 em 2026-10-14T17:33:00Z (o Anchor, pais `baf9de11f427` + `80c0d7c78592`, ramo
  `codex/ci-checkout-tags-20261013`). A API mostra a conta do Owner como quem abriu e quem mergeou os 2
  PRs, e a organização não tem app do GitHub instalado (0 instalações).
- Autoria: o git registra a conta do Owner como autora e committer de todos os commits dos 2 ramos, e
  eles estão sem assinatura (`%G?` = `N`, medido). O campo de autor do git é declarado por quem faz o
  commit e não prova quem o escreveu. Pelos registros locais da sessão do CEO que preparou esta
  ratificação: o patch do `coverage.yml` que entrou no PR #5 foi redigido nessa sessão; o commit
  `80c0d7c78592` do PR #5, o que leva esse patch, saiu de um script preparado nessa sessão e executado
  pelo Owner nela; e um commit não canônico do PR #5 foi feito e empurrado a partir de um clone dela.
  Quem escreveu os demais commits não foi medido. Esta assinatura não atesta a autoria de nenhum commit.
- O guard de edição canônica só vê o que um agente edita numa sessão; um merge pelo GitHub não passa por
  ele, e o `main` não tem proteção de branch nem ruleset, no repositório ou na organização (medido pela
  API em 2026-10-14).
- Esta assinatura fecha a cadeia desses bytes depois do fato: liga o Anchor-SHA, os sha256 dos 7
  arquivos, o registro do diff, a revisão medida, os controles e o gerador à chave do allowlist.
- A CLASSE — caminho canônico entrando no `main` por merge no GitHub sem cerimônia — segue aberta: ela já
  tinha ocorrido antes destes 2 merges (o `vmci-approved.md` ratificou outra leva depois do fato), e nada
  no repositório nem nas configurações medidas impede a próxima; fechá-la está fora desta assinatura.

## O que fica com o Owner, fora dos bytes assinados (pela forma)

- Tudo o que vive no GitHub ou na máquina virtual dos runners: a variável `VM_CI_ENABLED`; o grupo de
  runners (quais workflows e repositórios ele aceita, se aceita repositório público); os runners (quantos,
  se efêmeros, usuário Unix, diretório temporário, ferramentas, disco, se cada job roda num ambiente
  isolado e destruído depois); as credenciais e o acesso à máquina; e a medição contínua. Esta assinatura
  ratifica bytes; ela não atesta nenhuma condição da máquina nem do GitHub, nem as condições do
  `REVIEW-pr2.md` §8.

## Resíduos declarados (pela forma)

- Gravação do spool: o adiamento do primeiro fsync é durável (o fsync do corpo cobre o cabeçalho, mesmo
  inode, antes do commit no diário e do sinal de sucesso); quando esse fsync falha, o evento pode aparecer
  duas vezes depois (severidade baixa, `REVIEW-pr4-pr5.md` §2); e parte dos testes novos (arquivo não
  canônico) prende o mecanismo da otimização, não a propriedade de durabilidade.
- Workflows: checkout com credencial persistida (o padrão do `actions/checkout`) nos jobs que não a
  desligam, agora num host persistente compartilhado; o pino do arquivo do verificador de modelos é
  sha256 sobre um arquivo de release que pode mudar sob o mesmo endereço (o pino teve 3 valores dentro do
  PR #4), e o valor que decide mora num script NÃO canônico chamado pelo workflow canônico; o job desse
  verificador segue com `continue-on-error` no nível do job, a forma que escondeu por meses um vermelho
  contínuo; teto de 150 min em 12 jobs que podem ir para a máquina virtual; o gate do Ownership segue
  exato no conjunto de vermelhos, mas consome, por uma porta que o próprio gate documenta como só de
  controle positivo, um adaptador fora do manifesto de integridade; e a cura do vermelho de 13–14/10
  (estado de git deixado no workspace por outro job) é por job — a classe segue aberta nos outros jobs
  (`REVIEW-pr4-pr5.md` §4).
- Este sentinel não é destrava de edição, por 3 fatos medidos sobre estes bytes (R7 do `red-control.txt`):
  o nome não casa nenhum padrão de descoberta do `check_canonical_edit.py` nem do `ceo-boot.py`; o texto
  não tem linha de aprovação que o guard aceite; e o leitor de Scope do guard devolve conjunto vazio para
  ele. Assinado, ele não libera agente nenhum para editar os 7 arquivos.

## Revisão

- `REVIEW-pr4-pr5.md` (sha256 no cabeçalho): revisão medida — bytes previstos, durabilidade do spool,
  cache do planejador, roteamento para a máquina virtual, credenciais, pino do verificador de modelos,
  vermelho escondido desse verificador, tetos de tempo, o gate do Ownership, o vermelho de 13–14/10, a
  classe dos merges sem cerimônia.
- `red-control.txt` (sha256 no cabeçalho): os controles do gerador e do sentinel, com o resultado medido.
- `gen-ratify.py` (sha256 no cabeçalho): o gerador que preencheu este arquivo; as recusas estão listadas
  no topo dele. Ele lê objetos do git e, além do próprio git, executa só código da Base (o oráculo canônico
  e o classificador do kernel, extraídos com `git archive`); código do Anchor não é executado.
- As rodadas de rail sobre estes materiais revisam ESTES bytes; os registros delas vivem fora deste
  arquivo.

## Scope

- `.claude/hooks/_lib/spool_writer.py`
- `.claude/hooks/_lib/tests/test_goap_planner.py`
- `.github/workflows/coverage.yml`
- `.github/workflows/formal-verify.yml`
- `.github/workflows/ownership-nightly.yml`
- `.github/workflows/smoke-install.yml`
- `.github/workflows/validate.yml`
