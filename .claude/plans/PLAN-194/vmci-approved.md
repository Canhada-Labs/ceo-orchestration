# vmci-approved — ratificação pós-fato do PLAN-194 VM-CI (os bytes de `validate.yml` e `coverage.yml` que os merges dos PRs #2 e #3 puseram no `main`)

> Assinatura, 1 pinentry, a partir da raiz do repositório com este arquivo no estado do commit que o traz:
> `gpg --local-user <a impressão digital de .claude/sentinel-signers.txt> --detach-sign --armor
> .claude/plans/PLAN-194/vmci-approved.md` (gera `vmci-approved.md.asc` ao lado).
> Conferência contra o allowlist (GOODSIG e VALIDSIG ligados, impressão digital no allowlist):
> `python3 -I -c 'import sys; sys.path.insert(0, ".claude/hooks"); from pathlib import Path; from
> _lib.gpg_verify import verify_detached; print(verify_detached(Path(sys.argv[1]), Path(sys.argv[1] +
> ".asc"), allowlist_path=Path(".claude/sentinel-signers.txt")))' .claude/plans/PLAN-194/vmci-approved.md`
> tem de imprimir `(True, '<impressão digital>', '')` (o mesmo comando dá `True` sobre o `w3b1-approved.md`
> assinado e `False` com a `.asc` de outro arquivo — medido em 2026-10-11). O commit do sentinel com a
> `.asc` é livre (oráculo `--is-canonical` = 0 para os dois). Push é decisão sua.
> Antes de assinar: `git fetch origin && git diff --stat e21196817b299fe0557ae9c8dcf9e73b9dd4c10c origin/main
> -- .github/` tem de sair VAZIO (os 2 workflows no `main` ainda são os ratificados); se sair qualquer
> linha, não assine — os bytes mudaram depois do Anchor.

Plan: PLAN-194
Wave: VM-CI — ratificação pós-fato dos merges dos PRs #2 e #3 (`runs-on` condicional para os runners da VM; recuo no `ubuntu-latest`)
Anchor-SHA: e21196817b299fe0557ae9c8dcf9e73b9dd4c10c
Base-SHA: bc803a7ac0a00e679bc4c40b9a92f19a7d364314
File-sha256: .github/workflows/validate.yml 412a51d9d92d7a7948ea6c920184770386b6214452332fbe6a56642d9cc45f72
File-sha256: .github/workflows/coverage.yml bfb751b9d17c9daf087044261438112bd0fbb75c5f43c4b77a3dd6540dfd1f2f
Record: .claude/plans/PLAN-194/vmci/vmci.patch
Record-sha256: e6f5d1f9ecd7586567212d110f200bd4310bcc147f8dfdb7848a8b141f10a37a
Review: .claude/plans/PLAN-194/vmci/REVIEW-pr2.md
Review-sha256: fa6070077788a743d4e627456de9383ce1fe86f240246b5b4ef4f263d406991c
Control: .claude/plans/PLAN-194/vmci/red-control.txt
Control-sha256: 575cf8d6437ad5e9bbb6accba6e11009c7ae9d49470338122760ad24a7c46bf8
Data: a da assinatura, registrada na `.asc`

## O que esta assinatura ratifica, e nada além

- Os bytes exatos dos 2 arquivos no Anchor-SHA, pelos sha256 acima: `.github/workflows/validate.yml`
  (96.546 bytes, blob `a1b8d1124bd6…`) e `.github/workflows/coverage.yml` (13.925 bytes, blob
  `4e4919be8063…`). Os 2 são canônicos (oráculo `--is-canonical` = 1, medido). Os mesmos bytes estão em
  `e0c5ffc23dc2` e em `d8d13aafe348`, o `main` às 02:28Z de 2026-10-11 (os 9 commits entre o Anchor e ele
  não tocam `.github/`, medido); foram os que rodaram na 4.ª corrida na VM (push `d8d13aaf`, run
  `38104634181`, 9 de 9 jobs verdes na tentativa 1).
