---
name: prediction-markets
description: Prediction market integration and trading strategy for a crypto trading platform. Covers
  Polymarket API (CLOB, events, markets, orderbook), Kalshi integration, AutoTrader
  strategy engine (V2 insurance model, multi-timeframe, category discovery), event
  mapping (real-world event to market matching), edge detection (Kelly criterion),
  multi-timeframe portfolio management, and prediction arb (cross-venue price
  discrepancies). Use when working on any prediction-market module (market discovery,
  event mapping, AutoTrader, Polymarket/Kalshi integration, edge detection), on AutoTrader
  configuration, event discovery, or prediction market analysis. Also use when the user mentions "Polymarket",
  "Kalshi", "prediction market", "AutoTrader", "event mapping", or "prediction arb".
owner: Luna Park
secondary_owner: Viktor Petrov (VETO on edge/Kelly calculations)
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 5
risk_class: medium
stack: [python, typescript]
context_budget_tokens: 1100
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 9}
  engine: {active: true, priority: 6}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)polymarket|kalshi|prediction.?market|autotrader|kelly|edge.?detection"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/prediction-markets/**"
  - "**/polymarket/**"
  - "**/kalshi/**"
  - "**/autotrader/**"
---

# Prediction Markets

## Fail-Fast Rule

If a prediction market's status is not ACTIVE, **do not trade it**. If edge
calculation returns negative expected value, **do not place the bet**. If
event mapping confidence is below threshold, **do not auto-map**.

## Architecture

```
Market Discovery (periodic scan)
  → Event Mapper (match to real-world events)
    → Edge Calculator (Kelly criterion)
      → AutoTrader (strategy execution)
        → Polymarket CLOB / Kalshi API
          → Fill tracking → Portfolio management
```

### Key modules (archetype)

- **Collector** — market discovery and data collection (periodic scan of venues for new/closed markets)
- **Store** — in-memory market state (typical caps: ~15K books, ~2K events before flush)
- **Polymarket trading adapter** — Polymarket CLOB order submission via signed EIP-712 messages
- **AutoTrader (strategy engine)** — V2 insurance model, multi-timeframe, category discovery
- **AutoTrader manager** — credential loading, lifecycle, per-user isolation
- **Event mapper** — real-world event → market matching with confidence threshold
- **Prediction arb detector** — cross-venue price-discrepancy detection (Polymarket vs Kalshi)

## Polymarket Specifics

### API Patterns
- REST: markets, events, orderbook snapshots
- CLOB: order placement via signed EIP-712 messages
- Auth: Ethereum wallet signature (private key required)
- Rate limits: 100 req/min (REST), 10 orders/sec (CLOB)

### Market Lifecycle
```
PROPOSED → ACTIVE → RESOLVED (YES/NO/INVALID)
```
- Only trade ACTIVE markets
- Resolved markets: settle positions, cannot place new orders
- INVALID: full refund, no P&L impact

### Multi-Timeframe Discovery
- Timeframes: 5m, 15m, 1h, 4h (via POLYMARKET_TIMEFRAMES env)
- Category discovery: crypto, politics, sports, etc. (5min timer)
- Auto-classification on upsert: `classifyTimeframe`, `classifyCategory`, `extractAsset`

## AutoTrader V2

### Strategies
| Strategy | Description | Status |
|----------|-------------|--------|
| Insurance Model | Buy cheap protection (<$0.10) on tail events | ACTIVE |
| Crypto Arb | Arb prediction vs spot price | PLANNED (V3) |
| Multi-Timeframe | Portfolio across timeframes | PLANNED (V3) |

### Edge Detection (Kelly Criterion)
```
edge = (p_estimated - p_market) / (1 - p_market)
kelly_fraction = edge / odds
position_size = kelly_fraction * bankroll * fractional_kelly
```

### Rules
1. ALL edge/Kelly math uses Decimal.js — Viktor VETO
2. fractional_kelly ≤ 0.25 (never full Kelly)
3. Max position per market: configurable
4. Stop loss: exit if market moves > 2x against position
5. Never trade markets expiring in < 1 hour (low liquidity)

## Event Mapping

### Problem
Match real-world events to prediction markets automatically.
Example: "BTC price > $100K by June 2026" → find Polymarket market

### Algorithm
- Levenshtein similarity (MIN_SIMILARITY 0.80)
- MAX_DISCOVERIES_PER_CYCLE = 20 (prevent main thread flood)
- Deduplication to prevent remapping known events
- Manual override: admin can force-map events

### Pitfalls
- O(500×2000) Levenshtein + HTTP POSTs can crash the server
- Mitigations: similarity threshold, discovery cap, dedup
- Event-mapper runs on timer, NOT synchronous

## Prediction Arb

### Cross-Venue Price Discrepancies
- Same event on Polymarket vs Kalshi → price differs
- Arb if: buy_price_A + buy_complement_B < 1.00
- Must account for: fees, slippage, settlement time, counterparty risk
- Pre-gate: scan threshold 0.92 (not 0.95 — too aggressive)

## Known Pitfalls

- **Event-mapper floods main thread:** O(500×2000) Levenshtein combined with hundreds of HTTP POSTs can crash a Node server within minutes. Fix: MIN_SIMILARITY 0.80, MAX_DISCOVERIES_PER_CYCLE=20, dedup.
- **Auto-trader loadCredentials reading plaintext columns:** If credentials are stored encrypted (e.g. AES-256-GCM in an `api_key_enc` column), the plaintext `api_key` column will be empty. Always delegate to the dedicated fetch helper, never read the plaintext column directly.
- **Polymarket store limits:** MAX_BOOKS=15K, max_events=2K, WS subs=500. Exceeding causes silent drops.
