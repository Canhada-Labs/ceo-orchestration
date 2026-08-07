OpenAI Codex v0.144.6
--------
workdir: /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fde6b-4719-7a60-a11f-7b51e9259faf
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- unstaged stat ---\\n' && git diff --stat && printf '\\n--- staged stat ---\\n' && git diff --cached --stat" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-YREAuSBV' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ABTcLQvy' (errno=Operation not permitted)
A  .claude/plans/PLAN-168-ownership-followups-closure.md

--- unstaged stat ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-dAmEjhEz' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Ns1EAdsY' (errno=Operation not permitted)

--- staged stat ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-4ouS8iRs' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-0NKEcrmB' (errno=Operation not permitted)
 .../plans/PLAN-168-ownership-followups-closure.md  | 468 +++++++++++++++++++++
 1 file changed, 468 insertions(+)

exec
/bin/zsh -lc 'git diff --cached -- .claude/plans/PLAN-168-ownership-followups-closure.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-G1qRWZd2' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-fY5WLe4K' (errno=Operation not permitted)
diff --git a/.claude/plans/PLAN-168-ownership-followups-closure.md b/.claude/plans/PLAN-168-ownership-followups-closure.md
new file mode 100644
index 0000000..07fe767
--- /dev/null
+++ b/.claude/plans/PLAN-168-ownership-followups-closure.md
@@ -0,0 +1,468 @@
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
+> # (rail r2 P1) status ≠ GREEN e ≠ RED — TIMEOUT/ESCAPE/AMBIG — NUNCA é
+> # aceitável: um id esperado-vermelho que degrada para TIMEOUT/ESCAPE mantém
+> # o CONJUNTO intacto e esconderia uma regressão PIOR atrás de "mesmo set".
+> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2!="GREEN" && $2!="RED"' \
+>   | grep . && { echo "::error::célula em status nunca-aceitável"; exit 1; }
+> # conjunto RED exato observado vs esperado — QUALQUER diferença falha
+> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2=="RED" {print $1}' \
+>   | LC_ALL=C sort > /tmp/own-got.txt
+> grep -E '^OWN-' scripts/tests/ownership-expected-reds.txt | LC_ALL=C sort > /tmp/own-exp.txt
+> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
+>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
+> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
+> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
+> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
+> echo "ownership nightly: conjunto de vermelhos estável"
+> ```
+> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
+> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
+>
+> **Implementação entregue (W1):** o contrato acima vive em
+> `scripts/tests/ownership-nightly-gate.sh` (script chamado pelo workflow —
+> testável, diferente de YAML inline) com controle positivo
+> `scripts/tests/test-ownership-nightly-gate.sh`: **12 cenários de falha
+> plantados com harness fake**, incluindo os degrades TIMEOUT/ESCAPE/AMBIG
+> do rail r2.
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
+   > **⚠️ CORRIGIDO 2× (rail r1 P1 + r2 P1): o reconhecedor é por
+   > RECONSTRUÇÃO DE TEMPLATE, nunca substring E nunca hash estático.**
+   > Substring é destrutivo (um `PROTOCOL.md` do adotante que legitimamente
+   > CONTÉM o token seria força-refreshado — backup não desfaz a perda do
+   > arquivo ATIVO). Mas hash estático por versão é INÚTIL em campo (r2):
+   > o heredoc degradado embute `$TARGET`, `$PROFILE` e `$STACK` RESOLVIDOS
+   > (verificado em `_refresh_protocol_pointer`, ramo `*)`) — cada adotante
+   > tem um corpo degradado DIFERENTE, e um fingerprint fixo preservaria
+   > quase todos para sempre (AC-6b não cumprido).
+   >
+   > **A forma correta:** casar o corpo observado contra o ESQUELETO exato do
+   > template degradado (um por versão de framework que o produziu): extrair
+   > os campos variáveis das posições fixas, re-renderizar o template com os
+   > valores extraídos + `{{PROTOCOL_SOURCE}}` literal, e exigir
+   > **byte-igualdade** com o observado. Qualquer desvio ⇒ não-match ⇒
+   > **preservar**. Isso mantém a garantia do r1 (exatidão, fail-toward-
+   > preservation) sem a inutilidade do hash fixo. A semântica da célula D2
+   > (`live_content=degraded`) é determinada por essa reconstrução.
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
+   >
+   > **⚠️ E o teste TEM de estar FIADO em CI (rail r2 P1)** — senão é a
+   > classe não-fiada que o W1 existe para fechar, recriada no mesmo pack.
+   > Fiação: step no `ownership-nightly.yml` (obrigatório) + o arquivo do
+   > teste nos DOIS path filters do `smoke-install.yml`; entrar também como
+   > step por-PR no job `smoke` SE a medição couber no teto de 25 min
+   > (medir, não chutar — o orçamento já subiu 4×).
+   >
+   > **⚠️ ALIASING DE HASH NO `OWN-0074` (rail r2 P1, verificado no
+   > harness).** Com o fix + fonte persistida, o digest prior (do install) e
+   > o canônico passam a ser OS MESMOS bytes; `_derive_hash_source` testa
+   > `c_prior` ANTES de `c_pointer` **por design documentado** ("the
+   > canonical name is then reached only when the two genuinely differ").
+   > Resultado: a célula reporta `HASH_PRIOR_RECORD`, a TSV espera
+   > `HASH_CANONICAL_POINTER`, e o `OWN-0074` ficaria vermelho MESMO CURADO.
+   > **O pack atualiza a coluna `exp_hash` do `OWN-0074` para
+   > `HASH_PRIOR_RECORD`** — o VEREDITO (`PRESERVE_OWNED`) fica intocado; a
+   > mudança de contrato observável é consequência necessária da cura (o
+   > gate W2 "0074 VERDE" já a implica). **Nuance de escopo do D2 a
+   > ratificar na assinatura:** D2 dizia "só adição"; esta é UMA edição de
+   > coluna de hash na célula que está sendo curada, com causa registrada.
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
+| `.github/workflows/ownership-nightly.yml` (NOVO — rail r2 P2: todo `.github/workflows/*.yml` é sentinel-guarded; sem esta linha o inventário da cerimônia nasce incompleto) | 🔒 | W1 |
+| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
+| `scripts/tests/ownership_table.tsv` (célula nova D2 + coluna `exp_hash` do OWN-0074) | ✅ livre | W2 |
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
+| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: consumir `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — rail r2 P2 removeu a claim contrária, que era stale); fallback D3 só para estados antigos/ausentes |
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
+- **Rail r2 CONSUMIDO:** 4 P1 + 2 P2, **6 aceitos / 0 refutados**
+  (`rail/codex-r2.md`), os dois claims não-triviais verificados literalmente:
+  o heredoc degradado EMBUTE `$TARGET/$PROFILE/$STACK` (fingerprint estático
+  seria inútil em campo ⇒ reconstrução de template), e a ordem
+  prior-antes-de-canonical do `_derive_hash_source` colapsa o nome quando a
+  cura aliasa os digests (⇒ pack atualiza `exp_hash` do OWN-0074 para
+  `HASH_PRIOR_RECORD`, veredito intocado — nuance do D2 a ratificar na
+  assinatura). Gate endurecido: conjunto RED exato + zero-tolerância a
+  TIMEOUT/ESCAPE/AMBIG. Fixes: §W1.4, §W2.2, §W2.4 (fiação CI do teste
+  INV-4 + aliasing), §3 (nightly no inventário), §6 (claim stale removida).
+- **W1 EXECUTADO no overlay `plan168-dev` (verificado, aguardando pack):**
+  4 paths nos dois filtros + step do oráculo unitário em `smoke-install.yml`;
+  `ownership-nightly.yml` novo (schedule 43 6 UTC + dispatch, gate via
+  script); harness ganhou `--print-legacy-tag` (fonte única do pin, literais
+  internos convertidos) e `--stable-header` (baseline commitável sem paths de
+  máquina); `ownership-expected-reds.txt` (4 ids; W2 encolhe p/ 3 no mesmo
+  pack); `ownership-nightly-gate.sh` + controle positivo **12/12**; YAML
+  válido; shellcheck limpo; oráculo unitário 60/60.
+- **Próxima ação:** rail r3 (teto AC-8) sobre o plano amendado → asserção
+  AC-2 em `test_release_workflow_asserts.py` → W2.

exec
/bin/zsh -lc "sed -n '1,180p' .github/workflows/smoke-install.yml && printf '\\n--- harness options / rc / output ---\\n' && grep -nE -- '--map|print-pin|legacy|HARNESS-ERR|GREEN=' scripts/tests/test-ownership-table.sh | head -100 && printf '\\n--- state / protocol refs ---\\n' && grep -nE 'PROTOCOL_SOURCE|_refresh_protocol_pointer|PRESERVE_OWNED|degraded' scripts/install.sh scripts/upgrade.sh | head -160" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
name: Smoke Install

on:
  pull_request:
    paths:
      - "scripts/install.sh"
      - "scripts/upgrade.sh"
      # PLAN-161 (CI wiring): upgrade oracles + the manifest lib they
      # exercise — keep BOTH filter lists (pull_request + push) in sync.
      - "scripts/_framework_manifest_set.sh"
      # The ownership + parity e2e call _hash_file/_hash_stdin from here, and
      # this workflow is their ONLY CI execution — without the helper in the
      # filter, a PR touching only it skips the gate entirely (codex W1
      # round 10, P2: the "red gate nobody runs" class, one level deeper).
      - "scripts/_hash_lib.sh"
      - "scripts/tests/test-upgrade-dryrun-identity.sh"
      - "scripts/tests/test-upgrade-exclusions.sh"
      - "scripts/tests/smoke-install.sh"
      # PLAN-166 F4 (OQ-4): the install/upgrade parity e2e and its classifier.
      # The finding this closes is "a red gate nobody runs" (5th instance) --
      # an unwired test is the same as no test.
      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
      - "scripts/tests/_parity_classify.py"
      # PLAN-166 F3 (ADR-155-AMEND-1): delivery-record ownership e2e —
      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
      # rule as the parity e2e above).
      - "scripts/tests/test-upgrade-spec-ownership.sh"
      - "templates/**"
      # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
      # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
      # parity event, not just the CLI contract doc.
      - "SPEC/v1/**"
      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
      # PR touching just one of these would otherwise skip the regression.
      - "scripts/doctor.sh"
      - ".claude/.framework-version"
      - ".claude/scripts/check-framework-updates.sh"
      - ".github/workflows/smoke-install.yml"
      # PLAN-006 Phase 1 (Sprint 6): Adapter Layer migration changes
      # install-time expectations (hook import paths, contract). Scope
      # broadened for the sprint; narrow back post-Sprint-7 closeout.
      - ".claude/hooks/**"
  push:
    branches:
      - main
    paths:
      # KEEP IDENTICAL to the pull_request list above. The two had already
      # drifted (push was missing SPEC/v1 and this workflow file); PLAN-166 F4
      # re-syncs them, because a filter that fires on the PR and not on the
      # merge is a gate with a hole in it.
      - "scripts/install.sh"
      - "scripts/upgrade.sh"
      - "scripts/_framework_manifest_set.sh"
      - "scripts/_hash_lib.sh"
      - "scripts/tests/test-upgrade-dryrun-identity.sh"
      - "scripts/tests/test-upgrade-exclusions.sh"
      - "scripts/tests/smoke-install.sh"
      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
      - "scripts/tests/_parity_classify.py"
      - "scripts/tests/test-upgrade-spec-ownership.sh"
      - "templates/**"
      - "SPEC/v1/**"
      - "scripts/doctor.sh"
      - ".claude/.framework-version"
      - ".claude/scripts/check-framework-updates.sh"
      - ".github/workflows/smoke-install.yml"
      - ".claude/hooks/**"

concurrency:
  group: smoke-install-${{ github.ref }}
  cancel-in-progress: true

jobs:
  smoke:
    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
    if: vars.CEO_SOTA_DISABLE != '1'
    runs-on: ubuntu-latest
    # PLAN-161: 5 -> 8 — headroom for the two upgrade oracles (each runs
    # full install + upgrade legs against fixture adopter repos).
    # PLAN-166 F4: 8 -> 20. MEASURED, not guessed. The parity e2e runs 2 full
    # install legs + 1 upgrade leg PER ceremony mode, and the positive control
    # runs the same again with a planted divergence: 12 install/upgrade
    # operations added to this job. Local wall time (Darwin arm64, 16 cores,
    # 2026-08-05): gate 122s + control 118s = 240s. A 2-core ubuntu-latest
    # runner is the usual 2-3x slower, i.e. 8-12 min of NEW work on top of the
    # ~5 min this job already spent. 15 would sit inside the noise band, and
    # the perf-gate N=20 flake (PLAN-159) was exactly that mistake. Re-tighten
    # once real CI runs give a p95.
    # PLAN-166 F3 (assembler): 20 -> 25. The spec-ownership e2e adds 4 more
    # installs + 3 upgrades (S1-S8; ~3-4 min local per the W1-C measurement),
    # i.e. up to ~8-10 more CI minutes at the same 2-3x factor. Same
    # anti-flake sizing rule as the F4 bump above.
    timeout-minutes: 25
    permissions:
      contents: read
    steps:
      - name: Checkout
        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
        with:
          fetch-depth: 1

      # PLAN-166 F4: the parity e2e's historical leg installs from a PINNED
      # TAG. `fetch-depth: 1` produces a checkout with NO tags, so the pin
      # would not resolve and the gate would die before comparing a single
      # tree - "it passes on my clone" is precisely the hole this test exists
      # to close. The pin is READ FROM THE TEST (--print-pin) so the workflow
      # never becomes a second copy of that truth.
      - name: Fetch the parity pin tag
        run: |
          set -euo pipefail
          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
          echo "parity historical pin: $PIN"
          git fetch --no-tags --depth 1 origin "+refs/tags/$PIN:refs/tags/$PIN"
          git rev-parse --verify "refs/tags/$PIN^{commit}"

      - name: Setup Python 3.11
        # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
        with:
          python-version: "3.11"

      - name: Install jq (for settings.json merge)
        run: |
          set -euo pipefail
          if ! command -v jq >/dev/null 2>&1; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq jq
          fi
          jq --version

      - name: Run smoke install
        run: |
          set -euo pipefail
          bash scripts/tests/smoke-install.sh

      # PLAN-161 upgrade oracles (green only once the U1/U2/U3 upgrade.sh
      # fixes are in-tree — land atomically with them).
      - name: Upgrade oracle — --dry-run identity (U1)
        run: |
          set -euo pipefail
          bash scripts/tests/test-upgrade-dryrun-identity.sh

      - name: Upgrade oracle — exclusion parity + opt-in purge (U2/U3)
        run: |
          set -euo pipefail
          bash scripts/tests/test-upgrade-exclusions.sh

      # WS4-user-ceremony-leg
      - name: Install with --ceremony user (governance rc=0 + no out-of-.claude writes)
        run: |
          set -euo pipefail
          U="$(mktemp -d)"
          ( cd "$U" && git init -q )
          CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
            bash scripts/install.sh "$U" --ceremony user
          echo '--- validate-governance.sh (user) ---'
          ( cd "$U" && bash .claude/scripts/validate-governance.sh )
          echo '--- assert only .claude/ at top level ---'  # WS4-sc2010-glob
          extra=""
          for _e in "$U"/* "$U"/.[!.]* "$U"/..?*; do
            [ -e "$_e" ] || continue
            _b="$(basename "$_e")"
            case "$_b" in .claude|.git) continue ;; esac
            extra="$extra $_b"
          done
          if [ -n "$extra" ]; then
            echo "::error::--ceremony user wrote outside .claude/:$extra"
            exit 1
          fi
          echo 'user-ceremony leg: PASS'

      # PLAN-166 F4 (OQ-4) - install/upgrade parity on the RESULTING TREES,
      # per ceremony mode. NO continue-on-error, deliberately: the assertion
      # this replaces was dead twice over (tautological AND wired into no
      # workflow), and an escape hatch here would reinstate exactly that.
      # Exit 2 (KNOWN-OPEN) is a FAILURE too - it NAMES the outstanding
      # PLAN-166 W1 prerequisites instead of skipping them silently.
      - name: Install/upgrade parity e2e (maintainer + user ceremony)
        run: |

--- harness options / rc / output ---
16:#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
41:    --map)  MAP_ONLY=1; shift ;;
351:    legacy_pristine)
357:        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
366:    legacy_pristine_partial)
373:        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
681:echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"
683:# --map is a REPORTING mode, never a gate. Suppressing a non-zero exit is its
690:    echo "NOTE: --map is a REPORTING mode and is exiting 0 despite RED=$FAIL ERR=$ERR." >&2
691:    echo "      Do NOT use --map in a gate. Run without it to get a pass/fail exit." >&2

--- state / protocol refs ---
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
/bin/zsh -lc "sed -n '1,30p' scripts/tests/ownership-baseline-map.txt 2>/dev/null || true; printf '\\n--- harness output formatting ---\\n'; sed -n '620,710p' scripts/tests/test-ownership-table.sh; printf '\\n--- tsv head ---\\n'; sed -n '1,12p' scripts/tests/ownership_table.tsv" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
== PLAN-167 ownership decision table ==
   table:  /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/tests/ownership_table.tsv
   source: /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
   scratch:/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.toQDrn
   timeout:60s/cell   timeout-bin:<fallback>

OWN-0001   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155
OWN-0002   GREEN   exp=DELIVER         /HASH_CANONICAL_POINTER got=DELIVER         /HASH_CANONICAL_POINTER rc=0   adr-155
OWN-0003   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0004   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0005   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0006   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0007   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0008   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0010   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
OWN-0011   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r1-F1
OWN-0012   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
OWN-0013   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
OWN-0014   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F1
OWN-0015   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F2
OWN-0017   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r3-F2
OWN-0018   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0019   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0020   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r1-F3
OWN-0021   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0022   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0023   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r3-F1
OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_NONE              rc=0   r3-F1
OWN-0025   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r9-F3

--- harness output formatting ---
  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac

  # An escape outranks the verdict comparison. A row whose pair matches while
  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
  # exact damage class this table exists to prevent, and calling that GREEN
  # would be the instrument concealing a data loss.
  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
    status="ESCAPE"; FAIL=$((FAIL+1))
  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
    status="GREEN"; PASS=$((PASS+1))
  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
    status="AMBIG"; AMBIG=$((AMBIG+1))
  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
    status="TIMEOUT"; FAIL=$((FAIL+1))
  else
    FAIL=$((FAIL+1))
  fi

  MAP_LINES+="$( printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
      "$id" "$status" "$exp_verdict" "$exp_hash" "$got_verdict" "$got_hash" "$rc" "$origin" )"$'\n'
}

# =============================================================================
# Main
# =============================================================================
if [[ "$LIST_ONLY" -eq 1 ]]; then
  awk -F'\t' '!/^#/ && $1!="id" && NF>1 {print $1"\t"$13}' "$TSV"
  exit 0
fi

echo "== PLAN-167 ownership decision table =="
echo "   table:  $TSV"
echo "   source: $REPO_ROOT"
echo "   scratch:$WORK"
echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
echo ""

# Prime the canonical pointer digest for $T from a real install. Structurally
# fresh rows build no base, so without this the protocol candidate would be
# unavailable exactly where it is needed.
_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }


# Rows are consumed in file order; the map is sorted by id at emit time so the
# output is deterministic regardless of table order.
while IFS=$'\t' read -r id surface prior_record live_type live_content \
      source_has mode ceremony operation skip_requested fault \
      exp_verdict exp_hash origin note; do
  [[ -z "${id:-}" ]] && continue
  case "$id" in \#*|id) continue ;; esac
  # --only takes a comma-separated list: iterating on a cluster of related rows
  # should cost ONE base install, not one per row.
  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
           "$source_has" "$mode" "$ceremony" "$operation" "$skip_requested" \
           "${fault:-none}" "$exp_verdict" "$exp_hash" "$origin" "${note:-}"
done < "$TSV"

printf '%s' "$MAP_LINES" | LC_ALL=C sort

echo ""
echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"

# --map is a REPORTING mode, never a gate. Suppressing a non-zero exit is its
# whole purpose, so a CI step that uses it becomes a dead gate that reports
# success forever. Say so loudly on the way out, on stderr, so the mistake is
# visible in the job log instead of silent (PLAN-168 debate r1, QA must-fix 2).
if [[ "$MAP_ONLY" -eq 1 ]]; then
  if [[ "$FAIL" -gt 0 || "$ERR" -gt 0 ]]; then
    echo "" >&2
    echo "NOTE: --map is a REPORTING mode and is exiting 0 despite RED=$FAIL ERR=$ERR." >&2
    echo "      Do NOT use --map in a gate. Run without it to get a pass/fail exit." >&2
  fi
  exit 0
fi
[[ "$ERR" -gt 0 ]] && exit 2
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0

--- tsv head ---
# PLAN-167 — ownership decision table. THIS FILE IS THE TRUTH.
# Reasoning lives in docs/ownership-decision-table.md; values live ONLY here.
# Conventions: "*" = don't-care (harness instantiates the canonical
# representative); "-" = not applicable under a §4 legality rule.
# note carries PROSE ONLY. Structured values live in columns (round-1 C1).
# `indistinguishable=` / `open=` remain annotations, never dimensions.
id	surface	prior_record	live_type	live_content	source_has	mode	ceremony	operation	skip_requested	fault	expect_verdict	expect_hash_source	origin	note
OWN-0001	spec	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155	indistinguishable=HASH_TARGET
OWN-0002	protocol	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_CANONICAL_POINTER	adr-155	indistinguishable=HASH_TARGET
OWN-0003	marker	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155-amend-1	indistinguishable=HASH_TARGET
OWN-0004	spec	none	dir	edited	yes	copy	maintainer	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	install_one EXISTS-skips; adopter tree must not be inventoried
OWN-0005	marker	none	regular	edited	yes	copy	maintainer	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	pre-existing marker is NOT a delivery

exec
/bin/zsh -lc "ls .claude/plans | tail -30; printf '\\n--- PLAN id refs ---\\n'; grep -RIl '"'^id: PLAN-168$'"' .claude/plans || true; printf '\\n--- plan checks refs ---\\n'; grep -R \"budget_tokens\\|external_wait\" -n .claude/scripts .claude/hooks | head -50" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 646ms:

--- plan checks refs ---
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

exec
/bin/zsh -lc "find .claude/plans/PLAN-168 -maxdepth 3 -type f -print | sort | sed -n '1,120p'; printf '\\n--- schema ---\\n'; sed -n '1,180p' .claude/plans/PLAN-SCHEMA.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
.claude/plans/PLAN-168/debate/round-1/COLLISION-NOTE.md
.claude/plans/PLAN-168/debate/round-1/consensus.md
.claude/plans/PLAN-168/debate/round-1/devops.md
.claude/plans/PLAN-168/debate/round-1/qa-architect.md
.claude/plans/PLAN-168/debate/round-1/security-engineer.md
.claude/plans/PLAN-168/rail/codex-r1.md

--- schema ---
---
id: PLAN-SCHEMA
title: Plan File Schema — Frontmatter, Lifecycle, Conventions
status: accepted
created: 2026-04-11
owner: CEO
depends_on: []
---

# Plan File Schema

> This document defines the **schema** that every file under `.claude/plans/`
> must conform to. Plans are first-class artifacts: they persist across
> sessions, survive reboots, outlive individual conversations, and serve
> as the CEO's durable memory when a task spans multiple Claude Code
> sessions.
>
> See `.claude/plans/README.md` for the operational workflow. This file
> is about the schema and its rationale.

## 1. File naming + directory layout

Plans live at `.claude/plans/<filename>.md`. Naming convention:

```
PLAN-<NNN>-<kebab-case-slug>.md
```

- `<NNN>` is a zero-padded 3-digit sequence number, monotonically
  increasing. First plan is `PLAN-001`, second is `PLAN-002`, etc.
- `<kebab-case-slug>` is a 2-5 word descriptor. Lowercase, hyphen-separated.
- Examples:
  - `PLAN-001-evolution.md` ← the framework evolution roadmap
  - `PLAN-002-sprint-2-hardening.md` ← next sprint's plan
  - `PLAN-007-migrate-hooks-to-python.md`

**Why sequence numbers?** They give us stable references in commits,
issues, and conversation (`see PLAN-003`). They also make directory
listing stable (lexicographic sort = chronological).

### Naming invariant (Sprint 2 addition)

**Files directly under `.claude/plans/` MUST match one of:**

1. `PLAN-<NNN>-<kebab-case-slug>.md` (a real plan), OR
2. `PLAN-<NNN>-FOLLOWUP-<kebab-case-slug>.md` (a followup plan; see §1.4), OR
3. One of the known governance files: `README.md`, `PLAN-SCHEMA.md`,
   `AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md`, OR
4. `SPRINT-<N>-<anything>.md` (sprint retrospective / planning doc; the
   validator accepts the pattern `^SPRINT-[0-9]+.*\.md$`).

No other filenames are allowed at the top level. A test fixture, an
in-progress note, or an experiment does NOT go directly under
`.claude/plans/` — it goes under `examples/` or `archive/` (see below).

**Subdirectories directly under `.claude/plans/` MUST match one of:**

1. `PLAN-<NNN>/` (matching an existing plan file, for debate
   transcripts and multi-file plan state — see DEBATE-SCHEMA.md §3)
2. `examples/` (non-plan fixtures — e.g. `examples/debate-round-1/`
   showing a debate fixture that does not correspond to any real plan)
3. `archive/` (retired plans that reached `status: done` or
   `status: abandoned` and are no longer actively referenced)
4. `WAR-ROOM/` (ad-hoc cross-plan incident coordination space; not
   plan-scoped, not plan-NNN-scoped)
5. `_templates/` (plan-template fragments used by scaffolding scripts;
   not plan files themselves)

**Why:** the plan namespace is the CEO's durable state. Mixing
example fixtures or experiments into that namespace erodes the
invariant that every `.claude/plans/PLAN-*.md` file is a real,
executable contract. Debate round 1 on PLAN-002 caught the original
fixture path (`PLAN-000-example/`) as a violation of this rule — it
looked like a plan but wasn't one. The fix was to move fixtures to
`.claude/plans/examples/` outside the `PLAN-<NNN>` namespace entirely.

**Enforcement:** mechanically enforced from **PLAN-019 VP-F4** (Sprint 14 /
Session 30). `validate-governance.sh` now refuses to pass if any
subdirectory or filename under `.claude/plans/` violates the rules above:

- subdirectories not matching `PLAN-<NNN>` / `examples` / `archive` /
  `WAR-ROOM` / `_templates` → FAIL
- `PLAN-<NNN>/` subdirectories with no matching top-level
  `PLAN-<NNN>-*.md` plan file (orphan dirs) → FAIL (added PLAN-152
  governance-05; the PLAN-128 clean-room-migration class)
- files not matching `PLAN-<NNN>-<kebab-case-slug>.md` / `SPRINT-N-*.md`
  or one of the four known governance filenames (`README.md`,
  `PLAN-SCHEMA.md`, `AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md`) → FAIL

The enforcement code + tests live at
`.claude/scripts/validate-governance.sh` (section "PLAN-SCHEMA §1
invariants") and `.claude/scripts/tests/test_plan_schema_enforcement.py`
(10 tests covering valid baseline + 8 violation classes +
real-repo sanity). CODEOWNERS on `.claude/plans/PLAN-*.md` remains the
merge-side backstop for the rare case where someone bypasses the
validator locally.

**Support files** for a plan (debate transcripts per DEBATE-SCHEMA.md,
per-plan notes) live under `.claude/plans/PLAN-<NNN>/` — the
subdirectory matches the plan file's NNN. The subdirectory is
created on demand when a plan needs on-disk state (typically for
multi-round debate).

**Archived plans:** when a plan reaches `status: done` or `status: abandoned`
and is no longer actively referenced, it MAY be moved to
`.claude/plans/archive/`. Deferred until the plans directory grows
large enough to need it (Sprint 3+).

### §1.3a — Artifact retention policy (PLAN-114 F-11.16)

`PLAN-NNN/` subdirectories accumulate ceremony artifacts, staging bundles,
and wave-level outputs indefinitely. This is **intentional and acceptable**
for plans that are still active (`status: draft|reviewed|executing`).

For **done** or **abandoned** plans, the following retention rules apply:

**Permanent (never delete):**
- `PLAN-NNN/` debate transcripts (per DEBATE-SCHEMA.md §3) — audit trail
- Signed sentinel files (`approved*.md.asc`) — provenance record
- Codex pair-rail verdict files — provenance record

**Eligible for archival** (when plan reaches `status: done` AND the
`.claude/plans/archive/` subdir convention is activated):
- `staging/`, `wave-N-bundle/`, `ceremony/` subdirectories — may be
  moved to `archive/PLAN-NNN/` once the plan is done and the Owner
  confirms no in-flight references remain
- `shards/`, `scripts/` subdirs generated during plan execution

**Deferred cleanup gate (no CI enforcement currently):**
A mechanical CI gate that reports plan-subdir size at `status: done`
transition is tracked as a future hardening item. Current policy is
advisory: the validate-governance.sh §1 invariants enforce directory
_naming_ (PLAN-NNN/ only) but do not enforce artifact pruning.

**False premise guard:** `archive/` migration is explicitly deferred until
the plans directory needs it (PLAN-SCHEMA.md §1 line ~103). The retention
policy above documents the intended state; it does NOT trigger any
automated archival.

### §1.4 — Followup plans: `PLAN-NNN-FOLLOWUP` suffix convention (S127 addition)

A **followup plan** addresses residual scope descoped from a parent plan
during honest-scope-reduction or AC follow-up after shipping. It preserves
the parent's `NNN` for visual linkage, mirroring the canonical ADR
amendment convention (`ADR-NNN-AMEND-M-<slug>.md`).

**Use when:**

- Parent shipped with explicit deferred AC items (e.g., PLAN-094 Wave A.7
  → PLAN-094-FOLLOWUP Wave A.7-rem 14 residual tests).
- HARD-BLOCKER scope reduction folded `N` surfaces honestly to `M < N`
  (e.g., PLAN-093 Wave 0 reduced 10→8 surfaces, deferred to PLAN-093-FOLLOWUP).
- AC items deferred per ADR-115 §exception #1 or ADR-124 §Part 2 hotfix
  scope (where issuing a new ADR would be churn for residual close-out).

**Do NOT use when:**

- The work is net-new scope unrelated to the parent's residuals → allocate
  a new monotonic `NNN` instead (e.g., PLAN-094 → PLAN-095, *not*
  PLAN-094-FOLLOWUP).
- Pure cleanup that ships as part of the parent → fold into parent's
  closeout ceremony rather than scaffolding a separate followup plan.

**Naming:**

```
.claude/plans/PLAN-NNN-FOLLOWUP-<kebab-case-slug>.md    # plan body
.claude/plans/PLAN-NNN-FOLLOWUP/                         # artifact subdir
```

Where:

- `NNN` is the **parent plan's** zero-padded 3-digit number — *not* a
  fresh monotonic ID. That preservation is what distinguishes a followup
  from a successor plan.
- `<kebab-case-slug>` is a 2-5 word descriptor of the residual scope
  (lowercase, hyphen-separated, matching parent slug style).
- `FOLLOWUP` is literal UPPERCASE, mirroring `AMEND` uppercase in
  `ADR-NNN-AMEND-M`.


exec
/bin/zsh -lc "grep -nE '"'^## 2|budget_tokens|budget_sessions|context_risk|external_wait|status:'"' .claude/plans/PLAN-SCHEMA.md | head -100 && sed -n '210,390p' .claude/plans/PLAN-SCHEMA.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
4:status: accepted
62:3. `archive/` (retired plans that reached `status: done` or
63:   `status: abandoned` and are no longer actively referenced)
104:**Archived plans:** when a plan reaches `status: done` or `status: abandoned`
113:for plans that are still active (`status: draft|reviewed|executing`).
122:**Eligible for archival** (when plan reaches `status: done` AND the
130:A mechanical CI gate that reports plan-subdir size at `status: done`
199:status: draft|reviewed|executing|done   # standard lifecycle
211:`status: executing` until its parent reaches `status: done`. The followup
277:## 2. Required frontmatter fields
285:status: draft                    # see lifecycle below
298:completed_at: 2026-04-11         # date the plan reached status: done
310:budget_tokens: 95-130k           # CEO-context tokens (range or single estimate)
311:budget_sessions: 1               # how many fresh-terminal sessions
312:context_risk: low | medium | high # autocompact probability mid-task
313:external_wait: none              # ONLY for genuine external state (deploy/soak/SLA)
323:- `budget_tokens` — CEO-context token range (e.g. `95-130k`,
326:- `budget_sessions` — integer count of fresh-terminal sessions
329:- `context_risk` — `low` (<150k), `medium` (150-300k), `high`
331:- `external_wait` — `none` for CEO-only work. Use only for
402:1. The `status:` field is one of the legal states (`draft`, `reviewed`,
425:7. **`## Success criteria`** — checklist the plan must satisfy to move to `status: done`.
485:status: draft
497:status: executing
521:status: abandoned
549:Required frontmatter when `status: refused`:
551:status: refused
565:Required frontmatter when `status: superseded`:
567:status: superseded
580:status: executing
616:  word. "PLAN-064 status:reviewed gate" is a leaf; "blocked" is not.
640:status: executing
650:status: reviewed
651:external_wait: PLAN-064-status-reviewed
653:Body `## Blockers`: "PLAN-064 status:reviewed gate (external_wait
658:status: executing
791:- `status:` is one of `draft` / `reviewed` / `executing` (terminal states
863:  finding (`status: degraded`, remediation `/spawn spec-clarify`) per plan
A followup inherits gates from its parent. It **cannot** enter
`status: executing` until its parent reaches `status: done`. The followup
ships with its own patch tag (e.g., PLAN-094 `v1.27.0` → PLAN-094-FOLLOWUP
`v1.27.1`), bumping the parent's tag by one patch increment when the
followup scope is purely residual close-out.

**Multi-followup (supported as of S152):**

When a parent plan needs multiple followups (PLAN-112 surfaced 18 in S152
post-audit), disambiguate via kebab-slug suffix rather than numeric suffix.
Both the file (`.md`) and its artifact subdir use the same naming:

```
.claude/plans/PLAN-NNN-FOLLOWUP-<slug>.md    # plan body
.claude/plans/PLAN-NNN-FOLLOWUP-<slug>/      # artifact subdir (when shipped)
```

Authoritative regexes (`validate_governance_fast.py`):

```python
_PLAN_FILENAME_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$"
)
_VALID_PLAN_SUBDIR_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP(-[a-z0-9]+(-[a-z0-9]+)*)?)?$"
)
```

First multi-followup shipped: `PLAN-112-FOLLOWUP-hmac-tamper-fix` (v1.39.4,
S152 2026-05-21). 17 sibling followups queued at top-level as `.md` skeletons.

**Frontmatter `id:` MUST be slug-bearing + unique (S155 — PLAN-093-FOLLOWUP
dual-id fix).** Each followup's `id:` carries the same slug as its filename
(`id: PLAN-NNN-FOLLOWUP-<slug>`), NOT the bare `PLAN-NNN-FOLLOWUP`. Two
followups of one parent sharing a bare `id:` — the PLAN-093-FOLLOWUP collision
(`-cadence-amendment` + `-deferred-callsite-surfaces` both declared
`id: PLAN-093-FOLLOWUP`) — make every id reference ambiguous. This is now
mechanically enforced: `validate_governance_fast.py::_check_plan_id_uniqueness`
(+ the `validate-governance.sh` mirror) fail on any duplicate root-level
frontmatter `id:`. A single-followup parent MAY still use the bare form, but
slug-bearing is the recommended default to keep the id collision-proof.

**Historical exception:** `PLAN-076-plan-070-followup.md` (Apr 2026) used
an older convention — its own monotonic `NNN` with `plan-NNN-followup` in
the slug. This predates the `FOLLOWUP` suffix convention codified in S127
and is **grandfathered**, not recommended for new followups.

**Rationale:**

The suffix encoding (`PLAN-NNN-FOLLOWUP`) preserves the parent's identity
in commits, GPG-signed sentinels, and shipped tags. If the followup were
renumbered (e.g., `PLAN-105` for a followup of PLAN-094), every existing
sentinel and commit message referring to "PLAN-094-FOLLOWUP" would
reference a dead ID, creating permanent ID drift. The suffix mirrors the
canonical ADR amendment convention (`ADR-040-AMEND-2`, `ADR-055-AMEND-1`)
— the parent is the durable identity; the followup is a derivative record
of residual work.

**Enforcement:** `_PLAN_FILENAME_RE` and `_VALID_PLAN_SUBDIR_RE` in
`.claude/scripts/validate_governance_fast.py` accept both
`PLAN-NNN-<slug>.md` and `PLAN-NNN-FOLLOWUP-<slug>.md` (and the matching
subdirs). Other uppercase suffixes (e.g., `PLAN-NNN-AMEND`,
`PLAN-NNN-RANDOM`) remain rejected — `FOLLOWUP` is the only blessed
plan-level suffix; `AMEND` belongs to ADRs. Test coverage at
`.claude/scripts/tests/test_ceo_boot_plan_082.py::TestPlanSchemaCheck`
(7 tests: 4 pre-S127 + 3 followup-convention).

## 2. Required frontmatter fields

Every plan file begins with a YAML frontmatter block. Required fields:

```yaml
---
id: PLAN-001                     # must match the filename prefix
title: Short human title          # 3-10 words
status: draft                    # see lifecycle below
created: 2026-04-10              # ISO 8601 date
owner: CEO | "<Persona Name>"    # who is accountable for this plan
depends_on: [PLAN-001]           # list of other plan IDs, or []
---
```

## 3. Optional frontmatter fields

```yaml
---
reviewed_at: 2026-04-11          # date the owner reviewed / accepted
reviewed_by: "Example Owner"     # human reviewer name (if Owner-approved)
completed_at: 2026-04-11         # date the plan reached status: done
abandoned_at: 2026-04-12         # date the plan was abandoned (with reason in body)
related_commits:                 # commits that implemented parts of the plan
  - 07b8f8e
  - bedad24
  - c6e3c57
context_size_at_creation: 76%    # Claude Code context fill at save time
sprint: 1                        # optional: sprint number this plan belongs to
tags: [infrastructure, ci]       # optional: topic tags
spec_ref: .claude/plans/PLAN-001/spec.md   # ADR-058 optional: pre-plan-brainstorm spec artifact

# ADR-081 budget fields (recommended for new plans 2026-04-25+)
budget_tokens: 95-130k           # CEO-context tokens (range or single estimate)
budget_sessions: 1               # how many fresh-terminal sessions
context_risk: low | medium | high # autocompact probability mid-task
external_wait: none              # ONLY for genuine external state (deploy/soak/SLA)
---
```

### ADR-081 token-as-time budget fields (recommended for plans 2026-04-25+)

Per ADR-081, new plans express effort estimates in Claude tokens
(CEO context) and sessions, not in human dev-time units. Old plans
grandfathered — no mass migration.

- `budget_tokens` — CEO-context token range (e.g. `95-130k`,
  `1.3-2M`). Excludes sub-agent contexts (each sub-agent has its
  own 1M budget).
- `budget_sessions` — integer count of fresh-terminal sessions
  needed. Each new session pays gate-boot cost ~27k tokens
  (ADR-020 cache discipline).
- `context_risk` — `low` (<150k), `medium` (150-300k), `high`
  (>300k or split-session). Mid-task autocompact probability.
- `external_wait` — `none` for CEO-only work. Use only for
  genuine external state: deploy soak windows, ADR-057 FPR
  observation, third-party API SLAs.

Legacy fields (`estimated_effort`, `dev_days`, `human_hours`)
remain accepted in old plans but deprecated for new ones. See
ADR-081 §Cost reference table for per-operation token estimates.

### The `spec_ref:` field (ADR-058)

Optional pointer to the `spec.md` artifact emitted by the
`pre-plan-brainstorm` skill before the plan was drafted. Format:

- Repo-relative path to a `.md` file under the plan's own
  subdirectory (`.claude/plans/PLAN-<NNN>/spec.md`).
- Required for L3+ plans where `CEO_BRAINSTORM_GATE=0` is NOT set
  and the task had ambiguous requirements per the skill's
  smell-tests (see `.claude/skills/core/pre-plan-brainstorm/SKILL.md`
  §When to invoke).
- Optional for L1-L2 plans, well-precedented L3+ plans, hotfixes,
  and plans where `CEO_BRAINSTORM_GATE=0` was in effect at drafting.
- Absence on a matching-condition plan is a debate Round 1 signal
  (not a hook block) — debate prompts include `## BRAINSTORM GAP`
  section requiring CEO to explain.

The plan's debate Round 1 prompts inject the spec content (or
hash reference per ADR-051 pattern) into each agent prompt as
`## SPEC CONTEXT`. See `.claude/team.md` §Spawn Protocol Step 3.

## 4. Lifecycle states (`status` field)

Plans move through a finite state machine:

```
draft ──────► reviewed ──────► executing ──────► done
  │              │                   │             ▲
  │              │                   │             │
  └──────────────┴───────────────────┴──► abandoned
```

### State definitions

| Status | Meaning | Next allowed transitions |
|---|---|---|
| `draft` | Plan is being written. Not yet ready for execution. No commits depend on it. | `reviewed`, `abandoned` |
| `reviewed` | Owner (human) has read and accepted the plan. Execution may begin. | `executing`, `abandoned` |
| `executing` | Work on this plan is in progress. At least one commit references the plan. | `done`, `abandoned` |
| `done` | All items in the plan are complete and verified. No further work. | (terminal; `executing` re-open per ADR-092, or `superseded`) |
| `abandoned` | Plan was scoped out or proven wrong. Body must contain an "Abandonment reason" section. | (terminal) |
| `refused` | An Owner-signed ADR documents that the plan's premise is rejected. Requires `refused_at` + `refused_adr`. See §11. | (terminal) |
| `superseded` | A later plan fully absorbed this plan's scope; the work was valid but is now tracked elsewhere. Requires `superseded_by: PLAN-NNN`. See §11. | (terminal) |

### Why state transitions matter

- **`draft` → `reviewed`** is the human-gate: the Owner must read the plan
  before execution begins. This is the closest the framework gets to a
  formal approval workflow without adding out-of-band tools.
- **`reviewed` → `executing`** is the self-gate: the CEO marks the plan
  as in-progress when the first commit lands. Before this, nothing
  should reference the plan except itself.

exec
/bin/zsh -lc "git rev-parse --short HEAD; git log -1 --format='%h %s'; git cat-file -t 7c0828a 2>/dev/null || true; git cat-file -t 11cd4f6 2>/dev/null || true; git ls-files .claude/plans/PLAN-168; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '410,468p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-UnQTiF6Z' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Qrt7452L' (errno=Operation not permitted)
4234282
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-8CdVCqnN' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Vo9djfs6' (errno=Operation not permitted)
4234282 rail-scope: plano removido do baseline — reentra como diff não-commitado
commit
commit
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-mE5C9omA' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-vgfb7kgC' (errno=Operation not permitted)
.claude/plans/PLAN-168/debate/round-1/COLLISION-NOTE.md
.claude/plans/PLAN-168/debate/round-1/consensus.md
.claude/plans/PLAN-168/debate/round-1/devops.md
.claude/plans/PLAN-168/debate/round-1/qa-architect.md
.claude/plans/PLAN-168/debate/round-1/security-engineer.md
.claude/plans/PLAN-168/rail/codex-r1.md
   410	  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
   411	- **S297 (07/08, retomada):** commit `11cd4f6` pushado. Claims mecânicas do
   412	  plano re-verificadas na árvore viva — **todas conferem** (filtros `:15`/`:54`,
   413	  4 paths com grep=0, zero `schedule:`, `fetch-depth:1` em `:101`, header do
   414	  baseline com paths de máquina, 6 células protocol+upgrade sem REFRESH/DELIVER,
   415	  NOTE do `--map` em `test-ownership-table.sh:690`, `_SPEC_PRISTINE_FINGERPRINTS`
   416	  presente, `PROTOCOL_SOURCE` não persistido, sonda INV-4 presente).
   417	- **Decisões do Owner (07/08, registradas antes de codar):**
   418	  - **D1 (W2 direção): opção (b)** — gerador compartilhado único que
   419	    install/upgrade chamam.
   420	  - **D2 (célula da cura): a tabela GANHA linhas novas** — `live_content`
   421	    ganha o valor `degraded` (corpo com `{{PROTOCOL_SOURCE}}` literal = lixo
   422	    do próprio framework) ⇒ células novas com veredito `REFRESH` (com backup).
   423	    Só ADIÇÃO; os 62 vereditos existentes ficam intocados. O anti-objetivo de
   424	    §0 cede formalmente neste ponto, no molde do precedente r20.
   425	  - **D3 (fallback PROTOCOL_SOURCE): extrair do ponteiro são** no disco e
   426	    persistir; se degradado (literal), usar a fonte resolvida do upgrade +
   427	    backup + aviso. Nunca renomear silenciosamente um ponteiro são.
   428	  - **D4 (nightly): workflow NOVO** `ownership-nightly.yml` (schedule próprio,
   429	    timeout próprio, zero guards nos jobs existentes do `smoke-install.yml`).
   430	- **Rail codex:** 1ª invocação (18:02) foi mal-escopada — diff era um comentário
   431	  inerte sobre draft pré-debate; preservada como `rail/codex-r0-misscoped.md`,
   432	  NÃO conta para o teto do AC-8. r1 re-escopado disparado (plano inteiro como
   433	  diff staged sobre baseline com sujeira aplicada, clone overlay em scratchpad).
   434	- **Rail r1 (re-escopado) CONSUMIDO:** 4 P1 + 3 P2, **7 aceitos / 0
   435	  refutados**, todos verificados contra o código antes de aceitar
   436	  (`rail/codex-r1.md`). Destaque de governança: o P1 "fonte de verdade"
   437	  **derrubou a verificação do debate** — o security checou
   438	  `request.PROTOCOL_SOURCE` (top-level, inexistente) e "corrigiu" uma claim
   439	  CERTA para errada; `install.sh:2523` + writer provam que
   440	  `request.placeholders.PROTOCOL_SOURCE` É persistido (UNION entre runs).
   441	  Fixes aplicados como linhas: §0 (sonda = evidência histórica), §W1.2
   442	  (snippet consome `--print-legacy-tag`), §W1.4 (SCRIPT concreto do gate),
   443	  §W2.2 (fingerprint exato, nunca substring), §W2.3 (consumir chave
   444	  existente), §W2.4 (asserções de conteúdo anti-vacuidade), §W3 (0074
   445	  fechado histórico, 3 abertas), AC-5/6/6b/6c/7.
   446	- **Decisões amendadas pelos achados:** D2 ganha semântica fixa
   447	  (`degraded` = fingerprint exato); D3 vira fallback-only (a fonte primária
   448	  é a chave já persistida).
   449	- **Rail r2 CONSUMIDO:** 4 P1 + 2 P2, **6 aceitos / 0 refutados**
   450	  (`rail/codex-r2.md`), os dois claims não-triviais verificados literalmente:
   451	  o heredoc degradado EMBUTE `$TARGET/$PROFILE/$STACK` (fingerprint estático
   452	  seria inútil em campo ⇒ reconstrução de template), e a ordem
   453	  prior-antes-de-canonical do `_derive_hash_source` colapsa o nome quando a
   454	  cura aliasa os digests (⇒ pack atualiza `exp_hash` do OWN-0074 para
   455	  `HASH_PRIOR_RECORD`, veredito intocado — nuance do D2 a ratificar na
   456	  assinatura). Gate endurecido: conjunto RED exato + zero-tolerância a
   457	  TIMEOUT/ESCAPE/AMBIG. Fixes: §W1.4, §W2.2, §W2.4 (fiação CI do teste
   458	  INV-4 + aliasing), §3 (nightly no inventário), §6 (claim stale removida).
   459	- **W1 EXECUTADO no overlay `plan168-dev` (verificado, aguardando pack):**
   460	  4 paths nos dois filtros + step do oráculo unitário em `smoke-install.yml`;
   461	  `ownership-nightly.yml` novo (schedule 43 6 UTC + dispatch, gate via
   462	  script); harness ganhou `--print-legacy-tag` (fonte única do pin, literais
   463	  internos convertidos) e `--stable-header` (baseline commitável sem paths de
   464	  máquina); `ownership-expected-reds.txt` (4 ids; W2 encolhe p/ 3 no mesmo
   465	  pack); `ownership-nightly-gate.sh` + controle positivo **12/12**; YAML
   466	  válido; shellcheck limpo; oráculo unitário 60/60.
   467	- **Próxima ação:** rail r3 (teto AC-8) sobre o plano amendado → asserção
   468	  AC-2 em `test_release_workflow_asserts.py` → W2.

exec
/bin/zsh -lc "git show --stat --oneline --decorate 11cd4f6 --; printf '\\n--- r0/r2 existence all refs? ---\\n'; git log --all --oneline -- .claude/plans/PLAN-168/rail/codex-r0-misscoped.md .claude/plans/PLAN-168/rail/codex-r2.md; printf '\\n--- prior plan at commit ---\\n'; git ls-tree -r --name-only 11cd4f6 .claude/plans/PLAN-168 | sort" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 263ms:

--- prior plan at commit ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-RKFAPJHS' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-qClPephc' (errno=Operation not permitted)
.claude/plans/PLAN-168/debate/round-1/COLLISION-NOTE.md
.claude/plans/PLAN-168/debate/round-1/consensus.md
.claude/plans/PLAN-168/debate/round-1/devops.md
.claude/plans/PLAN-168/debate/round-1/qa-architect.md
.claude/plans/PLAN-168/debate/round-1/security-engineer.md
.claude/plans/PLAN-168/rail/codex-r1.md

exec
/bin/zsh -lc "git log --oneline --all --decorate -12; printf '\\n--- artifacts commit ---\\n'; git log --oneline -- .claude/plans/PLAN-168 | head -20; printf '\\n--- plan prior history ---\\n'; git log --all --oneline -- .claude/plans/PLAN-168-ownership-followups-closure.md | head -20" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 140ms:
4234282 rail-scope: plano removido do baseline — reentra como diff não-commitado
ec4bdcf fix(PLAN-168): premissa do W2 estava OBSOLETA — meu próprio land a invalidou
8ab0557 fix(PLAN-168): fecho um gate vacuoso no harness que EU construí
b0ec35f plan(PLAN-168): reviewed — debate 3 ADJUST/0 VETO; e uma classificação MINHA corrigida

exec
/bin/zsh -lc "sed -n '1450,1660p' scripts/upgrade.sh; printf '\\n--- decision function refs ---\\n'; grep -nE '_decide|live_content|_classify|PRESERVE_OWNED' scripts/install.sh scripts/upgrade.sh scripts/tests/test-ownership-verdict-unit.sh | head -250; printf '\\n--- state writer context ---\\n'; sed -n '2470,2550p' scripts/install.sh; grep -n \"placeholders\" scripts/upgrade.sh | head -40" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
  if [[ -d "$src" ]]; then
    if [[ "$_lg_excl_aware" -eq 1 ]]; then
      # PLAN-161 W2 fix-2 (codex r2 F11): exclusion-aware per-file copy —
      # non-excluded dirs first (preserves empty framework dirs), then
      # non-excluded files + symlinks (per-operand cp -R copies a symlink
      # as a symlink, POSIX). Excluded SOURCE paths are NEVER written, so
      # pre-existing excluded dst content (the pre-delete survivors) stays
      # byte-for-byte identical across the upgrade — neither deleted,
      # re-copied, nor overwritten by source bytes at a shadowed relpath.
      while IFS= read -r _lg_hit; do
        [[ -n "$_lg_hit" ]] || continue
        _lg_rel="${_lg_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_lg_rel"; then continue; fi
        mkdir -p "$TARGET/$_lg_rel"
      done < <( find "$src" -type d -print 2>/dev/null )
      while IFS= read -r _lg_hit; do
        [[ -n "$_lg_hit" ]] || continue
        _lg_rel="${_lg_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_lg_rel"; then continue; fi
        mkdir -p "$( dirname "$TARGET/$_lg_rel" )"
        cp -R "$_lg_hit" "$TARGET/$_lg_rel"
      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
    else
      cp -R "$src" "$dst"
    fi
    # PLAN-161 U2 (CF-7) r1 prune, F11-NARROWED (belt-and-suspenders): in
    # the wholesale-cp fallback this removes the excluded source content
    # cp -R just dragged in (~967 files in the live 2026-07-21 adopter
    # upgrade). In the exclusion-aware path above the copy never writes
    # excluded paths, so an excluded file found at dst here is either a
    # recorded pre-delete SURVIVOR (adopter-owned or mis-installed — F11:
    # MUST be left exactly as-is; only U3 --purge-misinstalled may delete
    # it) or the artifact of a future copy-path regression (prune it).
    # Per-file rm -f plus rmdir for the emptied dirs — NEVER rm -rf.
    if command -v _framework_path_excluded >/dev/null 2>&1; then
      local _pr_hit _pr_rel
      while IFS= read -r _pr_hit; do
        [[ -n "$_pr_hit" ]] || continue
        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_pr_rel"; then
          # F11a: never test or delete THROUGH a symlinked ancestor — the
          # dst path would resolve into the link target (adopter data
          # possibly outside the tree). Preserved symlink == opaque leaf.
          if _lg_ancestor_is_symlink "$TARGET" "$_pr_rel"; then continue; fi
          # Leaf: -L before -f (lstat-first; -f alone would follow a link).
          if [[ -L "$TARGET/$_pr_rel" || -f "$TARGET/$_pr_rel" ]]; then
            if [[ -n "$_lg_survivors" ]] \
               && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
              :  # pre-existing excluded content — keep exactly as-is (F11)
            else
              rm -f "$TARGET/$_pr_rel"
            fi
          fi
        fi
      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
      # Remove the now-empty excluded dirs, children before parents (-depth)
      # — but never a recorded survivor dir (pre-existing, adopter-held).
      while IFS= read -r _pr_hit; do
        [[ -n "$_pr_hit" ]] || continue
        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
        # F11a: ancestor-symlink guard first, then -L BEFORE -d (lstat-first
        # — -d follows a leaf symlink; a preserved excluded symlink-to-dir
        # must be kept whole and its target never rmdir'd).
        if _framework_path_excluded "$_pr_rel" \
           && ! _lg_ancestor_is_symlink "$TARGET" "$_pr_rel" \
           && [[ ! -L "$TARGET/$_pr_rel" && -d "$TARGET/$_pr_rel" ]]; then
          if [[ -n "$_lg_survivors" ]] \
             && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
            :  # pre-existing excluded dir — keep (F11)
          else
            rmdir "$TARGET/$_pr_rel" 2>/dev/null || true
          fi
        fi
      done < <( find "$src" -depth -type d -print 2>/dev/null )
    fi
  else
    cp "$src" "$dst"
  fi
  if [[ -n "$_lg_survivors" ]]; then
    rm -f "$_lg_survivors"
  fi
  echo "    UPDATED: $rel_path"
}

# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
# framework-derived content (not user data), so preserving it as-is
# across upgrades traps stale pointers when the framework moves. We
# regenerate it with the same heuristic install.sh uses.
_refresh_protocol_pointer() {
  local pointer="$TARGET/PROTOCOL.md"
  local body
  case "$SOURCE_DIR" in
    "$TARGET"/*)
      local rel="${SOURCE_DIR#$TARGET/}"
      body="The full CEO orchestration protocol lives at:
./${rel}/PROTOCOL.md

To pull updates:
  ( cd ./${rel} && git pull )
  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
      ;;
    *)
      body="The full CEO orchestration protocol lives at:
{{PROTOCOL_SOURCE}}/PROTOCOL.md

Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).

To pull updates:
  ( cd {{PROTOCOL_SOURCE}} && git pull )
  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
      ;;
  esac

  # The CANONICAL digest: the hash of exactly what the framework WOULD write.
  # Computed on every path, because the baseline rewrite must record it even
  # when the pointer is preserved — recording the customised bytes instead
  # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
  _REFRESH_PROTOCOL_CANON_HASH=""
  if command -v _hash_stdin >/dev/null 2>&1; then
    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
  fi

  # ---- OBSERVE -------------------------------------------------------------
  local _lt _pr _lc
  _lt="$( _ov_obs_live_type "$pointer" )"
  _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
  if [ "$_lt" != "regular" ]; then
    _lc="-"
  elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
       && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
    _lc="pristine"
  else
    _lc="edited"
  fi

  # ---- DECIDE --------------------------------------------------------------
  local _pair _verdict
  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
                   "$CEREMONY_EFFECTIVE" upgrade none )"; then
    echo "    WARNING: PROTOCOL.md dimensions are not a legal cell — PRESERVED" >&2
    return 0
  fi
  _verdict="${_pair%% *}"
  _PROTOCOL_HASH_SOURCE="${_pair##* }"

  # ---- EXECUTE -------------------------------------------------------------
  # The guards this surface never had are not new branches: they are what the
  # decision already says. A destination that is not a regular file is
  # adopter-owned, so the verdict is unowned and nothing is written — which is
  # exactly the leaf-symlink / directory / FIFO protection SPEC and the marker
  # acquired during the S296 rounds and the pointer did not.
  case "$_verdict" in
    PRESERVE_UNOWNED|OMIT_RECORD)
      case "$_lt" in
        symlink) echo "    SKIP: PROTOCOL.md is a symlink — refusing to write THROUGH it (would mutate a path outside the target)" >&2 ;;
        dir|dir_empty) echo "    SKIP: PROTOCOL.md is a directory — adopter-owned, refusing to write into it" >&2 ;;
        special) echo "    SKIP: PROTOCOL.md is an unsupported special file — preserved, surface untouched" >&2 ;;
        *) echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4)" ;;
      esac
      return 0
      ;;

    PRESERVE_OWNED)
      _PROTOCOL_DELIVERED=1
      if [ "$_lc" = "edited" ]; then
        # ADR-155 decision (iii): the verified S238 case. An adopter-customised
        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
        # the canonical digest so the next upgrade does not read it as pristine.
        if [ "$DRY_RUN" -eq 0 ] && [ -f "$pointer" ]; then
          mkdir -p "$BAK_DIR" 2>/dev/null || true
          cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
        fi
        echo "    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
      else
        echo "    SKIP: PROTOCOL.md pointer (ownership carried forward)"
      fi
      return 0
      ;;

    DELIVER|REFRESH)
      if [ "$DRY_RUN" -eq 1 ]; then
        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
        return 0
      fi
      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
      # Backup-always before the overwrite, even with no baseline manifest —
      # this is what made the S238 loss recoverable on a FIRST upgrade.
      if [ -f "$pointer" ]; then
        mkdir -p "$BAK_DIR" 2>/dev/null || true
        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
      fi
      cat > "$pointer" <<EOF
# Protocol reference

$body
EOF
      _PROTOCOL_DELIVERED=1
      echo "    REFRESHED: PROTOCOL.md pointer"
      return 0
      ;;
  esac
}

# ===========================================================================
# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
# refresh + framework version marker refresh.
# ---------------------------------------------------------------------------
# Ownership of the three conditional surfaces (PROTOCOL.md, SPEC/v1,
# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,

--- decision function refs ---
scripts/upgrade.sh:1064:_classify_against_baseline() {
scripts/upgrade.sh:1215:    verdict="$( _classify_against_baseline "$rel" )"
scripts/upgrade.sh:1313:      _drv="$( _classify_against_baseline "$rel_path" )"
scripts/upgrade.sh:1354:    _bfr_verdict="$( _classify_against_baseline "$rel_path" )"
scripts/upgrade.sh:1613:    PRESERVE_OWNED)
scripts/upgrade.sh:1913:    PRESERVE_OWNED)
scripts/upgrade.sh:2068:    PRESERVE_OWNED)
scripts/tests/test-ownership-verdict-unit.sh:61:while IFS=$'\t' read -r id surface prior_record live_type live_content \
scripts/tests/test-ownership-verdict-unit.sh:80:            "$live_content" "$source_has" "$mode" "$ceremony" \

--- state writer context ---
#
#   * Atomic: python writes a same-directory tempfile, then os.replace().
#   * Updated on every run: first_recorded_at + run_count + a bounded
#     history (last 20 runs) survive re-installs; request/operations
#     reflect the LATEST run.
#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
#     become upgrade DEFAULTS when its own flags are omitted. A missing or
#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
#     path — never an error, never a no-op (debate C back-compat must-fix).
#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
#     ADR-155 baseline manifest (whoever can write the target tree can
#     rewrite it). upgrade.sh charset-validates every replayed value and
#     falls back on anything suspect; values are data, never eval-ed.
#   * Fail-open: no python3 / write error => stderr NOTE, install still
#     succeeds. Dry-run never writes (the "no files modified" promise).
#   * NOT covered by the baseline-manifest enumeration (like the manifest
#     dotfile itself), so the upgrade classifier never touches it.
_write_install_state() {
  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: install-state skipped (python3 not found) — upgrade.sh will use the ADR-155 fallback path" >&2
    return 0
  fi
  local state_file="$TARGET/.claude/.install-state.json"
  local fw_version=""
  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  fi

  echo ""
  echo "==> Writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"

  # Flat key/value pairs, argv-passed (PLAN-106 G.2.b house pattern: never
  # source-string interpolation; python3 -I + PYTHONNOUSERSITE=1). Keys with
  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
  local pairs=(
    "target" "$TARGET"
    "mode" "$MODE"
    "profile" "$PROFILE"
    "stack" "$STACK"
    "stack_explicit" "$STACK_EXPLICIT"
    "ceremony" "$CEREMONY"
    "github_owner" "$GITHUB_OWNER"
    "with_reference_personas" "$WITH_REFERENCE_PERSONAS"
    "strict_placeholders" "$STRICT_PLACEHOLDERS"
    "verify" "$VERIFY"
    "harness" "$HARNESS"
    "managed_hooks" "$CODEX_MANAGED_HOOKS"
    "ph.OWNER_NAME" "$PH_OWNER_NAME"
    "ph.PROJECT_NAME" "$PH_PROJECT_NAME"
    "ph.PROJECT_PATH" "$PH_PROJECT_PATH"
    "ph.STACK" "$PH_STACK"
    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
    "ph.DEPLOY_COMMAND" "$PH_DEPLOY_COMMAND"
    "ph.DEPLOY_PLATFORM" "$PH_DEPLOY_PLATFORM"
    "ph.DEPLOY_TARGET" "$PH_DEPLOY_TARGET"
    "ph.RUNTIME_NOTES" "$PH_RUNTIME_NOTES"
    "ph.DATABASE" "$PH_DATABASE"
    "ph.N_BACKEND" "$PH_N_BACKEND"
    "ph.N_FRONTEND" "$PH_N_FRONTEND"
    "ph.FRONTEND_STACK" "$PH_FRONTEND_STACK"
    "ph.FRONTEND_PATH" "$PH_FRONTEND_PATH"
    "ph.FRONTEND_REPO_PATH" "$PH_FRONTEND_REPO_PATH"
    "ph.UI_LIBRARY" "$PH_UI_LIBRARY"
    "ph.STATE_MANAGEMENT" "$PH_STATE_MANAGEMENT"
    "ph.REALTIME_TRANSPORT" "$PH_REALTIME_TRANSPORT"
    "ph.CHARTING_LIBRARY" "$PH_CHARTING_LIBRARY"
    "ph.AUTH_PROVIDER" "$PH_AUTH_PROVIDER"
    "ph.I18N_FRAMEWORK" "$PH_I18N_FRAMEWORK"
    "ph.TEST_FRAMEWORK" "$PH_TEST_FRAMEWORK"
    "ph.TEST_TOOL" "$PH_TEST_TOOL"
    "ph.TEST_COUNT" "$PH_TEST_COUNT"
    "ph.LINT_TOOL" "$PH_LINT_TOOL"
    "ph.CI_TOOL" "$PH_CI_TOOL"
    "ph.APP_NAME" "$PH_APP_NAME"
    "ph.SOURCE_FILE_COUNT" "$PH_SOURCE_FILE_COUNT"
    "ph.LINE_COUNT" "$PH_LINE_COUNT"
    "ph.LINES" "$PH_LINES"
    "ph.FILE_COUNT" "$PH_FILE_COUNT"
    "ph.PAGE_COUNT" "$PH_PAGE_COUNT"
3166:# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
3251:        "placeholders": {},

exec
/bin/zsh -lc "sed -n '2990,3310p' scripts/upgrade.sh; printf '\\n--- ownership function ---\\n'; grep -R -n '"'^_ownership_verdict'"' scripts .claude | head -20; sed -n '1,260p' scripts/_ownership_verdict_lib.sh 2>/dev/null || true" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 599ms:
scripts/_framework_manifest_set.sh:472:_ownership_verdict() {
.claude/plans/PLAN-167/evidence/W2-manifest-set-with-verdict.sh.txt:472:_ownership_verdict() {
.claude/plans/PLAN-167/debate/round-1/proposal.md:116:_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
.claude/plans/PLAN-167/rail/codex-r3.md:14565:_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
.claude/plans/PLAN-167/rail/codex-r1.md:8699:_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
.claude/plans/PLAN-167-ownership-decision-table.md:705:_ownership_verdict <surface> <prior_record> <live_type> <live_content> \

exec
/bin/zsh -lc "sed -n '430,610p' scripts/_framework_manifest_set.sh; printf '\\n--- install pointer render ---\\n'; sed -n '1850,2010p' scripts/install.sh; printf '\\n--- replay read state ---\\n'; grep -nE '_INSTALL_STATE|placeholders|PROTOCOL_SOURCE|_REPLAY' scripts/upgrade.sh | sed -n '1,180p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
    rm -f "$_wbm_tmp" "$_wbm_tmp.sorted" 2>/dev/null || true
    echo "    NOTE: baseline manifest atomic mv failed — advisory only" >&2
  fi
  return 0
}

# =============================================================================
# PLAN-167 — _ownership_verdict: THE ownership decision.
#
# install.sh and upgrade.sh stop deciding and start executing. Every defect in
# the 35-finding S296 review series was a cell of this space whose answer was
# decided branch-locally, so two branches could disagree about the same
# question and nothing detected it.
#
#   $1 surface        spec | protocol | marker
#   $2 prior_record   none | hash | link_match | link_retargeted
#   $3 live_type      absent | dir | dir_empty | regular | symlink | special
#                     | ancestor_symlink
#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
#                     | edited | -
#   $5 source_has     yes | no
#   $6 mode           copy | link
#   $7 ceremony       user | maintainer
#   $8 operation      install_fresh | install_rerun | upgrade
#   $9 skip_requested none | self | descendant
#
#   stdout: "<VERDICT> <HASH_SOURCE>", rc 0
#   rc 1, no output: a combination the legality rules forbid.
#
# PURE: no filesystem, no globals, no environment. Callers observe the nine
# dimensions and pass them in. That purity is what lets the same table drive a
# millisecond unit oracle as well as the ~25-minute end-to-end suite; S296 had
# only the slow instrument, at one cell per ~40-minute round.
#
# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
# failed backup is not a property of these nine dimensions — it is the CALLER
# failing to carry out a verdict it was handed. And per INV-3 that failure
# NEVER advances the record: recording a delivery that did not happen is the
# over-claiming direction ADR-155-AMEND-1 §3 forbids.
#
# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
# =============================================================================
_ownership_verdict() {
  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"

  # Do not touch the surface; decide the RECORD. Ownership continuity and the
  # digit it carries are separate decisions, and moving one without the other
  # produced four distinct defects — so they are resolved together, once.
  _ov_carry() {
    case "$_ov_prior" in
      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
    esac
    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
    # bytes now on disk, which is how a later upgrade comes to overwrite an
    # adopter edit and uninstall comes to delete it.
    if [ "$_ov_surface" = "protocol" ] \
       || [ "$_ov_shas" = "no" ] \
       || [ "$_ov_ltype" = "dir_empty" ]; then
      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
    else
      printf 'PRESERVE_OWNED HASH_SOURCE'
    fi
  }

  # The framework must not claim this path. Whether a record existed changes
  # only which NAME the observation takes (OQ-9 — the evidence that these are
  # one outcome, not two).
  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.
  # OMIT_RECORD dizia a mesma coisa — sem registro no disco — e diferia apenas
  # por já existir registro antes, que é a coluna prior_record. Um membro de
  # enum redundante é onde dois ramos discordam sobre qual deles se aplica.
  _ov_unowned() { printf 'PRESERVE_UNOWNED HASH_NONE'; }

  # --- Stage A: gates that refuse to act, in priority order ------------------

  # A1. The source cannot deliver this surface.
  if [ "$_ov_shas" = "no" ]; then
    case "$_ov_surface" in
      marker)   printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;  # --pin: readers fall back to VERSION
      protocol) return 1 ;;                                  # R-03: generated, never absent
      *)        _ov_carry; return 0 ;;
    esac
  fi

  # A2. A user ceremony never receives the root surfaces (WS4).
  if [ "$_ov_cer" = "user" ] && [ "$_ov_surface" != "marker" ]; then
    if [ "$_ov_op" = "install_fresh" ]; then printf 'PRESERVE_UNOWNED HASH_NONE'
    else _ov_carry; fi
    return 0
  fi

  # A3. Reachable only by writing THROUGH a symlink, out of the target tree.
  # Always unowned: the relpath sanitizer already dropped any record whose path
  # crosses a symlink, so there is no record left to carry (docs §5.8).
  if [ "$_ov_ltype" = "ancestor_symlink" ]; then _ov_unowned; return 0; fi

  # A4. A leaf symlink is healthy ONLY as the recorded link-mode delivery.
  # The absence of a LINK row is not a match — it is the absence of evidence.
  if [ "$_ov_ltype" = "symlink" ]; then
    if [ "$_ov_prior" = "link_match" ]; then printf 'PRESERVE_OWNED LINK_RECORD'
    else _ov_unowned; fi
    return 0
  fi

  # A5. Anything that exists but is not shaped like this surface is
  # adopter-owned: never write into it, never through it, never block on it.
  case "$_ov_surface" in
    spec)
      case "$_ov_ltype" in special) _ov_unowned; return 0 ;; esac ;;
    protocol|marker)
      case "$_ov_ltype" in dir|dir_empty|special) _ov_unowned; return 0 ;; esac ;;
  esac

  # A6. An explicit skip is honoured as a UNIT — a partial contract refresh is
  # incoherent, so a descendant skip preserves the whole tree.
  if [ "$_ov_skip" != "none" ]; then _ov_carry; return 0; fi

  # --- Stage B: ownership resolution ----------------------------------------
  _ov_owned=""
  if [ "$_ov_prior" = "hash" ] || [ "$_ov_prior" = "link_match" ]; then
    _ov_owned=1
  elif [ "$_ov_ltype" = "absent" ]; then
    _ov_owned=1                                   # new delivery
  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
    _ov_owned=1                                   # current-source takeover / legacy migration
  fi
  # legacy_pristine_partial is deliberately NOT owned: every regular file may
  # match a shipped release, but a tree carrying an entry the fingerprint
  # cannot inventory has not been inventoried, and a partial inventory must
  # never certify a wholesale replace (ADR-155-AMEND-1 §4).

  if [ -z "$_ov_owned" ]; then _ov_unowned; return 0; fi

  # --- Stage C: execution ---------------------------------------------------
  if [ "$_ov_ltype" = "absent" ]; then
    case "$_ov_surface" in
      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
      *)        printf 'DELIVER HASH_SOURCE' ;;
    esac
    return 0
  fi

  # An install rerun does not re-deliver an existing surface; it decides the
  # record. Only the upgrade's forced route replaces content.
  if [ "$_ov_op" != "upgrade" ]; then _ov_carry; return 0; fi

  # The pointer is the ONE surface where an adopter edit is PRESERVED rather
  # than treated as a fork. SPEC/v1 is deliberately the opposite: it is the
  # published compliance CONTRACT, so an edit is a fork and the forced route
  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
  # prose, and overwriting a customised one is the verified S238 data loss that
  # ADR-155 decision (iii) exists to close.
  #
  # The recorded digest stays CANONICAL either way: recording the customised
  # bytes would make the NEXT upgrade read H_dst==H_base and clobber them.
  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
    printf 'PRESERVE_OWNED HASH_CANONICAL_POINTER'
    return 0
  fi

  case "$_ov_surface" in
    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
    *)        printf 'REFRESH HASH_SOURCE' ;;
  esac
}

--- install pointer render ---
    {
      echo ""
      echo "# PLAN-165 CX-3: per-machine posture/runtime state (never commit)"
      echo "$line"
    } >> "$gitignore"
    echo "    APPENDED to .gitignore: $line"
  done
}

if [[ "$CEREMONY" != "user" ]]; then install_mcp_secrets_dir; fi  # WS4-guard-mcp
if [[ "$CEREMONY" != "user" ]]; then install_posture_state_ignores; fi  # PLAN-165 CX-3

# ---- 7. Project-local templates (CLAUDE.md, MEMORY.md, .mcp.json — never overwrite) ----

echo ""
echo "==> Installing project templates"
_state_record_op "install_project_templates" "ceremony=$CEREMONY"
if [[ "$CEREMONY" != "user" ]]; then  # WS4-guard-projtmpl
install_template "templates/CLAUDE.md" "CLAUDE.md"
install_template "templates/MEMORY.md" "MEMORY.md"
# PLAN-135 W1 S5-lite: project-scope MCP registration for the Codex
# pair-rail (the 'codex' server backs the mcp__codex__codex |
# mcp__codex__codex-reply matchers in settings.json). install_template
# is idempotent EXISTS->SKIP — an adopter's own .mcp.json is never
# clobbered. Credentials via ${ENV} expansion only; no secrets on disk.
# Root-level file => stays inside the WS4-guard-projtmpl maintainer
# guard (user ceremony writes .claude/ only).
install_template "templates/.mcp.json" ".mcp.json"
fi  # WS4-guard-projtmpl

# ---- 8. Drop a pointer to PROTOCOL.md (DevOps-P1-4: relative, not absolute) ----

install_protocol_pointer() {
  if [[ -e "$TARGET/PROTOCOL.md" ]]; then
    return 0
  fi

  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
  # If the framework repo lives outside the target repo (common case),
  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
  # manually. Absolute paths are NOT hardcoded — they break portability
  # across dev machines and CI runners.
  #
  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
  # framework was copied INTO the target — use a relative pointer. In
  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
  local pointer_body
  case "$SOURCE_DIR" in
    "$TARGET"/*)
      local rel="${SOURCE_DIR#$TARGET/}"
      pointer_body="The full CEO orchestration protocol lives at:
./${rel}/PROTOCOL.md

To pull updates:
  ( cd ./${rel} && git pull )
  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
      ;;
    *)
      pointer_body="The full CEO orchestration protocol lives at:
{{PROTOCOL_SOURCE}}/PROTOCOL.md

Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).

To pull updates:
  ( cd {{PROTOCOL_SOURCE}} && git pull )
  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
      ;;
  esac

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
    return 0
  fi

  cat > "$TARGET/PROTOCOL.md" <<EOF
# Protocol reference

$pointer_body
EOF
  echo "    CREATED: PROTOCOL.md (pointer)"
  _state_record_op "install_protocol_pointer" "PROTOCOL.md"
  # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
  # reached when the heredoc actually wrote the pointer (the pre-existing
  # early-return above never gets here, so an adopter's own root
  # PROTOCOL.md is never inventoried as framework-owned; r13/r17).
  _DELIVERED_PROTOCOL=1
  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
}

if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto

# ----------------------------------------------------------------------
# P1-CR-3 / VP-F1: placeholder substitution pass
# ----------------------------------------------------------------------
# Iterate over a deterministic list of placeholder files (the ones
# templates/ writes out) and apply `sed -i` substitutions for every
# PH_* variable that is non-empty. Anything left as `{{...}}` after the
# pass is reported with a stderr warning.
#
# We restrict the pass to files install.sh actually placed (the
# templates/* files) to avoid touching user-authored content. If
# CLAUDE.md / MEMORY.md already existed at target, we leave them alone
# (install.sh never overwrites them).

# Portable sed -i for GNU + BSD (macOS): write to .tmp and mv.
portable_sed_inplace() {
  # $1 = sed script, $2 = file
  local script="$1" file="$2"
  local tmp="${file}.ceo-sed-tmp"
  sed "$script" "$file" > "$tmp" && mv "$tmp" "$file"
}

# Build the sed script iteratively. Each non-empty placeholder adds an
# expression. We use `|` as the delimiter so slashes in values (paths)
# don't break. Values with `|` are escaped.
build_sed_script() {
  local script=""
  _add_sub() {
    local key="$1" val="$2"
    if [[ -n "$val" ]]; then
      # Escape | & \ in the replacement
      local esc
      esc="$(printf '%s' "$val" | sed 's/[|&\\]/\\&/g')"
      script="${script}s|{{${key}}}|${esc}|g;"
    fi
  }
  _add_sub "OWNER_NAME"          "$PH_OWNER_NAME"
  _add_sub "OWNER_HANDLE"        "$GITHUB_OWNER"
  _add_sub "PROJECT_NAME"        "$PH_PROJECT_NAME"
  _add_sub "PROJECT_PATH"        "$PH_PROJECT_PATH"
  _add_sub "STACK"               "$PH_STACK"
  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
  _add_sub "DEPLOY_COMMAND"      "$PH_DEPLOY_COMMAND"
  _add_sub "DEPLOY_PLATFORM"     "$PH_DEPLOY_PLATFORM"
  _add_sub "DEPLOY_TARGET"       "$PH_DEPLOY_TARGET"
  _add_sub "RUNTIME_NOTES"       "$PH_RUNTIME_NOTES"
  _add_sub "DATABASE"            "$PH_DATABASE"
  _add_sub "N_BACKEND"           "$PH_N_BACKEND"
  _add_sub "N_FRONTEND"          "$PH_N_FRONTEND"
  _add_sub "FRONTEND_STACK"      "$PH_FRONTEND_STACK"
  _add_sub "FRONTEND_PATH"       "$PH_FRONTEND_PATH"
  _add_sub "FRONTEND_REPO_PATH"  "$PH_FRONTEND_REPO_PATH"
  _add_sub "UI_LIBRARY"          "$PH_UI_LIBRARY"
  _add_sub "STATE_MANAGEMENT"    "$PH_STATE_MANAGEMENT"
  _add_sub "REALTIME_TRANSPORT"  "$PH_REALTIME_TRANSPORT"
  _add_sub "CHARTING_LIBRARY"    "$PH_CHARTING_LIBRARY"
  _add_sub "AUTH_PROVIDER"       "$PH_AUTH_PROVIDER"
  _add_sub "I18N_FRAMEWORK"      "$PH_I18N_FRAMEWORK"
  _add_sub "TEST_FRAMEWORK"      "$PH_TEST_FRAMEWORK"
  _add_sub "TEST_TOOL"           "$PH_TEST_TOOL"
  _add_sub "TEST_COUNT"          "$PH_TEST_COUNT"
  _add_sub "LINT_TOOL"           "$PH_LINT_TOOL"
  _add_sub "CI_TOOL"             "$PH_CI_TOOL"
  _add_sub "APP_NAME"            "$PH_APP_NAME"
  _add_sub "SOURCE_FILE_COUNT"   "$PH_SOURCE_FILE_COUNT"
  _add_sub "LINE_COUNT"          "$PH_LINE_COUNT"
  _add_sub "LINES"               "$PH_LINES"
  _add_sub "FILE_COUNT"          "$PH_FILE_COUNT"
  _add_sub "PAGE_COUNT"          "$PH_PAGE_COUNT"

--- replay read state ---
644:_INSTALL_STATE_FILE="$TARGET/.claude/.install-state.json"
645:_REPLAY_SOURCE="cli-default"
653:  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
682:' "$_INSTALL_STATE_FILE" 2>/dev/null
686:  if [[ -f "$_INSTALL_STATE_FILE" ]]; then
712:        _REPLAY_SOURCE="replay"
715:      _REPLAY_SOURCE="fallback-invalid-state"
723:    _REPLAY_SOURCE="fallback-no-state"
746:  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
763:' "$_INSTALL_STATE_FILE" 2>/dev/null
786:if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
1553:{{PROTOCOL_SOURCE}}/PROTOCOL.md
1555:Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
1559:  ( cd {{PROTOCOL_SOURCE}} && git pull )
1560:  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
3166:# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
3188:    "replay_source" "$_REPLAY_SOURCE"
3251:        "placeholders": {},
3307:' "$_INSTALL_STATE_FILE" "${_UP_OPS_FILE:-}" "$fw_version" "${#pairs[@]}" "${pairs[@]}" \

exec
/bin/zsh -lc "git tag --sort=version:refname | tail -30; printf '\\n--- refresh history ---\\n'; git log --oneline --follow -- scripts/upgrade.sh | head -30; printf '\\n--- pointer function diffs/history commits ---\\n'; git log -S'{{PROTOCOL_SOURCE}}/PROTOCOL.md' --oneline --all -- scripts/upgrade.sh | head -30" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-q9G3VSbe' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-al5qM8LG' (errno=Operation not permitted)
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

--- refresh history ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GqWWABg4' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-2eS0wONU' (errno=Operation not permitted)
7c0828a feat(PLAN-167): ownership decision table — one function decides, callers execute
4f05eb7 governance(ADR-110-AMEND-2 + ADR-164-AMEND-1): pair-rail 120/150->180/210 + timeout_ms + censoring-rate trigger; ADR count 188 [SENT-S292-C]
8ed9f6f feat(PLAN-163): substrate uplift — CC 2.1.220 + Claude 5 family main pack [SENT-PLAN163-PACK]
e718cd8 fix(PLAN-161): U1/U2/U3 — upgrade dry-run identity, exclusion predicate, opt-in purge [SENT-PLAN161]
7769610 feat(PLAN-156): SENT-GK-C — installer --harness grok + CI matrix
8c032df feat(PLAN-155): land Wave-5 codex installer — _codex_harness + matrix tests [SENT-CX-C]
2094175 feat(PLAN-153 wave-B): land installer/release lifecycle — install-state + replay, doctor/repair, profiles manifest, release idempotency, plugin manifests [SENT-B round-2]
9777a8d ceo-orchestration v1.0.0 — initial public release

--- pointer function diffs/history commits ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-mgMILRot' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-nFOlGsgr' (errno=Operation not permitted)
9777a8d ceo-orchestration v1.0.0 — initial public release

exec
/bin/zsh -lc "grep ' RED ' scripts/tests/ownership-baseline-map.txt; grep '"'^OWN-0074'"' scripts/tests/ownership_table.tsv scripts/tests/ownership-baseline-map.txt; grep -nE '"'^OWN-00(16|24|27|74)'"' scripts/tests/ownership_table.tsv" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F2
OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_NONE              rc=0   r3-F1
OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_PRIOR_RECORD      rc=0   r4-F5
OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
scripts/tests/ownership_table.tsv:OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
scripts/tests/ownership-baseline-map.txt:OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
22:OWN-0016	spec	hash	dir_empty	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r11-F2	open=r11-F2; flag-only continuity emits zero file records
30:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
33:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
69:OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it

exec
/bin/zsh -lc "grep -nE 'live_content|legacy_pristine|edited\\)' scripts/tests/test-ownership-table.sh | head -120; sed -n '390,580p' scripts/tests/test-ownership-table.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
269:_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
325:    edited)
351:    legacy_pristine)
357:        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
366:    legacy_pristine_partial)
373:        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
494:  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
544:  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
665:while IFS=$'\t' read -r id surface prior_record live_type live_content \
673:  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
  # PRESERVE_UNOWNED: what a record USED to be no longer changes the name.
  local bd="$1" ad="$2" ar="$4" out="$5" surface="$6" rel="$7" op="${8:-upgrade}"
  if [[ "$bd" != "$ad" ]]; then
    if [[ "$bd" == "absent" ]]; then printf 'DELIVER'; else printf 'REFRESH'; fi
    return 0
  fi
  # Unchanged target from here on.
  if grep -Eq "$_ABORT_MARKERS" "$out" 2>/dev/null; then printf 'ABORT_SURFACE'; return 0; fi
  # A REFRESH that writes byte-identical content leaves the CONTENT unchanged,
  # so a content digest alone cannot separate it from a PRESERVE.
  #
  # Backup presence does not settle it either: the ADOPTER-FORK preserve path
  # also snapshots into BAK_DIR, so "a backup exists" is evidence the framework
  # looked, not that it wrote.
  #
  # Modification time settles it on the UPGRADE path, from state and without
  # reading prose: the forced route replaces content with `cp -R` (no -p),
  # which stamps new mtimes, while every preserve path leaves bytes AND
  # timestamps alone.
  #
  # Restricted to upgrade deliberately. install.sh re-runs placeholder
  # SUBSTITUTION on every invocation, so it rewrites the pointer with identical
  # bytes and a fresh mtime — a write with no semantic content. Counting that
  # as REFRESH would report an ownership change where none happened.
  #
  # No single signal is valid everywhere here: the content digest cannot see an
  # identical-content refresh, the backup fires on the preserve-with-snapshot
  # path, and mtime fires on install re-substitution. Each is used only where
  # it is sound, and the boundary is stated rather than assumed.
  if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
    printf 'REFRESH'; return 0
  fi
  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
  if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
}

_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
  local surface="$1" ar="$2" pr="$3" src="$4"
  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac

  local got="${ar#hash:}"
  local rel; rel="$( _relpath_for "$surface" )"

  # Candidate 1: the bytes now at the target.
  local c_target; c_target="$( _obs_digest "$T/$rel" )"
  # Candidate 2: the framework's copy in the source checkout.
  local c_source; c_source="$( _obs_digest "$src/$rel" )"
  # Candidate 3: the digest the PRE-run manifest recorded.
  local c_prior="${pr#hash:}"
  # Candidate 4: the canonical pointer digest (protocol only).
  local c_pointer="$CANON_POINTER_HASH"

  # For tree surfaces the recorded value is the roll-up of per-file rows, which
  # is not comparable to a content fingerprint — compare tree membership by
  # re-deriving both roll-ups instead.
  if [[ "$surface" == "spec" ]]; then
    local roll_t roll_s
    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
    printf 'HASH_UNCLASSIFIED'; return 0
  fi

  # The canonical pointer digest is the hash of what the framework WOULD
  # generate — it matches no file on disk when the pointer is customised, so it
  # has to be recognised explicitly or every correct record reads as
  # unclassified.
  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
  # digest and the prior record are the SAME bytes, so whichever is tested
  # first wins the name. Testing the prior record first keeps continuity rows
  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
  # when the two genuinely differ — i.e. when the pointer was customised, which
  # is the one cell where the distinction carries meaning.
  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
    printf 'HASH_CANONICAL_POINTER'; return 0
  fi
  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
  printf 'HASH_UNCLASSIFIED'
}

_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
  local root="$1" pfx="$2"
  [[ -d "$root" ]] || { printf ''; return 0; }
  ( cd "$root" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
    | while IFS= read -r r; do
        [[ -n "$r" ]] || continue
        printf '%s  %s/%s\n' "$( _hash_file "$root/$r" 2>/dev/null || echo FAIL )" "$pfx" "${r#./}"
      done | LC_ALL=C sort | _hash_stdin
}

# =============================================================================
# Row execution
# =============================================================================
PASS=0; FAIL=0; AMBIG=0; ERR=0
MAP_LINES=""

_run_row() {
  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
  local fault="${11}"
  local exp_verdict="${12}" exp_hash="${13}" origin="${14}" note="${15}"

  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }

  # --- base selection ------------------------------------------------------
  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
  # Conflating them would erase the r11-F1 cell — see docs §4.1.
  local base_mode="copy"
  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
  local base_ceremony="$ceremony"
  # A user-ceremony row asserting residue of a MAINTAINER install must be built
  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
  local transition_to_user=0
  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
    base_ceremony="maintainer"; transition_to_user=1
  fi

  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
  local src
  if [[ "$source_has" == "no" ]]; then
    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
  elif [[ "$operation" == "install_fresh" ]]; then
    src="$REPO_ROOT"
  else
    # An upgrade/rerun runs against a source NEWER than the one that wrote the
    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
  fi

  # --- base tree -----------------------------------------------------------
  if [[ "$operation" == "install_fresh" ]]; then
    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
    # a base and stripping one record would leave a manifest behind and make the
    # row an install_rerun wearing a fresh label.
    rm -rf "$T"; mkdir -p "$T"
  else
    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
    rm -rf "$T"; mkdir -p "$T"
    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
  fi

  # --- fixture mutation ----------------------------------------------------
  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
  fi
  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
    || { ERR=$((ERR+1)); return; }

  # Fault injection from the `fault` COLUMN. It rode in `note` until round-1
  # consensus C1 ruled that a dimension the harness parses out of prose is a
  # dimension nothing validates.
  local bak_guard=""
  case "$fault" in
    backup_unwritable)
      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
      # before any surface was reached — the branch under test never ran.
      # An unreadable SOURCE makes the copy fail while everything else proceeds.
      bak_guard="$T/$rel"
      chmod 000 "$bak_guard" 2>/dev/null || true ;;
  esac

  # --- BEFORE snapshot -----------------------------------------------------
  local b_digest b_rec
  b_digest="$( _obs_digest "$T/$rel" )"
  b_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_BEFORE="$( _obs_mtime "$T/$rel" )"
  # Everything outside $T that a run could reach. Any change here is an escape.
  _ESCAPE_BEFORE="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  # --- run the REAL script -------------------------------------------------
  local out="$WORK/run-$id.log"; : > "$out"
  local rc=0
  # A `ceremony=user` UPGRADE row asserts residue of a maintainer install that
  # was later re-run as `--ceremony user`. The ceremony is read from
  # .claude/.install-state.json, so labelling the row is not enough: the
  # transition has to actually happen, or upgrade.sh still sees `maintainer`
  # and the row silently tests the wrong branch.
  if [[ "$transition_to_user" -eq 1 && "$operation" == "upgrade" ]]; then
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "$T" --ceremony user \
      >> "$out" 2>&1 || true
  fi

exec
/bin/zsh -lc "sed -n '250,390p' scripts/tests/test-ownership-table.sh; sed -n '580,635p' scripts/tests/test-ownership-table.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
  local nxt="$WORK/src-next"
  [[ -d "$nxt" ]] && { printf '%s' "$nxt"; return 0; }
  _clone_source "$nxt" || return 1
  local first
  first="$( ( cd "$nxt/SPEC/v1" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
  first="${first#./}"
  [[ -n "$first" ]] && printf '\n<!-- next-version marker (PLAN-167 fixture) -->\n' >> "$nxt/SPEC/v1/$first"
  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
  printf '%s' "$nxt"
}

_strip_record() {  # $1 = manifest, $2 = relpath — make prior_record=none
  local m="$1" rel="$2" tmp
  [[ -f "$m" ]] || return 0
  tmp="$( mktemp "$m.XXXXXX" )" || return 1
  grep -vE "^([0-9a-f]{64}|LINK)  ${rel//./\\.}(/|  |$)" "$m" > "$tmp" 2>/dev/null
  mv "$tmp" "$m"
}

_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
  local surface="$1" ltype="$2" lcontent="$3" src_root="$4" prior="${5:-none}"
  local rel; rel="$( _relpath_for "$surface" )"
  local p="$T/$rel"

  # A `link_match` row means the live symlink IS the recorded delivery. The
  # base --link install already created exactly that, so pointing it somewhere
  # else here would silently convert every link_match row into a
  # link_retargeted one — the fixture would then agree with the expectation for
  # the wrong reason, which is how a row goes green while testing nothing.
  if [[ "$ltype" == "symlink" && "$prior" == "link_match" ]]; then
    [[ -L "$p" ]] || { echo "FIXTURE-ERR: $rel is not a symlink after a --link base install" >&2; return 1; }
    ltype="__keep__"
  fi

  case "$ltype" in
    absent)   rm -rf "$p" ;;
    dir_empty)
      rm -rf "$p"; mkdir -p "$p" ;;
    regular)
      if [[ -d "$p" ]]; then rm -rf "$p"; fi
      [[ -e "$p" ]] || { mkdir -p "$( dirname "$p" )"; printf 'adopter regular file\n' > "$p"; }
      ;;
    symlink)
      # The foreign leaf is a TRIPWIRE, not scenery. A surface written with
      # `cat >` follows a leaf symlink and mutates whatever it points at —
      # OUTSIDE the target tree, which is adopter or system data. Comparing
      # only the target would let that row report GREEN while the run
      # destroyed a file the test never looked at.
      rm -rf "$p"
      mkdir -p "$( dirname "$p" )" "$WORK/foreign"
      printf 'foreign content — MUST NOT be modified by any run\n' > "$WORK/foreign/leaf"
      ln -s "$WORK/foreign/leaf" "$p"
      ;;
    special)
      rm -rf "$p"; mkdir -p "$( dirname "$p" )"; mkfifo "$p" 2>/dev/null || return 1 ;;
    ancestor_symlink)
      # Move the parent aside and symlink it back — the leaf is then reachable
      # only by writing THROUGH a symlink out of the target tree.
      local parent; parent="$( dirname "$p" )"
      local real="$WORK/ancestor-real-$surface"
      rm -rf "$real"; mkdir -p "$( dirname "$real" )"
      mv "$parent" "$real" 2>/dev/null || return 1
      ln -s "$real" "$parent"
      ;;
    dir)
      # On a rerun the base install already left the tree; on a structurally
      # fresh target there is nothing yet, so the adopter's own directory has
      # to be built here.
      if [[ ! -d "$p" || -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$p"; printf 'adopter content\n' > "$p/adopter.md"
      fi
      ;;
  esac

  case "$lcontent" in
    edited)
      if [[ -d "$p" && ! -L "$p" ]]; then
        local victim
        victim="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
        victim="${victim#./}"
        # Guard the empty-tree case: without it the redirect target collapses to
        # "$p/" and the shell reports "Is a directory" instead of mutating.
        # if/fi, NOT `[[ ]] && cmd`: as the last statement of the branch, a
        # false test would make the whole function return 1 and the row would
        # be recorded as a harness error rather than run.
        if [[ -n "$victim" ]]; then
          printf '\nADOPTER EDIT\n' >> "$p/$victim"
        fi
      elif [[ -f "$p" && ! -L "$p" ]]; then
        printf 'ADOPTER EDIT\n' >> "$p"
      fi
      ;;
    pristine)
      # "byte-identical to what THIS run's source would deliver" — so it must be
      # synced from the RUN source, not left as whatever the base install wrote.
      # The generated pointer has no source file: the base install's own output
      # IS its pristine form, so protocol is left untouched.
      if [[ "$surface" != "protocol" && -e "$src_root/$rel" && ! -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$( dirname "$p" )"; cp -R "$src_root/$rel" "$p" 2>/dev/null || true
      fi
      ;;
    legacy_pristine)
      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
      # derived from — never a hand-built approximation, which would test the
      # fixture rather than the migration.
      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
        echo "             approximation. A CI checkout using fetch-depth:1 has NO tags" >&2
        echo "             — that job needs fetch-depth:0 or fetch-tags:true." >&2
        return 1
      fi
      rm -rf "$p"; mkdir -p "$p"
      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
        | ( cd "$T" && tar -xf - ) || return 1
      ;;
    legacy_pristine_partial)
      # A pristine shipped tree that ALSO carries an entry the fingerprint
      # cannot inventory. Distinct from `edited`: every regular file still
      # matches a shipped release, so content alone reads "pristine" — and the
      # tree must STILL be refused, because a partial inventory can never
      # certify a wholesale replace (ADR-155-AMEND-1 §4).
      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
        return 1
      fi
      rm -rf "$p"; mkdir -p "$p"
      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
        | ( cd "$T" && tar -xf - ) || return 1
      ln -s /dev/null "$p/adopter-added.link" 2>/dev/null || true
      ;;
  esac

}

# =============================================================================
# Verdict derivation
# =============================================================================
_derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 operation
  # $3 (before-record) went unused when OQ-9 collapsed OMIT_RECORD into
  # PRESERVE_UNOWNED: what a record USED to be no longer changes the name.
  fi
  if [[ "$operation" == "upgrade" ]]; then
    local uargs=( "$T" )
    [[ "$skip_requested" == "self" ]] && uargs+=( --skip "$rel" )
    if [[ "$skip_requested" == "descendant" ]]; then
      local victim; victim="$( ( cd "$T/$rel" 2>/dev/null && find . ! -type d -print 2>/dev/null | LC_ALL=C sort | head -1 ) )"
      victim="${victim#./}"
      [[ -n "$victim" ]] && uargs+=( --skip "$rel/$victim" )
    fi
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/upgrade.sh" "${uargs[@]}" >> "$out" 2>&1
    rc=$?
  else
    local iargs=( "$T" --ceremony "$ceremony" )
    [[ "$mode" == "link" ]] && iargs+=( --link )
    [[ "$transition_to_user" -eq 1 ]] && iargs=( "$T" --ceremony user )
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
    rc=$?
  fi
  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null

  local timed_out=0
  [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1

  # --- AFTER snapshot + derivation ----------------------------------------
  local a_digest a_rec got_verdict got_hash
  a_digest="$( _obs_digest "$T/$rel" )"
  a_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_AFTER="$( _obs_mtime "$T/$rel" )"
  _ESCAPE_AFTER="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  if [[ "$timed_out" -eq 1 ]]; then
    got_verdict="TIMEOUT"; got_hash="TIMEOUT"
  else
    got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
  fi

  # --- compare -------------------------------------------------------------
  local status="RED"
  local alt=""
  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac

  # An escape outranks the verdict comparison. A row whose pair matches while
  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
  # exact damage class this table exists to prevent, and calling that GREEN
  # would be the instrument concealing a data loss.
  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
    status="ESCAPE"; FAIL=$((FAIL+1))
  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
    status="GREEN"; PASS=$((PASS+1))
  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
    status="AMBIG"; AMBIG=$((AMBIG+1))
  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
    status="TIMEOUT"; FAIL=$((FAIL+1))
  else
    FAIL=$((FAIL+1))

exec
/bin/zsh -lc "sed -n '1,260p' .claude/plans/PLAN-168/rail/codex-r1.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
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

exec
/bin/zsh -lc "tail -80 .claude/plans/PLAN-168/rail/codex-r1.md; wc -l .claude/plans/PLAN-168/rail/codex-r1.md; grep -nE '\\[P[0-3]\\]|\"findings\"|overall_correctness|APPROVE|REJECT' .claude/plans/PLAN-168/rail/codex-r1.md | tail -30" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
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
     261 .claude/plans/PLAN-168/rail/codex-r1.md
212:   151	- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.

exec
/bin/zsh -lc "nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '90,260p'; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '350,410p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
    90	   `smoke-install.yml` — **4 caminhos, não 5**:
    91	   ```
    92	   scripts/tests/test-ownership-table.sh
    93	   scripts/tests/test-ownership-verdict-unit.sh
    94	   scripts/tests/ownership_table.tsv
    95	   docs/ownership-decision-table.md
    96	   ```
    97	   > **CORREÇÃO (debate r1, devops must-fix 2).** A versão anterior deste
    98	   > item listava também `scripts/_hash_lib.sh`. **Ele JÁ está nos dois
    99	   > filtros** (`smoke-install.yml:15` e `:54`) — verificado com `grep -n`.
   100	   > A lista foi escrita de memória sem abrir o arquivo, que é exatamente o
   101	   > modo de falha registrado em
   102	   > [[feedback-plan-mechanics-written-from-memory-fail]]. **Abra o arquivo
   103	   > antes de editar.**
   104	2. **Buscar o tag `v1.2.0`** antes do passo dos oráculos.
   105	
   106	   > **AJUSTE (debate r1, devops must-fix 3).** Hardcodar `v1.2.0` no YAML
   107	   > cria uma **segunda fonte de verdade** — o padrão existente no repo
   108	   > resolve o pin por `--print-pin`, e `test-ownership-table.sh` não suporta
   109	   > isso. Duas saídas: (a) dar ao harness um `--print-legacy-tag` e o YAML
   110	   > consumir; (b) aceitar o hardcode e adicionar uma asserção que ele bata
   111	   > com o valor embutido no harness. **(a) é o correto**; (b) só se o
   112	   > orçamento apertar. Nunca deixar os dois divergirem em silêncio.
   113	   ```yaml
   114	   # CORRIGIDO (rail r1 P2): o snippet consome a flag nova — NÃO hardcodar o
   115	   # tag no YAML (recriaria a divergência silenciosa que o parágrafo proíbe).
   116	   - name: Fetch the legacy_pristine tag
   117	     run: |
   118	       set -euo pipefail
   119	       TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
   120	       echo "legacy pristine tag: $TAG"
   121	       git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
   122	       git rev-parse --verify "refs/tags/$TAG^{commit}"
   123	   ```
   124	   **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
   125	   que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
   126	   (rejeitada no consenso do round 1 do PLAN-167).
   127	3. **Dois gates, dois tempos** — e isso exige **DOIS JOBS**, não duas
   128	   entradas de filtro:
   129	   - **por-PR:** `test-ownership-verdict-unit.sh` (segundos, 60 células)
   130	   - **nightly:** `test-ownership-table.sh` (~25 min, 62 installs reais)
   131	
   132	   > **BLOQUEADOR (debate r1, devops must-fix 1).** **NÃO EXISTE trigger
   133	   > `schedule:` em `smoke-install.yml`** — verificado: zero ocorrências de
   134	   > `schedule:`/`cron:`. O AC-4 é **insatisfazível** como estava escrito.
   135	   > Pior: eventos `schedule:` **ignoram filtros `paths:`**, então a divisão
   136	   > não sai de duas linhas num filtro. É preciso **criar** o job nightly
   137	   > (job novo com `if: github.event_name == 'schedule'`, ou workflow
   138	   > separado). **Decidir qual ANTES de codar** — é a diferença entre uma
   139	   > entrada de filtro e um workflow novo.
   140	
   141	   O e2e **não cabe** no teto de 25 min do job atual — o orçamento já foi
   142	   elevado 4× (5→8→20→25). Colocá-lo no caminho por-PR quebra o job.
   143	4. O e2e termina com **4 vermelhos deliberados**. O passo de CI precisa
   144	   aceitar isso explicitamente **e falhar se o CONJUNTO de vermelhos MUDAR**
   145	   — inclusive se encolher. Verde total significa que a tabela mudou.
   146	
   147	   > **CORREÇÃO (debate r1, devops must-fix 4).** `diff` literal contra
   148	   > `ownership-baseline-map.txt` **falha sempre em CI**: o cabeçalho do
   149	   > arquivo carrega caminhos da máquina que o gerou (`scratch:/var/folders/…`,
   150	   > `table:/tmp/claude-501/…`). Verificado nas linhas 2-4 do arquivo commitado.
   151	   >
   152	   > **Comparar o CONJUNTO DE IDs, não o arquivo.** O contrato estável é:
   153	   > ```sh
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
   191	> # (rail r2 P1) status ≠ GREEN e ≠ RED — TIMEOUT/ESCAPE/AMBIG — NUNCA é
   192	> # aceitável: um id esperado-vermelho que degrada para TIMEOUT/ESCAPE mantém
   193	> # o CONJUNTO intacto e esconderia uma regressão PIOR atrás de "mesmo set".
   194	> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2!="GREEN" && $2!="RED"' \
   195	>   | grep . && { echo "::error::célula em status nunca-aceitável"; exit 1; }
   196	> # conjunto RED exato observado vs esperado — QUALQUER diferença falha
   197	> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2=="RED" {print $1}' \
   198	>   | LC_ALL=C sort > /tmp/own-got.txt
   199	> grep -E '^OWN-' scripts/tests/ownership-expected-reds.txt | LC_ALL=C sort > /tmp/own-exp.txt
   200	> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
   201	>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
   202	> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
   203	> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
   204	> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
   205	> echo "ownership nightly: conjunto de vermelhos estável"
   206	> ```
   207	> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
   208	> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
   209	>
   210	> **Implementação entregue (W1):** o contrato acima vive em
   211	> `scripts/tests/ownership-nightly-gate.sh` (script chamado pelo workflow —
   212	> testável, diferente de YAML inline) com controle positivo
   213	> `scripts/tests/test-ownership-nightly-gate.sh`: **12 cenários de falha
   214	> plantados com harness fake**, incluindo os degrades TIMEOUT/ESCAPE/AMBIG
   215	> do rail r2.
   216	
   217	### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
   218	
   219	1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
   220	   - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
   221	   - **(b)** a geração do ponteiro vira **uma função compartilhada** que os
   222	     dois chamam — mais próximo da decisão (i) do ADR-155, e fecha a classe
   223	     em vez de o sintoma.
   224	   **Recomendação: (b).** (a) conserta este ponteiro; (b) impede o próximo.
   225	2. **⚠️ O FIX SOZINHO NÃO CURA QUEM JÁ ESTÁ EM CAMPO** (debate r1, security
   226	   must-fix 1). Adotante que já sofreu um upgrade tem `{{PROTOCOL_SOURCE}}`
   227	   literal no disco. Isso classifica `live_content=edited` ⇒ o veredito é
   228	   `PRESERVE_OWNED` e o ponteiro degradado é **preservado para sempre** —
   229	   verificado em `upgrade.sh` no ramo `PRESERVE_OWNED`/`_lc = edited`.
   230	   Pior: `doctor.sh` e `uninstall.sh` passam a tratar a **degradação do
   231	   próprio framework** como customização do adotante.
   232	
   233	   **Cura:** reconhecedor de corpo legado ⇒ `REFRESH` **com backup**.
   234	
   235	   > **⚠️ CORRIGIDO 2× (rail r1 P1 + r2 P1): o reconhecedor é por
   236	   > RECONSTRUÇÃO DE TEMPLATE, nunca substring E nunca hash estático.**
   237	   > Substring é destrutivo (um `PROTOCOL.md` do adotante que legitimamente
   238	   > CONTÉM o token seria força-refreshado — backup não desfaz a perda do
   239	   > arquivo ATIVO). Mas hash estático por versão é INÚTIL em campo (r2):
   240	   > o heredoc degradado embute `$TARGET`, `$PROFILE` e `$STACK` RESOLVIDOS
   241	   > (verificado em `_refresh_protocol_pointer`, ramo `*)`) — cada adotante
   242	   > tem um corpo degradado DIFERENTE, e um fingerprint fixo preservaria
   243	   > quase todos para sempre (AC-6b não cumprido).
   244	   >
   245	   > **A forma correta:** casar o corpo observado contra o ESQUELETO exato do
   246	   > template degradado (um por versão de framework que o produziu): extrair
   247	   > os campos variáveis das posições fixas, re-renderizar o template com os
   248	   > valores extraídos + `{{PROTOCOL_SOURCE}}` literal, e exigir
   249	   > **byte-igualdade** com o observado. Qualquer desvio ⇒ não-match ⇒
   250	   > **preservar**. Isso mantém a garantia do r1 (exatidão, fail-toward-
   251	   > preservation) sem a inutilidade do hash fixo. A semântica da célula D2
   252	   > (`live_content=degraded`) é determinada por essa reconstrução.
   253	
   254	3. **A FONTE DE VERDADE JÁ EXISTE — o debate a verificou ERRADO** (rail r1
   255	   P1, verificado literalmente; substitui o security must-fix 2 do round 1).
   256	   A "correção" do debate checou a chave errada: `request.PROTOCOL_SOURCE`
   257	   top-level de fato não existe, **mas o install PERSISTE o valor** —
   258	   `install.sh:2523` passa `"ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"` ao
   259	   state writer, que coleta todo `ph.*` em `request.placeholders` e faz
   260	   **UNION entre runs** (novo não-vazio sobrescreve; anterior permanece).
   350	| `.github/workflows/ownership-nightly.yml` (NOVO — rail r2 P2: todo `.github/workflows/*.yml` é sentinel-guarded; sem esta linha o inventário da cerimônia nasce incompleto) | 🔒 | W1 |
   351	| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
   352	| `scripts/tests/ownership_table.tsv` (célula nova D2 + coluna `exp_hash` do OWN-0074) | ✅ livre | W2 |
   353	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
   354	| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
   355	
   356	**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
   357	cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
   358	staged, o Owner assina uma vez.
   359	
   360	## 4. Critérios de aceite
   361	
   362	- [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
   363	- [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros — **JÁ ESTAVA** (`:15`, `:54`); o AC vira uma asserção de regressão, não trabalho.
   364	- [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
   365	- [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly** — exige CRIAR o job nightly (não existe `schedule:` hoje) e lembrar que `schedule:` ignora `paths:`.
   366	- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina. **O passo é o SCRIPT do §W1.4** (rc semântico + `HARNESS-ERR=0` exigido + diff de conjunto), nunca `--map`.
   367	- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico E com conteúdo certo** (token literal AUSENTE, fonte resolvida PRESENTE — rail r1 P1), com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
   368	- [ ] **AC-6b** Adotante com corpo DEGRADADO (fingerprint exato de corpo que o framework produziu — NUNCA substring; não-match preserva) é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
   369	- [ ] **AC-6c** O gerador consome `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — não criar campo novo), com fallback D3 declarado só para estados antigos/ausentes; verificar que o upgrade preserva `request.placeholders`.
   370	- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
   371	- [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
   372	- [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
   373	
   374	## 5. Regras do run (herdadas, custaram caro)
   375	
   376	1. **Nunca editar canônico na árvore viva.** Clone overlay; o clone precisa do
   377	   `git diff HEAD` aplicado se houver sujeira relevante.
   378	2. **Achado vira LINHA/ASSERÇÃO, nunca patch de ramo.**
   379	3. **Verifique cada instrução mecânica DESTE plano antes de executar** — no
   380	   PLAN-167, 4 instruções escritas de memória estavam erradas e uma delas
   381	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
   382	4. **Controle positivo obrigatório.** Verde sem controle não prova nada; 8
   383	   defeitos do PLAN-167 foram do INSTRUMENTO
   384	   ([[feedback-instrument-needs-same-scrutiny-as-subject]]).
   385	5. **Ordem das ondas é a mecânica que mais importa.** No PLAN-167, mudar o
   386	   gerador com 1 de 3 callers convertidos custou 24 regressões.
   387	6. **`git add` explícito, NUNCA `-A`** — a árvore carrega a cerimônia do
   388	   PLAN-166 suja.
   389	7. **Esperar por ARTEFATO, nunca por `pgrep`.**
   390	8. **Snippets POSIX** (`[[:space:]]`, nunca `\s` — BSD não suporta).
   391	9. Se um gate não fechar, o entregável é **RELATÓRIO**, não pack parcial.
   392	
   393	## 6. Riscos
   394	
   395	| Risco | Mitigação |
   396	|---|---|
   397	| e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
   398	| "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
   399	| Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
   400	| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: consumir `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — rail r2 P2 removeu a claim contrária, que era stale); fallback D3 só para estados antigos/ausentes |
   401	| Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
   402	| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
   403	
   404	## 7. Registro de execução
   405	
   406	<!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
   407	
   408	- **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
   409	  Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   410	  CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.

exec
/bin/zsh -lc "grep -nE 'exhaust|total|62|live_content|equival|legality|legal' docs/ownership-decision-table.md | head -100; sed -n '70,180p' docs/ownership-decision-table.md; sed -n '340,470p' docs/ownership-decision-table.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
18:>    the proposal is a `live_content` of `legacy_pristine_partial`, meaning a
51:| this document | defines the dimensions, the legality rules, and the reasoning |
52:| `scripts/tests/ownership_table.tsv` | **the truth** — one row per legal cell, with its expected verdict |
113:### 2.4 `live_content` — only defined when `live_type ∈ {dir, dir_empty, regular}`
250:A cell is **illegal** when the combination cannot occur against a real
258:| **R-02** | `operation ∈ {install_fresh, install_rerun}` ⇒ `skip_requested=none` | `--skip` is an `upgrade.sh` flag. `install.sh` has no equivalent (verified: zero occurrences). |
260:| **R-04** | `live_content=legacy_pristine` ⇒ `surface=spec` | The pristine fingerprints are a `SPEC/v1`-tree construct. No equivalent exists, or is needed, for a one-line marker or a generated pointer. |
261:| **R-05** | `live_type=absent` ⇒ `live_content` undefined | Nothing to hash. |
264:| **R-08** | `ceremony=user` ⇒ `surface ∈ {spec, protocol}` cannot yield `DELIVER` or `REFRESH` | WS4 guards forbid root surfaces under a user ceremony. **This prunes verdicts, not cells:** those surfaces still legally *appear* under `ceremony=user` as residue of a prior maintainer install, and those residue cells are exactly where two defects lived. |
266:| **R-10** | Rows are **equivalence classes**, not raw tuples; a dimension the row's outcome does not depend on is written `*` | Forced, not preferred. The raw product is ~24,000 tuples; at the mandated per-cell timeout the suite could not run in a day, so it would not be run — and an unrun suite is worse than a smaller honest one. `*` is the harness's instruction to instantiate the canonical representative, and any dimension that turns out to matter must be split into explicit rows. |
272:- `-` — not applicable under a rule above (e.g. `live_content` when the
292:  is the whole point. The cell is legal and important.
300:  `mode=copy ∧ prior_record=link` is a legal re-run after a mode change.
307:  review rounds — see §5.1. The cell is not illegal; it is **unguarded**, and
641:  too", that is a feature decision, and the pruned cells become legal.
644:  `legacy_pristine_partial` a real `live_content` value. Both were prose
| `marker` | `.claude/.framework-version` | a tracked single-line file |

The three differ in more than their path, and every difference has produced
at least one defect. `spec` is the only tree (so it is the only surface with
descendants, per-file records, and a "partially populated" state);
`protocol` is the only surface with no bytes in the source (so `source_has`
is meaningless for it, and its baseline digest comes from a *computed*
canonical hash); `marker` is the only surface inside `.claude/`, so it is
the only one both ceremonies receive.

### 2.2 `prior_record` — what the PRE-run baseline manifest says

| Value | Meaning |
|---|---|
| `none` | no record line for this relpath |
| `hash` | a `<64-hex>  <relpath>` record |
| `link_match` | a `LINK  <relpath>  <target>` record whose target equals the live `readlink` |
| `link_retargeted` | a `LINK` record whose target does **not** equal the live `readlink` |

This dimension describes the **previous** run's testimony, read before
anything is written this run. It is the operative meaning of "registered
delivery" in ADR-155-AMEND-1 §3.

### 2.3 `live_type` — `lstat` of the destination, never following

`absent` · `dir` · `dir_empty` · `regular` · `symlink` · `special`
(FIFO, socket, device) · `ancestor_symlink`.

`ancestor_symlink` is a value of this dimension rather than a tenth
dimension because the decision function short-circuits on it *before* it
ever looks at the leaf — exactly as it does for `special`. It answers the
same question ("what kind of destination is this?") with "one reachable only
by writing through a symlink out of the target tree".

`dir_empty` is split from `dir` because for `spec` it changes the *manifest*
outcome without changing the *filesystem* outcome — the enumeration walks
the target and emits a record per regular file, so an empty tree yields no
records at all even when every other signal says "owned".

`special` exists because two separate defects were `cp` invoked on a FIFO,
which blocks forever waiting for a writer and hangs the run **mid-upgrade**,
after earlier surfaces have already been modified.

### 2.4 `live_content` — only defined when `live_type ∈ {dir, dir_empty, regular}`

| Value | Meaning |
|---|---|
| `pristine` | byte-identical to what **this** source would deliver |
| `legacy_pristine` | matches a `SPEC/v1` fingerprint the framework shipped at v1.2.0 or earlier |
| `edited` | neither |

`legacy_pristine` exists because v1.2-and-earlier installs never enumerated
`SPEC/v1`, so no record can distinguish a framework-installed tree from an
adopter-authored one; the ambiguity is resolved by content against three
pinned fingerprints.

### 2.5 `source_has` — does `$SOURCE_DIR` carry this surface?

`yes` · `no`. The reachable `no` case is the documented `--pin` downgrade to
a pre-v1.3.0 tag, whose checkout has no marker. A `SPEC/v1` absent from
source means a broken or partial checkout.

### 2.6 `mode` — the delivery mode of **this** run

`copy` · `link`. On `install.sh` this is `--mode`. On `upgrade.sh` there is
no `--mode` flag: the value is *inferred* for the baseline rewrite, from a
prior `LINK` record first and a symlink probe second.

> **This dimension is about the current run, not the recorded one.** See
> pruning rule R-09 for why conflating them would delete a real defect.

### 2.7 `ceremony`

`user` · `maintainer` — the *effective* ceremony, read replay-independently
from `.claude/.install-state.json`, failing open to `maintainer` when the
state is absent (every pre-Wave-B install).

### 2.8 `operation`

`install_fresh` · `install_rerun` · `upgrade`. "Fresh" is defined
structurally: **no pre-existing baseline manifest at the target**.

### 2.9 `skip_requested`

`none` · `self` (`--skip SPEC/v1`) · `descendant`
(`--skip SPEC/v1/local.md`).

### 2.10 `fault` — the tenth dimension (ratified in round 1)

`none` · `backup_unwritable`.

An injected environmental failure. It is not a property of the target, which
is why it is not `live_type`; it is a genuine tenth axis, and it rode inside
the `note` column as a prose directive until the round-1 debate ruled that a
**dimension the harness parses out of prose is a dimension nothing
validates**.

Dropping those rows was the lower-friction alternative and was rejected:
they are the backup-failure *safety* cells, and a failed backup followed by a
delete is the data-loss path the whole backup-before-replace contract exists
to prevent. A column is cheap; a hole is not.

Consequently `note` now carries **prose only**. `indistinguishable=` and
`open=` survive as annotations because neither changes what the fixture does
or what the decision function returns.

## 3. The verdict enum (draft — W1 ratifies)

The outcome of a cell is a **pair**. Every defect found in the eleven review
rounds was a cell whose pair was wrong — which is the evidence that the pair
is the right shape for the answer.
rows where a surface is a symlink, that is not enough: a write that follows
the link lands **outside** the target, on adopter or system data, and the
target itself is unchanged. Such a row could report GREEN while the run
destroyed a file the test never looked at.

The fixture's foreign file is now a **tripwire**, digested before and after
every run. Any change to it produces status `ESCAPE`, which outranks the
verdict comparison entirely — a row whose pair matches while the run wrote
out of tree has not passed.

Arming it immediately converted a suspicion into evidence. `OWN-0034` — the
`protocol` surface as a leaf symlink — reports `ESCAPE`: `cat >` follows
the link and writes outside the target. `OWN-0044` (a `spec` symlink, which
is correctly preserved) does not, so the tripwire is not simply firing on
every symlink row.

That promotes the §5.1 finding. The missing leaf-symlink guard on the
pointer is not a hypothetical hardening gap; **it is a demonstrated
out-of-tree write**, which is the S238 class the whole baseline-manifest
design exists to close.

### 5.4c `prior_record` is ambiguous, and it matters exactly where it hurts

Running the decision function in shadow mode against the real callers — it
observes and records, it does not act — produced 17 agreements, 2
divergences and 10 rows the caller never reached. One divergence is a model
defect, not an implementation defect.

`prior_record` is defined as "what the pre-run baseline manifest says". There
are **two** such manifests and the definition does not choose between them:

- the **raw** file on disk, and
- the **sanitized** one the loader produces, which drops every record whose
  relpath traverses a symlinked component.

They agree everywhere except on the symlink-traversal rows — which are the
security-critical ones, and the same rows §5.8 is about. An observer reading
the sanitized manifest sees `none` and concludes `PRESERVE_UNOWNED`; an
observer reading the raw file sees `hash` and concludes `OMIT_RECORD`. Both
are defensible readings of a dimension that never said which it meant.

The resolution is not to pick the more convenient one. The **sanitized**
manifest is the authority, because honouring a record whose path crosses a
symlink is precisely what the ADR-155 decision-(v) provenance fence exists
to prevent — but the definition in §2.2 has to say so, and the harness has
to observe the same thing the caller does, or the two instruments will keep
disagreeing about cells neither of them is wrong about.

This is the kind of defect that survives eleven rounds of code review: every
branch reads *a* manifest, each reads a defensible one, and no branch is
individually wrong.

### 5.4d The missing cell was the most important one

The table had nine `protocol` rows and none for the combination that matters
most: an **adopter-customised pointer on a normal (maintainer) upgrade**.
`OWN-0072` covers the same content under `ceremony=user`; the ordinary path
was simply absent.

Deriving its expected pair exposed a **data-loss defect in the proposed
decision function**. For that cell the function returned `REFRESH` — it would
have overwritten a customised root `PROTOCOL.md`. That is the verified S238
loss that ADR-155 decision (iii) exists to close, and the live code has
preserved it correctly all along.

The asymmetry the function was missing is deliberate and is now stated in it:

| Surface | An adopter edit is… | Because |
|---|---|---|
| `SPEC/v1` | a **fork of the contract** → forced refresh | it is the published compliance contract (ADR-155-AMEND-1 §4) |
| `PROTOCOL.md` | **adopter content** → preserved | overwriting it is the verified S238 loss (ADR-155 (iii)) |

Both record a **canonical** digest regardless, because recording the
customised bytes would make the *next* upgrade read `H_dst == H_base` and
clobber them — the C.5 idempotency trap.

Two things are worth separating here. The defect was in the **new** code, not
the old: a refactor that had been driven only by "keep the map green" would
have shipped it, because **no existing row covered the cell**. What found it
was asking the completeness question — *which combinations does this surface
have, and is each one present?* — which is the one question a per-branch
review never asks.

### 5.4e Install and upgrade generate DIFFERENT pointers — every upgrade breaks it

Chasing a `HASH_UNCLASSIFIED` observation led to a defect in the live code
that has nothing to do with ownership records.

`install.sh` writes the root pointer and then **substitutes** its
placeholders, so the adopter gets a real path. `upgrade.sh` regenerates the
same file from a heredoc that leaves `{{PROTOCOL_SOURCE}}` **literal**, and
nothing substitutes it afterwards. Verified against the live tree:

| after | literal `{{PROTOCOL_SOURCE}}` occurrences |
|---|---:|
| `install.sh` | 0 — the file names the real checkout path |
| `upgrade.sh` | 4 — the file names a placeholder |

So **every upgrade degrades the pointer into a non-functional one** for any
adopter whose framework checkout lives outside the target. The file whose
entire job is to say where the protocol lives stops saying it.

This is the **install-set ≠ upgrade-set** class that ADR-155 decision (i) was
written to eliminate — the shared enumeration fixed *which paths* the two
sides touch, but not *what content* they produce for the same path. It is
pre-existing, unrelated to PLAN-167's changes, and no ownership assertion
would ever have caught it: the record is fine, the bytes are wrong.

It is recorded as **INV-4** because it is not a cell — it is a cross-writer
invariant.

### 5.5 Two findings are invariants, not cells

Two defects were about the **blast radius** of a fix rather than about any
one surface, and encoding them as rows would understate them. The harness
asserts them across every applicable row instead:

- **INV-1** — when ownership continuity fires on an install rerun, no
  enumerated path *outside* the continuity set may change its recorded
  digest. The original defect switched the whole tree's baseline to the
  unrendered source, which reads downstream as repo-wide adopter drift and
  silently stops those files from ever being refreshed again. One row could
  not have caught it; the damage was to the paths the row was not about.
- **INV-2** — `LINK` serialization may cover only paths that were already
  `LINK` records before the run. Otherwise an adopter's own symlink,
  preserved inside an enumerated directory, is promoted into a framework
  delivery record.
- **INV-4** — **install and upgrade must generate byte-identical content for
  the same surface.** Violated today by the root pointer (§5.4e): install
  substitutes its placeholders, upgrade does not. No per-cell ownership
  assertion can see this — the record is correct and the bytes are wrong —

exec
/bin/zsh -lc "grep -R -nE 'OWN-0024|OWN-0027|2 são defeito|dois.*TESTE|defeito do TESTE' .claude/plans/PLAN-167* .claude/plans/PLAN-168 docs scripts | head -120" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 239ms:
.claude/plans/PLAN-167/evidence/W2.3-FAILED-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2.3-FAILED-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_UNOWNED/HASH_NONE              rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W2-protocol-refactor-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2-protocol-refactor-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W2-shadow-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2-shadow-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W2.3-v2-map-54-8.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2.3-v2-map-54-8.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W2-shadow-divergence.txt:41:  OWN-0024  shadow line absent — caller path not reached
.claude/plans/PLAN-167/evidence/W2-post-refactor-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2-post-refactor-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W2-marker-refactor-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/evidence/W2-marker-refactor-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/evidence/W3-final-map-58-4.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_NONE              rc=0   r3-F1
.claude/plans/PLAN-167/evidence/W3-final-map-58-4.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_PRIOR_RECORD      rc=0   r4-F5
.claude/plans/PLAN-167/W2-STATUS-REPORT.md:63:`OWN-0024` aborts earlier under its injected fault, and `OWN-0025` is killed
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:46:   (OWN-0024, OWN-0027) would record `HASH_SOURCE` — the digest of bytes
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:137:   per-surface atomic for trees). The two fault rows (OWN-0024,
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:138:   OWN-0027) keep `HASH_PRIOR_RECORD` as the pinned observable. Lifting
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:57:2. **OWN-0024 and OWN-0027 are RED for a reason the plan does not address.** Running `test-ownership-table.sh --only OWN-0024,OWN-0027` produces `got=PRESERVE_OWNED/HASH_PRIOR_RECORD` for both, not `ABORT_SURFACE`. The `fault=backup_unwritable` injection makes `.claude.bak` unwritable (chmod 500, line 516-518). The scripts do emit the ABORT markers on the backup-failure path (upgrade.sh lines 1954-1955, 2059-2060), and the harness redirects stderr to `$out`. The RED result means the backup-failure path is not being reached — either the backup attempts a different directory, or the chmod 500 on `.claude.bak` does not prevent the actual backup path the scripts use. This is a fixture defect, not a subject defect: the fault injection is not injecting the fault. The plan does not document this specific RED cause, and it is distinct from the four documented fixture defects. It should be verified before W2 treats these rows as "code to fix" rather than "fixture to fix."
.claude/plans/PLAN-167/W4-approved-draft.md:77:| `OWN-0024` `OWN-0027` | the fault-injection fixture cannot distinguish "backup failed" from "the chmod never blocked the copy" | **instrument** |
.claude/plans/PLAN-167/rail/codex-r2.md:2963: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r2.md:2967: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r2.md:9827:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r2.md:9830:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r2.md:10516:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/rail/codex-r2.md:10519:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/rail/codex-r2.md:10563:  not decision cells, covered by the e2e: OWN-0024 OWN-0027 
.claude/plans/PLAN-167/rail/codex-r3.md:2599: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r3.md:2603: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r3.md:4660: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r3.md:4664: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r3.md:12484:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r3.md:12487:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r3.md:14273:   (OWN-0024, OWN-0027) would record `HASH_SOURCE` — the digest of bytes
.claude/plans/PLAN-167/rail/codex-r3.md:14364:   per-surface atomic for trees). The two fault rows (OWN-0024,
.claude/plans/PLAN-167/rail/codex-r3.md:14365:   OWN-0027) keep `HASH_PRIOR_RECORD` as the pinned observable. Lifting
.claude/plans/PLAN-167/rail/codex-r3.md:14830:2. **OWN-0024 and OWN-0027 are RED for a reason the plan does not address.** Running `test-ownership-table.sh --only OWN-0024,OWN-0027` produces `got=PRESERVE_OWNED/HASH_PRIOR_RECORD` for both, not `ABORT_SURFACE`. The `fault=backup_unwritable` injection makes `.claude.bak` unwritable (chmod 500, line 516-518). The scripts do emit the ABORT markers on the backup-failure path (upgrade.sh lines 1954-1955, 2059-2060), and the harness redirects stderr to `$out`. The RED result means the backup-failure path is not being reached — either the backup attempts a different directory, or the chmod 500 on `.claude.bak` does not prevent the actual backup path the scripts use. This is a fixture defect, not a subject defect: the fault injection is not injecting the fault. The plan does not document this specific RED cause, and it is distinct from the four documented fixture defects. It should be verified before W2 treats these rows as "code to fix" rather than "fixture to fix."
.claude/plans/PLAN-167/rail/codex-r3.md:15190:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/rail/codex-r3.md:15193:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/rail/codex-r3.md:24332: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r3.md:24336: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r3.md:24900:./.claude/plans/PLAN-167/debate/round-1/qa-architect.md:57:2. **OWN-0024 and OWN-0027 are RED for a reason the plan does not address.** Running `test-ownership-table.sh --only OWN-0024,OWN-0027` produces `got=PRESERVE_OWNED/HASH_PRIOR_RECORD` for both, not `ABORT_SURFACE`. The `fault=backup_unwritable` injection makes `.claude.bak` unwritable (chmod 500, line 516-518). The scripts do emit the ABORT markers on the backup-failure path (upgrade.sh lines 1954-1955, 2059-2060), and the harness redirects stderr to `$out`. The RED result means the backup-failure path is not being reached — either the backup attempts a different directory, or the chmod 500 on `.claude.bak` does not prevent the actual backup path the scripts use. This is a fixture defect, not a subject defect: the fault injection is not injecting the fault. The plan does not document this specific RED cause, and it is distinct from the four documented fixture defects. It should be verified before W2 treats these rows as "code to fix" rather than "fixture to fix."
.claude/plans/PLAN-167/rail/codex-r4.md:581: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r4.md:585: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r4.md:3159:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r4.md:3162:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r4.md:9227:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/rail/codex-r4.md:9229:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/rail/codex-r4.md:11104:   per-surface atomic for trees). The two fault rows (OWN-0024,
.claude/plans/PLAN-167/rail/codex-r4.md:11105:   OWN-0027) keep `HASH_PRIOR_RECORD` as the pinned observable. Lifting
.claude/plans/PLAN-167/rail/codex-r4.md:13585:33:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r4.md:14287:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r4.md:14290:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r1.md:5046:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r1.md:5049:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r1.md:6347:  not decision cells, covered by the e2e: OWN-0024 OWN-0027 
.claude/plans/PLAN-167/rail/codex-r1.md:6843: OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
.claude/plans/PLAN-167/rail/codex-r1.md:6847: OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
.claude/plans/PLAN-167/rail/codex-r1.md:8124:.claude/plans/PLAN-167/debate/round-1/qa-architect.md:57:2. **OWN-0024 and OWN-0027 are RED for a reason the plan does not address.** Running `test-ownership-table.sh --only OWN-0024,OWN-0027` produces `got=PRESERVE_OWNED/HASH_PRIOR_RECORD` for both, not `ABORT_SURFACE`. The `fault=backup_unwritable` injection makes `.claude.bak` unwritable (chmod 500, line 516-518). The scripts do emit the ABORT markers on the backup-failure path (upgrade.sh lines 1954-1955, 2059-2060), and the harness redirects stderr to `$out`. The RED result means the backup-failure path is not being reached — either the backup attempts a different directory, or the chmod 500 on `.claude.bak` does not prevent the actual backup path the scripts use. This is a fixture defect, not a subject defect: the fault injection is not injecting the fault. The plan does not document this specific RED cause, and it is distinct from the four documented fixture defects. It should be verified before W2 treats these rows as "code to fix" rather than "fixture to fix."
.claude/plans/PLAN-167/rail/codex-r1.md:9261:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
.claude/plans/PLAN-167/rail/codex-r1.md:9262:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
.claude/plans/PLAN-167/rail/codex-r1.md:10855:  If backing up a record-owned SPEC fails, `_SPEC_HASH_SOURCE` is still `HASH_SOURCE` from the unexecuted REFRESH verdict; setting only `_SPEC_DELIVERED=1` makes the manifest rewrite advance to source hashes although the target was untouched. This violates INV-3 and OWN-0024; the marker backup-failure branch at line 2099 has the same defect and must retain `HASH_PRIOR_RECORD` too.
.claude/plans/PLAN-167/rail/codex-r1.md:10882:  If backing up a record-owned SPEC fails, `_SPEC_HASH_SOURCE` is still `HASH_SOURCE` from the unexecuted REFRESH verdict; setting only `_SPEC_DELIVERED=1` makes the manifest rewrite advance to source hashes although the target was untouched. This violates INV-3 and OWN-0024; the marker backup-failure branch at line 2099 has the same defect and must retain `HASH_PRIOR_RECORD` too.
.claude/plans/PLAN-167-ownership-decision-table.md:534:  (`OWN-0024`/`OWN-0027` são células de EXECUÇÃO, cobertas pelo e2e)
.claude/plans/PLAN-168/debate/round-1/devops.md:53:  must extract only the RED cell IDs (OWN-0016, OWN-0024, OWN-0027, OWN-0074)
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:32:The plan section 0 states "2 sao defeito do TESTE" and later the ADR-190 content
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:64:{OWN-0016, OWN-0024, OWN-0027, OWN-0074} to {OWN-0016, OWN-0024, OWN-0027}.
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:71:the state AT LANDING: 3 known-open cells, 2 of which (OWN-0024/0027) are
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:95:### R-QA3 -- MEDIUM: OWN-0024/0027 assert an unverified safety property
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:97:The plan correctly characterises OWN-0024/0027 as fixture defects -- the
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:130:   specification must replace "2 sao defeito do TESTE" with the accurate split:
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:131:   OWN-0024/0027 are test-instrument defects; OWN-0074 is a product defect
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:133:   in W2 must explicitly reduce the expected red set to {OWN-0016, OWN-0024,
.claude/plans/PLAN-168/debate/round-1/qa-architect.md:134:   OWN-0027}. Without this correction, AC-5 blocks W2's first CI run after
.claude/plans/PLAN-168/rail/codex-r1.md:185:   124	- as 4 células conhecidas-abertas com causa, e que **2 são defeito do TESTE**.
scripts/tests/ownership_table.tsv:30:OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
scripts/tests/ownership_table.tsv:33:OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
scripts/tests/ownership-baseline-map.txt:29:OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_NONE              rc=0   r3-F1
scripts/tests/ownership-baseline-map.txt:32:OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=REFRESH         /HASH_PRIOR_RECORD      rc=0   r4-F5

exec
/bin/zsh -lc "sed -n '1,240p' .claude/plans/PLAN-168/debate/round-1/consensus.md; printf '\\n--- qa relevant ---\\n'; sed -n '85,150p' .claude/plans/PLAN-168/debate/round-1/qa-architect.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
---
plan: PLAN-168
round: 1
rounds_synthesized: [round-1]
agents_considered: [devops, qa-architect, security-engineer]
decisions_revised_in_plan:
  - "§0/§W1 — _hash_lib.sh JÁ estava nos filtros; 4 paths, não 5"
  - "§W1.3 — não existe trigger schedule:; AC-4 era insatisfazível"
  - "§W1.4 — AC-5 compara CONJUNTO DE IDs, não o arquivo (header tem paths de máquina)"
  - "§W2 — o fix não cura quem está em campo; falta reconhecedor de corpo legado"
  - "§W2 — PROTOCOL_SOURCE NÃO é persistido; o gerador não tem de onde ler"
  - "§0/§W3 — OWN-0074 é PRODUTO, não teste (minha classificação estava errada)"
synthesized_at: 2026-08-07T21:05:00Z
synthesized_by: CEO
---

# Round 1 consensus — PLAN-168

Três críticas, **três ADJUST, zero VETO**. Nenhum arquétipo rejeitou a forma
do plano; todos atacaram a mecânica — e **acertaram em tudo que verifiquei**.

Registrado como **design-coherent**. Não autoriza shipping: a cascata de
verificação (V2 rail, V3 GPG do Owner) é que autoriza.

## Consenso (2+ agentes)

**C1 — a mecânica do plano foi escrita de memória e está errada em pontos
verificáveis.** devops must-fix 2 e QA must-fix 1 são a mesma falha em lugares
diferentes. `_hash_lib.sh` JÁ estava nos dois filtros (`:15`, `:54`); o
`OWN-0074` NÃO é defeito de teste. **Ambos verificados literalmente antes de
aceitar.** É a lição
[[feedback-plan-mechanics-written-from-memory-fail]] se repetindo no plano
seguinte ao que a registrou.

**C2 — "descrever intenção não é gate".** QA must-fix 2 e devops must-fix 4
convergem: o AC-5 precisa do **script**, não do comportamento em prosa. E o
`diff` literal contra o baseline **falha sempre em CI**, porque o cabeçalho
carrega paths da máquina que o gerou.

## Insights de um agente, mantidos

1. **devops must-fix 1 — não existe trigger `schedule:`.** O AC-4 era
   insatisfazível. Pior: `schedule:` ignora `paths:`, então a divisão
   per-PR/nightly exige **dois jobs**, não duas linhas de filtro.
2. **security must-fix 1 — o fix não cura quem já está em campo.** Ponteiro com
   placeholder literal classifica `edited` ⇒ `PRESERVE_OWNED` ⇒ preservado
   para sempre. Cura: reconhecedor de corpo legado ⇒ REFRESH com backup, no
   molde do r20.
3. **security must-fix 2, CORRIGIDO E AGRAVADO na verificação.** A crítica
   dizia que o install grava `ph.PROTOCOL_SOURCE` em `:2523`. **Não grava** —
   `request.PROTOCOL_SOURCE` é `None` e a chave não existe. Logo o gerador
   compartilhado **não tem fonte de verdade**, e o W2 cresce: precisa
   PERSISTIR o valor, com fallback declarado.
4. **QA must-fix 1 — ordem W1/W2.** Se o gate do AC-5 landar antes do W2, a
   primeira CI depois do W2 falha por "o conjunto encolheu". O W2 tem de
   atualizar o conjunto esperado **no mesmo pack**.

## Rejeitados / adiados

- Nada foi rejeitado. Os 3 must-fix do security e os 4 do devops entraram; os
  2 do QA entraram.

## Ajustes no plano

§0 (tabela de evidência + linha nova do `OWN-0074`) · §W1.1 (4 paths + nota de
verificação) · §W1.2 (`--print-legacy-tag`) · §W1.3 (bloqueador do nightly) ·
§W1.4 (comparar conjunto de ids) · §W2.2-2.5 (cura, persistência, 3 caminhos
de teste) · §W3 (classificação correta) · AC-2/4/5/6/6b/6c · §6 riscos.

## Round verdict

**PROCEED** — o plano vai para `reviewed` com todos os must-fix aplicados.
Não há conflito entre críticas; todas as divergências foram entre um agente e
o plano, e cada uma resolveu por evidência literal.

--- qa relevant ---
expression then silently passes the gate. This is the "gate that never gates"
class the plan section 1 W1 item 3 correctly names for HARNESS-SKIP -- the
same class applies to --map misuse.

Required minimum: the CI step must (a) run the full harness WITHOUT --map,
(b) extract the set of RED cell IDs from the standard output lines, (c) compare
that set against the IDs recorded in ownership-baseline-map.txt, and (d) fail
(exit 1) if the two sets differ in either direction. The plan must supply this
implementation, not just describe the intent.

### R-QA3 -- MEDIUM: OWN-0024/0027 assert an unverified safety property

The plan correctly characterises OWN-0024/0027 as fixture defects -- the
chmod 000 "$T/$rel" approach may not simulate a backup failure the way the
spec expects (both cells show rc=0 with got=REFRESH, implying the backup step
either succeeded despite the chmod or silently continued after failure).

The concern is not about classifying them but about what the ADR-190 says.
ADR-190 must NOT state that backup-before-replace is enforced as of v1.3.0.
The safety property is aspirational until a green test proves it. A future plan
that repairs the fixture must simultaneously verify the production behaviour.

### R-QA4 -- LOW: scripts/_hash_lib.sh is already in both path filters

Verified: grep of .github/workflows/smoke-install.yml shows _hash_lib.sh at
lines 15 (pull_request filter) and 54 (push filter), added in PLAN-166. The
plan's W1 item 1 lists it as needing to be added. Adding it a second time is
harmless but creates spurious diff noise. The implementer should check before
editing.

### R-QA5 -- LOW: INV-4 test needs a non-substitution assertion

The plan requires W2 to produce "a test that installs, upgrades, and requires
the pointer to be byte-identical in both paths." Byte-identity is necessary but
not sufficient: a symmetric breakage where both paths produce the same wrong
output (both literal) would pass the equality check while the pointer remains
non-functional.

The existing probe (PLAN-167/evidence/probe-INV4-pointer-substitution.sh) already
asserts grep -c 'PROTOCOL_SOURCE' "$P" == 0 after each operation. The new test
must inherit this positive assertion.

## Must-fix (blocking)

1. Correct OWN-0074's classification. Plan section 0 and the ADR-190 content
   specification must replace "2 sao defeito do TESTE" with the accurate split:
   OWN-0024/0027 are test-instrument defects; OWN-0074 is a product defect
   caused by the INV-4 bug and will be resolved by W2. The baseline map update
   in W2 must explicitly reduce the expected red set to {OWN-0016, OWN-0024,
   OWN-0027}. Without this correction, AC-5 blocks W2's first CI run after
   W1 is landed.

2. Specify the AC-5 baseline-comparison implementation. W1 must deliver the
   exact nightly CI step body that: (a) runs the full harness without --map,
   (b) extracts the RED cell IDs from stdout, (c) compares the set against
   ownership-baseline-map.txt, and (d) fails on any set difference. Describing
   intent is not a gate; a script is.

## Nice-to-have (advisory)

1. INV-4 test: assert zero literal {{PROTOCOL_SOURCE}} in the pointer after both
   install and upgrade (not just byte-equality between the two). The existing
   probe's assertion is the right model.

2. Note in the W1 implementation runbook that _hash_lib.sh is already wired, so
   the implementer does not add a duplicate line.

exec
/bin/zsh -lc 'git diff --stat ec4bdcf -- .claude/plans/PLAN-168-ownership-followups-closure.md && git diff --unified=5 ec4bdcf -- .claude/plans/PLAN-168-ownership-followups-closure.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-n2WLH1H2' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-6NU49KQG' (errno=Operation not permitted)
 .../plans/PLAN-168-ownership-followups-closure.md  | 225 +++++++++++++++++----
 1 file changed, 191 insertions(+), 34 deletions(-)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-GSHVsUFu' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-CdkfyMbU' (errno=Operation not permitted)
diff --git a/.claude/plans/PLAN-168-ownership-followups-closure.md b/.claude/plans/PLAN-168-ownership-followups-closure.md
index ef9ae80..07fe767 100644
--- a/.claude/plans/PLAN-168-ownership-followups-closure.md
+++ b/.claude/plans/PLAN-168-ownership-followups-closure.md
@@ -24,11 +24,11 @@ tags: [ci, install, upgrade, adr, testing, canonical]
 
 | Item | Evidência existente |
 |---|---|
 | CI não dispara os oráculos | `grep -c` = 0 para os **4** paths novos em `smoke-install.yml` (o `_hash_lib.sh` JÁ está lá, `:15`/`:54`); codex rail r1/r2/r4 |
 | `fetch-depth: 1` não traz tags | `smoke-install.yml:101`; o harness precisa de `v1.2.0` para as linhas `legacy_pristine*` |
-| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — install=0 ocorrências literais, upgrade=4 |
+| INV-4: ponteiro degrada | sonda em `PLAN-167/evidence/probe-INV4-pointer-substitution.sh` — **evidência HISTÓRICA (pré-PLAN-167):** install=0 ocorrências literais, upgrade=4. **Na árvore landada a sonda dá 0/0** — o sintoma mudou de forma, ver §1 W2 (rail r1 P2) |
 | Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
 | **`OWN-0074` é PRODUTO, não teste** | debate r1 QA must-fix 1, verificado: registro=`hash(corpo com {{PROTOCOL_SOURCE}} literal)`, disco=`hash(corpo substituído)` ⇒ é a INV-4 no digest. **A classificação anterior ("2 são defeito do teste") estava ERRADA** e está corrigida aqui, na memória e no CLAUDE.md. |
 
 **Anti-objetivo:** não mexer na tabela de decisão nem nos vereditos. O
 PLAN-167 fechou aquilo com 58/62 e rail de 4 rodadas. Aqui só se fecha o
@@ -109,14 +109,19 @@ sobre propriedade, e vive só num `docs/`. Sem ADR, a próxima pessoa que
    > isso. Duas saídas: (a) dar ao harness um `--print-legacy-tag` e o YAML
    > consumir; (b) aceitar o hardcode e adicionar uma asserção que ele bata
    > com o valor embutido no harness. **(a) é o correto**; (b) só se o
    > orçamento apertar. Nunca deixar os dois divergirem em silêncio.
    ```yaml
+   # CORRIGIDO (rail r1 P2): o snippet consome a flag nova — NÃO hardcodar o
+   # tag no YAML (recriaria a divergência silenciosa que o parágrafo proíbe).
    - name: Fetch the legacy_pristine tag
      run: |
-       git fetch --no-tags --depth 1 origin +refs/tags/v1.2.0:refs/tags/v1.2.0
-       git rev-parse --verify refs/tags/v1.2.0
+       set -euo pipefail
+       TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
+       echo "legacy pristine tag: $TAG"
+       git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
+       git rev-parse --verify "refs/tags/$TAG^{commit}"
    ```
    **NÃO** adotar a alternativa "harness emite HARNESS-SKIP e sai 0" — suíte
    que fica verde pulando o que não consegue rodar é a classe de gate vacuoso
    (rejeitada no consenso do round 1 do PLAN-167).
 3. **Dois gates, dois tempos** — e isso exige **DOIS JOBS**, não duas
@@ -165,10 +170,51 @@ não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
 >
 > **QA must-fix 2: entregue o SCRIPT, não a intenção.** O passo de CI precisa
 > vir escrito no plano/pack — roda o harness, extrai os ids RED do stdout,
 > compara com `ownership-expected-reds.txt`, falha em qualquer diferença de
 > conjunto. Descrever o comportamento não é um gate.
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
+> # (rail r2 P1) status ≠ GREEN e ≠ RED — TIMEOUT/ESCAPE/AMBIG — NUNCA é
+> # aceitável: um id esperado-vermelho que degrada para TIMEOUT/ESCAPE mantém
+> # o CONJUNTO intacto e esconderia uma regressão PIOR atrás de "mesmo set".
+> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2!="GREEN" && $2!="RED"' \
+>   | grep . && { echo "::error::célula em status nunca-aceitável"; exit 1; }
+> # conjunto RED exato observado vs esperado — QUALQUER diferença falha
+> grep -E '^OWN-[0-9]+[[:space:]]' /tmp/own-map.txt | awk '$2=="RED" {print $1}' \
+>   | LC_ALL=C sort > /tmp/own-got.txt
+> grep -E '^OWN-' scripts/tests/ownership-expected-reds.txt | LC_ALL=C sort > /tmp/own-exp.txt
+> diff -u /tmp/own-exp.txt /tmp/own-got.txt \
+>   || { echo "::error::o CONJUNTO de nao-verdes mudou (inclusive se encolheu: verde-total = a tabela mudou)"; exit 1; }
+> # coerência rc↔conjunto: conjunto esperado não-vazio exige rc=1; vazio exige rc=0
+> if [ -s /tmp/own-exp.txt ] && [ "$rc" -ne 1 ]; then echo "::error::rc=$rc com vermelhos esperados"; exit 1; fi
+> if [ ! -s /tmp/own-exp.txt ] && [ "$rc" -ne 0 ]; then echo "::error::rc=$rc com conjunto esperado vazio"; exit 1; fi
+> echo "ownership nightly: conjunto de vermelhos estável"
+> ```
+> Controle natural embutido: extração vacuosa (grep que não casa nada) produz
+> conjunto vazio ≠ esperado ⇒ vermelho. NUNCA usar `--map` aqui.
+>
+> **Implementação entregue (W1):** o contrato acima vive em
+> `scripts/tests/ownership-nightly-gate.sh` (script chamado pelo workflow —
+> testável, diferente de YAML inline) com controle positivo
+> `scripts/tests/test-ownership-nightly-gate.sh`: **12 cenários de falha
+> plantados com harness fake**, incluindo os degrades TIMEOUT/ESCAPE/AMBIG
+> do rail r2.
 
 ### W2 — INV-4: install e upgrade geram o MESMO ponteiro (CANÔNICO)
 
 1. Decidir a direção **antes** de codar. Duas opções, e a escolha é do Owner:
    - **(a)** `upgrade.sh` passa a substituir os placeholders como o install faz;
@@ -182,36 +228,84 @@ não dispara); o job nightly roda o e2e e compara o conjunto de vermelhos.
    `PRESERVE_OWNED` e o ponteiro degradado é **preservado para sempre** —
    verificado em `upgrade.sh` no ramo `PRESERVE_OWNED`/`_lc = edited`.
    Pior: `doctor.sh` e `uninstall.sh` passam a tratar a **degradação do
    próprio framework** como customização do adotante.
 
-   **Cura:** reconhecedor de corpo legado — se o ponteiro contém o token
-   literal `{{PROTOCOL_SOURCE}}`, ele NÃO é customização, é lixo que o
-   framework produziu ⇒ `REFRESH` **com backup**. Há precedente exato: o
-   r20 usa fingerprints de conteúdo para migrar `SPEC/v1` legado
-   (`upgrade.sh` `_SPEC_PRISTINE_FINGERPRINTS`). Mesma forma, mesma
-   justificativa.
-
-3. **⚠️ NÃO EXISTE FONTE DE VERDADE PARA O GERADOR LER** (security must-fix 2,
-   **corrigido e agravado na verificação**). A crítica afirmou que o install
-   grava `ph.PROTOCOL_SOURCE` no install-state. **Não grava** — verificado:
-   `request.PROTOCOL_SOURCE` é `None` e a chave não existe em `request`. O
-   install RESOLVE o valor em tempo de instalação e escreve direto no corpo do
-   ponteiro; a **intenção nunca é persistida**.
-
-   Consequência: a opção (b) — gerador compartilhado — **não tem de onde ler o
-   valor certo**, e um upgrade rodado de outro checkout nomearia o
-   checkout-do-dia. Portanto o W2 **cresce**: é preciso PERSISTIR
-   `PROTOCOL_SOURCE` no install-state (campo novo), com fallback explícito
-   para instalações antigas que não o têm. **Decidir o fallback ANTES de
-   codar** — é a diferença entre curar e reescrever o ponteiro de todo mundo.
+   **Cura:** reconhecedor de corpo legado ⇒ `REFRESH` **com backup**.
+
+   > **⚠️ CORRIGIDO 2× (rail r1 P1 + r2 P1): o reconhecedor é por
+   > RECONSTRUÇÃO DE TEMPLATE, nunca substring E nunca hash estático.**
+   > Substring é destrutivo (um `PROTOCOL.md` do adotante que legitimamente
+   > CONTÉM o token seria força-refreshado — backup não desfaz a perda do
+   > arquivo ATIVO). Mas hash estático por versão é INÚTIL em campo (r2):
+   > o heredoc degradado embute `$TARGET`, `$PROFILE` e `$STACK` RESOLVIDOS
+   > (verificado em `_refresh_protocol_pointer`, ramo `*)`) — cada adotante
+   > tem um corpo degradado DIFERENTE, e um fingerprint fixo preservaria
+   > quase todos para sempre (AC-6b não cumprido).
+   >
+   > **A forma correta:** casar o corpo observado contra o ESQUELETO exato do
+   > template degradado (um por versão de framework que o produziu): extrair
+   > os campos variáveis das posições fixas, re-renderizar o template com os
+   > valores extraídos + `{{PROTOCOL_SOURCE}}` literal, e exigir
+   > **byte-igualdade** com o observado. Qualquer desvio ⇒ não-match ⇒
+   > **preservar**. Isso mantém a garantia do r1 (exatidão, fail-toward-
+   > preservation) sem a inutilidade do hash fixo. A semântica da célula D2
+   > (`live_content=degraded`) é determinada por essa reconstrução.
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
 
 4. **INV-4 vira asserção executável:** um teste que instala, faz upgrade e
    exige ponteiro **byte-idêntico**. Precisa cobrir três caminhos, não um
    (security must-fix 3): install→upgrade, **upgrade→upgrade** (idempotência),
-   e o **caminho de cura** (placeholder literal ⇒ REFRESH). Inputs
+   e o **caminho de cura** (corpo degradado ⇒ REFRESH). Inputs
    normalizados (`TARGET`/`PROFILE`/`STACK`/source) ou o teste vira flaky.
+
+   > **⚠️ BYTE-IDENTIDADE SOZINHA É VACUOSA (rail r1 P1).** Se o gerador
+   > compartilhado for acidentalmente baseado no heredoc QUEBRADO do upgrade
+   > atual, install e upgrade produzem o MESMO ponteiro errado: bytes
+   > idênticos, digest bate com o disco, classificação vira `pristine` e o
+   > `OWN-0074` fica verde — vacuosamente. O teste EXIGE, além da identidade,
+   > asserções de CONTEÚDO: `{{PROTOCOL_SOURCE}}` **ausente** e a fonte
+   > resolvida esperada **presente**, após install, upgrade E migração/cura.
+   >
+   > **⚠️ E o teste TEM de estar FIADO em CI (rail r2 P1)** — senão é a
+   > classe não-fiada que o W1 existe para fechar, recriada no mesmo pack.
+   > Fiação: step no `ownership-nightly.yml` (obrigatório) + o arquivo do
+   > teste nos DOIS path filters do `smoke-install.yml`; entrar também como
+   > step por-PR no job `smoke` SE a medição couber no teto de 25 min
+   > (medir, não chutar — o orçamento já subiu 4×).
+   >
+   > **⚠️ ALIASING DE HASH NO `OWN-0074` (rail r2 P1, verificado no
+   > harness).** Com o fix + fonte persistida, o digest prior (do install) e
+   > o canônico passam a ser OS MESMOS bytes; `_derive_hash_source` testa
+   > `c_prior` ANTES de `c_pointer` **por design documentado** ("the
+   > canonical name is then reached only when the two genuinely differ").
+   > Resultado: a célula reporta `HASH_PRIOR_RECORD`, a TSV espera
+   > `HASH_CANONICAL_POINTER`, e o `OWN-0074` ficaria vermelho MESMO CURADO.
+   > **O pack atualiza a coluna `exp_hash` do `OWN-0074` para
+   > `HASH_PRIOR_RECORD`** — o VEREDITO (`PRESERVE_OWNED`) fica intocado; a
+   > mudança de contrato observável é consequência necessária da cura (o
+   > gate W2 "0074 VERDE" já a implica). **Nuance de escopo do D2 a
+   > ratificar na assinatura:** D2 dizia "só adição"; esta é UMA edição de
+   > coluna de hash na célula que está sendo curada, com causa registrada.
 5. Reusar a sonda existente (`evidence/probe-INV4-pointer-substitution.sh`)
    como base; ela já reproduz o defeito.
 
 **Gate W2 (o anterior era vacuoso — este não):** o digest gravado para
 `PROTOCOL.md` **bate com os bytes no disco**, o ponteiro deixa de classificar
@@ -235,23 +329,29 @@ Registrar como contrato:
 - **INV-1..INV-4** (as quatro invariantes cross-surface);
 - a **assimetria deliberada** `SPEC/v1` (edição = fork ⇒ refresh) vs
   `PROTOCOL.md` (edição = conteúdo do adotante ⇒ preserve), com o motivo —
   é a que mais convida um "conserto" futuro;
 - que o `ADR-155-AMEND-1` é **emendado**, não revogado;
-- as 4 células conhecidas-abertas com causa, **corretamente classificadas**:
-  `OWN-0024`/`0027` = defeito do TESTE; `OWN-0016` e **`OWN-0074` = defeito de
-  PRODUTO** (o `0074` é a INV-4 se manifestando no digest — ver §W2).
+- as células conhecidas-abertas com causa, **corretamente classificadas E no
+  tempo certo (rail r1 P2 — o ADR nasce no MESMO pack que fecha o `0074`):**
+  abertas após este pack = `{OWN-0016, OWN-0024, OWN-0027}` (`0024`/`0027` =
+  defeito do TESTE; `0016` = PRODUTO); **`OWN-0074` entra como defeito de
+  PRODUTO FECHADO por este pack** (era a INV-4 se manifestando no digest —
+  ver §W2), registrado como histórico, não como aberto. Um ADR que listasse
+  4 abertas estaria stale no momento da criação.
 
 **Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
 novo muda a contagem — regenerar as superfícies derivadas).
 
 ## 3. Fronteira canônica
 
 | Superfície | Guard | Onda |
 |---|---|---|
 | `.github/workflows/smoke-install.yml` | 🔒 | W1 |
+| `.github/workflows/ownership-nightly.yml` (NOVO — rail r2 P2: todo `.github/workflows/*.yml` é sentinel-guarded; sem esta linha o inventário da cerimônia nasce incompleto) | 🔒 | W1 |
 | `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
+| `scripts/tests/ownership_table.tsv` (célula nova D2 + coluna `exp_hash` do OWN-0074) | ✅ livre | W2 |
 | `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
 | `scripts/tests/**`, `docs/**` | ✅ livre | todas |
 
 **As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
 cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
@@ -261,15 +361,15 @@ staged, o Owner assina uma vez.
 
 - [ ] **AC-1** PR tocando só `ownership_table.tsv` dispara `smoke-install`.
 - [ ] **AC-2** `scripts/_hash_lib.sh` está nos dois filtros — **JÁ ESTAVA** (`:15`, `:54`); o AC vira uma asserção de regressão, não trabalho.
 - [ ] **AC-3** O tag `v1.2.0` é buscado; as linhas `legacy_pristine*` rodam em CI (hoje dariam HARNESS-ERR).
 - [ ] **AC-4** Oráculo unitário roda **por-PR**; e2e roda **nightly** — exige CRIAR o job nightly (não existe `schedule:` hoje) e lembrar que `schedule:` ignora `paths:`.
-- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina.
-- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico**, com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
-- [ ] **AC-6b** Adotante com `{{PROTOCOL_SOURCE}}` literal é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
-- [ ] **AC-6c** `PROTOCOL_SOURCE` passa a ser persistido no install-state, com fallback declarado para instalações que não o têm.
-- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria e as 4 abertas.
+- [ ] **AC-5** O CI compara o CONJUNTO DE IDs (`ownership-expected-reds.txt`), nunca o arquivo de mapa inteiro — cujo cabeçalho tem paths de máquina. **O passo é o SCRIPT do §W1.4** (rc semântico + `HARNESS-ERR=0` exigido + diff de conjunto), nunca `--map`.
+- [ ] **AC-6** Install e upgrade produzem ponteiro **byte-idêntico E com conteúdo certo** (token literal AUSENTE, fonte resolvida PRESENTE — rail r1 P1), com teste cobrindo install→upgrade, upgrade→upgrade e o caminho de CURA.
+- [ ] **AC-6b** Adotante com corpo DEGRADADO (fingerprint exato de corpo que o framework produziu — NUNCA substring; não-match preserva) é CURADO (REFRESH com backup), não preservado — senão o defeito é imortal.
+- [ ] **AC-6c** O gerador consome `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — não criar campo novo), com fallback D3 declarado só para estados antigos/ausentes; verificar que o upgrade preserva `request.placeholders`.
+- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
 - [ ] **AC-8** Debate L3 com verdito registrado; rail codex encerrado por APPROVE, 2 rodadas limpas ou **teto de 3** — com motivo registrado.
 - [ ] **AC-9** Pack staged com manifesto RASTREADO, `shasum -c` rc=0 da RAIZ, `OWNER-LAND.sh` com espelhamento por TABELA e `--dry-run`.
 
 ## 5. Regras do run (herdadas, custaram caro)
 
@@ -295,17 +395,74 @@ staged, o Owner assina uma vez.
 | Risco | Mitigação |
 |---|---|
 | e2e estoura o teto de 25 min do job | é por isso que ele é nightly e o unitário é por-PR (AC-4) |
 | "consertar" os 4 vermelhos para o CI ficar verde | AC-5 falha se o conjunto MUDAR; os 2 de teste têm causa registrada |
 | Fix do ponteiro NÃO cura quem já está em campo (defeito imortal) | AC-6b: reconhecedor de corpo legado ⇒ REFRESH com backup, no molde do r20 |
-| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: persistir PROTOCOL_SOURCE; hoje a intenção do adotante NÃO é gravada |
+| Upgrade renomeia o ponteiro para o checkout-do-dia | AC-6c: consumir `request.placeholders.PROTOCOL_SOURCE` (JÁ persistido pelo install — rail r2 P2 removeu a claim contrária, que era stale); fallback D3 só para estados antigos/ausentes |
 | Digest canônico churna para todos os adotantes existentes | o corpo gerado MUDA ⇒ avaliar impacto em doctor/uninstall ANTES de landar |
 | ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |
 
 ## 7. Registro de execução
 
 <!-- o run anexa aqui: commit ativo, onda corrente, próxima ação concreta -->
 
 - **Estado inicial:** PLAN-167 landado em `7c0828a` (assinado, pushado).
   Mapa 58/62. Árvore ainda carrega a cerimônia do PLAN-166 suja (~34 arquivos).
   CI: "Translations drift" falha desde 04/08 — **pré-existente**, alheio.
-- **Próxima ação:** W1 item 1 (path filters), em clone overlay.
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
+- **Rail r2 CONSUMIDO:** 4 P1 + 2 P2, **6 aceitos / 0 refutados**
+  (`rail/codex-r2.md`), os dois claims não-triviais verificados literalmente:
+  o heredoc degradado EMBUTE `$TARGET/$PROFILE/$STACK` (fingerprint estático
+  seria inútil em campo ⇒ reconstrução de template), e a ordem
+  prior-antes-de-canonical do `_derive_hash_source` colapsa o nome quando a
+  cura aliasa os digests (⇒ pack atualiza `exp_hash` do OWN-0074 para
+  `HASH_PRIOR_RECORD`, veredito intocado — nuance do D2 a ratificar na
+  assinatura). Gate endurecido: conjunto RED exato + zero-tolerância a
+  TIMEOUT/ESCAPE/AMBIG. Fixes: §W1.4, §W2.2, §W2.4 (fiação CI do teste
+  INV-4 + aliasing), §3 (nightly no inventário), §6 (claim stale removida).
+- **W1 EXECUTADO no overlay `plan168-dev` (verificado, aguardando pack):**
+  4 paths nos dois filtros + step do oráculo unitário em `smoke-install.yml`;
+  `ownership-nightly.yml` novo (schedule 43 6 UTC + dispatch, gate via
+  script); harness ganhou `--print-legacy-tag` (fonte única do pin, literais
+  internos convertidos) e `--stable-header` (baseline commitável sem paths de
+  máquina); `ownership-expected-reds.txt` (4 ids; W2 encolhe p/ 3 no mesmo
+  pack); `ownership-nightly-gate.sh` + controle positivo **12/12**; YAML
+  válido; shellcheck limpo; oráculo unitário 60/60.
+- **Próxima ação:** rail r3 (teto AC-8) sobre o plano amendado → asserção
+  AC-2 em `test_release_workflow_asserts.py` → W2.

exec
/bin/zsh -lc "grep -nE 'OWN-0074|58/62|ownership' CLAUDE.md | head -50; grep -R -n 'feedback-plan-mechanics-written-from-memory-fail' . --exclude-dir=.git | head -20" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 831ms:
./.claude/plans/PLAN-168-ownership-followups-closure.md:102:   > [[feedback-plan-mechanics-written-from-memory-fail]]. **Abra o arquivo
./.claude/plans/PLAN-168-ownership-followups-closure.md:381:   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).
./.claude/plans/PLAN-168/debate/round-1/consensus.md:32:[[feedback-plan-mechanics-written-from-memory-fail]] se repetindo no plano
./.claude/plans/PLAN-168/rail/codex-r1.md:222:   161	   teria reaberto um P2 ([[feedback-plan-mechanics-written-from-memory-fail]]).

exec
/bin/zsh -lc "grep -n \"framework_manifest_set\\|_CANONICAL_GUARDS\" .claude/hooks/check_canonical_edit.py | head -30; nl -ba .claude/plans/PLAN-168-ownership-followups-closure.md | sed -n '342,358p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
115:_CANONICAL_GUARDS = [
199:    "scripts/_framework_manifest_set.sh",
788:# segments that every _CANONICAL_GUARDS entry starts with. Any path NOT
796:    # `_is_canonical` returns False BEFORE the new `_CANONICAL_GUARDS`
805:    # _CANONICAL_GUARDS without adding their first segments HERE would
892:_CANONICAL_GUARDS_FOLDED = [pat.lower() for pat in _CANONICAL_GUARDS]
914:    for pattern in _CANONICAL_GUARDS_FOLDED:
   342	**Gate W3:** `check-claude-md-claims.py` e `verify-counts.sh` verdes (o ADR
   343	novo muda a contagem — regenerar as superfícies derivadas).
   344	
   345	## 3. Fronteira canônica
   346	
   347	| Superfície | Guard | Onda |
   348	|---|---|---|
   349	| `.github/workflows/smoke-install.yml` | 🔒 | W1 |
   350	| `.github/workflows/ownership-nightly.yml` (NOVO — rail r2 P2: todo `.github/workflows/*.yml` é sentinel-guarded; sem esta linha o inventário da cerimônia nasce incompleto) | 🔒 | W1 |
   351	| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | W2 |
   352	| `scripts/tests/ownership_table.tsv` (célula nova D2 + coluna `exp_hash` do OWN-0074) | ✅ livre | W2 |
   353	| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
   354	| `scripts/tests/**`, `docs/**` | ✅ livre | todas |
   355	
   356	**As três ondas tocam superfície canônica** ⇒ o pack é **um só**, com uma
   357	cerimônia só. Desenvolver em clone overlay (padrão do PLAN-167), entregar
   358	staged, o Owner assina uma vez.

exec
/bin/zsh -lc "sed -n '105,220p' .claude/hooks/check_canonical_edit.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
# PLAN-019 Phase 2 Wave 2A (P1-SEC-A) expansion: full governance surface.
# Every path listed here is sentinel-gated (editable via Owner-signed
# sentinel). The arbitration-kernel subset (hook source files enforcing
# THIS guard, _lib/policy.py, _lib/redact.py, _lib/audit_emit.py, and
# .claude/policies/*.yaml) is ALSO covered by the stricter HARD-DENY
# hook `check_arbitration_kernel.py` — that hook has no sentinel escape
# and requires `CEO_KERNEL_OVERRIDE` with an audit-logged reason. The
# overlap is intentional defense-in-depth: if the arbitration hook is
# disabled by misconfiguration, this sentinel guard still blocks the
# edits (and vice versa).
_CANONICAL_GUARDS = [
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/pitfalls-catalog.yaml",
    # SKILL.md under any tier
    ".claude/skills/core/*/SKILL.md",
    ".claude/skills/frontend/*/SKILL.md",
    # PLAN-074 Wave 0 ADJ-A5: replace fixed 4-segment glob with
    # recursive ** to cover sub-namespaces (e.g. game-development/<engine>).
    ".claude/skills/domains/**/SKILL.md",
    # Domain-level governance files
    ".claude/skills/domains/*/team-personas.md",
    ".claude/skills/domains/*/pitfalls.yaml",
    # Sprint 9 (PLAN-009 A22 / A14) — defense-in-depth for confidence gate
    ".claude/**/conftest.py",
    ".claude/hooks/check_confidence_gate.py",
    ".claude/scripts/lessons.py",
    ".claude/scripts/prune-lessons.py",
    ".claude/scripts/lesson-restore.py",
    ".claude/scripts/lesson_ranker.py",
    # ---- PLAN-019 P1-SEC-A expansion: full governance surface ----
    # Hook source files (all PreToolUse / PostToolUse Python hooks).
    # An agent that can edit these can disable governance. Sentinel-gated
    # so Owner-signed ADRs can still land architectural changes.
    ".claude/hooks/*.py",
    ".claude/hooks/_python-hook.sh",
    # Hook shared library (_lib/*) — governance utilities.
    ".claude/hooks/_lib/*.py",
    ".claude/hooks/_lib/adapters/*.py",
    ".claude/hooks/_lib/**/*.py",
    # Policy-as-code (ADR-045) — policies + fixtures.
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    ".claude/policies/fixtures/*.jsonl",
    # PLAN-080 Phase 0b — JSON Schema for squad-bundle frontmatter validation
    # (M2-CDX-4 closure). Guarded so squad-bundle authoring contract cannot
    # be silently weakened. KERNEL-HARD-DENY since check_canonical_edit.py
    # itself is in _KERNEL_PATHS — extending its guard list requires both
    # CEO_KERNEL_OVERRIDE=PLAN-080-PHASE-0B-SCHEMA-GUARD-EXTENSION AND
    # CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT in addition to the sentinel.
    ".claude/policies/schemas/*.json",
    # PLAN-081 Phase 2 — Pair-Rail dispatcher canonical surface. The
    # routing-matrix.yaml carries the per-archetype coder/reviewer
    # decisions consumed by inject-agent-context.sh --pair-mode and
    # check_pair_rail.py (Phase 3 asymmetric VETO matrix arms). Mutation
    # of this YAML or the loader/predicate-eval would mis-route Pair-Rail
    # dispatches (T-4 archetype-spoofing in CROSS-LLM-THREAT-MODEL.md).
    # Sentinel-gated edits only — KERNEL-HARD-DENY since this guard list
    # itself is in _KERNEL_PATHS — extending requires
    # CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-2-DISPATCHER-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.
    ".claude/dispatcher/*.py",
    ".claude/dispatcher/*.yaml",
    ".claude/dispatcher/*.yml",
    ".claude/dispatcher/**/*.py",
    # Settings file — matcher/hook registration.
    ".claude/settings.json",
    # PLAN-074 Wave 0 ADJ-A3 BLOCKER 2: sub-agent definitions ship the
    # ROUTING TABLE personas + model: floor declarations. Editable only
    # via Owner-signed sentinel; CR/Sec/etc. archetype files cannot be
    # silently mutated by a sub-agent.
    ".claude/agents/*.md",
    # ADRs — architectural record, supersede/immutability discipline.
    ".claude/adr/ADR-*.md",
    ".claude/adr/README.md",
    # SPEC/v1 — published compliance contract.
    "SPEC/v1/*.md",
    "SPEC/**/*.md",
    # CI workflows — release / branch-protection / validation gates.
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    # CODEOWNERS — merge-side branch-protection gate.
    ".github/CODEOWNERS",
    # Installer + upgrader scripts — framework distribution surface.
    "scripts/install.sh",
    "scripts/install-npm.sh",
    "scripts/upgrade.sh",
    # PLAN-138 Wave C (ADR-155) — sourced helpers backing the install/upgrade
    # baseline-manifest engine. They are `source`d by the GPG-gated
    # install.sh/upgrade.sh, so mutating them silently changes the integrity
    # classification (FRAMEWORK-CHANGED vs ADOPTER-CUSTOMIZED) that protects
    # adopter customizations + the root PROTOCOL.md. Guarded so they are not a
    # soft underbelly relative to the scripts that source them.
    "scripts/_hash_lib.sh",
    "scripts/_framework_manifest_set.sh",
    # Root governance docs. PROTOCOL.md is rarely-changed governance;
    # CLAUDE.md is intentionally NOT guarded because it is edited every
    # session during closeout (see DYN-SEC1 dynamic finding). Protecting
    # CLAUDE.md needs a separate "session-closeout" ceremony convention
    # (tracked in dynamic-findings.md).
    "PROTOCOL.md",
    # PLAN-042 ITEM 6 (FINDING-14): spec.md is injected
    # verbatim into sub-agent prompts via `## SPEC CONTEXT`
    # (ADR-058). Guard prevents unauthorized spec edits from
    # becoming a prompt-injection vector across sub-agents.
    ".claude/plans/PLAN-*/spec.md",
    # PLAN-043 / ADR-064 — tier-policy artifacts
    ".claude/tier-policy.json",
    ".claude/tier-policy.json.sigchain",
    # PLAN-081 Phase 4-bis — Pair-Rail locked corpus governance per ADR-111.
    # The MANIFEST + each fixture file are SHA-pinned; mutation defeats the
    # cross-LLM disagreement signal (corpus immutability is a structural
    # defense per ADR-108 §Operational). Sentinel-gated edits only — KERNEL
    # HARD-DENY since this guard list itself is in _KERNEL_PATHS — extending
    # requires CEO_KERNEL_OVERRIDE=PLAN-081-PHASE-4-BIS-CORPUS-GUARD-EXTENSION
    # AND CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT.

