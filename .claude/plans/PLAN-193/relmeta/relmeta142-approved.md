# relmeta142-approved — sentinel da relmeta da v1.4.2 (o `release.sh` passa a mirar a v1.4.2)

Plan: PLAN-193
Wave: W6 — relmeta-142
Anchor-SHA: ANCHOR-PLACEHOLDER
Data: DATA-PLACEHOLDER
Patch-SHA256: a5941b4b90651a3878fd9c4914c8adc094039019793bb129850f5e8258bbb9bb
Derivator-SHA256: f1dcb806b04a8410d02ceb9285998d6a35729076932bce5783688cf415762ecb
Derived-From: f0e219c23a5a0578a36fdaa965ea3a03e1222d6a
Scope-Derived: PLAN-190 / PLAN-193 (ADRs tocados: ADR-149)

> `Patch-SHA256`, `Derivator-SHA256`, `Derived-From` e `Scope-Derived` são escritas pelo
> `derive-relmeta142.sh` sobre o HEAD depois de TODOS os lands da 1.4.2; `Anchor-SHA` e `Data`, pelo
> `OWNER-RELMETA142-SIGN.sh` no momento da assinatura. Reescrever um byte deste
> arquivo depois de assinar invalida o `.asc`.

## Decisões do Owner que este texto executa

- PLAN-193 OQ-3 (2026-09-22), verbatim: «1.4.2» — o material assinado RE-DECLARA que a cura do anexo
  da v1.4.0, que a decisão de 2026-09-18 re-alvejara para «a 1.4.2», não está nela.
- Papel do Opus 5.5 (S357, 2026-09-22), verbatim: «Padrão + piso VETO».
- PLAN-193 OQ-1 (2026-09-22), verbatim: «xhigh» — o esforço das instalações NOVAS.
- PLAN-193 OQ-7 (2026-09-23), verbatim: «Instalação nova + opt-in (Recomendado)» — o `upgrade.sh` não
  grava `xhigh` em quem já instalou.
- PLAN-193 OQ-8 (2026-09-24), verbatim: «Migrar gravando 'high' (Recomendado)» — quando o `upgrade.sh`
  migra o pin e o adopter não tem `effortLevel`, grava `"high"`; um `effortLevel` do adopter nunca é
  sobrescrito.
- PLAN-193 OQ-9 (2026-09-24), verbatim: «Exigir CC ≥ 2.1.280 (Recomendado)» — `install.sh` e
  `upgrade.sh` checam `claude --version` e avisam/recusam abaixo disso.
- PLAN-193 OQ-5 (2026-09-22), verbatim: «Sim, embarca (Recomendado)» — a opção B do `relaunch --out`.
- A condição 23 do material do GA da v1.4.1 alveja para a 1.4.2 a cura da classe «hook que roda antes
  da decisão de permissão e persiste os bytes de um caminho que o harness pode negar» (FN-04). A
  headline afirma a cura do CASO do hook do Workflow, que é o que a âncora abaixo sonda, e diz que a
  classe não se esgota nesse hook: a headline NÃO declara a classe curada.

## Scope

- `.claude/scripts/local/release.sh` — o bloco POR-RELEASE (`TARGET_BASE` 1.4.1 → 1.4.2,
  `RELEASE_TITLE`, `RELEASE_SCOPE`, `RELEASE_HEADLINE`) e UMA mudança de lógica: `--yes` no `gpg` do
  probe de assinatura do `preflight`, com o comentário do porquê (o `mktemp` cria o arquivo e
  `gpg --output` sobre arquivo existente pergunta «Overwrite? (y/N)» direto no terminal; a resposta
  padrão fazia o probe dizer que uma chave íntegra não conseguia assinar).
- `.claude/governance/gate-scripts-manifest.txt` — só a linha do sha256 do `release.sh` (canônico; o
  driver é membro do manifesto ADR-192, e os workflows o conferem com `shasum -a 256 -c`).
