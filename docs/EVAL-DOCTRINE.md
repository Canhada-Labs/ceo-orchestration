# EVAL-DOCTRINE — how this framework runs paid behavioral evals

> **Status:** doctrine (advisory but binding on prereg authors). Written once
> (PLAN-135 W5 O6) so the methodology is not re-derived per pilot. Companion to
> the instrument READMEs (`.claude/plans/PLAN-135/instruments/README.md`,
> `.claude/plans/PLAN-134/w2/PREREG-W2.md`) and the frozen harness
> (`.claude/plans/PLAN-123/harness/`). When this doctrine and a frozen prereg
> conflict, the **frozen prereg wins for that run** (an amendment must be
> appended BEFORE spend); this doctrine governs the NEXT prereg.

This is the epistemic core of the paid-eval program. Every dollar we spend on a
behavioral eval buys a verdict, and a verdict is only worth its dollar if the
measurement was hermetic, the subject couldn't game it, the grading was
multi-signal, and the noise floor was respected. The single most expensive lesson
of the arc — `[[feedback-paid-run-reveals-billing-regime-bugs-mocks-cant]]`,
~$94 burned on bugs green mocks could not catch — is that **the instrument is the
experiment**. This doc is how we keep the instrument honest.

---

## 0. The two failure modes we are defending against

1. **Eval awareness / contamination** — the subject model behaves differently
   because it can tell it is being evaluated, or because it inherited the
   operator's settings/skills/memory/prior-results as a live context vector. A
   contaminated run produces a number that does not transfer to production.
2. **Noise mistaken for signal** — a wall-clock or pass-rate delta inside the
   measurement noise floor gets recorded as a WIN or a KILL. A KILL is a
   permanent decision in this program (we close the question and bank the
   negative); a KILL on noise is a false closure that costs us the real answer.

Doctrines 1-4 defend against (1). Doctrines 5-6 defend against (2). Doctrine 7
is the retroactive audit that proves we apply them.

---

## 1. Anti-eval-awareness — the subject must not know, and must not be able to peek

The subject is a SUBJECT. It runs in a sandbox that is, as far as it can observe,
a normal coding task — not a benchmark cell.

- **Subject CWD is OUTSIDE the repo.** The subject runs in a `/tmp` scratch
  workdir (`eval-baseline-n20.js` step 1; w0b spawns `claude -p` children whose
  cwd is the seeded scratch). It must NOT run with the repo as cwd — the repo
  tree contains the prereg, the kill criteria, prior result ledgers, and the
  word "benchmark" everywhere. A subject that can `grep KILL` the harness is
  eval-aware by construction.
- **Corpora are served from OUTSIDE `CLAUDE_PROJECT_DIR`.** The frozen task
  seeds are copied into the scratch dir (`cp -R "${CORPUS}/<ID>/seed/."
  "$SCRATCH"/`); the subject reads only that copy. It must NOT be handed a path
  that resolves back into `.claude/plans/PLAN-123/harness/freeze/` (where the
  check runner, the manifest, and the answer key live). The answer-key-leakage
  P0 class (Codex `019eb859`, W2) is exactly this: a scout/subject that can read
  the sibling `check.py` or a sibling artifact has the answer.
- **No Read path to the ledger or prior results.** PREREG clause: the subject
  must have no filesystem path (relative or absolute, no `..` escape) to the
  result directory, the reconciliation JSON, or any prior run. The card-grounding
  re-grep gate (W2 E5) and the `..`-rejecting path validators are the mechanical
  enforcement.
- **Self-identification probe.** After a run, scan the transcripts for evidence
  that the subject identified the task AS a benchmark — phrases like "this looks
  like a test/benchmark/eval", "the grader will check", "to pass this". A run
  whose transcripts show benchmark self-identification is **eval-aware → flag the
  cell VOID-SUSPECT**, do not silently score it. (This is a transcript post-scan,
  not a live gate — it cannot bias the run, only audit it.)

