---
description: Toggle terse output mode for this session. Sacrifices prose polish for token efficiency in exploratory flows. VETO auto-off for code-review / security / compliance / debate consensus.
argument-hint: "on|off|status"
---

# /terse — Terse Mode toggle

Usage: `/terse on`, `/terse off`, or `/terse status`.

Toggles session-scoped terse output via the `CEO_TERSE_MODE` environment
convention. The rules and VETO auto-off contract live in
`.claude/skills/core/terse-mode/SKILL.md` (ship gate tracked in
`PLAN-047/phase-2-sp019-deferred.md` — skill body is proposal SP-019
pending `create-new-skill` flow landing). This slash exists now so
callers can rehearse the toggle shape; the runtime marker injection
into spawn prompts lands when the Wave 8 mega-kernel batch applies
`.claude/plans/PLAN-047/kernel-batch-terse-veto.py`.

## Argument parsing

The user invoked: `/terse $ARGUMENTS`.

Parse the first token as the subcommand. Accept case-insensitive
`on` / `off` / `status`. Default (no argument) = `status`. Reject
any other token with a short usage line.

## `on` — activate terse mode

1. Emit an audit breadcrumb `terse_mode_start` via `_lib.audit_emit`
   with `ts` = now (UTC ISO-8601 with `Z` suffix).
2. Print a one-line confirmation:
   `terse-mode: ON (fragments OK in exploratory; VETO roles unaffected)`.
3. Do NOT try to mutate the session environment — Claude Code agents
   cannot set env vars for their own parent session. Instead, bias
   this turn's subsequent tool outputs toward:
   - Tool first. Result first.
   - Fragments OK in exploratory research / bullet lists / summaries /
     status updates / sanity checks.
   - Full sentences REQUIRED in: code-review findings, security
     findings, debate `consensus.md`, `verdict.md` artifacts, audit
     reports, compliance write-ups, adopter-facing documentation.
   - Never truncate code. Never drop numbers. Never use ellipsis to
     hide content.

## `off` — deactivate terse mode

1. Emit `terse_mode_end` with `mode_end_ts` = now and
   `output_tokens_saved_estimate` = best-effort integer (compute from
   `ceo-cost.py --session` delta if available; else `0`).
2. Print: `terse-mode: OFF (prose quality restored)`.
3. Revert biasing — subsequent turn output returns to default prose.

## `status` — print current state

Print one of:

- `terse-mode: OFF` — no `terse_mode_start` breadcrumb in this session
  without a matching `terse_mode_end`.
- `terse-mode: ON since <ISO-8601-ts>` — the most recent
  `terse_mode_start` has no matching end.

Include a brief note on which VETO roles would auto-disable:
`code-reviewer, security-engineer, qa-architect (verdict writing),
compliance-specialist, CEO writing consensus.md / verdict.md`.

## VETO auto-off contract (advisory until Wave 8 lands)

Until the `kernel-batch-terse-veto.py` patch lands in
`check_agent_spawn.py`, VETO-role spawn prompts do NOT yet receive
the `## TERSE-MODE-DISABLED` marker automatically. CEO MUST manually
respect the auto-off contract when spawning canonical-5 agents during
terse-mode sessions — full-prose outputs for code-reviewer /
security-engineer / qa-architect / compliance-specialist even when
`/terse on` is active.

## Measurement

Session cost delta is observable via `.claude/scripts/ceo-cost.py
--stream`. After the Wave 8 kernel lands, `.claude/scripts/audit-tokens.py`
will additionally surface any terse-mode sessions via the
`terse_mode_session` detector derivation.
