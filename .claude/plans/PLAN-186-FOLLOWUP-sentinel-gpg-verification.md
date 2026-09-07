---
id: PLAN-186-FOLLOWUP-sentinel-gpg-verification
parent: PLAN-186
title: "Verificar de verdade a assinatura de um sentinel — o waiver ESTRUTURAL foi APAGADO na v4.1; este plano e a alternativa (a), se o Owner a quiser"
status: draft
created: 2026-09-04
related_commits: []
owner: CEO
depends_on: [PLAN-186]
level: L3
budget_tokens: "60-100k (1 modulo de gate + chave publica no repo + step de CI; molde = wave livre com rail, mais decisao do Owner sobre dependencia)"
budget_sessions: 1
context_risk: medium
external_wait: "decisao do Owner: instalar `gpg` no runner do CI e shipar a chave publica no repo"
eta_calendar: "1 wave, sem urgencia — a isencao ESTRUTURAL foi DELETADA nesta wave; o que resta e decidido por digest, declarado, nunca silencioso"
tags: [governanca, contaminacao, gpg, sentinel, seguranca, followup]
---

# PLAN-186-FOLLOWUP — a isencao de sentinel vira uma assinatura VERIFICADA

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** O PLAN-186 §Riscos entregou a regra `personal-path` do
> `check_contamination.py`. O pair-rail do land (round 2, achado G1, P1)
> mostrou que a isencao de sentinel era concedida por ESTRUTURA: um `.asc`
> de 4 bytes digitado a mao (`iA==`) satisfazia todo o teste e isentava
> qualquer documento ao lado dele. O Owner decidiu na S344: **marcador
> barato agora, verificacao real depois** — este followup e o "depois".
> Nao abre escopo novo. E o veiculo de UM residual declarado da regra — nao
> do unico: o cabecalho do modulo declara varios outros pontos cegos (formas
> do Windows, o slug `-home-<name>-`, dono hifenizado so na forma slug, forma
> relativa, caminho colado a uma palavra, e a fronteira INDEX-vs-WORKTREE
> abaixo). Este plano carrega TRES deles, nomeados no AC-0, no AC-6 e no AC-7.

## O estado que este followup substitui (o que landou)

**Atencao ao ler:** a funcao `is_personal_path_exempt`, citada nas versoes
anteriores deste plano, NAO EXISTE MAIS. A v4 do pacote apagou a isencao por
NOME inteira (secao seguinte).

**E o resto desta secao tambem e HISTORIA.** A v4.1 — este mesmo
pacote — apagou tambem o WAIVER `_sentinel_rule_waiver`: hoje `grep`
nao acha esse simbolo em `.claude/scripts/check_contamination.py`, e o
AC-0 abaixo registra a decisao. O que a secao descreve a seguir e o que
ESTE PATCH REMOVEU — um waiver aplicado a um achado que JA tinha sido
encontrado: ele nunca impedia a leitura de um arquivo, so perdoava o
resultado. Fica escrito porque as quatro checagens sao o argumento de
por que apagar era o certo.

Ele concedia o waiver por QUATRO checagens, todas estruturais:

1. o proprio arquivo **nao** e symlink — um link nao e documento assinado: o
   payload dele e uma string de destino que qualquer um reescreve sem tocar
   em assinatura nenhuma;
2. existe um `<file>.asc` irmao, RASTREADO pelo git e com modo `100644`
   (arquivo real, nunca symlink) — a leitura usa `O_NOFOLLOW`, entao "nao e
   link" e decidido pela mesma syscall que abre o inode;
3. o corpo e uma assinatura destacada ASCII-armored cujo payload base64
   decodifica para >= `_PGP_SIG_MIN_BYTES` (64) bytes e abre num packet tag
   de assinatura (RFC 4880 §4.2);
4. uma linha `Approved-By:` do sentinel nomeia uma fingerprint de 40 hex
   que a allowlist RASTREADA
   (`.claude/scripts/contamination-personal-path-allowlist.txt`) concede na
   linha `signer-fingerprint: <40 hex>`.

O waiver cobre o CORPO e nunca o NOME: um caminho que nomeia um diretorio de
home e inwaivavel por qualquer canal (`personal_path_verdict` checa a linha 0
acima de tudo).

