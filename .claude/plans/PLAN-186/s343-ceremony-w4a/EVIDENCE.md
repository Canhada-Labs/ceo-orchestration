# EVIDENCE — wave-s343-w4a (PLAN-186 W4a)

> Todo número desta página foi PRODUZIDO por um comando registrado aqui, com
> o `rc`. Nenhum foi lembrado, e nenhum é fonte: a fonte dos valores que os
> gates comparam é `EXPECTED-BASELINE.txt`.
> Base de tudo: `76578f33eaa25a373643a96d7df908ebd3082408` (HEAD de `main` em
> 2026-09-03/04). Sombra: um `git worktree --detach` nesse HEAD.

## 1. O artefato revisado da S341 vs o HEAD de hoje

```
diff <(git show HEAD:.github/workflows/validate.yml) \
     .claude/plans/PLAN-186/w4/validate.deletion.yml.txt
```
→ **3 hunks**, não 2. Além das duas deleções de step, o `.txt` também:
(a) reescreve o comentário `:330-331`, que citava «Run Python script unit
tests» pelo NOME — um step que a própria deleção remove; e (b) acrescenta 7
linhas de comentário ao `env:` da matriz, declarando a perda aceita de
`CEO_HOOK_ADAPTER`.

**Decisão:** as duas são adotadas. (a) é obrigatória — sem ela o arquivo se
contradiz. (b) põe a perda declarada ONDE o próximo leitor procura. O `.txt`
NÃO está stale: ele descreve exatamente o HEAD de hoje mais essas três
mudanças.

A cópia MEASURE-ONLY (`validate.deletion.measure.yml.txt`) difere do `.txt`
acima só por uma branch descartável em `on.push.branches`; ela **não** entra:
as três corridas acontecem no `main`, sob sentinel.

## 2. A derivação, aplicada na sombra

```
python3 apply-w4a-validate-deletion.py --list-paths          rc=0  (2 paths)
python3 apply-w4a-validate-deletion.py --root <sombra> --check-only   rc=0
python3 apply-w4a-validate-deletion.py --root <sombra>       rc=0  (5 edições, 2 paths)
python3 apply-w4a-validate-deletion.py --root <sombra> --check-only   rc=1  ← RECUSA nomeada
```
A última linha é o controle de idempotência: re-aplicar sobre uma árvore já
patchada é RECUSA nomeada («a âncora aparece 0 vez(es), esperado 1»), nunca
um no-op silencioso.

```
git -C <sombra> diff --stat
 .github/workflows/smoke-install.yml | 36 +++++++++++++++++++++++++++++++++++-
 .github/workflows/validate.yml      | 33 +++++++------------------------
 2 files changed, 44 insertions(+), 25 deletions(-)

git -C <sombra> diff -U0 | grep -c '^@@'        → 5 hunks
```

**A sombra é BYTE-IDÊNTICA ao artefato revisado da S341:**
```
diff <sombra>/.github/workflows/validate.yml \
     .claude/plans/PLAN-186/w4/validate.deletion.yml.txt      rc=0  (IDENTICAL)
```

## 3. Cobertura — o oráculo que autoriza a deleção, re-derivado

Comando por raiz, na sombra (`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest
--collect-only -q -p no:cacheprovider`), rc=0 em todas as invocações; a
comparação é por CONJUNTO (sha256 dos 16 primeiros hex da lista ordenada):

```
[ALL]        |A|=7476 |B|=6122 |A&B|=0 |AuB|=13598 |M|=13598
             U-M=0 M-U=0 sha(U)=20b53de6c4565586 sha(M)=20b53de6c4565586 equal=True
[not_serial] |A|=6982 |B|=5670 |A&B|=0 |AuB|=12652 |M|=12652
             U-M=0 M-U=0 sha(U)=895a4eb102af57dd sha(M)=895a4eb102af57dd equal=True
[serial]     |A|=494  |B|=452  |A&B|=0 |AuB|=946   |M|=946
             U-M=0 M-U=0 sha(U)=98290245961e7285 sha(M)=98290245961e7285 equal=True
```
A = `.claude/hooks/tests/`; B = `.claude/scripts/tests/` +
`.claude/scripts/optimizer/tests/`; M = as três juntas (o que a matriz roda).

