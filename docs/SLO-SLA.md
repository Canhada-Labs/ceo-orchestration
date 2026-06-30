# Service-Level Objectives (Internal SLOs) and SLA Posture

> **Honest framing.** This is a one-Owner pre-adopter framework. We
> publish **internal SLOs** the framework dogfoods against, not
> contractual SLAs. Adopters who need a contractual response time
> need to talk to the Owner about a formal support agreement; none
> exists today.

## Why an SLO doc at all?

Two reasons to commit numbers to paper, even pre-adopter:

1. **Calibration.** A target you measure against is a target you
   can improve. The numbers below are what the framework currently
   delivers in production-equivalent dogfood and what we will defend
   against regression in CI.
2. **Adopter transparency.** A CTO evaluating the framework deserves
   to know "spawn governance adds ~25ms p99" instead of guessing.
   The numbers are the contract — if we miss them, that's a bug.

## The SLO matrix

| Metric | SLO | Source / measurement | Where reported |
|--------|-----|------------------------|------------------|
| **Hook subprocess overhead** | p50 ≤ 25 ms; p99 ≤ 30 ms | `audit_log.py::hook_duration_ms` field per spawn (audit-log SPEC §required fields per agent_spawn) | `python3 .claude/scripts/audit-query.py spawn-stats --since 30d` |
| **Subprocess startup floor** | p50 ≤ 25 ms; p99 ≤ 28 ms | `python3 .claude/scripts/profile-opus-4-7.py --floor` (Session 32 baseline) | `docs/opus-4-7-baseline.md` |
| **Audit-log write latency** | p50 ≤ 2 ms; p99 ≤ 5 ms | embedded in `hook_duration_ms` for PostToolUse | derived |
| **Governance gate latency** (validate-governance.sh) | ≤ 30 s end-to-end | wall-clock | `validate.yml` CI step duration |
| **CI pipeline end-to-end** | ≤ 10 min p95 | GitHub Actions step durations | `gh run list --workflow validate.yml` |
| **Spawn governance availability** (block-when-required) | ≥ 99.9% — never bypass on infra error | `veto_triggered` event count vs. expected blocks | `audit-query.py vetoes --since 30d` |
| **Hook fail-open rate** | ≤ 1% spawn count | `audit-log.errors` line count / total spawn count | `wc -l ~/.claude/projects/<slug>/audit-log.errors` |
| **Skill-by-reference hash match** | 100% — no TOCTOU drift | `check_skill_reference_read.py` `reference_postread_mismatch` count | `audit-query.py raw --action veto_triggered --since 30d` |
| **Mutation kill rate** (formal verification) | 100% on TLA+ corpus | `formal-verify.yml` workflow result | weekly Mon 16:00 UTC |
| **Prompt-injection scan precision** | ≥ 95% on red-team corpus | `red-team.yml` State 1 PR-enforcing | every PR |
| **Test coverage** | ≥ 78% line (post-PLAN-019 baseline) | `coverage.yml` hard fail under threshold | every PR |

## Error budget

We allow **1% hook fail-open** for genuinely infrastructural reasons
(missing files, parse errors, transient OS errors). The fail-open is
**always advisory** — it never bypasses governance gates that would
have blocked an action. Specifically:

| Failure mode | Behavior |
|--------------|----------|
| Hook payload malformed JSON | `audit_log.py` writes breadcrumb to `audit-log.errors`; PreToolUse decisions default `allow` (fail-open per ADR-002 §Hook policy) |
| Audit log file unwritable | Same: breadcrumb + allow; investigation triggered when `audit-log.errors` grows |
| Hook process killed by OS | Claude Code treats as timeout; logs to `audit-log.errors` |
| Skill SKILL.md unreadable post-spawn (reference mode) | `check_skill_reference_read.py` emits `veto_triggered: reference_postread_mismatch`; spawn output discarded |

**What the 1% does NOT cover:**

- Deliberately bypassing a gate (use `CEO_KERNEL_OVERRIDE` —
  audit-logged, Owner-only)
- A bug that lets a hook return `decision: allow` when it should
  block (treated as SEV-1 per `SECURITY.md`)
- `CEO_SOTA_DISABLE=1` or other kill switches that disable optional
  features (these are documented disables, not failures)

If `audit-log.errors` line count exceeds 1% of spawn count over a
7-day window, that is a defect — file an issue.

## SLA posture (external commitments)

**There is no external SLA today.** The framework is pre-adopter; no
paid support tier exists. What we DO commit:

| Commitment | Status |
|------------|--------|
| Security vulnerability response per `SECURITY.md` (48h ack / 7d initial / 14-30d fix) | ✅ Best-effort, Owner-managed |
| Active support window per `SUPPORT.md` (current MINOR + previous MINOR for 6 months) | ✅ Pinky-promise; rooted in `release.yml` 24h RC hold (ADR-103) |
| Audit-log additivity within v1 SPEC (no field removal/rename) | ✅ Mechanically enforced via `check-audit-read-api-stable.py` |
| Stdlib-only runtime (no third-party deps for hooks) | ✅ Mechanically enforced via `check-stdlib-deps.py`-equivalent in `validate.yml` |
| Native subagent canonical-5 model field present | ✅ Mechanically enforced via `validate-governance.sh` lint |
| 24h RC re-pass hold before any GA tag (ADR-103) | ✅ Mechanically enforced via `release.yml` (24h creator-date delta between the RC and GA tag) |