**O limite honesto, que o modulo declarava antes de a v4.1 apagar o waiver:** nada nesse conjunto liga o
sidecar ao DOCUMENTO nem a fingerprint. Quem consegue escrever um arquivo
consegue copiar um `.asc` real e digitar uma fingerprint concedida. O custo
de um waiver saiu de "um NOME de arquivo" e chegou em "um corpo de
assinatura valido mais uma fingerprint que um arquivo rastreado ja nomeia" —
isso e uma barreira de REVISAO, nao uma barreira criptografica.

## Por que nao foi curado no mesmo pacote

`_lib/gpg_verify.verify_detached` ja existe
(`.claude/hooks/_lib/gpg_verify.py:232`) e e a cura correta. Ela exige o
binario `gpg` e um chaveiro com a chave publica do signatario. No runner do
CI nenhum dos dois e garantido hoje.

CORRECAO (pair-rail S344 round 4, P3): a versao anterior desta secao dizia que
a leitura fail-closed "transformaria os 75 sentinels em achados e o gate em
vermelho no ato". Isso esta ERRADO, e o proprio censo abaixo o contradiz. A
isencao de regra so e CONSULTADA depois de um hit no CORPO, e nenhum dos 75
sentinels tem hit — MEDIDO: varrer com o conjunto de signatarios e varrer com
ele VAZIO produzem o mesmo veredito (242 arquivos isentos por linha, 0 pela
regra, 0 nao isentos). Remover ou endurecer a isencao HOJE nao muda uma linha
do veredito. O custo real e futuro e de contrato: um dia um documento assinado
pode congelar um caminho de home, e e ai que a decisao pesa. Escolher entre
verificar de verdade e nao isentar continua sendo uma decisao de DESENHO do
Owner — mas pelo motivo certo, nao por um vermelho imaginario.

## O que a v4 do pacote mediu, e por que isso muda a PERGUNTA

A v3 foi DROPADA no land (`land-combined/rail-round-1.md`, P1): a isencao
por NOME de arquivo (`OWNER-*.sh`) dispensava a leitura do conteudo, entao
um symlink rastreado `docs/OWNER-leak.sh -> /Users/<owner>/repo` passava
pelo gate que reprovava `docs/plain-leak.md` com o MESMO alvo. A v4 fecha a
classe por REMOCAO: nada e isento por nome nem por sufixo, todo caminho
rastreado em escopo e lido igual, e o que sobrou virou WAIVER — aplicado a
um achado que ja existe, nunca um motivo para nao olhar.

Ao remover as isencoes, a v4 MEDIU o que cada uma valia nesta arvore:

| isencao removida ou mantida | arquivos | quantos tinham achado |
|---|---|---|
| `OWNER-*.sh` (REMOVIDA) | 54 em escopo | **0** |
| sufixo binario `_SKIP_SUFFIXES` (REMOVIDA) | 0 em escopo | **0** |
| symlinks em escopo (nunca isentos, agora lidos) | 0 | **0** |
| sentinel por 4 checagens (MANTIDA) | 75 em escopo | **0** |

Comando: `python3 .claude/scripts/check_contamination.py` mais os proprios
predicados do modulo sobre `git ls-files` (a derivacao esta na EVIDENCE do
pacote). **Nenhuma isencao que esta regra ja teve isentou um unico achado.**

Isso reformula o followup. A pergunta deixa de ser so "como verificar de
verdade" e passa a ser uma decisao de duas pontas:

**(a) VERIFICAR** — o caminho ja descrito abaixo (AC-1..AC-5): `gpg` no CI,
chave publica no repo, chaveiro efemero.

**(b) REMOVER** — apagar `_sentinel_rule_waiver`, `_is_detached_signature`,
`_sentinel_signer_fingerprint`, as constantes `_PGP_*` e a diretiva
`signer-fingerprint:`, deixando UM unico canal de waiver: a linha rastreada
com `sha256:`. Um sentinel e assinado, logo seus bytes sao congelados por
construcao — uma linha fixada no digest dele diz exatamente a mesma coisa e
nunca expira sozinha. O custo e uma linha por sentinel que tenha achado
(hoje: **zero**), e o ganho e apagar a superficie de MAIOR densidade de
defeito do pacote: dois P1 em duas rodadas de rail (`iA==` de 4 bytes
aceito; isencao pelo NOME `*-approved.md`), mais de 150 linhas de parsing de
armour PGP em um gate stdlib-only, e o unico ponto onde o modulo ainda le um
arquivo que nao e o que ele esta julgando.

