OpenAI Codex v0.144.6
--------
workdir: /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fde60-b773-7242-8394-7a75e0326ed6
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- DIFF STAT ---\\n' && git diff --stat && printf '\\n--- CACHED STAT ---\\n' && git diff --cached --stat" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-khLmtQuf' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ftCjWPwx' (errno=Operation not permitted)
A  .claude/plans/PLAN-168-ownership-followups-closure.md

--- DIFF STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-h3tSGrH2' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ufZwbaR8' (errno=Operation not permitted)

--- CACHED STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GbpLj5p9' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GqM4l1aT' (errno=Operation not permitted)
 .../plans/PLAN-168-ownership-followups-closure.md  | 409 +++++++++++++++++++++
 1 file changed, 409 insertions(+)

exec
/bin/zsh -lc 'git diff --cached -- .claude/plans/PLAN-168-ownership-followups-closure.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-D3kpNjmB' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-5iKjTxB2' (errno=Operation not permitted)
diff --git a/.claude/plans/PLAN-168-ownership-followups-closure.md b/.claude/plans/PLAN-168-ownership-followups-closure.md
new file mode 100644
index 0000000..7291d0e
--- /dev/null
+++ b/.claude/plans/PLAN-168-ownership-followups-closure.md
@@ -0,0 +1,409 @@
+---
+id: PLAN-168
+title: Fechamento dos follow-ups do PLAN-167 — CI que não roda, ponteiro que degrada, contrato sem ADR
+status: reviewed
+created: 2026-08-07
+reviewed_at: 2026-08-07
+owner: CEO
+depends_on: [PLAN-167]
+budget_tokens: 120-180k
+budget_sessions: 1
+context_risk: medium
+external_wait: assinatura GPG do Owner para o W1 (workflows são superfície canônica)
+tags: [ci, install, upgrade, adr, testing, canonical]
+---
+
+# PLAN-168 — fechamento dos follow-ups do PLAN-167
+
+> **Origem.** O PLAN-167 landou em `7c0828a` (assinado, pushado). Três coisas
+> ficaram deliberadamente FORA daquele Scope, e cada uma tem causa nomeada e
+> evidência já produzida. Este plano não descobre nada novo: ele **fecha o que
+> já foi diagnosticado**.
+
+## 0. O que já está provado (não re-investigar)
+
+| Item | Evidência existente |
+|---|---|
+| CI não dispara os oráculos | `grep -c` = 0 para os **4** paths novos em `smoke-install.yml` (o `_hash_lib.sh` JÁ está lá, `:15`/`:54`); codex rail r1/r2/r4 |
+| `fetch-depth: 1` não traz tags | `smoke-install.yml:101`; o harness precisa de `v1.2.0` para as linhas `legacy_pristine*` |
+| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — **evidência HISTÓRICA (pré-PLAN-167):** install=0 ocorrências literais, upgrade=4. **Na árvore landada a sonda dá 0/0** — o sintoma mudou de forma, ver §1 W2 (rail r1 P2) |
+| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
+| **`OWN-0074` é PRODUTO, não teste** | debate r1 QA must-fix 1, verificado: registro=`hash(corpo com {{PROTOCOL_SOURCE}} literal)`, disco=`hash(corpo substituído)` ⇒ é a INV-4 no digest. **A classificação anterior ("2 são defeito do teste") estava ERRADA** e está corrigida aqui, na memória e no CLAUDE.md. |
+
+**Anti-objetivo:** não mexer na tabela de decisão nem nos vereditos. O
+PLAN-167 fechou aquilo com 58/62 e rail de 4 rodadas. Aqui só se fecha o
+entorno.
+
+## 1. O problema, em uma frase cada
+
+**W1 — teste que não roda apodrece.** Os dois oráculos do PLAN-167
+(`test-ownership-verdict-unit.sh`, `test-ownership-table.sh`) não estão em
+nenhum path filter. Um PR que altere a tabela ou o harness **pula o gate
+inteiro**. É literalmente a classe do achado r10-F4 — um teste
+cuja única execução em CI era pulada — reaparecendo no trabalho que a
+consertou.
+
+**W2 — o framework trata a PRÓPRIA saída como customização do adotante.**
+
+> ⚠️ **PREMISSA CORRIGIDA (debate r1, security).** A versão anterior deste
+> parágrafo dizia "todo upgrade quebra o ponteiro raiz". **Isso era verdade
+> ANTES do land do PLAN-167 e não é mais.** Re-rodei a sonda contra a árvore
+> landada: **0 ocorrências literais, "pointer stays substituted"**. Meu
+> próprio refactor mudou o comportamento sem que eu percebesse — o ponteiro
+> substituído agora classifica `edited`, logo `PRESERVE_OWNED`, logo é
+> **preservado** em vez de regenerado.
+
+A CAUSA continua: `install.sh` **substitui** os placeholders,
+`_refresh_protocol_pointer` calcula o hash canônico do heredoc com
+`{{PROTOCOL_SOURCE}}` **literal**. Dois corpos diferentes para o mesmo
+arquivo. O sintoma só trocou de forma:
+
+| | antes do PLAN-167 | agora |
+|---|---|---|
+| bytes no disco | **degradados** a cada upgrade | preservados |
+| classificação | — | a saída DO PRÓPRIO FRAMEWORK lida como customização do adotante |
+| digest gravado | — | `HASH_CANONICAL_POINTER` que **não bate com o disco** ⇒ `OWN-0074` vermelha |
+
+É a classe *install-set ≠ upgrade-set* que a decisão (i) do ADR-155 existe
+para eliminar: a enumeração compartilhada resolveu QUAIS caminhos os dois
+lados tocam, nunca QUE CONTEÚDO produzem.
+
+> **O Gate W2 anterior era VACUOSO** ("a sonda reporta 0 literais") — já passa
+> hoje, sem fix. Substituído abaixo.
+
+> **E o ramo que escreve os bytes é INALCANÇÁVEL por célula** (security,
+> verificado): das 6 linhas `protocol`+`upgrade` da TSV, **nenhuma** é
+> `REFRESH`/`DELIVER`. O caminho que regenera o ponteiro não é exercitado por
+> nada. Isso colide com o anti-objetivo "não mexer na tabela" ⇒ **decisão do
+> Owner antes de codar**: ou a tabela ganha a célula que falta, ou o
+> anti-objetivo cede.
+
+**W3 — o contrato não tem ADR.** A tabela de decisão é hoje a autoridade
+sobre propriedade, e vive só num `docs/`. Sem ADR, a próxima pessoa que
+"consertar uma assimetria" não tem onde ler que ela é decidida.
+
+## 2. Ondas
+
+### W1 — CI wiring (CANÔNICO: `.github/workflows/` exige cerimônia)
+
+1. Adicionar aos **dois** filtros (`pull_request` e `push`) de
+   `smoke-install.yml` — **4 caminhos, não 5**:
+   ```
+   scripts/tests/test-ownership-table.sh
+   scripts/tests/test-ownership-verdict-unit.sh
+   scripts/tests/ownership_table.tsv
+   docs/ownership-decision-table.md
+   ```
+   > **CORREÇÃO (debate r1, devops must-fix 2).** A versão anterior deste
+   > item listava também `scripts/_hash_lib.sh`. **Ele JÁ está nos dois
+   > filtros** (`smoke-install.yml:15` e `:54`) — verificado com `grep -n`.
+   > A lista foi escrita de memória sem abrir o arquivo, que é exatamente o
+   > modo de falha registrado em
+   > [[feedback-plan-mechanics-written-from-memory-fail]]. **Abra o arquivo
+   > antes de editar.**
+2. **Buscar o tag `v1.2.0`** antes do passo dos oráculos.
+
+   > **AJUSTE (debate r1, devops must-fix 3).** Hardcodar `v1.2.0` no YAML
+   > cria uma **segunda fonte de verdade** — o padrão existente no repo
+   > resolve o pin por `--print-pin`, e `test-ownership-table.sh` não suporta
+   > isso. Duas saídas: (a) dar ao harness um `--print-legacy-tag` e o YAML
+   > consumir; (b) aceitar o hardcode e adicionar uma asserção que ele bata
+   > com o valor embutido no harness. **(a) é o correto**; (b) só se o
+   > orçamento apertar. Nunca deixar os dois divergirem em silêncio.
+   ```yaml
+   # CORRIGIDO (rail r1 P2): o snippet consome a flag nova — NÃO hardcodar o
+   # tag no YAML (recriaria a divergência silenciosa que o parágrafo proíbe).
+   - name: Fetch the legacy_pristine tag
+     run: |
+       set -euo pipefail
+       TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
+       echo "legacy pristine tag: $TAG"
+       git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
+       git rev-parse --verify "refs/tags/$TAG^{commit}"
+   ```
+   **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
+   que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
+   (rejeitada no consenso do round 1 do PLAN-167).
+3. **Dois gates, dois tempos** — e isso exige **DOIS JOBS**, não duas
+   entradas de filtro:
+   - **por-PR:** `test-ownership-verdict-unit.sh` (segundos, 60 células)
+   - **nightly:** `test-ownership-table.sh` (~25 min, 62 installs reais)
+
+   > **BLOQUEADOR (debate r1, devops must-fix 1).** **NÃO EXISTE trigger
+   > `schedule:` em `smoke-install.yml`** — verificado: zero ocorrências de
+   > `schedule:`/`cron:`. O AC-4 é **insatisfazível** como estava escrito.
+   > Pior: eventos `schedule:` **ignoram filtros `paths:`**, então a divisão
+   > não sai de duas linhas num filtro. É preciso **criar** o job nightly
+   > (job novo com `if: github.event_name == 'schedule'`, ou workflow
+   > separado). **Decidir qual ANTES de codar** — é a diferença entre uma
+   > entrada de filtro e um workflow novo.
+
+   O e2e **não cabe** no teto de 25 min do job atual — o orçamento já foi
+   elevado 4× (5→8→20→25). Colocá-lo no caminho por-PR quebra o job.
+4. O e2e termina com **4 vermelhos deliberados**. O passo de CI precisa
+   aceitar isso explicitamente **e falhar se o CONJUNTO de vermelhos MUDAR**
+   — inclusive se encolher. Verde total significa que a tabela mudou.
+
+   > **CORREÇÃO (debate r1, devops must-fix 4).** `diff` literal contra
+   > `ownership-baseline-map.txt` **falha sempre em CI**: o cabeçalho do
+   > arquivo carrega caminhos da máquina que o gerou (`scratch:/var/folders/…`,
+   > `table:/tmp/claude-501/…`). Verificado nas linhas 2-4 do arquivo commitado.
+   >
+   > **Comparar o CONJUNTO DE IDs, não o arquivo.** O contrato estável é:
+   > ```sh
+   > sed -n '7,$p' <mapa> | grep -E '^OWN-' | grep -v GREEN | awk '{print $1}' | sort
+   > ```
+   > e um arquivo `scripts/tests/ownership-expected-reds.txt` com os 4 ids,
+   > que é o que o CI compara. **Adicionar também um passo que normalize o
+   > cabeçalho ao gravar o baseline**, senão ele volta a poluir o repo com
+   > paths de máquina.
+
+**Gate W1:** um PR tocando só `ownership_table.tsv` dispara o workflow (hoje
+não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
+
+> **⚠️ GATE VACUOSO NO PRÓPRIO HARNESS (QA must-fix 2, verificado).** A flag
+> `--map` **sai rc=0 mesmo com células vermelhas** — provado:
+> `--only OWN-0016 --map` ⇒ rc=0, sem `--map` ⇒ rc=1. Um passo de CI que use
+> `--map` é um **gate morto que reporta sucesso para sempre**. Mitigado na
+> fonte (o harness agora emite NOTE em stderr quando `--map` suprime uma
+> falha), mas **o passo de CI NÃO PODE usar `--map`** — é regra, não estilo.
+>
+> **QA must-fix 2: entregue o SCRIPT, não a intenção.** O passo de CI precisa
+> vir escrito no plano/pack — roda o harness, extrai os ids RED do stdout,
+> compara com `ownership-expected-reds.txt`, falha em qualquer diferença de
+> conjunto. Descrever o comportamento não é um gate.
+>
+> **O SCRIPT (rail r1 P1 — rc semântico explícito, HARNESS-ERR=0 exigido):**
+> com N vermelhos esperados o harness sai rc=1 POR DESIGN; `set -e` cru morre
+> antes de comparar, e engolir o rc cegamente aceita rc=2 (erro de harness) ou
+> saída parcial. O passo é:
+> ```sh
+> set -uo pipefail
+> rc=0
+> bash scripts/tests/test-ownership-table.sh > /tmp/own-map.txt 2>/tmp/own-err.txt || rc=$?
+> cat /tmp/own-map.txt
+> sed -n '1,40p' /tmp/own-err.txt >&2 || true
+> # rc=2 (ou >2) = erro de harness/infra — NUNCA comparável
+> if [ "$rc" -ge 2 ]; then echo "::error::harness rc=$rc"; exit 1; fi
+> # o sumário precisa existir e reportar HARNESS-ERR=0 (saída parcial não passa)
+> grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' /tmp/own-map.txt \
+>   || { echo "::error::sumário ausente ou HARNESS-ERR>0 (saída parcial/vacuosa)"; exit 1; }
+> # conjunto de não-verdes observado vs esperado — QUALQUER diferença falha
+> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | grep -v '[[:space:]]GREEN[[:space:]]' \
+>   | awk '{print $1}' | LC_ALL=C sort > /tmp/own-got.txt
+> LC_ALL=C sort scripts/tests/ownership-expected-reds.txt > /tmp/own-exp.txt
+> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
+>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
+> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
+> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
+> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
+> echo "ownership nightly: conjunto de vermelhos estável"
+> ```
+> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
+> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
+
+### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
+
+1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
+   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
+   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
+     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
+     em vez de o sintoma.
+   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
+2. **⚠️ O FIX SOZINHO NÃO CURA QUEM JÁ ESTÁ EM CAMPO** (debate r1, security
+   must-fix 1). Adotante que já sofreu um upgrade tem `{{PROTOCOL_SOURCE}}`
+   literal no disco. Isso classifica `live_content=edited` ⇒ o veredito é
+   `PRESERVE_OWNED` e o ponteiro degradado é **preservado para sempre** —
+   verificado em `upgrade.sh` no ramo `PRESERVE_OWNED`/`_lc = edited`.
+   Pior: `doctor.sh` e `uninstall.sh` passam a tratar a **degradação do
+   próprio framework** como customização do adotante.
+
+   **Cura:** reconhecedor de corpo legado ⇒ `REFRESH` **com backup**.
+
+   > **⚠️ CORRIGIDO (rail r1 P1): o reconhecedor é por FINGERPRINT EXATO do
+   > corpo inteiro, NUNCA por substring.** Um `PROTOCOL.md` do adotante que
+   > legitimamente CONTÉM o token `{{PROTOCOL_SOURCE}}` (documentando-o, ou
+   > herdado e editado por cima) seria classificado como lixo por um matcher
+   > de substring e força-refreshado — backup não desfaz a perda do arquivo
+   > ATIVO. Reconhecer somente hashes exatos dos corpos degradados que o
+   > framework historicamente produziu (um por versão que os gerou), e
+   > **falhar em direção à preservação** em qualquer não-match. O precedente
+   > r20 (`_SPEC_PRISTINE_FINGERPRINTS`) já é exatamente essa forma — segui-lo
+   > literalmente, não por analogia frouxa. Isso também fixa a semântica da
+   > célula nova da tabela (D2): `live_content=degraded` é determinado por
+   > fingerprint exato.
+
+3. **A FONTE DE VERDADE JÁ EXISTE — o debate a verificou ERRADO** (rail r1
+   P1, verificado literalmente; substitui o security must-fix 2 do round 1).
+   A "correção" do debate checou a chave errada: `request.PROTOCOL_SOURCE`
+   top-level de fato não existe, **mas o install PERSISTE o valor** —
+   `install.sh:2523` passa `"ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"` ao
+   state writer, que coleta todo `ph.*` em `request.placeholders` e faz
+   **UNION entre runs** (novo não-vazio sobrescreve; anterior permanece).
+   `PH_PROTOCOL_SOURCE` tem default `$SOURCE_DIR` ⇒ efetivamente sempre
+   gravado em installs do install.sh atual.
+
+   Consequência: **NÃO criar campo novo** — seria uma segunda fonte de
+   verdade. O gerador compartilhado **consome e valida**
+   `request.placeholders.PROTOCOL_SOURCE`. O fallback (D3: extrair do
+   ponteiro são no disco; degradado ⇒ fonte resolvida do upgrade + backup +
+   aviso) aplica-se SOMENTE a estados genuinamente antigos/ausentes — e a
+   implementação deve verificar se o `upgrade.sh` preserva
+   `request.placeholders` ao reescrever o state (se não preserva, esse é um
+   sub-defeito do mesmo W2).
+
+4. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
+   exige ponteiro **byte-idêntico**. Precisa cobrir três caminhos, não um
+   (security must-fix 3): install→upgrade, **upgrade→upgrade** (idempotência),
+   e o **caminho de cura** (corpo degradado ⇒ REFRESH). Inputs
+   normalizados (`TARGET`/`PROFILE`/`STACK`/source) ou o teste vira flaky.
+
+   > **⚠️ BYTE-IDENTIDADE SOZINHA É VACUOSA (rail r1 P1).** Se o gerador
+   > compartilhado for acidentalmente baseado no heredoc QUEBRADO do upgrade
+   > atual, install e upgrade produzem o MESMO ponteiro errado: bytes
+   > idênticos, digest bate com o disco, classificação vira `pristine` e o
+   > `OWN-0074` fica verde — vacuosamente. O teste EXIGE, além da identidade,
+   > asserções de CONTEÚDO: `{{PROTOCOL_SOURCE}}` **ausente** e a fonte
+   > resolvida esperada **presente**, após install, upgrade E migração/cura.
+5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
+   como base; ela já reproduz o defeito.
+
+**Gate W2 (o anterior era vacuoso — este não):** o digest gravado para
+`PROTOCOL.md` **bate com os bytes no disco**, o ponteiro deixa de classificar
+`edited` no caminho comum, e **o `OWN-0074` fica VERDE** — o conjunto
+esperado de vermelhos encolhe para `{OWN-0016, OWN-0024, OWN-0027}`.
+
+> **Ordem obrigatória (QA must-fix 1):** o W2 tem de atualizar
+> `ownership-expected-reds.txt` **no mesmo pack**. Se o W1 landar o gate do
+> AC-5 antes, a primeira CI após o W2 falha por "o conjunto encolheu" — que é
+> o gate funcionando, mas bloqueando trabalho correto.
+
+### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
+
+Registrar como contrato:
+- que `ABORT_SURFACE` é **resultado de OBSERVAÇÃO do harness**, e não um
+  membro do enum de decisão — a função nunca o devolve (QA advisory 3). Sem
+  essa distinção o ADR contradiz o código;
+- as **10 dimensões** e o enum final (**4 vereditos** após o colapso da OQ-9
+  ratificado pelo Owner: `DELIVER · REFRESH · PRESERVE_OWNED ·
+  PRESERVE_UNOWNED`; `ABORT_SURFACE` é **falha de execução**, não veredito);
+- **INV-1..INV-4** (as quatro invariantes cross-surface);
+- a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
+  `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
+  é a que mais convida um "conserto" futuro;
+- que o `ADR-155-AMEND-1` é **emendado**, não revogado;
+- as células conhecidas-abertas com causa, **corretamente classificadas E no
+  tempo certo (rail r1 P2 — o ADR nasce no MESMO pack que fecha o `0074`):**
+  abertas após este pack = `{OWN-0016, OWN-0024, OWN-0027}` (`0024`/`0027` =
+  defeito do TESTE; `0016` = PRODUTO); **`OWN-0074` entra como defeito de
+  PRODUTO FECHADO por este pack** (era a INV-4 se manifestando no digest —
+  ver §W2), registrado como histórico, não como aberto. Um ADR que listasse
+  4 abertas estaria stale no momento da criação.
+
+**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
+novo muda a contagem — regenerar as superfícies derivadas).
+
+## 3. Fronteira canônica
+
+| Superfície | Guard | Onda |
+|---|---|---|
+| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
+| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
+| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
+| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
+
+**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
+cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
+staged, o Owner assina uma vez.
+
+## 4. Critérios de aceite
+
+- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
+- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros — **JÁ ESTAVA** (`:15`, `:54`); o AC vira uma asserção de regressão, não trabalho.
+- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
+- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly** — exige CRIAR o job nightly (não existe `schedule:` hoje) e lembrar que `schedule:` ignora `paths:`.
+- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina. **O passo é o SCRIPT do §W1.4** (rc semântico + `HARNESS-ERR=0` exigido + diff de conjunto), nunca `--map`.
+- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico E com conteúdo certo** (token literal AUSENTE, fonte resolvida PRESENTE — rail r1 P1), com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
+- [ ] **AC-6b** Adotante com corpo DEGRADADO (fingerprint exato de corpo que o framework produziu — NUNCA substring; não-match preserva) é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
+- [ ] **AC-6c** O gerador consome `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — não criar campo novo), com fallback D3 declarado só para estados antigos/ausentes; verificar que o upgrade preserva `request.placeholders`.
+- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
+- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
+- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
+
+## 5. Regras do run (herdadas, custaram caro)
+
+1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
+   `git diff HEAD` aplicado se houver sujeira relevante.
+2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
+3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
+   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
+   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
+4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
+   defeitos do PLAN-167 foram do INSTRUMENTO
+   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
+5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
+   gerador com 1 de 3 callers convertidos custou 24 regressões.
+6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
+   PLAN-166 suja.
+7. **Esperar por ARTEFATO, nunca por `pgrep`.**
+8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
+9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.
+
+## 6. Riscos
+
+| Risco | Mitigação |
+|---|---|
+| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
+| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
+| Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
+| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: persistir PROTOCOL_SOURCE; hoje a intenção do adotante NÃO é gravada |
+| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
+| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
+
+## 7. Registro de execução
+
+<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
+
+- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
+  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
+  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
+- **S297 (07/08, retomada):** commit `11cd4f6` pushado. Claims mecânicas do
+  plano re-verificadas na árvore viva — **todas conferem** (filtros `:15`/`:54`,
+  4 paths com grep=0, zero `schedule:`, `fetch-depth:1` em `:101`, header do
+  baseline com paths de máquina, 6 células protocol+upgrade sem REFRESH/DELIVER,
+  NOTE do `--map` em `test-ownership-table.sh:690`, `_SPEC_PRISTINE_FINGERPRINTS`
+  presente, `PROTOCOL_SOURCE` não persistido, sonda INV-4 presente).
+- **Decisões do Owner (07/08, registradas antes de codar):**
+  - **D1 (W2 direção): opção (b)** — gerador compartilhado único que
+    install/upgrade chamam.
+  - **D2 (célula da cura): a tabela GANHA linhas novas** — `live_content`
+    ganha o valor `degraded` (corpo com `{{PROTOCOL_SOURCE}}` literal = lixo
+    do próprio framework) ⇒ células novas com veredito `REFRESH` (com backup).
+    Só ADIÇÃO; os 62 vereditos existentes ficam intocados. O anti-objetivo de
+    §0 cede formalmente neste ponto, no molde do precedente r20.
+  - **D3 (fallback PROTOCOL_SOURCE): extrair do ponteiro são** no disco e
+    persistir; se degradado (literal), usar a fonte resolvida do upgrade +
+    backup + aviso. Nunca renomear silenciosamente um ponteiro são.
+  - **D4 (nightly): workflow NOVO** `ownership-nightly.yml` (schedule próprio,
+    timeout próprio, zero guards nos jobs existentes do `smoke-install.yml`).
+- **Rail codex:** 1ª invocação (18:02) foi mal-escopada — diff era um comentário
+  inerte sobre draft pré-debate; preservada como `rail/codex-r0-misscoped.md`,
+  NÃO conta para o teto do AC-8. r1 re-escopado disparado (plano inteiro como
+  diff staged sobre baseline com sujeira aplicada, clone overlay em scratchpad).
+- **Rail r1 (re-escopado) CONSUMIDO:** 4 P1 + 3 P2, **7 aceitos / 0
+  refutados**, todos verificados contra o código antes de aceitar
+  (`rail/codex-r1.md`). Destaque de governança: o P1 "fonte de verdade"
+  **derrubou a verificação do debate** — o security checou
+  `request.PROTOCOL_SOURCE` (top-level, inexistente) e "corrigiu" uma claim
+  CERTA para errada; `install.sh:2523` + writer provam que
+  `request.placeholders.PROTOCOL_SOURCE` É persistido (UNION entre runs).
+  Fixes aplicados como linhas: §0 (sonda = evidência histórica), §W1.2
+  (snippet consome `--print-legacy-tag`), §W1.4 (SCRIPT concreto do gate),
+  §W2.2 (fingerprint exato, nunca substring), §W2.3 (consumir chave
+  existente), §W2.4 (asserções de conteúdo anti-vacuidade), §W3 (0074
+  fechado histórico, 3 abertas), AC-5/6/6b/6c/7.
+- **Decisões amendadas pelos achados:** D2 ganha semântica fixa
+  (`degraded` = fingerprint exato); D3 vira fallback-only (a fonte primária
+  é a chave já persistida).
+- **Próxima ação:** rail r2 sobre o plano amendado → W1 item 1 (path filters
+  + `ownership-nightly.yml`), em clone overlay (`plan168-dev` já preparado).

