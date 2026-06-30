# Hook Adapter Layer — IDE Adapters

The ceo-orchestration framework's hooks communicate with the host IDE
via the **Adapter Layer** (ADR-008). A hook reads a `NormalizedEvent`
via `claude_adapter.read_event()` (or the adapter for whichever IDE
sent the payload) and emits a `Decision` via the same adapter's
`emit_decision()`. Hooks stay IDE-agnostic; adapters translate.

## Available adapters

### `claude` (default) — PRODUCTION

- Module: `.claude/hooks/_lib/adapters/claude.py`
- Parity: FULL. Exercised by all 6 hooks + 250+ tests.
- Wire shape: Claude Code `PreToolUse` / `PostToolUse` JSON envelope
  documented in `SPEC/v1/hook-io.schema.md`.
- Output shape: single-line `{"decision":"allow|block","reason":"...","systemMessage":"...","message":"..."}` on stdout; exit 0.

### `gemini` — STUB (Sprint 6 Phase 2a + Sprint 11 ABI conformance)

- Module: `.claude/hooks/_lib/adapters/gemini.py`
- Version: `ADAPTER_VERSION = "1.0.0-rc.1"`
- Parity: STUB. Probes common field-name conventions; real-parity
  deferred until a live Gemini CLI hook payload is captured.
- Status: do NOT use in production; advisory path only.
- Gap log: `.claude/hooks/tests/fixtures/adapters/gemini/GAPS.md`
- Capabilities: see `docs/provider_capability_matrix.md`.
- Test coverage: 22 tests in `test_adapter_gemini.py` + parity/drift/
  credential coverage in `test_adapters_parity.py`,
  `test_adapter_drift_detector.py`, `test_adapter_never_echoes_key.py`.

### `openai` — GATEWAY-SYNTHESIZED (Sprint 11 PLAN-011 Phase 1)

- Module: `.claude/hooks/_lib/adapters/openai.py`
- Version: `ADAPTER_VERSION = "1.0.0-rc.1"`
- Parity: Handles both Chat Completions (tool_calls with JSON-encoded
  `arguments`) and Responses API (top-level `tool_name` / `tool_input`)
  wire shapes. Auto-detected.
- Use case: **gateway deployments** that wrap OpenAI traffic and feed
  a synthesized hook payload via stdin. OpenAI does not ship a hook
  protocol; the gateway bridges the two.
- Capabilities: see `docs/provider_capability_matrix.md`.
- Test coverage: parity + drift + credential (`test_adapters_parity.py`,
  `test_adapter_drift_detector.py`, `test_adapter_never_echoes_key.py`).

### `local` — LOCAL LLM (Sprint 11 PLAN-011 Phase 1)

- Module: `.claude/hooks/_lib/adapters/local.py`
- Version: `ADAPTER_VERSION = "1.0.0-rc.1"`
- Parity: Handles Ollama chat API (`message.tool_calls` with native
  object or JSON-string `arguments`) and a minimal
  `{tool, tool_input}` envelope for test harnesses.
- `json_mode = False` — local runtimes accept the flag but emit
  invalid JSON often enough that governance cannot depend on it.
- Capabilities: see `docs/provider_capability_matrix.md`.
- Test coverage: parity + drift + credential.

### `codex` — NOT IMPLEMENTED

- Deferred beyond Sprint 11. Low demand signal.
- Add when a real Codex CLI user appears.

## Selecting an adapter

At hook runtime, the adapter is resolved via the **`CEO_HOOK_ADAPTER`**
environment variable. Precedence:

1. Explicit env-var (`CEO_HOOK_ADAPTER=<name>`) → if name is in
   `KNOWN_ADAPTERS`, use it.
2. Absent or empty env-var → `DEFAULT_ADAPTER` (`claude`).
3. Unknown name → silent fallback to `DEFAULT_ADAPTER`. No error to
   stderr (observability via `audit_emit`, not stderr).

### For Claude Code users (default path)

No env-var needed. Everything just works.

### For Gemini CLI early adopters

```bash
export CEO_HOOK_ADAPTER=gemini
# Launch your Gemini CLI
# Hooks now dispatch to adapters/gemini.py (stub)
```

Reminder: the Gemini adapter is a **stub**. Field probes may misalign
with real Gemini wire format. File an issue with a captured payload
to accelerate real-parity work.

### For OpenAI gateway operators

```bash
export CEO_HOOK_ADAPTER=openai
# Your gateway forwards tool-call shapes to the hook via stdin
# Hooks dispatch to adapters/openai.py (supports Chat Completions +
# Responses API)
```

The adapter auto-detects the wire shape per payload. Both
`{"tool_calls":[{"function":{"name":...,"arguments":"..."}}]}` and
`{"tool_name":..., "tool_input":{...}}` work.

