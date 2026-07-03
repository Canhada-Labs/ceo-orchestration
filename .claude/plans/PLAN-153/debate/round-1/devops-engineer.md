---
plan: PLAN-153
round: 1
archetype: devops-engineer
verdict: ADJUST_PROCEED
created_at: 2026-07-03
---

## Verdict

ADJUST_PROCEED — the plan is governance-coherent and the wave ordering (A→E→B→C→D→G→F) is right from a blast-radius seat. But three release/CI-mechanics items are load-bearing and currently under-specified or self-contradictory, and one Wave-E design detail can make the new gate *false-green on the exact S254 class it targets*. Fix those five before E/B execute; everything else is advisory.

## Summary (≤ 3 bullets)

- Strong: security wave promoted to 2nd, telemetry-before-mass-creation (C→D), "import the class not the implementation", and the honest "no auto-pull, Owner gate preserved" installer posture. These are the correct platform instincts.
- Weak (blocking): Wave B's "`next` dist-tag for -rc" silently reverses a ratified anti-goal (RC tags MUST NOT publish to npm); new CI surfaces (supply-chain-watch, harness-config gate) are speced without runner choice, without pytest-wiring for their own tests, and without modelling the harness's real path-resolution — the same CI-dark / fail-open classes we just paid for in PLAN-152/S254.
- Blind spot: the plan treats `check-harness-config.py` as new green field when `check-active-hooks-executable.py` already covers exists+exec-bit from `REPO_ROOT`; the *delta* (fail-open-shim + runtime-resolution modelling) is the only part with value, and it's the hard part.

## Risks

- **R-DO1 — `next` dist-tag for RC contradicts a shipped anti-goal. Severity: HIGH.**
  Wave B item 5 proposes "`next` dist-tag for -rc". Today `npm-publish.yml` hard-excludes RC tags (`if: "!contains(github.ref, '-rc.')"`) precisely to honor PLAN-013 anti-goal #3 ("NO npm publish during RC") and #16 ("NO auto-publish from tag without manual approval"), and GA publish routes through the `production-npm` manual-approval environment. Publishing RCs under `next` would (a) reverse a ratified anti-goal and (b) push a public artifact *without* the Owner-in-the-loop environment gate. Mitigation: drop the `next`-dist-tag idea, OR explicitly re-ratify the anti-goal with the Owner and route any RC publish through the *same* `production-npm` environment. Do not let this land as an incidental installer-wave line.

- **R-DO2 — new scheduled workflow on the `Ceo` runner is a queue/cost footgun. Severity: MEDIUM.**
  Every scheduled advisory workflow in the repo runs on `ubuntu-latest` (chaos, otel-smoke, perf-profile, reality-ledger, red-team, tier-policy); the *only* cron on `Ceo` is the heavy nightly `coverage.yml`, deliberately moved there off the per-push path (S220). The org `Ceo` 8-core larger runner cold-provisions in 30–60 min and queues *eternally* if the org Actions budget is at $0 (recorded footgun: feedback-larger-runner-setup-gotchas). A `supply-chain-watch.yml` cron on `Ceo` inherits that failure mode for a job that needs no cores. Mitigation: spec `supply-chain-watch.yml` (and any Wave-E gate that could be a standalone job) as `runs-on: ubuntu-latest`. Keep `Ceo` for the existing heavy validate/coverage jobs only.

- **R-DO3 — new gate scripts risk re-shipping CI-dark tests. Severity: HIGH (this is our own paid lesson).**
  Waves E/B/C add stdlib scripts (`check-harness-config.py`, `doctor.sh`/`upgrade.sh` replay, JSON-manifest validator, `/skill-health`, `/context-budget`). PLAN-152 tests-01 existed *because* ~1.4k tests — including security tests — shipped in v1.0.0 and ran in **no** CI job. New `.sh` are auto-covered by the `find`-based shellcheck + exec-bit steps, but new `*.py` test files are **not** auto-discovered: validate.yml pins explicit pytest *path lists* (hooks/tests, scripts/tests, the tests-01 roots). A new `check_harness_config_test.py` dropped anywhere else runs nowhere. Mitigation: make "wire this script's tests into an explicit validate.yml pytest path (both `not serial` and `serial` passes) in the same commit" a hard checklist item on every execution unit that adds a script. A security gate that is itself untested-in-CI is the S254 shape recursed.

