export const meta = {
  name: 'nightly-hygiene',
  description: 'Read-only repo hygiene sweep (PLAN-134 W1 item 4; PLAN-135 W1 w0r added dimension v; W5 o8o11o12 added dimensions vi+vii; PLAN-139 Wave B added dimension viii). Eight parallel read-only agents — (i) audit-log.errors triage by class, (ii) plan/ADR staleness via check-staleness.py, (iii) derived-counts drift via verify-counts.sh, (iv) CI red check via gh run list, (v) deprecated/retiring model-id scan via check-model-deprecations.py, (vi) consumed env-var drift via env-inventory-check.py (the S218 footgun class), (vii) Claude Code + Agent-SDK substrate drift via check-substrate-watch.py (the S214/S230 changelog sweep made permanent), (viii) inline-debt ledger via check-debt-ledger.py (PLAN-139 Wave B — advisory # CEO-DEBT: marker sweep) — then one synthesis agent merges everything into a single markdown report RETURNED by the workflow. ADR-136-AMEND-1 confinement: agents write NO files, emit NO canonical edits, stay no-network; findings travel as ADR-141 8-field shards (docs/triage-reduce-protocol.md).',
  phases: [{ title: 'Sweep' }, { title: 'Synthesize' }],
}

// ---------------------------------------------------------------------------
// CONFINEMENT (ADR-136-AMEND-1 §4): investigation fan-out ONLY. Every agent is
// instructed read-only (no Edit/Write, no mutating Bash); the report is a
// RETURN VALUE, never a file. Any write request from a child is a P0 breach.
// COST: 8 small agents (7 dimensions + 1 synth), quota-only (no claude -p
// children, no API spend); every dimension probe is a local read-only script.
// ---------------------------------------------------------------------------

const READ_ONLY_RULES = `HARD RULES (ADR-136-AMEND-1 read-only confinement):
- You are a READ-ONLY investigator. NEVER use Edit/Write/NotebookEdit. Write NO files anywhere (not even /tmp).
- Bash is allowed ONLY for read-only commands (ls, cat, grep, git log/status/diff, gh run list/view, python3 <reporting script>, bash <reporting script>). No redirection into files, no rm/mv/cp, no git mutations, no gh mutations.
- Report EVERYTHING via your structured return value. Redact secrets/tokens; never echo raw env values.
- If a probe target is missing, return status "skipped" with the reason — do NOT improvise an alternative probe.`

// ADR-141 mandatory 8-field shard schema (docs/triage-reduce-protocol.md:24-37)
// + dedup helpers `file`/`claim` (extra fields are allowed; the 8 are required).
const FINDING_SCHEMA = {
  type: 'object',
  required: ['finding_id', 'map_key', 'disposition', 'evidence_kind',
    'evidence_pointer', 'confidence', 'risk_tags', 'author'],
  properties: {
    finding_id: { type: 'string' },
    map_key: { type: 'string' },
    disposition: { type: 'string', enum: ['fix', 'accept', 'fixed-confirmed', 'dup', 'moot', 'defer'] },
    evidence_kind: { type: 'string', enum: ['file_line', 'grep', 'test_run', 'audit_event', 'none'] },
    evidence_pointer: { type: 'string' },
    confidence: { type: 'integer', minimum: 0, maximum: 10000 },
    risk_tags: { type: 'array', items: { type: 'string' } },
    author: { type: 'string' },
    file: { type: 'string' },
    claim: { type: 'string' },
  },
}

const DIM_SCHEMA = {
  type: 'object',
  required: ['dimension', 'status', 'summary', 'findings'],
  properties: {
    dimension: { type: 'string' },
    status: { type: 'string', enum: ['green', 'yellow', 'red', 'skipped'] },
    summary: { type: 'string' },
    findings: { type: 'array', items: FINDING_SCHEMA },
  },
}

