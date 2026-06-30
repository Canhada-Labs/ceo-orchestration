---
id: ADR-069
title: wondelai/skills import — refused (formal closure of Session 55 audit verdict)
status: ACCEPTED
created: 2026-04-22
accepted_at: 2026-04-22
accepted_via: Round-19 sentinel (84a4977 promote) + PLAN-058 Round-23 frontmatter flip (F-CR-02 residual closure)
proposed_by: CEO (PLAN-051 Phase 2 C1 Opção A, Session 57)
proposed_owner_response: Owner (direct confirmation 2026-04-22, SIM-SKIP response to PLAN-051 open-question #10)
related_plans: [PLAN-051]
related_adrs: [ADR-060, ADR-033]
related_memory: [project_wondelai_skills_audit.md]
blast_radius: L1-contained
supersedes: none
superseded_by: none
decision_category: refused
refused_reason: cost-exceeds-benefit
enforcement_commit: 84a4977
---

> **Status:** ACCEPTED. (Originally DRAFT-STAGED in a non-canonical
> plans/ path pending the round-18 canonical sentinel scoping
> `.claude/adr/ADR-069-wondelai-skills-import-refused.md`; that sentinel
> was signed and the file promoted to canonical `.claude/adr/` — see
> frontmatter `accepted_via`. Owner-confirmed content via direct response
> to PLAN-051 open-question #10 on 2026-04-22. Frontmatter `status:` is
> the source of truth — PLAN-113 W2 reconciled this body marker to match.)

# ADR-069 — wondelai/skills import refused

## Context

On 2026-04-22 (Session 55), Owner directed "analise esse repo com cuidado"
about `https://github.com/wondelai/skills` (42 book-based skills, MIT
license, Wondel.ai sp. z o.o., 696 stars at audit time). The CEO
executed a security + utility audit isolated in `/tmp/wondelai-audit/`
(`git clone --depth 1`, no execution, read-only markdown analysis).

### Security verdict (Session 55) — PASS

Zero threats identified across the 42 skill markdown files:
- No prompt injection patterns (sigil_system, jailbreak_persona, etc.)
- No `exec` or arbitrary code execution in `.md` content
- No unicode evasion (zero-width U+200B-200D, U+FEFF, tag chars
  U+E0000-E007F, homoglyphs)
- Sole executable `sync-ide-skills.sh` creates symlinks within its own
  clone — inert
- Amazon affiliate tag `?tag=wondelai00-20` is declared monetization,
  not a security issue

### Utility verdict (Session 55) — SKIP

Content inventory:
- **~90% business/product/marketing/design skills** — Jobs-To-Be-Done,
  CRO, StoryBrand, Cialdini Influence, Blue Ocean, Lean Startup,
  Refactoring UI, iOS HIG, etc. **Out of scope** for ceo-orchestration
  meta-engineering framework.
- **~10% technical skills** — clean-code, refactoring-patterns,
  domain-driven-design, designing-data-intensive-applications,
  system-design, clean-architecture, release-it, high-performance-
  browser-networking. **70-90% overlap** with existing canonical skills
  (`code-review-checklist`, `incremental-refactoring`,
  `architecture-decisions`, `chaos-and-resilience`,
  `data-schema-design`, `performance-engineering`).
- **Zero new mechanisms** (no hooks, validators, SPEC schemas, or
  contracts).

## Decision

**Refuse import.** The ceo-orchestration framework does NOT absorb
wondelai/skills into core, frontend, or community domains.

## Decision drivers (why refused)

1. **Scope mismatch (90% of content).** Framework is meta-engineering
   governance kernel; business/product skills expand surface without
   serving the Plan→Debate→Execute thesis.
2. **Content duplication (10% of content).** Technical overlap 70-90%
   with existing canonical skills creates competing sources of truth.
3. **No new mechanism.** Imported skills add markdown only; no hooks,
   validators, SPEC, enforcement.
4. **Adopter path already exists.** `npx skills add wondelai/skills/
   <slug>` lets adopter install paralleled if desired.
5. **Session 55 verdict already concluded.** This ADR formalizes that
   outcome, not a new decision. Honors PLAN-051 §3 anti-goal.

## Refused-reason taxonomy (PLAN-051 §3.1)

**Reason (b): cost-exceeds-benefit** — importing 42 skills (or even
the 3 T2/T3 watch candidates: jobs-to-be-done, domain-driven-design,
mom-test) triggers mandatory Debate Round 2 per ADR-060, costs ~2
dev-days per skill including SP-NNN sign, and produces value ≤
adopter-parallel-install alternative.

## Options considered

### Option A (ACCEPTED — this ADR) — SKIP formal

- ✅ Zero import cost
- ✅ Session 55 verdict honored
- ✅ Adopter path preserved via `npx skills add`
- ✅ Complies with PLAN-051 §3 anti-goals
- ✅ Owner-confirmed 2026-04-22

### Option B (REJECTED) — Import 3 T2/T3 watch skills

- ❌ Triggers mandatory Debate Round 2 per ADR-060
- ❌ ~2 dev-days × 3 skills = ~6 dev-days
- ❌ Expands scope mid-closure, violates PLAN-051 §3 anti-goal
- ❌ 70-90% overlap with existing canonicals creates routing ambiguity

## Consequences

### Positive
- Session 55 verdict formally closed; no implicit "TBD" pending.
- Adopter has clear path via `npx skills add`.
- T2/T3 WATCH items (jobs-to-be-done, DDD, mom-test) remain candidates
  for **reactive import** if adopter demand materializes post-v1.9.0.

### Negative / Accepted trade-offs
- CEO workflow gains no direct benefit from wondelai technical skills;
  overlap with existing canonicals assumed sufficient.
- If adopter requests specific wondelai skill AND overlap is <70% in
  practice, follow-up ADR overrides this one (reactive path).

## Blast radius

**L1-contained.** Touches:
- One new ADR file: `.claude/adr/ADR-069-wondelai-skills-import-refused.md`
- No code/schema/test/install.sh changes

## Dual co-sign (PLAN-051 §3.1 requirement)

- **VP Engineering** (architecture-decisions): ✅ co-signed during
  PLAN-051 Round 1 debate consensus — scope mismatch + content
  duplication + no new mechanism = architecturally consistent refusal
  per skill §When to Refactor vs Rewrite rubric.
- **Principal Security** (security-and-auth): ✅ co-signed during
  PLAN-051 Round 1 debate consensus — Session 55 audit confirmed zero
  threats; refusing import does not expose security regression
  (never-imported skills cannot vulnerability-leak); adopter-parallel-
  install path is adopter-owned threat surface.

## Lifecycle

This refused ADR is **durable** — no periodic review scheduled.
Supersession requires:

- Concrete adopter request for specific wondelai skill, with evidence
  that canonical alternatives are insufficient; OR
- Discovery of new technical skill in wondelai/skills that has zero
  overlap with canonicals AND introduces a new mechanism.

Either trigger produces new ADR (ADR-NNN) citing this one as
`supersedes: ADR-069`.

## References

- Memory: `~/.claude/projects/-Users-devuser-ceo-orchestration/memory/project_wondelai_skills_audit.md`
- CLAUDE.md §CHANGELOG 2026-04-22 Session 55 (audit entry)
- ADR-060 (curated skill import pipeline — the alternative path)
- ADR-033 (SP-NNN sign discipline)
- PLAN-026 finding #11 (precedent: `awesome-claude-plugins` SKIP)
- SPRINT-30-ROADMAP D-2 (precedent: `awesome-design-systems` SKIP)
- PLAN-051 §Phase 2 C1 (this sprint's closure of open-question #10)

## Enforcement commit

**Enforcement commit:** to be populated post-round-18-promote with the
canonical promote commit SHA. Pre-promote, enforcement is the absence
of `.claude/skills/domains/community/skills/{jobs-to-be-done,
domain-driven-design,mom-test}/` directories — i.e., the absence of
those skills on disk IS the enforcement.

Promotion chain (when round-18 lands):
- Round-18 sentinel: `<TBD-commit>` (GPG detach-sign Owner approved.md
  scoping ADR-069 + ADRs 070-073)
- Canonical promote: `<TBD-commit>` (`git mv` adr-drafts/ADR-069 →
  .claude/adr/ADR-069)

Future re-import requires: new ADR citing `supersedes: ADR-069` +
adopter-demand evidence OR new-mechanism justification + re-triggered
Debate Round 2 per ADR-060.
