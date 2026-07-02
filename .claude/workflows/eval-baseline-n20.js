export const meta = {
  name: 'eval-baseline-n20',
  description: 'Parameterized N=20 behavioral baseline (PLAN-134 W1 item 4, GATE-W0b shape). Runs the 20 frozen PLAN-123 independent tasks (T01-T20) against args.model. Because Workflow opts.model is INERT (W0a verdict, PLAN-134/W0a-VERDICT.md), each task is executed by a `claude -p --model <args.model>` SUBPROCESS in a /tmp scratch dir — Workflow agents only orchestrate + grade. PAID: requires args {model, confirm_spend: true}. Simplified single-shot protocol (no self-heal turn); the frozen ledger-grade instrument remains PLAN-134/w0b/w0b_baseline.py.',
  phases: [{ title: 'Eval' }, { title: 'Reconcile' }],
}

// ---------------------------------------------------------------------------
// HARD SPEND GUARD — paid runs need explicit opt-in. W0b observed $1.17-$8.82
// per 20-task arm depending on model; budget ceiling mirrors w0b HARD_CAP_USD.
// ---------------------------------------------------------------------------
// `typeof` guard first: args may be undeclared depending on harness version (w0a-probe precedent).
if (typeof args !== 'object' || args === null || args.confirm_spend !== true) {
  throw new Error("eval-baseline-n20 spends real money/quota (W0b observed $1-9 per model arm). Invoke as Workflow {name: 'eval-baseline-n20', args: {model: '<exact-id>', confirm_spend: true}}.")
}
if (typeof args.model !== 'string' || args.model.length === 0) {
  throw new Error("args.model is required — the EXACT model id for `claude -p --model` (e.g. 'claude-haiku-4-5'). Tier shorthands route, but exact ids are the only auditable form (ADR-149 allowlist spirit).")
}
// Shell-safety gate (Codex S228 finding #2): every arg below is interpolated
// into Bash snippets the batch agents execute — reject anything outside a
// strict token grammar BEFORE any agent spawns.
if (!/^claude-[a-z0-9][a-z0-9.-]*$/.test(args.model)) {
  throw new Error(`args.model '${args.model}' rejected: must match ^claude-[a-z0-9][a-z0-9.-]*$ (exact Anthropic model id; no spaces/quotes/shell metacharacters).`)
}
if (args.corpus !== undefined && (typeof args.corpus !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(args.corpus) || args.corpus.includes('..'))) {
  throw new Error('args.corpus rejected: relative path of [A-Za-z0-9._/-] only, no "..".')
}
if (args.run !== undefined && (typeof args.run !== 'string' || !/^[A-Za-z0-9._-]{1,40}$/.test(args.run))) {
  throw new Error('args.run rejected: label of [A-Za-z0-9._-], max 40 chars.')
}

const MODEL = args.model
// Frozen PLAN-123 corpus (e2_manifest/<ID>/{task.json, seed/, check.py}) — overridable.
const CORPUS = (typeof args.corpus === 'string' && args.corpus)
  ? args.corpus
  : '.claude/plans/PLAN-123/harness/freeze/e2_manifest'
const FREEZE = '.claude/plans/PLAN-123/harness/freeze'
// Run label passed IN — clock/random calls throw inside Workflow scripts (resume determinism).
const RUN = (typeof args.run === 'string' && args.run) ? args.run : 'N20-MANUAL'
const PER_BATCH_CAP_USD = 7 // 4 batches ≈ w0b HARD_CAP_USD=25 with headroom

