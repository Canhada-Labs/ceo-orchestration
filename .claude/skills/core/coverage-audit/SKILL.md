---
name: coverage-audit
description: Read-only cross-artifact consistency analyzer (port of spec-kit /analyze). 6 detection passes (Duplication/Ambiguity/Underspec/Constitution-Align/Coverage/Inconsistency) with CRITICAL/HIGH/MEDIUM/LOW severity. Capped at 50 findings. Manual-only invocation via /spawn coverage-audit <PLAN-NNN>. Never modifies files.
owner: Staff Code Reviewer + QA archetype (cross-cut)
domain: core
priority: 2
risk_class: low
context_budget_tokens: 1400
activation_mode: manual-only
read_only: true
inactive_but_retained: false
stack: []
plan_origin: PLAN-110
added_at: 2026-05-20
---

# coverage-audit — read-only cross-artifact consistency analyzer

> **Activation**: manual-only via `/spawn coverage-audit <PLAN-NNN>`.
> Never invoked by `/debate`, `/execute`, or `/ceo-boot` by default.
> Tier-A defensibility per ADR-125 §143-150 (zero token spend in steady state).

## Purpose

Port of github/spec-kit's `/speckit.analyze` (`templates/commands/analyze.md:L340-L381`).
Performs 6 detection passes across the loaded PLAN + canonical roadmap +
findings-master + ADR ledger. **STRICTLY READ-ONLY** — never modifies files
(enforced by `read_only: true` frontmatter + skill text contract).

## 6 detection passes (severity-classified)

| # | Pass | Severities flagged |
|---|------|---|
| 1 | Duplication        | HIGH (same AC text in 2+ plans) / MEDIUM (paraphrase) |
| 2 | Ambiguity          | HIGH (vague terms — "should", "may", "TBD"; **LIVE `[NEEDS CLARIFICATION: …]` marker** — PLAN-SCHEMA §14) / LOW (jargon w/o anchor) |
| 3 | Underspecification | CRITICAL (AC missing path) / HIGH (AC missing severity) |
| 4 | Constitution Alignment | CRITICAL (CLAUDE.md drift vs PLAN-NNN.related_adrs) |
| 5 | Coverage Gaps      | HIGH (AC -> no test file) / MEDIUM (AC -> 1 test only) |
| 6 | Inconsistency      | HIGH (status conflict draft vs reviewed) / LOW (date drift) |

Severity tiers: CRITICAL / HIGH / MEDIUM / LOW.
Limit: **50 findings max** per invocation; overflow summarized with
`+N more findings (run with --no-cap for full output)`.

### Pass #2 (Ambiguity) — inline clarification markers (PLAN-138 Wave A)

Pass #2 additionally flags a **LIVE** `[NEEDS CLARIFICATION: <question>]`
marker at **HIGH** severity. A LIVE marker is the actionable
colon-question-bracket token appearing OUTSIDE fenced code blocks and
inline-backtick spans (a backticked example like the token in this
sentence is EXEMPT, not a finding). This mirrors PLAN-SCHEMA §14 and the
`check-staleness.py` / `validate-governance.sh` advisory detectors. The
read-only contract is unchanged: the skill reports the marker, it never
edits the plan to remove it.

## Invocation contract

```
/spawn coverage-audit PLAN-NNN
```

Output: structured markdown table with deterministic ordering
(stable sort key = `(severity, pass_id, path, line)`). Reproducible
across 3 runs (same input -> same output hash).

## Constitution alignment check

Cross-checks PLAN-NNN's `related_adrs:` frontmatter against:

- CLAUDE.md §Critical Rules (current doctrinal anchors)
- PROTOCOL.md §Plan->Debate->Execute (governance contract)
- Each cited ADR-NNN status (must be ACCEPTED, not RETRACTED/SUPERSEDED)

Flags `CRITICAL` if any related_adr is RETRACTED.
Flags `HIGH` if any related_adr is SUPERSEDED without `superseded_by:` chain
recovery.

## Output format

```
# coverage-audit PLAN-NNN — generated YYYY-MM-DD

| Severity | Pass | Path | Line | Finding |
|----------|------|------|------|---------|
| CRITICAL | 4    | ... | ...  | ...     |
| HIGH     | 1    | ... | ...  | ...     |
...

# Summary
- Critical: N
- High:     N
- Medium:   N
- Low:      N
- Total:    N (capped at 50; +M more) [if applicable]
```

## Anti-pattern boundary

- Skill does NOT call `/debate` or `/execute`.
- Skill does NOT write to any file (read_only enforced).
- Skill does NOT trigger LLM calls when not invoked.
- Skill must NOT be added to `/ceo-boot` Tier-S default checks without
  ADR + kill-switch + debate (per Wave H doctrine).

## Tests

See `tests/skills/test_coverage_audit_skill.py` — 5 fixture cases asserting:
deterministic ordering, ≤50 findings, severity classification correct,
`activation_mode: manual-only` flag respected, `read_only: true` flag respected.

## References

- Port source: github/spec-kit `templates/commands/analyze.md:L340-L381`
- PLAN-110 Wave A acceptance metric
- ADR-125 §143-150 (Tier-A defensibility)
- Wave H activation-mode doctrine
