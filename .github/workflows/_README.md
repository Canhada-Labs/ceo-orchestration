# `.github/workflows/` — schedule, kill-switch, fork-PR rules

PLAN-012 Phase 2 (DevOps §S6 cron stagger + §R8 kill-switch parity +
§R9 fork-PR audit). Maintained by DevOps archetype.

## Weekly cron stagger (§R4)

Four weekly workflows were all cron-scheduled Monday 12:00 UTC, which
queued them onto the same free-tier runners and made triage confusing.
PLAN-012 §S6 spaced them 3 hours apart:

| UTC   | Workflow              | What runs                                 | Owning ADR |
|-------|-----------------------|-------------------------------------------|------------|
| 03:00 | `chaos.yml`           | thread-load + process-chaos + lockdown    | ADR-037 §3 |
| 06:00 | `perf-profile.yml`    | N=1000 hook profile + 90-day artifact     | ADR-024    |
| 09:00 | `otel-smoke.yml`      | stdlib mock receiver + dry-run            | ADR-035    |
| 12:00 | `adapter-live.yml`    | live-adapter smoke against real providers | ADR-040 §6 |
| 15:00 | `red-team.yml`        | adversarial corpus runner (40+ fixtures)  | PLAN-013 D.6 (ADR-044) |

### PLAN-014 Sprint 14 additions (Phase 0.7 per ADJ-043)

Four new weekly-cron slots reserved for PLAN-014 Phase B/F workflows.
Slot assignment locked here in Phase 0 BEFORE the workflows ship —
prevents Monday-AM collision with the 03-15 existing stagger.

| UTC   | Workflow                         | What runs                                       | Owning ADR | Shipped in |
|-------|----------------------------------|-------------------------------------------------|------------|------------|
| 16:00 | `formal-verify.yml`              | TLC runs on breaker + plan-lifecycle + debate-convergence TLA+ specs | ADR-044 + ADR-045 (amendments) | Phase B.6  |
| 18:00 | `replay-dry-run.yml` (optional)  | deterministic replay CI gate on recent plans   | ADR-046    | Phase F.1 (if shipped as CI) |
| 21:00 | `predict-budget-drift.yml`       | backtest drift detection on ≥10 historical plans | ADR-047    | Phase F.3  |
| 23:00 | `memory-shared-freshness.yml` (optional) | pattern-library size/redact-violation audit | ADR-048    | Phase F.5 (if shipped) |

**Order rationale:** Chaos runs first — its failures are highest-severity
and we want them surfaced before the remaining workflows run against the
same commit. Perf second (shares hooks with chaos). OTEL third (no
dependency). Adapter-live last of the original 5 (paid API round-trips).
Formal-verify (Sprint 14) takes 16:00 — TLC bounded to 60 min so won't
spill into 18:00. Replay/predict/memory-shared spaced 3h to follow the
original stagger discipline.

When adding a scheduled workflow, pick the next free 3-hour slot and
update this table. DO NOT re-crowd Monday 12:00 UTC. Occupied slots:
03/06/09/12/15/16/18/21/23 UTC Mon (next free: 00/19/20/22/01/02 UTC).

## CEO_SOTA_DISABLE kill-switch parity (§R8)

Every workflow in this directory honors `CEO_SOTA_DISABLE=1`. Operator
flow: Settings → Secrets and variables → Actions → Variables →
`CEO_SOTA_DISABLE=1`. Every workflow short-circuits on next trigger.

Implementation differs by job size:

| Workflow              | Pattern                 | Why                                    |
|-----------------------|-------------------------|----------------------------------------|
| `chaos.yml`           | Per-step `if:`          | ≤8 steps, kill-switch trace in UI      |
| `otel-smoke.yml`      | Per-step `if:`          | Same                                   |
| `perf-profile.yml`    | Per-step `if:`          | Same                                   |
| `adapter-live.yml`    | Per-step `if:`          | + GitHub Environment scoping           |
| `red-team.yml`        | Per-step `if:`          | Fork-PR guard + issues:write permission|
| `validate.yml`        | Job-level `if:`         | 18+ steps × 3 jobs — per-step = noise  |
| `benchmarks.yml`      | Job-level `if:` (conjoined with fork rule) | Single job |
| `release.yml`         | Job-level `if:`         | Tag-triggered                          |
| `smoke-install.yml`   | Job-level `if:`         | Single job                             |