// -------------------------------------------------------------------------
// O5 (PLAN-135 W5) — MECHANICAL HERMETICITY + BUDGET CEILING CONSTANTS.
// Each constant maps to one PROBE line in instruments/README.md. They are
// frozen instrument parameters, NOT experimental variables (Doctrine 6 of
// EVAL-DOCTRINE.md: "config of a feature is itself a variable" — so a fixed
// frozen value is the only way a verdict transfers across windows). The
// S229 lesson (9 instrument P0s survived green mocks) is why every one of
// these is asserted by the subject-side probe, not just documented.
// -------------------------------------------------------------------------
// PER-TASK budget ceiling, passed to the CLI as a MECHANICAL prereg cap via the
// `--max-budget-usd` flag (CLI-verified name; the JS-level arg below is
// `args.max_budgeted_usd` — a caller-facing workflow arg, distinct from the CLI
// flag spelling). The honor-system "BUDGET STOP" prompt sum is kept as a
// fail-open backstop, but the CLI flag is the load-bearing kill: a task that
// would exceed it stops with a budget-exceeded result subtype BEFORE
// over-spending, and that subtype is recorded as budget_kill, NOT pass=false
// (the budget-kill ≠ p_fail taxonomy — see instruments/README.md). The exact
// budget result-subtype string is PENDING-OWNER confirmation on the live
// shakedown; the step-5 mapper accepts both `error_max_budget_usd` and
// `error_max_budget` and falls back on `is_error`/`startswith("error")`.
const PER_TASK_BUDGET_USD = (typeof args.max_budgeted_usd === 'number' &&
  args.max_budgeted_usd > 0 && args.max_budgeted_usd <= PER_BATCH_CAP_USD)
  ? args.max_budgeted_usd
  : 1.5 // W0b real cost ~$0.41/task (Fable) → 1.5 is a ~3.6x cap-safe ceiling
// maxTurns: the O5 plan text asks for a mechanical turn cap so a runaway agent
// loop cannot inflate wall-clock/cost and confound the timing leg. DOCTRINE-3
// PROBE FINDING (claude CLI 2.1.177, `claude --help`): there is NO `--max-turns`
// flag on this CLI build — `claude -p "<prompt>"` (print/headless mode) is
// inherently SINGLE-TURN: it runs one prompt to completion and exits, it does
// not enter an interactive agent loop awaiting more user turns. So maxTurns=1 is
// the BUILT-IN behavior of the `-p` substrate; the cap is satisfied structurally,
// not by a flag. MAX_TURNS is retained as a recorded instrument constant (and a
// guard against a future caller passing >1, which this single-shot harness does
// not support) — it is NOT interpolated into the argv. If a future CLI build adds
// `--max-turns` and a multi-turn protocol is wanted, wire it here AND re-pin.
const MAX_TURNS = (typeof args.max_turns === 'number' && Number.isInteger(args.max_turns) &&
  args.max_turns >= 1 && args.max_turns <= 8) ? args.max_turns : 1
if (args.max_budgeted_usd !== undefined && (typeof args.max_budgeted_usd !== 'number' ||
    !(args.max_budgeted_usd > 0) || args.max_budgeted_usd > PER_BATCH_CAP_USD)) {
  throw new Error(`args.max_budgeted_usd rejected: must be a number in (0, ${PER_BATCH_CAP_USD}] (per-task mechanical ceiling).`)
}
if (args.max_turns !== undefined && (!Number.isInteger(args.max_turns) ||
    args.max_turns < 1 || args.max_turns > 8)) {
  throw new Error('args.max_turns rejected: integer in [1, 8] (single-shot frozen protocol = 1).')
}
if (MAX_TURNS !== 1) {
  // This single-shot `claude -p` harness has no multi-turn substrate (no --max-turns
  // flag on CLI 2.1.177). Refuse rather than silently run single-turn under a >1 cap.
  throw new Error(`args.max_turns=${MAX_TURNS} unsupported: this single-shot \`claude -p\` harness is structurally 1-turn (no --max-turns flag on the CLI). Use the frozen w0b driver for any multi-turn protocol.`)
}

const TASK_IDS = [
  'T01', 'T02', 'T03', 'T04', 'T05', 'T06', 'T07', 'T08', 'T09', 'T10',
  'T11', 'T12', 'T13', 'T14', 'T15', 'T16', 'T17', 'T18', 'T19', 'T20',
]
const BATCHES = [
  TASK_IDS.slice(0, 5), TASK_IDS.slice(5, 10),
  TASK_IDS.slice(10, 15), TASK_IDS.slice(15, 20),
]

