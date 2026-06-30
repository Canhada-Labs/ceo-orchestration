# Token-economy adopter guide

> Companion to PLAN-047 (Phase 1 ghost-token detectors + Phase 3
> `/audit-tokens` CLI + Phase 2 terse-mode opt-in). This document is
> adopter-facing: read it when you want to understand why your
> CEO-orchestration session cost what it cost and how to bring the
> number down without losing governance.

## Who this is for

- Adopters running `ceo-orchestration` in production repos and
  asking "where are my tokens going?"
- Framework CEOs dogfooding the same orchestration layer.
- Security / compliance reviewers who need to confirm the
  observability surface is advisory (no block, no VETO).

It is NOT for prompt-engineering novices — assume you already know
the Claude Code API, how `Task` tool calls bill, and how
`model:` frontmatter in `.claude/agents/*.md` routes dispatch.

## Why token observability

`ADR-052` dispatches models by role (Opus for VETO work, Sonnet for
most archetypes, Haiku for devops / boilerplate). It is **static** —
the mapping is read from `.claude/agents/*.md` frontmatter at spawn
time. Without a feedback loop, an adopter cannot tell whether the
actual usage matches the dispatch intent. PLAN-047 closes the loop
with six detectors over `audit-log.jsonl`.

## What the framework already does (before you touch anything)

Five of the ten habits from the 2026-04 viral "stop burning tokens"
post are implemented structurally — adopters do not need to learn
them as habits, the framework does them by design.

| Viral habit | Framework mechanism | Notes |
|---|---|---|
| Haiku for simple tasks | ADR-052 dispatch tier | `devops` archetype + boilerplate routed to Haiku via `model:` frontmatter |
| Memory & user preferences | auto memory subsystem | `~/.claude/projects/<slug>/memory/` loaded every session |
| Projects for recurring files | CLAUDE.md Gate-1 load | Project-specific context bootstraps the session |
| Turn off unused features | Skill gating via CLAUDE.md | Only skills referenced in team.md ROUTING TABLE participate in dispatch |
| Batch questions | CEO protocol | Plan→Debate→Execute batches related work into one spawn |

Five remain adopter behavior — no framework mechanism can enforce
them, but the adopter guide below tells you when each one moves the
needle.

## The 6 detectors (Phase 1)

All detectors read `audit-log.jsonl`, emit a `Finding` dataclass, and
never block. See `.claude/scripts/detectors/` for the source.

### `retry_churn`

**Signal:** same `(session_id, subagent_type, skill, prompt_len_bucket)`
spawned 3+ times within a 30-minute window.

**Root cause (typical):** a prompt the CEO keeps re-issuing because
the sub-agent response isn't good enough; a failing acceptance
criterion that the CEO didn't name explicitly; a flaky test the
CEO keeps asking the QA agent to "run again".

