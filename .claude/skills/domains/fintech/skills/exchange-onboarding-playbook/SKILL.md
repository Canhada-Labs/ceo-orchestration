---
name: exchange-onboarding-playbook
description: Step-by-step operational playbook for adding new cryptocurrency
  exchanges to a trading platform. Use when onboarding any new exchange
  (Bitget, NovaDAX, Bitso, BitPreco, Ripio, CoinEx, Gate.io, Digitra, or
  any other). Covers the full lifecycle from API discovery to production
  deploy in under 4 hours. Includes adapter scaffolding, symbol mapping,
  pair registration, WebSocket vs REST decision matrix, feature flags,
  testing checklist, and post-deploy validation. Also use when debugging
  a newly added exchange that isn't working, when reviewing an adapter
  for production readiness, or when planning batch onboarding of multiple
  exchanges. Even if the user just says "add Bitget" or "new exchange" or
  "onboard NovaDAX", use this skill. Always combine with the
  exchange-api-integration skill for exchange-specific quirks.
owner: Marcus Alencar
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7b) ---
domain: fintech
priority: 5
risk_class: medium
stack: [python]
context_budget_tokens: 1000
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 9}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 4}
  trading-readonly: {active: true, priority: 7}
  generic: {active: true, priority: 7}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)onboard|new.?exchange|add.?(bitget|novadax|bitso|bitpreco|ripio|coinex|gate\\.io|digitra)"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/exchanges/**"
  - "**/adapters/**"
  - "**/venues/**"
---

# Exchange Onboarding Playbook

## Fail-Fast Rule

If the exchange API docs are ambiguous about orderbook format, depth
limits, or rate limits, **stop and research before writing code**. Never
guess at API behavior — one wrong assumption about sequence numbers or
depth format can corrupt the entire consolidated book.

## Cardinal Rule

**Every exchange onboarding follows the same 8-step checklist.** No
shortcuts. No "I'll add tests later." The checklist exists because ad-hoc
onboardings routinely burn 6-8 hours on exchanges that could have been
done in 2-3h with discipline. Assume the operator is not a developer —
every step must produce a copy-paste command or a concrete deliverable.

## Time Budget

| Step | Time | Deliverable |
|------|------|-------------|
| 1. API Discovery | 20 min | Decision doc: WS vs REST, endpoints, limits |
| 2. Scaffold Adapter | 30 min | New adapter file from template |
| 3. Symbol Mapping | 20 min | pairs.ts entry + parseSymbol() |
| 4. Type Definitions | 15 min | types.ts additions |
| 5. Integration Wiring | 15 min | adapter-worker.ts + wiring.ts |
| 6. Testing | 30 min | Adapter-specific tests passing |
| 7. Feature Flag Deploy | 15 min | Deploy with exchange disabled |
| 8. Production Validation | 15 min | Enable, validate, monitor |
| **Total** | **~2.5h** | Production-ready exchange |

## Pre-Requisites

Before starting any exchange onboarding:

