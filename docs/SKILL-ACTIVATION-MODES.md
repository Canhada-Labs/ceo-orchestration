# Skill activation modes (PLAN-110 Wave H doctrine)

> **Doctrine declaration**: every skill's `activation_mode:` frontmatter
> key declares one of three values. Promoting a skill across modes is
> an L3+ doctrine change requiring its own ADR + debate + kill-switch.
> Anchored to ADR-125 §Part 3.

## The three modes

| Mode              | Definition                                          | Token spend in steady state |
|-------------------|-----------------------------------------------------|------------------------------|
| `manual-only`     | Owner invokes via `/spawn <skill>` ONLY.            | ZERO                         |
| `event-driven`    | Triggered by a specific tool-call pattern via hook. | ~1-5k per trigger (rare)     |
| `default-on`      | Loaded into context at session start.               | Persistent (Tier-B/C only)   |

## Tier mapping (ADR-125 §A)

- **Tier A** (NO token spend in steady state; LLM invocation NOT OK):
  must be `manual-only`. PLAN-110 ships 3 such skills:
  - `coverage-audit` (manual-only + read_only=true)
  - `spec-clarify` (manual-only)
  - `requirement-quality-checklist` (manual-only)
- **Tier B** (observable + non-blocking-advisory): may be `event-driven`
  or `manual-only`. Requires ADR.
- **Tier C** (default-OFF; opt-in via sentinel): may be `default-on`
  iff sentinel approved + kill-switch wired. Requires ADR + 6-layer
  kill-switch chain.

## Promotion ceremony (manual-only -> event-driven)

Each promotion is L3+ and requires:

1. New ADR (e.g., ADR-NNN-skill-<name>-promotion).
2. `/debate start PLAN-NNN-skill-<name>-promotion` with 5-archetype R1.
3. Codex MCP R2 ACCEPT (≥3-iter bundle review).
4. Kill-switch declared in the ADR (env var or sentinel file).
5. SPEC v1 row for any new audit action emitted by the event-driven trigger.
6. Owner GPG-signed sentinel for kernel override (if `_KNOWN_ACTIONS` extension).

## Promotion ceremony (event-driven -> default-on)

L3+ with additional gates:

7. 30-day soak in `event-driven` mode with audit-log telemetry proving
   trigger rate is bounded.
8. Cost-envelope ADR (port of ADR-133 §Part 1) if token spend > 10k/session.
9. Federation impact review (ADR-129 / ADR-135) if cross-machine fanout.

## Detection script

`.claude/scripts/check-skill-activation-mode.py` — advisory CI script
emits warning if a new skill is added without `activation_mode:` in
frontmatter. Fail-OPEN. Non-blocking.

## Anti-pattern

A future session that adds `/coverage-audit` to `/ceo-boot` Tier-S
default checks "because it would be useful as a default" re-classifies
the skill from Tier-A manual to Tier-B+ default-on. **This requires
the full promotion ceremony above** — NOT a settings.json one-liner.

## Reference

- ADR-125 §Part 3 (appended by Wave H — see ADR-125-AMEND-1 if amended)
- PLAN-110 Wave H acceptance metric
- spec-kit `templates/commands/plan.md:L275-L303` (anti-goal #1 anchor)
