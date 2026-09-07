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
> (round 1, K8; grafo de dependências em
> `.claude/plans/PLAN-SCHEMA.md:462-470` — o path completo, que resolve no
> HEAD; round 2, K11).
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

**Decisão (a) — a entrada em `DISCOVERY_ROOTS` NÃO basta: o predicado de
descoberta do toolkit é por DIRETÓRIO (round 2, D1).** A cura escrita no
round 1 era de ENDEREÇO, e a descoberta do lint é por CONTEÚDO e só `.sh`:
`.claude/scripts/check-ceremony-script.py:137` (`if not fn.endswith(".sh"):
continue`) e `:146` (`if SHEBANG_RE.match(body) and
CEREMONY_OPS_RE.search(body)`), com `CEREMONY_OPS_RE` em `:71-73`
(`gpg|git tag|gh release|npm publish|sentinel|approved\.md|VERDICT`). Sob esse
predicado, pôr `.claude/scripts/ceremony/` na lista **não descobre**
`read_manifest.py` — o parser fail-CLOSED no ponto exato onde o Owner assina —
e qualquer arquivo do toolkit sem token de cerimônia nasce invisível.
**Decisão:** a W0 entrega a MUDANÇA DE PREDICADO junto com a entrada — dentro
do TOOLKIT ROOT (`.claude/scripts/ceremony/`) todo arquivo `.sh` **ou** `.py`
é descoberto INCONDICIONALMENTE, sem teste de shebang e sem
`CEREMONY_OPS_RE`, porque ali o DIRETÓRIO é a superfície de cerimônia; o
predicado por conteúdo continua valendo para `.claude/plans/**`, onde o mesmo
diretório carrega material que não é cerimônia. O que isso muda no julgamento
de um membro `.py`: R1 (proveniência) e R8 (exec-bit) independem de linguagem e
valem como valem hoje; R2-R4 são regex de TEXTO e disparam se o padrão
aparecer; o `shellcheck` do `.github/workflows/validate.yml:341-359` não cobre
`.py` — cobre, sim, todo `.sh` novo do toolkit, porque o
`find .claude/scripts .claude/hooks -name '*.sh'` daquele step é recursivo e o
endereço escolhido cai dentro dele. **E há um consumidor do `--list` que a
mudança de predicado SUJA — não que ela quebre (rail r3 C3, corrigido pelo
round 3, M1):** o job `shellcheck-ceremony` do
`.github/workflows/ceremony-lint.yml:78-82` alimenta o `shellcheck` com o
conjunto INTEIRO devolvido por
`python3 .claude/scripts/check-ceremony-script.py --list`, e um `.py` nesse
conjunto sai como `SC1071`. **O que o round 3 mediu e a revisão anterior
errava:** o `shellcheck` sai rc 1, mas o STEP **não pode ficar vermelho**, por
DOIS mecanismos independentes — `ceremony-lint.yml:75` é
`continue-on-error: true` e `:81-82` fecha a invocação com
`> shellcheck-ceremony.txt 2>&1 || true`; o `run:` abre em `:77` com
`set -uo pipefail` (sem `-e`) e o último comando do step é o bloco que escreve
o `$GITHUB_STEP_SUMMARY` (`:84-89`). O comentário `:72` declara o job
«ADVISORY nesta fase». A frase «o passo devolve rc 1» que este plano publicava
está REFUTADA e sai. **A razão que sustenta a decisão é outra, e é
suficiente:** cada mudança legítima do toolkit passa a acrescentar `SC1071` ao
relatório advisory, permanentemente, num artefato que ninguém consegue ver
vermelho — ruído que treina o leitor a ignorar o canal.
**Decisão (inalterada):** a W0 entrega, no MESMO patch, o filtro de
shell nesse consumidor — ao `shellcheck` vai só o subconjunto `.sh`, enquanto
o julgamento do lint (R1-R4 e R8) continua cobrindo o `.py` inteiro. O
`.github/workflows/ceremony-lint.yml` já está no file assignment da W0a, então
o filtro não acrescenta path.
**E o filtro nasce FALSIFICÁVEL fora do motor de eventos (round 3, M2).** Um
critério cujo único observador é um humano lendo um sumário de step advisory
não é critério. Por isso o subconjunto é expresso como uma FLAG do próprio
checador — `--list --shell-only`, entregue na W0a dentro de
`.claude/scripts/check-ceremony-script.py`, que já está no file assignment
(zero path novo) — e é ELA que o step invoca. O filtro continua morando no
CONSUMIDOR (quem escolhe a flag é o step; o `--list` sem flag segue listando
tudo), e o par de comandos abaixo é o controle, executável em qualquer
checkout:

```
python3 .claude/scripts/check-ceremony-script.py --list              # contém o .py do toolkit
python3 .claude/scripts/check-ceremony-script.py --list --shell-only # NÃO contém nenhum .py
```

Controle VERMELHO nomeado: com a flag ausente ou ignorada, a segunda linha
devolve o `.py` e o controle reprova — é o mesmo `.py` que a primeira linha
tem de mostrar pelo controle positivo da descoberta.

**O piso do lint não responde «o guard vê o meu alvo?».**
`check-ceremony-script.py:100` fixa `DEFAULT_FLOOR = 41` e `:334-335` calcula
`floor_ok = len(tracked) >= floor` — piso de ENCOLHIMENTO. Os valores estão no
CENSO ÚNICO do §Riscos («A dimensão disso — CENSO ÚNICO desta revisão»), medido
em worktree limpo e único sítio deste plano que os declara: o conjunto
descoberto está muito acima do `floor`, e quase todo ele vem de
`.claude/plans/**`. Somar o toolkit não pede bump, e pela mesma aritmética o
piso JAMAIS ficaria vermelho se o toolkit saísse da descoberta. Quem responde
é o controle positivo do AC-1 — e é por isso que ele passou a ser um arquivo do
toolkit SEM token de cerimônia.

**Decisão (b) — as CINCO classes bloqueantes valem, e a marca é decidida
arquivo a arquivo (round 2, D2).** Com a descoberta funcionando, a R1
(`check-ceremony-script.py:163-166`: corpo sem `PROVENANCE_MARK` nem
`EXCEPTION_MARK`; `:84-85` = `"AUTO-GENERATED"` e
`"CEREMONY-LINT: handwritten-exception:"`) reprova TODO script escrito à mão.
São **cinco** classes herdadas, não quatro (rail r1 #13, que corrigiu a
aritmética desta frase): a versão anterior deste plano enumerava R1-R4 e tratava
a R8 como a quinta que só o alargamento traria — mas a R1 já estava DENTRO
daquelas quatro, e é ela que a marca anula. Ou seja: descoberto, o toolkit herda
R1-R4 de imediato e a R8 assim que a decisão (c) alargar o escopo; a marca de
exceção não é consequência da descoberta, é ENTREGA da W0, sem a qual a W0
nasce vermelha na R1 no dia 1. Decisão escrita: os arquivos do toolkit
são escritos à mão e carregam `CEREMONY-LINT: handwritten-exception: <razão>`
com razão auditável na própria linha; nenhum recebe `AUTO-GENERATED`, porque a
marca de proveniência afirma «produzido por gerador» e usá-la num arquivo
escrito à mão destrói o significado dela no corpus inteiro.

| arquivo (W0/W1) | marca | razão que a linha registra |
|---|---|---|
| `ceremony/lib.sh`, `ceremony/read_manifest.py` | `handwritten-exception` | biblioteca e leitor do manifesto; não há gerador, e a proteção contra edição é o AC-6 (manifesto ADR-192) |
| `ceremony/sign.sh`, `land.sh`, `finalize.sh`, `harness.sh` | `handwritten-exception` | são o GATE da assinatura; gerar o gate a partir de outro gerador só move a pergunta de lugar |
| `ceremony/controls/*.sh` e `controls/run.sh` | `handwritten-exception` | controles vermelhos: um controle gerado pelo mesmo produtor que ele testa não falsifica nada (lição S332) |
| `<pacote>/ceremony.tsv` | — | não é `.sh` nem `.py`, fica FORA da descoberta por desenho; quem o julga é o leitor fail-CLOSED |

**Decisão (c) — a R8 é alargada, e o plano declara o modo de invocação que
reconcilia a razão escrita no próprio checador (round 2, D4).** O comentário
`check-ceremony-script.py:192-194` escopa a R8 a `.claude/plans/` com a razão
«exec-bit em ferramenta de `scripts/local/` é legítimo (invocada
diretamente)». O toolkit **não** é invocado diretamente: o Owner o roda como
`bash .claude/scripts/ceremony/sign.sh <pacote>`, e os arquivos ficam `100644`
no índice — a razão do comentário não o alcança, e o alargamento não a
contradiz. A W0 alarga a R8 ao TOOLKIT ROOT **e emenda esse comentário no mesmo
patch**, para que a razão escrita continue descrevendo a regra escrita. Duas
consequências medidas: (i) `CLAUDE.md` §4 registra que o exec-bit volta no
primeiro `git add -A` se for largado só do índice — o modo sai do índice **e**
do sistema de arquivos, e o harness confere os dois; (ii) hoje
`.claude/scripts/local/generate-ceremony.sh` e
`.claude/scripts/local/verify-counts.sh` são `100755` no índice, e dos 48
`OWNER-*(SIGN|LAND)*.sh` rastreados **41 são `100644` e 7 são `100755`**
(`git ls-files -s .claude/plans | grep -E 'OWNER-.*(SIGN|LAND).*\.sh$' |
awk '{print $1}' | sort | uniq -c`; o round 2 escrevia «os `OWNER-*.sh` de
plano são `100644`», e este censo REFINA a aproximação — 41 são, 7 não) — a R8
já dispara hoje sobre **28**
arquivos descobertos, e os **28** estão isentos por waiver (a medição está na
seção seguinte): o que mantém essa regra verde no repo não é conformidade, é o
arquivo de isenções.

TRÊS controles POSITIVOS, um por decisão: um arquivo do toolkit SEM nenhum
token da `CEREMONY_OPS_RE` tem de APARECER no `--list` (a); um script do
toolkit com `|| true` numa linha de `gpg` tem de REPROVAR na R2 (b); e um
script do toolkit com exec-bit no índice tem de REPROVAR na R8 (c).
Nota de risco (round 1, K10):
`.github/workflows/validate.yml:354` já exclui
`.claude/scripts/owner-ceremony/archive/*` do shellcheck e
`.claude/scripts/owner-ceremony/` não existe — um nome de diretório vizinho já
tirou scripts de um gate uma vez, e a exclusão morta ficou.

