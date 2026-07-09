<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/testing-strategy/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## Test Patterns by Module

### External Integration Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Snapshot processing | Parse and store initial state | HIGH |
| Incremental update | Apply update to existing state | HIGH |
| Sequence validation | Detect and handle gaps | HIGH |
| Checksum verification | Validate integrity (where supported) | HIGH |
| Empty-entry removal | Zero/empty value removes entry | HIGH |
| Sort order | Deterministic ordering of outputs | HIGH |
| Identifier normalization | Upstream format to canonical | HIGH |
| Reconnect handling | Discard stale data after reconnect | MEDIUM |
| Rate limit handling | Backoff on 429 response | MEDIUM |
| Connection lifecycle | Connect, subscribe, disconnect | MEDIUM |

### Domain Math Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Basic computation | Known inputs, hand-computed result | HIGH |
| Edge cases | Empty, single entry, huge values | HIGH |
| Subtraction / differences | Normal, zero, inverted | HIGH |
| Estimation against known data | Deterministic fixtures | HIGH |
| Decimal precision | String round-trip, no Number conversion | HIGH |
| Rounding modes | Explicit mode per function | HIGH |
| Cumulative sums | Monotonic non-decreasing | MEDIUM |
| Signal detection | True positive, true negative | MEDIUM |
| Fee / cost calculation | Parameterized by config | MEDIUM |

### Route Tests

| What to Test | Example | Priority |
|-------------|---------|----------|
| Auth required | 401 without token | CRITICAL |
| Auth valid token | 200 with valid token | HIGH |
| Auth expired token | 401 with expired token | HIGH |
| Input validation | 400 on bad input | HIGH |
| Tier gating | 403 for insufficient tier | HIGH |
| Rate limiting | 429 after limit exceeded | MEDIUM |
| CORS headers | Correct origin in response | MEDIUM |

