---
id: PLAN-188
title: "Cerimônia compartilhada — scripts de assinatura e land por manifesto"
status: draft
created: 2026-09-05
owner: CEO
depends_on: [PLAN-186]
level: L3
tags: [cerimonia, assinatura, land, manifesto, rail, governanca]
---

# PLAN-188 — Cerimônia compartilhada (SIGN / LAND / finalize / harness por manifesto)

> **Nível L3 — debate antes de executar.** Os scripts são o GATE da assinatura
> do Owner: um defeito neles não é um bug de produto, é uma assinatura sobre o
> conteúdo errado. `/debate start PLAN-188 "<proposta>"` precede qualquer wave.
>
> **Dependência declarada:** PLAN-186 (`status: executing`) — o piloto do AC-2
> é o pacote W6a, um pacote DESSE plano; por isso `depends_on: [PLAN-186]`
> (round 1, K8; grafo de dependências em `PLAN-SCHEMA.md:462-470`).
>
> **Relacionados (leitura, não dependência):** PLAN-185, PLAN-183,
> ADR-010 (sentinel de edição canônica — é ELE que
> define o contrato `Scope:` + `check_canonical_edit.py` que este toolkit
> consome; o rascunho atribuía esse contrato ao ADR-031 e a OQ-1 registra a
> correção — o ADR-031 é «Self-improving skills» e está FORA do escopo deste
> toolkit),
> ADR-192 (manifesto de scripts de gate).

## Context

Cada pacote canônico carrega os próprios `OWNER-*-SIGN.sh`, `OWNER-*-LAND.sh`,
`finalize-*.sh` e `test-ceremony-scripts-*.sh`, clonados de um molde. O rail
de pares (codex) revisa cada clone e encontra as MESMAS classes em cada um:

| Classe (achada pelo rail; packs onde apareceu) | Packs | Consequência se assinado |
|---|---|---|
| SIGN gateia UMA família de rail (`RAIL_GLOB=rail-round-*`) | p169, w-rota | um registro de MATERIAIS `REJECT` não pára a assinatura |
| Trailer `Pair-Rail-Reviewed:` checado só como «não TO-FILL» (w6: só o índice MÁXIMO) | todos | commit reivindica 25 rodadas com 23 registros |
| Path absoluto pessoal em material assinado, sem guard em SIGN/LAND/harness | w4b (1 hit) | home do mantenedor commitado e assinado |
| Runner de controles que não roda de onde landa; instrumento que lê a prosa, não o runner | w4b | citações provadas por cópia cujo gêmeo committed está quebrado |
| Baseline (`EXPECTED-BASELINE`) editado à mão depois do finalize | w4b | finalize abortaria na assinatura; «bateria antes da última edição» |
| Escopo do sentinel digitado, diferente do diff | w6 | Owner assina escopo menor que o diff |
| Harness planta `Rail-Verdict: APPROVE` sintético | p169, w1, w4b, w6 | verde do harness lido como evidência de rail |

A coluna «Packs» lista os pacotes onde o rail nomeou a classe: três linhas
nomeiam dois ou mais pacotes, quatro nomeiam um só (as três de `w4b` e a de
`w6`). Uma classe vista em UM pacote entra na tabela porque o custo de
assinatura é o mesmo em qualquer clone, não porque já tenha repetido.

A cifra «25 rodadas com 23 registros» da linha 2 tem fonte, e ela é datada
(o conjunto de registros mudou depois): no pacote `w6-adapter`, o trailer
`Pair-Rail-Reviewed` afirmava «SUJEITO rodadas 1-14, MATERIAIS rodadas 1-11»
(14 + 11 = 25) enquanto `rail-round-12.md` e `rail-materials-round-9.md` não
existiam (13 + 10 = 23) — apurado em `rail-materials-round-12.md` daquele
pacote e em `STATE.md` F16. Os dois registros ausentes foram escritos depois,
então HOJE o conjunto está completo; o que a linha mede é o instante em que o
trailer teria entrado num commit assinado. Os pacotes citados na tabela ficam
fora do repo (área de trabalho da noite S345), por isso a cifra viaja com a
sua apuração, não com um comando reproduzível num checkout.

**Fração medida (medição S345).** Instrumento e saída viajam RASTREADOS com
este plano: `.claude/plans/PLAN-188/measure-rail-classes-v2.py` (o comando) e
`.claude/plans/PLAN-188/s345-rail-classes.txt` (a saída congelada). O arquivo
rastreado É a reprodução integral dessa saída; a evidência da wave mostra as
últimas 20 linhas dele. O bloco abaixo é o começo dessa saída.
Snapshot congelado da noite de 04→05/09/2026, corpus de
**528 blocos de achado em 168 registros de rail de 12 pacotes**:

```
ALL findings by class:      docs 132 25.0% | ceremony 122 23.1% | unknown 102 19.3%
                            instrument 63 11.9% | product 62 11.7% | ...
HIGH (P0/P1/BLOCKER/HIGH) by class: total=215
                            ceremony 60 27.9% | unknown 58 27.0% | docs 45 20.9% | product 28 13.0%
```

Ou seja: **cerimônia é 23,1 % de todos os achados de rail da noite e 27,9 %
dos de alta severidade** — a maior classe entre as de severidade alta —,
contra 25,0 % da classe `docs` e 11,7 % da classe `product`. As classes são as
do classificador do instrumento (por path e por palavra-chave); ele não julga
se o texto foi escrito à mão. O rascunho desta wave citava 22 % de uma execução
ANTERIOR do mesmo comando, na mesma noite (o closeout `e6b270c` registra
«medição das classes de rail 25/22/12/11 %»; a fração de ALTA severidade
daquela execução não ficou registrada em lugar nenhum). A medição é um SNAPSHOT:
o comando roda sobre os pacotes da noite S345 e o corpus cresce enquanto a
noite corre — a saída congelada acima é a fonte desta seção.

Cada pacote paga o rail de materiais do zero: em w6 o índice de rodada de
materiais chegou a 12 e em p169 a 11 (índices MÁXIMOS dos registros
`rail-materials-round-*.md`; NO INSTANTE MEDIDO da noite S345 a contagem de
registros EXISTENTES era menor que esses indices — exatamente a classe
«teto ≠ conjunto» da linha 2 da tabela. A nota da tabela acima registra que os
dois registros ausentes foram escritos depois, entao o conjunto daquele pacote
esta completo HOJE: o que estas cifras medem e o instante, nao o estado atual).
Para uma CONTAGEM,
rode `ls <pack>/rail-materials-round-*.md | wc -l` e cite o comando ao lado do
número.

## Goal

Que a assinatura do Owner passe por UM conjunto rastreado de scripts de
cerimônia, parametrizado por um manifesto por pacote, de modo que cada classe
de defeito da tabela acima seja fechada UMA vez, com controle vermelho, em vez
de ser reencontrada pelo rail em cada clone.

## Approach

UM conjunto rastreado de scripts em `.claude/scripts/ceremony/`
(`sign.sh`, `land.sh`, `finalize.sh`, `harness.sh`, `lib.sh`), parametrizado
por um manifesto por pacote, `ceremony.tsv`, gerado pelo derivador.

