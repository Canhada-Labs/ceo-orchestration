# Workflow → ADR Governance Map

> PLAN-025 Batch G F-wf-009 — single-source-of-truth mapping every CI
> workflow to the ADR(s) that govern its behaviour, kill-switches, and
> release-chain participation.

Last updated: 2026-05-25 (PLAN-113 RW-E doc/count drift reconcile — added 5 missing workflows; 20 total).

## Workflow inventory

| Workflow | Purpose | Primary ADR(s) | Kill switch | Gate strength |
|----------|---------|----------------|-------------|---------------|
| `validate.yml` | Governance structure + Python tests + actionlint | ADR-003 (branch protection), ADR-007 (SPEC v1) | `CEO_SOTA_DISABLE=1` (repo var) | ENFORCING |
| `coverage.yml` | Tiered coverage (ADR-139): subprocess-capture + Tier-1 per-module gate (`--tier1-min 86` for the ≥86% subset) + repo-wide line floor (`--fail-under=67`); branch advisory | ADR-139, ADR-007 (SPEC v1), PLAN-025 Batch B | `CEO_TIER1_COVERAGE_ENFORCING=0`, `CEO_BRANCH_COVERAGE_ENFORCING=0` | ENFORCING (Tier-1) |
| `red-team.yml` | Adversarial corpus run (State 1) | ADR-011 (injection_flag v2.1) | `CEO_RED_TEAM_DISABLE=1` | ADVISORY (State 1) |
| `translations-drift.yml` | PT-BR ↔ EN parity check | ADR-023 (docs freshness) | — | ENFORCING |
| `adapter-live.yml` | Live adapter smoke (gated on API-key env) | ADR-028 (multi-LLM parity), ADR-040 | `CEO_LIVE_ADAPTER_STUB=1` | ADVISORY |
| `formal-verify.yml` | TLA+ TLC + conformance harness | ADR-044 (formal verification pilot) | `CEO_FORMAL_VERIFY_DISABLE=1` | ADVISORY (weekly) |
| `release.yml` | Release gate (VERSION ↔ tag, 24h RC hold) | ADR-007 (SPEC v1 + SemVer + RC), ADR-014, ADR-103 | `CEO_SOTA_DISABLE=1` (repo var) | ENFORCING on tag push |
| `smoke-install.yml` | Fresh-install dogfood | ADR-007 | — | ADVISORY |
| `npm-publish.yml` | NPM publish — granular-token auth + Sigstore `--provenance` (Trusted-Publishing OIDC = v1.0.2 follow-up, PLAN-152) | ADR-012 (cross-adapter goldens + NPM publish) | — (opt-in via workflow_dispatch) | ENFORCING on tag push |
| `chaos.yml` | Chaos + resilience weekly probe | ADR-037 (chaos testing methodology) | `CEO_CHAOS_DISABLE=1` | ADVISORY (weekly) |
| `otel-smoke.yml` | OpenTelemetry export smoke | ADR-035 (OTEL export) | `CEO_OTEL_DISABLE=1` | ADVISORY (weekly) |
| `perf-profile.yml` | Hook latency p50/p95/p99 profile | ADR-024 (perf baseline policy) | `CEO_PERF_PROFILE_DISABLE=1` | ADVISORY (weekly) |
| `shadow-ci.yml` | Policy-dispatch dual-path shadow run | ADR-045 (policy-as-code), ADR-049 | `CEO_POLICY_ENGINE_DISABLE=1` | ADVISORY |
| `benchmarks.yml` | Skill benchmark corpus run (paths-filtered, fork-safe) | ADR-007 (benchmarks.schema) | — | ADVISORY |
| `actionlint.yml` | Static analysis of workflow YAML | PLAN-025 Batch G F-wf-008; ADR-054 (token rotation) | — | SOFT-FAIL (1 green week → flip ENFORCING) |
| `mcp-smoke.yml` | MCP server smoke test (end-to-end MCP protocol) | ADR-042 (MCP introspection) | `CEO_MCP_DISABLE=1` | ADVISORY |
| `mutation-gate.yml` | Mutmut mutation testing gate (spool/drain exclusions) | ADR-139 (coverage doctrine), PLAN-113 AC4 | `CEO_MUTATION_GATE_DISABLE=1` | ADVISORY |
| `reality-ledger.yml` | Reality-ledger YAML schema validation | PLAN-086 (reality ledger), ADR-007 | — | ADVISORY |
| `tier-policy.yml` | Tier-policy CLI integration + stale-detection | ADR-124 (risk-tiered defaulting) | — | ADVISORY |
| `tournament.yml` | Skill benchmark tournament (multi-model; cost-capped) | ADR-052 (multi-model dispatch) | `CEO_TOURNAMENT_DISABLE=1` | ADVISORY (weekly) |

