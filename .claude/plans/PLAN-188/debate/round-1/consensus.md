---
plan: PLAN-188
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§Approach:104-106 — o ENDEREÇO do toolkit é decisão de gate, não de arrumação: `.claude/scripts/ceremony/` está fora de DISCOVERY_ROOTS e do paths-trigger do ceremony-lint; ou o destino muda, ou os dois sítios de descoberta viajam no MESMO patch da W0"
  - "§Items:155 + §Riscos:144-145 — a contradição «W0 livre» × «o toolkit landa por cerimônia própria» é resolvida no plano; a nota «oráculo 0 até serem referenciados por SIGN» é falsa e sai"
  - "§Approach:116 + invariante 5 (:130-131) — `scope_generated_from` deixa de nomear um comando inexistente; o contrato `--describe` vira entrega da W0 ou a chave sai do manifesto"
  - "§Approach:108-117 + OQ-3 — o formato do manifesto é decidido ANTES da W0 (tomllib não existe no piso 3.9); OQ-3 sobe de pergunta aberta a pré-condição da W0"
  - "AC-1 (:162-167) — o conjunto de 9 controles da W0 é reduzido ao subconjunto que `lib.sh` pode falsificar sozinho; os controles de `land.sh`/`harness.sh` migram para o AC da W1"
  - "AC-3 (:172-175) — o Check ganha um mapa pacote→path e um controle POSITIVO; como está, já é verde no HEAD e não pode ficar vermelho"
  - "AC-4 (:176-181) — instrumento congelado por sha256, `SINCE`/corpus como PARÂMETRO, denominador declarado e critério de morte; OQ-5 decidida antes de AC-4 virar critério"
  - "§Approach invariantes (:119-140) — +invariante de SIGNATÁRIO (allowlist `sentinel-signers.txt`), que 33 dos 48 clones rastreados já fazem e as 9 omitem"
  - "§Approach invariante 1 (:120-123) + invariante 9 (:139-140) — registros de rail pinados por digest, não por nome; a invariante 9 é reescrita contra a forma de saída atual do codex"
  - "§Items:156-157 — W1 e W2 declaram o corte do modelo de operação v2 (≤ 400 linhas OU ≤ 8 paths); W2 vira subwaves na ordem da OQ-2"
  - "§Approach — reconciliação explícita com `.claude/scripts/local/generate-ceremony.sh` (PLAN-073 §2, mesma tese): aposentar, absorver ou coexistir, com oráculo mecânico"
  - "ACs — membresia no manifesto ADR-192 vira AC próprio (o toolkit passa a ser gate de assinatura); §Riscos nomeia o bootstrap da primeira assinatura"
  - "§Items:157 — a remoção dos clones da W2 preserva a cadeia de custódia (a razão já escrita em `check_contamination.py`), por arquivo ou por decisão registrada"
  - "frontmatter — `depends_on` cita PLAN-186 (o piloto W6a é pacote de um plano `executing`); §Items ganha file assignment + AC + commit hint por item (PLAN-SCHEMA:441)"
  - "§Open questions — +OQ-6 (registro nos gates existentes), +OQ-7 (contrato `--describe`), +OQ-8 (destino dos clones), +OQ-9 (quem executa o runner de controles e a que custo)"
synthesized_at: 2026-09-06T02:10:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-188 — consenso do round 1

Três críticos, três `ADJUST`, 13 bloqueantes somados (4 + 4 + 5). Nenhum pediu
`REJECT`, e os três concordam na TESE: um conjunto de scripts + manifesto por
pacote é o corte certo, porque as sete classes da tabela de §Context são
propriedades do MOLDE, não de nenhuma wave. O que os três atacam é a mesma
coisa por três lentes: **o plano endurece o CONTEÚDO assinado sem endurecer o
GATE que o decide**. Toda claim abaixo foi verificada em disco no HEAD `bb68edf`
antes de virar ajuste; as que não sobreviveram estão em
`## Single-agent insights rejected / deferred`.

