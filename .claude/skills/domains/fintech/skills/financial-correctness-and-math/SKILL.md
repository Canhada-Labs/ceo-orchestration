---
name: financial-correctness-and-math
description: Ensuring mathematical correctness and determinism in financial systems.
  Includes VWAP, cumulative depth, slippage modeling, precision handling,
  decimal arithmetic, invariants validation, and audit-friendly calculations.
  Use when reviewing or writing any code that affects prices, depth, volumes,
  PnL, arbitrage signals, or execution logic. Also use when designing schemas
  or types for financial data, validating orderbook invariants, or implementing
  any calculation where precision errors could cause incorrect trading decisions.
owner: Dr. Viktor Petrov
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 2
risk_class: high
stack: [python]
context_budget_tokens: 1400
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 7}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)vwap|slippage|pnl|decimal|precision|arbitrage|orderbook.?invariant"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/pricing/**"
  - "**/pnl/**"
  - "**/orderbook/**"
  - "**/depth/**"
  - "**/calculations/**"
---

# Financial Correctness and Math

## Fail-Fast Rule

If any mandatory invariant, validation, or precondition fails, **stop and
return a structured failure**. Never guess, infer, smooth, approximate,
or "fix" financial or market data. Never infer missing exchange behavior,
precision, limits, or semantics. Missing information must result in
rejection, not approximation.

## Cardinal Rule

Never use floating-point arithmetic for financial values. Every price,
quantity, volume, depth, and derived value (VWAP, slippage, PnL) must
use decimal arithmetic with explicit precision control.

NOTE: It is common for the trading STRATEGY layer (market-maker, taker-arb, basis-trader, position-manager) to drift toward float arithmetic while the EXECUTION layer stays on a decimal library. Audit both layers. Any float arithmetic on financial values in either layer is a defect pending migration.

## Computation Layers

Financial logic must flow through three layers in strict order.
Never skip or mix layers.

### Layer 1: Computation (Pure Math)

Only math. No decisions. No recommendations. No side effects.
Inputs must already be validated before reaching this layer.

### Layer 2: Validation (Invariants)

Check all invariants and preconditions on the computation result.
If any check fails, return structured failure — do not proceed.

### Layer 3: Decision (Only If Layers 1+2 Pass)

Business logic, signals, and recommendations exist only here.
If validation failed, this layer never executes.

## Decimal Arithmetic

### Language-Specific Patterns

**TypeScript/Node.js**: Use `decimal.js-light`.

```typescript
// CORRECT
import Decimal from 'decimal.js-light';
const price = new Decimal('50123.45');
const qty = new Decimal('0.00123');
const notional = price.mul(qty);

// WRONG — silent precision loss
const price = 50123.45;
const qty = 0.00123;
const notional = price * qty;
```

**Python**: Use `decimal.Decimal` with explicit context.

```python
from decimal import Decimal, ROUND_DOWN
price = Decimal('50123.45')
qty = Decimal('0.00123')
notional = price * qty
```

### Precision Rules

- Store prices and quantities as **strings** in JSON, databases, and API
  responses. Parse to Decimal only at computation boundaries.
- Never convert Decimal → float → Decimal. This round-trip loses precision.
- When serializing results, use `toFixed()` or equivalent with explicit
  decimal places matching the asset's tick size.
- Each exchange and pair has specific precision constraints (tick size for
  price, step size for quantity). Validate against these before submission.

### Rounding

- **Prices**: Round toward the book (bids round down, asks round up) unless
  the exchange specifies otherwise.
- **Quantities**: Always truncate (round down). Never round up a quantity —
  it can exceed available balance.
- **Use `ROUND_DOWN` / `ROUND_FLOOR`** as the default rounding mode.
- Make rounding mode explicit in every operation. Never rely on library defaults.

### Precision Provenance

Every final numeric result must carry provenance for audit and debug:

