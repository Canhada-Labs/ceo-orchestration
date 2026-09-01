---
id: PLAN-183
title: Adopter fitness — o instrumento de adopter existe, mas seu escopo exclui .github/ e ele nunca executa o CI entregue
status: executing
executing_at: 2026-08-25
reviewed_at: 2026-08-20
reviewed_by: "Owner — autorizacao explicita em chat (S315, 2026-08-20): 'se ja esta pronto deixa como revisado e apto pra fazer'. Debate L3 round 1 fechado com veredito PROCEED (10 consensos, 28 ajustes) e ajustes incorporados ao corpo; validate_governance_fast = 0 findings; pair-rail codex 6 rodadas fechadas, 32 achados, todos curados."
created: 2026-08-20
owner: CEO
depends_on: [PLAN-167, PLAN-168]
budget_tokens: 210-400k (W0 60-110k; W1 90-150k — re-orcado pela W0-US4 §7, cujo piso de re-baseline de ownership e 40-70k em 2-4 iteracoes; W2 40-90k; W3 20-40k; W4 piso nomeado ao fechar a W0)
budget_sessions: 3-5
context_risk: medium
external_wait: "nenhum — DECISAO do CEO registrada (§6, ajuste r1-25): o AC-2 aceita prova em repositorio DESCARTAVEL NOSSO, nao um PR em repo de terceiro. Manter dependencia de PR externo tornaria o plano refem de CI que nao e deste projeto; a evidencia que o AC precisa (template ativado sai verde) e integralmente reproduzivel localmente."
tags: [adopter, install, ci, templates, portability, contamination, field-report]
---

## 1. De onde isto veio, e qual é REALMENTE a causa-raiz

Um adopter real instalou o `ceo-orchestration v1.3.0` em 2026-08-16
(perfil `core,frontend,fintech`) e, na primeira sessão, escreveu o
próprio `PLAN-001` listando o que não funcionou. É um **relatório de
campo** — a classe de evidência que o dogfood não produz.

**A primeira redação deste plano afirmava: "o framework foi dogfoodado,
nunca exercitado como adopter". Isso é FALSO, e o debate round 1 o
provou por três lados** (consenso C2). O instrumento existe, é forte e
roda **por-PR**: `scripts/tests/smoke-install.sh` +
`.github/workflows/smoke-install.yml`, com install real em scratch dir e
paridade install/upgrade — e `smoke-install.yml:276` tem literalmente um
step **"Protocol pointer render control (generator parity)"**.

**A causa-raiz verdadeira é mais estreita e muito mais útil:**

1. **O escopo do instrumento exclui `.github/`.** Censo executado:
   `grep -rln` pelos dois templates de workflow sobre `scripts/tests/`,
   `.github/workflows/` e `.claude/scripts/tests/` devolve **ZERO**. Os
   dois templates são os únicos artefatos entregues ao adopter sem teste
   e sem referência de CI em lugar nenhum.
2. **O instrumento para em "o install escreveu os bytes certos?" e
   NUNCA ativa nem executa o CI entregue.** A pergunta que ninguém faz é
   exatamente a que o adopter fez em campo.

Toda vez que este plano disser "premissa de auto-instalação que vazou",
é uma dessas duas — não a ausência de instrumento.

## 2. Achados, com o que foi verificado no disco

| # | Achado | Verificado? | Onde |
|---|---|---|---|
| A1 | Ponteiro `PROTOCOL.md` do adopter é ABSOLUTO | **SIM, defeito vivo** | `scripts/_framework_manifest_set.sh:673-711` |
| A2 | Steps do template de CI que só rodam no repo do framework | **SIM, mas o censo precisa ser RE-DERIVADO** (ver W2) | `templates/.github/workflows/validate.yml.template` |
| A3 | `benchmarks.yml.template` chama script que o install não entrega | **SIM, defeito vivo** | template `:129`; `install.sh` não copia `.github/scripts/` |
| A4 | Skills de VETO em `name-only` | **SIM — e é defeito VIVO NESTE REPO, não só no adopter** | `.claude/settings.json:872-873` |
| A5 | 71 timeouts de hook em 10 dias | **REPRODUZIDO (S317, W0-US1)** — 71 exatos e todos breach do teto de 5 s; mas **70 são deste repositório e ZERO do adopter** — o defeito é nosso, não de campo (§4, W4) | transcripts de todos os projetos do `$HOME`, janela 2026-08-06..08-16 |
| A6 | CODEOWNERS com handle da org | **NÃO é defeito** — `{{OWNER_HANDLE}}` substituído corretamente | `templates/.github/CODEOWNERS.template` |
| **A7** | **O guard de contaminação é ele próprio vetor de contaminação** | **SIM, defeito vivo — achado NOVO do debate** | `.claude/scripts/check_contamination.py:70-73,100` |

### A1 — absoluto por construção, e a cura anterior estava na camada errada

`_render_protocol_pointer()` emite caminho relativo quando o framework
está DENTRO do alvo, e substitui o token pelo `$SOURCE_DIR` absoluto
quando está FORA — **o caso normal de adopter**.

**Três mecanismos garantem que o adopter fica com o absoluto para
sempre** (consenso C1, os três críticos por portas diferentes):

- `install.sh:663-668` persiste `PH_PROTOCOL_SOURCE="$SOURCE_DIR"`
  (absoluto) no install-state, e a precedência **#1** do upgrade relê
  exatamente essa chave, então o próximo upgrade re-renderiza absoluto.
  Como ambos usam o MESMO gerador, **INV-4 passa VERDE** — o mesmo
  formato de falso-verde que este plano diagnostica.
- Mudar o corpo renderizado muda `_REFRESH_PROTOCOL_CANON_HASH`
  (`upgrade.sh:1667,1686-1690`), o ponteiro antigo deixa de casar, cai
  em `PRESERVE_OWNED`, e `upgrade.sh:1730` imprime *"PRESERVED … pointer
  NOT refreshed"*.
- A precedência **#2** do upgrade é "um ponteiro **saudável** on-disk —
  *never silently rename a sound pointer*". **Um ponteiro absoluto É
  saudável por essa definição.**

Corolário que reescreve a W1: **a cura mora DENTRO de
`_render_protocol_pointer`** (a função já recebe `$2=TARGET`), nunca no
call-site; e o teste é `install → upgrade → assert relativo`, nunca
`install → assert relativo`.

### A4 — defeito VIVO neste repositório, com mecanismo identificado

`.claude/settings.json:872-873`: **`financial-correctness-and-math` e
`financial-display` estão em `name-only` AQUI**. As quatro skills de
VETO **core** (`code-review-checklist`, `security-and-auth`,
`identity-and-trust-architecture`, `incident-management`) estão
completas — protegidas por `if skill["tier"] != "domain": continue  #
NEVER demote core/frontend` em
`.claude/scripts/skill-budget-generator.py:352-362`.

**O eixo de proteção do gerador é `tier`, e ele não conhece o conceito
de VETO:** `grep -c "veto|VETO|risk_class"` no gerador inteiro = **0**.
Skill de VETO em tier `domain` é demovida por construção. Os dois vetos
que protegem conta de dinheiro estão sem descrição no catálogo — aqui e
no campo.

Registrar também: o mapa de overrides é **pré-cozido e embarcado** (104
entradas no `settings.base.json`, calculadas contra o inventário de 166
do framework). As órfãs do adopter não vêm de acúmulo local — vêm do
template. "Podar depois de copiar" contradiz a doutrina 167/168 (um
gerador, uma verdade).

### A7 — o guard de contaminação carrega a identidade do mantenedor até o adopter

Achado novo, dos três críticos, verificado linha a linha:

- `check_contamination.py:70-73` — o padrão inclui o nome real do
  mantenedor, inclusive o primeiro nome nu.
- O arquivo é entregue a **todo adopter** (`install_scripts_selective`,
  `install.sh:1135,1283`). **Confirmado no campo:** o adopter tem
  `.claude/scripts/check_contamination.py` com o padrão, e é o **único**
  arquivo do `.claude/` dele que carrega o nome.
- `_ALLOWLIST_EXACT:100` isenta o próprio arquivo — **o guard isenta a
  si mesmo**.
- `_ALLOWLIST_EXACT:97` isenta `.github/workflows/validate.yml`, mas o
  arquivo do adopter chama-se `validate.yml.template` — **a isenção nem
  viaja**.

Leitura honesta: o padrão é **intencional** e defende as superfícies
publicadas DESTE framework (o comentário `:61` diz isso). O defeito é de
**escopo que viaja**: no adopter, ele planta o nome do mantenedor num
repo de terceiro e defende a identidade errada. Cura = padrão
**configurável na instalação**, não editar lista de caminhos.

## 3. O que este plano NÃO faz

Não re-litiga o PLAN-175 (poda de skills) nem o PLAN-182 (audit dir).
A1/A2/A3/A7 são independentes dos dois.

## 4. A5 — hipótese aritmética nomeada, não busca aberta

O relatório afirma 71 timeouts de hook em 10 dias (`PreToolUse:Bash`
35x, `PreToolUse:Write` 25x, `Stop` 7x; pior caso 175 s e 231 s),
medidos pelo `/doctor`. Varri 42 transcripts de cada repositório em 30
dias e achei **zero** timeouts de hook — os hits eram `Monitor timed
out`, `Command timed out` do Bash, e o texto dos próprios comandos de
busca.

**O debate transformou isso numa hipótese testável de graça** (consenso
C7). Censo de `templates/settings/settings.base.json`: **46 registros de
timeout, 38 deles com valor 5**; os únicos tetos longos são **210**
(`check_pair_rail.py`, matcher `Edit|Write|MultiEdit`) e **130**
(`codex_review_user_code.py`); `CEO_PAIR_RAIL_TIMEOUT_S` default **180**
(`check_pair_rail.py:1722`). Logo:

- 175 s / 231 s no caminho **`PreToolUse:Bash`** é **aritmeticamente
  impossível** como estouro de teto por-hook (teto de 5 s), então o
  `/doctor` **não** está contando breach de teto por-hook.
- 175 s aproxima 180 menos startup, e 231 s excede 210: é a **assinatura
  do caminho `Write`** (pair-rail), com o harness matando o processo.

**→ CURADO (S317, 2026-08-20 — W0-US1 executada): as DUAS conclusões
acima estão ERRADAS. Ficam registradas por honestidade.**

- **(a) É FALSO que "o `/doctor` não está contando breach de teto
  por-hook" — ele ESTÁ.** Os 71 eventos são `hook_cancelled` com
  `timeoutMs=5000` e `timedOut=true`: breaches do teto de 5 s, sem
  exceção. A premissa que quebrou é outra — **`durationMs` não
  acompanha `timeoutMs`**: o `Stop` cancelado de 2026-08-06T13:43:19Z
  registra `durationMs=229987` contra `timeoutMs=5000` (**46× o teto**).
  Logo tempo grande NÃO implica teto grande, e a inferência
  "231 s ⇒ teto de 210 ⇒ pair-rail" não tem lastro.
- **(b) Os 231 s não são hook do framework, nem timeout.** São o
  `on-stop.sh` do plugin **Warp** no evento `Stop`, emitido como
  `hook_success` com exit 0 e `durationMs=230673` — nada foi estourado
  e nada foi morto.
- **(c) Os 175 s SÃO o pair-rail — mas não no caminho `Write` e não
  mortos pelo harness:** `PreToolUse:Edit`, `hook_success`,
  `durationMs=175470`, **abaixo** do teto de 210 s. O hook **completou**.

**Correção do r9 #3: a conta declarada não fecha** — 35 + 25 + 7 =
**67**, não 71. Os **4 eventos não contabilizados** podem pertencer a
outro matcher e mudar qual caminho explica o relatório; a W0-US1
identifica a categoria dos 4 ANTES de usar o breakdown como evidência.