**Ganho de custódia do endereço novo — argumento A FAVOR que o plano não
fazia (round 2, K9).** `.claude/scripts/check_contamination.py` isenta, por
cadeia de custódia, `".claude/scripts/owner-ceremony/*"` (`:298`),
`".claude/scripts/local/*"` (`:319`), `"OWNER-*.sh"` (`:320`),
`"scripts/local/historical/*"` (`:301`) e `"archive/*"` (`:326`) — as duas
últimas com o comentário «retained for chain-of-custody. Never re-executed».
Os clones de hoje casam a isenção por NOME (`OWNER-*.sh`) esteja onde
estiverem; um toolkit em `.claude/scripts/ceremony/` não casa nenhum dos cinco
padrões e passa, pela primeira vez, a ser julgado por essa regra. O endereço,
portanto, não troca só a visibilidade do lint: ele SUBTRAI uma isenção.
**Mas o ganho é da regra de TERMOS, não da de PATH PESSOAL — e o plano diz
qual (rail r2 M3, que reproduziu a confusão):** as cinco isenções acima valem
para a varredura de TERMOS privados; a regra de path pessoal tem escopo
PRÓPRIO, `_PERSONAL_PATH_SCOPE = (".claude/plans/", "docs/")`
(`.claude/scripts/check_contamination.py:625`), que **não** inclui
`.claude/scripts/ceremony/`. Consequência escrita: mudar de endereço NÃO
transfere a proteção de path pessoal para o toolkit — no novo endereço quem
responde por ela é a invariante 3 (guard de path absoluto no `sign.sh`, no
finalize e no harness, com o guard se auto-escaneando), e estender
`_PERSONAL_PATH_SCOPE` ao toolkit é follow-up nomeado, não pressuposto desta
wave. Um home path cujo dono não esteja na lista de termos privados escaparia
do gate de contaminação no endereço novo se a invariante 3 não existisse; ela
existe, e é por isso que ela é entrega da W0.

### O ESCAPE do lint: isenção por sha256 de CONTEÚDO (round 2, D3)

O plano tratava o `ceremony-lint` como se descobrir fosse reprovar. Não é:
`.claude/scripts/check-ceremony-script.py:288-297` carrega
`.claude/scripts/ceremony-lint-waivers.json` e `:312` isenta o arquivo cujo
**sha256 de CONTEÚDO** esteja na lista, com três rotas de escape somadas:
(i) a própria lista, hoje com **44** entradas
(`python3 -c "import json; print(len(json.load(open('.claude/scripts/ceremony-lint-waivers.json'))))"`
= 44, e o mesmo número sai como `waivers_active` no `--json`); (ii) o override `--waivers
<path>` (`:261-262`), que a CI nunca usa — `.github/workflows/ceremony-lint.yml:35-40`
invoca o checador sem argumento nenhum —, de modo que uma execução que passe
`--waivers` não é evidência de nada; (iii) o desbloqueio por ambiente
`CEO_CEREMONY_LINT_UNLOCK=<sha256>` + `CEO_CEREMONY_LINT_UNLOCK_REASON`
(`:34-35`, `:313-320`), que exige motivo e emite auditoria, mas continua sendo
uma isenção decidida fora do arquivo. O lint é fail-CLOSED em waiver ILEGÍVEL
(`:296-301`), e a isenção RE-ARMA quando o arquivo muda, porque a chave é o
conteúdo.

**A dimensão disso — CENSO ÚNICO desta revisão (refutação S347, F1).**
Todo número de descoberta e de bloqueio deste plano vive AQUI, uma vez; os
outros sítios APONTAM para este parágrafo em vez de repeti-lo — um sítio que
aponta não pode divergir do que ele aponta. **Base declarada: worktree limpo
(`git worktree add --detach`) no `a6629d0`**, só arquivos rastreados; os
diretórios `staged/` são `gitignore`d e por isso nem sequer aparecem na
DESCOBERTA de um checkout limpo. **O que exclui um arquivo do GATE é outro
mecanismo, e ele vale nas DUAS árvores (round 3, M14):** o filtro
`is_tracked` de `check-ceremony-script.py:329-330`
(`if n_block and not waived and is_tracked`), com a razão escrita em `:326-328`
(«o gate conta SÓ arquivos rastreados: o CI clona o repo e nunca vê
untracked/gitignored»). Uma árvore
de trabalho de mantenedor devolve números MAIORES: a refutação da S347 mediu
122 descobertos / 121 de `.claude/plans/**` / 55 com BLOCKING na árvore viva
contra 109 / 108 / 42 no checkout limpo — 13 arquivos de diferença, todos sob
`.claude/plans/PLAN-1{55,56,58,61,64,66,67,68}/staged/**`. O plano publica o
número do checkout limpo, porque é o que a CI e um clone novo enxergam.
Comando: `python3 .claude/scripts/check-ceremony-script.py --json`.

| figura | valor em `a6629d0` (worktree limpo) |
|---|---|
| `discovered_total` | **109** |
| `discovered_tracked` | **109** |
| descobertos sob `.claude/plans/**` | **108** (o 109.º é o `generate-ceremony.sh` de `EXPLICIT_FILES`) |
| arquivos com ao menos um achado BLOCKING | **42** |
| desses, isentos por waiver | **42** |
| `blocking_unwaived` | **0** |
| arquivos com achado R8 / isentos | **28** / **28** |
| `floor` | **41** |
| `waivers_active` | **44** |

Ou seja, a superfície bloqueante viva do repo hoje é **inteiramente absorvida
por isenções** — 42 arquivos com achado BLOCKING, 42 isentos por waiver — e um
toolkit descoberto entra nesse mesmo regime: a sua reprovação se apaga
acrescentando uma linha a um JSON. **Duas precisões que o round 3 exigiu
(M14), porque um leitor que as ignore erra o número em qualquer árvore:**
(i) `blocking_unwaived` conta ACHADOS, não arquivos (`:322` soma `n_block`,
`:330` acumula em `blocking_live`), então dele NÃO se deriva «42 de 42» — as
duas contagens de arquivo saem de `files[]` do `--json`, «arquivos com ≥ 1
achado BLOCKING» e, desses, os de `waived: true`; (ii) o `0` continua `0` numa
árvore de trabalho com 55 arquivos em BLOCKING e 13 NÃO isentos, porque esses
13 são untracked e o filtro `is_tracked` de `:329-330` os descarta — não
porque estejam waivados. Derivação das duas figuras, no `--json` de QUALQUER
árvore: `len([f for f in files if any(x["sev"]=="BLOCKING" for x in
f["findings"])])` e, dentro desse conjunto, `f["waived"]` e `f["tracked"]`.

**E a autoridade do lint mora fora de todo gate.** Medido, com o comando de
cada número ao lado: `python3 .claude/hooks/check_canonical_edit.py
--is-canonical <path>` responde `.claude/scripts/check-ceremony-script.py	0` e
`.claude/scripts/ceremony-lint-waivers.json	0`; `_KERNEL_PATHS`
(`.claude/hooks/check_arbitration_kernel.py:85`) tem **110** padrões e não casa
nenhum dos dois — `python3 -c "import importlib.util,fnmatch;
s=importlib.util.spec_from_file_location('k','.claude/hooks/check_arbitration_kernel.py');
m=importlib.util.module_from_spec(s); s.loader.exec_module(m);
print(len(m._KERNEL_PATHS))"` = 110, e o mesmo carregamento com `fnmatch`
devolve `False` para os dois paths (o consenso do round 2 cita «113 padrões»;
a contagem que este plano publica é a que o comando acima devolve em worktree
limpo no `a6629d0` — a base declarada no censo único do §Riscos, e a mesma de
toda medição deste documento —, e é ela que vale); e nenhum dos dois está entre os **9** membros do
`.claude/governance/gate-scripts-manifest.txt`
(`grep -cve '^#' -e '^$' .claude/governance/gate-scripts-manifest.txt` = 9). Logo a cura do C1 —
predicado de descoberta, `paths:` e escopo da R8 — pode ser desfeita por um
Edit livre, e a reprovação do toolkit pode ser apagada por um append de waiver,
sem cerimônia nenhuma. **Decisão:** os dois arquivos entram no manifesto
ADR-192 pelo AC-6, com controle vermelho próprio para o append de waiver. O
limite que sobra está escrito no §Riscos e é o mesmo do toolkit: a verificação
do ADR-192 é de CI, portanto detecção post-hoc; fechar a janela no ato da
edição é a OQ-6.

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
OQ-7 — que por isso **deixa de ser pergunta de execução e vira PRÉ-CONDIÇÃO da
W0** (round 2, K3). A razão é mecânica, não de gosto: o leitor do manifesto é
entrega da W0 e as suas RECUSAS NOMEADAS incluem «chave desconhecida» e «chave
obrigatória ausente» — as duas leituras da OQ-7 produzem leitores DIFERENTES.
No braço (a) `scope_generated_from` é chave OBRIGATÓRIA e a sua ausência é
recusa; no braço (b) ela é chave OPCIONAL-POR-CONSTRUÇÃO, o leitor aceita as
duas formas e recusa apenas a chave que aponte para um comando inexistente.
Escrever o leitor antes da escolha é escrever o leitor errado.

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

**Essa decisão está TOMADA (Owner, S348).** Na revisão de portfólio da S348 o
Owner respondeu à decisão D2 («um dono para a cerimônia: PLAN-174 × PLAN-188»)
com a opção (a): *«PLAN-174 vira superseded pelo PLAN-188»*. Registro em
`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md:136-137`
(a decisão D2 e as duas opções, §6) e
`.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md:174` (a
resposta do Owner, tabela do §7) — arquivo RASTREADO na base desta derivação.
As consequências, escritas aqui porque é exatamente isto que o parágrafo acima
exigia para poder aposentar o gerador:

1. O PLAN-174 **JÁ RECEBEU** `status: superseded` e `superseded_by: PLAN-188`
   (`.claude/plans/PLAN-174-ceremony-generation.md:4-5`), por pacote separado da
   S348; esta wave não edita aquele arquivo.
2. **O PLAN-188 ASSUME a W3 do PLAN-174 como item nomeado.** A W3 de lá
   (`.claude/plans/PLAN-174-ceremony-generation.md:125-126`: «estender
   `generate-ceremony.sh` para emitir cortes rc/GA de input declarativo, o
   gerado passando `bash -n` + lint por construção, corpo ASCII-safe») deixa
   de ser extensão de um gerador que vai sair e passa a ser um MODO do
   toolkit, entregue na subwave da aposentadoria (§Items, W2). Aposentar o
   gerador sem essa capacidade perderia uma função já planejada.
