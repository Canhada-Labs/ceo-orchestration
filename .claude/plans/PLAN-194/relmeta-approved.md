# relmeta-approved — sentinel do RM da v1.4.3 (relmeta-143): o `release.sh` passa a mirar a v1.4.3 (canônico `.claude/governance/gate-scripts-manifest.txt`)

Plan: PLAN-194
Wave: RM — relmeta-143 (o bloco por release do driver, o re-pin do manifesto ADR-192 e o re-pin do teste que fixa o escopo da anotação da tag)
Dados: .claude/plans/PLAN-194/relmeta/sign.tsv
Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
Patch: .claude/plans/PLAN-194/relmeta/relmeta.patch
Control: .claude/plans/PLAN-194/relmeta/red-control.txt
Derivator-SHA256: f0a69df4b94395c7805f4a28c9bacfe22b29ca07e362ba6f872dbb4ce115a0a9
Hard-SHA256: 1777724f34602fcc760a92222a99d5e92743190d85f059553026b62772b2cc30
Derived-From: 6b9904b13f9c6c66f876c60bc25a79e708ff15ce
Scope-Derived: PLAN-169 / PLAN-170 / PLAN-171 / PLAN-175 / PLAN-176 / PLAN-181 / PLAN-183 / PLAN-186 / PLAN-190 / PLAN-191 / PLAN-192 / PLAN-193 / PLAN-194 / PLAN-195 (ADRs tocados: nenhum)
Patch-sha256: 02b7fd110d0d84cbcf3b78cf22cd7574b74daba4ed7593e00f8aacc76f52816b
Rail-Record-sha256: 7f4b3b845221ecb9bd4273f5e58050d2b5aad64bcec6bc0ec9e90932ece03885
Anchor-SHA: df1132323ec2dcd1d884ec2b0c6180aa0964d460
Data: 2026-10-16

## Ratificação (Owner)

- Ao assinar este texto, o Owner aprova o `relmeta.patch` (sha256 em `Patch-sha256`) sobre o `Anchor-SHA`,
  aplicado e conferido pelo molde citado em `Molde:` com os dados citados em `Dados:`.
- O RM é o primeiro passo do corte da 1.4.3 no PLAN-194 (`PLAN-194-maintenance-train-v1-4-3.md`, seção
  «Next»: RM → kit → rc.1 → hold de 24 h → GA), DEPOIS de todo land que cite plano, porque o escopo da tag
  sai de `git log v1.4.2..HEAD`.
- Molde: a troca do SIGN próprio de cada pacote pelo molde «SIGN mínimo» é decisão do Owner (S363). A tabela
  de scripts do roteiro da 1.4.3 (fora do repositório) nomeava um SIGN próprio deste pacote; esta cerimônia
  usa a entrada compartilhada citada em `Molde:`, e aquela linha da tabela passou a citá-la.
- Ao assinar este texto, o Owner ratifica para este pacote as duas decisões do CEO sobre o molde que os
  pacotes do lote de 2026-10-15 ratificaram: o controle vermelho fica FORA do SIGN, como registro do
  construtor que o rail reproduz (seção «Controle vermelho (registro)»), e a rodada de rail do patch, deste
  texto e dos dados é única, com no máximo uma conferência de anexo.
- Congelamento: da derivação destes materiais até a publicação do commit deste SIGN no `main` do origin,
  nenhum commit fora dos materiais do pacote (este texto e `.claude/plans/PLAN-194/relmeta/`) entra no
  `main`, e o app do Codex não mergeia neste repositório. A linha `--verify` dos dados recusa, antes da
  assinatura, qualquer commit entre a linha `Derived-From` e o HEAD que toque caminho fora do pacote,
  inclusive trazido por merge, e qualquer commit que não seja merge e não toque caminho nenhum (seção
  «Comandos próprios do pacote»).

## O que esta cerimônia entrega, e nada além

- Tamanho: 3 caminhos, 1 canônico (`.claude/governance/gate-scripts-manifest.txt`, pelo oráculo
  `--is-canonical`; o `release.sh` e o teste dão 0 nele), nenhum caminho do kernel, 3 edições. O patch é
  DERIVADO por `derive-relmeta143.sh` (que roda o derivador num clone descartável e grava o `git diff` de
  formato fixo); nenhuma linha dele foi escrita à mão.
