# SPEC/v1/normalized_envelope.schema.md — Canonical NormalizedEvent contract

**Version:** 1.0.0-rc.1 (PLAN-011 Phase 1, Sprint 11)
**Status:** PROPOSED (additive under SPEC v1; no breaking changes to v1)
**Authoritative source:** `.claude/hooks/_lib/contract.py` (`class NormalizedEvent`)

---

## 0. Purpose

This document describes the **one canonical envelope** that every hook
adapter (`claude`, `gemini`, `openai`, `local`, future) must produce
from its provider-specific wire payload. The envelope is IDE-agnostic
and provider-agnostic: one tool-call shape, one system-prompt slot,
one stop-reason enum, one `parse_error` field for fail-open.

Per PLAN-011 debate round 1 §H2 consensus: **byte-identity across
providers is a fiction.** The realistic invariant is **canonical
envelope parity** — raw wire shapes diverge, but after normalization,
every adapter produces a `NormalizedEvent` with the same typed fields.

Per §H9 consensus: the adapter ABI (`read_event`, `read_post_event`,
`write_decision`, `emit_decision`) is normative and documented in
`adapters.schema.md`. This file documents only the envelope shape.

---

## 1. The canonical envelope

The canonical representation is the `NormalizedEvent` dataclass in
`.claude/hooks/_lib/contract.py`. This file mirrors its field set as
a grep-able schema for the drift detector
(`test_adapter_drift_detector.py`).

### 1.1 Field inventory (authoritative — grepped by drift detector)