Os números da S341 eram 7 474 / 6 063 / 13 537 e serial 924. **A suíte
cresceu**; a propriedade continua valendo. É por isso que o V5 do LAND
RE-DERIVA em vez de citar.

### 3-b. Re-derivação no LAND real (S344, 2026-09-04 09:27, HEAD `449f157`) — ABORT no V5 e cura do baseline

O primeiro LAND real (dry-run e land; `land-w4a-20260904-092715-*.log` e
`land-w4a-20260904-092746-*.log`, preservados neste diretório) passou
G-PRE..G7, V1, V3 e V4 e **abortou no V5**. A propriedade CONTINUOU valendo
(união == matriz por conjunto, sha idêntico nos dois recortes); o que
divergiu foi a segunda perna do gate, a contagem DECLARADA:

```
[todos]  |A|=7476 |B|=6136 |A&B|=0 |AuB|=13612 |matriz|=13612   sha(U)=sha(M)=7c4578d943625a6a
[serial] |A|=494  |B|=452  |A&B|=0 |AuB|=946   |matriz|=946     sha(U)=sha(M)=98290245961e7285 (inalterado)
```

Declarado em `EXPECTED-BASELINE.txt`: B=6122, matriz=13598. Delta = **+14
node-ids em B**, atribuído pela fonte e não por palpite: `git diff --stat
76578f3..HEAD -- .claude/scripts/tests .claude/scripts/optimizer/tests`
devolve UM arquivo, `.claude/scripts/tests/test_ac14_classifier_check_rc.py`
(+644 linhas, commit `b53fec1`, AC-14), que coleta exatamente 14 node-ids e
0 seriais (`pytest --collect-only -q -p no:cacheprovider` sobre o arquivo,
em worktree destacado de `449f157`). Os materiais foram congelados em
`44c16f4` (01:32) e três lands livres da mesma noite (`685868a`, `b53fec1`,
`37fd85b`) vieram DEPOIS: o baseline envelheceu por construção e o gate fez o
que existe para fazer — parar em vez de relaxar.

Cura (S344, consciente, com fonte): `EXPECTED_NODEID_SCRIPTS` 6122 → 6136 e
`EXPECTED_NODEID_MATRIX` 13598 → 13612; `COMMIT-MSG-W4A.txt` e a tabela de
cobertura do sentinel-draft passam a citar os mesmos números (recorte
`not serial` MEDIDO no mesmo worktree, não subtraído: 6 982 / 5 684 / 12 666,
sha 829e9e817588bc10 nos dois lados); nada mais muda (A, serial, patch e
derivador intocados). O V5 foi replicado com o bloco Python do LAND, byte a byte, em
worktree destacado de `449f157` com os valores novos: rc=0, «a delecao NAO e
recusada por cobertura». A cura muda o HEAD e, com ele, o `Anchor-SHA`: o
sentinel volta ao draft e o Owner re-assina; a assinatura anterior (sobre
`449f157`) fica inválida por desenho (G1).

## 4. Lint e forma, na sombra

```
actionlint -shellcheck="-S error -e SC2002,SC2012,SC2016,SC2129" .github/workflows/*.yml   rc=0
python3 .claude/scripts/check-action-sha-drift.py --offline    rc=0
   → "format OK: 73 compliant SHA pin(s); network drift check skipped."
python3 -c "import yaml; ..."   (PyYAML 6.0.3 presente)
   validate.yml  : 7 jobs; job `validate` = 48 steps (HEAD: 50)
   smoke-install.yml : 1 job; job `smoke` timeout-minutes = 150 (HEAD: 126)
```
Nota honesta: a CI baixa `actionlint 1.7.7` PINADO por sha256; este número
veio do actionlint desta máquina. O gate local ANTECIPA o step da CI, não o
substitui.

## 5. Gates de corpus, na sombra (todos rc=0)

