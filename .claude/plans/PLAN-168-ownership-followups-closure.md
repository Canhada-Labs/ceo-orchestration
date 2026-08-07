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
| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — **evidência HISTÓRICA (pré-PLAN-167):** install=0 ocorrências literais, upgrade=4. **Na árvore landada a sonda dá 0/0** — o sintoma mudou de forma, ver §1 W2 (rail r1 P2) |
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

**W2 — o framework trata a PRÓPRIA saída como customização do adotante.**

> ⚠️ **PREMISSA CORRIGIDA (debate r1, security).** A versão anterior deste
> parágrafo dizia "todo upgrade quebra o ponteiro raiz". **Isso era verdade
> ANTES do land do PLAN-167 e não é mais.** Re-rodei a sonda contra a árvore
> landada: **0 ocorrências literais, "pointer stays substituted"**. Meu
> próprio refactor mudou o comportamento sem que eu percebesse — o ponteiro
> substituído agora classifica `edited`, logo `PRESERVE_OWNED`, logo é
> **preservado** em vez de regenerado.

A CAUSA continua: `install.sh` **substitui** os placeholders,
`_refresh_protocol_pointer` calcula o hash canônico do heredoc com
`{{PROTOCOL_SOURCE}}` **literal**. Dois corpos diferentes para o mesmo
arquivo. O sintoma só trocou de forma:

| | antes do PLAN-167 | agora |
|---|---|---|
| bytes no disco | **degradados** a cada upgrade | preservados |
| classificação | — | a saída DO PRÓPRIO FRAMEWORK lida como customização do adotante |
| digest gravado | — | `HASH_CANONICAL_POINTER` que **não bate com o disco** ⇒ `OWN-0074` vermelha |

É a classe *install-set ≠ upgrade-set* que a decisão (i) do ADR-155 existe
para eliminar: a enumeração compartilhada resolveu QUAIS caminhos os dois
lados tocam, nunca QUE CONTEÚDO produzem.

> **O Gate W2 anterior era VACUOSO** ("a sonda reporta 0 literais") — já passa
> hoje, sem fix. Substituído abaixo.

> **E o ramo que escreve os bytes é INALCANÇÁVEL por célula** (security,
> verificado): das 6 linhas `protocol`+`upgrade` da TSV, **nenhuma** é
> `REFRESH`/`DELIVER`. O caminho que regenera o ponteiro não é exercitado por
> nada. Isso colide com o anti-objetivo "não mexer na tabela" ⇒ **decisão do
> Owner antes de codar**: ou a tabela ganha a célula que falta, ou o
> anti-objetivo cede.

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
   # CORRIGIDO (rail r1 P2): o snippet consome a flag nova — NÃO hardcodar o
   # tag no YAML (recriaria a divergência silenciosa que o parágrafo proíbe).
   - name: Fetch the legacy_pristine tag
     run: |
       set -euo pipefail
       TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
       echo "legacy pristine tag: $TAG"
       git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
       git rev-parse --verify "refs/tags/$TAG^{commit}"
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