### O ENDEREÇO é decisão de gate, não de arrumação (round 1, C1)

Verificado no HEAD: `.claude/scripts/check-ceremony-script.py:62-65` define
`DISCOVERY_ROOTS = [".claude/plans", ".claude/scripts/local/historical"]` e
`:66-68` define `EXPLICIT_FILES = [".claude/scripts/local/generate-ceremony.sh"]`;
`.github/workflows/ceremony-lint.yml:6-11` (push) e `:13-18` (pull_request)
disparam só por `.claude/plans/**/*.sh` mais QUATRO arquivos explícitos
(o gerador, o próprio checador, o `ceremony-lint-waivers.json` e o workflow).
`.claude/scripts/ceremony/` não está em nenhum dos dois — e o diretório ainda
não existe. Sem cura, o script que passa a SER o gate da assinatura nasce isento
das cinco classes BLOQUEANTES do próprio lint (R1 proveniência, R2 `|| true` em
operação irreversível, R3 `grep … | tail` em parsing de VERDICT, R4 `git add` de
diretório, R8 exec-bit no índice): falso-verde por endereço.

**Decisão:** o endereço fica, e a W0 entrega no MESMO patch os TRÊS sítios que
fazem o lint valer para o toolkit: (a) a entrada em `DISCOVERY_ROOTS`; (b) o
`paths:` dos DOIS gatilhos do `ceremony-lint.yml` (uma sem a outra dá lint que
nunca roda, ou gatilho que não descobre nada); e (c) o ALARGAMENTO da regra R8,
que hoje é escopada a `.claude/plans/` — `if git_mode == "100755" and
rel.startswith(".claude/plans/")`,
`.claude/scripts/check-ceremony-script.py:194` —, e sem a qual o toolkit
descoberto herdaria QUATRO das cinco classes bloqueantes (R1-R4), não cinco.
DOIS controles POSITIVOS: um script do toolkit com `|| true` numa linha de `gpg`
tem de REPROVAR (R2), e um script do toolkit com exec-bit no índice tem de
REPROVAR (R8). Nota de risco (round 1, K10):
`.github/workflows/validate.yml:354` já exclui
`.claude/scripts/owner-ceremony/archive/*` do shellcheck e
`.claude/scripts/owner-ceremony/` não existe — um nome de diretório vizinho já
tirou scripts de um gate uma vez, e a exclusão morta ficou.

### O FORMATO do manifesto é decidido ANTES da W0 (round 1, C3)

Medido nesta máquina: `python3 -V` = `Python 3.9.6` e
`python3 -c "import tomllib"` = `ModuleNotFoundError` — `tomllib` é 3.11+ e o
piso declarado em `CLAUDE.md` §4 é stdlib-only, ≥ 3.9. TOML sai; a OQ-3 deixa de
ser pergunta aberta e vira PRÉ-CONDIÇÃO da W0, porque é ela que decide se o
ponto onde o Owner assina parseia entrada com regex de shell — a camada mais
fraca — contra a doutrina fail-CLOSED de `CLAUDE.md` §4.

**Decisão:** TSV no molde de `scripts/delivery-routes.tsv` (precedente vivo com
três leitores, PLAN-183 W5), lido por UM leitor em Python que o `sign.sh`
invoca — nunca por regex de shell. Uma linha por chave, `TAB` como separador,
`#` inicia comentário, listas separadas por `,` sem espaço:

```tsv
# ceremony.tsv — manifesto do pacote. UMA fonte; o leitor é python3.
key	w6a
plan	PLAN-186
anchor	<sha do HEAD que o Owner assina>
paths	.claude/hooks/_lib/adapters/live/claude.py,...
sentinel	.claude/plans/PLAN-186/wave-s345-w6a-approved.md
rail_subject	rail-round-1.md:<sha256>,...
rail_materials	rail-materials-round-1.md:<sha256>,...
baseline	s345-ceremony-w6a/EXPECTED-BASELINE.txt
scope_generated_from	apply-w6a.py --describe
```

O leitor nasce fail-CLOSED em falha de parse de INPUT, com o conjunto de
RECUSAS NOMEADAS entregue pela W0, cada uma com controle vermelho: chave
desconhecida, chave duplicada, chave obrigatória ausente, valor multi-linha,
`TAB` dentro de valor, path absoluto em `paths`, arquivo com `CRLF`. Nenhuma
recusa é `|| true`. O `baseline` continua escrito SÓ pelo `finalize`, e o
`rail_subject`/`rail_materials` carregam o sha256 de cada registro
(invariante 1).

### A chave `scope_generated_from` só existe se o contrato existir

Ela nomeia `apply-<key>.py --describe`, e **nenhum derivador rastreado
implementa `--describe` hoje**. **Decisão:** o contrato `--describe` — imprimir
as ops por path, em forma estável, sem escrever nada — é ENTREGA da W0,
especificado ali e exigido do derivador de cada pacote migrado; se a W0 não o
entregar, a chave sai do manifesto — **mas a invariante 5 NÃO cai**: nesse
braço o `finalize.sh` GERA o arquivo de escopo a partir das ops do derivador e o
`sign.sh` regenera e compara byte a byte, exatamente como faz com o
`EXPECTED-BASELINE` (invariante 4). O que a wave nunca faz é (a) manter no
manifesto uma chave que aponta para um comando inexistente, nem (b) trocar
«escopo GERADO e conferido» por «escopo digitado». A W0 entrega um dos dois
braços, e o AC-1 exige o controle vermelho do braço entregue. Qual dos dois:
OQ-7.

### Reconciliação com `generate-ceremony.sh` (round 1, K1)

Já existe dono para «nunca escreva uma cerimônia à mão»:
`.claude/scripts/local/generate-ceremony.sh:6-7` diz que substitui escrever
`OWNER-CEREMONY.sh` do zero (entrega do PLAN-073 §2) e `:19-30` traz seis guards
pré-emissão G1-G6, dos quais G1 («cada `--canonical-paths` casa um padrão de
`_CANONICAL_GUARDS`») e G6 («o sentinel declara TODOS os paths») são parentes
diretos das invariantes 5 e 6 propostas aqui. Ignorar isso é a FORMA exata dos
defeitos D1-D4 (S322-S327): a ORIGEM tinha dono, a ROTA não.

**Decisão: ABSORVER.** O toolkit passa a ser o único produtor de cerimônia e o
`generate-ceremony.sh` é aposentado na subwave que migrar o último pacote que
depende dele. **Oráculo mecânico da escolha:** no MESMO patch em que ele sai,
`EXPLICIT_FILES` do `check-ceremony-script.py` e o `paths:` do
`ceremony-lint.yml` deixam de citá-lo, e um teste afirma que o repo tem UM
gerador de cerimônia. Enquanto os dois coexistirem, a fronteira é escrita:
`generate-ceremony.sh` serve pacotes NÃO migrados; nenhum pacote novo nasce
nele.

