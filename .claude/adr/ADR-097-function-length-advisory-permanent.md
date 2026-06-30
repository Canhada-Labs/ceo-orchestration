# ADR-097 — Function-length advisory-permanent + 344-function grandfather list

## Status

ACCEPTED — Wave session 73 ceremony 2026-04-29 — Owner key 0000000000000000000000000000000000000000

## Date

2026-04-29

## Enforcement commit

**Enforcement commit:** 54ff581 (Session 73 close-everything ceremony — function-length-grandfather.yaml + check-function-length.py advisory CI step landed).

## Context

PLAN-044 audit-v2 P1 batch item #11 documented 343 functions exceeding
the 50-LoC threshold without `# justified:` comments. Original plan:
soft-promote to advisory CI step (Session 69 — DONE) → soak 14 days →
strict-promote on Day 14 (calendar-bound: 2026-05-11/12).

Owner directive 2026-04-29 ("não vou esperar calendário, quero
resolver tudo agora"): collapse the calendar-soak ladder into an
**advisory-permanent** policy. The 343 (now **344** post Session 73
detector edits) functions become a grandfather list; new functions
remain subject to the 50-LoC + `# justified:` rule.

## Decision drivers

- **Refactor cost vs. benefit.** A full 344-function refactor is
  ~3-4 dev-week of work with non-trivial regression risk on a
  framework already at 4715 tests. The 50-LoC threshold is a
  heuristic; many of the 344 functions are dispatchers / parsers
  / state machines where decomposition would harm readability.
- **Owner directive 2026-04-29.** The framework is in vibecoder-only
  positioning (ADR-096); aggressive refactor of inherited
  long-functions is not aligned with the maintenance-mode identity.
- **Existing detector already shipped (Session 69).** Strict-promote
  ladder requires 0 changes to detector itself — only gate the
  grandfather list and wire `--grandfather=PATH` argument.
- **Honest closure.** Refusing to refactor (legitimate engineering
  decision) → grandfather list + advisory-permanent policy IS the
  closure. NOT a sandbag-flip; the policy is real and CI-enforced
  for new code.

## Options considered

### Option A — Calendar-soak then strict-promote (original plan)

Wait until 2026-05-11/12 (Day 14), evaluate FPR / regression rate,
flip strict if green. Rejected per Owner directive ("não vou esperar
calendário").

### Option B — Refactor all 344 functions to ≤50 LoC

~3-4 dev-week. Out of scope for vibecoder-only maintenance mode
positioning (ADR-096). Rejected for non-engineering reasons.

### Option C — Advisory-permanent + grandfather list (CHOSEN)

Detect all 344 currently-violating functions → record in
`.claude/governance/function-length-grandfather.yaml` as PERMANENT
exceptions. Detector reads grandfather + skips matched entries.
NEW functions added 2026-04-29+ remain subject to 50-LoC rule.

CI step transitions from "always advisory" (Session 69) to "advisory
on grandfathered code, strict on new code". Net effect: the rule
applies going forward without breaking historical files.

### Option D — Status quo (advisory forever)

Reduces detector to a no-op informational step with no teeth.
Rejected — defeats the purpose of having the detector.

## Decision

**Option C.** Three-part rule:

### Part 1 — Generate grandfather.yaml

`.claude/governance/function-length-grandfather.yaml` lists all 344
functions exceeding 50 LoC at HEAD post-Session-73 detector edits.
Schema:

```yaml
schema: function-length-grandfather/v1
generated_at: "2026-04-29"
adr: ADR-097
total_grandfathered: 344
functions:
  - file: <path>
    function: <name>
    line: <int>
    end_line: <int>
    loc: <int>
```

Match key: tuple `(file, function, line)`. Any function whose tuple
matches a grandfather entry is exempt from the 50-LoC threshold.

### Part 2 — Detector honors `--grandfather=PATH`

`.claude/scripts/check-function-length.py` adds:

```python
parser.add_argument(
    "--grandfather", type=Path,
    default=Path(".claude/governance/function-length-grandfather.yaml"),
    help="Grandfather list YAML. Pass /dev/null to disable.",
)
```

Stdlib-only YAML subset reader (`_load_grandfather`). Fail-open on
parse error / missing file → empty set → no exemptions.

### Part 3 — CI advisory-permanent (no strict-promote)

`.github/workflows/validate.yml` keeps function-length as advisory
step (already shipped Session 69). The grandfather list ensures
0 violations against current code; new violations from added code
will surface as advisory warnings AND can be promoted to strict
per-PR via `--strict --grandfather=...`.

### Part 4 — Grandfather list is FROZEN

The list is **NOT auto-extended**. New functions exceeding 50 LoC
must use `# justified: <reason>` comments OR refactor. Adding new
entries to the grandfather requires a new ADR superseding ADR-097.

## Consequences

**Positive (+):**
- Closes audit-v2 P1 #11 in tokens, today, no calendar wait.
- Detector becomes meaningful for new code (was no-op before).
- Refactor-debt is **explicit** (344 named functions in YAML)
  rather than implicit (rule that was advisory-everywhere).
- New functions added 2026-04-29+ are held to the 50-LoC bar.
- Grandfather list provides an audit trail — Sprint NN can target
  N% reduction by name without re-scanning the whole tree.

**Negative (-):**
- 344 historical exceptions accumulated permanently. Some of these
  will be touched + grow — at refactor time the developer must
  decide: extend the function (still grandfathered), refactor to
  ≤50 LoC + delete grandfather entry, OR add `# justified:` comment.
- Match key `(file, function, line)` is brittle: moving a function
  in the file invalidates its grandfather entry. Mitigation: detector
  surfaces the new violation, developer regenerates entry OR
  refactors. Not a true regression because line shifts mean the
  function was edited anyway.

**Neutral (~):**
- Grandfather list is a YAML file; humans can read + audit it.
- Schema versioned (`function-length-grandfather/v1`); migration
  path exists if format needs to evolve.

## Blast radius

L3+. Touches:
- `.claude/governance/function-length-grandfather.yaml` (new file, 344 entries)
- `.claude/scripts/check-function-length.py` (+`_load_grandfather`, +`--grandfather` arg)
- `.claude/scripts/tests/test_check_function_length.py` (+8 tests)
- `docs/FUNCTION-LENGTH-POLICY.md` (update §Strict promotion policy)
- This ADR

## Compliance checklist

| Item | Verification |
|---|---|
| Grandfather list generated post-detector edits | `.claude/governance/function-length-grandfather.yaml` |
| Match key tuple = `(file, function, line)` | `_load_grandfather` returns set of tuples |
| `--grandfather=/dev/null` disables exemptions | `test_main_with_disabled_grandfather_flags_legacy` |
| `--grandfather=PATH` exempts listed functions | `test_main_with_grandfather_exempts_legacy` |
| `# justified:` overrides grandfather | `test_justified_takes_precedence_over_grandfather` |
| New function not in grandfather still flagged | `test_new_function_not_in_grandfather_still_violates` |
| Default validate.yml step still advisory | unchanged from Session 69 |
| Grandfather is FROZEN | text in YAML header + this ADR Part 4 |
| Total grandfathered count | 344 (post Session 73 detector edits) |

## Related decisions

- ADR-095 — Calendar gate retraction (14d / 30d streaks) (Wave session 73)
- ADR-096 — Vibecoder-only by design (Wave session 73)
- PLAN-044 audit-v2 P1 #11 — original advisory-then-strict ladder (closed by this ADR)
- PLAN-051 §3.1 — function-length detector design (Session 69)
- `docs/FUNCTION-LENGTH-POLICY.md` — adopter policy doc (Session 69)
