---
id: PLAN-154
title: Gated Learning Loop
status: draft
created: 2026-07-03
owner: CEO
depends_on: [PLAN-153]
budget_tokens: 400-700k
budget_sessions: 2
context_risk: medium
external_wait: none
tags: [learning-loop, security, governance, ecc-analysis]
---

# PLAN-154 — Gated Learning Loop

## Context

Carved out of PLAN-153 by its round-1 debate consensus (2026-07-03): the
learning-loop wave was "3-4 plans in a trenchcoat" bundling a new data
surface, a model-in-the-loop distiller, guard-behavior changes and a
canonical-guarded `lessons.py` edit — with near-zero coupling to the rest of
the uplift program. It inherits the ecc-analysis evidence
(`PLAN-153/artifacts/`) and BOTH critics' security requirements as design
constraints, not suggestions.

**This plan is a stub awaiting its own debate.** Do not execute any item
before: (1) PLAN-153 Wave E ships (the positive-control + liveness
infrastructure this plan's hooks must pass), (2) a dedicated L3 debate runs on
this plan, (3) ADR-174 is drafted and accepted, (4) SENT-F is signed covering
`.claude/scripts/lessons.py` (canonical-guarded at `check_canonical_edit.py:129`
— NOT unguarded) plus any `.claude/hooks/**` additions.

## Goal

Import the CLASS of ecc's passive learning funnel (observe → distill →
candidate) under this framework's governance: nothing self-activates, the
human gate is explicitly NOT the injection defense (mechanical scanning is),
and no blocking guard ever loses legibility.

## Binding design constraints (from PLAN-153 round-1 debate)

1. **Metadata-only v1** (Security VETO-floor condition, resolves PLAN-153
   OQ2): the observe rail extends the content-free PLAN-125 WS-1
   `tool_lifecycle.py` rail. Redacted-payload capture is a LATER opt-in gated
   behind a documented PII/PHI redaction pass (beyond `redact.py`'s
   secret-only scope) + per-install named opt-in. Healthcare/fintech installs
   must never gain an un-de-identified content store by default.
2. **Injection-scanned pipeline**: the existing injection corpus runs over
   BOTH stored observations AND distiller output before anything becomes a
   candidate; the distiller spawn carries the ADR-175 Prompt Defense Baseline;
   audit-log content consumed by the distiller is untrusted data (it may
   contain verbatim attacker-influenced citations per ADR-175).
3. **Bounded lesson schema**: candidates are `trigger → advisory-text` from a
   constrained vocabulary — never free-form prose concatenated into
   `/ceo-boot`. Boot one-liners are fenced as untrusted data (same treatment
   as recalled memories). `/lesson-review` gains a mechanical
   imperative-detector — the human filters for usefulness, the machine for
   injection.
4. **Denial dampening is advisory-only**: condensation applies to advisory
   output exclusively. A blocking guard's block reason NEVER loses legibility
   regardless of repeat count (attacker-probing anti-pattern otherwise).
5. **Zero self-activation** (unchanged red line): PENDING → `/lesson-review`;
   instinct→skill via SP-NNN + `/skill-review` + soak. TTL 30d + 7d warning on
   pendings.
6. **E↔F interaction**: opt-in no-op hooks must carry the Wave-E
   annotation/allowlist marker so `check_harness_config.py` does not flag them;
   fixtures prove both directions.

## Items (to be refined by this plan's own debate)

1. Opt-in PostToolUse metadata rail extension (stdlib; kill-switch env).
2. Offline distiller (cheap model) proposing PENDING lesson-candidates into
   the existing `lessons.py` store (SENT-F ceremony — file is guarded).
3. Confidence score with deterministic decay in `lessons.py` (hit/miss exist).
4. Top-3 lessons as fenced one-liners in `/ceo-boot` (cap ~1k chars).
5. Advisory-output dampening with ordinal (blocking reasons untouched).
6. Fact-forcing deny-once gate ADVISORY→enforce path with fail-CLOSED
   citation verification (converges with ADR-175 semantics).
7. `/lesson-evolve`: trigger-clustering → SP-NNN candidates → `/skill-review`.

## How to continue

> After PLAN-153 Wave E ships: `/debate start PLAN-154 "<proposal>"`, draft
> ADR-174 from the consensus, get SENT-F signed, then execute. Success =
> zero writes outside pending stores without an approval event in the HMAC
> chain; kill-switch documented; liveness/positive-control fixtures green.