A recomendacao de quem mediu e **(b)**, e a razao e a regra que este
repositorio ja pagou tres vezes: canal que nao fecha por enumeracao fecha
por REMOCAO. Manter (a) so se paga se o Owner quiser que sentinels possam
congelar caminhos pessoais sem custo de revisao — o que hoje nunca aconteceu.
A decisao e do Owner porque muda o contrato entregue ao adopter.

## AC

- [x] **AC-0 — DECIDIDO: (b) REMOVER. Feito e medido no proprio pacote
  (S345); RATIFICADO pelo Owner em 2026-09-06 (S347, item 4.2 de
  `PLAN-186/debate/owner-decisions-S347.md`, AskUserQuestion: «Ratificar
  a remoção (Recomendado)»).** O AC-0 nascera como pergunta
  aberta entre **(a) verificar** e **(b) remover**. Uma rodada de refutacao
  sobre o pacote ja curado transformou a recomendacao em ACHADO: a isencao
  nao era apenas inutil, era FORJAVEL. As quatro checagens perguntavam por
  CONTEUDO, mas o gate so as fazia de um arquivo cujo BASENAME era
  `approved.md` / `*-approved.md`, e as quatro respostas sao transplantaveis
  por quem consegue escrever um arquivo: o `.asc` se copia de qualquer outro
  sentinel (nada o liga ao documento), o corpo armado e esses mesmos bytes, e
  a fingerprint do `Approved-By` e PUBLICA — o proprio gate shipava a linha
  que a concedia. Ou seja: `docs/leak-approved.md` com um `.asc` transplantado
  era ISENTO, e os MESMOS bytes com outro nome eram achado. Isso e isencao
  por NOME fantasiada de conteudo, que e a unica classe que esta regra existe
  para remover.

  A medicao que ja estava aqui dizia o resto: 75 sentinels em escopo, ZERO
  com achado, `rule_waived = 0` — 34 dos 75 passavam nas quatro checagens e
  nenhum desses 34 tinha o que ser perdoado. Remover nao moveu nenhuma linha
  da allowlist e fechou a superficie.

  **O que a remocao levou junto (~210 linhas):** o parser de armadura PGP,
  as constantes de packet-tag e piso de tamanho, o matcher de fingerprint do
  `Approved-By`, a diretiva `signer-fingerprint:` da allowlist, o argumento
  `signers` que atravessava `scan_personal_paths` e `report_personal_paths`,
  e o campo `rule_waived` de `PersonalPathScan` — um campo sempre vazio e um
  canal esperando ser reaberto.

  **Controles, em bytes:** a forja completa (documento `*-approved.md`
  rastreado + `.asc` rastreado com corpo armado real + `Approved-By` com a
  fingerprint) da rc 1 com o caminho NOMEADO; os MESMOS bytes renomeados dao
  o mesmo rc 1 e o mesmo achado (o NOME deixou de ser variavel); e nenhum
  identificador da camada removida sobrevive no modulo. Registro da decisao:
  `CEO-DECISIONS-r5-S345.md` do pacote.

  **O que o Owner ratifica:** que nada NA REGRA `personal-path` e isento por
  nome, sufixo, extensao, diretorio, modo, presenca de sidecar ou forma de
  armadura. O escopo importa e foi estreitado depois que uma rodada de rail
  leu a frase como escrita: a Regra 1 (contaminacao por TERMO), no mesmo
  arquivo, continua com `_ALLOWLIST_EXACT`, globs de diretorio e
  `_SKIP_SUFFIXES` — uma ratificacao que dissesse "nada neste gate" seria
  assinada contra o proprio arquivo. Ratifica tambem que a
  UNICA isencao e uma linha da allowlist rastreada pinada ao sha256 do
  conteudo; e que um `signer-fingerprint:` remanescente de um adopter vira
  linha MALFORMED (rc 1, nomeada), nao uma isencao silenciosa.

  **AC-1..AC-7 continuam validos e nao foram consumidos por essa decisao.**
  O caminho (a) — verificacao real da assinatura — deixa de ser alternativa
  a (b) e passa a ser um SEGUNDO jeito de isentar, ganho por uma assinatura
  que este gate de fato verifica, AO LADO da linha pinada e nunca no lugar
  dela. Se o Owner preferir (a) mesmo assim, nada aqui bloqueia: o custo e o
  mesmo de antes, e a linha pinada continua existindo enquanto (a) nao landa.
