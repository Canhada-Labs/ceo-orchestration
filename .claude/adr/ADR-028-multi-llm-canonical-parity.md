# ADR-028: Multi-LLM Canonical Envelope Parity

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per Sprint 11 Phase 1 (envelope + adapters shipped)) (2026-04-14)
**Date:** 2026-04-14
**Supersedes:** none
**Extends:** ADR-008 (Hook Adapter Layer), ADR-012 (Cross-adapter golden fixtures)
**Decision drivers:**
- Consensus finding §H2 (PLAN-011 debate round 1): byte-identity
  across provider wire shapes is a fiction.
- Consensus §H3: Phase 4 (self-improving skills) cannot execute
  before the canonical envelope is locked down.
- Consensus §H8: credential hygiene must be normative, not folklore.
- Consensus §H9: adapter ABI was implicit; hook authors cannot port
  to a new provider without re-reading existing adapter source.
- Consensus §H17: full adapter matrix on every PR is CI budget
  overrun. Rotation + paths-filter gets costs under control.

---

## Context

ADR-008 introduced the Hook Adapter Layer (HAL): hooks read a
`NormalizedEvent` and emit a `Decision` via an adapter module that
translates the provider's wire shape. At the time of ADR-008 only the
`claude` adapter was shipped, and `gemini` followed in Sprint 6 as a
stub.

Approaching Sprint 11 with plans to ship `openai` and `local` adapters
plus a self-improving skill proposal system (PLAN-011 Phase 4) that
MUST work across providers, the debate round 1 consensus surfaced
several cross-cutting problems:

1. **Byte-identity as an invariant is false** (§H2). One provider's
   streaming `tool_use` is another's `function_call` is another's
   inline JSON. Any test that compares provider-specific wire bytes
   across adapters will never converge. The realistic invariant is
   **canonical envelope parity**: all adapters produce the same
   `NormalizedEvent` field values (for overlapping capabilities) from
   semantically-equivalent payloads.

2. **Adapter ABI is implicit** (§H9). Hook authors infer the
   contract from the existing adapter source. A formal ABI spec
   prevents silent breakage when adding a fourth, fifth, sixth
   adapter.

3. **Credential hygiene is not enforced** (§H8). Some adapters echoed
   the full `JSONDecodeError.doc` into `parse_error`, which can leak
   secrets embedded in malformed payloads.

4. **CI cost escalates quadratically** (§H17). Running the full
   adapter matrix on every PR was projected at +2000 min/week.

## Decision Drivers

- **Ship multiple adapters (§H2 rename).** Canonical envelope parity,
  not byte-identity, is the invariant. Each adapter normalizes to the
  same `NormalizedEvent` shape.
- **Make the ABI explicit.** Adapter modules are a stable contract,
  not folklore. Ship `SPEC/v1/adapters.schema.md`.
- **Enforce credential hygiene in tests.** Per adapter, a test class
  asserts `parse_error` and side-channel fields never echo secrets.
- **Cap CI cost.** Paths-filter + PR rotation + main-only full matrix.

## Options Considered

### Option A: Ship stubs forever, defer real parity

- **Pros:** zero cost now.
- **Cons:** Phase 4 (skill patches) cannot verify cross-provider
  behavior; future IDE adopters have no path forward; the neutral
  contract stays theoretical.

### Option B: Pursue byte-identity across provider wire shapes

- **Pros:** appealing invariant — "every provider looks the same".
- **Cons:** fundamentally impossible. OpenAI's Chat Completions
  function-calling encodes `arguments` as a JSON-encoded STRING;
  Ollama's native `arguments` is a JSON OBJECT; Gemini's shape is
  not even published. A fixture comparison at the raw-bytes layer is
  permanently red.

### Option C: Canonical envelope parity (CHOSEN)

- **Pros:**
  - Real, achievable invariant: every adapter produces the same
    `NormalizedEvent` field values (for overlapping capabilities).
  - Explicit capability matrix documents gaps honestly
    (`streaming_tool_use=False` for Gemini, `json_mode=False` for
    local, etc.).
  - Drift detector test prevents silent schema divergence.
  - Credential hygiene test locks down H8 contractually.
- **Cons:**
  - 4 adapters now in KNOWN_ADAPTERS means 4x test surface.
  - PR rotation makes individual PR runs less thorough (by design —
    the remaining adapters run nightly).

## Decision

**Option C** — Canonical envelope parity.

### What ships in PLAN-011 Phase 1

1. `SPEC/v1/normalized_envelope.schema.md` — documents the canonical
   `NormalizedEvent` field set as a grep-able table (used by drift
   detector).
2. `SPEC/v1/adapters.schema.md` — adapter ABI: required module
   constants (`ADAPTER_VERSION`, `CAPABILITIES`), required functions
   (`read_event`, `read_post_event`, `write_decision`, `emit_decision`),
   error shape, credential hygiene, versioning + deprecation policy.
3. `.claude/hooks/_lib/adapters/gemini.py` — rewritten. Retains
   stub-fallback shape probing; adds `ADAPTER_VERSION` and
   `CAPABILITIES`; tightens `parse_error` strings to strip
   `JSONDecodeError.doc` (H8 compliance).
4. `.claude/hooks/_lib/adapters/openai.py` — new. Handles Chat
   Completions (JSON-string `arguments`) and Responses API (object
   `tool_input`) wire shapes.
5. `.claude/hooks/_lib/adapters/local.py` — new. Handles Ollama
   chat-API tool-calls and a minimal `{tool, tool_input}` envelope.
