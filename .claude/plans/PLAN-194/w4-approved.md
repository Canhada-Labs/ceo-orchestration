# w4-approved — sentinel da W4 do PLAN-194 (publish do npm em Node 24 com npm exato; a rc prova o toolchain)

> Assinatura e land em um passo: `bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh`
> (confere as pré-condições, as duas cópias staged dos arquivos canônicos, o patch dormente de
> rollback, o controle vermelho no HEAD e o último registro do rail, aplica o patch, confere que os
> bytes aplicados são os revisados, roda a bateria — as passadas duras do pacote, o actionlint nas duas
> formas do CI, os gates de corpus e as suítes do `pytest.ini` com a divisão de marcadores do CI —,
> preenche Anchor-SHA, Patch-sha256, Rail-Record-sha256 e Data no sentinel do HEAD, assina com a chave
> do allowlist de signatários, stageia o conjunto EXATO e commita; `--dry-run` ensaia sem assinar nem
> commitar). Push é decisão sua.

Plan: PLAN-194
Wave: W4 — publicação npm: Node suportado e npm com versão exata (W4.1, W4.2 e W4.3)
Patch: .claude/plans/PLAN-194/w4/w4.patch
Staged: .claude/plans/PLAN-194/w4/staged-w4/.github/workflows/npm-publish.yml
Staged: .claude/plans/PLAN-194/w4/staged-w4/.claude/governance/npm-trusted-publisher.txt
Patch-sha256: TO-FILL-BY-SIGN
Rail-Record-sha256: TO-FILL-BY-SIGN
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN

## Ratificação (Owner)

- PLAN-194, W4, objetivo: «o publish do GA roda num Node suportado pela publicação sem token (≥ 22.14)
  com npm em versão exata, e a rc prova o toolchain antes do GA». W4.1: «`setup-node` em 24 (ou 22 ≥
  22.14), pinado por SHA; npm com versão EXATA em vez de `^11.5.1`». W4.2: «registrar em
  `npm-trusted-publisher.txt` que a configuração no npmjs.com precisa permitir publicação direta […]
  **NÃO editar a configuração do publicador confiável.**» W4.3: «prova na rc: um passo/job que roda em
  tag rc com o MESMO Node e npm e faz tudo menos publicar (versões conferidas + empacotamento),
  mantendo a regra «rc não publica» intacta».
- Decisão D-12 (PLAN-194, tabela de decisões): «npm EXATO 11.20.0 na W4 (o provado no GA 1.4.2). npm 12
  só com decisão escrita.»
- OQ-5, respondida pelo Owner na S361 (Q9, 2026-10-01): aceitar a prova parcial do publish — a rc só
  prova o Node e o npm, não a publicação — e o playbook de rollback do PLAN-158.
- Linha de base (`PLAN-194/LEDGER.md`, seção «W4 — linha de base do publish»): o run 36719886734 (NPM
  Publish do GA v1.4.2, 2026-09-30) rodou com `node: v20.20.2` e `OK: npm 11.20.0`.
- Tamanho, declarado: o plano estimava 30-60 linhas em 2-3 caminhos; o patch muda 886 linhas (+855
  −31) em 5 caminhos — 353 nos 2 canônicos (`npm-publish.yml` +317 −22, `npm-trusted-publisher.txt`
  +14) e 533 nos 3 livres (o teste +512 −1, `docs/actions-versions.md` +10 −7, `npm/INTEGRITY.md` +2
  −1). Passa do teto de 400 linhas por pacote do modelo de operação; os 5 caminhos ficam abaixo do teto
  de 8. O que passa da estimativa é, no canônico, o job novo da rc (W4.3), cujos passos de toolchain e
  empacotamento são cópias dos do `publish`, e, no livre, a classe de teste nova. Teste e workflow
  landam no mesmo commit porque a classe nova reprova sem os canônicos novos (é o controle abaixo). A
  assinatura ratifica o pacote nesse tamanho.

## O que esta cerimônia entrega, e nada além