const ROW_SCHEMA = {
  type: 'object',
  required: ['task', 'pass', 'cost_usd', 'transcript_path', 'notes', 'result_subtype'],
  properties: {
    task: { type: 'string' },
    pass: { type: 'boolean' },
    cost_usd: { type: 'number' },
    transcript_path: { type: 'string' },
    notes: { type: 'string' },
    // O5 budget-kill ≠ p_fail taxonomy. The CLI result event carries a
    // `subtype`; we record it verbatim so reconcile/analysis can SEPARATE a
    // graded failure from a non-result. Closed enum:
    //   success           — model produced an answer; `pass` is the graded verdict
    //   error_max_budget  — --max-budget-usd tripped (budget_kill); NOT a p_fail
    //   error_max_turns   — maxTurns tripped (non-result); NOT a p_fail
    //   error_other       — any other CLI/error result subtype; NOT a p_fail
    //   instrument_error   — harness step failed before/around the call (timeout,
    //                        missing result file, nonzero claude exit, batch-stop);
    //                        NOT a p_fail — voids the cell, never scored as a loss
    result_subtype: {
      type: 'string',
      enum: ['success', 'error_max_budget', 'error_max_turns', 'error_other', 'instrument_error'],
    },
  },
}
const BATCH_SCHEMA = {
  type: 'object',
  required: ['rows'],
  properties: { rows: { type: 'array', items: ROW_SCHEMA } },
}