**→ CURADO (S317): a conta FECHA EXATO em 71 e os 4 estão nomeados.**
`PreToolUse:Bash` 35 + `PreToolUse:Write` 25 + `Stop` 7 +
**`PreToolUse:Read` 2** ("Scanning read content for injection
patterns", 5621 ms e 5624 ms, ambos 2026-08-06) +
**`UserPromptSubmit` 2** ("Prompt smell-test", 5392 ms em 2026-08-06 e
6506 ms em 2026-08-14) = **71**. Os 71 são `hook_cancelled` com
`timeoutMs=5000` e `timedOut=true`. A janela **2026-08-06..08-16 por
dia-calendário** é a ÚNICA que devolve 71 — o "10 dias" do relatório é
literal. Nenhum dos 4 pertence a matcher de teto longo: **todo** o
breakdown é teto de 5 s.

**A aritmética vem primeiro. A arqueologia da fonte do `/doctor` só abre
se ela não explicar.**

**→ RESOLVIDO (S317): a arqueologia NÃO abre — a fonte saiu de graça.**
O `/doctor` executa o prompt embutido no binário 2.1.237, seção *"Check
5 - slow hooks"*, que agrega `durationMs` por `hookName` e trata
`hook_cancelled` com `timedOut:true` como evidência. É comando dirigido
por **MODELO**, não contador determinístico — o que explica o breakdown
parcial (67 dos 71) sem escavação nenhuma.

**Sobre a instrumentação — a claim anterior estava errada duas vezes.**
A primeira redação disse "o audit-log não registra timeout"; a segunda
disse que o canônico registra e o resto é cego. O disco diz o seguinte:
`audit_emit.py:1128` já carrega `check_name` e `timeout_ms`, e o
deadline interno do matcher canônico é registrado como `veto_triggered`
com `reason_code=canonical_edit_hook_fault`
(`check_canonical_edit.py:2169-2171`, exceção ADR-186). **O gap real é
censura à direita:** um *harness kill* nunca alcança a linha de emissão,
então o evento não existe — não porque falte campo, mas porque o
processo morreu antes. Instrumentar o que falta; nunca reinventar o que
existe.

## 5. Coupling (PLAN-SCHEMA.md:202)

- **W1 ligado a PLAN-167 / PLAN-168** — INV-4 e a bateria de ownership.
  A cura do ponteiro toca o gerador compartilhado; o ciclo de
  re-baseline (~25 min por iteração, 62 installs reais) é orçado dentro
  da W1 com piso NOMEADO pela W0-US4: **40-70k tokens em 2-4
  iterações**, 1 sessão se o e2e rodar LOCAL e 2-4 se o veredito vier do
  nightly (`.github/workflows/ownership-nightly.yml:38`,
  `timeout-minutes: 110`). A W1 toca SETE artefatos, não cinco — tabela
  e aritmética em §7.
- **W3 ligado a PLAN-175** — colisão na seleção de skills em tempo de
  install. O 175 muda o conjunto instalado; este plano muda a regra de
  demoção. Quem executar primeiro avisa o outro.

## 6. Decisões do CEO registradas neste plano

- **`external_wait` e AC-2 (ajuste r1-25):** AC-2 aceita prova em
  repositório **descartável nosso**; `external_wait` permanece "nenhum".
  Razão: depender de PR em repo de terceiro tornaria o plano refém de CI
  que não controlamos, e a evidência exigida é integralmente
  reproduzível localmente.
- **OQ-1 respondida (ajuste r1-18):** `unittest discover` **não** é
  preservável atrás de guarda — `conftest` é pytest-only, logo produz
  falso-vermelho (lição já registrada neste repo). Rotas honestas:
  remover, ou reescrever para a invocação real do CI.
- **Rota do main vermelho — DECISÃO DO OWNER (S323, 2026-08-23),
  registrada verbatim:** *"Rota C — planejar sem tocar"*. Opções
  apresentadas: (A) reverter os 3 arquivos da S322 e ficar verde em
  minutos; (B) curar `upgrade.sh` já, cerimônia canônica L3+; (C) deixar
  o main vermelho e usar a sessão para desenhar a cura. O Owner escolheu
  **C**. Consequência aceita: `Smoke Install` segue vermelho em `main` e
  a branch protection pode barrar PRs enquanto durar. Esta decisão NÃO
  autoriza land nenhum — o entregável dela é a §8 deste arquivo mais a
  W5 em `.claude/plans/PLAN-183/w5-draft-s323.md` (draft; ver §8.10).

- **OQ-3 respondida (ajuste r1-21):** a demoção é escrita por
  `skill-budget-generator.py:352-362`. O invariante mora **no gerador**,
  com asserção nos testes dele — nunca corrigindo entradas no
  `settings.json` a posteriori.

## RESIDUAL DO r9 — CURADO em S316 (registro histórico)

A 9a rodada do pair-rail devolveu **REJECT** com achados contra ESTE
plano. **Curados em S316 (2026-08-20), ANTES de qualquer execução**, com
as emendas apontadas item a item. A rodada r10 confirmou 183-1 e 183-3
CLOSED e devolveu REJECT parcial no 183-2: a enumeração "4 core + 2
fintech" era conjunto fechado escrito de memória e omitia
`accessibility-and-wcag` (`frontend-team.md:164`) — curado trocando
enumeração por DERIVAÇÃO do organograma. r11 confirmou este item CLOSED;
**r12 = GO (2026-08-20)** — cadeia r9→r12 fechada. Registro histórico.

1. **[P1] O teste de relocacao que a W1 exige e IMPOSSIVEL como escrito.**
   Quando `SOURCE_DIR` esta fora de `TARGET` — o caso normal de adopter —
   relativizar so consegue codificar a relacao ATUAL entre os dois.
   Mover ou copiar o `TARGET` sozinho quebra essa relacao, entao o e2e
   exigido **nao pode passar**. (Ironia registrada: este check foi
   introduzido no r8 para curar um teste fraco, e criou um impossivel.)
   **Cura:** ou vendorizar uma copia do protocolo DENTRO do target, ou
   trocar o requisito para mover source e target JUNTOS.
   **→ CURADO (S316):** W1 redefiniu portabilidade — e2e move
   source+target JUNTOS; mover o target sozinho vira erro NOMEADO com
   reparo apontado; vendorização considerada e rejeitada (doutrina
   167/168).
2. **[P2] Nao existe marcador de VETO machine-readable.** Nenhuma das
   duas skills financeiras tem campo `veto` no frontmatter — so
   `risk_class` — e o status de VETO vive em prosa de roteamento e no
   organograma. O teste de gerador proposto **nao consegue decidir** se
   uma skill arbitraria e VETO sem hardcodar nomes, o que deixaria a
   PROXIMA skill de VETO ser demovida. **Cura:** definir campo ou
   mapeamento autoritativo e machine-readable, e inclui-lo no inventario
   que o gerador consome.
   **→ CURADO (S316):** W3 ganhou unidade P0 pré-requisito: mapeamento
   VETO autoritativo no inventário do gerador (não no frontmatter, que é
   gateado por SP-NNN + soak), com entradas DERIVADAS do organograma —
   nunca enumeradas — e lint bidirecional. O r10 pegou a enumeração
   errada desta própria cura (faltava accessibility-and-wcag), provando
   a regra.
3. **[P2] A aritmetica do A5 nao fecha:** 35 + 25 + 7 = **67**, nao 71.
   Como o diagnostico da W0 depende de aritmetica por evento, os 4 casos
   nao contabilizados podem mudar qual matcher explica o relatorio.
   **Cura:** identificar a categoria dos 4 antes de usar o breakdown
   como evidencia.
   **→ CURADO (S316):** §4 registra a conta 67≠71 e o check da W0-US1
   agora exige categoria nomeada para os 4 casos antes do veredito.

## 7. W0-US4 — inventário de ownership e orçamento do re-baseline (S322)

> Levantamento READ-ONLY (a wave declara US1/US2/US4 read-only, §W0).
> Sem checkbox aqui por construção: `PLAN-SCHEMA.md` §13 exige `Check:`
> por checkbox, e esta seção é evidência, não unidade de execução.

**Veredito: a W1 toca 4 dos 5 artefatos nomeados, e a lista de CINCO
(`PLAN-183/debate/round-1/devops-dx.md:50`, consolidada em
`consensus.md:143` como K9) está INCOMPLETA — o conjunto real é SETE.**

### 7.1 Os artefatos

| # | Artefato | W1 toca? | Mecanismo, com evidência |
|---|---|---|---|
| 1 | `scripts/tests/test-protocol-pointer-render.sh` | **SIM — obrigatório** | R2 (`:65-72`) assere `degraded + sed == healthy` (invariante de UM template). Hoje isso é verdade porque o ramo fora-do-target de `_render_protocol_pointer` **é** literalmente `degraded \| sed` (`scripts/_framework_manifest_set.sh:702-707`) — a relativização fora-do-target quebra a identidade por construção. R8 (`:114-124`) é a ÚNICA asserção de forma relativa e está presa ao caso dentro-do-target. O requisito "corpo contém `--protocol-source`" não tem cenário. **Roda POR-PR** (`.github/workflows/smoke-install.yml:279`) — vermelho aqui pinta o main, não o nightly. |
| 2 | `scripts/tests/test-protocol-pointer-inv4.sh` | **SIM — obrigatório, e contradiz o Check da W1** | `assert_sound()` (`:50-61`) exige `grep -F -q "$REPO_ROOT/PROTOCOL.md"` — o caminho ABSOLUTO PRESENTE — e é chamada em `:70`, `:75` e `:103`. Depois da relativização o arquivo NÃO PODE ficar verde sem editar `assert_sound`: o Check da W1 ("`test-protocol-pointer-inv4.sh` verde") é insatisfazível como escrito. Nightly-only (`.github/workflows/ownership-nightly.yml:110`) — o vermelho chega um dia atrasado. |
| 3 | `scripts/tests/ownership_table.tsv` | **SIM — tríade nova de linhas** | Enum de `live_content` hoje: `pristine \| legacy_pristine \| degraded \| edited` (`docs/ownership-decision-table.md:126-134`). A remediação retroativa ("absoluto legado") é classe NOVA e precisa da tríade paralela a `degraded`, que hoje ocupa OWN-0092/0093/0094. **Não-impacto medido:** OWN-0011/0014/0071/0072 NÃO viram, porque o harness define `pristine` de `protocol` como "a própria saída do install base" e deixa o arquivo intocado (`scripts/tests/test-ownership-table.sh:374-380`). **A mudança de BYTES não invalida o TSV:** `grep -E "[0-9a-f]{64}"` nos cinco devolve ZERO — valores simbólicos, nenhum digest fixado. |
| 4 | `scripts/tests/ownership-baseline-map.txt` | **SIM — RE-GRAVADO, nunca editado à mão** | Saída do harness em modo `--stable-header` (`test-ownership-table.sh:55,717-724`). Estado medido: 65 linhas `OWN-`, trailer `GREEN=62  RED=3  AMBIG=0  HARNESS-ERR=0`. **Não é gate:** a única referência em `scripts/` + `.github/` é um COMENTÁRIO (`test-ownership-table.sh:720`); nenhum script o lê — ele deriva em SILÊNCIO se não for re-gravado. Custo = a corrida de ~25 min, não tokens. |
| 5 | `scripts/tests/ownership-expected-reds.txt` | **CONDICIONAL — re-verificar toda iteração** | Hoje exatamente `OWN-0016`, `OWN-0024`, `OWN-0027` (`:13-15`); `ownership-nightly-gate.sh` falha em QUALQUER diferença, encolhimento incluído. Linha nova verde ⇒ nenhuma edição. Mas linha nova vermelha, ou o reconhecedor novo fechando por acidente a `OWN-0016`, obriga edição no MESMO commit — e por `CLAUDE.md` §4 uma corrida toda-verde é sinal de PARAR. |
| **6** | `docs/ownership-decision-table.md` | **SIM — AUSENTE da lista de cinco** | O TSV declara "values live ONLY here" e manda o raciocínio para o doc (`ownership_table.tsv:1-2`). A classe nova exige entrada no enum §2.4 e uma regra de legalidade irmã da **R-04b** (`:297`). Sem a regra, a linha nova é ILEGAL pela própria §4. 42.367 bytes. |
| **7** | `scripts/tests/test-ownership-table.sh` | **SIM — AUSENTE da lista de cinco** | O harness instancia cada `live_content` por ramo de `case` (`:382-391` para `degraded`). Sem ramo para a classe nova, cada linha nova vira `HARNESS-ERR`, não veredito. 37.690 bytes. |

### 7.2 O orçamento

Superfície de LEITURA, medida por `wc -c`, convertida a ~4 bytes/token:

| Artefato | bytes | ≈tokens |
|---|---|---|
| `ownership_table.tsv` | 11.671 | 2,9k |
| `ownership-baseline-map.txt` | 8.184 | 2,0k |
| `ownership-expected-reds.txt` | 795 | 0,2k |
| `test-protocol-pointer-inv4.sh` | 6.091 | 1,5k |
| `test-protocol-pointer-render.sh` | 6.502 | 1,6k |
| **subtotal dos CINCO** | **33.243** | **8,3k** |
| `docs/ownership-decision-table.md` | 42.367 | 10,6k |
| `test-ownership-table.sh` | 37.690 | 9,4k |
| **superfície completa (SETE)** | **113.300** | **28,3k** |

- **1 iteração ≈ 12-18k tokens** — leituras direcionadas
  (`_framework_manifest_set.sh:640-775`, `upgrade.sh:1593-1760`) mais a
  revisão do diff de 65 linhas do mapa — **+ ~25 min de espera
  bloqueante** (62 installs reais; `CELL_TIMEOUT` default 60s, o CI usa
  180 em `ownership-nightly.yml:131`, e o job cabe em
  `timeout-minutes: 110` em `:38`).
- **Iterações esperadas: 2-4.** Prior empírico DESTE código: 11 rodadas
  cross-model, 35 defeitos, metade das últimas sendo regressões da
  correção anterior (`docs/ownership-decision-table.md:46-52`); e o
  PLAN-167 precisou de mapa-baseline **v3**
  (`PLAN-167-ownership-decision-table.md:490`).
- **Piso do re-baseline: 40-70k tokens** — o re-baseline SOZINHO
  consumia 80%–64% do envelope de 50-110k que a W1 declarava. Daí a
  re-declaração no frontmatter (agora 90-150k para a W1).
- **Sessões: 1 pela rota LOCAL, 2-4 pela rota nightly.** O e2e é
  nightly-only por desenho (`smoke-install.yml:29-31,235`), então cada
  iteração que espera o nightly custa uma SESSÃO inteira.
  `budget_sessions: 3-5` só se sustenta se o e2e rodar LOCAL — é
  pré-condição, não preferência.

### 7.3 Onde mora a cerimônia GPG

Dos SETE artefatos, **ZERO** é canônico: `scripts/tests/*` e `docs/*`
não aparecem em `_CANONICAL_GUARDS`
(`.claude/hooks/check_canonical_edit.py:115-215`). O corpo deste plano
também não é — só `.claude/plans/PLAN-*/spec.md` é (`:210`). A cerimônia
da W1 recai inteira sobre o CÓDIGO:
`scripts/_framework_manifest_set.sh` (`:199`), `scripts/upgrade.sh`
(`:191`) e `.github/workflows/*.yml` (`:184`) se algum step mudar.

## 8. O vermelho da S322 são QUATRO defeitos sobrepostos, não um (S323)

> Medido nesta sessão, com os comandos citados. A S322 registrou UM
> defeito (`upgrade.sh` não entrega `.github/`). A medição encontrou
> **mais três**, e eles mudam a ordem de execução: D2 no instrumento de
> teste, D3 no gerador de manifesto, D4 no `doctor.sh`. Os três últimos
> são a MESMA classe — ninguém sabe responder "qual é a fonte deste
> path?" da mesma forma. A §8.5 nomeia essa forma; ela é o achado que
> mais muda o desenho.

### 8.1 D1 — PRODUTO: o upgrade nunca entregou `.github/` nem `docs/`

Medição **re-executada na S323** (o pair-rail pegou um número errado que
esta seção herdou da S322 sem re-rodar — a lição
`feedback-grep-counts-are-wrong-derive-behaviorally` aplicada a mim mesmo):

```
grep -c 'github' scripts/upgrade.sh   ->  0     [confere]
grep -c 'docs'   scripts/upgrade.sh   ->  3     [a S322 publicou 0 — ERRADO]
```

As três ocorrências de `docs` são **comentários**, nenhuma é sítio
executável: `:1623` (sobre heredocs, nem trata de `docs/`), `:3104` e
`:3206`. **Zero sítios executáveis** — a conclusão se mantém, a evidência
citada é que estava mal formulada.

E `:3104` é evidência MELHOR do que a que esta seção citava. O próprio
`upgrade.sh` documenta a classe, em prosa:

> *"the plans/ SCHEMA docs are FRAMEWORK contract files that install.sh
> seeds but upgrade never refreshed — the first framework edit (S305,
> DEBATE-SCHEMA) left every upgraded adopter on the old generation
> (F3 STALE)."*

Mesma frase, mesma assinatura F3, outra árvore. O defeito já foi
diagnosticado e curado uma vez neste arquivo — para `PLAN-SCHEMA.md` e
`DEBATE-SCHEMA.md`. Ver §8.6.

Mecanismo exato, agora localizado: o `install.sh` entrega as duas
árvores por funções dedicadas — `install_docs_templates` (`:1478-1482`,
chamada em `:1484`) e `install_github_templates` (`:1488-1523`, chamada
em `:1525`) — **as duas atrás da guarda `if [[ "$CEREMONY" != "user" ]]`**.
O `upgrade.sh` não possui equivalente. Daí a assinatura observada
`maintainer:1 user:0`: em modo `user` nenhuma das duas rotas escreve
esses paths, então a paridade é trivialmente verdadeira; em `maintainer`
a rota A tem a geração HEAD e a rota B fica com a do pin **para sempre**.

O defeito é PRÉ-EXISTENTE e estrutural. A S322 não o criou — tornou-o
FATAL, ao editar três arquivos dessas árvores. Enquanto eles não
mudavam, `ha == hb` e o classificador nem alcançava a decisão.

**O molde da cura já existe neste repo.** `_framework_manifest_set.sh`
resolve exatamente esta classe para `PROTOCOL.md`, `SPEC/v1` e
`.claude/.framework-version` com as entradas
**DELIVERY-RECORD-CONDITIONAL** (`:36-50`, PLAN-166 F3 / ADR-155-AMEND-1):
o path só entra no conjunto quando o caller exporta a flag
`FMS_DELIVERED_*`, e a flag deriva do **registro de entrega** — nunca da
cerimônia sozinha e nunca da presença do arquivo, porque um alvo que já
tinha o path (skip-if-exists) é adopter-owned e o upgrade não pode
TOMÁ-lo. As flags são exportadas em `install.sh:2537-2542` e
`upgrade.sh:3529-3534`.

**A pré-condição do molde NÃO está satisfeita — e a primeira redação
desta seção afirmou que estava. Correção do pair-rail r4, verificada.**
Existem dois `_state_record_op` (`install.sh:1479` e `:1491`), mas ambos
executam ANTES de qualquer teste de existência por arquivo: uma árvore
parcial ou inteiramente pré-existente produz **a mesma entrada de
journal** que uma cópia bem-sucedida. São **breadcrumbs de TENTATIVA**,
não registro de entrega, e o `ADR-155-AMEND-1:87-125` é explícito ao
proibir derivar posse assim: *"Delivered means REGISTERED ACTUAL
DELIVERY, not ceremony … and not file presence"*. O consumidor não é a
única peça que falta: **a fonte também precisa ser construída**, no ramo
que de fato copiou — `INSTALL_ONE_WROTE` é o precedente.

**E `install_docs_template` é skip-if-exists com `cp` puro, sem
substituição** (`install.sh:1446-1474`): a semântica é idêntica à do
`install_one` que motivou o AMEND-1. Um adopter que já tinha
`docs/BRANCH-PROTECTION.md` nunca recebeu a versão do framework — logo
esse arquivo NÃO pode ser sobrescrito por upgrade nenhum. Qualquer cura
que use `cp -R` cego reabre a classe S238 ("verified worst case").

### 8.2 D2 — INSTRUMENTO (teste): `_src_digest` resolve a fonte ERRADA

`_parity_classify.py:221-227` documenta a própria ordem: *"identity map
first, then the templates/ map"*. Para um path entregue a partir de
`templates/` que TAMBÉM existe como homônimo na raiz do repo, a identity
map casa primeiro e a comparação passa a ser feita contra um arquivo que
o adopter nunca recebeu.

Medição direta (chamando `_src_digest` do próprio módulo, `subs=[]`):

| rel | raiz sha[:16] | templates/ sha[:16] | `_src_digest` resolveu de |
|---|---|---|---|
| `docs/BRANCH-PROTECTION.md` | `01eab4f2197291e8` | `966e057147fbc3dc` | **IDENTITY (raiz)** |
| `docs/rotation-log.md` | `0249879f85888d12` | `0ab61d1615aad651` | **IDENTITY (raiz)** |
| `.github/workflows/validate.yml.template` | ausente | `7d0ee14b9871d0e7` | `templates/` (correto) |
| `.github/workflows/benchmarks.yml.template` | ausente | `e59a27bd2757843f` | `templates/` (correto) |
| `.github/CODEOWNERS.template` | ausente | `1955b01a16069f6d` | `templates/` (correto) |
| `.github/CODEOWNERS` (modo `--github-owner`) | **`ba6667d9e53bee9b`** | `1955b01a16069f6d` (via `.template`) | **IDENTITY (raiz)** ⇒ DEFEITO |

Consequência exata: para `docs/BRANCH-PROTECTION.md`, `h_head` e `h_pin`
são digests do arquivo da RAIZ (21.513 bytes, o doc do PRÓPRIO
framework), que nunca casam com `hb` (8.468 bytes, o template do pin).
O ramo `hb == h_pin` nunca é alcançado e o veredito cai em
**UNCLASSIFIED**, quando a verdade é **STALE**. **A classe reportada
está errada** — o instrumento acusa "diverge e não casa nenhuma das duas
gerações" para um caso que casa perfeitamente a geração do pin.

**Escopo de D2 — a S324 REFUTOU o "exatamente 2 paths" da S323, e a
causa é a FORMA do censo, não um path esquecido.** O censo da S323
enumerou pares `templates/X` contra `X` (mesmo relpath): quatro
homônimos, os quatro DIFEREM — `README.md`, `CLAUDE.md`,
`docs/rotation-log.md`, `docs/BRANCH-PROTECTION.md`. Dos quatro,
`templates/README.md` **não é entregue** (nenhum `install_template` o
cita, então nunca entra em `a_files`) e `CLAUDE.md` é absorvido pelo
`ACCEPTED` (`^(CLAUDE|MEMORY)\.md$`, `_parity_classify.py:118-121`).
Sobravam os dois de `docs/` — e a S323 concluiu, em prosa, que *"os 3
paths de `.github/` resolvem CORRETO (não há homônimo na raiz)"*.

**Isso está ERRADO, medido na S324 pelo próprio `_src_digest`:**

```
dest = .github/CODEOWNERS
  _src_digest  -> ba6667d9e53bee9b   = .github/CODEOWNERS VIVO da raiz (10.259 b)
  fonte real   -> templates/.github/CODEOWNERS.template (1.442 b, 1955b01a16069f6d)
```

`.github/CODEOWNERS` **tem** arquivo na raiz — é justamente o que o
`CLAUDE.md` §4 nomeia como *"the only live file carrying a real handle"*.
Ele não apareceu no censo porque **não é par de mesmo relpath**: a fonte
é `templates/.github/CODEOWNERS.template` e o destino é
`.github/CODEOWNERS` (sufixo cai + substituição de `{{OWNER_HANDLE}}`).
Um censo que procura homônimos de mesmo nome é estruturalmente cego a
essa rota.

⇒ **Exposição real de D2 = 3 paths**, não 2: os dois de `docs/` mais
`.github/CODEOWNERS`, este último alcançável só em modo
`--github-owner` (no modo default o destino é
`.github/CODEOWNERS.template`, sem homônimo, e resolve correto). É
exatamente por isso que o e2e nunca o acendeu:
`test-install-upgrade-parity-e2e.sh` não passa a flag.

⇒ **E a unidade de censo da W5-a muda de FORMA:** enumerar
*rotas de entrega* (pares fonte→destino extraídos das funções de cópia
do `install.sh`), nunca homônimos de mesmo nome. Um censo com a forma
antiga sai verde sobre um `.github/CODEOWNERS` quebrado — a classe
*instrumento verde cuja PERGUNTA envelheceu*, aplicada ao próprio
instrumento de censo.

**`docs/rotation-log.md` é um falso-verde vivo.** Ele tem o mesmo
defeito e não apareceu no vermelho de hoje por um único motivo: nem ele
nem seu template mudaram na S322, então `ha == hb` e a classificação não
foi alcançada. É a classe já catalogada neste repo —
*instrumento verde cuja PERGUNTA envelheceu*. A próxima edição em
`templates/docs/rotation-log.md` o acende, com a classe errada.

### 8.3 D3 — PRODUÇÃO: a mesma classe no gerador de manifesto

**Achado do pair-rail (codex, S323), verificado no código.** A resolução
source-sem-`templates/` não vive só no teste: o gerador do baseline tem a
mesma doença, e ali ela decide **ownership real**, não veredito de suíte.

O upgrade exporta `FMS_HASH_ROOT="$SOURCE_DIR"` (`upgrade.sh:3474-3476`)
para gravar o hash do FRAMEWORK e não o do arquivo preservado no target.
O gerador então resolve `"$_wbm_hash_root/$_wbm_rel"`
(`_framework_manifest_set.sh:430-436`) — **sem nenhum fallback para
`templates/`** — e, se o path não existe ali, faz `continue`: nenhum
registro de baseline. E `_wbm_hash_root_applies` (`:260-277`) retorna 0
quando `FMS_HASH_ROOT_PATHS` está unset; medido: **essa variável não é
setada em lugar nenhum** (`grep` em `install.sh` + `upgrade.sh` = zero),
logo o hash-root aplica a TODOS os paths.

Consequência, se `.github/` e `docs/` entrarem no conjunto sem mapeamento
template-aware:

| path enumerado | `SOURCE_DIR/<rel>` | resultado |
|---|---|---|
| `docs/BRANCH-PROTECTION.md` | existe (21.513 b, doc do framework) | grava o hash do **arquivo errado** |
| `docs/rotation-log.md` | existe | idem |
| `.github/workflows/*.template` | ausente | `continue` — **omitido do baseline, em silêncio** |

A primeira rodada de paridade pode passar mesmo assim; o dano aparece no
**upgrade SEGUINTE**, que classifica contra registro errado ou ausente —
exatamente o eixo FRAMEWORK-CHANGED vs ADOPTER-CUSTOMIZED que os
PLAN-167/168 fecharam.

**Diferença entre D2 e D3, e por que os dois precisam de nome próprio:**
o `_parity_classify.py` **tem** o fallback `templates/`, só na ordem
errada (`identity` antes); o `_framework_manifest_set.sh` **não tem
fallback nenhum**. São curas diferentes, em regimes de governança
diferentes — D2 é `scripts/tests/*` (não-canônico, L2); D3 é
`_framework_manifest_set.sh` (**canônico**, `check_canonical_edit.py:199`,
L3+ com cerimônia). D3 pertence à W5-b, não à W5-a.

### 8.4 D4 — `doctor.sh`: a terceira reimplementação, e a que REPARA

**Achado P1 do pair-rail r5, verificado.** O `doctor.sh` também consome o
mapeamento de fonte, e sem fallback nenhum:

- `:507` — entrada AUSENTE: `_hash_file "$SOURCE_DIR/$rel"`
- `:553` — entrada com DRIFT: idem
- `:401` — o REPARO: `cp -p "$SOURCE_DIR/$_rf_rel" "$TARGET/$_rf_rel"`

O `rel` aí vem do MANIFESTO — é relpath de destino. Para `docs/*` isso
seleciona o homônimo errado da raiz; para `.github/*.template` não acha
fonte nenhuma e o registro válido vira *"not repairable"*. E `:401` não
apenas classifica: **copia**. Um doctor que "conserta" com o arquivo
errado é pior do que um que não conserta.

### 8.5 A FORMA do problema: não existe UM resolvedor de fonte

Quatro rodadas de pair-rail acharam três consumidores do mesmo conceito —
*"qual é a fonte do path que o adopter recebeu?"* — e **cada um o
reimplementa, errando de um jeito diferente**:

| consumidor | tem fallback `templates/`? | erro |
|---|---|---|
| `_parity_classify.py:221-227` | **sim** | ordem errada (identity antes) |
| `_framework_manifest_set.sh:430-436` | **não** | hash do arquivo errado, ou `continue` silencioso |
| `scripts/doctor.sh:401,507,553` | **não** | classifica errado E **repara com a fonte errada** — CURADO na S325 (`_route_source`) |
| `scripts/doctor.sh` `_dr_delivered` (:625, usado em :633/:638/:643) | n/a | **quarto sítio, achado do debate S324 — e a medição da S325 o REFINA:** ele decide ENUMERAÇÃO (logo quem é acusado de órfão) por `grep -Eq` sobre o manifesto sanitizado, mas os três fragmentos que testa são `SPEC/v1`, `PROTOCOL.md` e `.claude/.framework-version` — **nenhuma das 6 rotas de entrega**. Medido: `grep -nE 'docs/\|\.github\|BRANCH-PROTECTION\|CODEOWNERS\|rotation-log' scripts/_framework_manifest_set.sh` devolve **1 linha, e é comentário**. Ele é da mesma CLASSE, mas responde outra pergunta (governada por `_ownership_verdict()`), então fazê-lo ler o TSV hoje seria ERRADO. Vira consumidor real só quando a W5-b puser `docs/` e `.github/` no manifesto |

Censo bruto (S323): `SOURCE_DIR/$rel`-e-parentes aparece em **8 arquivos**
sob `scripts/`, com ~23 sítios — número que a S323 marcou como "não
adivinhar, é trabalho da wave".

**CENSO EXECUTADO (S324) — e o número CONTINUA em aberto, agora com a
razão medida.** Dois censos independentes rodaram na S324 e **discordam**,
porque usam padrões de busca diferentes:

| censo | arquivos | sítios | padrão |
|---|---|---|---|
| S323 (herdado) | 8 | ~23 | não registrado |
| S324 — censo largo | 11 | 34 | inclui `_hash_file`/`_digest`/`src_root` e `scripts/tests/` |
| S324 — censo estreito | 10 | 29 | `grep -rn '\$SOURCE_DIR/\$\|\$FMS_HASH_ROOT/\$\|\$_wbm_hash_root/\$\|\$src_root/\$' scripts/ --include='*.sh'` (28 shell) + 1 resolvedor Python |

⇒ **Não fixar nenhum dos três.** A S323 acertou ao dizer que o número é
trabalho da wave; o que a S324 acrescenta é *por que* ele é escorregadio —
a resposta depende de onde se traça a fronteira do padrão, e essa
fronteira é uma decisão de desenho, não uma medição. A **primeira unidade
da W5** é fixar o padrão do censo (e ele passa a ser um TESTE, não uma
medição de sessão), e só então contar.

**O que os dois censos CONCORDAM, e isso basta para decidir:** a maioria
esmagadora dos sítios tem a **forma** do defeito (relpath de DESTINO
resolvido por identidade) mas **não erra hoje**, porque o domínio de
entrada atual contém apenas paths identity-mapped. O censo largo mediu
essa razão: **1 sítio LIVE contra 25 LATENT**.

⇒ E é essa razão que dá a justificativa mais forte do desenho:
**a W5-b, ao estender o domínio de entrada para as duas árvores novas,
converte defeitos latentes em defeitos vivos em massa.** Curar a FORMA
antes de estender o domínio não é elegância — é a diferença entre um
defeito e vinte e cinco. Essa consequência não existia no desenho da
S323.

**Este repo já curou esta forma duas vezes**, e as duas estão no
`CLAUDE.md` §4:

- **PLAN-182** — 16 módulos re-derivavam o slug de projeto localmente, em
  4 grafias, produzindo 7 diretórios onde deviam existir 3. Cura:
  resolvedor único (`_lib/runtime_paths.py`) **mais** um marcador de
  censo (M4) que prova que ninguém re-deriva localmente. 16 → 0.
- **PLAN-167/168** — ownership decidida localmente. Cura:
  `_ownership_verdict()` como função pura única, com tabela-verdade. O
  `CLAUDE.md` fecha com o aviso literal: *"Adding a branch that decides
  ownership locally re-opens the class this replaced."*

**Consequência para o desenho:** curar D2, D3 e D4 como três remendos
independentes reabre a classe no próximo consumidor. A cura com forma
certa é **um resolvedor único de fonte** — a função que responde "dado um
relpath de destino, qual arquivo do checkout o adopter realmente
recebeu?" — mais o censo que prova que ninguém mais responde essa
pergunta sozinho. É literalmente o instrumento do PLAN-182, aplicado a
outro eixo.

#### 8.5.1 A entrega tem TRÊS formas, não uma (S324, achado do pair-rail)

**Correção arquitetural.** O desenho até a S323 tratava entrega como uma
única forma — *copiar `templates/<rel>` para `<rel>`* — e por isso
modelava o resolvedor como `destino → fonte`. Medido no `install.sh`, há
**três** rotas, e a terceira quebra essa assinatura:

| | Rota | Exemplo | Destino |
|---|---|---|---|
| 1 | cópia crua, sufixo cai | `templates/docs/BRANCH-PROTECTION.md` → `docs/BRANCH-PROTECTION.md` | mesmo relpath |
| 2 | cópia crua, destino MANTÉM `.template` | `templates/.github/workflows/validate.yml.template` → idem | mesmo relpath |
| 3 | **RENDERIZADA, destino depende de FLAG** | `templates/.github/CODEOWNERS.template` → `.github/CODEOWNERS` (com `--github-owner`) ou `.github/CODEOWNERS.template` (sem) | **muda com a flag** |

A rota 3 está em `install.sh:1493-1515`, verificada: com `GITHUB_OWNER`
setado o destino é `.github/CODEOWNERS` e o conteúdo sai de
`sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g"` — **bytes que não existem em
lugar nenhum do checkout**. Sem a flag, cai em `install_docs_template` e
o destino guarda o sufixo.

⇒ **O resolvedor único não pode devolver só um path.** Ele devolve
`(fonte, transformação)`, e a transformação é parte da resposta —
`identity` para as rotas 1 e 2, `substitute({{OWNER_HANDLE}} → handle)`
para a 3. Um resolvedor `destino → path` é incapaz de produzir os bytes
que o adopter recebeu na rota 3, e todo consumidor a jusante herda a
incapacidade: o classificador compara contra a fonte errada, o gerador de
manifesto grava digest de bytes que o adopter nunca viu, e o `doctor.sh`
**repara escrevendo o template cru com `{{OWNER_HANDLE}}` literal** sobre
o arquivo renderizado do adopter.

⇒ **E o destino depender de flag significa que a chave do resolvedor não
é o relpath sozinho** — é `(relpath, estado de install relevante)`. O
`github_owner` já está gravado no install-state (`install.sh:2654`), então
a informação existe; o que não existe é o consumidor. Medido:
`grep` por `github_owner|GITHUB_OWNER|CODEOWNERS` em `scripts/upgrade.sh`
devolve **zero**.

⇒ **E há uma QUARTA rota, genérica, que já é live (S324, P1 do pair-rail,
verificado).** `apply_placeholder_substitutions` (`install.sh:2092+`)
renderiza `{{PROJECT_NAME}}`, `{{OWNER_NAME}}`, `{{DOMAIN}}` e mais numa
árvore inteira — `.claude/team.md`, as skills, os templates sob
`--project`/`--owner`. Não é um path: é uma classe de arquivos.

#### 8.5.2 O RESOLVEDOR JÁ EXISTE — e é `_ownership_verdict()` (pivô S324)

**Este é o achado que mais muda o desenho, e ele vem do próprio
`install.sh`.** As linhas `2489-2497` documentam que a classe da §8.5 já
foi encontrada e CURADA neste repositório:

> *"SCOPED, not global (codex W1 round 8, P1): install RENDERS templates
> (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
> so a global `FMS_HASH_ROOT` rewrote every rendered file's baseline to the
> UNRENDERED source — **doctor.sh then reports repo-wide adopter drift**
> and later upgrades classify those files as customized and stop
> refreshing them. **PLAN-167 W2.3 replaced that confinement with an
> EXPLICIT per-surface `hash_source`: the decision says which paths take
> the framework's bytes**, so no global override is set here at all."*

> **⚠️ CORREÇÃO (rodada final do pair-rail, S324, VERIFICADA).** A
> primeira redação desta seção afirmava que `HASH_SOURCE` **é** o
> resolvedor de fonte e que bastaria estendê-lo. **Isso está errado**, e a
> medição é direta: `HASH_SOURCE` é um valor de um enum de **ORIGEM** —
> `HASH_SOURCE` / `HASH_PRIOR_RECORD` / `HASH_CANONICAL_POINTER` /
> `HASH_TARGET` (`_framework_manifest_set.sh:398-410`) — e o ramo
> `HASH_SOURCE` faz `_hash_file "$FMS_SOURCE_ROOT/$_wbm_rel"`, isto é,
> **relpath de DESTINO sob a raiz de fonte**: ele já assume identidade.
> Além disso `_wbm_declared_hash_source` (`:311-315`) despacha num `case`
> com três relpaths *hardcoded*, e o manifesto persiste apenas
> **digest + relpath de destino** — logo o `doctor.sh` não tem de onde
> RECUPERAR a fonte.
>
> ⇒ `CODEOWNERS.template → CODEOWNERS` **mais** renderização é
> inexprimível nessa abstração. Acrescentar linhas na tabela de ownership,
> sozinho, **não** resolve D2/D3/D4.
>
> **A cura correta tem DUAS peças, não uma:**
>
> | | peça | estado |
> |---|---|---|
> | (a) | a decisão de **ORIGEM** — `_ownership_verdict()` + `ownership_table.tsv` | **já existe**; precisa das linhas novas (OQ-4) |
> | (b) | metadado de **ROTA DE ENTREGA**: `destino → (relpath de fonte, transformação)` | **NÃO existe em lugar nenhum** — é o que falta construir |
>
> A peça (b) tem de ser **COMPARTILHADA** pelos três consumidores, e dois
> deles são bash (`_framework_manifest_set.sh`, `doctor.sh`) e um é Python
> (`_parity_classify.py`). Compartilhar entre linguagens significa
> **arquivo de dados** lido pelos dois lados — exatamente a forma de
> `ownership_table.tsv`, não uma constante em cada módulo.
>
> **Consequência de escopo para a W5-a (declarada, não escondida):** a
> W5-a define a tabela de rotas **localmente** dentro de
> `_parity_classify.py`, porque a W5-a é L2 e só toca teste. Isso é
> aceitável **apenas** como primeiro consumidor, e **cria dívida
> nomeada**: a W5-b tem de PROMOVER essa tabela a arquivo de dados
> compartilhado, senão a segunda cópia (no bash) é literalmente o "ramo
> local" que o `CLAUDE.md` §4 proíbe. Item obrigatório da W5-b.

> **⚠️ ESTADO DA DÍVIDA (S325) — REDUZIDA, não fechada.** A promoção
> aconteceu: a tabela saiu de `_parity_classify.py` para
> `scripts/delivery-routes.tsv` (**6 rotas**, 6 colunas
> `dest/src/transform/flag_dep/origin/note`, forma copiada de
> `ownership_table.tsv`), com **dois** consumidores já convertidos —
> `scripts/tests/_parity_classify.py` (os dois dicts históricos passaram a
> ser VIEWS derivadas, então os 10 testes seguem verdes sem UMA asserção
> mudar) e `scripts/doctor.sh` (função `_route_source`, scan linear porque
> o piso de bash 3.2 não tem `declare -A`). O oráculo devolve **0** para os
> três paths ⇒ nada disso exigiu cerimônia.
>
> **O que FALTA para fechar:** `scripts/_framework_manifest_set.sh` é
> **CANÔNICO (=1)** e é o terceiro consumidor. Até ele ler o TSV, a dívida
> está em 1 tabela + 1 leitor canônico pendente, não em zero. O TSV foi
> desenhado para que ele leia as mesmas linhas com o idiom bash que
> `test-ownership-verdict-unit.sh:61` já usa — nenhuma segunda tabela
> precisa ser inventada para ele.
>
> **A verificação NÃO é `grep`** (convergência C3 do debate: grep prova
> MENÇÃO, não USO). Medido na S325: apontar
> `docs/BRANCH-PROTECTION.md` para `templates/docs/rotation-log.md` — uma
> fonte ERRADA mas existente — mantinha **os 10 testes verdes**, porque as
> asserções comparavam `_src_digest` contra a fonte que a própria tabela
> declarava (tautologia estrutural). A cura foi comparar contra uma verdade
> INDEPENDENTE, os call-sites do próprio `install.sh`; com ela os quatro
> controles (remover a tabela / apontar para fonte errada / remover uma
> rota / inventar uma rota) ficam VERMELHOS e a mensagem NOMEIA o plant.
>
> **⚠️ A §8.5.2 como CORRIGIDA na S324 NÃO passou por rodada de rail.** A
> correção (`HASH_SOURCE` não é o resolvedor; peças (a)/(b)) é redação
> pós-rail. Rodar rail sobre ela segue sendo a PRIMEIRA unidade da W5-b.

Três consequências, e elas invertem o plano de ação da §8.5:

1. **A decisão de ORIGEM já tem um dono único, e não deve ganhar um
   segundo.** É o segundo campo do retorno de `_ownership_verdict()` —
   `"<VERDICT> <HASH_SOURCE>"` (`CLAUDE.md` §4). O que falta a ela é
   apenas cobertura das duas árvores novas (OQ-4). O **mapeamento de
   path** é outra peça, nova, descrita no aviso acima.
2. **Construir um resolvedor NOVO ao lado dele seria o anti-padrão que o
   contrato proíbe.** O `CLAUDE.md` §4 fecha com *"Adding a branch that
   decides ownership locally re-opens the class this replaced."* Um
   segundo resolvedor de fonte, mesmo único e bem-feito, é exatamente
   esse ramo local. A §8.5 pedia "um resolvedor único" — a forma certa é
   **um só resolvedor, o que já existe**.
3. **Isso reclassifica a OQ-4 de tarefa lateral para PRÉ-REQUISITO — mas
   não para "a cura".** As linhas novas no `ownership_table.tsv` não são
   burocracia de cobertura: sem elas as duas árvores não têm **origem**
   declarada, e é por isso que `_framework_manifest_set.sh:430-436` cai no
   `continue`. Mas, pela correção acima, linhas sozinhas **não bastam** —
   elas resolvem a origem, não o mapeamento de path.

⇒ **A cura de D2/D3/D4 é, nesta ordem:** (a) construir o metadado de rota
de entrega `destino → (fonte, transformação)` como **dado
compartilhado**; (b) declarar as duas árvores na decisão de ownership
(OQ-4) para que tenham origem; (c) fazer os três consumidores lerem
(a) e (b) em vez de reconstruir o path localmente. O `doctor.sh` é o caso
mais agudo porque `:401` **copia** — e o comentário do `install.sh:2489`
prova que a falha "doctor reporta drift repo-wide" já foi vivida uma vez
neste repositório.

#### 8.5.3 Lacuna nomeada: pre-Wave-B não tem o estado que a rota 3 exige

**P1 do pair-rail S324, verificado em `upgrade.sh:3629-3633`.** Para um
alvo sem registro de install pré-Wave-B, o upgrade **sintetiza**:

```
req = { "argv": [], "target": …, "placeholders": {},
        "note": "synthesized by upgrade.sh - no pre-Wave-B install.sh record existed" }
```

Ou seja: um adopter instalado por uma v1.0.x **com** `--github-owner` tem
`.github/CODEOWNERS` renderizado no disco e **nenhum** `github_owner`
gravado. A chave `(relpath, estado)` da rota 3 não é computável para ele —
nem para reconhecer o destino, nem para regenerar os bytes, nem para
reparar. A fixture do pin `v1.2.0` **não** cobre esse caso e passaria
verde.

⇒ Item obrigatório da W5-b: definir comportamento explícito
(**preservar**, não adivinhar) e adicionar fixture **pré-install-state com
owner**. Preservar é a única opção compatível com a regra de under-claim:
sem estado, o arquivo é do adopter.

**E é por isso que esta análise para aqui.** A próxima descoberta útil
não vem de outra rodada de rail: vem de um CENSO MECÂNICO que enumere os
consumidores **e as rotas de entrega**. Rail é bom em achar a classe;
censo é o que a fecha. A S324 é a evidência: a rodada final de rail achou
a rota 3, e foi a MEDIÇÃO subsequente — não a rodada — que mostrou que o
censo da S323 tinha a forma errada e que D2 expõe 3 paths, não 2.

### 8.6 A cura PARCIAL já existe neste mesmo arquivo, para outra árvore

`upgrade.sh:3103-3115` resolve exatamente esta classe para os schema
docs, e o comentário nomeia as duas armadilhas que o desenho da S323
tinha deixado em aberto:

1. **Refresh HASH-GATED, não `backup_and_replace` cego.** *"a blanket
   backup_and_replace would CLOBBER an adopter-modified schema … Refresh
   is therefore HASH-GATED: only a byte-pristine copy of a KNOWN prior
   framework generation is replaced; anything else is PRESERVED loudly."*
   É o molde de `_protocol_pointer_is_degraded` que a W1 também usa.
2. **A flag de baseline deriva do RESULTADO da operação, não de um
   registro do install.** *"the schemas enter the enumeration ONLY when
   this upgrade left FRAMEWORK bytes at the path (INSTALLED / REFRESHED /
   IDENTICAL). PRESERVED and SKIPPED stay out."*

**Isso responde o P1 de migração do pair-rail r2** — como o upgrade
distingue "cópia do installer antigo" de "arquivo pré-existente pulado"
num adopter cujo install-state só tem registro grosso de tentativa, e
cujo baseline não contém nenhuma das duas árvores. A resposta não é
proveniência nova: é **hash contra o conjunto de gerações conhecidas do
framework**. Não-pristine ⇒ PRESERVED, ruidosamente.

E resolve o P1 de granularidade de forma mais limpa do que mover
`_state_record_op` para dentro dos ramos de cópia: a decisão passa a ser
**por path e por resultado**, derivada da operação que de fato ocorreu —
`_state_record_op` fica como o breadcrumb que já é, sem virar fonte de
verdade de ownership.

**Como o conjunto de gerações é enumerado — e por que NÃO é por tags.**
A primeira redação desta seção disse "pergunta finita, respondida por
enumeração de tags". Errado, e o pair-rail r4 mostrou onde: o install por
clone (`README.md:104-121`) instala **qualquer commit de `main`**, não só
release tags — uma geração que existiu apenas num commit sem tag ficaria
de fora, e um adopter pristine seria PRESERVED como se tivesse
modificado o arquivo, deixando D1 stale justamente em quem a cura
deveria alcançar. O precedente resolve melhor (`upgrade.sh:3204-3212`):
as gerações vêm do **histórico git de cada arquivo**, sob contrato
explícito — *"any commit that changes one of these schema docs MUST
append the hash of the generation it replaces to that doc's list, in the
SAME commit"* — com teste que deriva o conjunto do git *"instead of
memory"* (`test-schema-generation-pins-unit.sh`). E há incidente real
citado ali: `996d72b` mudou o PLAN-SCHEMA sem listar a geração
`8ca4f866`, e o resultado foi o smoke-install vermelho da S313.

**Consequência para a W5-b:** ela ESTENDE o padrão dos schema docs a mais
duas árvores — não inventa mecanismo. **Mas o hash-gate NÃO fecha a
migração sozinho** (§8.7).

### 8.7 O que o hash-gate NÃO resolve — e por que isso é decisão do Owner

**Achado P1 do pair-rail r4, verificado contra o ADR.** O refresh
hash-gated distingue "pristine de uma geração conhecida" de "modificado".
Ele **não** distingue *entregue pelo installer* de *já estava lá e por
acaso é byte-idêntico a um template antigo*. Nesse caso o
`install_docs_template` fez EXISTS-skip — o arquivo é do adopter — e o
gate marcaria REFRESHED, **tomando posse de arquivo adopter-owned**.

Isso contradiz frontalmente a regra de under-claim do
`ADR-155-AMEND-1:87-125`, que existe por causa de um caso idêntico já
vivido (r17: *"on a `maintainer` install where the destination ALREADY
had its own `SPEC/v1`, `install_one` EXISTS-skips — the file on disk is
the adopter's"*). O dano não é teórico: `uninstall.sh` remove arquivos
registrados no manifesto que casem por hash.

**Não há algoritmo que feche isto.** Para um adopter histórico o registro
de entrega não existe, e nenhuma inspeção de conteúdo recupera a
intenção. As saídas são três, e a escolha é do Owner, não do CEO:

| | Rota | O que custa |
|---|---|---|
| i | **Não migrar** — só instalações futuras ganham posse dessas árvores | adopters históricos ficam STALE nessas duas árvores para sempre; a rota B do e2e (instala no pin, faz upgrade) cai exatamente nesse caso, então o main pode NÃO ficar verde |
| ii | **Migrar com hash-gate**, aceitando a colisão como risco declarado | fecha o main; assume o risco de tomar arquivo adopter-owned byte-idêntico a um template antigo |
| iii | **Exigir ato explícito do adopter** (flag tipo `--adopt-github-docs`) | sem risco de tomada; exige ação humana em cada adopter e não fecha o main sozinho |

Registrado como **OQ-5, bloqueante**. A W5-b não abre antes da resposta.

> ## ✅ OQ-5 — RESPONDIDA pelo Owner (2026-08-24): rota **(ii) COM EMENDA**
>
> A rota (ii) sobrevive, **mas não como estava**: o debate mediu que ela não
> alcança a população que existe para curar. `upgrade.sh:798-799` resolve
> `CEREMONY_EFFECTIVE="user"` quando não há install-state legível, e a
> entrega é gateada em `CEREMONY != user` (`install.sh:1484`, `:1525`) ⇒ o
> adopter HISTÓRICO não recebe nada, e o e2e é estruturalmente incapaz de
> ver isso porque o pin `v1.2.0` grava cerimônia.
>
> **A emenda ratificada:** sem install-state legível **mas com
> `.claude/.framework-version` presente**, tratar como instalação de
> framework e ENTREGAR. O marcador é a evidência de que aquele diretório já
> é um adopter — que é exatamente a distinção que o `CEREMONY_EFFECTIVE`
> fail-safe perde. O default para um diretório que nunca recebeu install
> **não muda**.
>
> **Consequência de teste, e ela é obrigatória:** o Check da rota (ii) tem
> de rodar num e2e **SEM o pin** `v1.2.0`, senão ele continua cego pela
> mesma razão de hoje. Um Check que só exercite o caminho pinado passa
> vacuamente — é a classe C2 deste próprio debate.

### 8.8 Por que a ordem é D2/D3/D4 ANTES de D1

Enquanto D2 não estiver curado, o veredito do e2e sobre `docs/` sai na
classe errada — e não se valida a cura de D1 com um instrumento que
reporta a classe errada. Curar D1 primeiro produziria, no melhor caso,
um verde que ninguém consegue atribuir: não daria para distinguir
"o upgrade passou a entregar" de "o classificador parou de comparar
contra o arquivo errado".

Ordem, e o custo de cada:

| | Defeito | Superfície | Canônico? | Nível | Cerimônia |
|---|---|---|---|---|---|
| 1º | **D2** | `scripts/tests/_parity_classify.py` | **NÃO** (`scripts/tests/*` fora de `_CANONICAL_GUARDS`) | L2 | não exige |
| 2º | **D1 + D3** | `install.sh` + `upgrade.sh` + `_framework_manifest_set.sh` | **SIM** (`check_canonical_edit.py:189,191,199`) | **L3+** | **exige** + debate + ADR |
| 2º | **D4** | `scripts/doctor.sh` | **NÃO** — ver correção abaixo | L3+ (anda com D1/D3) | não exige sentinel, mas ENTRA no Scope |

**Correção medida na S324 (a versão anterior desta tabela estava
ERRADA).** O oráculo suportado — `python3 .claude/hooks/check_canonical_edit.py
--is-canonical <path>` — devolve, com controle positivo passando:

```
scripts/tests/_parity_classify.py     0
scripts/doctor.sh                     0     <-- NÃO é canônico
scripts/install.sh                    1
scripts/upgrade.sh                    1
scripts/_framework_manifest_set.sh    1
```

As três linhas citadas (`:189`, `:191`, `:199`) cobrem exatamente
`install.sh`, `upgrade.sh` e `_framework_manifest_set.sh`. **`doctor.sh`
não está na guard list** — a linha anterior agrupava os quatro sob "SIM"
e o rótulo era largo demais. A citação sempre foi honesta; o rótulo não.

**Consequência que MUDA o material de cerimônia, não só a prosa.** O gate
G4 (`PLAN-182/OWNER-S321-LAND.sh:174`) faz
`comm -23 touched scope` sobre **todos** os paths de
`git apply --numstat`, **sem filtro de canonicidade**. Um Scope que
liste só os 3 canônicos + o ADR, num patch que também toca `doctor.sh`,
aborta o land em
`die "o patch toca path(s) FORA do Scope assinado"`. O Scope tem de
enumerar **todo path tocado**, canônico ou não — que é o padrão que o
sentinel do PLAN-177 já usa ("Livre, MESMO commit").

D3 e D4 andam junto de D1 por construção: só se manifestam quando as duas
árvores passarem a ser enumeradas. D1 e D3 são a mesma edição canônica;
D4 é edição livre no MESMO commit. Se a §8.5 estiver certa, os três não
são remendos separados — são um resolvedor único mais o censo que o
protege.

D2 sozinho **não** deixa o main verde: os dois templates de workflow
seguem STALE legítimo, porque D1 é real. D2 muda `BRANCH-PROTECTION.md`
de UNCLASSIFIED para STALE — isto é, converte três fatais em três fatais
da MESMA classe, todos atribuíveis a D1. Esse é o ponto: depois de D2 há
UMA causa, não duas.

**MEDIDO na S324 — a afirmação acima deixa de ser raciocínio.** A classe
resultante depende de o template ter divergido entre o pin do e2e
(`v1.2.0`, `test-install-upgrade-parity-e2e.sh:110`) e HEAD, porque é isso
que separa `hb == h_pin ≠ h_head` (⇒ STALE) de `h_pin == h_head`
(⇒ outra classe). Diferença de digest, `git show v1.2.0:<path>` contra o
disco:

| `templates/…` | pin `v1.2.0` | HEAD | veredito |
|---|---|---|---|
| `docs/BRANCH-PROTECTION.md` | `61025a164c718e8b` | `966e057147fbc3dc` | **DIVERGIU** |
| `docs/rotation-log.md` | `0ab61d1615aad651` | `0ab61d1615aad651` | idêntico |
| `.github/workflows/validate.yml.template` | `11298f5bc28fa7b8` | `7d0ee14b9871d0e7` | **DIVERGIU** |
| `.github/workflows/benchmarks.yml.template` | `87106ceb7d4fec23` | `e59a27bd2757843f` | **DIVERGIU** |
| `.github/CODEOWNERS.template` | `1955b01a16069f6d` | `1955b01a16069f6d` | idêntico |

Três consequências, todas medidas e não inferidas:

1. **`docs/BRANCH-PROTECTION.md` sai `STALE` depois da cura de D2** — a
   fatalidade permanece, e a lista de classes FATAIS
   (`_parity_classify.py:430-433`) inclui `STALE`. **D1 é load-bearing
   para o verde; D2 não é.** O ganho de D2 é diagnóstico: três fatais de
   UMA causa em vez de duas.
2. **`docs/rotation-log.md` é idêntico pin↔HEAD** — confirma por medição
   por que ele é falso-verde LATENTE e não acendeu na S322: o defeito de
   resolução existe, mas `ha == hb` impede a classificação de ser
   alcançada.
3. **`CODEOWNERS.template` é idêntico pin↔HEAD** — confirma que qualquer
   teste de CODEOWNERS com o pin default é **VACUOSO**. O caso
   `--github-owner` da W5-b tem de PLANTAR divergência para ter poder de
   detecção.

### 8.9 Atalhos já descartados (não repetir o trabalho)

1. **`KNOWN_OPEN` não serve.** O ledger existe e está vazio
   (`_parity_classify.py:149-151`, "PLAN-166 W1 landed"), mas o driver
   imprime `RESULT: KNOWN-OPEN (exit 2) - This is a FAILURE, not a skip`
   e faz `exit "$OVERALL"`; sob `set -e` o exit 2 derruba o step igual.
2. **`ACCEPTED` seria mascarar.** O próprio classificador avisa: *"do not
   widen a pattern to make it disappear"*. Estes paths não são generated
   nem adopter-owned — são conteúdo de framework que o upgrade deveria
   entregar.
3. **Reverter os 3 arquivos** (rota A da S323) foi apresentado ao Owner e
   **recusado** em favor da rota C (§6).

### 8.10 Onde vive a wave que isto propõe

**A W5 NÃO está neste arquivo, e é de propósito.** O `status: reviewed`
do frontmatter é de 2026-08-20 e cobre W0–W4; o Owner autorizou apenas
*planejar* em 2026-08-23 (§6). Por `PLAN-SCHEMA.md` §status, `reviewed`
significa "o humano leu e aceitou; a execução pode começar" — colocar
checkboxes novas sob esse status faria qualquer dispatcher ou sessão
futura tratá-las como executáveis. Uma nota em prosa não muda esse
estado **machine-visible**, e o pair-rail r3 marcou isso duas rodadas
seguidas.

A wave vive em **`.claude/plans/PLAN-183/w5-draft-s323.md`**, em `draft`,
com orçamento próprio. Esta seção §8 fica aqui porque é EVIDÊNCIA e não
tem checkbox — o mesmo critério que a §7 declara para si.

Promoção: quando o Owner aceitar, o conteúdo do draft entra neste plano
com a revisão refrescada, ou vira plano próprio.

## Waves

### W0 — Reproduzir e medir antes de curar

> **US1, US2 e US4 são read-only. US3 NÃO é** — ele edita
> `smoke-install.sh` / `smoke-install.yml` e executa o CI entregue.
> Marcado explicitamente porque a redação anterior rotulava a wave
> inteira como read-only, e um executor teria de violar o contrato da
> wave ou deixar um P0 aberto (pair-rail r7).

- [x] `[P0][US1]` Testar a **hipótese aritmética** do §4 ANTES de
      qualquer arqueologia: confrontar os tetos declarados
      (`settings.base.json`) com os tempos do relatório e concluir qual
      caminho pode tê-los produzido. Só abrir a busca pela fonte do
      `/doctor` se a aritmética não explicar.
      **FECHADO (S317, 2026-08-20) — VEREDITO: `explicado pela
      aritmética`. A arqueologia NÃO abre.** Conta fechada
      nominalmente: 35 `Bash` + 25 `Write` + 7 `Stop` + 2
      `PreToolUse:Read` + 2 `UserPromptSubmit` = **71** (§4), todos
      `hook_cancelled` com `timeoutMs=5000` e `timedOut=true`, na janela
      2026-08-06..08-16 — a única que devolve 71. **Três claims do §4
      CAÍRAM e estão curadas lá:** o `/doctor` **está** contando breach
      de teto por-hook; os 231 s são o `on-stop.sh` do plugin Warp
      (`hook_success`, exit 0); os 175 s são o pair-rail em
      `PreToolUse:Edit`, `hook_success`, abaixo do teto de 210 s.
      **Achado que reescreve a W4:** 70 dos 71 vêm do repo do PRÓPRIO
      framework, 1 de `foxbit-bot-arbitrage`, **ZERO do adopter**.
      Check: a conclusão é registrada com os números dos dois lados E a conta 35+25+7=67≠71 fechada nominalmente — os 4 casos restantes recebem categoria (cura do r9 #3); veredito entre {explicado pela aritmética, exige arqueologia} — "não medido" não fecha
- [x] `[P0][US2]` Medir a **taxa de censura à direita**: invocações
      esperadas contra linhas de evento emitidas, por hook. Estender a
      forma que JÁ existe (`check_name` e `timeout_ms`), nunca criar
      paralela. Pré-condição: verificar se o drain do spool varre PID
      morto.
      **FECHADO (S322) — e o resultado é que a taxa é INCOMPUTÁVEL para
      47 dos 49 hooks, por razão ESTRUTURAL do schema, não por falta de
      esforço.** Instrumento rastreado:
      `.claude/plans/PLAN-183/w0-us2/measure-right-censoring.py`
      (read-only; resolve o state dir só via
      `_lib.runtime_paths.runtime_state_dir()`, nunca re-deriva o slug).
      **A causa raiz:** o audit-log **não carrega identidade do hook
      emissor** — não existe ação `hook_invoked`/`hook_entered`, então
      não há como ligar uma invocação (que vive no transcript, como
      `attachment.type ∈ {hook_success, hook_cancelled}`) à linha de
      evento que ela produziu, exceto onde existe um par 1:1 com produtor
      ÚNICO verificado. Só **2 de 49** registros têm esse par.
      **O único número que é taxa de verdade:** `Stop.py`
      ("Session interrupt cleanup…") → `session_stop` =
      `1 − 36/36` = **0,0% de censura** (36 invocações, 36 linhas,
      `hook_cancelled` na janela = 0; produtor único em
      `audit_emit.py`).
      **O que parece taxa e NÃO é:** `check_output_secrets.py` →
      `tool_call_lifecycle_recorded` = 517 inv / 2.473 linhas = **razão
      4,78**, rotulada explicitamente como MULTIPLICIDADE (três
      produtores emitem a mesma ação). Publicar isso como "censura
      negativa" seria um número falso.
      **Dois hooks com o denominador ele mesmo censurado:**
      `SessionEnd.py` e `UserPromptSubmit.py` — esses eventos **nunca**
      registram `hook_success` no transcript (só `hook_cancelled`, e só
      quando cancelam), então nem o denominador existe.
      Contexto medido na mesma passada (janela
      `2026-08-21T21:40:18Z .. 2026-08-23T05:31:28Z`, 11.252 linhas):
      **71,0% dos eventos são não-atribuíveis** (7.986/11.252;
      `policy_evaluated` + `policy_denied` no topo — a mesma assinatura
      da S321). `hook_cancelled` all-time = **132**, com reconciliação
      fechando por duas decomposições independentes (por evento:
      PreToolUse 99 + PostToolUse 22 + Stop 8 + UserPromptSubmit 3; por
      dia: 2+1+45+83+1). Denominador all-time = 126.798 registros.
      **Consequência para a W4:** a pré-condição do drain foi respondida
      por construção — a medição é sobre o log JÁ drenado, e a
      reconciliação aritmética (total direto == soma por (event,command)
      == soma por dia) fecha, o que exclui perda no drain como
      explicação. O que a W4 precisa decidir é outra coisa: se quer a
      taxa por hook, o schema precisa de uma ação `hook_invoked`
      (mudança em `SPEC/v1/audit-log.schema.md`, canônica).
      Republicar o número, nunca ajustar o script — a cadeia cresce a
      cada sessão (esta medição já andou 635 linhas em relação à do
      recon, 3 h antes).
      Check: a taxa de censura é um número publicado no plano, por hook, com o método ao lado
- [ ] `[P0][US3]` **Estender** `smoke-install.sh` e
      `smoke-install.yml` (o step `:276` já existe) para cobrir
      `.github/` e para ATIVAR e EXECUTAR o CI entregue. Nunca uma
      bateria paralela.
      Check: smoke-install passa a referenciar validate.yml.template; hoje o grep devolve ZERO — o teste é essa referência existir e o step rodar
- [x] `[P1][US4]` Inventariar quais dos cinco artefatos de ownership a
      W1 vai tocar, e orçar o ciclo de re-baseline em tokens e sessões.
      **FECHADO (S322) — VEREDITO: a W1 toca 4 dos 5 nomeados, e a lista
      de CINCO está INCOMPLETA: o conjunto real é SETE.**
      `test-protocol-pointer-render.sh` e `test-protocol-pointer-inv4.sh`
      são edição OBRIGATÓRIA — e o segundo **contradiz o próprio Check
      da W1** (`assert_sound()` exige o caminho ABSOLUTO presente, então
      "inv4 verde" é insatisfazível depois de relativizar).
      `ownership_table.tsv` ganha a tríade da classe nova de
      `live_content`; `ownership-baseline-map.txt` é RE-GRAVADO pelo
      harness, nunca editado à mão; `ownership-expected-reds.txt` só
      muda se o conjunto RED mudar, mas re-verifica a cada iteração.
      Faltam na lista de cinco: `docs/ownership-decision-table.md`
      (enum §2.4 + regra de legalidade) e
      `scripts/tests/test-ownership-table.sh` (o ramo de `case` que
      instancia o `live_content` novo — sem ele, cada linha nova vira
      `HARNESS-ERR`, não veredito). Piso do re-baseline: **40-70k tokens
      em 2-4 iterações**, 1 sessão pela rota LOCAL e 2-4 pela nightly.
      Tabela, evidência e aritmética em §7.
      Check: none (levantamento — a saída é a lista de artefatos e o orçamento)

### W1 — Ponteiro portátil e retroativo (A1)

- [ ] `[P0]` Relativização decidida **DENTRO** de
      `_render_protocol_pointer` (a função já recebe `$2=TARGET`), não
      no call-site. **Portabilidade redefinida pela cura do r9 #1** — o
      e2e exigido pelo r8 era IMPOSSÍVEL quando `SOURCE_DIR` está fora
      de `TARGET` (mover o target sozinho quebra qualquer codificação da
      relação entre os dois): o que o ponteiro relativo compra é
      sobreviver a mover **source e target JUNTOS**, preservando a
      relação entre eles (outro `$HOME`, outro username — a classe real
      de quebra do A1); mover o target SOZINHO tem como resposta correta
      um erro NOMEADO que conduz ao reparo, nunca resolução mágica.
      Vendorizar o protocolo dentro do target foi considerado e
      REJEITADO: duplica a verdade e contradiz a doutrina 167/168 (um
      gerador, uma verdade).
      Check: e2e move source+target JUNTOS (prefixo comum renomeado, simulando outro home) e o ponteiro RESOLVE; segundo e2e move o target SOZINHO e o corpo do ponteiro conduz ao reparo nomeando --protocol-source; asserir so relatividade in-place segue insuficiente (pair-rail r8+r9)
      — ⛔ S328: os DOIS e2e do Check não existem no HEAD (nenhum teste move source+target juntos, nenhum assere erro nomeado de `--protocol-source`), e a decisão in-function que está na árvore (`scripts/_framework_manifest_set.sh:1384-1386`) é do PLAN-168 (`67a4c75`), não desta wave — a W1 segue "cura desenhada e não executada" (`PLAN-183/resposta-ao-campo.md:44`).
- [ ] `[P0]` **Remediação retroativa:** reconhecedor de "absoluto
      legado" no molde de `_protocol_pointer_is_degraded`
      (`_framework_manifest_set.sh:736-742`), com re-render byte-a-byte,
      falha **para preservação**, e backup em `$BAK_DIR`.
      Check: e2e — instalação feita com a versão ANTERIOR, ao rodar upgrade.sh, termina com ponteiro relativo
      — ⛔ S328: não existe reconhecedor de "absoluto legado" — o único da árvore, `_protocol_pointer_is_degraded` (`scripts/_framework_manifest_set.sh:1439`, `67a4c75`), reconhece a classe do literal `{{PROTOCOL_SOURCE}}`, e o e2e "instalar com a versão ANTERIOR e depois dar upgrade" não existe.
- [x] `[P0]` Usar a interface que **já existe**: `--protocol-source` e
      `CEO_PROTOCOL_SOURCE` (`install.sh:409,522,663-668`), reusada pelo
      upgrade via install-state. Não introduzir env nova.
      Check: nenhuma env alternativa ao par `--protocol-source`/`CEO_PROTOCOL_SOURCE` aparece em `scripts/`; `--protocol-source` e o unico escape citado *(Check reescrito por PROPRIEDADE na S334 — a redacao anterior nomeava o proprio token que proibia, e por isso nunca podia fechar)*
      — ◐ S328: entregue a metade do gerador — `--protocol-source`/`CEO_PROTOCOL_SOURCE` em `scripts/install.sh:409,522`, reusados pelo upgrade via install-state (`scripts/upgrade.sh:1745-1760`), e a env alternativa com 0 ocorrências em `scripts/`, tudo código pré-existente do PLAN-167/168 e não entrega desta wave; falta a metade do plano — o token que o Check proíbe segue presente no próprio Check (:1172) e em 5 arquivos de `PLAN-183/debate/round-1/`.
      — ✅ S334: FECHADO. O Check acima foi reescrito por propriedade (não nomeia mais o token); os 5 arquivos de `debate/round-1/` são registro histórico CONGELADO — ficam anotados aqui como tal e não se editam (a doutrina de evidência congelada proíbe reescrever debate landado; menção histórica em debate não é ocorrência em `scripts/`, que é onde a propriedade mira). Gerador: 0 ocorrências, medido.
- [ ] `[P0]` O corpo renderizado passa a **nomear** a interface — hoje
      ele manda "editar" sem dizer que existe flag para isso.
      Check: o ponteiro renderizado contem a string --protocol-source
      — ⛔ S328: `grep --protocol-source` no corpo renderizado (`scripts/_framework_manifest_set.sh:1381-1440`) devolve 0 — a linha :1431 ainda manda só "Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout".
- [ ] `[P1]` Preservação silenciosa vira **preservação AVISADA**:
      WARNING quando um ponteiro preservado contém caminho absoluto.
      Check: e2e com ponteiro absoluto editado pelo adopter — a edição sobrevive E o WARNING aparece
      — ⛔ S328: o ramo `PRESERVE_OWNED` (`scripts/upgrade.sh:1855-1866`) imprime PRESERVED sem inspecionar o corpo preservado, e não há condição de caminho absoluto em ponto nenhum de `_refresh_protocol_pointer` (`:1718-1893`).
- [ ] `[P0]` Preservar INV-4 — a cura não pode reabrir o que os
      PLAN-167/168 fecharam.
      Check: scripts/tests/test-protocol-pointer-inv4.sh verde
      — ◐ S328: entregue o instrumento — `scripts/tests/test-protocol-pointer-inv4.sh` existe desde `67a4c75` (PLAN-168) e está fiado na CI (`ownership-nightly.yml:178`; `smoke-install.yml:80,151`); falta a cura da W1 que ele deveria proteger, então hoje o check é vacuoso.

### W2 — CI que passa no adopter (A2/A3/A7)

- [ ] `[P0]` **Vínculo template contra vivo, antes de qualquer patch.**
      Hoje o vivo tem 71 steps e 79.993 bytes (`runs-on: Ceo`, timeout
      25, checkout SHA-pinado) e o template tem 14 steps e 226 linhas
      (`ubuntu-latest`, timeout 5, `checkout@v4` sem pin) — e **nada
      regenera ou diffa um contra o outro**. É a única superfície de
      governança sem gate de drift. Gate de drift OU declaração escrita
      de "subconjunto mínimo congelado", com o teste que a executa.
      Check: a wave escolhe UM ramo na abertura e registra qual. Ramo A (gate de drift) — existe gate que falha quando o vivo ganha step fora da allowlist de divergencia. Ramo B (subconjunto congelado) — existe teste que falha se o template divergir do subconjunto declarado, e a declaracao nomeia cada step congelado. [pair-rail r8: o Check anterior exigia o ramo A e tornava o ramo B inexecutavel]
      — ⛔ S328: nenhum ramo foi escolhido nem registrado — "Ramo A"/"Ramo B" não aparecem em lugar nenhum de `.claude/plans/PLAN-183/` fora deste Check, e nenhum teste diffa o template contra o vivo (os 4 arquivos de teste que citam `validate.yml.template` o tratam como DESTINO de rota de entrega, não como gate de drift).
      — ✅ S334: **Ramo B escolhido e REGISTRADO** (decisão de abertura de wave; autonomia da sessão ratificada pelo Owner em chat). A declaração congelada vive em `.claude/scripts/tests/test_validate_template_frozen_subset.py` (`FROZEN_STEPS` nomeia cada um dos 11 steps, na ordem; pins congelados junto: checkout SHA-pinado 40-hex, `VERSION="1.7.7"` do actionlint, `timeout-minutes: 15`) e o teste falha em QUALQUER divergência — step a mais, a menos, fora de ordem, pin perdido, ou retorno de um dos 3 removidos. Coletado por `pytest.ini` testpaths (`.claude/scripts/tests`); controle negativo provado vermelho (step renomeado ⇒ FAIL) na S334. Racional contra o Ramo A: o vivo (71 steps) muda por cerimônia própria e um gate vivo→template re-acoplaria as duas superfícies que `4f750f0` separou deliberadamente; divergência DELIBERADA do template passa a exigir editar a declaração no MESMO patch.
- [x] `[P0]` **Re-derivar o censo step a step**, com mecanismo nomeado
      por step. Mínimo a cobrir: `:108-109` (PyYAML — dependência de
      terceiro, contra o stdlib-only do `CLAUDE.md` §3), `:148,158`
      (`unittest discover` — falso-vermelho por conftest pytest-only),
      `:176-177` (actionlint baixado de `main` **sem pin**, gradando os
      workflows do próprio adopter), `:77` (remediação aponta arquivo
      que o adopter não tem), `:22-23` (timeout 5 contra 25), `:27`
      (checkout sem pin).
      Check: tabela step para mecanismo para disposicao cobrindo os 14 steps; nenhum step fica sem veredito
      — ◐ S328: entregue o censo aplicado — `4f750f0` levou `templates/.github/workflows/validate.yml.template` de 14 para 11 steps, com mecanismo nomeado por step no próprio arquivo (checkout SHA-pinado :31, PyYAML condicional :107-113, actionlint pinado em 1.7.7 :177, timeout 15 :26, remoção do skill-inventory explicada :193-198); falta a tabela step→mecanismo→disposição cobrindo os 14 steps, e o artefato mais próximo (`PLAN-183/resposta-ao-campo.md:63-75`) dispõe só os 3 steps removidos.
      — ✅ S334: tabela completa abaixo, derivada COMPORTAMENTALMENTE (steps velhos de `git show afd228b:templates/.github/workflows/validate.yml.template`, novos do HEAD; razões dos removidos de `resposta-ao-campo.md` §A2 e dos comentários in-file do template). Item FECHADO.

      | # | step (afd228b, 14) | mecanismo | disposição |
      |---|---|---|---|
      | 1 | Checkout | `actions/checkout@SHA` 40-hex (:31) + `timeout-minutes: 15` (:26) | mantido, endurecido |
      | 2 | Run validate-governance.sh | governança core no adopter | mantido |
      | 3 | Run check-skill-health.sh --ci | telemetria advisory | mantido |
      | 4 | Run check-pitfall-regression.sh | catálogo universal de pitfalls | mantido |
      | 5 | Contamination check | allowlist NEUTRA pós-A7 (identidade do mantenedor removida) | mantido |
      | 6 | Placeholder lint | core/frontend only | mantido |
      | 7 | Validate settings.json and YAML catalogs | PyYAML **condicional** (:107-113) — stdlib-only preservado quando ausente | mantido, mecanismo trocado |
      | 8 | Shellcheck hooks and scripts | exclui `legacy/` | mantido |
      | 9 | Run Python hook unit tests | `unittest discover` contra `.claude/hooks/tests` que o install **nunca embarca** ⇒ `Ran 0 tests OK` rc=0 — **verde vácuo**; na população mis-installed purgada, `ImportError` (template :148-156) | **REMOVIDO** (`4f750f0`; slot documentado: "Put YOUR OWN test command") |
      | 10 | Run Python script unit tests | idem #9 (`.claude/scripts/tests` nunca embarcada) | **REMOVIDO** (mesmo slot) |
      | 11 | Check tier boundaries | core/frontend não referencia domains | mantido |
      | 12 | actionlint | release asset **pinado** `VERSION="1.7.7"` (:176-178) — antes baixava de `main` sem pin (supply-chain grading os workflows do adopter) | mantido, endurecido |
      | 13 | Skill inventory idempotency | estruturalmente impossível no adopter (inventário por perfil ≠ completo; template :193-198) | **REMOVIDO** |
      | 14 | Hook and script executable bits | bits de exec | mantido |
- [x] `[P0]` **`Contamination check`: manter "ele estava CERTO"** quanto
      ao gatilho do A1, **e** curar o A7 — o padrão embarca a identidade
      do mantenedor, o arquivo é entregue ao adopter, e ele se
      auto-isenta. Cura = padrão **configurável na instalação**.
      Check: instalacao limpa produz um guard cujo padrao NAO contem o nome do mantenedor; controle negativo com o nome plantado dispara
      — ✅ S328 (2026-08-25): .claude/scripts/check_contamination.py:74,80,83,108,133 + .claude/scripts/tests/test_check_contamination.py:223 · commit 4f750f0
- [ ] `[P0]` Após a W1, re-rodar o `Contamination check` no adopter:
      espera-se VERDE **sem tocar a allowlist**. Se exigir mudança de
      allowlist, PARAR — mexer nela esconderia a contaminação.
      Check: o step sai verde e o diff da allowlist e vazio
      — ⛔ S328: bloqueado na W1, que não foi executada (`PLAN-183/resposta-ao-campo.md:44`) — não há em disco registro de re-execução do `Contamination check` no adopter, e a allowlist MUDOU em `4f750f0` (`check_contamination.py:133`), logo o "diff vazio" tem de ser medido contra a baseline pós-A7.
- [x] `[P0]` `benchmarks.yml.template`: ou o `install.sh` entrega
      `.github/scripts/`, ou a referência sai. Cabeçalho declara a
      variável de API key exigida e o custo em dinheiro do adopter.
      Check: instalacao limpa nao deixa referencia a script ausente
      — ✅ S328 (2026-08-25): templates/.github/workflows/benchmarks.yml.template:9-15,17-22 + scripts/tests/smoke-install.sh:149-152 · commit 4f750f0
- [x] `[P1]` Template recebe kill-switch de job espelhando o vivo
      (16 ocorrências no vivo contra 0 no template).
      Check: actionlint limpo e o if presente no nivel de job
      — ✅ S328 (2026-08-25): templates/.github/workflows/validate.yml.template:25 (`if` no nível de job) · commit 4f750f0 — ressalva: a metade "actionlint limpo" está atestada só no corpo do commit, nenhum gate vivo linta o template.
- [ ] `[P1]` Nomear que o install entrega `.template` (**inerte**) e que
      o CI só existe após rename — o passo de ativação vira explícito.
      Check: AC-2 nomeia o passo de ativacao; prova em repo descartavel nosso
      — ◐ S328: entregue a nomeação para UM dos dois templates — `templates/.github/workflows/benchmarks.yml.template:3-7` declara "INERT AS SHIPPED" e o `git mv` de ativação (`4f750f0`; 1 ocorrência da string em todo `templates/`); falta o mesmo cabeçalho em `validate.yml.template`, e o AC-2 (:1301 pré-S328) segue `- [ ]` sem prova de template ativado saindo verde em repo descartável.

### W3 — Catálogo e a regra de VETO (A4)

- [x] *(S334 — landado em `ed4d1cf`: `.claude/scripts/veto_skill_map.py` DERIVA dos DOIS organogramas; `test_veto_skill_map.py` é lint bidirecional com `test_no_orphans` (:175); nenhum número fixo no check — a derivação produz o conjunto, hoje incluindo `accessibility-and-wcag`.)* `[P0]` **Marcador de VETO machine-readable (cura do r9 #2 —
      pré-requisito do invariante abaixo):** hoje NENHUMA fonte
      machine-readable diz quais skills são VETO — as duas financeiras
      só têm `risk_class`, e o status vive em prosa de roteamento e no
      organograma. Definir o mapeamento AUTORITATIVO no inventário que o
      gerador consome — **não** no frontmatter de cada `SKILL.md`, cuja
      edição é gateada por SP-NNN + soak de 7d e faria a cura esperar
      uma semana — com as entradas DERIVADAS do organograma completo
      (`team.md` E `frontend-team.md`) por comando, nunca enumeradas de
      memória. O r10 provou o porquê: a enumeração "4 core + 2 fintech"
      desta própria unidade já nasceu errada — faltava
      `accessibility-and-wcag` (`frontend-team.md:164`). Lint de
      consistência inventário↔organograma nos DOIS sentidos, para que a
      PRÓXIMA skill de VETO não nasça demovível.
      Check: as entradas do inventario sao GERADAS por derivacao do organograma; o lint falha nos dois sentidos (VETO no organograma ausente do inventario; entrada sem lastro no organograma); nenhum numero fixo de entradas aparece no check — o conjunto e o que a derivacao produzir, e no estado atual ele inclui accessibility-and-wcag
- [x] *(S334 — landado em `ed4d1cf`: eixo `veto_skills` em `skill-budget-generator.py:340,354-362,378` — "TWO protection axes, not one"; `test_no_veto_skill_is_shipped_name_only` em `test_veto_skill_map.py:291`.)* `[P0]` **O invariante mora no GERADOR:** conjunto de exclusão por
      VETO em `skill-budget-generator.py:352-362` mais asserção nos
      testes dele. Hoje o único eixo é `tier`, e o conceito de VETO
      aparece **0 vez** no arquivo.
      Check: teste do gerador falha se uma skill marcada VETO (pelo marcador acima) for demovida, independente do tier
- [x] *(S334 — landado em `ed4d1cf`: log ausente demove NADA; `test_missing_audit_log_fail_soft_zero_counts_exit_zero` em `test_skill_budget_generator.py:189`.)* `[P0]` **Corrigir a direção do fail-soft:** log de auditoria
      ausente hoje demove **tudo** — e adopter novo não tem histórico
      por construção. Falha de infra não pode ter consequência de
      segurança.
      Check: com log ausente, o gerador NAO demove; teste com diretorio de auditoria vazio
- [x] *(S334 — ENTREGUE pelo PLAN-185 W2 em `cc00235`: `_wbm_github_handle_ok` (`_framework_manifest_set.sh:876`), gramática ÚNICA produtor+consumidor; `&`, espaço e aspas RECUSADOS com erro nomeado, e2e F2 em bytes. **EMENDA à perna r8:** o Owner decidiu DEPOIS (PLAN-185 OQ-2, default ratificado) o CONTRÁRIO do Check abaixo quanto a `org/time` — o handle de time é RECUSADO deliberadamente, com mensagem que NOMEIA o caso org/team (e2e F2.1 assere a recusa explicativa). A perna "org/time PASSA" do Check está SUPERSEDIDA por essa decisão posterior; o resto do Check vale e está coberto.)* `[P0]` **Validar o handle do CODEOWNERS na instalação** (achado
      K5 do debate, mantido pelo consenso e ausente da primeira
      redação): a substituição por `sed` não escapa o valor de
      `--github-owner`. Um handle contendo `/` **quebra o install**, e um
      contendo `&` emite entrada malformada — um CODEOWNERS que não
      resolve **não bloqueia nada** e dá falsa sensação de revisão
      obrigatória. Isto é distinto do A6, que era não-defeito.
      **[INVERSAO CORRIGIDA pelo pair-rail r8]** A primeira redação
      mandava rejeitar todo valor com `/` e aceitar `&`. Os dois estão
      ao contrário: `/` é a sintaxe **legítima** de time de organização
      — **este próprio repositório usa `@Canhada-Labs/maintainers`**
      (`.github/CODEOWNERS:26,29,32`) — e rejeitá-la removeria suporte a
      times; já `&` não pode produzir um `@owner` válido e tem de ser
      **rejeitado**. A validação aceita `usuario` OU `org/time`, e
      rejeita o resto.
      Check: install com handle org/time PASSA e produz CODEOWNERS valido; handle com & FALHA com erro nomeado; handle com espaco ou aspas FALHA; controle negativo com handle limpo passa
- [ ] `[P1]` Origem do resíduo: o mapa de 104 overrides é **embarcado**
      no `settings.base.json`, calculado contra o inventário de 166. Ou
      o template deixa de embarcar, ou o install regenera a partir do
      inventário instalado — "podar depois de copiar" contradiz 167/168.
      Check: instalacao com subconjunto de perfis nao escreve override de dominio ausente

### W4 — Timeout de hook (gateada pela W0)

- [ ] Conteúdo definido pelo resultado da W0-US1 e W0-US2. Restrições já
      fixadas: nenhuma instrumentação adiciona lock no caminho quente; e
      serial contra paralelo, per-hook contra per-event, é decidido
      ANTES de desenhar qualquer cura. Orçamento ganha piso nomeado ao
      fechar a W0.
      **→ ESCOPO REESCRITO pela W0-US1 (S317): o A5 NÃO é defeito de
      campo do adopter — é NOSSO.** Dos 71 breaches, **70 vêm do
      repositório do PRÓPRIO framework** e **1** de
      `foxbit-bot-arbitrage`; **ZERO** vêm do repo do adopter. Mecanismo:
      o `/doctor` agrega os transcripts de **todos** os projetos do
      `$HOME`, então o relatório de campo mostrou ao adopter os timeouts
      DESTA máquina. Controle positivo: na mesma janela, o repo do
      adopter tem **5.391** `hook_success` e **0** `hook_cancelled`.
      Consequências para esta wave: (i) o alvo da cura é o teto de 5 s
      dos hooks **deste** repo, não portabilidade de adopter; (ii)
      qualquer critério que só se feche "no adopter" é infechável por
      construção — não há evento lá; (iii) a W4 não depende mais de
      arqueologia do `/doctor` (fonte já identificada, §4), só da
      W0-US2; (iv) a resposta ao campo (AC-7) tem de dizer ao adopter
      que os 71 não são dele.
      Check: none (a unidade nao abre antes da W0 fechar)


## Acceptance criteria

- [ ] AC-1 [P0] **Nenhum caminho de home ou de usuário no ponteiro
      entregue** (asserção explícita, mais forte que "é relativo"), com
      INV-4 intacto.
- [ ] AC-2 [P0] Template de CI ativado sai VERDE num repositório
      **descartável nosso**, com o passo de ativação nomeado.
- [x] AC-3 [P0] Skill de VETO em `name-only` é impossível **por teste do
      gerador** — não por correção no `settings.json`. **FECHADO (S324,
      2026-08-23) — verificado COMPORTAMENTALMENTE, rodando o gerador.**
      Cobre o achado **A4** (a numeração dos ACs não segue a dos achados;
      A3 é o `benchmarks.yml.template`). Landou em `ed4d1cf` (W3):
      `.claude/scripts/veto_skill_map.py` (232 linhas, DERIVA o conjunto
      dos organogramas de autoridade — nenhuma skill enumerada no
      arquivo), `test_veto_skill_map.py` (22 testes), e o gerador ganhou o
      **segundo eixo de proteção**: `skill-budget-generator.py:354-362`
      diz literalmente *"TWO protection axes, not one (PLAN-183 W3 P0).
      `tier` protects core/frontend; `veto_skills` protects VETO-bearing
      skills in ANY tier"*. Medido rodando `--json`:
      `veto_protected` = **18** entradas (inclui
      `financial-correctness-and-math`), e o `skillOverrides` gerado (99
      chaves) **não contém** nenhuma das três skills antes demovidas
      (`financial-correctness-and-math`, `financial-display`,
      `trading-execution` ⇒ todas `None`). O invariante mora no gerador,
      que é o que o AC exige.

      > **⚠️ FOLLOW-UP que este AC NÃO cobre, e que a S324 descobriu ao
      > verificá-lo.** O gerador está curado; o **artefato gerado não**.
      > `.claude/settings.json:872-873` AINDA tem
      > `"financial-correctness-and-math": "name-only"` e
      > `"financial-display": "name-only"` — medido no disco. Causa: a
      > regeneração é passo **MANUAL**
      > (`python3 .claude/scripts/skill-budget-generator.py --jq-fragment`,
      > citado no próprio `_skill_budget_comment` do settings), não está
      > wired em CI, e não foi rodada depois do land da W3. Logo o defeito
      > A4 **segue VIVO neste repositório** apesar do AC estar fechado — e
      > `.claude/settings.json` é **canônico**, então regenerar exige
      > cerimônia. É a classe "gerador curado, artefato obsoleto": o teste
      > do gerador não vigia o arquivo entregue.
      >
      > **Observação MEDIDA E REFUTADA (S324).** Eu suspeitei que duas das
      > 18 entradas de `veto_protected` — `'Kill Switches'` e
      > `'Latency Budgets'` — fossem títulos de prosa vazados. **Não são.**
      > `derive_veto_skills` devolve **27 slugs, zero** com espaço ou
      > maiúscula inicial (medido importando o módulo e chamando a
      > função). As duas são o `name:` de frontmatter de skills REAIS —
      > `domains/trading-hft/skills/kill-switches/` e
      > `latency-budgets/` — cujos DIRETÓRIOS são slugs corretos, e é o
      > `dir_name` que a derivação casa. O gerador então anexa
      > `skill["name"]` (o título humano), não o slug.
      >
      > O que sobra é **legibilidade, não defeito**: `veto_protected`
      > reporta nomes de EXIBIÇÃO enquanto `derive_veto_skills` devolve
      > SLUGS, então as duas listas não são diretamente comparáveis — foi
      > exatamente isso que me fez suspeitar. 14 SKILL.md usam `name:` em
      > prosa, logo é convenção do repositório e não anomalia. Registrado
      > para ninguém re-investigar.
- [x] AC-4 [P0] W0-US1 conclui com veredito nomeado, e a aritmética é
      tentada ANTES da arqueologia. **FECHADO (S317, 2026-08-20):**
      veredito = `explicado pela aritmética`; conta exata
      35+25+7+2+2 = **71**, todos `hook_cancelled` com `timeoutMs=5000`
      e `timedOut=true`; a arqueologia não precisou abrir — a fonte do
      `/doctor` saiu de graça (prompt embutido no binário 2.1.237,
      *"Check 5 - slow hooks"*, dirigido por MODELO).
- [ ] AC-5 [P0] `smoke-install` passa a cobrir `.github/` e a EXECUTAR o
      CI entregue — hoje o grep pelos templates devolve zero.
      — ◕ **REGISTRO S335 (wave-183batch, medido contra o DISCO; rail
      183-r1 barrou o flip — corretamente):** a «metade canônica» que a
      nota ◐ abaixo declarava faltante JÁ EXISTE —
      `.github/workflows/smoke-install.yml:485` invoca
      `bash scripts/tests/smoke-install.sh` por inteiro, e a perna de
      ativação vive em `scripts/tests/smoke-install.sh:180`: o template
      entregue é ATIVADO no target, validado estruturalmente (11 steps
      congelados) e por actionlint quando presente. A nota pré-`738007e`
      («wiring faltante») está superada. **O checkbox NÃO flipa** porque o
      texto do AC exige «EXECUTAR o CI entregue» e a execução REAL do
      workflow ativado segue não feita — é exatamente W0-US3 + OQ-2
      (decisão do Owner); um `[x]` aqui seria registro falso de
      governança. Resta SÓ essa perna.
      — ◐ S334 (nota histórica): entregue a metade NÃO-canônica — `scripts/tests/smoke-install.sh`
      ganhou a perna "PLAN-183 W0-US3 / AC-5" (`826688f`): o template
      entregue é ATIVADO no target descartável (rename do adopter),
      validado estruturalmente por stdlib SEMPRE (name/on/jobs + os 11
      steps congelados) e por `actionlint` quando presente no PATH, com o
      estado entregue restaurado para as pernas seguintes; run local
      completo verde. O premissa "grep pelos templates devolve zero" do
      texto acima descreve o estado pré-S328 e já não vale. FALTA a
      metade CANÔNICA (wiring de step em `.github/workflows/smoke-install.yml`,
      oráculo 1 — entra no batch de cerimônia da W1/W5-b) e a resposta da
      OQ-2 (fixture permanente vs roteiro) para a EXECUÇÃO real do
      workflow ativado — que é também a prova que fecha o AC-2.
- [x] AC-6 [P1] O A7 é curado: instalação limpa não planta a identidade
      do mantenedor no repositório do adopter. **FECHADO (S324,
      2026-08-23) — reconciliado contra o DISCO e contra o CI, não contra
      a memória.** Três pernas: (a) a cura landou em `4f750f0`,
      removendo o hardcode de identidade de
      `.claude/scripts/check_contamination.py` e tirando o módulo de
      `_ALLOWLIST_EXACT` (a auto-exenção era o que deixava a identidade
      passar); (b) o guard unitário existe —
      `.claude/scripts/tests/test_check_contamination.py` (+99 linhas no
      mesmo commit), coletado por-PR em `validate.yml`; (c) o guard de
      instalação entrou em `scripts/tests/smoke-install.sh` (+21 linhas) e
      o step **`Run smoke install` saiu `success`** no run mais recente
      (`32639637945`) — o vermelho daquele run é o step de paridade, outro
      step, outro defeito (D1). Comentário no código não seria prova; o
      step verde é.
- [x] AC-7 [P2, NÃO-BLOQUEANTE] Os achados do relatório de campo são
      respondidos ao adopter, inclusive os recusados (A6), com a razão.
      **Canal e dono:** o CEO escreve a resposta como um documento em
      `.claude/plans/PLAN-183/resposta-ao-campo.md`; a ENTREGA ao adopter
      é do Owner, no canal que ele escolher. **Rebaixado a
      não-bloqueante pelo pair-rail r8:** exigir round-trip com terceiro
      dentro de um AC bloqueante, com `external_wait: nenhum`, tornaria
      o plano infechável se o adopter não responder. Se o mecanismo do
      A6 não for explicado, o documento diz "não explicado" e nomeia o
      arquivo que faltaria.
      **FECHADO (S324, 2026-08-23).** Documento escrito em
      `.claude/plans/PLAN-183/resposta-ao-campo.md`. Responde os **sete**
      achados um a um com veredito e estado, **inclusive o A6 recusado —
      e o mecanismo FOI explicado**, não declarado inexplicado: os dois
      ramos de `install.sh:1493-1515`, com a medição que prova que a fonte
      de entrega é `templates/.github/CODEOWNERS.template` (`1955b01a…`,
      1.442 b) e não o `.github/CODEOWNERS` vivo deste repo (`ba6667d9…`,
      10.259 b) — artefatos distintos. Acrescenta três coisas que o
      relatório não tinha: (a) o **oitavo** item, o mais consequente para
      quem já instalou — o upgrade nunca entrega `.github/` nem `docs/`,
      então as curas de A2/A3 **não chegam por upgrade**, com contorno
      dado; (b) o achado adjacente ao A6 — no ramo sem `--github-owner` os
      11 `{{OWNER_HANDLE}}` ficam crus e `.github/` está fora dos dois
      scanners de placeholder, com dois `grep` de ação para o adopter;
      (c) os dois defeitos GRAVES do installer reproduzidos nesta
      investigação, com a cautela para a próxima reinstalação. A ENTREGA
      segue sendo do Owner, como o AC define.

## Open questions

> **✅ Decisão do Owner em 2026-08-27 (S330, AskUserQuestion, verbatim):
> «182 → done; 183 segue com W1 na fila (Recomendado)».** Este plano
> permanece `executing`. A **W1 — ponteiro portátil e retroativo (AC-1)** é
> a próxima wave DESTE plano no trem, imediatamente DEPOIS da wave OQ-E5 do
> PLAN-169 (ratificada na mesma sessão como próxima cerimônia). AC-2
> (template de CI verde num adopter) e AC-5 (`smoke-install` cobre
> `.github/` e EXECUTA o CI entregue) seguem abertos e nomeados; o
> `stranded` do staleness (>24 h sem commit) é informativo até a W1 tocar
> o plano. A alternativa «183 → abandoned com transferência de AC-1/2/5
> para plano novo» foi apresentada e NÃO escolhida.

1. **W2** — os dois steps de `unittest discover` saem do template ou são
   reescritos para a invocação real do CI? (a rota "preservar atrás de
   guarda" já foi eliminada em §6)
   > ✅ **Respondida POR IMPLEMENTAÇÃO** (`4f750f0`, registrada S334): os dois
   > steps SAÍRAM — eram verde-vácuo (`Ran 0 tests OK` contra árvores nunca
   > embarcadas) — e o template documenta o slot ("Put YOUR OWN test
   > command", :148-156). Não há invocação real possível: o install não
   > embarca testes por decisão do manifesto.
2. **W0-US3** — o repo descartável vira fixture permanente de CI (custo
   recorrente, cobertura real) ou roteiro de release?
3. **W2** — o gate de drift template contra vivo é diff estrutural de
   steps ou declaração congelada com teste? A primeira é mais forte e
   mais cara.
   > ✅ **Respondida na S334: declaração congelada com teste (Ramo B)** —
   > registro e racional no item W2 do vínculo; teste em
   > `.claude/scripts/tests/test_validate_template_frozen_subset.py`.
4. **W5-b** (em `PLAN-183/w5-draft-s323.md`) — quantas linhas novas o
   `ownership_table.tsv` recebe, e qual a regra de legalidade irmã da
   R-04b em `docs/ownership-decision-table.md`? **A rota "ficam FORA da
   tabela" foi RETIRADA da pergunta** (P1 do pair-rail r5): o
   `CLAUDE.md` §4 exige que ownership seja UMA decisão em
   `_ownership_verdict()` com o TSV como verdade, e avisa que *"adding a
   branch that decides ownership locally re-opens the class this
   replaced"* — omitir as duas árvores da tabela seria exatamente esse
   ramo local. Cobertura na tabela é **obrigatória**; o que resta em
   aberto é o dimensionamento. A resposta muda o orçamento da W5-b de ~1
   sessão para 2-4 (§7.2) **e** obriga a re-derivar o total
   `GREEN=62 RED=3` — por isso precisa vir ANTES da unidade de
   ownership, não durante.

   > ## ✅ OQ-4 — RATIFICADA pelo Owner em 2026-08-25 (histórico abaixo: em 2026-08-24 o Owner decidiu MEDIR primeiro; a medição é da S327)
   >
   > A proposta abaixo continua sendo a proposta, mas **não foi ratificada**:
   > o Owner escolheu medir a PISTA do gerador antes de fixar as linhas.
   > A razão está no próprio código — `install.sh:2508-2511` registra que a
   > tentativa anterior desta wave **regrediu 24 células** precisamente por
   > declarar cedo.
   >
   > **O que a medição da S325 já adianta** (`_framework_manifest_set.sh`):
   > `_wbm_is_conditional` (`:320-325`) cobre **apenas 4 paths** —
   > `SPEC/v1`, `SPEC/v1/*`, `PROTOCOL.md`, `.claude/.framework-version` — e
   > `_wbm_declared_hash_source` (`:313-315`) só tem `case` para esses. Logo
   > as 6 rotas de `docs/`/`.github/` hoje caem na pista NÃO-condicional, e
   > seu digest sai de `_wbm_abs` direto (`:393`).
   >
   > **A hipótese a testar** (recomendação do CEO, não decisão): pista
   > MISTA — os 5 paths verbatim ficam na não-condicional, e só
   > `.github/CODEOWNERS` entra na condicional, porque só ele é RENDERIZADO
   > e tem ownership genuinamente ambígua. Se confirmada, a OQ-4 encolhe de
   > ~13 linhas para ~2-3. **O experimento tem de rodar em árvore-sombra com
   > o e2e de ownership nas duas pistas, e comparar o id-set exato contra
   > `ownership-expected-reds.txt`** — o gate que falha em QUALQUER diferença
   > é o instrumento que pega uma regressão de 24 células.
   >
   > Até esse veredito, **nenhuma linha do TSV de ownership se escreve.**
   >
   > **MEDIDA na S327 (2026-08-24, night-run autônoma; `PLAN-183/w5-oq4-measurement-S327.md`):** braços A/B/C em clones separados; A registra 0/5 rotas no manifesto (D3 latente-por-não-entrada, confirmado), B e C registram 5/5 com manifestos byte-idênticos no install fresco; ownership e2e com RED set exato nos três; paridade idêntica; custo de C sobre B = +22 linhas de código, **0 linhas de TSV** (a moldura "2-3 linhas" estava errada). Recomendação do CEO: pista MISTA (braço C) — única que registra o `CODEOWNERS` renderizado na continuidade do upgrade. **Veredito = assinatura do Owner em `PLAN-183/wave-w5-approved.md` (pacote `w5-ceremony/`).**
   >
   > **W5 LANDADA em `6304f66` (2026-08-25 08:55, assinatura GPG do Owner sobre `wave-w5-approved.md`; `OWNER-S327-LAND.sh` V1–V6 verdes, V7 diferido ao nightly).** D1 e D3 curados no `main`; paridade maintainer `STALE 0` no próprio land; OQ-4 ratificada pela assinatura como pista MISTA com 0 linhas no TSV de ownership. Residual: o status textual do ADR-194 continua `PROPOSED` (arquivo canônico; o flip para `ACCEPTED` entra na próxima cerimônia). O primeiro land abortou no V4 por defeito do LAND (comparava contra zero uma suíte 33/1 por desenho) — curado em `ca0297c` antes da re-assinatura.
   >
   > **✅ RATIFICADA pelo Owner em 2026-08-25 (S328, AskUserQuestion, verbatim): «Pista MISTA — braço C (Recomendado)».** Retroativa: o braço C já é o conteúdo do patch landado em `6304f66` (`PLAN-183/w5-ceremony/PROPOSED-PATCH.md` — "pista MISTA (braço C), que é o conteúdo deste patch"; `_wbm_declared_hash_source` vivo em `scripts/_framework_manifest_set.sh`; `armC.diff` da medição não aplica mais — absorvido). A decisão inclui o flip deste plano `reviewed → executing` (frontmatter, `executing_at: 2026-08-25`). O que resta da W5-b é FECHAMENTO, não implementação: flip textual do ADR-194 para `ACCEPTED` com a seção de ratificação (arquivo canônico — pacote de cerimônia S328-A) e as obrigações residuais já nomeadas em `w5-draft-s323.md` / `w5-oq4-measurement-S327.md` §7 (@815 preservar + fixture pré-install-state-com-owner; @1579 chave do resolvedor tolerando os dois destinos sem o manifesto reivindicar ambos; §9.4 F4 `.github/` fora dos DOIS scanners de placeholder; @733 promoção da tabela; @1009 teste de `--github-owner` que PLANTA divergência — compartilhado com PLAN-185 W2, feito UMA vez aqui). Regra que a ratificação FIXA: a posse das duas árvores é o hash-gate da entrega + `hash_source` do `.github/CODEOWNERS`, **não** superfície nova em `_ownership_verdict()` — qualquer extensão é wave própria, com OQ própria.

   **PROPOSTA DERIVADA (S324), NÃO RATIFICADA — mantida como hipótese:** Medido no disco por mim
   (`scripts/tests/ownership_table.tsv`): **15 colunas, 65 linhas de
   dados** — `spec` 29, `protocol` 13, `marker` 23. As colunas de
   dimensão são `prior_record, live_type, live_content, source_has, mode,
   ceremony, operation, skip_requested, fault`; `spec` e `marker` variam
   nas **9**, `protocol` em **5**. `_ownership_verdict` ramifica em
   `surface` em **7 pontos**, logo uma superfície nova exige ramo dentro
   da MESMA função (§4 do `CLAUDE.md`).

   Conta, com os fatores explícitos:

   | cenário | linhas novas |
   |---|---|
   | piso — 1 superfície, perfil `protocol` (5 dims) | ~13 |
   | realista — 1 superfície, perfil `marker`/`spec` (9 dims) | ~23–29 |
   | `docs/` e `.github/` como superfícies SEPARADAS | ~26–58 |

   **Dois fatores REDUZEM a conta, e os dois são medidos:**
   (i) `ceremony=user` já é decidido em bloco (`:540`), o que casa
   exactamente com a guarda `CEREMONY != user` de `install.sh:1484/:1525`
   e elimina metade das combinações de `ceremony`;
   (ii) **`mode` (copy/link) é INERTE para estas rotas** —
   `install_docs_template:1472` faz `cp` incondicional sem consultar
   `$MODE`, e a medição confirma que os 5 destinos saem `REGFILE` mesmo
   com `--link` (§9.7 item 3), então `mode` pode ser `*`.
   E `expect_verdict`/`expect_hash_source` **reutilizam os enums
   existentes** — nenhum valor novo.

   **Recomendação do CEO: UMA superfície nova (`template_delivered`), com
   perfil de variação de `protocol` (5 dims) e `mode=*`** ⇒ ~13 linhas.
   Razão: as duas árvores compartilham a guarda de cerimônia, o
   skip-if-exists e a inércia de `mode`; o que as distingue é a
   TRANSFORMAÇÃO, e transformação é metadado de ROTA (§8.5.2 peça (b)),
   não dimensão de ownership. Separá-las em duas superfícies duplicaria
   linhas para codificar uma diferença que pertence a outra tabela.
   Fica registrado o custo se o Owner discordar: até ~58 linhas e o
   orçamento da W5-b sobe de ~1 para 2–4 sessões (§7.2).

5. **W5-b, BLOQUEANTE (§8.7)** — adopters históricos não têm registro de
   entrega e nenhum hash o recupera. Rota (i) não migrar, (ii) migrar com
   hash-gate assumindo o risco de colisão, ou (iii) exigir ato explícito
   do adopter? **Decisão do Owner.** A W5-b não abre antes disso, e a
   resposta determina se a cura de D1 é suficiente para deixar o main
   verde pela rota B do e2e.

   **RESPONDIDA — 2026-08-23 (S324), Owner. Opção selecionada:
   `(ii) Migrar com hash-gate`.** Texto da opção, verbatim:

   > Refresh gated contra as gerações conhecidas derivadas do histórico
   > git. É a ÚNICA rota que fecha o main. Risco declarado: um adopter
   > cujo arquivo seja byte-idêntico a uma geração antiga sem tê-la
   > recebido teria o arquivo tomado, e o `uninstall.sh` remove por hash.
   > Meu raciocínio: para `.github/**/*.template` a colisão é
   > praticamente impossível — são artefatos só-framework sem análogo de
   > adopter, então bytes idênticos são prova de origem; derivar as
   > gerações do git limita o conjunto de colisão aos bytes passados do
   > próprio framework.

   Consequências vinculantes para a W5-b:
   - O item `[P0]` de adopters históricos **desbloqueia** — a rota é (ii).
   - O item `[P0]` de paridade `maintainer` deixa de ser condicional:
     sob a rota (ii) a expectativa é **exit 0**, não "divergência
     esperada".
   - O e2e cobre os TRÊS casos do Check original (pristine de geração
     conhecida, modificado, e a COLISÃO) — a colisão passa a ser
     **risco declarado e testado**, não impedimento.
   - O ADR da W5-b registra a rota (ii) e o risco de tomada como
     decisão consciente, com o argumento de prova-de-origem para
     `.github/**/*.template` explicitado.

> **Itens 5–11 registrados na S328 (2026-08-25)** pela re-derivação
> read-only das obrigações residuais da W5-b (workflow `wf_b2e30e3d`:
> 2 leitores sobre fontes disjuntas + redutor; toda afirmação abaixo
> cita path:line verificado no HEAD `560dad0`). **Nenhum tem resposta
> na noite** (runbook §2.2 — o CEO não decide no lugar do Owner). A
> W5-b fecha o que é MECÂNICO — H.27 com divergência plantada em
> `test-upgrade-historical-adopter.sh`; confinamento nos 2 sítios de
> hash do `doctor.sh`; discriminante line-exact da continuidade em
> `install.sh` (canônico, pacote S328-A); bookkeeping das 20 checkboxes
> abertas do rascunho — e deixa estes SETE para a manhã. Provados
> ENTREGUES e retirados da lista: @815 (`upgrade.sh:4457` +
> `test-upgrade-historical-adopter.sh:691-730`, H.12/b/c/d/e), @733
> (`_framework_manifest_set.sh:463` `_WBM_ROUTES_TSV` + leitores) e
> §9.8 (`if: always()` em 7 steps do `smoke-install.yml`).

5. **W5-b / `uninstall.sh` com `docs/` + `.github/` no manifesto (§9.8
   P0)** — a expectativa da perna (b) do plano está FALSIFICADA pela W5:
   o manifesto registra o digest RENDERIZADO
   (`test_install_baseline_manifest.sh:557-563`), logo a comparação de
   SHA do `uninstall.sh` CASA e APAGA — o plano esperava `PRESERVED`. E
   `uninstall.sh:273` varre diretórios vazios SÓ sob `$TARGET/.claude`,
   então a perna `docs/`/`.github/` está descoberta por construção.
   **Pergunta:** o uninstall APAGA um `.github/CODEOWNERS` renderizado
   (entregue pelo framework, registrado exatamente) ou o PRESERVA como
   configuração do adopter? Estimativa após a decisão: ~180 linhas.
6. **§9.4 F4 — `.github/` fora dos DOIS scanners de placeholder**
   (`install.sh:2265-2281` `explicit_files`; `:2363-2374` `scan_roots`;
   e o walk filtra `-name '*.md' -o -name '*.py'` em `:2385`, então
   incluir a raiz SOZINHA ainda não veria `CODEOWNERS.template`).
   Medido: 11 `{{OWNER_HANDLE}}` viajam sem render via
   `install.sh:1647-1654` quando não há handle. **Pergunta:** um
   `*.template` entregue CARREGANDO placeholders é defeito a sinalizar,
   ou é o contrato pretendido "o adopter preenche" (o ramo `else` é
   tomado exatamente porque nenhum handle foi dado)? A disposição do
   próprio plano atribui F4 à W2, não à W5.
7. **§9.3 / @1582 — o par install-side.** Verificado aberto:
   `install.sh:1618` renderiza `.github/CODEOWNERS` só com o skip
   `[[ -e $dst ]]` e nunca procura um `.template` existente;
   `:1647-1654` copia o `.template` sem checar um renderizado existente;
   nenhum remove o outro; nenhum teste roda o install duas vezes;
   `upgrade.sh:4447-4450` DECLINA explicitamente reproduzir a cura.
   **Pergunta:** o install REMOVE o arquivo superado, ou deixa o par e
   apenas se recusa a REIVINDICAR os dois (under-claim,
   ADR-155-AMEND-1)? Estimativa após a decisão: 45-70 linhas.
8. **§7 residual (a) — `_register_delivered_template` recebe o relpath
   da FONTE como LITERAL por call-site** (`install.sh:1573`; call-sites
   `:1594-1597`, `:1650-1653`, `:1656-1667`) — um segundo lugar onde o
   par destino→fonte é declarado. A mitigação é real:
   `test-manifest-delivery-route.sh:247-256` (S.2b) cruza os argumentos
   com os call-sites de `install_docs_template`. **Pergunta:** colapsar
   para UM argumento resolvido via `_wbm_route_src` (o `install.sh`
   vira 4º consumidor do TSV, fail-CLOSED sem a tabela — alarga um
   arquivo CANÔNICO, exige cerimônia) ou manter o literal + o cruzamento
   mecânico? Estimativa: 35-45 linhas.
9. **`_parity_classify.py` resolve a rota RENDERIZADA para `None`** —
   o gate de paridade nunca classifica `.github/CODEOWNERS`, exatamente
   o destino pelo qual a pista MISTA (braço C) foi escolhida; o próprio
   arquivo nomeia isso como item da W5-b em
   `scripts/tests/_parity_classify.py:326-327`. **Pergunta:** um harness
   de TESTE pode ler o `.claude/.install-state.json` NÃO-ASSINADO do
   lado do adopter? A H.7 de `test-upgrade-historical-adopter.sh` trata
   um `github_owner` com `/` ali como entrada HOSTIL. Se sim: mesma
   validação de `upgrade.sh:3696-3702` + controle de que o handle do
   mantenedor nunca vaza para a saída. Estimativa: ~55 linhas.
10. **§9.6 F9 (ÓRFÃO)** — `install.sh` cita `docs/deny-baseline.md` 9
    vezes (medido: `grep -c` = 9), inclusive em mensagens de recuperação
    de erro, e nunca o entrega (`ls templates/docs/` =
    `BRANCH-PROTECTION.md`, `rotation-log.md`). A disposição diz "W2",
    mas a W2 landou (`4f750f0`/`ed4d1cf`) sem curá-lo e a lista de
    ratificação da S328 não o nomeia — hoje não pertence a wave aberta
    nenhuma. **Pergunta:** entregar `templates/docs/deny-baseline.md`
    (7ª rota + linha no TSV de rotas + entrada no manifesto) ou
    reescrever as 9 mensagens para não citarem um doc que o adopter
    nunca recebe? Estimativa: ~40 linhas.
11. **STALE ×2 do `SPEC/`** — o material ASSINADO
    (`PLAN-183/w5-ceremony/PROPOSED-PATCH.md:101`) registra que estender
    a emenda da OQ-5 ao `SPEC/` é "decisão do Owner, fora deste patch";
    os dois paths STALE são `SPEC/v1/audit-log.schema.md` e
    `SPEC/v1/state-stores.schema.md`. Precisa de disposição (fazer
    agora, ou registrar como W5-c) ANTES de a W5-b ser declarada
    fechada. (A W5-c em si — superfície `template` com linhas de 9
    dimensões em `ownership_table.tsv` — já está ratificada como wave
    própria em `PROPOSED-PATCH.md:89` e deliberadamente NÃO é obrigação
    da W5-b.)

## Reference links

- `.claude/plans/PLAN-183/debate/round-1/consensus.md` — round 1,
  veredito **PROCEED**, 28 ajustes, dos quais este documento incorpora
  os que mudam conteúdo.
- `.github/workflows/smoke-install.yml:276` — o instrumento de adopter
  que já existe, e o ponto exato onde a W0-US3 se enxerta.
- `.claude/plans/PLAN-167-ownership-decision-table.md` e
  `PLAN-168-ownership-followups-closure.md` — INV-4 e a bateria que a W1
  não pode regredir.

## 9. Achados REPRODUZIDOS fora do escopo da W5 (censo mecânico, S324)

O censo de rotas de entrega da S324 rodou **installs reais** em targets
`/tmp` (não leitura estática) e reproduziu defeitos que **não são** da
classe de resolução-de-fonte. Ficam registrados porque foram
reproduzidos e não devem ser perdidos — **nenhum entra na W5**, que segue
sendo só D1/D2/D3/D4. Disposição declarada por achado.

### 9.1 F1 — escrita FORA do `$TARGET` via symlink pendente (GRAVE)

`install_docs_template` guarda o destino com `[[ -e "$dst" ]]`
(`install.sh:1466-1472`). O teste `-e` **segue** symlink: um link
**pendente** faz `-e` dar falso, e o `cp` seguinte escreve **através** do
link, fora da árvore do target.

Reprodução: plantar um symlink pendente de `docs/rotation-log.md` para
`/tmp/<dir>/pwned.md` num target limpo e rodar o install em modo
`maintainer` → `exit 0`, log `COPIED:`, arquivo fora do target escrito.

A defesa **já existe no mesmo arquivo** para outra árvore
(`install.sh:2139-2159`) e está ausente aqui. Superfície canônica ⇒ exige
cerimônia.
**Disposição: plano próprio, classe segurança.** Misturar com a W5
alargaria uma cerimônia L3+ já grande.

### 9.2 F2 — `--github-owner` com `/` aborta e deixa CODEOWNERS de 0 bytes (GRAVE)

O `sed` de `install.sh:1508` interpola o valor da flag **sem escapar o
delimitador**. Reprodução: um valor contendo `/` → `exit 1`,
`sed: bad flag in substitute command`, e o destino com **0 bytes**. O
arquivo vazio sobrevive e passa a ser **EXISTS-skipped para sempre**
(`:1504`) — nenhum install ou upgrade posterior o corrige.
**Disposição: mesmo plano de segurança que F1** (mesma função, mesma
cerimônia).

### 9.3 F3 — os dois ramos do CODEOWNERS não são exclusivos no TEMPO

Os ramos gravam em **paths diferentes** e nenhum limpa o outro: instalar
sem a flag e depois com ela deixa **os dois** no disco (`:1497` vs
`:1514`).
**Disposição: item da W5-b** — a chave do resolvedor tem de tolerar os
dois destinos coexistindo, e o manifesto não pode reivindicar os dois
como framework-owned.

### 9.4 F4 — `.github/` está fora dos DOIS scanners de placeholder

Os 11 `{{OWNER_HANDLE}}` entregues pelo ramo sem flag **nunca** são
substituídos, e `.github/` não entra em `explicit_files`
(`install.sh:2126-2135`) — nem o gate `--strict-placeholders` nem o aviso
de fim de install olham para lá.
**Disposição: candidato à W2 deste plano**, não à W5.

### 9.5 F7 — o early-return de `apply_placeholder_substitutions` é MORTO

O ramo `if [[ -z "$sed_script" ]]` (`:2096-2101`) é inalcançável:
`:651-670` dá default **determinístico** a quatro `PH_*`, então
`build_sed_script` nunca devolve vazio. Logo **o estágio 2 SEMPRE roda** e
os dois docs são sempre reescritos in-place com troca de inode.
**Disposição: entra na W5 como FATO DE DESENHO** (§9.7), não como
correção.

### 9.6 F9 — `install.sh` aponta 9 vezes para um doc que nunca entrega

`grep -c 'docs/deny-baseline\.md' scripts/install.sh` = **9**, inclusive
em mensagens de **ERRO de recuperação**. O arquivo não existe em
`templates/docs/` e nunca é entregue: um adopter em falha é mandado ler um
arquivo que ele não tem.
**Disposição: W2 deste plano** — é a classe "instrução que não viaja para
o adopter" que a W2 existe para fechar.

### 9.7 O que DISSO muda a W5 (e só isso)

1. **A rota de `docs/` é de DOIS ESTÁGIOS** — `cp` cru (`:1472`) **mais**
   reescrita in-place (`:2130`/`:2131` via `:2165`). Todo hash de baseline
   de `docs/*` tem de sair do arquivo **PÓS-substituição**, nunca do
   template. Hoje os dois coincidem **por acidente** (os dois templates
   têm **zero** marcadores `{{...}}`, medido), não por desenho: um
   marcador novo em qualquer deles quebraria em silêncio um baseline
   derivado do template.
2. **As 5 rotas entregam ZERO registro de baseline.** Medido:
   `_framework_target_entries` (`_framework_manifest_set.sh:113-190`)
   enumera zero paths dessas árvores, e o manifesto entregue tem
   **541 linhas com 0 entradas** delas. Confirmação independente de
   D1/D3 pelo lado do produto entregue.
3. **Modo `--link` não se aplica:** `install_docs_template` faz `cp`
   incondicional (`:1472`) sem consultar `$MODE` — os 5 destinos são
   sempre REGFILE. A dimensão "link" da tabela de ownership é **vacuosa**
   para essas árvores, o que **reduz** a conta da OQ-4.
4. **O registro de estado de `.github/` é vazio** (`:1491` grava `detail`
   vazio; `docs/` grava string fixa em `:1479`). Confirma por medição que
   `_state_record_op` é breadcrumb, não fonte de verdade de ownership.

### 9.8 O controle positivo da paridade é SKIPPED exatamente quando importa

Observação do log do run `32639637945`, e ela é sobre o INSTRUMENTO, não
sobre o defeito. A sequência de steps do `smoke-install.yml` é:

```
failure   Install/upgrade parity e2e (maintainer + user ceremony)
skipped   Install/upgrade parity - positive control (planted divergence)
skipped   Upgrade SPEC/marker delivery-record ownership (S1-S8)
skipped   night-mode ignore efficacy (...)
```

O controle positivo — o step que responde *"o instrumento ainda DETECTA
divergência plantada?"* — só roda quando a asserção principal passa. Ou
seja: enquanto o main está vermelho por D1, **perdemos justamente o sinal
que diria se o classificador continua tendo poder de detecção**. Um verde
futuro do step principal, sem nunca ter reexecutado o controle, é
exatamente a classe *instrumento verde cuja PERGUNTA envelheceu*.

⇒ Item para a W5: o controle positivo tem de rodar **independentemente**
do veredito do step principal (`if: always()` ou step próprio), senão a
cura de D1 vai ser validada por um instrumento cujo poder de detecção não
foi verificado no mesmo run. Vale também para os outros dois steps
skipped, que testam ownership de entrega — exatamente a área que a W5-b
mexe.

- [x] *(S334 — ENTREGUE: `if: always()` nos TRÊS steps nomeados — paridade positive-control `smoke-install.yml:553`, delivery-record ownership `:593`, night-mode efficacy `:611` (o próprio step cita "§9.8: third of the three steps"); 17 ocorrências de `if: always()` no arquivo. Implementação canônica landou nas waves W5/W5-b assinadas — a nota CHECKBOX≠IMPLEMENTAÇÃO abaixo descreve o estado pré-S328 e fica como histórico.)* `[P0]` O controle positivo da paridade roda **independentemente** do
      veredito do step principal (`if: always()`), e o mesmo para os outros
      dois steps skipped (delivery-record ownership, night-mode).
      Check: num run com o step principal VERMELHO, o controle positivo sai
      `success` ou `failure` — **nunca `skipped`**. Um run em que ele saia
      `skipped` reprova o Check, mesmo que todo o resto esteja verde.

> **CHECKBOX ≠ IMPLEMENTAÇÃO (registrado na S325).** A checkbox acima é
> texto de plano e landa sem cerimônia. A implementação vive em
> `.github/workflows/smoke-install.yml`, que o oráculo classifica como
> **CANÔNICO (=1)** ⇒ exige sentinel + assinatura GPG do Owner. É item de
> CERIMÔNIA da W5-b e não foi tocado.

- [ ] `[P0]` `uninstall.sh` exercitado com as duas árvores no manifesto
      (convergência **C4** do debate: a wave AMPLIA o alcance de um
      consumidor DESTRUTIVO que hoje nenhum Check toca). Três pernas:
      (a) install → uninstall ⇒ `docs/` e `.github/` removidos e **nenhum
      path fora do `$TARGET`** tocado; (b) com `--github-owner`,
      `.github/CODEOWNERS` sai **PRESERVED** (o renderizado nunca casa o sha
      do template) e o exit avisa em vez de apagar; (c) dirs vazios de
      `docs/`/`.github/` — decidir e ASSERTAR, porque a varredura de
      `uninstall.sh:272` (`find "$TARGET/.claude" -depth -type d -empty
      -delete`) cobre **só** `.claude/`.
      Oráculo: `scripts/uninstall.sh` = **0** ⇒ pode landar sem cerimônia.
