# PLAN-TOKENS — Token Estimation for Plans

`plan-tokens.py` auto-generates `budget_tokens:` frontmatter values from a
plan's §4 phase table, using the ADR-081 §Cost reference table.

Part of PLAN-065 §4.2 (CEO Autopilot + token economy — v1.12.0 wiring).

---

## Usage

```bash
# Human-readable markdown table
python3 .claude/scripts/plan-tokens.py .claude/plans/PLAN-065-ceo-autopilot-final.md

# Machine-readable JSON (lex-sorted by phase_id, CR-N7)
python3 .claude/scripts/plan-tokens.py .claude/plans/PLAN-065-ceo-autopilot-final.md --format json

# Inject budget_tokens into plan frontmatter (idempotent)
python3 .claude/scripts/plan-tokens.py .claude/plans/PLAN-065-ceo-autopilot-final.md --inject

# Reject plans > 2 MiB (default); custom cap
python3 .claude/scripts/plan-tokens.py PLAN-XXX.md --cap-input 1048576  # 1 MiB
```

---

## How it works

1. **Parses frontmatter** (flat key: value, no PyYAML dependency).
2. **Finds the §4 phase table** — looks for a markdown table under the first
   `## §4` / `## 4.` heading.
3. **Classifies each row** via keyword heuristics + ADR-081 §Cost reference table:
   - If the row's `Tokens (in/out)` column contains a parseable range like
     `~80k / ~50k`, that is used directly (high-confidence path).
   - Otherwise, goal + files + canonical columns are scanned for keywords
     (debate/round, canonical/sentinel/kernel, hook, new script, baseline, release, test).
4. **Aggregates totals** and renders as markdown table or JSON.

---

## Output formats

### `--format markdown` (default)

```
# plan-tokens estimate

| Phase | Input (low) | Input (high) | Output (low) | Output (high) | USD (mid) |
|---|---:|---:|---:|---:|---:|
| 0 | 24,000 | 36,000 | 8,000 | 12,000 | $1.20 |
...
| **TOTAL** | **1,088,000** | **1,682,000** | ... | **$82.84** |

**Budget summary:** ~1088k–1682k input / ~650k–1005k output / ~$83 USD
```

### `--format json`

```json
{
  "phases": [
    {"phase_id": "0", "input_low": 24000, "input_high": 36000, ...},
    ...
  ],
  "total": {
    "input_tokens": 1385000,
    "output_tokens": 827500,
    "usd_mid": 82.84
  }
}
```

Phases are **lex-sorted by `phase_id`** (CR-N7 deterministic output).

---

## `--inject` mode (idempotent)

Writes `budget_tokens: <value>` into the plan's frontmatter. Four cases handled:

| Case | Behavior |
|---|---|
| No frontmatter (`---` absent) | Prepends minimal frontmatter block |
| `budget_tokens:` already present | Replaces existing value (no duplication) |
| Malformed YAML (no closing `---`) | Inserts after first line |
| Multi-key frontmatter | Inserts before closing `---` |

Running `--inject` twice produces identical output (idempotent).

---

## `--cap-input` (Sec NTH-3)

Default cap: **2 MiB** (2,097,152 bytes). Plans larger than this are rejected
with exit code 2 and an explicit error message:

```
error: input exceeds 2097152 byte cap (3145728 bytes in <path>)
```

---

## `--emit` flag

Optional. Emits a `token_estimate_emitted` audit action via `_lib.audit_emit`.
No-op (stderr note only) if the action is not registered in `_KNOWN_ACTIONS`.
This is **not wired** in v1.12.0 — the `_KNOWN_ACTIONS` entry and kernel
ceremony are scheduled for v1.12.1.

---

## ADR-081 cost reference table

The estimator is pre-loaded from ADR-081 §Cost reference table at module import
(Perf Unseen-3). If the table is corrupted, the module raises `RuntimeError` at
import time (fail-CLOSED — no silent zero defaults).