const batchPrompt = (ids) => `You are an eval runner for the ${MODEL} N=20 baseline (run ${RUN}, PLAN-134 W1).
Repo root = current working directory. Your tasks, IN ORDER: ${ids.join(', ')}.

CONFINEMENT (ADR-136-AMEND-1): the REPO is read-only for you — never Edit/Write any repo file,
never touch the corpus under ${CORPUS}. Your ONLY writes are scratch dirs/files under /tmp.
The model under test runs in a SUBPROCESS (Workflow opts.model is inert — W0a verdict); you
yourself must NOT solve the tasks.

FOR EACH task ID, run this exact procedure via Bash (use a generous per-command timeout, ~600000ms for step 4):

1. Scratch dir:  SCRATCH=$(mktemp -d "/tmp/n20-${RUN}-<ID>.XXXXXX")
2. Seed it:      cp -R "${CORPUS}/<ID>/seed/." "$SCRATCH"/
3. Build the frozen Arm-D solo prompt (byte-faithful to freeze/arms.py _solo_prompt) into a
   SIBLING file (never inside $SCRATCH — the workdir must hold only seed + model edits):
     python3 - "${CORPUS}/<ID>/task.json" "${FREEZE}/shared_prefix.txt" > "$SCRATCH.prompt.txt" <<'PY'
     import json, sys
     t = json.load(open(sys.argv[1])); prefix = open(sys.argv[2]).read()
     files = sorted(set(t.get("allowed_paths", [])) | set(t.get("expected_paths", [])))
     sys.stdout.write(prefix
         + "\\n\\n=== TASK CONTRACT ===\\n" + t.get("contract", "")
         + "\\n\\nFiles you may edit (in the current directory): " + ", ".join(files)
         + "\\nEdit ONLY these files. Do not create, rename or touch any other file.")
     PY
4. Run the subject model in the scratch dir, HERMETICALLY (O5 hardening, PLAN-135 W5). The
   subject is a SUBJECT — it must not inherit the operator's settings, skills, memory, MCP, or
   config, and it must be mechanically capped. Build a SCRATCH config dir SIBLING to the workdir
   so the subject's own state never touches the operator's ~/.claude:
     CONFIGDIR=$(mktemp -d "/tmp/n20cfg-${RUN}-<ID>.XXXXXX")
     ( cd "$SCRATCH"
       # (a) drop every CLAUDE_CODE_* var (W0B amendment #3b — billing-affecting env drift voids runs)
       for v in $(env | sed -n 's/^\\(CLAUDE_CODE_[A-Za-z0-9_]*\\)=.*/\\1/p'); do unset "$v"; done
       # (b) RE-SET the disable-auto-memory toggle AFTER the unset (it is itself a CLAUDE_CODE_* var,
       #     so step (a) just stripped any inherited value — order is load-bearing). + scratch config dir.
       export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
       export CLAUDE_CONFIG_DIR="$CONFIGDIR"
       claude -p "$(cat "$SCRATCH.prompt.txt")" --model ${MODEL} --output-format json \\
         --setting-sources "" \\
         --strict-mcp-config --mcp-config '{}' \\
         --max-budget-usd ${PER_TASK_BUDGET_USD} \\
         > "$SCRATCH.result.json" 2> "$SCRATCH.stderr.txt" )
     CLAUDE_RC=$?
     rm -rf "$CONFIGDIR"
   FLAG INTENT — flag names VERIFIED against \`claude --help\` on CLI 2.1.177 (Doctrine 3
   "verify-the-knob-routes"; the harvest text's --settingSources / --max-budgeted-usd / --max-turns
   were WRONG — see instruments/README.md PROBE table). Do NOT silently drop a flag if a future CLI
   rejects it; record the row result_subtype="instrument_error", notes="flag-unsupported:<flag>", and
   STOP the batch so the whole run is re-pinned, never half-hermetic:
     • CLAUDE_CONFIG_DIR (scratch)        — subject reads/writes config in a throwaway dir, not ~/.claude
     • CLAUDE_CODE_DISABLE_AUTO_MEMORY=1  — no operator memory auto-loaded into the subject
     • --setting-sources ""               — children load NO operator settings/skills/memory (the flagship
                                            instrument's "vetor vivo de contaminação"; "" disables all of
                                            {user,project,local} per the CLI help)
     • --strict-mcp-config --mcp-config '{}' — no MCP servers; subject cannot reach operator tools
     • --max-budget-usd ${PER_TASK_BUDGET_USD} — MECHANICAL prereg ceiling (only-works-with --print);
                                            budget_kill ≠ p_fail (taxonomy below)
   maxTurns (=${MAX_TURNS}): NOT a flag on this CLI — \`claude -p\` is structurally single-turn, so the
   cap is satisfied by the substrate, not the argv (see MAX_TURNS const). NOTE on --bare: when this run
   is API-billed (a key in env, not a subscription session) the operator adds \`--bare\` to the argv
   (minimal mode — skips hooks/LSP/plugin/CLAUDE.md-dirs/auto-memory, per CLI help) for a clean API path;
   it is OMITTED here because the Workflow substrate is subscription-denominated and \`--bare\` would also
   drop the governance hooks we keep on that path. Do NOT add --dangerously-skip-permissions.
5. Read the result SUBTYPE first (the budget-kill ≠ p_fail gate), THEN grade. The CLI result event
   carries {is_error, subtype, total_cost_usd}:
     python3 - "$SCRATCH.result.json" "$CLAUDE_RC" <<'PY'
     import json, sys
     try:
         d = json.load(open(sys.argv[1]))
     except Exception as e:
         print("subtype=instrument_error cost=0 note=unparseable-result:%s" % str(e)[:60]); sys.exit(0)
     rc = sys.argv[2]
     is_err = bool(d.get("is_error"))
     sub = str(d.get("subtype") or "")
     cost = d.get("total_cost_usd", 0)
     # Map the CLI subtype onto the frozen closed enum (budget-kill ≠ p_fail).
     if sub in ("error_max_budget_usd", "error_max_budget"):
         st = "error_max_budget"
     elif sub in ("error_max_turns",):
         st = "error_max_turns"
     elif is_err or sub.startswith("error"):
         st = "error_other"
     elif rc != "0":
         st = "instrument_error"
     else:
         st = "success"
     print("subtype=%s cost=%s note=%s" % (st, cost, sub or "clean"))
     PY
6. Grade ONLY if step-5 subtype == "success" (a non-result is NOT a graded failure):
     python3 "${FREEZE}/check_runner.py" "${CORPUS}/<ID>/check.py" "$SCRATCH"; echo "check_exit=$?"

Record one row per task: task=<ID>, transcript_path="$SCRATCH.result.json", cost_usd=<from step 5>,
result_subtype=<from step 5>, and:
  • subtype=="success"          → pass=(check_exit==0); notes="" (or first redacted issue)
  • subtype=="error_max_budget" → pass=false, notes="BUDGET-KILL:max-budget-usd"  ← budget_kill, NOT p_fail
  • subtype=="error_max_turns"  → pass=false, notes="MAX-TURNS"                      ← non-result, NOT p_fail
  • subtype=="error_other"      → pass=false, notes="<redacted first stderr line>"   ← non-result, NOT p_fail
  • subtype=="instrument_error" → pass=false, notes="<timeout|missing-result|nonzero-exit|flag-unsupported>"
The reconciler computes pass@1 over the SUCCESS cells only and reports the subtype histogram separately —
a budget/turns/instrument cell is VOID for the quality denominator, never a 0. Never skip a row, never
re-run a paid call.

BUDGET STOP (batch backstop): keep a running cost sum; if it exceeds $${PER_BATCH_CAP_USD} BEFORE starting a
task, do NOT start it — emit its row as pass=false, cost_usd=0, result_subtype="instrument_error",
notes="BUDGET-STOP". Return ONLY {rows: [...]} with exactly ${ids.length} rows in task order.`