- `.claude/scripts/local/release.sh` (100755, o modo não muda): o bloco PER-RELEASE inteiro, entre a linha
  `TARGET_BASE="1.4.2"` e a linha `RC_NUM="1"`, é trocado pelo bloco derivado: `TARGET_BASE="1.4.3"`, o
  `RELEASE_TITLE`, o comentário que nomeia o derivador e a faixa, o `RELEASE_SCOPE` derivado e o
  `RELEASE_HEADLINE`. Nada mais do driver muda.
- `.claude/governance/gate-scripts-manifest.txt`: só a linha do `release.sh`, com o sha256 do driver depois
  da edição.
- `.claude/scripts/tests/test_release_bump_sites.py`:
  `test_tag_annotation_carries_the_whole_train_and_no_stale_release` passa a exigir o escopo novo na
  anotação; o escopo da 1.4.2 (`PLAN-190 / PLAN-193`) vira asserção negativa, ao lado das negativas que já
  estavam lá; o docstring ganha o parágrafo do trem 1.4.3.
- O `CHANGELOG.md` NÃO é escrito: é pré-condição. A seção `[1.4.3]` é única e datada, não há seção
  `[Unreleased]`, as contagens do preâmbulo são as vivas (`verify-counts.sh`, que tem de sair rc 0 com os
  campos `violations` e `live` presentes e dos tipos certos), e a re-declaração do anexo da v1.4.0 está num
  Known-open, com um item próprio, que não cita, entre colchetes, a entrada de outra release, dizendo que
  nenhuma release está atribuída à cura. Nem esse Known-open nem a seção inteira nomeia versão de três
  números (`x.y.z`) posterior à 1.4.3, em qualquer major e com ou sem o prefixo `v`, salvo as versões de
  ferramentas externas declaradas uma a uma no derivador (`EXTERNAL_VERSIONS`: Claude Code 2.1.280,
  2.1.284, 2.1.285, 2.1.293 e 2.1.295; npm 11.5.1 e 11.20.0); versões de dois números ficam fora do
  mecanismo.
- O `CHANGELOG.md` desta derivação é o do commit `6b9904b1`, que afirma o verde do gate do harness só para a
  cerimônia padrão (`maintainer`) e deixa a instalação `--ceremony user` fora dessa afirmação.
- Consequência: daqui em diante o driver mira a v1.4.3 (`release.sh --help` anuncia
  `target base version: 1.4.3`), e o título, o escopo e a headline abaixo vão para a anotação ASSINADA da tag
  de cada corte da 1.4.3 (rc e GA).

## O texto que vai para a anotação da tag

A seção entre os marcadores é DERIVADA: o `derive-relmeta143.sh` a grava a partir das mesmas constantes que
geram o patch, e a linha `--verify` dos dados exige que ela seja, byte a byte, a re-derivada a partir do
`Anchor-SHA`. A forma é a do `msg` que o driver assina na fase `tag` (o `--verify` exige esse molde uma vez no
driver com o patch): `<tag>` é `v1.4.3-rc.N` no corte de uma rc e `v1.4.3` no GA, e `<commit do corte>` é o
HEAD do corte; o resto vai para a anotação como está aqui. O roteiro do Owner imprime esta seção, lida do
`Anchor-SHA`, antes de pedir o «SIM» que inicia a cerimônia; o SIGN não a imprime.