**Adopter action:** open the audit-log at the offending timestamp,
read the spawn prompt, and make the acceptance criterion
mechanical (e.g. "`pytest -q` exits 0" instead of "tests look
fine"). Re-prompt once with the sharper criterion.

### `tool_cascade`

**Signal:** run of 10+ consecutive short-response spawns in a single
session (tokens_out under a cap).

**Root cause:** CEO is using sub-agent spawns as a search engine.
Each spawn burns the spawn-prompt budget (~500–2000 tokens) and
returns one line. Would have been a `Grep` or `Glob` call.

**Adopter action:** prefer direct tools (Grep, Glob, Read) when the
target is already known. Reserve sub-agent spawns for multi-step
investigations.

### `looping`

**Signal:** same `subagent_type` + same `desc_hash` prefix + same
`file_assignment` repeated 3+ times in 30 min.

**Root cause:** CEO gave the same agent the same task 3× hoping for
a different output. Same-LLM limitation (see PROTOCOL.md §Honest
limitation): retrying the same prompt gets the same answer.

**Adopter action:** change the persona, change the skill, or re-scope
the file assignment. If none of those moves the answer, stop and
rethink the architecture (PROTOCOL.md anti-pattern #6).

### `wasteful_thinking`

**Signal:** Opus used for a spawn whose output is short (≤ 10 LoC
edit, no VETO role, no L3+ decision).

**Root cause:** `model:` frontmatter on the archetype is Opus but
the actual work is boilerplate. ADR-052 expects Haiku for those.

**Adopter action:** downshift the archetype's `model:` to Sonnet or
Haiku. Keep Opus for the canonical-5 (code-reviewer,
security-engineer, qa-architect-on-verdict, compliance, CEO on
debate consensus / verdict).

### `weak_model`

**Signal:** Haiku dispatched for a task type that ADR-052 routes to
Opus (i.e. a VETO role).

**Root cause:** someone downshifted a VETO archetype, or a spawn
prompt invoked a VETO-role-shaped task under a non-VETO persona.
Either way, the VETO floor is compromised.

**Adopter action:** revert the `model:` downshift. The VETO floor
(`code-reviewer`, `security-engineer`) is hardcoded at multiple
layers for a reason — do not downshift without Owner sign-off and
an ADR.

### `overpowered`

**Signal:** Opus/Sonnet used for a devops spawn with <30 LoC
change.

**Root cause:** devops archetype's `model:` is not set to Haiku, or
the persona's usage pattern happens to pull Sonnet. ADR-052 routes
devops to Haiku for cost.

**Adopter action:** verify `.claude/agents/devops.md` has
`model: claude-haiku-4-5-20251001`. Any spawn with an explicit
`subagent_type=devops` override should inherit.

## How to read `/audit-tokens` output

### Markdown report

Header first: total findings + summed `estimated_wasted_tokens`.
Zero findings in a 30-day window on an active repo is normal —
detectors need telemetry density (post-PLAN-020 streaming fills
`model` / `tokens_out`). A fresh adopter repo with <10 sessions
typically reports 0–2 findings.

Per-detector sections list severity tally and the top 20 findings.
Columns:

- `[severity]` — `warning` for governance/behavior signals
  (retry_churn, tool_cascade, looping, weak_model); `info` for
  pure cost-optimization (wasteful_thinking, overpowered).
- `recommendation` — human-actionable sentence.
- `evidence` preview — first four key=value pairs from the
  finding's evidence dict.

### JSONL / JSON

For pipeline integration. JSONL is one finding per line (streamable),
JSON is a single summary object with `findings` array (parseable in
one read). Both include full `evidence` and `audit_spans` references.

## The remaining 5 viral-post habits — adopter behavior

These are not framework features — nobody can hook your editing
cadence. Treat the list as a cost-awareness checklist.

| # | Habit | When it matters |
|---|---|---|
| 1 | Edit the prompt instead of a follow-up (Claude.ai UI) | N/A — Claude Code API does not have this affordance |
| 2 | Start a fresh chat every 15–20 messages | When CLAUDE.md §Current Work grows past 40 KiB, Gate-1 cache starts evicting other context; session-splits at phase boundaries retain prompt-cache |
| 3 | Batch related questions | The CEO protocol (Plan → Debate → Execute) already batches. If you're asking ad-hoc Q/A, you're paying for per-turn overhead |
| 8 | Spread work across the day | Same-session long turns blow past prompt cache TTL (5 min). Two turns 6 minutes apart re-pay Gate-1 boot (~27k tokens) |
| 9 | Work off-peak hours | Anthropic capacity pricing is flat; "off-peak" matters mostly for rate-limit headroom on Max plan (relevant for L3+ parallel dispatch) |
| 10 | Overage safety net | Sign up for the overage cap so a runaway automation can't burn a month of budget in an afternoon |

Habits 4–7 are already framework-structural — see the table at the
top of this guide.

## Opt-in: terse mode (Phase 2, SP-019)

`.claude/skills/core/terse-mode/SKILL.md` (once SP-019 promote lands
— see `PLAN-047/phase-2-sp019-deferred.md`) gives the CEO a way to
bias session output toward shorter prose during research loops. The
contract:

- **On:** `/terse on`. Fragments are OK in exploratory research,
  bullet lists, summaries, sanity checks.
- **Off:** `/terse off`. Default prose restored.
- **Auto-off for VETO roles:** `check_agent_spawn.py` injects
  `## TERSE-MODE-DISABLED` into spawn prompts for code-reviewer,
  security-engineer, qa-architect-on-verdict,
  compliance-specialist. The VETO floor is inviolate.
- **Never truncate code. Never drop numbers. Never use ellipsis
  to hide content.** The goal is prose economy, not fact economy.

Use terse-mode for: research loops, progress updates between
milestones, internal logs where the CEO is the only reader,
repetitive sanity checks.

Do NOT use terse-mode for: production deploys, customer-facing
artifacts, debate rounds, adopter documentation.

Cost delta is measurable via `.claude/scripts/ceo-cost.py --stream`
(or the `ceo-cost` streaming output if `PLAN-040` is wired in your
repo).

## A suggested adopter workflow

1. Week 1: do nothing. Let the audit-log accumulate.
2. Week 2: run `/audit-tokens window=14` and read the report.
3. If `retry_churn` > 0: sharpen the acceptance criteria in your
   plans. Re-run next week.
4. If `wasteful_thinking` > 0: downshift non-VETO archetypes to
   Sonnet/Haiku in `.claude/agents/*.md`.
5. If `overpowered` > 0: confirm your devops archetype is Haiku.
6. If `weak_model` > 0: **stop**. A VETO role was downshifted. This
   is a governance drift — revert and document the mistake.
7. After any of the above: run `/audit-tokens window=7` to confirm
   the signal dropped.

## What this guide is NOT

- NOT a replacement for the ADR-052 dispatch contract. The detectors
  observe dispatch; they do not change it. VETO floor hardcode stays
  hardcoded.
- NOT a promise of specific token savings. Savings depend on the
  adopter's dispatch discipline baseline. A clean repo already
  obeying ADR-052 will see near-zero findings.
- NOT a substitute for `OWNER-MEGA-KERNEL-BUNDLE.sh` review. Terse
  mode's VETO auto-off marker injection lives in
  `check_agent_spawn.py` and only activates when the staged Wave 8
  kernel batch has been applied.

## Cross-references

- `PLAN-047-token-economy-observability.md` — plan of record.
- `ADR-052` — multi-model dispatch by role.
- `ADR-031` — SP-NNN skill-patch lifecycle (gates terse-mode SKILL
  rollout).
- `ADR-059` — two-factor env-var bootstrap for NEW SKILL.md files.
- `.claude/scripts/detectors/` — detector source, each with tests.
- `.claude/scripts/audit-tokens.py` — aggregator CLI.
- `.claude/commands/audit-tokens.md` — slash-command wrapper.
- `.claude/commands/terse.md` — `/terse` toggle.
