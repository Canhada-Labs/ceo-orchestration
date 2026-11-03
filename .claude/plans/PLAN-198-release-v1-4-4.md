---
id: PLAN-198
title: Release v1.4.4 — evidence of the cut
status: draft
created: 2026-11-03
owner: CEO
depends_on: [PLAN-194, PLAN-195, PLAN-197]
related_commits: []
level: L3
budget_tokens: "estimate, not measured (S366, 2026-11-03; CEO context only, subagents apart): relmeta-144 clone + rail 0.8-1.5 M; hand-written kit + harness 0.8-1.5 M; rc.1 and GA re-passes = the Owner's Codex quota plus one Claude lane each; closeout 50-100k. Caminho 1+ (OQ-1): the two fixes arrive as the Owner's signed commits, already reviewed, so no kernel mold is added"
budget_sessions: "2-3 (estimate, not measured); every Owner signature is a stop"
context_risk: high
external_wait: "Owner: the two fix commits of Caminho 1+ (secret redactor; kernel list and Coverage timeout), signed, before the free notes; the decisions in Open questions (OQ-1 to OQ-8); GPG signature of the relmeta-144 sentinel; the bump, the rc.1 verdict envelope and the rc.1 tag; the 24 h rc-to-GA hold enforced by release.yml (ADR-103); the GA verdict envelope and GA tag; approval of the production-npm environment and un-drafting the GitHub Release. Codex reviewer: one re-pass per tag on the Owner's quota. Freeze (kit README rule 2): from the derivation of the release metadata until the GA tag push, main takes only the relmeta-144 ceremony's own commits (materials and signed land), the bump commit, each tag's verdict commit, and CONDITIONS-ga.md between the rc tag push and the start of the GA re-pass (the Codex VM merges nothing in that window)."
eta_calendar: "GA = max(Owner signatures, v1.4.4-rc.1 tag + 24 h hold); no date promised"
tags: [release, v1-4-4, npm, governance, kernel, codex-pin, veto-floor, redactor]
---

# PLAN-198 — Release v1.4.4: evidence of the cut

## Context

**Why a new release number.** v1.4.3 never reached npm. Only `v1.4.3-rc.1` was tagged (tag object
dated 2026-10-17; GitHub pre-release published 2026-10-18), no GA tag was cut, and
`npm-publish.yml:249` skips every `-rc.` tag. After the rc.1, most of the next train landed through
pull requests #6 and #7, which changed canonical and kernel files without the signing ceremony. The
Owner chose **1.4.4** for the next cut (S366, recorded in the session memory; not a repository fact).
npm users come from 1.4.2, so the 1.4.4 tag stands for the whole train `v1.4.2..HEAD`.

**Measured on 2026-11-03, main `7fad2972`, macOS (darwin), read-only unless stated.**