> Why this is hard and why we keep paying for it: hermeticity flags that work in
> a mock do nothing against a live subject. `--setting-sources ""` /
> `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` / scratch `CLAUDE_CONFIG_DIR` (the O5
> hermeticity set) only matter on the live paid call — which is why the doctrine
> requires a **live shakedown** before the full N (Doctrine 5, last bullet).

---

## 2. Hermeticity is mechanical, not aspirational

The flagship instrument's contamination vector is that children inherit the
operator's settings, skills, and memory unless told not to (HARVEST-REPORT O5:
"os filhos hoje carregam settings/skills/memória do operador — vetor vivo de
contaminação"). Each defense is a CLI flag or env var, and each maps to one PROBE
line in the instrument README so it is **asserted**, not assumed. **Flag names are
the ones VERIFIED against `claude --help` (CLI 2.1.177)** — the harvest text's
`--settingSources` / `--max-budgeted-usd` / `--max-turns` were WRONG (Doctrine 3 in
action; see `instruments/README.md` §2):

| Hermeticity property | Mechanism (CLI-verified) | Why |
|---|---|---|
| No operator config | `CLAUDE_CONFIG_DIR=<scratch>` (rm -rf after) | subject's `~/.claude` is a throwaway dir |
| No operator memory | `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` **set AFTER the `CLAUDE_CODE_*` unset** | the toggle is itself a `CLAUDE_CODE_*` var — the sanitizer would strip it; order is load-bearing |
| No operator settings/skills/memory | `--setting-sources ""` (`""` disables all of {user,project,local}) | the live contamination vector — children load nothing of the operator's |
| No operator tools | `--strict-mcp-config --mcp-config '{}'` | subject cannot reach MCP servers the operator has |
| No runaway loop | NO `--max-turns` flag on 2.1.177 — `claude -p` is structurally single-turn | a loop inflates wall-clock and cost, confounding the timing leg; the cap is satisfied by the `-p` substrate, not a flag |
| Mechanical budget ceiling | `--max-budget-usd <cap>` (only-works-with --print) | the prereg ceiling becomes a CLI kill, not a prompt honor-system |
| No banner/telemetry chrome (API-billed) | `--bare` when a key is in env | clean argv on the API path; OMITTED on the subscription substrate (it would also drop governance hooks) |
| Billing-env drift | drop every `CLAUDE_CODE_*` var (W0b amendment #3b) | billing-affecting env drift between terminals was a VOID suspect |

**Doctrine 3 sub-rule — verify the knob routes before relying on it.** A harvested
"flag" may not be a flag, or may be silently ignored by the installed CLI
(precedent: `probe_env_bundle.py` found 3 of 7 harvested "env keys" were actually
top-level settings keys; `CLAUDE_CODE_MAX_OUTPUT_TOKENS` was NOT honored by the CLI
in W3 pilot attempt 1, $19.95 ABORT). Before a flag is trusted in a paid run,
probe that it actually changes behavior. If the installed CLI rejects a flag, the
instrument records the cell `instrument_error` and STOPS the batch — a
half-hermetic run is VOID, never quietly degraded.

---

## 3. Budget-kill ≠ p_fail — the result-subtype taxonomy

A run can stop for reasons that are NOT a graded failure. Conflating them is a
grading confound (HARVEST-REPORT O5). The closed enum (`eval-baseline-n20.js`
`ROW_SCHEMA.result_subtype`):

| `result_subtype` | Meaning | Counts in pass@1 denominator? |
|---|---|---|
| `success` | model produced an answer; `pass` is the graded verdict | **Yes** (and `pass==false` here IS a real loss) |
| `error_max_budget` | `--max-budget-usd` tripped — **budget_kill** | **No** — VOID cell |
| `error_max_turns` | a turn cap tripped (reserved; no `--max-turns` flag on 2.1.177) | **No** — VOID cell |
| `error_other` | any other CLI error result subtype | **No** — VOID cell |
| `instrument_error` | harness step failed (timeout, missing result, flag-unsupported, batch-stop) | **No** — VOID cell |

`pass@1 = pass_count / success_cells`, **not** `/N`. A run that budget-killed 5
tasks is `15/15`, not `15/20`. The reconciler reports the subtype histogram
separately and flags `VOID-SUSPECT` when `success_cells < 18` (effective N too
small to power even a KILL). This is the same discipline as the W0b 4-VOID hunt:
a non-reconciling cell is removed from the science, never scored as a zero.

---

## 4. Cost is reconciled against the API, never derived alone

`[[feedback-paid-run-reveals-billing-regime-bugs-mocks-cant]]`: API cost is
ground truth; any derived cost is advisory. The W3 pilot lost ~$94 to billing-regime
bugs (mixed-TTL cache + quota→credits) that made derived ≠ API. Rules:

- **The API/CLI `total_cost_usd` (or per-model `modelUsage.costUSD`) is
  authoritative.** Derived token×rate math is a cross-check, reconciled within a
  2% tolerance; on drift the cell VOIDs (W0b) — it does not silently pick the
  cheaper number.
- **Subagent accounting via `modelUsage`, not top-level `usage`** (W0b amendment
  #2 — top-level usage covers only the main thread; `total_cost_usd` also bills
  subagent threads).
- **Never discard experimental data to make the books balance.** The W3 lesson:
  18 reconciliation-VOID rows were dropped and the run came out BIASED. The fix
  was API-cost-authoritative + reconciliation-advisory, keeping every cell.
- **Smoke-pay 1-2 tasks before the full N.** The live shakedown (Doctrine 5) is
  also the billing-regime smoke test — it surfaces the cache-TTL / quota-bucket
  bug class for ~$5 instead of ~$74.

---

## 5. Grading: a mix of signals, partial credit, read-N-transcripts-per-verdict

A single grader is a single point of failure, and a binary check throws away
information. The doctrine:

- **Grader mix.** Combine an objective deterministic check (the frozen
  `check_runner.py`, exit 0 = pass — the primary, no LLM judge) with, where the
  task admits it, a secondary signal (a cross-model blind reviewer, e.g. the
  Codex pair-rail; a claim-grounding re-grep). The W2 Contraprova KILL on
  criterion (iii) is the canonical use: marginal catch is scored *over* {V1
  deterministic + Codex}, so a "catch" already found by a cheaper signal does not
  count.
- **Partial credit where the task is decomposable.** Prefer a graded score
  (criteria-met / criteria-total, per `user.define_outcome` rubric style) over a
  raw boolean when the artifact has independently-checkable parts — vague rubrics
  ("data looks good") produce noisy loops; explicit per-criterion rubrics
  ("CSV has a numeric `price` column") grade cleanly. The binary `pass` stays the
  headline for KILL/WIN power; partial credit is the diagnostic.
- **Read N transcripts per verdict.** A verdict is not the aggregate number alone
  — before recording WIN/KILL, read at least a sample of the actual transcripts
  (and ALL of them on a small-N pilot) to confirm the cells are what the number
  claims: no answer-key leakage, no benchmark self-identification, no
  instrument_error miscoded as a loss. The S229 lesson is that 9 instrument P0s
  survived green mocks — the transcripts, not the summary, are where they show.
- **AI-resistant authorship.** Where the grader or the falsifier is itself
  authored by a model, author it BLIND to the artifact (Contraprova: falsifier
  pack authored from the SPEC only, sha-pinned before the artifact exists,
  authoring `claude -p` runs cwd-outside-the-repo + tool-less). A grader that has
  seen the artifact can be led by it.
- **ONE live shakedown before the full N.** Validation of any hardened instrument
  includes a single LIVE run (one model, N=20, ~$5 by W0b arithmetic) — because
  green mocks do not exercise the billing regime or the live hermeticity flags
  (S229). The shakedown is PENDING-OWNER (paid); its recipe is frozen in the
  instrument README. Do not certify an instrument on mocks alone.

---

## 6. Noise-floor clause — config is a variable; timing verdicts need replication

> **This is the clause most likely to be skipped under deadline, and the one whose
> absence is most expensive (a false KILL closes a question forever).**

- **A feature's configuration is an experimental variable, not a fixed
  background.** `effort`, `max_turns`, cache TTL, the model's own version, the
  quota bucket — changing any of them changes the measurement. A verdict only
  transfers to another window if the instrument's `hermeticity` block (frozen
  constants) is byte-identical there. This is why O5 froze the flag set as
  instrument constants, not run-time arguments.
