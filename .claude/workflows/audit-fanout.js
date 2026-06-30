export const meta = {
  name: 'audit-fanout',
  description: 'Read-only audit fan-out in the S185/S225 shape (PLAN-134 W1 item 4): 8 parallel finder agents (one per audit dimension) return evidence-backed findings as ADR-141 8-field shards; deterministic dedup by file+claim; every surviving finding is ADVERSARIALLY re-verified by a per-dimension refuter (REDUCE = evidence-bound verification, never a summary merge — docs/triage-reduce-protocol.md); synthesis returns verdict + findings table. ADR-136-AMEND-1 confinement: agents write NO files; the report is a return value. args: {scope: "<subtree or topic>", default whole repo}.',
  phases: [{ title: 'Find' }, { title: 'Refute' }, { title: 'Synthesize' }],
}

const SCOPE = (typeof args === 'object' && args !== null && typeof args.scope === 'string' && args.scope) ? args.scope : '.'
const MAX_FINDINGS_PER_DIM = 8 // scale the PROOF surface, not the finding count (ADR-141)

const READ_ONLY_RULES = `HARD RULES (ADR-136-AMEND-1 read-only confinement):
- READ-ONLY investigator: NEVER Edit/Write/NotebookEdit; write NO files anywhere (not even /tmp).
- Bash only for read-only commands (grep/ls/cat/git log|status|diff/python3 -m py_compile/pytest --collect-only). No redirections into files, no mutations.
- Evidence or it does not exist: every finding needs a checkable evidence_pointer (path:line, grep pattern, test id, audit finding id) — prose is not evidence.
- Report ONLY via the structured return value; redact secrets/handles.`

