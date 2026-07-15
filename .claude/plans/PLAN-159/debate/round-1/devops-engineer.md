---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer
generated_at: 2026-07-15T19:30:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The diagnosis is correct and evidence-backed. Verified against the code:
  `_pct_of_sorted` (`profile-opus-4-7.py:325`) uses `int((n-1)*p/100)`, so at
  N=20 the p95 index and p99 index both collapse to `18` (2nd-largest of 20)
  and at N=200 they separate to `189`/`197`. N=200 is the right root fix, and
  a plain-shell 2-attempt retry (no third-party action, both attempts logged)
  is the correct CI retry pattern for this repo's SHA-pin discipline.
- **One blocking mechanism flaw:** N=200 and the in-step retry share a *single*
  job timeout, while CI contention — the exact condition this plan fixes —
  multiplies N=200 wall-time. On their own numbers (76.6 s local at N=200,
  measurements §3; warm p95 ~65 ms local vs 300–700 ms contended, §2 = a 5–10×
  slowdown) a single contended attempt is ≈ 6–13 min. Two attempts cannot both
  run inside the proposed 10-min budget, so the retry provides **zero**
  protection in the sustained-contention case it was added for.
- The retry must be bounded in *wall-time*, not just attempt-count; attempt-1
  percentiles must stay visible (drift), and a concurrency guard is needed so
  N=200 runs don't stack on rapid pushes.

## Risks