- **Timing deltas under ~3-6pp (≈3-6% of the baseline p50) are INCONCLUSIVE,
  not a KILL.** Wall-clock on a shared-quota substrate is noisy: ITPM/OTPM
  ceilings, 429 backoff, server load, and time-of-day all move p50 by single-digit
  percent run-to-run. A delta inside that band is **inconclusive — replicate, do
  not KILL on it.** (A delta WAY outside the band — e.g. W2 E5's 51% SLOWER — is
  robust and a KILL stands on a single window; see Doctrine 7.)
- **Timing verdicts require replication across windows.** A speed WIN or KILL that
  rests on a sub-10pp delta must be reproduced on ≥2 independent windows (different
  day, ideally different quota bucket) before it is recorded. A single-window
  timing number near the noise floor is a hypothesis, not a verdict.
- **Quota-bucket is part of every number.** From 2026-06-15 headless `claude -p`
  draws the Agent-SDK credit bucket; from 2026-06-22 Fable bills usage credits.
  Record every paid number WITH its bucket — a cross-bucket comparison is a
  confound (PLAN-135 §W5 accounting axes).

---

## 7. Retroactive audit (annotation only — verdicts stand)

This doctrine is only credible if we apply it to our own recorded KILLs. The
retroactive re-annotation of every prior speed-KILL —
**timing-robust vs within-noise** — lives at
`.claude/plans/PLAN-135/research/SPEED-KILLS-TIMING-ANNOTATION.md`.

