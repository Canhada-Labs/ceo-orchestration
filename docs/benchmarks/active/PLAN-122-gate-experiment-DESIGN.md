# PLAN-122 — Gate Experiment (adversarial) — DESIGN for approval (v2, panel-hardened)

> **Status: DESIGN ONLY — nothing executed, nothing committed.** This specifies the single
> decisive experiment that decides whether the "verified decomposition compiler" thesis
> (CEO-ORCHESTRATION-DOSSIER.md §9.6) is real or should be dropped for the governance/audit-only
> repositioning. **v2 folds a 4-LLM design review (ChatGPT, Claude, Gemini) — see §11.**
>
> Date: 2026-06-01. Owner approval required before Phase 0b (paid). Panel consensus: **GO 0a, HOLD 0b.**

---

## 0. The one question — and why it has TWO factors (panel fix #1)

> **Can a planner produce a DAG that *faithfully exposes* real coupling, AND can a cheap static
> checker REFUSE to fan out when the DAG is coupled — before spending tokens?**

The single most important correction from the review: the product is **planner + checker**, and
the headline number **decomposes**:

```
P(gate correctly refuses a coupled task) = P(planner EXPOSES the coupling in the DAG)
                                         × P(checker CATCHES exposed coupling)
```

A perfect checker on an **unfaithful DAG detects nothing**: if the planner declares two leaves
`allowed_files:[a.py]` / `[b.py]` because it *didn't realize* leaf A changes a helper's behavior
that B depends on, there is nothing in the DAG for `ast` to catch. **That** is the DafnyComp
wound (95.7% local / 3.69% compositional), and the original v1 design never measured it — v1's
Phase 0a could pass while the thesis was already dead. v2 measures both factors.

---

## 1. Four phases (cheapest kill first; arms de-confounded)

### Phase 0a-1 — FREE checker characterization (zero paid calls)
Build the static checker (§2) + a **large synthetic DAG corpus (≥60 contaminated + ≥60 clean)**
spanning the contamination families in §4, generated **blind** (§4). Measure the **confusion
matrix**, separating the two coupling classes:
- **Structural coupling** (write-set overlap, shared symbol def/use, shared global): checker is
  *expected to catch*. KILL if recall < 95% here.
- **Semantic/behavioral coupling** (disjoint files/symbols, runtime/behavioral dependency):
  checker is **expected to MISS** — pre-registered. The size of this miss **maps the checker's
  true scope** and is the honest deliverable, not a failure.
- Also measure **clean false-reject rate** (KILL if > 25% — a checker that rejects everything is
  useless: "the safest team is the one where nobody works").

### Phase 0a-2 — CHEAP planner-faithfulness probe (planning-only, ~$15-30)
Feed the **real planner** (Opus 4.8, planning-only, **no execution**) the contaminated WIDE
tasks (§4) and measure: **does the emitted DAG declare the hidden dependency?** This isolates
`P(planner exposes coupling)` — the factor v1 missed. KILL if the planner exposes the coupling
in < 70% of cases (a planner that hides coupling makes the checker irrelevant).

### Phase 0b — PAID execution, A vs B ONLY (panel fix: de-confound)
Run the **2-arm** paired experiment (A solo vs B compiler) on the frozen 24-task set with
objective test scoring + **hidden integration assertions** (§6). Arm C (cheap-model routing) is
**cut from this experiment** and deferred to Phase 0d. **CAP $250** (see §8 math), batch-staged,
auto-kill, HALT-file, resume by `(arm, task)`.

### Phase 0c — external-repo credibility (later, before any public claim)
Re-run ≥6 tasks on an external repo where the operator does **not** pre-know the coupling. Dogfood
ground-truth is a validity trap for public claims (§11). Not required to *kill*; required to *sell*.

### Phase 0d — Arm C (cheap-model leaves) — only if B proves out
The `cheap_model_safe` certificate is a **second hypothesis** (and S194 already returned NO on
naive routing). Test it only after the gate proves, to avoid entangling "decomposition works"
with "cheap routing works."

Reuses the WS-0b harness (`.claude/plans/PLAN-122/ws0b/`) + classifier-exp scaffolding.

---

## 2. The static independence checker (Phase 0a-1 deliverable) — with honest scope limits

**Input:** planner-emitted DAG (nodes: `{id, allowed_files[], read_only_files[], inputs[],
outputs[], acceptance_test, deps[]}`) + the repo. **Stack:** Python `ast` + import graph (stdlib).

