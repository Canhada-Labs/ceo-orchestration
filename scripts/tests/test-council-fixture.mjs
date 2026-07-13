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
//
// Run: node scripts/tests/test-council-fixture.mjs   (exit 0 = pass)

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

import { existsSync } from 'node:fs'

const HERE = dirname(fileURLToPath(import.meta.url))
const REPO = resolve(HERE, '..', '..')
const WORKFLOW = resolve(REPO, '.claude', 'workflows', 'council-audit.js')

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
      if (label === 'verify') return { verdicts: verifyVerdicts }
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
}

console.log(`\n==> Results: ${PASS} passed, ${FAIL} failed`)
process.exit(FAIL === 0 ? 0 : 1)
