---
name: Order Routing
description: Order routing for high-frequency trading systems — venue selection, IOC/FOK semantics, child-order slicing, retry vs. cancel-on-error policies, and audit-trail completeness for surveillance.
trigger: Any work that touches the order send / replace / cancel paths, venue selection, or order-message construction. Pair with `latency-budgets` whenever the routing change affects the hot path.
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: trading-hft
priority: 2
risk_class: high
stack: [python, cpp]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: true, priority: 2}
  generic: {active: false, priority: 10}
activation_triggers:
  - {event: file-edit, regex: "(?i)order.?routing|venue|smart.?order|sor"}
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/order-routing/**"
  - "**/orders/**"
  - "**/venues/**"
  - "**/routing/**"
  - "**/sor/**"
---

# Order Routing — Trading-HFT skill

> Owned by **Diane Okafor** (Head of Trading Systems) with VETO from
> the Latency Architect (latency budgets) and Kill-Switch Operator
> (cancel paths).

## When to load this skill

- Adding or modifying a venue adapter (FIX session, native API)
- Changing order-message construction (TIF, side, price, size, tags)
- Modifying retry / fallback / re-route logic
- Tuning child-order slicing for parent order types (TWAP, VWAP, IS)
- Reviewing post-trade audit log completeness

## Core rules

1. **Idempotent client order IDs.** Every outbound order carries a
   `cl_ord_id` derived from `(strategy_id, symbol, sequence_number)`.
   Re-sends MUST reuse the same `cl_ord_id` so the venue dedupes;
   replacements MUST carry a new `cl_ord_id` AND reference the prior
   one via `orig_cl_ord_id`.
2. **TIF defaults are explicit.** Never default a Time-In-Force
   silently. Code MUST require the caller to specify `IOC`, `FOK`,
   `DAY`, `GTC`, etc. Defaulting to `DAY` because the field was
   omitted has caused multi-million-dollar incidents.
3. **Cancel-on-disconnect (COD) is opt-out, not opt-in.** Every
   session MUST request COD from the venue at logon. Removing COD
   requires VETO from the Kill-Switch Operator.
4. **Audit before send.** The audit log entry MUST be written and
   flushed (or queued to a non-blocking ring buffer with a
   guaranteed-flush sidecar) BEFORE the wire send. No "fire and forget"
   sends without audit evidence.
5. **No side-effects in retry handlers.** Retry / re-route logic
   must not mutate strategy state; the only side effect is the new
   wire message. State updates happen on the venue ack / reject.

## Anti-patterns to detect

- **Floating-point price arithmetic.** Prices are always integer
  ticks (quantity × tick_size), or a domain-specific Decimal type.
  Float = nondeterministic = audit failure.
- **Implicit re-pricing on replace.** A replace with no new price MUST
  use `same_price = true`, never `price = old_price + 0.0`.
- **Per-order `time.time()` calls in the hot path.** Use a monotonic
  cached clock with a documented update cadence; reading the wall
  clock per-order is a syscall storm.
- **Logging the full payload synchronously.** Log only the bytes
  needed for surveillance (cl_ord_id, venue, side, qty, price,
  tags) and write to a lock-free ring; the formatter is a sidecar.
- **String concatenation for FIX messages.** Use a typed builder.
  Manual concat hides field-tag bugs that surveillance later flags.

## Output checklist (every order-routing PR must satisfy)

- [ ] `cl_ord_id` derivation documented or tested
- [ ] TIF is explicit in every code path (no language defaults)
- [ ] Cancel-on-disconnect verified at session-logon test
- [ ] Audit-write happens before wire-send (or queued via guaranteed
      sidecar with proof of latency budget)
- [ ] No `time.time()` / `clock_gettime` syscalls in the hot loop
- [ ] No float prices anywhere on the routing path
- [ ] Surveillance taps untouched (or amended with Compliance VETO sign-off)

## References

- ADR-013 (this squad)
- `latency-budgets` skill (always pair with this skill on hot-path edits)
- `kill-switches` skill (cancel paths)
- Universal `state-machines-and-invariants` skill (order state machine)