- `.github/workflows/npm-publish.yml`, toolchain (W4.1): um `env:` no nível do workflow declara UMA vez
  `PUBLISH_NODE_MAJOR: "24"` e `PUBLISH_NPM_VERSION: "11.20.0"`, lidos pelos dois jobs que rodam o
  toolchain; nenhum job ou passo redefine essas chaves. No job `publish`, o `actions/setup-node` segue
  no MESMO SHA (`48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e`, a tag `v6.4.0`), agora com `node-version`
  da linha 24; o passo do npm instala `npm@${PUBLISH_NPM_VERSION}` (era o intervalo `^11.5.1`) e
  reprova o job se o `node --version` não estiver na linha `v24.` ou se o `npm --version` não for
  exatamente o pinado, antes de qualquer passo de empacotamento; o checkout passa a
  `persist-credentials: false` (o token do job não fica no `.git/config`; a única chamada git remota
  do job, o `git ls-remote origin` da conferência da tag, funciona anônima neste repositório público).
  Ficam iguais: o gatilho (`push` de tags `v*`), as permissões do workflow (`contents: read`,
  `id-token: write`), a exclusão de rc do `publish` (`if: !contains(github.ref, '-rc.')`), o
  `environment: production-npm`, a espera do `await-release-gate` e os passos de publicação, inclusive
  o ponto onde o patch dormente de rollback reintroduz o `NODE_AUTH_TOKEN`.
- Mesmo arquivo, prova na rc (W4.3): um job novo, `rc-toolchain-proof`, com `if: contains(github.ref,
  '-rc.')`, `permissions: contents: read` (só isso: sem `id-token`, o que impede emitir credencial de
  registry), sem `environment`, sem `needs`, sem referência a `secrets.` e sem passo que escreva no
  registry. Roda 12 passos: 10 cópias byte a byte dos passos do `publish` (checkout, setup-node, o passo
  do npm, as conferências de versão do `package.json` e de zero dependências, o staging do bundle, a
  checagem de sintaxe do shim, a presença e o trailer do `install.sh` e o gate do packlist) e 2
  próprios — a conferência do VERSION contra a base da tag rc (tira o `-rc.N`, como o `release.yml`;
  tag sem `-rc.N` reprova) e um `npm pack --dry-run` (nenhum `.tgz` é escrito). Não espera o
  `await-release-gate`.
- Mesmo arquivo, comentários: o cabeçalho (`:4-5` antes) passa a descrever o publish em tag GA com npm
  exato em Node 24; a nota do PLAN-013 no cabeçalho e o comentário da exclusão de rc do `publish` passam
  a dizer que as tags rc rodam o `rc-toolchain-proof`; o comentário do passo do npm deixa de dizer que
  as tags rc pulam o workflow inteiro («RC tags skip this workflow entirely», que o job novo tornou
  falso) e passa a dizer que a rc é o ponto de prova anterior do toolchain; o comentário do
  `setup-node` passa a citar a tag certa do SHA (`v6.4.0`, não `v4.1.0`).
- `.claude/governance/npm-trusted-publisher.txt` (W4.2): só um parágrafo de comentário — a configuração
  no npmjs.com por trás da tripla precisa permitir publicação DIRETA (`npm publish`); uma configuração
  criada depois de 2026-09-03 só permite `npm stage publish`, e uma anterior exige escolher ao menos
  uma ação permitida; recriá-la ou editá-la sem marcar a publicação direta quebra o publish do GA, e
  nenhuma rc pega isso. A tripla (`repository`, `workflow`, `environment`) não muda, e a configuração no
  npmjs.com não é tocada.
- Livres, no mesmo commit: `.claude/scripts/tests/test_release_workflow_asserts.py` ganha a classe
  `Plan194W4PublishToolchainTest` (17 testes, duas lanes: texto, e estrutura por PyYAML — esta pula sem
  PyYAML), que pina o `env` único, Node 24, o npm exato, as cópias byte a byte, as permissões e a
  condição do job da rc e o checkout sem credencial, com controles que reprovam mutantes;
  `docs/actions-versions.md` corrige a linha do `setup-node` (o pin real é `v6.4.0`/`48b55a01`, em Node
  24) e registra que o bump para Node 24 do Sprint 6 nunca landou (feito por esta W4);
  `npm/INTEGRITY.md` (`:125` antes) passa a Node 24.x + o npm exato do workflow.

## Residual declarado (pela forma)

- A troca OIDC e a escrita no registry só são exercidas no GA (OQ-5): a rc prova o toolchain (Node da
  linha 24, npm exato, staging, packlist, `npm pack --dry-run`), não a publicação. A rede é o playbook
  `.claude/plans/PLAN-158/oidc-failure-playbook.md` e o patch dormente de rollback.
- O Node é a LINHA 24, não um build: o `setup-node` resolve uma 24.x na hora do run (cache do runner
  primeiro, senão o manifesto), e o passo confere só o prefixo `v24.`. O npm é exato por VERSÃO, baixado
  do registry na hora do run, sem hash pinado no repositório.
