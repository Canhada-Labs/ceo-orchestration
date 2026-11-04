# relmeta-approved — sentinel do RM da v1.4.4 (relmeta-144): o `release.sh` passa a mirar a v1.4.4 (canônico `.claude/governance/gate-scripts-manifest.txt`)

Plan: PLAN-198
Wave: W2 — relmeta-144 (o bloco por release do driver, o re-pin do manifesto ADR-192 e o re-pin do teste que fixa o escopo da anotação da tag)
Dados: .claude/plans/PLAN-198/relmeta/sign.tsv
Molde: .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
Patch: .claude/plans/PLAN-198/relmeta/relmeta.patch
Control: .claude/plans/PLAN-198/relmeta/red-control.txt
Derivator-SHA256: a5a49eaaae58335e6319cca164c78079259923c0d8ef2b7a9fbdf2496545cdf7
Hard-SHA256: fb653b73535171bd8917e9c9f7693ec89fcf9e7607439e5827ef6cd4f68a00fe
Derived-From: ba867cde8b37123af5c95be140b534d02931fac2
Scope-Derived: PLAN-169 / PLAN-170 / PLAN-171 / PLAN-175 / PLAN-176 / PLAN-181 / PLAN-183 / PLAN-186 / PLAN-190 / PLAN-191 / PLAN-192 / PLAN-193 / PLAN-194 / PLAN-195 / PLAN-196 / PLAN-197 / PLAN-198 (ADRs touched: ADR-055 ADR-149 ADR-158 ADR-182 ADR-201 ADR-202)
Patch-sha256: e01de880df3c069edc2af778071ec8fc931b5411c39ad53665a2870f72e2234b
Rail-Record-sha256: 3fdef9bf3db58b6fffa0612982ffec421a04a6d19c9dad0920ce2fa6439e2a6e
Anchor-SHA: 6774b929a74bae65c364c5309d0887b56fa47687
Data: 2026-11-04

## Ratificação (Owner)

- Ao assinar este texto, o Owner aprova o `relmeta.patch` (sha256 em `Patch-sha256`) sobre o `Anchor-SHA`,
  aplicado e conferido pelo molde citado em `Molde:` com os dados citados em `Dados:`.
- O RM é a W2 do corte da 1.4.4 no PLAN-198 (`PLAN-198-release-v1-4-4.md`, seção «Sequence»: RM → bump da rc.1 →
  re-pass de duas lanes → tag da rc.1 → espera de 24 h → GA), DEPOIS de todo land que cite plano, porque o escopo
  da tag sai de `git log v1.4.2..HEAD`. A v1.4.3 só teve a `v1.4.3-rc.1` e nunca chegou ao npm: a base da faixa é
  a v1.4.2, e a tag da 1.4.4 vale pelo trem inteiro desde ela.
- Molde: o SIGN deste pacote é a entrada compartilhada do molde «SIGN mínimo» citada em `Molde:` (decisão do Owner
  na S363, a mesma do RM da 1.4.3); o diretório do molde segue no PLAN-194 e o patch não o toca.
- Ao assinar este texto, o Owner ratifica para este pacote as duas decisões do CEO sobre o molde que o RM da 1.4.3
  ratificou: o controle vermelho fica FORA do SIGN, como registro do construtor que o rail reproduz (seção
  «Controle vermelho (registro)»); e o rail do patch, deste texto e dos dados segue a regra de parada
  pré-registrada no registro do rail: no máximo duas rodadas para código e âncoras, e depois da segunda um achado
  abaixo de P0 só se cura estreitando ou removendo texto da headline, ou fica declarado.
- Decisões do Owner que este texto segue (PLAN-198, «Owner decisions», 2026-11-03): o título e a headline em
  inglês, ASCII (OQ-5); a 1.4.4 segue PATCH (OQ-4); os 233 caminhos canônicos trazidos pelos pull requests
  seguem declarados, sem ratificação por bytes neste corte (OQ-3); este corte segue o molde do PLAN-194 sem
  debate novo (OQ-7).