Kill-switch does NOT disable pre-Sprint-11 invariants (governance, hook
unit tests). Those stay load-bearing.

## Fork-PR safety (§R9)

- **`pull_request_target` is forbidden** (PLAN-002 §8 finding #18) on
  untrusted code.
- Workflows consuming provider keys (`benchmarks.yml`, `adapter-live.yml`)
  guard with `github.event.pull_request.head.repo.full_name ==
  github.repository`. Forks skip visibly.

## Release-tag gates (PLAN-013 §0.2 + §0.3)

Two mechanical gates hardened in Phase 0 of PLAN-013 prevent the
release-chain anti-goals from being violated by any tag push.

### §0.2 — NPM publish double-gate

`npm-publish.yml` was originally `on: push: tags: v*` with a direct
`npm publish` step. Debate Round 1 consensus §C5 (CRITICAL, 2/5
agents — DevOps + Staff Backend) flagged that pushing `v1.4.0-rc.1`
would trigger a public NPM publish, violating anti-goal #3 ("NO NPM
publish during Sprint 13").

Two gates layered on top of the existing tag filter:

| Gate | Mechanism | Applies to |
|---|---|---|
| RC skip | Job-level `if: "!contains(github.ref, '-rc.')"` | `v*-rc.*` tags never run the publish job |
| Manual approval | `environment: production-npm` (configured in Settings → Environments with required reviewers) | `v*` GA tags run the job but pause for human approval before `npm publish` |

Operator flow when a real GA tag is pushed:
1. Tag landed, workflow queues `publish` job.
2. GitHub Environments blocks the job pending Owner review.
3. Owner reviews VERSION + npm/package.json + CHANGELOG one last time.
4. Owner approves → job resumes and runs `npm publish --provenance`.
5. Owner rejects → job cancels; no publish happens.

**Sprint 13 posture:** repo is private; `npm publish` will never be
approved. Gates are load-bearing for Sprint 17+ when public launch
decision lands. Zero `npm publish` is expected throughout PLAN-013.

### §0.3 — `release.yml` 24h RC hold enforcement

Debate Round 1 consensus §S3 HIGH (DevOps): "policy without mechanism
is hope." The RC hold (originally a 7-day calendar gate per ADR-014;
reduced to a 24h Codex re-pass window per ADR-103) is now enforced by a
step in `release.yml` that:

1. Skips check on RC tags (`v*-rc.*`).
2. On GA tags (`v1.x.y`), finds the most recent `v1.x.y-rc.*` tag via
   `git tag -l --sort=-creatordate`.
3. If no prior RC → fail (mandatory RC before GA).
4. Else compute delta; reject if <24h (86400s).

Step lives in the `release-gate` job between "Assert VERSION matches
tag" and "Assert CHANGELOG entry exists" — fails fast before any
heavier checks run. Uses `creatordate` (unified for lightweight +
annotated tags) and `fetch-depth: 0` (already set on checkout).

## SHA pinning

Every `uses:` is pinned to a full commit SHA:

- `actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd` (v6.0.2)
- `actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405` (v6.2.0)
- `actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (v7.0.1)

Tag-based pinning (`@v6.0.2`) is rejected as a silent supply-chain risk.

## Concurrency

- `cancel-in-progress: true` on PR-triggered workflows (validate,
  benchmarks, smoke-install).
- `cancel-in-progress: false` on cron-triggered workflows (chaos,
  otel-smoke, perf-profile, adapter-live, release) — a mid-run kill
  would leave provider/state indeterminate.

## Adding a new workflow — checklist

- [ ] Paths-filter `on.pull_request.paths` + `on.push.paths` unless
      genuinely always-on
- [ ] SHA-pin every `uses:`
- [ ] Explicit `permissions:` (`contents: read` default)
- [ ] Honour `CEO_SOTA_DISABLE` (job-level or per-step)
- [ ] Fork-PR rejection if consuming secrets
- [ ] Pick free cron slot + update the table above in the same PR
- [ ] Set `concurrency.group` with ref + cancel policy
- [ ] Set `timeout-minutes:` — no unbounded runs
- [ ] `actionlint` must pass (validate.yml catches this)

## References

- PLAN-012 §S6/§R4/§R8/§R9
- ADR-037 §3 — chaos kill-switch precedent
- ADR-040 §6 — live-adapter activation gate
- `.claude/skills/core/devops-ci-cd/SKILL.md`
