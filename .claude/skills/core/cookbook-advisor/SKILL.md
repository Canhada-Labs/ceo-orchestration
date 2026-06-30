---
name: cookbook-advisor
description: Advise on 4 Anthropic Cookbook 2026 patterns (COOK-P1..P4) — surface UX hints when a task signature matches a pattern trigger class. Advisory-only emit; never blocks.
owner: CEO
tier: core
plan_origin: PLAN-092
adr_origin: ADR-127 (advisory-only doctrine — shared with check_pair_rail.py)
pattern_ids:
  - COOK-P1
  - COOK-P2
  - COOK-P3
  - COOK-P4
audit_action: cookbook_pattern_advised
kill_switch_env: CEO_COOKBOOK_ADVISOR_ENABLED
---

# cookbook-advisor

## §Purpose

The Anthropic Cookbook 2026 catalogues four canonical patterns
(Structured output / Chain-of-Verification / Citations API /
Message Batches) consumed by framework users at runtime. This skill is
the **routing surface** that `check_agent_spawn.py` fires when a spawn
prompt or task description matches one of the pattern trigger taxonomies
loaded from `.claude/data/cookbook_patterns.json`.

Emit is **advisory-only** (UX hint via
`audit_emit.emit_cookbook_pattern_advised`) and **never blocks** the
agent dispatch path. Rate-cap is enforced via the PLAN-088 global
`_plan088_rate_admit("cookbook_pattern_advised")` bucket — a single
global cap, not per-pattern-class (R1 P1-7 correction locked into
ADR-127 §Migration). The kill-switch env
`CEO_COOKBOOK_ADVISOR_ENABLED=0` disables emit entirely.

The skill shares advisory-only doctrine with `check_pair_rail.py` (both
governed by ADR-127 Tier-B promotion path — see
`.claude/adr/ADR-127-pair-rail-advisory-promotion.md` for the canonical
governance contract).

## §Pattern catalogue (4 canonical IDs)

### COOK-P1 — Structured output / JSON mode

**Intent**: LLM responses destined for downstream automation must be
parseable. Free-form text introduces parsing risk (model prefixes a
sentence before the JSON, wraps it in Markdown fences, etc.).
Structured-output / JSON mode tells the model to emit *only*
well-formed JSON conforming to a caller-supplied shape. Anthropic SDK
exposes this via the `tool_choice` strict-JSON pattern and the
`response_format` parameter.

**Trigger taxonomy** (task signatures that fire COOK-P1 advice):
- task involves emitting JSON for downstream automation
- task mentions "parse the model's response", "extract structured data",
  "schema validation", "JSON mode"
- task_class: `structured-extract` | `json-emit` | `downstream-automation`

**Suggested action**: Use Anthropic `tool_choice` strict-JSON or
`response_format`. See `docs/cookbook-patterns.md` Pattern 1.

### COOK-P2 — Chain-of-Verification (CoVe)

**Intent**: CoVe is a 4-step self-verification pattern that reduces
hallucination on factual claims. The model emits a draft answer →
generates verification questions about the draft → answers each
verification question independently → revises the draft using verified
answers. Each step is a separate model call; the final revised draft
is returned to the caller.

**Trigger taxonomy**:
- task involves factual claims that need self-check
- task mentions "verify", "double-check", "fact-check", "self-review",
  "chain-of-verification", "CoVe", "hallucination mitigation"
- task_class: `self-verification` | `factual-claim-emit` |
  `hallucination-mitigation`

**Suggested action**: Implement CoVe via canonical 4-call sequence
(draft → verify-questions → verify-answers → revise). See
`docs/cookbook-patterns.md` Pattern 2.

### COOK-P3 — Citations API

**Intent**: The Anthropic Citations API tags spans in the response
with references to source-document chunks supplied alongside the
prompt. Each cited span carries a `document_index` +
`start_char_index` + `end_char_index` pointing back to the source
corpus the model was given, giving downstream consumers verifiable
attribution for every quoted fact.

**Trigger taxonomy**:
- task involves quoting or referencing source documents
- task mentions "cite", "citation", "attribution", "source reference",
  "doc-grounded generation", "where did this come from"
- task_class: `source-attribution` | `citation-required` |
  `doc-grounded-generation`

**Suggested action**: Enable Citations API + supply documents array.
See `docs/cookbook-patterns.md` Pattern 3.

### COOK-P4 — Message Batches API

