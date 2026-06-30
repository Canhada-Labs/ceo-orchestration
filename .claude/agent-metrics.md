# Agent Performance Metrics

> Updated by CEO after each session. Tracks agent effectiveness over time.
> Purpose: identify which agents/skills need improvement, NOT punishment.

## Schema constraints (PLAN-025 Batch J F-chaos-P2)

The tables below follow a declared schema so `validate-governance.sh` can
lint the file and surface drift. Required columns per team section:

- `Agent` — archetype or concrete persona name; NON-EMPTY string
- `Tasks` — non-negative integer
- `Revisions` — non-negative integer
- `Strikes` — one of `0/3`, `1/3`, `2/3`, `3/3`
- `Efficiency` — percentage string `NN%` OR em-dash `—` (never-active)
- `Last Active` — ISO-8601 date (`YYYY-MM-DD`) OR em-dash `—`
- `Notes` — free-form string

### 3-strike lifecycle (enforced)

| Strikes | State | Next action |
|---------|-------|-------------|
| `0/3` | healthy | continue normal dispatch |
| `1/3` | warning | CEO prepends "ATTENTION: <prior_error>" to next spawn |
| `2/3` | supervised | another agent reviews every output BEFORE CEO accepts |
| `3/3` | TERMINATED | rename persona + reset score + write Session Log entry |

### Revisions accounting

A "revision" counts when the CEO explicitly asks the agent to redo work
because of factual error, skill violation, incomplete output, or
regression (per PROTOCOL.md §3-Strike Policy). It does NOT count:

- Owner preferred a different approach (taste, not error)
- CEO prompt was incomplete (CEO failed, not agent)

## Metrics Legend

- **Tasks**: Number of tasks completed
- **Revisions**: Times output needed revision (rework) — per schema above
- **Strikes**: From 3-strike policy (see team.md); values `0/3` to `3/3`
- **Efficiency**: Tasks / (Tasks + Revisions) as percentage

## How to use this file

After you define your concrete team in `.claude/team.md`, replace the
placeholder rows below with one row per named agent. Track metrics per session.
When an agent reaches 3 strikes, rewrite the persona with a new name and
reset their score.

For a fully populated example, see `.claude/skills/domains/fintech/team-personas.md`
which instantiates 18 backend + 11 frontend personas.

## Backend Team

| Agent | Tasks | Revisions | Strikes | Efficiency | Last Active | Notes |
|-------|-------|-----------|---------|------------|-------------|-------|
| {{VP_Engineering}} | 0 | 0 | 0/3 | — | — | |
| {{VP_Product}} | 0 | 0 | 0/3 | — | — | |
| {{VP_Operations}} | 0 | 0 | 0/3 | — | — | |
| {{Principal_Perf_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Staff_Backend_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Real_Time_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Data_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{QA_Architect}} | 0 | 0 | 0/3 | — | — | |
| {{Growth_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Billing_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Compliance_Specialist}} | 0 | 0 | 0/3 | — | — | |
| {{Chaos_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Security_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{DevOps_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Staff_Code_Reviewer}} (VETO) | 0 | 0 | 0/3 | — | — | merge VETO holder |
| {{Staff_Domain_Expert}} (VETO) | 0 | 0 | 0/3 | — | — | domain VETO holder |

## Frontend Team

| Agent | Tasks | Revisions | Strikes | Efficiency | Last Active | Notes |
|-------|-------|-----------|---------|------------|-------------|-------|
| {{UI_UX_Lead}} | 0 | 0 | 0/3 | — | — | |
| {{Component_Architect}} | 0 | 0 | 0/3 | — | — | |
| {{Frontend_Perf_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Accessibility_Lead}} | 0 | 0 | 0/3 | — | — | |
| {{UX_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Data_Layer_Lead}} | 0 | 0 | 0/3 | — | — | |
| {{Real_Time_Data_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Frontend_Security_Engineer}} | 0 | 0 | 0/3 | — | — | |
| {{Frontend_QA_Architect}} | 0 | 0 | 0/3 | — | — | |
| {{Quality_Lead}} (VETO) | 0 | 0 | 0/3 | — | — | merge VETO holder |
| {{TypeScript_Quality_Lead}} | 0 | 0 | 0/3 | — | — | |

## Skill Effectiveness

| Skill | Times Used | Avg Quality | Common Issues |
|-------|-----------|-------------|---------------|
| (populated after first usage) | | | |

## Session Log

| Session | Agents Used | Tasks Done | Revisions | Notes |
|---------|------------|-----------|-----------|-------|
| (populated after each session) | | | | |