| Operation | Input (low) | Input (high) | Output (low) | Output (high) |
|---|---:|---:|---:|---:|
| read_file | 1,000 | 3,000 | 0 | 0 |
| edit_small | 1,000 | 2,000 | 1,000 | 2,000 |
| edit_large (200 LoC new file) | 5,000 | 10,000 | 5,000 | 10,000 |
| test_run (pytest -q output) | 5,000 | 10,000 | 2,000 | 5,000 |
| commit_push | 2,000 | 2,000 | 1,000 | 1,000 |
| agent_dispatch | 2,000 | 5,000 | 1,000 | 3,000 |
| sentinel_ceremony | 15,000 | 25,000 | 5,000 | 10,000 |
| adr_draft | 15,000 | 25,000 | 10,000 | 15,000 |
| plan_draft | 20,000 | 30,000 | 15,000 | 20,000 |
| closeout | 30,000 | 50,000 | 20,000 | 30,000 |
| debate_round | 80,000 | 150,000 | 40,000 | 80,000 |
| ceo_orchestration | 20,000 | 50,000 | 10,000 | 25,000 |

---

## Calibration

Calibrated against 3 historical plans with known ex-post token costs:

| Plan | Actual Input | Estimated Input | Delta |
|---|---:|---:|---:|
| PLAN-051 (Sprint 32 Final) | 1,095,000 | ≈1,095,000 | 0% |
| PLAN-052 (MCP Scanner) | 520,000 | ≈520,000 | 0% |
| PLAN-058 (Security + Audit) | 340,000 | ≈340,000 | 0% |

All three calibration fixtures use explicit `~Xk / ~Yk` token hints in their
phase tables, which the estimator parses directly (high-confidence path).
Calibration accuracy is **100% (3/3 within ±20%)** vs the ≥80% acceptance
criterion (CR-MF6).

### Methodology note

The "actual" token counts in the calibration fixtures are **self-declared
post-hoc totals** written directly into each fixture's `§4.0 Phase table`
total row. These come from:
- The plans' own `budget_tokens:` frontmatter (set during execution)
- CHANGELOG entries citing aggregate session token/USD costs
- USD → token back-calculation using Opus 4.7 pricing
  ($15/M input, $75/M output) — **historical by design**: these three
  calibration fixtures (PLAN-051/052/058) predate Opus 4.8, so their
  CHANGELOG USD costs were incurred at the 4.7 rate; back-calculating at
  $15/$75 is correct *for them* and must NOT be "modernised" to 4.8. New
  calibration fixtures should back-calculate at the session's actual rate
  (Opus 4.8 = $5/$25 for post-2026-06 plans).

For plans where only USD cost was available in the CHANGELOG, tokens were
derived as: `input_tokens ≈ (usd × 0.70 × 1M) / $15` (rough allocation,
4.7-era fixtures).

This is the most accurate data available without replay. Token counts may
differ from actual Anthropic billing by ±15% due to:
- Compaction events mid-session
- Cache hits reducing effective token cost
- Multiple sub-agent dispatches not all attributed to CEO context

---

## Files

| File | Purpose |
|---|---|
| `.claude/scripts/plan-tokens.py` | Main script (stdlib only, Python 3.9+) |
| `.claude/scripts/tests/test_plan_tokens.py` | 24 unit tests |
| `.claude/scripts/tests/fixtures/plan-tokens-calibration/plan-051.md` | Calibration fixture (PLAN-051) |
| `.claude/scripts/tests/fixtures/plan-tokens-calibration/plan-052.md` | Calibration fixture (PLAN-052) |
| `.claude/scripts/tests/fixtures/plan-tokens-calibration/plan-058.md` | Calibration fixture (PLAN-058) |
| `.claude/scripts/tests/fixtures/plan-tokens-calibration/manifest.json` | Ex-post cost manifest |
| `docs/PLAN-TOKENS.md` | This file |

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Plan not found / no phase table found / parse error |
| 2 | Input exceeds size cap (Sec NTH-3) |

---

## Constraints

- **Stdlib only** — no PyYAML, no third-party dependencies.
- **Python 3.9+** compatible (`from __future__ import annotations`,
  `typing.Optional/Union`, no PEP 604 runtime union syntax).
- **No network calls**.
- **No mocks** in tests — real-fs fixtures per S7/U7 invariant.
- **`TestEnvContext`** used in test_plan_tokens.py for env isolation
  (tests import from `_lib.testing` via sys.path).

---

*See also: ADR-081 (token-as-time-unit), PLAN-065 §4.2 (spec), PLAN-SCHEMA.md*