```typescript
interface PreciseResult {
  value: Decimal;
  precision: number;         // decimal places
  roundingMode: string;      // e.g. 'ROUND_DOWN'
  sourceTickSize?: Decimal;  // exchange tick/step size used
  sourceExchange?: string;
}
```

When reviewing code, reject any calculation output that does not make
its precision and rounding mode traceable.

## No Silent Nulls

Returning `null`, `undefined`, `0`, or empty results as a financial value
is **forbidden** unless explicitly justified and flagged with a reason code.

```typescript
// WRONG
function getVWAP(levels: PriceLevel[]): Decimal | null {
  if (levels.length === 0) return null; // silent failure
}

// CORRECT
function getVWAP(levels: PriceLevel[]): VWAPResult {
  if (levels.length === 0) {
    return { state: 'INSUFFICIENT_DATA', reason: 'empty_levels', value: null };
  }
  // ... compute ...
  return { state: 'OK', value: vwap, precision: 8, roundingMode: 'ROUND_DOWN' };
}
```

A zero spread, zero VWAP, or zero depth must always be accompanied by
an explicit justification — never accepted as a default.

## Core Financial Formulas

### VWAP (Volume-Weighted Average Price)

```
VWAP = Σ(price_i × quantity_i) / Σ(quantity_i)
```

Invariants:
- Accumulate numerator and denominator separately as Decimals.
- Never compute VWAP incrementally by averaging averages.
- If total quantity is zero, return `INSUFFICIENT_DATA` — never divide by zero.
- VWAP across exchanges must only combine books with the **same quote currency**.

### Cumulative Depth

```
cumulative_depth[i] = Σ(quantity[0..i])
cumulative_notional[i] = Σ(price[j] × quantity[j] for j in 0..i)
```

Invariants:
- `cumulative_depth` must be monotonically non-decreasing.
- `cumulative_depth[last] == total_depth` — verify explicitly.
- If depth levels are aggregated from multiple exchanges, each level must
  carry provenance (exchange + pair) for audit.

### Slippage Modeling

```
slippage = (execution_price - mid_price) / mid_price
execution_price = cumulative_notional_at_fill / fill_quantity
```

- Always compute against the **actual book** at the moment of estimation.
- Stale book data must be flagged — never compute slippage on stale books.
- On empty or thin books, return `INSUFFICIENT_LIQUIDITY` — not a number.

### Spread

```
spread_absolute = best_ask - best_bid
spread_bps = (spread_absolute / mid_price) × 10000
mid_price = (best_ask + best_bid) / 2
```

Invariants:
- `best_ask > best_bid` — if violated, the book is crossed. Mark INVALID.
  Do NOT use for any trading decision.
- Spread must be non-negative. A negative spread is a data integrity issue.

## Orderbook Invariants

Enforce at every layer (collector, cache, API):

1. **Bid/ask ordering**: Bids descending, asks ascending.
2. **No crossed books**: `best_ask > best_bid`. Crossed = always a bug.
3. **No duplicate price levels**: Each price at most once per side.
4. **No zero/negative quantities**: Every level has `quantity > 0`.
5. **Quote currency isolation**: Consolidated book for X/Y only contains
   data where quote == Y. Never merge X/Y with X/Z.
6. **No synthetic routes**: Depth must represent directly executable orders.

### Validation Pattern

```typescript
function validateBook(book: OrderbookSnapshot): ValidationResult {
  const errors: string[] = [];

  for (let i = 1; i < book.bids.length; i++) {
    if (book.bids[i].price.gte(book.bids[i - 1].price))
      errors.push(`Bids not descending at index ${i}`);
  }
  for (let i = 1; i < book.asks.length; i++) {
    if (book.asks[i].price.lte(book.asks[i - 1].price))
      errors.push(`Asks not ascending at index ${i}`);
  }

  if (book.bids.length > 0 && book.asks.length > 0) {
    if (book.bids[0].price.gte(book.asks[0].price))
      errors.push('Crossed book detected');
  }

  for (const level of [...book.bids, ...book.asks]) {
    if (level.quantity.lte(0))
      errors.push(`Zero/negative quantity at price ${level.price}`);
  }

  return { valid: errors.length === 0, errors };
}
```

