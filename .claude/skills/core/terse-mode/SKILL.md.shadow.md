---
name: Terse Mode
description: Output-economy skill for research-heavy flows. Sacrifices prose polish for token efficiency in exploratory loops. VETO auto-off for code-review, security-engineer, compliance, debate consensus, audit artifacts.
trigger: CEO activates via /terse on; auto-off for VETO roles; check_agent_spawn.py injects TERSE-DISABLED marker into spawn prompts of canonical-5.
---

# Terse Mode

## Identity

When `/terse on` is active, CEO and non-VETO sub-agents produce
minimally-verbose outputs. Target: -40-60% output tokens in
exploratory research, bullet-list summaries, short factual answers.

## Rules

- **Tool first. Result first.** State the action/outcome in line 1.
- **Fragments OK** in: exploratory research, bullet lists, summaries,
  status updates, sanity checks.
- **Full sentences REQUIRED** in: code-review findings, security
  findings, debate consensus.md, verdict.md artifacts, audit reports,
  compliance write-ups, adopter-facing documentation.
- **Never truncate code** — code blocks remain verbatim.
- **Never drop numbers** — quantitative claims carry units + source.
- **Never use ellipsis to hide content** — if a finding matters,
  name it.

## VETO auto-off

Terse mode AUTO-DISABLES for these roles (hardcoded in
check_agent_spawn.py P0-TERSE-VETO guard):

- code-reviewer (merge VETO)
- security-engineer (auth/crypto VETO)
- qa-architect (when writing verdict.md)
- compliance-specialist (LGPD/GDPR findings)
- CEO writing consensus.md or verdict.md

For these roles, spawn prompt receives injected marker:
`## TERSE-MODE-DISABLED — VETO role requires full-prose rationale`.

## Toggle

- `/terse on` — activate for session
- `/terse off` — deactivate
- `/terse status` — print current state

## Measurement

Session cost delta is tracked via ceo-cost.py. Terse-mode sessions
emit `terse_mode_session` audit event with `mode_start_ts`,
`mode_end_ts`, `output_tokens_saved_estimate` fields.

## Adopter guidance

Terse mode IS NOT for:
- Production deploys (full audit trail needed)
- Customer-facing artifacts (quality over economy)
- Debate rounds (consensus quality depends on full reasoning)

Terse mode IS for:
- Research loops (scanning docs, grep-like tasks)
- Progress updates between milestones
- Internal logs where CEO is the only reader
- Repetitive sanity checks
