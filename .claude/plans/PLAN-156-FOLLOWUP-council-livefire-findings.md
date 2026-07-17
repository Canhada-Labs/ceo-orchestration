---
id: PLAN-156-FOLLOWUP-council-livefire-findings
parent: PLAN-156
title: Council live-fire S270 findings — redactor CLI, fail-open verify, guard gaps
status: reviewed
created: 2026-07-13
owner: CEO
# OQ1/OQ2 Owner-ratified S270 (see §Clarifications); W0 debate DONE S272;
# draft→reviewed ratified by Owner directive S276 (see §Clarifications).
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

### Wave 0 — debate + ratification — debate DONE S272 (3×ADJUST → PROCEED, ajustes desta revisão); ratificação Owner PENDENTE
Check: none (ceremony gate)
- [x] Debate L3 (`/debate start PLAN-156-FOLLOWUP` — canonical-heavy touch
  set: `_lib`, hooks, shim, guard list) — round 1 3×ADJUST, consensus
  `PLAN-156-FOLLOWUP/debate/round-1/consensus.md` (7 consensus findings
  folded nesta revisão; verdict PROCEED = design-coherent).
- [x] **Owner ratifica `draft → reviewed`** (gate deste plano; C1-C7 já
  aplicados abaixo). Ratificado 2026-07-16 (S276) por diretiva Owner em
  chat ("finaliza absolutamente tudo que tá pendente"), escopo = executar
  este plano até done incluindo cerimônia e W4.

### Wave 1 — F1 redactor CLI (canonical `_lib` → ceremony) [C4+C7] — LANDED S276 `927c5ca` (FU-MAIN sentinel)
Check: printf 'x' | python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing (exit 0, redacted output — run from repo root as a SUBPROCESS, never `python3 -m`) — VERIFIED S276: rc=0 redacted; 72/72 F1-F7 regression tests green
- [ ] Script-safe import (try relative → except ImportError: sys.path
  insert + absolute) + `__main__`/argparse — argparse ALONE does not fix
  run-as-file (debate C4). Library `redact()` single-pass /
  never-raise / never-echo contract untouched (AST conformance test
  keeps passing).
- [ ] **Fail-CLOSED CLI contract (VETO line):** on ANY internal error,
  exit NONZERO and emit NOTHING to stdout — never echo input. Smoke
  asserts BOTH paths: redaction works AND induced-failure → exit≠0 +
  empty stdout.
- [ ] Acceptance = the LITERAL `council-audit.js:145` command string run
  from repo root. Smoke lands in `_lib/tests/` (TestEnvContext) AND
  mirrored in a matrix dir (`.claude/scripts/tests/`) — `_lib/tests/`
  is not covered by the 3.9-3.12 matrix (debate C7) and this is
  literally an import-safety fix.

### Wave 2 — F2 fail-loud + F7 re-anchored (council-audit.js GUARDED — rides the ceremony) [C1+C5-sem+C7] — LANDED S276 `927c5ca` (FU-MAIN sentinel)
Check: python3 -m pytest .claude/scripts/tests/test_council_verify_semantics.py -q (Python mirror — the .mjs fixture runs in NO CI job today, debate C7) — VERIFIED S276 green
- [ ] F2 **split** `verify_failed` (refuter crash/omission — synthesized
  default) from explicit `unverifiable` (refuter ran and judged): CLEAN
  ⇔ `lanes>=3 AND confirmed==0 AND verify_failed==0`; legitimate
  refute-everything CLEAN stays reachable; `verify_failed` count surfaced
  PROMINENTLY in the report (silent DEGRADED is still a soft failure).
  No exit-code change — advisory instrument, o verdict É o produto.
  Fixture covers refuter-null AND refuter-omits-one-key.
- [ ] F7 **re-anchored (debate C1):** council-audit.js already threads
  `args.scope` (:54/:112/:339, present desde o commit inaugural) — the
  S270 scope=`.` bug is UPSTREAM at the invocation layer (`/council` →
  `Workflow({args:{scope}})`). Fix/assert the command→workflow boundary;
  proof exercises the REAL `/council` entry. If the invocation layer
  also proves correct → close F7 as NOT-A-CODE-DEFECT + W4 scoped-prompt
  assertion. A workflow-internal round-trip fixture is NOT acceptable
  evidence (passes today on correct code).
- [ ] Redact→send pipe fold (C4/Critic-B Unseen 2): lane brief in
  council-audit.js becomes a single `redactor | vendor-cli` pipe under
  `set -o pipefail` — a skipped redaction cannot produce a sendable
  prompt. Prose-level residual named in §Clarifications.
- [ ] `.mjs` fixture cases still added/kept for local runs; the CI-load-
  bearing assertions are the Python mirror (matrix dir).

