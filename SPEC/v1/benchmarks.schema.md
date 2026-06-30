# SPEC v1 — benchmarks.schema

> **Normative source:** `.claude/scripts/run-skill-benchmark.py` (runner)
> and `.claude/skills/**/benchmarks/*.yaml` (instance files).
> **Spec version:** 1.0.1-rc.1 (amended PLAN-011 Phase 3 — judge-mode fields)
> **Related:** ADR-030 (LLM-as-judge methodology), `SPEC/v1/judge-payload.schema.md`.

## Summary (normative)

Per-skill benchmark files define a set of scenarios the runner exercises
against the skill at temperature 0, median-of-3, and reports pass rate
+ median score. Used by CI (`benchmarks.yml`) as an advisory gate and
by operators to detect skill regressions.

## File location

```
.claude/skills/<tier>/<skill-name>/benchmarks/<benchmark-id>.yaml
```

Tier is one of `core`, `frontend`, `domains/<domain>`. A skill MAY
have multiple benchmark files (e.g. `owasp-basics.yaml` + future
`owasp-advanced.yaml`). The runner uses `<benchmark-id>.yaml` stem as
the benchmark identifier in audit events.

## Top-level fields (required)

| field | type | description |
|---|---|---|
| `skill` | string | Must match the skill directory name (kebab-case) |
| `benchmark_version` | int | Bumped on any scenario content change |
| `created` | date (ISO 8601) | First authored date |
| `owner` | string | Persona or archetype accountable for benchmark quality |
| `description` | string (multiline) | One-paragraph scope summary |
| `scoring` | object | See Scoring section below |
| `scenarios` | list of scenario objects | See Scenario section below |

## Top-level fields (optional)

| field | type | description |
|---|---|---|
| `cost_ceiling_usd_per_run` | float | Per-run soft cap; CI workflow enforces |
| `notes` | string | Free-text operator notes |

## Scoring (required sub-object)

```yaml
scoring:
  pass_threshold: 0.7              # required; float 0.0-1.0
  health_thresholds:               # required; used by audit-query health
    critical: 0.4
    warning: 0.6
    healthy: 0.8
  tag_weight: 0.5                  # required; must-flag-tag match weight
  suggestion_weight: 0.3           # required; must-suggest-keyword weight
  severity_weight: 0.2             # required; severity-identification weight
```

Weights SHOULD sum to 1.0 but the runner does not enforce.

## Scenario object (required fields)

```yaml
- id: <KEY>-<NNN>               # unique within file; uppercase kebab
  name: short human title
  category: <taxonomy tag>      # e.g. OWASP-A07; optional for non-sec
  severity: LOW | MEDIUM | HIGH | CRITICAL
  version: 1                    # bumps on content change
  validated_by: YYYY-MM-DD
  input:
    type: code | question | scenario
    language: typescript | python | go | markdown | ...
    content: |
      ... multiline content ...
  prompt_template: |
    ... must end with a JSON response contract ...
  expected:
    # For POSITIVE scenarios:
    must_flag_tags: [list of required tag hits — any one match passes]
    acceptable_alternative_tags: [list — single match from this set also OK]
    must_suggest_keywords: [list — any one keyword in suggestion passes]
    must_identify_severity: HIGH | MEDIUM | LOW | CRITICAL

    # For CONTROL scenarios (precision tests):
    must_not_flag_tags: [list — scoring penalises MEDIUM+ flagging]
```

Scenarios with `id` starting `CTRL-` are precision controls: the skill
MUST NOT flag them at MEDIUM+ severity. A benchmark with only positive
scenarios measures recall; precision requires controls.

## Runner contract

`run-skill-benchmark.py <skill> [--benchmark BENCHMARK_ID] [--floor F]`

- Reads all `benchmarks/*.yaml` for the skill (or filtered to one)
- Spawns 3 Claude calls per scenario at temperature 0; takes median score
- Computes pass rate = (scenarios with score >= pass_threshold) / total
- Exits 0 if pass rate >= `--floor` (default 0.6); else exit 1
- Emits `benchmark_run` audit event per skill run

## Additivity

- Adding a new scenario → MINOR bump `benchmark_version`
- Editing scenario `content`, `must_flag_tags`, or `severity` → MAJOR
  bump the scenario's `version` field AND update `validated_by`
- Removing a scenario → MAJOR bump `benchmark_version`; note in commit

## Cost ceiling

Each benchmark run issues N scenarios × 3 median calls at the model's
temp-0 price. For Claude Sonnet 4.6 at the current rate, a 10-scenario
benchmark runs at roughly $0.30 per execution. The global CI ceiling
(`benchmarks.yml`) is 500 total LLM calls per run across all
benchmarks to bound cost per push.

## Judge-mode fields (additive, PLAN-011 Phase 3)

The runner optionally runs an LLM-as-judge pass (and/or a deterministic
fallback) via `--judge-mode={fixture|llm|both|fallback}`. When the
judge is invoked, the following OPTIONAL fields are added to the
`benchmark_run` audit event. Consumers that do not understand them
MUST ignore them (additive compatibility).

| Field | Type | When present | Meaning |
|---|---|---|---|
| `judge_mode` | string | always (Phase 3+) | `"fixture"` \| `"llm"` \| `"both"` \| `"fallback"`. |
| `judge_adapter` | string | `judge_mode != "fixture"` and judge ran | `"gemini"` \| `"openai"` \| `"local"` \| `"fallback"`. MUST differ from `CEO_HOOK_ADAPTER` (cross-provider guard, ADR-030). |
| `judge_score_forward` | float | judge ran | 0–10 integer grade from the forward pass (rubric before response). |
| `judge_score_reverse` | float | judge ran | 0–10 integer grade from the reverse pass (response before rubric). Position-bias control per §H5. |
| `judge_delta` | float | judge ran | `abs(forward - reverse)`. `>0.5` flags the grade for human review. |
| `fallback_score` | float | `judge_mode="fallback"` or silent fallback | Deterministic keyword-match score (0–10). Used for audit parity when the LLM judge was unreachable. |

The judge reads ONLY the default-deny payload defined in
`SPEC/v1/judge-payload.schema.md`. The committed prompt and its SHA-256
("golden prompt hash") are pinned in ADR-030.

### Disagreement veto

When `judge_mode="both"` and the fixture-score (normalised to [0, 1])
differs from the judge-score/10 by more than 0.2, the runner emits an
additional `veto_triggered` event:

```json
{
  "action": "veto_triggered",
  "hook": "run_skill_benchmark",
  "reason_code": "benchmark_judge_disagreement",
  "reason_preview": "benchmark=<id> fixture=<f> judge=<j> delta=<d>"
}
```

This is advisory in PLAN-011; enforcement (κ ≥ 0.7 flip criterion) is
deferred to Sprint 12+ per ADR-030.

## References

- PLAN-008 Phase 5 (introduces this schema file)
- PLAN-011 Phase 3 (adds judge-mode fields; §H5/§H6/§H7 consensus)
- ADR-015 (Reflexion v2 outcome loop — uses benchmarks to write lessons)
- ADR-030 (LLM-as-judge methodology)
- `SPEC/v1/judge-payload.schema.md` (default-deny payload)
- `.claude/scripts/run-skill-benchmark.py`
- `.claude/scripts/benchmark-judge.py`
- `.claude/scripts/benchmark-fallback-scorer.py`
- `.github/workflows/benchmarks.yml`
