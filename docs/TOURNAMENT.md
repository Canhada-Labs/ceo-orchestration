# Tournament framework — adopter guide

> **What:** Empirical validation of the framework's multi-model dispatch
> policy (ADR-052). Runs the same task against Opus / Sonnet / Haiku,
> scores each with an LLM-judge panel, and emits a reproducible report.
>
> **Why:** Most multi-agent frameworks trust vendor claims. This one
> measures. The tournament is the framework's single empirical
> differentiator (per external audit PLAN-026 sub-T1).
>
> **When:** opt-in only. Default off; cost-bounded (\$40-120/run);
> monthly cadence or on-demand.

---

## TL;DR — 1-minute install

```bash
# 1. Set the two-factor kill-switch (both required for local mode)
export CEO_TOURNAMENT=1
mkdir -p ~/.ceo-orchestration/tournament
touch ~/.ceo-orchestration/tournament/.enabled
chmod 600 ~/.ceo-orchestration/tournament/.enabled

# 2. Set your Anthropic API key (tournament dispatches real API calls)
export ANTHROPIC_API_KEY=sk-ant-...

# 3. (Recommended) dry-run first — see projected cost before spending
cd <your-repo-root>
python3 -m tournament.runner --estimate-cost --fixtures-count 50 --judge-runs 3
# → shows projected $40-120 per full run

# 4. Actually run (Phase 5 wires live-dispatch glue; until then use CI)
# In CI: trigger .github/workflows/tournament.yml via GitHub UI or gh CLI
```

---

## Cost expectation (important)

Round 1 empirical projection from `ceo-cost.py` pricing table:

| Fixture count | Judge runs | Models | Projected USD |
|---:|---:|---:|---:|
| 50 | 3 | 3 (Opus/Sonnet/Haiku) | **\$40-\$120** typical; \$59 median |
| 20 | 3 | 3 | \$16-\$48 |
| 20 | 1 | 3 | \$7-\$20 |
| 10 | 1 | 3 | \$3-\$10 |

**Key insight:** judges dominate cost at 82% of total (judges are all
Opus 4.8 per VETO floor). Cutting `CEO_TOURNAMENT_JUDGE_RUNS` from 3→1
drops cost roughly 3×. Cutting fixture count helps linearly.

The default budget cap `CEO_TOURNAMENT_BUDGET_USD=75` covers the full
50-fixture × 3-model × 3-judge-run corpus. Raise for larger runs; lower
to force smaller runs.

Cost projection **always runs first**. If projection exceeds the cap,
the tournament aborts at startup — zero API calls, zero spend. This is
dual-gated by a per-task cumulative check at 1.5× projection during the
run, so even if projection is wrong the tournament cannot blow through
1.5× the cap silently.

---

## What gets measured

Five task-types × 10 fixtures each (50 fixtures baseline):

| Task type | What contestants are asked | Expected tier per ADR-052 |
|---|---|---|
| `security-review` | OWASP Top 10 detection in code snippets | Opus |
| `code-review` | idiomatic patterns + bugs + type-checker wisdom | Opus/Sonnet |
| `performance-triage` | hot-path identification + GC hints | Sonnet |
| `test-design` | edge cases + property tests + mutation surface | Sonnet |
| `docs-writing` | clarity + precision + honest limitations | Haiku |

For each `(fixture × model)` pair:
1. Dispatch contestant prompt to the model at `temperature=0`
2. Score in **strict mode** (regex/substring vs `acceptance_strict`)
3. Score in **llm-judge mode** (Opus judge with envelope hardening +
   multi-run median, default 3 runs)
4. Record verdict + tokens + cost + wall-clock

The aggregate report includes per-`(task-type × model)` win-rate +
ADR-052 validation signals.

---

## Kill switches (two-factor by design)

| Env var | File | Effect |
|---|---|---|
| `CEO_TOURNAMENT=1` | + `~/.ceo-orchestration/tournament/.enabled` (0600) | enabled locally |
| `CEO_TOURNAMENT=0` (default) | — | disabled unconditionally |
| `CEO_TOURNAMENT_CI=1` | — (CI replaces sentinel) | CI mode; `tournament.yml` workflow uses this |
| `CEO_SOTA_DISABLE=1` | — | framework master-off (overrides everything) |

You can delete the sentinel file at any moment to disable tournament
even with the env var set — both factors required simultaneously. This
prevents accidental enable inside automation that may have inherited
the env var.

---

## Budget configuration

Tune via environment (CI: set as repo secrets):

| Variable | Default | Effect |
|---|---|---|
| `CEO_TOURNAMENT_BUDGET_USD` | `75` | hard cap per run |
| `CEO_TOURNAMENT_CONCURRENCY` | `10` | semaphore for Anthropic calls (max 50) |
| `CEO_TOURNAMENT_CALL_TIMEOUT_S` | `60` | per-call timeout |
| `CEO_TOURNAMENT_JUDGE_RUNS` | `3` | multi-run median count |