<!-- texto-da-tag: derivado -->
```text
<tag> — Maintenance release: harness-config gate cured for the default ceremony on upgrade and fresh install, condition 67 of v1.4.0-rc.1 retired, Codex CLI re-pin

Anchor: <commit do corte>
Scope:  PLAN-169 / PLAN-170 / PLAN-171 / PLAN-175 / PLAN-176 / PLAN-181 / PLAN-183 / PLAN-186 / PLAN-190 / PLAN-191 / PLAN-192 / PLAN-193 / PLAN-194 / PLAN-195 (ADRs tocados: nenhum)

Headline: Release de manutencao (PLAN-194). Os requisitos nao mudam desde a
v1.4.2: Claude Code v2.1.280 ou mais novo (install.sh e upgrade.sh
seguem recusando, com saida 6, um claude mais antigo no PATH, salvo
com --allow-old-claude-code), Python 3.9 ou mais novo e Node.js 20
ou mais novo para o shim do npm.

O gate de configuracao do harness do /ceo-boot reprovava nas
instalacoes: as fixtures do replay moravam num diretorio que a
instalacao nao recebe. Elas passam a morar em
.claude/hooks/_lib/harness_replay/. Na cerimonia padrao
(maintainer), o gate sai verde numa instalacao feita da v1.4.2 e
atualizada pelo upgrade.sh desta release e numa instalacao nova;
testes no CI provam os dois casos para uma forma de instalacao
(--profile core --ceremony maintainer), e a arvore de antes da cura
reproduz o vermelho. A instalacao com --ceremony user nao e coberta
por esta afirmacao (Known-open do CHANGELOG). O gate fica mais
estrito: as leituras de JSON dele recusam os tokens NaN e Infinity.

O gravador do agent_spawn passa a ler o elo anterior da cadeia,
calcular o HMAC, gravar a linha e atualizar o sidecar sob uma unica
trava do log. Isto aposenta a condicao 67 assinada da v1.4.0-rc.1:
a quebra de cadeia quando esse gravador lia o elo anterior antes de
pegar a trava. As quebras que a corrida ja gravou ficam nos logs, e
gravadores que resolvem travas diferentes para o mesmo log seguem
sem se excluir.

Uma instalacao nova com --ceremony user grava
permissions.defaultMode com o valor manual quando o settings.json
produzido por essa mesma execucao nao tem defaultMode, salvo com
CEO_INSTALL_SKIP_DENY_BASELINE=1. Um settings.json que ja existia
antes da instalacao nunca e tocado, e o upgrade.sh nao muda.

Numa instalacao que registrou a mao o hook do envelope de custo, um
bloqueio passa a ser gravado no log de auditoria; nenhuma release
anterior o gravava. Nenhum template de settings enviado registra
esse hook. Correcoes em audit-query.py, /status, /ceo-boot e
check-substrate-drift.py.

Pair-rail: o revisor e re-pinado no Codex CLI v0.160.0; o manifesto
do payload pina esse binario por sha256, para uma plataforma so.
Numa instalacao o pin resolve como infraestrutura e segue advisory,
como antes.

A parte honesta: este trem saiu para curar o spool de auditoria, e
essa cura nao entrou no corte; o spool deixa arquivos por processo
para tras, e a drenagem forcada dele pode passar do timeout de um
hook. Do anexo assinado da v1.4.0 esta release cura so a condicao
67; o resto segue aberto, sem release atribuida a cura, e o mesmo
vale para os tres achados P1 do anexo assinado da v1.4.2-rc.1. A
limpeza do Claude Code (cleanupPeriodDays, 30 dias por padrao)
ainda pode apagar o log de auditoria, e nenhum plano desta release
carrega uma cura estrutural; o backup deixa de fora o material de
chave, entre ele a chave HMAC e o sal. Quatro merges de pull
request trouxeram arquivos do framework ao main sem a cerimonia de
assinatura, e nada no repositorio impede a repeticao (medido em
2026-10-14). Os demais residuos estao no Known-open da entrada do
CHANGELOG.

No speed claim. See CHANGELOG.md [1.4.3].
```
<!-- fim do texto-da-tag -->

## Como ler o Scope da tag

- A linha `Scope` sai da regra que o G0 do corte exige (`assert_release_scope_covers_log`): todo `PLAN-NNN`
  citado num assunto de commit de `v1.4.2..HEAD`, mais os ADRs tocados na faixa (nenhum, nesta derivação).
- Por isso ela lista planos que esta release não entrega: PLAN-170 e PLAN-181 aparecem só em commits que os
  abandonam; PLAN-192 aparece só num commit de fechamento; PLAN-193 aparece em commits de fechamento e num
  commit de documentação posterior ao GA da v1.4.2 (`429a5b39`, a lista de adopters no `CLAUDE.md`). A linha
  diz quais planos os commits da faixa citam, não que cada um entregou algo na 1.4.3. O que a release entrega
  está na headline e na seção `[1.4.3]` do `CHANGELOG.md`.
- Filtrar a lista à mão faria o G0 do corte recusar a tag (ele exige o superconjunto).

## O que o texto afirma, e a âncora

Cada parágrafo da headline tem uma âncora no derivador (`CLAIMS`), com uma parte de CÓDIGO (arquivos, AST,
ancestralidade, sondas) e uma de TEXTO (frases da seção `[1.4.3]`, com o espaço em branco normalizado). As
âncoras rodam no `--claims-only` (manual: antes da derivação, antes da rc.1 e antes do GA) e na derivação;
NÃO rodam no SIGN.

