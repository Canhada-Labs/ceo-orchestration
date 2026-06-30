---
name: exchange-api-integration
description: Integrating with cryptocurrency exchange APIs (REST and WebSocket),
  handling exchange-specific quirks, discrete limits, rate limits,
  symbol mapping, depth constraints, sequencing, and fallback logic.
  Use when working with Binance, OKX, ExchangeX, Bybit, Mercado Bitcoin,
  or any exchange adapter or collector. Also use when debugging WebSocket
  disconnections, implementing reconnect logic, parsing exchange-specific
  orderbook formats, or adding a new exchange to the platform.
  Never assume uniform API behavior across exchanges.
owner: Marcus Alencar
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 3
risk_class: medium
stack: [python, typescript]
context_budget_tokens: 1200
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 8}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 2}
  trading-readonly: {active: true, priority: 4}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: file-edit, glob: "**/exchanges/**"}
  - {event: file-edit, glob: "**/adapters/**"}
  - {event: help-me-invoked, regex: "(?i)binance|okx|bybit|kraken|kucoin|exchange.?api|rate.?limit"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/exchanges/**"
  - "**/adapters/**"
  - "**/collectors/**"
---

# Exchange API Integration

## Fail-Fast Rule

If any mandatory invariant, validation, or precondition fails, **stop and
return a structured failure**. Never guess, infer, smooth, approximate,
or "fix" financial or market data. Never infer missing exchange behavior,
precision, limits, or semantics.

## Cardinal Rule

Every exchange is different. Never write generic "exchange adapter" code
that assumes uniform behavior. Each adapter must be written against the
exchange's actual documented API, with quirks explicitly handled.

## No Magic Merge

**Never merge, compare, or aggregate data from different exchanges unless
the exact compatibility rules are explicitly defined.** "They look the same"
is not a compatibility rule. Require identical CanonicalPair (base + quote)
and explicit freshness validation before any cross-exchange operation.

## Symbol Mapping

### Exchange-Specific Formats

| Exchange | Format | Example | Separator |
|---|---|---|---|
| Binance | Concatenated uppercase | `BTCUSDT` | none |
| OKX | Hyphenated uppercase | `BTC-USDT` | `-` |
| Bybit | Concatenated uppercase | `BTCUSDT` | none |
| ExchangeX | Lowercase with underscore | `btc_brl` | `_` |
| Mercado Bitcoin | Lowercase with hyphen | `btc-brl` | `-` |

### Normalization Rules

- Normalize to `CanonicalPair` at the **ingestion boundary** — the first
  function that touches raw exchange data.
- Each adapter exports `parseSymbol(raw: string): CanonicalPair | null`.
- Never parse symbols with regex guessing. Use the exchange's asset list
  endpoint to build a lookup map at startup.
- Edge cases like `SOLUSD` vs `SOLUSDT` require a lookup map — you cannot
  know where base ends and quote begins without one.

```typescript
// CORRECT: Explicit mapping from exchange info endpoint
const symbolMap = await fetchExchangeInfo();

function parseSymbol(raw: string): CanonicalPair | null {
  const info = symbolMap[raw];
  if (!info) return null;
  return canonicalizePair(info.base, info.quote);
}

// WRONG: Regex guessing
function parseSymbol(raw: string): CanonicalPair {
  const match = raw.match(/^(\w+)(USDT|BRL|USD)$/);
  // breaks on SUSDT, USDTBRL, etc.
}
```

## Connection State

Connection state is a first-class concept. Every adapter tracks it explicitly:

```typescript
type ConnectionState =
  | 'DISCONNECTED'
  | 'CONNECTING'
  | 'CONNECTED'
  | 'SUBSCRIBED'
  | 'DEGRADED'
  | 'CIRCUIT_OPEN';
```

Rules:
- Data from `DEGRADED` or `CIRCUIT_OPEN` sources must **never** be treated
  as equivalent to live WebSocket data.
- State transitions are logged and metricked.
- Consumers can query connection state before using data.

## WebSocket Orderbook Streams

### Binance

- **Depth stream**: `<symbol>@depth<levels>@<speed>`
  - Levels: `5`, `10`, `20` (discrete — do not request other values)
  - Speed: `100ms` or `1000ms`
- **Diff depth stream**: `<symbol>@depth@<speed>`
  - Requires local book management with sequence validation (`lastUpdateId`)
- **Snapshot + diff sync**:
  1. Open diff stream, buffer events
  2. Fetch REST snapshot (has `lastUpdateId`)
  3. Drop buffered events where `u <= lastUpdateId`
  4. Apply events where `U <= lastUpdateId+1 <= u`
  5. If gap detected, re-snapshot

### OKX

- **Channel**: `books5` (5 levels), `books` (400 levels), `books50-l2` (50)
- **Checksum**: OKX provides CRC32 checksum. Compute on top 25 levels
  and compare. On mismatch, re-subscribe.
- **Action field**: `snapshot` vs `update` — handle both explicitly.

### Bybit

- **Topic**: `orderbook.<depth>.<symbol>`
  - Depth: `1`, `25`, `50`, `200`, `500`
- **Type field**: `snapshot` vs `delta`
- **Sequence**: `seq` field. Validate monotonic increase.

### ExchangeX / Mercado Bitcoin

- Typically REST-only or polling-based for orderbook.
- Lower liquidity — staleness detection is critical.

## Timestamp Responsibility

Every freshness calculation must explicitly state which timestamp was used:

- `exchangeTimestamp`: provided by the exchange (may have clock drift)
- `receivedAt`: our clock when we received the message

**Rule**: Use `receivedAt` for staleness calculations. `exchangeTimestamp`
is useful for audit and latency measurement but unreliable for freshness
because of clock drift across exchanges.

Any code that assesses freshness must document which timestamp it uses.

## Rate Limiting

### Principles

- Track rate limit budget per exchange, per endpoint category.
- Use the exchange's reported limits, not guessed values.
- Implement token bucket or sliding window counter.
- Leave safety margin (~80% of stated limit).
- On HTTP 429: exponential backoff with jitter. Never retry immediately.

### Exchange-Specific Limits

| Exchange | REST Limits | WebSocket Limits |
|---|---|---|
| Binance | 1200 weight/min (varies by endpoint) | 5 messages/sec per connection |
| OKX | 20 req/2sec per endpoint (varies) | 240 subscriptions per connection |
| Bybit | Varies by endpoint tier | 20 subscriptions per connection |

- **Binance weight system**: Each endpoint costs different "weight".
  Track total weight, not just request count.
- Check response headers (`X-MBX-USED-WEIGHT-*`).

## Connection Lifecycle

### WebSocket Reconnection Pattern

```
1. Connect with exponential backoff (1s, 2s, 4s, 8s... max 60s)
2. Add jitter (±20%) to prevent thundering herd
3. On connect: re-subscribe to all active channels
4. On subscribe: re-sync book state (snapshot + apply pending diffs)
5. Emit metric: ws.reconnect { exchange, attempt, duration_ms }
6. After N consecutive failures: CIRCUIT_OPEN, stop retrying until cooldown
```

### Ping/Pong and Keepalive

- **Binance**: Server sends ping every 3 min. Respond within 10 min.
- **OKX**: Send ping frame every 30s. Dropped after 30s of silence.
- **Bybit**: Send `{"op":"ping"}` every 20s.
- Watchdog: if no message within `2 × expected_interval`, reconnect.

## Fallback Rules

**REST fallback is never transparent.** When falling back from WebSocket
to REST polling:

- Label all data with `source: 'rest_fallback'` — never silently replace WS.
- Apply looser staleness thresholds for REST (polling interval is slower).
- Emit metric: `adapter.fallback { exchange, reason }`.
- Log at `warn` level with context.
- Consumers must be able to distinguish WS data from REST fallback.

## Depth and Precision Constraints

### Discrete Depth Values

```typescript
const ALLOWED_DEPTHS: Record<string, number[]> = {
  binance: [5, 10, 20],
  okx: [1, 5, 50, 400],
  bybit: [1, 25, 50, 200, 500],
};
```

Never request arbitrary depth values.

### Price and Quantity Precision

- Fetch tick/step size from exchange info at startup. Store as `Decimal`.
- Precision can change — refresh periodically (daily).

## Adapter Structure

```
adapters/
├── binance/
│   ├── types.ts      # Exchange-specific raw types
│   ├── symbols.ts    # Symbol mapping and parsing
│   ├── ws.ts         # WebSocket connection and messages
│   ├── rest.ts       # REST API calls
│   └── adapter.ts    # Unified interface implementation
├── okx/
│   └── ...
└── types.ts          # Shared adapter interface
```

### Shared Interface

```typescript
interface ExchangeAdapter {
  readonly exchange: string;
  readonly connectionState: ConnectionState;
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  subscribeOrderbook(pair: CanonicalPair, depth: number): void;
  unsubscribeOrderbook(pair: CanonicalPair): void;
  onSnapshot(handler: (snap: OrderbookSnapshot) => void): void;
  onError(handler: (err: ExchangeError) => void): void;
  getHealth(): AdapterHealthStatus;
}
```

Every adapter implements this interface. Internals are exchange-specific.
Do not force shared base classes that hide quirks.

## Testing per Exchange

1. **Symbol parsing**: Raw symbol → CanonicalPair (and invalid inputs).
2. **Snapshot parsing**: Raw JSON → OrderbookSnapshot with correct types.
3. **Sequence validation**: Out-of-order messages → rejection/re-sync.
4. **Reconnection**: Disconnect → reconnect with correct state recovery.
5. **Rate limit**: Simulate 429 → verify backoff, no immediate retry.
6. **Fallback labeling**: REST fallback → verify data is labeled, not silent.

Record real exchange responses (sanitized) and replay against the adapter.

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Generic `BaseExchangeAdapter` | Hides exchange quirks | Independent adapters, shared interface |
| Regex-based symbol parsing | Ambiguous without asset list | Lookup map from exchange info |
| `depth: any` parameter | May send invalid depth | Validate against allowed values |
| Ignoring sequence numbers | Silent data loss | Validate monotonicity |
| Single reconnect delay | Thundering herd | Exponential backoff with jitter |
| Shared WS for all pairs | One failure kills all | Isolate failure domains |
| Silent REST fallback | Users act on stale data | Always label fallback data |
| Using exchangeTs for staleness | Clock drift lies | Use receivedAt |
| Merging "similar" exchanges | Produces fake markets | Require explicit compatibility |

## Known Pitfalls

- **MB WS pair REVERSED:** format is BRLBTC not BTCBRL (quote+base, no separator)
- **ExchangeX WS trade channel mismatch:** subscribe "trades", receive channel "trade" (singular)
- **Fake 0-1ms latency:** happens when adapter fallbacks to tsExchange = Date.now(). Fix: measure WS ping/pong RTT.
- **Coinext AlphaPoint:** SubscribeLevel2 uses m=0 (request), NOT m=2. row[7] = InstrumentId (number).
- **Coinext Rolling24HrPxChangePercent:** API returns as percentage (0.407 = 0.4%), NOT fraction. Do NOT ×100.
- **Reconnect MUST clear orderbooks (ExchangeX/OKX/Bybit/Bitget):** cleanupConnection() must clear books for that connection. Otherwise stale data → crossed books.
- **BitPreço keys already dash-separated:** "BTC-BRL". Don't slice+re-add → "BTC--BRL".
- **New exchange → ALWAYS update ticker.ts** — poll fetchers + backoff config.
- **Engine.IO v4 REVERSED ping/pong from v3:** v3: server "2"→client "3". v4: CLIENT sends "2"→server "3".
- **NovaDAX Engine.IO:** pingInterval=25s, pingTimeout=5s. Server sends ping, expects pong within 5s.
- **Multiple WS on one event loop:** setInterval heartbeats can be starved by message processing.
- **Never use getAllBooks() in periodic timers** — use iterateBooks() (zero-allocation iterator).
- **Hyperliquid pair normalization:** Adapter uses "BTC-USDC" internally but engine expects "btcusdc". subscribedKeys filter silently rejected ALL tickers.
- **extractBaseFromPair must strip suffixes:** PERP/SWAP/PERPETUAL cause wrong base extraction. Always strip first.
- **Coinbase USD pairs not in priority set:** "btcusd" not in PRIORITY_PAIRS_NORMALIZED. Add btcusd/ethusd/solusd.
- **Binance/Bybit pair fetch from specific regions intermittent:** Timeout 25s + retry 3x. May need cached fallback.
- **Bybit linear depth 1000 silently rejected:** Linear max is 500. Cap HOT at 500.
- **Exchange weight budget overflow:** e.g. 58 pairs polled every 8s can exceed a 1800/min weight budget. Fix: dual-tier (HOT 8s, non-HOT 15s).
