---
id: PLAN-158
title: Release v1.1.0 — ship PLAN-153..156 + OIDC before token expiry
status: reviewed
created: 2026-07-13
reviewed_at: 2026-07-13
reviewed_by: "Owner (chat ratification, S270)"
owner: CEO
depends_on: [PLAN-153, PLAN-154, PLAN-155, PLAN-156]
budget_tokens: 120-180k
budget_sessions: 2
context_risk: medium
external_wait: npm-console-trusted-publisher (Owner) + RC-hold 24h (ADR-103)
tags: [release, npm, oidc]
---

# PLAN-158 — Release v1.1.0

## Context

npm `ceo-orchestration@latest` is still **v1.0.1** (2026-07-06). Since
then main accumulated 55 commits, all shipped plans: PLAN-153 (ecc uplift
— catalog 151→166, security gates, installer lifecycle, release.yml
fixes), PLAN-154 (gated learning loop), PLAN-155 (Codex host-harness
compat), PLAN-156 (Grok third harness + `/council` cross-vendor council +
GPT-5.6 codex pin). New harnesses and a new command are **features →
semver minor → v1.1.0** (not 1.0.2).

Two premises from the original backlog were re-verified S270 and are
**already resolved**: the 2 latent release.yml bugs (RC-version-mismatch,
hardcoded release notes) were fixed in PLAN-153 Wave B5 (`2094175`; live
at release.yml:55-70, :293-310, :725-788). The PLAN-152 §Deferred ledger
(tracker: `docs/PLAN-152-deferred-status.md`, re-verified S270) has **7
items still open**, of which exactly one carries a calendar deadline:
**backlog-oidc — the granular `NPM_TOKEN` expires ~2026-09-28** (flags:
docs/PLAN-152-deferred-status.md:28/:74 + the npm-publish.yml header;
the GOVERNANCE-MAP.md:56 citation is stale — W0 rider fixes it). v1.1.0
is plausibly the last release before that date.

> Debate round 1 (S270): 3×ADJUST → PROCEED, security VETO not
> exercised; 7 consensus adjustments applied
> (`PLAN-158/debate/round-1/consensus.md`). Standing precondition: main
> Validate green (satisfied S270 at `9b09f7c`; re-verify at execution
> start).

## Goal

Signed `v1.1.0` GA live on GitHub Releases + npm (`npx ceo-orchestration`
smoke rc=0), with npm auth either migrated to Trusted Publishing (OIDC)
or the token expiry risk explicitly re-dated by the Owner.

## Approach

**Scope: minimum-plus** (S270 dossier recommendation). The release is a
vehicle — all feature work is already on main. We ship the ceremony
itself plus exactly one deferral, backlog-oidc, because it is
deadline-bound to this release window. The other six open PLAN-152
deferrals (governance-04/07 kernel work, `_lib/tests` env-hygiene
burndown, nested-subagent red-team corpus, canonical-models sonnet5
refresh, PLAN-128 wave1 tooling) have their own successor tracks and gain
nothing riding a release plan; pulling kernel ceremonies into a release
was explicitly the anti-pattern debate C6 rejected for v1.0.1.

One small rider is proposed as OQ2 (debate decides): the
`check_adversary.py` secret-in-command scan currently swallows numeric
BR-PII checksum collisions (S270 live incident: benign GitHub run id
`29248385761` is a checksum-valid CPF, blocking every command containing
it, with no env escape by design). Fix = restrict the pre-exec Bash scan
to token/credential families (check_adversary.py:120-123); PII redaction
stays on the egress rail where it belongs. Canonical hook → needs
sentinel ceremony; it is small, security-tightening-in-spirit
(fail-closed retained for real credentials), and this release already
pays the ceremony cost.

## Waves

### Wave 0 — debate + version prep (unguarded)
Check: bash .claude/scripts/validate-governance.sh --fast
- [ ] Debate L3 (`/debate start PLAN-158`); fold adjustments; Owner
  ratifies OQ1-OQ3 at `draft → reviewed`.
- [ ] Bump the version triple: `VERSION`=1.1.0, `npm/package.json`; the
  plugin manifests regenerate via `scripts/build-plugin.py` (validate.yml
  runs its `--check` — do NOT hand-edit; debate Critic-C).
  Check: grep -l "1\.1\.0" VERSION npm/package.json .claude-plugin/plugin.json .claude-plugin/marketplace.json | wc -l  # must print 4 (Codex S270: marketplace.json missing from the check let a stale manifest pass)
- [ ] CHANGELOG `## [1.1.0]` section (release.yml:293-310 gate) — delta
  grouped by PLAN-153/154/155/156, no speed claims.
  Check: grep -n "## \[1.1.0\]" CHANGELOG.md