| Parágrafo da headline | Âncora | O que a parte de código confere |
|---|---|---|
| requisitos inalterados | `ccfloor` | o bloco do piso do Claude Code rodado contra um `claude` falso no `install.sh` e no `upgrade.sh`, e byte a byte o da v1.4.2 nos dois; `SUPPORT.md` cita 2.1.280; `engines.node` `>=20` |
| gate do harness | `harness` | a constante da pasta e o marcador novos; a pasta nova só com os 3 `.json`; a antiga ausente; os grupos `harness-*` no teste histórico, que o `smoke-install.yml` roda; C9 (`7428d25b`) e o SIGN da W7a (`b0f5fd45`) ancestrais; o resíduo da cerimônia `user` preso ao código: as entradas do `DENY_BASELINE` do gate que faltam no deny que o `install.sh` grava para `user` (o template `user` sem bloco `permissions`) são EXATAMENTE as 4 que a `[1.4.3]` nomeia; e o gate no modo do CI, na raiz do repositório, verde |
| condição 67 | `cond67` | por AST, em `append_entry`, a leitura do elo (`read_prev_hmac`), a escrita da linha (uma chamada `.write`) e a atualização do sidecar (`write_last_hmac`) dentro de UM MESMO `with FileLock(paths["lock"], …)` (duas travas separadas reprovam); sentinel e `.asc` da cura presentes, SIGN `65cd50d7` ancestral; a condição 67 no envelope da v1.4.0-rc.1 |
| `defaultMode` no install user | `defaultmode` | `DEFAULT_MODE_BASELINE="manual"` (1 linha), as rotas `jq` e `python3` e o skip por ambiente no `install.sh`; o template `user` sem `permissions.defaultMode` (leitura JSON); o `upgrade.sh` com o mesmo blob da v1.4.2 |
| envelope de custo e correções | `cenv`, `fixes` | por AST, uma chamada `emit_generic("cost_envelope_capped", …)` com os 6 kwargs da allowlist e sem `action`; nenhum `templates/settings/*.json` registra o hook; SIGN do cenv ancestral; `status.py` sem `--as-json`, `check-substrate-drift.py` com `COMPONENT_CHECK_ERROR`, `ceo-boot.py` com `external_wait` e o teste novo da ordem dos flags do `audit-query.py` |
| pair-rail | `codex` | o manifesto pina 0.160.0 por sha256 só para `aarch64-apple-darwin`; o range do pin o admite; SIGN do re-pin (`4a1eec73`) ancestral |
| a parte honesta | `annex` | os envelopes da v1.4.0 e da v1.4.2-rc.1 presentes; o guia de recuperação (`docs/DISASTER-RECOVERY.md`) sem `audit-key` nem `.salt`, porque a seção `[1.4.3]` diz que ele não fala disso |

A tabela diz o que cada âncora de código confere; ela não é a lista do que fica sem âncora. Em todo parágrafo
há frases que só a parte de TEXTO ancora (a frase está na `[1.4.3]`), e elas são, pela forma: o que fica de
fora ou aberto (os resíduos declarados); requisitos que o instalador não confere; estados fora do
repositório (o GitHub, o CI de um commit futuro); o comportamento dentro de uma INSTALAÇÃO, que nenhuma
âncora roda (a prova de instalação do gate é a do CI, C9, e a do SIGN da W7a; a da gravação do `defaultMode`
é a linha `test-install-deny-baseline.sh` dos dados); e efeitos que a âncora vê só por um marcador de presença
(do `/ceo-boot`, por exemplo, ela vê a espera declarada, não a cura do vermelho falso de
`scheduled_workflows_red`).

## Controle vermelho (registro)

Medição do construtor, com data e substrato em `.claude/plans/PLAN-194/relmeta/red-control.txt`; o SIGN não a
executa, e o rail a reproduz.

- `--claims-only` na árvore da v1.4.2 (`b55084da`) com o `CHANGELOG.md` do HEAD sobreposto: a parte de
  TEXTO passa nas 8 âncoras (o CHANGELOG é o do HEAD), e a parte de CÓDIGO falha em 6, cada uma pelo motivo
  dela: `harness` (a constante ainda aponta a pasta antiga e a nova não existe), `cond67` (`read_prev_hmac`
  fora do `with FileLock`), `defaultmode` (`DEFAULT_MODE_BASELINE` ausente), `cenv` (o kwarg `action`),
  `fixes` (`--as-json` no `status.py`) e `codex` (`package_version` 0.156.1). Passam, por desenho, `ccfloor`
  (os requisitos não mudam: o código do piso é o mesmo) e `annex` (só presença de envelopes e um
  acoplamento com o guia de recuperação, verdes nas duas árvores).
