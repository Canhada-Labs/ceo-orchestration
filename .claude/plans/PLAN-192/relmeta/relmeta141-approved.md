# relmeta141-approved — sentinel da relmeta da v1.4.1 (o `release.sh` passa a mirar a v1.4.1)

Plan: PLAN-192
Wave: W2 — relmeta-141
Anchor-SHA: 7d807f4ccaa43b8d046f06eea97a0a14685d03d5
Patch-SHA256: edba3bb889ffd2c7ffde2c56c5ce474581e829a55b8f2b06db9992dfe7766dae
Data: 2026-09-18

## Ratificação (Owner, 2026-09-18)

Mandato verbatim, registrado no fim da S355: «o próximo terminal finaliza o que entra na 1.4.1, assina,
publica, e atualiza os repos que uso o framework pra seguirmos trabalhando. essa é a urgência máxima
agora. inclui o que dá pra fazer rápido e bora.»

Decisão desta sessão sobre o que o texto da release tem de dizer (PLAN-192 OQ-1), opção escolhida,
verbatim: «Declarar e seguir (Recomendado)» — «Corto a 1.4.1 pequena agora. O material assinado da 1.4.1
e o CHANGELOG dizem, com todas as letras, que o anexo da 1.4.0 continua aberto e passa para a 1.4.2, e
por quê (patch urgente fora de ordem). Honesto e rápido; o revisor julga isso como condição declarada,
não como promessa quebrada.»

## Scope

- `.claude/scripts/local/release.sh` — só o bloco POR-RELEASE: `TARGET_BASE` 1.4.0 → 1.4.1, `RELEASE_TITLE`,
  `RELEASE_SCOPE` e `RELEASE_HEADLINE`. Nenhuma linha de lógica muda.
- `.claude/governance/gate-scripts-manifest.txt` — o sha256 do `release.sh` (canônico; o driver é membro
  do manifesto ADR-192, e os workflows conferem o manifesto com `shasum -a 256 -c`).
- `.claude/scripts/tests/test_release_bump_sites.py` — o re-pin CONSCIENTE de
  `test_tag_annotation_carries_the_whole_train_and_no_stale_release`: o escopo novo vira a asserção
  positiva e o trem da v1.4.0 vira asserção NEGATIVA. Arquivo livre; viaja aqui porque driver e teste só
  são verdadeiros juntos.

Nada além desses três arquivos, deste sentinel e da sua assinatura entra no commit da cerimônia (o
script confere o índice contra o escopo EXATO, nos dois sentidos).

## O que você assina, e como confere

O conteúdo é o patch `RELMETA141.patch`, cujo sha256 está pinado acima. O script de cerimônia, antes de
pedir a assinatura:

1. re-deriva o patch do HEAD num clone descartável, com o `apply-relmeta141-edits.py` do próprio HEAD, e
   exige igualdade BYTE A BYTE com o patch commitado — um land posterior aos materiais que mude o trem
   (um plano novo citado num assunto de commit) ou a pré-imagem de um dos três arquivos aborta aqui;
2. confere que o sha256 do patch é o pinado neste sentinel;
3. imprime o bloco POR-RELEASE inteiro — é esse texto que vai para DENTRO da anotação ASSINADA da tag
   (`release.sh tag` monta a mensagem a partir dele) — e espera o seu Enter.

O escopo do trem (`RELEASE_SCOPE`) não é digitado: sai de `git log v1.4.0..HEAD` (planos citados nos
assuntos de commit) e de `git diff --name-only v1.4.0..HEAD -- .claude/adr/` (ADRs tocados; nesta
faixa, nenhum — escrito como «nenhum», nunca omitido).

## O que o texto da tag afirma, e onde cada afirmação se confere

- «todo lançamento passa a ser registrado ANTES do despacho … uma retomada sobre args DIFERENTES … é
  recusada» — `check_workflow_launch.py` + `_lib/launch_ledger.py`, assinados em `075beed9`
  (`PLAN-190/w1/w1-approved.md`); a suíte é `test_check_workflow_launch.py`.
- «o guard pode BLOQUEAR e o perfil user o mantém» — a registração está em
  `templates/settings/settings.user.json`; as três saídas nomeadas são as do CHANGELOG `[1.4.1]`.
- «relaunch --out … o arquivo inteiro ou nenhum arquivo» — PLAN-190 W1.1, com prova por mutação.
- «cinco CLIs … sem hook que as imponha» — `approval_gate.py`, `test_refs.py`, `mutant_sandbox.py`,
  `worktree_lock.py`, `phase_checkpoint.py`.
- «o envelope assinado da v1.4.0 prometia curar NESTA versão … NÃO os cura … v1.4.2» — a promessa está
  nas `conditions:` de `.claude/governance/pair-rail-verdict-v1.4.0.md`; a decisão é a OQ-1 acima.

## Verificado pela cerimônia depois de aplicar

`shasum -a 256 -c` do manifesto (o mesmo comando do CI); `bash -n` do driver; `release.sh --help`
anunciando 1.4.1; a suíte do driver inteira (`test_release_bump_sites.py`); validate-governance com 0
erros, contamination, verify-counts, ceremony-lint e check-claude-md-claims. Qualquer um reprovando
restaura a árvore (`git checkout` dos três alvos e do sentinel; a assinatura parcial é removida).

Medido antes, em clone descartável (2026-09-18): este driver nunca tinha cortado uma versão de PATCH;
com `TARGET_BASE="1.4.1"` o `bump` toca 12 arquivos e 13 linhas, deixa as janelas de suporte
(`v1.4.x` / `v1.3.x`) intactas, e a suíte do driver passa 153/153.

## Consequência DECLARADA

A partir deste commit o `release.sh` mira a v1.4.1: `preflight` exige a entrada `## [1.4.1]` do
CHANGELOG (já landada) e a tag `v1.4.1-rc.1` livre; o `bump` seguinte move os sítios de versão. Não há
caminho de volta para cortar outra 1.4.0 com este driver — o que é o comportamento desejado.

## Residual

1. A prosa do título e da headline não tem oráculo mecânico: nenhum teste prova que um texto descreve um
   diff. As âncoras da seção acima são o que existe; a leitura antes do Enter é sua.
2. O probe de assinatura do `preflight` (que já respondeu «cannot sign» com a chave funcionando) e o gate
   de latência de hooks com chave relativa seguem como estavam: nenhum dos dois é tocado aqui.