exec
/bin/zsh -lc "printf '%s\\n' '--- workflow ---'; nl -ba .github/workflows/smoke-install.yml | sed -n '1,180p'; printf '%s\\n' '--- ownership harness options / summary ---'; grep -nE 'print-legacy|--map|HARNESS-ERR|GREEN=|ownership-baseline|legacy_pristine|v1\\.2\\.0' scripts/tests/test-ownership-table.sh | head -120; printf '%s\\n' '--- decision rows protocol upgrade ---'; awk -F '\\t' 'NR==1 || (tolower("'$0) ~ /protocol/ && tolower($0) ~ /upgrade/)'"' scripts/tests/ownership_table.tsv | cat -n; printf '%s\\n' '--- protocol source refs ---'; grep -n 'PROTOCOL_SOURCE\\|HASH_CANONICAL_POINTER\\|_refresh_protocol_pointer\\|PRESERVE_OWNED' scripts/install.sh scripts/upgrade.sh | head -240" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
--- workflow ---
     1	name: Smoke Install
     2	
     3	on:
     4	  pull_request:
     5	    paths:
     6	      - "scripts/install.sh"
     7	      - "scripts/upgrade.sh"
     8	      # PLAN-161 (CI wiring): upgrade oracles + the manifest lib they
     9	      # exercise — keep BOTH filter lists (pull_request + push) in sync.
    10	      - "scripts/_framework_manifest_set.sh"
    11	      # The ownership + parity e2e call _hash_file/_hash_stdin from here, and
    12	      # this workflow is their ONLY CI execution — without the helper in the
    13	      # filter, a PR touching only it skips the gate entirely (codex W1
    14	      # round 10, P2: the "red gate nobody runs" class, one level deeper).
    15	      - "scripts/_hash_lib.sh"
    16	      - "scripts/tests/test-upgrade-dryrun-identity.sh"
    17	      - "scripts/tests/test-upgrade-exclusions.sh"
    18	      - "scripts/tests/smoke-install.sh"
    19	      # PLAN-166 F4 (OQ-4): the install/upgrade parity e2e and its classifier.
    20	      # The finding this closes is "a red gate nobody runs" (5th instance) --
    21	      # an unwired test is the same as no test.
    22	      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
    23	      - "scripts/tests/_parity_classify.py"
    24	      # PLAN-166 F3 (ADR-155-AMEND-1): delivery-record ownership e2e —
    25	      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
    26	      # rule as the parity e2e above).
    27	      - "scripts/tests/test-upgrade-spec-ownership.sh"
    28	      - "templates/**"
    29	      # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
    30	      # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
    31	      # parity event, not just the CLI contract doc.
    32	      - "SPEC/v1/**"
    33	      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
    34	      # PR touching just one of these would otherwise skip the regression.
    35	      - "scripts/doctor.sh"
    36	      - ".claude/.framework-version"
    37	      - ".claude/scripts/check-framework-updates.sh"
    38	      - ".github/workflows/smoke-install.yml"
    39	      # PLAN-006 Phase 1 (Sprint 6): Adapter Layer migration changes
    40	      # install-time expectations (hook import paths, contract). Scope
    41	      # broadened for the sprint; narrow back post-Sprint-7 closeout.
    42	      - ".claude/hooks/**"
    43	  push:
    44	    branches:
    45	      - main
    46	    paths:
    47	      # KEEP IDENTICAL to the pull_request list above. The two had already
    48	      # drifted (push was missing SPEC/v1 and this workflow file); PLAN-166 F4
    49	      # re-syncs them, because a filter that fires on the PR and not on the
    50	      # merge is a gate with a hole in it.
    51	      - "scripts/install.sh"
    52	      - "scripts/upgrade.sh"
    53	      - "scripts/_framework_manifest_set.sh"
    54	      - "scripts/_hash_lib.sh"
    55	      - "scripts/tests/test-upgrade-dryrun-identity.sh"
    56	      - "scripts/tests/test-upgrade-exclusions.sh"
    57	      - "scripts/tests/smoke-install.sh"
    58	      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
    59	      - "scripts/tests/_parity_classify.py"
    60	      - "scripts/tests/test-upgrade-spec-ownership.sh"
    61	      - "templates/**"
    62	      - "SPEC/v1/**"
    63	      - "scripts/doctor.sh"
    64	      - ".claude/.framework-version"
    65	      - ".claude/scripts/check-framework-updates.sh"
    66	      - ".github/workflows/smoke-install.yml"
    67	      - ".claude/hooks/**"
    68	
    69	concurrency:
    70	  group: smoke-install-${{ github.ref }}
    71	  cancel-in-progress: true
    72	
    73	jobs:
    74	  smoke:
    75	    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
    76	    if: vars.CEO_SOTA_DISABLE != '1'
    77	    runs-on: ubuntu-latest
    78	    # PLAN-161: 5 -> 8 — headroom for the two upgrade oracles (each runs
    79	    # full install + upgrade legs against fixture adopter repos).
    80	    # PLAN-166 F4: 8 -> 20. MEASURED, not guessed. The parity e2e runs 2 full
    81	    # install legs + 1 upgrade leg PER ceremony mode, and the positive control
    82	    # runs the same again with a planted divergence: 12 install/upgrade
    83	    # operations added to this job. Local wall time (Darwin arm64, 16 cores,
    84	    # 2026-08-05): gate 122s + control 118s = 240s. A 2-core ubuntu-latest
    85	    # runner is the usual 2-3x slower, i.e. 8-12 min of NEW work on top of the
    86	    # ~5 min this job already spent. 15 would sit inside the noise band, and
    87	    # the perf-gate N=20 flake (PLAN-159) was exactly that mistake. Re-tighten
    88	    # once real CI runs give a p95.
    89	    # PLAN-166 F3 (assembler): 20 -> 25. The spec-ownership e2e adds 4 more
    90	    # installs + 3 upgrades (S1-S8; ~3-4 min local per the W1-C measurement),
    91	    # i.e. up to ~8-10 more CI minutes at the same 2-3x factor. Same
    92	    # anti-flake sizing rule as the F4 bump above.
    93	    timeout-minutes: 25
    94	    permissions:
    95	      contents: read
    96	    steps:
    97	      - name: Checkout
    98	        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
    99	        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
   100	        with:
   101	          fetch-depth: 1
   102	
   103	      # PLAN-166 F4: the parity e2e's historical leg installs from a PINNED
   104	      # TAG. `fetch-depth: 1` produces a checkout with NO tags, so the pin
   105	      # would not resolve and the gate would die before comparing a single
   106	      # tree - "it passes on my clone" is precisely the hole this test exists
   107	      # to close. The pin is READ FROM THE TEST (--print-pin) so the workflow
   108	      # never becomes a second copy of that truth.
   109	      - name: Fetch the parity pin tag
   110	        run: |
   111	          set -euo pipefail
   112	          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
   113	          echo "parity historical pin: $PIN"
   114	          git fetch --no-tags --depth 1 origin "+refs/tags/$PIN:refs/tags/$PIN"
   115	          git rev-parse --verify "refs/tags/$PIN^{commit}"
   116	
   117	      - name: Setup Python 3.11
   118	        # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
   119	        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
   120	        with:
   121	          python-version: "3.11"
   122	
   123	      - name: Install jq (for settings.json merge)
   124	        run: |
   125	          set -euo pipefail
   126	          if ! command -v jq >/dev/null 2>&1; then
   127	            sudo apt-get update -qq
   128	            sudo apt-get install -y -qq jq
   129	          fi
   130	          jq --version
   131	
   132	      - name: Run smoke install
   133	        run: |
   134	          set -euo pipefail
   135	          bash scripts/tests/smoke-install.sh
   136	
   137	      # PLAN-161 upgrade oracles (green only once the U1/U2/U3 upgrade.sh
   138	      # fixes are in-tree — land atomically with them).
   139	      - name: Upgrade oracle — --dry-run identity (U1)
   140	        run: |
   141	          set -euo pipefail
   142	          bash scripts/tests/test-upgrade-dryrun-identity.sh
   143	
   144	      - name: Upgrade oracle — exclusion parity + opt-in purge (U2/U3)
   145	        run: |
   146	          set -euo pipefail
   147	          bash scripts/tests/test-upgrade-exclusions.sh
   148	
   149	      # WS4-user-ceremony-leg
   150	      - name: Install with --ceremony user (governance rc=0 + no out-of-.claude writes)
   151	        run: |
   152	          set -euo pipefail
   153	          U="$(mktemp -d)"
   154	          ( cd "$U" && git init -q )
   155	          CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
   156	            bash scripts/install.sh "$U" --ceremony user
   157	          echo '--- validate-governance.sh (user) ---'
   158	          ( cd "$U" && bash .claude/scripts/validate-governance.sh )
   159	          echo '--- assert only .claude/ at top level ---'  # WS4-sc2010-glob
   160	          extra=""
   161	          for _e in "$U"/* "$U"/.[!.]* "$U"/..?*; do
   162	            [ -e "$_e" ] || continue
   163	            _b="$(basename "$_e")"
   164	            case "$_b" in .claude|.git) continue ;; esac
   165	            extra="$extra $_b"
   166	          done
   167	          if [ -n "$extra" ]; then
   168	            echo "::error::--ceremony user wrote outside .claude/:$extra"
   169	            exit 1
   170	          fi
   171	          echo 'user-ceremony leg: PASS'
   172	
   173	      # PLAN-166 F4 (OQ-4) - install/upgrade parity on the RESULTING TREES,
   174	      # per ceremony mode. NO continue-on-error, deliberately: the assertion
   175	      # this replaces was dead twice over (tautological AND wired into no
   176	      # workflow), and an escape hatch here would reinstate exactly that.
   177	      # Exit 2 (KNOWN-OPEN) is a FAILURE too - it NAMES the outstanding
   178	      # PLAN-166 W1 prerequisites instead of skipping them silently.
   179	      - name: Install/upgrade parity e2e (maintainer + user ceremony)
   180	        run: |
--- ownership harness options / summary ---
16:#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
41:    --map)  MAP_ONLY=1; shift ;;
351:    legacy_pristine)
352:      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
355:      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
356:        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
357:        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
363:      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
366:    legacy_pristine_partial)
372:      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
373:        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
377:      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
681:echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"
683:# --map is a REPORTING mode, never a gate. Suppressing a non-zero exit is its
690:    echo "NOTE: --map is a REPORTING mode and is exiting 0 despite RED=$FAIL ERR=$ERR." >&2
691:    echo "      Do NOT use --map in a gate. Run without it to get a pass/fail exit." >&2
--- decision rows protocol upgrade ---
     1	# PLAN-167 — ownership decision table. THIS FILE IS THE TRUTH.
     2	OWN-0032	protocol	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: no non-regular guard; cat > fails and set -e ABORTS the run
     3	OWN-0033	protocol	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: FIFO blocks the run; sibling of r9-F3/r2-F3
     4	OWN-0034	protocol	hash	symlink	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: cat > follows the leaf symlink OUTSIDE the target
     5	OWN-0071	protocol	hash	regular	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r7-F2	analogous PROTOCOL skip
     6	OWN-0072	protocol	hash	regular	edited	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r9-F2	flag alone re-baselines the customized pointer
     7	OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
--- protocol source refs ---
scripts/install.sh:401:# {{PROTOCOL_SOURCE}} substitution. Resolved (CLI > env > $SOURCE_DIR
scripts/install.sh:403:# literal `{{PROTOCOL_SOURCE}}` marker.
scripts/install.sh:404:PH_PROTOCOL_SOURCE="${CEO_PROTOCOL_SOURCE:-}"
scripts/install.sh:517:    --protocol-source)     PH_PROTOCOL_SOURCE="${2:-}";    shift 2 ;;
scripts/install.sh:656:# PLAN-085 Wave A.5 deterministic default — point PROTOCOL_SOURCE at
scripts/install.sh:658:# --protocol-source / CEO_PROTOCOL_SOURCE if their framework lives
scripts/install.sh:662:if [[ -z "$PH_PROTOCOL_SOURCE" ]]; then
scripts/install.sh:663:  PH_PROTOCOL_SOURCE="$SOURCE_DIR"
scripts/install.sh:1889:  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
scripts/install.sh:1896:  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
scripts/install.sh:1910:{{PROTOCOL_SOURCE}}/PROTOCOL.md
scripts/install.sh:1912:Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
scripts/install.sh:1916:  ( cd {{PROTOCOL_SOURCE}} && git pull )
scripts/install.sh:1917:  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
scripts/install.sh:1983:  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
scripts/install.sh:2523:    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
scripts/upgrade.sh:1538:_refresh_protocol_pointer() {
scripts/upgrade.sh:1553:{{PROTOCOL_SOURCE}}/PROTOCOL.md
scripts/upgrade.sh:1555:Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
scripts/upgrade.sh:1559:  ( cd {{PROTOCOL_SOURCE}} && git pull )
scripts/upgrade.sh:1560:  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
scripts/upgrade.sh:1613:    PRESERVE_OWNED)
scripts/upgrade.sh:1913:    PRESERVE_OWNED)
scripts/upgrade.sh:2068:    PRESERVE_OWNED)
scripts/upgrade.sh:3041:  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
scripts/upgrade.sh:3062:  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
scripts/upgrade.sh:3066:  _refresh_protocol_pointer

exec
/bin/zsh -lc "printf '%s\\n' '--- workflow remaining ---'; nl -ba .github/workflows/smoke-install.yml | sed -n '173,300p'; printf '%s\\n' '--- harness header/options and output ---'; nl -ba scripts/tests/test-ownership-table.sh | sed -n '1,75p'; nl -ba scripts/tests/test-ownership-table.sh | sed -n '620,705p'; printf '%s\\n' '--- baseline map ---'; nl -ba scripts/tests/ownership-baseline-map.txt | sed -n '1,24p'; printf '%s\\n' '--- table header + protocol rows raw ---'; grep -nE '"'^#|''^OWN-003[234]|''^OWN-007[124]'"' scripts/tests/ownership_table.tsv; printf '%s\\n' '--- install pointer generation ---'; nl -ba scripts/install.sh | sed -n '1860,2005p'; printf '%s\\n' '--- upgrade pointer refresh ---'; nl -ba scripts/upgrade.sh | sed -n '1500,1645p';" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
--- workflow remaining ---
   173	      # PLAN-166 F4 (OQ-4) - install/upgrade parity on the RESULTING TREES,
   174	      # per ceremony mode. NO continue-on-error, deliberately: the assertion
   175	      # this replaces was dead twice over (tautological AND wired into no
   176	      # workflow), and an escape hatch here would reinstate exactly that.
   177	      # Exit 2 (KNOWN-OPEN) is a FAILURE too - it NAMES the outstanding
   178	      # PLAN-166 W1 prerequisites instead of skipping them silently.
   179	      - name: Install/upgrade parity e2e (maintainer + user ceremony)
   180	        run: |
   181	          set -euo pipefail
   182	          bash scripts/tests/test-install-upgrade-parity-e2e.sh
   183	
   184	      # Control of the control (AC-4). With ONE backup_and_replace line deleted
   185	      # from a COPY of upgrade.sh, the gate above must come back RED in EVERY
   186	      # ceremony mode. rc must be exactly 1: rc 0/2 means the gate went blind,
   187	      # rc 9 means the plant stopped biting (vacuous control). Both fail here.
   188	      # This step MUST stay AFTER the plain gate: if the un-planted run were
   189	      # already fatal, rc=1 here would prove nothing about the plant.
   190	      - name: Install/upgrade parity - positive control (planted divergence)
   191	        run: |
   192	          set -uo pipefail
   193	          rc=0
   194	          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
   195	            --positive-control > /tmp/parity-control.log 2>&1 || rc=$?
   196	          if [ "$rc" -ne 1 ]; then
   197	            cat /tmp/parity-control.log
   198	            echo "::error::parity positive control returned rc=$rc, expected 1 - the planted install/upgrade divergence did NOT turn the gate red, so the gate above proves nothing"
   199	            exit 1
   200	          fi
   201	          # Second factor, LOAD-BEARING (re-pass closure): under `set -uo
   202	          # pipefail` (no -e) a non-matching grep would NOT fail the step, so
   203	          # an rc=1 from a failure UNRELATED to the plant (log with none of
   204	          # the plant markers) would pass — the registered-vacuous class
   205	          # (S292) this step exists to close. Demand plant evidence or fail.
   206	          grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control.log || {
   207	            cat /tmp/parity-control.log
   208	            echo "::error::rc=1 but the log carries no PLANTED/per-mode-verdict evidence - the control went red for an unrelated reason, which proves nothing about the plant (vacuous control)"
   209	            exit 1
   210	          }
   211	          echo "positive control OK: planted divergence -> exit 1 in every ceremony mode"
   212	
   213	      # PLAN-166 F3 (ADR-155-AMEND-1, AC-3) — delivery-record ownership of
   214	      # the three conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
   215	      # .claude/.framework-version) across install -> upgrade -> doctor ->
   216	      # updater. Scenarios S1-S8 incl. the forced-refresh route (S2), the
   217	      # legacy ADOPTER-FORK preserve (S4) and the marker-first updater
   218	      # regression (S6). Same wiring rationale as the parity e2e above:
   219	      # scripts/tests/*.sh runs ONLY here — unwired = no test. NO
   220	      # continue-on-error, deliberately.
   221	      - name: Upgrade SPEC/marker delivery-record ownership (S1-S8)
   222	        run: |
   223	          set -euo pipefail
   224	          bash scripts/tests/test-upgrade-spec-ownership.sh
   225	
   226	      - name: Assert npx/npm shim contract (if present)
   227	        # Phase 4 deliverable; skip if directory missing
   228	        run: |
   229	          set -euo pipefail
   230	          if [[ -d "npm" ]]; then
   231	            # Check no runtime deps
   232	            if [[ -f npm/package.json ]]; then
   233	              deps=$(jq '.dependencies // {} | length' npm/package.json)
   234	              if [[ "$deps" -ne 0 ]]; then
   235	                echo "::error::ceo-orchestration must ship with 0 runtime deps (got $deps)"
   236	                exit 1
   237	              fi
   238	              echo "OK: npm shim has zero runtime dependencies"
   239	            fi
   240	          else
   241	            echo "npm/ shim not yet present — skipping"
   242	          fi
--- harness header/options and output ---
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-167 W0.3 — ownership decision table runner.
     4	#
     5	# Executes EVERY legal cell of scripts/tests/ownership_table.tsv against the
     6	# REAL scripts/install.sh and scripts/upgrade.sh. There is no mock of the
     7	# subject under test: the fixture is a real target tree, the run is a real
     8	# invocation, and the verdict is DERIVED from observable state, never parsed
     9	# out of prose.
    10	#
    11	# Reasoning + dimension/enum definitions: docs/ownership-decision-table.md
    12	#
    13	# Usage:
    14	#   test-ownership-table.sh              run every row
    15	#   test-ownership-table.sh --only OWN-0013
    16	#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
    17	#   test-ownership-table.sh --list       list row ids and exit
    18	#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
    19	#
    20	# Exit: 0 = every row matched its expected pair. 1 = at least one mismatch.
    21	#       2 = harness/usage error (never confused with a row failure).
    22	#
    23	# NOT `set -e`: this harness OBSERVES scripts that are expected to fail on
    24	# some rows. Dying on their exit status would erase the observation.
    25	# =============================================================================
    26	set -uo pipefail
    27	
    28	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    29	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    30	TSV="$SCRIPT_DIR/ownership_table.tsv"
    31	
    32	CELL_TIMEOUT="${CELL_TIMEOUT:-60}"
    33	ONLY=""
    34	MAP_ONLY=0
    35	LIST_ONLY=0
    36	KEEP=0
    37	
    38	while [[ $# -gt 0 ]]; do
    39	  case "$1" in
    40	    --only) ONLY="${2:-}"; shift 2 ;;
    41	    --map)  MAP_ONLY=1; shift ;;
    42	    --list) LIST_ONLY=1; shift ;;
    43	    --keep) KEEP=1; shift ;;
    44	    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    45	    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
    46	  esac
    47	done
    48	
    49	[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
    50	
    51	# --- framework hash helpers (the same ones the scripts use) ------------------
    52	# shellcheck source=/dev/null
    53	. "$REPO_ROOT/scripts/_hash_lib.sh" 2>/dev/null || {
    54	  echo "ERROR: cannot source scripts/_hash_lib.sh" >&2; exit 2; }
    55	command -v _hash_file  >/dev/null 2>&1 || { echo "ERROR: _hash_file missing"  >&2; exit 2; }
    56	command -v _hash_stdin >/dev/null 2>&1 || { echo "ERROR: _hash_stdin missing" >&2; exit 2; }
    57	
    58	# --- scratch ----------------------------------------------------------------
    59	# NEVER $HOME, NEVER inside the repo (PLAN-167 W0.3 hard requirement).
    60	WORK="$( mktemp -d "${TMPDIR:-/tmp}/plan167-own.XXXXXX" )" || exit 2
    61	T="$WORK/t"                 # the ONE target path every row uses (see §fixtures)
    62	cleanup() {
    63	  [[ "$KEEP" -eq 1 ]] && { echo "scratch kept: $WORK" >&2; return; }
    64	  chmod -R u+w "$WORK" 2>/dev/null || true
    65	  rm -rf "$WORK" 2>/dev/null || true
    66	}
    67	trap cleanup EXIT
    68	
    69	# --- portable timeout -------------------------------------------------------
    70	# macOS ships no timeout(1). A cell that hangs (the FIFO class) must be killed,
    71	# not waited on — two separate defects in this space were a blocking cp.
    72	_TIMEOUT_BIN=""
    73	if command -v timeout  >/dev/null 2>&1; then _TIMEOUT_BIN="timeout"
    74	elif command -v gtimeout >/dev/null 2>&1; then _TIMEOUT_BIN="gtimeout"; fi
    75	
   620	  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac
   621	
   622	  # An escape outranks the verdict comparison. A row whose pair matches while
   623	  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
   624	  # exact damage class this table exists to prevent, and calling that GREEN
   625	  # would be the instrument concealing a data loss.
   626	  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
   627	    status="ESCAPE"; FAIL=$((FAIL+1))
   628	  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
   629	    status="GREEN"; PASS=$((PASS+1))
   630	  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
   631	    status="AMBIG"; AMBIG=$((AMBIG+1))
   632	  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
   633	    status="TIMEOUT"; FAIL=$((FAIL+1))
   634	  else
   635	    FAIL=$((FAIL+1))
   636	  fi
   637	
   638	  MAP_LINES+="$( printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
   639	      "$id" "$status" "$exp_verdict" "$exp_hash" "$got_verdict" "$got_hash" "$rc" "$origin" )"$'\n'
   640	}
   641	
   642	# =============================================================================
   643	# Main
   644	# =============================================================================
   645	if [[ "$LIST_ONLY" -eq 1 ]]; then
   646	  awk -F'\t' '!/^#/ && $1!="id" && NF>1 {print $1"\t"$13}' "$TSV"
   647	  exit 0
   648	fi
   649	
   650	echo "== PLAN-167 ownership decision table =="
   651	echo "   table:  $TSV"
   652	echo "   source: $REPO_ROOT"
   653	echo "   scratch:$WORK"
   654	echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
   655	echo ""
   656	
   657	# Prime the canonical pointer digest for $T from a real install. Structurally
   658	# fresh rows build no base, so without this the protocol candidate would be
   659	# unavailable exactly where it is needed.
   660	_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }
   661	
   662	
   663	# Rows are consumed in file order; the map is sorted by id at emit time so the
   664	# output is deterministic regardless of table order.
   665	while IFS=$'\t' read -r id surface prior_record live_type live_content \
   666	      source_has mode ceremony operation skip_requested fault \
   667	      exp_verdict exp_hash origin note; do
   668	  [[ -z "${id:-}" ]] && continue
   669	  case "$id" in \#*|id) continue ;; esac
   670	  # --only takes a comma-separated list: iterating on a cluster of related rows
   671	  # should cost ONE base install, not one per row.
   672	  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
   673	  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
   674	           "$source_has" "$mode" "$ceremony" "$operation" "$skip_requested" \
   675	           "${fault:-none}" "$exp_verdict" "$exp_hash" "$origin" "${note:-}"
   676	done < "$TSV"
   677	
   678	printf '%s' "$MAP_LINES" | LC_ALL=C sort
   679	
   680	echo ""
   681	echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"
   682	
   683	# --map is a REPORTING mode, never a gate. Suppressing a non-zero exit is its
   684	# whole purpose, so a CI step that uses it becomes a dead gate that reports
   685	# success forever. Say so loudly on the way out, on stderr, so the mistake is
   686	# visible in the job log instead of silent (PLAN-168 debate r1, QA must-fix 2).
   687	if [[ "$MAP_ONLY" -eq 1 ]]; then
   688	  if [[ "$FAIL" -gt 0 || "$ERR" -gt 0 ]]; then
   689	    echo "" >&2
   690	    echo "NOTE: --map is a REPORTING mode and is exiting 0 despite RED=$FAIL ERR=$ERR." >&2
   691	    echo "      Do NOT use --map in a gate. Run without it to get a pass/fail exit." >&2
   692	  fi
   693	  exit 0
   694	fi
   695	[[ "$ERR" -gt 0 ]] && exit 2
   696	[[ "$FAIL" -gt 0 ]] && exit 1
   697	exit 0
--- baseline map ---
     1	== PLAN-167 ownership decision table ==
     2	   table:  /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/tests/ownership_table.tsv
     3	   source: /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
     4	   scratch:/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.toQDrn
     5	   timeout:60s/cell   timeout-bin:<fallback>
     6	
     7	OWN-0001   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155
     8	OWN-0002   GREEN   exp=DELIVER         /HASH_CANONICAL_POINTER got=DELIVER         /HASH_CANONICAL_POINTER rc=0   adr-155
     9	OWN-0003   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
    10	OWN-0004   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
    11	OWN-0005   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
    12	OWN-0006   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
    13	OWN-0007   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
    14	OWN-0008   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
    15	OWN-0010   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
    16	OWN-0011   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r1-F1
    17	OWN-0012   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
    18	OWN-0013   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
    19	OWN-0014   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F1
    20	OWN-0015   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
    21	OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F2
    22	OWN-0017   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r3-F2
    23	OWN-0018   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
    24	OWN-0019   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
--- table header + protocol rows raw ---
1:# PLAN-167 — ownership decision table. THIS FILE IS THE TRUTH.
2:# Reasoning lives in docs/ownership-decision-table.md; values live ONLY here.
3:# Conventions: "*" = don't-care (harness instantiates the canonical
4:# representative); "-" = not applicable under a §4 legality rule.
5:# note carries PROSE ONLY. Structured values live in columns (round-1 C1).
6:# `indistinguishable=` / `open=` remain annotations, never dimensions.
38:OWN-0032	protocol	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: no non-regular guard; cat > fails and set -e ABORTS the run
39:OWN-0033	protocol	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: FIFO blocks the run; sibling of r9-F3/r2-F3
40:OWN-0034	protocol	hash	symlink	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: cat > follows the leaf symlink OUTSIDE the target
61:OWN-0071	protocol	hash	regular	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r7-F2	analogous PROTOCOL skip
62:OWN-0072	protocol	hash	regular	edited	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r9-F2	flag alone re-baselines the customized pointer
69:OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
--- install pointer generation ---
  1860	if [[ "$CEREMONY" != "user" ]]; then install_posture_state_ignores; fi  # PLAN-165 CX-3
  1861	
  1862	# ---- 7. Project-local templates (CLAUDE.md, MEMORY.md, .mcp.json — never overwrite) ----
  1863	
  1864	echo ""
  1865	echo "==> Installing project templates"
  1866	_state_record_op "install_project_templates" "ceremony=$CEREMONY"
  1867	if [[ "$CEREMONY" != "user" ]]; then  # WS4-guard-projtmpl
  1868	install_template "templates/CLAUDE.md" "CLAUDE.md"
  1869	install_template "templates/MEMORY.md" "MEMORY.md"
  1870	# PLAN-135 W1 S5-lite: project-scope MCP registration for the Codex
  1871	# pair-rail (the 'codex' server backs the mcp__codex__codex |
  1872	# mcp__codex__codex-reply matchers in settings.json). install_template
  1873	# is idempotent EXISTS->SKIP — an adopter's own .mcp.json is never
  1874	# clobbered. Credentials via ${ENV} expansion only; no secrets on disk.
  1875	# Root-level file => stays inside the WS4-guard-projtmpl maintainer
  1876	# guard (user ceremony writes .claude/ only).
  1877	install_template "templates/.mcp.json" ".mcp.json"
  1878	fi  # WS4-guard-projtmpl
  1879	
  1880	# ---- 8. Drop a pointer to PROTOCOL.md (DevOps-P1-4: relative, not absolute) ----
  1881	
  1882	install_protocol_pointer() {
  1883	  if [[ -e "$TARGET/PROTOCOL.md" ]]; then
  1884	    return 0
  1885	  fi
  1886	
  1887	  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
  1888	  # If the framework repo lives outside the target repo (common case),
  1889	  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
  1890	  # manually. Absolute paths are NOT hardcoded — they break portability
  1891	  # across dev machines and CI runners.
  1892	  #
  1893	  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
  1894	  # framework was copied INTO the target — use a relative pointer. In
  1895	  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
  1896	  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
  1897	  local pointer_body
  1898	  case "$SOURCE_DIR" in
  1899	    "$TARGET"/*)
  1900	      local rel="${SOURCE_DIR#$TARGET/}"
  1901	      pointer_body="The full CEO orchestration protocol lives at:
  1902	./${rel}/PROTOCOL.md
  1903	
  1904	To pull updates:
  1905	  ( cd ./${rel} && git pull )
  1906	  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
  1907	      ;;
  1908	    *)
  1909	      pointer_body="The full CEO orchestration protocol lives at:
  1910	{{PROTOCOL_SOURCE}}/PROTOCOL.md
  1911	
  1912	Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
  1913	(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
  1914	
  1915	To pull updates:
  1916	  ( cd {{PROTOCOL_SOURCE}} && git pull )
  1917	  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
  1918	      ;;
  1919	  esac
  1920	
  1921	  if [[ "$DRY_RUN" -eq 1 ]]; then
  1922	    echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
  1923	    return 0
  1924	  fi
  1925	
  1926	  cat > "$TARGET/PROTOCOL.md" <<EOF
  1927	# Protocol reference
  1928	
  1929	$pointer_body
  1930	EOF
  1931	  echo "    CREATED: PROTOCOL.md (pointer)"
  1932	  _state_record_op "install_protocol_pointer" "PROTOCOL.md"
  1933	  # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
  1934	  # reached when the heredoc actually wrote the pointer (the pre-existing
  1935	  # early-return above never gets here, so an adopter's own root
  1936	  # PROTOCOL.md is never inventoried as framework-owned; r13/r17).
  1937	  _DELIVERED_PROTOCOL=1
  1938	  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
  1939	}
  1940	
  1941	if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto
  1942	
  1943	# ----------------------------------------------------------------------
  1944	# P1-CR-3 / VP-F1: placeholder substitution pass
  1945	# ----------------------------------------------------------------------
  1946	# Iterate over a deterministic list of placeholder files (the ones
  1947	# templates/ writes out) and apply `sed -i` substitutions for every
  1948	# PH_* variable that is non-empty. Anything left as `{{...}}` after the
  1949	# pass is reported with a stderr warning.
  1950	#
  1951	# We restrict the pass to files install.sh actually placed (the
  1952	# templates/* files) to avoid touching user-authored content. If
  1953	# CLAUDE.md / MEMORY.md already existed at target, we leave them alone
  1954	# (install.sh never overwrites them).
  1955	
  1956	# Portable sed -i for GNU + BSD (macOS): write to .tmp and mv.
  1957	portable_sed_inplace() {
  1958	  # $1 = sed script, $2 = file
  1959	  local script="$1" file="$2"
  1960	  local tmp="${file}.ceo-sed-tmp"
  1961	  sed "$script" "$file" > "$tmp" && mv "$tmp" "$file"
  1962	}
  1963	
  1964	# Build the sed script iteratively. Each non-empty placeholder adds an
  1965	# expression. We use `|` as the delimiter so slashes in values (paths)
  1966	# don't break. Values with `|` are escaped.
  1967	build_sed_script() {
  1968	  local script=""
  1969	  _add_sub() {
  1970	    local key="$1" val="$2"
  1971	    if [[ -n "$val" ]]; then
  1972	      # Escape | & \ in the replacement
  1973	      local esc
  1974	      esc="$(printf '%s' "$val" | sed 's/[|&\\]/\\&/g')"
  1975	      script="${script}s|{{${key}}}|${esc}|g;"
  1976	    fi
  1977	  }
  1978	  _add_sub "OWNER_NAME"          "$PH_OWNER_NAME"
  1979	  _add_sub "OWNER_HANDLE"        "$GITHUB_OWNER"
  1980	  _add_sub "PROJECT_NAME"        "$PH_PROJECT_NAME"
  1981	  _add_sub "PROJECT_PATH"        "$PH_PROJECT_PATH"
  1982	  _add_sub "STACK"               "$PH_STACK"
  1983	  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
  1984	  _add_sub "DEPLOY_COMMAND"      "$PH_DEPLOY_COMMAND"
  1985	  _add_sub "DEPLOY_PLATFORM"     "$PH_DEPLOY_PLATFORM"
  1986	  _add_sub "DEPLOY_TARGET"       "$PH_DEPLOY_TARGET"
  1987	  _add_sub "RUNTIME_NOTES"       "$PH_RUNTIME_NOTES"
  1988	  _add_sub "DATABASE"            "$PH_DATABASE"
  1989	  _add_sub "N_BACKEND"           "$PH_N_BACKEND"
  1990	  _add_sub "N_FRONTEND"          "$PH_N_FRONTEND"
  1991	  _add_sub "FRONTEND_STACK"      "$PH_FRONTEND_STACK"
  1992	  _add_sub "FRONTEND_PATH"       "$PH_FRONTEND_PATH"
  1993	  _add_sub "FRONTEND_REPO_PATH"  "$PH_FRONTEND_REPO_PATH"
  1994	  _add_sub "UI_LIBRARY"          "$PH_UI_LIBRARY"
  1995	  _add_sub "STATE_MANAGEMENT"    "$PH_STATE_MANAGEMENT"
  1996	  _add_sub "REALTIME_TRANSPORT"  "$PH_REALTIME_TRANSPORT"
  1997	  _add_sub "CHARTING_LIBRARY"    "$PH_CHARTING_LIBRARY"
  1998	  _add_sub "AUTH_PROVIDER"       "$PH_AUTH_PROVIDER"
  1999	  _add_sub "I18N_FRAMEWORK"      "$PH_I18N_FRAMEWORK"
  2000	  _add_sub "TEST_FRAMEWORK"      "$PH_TEST_FRAMEWORK"
  2001	  _add_sub "TEST_TOOL"           "$PH_TEST_TOOL"
  2002	  _add_sub "TEST_COUNT"          "$PH_TEST_COUNT"
  2003	  _add_sub "LINT_TOOL"           "$PH_LINT_TOOL"
  2004	  _add_sub "CI_TOOL"             "$PH_CI_TOOL"
  2005	  _add_sub "APP_NAME"            "$PH_APP_NAME"
--- upgrade pointer refresh ---
  1500	              rm -f "$TARGET/$_pr_rel"
  1501	            fi
  1502	          fi
  1503	        fi
  1504	      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
  1505	      # Remove the now-empty excluded dirs, children before parents (-depth)
  1506	      # — but never a recorded survivor dir (pre-existing, adopter-held).
  1507	      while IFS= read -r _pr_hit; do
  1508	        [[ -n "$_pr_hit" ]] || continue
  1509	        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
  1510	        # F11a: ancestor-symlink guard first, then -L BEFORE -d (lstat-first
  1511	        # — -d follows a leaf symlink; a preserved excluded symlink-to-dir
  1512	        # must be kept whole and its target never rmdir'd).
  1513	        if _framework_path_excluded "$_pr_rel" \
  1514	           && ! _lg_ancestor_is_symlink "$TARGET" "$_pr_rel" \
  1515	           && [[ ! -L "$TARGET/$_pr_rel" && -d "$TARGET/$_pr_rel" ]]; then
  1516	          if [[ -n "$_lg_survivors" ]] \
  1517	             && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
  1518	            :  # pre-existing excluded dir — keep (F11)
  1519	          else
  1520	            rmdir "$TARGET/$_pr_rel" 2>/dev/null || true
  1521	          fi
  1522	        fi
  1523	      done < <( find "$src" -depth -type d -print 2>/dev/null )
  1524	    fi
  1525	  else
  1526	    cp "$src" "$dst"
  1527	  fi
  1528	  if [[ -n "$_lg_survivors" ]]; then
  1529	    rm -f "$_lg_survivors"
  1530	  fi
  1531	  echo "    UPDATED: $rel_path"
  1532	}
  1533	
  1534	# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
  1535	# framework-derived content (not user data), so preserving it as-is
  1536	# across upgrades traps stale pointers when the framework moves. We
  1537	# regenerate it with the same heuristic install.sh uses.
  1538	_refresh_protocol_pointer() {
  1539	  local pointer="$TARGET/PROTOCOL.md"
  1540	  local body
  1541	  case "$SOURCE_DIR" in
  1542	    "$TARGET"/*)
  1543	      local rel="${SOURCE_DIR#$TARGET/}"
  1544	      body="The full CEO orchestration protocol lives at:
  1545	./${rel}/PROTOCOL.md
  1546	
  1547	To pull updates:
  1548	  ( cd ./${rel} && git pull )
  1549	  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
  1550	      ;;
  1551	    *)
  1552	      body="The full CEO orchestration protocol lives at:
  1553	{{PROTOCOL_SOURCE}}/PROTOCOL.md
  1554	
  1555	Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
  1556	(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
  1557	
  1558	To pull updates:
  1559	  ( cd {{PROTOCOL_SOURCE}} && git pull )
  1560	  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
  1561	      ;;
  1562	  esac
  1563	
  1564	  # The CANONICAL digest: the hash of exactly what the framework WOULD write.
  1565	  # Computed on every path, because the baseline rewrite must record it even
  1566	  # when the pointer is preserved — recording the customised bytes instead
  1567	  # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
  1568	  _REFRESH_PROTOCOL_CANON_HASH=""
  1569	  if command -v _hash_stdin >/dev/null 2>&1; then
  1570	    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
  1571	  fi
  1572	
  1573	  # ---- OBSERVE -------------------------------------------------------------
  1574	  local _lt _pr _lc
  1575	  _lt="$( _ov_obs_live_type "$pointer" )"
  1576	  _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
  1577	  if [ "$_lt" != "regular" ]; then
  1578	    _lc="-"
  1579	  elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
  1580	       && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
  1581	    _lc="pristine"
  1582	  else
  1583	    _lc="edited"
  1584	  fi
  1585	
  1586	  # ---- DECIDE --------------------------------------------------------------
  1587	  local _pair _verdict
  1588	  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
  1589	                   "$CEREMONY_EFFECTIVE" upgrade none )"; then
  1590	    echo "    WARNING: PROTOCOL.md dimensions are not a legal cell — PRESERVED" >&2
  1591	    return 0
  1592	  fi
  1593	  _verdict="${_pair%% *}"
  1594	  _PROTOCOL_HASH_SOURCE="${_pair##* }"
  1595	
  1596	  # ---- EXECUTE -------------------------------------------------------------
  1597	  # The guards this surface never had are not new branches: they are what the
  1598	  # decision already says. A destination that is not a regular file is
  1599	  # adopter-owned, so the verdict is unowned and nothing is written — which is
  1600	  # exactly the leaf-symlink / directory / FIFO protection SPEC and the marker
  1601	  # acquired during the S296 rounds and the pointer did not.
  1602	  case "$_verdict" in
  1603	    PRESERVE_UNOWNED|OMIT_RECORD)
  1604	      case "$_lt" in
  1605	        symlink) echo "    SKIP: PROTOCOL.md is a symlink — refusing to write THROUGH it (would mutate a path outside the target)" >&2 ;;
  1606	        dir|dir_empty) echo "    SKIP: PROTOCOL.md is a directory — adopter-owned, refusing to write into it" >&2 ;;
  1607	        special) echo "    SKIP: PROTOCOL.md is an unsupported special file — preserved, surface untouched" >&2 ;;
  1608	        *) echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4)" ;;
  1609	      esac
  1610	      return 0
  1611	      ;;
  1612	
  1613	    PRESERVE_OWNED)
  1614	      _PROTOCOL_DELIVERED=1
  1615	      if [ "$_lc" = "edited" ]; then
  1616	        # ADR-155 decision (iii): the verified S238 case. An adopter-customised
  1617	        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
  1618	        # the canonical digest so the next upgrade does not read it as pristine.
  1619	        if [ "$DRY_RUN" -eq 0 ] && [ -f "$pointer" ]; then
  1620	          mkdir -p "$BAK_DIR" 2>/dev/null || true
  1621	          cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1622	        fi
  1623	        echo "    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
  1624	      else
  1625	        echo "    SKIP: PROTOCOL.md pointer (ownership carried forward)"
  1626	      fi
  1627	      return 0
  1628	      ;;
  1629	
  1630	    DELIVER|REFRESH)
  1631	      if [ "$DRY_RUN" -eq 1 ]; then
  1632	        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
  1633	        return 0
  1634	      fi
  1635	      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
  1636	      # Backup-always before the overwrite, even with no baseline manifest —
  1637	      # this is what made the S238 loss recoverable on a FIRST upgrade.
  1638	      if [ -f "$pointer" ]; then
  1639	        mkdir -p "$BAK_DIR" 2>/dev/null || true
  1640	        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1641	        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
  1642	      fi
  1643	      cat > "$pointer" <<EOF
  1644	# Protocol reference
  1645	

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1630,1665p'; printf '%s\\n' '--- install substitution target collection ---'; nl -ba scripts/install.sh | sed -n '2000,2070p'; printf '%s\\n' '--- state writer around install invocation ---'; nl -ba scripts/install.sh | sed -n '2460,2545p'; printf '%s\\n' '--- state helper ph behavior ---'; grep -nE 'ph\\.\\*|placeholders|_state_write|state.*write' scripts/install.sh | head -100; printf '%s\\n' '--- upgrade state placeholder behavior ---'; grep -nE 'placeholders|PROTOCOL_SOURCE|delivery' scripts/upgrade.sh | head -160" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
  1630	    DELIVER|REFRESH)
  1631	      if [ "$DRY_RUN" -eq 1 ]; then
  1632	        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
  1633	        return 0
  1634	      fi
  1635	      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
  1636	      # Backup-always before the overwrite, even with no baseline manifest —
  1637	      # this is what made the S238 loss recoverable on a FIRST upgrade.
  1638	      if [ -f "$pointer" ]; then
  1639	        mkdir -p "$BAK_DIR" 2>/dev/null || true
  1640	        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1641	        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
  1642	      fi
  1643	      cat > "$pointer" <<EOF
  1644	# Protocol reference
  1645	
  1646	$body
  1647	EOF
  1648	      _PROTOCOL_DELIVERED=1
  1649	      echo "    REFRESHED: PROTOCOL.md pointer"
  1650	      return 0
  1651	      ;;
  1652	  esac
  1653	}
  1654	
  1655	# ===========================================================================
  1656	# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
  1657	# refresh + framework version marker refresh.
  1658	# ---------------------------------------------------------------------------
  1659	# Ownership of the three conditional surfaces (PROTOCOL.md, SPEC/v1,
  1660	# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
  1661	# the PRE-upgrade baseline manifest records (the same record install.sh
  1662	# writes and doctor.sh reads) — never from the ceremony alone and never from
  1663	# file presence (r7/r13/r17/r19/r20).
  1664	# ===========================================================================
  1665	_baseline_has_spec_record() {
--- install substitution target collection ---
  2000	  _add_sub "TEST_FRAMEWORK"      "$PH_TEST_FRAMEWORK"
  2001	  _add_sub "TEST_TOOL"           "$PH_TEST_TOOL"
  2002	  _add_sub "TEST_COUNT"          "$PH_TEST_COUNT"
  2003	  _add_sub "LINT_TOOL"           "$PH_LINT_TOOL"
  2004	  _add_sub "CI_TOOL"             "$PH_CI_TOOL"
  2005	  _add_sub "APP_NAME"            "$PH_APP_NAME"
  2006	  _add_sub "SOURCE_FILE_COUNT"   "$PH_SOURCE_FILE_COUNT"
  2007	  _add_sub "LINE_COUNT"          "$PH_LINE_COUNT"
  2008	  _add_sub "LINES"               "$PH_LINES"
  2009	  _add_sub "FILE_COUNT"          "$PH_FILE_COUNT"
  2010	  _add_sub "PAGE_COUNT"          "$PH_PAGE_COUNT"
  2011	  _add_sub "COMPONENT_COUNT"     "$PH_COMPONENT_COUNT"
  2012	  _add_sub "HOOK_COUNT"          "$PH_HOOK_COUNT"
  2013	  _add_sub "BUNDLE_SIZE"         "$PH_BUNDLE_SIZE"
  2014	  _add_sub "CITY"                "$PH_CITY"
  2015	  _add_sub "COUNTRY"             "$PH_COUNTRY"
  2016	  _add_sub "DOMAIN"              "$PH_DOMAIN"
  2017	  _add_sub "FOUNDER_NAME"        "${PH_FOUNDER_NAME:-$PH_OWNER_NAME}"
  2018	  _add_sub "LEGAL_ID"            "$PH_LEGAL_ID"
  2019	  _add_sub "PRODUCTION_URL"      "$PH_PRODUCTION_URL"
  2020	  printf '%s' "$script"
  2021	}
  2022	
  2023	apply_placeholder_substitutions() {
  2024	  local sed_script
  2025	  sed_script="$(build_sed_script)"
  2026	
  2027	  if [[ -z "$sed_script" ]]; then
  2028	    echo ""
  2029	    echo "==> Placeholder substitution: no values supplied (use --owner / --project / env vars)"
  2030	    echo "    Template files ship as-is. Edit them manually or re-run install.sh with flags."
  2031	    return 0
  2032	  fi
  2033	
  2034	  echo ""
  2035	  echo "==> Applying placeholder substitutions"
  2036	  _state_record_op "apply_placeholder_substitutions" ""
  2037	
  2038	  # Files we are allowed to rewrite — strictly the template-sourced files
  2039	  # that install.sh just placed. We check existence first.
  2040	  #
  2041	  # We intentionally do NOT touch:
  2042	  #   - .claude/settings.json          (user-edited hook registry)
  2043	  #   - .claude/plans/PLAN-*.md        (user's own plans)
  2044	  #   - .claude/adr/ADR-*.md           (user's own ADRs)
  2045	  #   - .claude/scripts/*              (executable code; placeholders
  2046	  #     inside .py docstrings are instructional, not install-time)
  2047	  #   - .claude/hooks/*                (same reason)
  2048	  # WS4-explicit-files-partition: maintainer rewrites root + docs/ +
  2049	  # .claude/ template files; user ceremony rewrites ONLY .claude/ files so
  2050	  # a real adopter repo's own root/docs files are never touched.
  2051	  local explicit_files=(
  2052	    "$TARGET/.claude/team.md"
  2053	    "$TARGET/.claude/frontend-team.md"
  2054	    "$TARGET/.claude/agent-metrics.md"
  2055	  )
  2056	  if [[ "$CEREMONY" != "user" ]]; then
  2057	    explicit_files=(
  2058	      "$TARGET/CLAUDE.md"
  2059	      "$TARGET/MEMORY.md"
  2060	      "$TARGET/PROTOCOL.md"
  2061	      "$TARGET/docs/BRANCH-PROTECTION.md"
  2062	      "$TARGET/docs/rotation-log.md"
  2063	      "$TARGET/.claude/team.md"
  2064	      "$TARGET/.claude/frontend-team.md"
  2065	      "$TARGET/.claude/agent-metrics.md"
  2066	    )
  2067	  fi
  2068	
  2069	  local f
  2070	  for f in "${explicit_files[@]}"; do
--- state writer around install invocation ---
  2460	}
  2461	
  2462	
  2463	# ----------------------------------------------------------------------
  2464	# PLAN-153 Wave B item B1 — persist the install-state.
  2465	# ----------------------------------------------------------------------
  2466	# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
  2467	# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
  2468	# RESOLVED placeholder map (CLI > env > deterministic default; empty values
  2469	# omitted) — plus the operation journal for THIS run.
  2470	#
  2471	#   * Atomic: python writes a same-directory tempfile, then os.replace().
  2472	#   * Updated on every run: first_recorded_at + run_count + a bounded
  2473	#     history (last 20 runs) survive re-installs; request/operations
  2474	#     reflect the LATEST run.
  2475	#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
  2476	#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
  2477	#     become upgrade DEFAULTS when its own flags are omitted. A missing or
  2478	#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
  2479	#     path — never an error, never a no-op (debate C back-compat must-fix).
  2480	#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
  2481	#     ADR-155 baseline manifest (whoever can write the target tree can
  2482	#     rewrite it). upgrade.sh charset-validates every replayed value and
  2483	#     falls back on anything suspect; values are data, never eval-ed.
  2484	#   * Fail-open: no python3 / write error => stderr NOTE, install still
  2485	#     succeeds. Dry-run never writes (the "no files modified" promise).
  2486	#   * NOT covered by the baseline-manifest enumeration (like the manifest
  2487	#     dotfile itself), so the upgrade classifier never touches it.
  2488	_write_install_state() {
  2489	  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  2490	  if ! command -v python3 >/dev/null 2>&1; then
  2491	    echo "    NOTE: install-state skipped (python3 not found) — upgrade.sh will use the ADR-155 fallback path" >&2
  2492	    return 0
  2493	  fi
  2494	  local state_file="$TARGET/.claude/.install-state.json"
  2495	  local fw_version=""
  2496	  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
  2497	    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  2498	  fi
  2499	
  2500	  echo ""
  2501	  echo "==> Writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
  2502	
  2503	  # Flat key/value pairs, argv-passed (PLAN-106 G.2.b house pattern: never
  2504	  # source-string interpolation; python3 -I + PYTHONNOUSERSITE=1). Keys with
  2505	  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
  2506	  local pairs=(
  2507	    "target" "$TARGET"
  2508	    "mode" "$MODE"
  2509	    "profile" "$PROFILE"
  2510	    "stack" "$STACK"
  2511	    "stack_explicit" "$STACK_EXPLICIT"
  2512	    "ceremony" "$CEREMONY"
  2513	    "github_owner" "$GITHUB_OWNER"
  2514	    "with_reference_personas" "$WITH_REFERENCE_PERSONAS"
  2515	    "strict_placeholders" "$STRICT_PLACEHOLDERS"
  2516	    "verify" "$VERIFY"
  2517	    "harness" "$HARNESS"
  2518	    "managed_hooks" "$CODEX_MANAGED_HOOKS"
  2519	    "ph.OWNER_NAME" "$PH_OWNER_NAME"
  2520	    "ph.PROJECT_NAME" "$PH_PROJECT_NAME"
  2521	    "ph.PROJECT_PATH" "$PH_PROJECT_PATH"
  2522	    "ph.STACK" "$PH_STACK"
  2523	    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
  2524	    "ph.DEPLOY_COMMAND" "$PH_DEPLOY_COMMAND"
  2525	    "ph.DEPLOY_PLATFORM" "$PH_DEPLOY_PLATFORM"
  2526	    "ph.DEPLOY_TARGET" "$PH_DEPLOY_TARGET"
  2527	    "ph.RUNTIME_NOTES" "$PH_RUNTIME_NOTES"
  2528	    "ph.DATABASE" "$PH_DATABASE"
  2529	    "ph.N_BACKEND" "$PH_N_BACKEND"
  2530	    "ph.N_FRONTEND" "$PH_N_FRONTEND"
  2531	    "ph.FRONTEND_STACK" "$PH_FRONTEND_STACK"
  2532	    "ph.FRONTEND_PATH" "$PH_FRONTEND_PATH"
  2533	    "ph.FRONTEND_REPO_PATH" "$PH_FRONTEND_REPO_PATH"
  2534	    "ph.UI_LIBRARY" "$PH_UI_LIBRARY"
  2535	    "ph.STATE_MANAGEMENT" "$PH_STATE_MANAGEMENT"
  2536	    "ph.REALTIME_TRANSPORT" "$PH_REALTIME_TRANSPORT"
  2537	    "ph.CHARTING_LIBRARY" "$PH_CHARTING_LIBRARY"
  2538	    "ph.AUTH_PROVIDER" "$PH_AUTH_PROVIDER"
  2539	    "ph.I18N_FRAMEWORK" "$PH_I18N_FRAMEWORK"
  2540	    "ph.TEST_FRAMEWORK" "$PH_TEST_FRAMEWORK"
  2541	    "ph.TEST_TOOL" "$PH_TEST_TOOL"
  2542	    "ph.TEST_COUNT" "$PH_TEST_COUNT"
  2543	    "ph.LINT_TOOL" "$PH_LINT_TOOL"
  2544	    "ph.CI_TOOL" "$PH_CI_TOOL"
  2545	    "ph.APP_NAME" "$PH_APP_NAME"
--- state helper ph behavior ---
21:#                                    and {{OWNER_HANDLE}} placeholders (e.g. --github-owner alice).
97:#   --strict-placeholders          Post-install validator: fail install if any
123:#      - .claude/team.md, .claude/frontend-team.md (template with placeholders)
150:#      template files for the placeholders supplied via CLI / env. Any
153:#   8. Lists placeholders the user must fill in.
479:    --strict-placeholders)
646:# Fill in deterministic defaults for placeholders now that $TARGET is known.
953:# ---- 1. Team rosters (always installed — these are templates with placeholders) ----
2045:  #   - .claude/scripts/*              (executable code; placeholders
2073:      echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
2085:  # instructional placeholders). Recurse into the skills tree.
2091:        echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
2115:# Default: warn + continue. --strict-placeholders (or
2119:validate_no_unrendered_placeholders() {
2126:  echo "==> Scanning for unrendered placeholders ({{X}} patterns)"
2127:  _state_record_op "scan_unrendered_placeholders" "strict=$strict"
2162:    echo "    UNRENDERED placeholders found ($found occurrences):"
2169:      echo "    STRICT mode (--strict-placeholders) — failing install." >&2
2173:      echo "    WARN: install continues. Re-run with --strict-placeholders" >&2
2174:      echo "          to fail-closed on unrendered placeholders." >&2
2177:    echo "    OK: no unrendered placeholders detected."
2183:validate_no_unrendered_placeholders
2288:  _state_record_op "write_install_manifest" ".claude/.install-manifest.sha256"
2401:  # (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
2505:  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
2515:    "strict_placeholders" "$STRICT_PLACEHOLDERS"
2622:        oph = pr.get("placeholders")
2640:    "strict_placeholders": vals.get("strict_placeholders", "0") == "1",
2645:    "placeholders": ph,
2678:    echo "    NOTE: install-state write failed — upgrade.sh will use the ADR-155 fallback path (fail-open)" >&2
2787:# Grep for unsubstituted placeholders. Count + list files, then list
--- upgrade state placeholder behavior ---
848:# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
1553:{{PROTOCOL_SOURCE}}/PROTOCOL.md
1555:Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
1559:  ( cd {{PROTOCOL_SOURCE}} && git pull )
1560:  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
1656:# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
1689:# enumerated SPEC/v1, so no historical delivery record can distinguish a
1787:    # delivery as redirected.
1844:# _ov_obs_mode — the delivery mode this run carries. Evidence order: a prior
1867:#     no target SPEC => new delivery; target SPEC with NO record => LEGACY
1917:        symlink/*/*)          echo "    SKIP: SPEC/v1 is the recorded --mode link delivery (target unchanged)" ;;
1939:        echo "    WARNING: SPEC/v1 is not framework-owned (no delivery record, and it" >&2
2072:        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
2086:          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
2091:        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
3056:      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
3070:# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
3119:    # adopter's own file under `.claude/hooks/` — into a framework delivery
3147:  # The decision travels with the delivery flag.
3166:# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
3251:        "placeholders": {},