phase('Eval')
log(`eval-baseline-n20: model=${MODEL} run=${RUN} corpus=${CORPUS} — 4 batches x 5 tasks via claude -p subprocesses`)

const batches = await parallel(BATCHES.map((ids, i) => () =>
  agent(batchPrompt(ids), { label: `eval:${MODEL}:batch${i + 1}`, phase: 'Eval', schema: BATCH_SCHEMA })
    // agent() RESOLVES null on terminal API error (never rejects) — .catch alone
    // misses it and the row loop crashes on null.rows (PLAN-152 error-handling-03;
    // crash class from run wf_071ef6c5). Degraded rows carry result_subtype=
    // instrument_error so the reconciler voids the cells instead of miscounting.
    .then((r) => r || {
      rows: ids.map((id) => ({
        task: id, pass: false, cost_usd: 0, transcript_path: '',
        notes: 'BATCH-AGENT-NULL: agent resolved null (terminal API error or user skip)',
        result_subtype: 'instrument_error',
      })),
    })
    .catch((e) => ({
      rows: ids.map((id) => ({
        task: id, pass: false, cost_usd: 0, transcript_path: '',
        notes: `BATCH-AGENT-ERROR: ${String(e).slice(0, 160)}`,
        result_subtype: 'instrument_error',
      })),
    }))))

const rows = []
for (const b of batches) for (const r of (b.rows || [])) rows.push(r)

phase('Reconcile')

const RECON_SCHEMA = {
  type: 'object',
  required: ['n', 'pass_count', 'success_cells', 'subtype_histogram', 'total_cost_usd',
    'missing_transcripts', 'anomalies', 'summary'],
  properties: {
    n: { type: 'integer' },
    pass_count: { type: 'integer' },
    // O5 taxonomy: pass@1 denominator is the SUCCESS cells only — a budget/turns/instrument
    // cell is VOID, never a graded loss. Both counts surface so a reader sees the effective N.
    success_cells: { type: 'integer' },
    subtype_histogram: {
      type: 'object',
      required: ['success', 'error_max_budget', 'error_max_turns', 'error_other', 'instrument_error'],
      properties: {
        success: { type: 'integer' },
        error_max_budget: { type: 'integer' },
        error_max_turns: { type: 'integer' },
        error_other: { type: 'integer' },
        instrument_error: { type: 'integer' },
      },
    },
    total_cost_usd: { type: 'number' },
    missing_transcripts: { type: 'array', items: { type: 'string' } },
    anomalies: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
  },
}

const recon = await agent(`You are the reconciler for the ${MODEL} N=20 baseline (run ${RUN}). READ-ONLY: no writes anywhere.
Rows reported by the 4 eval batches:

${JSON.stringify(rows, null, 1)}

Reconcile (W0b discipline — counts must close, never trust a single accounting path; O5 budget-kill ≠ p_fail taxonomy):
1. n = row count; verify it is exactly 20 with task ids exactly T01-T20, no dup/no gap. Any deviation -> anomalies.
2. subtype_histogram = count rows by result_subtype across the 5 enum values {success, error_max_budget,
   error_max_turns, error_other, instrument_error}. success_cells = the success count.
3. pass_count = number of rows that are BOTH result_subtype=="success" AND pass==true (recompute yourself).
   pass@1 = pass_count / success_cells (NOT /20). A budget/turns/instrument cell is VOID for the quality
   denominator — it is NEVER counted as a 0/failure (that is the whole point of the taxonomy: a run that
   budget-killed 5 tasks is 15/15, not 15/20). If a row has result_subtype=="success" but pass==false, that
   IS a real graded failure and counts in the denominator.
4. total_cost_usd = sum of cost_usd. Cross-check each row with a transcript: the transcript file must
   exist (Bash: ls / python3 json.load it read-only) and its total_cost_usd must match the row within 2%
   tolerance. Missing/unreadable file -> missing_transcripts; >2% drift -> anomalies. A non-empty notes row
   on a SUCCESS cell is an anomaly; a notes row on a budget/turns/instrument cell is EXPECTED, not an anomaly.
5. summary: one paragraph — pass@1 = pass_count/success_cells with the caveat verbatim: "N=20 powers a KILL
   only (POWERED_N=40); no WIN/superiority claim is admissible" (W0b finding #2); state success_cells (the
   effective N) and the subtype histogram inline (e.g. "3 budget-killed, 0 max-turns"); total cost; and
   whether the run is CLEAN (no anomalies, no missing transcripts, success_cells>=18) or VOID-SUSPECT
   (success_cells<18 → the effective N is too small to power even a KILL; flag it).
Return ONLY the structured object.`,
  { label: `eval:${MODEL}:reconcile`, phase: 'Reconcile', schema: RECON_SCHEMA })

