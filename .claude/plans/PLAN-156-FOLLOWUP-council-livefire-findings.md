---
id: PLAN-156-FOLLOWUP-council-livefire-findings
parent: PLAN-156
title: Council live-fire S270 findings — redactor CLI, fail-open verify, guard gaps
status: draft
created: 2026-07-13
owner: CEO
# OQ1/OQ2 Owner-ratified S270 (see §Clarifications); stays draft until
# its own Wave 0 debate runs (canonical-heavy touch set).
depends_on: [PLAN-156]
budget_tokens: 90-140k
budget_sessions: 1
context_risk: medium
external_wait: none
tags: [council, egress, hooks, grok]
---

# PLAN-156-FOLLOWUP — Council live-fire S270 findings

## Context

The first live `/council` run (S270, 2026-07-13; run `wf_1adfc111-a79`,
Owner-authorized OQ5 egress) closed **1-lane degraded**: grok refused to
start (no `~/.grok/sandbox.toml` — correct fail-loud), codex lane died
pre-send (`budget/timeout`; the mandatory redaction step is structurally
non-executable, see F1, and a concurrent `codex exec review` contended
for the binary). **Privacy outcome: zero bytes reached xAI or OpenAI**
(journal-verified: both external lanes returned `status: unavailable`
with empty findings). The Claude lane produced 6 adversarially-verified
findings — a second confirmation of
[[feedback-livefire-catches-what-fixtures-miss]]: the 11/11 council
fixture suite (PLAN-156 W6) proved parse/fail-loud logic, not the live
egress path.

Findings (advisory evidence — triaged here into the normal cascade):

| # | Surface | Finding |
|---|---|---|
| F1 | `.claude/hooks/_lib/codex_egress_redact.py` + `council-audit.js:145` | Mandated egress-redaction command (`python3 codex_egress_redact.py --outgoing`) is non-executable: no CLI entrypoint, relative import fails as script (ImportError L47). External lanes can never redact-and-send → council live is structurally 1-lane until fixed. |
| F2 | `council-audit.js:265-277,328-330` | Verify-stage fail-open: refuter error/null → `verdicts:[]` → all groups `unverifiable` → `confirmed=0` → mechanical CLEAN at 3 lanes. Raised findings can vanish into a false-green (the S-class false-green from memory: vacuous pass masking). |
| F3 | `check_canonical_edit.py:320-321` | Workflow guard covers only `council-audit.js` + `council.md` exact paths; sibling/new `.claude/workflows/*.js` are ordinary-writable → a second egress-bearing workflow could bypass the guard. |
| F4 | `scripts/_grok_harness.sh:333,348` | Trust probe is substring `grep -qF` over `trusted_folders.toml` → prefix-sibling or commented entries yield false `VERDICT: ARMED`. |
| F5 | `templates/grok/pre-push-review-gate.sh:69-76,167` vs `check_codex_stop_review.py:472` | Fingerprint parity broken: gate hashes coarse per-commit paths, recorder hashes precise working-tree `_is_canonical` paths → divergence on coarse-only paths (e.g. `.claude/plans/*.md`). |
| F6 | `.claude/hooks/_python-hook.sh:463-464` | Exit-2 map is order-sensitive substring over whole stdout (`*"decision"*"deny"*`) → an allow payload containing a later quoted deny token exits 2 = spurious block on grok. |
| F7 | `council-audit.js` (instrument) | Requested `scope: .claude/hooks/` but the report/prompts ran scope `.` — args.scope not propagated. Minor, but breaks scoped-egress expectations (Owner authorizes a scope, lane sees the repo). |

## Goal

All 7 findings fixed + regression-tested, and a full-quorum (3-lane)
council live-fire completes with real cross-vendor attribution.

## Waves

### Wave 0 — debate + ratification
Check: none (ceremony gate)
- [ ] Debate L3 (`/debate start PLAN-156-FOLLOWUP` — canonical-heavy touch
  set: `_lib`, hooks, shim, guard list); Owner ratifies at review.