- Congelamento: da derivação destes materiais até a publicação do commit deste SIGN no `main` do origin,
  nenhum commit fora dos materiais do pacote (este texto e `.claude/plans/PLAN-198/relmeta/`) entra no
  `main`, e o app do Codex não mergeia neste repositório (o PLAN-198 estende o congelamento até o push da tag
  do GA, pela regra 2 do README do kit). O `--verify` do derivador, que a linha `hard-relmeta.sh` dos dados
  roda, recusa, antes da assinatura, qualquer commit entre a linha `Derived-From` e o HEAD que toque caminho
  fora do pacote, inclusive trazido por merge, e qualquer commit que não seja merge e não toque caminho
  nenhum; um commit que só toque o pacote passa por ele. O patch, este texto e os dados são conferidos pelo
  registro do rail que o SIGN confere; o derivador roda isolado (`python3 -I -B`), sem o diretório dele no
  `sys.path`.

## O que esta cerimônia entrega, e nada além

- Tamanho: 3 caminhos, 1 canônico (`.claude/governance/gate-scripts-manifest.txt`, pelo oráculo
  `--is-canonical`; o `release.sh` e o teste dão 0 nele), nenhum caminho do kernel, 3 edições. O patch é
  DERIVADO por `derive-relmeta144.sh` (que roda o derivador num clone descartável e grava o `git diff` de
  formato fixo); nenhuma linha dele foi escrita à mão.
- `.claude/scripts/local/release.sh` (100755, o modo não muda): o bloco PER-RELEASE inteiro, entre a linha
  `TARGET_BASE="1.4.3"` e a linha `RC_NUM="1"`, é trocado pelo bloco derivado: `TARGET_BASE="1.4.4"`, o
  `RELEASE_TITLE`, o comentário que nomeia o derivador e a faixa, o `RELEASE_SCOPE` derivado e o
  `RELEASE_HEADLINE`. `RC_NUM="1"` e o resto do driver não mudam.
- `.claude/governance/gate-scripts-manifest.txt`: só a linha do `release.sh`, com o sha256 do driver depois
  da edição.
- `.claude/scripts/tests/test_release_bump_sites.py`:
  `test_tag_annotation_carries_the_whole_train_and_no_stale_release` passa a exigir o escopo novo na
  anotação; o escopo da 1.4.3 inteiro vira asserção negativa, ao lado das negativas que já estavam lá; o
  docstring ganha o parágrafo do trem 1.4.4.
- O `CHANGELOG.md` NÃO é escrito: é pré-condição. As seções `[1.4.4]` e `[1.4.3]` são únicas e datadas, não há
  seção `[Unreleased]`, as contagens do preâmbulo são as vivas (`verify-counts.sh`, que tem de sair rc 0 com os
  campos `violations` e `live` presentes e dos tipos certos) com o rótulo `v1.4.4`, e a re-declaração do anexo
  da v1.4.0 está num Known-open da `[1.4.4]`, com um item próprio, que não cita, entre colchetes, a entrada de
  outra release, dizendo que nenhuma release está atribuída à cura. Nem esse Known-open nem a seção `[1.4.4]`
  inteira nomeia versão de três números (`x.y.z`) posterior à 1.4.4, em qualquer major e com ou sem o prefixo
  `v`, salvo as versões de ferramentas externas declaradas uma a uma no derivador (`EXTERNAL_VERSIONS`: Claude
  Code 2.1.280; npm 11.20.0); versões de dois números ficam fora do mecanismo. Cada parágrafo da headline tem
  uma frase na seção `[1.4.4]` (`PARAGRAPH_LINKS` do derivador, na ordem dos parágrafos; a mesma frase serve
  aos parágrafos 2 e 3).
- Consequência: daqui em diante o driver mira a v1.4.4 (`release.sh --help` anuncia
  `target base version: 1.4.4`), e o título, o escopo e a headline abaixo vão para a anotação ASSINADA da tag
  de cada corte da 1.4.4 (rc e GA). O mesmo texto vale para as duas tags, por isso ele não afirma publicação
  no npm.