- `SPEC/v1/npm-shim.md:61` segue dizendo que o npm é `>=11.5.1` atualizado no job porque o Node 20 traz
  npm 10.x: fica desatualizado por contrato — o `SPEC/v1` não é deste pacote.
- Afirmações vizinhas falsas fora do escopo: `docs/BRANCH-PROTECTION.md:447-457` repete o bump para Node
  24 que a W4 corrigiu em `docs/actions-versions.md` (e as linhas vizinhas sobre o `upload-artifact` e o
  `setup-node`). Vão para um pacote LIVRE depois do LAND.
- Lacunas do teste novo, todas P3 na rodada 1 e no pacote livre de depois do LAND: mutantes que ficam
  verdes — remover as conferências de versão do passo do npm, um `npm pack` sem `--dry-run` no passo
  próprio da rc, apagar o `id-token: write` do workflow e acrescentar `workflow_dispatch` ao `on:`
  (estes dois, pré-existentes); a lane de texto não exige o bloco `permissions:` da rc (só a lane YAML
  o pega); o teste antigo da exclusão de rc casa o texto também no comentário do cabeçalho.
- `contains()` do GitHub não distingue maiúsculas: uma tag `-RC.` cai no job da rc, onde o corte
  `-rc.[0-9]*` distingue e reprova (como no `release.yml`); não abre caminho de publish.
- O controle vermelho→verde do PLAN-194 em CI (o job da rc.1 da 1.4.3 com Node 24 e npm exato, contra o
  log do 1.4.2) só existe depois do LAND, na rc.1; o controle desta cerimônia é a classe de teste.
- Com a base vermelha no `validate-governance`, um detalhe que traga o caminho absoluto da árvore
  difere entre a árvore viva e o worktree da base e reprova por ruído (falha FECHADA): a comparação não
  normaliza caminhos.

## Bateria e revisão

- O SIGN confere, antes de aplicar, que o patch só MODIFICA conteúdo de arquivo existente (cria, remove,
  renomeia, copia ou muda modo ⇒ recusa nomeada), que cada cópia staged (`w4/staged-w4/<caminho>`) tem
  o blob da pós-imagem que o patch declara para o seu arquivo canônico, e que os caminhos canônicos que o
  patch toca, pelo oráculo `--is-canonical`, são exatamente os dois declarados.
- Patch dormente de rollback (`.claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch`): NÃO
  é rastreado (`.gitignore`, `staged/`) e vive só no checkout vivo. O SIGN o lê pelo caminho absoluto
  resolvido da raiz do repositório em que roda, exige arquivo regular com 537 bytes e sha256
  `e68a508c86ebe2ac6c2eac444530934e4aa91fe05186f98b6a490d391a845b6a` (ausente ou diferente ⇒ recusa
  nomeada) e exige `git apply --check` verde no HEAD e, de novo, com o patch.
- Controle vermelho→verde: a classe `Plan194W4PublishToolchainTest`, rodada pelo id do nó. No P0, num
  worktree destacado do HEAD que recebe só a parte livre do patch (os dois canônicos ficam os do HEAD:
  Node "20", npm `^11.5.1`), ela tem de sair rc 1 com exatamente 17 falhas e nada mais (nem passed, nem
  skipped, nem error); na bateria, com o patch, rc 0 com exatamente 17 passed e nada mais. PyYAML é
  pré-condição do P0 (sem ele a lane estrutural pula). Medido em 2026-10-09: 17 failed na base, 17
  passed com o patch (`w4/red-control.txt`).
- Aplica o patch e confere que o blob de cada caminho tocado é o `index` pós-imagem do patch — depois
  de aplicar, de novo depois da bateria e, no índice, depois de stagear, junto do estado (cada caminho
  do patch e o sentinel como modificação, a `.asc` como arquivo novo, sem detecção de rename) e do modo,
  que segue o do HEAD e é 100644 para tudo o que entra. A árvore desse índice conferido é gravada (`git
  write-tree`) logo antes do commit; depois dele, a árvore commitada (`HEAD^{tree}`) tem de ser ela e o
  pai, o Anchor-SHA; se um hook mudou o commit, ele é desfeito com `reset --soft` para o Anchor-SHA e o
  SIGN aborta.