1. Engine is stable (no active crashes or memory leaks)
2. Current tests pass: `npx vitest run` — all green
3. Event loop healthy: check `/admin/runtime` — p95 < 50ms
4. You have the exchange's API documentation URL
5. You know if the exchange requires API keys for market data
   (most don't for public orderbook data)

## Step 1: API Discovery (20 min)

### Decision Matrix: WS vs REST

```
Does the exchange offer WebSocket orderbook streams?
├── YES → Does it support incremental updates (deltas)?
│   ├── YES → Use WS with snapshot+delta sync (best quality)
│   └── NO → Use WS with periodic snapshots (good quality)
└── NO → Use REST polling (acceptable for WARM/LONG_TAIL)
```

### Discovery Checklist

Fill this out BEFORE writing any code:

```markdown
## Exchange: [NAME]
- [ ] API Docs URL: ___
- [ ] Requires API key for public market data? YES/NO
- [ ] WebSocket available? YES/NO
  - [ ] WS URL: ___
  - [ ] WS orderbook channel name: ___
  - [ ] Supports depth snapshots? YES/NO
  - [ ] Supports delta/diff updates? YES/NO
  - [ ] Provides sequence numbers? YES/NO
  - [ ] Provides CRC32 checksum? YES/NO
  - [ ] Max subscriptions per connection: ___
  - [ ] Ping/pong required? Interval: ___
- [ ] REST orderbook endpoint: ___
  - [ ] Depth parameter name and allowed values: ___
  - [ ] Rate limit: ___ req/min (or weight system)
- [ ] Symbol format: ___ (e.g., "BTC_BRL", "btc-brl", "BTCBRL")
  - [ ] Separator: ___ (none / - / _ / /)
  - [ ] Case: uppercase / lowercase
- [ ] Exchange info endpoint (for asset list): ___
- [ ] Has BRL pairs? YES/NO — How many approximately? ___
- [ ] Has USDT pairs? YES/NO
- [ ] Price precision: ___ decimal places typical
- [ ] Quantity precision: ___ decimal places typical
```

### Brazilian Exchange Quick Reference

| Exchange | WS? | Symbol Format | BRL Pairs | Key Needed? | Status |
|----------|-----|---------------|-----------|-------------|--------|
| Bitget | ✅ WS | `BTCUSDT` (concat) | Few | No (public) | LIVE |
| NovaDAX | ✅ WS | `BTC_BRL` (underscore) | ~30 | No | LIVE |
| Bitso | ✅ WS | `btc_brl` (lower_under) | ~20 | No | LIVE |
| BitPreco | ✅ WS (Phoenix v2) | `BTC-BRL` (hyphen) | ~10 | No | LIVE |
| Ripio | ❌ REST | `BTC_BRL` | ~15 | No | LIVE |
| CoinEx | ✅ WS | `BTCBRL` (concat) | ~10 | No | Sprint 4 |
| Gate.io | ✅ WS | `BTC_BRL` (underscore) | ~5 | No | Sprint 4 |
| Digitra | ✅ WS | TBD | ~20 | TBD | LIVE |

## Step 2: Scaffold Adapter (30 min)

### Choose Template Based on Connection Type

```
WS exchange with delta support → Copy from binance adapter
WS exchange with snapshot-only → Copy from okx adapter
REST-only exchange → Copy from mb (Mercado Bitcoin) adapter
```

### Template: WebSocket Adapter

The engine has `AdapterFactory` and `AdapterRegistry`. For a standard WS
exchange, use the factory:

```typescript
// In the adapter worker or a new file: adapters/[exchange].ts
import { createWSAdapter } from './adapter-factory';

export const novaDAXConfig = {
  exchange: 'novadax' as ExchangeCode,
  wsUrl: 'wss://api.novadax.com/ws/market',

  buildSubscribeMessage(pairs: string[]): string {
    return JSON.stringify({
      op: 'subscribe',
      args: pairs.map(p => `orderbook:${p}`),
    });
  },

  parseMessage(raw: string): ParsedMessage | null {
    const msg = JSON.parse(raw);
    if (msg.channel?.startsWith('orderbook:')) {
      const pair = msg.channel.replace('orderbook:', '');
      return {
        type: msg.action === 'snapshot' ? 'snapshot' : 'update',
        pair: formatPair(pair),  // normalize to CanonicalPair
        bids: msg.data.bids.map(([p, q]: string[]) => [p, q]),
        asks: msg.data.asks.map(([p, q]: string[]) => [p, q]),
        timestamp: msg.timestamp || Date.now(),
        sequence: msg.seq,
      };
    }
    return null;
  },

  formatPair(canonical: string): string {
    // CanonicalPair "BTC/BRL" → exchange format "BTC_BRL"
    return canonical.replace('/', '_');
  },

  parsePair(exchangeSymbol: string): string {
    // Exchange format "BTC_BRL" → CanonicalPair "BTC/BRL"
    return exchangeSymbol.replace('_', '/').toUpperCase();
  },

  pingMessage: JSON.stringify({ op: 'ping' }),
  pingIntervalMs: 30_000,
  maxSubscriptionsPerConnection: 100,
};
```

### Template: REST Adapter

```typescript
// For REST-only exchanges
export const bitPrecoConfig = {
  exchange: 'bitpreco' as ExchangeCode,
  restBaseUrl: 'https://api.bitpreco.com',
  pollIntervalMs: 5_000,  // REST: poll every 5s (WARM tier)

  async fetchOrderbook(pair: string): Promise<RawOrderbook> {
    const url = `${this.restBaseUrl}/v1/orderbook/${pair}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`BitPreco ${res.status}`);
    const data = await res.json();
    return {
      bids: data.bids.map((b: any) => [String(b.price), String(b.amount)]),
      asks: data.asks.map((a: any) => [String(a.price), String(a.amount)]),
      timestamp: Date.now(),
    };
  },

  formatPair(canonical: string): string {
    // "BTC/BRL" → "BTC-BRL"
    return canonical.replace('/', '-');
  },

  parsePair(exchangeSymbol: string): string {
    // "BTC-BRL" → "BTC/BRL"
    return exchangeSymbol.replace('-', '/').toUpperCase();
  },
};
```

## Step 3: Symbol Mapping (20 min)

### pairs.ts Entry

Every exchange needs an entry in `pairs.ts` with its supported pairs:

```typescript
// pairs.ts — add entry for new exchange
export const EXCHANGE_PAIRS: Record<ExchangeCode, string[]> = {
  // ... existing entries ...
  novadax: [
    'BTC/BRL', 'ETH/BRL', 'USDT/BRL', 'SOL/BRL', 'XRP/BRL',
    'ADA/BRL', 'DOGE/BRL', 'DOT/BRL', 'AVAX/BRL', 'MATIC/BRL',
    // ... discover from exchange info endpoint
  ],
};
```

### Discovering Pairs Automatically

```bash
# Most exchanges have an info endpoint that lists all pairs
# Run this ONCE to discover pairs, then hardcode the BRL ones

