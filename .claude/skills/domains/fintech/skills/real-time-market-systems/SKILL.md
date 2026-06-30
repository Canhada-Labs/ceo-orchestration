---
name: real-time-market-systems
description: Designing, reviewing, and evolving real-time market data systems,
  including order book engines, WebSocket ingestion, exchange adapters,
  pair normalization, depth aggregation, VWAP calculation, and
  latency-sensitive financial infrastructure. Use when working on order books,
  arbitrage engines, market data pipelines, exchange integrations, real-time
  trading systems, consolidated book design, or any architecture decision
  involving the data plane, control plane, or analytics plane of the platform.
  Prioritize correctness, determinism, and observability over UI.
  This is the orchestrating skill — apply financial-correctness-and-math,
  exchange-api-integration, and state-machines-and-invariants for details.
owner: Tomas Herrera
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 3
risk_class: medium
stack: [python]
context_budget_tokens: 1300
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 8}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)order.?book|market.?data|consolidated.?book|depth.?aggreg|websocket.?ingest"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/orderbook/**"
  - "**/market-data/**"
  - "**/arbitrage/**"
  - "**/ingestion/**"
---

# Real-Time Market Systems

## Fail-Fast Rule

If any mandatory invariant, validation, or precondition fails, **stop and
return a structured failure**. Never guess, infer, smooth, approximate,
or "fix" financial or market data. Never infer missing exchange behavior,
precision, limits, or semantics.

## System Architecture

The platform has three planes with strict separation.

### Data Plane (Hot Path)

The real-time path from exchange WebSocket to consumer. Latency-sensitive.

```
Exchange WS → Adapter → Normalizer → Cache → API/Consumer
```

**Hot path definition**: Any code that executes on every incoming market
data message. This includes adapter message handling, normalization,
cache update, and snapshot serving.

Rules:
- Minimal allocations. Pre-allocate buffers where possible.
- No database writes. Persist asynchronously via analytics plane.
- No blocking I/O. All operations async or event-driven.
- Errors are logged and metricked, never thrown to crash the pipeline.
- Isolate failures per exchange/pair — one bad stream cannot kill others.
- **Never refactor or modify hot-path logic unless explicitly instructed.**

### Cold Path

Everything that does NOT execute per-message: config loading, exchange
info refresh, health checks, admin endpoints, historical queries.
Refactoring and observability additions are safe here.

### Control Plane

Configuration, orchestration, lifecycle management.

- Active exchanges and pairs per exchange
- Depth levels per pair
- Connection lifecycle (connect, reconnect, circuit-break)
- Feature flags for rollout
- Config changes must not require restart. Hot-reload with validation.

### Analytics Plane

Storage, aggregation, historical analysis. Eventual consistency acceptable.

- Non-blocking writes from data plane (fire-and-forget or queue).
- Historical snapshots for backtesting.
- Aggregated metrics (spread over time, depth trends, VWAP history).
- May use different storage than hot path cache.

## Timestamp Provenance

Every message carries three timestamps:

- `exchangeTimestamp`: when the exchange generated the event (may be null)
- `receivedAt`: when our adapter received it (always present)
- `processedAt`: when the cache updated (always present)

**Standard time unit**: Always milliseconds (ms). If a source provides
ns/µs/s, normalize to ms and log the conversion. Never mix time units.

## OrderbookSnapshot Schema

```typescript
interface OrderbookSnapshot {
  pair: CanonicalPair;
  exchange: string;
  quoteCurrency: string;            // redundant guard
  bids: PriceLevel[];               // sorted descending
  asks: PriceLevel[];               // sorted ascending
  exchangeTimestamp: number | null;
  receivedAt: number;
  sequenceId: number | null;
  isSnapshot: boolean;              // full snapshot vs delta
  source: 'websocket' | 'rest_fallback';
}

interface PriceLevel {
  price: Decimal;
  quantity: Decimal;
}
```

Prices and quantities are always `Decimal`, never `number`.

## Consolidated Book

Merges orderbooks from multiple exchanges for the **same canonical pair**.

### Eligibility Rules

A source contributes to consolidation only if:
- BookState is `READY` (see state-machines-and-invariants skill)
- ConnectionState is `SUBSCRIBED` or `CONNECTED` (not DEGRADED/CIRCUIT_OPEN)
- Freshness check passes (receivedAt within threshold)
- Quote currency matches the canonical pair

### Data Quality Label

Every consolidated response carries a quality label:

```typescript
interface ConsolidatedResponse {
  pair: CanonicalPair;
  responseState: 'OK' | 'DEGRADED' | 'INSUFFICIENT_DATA';
  quality: {
    level: 'HIGH' | 'MEDIUM' | 'LOW';
    sourcesTotal: number;
    sourcesEligible: number;
    sourcesExcluded: number;
    maxAgeMs: number;
    excludedReasons: string[];  // e.g. ['binance:stale', 'okx:circuit_open']
  };
  book: MergedOrderbook | null;
}
```

Rules:
- `sourcesEligible >= 2` → OK
- `sourcesEligible === 1` → DEGRADED
- `sourcesEligible === 0` → INSUFFICIENT_DATA, `book` is null
- Never "fill in" missing exchanges with stale data to look complete.

### Merge Logic

