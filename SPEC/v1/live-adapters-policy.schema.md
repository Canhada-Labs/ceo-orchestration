# SPEC/v1/live-adapters-policy.schema.md — `LiveCallPolicy` contract

**Version:** 1.0.0-rc.1 (PLAN-012 Phase 1, Sprint 12)
**Status:** PROPOSED (additive; extends ADR-040 Live Adapter
Activation Contract and ADR-028 envelope parity)
**Authoritative source:** `.claude/hooks/_lib/adapters/live/_policy.py`
— the frozen `LiveCallPolicy` dataclass implementing this schema.

## 0. Purpose

ADR-040 §1-§6 establishes the per-call policy every live adapter MUST
obey. This document is the grep-able field inventory + type
constraints + validation rules the dataclass is tested against.
Companion to `adapters.schema.md` (ABI) and
`normalized_envelope.schema.md` (return shape).

## 1. Dataclass shape (frozen)

Per-provider subclasses (`ClaudeLivePolicy`, `GeminiLivePolicy`,
`OpenAILivePolicy`, `LocalLivePolicy`) inherit and override only
§5 provider-specific fields; §1-§3 numeric fields are identical across
providers.

```yaml
LiveCallPolicy:
  # §1 ADR-040 — timeout + retry + breaker
  connect_timeout_ms:     int    # required, [100, 10000],   default 2500
  read_timeout_ms:        int    # required, [1000, 30000],  default 8000
  max_retries:            int    # required, [0, 3],         default 1
  backoff_initial_ms:     int    # required, [50, 2000],     default 250
  backoff_max_ms:         int    # required, [initial, 5000], default 1000
  backoff_jitter_pct:     int    # required, [0, 100],       default 100
  breaker_threshold:      int    # required, [2, 20],        default 5
  breaker_window_s:       int    # required, [5, 300],       default 30
  breaker_half_open_s:    int    # required, [10, 600],      default 60

  # §3 ADR-040 — cost ceiling
  max_spend_usd_per_spawn:      float  # required, (0.0, 10.0],  default 0.50
  max_spend_usd_per_plan_5min:  float  # required, (0.0, 100.0], default 2.00
  max_debate_rounds:            int    # required, [1, 20],      default 5

  # §4 ADR-040 — credential lifecycle
  credential_env_var:           str        # required, non-empty
  credential_max_age_days:      int        # required, [7, 365], default 90
  credential_warn_age_days:     int        # required, [1, max_age), default 75
  leak_detection_patterns:      list[str]  # required, non-empty regex literals

  # §5 ADR-040 — provider-side scope
  scope:                         str             # enum: "chat_only" | "embeddings_only" | "chat_and_embeddings"
  data_retention_opt_out:        bool            # required; MUST be True for OpenAI embedding calls
  data_retention_opt_out_header: Optional[str]   # e.g. "OpenAI-Data-Retention: opt_out"; None if provider has no header mechanism

  # §6 ADR-040 — activation
  provider:                     str    # enum: "claude" | "gemini" | "openai" | "local"
  activation_env_var:           str    # required, non-empty, e.g. "CEO_LIVE_CLAUDE"
  fixture_fallback_enabled:     bool   # default True — short-circuits when activation_env_var absent
```

All fields required EXCEPT `data_retention_opt_out_header` which is
`Optional[str]` — `None` means the provider has no REST header
mechanism (Anthropic, Google) and `docs/rotation-log.md` operator
attestation is the compensating control.

## 2. Validation rules (`__post_init__`)

1. `connect_timeout_ms > 0` AND `read_timeout_ms > connect_timeout_ms`.
2. `max_retries <= 3` — hard upper bound prevents retry-storm
   amplification (Chaos CRITICAL-2).
3. `backoff_max_ms >= backoff_initial_ms` AND `backoff_max_ms <= 5000`.
4. `breaker_threshold >= 2` — single failure cannot open breaker.
5. `max_spend_usd_per_spawn > 0` AND `max_spend_usd_per_spawn <=
   max_spend_usd_per_plan_5min`.
6. `credential_warn_age_days < credential_max_age_days` strictly.
7. `scope` ∈ enum; any other value raises `ValueError` at construction.
8. If `provider == "openai"` AND scope includes embeddings, then
   `data_retention_opt_out == True` AND
   `data_retention_opt_out_header is not None` (Security §S1 + ADR-040 §5).
9. `leak_detection_patterns` non-empty; each element a valid `re` regex
   (compiled at construction).
10. `activation_env_var` matches `^CEO_LIVE_[A-Z_]+$`.

Failures raise `ValueError` at construction; the adapter refuses to
initialize rather than silently accept an invalid policy.

## 3. Failure classification enum

Terminal event `live_adapter_call_failed` field `failure_mode`:

```yaml
FailureMode:
  - auth_permanent        # 401/403 — breaker opens immediately
  - rate_limit            # 429 — transient, retried once
  - server_error          # 5xx — transient, retried once
  - connect_timeout       # transient
  - read_timeout          # transient
  - connection_refused    # transient
  - parse_error           # malformed JSON — permanent this call; does NOT count toward breaker
  - breaker_open          # fail-fast while breaker is open
  - budget_hard_stop      # §3 ceiling hit — does NOT retry
  - scope_misconfigured   # e.g. OpenAI embedding without opt-out header
```

Every adapter terminal failure MUST map to exactly one value. New
values require a SPEC minor-version bump AND an ADR-040 amendment.

## 4. Referenced by

- ADR-040 §1, §2, §3, §4, §5, §6, §7 — all field definitions trace here.
- `_lib/adapters/live/_policy.py` — implementation.
- `_lib/adapters/live/_breaker.py` — consumes breaker fields.
- `_lib/adapters/live/_transport.py` — consumes timeout/retry/backoff.
- `tests/chaos/test_live_adapter_failure_injection.py` — validates §2 + §3.
- `tests/integration/test_live_adapter_smoke.py` — validates §6 activation.

## 5. Changelog

- **1.0.0-rc.1** (2026-04-14, PLAN-012 Phase 1 D3.2): initial
  publication. Codifies ADR-040 §1-§6 as a frozen-dataclass contract.
