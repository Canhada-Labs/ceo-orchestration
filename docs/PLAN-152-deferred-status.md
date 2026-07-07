# PLAN-152 §Deferred — consolidated disposition record

> **Date:** 2026-07-07 (post-v1.0.1 backlog pass, PLAN-153 cycle)
> **Source of truth:** `.claude/plans/PLAN-152-v1-0-1-hardening-sweep.md` §Deferred
> (lines 203–262 at the time of writing). This note records where each deferred
> item stands NOW — what has been authored/staged, what remains deferred, and
> which items are blocked on an Owner-only prerequisite. It claims **no**
> protection that has not actually landed: "staged" means the artifact exists
> under `.claude/plans/PLAN-153/staged/` (gitignored, `.gitignore:17`) and the
> LIVE tree is unchanged until the Owner's GPG sentinel ceremony lands it.

## Count reconciliation

PLAN-152 §Deferred contains **10 active entries** — the 8 original defers plus
2 latent `release.yml` bugs discovered in the S260 GA-tag live-fire — and 1
struck-through entry (`tests-07`, pulled back into Wave B by debate C2 and
completed in v1.0.1, commit `0396b71`). All 11 are enumerated below; none are
silently dropped.

## Summary table

| # | Item | Disposition (2026-07-07) | Vehicle / prerequisite |
|---|---|---|---|
| 1 | `governance-04` — kernel-paths expansion | **Deferred** (unchanged) | Own follow-on plan: dedicated ADR + kernel ceremony |
| 2 | `governance-07` — NotebookEdit coverage | **Deferred** (unchanged) | Folds into the governance-04 plan |
| 3 | ~~`tests-07`~~ — serial markers | **Resolved in v1.0.1** (not deferred) | Done, commit `0396b71` (Wave B, debate C2) |
| 4 | `burndown-lib-tests` — 128-site `_lib/tests` env-hygiene | **Deferred** (unchanged) | v1.0.2; ceremony-scoped (`.claude/hooks/_lib/**` canonical-guarded) |
| 5 | `backlog-oidc` — npm Trusted Publishing | **Deferred** (unchanged) | v1.0.2 plan; **Owner web-console prereq**; NPM_TOKEN expires ~2026-09-28 |
| 6 | `nested-subagent-redteam` — red-team corpus cases | **Deferred** (unchanged) | v1.0.2 / follow-on scoped corpus effort |
| 7 | `canonical-models-sonnet5-entry` — pricing entry | **Deferred** (unchanged) | **Owner prereq**: next Owner-run `build-canonical-models.py --fetch` refresh |
| 8 | `spec-npm-shim-oidc-wording` — SPEC false-claim fix | **Addressed — STAGED** (this pass) | Owner GPG ceremony; sentinel Scope must carry `SPEC/v1/npm-shim.md` (Amends clause, PLAN-085 E.5) |
| 9 | `plan128-wave1-tooling` — measurement tooling gap | **Deferred** (unchanged) | v1.0.2; **Owner prereq**: private-archive access for the de-identified restore |
| 10 | `release-gate-rc-version-mismatch` — RC tag reds its own run | **Addressed — STAGED** (PLAN-153 Wave B item B5) | Owner GPG ceremony (SENT-B series) |
| 11 | `release-notes-hardcoded-first-release` — stale notes string | **Addressed — STAGED** (PLAN-153 Wave B item B5) | Owner GPG ceremony (SENT-B series) |

Net: **3 addressed in staged form** (pending Owner ceremony — nothing live yet),
**7 remain deferred with successor targets**, **1 was already resolved** inside
v1.0.1 itself.

## Per-item detail

### 1. `governance-04` — 15 registered hooks absent from `_KERNEL_PATHS`
- **Where:** `check_arbitration_kernel.py:76`; PLAN-152:205-211.
- **Status:** deferred, unchanged. No PLAN-153 staged wave touches
  `check_arbitration_kernel.py` (wave-E stages `check_bash_safety.py`,
  `check_harness_config.py`, `check_agent_spawn.py` only).
- **Successor:** its own follow-on plan — kernel expansion needs a dedicated
  ADR + ceremony; explicitly judged too large for a hotfix release.