```typescript
function getConsolidated(pair: CanonicalPair): ConsolidatedResponse {
  const allBooks = cache.getAll(pair);
  const eligible = allBooks.filter(b =>
    b.bookState === 'READY' &&
    b.quoteCurrency === pair.quote &&
    !isStale(b) &&
    getConnectionState(b.exchange) !== 'CIRCUIT_OPEN'
  );
  const excluded = allBooks.filter(b => !eligible.includes(b));

  if (eligible.length === 0) {
    return {
      pair, responseState: 'INSUFFICIENT_DATA',
      quality: buildQuality(allBooks, eligible, excluded),
      book: null,
    };
  }

  // Each level carries provenance (exchange source)
  return {
    pair,
    responseState: eligible.length >= 2 ? 'OK' : 'DEGRADED',
    quality: buildQuality(allBooks, eligible, excluded),
    book: mergeBooksWithProvenance(eligible),
  };
}
```

## Event Schema and Versioning

**Schema versioning is always-on.** Everything crossing a boundary
(events, API responses) has a `version` field. Additive changes only.

```typescript
interface OrderbookEvent {
  version: number;          // start at 1
  type: 'snapshot' | 'update' | 'stale' | 'unavailable';
  pair: CanonicalPair;
  exchange: string;
  timestamp: number;
  payload: OrderbookSnapshot | null;
}
```

Rules:
- Consumers check `version` and handle unknown versions gracefully.
- Adding fields = backward compatible.
- Removing/renaming fields = breaking change, requires migration.

## Staleness Detection

```typescript
function isStale(snapshot: OrderbookSnapshot): boolean {
  const threshold = STALENESS_THRESHOLDS[snapshot.exchange]
    ?? STALENESS_THRESHOLDS.default;
  return (Date.now() - snapshot.receivedAt) > threshold;
}
```

- Stale data is **flagged and excluded**, never silently served.
- API responses include `stale: boolean`.
- If all exchanges for a pair are stale, pair is `INSUFFICIENT_DATA`.
- Thresholds are per-exchange (some are slower).

## Pair Normalization Pipeline

```
Raw exchange symbol → parseSymbol(exchange) → CanonicalPair → all downstream
```

After normalization, no code constructs pairs from raw strings.
All functions accept `CanonicalPair`, never `string`.

### Pair Registry

```typescript
interface PairRegistry {
  isValid(exchange: string, pair: CanonicalPair): boolean;
  getExchangeSymbol(exchange: string, pair: CanonicalPair): string | null;
  getCanonicalPair(exchange: string, rawSymbol: string): CanonicalPair | null;
  refresh(exchange: string): Promise<void>;
}
```

Single source of truth for symbol mapping.

## Arbitrage Detection (Read Path)

```
For pair X/Y:
  best_bid = max(bid[0].price) across eligible exchanges
  best_ask = min(ask[0].price) across eligible exchanges

  If best_bid.exchange ≠ best_ask.exchange AND best_bid > best_ask:
    → potential arbitrage
    → verify both books fresh (not stale)
    → verify sufficient depth at those levels
    → compute slippage-adjusted execution price
```

- Never signal arbitrage on stale data.
- Compute slippage-adjusted price, not just top-of-book.
- Log every opportunity with full provenance.
- Arbitrage detection is **read-only** — never modifies orderbook state.

## No Helpful Aggregation

Never perform FX conversion, synthetic route calculation, or cross-currency
triangulation inside the consolidated book unless an explicit skill and
policy exists for it. The Claude model must not "helpfully" combine
BTC/USDT with BTC/BRL by converting currencies.

## Performance Considerations

- Flat `Map<CacheKey, OrderbookSnapshot>` for O(1) lookups.
- Cache consolidated view with invalidation on write if reads are frequent.
- Avoid JSON.parse/stringify on hot path.
- Minimize GC pressure in Node.js on hot path.
- Only optimize after profiling. Premature optimization adds complexity.

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| DB write on hot path | Adds latency, blocks | Async write to analytics plane |
| String pair keys without validation | Format drift | Always `CanonicalPair` type |
| Swallowing errors silently | Hides data issues | Log, metric, propagate signal |
| Shared mutable state across exchanges | Race conditions | Isolate per exchange, merge on read |
| Optimizing before profiling | Wastes effort | Profile first, then targeted fix |
| Treating all exchanges as equal latency | False assumption | Track per-exchange latency |
| Serving stale as "OK with warning" | Users still act on it | Exclude stale from consolidated |
| Cross-currency aggregation | Produces fake markets | Reject unless explicit policy |

## Known Pitfalls

- **IPC message COUNT > SIZE** — each process.send() has ~85ms overhead. Coalesce into batch buffer (50ms timer).
- **V8 structured clone vs JSON.stringify** — for flat data, JSON.stringify is 3-5x faster. Structured clone for complex objects.
- **IPC prefix routing** — other message types sharing same prefix get misrouted. Use unique prefixes.
- **Larger IPC batches do NOT help stalls** — larger batch = larger JSON.parse = longer blocking. Many small beats few large.
- **Deferred paths unreliable after hot-path optimization** — handle ALL IPC types in same code path.
- **storeFastBook must NOT have time-based skip guard:** a 100ms guard blocks consecutive writes because storeFastBook itself sets last_book_update_ms.
- **storeProcessedBook must guard against overwriting fresher books:** batch-processing workers run with delay. Without a ts_ingest guard, they overwrite fresh fast-path data with stale batches. Merge analytics only.
- **storeFastBook in-place mutation must copy ALL fields:** bids/asks/bestBid/bestAsk/midPrice/spreadPct/ts_exchange/ts_ingest/status/latency_ms/internal_depth_levels + conditionals. Leave a comment "UPDATE THIS LIST when BookState changes" to mark the spot.
- **Timer scope crash:** variables referenced by setInterval at outer scope MUST be declared at outer scope.
- **slog→captureError infinite recursion** — must add recursion guard when wiring slog into captureError.