- `.claude/scripts/tests/test_release_bump_sites.py` — o re-pin CONSCIENTE de
  `test_tag_annotation_carries_the_whole_train_and_no_stale_release` (o escopo novo vira a asserção
  positiva e o trem da v1.4.1 vira asserção NEGATIVA), o controle novo
  `test_preflight_signature_probe_answers_its_own_overwrite_question` e o controle do instrumento
  dele, `test_gpg_output_scanner_reads_commands_not_lines` (o teste lê os comandos `gpg` do driver
  por comando, não por linha: comentário, heredoc, `;`/`|`/`&&` e caminho absoluto têm um caso cada).
  Arquivo livre; viaja aqui porque driver e teste só são verdadeiros juntos.

Nada além desses três arquivos, deste sentinel e da sua assinatura entra no commit da cerimônia: o
script monta a árvore do commit a partir de cópias congeladas e confere o conjunto EXATO de caminhos.

## O que você assina, e como confere

O conteúdo é o patch `RELMETA142.patch`, cujo sha256 está pinado acima, gerado pelo
`apply-relmeta142-edits.py` cujo sha256 também está pinado, com um `git diff` de formato fixo (sem a
config git do usuário). O script de cerimônia captura o HEAD uma vez, no P0, e usa esse commit até o
fim: um HEAD que muda no meio aborta. Antes de pedir a assinatura, ele:

1. recusa um patch VELHO pelo nome e pelo motivo — patch nunca derivado; sha256 do patch diferente
   do pinado; derivador diferente do pinado; commit fora de `.claude/plans/PLAN-193/relmeta/` landado
   depois de `Derived-From` (lista os commits); ou a re-derivação do HEAD, num clone descartável,
   diferente byte a byte do patch commitado (mostra o escopo pinado ao lado do re-derivado). Em todos
   os casos a rota é a mesma: re-derivar, commitar, pushar e rodar a cerimônia de novo;
2. confere que o patch commitado aplica sobre a árvore viva (`git apply --check`);
3. imprime o bloco POR-RELEASE inteiro — o texto que vai para DENTRO da anotação ASSINADA da tag
   (`release.sh tag` monta a mensagem a partir dele) —, descarta o que foi teclado enquanto ele
   re-derivava e espera você digitar `assino`. Qualquer outra resposta aborta sem assinar.

O escopo do trem (`RELEASE_SCOPE`) não é digitado: sai de `git log v1.4.1..HEAD` (planos citados nos
assuntos de commit; o PLAN-193 tem de já estar entre eles, porque o commit dos materiais o cita) e de
`git diff --name-only v1.4.1..HEAD -- .claude/adr/` (ADRs tocados, listados; «nenhum» quando vazio).
O valor derivado está em `Scope-Derived` acima.

## O que o texto da tag afirma, e a âncora que o derivador confere

O derivador recusa derivar se QUALQUER âncora falhar sobre a árvore derivada, e diz qual. Uma âncora
que passa é evidência LIMITADA daquilo que está escrito ao lado dela, não prova de que a prosa descreve
o diff (o Residual diz o que fica de fora).

- Opus 5.5 padrão: `model` = `claude-opus-5-5` nos três settings enviados (dogfood, template base e
  template `user`); o id em `availableModels` e `generate-available-models.py --check` verde
  (settings × working set do ADR-149); o id em `VETO_FLOOR_ALLOWED`, lido em RUNTIME de
  `agent_frontmatter`; nenhuma linha `model:` de um agente de `.claude/agents/` que já existia na v1.4.1
  mudou; o ADR-149 (A3.3) declara, pela forma, que o despacho mitigado `general-purpose` e os agentes
  de Workflow, sem modelo próprio, rodam no modelo da sessão, cujo pin é `claude-opus-5-5`;
  `fallbackModel` = `["claude-opus-5"]` no template base.
