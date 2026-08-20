---
id: PLAN-183
title: Adopter fitness — o instrumento de adopter existe, mas seu escopo exclui .github/ e ele nunca executa o CI entregue
status: reviewed
reviewed_at: 2026-08-20
reviewed_by: "Owner — autorizacao explicita em chat (S315, 2026-08-20): 'se ja esta pronto deixa como revisado e apto pra fazer'. Debate L3 round 1 fechado com veredito PROCEED (10 consensos, 28 ajustes) e ajustes incorporados ao corpo; validate_governance_fast = 0 findings; pair-rail codex 6 rodadas fechadas, 32 achados, todos curados."
created: 2026-08-20
owner: CEO
depends_on: [PLAN-167, PLAN-168]
budget_tokens: 170-360k (W0 60-110k; W1 50-110k incl. re-baseline de ownership; W2 40-90k; W3 20-40k; W4 piso nomeado ao fechar a W0)
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
  re-baseline (~25 min por iteração) é orçado dentro da W1.
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
- [ ] `[P0][US2]` Medir a **taxa de censura à direita**: invocações
      esperadas contra linhas de evento emitidas, por hook. Estender a
      forma que JÁ existe (`check_name` e `timeout_ms`), nunca criar
      paralela. Pré-condição: verificar se o drain do spool varre PID
      morto.
      Check: a taxa de censura é um número publicado no plano, por hook, com o método ao lado
- [ ] `[P0][US3]` **Estender** `smoke-install.sh` e
      `smoke-install.yml` (o step `:276` já existe) para cobrir
      `.github/` e para ATIVAR e EXECUTAR o CI entregue. Nunca uma
      bateria paralela.
      Check: smoke-install passa a referenciar validate.yml.template; hoje o grep devolve ZERO — o teste é essa referência existir e o step rodar
- [ ] `[P1][US4]` Inventariar quais dos cinco artefatos de ownership a
      W1 vai tocar, e orçar o ciclo de re-baseline em tokens e sessões.
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
- [ ] `[P0]` **Remediação retroativa:** reconhecedor de "absoluto
      legado" no molde de `_protocol_pointer_is_degraded`
      (`_framework_manifest_set.sh:736-742`), com re-render byte-a-byte,
      falha **para preservação**, e backup em `$BAK_DIR`.
      Check: e2e — instalação feita com a versão ANTERIOR, ao rodar upgrade.sh, termina com ponteiro relativo
- [ ] `[P0]` Usar a interface que **já existe**: `--protocol-source` e
      `CEO_PROTOCOL_SOURCE` (`install.sh:409,522,663-668`), reusada pelo
      upgrade via install-state. Não introduzir env nova.
      Check: CEO_ORCHESTRATION_DIR nao aparece no gerador nem no plano; --protocol-source e o unico escape citado
- [ ] `[P0]` O corpo renderizado passa a **nomear** a interface — hoje
      ele manda "editar" sem dizer que existe flag para isso.
      Check: o ponteiro renderizado contem a string --protocol-source
- [ ] `[P1]` Preservação silenciosa vira **preservação AVISADA**:
      WARNING quando um ponteiro preservado contém caminho absoluto.
      Check: e2e com ponteiro absoluto editado pelo adopter — a edição sobrevive E o WARNING aparece
- [ ] `[P0]` Preservar INV-4 — a cura não pode reabrir o que os
      PLAN-167/168 fecharam.
      Check: scripts/tests/test-protocol-pointer-inv4.sh verde

### W2 — CI que passa no adopter (A2/A3/A7)

- [ ] `[P0]` **Vínculo template contra vivo, antes de qualquer patch.**
      Hoje o vivo tem 71 steps e 79.993 bytes (`runs-on: Ceo`, timeout
      25, checkout SHA-pinado) e o template tem 14 steps e 226 linhas
      (`ubuntu-latest`, timeout 5, `checkout@v4` sem pin) — e **nada
      regenera ou diffa um contra o outro**. É a única superfície de
      governança sem gate de drift. Gate de drift OU declaração escrita
      de "subconjunto mínimo congelado", com o teste que a executa.
      Check: a wave escolhe UM ramo na abertura e registra qual. Ramo A (gate de drift) — existe gate que falha quando o vivo ganha step fora da allowlist de divergencia. Ramo B (subconjunto congelado) — existe teste que falha se o template divergir do subconjunto declarado, e a declaracao nomeia cada step congelado. [pair-rail r8: o Check anterior exigia o ramo A e tornava o ramo B inexecutavel]
- [ ] `[P0]` **Re-derivar o censo step a step**, com mecanismo nomeado
      por step. Mínimo a cobrir: `:108-109` (PyYAML — dependência de
      terceiro, contra o stdlib-only do `CLAUDE.md` §3), `:148,158`
      (`unittest discover` — falso-vermelho por conftest pytest-only),
      `:176-177` (actionlint baixado de `main` **sem pin**, gradando os
      workflows do próprio adopter), `:77` (remediação aponta arquivo
      que o adopter não tem), `:22-23` (timeout 5 contra 25), `:27`
      (checkout sem pin).
      Check: tabela step para mecanismo para disposicao cobrindo os 14 steps; nenhum step fica sem veredito