### Wave 3 — F3 guard glob + F4/F5/F6 grok-rail fixes (canonical → ceremony) [C2+C3+C5+C6+C7] — LANDED S276 `7224e8f` (FU-KERNEL sentinel, CEO_KERNEL_OVERRIDE=PLAN-156-FOLLOWUP-GUARD-GLOB) + `927c5ca` (F4/F6 in FU-MAIN); VERIFIED S276: --is-canonical oracle guards sibling .claude/workflows/*.js; shellcheck -S warning rc=0
Check: python3 -m pytest .claude/hooks/tests/ -q -k "canonical or python_hook" && python3 -m pytest .claude/hooks/tests/test_codex_stop_review.py .claude/scripts/tests/test_grok_trust_probe.py .claude/scripts/tests/test_fingerprint_parity.py -q && shellcheck -S warning scripts/_grok_harness.sh templates/grok/pre-push-review-gate.sh
(named files — `-k grok` seleciona 0 testes hoje → pytest exit 5 = red espúrio, debate C7)
- [ ] F3 `check_canonical_edit.py`: guard `.claude/workflows/**/*.js` as
  a CLASS (glob, subdirs included — "a file we choose not to ship is the
  file an attacker would CREATE"); regression: sibling write blocked; NO
  redundant `_CANONICAL_PREFIXES` add (`.claude` already fast-pathed).
  **Ceremony mechanics (C3):** file is `_KERNEL_PATHS` → landing script
  exports `CEO_KERNEL_OVERRIDE=<reason-slug>` + `_ACK=I-ACCEPT` for this
  hunk (audit-emitted); F3 lands as its OWN commit segment (independent
  rollback of the widest-blast-radius change); dry-run before real land.
- [ ] F4 `_grok_harness.sh`: trust probe parses exact normalized path
  entries line-wise (skip comments; realpath both sides); on ANY parse
  ambiguity → NOT-ARMED (never over-claim). **Characterize-then-pin
  (C6):** capture a REAL `trusted_folders.toml` from the pinned grok
  binary as fixture BEFORE writing the parser.
- [ ] F5 **full rescope (C2, unanimous):** (a) align BOTH sides UP to the
  fine `_is_canonical` set — NEVER down (coarse = collision-prone =
  review-reuse bypass [VETO line]; coarse also under-triggers on
  `templates/**`, `.grok/**`, `.codex/**`, `AGENTS.md` — exactly the
  egress/disarm surfaces); (b) single-source oracle: new
  "is-this-path-canonical" CLI on `check_canonical_edit.py`, gate
  shells out, recorder keeps importing (bash re-implementation IS the
  drift class); (c) reconcile granularity: gate aggregates the WHOLE
  pushed range into one fingerprint (recorder is aggregate); parity
  test MUST exercise a multi-commit push; (d) shell-out failure →
  coarse fallback = over-trigger = fail-CLOSED, both sides; (e)
  enumerate the coverage delta in the ceremony record; (f) confirm the
  grok gate's actual recorder pairing (the analyzed recorder is the
  codex Stop hook — cross-harness check). Fallback if multi-commit
  parity can't hold: DEMOTE sidecar path (b) formally + 2-line ADR.
- [ ] F6 `_python-hook.sh` exit-2 map: **structural top-level JSON parse**
  via the already-resolved `$FOUND_PY` (VETO line: first-occurrence
  substring/regex REJECTED — decoy `"decision":"allow"` before the real
  deny defeats it). Dual fail semantics: parse OK → field governs; parse
  FAILURE + deny token present → exit 2 (fail-CLOSED); parse failure +
  no deny token → hook rc (INFRA fail-open preserved — never
  "nonzero→deny"). Regressions BOTH directions: allow-with-quoted-"deny"
  → 0; decoy-allow-before-real-deny → 2.

### Wave 4 — full-quorum live-fire (positive control) — RAN S276 (Owner-authorized egress); **DEGRADED 2-lane, NOT clean 3-lane**
Check: council run report shows quorum 3-lane + one council_lane_invoked per lane
- [x] **Owner-authorized egress + grok council sandbox installed & VERIFIED
  ENFORCING** (S276): `~/.grok/sandbox.toml` from template; `ProfileApplied
  profile:council enforced:true restrict_network:true` landed for the run
  (15:11:12Z / 15:12:46Z) with the full credential-surface deny-list. The
  S270 blocker (grok refused, no sandbox) is RESOLVED.
- [~] **`/council .claude/hooks/` ran (run wf_6ff53f95-2aa)** — real egress:
  **grok lane AVAILABLE**, returned 7 findings (F1 redactor now executable +
  sandbox enforced = the S270 1-lane structural blocker is FIXED, proven
  live). **codex lane UNAVAILABLE** — hit the ~180s wall-clock hard budget
  (SIGTERM at 3m) mid-probe on the large scope; not retried, not substituted
  (fail-loud held). Claude lane AVAILABLE (2 findings). → **quorum 2-lane
  DEGRADED**, not the 3-lane the criterion requires.
- [~] **verify_failed = 9** — the adversarial verifier agent died on a
  transient API error ("Connection closed mid-response"); all 9 raised
  groups went UNADJUDICATED. Verdict correctly DEGRADED (confirmed=0,
  verify_failed=9). The 9 are OPEN QUESTIONS, not confirmed bugs (several —
  git_bypass token-matcher evasion, env-hijack default-OFF — are known
  ACCEPTED boundaries; the credential-guard ones are the known example-token
  class). Re-verify before treating any as a finding.