- A âncora `cond67` contra um `append_entry` sintético que lê o elo sob uma trava e grava a linha e o sidecar
  sob outra: reprova (o mesmo `append_entry` com uma trava só passa).
- `--verify` sobre o Anchor dos materiais SEM o patch aplicado falha (o driver na árvore ainda mira a 1.4.2).

## Comandos próprios do pacote (as linhas `hard` dos dados, nesta ordem)

1. `bash -n .claude/scripts/local/release.sh`.
2. `bash .claude/plans/PLAN-194/relmeta/hard-relmeta.sh` (forma 2 do molde), que sai rc 0 só se, nesta ordem:
   o sha256 do derivador é o da linha `Derivator-SHA256` deste texto no HEAD e o do próprio envoltório é o da
   linha `Hard-SHA256`; `shasum -a 256 -c` do manifesto sai rc 0 com tantas linhas OK quantas linhas não
   vazias; exatamente uma linha do manifesto é a do `release.sh`, com o sha256 do arquivo; `TARGET_BASE="1.4.3"`
   aparece uma vez no driver e `TARGET_BASE="1.4.2"` nenhuma; `release.sh --help` sai rc 0 com a primeira
   linha `release.sh — operator release driver (target base version: 1.4.3)`; e o commit da v1.4.2
   (`b55084da`) é ancestral do HEAD. Só lê; o git roda com `GIT_OPTIONAL_LOCKS=0`.
3. `python3 .claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py --repo=. --verify`, que sai rc 0 só se:
   `b55084da` é ancestral do HEAD (e a tag `v1.4.2`, se o clone a tem, descasca nele); a linha
   `Derived-From` deste texto é ancestral do HEAD e é o último commit do HEAD que toca algo fora de
   `.claude/plans/PLAN-194/relmeta/` e deste texto; `git rev-list --full-history` de `Derived-From` até o HEAD,
   limitado aos caminhos fora do pacote, sai vazio (um commit fora do pacote, inclusive trazido por merge,
   recusa aqui, antes da assinatura); nenhum commit dessa faixa que não seja merge deixa de tocar caminho
   (um commit vazio recusa); o escopo re-derivado de
   `git log` sobre o HEAD é a linha `Scope-Derived`; a partir das pré-imagens `HEAD:<alvo>` dos 3 caminhos, o
   bloco, o manifesto e o teste re-derivados são, byte a byte, os da árvore com o patch; o driver monta a
   anotação pelo molde que a seção do texto da tag reproduz, e essa seção é, byte a byte, a re-derivada; e o
   `CHANGELOG.md` cumpre a pré-condição da seção «O que esta cerimônia entrega». Só plumbing do git
   (`log`, `rev-list`, `cat-file`, `rev-parse`, `merge-base`, `diff`, `diff-tree`), com
   `GIT_OPTIONAL_LOCKS=0`, mais o `verify-counts.sh --json --no-tests`, que tem de sair rc 0; as âncoras NÃO
   rodam aqui.
4. `bash scripts/tests/test-install-deny-baseline.sh`: o teste que prova que a instalação `user` grava o
   `defaultMode` quando ele falta e o preserva quando existe (o CI não o roda; medido em 7 min 17 s em
   2026-10-15, na máquina do construtor).
5. `python3 .claude/scripts/validate_governance_fast.py`.
6. `python3 -m pytest` sobre `.claude/scripts/tests/test_release_bump_sites.py`, com resumo só de aprovados.

## Rail

- O registro citado em `rail` nos dados traz a rodada ÚNICA do molde sobre o patch, este texto (com os quatro
  campos por preencher) e os dados: o Codex 0.160.0 em `exec --sandbox read-only` e dois refutadores Claude na
  MESMA rodada, com o derivador como terceira lane, e no máximo uma conferência de anexo. Pauta: cada frase da
  headline contra a seção `[1.4.3]` e o código; cada âncora prova a frase e é vermelha na v1.4.2; o `--verify`
  recusa escopo velho e land depois da derivação; o `Scope` deste texto são os caminhos do patch.