**Aposentar não é apagar: os CONSUMIDORES vivos entram na mesma subwave.** Dois
estão nomeados e verificados no HEAD — `.claude/scripts/local/tests/test_generate_ceremony.sh:21`
fixa `GEN="$REPO_ROOT/.claude/scripts/local/generate-ceremony.sh"` e exercita o
gerador em toda a suíte; e o `PLAN-174:98` ainda agenda uma W3 que ESTENDE o
gerador para cortes rc/GA. Remover o comando sem tratá-los quebra uma suíte de
regressão e deixa uma wave planejada apontando para um arquivo que não existe.
Portanto a subwave da aposentadoria (a) migra ou aposenta essa suíte junto, e
(b) exige uma decisão registrada sobre a W3 do PLAN-174 — transferir a
responsabilidade para o toolkit ou manter o gerador até ela fechar. Antes disso,
o `generate-ceremony.sh` não sai.

Invariantes fechadas UMA vez, com controle vermelho cada:
1. Gate das DUAS famílias de rail: o registro LISTADO de maior número de cada
   família lê exatamente `Rail-Verdict: APPROVE`; registro em disco fora da
   lista ⇒ recusa nomeada. Os registros entram no manifesto PINADOS por sha256
   gravado pelo `finalize` — mesma forma do `EXPECTED-BASELINE` da invariante 4
   —, nunca por nome (round 1, K3): nome sozinho deixa o arquivo mutável depois
   de listado. **Residual escrito:** o rail é ADVISORY e este gate mede
   PROVENIÊNCIA (o registro que o SIGN leu é o registro que o rail produziu),
   não a verdade do veredito.
2. Trailer de proveniência GERADO do conjunto de registros; `land.sh` compara
   CONJUNTOS nos dois sentidos.
3. Guard de path absoluto fora do repo em qualquer material, em `sign.sh` P0,
   no finalize e no harness; o guard se auto-escaneia. **A exceção do self-test
   NÃO é um literal de máquina** (round 1, C7): a regra publicada não conhece
   UID nenhum — o próprio self-test injeta um MARCADOR (variável de ambiente do
   harness, ou sentinela de conteúdo no fixture) e o guard isenta o MARCADOR,
   não um path. O rascunho isentava por regex o glob real de scratchpad desta
   máquina: um material assinado colocado sob ela passaria. Controle vermelho:
   material sob essa árvore, sem o marcador, tem de REPROVAR.
4. `EXPECTED-BASELINE` e `BASE-SHA` escritos SÓ pelo finalize; `sign.sh`
   regenera e compara byte a byte (edição manual ⇒ recusa).
5. Escopo do sentinel e `PROPOSED-PATCH` GERADOS das ops por path, nunca
   digitados; `sign.sh` regenera e compara byte a byte. **A verificação é
   INCONDICIONAL** — o que a OQ-7 escolhe é o BRAÇO, não a dispensa: (a) com a
   chave `scope_generated_from`, o gerador é `apply-<key>.py --describe`; (b)
   sem ela, o `finalize.sh` grava o arquivo de escopo a partir das ops e o
   `sign.sh` compara contra ele. Um pacote sem NENHUM dos dois braços é recusa
   nomeada — é o mesmo controle que o `generate-ceremony.sh` já faz no guard G6
   («o sentinel declara TODOS os paths»).
6. `land.sh` liga o `NEW_SHA` empurrado ao índice aprovado (parent, conjunto
   de paths, blob ids e modos, mensagem byte-igual), verifica a TREE antes do
   push e pina o push ao `NEW_SHA` **e ao DESTINO**: remoto e refspec nomeados,
   e `core.hooksPath` verificado (round 1, K9) — um push pinado ao sha CERTO
   para o remoto ERRADO entrega o conteúdo assinado no lugar errado.
7. Runner de controles auto-resolvente (`git rev-parse --git-dir`, funciona
   em worktree) e EXECUTADO pelo harness a partir da posição landada.
8. Harness NUNCA planta `APPROVE`: copia os registros reais; sem APPROVE, o
   verde esperado é «SIGN recusa».
9. Liveness de rodada de rail — **ADVISORY na W0 e na W1** (round 1, K5). A
   forma que esta invariante testava não existe mais: `CLAUDE.md:108` registra
   que «o rail codex corrente NÃO emite `VERDICT:` (rodada limpa = ausência do
   bloco `Full review comments:`)». Contra a forma ATUAL, os sinais disponíveis
   são o cabeçalho `model:` da própria saída, o bloco final
   `Full review comments:` (ou uma afirmação explícita de ausência de defeito
   acionável) e, para rodada de texto com brief em stdin, a linha `tokens used`.
   Enquanto essas âncoras forem propriedade do CLI de um terceiro, a invariante
   INFORMA e nunca recusa; a promoção a BLOQUEANTE é decisão registrada quando
   existir âncora estável, não drift.
10. **Verificação de SIGNATÁRIO** (round 1, K2 — o único achado do round que
    SUBTRAI segurança se for esquecido): o `.asc` do sentinel é verificado
    contra a allowlist de impressões digitais `.claude/sentinel-signers.txt`
    (ADR-010 / PLAN-045 P0-01; o próprio arquivo declara fail-CLOSED em
    allowlist vazia). Medido no HEAD, **33 dos 48** `OWNER-*` de assinatura e
    land rastreados já fazem esse controle
    (`grep -l sentinel-signers $(git ls-files | grep -E 'OWNER-.*(SIGN|LAND).*\.sh$') | wc -l`
    = 33; denominador pelo mesmo `git ls-files | grep -cE` = 48): tomar as nove
    invariantes anteriores como ESPECIFICAÇÃO removeria esse controle — o que
    responde «foi a chave do Owner?» — de **33 SCRIPTS** (a unidade que o
    comando conta; quantos PACOTES eles cobrem é outro censo, não feito aqui).
    Controle vermelho: `.asc` de chave fora da allowlist ⇒ recusa nomeada.

### Riscos e o que NÃO muda

- Os scripts são GATE de assinatura ⇒ a wave é L3: debate antes de executar.
  **Bootstrap da primeira assinatura (round 1, C5/C6) — escrito como FATO do
  plano, não como nota de rodapé:** o toolkit não pode assinar a si mesmo. A W0
  e a W1 landam por cerimônia CLONADA — são DUAS «à moda antiga», pela razão
  medida no bullet seguinte —, e é o `land.sh` do toolkit que vale a partir do
  pacote seguinte à W1.
- **A razão «oráculo 0 até serem referenciados por SIGN» era falsa por
  construção e sai do plano.** Medido: o oráculo responde
  `.claude/scripts/ceremony/sign.sh	0` porque `_CANONICAL_GUARDS`
  (`.claude/hooks/check_canonical_edit.py:115`) é lista ESTÁTICA por path e não
  tem prefixo `ceremony/` — logo a resposta **não muda** quando a W1 referenciar
  o arquivo (C5/C6). Só que a conclusão que o rascunho tirava dela também cai:
  **a W0 é CANÔNICA**, porque a cura do C1 obriga o `paths:` do
  `ceremony-lint.yml` a viajar no MESMO patch, e o oráculo responde
  `.github/workflows/ceremony-lint.yml	1`. Ou seja, são DOIS lands «à moda
  antiga» por cerimônia clonada — a W0 e a W1 —, não um. O toolkit passa a valer
  a partir do pacote seguinte à W1.
