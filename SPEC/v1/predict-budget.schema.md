---
status: experimental
spec_version: 1.0.0-rc.1
created: 2026-04-16
plan: PLAN-014
phase: F.3a
supersedes: none
---

# SPEC/v1/predict-budget.schema.md — Predictive Budget Contract

**Version:** 1.0.0-rc.1 (PLAN-014 Phase F.3a, Sprint 14)
**Status:** experimental (per ADJ-003 + ADJ-034 until Sprint 15 adopter signal + backtest refresh)
**Authoritative source:** `.claude/scripts/predict-budget/predict-plan-cost.py` — this SPEC is the grep-able output schema + bucketing semantics the predictor is tested against.

## 0. Purpose

ADR-047 §Decision establishes WHY predictive budgeting exists (Owner approval UX; one-way accuracy ratchet; cold-start handling). This document is the normative companion: JSON output schema, bucketing math, cold-start semantics, training-data exclusions, versioning.

**Scope:** predict plan token + USD-bucket cost range from the plan file + historical audit-log token counts.

**Non-scope:** per-spawn prediction (out of scope; predictor aggregates at plan level), real-time prediction during execution (only at plan-draft time), cross-adopter prediction (training window is local audit log only).

Companion documents:
- ADR-047 — Predictive Budgeting decision (options + ratchet + security)
- ADR-033 — Budget-gate + pricing contract
- `audit-log.schema.md` v2.6 — `prediction_queried` event registered
- PLAN-014 §Phase F.3 / §F.4

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | `1.0.0-rc.1` |
| Schema status | `experimental` (frontmatter; awaiting empirical CI ≤±30% for ≥70% of backtests per ADJ-034) |
| Spec lifetime | v1.x.y — additive only per §8 Versioning |
| Authoritative source | `.claude/scripts/predict-budget/predict-plan-cost.py` |
| Cache directory | `$CLAUDE_PROJECT_DIR/state/predict-cache/` (mode 0o700) |
| Cache entry format | `<plan_hash>.json` |

SemVer-shaped. Within v1 every output-field addition is MINOR-bump additive only. Field removal or bucketing-semantics change is MAJOR bump (forbidden in v1 without new SPEC file).

---

## 2. Surface

The predictor surface is **one executable**: `.claude/scripts/predict-budget/predict-plan-cost.py`.

### 2.1 Invocation

```
predict-plan-cost.py --plan-file <PATH> [--audit-log <path>]
                                        [--training-plans <N>]  # default 10
                                        [--confidence ci|low]    # default ci
                                        [--out stdout|file|cache]
                                        [--cache-dir <path>]
                                        [--backtest]             # run backtest vs actuals
                                        [--no-cache]             # skip cache read
                                        [--json]                 # default
                                        [--help]
```

### 2.2 Invariants