exec
/bin/zsh -lc "find .claude/adr -maxdepth 1 -type f -name 'ADR-190*' -o -name 'ADR-189*'; python3 -c \"import os,re; ns=[int(m.group(1)) for f in os.listdir('.claude/adr') if (m:=re.match(r'ADR-(\\\\d+)',f))]; print(max(ns),len(set(ns)),len(ns))\"" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-GB8k7243' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-hZLsEfJg' (errno=Operation not permitted)
186 167 189

exec
/bin/zsh -lc "grep -R -nE 'ADR-18[7-9]|ADR-190' .claude/plans/*.md .claude/adr/README.md CLAUDE.md | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
.claude/plans/PLAN-167-ownership-decision-table.md:260:**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
.claude/plans/PLAN-167-ownership-decision-table.md:320:- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
.claude/plans/PLAN-167-ownership-decision-table.md:371:- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
.claude/plans/PLAN-167-ownership-decision-table.md:413:- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a
.claude/plans/PLAN-168-ownership-followups-closure.md:30:| Contrato sem ADR | `docs/ownership-decision-table.md` é o contrato de fato; o AC-10 do PLAN-167 pedia `ADR-190` e não foi cumprido |
.claude/plans/PLAN-168-ownership-followups-closure.md:320:### W3 — ADR-190 (CANÔNICO: `.claude/adr/`)
.claude/plans/PLAN-168-ownership-followups-closure.md:353:| `.claude/adr/ADR-190-*.md` | 🔒 | W3 |
.claude/plans/PLAN-168-ownership-followups-closure.md:370:- [ ] **AC-7** `ADR-190` registra dimensões, enum de 4, INV-1..4, a assimetria, as **3 abertas pós-pack** e o `OWN-0074` como fechado histórico.
.claude/plans/PLAN-168-ownership-followups-closure.md:402:| ADR-190 contradiz o ADR-155-AMEND-1 | §2 W3 exige "emendado, não revogado", com a assimetria explícita |