const DIMENSIONS = [
  {
    key: 'audit-errors',
    brief: `Triage the audit error sidecar BY CLASS.
1. Locate it: try ~/.claude/projects/ceo-orchestration/audit-log.errors first; if absent, ls ~/.claude/projects/ceo-orchestration/ and ~/.claude/projects/-Users-*-ceo-orchestration/ for *.errors files. If none exists, status=green with summary "no error sidecar".
2. Count total lines. Group lines into ERROR CLASSES by their stable shape (strip timestamps, PIDs, absolute paths, hex ids) — e.g. "indeterminate plan_id", "field drift scrubbed", parse errors.
3. For each class: line count + ONE truncated exemplar (<=160 chars, redacted) as evidence_pointer (evidence_kind=audit_event).
4. Emit one 8-field finding per class with >0 lines (disposition=fix for classes that look like live producer bugs, accept for known-benign noise; say which and why in claim). status: green if 0 lines, yellow if only known-benign classes, red if any class suggests a live producer bug.`,
  },
  {
    key: 'staleness',
    brief: `Plan/ADR/benchmark staleness.
1. From the repo root run: python3 .claude/scripts/check-staleness.py (read --help first if it needs flags; it is an ADVISORY CLI — a non-zero exit with findings is data, not infra failure).
2. Summarize its output: stale plans (executing/reviewed with old mtimes), stale ADRs (PROPOSED past their debate window), stale benchmarks.
3. One 8-field finding per stale item (evidence_kind=file_line, evidence_pointer=<path> or the checker's own output line; disposition=defer unless the item contradicts CLAUDE.md §Current Work, then fix). status: green if checker reports nothing stale.`,
  },
  {
    key: 'counts-drift',
    brief: `Derived-counts drift.
1. If .claude/scripts/local/verify-counts.sh exists, run: bash .claude/scripts/local/verify-counts.sh from the repo root. If it does not exist, status=skipped.
2. Compare every derived count it prints against the documented counts it checks (it self-reports drift; also note its exit code).
3. One 8-field finding per drifted count (evidence_kind=test_run, evidence_pointer=the script's drift line, disposition=fix, risk_tags=["docs"]). status: green on exit 0 / no drift, red on drift.`,
  },
  {
    key: 'ci-red',
    brief: `CI workflow red check.
1. Run: gh run list --branch main --limit 20 (read-only). If gh is unauthenticated/absent, status=skipped with the error summary.
2. List every run with conclusion failure/cancelled/timed_out: workflow name, run id, head sha, age.
3. For the MOST RECENT run of each distinct workflow, flag red conclusions as findings (older reds superseded by a newer green of the same workflow are history, not findings — mention them only in summary).
4. One 8-field finding per currently-red workflow (evidence_kind=test_run, evidence_pointer="gh run <id>", disposition=fix, risk_tags=["ci"]). status: green if latest run of every workflow succeeded.`,
  },
  {
    key: 'model-deprecations',
    brief: `Deprecated/retiring Claude model-id pins (PLAN-135 W1 w0r — the S230 sweep made permanent).
1. If .claude/scripts/check-model-deprecations.py exists, run from the repo root: python3 .claude/scripts/check-model-deprecations.py --json (read-only reporting script; scans the repo against the .claude/scripts/model-deprecations.json ledger; never writes files). If the script or its ledger is missing, status=skipped with the reason.
2. Parse the JSON report: summary counts (breaks/warns/info/inert), source_stale, and per-hit severity. Severity semantics: BREAK = id already retired (API requests fail today) on a non-inert path; WARN = id retires within 60 days on a non-inert path; INERT = a ledger inert_path_rules entry matched (negative fixtures, prose docs, historical results — by design, NOT findings).
3. One 8-field finding per non-inert BREAK or WARN, grouped by (model_id, file): evidence_kind=file_line, evidence_pointer=<path>:<line>, disposition=fix, risk_tags=["deprecation"], claim names the model_id + retirement date + recommended replacement. Mention info/inert counts only in summary.
4. If source_stale=true in the report, add ONE extra finding (disposition=defer, evidence_kind=file_line, evidence_pointer=.claude/scripts/model-deprecations.json, claim "ledger populated from fallback data — refresh from the official deprecations page").
status: red if any BREAK, yellow if any WARN or source_stale=true, green otherwise.`,
  },
  {
    key: 'env-var-drift',
    brief: `Consumed env-var drift (PLAN-135 W5 O8 — the S218 footgun class made permanent).
Context: a single env var set outside the reviewed surface (CLAUDE_CODE_SUBAGENT_MODEL=haiku, removed in S218/ADR-144) silently re-routed every subagent for weeks. This dimension diffs the live tree's referenced CLAUDE_*/ANTHROPIC_*/CEO_* names against the canonical inventory so a NEW (unreviewed) or VANISHED (stale-inventory) name surfaces here, not in a future incident.
1. If .claude/scripts/env-inventory-check.py exists, run from the repo root: python3 .claude/scripts/env-inventory-check.py --json (read-only reporting script; diffs referenced env names against .claude/scripts/env-inventory.json; --generate is the only writing mode and you must NOT use it). If the script or its inventory is missing, status=skipped with the reason.
2. Parse the JSON: status (clean|drift|fail-open), the "new" list (names referenced in code but absent from the inventory — an UNREVIEWED env surface) and the "stale" list (names in the inventory no longer referenced — inventory rot).
3. One 8-field finding per NEW name (evidence_kind=grep, evidence_pointer=<the name's evidence file>, disposition=fix, risk_tags=["env-surface"], claim names the var + the file(s) that reference it + "unreviewed env surface — confirm intended + regenerate the inventory"). One 8-field finding per STALE name (disposition=defer, risk_tags=["env-surface","docs"], claim "inventory references a name no longer in code — regenerate"). If status=fail-open (corrupt inventory) emit ONE finding disposition=fix naming the inventory file.
status: red if any NEW name (unreviewed surface is the live-risk class), yellow if only stale names or fail-open, green if clean.`,
  },
  {
    key: 'substrate-watch',
    brief: `Claude Code + Agent-SDK substrate drift (PLAN-135 W5 O12 — the heroic S214/S230 changelog sweep made permanent).
Context: when the upstream substrate (Claude Code CLI or the Agent SDKs) moves, assumptions baked against an older surface go silently stale (the S217/S228 silent-knob class). This dimension reports the substrate version the framework was last RECONCILED against vs what is installed/known — a maintenance prompt, never a defect.
1. If .claude/scripts/check-substrate-watch.py exists, run from the repo root: python3 .claude/scripts/check-substrate-watch.py --json --probe-installed (read-only; --probe-installed runs each component's documented version command — claude --version etc. — fail-soft; the script NEVER fetches the network or writes files). If the script or its ledger (.claude/scripts/substrate-watch.json) is missing, status=skipped with the reason. Do NOT run --refresh (that is the Owner-only step) and do NOT WebFetch anything — you are no-network.
2. Parse the JSON: status (current|stale-ledger|drift), source_stale, and per-component last_seen_version vs installed_version.
3. If status=stale-ledger, emit ONE finding (disposition=defer, evidence_kind=file_line, evidence_pointer=.claude/scripts/substrate-watch.json, risk_tags=["substrate"], claim "ledger never Owner-refreshed against the live changelog — run check-substrate-watch.py --refresh for the PENDING-OWNER recipe"). For each component with drift=true, emit ONE finding (disposition=defer, evidence_kind=test_run, evidence_pointer="check-substrate-watch --probe-installed", risk_tags=["substrate"], claim names the component + last_seen vs installed version + "re-run verify-the-knob-routes before trusting old assumptions").
status: yellow if stale-ledger or any drift (a maintenance signal — call it out), green if current.`,
  },
  {
    key: 'debt-ledger',
    brief: `Inline-debt ledger (PLAN-139 Wave B — advisory, derived, nightly-only).
Context: a structured "# CEO-DEBT: <ceiling>, <upgrade-trigger>" marker governs in-code shortcuts that sit BELOW the ADR/PLAN bar. A marker missing its upgrade-trigger is UNGOVERNED debt — it has no defined exit condition. 0 such markers exist today by design; this dimension surfaces them as they appear.
1. If .claude/scripts/check-debt-ledger.py exists, run from the repo root: python3 .claude/scripts/check-debt-ledger.py --json (read-only reporting script; greps first-party code for the marker grammar and emits a DERIVED ledger; never writes files; ALWAYS exits 0 — advisory). If the script is missing, status=skipped with the reason.
2. Parse the JSON: markers_count (total), ungoverned_count, and the markers list (each carries its file:line + whether it is governed).
3. One 8-field finding per UNGOVERNED marker (evidence_kind=file_line, evidence_pointer=<path>:<line>, disposition=defer, risk_tags=["debt"], claim names the marker location + "inline debt missing an upgrade-trigger — add a trigger or promote to a PLAN/ADR"). Mention the governed marker count in summary only (no finding for governed markers).
status: green if 0 markers OR every marker governed, yellow if any ungoverned marker. Advisory — NEVER red.`,
  },
]

