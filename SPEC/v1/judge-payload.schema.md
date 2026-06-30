# SPEC v1 — judge-payload.schema

> **Normative source:** `.claude/scripts/benchmark-judge.py`
> (`validate_payload`, `build_payload`).
> **Spec version:** 1.0.0-rc.1 (added PLAN-011 Phase 3, debate §H6)
> **Related:** ADR-030 (LLM-as-judge methodology), `SPEC/v1/benchmarks.schema.md`.

## 1. Purpose

Defines the **default-deny** payload shape that reaches an LLM-as-judge
adapter. The principle, from debate round-1 §H6:

> The judge MUST see only: (a) the rubric, (b) the redacted candidate
> response, and (c) the minimal task context. NEVER the audit log,
> NEVER raw Owner source snippets, NEVER secrets.

Every other field that downstream refactors might be tempted to add
(`description_hash`, `session_id`, `source_path`, `skill_content`,
`agent_name`, …) is a regression. This schema is the gate.

## 2. Normative shape

The judge payload is a JSON object with EXACTLY three top-level keys:

```json
{
  "task_context": "<string, redacted, <=4000 chars>",
  "rubric":       {"version": 1, "rubric_id": "<slug>", "items": [...], "scoring": "..."},
  "response":     "<string, redacted via redact_secrets(), <=8000 chars>"
}
```

Any other top-level key — including but not limited to:

- `audit_log`, `audit_context`
- `session_id`, `session_context`
- `source_code`, `skill_content`, `description_hash`
- `secrets`, `env`, `credentials`
- `tools`, `tool_input`, `tool_response`

…MUST raise `ValueError("judge-payload default-deny violation; extra keys: …")`
at `validate_payload` time.

## 3. Field rules

### 3.1 `task_context` (string, required)

- UTF-8 string.
- Redacted via `_lib.redact.redact_secrets()` BEFORE inclusion.
- Capped at `TASK_CONTEXT_MAX_CHARS = 4000` (truncation suffix
  `"...[truncated]"`).
- MAY contain the marker `"[REVERSE-PASS] "` as the first 15 chars to
  signal the reverse-pass in two-pass grading. The marker itself is
  part of the string; it does not create a new field.

### 3.2 `rubric` (object, required)

- Object shape per `.claude/benchmarks/_schemas/judge-rubric.yaml`
  (public doc) and `.claude/benchmarks/_schemas/judge-rubric-example.json`
  (the JSON twin that code actually consumes, since the framework is
  stdlib-only).
- Required keys: `version`, `rubric_id`, `items`, `scoring`.
- `items` is a non-empty array; each item has `id` + `description` + `weight`.
- `scoring` is one of `"weighted_average"` or `"all_or_nothing"`.

### 3.3 `response` (string, required)

- UTF-8 string.
- MUST have passed through `redact_secrets(response, max_chars=0)`
  BEFORE inclusion (the scorer does not re-redact; callers are
  responsible for the redaction contract).
- Capped at `RESPONSE_MAX_CHARS = 8000` (truncation suffix
  `"...[truncated]"`).

## 4. Enforcement points

| Where | Check | Failure mode |
|---|---|---|
| `build_payload()` | Applies redaction + caps + calls `validate_payload`. | raises `ValueError` |
| `validate_payload()` | Asserts exactly three top-level keys. | raises `ValueError` |
| Unit tests | `test_benchmark_judge.TestPayloadDefaultDeny.*` (6 tests). | CI fails |
| Review | Any diff adding a 4th key to `JUDGE_PAYLOAD_ALLOWED_KEYS` requires an ADR update AND a test update AND is Owner-gated via CODEOWNERS. | — |

## 5. What this schema does NOT do

- **Encrypt the payload.** Transport encryption is the adapter's
  responsibility. This schema governs structure, not confidentiality
  in flight.
- **Prevent the response itself from smuggling content.** An
  adversarial response might embed claim-shaped tokens or prompt-
  injection strings. Those are out of scope; see
  `check_read_injection.py` and output-safety (Phase 9, ADR-036).
- **Authenticate the rubric.** The rubric is a trusted input (committed
  file). Runtime rubric mutation is not in scope of this schema.

## 6. Changelog

- `1.0.0-rc.1` (2026-04-14) — initial shape.
