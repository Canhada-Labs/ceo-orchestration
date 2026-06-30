# Provider Capability Matrix

**Source:** PLAN-011 Phase 1, consensus §H2 / §H9.
**Authoritative per-adapter source:** `.claude/hooks/_lib/adapters/<name>.py`
`CAPABILITIES` dict.
**Last refreshed:** 2026-06-15 (claude `max_context` 200k→1M per PLAN-137 A4 gate; see `docs/provider-pricing.md` → Long-context pricing section. The `max_context` column is an informational approximation — it is NOT a structured `CAPABILITIES` field, so this edit does not touch any adapter or trip the drift/parity detector.)

This matrix documents each shipped adapter's protocol-level capabilities.
A field absent from this matrix is a **bug**, not a feature — the drift
detector test (`test_adapter_drift_detector.py`) and the parity test
(`test_adapters_parity.py`) reject PRs that add fields without updating
this table.

> **Provenance rule.** Values marked `N/A` mean the provider does not
> document or expose the capability at all. Values marked `advisory`
> mean the provider supports it on paper but reliability varies by
> model/version. `Y` / `N` are hard guarantees.

## Matrix

| Adapter | `streaming_tool_use` | `json_mode` | `function_calling` | `system_prompt_slot` | `max_context` (tokens, approx) | `latency_ms_p50` (hook roundtrip) |
|---|---|---|---|---|---|---|
| **claude** | Y | Y | Y | Y | 1M (Opus 4.6+/Sonnet 4.6/Fable 5); 200k (Haiku 4.5) | ~2 ms |
| **gemini** | N | advisory | Y | Y | 1M (2.0 Pro) | N/A (stub) |
| **openai** | Y | Y | Y | Y | 128k (GPT-4o) / 200k (o1) | N/A (gateway) |
| **local** | N | N | Y | Y | varies by model (Llama 3.1: 128k) | N/A (stub) |

### Notes per column

- **`streaming_tool_use`** — Provider streams partial tool-call deltas as
  the LLM decides to invoke a tool. Claude Code and OpenAI Chat
  Completions both stream; Gemini and local runtimes typically do not.
- **`json_mode`** — Strict JSON output guarantee. Claude and OpenAI
  guarantee; Gemini marks it advisory because the feature flag exists
  but older models ignore it; local runtimes are `False` because JSON
  mode on Ollama / llama.cpp is model-dependent and not enforceable.
- **`function_calling`** — Native structured tool-call API. All 4
  adapters support a function-calling surface; wire shapes differ
  (normalized to the same canonical envelope — see
  `SPEC/v1/normalized_envelope.schema.md`).
- **`system_prompt_slot`** — Provider accepts a dedicated system role.
  All 4 support this; the canonical envelope surfaces it in
  `raw_payload["system_prompt"]` per SPEC §1.3.
- **`max_context`** — informational, not tested. Shown to help operators
  pick an adapter for long-context workloads.
- **`latency_ms_p50`** — HOOK round-trip only (stdin parse → stdout
  decision). Provider-side LLM latency is out of scope. Measured on
  the macOS dev baseline (PLAN-010 Phase 2 `hook-profiler.py`). Stubs
  and gateways show `N/A` because there is no deployment to measure.

## Known gaps (per adapter)

### claude

No capability gaps — Claude Code is the default production adapter and
its field set is the reference for canonical envelope parity.

### gemini

- Real wire shape **not captured** as of this writing. Adapter
  ships as a shape-probing stub. See
  `.claude/hooks/tests/fixtures/adapters/gemini/GAPS.md`.
- `json_mode` marked `advisory` — behavior varies by model version.

### openai

- Adapter assumes a **gateway synthesizes** the hook payload from
  OpenAI Chat Completions or Responses API traffic. There is no
  OpenAI-published hook protocol analogous to Claude Code's
  PreToolUse / PostToolUse envelope.
- No per-hook capture fixture beyond the shipped 2 (one per wire
  shape). Production use requires the gateway layer.

### local

- Adapter assumes a local harness emits either Ollama chat-API
  tool-call shape or a minimal `{tool, tool_input}` envelope.
- `json_mode: False` because most local runtimes accept the flag but
  emit invalid JSON ~1-5% of the time; governance cannot depend on it.

## Drift invariant

`test_adapter_drift_detector.py` parses:

1. The `NormalizedEvent` dataclass in `.claude/hooks/_lib/contract.py`.
2. The `§1.1 field inventory` table in
   `SPEC/v1/normalized_envelope.schema.md`.
3. Every `NormalizedEvent(...)` call site in `claude.py`.

Any field populated by any adapter that is not documented in SPEC §1.1
fails CI. Any field documented in SPEC §1.1 that is not on the dataclass
also fails CI.

## Updating this matrix

When adding a new adapter or extending an existing one:

1. Add the module under `.claude/hooks/_lib/adapters/<name>.py`.
2. Export `ADAPTER_VERSION: str` and `CAPABILITIES: dict` per
   `SPEC/v1/adapters.schema.md §2`.
3. Add a row to this matrix with honest `N/A` / `advisory` / `Y` / `N`
   values. Do not guess.
4. Register in `contract.KNOWN_ADAPTERS` + `adapters.__init__.ADAPTER_REGISTRY`.
5. Ship ≥2 input fixtures under `tests/fixtures/adapters/<name>/in/`.
6. Add a normalized counterpart fixture for each `in/` scenario under
   `tests/fixtures/normalized/` (adapter-agnostic canonical envelope).
7. Run `python3 -m pytest .claude/hooks/tests/test_adapters_parity.py -v`
   and fix any parity breaks before merging.

## References

- `SPEC/v1/normalized_envelope.schema.md` — the canonical envelope.
- `SPEC/v1/adapters.schema.md` — ABI contract.
- `docs/adapters.md` — swap guide + troubleshooting.
- ADR-008 — Hook Adapter Layer (foundation).
- ADR-012 — Cross-adapter golden fixtures.
- ADR-028 — Multi-LLM canonical envelope parity (Sprint 11).
- PLAN-011 consensus.md §H2 / §H9 / §H17.