- [ ] **AC-1** — `check_contamination.py` isenta um sentinel apenas quando
  `_lib/gpg_verify.verify_detached` VERIFICA o `.asc` contra o documento com
  a chave publica do Owner. A checagem 4 (fingerprint na allowlist rastreada)
  permanece: ela passa a decidir QUAL chave, e a verificacao decide SE a
  assinatura bate. As checagens 1, 2 e 3 viram pre-filtro barato, nao a
  decisao.
- [ ] **AC-2** — a chave publica do Owner viaja NO REPO, em caminho rastreado
  e nomeado pelo modulo (nao um chaveiro do ambiente), e o `verify_detached`
  roda contra um chaveiro EFEMERO montado a partir dela — nunca contra o
  `~/.gnupg` de quem executa, que e estado do operador e nao do repositorio.
- [ ] **AC-3** — `gpg` passa a ser DEPENDENCIA declarada do gate: instalado
  no job de CI que roda o `check_contamination.py`, registrado no `SBOM.md`
  como dependencia de FERRAMENTA (o runtime segue stdlib-only), e ausencia
  do binario e rc 2 fail-closed com razao nomeada — nunca uma isencao
  concedida em silencio por falta de ferramenta.
- [ ] **AC-4** — MEDIDO na arvore: TODOS os sentinels em escopo ficam VERDES
  sob a verificacao real (cada `.asc` verifica contra o seu documento), e o
  numero de sentinels isentos ANTES e DEPOIS e reportado lado a lado. O
  conjunto e DERIVADO DO DISCO pelo proprio script do AC — nunca um numero
  digitado a mao, que envelhece em silencio e deixa o sentinel a mais sem
  verificar (pair-rail round 2, P2: este AC dizia `74` enquanto o censo do
  modulo e o disco diziam **75**). No corte deste followup o disco responde
  `75 sentinels em escopo, 75 com sidecar .asc, 0 sem`; o AC fecha com o
  numero que o disco der no dia, junto do comando que o produziu. Um
  sentinel que nao verifica e um achado nomeado, com decisao registrada:
  cura, linha de allowlist com razao, ou re-assinatura.
- [ ] **AC-5** — controle POSITIVO em bytes: (a) o `.asc` de 4 bytes que
  passava na v3 e RECUSADO; (b) um `.asc` real de OUTRO sentinel copiado ao
  lado deste documento e RECUSADO (e o furo que a v3 declara e que so a
  verificacao fecha); (c) um sentinel real com o seu `.asc` real e ACEITO.
  Cada controle roda como o CI roda, nao como fixture.

- [ ] **AC-6** — a fronteira INDEX-vs-WORKTREE fica DECIDIDA. Hoje a regra
  ENUMERA o indice do git (`git ls-files`) e LE o worktree, entao um blob que
  vaza, colocado no indice e depois sobrescrito ou apagado no worktree, nao e
  varrido — e `git commit` landa o vazamento. Pela mesma razao, uma linha da
  allowlist fixa os bytes do WORKTREE, que nao sao necessariamente os bytes
  que vao ser landados. (Pair-rail S344 round 1, P1, nas duas lanes; e
  comportamento PRE-EXISTENTE da RULE 1 e do `FileWalker`, nao introduzido
  pela regra nova; na CI, onde este gate roda, indice e worktree sao a mesma
  arvore por construcao.) A wave decide entre: (a) ler os blobs por
  `git cat-file --batch`, o que muda o SIGNIFICADO de todo digest ja shipado
  na allowlist e exige regenera-la; (b) recusar rodar quando
  `git diff --quiet` falha, transformando a divergencia em rc 2
  nomeado — `--quiet` SEM `--cached`, porque `--cached` compara o indice
  com o HEAD e a fronteira declarada aqui e indice contra WORKTREE
  (medido no proprio pack: `--cached` devolve 1 e o simples devolve 0 na
  mesma arvore); ou (c) declarar a fronteira como definitiva e documenta-la no
  contrato entregue ao adopter. Medir antes de escolher: quantas invocacoes
  reais rodam sobre uma arvore com indice divergente.