3. A suíte `.claude/scripts/local/tests/test_generate_ceremony.sh` migra para o
   toolkit ou é aposentada na MESMA subwave — é a alínea (a) acima, agora com
   dono e data.

O que esta decisão NÃO faz: ela não muda o gate da aposentadoria (o gerador só
sai quando o último pacote migrar) nem antecipa a OQ-2 (a ordem das subwaves
segue do Owner).

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
   UID nenhum. **O BRAÇO do marcador é decidido AQUI, antes da W0 (round 2,
   K2), e não é nenhum dos dois que o texto anterior oferecia.** Os dois eram
   inseguros de formas opostas: sentinela de CONTEÚDO no fixture põe a isenção
   DENTRO do material que o guard existe para julgar; variável de AMBIENTE do
   harness é herdada por todo processo filho, inclusive o `sign.sh` do Owner —
   a classe de carrier que `CLAUDE.md` §5 registra ter sido curada por
   NEUTRALIZAÇÃO no import, não por enumeração. **Decisão:** o marcador é um
   ARGUMENTO EXPLÍCITO do guard (`--selftest-fixtures <path>`), cujo valor é um
   arquivo FORA da árvore do material; ele não é herdado por filho nenhum e não
   existe como byte dentro de nada que seja assinado. TRÊS controles vermelhos:
   (i) material sob a árvore de scratchpad, sem o argumento, REPROVA; (ii)
   material que CARREGA a sentinela de conteúdo do rascunho, e um processo com
   a variável de ambiente do rascunho exportada, REPROVAM do mesmo jeito — é o
   controle que prova que os dois canais estão MORTOS, não apenas
   desaconselhados; e (iii) **material MARCADO fora do self-test REPROVA** —
   um arquivo que se declara fixture (pelo nome, por um cabeçalho, ou por
   qualquer marca CARREGADA por ele) e que NÃO está no arquivo apontado por
   `--selftest-fixtures` continua reprovando. É o controle que o round 2 exigiu
   nesses termos (K2: «controle vermelho que reprove material MARCADO fora do
   self-test») e o que torna a escolha do braço verificável: a isenção vem do
   ARGUMENTO, nunca do material.
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
    **O rail da própria allowlist, nomeado para o leitor não supor gate único
    (round 2, K10):** `.claude/sentinel-signers.txt` casa `_KERNEL_PATHS`
    (`.claude/hooks/check_arbitration_kernel.py:85`), o guard de arbitragem
    fail-closed — logo consolidar as 33 checagens nela não cria ponto único
    forjável por Edit. Medido, e registrado porque contraria a leitura fácil:
    `python3 .claude/hooks/check_canonical_edit.py --is-canonical
    .claude/sentinel-signers.txt` responde `.claude/sentinel-signers.txt	0`,
    isto é, o `check_canonical_edit.py` NÃO é o guard desse arquivo — o round 2
    (K10) sugeria nomeá-lo como segundo rail, e a medição diz que ele não é. O segundo
    rail é a assinatura em si: forjar exige editar um arquivo guardado pelo
    kernel **e** possuir uma chave privada.

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
  assinatura» seria falsa. Por isso a W0 acrescenta um QUARTO sítio no mesmo
  patch, ao lado dos três sítios de lint, com controle POSITIVO: um PR que toca
  só um arquivo do toolkit tem de EXECUTAR o step de integridade.
  **O que esse quarto sítio compra é LATÊNCIA, não a primeira visibilidade — a
  redação «e só com ele» era falsa e sai (round 3, M7).** Duas medições a
  derrubam, por caminhos independentes: (a)
  `.github/workflows/ownership-nightly.yml:19-24` dispara por
  `schedule: cron "43 6 * * *"` + `workflow_dispatch`, **sem `paths:`** — e o
  cabeçalho do próprio arquivo (`:6-10`) registra que eventos `schedule`
  IGNORAM filtros de `paths:` —, e `:59-66` roda o MESMO `shasum -a 256 -c`
  sobre o mesmo manifesto: a detecção post-hoc já existe hoje, em ≤ 24 h;
  (b) o step de integridade só cobre MEMBROS do manifesto, e a entrada do
  toolkit no manifesto é entrega do AC-6, isto é, da W1 — entre a W0 e a W1 o
  step roda e PASSA. A promessa correta, escrita como o plano a assume:
  **o quarto sítio antecipa a detecção do nightly para o tempo de PR, e só
  passa a cobrir o toolkit depois que o AC-6 o puser no manifesto** — gatilho
  (W0) e membresia (W1) são as duas metades, e nenhuma sozinha entrega
  visibilidade.
  **O instrumento dos três controles positivos é NOMEADO, e prova o predicado,
  não o motor de eventos do GitHub (round 3, M12).** Sem instrumento, «um PR
  que toca só o toolkit dispara o workflow» prova um NOME no YAML. O
  instrumento é um caso novo em `.claude/scripts/tests/test_release_workflow_asserts.py`
  (oráculo `--is-canonical` = **0**, arquivo que já existe e já é coletado pelo
  `pytest.ini`), reusando o extrator `_workflow_paths_lists` (`:1095-1134`, que
  devolve as listas `paths:` de `pull_request` e `push` de um workflow) na
  mesma forma do `test_ownership_paths_present_in_both_filters` (`:1167-1174`):
  o caso lê as duas listas do `ceremony-lint.yml` e as do workflow do quarto
  sítio, e casa por `fnmatch` cada path concreto —
  `.claude/scripts/ceremony/lib.sh`, `.claude/scripts/check-ceremony-script.py`
  e `.claude/scripts/ceremony-lint-waivers.json` — contra os globs declarados.
  Controle VERMELHO: remover uma das entradas novas faz o caso reprovar.
  Limite escrito: isso prova o PREDICADO de gatilho (glob × path), não a
  fiação do motor de eventos — o precedente da casa para essa distinção é
  `.claude/hooks/tests/test_workflows_class_guard.py`, que testa o predicado de
  classificação e não a fiação do hook.
  **ONDE mora esse sítio é decisão da OQ-9, porque o CUSTO foi medido
  (round 2, K1):** o `smoke-install.yml`
  tem UM job (`smoke`, `.github/workflows/smoke-install.yml:193`,
  `runs-on: ubuntu-latest` em `:196`) com `timeout-minutes: 150` (`:337`), e
  `CLAUDE.md` §5 registra duas execuções reais de **1 h 08** e **58 min**;
  o step que interessa (`:355-360`) é um `shasum -a 256 -c` de segundos. Pôr
  `.claude/scripts/ceremony/**` e `.claude/governance/gate-scripts-manifest.txt`
  nos dois `paths:` desse workflow faz todo PR do
  toolkit pagar a hora inteira para rodar um checksum. **Alternativas
  nomeadas** — a escolha é da OQ-9, promovida a pré-condição da W0: (i) as duas
  entradas nos `paths:` do `smoke-install.yml`, aceitando a hora por PR;
  (ii) um JOB próprio dentro do `smoke-install.yml`, com `if:`/`paths` que o
  faça rodar sozinho quando só o toolkit muda; (iii) o step de integridade
  ADR-192 REPLICADO num workflow BARATO, disparado pelo `paths:` do toolkit e
  do manifesto, **sem tirar o step de dentro do job `smoke`** (rail r2 M1).
  Mover o step para fora seria um erro de ORDEM, não de custo: o
  `ADR-192:49-53` exige a verificação «fail-closed e ANTES de qualquer membro
  ser invocado», e o job `smoke` instala o framework e EXECUTA o
  `validate-governance.sh` entregue — dois workflows separados não têm ordem
  entre si, então a relocação deixaria o consumidor rodando antes do checksum.
  A opção (iii) é portanto ADITIVA: o step barato responde pelo PR que toca só
  o toolkit, o step de dentro do job continua respondendo pela ordem.
  **A superfície de gatilho do quarto sítio, em QUALQUER das três opções, é a
  do manifesto INTEIRO (rail r1 #5):** `.claude/scripts/ceremony/**`,
  `.claude/governance/gate-scripts-manifest.txt` **e** os dois arquivos que o
  AC-6 absorve — `.claude/scripts/check-ceremony-script.py` e
  `.claude/scripts/ceremony-lint-waivers.json`. Sem os dois últimos, um PR que
  edite SÓ o checador, ou que só acrescente um waiver, entra no manifesto sem
  nunca executar o `shasum -c` — que é exatamente o buraco «membresia sem
  execução» que este parágrafo existe para fechar. O controle positivo passa a
  ser TRÊS: um PR que toca só um arquivo do toolkit, um que toca só o checador
  e um que só acrescenta uma entrada de waiver — os três têm de EXECUTAR o step
  de integridade. O plano não escolhe
  por conta própria porque as três têm custo de runner diferente e a decisão é
  de orçamento; o que ele fixa é que ALGUM sítio existe no MESMO patch da W0,
  com o mesmo controle positivo: um PR que toque só um arquivo do toolkit tem
  de EXECUTAR o step de integridade.
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
mensagem de commit**, como `.claude/plans/PLAN-SCHEMA.md:441` exige (path
completo, round 2, K11); e cada uma DECLARA o
corte do modelo de operação v2 (≤ 400 linhas alteradas OU ≤ 8 paths por
pacote), que o rascunho estourava sem dizer (round 1, K4).

**W0 — leitor do manifesto, `lib.sh` e o subconjunto falsificável.** Gate:
**canônico por DOIS paths** — os scripts do toolkit são oráculo 0, mas a cura
do C1 põe `.github/workflows/ceremony-lint.yml` (oráculo **1**) e a do C5 põe
um workflow no mesmo patch, e são eles que decidem, respectivamente, se o lint
e o step de integridade enxergam o toolkit (§Riscos). O gate NÃO depende de
QUAL workflow a OQ-9 escolher para o quarto sítio: todo `.github/workflows/*`
é oráculo 1, então a W0 é canônica nos dois braços. A W0 do rascunho dizia «livre» pela razão refutada; ela é
canônica pela razão medida.
- Arquivos: `.claude/scripts/ceremony/lib.sh`,
  `.claude/scripts/ceremony/read_manifest.py`, e UM arquivo de controle por
  invariante falsificável — `controls/inv1_rail_set.sh`,
  `controls/inv3_abs_path.sh`, `controls/inv4_baseline.sh`,
  `controls/inv5_scope.sh`, `controls/inv10_signer.sh`, mais o runner
  `controls/run.sh` [todos criados na W0]. **ARQUIVO não é a unidade do
  aceite (round 3, M8):** o `inv3_abs_path.sh` carrega TRÊS vermelhos com id
  próprio — `inv3a` (sem o argumento), `inv3b` (sentinela de conteúdo +
  variável de ambiente do rascunho) e `inv3c` (material MARCADO fora do
  self-test) —, de modo que os 5 arquivos de controle (o `run.sh` é o runner,
  não um controle) entregam **7** vermelhos, e é essa enumeração que o runner
  imprime. E, no MESMO patch, os TRÊS arquivos
  de gate — (1) `.claude/scripts/check-ceremony-script.py`, que recebe o
  PREDICADO de descoberta por diretório (`.sh` **e** `.py` sob o toolkit root,
  §Approach decisão (a)) além da entrada em `DISCOVERY_ROOTS`, o escopo
  alargado da R8 e o comentário de `:192-194` emendado junto (decisão (c));
  (2) `.github/workflows/ceremony-lint.yml` (+`paths:` nos dois gatilhos); e
  (3) o QUARTO sítio, que dispara o step de integridade ADR-192 para o toolkit
  — as duas entradas nos dois `paths:` do `.github/workflows/smoke-install.yml`
  **ou** o workflow barato que o substitua, conforme a OQ-9 (§Riscos: o job
  `smoke` é único e custa ~1 h para rodar um `shasum -c` de segundos); e, no
  mesmo patch, as DUAS suítes que a CI já coleta e que a mudança desmente
  (round 3, M5 e M12) — `.claude/scripts/tests/test_check_ceremony_script.py`
  (o predicado novo e a R8 alargada) e
  `.claude/scripts/tests/test_release_workflow_asserts.py` (o casador de
  `paths:` dos controles de EVENTO).
- Aceite: AC-1, metade W0. As invariantes que `lib.sh` falsifica SOZINHO são
  **1, 3, 4, 5 e 10** — todas predicados sobre ARQUIVOS. As invariantes 2, 6, 7
  e 8 são propriedades de `land.sh` e `harness.sh`, que só existem na W1
  (round 1, C6): controle sem o objeto que ele falsifica é verde vacuoso, o
  oposto do que a W0 promete provar.
- **QUEM escreve o arquivo que cada controle da W0 falsifica (round 2, K5).**
  Três das cinco invariantes estão DEFINIDAS em termos de escritores da W1 — a
  1 fala em «pinados por sha256 gravado pelo `finalize`», a 4 em «escritos SÓ
  pelo finalize» e a 5 em «`sign.sh` regenera e compara» —, e sem esta tabela a
  justificativa «todas predicados sobre ARQUIVOS» fica incoerente. Na W0 o
  ESCRITOR é sempre a fixture do próprio controle; o escritor de PRODUÇÃO chega
  na W1, e o que a W0 prova é o LEITOR/COMPARADOR de `lib.sh`, não a disciplina
  de escrita:

  | inv. | arquivo falsificado | quem o escreve na W0 | quem na produção (W1) |
  |---|---|---|---|
  | 1 | `ceremony.tsv` + registros de rail pinados | fixture de `controls/inv1_rail_set.sh` | `finalize.sh` |
  | 3 | material com path absoluto fora do repo | fixture de `controls/inv3_abs_path.sh` | qualquer material do pacote |
  | 4 | `EXPECTED-BASELINE` / `BASE-SHA` | fixture de `controls/inv4_baseline.sh` | `finalize.sh` |
  | 5 | arquivo de escopo do sentinel | fixture de `controls/inv5_scope.sh` | `finalize.sh` ou `apply-<key>.py --describe` (OQ-7) |
  | 10 | `.asc` + chaveiro GPG descartável | fixture de `controls/inv10_signer.sh` | o Owner, na assinatura |

  Consequência escrita, não escondida: a metade «escrito SÓ pelo finalize» das
  invariantes 4 e 5 é falsificável apenas na W1, e migra para o aceite dela
  junto com as invariantes 2, 6, 7 e 8. A fixture da inv. 10 precisa de um
  chaveiro GPG descartável que nenhum runner semeia hoje — custo que a OQ-9
  passa a cobrir.
- Corte v2: **13 paths** (2 de biblioteca + 6 de controle + 3 arquivos de gate
  + 2 suítes que o CI já coleta) — **e 13 é o piso, não o total: a contagem
  depende da OQ-9** (rail r1 #1; as duas suítes entraram no round 3, M5 e M12).
  Se ela puser o quarto sítio num workflow BARATO próprio e/ou o runner
  de controles noutro workflow, cada um desses é um path a mais — e o branch
  «step no `validate.yml`» acrescenta ESSE arquivo, que hoje não está nem na
  W0a nem na W0b: **14 paths**, não 13 (rail r2 M2). Pior que a aritmética:
  `.github/workflows/validate.yml` é path de KERNEL
  (`.claude/hooks/check_arbitration_kernel.py:144`), então a cerimônia de
  sentinel COMUM da W0 não autoriza essa edição — ela exige a rota de kernel.
  **Decisão:** o executor do runner é uma SUBWAVE própria (`W0c`), com o seu
  file assignment e o requisito de kernel escrito nele; nenhum braço da OQ-9
  entra na W0a por acidente. Contagem por braço: **13** com o quarto sítio no
  `smoke-install.yml` e o runner FORA da W0; **14** quando um workflow entra;
  **15** quando entram dois. A W0 reconta os paths depois da decisão e antes de
  abrir o patch. Em qualquer dos braços isso ESTOURA a metade
  «≤ 8 paths» do critério. A W0 só passa
  pela outra metade da disjunção, «≤ 400 linhas alteradas», e a wave MEDE isso
  sobre a árvore STAGED — `git add -A` e então
  `git diff --cached --numstat` —, nunca com `git diff` sozinho: oito dos treze
  arquivos da W0 são NOVOS, e o `git diff` do working tree não conta arquivo
  não-rastreado, o que faria a medição admitir um pacote que estoura os DOIS
  tetos. É a mesma ordem que `CLAUDE.md` §4 impõe aos gates de corpus
  («`git add -A` → gates sobre a árvore staged → `git commit`»). Se não couber,
  a divisão concreta nomeia ARQUIVOS, não categorias (round 2, K4 — a redação
  anterior dizia «manifesto» para um artefato que a W0 não entrega: o
  `ceremony.tsv` é da W1, e `lib.sh` não aparecia em metade nenhuma):
  **W0a = 7 paths** — `.claude/scripts/ceremony/lib.sh`,
  `.claude/scripts/ceremony/read_manifest.py`,
  `.claude/scripts/check-ceremony-script.py`,
  `.github/workflows/ceremony-lint.yml`, o QUARTO sítio escolhido pela OQ-9
  (`.github/workflows/smoke-install.yml` ou o workflow barato que o substitua)
  **e as DUAS suítes que a CI já coleta e que esta subwave desmente (round 3,
  M5 e M12)**: `.claude/scripts/tests/test_check_ceremony_script.py` — 198
  linhas, `pytest.ini:41` lista `.claude/scripts/tests` em `testpaths`, o
  harness `make_repo` (`:35-44`) planta o fixture sob
  `<tmp>/.claude/plans/PLAN-999` e roda `--root <tmp> --floor 1`, e
  `test_r8_exec_bit_under_plans_is_blocking` (`:104-109`) afirma a forma ANTIGA
  da R8; sem ela no patch, o PREDICADO novo (`.sh` **e** `.py` por diretório
  sob o toolkit root) e a R8 alargada nascem sem um único teste na bateria que
  a CI roda. A segunda é
  `.claude/scripts/tests/test_release_workflow_asserts.py`, que hospeda o
  casador de `paths:` dos controles de EVENTO (§Riscos, quarto sítio). As duas
  são oráculo `--is-canonical` = **0**, logo não mudam o gate da subwave.
  Armadilha de implementação a fixar aqui, achada pelo round 3 e verificada:
  `discover()` monta as raízes a partir do argumento `--root`
  (`check-ceremony-script.py:131`) enquanto o default dos waivers usa a
  constante `REPO_ROOT` (`:93`, `:288-291`) — um predicado de toolkit escrito
  contra `REPO_ROOT` fica INVISÍVEL para essa suíte inteira, que roda com
  `--root <tmp>`;
  **W0b = 6 paths** — `controls/inv1_rail_set.sh`, `controls/inv3_abs_path.sh`,
  `controls/inv4_baseline.sh`, `controls/inv5_scope.sh`,
  `controls/inv10_signer.sh` e `controls/run.sh`. **W0c = 0 ou 1 path,
  CONDICIONAL à OQ-9 (rail r3 C2)** — o executor do runner de controles:
  VAZIA no braço em que a OQ-9 não cria executor de CI; **um** path no braço
  que o cria. **A autorização da W0c é DERIVADA do path escolhido, não
  declarada aqui (rail r4 D2):** a lista `_KERNEL_PATHS`
  (`.claude/hooks/check_arbitration_kernel.py:85`) enumera NOMES de arquivo e
  não tem glob para `.github/workflows/*` — o `.github/workflows/validate.yml`
  do braço (i) está nela (`:144`) e a edição exige a rota de KERNEL; um
  workflow NOVO, criado pelo braço (ii), NÃO está, é canônico COMUM e a
  cerimônia de sentinel da W0 basta. Pedir override de kernel para um path que
  o kernel não guarda relaxaria a proteção sem necessidade. **A W0 não fecha com a W0c em aberto
  quando a OQ-9 escolhe um executor:** sem ela os sete controles vermelhos
  existem e ninguém os roda — exatamente a classe «a red gate nobody runs» que
  a D5 mandou fechar. Os quatro sítios de gate
  continuam no MESMO patch (W0a), que é a exigência do C1 e do C5; a W0b sem a
  W0a seria controle sem lint que o enxergue. Declarado aqui
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
- Aceite: AC-2, AC-6 e a metade migrada do AC-1 — controles das invariantes 2,
  6, 7 e 8, MAIS as duas metades de ESCRITA das invariantes 4 e 5 que a W0
  declara não-falsificáveis sem o `finalize.sh` (rail r1 #4), + o harness
  rodando a partir de um clone descartável em worktree. São **6/6**, não 4/4.
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
- **A subwave que migrar o ÚLTIMO pacote é a da APOSENTADORIA, e ela leva TRÊS
  entregas nomeadas (Owner, S348 — §Approach «Reconciliação»):** (i) o
  `generate-ceremony.sh` sai, e no MESMO patch `EXPLICIT_FILES`
  (`.claude/scripts/check-ceremony-script.py:66-68`) e o `paths:` do
  `.github/workflows/ceremony-lint.yml` deixam de citá-lo; (ii)
  `.claude/scripts/local/tests/test_generate_ceremony.sh` migra ou é aposentada
  junto; (iii) o **corte rc/GA de input declarativo** — a W3 herdada do
  `.claude/plans/PLAN-174-ceremony-generation.md:125-126` — nasce como MODO do
  toolkit. Se as três não couberem no teto v2 dessa subwave, ela se parte em
  duas (a regra de corte vale para qualquer `W2x`), e a segunda metade herda o
  gate canônico porque toca `.github/workflows/*`.
- Aceite: AC-3 — e o AC-3 só conta com o mapa COMPLETO (6/6, ver abaixo).
- Commit: `refactor(PLAN-188 w2<x>): <pacote> migra para o manifesto; clones
  assinados para custódia`.

**W3 — medição e ADR.** Gate: **CANÔNICO enquanto o ADR estiver nesta wave —
o rótulo «docs» era falso e sai (round 3, M4).** Medido com o oráculo do repo,
que classifica por PADRÃO de path e não exige que o arquivo exista:
`python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>` responde
**1** tanto para `.claude/adr/ADR-010-canonical-edit-sentinel.md` (existe no
HEAD) quanto para o nome ainda não criado do ADR desta wave — todo
`.claude/adr/*.md` é canônico, pela mesma razão medida que reclassificou a W0
(o último ADR do repo hoje é o `ADR-197`, então o número do novo é da OQ-1).
E o AC-5 exige um
`.asc` do Owner sobre o sentinel da wave, artefato que um pacote «docs» não
produz por construção. **As duas leituras possíveis, ambas escritas porque
QUAL delas vale é da OQ-1, não deste parágrafo:** (a) o ADR fica aqui e a W3
inteira é canônica, com sentinel e `.asc` como qualquer wave assinada; (b) a
OQ-1 põe o ADR (e a emenda ao ADR-010) noutra wave, e então o que resta na W3
— instrumento de medição, digest, listas e este plano — é oráculo **0** e a
wave é livre. O restante do file assignment não muda em nenhuma das duas.
- Arquivos: `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` [criado na W3 —
  sai daqui no braço (b) da OQ-1],
  `.claude/plans/PLAN-188/measure-rail-classes-v2.py` (o AC-4 exige `--since`
  obrigatório e a regra de classificação do toolkit — ver abaixo; sem esse
  arquivo no escopo, seguir este file assignment não satisfaz o AC-4),
  `.claude/plans/PLAN-188/measure-rail-classes-v2.sha256`
  [criado na W3 — rail r2 M4: o passo (1) do `Check:` do AC-4 roda
  `shasum -a 256 -c` contra ESTE arquivo, e um file assignment que não o
  entrega faz o AC-4 falhar antes de medir],
  **os DOIS artefatos que o `Check:` do AC-4 consome e que nenhuma wave
  entregava (round 3, M10)** —
  `.claude/plans/PLAN-188/cohort-records.sha256` [criado na W3: a LISTA
  sha256-pinada dos registros de rail dos três pacotes da coorte, no formato de
  `shasum -c`, sobre a qual a re-medição roda] e
  `.claude/plans/PLAN-188/rail-classes-rebased.txt` [criado na W3: a base
  RE-MEDIDA com a raiz `.claude/scripts/ceremony/**` já no classificador, que é
  contra quem o AC-4 compara — a saída congelada `s345-rail-classes.txt` fica
  como está, é a base da regra ANTIGA] —, e
  este plano. Contagem: **6 paths** no braço (a) da OQ-1, 5 no braço (b) — os
  dois dentro do teto v2. **A emenda ao ADR-010 NÃO é agendada aqui:** a OQ-1
  deixa com o
  Owner tanto o número `ADR-2xx` quanto a WAVE em que a emenda entra; enquanto
  ela estiver aberta, a emenda não pertence a wave nenhuma. Se o Owner a
  colocar na W3, `.claude/adr/ADR-010-*.md` entra neste file assignment (e a
  contagem sobe para 7).
- Aceite: AC-4 (com a OQ-5 já decidida) e AC-5.
- Commit: `docs(PLAN-188 w3): ADR do toolkit + medição da fração «cerimônia»`
  — o prefixo `docs(` descreve o CONTEÚDO, não o gate: no braço (a) da OQ-1
  esta wave é assinada como qualquer canônica.

## Acceptance criteria

- [ ] AC-1 (metades W0 e W1) Os scripts existem, `bash -n` + `shellcheck`
      limpos, sem path pessoal, com ≥ 1 controle VERMELHO por invariante
      **BLOQUEANTE — a invariante 9 é a exceção ESCRITA (round 3, M9)**: ela é
      ADVISORY por decisão registrada em §Approach («INFORMA e nunca recusa»,
      enquanto as âncoras forem propriedade do CLI de um terceiro), logo não
      tem controle vermelho em wave nenhuma, e um leitor que audite este AC
      pelo cabeçalho tem de contar 9 invariantes com controle, não 10.
      **O escopo da W0 é o subconjunto que `lib.sh` falsifica SOZINHO**
      (round 1, C6): invariantes 1, 3, 4, 5 e 10, todas predicados sobre
      arquivos. Os controles das invariantes 2, 6, 7 e 8 e «o harness rodando a
      partir de um clone descartável em worktree» dependem de `land.sh` e
      `harness.sh` e MIGRAM para o aceite da W1 — na W0 eles não teriam objeto
      para falsificar.
      Check (W0): `bash -n` + `shellcheck -S warning` nos scripts entregues; o
      runner de controles imprime **7/7** VERMELHO-antes / VERDE-depois; e
      `python3 .claude/scripts/check-ceremony-script.py --list` LISTA todos os
      arquivos do toolkit, os `.py` inclusive — a flag EXISTE hoje
      (`.claude/scripts/check-ceremony-script.py:266-268`, «só imprime os
      arquivos descobertos, um por linha») e imprime TODOS os descobertos, sem
      filtrar por rastreamento (`:283-286`), não é entrega de wave nenhuma.
      **A contagem é DERIVADA da enumeração, nunca digitada (round 3, M8).** O
      «5/5» que este Check publicava contava ARQUIVOS de controle (cinco, mais
      o runner), enquanto a invariante 3 sozinha exige TRÊS vermelhos nomeados
      em §Approach — (i) material sob a árvore de scratchpad sem o argumento,
      (ii) sentinela de conteúdo do rascunho + variável de ambiente exportada,
      (iii) material MARCADO fora do self-test. O piso real da W0 é **7
      vermelhos** distribuídos por 5 arquivos de controle (mais o runner, 6
      arquivos ao todo): `inv1`, `inv3a`, `inv3b`, `inv3c`, `inv4`, `inv5`,
      `inv10`. Um runner que agregue por ARQUIVO imprime «5/5» com dois dos
      três vermelhos da invariante 3 AUSENTES — que são justamente os que
      provam que os dois canais do rascunho estão mortos. Por isso o runner
      imprime `N/N` derivado da lista de ids que ele mesmo enumera, e este AC
      cita os ids, nunca um total digitado.
      **Controle POSITIVO da descoberta, REFEITO (round 2, D1): um arquivo do
      toolkit SEM nenhum token da `CEREMONY_OPS_RE`** (`:71-73` — sem `gpg`,
      sem `sentinel`, sem `VERDICT`) **tem de aparecer no `--list`.** O controle
      anterior era verde por construção: ele exigia um script com `|| true`
      numa linha de `gpg`, e a palavra `gpg` é ELA PRÓPRIA o token que torna o
      arquivo descoberto sob o predicado por conteúdo — o controle fornecia a
      condição que dizia medir e passaria mesmo com a cura ausente. Ele fica,
      mas na função certa: prova que a REGRA R2 dispara no toolkit, não que a
      DESCOBERTA funciona. Terceiro controle: um script do toolkit com exec-bit
      no índice REPROVA na R8. E o piso do lint não substitui nenhum dos três —
      pelo CENSO ÚNICO do §Riscos (worktree limpo, base declarada lá), o
      conjunto descoberto está muito acima do `floor` e quase todo ele vem de
      `.claude/plans/**`, então o conjunto pode perder o toolkit inteiro sem
      ficar vermelho.
      **Quarto controle — de EVENTO, não de descoberta (rail r1 #6):** um PR
      que toca SÓ um arquivo do toolkit tem de DISPARAR o `ceremony-lint.yml`
      pelo `paths:` novo. Descoberta e gatilho são perguntas diferentes — um
      lint que enxerga o arquivo mas nunca roda no PR é a mesma classe «a red
      gate nobody runs» —, e por isso os dois controles coexistem; o controle
      de evento do step de integridade ADR-192 é o do quarto sítio (§Riscos).
      **O instrumento é o casador de `paths:` nomeado no §Riscos** — o caso
      novo em `.claude/scripts/tests/test_release_workflow_asserts.py`, que
      reusa `_workflow_paths_lists` (`:1095-1134`) e casa por `fnmatch` os
      paths concretos contra os globs das duas listas; ele prova o PREDICADO de
      gatilho, não o motor de eventos, e o vermelho é remover a entrada nova.
      **Quinto controle — o filtro do consumidor do `--list`, executável
      (round 3, M2):** `--list` devolve o `.py` do toolkit e
      `--list --shell-only` não devolve nenhum `.py` (§Approach, decisão (a));
      vermelho = a segunda invocação devolver um `.py`. Não há contradição
      entre este controle e o anterior: o `--list` lista TODOS os descobertos
      por desenho (`check-ceremony-script.py:283-286`) e o filtro é do
      CONSUMIDOR — no `ceremony-lint.yml` são DOIS os consumidores do `--list`,
      `:51` (sumário) e `:78` (shellcheck), e só o segundo pede o subconjunto;
      o gate de `:39` invoca o checador sem argumento nenhum, logo não é
      consumidor do `--list` (round 3, M13).
      Falha = qualquer controle que passe com a invariante removida, o arquivo
      SEM token ausente do `--list`, um script do toolkit que o lint não
      enxergue, um PR do toolkit que não dispare o `ceremony-lint.yml`, ou o
      `--list --shell-only` devolvendo um `.py`. **O que SAIU desta lista
      (round 3, M2):** «o job `shellcheck-ceremony` recebendo um `.py`» não é
      critério de FALHA de CI, porque esse job não pode ficar vermelho —
      `ceremony-lint.yml:75` é `continue-on-error: true` e `:81-82` fecha em
      `|| true` (§Approach, decisão (a)). O sintoma continua real e é observado
      FORA do gate: o `shellcheck-ceremony.txt` do PR do toolkit acumula
      `SC1071`.
      Check (W1): **6/6** VERMELHO-antes / VERDE-depois — as invariantes 2, 6,
      7 e 8, com o harness rodando de um clone descartável em worktree, MAIS as
      duas metades de ESCRITA que a tabela da W0 declara não-falsificáveis lá
      (rail r1 #4): «`EXPECTED-BASELINE` e `BASE-SHA` escritos SÓ pelo
      `finalize`» (inv. 4) e «o arquivo de escopo escrito SÓ pelo `finalize`
      ou pelo `--describe`» (inv. 5). Na W0 essas duas foram provadas do lado
      do COMPARADOR, com o arquivo plantado por fixture; o lado do ESCRITOR só
      tem objeto quando o `finalize.sh` existe. Controle vermelho de cada uma:
      um arquivo cujo conteúdo DIFERE da regeneração pelo
      `finalize` (respectivamente pelo `--describe`) ⇒ recusa nomeada. O
      controle compara BYTES REGENERÁVEIS, não a identidade do processo que
      escreveu (rail r3 C1) — «escrito só pelo `finalize`» na forma literal
      não é falsificável por teste nenhum. **Limite declarado:** nem o
      manifesto nem estas invariantes autenticam o PRODUTOR; um segundo
      programa que escreva bytes idênticos aos que o `finalize` escreveria
      passa, e passar é o comportamento CORRETO sob este contrato. Autenticar
      proveniência de produtor (assinar o próprio artefato de baseline/escopo)
      é follow-up NOMEADO — `PLAN-188-FOLLOWUP-producer-provenance` —, nunca
      requisito de aceite da W1.
      Nota de custo (round 1, K6; round 2, D5 — a classe «a red gate nobody
      runs»): a metade «shellcheck limpo» já é automática E já cobre o endereço
      escolhido — `.github/workflows/validate.yml:341-359` roda
      `shellcheck -S warning` sobre `find .claude/scripts .claude/hooks -name
      '*.sh'`, que é recursivo, então todo `.sh` do toolkit entra sem sítio
      novo. A metade CARA é o runner de controles: hoje não tem workflow, não
      tem step e não tem custo de runner-minutos medido, e o controle vermelho
      da invariante 10 ainda pede um chaveiro GPG descartável que nenhum runner
      semeia (aquele step é o único de shell relevante e não invoca `gpg`).
      **O EXECUTOR é nomeado ANTES da W0:** a OQ-9 vira pré-condição e é
      reduzida a UMA pergunta — qual das três opções nomeadas executa o
      runner —, porque sem executor o AC-1 não FECHA; o custo em runner-minutos
      pode ser medido depois, o evento não.
- [ ] AC-2 Um pacote piloto (W6a) migra para o manifesto e assina/landa por
      `ceremony/sign.sh` + `land.sh` sem script próprio.
      **O Check do round 1 tinha a MESMA vacuidade que o C2 curou no AC-3
      (round 2, K6):** «o commit landado não referencia nenhum
      `OWNER-*-{SIGN,LAND}.sh` próprio» já é verdade ANTES do trabalho, porque
      os pacotes ficam fora do repo (§Context) e
      `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0** no HEAD — a pergunta
      responde «não» tanto se a migração acontecer quanto se ela fracassar.
      O AC-2 herda, portanto, a forma do AC-3:
      Check: (a) a linha `W6a → <PK>/<diretório do pacote>` existe no MAPA das
      seis chaves definido no AC-3, escrita pela W1; (b) esse diretório tem
      `ceremony.tsv` e NENHUM `OWNER-*-{SIGN,LAND}.sh`; (c) o `.asc` do sentinel
      verifica contra `.claude/sentinel-signers.txt`.
      **Controle POSITIVO (obrigatório):** plantar um `OWNER-W6a-SIGN.sh` no
      diretório do piloto faz o Check ficar VERMELHO; se não ficar, o
      instrumento está morto e o AC não conta.
      **Critério de morte pré-registrado:** corpus `<PK>` indisponível na sessão
      que mede ⇒ **NÃO CONCLUSIVO**, nunca «falhou».
      Falha = o piloto precisar de um script clonado, ou o controle positivo não
      reprovar.
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
      **Critério de morte pré-registrado (round 2, K7 — o AC-4 tinha, o AC-3
      não):** os seis diretórios do mapa vivem FORA do repo, na árvore de
      trabalho `<PK>`; se `<PK>` não estiver disponível na sessão que mede, o
      AC-3 sai **NÃO CONCLUSIVO** — nem «passou» nem «falhou» —, com o porquê
      escrito, e a medição é refeita numa sessão que tenha o corpus. O AC-3 só
      fica VERDE numa sessão em que (a) o mapa esteja completo 6/6, (b) os seis
      diretórios sejam legíveis e (c) o controle positivo tenha rodado nessa
      MESMA sessão. Ausência de corpus nunca é evidência de migração.
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
      (`shasum -a 256 <esse path>`, no HEAD deste plano).
      **O pin é CONFERIDO por máquina, não é prosa (round 2, K8):** um valor
      esperado digitado num plano é exatamente a classe «instrumento verde cuja
      pergunta envelheceu», e a W3 edita esse binário por desenho. A wave da
      medição grava o digest em
      `.claude/plans/PLAN-188/measure-rail-classes-v2.sha256`
      [criado na wave da medição], no formato de `shasum -c`, e o `Check:`
      abaixo roda `shasum -a 256 -c` contra ele ANTES de ler qualquer número;
      digest que não bate ⇒ a medição não acontece. O leitor desse arquivo é o
      `Check:` do próprio AC — o instrumento NÃO entra no manifesto ADR-192,
      que pina scripts de GATE, e escrever que entra seria inventar membresia.
      Quando a W3 editar o binário, o digest novo é gravado no MESMO arquivo, no
      MESMO patch, e a base é re-medida com ele. A comparação só vale
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
      esse controle só é honesto se os INPUTS também estiverem congelados**,
      **e ele NÃO cobre a mudança de REGRA que o mesmo patch faz** (round 3,
      M6: a igualdade classe-a-classe é verde por construção sobre um corpus
      que precede o diretório do toolkit — ver o controle POSITIVO sintético
      logo abaixo).
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
      a medição roda sobre a LISTA sha256-pinada dos registros DESSES três,
      gravada em `.claude/plans/PLAN-188/cohort-records.sha256` [criado na W3,
      no file assignment dela — round 3, M10] — a
      mesma exigência que a base congelada já carrega. `--since` fica como
      filtro auxiliar dentro da coorte, nunca como seletor da amostra.
      Check, em DOIS passos e nesta ordem — o segundo só roda se o primeiro
      sair verde: (1) `shasum -a 256 -c
      .claude/plans/PLAN-188/measure-rail-classes-v2.sha256`
      [arquivo criado na wave da medição] confere o binário contra o digest
      gravado; digest que não bate ⇒ a medição não acontece e o AC não conta.
      (2) `python3 .claude/plans/PLAN-188/measure-rail-classes-v2.py
      --pack-dir <PK> --cohort <as 3 chaves de pacote> --since <TS>`
      [`--cohort` e `--since` criados na wave da medição] imprime `ceremony`
      com numerador e denominador para EXATAMENTE as 3 assinaturas da coorte,
      medidas pelo binário pinado, e a comparação é contra
      `.claude/plans/PLAN-188/rail-classes-rebased.txt` [criado na W3], a base
      RE-MEDIDA com a raiz nova — nunca contra `s345-rail-classes.txt`, que é a
      base da regra ANTIGA.
      **A migração MOVE defeitos para fora da classe medida — e isso é
      corrigido antes de a comparação valer.** Medido no HEAD, com o comando ao
      lado (`classify_path` de `measure-rail-classes-v2.py:52-64`, carregado por
      `importlib`), os arquivos do toolkit se espalham hoje por TRÊS classes:
      `.claude/scripts/ceremony/read_manifest.py` sai **`product`** (casa
      `PRODUCT_RE`, `:40`, `\.claude/scripts/[\w\-/]+\.py`);
      `lib.sh`, `sign.sh` e `land.sh` do toolkit saem **`other-path`**; e só
      `finalize.sh` e `harness.sh` já saem `ceremony`, por acidente de token
      (`CEREMONY_RE`, `:37`, casa `finalize[\w\-]*\.sh` e `harness`). O MESMO
      achado sobre um `OWNER-*-SIGN.sh` sai `ceremony`: o
      toolkit faria a fração cair só por mudar o parsing de lugar. A wave da
      medição acrescenta `.claude/scripts/ceremony/**` às raízes de `ceremony`
      no classificador, re-mede a base com a regra nova e grava o digest novo —
      é o mesmo pacote da entrega do `--since`. Sem isso, uma queda da fração
      não é evidência de nada.
      **Controle POSITIVO sintético da REGRA NOVA — obrigatório, e o único
      controle da mudança de REGRA que pode ficar vermelho (round 3, M6).** A
      igualdade classe-a-classe contra
      `s345-rail-classes.txt` NÃO responde por esta mudança: o corpus congelado
      é da noite de 04→05/09, o diretório do toolkit ainda não existia e
      `grep -c "scripts/ceremony" .claude/plans/PLAN-188/s345-rail-classes.txt`
      devolve **0** — a igualdade passa com a raiz nova certa, com um typo
      (`ceremonies/`, glob mal ancorado, ordem errada em relação a `TEST_RE`) ou
      com a mudança AUSENTE. Por isso a wave da medição entrega, no mesmo
      patch, DOIS blocos sintéticos e imprime as duas saídas na EVIDENCE:
      (i) POSITIVO — um bloco de achado citando
      `.claude/scripts/ceremony/read_manifest.py` classifica `product` sob as
      regras antigas e tem de classificar `ceremony` sob as novas; um bloco
      citando `.claude/scripts/ceremony/lib.sh` sai `other-path` antes e
      `ceremony` depois; (ii) NEGATIVO — um bloco citando
      `.claude/scripts/check_contamination.py` continua `product` nas duas
      (medido: `product` hoje), porque a raiz nova não pode alargar-se para o
      resto de `.claude/scripts/`.
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
      **O AC-6 ABSORVE também a autoridade do lint (round 2, D3), porque é
      entrega e não gosto:** `.claude/scripts/check-ceremony-script.py` e
      `.claude/scripts/ceremony-lint-waivers.json` entram no MESMO manifesto.
      Medido no HEAD, os dois são oráculo **0**, não casam `_KERNEL_PATHS`
      (`.claude/hooks/check_arbitration_kernel.py:85`, 110 padrões) e não estão
      entre os 9 membros — de modo que a cura do C1 (predicado de descoberta,
      `paths:`, escopo da R8) pode ser desfeita por um Edit livre, e a
      reprovação do toolkit pode ser apagada por um append de waiver. Sem esta
      absorção, tudo o que a W0 constrói tem uma porta lateral sem cerimônia.
      Check: `shasum -a 256 -c` sobre o manifesto passa com as linhas novas e
      falha em DOIS controles vermelhos obrigatórios, que são a evidência do
      AC — (i) um byte de `sign.sh` ou de `land.sh` muda sem bump do manifesto;
      (ii) **uma entrada é acrescentada ao `ceremony-lint-waivers.json` sem bump
      do manifesto**. Ver os dois vermelhos é parte do AC.
      **ONDE cada vermelho é observável — sem isto o (ii) é inalcançável
      (round 3, M3).** A verificação `shasum -c` do manifesto mora em QUATRO
      workflows (`ADR-192:49-53`) e **nenhum deles é disparado por um PR que
      toca o JSON de waivers**: `release.yml` roda em push de tag `v*` (`:3-6`),
      `npm-publish.yml` idem (`:82-85`), `ownership-nightly.yml` em `schedule` +
      `workflow_dispatch` sem `paths:` (`:19-24`) e o `smoke-install.yml` tem
      `paths:` sem NENHUMA entrada que case o JSON ou o manifesto. O sítio que
      torna o (ii) alcançável em tempo de PR é o QUARTO SÍTIO da W0, cuja
      superfície de gatilho é a do manifesto INTEIRO — `.claude/scripts/ceremony/**`,
      `.claude/governance/gate-scripts-manifest.txt`,
      `.claude/scripts/check-ceremony-script.py` **e**
      `.claude/scripts/ceremony-lint-waivers.json` (§Riscos, rail r1 #5): é ELE
      que liga o append de waiver ao `shasum -c`. Sem esse sítio no lugar, o
      (ii) só acende no corte de release, publish ou na nightly — post-hoc, não
      no PR. **E o CUSTO OPERACIONAL desta absorção, escrito porque é o outro
      lado da mesma moeda:** o append de waiver é hoje a rota de escape
      ROTINEIRA — 44 entradas ativas — e passa a exigir bump ASSINADO do
      manifesto; um append sem bump reprova, e se o esquecimento não for pego no
      PR, quem o descobre é o corte de release ou o publish, com o release
      travado até a cerimônia. Aceitar o AC-6 é aceitar esse custo.
      **Limite escrito, não nota de rodapé:** a verificação do ADR-192 mora em
      workflows (`ADR-192:49-53`), nunca num lançador local — isto é DETECÇÃO
      post-hoc. Ela também não fecha a rota `--waivers <path>` nem o
      `CEO_CEREMONY_LINT_UNLOCK`, que são decididos fora do arquivo; o que fecha
      a janela no ato da edição é a OQ-6.
      Falha = o toolkit ou os dois arquivos do lint shipados fora do manifesto,
      ou o bump feito sem que os dois controles vermelhos tenham sido vistos.

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
  `.claude/governance/gate-scripts-manifest.txt`, e é a W0 que acrescenta o
  QUARTO sítio (§Riscos) — nos `paths:` deste workflow ou no workflow barato
  que a OQ-9 escolher, porque o job `smoke` é único e custa ~1 h para rodar um
  `shasum -c` de segundos. **O que esse sítio muda é a LATÊNCIA da detecção, e
  só depois do AC-6 (round 3, M7):** o `ownership-nightly.yml:19-24` já roda o
  mesmo `shasum -a 256 -c` (`:59-66`) por `schedule` sem `paths:`, então um
  toolkit MEMBRO do manifesto alterado fora de cerimônia já apareceria em
  ≤ 24 h; o quarto sítio antecipa isso para o PR, e nada disso cobre o toolkit
  enquanto a membresia do AC-6 (W1) não existir. **Mas a
  proteção direta não é redundante, e por isso a OQ-6 é decisão de verdade:** a
  verificação do ADR-192 mora em workflows (`ADR-192:49-53`), nunca num lançador
  local, então uma assinatura feita com um `sign.sh` já modificado ACONTECE
  antes de qualquer reprovação. O que a OQ-6 escolhe é entre detecção post-hoc
  (só o manifesto) e prevenção no ato da edição (manifesto + hook) — e, enquanto
  estiver aberta, o §Riscos declara a janela como limite assumido.
- OQ-7 — **PROMOVIDA a PRÉ-CONDIÇÃO da W0 (round 2, K3), decisão do Owner:** o
  alcance do contrato `--describe`. A W0 o especifica e o exige de cada pacote
  migrado; nenhum derivador rastreado o implementa hoje. Em aberto: se o
  contrato é RETRO-aplicado aos derivadores dos 5 pacotes do AC-3 (custo por
  pacote) ou se `scope_generated_from` é chave OPCIONAL, caindo no braço (b) da
  invariante 5 (escopo gravado pelo `finalize`). **A escolha é entre BRAÇOS, não
  entre verificar e não verificar:** nenhum pacote migrado assina escopo que não
  tenha sido gerado e conferido. O que não é aceitável é a chave apontar para um
  comando inexistente — nem um pacote sem braço nenhum. **Por que é
  pré-condição, e não pergunta de execução:** o leitor do manifesto é ENTREGA da
  W0 e as suas recusas nomeadas incluem «chave desconhecida» e «chave
  obrigatória ausente» (§Approach), então as duas leituras produzem leitores
  DIFERENTES — no braço (a) a chave é obrigatória e a ausência dela é recusa;
  no braço (b) ela é opcional-por-construção, o leitor aceita as duas formas e
  recusa só a chave que aponte para comando inexistente. Escrever o leitor antes
  da escolha é escrever o leitor errado, e reescrevê-lo depois custa uma
  cerimônia. Como a OQ-3, esta é colhível AGORA — o round 3 já rodou.
- OQ-8 (Owner): o DESTINO dos clones. O plano já decide que clone de cerimônia
  JÁ ASSINADA vai para custódia e não para o `rm` — a razão está escrita em
  `.claude/scripts/check_contamination.py:299-301` («retained for
  chain-of-custody. Never re-executed») e `:321-326`. Em aberto: qual dos dois
  diretórios isentos recebe os clones migrados (`scripts/local/historical/` ou
  `archive/`), ou um terceiro; e se o clone que NUNCA assinou nada é removido ou
  também arquivado.
- OQ-9 — **PROMOVIDA a PRÉ-CONDIÇÃO da W0 (round 2, D5 + K1), decisão do
  Owner:** quem EXECUTA o runner de controles, em que evento — e, agora, onde
  mora o QUARTO sítio. Medido (round 1, K6):
  `.github/workflows/validate.yml:341-359` já roda `shellcheck -S warning`
  sobre `find .claude/scripts .claude/hooks -name '*.sh'`, que é recursivo,
  então a metade barata do AC-1 é automática e cobre o endereço novo; a metade
  CARA — rodar os controles vermelhos — não tem workflow, step nem custo de
  runner-minutos medido, e o controle da invariante 10 ainda pede um chaveiro
  GPG descartável que nenhum runner semeia hoje. Opções nomeadas, com a
  consequência de cada uma: (i) step no `validate.yml` — barato de escrever,
  paga o tempo dos controles em todo PR que o dispare; (ii) workflow próprio
  disparado pelo `paths:` do toolkit — isola o custo, exige um sítio novo;
  (iii) execução local exigida pelo `harness.sh` de cada cerimônia — custo zero
  de runner, mas volta a ser «a red gate nobody runs» fora da janela de
  assinatura, **e carrega uma consequência de SEQUÊNCIA que o Owner precisa ver
  antes de escolher (round 3, M11): o `harness.sh` é entrega da W1** («Arquivos:
  … `ceremony/harness.sh` [criados na W1]») **e não está entre os 6 paths da
  W0b**. Neste braço, os SETE controles vermelhos da W0 nascem sem executor
  NENHUM até a W1 — a janela que a promoção da OQ-9 a pré-condição existia para
  fechar reabre por escolha legítima. Quem escolher (iii) escolhe também uma de
  duas consequências, e a wave escreve qual: ou a metade W0 do AC-1 se desloca
  para o aceite da W1 (o mesmo tratamento que o plano já dá às invariantes 2, 6,
  7 e 8), ou o `harness.sh` é antecipado para a W0 — e aí ele deixa de ser
  entrega da W1 e a contagem de paths das duas subwaves muda. **Isto NÃO decide
  a OQ-9**; escreve o que o braço custa. **A OQ-9 passa a decidir junto o CUSTO do quarto sítio (K1):** as
  duas entradas no `smoke-install.yml` arrastam um job único de
  `timeout-minutes: 150`, medido em 1 h 08 e 58 min (`CLAUDE.md` §5), para
  executar um `shasum -a 256 -c` de segundos — as alternativas (job próprio,
  ou o step de integridade REPLICADO num workflow barato) estão escritas no
  §Riscos — e a regra que vale é a de LÁ, escrita uma vez: a réplica é
  ADITIVA e o step de dentro do job `smoke` NUNCA sai, porque dois workflows
  separados não têm ordem entre si e o `ADR-192:49-53` exige a verificação
  ANTES de qualquer membro ser invocado (rail r2 M1). Ler a opção (iii) como
  «mover» é lê-la contra o §Riscos — e removeria a verificação que hoje corre
  antes de o job `smoke` executar o `validate-governance.sh` entregue
  (rail r4 D1). É pré-condição porque sem executor nomeado o AC-1 não FECHA e a W0
  nasce com um controle que ninguém roda. O custo em runner-minutos pode ser
  medido depois da escolha; o evento, não. Colhível AGORA — o round 3 já rodou.
  **Recomendação REGISTRADA, não uma quarta opção (round 3, crítico único,
  deferido ao Owner):** a detecção post-hoc do `ownership-nightly.yml` já
  existe sem sítio novo (`:19-24` sem `paths:`, `:59-66` com o mesmo
  `shasum -c`), de modo que a escolha entre (i), (ii) e (iii) é entre
  LATÊNCIAS e custos de runner, não entre visível e invisível. Aceitar apenas a
  latência da nightly (≤ 24 h) é uma resposta possível do Owner; o plano não a
  numera como opção porque isso seria decidir a OQ.

## How to continue

**O ponteiro deste plano, escrito uma vez (round 2, K12):** o arquivo é
`.claude/plans/PLAN-188-shared-ceremony-toolkit.md`. **`.claude/plans/PLAN-188.md`
NÃO existe no HEAD** (`git ls-files .claude/plans/PLAN-188.md` não devolve nada;
o plano não afirma nada sobre o histórico, rail r1 #16);
`.claude/plans/PLAN-188/` é o DIRETÓRIO de
materiais (instrumento de medição, saída congelada e as rodadas do debate).
Prompts e runbooks que citem o caminho curto estão apontando para nada.

Primeira mensagem de uma sessão futura: «Leia
`.claude/plans/PLAN-188-shared-ceremony-toolkit.md` e os consensos do debate em
`.claude/plans/PLAN-188/debate/round-1/consensus.md` e
`.claude/plans/PLAN-188/debate/round-2/consensus.md` e
`.claude/plans/PLAN-188/debate/round-3/consensus.md`. O round 3 fechou
`RUN-ANOTHER-ROUND` com 4 consensos (C1-C4), 9 achados de crítico único e 14
must-fix (M1-M14), TODOS absorvidos neste arquivo — então um round 4, se
houver, revisa ESTA revisão. Duas decisões do Owner podem ser colhidas
em PARALELO, porque são pré-condições da W0: **OQ-7** (o braço do
`scope_generated_from`, que define o leitor) e **OQ-9** (quem executa o runner
de controles e onde mora o quarto sítio). Se o Owner marcar o
plano `reviewed`, execute a W0a — `lib.sh` + `read_manifest.py` + os TRÊS
arquivos de gate + as DUAS suítes que a CI já coleta — e depois a W0b, os
SETE controles vermelhos das invariantes 1, 3, 4, 5 e 10 mais o runner
`controls/run.sh` (seis ARQUIVOS, sete controles — a invariante 3 sozinha
carrega `inv3a`/`inv3b`/`inv3c`: o AC-1 espera 7/7, round 3 M8); e, se a OQ-9 tiver
escolhido um executor de CI para esse runner, a **W0c** — um path, pela rota
de KERNEL — ANTES de dar a W0 por fechada (rail r3 C2); os QUATRO sítios (predicado de descoberta em `DISCOVERY_ROOTS`,
escopo da R8, `paths:` do `ceremony-lint.yml` e o quarto sítio que a OQ-9
escolher) viajam no MESMO patch da W0a. Só então proponha a W1.»

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
- 2026-09-06 (S347): round 2 do debate L3 sintetizado
  (`.claude/plans/PLAN-188/debate/round-2/consensus.md`; três críticos `ADJUST`
  com 10 bloqueantes somados, veredito `RUN-ANOTHER-ROUND`; dos 15 must-fix do
  round 1, o sintetizador verificou 12 FECHADOS e 3 PARCIAIS em disco). Os 5
  achados de consenso (D1-D5) e os 15 must-fix do round 2 foram absorvidos
  NESTE arquivo: predicado de descoberta por DIRETÓRIO incluindo `.py`, com o
  controle positivo trocado por um arquivo SEM token de cerimônia (D1); as
  CINCO classes bloqueantes e a marca decidida arquivo a arquivo (D2); o ESCAPE
  do lint — 44 waivers por sha256 de conteúdo, `--waivers`,
  `CEO_CEREMONY_LINT_UNLOCK` — escrito, com os dois arquivos de autoridade
  absorvidos pelo AC-6 (D3); a R8 alargada com o modo de invocação declarado
  (D4); o executor do runner promovido a pré-condição e o custo do quarto sítio
  medido (D5, K1); o braço do marcador da invariante 3 decidido como argumento
  explícito (K2); OQ-7 e OQ-9 promovidas a pré-condições da W0 (K3, D5); W0a/W0b
  nomeando ARQUIVOS e a tabela de QUEM escreve o arquivo que cada controle
  falsifica (K4, K5); AC-2 com mapa e controle positivo (K6); AC-3 com critério
  de morte (K7); AC-4 com digest conferido por `shasum -c` (K8); o ganho de
  custódia do endereço novo escrito (K9); o rail da allowlist de signatários
  nomeado (K10); citações do `PLAN-SCHEMA.md` com path completo (K11); e o
  ponteiro do plano corrigido (K12). Round 3 devido; o plano segue `draft`.
- 2026-09-06 (S348): duas correções sobre a revisão acima. (i) **Refutação F1**
  — as figuras do lint que esta revisão passou a citar (122 descobertos, 121 de
  `.claude/plans/**`, 55 com BLOCKING) eram propriedade da ÁRVORE VIVA do
  mantenedor, cujos diretórios `staged/` são `gitignore`d; um checkout limpo
  devolve 109 / 108 / 42. Os números passaram a viver em UM censo (§Riscos),
  medido em worktree limpo com a base declarada, e os outros dois sítios
  APONTAM para ele em vez de repeti-lo. (ii) **Decisão do Owner (S348)**: o
  PLAN-174 vira `superseded_by: PLAN-188`, e a W3 dele — cortes rc/GA de input
  declarativo — passa a ser item NOMEADO da subwave de aposentadoria do
  `generate-ceremony.sh`, junto com a suíte `test_generate_ceremony.sh`
  (§Approach «Reconciliação», §Items W2). O plano segue `draft` e o round 3
  segue devido.
- 2026-09-07 (S348, noite autônoma, Owner ausente, land livre combinado):
  `p188-plan-r3` landado — a revisão do round 2 do debate L3 entra na árvore
  (52 ops, 15/15 must-fix com o denominador LIDO do consenso, 636/85 linhas),
  rebaseada em `a6629d0`: o censo do §Riscos volta a conferir com a medição em
  checkout limpo (`gen-figures.py` rc 0, 10/10 linhas), o colchete falso sobre
  a revisão de portfólio saiu e as duas citações do PLAN-174 apontam para as
  linhas que existem hoje (`:4-5` e `:125-126`). Sem rodada de codex por regra
  R1 do Owner (pacote de DOCS): o portão foi os gates de corpus + verificação
  do CEO + CI. Bateria: validate-governance COMPLETO 0 erros, staleness rc 0,
  claude-md-claims rc 0, env-hygiene rc 0, contamination rc 0, verify-counts
  rc 0 (15993 em [15193..16792]), validadores de plano 76 passed, âncoras
  43/43 na árvore VIVA, inventário 100 citações com OUT-OF-RANGE 0, oráculo 0.
  Controles negativos: sha do censo revertido rc 2, árvore não derivada rc 2,
  2.ª aplicação rc 2, `--root` ausente rc 2. O plano segue `draft`: o round 3
  do debate L3 continua devido.
- 2026-09-07 (S348): round 3 do debate L3 sintetizado
  (`.claude/plans/PLAN-188/debate/round-3/consensus.md`; três críticos `ADJUST`
  com 2 + 2 + 3 bloqueantes, veredito `RUN-ANOTHER-ROUND`, `design-coherent`
  NÃO concedido). Os 4 achados de consenso (C1-C4), os 9 de crítico único e os
  14 must-fix (M1-M14) foram absorvidos NESTE arquivo. A classe que o round
  fechou é UMA só, em sítios novos: **critério de aceite cuja metade vermelha
  não é alcançável pelo evento que deveria dispará-la** — a mesma do D1 do
  round 2. O que mudou de FATO: a justificativa do filtro de shell (o step
  `shellcheck-ceremony` é `continue-on-error` + `|| true`, logo NÃO devolve
  rc 1 — a razão passa a ser o ruído `SC1071` permanente, e o critério de falha
  vira o par `--list` × `--list --shell-only`); o AC-6 diz ONDE o vermelho do
  append de waiver é observável (o quarto sítio da W0, não os 4 workflows do
  ADR-192) e a que custo; a W3 deixa de ser rotulada «docs» (o oráculo responde
  1 para `.claude/adr/*.md`), com as duas leituras da OQ-1 escritas; as DUAS
  suítes que a CI já coleta entram na W0a (5 → 7 paths; corte v2 11 → 13); o
  AC-4 ganha controle POSITIVO sintético da regra nova do classificador (o
  corpus congelado tem 0 ocorrências de `scripts/ceremony`, logo a igualdade
  classe-a-classe é verde por construção) e os dois artefatos que o seu `Check:`
  consome; a suficiência «e só com ele» do quarto sítio cai (a nightly já roda
  o mesmo `shasum -c` por cron sem `paths:`); o piso de vermelhos da W0 passa de
  5 para **7**, com id por controle; a exceção da invariante 9 (ADVISORY) fica
  escrita no cabeçalho do AC-1; o instrumento dos controles de EVENTO é
  nomeado; a consequência do braço (iii) da OQ-9 é escrita DENTRO da opção; e o
  censo declara o mecanismo certo (o filtro `is_tracked`, não a `gitignore`).
  Nenhuma OQ foi decidida. O plano segue `draft`.

### Respostas do Owner às OQs (S348, 2026-09-07 ~05:1x–08:5x; AskUserQuestion; rótulos VERBATIM; registro em `s344-packs/OWNER-DECISIONS-S348-C.md`)

- Investimento da manhã: «Responder as OQs e construir a W0 (Recomendado)».
- OQ-2 (ordem de migração e janelas): «W6a → 169 W4.1 → w4b-gates-v2 → W1-widen; uma assinatura por manhã (Recomendado)». O PLAN-183 W1 sai pelos moldes por exceção explícita do Owner à regra R3 (mesma data).
- OQ-4 (cinco chaves de orçamento): «Ratificar a omissão (Recomendado)» — o frontmatter segue sem números inventados; cada wave imprime o que gastou.
- OQ-5 (instrumento): «(a) Corrigir o classificador e re-medir a base (Recomendado)» — os 6 limites + a raiz `.claude/scripts/ceremony/**` entram no classificador; a base de 23,1 % morre; as 3 assinaturas seguintes são medidas com o MESMO binário novo. Amostra intermediária com o binário antigo em `PLAN-188/s348-rail-classes.txt` (426 registros, 27 packs).
- OQ-6 (registro nos gates): «Manifesto + hook, na W1 (Recomendado)» — a entrada em `_CANONICAL_GUARDS` viaja no mesmo patch assinado do bump do manifesto (AC-6).
- OQ-7 (alcance do `--describe`): «(b) Chave opcional; sem ela, escopo gravado pelo finalize (Recomendado)» — o leitor aceita as duas formas e recusa só chave apontando para comando inexistente.
- OQ-8 (destino dos clones): «`scripts/local/historical/` para assinados; clone nunca assinado é removido (Recomendado)» — o clone removido fica registrado por digest no `STATE.md` do pack.
- OQ-9 (executor dos controles + 4.º sítio): «(ii) Workflow próprio e barato, disparado pelos paths do toolkit (Recomendado)» — replica o step de integridade (aditivo; o do `smoke` nunca sai), roda os controles vermelhos, semeia chaveiro GPG descartável. O arquivo de workflow é canônico (oráculo 1): nasce no pack da W0 e é assinado com ela.
- Corpus de defeitos do molde para a W0: `PLAN-188/ceremony-defect-corpus-S348.md` (17 classes; §3 propõe a invariante 11 «o leitor falha para cima», CM-09 na W1, controle de CM-10 do lado do SIGN, nuance de CM-12).