exec
/bin/zsh -lc "tail -8 scripts/tests/ownership-baseline-map.txt; grep -nE '[[:space:]](RED|AMBIG|TIMEOUT|ESCAPE)[[:space:]]' scripts/tests/ownership-baseline-map.txt; grep -n 'indistinguishable=' scripts/tests/ownership_table.tsv" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
OWN-0080   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r9-F4
OWN-0081   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F3
OWN-0082   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   adr-155-amend-1
OWN-0090   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r7-F1
OWN-0091   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r7-F1

GREEN=58  RED=4  AMBIG=0  HARNESS-ERR=0
21:OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F2
29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_NONE              rc=0   r3-F1
32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_PRIOR_RECORD      rc=0   r4-F5
63:OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
6:# `indistinguishable=` / `open=` remain annotations, never dimensions.
8:OWN-0001	spec	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155	indistinguishable=HASH_TARGET
9:OWN-0002	protocol	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_CANONICAL_POINTER	adr-155	indistinguishable=HASH_TARGET
10:OWN-0003	marker	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155-amend-1	indistinguishable=HASH_TARGET

exec
/bin/zsh -lc "grep -R -n \"_ownership_verdict\" scripts | head -30; grep -nE 'live_content|pristine|edited|ABORT_SURFACE|protocol' scripts/_framework_manifest_set.sh | head -200; nl -ba scripts/_framework_manifest_set.sh | sed -n '730,930p'; printf '%s\\n' '--- unit test ---'; nl -ba scripts/tests/test-ownership-verdict-unit.sh | sed -n '1,260p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
scripts/_framework_manifest_set.sh:292:# _ownership_verdict chooses a hash_source per conditional surface; the writer
scripts/_framework_manifest_set.sh:437:# PLAN-167 — _ownership_verdict: THE ownership decision.
scripts/_framework_manifest_set.sh:472:_ownership_verdict() {
scripts/tests/test-ownership-verdict-unit.sh:3:# PLAN-167 W2 — UNIT oracle for _ownership_verdict().
scripts/tests/test-ownership-verdict-unit.sh:51:command -v _ownership_verdict >/dev/null 2>&1 || {
scripts/tests/test-ownership-verdict-unit.sh:52:  echo "ERROR: _ownership_verdict is not defined in $LIB" >&2
scripts/tests/test-ownership-verdict-unit.sh:79:  got="$( _ownership_verdict "$surface" "$prior_record" "$live_type" \
scripts/upgrade.sh:1588:  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
scripts/upgrade.sh:1752:# _ownership_verdict, and execute what comes back. Everything below answers a
scripts/upgrade.sh:1883:  # world, and the answers go to _ownership_verdict as the nine dimensions.
scripts/upgrade.sh:1898:  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
scripts/upgrade.sh:2057:  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
7:# ".claude/commands" / the install_protocol_pointer at install.sh:1425) while
9:# upgrade.sh:654-679 + _refresh_protocol_pointer at :450-486). Those two
117:    # delivery. A `--ceremony user` install SKIPS install_protocol_pointer
363:        # exported by upgrade.sh _refresh_protocol_pointer) so a PRESERVED
444:#   $1 surface        spec | protocol | marker
448:#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
449:#                     | edited | -
464:# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
488:    if [ "$_ov_surface" = "protocol" ] \
512:      protocol) return 1 ;;                                  # R-03: generated, never absent
542:    protocol|marker)
556:  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
559:  # legacy_pristine_partial is deliberately NOT owned: every regular file may
569:      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
588:  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
594:    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
--- unit test ---
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-167 W2 — UNIT oracle for _ownership_verdict().
     4	#
     5	# The same table, the other half of the contract:
     6	#
     7	#   this script            — does the DECISION match the model?   (milliseconds)
     8	#   test-ownership-table.sh — do the callers OBSERVE the dimensions
     9	#                             correctly and EXECUTE the verdict?  (~25 minutes)
    10	#
    11	# Both are required and they fail for different reasons. A wrong decision shows
    12	# up here; a caller that reads the world wrong, or ignores the verdict it was
    13	# handed, only shows up there.
    14	#
    15	# This one exists because of how PLAN-167 was caused. In S296 the only
    16	# instrument was the slow one, one cell per ~40-minute round — a loop too long
    17	# to converge in. An oracle that answers in milliseconds is what makes
    18	# "drive the map to 100% green" a normal edit-run cycle instead of an
    19	# overnight gamble.
    20	#
    21	# Usage:
    22	#   test-ownership-verdict-unit.sh            every row
    23	#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
    24	#   test-ownership-verdict-unit.sh --quiet    only the summary
    25	#
    26	# Exit: 0 all rows match · 1 at least one mismatch · 2 harness/usage error.
    27	# =============================================================================
    28	set -uo pipefail
    29	
    30	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    31	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    32	TSV="$SCRIPT_DIR/ownership_table.tsv"
    33	LIB="$REPO_ROOT/scripts/_framework_manifest_set.sh"
    34	
    35	ONLY=""
    36	QUIET=0
    37	while [[ $# -gt 0 ]]; do
    38	  case "$1" in
    39	    --only)  ONLY="${2:-}"; shift 2 ;;
    40	    --quiet) QUIET=1; shift ;;
    41	    -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
    42	    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
    43	  esac
    44	done
    45	
    46	[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
    47	[[ -f "$LIB" ]] || { echo "ERROR: library not found: $LIB" >&2; exit 2; }
    48	
    49	# shellcheck source=/dev/null
    50	. "$LIB" 2>/dev/null || { echo "ERROR: cannot source $LIB" >&2; exit 2; }
    51	command -v _ownership_verdict >/dev/null 2>&1 || {
    52	  echo "ERROR: _ownership_verdict is not defined in $LIB" >&2
    53	  echo "       (W2 has not landed the function yet)" >&2
    54	  exit 2
    55	}
    56	
    57	PASS=0; FAIL=0; SKIPPED=0
    58	SKIP_IDS=""
    59	LINES=""
    60	
    61	while IFS=$'\t' read -r id surface prior_record live_type live_content \
    62	      source_has mode ceremony operation skip_requested fault \
    63	      exp_verdict exp_hash origin note; do
    64	  [[ -z "${id:-}" ]] && continue
    65	  case "$id" in \#*|id) continue ;; esac
    66	  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
    67	
    68	  # Rows with an injected fault assert what the CALLER does when it cannot
    69	  # carry out a verdict. That is execution, not decision (round-1 consensus
    70	  # C2), so the pure function has nothing to say about them and the e2e suite
    71	  # covers them. Counted and named, never silently skipped: a suite that goes
    72	  # green by quietly not running rows is the vacuous-gate class.
    73	  if [[ "${fault:-none}" != "none" ]]; then
    74	    SKIPPED=$((SKIPPED+1))
    75	    SKIP_IDS+="$id "
    76	    continue
    77	  fi
    78	
    79	  got="$( _ownership_verdict "$surface" "$prior_record" "$live_type" \
    80	            "$live_content" "$source_has" "$mode" "$ceremony" \
    81	            "$operation" "$skip_requested" 2>/dev/null )"
    82	  rc=$?
    83	  exp="$exp_verdict $exp_hash"
    84	
    85	  # A non-zero return or unparseable output is a FAILURE, never a skip: a
    86	  # decision function that cannot answer for a legal cell has a hole in it,
    87	  # and a hole that reports as "not applicable" is how a gap stays invisible.
    88	  if [[ $rc -ne 0 || -z "$got" ]]; then
    89	    LINES+="$( printf '%-10s FAIL   exp=%-40s got=<no answer, rc=%s>  %s\n' "$id" "$exp" "$rc" "$origin" )"$'\n'
    90	    FAIL=$((FAIL+1)); continue
    91	  fi
    92	
    93	  if [[ "$got" == "$exp" ]]; then
    94	    PASS=$((PASS+1))
    95	    [[ "$QUIET" -eq 1 ]] || LINES+="$( printf '%-10s ok     %-40s %s\n' "$id" "$exp" "$origin" )"$'\n'
    96	  else
    97	    FAIL=$((FAIL+1))
    98	    LINES+="$( printf '%-10s FAIL   exp=%-40s got=%-40s %s\n' "$id" "$exp" "$got" "$origin" )"$'\n'
    99	  fi
   100	done < "$TSV"
   101	
   102	printf '%s' "$LINES" | LC_ALL=C sort
   103	echo ""
   104	echo "unit oracle: PASS=$PASS  FAIL=$FAIL  SKIPPED(execution-fault rows)=$SKIPPED"
   105	[[ -n "$SKIP_IDS" ]] && echo "  not decision cells, covered by the e2e: $SKIP_IDS"
   106	[[ "$FAIL" -gt 0 ]] && exit 1
   107	exit 0

exec
/bin/zsh -lc "nl -ba scripts/_framework_manifest_set.sh | sed -n '430,610p'; nl -ba scripts/_framework_manifest_set.sh | sed -n '330,385p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
   430	    rm -f "$_wbm_tmp" "$_wbm_tmp.sorted" 2>/dev/null || true
   431	    echo "    NOTE: baseline manifest atomic mv failed — advisory only" >&2
   432	  fi
   433	  return 0
   434	}
   435	
   436	# =============================================================================
   437	# PLAN-167 — _ownership_verdict: THE ownership decision.
   438	#
   439	# install.sh and upgrade.sh stop deciding and start executing. Every defect in
   440	# the 35-finding S296 review series was a cell of this space whose answer was
   441	# decided branch-locally, so two branches could disagree about the same
   442	# question and nothing detected it.
   443	#
   444	#   $1 surface        spec | protocol | marker
   445	#   $2 prior_record   none | hash | link_match | link_retargeted
   446	#   $3 live_type      absent | dir | dir_empty | regular | symlink | special
   447	#                     | ancestor_symlink
   448	#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
   449	#                     | edited | -
   450	#   $5 source_has     yes | no
   451	#   $6 mode           copy | link
   452	#   $7 ceremony       user | maintainer
   453	#   $8 operation      install_fresh | install_rerun | upgrade
   454	#   $9 skip_requested none | self | descendant
   455	#
   456	#   stdout: "<VERDICT> <HASH_SOURCE>", rc 0
   457	#   rc 1, no output: a combination the legality rules forbid.
   458	#
   459	# PURE: no filesystem, no globals, no environment. Callers observe the nine
   460	# dimensions and pass them in. That purity is what lets the same table drive a
   461	# millisecond unit oracle as well as the ~25-minute end-to-end suite; S296 had
   462	# only the slow instrument, at one cell per ~40-minute round.
   463	#
   464	# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
   465	# failed backup is not a property of these nine dimensions — it is the CALLER
   466	# failing to carry out a verdict it was handed. And per INV-3 that failure
   467	# NEVER advances the record: recording a delivery that did not happen is the
   468	# over-claiming direction ADR-155-AMEND-1 §3 forbids.
   469	#
   470	# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
   471	# =============================================================================
   472	_ownership_verdict() {
   473	  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
   474	  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"
   475	
   476	  # Do not touch the surface; decide the RECORD. Ownership continuity and the
   477	  # digit it carries are separate decisions, and moving one without the other
   478	  # produced four distinct defects — so they are resolved together, once.
   479	  _ov_carry() {
   480	    case "$_ov_prior" in
   481	      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
   482	      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
   483	      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
   484	    esac
   485	    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
   486	    # bytes now on disk, which is how a later upgrade comes to overwrite an
   487	    # adopter edit and uninstall comes to delete it.
   488	    if [ "$_ov_surface" = "protocol" ] \
   489	       || [ "$_ov_shas" = "no" ] \
   490	       || [ "$_ov_ltype" = "dir_empty" ]; then
   491	      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
   492	    else
   493	      printf 'PRESERVE_OWNED HASH_SOURCE'
   494	    fi
   495	  }
   496	
   497	  # The framework must not claim this path. Whether a record existed changes
   498	  # only which NAME the observation takes (OQ-9 — the evidence that these are
   499	  # one outcome, not two).
   500	  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.
   501	  # OMIT_RECORD dizia a mesma coisa — sem registro no disco — e diferia apenas
   502	  # por já existir registro antes, que é a coluna prior_record. Um membro de
   503	  # enum redundante é onde dois ramos discordam sobre qual deles se aplica.
   504	  _ov_unowned() { printf 'PRESERVE_UNOWNED HASH_NONE'; }
   505	
   506	  # --- Stage A: gates that refuse to act, in priority order ------------------
   507	
   508	  # A1. The source cannot deliver this surface.
   509	  if [ "$_ov_shas" = "no" ]; then
   510	    case "$_ov_surface" in
   511	      marker)   printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;  # --pin: readers fall back to VERSION
   512	      protocol) return 1 ;;                                  # R-03: generated, never absent
   513	      *)        _ov_carry; return 0 ;;
   514	    esac
   515	  fi
   516	
   517	  # A2. A user ceremony never receives the root surfaces (WS4).
   518	  if [ "$_ov_cer" = "user" ] && [ "$_ov_surface" != "marker" ]; then
   519	    if [ "$_ov_op" = "install_fresh" ]; then printf 'PRESERVE_UNOWNED HASH_NONE'
   520	    else _ov_carry; fi
   521	    return 0
   522	  fi
   523	
   524	  # A3. Reachable only by writing THROUGH a symlink, out of the target tree.
   525	  # Always unowned: the relpath sanitizer already dropped any record whose path
   526	  # crosses a symlink, so there is no record left to carry (docs §5.8).
   527	  if [ "$_ov_ltype" = "ancestor_symlink" ]; then _ov_unowned; return 0; fi
   528	
   529	  # A4. A leaf symlink is healthy ONLY as the recorded link-mode delivery.
   530	  # The absence of a LINK row is not a match — it is the absence of evidence.
   531	  if [ "$_ov_ltype" = "symlink" ]; then
   532	    if [ "$_ov_prior" = "link_match" ]; then printf 'PRESERVE_OWNED LINK_RECORD'
   533	    else _ov_unowned; fi
   534	    return 0
   535	  fi
   536	
   537	  # A5. Anything that exists but is not shaped like this surface is
   538	  # adopter-owned: never write into it, never through it, never block on it.
   539	  case "$_ov_surface" in
   540	    spec)
   541	      case "$_ov_ltype" in special) _ov_unowned; return 0 ;; esac ;;
   542	    protocol|marker)
   543	      case "$_ov_ltype" in dir|dir_empty|special) _ov_unowned; return 0 ;; esac ;;
   544	  esac
   545	
   546	  # A6. An explicit skip is honoured as a UNIT — a partial contract refresh is
   547	  # incoherent, so a descendant skip preserves the whole tree.
   548	  if [ "$_ov_skip" != "none" ]; then _ov_carry; return 0; fi
   549	
   550	  # --- Stage B: ownership resolution ----------------------------------------
   551	  _ov_owned=""
   552	  if [ "$_ov_prior" = "hash" ] || [ "$_ov_prior" = "link_match" ]; then
   553	    _ov_owned=1
   554	  elif [ "$_ov_ltype" = "absent" ]; then
   555	    _ov_owned=1                                   # new delivery
   556	  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
   557	    _ov_owned=1                                   # current-source takeover / legacy migration
   558	  fi
   559	  # legacy_pristine_partial is deliberately NOT owned: every regular file may
   560	  # match a shipped release, but a tree carrying an entry the fingerprint
   561	  # cannot inventory has not been inventoried, and a partial inventory must
   562	  # never certify a wholesale replace (ADR-155-AMEND-1 §4).
   563	
   564	  if [ -z "$_ov_owned" ]; then _ov_unowned; return 0; fi
   565	
   566	  # --- Stage C: execution ---------------------------------------------------
   567	  if [ "$_ov_ltype" = "absent" ]; then
   568	    case "$_ov_surface" in
   569	      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
   570	      *)        printf 'DELIVER HASH_SOURCE' ;;
   571	    esac
   572	    return 0
   573	  fi
   574	
   575	  # An install rerun does not re-deliver an existing surface; it decides the
   576	  # record. Only the upgrade's forced route replaces content.
   577	  if [ "$_ov_op" != "upgrade" ]; then _ov_carry; return 0; fi
   578	
   579	  # The pointer is the ONE surface where an adopter edit is PRESERVED rather
   580	  # than treated as a fork. SPEC/v1 is deliberately the opposite: it is the
   581	  # published compliance CONTRACT, so an edit is a fork and the forced route
   582	  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
   583	  # prose, and overwriting a customised one is the verified S238 data loss that
   584	  # ADR-155 decision (iii) exists to close.
   585	  #
   586	  # The recorded digest stays CANONICAL either way: recording the customised
   587	  # bytes would make the NEXT upgrade read H_dst==H_base and clobber them.
   588	  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
   589	    printf 'PRESERVE_OWNED HASH_CANONICAL_POINTER'
   590	    return 0
   591	  fi
   592	
   593	  case "$_ov_surface" in
   594	    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
   595	    *)        printf 'REFRESH HASH_SOURCE' ;;
   596	  esac
   597	}
   330	  # holds), but the recorded baseline must be what the framework SHIPS — never
   331	  # an adopter-customized target file. Without this, upgrade.sh's post-upgrade
   332	  # rewrite (C.7) records hash(customized-but-preserved file) as the baseline,
   333	  # which the NEXT upgrade reads as H_dst==H_base => FRAMEWORK-CHANGED => clobber
   334	  # (the verified C.5 idempotency failure). Default = FMS_ROOT (install path,
   335	  # where the target IS the freshly-written framework version). The root
   336	  # PROTOCOL.md is GENERATED (a pointer), not a source copy, so it always hashes
   337	  # from FMS_ROOT (the target pointer), never FMS_HASH_ROOT. (Codex R1 + dry-run)
   338	  _wbm_hash_root="${FMS_HASH_ROOT:-$FMS_ROOT}"
   339	
   340	  _wbm_tmp="$( mktemp "$_wbm_manifest.XXXXXX" 2>/dev/null )" || {
   341	    echo "    NOTE: baseline manifest skipped (mktemp failed) — advisory only" >&2
   342	    return 0
   343	  }
   344	
   345	  _framework_manifest_files | while IFS= read -r _wbm_rel; do
   346	    [ -n "$_wbm_rel" ] || continue
   347	    _wbm_abs="$FMS_ROOT/$_wbm_rel"
   348	    # Drop relpaths carrying control chars (line-based manifest).
   349	    case "$_wbm_rel" in
   350	      *[$'\n\r\t']*) continue ;;
   351	    esac
   352	    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ] \
   353	       && _wbm_link_allowed "$_wbm_rel"; then
   354	      _wbm_target="$( readlink "$_wbm_abs" 2>/dev/null || true )"
   355	      [ -n "$_wbm_target" ] || continue
   356	      case "$_wbm_target" in
   357	        *[$'\n\r\t']*) continue ;;
   358	      esac
   359	      printf 'LINK  %s  %s\n' "$_wbm_rel" "$_wbm_target" >> "$_wbm_tmp"
   360	    elif [ -f "$_wbm_abs" ]; then
   361	      if [ "$_wbm_rel" = "PROTOCOL.md" ]; then
   362	        # Generated pointer. Use the CANONICAL pointer hash (FMS_PROTOCOL_HASH,
   363	        # exported by upgrade.sh _refresh_protocol_pointer) so a PRESERVED
   364	        # adopter-customized PROTOCOL.md is NOT re-recorded as its own baseline
   365	        # (Codex R2 P0 — else the next upgrade reads H_dst==H_base and clobbers
   366	        # it). On install (no FMS_PROTOCOL_HASH) the target IS the freshly
   367	        # written pointer, so hashing it directly is correct.
   368	        if [ -n "${FMS_PROTOCOL_HASH:-}" ]; then
   369	          _wbm_digest="$FMS_PROTOCOL_HASH"
   370	        else
   371	          _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )"
   372	        fi
   373	      elif _wbm_is_conditional "$_wbm_rel"; then
   374	        _wbm_decl="$( _wbm_declared_hash_source "$_wbm_rel" )"
   375	        case "$_wbm_decl" in
   376	          HASH_SOURCE)
   377	            # FMS_SOURCE_ROOT, never FMS_HASH_ROOT: the global override is an
   378	            # upgrade-only mechanism, and borrowing it here is what dragged
   379	            # install into the r8-F1 rendered-tree regression.
   380	            if [ -n "${FMS_SOURCE_ROOT:-}" ] && [ -f "$FMS_SOURCE_ROOT/$_wbm_rel" ]; then
   381	              _wbm_digest="$( _hash_file "$FMS_SOURCE_ROOT/$_wbm_rel" 2>/dev/null || true )"
   382	            else
   383	              continue   # the framework no longer ships it: record nothing
   384	            fi
   385	            ;;

