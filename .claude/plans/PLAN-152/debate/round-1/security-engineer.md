---
plan: PLAN-152
round: 1
archetype: security-engineer
verdict: ADJUST_PROCEED
---

## Verdict
ADJUST_PROCEED. The thesis is sound, the wave order is right, and the three P0
fail-opens are real (I re-proved two by tracing the code, not the shards). But the
plan carries four blocking gaps: a false "ceremony" label on an unguarded path, an
unstated assumption that the restored gate self-heals mid-session, a fail-closed
conversion whose §4 doctrinal conflict is left uncodified (and whose brick surface
the Check line does not cover), and an OIDC/NPM_TOKEN sequence that can brick the
release pipeline. None require a redesign — hence ADJUST, not REJECT.

## Summary
Every Wave A finding reproduces against the current tree. Fail-open on a security
gate is my #1 red flag, and three ship live in v1.0.0. The remediations are
directionally correct; my findings are guardrails around *how* they land, plus one
factual mislabel that would give the Owner false assurance when scoping the sentinel.

## Risks (the CEO did not see)
- **R1 — the pair-rail fix may not restore the gate for THIS session.** Claude Code
  loads `settings.json` hooks at session start. Editing `:201` mid-run (governance-01)
  likely does NOT re-register the hook until a fresh session. If so, the ENTIRE
  A/C/D/F kernel-edit sequence runs with the pair-rail dead — not just "until Wave A
  lands" as the proposal frames it. The interim manual-codex control must cover the
  whole run, and the restored gate must be verified in a FRESH session at Wave G.
