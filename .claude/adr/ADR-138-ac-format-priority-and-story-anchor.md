---
id: ADR-138
title: AC format extension — priority + user-story + path discipline
status: ACCEPTED
proposed_at: 2026-05-20
proposing_session: S147
related_plans: [PLAN-110]
related_adrs: [ADR-115, ADR-125]
risk_tier: A
debate_required: true
accepted_at: 2026-05-28
accepting_session: S177
authorization: PLAN-117 WS-B sentinel `.claude/plans/PLAN-117/architect/round-4/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-138 — AC format priority + story + path

**Enforcement commit:** n/a (documentation-only — text-only AC-format doctrine; no parser ships, §Future Work RESERVED)

## Context

GitHub's `spec-kit` enforces a discipline in `tasks.md` template
(`templates/commands/tasks.md:L378-L404`) that ceo-orchestration's
PLAN ACs currently lack: every task line declares optional priority
prefix `[P0]/[P1]/[P2]/[P3]`, optional user-story group `[USn]`, and
**mandatory** file path `[path/to/file.py]`. The structure makes
tasks both LLM-parsable (execution dispatcher reads priority + path)
and human-scannable.

Example spec-kit task line:

```
- [P0] [US1] [src/cli/parser.py] Implement argparse with --verbose flag
```

ceo-orchestration's ACs today are typically descriptive prose with
implicit paths (the path is inferable from surrounding context but
not always explicit). Several recent plans (PLAN-107, PLAN-108,
PLAN-110 itself) have de-facto adopted the `[path]` convention for
clarity but with no schema enforcement.

The doctrinal question Wave B adjudicates: **should PLAN-SCHEMA.md
formalize this AC format as optional opt-in for new plans, preserving
backward compatibility for existing PLANs 001-109?**

## Decision

**PROPOSED: ADOPT as text-only doctrine** — formalize the spec-kit
AC line convention as **optional opt-in** in PLAN-SCHEMA.md, with
explicit backward compatibility for existing PLANs.

### Format (text-only doctrine)

```
- [P0] [US1] [.claude/skills/core/<name>/SKILL.md] Description ...
```

Where:

- **`[P0]/[P1]/[P2]/[P3]`** — optional priority. Defaults to `[P1]` if
  absent. Higher P = more urgent.
- **`[USn]`** — optional user-story group. Wave-level if absent.
- **`[path]`** — RECOMMENDED file-anchor.

### Backward compatibility

- PLANs 001-109 remain **valid without modification**.
- ACs without `[P?]` prefix default to `[P1]` semantically.
- ACs without `[USn]` group are wave-level (no story grouping).
- ACs without `[path]` remain valid (anchor inferable from context).

### Enforcement boundary — TEXT-ONLY (no parser ships in v1.39.0)

- PLAN-SCHEMA is currently consumed by:
  - `validate-governance.sh` for filename/subdir invariants.
  - `.claude/hooks/_lib/plan_frontmatter.py` for YAML frontmatter parsing.
- **Neither parses AC-line syntax today.**
- Adding an AC-line parser is **OUT OF SCOPE** for v1.39.0.

### Future Work (RESERVED)

A separate PLAN-NNN may implement an AC-line parser in the future,
gated on:

1. Codex R2 ≥3-iter ACCEPT on the parser plan.
2. Owner GPG-signed sentinel for hook addition.
3. Backward-compat re-test of all PLANs 001-109+.

The parser plan would target an advisory-only hook initially (warn on
non-conforming new ACs); promotion to enforcing would be a separate
L3+ doctrine change.

## Consequences

### Positive

- **Improved scannability**. New plans following the format are easier
  for human + LLM readers to triage by priority and locate by path.
- **Cross-plan consistency**. Recent plans (PLAN-107, PLAN-108,
  PLAN-110) de-facto adopt `[path]`; this ADR formalizes the
  convention rather than letting it drift.
- **Zero migration cost**. PLANs 001-109 unchanged.
- **Reversible**. Text-only addendum — single git revert removes the
  doctrine; no parser to roll back.

### Negative

- **No enforcement** until a follow-up parser plan ships. Adopters may
  ignore the convention. Mitigated by `coverage-audit` skill (PLAN-110
  Wave A) flagging missing `[path]` as Underspecification HIGH.
- **Adopter friction (minor)**. Style change for new plan authors.

### Neutral

- §Future Work clause reserves parser implementation for separate
  ceremony — opens optionality without committing.

## Alternatives Considered

### Alternative 1: ADOPT with parser (full enforcement in v1.39.0)

Pros: enforcement bite. Cons: +1 hook + +1 ADR + +20 tests + re-test
PLANs 001-109. **REJECTED** — too big for v1.39.0; scope creeps Wave B
beyond its tier classification.

### Alternative 2: ADOPT text-only with §Future Work parser (this ADR)

Pros: low risk, reversible, formalizes drift toward consistency.
Cons: no enforcement bite. **RECOMMENDED**.

### Alternative 3: SKIP

Pros: zero migration. Cons: lets the de-facto convention continue
drifting unanchored. **REJECTED** — Wave B explicit recommendation.

## References

- spec-kit `templates/commands/tasks.md:L378-L404` — `[P?]` `[USn]` `[path]` format
- PLAN-SCHEMA.md §AC format addendum (PLAN-110 Wave B deliverable)
- PLAN-110 §4 Wave B acceptance metric
- `coverage-audit` skill (PLAN-110 Wave A) — flags missing path as Underspecification HIGH
- ADR-115 §3 — schema-evolution doctrine

## Notes

PROPOSED status only. §Future Work clause reserves parser
implementation for a follow-up PLAN-NNN if Owner approves at separate
ceremony. PLAN-110 itself uses the new AC format in its body — eat
own dog food. See PLAN-110-spec-kit-adoption-sweep.md §4.
