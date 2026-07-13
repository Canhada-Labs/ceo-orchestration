# PLAN-157 — Wave 0 baseline snapshot

- **Date:** 2026-07-13 (S272)
- **HEAD at snapshot:** `264a8c4af060c59614c873c1e6ff9b0968d91bba` (main, Validate green após rerun de perf-flake)
- **Policy file:** `.claude/policies/grandfather-cap.policy.yaml`
- **Gate array:** `SQUAD_GRANDFATHER` em `.claude/scripts/validate-governance.sh` (cite por padrão — a linha drifta; hoje `:318`)

## Policy state (pre-drain)

| Field | Value |
|---|---|
| `domain_bundles.cap` | 32 |
| `domain_bundles.current` | 32 |
| `domain_bundles.target_cap` | 15 |
| `individual_skills.cap/current` | 5/5 |
| `_EXPECTED_DOMAIN_CAP` (test constant) | 32 |

## Roster membership (32 = 24 legacy + 8 Wave D imports)

Legacy 24: fintech, community, devrel, marketing-global, paid-media,
mobile, embedded, voice-ai, hospitality, retail, supply-chain,
training-l-and-d, civil-engineering, academic-humanities, healthcare,
hr, real-estate-finance, finance-accounting, i18n-business,
business-support, project-management, saas-platforms, identity-systems,
lgpd-heavy-saas.

Wave D imports to drain (8): agents-meta, architecture, cpp, data-ml,
desktop, dotnet, golang, jvm.

Set-equality bash-array ↔ policy-members verificada no snapshot (rider
`TestSquadGrandfatherSetEqualsPolicyMembers` adicionado neste W0).

## Imported skills inventory (13 skills nos 8 squads)

| Squad | Skills |
|---|---|
| agents-meta | dynamic-workflow-mode, loop-design-check |
| architecture | hexagonal-architecture, recsys-pipeline-architect |
| cpp | cpp-coding-standards, cpp-testing |
| data-ml | prisma-patterns, pytorch-patterns |
| desktop | windows-desktop-e2e |
| dotnet | csharp-testing |
| golang | golang-patterns |
| jvm | java-coding-standards, springboot-patterns |

## Catalog counts at baseline (derived-surface reconcile targets)

- Total skills: **166** (42 core + 8 frontend + 116 domain) — claims em
  `CLAUDE.md`, `INSTALL.md`, `README.md`, `docs/COMMAND-SKILL-HOOK-MAP.md`,
  inventário embutido em `ceo-orchestration/SKILL.md`, profiles.
- OQ ratifications (S270): OQ1 reach-criterion, OQ2 git-history-only
  deletion + pointer, OQ3 `cap := current` a cada wave boundary, OQ4
  fold-soak WAIVED, OQ5 prisma→saas-platforms via SP + data-ml ML-only.