- [x] Fail-loud crash check — proven LOCALLY (broken redactor under pipefail
  → pipe exit≠0 → lane `unavailable`, never crash; redactor fail-closed
  contract 5/5 green). Live corroboration: codex went `unavailable` on
  timeout without crashing the run or substituting.
- [!] **OQ2 planted-employer-class-token proof — RE-FRAMED, not run.** The
  vendor CLIs read the repo THEMSELVES under read-only sandbox; the ADR-114
  redactor only guards the BRIEF (instruction text), NOT vendor-read file
  content — and does not catch employer-class strings anyway (that is the
  pair-rail's separate scan). Planting a real foxbit token would LEAK it, not
  prove redaction. File-content containment is scope-choice + sandbox
  deny-list, not the brief redactor. This criterion needs rewording (a
  future revision) before it can be a meaningful proof.

**W4 disposition:** the FOLLOWUP fixes are VALIDATED in live-fire (grok lane
went from S270-refused → functional; redaction pipe + sandbox enforced), but
the literal "clean 3-lane quorum" criterion is UNMET because codex times out
on the full `.claude/hooks/` scope in its 180s budget (an operational tuning
gap, not a fix defect) and the verifier hit a transient API blip. Getting a
clean 3-lane needs either a narrower codex scope or a longer codex wall-clock
budget — a small council-tuning follow-up, tracked separately.

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
- 2026-07-16 (S276, Owner via chat): **draft → reviewed ratificado** por
  diretiva explícita ("finaliza absolutamente tudo que tá pendente…
  termina o backlog completo") — cobre a cerimônia de landing (F1-F7) e
  o W4 full-quorum live-fire (egress redigida, mesmo enquadramento do
  OQ5/S270).
- 2026-07-13 (S272, debate round-1 consensus — accepted residuals +
  deferrals, recorded per Critic-B/Critic-A): (a) the egress workflow
  remains SINGLE-guarded by a fail-open hook (framework-wide posture;
  explicit accept for an egress surface — revisit if a 2nd egress-bearing
  workflow ships); (b) the redact-then-send step remains prompt-level
  even after F1 — mitigated by the W2 pipe fold, named residual; (c)
  commands sibling gap (`council.md` is an exact-path guard) — LOW,
  deferred: a sibling command cannot transmit without an egress-bearing
  workflow, which the F3 glob guards; (d) F6 adjacency-glob alternative
  REJECTED in favor of the security-VETO structural parse; (e) sidecar
  path (b) demotion is the recorded FALLBACK if multi-commit parity
  cannot hold (2-line ADR then).

## How to continue

**STATE (S276, 2026-07-16/17):** status = `reviewed`. **Waves 1+2+3 LANDED**
via `land-followup.sh` — 2 GPG sentinels (FU-MAIN `927c5ca`, FU-KERNEL
`7224e8f`); 72/72 F1-F7 regression tests green; F3 oracle guards sibling
`.claude/workflows/*.js`. **Wave 4 RAN** (Owner-authorized egress, run
`wf_6ff53f95-2aa`) and **validated the fixes in live-fire**: the grok lane —
refused/1-lane in S270 — is now FUNCTIONAL (F1 redactor executable + council
sandbox enforced), returning findings under contained egress. **But it
degraded to 2-lane** (codex timed out at its 180s budget on the full
`.claude/hooks/` scope) with the verifier hitting a transient API error
(verify_failed=9), so the literal "clean 3-lane quorum" criterion is UNMET.

**To reach `done`, the only remaining item is a clean 3-lane run**, which
needs codex to finish inside budget — either (a) re-run `/council` on a
NARROWER scope (a hooks subdir) so codex fits its wall-clock, or (b) raise
the codex lane's time budget. This is council operational tuning, not a
FOLLOWUP fix gap. Also reword the OQ2 employer-class proof first (see W4
notes: the brief redactor cannot guard vendor-read file content — that is
scope-choice + sandbox deny-list). Until a clean 3-lane lands, this plan
rests at `reviewed` with all fixes shipped, locally verified, AND
live-fire-validated (grok functional). Owner may alternatively ACCEPT the
2-lane live-fire as sufficient proof and close W4 with the clean-3-lane as a
documented council-tuning follow-up.

## Success criteria

- [x] All 7 findings closed with regression tests; suites green. (S276:
  72/72 F1-F7 regression tests + 20 redactor-invariant tests green;
  landed `927c5ca` + `7224e8f`.)
- [ ] Full-quorum council run recorded (3 lanes AVAILABLE, scoped,
  redaction proven on planted fixture). **BLOCKED on Owner egress auth
  (Wave 4).** Locally provable parts done (redactor is not a no-op;
  fail-loud); the 3-lane egress itself needs Owner sign-off.
- [ ] Validate workflow green on closeout commit. (Perf-gate load-flake
  in the current runner regime may require a job re-run — see PLAN-159
  post-land checkpoint #2; not a code defect.)