// ADR-141 mandatory 8-field shard schema + `file`/`claim` dedup keys (extras allowed).
const FINDING_SCHEMA = {
  type: 'object',
  required: ['finding_id', 'map_key', 'disposition', 'evidence_kind',
    'evidence_pointer', 'confidence', 'risk_tags', 'author', 'file', 'claim'],
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
const FINDER_SCHEMA = {
  type: 'object',
  required: ['dimension', 'findings'],
  properties: {
    dimension: { type: 'string' },
    findings: { type: 'array', items: FINDING_SCHEMA },
  },
}

const DIMENSIONS = [
  { key: 'security', brief: 'Injection surfaces, secret/credential handling, fail-open vs fail-closed mistakes, path traversal, subprocess/shell construction, trust-boundary crossings.' },
  { key: 'governance', brief: 'Canonical-guard coverage gaps, spawn-protocol compliance, audit-emit contract drift (_KNOWN_ACTIONS vs SPEC), plan/ADR lifecycle violations, hook registration vs settings drift.' },
  { key: 'tests', brief: 'Untested load-bearing modules, env-hygiene violations (bare os.environ in tests), flake patterns, assertions pinning stale state, coverage holes on Tier-1 hooks.' },
  { key: 'docs', brief: 'Doc claims contradicting code reality (counts, paths, behavior), stale how-to commands, README/INSTALL drift vs derived counts.' },
  { key: 'economics', brief: 'Token/quota waste: oversized always-loaded context, redundant fan-out, hooks doing heavy work per event, cache-invalidating edit patterns, missing batching.' },
  { key: 'dead-code', brief: 'Unreferenced modules/scripts/fixtures, orphaned config keys, hooks on disk but not registered, plans/dirs left behind by shipped work.' },
  { key: 'error-handling', brief: 'Swallowed exceptions hiding real failures, breadcrumbs that echo rejected values, fail-open paths that should be fail-closed (and vice versa per §5 fail-open-on-infra doctrine).' },
  { key: 'dependencies', brief: 'stdlib-only violations, Python <3.9 incompat (runtime PEP 604, match), bash-3.2 unsafe constructs (mapfile, declare -A) in scripts meant for macOS.' },
]

const finderPrompt = (d) => `You are the "${d.key}" finder of an audit fan-out (S185/S225 shape) over SCOPE: ${SCOPE}
Repo root = current working directory (ceo-orchestration).

${READ_ONLY_RULES}

DIMENSION: ${d.brief}

Investigate the scope for THIS dimension only. Quality over quantity: at most ${MAX_FINDINGS_PER_DIM} findings,
each one independently checkable. Skip anything CLAUDE.md/plans already document as known/deferred
(that is "accept" disposition with the doc pointer as evidence, or simply omit).

8-FIELD CONTRACT (ADR-141 — every finding carries ALL of):
finding_id="${d.key}-NN", map_key="${d.key}", disposition (fix/accept/defer/moot),
evidence_kind (file_line/grep/test_run/audit_event/none), evidence_pointer (path:line or
exact grep — NOT prose), confidence as INTEGER basis points 0-10000 (never a float),
risk_tags, author="audit-fanout/${d.key}", plus file (primary path, "-" if repo-wide)
and claim (<=200 chars, the falsifiable assertion a refuter can re-check).
Return ONLY {dimension, findings}. Zero findings is a valid (good) result.`

phase('Find')
log(`audit-fanout: scope=${SCOPE} — ${DIMENSIONS.length} read-only finders in parallel`)

const finderResults = await parallel(DIMENSIONS.map((d) => () =>
  agent(finderPrompt(d), { label: `find:${d.key}`, phase: 'Find', schema: FINDER_SCHEMA })
    .catch((e) => ({ dimension: d.key, findings: [], finder_error: String(e).slice(0, 200) }))))

// Deterministic dedup by file+claim (normalized) BEFORE verification spend.
const seen = {}
const deduped = []
let dupCount = 0
for (const fr of finderResults) {
  for (const f of fr.findings) {
    const key = `${f.file}|${String(f.claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
    if (seen[key]) {
      dupCount += 1
      seen[key].dup_of_dimensions = (seen[key].dup_of_dimensions || []).concat(f.map_key)
    } else {
      seen[key] = f
      deduped.push(f)
    }
  }
}
log(`audit-fanout: ${deduped.length} unique findings after dedup (${dupCount} cross-dimension dups folded)`)

phase('Refute')

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['verdicts'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['finding_id', 'verdict', 'evidence_check'],
        properties: {
          finding_id: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'refuted', 'unverifiable'] },
          evidence_check: { type: 'string' },
        },
      },
    },
  },
}

const refuterPrompt = (dim, items) => `You are an ADVERSARIAL refuter (audit-fanout REDUCE step, dimension "${dim}").
Your job is to KILL findings, not to summarize them: PLAN-114 showed ~57% of unverified findings are stale.

${READ_ONLY_RULES}

For EACH finding below, independently re-check its evidence_pointer FIRST-HAND (open the file at the
line, re-run the grep, collect the test — read-only) and judge the CLAIM, not the prose:
- confirmed    = evidence exists AND supports the claim as stated
- refuted      = evidence missing, stale, or does not support the claim (say exactly what you saw instead)
- unverifiable = the pointer cannot be checked read-only (treat evidence_kind=none claims harshly)
Accepting without re-checking evidence is prose-laundering (ADR-141 P0). evidence_check = what you
actually ran/read, <=200 chars.

FINDINGS:
${JSON.stringify(items, null, 1)}

Return ONLY {verdicts} with exactly one verdict per finding_id above.`

const byDim = {}
for (const f of deduped) {
  if (!byDim[f.map_key]) byDim[f.map_key] = []
  byDim[f.map_key].push(f)
}
const refuteDims = Object.keys(byDim).sort()

const refuteResults = await parallel(refuteDims.map((dim) => () =>
  agent(refuterPrompt(dim, byDim[dim]), { label: `refute:${dim}`, phase: 'Refute', schema: VERDICT_SCHEMA })
    .catch((e) => ({
      verdicts: byDim[dim].map((f) => ({
        finding_id: f.finding_id, verdict: 'unverifiable',
        evidence_check: `refuter error: ${String(e).slice(0, 160)}`,
      })),
    }))))

const verdictById = {}
for (const rr of refuteResults) for (const v of rr.verdicts) verdictById[v.finding_id] = v
const merged = deduped.map((f) => ({
  ...f,
  verdict: (verdictById[f.finding_id] || { verdict: 'unverifiable', evidence_check: 'no refuter verdict returned' }).verdict,
  evidence_check: (verdictById[f.finding_id] || { evidence_check: 'no refuter verdict returned' }).evidence_check,
}))
const confirmed = merged.filter((f) => f.verdict === 'confirmed')
const refuted = merged.filter((f) => f.verdict === 'refuted')
const unverifiable = merged.filter((f) => f.verdict === 'unverifiable')

phase('Synthesize')

const SYNTH_SCHEMA = {
  type: 'object',
  required: ['verdict', 'report'],
  properties: {
    verdict: { type: 'string', enum: ['CLEAN', 'FINDINGS', 'DEGRADED'] },
    report: { type: 'string' },
  },
}

const synth = await agent(`You are the audit-fanout synthesizer (use NO tools, write NO files).
Scope: ${SCOPE}. Adversarially-verified results:
- confirmed: ${JSON.stringify(confirmed, null, 1)}
- refuted (count ${refuted.length}): ${JSON.stringify(refuted.map((f) => ({ finding_id: f.finding_id, claim: f.claim, evidence_check: f.evidence_check })), null, 1)}
- unverifiable (count ${unverifiable.length}): ${JSON.stringify(unverifiable.map((f) => ({ finding_id: f.finding_id, claim: f.claim })), null, 1)}

Produce a markdown report:
# Audit fan-out — ${SCOPE}
## Verdict        (CLEAN = zero confirmed; FINDINGS = confirmed findings exist; DEGRADED = unverifiable > confirmed, audit quality suspect)
## Confirmed findings   (table: id | dimension | disposition | confidence(bps) | file | claim | evidence)
## Refuted at REDUCE    (table: id | claim | what the refuter actually found — these are the saved false-positives)
## Unverifiable         (list, with why)
## Recommended next actions   (only from confirmed disposition=fix, ordered by risk_tags severity)
Restructure only — invent NOTHING beyond the verdict rule above. Return ONLY {verdict, report}.`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA })

return {
  scope: SCOPE,
  verdict: synth.verdict,
  report: synth.report,
  stats: {
    raw_findings: finderResults.reduce((n, fr) => n + fr.findings.length, 0),
    dedup_folded: dupCount,
    confirmed: confirmed.length,
    refuted: refuted.length,
    unverifiable: unverifiable.length,
  },
  confirmed_findings: confirmed,
  confinement: 'ADR-136-AMEND-1 read-only fan-out; ADR-141 8-field shards + adversarial REDUCE; no file writes.',
}
