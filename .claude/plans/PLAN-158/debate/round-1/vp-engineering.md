---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering
generated_at: 2026-07-13T18:20:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The plan ships v1.1.0 as a pure release vehicle (55 verified commits since
  v1.0.1, all features already on main) plus exactly one deadline-bound
  deferral (backlog-oidc). Scope thesis, semver call, and Wave 0 gate
  inventory are fundamentally sound and were verified against the as-landed
  `release.yml` / `npm-publish.yml`.
- Strong: the minimum-plus scope is honest (six other PLAN-152 deferrals
  correctly excluded), OIDC inclusion is structurally justified (a
  npm-publish.yml auth change can ONLY be mechanically proven by a real GA
  publish, and publishes only happen at releases — this is coupling, not
  creep), and every release.yml line reference I checked resolves to the
  claimed gate.
- Weak: Wave 3 names the WRONG verdict file for the RC tag (guaranteed step-15
  red on the RC release run — contradicting the plan's own Wave 3 check);
  Wave 1 omits the OIDC flip's mechanical prerequisite (npm CLI version) and
  its documented doc cascade (including the kernel-guarded
  `SPEC/v1/npm-shim.md` that PLAN-152 §Deferred explicitly assigned to THIS
  plan's sentinel); Wave 2's ceremony vehicle silently depends on OQ1
  resolving a particular way.

## Risks

1. **R-VP1 — HIGH — RC verdict-file name mismatch guarantees a red RC run.**
   `release.yml:653` resolves `VERDICT_FILE=".claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md"`
   and `validate-pair-rail-verdict.py` replay-binds `verdict.release_tag ==
   ${GITHUB_REF_NAME}`. For tag `v1.1.0-rc.1` the gate requires
   `pair-rail-verdict-v1.1.0-rc.1.md` with `release_tag: v1.1.0-rc.1`. Wave 3
   instead names `pair-rail-verdict-v1.1.0.md` → step 15 hard-blocks the RC's
   own release run, failing Wave 3's own check ("release-gate green on the RC
   tag") and reintroducing the exact red-RC-run hygiene class PLAN-153 B5 was
   shipped to eliminate. On-disk precedent confirms the two-file convention:
   `pair-rail-verdict-v1.16.0-rc.1.md` + `pair-rail-verdict-v1.16.0.md`.
   Mitigation: rename the Wave 3 artifact; keep Wave 4's fresh GA verdict as
   written.

2. **R-VP2 — HIGH — OIDC flip has an unstated mechanical prerequisite (npm
   CLI version).** `npm-publish.yml:65-70` pins Node 20, which ships npm 10.x.
   npm Trusted Publishing requires a newer npm CLI (≥11.5.1 per npm's trusted
   publishing docs at its 2025 GA). Dropping `NODE_AUTH_TOKEN` without
   upgrading the CLI in-workflow means the first OIDC publish fails
   (ENEEDAUTH) at the worst possible moment: inside the Owner's
   `production-npm` approval on an already-pushed GA tag, and the recovery
   path (re-adding the token env) is a guarded-workflow edit needing another
   sentinel ceremony mid-release. Mitigation: Wave 1 adds an explicit npm CLI
   version step (or Node 24) + a pre-publish `npm --version` assert, and the
   Wave 1 sentinel Scope pre-authorizes the one-line token-fallback revert so
   a failed OIDC publish does not strand the GA (the `already_published`
   guard at npm-publish.yml:224-241 already makes the re-run itself safe).

3. **R-VP3 — MEDIUM — OIDC doc cascade omitted; one file is kernel-guarded
   and contractually assigned to this plan.** After the flip, at least four
   surfaces become false again (the same false-claim class PLAN-152
   tarball-01 fixed, now in reverse): `SPEC/v1/npm-shim.md:59-69` ("Trusted
   Publishing … is NOT configured"), the `npm-publish.yml:1-28` header
   comment, `.github/workflows/GOVERNANCE-MAP.md:56` (auth-inventory row),
   and `scripts/install-npm.sh` (4 OIDC/token mentions, e.g. line 23).
   PLAN-152 §Deferred `spec-npm-shim-oidc-wording` (PLAN-152:236-242)
   explicitly routes the SPEC path "into the backlog-oidc plan (whose
   sentinel will carry the SPEC path)" — PLAN-158 IS that plan and Wave 1's
   sentinel scope does not carry it. `SPEC/**` has its own deny-stack
   (Amends clause per PLAN-085 E.5), so discovering this at ceremony time
   forces a sentinel re-draft. Mitigation: enumerate the cascade in Wave 1.

4. **R-VP4 — MEDIUM — Wave 2's ceremony vehicle is conditional on OQ1's
   outcome.** Wave 2 says the `check_adversary.py` fix "rides the Wave 1
   sentinel ceremony", but if OQ1 resolves to the fallback (regenerate token,
   defer OIDC), Wave 1 contains only Owner console work + a GOVERNANCE-MAP
   re-date — no guarded-workflow sentinel exists to ride. Also note the two
   files are different guard classes (guarded workflow vs canonical hook);
   one sentinel CAN carry both, but only if its Scope enumerates both paths
   (touched−scope=∅ is verified at landing). Mitigation: state the
   dependency, or give Wave 2 its own sentinel line.

5. **R-VP5 — LOW — advisory-workflow gate state is time-sensitive.** Verified
   live (2026-07-13 ~18:00Z): latest runs of all 6 advisory workflows are
   `success` and Validate on main is green (the S269 runner outage recovered;
   chaos + perf-profile carry older failures inside the last-3 window, which
   the as-landed gate accepts because the latest run is green,
   release.yml:519-527). Risk is only that a fresh infra failure lands as
   `latest` before the RC cut. The plan's Wave 3 gh-check covers detection;
   phrase it as "latest run of each must be non-failure + ≤14d", which is the
   actual as-landed rule, rather than "non-red" across the board.

## Must-fix (blocking)

1. **Waves §Wave 3, first checklist item:** rename the RC verdict artifact to
   `.claude/governance/pair-rail-verdict-v1.1.0-rc.1.md` with
   `release_tag: v1.1.0-rc.1` (release.yml:653 + replay-defense bind). Keep
   the Wave 4 GA verdict (`pair-rail-verdict-v1.1.0.md`) as already written.
   Two verdicts total, one per tag. (R-VP1)

2. **Waves §Wave 1, second checklist item (OIDC flip):** add the npm CLI
   prerequisite — an in-workflow npm upgrade step (or Node 24) so the CLI
   meets Trusted Publishing's minimum (verify the exact floor against npm
   docs at execution; ≥11.5.1 per the 2025 GA docs), plus a pre-publish
   `npm --version` assert. Additionally, pre-authorize the token-fallback
   revert inside the same sentinel Scope so a failed OIDC publish is
   recoverable without a second mid-release ceremony. (R-VP2)