6. `test_adapters_parity.py` — 35 tests. Cross-adapter parity on
   overlap fields, metadata, write-decision shape, fail-open.
7. `test_adapter_drift_detector.py` — 7 tests. Compares dataclass
   field set ↔ SPEC field table ↔ claude.py populated fields.
8. `test_adapter_never_echoes_key.py` — 17 tests. Five secret
   patterns across three adapters; `parse_error` + `tool_name` MUST
   never leak them.
9. `.github/workflows/validate.yml` — new `adapter-matrix` job with
   paths-filter, full-on-main, rotating-on-PR strategy per §H17.
10. `docs/provider_capability_matrix.md` — new. Per-adapter matrix
    with honest `N/A` / `advisory` / `Y` / `N` values.
11. `docs/adapters.md` — amended. Documents openai + local + new
    constants + new CI strategy.

### What does NOT ship

- Automatic capture of real Gemini CLI hook payloads (still a stub).
- Nightly cron scheduling of full `openai` + `local` matrix — tracked
  for a follow-up commit in PLAN-011 closeout; the matrix-job wiring
  ships, only the cron trigger is deferred.
- A `claude.py` refactor to add `ADAPTER_VERSION` + `CAPABILITIES`
  module constants. Reason: Phase 1 file assignment restricted edits
  to the three new adapters. Claude's capabilities are documented in
  SPEC and the matrix, and the drift detector verifies its envelope
  field production. A minor commit in PLAN-011 Phase 13 closeout can
  add the constants for symmetry without breaking Phase 1 scope.

### Claude capabilities (documented, not code-enforced in Phase 1)

Per `docs/provider_capability_matrix.md`:

```
claude: {
    streaming_tool_use: True,
    json_mode: True,
    function_calling: True,
    system_prompt_slot: True,
}
```

## Consequences

### Positive (+)

- Phase 4 (self-improving skills, PLAN-011 group B) unblocked: the
  canonical envelope is locked, so skill-patch proposals can be
  tested in a provider-agnostic way.
- Future adapters ship faster: the ABI is explicit, the test
  scaffolding (parity + drift + credential) is reusable by inclusion
  in `NEW_ADAPTERS`.
- Credential hygiene becomes a regression gate rather than a review
  hope.
- CI cost stays under control: ~500 min/week additional vs ~2000
  naive.

### Negative (-)

- `claude.py` does not (yet) carry `ADAPTER_VERSION`/`CAPABILITIES`
  constants — SPEC §2 calls them MUST but Phase 1 scope excluded
  editing it. Closure work in Phase 13.
- Fixture duplication: each new adapter scenario needs a matching
  normalized fixture. Semi-automated (see `bash_minimal.json` shared
  across adapters), but not fully deduped.
- PR-time coverage on rotating adapters is probabilistic. A malicious
  commit targeting a specific adapter could land in a PR cycle that
  doesn't rotate to that adapter. Nightly cron (deferred) closes the
  window within 24h.

### Neutral (~)

- `KNOWN_ADAPTERS` grows from 2 to 4, but the registry machinery was
  already in place.
- SPEC v1 stays at the same major (adapters.schema.md is additive).

## Blast Radius

**L2** — Cross-module contract change affecting:
- `.claude/hooks/_lib/contract.py` (KNOWN_ADAPTERS list)
- `.claude/hooks/_lib/adapters/` (gemini rewrite, openai + local new)
- `.claude/hooks/_lib/adapters/__init__.py` (ADAPTER_REGISTRY)
- `.claude/hooks/tests/` (3 new test files)
- `.claude/hooks/tests/fixtures/adapters/{openai,local}/` (new)
- `.claude/hooks/tests/fixtures/normalized/` (new canonical fixtures)
- `.github/workflows/validate.yml` (new adapter-matrix job)
- `SPEC/v1/` (2 new files)
- `docs/adapters.md` (amended)
- `docs/provider_capability_matrix.md` (new)

**Reversibility:** HIGH — all changes are additive. Rolling back to
pre-Phase 1 is:
1. Revert the gemini.py diff (restores prior stub shape).
2. Delete openai.py, local.py, __init__.py registry, all new SPECs,
   docs, fixtures, tests.
3. Revert KNOWN_ADAPTERS to `["claude", "gemini"]`.
4. Remove `adapter-matrix` job from validate.yml.

No migration path touches existing hooks or Claude adapter behavior.

## Amendment to ADR-008

ADR-008's §Decision "What the contract does NOT ship" clause
"Gemini CLI adapter (deferred to Sprint 5 — pending real user)" and
"Codex CLI adapter (deferred indefinitely)" are preserved. This ADR
adds the v1.3 extension:

> **Sprint 11 update (PLAN-011 Phase 1):** the HAL is extended to four
> adapters — `claude`, `gemini`, `openai`, `local`. Each now publishes
> `ADAPTER_VERSION` and `CAPABILITIES` per `SPEC/v1/adapters.schema.md`.
> Gemini remains a stub; OpenAI and Local are gateway-synthesized.
> Real byte-identity-across-adapters is explicitly rejected as an
> invariant; the new invariant is canonical envelope parity.

## References

- PLAN-011 §Phase 1 — Multi-LLM canonical envelope parity
- PLAN-011/debate/round-1/consensus.md §H2, §H3, §H8, §H9, §H17
- ADR-008 — Hook Adapter Layer (foundation)
- ADR-012 — Cross-adapter golden fixtures
- SPEC/v1/normalized_envelope.schema.md
- SPEC/v1/adapters.schema.md
- docs/provider_capability_matrix.md
- docs/adapters.md

## Enforcement commit

`4b4bb92580f0` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