- **Cadeia de autoridade do próprio toolkit (round 1, C5).** Hoje
  `.claude/governance/gate-scripts-manifest.txt` pina **9** scripts de gate por
  sha256 (`verify-counts.sh`, `validate-governance.sh`, `release.sh`,
  `_release_tag_guard.py`, `validate-pair-rail-verdict.py`, …;
  `grep -cve '^#' -e '^$' .claude/governance/gate-scripts-manifest.txt` = 9), e
  o toolkit entraria editável sem sentinel e sem checksum — enquanto o
  `verify-counts.sh`, que só conta, tem os dois. A membresia ADR-192 vira AC
  próprio (AC-6); a entrada em `_CANONICAL_GUARDS` é decisão explícita da OQ-6.
  **O que a OQ-6 decide é a proteção DIRETA pelo hook, não a liberdade das waves
  futuras:** a partir do AC-6, mexer num script pinado obriga a atualizar o
  manifesto — que o oráculo já responde `1` — e o step de integridade do
  `smoke-install.yml` (`.github/workflows/smoke-install.yml:355-360`,
  `shasum -a 256 -c` sobre o manifesto) reprova se o hash não bater.
  **Esse step só dispara se o `paths:` do workflow casar o toolkit — e hoje NÃO
  casa:** verificado no HEAD, nenhuma das duas listas (`pull_request` e `push`)
  menciona `.claude/scripts/ceremony/**` ou
  `.claude/governance/gate-scripts-manifest.txt`, então um PR que toca SÓ o
  toolkit nunca roda o step, e a promessa «toda edição do toolkit custa uma
  assinatura» seria falsa. Por isso a W0 acrescenta as DUAS entradas nas DUAS
  listas do `smoke-install.yml` — QUARTO sítio do mesmo patch, ao lado dos três
  sítios de lint —, com controle POSITIVO: um PR que toca só um arquivo do
  toolkit tem de EXECUTAR o step de integridade. Com esse quarto sítio no lugar,
  e só com ele, um toolkit alterado fora de cerimônia fica VISÍVEL: o CI reprova
  no PR seguinte.
  **O que isso NÃO faz — limite declarado, não nota de rodapé:** a verificação
  do ADR-192 é de CI. O próprio ADR a define como «`shasum -a 256 -c`,
  fail-closed e ANTES de qualquer membro ser invocado, em **4 superfícies**»
  (`ADR-192:49-53`) — e as quatro são workflows (`release.yml`,
  `smoke-install.yml`, `ownership-nightly.yml`, `npm-publish.yml`). Não existe
  lançador LOCAL que confira o hash antes de executar, então o Owner pode
  assinar com um `sign.sh` já modificado na própria árvore e o CI só reprova
  DEPOIS: isto é DETECÇÃO post-hoc, não prevenção. Quem fecharia a janela no ato
  da edição é exatamente a entrada em `_CANONICAL_GUARDS` — a OQ-6. Enquanto ela
  estiver aberta, este plano ASSUME o limite e o escreve; o que não faz é
  afirmar que a membresia no manifesto torna a proteção direta dispensável.
- O formato do sentinel assinado (ADR-010) não muda: o toolkit consome o mesmo
  `.asc`. O `check_canonical_edit.py` só muda se a OQ-6 mandar — a entrada dos
  scripts do toolkit em `_CANONICAL_GUARDS` é decisão do Owner, e enquanto ela
  estiver aberta este plano não edita esse arquivo. (O rascunho afirmava «nada
  muda» de forma incondicional, o que contradizia a própria OQ-6.)
- Pacotes já em voo terminam nos scripts clonados COM as notas de classe
  aplicadas; a migração é por manifesto, sem re-derivar o patch.

## Items

Cada unidade traz **file assignment**, **critério de aceite** e **hint de
mensagem de commit**, como `PLAN-SCHEMA.md:441` exige; e cada uma DECLARA o
corte do modelo de operação v2 (≤ 400 linhas alteradas OU ≤ 8 paths por
pacote), que o rascunho estourava sem dizer (round 1, K4).

**W0 — manifesto, leitor e o subconjunto falsificável.** Gate: **canônico por
DOIS paths** — os scripts do toolkit são oráculo 0, mas a cura do C1 põe
`.github/workflows/ceremony-lint.yml` (oráculo **1**) e a do C5 põe
`.github/workflows/smoke-install.yml` (oráculo **1**) no mesmo patch, e são eles
que decidem, respectivamente, se o lint e o step de integridade enxergam o
toolkit (§Riscos). A W0 do rascunho dizia «livre» pela razão refutada; ela é
canônica pela razão medida.
- Arquivos: `.claude/scripts/ceremony/lib.sh`,
  `.claude/scripts/ceremony/read_manifest.py`, e UM arquivo de controle por
  invariante falsificável — `controls/inv1_rail_set.sh`,
  `controls/inv3_abs_path.sh`, `controls/inv4_baseline.sh`,
  `controls/inv5_scope.sh`, `controls/inv10_signer.sh`, mais o runner
  `controls/run.sh` [todos criados na W0]; e, no MESMO patch, os TRÊS arquivos
  de gate — `.claude/scripts/check-ceremony-script.py` (+`DISCOVERY_ROOTS`
  **e** escopo da R8), `.github/workflows/ceremony-lint.yml` (+`paths:` nos dois
  gatilhos) e `.github/workflows/smoke-install.yml` (+ as duas entradas do
  toolkit nos dois `paths:`, para o step de integridade disparar).
- Aceite: AC-1, metade W0. As invariantes que `lib.sh` falsifica SOZINHO são
  **1, 3, 4, 5 e 10** — todas predicados sobre ARQUIVOS. As invariantes 2, 6, 7
  e 8 são propriedades de `land.sh` e `harness.sh`, que só existem na W1
  (round 1, C6): controle sem o objeto que ele falsifica é verde vacuoso, o
  oposto do que a W0 promete provar.
- Corte v2: **11 paths** (2 de biblioteca + 6 de controle + 3 arquivos de
  gate) — isso ESTOURA a metade «≤ 8 paths» do critério. A W0 só passa
  pela outra metade da disjunção, «≤ 400 linhas alteradas», e a wave MEDE isso
  sobre a árvore STAGED — `git add -A` e então
  `git diff --cached --numstat` —, nunca com `git diff` sozinho: oito dos onze
  arquivos da W0 são NOVOS, e o `git diff` do working tree não conta arquivo
  não-rastreado, o que faria a medição admitir um pacote que estoura os DOIS
  tetos. É a mesma ordem que `CLAUDE.md` §4 impõe aos gates de corpus
  («`git add -A` → gates sobre a árvore staged → `git commit`»). Se não couber,
  a divisão
  concreta é **W0a** (manifesto + leitor + os TRÊS arquivos de gate = 5
  paths; os quatro sítios continuam no MESMO patch, que é a exigência do C1 e
  do C5) e **W0b** (os seis arquivos de controle = 6 paths). Declarado aqui
  porque a contagem mudou duas vezes — quando os controles passaram a ser
  nomeados um a um, e quando o `smoke-install.yml` entrou —, e cura que gera o
  defeito seguinte é classe conhecida.
