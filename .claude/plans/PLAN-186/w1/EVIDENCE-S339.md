# PLAN-186 W1 — Evidência de execução (S339)

Todos os comandos abaixo foram rodados de fato nesta sessão. Sombra criada com
`git worktree add --detach <scratch>/shadow-w1 HEAD` a partir do commit
`8efe09b7484ffb9d25fa393df47a5c8002597bb1` (HEAD do repo no momento). Worktree
removido ao final (`git worktree remove --force`) — ver §6.

---

## 1. `--check` sobre a árvore VIVA (só leitura, nunca escreveu nada)

```
$ cd /Users/<user>/canhada-labs/ceo-orchestration
$ python3 .claude/plans/PLAN-186/w1/apply-w1-explicit-model.py --check --root .
CHECK OK — 10 anchor(s) verified across 4 file(s).
EXIT: 0
```

## 2. `--check` sobre a sombra, PRÉ-apply (idêntico à viva, mesmo HEAD)

```
CHECK OK — 10 anchor(s) verified across 4 file(s).
EXIT: 0
```

## 3. `--apply` sobre a sombra

```
$ python3 .claude/plans/PLAN-186/w1/apply-w1-explicit-model.py --apply --root "$SHADOW"
.claude/workflows/audit-fanout.js: 3 edit(s) applied
.claude/workflows/nightly-hygiene.js: 2 edit(s) applied
.claude/workflows/council-audit.js: 3 edit(s) applied
.claude/workflows/eval-baseline-n20.js: 2 edit(s) applied

10 edicoes em 4 arquivos
EXIT: 0
```

## 4. `node --check` (sintaxe) nos 4 arquivos pós-apply

```
$ node -v
v26.3.0
OK: .claude/workflows/audit-fanout.js
OK: .claude/workflows/nightly-hygiene.js
OK: .claude/workflows/council-audit.js
OK: .claude/workflows/eval-baseline-n20.js
```

## 5. `git diff --stat` na sombra pós-apply

```
 .claude/workflows/audit-fanout.js      | 6 +++---
 .claude/workflows/council-audit.js     | 6 +++---
 .claude/workflows/eval-baseline-n20.js | 4 ++--
 .claude/workflows/nightly-hygiene.js   | 4 ++--
 4 files changed, 10 insertions(+), 10 deletions(-)
```

10 linhas removidas / 10 adicionadas — exatamente 1 linha tocada por sítio
(o `opts` object de cada `agent()` call é de linha única em todos os 10 casos).

## 6. `--check` sobre a sombra PÓS-apply — relata ALREADY-APPLIED, ainda rc 0

```
ALREADY-APPLIED: .claude/workflows/audit-fanout.js :: "{ label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA, model: 'claude-sonnet-5' }"
ALREADY-APPLIED: .claude/workflows/audit-fanout.js :: "{ label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }"
ALREADY-APPLIED: .claude/workflows/audit-fanout.js :: "{ label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
ALREADY-APPLIED: .claude/workflows/nightly-hygiene.js :: "{ label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA, model: 'claude-sonnet-5' }"
ALREADY-APPLIED: .claude/workflows/nightly-hygiene.js :: "{ label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
ALREADY-APPLIED: .claude/workflows/council-audit.js :: "{ label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA, model: 'claude-sonnet-5' }"
ALREADY-APPLIED: .claude/workflows/council-audit.js :: "{ label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }"
ALREADY-APPLIED: .claude/workflows/council-audit.js :: "{ label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
ALREADY-APPLIED: .claude/workflows/eval-baseline-n20.js :: "{ label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA, model: 'claude-sonnet-5' }"
ALREADY-APPLIED: .claude/workflows/eval-baseline-n20.js :: "{ label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA, model: 'claude-fable-5-1' }"
CHECK OK — 10 anchor(s) verified across 4 file(s).
EXIT: 0
```

## 7. Guarda de dupla aplicação — `--apply` de novo na sombra JÁ APLICADA