- O registro traz, além dos três sha256 e do `Rail-Verdict` que o SIGN confere, o sha256 do derivador, do
  `hard-relmeta.sh` e do `red-control.txt` revisados (o SIGN não os confere: o `hard-relmeta.sh` confere os
  dois primeiros contra as linhas deste texto).

## Conferências do SIGN anterior (relmeta-142) aposentadas, e o que fica no lugar

- A re-derivação dentro do SIGN e a recusa de um patch velho pelo nome: no lugar, a linha `--verify` dos
  dados (re-derivação a partir das pré-imagens do Anchor, comparação byte a byte com a árvore com o patch,
  `Derived-From` e `Scope-Derived`).
- A exibição do bloco no terminal com a palavra «assino»: no lugar, a seção do texto da tag deste texto,
  conferida pelo `--verify`, que o roteiro imprime antes do «SIM».
- A restauração da árvore em falha: aposentada; o molde não desfaz nada.
- O `--yes` do probe de assinatura do preflight e o controle dele: já estão no HEAD desde a relmeta-142
  (`36bbe90c`), e saíram do derivador.
- As âncoras na derivação feita dentro do SIGN: no lugar, o `--claims-only` manual antes da derivação, antes
  da rc.1 e antes do GA.
- A validade da chave no registro de signatários (`is_valid_signer` sobre
  `.claude/security/sentinel-signers-registry.yaml`: chave vencida ou revogada recusada na escolha e na
  verificação): aposentada sem substituto. O molde escolhe e verifica a chave só pelo allowlist
  `.claude/sentinel-signers.txt` do `Anchor-SHA`, e o portão do roteiro (`ceo-f2-e4.py`) também. Hoje sem
  efeito: a única chave do allowlist, `AE9B236F…0335DC74`, vale no registro até 2027-05-13 e não está
  revogada. O guard de edição canônica consulta o registro; o SIGN não.
- O `git remote -v` com o nome do repositório e o `git fetch` antes do SIGN: no lugar, o roteiro do Owner
  confere a URL do origin pela forma do arquivo de valores, a configuração do clone (`confere_config`) e o
  `main` do origin por `git ls-remote` contra o Anchor; o SIGN não faz `fetch`.
- A tag da base obrigatória (na relmeta-142, a `v1.4.1`; aqui, a `v1.4.2`): no `--verify` ela é opcional
  (o clone do roteiro pode não trazer tags); quando presente, tem de descascar no commit da v1.4.2.

## Resíduos declarados (pela forma)

- As âncoras são, em maioria, tripwires de presença e de forma: uma âncora que passa não prova que a prosa
  descreve o diff inteiro, e há frases só com a âncora de texto (a seção «O que o texto afirma, e a âncora»
  as declara pela forma).
- A headline usa rótulos e siglas técnicos sem os definir (HMAC, sidecar, P1, pair-rail, shim, CI,
  `deny_baseline`): a anotação da tag é uma nota técnica, e a seção `[1.4.3]` do `CHANGELOG.md` é a
  referência para quem lê.
- As âncoras não rodam no SIGN nem no G0 do corte: o `--claims-only` é um passo manual antes de cada corte.
  Uma mudança do `CHANGELOG.md` depois do land deste RM que tire uma frase ancorada só aparece nele.
- Um estado fora do repositório pode tornar falsa uma frase assinada sem que nada aqui o pegue: a frase
  «nada no repositório impede a repetição (medido em 2026-10-14)» fica falsa se o `main` ganhar proteção de
  branch ou ruleset antes do GA; a frase «testes no CI provam» depende do CI verde no commit do corte.
- Um land depois da publicação deste RM que cite um plano fora do `Scope` é recusado pelo G0 do corte, e o
  corte pede outro RM.
- As linhas `python3 <arquivo>.py` dos dados rodam sem `-I`: o diretório do script entra no `sys.path`. Em
  `.claude/plans/PLAN-194/relmeta/` o único `.py` é o próprio derivador.
- O derivador, o `hard-relmeta.sh` e o `red-control.txt` entram nos dados por caminho; o molde não os pina.
  O `hard-relmeta.sh` confere o sha256 do derivador e o seu próprio contra as linhas `Derivator-SHA256` e
  `Hard-SHA256` deste texto: é um vínculo de auditoria, não uma guarda contra um envoltório alterado que pule
  a conferência; o que fixa os bytes é o `Anchor-SHA` e o registro do rail.