exec
/bin/zsh -lc "find .claude/adr -maxdepth 1 -type f -name 'ADR-18*.md' -print | sort" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
.claude/adr/ADR-181-claude-5-model-refresh.md
.claude/adr/ADR-182-codex-payload-pin-enforcement.md
.claude/adr/ADR-183-directory-added-notification-events.md
.claude/adr/ADR-185-night-mode-posture-toggle.md
.claude/adr/ADR-186-hook-deadline-policy.md

exec
/bin/zsh -lc "grep -R -nE 'ADR-187|ADR-188|ADR-189' . --exclude-dir=.git | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 1237ms:
exec
/bin/zsh -lc "find . -type f -name 'verify-counts.sh' -print" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo
 succeeded in 0ms:
./.claude/scripts/local/verify-counts.sh

codex
The plan omits a required sentinel-guarded implementation surface, lacks the rail artifacts it claims as consumed, and introduces another unwired control test. It would not provide the complete, auditable execution contract required for the canonical pack.

Full review comments:

- [P1] Add the shared helper to the signed boundary — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:351-351
  When W2 adds `live_content=degraded`, `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` must change because it currently recognizes only `pristine` and `legacy_pristine` as owned. That file is explicitly sentinel-guarded by `_CANONICAL_GUARDS`, but this boundary lists only `install.sh` and `upgrade.sh`, so the required edit can be omitted from the signed pack or blocked by the canonical-edit hook.

