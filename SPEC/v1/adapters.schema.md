# SPEC/v1/adapters.schema.md — Hook adapter ABI contract

**Version:** 1.0.0-rc.1 (PLAN-011 Phase 1, Sprint 11)
**Status:** PROPOSED (additive; extends ADR-008 Hook Adapter Layer)
**Authoritative source:** `.claude/hooks/_lib/adapters/<name>.py` per adapter

---

## 0. Purpose

This document specifies the **Application Binary Interface** (ABI) that
every hook adapter module in `.claude/hooks/_lib/adapters/` MUST
implement. Consensus finding §H9 (PLAN-011 debate round 1) made the
adapter ABI implicit — this document makes it explicit and normative.

Companion documents:
- `normalized_envelope.schema.md` — the canonical envelope each
  adapter produces.
- `hook-io.schema.md` — the Claude-specific wire shape (legacy).

---

## 1. Module layout

Each adapter is a single Python module at
`.claude/hooks/_lib/adapters/<name>.py`. The adapter package
(`__init__.py`) contains only package-level helpers — no adapter code.

Adapters MUST be:

- **stdlib-only** (ADR-002). No external dependencies.
- **Python >= 3.9 compatible**. `from __future__ import annotations`
  required. `typing.Optional/Union` at runtime (no PEP-604 `X|Y` except
  in string type hints).
- **fail-open**. Any parse failure returns a NormalizedEvent with
  `parse_error` set; never raises to the hook.
- **pure** — no network I/O, no disk I/O except stdin/stdout streams
  passed in.

---

## 2. Required module-level constants

Each adapter module MUST export:

### 2.1 `ADAPTER_VERSION: str`

SemVer-shaped version string for the adapter implementation.
Format: `MAJOR.MINOR.PATCH[-rc.N]`. Bumps follow:

- **MAJOR**: breaking change to adapter behavior (e.g. output shape
  diverges from prior minor).
- **MINOR**: new capability surfaced (new field in CAPABILITIES).
- **PATCH**: bug fix, internal refactor, doc update.

Initial value for a newly-shipped adapter is `"1.0.0-rc.1"`.

### 2.2 `CAPABILITIES: dict`

Dictionary describing the provider's protocol-level capabilities.
Required keys:

| Key | Type | Value examples | Meaning |
|---|---|---|---|
| `streaming_tool_use` | `bool` | `True` / `False` | Provider streams partial tool-call deltas. |
| `json_mode` | `bool \| str` | `True`, `False`, `"advisory"` | Provider supports strict JSON mode. `"advisory"` = best-effort only. |
| `function_calling` | `bool` | `True` / `False` | Provider's native function-calling API is available. |
| `system_prompt_slot` | `bool` | `True` / `False` | Provider accepts a dedicated system prompt role. |

Optional keys allowed (additive); unknown keys ignored by tests.
This dict is informational — tests assert the **keys exist**, not
specific values (values documented in `docs/provider_capability_matrix.md`).

---

## 3. Required functions (ABI)

### 3.1 `read_event(stream=None, phase="PreToolUse") -> NormalizedEvent`

**Input:**
- `stream`: file-like `IO[str]` object or `None`. If `None`, read
  `sys.stdin` at call-time (to support test stream swaps).
- `phase`: either `"PreToolUse"` or `"PostToolUse"`. Any other value
  (including `None`, `""`, `"bogus"`) MUST be coerced to
  `"PreToolUse"` — fail-open, no raise.

**Output:** `NormalizedEvent` (never raises).

**Semantics:**
1. Read full stream via `stream.read()`.
2. If empty / whitespace-only → return NormalizedEvent(phase=phase).
3. Parse JSON. On `JSONDecodeError`, return NormalizedEvent with
   `parse_error` populated and `phase` preserved.
4. If top-level is not a JSON object, return NormalizedEvent with
   `parse_error`.
5. Map provider wire-shape to envelope fields. Missing fields default
   to empty string / empty dict / False per the dataclass.
6. Preserve original payload in `raw_payload` (per-adapter discretion
   — Claude sets `{}`; Gemini/OpenAI/Local preserve the full dict).

### 3.2 `read_post_event(stream=None) -> NormalizedEvent`

Convenience wrapper equivalent to `read_event(stream, phase="PostToolUse")`.
Required for symmetry; hook code calling `read_post_event()` must be
IDE-agnostic.

### 3.3 `write_decision(decision: Decision) -> str`

**Input:** `Decision` dataclass instance.
**Output:** single-line JSON string (no trailing newline).

The string is the payload the host IDE will read from the hook's stdout.
Key ordering convention (Claude adapter; others may diverge if the host
IDE demands):

1. `"decision"` — always present, `"allow"` or `"block"`.
2. `"reason"` — present iff `decision.allow=False` AND `decision.reason`
   is non-empty.
3. `"systemMessage"` — present iff `decision.system_message` is non-empty.
4. `"message"` — present iff `decision.message` is non-empty.
5. Any `decision.extra` keys that don't collide with the above.

`ensure_ascii=False` so UTF-8 passes through.

### 3.4 `emit_decision(decision, stream=None) -> None`

Writes `write_decision(decision) + "\n"` to `stream` (defaults to
`sys.stdout` resolved at call-time).

---

## 4. Error shape

Adapters never raise to the hook caller. The only error surface is
`NormalizedEvent.parse_error: Optional[str]`.