**Checks it CAN do (structural):**
1. Write-set disjointness (parallel nodes sharing a path → REJECT).
2. Symbol def/use coupling via `ast` (A defines what B uses → must be an edge, else REJECT).
3. Shared mutable module-global written by >1 parallel node → REJECT.
4. Import/call-graph reachability between "parallel" file sets → REJECT (2nd opinion via an
   `import-linter`-style boundary contract).
5. Test scoping (a leaf's `acceptance_test` reaching outside its files → leak → REJECT).
6. Canonical guard (canonical paths → no auto-fan-out; PASS_THROUGH).
7. DAG hygiene: acyclicity, orphan, input arity, required params (PlanCompiler-style).

**Checks it CANNOT honestly do statically (panel fixes #10, #11 — stated, not hidden):**
- **#8 contract-chaining is downgraded to SCHEMA/TYPE level only.** Proving NL/dict outputs
  satisfy downstream preconditions is not statically decidable without a formal language (Dafny)
  or an LLM (which violates "before spending tokens"). Semantic contract-chaining is **deferred
  to test-gated integration** as the only real oracle.
- **AST blindspot:** `getattr`/`setattr`, decorator registration, subprocess, env-var mutation,
  shared fixtures, dynamic/string imports, config/schema coupling, shared DB rows — **invisible
  to `ast`.** These are the semantic-coupling class (§4b) the checker is pre-registered to MISS.

**Output:** `ACCEPT (fan out)` | `REJECT (replan DAG)` | `PASS_THROUGH (solo)` — the last two are
**measured separately** (panel fix #5: a checker that only ever REJECTs is useless).

---

## 3. The task set (24 tasks, pre-registered, blind-frozen before any run)

Stratified; candidates from this repo (ground truth known). **Finalize + sha-pin before 0b.**
- **8 WIDE** — genuinely independent (4 will be contaminated, §4): e.g. "add the missing
  fail-open regression test to hook `<X>`" for 4 independent hooks; refresh stale counts in 2
  independent docs; normalize frontmatter in 2 independent domain SKILL.md.
- **8 MIXED** — serial spine + parallel ribs: "add a param to a shared `_lib` helper THEN update
  N call sites"; "add an audit-action enum + wire K emit sites + SPEC row + registry SHA."
- **8 COUPLED** — should PASS_THROUGH: HMAC-chain field change; spawn-protocol/canonical change;
  diagnose+fix a failing integration test with unknown root cause.

Ground-truth labels: WIDE→ACCEPT, MIXED→ACCEPT-with-edges, COUPLED→PASS_THROUGH, contaminated
WIDE→REJECT/PASS_THROUGH.

---

## 4. Contamination — TWO classes, generated BLIND (panel fixes #2, #3, #13)

**4a. Structural (statically visible — checker SHOULD catch):** shared helper signature change;
shared enum/constant; file required outside `allowed_files`.

**4b. Semantic / behavioral (NO static signature — checker is pre-registered to MISS):** disjoint
files + disjoint symbols + no shared global, but leaf A changes the *behavior* of a same-file,
same-signature function (or a shared DB row / config value / ordering assumption / dynamic lookup)
that leaf B's correct output depends on. **This is the class that kills real systems and that
`ast` cannot see.** Pre-registered expectation: the checker MISSES these; the size of the miss is
the finding (it bounds the thesis).

**Diversity requirement** (≥10 families across the synthetic corpus): same-file overlap, shared
helper signature, shared enum/constant, imported-symbol changed, implicit registry coupling,
canonical touch, test leakage, read-only-actually-needed-for-write, dynamic/string import,
config/schema coupling.

**Blind generation (anti-vanity):** the contamination corpus + keys are generated by a
**decoupled session/third party**; the engineer authoring the checker rules must **not** see the
contamination vectors. Otherwise 0a-1 just proves "the team can solve its own riddle."

**N:** ≥60 contaminated synthetic DAGs in 0a-1 (statistical power lives here, free). The 4 real
contaminated WIDE in 0b are a **falsification probe, not statistics** (Wilson on 4/4 ≈ [0.51,1.0];
cannot distinguish a 90% from a 51% checker — so the real-task contamination only *demonstrates*,
the free corpus *measures*).

---

## 5. Arms (A vs B only in 0b; C deferred to 0d)

| Arm | Description |
|---|---|
| **A** | Raw Claude Code solo, strongest model (baseline) |
| **B** | Verified-decomposition-compiler: planner → static gate (§2) → parallel fan-out (scoped context + skill, **same model as A**) → test-gated integration → local replan on failure; **PASS_THROUGH to solo** when the gate says so |
| ~~C~~ | *Deferred to Phase 0d (cheap-model leaves) — second hypothesis, do not entangle* |

Same prompts, time budget, test harness, model. No manual steering except a predefined rescue policy.

---

## 6. Metrics (objective — tests + checker output, NO LLM judge)

**Headline (decomposed — panel fix #1):**
- `P(planner exposes coupling)` (from 0a-2) × `P(checker catches exposed coupling)` (from 0a-1,
  structural class). Report BOTH factors; the product is the real gate quality.

**Decision quality (the primary KPI — panel fix: decision > speedup):**
- Confusion matrix over `{ACCEPT, REJECT, PASS_THROUGH}` vs ground truth, with **asymmetric error
  accounting:**
  - **False orchestration** (coupled/contaminated → fan-out) = **P0** (corrupts output).
  - **False pass-through** (decomposable → solo) = opportunity loss only.
- **Useful-accept rate** on clean WIDE (must be high — else the gate is useless).
- **Correct edge-recovery** on MIXED (did it find the real dependency edges?).

**Composition (panel fix #3 — DafnyComp):** **hidden integration assertions** beyond per-leaf
tests. Track **local-leaf-pass-rate vs final-integration-pass-rate** — the gap IS the DafnyComp risk.

**Self-healing reality (panel fix #12):** fraction of integration failures resolved by **local
replan** vs requiring **full re-decomposition** (tests the §9.6 self-healing claim).

**Secondary (only if the gate works):** wall-clock per task **per stratum** (NOT a geomean
headline — panel fix #6: a 1:1:1 strata mix manufactures a portfolio number); cost multiple incl.
planner+retries+integration (settles [1.5×,8×]); governance false-positive rate `p_fp`
(tests the §9.5 `(1−p_fp)^W` claim); quality via repo tests + P0/P1 regressions.

---

## 7. Kill / Prove gates (asymmetric — panel fixes #3, #4, #6)

**KILL the speed thesis (→ governance-only) if any:**
- 0a-1: structural recall < 95%, OR clean false-reject > 25%.
- 0a-2: planner exposes coupling in < 70% of contaminated tasks.
- **Any semantic false-negative in 0b that produces a wrong integrated result** (near-zero
  tolerance; this is the catastrophic case, NOT a "20% tolerated" knob).
- **False-orchestration rate > 10%** (asymmetric: this corrupts output).
- Arm B slower than A on COUPLED tasks by > 10% (it should pass-through ≈ A).
- Local-leaf-pass high but final-integration-fail > 15% (the brick-perfect/house-collapses case).
- Cost multiple > 3× on accepted-DAG tasks with no speed win.

**WARN (narrow, don't kill):** false-pass-through > 25% (lost speedup, not corruption).

**PROVE (→ build the product) only if ALL:**
- Structural recall ≥ 95% (0a-1) AND planner-exposure ≥ 70% (0a-2).
- False-orchestration ≤ 10%; zero uncaught semantic FNs that corrupt output.
- WIDE-stratum: Arm B ≥ **2.5×** wall-clock vs A (lowered from 3× per the dossier's own
  1.5–3× honest band; report per-stratum, no geomean headline).
- MIXED/COUPLED: mostly correctly passed-through / edge-recovered.
- Quality non-inferior (B ≥ A − 5%, no P0/P1 regression); cost ≤ 2.5×; integration < 20%.

Between KILL and PROVE = **inconclusive → narrow, re-run, ship no claims.**

---

## 8. Cost, safety, provenance (panel fix #7 — the budget was broken)

v1's $120 over 24×3 arms ≈ $1.66/execution was unrunnable (Arm B ≈ $3–8/task). v2 fixes it by
**cutting Arm C** and **right-sizing the cap**:
- Realistic per-task: A ≈ $0.3–0.6; B (planner + 4–8 leaves + integration + retries) ≈ $3–8.
  24 × (A+B) ≈ **$85–215**. Plus 0a-2 planning-only ≈ $15–30.
- **HARD CAP $250**, **batch-staged** (run 6 tasks → checkpoint cost/signal → continue), auto-kill,
  HALT-file (`/tmp/gate-exp/HALT`) + `CEO_GATEEXP_RUN=halt`, resume by `(arm, task)`.
- 0a-1 is **free**; 0a-2 is **cheap** ($15–30, planning-only).
- Blind-frozen, sha-pinned manifest + sealed contamination key before 0b; advisory/untracked; off
  the live audit chain; objective scoring only, **no LLM judge anywhere**.

---

## 9. What each outcome means

- **0a-1 fails** (structural recall <95% or false-reject >25%) → checker not buildable → **$0
  reposition to governance-only.**
- **0a-2 fails** (planner hides coupling <70%) → the planner can't faithfully expose coupling →
  the whole compiler is moot → reposition. *(Panel's honest prediction: the semantic class (§4b)
  is where this most likely breaks.)*
- **0b KILL** → gate works structurally but real economics/composition fail → reposition; keep the
  checker as a governance lint.
- **0b PROVE** → build the product around the pass-through detector + auditable
  `orchestration_decision.md` + test-gated fan-out, honest per-stratum claims, then Phase 0c/0d.

---

## 10. Open decisions for the Owner (before Phase 0b)

1. **Budget:** confirm **$250** cap (panel rejected the $120 toy budget; Gemini argued $450 for a
   full matrix — v2 avoids that by cutting Arm C and putting statistical power in the FREE 0a-1
   corpus instead of paid tasks).
2. **Repo scope:** ceo-orchestration for the kill-probe (0b); external repo deferred to 0c for
   public credibility.
3. **Model:** Opus 4.8 for A and B (same model — isolate decomposition, not model tier).
4. **Blind freeze:** approve generating the 24-task list + contamination key in a **decoupled
   session** (checker author blind to vectors); I draft, a separate session injects + seals.
5. **Go/no-go:** authorize **Phase 0a-1 (free) + 0a-2 (~$15–30) now**; hold 0b for a second
   approval after seeing the two-factor numbers.

---

## 11. Panel design-review (round 2) — what changed and why

Four models reviewed v1. Consensus: **GO 0a, HOLD 0b.** The fixes folded into v2:
1. **Phase 0a now measures planner faithfulness, not just the checker** (Claude) — the single most
   important change; v1 could pass on a dead thesis.
2. **Two contamination classes; semantic/behavioral pre-registered as expected MISSES** (Claude,
   Gemini) — the `ast` checker structurally cannot see behavioral coupling; the miss is the finding.
3. **Synthetic N raised to ≥60; real 4 = falsification probe, not statistics** (ChatGPT, Claude).
4. **Asymmetric errors: false-orchestration (P0, KILL >10%) ≠ false-pass-through (WARN)** (ChatGPT, Claude).
5. **Added useful-accept-rate + REJECT-vs-PASS_THROUGH separation** (ChatGPT, Claude) — avoid the
   "rejects everything" degenerate.
6. **Dropped the geomean headline; per-stratum only** (Claude) — a 1:1:1 mix manufactures the number.
7. **Cut Arm C → Phase 0d; A-vs-B only** (ChatGPT, Claude) — don't entangle two hypotheses.
8. **Budget right-sized to $250 + batch staging** (Gemini) — v1's $120 was unrunnable.
9. **Check #8 downgraded to schema/type; semantic contract-chaining deferred to test-gate**
   (Gemini) — it is not statically decidable without Dafny/LLM.
10. **AST scope limits stated explicitly** (Gemini); **blind contamination generation** (Gemini,
    Claude) — anti-vanity; **external repo → Phase 0c** for credibility (ChatGPT, Claude).
11. **Local-replan resolution rate** added as a metric (Claude) — tests the §9.6 self-healing claim.

**Honest meta-finding:** every fix makes the experiment **cheaper to kill on and harder to fool
yourself with** — and several reviewers predict the hardened version (esp. fix #2, semantic
contamination) will **kill the speed thesis**, because behavioral coupling is exactly what an
`ast` checker cannot see and exactly what DafnyComp's 3.69% measures. That is the experiment
working as intended: a thesis that can only survive an easy test was never alive.
**Pitch hygiene reminder:** in any external doc, use "low-latency mechanical governance" (not
"near-free"), and ship **no speed number** until 0b measures one.