- [P1] Track the actual rail reviews before counting them — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:449-450
  When AC-8 is used to authorize the canonical pack, the claimed evidence is unavailable: the rail directory contains only `codex-r1.md`, and that file is the original misscoped inert-comment review with no findings; `codex-r0-misscoped.md` and `codex-r2.md` do not exist. Consequently the claimed 13 accepted findings and two consumed rounds cannot be audited or counted toward the rail ceiling until the actual transcripts are retained under the referenced names.

- [P1] Run the gate's positive control in pull-request CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:210-215
  When `ownership-nightly-gate.sh` changes, the new fake-harness control is only described as having run locally: the exact W1 filters omit both gate scripts, and neither W1 nor the acceptance criteria require executing `test-ownership-nightly-gate.sh` in a job. A PR can therefore break the rc/status handling while all PR checks pass, recreating the unwired-test defect this wave is intended to close; wire the fast control and its inputs into PR CI.

- [P2] Update the live_content contract for degraded — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:245-252
  When D2 introduces `degraded`, `docs/ownership-decision-table.md` §2.4 will still define the domain as only `pristine`, `legacy_pristine`, and `edited`, even though that document declares itself authoritative for dimensions and legality. No W2 step or acceptance criterion requires updating it, so implementing the plan as written leaves the documentation, TSV, and decision function disagreeing; require the contract update in the same pack.