## O texto que vai para a anotação da tag

A seção entre os marcadores é DERIVADA: o `derive-relmeta144.sh` a grava a partir das mesmas constantes que
geram o patch, e o `--verify` do derivador, que a linha `hard-relmeta.sh` dos dados roda, exige que ela seja,
byte a byte, a re-derivada a partir do `Anchor-SHA`. A forma é a do `msg` que o driver assina na fase `tag`
(o `--verify` exige esse molde uma vez no driver com o patch): `<tag>` é `v1.4.4-rc.N` no corte de uma rc e
`v1.4.4` no GA, e `<commit do corte>` é o HEAD do corte; o resto vai para a anotação como está aqui. O roteiro
do Owner imprime esta seção, lida do `Anchor-SHA`, antes de pedir o «SIM» que inicia a cerimônia; o SIGN não
a imprime.

<!-- texto-da-tag: derivado -->
```text
<tag> — Maintenance release: the train since v1.4.2, with a Bash guard against indirect execution, hooks split into modules, and fixes to the kernel hard-deny list and the secret redactor

Anchor: <commit do corte>
Scope:  PLAN-169 / PLAN-170 / PLAN-171 / PLAN-175 / PLAN-176 / PLAN-181 / PLAN-183 / PLAN-186 / PLAN-190 / PLAN-191 / PLAN-192 / PLAN-193 / PLAN-194 / PLAN-195 / PLAN-196 / PLAN-197 / PLAN-198 (ADRs touched: ADR-055 ADR-149 ADR-158 ADR-182 ADR-201 ADR-202)

Headline: Maintenance release (PLAN-198). v1.4.3 never reached npm: only
v1.4.3-rc.1 was tagged, so this release covers the whole train since
v1.4.2, and everything in the v1.4.3 entry of the CHANGELOG is part
of it, as changed by the v1.4.4 entry. The requirements do not
change from v1.4.2: Claude Code v2.1.280 or later (install.sh and
upgrade.sh still refuse an older claude on the PATH with exit 6,
unless --allow-old-claude-code is given), Python 3.9 or later and
Node.js 20 or later for the npm shim.

From the v1.4.3 entry: the harness-config gate of /ceo-boot turns
green with the default ceremony (maintainer), both on an install
upgraded from v1.4.2 with upgrade.sh and on a fresh install; this
green is claimed for the default ceremony only. The agent_spawn
writer reads the previous chain link, computes the HMAC, writes the
line and updates the sidecar under one lock of the log, which retires
signed condition 67 of v1.4.0-rc.1; breaks the race already wrote
stay in the logs, and writers that resolve different locks for the
same log still do not exclude each other.

Also from that entry: a fresh --ceremony user install writes
permissions.defaultMode with the value manual when the settings.json
produced by that same run has none, unless
CEO_INSTALL_SKIP_DENY_BASELINE=1, and a settings.json that existed
before the install is never touched. Fixes to
audit-query.py, /status, /ceo-boot and check-substrate-drift.py.

New since v1.4.3-rc.1: a bounded scan in the Bash guard against
indirect execution, on by default (PLAN-195, ADR-201); it only adds
blocks, and CEO_BASH_INDIRECT_GUARD=0 turns it off. Several of the
largest hooks and scripts become thin entry points over modules
under .claude/hooks/_lib/ (PLAN-197, ADR-202): a hook patched by hand
must be patched again in its module. A registered hook no longer
drains the audit spool at exit, a partial cure.

The preparation of this release found that the kernel's hard-deny
list had not followed the code that moved out of seven kernel entry
points; that code is hard-deny again. The secret redactor that the
Codex and Grok egress uses had, since v1.0.0, cut the text at offsets
taken from its normalized form, which the signed v1.4.0 verdict had
declared as its condition 58; its scan() offsets now index the text
passed in. Neither fix has a sentinel file.

The honest part: most of this train after v1.4.3-rc.1 reached main
through two pull-request merges, without the signing ceremony; four
earlier ones are in the v1.4.3 entry. The two changed 233 canonical
paths, 15 of them kernel paths by the list as merged, and with them
the meaning of three governance checks: the VETO floor and the model
allowlist now accept model families, retired ids among them, and a
Codex CLI newer than the one the manifest pins by sha256 (v0.160.0,
one platform) passes on a version floor, without a matching hash. No
signed sentinel ratifies those files, and main has no branch
protection and no ruleset (measured through the GitHub API on
2026-11-03).

Declared, with no release assigned to their cure: the audit spool
cure is partial, the new guard's false-positive limits were never
measured on this implementation, and the backup leaves out the key
material. One condition of the redactor fix is declared too: the
ingress path redacts the raw answer text before parsing it, so a
redaction can change whether an answer parses; its structural cure
is scheduled for the next release. Of the signed v1.4.0 annex,
conditions 67 and 58 are cured, and this release does not claim the
cure of any other annex condition. This release does not claim the
cure of the three P1 findings of the signed v1.4.2-rc.1 annex.
Claude Code's cleanup (cleanupPeriodDays, default 30) can still
delete the audit logs, and no plan in this release carries a
structural cure. Everything else that stays open is in the
Known-open of the CHANGELOG entry.

No speed claim. See CHANGELOG.md [1.4.4].
```
<!-- fim do texto-da-tag -->

