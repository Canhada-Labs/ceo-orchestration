// test-council-fixture.mjs — PLAN-156 Wave 6 hermetic council test.
//
// The Cross-Vendor Audit Council transmits repo scope to xAI/OpenAI when it
// runs LIVE. Per the plan (debate C8 / R-OPS-3), CI must NEVER invoke a live
// lane — it may exercise ONLY the shard-parse + fail-loud degradation logic
// against FIXTURE lane outputs. This harness does exactly that: it loads
// council-audit.js with stubbed workflow globals (agent/parallel/phase/log)
// and injected FIXTURE lane outputs (args.fixture_lanes), so ZERO external
// egress happens and no vendor binary/secret is touched.
//
// It asserts the four things the council must get right when a lane dies:
//   1. an unavailable lane is SURFACED (fail-loud), never silently dropped;
//   2. the quorum DEGRADES explicitly (3-lane -> 2-lane, labeled);
//   3. a council with < 3 available lanes is NEVER verdict CLEAN;
//   4. a confirmed finding raised by only one vendor is flagged as a
//      cross-vendor DISAGREEMENT (the council's headline signal).
// PLAN-156-FOLLOWUP W2 (F2) adds the verify-stage split:
//   5. a refuter crash/null/omitted key synthesizes verify_failed (never
//      the explicit `unverifiable` judgment) and BLOCKS CLEAN;
//   6. explicit refute-everything / unverifiable judgments keep CLEAN
//      reachable at full quorum (split, not rename).
//
// Run: node scripts/tests/test-council-fixture.mjs   (exit 0 = pass)
// CI home for these semantics (debate C7): the Python structural twin
// .claude/scripts/tests/test_council_verify_semantics.py — this .mjs runs
// in no CI job and stays the local node behavioral harness.

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import { existsSync } from 'node:fs'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO = resolve(HERE, '..', '..')
// PLAN-156-FOLLOWUP W2: pre-ceremony the FIXED workflow lives under the
// plan's STAGED root; post-ceremony it is canonical. Resolution mirrors
// .claude/scripts/tests/test_council_verify_semantics.py (the CI-load-
// bearing Python twin — this .mjs runs in no CI job, debate C7):
//   1. $CEO_FU_STAGED_ROOT (repo-relative or absolute; set '.' to force
//      the canonical file explicitly);
//   2. the default staged root, if it holds the staged workflow;
//   3. the canonical path.
const REL = ['.claude', 'workflows', 'council-audit.js']
const DEFAULT_STAGED = resolve(REPO, '.claude', 'plans', 'PLAN-156-FOLLOWUP', 'staged', 'root')
const ENV_ROOT = process.env.CEO_FU_STAGED_ROOT
const ROOT = ENV_ROOT
  ? resolve(REPO, ENV_ROOT)
  : (existsSync(resolve(DEFAULT_STAGED, ...REL)) ? DEFAULT_STAGED : REPO)
const WORKFLOW = resolve(ROOT, ...REL)

// The workflow and this test land together (PLAN-156 SENT-GK-F), so in any
// committed state both are present. A clear message beats a raw ENOENT stack
// if someone runs this against a tree where the workflow has not landed yet.
if (!existsSync(WORKFLOW)) {
  console.error(`FATAL: council workflow not found at ${WORKFLOW}\n` +
    '  This test lands WITH council-audit.js under SENT-GK-F. If you see this\n' +
    '  pre-land, the workflow is still in .claude/plans/PLAN-156/staged/wave6/.')
  process.exit(1)
}

let PASS = 0
let FAIL = 0
const ok = (m) => { PASS++; console.log('PASS ', m) }
const bad = (m) => { FAIL++; console.error('FAIL ', m) }

// ---- workflow global stubs (no live egress) --------------------------------
function makeStubs(fixtureLanes, verifyVerdicts, reduceReport) {
  return {
    // agent() is called for: verify (refuter) + reduce (synth). In fixture
    // mode the LANE agents are NOT called (lanes come from args.fixture_lanes),
    // so any agent() call here is verify or reduce — return the canned result.
    agent: async (prompt, opts) => {
      const label = (opts && opts.label) || ''
      // verifyVerdicts === null simulates a refuter CRASH (agent resolved
      // null) — PLAN-156-FOLLOWUP F2 exercises this path.
      if (label === 'verify') return verifyVerdicts === null ? null : { verdicts: verifyVerdicts }
      if (label === 'reduce') return { verdict: 'FINDINGS', report: reduceReport }
      // A lane agent must NEVER be called in fixture mode — fail loudly.
      throw new Error(`unexpected live agent() call in fixture mode: label=${label}`)
    },
    parallel: async (thunks) => Promise.all(thunks.map((t) => t())),
    phase: () => {},
    log: () => {},
  }
}