// recon === null on terminal API error — return a DEGRADED reconciliation instead
// of silently dropping the accounting leg (PLAN-152 error-handling-03). The degraded
// object still DERIVES histogram/pass_count/total_cost mechanically from `rows`
// (counts-must-close: zeroed numbers would under-report paid spend — Codex P2);
// only the transcript cross-check leg is lost.
const reconSafe = recon || (() => {
  const hist = { success: 0, error_max_budget: 0, error_max_turns: 0, error_other: 0, instrument_error: 0 }
  let passCount = 0
  let totalCost = 0
  for (const r of rows) {
    const st = (r && Object.prototype.hasOwnProperty.call(hist, r.result_subtype)) ? r.result_subtype : 'instrument_error'
    hist[st] += 1
    if (st === 'success' && r.pass === true) passCount += 1
    totalCost += (r && typeof r.cost_usd === 'number') ? r.cost_usd : 0
  }
  return {
    n: rows.length, pass_count: passCount, success_cells: hist.success,
    subtype_histogram: hist, total_cost_usd: totalCost, missing_transcripts: [],
    anomalies: ['RECONCILER-NULL: agent resolved null (terminal API error or user skip) — counts derived mechanically from rows; transcript cross-check NOT performed'],
    summary: `DEGRADED: reconciler agent resolved null; mechanical derivation from rows: pass ${passCount}/${hist.success} success cells, `
      + `subtype histogram ${JSON.stringify(hist)}, total cost $${totalCost.toFixed(4)}. `
      + 'Transcript cross-check not performed; no pass@1 claim admissible.',
  }
})()

return {
  run_id: RUN,
  model: MODEL,
  corpus: CORPUS,
  protocol: 'single-shot solo (frozen _solo_prompt, NO self-heal turn) — comparable in shape, NOT identical to the frozen w0b Arm-D instrument; for ledger-grade numbers run PLAN-134/w0b/w0b_baseline.py',
  // O5 hermeticity profile (PLAN-135 W5) — the frozen instrument constants this
  // run enforced. A verdict from this run only transfers to another window if
  // this block is byte-identical there (EVAL-DOCTRINE Doctrine 6).
  hermeticity: {
    cli_verified: 'flag names checked against `claude --help` on CLI 2.1.177 (Doctrine 3)',
    config_dir: 'scratch (CLAUDE_CONFIG_DIR per task, rm -rf after)',
    auto_memory: 'disabled (CLAUDE_CODE_DISABLE_AUTO_MEMORY=1, set AFTER the CLAUDE_CODE_* unset)',
    setting_sources: 'none (--setting-sources "")',
    mcp: 'strict, empty (--strict-mcp-config --mcp-config "{}")',
    max_turns: MAX_TURNS + ' (structural: `claude -p` is single-turn; no --max-turns flag on 2.1.177)',
    max_budget_usd: PER_TASK_BUDGET_USD + ' (--max-budget-usd, only-works-with --print)',
    bare: 'omitted here (subscription substrate keeps governance hooks); operator adds --bare on the API-billed path',
    permissions: 'NO --dangerously-skip-permissions (operator global allowlist only)',
    taxonomy: 'budget-kill ≠ p_fail: result_subtype splits success | error_max_budget | error_max_turns | error_other | instrument_error; pass@1 denominator = success cells only',
  },
  rows,
  reconciliation: reconSafe,
  note: 'Subject model ran only via `claude -p --model` subprocesses (W0a: Workflow opts.model is INERT). Repo untouched; all writes confined to /tmp scratch + a per-task scratch CLAUDE_CONFIG_DIR (no operator ~/.claude contamination — O5).',
}