- Piso do Claude Code e esforço: a função do piso, extraída do `install.sh` e do `upgrade.sh`, roda
  contra um `claude` FALSO — recusa 2.1.279 e 2.1.99 (ordem numérica), aceita 2.1.280 e 2.2.0, recusa
  uma versão com sufixo colado aos três números mesmo no piso ou acima dele (2.1.280-rc.1,
  2.2.0-beta.1), lê só a linha que nomeia `(Claude Code)` (uma linha de outra ferramenta com versão
  maior, impressa antes, não é lida), com `--allow-old-claude-code` aceita avisando, num dry-run aceita
  nomeando a recusa, e sem `claude` no PATH, sem versão legível ou com um `claude --version` que não
  termina (parado pelo limite da sonda, rebaixado a 1 s só nesse caso) aceita avisando —; a chamada
  dela no nível de topo dos dois scripts sai 6 na recusa; `CC_FLOOR_VERSION` = 2.1.280; uma linha
  do `SUPPORT.md` cita 2.1.280 e `claude-opus-5-5`; `effortLevel` = `xhigh` nos dois templates; na
  tabela de migração do `upgrade.sh`
  (a que `--print-settings-baselines` imprime), `model` troca `claude-opus-5` (enviado antes) e a
  ausência por `claude-opus-5-5` exigindo a lista de modelos, e `effortLevel` é opt-in `xhigh` com
  `high` na troca a partir de `claude-opus-5`; `--adopt-setting` no `upgrade.sh`; o CHANGELOG declara
  que esse `effortLevel` passa a valer sobre o nível salvo com `/effort` e que um valor definido nunca
  é sobrescrito.
- Pin do Codex: `codex-cli-pin-manifest.json` pina a 0.156.1 com sha256 de payload, e o range de
  `codex-cli-pin.txt` a admite.
- FN-04 (o caso do Workflow): sonda de RUNTIME — o hook do Workflow roda como o harness o roda (stdin
  JSON, processo próprio), com HOME, estado e TMPDIR num diretório temporário, para duas chamadas
  PreToolUse sem PostToolUse: `scriptPath` absoluto fora do projeto e relativo ao cwd dentro dele, cada
  um apontando para um canário com token aleatório próprio. Cada lançamento é então vinculado à mão
  (`ceo-launches.py bind`, que não tira cópia) e `relaunch <run> --out <arquivo>` tem de sair 7 sem
  criar o arquivo. Um token em qualquer arquivo da árvore temporária (fora os canários) ou em arquivo
  do repositório escrito durante a sonda (ignorados inclusos) reprova; o sha256 e o tamanho de CADA
  canário têm de estar gravados juntos num registro, senão a sonda reprova por vazia. E um Known-open
  do CHANGELOG declara que as cópias gravadas pela v1.4.1 ficam em `launches/`, e o sentinel da cura
  (`wave-fn04-approved.md`) declara no residual dele que a classe não se esgota nesse hook — a
  headline afirma a cura do CASO e repete essa declaração; nenhum outro hook da classe é sondado.
- `relaunch --out`: `ceo-launches.py` mudou desde a v1.4.1 e publica por `os.link`; o plano
  `PLAN-190-FOLLOWUP-relaunch-out-partial-write.md` e a seção de limites declarados do
  `relaunch --out` em `docs/workflow-recovery.md` estão no HEAD.
- Via expressa: `re-pin-codex.py`, `check-substrate-drift.py` e `derive-settings-baselines.py` no HEAD,
  nenhum deles nomeado nos três arquivos de settings que registram hooks.
- Parte honesta: o envelope da v1.4.0 existe; uma subseção Known-open da entrada `[1.4.2]` re-declara o
  anexo da v1.4.0, diz que nenhuma release está atribuída à cura dele e não nomeia versão do framework
  posterior à 1.4.2 (versões de outras ferramentas, como a do Claude Code, não contam); a entrada cita
  `cleanupPeriodDays` com o padrão de 30 e um Known-open declara, sem plano de cura, que a limpeza do
  Claude Code pode apagar o log de auditoria.

`--claims-only` roda só essas âncoras (uma linha PASS/FAIL por parágrafo; rc 0 = todas passam).

Pré-condições do CHANGELOG (ele NÃO é escrito aqui): exatamente uma seção `[1.4.2]`, DATADA
(`## [1.4.2] - AAAA-MM-DD`: a anotação da tag termina apontando para ela), nenhuma `[Unreleased]`, e o
claim de contagens do preâmbulo igual às contagens vivas, com o rótulo v1.4.2 — ou v1.4.1, desde que o
preâmbulo seja byte a byte o que a tag v1.4.1 publicou.

