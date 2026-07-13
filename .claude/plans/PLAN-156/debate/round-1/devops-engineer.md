---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer
generated_at: 2026-07-10T00:00:00Z
---

## Verdict

ADJUST — the plan reuses the PLAN-155 seam correctly and its pin/watch
instincts are right, but five concrete platform/CI properties are either
implicit or mis-tiered and will silently regress or blow up a runner if
left as written. None is a redesign; each is a bounded scope pin-down.

## Summary (≤ 3 bullets)

- **What it does:** adds a third harness (Grok Build) behind the existing
  adapter seam, bumps the codex lane past pin `<0.140.0` to reach the
  GPT-5.6 family via the ADR-111 ceremony, and ships a read-only
  cross-vendor audit council invoking three external CLIs.
- **Strong:** exact-version grok pin + substrate watch (§Wave-0) is the
  only sane posture for a proprietary 0.x binary on a *daily* cadence;
  Wave 1 (codex 5.6) is correctly independent of the grok waves so it can
  land alone; the fail-loud council doctrine is load-bearing, not decor.
- **Weak (all platform-shaped):** the grok CI matrix hermeticity is
  never stated (codex's is explicit); the exit-2 fail-closed property has
  only a *local* positive control; the council is nowhere fenced OUT of
  CI; three new riders pile onto the one validate.yml anchor two PLAN-155
  riders already sit on; and the pin bump has a release-window sequencing
  hazard the plan doesn't name.

## Risks

1. **R-OPS-1 — HIGH. Grok CI matrix could demand a live binary + xAI
   auth secret on the runner.** The plan (§Wave 4) says the grok installer
   matrix "mirror[s] `_codex_harness.sh`" and adds "matrix tests" but
   never asserts the codex matrix's defining property: `test-install-harness-codex.sh`
   is hermetic — "NO codex binary required … recorded-wire replay"
   (validate.yml:348-351). A grok binary in CI means (a) a `curl|bash`
   install step against a daily-moving 0.x that will flake CI constantly,
   and (b) a SuperGrok/xAI auth token in GitHub Secrets — a standing
   egress/supply-chain liability the framework otherwise forbids (only the
   deploy-auth token belongs in CI secrets, per the skill's Secrets Rule).
   *Mitigation:* make hermeticity a written acceptance criterion — grok
   matrix runs fixture/recorded-wire replay, **zero** grok binary, **zero**
   xAI secret on any runner; live-fire is the T2 local tier (Owner's
   authed machine), exactly the codex T1/T2 split.

2. **R-OPS-2 — HIGH. The exit-2 fail-closed property has no CI teeth.**
   Grok is the only harness where an unhandled hook crash is fail-OPEN
   (plan §Honest-limitations). The plan's proof that a crashing matcher
   still DENIES lives in Wave-7 *local* artifacts (`PLAN-156/artifacts/`).
   A security-critical property whose only positive control is off-CI is a
   property that regresses the first time someone refactors the shim and
   nobody re-runs the local demo. The PLAN-155 precedent already shows the
   right shape: validate.yml:380-387 runs a *functional* RED-on-absence
   self-test in CI ("a fail-open rail's silence is NOT health — the teeth
   must bite in CI"). *Mitigation:* add a hermetic CI assertion — feed the
   grok adapter a matcher that raises, assert it emits structured deny +
   exit 2 (no grok binary needed; it's a pure adapter unit test). Ride it
   in the Wave-2 golden/drift suite, not only Wave-7.

3. **R-OPS-3 — HIGH. The council is never fenced out of CI.** Wave 6 ships
   `council-audit.js` + `/council` as a workflow, "advisory," but nowhere
   states it must NOT run in any CI job. A CI job that invokes live Claude
   + `codex exec` + `grok -p` lanes would need three vendor auth secrets on
   the runner, burn unbounded tokens per push, be non-deterministic, and
   egress repo content to three external services on every trigger.
   *Mitigation:* write it explicitly — council is operator/local-only;
   NO CI job invokes a live lane. The most CI may do is exercise the
   shard-parse + fail-loud degradation logic against **fixture** lane
   outputs (a mocked `STATUS: unavailable` lane), never a live call.

4. **R-OPS-4 — MEDIUM. Three new riders converge on the one validate.yml
   anchor two PLAN-155 riders already occupy.** The codex installer-matrix
   step and the Wave-6 pair-rail/advisory-teeth step are adjacent at
   validate.yml:353-388. PLAN-156 adds a grok installer-matrix step
   (Wave 4) and a grok pair-rail/advisory step (Wave 5). Landed as
   separately-signed staged patches (the S265 bundle README §3 conflict
   class), the second and third patch will 3-way-conflict on the lines the
   first moved. *Mitigation:* two levers — (a) the pair-rail/advisory rider
   is already a loop `for adapter in claude codex` (validate.yml:374);
   extend it to `claude codex grok` (adapter-shape-aware body: grok takes
   the fixture-replay path) so **no new step** is added; (b) for steps that
   must be new, append at the END of the job's step list (fresh anchor) or
   consolidate all grok validate.yml edits into ONE signed patch rather
   than splitting across SENT-GK-C and SENT-GK-D.

5. **R-OPS-5 — MEDIUM. Pin bump vs release.yml step-15 forward-binding is
   a release-window sequencing hazard.** The codex pin's real enforced
   consumer is release.yml step 15: `verdict.tool_versions.codex_cli in
   codex-cli-pin.txt range` (release.yml:632). (`pair-rail-gate.sh` Gate 4
   is a Phase-1 stub-pass — line 149 — so it is NOT the gate; the plan
   should not lean on it.) Bumping the upper bound past 0.140 means any
   in-flight RC verdict authored against 0.139 stays valid only while 0.139
   remains in-range; if the ceremony ever *raises the lower bound*, a live
   RC verdict silently falls out of range and red-locks the GA cut.
   *Mitigation:* Wave 1 must only WIDEN the upper bound (keep `>=0.128.0`),
   refresh `codex-cli-binary-sha256.txt` (the actual supply-chain gate — a
   `_KERNEL_PATHS` edit needing sentinel + override), and not run the bump
   during an open release window.

## Must-fix (blocking)

1. **State grok CI hermeticity as acceptance criteria (R-OPS-1).** Grok
   matrix = fixture/recorded-wire replay; no grok binary, no xAI secret on
   any runner; live-fire confined to the T2 local tier. Mirror the exact
   codex property at validate.yml:348-351, don't just "mirror the script."
2. **Add a hermetic CI positive control for exit-2 fail-closed (R-OPS-2).**
   A crashing matcher under the grok adapter must be asserted to DENY +
   exit 2 in CI (adapter unit test), in the Wave-2 suite — not only in the
   Wave-7 local artifact. Centralize the exit-2 wrap in the shared dispatch
   shim so no future hook can forget it (the proposal's own open question —
   answer it YES).
3. **Fence the council out of CI (R-OPS-3).** Write into Wave 6 that no CI
   job invokes a live council lane; CI may only test degradation logic with
   fixture lane outputs. Per-lane budget ceilings (OQ6) must be enforced in
   the workflow code, with a hard default cap, before first live run.
4. **Resolve the validate.yml anchor conflict before staging (R-OPS-4).**
   Prefer extending the existing `for adapter in …` loop to grok over
   adding adjacent steps; consolidate grok validate.yml edits into one
   signed patch or append at a fresh anchor.

## Nice-to-have (advisory)

1. **Pin the grok installer fetch, not just record its SHA post-hoc.**
   §Wave-0 has the Owner `curl -fsSL https://x.ai/cli/install.sh | bash`
   and record the SHA after. The framework's own install.sh carries a
   self-SHA trailer and the deny-baseline ships a curl-pipe-bash tripwire;
   asking the Owner to pipe an unpinned installer to bash is the same class
   we guard against. If x.ai publishes a versioned installer URL or a
   release-asset SHA, pin to that; otherwise keep it in HONEST-LIMITATIONS
   (the plan already does — acceptable residual).
2. **Add the grok binary-SHA pin file alongside the version pin.** §Wave-0
   creates `grok-cli-pin.txt` + "binary SHA file" — make the SHA file a
   first-class governance artifact mirroring `codex-cli-binary-sha256.txt`,
   and register both in the kernel-path guard from day one so the first
   edit isn't a surprise sentinel.
3. **Give the grok substrate-watch item an explicit weekly staleness
   budget.** On a daily 0.x cadence, a weekly Owner-run `--refresh` (the
   PENDING-OWNER network step, no agent network under ADR-136-AMEND-1)
   leaves the pin ~7 releases stale on average. Document that this drift is
   expected and detection-only, and that a red staleness finding is a
   prompt to re-harvest, not a break — so it doesn't read as CI failure.

## Unseen by the original plan

1. **Bus-factor / maintenance-cadence cost of a third proprietary daily-0.x
   harness.** CLAUDE.md §5 already names single-maintainer bus factor as an
   honest limitation. A daily-release proprietary binary adds a standing
   weekly watch + re-fixture obligation that no CI can automate (no binary,
   no secret on the runner by R-OPS-1). The plan should state the ongoing
   operational load, not just the one-time build cost, so the Owner ratifies
   the *recurring* commitment at Wave-0 signing.
2. **Grok subscription (OQ5) is a hard external dependency with no CI
   fallback.** If SuperGrok/X Premium+ lapses, every grok live-fire and the
   grok council lane go dark simultaneously. The plan should specify the
   degraded-mode contract: grok waves' *hermetic* CI stays green (no auth
   needed), and the council grok lane reports `unavailable` (the fail-loud
   doctrine already covers this — make it explicit that a lapsed sub is
   just another `unavailable`, not a red build).
3. **`check_arbitration_kernel.py` / `check_canonical_edit.py` will guard
   the new grok pin + adapter registry the moment they exist.** The codex
   pin files are `_KERNEL_PATHS`; the grok equivalents should be enrolled
   in the same guard in the SAME wave they're created, or Wave-4's routine
   registry edit (316→318 actions, `KNOWN_ADAPTERS += grok`) trips an
   unexpected kernel-guard block mid-execution.

## What I would NOT change

- **Exact-version pin + weekly substrate watch for grok** (§Wave-0, OQ2).
  A semver range is meaningless on a daily 0.x proprietary binary; exact
  pin + watch is the correct and only honest posture. Do not "simplify"
  to a range.
- **Wave 1 (codex 5.6) decoupled from the grok waves.** This is correct
  risk sequencing — the pin ceremony can land and be verified on its own,
  independent of grok subscription/install blockers. Keep them separable.
- **The hermetic-CI / local-live-fire tiering inherited from codex.** It is
  exactly right; my must-fixes only ask that grok be held to the SAME bar
  explicitly rather than by implication.
- **Advisory-Stop honesty on grok** (§Wave 5). Not faking a blocking Stop
  where the harness doesn't support one, and moving the teeth to the
  git pre-push gate, is the correct and auditable choice — do not paper
  over it with a synthetic Stop.
- **Fail-loud council with vendor attribution and no silent substitution**
  (§Wave 6). This is the council's reason to exist; degrading to a labeled
  2-lane verdict rather than quietly swapping vendors is the property that
  makes the instrument trustworthy. Keep it.
