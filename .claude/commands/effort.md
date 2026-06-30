---
description: Set extended-thinking effort for the next live-adapter spawn (PLAN-086 Wave A R-013, B.2 auto-activation; PLAN-134 W0 E6-F2 adaptive surface).
allowed-tools: Bash, Read
---

# /effort — Extended-thinking effort controller

Activates Claude extended thinking for the next
`_lib/adapters/live/claude.py:ClaudeLiveAdapter.call()` invocation.
On the current API generation (Opus 4.6+ / Sonnet 4.6 / Opus 4.7 / Opus 4.8 /
Fable 5) the adapter emits `thinking={"type": "adaptive"}` plus
`output_config={"effort": "<level>"}`. The legacy
`{"type": "enabled", "budget_tokens": N}` shape returns HTTP 400 on that
generation and is emitted ONLY for legacy (pre-4.6) model ids.
Closes PLAN-086 Wave A R-013 (B.2 auto-activation enabler); repaired under
PLAN-134 W0 (E6-F2 latent HTTP-400).

## Arguments

`/effort <off|low|med|high|xhigh|max|--no-thinking|--budget-tokens N>`

| Form | Adaptive-only models (current generation) | Legacy (pre-4.6) models |
|---|---|---|
| `/effort low` | `output_config.effort = "low"` | `budget_tokens = 1024` |
| `/effort med` | `output_config.effort = "medium"` | `budget_tokens = 4096` |
| `/effort high` | `output_config.effort = "high"` | `budget_tokens = 16384` |
| `/effort xhigh` | `output_config.effort = "xhigh"` | `budget_tokens = 24576` |
| `/effort max` | `output_config.effort = "max"` | `budget_tokens = 32768` |
| `/effort off` / `--no-thinking` | `thinking` param OMITTED entirely — NEVER `{"type": "disabled"}` (HTTP 400 on Fable 5) | kwarg omitted |
| `/effort --budget-tokens N` | **LEGACY-ONLY** — ignored on adaptive-only models | explicit budget (clamped 1024..32768) |

The level keyword is `med` (not `medium`). The canonical value tables live in
`_lib/model_routing.py`: `_SLASH_EFFORT_TABLE` (adaptive surface) and
`_SLASH_BUDGET_TABLE` (legacy budgets) — this doc mirrors them; the code is
the source of truth.

`xhigh` (PLAN-135 W1 K8b) is the API effort tier between `high` and `max`,
introduced with Opus 4.7 (supported on Opus 4.7/4.8 + Fable 5; the
recommended setting for most coding/agentic work and the Claude Code
default). Legacy (pre-4.6) ids have no native xhigh tier — the legacy column
value is the high↔max interpolation so the keyword stays monotonic on that
surface.

## Transport — CEO_EFFORT_OVERRIDE env var

The override travels via the `CEO_EFFORT_OVERRIDE` environment variable
(values: `off`/`low`/`med`/`high`/`xhigh`/`max`). There is NO state file — earlier
revisions of this doc described a `thinking_budget.json` state file that the
adapter never read; the env var is the real and only transport
(`claude.py:_resolve_effort_config` reads it on every `call()`).

## Task-class guard table (Perf-2 fold)

| Task class | Thinking allowed | Default level | Opt-out flag |
|---|---|---|---|
| `arch` | yes | high | `--no-thinking` |
| `code_gen` | yes | med | `--no-thinking` |
| `debate` | yes | high | `--no-thinking` |
| `finops` | yes | med | `--no-thinking` |
| `file_read` | **no** | — | n/a (forced off) |
| `line_audit` | **no** | — | n/a (forced off) |
| `digest` | **no** | — | n/a (forced off) |

Global kill-switch env var: `CEO_THINKING_AUTO_DISABLE=1` honored regardless of
task class (per handoff §9.3 Sec-P0-2). Setting forces `--no-thinking` semantics.

## Procedure

1. Parse `$ARGUMENTS` against the form table above. Reject unknown flags.
2. Resolve task class from active `dispatch_archetype_hint` (ADR-112) OR from
   command-line `--task-class <name>` override. If task class is in the
   forced-off set (`file_read`/`line_audit`/`digest`), emit `thinking_kwarg_skipped`
   audit breadcrumb and exit 0 without setting the env var.
3. Export `CEO_EFFORT_OVERRIDE=<off|low|med|high|xhigh|max>` for the next
   live-adapter spawn (env-var transport — see §Transport above).
4. Emit `thinking_budget_set` audit event with whitelisted fields
   (`budget_tokens`, `task_class`, `session_id`).
5. `ClaudeLiveAdapter.call()` reads `CEO_EFFORT_OVERRIDE` on the next
   invocation when the caller passed no explicit `thinking` kwarg:
   - adaptive-only model → `thinking={"type":"adaptive"}` +
     `output_config={"effort":"<level>"}` (adaptive auto-interleaves — the
     `interleaved-thinking-2025-05-14` beta header is legacy-only and is
     never added for adaptive)
   - legacy (pre-4.6) model → `thinking={"type":"enabled","budget_tokens":N}`
   - `off` → the `thinking` param is omitted entirely
   A caller-passed legacy dict on an adaptive-only model is translated to
   `{"type":"adaptive"}` by a hard guard (the legacy shape is a guaranteed
   HTTP 400 there).

## Kill switches

- `CEO_THINKING_AUTO_DISABLE=1` — disables all extended thinking regardless
  of the override (drops both the `thinking` param and the resolver-supplied
  `output_config`).

## Cost-delta smoke test (AC A.7)

`/effort --no-thinking` followed by a `code_gen` spawn MUST NOT inject the
`thinking` kwarg. Verified by `test_thinking_budget_command.py::test_no_thinking_kwarg_for_excluded_classes`.