# Example: NovaDAX
curl -s https://api.novadax.com/v1/common/symbols | \
  jq '[.data[] | select(.quoteCurrency == "BRL") | .symbol]'

# Example: Bitget
curl -s https://api.bitget.com/api/v2/spot/public/symbols | \
  jq '[.data[] | select(.quoteCoin == "BRL") | .symbol]'
```

**Rule**: Always discover pairs from the exchange's info endpoint. Never
guess which pairs exist. Some exchanges have BRL pairs that aren't
documented.

### parseSymbol Validation

```typescript
// Every adapter must validate symbol parsing round-trips
const testPairs = ['BTC/BRL', 'ETH/BRL', 'USDT/BRL'];
for (const pair of testPairs) {
  const exchangeFormat = formatPair(pair);
  const canonical = parsePair(exchangeFormat);
  assert(canonical === pair, `Round-trip failed: ${pair} → ${exchangeFormat} → ${canonical}`);
}
```

## Step 4: Type Definitions (15 min)

### Add to types.ts

```typescript
// types.ts — add ExchangeCode
export type ExchangeCode =
  | 'exchangex' | 'okx' | 'binance' | 'bybit' | 'mb' | 'bb'
  | 'novadax' | 'bitso' | 'bitpreco' | 'ripio' | 'bitget'
  | 'kucoin' | 'trubit' | 'digitra' | 'coinext' | 'kraken'
  | 'coinbase' | 'bitstamp' | 'deribit' | 'bitfinex' | 'hyperliquid'
  ;

// If exchange has unique response shapes, add them:
export interface NovaDAXOrderbookMessage {
  channel: string;
  action: 'snapshot' | 'update';
  data: {
    bids: [string, string][];
    asks: [string, string][];
  };
  timestamp: number;
  seq?: number;
}
```

## Step 5: Integration Wiring (15 min)

### adapter-worker.ts

```typescript
// Add to the switch/case or use AdapterRegistry
case 'novadax':
  adapter = createWSAdapter(novaDAXConfig);
  break;
