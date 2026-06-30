---
id: ADR-140
title: Receiving-review anti-sycophancy doctrine — superpowers BORROW-3
status: ACCEPTED
date: 2026-05-27
related: [ADR-058, ADR-051, ADR-032]
accepted_at: 2026-05-28
accepting_session: S177
authorization: PLAN-117 WS-B sentinel `.claude/plans/PLAN-117/architect/round-4/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-140: Receiving-review anti-sycophancy doctrine — superpowers BORROW-3

**Status:** ACCEPTED (S177, 2026-05-28)
**Date:** 2026-05-27
**Enforcement commit:** `a2986b8` (PLAN-115 Batch-1 — receiving-review skill + PROTOCOL §Receiving review, S170)
(`.github/workflows/benchmarks.yml` ceiling raise + `receiving-review` skill +
its advisory benchmark + the `PROTOCOL.md` §Receiving review clause). No
blocking hook: the doctrine is checklist-enforced (skill-loaded + PROTOCOL
clause + advisory benchmark), the same enforcement model as the same-LLM
mitigations in PROTOCOL.md §Honest limitation._
**Decision drivers:** missing receiving-side review discipline; observed
sycophancy/performative-agreement failure mode; the dormant benchmark ceiling
breach that the new benchmark would activate.

## Context

The framework has a mature **giving** side of code review — the
`code-review-checklist` skill, the `code-reviewer` archetype, the `/debate`
protocol, and ADR-058 (brainstorm gate + two-pass adversarial review). It has
**no** doctrine for the **receiving** side: how the CEO or any agent should
respond when it receives review/feedback from the Owner, the Codex pair-rail,
a debate archetype, or an external reviewer.

The gap matters because the dominant failure mode of an LLM recipient is
**sycophancy** — performative agreement ("You're absolutely right!") followed
by an unverified change. This is the same-LLM fluency trap (PROTOCOL.md
§Honest limitation) seen from the receiving end: a confident reviewer comment
primes auto-acceptance, and the recipient "fixes" code that was already
correct, or implements a scope expansion it never needed.

The S166 re-audit of `github.com/obra/superpowers` @ v5.1.0 (memory
`reference-superpowers-reaudit-v510`, Codex-validated thread `019e63a2`) ranked
`receiving-code-review` the **strongest** net-new borrow: "verify before
implementing, no performative agreement, technical rigor over social comfort."

## Decision drivers

- We hold the giving side but not the receiving side of review discipline.
- Sycophancy is a measured, named failure mode (Artifact Paradox, PROTOCOL.md).
- Codex pair-rail feedback in particular must be *verified*, not obeyed — a
  Codex finding is a claim, not an order ([[feedback-codex-validates-reality-debate-validates-design]]).
- Adding any benchmark file touches the dormant `CEO_BENCHMARK_MAX_SCENARIOS`
  ceiling, which must be reconciled in the same change.

## Options considered

### Option A: Standalone `receiving-review` core skill + PROTOCOL clause (CHOSEN)

A new core skill `.claude/skills/core/receiving-review/SKILL.md` plus a short
governance clause in `PROTOCOL.md`. Cross-linked to ADR-058 (giving side).

- **Pros:** reception is a distinct discipline; clean CSO description; does not
  entangle the new doctrine with `code-review-checklist`'s live ADR-031
  shadow-mode patch lifecycle; benchmarkable independently.
- **Cons:** a new skill bumps the core/total counts (count-bump ceremony).

### Option B: Fold into `code-review-checklist`

- **Pros:** no count bump.
- **Cons:** reception ≠ authoring; folding dilutes the Staff Code Reviewer
  CSO description and entangles a new discipline with an active patch
  lifecycle. **Rejected** (Wave A debate Q1, 6/6).

### Option C: Reject `review-reception` as the name

- **Cons:** less discoverable; non-idiomatic. **Rejected** in favor of
  `receiving-review`.

## Decision

Adopt the **receiving-review anti-sycophancy doctrine** as a standalone core
skill plus a `PROTOCOL.md` §Receiving review clause, attributed to
`obra/superpowers` (MIT, v5.1.0, HEAD `f2cbfbe`) as **BORROW-3** (BORROW-1 =
brainstorming, BORROW-2 = two-pass adversarial review, both ADR-058). The
doctrine: read fully → restate → **verify against codebase reality** →
evaluate for THIS codebase → respond with acknowledgment or **reasoned
pushback** → implement per item (never deadlock N clear CRITICALs behind one
unclear NIT). It forbids performative agreement, applies a YAGNI check to "do
it properly" suggestions, and carries a **security carve-out**: any feedback
that would weaken a security control re-enters the VETO gate regardless of who
suggested it (Owner / Codex / archetype).

### Benchmark-ceiling bump (WS-A0)

`benchmarks.yml` enforces an aggregate scenario ceiling
`CEO_BENCHMARK_MAX_SCENARIOS` (exit 1 on breach; the workflow's own error
message mandates an accompanying ADR for any raise). The current aggregate is
**78** scenarios across 6 benchmark files — **already over the 60 ceiling**
(the breach is dormant only because `benchmarks.yml` is paths-filtered and
advisory). Adding the `receiving-review` benchmark (8 scenarios) plus the WS-B
planted-bug scenarios (+4 to `code-review-checklist.yaml`) brings the aggregate
to **~90**. This ADR authorizes raising `CEO_BENCHMARK_MAX_SCENARIOS` from
`60` to **`100`** — enough headroom for the PLAN-115 borrows plus the next
benchmark without re-amending. The per-file `DEFAULT_MAX_SCENARIOS=50` is
unchanged and remains adequate.

## Consequences

- **(+)** Closes the receiving-side review gap; gives an explicit, benchmarked
  anti-sycophancy discipline applicable to Owner / Codex / archetype feedback.
- **(+)** Reconciles a latent dormant ceiling breach (78 > 60) instead of
  leaving it to surface later.
- **(−)** Count-bump ceremony: core 41 → 42, total 150 → 151, across
  `CLAUDE.md` / `README.md` / `INSTALL.md` / `npm/` / `verify-counts.sh` +
  skill-inventory regen.
- **(~)** The doctrine is checklist-enforced, not hook-enforced. Like the
  same-LLM mitigations, it relies on the skill being loaded and the PROTOCOL
  clause being honored; the benchmark is advisory (no new required CI gate per
  Wave A Q3).

## Blast radius

**L3+** — touches a new skill, a governance contract (`PROTOCOL.md`), a CI
workflow (`benchmarks.yml`), and the framework count surface
(`CLAUDE.md`/`README.md`/`INSTALL.md`/`npm`/`verify-counts.sh`/skill inventory).

## Attribution

Pattern borrowed from `obra/superpowers`
(`skills/receiving-code-review/SKILL.md`), MIT licensed, release v5.1.0, HEAD
`f2cbfbe` (2026-05-04). Re-expressed in this framework's idiom (named skill,
CSO description, PROTOCOL clause, advisory benchmark) — not copied prose.
Audit record + Codex cross-validation: memory
`reference-superpowers-reaudit-v510` (thread `019e63a2`). Precedent: ADR-058
(superpowers BORROW-1/2).