- **R-DO4 — `check-harness-config.py` can be false-green on the S254 class. Severity: HIGH.**
  The S254 P0 was a hook whose path did not resolve *at runtime*, so the `_python-hook.sh` shim fell through to `{}` (allow). The shim resolves via `$CLAUDE_PROJECT_DIR`; the existing `check-active-hooks-executable.py` resolves each hook relative to `REPO_ROOT`. A file can be present from `REPO_ROOT` yet unresolvable at runtime — so a REPO_ROOT-relative scanner would have *passed the original bug*. If the new gate copies that resolution model, it certifies "no fail-open shim" while the exact fail-open shim ships. Mitigation: the gate must model the harness's real resolution (`$CLAUDE_PROJECT_DIR` + the shim's own dirname/cwd logic) and assert the negative — a planted relative-path/fail-open-shim fixture must go **red**. The plan's own success-criterion ("gate red on a planted fail-open shim fixture") is right; make the fixture reproduce the *runtime-resolution* failure, not just a missing file.

- **R-DO5 — upgrade=replay has no story for pre-Wave-B installs. Severity: MEDIUM.**
  Wave B persists the original install request and defines `upgrade = replay of recorded request`. Existing adopters (and our own dogfood install) have `skill-manifest.sha256` + HMAC sidecar but **no** recorded request — the current `_write_baseline_manifest` writes only `sha256 relpath`. A replay-based `upgrade.sh` has nothing to replay for them. Mitigation: on a missing request record, `upgrade.sh` must fall back to the existing ADR-155 `--dry-run` + drift-classifier path (which is already drift-aware), never error or no-op. State this migration/back-compat contract in the wave.

- **R-DO6 — two tag-triggered workflows; "idempotency" must name which. Severity: MEDIUM.**
  `v*` tags fan out to *both* `release.yml` and `npm-publish.yml`. "release.yml idempotency + already_published check" must be explicit that: the npm `already_published` guard lives in `npm-publish.yml` (re-running a published tag currently 403/409s on `npm publish`), and `release.yml`'s `gh release create` is *also* non-idempotent (fails if the Release exists) — a tag-workflow re-run needs `gh release view || gh release create`. Mitigation: scope the idempotency work to both workflows and both non-idempotent operations, and add the version↔plugin-manifest sync test to the release gate where the other VERSION-consistency asserts already live.

## Must-fix (blocking)

1. **Reconcile the `next`-dist-tag/RC-publish contradiction (R-DO1).** Either remove it or re-ratify anti-goals #3/#16 with the Owner and route RC publish through `production-npm`. No RC artifact reaches npm without the manual environment gate.
2. **Pin `supply-chain-watch.yml` (and any standalone Wave-E gate job) to `ubuntu-latest` (R-DO2).** Reserve `Ceo` for existing heavy jobs; keep scheduled crons off it to avoid the $0-budget eternal-queue class.
3. **Make CI-wiring of new-script tests a per-execution-unit checklist item (R-DO3).** Every new `*.py` under Waves B/C/E adds its tests to an explicit validate.yml pytest path (both `serial`/`not serial` passes) in the same commit. Security gates especially cannot ship CI-dark.
4. **`check-harness-config.py` must model runtime path-resolution, not `REPO_ROOT` (R-DO4), and dedupe with `check-active-hooks-executable.py`.** Ship the planted fixture as a *runtime-unresolvable* shim so the gate proves it catches the real S254 class; extend the existing script or clearly partition responsibilities so two gates don't drift.
5. **Specify upgrade=replay back-compat for pre-Wave-B installs (R-DO5):** missing request record ⇒ fall back to ADR-155 drift-classifier, never error/no-op.