```
bash .claude/scripts/validate-governance.sh          rc=0   "Errors:   0"
python3 .claude/scripts/check_contamination.py       rc=0   "✓ No contamination outside allowed zones"
python3 .claude/scripts/check-claude-md-claims.py    rc=0
bash .claude/scripts/local/verify-counts.sh          rc=0   "(no drift detected — all doc counts match the live source)"
python3 scripts/build-plugin.py --check              rc=0
python3 .claude/scripts/check-test-env-hygiene.py    rc=0
python3 .claude/scripts/gen-command-skill-hook-map.py --check   rc=0
```

## 6. A suíte que LÊ os workflows vivos (conjunto DERIVADO, não lembrado)

```
grep -rn '\.github/workflows/validate\.yml\|\.github/workflows/smoke-install\.yml' \
     .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ tests/
```
Devolve 13 linhas em 12 arquivos; **nenhuma delas parseia os STEPS** — são
strings de path (testes de canonicidade, de classificação, de kernel) e um
único `read_text()` real (`test_release_bump_sites.py:1717`, que só afirma
ausência de `SOURCE_DATE_EPOCH`). Os 6 arquivos que tocam a superfície de
verdade rodaram na sombra:

```
pytest test_check_canonical_edit.py test_kernel_subsumes_security_critical_lib.py
       test_release_bump_sites.py test_check_active_hooks_executable.py
       test_validate_template_frozen_subset.py test_parity_source_resolution.py
   → 225 passed in 63.70s   rc=0
```

## 7. Censo derivado das duas superfícies que a wave apaga

```
grep -rn "Run Python hook unit tests\|Run Python script unit tests" . --exclude-dir=.git
```
Consumidores VIVOS: **zero**. Os acertos são (i) planos/debates/transcripts —
ledger, que descreve estados passados e não deve ser reescrito; (ii)
`.claude/plans/PLAN-169/staged-s318/validate.yml`, artefato CONGELADO de
evidência; (iii) `PLAN-183:1245-1246`, que registra que o TEMPLATE do adopter
já perdeu esses dois steps em `4f750f0` — nada a propagar.

```
grep -rn "timeout-minutes: 126" . --exclude-dir=.git
```
Consumidor VIVO: **um**, `.github/workflows/smoke-install.yml:296`. Os demais
são plano/doc/patch congelado descrevendo a derivação como ledger.

## 8. As sete amostras do bump (wall do JOB `smoke`)

`gh run list --workflow=smoke-install.yml` + `gh run view <id> --json jobs`,
`startedAt`→`completedAt` do job `smoke` (o `timeout-minutes` fecha o JOB; o
wall do RUN é 1–5 min maior e NÃO é o instrumento):

| run | sha | job `smoke` |
|---|---|---|
| 33809424817 | 35f33a8 | 92m32s |
| 33743649231 | ba15c71 | 90m40s |
| 33630753302 | 8efe09b | 77m53s |
| 33582381725 | f0e98de | 87m50s |
| 33503515412 | b7dad83 | 86m52s |
| 33388608651 | 826688f | 86m44s |
| 33364620284 | f348ee9 | 73m18s |

min 73m18s, max 92m32s. Isso é a FAIXA observada — não uma medida de
variância de runner: os sete runs têm cargas diferentes dentro dos mesmos
steps (achado P3 do rail r4, aceito). Margem em 126 = 33m28s (1,36×); em
150 = 57m28s (1,62×), ambas sobre o MÁXIMO observado. A memória da S336 registrava `b7dad83` como «1h32» —
esse número é o wall do RUN (91m56s); o JOB do mesmo run mede 86m52s. O
`1h32` real, como JOB, é o `33809424817` (92m32s).

## 9. Kernel, verificado ao vivo (não lembrado)

```
python3 -c "carrega check_arbitration_kernel.py; imprime _KERNEL_PATHS"
   .github/workflows/validate.yml       → in kernel? True
   .github/workflows/smoke-install.yml  → in kernel? False
```
Por isso o LAND arma `CEO_KERNEL_OVERRIDE`; e por isso o harness re-verifica
a pertinência AO VIVO (T20f): se o path sair do kernel, o override vira
cerimônia sem sujeito.

## 10. Canonicidade dos paths do pacote

