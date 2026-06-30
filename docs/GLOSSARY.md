# GLOSSARY — ceo-orchestration term dictionary

> **PT-BR:** [GLOSSARY.pt-BR.md](GLOSSARY.pt-BR.md) (mirror).

> This EN glossary uses the canonical EN term as entry; the PT-BR
> version may introduce translated terms with the EN term in parens.

Terms that appear in `CLAUDE.md`, `PROTOCOL.md`, logs, plans, etc.

## Core concepts

**CEO** — The role Claude takes on when the framework is active.
Not a separate agent; it is the **main Claude** orchestrating a
team. Think "conductor" more than "executor".

**Owner** — You. The human making the final call. The CEO reports
to the Owner. The Owner can fire the CEO (rewrite the persona if it
fails 3 times).

**Agent / Subagent** — A Claude spawned by the CEO with a specific
persona + skill. Runs in parallel or sequentially. Returns with
output.

**Persona** — Profile of an agent (name, background, mantra, red
flags, anti-patterns). Lives in `.claude/team.md` or
`<domain>/team-personas.md`.

**Skill** — Technical manual. Checklist, not "vibe". Lives in
`.claude/skills/<tier>/<name>/SKILL.md`. Each agent has 1-2 skills.

**Archetype** — Generic role (e.g. "VP Engineering", "Staff
Security"). Concrete personas instantiate archetypes.

**Squad** — Cohesive set of personas + skills + pitfalls + task
chains for a specific domain (fintech, lgpd-heavy-saas,
trading-hft).

## Governance

**PROTOCOL** — The governance contract. Lives in `PROTOCOL.md`.
Defines gates (GATE 1 read, GATE 2 activate, GATE 3 plan), vetoes,
3-strike.

**Gate (1, 2, 3)** — Mandatory steps at the start of every session.
Gate 1 = read docs. Gate 2 = invoke the ceo-orchestration skill +
read team. Gate 3 = plan before coding.

**Plan** — File `.claude/plans/PLAN-NNN-slug.md` with frontmatter
(id, title, status, owner). Plans survive across sessions.

**Lifecycle** — Plan states: `draft → reviewed → executing →
done` (or `abandoned`). Transitions are hook-governed.

**ADR** — Architecture Decision Record. File `.claude/adr/ADR-NNN`
that records irreversible architectural decisions. Has Status,
Context, Options, Decision, Consequences, Blast Radius.

**Blast radius** — Scope of impact of a change. L1 = 1 file,
L5 = dozens of modules.

## Debate

**/debate** — Slash command to run a multi-specialist debate on a
plan. Entry forms: `start`, `round2`, `round3`, `status`.

**Round** — Debate iteration. Each round spawns 3 agents (team
archetypes), each critiquing the plan from the angle of their
skill.

**Consensus finding** — Risk flagged by 2+ agents. If consensus, the
CEO **must** adjust the plan (non-negotiable).

**Round verdict** — At the end of the round: `PROCEED` (continue),
`RUN-ANOTHER-ROUND` (one more round), `ESCALATE` (can't resolve
alone, calls the Owner).

## Vetoes and approvals

**VETO** — Hard block. If a veto holder says "no", it doesn't
ship. Universal vetoers: Staff Code Reviewer (any merge), Staff
Security Engineer (auth/input/token).

**3-strike policy** — An agent with 3 consecutive factual errors is
"fired" — persona rewritten with a new name. Strikes tracked in
`.claude/agent-metrics.md`.

## Hooks (mechanics)

**Hook** — Python script in `.claude/hooks/` that runs at specific
points in the session (PreToolUse, PostToolUse). Blocks
anti-pattern actions.

**PreToolUse** — Hook that runs BEFORE the tool executes. Can
block (`{"decision":"block"}`).

**PostToolUse** — Hook that runs AFTER. Usually a silent observer
(e.g. `audit_log` recording what happened).

**Fail-open** — Rule: a hook never blocks the user because of its
own bug. Parse error, timeout, missing file → emits `allow`.
Safety comes from guaranteeing the hook is NEVER on the critical
path.

**Adapter Layer** — Translation layer between the IDE-specific shape
(Claude Code, Gemini CLI) and the internal NormalizedEvent. V1.0 is
100% Claude. Gemini is a stub.

## Memory and audit

**Auto-memory** — Files in `~/.claude/projects/<slug>/memory/` that
Claude auto-loads every session. 4 types: user, feedback, project,
reference.

**Audit log** — JSONL at `~/.claude/projects/<slug>/audit-log.jsonl`.
Append-only. Secrets redacted. Queried via `audit-query.py`.

**Event schema v2** — Current audit-log format. Actions: agent_spawn,
debate_event, plan_transition, veto_triggered, benchmark_run,
lesson_write, injection_flag, lesson_outcome.

**Redaction** — Process that strips secrets/PII from text before
logging. Implemented in `_lib/redact.py`.

## Reflexion

**Reflexion** — System that learns from benchmark failures. Writes
lessons on failure. Lessons injected into future prompts.

**Lesson** — JSON file in `lessons/<id>.json` with
`remember_this`, `scope_tags`, `archetype`, `hit_count`, `miss_count`.

**Hit / Miss** — Outcome of an applied lesson. Hit = scenario
passed. Miss = failed. Recorded by `record_outcome()`.

**Top-K** — Cap on how many lessons are considered per spawn (K=50
hard ceiling in V1.0).

**Pruning** — Removal of lessons with `hit_rate < 0.3` after
`n >= 5`. V1.0 is dry-run only; enforcement in Sprint 7+ after FPR
is measured.

## CI/CD and release

**Governance check** — Workflow `.github/workflows/validate.yml`.
Checks skills, team, plans, CODEOWNERS structure.

**Coverage gate** — Workflow `.github/workflows/coverage.yml`. V1.0
enforces at 86% (`--fail-under=86`).

**Smoke install** — Workflow `smoke-install.yml`. Simulates install
on a clean repo.

**Release gate** — Workflow `release.yml`. Fires on tag push. 7 gates
including smoke install, SPEC version match, CHANGELOG.

**SemVer** — Major.Minor.Patch. V1.0.0-rc.1 = release candidate 1.

## Roles (main archetypes)

**VP Engineering** — Architecture, ADRs, review of changes touching
3+ modules.

**VP Product** — Features, conversion, revenue.

**VP Operations** — Deploys, monitoring, SRE.

**Staff Code Reviewer** — Merge VETO.

**Staff Security Engineer** — VETO on auth/token/input. (There's
also Staff Quant in fintech, Staff Privacy in healthcare, etc.)

**Principal Performance Engineer** — Latency, memory, GC.

**Principal Data Engineer** — Schema, migrations, RLS.

**Principal QA Architect** — Tests, regression, edge cases.

**Chaos & Resilience Engineer** — Circuit breakers, failure modes.

**Growth Engineer** — Funnel, onboarding.

## Quick acronyms

- **L1-L5** — blast radius levels
- **ADR** — Architecture Decision Record
- **RLS** — Row-Level Security (postgres)
- **RC** — Release Candidate
- **FPR** — False Positive Rate
- **PR** — Pull Request
- **SHA** — git commit hash (7-char prefix = enough)
- **IPC** — Inter-Process Communication
- **WCAG** — Web Content Accessibility Guidelines