### 2. `governance-07` — `NotebookEdit` not covered by canonical-edit/arbitration matchers
- **Where:** PLAN-152:212-214. Exploitability bounded to `.ipynb`-parseable
  guarded targets.
- **Status:** deferred, unchanged. **Successor:** folds into the governance-04
  kernel-matcher plan (same matcher surface, same ceremony).

### 3. ~~`tests-07`~~ — serial markers on wall-clock perf test classes
- **Status:** NOT a deferred item — pulled into Wave B by debate consensus C2
  and completed in v1.0.1 (commit `0396b71`). Listed only because the struck
  entry still appears inside the §Deferred section body (PLAN-152:215-216).

### 4. `burndown-lib-tests` — the 128-site `_lib/tests` env-hygiene burndown
- **Where:** PLAN-152:217-219 (debate C8).
- **Status:** deferred, unchanged. The files are canonical-guarded
  (`.claude/hooks/_lib/**/*.py`), making this the largest ceremony-scoped
  item; it travels WITH its `_DEFAULT_SCAN_ROOTS` tuple entry.
- **Successor:** v1.0.2.

### 5. `backlog-oidc` — npm Trusted Publishing migration
- **Where:** PLAN-152:220-222 (debate C6).
- **Status:** deferred, unchanged. **Owner-console prerequisite:** registering
  the trusted publisher happens on the npmjs.com web console — not CI-verifiable,
  Owner-only. Migration plan must keep a fallback window (NPM_TOKEN stays until
  the first OIDC publish succeeds).
- **Standing risk flag (live):** NPM_TOKEN (repo-scoped granular token, env
  `production-npm`) **expires ~2026-09-28** — calendar-flagged at
  `.github/workflows/GOVERNANCE-MAP.md:56` and `CHANGELOG.md` (v1.0.1 entry).
  Any release after expiry fails at publish until the token is regenerated or
  Trusted Publishing lands.
- **Successor:** v1.0.2 plan; item 8 below rides its sentinel if not landed earlier.

### 6. `nested-subagent-redteam` — corpus cases for nested subagents + background auto-push
- **Where:** PLAN-152:223-229 (Wave F execution decision, via the item's own
  escape clause). Net-new substrate scope — NOT one of the 41 audit findings.
- **Status:** deferred, unchanged. A quality corpus addition needs its own
  scoped effort against `SPEC/v1/red-team-corpus.schema.md` (flake budget,
  provenance). **Successor:** v1.0.2 / follow-on plan.

### 7. `canonical-models-sonnet5-entry` — no `claude-sonnet-5` pricing entry
- **Where:** PLAN-152:230-235. `.claude/data/canonical_models.json` is
  provenance-stamped + checksum-protected (PLAN-133 B1); the ONLY sanctioned
  write path is the Owner-run `build-canonical-models.py --fetch` from models.dev.
- **Status:** deferred, unchanged. ADR-157 records the cost/capability envelope
  in-repo meanwhile. **Prerequisite:** Owner-run refresh (not authorable by an
  agent by design). **Successor:** next Owner models.dev refresh.

### 8. `spec-npm-shim-oidc-wording` — SPEC/v1 false "OIDC trusted publisher" claim
- **Where:** `SPEC/v1/npm-shim.md:54` (live) still says CI publishes "via OIDC
  trusted publisher" — same false-claim class as the `npm-publish.yml` header
  fixed by PLAN-152 tarball-01. All non-SPEC surfaces were already corrected in
  v1.0.1 (workflow header `npm-publish.yml:4-7`, `scripts/install-npm.sh:22-23`
  and `:60`, `.github/workflows/GOVERNANCE-MAP.md:56`).