exec
/bin/zsh -lc "grep -nE '10 dimens|dez dimens|dimensions|dimensões|fault|ABORT_SURFACE|enum' docs/ownership-decision-table.md | head -120; nl -ba docs/ownership-decision-table.md | sed -n '40,170p'; grep -R -n \"ADR-190\" .claude/adr .claude/plans CLAUDE.md README.md 2>/dev/null | head -80" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 152ms:
.claude/plans/PLAN-168-ownership-followups-closure.md:30:| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
.claude/plans/PLAN-168-ownership-followups-closure.md:281:### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
.claude/plans/PLAN-168-ownership-followups-closure.md:312:| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
.claude/plans/PLAN-168-ownership-followups-closure.md:329:- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
.claude/plans/PLAN-168-ownership-followups-closure.md:361:| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
.claude/plans/PLAN-167/debate/round-1/consensus.md:56:`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:123:   — but ADR-190 must name it as an extension of the accepted risk, not
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:139:   condition: consensus text (and later ADR-190) carries INV-3 verbatim.
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:169:2. ADR-190 names the OWN-0017 current-source takeover as an explicit
.claude/plans/PLAN-167/rail/codex-r3.md:14012:**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
.claude/plans/PLAN-167/rail/codex-r3.md:14072:- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
.claude/plans/PLAN-167/rail/codex-r3.md:14150:`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:
.claude/plans/PLAN-167/rail/codex-r3.md:14350:   — but ADR-190 must name it as an extension of the accepted risk, not
.claude/plans/PLAN-167/rail/codex-r3.md:14366:   condition: consensus text (and later ADR-190) carries INV-3 verbatim.
.claude/plans/PLAN-167/rail/codex-r3.md:14396:2. ADR-190 names the OWN-0017 current-source takeover as an explicit
.claude/plans/PLAN-167/rail/codex-r4.md:1572:**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
.claude/plans/PLAN-167/rail/codex-r4.md:1632:- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
.claude/plans/PLAN-167/rail/codex-r4.md:1683:- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
.claude/plans/PLAN-167/rail/codex-r4.md:1725:- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a
.claude/plans/PLAN-167/rail/codex-r4.md:1800:`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:
.claude/plans/PLAN-167/rail/codex-r4.md:11048:.claude/plans/PLAN-167/debate/round-1/security-engineer.md:169:2. ADR-190 names the OWN-0017 current-source takeover as an explicit
.claude/plans/PLAN-167/rail/codex-r4.md:11090:   — but ADR-190 must name it as an extension of the accepted risk, not
.claude/plans/PLAN-167/rail/codex-r4.md:11106:   condition: consensus text (and later ADR-190) carries INV-3 verbatim.
.claude/plans/PLAN-167/rail/codex-r4.md:11136:2. ADR-190 names the OWN-0017 current-source takeover as an explicit
.claude/plans/PLAN-167/rail/codex-r1.md:8413:**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
.claude/plans/PLAN-167/rail/codex-r1.md:8473:- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
.claude/plans/PLAN-167/rail/codex-r1.md:8524:- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
.claude/plans/PLAN-167/rail/codex-r1.md:8566:- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a
.claude/plans/PLAN-167/rail/codex-r1.md:8774:`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:
.claude/plans/PLAN-168/debate/round-1/security-engineer.md:79:  ADR-190: degradado que não casar com candidato fica degradado
.claude/plans/PLAN-168/debate/round-1/security-engineer.md:95:  de classe de confiança escrito no ADR-190) — nunca silenciosamente no
.claude/plans/PLAN-168/debate/round-1/security-engineer.md:164:5. **Decidir e registrar no ADR-190 as duas escolhas de residual**: (a)
.claude/plans/PLAN-168/debate/round-1/security-engineer.md:223:  o ADR-190 vai registrar: SPEC edited+owned ⇒ refresh FORÇADO com backup
.claude/plans/PLAN-168/debate/round-1/security-engineer.md:228:  ADR-190 deve também restatar a direção de falha do §3 (over-claim
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:26:  must deliver, what the baseline map must say, and what ADR-190 must record.
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:32:The plan section 0 states "2 sao defeito do TESTE" and later the ADR-190 content
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:68:Consequence for ADR-190: the proposed ADR content says "4 known-open cells,
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:102:The concern is not about classifying them but about what the ADR-190 says.
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:103:ADR-190 must NOT state that backup-before-replace is enforced as of v1.3.0.
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:129:1. Correct OWN-0074's classification. Plan section 0 and the ADR-190 content
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:152:3. ADR-190 ABORT_SURFACE clarity: the decision function emits 4 verdicts;
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:172:   verified before ADR-190 cites the ESCAPE mechanism as an enforcement example.
.claude/plans/PLAN-168/rail/codex-r1.md:90:    29	| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
.claude/plans/PLAN-168/rail/codex-r1.md:174:   113	### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
.claude/plans/PLAN-168/rail/codex-r1.md:196:   135	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
.claude/plans/PLAN-168/rail/codex-r1.md:211:   150	- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria e as 4 abertas.
.claude/plans/PLAN-168/rail/codex-r1.md:241:   180	| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
.claude/plans/PLAN-167-ownership-decision-table.md:260:**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
.claude/plans/PLAN-167-ownership-decision-table.md:320:- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
.claude/plans/PLAN-167-ownership-decision-table.md:371:- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
.claude/plans/PLAN-167-ownership-decision-table.md:413:- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a

exec
/bin/zsh -lc "nl -ba .claude/plans/PLAN-168/debate/round-1/security-engineer.md | sed -n '35,190p'; printf '%s\\n' '--- consensus ---'; if [ -f .claude/plans/PLAN-168/debate/round-1/consensus.md ]; then nl -ba .claude/plans/PLAN-168/debate/round-1/consensus.md | sed -n '1,240p'; fi; printf '%s\\n' '--- r1 findings tail/head ---'; sed -n '1,240p' .claude/plans/PLAN-168/rail/codex-r1.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
    35	## Risks
    36	
    37	- **R-SEC1 — HIGH — Gate W2 vacuoso (controle que não pode falhar).**
    38	  Evidência: execução da sonda em 2026-08-07 contra a árvore viva → 0
    39	  literais após upgrade (o verdito da sonda é "pointer stays substituted").
    40	  O gate declarado no plano (§2 W2: "a sonda passa a reportar 0 ocorrências
    41	  literais após o upgrade") passa HOJE, sem fix nenhum. Um gate de
    42	  superfície canônica de installer que não pode falhar não prova nada e
    43	  carimba o pack. Mitigação: o teste do AC-6 deve FORÇAR uma célula de
    44	  escrita (ponteiro ausente ⇒ DELIVER; disco == canônico ⇒ REFRESH) e
    45	  comparar os bytes que o upgrade ESCREVE contra os bytes que o install
    46	  escreve, sob inputs idênticos e pinados — com controle positivo que
    47	  falhe na árvore atual.
    48	
    49	- **R-SEC2 — HIGH — Fix (b) sem unificar a camada de RESOLUÇÃO reabre a
    50	  classe um nível acima.** O corpo embute `$SOURCE_DIR`, `$TARGET`,
    51	  `$PROFILE`, `$STACK`. No install a resolução é CLI > env > `$SOURCE_DIR`
    52	  (`--protocol-source` / `CEO_PROTOCOL_SOURCE`, install.sh:404, 517,
    53	  662-663). O upgrade.sh NÃO tem essa flag nem lê o env — sob (b), numa
    54	  célula de escrita, ganha o `$SOURCE_DIR` de QUEM RODA o upgrade. Caminho
    55	  concreto para "ponteiro nomeando um checkout que o adotante não
    56	  pretendia": adotante instala com `--protocol-source ../vendor/ceo`;
    57	  upgrade rodado de um clone scratch/CI em `/tmp/...` numa célula
    58	  DELIVER escreve um caminho efêmero que PARECE válido — pior que o
    59	  placeholder, que é autoevidentemente um placeholder. Mitigação: a função
    60	  compartilhada carrega a REGRA DE RESOLUÇÃO junto com o corpo; upgrade.sh
    61	  ganha `--protocol-source`/env com a mesma precedência; AC-6 pina os
    62	  quatro inputs E a grafia do `$TARGET` (install `.` vs caminho absoluto
    63	  muda os bytes).
    64	
    65	- **R-SEC3 — HIGH — Migração dos degradados em campo: indecidida, e a
    66	  direção do over-claim é a proibida.** Após (b), o adotante que já tem
    67	  `{{PROTOCOL_SOURCE}}` literal em disco (upgrades pré-PLAN-167) classifica
    68	  `edited` → PRESERVE_OWNED → **o arquivo quebrado é preservado para sempre
    69	  e rotulado "adopter-customised"** — o fix nunca conserta as próprias
    70	  vítimas que o plano cita. A alternativa (reconhecer degradado ⇒ refresh)
    71	  não pode ser um conjunto finito de hashes: o corpo literal embute o
    72	  `$TARGET`/`$PROFILE`/`$STACK` da invocação ORIGINAL (upgrade.sh:1560),
    73	  que não conhecemos. Mitigação: espelhar a migração legacy do
    74	  ADR-155-AMEND-1 §4 — regenerar corpos-candidatos degradados com os
    75	  valores DESTE run, match por hash EXATO do corpo inteiro (nunca substring
    76	  "contém o marcador" — um PROTOCOL.md autoral do adotante pode conter a
    77	  string, e over-claim é a classe proibida pelo §3), falha na direção
    78	  preserve + WARNING nomeado com instrução manual. Registrar o residual no
    79	  ADR-190: degradado que não casar com candidato fica degradado
    80	  (recuperável à mão; under-claim, direção permitida).
    81	
    82	- **R-SEC4 — MEDIUM — Hash canônico vira dependente do run; o
    83	  checkout-móvel produz ponteiro-fóssil "válido".** Sob (b),
    84	  `_REFRESH_PROTOCOL_CANON_HASH` passa a ser função de
    85	  SOURCE_DIR/TARGET/PROFILE/STACK. Adotante move o checkout ⇒
    86	  canônico(novo) ≠ disco(antigo) ⇒ `edited` ⇒ preservado como
    87	  "adopter-customised" ⇒ o ponteiro nomeia um caminho MORTO para sempre,
    88	  parecendo válido. A cura possível — `pristine_prior` (disco ==
    89	  digest registrado no baseline ⇒ refrescável) — AUTORIZA overwrite a
    90	  partir do registro NÃO-ASSINADO: é exatamente o residual aceito do
    91	  ADR-155 ("Tampered H_base==H_dst", Codex R1 P0#1), e só fica dentro da
    92	  classe de confiança aceita com as duas cercas que este caminho JÁ tem
    93	  (backup-always + stderr alto, upgrade.sh:1638-1642). Mitigação: DECIDIR
    94	  (aceitar o residual do fóssil, ou adotar pristine_prior com o argumento
    95	  de classe de confiança escrito no ADR-190) — nunca silenciosamente no
    96	  código; e jamais re-baselinar bytes customizados (C.5).
    97	
    98	- **R-SEC5 — MEDIUM — O que quebra no delta de digest: nada na direção
    99	  destrutiva, DESDE QUE o preserve continue registrando o canônico.**
   100	  Verificado consumidor a consumidor: (i) classificação — `_lc` compara
   101	  disco vs canônico DESTE run (upgrade.sh:1579-1580) e
   102	  `_ov_obs_prior_record` greppa só a PRESENÇA do relpath, nunca o digest
   103	  (upgrade.sh:1780-1798) ⇒ o delta de digest não muda verdito; (ii)
   104	  uninstall — só deleta com sha IGUAL ao registro (uninstall.sh:6-7, 193,
   105	  256); registro=canônico nunca iguala bytes customizados ⇒ nenhum corredor
   106	  novo de deleção de arquivo do adotante; a população em transição
   107	  (registro=canônico-literal do upgrade.sh:3142, disco=substituído) dá
   108	  mismatch ⇒ preservado ⇒ resíduo pós-uninstall, não perda; (iii) doctor —
   109	  flag cosmética de drift na população em transição, que o fix cura no
   110	  próximo rewrite C.7. CONDIÇÃO: o fix mantém a semântica
   111	  HASH_CANONICAL_POINTER no preserve (nota da OWN-0074;
   112	  `_framework_manifest_set.sh:361-369`) — agora com canônico=substituído —
   113	  e o teste INV-4 assere registro-digest == hash(saída do gerador).
   114	
   115	- **R-SEC6 — LOW — Valores do estado não-assinado fluem para o corpo
   116	  gerado (pré-existente, cercado; a cerca vira contrato).** PROFILE/STACK
   117	  replayados de `.claude/.install-state.json` (upgrade.sh:685-701) entram
   118	  no comando sugerido do corpo (upgrade.sh:1560) — já hoje. A cerca de
   119	  charset (upgrade.sh:672-675: `^[A-Za-z0-9_,.-]{1,200}$` /
   120	  `^[A-Za-z0-9_.-]{1,100}$`, sem espaço/`;`/`$`) impede injeção de shell no
   121	  comando que o adotante copia-cola. Sob (b) isso vira input do gerador
   122	  compartilhado: manter a cerca, nunca alargar o charset, e
   123	  PROTOCOL_SOURCE jamais resolvido de estado/manifesto (só CLI/env).
   124	
   125	- **R-SEC7 — LOW — W1: o fetch do tag verifica existência, não conteúdo.**
   126	  `git rev-parse --verify refs/tags/v1.2.0` prova que o ref existe; um tag
   127	  movido no origin muda os inputs do harness. Direção de falha é visível
   128	  (as fingerprints pristine hardcoded em upgrade.sh §4 do AMEND-1 deixam de
   129	  casar ⇒ vermelho), então advisory: assertar o SHA do commit do tag contra
   130	  constante registrada, coerente com a regra de SHA-pinning do repo.
   131	
   132	## Must-fix (blocking)
   133	
   134	1. **W2 passo 0 — re-verificar a premissa na árvore landada e estabelecer
   135	   alcançabilidade.** Registrar no plano que a sonda hoje dá 0/0 (o §0
   136	   "upgrade=4" é evidência PRÉ-refactor do PLAN-167), e provar com controle
   137	   positivo QUAL combinação alcança o branch `DELIVER|REFRESH` de
   138	   `_refresh_protocol_pointer` (upgrade.sh:1630-1651). A TSV não tem
   139	   nenhuma célula `protocol` com REFRESH, nem DELIVER em `upgrade`
   140	   (verificado por enumeração: OWN-0002 é install_fresh; OWN-0032/33/34,
   141	   0071/0072, 0074 são todas PRESERVE_*); célula ilegal cai no fallback
   142	   preserve (upgrade.sh:1588-1592). Se o branch é morto, o defeito vivo é
   143	   "ponteiro nunca refrescável", não "todo upgrade degrada" — e o fix é
   144	   outro.
   145	2. **Resolver o conflito com o anti-objetivo ANTES de codar.** Se
   146	   (hash, regular, pristine, maintainer, upgrade) é célula ilegal hoje, o
   147	   fix (b) sozinho NÃO devolve a capacidade de refresh — devolver exige
   148	   células novas de escrita para `protocol` em `upgrade` na TSV, o que o
   149	   anti-objetivo do plano proíbe ("não mexer na tabela nem nos vereditos").
   150	   O plano precisa ou escopar uma exceção explícita ratificada pelo Owner,
   151	   ou declarar que o refresh permanece inalcançável e reescrever o AC-6
   152	   para o que sobra testável. Sem essa decisão, AC-6 ("byte-idêntico") é
   153	   vacuamente verdadeiro de novo: nada no lado upgrade escreve.
   154	3. **Substituir o Gate W2 vacuoso** (R-SEC1): teste INV-4 força célula de
   155	   escrita, compara bytes escritos pelos DOIS writers sob inputs pinados
   156	   (incl. grafia do `$TARGET`), assere registro==hash(gerador), e tem
   157	   controle positivo que falha na árvore atual. Cobrir install→upgrade E
   158	   upgrade→upgrade (o plano já pede; manter).
   159	4. **Unificar a camada de resolução junto com o gerador** (R-SEC2):
   160	   upgrade.sh ganha `--protocol-source`/`CEO_PROTOCOL_SOURCE` com a
   161	   precedência do install (CLI > env > SOURCE_DIR); inputs do gerador nunca
   162	   vêm de estado/manifesto não-assinado além dos PROFILE/STACK já cercados
   163	   por charset (a cerca vira asserção de teste).
   164	5. **Decidir e registrar no ADR-190 as duas escolhas de residual**: (a)
   165	   migração dos degradados em campo (R-SEC3 — match por hash exato de
   166	   corpo-candidato regenerado, fail-toward-preserve, over-claim proibido
   167	   por AMEND-1 §3); (b) comportamento no checkout-móvel (R-SEC4 — fóssil
   168	   preservado documentado, OU pristine_prior com o argumento de classe de
   169	   confiança do baseline não-assinado + cercas backup-always/loud
   170	   nomeadas). Nenhuma das duas pode ser decidida silenciosamente no código.
   171	
   172	## Nice-to-have (advisory)
   173	
   174	1. W1: assertar o SHA do commit de `v1.2.0` contra constante registrada
   175	   após o fetch (R-SEC7).
   176	2. WARNING no DELIVER/REFRESH quando o `$SOURCE_DIR` resolvido está sob
   177	   diretório temporário (`/tmp`, `$TMPDIR`) — o cenário CI-escreve-caminho-
   178	   efêmero de R-SEC2 fica ao menos audível.
   179	3. doctor.sh: nota nomeada para a população em transição
   180	   (registro=canônico-literal antigo ≠ disco) para o drift cosmético não
   181	   virar ticket de adotante.
   182	4. Guardar a saída da re-execução da sonda (0/0) como evidência datada em
   183	   `PLAN-168/evidence/` — o §0 do plano hoje cita como atual um número que
   184	   não é mais.
   185	
   186	## Unseen by the original plan
   187	
   188	1. **A tabela de evidências do §0 está stale**: "upgrade=4" era verdade
   189	   pré-refactor; a árvore landada (`7c0828a`) preserva no caminho comum
   190	   (execução da sonda em 2026-08-07: 0/0). A regra 3 do próprio plano
--- consensus ---
     1	---
     2	plan: PLAN-168
     3	round: 1
     4	rounds_synthesized: [round-1]
     5	agents_considered: [devops, qa-architect, security-engineer]
     6	decisions_revised_in_plan:
     7	  - "§0/§W1 — _hash_lib.sh JÁ estava nos filtros; 4 paths, não 5"
     8	  - "§W1.3 — não existe trigger schedule:; AC-4 era insatisfazível"
     9	  - "§W1.4 — AC-5 compara CONJUNTO DE IDs, não o arquivo (header tem paths de máquina)"
    10	  - "§W2 — o fix não cura quem está em campo; falta reconhecedor de corpo legado"
    11	  - "§W2 — PROTOCOL_SOURCE NÃO é persistido; o gerador não tem de onde ler"
    12	  - "§0/§W3 — OWN-0074 é PRODUTO, não teste (minha classificação estava errada)"
    13	synthesized_at: 2026-08-07T21:05:00Z
    14	synthesized_by: CEO
    15	---
    16	
    17	# Round 1 consensus — PLAN-168
    18	
    19	Três críticas, **três ADJUST, zero VETO**. Nenhum arquétipo rejeitou a forma
    20	do plano; todos atacaram a mecânica — e **acertaram em tudo que verifiquei**.
    21	
    22	Registrado como **design-coherent**. Não autoriza shipping: a cascata de
    23	verificação (V2 rail, V3 GPG do Owner) é que autoriza.
    24	
    25	## Consenso (2+ agentes)
    26	
    27	**C1 — a mecânica do plano foi escrita de memória e está errada em pontos
    28	verificáveis.** devops must-fix 2 e QA must-fix 1 são a mesma falha em lugares
    29	diferentes. `_hash_lib.sh` JÁ estava nos dois filtros (`:15`, `:54`); o
    30	`OWN-0074` NÃO é defeito de teste. **Ambos verificados literalmente antes de
    31	aceitar.** É a lição
    32	[[feedback-plan-mechanics-written-from-memory-fail]] se repetindo no plano
    33	seguinte ao que a registrou.
    34	
    35	**C2 — "descrever intenção não é gate".** QA must-fix 2 e devops must-fix 4
    36	convergem: o AC-5 precisa do **script**, não do comportamento em prosa. E o
    37	`diff` literal contra o baseline **falha sempre em CI**, porque o cabeçalho
    38	carrega paths da máquina que o gerou.
    39	
    40	## Insights de um agente, mantidos
    41	
    42	1. **devops must-fix 1 — não existe trigger `schedule:`.** O AC-4 era
    43	   insatisfazível. Pior: `schedule:` ignora `paths:`, então a divisão
    44	   per-PR/nightly exige **dois jobs**, não duas linhas de filtro.
    45	2. **security must-fix 1 — o fix não cura quem já está em campo.** Ponteiro com
    46	   placeholder literal classifica `edited` ⇒ `PRESERVE_OWNED` ⇒ preservado
    47	   para sempre. Cura: reconhecedor de corpo legado ⇒ REFRESH com backup, no
    48	   molde do r20.
    49	3. **security must-fix 2, CORRIGIDO E AGRAVADO na verificação.** A crítica
    50	   dizia que o install grava `ph.PROTOCOL_SOURCE` em `:2523`. **Não grava** —
    51	   `request.PROTOCOL_SOURCE` é `None` e a chave não existe. Logo o gerador
    52	   compartilhado **não tem fonte de verdade**, e o W2 cresce: precisa
    53	   PERSISTIR o valor, com fallback declarado.
    54	4. **QA must-fix 1 — ordem W1/W2.** Se o gate do AC-5 landar antes do W2, a
    55	   primeira CI depois do W2 falha por "o conjunto encolheu". O W2 tem de
    56	   atualizar o conjunto esperado **no mesmo pack**.
    57	
    58	## Rejeitados / adiados
    59	
    60	- Nada foi rejeitado. Os 3 must-fix do security e os 4 do devops entraram; os
    61	  2 do QA entraram.
    62	
    63	## Ajustes no plano
    64	
    65	§0 (tabela de evidência + linha nova do `OWN-0074`) · §W1.1 (4 paths + nota de
    66	verificação) · §W1.2 (`--print-legacy-tag`) · §W1.3 (bloqueador do nightly) ·
    67	§W1.4 (comparar conjunto de ids) · §W2.2-2.5 (cura, persistência, 3 caminhos
    68	de teste) · §W3 (classificação correta) · AC-2/4/5/6/6b/6c · §6 riscos.
    69	
    70	## Round verdict
    71	
    72	**PROCEED** — o plano vai para `reviewed` com todos os must-fix aplicados.
    73	Não há conflito entre críticas; todas as divergências foram entre um agente e
    74	o plano, e cada uma resolveu por evidência literal.
--- r1 findings tail/head ---
OpenAI Codex v0.144.6
--------
workdir: /private/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp.w0RhkTBce4/p168
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fddf7-b75d-7a23-8703-562c462d554b
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- DIFF STAT ---\\n' && git diff --stat && printf '\\n--- CACHED STAT ---\\n' && git diff --cached --stat && printf '\\n--- UNTRACKED ---\\n' && git ls-files --others --exclude-standard" in /private/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp.w0RhkTBce4/p168
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Rb4glAA4' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-8vWmrfn2' (errno=Operation not permitted)
 M PLAN-168.md

--- DIFF STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-kwi7MKGn' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-vLkX0GlH' (errno=Operation not permitted)
 PLAN-168.md | 2 ++
 1 file changed, 2 insertions(+)

--- CACHED STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Q0dXFqfg' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GUgpdKMG' (errno=Operation not permitted)

--- UNTRACKED ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-qQ7zR5NP' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-kRAWC07x' (errno=Operation not permitted)

exec
/bin/zsh -lc "git diff -- PLAN-168.md && printf '\\n--- FILE ---\\n' && nl -ba PLAN-168.md && printf '\\n--- REPO ---\\n' && find . -maxdepth 2 -type f -not -path './.git/*' | sort | sed -n '1,200p'" in /private/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp.w0RhkTBce4/p168
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-EEECTssl' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-DuqrUFe3' (errno=Operation not permitted)
diff --git a/PLAN-168.md b/PLAN-168.md
index b6d59de..f2ca473 100644
--- a/PLAN-168.md
+++ b/PLAN-168.md
@@ -187,3 +187,5 @@ staged, o Owner assina uma vez.
   Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
 - **Próxima ação:** W1 item 1 (path filters), em clone overlay.
+
+<!-- rail: revise ESTE plano -->

--- FILE ---
     1	---
     2	id: PLAN-168
     3	title: Fechamento dos follow-ups do PLAN-167 — CI que não roda, ponteiro que degrada, contrato sem ADR
     4	status: draft
     5	created: 2026-08-07
     6	owner: CEO
     7	depends_on: [PLAN-167]
     8	budget_tokens: 120-180k
     9	budget_sessions: 1
    10	context_risk: medium
    11	external_wait: assinatura GPG do Owner para o W1 (workflows são superfície canônica)
    12	tags: [ci, install, upgrade, adr, testing, canonical]
    13	---
    14	
    15	# PLAN-168 — fechamento dos follow-ups do PLAN-167
    16	
    17	> **Origem.** O PLAN-167 landou em `7c0828a` (assinado, pushado). Três coisas
    18	> ficaram deliberadamente FORA daquele Scope, e cada uma tem causa nomeada e
    19	> evidência já produzida. Este plano não descobre nada novo: ele **fecha o que
    20	> já foi diagnosticado**.
    21	
    22	## 0. O que já está provado (não re-investigar)
    23	
    24	| Item | Evidência existente |
    25	|---|---|
    26	| CI não dispara os oráculos | `grep -c` = 0 para os 3 paths novos em `smoke-install.yml`; devops-critique r1 must-fix 1; codex rail r1/r2/r4 |
    27	| `fetch-depth: 1` não traz tags | `smoke-install.yml:101`; o harness precisa de `v1.2.0` para as linhas `legacy_pristine*` |
    28	| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — install=0 ocorrências literais, upgrade=4 |
    29	| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
    30	
    31	**Anti-objetivo:** não mexer na tabela de decisão nem nos vereditos. O
    32	PLAN-167 fechou aquilo com 58/62 e rail de 4 rodadas. Aqui só se fecha o
    33	entorno.
    34	
    35	## 1. O problema, em uma frase cada
    36	
    37	**W1 — teste que não roda apodrece.** Os dois oráculos do PLAN-167
    38	(`test-ownership-verdict-unit.sh`, `test-ownership-table.sh`) não estão em
    39	nenhum path filter. Um PR que altere a tabela, o harness ou o `_hash_lib.sh`
    40	**pula o gate inteiro**. É literalmente a classe do achado r10-F4 — um teste
    41	cuja única execução em CI era pulada — reaparecendo no trabalho que a
    42	consertou.
    43	
    44	**W2 — todo upgrade quebra o ponteiro raiz.** `install.sh` escreve
    45	`PROTOCOL.md` e **substitui** os placeholders; `upgrade.sh` regenera do
    46	heredoc e deixa `{{PROTOCOL_SOURCE}}` **literal**. Qualquer adotante cujo
    47	checkout esteja fora do target fica com um arquivo que não diz mais onde o
    48	protocolo mora. É a classe *install-set ≠ upgrade-set* que a decisão (i) do
    49	ADR-155 existe para eliminar: a enumeração compartilhada resolveu QUAIS
    50	caminhos os dois lados tocam, nunca QUE CONTEÚDO produzem.
    51	
    52	**W3 — o contrato não tem ADR.** A tabela de decisão é hoje a autoridade
    53	sobre propriedade, e vive só num `docs/`. Sem ADR, a próxima pessoa que
    54	"consertar uma assimetria" não tem onde ler que ela é decidida.
    55	
    56	## 2. Ondas
    57	
    58	### W1 — CI wiring (CANÔNICO: `.github/workflows/` exige cerimônia)
    59	
    60	1. Adicionar aos **dois** filtros (`pull_request` e `push`) de
    61	   `smoke-install.yml`:
    62	   ```
    63	   scripts/tests/test-ownership-table.sh
    64	   scripts/tests/test-ownership-verdict-unit.sh
    65	   scripts/tests/ownership_table.tsv
    66	   docs/ownership-decision-table.md
    67	   scripts/_hash_lib.sh
    68	   ```
    69	   O `_hash_lib.sh` é o r10-F4 literal: os oráculos usam `_hash_file`/
    70	   `_hash_stdin`, e hoje um PR que só toque o helper pula a suíte.
    71	2. **Buscar o tag `v1.2.0`** antes do passo dos oráculos (espelhar o fetch do
    72	   pin de paridade que já existe no arquivo):
    73	   ```yaml
    74	   - name: Fetch the legacy_pristine tag
    75	     run: |
    76	       git fetch --no-tags --depth 1 origin +refs/tags/v1.2.0:refs/tags/v1.2.0
    77	       git rev-parse --verify refs/tags/v1.2.0
    78	   ```
    79	   **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
    80	   que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
    81	   (rejeitada no consenso do round 1 do PLAN-167).
    82	3. **Dois gates, dois tempos** — a divisão é o produto do W2 do PLAN-167:
    83	   - **por-PR:** `test-ownership-verdict-unit.sh` (segundos, 60 células)
    84	   - **nightly:** `test-ownership-table.sh` (~25 min, 62 installs reais)
    85	   O e2e **não cabe** no teto de 25 min do job atual — o orçamento já foi
    86	   elevado 4× (5→8→20→25). Colocá-lo no caminho por-PR quebra o job.
    87	4. O e2e termina com **4 vermelhos deliberados**. O passo de CI precisa
    88	   aceitar isso explicitamente (comparar contra `ownership-baseline-map.txt`,
    89	   não exigir rc=0) **e falhar se o conjunto de vermelhos MUDAR** — inclusive
    90	   se encolher. Verde total significa que a tabela mudou.
    91	
    92	**Gate W1:** um PR tocando só `ownership_table.tsv` dispara o workflow (hoje
    93	não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
    94	
    95	### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
    96	
    97	1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
    98	   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
    99	   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
   100	     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
   101	     em vez de o sintoma.
   102	   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
   103	2. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
   104	   exige que o ponteiro seja **byte-idêntico** nos dois caminhos. Sem isso a
   105	   divergência volta — nenhuma asserção de propriedade a enxerga, porque o
   106	   registro está certo e os bytes errados.
   107	3. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   108	   como base do teste; ela já reproduz o defeito.
   109	
   110	**Gate W2:** a sonda passa a reportar 0 ocorrências literais após o upgrade,
   111	e o teste novo falha se alguém reverter.
   112	
   113	### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
   114	
   115	Registrar como contrato:
   116	- as **10 dimensões** e o enum final (**4 vereditos** após o colapso da OQ-9
   117	  ratificado pelo Owner: `DELIVER · REFRESH · PRESERVE_OWNED ·
   118	  PRESERVE_UNOWNED`; `ABORT_SURFACE` é **falha de execução**, não veredito);
   119	- **INV-1..INV-4** (as quatro invariantes cross-surface);
   120	- a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
   121	  `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
   122	  é a que mais convida um "conserto" futuro;
   123	- que o `ADR-155-AMEND-1` é **emendado**, não revogado;
   124	- as 4 células conhecidas-abertas com causa, e que **2 são defeito do TESTE**.
   125	
   126	**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
   127	novo muda a contagem — regenerar as superfícies derivadas).
   128	
   129	## 3. Fronteira canônica
   130	
   131	| Superfície | Guard | Onda |
   132	|---|---|---|
   133	| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
   134	| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
   135	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
   136	| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
   137	
   138	**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
   139	cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
   140	staged, o Owner assina uma vez.
   141	
   142	## 4. Critérios de aceite
   143	
   144	- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
   145	- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros (r10-F4 fechado de verdade).
   146	- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
   147	- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly**.
   148	- [ ] **AC-5** O passo de CI falha se o CONJUNTO de vermelhos mudar — inclusive encolher.
   149	- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico**, com teste que prova.
   150	- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria e as 4 abertas.
   151	- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
   152	- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
   153	
   154	## 5. Regras do run (herdadas, custaram caro)
   155	
   156	1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
   157	   `git diff HEAD` aplicado se houver sujeira relevante.
   158	2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
   159	3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
   160	   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
   161	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
   162	4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
   163	   defeitos do PLAN-167 foram do INSTRUMENTO
   164	   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
   165	5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
   166	   gerador com 1 de 3 callers convertidos custou 24 regressões.
   167	6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
   168	   PLAN-166 suja.
   169	7. **Esperar por ARTEFATO, nunca por `pgrep`.**
   170	8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
   171	9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.
   172	
   173	## 6. Riscos
   174	
   175	| Risco | Mitigação |
   176	|---|---|
   177	| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
   178	| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
   179	| Fix do ponteiro quebra adotantes com placeholder já literal | o teste do AC-6 cobre install→upgrade; testar também upgrade→upgrade |

exec
/bin/zsh -lc "grep -n '_framework_manifest_set.sh' scripts/install.sh scripts/upgrade.sh; grep -n '_hash_lib.sh' scripts/install.sh scripts/upgrade.sh; grep -n '_CANONICAL_GUARDS' -A90 .claude/hooks/check_canonical_edit.py | sed -n '1,120p'; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '214,275p'; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '300,410p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
scripts/install.sh:249:if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
scripts/install.sh:250:  # shellcheck source=scripts/_framework_manifest_set.sh
scripts/install.sh:251:  . "$SCRIPT_DIR/_framework_manifest_set.sh"
scripts/install.sh:788:# enumeration (_framework_manifest_set.sh) only records what the framework
scripts/install.sh:1060:    # exclusion predicate (scripts/_framework_manifest_set.sh) so install and
scripts/install.sh:2262:# set from _framework_manifest_set.sh, so the manifest writer (here) and the
scripts/install.sh:2291:  # generator in _framework_manifest_set.sh does the walk + hashing + LINK
scripts/upgrade.sh:105:if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
scripts/upgrade.sh:106:  # shellcheck source=scripts/_framework_manifest_set.sh
scripts/upgrade.sh:107:  . "$SCRIPT_DIR/_framework_manifest_set.sh"
scripts/install.sh:245:if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
scripts/install.sh:246:  # shellcheck source=scripts/_hash_lib.sh
scripts/install.sh:247:  . "$SCRIPT_DIR/_hash_lib.sh"
scripts/install.sh:2201:    # PLAN-138 Wave C (ADR-155): portable verify via _hash_lib.sh
scripts/upgrade.sh:101:if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
scripts/upgrade.sh:102:  # shellcheck source=scripts/_hash_lib.sh
scripts/upgrade.sh:103:  . "$SCRIPT_DIR/_hash_lib.sh"
115:_CANONICAL_GUARDS = [
116-    ".claude/team.md",
117-    ".claude/frontend-team.md",
118-    ".claude/pitfalls-catalog.yaml",
119-    # SKILL.md under any tier
120-    ".claude/skills/core/*/SKILL.md",
121-    ".claude/skills/frontend/*/SKILL.md",
122-    # PLAN-074 Wave 0 ADJ-A5: replace fixed 4-segment glob with
123-    # recursive ** to cover sub-namespaces (e.g. game-development/<engine>).
124-    ".claude/skills/domains/**/SKILL.md",
125-    # Domain-level governance files
126-    ".claude/skills/domains/*/team-personas.md",
127-    ".claude/skills/domains/*/pitfalls.yaml",
128-    # Sprint 9 (PLAN-009 A22 / A14) — defense-in-depth for confidence gate
129-    ".claude/**/conftest.py",
130-    ".claude/hooks/check_confidence_gate.py",
131-    ".claude/scripts/lessons.py",
132-    ".claude/scripts/prune-lessons.py",
133-    ".claude/scripts/lesson-restore.py",
134-    ".claude/scripts/lesson_ranker.py",
135-    # ---- PLAN-019 P1-SEC-A expansion: full governance surface ----
136-    # Hook source files (all PreToolUse / PostToolUse Python hooks).
137-    # An agent that can edit these can disable governance. Sentinel-gated
138-    # so Owner-signed ADRs can still land architectural changes.
139-    ".claude/hooks/*.py",
140-    ".claude/hooks/_python-hook.sh",
141-    # Hook shared library (_lib/*) — governance utilities.
142-    ".claude/hooks/_lib/*.py",
143-    ".claude/hooks/_lib/adapters/*.py",
144-    ".claude/hooks/_lib/**/*.py",
145-    # Policy-as-code (ADR-045) — policies + fixtures.
146-    ".claude/policies/*.yaml",
147-    ".claude/policies/*.yml",
148-    ".claude/policies/fixtures/*.jsonl",
149-    # PLAN-080 Phase 0b — JSON Schema for squad-bundle frontmatter validation
150-    # (M2-CDX-4 closure). Guarded so squad-bundle authoring contract cannot
151-    # be silently weakened. KERNEL-HARD-DENY since check_canonical_edit.py
152-    # itself is in _KERNEL_PATHS — extending its guard list requires both
153-    # CEO_KERNEL_OVERRIDE=PLAN-080-PHASE-0B-SCHEMA-GUARD-EXTENSION AND
154-    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to the sentinel.
155-    ".claude/policies/schemas/*.json",
156-    # PLAN-081 Phase 2 — Pair-Rail dispatcher canonical surface. The
157-    # routing-matrix.yaml carries the per-archetype coder/reviewer
158-    # decisions consumed by inject-agent-context.sh --pair-mode and
159-    # check_pair_rail.py (Phase 3 asymmetric VETO matrix arms). Mutation
160-    # of this YAML or the loader/predicate-eval would mis-route Pair-Rail
161-    # dispatches (T-4 archetype-spoofing in CROSS-LLM-THREAT-MODEL.md).
162-    # Sentinel-gated edits only — KERNEL-HARD-DENY since this guard list
163-    # itself is in _KERNEL_PATHS — extending requires
164-    # CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-2-DISPATCHER-GUARD-EXTENSION
165-    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
166-    ".claude/dispatcher/*.py",
167-    ".claude/dispatcher/*.yaml",
168-    ".claude/dispatcher/*.yml",
169-    ".claude/dispatcher/**/*.py",
170-    # Settings file — matcher/hook registration.
171-    ".claude/settings.json",
172-    # PLAN-074 Wave 0 ADJ-A3 BLOCKER 2: sub-agent definitions ship the
173-    # ROUTING TABLE personas + model: floor declarations. Editable only
174-    # via Owner-signed sentinel; CR/Sec/etc. archetype files cannot be
175-    # silently mutated by a sub-agent.
176-    ".claude/agents/*.md",
177-    # ADRs — architectural record, supersede/immutability discipline.
178-    ".claude/adr/ADR-*.md",
179-    ".claude/adr/README.md",
180-    # SPEC/v1 — published compliance contract.
181-    "SPEC/v1/*.md",
182-    "SPEC/**/*.md",
183-    # CI workflows — release / branch-protection / validation gates.
184-    ".github/workflows/*.yml",
185-    ".github/workflows/*.yaml",
186-    # CODEOWNERS — merge-side branch-protection gate.
187-    ".github/CODEOWNERS",
188-    # Installer + upgrader scripts — framework distribution surface.
189-    "scripts/install.sh",
190-    "scripts/install-npm.sh",
191-    "scripts/upgrade.sh",
192-    # PLAN-138 Wave C (ADR-155) — sourced helpers backing the install/upgrade
193-    # baseline-manifest engine. They are `source`d by the GPG-gated
194-    # install.sh/upgrade.sh, so mutating them silently changes the integrity
195-    # classification (FRAMEWORK-CHANGED vs ADOPTER-CUSTOMIZED) that protects
196-    # adopter customizations + the root PROTOCOL.md. Guarded so they are not a
197-    # soft underbelly relative to the scripts that source them.
198-    "scripts/_hash_lib.sh",
199-    "scripts/_framework_manifest_set.sh",
200-    # Root governance docs. PROTOCOL.md is rarely-changed governance;
201-    # CLAUDE.md is intentionally NOT guarded because it is edited every
202-    # session during closeout (see DYN-SEC1 dynamic finding). Protecting
203-    # CLAUDE.md needs a separate "session-closeout" ceremony convention
204-    # (tracked in dynamic-findings.md).
205-    "PROTOCOL.md",
--
788:# segments that every _CANONICAL_GUARDS entry starts with. Any path NOT
789-# starting with one of these prefixes is non-canonical in O(1) without
790-# running fnmatch 30+ times. Preserves semantics — every guard pattern
791-# starts with one of these prefixes by construction.
792-_CANONICAL_PREFIXES = frozenset({
793-    ".claude", ".github", "scripts", "SPEC", "PROTOCOL.md",
794-    # PLAN-155 Wave 3b (SENT-CX-E) — first-segment prefixes for the Codex
795-    # kill-switch surface. Without these three the fast-path bail-out in
796:    # `_is_canonical` returns False BEFORE the new `_CANONICAL_GUARDS`
797-    # entries are ever consulted (the guard would be dead — the S254
798-    # dead-gate class). Every kill-switch guard pattern starts with one of
799-    # these by construction (`.codex/*`, `requirements.toml`, `AGENTS.md`).
800-    ".codex", "requirements.toml", "AGENTS.md",
801-    # PLAN-156 Wave 3 (SENT-GK-E) — the same dead-guard class as `.codex`
802-    # above, twice over (pair-rail R4 + R14). `_is_canonical()` bails out
803-    # BEFORE any glob matching unless the path's first segment is in this
804-    # set, so adding the `.grok/**` and `templates/settings/*` patterns to
805:    # _CANONICAL_GUARDS without adding their first segments HERE would
806-    # leave both guards INERT — unsentineled edits sailing straight through
807-    # a list that LOOKS like it protects them. The S254 dead-gate class,
808-    # and the reason this pair of edits can never be split across waves.
809-    ".grok", "templates",
810-})
811-
812-
813-# PLAN160_FIX_A — upper bound on candidates classified per multi-candidate
814-# event. Beyond this the event is fail-CLOSED (blocked) rather than risk an
815-# unexamined canonical candidate riding through past a truncated scan. Real
   214	   must-fix 1). Adotante que já sofreu um upgrade tem `{{PROTOCOL_SOURCE}}`
   215	   literal no disco. Isso classifica `live_content=edited` ⇒ o veredito é
   216	   `PRESERVE_OWNED` e o ponteiro degradado é **preservado para sempre** —
   217	   verificado em `upgrade.sh` no ramo `PRESERVE_OWNED`/`_lc = edited`.
   218	   Pior: `doctor.sh` e `uninstall.sh` passam a tratar a **degradação do
   219	   próprio framework** como customização do adotante.
   220	
   221	   **Cura:** reconhecedor de corpo legado ⇒ `REFRESH` **com backup**.
   222	
   223	   > **⚠️ CORRIGIDO (rail r1 P1): o reconhecedor é por FINGERPRINT EXATO do
   224	   > corpo inteiro, NUNCA por substring.** Um `PROTOCOL.md` do adotante que
   225	   > legitimamente CONTÉM o token `{{PROTOCOL_SOURCE}}` (documentando-o, ou
   226	   > herdado e editado por cima) seria classificado como lixo por um matcher
   227	   > de substring e força-refreshado — backup não desfaz a perda do arquivo
   228	   > ATIVO. Reconhecer somente hashes exatos dos corpos degradados que o
   229	   > framework historicamente produziu (um por versão que os gerou), e
   230	   > **falhar em direção à preservação** em qualquer não-match. O precedente
   231	   > r20 (`_SPEC_PRISTINE_FINGERPRINTS`) já é exatamente essa forma — segui-lo
   232	   > literalmente, não por analogia frouxa. Isso também fixa a semântica da
   233	   > célula nova da tabela (D2): `live_content=degraded` é determinado por
   234	   > fingerprint exato.
   235	
   236	3. **A FONTE DE VERDADE JÁ EXISTE — o debate a verificou ERRADO** (rail r1
   237	   P1, verificado literalmente; substitui o security must-fix 2 do round 1).
   238	   A "correção" do debate checou a chave errada: `request.PROTOCOL_SOURCE`
   239	   top-level de fato não existe, **mas o install PERSISTE o valor** —
   240	   `install.sh:2523` passa `"ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"` ao
   241	   state writer, que coleta todo `ph.*` em `request.placeholders` e faz
   242	   **UNION entre runs** (novo não-vazio sobrescreve; anterior permanece).
   243	   `PH_PROTOCOL_SOURCE` tem default `$SOURCE_DIR` ⇒ efetivamente sempre
   244	   gravado em installs do install.sh atual.
   245	
   246	   Consequência: **NÃO criar campo novo** — seria uma segunda fonte de
   247	   verdade. O gerador compartilhado **consome e valida**
   248	   `request.placeholders.PROTOCOL_SOURCE`. O fallback (D3: extrair do
   249	   ponteiro são no disco; degradado ⇒ fonte resolvida do upgrade + backup +
   250	   aviso) aplica-se SOMENTE a estados genuinamente antigos/ausentes — e a
   251	   implementação deve verificar se o `upgrade.sh` preserva
   252	   `request.placeholders` ao reescrever o state (se não preserva, esse é um
   253	   sub-defeito do mesmo W2).
   254	
   255	4. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
   256	   exige ponteiro **byte-idêntico**. Precisa cobrir três caminhos, não um
   257	   (security must-fix 3): install→upgrade, **upgrade→upgrade** (idempotência),
   258	   e o **caminho de cura** (corpo degradado ⇒ REFRESH). Inputs
   259	   normalizados (`TARGET`/`PROFILE`/`STACK`/source) ou o teste vira flaky.
   260	
   261	   > **⚠️ BYTE-IDENTIDADE SOZINHA É VACUOSA (rail r1 P1).** Se o gerador
   262	   > compartilhado for acidentalmente baseado no heredoc QUEBRADO do upgrade
   263	   > atual, install e upgrade produzem o MESMO ponteiro errado: bytes
   264	   > idênticos, digest bate com o disco, classificação vira `pristine` e o
   265	   > `OWN-0074` fica verde — vacuosamente. O teste EXIGE, além da identidade,
   266	   > asserções de CONTEÚDO: `{{PROTOCOL_SOURCE}}` **ausente** e a fonte
   267	   > resolvida esperada **presente**, após install, upgrade E migração/cura.
   268	5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   269	   como base; ela já reproduz o defeito.
   270	
   271	**Gate W2 (o anterior era vacuoso — este não):** o digest gravado para
   272	`PROTOCOL.md` **bate com os bytes no disco**, o ponteiro deixa de classificar
   273	`edited` no caminho comum, e **o `OWN-0074` fica VERDE** — o conjunto
   274	esperado de vermelhos encolhe para `{OWN-0016, OWN-0024, OWN-0027}`.
   275	
   300	  ver §W2), registrado como histórico, não como aberto. Um ADR que listasse
   301	  4 abertas estaria stale no momento da criação.
   302	
   303	**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
   304	novo muda a contagem — regenerar as superfícies derivadas).
   305	
   306	## 3. Fronteira canônica
   307	
   308	| Superfície | Guard | Onda |
   309	|---|---|---|
   310	| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
   311	| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
   312	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
   313	| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
   314	
   315	**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
   316	cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
   317	staged, o Owner assina uma vez.
   318	
   319	## 4. Critérios de aceite
   320	
   321	- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
   322	- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros — **JÁ ESTAVA** (`:15`, `:54`); o AC vira uma asserção de regressão, não trabalho.
   323	- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
   324	- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly** — exige CRIAR o job nightly (não existe `schedule:` hoje) e lembrar que `schedule:` ignora `paths:`.
   325	- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina. **O passo é o SCRIPT do §W1.4** (rc semântico + `HARNESS-ERR=0` exigido + diff de conjunto), nunca `--map`.
   326	- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico E com conteúdo certo** (token literal AUSENTE, fonte resolvida PRESENTE — rail r1 P1), com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
   327	- [ ] **AC-6b** Adotante com corpo DEGRADADO (fingerprint exato de corpo que o framework produziu — NUNCA substring; não-match preserva) é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
   328	- [ ] **AC-6c** O gerador consome `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — não criar campo novo), com fallback D3 declarado só para estados antigos/ausentes; verificar que o upgrade preserva `request.placeholders`.
   329	- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
   330	- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
   331	- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
   332	
   333	## 5. Regras do run (herdadas, custaram caro)
   334	
   335	1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
   336	   `git diff HEAD` aplicado se houver sujeira relevante.
   337	2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
   338	3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
   339	   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
   340	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
   341	4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
   342	   defeitos do PLAN-167 foram do INSTRUMENTO
   343	   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
   344	5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
   345	   gerador com 1 de 3 callers convertidos custou 24 regressões.
   346	6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
   347	   PLAN-166 suja.
   348	7. **Esperar por ARTEFATO, nunca por `pgrep`.**
   349	8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
   350	9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.
   351	
   352	## 6. Riscos
   353	
   354	| Risco | Mitigação |
   355	|---|---|
   356	| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
   357	| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
   358	| Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
   359	| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: persistir PROTOCOL_SOURCE; hoje a intenção do adotante NÃO é gravada |
   360	| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
   361	| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
   362	
   363	## 7. Registro de execução
   364	
   365	<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
   366	
   367	- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
   368	  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   369	  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
   370	- **S297 (07/08, retomada):** commit `11cd4f6` pushado. Claims mecânicas do
   371	  plano re-verificadas na árvore viva — **todas conferem** (filtros `:15`/`:54`,
   372	  4 paths com grep=0, zero `schedule:`, `fetch-depth:1` em `:101`, header do
   373	  baseline com paths de máquina, 6 células protocol+upgrade sem REFRESH/DELIVER,
   374	  NOTE do `--map` em `test-ownership-table.sh:690`, `_SPEC_PRISTINE_FINGERPRINTS`
   375	  presente, `PROTOCOL_SOURCE` não persistido, sonda INV-4 presente).
   376	- **Decisões do Owner (07/08, registradas antes de codar):**
   377	  - **D1 (W2 direção): opção (b)** — gerador compartilhado único que
   378	    install/upgrade chamam.
   379	  - **D2 (célula da cura): a tabela GANHA linhas novas** — `live_content`
   380	    ganha o valor `degraded` (corpo com `{{PROTOCOL_SOURCE}}` literal = lixo
   381	    do próprio framework) ⇒ células novas com veredito `REFRESH` (com backup).
   382	    Só ADIÇÃO; os 62 vereditos existentes ficam intocados. O anti-objetivo de
   383	    §0 cede formalmente neste ponto, no molde do precedente r20.
   384	  - **D3 (fallback PROTOCOL_SOURCE): extrair do ponteiro são** no disco e
   385	    persistir; se degradado (literal), usar a fonte resolvida do upgrade +
   386	    backup + aviso. Nunca renomear silenciosamente um ponteiro são.
   387	  - **D4 (nightly): workflow NOVO** `ownership-nightly.yml` (schedule próprio,
   388	    timeout próprio, zero guards nos jobs existentes do `smoke-install.yml`).
   389	- **Rail codex:** 1ª invocação (18:02) foi mal-escopada — diff era um comentário
   390	  inerte sobre draft pré-debate; preservada como `rail/codex-r0-misscoped.md`,
   391	  NÃO conta para o teto do AC-8. r1 re-escopado disparado (plano inteiro como
   392	  diff staged sobre baseline com sujeira aplicada, clone overlay em scratchpad).
   393	- **Rail r1 (re-escopado) CONSUMIDO:** 4 P1 + 3 P2, **7 aceitos / 0
   394	  refutados**, todos verificados contra o código antes de aceitar
   395	  (`rail/codex-r1.md`). Destaque de governança: o P1 "fonte de verdade"
   396	  **derrubou a verificação do debate** — o security checou
   397	  `request.PROTOCOL_SOURCE` (top-level, inexistente) e "corrigiu" uma claim
   398	  CERTA para errada; `install.sh:2523` + writer provam que
   399	  `request.placeholders.PROTOCOL_SOURCE` É persistido (UNION entre runs).
   400	  Fixes aplicados como linhas: §0 (sonda = evidência histórica), §W1.2
   401	  (snippet consome `--print-legacy-tag`), §W1.4 (SCRIPT concreto do gate),
   402	  §W2.2 (fingerprint exato, nunca substring), §W2.3 (consumir chave
   403	  existente), §W2.4 (asserções de conteúdo anti-vacuidade), §W3 (0074
   404	  fechado histórico, 3 abertas), AC-5/6/6b/6c/7.
   405	- **Decisões amendadas pelos achados:** D2 ganha semântica fixa
   406	  (`degraded` = fingerprint exato); D3 vira fallback-only (a fonte primária
   407	  é a chave já persistida).
   408	- **Próxima ação:** rail r2 sobre o plano amendado → W1 item 1 (path filters
   409	  + `ownership-nightly.yml`), em clone overlay (`plan168-dev` já preparado).

exec
/bin/zsh -lc 'tail -180 .claude/plans/PLAN-168/rail/codex-r1.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
    21	
    22	## 0. O que já está provado (não re-investigar)
    23	
    24	| Item | Evidência existente |
    25	|---|---|
    26	| CI não dispara os oráculos | `grep -c` = 0 para os 3 paths novos em `smoke-install.yml`; devops-critique r1 must-fix 1; codex rail r1/r2/r4 |
    27	| `fetch-depth: 1` não traz tags | `smoke-install.yml:101`; o harness precisa de `v1.2.0` para as linhas `legacy_pristine*` |
    28	| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — install=0 ocorrências literais, upgrade=4 |
    29	| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
    30	
    31	**Anti-objetivo:** não mexer na tabela de decisão nem nos vereditos. O
    32	PLAN-167 fechou aquilo com 58/62 e rail de 4 rodadas. Aqui só se fecha o
    33	entorno.
    34	
    35	## 1. O problema, em uma frase cada
    36	
    37	**W1 — teste que não roda apodrece.** Os dois oráculos do PLAN-167
    38	(`test-ownership-verdict-unit.sh`, `test-ownership-table.sh`) não estão em
    39	nenhum path filter. Um PR que altere a tabela, o harness ou o `_hash_lib.sh`
    40	**pula o gate inteiro**. É literalmente a classe do achado r10-F4 — um teste
    41	cuja única execução em CI era pulada — reaparecendo no trabalho que a
    42	consertou.
    43	
    44	**W2 — todo upgrade quebra o ponteiro raiz.** `install.sh` escreve
    45	`PROTOCOL.md` e **substitui** os placeholders; `upgrade.sh` regenera do
    46	heredoc e deixa `{{PROTOCOL_SOURCE}}` **literal**. Qualquer adotante cujo
    47	checkout esteja fora do target fica com um arquivo que não diz mais onde o
    48	protocolo mora. É a classe *install-set ≠ upgrade-set* que a decisão (i) do
    49	ADR-155 existe para eliminar: a enumeração compartilhada resolveu QUAIS
    50	caminhos os dois lados tocam, nunca QUE CONTEÚDO produzem.
    51	
    52	**W3 — o contrato não tem ADR.** A tabela de decisão é hoje a autoridade
    53	sobre propriedade, e vive só num `docs/`. Sem ADR, a próxima pessoa que
    54	"consertar uma assimetria" não tem onde ler que ela é decidida.
    55	
    56	## 2. Ondas
    57	
    58	### W1 — CI wiring (CANÔNICO: `.github/workflows/` exige cerimônia)
    59	
    60	1. Adicionar aos **dois** filtros (`pull_request` e `push`) de
    61	   `smoke-install.yml`:
    62	   ```
    63	   scripts/tests/test-ownership-table.sh
    64	   scripts/tests/test-ownership-verdict-unit.sh
    65	   scripts/tests/ownership_table.tsv
    66	   docs/ownership-decision-table.md
    67	   scripts/_hash_lib.sh
    68	   ```
    69	   O `_hash_lib.sh` é o r10-F4 literal: os oráculos usam `_hash_file`/
    70	   `_hash_stdin`, e hoje um PR que só toque o helper pula a suíte.
    71	2. **Buscar o tag `v1.2.0`** antes do passo dos oráculos (espelhar o fetch do
    72	   pin de paridade que já existe no arquivo):
    73	   ```yaml
    74	   - name: Fetch the legacy_pristine tag
    75	     run: |
    76	       git fetch --no-tags --depth 1 origin +refs/tags/v1.2.0:refs/tags/v1.2.0
    77	       git rev-parse --verify refs/tags/v1.2.0
    78	   ```
    79	   **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
    80	   que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
    81	   (rejeitada no consenso do round 1 do PLAN-167).
    82	3. **Dois gates, dois tempos** — a divisão é o produto do W2 do PLAN-167:
    83	   - **por-PR:** `test-ownership-verdict-unit.sh` (segundos, 60 células)
    84	   - **nightly:** `test-ownership-table.sh` (~25 min, 62 installs reais)
    85	   O e2e **não cabe** no teto de 25 min do job atual — o orçamento já foi
    86	   elevado 4× (5→8→20→25). Colocá-lo no caminho por-PR quebra o job.
    87	4. O e2e termina com **4 vermelhos deliberados**. O passo de CI precisa
    88	   aceitar isso explicitamente (comparar contra `ownership-baseline-map.txt`,
    89	   não exigir rc=0) **e falhar se o conjunto de vermelhos MUDAR** — inclusive
    90	   se encolher. Verde total significa que a tabela mudou.
    91	
    92	**Gate W1:** um PR tocando só `ownership_table.tsv` dispara o workflow (hoje
    93	não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
    94	
    95	### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
    96	
    97	1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
    98	   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
    99	   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
   100	     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
   101	     em vez de o sintoma.
   102	   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
   103	2. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
   104	   exige que o ponteiro seja **byte-idêntico** nos dois caminhos. Sem isso a
   105	   divergência volta — nenhuma asserção de propriedade a enxerga, porque o
   106	   registro está certo e os bytes errados.
   107	3. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   108	   como base do teste; ela já reproduz o defeito.
   109	
   110	**Gate W2:** a sonda passa a reportar 0 ocorrências literais após o upgrade,
   111	e o teste novo falha se alguém reverter.
   112	
   113	### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
   114	
   115	Registrar como contrato:
   116	- as **10 dimensões** e o enum final (**4 vereditos** após o colapso da OQ-9
   117	  ratificado pelo Owner: `DELIVER · REFRESH · PRESERVE_OWNED ·
   118	  PRESERVE_UNOWNED`; `ABORT_SURFACE` é **falha de execução**, não veredito);
   119	- **INV-1..INV-4** (as quatro invariantes cross-surface);
   120	- a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
   121	  `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
   122	  é a que mais convida um "conserto" futuro;
   123	- que o `ADR-155-AMEND-1` é **emendado**, não revogado;
   124	- as 4 células conhecidas-abertas com causa, e que **2 são defeito do TESTE**.
   125	
   126	**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
   127	novo muda a contagem — regenerar as superfícies derivadas).
   128	
   129	## 3. Fronteira canônica
   130	
   131	| Superfície | Guard | Onda |
   132	|---|---|---|
   133	| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
   134	| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
   135	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
   136	| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
   137	
   138	**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
   139	cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
   140	staged, o Owner assina uma vez.
   141	
   142	## 4. Critérios de aceite
   143	
   144	- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
   145	- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros (r10-F4 fechado de verdade).
   146	- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
   147	- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly**.
   148	- [ ] **AC-5** O passo de CI falha se o CONJUNTO de vermelhos mudar — inclusive encolher.
   149	- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico**, com teste que prova.
   150	- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria e as 4 abertas.
   151	- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
   152	- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
   153	
   154	## 5. Regras do run (herdadas, custaram caro)
   155	
   156	1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
   157	   `git diff HEAD` aplicado se houver sujeira relevante.
   158	2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
   159	3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
   160	   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
   161	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
   162	4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
   163	   defeitos do PLAN-167 foram do INSTRUMENTO
   164	   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
   165	5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
   166	   gerador com 1 de 3 callers convertidos custou 24 regressões.
   167	6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
   168	   PLAN-166 suja.
   169	7. **Esperar por ARTEFATO, nunca por `pgrep`.**
   170	8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
   171	9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.
   172	
   173	## 6. Riscos
   174	
   175	| Risco | Mitigação |
   176	|---|---|
   177	| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
   178	| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
   179	| Fix do ponteiro quebra adotantes com placeholder já literal | o teste do AC-6 cobre install→upgrade; testar também upgrade→upgrade |
   180	| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
   181	
   182	## 7. Registro de execução
   183	
   184	<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
   185	
   186	- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
   187	  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   188	  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
   189	- **Próxima ação:** W1 item 1 (path filters), em clone overlay.
   190	
   191	<!-- rail: revise ESTE plano -->

--- REPO ---
./PLAN-168.md
./baseline-map.txt
./smoke-install.yml

codex
The only change adds an inert HTML comment to a Markdown planning document and does not affect code, tests, or documented behavior.
The only change adds an inert HTML comment to a Markdown planning document and does not affect code, tests, or documented behavior.

exec
/bin/zsh -lc "grep -nE '\"findings\"|\\[P[0-3]\\]' .claude/plans/PLAN-168/rail/codex-r1.md | tail -30" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
exec
/bin/zsh -lc "grep -nE 'P1|P2|priority|overall_correctness|rail r1|fingerprint' .claude/plans/PLAN-168/rail/codex-r1.md | tail -80" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
87:    26	| CI não dispara os oráculos | `grep -c` = 0 para os 3 paths novos em `smoke-install.yml`; devops-critique r1 must-fix 1; codex rail r1/r2/r4 |
222:   161	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).

exec
/bin/zsh -lc "git diff --cached --check; find .claude/scripts -maxdepth 1 -type f -name 'check-*' -o -name '*plan*' | sort | sed -n '1,200p'; grep -R -nE 'budget_tokens|status: reviewed|reviewed_at|PLAN-[0-9]+.*frontmatter' .claude/scripts tests | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 454ms:
.claude/scripts/swarm/loop_runner.py:378:    budget_tokens: int
.claude/scripts/swarm/loop_runner.py:398:        if self.budget_tokens <= 0:
.claude/scripts/swarm/loop_runner.py:399:            raise ValueError("budget_tokens must be > 0")
.claude/scripts/swarm/coordinator.py:94:    ``budget_tokens`` MUST be strictly positive — zero/negative raises
.claude/scripts/swarm/coordinator.py:99:    budget_tokens: int
.claude/scripts/swarm/coordinator.py:112:        if self.budget_tokens <= 0:
.claude/scripts/swarm/coordinator.py:113:            raise ValueError("budget_tokens must be > 0")
.claude/scripts/swarm/coordinator.py:378:        budget_tokens=cfg.budget_tokens,
.claude/scripts/swarm/coordinator.py:487:            budget_tokens=args.budget_tokens,
.claude/scripts/swarm/recovery.py:51:    budget_tokens: int = 0
.claude/scripts/swarm/recovery.py:76:            budget_tokens=int(data.get("budget_tokens", 0)),
.claude/scripts/swarm/recovery.py:89:    budget_tokens: int,
.claude/scripts/swarm/recovery.py:105:        budget_tokens=budget_tokens,
.claude/scripts/swarm/tests/test_optimizer_killswitch.py:175:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_optimizer_killswitch.py:190:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_optimizer_killswitch.py:202:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:63:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:74:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:85:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:97:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:111:        loops, budget_tokens=1000, env={"CEO_SWARM": "1"}
.claude/scripts/swarm/tests/test_kill_switch.py:124:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:137:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:150:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:181:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:194:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:212:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:229:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:248:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:261:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:277:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:293:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_kill_switch.py:303:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:41:            budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:53:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:72:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:90:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:106:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:131:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:146:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner.py:163:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_coordinator.py:58:    cfg = co.SwarmConfig(n_loops=20, budget_tokens=1000, goal="bench")
.claude/scripts/swarm/tests/test_coordinator.py:64:        co.SwarmConfig(n_loops=0, budget_tokens=1000, goal="g")
.claude/scripts/swarm/tests/test_coordinator.py:68:    with pytest.raises(ValueError, match="budget_tokens"):
.claude/scripts/swarm/tests/test_coordinator.py:69:        co.SwarmConfig(n_loops=2, budget_tokens=0, goal="g")
.claude/scripts/swarm/tests/test_coordinator.py:74:        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="g", jaccard_threshold=1.5)
.claude/scripts/swarm/tests/test_coordinator.py:79:        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="   ")
.claude/scripts/swarm/tests/test_coordinator.py:84:        co.SwarmConfig(n_loops=2, budget_tokens=1000, goal="g", max_strikes=0)
.claude/scripts/swarm/tests/test_coordinator_production_integration.py:84:        budget_tokens=10_000_000,
.claude/scripts/swarm/tests/test_recovery.py:28:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_recovery.py:57:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_recovery.py:64:    assert cp.budget_tokens == 1000
.claude/scripts/swarm/tests/test_recovery.py:160:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_coordinator_tick.py:24:        n_loops=2, budget_tokens=100, goal="x",
.claude/scripts/swarm/tests/test_coordinator_tick.py:161:        loops, cfg=_cfg(budget_tokens=100),
.claude/scripts/swarm/tests/test_loop_runner_circuit_breaker.py:62:        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_circuit_breaker.py:495:                    budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_gate_kill_switch.py:77:            budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_gate_kill_switch.py:137:                        budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_gate_enforcement.py:129:            budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_gate_enforcement.py:206:                budget_tokens=1000,
.claude/scripts/swarm/tests/test_loop_runner_sentinel_revocation_slo.py:96:                    budget_tokens=1000,
.claude/scripts/swarm/kill_switch.py:140:    budget_tokens: int,
.claude/scripts/swarm/kill_switch.py:192:    if loops and budget_exceeded(loops, budget_tokens):
.claude/scripts/policy-shadow-runner.py:89:    ("'reviewed' requires", "missing_reviewed_at"),
.claude/scripts/policy-shadow-runner.py:244:                    if derived.get("reviewed_at_present"):
.claude/scripts/policy-shadow-runner.py:245:                        fm["reviewed_at"] = "2026-01-01"
.claude/scripts/plan-tokens.py:2:"""plan-tokens.py — Auto-generate budget_tokens estimates from a plan's §4 phase table.
.claude/scripts/plan-tokens.py:16:  --inject           — writes budget_tokens: directly into plan frontmatter (idempotent)
.claude/scripts/plan-tokens.py:649:    """Build the budget_tokens frontmatter string from estimates."""
.claude/scripts/plan-tokens.py:668:    """Write budget_tokens: into plan frontmatter. Idempotent (CR-N6).
.claude/scripts/plan-tokens.py:672:    2. budget_tokens: already present → replace existing value
.claude/scripts/plan-tokens.py:674:    4. Multi-key frontmatter → find and replace budget_tokens key
.claude/scripts/plan-tokens.py:679:    new_line = f"budget_tokens: {value}"
.claude/scripts/plan-tokens.py:698:    # Check if budget_tokens already present in frontmatter
.claude/scripts/plan-tokens.py:700:        if lines[i].startswith("budget_tokens:"):
.claude/scripts/plan-tokens.py:747:            "Auto-generate budget_tokens estimates from a plan's §4 phase table. "
.claude/scripts/plan-tokens.py:761:        help="Write budget_tokens: into plan frontmatter (idempotent).",
.claude/scripts/plan-tokens.py:826:            f"[plan-tokens] injected budget_tokens into {plan_path}\n"
.claude/scripts/check-roadmap-binding.py:76:    # PLAN-105 R2 P2 fold — line-anchored frontmatter parse (split on
.claude/scripts/context-budget.py:1524:    budget_tokens: Any,
.claude/scripts/context-budget.py:1543:    budget_tokens
.claude/scripts/context-budget.py:1561:        "budget_tokens": int,       # the budget projected against
.claude/scripts/context-budget.py:1583:        "budget_tokens": 0,
.claude/scripts/context-budget.py:1604:        budget = int(budget_tokens)
.claude/scripts/context-budget.py:1610:    plan["budget_tokens"] = budget
.claude/scripts/context-budget.py:2109:        budget = args.budget_tokens if args.budget_tokens is not None else 0
.claude/scripts/validate-skill-frontmatter.py:27:  .claude/plans/PLAN-074/staging/validate-skill-frontmatter.py
.claude/scripts/tests/test_smart_loading_resolver.py:62:    context_budget_tokens: int = 500,
.claude/scripts/tests/test_smart_loading_resolver.py:73:        "context_budget_tokens": context_budget_tokens,
.claude/scripts/tests/test_smart_loading_resolver.py:92:            context_budget_tokens=300,
.claude/scripts/tests/test_smart_loading_resolver.py:113:                context_budget_tokens=400,
.claude/scripts/tests/test_smart_loading_resolver.py:163:    """AC-b — sum of context_budget_tokens across active set <= 30000."""
.claude/scripts/tests/test_smart_loading_resolver.py:174:                context_budget_tokens=2000,
.claude/scripts/tests/test_smart_loading_resolver.py:518:            self.assertEqual(table[p]["context_budget_tokens"], 30000)
.claude/scripts/tests/test_smart_loading_resolver.py:541:context_budget_tokens: 1400
.claude/scripts/tests/test_smart_loading_resolver.py:554:context_budget_tokens: 400
.claude/scripts/tests/test_smart_loading_resolver.py:579:context_budget_tokens: 500
.claude/scripts/tests/test_smart_loading_resolver.py:587:context_budget_tokens: 400
.claude/scripts/tests/test_smart_loading_resolver.py:638:# PLAN-094 Wave B — File-backed frontmatter cache (R-039)

exec
/bin/zsh -lc "grep -R '"'^budget_tokens:'"' .claude/plans/PLAN-*.md | tail -30; grep -R '"'^status: reviewed'"' .claude/plans/PLAN-*.md | tail -10" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
.claude/plans/PLAN-139-canonical-invariants-and-debt-ledger.md:budget_tokens: 90-170k            # EXECUTION only. Wave A ≈50k (S) · Wave B ≈70k (M) · Wave V Codex ≈40k. Rite (harvest+debate+validation) already spent S243.
.claude/plans/PLAN-140-compaction-hook-origin-dropfix.md:budget_tokens: 5-10k               # two one-line Edits + re-run of the compaction-continuity test
.claude/plans/PLAN-141-mcp-smoke-staging-ruff-tolerance.md:budget_tokens: 5-10k
.claude/plans/PLAN-142-codex-cli-0139-adapter-migration.md:budget_tokens: TBD
.claude/plans/PLAN-152-v1-0-1-hardening-sweep.md:budget_tokens: 400-700k
.claude/plans/PLAN-153-ecc-comparative-uplift.md:budget_tokens: 2.0-2.8M
.claude/plans/PLAN-154-gated-learning-loop.md:budget_tokens: 400-700k
.claude/plans/PLAN-155-codex-harness-compat.md:budget_tokens: 0.95-1.4M
.claude/plans/PLAN-156-FOLLOWUP-council-livefire-findings.md:budget_tokens: 90-140k
.claude/plans/PLAN-156-grok-harness-56-refresh-council.md:budget_tokens: 1.2-1.8M
.claude/plans/PLAN-157-architect-graduation.md:budget_tokens: 400-600k
.claude/plans/PLAN-158-release-v1-1-0.md:budget_tokens: 120-180k
.claude/plans/PLAN-159-perf-gate-robustness.md:budget_tokens: 120-180k
.claude/plans/PLAN-160-canonical-edit-council-findings.md:budget_tokens: 120-180k
.claude/plans/PLAN-161-maintenance-sweep.md:budget_tokens: 200-300k
.claude/plans/PLAN-162-canonical-edit-council-s280-triage.md:budget_tokens: 120-180k
.claude/plans/PLAN-163-substrate-uplift.md:budget_tokens: 250-350k
.claude/plans/PLAN-164-pair-rail-timeout-uplift.md:budget_tokens: 60-120k
.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:budget_tokens: 90-140k
.claude/plans/PLAN-166-release-hold-findings-closure.md:budget_tokens: 90-140k
.claude/plans/PLAN-167-ownership-decision-table.md:budget_tokens: 180-260k
.claude/plans/PLAN-168-ownership-followups-closure.md:budget_tokens: 120-180k
.claude/plans/PLAN-SCHEMA.md:budget_tokens: 95-130k           # CEO-context tokens (range or single estimate)
.claude/plans/PLAN-167-ownership-decision-table.md:status: reviewed
.claude/plans/PLAN-168-ownership-followups-closure.md:status: reviewed
.claude/plans/PLAN-SCHEMA.md:status: reviewed

exec
/bin/zsh -lc 'git log --oneline --decorate -8; git tag --list | tail -20; git show 7c0828a''^:scripts/upgrade.sh 2>/dev/null | nl -ba | sed -n '"'1510,1585p'; git show 7c0828a"'^:scripts/upgrade.sh 2>/dev/null | grep -n -A35 '"'_refresh_protocol_pointer()' | head -60" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-LzE15XP7' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-S3SPUSej' (errno=Operation not permitted)
4234282 (HEAD -> main) rail-scope: plano removido do baseline — reentra como diff não-commitado
d4c494c baseline: árvore com cerimônia PLAN-166 aplicada (estado que o W1 vai editar)
11cd4f6 (origin/main, origin/HEAD) plan(PLAN-167): §9 final — cerimônia executada, pack landado
287c14d governance(PLAN-168): registro de colisão de escrita no debate — erro meu
ec4bdcf fix(PLAN-168): premissa do W2 estava OBSOLETA — meu próprio land a invalidou
8ab0557 fix(PLAN-168): fecho um gate vacuoso no harness que EU construí
b0ec35f plan(PLAN-168): reviewed — debate 3 ADJUST/0 VETO; e uma classificação MINHA corrigida
7c0828a feat(PLAN-167): ownership decision table — one function decides, callers execute
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-3tQdqbwP' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-MxG68vZR' (errno=Operation not permitted)
v1.0.0
v1.0.1
v1.0.1-rc.1
v1.1.0
v1.1.0-rc.1
v1.2.0
v1.2.0-rc.1
v1.2.0-rc.2
v1.2.0-rc.3
v1.3.0-rc.1
  1510	  #     S238 acme case) lost it irrecoverably. This backup applies EVEN when
  1511	  #     no baseline manifest exists — making the loss recoverable on a first
  1512	  #     upgrade (Codex R1 P0 first-upgrade safety).
  1513	  if [[ -f "$pointer" ]]; then
  1514	    mkdir -p "$BAK_DIR" 2>/dev/null || true
  1515	    cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1516	    echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
  1517	  fi
  1518	
  1519	  # (b) When a baseline manifest is loaded, classify the root PROTOCOL.md
  1520	  #     against the recorded install-time pointer hash. The pointer's "source"
  1521	  #     is a generated string (not a file in $SOURCE_DIR), so we compare the
  1522	  #     CURRENT target hash against the recorded BASELINE only:
  1523	  #       H_dst == H_base  -> still the generated pointer -> safe to refresh
  1524	  #       H_dst != H_base  -> adopter customized it -> ADOPTER-CUSTOMIZED:
  1525	  #                           preserve (default/refuse) or overwrite per
  1526	  #                           --on-conflict={theirs|backup}.
  1527	  if [[ -f "$pointer" && -n "$_BASELINE_MANIFEST_FILE" ]] && command -v _hash_file >/dev/null 2>&1; then
  1528	    local _rp_base _rp_dst
  1529	    _rp_base="$( _baseline_lookup "PROTOCOL.md" || true )"
  1530	    _rp_dst="$( _hash_file "$pointer" 2>/dev/null || true )"
  1531	    if [[ -n "$_rp_base" && -n "$_rp_dst" && "$_rp_dst" != "$_rp_base" ]]; then
  1532	      case "$ON_CONFLICT" in
  1533	        theirs|backup)
  1534	          # Original already backed up above; proceed to refresh.
  1535	          echo "    OVERWROTE (root PROTOCOL.md ADOPTER-CUSTOMIZED, --on-conflict=$ON_CONFLICT; original in $BAK_DIR/PROTOCOL.md)" >&2
  1536	          ;;
  1537	        *)  # refuse (default): preserve the customized root PROTOCOL.md.
  1538	          echo "    PRESERVED (root PROTOCOL.md ADOPTER-CUSTOMIZED — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
  1539	          return 0
  1540	          ;;
  1541	      esac
  1542	    fi
  1543	  fi
  1544	
  1545	  cat > "$pointer" <<EOF
  1546	# Protocol reference
  1547	
  1548	$body
  1549	EOF
  1550	  echo "    REFRESHED: PROTOCOL.md pointer"
  1551	}
  1552	
  1553	has_profile() {
  1554	  local p="$1"
  1555	  for part in "${PROFILE_PARTS[@]}"; do
  1556	    if [[ "$part" == "$p" ]]; then
  1557	      return 0
  1558	    fi
  1559	  done
  1560	  return 1
  1561	}
  1562	
  1563	# ---------------------------------------------------------------------------
  1564	# PLAN-135 W1 (unit w0r) — pre-flight model-deprecation advisory.
  1565	# Runs check-model-deprecations.py --check against the TARGET when the checker
  1566	# is available (source copy preferred — fresher ledger; falls back to the
  1567	# target's installed copy). NEVER blocks the upgrade: findings emit stderr
  1568	# WARNING lines (F-CHAOS-3 convention); any infra failure (no python3, corrupt
  1569	# ledger, unexpected rc) degrades to a NOTE and the upgrade proceeds
  1570	# (fail-open per CLAUDE.md §5). Suppress with --no-deprecation-warn.
  1571	# ---------------------------------------------------------------------------
  1572	_emit_deprecation_warnings() {
  1573	  [[ "$DEPRECATION_WARN" -eq 1 ]] || return 0
  1574	  local checker=""
  1575	  if [[ -f "$SOURCE_DIR/.claude/scripts/check-model-deprecations.py" ]]; then
  1576	    checker="$SOURCE_DIR/.claude/scripts/check-model-deprecations.py"
  1577	  elif [[ -f "$TARGET/.claude/scripts/check-model-deprecations.py" ]]; then
  1578	    checker="$TARGET/.claude/scripts/check-model-deprecations.py"
  1579	  fi
  1580	  [[ -n "$checker" ]] || return 0
  1581	  if ! command -v python3 >/dev/null 2>&1; then
  1582	    echo "    NOTE: model-deprecation scan skipped (python3 not found) — advisory only" >&2
  1583	    return 0
  1584	  fi
  1585	  local dep_rc=0
1459:_refresh_protocol_pointer() {
1460-  local pointer="$TARGET/PROTOCOL.md"
1461-  local body
1462-  case "$SOURCE_DIR" in
1463-    "$TARGET"/*)
1464-      local rel="${SOURCE_DIR#$TARGET/}"
1465-      body="The full CEO orchestration protocol lives at:
1466-./${rel}/PROTOCOL.md
1467-
1468-To pull updates:
1469-  ( cd ./${rel} && git pull )
1470-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
1471-      ;;
1472-    *)
1473-      body="The full CEO orchestration protocol lives at:
1474-{{PROTOCOL_SOURCE}}/PROTOCOL.md
1475-
1476-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
1477-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
1478-
1479-To pull updates:
1480-  ( cd {{PROTOCOL_SOURCE}} && git pull )
1481-  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
1482-      ;;
1483-  esac
1484-
1485-  # PLAN-138 C.7 fix (Codex R2 P0): compute the CANONICAL pointer hash — the
1486-  # hash of exactly what the framework WOULD write below (heredoc body) — and
1487-  # export it so the post-upgrade manifest rewrite records THAT as the
1488-  # PROTOCOL.md baseline, never the current target file. Without this, a
1489-  # preserved adopter-customized PROTOCOL.md would be re-recorded as its own
1490-  # baseline and the NEXT upgrade would read H_dst==H_base and clobber it.
1491-  # Computed on ALL paths (preserve + refresh) so it is set whenever the C.7
1492-  # rewrite runs. printf reproduces the heredoc byte-for-byte.
1493-  _REFRESH_PROTOCOL_CANON_HASH=""
1494-  if command -v _hash_stdin >/dev/null 2>&1; then

exec
/bin/zsh -lc "grep -n -A90 -B25 '_fixture_protocol\\|surface.*protocol\\|protocol)' scripts/tests/test-ownership-table.sh | sed -n '1,360p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
74-elif command -v gtimeout >/dev/null 2>&1; then _TIMEOUT_BIN="gtimeout"; fi
75-
76-_run_with_timeout() {  # $1 = seconds; rest = command
77-  local secs="$1"; shift
78-  if [[ -n "$_TIMEOUT_BIN" ]]; then
79-    "$_TIMEOUT_BIN" "$secs" "$@"
80-    return $?
81-  fi
82-  # Fallback: background + watchdog. Kills the process group so a blocked cp
83-  # inside the script dies with it.
84-  "$@" &
85-  local pid=$!
86-  ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) &
87-  local watch=$!
88-  wait "$pid" 2>/dev/null
89-  local rc=$?
90-  kill "$watch" 2>/dev/null
91-  wait "$watch" 2>/dev/null
92-  return $rc
93-}
94-
95-# --- surface geometry -------------------------------------------------------
96-_relpath_for() {
97-  case "$1" in
98-    spec)     printf 'SPEC/v1' ;;
99:    protocol) printf 'PROTOCOL.md' ;;
100-    marker)   printf '.claude/.framework-version' ;;
101-    *) return 1 ;;
102-  esac
103-}
104-MANIFEST_REL=".claude/.install-manifest.sha256"
105-
106-# --- observation primitives -------------------------------------------------
107-_obs_type() {  # $1 = abs path -> the live_type vocabulary
108-  local p="$1"
109-  if   [[ -L "$p" ]]; then printf 'symlink'
110-  elif [[ ! -e "$p" ]]; then printf 'absent'
111-  elif [[ -d "$p" ]]; then
112-    if [[ -z "$( ls -A "$p" 2>/dev/null )" ]]; then printf 'dir_empty'; else printf 'dir'; fi
113-  elif [[ -p "$p" || -S "$p" || -b "$p" || -c "$p" ]]; then printf 'special'
114-  elif [[ -f "$p" ]]; then printf 'regular'
115-  else printf 'special'; fi
116-}
117-
118-# Content digest of a surface, whatever its shape. Directory digest reproduces
119-# upgrade.sh's _spec_tree_fingerprint semantics (sorted "<sha>  <rel>" lines).
120-_obs_digest() {  # $1 = abs path
121-  local p="$1" lines
122-  if [[ -L "$p" ]]; then printf 'link:%s' "$( readlink "$p" 2>/dev/null || true )"; return 0; fi
123-  if [[ ! -e "$p" ]]; then printf 'absent'; return 0; fi
124-  if [[ -d "$p" ]]; then
125-    lines="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
126-      | while IFS= read -r r; do
127-          [[ -n "$r" ]] || continue
128-          printf '%s  %s\n' "$( _hash_file "$p/$r" 2>/dev/null || echo FAIL )" "$r"
129-        done )"
130-    [[ -z "$lines" ]] && { printf 'emptydir'; return 0; }
131-    printf '%s' "$( printf '%s\n' "$lines" | _hash_stdin )"
132-    return 0
133-  fi
134-  if [[ -f "$p" ]]; then printf '%s' "$( _hash_file "$p" 2>/dev/null || echo UNREADABLE )"; return 0; fi
135-  printf 'special'
136-}
137-
138-# Modification-time signature of a surface. BSD stat takes -f, GNU takes -c;
139-# both are tried so the harness behaves the same on macOS and CI.
140-_stat_mtime() {  # $1 = abs path
141-  stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null || printf '0'
142-}
143-_obs_mtime() {  # $1 = abs path -> newest mtime under it (or its own)
144-  local p="$1" newest=0 m r
145-  if [[ -L "$p" || ! -e "$p" ]]; then printf '%s' "$( _stat_mtime "$p" )"; return 0; fi
146-  if [[ -d "$p" ]]; then
147-    while IFS= read -r r; do
148-      [[ -n "$r" ]] || continue
149-      m="$( _stat_mtime "$p/$r" )"
150-      [[ "$m" =~ ^[0-9]+$ ]] || continue
151-      (( m > newest )) && newest="$m"
152-    done < <( cd "$p" && find . -type f -print 2>/dev/null )
153-    printf '%s' "$newest"; return 0
154-  fi
155-  printf '%s' "$( _stat_mtime "$p" )"
156-}
157-
158-# The manifest's record for a relpath: "" | "hash:<64hex>" | "link:<target>"
159-# For SPEC/v1 the record may be per-file rows; presence of ANY row counts, and
160-# the digest reported is the tree-shaped roll-up of those rows.
161-_obs_record() {  # $1 = manifest abs path, $2 = relpath
162-  local m="$1" rel="$2" line rows
163-  [[ -f "$m" ]] || { printf ''; return 0; }
164-  line="$( grep -E "^LINK  ${rel//./\\.}  " "$m" 2>/dev/null | head -1 || true )"
165-  if [[ -n "$line" ]]; then printf 'link:%s' "${line#LINK  $rel  }"; return 0; fi
166-  line="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}$" "$m" 2>/dev/null | head -1 || true )"
167-  if [[ -n "$line" ]]; then printf 'hash:%s' "${line%% *}"; return 0; fi
168-  # tree surface: any per-file row under the relpath
169-  rows="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}/" "$m" 2>/dev/null || true )"
170-  if [[ -n "$rows" ]]; then
171-    printf 'hash:%s' "$( printf '%s\n' "$rows" | LC_ALL=C sort | _hash_stdin )"
172-    return 0
173-  fi
174-  printf ''
175-}
176-
177-# Refusal markers — the operator-visible contract of ABORT_SURFACE. Matching
178-# output is a deliberate choice, recorded in docs §6 (OQ-1/OQ-2): a refusal is
179-# defined by the framework having ATTEMPTED and declined, which leaves no
180-# filesystem trace at all. If this wording changes, this test fails loudly —
181-# which is correct, because the operator-visible contract changed.
182-# Only GENUINE execution failures. Refusing to act on an unsupported
183-# destination is a DECISION (the surface is adopter-owned), not a failed
184-# attempt — conflating them made the e2e and the decision function disagree
185-# about the same cell (round-1 consensus C2).
186-_ABORT_MARKERS='REFUSING to|could not back up|backup-before-replace'
187-
188-# =============================================================================
189-# Fixtures
--
322-  esac
323-
324-  case "$lcontent" in
325-    edited)
326-      if [[ -d "$p" && ! -L "$p" ]]; then
327-        local victim
328-        victim="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
329-        victim="${victim#./}"
330-        # Guard the empty-tree case: without it the redirect target collapses to
331-        # "$p/" and the shell reports "Is a directory" instead of mutating.
332-        # if/fi, NOT `[[ ]] && cmd`: as the last statement of the branch, a
333-        # false test would make the whole function return 1 and the row would
334-        # be recorded as a harness error rather than run.
335-        if [[ -n "$victim" ]]; then
336-          printf '\nADOPTER EDIT\n' >> "$p/$victim"
337-        fi
338-      elif [[ -f "$p" && ! -L "$p" ]]; then
339-        printf 'ADOPTER EDIT\n' >> "$p"
340-      fi
341-      ;;
342-    pristine)
343-      # "byte-identical to what THIS run's source would deliver" — so it must be
344-      # synced from the RUN source, not left as whatever the base install wrote.
345-      # The generated pointer has no source file: the base install's own output
346-      # IS its pristine form, so protocol is left untouched.
347:      if [[ "$surface" != "protocol" && -e "$src_root/$rel" && ! -L "$p" ]]; then
348-        rm -rf "$p"; mkdir -p "$( dirname "$p" )"; cp -R "$src_root/$rel" "$p" 2>/dev/null || true
349-      fi
350-      ;;
351-    legacy_pristine)
352-      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
353-      # derived from — never a hand-built approximation, which would test the
354-      # fixture rather than the migration.
355-      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
356-        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
357-        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
358-        echo "             approximation. A CI checkout using fetch-depth:1 has NO tags" >&2
359-        echo "             — that job needs fetch-depth:0 or fetch-tags:true." >&2
360-        return 1
361-      fi
362-      rm -rf "$p"; mkdir -p "$p"
363-      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
364-        | ( cd "$T" && tar -xf - ) || return 1
365-      ;;
366-    legacy_pristine_partial)
367-      # A pristine shipped tree that ALSO carries an entry the fingerprint
368-      # cannot inventory. Distinct from `edited`: every regular file still
369-      # matches a shipped release, so content alone reads "pristine" — and the
370-      # tree must STILL be refused, because a partial inventory can never
371-      # certify a wholesale replace (ADR-155-AMEND-1 §4).
372-      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
373-        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
374-        return 1
375-      fi
376-      rm -rf "$p"; mkdir -p "$p"
377-      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
378-        | ( cd "$T" && tar -xf - ) || return 1
379-      ln -s /dev/null "$p/adopter-added.link" 2>/dev/null || true
380-      ;;
381-  esac
382-
383-}
384-
385-# =============================================================================
386-# Verdict derivation
387-# =============================================================================
388-_derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 operation
389-  # $3 (before-record) went unused when OQ-9 collapsed OMIT_RECORD into
390-  # PRESERVE_UNOWNED: what a record USED to be no longer changes the name.
391-  local bd="$1" ad="$2" ar="$4" out="$5" surface="$6" rel="$7" op="${8:-upgrade}"
392-  if [[ "$bd" != "$ad" ]]; then
393-    if [[ "$bd" == "absent" ]]; then printf 'DELIVER'; else printf 'REFRESH'; fi
394-    return 0
395-  fi
396-  # Unchanged target from here on.
397-  if grep -Eq "$_ABORT_MARKERS" "$out" 2>/dev/null; then printf 'ABORT_SURFACE'; return 0; fi
398-  # A REFRESH that writes byte-identical content leaves the CONTENT unchanged,
399-  # so a content digest alone cannot separate it from a PRESERVE.
400-  #
401-  # Backup presence does not settle it either: the ADOPTER-FORK preserve path
402-  # also snapshots into BAK_DIR, so "a backup exists" is evidence the framework
403-  # looked, not that it wrote.
404-  #
405-  # Modification time settles it on the UPGRADE path, from state and without
406-  # reading prose: the forced route replaces content with `cp -R` (no -p),
407-  # which stamps new mtimes, while every preserve path leaves bytes AND
408-  # timestamps alone.
409-  #
410-  # Restricted to upgrade deliberately. install.sh re-runs placeholder
411-  # SUBSTITUTION on every invocation, so it rewrites the pointer with identical
412-  # bytes and a fresh mtime — a write with no semantic content. Counting that
413-  # as REFRESH would report an ownership change where none happened.
414-  #
415-  # No single signal is valid everywhere here: the content digest cannot see an
416-  # identical-content refresh, the backup fires on the preserve-with-snapshot
417-  # path, and mtime fires on install re-substitution. Each is used only where
418-  # it is sound, and the boundary is stated rather than assumed.
419-  if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
420-    printf 'REFRESH'; return 0
421-  fi
422-  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
423-  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
424-  if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
425-}
426-
427-_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
428-  local surface="$1" ar="$2" pr="$3" src="$4"
429-  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
430-  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac
431-
432-  local got="${ar#hash:}"
433-  local rel; rel="$( _relpath_for "$surface" )"
434-
435-  # Candidate 1: the bytes now at the target.
436-  local c_target; c_target="$( _obs_digest "$T/$rel" )"
437-  # Candidate 2: the framework's copy in the source checkout.
--
443-
444-  # For tree surfaces the recorded value is the roll-up of per-file rows, which
445-  # is not comparable to a content fingerprint — compare tree membership by
446-  # re-deriving both roll-ups instead.
447-  if [[ "$surface" == "spec" ]]; then
448-    local roll_t roll_s
449-    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
450-    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
451-    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
452-    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
453-    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
454-    printf 'HASH_UNCLASSIFIED'; return 0
455-  fi
456-
457-  # The canonical pointer digest is the hash of what the framework WOULD
458-  # generate — it matches no file on disk when the pointer is customised, so it
459-  # has to be recognised explicitly or every correct record reads as
460-  # unclassified.
461-  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
462-  # digest and the prior record are the SAME bytes, so whichever is tested
463-  # first wins the name. Testing the prior record first keeps continuity rows
464-  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
465-  # when the two genuinely differ — i.e. when the pointer was customised, which
466-  # is the one cell where the distinction carries meaning.
467-  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
468:  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
469-    printf 'HASH_CANONICAL_POINTER'; return 0
470-  fi
471-  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
472-  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
473-  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
474-  printf 'HASH_UNCLASSIFIED'
475-}
476-
477-_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
478-  local root="$1" pfx="$2"
479-  [[ -d "$root" ]] || { printf ''; return 0; }
480-  ( cd "$root" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
481-    | while IFS= read -r r; do
482-        [[ -n "$r" ]] || continue
483-        printf '%s  %s/%s\n' "$( _hash_file "$root/$r" 2>/dev/null || echo FAIL )" "$pfx" "${r#./}"
484-      done | LC_ALL=C sort | _hash_stdin
485-}
486-
487-# =============================================================================
488-# Row execution
489-# =============================================================================
490-PASS=0; FAIL=0; AMBIG=0; ERR=0
491-MAP_LINES=""
492-
493-_run_row() {
494-  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
495-  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
496-  local fault="${11}"
497-  local exp_verdict="${12}" exp_hash="${13}" origin="${14}" note="${15}"
498-
499-  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }
500-
501-  # --- base selection ------------------------------------------------------
502-  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
503-  # Conflating them would erase the r11-F1 cell — see docs §4.1.
504-  local base_mode="copy"
505-  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
506-  local base_ceremony="$ceremony"
507-  # A user-ceremony row asserting residue of a MAINTAINER install must be built
508-  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
509-  local transition_to_user=0
510-  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
511-    base_ceremony="maintainer"; transition_to_user=1
512-  fi
513-
514-  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
515-  local src
516-  if [[ "$source_has" == "no" ]]; then
517-    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
518-  elif [[ "$operation" == "install_fresh" ]]; then
519-    src="$REPO_ROOT"
520-  else
521-    # An upgrade/rerun runs against a source NEWER than the one that wrote the
522-    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
523-    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
524-  fi
525-
526-  # --- base tree -----------------------------------------------------------
527-  if [[ "$operation" == "install_fresh" ]]; then
528-    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
529-    # a base and stripping one record would leave a manifest behind and make the
530-    # row an install_rerun wearing a fresh label.
531-    rm -rf "$T"; mkdir -p "$T"
532-  else
533-    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
534-    rm -rf "$T"; mkdir -p "$T"
535-    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
536-  fi
537-
538-  # --- fixture mutation ----------------------------------------------------
539-  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
540-  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
541-    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
542-    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
543-  fi
544-  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
545-    || { ERR=$((ERR+1)); return; }
546-
547-  # Fault injection from the `fault` COLUMN. It rode in `note` until round-1
548-  # consensus C1 ruled that a dimension the harness parses out of prose is a
549-  # dimension nothing validates.
550-  local bak_guard=""
551-  case "$fault" in
552-    backup_unwritable)
553-      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
554-      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
555-      # before any surface was reached — the branch under test never ran.
556-      # An unreadable SOURCE makes the copy fail while everything else proceeds.
557-      bak_guard="$T/$rel"
558-      chmod 000 "$bak_guard" 2>/dev/null || true ;;

exec
/bin/zsh -lc "nl -ba scripts/tests/test-ownership-table.sh | sed -n '190,325p'; nl -ba scripts/tests/test-ownership-table.sh | sed -n '485,620p'; grep -n '_run_install\\|_base_tar\\|_next_source' scripts/tests/test-ownership-table.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
   190	#
   191	# Every row runs at the SAME target path ($T). That is load-bearing, not
   192	# convenience: the root PROTOCOL.md pointer body embeds the target path, so a
   193	# base tree captured at one path and restored at another would carry a stale
   194	# canonical pointer digest and silently corrupt every protocol row.
   195	# =============================================================================
   196	BASE_DIR="$WORK/base"; mkdir -p "$BASE_DIR"
   197	CANON_POINTER_HASH=""       # captured from a real install at $T (never recomputed)
   198	
   199	_base_tar() {  # $1 = ceremony, $2 = base mode(copy|link) -> path to tarball
   200	  local ceremony="$1" bmode="$2"
   201	  local tarball="$BASE_DIR/$ceremony-$bmode.tar"
   202	  [[ -f "$tarball" ]] && { printf '%s' "$tarball"; return 0; }
   203	
   204	  rm -rf "$T"; mkdir -p "$T"
   205	  local args=( "$T" --ceremony "$ceremony" )
   206	  [[ "$bmode" == "link" ]] && args+=( --link )
   207	  if ! _run_with_timeout 300 "$REPO_ROOT/scripts/install.sh" "${args[@]}" \
   208	        > "$BASE_DIR/$ceremony-$bmode.install.log" 2>&1; then
   209	    echo "ERROR: base install failed ($ceremony/$bmode) — see $BASE_DIR/$ceremony-$bmode.install.log" >&2
   210	    return 1
   211	  fi
   212	  # The canonical pointer digest for THIS target path, taken from the file the
   213	  # real installer just generated (never reproduced by duplicating the heredoc,
   214	  # which would be an oracle that passes when both sides are wrong together).
   215	  if [[ -z "$CANON_POINTER_HASH" && -f "$T/PROTOCOL.md" ]]; then
   216	    CANON_POINTER_HASH="$( _hash_file "$T/PROTOCOL.md" 2>/dev/null || true )"
   217	  fi
   218	  ( cd "$T" && tar -cf "$tarball" . ) || return 1
   219	  rm -rf "$T"
   220	  printf '%s' "$tarball"
   221	}
   222	
   223	# A source checkout that LACKS a surface — what `--pin <pre-v1.3 tag>` yields.
   224	_alt_source() {  # $1 = surface -> path to a source tree without it
   225	  local surface="$1"
   226	  local alt="$WORK/src-no-$surface"
   227	  [[ -d "$alt" ]] && { printf '%s' "$alt"; return 0; }
   228	  _clone_source "$alt" || return 1
   229	  local rel; rel="$( _relpath_for "$surface" )"
   230	  rm -rf "${alt:?}/$rel"
   231	  printf '%s' "$alt"
   232	}
   233	
   234	_clone_source() {  # $1 = destination
   235	  mkdir -p "$1"
   236	  ( cd "$REPO_ROOT" && tar -cf - --exclude='./.git' --exclude='./node_modules' . ) \
   237	    | ( cd "$1" && tar -xf - )
   238	}
   239	
   240	# The NEXT version of the framework — a source whose surfaces differ from the
   241	# one that produced the baseline.
   242	#
   243	# This is not decoration. A real upgrade runs against a source NEWER than the
   244	# install that wrote the manifest. Reusing one source makes `HASH_SOURCE` and
   245	# `HASH_PRIOR_RECORD` byte-equal, and a classifier can then only tell them
   246	# apart by preferring one — which is resolving an ambiguity by preference, the
   247	# exact thing docs §5.6 forbids. Perturbing the source is how the fixture is
   248	# DIFFERENTIATED until the two candidates separate.
   249	_next_source() {
   250	  local nxt="$WORK/src-next"
   251	  [[ -d "$nxt" ]] && { printf '%s' "$nxt"; return 0; }
   252	  _clone_source "$nxt" || return 1
   253	  local first
   254	  first="$( ( cd "$nxt/SPEC/v1" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
   255	  first="${first#./}"
   256	  [[ -n "$first" ]] && printf '\n<!-- next-version marker (PLAN-167 fixture) -->\n' >> "$nxt/SPEC/v1/$first"
   257	  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
   258	  printf '%s' "$nxt"
   259	}
   260	
   261	_strip_record() {  # $1 = manifest, $2 = relpath — make prior_record=none
   262	  local m="$1" rel="$2" tmp
   263	  [[ -f "$m" ]] || return 0
   264	  tmp="$( mktemp "$m.XXXXXX" )" || return 1
   265	  grep -vE "^([0-9a-f]{64}|LINK)  ${rel//./\\.}(/|  |$)" "$m" > "$tmp" 2>/dev/null
   266	  mv "$tmp" "$m"
   267	}
   268	
   269	_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
   270	  local surface="$1" ltype="$2" lcontent="$3" src_root="$4" prior="${5:-none}"
   271	  local rel; rel="$( _relpath_for "$surface" )"
   272	  local p="$T/$rel"
   273	
   274	  # A `link_match` row means the live symlink IS the recorded delivery. The
   275	  # base --link install already created exactly that, so pointing it somewhere
   276	  # else here would silently convert every link_match row into a
   277	  # link_retargeted one — the fixture would then agree with the expectation for
   278	  # the wrong reason, which is how a row goes green while testing nothing.
   279	  if [[ "$ltype" == "symlink" && "$prior" == "link_match" ]]; then
   280	    [[ -L "$p" ]] || { echo "FIXTURE-ERR: $rel is not a symlink after a --link base install" >&2; return 1; }
   281	    ltype="__keep__"
   282	  fi
   283	
   284	  case "$ltype" in
   285	    absent)   rm -rf "$p" ;;
   286	    dir_empty)
   287	      rm -rf "$p"; mkdir -p "$p" ;;
   288	    regular)
   289	      if [[ -d "$p" ]]; then rm -rf "$p"; fi
   290	      [[ -e "$p" ]] || { mkdir -p "$( dirname "$p" )"; printf 'adopter regular file\n' > "$p"; }
   291	      ;;
   292	    symlink)
   293	      # The foreign leaf is a TRIPWIRE, not scenery. A surface written with
   294	      # `cat >` follows a leaf symlink and mutates whatever it points at —
   295	      # OUTSIDE the target tree, which is adopter or system data. Comparing
   296	      # only the target would let that row report GREEN while the run
   297	      # destroyed a file the test never looked at.
   298	      rm -rf "$p"
   299	      mkdir -p "$( dirname "$p" )" "$WORK/foreign"
   300	      printf 'foreign content — MUST NOT be modified by any run\n' > "$WORK/foreign/leaf"
   301	      ln -s "$WORK/foreign/leaf" "$p"
   302	      ;;
   303	    special)
   304	      rm -rf "$p"; mkdir -p "$( dirname "$p" )"; mkfifo "$p" 2>/dev/null || return 1 ;;
   305	    ancestor_symlink)
   306	      # Move the parent aside and symlink it back — the leaf is then reachable
   307	      # only by writing THROUGH a symlink out of the target tree.
   308	      local parent; parent="$( dirname "$p" )"
   309	      local real="$WORK/ancestor-real-$surface"
   310	      rm -rf "$real"; mkdir -p "$( dirname "$real" )"
   311	      mv "$parent" "$real" 2>/dev/null || return 1
   312	      ln -s "$real" "$parent"
   313	      ;;
   314	    dir)
   315	      # On a rerun the base install already left the tree; on a structurally
   316	      # fresh target there is nothing yet, so the adopter's own directory has
   317	      # to be built here.
   318	      if [[ ! -d "$p" || -L "$p" ]]; then
   319	        rm -rf "$p"; mkdir -p "$p"; printf 'adopter content\n' > "$p/adopter.md"
   320	      fi
   321	      ;;
   322	  esac
   323	
   324	  case "$lcontent" in
   325	    edited)
   485	}
   486	
   487	# =============================================================================
   488	# Row execution
   489	# =============================================================================
   490	PASS=0; FAIL=0; AMBIG=0; ERR=0
   491	MAP_LINES=""
   492	
   493	_run_row() {
   494	  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
   495	  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
   496	  local fault="${11}"
   497	  local exp_verdict="${12}" exp_hash="${13}" origin="${14}" note="${15}"
   498	
   499	  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }
   500	
   501	  # --- base selection ------------------------------------------------------
   502	  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
   503	  # Conflating them would erase the r11-F1 cell — see docs §4.1.
   504	  local base_mode="copy"
   505	  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
   506	  local base_ceremony="$ceremony"
   507	  # A user-ceremony row asserting residue of a MAINTAINER install must be built
   508	  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
   509	  local transition_to_user=0
   510	  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
   511	    base_ceremony="maintainer"; transition_to_user=1
   512	  fi
   513	
   514	  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
   515	  local src
   516	  if [[ "$source_has" == "no" ]]; then
   517	    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
   518	  elif [[ "$operation" == "install_fresh" ]]; then
   519	    src="$REPO_ROOT"
   520	  else
   521	    # An upgrade/rerun runs against a source NEWER than the one that wrote the
   522	    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
   523	    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
   524	  fi
   525	
   526	  # --- base tree -----------------------------------------------------------
   527	  if [[ "$operation" == "install_fresh" ]]; then
   528	    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
   529	    # a base and stripping one record would leave a manifest behind and make the
   530	    # row an install_rerun wearing a fresh label.
   531	    rm -rf "$T"; mkdir -p "$T"
   532	  else
   533	    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
   534	    rm -rf "$T"; mkdir -p "$T"
   535	    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
   536	  fi
   537	
   538	  # --- fixture mutation ----------------------------------------------------
   539	  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
   540	  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
   541	    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
   542	    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
   543	  fi
   544	  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
   545	    || { ERR=$((ERR+1)); return; }
   546	
   547	  # Fault injection from the `fault` COLUMN. It rode in `note` until round-1
   548	  # consensus C1 ruled that a dimension the harness parses out of prose is a
   549	  # dimension nothing validates.
   550	  local bak_guard=""
   551	  case "$fault" in
   552	    backup_unwritable)
   553	      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
   554	      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
   555	      # before any surface was reached — the branch under test never ran.
   556	      # An unreadable SOURCE makes the copy fail while everything else proceeds.
   557	      bak_guard="$T/$rel"
   558	      chmod 000 "$bak_guard" 2>/dev/null || true ;;
   559	  esac
   560	
   561	  # --- BEFORE snapshot -----------------------------------------------------
   562	  local b_digest b_rec
   563	  b_digest="$( _obs_digest "$T/$rel" )"
   564	  b_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
   565	  _MTIME_BEFORE="$( _obs_mtime "$T/$rel" )"
   566	  # Everything outside $T that a run could reach. Any change here is an escape.
   567	  _ESCAPE_BEFORE="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"
   568	
   569	  # --- run the REAL script -------------------------------------------------
   570	  local out="$WORK/run-$id.log"; : > "$out"
   571	  local rc=0
   572	  # A `ceremony=user` UPGRADE row asserts residue of a maintainer install that
   573	  # was later re-run as `--ceremony user`. The ceremony is read from
   574	  # .claude/.install-state.json, so labelling the row is not enough: the
   575	  # transition has to actually happen, or upgrade.sh still sees `maintainer`
   576	  # and the row silently tests the wrong branch.
   577	  if [[ "$transition_to_user" -eq 1 && "$operation" == "upgrade" ]]; then
   578	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "$T" --ceremony user \
   579	      >> "$out" 2>&1 || true
   580	  fi
   581	  if [[ "$operation" == "upgrade" ]]; then
   582	    local uargs=( "$T" )
   583	    [[ "$skip_requested" == "self" ]] && uargs+=( --skip "$rel" )
   584	    if [[ "$skip_requested" == "descendant" ]]; then
   585	      local victim; victim="$( ( cd "$T/$rel" 2>/dev/null && find . ! -type d -print 2>/dev/null | LC_ALL=C sort | head -1 ) )"
   586	      victim="${victim#./}"
   587	      [[ -n "$victim" ]] && uargs+=( --skip "$rel/$victim" )
   588	    fi
   589	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/upgrade.sh" "${uargs[@]}" >> "$out" 2>&1
   590	    rc=$?
   591	  else
   592	    local iargs=( "$T" --ceremony "$ceremony" )
   593	    [[ "$mode" == "link" ]] && iargs+=( --link )
   594	    [[ "$transition_to_user" -eq 1 ]] && iargs=( "$T" --ceremony user )
   595	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
   596	    rc=$?
   597	  fi
   598	  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null
   599	
   600	  local timed_out=0
   601	  [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1
   602	
   603	  # --- AFTER snapshot + derivation ----------------------------------------
   604	  local a_digest a_rec got_verdict got_hash
   605	  a_digest="$( _obs_digest "$T/$rel" )"
   606	  a_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
   607	  _MTIME_AFTER="$( _obs_mtime "$T/$rel" )"
   608	  _ESCAPE_AFTER="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"
   609	
   610	  if [[ "$timed_out" -eq 1 ]]; then
   611	    got_verdict="TIMEOUT"; got_hash="TIMEOUT"
   612	  else
   613	    got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
   614	    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
   615	  fi
   616	
   617	  # --- compare -------------------------------------------------------------
   618	  local status="RED"
   619	  local alt=""
   620	  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac
199:_base_tar() {  # $1 = ceremony, $2 = base mode(copy|link) -> path to tarball
249:_next_source() {
523:    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
533:    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
660:_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }

exec
/bin/zsh -lc "nl -ba scripts/tests/test-ownership-table.sh | sed -n '425,478p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
   425	}
   426	
   427	_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
   428	  local surface="$1" ar="$2" pr="$3" src="$4"
   429	  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
   430	  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac
   431	
   432	  local got="${ar#hash:}"
   433	  local rel; rel="$( _relpath_for "$surface" )"
   434	
   435	  # Candidate 1: the bytes now at the target.
   436	  local c_target; c_target="$( _obs_digest "$T/$rel" )"
   437	  # Candidate 2: the framework's copy in the source checkout.
   438	  local c_source; c_source="$( _obs_digest "$src/$rel" )"
   439	  # Candidate 3: the digest the PRE-run manifest recorded.
   440	  local c_prior="${pr#hash:}"
   441	  # Candidate 4: the canonical pointer digest (protocol only).
   442	  local c_pointer="$CANON_POINTER_HASH"
   443	
   444	  # For tree surfaces the recorded value is the roll-up of per-file rows, which
   445	  # is not comparable to a content fingerprint — compare tree membership by
   446	  # re-deriving both roll-ups instead.
   447	  if [[ "$surface" == "spec" ]]; then
   448	    local roll_t roll_s
   449	    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
   450	    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
   451	    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
   452	    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
   453	    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
   454	    printf 'HASH_UNCLASSIFIED'; return 0
   455	  fi
   456	
   457	  # The canonical pointer digest is the hash of what the framework WOULD
   458	  # generate — it matches no file on disk when the pointer is customised, so it
   459	  # has to be recognised explicitly or every correct record reads as
   460	  # unclassified.
   461	  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
   462	  # digest and the prior record are the SAME bytes, so whichever is tested
   463	  # first wins the name. Testing the prior record first keeps continuity rows
   464	  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
   465	  # when the two genuinely differ — i.e. when the pointer was customised, which
   466	  # is the one cell where the distinction carries meaning.
   467	  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
   468	  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
   469	    printf 'HASH_CANONICAL_POINTER'; return 0
   470	  fi
   471	  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
   472	  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
   473	  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
   474	  printf 'HASH_UNCLASSIFIED'
   475	}
   476	
   477	_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
   478	  local root="$1" pfx="$2"

exec
/bin/zsh -lc "nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '154,213p'; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '265,285p'; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '352,380p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
   154	   > sed -n '7,$p' <mapa> | grep -E '^OWN-' | grep -v GREEN | awk '{print $1}' | sort
   155	   > ```
   156	   > e um arquivo `scripts/tests/ownership-expected-reds.txt` com os 4 ids,
   157	   > que é o que o CI compara. **Adicionar também um passo que normalize o
   158	   > cabeçalho ao gravar o baseline**, senão ele volta a poluir o repo com
   159	   > paths de máquina.
   160	
   161	**Gate W1:** um PR tocando só `ownership_table.tsv` dispara o workflow (hoje
   162	não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
   163	
   164	> **⚠️ GATE VACUOSO NO PRÓPRIO HARNESS (QA must-fix 2, verificado).** A flag
   165	> `--map` **sai rc=0 mesmo com células vermelhas** — provado:
   166	> `--only OWN-0016 --map` ⇒ rc=0, sem `--map` ⇒ rc=1. Um passo de CI que use
   167	> `--map` é um **gate morto que reporta sucesso para sempre**. Mitigado na
   168	> fonte (o harness agora emite NOTE em stderr quando `--map` suprime uma
   169	> falha), mas **o passo de CI NÃO PODE usar `--map`** — é regra, não estilo.
   170	>
   171	> **QA must-fix 2: entregue o SCRIPT, não a intenção.** O passo de CI precisa
   172	> vir escrito no plano/pack — roda o harness, extrai os ids RED do stdout,
   173	> compara com `ownership-expected-reds.txt`, falha em qualquer diferença de
   174	> conjunto. Descrever o comportamento não é um gate.
   175	>
   176	> **O SCRIPT (rail r1 P1 — rc semântico explícito, HARNESS-ERR=0 exigido):**
   177	> com N vermelhos esperados o harness sai rc=1 POR DESIGN; `set -e` cru morre
   178	> antes de comparar, e engolir o rc cegamente aceita rc=2 (erro de harness) ou
   179	> saída parcial. O passo é:
   180	> ```sh
   181	> set -uo pipefail
   182	> rc=0
   183	> bash scripts/tests/test-ownership-table.sh > /tmp/own-map.txt 2>/tmp/own-err.txt || rc=$?
   184	> cat /tmp/own-map.txt
   185	> sed -n '1,40p' /tmp/own-err.txt >&2 || true
   186	> # rc=2 (ou >2) = erro de harness/infra — NUNCA comparável
   187	> if [ "$rc" -ge 2 ]; then echo "::error::harness rc=$rc"; exit 1; fi
   188	> # o sumário precisa existir e reportar HARNESS-ERR=0 (saída parcial não passa)
   189	> grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' /tmp/own-map.txt \
   190	>   || { echo "::error::sumário ausente ou HARNESS-ERR>0 (saída parcial/vacuosa)"; exit 1; }
   191	> # conjunto de não-verdes observado vs esperado — QUALQUER diferença falha
   192	> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | grep -v '[[:space:]]GREEN[[:space:]]' \
   193	>   | awk '{print $1}' | LC_ALL=C sort > /tmp/own-got.txt
   194	> LC_ALL=C sort scripts/tests/ownership-expected-reds.txt > /tmp/own-exp.txt
   195	> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
   196	>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
   197	> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
   198	> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
   199	> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
   200	> echo "ownership nightly: conjunto de vermelhos estável"
   201	> ```
   202	> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
   203	> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
   204	
   205	### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
   206	
   207	1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
   208	   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
   209	   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
   210	     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
   211	     em vez de o sintoma.
   212	   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
   213	2. **⚠️ O FIX SOZINHO NÃO CURA QUEM JÁ ESTÁ EM CAMPO** (debate r1, security
   265	   > `OWN-0074` fica verde — vacuosamente. O teste EXIGE, além da identidade,
   266	   > asserções de CONTEÚDO: `{{PROTOCOL_SOURCE}}` **ausente** e a fonte
   267	   > resolvida esperada **presente**, após install, upgrade E migração/cura.
   268	5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
   269	   como base; ela já reproduz o defeito.
   270	
   271	**Gate W2 (o anterior era vacuoso — este não):** o digest gravado para
   272	`PROTOCOL.md` **bate com os bytes no disco**, o ponteiro deixa de classificar
   273	`edited` no caminho comum, e **o `OWN-0074` fica VERDE** — o conjunto
   274	esperado de vermelhos encolhe para `{OWN-0016, OWN-0024, OWN-0027}`.
   275	
   276	> **Ordem obrigatória (QA must-fix 1):** o W2 tem de atualizar
   277	> `ownership-expected-reds.txt` **no mesmo pack**. Se o W1 landar o gate do
   278	> AC-5 antes, a primeira CI após o W2 falha por "o conjunto encolheu" — que é
   279	> o gate funcionando, mas bloqueando trabalho correto.
   280	
   281	### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
   282	
   283	Registrar como contrato:
   284	- que `ABORT_SURFACE` é **resultado de OBSERVAÇÃO do harness**, e não um
   285	  membro do enum de decisão — a função nunca o devolve (QA advisory 3). Sem
   352	## 6. Riscos
   353	
   354	| Risco | Mitigação |
   355	|---|---|
   356	| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
   357	| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
   358	| Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
   359	| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: persistir PROTOCOL_SOURCE; hoje a intenção do adotante NÃO é gravada |
   360	| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
   361	| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
   362	
   363	## 7. Registro de execução
   364	
   365	<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
   366	
   367	- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
   368	  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   369	  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
   370	- **S297 (07/08, retomada):** commit `11cd4f6` pushado. Claims mecânicas do
   371	  plano re-verificadas na árvore viva — **todas conferem** (filtros `:15`/`:54`,
   372	  4 paths com grep=0, zero `schedule:`, `fetch-depth:1` em `:101`, header do
   373	  baseline com paths de máquina, 6 células protocol+upgrade sem REFRESH/DELIVER,
   374	  NOTE do `--map` em `test-ownership-table.sh:690`, `_SPEC_PRISTINE_FINGERPRINTS`
   375	  presente, `PROTOCOL_SOURCE` não persistido, sonda INV-4 presente).
   376	- **Decisões do Owner (07/08, registradas antes de codar):**
   377	  - **D1 (W2 direção): opção (b)** — gerador compartilhado único que
   378	    install/upgrade chamam.
   379	  - **D2 (célula da cura): a tabela GANHA linhas novas** — `live_content`
   380	    ganha o valor `degraded` (corpo com `{{PROTOCOL_SOURCE}}` literal = lixo

exec
/bin/zsh -lc "nl -ba scripts/install.sh | sed -n '2585,2665p'; nl -ba scripts/upgrade.sh | sed -n '3150,3275p'; nl -ba scripts/upgrade.sh | sed -n '620,725p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
  2585	                parts = line.split("\t", 1)
  2586	                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
  2587	    except OSError:
  2588	        pass
  2589	now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  2590	prev = None
  2591	try:
  2592	    with open(state_path, "r", encoding="utf-8") as f:
  2593	        prev = json.load(f)
  2594	    if not isinstance(prev, dict):
  2595	        prev = None
  2596	except (OSError, ValueError):
  2597	    prev = None
  2598	first, run_count, history = now, 1, []
  2599	if prev is not None:
  2600	    v = prev.get("first_recorded_at")
  2601	    if isinstance(v, str) and v:
  2602	        first = v
  2603	    rc = prev.get("run_count")
  2604	    if isinstance(rc, int) and rc > 0:
  2605	        run_count = rc + 1
  2606	    h = prev.get("history")
  2607	    if isinstance(h, list):
  2608	        history = [e for e in h if isinstance(e, dict)][-19:]
  2609	    pr = prev.get("request"); pt = prev.get("tool"); pw = prev.get("written_at")
  2610	    history.append({
  2611	        "at": pw if isinstance(pw, str) else "",
  2612	        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
  2613	        "profile": (pr.get("profile", "") if isinstance(pr, dict) else ""),
  2614	        "stack": (pr.get("stack", "") if isinstance(pr, dict) else ""),
  2615	    })
  2616	    history = history[-20:]
  2617	    # Placeholder map is a UNION across runs: install.sh is EXISTS-SKIP
  2618	    # idempotent and never un-substitutes, so a value recorded by an earlier
  2619	    # run remains in effect on disk even when a later run omits the flag.
  2620	    # New non-empty values override recorded ones.
  2621	    if isinstance(pr, dict):
  2622	        oph = pr.get("placeholders")
  2623	        if isinstance(oph, dict):
  2624	            merged = {}
  2625	            for k in oph:
  2626	                if isinstance(k, str) and isinstance(oph[k], str):
  2627	                    merged[k] = oph[k]
  2628	            merged.update(ph)
  2629	            ph = merged
  2630	req = {
  2631	    "argv": orig_argv,
  2632	    "target": vals.get("target", ""),
  2633	    "mode": vals.get("mode", ""),
  2634	    "profile": vals.get("profile", ""),
  2635	    "stack": vals.get("stack", ""),
  2636	    "stack_explicit": vals.get("stack_explicit", "0") == "1",
  2637	    "ceremony": vals.get("ceremony", ""),
  2638	    "github_owner": vals.get("github_owner", ""),
  2639	    "with_reference_personas": vals.get("with_reference_personas", "0") == "1",
  2640	    "strict_placeholders": vals.get("strict_placeholders", "0") == "1",
  2641	    "verify": vals.get("verify", "0") == "1",
  2642	    # PLAN-155 Wave 5: recorded so upgrade.sh replays the harness (B2 mirror).
  2643	    "harness": vals.get("harness", "claude"),
  2644	    "managed_hooks": vals.get("managed_hooks", "0") == "1",
  2645	    "placeholders": ph,
  2646	}
  2647	state = {
  2648	    "schema": "ceo.install-state/v1",
  2649	    "schema_version": 1,
  2650	    "written_at": now,
  2651	    "first_recorded_at": first,
  2652	    "run_count": run_count,
  2653	    "tool": {"name": "install.sh", "framework_version": fw_version},
  2654	    "request": req,
  2655	    "operations": ops,
  2656	    "result": {"install_succeeded": True,
  2657	               "baseline_manifest": ".claude/.install-manifest.sha256"},
  2658	    "history": history,
  2659	    "_comment": "Target-side, UNSIGNED, advisory record (same trust class as the ADR-155 baseline manifest). upgrade.sh replays request.profile/request.stack as DEFAULTS only; explicit flags always win. Not a trust anchor.",
  2660	}
  2661	d = os.path.dirname(state_path) or "."
  2662	if not os.path.isdir(d):
  2663	    sys.exit(3)
  2664	fd, tmp = tempfile.mkstemp(prefix=".install-state.", suffix=".tmp", dir=d)
  2665	try:
  3150	  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
  3151	  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
  3152	  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
  3153	  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
  3154	  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
  3155	  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
  3156	  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  3157	  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
  3158	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  3159	fi
  3160	
  3161	# ===========================================================================
  3162	# PLAN-153 Wave B item B2 — (re)write the install-state after a successful
  3163	# upgrade, mirroring the ADR-155 decision-(iv) manifest rewrite above: a
  3164	# pre-Wave-B adopter (no state file) ACQUIRES one on their first post-Wave-B
  3165	# upgrade, so the NEXT upgrade can replay. Merge semantics preserve the
  3166	# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
  3167	# update the replayable fields (request.profile/request.stack) to the values
  3168	# THIS run effectively used; the upgrade run itself is recorded under
  3169	# last_upgrade + history. Atomic (same-directory tempfile + os.replace),
  3170	# schema ceo.install-state/v1, fail-open (a write problem emits a NOTE and
  3171	# never aborts the completed upgrade). Skipped on --dry-run.
  3172	_write_upgrade_state() {
  3173	  [[ "$DRY_RUN" -eq 0 ]] || return 0
  3174	  if ! command -v python3 >/dev/null 2>&1; then
  3175	    echo "    NOTE: install-state not (re)written (python3 not found) — the next upgrade uses the ADR-155 fallback path" >&2
  3176	    return 0
  3177	  fi
  3178	  local fw_version=""
  3179	  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
  3180	    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  3181	  fi
  3182	  local pairs=(
  3183	    "target" "$TARGET"
  3184	    "profile" "$PROFILE"
  3185	    "stack" "$STACK"
  3186	    "on_conflict" "$ON_CONFLICT"
  3187	    "pin" "$PIN_REF"
  3188	    "replay_source" "$_REPLAY_SOURCE"
  3189	    "harness" "$HARNESS"
  3190	    "managed_hooks" "$CODEX_MANAGED_HOOKS"
  3191	    "ceremony_effective" "$CEREMONY_EFFECTIVE"
  3192	  )
  3193	  echo ""
  3194	  echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
  3195	  if ! PYTHONNOUSERSITE=1 python3 -I -c '
  3196	import json, os, sys, tempfile, time
  3197	args = sys.argv[1:]
  3198	state_path, ops_path, fw_version = args[0], args[1], args[2]
  3199	n = int(args[3]); kv = args[4:4 + n]; up_argv = list(args[4 + n:])
  3200	vals = {}
  3201	i = 0
  3202	while i + 1 < len(kv):
  3203	    vals[kv[i]] = kv[i + 1]; i += 2
  3204	ops = []
  3205	if ops_path and os.path.isfile(ops_path):
  3206	    try:
  3207	        with open(ops_path, "r", encoding="utf-8", errors="replace") as f:
  3208	            for line in f:
  3209	                line = line.rstrip("\n")
  3210	                if not line:
  3211	                    continue
  3212	                parts = line.split("\t", 1)
  3213	                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
  3214	    except OSError:
  3215	        pass
  3216	now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  3217	prev = None
  3218	try:
  3219	    with open(state_path, "r", encoding="utf-8") as f:
  3220	        prev = json.load(f)
  3221	    if not isinstance(prev, dict):
  3222	        prev = None
  3223	except (OSError, ValueError):
  3224	    prev = None
  3225	first, run_count, history, req = now, 1, [], None
  3226	if prev is not None:
  3227	    v = prev.get("first_recorded_at")
  3228	    if isinstance(v, str) and v:
  3229	        first = v
  3230	    rc = prev.get("run_count")
  3231	    if isinstance(rc, int) and rc > 0:
  3232	        run_count = rc + 1
  3233	    h = prev.get("history")
  3234	    if isinstance(h, list):
  3235	        history = [e for e in h if isinstance(e, dict)][-19:]
  3236	    pr = prev.get("request")
  3237	    if isinstance(pr, dict):
  3238	        req = pr
  3239	    pt = prev.get("tool"); pw = prev.get("written_at")
  3240	    history.append({
  3241	        "at": pw if isinstance(pw, str) else "",
  3242	        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
  3243	        "profile": (req.get("profile", "") if isinstance(req, dict) else ""),
  3244	        "stack": (req.get("stack", "") if isinstance(req, dict) else ""),
  3245	    })
  3246	    history = history[-20:]
  3247	if req is None:
  3248	    req = {
  3249	        "argv": [],
  3250	        "target": vals.get("target", ""),
  3251	        "placeholders": {},
  3252	        "note": "synthesized by upgrade.sh - no pre-Wave-B install.sh record existed (back-compat path)",
  3253	    }
  3254	req["profile"] = vals.get("profile", "")
  3255	req["stack"] = vals.get("stack", "")
  3256	# PLAN-155 Wave 5: persist harness so it survives even a pre-Wave-B target
  3257	# whose request was synthesized above. Only overwrite when non-empty so a
  3258	# claude-only upgrade never clobbers a recorded codex harness with "".
  3259	_h = vals.get("harness", "")
  3260	if _h in ("claude", "codex"):
  3261	    req["harness"] = _h
  3262	elif "harness" not in req:
  3263	    req["harness"] = "claude"
  3264	if vals.get("managed_hooks", "0") == "1":
  3265	    req["managed_hooks"] = True
  3266	elif "managed_hooks" not in req:
  3267	    req["managed_hooks"] = False
  3268	state = {
  3269	    "schema": "ceo.install-state/v1",
  3270	    "schema_version": 1,
  3271	    "written_at": now,
  3272	    "first_recorded_at": first,
  3273	    "run_count": run_count,
  3274	    "tool": {"name": "upgrade.sh", "framework_version": fw_version},
  3275	    "request": req,
   620	fi
   621	
   622	TARGET="$( cd "$TARGET" && pwd )"
   623	
   624	# ===========================================================================
   625	# PLAN-153 Wave B item B2 — replay the RECORDED install request.
   626	# ===========================================================================
   627	# install.sh (>= Wave B) records the original request in
   628	# $TARGET/.claude/.install-state.json (schema ceo.install-state/v1). When
   629	# present + valid, request.profile / request.stack become the DEFAULTS for
   630	# this upgrade so an adopter who installed `--profile core,fintech` does not
   631	# silently get the core,frontend default by forgetting the flag. Explicit
   632	# flags always win; --no-replay opts out.
   633	#
   634	# BACK-COMPAT (debate C must-fix): missing state (ALL pre-Wave-B installs)
   635	# or unreadable/invalid state NEVER errors and NEVER no-ops — the upgrade
   636	# proceeds with CLI/default flags on the ADR-155 path (the --dry-run preview
   637	# and the baseline drift-classifier below), and a state file is (re)written
   638	# after a successful non-dry upgrade so the NEXT run can replay.
   639	#
   640	# TRUST: the state file is target-side, UNSIGNED, advisory (ADR-155 trust
   641	# class). Values are parsed by python3 -I under PYTHONNOUSERSITE=1, charset-
   642	# validated (profile: [A-Za-z0-9_,.-]{1,200}; stack: [A-Za-z0-9_.-]{1,100}),
   643	# and NEVER eval-ed; anything suspect => fallback, exactly as if absent.
   644	_INSTALL_STATE_FILE="$TARGET/.claude/.install-state.json"
   645	_REPLAY_SOURCE="cli-default"
   646	_UP_OPS_FILE=""
   647	
   648	# Print "<profile>\t<stack>" from a valid state file; non-zero rc on ANY
   649	# problem (missing python3, unreadable file, bad JSON, wrong schema_version,
   650	# non-string or charset-violating values) => caller falls back.
   651	_read_install_state_request() {
   652	  command -v python3 >/dev/null 2>&1 || return 3
   653	  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
   654	  PYTHONNOUSERSITE=1 python3 -I -c '
   655	import json, re, sys
   656	try:
   657	    with open(sys.argv[1], "r", encoding="utf-8") as f:
   658	        d = json.load(f)
   659	except (OSError, ValueError):
   660	    sys.exit(3)
   661	if not isinstance(d, dict):
   662	    sys.exit(3)
   663	if d.get("schema_version") != 1:
   664	    sys.exit(3)
   665	req = d.get("request")
   666	if not isinstance(req, dict):
   667	    sys.exit(3)
   668	prof = req.get("profile", "")
   669	stack = req.get("stack", "")
   670	if not isinstance(prof, str) or not isinstance(stack, str):
   671	    sys.exit(3)
   672	if prof and not re.match(r"^[A-Za-z0-9_,.-]{1,200}$", prof):
   673	    sys.exit(3)
   674	if stack and not re.match(r"^[A-Za-z0-9_.-]{1,100}$", stack):
   675	    sys.exit(3)
   676	# PLAN-155 Wave 5: harness (closed enum) + managed_hooks bool round-trip.
   677	harness = req.get("harness", "")
   678	if harness not in ("", "claude", "codex"):
   679	    harness = ""  # unknown value => fall back to CLI/default, never trust it
   680	managed = "1" if req.get("managed_hooks") is True else "0"
   681	sys.stdout.write(prof + "\t" + stack + "\t" + harness + "\t" + managed + "\n")
   682	' "$_INSTALL_STATE_FILE" 2>/dev/null
   683	}
   684	
   685	if [[ "$REPLAY" -eq 1 ]]; then
   686	  if [[ -f "$_INSTALL_STATE_FILE" ]]; then
   687	    _rp_line=""
   688	    if _rp_line="$(_read_install_state_request)" && [[ -n "$_rp_line" ]]; then
   689	      # TAB-separated: profile<TAB>stack<TAB>harness<TAB>managed (PLAN-155 W5).
   690	      IFS=$'\t' read -r _rp_profile _rp_stack _rp_harness _rp_managed <<< "$_rp_line"
   691	      _rp_used=0
   692	      if [[ "$PROFILE_EXPLICIT" -eq 0 && -n "$_rp_profile" ]]; then
   693	        PROFILE="$_rp_profile"
   694	        _rp_used=1
   695	        echo "    REPLAY: --profile $PROFILE (recorded request in .claude/.install-state.json; pass --profile or --no-replay to override)" >&2
   696	      fi
   697	      if [[ "$STACK_EXPLICIT" -eq 0 && -n "$_rp_stack" ]]; then
   698	        STACK="$_rp_stack"
   699	        _rp_used=1
   700	        echo "    REPLAY: --stack $STACK (recorded request in .claude/.install-state.json; pass --stack or --no-replay to override)" >&2
   701	      fi
   702	      if [[ "$HARNESS_EXPLICIT" -eq 0 && -n "$_rp_harness" ]]; then
   703	        HARNESS="$_rp_harness"
   704	        _rp_used=1
   705	        echo "    REPLAY: --harness $HARNESS (recorded request in .claude/.install-state.json; pass --harness or --no-replay to override)" >&2
   706	      fi
   707	      if [[ "$CODEX_MANAGED_HOOKS" -eq 0 && "${_rp_managed:-0}" = "1" ]]; then
   708	        CODEX_MANAGED_HOOKS=1
   709	        _rp_used=1
   710	      fi
   711	      if [[ "$_rp_used" -eq 1 ]]; then
   712	        _REPLAY_SOURCE="replay"
   713	      fi
   714	    else
   715	      _REPLAY_SOURCE="fallback-invalid-state"
   716	      echo "    NOTE: .claude/.install-state.json present but unreadable/invalid — IGNORED." >&2
   717	      echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2
   718	      echo "          drift-classifier; --dry-run previews). Never blocks (PLAN-153" >&2
   719	      echo "          debate C back-compat must-fix); a valid state file is rewritten" >&2
   720	      echo "          after this upgrade completes." >&2
   721	    fi
   722	  else
   723	    _REPLAY_SOURCE="fallback-no-state"
   724	    echo "    NOTE: no .claude/.install-state.json in target (pre-Wave-B install)." >&2
   725	    echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2

codex
The proposed nightly gate can accept timeout or escape regressions, and key W2 acceptance outcomes are not achievable as specified because legacy bodies are invocation-specific and OWN-0074 aliases canonical and prior hashes. The plan also leaves the new regression test and guarded workflow incompletely wired or inventoried.

Full review comments:

- [P1] Match only RED rows in the nightly baseline — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:191-193
  If an expected-red row starts timing out or escaping the target, the harness emits the same ID with `TIMEOUT` or `ESCAPE`, increments `FAIL`, and still exits 1. This pipeline accepts every non-GREEN status and compares only IDs, so the expected set and rc remain unchanged and the nightly gate passes a more severe regression; extract exactly `RED` and reject other statuses.

- [P1] Derive legacy fingerprints from invocation-specific bodies — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:228-230
  For adopters upgraded before PLAN-167, the degraded heredoc embeds the invocation's `$TARGET`, `$PROFILE`, and `$STACK`, so one static whole-body fingerprint per framework version cannot match the deployed population. Most affected pointers would miss the fingerprint and remain preserved forever, violating AC-6b; candidate fingerprints must account for validated invocation-specific values or the residual must be explicitly scoped.

- [P1] Account for OWN-0074 canonical/prior hash aliasing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:271-274
  With the required byte identity and persisted `PROTOCOL_SOURCE`, OWN-0074's prior install digest and new canonical digest become equal. The harness intentionally tests `c_prior` before `c_pointer`, so this preserved edited row reports `HASH_PRIOR_RECORD` while the TSV expects `HASH_CANONICAL_POINTER`; OWN-0074 therefore remains red unless the observable contract or indistinguishable alternative is updated in the pack.

- [P1] Wire the new INV-4 regression test into CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:255-259
  The CI work specifies only the unit oracle and table harness, while this separate three-leg test is not assigned to either job or any path filter. Unless these assertions are explicitly embedded in `test-ownership-table.sh`, the new install→upgrade→upgrade and migration regression remains a local test that CI never invokes—the same unwired-test failure class W1 is intended to close.

- [P2] Inventory the new guarded nightly workflow — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:310-310
  D4 explicitly creates `.github/workflows/ownership-nightly.yml`, but the canonical-boundary table lists only `smoke-install.yml`. Because every `.github/workflows/*.yml` file is sentinel-guarded, omitting the new workflow leaves the plan's pack and ceremony inventory incomplete.

- [P2] Remove stale PROTOCOL_SOURCE persistence claims — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:359-359
  Current installs already pass `ph.PROTOCOL_SOURCE` to the state writer, which merges it into `request.placeholders`; W2.3 correctly documents this. This risk entry states the opposite, and the execution log repeats it, which conflicts with the explicit decision not to add a second persistence field and can misdirect implementation.
The proposed nightly gate can accept timeout or escape regressions, and key W2 acceptance outcomes are not achievable as specified because legacy bodies are invocation-specific and OWN-0074 aliases canonical and prior hashes. The plan also leaves the new regression test and guarded workflow incompletely wired or inventoried.

Full review comments:

- [P1] Match only RED rows in the nightly baseline — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:191-193
  If an expected-red row starts timing out or escaping the target, the harness emits the same ID with `TIMEOUT` or `ESCAPE`, increments `FAIL`, and still exits 1. This pipeline accepts every non-GREEN status and compares only IDs, so the expected set and rc remain unchanged and the nightly gate passes a more severe regression; extract exactly `RED` and reject other statuses.

- [P1] Derive legacy fingerprints from invocation-specific bodies — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:228-230
  For adopters upgraded before PLAN-167, the degraded heredoc embeds the invocation's `$TARGET`, `$PROFILE`, and `$STACK`, so one static whole-body fingerprint per framework version cannot match the deployed population. Most affected pointers would miss the fingerprint and remain preserved forever, violating AC-6b; candidate fingerprints must account for validated invocation-specific values or the residual must be explicitly scoped.

- [P1] Account for OWN-0074 canonical/prior hash aliasing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:271-274
  With the required byte identity and persisted `PROTOCOL_SOURCE`, OWN-0074's prior install digest and new canonical digest become equal. The harness intentionally tests `c_prior` before `c_pointer`, so this preserved edited row reports `HASH_PRIOR_RECORD` while the TSV expects `HASH_CANONICAL_POINTER`; OWN-0074 therefore remains red unless the observable contract or indistinguishable alternative is updated in the pack.

- [P1] Wire the new INV-4 regression test into CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:255-259
  The CI work specifies only the unit oracle and table harness, while this separate three-leg test is not assigned to either job or any path filter. Unless these assertions are explicitly embedded in `test-ownership-table.sh`, the new install→upgrade→upgrade and migration regression remains a local test that CI never invokes—the same unwired-test failure class W1 is intended to close.

- [P2] Inventory the new guarded nightly workflow — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:310-310
  D4 explicitly creates `.github/workflows/ownership-nightly.yml`, but the canonical-boundary table lists only `smoke-install.yml`. Because every `.github/workflows/*.yml` file is sentinel-guarded, omitting the new workflow leaves the plan's pack and ceremony inventory incomplete.

- [P2] Remove stale PROTOCOL_SOURCE persistence claims — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:359-359
  Current installs already pass `ph.PROTOCOL_SOURCE` to the state writer, which merges it into `request.placeholders`; W2.3 correctly documents this. This risk entry states the opposite, and the execution log repeats it, which conflicts with the explicit decision not to add a second persistence field and can misdirect implementation.
