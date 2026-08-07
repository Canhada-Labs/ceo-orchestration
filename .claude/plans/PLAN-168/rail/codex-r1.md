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
The only change adds an inert HTML comment to a Markdown planning document and does not affect code, tests, or documented behavior.