## Como ler o Scope da tag

- A linha `Scope` sai da regra que o G0 do corte e o `scope_check` do kit do PLAN-198 exigem: todo `PLAN-NNN`
  citado num assunto de commit de `v1.4.2..HEAD`, mais os ADRs tocados na faixa (`.claude/adr/`), listados.
- Por isso ela lista planos que esta release não entrega: PLAN-170 e PLAN-181 aparecem só em commits que os
  abandonam; PLAN-192 aparece só num commit de fechamento; PLAN-193 aparece em commits de fechamento e de
  documentação; PLAN-196 aparece só no commit que abre um plano de backlog, ainda em rascunho. A linha diz quais
  planos os commits da faixa citam, não que cada um entregou algo na 1.4.4. O que a release entrega está na
  headline e nas seções `[1.4.4]` e `[1.4.3]` do `CHANGELOG.md`.
- Um ADR na lista quer dizer que um arquivo dele mudou na faixa (um ADR novo, uma emenda ou um status), não que
  a release cumpre o ADR inteiro.
- Filtrar a lista à mão faria o G0 do corte e o kit recusarem a tag (eles exigem o superconjunto).

## O que o texto afirma, e a âncora

Cada parágrafo da headline tem âncoras no derivador (`CLAIMS`), cada uma com uma parte de CÓDIGO (arquivos, AST,
ancestralidade, sondas em processo próprio) e uma de TEXTO (frases do `CHANGELOG.md`, com o espaço em branco
normalizado): as âncoras herdadas da 1.4.3 leem a seção `[1.4.3]` e a frase da `[1.4.4]` que a põe no trem; as
novas leem a `[1.4.4]`. As âncoras rodam no `--claims-only` (manual: antes da derivação, antes da rc.1 e antes do
GA) e na derivação; NÃO rodam no SIGN.