| Field | Type | Default | Purpose |
|---|---|---|---|
| `session_id` | `str` | `""` | Session identifier supplied by the IDE. Opaque. |
| `project` | `str` | `""` | Absolute path of the project root (from `CLAUDE_PROJECT_DIR` or adapter-specific env). |
| `phase` | `str` | `"PreToolUse"` | Hook phase: `"PreToolUse"`, `"PostToolUse"`, or `"PostToolUseFailure"` (PLAN-125 WS-1 — distinct failure phase; `is_posttooluse()` is true ONLY for `"PostToolUse"`). Genuinely-unknown values fail-open to `"PreToolUse"`. |
| `tool_name` | `str` | `""` | Canonical tool name (`Agent`, `Bash`, `Edit`, `Read`, `Write`, etc.). |
| `tool_input` | `Dict[str, Any]` | `{}` | Pre-tool payload (the tool's input arguments). |
| `tool_response` | `Dict[str, Any]` | `{}` | Post-tool payload (the tool's output). Empty dict in PreToolUse. |
| `description` | `str` | `""` | Convenience: `tool_input["description"]` or top-level `description`. |
| `prompt` | `str` | `""` | Convenience: `tool_input["prompt"]` or top-level `prompt`. |
| `subagent_type` | `str` | `""` | Convenience: `tool_input["subagent_type"]`. |
| `file_path` | `str` | `""` | Convenience: `tool_input["file_path"]`. |
| `old_string` | `str` | `""` | Convenience: `tool_input["old_string"]`. |
| `new_string` | `str` | `""` | Convenience: `tool_input["new_string"]`. |
| `replace_all` | `bool` | `False` | Convenience: `tool_input["replace_all"]`. |
| `command` | `str` | `""` | Convenience: `tool_input["command"]`. |
| `tool_use_id` | `str` | `""` | PLAN-125 WS-1 — per-tool-call pairing key (top-level payload field, identical across `PreToolUse` / `PostToolUse` / `PostToolUseFailure`). Surfaced as a NAMED scalar, NOT via `raw_payload`. Used to pair the Pre stamp with its completion for lifecycle telemetry. |
| `duration_ms` | `Optional[int]` | `None` | PLAN-125 WS-1 — native tool wall-clock on `PostToolUse` / `PostToolUseFailure` (top-level payload field); `None` on `PreToolUse` / when absent. Kept numeric so the lifecycle bucketing mapper sees a number. NEVER emitted raw to the audit chain — bucketed to `duration_bucket` (MF-SEC-3). |
| `raw_payload` | `Dict[str, Any]` | `{}` | Raw provider payload preserved for fields not surfaced here. Adapters MAY populate. |
| `parse_error` | `Optional[str]` | `None` | Non-fatal parse error. Set when JSON invalid / payload malformed. Callers fail-open. |

**Evolution rule (§H10 / S1):** within SPEC v1, fields may be **added**
but not removed or renamed. A breaking change bumps the SPEC version
and requires a new ADR. See `adapters.schema.md §Versioning`.

### 1.2 Stop-reason enum

PreToolUse has no stop reason (the tool hasn't run). PostToolUse hook
consumers that need a stop reason derive it from
`tool_response` contents. This envelope does not expose a stop_reason
field; it is out-of-scope for v1. Future breaking change eligible.

### 1.3 System-prompt slot

Claude Code does not put system prompts in hook payloads; other
providers do (OpenAI `system` role, Ollama `system` field). When an
adapter sees a system prompt, it SHOULD place it in `raw_payload`
under the key `"system_prompt"`. The canonical envelope does not
surface system prompts as a typed field in v1 (adapters that need it
read `raw_payload["system_prompt"]`).

---

## 2. Canonical JSON representation

The envelope, when serialized (e.g. for cross-adapter fixture
comparison), uses this JSON shape:

```json
{
  "session_id": "gem-sess-001",
  "project": "",
  "phase": "PreToolUse",
  "tool_name": "Agent",
  "tool_input": {
    "subagent_type": "general-purpose",
    "description": "Sample spawn",
    "prompt": "## AGENT PROFILE\n## SKILL CONTENT\nX"
  },
  "tool_response": {},
  "description": "Sample spawn",
  "prompt": "## AGENT PROFILE\n## SKILL CONTENT\nX",
  "subagent_type": "general-purpose",
  "file_path": "",
  "old_string": "",
  "new_string": "",
  "replace_all": false,
  "command": "",
  "raw_payload": {},
  "parse_error": null
}
```

Adapters do NOT output this JSON directly to the host IDE. This shape
is used only by:

- Cross-adapter parity tests (`test_adapters_parity.py`)
- Drift-detection (`test_adapter_drift_detector.py`)
- Fixture golden files under `fixtures/normalized/`

The IDE output shape is the adapter's `write_decision` return value
— documented per-adapter in `adapters.schema.md §Decision shape`.

---

## 3. Parity matrix (what "canonical envelope parity" means)

For the overlapping capability set across all 4 shipped adapters,
given the same **semantic** input (e.g. "Agent spawn with description
D and prompt P"), every adapter MUST produce a `NormalizedEvent` whose
overlap fields are equal:

| Field | Claude | Gemini | OpenAI | Local |
|---|---|---|---|---|
| `session_id` | Y | Y (probed) | Y | Y |
| `tool_name` | Y | Y (probed) | Y | Y |
| `tool_input` keys | Y | Y (probed) | Y | Y |
| `description` | Y | Y | Y | Y |
| `prompt` | Y | Y | Y | Y |
| `command` | Y | Y | Y | Y |
| `phase` | Y (authoritative arg) | Y | Y | Y |
| `parse_error` | Y (fail-open) | Y | Y | Y |
| `raw_payload` | empty dict | full payload | full payload | full payload |

Gaps (fields a provider cannot fill): documented row-by-row in
`docs/provider_capability_matrix.md`. A field absent from that matrix
is a bug, not a feature.

---

## 4. Fail-open contract (MUST)

Every adapter MUST satisfy:

1. **Empty stdin** → NormalizedEvent with default field values,
   `parse_error=None`. Caller emits `allow`.
2. **Malformed JSON** → NormalizedEvent with `parse_error` set to
   non-empty string. All other fields empty-but-present (defaults).
3. **Non-object top-level** (e.g. `[1,2,3]`, `"string"`, `null`) →
   `parse_error` set with message indicating shape mismatch.
4. **Unknown field in payload** → silently ignored; does NOT raise.
5. **Unknown phase argument** → coerced to `"PreToolUse"`; no error.
6. **Credentials in payload** → **never echoed into `parse_error`,
   `tool_name`, `description`, or adapter log output** (H8). Preserved
   in `prompt` / `description` where semantically present (i.e. the
   envelope does not attempt to scrub user content; the _adapter_ does
   not add credentials to side-channel fields).

Infrastructure bugs NEVER block the session. Missing `parse_error`
when JSON fails == adapter contract violation.

---

## 5. Referenced by

- `SPEC/v1/adapters.schema.md` — adapter ABI
- `SPEC/v1/hook-io.schema.md` — Claude-specific wire shape
- `docs/provider_capability_matrix.md` — capability gaps per adapter
- `docs/adapters.md` — runbook for swapping adapters
- ADR-008 — Hook Adapter Layer (foundation)
- ADR-012 — Cross-adapter golden fixtures
- ADR-028 — Multi-LLM canonical envelope parity (this extension)

## 6. Changelog

- **1.0.0-rc.1** (2026-04-14, PLAN-011 Phase 1): initial publication.
  Mirrors `contract.NormalizedEvent` field set. Additive within SPEC v1.