Adopters needing contractual SLAs (e.g. "P1 incident response ≤ 1h
24/7") should contact the Owner about a formal support agreement.
None exists today; the surface area for offering one isn't ready.

## Measurement methodology

### How we measure hook overhead

`audit_log.py` writes `hook_duration_ms` per `agent_spawn` event
(per `SPEC/v1/audit-log.schema.md` §Required fields). Aggregate via:

```bash
python3 .claude/scripts/audit-query.py spawn-stats --since 30d
```

The output includes p50 / p99 by skill + by subagent_type. Track
the rolling 30d window. Regressions surface when the 30d delta
exceeds 10% from baseline.

### How we measure CI duration

```bash
gh run list --workflow validate.yml --limit 50 --json conclusion,createdAt,updatedAt | \
  jq '[.[] | select(.conclusion == "success") | (((.updatedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)))] | sort | .[((length * 0.95) | floor)]'
```

p95 over the last 50 successful runs. Regressions trigger
investigation; the budget is fixed at 10 minutes because longer
feedback loops degrade developer flow.

### How we measure availability

"Availability" for the governance hooks means: when a spawn SHOULD
have been blocked, was it blocked? Measured indirectly via:

- `audit-log.errors` line count (accidents)
- `veto_triggered` events (intentional blocks)
- Test suite mutation kill rate (formal proof of kill capability on
  conformance corpus)

Direct availability measurement requires synthetic adversarial
spawns; the red-team corpus + `red-team.yml` State 1 workflow
exercises this on every PR.

## How SLOs are reviewed

| Review | Cadence | Output |
|--------|---------|--------|
| **Sprint retro** | per-sprint | "Did we hit hook overhead p99 ≤ 30 ms last sprint?" |
| **Quarterly SLO review** | quarterly | `docs/metrics-reports/Q<N>-<year>.md` summary; updates this doc if targets shifted |
| **Pre-release** | per RC tag | `release.yml` validates SLO snapshot; blocks tag if regressed > 20% |
| **Post-incident** | per SEV-1/SEV-2 | SLO impact section in incident post-mortem; tighten if needed |

## Honest limitations

1. **Single dogfood adopter.** All measurements come from the
   Owner's daily usage + CI on this repo. We have no third-party
   adopter telemetry yet (no opt-in phone-home; see `SUPPORT.md`).
   Sprint 15 deploys to a real adopter (adopter-1) and starts
   collecting external data points.
2. **No 24/7 monitoring.** The Owner is one person on one timezone.
   "Availability" of human response is bursty, not continuous.
3. **No formal SLA contract.** We have not signed any. We do not
   intend to without a paid support agreement structure (out of
   scope for v1).
4. **Measurements are point-in-time.** We do not maintain a
   continuous SLO dashboard yet. Adopters who need one wire it via
   their own observability stack reading the audit log.
5. **Some SLO components rely on advisory CI** (e.g. `formal-verify.yml`
   is Mon 16:00 UTC weekly, not per-PR). The advisory cadence is
   intentional — full TLC runs are too slow for PR latency budget.

## Where adopters get telemetry

The audit log at `~/.claude/projects/<slug>/audit-log.jsonl` is the
single source of truth for SLO measurement. Adopter-side automation:

```bash
# Daily: snapshot the log + run health check
0 3 * * * /bin/bash -c 'bash .claude/scripts/ceo-backup.sh && \
  python3 .claude/scripts/ceo-health.py --quiet || \
  curl -X POST <your-pager-webhook>'

# Weekly: export rollup
0 8 * * 1 python3 .claude/scripts/audit-query.py spawn-stats \
  --since 7d --json > /tmp/ceo-weekly-stats.json
```

Pipe these into your existing observability platform. The framework
does not ship a dashboard; you wire one when you need one.

## What changes when an adopter signs a paid support agreement

If/when paid support exists:

- **External SLAs** documented per agreement (response time, RTO,
  RPO targets stricter than the internal best-effort defaults)
- **24/7 on-call rotation** (currently zero rotations)
- **Customer-named escalation paths** (currently single-Owner
  funnel)
- **Adopter telemetry backchannel** (opt-in; never automatic — see
  `SUPPORT.md` §Telemetry)
- **Formal SLO reports** quarterly / monthly to the customer

None of this exists in v1.6. This section is here as a north star,
not a current promise.

## References

- `docs/opus-4-7-baseline.md` — subprocess startup floor measurement
  (Session 32)
- `SPEC/v1/audit-log.schema.md` — `hook_duration_ms` field
  definition
- `SECURITY.md` — vulnerability response SLA (Owner best-effort)
- `SUPPORT.md` — what's supported, by version
- `docs/INCIDENT-RESPONSE.md` — incident escalation tiers
- `.github/workflows/validate.yml` — CI gates that backstop SLO claims
- `.github/workflows/release.yml` — release-gate consistency check
  (per ADR-049)
- `bash .claude/scripts/audit-query.py spawn-stats` — primary SLO
  measurement entry point

Last reviewed: 2026-04-18 (Session 33 / PLAN-022 Phase 4).