```
$ python3 .claude/plans/PLAN-186/w1/apply-w1-explicit-model.py --apply --root "$SHADOW"
APPLY REFUSED — double-application guard: the following anchor(s) are
already in their NEW (model-explicit) form:
  - .claude/workflows/audit-fanout.js :: "{ label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA, model: 'claude-sonnet-5' }"
  - .claude/workflows/audit-fanout.js :: "{ label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }"
  - .claude/workflows/audit-fanout.js :: "{ label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
  - .claude/workflows/nightly-hygiene.js :: "{ label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA, model: 'claude-sonnet-5' }"
  - .claude/workflows/nightly-hygiene.js :: "{ label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
  - .claude/workflows/council-audit.js :: "{ label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA, model: 'claude-sonnet-5' }"
  - .claude/workflows/council-audit.js :: "{ label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA, model: 'claude-opus-5' }"
  - .claude/workflows/council-audit.js :: "{ label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }"
  - .claude/workflows/eval-baseline-n20.js :: "{ label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA, model: 'claude-sonnet-5' }"
  - .claude/workflows/eval-baseline-n20.js :: "{ label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA, model: 'claude-fable-5-1' }"
EXIT: 3
```

`git diff --stat` re-medido logo após a recusa continua idêntico ao §5 (10
inserções / 10 remoções) — a árvore não mudou com a tentativa recusada.

## 8. sha256 do patch candidato

```
$ git -C "$SHADOW" diff > w1-candidate.patch
$ shasum -a 256 w1-candidate.patch
b57cf0b8b34e07d884c44ed31a2ba80f1d97c815190f18fc80852bd1b40f52b1  w1-candidate.patch
```

`w1-candidate.patch` tem 106 linhas. **Este sha256 NÃO é o que uma cerimônia
real assinaria** — ver `DESIGN-W1-S339.md` §3: o LAND re-executa o derivador
contra o `ANCHOR_SHA` do dia e assina o que sair daquela execução. Este valor
prova só que, em `8efe09b`, o derivador produz um patch determinístico e
sintaticamente válido.

## 9. Patch completo (candidato, sombra, base `8efe09b`)

```diff
diff --git a/.claude/workflows/audit-fanout.js b/.claude/workflows/audit-fanout.js
index fbc06bc..7d297de 100644
--- a/.claude/workflows/audit-fanout.js
+++ b/.claude/workflows/audit-fanout.js
@@ -202,7 +202,7 @@ phase('Find')
 log(`audit-fanout: scope=${SCOPE} — ${DIMENSIONS.length} read-only finders in parallel`)
 
 const finderResults = await parallel(DIMENSIONS.map((d) => () =>
-  agent(assertDispatchable(finderPrompt(d), `find:${d.key}`), { label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA })
+  agent(assertDispatchable(finderPrompt(d), `find:${d.key}`), { label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA, model: 'claude-sonnet-5' })
     // agent() RESOLVES null on terminal API error (never rejects) — .catch alone
     // misses it and the reducer crashes on null.findings (PLAN-152 error-handling-03;
     // crashed real run wf_071ef6c5). Degrade to an empty-finder shard instead.
@@ -312,7 +312,7 @@ for (const dim of refuteDims) {
 }
 
 const refuteResults = await parallel(refuteDims.map((dim) => () =>
-  agent(assertDispatchable(refuterPrompt(dim, refuteFences[dim]), `refute:${dim}`), { label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA })
+  agent(assertDispatchable(refuterPrompt(dim, refuteFences[dim]), `refute:${dim}`), { label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA, model: 'claude-opus-5' })
     .catch((e) => ({
       verdicts: byDim[dim].map((f) => ({
         finding_id: f.finding_id, verdict: 'unverifiable',
@@ -381,7 +381,7 @@ Produce a markdown report:
 ## Unverifiable         (list, with why)
 ## Recommended next actions   (only from confirmed disposition=fix, ordered by risk_tags severity)
 Restructure only — invent NOTHING beyond the verdict rule above. Return ONLY {verdict, report}.`, 'synthesize'),
-  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA })
+  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' })
 
 // synth === null on terminal API error — degrade to a DEGRADED report carrying the
 // already-computed counts instead of crashing (PLAN-152 error-handling-03).
