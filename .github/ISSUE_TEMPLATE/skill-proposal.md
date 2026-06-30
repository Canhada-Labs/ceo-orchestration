---
name: Skill proposal
about: Propose a new core / frontend / domain skill
title: "[skill] "
labels: ["skill-proposal", "needs-triage"]
assignees: []
---

## Skill name (kebab-case)

e.g., `distributed-tracing`, `kafka-streams`, `grpc-service-design`.

## Tier

- [ ] Core (universal — any backend project)
- [ ] Frontend (universal — any frontend project)
- [ ] Domain (specific to a vertical — name the domain, e.g. fintech, edtech)

## Frontmatter draft

```yaml
---
name: <skill-name>
description: <one-sentence — what this skill teaches>
trigger: <when does the CEO load this skill?>
---
```

## Problem this solves

What decision-making gap exists today? Point to real PRs or incidents
where NOT having this skill caused a problem. No hypothetical scenarios.

## Who owns it

Which archetype in `.claude/team.md` (or frontend-team.md) would load this
skill? If no archetype fits, propose a new archetype too.

## Content sketch

What the SKILL.md will cover (2-5 bullets):
- ...
- ...
- ...

## Pitfalls

List 3-5 universal pitfalls this skill MUST catch — these become entries
in `.claude/pitfalls-catalog.yaml` or a domain `pitfalls.yaml`.

1. ...
2. ...
3. ...

## Benchmark plan

Every new skill ships with a benchmark YAML in `.claude/skills/<tier>/<name>/benchmarks/`.
Sketch the positive cases + control cases:

- Positive (at least 10):
- Control (should NOT trigger the skill, at least 4):

## Scope discipline

- [ ] This skill is NOT covered by an existing skill (check `.claude/skills/core/` inventory)
- [ ] Adding this does NOT increase skill count beyond 48 (or provides concrete replacement path)
- [ ] Follows SKILL.md template + benchmark pattern of existing skills
- [ ] Has no runtime dependencies (stdlib only per ADR-002)

## Cross-reference

- Existing skills nearby: ...
- Existing squads that would use this: ...
- Related pitfalls: ...