- **No raw dollar figures (ADJ-038, Tier 2 sensitive).** Output is always a bucketed range (integer boundaries) + token counts. USD estimates are internally computed but never emitted as raw floats. Operators can compute USD locally via ADR-033 pricing contract.
- **Training excludes anomaly events.** Events with `veto_triggered` OR `budget_bypass_used` in same spawn window are FILTERED OUT before aggregation (Security unseen #4).
- **Cold-start advisory.** New adopter with zero-history audit log emits `prediction_queried(confidence=cold_start)` + range is widest (±100%).
- **One-way ratchet (ADJ-034).** Within v1, `relative_width` (half-width as fraction) only TIGHTENS across SPEC minor releases, never widens. Widening requires MAJOR bump + new SPEC file.

---

## 3. Output schema (JSON)

### 3.1 Top-level envelope

```json
{
  "schema_version": "1.0.0-rc.1",
  "plan_id": "PLAN-014",
  "plan_hash": "<sha256-prefix-16>",
  "prediction": { ... },
  "training": { ... },
  "emitted_audit_event": true,
  "generated_at": "<utc-iso-second>",
  "warnings": [ ... ]
}
```

### 3.2 `prediction` object

```json
{
  "tokens_in_bucket": "<lower>-<upper>",
  "tokens_out_bucket": "<lower>-<upper>",
  "tokens_total_bucket": "<lower>-<upper>",
  "confidence": "high" | "medium" | "low" | "cold_start",
  "bucket_half_width_ratio": 0.3,
  "bucketing_strategy": "relative_ci"
}
```

- Bucket strings are of the form `"<int>-<int>"` with both boundaries in thousands-of-tokens (`k`) units:
  - Example: `"100k-130k"` means 100,000..130,000 tokens.
- `bucket_half_width_ratio` is the relative CI half-width. Default `0.3` (±30%).
- `confidence` closed enum. `cold_start` means fewer than 3 historical plans; `low` means 3-5; `medium` means 6-9; `high` means 10+.

### 3.3 `training` object

```json
{
  "historical_plans_count": <int>,
  "training_plans": ["PLAN-003", "PLAN-004", ...],
  "excluded_event_count": <int>,
  "excluded_reasons": {"veto_triggered": 2, "budget_bypass_used": 1},
  "median_tokens_in": <int>,
  "median_tokens_out": <int>
}
```

### 3.4 `warnings` list

Free-text advisory. Examples: `"cold_start"`, `"training_window_narrow"`, `"plan_file_not_found_in_git"`. Always emitted; empty list when none.

---

## 4. Error model (closed enum)

All predictor errors exit non-zero + print JSON to stderr:

| Exit code | Name | Meaning |
|---|---|---|
| 0 | `ok` | Prediction emitted (may include warnings) |
| 2 | `missing_input` | `--plan-file` doesn't exist |
| 3 | `plan_parse_error` | Plan file malformed frontmatter |
| 4 | `audit_parse_error` | Audit log line unparseable |
| 5 | `cache_write_error` | Filesystem failure on cache write |
| 6 | `invalid_args` | Bad argparse combination |
| 7 | `backtest_failed` | Backtest mode couldn't complete (insufficient historical actuals) |

Cold-start is NOT an error (exit 0 + confidence=cold_start warning).

---

## 5. Bucketing semantics

### 5.1 Point estimate

Per training plan, compute total tokens (sum of `tokens_in` + `tokens_out` from `agent_spawn` events filtered per §2.2 exclusions). The plan-level point estimate is the **median** across training plans (NOT mean — median is robust to outliers).

### 5.2 Bucket bounds

```
half_width = point_estimate * bucket_half_width_ratio
lower = max(0, round((point_estimate - half_width) / 1000) * 1000)
upper = round((point_estimate + half_width) / 1000) * 1000
bucket_string = "{}k-{}k".format(lower // 1000, upper // 1000)
```

Integer boundaries in `k` units. `lower` is clamped to 0.

### 5.3 Confidence → ratio mapping (v1.0.0-rc.1)

| confidence | ratio | Applies when |
|---|---|---|
| `cold_start` | 1.0 (±100%) | <3 historical plans |
| `low` | 0.5 (±50%) | 3..5 historical plans |
| `medium` | 0.3 (±30%) | 6..9 historical plans |
| `high` | 0.3 (±30%) | ≥10 historical plans |

Within v1, MINOR bumps may TIGHTEN these (e.g. high → 0.2) but never widen (ADJ-034 one-way ratchet).

### 5.4 Cold-start rule

If `historical_plans_count < 3`, the predictor:
1. Emits `confidence=cold_start`
2. Sets `tokens_in_bucket="unknown"`, `tokens_out_bucket="unknown"`, `tokens_total_bucket="unknown"`
3. Appends `"cold_start"` to `warnings`
4. Emits `prediction_queried(confidence=cold_start, training_window_plans=<count>)` audit event

No numeric range is fabricated from empty data.

---

## 6. Bounds

Runtime bounds enforced pre-execution:

| Bound | Default | Max | Rationale |
|---|---|---|---|
| Plan file size | 1 MiB | 4 MiB | Defense against crafted plans |
| Audit log lines scanned | 1M | 10M | Stream-read; memory cap ~200 MB |
| Training plans sampled | 10 | 50 | Default window; overridable via `--training-plans` |
| Cache entry size | 4 KiB | 64 KiB | Per-plan cache bound |
| Wallclock timeout | 30s | 300s | Predictor must be fast for Owner-UX |

---

## 7. Revocation

### 7.1 Cache revocation

Cache entries under `state/predict-cache/` are:
- Keyed by `<plan_hash>.json`
- TTL unbounded (manual eviction only)
- Operator-facing eviction: `rm -rf state/predict-cache/` or `--no-cache` to skip read

### 7.2 Audit event revocation

Audit events are append-only. `prediction_queried` is never "un-queried". Callers wanting to invalidate a prediction emit a new event.

---

## 8. Deprecation + versioning

Within v1 (1.0.0-rc.1 through 1.x.y):

- **Output-field additions** are MINOR bump, additive only.
- **Output-field removals** are MAJOR (forbidden in v1).
- **Bucketing-ratio tightening** is MINOR (one-way ratchet per ADJ-034).
- **Bucketing-ratio widening** is MAJOR (forbidden in v1).
- **Confidence-enum additions** are MINOR.
- **Default bucket strategy change** (e.g. `relative_ci` → `absolute_k_buckets`) is MAJOR.

### 8.1 One-way ratchet rule (normative)

For any schema version `1.N.M`, the `bucket_half_width_ratio` MUST satisfy:

    ratio(1.N.M) <= ratio(1.N-1.M_last)

i.e. newer versions may only match or tighten. CI enforcement: `.claude/scripts/tests/test_predict_plan_cost.py::test_one_way_ratchet_smoke` asserts this invariant against a pinned-baseline.

---

## 9. Security considerations

### 9.1 Tier 2 sensitive

Predictor output contains cost proxy information (token ranges) — same sensitivity tier as audit log. Storage under `state/predict-cache/` MUST have mode 0o700.

### 9.2 Side-channel via cost output

Per C31 (Staff Backend unseen #5), the emitted bucket reveals plan complexity signal. Mitigations:
- Output is BUCKETED (no per-token precision leak)
- No raw USD emitted (local computation per ADR-033 pricing contract)
- Cache directory 0o700 (owner-only)

### 9.3 Training poisoning

Adversarial events inserted into audit log could skew predictions. Mitigations:
- Exclude events with `veto_triggered` or `budget_bypass_used` (§2.2)
- Training-plans list is logged in output (`training.training_plans`) — operator can audit
- Backtest mode (`--backtest`) compares prediction vs actual for past plans, surfacing drift

### 9.4 Cold-start fabrication guard

Predictor REFUSES to emit a numeric range on <3 training plans (§5.4). Prevents "single-sample = high-confidence illusion".

---

## 10. History

| Version | Released | Summary |
|---|---|---|
| 1.0.0-rc.1 | 2026-04-16 | Initial experimental release. Bucketed output, median-based point estimate, ±30% default CI, cold-start handling, training exclusions. Status: experimental pending Sprint 15 adopter signal + backtest empirical confirmation. |

---

## 11. Backward compatibility

- **Old predictions** (cached JSON from v1.0.0-rc.1) remain readable by future tool versions (additive-only).
- **Unknown fields** in prediction output: consumers MUST tolerate.
- **Unknown `confidence` values**: consumers MUST tolerate (treat as `low`, advisory).
- **One-way ratchet** is a NORMATIVE backward-compatibility constraint: any consumer that assumed ≤30% range on v1.0.0-rc.1 will still see ≤30% on v1.N.M for N>0.

---

## References

- ADR-047 — Predictive Budgeting decision
- ADR-033 — Budget-gate + pricing contract
- `audit-log.schema.md` v2.6 — `prediction_queried` event
- PLAN-014 §Phase F.3 / §F.3a / §F.4
- `.claude/scripts/predict-budget/predict-plan-cost.py` (authoritative)

---

**End of SPEC/v1/predict-budget.schema.md v1.0.0-rc.1 (experimental).**