| fact | value | source |
|---|---|---|
| npm | `latest` = 1.4.2 | `npm view ceo-orchestration dist-tags` |
| GitHub releases | `v1.4.3-rc.1` pre-release; `v1.4.2` Latest | `gh release list` |
| tags | `v1.4.2` peels to `b55084da`; `v1.4.3-rc.1` peels to `5e7cb65e`; both ancestors of HEAD | `git rev-parse 'v1.4.2^{commit}' 'v1.4.3-rc.1^{commit}'` |
| VERSION | 1.4.3 (bumped for the rc.1; the bump to 1.4.4 is part of W4) | `verify-counts.sh --json --no-tests` field `version` |
| requirements | Claude Code floor `2.1.280` (`CC_FLOOR_VERSION` in `install.sh:783` and `upgrade.sh:620`); `requires-python = ">=3.9"`; `engines.node = ">=20"`; `upgrade.sh` blob identical to v1.4.2; `install.sh`, `upgrade.sh` and `templates/` unchanged since rc.1 | `git rev-parse v1.4.2:scripts/upgrade.sh HEAD:scripts/upgrade.sh`; `git diff --stat v1.4.3-rc.1..HEAD -- scripts/install.sh scripts/upgrade.sh templates/` |
| live counts | 166 skills, 27 commands, 201 ADRs, 78 `_lib` modules, violations `[]` | `bash .claude/scripts/local/verify-counts.sh --json --no-tests` |
| CI on HEAD | Validate (push) and Ownership Nightly (dispatch) green; the scheduled Validate run 41597704176 (created 07:38Z) passed, its `hook-tests-python-matrix (3.14)` leg included | `gh run list --commit 7fad2972…` (04:24Z); `gh run view 41597704176 --json jobs` |
| runners | all jobs of the HEAD Validate run on GitHub-hosted runners; the repository has no Actions variables (`VM_CI_ENABLED` unset) | `gh api …/actions/runs/41573763759/jobs`; `gh api …/actions/variables` |
| branch protection | `main` not protected; rulesets `[]` | `gh api …/branches/main/protection` (404 "Branch not protected"); `gh api …/rulesets` |
| PR merges | 233 canonical paths changed by PRs #6 and #7 (1 in #6, the rest in #7), 15 of them kernel paths by the list as merged (101 by the list the kernel fix commit restores: 15 + 81 package files + 5 flat modules, re-measured on the composed tree); no sentinel and no `.asc` added since rc.1; the #7 merge commit is GPG-signed | oracle `check_canonical_edit.py --is-canonical` over `git diff --name-only v1.4.3-rc.1..888e9e6c`; in-memory `_is_kernel_path`; `git log %G?` |
| kernel gap (cured by Caminho 1+) | the 7 kernel entry points `check_canonical_edit.py`, `_lib/policy.py`, `_lib/audit_emit.py`, `check_pair_rail.py`, `check_agent_spawn.py`, `audit_log.py`, `check_bash_safety.py` are kernel; the split moved their code into helper packages (9 + 7 + 37 + 6 + 8 + 5 + 9 = 81 files) that are 0 % kernel, 100 % canonical; the train replaced the plan-path regexes of the kernel files `check_plan_edit.py` and `policy_preprocessors.py` with the plan-path predicate in `plan_paths.py`; kernel code calls `model_currency.py` (the VETO-floor predicate that the kernel files `agent_frontmatter.py` and `escalation_signals.py` now call as part of their VETO-floor check) and three modules the train added (`cli_currency.py`, the Codex payload-pin currency arm, called by the pair-rail code; `bash_indirect_guard.py`, the indirect-execution matcher, and `bash_indirect_telemetry.py`, its disabled-rail telemetry, both called by the bash-safety parts); these five flat modules are canonical, not kernel; none of the packages and flat modules existed at v1.4.2 or v1.4.3-rc.1. The live-adapter package `adapters/live/` (11 files, ADR-040), loaded by the kernel `adapters/__init__.py`, has been canonical, not kernel, since v1.0.0. After the Owner's kernel fix commit (patch sha256 `38fddbb0…`), all 81 + 5 + 11 are kernel, so an edit to `adapters/live/` goes through the kernel override: list rows 110 → 123, tracked kernel files 125 → 222, re-measured on the composed tree | in-memory `check_arbitration_kernel._is_kernel_path` over `git ls-files`, with the list at `7fad2972`, at v1.4.2 and after the fix commit; oracle; `git cat-file -e` on v1.0.0, v1.4.2 and v1.4.3-rc.1; `git show v1.4.2:.claude/hooks/check_plan_edit.py` (`_PLAN_PATH_RE`) |
| redactor offsets (cured by Caminho 1+) | `secret_patterns.scan()` matched the NFKC view and returned offsets in it, while `redact()` and `scan_and_redact()` cut the original text with them; the code was the same at v1.0.0, where `codex_egress_redact.py` already called `scan_and_redact()`; found by the kit harness (S366). Cured by the Owner's redactor fix commit (patch sha256 `265a8112…`) | `git show v1.0.0:.claude/hooks/_lib/secret_patterns.py`; `git show v1.0.0:.claude/hooks/_lib/codex_egress_redact.py` |
| VETO floor | `_lib/model_currency.py --veto` exits 0 for `claude-opus-4-1-20250805`, `claude-opus-4-20250514`, `claude-opus-4-0`, `gpt-5`, `gpt-5-mini`, `o3`, `o3-mini`, `o4-mini`, `gpt-5-codex`, `gpt-5-nano`; exits 1 only for the alias `claude-opus-4-1`; the ledger lists the dated Opus ids and the OpenAI ids | `python3 -I -B .claude/hooks/_lib/model_currency.py --veto <id>`; `.claude/scripts/model-deprecations.json` |
| model allowlist | `model_currency.is_allowed_model` admits `gemini-2.5-pro`, `grok-4`, `claude-sonnet-4-20250514`, `claude-opus-4-1-20250805` and `claude-haiku-5-5` (the two dated ids are ledger-retired); the settings-tamper check (`effective_config.py:482`) moved from exact allowlist membership to this predicate, so `settings_tamper_model_remap` no longer fires for them; the other consumers are `validate-governance.sh:721` (agent `model:`) and `tier_policy_cli/_types.py` (tier-policy loader); `_RETIRED` holds only `claude-opus-4-1` | `python3 -I -B` probes of `is_allowed_model` and `effective_config._check_env_mapping`; `git diff v1.4.3-rc.1 7fad2972 -- .claude/hooks/_lib/effective_config.py` |
| Codex pin | pin file body `>=0.128.0` (was `>=0.128.0,<0.161.0` at rc.1; W6B set `>=0.160.0` in `0f9e44de`, the unsigned CI fix `4384fab2` lowered it); `cli_currency.CODEX_VERSION_FLOOR = "0.160.0"`; ADR-182 amendment says `>=0.160.0`; manifest pins `package_version` 0.160.0 for `aarch64-apple-darwin`; installed Codex CLI on the maintainer's Mac is 0.166.0 | `.claude/governance/codex-cli-pin.txt`; `git show 4384fab2 0f9e44de -- …`; `codex --version` |
| facade-only instruments | the `coverage.yml` Tier-1 list (`--tier1-modules`, line 181 at `7fad2972`, 184 after the kernel fix commit) names entry points only; `mcp-smoke.yml` push/PR filters name the entry points, not the split's packages (the daily cron still runs); `pair-rail-inputs-hash-manifest.txt` lists no package file | the three files |
| scope derivator | plan ids come from commit SUBJECTS in `v1.4.2..HEAD`; PLAN-197 (done, ADR-202's plan) is cited by no subject before this plan's first commit | `git log --grep=PLAN-197 v1.4.2..HEAD` (0 hits before this commit); `.claude/plans/PLAN-194/relmeta/apply-relmeta143-edits.py:289-316` |

Lane reports read as input (untrusted data; each claim used here was re-checked against code or git
before it entered this plan or the CHANGELOG): CHANGELOG lane and its verifier, release-metadata lane
and its verifier, kernel lane and its verifier, kit lane and its verifier (workflow `wf_707c6893-2be`,
S366). Refutations the verifiers raised and this plan honours: the VETO-floor defect is wider than three
ids; the sign-min mold refuses kernel paths; the Tier-1 gate measures three gutted entry points, not one;
`_audit_log_parts/` is part of the kernel gap; the 3.14 cure was not yet proven by CI (it is now: scheduled
Validate run 41597704176); the pin floor was
lowered by a separate unsigned commit; the validator does not bind a declared Codex version to its hash.

## Goal

npm `latest` becomes 1.4.4, cut through rc.1 → 24 h hold → GA with signed tags and passing release
gates, and the signed material (CHANGELOG `[1.4.4]` and the tag text) states plainly what PRs #6 and #7
changed in governance, the two fixes this cut ships (secret redactor offsets; kernel list), and what
stays open, with no release promised for the cure except the redactor fix's declared condition (R11),
scheduled for the next release.

## Approach

1. **Base and scope.** The release-metadata derivation keeps `BASE_TAG=v1.4.2` (`b55084da`), as every
   earlier GA did; `v1.4.3-rc.1` becomes a checked ancestor, not the base. This plan's first commit
   cites PLAN-197 and PLAN-198 in its subject, so both enter the derived scope honestly; the rule
   "plan ids from subjects" does not change.
2. **CHANGELOG first, free.** `CHANGELOG.md` is oracle 0. `[1.4.4]` lands now, dated, with the preamble
   label `v1.4.4`, because the release-metadata derivator treats it as a precondition and never writes
   it. `[1.4.3]` stays byte-identical (the signed rc.1 tag points at it). If any later ceremony makes a
   CHANGELOG sentence false (a residual is cured, an ADR is added so counts move, or the PR-merged files
   are ratified by bytes), the CHANGELOG changes in the SAME patch as that ceremony. The two Caminho 1+
   fix commits come BEFORE the notes, so the notes describe them as shipped.
3. **Release metadata (relmeta-144).** Clone, never reuse, the 1.4.3 derivator into
   `.claude/plans/PLAN-198/relmeta/`. Its sha is pinned in a signed sentinel, its CLI has no version
   parameter, and three of its eight claim anchors already fail on HEAD (the condition-67 writer moved to
   `_lib/_audit_log_parts/rotation_storage.py`, `external_wait` moved to `_lib/_ceo_boot_parts/`, the pin
   range lost its upper bound). The tag text is shared by the rc and the GA tag, so it must not claim an
   npm publication.
4. **Kit.** A new, hand-written kit parameterized by `--tag`, under `.claude/plans/PLAN-198/kit/`, with
   evidence in `PLAN-198/repass-rc1/` and `PLAN-198/repass-ga/`. The October kit cannot be patched: it is
   pinned to `v1.4.3-rc.1`, to an exact Codex 0.160.0 and to a validator function PR #7 removed.
5. **Cut.** rc.1 → adopters may test with `upgrade.sh --pin v1.4.4-rc.1` → hold ≥ 24 h → GA → npm.
6. **Caminho 1+ (proposed to the Owner on 2026-11-03; OQ-1).** Two reviewed fixes ship in this cut as the
   Owner's own signed commits on `7fad2972`, before any free commit of this plan: the secret redactor
   (offsets of the NFKC view cut into the original text, present since v1.0.0; Codex/Grok egress) and
   the kernel list restore (R1) together with the Coverage job timeout 35 → 50. The redactor fix
   carries one declared condition (R11). The other governance findings from PR #7 stay declared
   residuals (below), each with a follow-up target and no release assigned, unless the Owner folds a
   cure into this cut (OQ-2, OQ-3).

Alternatives rejected: re-cutting `v1.4.3` (the rc.1 tag and its signed tree no longer match `main`);
`v1.4.3-rc.2` (the tag would carry a version whose `[1.4.3]` entry describes another tree).

## Sequence (Caminho 1+)

1. **Owner: the two fix commits** on `7fad2972`, signed, in this order: the secret redactor, then the
   kernel list with the Coverage timeout. Local only; the Owner's script does not push.
2. **CEO: the free commits on top** — CHANGELOG `[1.4.4]` and this plan (W0), the kit (W3), then the W1
   record (Owner decisions, OQ-7 included; `draft → reviewed`) and `PLAN-198/CONDITIONS-rc1.md`. Every
   subject cites only plans in the release scope.
3. **relmeta-144 materials (W2) as the LAST land** before the SIGN: derive, rail, rail record. The plan
   moves `reviewed → executing` with the first W2 commit. The freeze starts at the derivation.
4. **Owner: SIGN → land → push** (the push carries steps 1-3 if none of them was pushed before; an earlier
   push is allowed, a commit between the materials and the SIGN is not) **→ CI green** on the landed
   commit, including one scheduled Validate run (the Python 3.14 leg) before the bump.
5. **Owner: bump rc.1** (`release.sh bump --rc 1`) → push → CI green.
6. **rc.1 re-pass, two lanes** (Codex and Claude on the same redacted payloads) → fields → Owner signature
   → verdict envelope commit (Owner) → push → CI green.
7. **Owner: tag `v1.4.4-rc.1`** (signed; `precut` first) → push the tag → `release.yml` green.
8. **Hold ≥ 24 h with `main` frozen** (ADR-103; kit README rule 2). `CONDITIONS-ga.md` may land between the
   rc tag push and the start of the GA re-pass, and the GA verdict commit after the GA re-pass; nothing else.
9. **GA**: re-pass on the same tree → verdict → Owner: tag `v1.4.4` → push the tag.
10. **Owner: approve the `production-npm` environment** (npm `latest` = 1.4.4) → **publish the draft
    GitHub Release** that `release.yml` created.

## Paths × oracle

Oracle: `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>` (prints `path<TAB>0|1`).

| path | oracle | kernel | who writes |
|---|---|---|---|
| `.claude/plans/PLAN-198-release-v1-4-4.md`, `.claude/plans/PLAN-198/**` | 0 | no | CEO (free land) |
| `CHANGELOG.md` | 0 | no | CEO (free land) |
| `.claude/scripts/local/release.sh` | 0, but member of the ADR-192 gate-scripts manifest | no | relmeta-144 ceremony |
| `.claude/governance/gate-scripts-manifest.txt` | 1 | — | relmeta-144 ceremony |
| `.claude/governance/pair-rail-verdict-v1.4.4-rc.1.md`, `-v1.4.4.md` | 1 | — | Owner's shell (kit generator), committed by the Owner |
| `.claude/hooks/_lib/secret_patterns.py`, `.claude/hooks/_lib/pii_patterns.py` | 1 | yes | Owner's redactor fix commit (Caminho 1+, signed, from the Owner's shell) |
| `.claude/hooks/check_arbitration_kernel.py`, `.github/workflows/coverage.yml` | 1 | yes | Owner's kernel fix commit (Caminho 1+, signed, from the Owner's shell) |
| `.claude/hooks/tests/test_secret_patterns.py`, `test_pii_patterns.py`, `test_codex_egress_redact.py`, `test_kernel_decomposition_coverage.py` | 0 | no | the same two commits |
| `.claude/governance/pair-rail-inputs-hash-manifest.txt` | 1 | yes | not in this cut (R3 follow-up) |
| `.github/workflows/mcp-smoke.yml` | 1 | no | not in this cut (R2 follow-up) |