const dimPrompt = (d) => `You are the "${d.key}" dimension of the nightly-hygiene read-only sweep (PLAN-134 W1).
Repo root: the current working directory (ceo-orchestration).

${READ_ONLY_RULES}

YOUR DIMENSION:
${d.brief}

8-FIELD FINDING CONTRACT (ADR-141, every finding MUST carry all 8):
finding_id="${d.key}-NN" (stable within this run), map_key="${d.key}", disposition (fix/accept/defer/moot),
evidence_kind, evidence_pointer (path:line / run id / redacted exemplar — NOT prose), confidence as INTEGER
basis points 0-10000 (never a float), risk_tags (short list), author="nightly-hygiene/${d.key}".
Also include file (path or "-") and claim (<=200 chars) on each finding for dedup.
Return ONLY the structured object.`

phase('Sweep')
log(`nightly-hygiene: ${DIMENSIONS.length} read-only dimension agents in parallel`)

const dims = await parallel(DIMENSIONS.map((d) => () =>
  agent(dimPrompt(d), { label: `hygiene:${d.key}`, phase: 'Sweep', schema: DIM_SCHEMA })
    // agent() RESOLVES null on terminal API error (never rejects) — .catch alone
    // misses it (PLAN-152 error-handling-03; crash class from run wf_071ef6c5).
    .then((r) => r || {
      dimension: d.key, status: 'skipped',
      summary: 'agent resolved null (terminal API error or user skip)', findings: [],
    })
    .catch((e) => ({
      dimension: d.key, status: 'skipped',
      summary: `agent error: ${String(e).slice(0, 200)}`, findings: [],
    }))))

