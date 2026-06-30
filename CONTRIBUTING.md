# Contributing to ceo-orchestration

> **English is canonical.** PT-BR mirror: [CONTRIBUTING.pt-BR.md](CONTRIBUTING.pt-BR.md).
> EN is the Single Source of Truth. See `docs/translations/README.md` for
> the drift tracker; `.github/workflows/translations-drift.yml` enforces
> structural parity.

Thanks for considering a contribution. This framework is correctness-first
and opinionated — we optimize for mechanical governance, not breadth. Read
this file before opening a PR so your contribution lands on the first try.

## Adoption ladder

| Level | Trigger artifact | What it means |
|---|---|---|
| **Evaluator** | read README + PROTOCOL | You know what the framework is |
| **Adopter** | ran `install.sh`; has `.claude/` in a target repo | You're using it |
| **Contributor** | merged PR with ADR if L3+ | You extended the framework |
| **Committer** | CODEOWNERS entry; sponsors a squad | You maintain part of it |

No paid tier exists. None is planned until 50+ organic adoptions
(competitive analysis recommendation).

## Before you open a PR

1. **Read `PROTOCOL.md`** — the governance contract you're working under.
2. **Read `.claude/plans/PLAN-SCHEMA.md`** — if your work spans multiple
   sessions, it needs a plan file.
3. **Read `SPEC/v1/README.md`** — if your change touches any schema, it's
   a SPEC-level change. SemVer rules apply.
4. **Check `.claude/plans/` for active plans** — if there's a current
   sprint, your work probably belongs in that plan or needs a follow-up.

## Types of contributions

### Tier A — Trivial (no gate)

- Typo fixes
- Doc clarifications
- Log message tweaks
- CI config fixes that don't change behavior

Open a PR; one approving review; merge.

### Tier B — Additive (ADR not required)

- New test
- New skill under an existing domain
- New archetype in `team.md`
- New task chain entry
- New field in a SKILL.md frontmatter (optional, additive)

PR requirements:
- Passes `validate-governance.sh`
- Passes `python3 .claude/scripts/registry.py --validate`
- Passes full test suite (hooks + scripts)
- Describes the change + rationale in the PR body

### Tier C — L3+ (ADR required, debate recommended)

- New hook
- Schema change (even additive) — requires ADR documenting the addition
- New event type in audit-log v2 — requires ADR extending ADR-005
- New squad — requires ADR-009-style squad documentation
- Changes to `PROTOCOL.md`
- Changes to `install.sh` flags or exit codes
- Changes to `upgrade.sh --pin` contract
- Breaking changes of any kind (MAJOR bump of SPEC)

PR requirements:
- ADR at `.claude/adr/ADR-NNN-<slug>.md` (follow existing ADR format)
- If L3+ plan scope: `/debate start PLAN-NNN` on-disk debate round 1
- CHANGELOG entry under `## [Unreleased]`
- All Tier B requirements

## Code standards

- **Python ≥ 3.9** — no `match` statements, no PEP-604 union syntax at
  runtime (use `Optional[X]` / `Union[X, Y]` from `typing`)
- **Stdlib only** in hooks, scripts, and `_lib/` — zero `pip install`
  runtime deps. Dev-only deps (e.g. `coverage.py` in coverage.yml) OK.
- **`from __future__ import annotations`** in every module
- **Type hints on public functions**
- **Unit tests** via `unittest` (stdlib). `TestEnvContext` for env
  isolation; never touch real `$HOME` or `$CLAUDE_PROJECT_DIR` in tests
- **Fail-open on infra bugs** — hooks NEVER block the user session on
  their own failure; log a breadcrumb and allow

## Commit message style

```
<scope>: <imperative short line (≤ 70 chars)>

Why this change exists (paragraph, not every file touched).

What shipped:
- bullet
- bullet

Tests: counts if relevant. Zero regressions claimed = true.

Related: PLAN-NNN §X, ADR-NNN, consensus finding §CN.

Co-Authored-By: Claude <model-id> <noreply@anthropic.com>
```

Scope examples: `PLAN-004 Phase 2`, `hook`, `SPEC/v1`, `docs`, `ci`.

## Testing

```bash
# Full hook test suite
python3 -m unittest discover -s .claude/hooks/tests -v

# Full script test suite
python3 -m unittest discover -s .claude/scripts/tests -v

# Governance + tier-boundary + registry check
bash .claude/scripts/validate-governance.sh
python3 .claude/scripts/registry.py --validate
python3 .claude/scripts/check-staleness.py

# Smoke install into a scratch dir
bash scripts/tests/smoke-install.sh
```

## What NOT to contribute

- **Real-person persona names.** Fictional composites only (brand
  appropriation + legal risk).
- **JS runtime in hooks.** Stdlib Python is non-negotiable.
- **SaaS integrations in CI** (Codecov, CodeRabbit). Supply-chain model
  requires zero third-party trust.
- **Pro/paid tier content.** Deferred until 50+ organic adoptions.
- **Skills that duplicate existing ones.** Check the registry first:
  `python3 .claude/scripts/registry.py --list-skills`.
- **Dashboard-as-gate behavior.** Observability is read-only.

## Translations

PT-BR is a tracked mirror, not a second canonical. See
`docs/translations/README.md` for the workflow. If you're adding a new
translation (ES, ZH, etc.), open an issue first — we defer new languages
until 50+ stars (positioning decision).

## Questions

Open an issue. Be specific. Include:
- What you tried
- What happened
- What you expected

Issues with repro steps + relevant files get triaged faster.