```
python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>
  .github/workflows/validate.yml                              → 1
  .github/workflows/smoke-install.yml                         → 1
  .claude/plans/PLAN-186/w4/validate-deletion-RESULT.md       → 0   (o MEASURE escreve)
  .claude/plans/PLAN-186/s343-ceremony-w4a/DESIGN-W4A-S343.md → 0   (material livre)
```

## 11. Lint dos artefatos deste pacote

```
bash -n + shellcheck -S warning:
  finalize-w4a.sh            OK / OK
  test-ceremony-scripts-w4a.sh   OK / OK
  owner/OWNER-S343-W4A-SIGN.sh   OK / OK
  owner/OWNER-S343-W4A-LAND.sh   OK / OK
  owner/OWNER-S343-W4A-MEASURE.sh  OK / OK
py_compile apply-w4a-validate-deletion.py    rc=0
bijeção `_expect` (4 scripts × EXPECTED-BASELINE.txt): 36 chaves, ZERO lidas-e-não-declaradas, ZERO declaradas-e-não-lidas
```

## 12. O que NÃO foi medido, e por quê

- O `Validate` e o `Smoke Install` do CI: só rodam depois do push. O V-block
  ANTECIPA os gates que dá para antecipar (actionlint, sha-drift, governança,
  verify-counts); os outros são o próprio land.
- A suíte COMPLETA (~15,4k casos): a wave não toca código Python nem shell, e
  o conjunto que lê os workflows foi derivado por grep e rodado inteiro (§6).
- As 3 corridas de medição: são o `OWNER-S343-W4A-MEASURE.sh`, DEPOIS do land.

## 13. O que o rail achou (e o controle positivo de cada cura)

**r1 (patch, `codex exec review --uncommitted`, 5 826 linhas de saída bruta em
`evidence/rail-r1-raw.txt`) — 2 × P1:**

1. *Keep the moved test suites behind a required check* — o codex citou
   `docs/BRANCH-PROTECTION.md:101-105` por conta própria e chegou ao MESMO
   achado que o rail r24 da S340. **REAL.** Cura: o **G7** do LAND, que LÊ a
   config viva por `gh api` e PARA o land nos estados `window`/`unreadable`
   sem `CEO_W4A_REQUIRED_CHECK_ACK=I-ACCEPT`. Controle positivo: **T25** do
   harness roda o LAND sem o ack e exige vermelho com a razão nomeada; todos
   os outros casos passam o ack, para que cada um fique vermelho pelo SEU
   motivo.
2. *Attach signed sentinel evidence* — estrutural e esperado: o sentinel e o
   `.asc` vivem na árvore VIVA (materiais commitados ANTES do SIGN) e não
   podem existir na sombra por construção; o `finalize-w4a.sh` RECUSA
   qualquer path fora do EXPECTED. É o mesmo item que a r5 do `wave-fable51`
   registrou antes de um land real. A autorização é provada no G5 do LAND
   pela MESMA função do hook (`_sentinel_grants_path`).

**materiais r1 (gate `check-ceremony-script.py`, executado sobre a árvore de
harness com o pacote commitado) — 1 × BLOCKING real:**

- `[R8/BLOCKING] exec-bit no índice git (modo 100755)` nos 4 `.sh` do pacote.
  `blocking_unwaived = 4`, rc=1 — e o **V9a do próprio LAND** teria abortado.
  Os scripts do molde (`PLAN-169/...`) são `100644`; o `chmod +x` foi meu.
  Cura nos DOIS lados (CLAUDE.md §4: `git update-index --chmod=-x` sozinho não
  gruda): `chmod -x` no filesystem + `git add` de novo.
  **Controle positivo, em bytes:** antes `rc=1, blocking_unwaived=4`; depois
  `rc=0`, e `git ls-files --stage` mostra `100644` nos seis artefatos.

## 14. Rail r2 (prompt-only com contexto) — o que ele confirmou e o que achou

Comando: `codex exec review` com PROMPT (as duas formas são XOR com
`--uncommitted`). O prompt deu o contexto de cerimônia que a r1 não tinha, para
que o item estrutural do sentinel não consumisse a rodada.