phase('Synthesize')

const SYNTH_SCHEMA = {
  type: 'object',
  required: ['overall', 'report'],
  properties: {
    overall: { type: 'string', enum: ['green', 'yellow', 'red'] },
    report: { type: 'string' },
  },
}

const synth = await agent(`You are the nightly-hygiene synthesizer (read-only — use NO tools, write NO files).
Merge the ${dims.length} dimension results below into ONE markdown report:

${JSON.stringify(dims, null, 1)}

Report shape:
# Nightly hygiene — <overall status>
## Status board    (table: dimension | status | summary)
## Findings        (table: id | dimension | disposition | confidence(bps) | claim | evidence)
## Recommended next actions   (ordered, only for disposition=fix findings; cite finding ids)
Overall = red if any dimension red, else yellow if any yellow, else green (skipped counts as yellow and must be called out).
Do not invent findings; only restructure what the dimensions returned. Return ONLY the structured object.`,
  { label: 'hygiene:synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA })

// synth === null on terminal API error — degrade instead of crashing on
// null.overall (PLAN-152 error-handling-03).
const synthSafe = synth || {
  overall: 'yellow',
  report: '# Nightly hygiene — DEGRADED\n\nSynthesizer agent resolved null (terminal API error or user skip); '
    + 'per-dimension results are in `dimensions` below (skipped counts as yellow).',
}

return {
  overall: synthSafe.overall,
  report: synthSafe.report,
  dimensions: dims,
  confinement: 'ADR-136-AMEND-1 read-only fan-out; no agent wrote any file; report is a return value only.',
}