async function runCouncil(args, stubs) {
  const src = readFileSync(WORKFLOW, 'utf-8')
  // Strip the `export const meta = {...}` (harness supplies its own scope) and
  // wrap the body in an async function with the globals + args injected.
  const body = src.replace(/export\s+const\s+meta\s*=\s*\{[\s\S]*?\n\}\n/, '')
  const fn = new Function(
    'args', 'agent', 'parallel', 'phase', 'log',
    `return (async () => { ${body} })()`,
  )
  return fn(args, stubs.agent, stubs.parallel, stubs.phase, stubs.log)
}

const mkFinding = (vendor, n, file, claim) => ({
  finding_id: `${vendor}-${n}`, map_key: 'security', disposition: 'fix',
  evidence_kind: 'file_line', evidence_pointer: `${file}:1`, confidence: 8000,
  risk_tags: ['sec'], author: `council/${vendor}`, file, claim, vendor,
})

// ===========================================================================
// Scenario A — one lane UNAVAILABLE (grok), two OK, one shared finding + one
// codex-only finding. Expect: fail-loud grok, 2-lane quorum, disagreement.
// ===========================================================================
{
  const shared = 'unsanitized subprocess input in foo.py'
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', shared)] },
    codex: { vendor: 'codex', status: 'ok', findings: [
      mkFinding('codex', 1, 'foo.py', shared),
      mkFinding('codex', 2, 'bar.py', 'fail-open on parse error in bar.py'),
    ] },
    grok: { vendor: 'grok', status: 'unavailable', unavailable_reason: 'subscription lapsed', findings: [] },
  }
  // verify confirms BOTH grouped findings (keys are `file|normalized-claim`).
  const key = (file, claim) => `${file}|${String(claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
  const verifyVerdicts = [
    { key: key('foo.py', shared), verdict: 'confirmed', evidence_check: 're-read foo.py:1' },
    { key: key('bar.py', 'fail-open on parse error in bar.py'), verdict: 'confirmed', evidence_check: 're-read bar.py:1' },
  ]
  const stubs = makeStubs(fixture_lanes, verifyVerdicts, '# council report')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)

  // 1. fail-loud: grok surfaced as unavailable with its reason.
  const grokUnavail = out.lanes.unavailable.find((u) => u.vendor === 'grok')
  if (grokUnavail && /subscription/.test(grokUnavail.reason)) ok('A1: grok lane surfaced unavailable with reason (fail-loud)')
  else bad(`A1: grok unavailable not surfaced: ${JSON.stringify(out.lanes)}`)

  // 2. quorum degraded to 2-lane, labeled.
  if (/2-lane/.test(out.quorum)) ok('A2: quorum degraded to 2-lane, labeled')
  else bad(`A2: quorum not labeled 2-lane: ${out.quorum}`)

  // 3. NOT CLEAN (only 2 lanes available) — and FINDINGS since confirmed>0.
  if (out.verdict === 'FINDINGS') ok('A3: verdict FINDINGS (confirmed>0, never CLEAN under partial quorum)')
  else bad(`A3: verdict expected FINDINGS, got ${out.verdict}`)

  // 4. the codex-only 'bar.py' finding is a cross-vendor DISAGREEMENT
  //    (raised by 1 of 2 available vendors); the shared foo.py one is not.
  const disagreeFiles = out.cross_vendor_disagreements.map((d) => d.file)
  if (disagreeFiles.includes('bar.py') && !disagreeFiles.includes('foo.py')) {
    ok('A4: codex-only finding flagged as cross-vendor disagreement; shared one is not')
  } else {
    bad(`A4: disagreement set wrong: ${JSON.stringify(disagreeFiles)}`)
  }
}

// ===========================================================================
// Scenario B — ALL lanes unavailable. Expect: 0-lane quorum, DEGRADED, no crash.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'unavailable', unavailable_reason: 'x', findings: [] },
    codex: { vendor: 'codex', status: 'unavailable', unavailable_reason: 'no binary', findings: [] },
    grok: { vendor: 'grok', status: 'unavailable', unavailable_reason: 'no auth', findings: [] },
  }
  const stubs = makeStubs(fixture_lanes, [], '# empty')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'DEGRADED') ok('B1: all-unavailable → DEGRADED (never CLEAN)')
  else bad(`B1: expected DEGRADED, got ${out.verdict}`)
  if (out.lanes.available.length === 0 && out.lanes.unavailable.length === 3) ok('B2: all 3 lanes surfaced unavailable (none silently dropped)')
  else bad(`B2: lane accounting wrong: ${JSON.stringify(out.lanes)}`)
}

// ===========================================================================
// Scenario C — full 3-lane quorum, zero findings. Expect CLEAN.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [] },
    codex: { vendor: 'codex', status: 'ok', findings: [] },
    grok: { vendor: 'grok', status: 'ok', findings: [] },
  }
  const stubs = makeStubs(fixture_lanes, [], '# clean')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'CLEAN') ok('C1: full 3-lane quorum + zero findings → CLEAN')
  else bad(`C1: expected CLEAN, got ${out.verdict}`)
}

// ===========================================================================
// Scenario D (PLAN-156-FOLLOWUP F2) — refuter CRASH (resolves null) with a
// full 3-lane quorum and raised findings. Pre-fix this laundered into
// unverifiable -> confirmed=0 -> mechanical CLEAN (the S270 false-green).
// Expect: every group verify_failed, verdict DEGRADED, loud banner.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'raised but never re-checked')] },
    codex: { vendor: 'codex', status: 'ok', findings: [] },
    grok: { vendor: 'grok', status: 'ok', findings: [] },
  }
  const stubs = makeStubs(fixture_lanes, null /* refuter crash */, '# crash')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'DEGRADED') ok('D1: refuter crash + raised findings → DEGRADED (never CLEAN)')
  else bad(`D1: expected DEGRADED, got ${out.verdict}`)
  if (out.stats.verify_failed === 1) ok('D2: crashed group counted as verify_failed in stats')
  else bad(`D2: stats.verify_failed expected 1, got ${JSON.stringify(out.stats)}`)
  const vf = (out.verify_failed_findings || [])[0]
  if (vf && vf.verdict === 'verify_failed' && vf.file === 'foo.py') ok('D3: group labeled verify_failed (a crash, NOT an unverifiable judgment)')
  else bad(`D3: verify_failed_findings wrong: ${JSON.stringify(out.verify_failed_findings)}`)
  if (/VERIFY_FAILED = 1/.test(out.report)) ok('D4: verify_failed count surfaced loudly at the top of the report')
  else bad('D4: report does not surface the verify_failed count')
}

// ===========================================================================
// Scenario E (PLAN-156-FOLLOWUP F2) — refuter RAN but OMITTED one group key.
// The judged group keeps its explicit verdict; the omitted one is
// verify_failed (synthesized default). Expect DEGRADED.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'claim one')] },
    codex: { vendor: 'codex', status: 'ok', findings: [mkFinding('codex', 1, 'bar.py', 'claim two')] },
    grok: { vendor: 'grok', status: 'ok', findings: [] },
  }
  const key = (file, claim) => `${file}|${String(claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
  // Verdict for foo.py only — bar.py's key is OMITTED.
  const verifyVerdicts = [
    { key: key('foo.py', 'claim one'), verdict: 'refuted', evidence_check: 're-read foo.py:1 — stale' },
  ]
  const stubs = makeStubs(fixture_lanes, verifyVerdicts, '# omission')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'DEGRADED') ok('E1: omitted group key → DEGRADED (never CLEAN)')
  else bad(`E1: expected DEGRADED, got ${out.verdict}`)
  const vfFiles = (out.verify_failed_findings || []).map((g) => g.file)
  if (out.stats.verify_failed === 1 && vfFiles.includes('bar.py') && !vfFiles.includes('foo.py')) {
    ok('E2: ONLY the omitted group is verify_failed; the explicitly judged one is not')
  } else {
    bad(`E2: verify_failed split wrong: stats=${JSON.stringify(out.stats)} files=${JSON.stringify(vfFiles)}`)
  }
}