- O que esses bytes fazem: os 8 jobs dos 2 arquivos (`validate`, `integration-tests`,
  `formal-verification-mutation-harness`, `opus-4-7-profiler-smoke`, `hook-tests-dual-rail`,
  `hook-tests-python-matrix`, `hook-stdout-schema-oracle` e `coverage`) têm `runs-on` por expressão:
  rótulos `["self-hosted","Linux","X64","canhada-ci"]` quando `vars.VM_CI_ENABLED == '1'` E `github.ref ==
  'refs/heads/main'` E o evento é `push`, `schedule` ou `workflow_dispatch`; senão, `ubuntu-latest` — na
  matriz, `ubuntu-24.04` para a 3.9 e `ubuntu-26.04` para a 3.14, que nunca vai para a VM. Nenhum job dos 2
  arquivos usa mais o `Ceo`. Medido pelo avaliador do `REVIEW-pr2.md` (Apêndice B): fora da VM, o
  `runs-on` é o do Base-SHA com `Ceo` trocado por `ubuntu-latest`, e nada mais, nas 3.240 células avaliadas
  (10.800 avaliações, com repetição); o YAML é igual ao do Base-SHA em todas as outras chaves.
- O registro do que entrou é o `Record`: `git diff --full-index bc803a7a e2119681 -- .github/workflows/`,
  só os 2 arquivos, +55 −9; o diff de `bc803a7a` a `e2119681` na árvore inteira não muda mais nada.
- A assinatura não ratifica commits depois do Anchor-SHA: qualquer mudança posterior nesses 2 arquivos —
  inclusive tirar o espaço no fim das 24 linhas que o têm, ou corrigir os comentários que ficaram falsos —
  é mudança canônica nova.

## Como os bytes entraram (pela forma)

- Entraram no `main` por 2 merges de PR no GitHub, feitos pela conta do Owner em 2026-10-11 (PR #2 às
  00:37:04Z, `d7309efa`, do ramo `codex/vm-ci-main-routing-20261009`, cabeça `29e9e2a2`; PR #3 às
  01:44:41Z, `e2119681`, do ramo `codex/free-public-pr-runners-20261011`, cabeça `fc4bf83c`), sem sentinel
  assinado. Os 2 commits de cabeça foram escritos por outro agente — o app Codex (registro do CEO na S363 e
  nomes dos ramos); o git registra a conta do Owner como autora, e os dois estão SEM assinatura (`%G?` =
  `N`). A decisão anterior do Owner, de 2026-09-18, era manter o Codex fora da autoria neste repositório
  (segue revisor); qualquer decisão nova sobre isso é do Owner. O guard de edição canônica
  só vê o que um agente edita na sessão; um merge pelo GitHub não passa por ele, e o `main` não tem
  proteção de branch nem ruleset (medido pela API em 2026-10-11).
- Esta assinatura fecha a cadeia desses bytes depois do fato: liga o Anchor-SHA, os sha256 dos 2
  arquivos, o registro do diff, a revisão medida e os controles à chave do allowlist.
- A CLASSE — caminho canônico entrando no `main` por merge no GitHub sem cerimônia — segue aberta: ocorreu
  2 vezes em 68 minutos, e nada no repositório nem nas configurações medidas impede a repetição;
  fechá-la está fora desta assinatura.

## O que fica com o Owner, fora dos bytes assinados (pela forma)

- Tudo o que vive no GitHub ou na VM: o valor da variável `VM_CI_ENABLED` (vale `"1"` desde
  2026-10-11T00:37:01Z); a configuração do grupo de runners (workflows permitidos, permissão para
  repositório público, quais repositórios compartilham o grupo); os runners (quantos, se efêmeros, usuário
  Unix, `TMPDIR`, arquivo de ambiente, tool cache, sistema operacional, e se cada job roda num ambiente
  isolado e destruído depois — o registro efêmero `--ephemeral`/JIT sozinho não isola, `REVIEW-pr2.md` §6);
  a VM (credenciais, disco, uso por SSH); e a medição contínua. Esta assinatura ratifica bytes de YAML; ela não atesta que a VM cumpre as
  condições do `REVIEW-pr2.md` §8, e nenhuma delas está medida como cumprida.

## Resíduos declarados (pela forma)