| Parágrafo da headline | Âncoras | O que a parte de código confere |
|---|---|---|
| 1. a v1.4.3 não chegou ao npm; requisitos | `train`, `ccfloor` | o commit da v1.4.3-rc.1 (`5e7cb65e`) ancestral do HEAD e o `npm-publish.yml` pulando as tags `-rc.`; o bloco do piso do Claude Code rodado contra um `claude` falso no `install.sh` e no `upgrade.sh`, e byte a byte o da v1.4.2 nos dois; `SUPPORT.md` cita 2.1.280; `engines.node` `>=20` |
| 2. gate do harness, condição 67 (da `[1.4.3]`) | `harness`, `cond67` | as fixtures do replay na pasta entregue, os grupos `harness-*` no teste histórico, C9 e o SIGN da W7a ancestrais, o resíduo da cerimônia `user` preso ao código e o gate no modo do CI na raiz verde; a fachada `audit_log.py` executa as partes de `_lib/_audit_log_parts/` e o único `append_entry` delas, em `rotation_storage.py`, lê o elo, grava a linha e atualiza o sidecar dentro de UM MESMO `with FileLock(paths["lock"], …)` (por AST); sentinel e `.asc` da cura e a condição 67 no envelope da v1.4.0-rc.1 |
| 3. `defaultMode`, correções (da `[1.4.3]`) | `defaultmode`, `fixes` | `DEFAULT_MODE_BASELINE="manual"` e as rotas do `install.sh`, o template `user` sem `permissions.defaultMode`; `status.py`, `check-substrate-drift.py`, o `external_wait` hoje em `_lib/_ceo_boot_parts/` (que o `ceo-boot.py` instala) e o teste da ordem dos flags do `audit-query.py` |
| 4. guarda de Bash, divisão em módulos, spool | `guard`, `split`, `spool` | a fachada `check_bash_safety.py` executa `posture_scan`, que importa `bash_indirect_guard`, lê os dois interruptores, só desliga a varredura com o valor `0` e, no ramo do acerto, devolve só `Decision(allow=False, …)` (por AST); ADR-201 presente; `check_bash_safety.py` com no máximo 100 linhas e `_lib/audit_emit.py` com no máximo 1000, os pacotes deles com módulos, ADR-202 presente; `_python-hook.sh` exporta `CEO_HOOK_BOUNDED_EXIT=1` e o `spool_writer.py` lê a variável e grava `exit_deadline_skip` |
| 5. as duas correções | `kernelfix`, `redactor` | pelo predicado do kernel do HEAD, num processo próprio, todo arquivo rastreado dos 7 pacotes que receberam o código das fachadas do kernel e de `adapters/live/`, e os 5 módulos planos, são caminhos do kernel; o teste novo presente; o commit `161e1dc3` ancestral; `scan_and_redact`, num processo próprio, sobre um texto com uma reticência antes de um token de exemplo, devolve o texto com só o token trocado pelo rótulo; o redator de saída do Codex o chama; o commit `54bab3cc` ancestral; o envelope assinado da v1.4.0 traz a condição 58 com o título do defeito dos offsets |
| 6. a parte honesta: os merges e as três checagens | `merges`, `models`, `codex` | pelos assuntos, 4 merges de pull request em `v1.4.2..v1.4.3-rc.1` e os #6 e #7 depois; nos caminhos que os dois trouxeram, 233 canônicos pelo oráculo do HEAD, 15 do kernel pela lista como mergeada e nenhum `.asc`; o `model_currency`, num processo próprio, admite os ids sondados (dois datados com a retirada no ledger, um de cada fornecedor externo) e os três chamadores o importam; o manifesto pina 0.160.0 por sha256 só para `aarch64-apple-darwin`, o corpo do pin é `>=0.128.0`, `CODEX_VERSION_FLOOR = "0.160.0"` e o resultado `version_floor_only` existe |
| 7. o que fica declarado | `annex` | os envelopes da v1.4.0 e da v1.4.2-rc.1 presentes; o `ceo-backup.sh` sem `audit-key` nem `.salt` |

A tabela diz o que cada âncora de código confere; ela não é a lista do que fica sem âncora. Em todo parágrafo
há frases que só a parte de TEXTO ancora (a frase está no `CHANGELOG.md`), e elas são, pela forma: o que fica de
fora ou aberto (os resíduos declarados, inclusive a condição do redator e a espera da cura dela); estados fora do
repositório (o GitHub, o npm, o CI de um commit futuro, a proteção do `main`); requisitos que o instalador não
confere; e o comportamento dentro de uma INSTALAÇÃO, que nenhuma âncora roda (a prova de instalação do gate é a
do CI, C9, e a do SIGN da W7a; a da gravação do `defaultMode` é a linha `test-install-deny-baseline.sh` dos
dados).

## Controle vermelho (registro)