3. **Waves §Wave 1 (sentinel scope):** enumerate the OIDC doc cascade in the
   sentinel Scope: `SPEC/v1/npm-shim.md` (kernel-guarded; Amends clause per
   PLAN-085 E.5 — this discharges PLAN-152 §Deferred
   `spec-npm-shim-oidc-wording`, which names this plan's sentinel as its
   vehicle), the `npm-publish.yml` header comment,
   `.github/workflows/GOVERNANCE-MAP.md:56`, and `scripts/install-npm.sh`.
   Doc edits are conditional on the flip actually landing (skip under the
   OQ1 fallback, where only the GOVERNANCE-MAP re-date applies). (R-VP3)

4. **Waves §Wave 2, first checklist item:** replace "rides the Wave 1
   sentinel ceremony" with an explicit vehicle rule: if OQ1 = OIDC, one
   sentinel whose Scope enumerates BOTH `npm-publish.yml` (guarded workflow)
   and `check_adversary.py` (canonical hook); if OQ1 = fallback, Wave 2
   requires its own sentinel or is dropped. (R-VP4)

## Nice-to-have (advisory)

1. **Waves §Wave 0:** add the user-visible stale-count refresh that no gate
   catches: `.claude-plugin/plugin.json` `description` still advertises
   "151 skill checklists" (catalog is 166), and the CHANGELOG.md:11-14
   preamble pins counts "as of v1.0.1: 151 skills, 22 slash commands, 172
   ADRs, 67 `_lib` modules" — refresh to as-of-v1.1.0 alongside the `##
   [1.1.0]` section. The marketplace/plugin gate (release.yml:86-115) asserts
   version fields only; description drift ships silently.
2. **Waves §Wave 4, second checklist item:** the line reference
   "release.yml:312-433" covers registry/governance/test-suites/smoke/self-SHA
   but NOT SBOM (SBOM generation is release.yml:570-575 in release-gate and
   :721-724 in publish-release). Cosmetic, but the plan sells its refs as
   ground truth.
3. **Waves §Wave 0, doc-freshness item:** state that the gate would actually
   PASS at 1.0.x stamps (all seven docs verified: worst case is exactly 1
   minor behind = at, not over, the N=1 security tier), so the restamp is a
   re-review-for-honesty choice, not a gate requirement. Keeps the "gate
   would have caught it" narrative accurate — and a restamp without real
   re-review would be stamp theater.
4. **§Context:** the citation "GOVERNANCE-MAP.md:56" should be
   `.github/workflows/GOVERNANCE-MAP.md:56` — there are two files with that
   name (`docs/GOVERNANCE-MAP.md` does not carry the token-expiry row).

## Unseen by the original plan

1. **The manifest "generator" does not exist.** release.yml:77-84 claims
   `.claude-plugin/{plugin,marketplace}.json` "are generated by
   build-plugin.py (Wave B item 6)" — no `build-plugin.py` exists anywhere in
   the tree (verified). The manifests are hand-maintained, which is exactly
   what Wave 0 implicitly does; but the stale workflow comment is a doc-drift
   landmine for the next editor, and the plan should not inherit the fiction.
   One-line comment fix rides any release.yml sentinel this plan already cuts
   — or record it as a known-stale note.
2. **NODE_AUTH_TOKEN precedence silently defeats the OIDC proof.** If the
   token env var stays live on the publish step "as fallback", npm uses token
   auth and the GA publish "succeeds" WITHOUT ever exercising OIDC — the plan
   would close backlog-oidc on a false proof. The flip must actually remove
   the env from the executed path (the plan's "behind a comment" wording is
   right, but the WHY — auth precedence, not tidiness — is load-bearing and
   should be stated so a future editor doesn't "helpfully" keep both).
3. **Success-criteria gap for the rider:** §Success criteria has no line for
   Wave 2. If OQ2 confirms the rider, add "CPF-shaped benign numeric passes /
   live token still denies, regression tests green" so closeout can't declare
   done with the rider half-landed. (Mechanics verified feasible:
   `secret_patterns.scan(patterns=...)` supports subsetting and PII families
   are `category="pii"`-tagged, distinct from token/credential — the fix is a
   category filter at check_adversary.py:120-123, exactly as claimed.)
4. **Verdict-freshness ↔ RC-hold interplay is tight but unstated:** the GA
   verdict must be authored inside the 24h before the GA tag push
   (`--max-age-hours 24`) yet after the ≥24h RC hold has elapsed, and the GA
   tag must include the verdict commit (parent-sha bind). The `land-plan156.sh`
   single-script pattern the plan invokes handles this only if the script
   sequences verdict-commit → tag → push in one sitting; worth one sentence
   in §How to continue.

## What I would NOT change

- **The semver call.** 1.1.0 is correct. I checked the delta for breaking
  surface: new harness adapters, `/council`, 15 skills, learning loop, codex
  pin widened — all additive; the npm shim contract (`SPEC/v1/npm-shim.md`:
  version follows VERSION 1:1, zero runtime deps) is unchanged; nothing
  renames or removes an adopter-facing surface. The check_adversary rider
  loosens a false-positive class, not a contract.
- **OIDC inside the release is NOT the C6 anti-pattern.** C6 rejected kernel
  ceremonies holding a release hostage. backlog-oidc is the inverse case: its
  mechanical proof (a real publish) structurally exists ONLY at a release,
  it carries the sole calendar deadline in the deferral ledger
  (NPM_TOKEN ~2026-09-28), and OQ1's fallback keeps the release unhostaged if
  the Owner defers. Keep it — with the R-VP2/R-VP3 fixes.
- **The exclusion of the other six PLAN-152 deferrals.** Verified against
  `docs/PLAN-152-deferred-status.md`: each has a successor vehicle;
  none is deadline-bound. This is the scope discipline C6 asked for.
- **OQ3 default = full 24h hold.** The waiver registry
  (governance-waivers.yaml) carries only the 1.0.0 bootstrap entries; v1.1.0
  running the gates fully-enforcing for the first time with zero waiver
  additions is exactly the honest posture, and the sunset tripwire
  (FIRST_GA=2.0.0) stays untouched.
- **Wave 0's four-file version-triple check including marketplace.json** —
  it matches the release gate's every-nested-version assert
  (release.yml:100-113) and encodes the Codex S270 stale-manifest catch.
