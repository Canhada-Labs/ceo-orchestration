---
id: ADR-123
title: BatchClaudeLiveAdapter — canonical source for batch + streaming dispatch
status: ACCEPTED
proposed_at: 2026-05-13
proposed_by: CEO (PLAN-090 Wave B — R1 6-archetype + R2 Codex MCP iter-3 ACCEPT 2026-05-13)
accepted_at: 2026-05-13
accepted_by: Owner @Canhada-Labs (0000000000000000000000000000000000000000) — PLAN-090 closeout ceremony S118 (v1.24.0)
related_plans: [PLAN-085, PLAN-086, PLAN-088, PLAN-090]
related_adrs: [ADR-040, ADR-052, ADR-064, ADR-118, ADR-122, ADR-124, ADR-125]
veto_floor: ADR-052 (security-engineer + code-reviewer + performance-engineer + qa-architect)
codex_pair_rail: required (PLAN-090 R2 thread 019e212f-f85f-7fd2-a73a-29713ea9cc1f)
tags: [adapter, batch, streaming, anthropic, cost-optimization, side-channel]
authorization: PLAN-090 closeout ceremony
---

# ADR-123 — `BatchClaudeLiveAdapter` is the canonical source for batch + streaming dispatch

## §1. Context

PLAN-088 W4.2 was scoped to migrate a `BatchClaudeLiveAdapter` from
`staging/` to canonical at `_lib/adapters/live/claude_batch.py`. Wave B
audit (PLAN-090 §4 B.1) confirmed PLAN-088's `staging/` subdirectory does
**not** exist on disk — only wave sentinels live under
`.claude/plans/PLAN-088/`. Wave B is therefore a **green-field
implementation** with ABI parity against the synchronous
`ClaudeLiveAdapter` at `_lib/adapters/live/claude.py` (PLAN-085 Wave
C.1-wired).

This ADR fixes the canonical location, the inheritance contract, and the
audit / cost-attribution surface for the new adapter.

## §2. Decision

`BatchClaudeLiveAdapter` lives at
`.claude/hooks/_lib/adapters/live/claude_batch.py` and inherits from
`ClaudeLiveAdapter` (same provider, same activation gate, same allowlist
gate, same credential lifecycle gate).

It extends the synchronous baseline with two new public methods:

- `batch_call(*, requests: List[Dict[str, Any]]) -> List[LiveAdapterResult]`
  — Anthropic Messages Batches API
  (`https://api.anthropic.com/v1/messages/batches`). 50 % cost discount
  per AUTO-08 rationale. Returns ordered list aligned with input. Emits
  ONE `batch_dispatched` event with aggregate `tokens_total`.
- `stream_call(*, messages, model, max_tokens=1024, thinking=None) ->
  Iterator[Tuple[Optional[str], Optional[LiveAdapterResult]]]` —
  streaming via SSE on `/v1/messages?stream=true`. Yields
  `(token, None)` for each delta then `(None, LiveAdapterResult)` as the
  final tuple.

The class is exposed via `.claude/hooks/_lib/adapters/__init__.py` (a
re-export attribute alongside the existing `ClaudeLiveAdapter`).

## §3. Migration

PLAN-090 migrates ONE canonical benchmark caller:

- `.claude/scripts/run-skill-benchmark.py` — switch from
  `ClaudeLiveAdapter.call(...)` to
  `BatchClaudeLiveAdapter.batch_call(requests=...)` when the benchmark
  payload has ≥ 2 prompts. Single-prompt benchmarks stay on the
  synchronous adapter (no cost discount over 1 request).

Other callers (TBD if any) remain on the synchronous adapter. The
synchronous adapter is **not deprecated** — it is the single-prompt
canonical surface and remains valid for low-cardinality dispatch.

## §4. Side-channel discipline (security-engineer P0 fold)

`stream_call` emits per-token audit events ONLY when
`CEO_AUDIT_STREAM_VERBOSE=1` is set in the parent shell (S110 pattern).

- EXACT MATCH `=1` only (truthiness footgun mirror)
- PARENT-SHELL ONLY (never accepted via stdin or tool-param)
- Token bucket: 10 burst capacity + 5/min sustained refill (per-persona)
- Aggregate ceiling: 20/min across all personas in a session
- On rate-cap: drop tokens silently; emit ONE `streaming_rate_capped`
  summary with `dropped_count` at stream end
- `audit-stream.jsonl` created with mode `0600` (owner-only)

DEFAULT mode (env unset or any value other than `=1`): emit ONE
aggregate `batch_dispatched` event with `tokens_total` at stream end.
Closes the side-channel volumetric leak.

## §5. ATLAS bindings

| Action | Technique | Rationale |
|---|---|---|
| `batch_dispatched` | (none — cost-optimization telemetry) | PLAN-088 W4.2 baseline; atlas_technique=null per §1.5 |
| `streaming_token_yielded` | `T1071` (Application Layer Protocol — exfil channel monitor) | R1 TDE P1 fold |
| `streaming_rate_capped` | (none — meta-event) | summary emit; ATLAS not applicable |

`batch_dispatched` and `streaming_token_yielded` share the same caller
discriminator (`request_class: "batch" | "streaming"`) for downstream
SOC consumption.

## §6. ABI parity invariants

`BatchClaudeLiveAdapter` is a strict subclass of `ClaudeLiveAdapter`.
Test row `TestAbiParityWithClaudeAdapter` asserts:

- `provider_name == "anthropic"` (inherited verbatim)
- `__init__` rejects `policy.provider != "claude"` (inherited)
- `call(...)` synchronous path works as expected (inherited verbatim)
- `policy` / `_spawn_tracker` / `_breaker` are instance attrs (inherited)

If a future refactor breaks any of these, `pytest
test_claude_batch_adapter.py::TestAbiParityWithClaudeAdapter` fails the
CI gate.

## §7. Cost

- Implementation: ~250 LoC `_lib/adapters/live/claude_batch.py` + ~10
  LoC `_lib/adapters/__init__.py` extension = ~260 LoC net-new.
- Test suite: ~30 tests at `test_claude_batch_adapter.py` + ~6 tests at
  `test_streaming_rate_cap.py` + ~3 tests at
  `test_audit_stream_verbose_protection.py` = ~39 NEW tests.
- Cost saving: 50 % per benchmark cycle for multi-prompt batches
  (Anthropic API price-list constant).

## §8. Sunset trigger

This ADR is superseded if:

- Anthropic deprecates the `/v1/messages/batches` endpoint (no
  in-product migration path observed as of 2026-05-13).
- A v2.0 transport rewrite consolidates `_lib/adapters/live/*.py` into
  a single multi-mode adapter (RESERVED per ADR-126 §Part 7).