- O `--verify` lê do HEAD este texto e as pré-imagens, e da árvore os 3 alvos e o `CHANGELOG.md`; ele não
  confere outros arquivos da árvore (o SIGN confere a árvore inteira contra o índice antes e depois da
  bateria).
- A bateria do molde roda o pytest completo, com testes de teto de tempo ABSOLUTO; uma falha por tempo que
  se repita nas 3 repetições isoladas reprova o SIGN.
- O `test-install-deny-baseline.sh` roda só nesta bateria (o CI não o roda).

<!-- bloco-comum sign-min v1 -->
## O SIGN deste pacote (bloco comum a todos os pacotes do molde sign-min)

Este texto é assinado pelo arquivo citado em `Molde:`, que executa o núcleo `.claude/plans/PLAN-194/sign-min/sign_min.py`, com os dados do arquivo citado em `Dados:`; os três estão no commit `Anchor-SHA`.

**Antes de escrever qualquer coisa no clone**, o SIGN confere o que segue e recusa com o fato medido e rc 1; valendo os Requisitos abaixo, nessa fase nem o SIGN nem o `git` e o `gpg` que ele executa criam ou alteram arquivo na árvore ou no `.git` do clone (inclusive os bytes do `.git/index`):
- a entrada foi chamada por um caminho com «/», o PATH só tem diretórios absolutos, o `python3` está no PATH e o núcleo tem o sha256 informado pelo roteiro;
- o ambiente recebido pelo núcleo só tem nomes da lista do molde ou os 6 nomes que o `python3` do sistema acrescenta;
- o diretório atual é a raiz do clone, com um `.git` próprio;
- no modo real, a entrada padrão é um terminal e `GPG_TTY` é esse terminal;
- `git`, `gpg` e `bash` estão no PATH; o SIGN fixa o caminho absoluto e o sha256 do arquivo de `git` e do de `gpg`, e daí em diante executa `git` e `gpg` só por esses caminhos;
- `core.hooksPath` tem um único valor, `/dev/null`, e `core.fsmonitor` um único valor, falso, ambos vindos do `.git/config` do clone;
- a identidade do commit vem só da configuração do git;
- não há arquivo `*.lock` sob `.git`;
- `HEAD` é `refs/heads/main` e aponta para o mesmo commit que `refs/remotes/origin/main` do clone; esse commit é o `Anchor-SHA`;
- nenhum caminho rastreado tem atributo `filter`;
- `git status` não lista nada, nem arquivo não rastreado ou ignorado;
- cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice, e todo modo do índice é 100644 ou 100755;
- os dados seguem a gramática do molde; o patch só cria, modifica ou remove arquivos, sem renomear, sem mudar modo, sem tocar `.gitattributes` nem o diretório do molde; cada pré-imagem é a do `Anchor-SHA`; e o patch aplica;
- este texto tem os 4 campos por preencher, este bloco igual ao `bloco-comum.md` do molde, e o `Scope` igual aos caminhos do patch;
- a `.asc` deste texto não existe no `Anchor-SHA`;
- o registro do rail citado nos dados traz o sha256 do patch, deste texto com os campos por preencher e dos dados, e o veredito APPROVE ou DECLARED-P2;
- os caminhos canônicos do patch, segundo o oráculo `--is-canonical`, são os declarados nos dados, e nenhum caminho do patch é do kernel;
- `python3` importa `pytest` e `xdist`; o allowlist `.claude/sentinel-signers.txt` do `Anchor-SHA` carrega sem erro e não está vazio; e o gpg tem uma chave secreta dele.