Medição do construtor, com data e substrato em `.claude/plans/PLAN-198/relmeta/red-control.txt`; o SIGN não a
executa, e o rail a reproduz.

- `--claims-only` na árvore da v1.4.2 (`b55084da`) com o `CHANGELOG.md` do HEAD sobreposto: a parte de TEXTO
  passa em todas as âncoras (o CHANGELOG é o do HEAD), e a parte de CÓDIGO falha em todas menos duas, cada uma
  pelo motivo dela; passam, por desenho, `ccfloor` (os requisitos não mudam: o código do piso é o mesmo) e
  `annex` (só presença de envelopes e um acoplamento com o `ceo-backup.sh`, verdes nas duas árvores).
- A âncora `redactor` é uma sonda de runtime: na v1.4.2 o mesmo texto sai com o corte deslocado.
- `--claims-only` na árvore dos materiais com o `CHANGELOG.md` de `e85f7a7f` (o commit antes do que nomeia a
  condição 58 na `[1.4.4]`) sobreposto: a parte de CÓDIGO passa em todas as âncoras, e a de TEXTO falha só em
  `kernelfix`, `redactor`, `annex` e no parágrafo 5 da pseudo-âncora `paragrafos`, cada uma pelo motivo dela (as
  frases da headline sobre a condição 58 e sobre as curas do anexo da v1.4.0).
- A âncora `redactor` contra uma cópia do envelope da v1.4.0 com a condição 58 renumerada: reprova (o envelope
  real passa).
- A âncora `cond67` contra um `append_entry` sintético que lê o elo sob uma trava e grava a linha e o sidecar
  sob outra: reprova (o mesmo `append_entry` com uma trava só passa).
- A conferência de nomes do derivador contra uma cópia dele sem uma constante que ele lê: recusa, nomeando-a.
- `--verify` sobre o Anchor dos materiais SEM o patch aplicado falha (o driver na árvore ainda mira a 1.4.3).
- Num clone dos materiais com o patch, depois de um commit fora do pacote e de um commit só do pacote que
  acrescenta ao diretório do derivador um `argparse.py` que sai rc 0: o `--verify` rodado sem `-I` sai rc 0
  antes de conferir qualquer coisa (sem o `argparse.py`, ele recusa o commit fora do pacote); o
  `hard-relmeta.sh`, que o roda com `-I`, recusa o commit fora do pacote. Com o `argparse.py` e sem o commit
  fora do pacote, o `hard-relmeta.sh` sai rc 0.

## Comandos próprios do pacote (as linhas `hard` dos dados, nesta ordem)