diff --git a/.claude/workflows/council-audit.js b/.claude/workflows/council-audit.js
index c0a1f1a..7b8ffc0 100644
--- a/.claude/workflows/council-audit.js
+++ b/.claude/workflows/council-audit.js
@@ -474,7 +474,7 @@ const laneThunks = REQUESTED_VENDORS.map((vendor) => () => {
   const prompt = vendor === 'claude'
     ? `You are the CLAUDE council lane (in-harness, ADR-136 confined). ${READ_ONLY_RULES}\n\n${PROMPT_DEFENSE}\n\n${FILE_ASSIGNMENT_BLOCK}\n\n${laneBrief('claude')}`
     : `${externalLaneOrchestration(vendor)}\n\n${EXTERNAL_LANE_RULES}\n\n${PROMPT_DEFENSE_EXTERNAL}\n\n${FILE_ASSIGNMENT_EXTERNAL}`
-  return agent(assertDispatchable(prompt, `lane:${vendor}`), { label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA })
+  return agent(assertDispatchable(prompt, `lane:${vendor}`), { label: `lane:${vendor}`, phase: 'Council', schema: LANE_SCHEMA, model: 'claude-sonnet-5' })
     .then((r) => r || { vendor, status: 'unavailable', unavailable_reason: 'agent resolved null (terminal API error/skip)', findings: [] })
     .catch((e) => ({ vendor, status: 'unavailable', unavailable_reason: String(e).slice(0, 160), findings: [] }))
 })
@@ -607,7 +607,7 @@ Return ONLY {verdicts} with exactly one verdict per key above.`
 if (groupsFence.truncated) log(`council-audit: verification ingest TRUNCATED at ${INGEST_CAP} chars — CLEAN is off the table (mechanical)`)
 
 const verdictWrap = groupList.length
-  ? await agent(assertDispatchable(refuterPrompt, 'verify'), { label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA })
+  ? await agent(assertDispatchable(refuterPrompt, 'verify'), { label: 'verify', phase: 'Verify', schema: VERDICT_SCHEMA, model: 'claude-opus-5' })
     .then((r) => r || { verdicts: [] }).catch(() => ({ verdicts: [] }))
   : { verdicts: [] }
 
@@ -706,7 +706,7 @@ Produce a markdown report:
 ## ⚠ Cross-vendor disagreements   (the findings ONE vendor caught and others missed — the council's headline signal)
 ## Advisory note   (this is ADVISORY evidence — it authorizes nothing; the verification cascade V0-V3 is unchanged)
 Return ONLY {verdict, report}.`, 'reduce'),