// ===========================================================================
// Scenario F (PLAN-156-FOLLOWUP F2) — legitimate refute-everything: the
// refuter RAN and explicitly refuted every group. confirmed=0 AND
// verify_failed=0 at full quorum → CLEAN must stay REACHABLE.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'stale claim')] },
    codex: { vendor: 'codex', status: 'ok', findings: [mkFinding('codex', 1, 'bar.py', 'another stale claim')] },
    grok: { vendor: 'grok', status: 'ok', findings: [] },
  }
  const key = (file, claim) => `${file}|${String(claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
  const verifyVerdicts = [
    { key: key('foo.py', 'stale claim'), verdict: 'refuted', evidence_check: 're-read foo.py:1 — code moved' },
    { key: key('bar.py', 'another stale claim'), verdict: 'refuted', evidence_check: 're-read bar.py:1 — fixed in HEAD' },
  ]
  const stubs = makeStubs(fixture_lanes, verifyVerdicts, '# refuted all')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'CLEAN' && out.stats.verify_failed === 0) ok('F1: explicit refute-everything at full quorum → CLEAN stays reachable')
  else bad(`F1: expected CLEAN with verify_failed=0, got ${out.verdict} / ${JSON.stringify(out.stats)}`)
}

// ===========================================================================
// Scenario G (PLAN-156-FOLLOWUP F2) — an EXPLICIT refuter `unverifiable`
// judgment stays `unverifiable`: it is a judgment, not a crash, so it does
// NOT count as verify_failed and does NOT block CLEAN at full quorum.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'gone.py', 'pointer into a deleted file')] },
    codex: { vendor: 'codex', status: 'ok', findings: [] },
    grok: { vendor: 'grok', status: 'ok', findings: [] },
  }
  const key = (file, claim) => `${file}|${String(claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
  const verifyVerdicts = [
    { key: key('gone.py', 'pointer into a deleted file'), verdict: 'unverifiable', evidence_check: 'gone.py absent — cannot check read-only' },
  ]
  const stubs = makeStubs(fixture_lanes, verifyVerdicts, '# unverifiable')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.stats.verify_failed === 0 && out.verdict === 'CLEAN') ok('G1: explicit unverifiable judgment is NOT verify_failed (split, not rename) — CLEAN preserved')
  else bad(`G1: expected CLEAN with verify_failed=0, got ${out.verdict} / ${JSON.stringify(out.stats)}`)
}

