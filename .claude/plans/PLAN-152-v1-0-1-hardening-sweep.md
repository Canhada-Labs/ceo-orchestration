---
id: PLAN-152
title: v1.0.1 Hardening Sweep — Audit Fan-out Remediation + Backlog Closeout
status: reviewed
reviewed_at: 2026-07-01
created: 2026-07-01
owner: CEO
depends_on: []
budget_tokens: 400-700k
budget_sessions: 2  # 1 execution session + 1 tiny fresh-session pair-rail probe (Wave G — Codex R5-P3)
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

**Lifecycle note (S255):** `draft → reviewed` executed by the CEO under the Owner's
explicit same-day delegation ("Termina o plano, deixa ele pronto para ser executado,
revisa, debate […] não pare até concluir"). Review = S255 claim-verification
(62 claims, `wf_9a1dd57e`) + L3 debate round-1 (4× ADJUST_PROCEED → PROCEED,
design-coherent) + Codex pair-rail on the revision diff. The 3 §Resolved questions
still require Owner ratification at Wave 0 (K10).

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
  (`.claude/settings.json`, `.claude/hooks/**` — incl. `_lib/tests/**`,
  `.github/workflows/*.yml` (ALL of them — debate C8, `check_canonical_edit.py:182`),
  `scripts/install*.sh`, the `MODEL_ID` enum, `SPEC/**`) require the GPG canonical-edit
  ceremony (sentinel with real anchor-sha + Scope; dual signer rails per ADR-121;
  re-sign if `approved.md` is rewritten). Non-guarded edits (docs, `.claude/scripts/**`
  test roots, `.claude/workflows/*.js` — debate C3) land directly.
- **Fable execution model**: give the full spec up front, run at `high`/`xhigh`,
  delegate fan-outable waves (B docs-batch, E) to async sub-agents, self-verify each
  wave against its `Check:` line before advancing.
- **Every finding is accounted for**: `fix` → a wave item; `accept` → a one-line
  documented acceptance with pointer (§Accepted); `defer` → §Deferred with a successor
  target. Nothing is dropped.
- **The auto pair-rail is DEAD for this ENTIRE run** (debate C5): hooks load at session
  start, so fixing settings.json:201 in Wave A does NOT revive the gate mid-session.
  Manual `codex exec review --uncommitted` is a HARD, RECORDED gate (APPROVE artifact
  per commit — `37867c2` precedent) for **EVERY guarded/canonical commit, i.e. Waves
  A/B/C/D/F** (B included since validate.yml + coverage.yml entered the guarded scope —
  Codex pair-rail R2-P1b). Wave G verifies the restored registration in a FRESH session.
  Note Wave A is circular (the rail cannot review its own repair) — the manual gate is
  the only cross-model check there.
- **A-before-B is safe** (debate, Critic-D): Wave A's blast radius is covered by the
  already-CI-wired `.claude/hooks/tests/`, not by the CI-dark roots Wave B wires.
- **Rollback**: each ceremony wave lands as ONE commit → revert path = `git revert
  <wave-commit>`; the Wave A fail-closed flip additionally ships behind a default-on
  env kill-switch (see error-handling-01) for no-redeploy disable.

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

- [x] [P0] [OQ ratification] Present the 3 resolved questions (§Resolved questions) to the Owner via AskUserQuestion (K10 doctrine — structured multiple-choice, debate synthesis marked "(Recomendado)"); log the picked option verbatim into that section. *(DONE 2026-07-02 — all three explicitly answered "(Recomendado)"; verbatim record in §Resolved questions.)*
- [x] [P0] [.claude/plans/PLAN-140..142/architect/**/approved.md] Owner GPG-signs the 3 pending sentinels (backlog #1 / governance-06) — OR confirms they are residue of already-merged plans and closes Task #1. Independent of PLAN-152's own scope. *(DONE 2026-07-02 — all 3 SIGNED with key `AE9B…DC74`; the stale pre-de-id signer fingerprint (`D7227DFE…`) in their prose was corrected to `AE9B…DC74` BEFORE signing — the rails only register the AE9B hot-key.)*
- [x] *(DONE 2026-07-02 — signed at anchor `c88daf9`, 14-file Scope, ADR-157 pinned; `.asc` verified against both rails.)* [P0] [.claude/plans/PLAN-152/] Owner GPG-signs the PLAN-152 canonical-edit sentinel (anchor-sha + Scope) per the OQ2 resolution: ONE sentinel whose Scope is an **enumerated explicit-file allowlist** (no globs) covering the guarded paths of Waves A/B/C/D/F (incl. `validate.yml` + `coverage.yml` — debate C8) and **excluding** `.claude/workflows/*.js` (not guarded — debate C3). **Allocate the Wave F ADR number NOW** (next free NNN in `.claude/adr/`) and pin the exact `ADR-<NNN>-sonnet-5-tier.md` path in Scope — the canonical-edit hook exact-matches Scope entries, so a placeholder `ADR-NNN-…` authorizes nothing (Codex R5-P2). `touched−scope=∅` is re-checked mechanically at EVERY wave boundary before commit. (Zero-cost variant at Owner discretion: split a second, tighter Wave-A-only sentinel in the same sitting — minority position, Critic-C.)
- [ ] [P0] [kernel-override authorization — Codex pair-rail R2-P1] Several target paths are in `check_arbitration_kernel.py::_KERNEL_PATHS` (`.claude/settings.json`, `_python-hook.sh`, `check_bash_safety.py`, `.github/workflows/*.yml`, `tier_policy/_types.py`), and that hook is HARD-DENY with **no sentinel escape** (:31-36: "Absent BOTH env vars, the edit is blocked regardless of any sentinel"). **Launch procedure** (Codex pair-rail R3-P2: hooks read the Claude Code PROCESS env — a Bash-tool `export` mid-session never reaches hook invocations): the Owner launches the executing session with the vars in the launch environment, e.g. `CEO_KERNEL_OVERRIDE="PLAN-152-v1-0-1-hardening" CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT" claude`. Scope is therefore the WHOLE session — compensating controls: signed sentinel + `touched−scope=∅` per wave + `kernel_override_used` audit emit on every use (ADR-031 frozen invariant) + manual pair-rail APPROVE per guarded commit. Optional tightening: after the last kernel wave (F), relaunch WITHOUT the vars for E/G-style non-kernel edits. Without this launch env, the run stops at the first Wave A edit even with the sentinel signed.

### Wave A — P0 security fail-opens (SHIPPED-BROKEN in v1.0.0)
Check: python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q AND manual exec probes below pass (pair-rail no longer fail-opens; `rm -rf ~ ";"` blocks)

- [ ] [P0] [.claude/settings.json] **governance-01** — fix the `check_pair_rail.py` PreToolUse registration (line 201, the ONLY non-basename arg among 44 shim registrations): pass the **basename** `check_pair_rail.py` to `_python-hook.sh` and invoke the shim via `"$CLAUDE_PROJECT_DIR"`, matching the other 43, so `$HOOKS_DIR/$1` resolves. (`check_codex_filewrite.py` does NOT share the defect — :211 registers it via raw absolute-path `python3`.) CANONICAL/KERNEL → ceremony. Check (two-sided — the probe argument CHANGES with the fix, per Codex pair-rail P1): (pre-fix baseline) the OLD registered form `… | bash .claude/hooks/_python-hook.sh .claude/hooks/check_pair_rail.py` prints `hook not found` + `{}`; (post-fix) the NEW registered form `echo '{"tool_name":"Edit","tool_input":{"file_path":"x"}}' | bash .claude/hooks/_python-hook.sh check_pair_rail.py` EXECUTES the hook (real JSON verdict, no `hook not found`); AND `grep -n check_pair_rail .claude/settings.json` shows the basename arg with `"$CLAUDE_PROJECT_DIR"` shim invocation. Wave G's fresh-session probe runs the AS-REGISTERED (post-fix) command, never the old relative-path string.
- [ ] [P0] [.claude/hooks/check_bash_safety.py] **error-handling-01** — close the destructive-command guard's `shlex.ValueError` bypass via the **raw-text rescan branch** (debate C4 — NOT a blanket fail-closed: `_tokenize` :274-284 and `_e3` :904 use different tokenizers, so blanket-block would newly brick commands `_e3` accepts, e.g. benign unbalanced quotes): on ValueError, regex-scan the RAW subcommand for the destructive signatures and block only on a hit. Ship behind a default-on env kill-switch (e.g. `CEO_BASH_RAWSCAN=0` reverts) and fix the `_tokenize` docstring (:277-280) that falsely claims "fail-safe, not fail-open". CANONICAL → ceremony. Check (positive AND negative): hook-input probe `rm -rf ~ ";"` → block (currently allow) AND benign unparseable `echo it's fine` → allow.
- [ ] [P1] [.claude/hooks/_python-hook.sh] **security-01** — harden the interpreter-cache fast path (:120-173): verify ownership + reject symlinks (or move cache under a 0700-verified dir) before read+exec of the cached path. CANONICAL → ceremony. Check (positive AND negative, debate C4): added unit asserts a symlinked/foreign-owned cache path is rejected AND a legitimate owner-created cache path is still accepted (no over-block).
- [ ] [P1] [.claude/hooks/tests/test_template_dogfood_parity.py] **governance-02** — widen `_HOOK_RE` (:35) to parse relative-path AND raw-`python3` hook registrations, so the template≥dogfood parity assertion stops being vacuous for `check_pair_rail.py` + `check_codex_filewrite.py`. Check: test now fails if either registration is dropped from settings.json.
- [ ] [P1] [templates/settings/settings.base.json] **governance-03** — register `check_pair_rail.py` + `check_codex_filewrite.py` in the template settings (or add to `DOGFOOD_ONLY_HOOKS` with rationale); adopters currently get the codex `.mcp.json` (install.sh:1383) but no pair-rail/filewrite gate. Check: `git grep -l check_pair_rail templates/settings/` non-empty OR DOGFOOD_ONLY_HOOKS lists it with a comment.

### Wave B — CI-dark tests + coverage-truth
Check: the NEW CI job collects the expected count AND is green over ≥2 consecutive runs (quarantine lane for any flaking root — a quarantined root may NOT block the release tag) AND check-test-env-hygiene.py over the v1.0.1 roots exits 0 (55 NEW violations burned down; `_lib/tests` 128 → v1.0.2)
> Ceremony note (debate C8/Critic-D MF-1): `.github/workflows/*.yml` IS canonical-guarded (`check_canonical_edit.py:182`) — the validate.yml + coverage.yml edits below enter the PLAN-152 sentinel Scope. The `.claude/scripts/**` test roots are NOT guarded (land direct).

- [ ] [P0] [tests/unit/] [pytest.ini] **tests-02** — relocate the 13 root `tests/*.py` (112 tests incl. the 3 SECURITY files `test_codex_redact_fail_closed.py`, `test_mcp_bearer_nonce_replay.py`, `test_output_scan_llm03.py`) into a new `tests/unit/` and add THAT path to `testpaths` (debate C1: bare `tests/` would double-collect the 7 existing `tests/<subdir>` entries at pytest.ini:45-53 and break `make test-collect`). **The move changes `__file__` depth** (Codex pair-rail R2-P2): update every `REPO_ROOT` derivation in the moved files (`parent.parent` / `parents[1]` → one level deeper — confirmed sites: test_codex_redact_fail_closed.py:27, test_output_scan_llm03.py:19, test_mcp_bearer_nonce_replay.py:43; sweep all 13). **AND rekey the path-keyed gates** (Codex pair-rail R3-P1): `test-env-hygiene-allowlist.yaml` root-level entries `tests/test_*.py` → `tests/unit/test_*.py` (confirmed: :1026 atlas_technique, :1029 check_atlas_fpr, :1032 codex_redact_fail_closed, :1035 credential_rotation — sweep the whole file) and `check_contamination.py:178` (`tests/test_output_scan_llm03.py`). Check: `pytest --collect-only -q tests/unit` = 112 AND `python3 -m pytest tests/unit -q` GREEN (collect-only is not proof after a path-depth move); `make test-collect` total rises by exactly 112 with zero duplicate-nodeid errors; `check-test-env-hygiene.py` reports zero NEW violations from the move; `check-contamination` green.
- [ ] [P0] [.github/workflows/validate.yml] **tests-01** — wire `tests/unit` + the 8 CI-dark roots (~1377 tests: `_lib/tests`, `swarm/tests`, `test_federation`, `mcp-server/tests`, `detectors`, `predict-budget`, `forensic`, `synthetic`) into CI as EXPLICIT paths (no bare pytest/testpaths job — debate C1), replicating the existing two-pass `not serial`/`serial` split (validate.yml:298 pattern) and co-locating `replay/tests` after `swarm/tests` to reproduce the S228 ordering. Pre-wiring audit: grep the new roots for wall-clock/perf tests and mark them `serial` FIRST (debate C2). GUARDED (validate.yml) → sentinel Scope. Check: see wave Check line (outcome, not presence).
- [ ] [P0] [pytest.ini or affected test files] **tests-07 (pulled in from §Deferred — debate C2)** — add the `serial` marker to `TestPerformance` (test_output_scan.py:570) + `TestPerformanceBudget` (test_codex_egress_redact.py:313) wall-clock classes; `-m "not serial"` at validate.yml:298 already filters them into the serial lane. Check: the classes carry the marker; serial pass stays green.
- [ ] [P1] [.claude/scripts/check-test-env-hygiene.py] **tests-03** — extend `_DEFAULT_SCAN_ROOTS` (currently 6 entries) with the CLEANED v1.0.1 roots only: `.claude/scripts/swarm/tests`, `.claude/scripts/mcp-server/tests`, `.claude/scripts/detectors/tests` — and burn down their 55 NEW violations (43 swarm + 12 mcp-server; detectors clean) using `TestEnvContext`. **`.claude/hooks/_lib/tests` (128 violations) moves to v1.0.2** (debate C8: those files are canonical-guarded, the burndown is the single biggest session-scope item; add the root to the tuple only WITH its burndown). The federation/forensic/synthetic roots are already covered by the recursive `tests` entry; predict-budget/tests is already in the tuple; ~70 occurrences there are already allowlisted. Check: `check-test-env-hygiene.py --paths <v1.0.1 roots>` exits 0.
- [ ] [P2] [.github/workflows/coverage.yml] **tests-04** — reconcile the THREE stale "78%" enforcing-floor claims (:194-195 comment, :220 step-summary header, :238 step-summary footer "_calibrated to 78% post-hardening_") with the real enforcing `--fail-under=67` (:188); the :54/:200 hits are historical comments and may stay. Check: `grep -n 78 coverage.yml` returns only historical/comment context, not an enforcing-floor claim.
- [ ] [P2] [.claude/adr/ADR-042-mcp-server-contract.md] **tests-05** — fix the dead `mcp-coverage.yml` citation (:629) — either ship the workflow (folds into tests-01's mcp-server root) or correct the ADR to name `mcp-smoke.yml`. Check: cited workflow filename exists OR ADR text matches reality.

### Wave C — hot-path economics + workflow robustness
Check: python3 -m pytest .claude/hooks/tests/ -q AND the 3 canonical workflows null-guard (grep for the guard) AND a synthetic degraded-finder run does not crash

- [ ] [P1] [.claude/hooks/check_output_secrets.py] **economics-01** — remove the deprecated aggregate sidecar emit (PLAN-106 window elapsed); it doubles HMAC appends + filelocks on the all-tools PostToolUse path (~2x per hit). CANONICAL → ceremony. Check: after a scan hit, only per-pattern `output_scan_finding` events emit (no aggregate twin).
- [ ] [P1] [.claude/hooks/check_read_injection.py] **economics-02** — eliminate/cap the 2nd uncapped full-file `read_text` + unconditional unicode sanitize (:320); gate the heavy path on `CEO_UNICODE_HARDBLOCK` before doing the work. CANONICAL → ceremony. Check: a large-file Read triggers a single capped scan (assert via added test or timing).
- [ ] [P1] [.claude/hooks/check_anti_ceo_overhead.py] **economics-03** — session-scope (or exempt sanctioned read-only fan-outs from) the 5-min project-wide window (:175/:221) so parallel finders stop pooling one budget and blocking sanctioned audit greps. CANONICAL → ceremony. Check: two concurrent sessions do not share the P4 counter (added test).
- [ ] [P1] [.claude/workflows/audit-fanout.js] [.claude/workflows/nightly-hygiene.js] [.claude/workflows/eval-baseline-n20.js] **error-handling-03 / backlog #4** — null-guard the reducer derefs (agent() resolves NULL on terminal API error; `.catch()` misses it — crashed real run `wf_071ef6c5`). Port the validated 3-point fix (finder `.then(r=>r||{…})`, `refuteResults.filter(Boolean)` + `rr.verdicts||[]`, `synth||{DEGRADED}`). **NOT canonical-guarded — lands DIRECT** (debate C3: `.claude/workflows/*.js` is absent from `_CANONICAL_GUARDS`, check_canonical_edit.py:113-240; do NOT list these paths in the sentinel Scope; whether workflows SHOULD be guarded pairs with the deferred governance-04 kernel-matcher plan). Check: a forced-null finder degrades to a report instead of TypeError.
- [ ] [P2] [.claude/hooks/_lib/pii_patterns.py] **error-handling-02** — make `Match.snippet` actually redacted (or correct the ":114 redacted/preview-safe" docstring) so a future consumer trusting the contract cannot write cleartext secrets. Latent, not an active leak (emit path re-redacts today). CANONICAL → ceremony. Check: `_snippet()` output is masked OR docstring no longer claims preview-safe.
- [ ] [P3] [docs/performance-budgets.md] **economics-04** — update the assumed Edit hook-chain (:15/:37) to the real 10 PreToolUse + 3 PostToolUse count, and file/land the deferred aggregate per-tool-call latency-gate ADR (or record the deferral). Check: doc count matches `settings.json` Edit-matched hooks.

### Wave D — npm tarball hygiene (backlog #2)
Check: run the staging loop first (mirror of npm-publish.yml Stage-bundle step, into a scratch copy of npm/ — an unstaged npm/ passes vacuously), THEN cd <scratch-npm> && npm pack --dry-run --json shows ZERO paths matching `(tests|fixtures|eval|red-team|PLAN-[0-9])` (numeric-plan glob — `PLAN-SCHEMA.md`/`README.md`/`examples/` MUST remain packaged) AND a new CI packlist gate fails on any forbidden pattern

- [ ] [P1] [.github/workflows/npm-publish.yml] [scripts/install-npm.sh] **tarball-01** — replace the blanket `cp -r .claude npm/` with selective staging (rsync excludes: `**/tests/`, `**/fixtures/`, `.claude/scripts/red-team-corpus/`, `.claude/eval/`, `.claude/plans/PLAN-[0-9]*` (numeric-plan glob ONLY — must NOT match `PLAN-SCHEMA.md`, which the npm installer installs via `install_one`; a bare `PLAN-*` would drop it and the packlist gate would still pass — Codex R7-P2) — KEEP `plans/{README,*-SCHEMA}.md` + `examples/`; keep `policies/`). Root cause: `package.json` `files:["\.claude/"]` whitelist makes the existing `npm/.npmignore` impotent. Mirror in BOTH stagers IF install-npm.sh actually stages the tree — VERIFY first (debate/Critic-D Nice-1: the only confirmed blanket copy is npm-publish.yml:98-100; if install-npm.sh does not stage, the "second mirror" edit is a phantom — drop it). Also fix the FALSE "OIDC trusted publisher" header comment at npm-publish.yml:3 while the file is open (debate C6: `id-token:write` + `--provenance` is Sigstore provenance, not Trusted-Publishing auth). CANONICAL/KERNEL → ceremony. Check: `npm pack --dry-run` packlist has 0 forbidden paths; install.sh consumes none of the excluded (verified: eval 0 refs, red-team 0 refs).
- [ ] [P2] [.github/workflows/validate.yml] [.github/workflows/npm-publish.yml] **tarball-02** — add the packlist gate to **validate.yml (PR/push)**: stage `.claude` into a scratch npm/ copy (mirror of the Stage-bundle step), run `npm pack --dry-run --json`, FAIL on `(tests|fixtures|eval|red-team|PLAN-[0-9])` (debate/Critic-B M2: a tag-only gate cannot prevent the regression it is named for — npm-publish.yml triggers only on tag push :23-26). Keep a copy in npm-publish.yml as the last-line release assert. GUARDED (both workflows) → sentinel Scope. Check: PR-side gate fails on a seeded forbidden path.
- [ ] [P3] [.claude/skills/frontend/NOTICE.md] **license-cosmetic** — add an SPDX `MIT` header so Socket.dev License score (80, from the 47% frontend NOTICE match) rises. Cosmetic. Check: Socket re-scan or local SPDX-lint shows full MIT match.
- [x] ~~**backlog-oidc**~~ — **DEFERRED to v1.0.2 by debate consensus C6** (2 critics: auth-mode migration inside the security-hotfix release risks holding Wave A hostage; the npmjs.org trusted-publisher config is Owner/web-console work unverifiable by CI; token is NOT blocking — expires ~2026-09-28). v1.0.1 actions only: (a) the npm-publish.yml:3 false-comment fix rides tarball-01; (b) **calendar-flag the NPM_TOKEN expiry ~2026-09-28 NOW** (90-day granular token, env scope `production-npm` — next release after expiry fails until regenerated). See §Deferred.

### Wave E — docs-drift + dead-code + orphan PLAN-128 (minors/cosmetics)
Check: git grep of each cited dead path/count returns the corrected value AND validate-governance.sh passes (orphan PLAN-128 resolved)

- [ ] [P2] [docs/GUIA-COMPLETO.md] [docs/GUIA-COMPLETO.pt-BR.md] **docs-01/02/03** — fix stale counts: tests 1529→(live collect-only), "6 hooks on Pre/PostToolUse"→31 registrations, audit-query "9 subcommands"→29. Check: each number matches its live source command.
- [ ] [P2] [INSTALL.md] [docs/CTO-GUIDE.md] [RELEASE.md] [docs/QUICKSTART.md] [SBOM.md] **docs-04..08** — fix dead refs: INSTALL.md THREE dead SPEC cites (:321 `audit-log.md`→`audit-log.schema.md`; :323 `plan-frontmatter.md`→`plan.schema.md`; :326 `governance.md` — no SPEC counterpart, repoint to `hook-io.schema.md` or drop the bullet); CTO-GUIDE PLAN-018/019 pointers; RELEASE `CLAUDE.md §CHANGELOG` + `docs/coverage-baseline.md` (also coverage.yml:5); QUICKSTART gemini path (`adapters/live/gemini.py`); SBOM PLAN-112 citation. Check: every cited path exists (or the citation is removed).
- [ ] [P2] [SBOM.md] **dependencies-01** — correct bash requirement `≥4`→`≥3.2` per install.sh's documented/enforced floor. Check: SBOM:210 matches install.sh:121-141.
- [ ] [P2] [.claude/plans/PLAN-128/] [.claude/scripts/validate-governance.sh] **governance-05 / dead-code-03** — resolve orphan `PLAN-128/` (restore the plan file OR rehome `AB-PROTOCOL.md`/`measure-state.sh`, updating `docs/ACCELERATORS.md` + installer refs), and tighten `validate-governance.sh:467-476` to enforce the matching-plan-file rule. Check: `validate-governance.sh` FAILs on an orphan PLAN-NNN dir (added), passes on the repo.
- [ ] [P3] [tools/check-version-drift.py] [scripts/install-accelerators.sh] [scripts/local/] [benchmarks/hook-latency-p50-p99-post-batch-F.jsonl] [docs/OWNER-CEREMONY-CONTRACT.md] **dead-code-01/02/04/06/08** — wire-or-remove check-version-drift (false docstring); fix install-accelerators:165 dead `EMIT-WIRING-DESIGN.md` pointer + stale note; create `scripts/local/historical/` (ADR-098:232) and move the 7 shipped ceremony scripts; delete/annotate the null-valued benchmark jsonl (fix its dead `replay.py` path); fix OWNER-CEREMONY-CONTRACT:167 `generate-ceremony.sh` path. Check: each cited dead path resolves or the reference is deleted.
- [x] ~~**backlog-issue-template**~~ — **REFUTED at plan-verify (S255)**: `.github/ISSUE_TEMPLATE/` shipped in `9777a8d` (bug.md, feature.md, skill-proposal.md, config.yml); all other community-health files also present (CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, PR template, LICENSE). No action. Optional Owner verify-only step: confirm the GitHub community-profile page shows 100% and only act on whatever specific element it flags.

### Wave F — model/substrate modernization (backlog #3)
Check: model-deprecations.json has fast-mode model_id entries AND tier_policy tests pass with the new MODEL_ID member

- [x] ~~**substrate-refresh**~~ — **ALREADY DONE (verified S255)**: committed as `37867c2` (ledger refresh + companion test update; Codex pair-rail APPROVE recorded in the commit message). `check-substrate-watch.py --check` already reports `current`; suite 14/14. No execution needed.
- [ ] [P2] [.claude/scripts/model-deprecations.json] **fastmode-deprecation** — the checker has NO class/mode concept (per-`model_id` literals only): add ledger entries `claude-opus-4-6-fast` (retirement 2026-06-29, silent standard-speed fallback) + `claude-opus-4-7-fast` (retirement 2026-07-24, hard error). Check: `check-model-deprecations.py --json` lists hits for both ids (expected severity INERT — sole in-repo occurrences are `canonical_models.json:875/886/897`, matched by the `by-design-id-carriers` inert rule); extend `test_check_model_deprecations.py` asserting the new entries parse and classify BREAK by date.
- [ ] [P2] [.claude/hooks/_lib/tier_policy/_types.py] [.claude/adr/ADR-NNN-sonnet-5-tier.md] **sonnet5-tier** — author an ADR (cost/capability envelope: intro $2/$10 → $10 std, -33% vs 4.6, tokenizer +30%) and do the KERNEL edit to the closed `MODEL_ID` enum: ADD the Sonnet-5 member. "Reconcile OPUS47" = **docstring/comment fixes ONLY at :12/:41/:94 — do NOT rename the `MODEL_ID.OPUS47` member** (stable identifier per the R-CR R2-2 note at :41; a rename is a breaking ref-sweep with zero benefit — debate/Critic-D). Add a regression test pinning the CURRENT M-tier routing UNCHANGED so the reconcile cannot silently repoint (debate/Critic-A). Routing flip to Sonnet 5 stays OUT (see OQ1). CANONICAL/KERNEL → ceremony. Check: tier_policy loader + type tests pass (6 `test_tier_policy_*` files) incl. the new routing-pin test; model-keyed cost surfaces updated where they exist (`.claude/data/canonical_models.json` / cost-table.yaml) — NOTE `.claude/scripts/predict-budget/` carries no model-id calibration (history-median estimator, zero `claude-*` literals), so no re-baseline artifact lives there.
- [ ] [P3] [.claude/scripts/red-team-corpus/] **nested-subagent-redteam** — add red-team cases for Claude Code 2.1.19x nested-subagents (5 levels) + background-agent auto-push against the spawn/canonical guards; OR defer to a follow-on plan if scope balloons. Check: added corpus cases OR §Deferred entry with successor target.

### Wave G — closeout
Check: full CI gate set green locally (validate-governance --fast, shellcheck -S warning, env-hygiene, check-contamination, perf p95/p99, check-claude-md-claims) AND VERSION bumped AND CHANGELOG updated

- [ ] [P0] [CLAUDE.md] [SBOM.md] — re-run `check-claude-md-claims.py` after all ADR/skill/hook count changes (tolerance=0 ENFORCING gate); reconcile any drift. ALSO (debate C4): amend CLAUDE.md §4 to codify the input-vs-infra fail-mode distinction — input-parse failure in a security matcher is fail-CLOSED by design (precedents: `_e3:907-922`, `_check_credential_leak:692-695`); INFRA failure (missing file / import / timeout) remains fail-open. §4 is Gate-1 cache-stable → this is a closeout-only edit, LAST in the session. Check: `check-claude-md-claims.py` exits 0; §4 carries the distinction.
- [ ] [P0] [VERSION] [CHANGELOG.md] [npm/package.json] — bump `1.0.0`→`1.0.1` in **BOTH** VERSION and `npm/package.json` (debate/Critic-B M1 release-blocker: npm-publish.yml:72-81 hard-fails the publish on mismatch); write the CHANGELOG entry enumerating the fixed findings. Check: VERSION reads 1.0.1 AND `node -p "require('./npm/package.json').version"` reads 1.0.1; CHANGELOG has the entry.
- [ ] [P0] [pre-push] — run the EXACT CI gates (not just touched-file pytest): full hooks+scripts suites, shellcheck `-S warning`, env-hygiene, contamination, perf p95/p99; force exec bit where needed. Check: every CI job's local equivalent is green.
- [ ] [P0] [fresh-session probe] — after the final commit, open a FRESH session (or re-launch) and run the governance-01 Check verbatim (debate C5: hooks load at session start — only a fresh session proves the pair-rail registration is live again). Check: the registered command executes the hook (no `hook not found` + `{}`).

---

## Release floor & degradation ladder (debate C7 — all 4 critics)

- **Floor (non-negotiable for the v1.0.1 tag):** Wave A + Wave B-core (tests-01/02/07 wiring + the 55-site hygiene burndown) + **error-handling-03 null-guards (the only Wave C floor item — closes backlog #4 / the `wf_071ef6c5` crash class; Codex R5-P2)** + Wave D (tarball + packlist gate) + Wave G. A quarantined flaking root does NOT block the tag (quarantine lane rule, Wave B Check).
- **Cut order under session degradation:** E → F (P3 first, then P2s) → C economics items (error-handling-03 null-guards are FLOOR, never cut). **Wave D is NOT cuttable** (Codex pair-rail P2: the packlist gate correctly FAILS while the blanket `cp -r .claude npm/` staging persists — gate without staging-fix = blocked release, staging-fix without gate = recurrence vector; they land together in the floor). If Wave D cannot land, the release is **BLOCKED**, not shipped-dirty.
- **Pre-moved to v1.0.2 already (this revision):** `_lib/tests` 128-site env-hygiene burndown; backlog-oidc.
- **If only the floor ships:** tag it v1.0.1; everything cut rolls into a v1.0.2 plan stub created at closeout. Split-as-primary (Critic-D) is thereby absorbed: the floor IS the hotfix release if degradation forces it.

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

## Deferred (successor target required — audit defers + debate defers)

- **governance-04** (7500) — 15 registered hooks absent from `_KERNEL_PATHS`
  (`check_arbitration_kernel.py:76`): 11 `check_*` incl. blocking-capable
  `check_adversary` + `check_config_protection`, plus `accel_dispatch` /
  `turbo_sessionstart` / `codex_review_user_code` / `review_loop`. (The audit
  shard said "14 post-ADR-116-AMEND-1" — that temporal subset is not
  reproducible from the squashed public history; live count re-derived S255.)
  Kernel expansion needs its own ADR + ceremony; too large for v1.0.1. → follow-on plan.
- **governance-07** (6000) — `NotebookEdit` not covered by canonical-edit/arbitration
  matchers nor `permissions.deny`; exploitability bounded to `.ipynb`-parseable guarded
  targets. → fold into the governance-04 kernel-matcher plan.
- ~~**tests-07**~~ — **PULLED INTO Wave B by debate consensus C2** (one-line serial
  marker; `-m "not serial"` filter already live at validate.yml:298). No longer deferred.
- **burndown-lib-tests** (debate C8) — the 128-site `_lib/tests` env-hygiene burndown:
  files are canonical-guarded (`.claude/hooks/_lib/**/*.py`), making it the largest
  ceremony-scoped item; deferred WITH its `_DEFAULT_SCAN_ROOTS` tuple entry. → v1.0.2.
- **backlog-oidc** (debate C6) — npm Trusted Publishing migration: own plan with an
  Owner web-console prereq + fallback window (NPM_TOKEN stays until one OIDC publish
  succeeds). NPM_TOKEN expiry ~2026-09-28 calendar-flagged in v1.0.1. → v1.0.2.

> NOTE — `nested-subagent-redteam` (Wave F P3) is NOT one of the 41 confirmed findings;
> it is net-new red-team scope from the substrate sweep. It may itself be deferred to a
> follow-on plan if the corpus scope balloons — that is a Wave F execution decision, not
> a double-count against the audit's 3 defers.

## Resolved questions (debate round-1, 2026-07-01 — RATIFIED by Owner, Wave 0, 2026-07-02)

> **Ratification record (Wave 0, S256, 2026-07-02):** the 3 resolutions were
> presented to the Owner via AskUserQuestion (K10, debate synthesis marked
> "(Recomendado)") and EXPLICITLY answered, verbatim: OQ1 = "Sim, membro + ADR
> agora (Recomendado)"; OQ2 = "Sim, um sentinel (Recomendado)"; OQ3 = "Sim,
> única com floor (Recomendado)". Same Wave-0 sitting, the Owner GPG-signed
> (key `AE9B…DC74`) the PLAN-152 sentinel encoding OQ2 (14-file enumerated
> allowlist, anchor `c88daf9`, ADR-157 allocated per OQ1) and the 3 pending
> PLAN-140/141/142 sentinels (SIGNED, not residue-closed — backlog #1 /
> governance-06 closed).

1. **OQ1 — Sonnet-5 scope** · RESOLVED (unanimous, 4/4 critics + CEO):
   ADD the Sonnet-5 `MODEL_ID` member + envelope ADR now; "reconcile OPUS47" =
   docstring fixes at `_types.py:12/:41/:94` ONLY (member name is a stable
   identifier — no rename); add a regression test pinning current M-tier routing
   UNCHANGED. The routing flip to Sonnet 5 is a cost/behavior decision → own plan
   (v1.0.2+) with soak + documented revert.
2. **OQ2 — ceremony batching** · RESOLVED (3/4 critics + CEO): ONE sentinel,
   Scope = enumerated explicit-file allowlist (no globs), incl. `validate.yml` +
   `coverage.yml`, excl. `.claude/workflows/*.js`; mechanical `touched−scope=∅`
   re-check at every wave boundary + one out-of-scope dry-run probe exercising the
   gate itself. Minority (Critic-C, recorded): a second Wave-A-only sentinel is a
   zero-cost variant the Owner may choose at the same signing sitting.
3. **OQ3 — single vs split** · RESOLVED (synthesis of 4 positions): SINGLE v1.0.1
   as target, governed by the §Release floor & degradation ladder (floor =
   A + B-core + C-null-guards (error-handling-03) + D + G; pre-committed cut
   order; `_lib/tests` burndown + OIDC already pre-moved to v1.0.2). If
   degradation forces floor-only, the floor ships AS v1.0.1 and the remainder
   becomes v1.0.2 — split is thereby the built-in fallback, not a separate
   decision.

## How to continue

Next terminal (Fable, `effort: high`/`xhigh`). **Debate is DONE** (round-1
design-coherent, 4× ADJUST_PROCEED → PROCEED; artifacts in
`.claude/plans/PLAN-152/debate/round-1/`; V0 satisfied — shipping still requires
V1 deterministic + V2 Codex pair-rail + V3 Owner GPG per wave):

> Read PLAN-152 (this revision). Execute Wave 0 with the Owner: (1) ratify the 3
> §Resolved questions via AskUserQuestion (K10); (2) 3 pending sentinels signed or
> closed; (3) PLAN-152 sentinel signed with the enumerated-allowlist Scope (OQ2).
> Then execute wave-by-wave A→G under the §Release floor & degradation ladder;
> each wave self-verifies against its `Check:` line before advancing.
> THE AUTO PAIR-RAIL IS DEAD FOR THE WHOLE RUN (hooks load at session start):
> EVERY guarded/canonical commit — Waves A/B/C/D/F — requires a manual
> `codex exec review --uncommitted` APPROVE recorded in the commit message
> (`37867c2` precedent); `touched−scope=∅` re-checked at every wave boundary. Close with Wave G: VERSION + npm/package.json
> → 1.0.1, CHANGELOG, full CI gate set green locally, `check-claude-md-claims`
> tolerance=0, CLAUDE.md §4 input-vs-infra amendment (LAST edit), then the
> fresh-session pair-rail probe.

## Success criteria

- [ ] All 32 `fix` findings resolved OR explicitly re-classified with an on-disk pointer (incl. the two debate re-classifications: `_lib/tests` burndown + OIDC → §Deferred/v1.0.2) — zero silently dropped.
- [ ] All 6 `accept` + all §Deferred findings have an on-disk pointer — zero silently dropped.
- [ ] Backlog closed: npm tarball (#2), Sonnet 5 (#3), workflow null-guards (#4), sentinels (#1 / Wave 0); OIDC deferred-with-pointer + NPM_TOKEN expiry (~2026-09-28) calendar-flagged. (Issue template: already shipped in v1.0.0 — verified S255, no action.)
- [ ] Wave A: pair-rail registration fixed (fresh-session probe green at Wave G); `rm -rf ~ ";"` blocks AND `echo it's fine` still allows; cache path hardened with positive+negative tests.
- [ ] Wave B: the 3 security root-tests (now `tests/unit/`) collect + pass in CI; env-hygiene 55→0 on the v1.0.1 roots (`_lib/tests` 128 → v1.0.2).
- [ ] §Release floor shipped even under degradation; anything cut has a v1.0.2 plan stub.
- [ ] Wave D: `npm pack --dry-run` ships zero `(tests|fixtures|eval|red-team|PLAN-[0-9])` paths (but KEEPS `PLAN-SCHEMA.md` + `examples/`); packlist gate live.
- [ ] `check-claude-md-claims.py` (tolerance=0) + `validate-governance.sh` + full CI green.
- [ ] VERSION=1.0.1, CHANGELOG entry, tag ceremony ready.
- [ ] `check-contamination` green (no foxbit/employer-class residue introduced).

## Reference links

- Audit findings: `project_s254_audit_fanout_findings.md` (memory); run `wf_071ef6c5`.
- Backlog: `project_v101_backlog.md` (memory) — tarball (#2), Trusted-Publishing OIDC,
  NPM_TOKEN expiry ~2026-09-28, issue template.
- Launch record: `project_s253_plan151_launch_built.md`.
- Substrate refresh: committed as `37867c2` (pair-rail APPROVE in the commit message) — Wave F item already done.
- Plan claim-verification (S255): workflow `wf_9a1dd57e` — 62 claims checked read-only
  (51 CONFIRMED / 9 PARTIAL / 1 STALE / 1 INCORRECT / 0 unverifiable); all 11
  divergences folded into this revision. Full shards in the session transcript dir.
- Debate round-1 (S255, design-coherent): `.claude/plans/PLAN-152/debate/round-1/`
  — proposal, 4 critiques (4× ADJUST_PROCEED), anonymization-map, consensus
  (verdict PROCEED, 10 plan adjustments indexed there).
