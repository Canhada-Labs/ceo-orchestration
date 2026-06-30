# Function-length policy

> **Default rule:** Python functions ≤50 LoC. Exceptions need an
> explicit `# justified: <reason ≥10 chars>` comment inside the
> function body.
>
> **Mode:** advisory at v1.11.2 (CI prints findings, exits 0).
> Promotion to strict gate is a calendar-soak decision, not a
> token-spendable one — see §Path to strict-gate at the bottom.

## Why a length budget

Long functions correlate with:

- **Higher mutation-test escape rate.** Larger functions hide more
  paths a mutation can survive.
- **Lower review fidelity.** Adversarial reviewer rubric (PLAN-034)
  measures more reliable critique on functions ≤50 LoC.
- **Harder bisection.** When a regression lands inside a
  150-LoC function, `git blame` points at one commit but the
  fault could be on any of the 150 lines.

The 50-LoC default is a **convention**, not a hard limit. Some
problems genuinely need a longer single-function answer (state
machines, complex parsers, regex-driven dispatch tables). The
`# justified:` comment makes the convention auditable: a long
function with a stated reason is a deliberate exception, not
drift.

## How the detector works

The script `.claude/scripts/check-function-length.py` walks every
`.py` file under `.claude/` (or a custom `--root`), parses with
`ast`, and emits one record per `def` / `async def`. A function is
a **violation** when:

- LoC (def line through last body line, inclusive) > threshold, AND
- No comment line in the function body matches
  `# justified: <reason of ≥10 characters>`.

### Excluded by default

The detector skips path fragments unrelated to production code:

- `__pycache__` / `.pytest_cache` / `build` / `dist` / `.egg-info`
  directories
- Path fragments: `/staged-code/`, `/staged-wave-`, `/staged-spec/`,
  `/audit-v2/staged-`

Adopters can pass `--exclude` (repeatable) to add custom fragments,
e.g. `--exclude /vendor/` or `--exclude /third_party/`.

## Usage

### Advisory check (default)

```bash
python3 .claude/scripts/check-function-length.py
# Exits 0; prints WARN: N functions over 50 LoC + top 10 by LoC
```

### Stricter threshold

```bash
python3 .claude/scripts/check-function-length.py --threshold 75
```

### Strict gate (exit 1 on any violation)

```bash
python3 .claude/scripts/check-function-length.py --strict
# Exit 1 if any un-justified function exceeds 50 LoC
```

### Machine-readable

```bash
python3 .claude/scripts/check-function-length.py --json
```

JSON shape:

```json
{
  "threshold": 50,
  "total_functions": 8887,
  "violations": 342,
  "items": [
    {
      "file": ".claude/hooks/_lib/audit_hmac.py",
      "function": "verify_chain",
      "line": 702,
      "end_line": 920,
      "loc": 219,
      "justified": false
    }
  ]
}
```

## How to justify a function

Add a `# justified: <reason ≥10 chars>` comment **inside the function
body** (not above the `def`). The first matching comment wins.

```python
def verify_chain(...) -> VerifyResult:
    # justified: 6-stage chain integrity verifier kept in one
    # function for readability — splitting hides the linear flow.
    # Each stage maps 1:1 to a numbered §audit-log.schema.md row.
    ...
```

The reason is **not** validated for content beyond the 10-char
floor. The intent is auditability ("someone made a deliberate call"),
not policy enforcement.

## What's currently flagged

At v1.11.2 the framework's own code has **342 functions** flagged
(of ~8,887 total). The top 10 by LoC are visible in CI advisory
output; the longest is `audit_hmac.py::verify_chain` at 219 LoC.

These existed before the policy was introduced. The advisory mode
gives the framework time to:

1. Justify the legitimate exceptions (e.g. `verify_chain` is a
   single linear chain integrity check that benefits from being
   readable end-to-end)
2. Refactor the un-justified ones (the `_compile_predicate` family
   in `policy.py` is a candidate)

## Path to strict-gate

Strict-gate promotion (advisory → required-pass) is a **calendar
decision**, not token-spendable:

| Gate | Status | Trigger / target date |
|---|---|---|
| **Advisory** (current) | **active since 2026-04-27** (Session 69 / commit `268c44a`) | CI prints, exits 0. No PR blocked. |
| **Soft gate** | proposed for **2026-05-04** (Day 7 of soak) | Advisory + CI shows function-length WARN as PR comment. PR may still merge. |
| **Strict gate** | proposed for **2026-05-11** (Day 14 of soak) | CI fails on any new violation. Existing violations grandfathered via allowlist. |
| **Hard gate** (long-term) | open-ended | All violations must be justified or refactored. Allowlist removed. |

Promotion criteria (soft → strict):

- Top-10 by LoC all justified or refactored
- Total violation count stable (no upward drift across 14-day window)
- 14-day soak with **0 false-positives** across the framework's CI runs

### Soak window log (2026-04-27 → 2026-05-11)

| Day | Date | Advisory output | False-positives | Owner sign |
|---|---|---|---|---|
| 0 | 2026-04-27 | Detector activated | 0 | (initial) |
| 1 | 2026-04-28 | Stable | 0 | (Day 1 audit-v2 P1 #11 stage) |
| 2-13 | tracking | TBD | TBD | (weekly Owner snap) |
| 14 | 2026-05-11 | Soft-gate decision | total: TBD | Owner GPG required |

Owner can **antecipate** the soft-gate flip (skip the 14-day soak)
via a `round-N/approved.md` sentinel if the advisory shows zero
drift after Day 7. Antecipation MUST cite the specific runs
inspected and the FP count.

The framework's own code makes the soft → strict transition first,
then publishes the migration recipe for adopters via this doc's
§Migration recipe (added when the framework lands strict).

## For adopters

Default behavior at install:

- Advisory only. CI prints findings, exits 0. No surprise.
- The detector runs against your `.claude/` only — your project's
  `src/`, `app/`, `lib/`, etc. are NOT scanned unless you pass
  `--root .` and explicitly opt in.

To opt your own code into the same detector:

```bash
python3 .claude/scripts/check-function-length.py --root src/
```

To gate your CI on it:

```yaml
# .github/workflows/code-quality.yml
- name: Function length
  run: |
    python3 .claude/scripts/check-function-length.py \
      --root src/ \
      --strict
```

The framework does **not** force this on adopter code. The
advisory inside `.claude/` is for framework dogfood; adopting
the rule for your own code is a per-team decision.

## References

- Detector: `.claude/scripts/check-function-length.py`
- Tests: `.claude/scripts/tests/test_check_function_length.py`
- Adversarial reviewer rubric (research): PLAN-034
- Mutation-test correlation (data): `.claude/plans/PLAN-040/`

## Last reviewed

2026-04-28 (Session 71 / Wave D-3 — soak window dates fixed at
2026-04-27 → 2026-05-11; soft-gate flip proposed for Day 7
2026-05-04 with Owner sentinel antecipation option).