- [ ] `[P0]` **`Contamination check`: manter "ele estava CERTO"** quanto
      ao gatilho do A1, **e** curar o A7 — o padrão embarca a identidade
      do mantenedor, o arquivo é entregue ao adopter, e ele se
      auto-isenta. Cura = padrão **configurável na instalação**.
      Check: instalacao limpa produz um guard cujo padrao NAO contem o nome do mantenedor; controle negativo com o nome plantado dispara
- [ ] `[P0]` Após a W1, re-rodar o `Contamination check` no adopter:
      espera-se VERDE **sem tocar a allowlist**. Se exigir mudança de
      allowlist, PARAR — mexer nela esconderia a contaminação.
      Check: o step sai verde e o diff da allowlist e vazio
- [ ] `[P0]` `benchmarks.yml.template`: ou o `install.sh` entrega
      `.github/scripts/`, ou a referência sai. Cabeçalho declara a
      variável de API key exigida e o custo em dinheiro do adopter.
      Check: instalacao limpa nao deixa referencia a script ausente
- [ ] `[P1]` Template recebe kill-switch de job espelhando o vivo
      (16 ocorrências no vivo contra 0 no template).
      Check: actionlint limpo e o if presente no nivel de job
- [ ] `[P1]` Nomear que o install entrega `.template` (**inerte**) e que
      o CI só existe após rename — o passo de ativação vira explícito.
      Check: AC-2 nomeia o passo de ativacao; prova em repo descartavel nosso

### W3 — Catálogo e a regra de VETO (A4)

- [ ] `[P0]` **Marcador de VETO machine-readable (cura do r9 #2 —
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
- [ ] `[P0]` **O invariante mora no GERADOR:** conjunto de exclusão por
      VETO em `skill-budget-generator.py:352-362` mais asserção nos
      testes dele. Hoje o único eixo é `tier`, e o conceito de VETO
      aparece **0 vez** no arquivo.
      Check: teste do gerador falha se uma skill marcada VETO (pelo marcador acima) for demovida, independente do tier
- [ ] `[P0]` **Corrigir a direção do fail-soft:** log de auditoria
      ausente hoje demove **tudo** — e adopter novo não tem histórico
      por construção. Falha de infra não pode ter consequência de
      segurança.
      Check: com log ausente, o gerador NAO demove; teste com diretorio de auditoria vazio
- [ ] `[P0]` **Validar o handle do CODEOWNERS na instalação** (achado
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
- [ ] AC-3 [P0] Skill de VETO em `name-only` é impossível **por teste do
      gerador** — não por correção no `settings.json`.
- [x] AC-4 [P0] W0-US1 conclui com veredito nomeado, e a aritmética é
      tentada ANTES da arqueologia. **FECHADO (S317, 2026-08-20):**
      veredito = `explicado pela aritmética`; conta exata
      35+25+7+2+2 = **71**, todos `hook_cancelled` com `timeoutMs=5000`
      e `timedOut=true`; a arqueologia não precisou abrir — a fonte do
      `/doctor` saiu de graça (prompt embutido no binário 2.1.237,
      *"Check 5 - slow hooks"*, dirigido por MODELO).
- [ ] AC-5 [P0] `smoke-install` passa a cobrir `.github/` e a EXECUTAR o
      CI entregue — hoje o grep pelos templates devolve zero.
- [ ] AC-6 [P1] O A7 é curado: instalação limpa não planta a identidade
      do mantenedor no repositório do adopter.
- [ ] AC-7 [P2, NÃO-BLOQUEANTE] Os achados do relatório de campo são
      respondidos ao adopter, inclusive os recusados (A6), com a razão.
      **Canal e dono:** o CEO escreve a resposta como um documento em
      `.claude/plans/PLAN-183/resposta-ao-campo.md`; a ENTREGA ao adopter
      é do Owner, no canal que ele escolher. **Rebaixado a
      não-bloqueante pelo pair-rail r8:** exigir round-trip com terceiro
      dentro de um AC bloqueante, com `external_wait: nenhum`, tornaria
      o plano infechável se o adopter não responder. Se o mecanismo do
      A6 não for explicado, o documento diz "não explicado" e nomeia o
      arquivo que faltaria.

## Open questions

1. **W2** — os dois steps de `unittest discover` saem do template ou são
   reescritos para a invocação real do CI? (a rota "preservar atrás de
   guarda" já foi eliminada em §6)
2. **W0-US3** — o repo descartável vira fixture permanente de CI (custo
   recorrente, cobertura real) ou roteiro de release?
3. **W2** — o gate de drift template contra vivo é diff estrutural de
   steps ou declaração congelada com teste? A primeira é mais forte e
   mais cara.

## Reference links

- `.claude/plans/PLAN-183/debate/round-1/consensus.md` — round 1,
  veredito **PROCEED**, 28 ajustes, dos quais este documento incorpora
  os que mudam conteúdo.
- `.github/workflows/smoke-install.yml:276` — o instrumento de adopter
  que já existe, e o ponto exato onde a W0-US3 se enxerta.
- `.claude/plans/PLAN-167-ownership-decision-table.md` e
  `PLAN-168-ownership-followups-closure.md` — INV-4 e a bateria que a W1
  não pode regredir.