- [ ] **AC-7** — a RULE 1 (a regra de TERMOS) ganha a mesma asserção de
  enumeracao que a RULE 2 tem. `FileWalker` converte falha ou timeout do
  `git ls-files` em iteracao VAZIA (`_lib/file_walker.py:80-93`), e a RULE 2
  hoje recusa uma varredura cujo CONJUNTO de caminhos vistos nao COBRE o
  indice — a RULE 1 nao tem checagem nenhuma, entao uma falha transitoria na
  primeira caminhada devolve "sem contaminacao" sobre zero arquivos (pair-rail
  S344 round 2, P1). A cura e a mesma comparacao, no mesmo lugar. **Nao e uma
  CONTAGEM** (pair-rail S344 round 4, P3): a versao anterior deste AC dizia
  "viu menos arquivos" e "a mesma contagem", e o round 3 provou que contar e
  insuficiente — uma caminhada que entrega um caminho duas vezes e omite outro
  tem a contagem certa e a cobertura errada. Implementar este AC pela letra
  antiga reproduziria exatamente esse falso-verde. Nao entrou no pacote livre
  porque `scan()` e a superficie da regra ANTIGA e mudar o seu contrato de
  retorno pede a bateria dela inteira.

## Check

- `python3 .claude/scripts/check_contamination.py` rc 0 na arvore, com a
  contagem de isentos impressa e comparada com a da v3;
- suite `.claude/scripts/tests/test_check_contamination_personal_path.py`
  verde, incluindo os tres controles do AC-5;
- job de CI que roda o gate exibe o `gpg --version` que usou;
- `_lib/gpg_verify` sem novo consumidor fora deste modulo.

## Riscos

- **PREMISSA REMOVIDA: a legibilidade da allowlist no `git diff` NAO e uma
  propriedade de seguranca desta regra.** Quatro rodadas de pair-rail
  (18 a 21) defenderam a premissa contraria — «uma isencao so vale se um
  humano puder LE-LA no diff» — e cada rodada a derrubou por um canal que a
  cura anterior nao tinha enumerado: um NUL nos bytes, um `.gitattributes`
  com `-diff`, um driver de diff NOMEADO como binario e, por fim, um driver
  chamado literalmente `unspecified` (e `core.bigFileThreshold=1`, sem
  atributo nenhum). Toda cura dessas decidia por um NOME, que e exatamente o
  que esta regra existe para nao fazer. A decisao do Owner foi REMOVER a
  camada: o gate nao pergunta mais ao git como o arquivo e renderizado.
  Em troca ele IMPRIME, em toda execucao, o conjunto de linhas que HONROU
  (`<path> | sha256:<64 hex> | <reason>`, uma por linha, ordenado por path,
  sem cap) e um digest sobre esse conjunto. Uma isencao que concede alguma
  coisa fica visivel no log da execucao que concedeu, independentemente do
  que o git mostra. O controle que sustenta a isencao continua sendo o
  mesmo e unico: a linha fixada ao sha256 do conteudo. O que NAO esta
  fechado: quem controla o repositorio pode tornar o arquivo ilegivel no
  diff — isso deixou de importar para o veredito, mas continua sendo
  verdade, e esta escrito aqui em vez de implicito.
- **A razao de uma linha e julgada por um predicado POSITIVO.** Depois de
  NFKC, ela precisa carregar ao menos oito caracteres `[A-Za-z0-9]` e ser
  inteiramente imprimivel; qualquer outra coisa e MALFORMED por numero de
  linha. A forma anterior era uma lista de categorias proibidas (`Cf`, `Cc`,
  `Mn`) e foi derrotada tres rodadas seguidas, a ultima por preenchedores
  `Lo`/`So` (U+3164, U+2800) que «carregam tinta» por categoria e nao
  renderizam nada. Uma classe fechada por enumeracao reabre no proximo
  membro; um predicado positivo nao tem proximo membro.
- **O matcher e linear e tem prazo.** `(?<![\w.~])/+` reiniciava em cada
  barra de uma sequencia: 16 000 barras levavam 1,833 s. A cura consome UMA
  barra sob lookbehind de largura fixa — mesma resposta, verificada como
  diferencial sobre todos os arquivos em escopo — e a varredura por arquivo
  carrega um prazo (`_PERSONAL_PATH_FILE_BUDGET_S`) que RECUSA o arquivo
  (rc 2) em vez de rodar sem fim.

