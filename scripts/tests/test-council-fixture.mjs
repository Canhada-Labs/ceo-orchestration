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
// PLAN-161 C2/C3 replace the universal pipe-fold source guard (SRC5) with
// vendor-specific transport guards: codex keeps the redactor pipe fold
// into a WATCHDOG-WRAPPED CLI (mechanical scope-aware budget); grok uses
// a 0600 artifact + fixed pointer argv (grok 0.2.93 -p cannot read
// stdin). The behavioral money-oracle for the grok compose block is
// scripts/tests/test-council-grok-artifact.sh.
// PLAN-161 W2 (codex r1 F3/F4) adds the attestation demotion gate:
//   7. a status-ok grok lane WITHOUT a well-formed artifact_sha256
//      (64 lowercase hex) is DEMOTED to unavailable before quorum
//      (scenario H); a valid attestation keeps CLEAN reachable and is
//      threaded into the report (scenario I);
//   8. the fixture-only ARTIFACT_KEEP_DIR env redirect is GONE (SRC8).
// PLAN-161 W2 fix-round-2 (codex r2 F12/F13):
//   9. the grok compose mkdtemp + stale sweep are pinned to the fixed /tmp
//      base — the TMPDIR-honoring `mktemp -d -t` form is gone, so an
//      inherited TMPDIR can neither relocate the artifact into the repo
//      nor aim the sweep's rm -rf at repo dirs (SRC5h);
//  10. lane vendor identity is canonicalized to the REQUESTED_VENDORS
//      position and written back onto the lane object — a lane whose
//      model-written vendor differs from its requested position cannot
//      impersonate another vendor downstream (scenario J, SRC9).
// PLAN-161 W2 fix-round-3 (codex r3 F3):
//  11. the operator-controlled scope is POSIX shell-quoted (shq) before
//      interpolation into the codex-lane shell source — a scope carrying
//      a single quote arrives as ONE inert argv token to git ls-files and
//      cannot break out of the quoting to inject commands into the
//      redactor/vendor pipeline block (scenario K, SRC10).
// PLAN-161 W2 fix-round-4 (codex r4 F3):
//  12. the injection guard is BEHAVIORAL, not just a string compare
//      (scenario K2): the rendered codex shell block must `bash -n` clean
//      with the hostile scope embedded; the rendered budget line is then
//      EXECUTED in a throwaway mkdtemp sandbox and the injected marker
//      file must be ABSENT afterward; and a counter-proof executes the
//      SAME line rendered the pre-fix way (raw '${SCOPE}', shq bypassed)
//      and asserts the marker DOES appear — proving the marker-absence
//      oracle is load-bearing (RED-on-unfixed), not vacuous.
//
// Run: node scripts/tests/test-council-fixture.mjs   (exit 0 = pass)
// CI home for these semantics (debate C7): the Python structural twin
// .claude/scripts/tests/test_council_verify_semantics.py — this .mjs runs
// in no CI job and stays the local node behavioral harness.

import { readFileSync, mkdtempSync, rmSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, join } from 'node:path'
import { tmpdir } from 'node:os'
import { execFileSync } from 'node:child_process'

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