**Confirmado por um segundo modelo, verbatim:** «The deleted test commands are
functionally covered by the matrix with equivalent paths, markers, flags,
working directory, and default Claude adapter behavior, and both YAML files
pass structural validation. The smoke timeout block records measurements
rather than predicting speed or duration…»

**[P2] REAL — comentários órfãos.** O E1 reconciliou UM comentário; o arquivo
tinha SETE. Censo mecânico, HEAD → pós-patch:

| literal | HEAD | pós-patch |
|---|---|---|
| `ALREADY collected by "Run Python script unit tests" below` | 1 | 0 |
| `step below runs the whole` | 1 | 0 |
| `is dir-collected above` | 1 | 0 |
| `` `serial` split above `` | 1 | 0 |
| `directory pins in the pytest steps` | 2 | 0 |
| `Step: Python hook unit tests` | 1 | 0 |
| `hook-tests-python-matrix` (contrapositivo) | 2 | **8** |

Cura: E6..E11 (5 → 11 edições no derivador). Gate: **V6c**, nas duas pernas.
Controle positivo: o mesmo censo contra HEAD acusa 7 sobras e `mencoes=2`;
contra a sombra, 0 e 8. Harness: **T26** planta
`EXPECTED_MATRIX_JOB_MENTIONS=42` e exige vermelho nomeado.

**Achado de auto-revisão, no mesmo passo.** A primeira pós-condição declarava
`hook-tests-python-matrix` × 7 — esqueceu a linha que DEFINE o job — e foi a
própria pós-condição que reprovou (`aparece 8 vez(es), esperado 7`). Isso
expôs que um refuse PÓS-escrita deixava a árvore mutada; o derivador ganhou
**rollback transacional** (guarda o original, restaura no refuse).

## 15. O patch final

```
sha256 : 66219c2b853b91d652ae7082bac7c5126926a650ed36b188f3a80f993f150f36
base   : 76578f33eaa25a373643a96d7df908ebd3082408
numstat: 35 1 .github/workflows/smoke-install.yml
         32 39 .github/workflows/validate.yml
hunks  : 11
git apply --check (árvore viva): rc=0
```

## 16. G7 — o gate medido contra a API VIVA

O `gh api repos/Canhada-Labs/ceo-orchestration/branches/main/protection/required_status_checks`
responde hoje `Branch not protected (HTTP 404)` ⇒ o G7 classifica
**`unprotected`** e o land segue com uma NOTA verdadeira: sem required checks,
não existe o «verde obrigatório enquanto a matriz está vermelha».

**Defeito que essa sonda encontrou no meu próprio gate:** num 404 o `gh` sai 1,
escreve a mensagem humana no **stderr** E o corpo JSON no **stdout**. A forma
`_rq_out="$(gh ... || printf '__GH_FAILED__')"` produzia
`{"message":…}__GH_FAILED__`, a comparação com a sentinela falhava e o gate
classificaria um 404 como janela ABERTA — pedindo reconhecimento com uma
explicação falsa. Curado lendo o **rc** numa variável própria. Controle
positivo: a lógica corrigida, replicada isolada contra a API viva, devolve
`unprotected`.

## 17. `finalize-w4a.sh` EXECUTADO (o buraco que o harness clonado tinha)

O harness do molde exercitava SIGN e LAND; o `finalize` — o PRIMEIRO comando
do fluxo do Owner — nunca era executado, só grepado (T20a/T20b). Corrigido por
execução real contra a árvore de harness com os materiais commitados:

```
CEO_W4A_SHADOW=<sombra> bash .../finalize-w4a.sh --no-commit     rc=0
```

Passos 0→6 verdes, incluindo 4a (reprodutibilidade byte a byte), 4b
(topologia), 4c (actionlint + pins), 4d (cobertura por CONJUNTO) e 4e
(não-vácuo com o ledger preservado). **O negativo forte:** o patch que o
`finalize_patch.py` gerou é BYTE-IDÊNTICO ao gerado à mão com
`git diff HEAD --binary` (`patch inalterado (66219c2b…)`), e o bloco `Scope:`
que ele DERIVOU de `git apply --numstat` é exatamente os dois paths do
sentinel. Duas rotas independentes, um artefato.