1. `bash -n .claude/scripts/local/release.sh`: a sintaxe do driver com o bloco novo.
2. `bash .claude/plans/PLAN-198/relmeta/hard-relmeta.sh` (forma 2 do molde), que sai rc 0 só se, nesta ordem:
   o sha256 do derivador é o da linha `Derivator-SHA256` deste texto no HEAD e o do próprio envoltório é o da
   linha `Hard-SHA256`; `shasum -a 256 -c` do manifesto sai rc 0 com tantas linhas OK quantas linhas não
   vazias; exatamente uma linha do manifesto é a do `release.sh`, com o sha256 do arquivo; `TARGET_BASE="1.4.4"`
   aparece uma vez no driver e `TARGET_BASE="1.4.3"` nenhuma; `release.sh --help` sai rc 0 com a primeira
   linha `release.sh — operator release driver (target base version: 1.4.4)`; os commits da v1.4.2
   (`b55084da`) e da v1.4.3-rc.1 (`5e7cb65e`) são ancestrais do HEAD; e, por último,
   `python3 -I -B .claude/plans/PLAN-198/relmeta/apply-relmeta144-edits.py --repo=. --verify` sai rc 0. O `-I`
   tira do `sys.path` o diretório do derivador e o site do usuário e faz o Python ignorar as variáveis
   `PYTHON*`; o `-B` não grava `.pyc`; o derivador só importa a stdlib. O molde não aceita opção antes do
   caminho de um script `python3` numa linha `hard`: por isso o derivador roda dentro do envoltório, depois
   da conferência do sha256 dele. O envoltório só lê; o git roda com `GIT_OPTIONAL_LOCKS=0`.
   O `--verify` sai rc 0 só se: a conferência de nomes do derivador passa (nenhum nome lido que o arquivo não
   defina em lugar nenhum); `b55084da` é ancestral do HEAD (e a tag `v1.4.2`, se o clone a tem, descasca
   nele); a linha `Derived-From` deste texto é ancestral do HEAD e é o último commit do HEAD que toca algo
   fora de `.claude/plans/PLAN-198/relmeta/` e deste texto;
   `git rev-list --full-history` de `Derived-From` até o HEAD, limitado aos caminhos fora do pacote, sai vazio
   (um commit fora do pacote, inclusive trazido por merge, recusa aqui, antes da assinatura); nenhum commit
   dessa faixa que não seja merge deixa de tocar caminho (um commit vazio recusa); o escopo re-derivado de
   `git log` sobre o HEAD é a linha `Scope-Derived` e contém PLAN-197 e PLAN-198; a partir das pré-imagens
   `HEAD:<alvo>` dos 3 caminhos, o bloco, o manifesto e o teste re-derivados são, byte a byte, os da árvore com
   o patch; o driver monta a anotação pelo molde que a seção do texto da tag reproduz, e essa seção é, byte a
   byte, a re-derivada; e o `CHANGELOG.md` cumpre a pré-condição da seção «O que esta cerimônia entrega». Só
   plumbing do git (`log`, `rev-list`, `cat-file`, `rev-parse`, `merge-base`, `diff`, `diff-tree`), com
   `GIT_OPTIONAL_LOCKS=0`, mais o `verify-counts.sh --json --no-tests`, que tem de sair rc 0; as âncoras NÃO
   rodam aqui.
3. `bash scripts/tests/test-install-deny-baseline.sh`: o teste que prova que a instalação `user` grava o
   `defaultMode` quando ele falta e o preserva quando existe; o parágrafo 3 da headline herda essa frase, e
   nenhum workflow do CI roda este teste.
4. `python3 .claude/scripts/validate_governance_fast.py`: o validate rápido sobre a árvore com o patch.
5. `python3 -m pytest` sobre `.claude/scripts/tests/test_release_bump_sites.py`, com resumo só de aprovados: o
   teste re-pinado (o escopo novo exigido, o da 1.4.3 negado) e os testes de prosa do driver (versões derivadas
   de `TARGET_BASE`, nenhuma contagem de sítios, a atribuição da publicação ao `npm-publish.yml`).

## Rail

- O registro citado em `rail` nos dados traz as rodadas do molde sobre o patch, este texto (com os quatro
  campos por preencher) e os dados, pela regra de parada pré-registrada nele: na rodada 1, o Codex em
  `exec --sandbox read-only` e dois refutadores Claude na MESMA rodada, com o derivador como terceira lane; a
  rodada 2 é a última para código e âncoras. Pauta: cada frase da headline contra as seções `[1.4.4]` e
  `[1.4.3]` e o código; cada âncora prova a frase e é vermelha na v1.4.2; o `--verify` recusa escopo velho e
  land depois da derivação; o `Scope` deste texto são os caminhos do patch.
- O registro traz, além dos três sha256 e do `Rail-Verdict` que o SIGN confere, o sha256 do derivador, do
  `hard-relmeta.sh` e do `red-control.txt` revisados (o SIGN não os confere: o `hard-relmeta.sh` confere os
  dois primeiros contra as linhas deste texto).

## O que muda em relação à relmeta-143

- A constante única da release anterior virou duas: o alvo anterior do driver (1.4.3, a âncora inicial do bloco
  e do docstring do teste) e a base da faixa (1.4.2, o commit da tag `v1.4.2`).