- Das 4 corridas medidas na VM, as tentativas 1 das 3 primeiras falharam, por causas de natureza
  diferente: na 1.ª, por AMBIENTE — `/tmp` dividido entre runners (um teste que lista o `/tmp` inteiro viu a
  sobra de outro job); na 2.ª, a perna 3.9 por AMBIENTE — subprocessos de ambiente enxuto que, com o
  Python do tool cache de um runner novo, não acham a `libpython3.9.so.1.0` (comprovado pela mensagem); na
  2.ª e na 3.ª, 4 testes da perna 3.12 com subprocesso morto por sinal 11, de causa NÃO diagnosticada. A
  4.ª corrida (push `d8d13aaf`) ficou verde na tentativa 1, com a 3.9 verde no mesmo runner onde caíra por
  `libpython` — essa classe também não é fixa de um runner (ou foi curada na VM no intervalo; não se sabe
  qual). As tentativas 2 da 1.ª e da 2.ª corridas ficaram verdes (na 2.ª, a 3.12 passou no mesmo runner
  onde falhara); a tentativa 3 da 2.ª caiu em outro teste da 3.12 (`shutil.Error`, não diagnosticado). Com a variável ligada,
  todo `push`/`schedule` do `main` roda na VM com essas classes abertas; as curas de infraestrutura
  diagnosticadas (`TMPDIR` por runner ou ambiente descartável por job; tool cache no caminho de build, por
  runner isolado) ficam com o Owner, e os caminhos fixos em `/tmp` do próprio `validate.yml` são canônicos
  (pacote próprio).
- O recuo é o `ubuntu-latest` de 4 vCPU, em todo `pull_request` e em `push`/`schedule` com a variável
  desligada: medido nele, o `coverage` levou 1925 s contra o teto de 35 min (92 %); a matriz, 824 s na
  perna mais lenta contra 25 min (55 %). Mudar teto ou runner é canônico.
- Os comentários `validate.yml:1646` («3.10-3.12 seguem no `Ceo`») e `:1656` («`Ceo` (8 nucleos) segue
  25») ficaram falsos nestes bytes.
- A barreira contra código de fork é o grupo de runners (restrito a `@refs/heads/main`), não a expressão:
  a comparação de strings do GitHub ignora caixa (`refs/heads/MAIN` também roteia), e um gatilho que
  executa o arquivo do `main` com dados de fork (`pull_request_target`, `workflow_run`) seria aceito pelo
  grupo. Nenhum dos 2 arquivos tem esses gatilhos.
- Sem recuo automático: com a variável `"1"` e os runners ocupados ou fora do ar, o job fica na fila.
- O `actionlint` não confere rótulo dentro de expressão: os 8 jobs perderam a checagem `[runner-label]`.
- O teto absoluto do gate de latência dos hooks foi calibrado no runner hospedado; na VM fica mais frouxo
  sem contenção e reprova por infraestrutura com contenção.
- A perna 3.9 depende de a VM ser Ubuntu ≤ 24.04 (ou ter a 3.9 posta à mão no tool cache).
- Num runner persistente, o `site-packages` do Python do tool cache, o `/tmp` e o `$HOME` passam de um
  job para o seguinte, inclusive de outro repositório do grupo.
- Nenhum teste do repositório pina esta expressão; o controle semântico é o avaliador (R5 do
  `red-control.txt`).
- Este sentinel não é destrava de edição, por 3 fatos medidos sobre estes bytes (R6): o nome não casa
  nenhum padrão de descoberta do `check_canonical_edit.py` nem do `ceo-boot.py`; o texto não tem linha
  `Approved-By:` que o guard aceite; e o parser de Scope do guard devolve conjunto vazio para ele. Assinado,
  ele não libera agente nenhum para editar os 2 workflows.

## Revisão

- `REVIEW-pr2.md` (sha256 no cabeçalho): revisão medida — tabela-verdade avaliada, dependências por job,
  gates sensíveis ao runner, as 4 corridas na VM (e as tentativas seguintes) contra o hospedado, fila com 2 e com
  4 runners, a fotografia do grupo de runners com horário, o risco do
  recuo no `ubuntu-latest`, segurança de repositório público, runner persistente, condições para manter a
  variável ligada.
- `red-control.txt` (sha256 no cabeçalho): os controles R0–R7 com o resultado medido.
- Rodada 1 do rail sobre `3fbd13c6` (Codex NO-GO; refutador Claude GO-WITH-CONDITIONS); rodada 2 sobre
  `a6f11663` (Codex e refutador Claude GO-WITH-CONDITIONS); curas nesta versão. As rodadas seguintes
  revisam ESTES bytes, e os registros delas vivem fora deste arquivo.

## Scope

- `.github/workflows/coverage.yml`
- `.github/workflows/validate.yml`