## Verificado pela cerimônia depois de aplicar

Os três arquivos aplicados são byte a byte os da re-derivação; `shasum -a 256 -c` do manifesto (o
comando do CI), com o número de linhas OK igual ao de linhas do manifesto; `bash -n` do driver;
`release.sh --help` anunciando 1.4.2; a suíte do driver inteira (`test_release_bump_sites.py`);
validate-governance com 0 erros, contamination, verify-counts, ceremony-lint e
check-claude-md-claims — em ambiente de allowlist. Qualquer um reprovando restaura a árvore (os três
alvos e o sentinel voltam ao byte de antes; a assinatura parcial sai), também num Ctrl-C. O commit é
montado por plumbing a partir das cópias congeladas e só avança o `main` LOCAL por compare-and-swap;
nada é pushado.

## Se um run morrer sem restaurar

Um `kill -9` ou uma queda de energia não passam pelo trap. O próximo run reconhece a forma que ficou e
imprime a rota exata: antes do commit (sentinel com `Anchor-SHA` real, `.asc` fora do HEAD ou alvos
com o patch aplicado), `git checkout --` dos três alvos e do sentinel e `rm -f` do `.asc`; depois do
commit (o `main` local já tem o commit e o índice ficou o de antes), `git reset -q --` dos cinco
caminhos, e em seguida o push.

## Medido no ensaio (2026-09-25 e 2026-09-28, antes da assinatura)

`rehearse-relmeta142.sh --sim`, em clone descartável e com chave GPG descartável sem senha, com os
três scripts e o derivador deste diretório nos bytes do commit que carrega este texto, sobre um HEAD
SIMULADO montado a partir dos tips FINAIS das lanes, na ordem e pelas unidades da esteira da manhã
(checkout por lista de caminhos, nunca merge de branch; os assuntos de commit das unidades e das
cerimônias são os reais, porque o escopo sai deles): `5c6ab5f6` com uma tag v1.4.1 FALSA; o
`.tag-push-epoch`; plano e pack do re-pin (`69b7a593`); kit da rc.1 (`31887e0f`); opção B do
`relaunch --out` (`1c94a19c`) com a seção que o `RATIFICO` acrescenta; materiais do FN-04
(`9cb92fb5`); os `.new` do re-pin aplicados como o SIGN dele os aplica; materiais da wave
(`1730312b`) e o `WOPUS55.patch` `ed3dd914…` aplicado, com a mensagem `COMMIT-MSG-OPUS55.txt`; via
expressa (`e63a4e1e`); varredura (`880300f6`) com `env-inventory-check.py --generate`, que
acrescentou exatamente os 2 nomes declarados; o `fn04.patch` `cd31657c…` aplicado como o SIGN dele o
aplica; e o CHANGELOG `[1.4.2]` e o LEDGER do tip `a03c1338` da lane de docs (a reconciliação do
FN04-C1: a classe da condição 23 declarada, não curada;
e a frase das recusas antes do piso do Claude Code corrigida — algumas vêm depois dele). Escopo derivado: `PLAN-190 / PLAN-193 (ADRs
tocados: ADR-149)`. Substrato: macOS 27.0 arm64, bash 3.2.57, gpg 2.5.18, git 2.54.0, Python 3.9.6.
Placar 48/0 nos bytes dos scripts e do derivador deste commit, com o docs `a03c1338` e o kit
`31887e0f` (2026-09-28) e, antes, com os tips anteriores dessas duas lanes (docs `62765543` e
`ba3213fa`, kit `f2cf6c6a`). Sobre a
árvore de `5c6ab5f6` as âncoras reprovaram, a do FN-04 achando os bytes do canário gravados pelo
PreToolUse (controle vermelho); sobre o HEAD simulado as sete passaram. Fora do placar, na mesma
árvore simulada (com os tips de docs `ba3213fa` e `62765543`, kit `f2cf6c6a`): treze mutações, doze derrubando
cada uma só a âncora esperada — a chamada do piso saindo 0 no `install.sh`, o piso em 2.1.279, a
comparação por texto e o `--version` parado virando recusa no `upgrade.sh`, a regra do sufixo tirada
dos dois scripts, o `install.sh` lendo a primeira linha com versão, a troca do pin gravando
`medium`, um agente passando de `claude-fable-5` a `claude-opus-5-5`, o ADR-149 sem a declaração do
despacho sem modelo próprio, o anexo prometendo uma 1.4.3, o sentinel do FN-04 sem o residual da
classe e o commit do FN-04 revertido — e a décima terceira (o anexo citando Claude Code 2.1.280 e
gpg 2.5.18) sem derrubar nenhuma; a pré-condição do CHANGELOG recusou a seção `— unreleased`; e, com
o patch aplicado e o `--yes` tirado do driver, o controle novo reprovou. No placar: a suíte do
driver passou com o patch (162 testes, 0 falhas); o `--commit` do derivador recusou um caminho fora
deste diretório no índice, nomeando a rota, e aceitou o sentinel já stageado; a forma que um SIGN
morto sem trap deixa antes do commit e a que deixa depois dele (índice velho), montadas à mão, foram
reconhecidas no run seguinte, e o comando que cada uma imprimiu devolveu a árvore ao estado certo;
`assino` digitado durante a re-derivação foi descartado e o `nao` digitado no prompt abortou sem
assinar; sem terminal, o comando do probe da v1.4.1 falhou sobre o arquivo do `mktemp` e o da v1.4.2
assinou; com `TARGET_BASE="1.4.2"`, o `bump --dry-run` reescreveu 12 arquivos e restaurou a árvore.
O escopo e os bytes do patch que você assina NÃO são os do ensaio: saem da árvore real depois dos
lands.

