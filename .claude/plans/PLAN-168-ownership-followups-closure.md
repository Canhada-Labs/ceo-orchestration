---
id: PLAN-168
title: Fechamento dos follow-ups do PLAN-167 — CI que não roda, ponteiro que degrada, contrato sem ADR
status: reviewed
created: 2026-08-07
reviewed_at: 2026-08-07
owner: CEO
depends_on: [PLAN-167]
budget_tokens: 120-180k
budget_sessions: 1
context_risk: medium
external_wait: assinatura GPG do Owner para o W1 (workflows são superfície canônica)
tags: [ci, install, upgrade, adr, testing, canonical]
---

# PLAN-168 — fechamento dos follow-ups do PLAN-167

> **Origem.** O PLAN-167 landou em `7c0828a` (assinado, pushado). Três coisas
> ficaram deliberadamente FORA daquele Scope, e cada uma tem causa nomeada e
> evidência já produzida. Este plano não descobre nada novo: ele **fecha o que
> já foi diagnosticado**.

## 0. O que já está provado (não re-investigar)

| Item | Evidência existente |
|---|---|
| CI não dispara os oráculos | `grep -c` = 0 para os **4** paths novos em `smoke-install.yml` (o `_hash_lib.sh` JÁ está lá, `:15`/`:54`); codex rail r1/r2/r4 |
| `fetch-depth: 1` não traz tags | `smoke-install.yml:101`; o harness precisa de `v1.2.0` para as linhas `legacy_pristine*` |
| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — install=0 ocorrências literais, upgrade=4 |
| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
| **`OWN-0074` é PRODUTO, não teste** | debate r1 QA must-fix 1, verificado: registro=`hash(corpo com {{PROTOCOL_SOURCE}} literal)`, disco=`hash(corpo substituído)` ⇒ é a INV-4 no digest. **A classificação anterior ("2 são defeito do teste") estava ERRADA** e está corrigida aqui, na memória e no CLAUDE.md. |

**Anti-objetivo:** não mexer na tabela de decisão nem nos vereditos. O
PLAN-167 fechou aquilo com 58/62 e rail de 4 rodadas. Aqui só se fecha o
entorno.

## 1. O problema, em uma frase cada

**W1 — teste que não roda apodrece.** Os dois oráculos do PLAN-167
(`test-ownership-verdict-unit.sh`, `test-ownership-table.sh`) não estão em
nenhum path filter. Um PR que altere a tabela ou o harness **pula o gate
inteiro**. É literalmente a classe do achado r10-F4 — um teste
cuja única execução em CI era pulada — reaparecendo no trabalho que a
consertou.

**W2 — todo upgrade quebra o ponteiro raiz.** `install.sh` escreve
`PROTOCOL.md` e **substitui** os placeholders; `upgrade.sh` regenera do
heredoc e deixa `{{PROTOCOL_SOURCE}}` **literal**. Qualquer adotante cujo
checkout esteja fora do target fica com um arquivo que não diz mais onde o
protocolo mora. É a classe *install-set ≠ upgrade-set* que a decisão (i) do
ADR-155 existe para eliminar: a enumeração compartilhada resolveu QUAIS
caminhos os dois lados tocam, nunca QUE CONTEÚDO produzem.

**W3 — o contrato não tem ADR.** A tabela de decisão é hoje a autoridade
sobre propriedade, e vive só num `docs/`. Sem ADR, a próxima pessoa que
"consertar uma assimetria" não tem onde ler que ela é decidida.

## 2. Ondas

### W1 — CI wiring (CANÔNICO: `.github/workflows/` exige cerimônia)

1. Adicionar aos **dois** filtros (`pull_request` e `push`) de
   `smoke-install.yml` — **4 caminhos, não 5**:
   ```
   scripts/tests/test-ownership-table.sh
   scripts/tests/test-ownership-verdict-unit.sh
   scripts/tests/ownership_table.tsv
   docs/ownership-decision-table.md
   ```
   > **CORREÇÃO (debate r1, devops must-fix 2).** A versão anterior deste
   > item listava também `scripts/_hash_lib.sh`. **Ele JÁ está nos dois
   > filtros** (`smoke-install.yml:15` e `:54`) — verificado com `grep -n`.
   > A lista foi escrita de memória sem abrir o arquivo, que é exatamente o
   > modo de falha registrado em
   > [[feedback-plan-mechanics-written-from-memory-fail]]. **Abra o arquivo
   > antes de editar.**