- **R2 — `.claude/workflows/*.js` is not canonically guarded.** error-handling-03 is
  labelled "CANONICAL (workflows) → ceremony," but `check_canonical_edit.py:113-240`
  has no `.claude/workflows/*.js` entry and the pair-rail L3+ heuristic
  (`check_pair_rail.py:32-39`) covers only `.github/workflows/*`. The edit lands
  DIRECT; no sentinel is enforced. A sentinel Scope line naming these paths gives
  false assurance (the hook won't back it), and eval-baseline-n20.js spawns
  `claude -p` subprocesses with spend authority — an unguarded surface worth a
  follow-on, but the label is wrong TODAY.
- **R3 — fail-closed brick surface + §4 conflict.** CLAUDE.md §4 literally says "On a
  parse error … emits `{}` (allow)." error-handling-01 inverts that for the
  destructive matcher. Without codifying the input-vs-infra distinction, the next
  maintainer citing §4 reverts the fix and re-opens the hole.

## Must-fix (blocking — cite rule/evidence)
- **MF1 (R2) — correct the error-handling-03 ceremony label.** Evidence:
  `check_canonical_edit.py:113-240` (no `.claude/workflows` glob) +
  `check_pair_rail.py:32-39`. Rule: "trust boundary — least privilege / fail-closed"
  is undermined by a Scope that claims enforcement the hook does not provide. Relabel
  as "NOT guarded — lands direct; follow-on to evaluate guarding `.claude/workflows/*.js`
  (pairs with the deferred governance-04 kernel-matcher plan)." Do NOT list these
  paths in the PLAN-152 sentinel Scope.
- **MF2 (R1) — make the manual codex pair-rail a HARD, RECORDED gate for EVERY
  A/C/D/F kernel commit, and verify the restored gate in a fresh session.** Evidence:
  hooks load at session start; `check_pair_rail.py:53-59` marks the rail additive, so
  the sentinel ceremony (`check_canonical_edit.py:105`, live) remains the primary gate
  — but a dead additive layer for the whole run is a defense-in-depth regression on the
  release that fixes it. Rule: my red flag "fail-open paths on security gates." Require
  a recorded APPROVE artifact per kernel commit (the `37867c2` substrate precedent), and
  add a Wave G step: open a NEW session and run the governance-01 Check (the registered
  command must no longer print `hook not found`) before declaring the gate restored.
  Order governance-01 FIRST in Wave A regardless.
- **MF3 (R3) — prefer raw-text re-scan over hard fail-closed, and codify §4.**
  Evidence: `_tokenize` (`:274-284`) and `_e3` (`:904`) use DIFFERENT shlex tokenizers,
  so a command `_e3` accepts but `_tokenize` rejects (e.g. ANSI-C `$'…'`, lone-quote
  edge cases) would be newly bricked by a blanket fail-closed. The plan's "or re-scan
  raw text" option is the safe one: on `_tokenize` ValueError, regex-scan the RAW
  command for the destructive signatures and block only on a hit (false-positives are
  confined to already-unparseable commands, which are bash errors anyway). Add a
  false-positive regression probe to the Wave A Check (a legit shlex-unparseable command
  still allowed). Then, at Wave G closeout, amend CLAUDE.md §4 to state: input-parse
  failure in a security matcher is fail-CLOSED by design (precedents: `_e3:907-922`,
  `_check_credential_leak:692-695`, git_bypass bounded parse_failure); infra failure
  (missing file / import / timeout) remains fail-open. Rule: skill Fail-Fast — "never
  degrade security silently." §4 is a Gate-1 cache-stable file → closeout-only edit.
- **MF4 (Wave D) — do NOT remove `NPM_TOKEN` until an OIDC publish is proven.**
  Evidence: backlog-oidc drops `secrets.NPM_TOKEN` and adds trusted-publishing, but
  trusted publishing requires an Owner web-console config on npmjs.org that the plan's
  Check ("no NPM_TOKEN reference remains") cannot verify. Removing the token before the
  npmjs.org side is confirmed bricks the next release. Rule: my red flag "supply chain
  / fail-closed discipline" + availability. Either (a) add a Wave-0-style Owner prereq
  "trusted publisher configured on npmjs.org" that BLOCKS token removal AND keep
  NPM_TOKEN as fallback until one OIDC publish succeeds, or (b) DEFER OIDC to v1.0.2 and
  only calendar-flag the ~2026-09-28 expiry now (my recommendation — do not flip auth
  mode in the same release that ships the security hotfix).

## Nice-to-have
- **Wave D info-disclosure framing.** tarball-01 is not just bloat: shipping
  `red-team-corpus/` (attack payloads) + `PLAN-*` (internal architecture) + test
  fixtures to a PUBLIC npm tarball is a mild info-disclosure AND a source of
  adopter-side scanner false-positives (Socket.dev, secret scanners). Note this so the
  finding is not deprioritized as cosmetic — it belongs in v1.0.1.
- **security-01 remediation must check the cache DIR on the READ path.** The robust fix
  is the "0700-verified dir" option: verify the dir exists, is owned by us, is 0700, is
  not a symlink BEFORE the `cat` (`_python-hook.sh:165-173`), else fall to full probe
  (fail-functional). Ownership-on-read, not just symlink rejection on the file.

## Unseen (missing from the plan entirely)
- **Threat-model note for the destructive-guard PoC set.** The bash-safety fix should
  ship with a small corpus of parser-differential bypass vectors beyond `rm -rf ~ ";"`
  (e.g. `rm -rf ~ '` , trailing-backslash, `$'…'` splices) promoted to CI regression
  tests, per skill §Proof-of-Exploitability "the PoC becomes the regression test." The
  plan's single Check probe is necessary but not sufficient to prevent re-regression.
- **No rollback line for the release ceremony.** Wave G declares the release-eligible
  set but names no rollback if the tag/publish step fails after A-F land. Given
  context_risk:high, name the fallback explicitly (it is OQ3's split).

## What I would NOT change
- **Wave order (security → tests → …); A before B.** Correct. A's Check lines are
  executable probes independent of the test harness; B then LOCKS IN A by making the
  three security root-tests collectable. The regression guard for the pair-rail class
  (governance-02, widen `_HOOK_RE`) is already co-located in Wave A — right call.
- **The tarball Check's "stage-first-or-vacuous-pass" caveat.** Sharp and correct: the
  on-disk `npm/` has no staged `.claude/`, so a naive `npm pack` there passes vacuously.
- **The packlist CI gate (tarball-02).** Closing the recurrence vector with a
  `npm pack --dry-run --json` deny-pattern gate is exactly right — empirical, not
  theoretical.

## Open questions
- **OQ1 — label + enum member + ADR now; DEFER the routing flip.** The actual defect
  is the stale `OPUS47 = "claude-opus-4-8"` label — a model-id/label mismatch in a
  cost/routing table is a correctness + audit-trail hazard and should be fixed. Adding
  the enum member is low-risk. Flipping M-tier routing to Sonnet 5 is a behavioral/cost
  change with its own soak, not a security fix, and does not belong in a hardening
  release. Firm: label + member + ADR; routing flip → follow-on.
- **OQ2 — split Wave A into its own tight sentinel; C/D/F may share.** Wave A edits the
  SECURITY GATES THEMSELVES (settings.json, check_bash_safety.py, _python-hook.sh). The
  sentinel authorizing those must be scoped to EXACTLY those paths so a Scope typo
  cannot silently authorize an unrelated kernel edit later in the run, and so a stray
  edit to a Wave-C path during Wave A is BLOCKED (tighter blast radius). One broad
  sentinel also drifts from its anchor-sha as A/B land commits. Firm: per-wave for A (at
  minimum A separate); a single C+D+F sentinel is acceptable IF the Scope enumerates
  exact paths (not `.claude/hooks/*.py` globs) and touched−scope=∅ is re-checked before
  EVERY kernel commit.
- **OQ3 — single v1.0.1, with Wave A+B as the non-negotiable release floor.** The P0s
  are LOCAL-only (self-footgun / shared-host / in-session), not remote-exploitable, so
  the urgency that would justify a decoupled hotfix is absent — and doubling the release
  ceremony doubles the highest-risk pipeline operation. Ship single. BUT bind it: A + B
  green is the release-eligibility floor; never delay a verified security fix to finish
  docs (E) or models (F). If the session degrades, cut in order E → F-P3 → C, HOLD
  D-tarball + A + B + G, and ship what is green as v1.0.1. Split stays the fallback.