## Release-chain participation

Workflows gated by `release-gate` in `release.yml`:

- `chaos.yml`, `otel-smoke.yml`, `perf-profile.yml`, `adapter-live.yml`,
  `red-team.yml`, `formal-verify.yml` — all must have a successful run
  within the last 14 days for a GA release tag to pass the staleness
  gate (release.yml §Weekly workflow status gate).

Workflows NOT in release-chain (advisory-only):

- `actionlint.yml` — soft-fail; UI-only signal; 1-week graduation
- `benchmarks.yml` — paths-filtered; fork-safe; cost-capped advisory
- `translations-drift.yml` — runs on its own PR-trigger; release gate
  does not block on it
- `smoke-install.yml` — runs on release tag but not enforced for non-tag

## Token + secret dependencies

| Workflow | Secret | Rotation cadence |
|----------|--------|------------------|
| `adapter-live.yml` | `ANTHROPIC_API_KEY` (repo secret) | 90 days (ADR-054) |
| `npm-publish.yml` | `NPM_TOKEN` (repo-scoped npm granular token, env `production-npm` — the actual publish auth; **expires ~2026-09-28**, regenerate before the next release after that) + a per-run OIDC JWT via `id-token: write` used ONLY for Sigstore `--provenance` attestation, not registry auth (blast-radius of the JWT: a compromised step could mint short-lived tokens toward OIDC-aware services; mitigated by the `production-npm` manual-approval gate before any publish step). Trusted-Publishing (OIDC registry auth) is a v1.0.2 follow-up (PLAN-152 §Deferred backlog-oidc). | NPM_TOKEN: 90-day granular token; JWT: per-run |
| Others | `github.token` (ephemeral per-workflow) | N/A |

See `ADR-054-github-token-rotation.md` for the full rotation policy
and `docs/rotation-log.md` for the append-only rotation history.

> **`id-token: write` blast-radius note** (`npm-publish.yml`): this permission
> allows the workflow to call the GitHub OIDC endpoint and receive a signed JWT
> asserting the workflow's identity. A malicious step injected before
> `actions/attest-build-provenance` or `npm publish --provenance` could use
> this token to authenticate against any OIDC-aware external service (e.g.,
> cloud provider role assumption). The `production-npm` environment gate
> (requiring manual Owner approval) limits this to manually-triggered GA-tag
> runs only. No `pull_request_target` trigger exists (explicitly forbidden per
> `.github/workflows/_README.md` §fork-safety).

## Flake-auto-removal policy (red-team.yml)

Per PLAN-024 F-wf-006, flaky red-team corpus entries that produce
>30% false-positive rate in a 30-day rolling window SHOULD be
demoted to `--skip-known-flake` (marked in the corpus manifest)
pending refactor. Current State: manual review; automated removal
tracked as DYN item for Sprint 26.

## actionlint soft-fail → hard-fail flip

`actionlint.yml` ships with `continue-on-error: true`. After **one**
calendar week of green runs (no false positives, no actionlint
regressions), remove the `continue-on-error` flag to flip it
ENFORCING. Tracker: this doc's §Status timeline.

### Status timeline

| Date | Event |
|------|-------|
| 2026-04-18 | `actionlint.yml` shipped with `continue-on-error: true` (PLAN-025 Batch G) |
| 2026-04-25 | Earliest flip date (1 green week threshold) |

## Cross-references

- `.claude/adr/ADR-054-github-token-rotation.md` — token rotation policy
- `docs/rotation-log.md` — rotation history
- `.github/CODEOWNERS` — merge gate
- `docs/threat-model.md` §T-new-toctou + §Residual-sentinel-hmac — adjacent workflow-related residuals
- PLAN-024 F-wf-001 through F-wf-009 — workflow findings closed by Batch G