- Commit: `feat(PLAN-188 w0): manifesto TSV com leitor fail-closed, os quatro
  sítios de gate e os controles vermelhos que lib.sh falsifica sozinho`.

**W1 — os quatro scripts + piloto W6a.** Gate: **canônico**, por cerimônia
CLONADA (o bootstrap de §Riscos).
- Arquivos: `.claude/scripts/ceremony/sign.sh`,
  `.claude/scripts/ceremony/land.sh`, `.claude/scripts/ceremony/finalize.sh`,
  `.claude/scripts/ceremony/harness.sh` [criados na W1]; o `ceremony.tsv` do
  pacote piloto; `.claude/governance/gate-scripts-manifest.txt`.
- Aceite: AC-2, AC-6 e a metade migrada do AC-1 (controles das invariantes 2, 6,
  7 e 8 + o harness rodando a partir de um clone descartável em worktree).
- Corte v2: 4 scripts + manifesto do piloto + `gate-scripts-manifest.txt` =
  **6 paths**, e o critério é uma DISJUNÇÃO (≤ 400 linhas **OU** ≤ 8 paths):
  6 paths já satisfazem o teto, qualquer que seja a contagem de linhas. Se o
  Owner ainda assim quiser dividir, a divisão natural é **W1a**
  (`finalize.sh` + `harness.sh`) e **W1b** (`sign.sh` + `land.sh`), nessa ordem,
  porque o `sign.sh` consome o que o `finalize` escreve — mas isso é OPÇÃO, não
  regra: o plano não aperta o teto acordado.
- Commit: `feat(PLAN-188 w1): sign/land/finalize/harness por manifesto + piloto W6a`.

**W2 — migração dos 5 pacotes restantes, em SUBWAVES.** Gate: canônico.
- A W2 do rascunho («migração dos 5 packs + remoção dos clones») estoura o teto
  v2 sozinha: só o PLAN-169 tem **13** `OWNER-*.sh` rastreados
  (`git ls-files '.claude/plans/PLAN-169*' | grep -cE 'OWNER-.*\.sh$'` = 13).
  **Decisão:** uma subwave POR PACOTE (`W2a`..`W2e`), na ordem que a OQ-2 fixar
  — a OQ-2 passa a ser a mesma decisão que o corte das subwaves —, cada uma
  ≤ 8 paths, com o seu manifesto e a sua janela de assinatura.
- **Os clones não são apagados por atacado (round 1, K7).** A razão já está
  escrita no repo: `.claude/scripts/check_contamination.py:299-301`
  isenta `scripts/local/historical/*` com o comentário «retained for
  chain-of-custody. Never re-executed», e `:321-326` isenta `archive/*` pela
  mesma razão.
  **Decisão:** clone de cerimônia JÁ ASSINADA vai para CUSTÓDIA, nunca para o
  `rm`; clone que nunca assinou nada pode ser removido; e cada subwave nomeia,
  arquivo a arquivo, a qual dos dois conjuntos ele pertence. O DESTINO da
  custódia é OQ-8.
- File assignment de CADA subwave `W2x`, na forma fixa (concreta quando a
  subwave é escrita, porque só então o diretório do pacote é conhecido pelo
  `ceremony.tsv` que ela cria): `<PK>/<dir do pacote>/ceremony.tsv` (novo) +
  os `OWNER-*-{SIGN,LAND}.sh` daquele pacote (removidos ou movidos para
  custódia, um a um, nomeados) + a linha do MAPA do AC-3.
- Aceite: AC-3 — e o AC-3 só conta com o mapa COMPLETO (6/6, ver abaixo).
- Commit: `refactor(PLAN-188 w2<x>): <pacote> migra para o manifesto; clones
  assinados para custódia`.

**W3 — medição e ADR.** Gate: docs.
- Arquivos: `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` [criado na W3],
  `.claude/plans/PLAN-188/measure-rail-classes-v2.py` (o AC-4 exige `--since`
  obrigatório e a regra de classificação do toolkit — ver abaixo; sem esse
  arquivo no escopo, seguir este file assignment não satisfaz o AC-4) e
  este plano. **A emenda ao ADR-010 NÃO é agendada aqui:** a OQ-1 deixa com o
  Owner tanto o número `ADR-2xx` quanto a WAVE em que a emenda entra; enquanto
  ela estiver aberta, a emenda não pertence a wave nenhuma. Se o Owner a
  colocar na W3, `.claude/adr/ADR-010-*.md` entra neste file assignment.
- Aceite: AC-4 (com a OQ-5 já decidida) e AC-5.
- Commit: `docs(PLAN-188 w3): ADR do toolkit + medição da fração «cerimônia»`.

## Acceptance criteria

- [ ] AC-1 (metades W0 e W1) Os scripts existem, `bash -n` + `shellcheck`
      limpos, sem path pessoal, com ≥ 1 controle VERMELHO por invariante.
      **O escopo da W0 é o subconjunto que `lib.sh` falsifica SOZINHO**
      (round 1, C6): invariantes 1, 3, 4, 5 e 10, todas predicados sobre
      arquivos. Os controles das invariantes 2, 6, 7 e 8 e «o harness rodando a
      partir de um clone descartável em worktree» dependem de `land.sh` e
      `harness.sh` e MIGRAM para o aceite da W1 — na W0 eles não teriam objeto
      para falsificar.
      Check (W0): `bash -n` + `shellcheck -S warning` nos scripts entregues; o
      runner de controles imprime **5/5** VERMELHO-antes / VERDE-depois; e o
      `check-ceremony-script.py` DESCOBRE os scripts do toolkit. Controle
      POSITIVO da descoberta: um script do toolkit com `|| true` numa linha de
      `gpg` REPROVA na regra R2, e o `ceremony-lint.yml` dispara pelo `paths:`
      do diretório novo. Falha = qualquer controle que passe com a invariante
      removida, ou um script do toolkit que o lint não enxergue.
      Check (W1): **4/4** VERMELHO-antes / VERDE-depois para as invariantes 2,
      6, 7 e 8, com o harness rodando de um clone descartável em worktree.
      Nota de custo (round 1, K6 ⇒ OQ-9): a metade «shellcheck limpo» já é
      automática — `.github/workflows/validate.yml:341-359` roda
      `shellcheck -S warning` sobre `find .claude/scripts .claude/hooks -name
      '*.sh'`; a metade CARA é o runner de controles, que hoje não tem workflow,
      step nem custo de runner-minutos medido.
- [ ] AC-2 Um pacote piloto (W6a) migra para o manifesto e assina/landa por
      `ceremony/sign.sh` + `land.sh` sem script próprio.
      Check: o commit landado do piloto não referencia nenhum `OWNER-*-{SIGN,LAND}.sh`
      próprio e o `.asc` verifica; falha = o piloto precisar de um script clonado.