## Consequência DECLARADA

A partir deste commit o `release.sh` mira a v1.4.2: `preflight` exige a entrada `## [1.4.2]` do
CHANGELOG e a tag `v1.4.2-rc.1` livre; o `bump` seguinte move os sítios de versão. Não há caminho de
volta para cortar outra 1.4.1 com este driver — o que é o comportamento desejado.

## Residual

1. Nenhum oráculo prova que a prosa do título e da headline descreve o diff: as âncoras acima são, em
   sua maioria, tripwires de presença; as duas sondas de runtime provam cada uma as propriedades
   escritas ao lado dela. A leitura antes de digitar `assino` é sua.
2. As âncoras valem na árvore do `Anchor-SHA`. O MESMO texto vai depois para a anotação da tag
   `v1.4.2-rc.1` e da tag do GA, e esta cerimônia não re-roda as âncoras nesses cortes: um land
   posterior pode torná-las falsas sem que nada aqui perceba. Antes de cada corte, rode
   `python3 .claude/plans/PLAN-193/relmeta/apply-relmeta142-edits.py --repo . --claims-only` e só corte
   com rc 0.
3. A sonda do FN-04 cobre o hook do Workflow, com duas formas de `scriptPath` e sem PostToolUse. Que o
   PostToolUse da mesma chamada tira a cópia (e só ele) é o que a suíte do FN-04 prova, não esta
   cerimônia; outro hook que rode antes da decisão de permissão não é sondado.
4. A sonda do piso roda a FUNÇÃO extraída dos dois scripts e confere a forma da chamada; não roda o
   `install.sh` nem o `upgrade.sh` de ponta a ponta. O caso do `claude --version` que não termina roda
   com o limite da sonda rebaixado a 1 s: prova a FORMA da parada (aviso, sem recusa), não o valor de
   produção do bloco.
5. As âncoras do CHANGELOG são presença de palavras em subseções; o que o Claude Code apaga com
   `cleanupPeriodDays` é a medição que a entrada do CHANGELOG declara, não algo que esta cerimônia mede.
6. A âncora do `relaunch --out` é de presença (o arquivo mudou e usa `os.link`); o comportamento é o
   que a revisão da opção B e a suíte dela provaram, não esta cerimônia.
7. O gate de latência de hooks com chave relativa segue como estava: nada aqui o toca.