**Rate-limit guidance:** At Anthropic Tier-2 (1000 RPM, 100K tok/min),
concurrency 20 is safe. Tier-1 (60 RPM, 40K tok/min): drop to 8.

---

## Interpreting the report

Each tournament emits two artifacts:

- **`benchmarks/tournament-<run_id>.jsonl`** — strict-schema JSONL per
  `SPEC/v1/tournament-report.schema.md`. Hashes-only, no raw prompt/
  output/rationale content. Git-tracked for historical comparison.
- **`benchmarks/tournament-<run_id>.jsonl.hmac`** — HMAC chain anchor
  preventing retroactive forgery (ADR-055 precedent).

The aggregate record includes `adr052_validation` with one signal per
task-type:

| Signal | Meaning | What to do |
|---|---|---|
| `opus_confirmed` | Opus > Sonnet by ≥15pp on VETO task | ADR-052 holds |
| `opus_marginal` | Opus > Sonnet 5-15pp | directional signal only |
| `opus_mid_surprise` | Opus - Sonnet < 5pp | Owner review; may warrant amendment proposal |
| `parity_confirmed` | Opus ≈ Sonnet on performance task | ADR-052 holds |
| `sonnet_underperforms` | Opus - Sonnet > 15pp on mid-tier | Owner review |
| `haiku_sufficient` | Haiku pass-rate ≥ 0.7 on low-risk | cost-optimal tier confirmed |
| `haiku_insufficient` | Haiku pass-rate < 0.7 | consider tier uplift |

**Advisory only.** Signals NEVER auto-revoke the VETO floor. ADR-052
amendment requires Owner signature.

### Statistical power caveat

Default corpus (10 fixtures per task-type) gives standard error ≈ 0.16
at p=0.5. Differences < 15pp are sampling noise. Scale to ≥30 fixtures
per task-type for 0.05 significance at α=0.05.

---

## Verification

Before trusting a tournament report for governance decisions, verify
the HMAC anchor:

```bash
# Phase 5 wires audit-verify-chain.py --tournament flag
python3 .claude/scripts/audit-verify-chain.py \
  --tournament benchmarks/tournament-<run_id>.jsonl
```

Mismatched HMAC implies post-emission tampering. Do not cite that
report's signals in an ADR-052 amendment proposal.

---

## CI integration

`.github/workflows/tournament.yml` ships with:

- Manual trigger (`workflow_dispatch`) + scheduled monthly run
  (04:00 UTC 1st of month)
- 75-minute job timeout (5× headroom on Tier-2 projected wall-clock)
- `TOURNAMENT_BUDGET_USD` secret override (default \$75)
- Fork-PR guard — fork PRs cannot trigger live dispatch
- Offline pytest smoke always runs (FakeLLMDispatcher, no API key needed)
- Live dispatch gated on `ANTHROPIC_API_KEY` secret presence + not-fork
- Projection artifact uploaded (90-day retention)

**NEVER** triggered on PR (cost discipline). `pull_request_target` is
explicitly forbidden (code-injection vector in forked workflows).

---

## Common runbook

### Q: Tournament aborts at startup with "projected > budget"

The default \$75 cap covers 50-fixture × 3-model × 3-judge-run. If
you've raised fixture count or judge runs past defaults, either:

1. Lower `--fixtures-count` or `--judge-runs`
2. Raise `CEO_TOURNAMENT_BUDGET_USD` (requires Owner signature for CI
   via repo secret edit)

### Q: Fixture rejected by `check_fixture.py`

Your fixture tripped one of: schema hard caps (`max_tokens`/prompt/
`acceptance_llm_judge` bounds), unicode injection scan (bidi/zero-width/
tag chars/homoglyph), LLM01 prompt-injection pattern, or secret-shape
regex (JWT/API-key). The failing fixture + family are printed to stderr.

### Q: I get `haiku_insufficient` signal but I don't think Haiku is actually worse

Scale your docs-writing fixture count to 30+ and re-run. At n=10,
standard error is 0.16; a one-fixture flip changes win-rate by 10pp.

### Q: My report.hmac verifier mismatches

Either (a) the report was tampered post-emission — do NOT cite in
governance decisions; or (b) the framework audit key was rotated
between emission and verification — check `docs/rotation-log.md` for
the rotation timestamp.

### Q: Tournament takes 60+ minutes in CI

Concurrency is at default 10. At Tier-2 (1000 RPM) you can raise to 20.
At Tier-1, the 60-minute cost is the rate-limit floor; split fixtures
across multiple runs (`--fixtures-count 25` twice) to stay within
timeout.

---

## Related

- **ADR-063** — tournament framework decision record
- **ADR-052** — tier dispatch policy under validation
- **ADR-055** — HMAC audit chain (report anchor pattern)
- **SPEC/v1/tournament-report.schema.md** — strict report schema
- **PLAN-032** — implementation plan + Round 1 debate transcript
- **`.claude/scripts/tournament/`** — code + fixtures