It is an **annotation only**: it re-reads the recorded verdict files against the
noise-floor clause and labels each, but **the verdicts STAND** — none are reopened.
The headline finding (see that file for the per-kill detail): the speed thesis was
killed in part by deltas FAR outside the noise floor (W2 E5 at +51% slower; PLAN-123
E2 at a 2.69× cost multiple) and in part by structural/paper kills (Amdahl-ceiling
falsification, AST-gate semantic-recall 0.00) that do not depend on a timing delta
at all — so the death of the speed thesis is timing-robust regardless of where the
noise floor is drawn. The annotation also flags any kill that DID rest on a
near-noise timing delta, as a transparency record of where this doctrine, had it
existed at the time, would have demanded a second window.

---

## Cross-references

- Hardened instrument + the O5 flag PROBE lines: `.claude/plans/PLAN-135/instruments/README.md`
- The hardened workflow itself: `.claude/workflows/eval-baseline-n20.js`
- Ledger-grade frozen driver: `.claude/plans/PLAN-134/w0b/w0b_baseline.py`
- Frozen prereg (W2 pilots): `.claude/plans/PLAN-134/w2/PREREG-W2.md`
- Frozen harness (rules, freeze, kill criteria): `.claude/plans/PLAN-123/harness/`
- Retroactive timing annotation: `.claude/plans/PLAN-135/research/SPEED-KILLS-TIMING-ANNOTATION.md`
- Cost-reconciliation lesson: `[[feedback-paid-run-reveals-billing-regime-bugs-mocks-cant]]`
- Codex-validates-reality lesson: `[[feedback-codex-validates-reality-debate-validates-design]]`