### Wave 1 — F1 redactor CLI (canonical `_lib` → ceremony)
Check: printf 'x' | python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing (exit 0, redacted output)
- [ ] Add `__main__`/argparse CLI entry (absolute-import safe) to
  `codex_egress_redact.py`; keep library API unchanged; executable smoke
  test in `_lib/tests/` (TestEnvContext).

### Wave 2 — F2 verify fail-open → fail-loud (council-audit.js is GUARDED — rides the ceremony)
Check: node scripts/tests/test-council-fixture.mjs (all cases green incl. new refuter-null case)
- [ ] Refuter error/null marks the group `verify_failed` (surfaced in
  report + blocks CLEAN verdict), never silent `unverifiable`-drop; add
  fixture case. NOTE (Codex pair-rail S270): `council-audit.js` is
  ALREADY in `check_canonical_edit.py`'s guard list — F3 is about the
  unguarded SIBLINGS. This wave therefore lands via the same sentinel
  ceremony as Waves 1+3, not direct.
- [ ] F7 in the same file: propagate `args.scope` into lane prompts +
  report header; fixture asserts scope string round-trip.
  Check: grep -n "args.scope" .claude/workflows/council-audit.js

### Wave 3 — F3 guard glob + F4/F5/F6 grok-rail fixes (canonical → ceremony)
Check: python3 -m pytest .claude/hooks/tests/ -q -k "canonical or python_hook" && python3 -m pytest .claude/scripts/tests/ -q -k grok
- [ ] `check_canonical_edit.py`: guard `.claude/workflows/*.js` as a
  class (glob), not the single file; regression test (sibling write
  blocked).
- [ ] `_grok_harness.sh`: trust probe parses exact path entries (no
  substring/commented matches); test with prefix-sibling fixture.
- [ ] Fingerprint parity: gate and recorder hash the same path set
  (align on the precise `_is_canonical` set); parity test.
- [ ] `_python-hook.sh` exit-2 map: parse the decision FIELD (first
  `"decision"` key value), not whole-stdout substring; regression: allow
  payload containing quoted "deny" string exits 0.

### Wave 4 — full-quorum live-fire (positive control)
Check: council run report shows quorum 3-lane + one council_lane_invoked per lane
- [ ] **Owner (or CEO with Owner ack):** install grok council sandbox
  profile: `cp templates/grok/sandbox.toml.example ~/.grok/sandbox.toml`
  (review contents first).
- [ ] Re-run `/council` on the ORIGINAL intended scope
  (`.claude/hooks/`), no concurrent codex processes; verify 3-lane
  quorum, scoped prompts, `ProfileApplied+enforced` in
  `~/.grok/sandbox-events.jsonl`, and redaction smoke on a planted
  fake-secret fixture file inside scope.

## Open questions

- **OQ1** — F3 guard glob may collide with legitimate future workflow
  authoring flow (workflows become ceremony-gated). Accept that cost?
  CEO default: yes — egress-bearing surface warrants it.
- **OQ2** — Wave 4 planted-fixture redaction proof: plant under scope a
  file with a fake token and assert the lane prompt redacts it. Include?
  CEO default: yes (cheap, converts "no egress observed" into "egress
  provably redacted").

## Clarifications

- 2026-07-13 (S270, Owner via structured tie-break, block ratification):
  OQ1 → **guard glob on `.claude/workflows/*.js` ratified** (workflows
  become ceremony-gated; egress-bearing surface warrants it); OQ2 →
  **planted-fixture redaction proof ratified** for the Wave 4 full-quorum
  re-run.

## How to continue

Read this plan + parent PLAN-156. If `draft`: run Wave 0 debate. Waves
1+2+3 are ALL canonical (council-audit.js included — it is on the guard
list) → stage + one sentinel ceremony (the `land-plan156.sh` pattern).
Wave 4 needs grok CLI local + codex budget; run with no concurrent
codex processes.

## Success criteria

- [ ] All 7 findings closed with regression tests; suites green.
- [ ] Full-quorum council run recorded (3 lanes AVAILABLE, scoped,
  redaction proven on planted fixture).
- [ ] Validate workflow green on closeout commit.
