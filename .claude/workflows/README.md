# Saved Workflows — `.claude/workflows/`

Reviewed, spawn-compliant saved workflows for the harness `Workflow` tool
(PLAN-134 W1 item 4). Invoke by name:

```js
Workflow {name: 'nightly-hygiene'}
Workflow {name: 'audit-fanout', args: {scope: '.claude/hooks'}}
Workflow {name: 'eval-baseline-n20', args: {model: 'claude-haiku-4-5', confirm_spend: true, run: 'N20-S228'}}
```

## Doctrine: ADR-136-AMEND-1 read-only confinement

All three workflows operate under ADR-136-AMEND-1 (ADOPT-CONFINED):

- **§4.1 Read-only only.** Workflow agents perform investigation/audit/eval
  fan-out exclusively. They write NO repo files, drive NO canonical edits, NO
  ceremony, NO `audit_emit` write path. Reports are **return values**, never
  files. (The single carve-out: `eval-baseline-n20` agents create scratch dirs
  under `/tmp` for the *subprocess* model under test — the repo itself stays
  untouched.)
- **§4.3 Structured returns.** Audit-shaped findings travel as the ADR-141
  8-field shard schema (`finding_id`, `map_key`, `disposition`,
  `evidence_kind`, `evidence_pointer`, `confidence` in integer basis points,
  `risk_tags`, `author` — see `docs/triage-reduce-protocol.md`), plus `file` +
  `claim` for deterministic dedup. Eval rows in `eval-baseline-n20` are
  measurements, not audit findings — they carry their own literal schema with
  `transcript_path` as the evidence pointer (precedent: the reviewed
  `PLAN-134/staged/gates/w0a-probe-workflow.js`).
- **§4.2 caveat (S185 lesson).** Workflow subagents share the parent session's
  live hook rail. Large audit runs that must keep the canonical audit chain
  pristine should run from a throwaway clone or with a session-level audit-dir
  redirect, and re-verify the chain LAST.

## The W0a caveat: `opts.model` is INERT

`PLAN-134/W0a-VERDICT.md` (S227, double ground truth): the Workflow tool's
per-agent `opts.model` override does **not** route on this harness version —
every Workflow agent runs the inherited session model. Consequences baked into
these scripts:

- Workflow agents are priced at the session model's rate. Keep their prompts
  lean; they orchestrate and grade, they do not do cheap-tier work.
- Any cheap-tier or cross-model execution happens via a
  **`claude -p --model <exact-id>` subprocess** (the W0b methodology) — never
  via `opts.model`. `eval-baseline-n20` is built on exactly this substrate.

## Workflow script contract (for authors)

`export const meta = {...}` as a pure literal first; plain JS (no TS); no
`Date.now()` / `Math.random()` / argless `new Date()` (they THROW — resume
determinism; pass run ids in via `args`); only `agent()` / `parallel()` /
`pipeline()` / `phase()` / `log()`; schemas as literals; top-level `await` +
`return` allowed.

---

## 1. `nightly-hygiene` — read-only repo hygiene sweep

**Args:** none.
**Cost:** quota-only (5 small agents, no paid subprocesses).

Phase *Sweep* — 4 parallel read-only dimension agents:

| Dimension | Probe |
|---|---|
| `audit-errors` | triage `~/.claude/projects/.../audit-log.errors` lines BY CLASS (count + redacted exemplar each) |
| `staleness` | `python3 .claude/scripts/check-staleness.py` (advisory CLI) — stale plans/ADRs/benchmarks |
| `counts-drift` | `bash .claude/scripts/local/verify-counts.sh` — derived counts vs documented counts |
| `ci-red` | `gh run list --branch main --limit 20` — latest-run-per-workflow red check |

Phase *Synthesize* — one agent merges the 4 results into a single markdown
report (status board + 8-field findings table + recommended actions).
**Returns** `{overall, report, dimensions}`. No agent writes any file.

## 2. `eval-baseline-n20` — parameterized N=20 behavioral baseline

**Args:** `{model: '<exact-id>', confirm_spend: true, corpus?, run?}`.
**Cost:** PAID — W0b observed $1.17–$8.82 per 20-task arm (`docs/fable-5-baseline.md`).

- **HARD GUARD:** throws immediately unless `args.confirm_spend === true`
  (paid runs need explicit opt-in) and `args.model` is a non-empty exact id.
- **Corpus:** `args.corpus`, default = the frozen PLAN-123 corpus
  `.claude/plans/PLAN-123/harness/freeze/e2_manifest` (T01–T20,
  `kind=independent`, each `{task.json, seed/, check.py}`).
- **Substrate (W0a-binding):** 4 batch agents × 5 tasks. Per task: `mktemp -d`
  scratch under `/tmp` → copy `seed/` → build the frozen Arm-D solo prompt
  (byte-faithful to `freeze/arms.py:_solo_prompt`) → run
  `claude -p "$(cat …)" --model <args.model> --output-format json` in the
  scratch dir with a sanitized env (every `CLAUDE_CODE_*` dropped — W0B-PREREG
  amendment #3b) → grade via the frozen isolated `check_runner.py` → cost from
  the result event's `total_cost_usd`. Per-batch budget stop at $7
  (≈ w0b `HARD_CAP_USD=25` across 4 batches).
- Phase *Reconcile* — a final agent re-verifies 20 unique rows T01–T20,
  recomputes pass count, sums cost, cross-checks each row against its
  transcript at 2% tolerance (W0b counts-must-close discipline), and stamps the
  run CLEAN or VOID-SUSPECT.
- **Protocol honesty:** single-shot solo, **no self-heal turn** — comparable in
  shape but NOT identical to the frozen W0b Arm-D instrument. N=20 powers a
  KILL only (`POWERED_N=40`); no WIN claim is admissible. For ledger-grade
  numbers run `PLAN-134/w0b/w0b_baseline.py` from a plain terminal.

**Returns** `{run_id, model, corpus, protocol, rows, reconciliation, note}`.

## 3. `audit-fanout` — S185/S225 audit shape

**Args:** `{scope: '<subtree or topic>'}` (default whole repo).
**Cost:** quota-only (8 finders + ≤8 refuters + 1 synthesizer, all read-only).

- Phase *Find* — 8 parallel finder agents, one per dimension (security,
  governance, tests, docs, economics, dead-code, error-handling,
  dependencies); ≤8 evidence-backed findings each, ADR-141 8-field shards.
- Deterministic in-script **dedup by `file` + normalized `claim`** before any
  verification spend (cross-dimension dups folded, provenance kept).
- Phase *Refute* — adversarial REDUCE: one refuter per dimension re-checks
  every finding's `evidence_pointer` FIRST-HAND and rules
  confirmed/refuted/unverifiable. Accepting without re-checking evidence is
  prose-laundering (ADR-141 P0; PLAN-114: ~57% of unverified findings were
  stale).
- Phase *Synthesize* — verdict (`CLEAN` / `FINDINGS` / `DEGRADED`) + markdown
  findings table, refuted-at-REDUCE table (the saved false positives), and
  next actions from confirmed `fix` findings only.

**Returns** `{scope, verdict, report, stats, confirmed_findings, confinement}`.