## Items

### W-fix — The two fix commits of Caminho 1+ (Owner, signed, below every free commit of this plan)
Check: git log --format=%s 7fad2972..HEAD | grep -qF 'fix(security): the secret redactor cuts the original text' && git log --format=%s 7fad2972..HEAD | grep -qF 'fix(kernel): restore hard-deny coverage'
(In the Owner's shell, `git verify-commit` on both commits as well; CI has no key to check `%G?`.)
- [x] Secret redactor: `scan()` offsets index the original text (two frames, NFKC spans mapped back,
  merged spans; `pii_patterns` applies overlaps as a union); tests in `test_secret_patterns.py`,
  `test_pii_patterns.py`, `test_codex_egress_redact.py`. Codex APPROVE-WITH-CONDITION; the condition is
  R11.
- [x] Kernel list: one recursive row per helper package that holds the code the split moved out of the
  seven kernel facades; one row for `plan_paths.py`, the plan-path predicate the train put in place of
  the plan-path regexes of the kernel files `check_plan_edit.py` and `policy_preprocessors.py`; one row
  for each of four modules that kernel code calls — `model_currency.py` (the VETO-floor predicate kernel
  files now call as part of their VETO-floor check), and `cli_currency.py` (the Codex payload-pin
  currency arm), `bash_indirect_guard.py` (the indirect-execution matcher) and
  `bash_indirect_telemetry.py` (its disabled-rail telemetry), which the train added; and one recursive
  row for the live-adapter package `adapters/live/`, now enrolled, so an edit to it goes through the
  kernel override: rows 110 → 123, tracked kernel files 125 → 222. Guard
  `test_kernel_decomposition_coverage.py`: each helper package below `_lib/` that a kernel source
  reaches by an import statement or by a `/` chain of string literals is kernel in full (positive
  control on the known packages), and each of these five flat modules is kernel and still imported by
  a kernel source; dropping any one of the 13 new rows turns it red.
  `coverage.yml` timeout 35 → 50. Cures R1.
- [x] The free notes, this plan and the kit land only on top of these two commits: CHANGELOG `[1.4.4]`
  describes both fixes as shipped.

### W0 — Evidence plan and CHANGELOG `[1.4.4]` (this commit, free paths)
Check: python3 .claude/hooks/check_canonical_edit.py --is-canonical CHANGELOG.md .claude/plans/PLAN-198-release-v1-4-4.md | awk -F'\t' 'NF!=2 || $2!="0" {bad=1} END {exit (bad || NR!=2)}' && bash .claude/scripts/local/verify-counts.sh --quiet && bash .claude/scripts/validate-governance.sh --fast
(The oracle answers on STDOUT, one `path<TAB>0|1` line per path, and exits 0 either way; the `awk` step fails unless both lines read `0`.)
- [x] Plan file created under PLAN-SCHEMA (status `draft`; this plan cites only verified facts).
- [x] `## [1.4.4] - 2026-11-03` added on top, covering the whole train since v1.4.2; says v1.4.3 never
  reached npm; keeps "The requirements do not change from v1.4.2"; preamble label `v1.4.4` with the live
  counts; no `[Unreleased]`; no framework version above 1.4.4; Known-open re-declares the v1.4.0 annex
  in its own item with no release assigned; the external versions it cites are only Claude Code
  `2.1.280` and npm `11.20.0` (input for the clone's `EXTERNAL_VERSIONS`).
- [x] Commit subject cites PLAN-197 and PLAN-198, so the subject-based scope sees both.
  Check: git log --format=%s v1.4.2..HEAD | grep -E 'PLAN-197.*PLAN-198'

### W1 — Owner decisions before any ceremony material
Check: none (doc-only) — each answer is recorded verbatim under "Owner decisions" before W2 starts
- [ ] OQ-1: the Owner's answer on Caminho 1+ recorded in the Owner's words (the Owner's two signed fix commits are its
  mechanical trace, not its record).
- [ ] OQ-2: Codex instrument for the re-passes (re-pin 0.166.0 by the pin pack, or accept the
  version-floor route PR #7 introduced, with the observed payload sha recorded as the instrument id).
- [ ] OQ-3: ratify by bytes the 233 PR-merged canonical paths in a signed sentinel, or keep them declared.
- [ ] OQ-4 to OQ-6 answered (below).
- [ ] OQ-7: this plan is L3 and has no debate record. Either `/debate start PLAN-198 "<proposal>"` reaches
  `design-coherent` (PROTOCOL V0) before any W2 material, or the Owner records under "Owner decisions" a
  ruling that this release cut follows the PLAN-194 precedent without a new debate. No such ruling is
  recorded as of 2026-11-03; this is an open item for the Owner, not a decision.
  Check: test -n "$(find .claude/plans/PLAN-198/debate -name approved.md 2>/dev/null)" || grep -qE '^- OQ-7 \(answered ' .claude/plans/PLAN-198-release-v1-4-4.md
- [ ] OQ-8: the kit limits declared in the kit README accepted, or another kit round asked for.
- [ ] Once the Owner has read the plan and the answers above are recorded, the plan moves `draft → reviewed`
  with `reviewed_at` (PLAN-SCHEMA §4: the human gate, before any W2 material; `check_plan_edit.py` refuses
  `reviewed` without `reviewed_at`). W0 landed under `draft` because it only created this plan and the
  CHANGELOG entry it describes.
  Check: grep -qE '^reviewed_at: [0-9]{4}-[0-9]{2}-[0-9]{2}' .claude/plans/PLAN-198-release-v1-4-4.md && ! grep -qE '^status: draft$' .claude/plans/PLAN-198-release-v1-4-4.md

### W2 — Release metadata ceremony (relmeta-144)
Check: python3 .claude/plans/PLAN-198/relmeta/apply-relmeta144-edits.py --claims-only (script created in this wave; green before derivation)
- [ ] With the first W2 commit, the plan moves `reviewed → executing` (PLAN-SCHEMA §4: the first commit that
  depends on the plan after the Owner gate).
  Check: grep -qE '^status: (executing|done)$' .claude/plans/PLAN-198-release-v1-4-4.md
- [ ] Clone `.claude/plans/PLAN-194/relmeta/` into `.claude/plans/PLAN-198/relmeta/`: split `PREV_BASE`
  into the driver's previous target (`1.4.3`) and the range base (`1.4.2`); `TARGET_BASE="1.4.4"`;
  keep `RC_NUM="1"`; re-anchor the three CLAIMS that fail on HEAD to the code that holds them now;
  read the inherited claims from `[1.4.3]` and the new ones from `[1.4.4]`; `EXTERNAL_VERSIONS` from
  the real `[1.4.4]` text; a static check that no removed constant is still referenced.
- [ ] `RELEASE_TITLE` and `RELEASE_HEADLINE` rewritten for `v1.4.2..HEAD`: ASCII, every version with a
  `v` prefix, no line that starts with `#` (git's default tag cleanup would strip it), no npm-publication
  claim, the PR-merge sentence re-measured and stated by its form.
- [ ] Derived scope covers `git log v1.4.2..HEAD` and includes PLAN-197 and PLAN-198.
  Check: git log --format=%s v1.4.2..HEAD | grep -oE 'PLAN-[0-9]{3}' | sort -u
- [ ] Re-pin `test_release_bump_sites.py` (new scope positive, 1.4.3 scope negative) and the
  `release.sh` line of the gate-scripts manifest.
- [ ] Rail: Codex plus two Claude refuters in the same round, the derivator as a third lane; stop rule
  fixed before round 3; rail record committed.
- [ ] Owner: SIGN (GPG) → land → push; CI green on the landed commit.
  Check: gh run list --commit "$(git rev-parse HEAD)" --json workflowName,conclusion

### W3 — Release kit (hand-written, parameterized by `--tag`)
Check: bash .claude/plans/PLAN-198/kit/test-kit.sh (harness created in this wave)
- [x] One kit for both tags: the scripts take `--tag`, and no release version is written in their code.
- [x] The generator admits a Codex instrument only through `check_instrument()`: a stable `X.Y.Z` at or
  above the ADR-182 floor `CODEX_VERSION_FLOOR`, enforced even when the payload sha is the manifest's (the
  validator alone would accept such a version), a well-formed sha256, and a target triple the manifest
  lists. Status `verified` needs the manifest's version and payload sha; status `compatible` needs a
  version above the manifest's and a payload sha different from the manifest's. No manifest says which
  payload a `compatible` version has, so that route binds no version to a payload sha: the run header
  (`PROVENANCE`) records the observed version, target triple, payload sha and pin status, the signed
  fields carry them, and the GA refuses a Codex identity that differs from the rc's unless the generator
  is given `--instrument-change-declared`, which puts an `instrument-changed-since-<rc>` finding in the
  signed fields. Negative control: a version below 0.160.0 carrying the manifest sha is refused by the
  generator.
- [x] A Claude lane reviews the same payloads as the Codex lane: part of the range was authored by Codex,
  and Codex alone would be author and reviewer. The Claude lane runs without `--bare` (no API key).
- [x] Kit committed before the bump, so it is part of the candidate tree; the runner refuses files that
  differ from the candidate's tree.

### W4 — rc.1
Check: git tag -v v1.4.4-rc.1 && gh run list --workflow release.yml --limit 1
- [ ] `main` stays frozen from the W2 derivation until the GA tag push (kit README rule 2): only the
  relmeta-144 ceremony's own commits, the bump commit, each tag's verdict commit, and `CONDITIONS-ga.md`
  between the rc tag push and the start of the GA re-pass.
- [ ] Owner: `release.sh bump --rc 1` (VERSION and the bump sites move to 1.4.4).
- [ ] rc.1 re-pass (Codex + Claude lanes); verdict envelope generated in the Owner's shell and committed by
  the Owner (canonical path).
- [ ] Owner: signed tag `v1.4.4-rc.1`, push; `release.yml` green; adopters may test with
  `upgrade.sh --pin v1.4.4-rc.1`.

### W5 — Hold, GA and npm
Check: git tag -v v1.4.4 && npm view ceo-orchestration dist-tags
- [ ] Hold ≥ 24 h after the newest `v1.4.4-rc.*` tag (`release.yml` RC-to-GA hold gate, ADR-103).
- [ ] GA re-pass on the same tree; GA verdict envelope (Owner's shell, Owner's commit).
- [ ] Owner: signed tag `v1.4.4`; approve the `production-npm` environment; un-draft the GitHub Release.
- [ ] npm `latest` = 1.4.4.

### W6 — Closeout
Check: python3 .claude/scripts/check-staleness.py --json
- [ ] Plan moves `executing → done` (the earlier transitions happen in W1 and W2), with `completed_at` and
  a non-empty `related_commits` (inline list); `check_plan_edit.py` refuses `done` without both.
- [ ] Each declared residual below has its follow-up file or its answer recorded.
- [ ] Session memory updated; adopters told (upgrade path from 1.4.2).

## Declared residuals (governance findings from PR #7)

R1 is cured in this cut by Caminho 1+ and lives under "Fixed" in CHANGELOG `[1.4.4]`. Every other row is
declared in CHANGELOG `[1.4.4]` Known-open: R2-R10 with "No release is assigned to its cure yet", R11 with
its cure scheduled for the next release (Owner default). "Follow-up
target" names where the cure is tracked; a `PLAN-198-FOLLOWUP-*` file is opened at closeout (W6) unless
the Owner folds the cure into this cut, in which case the CHANGELOG item is rewritten in the same patch.
From the kernel fix commit on, an edit to any of the 97 files it makes kernel (the 81 package files, the
five flat modules and `adapters/live/`) goes through the kernel override, like an edit to any kernel file.

| id | residual (by its form) | follow-up target |
|---|---|---|
| R1 | CURED (Caminho 1+, the Owner's kernel fix commit): the kernel hard-deny list now covers the seven helper packages that hold the code the split moved out of the kernel facades; `plan_paths.py`, the predicate the train put in place of the plan-path regexes of two kernel files; four modules that kernel code calls, `model_currency.py` (the VETO-floor predicate kernel files now call as part of their VETO-floor check) and `cli_currency.py`, `bash_indirect_guard.py` and `bash_indirect_telemetry.py` (added by the train); and the live-adapter package `adapters/live/`, so an edit to it goes through the kernel override. Guard `test_kernel_decomposition_coverage.py` checks that each helper package below `_lib/` that a kernel source reaches by an import statement or by a `/` chain of string literals is kernel in full, and that each of these five flat modules is kernel and still imported by a kernel source. | none (CHANGELOG `[1.4.4]` Fixed) |
| R2 | Tier-1 coverage gate and `mcp-smoke.yml` path filters name only entry points. | `PLAN-198-FOLLOWUP-decomposition-residuals` (aggregate mode in `parse-coverage.py`, then `coverage.yml`; filter line in `mcp-smoke.yml`) |
| R3 | Pair-rail inputs-hash manifest lists entry points only (and not the Codex pin manifest). | same follow-up as R2; must land before any verdict whose inputs hash it would change |
| R4 | VETO floor moved from a closed list of four Owner-signed ids to family patterns that admit retired and retiring ids. | `PLAN-198-FOLLOWUP-veto-floor-retired-ids` (exclude ledger-retired ids or return to an explicit list; kernel files) |
| R5 | Codex pin moved from exact payload hash to a version floor without a hash match (the payload sha is computed and recorded; a mismatch passes when the nearby @openai/codex package declares a stable version newer than the manifest version and at or above the floor); pin file `>=0.128.0` vs ADR-182 amendment `>=0.160.0`; validator does not bind version to hash; `--harness codex` prints "verified 0.160.0" over 0.139.0 fixtures. | OQ-2; else `PLAN-198-FOLLOWUP-codex-pin-floor` (kernel files: `_lib/cli_currency.py`, `_lib/_pair_rail_parts/`) |
| R6 | 233 canonical paths (15 kernel by the list as merged, 101 by the restored list) merged through PRs without a sentinel; `main` unprotected, so nothing prevents a repeat. | OQ-3; branch protection is an Owner setting outside the repository |
| R7 | Audit spool: exit-drain change partial (ADR-055-AMEND-4 `PARTIAL`), stress run incomplete. | existing owner: `PLAN-194-FOLLOWUP-v1-4-4-backlog` items 2, 18, 19 |
| R8 | Bash guard (ADR-201): replay acceptance, private vocabulary row and OS-sandbox measurements not run on the implementation. | existing owner: ADR-201 acceptance evidence; PLAN-195 records it |
| R9 | Backups leave out `audit-key` and `.salt`; restore without `.sha256` only warns; restore without `--dest` overwrites live logs while chain state stays. | `PLAN-198-FOLLOWUP-backup-key-material` |
| R10 | Model allowlist moved from exact membership to family patterns that also admit Sonnet/Haiku 4-9, Gemini 2-9, Grok 3-9 and ledger-retired ids; the settings-tamper detector (`settings_tamper_model_remap`), the agent `model:` check and the tier-policy loader no longer flag them. | same follow-up as R4 (both predicates live in `_lib/model_currency.py`) |
| R11 | The ingress path redacts the raw answer text before parsing it, so a redaction can change whether an answer parses. Declared condition of Codex's APPROVE-WITH-CONDITION on the redactor fix; it predates that fix. Its structural cure is scheduled for the next release (Owner default). | `PLAN-198-FOLLOWUP-redact-after-parse`, scheduled for the next release (redact the decoded values after parsing, the structural cure the fix commit names) |

Observations outside this plan's file assignment (not edited here): the SPEC row for
`learning_rail_disabled` still calls ADR-201 `PROPOSED`; the `agent_frontmatter.py` docstring still
describes the closed VETO list; the operating contract's Codex line ("pinned by SHA, not by range") no
longer describes `main`; PLAN-197's table places three script packages under `.claude/scripts/` while they
live under `.claude/hooks/_lib/`; two root-level files merged by the PRs (`RELATORIO-M15-22.md`,
`codex-planos/`) carry a machine-specific absolute path and should go through the contamination review.

## Open questions

- **OQ-1 (Owner): Caminho 1+.** The CEO first offered two paths on 2026-11-03: ship 1.4.4 with R1-R3
  declared ("Caminho 1"), or cure first. Then the redactor offset defect was found and both fixes were
  reviewed (redactor: Codex and two Claude refuters, over several rounds; kernel list: the same
  lanes). Caminho 1+ ships both in 1.4.4 as the Owner's own signed commits on `7fad2972`, applied
  from the Owner's shell, before every free commit of this plan; no ceremony mold is involved, because sign-min
  refuses kernel paths at P0 and the kernel mold used for the audit-race fix refuses new files. This
  plan, CHANGELOG `[1.4.4]` and the kit are written for Caminho 1+ and land only on top of those two
  commits. A kernel scope change is L3+ and needs a debate record unless the Owner rules otherwise; under
  Caminho 1+ the fix commits land before W1, so the OQ-7 answer has to cover them too. The Owner's answer
  goes under "Owner decisions".
- **OQ-2 (Owner): Codex instrument.** The installed Codex CLI is 0.166.0; the manifest pins 0.160.0.
  Under PR #7's rule 0.166.0 passes as `compatible/version_floor_only`; under the operating contract a
  re-pin comes before any cut. Which one governs the re-passes of this release?
- **OQ-3 (Owner): ratification.** Ratify the PR-merged canonical files by bytes in a signed sentinel (the
  1.4.3 train did this for earlier PR merges), or keep them declared only?
- **OQ-4 (Owner): version class.** GuardFall on by default, the family-based VETO floor and the floor-only
  Codex pin are trust-boundary changes, and `VERSIONING.md` lists a new trust boundary under MINOR. The
  Owner chose 1.4.4; should the CHANGELOG or `VERSIONING.md` state why PATCH holds?
- **OQ-5 (Owner): tag text language.** The 1.4.3 headline was accent-free Portuguese; the CHANGELOG is
  English. Either is valid if ASCII; every headline paragraph needs a matching phrase in `[1.4.4]`.
- **OQ-6 (Owner): branch protection.** Turn on protection or a ruleset for `main` before the freeze, so
  that the freeze is enforced by GitHub and not only by convention?
- **OQ-7 (Owner): debate for this L3 plan.** PROTOCOL makes a debate mandatory for L3+ before execution
  (V0: `design-coherent`), and this plan has none on disk; the precedent release plan PLAN-194 ran three
  rounds. Run `/debate start PLAN-198 "<proposal>"` before W2, or rule that this cut, which follows the
  PLAN-194 release mold, skips it? No Owner ruling on this is recorded yet.
- **OQ-8 (Owner): kit limits.** The round-5 review of the kit found limits in what its redaction covers
  (the payloads redact each path with what the redactor detects in that path's two versions; the
  reviewers' copy, each file with what it detects in that file) and in its custody of an interrupted
  attempt (the kit checks the process that launched each lane, and the outcomes of the lanes dispatched
  for the same commit). The kit README declares them under "Limites declarados" and "Se algo der
  errado", with an operator procedure for any kill, instead of another kit round; what the kit sends is
  already public once the operator confirms that `origin` is this public GitHub repository (the
  runner starts only when the `main` of `origin` is the candidate). Accept these
  declared limits (default: accept), or ask for another kit round?

## Owner decisions

None is recorded in this file as of 2026-11-03. The version number 1.4.4 was chosen by the Owner in S366
(session memory, not a repository fact). Each answer goes here as one line in the form
`- OQ-<n> (answered <YYYY-MM-DD>): <the Owner's words>`.

## Risks

- A land on `main` after the relmeta derivation that cites a new plan or touches a new ADR makes the signed
  scope false; `make mac-cut-*` has no scope guard, so the kit must carry it.
- The tag text is shared by rc and GA; a publication claim would be false if the GA never ships, as
  happened to 1.4.3.
- Any ceremony that adds an ADR or a `_lib` module moves the counts; the CHANGELOG preamble must move in the
  same patch, or `verify-counts.sh` and the derivator refuse.
- The Python 3.14 cure in `7fad2972` passed the scheduled Validate run on that commit (41597704176); the
  preflight still refuses a HEAD whose runs are not green, so the landed commit needs its own scheduled
  Validate run before the bump (Sequence step 4).
- Caminho 1+ moved R1 from Known-open to Fixed in CHANGELOG `[1.4.4]`; R2 and R3 stay true after the
  kernel fix commit (re-checked on the composed tree). If the two fix commits do not land, these notes must not
  land either: the CHANGELOG would claim fixes `main` does not have.
- The two fix commits change kernel paths through the Owner's signed commits, with no sentinel file; the
  CHANGELOG says so in each Fixed item.

## How to continue

"Read `.claude/plans/PLAN-198-release-v1-4-4.md` and CHANGELOG `[1.4.4]`. Check `git log --oneline -6`
(the two Caminho 1+ fix commits sit below the notes and the kit; W-fix Check),
`gh run list --limit 10`, `npm view ceo-orchestration dist-tags`, `codex --version`. The kit (W3) is
already committed. If the Owner decisions (W1, OQ-7 on the debate included) are not recorded, ask them
first, with defaults; run the debate unless the Owner waives it; move the plan to `reviewed`. Then, in the
order of the Sequence: the W1 record and `PLAN-198/CONDITIONS-rc1.md`, and LAST the relmeta-144 materials
(W2: clone the derivator; the plan moves to `executing` with its first commit). Nothing lands between those
materials and the Owner's SIGN; nothing canonical is edited by Claude's tools."

## Success criteria

- [ ] `v1.4.4-rc.1` and `v1.4.4` tags signed and verified — Check: git tag -v v1.4.4-rc.1 && git tag -v v1.4.4
- [ ] `release.yml` green on both tags, including the CHANGELOG, verdict and hold gates — Check: gh run list --workflow release.yml --limit 2
- [ ] npm `latest` = 1.4.4 — Check: npm view ceo-orchestration dist-tags
- [ ] Every residual R1-R11 is either cured in a signed patch (with the CHANGELOG rewritten in that patch)
  or declared in the signed material with no release assigned (R11: its cure scheduled for the next release). The
  check reads only the "Known-open (declared by this release)" subsection of `[1.4.4]`, ignores line
  wrapping, and passes only when every item ends with the phrase or, as the R11 item does, with "is
  scheduled for the next release."; it prints the item count, 10 with R1 cured by Caminho 1+ (R2-R11) — Check: python3 -c "import re,sys; t=open('CHANGELOG.md').read(); s=t[t.index('## [1.4.4]'):t.index('## [1.4.3]')]; k=s[s.index('### Known-open (declared'):]; k=k[:k.index('### ', 4)]; items=[' '.join(i.split()) for i in re.split(r'(?m)^- ', k)[1:]]; bad=[i[:50] for i in items if not i.endswith(('No release is assigned to its cure yet.', 'is scheduled for the next release.'))]; print(len(items), bad); sys.exit(0 if items and not bad else 1)"

## Session history

- S366 (2026-11-02/03): PR #7 merged (`888e9e6c`); two red nightly runs cured in `7fad2972` and pushed
  with the Owner's approval; the release-metadata, CHANGELOG, kernel and kit lanes mapped the cut, each
  with an adversarial verifier; this plan and CHANGELOG `[1.4.4]` written from those maps after re-checking
  every claim against code and git.
- S366 (2026-11-03, later): the kit harness found the redactor offset defect; it and the kernel-list gap
  got reviewed fixes. Caminho 1+ was put to the Owner: both fixes ship in 1.4.4 as the Owner's signed commits on
  `7fad2972`, and the CHANGELOG entry, this plan and the kit were rewritten for that path (R1 cured,
  R11 added). In review, the kernel fix grew to cover three more flat modules and the live-adapter
  package (125 → 222 tracked kernel files), and the kit came to redact the original text before its
  display escape.

## Reference links

- `.claude/plans/PLAN-194-maintenance-train-v1-4-3.md` (the 1.4.3 train), `.claude/plans/PLAN-194/relmeta/`
  (the derivator to clone), `.claude/plans/PLAN-194/sign-min/` (the free-path signing mold).
- `.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md` (status `draft`; only items 28-30 ticked).
- `.claude/plans/PLAN-195-bash-guard-indirect-execution.md`, `.claude/adr/ADR-201-bash-guard-indirect-execution.md`.
- `.claude/plans/PLAN-197-full-monolith-decomposition.md`, `.claude/adr/ADR-202-kernel-and-hooks-modularization.md`.
- `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` (amendment "Onda 6B"),
  `.claude/adr/ADR-055-AMEND-4-spool-state-drain-and-signal-hardening.md`.
- `.github/workflows/release.yml` (CHANGELOG gate, RC-to-GA hold), `.github/workflows/npm-publish.yml`.