**Depois disso, nesta ordem**, o SIGN: cria um diretório temporário sob `/tmp` para os logs; aplica o patch ao índice e à árvore; confere que o índice difere do `Anchor-SHA` exatamente nas linhas `index` do patch (caminhos, modos e blobs) e que cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice; roda cada comando `hard` dos dados, que tem de sair com rc 0 e, quando é `python3 -m pytest`, terminar com um resumo só de testes aprovados; roda o pytest sobre as raízes do `testpaths` do `pytest.ini`, nas duas passadas da divisão de marcadores do CI (`not serial` com `-n auto`, e `serial`), conta erro de coleta como falha, repete isolado até 3 vezes cada teste que falhou numa passada e conta como falha o que não terminou, em nenhuma repetição, com resumo só de aprovados; roda os gates de corpus (check-test-env-hygiene, env-inventory-check, check-active-hooks-executable, check-contamination, build-plugin --check, gen-command-skill-hook-map --check, check-docs-freshness, check-docs-drift, verify-counts --no-tests, check-claude-md-claims, check-ceremony-script, check-staleness e validate-governance), cada um com rc 0, sobre a árvore com o patch e com este texto ainda com os campos por preencher; os comandos `hard`, o pytest e os gates recebem um `GNUPGHOME` vazio, um `TMPDIR` com o caminho real, sem link simbólico, de um diretório da bateria criado dentro do diretório temporário, e nenhum `GPG_TTY`, cada um roda num grupo de processos próprio, e o SIGN falha se esse grupo ainda tem processo vivo 10 s depois de o comando terminar; confere de novo que a configuração efetiva do git é a lida no início, que `HEAD`, `refs/heads/main` e `refs/remotes/origin/main` são os lidos no início, que nenhum caminho rastreado tem atributo `filter`, o índice e a árvore, e que `git` e `gpg` resolvem no PATH para os mesmos caminhos, com o mesmo sha256 do início; preenche os 4 campos; confere que a `.asc` deste texto não existe na árvore; assina este texto com a chave escolhida e verifica a assinatura com o `gpg_verify` e o allowlist lidos do `Anchor-SHA` antes da bateria, executando o `gpg` pelo caminho fixado; grava este texto e a `.asc` no índice pelos bytes assinados, sem filtro, e confere o índice e a árvore; faz um `git commit` sem editor, sem hooks e sem assinatura do git; e confere o commit. Depois da assinatura, o SIGN não inicia nenhum programa lido da árvore com o patch; um descendente da bateria que tenha saído do próprio grupo de processos não é conferido e pode continuar rodando.

**O que o SIGN entrega, e só com rc 0:** um commit em `refs/heads/main` deste clone cujo único pai é o `Anchor-SHA`, que difere dele exatamente nos caminhos do patch (com os blobs e modos das linhas `index`), neste texto e na `.asc`, com os bytes assinados; a `.asc` lida desse commit verifica com a mesma chave; autor e committer são a identidade conferida. Com qualquer outro rc, o SIGN não afirma nada: cada linha impressa antes vale só para o passo que ela relata.

**Requisitos** (o que o SIGN precisa encontrar; ele não diz de onde vêm):
- o bash começa com o ambiente montado por `env -i`: sem `BASH_ENV`, sem `ENV` e sem função importada;
- nenhum processo além do SIGN e dos comandos que ele inicia escreve no clone nem no diretório temporário durante a execução;
- a configuração efetiva do git no clone, no início, não define programa que o git execute além do que o SIGN confere acima;
- a configuração que o `gpg` e o `gpg-agent` leem do `GNUPGHOME`, e a que o `git` lê fora do clone, não os manda gravar arquivo no clone nem no diretório temporário; o SIGN não confere essas configurações, porque a máquina, a conta e a configuração do Owner estão dentro da fronteira de confiança do roteiro;
- `/tmp` gravável; no PATH, `git`, `gpg`, `bash` e `python3`;
- nada troca, durante a execução, o que o `git` e o `gpg` carregam ou executam (bibliotecas, o programa para o qual um executável delega, o gpg-agent e o pinentry): o SIGN confere só o sha256 dos dois executáveis;
- no modo real, a chave do allowlist utilizável pelo gpg, com pinentry no terminal, o gpg-agent iniciado sem a senha em cache e a senha não guardada no chaveiro do sistema;
- um `HOME` gravável pelos testes da bateria.

**Publicação:** o Owner publica o commit no `main` do origin, sem force, pelo roteiro; o SIGN não faz push nem fetch.

**Fora do estado esperado:** o SIGN não diagnostica execução anterior, não desfaz e não apaga nada; recusa ou falha com o fato medido, e o clone e o diretório temporário ficam como estiverem. Depois que o núcleo restaura a disposição padrão dos sinais (nas suas primeiras instruções), um sinal INT, PIPE, TERM ou KILL encerra o SIGN sem linha nova dele.
<!-- fim do bloco-comum -->

## Scope

- `.claude/governance/gate-scripts-manifest.txt`
- `.claude/scripts/local/release.sh`
- `.claude/scripts/tests/test_release_bump_sites.py`