- [ ] Doc-freshness: VERIFY first — live check S270 says stamps pass
  at-limit for a 1.0→1.1 bump without restamp; restamp only what the
  gate actually flags.
  Check: python3 .claude/scripts/check-docs-freshness.py --format=text
- [ ] Stale-claims riders: README says "151 skills" in 4 places +
  plugin.json description says 151 (disk truth: 166) — both slip the
  mechanical gates. Fix here (dedup: PLAN-157 W1 carries an overlapping
  README rider; whichever lands first takes it). Also fix the stale
  NPM_TOKEN-expiry citation (GOVERNANCE-MAP.md:56 → the real flags).
  Check: grep -rniE "151[^0-9]{0,3}(skill|checklist)" README.md .claude-plugin/plugin.json scripts/build-plugin.py | wc -l  # must print 0 — broad pattern (Codex S270: "151 skills" alone misses "151 skill files"/"**151**"/"151 skill checklists"; bare "151" would false-positive on PLAN-151 refs)

### Wave 1 — backlog-oidc: npm Trusted Publishing
Check: none (Owner console work + guarded workflow edit; mechanical proof lands at the Wave 4 GA publish — RC tags skip npm-publish entirely, so no earlier proof point exists)
- [ ] **Owner (web console, prereq):** configure the GitHub Actions
  trusted publisher for `ceo-orchestration` on npmjs.com
  (repo `Canhada-Labs/ceo-orchestration`, workflow `npm-publish.yml`,
  environment `production-npm`).
- [ ] Flip `npm-publish.yml` publish step to OIDC — **guarded workflow →
  sentinel ceremony**, scope MUST also carry the kernel-guarded
  `SPEC/v1/npm-shim.md` doc cascade (PLAN-152 §Deferred assigned it to
  this flip) with per-file pair-rail verdicts. The sentinel scope ALSO
  carries the auth-doc cascade on the SUCCESS path (Codex S270):
  `.github/workflows/GOVERNANCE-MAP.md` and `scripts/install-npm.sh`
  both currently state token auth is live / Trusted Publishing is not
  configured — update them in the same ceremony, not only under the
  fallback. Mechanics (debate, all 3 critics): add `id-token: write`
  permission + an explicit **npm CLI ≥11.5.1 upgrade step** (Node 20
  bundles npm 10.x — without it the token exchange never happens and GA
  dies ENEEDAUTH); `--provenance` keeps working; keep `NPM_TOKEN`
  fallback behind a comment with the **rollback diff pre-staged in the
  same sentinel**.