2. **Buscar o tag `v1.2.0`** antes do passo dos oráculos.

   > **AJUSTE (debate r1, devops must-fix 3).** Hardcodar `v1.2.0` no YAML
   > cria uma **segunda fonte de verdade** — o padrão existente no repo
   > resolve o pin por `--print-pin`, e `test-ownership-table.sh` não suporta
   > isso. Duas saídas: (a) dar ao harness um `--print-legacy-tag` e o YAML
   > consumir; (b) aceitar o hardcode e adicionar uma asserção que ele bata
   > com o valor embutido no harness. **(a) é o correto**; (b) só se o
   > orçamento apertar. Nunca deixar os dois divergirem em silêncio.
   ```yaml
   - name: Fetch the legacy_pristine tag
     run: |
       git fetch --no-tags --depth 1 origin +refs/tags/v1.2.0:refs/tags/v1.2.0
       git rev-parse --verify refs/tags/v1.2.0
   ```
   **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
   que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
   (rejeitada no consenso do round 1 do PLAN-167).
3. **Dois gates, dois tempos** — e isso exige **DOIS JOBS**, não duas
   entradas de filtro:
   - **por-PR:** `test-ownership-verdict-unit.sh` (segundos, 60 células)
   - **nightly:** `test-ownership-table.sh` (~25 min, 62 installs reais)

   > **BLOQUEADOR (debate r1, devops must-fix 1).** **NÃO EXISTE trigger
   > `schedule:` em `smoke-install.yml`** — verificado: zero ocorrências de
   > `schedule:`/`cron:`. O AC-4 é **insatisfazível** como estava escrito.
   > Pior: eventos `schedule:` **ignoram filtros `paths:`**, então a divisão
   > não sai de duas linhas num filtro. É preciso **criar** o job nightly
   > (job novo com `if: github.event_name == 'schedule'`, ou workflow
   > separado). **Decidir qual ANTES de codar** — é a diferença entre uma
   > entrada de filtro e um workflow novo.

   O e2e **não cabe** no teto de 25 min do job atual — o orçamento já foi
   elevado 4× (5→8→20→25). Colocá-lo no caminho por-PR quebra o job.
4. O e2e termina com **4 vermelhos deliberados**. O passo de CI precisa
   aceitar isso explicitamente **e falhar se o CONJUNTO de vermelhos MUDAR**
   — inclusive se encolher. Verde total significa que a tabela mudou.

   > **CORREÇÃO (debate r1, devops must-fix 4).** `diff` literal contra
   > `ownership-baseline-map.txt` **falha sempre em CI**: o cabeçalho do
   > arquivo carrega caminhos da máquina que o gerou (`scratch:/var/folders/…`,
   > `table:/tmp/claude-501/…`). Verificado nas linhas 2-4 do arquivo commitado.
   >
   > **Comparar o CONJUNTO DE IDs, não o arquivo.** O contrato estável é:
   > ```sh
   > sed -n '7,$p' <mapa> | grep -E '^OWN-' | grep -v GREEN | awk '{print $1}' | sort
   > ```
   > e um arquivo `scripts/tests/ownership-expected-reds.txt` com os 4 ids,
   > que é o que o CI compara. **Adicionar também um passo que normalize o
   > cabeçalho ao gravar o baseline**, senão ele volta a poluir o repo com
   > paths de máquina.