`Patch-base` foi re-escrito para o HEAD da árvore em que rodou — comportamento
correto: o commit dos materiais move o HEAD de propósito, e o SIGN valida
ancestralidade + ausência de drift, não igualdade. Nenhum editor abriu.

## 18. Rodadas de rail — resumo

| rodada | modo | achados | estado |
|---|---|---|---|
| r1 (patch) | `--uncommitted` | 2 × P1: required-check (REAL) + sentinel ausente (estrutural) | curado por G7 / explicado |
| r2 (patch) | prompt + contexto | 1 × P2: CLASSE dos comentários órfãos (REAL) | curado por E6..E11 + V6c |
| r3 (patch) | `--uncommitted` | 0 NOVOS; reabre o required-check | mesmo item, já sob gate |
| r4 (patch) | prompt + 4 fatos dados | 2 × P3 REAIS, ambos em texto que EU escrevi | curados em E7 e E5 |
| r5 (patch) | prompt + 5 fatos dados | 2 x P3 REAIS: lede contraditorio; npm packlist nao invoca pytest | curados no derivador |
| **r6 (patch)** | **prompt + 6 fatos dados** | **NENHUM — «No actionable issues found»** | **APPROVE** |
| materiais r4 | gates + harness x2 | 0 | APPROVE |
| materiais r1 | gates do pacote | 1 × BLOCKING: exec-bit no índice (REAL) | curado nos dois lados |
| materiais r2 | gates + varredura | 0 (2 falsos positivos nomeados) | APPROVE |
| materiais r3 | execução do finalize | 0 | APPROVE |

Confirmações que o rail trouxe, e que valem tanto quanto os achados: a
cobertura equivalente (paths, markers, flags, working directory, adapter
default) e o bloco do timeout «records measurements rather than predicting
speed or duration» — verbatim da r2.

## 19. Rail r4 — os dois P3 e o que eles custaram

**P3-1 (PyYAML).** O banner novo afirmava que os steps posteriores precisam de
«pytest/PyYAML». Medido antes de curar, sobre a árvore pós-patch: 25 steps
depois do install; **3** rodam pytest (teeth da PLAN-155 W6, raízes tests-01,
npm packlist gate); **0** raízes de teste posteriores importam `yaml`; os dois
`import yaml` diretos do job rodam ANTES do install. Cura: afirmar só o
medido (pytest) e **FLAGAR** a pergunta do PyYAML em vez de adivinhar —
remover o `pip install` seria mudança funcional fora de escopo, e
`tools/migrate-peers-yaml.py` (step posterior) não foi auditado.

**P3-2 (atribuição ao runner).** Eu escrevi «spread de 26 % sobre a MESMA
lista de steps» e concluí que «a variação de runner domina». O codex mostrou
que os sete runs têm CARGAS diferentes dentro dos mesmos steps (`826688f`
mexeu no `smoke-install.sh`; `ba15c71` no `doctor.sh` e na e2e de
write-safety). As amostras estabelecem a FAIXA, não a causa. **É a mesma
classe que esta wave existe para curar, cometida por mim no texto da cura.**
A conclusão foi reescrita no YAML **e** no sentinel, no DESIGN, neste EVIDENCE
e na mensagem de commit — consertar a tabela e deixar as conclusões erradas é
`feedback-reconcile-the-conclusions-not-just-the-table`.

Patch re-gerado após as curas da r4 e, depois, da r5: sha final
`35e26cdc47e606d1…` — 11 edições, 10 hunks no patch (11 sob `-U0`),
`83 insertions(+), 40 deletions(-)`, `actionlint` rc=0, menções à matriz = 8.

## 20. Rail r5 e r6 — as duas ultimas frases, e o fechamento

**r5 achou dois P3, os dois DENTRO das curas da r4** — o que e o argumento
mais forte a favor de rodar outra rodada depois de cada cura:

1. *Remaining runner attribution.* A r4 corrigiu o paragrafo da tabela e eu
   deixei o **lede** do mesmo bloco dizendo «the samples below say the RUNNER,
   not the step list, is what moves this job». O bloco se contradizia. E a
   MESMA classe que esta wave cura no `validate.yml`, cometida dentro da cura.
2. *npm packlist nao e consumidor de pytest.* Eu escrevi TRES steps
   posteriores rodando pytest. Medicao propria antes de aceitar: dos 3 steps
   cujo `run` contem a palavra, so **DOIS** invocam `python3 -m pytest`; o npm
   packlist gate usa o interpretador `python3`, nao o pacote pytest.

**r6 revisou exatamente a superficie corrigida** — com o pedido apontado para
as linhas de comentario acrescentadas, que e onde as quatro imprecisoes
apareceram — e devolveu: «No actionable issues found. The added and adjacent
comments are consistent with the workflow behavior and supplied facts, and
actionlint plus diff validation pass.»

### Patch final

```
sha256  : 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3
base    : 76578f33eaa25a373643a96d7df908ebd3082408
numstat : 42/1 .github/workflows/smoke-install.yml
          41/39 .github/workflows/validate.yml
hunks   : 10 no patch (11 sob `git diff -U0`)
git apply --check na arvore VIVA : rc=0
```

### Harness

`27/0/0` em **duas** execucoes consecutivas sobre os bytes finais (runs 4 e 5),
depois de `26/0/0` e `27/0/0` nas anteriores. Nenhum FAIL em nenhuma execucao.

---

## Rodada de rail do LAND dos materiais (S343, `rail-land-round-1.md`)

O pacote foi montado numa sombra e revisado la. Antes de commitar os materiais
LIVRES na arvore viva, uma rodada de `codex exec review --uncommitted` correu
sobre o INDEX completo do commit — a superficie que o Owner vai realmente ler.
Ela devolveu `REJECT` com **4 achados REAIS**, todos nos scripts de cerimonia e
nenhum no patch canonico nem no derivador (as 6 rodadas do patch seguem
descrevendo os bytes que serao aplicados; o `W4A.patch` nao mudou).

| # | Sev | Arquivo | Classe |
|---|-----|---------|--------|
| 1 | P1 | `OWNER-S343-W4A-MEASURE.sh` | baseline nao comparavel: os 3 ids abrangem TRES commits e o §6 do relatorio da S340 diz que eles «nao sao o baseline definitivo» |
| 2 | P1 | `OWNER-S343-W4A-LAND.sh` | um 404 GENERICO (autorizacao) era lido como «sem protecao», furando o `unreadable` fail-closed que o DESIGN declara |
| 3 | P2 | `OWNER-S343-W4A-MEASURE.sh` | selecao de run sem filtro de evento: fora do `push` a matriz abre 4 legs e a comparacao mede outra carga |
| 4 | P2 | `OWNER-S343-W4A-MEASURE.sh` | run com todos os jobs `skipped` (`CEO_SOTA_DISABLE=1`) conclui `success` e virava tabela com `n/d` |

As quatro curas estao descritas em `rail-land-round-1.md`. A mais cara e a
primeira: o `MEASURE` ganhou o gate `M0-d`, que mede o drift, o imprime e PARA
sem `CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT` — e carimba o reconhecimento no
proprio `RESULT`, para que a tabela nunca se leia como efeito isolado da
delecao.

### Controles positivos das curas

`rail-land-controls.sh` — **16 PASS / 0 FAIL**, rc 0. Cada caso EXTRAI o texto
embarcado do arquivo que sera assinado (funcao shell por `awk`; corpo de
`measure()` por `ast` sobre o heredoc) e o exercita com substitutos; nenhuma
regra e recopiada para dentro do controle. O caso do G7 mede a regra ANTIGA e a
NOVA sobre as MESMAS entradas e prova que elas divergem exatamente no 404 de
autorizacao — e concordam no corpo real de hoje, logo a cura nao muda o
presente.

### Rodada 2 do rail do land (`rail-land-round-2.md`)