// PLAN-161 W2 (codex r1 F3): the attestation demotion gate applies in
// fixture mode too, so a status-ok grok FIXTURE lane must carry a valid
// (dummy) 64-lowercase-hex artifact_sha256 — scenario H covers the
// demotion path itself.
const GROK_SHA = 'ab'.repeat(32)

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
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
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
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
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
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
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
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
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
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
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
// Scenario H (PLAN-161 W2, codex r1 F3) — a grok lane claims status ok but
// the artifact attestation is MISSING (run 1) or MALFORMED (run 2). The
// artifact transport is then unattested (ADR-114), so the lane must be
// DEMOTED to unavailable BEFORE quorum/verdict: findings discarded, quorum
// degraded to a labeled 2-lane, verdict never CLEAN, no sha in the report.
// ===========================================================================
for (const [tag, sha] of [['missing', undefined], ['malformed', 'DEADBEEF-not-64-lowercase-hex']]) {
  const grokLane = { vendor: 'grok', status: 'ok',
    findings: [mkFinding('grok', 1, 'sneak.py', 'finding from an unattested lane')] }
  if (sha !== undefined) grokLane.artifact_sha256 = sha
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [] },
    codex: { vendor: 'codex', status: 'ok', findings: [] },
    grok: grokLane,
  }
  const stubs = makeStubs(fixture_lanes, [], '# unattested')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  const grokU = out.lanes.unavailable.find((u) => u.vendor === 'grok')
  if (grokU && /artifact attestation/.test(grokU.reason)) ok(`H1(${tag}): unattested grok ok-lane DEMOTED to unavailable; reason names the attestation`)
  else bad(`H1(${tag}): grok not demoted / reason wrong: ${JSON.stringify(out.lanes)}`)
  if (/2-lane/.test(out.quorum) && !out.lanes.available.includes('grok')) ok(`H2(${tag}): quorum degraded to labeled 2-lane without grok`)
  else bad(`H2(${tag}): quorum/availability wrong: ${out.quorum} / ${JSON.stringify(out.lanes.available)}`)
  if (out.verdict === 'DEGRADED' && out.stats.raw_findings === 0) ok(`H3(${tag}): demoted lane's findings discarded; verdict DEGRADED (never CLEAN)`)
  else bad(`H3(${tag}): expected DEGRADED with raw_findings=0, got ${out.verdict} / ${JSON.stringify(out.stats)}`)
  if (!(out.lanes.artifact_sha256 && 'grok' in out.lanes.artifact_sha256)) ok(`H4(${tag}): no grok attestation leaks into the run report`)
  else bad(`H4(${tag}): demoted lane still reports artifact_sha256: ${JSON.stringify(out.lanes.artifact_sha256)}`)
}

// ===========================================================================
// Scenario I (PLAN-161 W2, codex r1 F3) — the attested twin of scenario H:
// a VALID dummy sha keeps the grok lane counted (CLEAN stays reachable) and
// the attestation is threaded into the run report's lanes mapping.
// ===========================================================================
{
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [] },
    codex: { vendor: 'codex', status: 'ok', findings: [] },
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
  }
  const stubs = makeStubs(fixture_lanes, [], '# attested clean')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.verdict === 'CLEAN' && out.lanes.available.includes('grok')) ok('I1: attested grok lane counts — CLEAN reachable at full quorum')
  else bad(`I1: expected CLEAN with grok available, got ${out.verdict} / ${JSON.stringify(out.lanes.available)}`)
  if (out.lanes.artifact_sha256 && out.lanes.artifact_sha256.grok === GROK_SHA) ok('I2: grok attestation threaded into lanes.artifact_sha256')
  else bad(`I2: attestation missing from report: ${JSON.stringify(out.lanes.artifact_sha256)}`)
}

// ===========================================================================
// Scenario J (PLAN-161 W2 fix-round-2, codex r2 F13) — vendor impersonation
// neutralized. A lane's model-written vendor field is UNTRUSTED: identity is
// the REQUESTED_VENDORS position, and the canonical identity is written back
// onto the lane object so ALL downstream consumers (attribution,
// availability, disagreements, the attestation map) see it. Here the
// codex-POSITION lane claims vendor:"grok" (with a plausible sha) and stamps
// its finding vendor:"grok" too. Expect: the lane counts as codex,
// attribution says codex, and the true grok lane's attestation is intact.
// ===========================================================================
{
  const impersonator = {
    vendor: 'grok', status: 'ok', artifact_sha256: 'cd'.repeat(32),
    findings: [mkFinding('grok', 1, 'imp.py', 'finding from an impersonating lane')],
  }
  const fixture_lanes = {
    claude: { vendor: 'claude', status: 'ok', findings: [] },
    codex: impersonator, // the codex-position lane lies about its vendor
    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
  }
  const key = (file, claim) => `${file}|${String(claim).toLowerCase().replace(/\s+/g, ' ').trim()}`
  const verifyVerdicts = [
    { key: key('imp.py', 'finding from an impersonating lane'), verdict: 'confirmed', evidence_check: 're-read imp.py:1' },
  ]
  const stubs = makeStubs(fixture_lanes, verifyVerdicts, '# impersonation')
  const out = await runCouncil({ scope: '.', fixture_lanes }, stubs)
  if (out.lanes.available.length === 3
      && out.lanes.available[1] === 'codex'
      && out.lanes.available.filter((v) => v === 'grok').length === 1) {
    ok('J1: codex-position lane canonicalized to codex — no duplicate grok in availability')
  } else bad(`J1: availability wrong: ${JSON.stringify(out.lanes.available)}`)
  const conf = (out.confirmed_findings || []).find((g) => g.file === 'imp.py')
  if (conf && conf.raised_by.length === 1 && conf.raised_by[0] === 'codex') {
    ok('J2: finding attribution follows the canonical lane identity (codex), not the model-written grok')
  } else bad(`J2: attribution wrong: ${JSON.stringify(conf && conf.raised_by)}`)
  if (out.lanes.artifact_sha256 && out.lanes.artifact_sha256.grok === GROK_SHA) {
    ok('J3: true grok attestation not displaced by the impersonating lane')
  } else bad(`J3: attestation map wrong: ${JSON.stringify(out.lanes.artifact_sha256)}`)
}

