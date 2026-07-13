---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps Engineer (VP Operations line)
generated_at: 2026-07-13T19:30:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The plan ships v1.1.0 as a ceremony-only vehicle for PLAN-153..156 plus
  exactly one deadline-bound deferral (backlog-oidc) and one optional
  rider. Scope discipline is right; semver-minor call is right; the RC →
  24h-hold → GA → production-npm skeleton matches release.yml/npm-publish.yml
  as landed.
- Strong: verified premises (release.yml RC fixes ARE live at :55-70,
  :293-310, :736-756 — I re-read them), correct RC flow (VERSION=1.1.0
  before rc.1), correct pin state (`>=0.128.0,<0.145.0` +
  binary sha `134063e1…` current), correct npm-publish anchors
  (:54 RC exclusion, :56 environment, :105-204 staging+packlist).
- Weak: two mechanics defects that each produce a RED tag run as written —
  the Wave 3 RC verdict file is GA-named (step-15 keys on
  `${GITHUB_REF_NAME}`; v1.0.1-rc.1's gate run failed exactly this way),
  and the OIDC flip omits the npm ≥ 11.5.1 runner requirement plus any
  failure-remediation path (npm-publish.yml has no `workflow_dispatch`
  and tag-push runs pin the workflow to the tag's tree).

## Risks

1. **R-DEV1 — HIGH — RC release-gate run is guaranteed red as written.**
   release.yml:653 resolves `VERDICT_FILE=".claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md"`,
   and validate-pair-rail-verdict.py asserts `release_tag == GITHUB_REF_NAME`.
   Wave 3 tells the ceremony to produce `pair-rail-verdict-v1.1.0.md` for the
   RC tag `v1.1.0-rc.1` → step-15 hard-fails "verdict file missing". Live-fire
   precedent: no `pair-rail-verdict-v1.0.1-rc.1.md` ever existed in history and
   the v1.0.1-rc.1 release-gate run (2026-07-03) FAILED; only the GA run went
   green after round-3. The plan's own Wave 3 check ("release-gate green on the
   RC tag") is unsatisfiable as drafted. Mitigation: Wave 3 authors
   `pair-rail-verdict-v1.1.0-rc.1.md` (release_tag `v1.1.0-rc.1`, ≤24h before
   tag push, parent_sha bound, pin+binary-sha fields); Wave 4 keeps its
   separate fresh GA verdict. Note the ≤24h TTL binds verdict authorship to
   tag-push timing for BOTH tags.
2. **R-DEV2 — HIGH — OIDC first live-fire happens at the GA publish with no
   retry rail.** RC tags skip npm-publish entirely (:54), so the flip is only
   ever exercised at the most expensive moment — after Owner approval of
   `production-npm`. Two omissions: (a) npm Trusted Publishing requires npm
   CLI ≥ 11.5.1; setup-node "20" (npm-publish.yml:65-70) bundles npm 10.x →
   the OIDC exchange never happens and publish falls back to whatever token is
   configured (with NPM_TOKEN commented out, setup-node's placeholder
   `NODE_AUTH_TOKEN` → E401). (b) npm-publish.yml has NO `workflow_dispatch`;
   a tag-push run executes the workflow AT THE TAG'S COMMIT, so a post-tag
   workflow fix on main is unreachable for `v1.1.0` — remediation would mean
   deleting/re-pushing a signed, already-released GA tag. Mitigation: the
   sentinel edit must add an explicit `npm install -g npm@^11.5.1` (or
   equivalent) step, and the debate must pick a remediation posture BEFORE
   tagging (see Must-fix 2).
3. **R-DEV3 — MEDIUM — Validate on main runs on the self-hosted `Ceo` runner,
   which is currently stuck** (S269: run 29248385951 queued 6h+; multiple
   validate.yml jobs are `runs-on: Ceo`). Release.yml and npm-publish.yml run
   on ubuntu-latest and are NOT blocked, but the plan's success criterion
   "Validate + release-gate green on the GA tag" and basic hygiene (don't cut
   an RC from a bump commit whose Validate never executed) are hostage to the
   runner being unstuck — and validate.yml's `build-plugin.py --check` +
   packlist jobs are part of what proves Wave 0 correct. Mitigation: make
   "Validate green on the Wave 0 bump commit" an explicit Wave 3 entry gate;
   keep the Owner runner-settings action from S269 as a plan prerequisite.
4. **R-DEV4 — MEDIUM — the advisory-workflow gate evaluates TWICE (once per
   tag run), and the plan only stations it in Wave 3.** All 6 advisory
   workflows are cron'd Mondays (03/06/09/12/15/16 UTC, ubuntu-latest). A red
   cron landing between RC and GA flips `latest_conclusion=failure` and blocks
   the GA run even though the RC run passed — and this morning's infra wobble
   produced exactly that class (chaos 06:11Z and perf-profile 08:44Z failures
   on 2026-07-13, both later superseded by green re-runs). Mitigation: re-check
   all 6 green/fresh immediately before the GA push too, and prefer an RC→GA
   window that does not straddle the Monday cron burst.
5. **R-DEV5 — LOW — doc-freshness is a pass-at-limit, and a stamp bump without
   content review is theater.** Checker math (check-canonical-doc-freshness.py):
   fails only when minor-behind > N. Stamps today: SECURITY v1.0.0,
   VERSIONING v1.0.0, SBOM v1.0.1 → all 1 minor behind at VERSION=1.1.0 →
   1 > 1 is false → the gate PASSES v1.1.0 with no restamp (hard requirement
   arrives at v1.2.0). Restamping now is still right — but SECURITY.md
   (reviewed 2026-05-25, v1.0.0) predates BOTH new harnesses and the /council
   cross-vendor egress this release ships; the re-review must be real.
6. **R-DEV6 — LOW — an rc.2 restarts the 24h clock.** The hold gate picks the
   most-recent `v1.1.0-rc.*` by creatordate (release.yml:261). Any respin
   resets the GA-earliest time; budget the calendar accordingly.

## Must-fix (blocking)

1. **Wave 3 verdict filename → per-tag.** Replace
   `.claude/governance/pair-rail-verdict-v1.1.0.md` with
   `.claude/governance/pair-rail-verdict-v1.1.0-rc.1.md` for the RC ceremony
   (release_tag field = `v1.1.0-rc.1`), keeping Wave 4's separate fresh
   `pair-rail-verdict-v1.1.0.md` for GA. Without this the Wave 3 check
   contradicts release.yml:653 and the v1.0.1-rc.1 red-run precedent repeats.
2. **Complete the OIDC flip mechanics in the Wave 1 sentinel edit.**
   (a) Add an npm-CLI upgrade step (`npm install -g npm@^11.5.1`) — Node 20
   bundles npm 10.x, which cannot do the OIDC exchange; (b) decide and record
   the failure playbook BEFORE tagging, choosing one of: keep the real
   `NODE_AUTH_TOKEN` env live for THIS GA (npm ≥11.5.1 attempts OIDC first and
   falls back to the token; prove OIDC afterwards via the registry's
   trusted-publisher/provenance metadata, then drop the token in v1.1.1+), OR
   ship OIDC-only (commented fallback) plus a documented re-tag recovery, OR
   add a `workflow_dispatch` re-publish path in the same sentinel edit. The
   current wording ("keep fallback behind a comment until GA proves OIDC")
   silently selects OIDC-only-with-no-recovery. Also pin the job to
   GitHub-hosted ubuntu-latest (do not migrate to `Ceo`; trusted publishing is
   documented for hosted runners).
3. **Wave 0 manifest bump must go through the generator.**
   `.claude-plugin/{plugin,marketplace}.json` are GENERATED by
   `scripts/build-plugin.py` and validate.yml:821-839 enforces
   `build-plugin.py --check` equality — a VERSION bump with hand-edited (or
   un-regenerated) manifests reds Validate. Reword the Wave 0 bullet to "run
   `python3 scripts/build-plugin.py` after the VERSION bump", keep the
   4-file grep as the after-check.
4. **Sweep the stale "151" user-facing count claims into Wave 0.** Disk truth
   is 166 skills (42 core + 8 frontend + 116 domains; verified by glob).
   README.md still claims 151 at lines 44, 54 (with a stale 42+8+101
   breakdown), 72, and 184 — and root README.md is what ships as the npm
   package README (staging rsync clobbers npm/README.md). build-plugin.py:91
   hardcodes "151 skill checklists" into the shipped plugin.json description.
   Shipping v1.1.0 whose CHANGELOG headline is "catalog 151→166" inside
   artifacts that say 151 is a self-contradicting release. Fix literals +
   regenerate manifests (+ npm/README.md hygiene).
5. **Fix the broken expiry-flag citation in Wave 1's fallback item.**
   `GOVERNANCE-MAP.md:56` does not carry the NPM_TOKEN expiry flag —
   docs/GOVERNANCE-MAP.md has no npm/token mention at all. The live flags are
   docs/PLAN-152-deferred-status.md:28 and :74, the npm-publish.yml header
   comment (lines 4-8, which also still says "tracked as a v1.0.2 follow-up"
   and must be refreshed in the same sentinel edit), and the historical
   CHANGELOG §[1.0.1] note (do not retro-edit that; state the migration in
   §[1.1.0]).

## Nice-to-have (advisory)

1. The Owner terminal script for Wave 3 should pre-run the EXACT release-gate
   set locally before the tag push: `registry.py --validate`, FULL
   `validate-governance.sh` (Wave 0's check is `--fast` only), the three
   pytest suites (hooks/scripts/replay), `check-canonical-doc-freshness.py`,
   `build-plugin.py --check`, and the npm-pack packlist dry-run — the
   pre-push-mirrors-CI lesson.
2. Make the post-publish OIDC/provenance proof explicit in Wave 4:
   `npm view ceo-orchestration@1.1.0 --json | jq .dist.attestations` (or the
   registry provenance page) alongside the npx smoke — this is the "proven
   end-to-end" evidence Wave 1 defers to.
3. Note in Wave 3 that all 6 advisory workflows carry `workflow_dispatch`
   (verified) and, as of 2026-07-13 19:12Z, all 6 are latest-green and fresh
   same-day — no pre-dispatch needed if the release executes within ~14 days
   (staleness cliff 2026-07-27 only if the Monday crons stop producing runs).
4. State that the FIRST_GA=2.0.0 waiver-sunset gate (release.yml:140-190)
   passes untouched for v1.1.0 (only 1.0.0 bootstrap entries exist) so nobody
   "fixes" it mid-release.
5. Wave 2 rider: the mechanical shape is a family filter at the
   `_command_carries_secret` call site (the bank already carries
   `family_id`/`owasp_class="LGPD"` discriminators), which keeps the diff
   small and reviewable; security-engineer's VETO lane owns the posture call.

## Unseen by the original plan

1. **The `Ceo` runner outage is not mentioned at all**, yet it currently
   blocks the "Validate green" success criterion and all `runs-on: Ceo`
   validate.yml jobs for every Wave 0 commit (R-DEV3).
2. **The advisory gate re-evaluates on the GA tag run** — freshness/red status
   must hold at two instants, not one (R-DEV4); the Monday cron burst can
   interpose between RC and GA.
3. **npm-publish.yml has no `workflow_dispatch` and tag-push runs execute the
   workflow at the tag's commit** — post-tag workflow repairs cannot reach the
   already-pushed tag; this converts any OIDC misconfiguration into a
   delete/re-tag incident unless a fallback is pre-positioned (R-DEV2).
4. **Release-artifact count-claim drift**: README.md (4× "151") and
   build-plugin.py:91 ("151 skill checklists" → plugin.json description) ship
   inside the very release whose headline is 151→166; no existing count gate
   covers these surfaces (check-claude-md-claims.py is CLAUDE.md-only).
5. **SECURITY.md content (not merely its stamp) predates the delta**: v1.1.0
   introduces two external-vendor harness surfaces and the /council egress
   path; a doc-freshness restamp without covering those is a stamp-theater
   release.
6. Gates the plan never names but that run on both tag pushes (all currently
   expected-green, listed for completeness): registry validation, full
   governance structural validation, hooks/scripts/replay pytest suites,
   audit-log schema additivity, install.sh self-SHA end-to-end validation,
   release-notes template render (template verified present, fail-closed),
   idempotent `gh release create`, and the dormant sigstore step
   (`SIGSTORE_ACTIVATED` unset — leave it dormant).

## What I would NOT change

- **Minimum-plus scope and the refusal to pull the other six PLAN-152
  deferrals into the release** — the C6 anti-pattern call is correct and the
  deadline-bound argument for backlog-oidc alone is sound (token expiry
  ~2026-09-28 is real per docs/PLAN-152-deferred-status.md; npm `latest` is
  1.0.1, published 2026-07-06 — verified live).
- **Semver minor (1.1.0)** — two new harnesses + a new command are features.
- **OQ3 default: full 24h RC-hold, no waiver** — the machinery exists but the
  precedent value of running the real gate on a real minor is worth 24h.
- **The RC exclusion (`!contains(github.ref, '-rc.')`) and
  `environment: production-npm` in npm-publish.yml stay untouched** — both
  load-bearing, test-pinned (test_release_workflow_asserts.py), and correctly
  cited by the plan.
- **Widen-upper-only pin discipline** — `<0.145.0` + binary sha `134063e1…`
  are current for codex-cli 0.144.1; nothing stale; do NOT touch the pin
  inside the release window (debate C10 rationale on record in the pin file).
- **The Wave 0 four-file grep including marketplace.json** (Codex S270 catch)
  and the **single-terminal-script-per-ceremony Owner UX** (land-plan156.sh
  pattern) — keep both.

## Appendix — task pressure-tests answered (free-form, non-schema)

- **(a) Gates unnamed by the plan:** generator contract
  (`build-plugin.py --check`, Must-fix 3); registry/full-governance/pytest/
  audit-schema/self-SHA/notes-template/idempotent-create (Unseen 6); waiver
  sunset FIRST_GA (passes; Nice-to-have 4); GA-side advisory re-evaluation
  (Unseen 2). Doc-freshness detail: plan slightly overstates — v1.1.0 passes
  at-limit without restamp; v1.2.0 is where it hard-blocks (R-DEV5).
- **(b) OIDC flip:** `id-token: write` already present (workflow-level,
  npm-publish.yml:39-41); `registry-url` already set (:70); the REAL missing
  pieces are npm ≥ 11.5.1 on the runner (Node 20 ships npm 10.x) and the
  no-dispatch/tag-pinned-workflow remediation gap. Coexistence: yes, the
  commented token path does not break the flip mechanically — setup-node
  exports a placeholder `NODE_AUTH_TOKEN` when `registry-url` is configured,
  so config parsing survives token removal; but commented-out = zero fallback
  at tag time (Must-fix 2).
- **(c) Packlist vs delta:** staging rsync is selective enough. New
  `templates/grok/` + `templates/codex/` trees carry no tests/ or fixtures/
  dirs (verified) and SHOULD ship (install.sh --harness consumes them,
  verified at install.sh:555-682, :2374-2394); new plans are excluded by
  `.claude/plans/PLAN-[0-9]*`; workflows live under .github/ which is never
  staged; grok golden fixtures fall under the global `**/fixtures/` exclude
  (test-only, correct). The packlist gate also runs on PR/push via
  validate.yml:1021-1068, so drift would have been caught continuously. One
  real artifact-content issue found: the README/plugin-description 151-drift
  (Must-fix 4).
- **(d) Advisory freshness at plausible execution time:** none of the 6 needs
  pre-dispatch — all are latest-green with same-day runs (2026-07-13); the
  binding risk is red-cron interposition between RC and GA, not staleness
  (R-DEV4).
- **(e) Per-tag verdicts:** GA correctly captured; RC incorrectly captured
  (GA-named file) — Must-fix 1, with the v1.0.1-rc.1 red run as precedent.