- **Risk ID R-DO1 — job-timeout vs (N=200 × retry) collision**
  - Severity: **HIGH**
  - Description: The retry is in-step, so both attempts draw from one
    `timeout-minutes`. The profiler fires **1407 Python subprocesses per
    attempt** at N=200 (`201×3` unseeded + `402×2` seeded — the two
    `check_output_secrets` entries run a seed subprocess per `_run_once`,
    `profile-opus-4-7.py:524-536`). At the measured 5–10× contention slowdown
    a single attempt is ~6–13 min; attempt-1 alone can consume the whole 10-min
    job budget, leaving attempt-2 unable to start. Worse, this converts today's
    *fast* flake (a ~9 s N=20 step that fails in seconds and reruns cheaply)
    into a *slow* 10-min timeout-fail — a strictly more expensive failure mode
    on the contended tail, with the retry silently inert.
  - Mitigation: Bound each attempt independently. Wrap each profiler
    invocation inside the retry loop in a coreutils `timeout <sec>` (e.g.
    `timeout 360`), and set the job `timeout-minutes` to at least
    `2×cap + overhead` (~14–15 min for a 6-min cap). Then "bounded retry" is
    bounded in wall-time, and a genuinely hung/pathologically-contended
    attempt-1 is killed in time for attempt-2 to run in a fresh scheduling
    window (the retry's stated purpose per measurements §2 corollary).

- **Risk ID R-DO2 — retry masks slow drift (green-on-attempt-2)**
  - Severity: **MEDIUM**
  - Description: A check that passes on attempt-2 shows a GREEN status; the
    attempt-1 `::warning` is invisible in the check state. If the code slowly
    drifts toward the ceiling so attempt-1 begins breaching regularly while
    attempt-2 usually clears, the gate stays green and the eroding margin goes
    unobserved. The proposal frames the retry purely as anti-flake insurance
    and never considers this. My mantra applies inverted: a gate that quietly
    self-heals also quietly stops reporting.
  - Mitigation: Always emit the attempt-1 p95/p99 (per corpus entry) into
    `$GITHUB_STEP_SUMMARY` regardless of outcome, and count attempt-1-failure
    frequency over time. If attempt-1 failure rate climbs on unregressed code,
    that is the drift signal N=200 was supposed to remove — surface it, don't
    bury it under a green check.

- **Risk ID R-DO3 — set -euo pipefail + retry abort**
  - Severity: **LOW**
  - Description: The step runs under `set -euo pipefail` (`validate.yml:1205`).
    A naive `python3 ... ; retry` aborts the step on attempt-1's non-zero exit
    before the fallback runs; a `timeout`-killed attempt returns 124, also
    fatal under `set -e`.
  - Mitigation: Guard the tested command so `set -e` does not fire — use an
    `if ! timeout <sec> python3 ...; then` block that logs a `::warning::` and
    runs attempt-2, letting attempt-2's own exit status propagate as the step
    verdict.

- **Risk ID R-DO4 — stacked N=200 runs on rapid pushes / PR double-trigger**
  - Severity: **LOW**
  - Description: At N=20 (~9 s) overlapping runs are free; at N=200 (2–13 min)
    they are not. `on: push` + `on: pull_request` means a PR-branch push can
    trigger this job twice, and back-to-back pushes stack full N=200 runs. On a
    public repo the minutes are free, but each stacked run re-rolls the flake
    dice and lengthens the busy-runner window the plan is trying to escape.
  - Mitigation: Confirm a `concurrency` group with `cancel-in-progress: true`
    covers this job (I only read `validate.yml:1155-1254`; the top-level was
    not in scope). If absent, add one keyed on `github.ref` so a superseded
    push cancels its in-flight profiler run.

## Must-fix (blocking)

1. **Bound the retry in wall-time, and size the job timeout for two attempts
   (R-DO1).** As written (N=200 + in-step retry + `timeout-minutes: 10`), the
   retry cannot run under the sustained contention it exists to defend against,
   and a contended attempt-1 turns a fast flake into a slow timeout. Before
   Wave 1 implements the step, the design must specify: (a) a per-attempt
   `timeout <sec>` cap inside the retry loop, and (b) a job `timeout-minutes`
   sized at least `2×cap + checkout/setup/smoke/floor overhead`. Record the
   chosen cap and its basis in the Wave-1 ADR alongside the N choice. Without
   this, levers 1 and 2 compete for one budget instead of complementing each
   other.

## Nice-to-have (advisory)

1. **Always-log attempt-1 percentiles (R-DO2).** Cheap (`$GITHUB_STEP_SUMMARY`
   append) and it preserves the gate's drift-detection value through the
   retry.
2. **Consider whether N=200 alone suffices, dropping the retry.** N=200 makes
   p95 tolerate 10 outliers within a window (robust to bursts). The retry only
   adds value against *sustained* contention on attempt-1 — which is precisely
   the case R-DO1 shows is hardest to fit in the budget. If Wave 2's 3× green
   proof (including a busy-runner window) passes on N=200 *without* the retry
   ever firing, retire the retry to shrink the drift-masking surface (R-DO2)
   and the timeout budget. Let the data from the acceptance runs decide.
3. **The more surgical root fix is the percentile formula, not a bigger N.**
   The `int()` truncation is the actual defect; a nearest-rank `ceil` (or
   interpolated) percentile would give a stable, separated p95/p99 at a much
   smaller N (~50–100), keeping each attempt ~30–60 s so the retry is genuinely
   cheap and the per-push tax stays low. The proposal defers this for
   blast-radius reasons (it changes percentile semantics for `--floor` and
   `perf-profile.yml` too), which is defensible — but the trade-off is that
   N=200-on-every-push is the expensive way to paper over a one-line bug.
   Since `profile-opus-4-7.py` is already inside the Wave-1 sentinel touch set,
   fixing the formula there under the same ceremony is low marginal cost; weigh
   it explicitly rather than by default.

## Unseen by the original plan

1. **Contention multiplies N=200 wall-time and collides with the retry
   budget.** The plan bumps `timeout-minutes` 5→10 but never models that the
   same runner contention driving the flake also inflates a 76.6 s N=200 run
   by 5–10×. The timeout was sized for the *clean*-runner cost, not the
   contended one — the scenario the plan exists to survive. (Basis for R-DO1.)
2. **Step-level `timeout-minutes` / per-attempt `timeout` are never mentioned.**
   The plan reasons only about the job-level timeout. GitHub Actions supports
   step-level `timeout-minutes`, and coreutils `timeout` (present on
   `ubuntu-latest`) bounds each invocation — the missing mechanism that makes a
   retry actually bounded.
3. **The retry can silently erode drift detection over time (R-DO2).** The plan
   treats the retry as pure upside; the standard cost of any auto-retry — a
   green check hiding a real attempt-1 breach — is unaddressed.
4. **Runner choice is correctly constrained but not stated.** The root cause is
   the shared GitHub-hosted `ubuntu-latest` runner; a dedicated runner would
   eliminate the contention outright, but prior repo experience already forbids
   routing perf gates to the self-hosted `Ceo` runner (billing-window queued-
   eternal failures). N=200's statistical robustness is the right lever *given*
   that constraint — worth recording so a future reader doesn't "fix" this by
   moving the job to `Ceo`.

## What I would NOT change

1. **Plain-shell 2-attempt retry over a third-party retry action.** Correct.
   This repo SHA-pins `actions/checkout` and `actions/setup-python`
   (`validate.yml:1187,1191`); a third-party retry action would add a new
   pinned supply-chain surface for a loop bash does in three lines. Keep it
   in-house.
2. **Rejecting `CEO_SOTA_DISABLE=1` and `continue-on-error`.** Both are correct
   rejections. `CEO_SOTA_DISABLE=1` gates the whole job (`validate.yml:1179`) —
   a kill-switch, not a fix — and `continue-on-error` would silently demote a
   hard gate to advisory. Neither should be reconsidered.
3. **Ceilings unchanged (p95<120 / p99<160).** Agreed — N=200 local/clean p95
   sits at or below 98 ms (measurements §3), so lever 3 is correctly not
   exercised. Loosening the ceiling without data would trade away exactly the
   ≥2× regression detection the gate exists for.
4. **Accepting one bounded rerun for the bootstrapping commit (OQ2).** The
   fixing commit must pass the OLD gate; you cannot escape that without
   disabling the gate for that push (too broad). A documented single rerun (or
   landing in an off-peak window via the sentinel ceremony the Owner runs
   manually anyway) is the pragmatic, honest answer.
5. **Scoping the fix to this one step (OQ3).** Verified against measurements §5:
   `--floor` gates on p50 (contention-robust) with 4× margin, `perf-profile.yml`
   is advisory (`::notice`), `benchmarks.yml` has no latency percentile gate.
   Only this step carries the N=20 fragility. Do not expand scope.
