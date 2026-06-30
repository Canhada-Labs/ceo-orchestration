#!/usr/bin/env node
// Validator for the saved Workflow scripts in .claude/workflows/ (PLAN-134 W1 item 4).
// Workflow scripts use top-level await + top-level `return`, so plain `node --check`
// rejects them; compile each body as an AsyncFunction (which permits both) with the
// runner globals bound as params. Exits non-zero on any contract violation.
'use strict'

const fs = require('fs')
const path = require('path')

const DIR = path.join(__dirname, '..', '..', 'workflows')
const EXPECTED = ['nightly-hygiene', 'eval-baseline-n20', 'audit-fanout']
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor

let failed = false
const fail = (msg) => { failed = true; console.error('FAIL ' + msg) }

for (const name of EXPECTED) {
  const file = path.join(DIR, name + '.js')
  let src
  try {
    src = fs.readFileSync(file, 'utf8')
  } catch (e) {
    fail(file + ': missing (' + e.code + ')')
    continue
  }
  // meta must be the FIRST statement, a pure literal export.
  if (!src.startsWith('export const meta = {')) {
    fail(file + ': `export const meta = {` must be the first statement')
  }
  // meta.name must match the file name (Workflow {name} dispatch).
  const m = src.match(/name: '([^']+)'/)
  if (!m || m[1] !== name) {
    fail(file + ': meta.name ' + JSON.stringify(m && m[1]) + ' != ' + JSON.stringify(name))
  }
  // Determinism contract: these THROW inside Workflow scripts (resume determinism).
  if (/Date\.now\(|Math\.random\(|new Date\(\)/.test(src)) {
    fail(file + ': forbidden nondeterminism (Date.now/Math.random/argless new Date)')
  }
  // Syntax: compile as an async function body with the runner API as bound params.
  try {
    void new AsyncFunction('agent', 'parallel', 'pipeline', 'log', 'phase', 'args',
      src.replace(/^export /, ''))
  } catch (e) {
    fail(file + ': does not compile as a Workflow body: ' + e.message)
    continue
  }
  console.log('OK   ' + file)
}

// eval-baseline-n20 MUST hard-guard paid spend before anything else.
const evalSrc = fs.readFileSync(path.join(DIR, 'eval-baseline-n20.js'), 'utf8')
if (!/confirm_spend !== true[\s\S]{0,200}?throw new Error/.test(evalSrc)) {
  fail('eval-baseline-n20.js: confirm_spend hard guard missing')
} else {
  console.log('OK   eval-baseline-n20.js spend guard present')
}
// ...and must use the claude -p subprocess substrate, never opts.model (W0a verdict).
if (!evalSrc.includes('claude -p')) {
  fail('eval-baseline-n20.js: missing the `claude -p --model` subprocess substrate (W0a: opts.model is inert)')
}
if (/opts\.model\s*=/.test(evalSrc)) {
  fail('eval-baseline-n20.js: sets opts.model — inert per W0a verdict')
}

if (!fs.existsSync(path.join(DIR, 'README.md'))) fail('README.md missing in ' + DIR)
else console.log('OK   ' + path.join(DIR, 'README.md'))

process.exit(failed ? 1 : 0)