- Bateria: `py_compile` dos 4 arquivos de teste; passadas DURAS, que reprovam o SIGN em qualquer rc ≠ 0
  com o patch, sem julgamento de pré-existente — o controle acima; `python3 -m pytest` sobre
  `test_release_workflow_asserts.py`, `test_install_sh_self_sha.py`, `test_await_release_gate.py` e
  `test_release_bump_sites.py` (os que leem o `npm-publish.yml`; 274 passed em 2026-10-09); `actionlint
  .github/workflows/npm-publish.yml`, depois de uma sonda que prova que a regra shellcheck do actionlint
  executa; e o `git apply --check` do patch dormente. Depois, o actionlint nas duas formas do CI (a do
  job validate e a do `actionlint.yml`) sobre todos os workflows e o `validate-governance`, julgados
  pelo conjunto de achados com e sem o patch (o do `validate-governance` pela saída inteira —
  cabeçalho, detalhe de cada violação e contagem, fora as linhas de aviso, reconhecidas pelo prefixo com
  que o próprio script as emite e nunca por substring, e fora a linha `Repo:`, com espaços normalizados;
  uma execução sem o resumo `Errors:` reprova); os demais gates de corpus; e as suítes do `pytest.ini`
  (os `testpaths`) com a divisão de marcadores do CI (`-n auto -m 'not serial'` e `-m serial`). Nas
  suítes, uma falha é rerrodada ISOLADA com o patch, até 3 vezes; passar em alguma é nota (instável). Se
  falhar nas 3, é rerrodada uma vez num worktree destacado do HEAD (a árvore sem o patch): se lá ela
  também falha (rc 1 do pytest), é nota (pré-existente) e não bloqueia; qualquer outro resultado sem o
  patch reprova o SIGN. Um gate de corpus (fora os julgados pelo conjunto de achados) que reprova com o
  patch é rodado de novo nesse worktree: se também reprova lá, é nota; se passa, reprova o SIGN. O HEAD
  não pode mudar entre as pré-condições e o commit: o Anchor-SHA é o pai do commit.
- O texto que se assina é o deste arquivo no HEAD, com os quatro campos preenchidos: o SIGN recusa se o
  arquivo vivo mudar durante a bateria, e depois do stage confere que o blob do índice é o assinado e
  reverifica a assinatura sobre o conteúdo do índice.
- A assinatura é feita com `--local-user` pela chave secreta cuja impressão digital está em
  `.claude/sentinel-signers.txt` e precisa verificar contra esse allowlist (GOODSIG e VALIDSIG); o
  allowlist e a biblioteca de verificação são as do HEAD, lidas no P0; senão o SIGN desfaz o que
  aplicou.
- Rail: Codex (`codex exec --sandbox read-only`) e dois refutadores Claude na MESMA rodada; registros
  `.claude/plans/PLAN-194/w4/rail-round-N.md`. Regra de parada pré-registrada: no máximo 3 rodadas. A
  rodada 1 teve por sujeito o patch (`git diff a953a08204d4..4672153e8ed9`, patch-id `e869026b17c3…`):
  Codex «NENHUM ACHADO» e GO; os dois refutadores, GO só com P3. Este texto e os scripts da cerimônia
  foram escritos depois da rodada 1: ela não os revisou. O SIGN exige que o registro da última rodada
  nomeie o sha256 deste patch e o sha256 deste texto no HEAD (com os quatro campos por preencher) — o
  que impede editar este texto sem um registro novo —, que a linha Rail-Reviewer-Verdict seja a última
  linha `VERDICT:` da saída verbatim do revisor — lida pela gramática estrita do registro: exatamente uma
  seção `## Saída do revisor` e, nela, exatamente um bloco que abre numa linha igual a três crases
  seguidas de `text` e fecha na próxima linha igual a três crases, lido inteiro (um título dentro dele
  não encerra a seção; uma linha de cerca a mais, inclusive indentada, é recusada); seção ou cerca
  ausente, duplicada, mal formada ou não fechada é recusada com o motivo nomeado —, e veredito
  `APPROVE` (revisor `GO`) ou `DECLARED-P2` (revisor `GO` ou `GO-WITH-CONDITIONS`); vincula esse
  registro por hash (Rail-Record-sha256) a esta assinatura. O rail não revisa o script do SIGN; o ensaio
  dele é o harness `w4/test-ceremony-w4.sh` (chave GPG descartável, clone descartável).

## Scope

- `.claude/governance/npm-trusted-publisher.txt`
- `.claude/scripts/tests/test_release_workflow_asserts.py`
- `.github/workflows/npm-publish.yml`
- `docs/actions-versions.md`
- `npm/INTEGRITY.md`