- [ ] Failure playbook (mandatory — npm-publish.yml has NO
  workflow_dispatch and tag runs pin the workflow to the tag's tree): a
  failed OIDC-only GA publish means delete/re-tag with the rollback
  diff applied. Document the exact command sequence in the wave.
- [ ] After the GA publish proves OIDC end-to-end: **explicitly REVOKE**
  the old granular token (not just stop using it) and record revocation.
- [ ] Fallback if Owner defers OIDC (OQ1): regenerate the granular
  token NOW, re-date the expiry flags (deferred-status tracker +
  npm-publish.yml header), fix the stale GOVERNANCE-MAP citation.

### Wave 2 — rider: check_adversary PII-collision fix (OQ2-gated; OWN conditional sentinel)
Check: python3 -m pytest .claude/hooks/tests/ -q -k adversary
- [ ] Debate upgraded this from "optional" to **spec-conformance**: the
  E1 gate's own docstring scopes it to live credentials — ALL_PATTERNS
  exceeded the spec. FP class is wider than CPF: `br_rg` blocks ANY
  bare 8-9 digit run (validator=None, no context gate). Restrict
  `_command_carries_secret` to token/credential families
  (check_adversary.py:120-123) + regression tests (CPF-shaped run id
  allowed; 8-9 digit bare run allowed; npm/ghp/PEM/aws forms still
  denied/ask — verified live by the security critic).
- [ ] **Security guardrails (VETO lines, recorded):** no PII family is
  DELETED from the shared catalog (egress-redact keeps consuming them);
  the unconditional credential fail-closed path is untouched; no RC
  dist-tag npm publish to "prove OIDC early".
- [ ] Ceremony vehicle: its OWN sentinel (exact-scope, per-file
  verdict), scheduled with Wave 1's when OQ1=OIDC, standalone when
  OQ1=fallback (debate: riding W1 breaks under fallback).
- [ ] If Owner rejects OQ2: record refusal in §Clarifications and drop
  the wave.
  Check: none (doc-only)

### Wave 3 — RC ceremony
Check: gh run list --workflow release.yml --limit 1 (release-gate green on the RC tag)
- [ ] Codex pair-rail verdict for the RC: signed
  **`.claude/governance/pair-rail-verdict-v1.1.0-rc.1.md`** — the gate
  keys the filename on `GITHUB_REF_NAME`, so the RC tag needs an
  RC-named verdict (debate consensus #1; precedent: v1.0.1-rc.1's gate
  run failed and no RC verdict ever existed in history). ≤24h old,
  bound to parent sha, codex-cli inside `codex-cli-pin.txt` (<0.145.0)
  + binary sha256 (release.yml:641-695 hard-block).
- [ ] Advisory-workflow freshness gate (release.yml:457-557): all 6
  advisory workflows non-red AND fresh ≤14d; manual dispatch any stale
  one BEFORE cutting the tag (the v1.0.1 lesson — otel/adapter needed
  dispatch).
  Check: gh run list --limit 20 --json workflowName,conclusion,createdAt
- [ ] **Owner:** cut signed `v1.1.0-rc.1` (VERSION already 1.1.0;
  release.yml:42-53 RC flow). RC runs the full gate, publishes GitHub
  prerelease, does NOT touch npm (npm-publish.yml:54).
- [ ] RC-hold 24h (ADR-103; release.yml:231-291) — Codex re-pass window.
  Waivable only via `rc_hold:` in governance-waivers.yaml. NOTE
  (debate): the advisory-freshness gate evaluates AGAIN at GA — a
  scheduled cron (e.g. Monday) can interpose a red between RC and GA;
  if so, re-dispatch the affected advisory workflow before the GA tag.
  Check: none (calendar wait)

### Wave 4 — GA + publish
Check: npx ceo-orchestration@latest --help exits 0 (post-publish smoke)
- [ ] Fresh pair-rail verdict for the GA tag: signed
  `.claude/governance/pair-rail-verdict-v1.1.0.md` (verdicts are
  per-tag, filename keyed on the tag name).
- [ ] **Owner:** cut signed `v1.1.0` GA (signature verified against
  `.claude/trust/owner.asc`, release.yml:588-610); release-gate suites +
  smoke install + SBOM must pass (release.yml:312-433).
- [ ] **Owner:** approve the `production-npm` environment gate
  (npm-publish.yml:56); publish runs with provenance; verify
  `already_published` guard honored on any re-run.
- [ ] Closeout: plan → done with `completed_at` + `related_commits`;
  memory + CLAUDE.md version references updated at session closeout.
  Check: python3 .claude/scripts/check-claude-md-claims.py

## Open questions

- **OQ1 (OIDC vs re-token)** — OIDC needs Owner npm-console work
  unverifiable by CI. If deferred again: regenerate the token NOW and
  re-date the flag — v1.1.0 must not ship leaving a September release
  cliff silent. CEO default: do OIDC in this release.
- **OQ2 (check_adversary rider)** — include the PII-collision fix
  (Wave 2)? CEO default: yes — debate upgraded it to spec-conformance
  (the gate's own docstring scopes it to live credentials) and the
  security critic verified SECRETS-only keeps all credential forms
  fail-closed; VETO explicitly not exercised, guardrails recorded in
  the wave.
- **OQ3 (RC-hold)** — full 24h hold or waiver? CEO default: full hold
  (no urgency justifies waiving; the sunset gate watches waiver abuse).

## Clarifications

- 2026-07-13 (S270, Owner via structured tie-break): OQ1 → selected
  **"OIDC nesta release (Recomendado)"** — Trusted Publishing migrates
  in this release; Owner configures the npmjs trusted publisher before
  Wave 1; token revoked after GA proof.
- 2026-07-13 (S270, Owner): OQ2 + OQ3 → selected **"Ratificar os 4
  (Recomendado)"** (block with FOLLOWUP OQs) — check_adversary rider IN
  (Wave 2, own conditional sentinel, security guardrails recorded);
  RC-hold full 24h, no waiver.

## How to continue

Read this plan; check `git tag -l 'v1.1.*'` and npm dist-tags to locate
the current step. Wave order is strict (0→4); Waves 3-4 are Owner-gated
(signed tags + production-npm approval) — prepare everything, then hand
the Owner a single terminal script per ceremony (the `land-plan156.sh`
pattern). Release mechanics reference: release.yml:38-53 (RC flow),
:641-695 (verdict gate), npm-publish.yml:105-204 (staging+packlist).

## Success criteria

- [ ] `v1.1.0` GA on GitHub Releases with SBOM + install.sh.sha256.
- [ ] npm `ceo-orchestration@latest` = 1.1.0; `npx` smoke rc=0.
- [ ] npm auth: OIDC trusted publisher live, OR token regenerated with
  expiry re-dated and flagged.
- [ ] No open `[NEEDS CLARIFICATION]` markers; all OQs ratified.
- [ ] Validate + release-gate green on the GA tag.