A segunda passagem, ja com as quatro curas da r1 dentro, devolveu `REJECT` com
**4 achados NOVOS** — nenhum repetido. Dois deles sao a mesma classe que esta
wave existe para curar, agora dentro dos PROPRIOS materiais: (i) o G7 imprimia
uma remediacao que APAGARIA o `validate` e todo o resto dos required checks (o
`PATCH` trata `contexts` como a configuracao INTEIRA) — trocada pelo endpoint
ADITIVO; (ii) a secao «Como ler» do `RESULT` reintroduzia o claim causal que a
cura da r1 tinha acabado de carimbar contra, e o documento se contradizia. Os
outros dois: (iii) as 3 corridas podiam medir ARVORES diferentes se um commit
entrasse entre o land e a medicao — agora `HEAD` tem de ser o commit do land,
com ACK proprio; (iv) a garantia transacional do derivador nao cobria a
EXCECAO, so a pos-condicao — uma falha de escrita no segundo path deixava a
arvore meio-aplicada.

**O patch nao mudou:** a derivacao foi re-executada num worktree limpo em `HEAD`
depois da cura (iv) e o `git diff` continua byte-identico ao `W4A.patch`, mesmo
`sha256 35e26cd…`. O V3 do LAND segue valido.

Controles acumulados: `rail-land-controls.sh` **23 PASS / 0 FAIL**, rc 0 —
inclusive um caso que torna o segundo workflow NAO-ESCREVIVEL e prova que os
dois arquivos voltam aos bytes originais, com um controle RED independente
(variante pre-cura) que reproduz a arvore meio-aplicada.

### Rodada 3 do rail do land (`rail-land-round-3.md`) — e o teto

A terceira passagem devolveu `REJECT` com **5 achados NOVOS** (1 P1, 4 P2), de
novo nenhum repetido e nenhum no patch. O P1 e de PROVENIENCIA: um material de
cerimonia sujo (`EXPECTED-BASELINE.txt`, `COMMIT-MSG-W4A.txt`) era so um AVISO
no G0 — e e dele que saem TODOS os limiares do V-block, lidos da ARVORE DE
TRABALHO enquanto o `Anchor-SHA` amarra o COMMIT. Os quatro P2: o `--dry-run`
podia sair 0 sem ter restaurado (o bash preserva o status de entrada do trap
EXIT — sonda propria mede isso); o path cuja escrita FALHA nao era restaurado
(defeito DA CURA da rodada 2, achado que o proprio controle C7 reproduziu); a
rota limpa que o `M0-d` IMPRIME era inexequivel (baseline num sha unico ainda
exigia o ACK e carimbaria uma ressalva FALSA); e baseline sem `conclusion ==
success` entrava na tabela.

**Teto de 3 rodadas atingido.** As cinco curas tem controle positivo mas NAO
foram revisadas por uma 4a rodada — declarado, nao escondido. As tres rodadas
acharam 4, 4 e 5 defeitos: a curva nao estava caindo.

A primeira versao da cura do P1 pegava TODOS os materiais e derrubou 20 dos 27
casos do harness (o SIGN muta o sentinel na arvore de trabalho por desenho) — o
harness reprovou uma cura escrita minutos antes e disse por que. Escopo fixado
em ambas as direcoes pelos controles C10d-C10g.

Controles finais: `rail-land-controls.sh` **36 PASS / 0 FAIL**, rc 0.
Derivacao re-verificada DEPOIS da ultima cura, em worktree limpo no HEAD:
`--check-only` 11/2, apply rc 0, `git diff` byte-identico ao `W4A.patch`
(`sha256 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3`),
2a `--check-only` rc 1 (recusa nomeada de idempotencia).

### Harness apos as curas

`test-ceremony-scripts-w4a.sh` re-executado com os scripts JA curados (os
materiais entram no clone por copia da arvore viva, nao por `HEAD`), sob
`CEO_W4A_HARNESS_UNCOMMITTED=1`: **PASS=27 FAIL=0 SKIP=0**, rc 0 — inclusive o
`T24`, que faz o land COMPLETO e prova que o `.asc` entra no commit, e o `T25`,
que prova que o G7 ainda morde sem o reconhecimento. Nenhum caso regrediu com o
estreitamento do G7 nem com o gate `M0-d`.