// ===========================================================================
// Scenario K (PLAN-161 W2 fix-round-3, codex r3 F3) — shell injection via a
// quote-bearing scope is neutralized. NON-fixture mode renders the REAL
// external-lane orchestration prompts; the stub agent captures the codex
// lane's prompt (returning every lane unavailable, so zero live egress and
// no vendor CLI is touched). The operator-controlled scope must arrive in
// the `git ls-files` budget line POSIX-quoted — one inert argv token — and
// the raw single-quoted interpolation must be gone. The scope legitimately
// appears RAW inside the fenced BRIEF (redacted data, not shell source), so
// the assertions target the shell line, not the whole prompt.
// ===========================================================================
{
  const HOSTILE = "x'; touch /tmp/council-injected; echo '"
  let codexPrompt = null
  const stubs = {
    agent: async (prompt, opts) => {
      const label = (opts && opts.label) || ''
      if (label === 'lane:codex') codexPrompt = prompt
      if (label.startsWith('lane:')) {
        const vendor = label.slice('lane:'.length)
        return { vendor, status: 'unavailable', unavailable_reason: 'prompt captured (hermetic test — no live egress)', findings: [] }
      }
      if (label === 'verify') return { verdicts: [] }
      if (label === 'reduce') return { verdict: 'DEGRADED', report: '# capture' }
      throw new Error(`unexpected agent label: ${label}`)
    },
    parallel: async (thunks) => Promise.all(thunks.map((t) => t())),
    phase: () => {},
    log: () => {},
  }
  const out = await runCouncil({ scope: HOSTILE }, stubs)
  // The POSIX-quoted form: whole string in single quotes, each embedded
  // single quote as the close-escape-reopen sequence.
  const q = "'" + HOSTILE.replace(/'/g, "'\\''") + "'"
  const nLine = codexPrompt ? ((codexPrompt.match(/^N=\$\( git ls-files [^\n]*$/m) || [])[0] || '') : ''
  const expected = `N=$( git ls-files -- ${q} 2>/dev/null | wc -l | tr -d ' ' ); [ -n "$N" ] || N=0`
  if (codexPrompt && nLine === expected) {
    ok('K1: quote-bearing scope arrives POSIX-quoted in the git ls-files budget line (one inert argv token)')
  } else {
    bad(`K1: budget line not safely quoted: ${JSON.stringify(nLine)}`)
  }
  if (codexPrompt && !codexPrompt.includes(`git ls-files -- '${HOSTILE}'`)) {
    ok('K2: raw single-quoted scope interpolation absent — the embedded quote cannot close the shell quoting')
  } else {
    bad('K2: raw interpolation of the hostile scope still present in the codex-lane shell source')
  }
  if (out && out.verdict === 'DEGRADED' && out.scope === HOSTILE) {
    ok('K3: run completes (all lanes unavailable → DEGRADED); scope round-trips as DATA in the return value')
  } else {
    bad(`K3: unexpected run shape: verdict=${out && out.verdict}`)
  }
}

// ===========================================================================
// Scenario K2 (PLAN-161 W2 fix-round-4, codex r4 F3) — BEHAVIORAL injection
// proof. Scenario K's checks are string comparisons on the rendered N= line;
// this scenario runs REAL shell against the REAL rendered bytes:
//   (a) `bash -n` PARSES the full rendered codex shell block clean — the
//       quote-bearing scope cannot even unbalance the block's syntax;
//   (b) the rendered budget line is EXECUTED in a throwaway mkdtemp sandbox
//       with an injection payload aimed at a marker file inside that
//       sandbox — afterward the marker must NOT exist (the injected `touch`
//       never ran; the payload stayed one inert argv token);
//   (c) COUNTER-PROOF (RED-on-unfixed): the SAME line rendered the pre-fix
//       way — raw '${SCOPE}' interpolation, shq bypassed — DOES create the
//       marker when executed, proving the (b) oracle is load-bearing.
// Only mkdtemp tmp paths are written; the repo tree is never touched. The
// redactor/vendor CLI lines are PARSED by (a) but never executed — only the
// git-ls-files budget line runs, so zero egress and zero vendor calls.
// ===========================================================================
{
  const SBX = mkdtempSync(join(tmpdir(), 'council-k2-'))
  try {
    const MARKER = join(SBX, 'injected.marker')
    const HOSTILE = `x'; touch ${MARKER}; echo '`
    let codexPrompt = null
    const stubs = {
      agent: async (prompt, opts) => {
        const label = (opts && opts.label) || ''
        if (label === 'lane:codex') codexPrompt = prompt
        if (label.startsWith('lane:')) {
          const vendor = label.slice('lane:'.length)
          return { vendor, status: 'unavailable', unavailable_reason: 'prompt captured (hermetic test — no live egress)', findings: [] }
        }
        if (label === 'verify') return { verdicts: [] }
        if (label === 'reduce') return { verdict: 'DEGRADED', report: '# capture' }
        throw new Error(`unexpected agent label: ${label}`)
      },
      parallel: async (thunks) => Promise.all(thunks.map((t) => t())),
      phase: () => {},
      log: () => {},
    }
    await runCouncil({ scope: HOSTILE }, stubs)
    const block = codexPrompt ? ((codexPrompt.match(/^set -o pipefail\n[\s\S]*?^fi$/m) || [])[0] || '') : ''
    const nLine = codexPrompt ? ((codexPrompt.match(/^N=\$\( git ls-files [^\n]*$/m) || [])[0] || '') : ''

    // (a) the full rendered shell block must PARSE clean under bash -n.
    let parseClean = false
    if (block) {
      try {
        execFileSync('bash', ['-n', '-c', block], { stdio: ['ignore', 'ignore', 'pipe'] })
        parseClean = true
      } catch { parseClean = false }
    }
    if (parseClean) ok('K2a: bash -n parses the FULL rendered codex shell block CLEAN with the hostile scope embedded (exit 0)')
    else bad(`K2a: rendered block missing or fails bash -n: ${JSON.stringify(block.slice(0, 120))}`)

    // (b) EXECUTE the rendered budget line in the sandbox — the injected
    // touch must never run. (git ls-files fails harmlessly outside a repo;
    // the marker is the oracle.)
    let execOk = false
    if (nLine) {
      try {
        execFileSync('bash', ['-c', nLine], { cwd: SBX, stdio: ['ignore', 'ignore', 'ignore'] })
        execOk = true
      } catch { execOk = false }
    }
    if (execOk && !existsSync(MARKER)) ok('K2b: rendered budget line EXECUTED (exit 0) — injected marker ABSENT: the payload never ran under shq')
    else bad(`K2b: behavioral exec wrong: execOk=${execOk} markerExists=${existsSync(MARKER)}`)

    // (c) counter-proof: the pre-fix render — SCOPE interpolated RAW between
    // single quotes (this JS template literal reproduces those exact bytes,
    // shq bypassed) — DOES execute the payload. RED-on-unfixed by
    // construction: if (b)'s oracle were vacuous, this marker check fails.
    const rawLine = `N=$( git ls-files -- '${HOSTILE}' 2>/dev/null | wc -l | tr -d ' ' ); [ -n "$N" ] || N=0`
    try {
      execFileSync('bash', ['-c', rawLine], { cwd: SBX, stdio: ['ignore', 'ignore', 'ignore'] })
    } catch { /* exit status irrelevant — the marker is the oracle */ }
    if (existsSync(MARKER)) ok('K2c: COUNTER-PROOF — same line with shq bypassed (raw interpolation) DOES create the marker: the K2b oracle is load-bearing')
    else bad('K2c: counter-proof failed — raw interpolation did not execute the payload; the K2b marker oracle may be vacuous')
  } finally {
    rmSync(SBX, { recursive: true, force: true })
  }
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
  // PLAN-161 C2/C3 (supersedes the PLAN-156-FOLLOWUP universal pipe fold):
  // ONE redaction chokepoint, TWO vendor transports. codex — redactor
  // stdout pipes into the WATCHDOG-WRAPPED codex CLI; grok — redactor
  // stdout becomes a 0600 artifact + fixed pointer argv (grok 0.2.93 -p
  // cannot read stdin, so the old universal `--outgoing | ${cli}` shape
  // must be GONE: unwrapped codex is unbounded burn, piped grok is dead).
  if (/set -o pipefail/.test(src)
      && /codex_egress_redact\.py --outgoing \| "\$TOUT" -k 10 "\$BUDGET_S" \$\{cli\}/.test(src)
      && /codex_egress_redact\.py --outgoing \| python3 -c '/.test(src)) {
    ok('SRC5a: codex lane keeps the redactor pipe fold into the watchdog-wrapped CLI (both wrapper branches)')
  } else bad('SRC5a: codex redactor|watchdog-wrapped-cli pipe fold MISSING')
  if (!/codex_egress_redact\.py --outgoing \| \$\{cli\}/.test(src)) {
    ok('SRC5b: old universal unwrapped `--outgoing | ${cli}` transport removed')
  } else bad('SRC5b: unwrapped `--outgoing | ${cli}` still present (unbounded codex / dead grok pipe)')
  const beginCount = (src.match(/# --- GROK-ARTIFACT-COMPOSE BEGIN ---/g) || []).length
  const endCount = (src.match(/# --- GROK-ARTIFACT-COMPOSE END ---/g) || []).length
  if (beginCount === 1 && endCount === 1) ok('SRC5c: exactly one grok artifact compose block (markers)')
  else bad(`SRC5c: marker counts wrong: BEGIN=${beginCount} END=${endCount}`)
  const gbm = src.match(/# --- GROK-ARTIFACT-COMPOSE BEGIN ---([\s\S]*?)# --- GROK-ARTIFACT-COMPOSE END ---/)
  const gb = gbm ? gbm[1] : ''
  if (/--outgoing > \$ART_DIR\/brief\.tmp/.test(gb)
      && /chmod 600 \$ART_DIR\/brief\.tmp/.test(gb)
      && /mv \$ART_DIR\/brief\.tmp \$ART_DIR\/brief\.txt/.test(gb)
      && /umask 077/.test(gb) && /mktemp -d \/tmp\/ceo-council-grok\./.test(gb)
      && /trap 'rm -rf "\$ART_DIR"' EXIT/.test(gb)) {
    ok('SRC5d: grok artifact transport shape (0600 tmp, rename-into-place, mkdtemp, trap cleanup)')
  } else bad('SRC5d: grok artifact transport shape incomplete')
  // PLAN-161 W2 fix-round-2 (codex r2 F12): `mktemp -d -t` honors an
  // inherited TMPDIR — pointed inside the repo it relocates the artifact
  // INTO the repo tree AND aims the stale sweep's recursive delete at repo
  // dirs. Both mkdtemp and the sweep must be pinned to the fixed /tmp base.
  if (/mktemp -d \/tmp\/ceo-council-grok\./.test(gb)
      && !/mktemp -d -t/.test(gb)
      && /find \/tmp -maxdepth 1 -type d -name 'ceo-council-grok\.\*'/.test(gb)
      && !/dirname "\$ART_DIR"/.test(gb)) {
    ok('SRC5h: mkdtemp + stale sweep pinned to the fixed /tmp base — TMPDIR cannot redirect artifact writes or aim the sweep at the repo (F12)')
  } else bad('SRC5h: TMPDIR-honoring mktemp -t / dirname-derived sweep base still present (F12)')
  if (!/\$\(cat/.test(gb)
      && (gb.match(/\$BRIEF/g) || []).length === 1
      && /\$\{cli\} "[^"]*brief\.txt[^"]*"/.test(gb)
      && !/\| \$\{cli\}/.test(gb)) {
    ok('SRC5e: grok argv is a fixed pointer (brief.txt ref; $BRIEF feeds ONLY the redactor; no $(cat …); no stdin pipe)')
  } else bad('SRC5e: grok argv/pointer contract violated — brief-derived bytes could reach grok argv/stdin')
  const outgoingTails = []
  const reOut = /codex_egress_redact\.py --outgoing(.{0,30})/g
  let mo
  while ((mo = reOut.exec(src)) !== null) outgoingTails.push(mo[1])
  const sanctioned = (t) => t.startsWith(' | "$TOUT"') || t.startsWith(" | python3 -c") || t.startsWith(' > $ART_DIR/brief.tmp')
  if (outgoingTails.length === 3 && outgoingTails.every(sanctioned)) {
    ok('SRC5f: zero unredacted egress paths — every --outgoing invocation feeds a sanctioned transport')
  } else bad(`SRC5f: stray --outgoing tails: ${JSON.stringify(outgoingTails.filter((t) => !sanctioned(t)))} (n=${outgoingTails.length})`)
  if (/artifact_sha256:\s*\{\s*type:\s*'string'\s*\}/.test(src)
      && /BUDGET_S=\$\(\( 180 \+ 2 \* N \)\)/.test(src)
      && /"\$BUDGET_S" -gt 600/.test(src)
      && /git ls-files/.test(src)
      && /sys\.exit\(124\)/.test(src) && /preexec_fn=os\.setsid/.test(src)) {
    ok('SRC5g: artifact attestation field + mechanical scope-aware codex budget (180 + 2s/file, cap 600, watchdog)')
  } else bad('SRC5g: attestation field / mechanical budget / watchdog mechanics missing')
  if (/verifyFailed\.length === 0/.test(src)) ok('SRC6: CLEAN mechanically gated on verify_failed==0 (F2)')
  else bad('SRC6: CLEAN condition does NOT include verify_failed==0 — refuter crash could launder into CLEAN')
  // PLAN-161 W2 (codex r1 F3): the attestation demotion gate must exist,
  // enforce the 64-lowercase-hex shape, and run BEFORE quorum computation.
  if (/const SHA256_HEX = \/\^\[0-9a-f\]\{64\}\$\//.test(src)
      && /missing\/malformed artifact attestation/.test(src)
      && src.indexOf('const SHA256_HEX') !== -1
      && src.indexOf('const SHA256_HEX') < src.indexOf('const availableLanes')) {
    ok('SRC7: grok attestation demotion gate present (64-hex shape) and placed before quorum computation (F3)')
  } else bad('SRC7: grok attestation demotion gate MISSING/misplaced — an unattested ok-lane could count toward quorum')
  // PLAN-161 W2 (codex r1 F4): the fixture-only ARTIFACT_KEEP_DIR redirect
  // must be GONE — an inherited env var could point artifact writes at the
  // repo tree and leave brief.txt uncleaned.
  if (!/ARTIFACT_KEEP_DIR/.test(src)) ok('SRC8: ARTIFACT_KEEP_DIR env hook absent from the workflow (F4)')
  else bad('SRC8: ARTIFACT_KEEP_DIR still present — inherited env var redirects artifact writes')
  // PLAN-161 W2 fix-round-2 (codex r2 F13): the canonical requested-position
  // vendor is written back onto every surviving lane object. Behavioral
  // twin: scenario J above.
  if (/const requested = REQUESTED_VENDORS\[i\]/.test(src)
      && /return \{ \.\.\.l, vendor: requested \}/.test(src)) {
    ok('SRC9: canonical vendor write-back present — lane identity from REQUESTED_VENDORS position (F13)')
  } else bad('SRC9: lane vendor canonicalization write-back MISSING (F13) — a lane can impersonate another vendor downstream')
  // PLAN-161 W2 fix-round-3 (codex r3 F3): the operator-controlled scope
  // must cross into shell source ONLY through the POSIX shell-quote helper.
  // The exact helper bytes (close-escape-reopen replacement, single-quote
  // wrap) and its application at the git ls-files site are load-bearing;
  // the raw single-quoted interpolation is the injection surface and must
  // be gone. (String-built patterns: a template literal would interpolate.)
  const SHQ_SRC = `const shq = (s) => "'" + String(s).replace(/'/g, "'\\\\''") + "'"`
  const RAW_SCOPE_INTERP = "'$" + '{SCOPE}' + "'" // '${SCOPE}' without tripping JS interpolation
  if (src.includes(SHQ_SRC)) ok('SRC10a: POSIX shell-quote helper present with the exact close-escape-reopen shape (F3)')
  else bad('SRC10a: shq shell-quote helper MISSING/altered — operator scope can inject into shell source')
  if (src.includes('git ls-files -- ${shq(SCOPE)} 2>/dev/null')) ok('SRC10b: shq applied at the git ls-files scope-arg site')
  else bad('SRC10b: git ls-files scope arg is NOT routed through shq')
  if (!src.includes(RAW_SCOPE_INTERP)) ok('SRC10c: raw single-quoted scope interpolation gone from the workflow source')
  else bad('SRC10c: raw single-quoted scope interpolation still present — shell-injection surface (F3)')
}

console.log(`\n==> Results: ${PASS} passed, ${FAIL} failed`)
process.exit(FAIL === 0 ? 0 : 1)