**Gate W1:** um PR tocando só `ownership_table.tsv` dispara o workflow (hoje
não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.

> **QA must-fix 2: entregue o SCRIPT, não a intenção.** O passo de CI precisa
> vir escrito no plano/pack — roda o harness, extrai os ids RED do stdout,
> compara com `ownership-expected-reds.txt`, falha em qualquer diferença de
> conjunto. Descrever o comportamento não é um gate.

### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)

1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
     em vez de o sintoma.
   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
2. **⚠️ O FIX SOZINHO NÃO CURA QUEM JÁ ESTÁ EM CAMPO** (debate r1, security
   must-fix 1). Adotante que já sofreu um upgrade tem `{{PROTOCOL_SOURCE}}`
   literal no disco. Isso classifica `live_content=edited` ⇒ o veredito é
   `PRESERVE_OWNED` e o ponteiro degradado é **preservado para sempre** —
   verificado em `upgrade.sh` no ramo `PRESERVE_OWNED`/`_lc = edited`.
   Pior: `doctor.sh` e `uninstall.sh` passam a tratar a **degradação do
   próprio framework** como customização do adotante.

   **Cura:** reconhecedor de corpo legado — se o ponteiro contém o token
   literal `{{PROTOCOL_SOURCE}}`, ele NÃO é customização, é lixo que o
   framework produziu ⇒ `REFRESH` **com backup**. Há precedente exato: o
   r20 usa fingerprints de conteúdo para migrar `SPEC/v1` legado
   (`upgrade.sh` `_SPEC_PRISTINE_FINGERPRINTS`). Mesma forma, mesma
   justificativa.

3. **⚠️ NÃO EXISTE FONTE DE VERDADE PARA O GERADOR LER** (security must-fix 2,
   **corrigido e agravado na verificação**). A crítica afirmou que o install
   grava `ph.PROTOCOL_SOURCE` no install-state. **Não grava** — verificado:
   `request.PROTOCOL_SOURCE` é `None` e a chave não existe em `request`. O
   install RESOLVE o valor em tempo de instalação e escreve direto no corpo do
   ponteiro; a **intenção nunca é persistida**.

   Consequência: a opção (b) — gerador compartilhado — **não tem de onde ler o
   valor certo**, e um upgrade rodado de outro checkout nomearia o
   checkout-do-dia. Portanto o W2 **cresce**: é preciso PERSISTIR
   `PROTOCOL_SOURCE` no install-state (campo novo), com fallback explícito
   para instalações antigas que não o têm. **Decidir o fallback ANTES de
   codar** — é a diferença entre curar e reescrever o ponteiro de todo mundo.

4. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
   exige ponteiro **byte-idêntico**. Precisa cobrir três caminhos, não um
   (security must-fix 3): install→upgrade, **upgrade→upgrade** (idempotência),
   e o **caminho de cura** (placeholder literal ⇒ REFRESH). Inputs
   normalizados (`TARGET`/`PROFILE`/`STACK`/source) ou o teste vira flaky.
5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   como base; ela já reproduz o defeito.

**Gate W2:** a sonda reporta 0 ocorrências literais após o upgrade, o teste
novo falha se alguém reverter, **e o `OWN-0074` fica VERDE** — o conjunto
esperado de vermelhos encolhe para `{OWN-0016, OWN-0024, OWN-0027}`.

> **Ordem obrigatória (QA must-fix 1):** o W2 tem de atualizar
> `ownership-expected-reds.txt` **no mesmo pack**. Se o W1 landar o gate do
> AC-5 antes, a primeira CI após o W2 falha por "o conjunto encolheu" — que é
> o gate funcionando, mas bloqueando trabalho correto.

### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)

Registrar como contrato:
- as **10 dimensões** e o enum final (**4 vereditos** após o colapso da OQ-9
  ratificado pelo Owner: `DELIVER · REFRESH · PRESERVE_OWNED ·
  PRESERVE_UNOWNED`; `ABORT_SURFACE` é **falha de execução**, não veredito);
- **INV-1..INV-4** (as quatro invariantes cross-surface);
- a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
  `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
  é a que mais convida um "conserto" futuro;
- que o `ADR-155-AMEND-1` é **emendado**, não revogado;
- as 4 células conhecidas-abertas com causa, **corretamente classificadas**:
  `OWN-0024`/`0027` = defeito do TESTE; `OWN-0016` e **`OWN-0074` = defeito de
  PRODUTO** (o `0074` é a INV-4 se manifestando no digest — ver §W2).

**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
novo muda a contagem — regenerar as superfícies derivadas).

## 3. Fronteira canônica

| Superfície | Guard | Onda |
|---|---|---|
| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
| `scripts/tests/**`, `docs/**` | ✅ livre | todas |

**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
staged, o Owner assina uma vez.

## 4. Critérios de aceite

- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros — **JÁ ESTAVA** (`:15`, `:54`); o AC vira uma asserção de regressão, não trabalho.
- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly** — exige CRIAR o job nightly (não existe `schedule:` hoje) e lembrar que `schedule:` ignora `paths:`.
- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina.
- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico**, com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
- [ ] **AC-6b** Adotante com `{{PROTOCOL_SOURCE}}` literal é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
- [ ] **AC-6c** `PROTOCOL_SOURCE` passa a ser persistido no install-state, com fallback declarado para instalações que não o têm.
- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria e as 4 abertas.
- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.

## 5. Regras do run (herdadas, custaram caro)

1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
   `git diff HEAD` aplicado se houver sujeira relevante.
2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
   defeitos do PLAN-167 foram do INSTRUMENTO
   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
   gerador com 1 de 3 callers convertidos custou 24 regressões.
6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
   PLAN-166 suja.
7. **Esperar por ARTEFATO, nunca por `pgrep`.**
8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.

## 6. Riscos

| Risco | Mitigação |
|---|---|
| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
| Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: persistir PROTOCOL_SOURCE; hoje a intenção do adotante NÃO é gravada |
| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |

## 7. Registro de execução

<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->

- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
- **Próxima ação:** W1 item 1 (path filters), em clone overlay.