The plan omits a required sentinel-guarded implementation surface, lacks the rail artifacts it claims as consumed, and introduces another unwired control test. It would not provide the complete, auditable execution contract required for the canonical pack.

Full review comments:

- [P1] Add the shared helper to the signed boundary — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:351-351
  When W2 adds `live_content=degraded`, `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` must change because it currently recognizes only `pristine` and `legacy_pristine` as owned. That file is explicitly sentinel-guarded by `_CANONICAL_GUARDS`, but this boundary lists only `install.sh` and `upgrade.sh`, so the required edit can be omitted from the signed pack or blocked by the canonical-edit hook.

- [P1] Track the actual rail reviews before counting them — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:449-450
  When AC-8 is used to authorize the canonical pack, the claimed evidence is unavailable: the rail directory contains only `codex-r1.md`, and that file is the original misscoped inert-comment review with no findings; `codex-r0-misscoped.md` and `codex-r2.md` do not exist. Consequently the claimed 13 accepted findings and two consumed rounds cannot be audited or counted toward the rail ceiling until the actual transcripts are retained under the referenced names.

- [P1] Run the gate's positive control in pull-request CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:210-215
  When `ownership-nightly-gate.sh` changes, the new fake-harness control is only described as having run locally: the exact W1 filters omit both gate scripts, and neither W1 nor the acceptance criteria require executing `test-ownership-nightly-gate.sh` in a job. A PR can therefore break the rc/status handling while all PR checks pass, recreating the unwired-test defect this wave is intended to close; wire the fast control and its inputs into PR CI.

- [P2] Update the live_content contract for degraded — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/619e7994-8171-4443-9eb3-66fb5368512f/scratchpad/plan168-rail/repo/.claude/plans/PLAN-168-ownership-followups-closure.md:245-252
  When D2 introduces `degraded`, `docs/ownership-decision-table.md` §2.4 will still define the domain as only `pristine`, `legacy_pristine`, and `edited`, even though that document declares itself authoritative for dimensions and legality. No W2 step or acceptance criterion requires updating it, so implementing the plan as written leaves the documentation, TSV, and decision function disagreeing; require the contract update in the same pack.
