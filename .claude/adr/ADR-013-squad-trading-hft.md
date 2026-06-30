# ADR-013: Squad — trading-hft

**Status:** ACCEPTED
**Date:** 2026-04-13
**Sprint:** 5 Phase 6
**Squad contract:** ADR-009
**Foundational profile:** core,fintech (recommended)

## Context

PLAN-005 Phase 6 (B.6) asked for the second post-LGPD squad under the
ADR-009 contract. Trading-HFT was selected because:

- It exercises the squad contract (5 personas, 3 skills, 10+
  pitfalls, 2 task chains, 1 example plan).
- It demonstrates a critical-path domain with three independent
  VETO holders (Latency, Kill-Switch, Compliance) — a stress test of
  the multi-VETO governance model.
- It complements the existing fintech squad (which covers spot/perp
  exchange integration) without overlap.

## Decision drivers

- **VETO independence.** The three VETOs (latency / kill / compliance)
  must NOT live in the same persona. An incident where the same
  person owns both latency budgets and kill switches has historically
  produced "kill is fast enough because I optimized it" — which is
  exactly the unverified claim ADR-009 §VETO red lines forbid.
- **Latency budget discipline.** HFT systems live and die by p99/p99.9
  latency. The squad's `latency-budgets` skill enforces measurement-
  first review on every hot-path PR.
- **Kill switch independence.** Real kill switches don't share infra
  with order paths. The squad's `kill-switches` skill encodes that
  rule.
- **Compliance reality.** Surveillance retroactively flags patterns
  the strategy author didn't anticipate. The squad bakes red-team
  review into every strategy launch (`hft-launch-new-strategy` task
  chain step 2).

## Decision

Ship the trading-hft squad with:

| Artifact | Count | File |
|---|---|---|
| Personas | 5 | `team-personas.md` |
| Skills | 3 | `skills/{order-routing,latency-budgets,kill-switches}/SKILL.md` |
| Pitfalls | 18 | `pitfalls.yaml` |
| Task chains | 2 | `task-chains.yaml` |
| Example plan | 1 | `examples/PLAN-EXAMPLE.md` |

### VETO holders

| Persona | VETO scope | Block triggers |
|---|---|---|
| Marcelo Andrade (Latency Architect) | Hot-path latency budgets | Heap allocations; syscalls; contended locks; missing histogram |
| Yara Bensoussan (Kill-Switch Operator) | Cancel-all / flatten / circuit-breaker paths | Shared infra with orders; non-batched cancel; flag-gated kill |
| Eluned Pryce (Compliance Officer) | Audit trail + surveillance | Missing audit fields; broken PTP; new strategy without red-team |

The Head of Trading Systems (Diane Okafor) is NOT a VETO holder by
design — she escalates VETO conflicts to CEO. This avoids the "the
same person who runs the trading floor also approves the changes
that affect it" anti-pattern.

### Foundational profile

`install.sh --profile core,fintech,trading-hft` is the recommended
install. The squad assumes:

- Universal `state-machines-and-invariants` (order state machine)
- Universal `chaos-and-resilience` (drill methodology)
- Universal `performance-engineering` (general perf tuning)
- Fintech `financial-correctness-and-math` (decimal arithmetic)
- Fintech `exchange-api-integration` (FIX engine + venue adapters)

Without those foundations, the squad's skills assume context the
adopter doesn't have.

### Positioning invariants (ADR-009 §positioning)

- Personas are **fictional composites** (Diane Okafor, Marcelo
  Andrade, Yara Bensoussan, Hiroshi Tanaka, Eluned Pryce — none
  reference real people).
- The squad does NOT advertise a paid tier.
- Three VETO holders are explicit + scoped.
- The "what the squad does NOT cover" section in `team-personas.md`
  prevents scope creep into adjacent domains.

## Consequences

### Positive

- Adds a credibility marker for HFT-curious adopters.
- Forces the framework to demonstrate three-VETO interaction in
  a non-trivial domain.
- The example plan walks adopters through the full launch flow.
- Pitfalls catalog adds 18 HFT-specific rules to the validator's
  knowledge base.

### Negative

- HFT is a small audience; squad maintenance cost is real for
  potentially few users. Mitigated by the fact that the squad
  doubles as a stress test of the governance model.
- Three VETOes increase friction on every launch — by design;
  this is the contract.

### Neutral

- Squad install is opt-in via `--profile`. Adopters who don't need
  it pay zero cost.

## Blast radius

L1:
- New `.claude/skills/domains/trading-hft/` subtree (entire bundle)
- ADR-013 (this file)
- `validate-governance.sh` minimum-count check now applies to this
  squad (introduced Sprint 5 Phase 1 A.4)

**Reversibility:** HIGH — `git rm -r .claude/skills/domains/trading-hft/`
removes the squad without affecting any other code.

## References

- ADR-009 (squad contract — defines the 5-artifact shape)
- ADR-007 (SemVer + RC policy)
- PLAN-005 §3 Phase 6
- `.claude/skills/domains/trading-hft/team-personas.md` for VETO scopes
- `.claude/skills/domains/trading-hft/examples/PLAN-EXAMPLE.md` for
  the launch flow

## Enforcement commit

`05812508e7f3` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