### For local-LLM harnesses

```bash
export CEO_HOOK_ADAPTER=local
# Your harness emits Ollama chat API shape or minimal {tool, tool_input}
# Hooks dispatch to adapters/local.py
```

JSON mode is NOT guaranteed on local runtimes — emitters should
sanitize their output and fall back to the minimal envelope when the
model deviates.

### In CI

The framework's `.github/workflows/validate.yml` runs two jobs:

1. **`validate`** — existing governance job. Runs hook tests twice
   (once with `CEO_HOOK_ADAPTER=claude`, once with `CEO_HOOK_ADAPTER=gemini`)
   to confirm dispatch stays green.
2. **`adapter-matrix`** — PLAN-011 Phase 1 cost-capped matrix:
   - **Push to main**: full matrix `[claude, gemini, openai, local]`.
   - **Pull request**: `claude` + one rotating non-claude adapter
     (selected by `PR number % 3`). Skipped entirely unless the PR
     touches `.claude/hooks/_lib/adapters/**`, `validate.yml`, or
     the SPEC v1 envelope/adapter schemas.
   - **Nightly**: (scheduled cron — out of scope for Phase 1, tracked
     for a follow-up commit) full `openai` + `local` matrix to catch
     drift.

Target cost increase: ~500 min/week vs ~2000 for running the full
matrix on every PR. See PLAN-011 consensus §H17.

## Implementing a new adapter

To add a new adapter `foo`:

1. **Create module** — `.claude/hooks/_lib/adapters/foo.py` implementing:
   - `ADAPTER_VERSION: str` (SemVer, e.g. `"1.0.0-rc.1"`)
   - `CAPABILITIES: dict` with required keys per
     `SPEC/v1/adapters.schema.md §2.2`
   - `read_event(stream=None, phase="PreToolUse") -> NormalizedEvent`
   - `read_post_event(stream=None) -> NormalizedEvent` (convenience)
   - `write_decision(decision: Decision) -> str`
   - `emit_decision(decision: Decision, stream=None) -> None`
2. **Register** in `_lib/contract.py` and `_lib/adapters/__init__.py`:
   ```python
   KNOWN_ADAPTERS: List[str] = ["claude", "gemini", "openai", "local", "foo"]
   ADAPTER_REGISTRY: List[str] = ["claude", "gemini", "openai", "local", "foo"]
   ```
3. **Ship fixtures** — capture real `foo` hook payloads to
   `.claude/hooks/tests/fixtures/adapters/foo/in/*.json` (at least 2);
   add matching normalized expectations to
   `fixtures/normalized/<scenario>.json`.
4. **Write tests** — at minimum:
   - Add coverage to `test_adapters_parity.py` including foo in the
     NEW_ADAPTERS list.
   - Add a dedicated `test_adapter_foo.py` with ≥15 probe / fallback /
     phase / fail-open cases.
5. **Document** — extend this file + add row to
   `docs/provider_capability_matrix.md`. Write an ADR if there are
   material trade-offs (e.g. output shape deviates from Claude's
   single-line JSON convention).
6. **Credential hygiene check** — add a class to
   `test_adapter_never_echoes_key.py` per SPEC §4.1 covering
   `sk-...`, `AKIA...`, JWT, Bearer, and env-var-leak shapes.

## Contract invariants (all adapters must uphold)

- **Fail-open on parse error.** Malformed stdin → NormalizedEvent with
  `parse_error` set; hook emits `allow` (or nothing, for PostToolUse
  observers). No hook may exit non-zero on infrastructure bugs.
- **Phase is authoritative.** Hooks declare phase via
  `read_event(..., phase=...)` or `read_post_event()`. Adapters MUST
  preserve the declared phase even when payload shape is ambiguous.
- **Byte-fidelity on write.** `write_decision` output must be a
  single-line JSON with key order: `decision`, `reason` (if block +
  reason set), `systemMessage`, `message`, then `extra` keys. The
  Claude adapter's test suite (`test_hook_byte_fidelity`) enforces
  this for existing hooks; new adapters should ship comparable
  coverage.

## References

- ADR-008 — Hook Adapter Layer foundation
- ADR-012 — Cross-adapter golden fixtures
- ADR-014 — Hook migration batch policy (Sprint 6)
- ADR-028 — Multi-LLM canonical envelope parity (Sprint 11)
- PLAN-006 §Phase 2a — Gemini stub scope
- PLAN-011 §Phase 1 — canonical envelope parity
- SPEC/v1/hook-io.schema.md — Claude wire format
- SPEC/v1/normalized_envelope.schema.md — canonical envelope
- SPEC/v1/adapters.schema.md — adapter ABI
- docs/provider_capability_matrix.md — per-provider capability gaps
