# Methodology disclaimer — value dashboard hours-saved estimate

**Hours-saved is an estimate, not a measured outcome.**

## Baseline assumptions (visible in every dashboard run)

1. `baseline_serial = "Opus serial 30s + 0.5min thought"` — counterfactual
   is solo-CEO running Opus serially, 30s execute + 30s think per op
   (60s/op). This is what we compare against.
2. `parallel_ceiling = 6` — framework dispatches sub-agents in batches
   of at most 6 (PLAN-083 §5 cap). Wallclock = `ceil(N/6) * per_op_seconds`.
3. `audit_overhead_pct = 5%` — audit emit + canonical guard + hook
   fan-out adds ~5% (3s on top of 60s = 63s/op with framework).

## Known biases (we measure what we can)

- **Sub-agent debug time NOT tracked.** Iterative Codex reviews, R1+R2
  rework, failed dispatches absorbed into framework wallclock but
  baseline gets no equivalent penalty. Biased upward in review-heavy plans.
- **Owner physical GPG time excluded** (PLAN-083 §17 scope, not dashboard).
- **Commits + ceremonies are best-effort** from audit log; git log +
  sentinel `.asc` files remain authoritative.
- **Pricing is upper-bound.** Anthropic + OpenAI public list prices,
  2026-05; volume discounts and prompt caching NOT applied.

## How to invalidate the claim (specific CTO tests)

1. **Time a representative dispatch.** Stopwatch one sub-agent end-to-end.
   If median exceeds 63s by >2x, raise `_FRAMEWORK_OVERHEAD_SECONDS_PER_OP`.
2. **Run the counterfactual.** Solo-CEO an equivalent task in Opus serial.
   If real baseline > 60s/op, raise `_BASELINE_SERIAL_SECONDS_PER_OP`.
3. **Audit dispatches.** `audit-query.py by-action agent_spawn` is the
   ground-truth dispatch counter; deltas indicate rotation-dedup bugs.

## Framing — why "ESTIMATE" not "actual"

Per Codex P1 review of PLAN-083: marketing-style claims fail AI-skeptic
CTO review. Every value-claim line is labeled `ESTIMATE` so it cannot
be mistaken for a measurement. Dashboard's job = make assumptions
visible; CTO's job = challenge them.