// ===========================================================================
// Source-contract guards — the four BLOCKING invariants must be present in
// the workflow source (RED-on-absence if a future edit strips them).
// ===========================================================================
{
  const src = readFileSync(WORKFLOW, 'utf-8')
  if (/codex_egress_redact/.test(src)) ok('SRC1: ADR-114 egress redactor referenced (invariant 1)')
  else bad('SRC1: egress redactor call MISSING — external lanes could send unredacted')
  if (/--sandbox read-only/.test(src) && /--sandbox council/.test(src)) ok('SRC2: OS read-only containment flags present for both CLI lanes (invariant 2)')
  else bad('SRC2: OS sandbox flags MISSING for a CLI lane')
  if (/status:\s*['"]unavailable['"]|status:\s*"unavailable"|'unavailable'/.test(src)) ok('SRC3: fail-loud STATUS unavailable present (invariant 3)')
  else bad('SRC3: fail-loud unavailable path MISSING')
  if (/IS_FIXTURE_MODE|fixture_lanes/.test(src)) ok('SRC4: fixture-mode branch present (CI can test without live egress, invariant 4)')
  else bad('SRC4: fixture-mode branch MISSING — CI cannot test without live egress')
  // PLAN-156-FOLLOWUP W2 additions:
  if (/set -o pipefail/.test(src) && /codex_egress_redact\.py --outgoing \| \$\{cli\}/.test(src)) {
    ok('SRC5: redact-and-send is ONE pipeline under pipefail (pipe fold)')
  } else bad('SRC5: redactor | vendor-cli pipe fold MISSING — a skipped redaction could yield a sendable prompt')
  if (/verifyFailed\.length === 0/.test(src)) ok('SRC6: CLEAN mechanically gated on verify_failed==0 (F2)')
  else bad('SRC6: CLEAN condition does NOT include verify_failed==0 — refuter crash could launder into CLEAN')
}

console.log(`\n==> Results: ${PASS} passed, ${FAIL} failed`)
process.exit(FAIL === 0 ? 0 : 1)