- **A allowlist do adopter nao sobrevive a um upgrade — RESIDUAL DECLARADO,
  fora do alcance deste pack.** O `install.sh` entrega `.claude/scripts/`
  pelo glob `*.sh *.py *.yaml`: `.txt` nao esta nele, entao a allowlist
  shipada NAO chega ao adopter e o arquivo dele nasce dele. Ate ai o
  comportamento e o desejado (sem arquivo, a regra le a lista como VAZIA e
  nada e isento — fail-closed). O problema e o passo seguinte: o
  `upgrade.sh` roda `backup_and_replace ".claude/scripts"`, e o ramo
  FALLBACK — o que vale exatamente para um arquivo sem baseline, que e o
  caso desta allowlist — sobrescreve, deixando backup. O aviso e
  CONDICIONAL: `DIFF_WARN` nasce 1 e `--no-diff-warn`, documentada, o
  desliga — entao no caminho padrao o adopter e avisado e num caminho
  documentado nao e. As linhas que o adopter escreveu para isentar um
  artefato congelado local somem no upgrade seguinte e o gate volta a
  acusar aquele arquivo. E o upgrade e tambem COMO a allowlist do
  framework chega ao adopter: o installer nao a entrega, o upgrade
  entrega por cima. A cura fica em `install.sh`/`upgrade.sh`, que sao caminhos
  canonicos e so entram por cerimonia GPG; este pack e livre e nao os toca.
  O que ele pode fazer com honestidade e o que esta escrito aqui: DECLARAR
  o residual onde o adopter e o Owner leem, em vez de deixa-lo num registro
  de rail que nunca aterrissa. Ate a cura, a operacao correta apos um
  upgrade e reaplicar as proprias linhas a partir do backup que o
  `upgrade.sh` guarda.
- **Marcadores de comando de workflow dentro de uma razao — RESIDUAL
  DECLARADO, a cura fica num caminho canonico.** A razao de uma linha
  honrada e impressa como foi escrita (controles sao escapados; `#`, `[`,
  `]` e `:` sao imprimiveis e sobrevivem). Duas rodadas de rail apontaram
  que um runner do GitHub Actions pode interpretar um marcador de comando
  no meio dessa linha — `::add-mask::<path>` na rodada 23 e a forma legada
  `##[add-mask]<path>` na rodada 25 — e mascarar aquele path nas linhas
  seguintes do log, que e justamente onde a isencao passou a ser visivel.
  O que foi MEDIDO nesta maquina: a razao aparece literal e o bloco de
  linhas honradas e INDENTADO, entao o marcador nunca chega ao inicio de
  uma linha; a rodada 12 desta mesma regra so virou achado porque uma
  quebra de linha punha o marcador no inicio, e por isso a quebra e
  escapada ate hoje. O que NAO pode ser medido aqui: como cada parser do
  runner trata um marcador no meio da linha. Nao ha runner nesta maquina,
  entao o pack DECLARA em vez de descartar. A cura robusta e suspender o
  processamento de comandos em volta do passo (`::stop-commands::`) em
  `.github/workflows/validate.yml` — canonico, cerimonia GPG, fora de um
  pack livre; hoje esse arquivo nao tem nenhuma ocorrencia de
  `stop-commands`. Enumerar marcadores dentro do modulo seria repetir
  exatamente o movimento que as rodadas 18 a 21 provaram nao fechar canal:
  cada enumeracao caiu na grafia seguinte. Enquanto a cura nao entra, o
  numero de linhas honradas e o digest do conjunto continuam sendo
  calculados pelo gate e impressos no mesmo bloco, de modo que um leitor
  compara o conjunto mesmo que um path apareca mascarado.
- **Adopter sem `gpg`.** O gate e entregue ao adopter. Um checkout de adopter
  nao tem sentinels do framework, entao a checagem nunca dispara — mas o rc 2
  por binario ausente dispararia. A wave decide isso explicitamente: ou o
  fail-closed vale so quando existe um sentinel a julgar, ou a dependencia e
  declarada como requisito de instalacao. Medir antes de escolher.
- **A allowlist de fingerprints e a chave publica sao dois artefatos que
  podem divergir.** A wave verifica que toda fingerprint concedida existe na
  chave shipada, senao a linha e uma concessao para uma chave que ninguem tem.
- **A raiz do caminho de home casa sem distinguir maiusculas.** Sao DUAS
  classes de equivalencia, nao uma: `/Users/`, `/users/` e `/USERS/` nomeiam
  o mesmo diretorio num volume case-insensitive, e `/home/`, `/Home/` e
  `/HOME/` nomeiam outro. Decidir por GRAFIA dentro de cada classe era a
  falha que esta regra existe para remover. So o TOKEN DA RAIZ dobra — o segmento
  do dono e a lista de placeholders sao comparados como antes — e a dobra foi
  MEDIDA sobre os 2190 arquivos em escopo deste repositorio antes de shipar:
  move ZERO linhas.