## Consensus findings (2+ agents flagged)

### C1 — CRITICAL — o endereço escolhido tira o toolkit do único lint de cerimônia (Critic-A, Critic-B)

Verificado: `.claude/scripts/check-ceremony-script.py:62-67` define
`DISCOVERY_ROOTS = [".claude/plans", ".claude/scripts/local/historical"]` mais
`EXPLICIT_FILES = [".claude/scripts/local/generate-ceremony.sh"]`; e
`.github/workflows/ceremony-lint.yml:5-17` dispara só por
`.claude/plans/**/*.sh` + 3 arquivos explícitos. `.claude/scripts/ceremony/`
não está em nenhum dos dois (verificado: o diretório ainda não existe).
As regras que deixariam de valer são BLOQUEANTES e nomeadas no catálogo do
próprio lint: R1 (proveniência), R2 (`|| true` em operação irreversível),
R3 (`grep … | tail` em parsing de VERDICT), R4 (`git add` de diretório),
R8 (exec-bit no índice).

A ironia é o achado: o script que passa a ser O gate da assinatura do Owner
nasce isento das cinco classes bloqueantes que hoje cobrem os clones que ele
substitui — e a isenção é silenciosa, do tipo «falso-verde por endereço».

**Severidade acordada:** CRITICAL. **Mitigação:** a W0 entrega, no MESMO patch,
a entrada em `DISCOVERY_ROOTS` **e** o `paths:` do workflow (as duas metades:
uma sem a outra dá lint que nunca roda, ou trigger que não descobre nada), com
controle POSITIVO — um script do toolkit com `|| true` numa linha de `gpg`
reprovando. **Landa em:** §Approach:104-106, §Items W0, +OQ-6.

### C2 — CRITICAL — o Check do AC-3 já é verde no HEAD e não pode ficar vermelho (Critic-A, Critic-B, Critic-C)