## Pair-Strict Correctness

### Canonical Pair Type

```typescript
type CanonicalPair = {
  base: string;    // uppercase: "BTC"
  quote: string;   // uppercase: "USDT"
  symbol: string;  // canonical: "BTC/USDT"
};
```

Rules:
- Normalize at the ingestion boundary. All downstream receives `CanonicalPair`.
- `BTC/USDT ≠ USDT/BTC` — never auto-flip.
- Cache keys include full canonical symbol: `"BTC/USDT:binance"`.
- Add `quoteCurrency` as redundant field on events for defense in depth.
- Never do helpful aggregation across currencies — no FX conversion or
  synthetic triangulation inside consolidated books.

### Consolidation Rules

- Only merge books with **identical** `CanonicalPair`.
- Verify quote currency equality with explicit check before merge.
- On mismatch: log, metric, **reject** — never silently combine.

## Testing Strategies

### Unit Tests (Mandatory)

- Pair normalization: case, format variants, invalid input rejection.
- Decimal operations: precision preserved through calculation chains.
- VWAP: known inputs → hand-computed expected results.
- Rounding: truncation at boundary values.
- No-silent-null: empty input → structured failure, not null/zero.

### Property-Based Tests (Recommended)

```typescript
// consolidated book never mixes quote currencies
fc.assert(fc.property(
  fc.array(arbOrderbookSnapshot(), { minLength: 1, maxLength: 20 }),
  (snapshots) => {
    const consolidated = buildConsolidated(snapshots);
    for (const [pair, book] of consolidated) {
      const quotes = new Set(book.sources.map(s => s.quoteCurrency));
      return quotes.size <= 1;
    }
  }
));

// cumulative depth is monotonically non-decreasing
fc.assert(fc.property(arbOrderbook(), (book) => {
  const depths = computeCumulativeDepth(book.bids);
  for (let i = 1; i < depths.length; i++) {
    if (depths[i].lt(depths[i - 1])) return false;
  }
  return true;
}));
```

### Integration Tests

- Inject mismatched quote currency → verify rejection.
- Inject crossed book → verify INVALID state + alert.
- Empty levels → verify INSUFFICIENT_DATA, never null/zero.

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `parseFloat(price)` | Silent precision loss | `new Decimal(price)` |
| `Math.round(qty * 100) / 100` | Float rounding artifacts | `qty.toDecimalPlaces(2, ROUND_DOWN)` |
| `vwap = prices.reduce(avg)` | Average of averages ≠ VWAP | Accumulate Σ(p×q) and Σ(q) separately |
| Storing prices as `NUMBER` in DB | Float storage | Use `DECIMAL(p,s)` or `TEXT` |
| `if (spread < 0)` with float | Float comparison unreliable | Decimal comparison methods |
| Merging without quote check | Quote currency mixing | Explicit `quoteCurrency` guard |
| "Looks reasonable" | Intuition doesn't validate math | Invariant checks validate math |
| "Approximate fill price" | Approximation in trading = error | Exact computation or reject |
| "Average of VWAPs" | Classic silent error | Re-compute from raw levels |
| Returning null/0 without reason | Hides data absence | Structured failure with reason |

## Known Pitfalls

- **decimal.js-light has NO .isFinite() or .isNaN()** — use try-catch around constructor instead
- **String.replace("BRL","") removes FIRST occurrence, not last** — for suffix removal, use str.slice(0, -suffix.length) after endsWith()
- **Delta drift grows depth indefinitely** — applyBookDelta() binary merge must be capped. Observed: 837 levels when the real book was 20. Enforce a max adapter emit (e.g. 50 levels).
- **Runtime wrong-method errors:** tsx/esbuild has NO type checking. e.g. calling `getBooks()` when the method is `getAllBooks()` silently returns undefined. Verify method names.