**Intent**: The Anthropic Message Batches API processes large request
sets asynchronously at a 50% cost discount vs synchronous calls.
Useful when no real-time SLA — overnight pipelines, bulk evaluation,
offline annotation. Batch results return via a single retrieve call
after the batch transitions to `ended`; partial results are not
available before then.

**Trigger taxonomy**:
- task involves >50 similar requests without real-time SLA
- task mentions "batch", "bulk", "process all", "overnight job",
  "offline pipeline", "Message Batches API", "async batch"
- task_class: `bulk-processing` | `async-batch` | `offline-pipeline`

**Suggested action**: Use Anthropic Message Batches API for ≥50% cost
savings vs synchronous. See `docs/cookbook-patterns.md` Pattern 4.

## §Invocation contract

This skill does NOT generate code on its own. It is the **routing
surface** consumed by `check_agent_spawn.py`:

1. Hook reads spawn-prompt + tool_input on `Task` tool calls.
2. Hook calls `_lib.cookbook_patterns.match_pattern(prompt_text)` to
   evaluate the spawn against all 4 patterns in canonical order.
3. On match, hook calls
   `audit_emit.emit_cookbook_pattern_advised(pattern_id, trigger_class,
   match_confidence_bucket)`.
4. Hook returns `{}` (allow + advisory only; never blocks per ADR-127).

Trigger taxonomies are sourced from
`.claude/data/cookbook_patterns.json` (stdlib-JSON, NOT YAML per
ADR-126 stdlib-core invariant); validated by
`.claude/hooks/_lib/cookbook_patterns.py` (stdlib-only ≤120 LoC helper).

## §Audit-emit contract

Emitted action: `cookbook_pattern_advised` (registered in
`_lib/audit_emit.py:448` since PLAN-090 W3.2 SEMI-11).

**Whitelisted fields (3 EXACTLY** per Sec MF-3 / AC3b privacy invariant):
- `pattern_id` — one of `COOK-P1` / `COOK-P2` / `COOK-P3` / `COOK-P4`
- `trigger_class` — short label string (one of the task classes
  enumerated above)
- `match_confidence_bucket` — `high` / `medium` / `low` (regex-strength
  heuristic; ratio of matched regexes to total per pattern)

**DENIED fields** (privacy invariant — test
`test_audit_emit_fields_no_raw_prompt` enforces):
- raw spawn-prompt text
- file paths
- token counts
- environment values

Rate-cap: PLAN-088 global
`_plan088_rate_admit("cookbook_pattern_advised")` applies (NOT
per-pattern-class — single global bucket per R1 P1-7 correction
locked in PLAN-092 frontmatter).

## §Kill switch

Setting `CEO_COOKBOOK_ADVISOR_ENABLED=0` (or `false`/`no`/`off`)
disables emit entirely. Default is enabled (Tier-A simple-env-flip
reversibility per ADR-125 criterion #3).

## §Out-of-scope (v1.x)

- Auto-generating cookbook code from task signatures (deferred to v2.0
  per ADR-115 §exception #1 ship-before-perf doctrine).
- Per-pattern-class rate buckets (PLAN-088 global cap is the contract
  for v1.x; per-class buckets re-evaluated under PLAN-098+).
- Telemetry on advisory-acceptance (was the hint useful? — needs Owner
  feedback loop; deferred to v2.0 cluster).

## §Cross-references

- Source patterns: `docs/cookbook-patterns.md` (PLAN-087 Wave G ship)
- Pattern data: `.claude/data/cookbook_patterns.json` (PLAN-092 Wave A.2)
- Validator: `.claude/hooks/_lib/cookbook_patterns.py` (PLAN-092 Wave A.2)
- Callsite: `.claude/hooks/check_agent_spawn.py` (PLAN-092 Wave A.4)
- Audit emit: `.claude/hooks/_lib/audit_emit.py:4984` (PLAN-090 W3.2)
- Shares advisory-only doctrine: `check_pair_rail.py` + ADR-127 Tier-B
- Inventory regen: `.claude/scripts/generate-skill-inventory.sh` (CI gate)
- Persona routing: `_lib/persona_routing.py:76` (SEMI-11 = advisory)

## §Status

PROPOSED → ACCEPTED by PLAN-092 Wave A.1 ceremony (S121 / 2026-05-14).
Plan-level `risk_tier: B` (per-wave A=A, B=B 30d-soak, C=A, D=A;
Wave A.1 alone is Tier A — observable-ON + new-skill-bootstrap only).