Medido: `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0**, e o próprio plano
(:54-56) diz que os pacotes citados ficam FORA do repo. O Check de AC-3
(:172-175) pergunta se `git ls-files` lista `OWNER-*-{SIGN,LAND}.sh` para os 6
pacotes — a resposta é «não» antes de qualquer trabalho, e continua «não» se a
migração fracassar. No mesmo comando existem **48** `OWNER-*(SIGN|LAND)*.sh`
rastreados (de PLAN-166..186), que o AC não distingue: a mesma consulta é ao
mesmo tempo vacuosa para o alvo e ruidosa para o resto.

**Severidade acordada:** CRITICAL (é um critério de aceite inobservável, a
classe «instrumento verde cuja pergunta envelheceu» que esta casa já pagou duas
vezes). **Mitigação:** o AC-3 declara um mapa pacote→path (onde cada um dos 6
vive hoje, rastreado ou não), o Check roda sobre esse conjunto, e o controle
positivo é um clone plantado que o faz ficar VERMELHO.
**Landa em:** AC-3 (:172-175).

### C3 — CRITICAL — o manifesto tem formato congelado e leitor indefinido (Critic-A, Critic-B, Critic-C)

Medido nesta máquina: `python3 -V` = **3.9.6** e `import tomllib` =
`ModuleNotFoundError` (`tomllib` é 3.11+; o piso declarado em `CLAUDE.md` §4 é
stdlib-only, ≥ 3.9). O plano congela TOML no §Approach:108-117 e deixa o leitor
em OQ-3 (:200-201). Isso não é uma pergunta aberta: é a decisão que determina
se o ponto onde o Owner assina vai parsear entrada com regex de shell — a
camada mais fraca — enquanto a doutrina da casa (`CLAUDE.md` §4) é fail-CLOSED
em falha de parse de INPUT.

**Severidade acordada:** CRITICAL para o sequenciamento (bloqueia a W0, que
entrega o schema). **Mitigação:** decidir o formato ANTES da W0. As duas formas
que o repo já tem dono para: TSV no molde de `scripts/delivery-routes.tsv` (3
leitores, precedente vivo) ou JSON lido por `python3 -c` (stdlib em 3.9). Em
qualquer das duas, o conjunto de RECUSAS nomeadas (chave desconhecida, chave
duplicada, valor multi-linha) entra na W0 com controle vermelho.
**Landa em:** §Approach:108-117, OQ-3 (promovida a pré-condição).

### C4 — HIGH — o AC-4 não é reprodutível e não tem critério de morte (Critic-A, Critic-B, Critic-C)

Verificado em `.claude/plans/PLAN-188/measure-rail-classes-v2.py`: `SINCE` é um
literal congelado (`:32`, `'2026-09-04 20:00'`) e o filtro do corpus é
`os.path.getmtime(f) >= SINCE` (`:123`) — **mtime, não conteúdo**: um `touch`
ou um `git checkout` re-datam arquivos e mudam o corpus sem mudar um byte de
achado. O corpus vive fora do repo (plano :54-56) e a evidência do Check pede
`--pack-dir <árvore dos pacotes>`, isto é, um path que tende a ser pessoal num
plano rastreado. O denominador é livre (a fração cai se OUTRAS classes
crescerem, sem nenhuma cerimônia melhorar) e o instrumento não é pinado por
sha256 — a parte medida pode editá-lo. Some-se a OQ-5(vi), que o próprio plano
já registra: um path sob `tests/` na raiz sai classificado `ceremony`,
inflando exatamente a fração que o AC-4 compara.

**Severidade acordada:** HIGH. **Mitigação:** OQ-5 decidida ANTES de o AC-4
virar critério (corrigir o classificador e re-medir a base, ou congelar e
comparar igual-com-igual — mas escrito); `SINCE` e corpus viram PARÂMETROS
explícitos (a lição «parâmetro que muda o veredito não tem default»);
instrumento pinado por sha256 no plano; denominador declarado (numerador E
denominador citados, não só a razão); e critério de morte pré-registrado.
**Landa em:** AC-4 (:176-181), OQ-5.

### C5 — HIGH — o toolkit vira o gate de toda assinatura sem cadeia de autoridade (Critic-A, Critic-B, Critic-C)

Medido: o oráculo responde `.claude/scripts/ceremony/sign.sh 0` — NÃO canônico
— e `_CANONICAL_GUARDS` (`check_canonical_edit.py:115+`) é lista ESTÁTICA por
path (nomeia `.claude/hooks/*.py`, `.claude/scripts/lessons.py`, SKILL.md etc.;
nenhum prefixo `ceremony/`), logo continuará respondendo 0 depois de a W1
referenciá-lo. E `.claude/governance/gate-scripts-manifest.txt` pina **9**
scripts de gate por sha256 (`verify-counts.sh`, `validate-governance.sh`,
`release.sh`, `_release_tag_guard.py`, `validate-pair-rail-verdict.py`, …);
o PLAN-188 cita ADR-192 como leitura (:24) e não o menciona em nenhum AC.

Resultado: o script que decide se a assinatura do Owner acontece seria editável
sem sentinel e sem checksum — enquanto o `verify-counts.sh`, que só conta,
tem os dois.

**Severidade acordada:** HIGH. **Mitigação:** AC próprio para a membresia
ADR-192 dos scripts de gate do toolkit; decisão explícita sobre entrar em
`_CANONICAL_GUARDS` (é ela que define se a W0 é livre ou canônica — ver C6); e
o bootstrap escrito: a primeira versão é assinada pela cerimônia velha, e isso
é um FATO do plano, não uma nota de rodapé.
**Landa em:** ACs, §Riscos:144-145, +OQ-6.

### C6 — HIGH — «W0 livre» contradiz «o toolkit landa por cerimônia», e a razão dada é falsa (Critic-A, Critic-C)

O plano diz em :144-145 que «os scripts são GATE de assinatura ⇒ a wave é L3 …
o toolkit landa por cerimônia própria» e em :155 que a W0 é **livre**, com a
razão «oráculo 0 até serem referenciados por SIGN». A razão é falsa por
construção (C5: a lista é estática por path — o oráculo não muda de resposta
quando alguém referencia o arquivo). E a W0, como escrita, entrega os 9
controles vermelhos «sem consumidor», mas as invariantes **2, 6, 7 e 8** são
propriedades de `land.sh` e `harness.sh`, que só chegam na W1 — e o AC-1
(:162-167) exige «o harness rodando a partir de um clone descartável em
worktree». Um controle sem o objeto que ele falsifica é verde vacuoso: o
oposto do que a W0 promete provar.

**Severidade acordada:** HIGH. **Mitigação:** a W0 declara o subconjunto de
invariantes que `lib.sh` pode falsificar SOZINHO (1, 3, 4, 5 são candidatas —
todas são predicados sobre arquivos), com controle vermelho de verdade; os
controles de 2/6/7/8 e o harness migram para o AC da W1; e a linha de gate da
W0 passa a citar a razão VERDADEIRA (o que a canonicidade e o ADR-192 decidirem
em C5), não a razão refutada.
**Landa em:** §Items:155, §Riscos:144-145, AC-1.

### C7 — MEDIUM — o guard de path absoluto nasce com um path desta máquina dentro (Critic-A, Critic-B, Critic-C)

A invariante 3 (:125-127) declara «único allow por regex: o glob de self-test
`claude-501/*/scratchpad`». Esse literal é o scratchpad REAL desta máquina: o
guard construído para impedir path pessoal em material assinado nasce com uma
isenção que casa justamente a árvore onde o path pessoal desta máquina vive —
e, pior, um material assinado colocado sob ela passaria.

**Severidade acordada:** MEDIUM (P3 para dois críticos, P2 para um; adotado
MEDIUM porque a superfície é o material ASSINADO). **Mitigação:** a exceção do
self-test não é um literal de máquina: é um marcador que o próprio self-test
injeta (variável de ambiente do harness, ou um sentinela de conteúdo no
fixture), de modo que a regra publicada não conheça nenhum UID.
**Landa em:** §Approach invariante 3 (:125-127).

## Single-agent insights kept

1. **K1 (Critic-B, R-DO2) — já existe dono para «nunca escreva uma cerimônia à
   mão», e o plano não o reconcilia.** Verificado:
   `.claude/scripts/local/generate-ceremony.sh:2-7` diz literalmente que
   substitui escrever `OWNER-CEREMONY.sh` do zero (PLAN-073 §2) e traz seis
   guards pré-emissão G1-G6 (`:17-30`), incluindo G1 «cada `--canonical-paths`
   casa um padrão de `_CANONICAL_GUARDS`» e G6 «o sentinel declara TODOS os
   paths» — parentes diretos das invariantes 3 e 5 propostas. §Approach e a W2
   nunca o citam. É a FORMA exata dos defeitos D1-D4 (S322-S327): a ORIGEM
   tinha dono, a ROTA não. **Aceito:** o plano declara o destino
   (aposentar / absorver / coexistir com fronteira escrita) e o oráculo
   mecânico que prova a escolha. Sem isso, o repo passa a ter DOIS geradores de
   cerimônia — que é o problema que o PLAN-188 existe para acabar.
2. **K2 (Critic-C, R-SEC4) — as 9 invariantes omitem a verificação de
   SIGNATÁRIO.** Medido: `grep -l sentinel-signers .claude/plans/*/OWNER-*.sh`
   = **33** de 48 scripts rastreados, e `.claude/sentinel-signers.txt` existe.
   Uma migração que tome as 9 invariantes como ESPECIFICAÇÃO remove, em 33
   pacotes, o controle que responde «foi a chave do Owner?». Esse é o único
   achado do round que subtrai segurança em vez de deixar de somar.
   **Aceito como invariante 10**, com controle vermelho (`.asc` de chave fora
   da allowlist ⇒ recusa nomeada).
3. **K3 (Critic-C, R-SEC3) — registros de rail entram por NOME, sem digest.**
   `rail_records` (:114) é lista de nomes e a invariante 1 (:120-123) lê a
   string `Rail-Verdict: APPROVE` num arquivo que o próprio builder escreve; a
   invariante 9 (liveness, :139-140) é prosa no MESMO arquivo, logo forjável
   por quem forjaria o veredito. **Aceito:** os registros são pinados por
   sha256 gravado pelo `finalize` (a mesma forma do `EXPECTED-BASELINE` da
   invariante 4), e o plano escreve o residual: o rail é ADVISORY e o gate mede
   PROVENIÊNCIA, não verdade do veredito.
4. **K4 (Critic-A, R-VP7) — W1 e W2 estouram o modelo de operação v2 sem
   declarar o corte.** Medido: só o PLAN-169 tem **13** `OWNER-*.sh` rastreados
   (PLAN-183: 8, PLAN-179: 7, PLAN-182: 6). A W2 («migração dos 5 packs +
   remoção dos clones», :157) é um pacote canônico com 5 manifestos e dezenas
   de remoções; a W1 entrega 4 scripts + piloto. O teto vigente é ≤ 400 linhas
   OU ≤ 8 paths. **Aceito:** W2 vira subwaves na ordem da OQ-2 (que passa a ser
   a mesma decisão), e a W1 declara o seu corte.
5. **K5 (Critic-A, R-VP8) — a invariante 9 testa uma forma de saída que não
   existe mais.** Verificado em `CLAUDE.md:108`: «o rail codex corrente NÃO
   emite `VERDICT:` (rodada limpa = ausência do bloco `Full review comments:`)».
   A invariante 9 exige «`VERDICT:` próprio + `tokens used` diferente de toda
   rodada anterior». **Aceito:** reescrever contra a forma atual do CLI (e
   contra o `model:` no cabeçalho, que a doutrina desta noite já usa como
   critério de rodada válida), ou declarar a invariante 9 como ADVISORY até
   existir uma âncora estável.
6. **K6 (Critic-B, R-DO5) — ninguém executa os 9 controles.** Verificado: o
   `validate.yml:341-359` roda `shellcheck -S warning` sobre
   `find .claude/scripts .claude/hooks -name '*.sh'` — logo a metade
   «shellcheck limpo» do AC-1 é automática, e a metade cara (o runner de
   controles) não tem workflow, step nem custo medido. **Aceito** como OQ nova:
   quem roda, em que evento, e a que custo de runner-minutos.
7. **K7 (Critic-C, R-SEC9) — a W2 apagaria cadeia de custódia.** Verificado: a
   razão já está escrita no repo — `check_contamination.py` isenta
   `scripts/local/historical/*` e `archive/*` com o comentário
   «chain-of-custody. Never re-executed». Remover clones de cerimônias JÁ
   ASSINADAS é diferente de remover clones não usados. **Aceito:** a W2
   distingue os dois conjuntos; o que já assinou vai para o arquivo com
   custódia, não para o `rm`.
8. **K8 (Critic-A, R-VP9) — desvios de PLAN-SCHEMA.** Verificado:
   `PLAN-SCHEMA.md:441` exige que `## Items` liste unidades «each with file
   assignment, acceptance criteria, and commit message hint» — a tabela de
   :153-158 tem quatro linhas de wave, sem nenhum dos três. E `depends_on: []`
   (:7) com o piloto AC-2 sendo um pacote do PLAN-186, cujo frontmatter diz
   `status: executing`. **Aceito** (correção de forma, custo baixo).
9. **K9 (Critic-C, R-SEC10) — a invariante 6 não pina o destino.** Ela liga o
   `NEW_SHA` ao índice aprovado e pina o push ao sha (:132-134), mas não nomeia
   remoto/refspec nem `core.hooksPath`: um push pinado ao sha CERTO para o
   remoto ERRADO entrega o conteúdo assinado no lugar errado. **Aceito** como
   emenda de uma linha à invariante 6.
10. **K10 (Critic-B, R-DO9) — exclusão morta de shellcheck ao lado do nome
    proposto.** Verificado: `validate.yml:354` exclui
    `.claude/scripts/owner-ceremony/archive/*` e
    `ls .claude/scripts/owner-ceremony/` = «No such file or directory».
    A exclusão é inerte hoje, mas documenta que um nome de diretório vizinho já
    tirou scripts do shellcheck uma vez. **Aceito** como nota de risco na
    escolha de endereço (C1), não como item próprio.

## Single-agent insights rejected / deferred

1. **REFUTADO em parte — «o guard de path absoluto duplica
   `check_contamination.py`» (Critic-C, R-SEC7).** Verificado o OPOSTO para a
   árvore que importa: `check_contamination.py` isenta `.claude/plans/*` por
   atacado (o comentário do próprio arquivo avisa que o `*` do `fnmatch` cruza
   `/`) e `OWNER-*.sh` por NOME — e é exatamente aí que vivem os MATERIAIS que
   o Owner assina. Logo a invariante 3 não é uma segunda superfície decidindo o
   mesmo fato: ela cobre o buraco que a primeira declara não olhar. (E
   `.claude/scripts/ceremony/*` NÃO está na allowlist, então o toolkit em si já
   é coberto.) **Mantido do achado:** o literal de máquina na isenção (virou
   C7) e a poda das isenções por nome, que fica como pergunta para o Owner, não
   como must-fix desta wave.
2. **DEFERIDO — OQ-4, as cinco chaves de orçamento omitidas** (`budget_tokens`,
   `budget_sessions`, `context_risk`, `external_wait`, `eta_calendar`).
   Verificado que `PLAN-SCHEMA.md` §frontmatter as define e as descreve. O
   plano optou por não inventar números, o que é a postura certa; a omissão é
   ratificação do Owner e não bloqueia o round 2 nem a W0.
3. **DEFERIDO — o número `ADR-2xx` do AC-5 e a wave da emenda ao ADR-010.** É
   decisão de sequenciamento do Owner (OQ-1, cuja primeira metade o CEO já
   resolveu); não muda nenhum mecanismo.
4. **NÃO ALTERADO — a tabela de classes de §Context (:32-45) e a nota da cifra
   «25 rodadas com 23 registros» (:47-56).** Nenhum dos três críticos a
   contestou; a nota já registra que os dois registros ausentes foram escritos
   depois e que a cifra mede o INSTANTE. Um round futuro que a queira revisar
   tem de pedir foco nela.

## Plan adjustments

| § do plano | mudança |
|---|---|
| frontmatter | `depends_on` cita PLAN-186 (piloto W6a é pacote de plano `executing`); OQ-4 registrada como ratificação pendente do Owner |
| §Approach:104-106 | endereço decidido com os DOIS sítios de descoberta (`DISCOVERY_ROOTS` + `paths:` do `ceremony-lint.yml`) no mesmo patch da W0, com controle positivo |
| §Approach:108-117 | formato do manifesto decidido antes da W0 (TSV no molde `delivery-routes.tsv` ou JSON por `python3 -c`; `tomllib` não existe no piso 3.9) + conjunto de recusas nomeadas |
| §Approach:116 + inv. 5 | `scope_generated_from`: contrato `--describe` entregue pela W0, ou a chave sai; nenhum dos 9 derivadores rastreados o implementa hoje |
| §Approach inv. 1 | registros de rail pinados por sha256 gravado pelo `finalize`, não por nome |
| §Approach inv. 3 | isenção de self-test por marcador injetado pelo harness — nenhum literal de máquina na regra |
| §Approach inv. 6 | +remoto/refspec e `core.hooksPath` no pin do push |
| §Approach inv. 9 | reescrita contra a forma atual da saída do codex, ou declarada ADVISORY |
| §Approach +inv. 10 | verificação de SIGNATÁRIO (`sentinel-signers.txt`) — controle que 33 dos 48 clones já fazem |
| §Approach (novo) | reconciliação com `generate-ceremony.sh` (PLAN-073 §2): aposentar / absorver / coexistir, com oráculo |
| §Riscos:144-145 | contradição com :155 resolvida; a razão «oráculo 0 até serem referenciados» sai (é falsa); bootstrap da 1.ª assinatura escrito |
| §Items:155 | W0 = subconjunto de invariantes falsificável por `lib.sh` sozinho + os dois sítios de descoberta + schema/leitor |
| §Items:156-157 | W1 e W2 declaram o corte do modelo v2 (≤ 400 linhas OU ≤ 8 paths); W2 vira subwaves na ordem da OQ-2; clones de cerimônias assinadas vão para custódia, não para `rm` |
| §Items | cada item ganha file assignment + AC + commit hint (PLAN-SCHEMA:441) |
| AC-1 | escopo reduzido ao que a W0 pode falsificar; harness e controles de `land.sh` migram para o AC da W1 |
| AC-3 | mapa pacote→path + controle positivo (hoje verde no HEAD e insensível ao fracasso) |
| AC-4 | OQ-5 decidida antes; instrumento pinado por sha256; `SINCE`/corpus como parâmetros; denominador declarado; critério de morte |
| ACs (novo) | membresia no manifesto ADR-192 para os scripts de gate do toolkit |
| Open questions | OQ-3 promovida a pré-condição da W0; +OQ-6 (registro nos gates), +OQ-7 (contrato `--describe`), +OQ-8 (destino dos clones), +OQ-9 (quem executa o runner de controles, a que custo) |
| Progress log | entrada «round 1 sintetizado» |

## Round verdict

**RUN-ANOTHER-ROUND**

Regra aplicada: risco levantado por 2+ críticos ⇒ o plano MUDA (sete findings,
C1-C7, todos aplicados); risco de um só crítico ⇒ decisão escrita do
sintetizador (10 mantidos com verificação em disco, 4 rejeitados ou deferidos
com razão).

Por que não `PROCEED`: os três críticos retornaram `ADJUST` com 13 bloqueantes
somados, e o rótulo **design-coherent NÃO é concedido** — ele exige zero
bloqueantes nas três críticas. O plano sai do round com estrutura diferente: o
endereço do toolkit virou decisão de gate, a W0 mudou de conteúdo (subconjunto
de invariantes + dois sítios de descoberta + leitor do manifesto), duas das
cinco ACs são inobserváveis como escritas, e apareceu uma décima invariante que
SUBTRAI segurança se esquecida. A doutrina desta casa é que rodada limpa prova
a SUPERFÍCIE revisada, não o entregável: o round 2 tem de revisar o plano
REVISADO.

Por que não `ESCALATE-TO-OWNER`: nenhuma das quatro OQs novas impede o round 2
de rodar. Três decisões do Owner podem ser colhidas em PARALELO ao round 2
porque mudam o TAMANHO das waves, não a tese — (i) o endereço + membresia
ADR-192 e canonicidade, que decide se a W0 é livre ou canônica; (ii) OQ-5
(corrigir o classificador e re-medir × congelar e comparar igual-com-igual),
que decide se o AC-4 é criterion ou observação; (iii) OQ-2/OQ-8, ordem de
migração e destino dos clones, que é o corte das subwaves da W2.