- As três âncoras da 1.4.3 que o HEAD não sustentava como estavam foram re-ancoradas no código que as sustenta
  hoje (`cond67` no `append_entry` de `_lib/_audit_log_parts/rotation_storage.py`; `fixes` no `external_wait`
  de `_lib/_ceo_boot_parts/`; `codex` no piso de versão, com o corpo do pin sem limite superior); o
  acoplamento com o guia de recuperação saiu, e o lugar dele é o do `ceo-backup.sh`.
- O título, a headline e a palavra de ligação dos ADRs no `Scope` estão em inglês (OQ-5); a pré-condição do
  CHANGELOG exige o rótulo `v1.4.4` no preâmbulo (a tolerância a um preâmbulo intocado da release anterior saiu).
- O derivador confere, por AST e em todo modo, que todo nome que ele lê é definido em algum lugar do arquivo
  (um nome definido só como local de outra função não é pego aqui e falha ao rodar), e que nenhum dos nomes
  removidos no clone segue em uso.
- O `--verify` não é mais uma linha `hard` própria: ele roda no fim do `hard-relmeta.sh`, isolado
  (`python3 -I -B`).

## Resíduos declarados (pela forma)

- As âncoras são, em maioria, tripwires de presença e de forma: uma âncora que passa não prova que a prosa
  descreve o diff inteiro, e há frases só com a âncora de texto (a seção «O que o texto afirma, e a âncora»
  as declara pela forma).
- A headline usa rótulos e siglas técnicos sem os definir (HMAC, sidecar, P1, VETO, sha256): a anotação da
  tag é uma nota técnica, e as seções `[1.4.4]` e `[1.4.3]` do `CHANGELOG.md` são a referência para quem lê.
- As âncoras não rodam no SIGN nem no G0 do corte: o `--claims-only` é um passo manual antes de cada corte.
  Uma mudança do `CHANGELOG.md` depois do land deste RM que tire uma frase ancorada só aparece nele.
- Um estado fora do repositório pode tornar falsa uma frase assinada sem que nada aqui o pegue: a frase
  «main has no branch protection and no ruleset (measured through the GitHub API on 2026-11-03)» fica falsa
  se o `main` ganhar proteção de branch ou ruleset antes do GA; a frase «v1.4.3 never reached npm» depende do
  registro do npm.
- Um land depois da publicação deste RM que cite um plano fora do `Scope` é recusado pelo G0 do corte e pelo
  kit, e o corte pede outro RM.
- A linha `python3 .claude/scripts/validate_governance_fast.py` dos dados roda sem `-I` (o molde não aceita
  opção antes do caminho do script): o diretório `.claude/scripts/` entra no `sys.path` dela. Ele fica fora do
  pacote, e um commit depois da derivação que toque caminho fora do pacote é recusado pelo `--verify`, que
  roda antes, na linha 2. Um arquivo que um commit depois da derivação acrescente ao pacote não é recusado:
  o derivador, isolado, não o importa, e nenhuma linha dos dados o executa.
- O `hard-relmeta.sh` entra nos dados por caminho, e o derivador e o `red-control.txt` são citados por caminho
  neste texto; o molde não pina nenhum dos três. O `hard-relmeta.sh` confere o sha256 do derivador e o seu
  próprio contra as linhas `Derivator-SHA256` e `Hard-SHA256` deste texto antes de rodar o derivador: é um
  vínculo de auditoria, não uma guarda contra um envoltório alterado que pule a conferência; o que fixa os
  bytes é o `Anchor-SHA`.
- O `--verify` lê do HEAD este texto e as pré-imagens, e da árvore os 3 alvos e o `CHANGELOG.md` (o SIGN
  confere a árvore inteira contra o índice antes e depois da bateria).
- A bateria do molde roda o pytest completo, com testes de teto de tempo ABSOLUTO; uma falha por tempo que
  se repita nas 3 repetições isoladas reprova o SIGN.
- O `test-install-deny-baseline.sh` roda só nesta bateria (o CI não o roda).
- O SIGN confere o allowlist de signatários, não o registro de validade (`is_valid_signer`), como no RM da 1.4.3.

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