```

### wiring.ts — Feature Flag

```typescript
// Add with feature flag (disabled by default)
const NOVADAX_ENABLED = process.env.ENABLE_NOVADAX === 'true';

if (NOVADAX_ENABLED) {
  startAdapter('novadax', novaDAXConfig.pairs);
}
```

### Deploy Environment Variable

```bash
# Deploy with exchange DISABLED first (example uses Fly.io — adapt to your platform)
fly secrets set ENABLE_NOVADAX=false -a {{APP_NAME}}

# After validation, enable:
fly secrets set ENABLE_NOVADAX=true -a {{APP_NAME}}
```

## Step 6: Testing (30 min)

### Minimum Test Suite for New Exchange

```typescript
// tests/adapters/novadax.test.ts
import { describe, test, expect } from 'vitest';

describe('NovaDAX Adapter', () => {
  // 1. Symbol parsing round-trip
  test('formatPair converts canonical to exchange format', () => {
    expect(formatPair('BTC/BRL')).toBe('BTC_BRL');
    expect(formatPair('ETH/BRL')).toBe('ETH_BRL');
    expect(formatPair('USDT/BRL')).toBe('USDT_BRL');
  });

  test('parsePair converts exchange format to canonical', () => {
    expect(parsePair('BTC_BRL')).toBe('BTC/BRL');
    expect(parsePair('eth_brl')).toBe('ETH/BRL');  // case handling
  });

  test('round-trip is lossless', () => {
    const pairs = ['BTC/BRL', 'ETH/BRL', 'SOL/BRL', 'USDT/BRL'];
    for (const p of pairs) {
      expect(parsePair(formatPair(p))).toBe(p);
    }
  });

  // 2. Message parsing
  test('parseMessage handles snapshot correctly', () => {
    const raw = JSON.stringify({
      channel: 'orderbook:BTC_BRL',
      action: 'snapshot',
      data: {
        bids: [['510000.00', '0.5'], ['509900.00', '1.2']],
        asks: [['510100.00', '0.3'], ['510200.00', '0.8']],
      },
      timestamp: 1708799400000,
    });
    const result = parseMessage(raw);
    expect(result).not.toBeNull();
    expect(result!.type).toBe('snapshot');
    expect(result!.pair).toBe('BTC/BRL');
    expect(result!.bids).toHaveLength(2);
    expect(result!.bids[0][0]).toBe('510000.00');  // string, not number
  });

  // 3. Invalid input rejection
  test('parseMessage rejects malformed data', () => {
    expect(parseMessage('{')).toBeNull();
    expect(parseMessage(JSON.stringify({ type: 'pong' }))).toBeNull();
  });

  // 4. Orderbook invariants
  test('parsed bids are price-descending', () => {
    // Use real captured response from exchange
    const snapshot = parseMessage(REAL_SNAPSHOT_JSON);
    for (let i = 1; i < snapshot!.bids.length; i++) {
      expect(Number(snapshot!.bids[i][0]))
        .toBeLessThan(Number(snapshot!.bids[i - 1][0]));
    }
  });

  // 5. Depth limits respected
  test('does not request invalid depth values', () => {
    // If exchange has discrete depth limits, verify
    expect(ALLOWED_DEPTHS.novadax).toBeDefined();
    expect(ALLOWED_DEPTHS.novadax.every(d => d > 0)).toBe(true);
  });
});
```

### Capture Real Responses

```bash
# Capture a real response for replay in tests
# WebSocket exchange:
wscat -c wss://api.novadax.com/ws/market -x '{"op":"subscribe","args":["orderbook:BTC_BRL"]}' | head -5 > tests/fixtures/novadax_snapshot.json

# REST exchange:
curl -s https://api.bitpreco.com/v1/orderbook/BTC-BRL > tests/fixtures/bitpreco_orderbook.json
```

**Rule**: Every adapter test must include at least one real captured response.
Mock data hides integration bugs.

## Step 7: Feature Flag Deploy (15 min)

### Deploy Sequence

```bash
# 1. Run tests locally
cd {{PROJECT_PATH}}
npx vitest run