-  { label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA }).then((r) => r).catch(() => null)
+  { label: 'reduce', phase: 'Reduce', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' }).then((r) => r).catch(() => null)
 
 const synthSafe = synth || {
   verdict: 'DEGRADED',
diff --git a/.claude/workflows/eval-baseline-n20.js b/.claude/workflows/eval-baseline-n20.js
index 0bdaf35..8aa221d 100644
--- a/.claude/workflows/eval-baseline-n20.js
+++ b/.claude/workflows/eval-baseline-n20.js
@@ -384,7 +384,7 @@ phase('Eval')
 log(`eval-baseline-n20: model=${MODEL} run=${RUN} corpus=${CORPUS} — 4 batches x 5 tasks via claude -p subprocesses`)
 
 const batches = await parallel(BATCHES.map((ids, i) => () =>
-  agent(assertDispatchable(batchPrompt(ids), `eval:${MODEL}:batch${i + 1}`), { label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA })
+  agent(assertDispatchable(batchPrompt(ids), `eval:${MODEL}:batch${i + 1}`), { label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA, model: 'claude-sonnet-5' })
     // agent() RESOLVES null on terminal API error (never rejects) — .catch alone
     // misses it and the row loop crashes on null.rows (PLAN-152 error-handling-03;
     // crash class from run wf_071ef6c5). Degraded rows carry result_subtype=
@@ -475,7 +475,7 @@ Reconcile (W0b discipline — counts must close, never trust a single accounting
    whether the run is CLEAN (no anomalies, no missing transcripts, success_cells>=18) or VOID-SUSPECT
    (success_cells<18 → the effective N is too small to power even a KILL; flag it).
 Return ONLY the structured object.`, `eval:${MODEL}:reconcile`),
-  { label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA })
+  { label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA, model: 'claude-fable-5-1' })
 
 // recon === null on terminal API error — return a DEGRADED reconciliation instead
 // of silently dropping the accounting leg (PLAN-152 error-handling-03). The degraded
diff --git a/.claude/workflows/nightly-hygiene.js b/.claude/workflows/nightly-hygiene.js
index ed5afd2..e6faf57 100644
--- a/.claude/workflows/nightly-hygiene.js
+++ b/.claude/workflows/nightly-hygiene.js
@@ -273,7 +273,7 @@ phase('Sweep')
 log(`nightly-hygiene: ${DIMENSIONS.length} read-only dimension agents in parallel`)
 
 const dims = await parallel(DIMENSIONS.map((d) => () =>
-  agent(assertDispatchable(dimPrompt(d), `hygiene:${d.key}`), { label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA })
+  agent(assertDispatchable(dimPrompt(d), `hygiene:${d.key}`), { label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA, model: 'claude-sonnet-5' })
     // agent() RESOLVES null on terminal API error (never rejects) — .catch alone
     // misses it (PLAN-152 error-handling-03; crash class from run wf_071ef6c5).
     .then((r) => r || {
@@ -350,7 +350,7 @@ Report shape:
 ## Recommended next actions   (ordered, only for disposition=fix findings; cite finding ids)
 Overall = red if any dimension red, else yellow if any yellow, else green (skipped counts as yellow and must be called out).
 Do not invent findings; only restructure what the dimensions returned. Return ONLY the structured object.`, 'hygiene:synthesize'),
-  { label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA })
+  { label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'claude-fable-5-1' })
 
 // synth === null on terminal API error — degrade instead of crashing on
 // null.overall (PLAN-152 error-handling-03).
```

---

## 10. Codex P2 (review V2) — `--check` aceitava OLD+NEW coexistindo / NEW duplicado

Achado do Codex: em `apply-w1-explicit-model.py:162-171` (versão pré-fix), o
ramo `n_old == 0 and n_new >= 1` aceitava QUALQUER contagem ≥1 de NEW (uma
duplicata do anchor NEW passava sem aviso), e o ramo `elif n_old == 1: pass`
ignorava `n_new` por completo — uma árvore carregando o form OLD **e** o form
NEW ao mesmo tempo (drift ou aplicação parcial) lia como `CHECK OK`.

### 10.1 Reprodução do falso-verde (script BUGGY, backup pré-fix)

Duas sombras descartáveis (`git worktree add --detach`), cada uma com o patch
completo já aplicado (`--apply`, script buggy — a bifurcação problemática é só
em `check()`), depois mutadas à mão:

- **Caso A — NEW duplicado**: em `audit-fanout.js`, duplicada a ocorrência do
  anchor NEW do sítio `find:${d.key}` (inserida como comentário logo abaixo do
  original) → `OLD count=0, NEW count=2` nesse sítio.
- **Caso B — OLD+NEW coexistindo**: em `nightly-hygiene.js`, reintroduzida uma
  cópia do anchor OLD do sítio `hygiene:${d.key}` (comentário logo após a
  ocorrência já aplicada) → `OLD count=1, NEW count=1` nesse sítio.

Resultado do script BUGGY (`shasum -a 256` do backup:
`730d0b3ac9341ff6e9ba6504ffbc671d146b7cbdc99c75c8fec6a37be12700c4`):

```
=== BUGGY --check on Case A (NEW duplicated) ===
...
CHECK OK — 10 anchor(s) verified across 4 file(s).
EXIT: 0

=== BUGGY --check on Case B (OLD+NEW coexist) ===
...
CHECK OK — 10 anchor(s) verified across 4 file(s).
EXIT: 0
```

Caso B é o mais grave: o sítio mutado (`nightly-hygiene.js` `hygiene:${d.key}`)
nem aparece na lista `ALREADY-APPLIED` — o ramo `elif n_old == 1: pass` engole
o problema silenciosamente, sem imprimir nada. **Falso-verde REPRODUZIDO nos
dois casos**, `rc 0` em ambos.

### 10.2 Cura

`check()` reescrito: cada sítio precisa estar em EXATAMENTE um de dois estados
mutuamente exclusivos — `(n_old=1, n_new=0)` = pendente, ou `(n_old=0, n_new=1)`
= já aplicado. Qualquer outro par `(n_old, n_new)` — ambos zero, ambos não-zero,
ou qualquer contagem >1 — vira `CHECK FAILED` nomeado com as contagens exatas.
`apply()` não precisou de mudança: seu guard de dupla aplicação (`if new in
text: already.append(...)`) já recusava os dois casos ANTES de tocar qualquer
arquivo (`new in text` é verdadeiro tanto no Caso A quanto no B) — o bug era
exclusivo de `check()`.

### 10.3 Vermelho→verde com o script CORRIGIDO

```
=== FIXED --check on Case A (NEW duplicated) — expect CHECK FAILED ===
...
CHECK FAILED — 1 problem(s):
  - .claude/workflows/audit-fanout.js: anchor in an invalid state (OLD count=0, NEW count=2; ...)
EXIT: 1

=== FIXED --check on Case B (OLD+NEW coexist) — expect CHECK FAILED ===
...
CHECK FAILED — 1 problem(s):
  - .claude/workflows/nightly-hygiene.js: anchor in an invalid state (OLD count=1, NEW count=1; ...)
EXIT: 1
```

### 10.4 Os 4 checks pedidos pela tarefa

| # | comando | resultado | rc |
|---|---|---|---|
| 1 | `FIXED --check` no Caso A (NEW duplicado) | `CHECK FAILED` nomeando o sítio | 1 |
| 2 | `FIXED --check` no Caso B (OLD+NEW coexistindo) | `CHECK FAILED` nomeando o sítio | 1 |
| 3 | `FIXED --check` na árvore VIVA (nunca tocada) | `CHECK OK — 10 anchor(s) ... (10 pending, 0 already-applied)` | 0 |
| 4 | `FIXED --check` numa sombra LIMPA pós-`--apply` | `CHECK OK — 10 anchor(s) ... (0 pending, 10 already-applied)` com as 10 linhas `ALREADY-APPLIED` | 0 |

Sombra limpa também confirmou o fluxo completo: `--check` pré-apply (10
pending, rc0) → `--apply` (`10 edicoes em 4 arquivos`, rc0) → `--check`
pós-apply (10 already-applied, rc0). Os 5 worktrees descartáveis usados nesta
rodada (`shadow-w1-caseA`, `shadow-w1-caseB`, `shadow-w1-clean`, mais o
`shadow-w1` original da rodada anterior) foram todos removidos
(`git worktree remove --force`) — `git worktree list` ao final só mostra o
repo principal e worktrees de OUTRAS tarefas (`shadow-179fu`, `shadow-fable51`,
não tocados por esta sessão).

### 10.5 sha256 do script

```
$ shasum -a 256 apply-w1-explicit-model.py
2b61cffe96d4f4a9fe460b1cde5cf9f7d2c2adf77285d1b8da1d03a570c53c37  apply-w1-explicit-model.py
```

(sha256 anterior, pré-fix: `730d0b3ac9341ff6e9ba6504ffbc671d146b7cbdc99c75c8fec6a37be12700c4`
— preservado só no backup de scratch, não no repo.) O sha256 do PATCH candidato
em §8/§9 continua válido: `apply()` não mudou, e a árvore viva nunca teve o
patch aplicado nesta sessão.

---

## 11. Ambiente

- HEAD do repo no início desta tarefa: `8efe09b7484ffb9d25fa393df47a5c8002597bb1`
- Worktree sombra: `git worktree add --detach <scratch>/shadow-w1 HEAD`
- `node -v`: `v26.3.0`
- `python3` stdlib only, sem dependências de terceiros (`apply-w1-explicit-model.py`)
- Nenhum arquivo canônico foi editado na árvore viva. Nenhum commit foi feito.
