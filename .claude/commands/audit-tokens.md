---
description: Analyze audit-log.jsonl for ghost-token-waste patterns across the 6 PLAN-047 detectors. Emits a markdown report (default) or JSONL stream; advisory-only (never blocks a session).
argument-hint: "[window=30] [format=markdown|jsonl|json] [output=<path>]"
# --- K1 context fork: heavy analytic skill runs in a forked context (PLAN-135 W3 unit k1a) ---
context: fork
---

# /audit-tokens — Token economy audit

Runs the 6 ghost-token detectors shipped in PLAN-047 Phase 1
(`retry_churn`, `tool_cascade`, `looping`, `wasteful_thinking`,
`weak_model`, `overpowered`) over `audit-log.jsonl` and aggregates
the findings into an adopter-facing report.

## Execution

Shell the CLI directly (it is stdlib-only and exits fast on large
logs):

```bash
python3 .claude/scripts/audit-tokens.py \
    --window "${window:-30}" \
    --format "${format:-markdown}" \
    ${output:+--output "$output"}
```

Defaults:

- `window=30` — days lookback applied to finding timestamps in
  `evidence.first_seen` / `evidence.last_seen` / `evidence.ts`.
  Findings with no parseable timestamp are kept (unknown > drop).
- `format=markdown` — alternatives are `jsonl` (one finding per
  line) and `json` (single summary object with findings array).
- `output` — if omitted, content prints to stdout; otherwise the
  parent directory is created and the report is written there.

## Invocation examples

| Intent | Command |
|---|---|
| Quick dashboard read | `/audit-tokens` |
| Last 7 days only | `/audit-tokens window=7` |
| Save JSONL for pipeline | `/audit-tokens format=jsonl output=ceo-audit-tokens-2026-04-21.jsonl` |
| All history | `/audit-tokens window=0` |

## Output sections (markdown)

1. Header — `generated_at`, `window`, `log_path`, total findings,
   summed `estimated_wasted_tokens`.
2. Per-detector groups — severity tally + top-N findings per
   detector (default 20), each line listing `[severity]`,
   recommendation, and first four `evidence` pairs. Remaining
   findings are folded into a "N more" note; full set is in the
   JSON/JSONL outputs.
3. No findings? The report explicitly says so. Adopter treats this
   as either "dispatch is clean in window" or "detectors need more
   post-PLAN-020 streaming telemetry to get signal" — both are OK.

## Advisory-only contract

Per PLAN-047 §Goal, these detectors are observability. No finding
ever blocks a session, triggers a VETO, or mutates state. Adopter
reads the report, decides whether to adjust `.claude/agents/*.md`
`model:` fields (weak_model / wasteful_thinking findings), refactor
a prompt that retries (retry_churn / looping), or rebalance task-type
dispatch (overpowered / tool_cascade).

See `docs/TOKEN-ECONOMY-ADOPTER-GUIDE.md` for interpretation,
detector thresholds, the 10 viral-post habits mapped to framework
mechanisms, and when to act on which finding.

## Performance

Typical execution on a 9.4 MiB audit-log (~21k spans):

- Wall clock: ~0.1–0.5 s.
- Allocations: proportional to number of spawn events; fail-open
  on malformed JSONL lines (skipped).
- Deterministic output given the same log and clock — safe for
  scripted diffing across sessions.

## Related

- `.claude/scripts/detectors/` — 6 detector modules + tests.
- `.claude/plans/PLAN-047-token-economy-observability.md` — plan of
  record.
- `.claude/skills/core/terse-mode/SKILL.md` — companion opt-in
  behavior (ships end-to-end once SP-019 lands; see
  `PLAN-047/phase-2-sp019-deferred.md`).