> **⚠️ GATE VACUOSO NO PRÓPRIO HARNESS (QA must-fix 2, verificado).** A flag
> `--map` **sai rc=0 mesmo com células vermelhas** — provado:
> `--only OWN-0016 --map` ⇒ rc=0, sem `--map` ⇒ rc=1. Um passo de CI que use
> `--map` é um **gate morto que reporta sucesso para sempre**. Mitigado na
> fonte (o harness agora emite NOTE em stderr quando `--map` suprime uma
> falha), mas **o passo de CI NÃO PODE usar `--map`** — é regra, não estilo.
>
> **QA must-fix 2: entregue o SCRIPT, não a intenção.** O passo de CI precisa
> vir escrito no plano/pack — roda o harness, extrai os ids RED do stdout,
> compara com `ownership-expected-reds.txt`, falha em qualquer diferença de
> conjunto. Descrever o comportamento não é um gate.
>
> **O SCRIPT (rail r1 P1 — rc semântico explícito, HARNESS-ERR=0 exigido):**
> com N vermelhos esperados o harness sai rc=1 POR DESIGN; `set -e` cru morre
> antes de comparar, e engolir o rc cegamente aceita rc=2 (erro de harness) ou
> saída parcial. O passo é:
> ```sh
> set -uo pipefail
> rc=0
> bash scripts/tests/test-ownership-table.sh > /tmp/own-map.txt 2>/tmp/own-err.txt || rc=$?
> cat /tmp/own-map.txt
> sed -n '1,40p' /tmp/own-err.txt >&2 || true
> # rc=2 (ou >2) = erro de harness/infra — NUNCA comparável
> if [ "$rc" -ge 2 ]; then echo "::error::harness rc=$rc"; exit 1; fi
> # o sumário precisa existir e reportar HARNESS-ERR=0 (saída parcial não passa)
> grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' /tmp/own-map.txt \
>   || { echo "::error::sumário ausente ou HARNESS-ERR>0 (saída parcial/vacuosa)"; exit 1; }
> # (rail r2 P1) status ≠ GREEN e ≠ RED — TIMEOUT/ESCAPE/AMBIG — NUNCA é
> # aceitável: um id esperado-vermelho que degrada para TIMEOUT/ESCAPE mantém
> # o CONJUNTO intacto e esconderia uma regressão PIOR atrás de "mesmo set".
> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2!="GREEN" && $2!="RED"' \
>   | grep . && { echo "::error::célula em status nunca-aceitável"; exit 1; }
> # conjunto RED exato observado vs esperado — QUALQUER diferença falha
> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2=="RED" {print $1}' \
>   | LC_ALL=C sort > /tmp/own-got.txt
> grep -E '^OWN-' scripts/tests/ownership-expected-reds.txt | LC_ALL=C sort > /tmp/own-exp.txt
> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
> echo "ownership nightly: conjunto de vermelhos estável"
> ```
> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
>
> **Implementação entregue (W1):** o contrato acima vive em
> `scripts/tests/ownership-nightly-gate.sh` (script chamado pelo workflow —
> testável, diferente de YAML inline) com controle positivo
> `scripts/tests/test-ownership-nightly-gate.sh`: **12 cenários de falha
> plantados com harness fake**, incluindo os degrades TIMEOUT/ESCAPE/AMBIG
> do rail r2.

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

   **Cura:** reconhecedor de corpo legado ⇒ `REFRESH` **com backup**.

   > **⚠️ CORRIGIDO 2× (rail r1 P1 + r2 P1): o reconhecedor é por
   > RECONSTRUÇÃO DE TEMPLATE, nunca substring E nunca hash estático.**
   > Substring é destrutivo (um `PROTOCOL.md` do adotante que legitimamente
   > CONTÉM o token seria força-refreshado — backup não desfaz a perda do
   > arquivo ATIVO). Mas hash estático por versão é INÚTIL em campo (r2):
   > o heredoc degradado embute `$TARGET`, `$PROFILE` e `$STACK` RESOLVIDOS
   > (verificado em `_refresh_protocol_pointer`, ramo `*)`) — cada adotante
   > tem um corpo degradado DIFERENTE, e um fingerprint fixo preservaria
   > quase todos para sempre (AC-6b não cumprido).
   >
   > **A forma correta:** casar o corpo observado contra o ESQUELETO exato do
   > template degradado (um por versão de framework que o produziu): extrair
   > os campos variáveis das posições fixas, re-renderizar o template com os
   > valores extraídos + `{{PROTOCOL_SOURCE}}` literal, e exigir
   > **byte-igualdade** com o observado. Qualquer desvio ⇒ não-match ⇒
   > **preservar**. Isso mantém a garantia do r1 (exatidão, fail-toward-
   > preservation) sem a inutilidade do hash fixo. A semântica da célula D2
   > (`live_content=degraded`) é determinada por essa reconstrução.

3. **A FONTE DE VERDADE JÁ EXISTE — o debate a verificou ERRADO** (rail r1
   P1, verificado literalmente; substitui o security must-fix 2 do round 1).
   A "correção" do debate checou a chave errada: `request.PROTOCOL_SOURCE`
   top-level de fato não existe, **mas o install PERSISTE o valor** —
   `install.sh:2523` passa `"ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"` ao
   state writer, que coleta todo `ph.*` em `request.placeholders` e faz
   **UNION entre runs** (novo não-vazio sobrescreve; anterior permanece).
   `PH_PROTOCOL_SOURCE` tem default `$SOURCE_DIR` ⇒ efetivamente sempre
   gravado em installs do install.sh atual.

   Consequência: **NÃO criar campo novo** — seria uma segunda fonte de
   verdade. O gerador compartilhado **consome e valida**
   `request.placeholders.PROTOCOL_SOURCE`. O fallback (D3: extrair do
   ponteiro são no disco; degradado ⇒ fonte resolvida do upgrade + backup +
   aviso) aplica-se SOMENTE a estados genuinamente antigos/ausentes — e a
   implementação deve verificar se o `upgrade.sh` preserva
   `request.placeholders` ao reescrever o state (se não preserva, esse é um
   sub-defeito do mesmo W2).

4. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
   exige ponteiro **byte-idêntico**. Precisa cobrir três caminhos, não um
   (security must-fix 3): install→upgrade, **upgrade→upgrade** (idempotência),
   e o **caminho de cura** (corpo degradado ⇒ REFRESH). Inputs
   normalizados (`TARGET`/`PROFILE`/`STACK`/source) ou o teste vira flaky.

   > **⚠️ BYTE-IDENTIDADE SOZINHA É VACUOSA (rail r1 P1).** Se o gerador
   > compartilhado for acidentalmente baseado no heredoc QUEBRADO do upgrade
   > atual, install e upgrade produzem o MESMO ponteiro errado: bytes
   > idênticos, digest bate com o disco, classificação vira `pristine` e o
   > `OWN-0074` fica verde — vacuosamente. O teste EXIGE, além da identidade,
   > asserções de CONTEÚDO: `{{PROTOCOL_SOURCE}}` **ausente** e a fonte
   > resolvida esperada **presente**, após install, upgrade E migração/cura.
   >
   > **⚠️ E o teste TEM de estar FIADO em CI (rail r2 P1)** — senão é a
   > classe não-fiada que o W1 existe para fechar, recriada no mesmo pack.
   > Fiação: step no `ownership-nightly.yml` (obrigatório) + o arquivo do
   > teste nos DOIS path filters do `smoke-install.yml`; entrar também como
   > step por-PR no job `smoke` SE a medição couber no teto de 25 min
   > (medir, não chutar — o orçamento já subiu 4×).
   >
   > **⚠️ ALIASING DE HASH NO `OWN-0074` (rail r2 P1, verificado no
   > harness).** Com o fix + fonte persistida, o digest prior (do install) e
   > o canônico passam a ser OS MESMOS bytes; `_derive_hash_source` testa
   > `c_prior` ANTES de `c_pointer` **por design documentado** ("the
   > canonical name is then reached only when the two genuinely differ").
   > Resultado: a célula reporta `HASH_PRIOR_RECORD`, a TSV espera
   > `HASH_CANONICAL_POINTER`, e o `OWN-0074` ficaria vermelho MESMO CURADO.
   > **O pack atualiza a coluna `exp_hash` do `OWN-0074` para
   > `HASH_PRIOR_RECORD`** — o VEREDITO (`PRESERVE_OWNED`) fica intocado; a
   > mudança de contrato observável é consequência necessária da cura (o
   > gate W2 "0074 VERDE" já a implica). **Nuance de escopo do D2 a
   > ratificar na assinatura:** D2 dizia "só adição"; esta é UMA edição de
   > coluna de hash na célula que está sendo curada, com causa registrada.
5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   como base; ela já reproduz o defeito.

**Gate W2 (o anterior era vacuoso — este não):** o digest gravado para
`PROTOCOL.md` **bate com os bytes no disco**, o ponteiro deixa de classificar
`edited` no caminho comum, e **o `OWN-0074` fica VERDE** — o conjunto
esperado de vermelhos encolhe para `{OWN-0016, OWN-0024, OWN-0027}`.

> **Ordem obrigatória (QA must-fix 1):** o W2 tem de atualizar
> `ownership-expected-reds.txt` **no mesmo pack**. Se o W1 landar o gate do
> AC-5 antes, a primeira CI após o W2 falha por "o conjunto encolheu" — que é
> o gate funcionando, mas bloqueando trabalho correto.

### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)

Registrar como contrato:
- que `ABORT_SURFACE` é **resultado de OBSERVAÇÃO do harness**, e não um
  membro do enum de decisão — a função nunca o devolve (QA advisory 3). Sem
  essa distinção o ADR contradiz o código;
- as **10 dimensões** e o enum final (**4 vereditos** após o colapso da OQ-9
  ratificado pelo Owner: `DELIVER · REFRESH · PRESERVE_OWNED ·
  PRESERVE_UNOWNED`; `ABORT_SURFACE` é **falha de execução**, não veredito);
- **INV-1..INV-4** (as quatro invariantes cross-surface);
- a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
  `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
  é a que mais convida um "conserto" futuro;
- que o `ADR-155-AMEND-1` é **emendado**, não revogado;
- as células conhecidas-abertas com causa, **corretamente classificadas E no
  tempo certo (rail r1 P2 — o ADR nasce no MESMO pack que fecha o `0074`):**
  abertas após este pack = `{OWN-0016, OWN-0024, OWN-0027}` (`0024`/`0027` =
  defeito do TESTE; `0016` = PRODUTO); **`OWN-0074` entra como defeito de
  PRODUTO FECHADO por este pack** (era a INV-4 se manifestando no digest —
  ver §W2), registrado como histórico, não como aberto. Um ADR que listasse
  4 abertas estaria stale no momento da criação.

**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
novo muda a contagem — regenerar as superfícies derivadas).

## 3. Fronteira canônica

| Superfície | Guard | Onda |
|---|---|---|
| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
| `.github/workflows/ownership-nightly.yml` (NOVO — rail r2 P2: todo `.github/workflows/*.yml` é sentinel-guarded; sem esta linha o inventário da cerimônia nasce incompleto) | 🔒 | W1 |
| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
| `scripts/tests/ownership_table.tsv` (célula nova D2 + coluna `exp_hash` do OWN-0074) | ✅ livre | W2 |
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
- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina. **O passo é o SCRIPT do §W1.4** (rc semântico + `HARNESS-ERR=0` exigido + diff de conjunto), nunca `--map`.
- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico E com conteúdo certo** (token literal AUSENTE, fonte resolvida PRESENTE — rail r1 P1), com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
- [ ] **AC-6b** Adotante com corpo DEGRADADO (fingerprint exato de corpo que o framework produziu — NUNCA substring; não-match preserva) é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
- [ ] **AC-6c** O gerador consome `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — não criar campo novo), com fallback D3 declarado só para estados antigos/ausentes; verificar que o upgrade preserva `request.placeholders`.
- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
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
| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: consumir `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — rail r2 P2 removeu a claim contrária, que era stale); fallback D3 só para estados antigos/ausentes |
| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |

## 7. Registro de execução

<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->

- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
- **S297 (07/08, retomada):** commit `11cd4f6` pushado. Claims mecânicas do
  plano re-verificadas na árvore viva — **todas conferem** (filtros `:15`/`:54`,
  4 paths com grep=0, zero `schedule:`, `fetch-depth:1` em `:101`, header do
  baseline com paths de máquina, 6 células protocol+upgrade sem REFRESH/DELIVER,
  NOTE do `--map` em `test-ownership-table.sh:690`, `_SPEC_PRISTINE_FINGERPRINTS`
  presente, `PROTOCOL_SOURCE` não persistido, sonda INV-4 presente).
- **Decisões do Owner (07/08, registradas antes de codar):**
  - **D1 (W2 direção): opção (b)** — gerador compartilhado único que
    install/upgrade chamam.
  - **D2 (célula da cura): a tabela GANHA linhas novas** — `live_content`
    ganha o valor `degraded` (corpo com `{{PROTOCOL_SOURCE}}` literal = lixo
    do próprio framework) ⇒ células novas com veredito `REFRESH` (com backup).
    Só ADIÇÃO; os 62 vereditos existentes ficam intocados. O anti-objetivo de
    §0 cede formalmente neste ponto, no molde do precedente r20.
  - **D3 (fallback PROTOCOL_SOURCE): extrair do ponteiro são** no disco e
    persistir; se degradado (literal), usar a fonte resolvida do upgrade +
    backup + aviso. Nunca renomear silenciosamente um ponteiro são.
  - **D4 (nightly): workflow NOVO** `ownership-nightly.yml` (schedule próprio,
    timeout próprio, zero guards nos jobs existentes do `smoke-install.yml`).
- **Rail codex:** 1ª invocação (18:02) foi mal-escopada — diff era um comentário
  inerte sobre draft pré-debate; preservada como `rail/codex-r0-misscoped.md`,
  NÃO conta para o teto do AC-8. r1 re-escopado disparado (plano inteiro como
  diff staged sobre baseline com sujeira aplicada, clone overlay em scratchpad).
- **Rail r1 (re-escopado) CONSUMIDO:** 4 P1 + 3 P2, **7 aceitos / 0
  refutados**, todos verificados contra o código antes de aceitar
  (`rail/codex-r1.md`). Destaque de governança: o P1 "fonte de verdade"
  **derrubou a verificação do debate** — o security checou
  `request.PROTOCOL_SOURCE` (top-level, inexistente) e "corrigiu" uma claim
  CERTA para errada; `install.sh:2523` + writer provam que
  `request.placeholders.PROTOCOL_SOURCE` É persistido (UNION entre runs).
  Fixes aplicados como linhas: §0 (sonda = evidência histórica), §W1.2
  (snippet consome `--print-legacy-tag`), §W1.4 (SCRIPT concreto do gate),
  §W2.2 (fingerprint exato, nunca substring), §W2.3 (consumir chave
  existente), §W2.4 (asserções de conteúdo anti-vacuidade), §W3 (0074
  fechado histórico, 3 abertas), AC-5/6/6b/6c/7.
- **Decisões amendadas pelos achados:** D2 ganha semântica fixa
  (`degraded` = fingerprint exato); D3 vira fallback-only (a fonte primária
  é a chave já persistida).
- **Rail r2 CONSUMIDO:** 4 P1 + 2 P2, **6 aceitos / 0 refutados**
  (`rail/codex-r2.md`), os dois claims não-triviais verificados literalmente:
  o heredoc degradado EMBUTE `$TARGET/$PROFILE/$STACK` (fingerprint estático
  seria inútil em campo ⇒ reconstrução de template), e a ordem
  prior-antes-de-canonical do `_derive_hash_source` colapsa o nome quando a
  cura aliasa os digests (⇒ pack atualiza `exp_hash` do OWN-0074 para
  `HASH_PRIOR_RECORD`, veredito intocado — nuance do D2 a ratificar na
  assinatura). Gate endurecido: conjunto RED exato + zero-tolerância a
  TIMEOUT/ESCAPE/AMBIG. Fixes: §W1.4, §W2.2, §W2.4 (fiação CI do teste
  INV-4 + aliasing), §3 (nightly no inventário), §6 (claim stale removida).
- **W1 EXECUTADO no overlay `plan168-dev` (verificado, aguardando pack):**
  4 paths nos dois filtros + step do oráculo unitário em `smoke-install.yml`;
  `ownership-nightly.yml` novo (schedule 43 6 UTC + dispatch, gate via
  script); harness ganhou `--print-legacy-tag` (fonte única do pin, literais
  internos convertidos) e `--stable-header` (baseline commitável sem paths de
  máquina); `ownership-expected-reds.txt` (4 ids; W2 encolhe p/ 3 no mesmo
  pack); `ownership-nightly-gate.sh` + controle positivo **12/12**; YAML
  válido; shellcheck limpo; oráculo unitário 60/60.
- **Rail r3 CONSUMIDO (teto do AC-8 atingido):** 3 P1 + 1 P2 — **3 aceitos,
  1 REFUTADO com evidência** (`rail/codex-r3.md`): a claim "artefatos do rail
  inexistentes" era artefato de CLONE STALE — o codex revisou o clone
  congelado pré-arquivamento; na árvore viva `codex-r0-misscoped.md`/`r1`/
  `r2`/`README-scope.md` existem (ls datado registrado). Aceitos: fronteira
  ganhou `scripts/_framework_manifest_set.sh` (está em `_CANONICAL_GUARDS:199`
  — o gerador foi PARA DENTRO dele, zero superfície de guard nova); controle
  do gate + render control fiados POR-PR no smoke; docs §2.4 ganhou `degraded`
  + regra de aliasing + R-04b.
  **Rail encerrado no teto de 3 com motivo:** severidade decrescente
  (fundamentos → semântica → inventário), 16 achados aplicados / 1 refutado,
  zero achados estruturais no r3, e o V3 (cerimônia GPG do Owner) ainda
  sela o pack. Rodadas r1/r2/r3 arquivadas.
- **W2 EXECUTADO no overlay (provado):** gerador único
  (`_render_protocol_pointer*` + `_protocol_pointer_is_degraded` DENTRO do
  FMS); install e upgrade convertidos NO MESMO edit-set; leitura de
  `request.placeholders.PROTOCOL_SOURCE` com fallback D3 (extração validada
  por reconstrução do ponteiro são); `_lc` ganha `degraded` (reconstrução de
  template, nunca substring); Stage B ganha cláusula `degraded` (doutrina
  legacy_pristine); TSV +3 células (OWN-0092/0093/0094); regra de aliasing
  em `_derive_hash_source` (5º arg, só quando candidatos aliasam).
  **Provas:** render control 8/8 (inclui paridade byte-a-byte com install
  REAL); INV-4 4/4 pernas (install→upgrade idêntico, idempotente, degradado
  CURADO com backup, customização preservada); oráculo unitário 63/63;
  e2e `--only` das 7 células protocol TODAS GREEN — **OWN-0074 verde pela
  primeira vez**; `ownership-expected-reds.txt` → 3 ids. **Descoberta do
  aliasing confirmada:** manter TSV 0074 = `HASH_CANONICAL_POINTER` e
  resolver o nome no harness SÓ quando os digests são iguais (a alternativa
  — reordenar probes — renomearia 0071/0072 também).
- **W3 EXECUTADO:** `ADR-190` escrito (dimensões, enum 4, ABORT_SURFACE como
  falha de execução, INV-1..4, assimetria decidida, degraded/aliasing,
  ADR-155-AMEND-1 emendado, 3 abertas + 0074 histórico). Superfícies
  derivadas regeneradas (CLAUDE.md 190 ADRs; FAQ/CTO-GUIDE/READMEs/
  ARCHITECTURE/docs-README; workflows 21→22 pego pelo próprio
  verify-counts). `check-claude-md-claims.py` rc=0; `verify-counts.sh` rc=0.
- **E2E COMPLETO (65 células) via o gate REAL: `GREEN=62 RED=3 AMBIG=0
  HARNESS-ERR=0`, RED set = exatamente `{OWN-0016, OWN-0024, OWN-0027}`,
  gate rc=0** (run 2026-08-07 20:17, ~40 min; log em /tmp/p168-full-e2e.log
  da sessão). O OWN-0074 está verde na tabela CHEIA, não só no `--only`.
  Baseline re-gravado (`ownership-baseline-map.txt`): cabeçalho estável
  (placeholders) + corpo DESTE run — proveniência: as linhas `OWN-*` e o
  sumário são a saída literal do harness; só as 4 linhas de cabeçalho vêm do
  modo `--stable-header` (determinísticas).
- **Risco §6 "doctor/uninstall" avaliado e fechado:** `doctor.sh` decide por
  REGISTRO DE ENTREGA (`_dr_delivered`), não por classificação de conteúdo —
  a cura não altera a presença do registro; `uninstall.sh` não referencia o
  ponteiro. Sem falso-positivo novo; adotantes da era degradada saram
  (bytes+registro coerentes) no upgrade seguinte.
- **PACK MONTADO (AC-9):** `staged/` com 24 arquivos (gitignored por design)
  + `staged-manifest.sha256` RASTREADO (24 entradas, `shasum -c` da raiz
  24/24 OK) + `land-table.tsv` (precondições por sha da baseline; 7 ABSENT)
  + `OWNER-LAND.sh` (fail-closed: manifesto → precondições de bytes →
  **2b: pack files LIMPOS no git** — bytes certos não provam 166 commitado;
  provado: rc=1 hoje com a sujeira do 166 presente → apply por tabela com
  exec-bit → re-verificação pós-cópia → gates rápidos → git add explícito
  impresso) + `W-approved-draft.md` (Scope: 6 canônicos; nuance D2
  explicitada para ratificação).
- **ORDEM DOS PACKS (contrato):** a cerimônia do PLAN-166 landa PRIMEIRO —
  as cópias staged dos arquivos compartilhados carregam aquele conteúdo por
  baixo; o `OWNER-LAND.sh` aborta enquanto qualquer arquivo do pack estiver
  sujo no git.
- **Próxima ação:** fila do Owner — (1) landar PLAN-166 (runbook próprio),
  (2) assinar `approved.md` do PLAN-168 (anchor real + Scope), (3)
  `OWNER-LAND.sh --dry-run` → apply → bateria → commit -S → push.
