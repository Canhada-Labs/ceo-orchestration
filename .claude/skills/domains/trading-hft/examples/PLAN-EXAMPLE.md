---
id: PLAN-EXAMPLE-trading-hft
title: Launch the "MeanReversion-EUR" strategy with full kill coverage
status: draft
created: 2026-04-13
owner: CEO
sprint: example
tags: [trading-hft, strategy-launch, example]
---

# PLAN-EXAMPLE — Launch MeanReversion-EUR strategy

> Example plan demonstrating how the trading-hft squad routes work
> through its four-VETO process. Not for execution. Used by adopters
> as a reference template when proposing a real strategy launch.

## 0. Thesis

Add a mean-reversion strategy on the EURUSD spot pair, running on the
existing FIX session to LMAX. Expected behavior: capture short-term
mean-reversion edge during low-volatility windows; flatten on
volatility spikes. Latency budget: well within current p99 (12 µs
strategy decision).

This plan exists to demonstrate the squad's launch process end-to-end.

## 1. Phases + owners

| Phase | Owner | Approver | Output |
|---|---|---|---|
| 1. Strategy build | Hiroshi Tanaka (Quant) | Diane Okafor | Backtest + slippage model |
| 2. Surveillance review | Eluned Pryce (Compliance) | self (VETO) | Red-team report |
| 3. Latency analysis | Marcelo Andrade (Latency Architect) | self (VETO) | Budget + histograms |
| 4. Kill-switch wire-up | Yara Bensoussan (Kill-Switch Operator) | self (VETO) | Drill report (paper) |
| 5. Production deploy | Diane Okafor (Head of Trading) | Owner (CEO) | 4 sign-offs + paper window |
| 6. 30-day monitoring | All four | Diane Okafor | Post-deployment review |

## 2. Phase 1 — Strategy build

**Owner:** Hiroshi Tanaka

- Implement `strategies/mean_reversion_eur.py` with deterministic
  backtest path. Use integer-tick prices (no floats).
- Validate against 6 months of L2 data from LMAX.
- Slippage analysis: walk-forward 1-month windows; report mean,
  median, 95th percentile. Compare to paper-trade slippage when
  available.
- Cite data window for every parameter (lookback, threshold, sizing).

**Acceptance:** Slippage match within 1 bps of paper-trade observation
(once paper window ships in Phase 5). Backtest determinism verified
(same data → same trades).

## 3. Phase 2 — Surveillance review

**Owner:** Eluned Pryce

- Layering / spoofing red-team: would surveillance flag the strategy's
  natural order pattern? Document expected pattern (size, frequency,
  cancel-to-fill ratio) and risk score.
- Best-execution evidence: confirm strategy doesn't produce orders
  that miss best-ex requirements (e.g. crossing the spread when not
  warranted).

**Acceptance:** Red-team document signed off + filed in
`compliance/strategy-reviews/`.

## 4. Phase 3 — Latency analysis

**Owner:** Marcelo Andrade

- Set p50/p99/p99.9 budgets for the new strategy hot path:
  - Tick-in → decision: 4 µs / 10 µs / 30 µs
  - Decision → wire: 3 µs / 7 µs / 22 µs
- Run 1-hour replay against historical market data; capture
  histograms.
- Verify NO new heap allocations (object pool for the order builder).
- Verify NO new syscalls (cached monotonic clock).
- Verify NO new contended locks (lock-free queue for the audit
  sidecar).

**Acceptance:** Histogram matches budget; perf-trace shows top 3 call
sites; before/after diff vs current baseline attached to PR.

## 5. Phase 4 — Kill-switch wire-up

**Owner:** Yara Bensoussan

- Wire `MeanReversion-EUR` into the per-strategy kill switch
  (`strategies.killable_set.add("MeanReversion-EUR")`).
- Verify cancel path is independent of order infra (uses separate
  cancel queue + sidecar audit).
- Drill the kill in paper:
  - Inject 10 simulated open orders.
  - Fire kill.
  - Verify all 10 cancelled within 100 ms (first cancel) and 500 ms
    (last cancel).
- Document termination SLA in `kill-switches/strategies.md`.

**Acceptance:** Drill report (paper) attached; SLA met; audit trail
captured with operator + timestamp + outcome.

## 6. Phase 5 — Production deploy

**Owner:** Diane Okafor

- Final go/no-go review across all four VETO sign-offs.
- Schedule 5-trading-day paper window before live.
- Production deployment ticket filed; ops on call.

**Acceptance:** Paper window completes with zero kill drills failing,
zero surveillance flags, latency within budget. Then live with
position cap at 10% of normal for first week.

## 7. Phase 6 — 30-day monitoring

**Owner:** All four (rotating)

- Daily dashboard check: latency p99 trend, kill drill cadence,
  surveillance taps capturing.
- Weekly review meeting: PnL vs. backtest, slippage vs. expectation,
  any anomalies.
- 30-day formal review: write up findings, raise position cap if
  metrics support it; otherwise extend the cap window.

**Acceptance:** 30-day review document filed; position cap adjustment
decision logged.

## 8. Open questions

1. Position-cap escalation policy: how fast can the cap grow without
   re-triggering Phase 5 sign-off?
2. Volatility-spike auto-flatten: should this strategy auto-disarm
   when realized vol > 2x historical, or stay on with smaller size?
3. Multi-venue: future expansion to additional ECNs requires Phase 4
   re-drill per new venue.

## 9. Rollback

- Per-strategy kill is the rollback. Operator fires `kill MeanReversion-EUR`,
  positions flatten within 2 s, audit trail captured. No code rollback
  required.
- If the strategy code introduces a latency regression on a shared
  hot path, the latency monitoring alert fires Phase 6 of
  `hft-latency-regression-triage`.