- [ ] AC-3 Os 5 pacotes restantes (W4b, W5a, W1a, SF, WR) migram por
      manifesto; os `OWNER-*-{SIGN,LAND}.sh` próprios deixam de ser o caminho
      de assinatura.
      **O Check do rascunho era inobservável** (round 1, C2): medido no HEAD,
      `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0** — os pacotes ficam
      fora do repo (§Context) —, então a pergunta «`git ls-files` não lista …»
      já responde «não» ANTES de qualquer trabalho e continua «não» se a
      migração FRACASSAR; e a mesma consulta é ruidosa para o resto, porque há
      **48** `OWNER-*(SIGN|LAND)*.sh` rastreados de outros planos
      (`git ls-files | grep -cE 'OWNER-.*(SIGN|LAND).*\.sh$'` = 48) que ela não
      distingue.
      **Pré-condição — o MAPA das SEIS chaves, não das cinco.** O conjunto
      exigido é `{W6a, W4b, W5a, W1a, SF, WR}` (W6a incluído: é o piloto do
      AC-2, e sem ele o AC-3 mediria um subconjunto). Cada linha é
      `<chave> → <PK>/<diretório do pacote>` e é escrita pela wave que migra
      aquele pacote — a W1 escreve a de W6a, cada subwave `W2x` escreve a sua.
      Os seis vivem hoje como diretórios irmãos da árvore de trabalho `<PK>`
      (§Context: ficam FORA do repo), e é por isso que o plano carrega o
      placeholder `<PK>` e não um path absoluto: um plano rastreado não leva o
      home de ninguém (a mesma regra do AC-4).
      Check: (a) o mapa tem EXATAMENTE as seis chaves — subconjunto REPROVA, e
      chave a mais REPROVA; (b) para cada par do mapa, o diretório do pacote tem
      `ceremony.tsv` e NENHUM `OWNER-*-{SIGN,LAND}.sh`.
      **Controle POSITIVO (obrigatório):** plantar um `OWNER-*-SIGN.sh` num dos
      diretórios do mapa faz o Check ficar VERMELHO. Se não ficar, o instrumento
      está morto e o AC não conta — é a classe «instrumento verde cuja pergunta
      envelheceu», que esta casa já pagou duas vezes.
      Falha = qualquer pacote do mapa sobreviver com script próprio, ou o
      controle positivo não reprovar.
- [ ] AC-4 Medição: fração «cerimônia» dos achados de rail nas 3 assinaturas
      seguintes, contra a base congelada de 23,1 %
      (`.claude/plans/PLAN-188/s345-rail-classes.txt`).
      **Pré-condição (round 1, C4): a OQ-5 é decidida ANTES de o AC-4 virar
      critério.** Enquanto ela estiver aberta, o AC-4 é OBSERVAÇÃO, não gate —
      o limite (vi) da OQ-5 infla exatamente a classe que este AC compara.
      **Instrumento pinado AGORA, não em promessa.** O binário que produziu a
      base de 23,1 % é
      `.claude/plans/PLAN-188/measure-rail-classes-v2.py`, sha256
      `d2234bdfd78bc9b26bd8c85fe9561df7642d333aa5164b7913aeff1aeb181062`
      (`shasum -a 256 <esse path>`, no HEAD deste plano). A comparação só vale
      contra ESSE digest; instrumento re-editado invalida a série, porque quem o
      editaria é justamente a parte MEDIDA. Se a OQ-5 escolher corrigir o
      classificador, o plano grava o digest NOVO no mesmo lugar e re-mede a base
      com ele — dois digests escritos, nunca um implícito.
      **Parâmetros, nunca defaults** («parâmetro que muda o veredito não tem
      default»): hoje `measure-rail-classes-v2.py:32` congela
      `SINCE = '2026-09-04 20:00'` e `:123` filtra o corpus por
      `os.path.getmtime(f) >= SINCE` — **mtime, não conteúdo**: um `touch` ou um
      `git checkout` re-datam arquivos e mudam o corpus sem mudar um byte de
      achado. `SINCE` e a árvore do corpus passam a ser argumentos EXPLÍCITOS, e
      a árvore viaja como placeholder (`<PK>`) — um plano rastreado não carrega
      path pessoal.
      **Denominador declarado:** a evidência cita NUMERADOR e DENOMINADOR
      («`ceremony` N de M blocos classificados»), não só a razão: uma razão
      sozinha cai se OUTRAS classes crescerem, sem nenhuma cerimônia ter
      melhorado.
      **A flag `--since` NÃO EXISTE hoje — é entrega nomeada, não suposição.**
      Verificado no HEAD: `measure-rail-classes-v2.py:104-113` só reconhece
      `--pack-dir` (e a variável `CEO_RAIL_PACK_DIR`), e `:32` mantém o
      timestamp fixo; passar `--since <qualquer coisa>` é IGNORADO em silêncio e
      o comando ainda sai rc 0. A wave que fizer a medição entrega, no mesmo
      patch, `--since` como argumento OBRIGATÓRIO (sem default) e a recusa
      nomeada para valor não-parseável — e, como isso muda o binário, grava o
      digest novo e re-mede a base com ele. Congelar o classificador (opção (b)
      da OQ-5) significa congelar as REGRAS de classificação, não proibir a
      flag: o controle de que a mudança foi só de CLI é a base re-medida bater
      classe a classe com a saída congelada em `s345-rail-classes.txt` — **e
      esse controle só é honesto se os INPUTS também estiverem congelados**.
      Congelar o binário não congela o corpus: `measure-rail-classes-v2.py:121-123`
      escolhe os arquivos por `mtime`, então uma rodada nova ou uma cópia do
      `<PK>` muda o conjunto e a igualdade classe-a-classe reprovaria uma
      mudança só-de-CLI que está correta. Por isso a wave da medição grava, ao
      lado da saída congelada, a LISTA dos registros que a produziram com o
      sha256 de cada um, e a re-medição roda sobre ESSA lista; se a lista não
      puder ser reconstruída, o plano declara uma base NOVA em vez de exigir os
      números antigos.
      **`--since` NÃO SELECIONA três assinaturas — a coorte é EXPLÍCITA.**
      `measure-rail-classes-v2.py:121-123` varre o `<PK>` INTEIRO de forma
      recursiva (`glob` de `*/**/rail-*round-*.md`) e só filtra por `mtime`:
      um QUARTO pacote sem relação nenhuma que ganhe registros depois de `<TS>`
      entra no DENOMINADOR e move a fração sem que uma linha de cerimônia tenha
      mudado — o mesmo oito achados de cerimônia sai 8/120 (6,7 %) ou 8/240
      (3,3 %) conforme haja três ou quatro pacotes na árvore. Por isso o AC-4
      mede sobre uma COORTE NOMEADA: os três pacotes das assinaturas seguintes
      são listados por chave no próprio plano no momento em que a wave começa, e
      a medição roda sobre a LISTA sha256-pinada dos registros DESSES três — a
      mesma exigência que a base congelada já carrega. `--since` fica como
      filtro auxiliar dentro da coorte, nunca como seletor da amostra.
      Check: `python3 .claude/plans/PLAN-188/measure-rail-classes-v2.py
      --pack-dir <PK> --cohort <as 3 chaves de pacote> --since <TS>`
      [`--cohort` e `--since` criados na wave da medição] imprime `ceremony`
      com numerador e denominador para EXATAMENTE as 3 assinaturas da coorte,
      medidas pelo binário pinado.
      **A migração MOVE defeitos para fora da classe medida — e isso é
      corrigido antes de a comparação valer.** Sob as regras congeladas, um
      achado sobre `.claude/scripts/ceremony/read_manifest.py` sai `product`,
      enquanto o MESMO achado sobre um `OWNER-*-SIGN.sh` sai `ceremony`: o
      toolkit faria a fração cair só por mudar o parsing de lugar. A wave da
      medição acrescenta `.claude/scripts/ceremony/**` às raízes de `ceremony`
      no classificador, re-mede a base com a regra nova e grava o digest novo —
      é o mesmo pacote da entrega do `--since`. Sem isso, uma queda da fração
      não é evidência de nada.
      **Critério de morte pré-registrado:** (a) se as 3 assinaturas seguintes
      não produzirem ≥ 100 blocos classificados no total, a amostra é pequena
      demais e o AC-4 sai **NÃO CONCLUSIVO** — nem «passou» nem «falhou» — com o
      porquê escrito; (b) se a fração cair sem que nenhuma classe da tabela de
      §Context tenha sido fechada com controle vermelho, o AC-4 sai **INVÁLIDO**
      e a queda é atribuída ao denominador.
      Meta: < 5 % com a OQ-5 decidida; falha = ≥ 5 % com amostra suficiente, e o
      plano diz o porquê.
- [ ] AC-5 ADR próprio (`ADR-2xx-shared-ceremony-toolkit`) ACEITO pelo Owner;
      ADR-010 emendado para apontar o toolkit como implementação canônica da
      disciplina de sentinel.
      Check: o ADR existe com `Status: ACCEPTED` e um `.asc` do Owner sobre o
      sentinel da wave; falha = status flipado sem assinatura rastreada.
- [ ] AC-6 (W1) Os scripts de gate do toolkit entram no manifesto ADR-192
      `.claude/governance/gate-scripts-manifest.txt`, que hoje pina **9**
      scripts por sha256. Round 1, C5: o script que decide se a assinatura do
      Owner acontece não pode ser MENOS protegido que o `verify-counts.sh`, que
      só conta e tem sentinel e checksum.
      Check: `shasum -c` sobre o manifesto passa com as linhas novas e FALHA
      quando um byte de `sign.sh` ou de `land.sh` muda sem bump do manifesto —
      esse controle vermelho é obrigatório e é a evidência do AC.
      Falha = o toolkit shipado fora do manifesto, ou o bump feito sem que o
      controle vermelho tenha sido visto.

## Open questions

- OQ-1 — **Resolvida (CEO, S347)**: o alvo da emenda do AC-5 é o **ADR-010**
  («Canonical-edit sentinel for meta-agent drafts»), que define o contrato
  `Scope:` + `check_canonical_edit.py` consumido por este toolkit; o **ADR-031**
  («Self-improving skills, Owner-gated, shadow-mode») está FORA do escopo e não
  é emendado. O rascunho de origem atribuía o formato do sentinel ao ADR-031
  (achado pelo rail de mecanismo desta wave); a atribuição foi corrigida em
  todos os sítios deste arquivo. Aberto para o debate: qual número `ADR-2xx`
  recebe o ADR próprio e em que wave a emenda ao ADR-010 entra.
- OQ-2 (Owner): a ordem de migração dos 5 packs do AC-3 (o rascunho não a fixa)
  e a janela de assinatura de cada um.
- OQ-3 — **Promovida a PRÉ-CONDIÇÃO da W0 e decidida (round 1, C3):** o
  manifesto é TSV no molde de `scripts/delivery-routes.tsv`, lido por um leitor
  Python que o `sign.sh` invoca — nunca por regex de shell no ponto onde o Owner
  assina. `tomllib` é 3.11+ e o piso é 3.9 (`python3 -V` = `Python 3.9.6` nesta
  máquina; `python3 -c "import tomllib"` = `ModuleNotFoundError`), então o TOML
  do rascunho era impossível. O que resta ao debate não é o formato, e sim a
  lista final de RECUSAS NOMEADAS do leitor (§Approach): acrescentar uma recusa
  é barato, remover não.
- OQ-4: as cinco chaves de orçamento do molde `PLAN-187` que este frontmatter
  omite (`budget_tokens`, `budget_sessions`, `context_risk`, `external_wait` —
  ADR-081; `eta_calendar` — PLAN-180) ficam em aberto: o rascunho não estimou e
  este arquivo não inventa números. O round 1 DEFERIU o item («a omissão é
  ratificação do Owner e não bloqueia o round 2 nem a W0») e registrou que a
  postura de não inventar número é a certa. Decisão do Owner, portanto: ou ele
  RATIFICA a omissão, ou dita os cinco valores.
- OQ-5: o instrumento tem SEIS limites conhecidos, achados pelas rodadas
  de mecanismo desta wave sobre os bytes landados e reproduzidos no código:
  (i) todo cabeçalho `#` fecha bloco (`measure-rail-classes-v2.py:90-93`), então
  um achado anunciado por `## Achado P1 …` perde a severidade e o corpo;
  (ii) linhas de tabela consecutivas se FUNDEM num bloco só
  (`:94-99`, `START_RE` não casa o `|` inicial e `and not cur` só deixa a
  primeira linha abrir bloco); (iii) qualquer bloco com path entra no
  denominador (`:131-134`), inclusive bullets de proveniência — a classe
  `other-path` da saída congelada contém exatamente isso;
  (iv) um pacote cujas rodadas são todas limpas nunca entra em `per_pack`
  (`:136` — a ÚNICA inserção em `per_pack`; `:126-129` é o cabeçalho do laço),
  então some da contagem de pacotes: um registro `APPROVE` sem achado dá
  `records=1 packs=0`; (v) `nh = sum(high.values()) or 1` (`:147-148`)
  imprime `HIGH ... total=1` quando NÃO há achado de alta severidade — a
  proteção contra divisão por zero sai como se fosse medida; (vi) um path na
  RAIZ do repo sob `tests/` não é reconhecido por `PATH_RE` (`:33` — `tests`
  não está entre as raízes e o lookbehind `(?<![\w/])` impede casar o basename
  depois de `/`), então o achado cai na classificação por palavra-chave e um
  bloco como `[P1] tests/integration/test_install_npm_smoke.py fails to check
  the sentinel` sai `ceremony` em vez de `tests` — inflando justamente a
  fração que o AC-4 compara. Consequência: o
  23,1 % é a fração DESTE classificador, não uma contagem canônica de defeitos,
  e a comparação do AC-4 só é honesta se as 3 assinaturas seguintes forem
  medidas pelo MESMO binário. Decidir no debate: corrigir o classificador e
  re-medir a linha de base, ou congelar o instrumento como está e comparar
  igual-com-igual. **Sequenciamento (round 1, C4): esta OQ é decidida ANTES de
  o AC-4 virar critério** — enquanto ela estiver aberta o AC-4 é observação. As
  consequências das duas opções, escritas: (a) corrigir o classificador e
  re-medir ⇒ a base de 23,1 % MORRE e nasce outra, e as três assinaturas
  seguintes são medidas contra a nova; (b) congelar o instrumento como está ⇒ a
  base vale, a comparação é igual-com-igual, e o plano escreve que a fração é a
  DESTE classificador, não uma contagem canônica de defeitos. **Um sétimo
  limite, achado pelo rail de mecanismo desta revisão e que vale nas DUAS
  opções:** o classificador não conhece `.claude/scripts/ceremony/**`, então um
  achado no toolkit sai `product` e o mesmo achado num clone sai `ceremony` — a
  própria migração derrubaria a fração sem nenhuma cerimônia ter melhorado. Seja
  qual for a opção escolhida, essa raiz entra no classificador e a base é
  re-medida antes de o AC-4 comparar.

- OQ-6 (Owner): o REGISTRO do toolkit nos gates existentes. A membresia no
  manifesto ADR-192 NÃO está em aberto — é entrega da W1 e critério do AC-6. O
  que fica com o Owner é (i) a entrada dos scripts em `_CANONICAL_GUARDS`
  (`.claude/hooks/check_canonical_edit.py:115`, lista ESTÁTICA por path) — isto
  é, se o HOOK protege os scripts DIRETAMENTE, defesa em profundidade —, e
  (ii) em que wave essa entrada acontece, já que ela torna canônica a própria
  wave que a faz. **O que a OQ-6 NÃO decide é se as waves futuras do toolkit são
  livres:** a partir do AC-6, todo bump de hash no
  `.claude/governance/gate-scripts-manifest.txt` — que o oráculo já responde
  `1` — exige cerimônia assinada, e um hash desatualizado reprova no step de
  integridade do `smoke-install.yml` — DESDE QUE o `paths:` do workflow o
  dispare para o toolkit. Hoje não dispara: nenhuma das duas listas casa
  `.claude/scripts/ceremony/**` nem
  `.claude/governance/gate-scripts-manifest.txt`, e é a W0 que acrescenta as
  duas entradas (§Riscos, quarto sítio do patch). Com esse sítio no lugar, um
  toolkit alterado fora de cerimônia fica VISÍVEL no CI seguinte. **Mas a
  proteção direta não é redundante, e por isso a OQ-6 é decisão de verdade:** a
  verificação do ADR-192 mora em workflows (`ADR-192:49-53`), nunca num lançador
  local, então uma assinatura feita com um `sign.sh` já modificado ACONTECE
  antes de qualquer reprovação. O que a OQ-6 escolhe é entre detecção post-hoc
  (só o manifesto) e prevenção no ato da edição (manifesto + hook) — e, enquanto
  estiver aberta, o §Riscos declara a janela como limite assumido.
- OQ-7: o alcance do contrato `--describe`. A W0 o especifica e o exige de cada
  pacote migrado; nenhum derivador rastreado o implementa hoje. Em aberto: se o
  contrato é RETRO-aplicado aos derivadores dos 5 pacotes do AC-3 (custo por
  pacote) ou se `scope_generated_from` é chave OPCIONAL, caindo no braço (b) da
  invariante 5 (escopo gravado pelo `finalize`). **A escolha é entre BRAÇOS, não
  entre verificar e não verificar:** nenhum pacote migrado assina escopo que não
  tenha sido gerado e conferido. O que não é aceitável é a chave apontar para um
  comando inexistente — nem um pacote sem braço nenhum.
- OQ-8 (Owner): o DESTINO dos clones. O plano já decide que clone de cerimônia
  JÁ ASSINADA vai para custódia e não para o `rm` — a razão está escrita em
  `.claude/scripts/check_contamination.py:299-301` («retained for
  chain-of-custody. Never re-executed») e `:321-326`. Em aberto: qual dos dois
  diretórios isentos recebe os clones migrados (`scripts/local/historical/` ou
  `archive/`), ou um terceiro; e se o clone que NUNCA assinou nada é removido ou
  também arquivado.
- OQ-9: quem EXECUTA o runner de controles, em que evento e a que custo. Medido
  (round 1, K6): `.github/workflows/validate.yml:341-359` já roda
  `shellcheck -S warning` sobre `find .claude/scripts .claude/hooks -name
  '*.sh'`, então a metade barata do AC-1 é automática; a metade CARA — rodar os
  controles vermelhos — não tem workflow, step nem custo de runner-minutos
  medido. Opções nomeadas pelo round: step no `validate.yml`, workflow próprio
  disparado pelo `paths:` do toolkit, ou execução local exigida pelo
  `harness.sh` de cada cerimônia.

## How to continue

Primeira mensagem de uma sessão futura: «Leia
`.claude/plans/PLAN-188-shared-ceremony-toolkit.md`, o consenso do round 1 em
`.claude/plans/PLAN-188/debate/round-1/consensus.md` e o resultado do round 2.
O round 1 fechou `RUN-ANOTHER-ROUND`, então o round 2 revisa ESTE arquivo
revisado, não o rascunho. Se o round 2 ainda não rodou, rode-o (L3). Se rodou e
o Owner marcou o plano `reviewed`, execute a W0 — leitor TSV + `lib.sh` + os
controles vermelhos das invariantes 1, 3, 4, 5 e 10 + os QUATRO sítios de gate
(DISCOVERY_ROOTS, escopo da R8, `paths:` do `ceremony-lint.yml` e `paths:` do
`smoke-install.yml`) no mesmo patch — e só então proponha a W1.»

## Success criteria

- AC-1 a AC-6 marcados, cada um com a evidência do seu `Check:` citada — a
  AC-6 (membresia ADR-192) inclusive: um plano que feche sem ela deixa o gate
  da assinatura sem checksum, que é o achado C5 do round 1.
- O plano só sai de `draft` por decisão do Owner após o `/debate`.

## Progress log

- 2026-09-05 (S345): plano criado como rascunho a partir da medição da noite
  (`.claude/plans/PLAN-188/measure-rail-classes-v2.py`, saída congelada em
  `.claude/plans/PLAN-188/s345-rail-classes.txt`). Debate L3 devido.
- 2026-09-06 (S347): round 1 do debate L3 sintetizado
  (`.claude/plans/PLAN-188/debate/round-1/consensus.md`; três críticos `ADJUST`,
  veredito `RUN-ANOTHER-ROUND`). Os 7 achados de consenso (C1-C7) e os 15
  must-fix foram absorvidos NESTE arquivo: endereço do toolkit como decisão de
  gate com os dois sítios de descoberta na W0; formato do manifesto decidido
  (TSV — `tomllib` não existe no piso 3.9); `--describe` como entrega da W0 ou a
  chave sai; reconciliação com `generate-ceremony.sh`; invariantes 1, 3, 6 e 9
  reescritas e a 10 (signatário) acrescentada; AC-1 reduzido ao que a W0
  falsifica; AC-3 com mapa e controle positivo; AC-4 com instrumento pinado,
  parâmetros, denominador e critério de morte; AC-6 (ADR-192); §Items com file
  assignment, aceite, commit hint e corte v2, com a W2 em subwaves e custódia
  dos clones assinados; OQ-3 promovida a pré-condição e OQ-6 a OQ-9 abertas.
  Round 2 devido sobre o arquivo REVISADO — o round 1 não concedeu
  `design-coherent`.