- **Status:** **addressed in STAGED form (this pass).** A complete corrected
  copy is staged at
  `.claude/plans/PLAN-153/staged/wave-backlog/SPEC/v1/npm-shim.md`
  (base = LIVE at `314891a`, base sha256
  `bcc928227f00c63128aa3c209be6b9b839df0832ab495d461b0aa60ffb157f95`).
  Changes: §Publishing rewritten to the shipped mechanism (granular-token auth
  behind the `production-npm` manual gate; per-run OIDC JWT used ONLY for the
  Sigstore `--provenance` attestation; Trusted Publishing explicitly "NOT
  configured", tracked v1.0.2); ADR-012 cross-ref annotated as target
  end-state; spec version bumped `1.0.0-rc.1 → 1.0.1-rc.1` with a Version
  history row (benchmarks.schema.md amendment precedent). Documentation
  correction only — no contract or behavioral change.
- **Honesty residual:** the LIVE spec still carries the false claim until the
  ceremony lands. `SPEC/**` is kernel-guarded (`deny: Edit(SPEC/**)`) and is
  NOT in the PLAN-152 sentinel Scope; landing requires an Owner GPG sentinel
  whose Scope carries `SPEC/v1/npm-shim.md` — via an **`Amends:` clause
  (PLAN-085 E.5)** on a PLAN-153 sentinel, or by riding the backlog-oidc
  v1.0.2 plan sentinel as originally pointed (PLAN-152:236-242). Staging now
  simply gives the Owner the earlier option.

### 9. `plan128-wave1-tooling` — `measure_multiplier.py` stripped in the clean-room migration
- **Where:** PLAN-152:243-249. `measure-state.sh` FATALs at preflight;
  `install-accelerators.sh:162` prints a command guaranteed to fail for
  adopters. Documented in `PLAN-128-sota-solo-accelerator.md` §Known gap.
- **Status:** deferred, unchanged. **Prerequisite:** restoring a de-identified
  copy requires Owner access to the private archive; the alternative
  (degrading the artifacts) is agent-authorable but is a product decision.
- **Successor:** v1.0.2.

### 10. `release-gate-rc-version-mismatch` — RC tags can never pass their own release run
- **Where:** PLAN-152:250-259 (S260 live-fire; red run 28663453202 —
  `v1.0.1-rc.1` vs `VERSION=1.0.1`).
- **Status:** **addressed in STAGED form** by PLAN-153 Wave B item B5 (a
  sibling author, this same cycle): staged
  `.claude/plans/PLAN-153/staged/wave-B/.github/workflows/release.yml` strips
  `-rc.[0-9]*` before the VERSION comparison AND applies the same strip to the
  "Assert CHANGELOG entry exists" step (same bug class). See
  `staged/wave-B/MANIFEST-B5.md` for base hashes, behavior-change disclosure
  (RC tags will get green `--prerelease` release runs; npm posture unchanged —
  RC tags remain job-level excluded from npm-publish), and gate results.
- **Honesty residual:** live `release.yml` is unchanged until the SENT-B
  ceremony lands; the next RC cut before landing still reds its own run
  (harmless to GA, as documented in the plan).

### 11. `release-notes-hardcoded-first-release` — notes hardcode "first public release"
- **Where:** PLAN-152:260-262 (same S260 live-fire, same guarded file).
- **Status:** **addressed in STAGED form** by the same B5 staged `release.yml`:
  the `gh release create` step is replaced by render-from-template +
  view/upload-clobber/create idempotency; `.github/release-notes-template.md`
  is already live and inert (not canonical-guarded; fail-closed — the staged
  workflow errors if the template is absent).
- **Honesty residual:** same as item 10 — nothing live until SENT-B lands.

## Landing / coordination notes

- **Staged-tree layout:** this pass adds `staged/wave-backlog/` containing
  ONLY `SPEC/v1/npm-shim.md`. It does NOT touch `.claude/settings.json` — the
  settings surface in the backlog cycle belongs to the sibling settings
  authors; no merge conflict is possible from this file set.
- **Sentinel scope math at landing:** whichever sentinel lands the SPEC fix
  must enumerate `SPEC/v1/npm-shim.md` (Amends clause per PLAN-085 E.5 if the
  signed Scope predates it), and the standard `touched − scope = ∅` re-check
  applies. Items 10–11 land under the Wave B sentinel series per MANIFEST-B5.
- **No new tests:** the SPEC fix is documentation-only (no content pin exists —
  verified: no test/script greps `npm-shim.md` content; `check-spec-drift.py`
  covers `plan.schema.md` only). B5's staged workflows carry their own test
  file (`.claude/scripts/tests/test_release_workflow_asserts.py`, already
  landed direct).