## Nice-to-have (advisory)

1. **Generated marketplace/plugin manifests need an idempotency gate.** `build-plugin.py` output (`.claude-plugin/{marketplace.json,plugin.json}`) should be gated like the existing "Skill inventory idempotency" step (regen + diff), or it silently drifts from source. Also confirm `/plugin update` is Owner-initiated pull, not background auto-update — an auto-pull marketplace contradicts the PLAN-125 manual-gate ethos.
2. **`npm audit signatures` value is thin on a zero-dep package.** With 0 runtime deps it mostly re-verifies our own provenance attestation; the higher-value half is the online SHA-pin/workflow-policy validator. Note this so the watch job's effort goes to the SHA-drift/policy check (which extends the existing offline `check-action-sha-drift.py`), not to a near-noop audit.
3. **`release.yml` publish-release step notes describe "first public release"** in the `gh release create --notes`; a v1.0.2+/next-tag flow should templatize that string or it ships a stale note.
4. **AGENTS.md becomes an input to the Codex pair-rail (`codex exec`).** Give it a freshness/derived check — drift there degrades the *review rail* silently, which is worse than a docs typo.

## Unseen by the original plan

1. **The new security gate is itself an unguarded input surface.** `check-harness-config.py` reads `.claude/settings.json` to decide what's fail-open. If an attacker/misedit can shape settings.json to *look* compliant to the scanner while resolving differently at runtime (the R-DO4 gap), the gate becomes a rubber stamp — a "detection that trains the operator to trust a broken config." Model the adversarial case: the fixture corpus must include a settings.json that passes the *old* exists-check but fails *runtime* resolution.
2. **Fork-PR execution of the new gates is unspecified.** validate.yml runs on `pull_request` (forks included) and the plan's Wave-E deny-baseline touches settings.json. Confirm the new gate + deny baseline are static/no-network/no-credential on fork PRs (the plan's existing surface-hygiene step is explicitly "no network, runs on fork PRs" — hold the new gate to that same bar), and that `supply-chain-watch` (which may need registry access) is `schedule`-only, never fork-`pull_request`.
3. **No rollback/kill-switch named for the two new CI gates.** Every other job here honors `vars.CEO_SOTA_DISABLE != '1'`. New jobs/steps should inherit that switch so a false-positive gate can be disabled without a YAML revert mid-incident.
4. **`Ceo` contention is additive.** validate.yml already runs 5 jobs on `Ceo` per push; adding gate *steps* to the `validate` job is free, but any new *job* on `Ceo` widens the concurrency surface on a single 8-core runner. Prefer adding steps to the existing `validate` job over new `Ceo` jobs where the check is cheap.

## What I would NOT change

- **The A→E→B→C→D→G→F ordering.** Docs-first (cheap, honesty), security gates second (highest lesson value), telemetry before mass skill creation, learning-loop last. This is exactly the blast-radius discipline PLAN-152 established; don't let anyone "optimize" D before C.
- **No-auto-pull upgrade / Owner-gated everything.** Keeping the manual gate (PLAN-125) through the installer lifecycle and the learning loop is the whole differentiator. The "nothing self-activates" red line on Wave F is correct and must survive later rounds.
- **SHA-identical uninstall safety and stdlib-only ports.** Our uninstall (delete only on SHA match + HMAC sidecar) is stronger than the upstream doctor/repair; the plan keeps it. Zero-runtime-dep, stdlib-py≥3.9 rewrites preserve the SBOM posture. Don't trade either away for parity with the upstream node implementation.
- **Treating imported SKILL.md content as untrusted data with line-by-line injection review.** Correct posture; the artifacts note upstream skills instruct verbatim script execution.
