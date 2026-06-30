# ADR-021: E2E integration harness contract

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 10 (PLAN-010 Phase 1)
**Related:** ADR-008 (hook adapter layer), ADR-014 (hook migration batch policy), ADR-012 (cross-adapter golden fixtures)

## Context

Through Sprint 9 the framework accumulated 728 unit tests across
`.claude/hooks/tests/` and `.claude/scripts/tests/` plus 27 byte-identity
fixtures plus six cross-adapter goldens. Coverage measures 88% and the
gate enforces 86%. What is missing: a layer that exercises hooks
**as Claude Code spawns them** — via subprocess, JSON on stdin, JSON
decision on stdout — across end-to-end sessions that chain more than
one hook.

Unit tests call `decide()` and `build_entry()` directly. That path
never exercises:

- The `_python-hook.sh` shim / argv contract
- stdin parser failure modes under real subprocess piping
- The audit log filelock under genuine cross-process contention
  (our unit tests use a single process + `FileLock`; 2 real processes
  never grab the same OS-level fcntl lock in CI)
- `install.sh` producing a complete target layout (smoke-install.yml
  touches this but only a few smoke assertions)

PLAN-010 debate round 1 (C5) listed 12 scenarios the E2E suite must
cover before Sprint 10 ends. This ADR captures the contract so future
scenario authors do not drift.

## Decision drivers

- **Isolation mandate.** Any test that touches real `$HOME` or the
  real framework audit log is a production-data hazard. The unit
  test bed already solves this via `_lib.testing.TestEnvContext`; the
  E2E bed MUST reuse it, not re-invent it.
- **Subprocess fidelity.** The hooks ship as single-file scripts with
  an argv/stdin contract. Importing them and calling `main()` inside
  pytest bypasses the shim — any bug in that shim or in the packaging
  of `_lib` would go undetected. E2E tests MUST invoke hooks via
  `subprocess.run`.
- **xdist compatibility.** CI will eventually want parallel test
  execution. The suite must assume nothing about CWD, shared files,
  or serial execution. Per-test tmpdirs (from TestEnvContext) already
  give us this; we must not add any shared state on top.
- **Runtime budget.** The whole E2E suite must finish in under 30
  seconds locally so developers run it on every commit. (Target
  validated at 5.66s on a 2021 Apple M1.)

## Decision

### 1. Scope of "scenario"

A scenario is a pytest test function that:

- Uses the `ceo_env` fixture (or instantiates a `_IntegrationEnv`
  directly) for environment isolation.
- Invokes at least one real hook subprocess OR `install.sh`.
- Asserts **behavior** (decision JSON, file presence, audit contents),
  not merely `returncode == 0`.

Acceptance-criterion scenarios in PLAN-010 Phase 1 debate C5 are
enumerated 1-12; any future Phase in PLAN-010 that adds scenarios must
append to the enumerated list in the plan before merging code.

### 2. TestEnvContext reuse mandate

`tests/integration/conftest.py` wraps `_lib.testing.TestEnvContext` as
the `ceo_env` fixture. No test file may:

- Call `monkeypatch.setenv` directly for `HOME`, `CEO_*`, or
  `CLAUDE_*` variables.
- Rewrite `os.environ` without relying on `ceo_env.tearDown()` to
  restore it.
- Hardcode an absolute path under `~`.

The single approved extension point is subprocess-level
`env_overrides` passed to `run_hook()`, which copies the current
(already-isolated) environment and layers additions on top. This is
the only way a test can override `CEO_*` for a specific hook call
without leaking into the next test.

The conftest module docstring cites this rule explicitly.

### 3. Subprocess invocation contract

`run_hook(hook_name, payload, env_overrides=None, timeout=5.0)` in
`conftest.py` is the single supported entrypoint. It:

- Resolves the hook path relative to `REPO_ROOT / ".claude" / "hooks"`.
- Asserts the hook file exists (fails loud, not silent).
- Serializes the payload as JSON on stdin.
- Captures stdout + stderr as text.
- Enforces a 5s default timeout.

Tests that need a different timeout (e.g. install.sh smoke at 90s)
use `subprocess.run` directly with explicit arguments; they MUST NOT
re-implement JSON piping because that path's serialization rules must
stay centralized.

### 4. Fixture corpus policy

Fixtures live under `tests/integration/fixtures/`:

- `minimal-plan.md` — frontmatter-only plan for `check_plan_edit`
- `minimal-debate.md` — debate-round-1 shape placeholder
- `injection-payload.md` — intentionally malicious content that
  matches scan-injection's 3 pattern families (verified at PR review)

Fixtures are checked in. They are NOT generated at test-time. Rationale:
generated fixtures drift from the assertions that inspect them and
make git diffs illegible. When a new scenario needs new content, the
author adds the file.

### 5. xdist compatibility

Every test receives an isolated tmp tree via `TestEnvContext._tmp_root`.
No test writes to `REPO_ROOT`, `~/.claude/`, or `/tmp/<fixed-name>`.
Tests that need to run the install.sh smoke use `pytest`'s `tmp_path`
fixture, which is already xdist-safe.

If a future scenario genuinely requires serial execution (e.g. spawns
2 real subprocesses that share an OS-level resource), it must mark
itself `@pytest.mark.xdist_group("integration_serial")` rather than
assume serial execution globally.

### 6. Runtime budget + CI wiring

The suite runs as the `integration-tests` job in
`.github/workflows/validate.yml` with an 8-minute timeout. A single
run should land in under 30 seconds; the job timeout is high only to
cover CI runner cold-start + `pip install pytest`. If a scenario
pushes the local runtime above 30s, it must either be refactored or
split into a separate xdist group and kept out of the default happy
path.

### 7. What the E2E harness does NOT cover

- Production-traffic volume (that is Phase 4 hook-profiler territory)
- Cross-agent debate correctness (covered by unit tests on
  `_lib/audit_emit` + debate schema)
- Claude Code's own hook runner — we test the hook contract, not
  Claude Code
- Coverage gate impact — the E2E job does not run under `coverage.py`
  because subprocess coverage would require `--source` plumbing that
  would double the CI cost for negligible signal. The 86% coverage
  gate continues to be driven by the unit-test coverage job.

## Consequences

### Positive

- Future contributors who break the `_python-hook.sh` shim, stdin
  parser, or install.sh layout will see a red integration-tests
  job on their PR — a signal unit tests cannot produce.
- The scenario enumeration (1-12) is the first place where
  "compliance contract" means "observable end-to-end behavior", not
  just "schema validates".
- Dogfooded reuse of `_lib.testing.TestEnvContext` keeps the
  isolation discipline we established in Sprint 2 honest across both
  test tiers.

### Negative

- Two subprocess starts per test + the install.sh smoke (90s timeout)
  push the CI runtime budget by ~1 minute. Acceptable at 8 total jobs.
- pytest is a new dev dep. It is not shipped to target repos; only
  CI + contributor laptops need it. Documented in RELEASE.md under
  "dev dependencies".

### Neutral

- Future phases of PLAN-010 (hook-profiler in Phase 2,
  docs-freshness in Phase 3) will add more integration scenarios.
  This ADR's scenario policy applies to them transitively.

## Rollback

If the E2E job becomes flaky for runner-specific reasons, the job
can be downgraded to `continue-on-error: true` in validate.yml
without removing the scenarios. Recovery: stabilize, re-enable the
gate. Do NOT delete scenarios to quiet flakes — the entire point is
that flaky behavior-assertion is a real production signal.

## Enforcement commit

`0db6c3e5974a` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
