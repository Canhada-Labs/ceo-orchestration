---
name: trading-execution
description: Trading execution architecture for a crypto trading platform. Covers CEX gateway design
  (OKX, ExchangeX, Binance, Bybit, Kalshi), order lifecycle management, Smart Order
  Routing (SOR), split optimization, position tracking, fill processing, market-making
  (Stoikov model), partial fill handling, rate limiting per venue, credential management
  (AES-256-GCM encrypted), and trading worker orchestration. Use when working on any
  code in src/trading/, src/execution/, src/market-making/, src/sor/, or any route
  that submits, cancels, or queries orders. Also use when debugging order failures,
  reviewing fill processing, implementing new venue gateways, or tuning SOR parameters.
  43 files, ~9.3K lines across 5 directories.
owner: Luna Park
secondary_owner: Viktor Petrov (VETO on all P&L-affecting logic)
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 2
risk_class: high
stack: [python, typescript]
context_budget_tokens: 1500
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 9}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 2}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: file-edit, glob: "**/trading/**"}
  - {event: file-edit, glob: "**/execution/**"}
  - {event: file-edit, glob: "**/sor/**"}
  - {event: help-me-invoked, regex: "(?i)smart.?order.?routing|sor|stoikov|market.?maker|fill.?process|order.?lifecycle"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/trading/**"
  - "**/execution/**"
  - "**/market-making/**"
  - "**/sor/**"
---

# Trading Execution

## Fail-Fast Rule

If an order cannot be validated (missing price, invalid size, unknown venue,
expired credentials), **reject immediately with structured error**. Never
send a malformed order to an exchange. Never guess parameters. Never retry
a rejected order without understanding why it was rejected.

## Architecture

```
Client → Trading Gateway (auth + validation)
  → SOR (venue selection + split optimization)
    → CEX Gateway (OKX | ExchangeX | Binance | Bybit | Kalshi)
      → Exchange API
        → Fill callback → Position tracker → P&L update
```

### Key Directories
- `src/trading/` (30 files) — Gateway manager, venue gateways, trading router
- `src/execution/` (8 files) — Order manager, fill processor, arb executor, risk engine
- `src/market-making/` (4 files) — Stoikov model, quote engine, inventory manager
- `src/sor/` (5 files) — Smart order router, depth aggregator, split optimizer

## Order Lifecycle State Machine

```
PENDING → SUBMITTED → PARTIALLY_FILLED → FILLED → SETTLED
                    → REJECTED (terminal)
                    → CANCELLED (terminal)
                    → EXPIRED (terminal)
```

### Invariants
1. Once FILLED or SETTLED, order cannot change state
2. PARTIALLY_FILLED must track cumulative filled qty
3. CANCELLED must attempt to cancel on exchange first
4. REJECTED must include exchange error code
5. State transitions must be logged with timestamp

## Smart Order Router (SOR)

### Decision Algorithm
```
For order of size Q across N venues:
1. Aggregate depth across all eligible venues
2. For each possible split:
   - Calculate slippage per venue (from depth)
   - Add fees per venue
   - Add latency cost per venue
3. Minimize: Σ(slippage_i + fee_i + latency_cost_i)
4. Subject to: max_per_venue, min_order_size, venue_status
```

### Venue Selection Criteria
- Venue must be READY (not STALE/DISABLED)
- Sufficient depth at target price level
- Rate limit budget available
- Credentials valid and not expired

## Market-Making (Stoikov Model)

### Parameters
| Parameter | Description | Default |
|-----------|-------------|---------|
| risk_aversion (γ) | Controls spread width | 0.1 |
| max_inventory | Position limit | Exchange-specific |
| time_horizon (T) | Quoting horizon | 300s |
| volatility (σ) | Price volatility estimate | From VWAP |

### Invariants
- Bid < mid < ask (always)
- Spread ≥ min_spread (exchange minimum)
- Inventory within [-max, +max]
- Quotes cancelled before position exceeds limits

## Critical Rules

1. **ALL price/size math uses Decimal.js-light** — Viktor VETO
2. **Credentials AES-256-GCM encrypted** — never plaintext in memory longer than needed
3. **Rate limits tracked per venue** — SOR considers remaining budget
4. **Partial fills must update position atomically** — no intermediate inconsistent state
5. **Trading worker runs in dedicated Fly.io machine** — not in main process
6. **WORKER_SECRET + HMAC auth** between main and trading worker
7. **Circuit breaker per venue** — trip on 3 consecutive failures
8. **All order submissions logged** — exchange, pair, side, price, size, timestamp
