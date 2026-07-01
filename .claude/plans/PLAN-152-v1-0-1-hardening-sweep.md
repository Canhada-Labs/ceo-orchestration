---
id: PLAN-152
title: v1.0.1 Hardening Sweep — Audit Fan-out Remediation + Backlog Closeout
status: draft
created: 2026-07-01
owner: CEO
depends_on: []
budget_tokens: 400-700k
budget_sessions: 1
context_risk: high
external_wait: none
tags: [v1.0.1, security, governance, ci, docs, npm, substrate]
---

# PLAN-152 — v1.0.1 Hardening Sweep

## Context

The public `ceo-orchestration@1.0.0` (commit `9777a8d`, doc-fix `489f020`) shipped
2026-07-01. A dogfood **audit fan-out** the same day (run `wf_071ef6c5`, 8 read-only
finder agents + adversarial REDUCE refuter, ADR-141 8-field shards) returned verdict
**FINDINGS**: **41 confirmed** (32 fix / 6 accept / 3 defer — table is ground truth;
the synthesizer's prose "30/7/4" was a miscount), 2 refuted, 0
unverifiable. Two P0s were **re-proven first-hand via execution** (not just refuter
evidence): the pair-rail PreToolUse gate is **fail-open since v1.0.0**, and the
bash-safety destructive-command guard **fail-opens** on a quoted metachar.

Full findings memory: `project_s254_audit_fanout_findings.md`. This plan folds those
41 findings **plus** the pre-existing v1.0.1 backlog (npm tarball, Sonnet 5, workflow
null-guards, GPG sentinels) into one release. Owner directive: contemplate
**absolutely everything, including minors and cosmetics**, to close in a single
next-terminal Fable run.

## Goal

Ship `ceo-orchestration@1.0.1` with every confirmed audit finding resolved
(fixed, or explicitly accepted/deferred with an on-disk pointer), the npm tarball
cleaned, the model tier modernized, and CI green — leaving zero silently-dropped
findings.

## Approach / Thesis

- **Wave-ordered by blast radius**: security fail-opens first (they are live in the
  shipped release and are the framework's core value prop), then the test safety net,
  then economics/robustness, then packaging, then docs/dead-code hygiene, then model
  modernization, then closeout.
- **Ceremony boundary is explicit per wave.** Edits to kernel/canonical-guarded paths
  (`.claude/settings.json`, `.claude/hooks/**`, `.github/workflows/npm-publish.yml`,
  `scripts/install*.sh`, the `MODEL_ID` enum, `SPEC/**`) require the GPG canonical-edit
  ceremony (sentinel with real anchor-sha + Scope; dual signer rails per ADR-121;
  re-sign if `approved.md` is rewritten). Non-guarded edits (docs, templates, tests)
  land directly.
- **Fable execution model**: give the full spec up front, run at `high`/`xhigh`,
  delegate fan-outable waves (B docs-batch, E) to async sub-agents, self-verify each
  wave against its `Check:` line before advancing.
- **Every finding is accounted for**: `fix` → a wave item; `accept` → a one-line
  documented acceptance with pointer (§Accepted); `defer` → §Deferred with a successor
  target. Nothing is dropped.

## Do NOT re-flag (refuted at REDUCE — saved false-positives)

- **tests-06** — `test_crash_injection_sigterm_mid_write` 50ms-sleep flake is moot:
  the test is `@pytest.mark.xfail(strict=True, run=False)` and never executes.
- **dead-code-05** — `scripts/local/trading-readonly-escape-hatch.sh` is NOT an orphan
  duplicate: `SPEC/v1/audit-log.schema.md:332` + `test_trading_readonly.py:542`
  (PLAN-136 W4 F3) guard the two-copy byte-identity as intentional install-source.

---

## Waves

### Wave 0 — Owner prerequisites (unblocks canonical edits)
Check: none (Owner-only; not a CEO execution unit)

- [ ] [P0] [.claude/plans/PLAN-140..142/architect/**/approved.md] Owner GPG-signs the 3 pending sentinels (backlog #1 / governance-06) — OR confirms they are residue of already-merged plans and closes Task #1. Independent of PLAN-152's own scope.
- [ ] [P0] [.claude/plans/PLAN-152/] Owner GPG-signs a fresh PLAN-152 canonical-edit sentinel (anchor-sha + Scope covering the kernel/canonical paths touched by Waves A/C/D/F) before those waves execute.

### Wave A — P0 security fail-opens (SHIPPED-BROKEN in v1.0.0)
Check: python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q AND manual exec probes below pass (pair-rail no longer fail-opens; `rm -rf ~ ";"` blocks)

- [ ] [P0] [.claude/settings.json] **governance-01** — fix the `check_pair_rail.py` PreToolUse registration (line ~201): pass the **basename** `check_pair_rail.py` to `_python-hook.sh`, matching the other 40+ registrations, so `$HOOKS_DIR/$1` resolves. CANONICAL/KERNEL → ceremony. Check: `echo '{"tool_name":"Edit","tool_input":{"file_path":"x"}}' | bash .claude/hooks/_python-hook.sh check_pair_rail.py` no longer prints `hook not found` + `{}`.
- [ ] [P0] [.claude/hooks/check_bash_safety.py] **error-handling-01** — make the destructive-command guard **fail-CLOSED** (or re-scan raw text) when `_tokenize()` hits `shlex.ValueError`, matching sibling `_e3`. CANONICAL → ceremony. Check: live probe `rm -rf ~ ";"` → block (currently allow).
- [ ] [P1] [.claude/hooks/_python-hook.sh] **security-01** — harden the interpreter-cache fast path (:120-173): verify ownership + reject symlinks (or move cache under a 0700-verified dir) before read+exec of the cached path. CANONICAL → ceremony. Check: added unit asserts a symlinked/foreign-owned cache path is rejected.
- [ ] [P1] [.claude/hooks/tests/test_template_dogfood_parity.py] **governance-02** — widen `_HOOK_RE` (:35) to parse relative-path AND raw-`python3` hook registrations, so the template≥dogfood parity assertion stops being vacuous for `check_pair_rail.py` + `check_codex_filewrite.py`. Check: test now fails if either registration is dropped from settings.json.
- [ ] [P1] [templates/settings/settings.base.json] **governance-03** — register `check_pair_rail.py` + `check_codex_filewrite.py` in the template settings (or add to `DOGFOOD_ONLY_HOOKS` with rationale); adopters currently get the codex `.mcp.json` (install.sh:1383) but no pair-rail/filewrite gate. Check: `git grep -l check_pair_rail templates/settings/` non-empty OR DOGFOOD_ONLY_HOOKS lists it with a comment.

### Wave B — CI-dark tests + coverage-truth
Check: .github/workflows/ runs the newly-wired roots (grep the workflow) AND check-test-env-hygiene.py over all roots exits 0 (211 violations burned down)

- [ ] [P0] [pytest.ini] **tests-02** — add root `tests/` to `testpaths`; the 112 root tests include SECURITY tests (`test_codex_redact_fail_closed.py`, `test_mcp_bearer_nonce_replay.py`, `test_output_scan_llm03.py`) never collected. Check: `pytest --collect-only` count rises by 112.
- [ ] [P0] [.github/workflows/validate.yml] **tests-01** — wire the 8 CI-dark roots (~1377 tests: `_lib/tests`, `swarm/tests`, `test_federation`, `mcp-server/tests`, `detectors`, `predict-budget`, `forensic`, `synthetic`) into a CI job. Check: workflow grep shows all 8 roots collected in CI.
- [ ] [P1] [.claude/scripts/check-test-env-hygiene.py] **tests-03** — extend `_DEFAULT_SCAN_ROOTS` (currently 6 entries: `hooks/tests`, `scripts/tests`, `tier_policy_cli/tests`, `tournament/tests`, `predict-budget/tests`, `tests`) with the test roots present in tests-01's CI-dark set but ABSENT from the tuple — at minimum `.claude/hooks/_lib/tests`, `.claude/scripts/swarm/tests`, `.claude/scripts/mcp-server/tests`, plus the federation/detectors/forensic/synthetic roots (enumerate exactly against the live tuple, do not assume). Then burn down the 211 env-hygiene violations (128 `_lib/tests`, 43 `swarm`, …) using `TestEnvContext`. Check: `check-test-env-hygiene.py --paths <every root>` exits 0.
- [ ] [P2] [.github/workflows/coverage.yml] **tests-04** — reconcile the stale "78%" header/comment (:194-196, :220) with the real enforcing `--fail-under=67` (:188). Check: `grep -n 78 coverage.yml` returns only historical/comment context, not an enforcing-floor claim.
- [ ] [P2] [.claude/adr/ADR-042-mcp-server-contract.md] **tests-05** — fix the dead `mcp-coverage.yml` citation (:629) — either ship the workflow (folds into tests-01's mcp-server root) or correct the ADR to name `mcp-smoke.yml`. Check: cited workflow filename exists OR ADR text matches reality.

### Wave C — hot-path economics + workflow robustness
Check: python3 -m pytest .claude/hooks/tests/ -q AND the 3 canonical workflows null-guard (grep for the guard) AND a synthetic degraded-finder run does not crash

- [ ] [P1] [.claude/hooks/check_output_secrets.py] **economics-01** — remove the deprecated aggregate sidecar emit (PLAN-106 window elapsed); it doubles HMAC appends + filelocks on the all-tools PostToolUse path (~2x per hit). CANONICAL → ceremony. Check: after a scan hit, only per-pattern `output_scan_finding` events emit (no aggregate twin).
- [ ] [P1] [.claude/hooks/check_read_injection.py] **economics-02** — eliminate/cap the 2nd uncapped full-file `read_text` + unconditional unicode sanitize (:320); gate the heavy path on `CEO_UNICODE_HARDBLOCK` before doing the work. CANONICAL → ceremony. Check: a large-file Read triggers a single capped scan (assert via added test or timing).
- [ ] [P1] [.claude/hooks/check_anti_ceo_overhead.py] **economics-03** — session-scope (or exempt sanctioned read-only fan-outs from) the 5-min project-wide window (:175/:221) so parallel finders stop pooling one budget and blocking sanctioned audit greps. CANONICAL → ceremony. Check: two concurrent sessions do not share the P4 counter (added test).
- [ ] [P1] [.claude/workflows/audit-fanout.js] [.claude/workflows/nightly-hygiene.js] [.claude/workflows/eval-baseline-n20.js] **error-handling-03 / backlog #4** — null-guard the reducer derefs (agent() resolves NULL on terminal API error; `.catch()` misses it — crashed real run `wf_071ef6c5`). Port the validated 3-point fix (finder `.then(r=>r||{…})`, `refuteResults.filter(Boolean)` + `rr.verdicts||[]`, `synth||{DEGRADED}`). CANONICAL (workflows) → ceremony. Check: a forced-null finder degrades to a report instead of TypeError.
- [ ] [P2] [.claude/hooks/_lib/pii_patterns.py] **error-handling-02** — make `Match.snippet` actually redacted (or correct the ":114 redacted/preview-safe" docstring) so a future consumer trusting the contract cannot write cleartext secrets. Latent, not an active leak (emit path re-redacts today). CANONICAL → ceremony. Check: `_snippet()` output is masked OR docstring no longer claims preview-safe.
- [ ] [P3] [docs/performance-budgets.md] **economics-04** — update the assumed Edit hook-chain (:15/:37) to the real 10 PreToolUse + 3 PostToolUse count, and file/land the deferred aggregate per-tool-call latency-gate ADR (or record the deferral). Check: doc count matches `settings.json` Edit-matched hooks.

### Wave D — npm tarball hygiene (backlog #2)
Check: cd npm && npm pack --dry-run --json shows ZERO eval/tests/fixtures/red-team/PLAN-* paths AND a new CI packlist gate fails on any forbidden pattern

- [ ] [P1] [.github/workflows/npm-publish.yml] [scripts/install-npm.sh] **tarball-01** — replace the blanket `cp -r .claude npm/` with selective staging (rsync excludes: `**/tests/`, `**/fixtures/`, `scripts/red-team-corpus/`, `.claude/eval/`, `.claude/plans/PLAN-*` — KEEP `plans/{README,*-SCHEMA}.md` + `examples/`; keep `policies/`). Root cause: `package.json` `files:["\.claude/"]` whitelist makes the existing `npm/.npmignore` impotent. Mirror in BOTH kernel-guarded stagers. CANONICAL/KERNEL → ceremony. Check: `npm pack --dry-run` packlist has 0 forbidden paths; install.sh consumes none of the excluded (verified: eval 0 refs, red-team 0 refs).
- [ ] [P2] [.github/workflows/npm-publish.yml] **tarball-02** — add a CI packlist gate step: run `npm pack --dry-run --json` and FAIL if any path matches `(tests|fixtures|eval|red-team|PLAN-[0-9])`. Closes the recurrence vector. Check: gate fails on a seeded forbidden path.
- [ ] [P3] [.claude/skills/frontend/NOTICE.md] **license-cosmetic** — add an SPDX `MIT` header so Socket.dev License score (80, from the 47% frontend NOTICE match) rises. Cosmetic. Check: Socket re-scan or local SPDX-lint shows full MIT match.
- [ ] [P2] [.github/workflows/npm-publish.yml] **backlog-oidc** — migrate CI to npm Trusted Publishing (OIDC): drop `secrets.NPM_TOKEN`, add trusted-publisher config on npmjs.org (removes the expiring secret entirely). KERNEL → ceremony. Check: workflow authenticates via OIDC, no `NPM_TOKEN` reference remains. NOTE: if not done, **NPM_TOKEN expires ~2026-09-28** (90-day granular token, env scope `production-npm`) → next release fails until regenerated. If deferring OIDC, at minimum calendar-flag the expiry.

### Wave E — docs-drift + dead-code + orphan PLAN-128 (minors/cosmetics)
Check: git grep of each cited dead path/count returns the corrected value AND validate-governance.sh passes (orphan PLAN-128 resolved)

- [ ] [P2] [docs/GUIA-COMPLETO.md] [docs/GUIA-COMPLETO.pt-BR.md] **docs-01/02/03** — fix stale counts: tests 1529→(live collect-only), "6 hooks on Pre/PostToolUse"→31 registrations, audit-query "9 subcommands"→29. Check: each number matches its live source command.
- [ ] [P2] [INSTALL.md] [docs/CTO-GUIDE.md] [RELEASE.md] [docs/QUICKSTART.md] [SBOM.md] **docs-04..08** — fix dead refs: INSTALL SPEC filenames (`audit-log.schema.md`/`plan.schema.md`); CTO-GUIDE PLAN-018/019 pointers; RELEASE `CLAUDE.md §CHANGELOG` + `docs/coverage-baseline.md` (also coverage.yml:5); QUICKSTART gemini path (`adapters/live/gemini.py`); SBOM PLAN-112 citation. Check: every cited path exists (or the citation is removed).
- [ ] [P2] [SBOM.md] **dependencies-01** — correct bash requirement `≥4`→`≥3.2` per install.sh's documented/enforced floor. Check: SBOM:210 matches install.sh:121-141.
- [ ] [P2] [.claude/plans/PLAN-128/] [.claude/scripts/validate-governance.sh] **governance-05 / dead-code-03** — resolve orphan `PLAN-128/` (restore the plan file OR rehome `AB-PROTOCOL.md`/`measure-state.sh`, updating `docs/ACCELERATORS.md` + installer refs), and tighten `validate-governance.sh:467-476` to enforce the matching-plan-file rule. Check: `validate-governance.sh` FAILs on an orphan PLAN-NNN dir (added), passes on the repo.
- [ ] [P3] [tools/check-version-drift.py] [scripts/install-accelerators.sh] [scripts/local/] [benchmarks/hook-latency-p50-p99-post-batch-F.jsonl] [docs/OWNER-CEREMONY-CONTRACT.md] **dead-code-01/02/04/06/08** — wire-or-remove check-version-drift (false docstring); fix install-accelerators:165 dead `EMIT-WIRING-DESIGN.md` pointer + stale note; create `scripts/local/historical/` (ADR-098:232) and move the 7 shipped ceremony scripts; delete/annotate the null-valued benchmark jsonl (fix its dead `replay.py` path); fix OWNER-CEREMONY-CONTRACT:167 `generate-ceremony.sh` path. Check: each cited dead path resolves or the reference is deleted.
- [ ] [P3] [.github/ISSUE_TEMPLATE/] **backlog-issue-template** — add the missing GitHub issue template (only community-health file absent per GitHub's checklist; raises community-health 85%→100%). Check: `.github/ISSUE_TEMPLATE/` exists with at least one template; GitHub community profile shows the item satisfied.

### Wave F — model/substrate modernization (backlog #3)
Check: python3 .claude/scripts/check-model-deprecations.py has fast-mode entries AND tier_policy tests pass with the new MODEL_ID member

- [ ] [P2] [.claude/scripts/substrate-watch.json] [.claude/scripts/tests/test_check_substrate_watch.py] **substrate-refresh** — commit the already-done + pair-rail-APPROVED ledger refresh (Claude Code 2.1.198, SDK-TS 0.3.198, SDK-Py 0.2.110, source URL → raw GitHub, source_stale=false) + its companion test update. Check: `check-substrate-watch.py` reports `current`; suite 14/14.
- [ ] [P2] [.claude/scripts/model-deprecations.json] **fastmode-deprecation** — add fast-mode class entries: Opus 4.6 fast removed 2026-06-29 (silent standard-speed fallback), Opus 4.7 fast → error 2026-07-24. Check: `check-model-deprecations.py` surfaces the fast-mode class.
- [ ] [P2] [.claude/hooks/_lib/tier_policy/_types.py] [.claude/adr/ADR-NNN-sonnet-5-tier.md] **sonnet5-tier** — author an ADR (cost/capability envelope: intro $2/$10 → $10 std, -33% vs 4.6, tokenizer +30% → re-baseline predict-budget/calibrations) and do the KERNEL edit to the closed `MODEL_ID` enum (add Sonnet 5; the `OPUS47 = "claude-opus-4-8"` label at :94 is stale — reconcile). CANONICAL/KERNEL → ceremony. Check: tier_policy loader + type tests pass; predict-budget calibration re-baselined.
- [ ] [P3] [.claude/scripts/red-team-corpus/] **nested-subagent-redteam** — add red-team cases for Claude Code 2.1.19x nested-subagents (5 levels) + background-agent auto-push against the spawn/canonical guards; OR defer to a follow-on plan if scope balloons. Check: added corpus cases OR §Deferred entry with successor target.

### Wave G — closeout
Check: full CI gate set green locally (validate-governance --fast, shellcheck -S warning, env-hygiene, check-contamination, perf p95/p99, check-claude-md-claims) AND VERSION bumped AND CHANGELOG updated

- [ ] [P0] [CLAUDE.md] [SBOM.md] — re-run `check-claude-md-claims.py` after all ADR/skill/hook count changes (tolerance=0 ENFORCING gate); reconcile any drift. Check: `check-claude-md-claims.py` exits 0.
- [ ] [P0] [VERSION] [CHANGELOG.md] — bump `1.0.0`→`1.0.1`; write the CHANGELOG entry enumerating the fixed findings. Check: VERSION reads 1.0.1; CHANGELOG has the entry.
- [ ] [P0] [pre-push] — run the EXACT CI gates (not just touched-file pytest): full hooks+scripts suites, shellcheck `-S warning`, env-hygiene, contamination, perf p95/p99; force exec bit where needed. Check: every CI job's local equivalent is green.

---

## Accepted (documented, no code change — do not re-flag)

- **security-02** (3200) — `check_config_protection.py` basename-match / no `.resolve()`
  is a documented Owner-pre-resolved design choice (self-footgun gate, not an adversary
  boundary); pointer `check_config_protection.py:19,246`.
- **tests-08** (9000) — `check_agent_spawn.py` excluded from the 86% per-module coverage
  gate is on record with named uplift owner (`coverage.yml:157-170`).
- **economics-05** (9000) — Gate-1/2 boot-read bytes (~153KB) tracked by ADR-152 M1
  (PROPOSED); decomposition is a separate scoped effort, not v1.0.1.
- **dead-code-07** (9000) — `.claude/gpg-revocations.jsonl` zero-consumer is a
  self-documented deferred Wave-3 item (`docs/SP-NNN-OWNER-WORKFLOW.md:226-229`).
- **dependencies-02** (9000) — all non-stdlib imports are documented opt-in/dev/sidecar
  deps (SBOM §A/§B/§2); `check-stdlib-only.py` passes. No action.
- **governance-06** (9000) — the 3 unsigned sentinels are Wave 0 / Task #1 (Owner).

## Deferred (the 3 confirmed `defer` findings — successor target required)

- **governance-04** (7500) — 14 post-ADR-116-AMEND-1 hooks absent from
  `_KERNEL_PATHS` (incl. blocking-capable `check_adversary`, `check_config_protection`).
  Kernel expansion needs its own ADR + ceremony; too large for v1.0.1. → follow-on plan.
- **governance-07** (6000) — `NotebookEdit` not covered by canonical-edit/arbitration
  matchers nor `permissions.deny`; exploitability bounded to `.ipynb`-parseable guarded
  targets. → fold into the governance-04 kernel-matcher plan.
- **tests-07** (5000) — `TestPerformance` wall-clock budgets run under `-n auto`
  (perf-microbench-under-load flake class). → add a `serial`/advisory marker in a CI
  hardening pass (low risk; may pull into Wave B if cheap).

> NOTE — `nested-subagent-redteam` (Wave F P3) is NOT one of the 41 confirmed findings;
> it is net-new red-team scope from the substrate sweep. It may itself be deferred to a
> follow-on plan if the corpus scope balloons — that is a Wave F execution decision, not
> a double-count against the audit's 3 defers.

## Open questions

1. **Scope of Wave F sonnet5-tier**: reconcile the stale `OPUS47 = "claude-opus-4-8"`
   enum label only, or do the full M-tier route change to Sonnet 5? (The label is stale
   regardless; the *routing* change is the cost decision.) Owner call at debate.
2. **Wave A ceremony batching**: one PLAN-152 sentinel covering all kernel paths in
   A/C/D/F, or per-wave sentinels? (One broad scope is fewer round-trips; per-wave is
   tighter blast radius.)
3. **v1.0.1 vs split**: land everything as v1.0.1, or ship Waves A+B as v1.0.1 (security
   hotfix) and C–F as v1.0.2? Owner call.

## How to continue

Next terminal (Fable, `effort: high`/`xhigh`):

> Read PLAN-152. Confirm the Wave 0 Owner prerequisites are done (3 sentinels signed
> or closed; a PLAN-152 canonical-edit sentinel signed covering the kernel/canonical
> paths in Waves A/C/D/F). Then run `/debate start PLAN-152 "v1.0.1 hardening sweep:
> resolve 41 audit findings + backlog across 7 waves"` (L3 gate). After consensus,
> execute wave-by-wave in order A→G; each wave self-verifies against its `Check:` line
> before advancing. Kernel/canonical edits go through the GPG ceremony + Codex pair-rail
> (note: the pair-rail PreToolUse gate itself is fixed in Wave A — until then, invoke
> the rail manually via `codex exec review --uncommitted`). Commit the
> already-approved substrate-watch diff early (Wave F substrate-refresh). Close with
> Wave G: VERSION→1.0.1, CHANGELOG, full CI gate set green, `check-claude-md-claims`
> tolerance=0.

## Success criteria

- [ ] All 32 `fix` findings resolved OR explicitly re-classified with Owner sign-off.
- [ ] All 6 `accept` + 3 `defer` findings have an on-disk pointer (§Accepted / §Deferred) — zero silently dropped.
- [ ] Backlog closed: npm tarball (#2), OIDC/NPM_TOKEN (backlog-oidc), issue template (backlog-issue-template), Sonnet 5 (#3), workflow null-guards (#4), sentinels (#1 / Wave 0).
- [ ] Wave A: pair-rail gate executes (no fail-open); `rm -rf ~ ";"` blocks; cache path hardened.
- [ ] Wave B: the 3 security root-tests collect + pass in CI; env-hygiene 211→0.
- [ ] Wave D: `npm pack --dry-run` ships zero eval/tests/fixtures/PLAN-* paths; packlist gate live.
- [ ] `check-claude-md-claims.py` (tolerance=0) + `validate-governance.sh` + full CI green.
- [ ] VERSION=1.0.1, CHANGELOG entry, tag ceremony ready.
- [ ] `check-contamination` green (no foxbit/employer-class residue introduced).

## Reference links

- Audit findings: `project_s254_audit_fanout_findings.md` (memory); run `wf_071ef6c5`.
- Backlog: `project_v101_backlog.md` (memory) — tarball (#2), Trusted-Publishing OIDC,
  NPM_TOKEN expiry ~2026-09-28, issue template.
- Launch record: `project_s253_plan151_launch_built.md`.
- Substrate refresh (this session, pair-rail APPROVED, uncommitted): `substrate-watch.json`.