- `None` → parse succeeded (even if payload was empty and all other
  fields defaulted).
- Non-empty string → parse failed. The string SHOULD start with the
  adapter name in brackets for log grep-ability:
  `"[gemini] JSON parse error: Expecting value: line 1 column 1"`.

Hooks inspecting `parse_error` emit `allow` + a breadcrumb to the
audit log. They never surface the parse_error text to the user session.

### 4.1 Credential hygiene (H8 normative)

**The following is MANDATORY for every adapter:**

- Credentials and secrets present in the **payload** (e.g. in `prompt`,
  `description`, `tool_input.command`) remain in their semantic fields.
  The envelope does NOT scrub user content — that is the redaction
  layer's job (`_lib.redact`).
- The adapter MUST NOT echo credentials into **side-channel fields**:
  - `parse_error` — never include payload excerpts. Use only the
    Python error type + position, not the content.
  - Log lines / print statements — adapters do not print.
  - `tool_name` — must be either the canonical tool name or `""`.
  - Any header value, env var name, or identifier that the adapter
    itself synthesizes.
- **Test:** every adapter MUST have
  `test_adapter_never_echoes_key.py::test_<name>_never_echoes_<kind>`
  that feeds a payload containing `sk-...`, `AKIA...`, JWT, Bearer
  tokens, and confirms the credential never appears in
  `parse_error` or any synthesized adapter-only field.
- Environment variables holding credentials (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.) are **read-nowhere** by
  adapters. Adapters receive the full payload from stdin; the host
  IDE, not the adapter, authenticated the upstream LLM call.

---

## 5. Versioning and deprecation

### 5.1 Adapter-level versioning

Each adapter carries its own `ADAPTER_VERSION`. The framework version
(`VERSION=1.3.0-rc.1`) is independent.

### 5.2 Compatibility

Within SPEC v1:
- Adding a new adapter is always safe.
- Adding a new field to `CAPABILITIES` is safe.
- Adding a new field to `NormalizedEvent` (per `normalized_envelope.schema.md`)
  is safe — adapters that don't know how to fill it leave it at default.
- **Removing** a field from either `NormalizedEvent` or `CAPABILITIES`
  is a breaking change requiring:
  - SPEC version bump (SPEC v2)
  - ADR documenting the migration
  - Deprecation notice in each adapter's `ADAPTER_VERSION` bumped to
    MAJOR with a prior PATCH release warning.

### 5.3 Deprecation policy

An adapter slated for removal:

1. First PR: bumps `ADAPTER_VERSION` MAJOR, adds `DEPRECATED: str`
   module constant explaining replacement.
2. Gap: **minimum 1 framework minor release** before removal.
3. Removal PR: deletes the module, updates `KNOWN_ADAPTERS` in
   `contract.py`, updates `docs/adapters.md`.

---

## 6. Runtime resolution

The `CEO_HOOK_ADAPTER` env-var selects the adapter at runtime, per
`_lib.contract.resolve_adapter()`:

- Empty / unset → `DEFAULT_ADAPTER = "claude"`.
- Value matches `KNOWN_ADAPTERS` → that adapter.
- Value not in `KNOWN_ADAPTERS` → silent fallback to default. No
  stderr output. Observability is via `audit_emit`, not stderr.

### 6.1 `KNOWN_ADAPTERS` after PLAN-011 Phase 1

```python
KNOWN_ADAPTERS: List[str] = ["claude", "gemini", "openai", "local"]
```

---

## 7. Cross-adapter fixtures

Per ADR-012, cross-adapter golden fixtures live under
`.claude/hooks/tests/fixtures/`:

- `adapters/<name>/in/*.json` — raw provider-shape payloads.
- `adapters/<name>/out/*.json` — decision outputs (optional — most
  adapters emit identical Claude-shaped JSON today).
- `adapters/<name>/GAPS.md` — known shape gaps (Gemini has one;
  OpenAI/Local document gaps in the capability matrix).
- `normalized/<scenario>.json` — the expected canonical envelope for
  that scenario.

`test_adapters_parity.py` asserts: for every `normalized/<scenario>.json`,
every adapter's `in/<scenario>.json` (when provided) maps to the
canonical envelope with overlap fields matching.

---

## 8. Drift detector

`test_adapter_drift_detector.py` prevents silent contract drift:

- Parses `contract.py` for the `NormalizedEvent` dataclass field set.
- Parses this file for the § 1.1 field inventory table.
- Asserts the two field sets are identical. Any new field in the
  dataclass without a corresponding table row fails CI.
- Parses `claude.py` source for every `NormalizedEvent(...)` call-site
  and enumerates the fields it populates. Fields populated by the
  Claude adapter that don't appear in the canonical schema fail CI.

See consensus §H2.

---

## 9. Referenced by

- `SPEC/v1/normalized_envelope.schema.md`
- `docs/adapters.md`
- `docs/provider_capability_matrix.md`
- ADR-008 — Hook Adapter Layer (foundation)
- ADR-012 — Cross-adapter golden fixtures
- ADR-028 — Multi-LLM canonical envelope parity (this extension)

## 10. Changelog

- **1.0.0-rc.1** (2026-04-14, PLAN-011 Phase 1): initial publication.
  Codifies the ABI implicit in ADR-008. Adds credential hygiene
  normativity (§4.1) and versioning rules (§5).