# 2. Deploy with exchange DISABLED (platform-agnostic: adapt to your deploy tool)
fly deploy -a {{APP_NAME}}

# 3. Verify engine starts and existing exchanges work
curl {{PRODUCTION_URL}}/healthz
curl {{PRODUCTION_URL}}/exchanges | jq '.exchanges | keys'

# 4. Check no regressions
curl {{PRODUCTION_URL}}/admin/runtime \
  -H "Authorization: Basic $(echo -n user:pass | base64)" | \
  jq '.event_loop'
```

## Step 8: Production Validation (15 min)

### Enable and Validate

```bash
# 1. Enable the exchange
fly secrets set ENABLE_NOVADAX=true -a {{APP_NAME}}

# 2. Wait 30s for adapter to connect and receive first data

# 3. Verify exchange appears
curl {{PRODUCTION_URL}}/exchanges | \
  jq '.exchanges.novadax'

# 4. Verify books are flowing
curl {{PRODUCTION_URL}}/books/BTC/BRL | \
  jq '.books[] | select(.exchange == "novadax")'

# 5. Check connection state
curl {{PRODUCTION_URL}}/admin/health \
  -H "Authorization: Basic ..." | \
  jq '.exchanges.novadax'

# 6. Verify no event loop degradation
curl {{PRODUCTION_URL}}/admin/runtime \
  -H "Authorization: Basic ..." | \
  jq '.event_loop.p95_ms'
# Should still be < 50ms
```

### Post-Enable Monitoring (next 30 min)

- Watch `/admin/runtime` for event loop p95 — should not increase >20%
- Watch RSS memory — new exchange adds ~5-15MB depending on pair count
- Verify books aren't stale: check `updated_at` timestamps in `/books/:pair`
- Verify consolidated book includes new exchange data

### Rollback

```bash
# If anything goes wrong:
fly secrets set ENABLE_NOVADAX=false -a {{APP_NAME}}
# Engine will gracefully disconnect the adapter on next cycle
```

## Batch Onboarding Strategy (Sprint 2-4)

When onboarding multiple exchanges in sequence:

1. **One exchange per deploy.** Never enable 2+ new exchanges simultaneously.
2. **24h soak between exchanges.** Let each new exchange run 24h in production
   before adding the next. Catches memory leaks and connection issues.
3. **Monitor total RSS.** Each exchange adds pairs → more book cache → more RAM.
   With 21 exchanges, budget ~2-3GB for book cache alone.
4. **Tier auto-classification.** New exchanges start as WARM by default.
   After 24h of volume data, auto-tiering will classify them correctly.

### Sprint 2-4 Recommended Order

```
Sprint 2: Bitget → NovaDAX → Bitso     (3 exchanges, all WS)
Sprint 3: BitPreco → Ripio → CoinEx    (2 REST + 1 WS)
Sprint 4: Gate.io → Digitra + others    (remaining)
```

> **NOTE:** Track which exchanges are live in your own inventory. The list above is illustrative order-of-operations, not a current status.

Rationale: WS exchanges first (higher data quality, lower polling overhead),
REST exchanges later (need careful rate limit management).

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| "I'll add tests after deploy" | Bugs in production corrupt consolidated book | Tests before deploy, always |
| Enable exchange without feature flag | No rollback path | Feature flag default OFF |
| Guess at pair list | Missing pairs or phantom pairs | Discover from exchange info endpoint |
| Copy adapter without understanding | Exchange quirks differ | Read API docs first, then copy template |
| Deploy 3 exchanges at once | Can't isolate which one causes problems | One exchange per deploy |
| Skip real response fixtures | Mock data hides parsing bugs | Capture at least one real response |
| Hardcode WS URL | Some exchanges have regional URLs | Config or env var |
| Ignore rate limits | IP ban from exchange | Research and enforce limits |
| Skip event loop check post-deploy | New exchange could saturate main thread | Always check /admin/runtime |
