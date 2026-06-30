# ADR-082 — L7c Mitigation Default-On — `--dispatch=mitigated` becomes default for non-`code-reviewer` archetypes

## Status

ACCEPTED — Session 67 (2026-04-27) Owner directive override on the
ADR-057 soak window. Acceptance grounds: (a) Sonnet 2×2 empirical
30/30 dispatches succeeded across model + body combinations
(Sessions 65+66, see ADR-080 §Layer 7d-v2 Sonnet companion),
which retired the strongest non-mitigation hypothesis (model as
discriminator) and confirmed mitigation is the load-bearing fix
regardless of model. (b) Production-side rollback path remains
intact via `CEO_MITIGATION_DISABLE=1` env-var kill-switch — soak
window in production becomes passive monitoring (advisory) rather
than gating decision. (c) Owner deadline directive 2026-04-27
to close all open code/audit/optimization items by 2026-05-01.

## Acceptance fields

- accepted_at: 2026-04-27
- accepted_via: Owner directive override on ADR-057 soak (Session 67)
- enforcement_commit: 94783b4
- soak_disposition: passive — `CEO_MITIGATION_DISABLE=1` kill-switch
  available for instant rollback if production fabrication rate >5%
  observed via `audit-telemetry.py` (D1.4 deliverable).

## Context

PLAN-060 Layer 7d-v2 EMPIRICAL (Session 65, 2026-04-26, commit
`d35b882`) demonstrated that all 4 experimental cells declared with
`model: claude-opus-4-7` + `tools: [Read, Grep, Glob, Bash]`
successfully execute Bash, regardless of name pattern or body
content. The strong remaining discriminator candidate is `model:
claude-opus-4-7` in frontmatter.

Production reality (per PLAN-060 §Layer 7 N=11 self-report sweep
+ §Layer 7c mitigation experiments):

| archetype | model | runtime tool grant (empirical) |
|---|---|---|
| `code-reviewer` | opus-4-7 | full Read+Grep+Glob+Bash ✅ |
| `qa-architect` | sonnet-4-6 | Grep+Glob only ❌ |
| `performance-engineer` | sonnet-4-6 | Grep+Glob only ❌ |
| `security-engineer` | opus-4-7 | (residual datum, possibly self-report fabrication) |
| `devops` | haiku-4-5 | Grep+Glob only ❌ |

Layer 7c shipped a mitigation: route via `subagent_type=
general-purpose` with persona injected as system prompt. Empirical
6/6 success across qa+cr personas. Implementation lives behind:

- `--dispatch=mitigated` flag on `.claude/scripts/inject-agent-context.sh`
- `CEO_DISPATCHER_MODE=mitigated` env-var fallback
- `CEO_MITIGATION_DISABLE=1` kill-switch
- 14 unit tests
- Adopter guide `docs/CEO-MITIGATION-DISPATCH.md`

This was shipped as **opt-in** in commit `57da31b` (Session 63
cont). Production CEO turns continue to dispatch via native rail
unless the operator explicitly invokes the flag.

## Problem

The opt-in disposition leaves the rail anomaly (Sub-agent fabrication
documented in ADR-080 §H4) live for 4 of 5 production archetypes by
default. Every spawn of qa-architect / performance-engineer /
security-engineer / devops on the native rail risks:

1. Tool-grant mismatch between persona expectation and runtime
   reality (Bash declared in FM but not granted at runtime).
2. Coping behavior modes documented in ADR-080: fabrication of
   tool-call syntax in text OR honest refusal. Both invalidate
   the verdict file the debate protocol depends on.
3. Operator cognitive load: "did I remember to set the flag for
   this dispatch?" — a manual gate that fails open.

The Layer 7d-v2 EMPIRICAL outcome confirms the model-as-discriminator
hypothesis is the strongest remaining candidate. While we wait for
Anthropic-side resolution (or sonnet companion experiment to fully
falsify model-as-discriminator), the safer prod posture is to make
the working dispatch path the default.

## Decision

**Flip `--dispatch=mitigated` from opt-in to default-on for all
non-`code-reviewer` archetypes.** Specifically:

1. **`.claude/scripts/inject-agent-context.sh`:** change default
   mode resolution order to:
   ```
   default: mitigated  (was: native)
   override: --mode=native | CEO_DISPATCHER_MODE=native
   kill-switch: CEO_MITIGATION_DISABLE=1 (preserves prior behavior)
   ```
   `code-reviewer` archetype continues on native rail (it's the only
   one with empirically-confirmed full tool grant + the L7c mitigation
   would lose ADR-052 VETO-floor model assignment for cr alone if
   universally applied).

2. **`.claude/team.md` ROUTING TABLE:** annotate each archetype row
   with a "Dispatch path" column stating native (cr only) vs mitigated
   (qa, pe, se, devops). Reference ADR-082.

3. **`PROTOCOL.md` Spawn Protocol §Step 3:** add a sub-bullet
   describing the default-on policy + how to override per-call for
   diagnostic dispatch.

4. **`.claude/commands/spawn.md` slash command:** mention the default
   in the procedure preamble + how to override.

5. **Tests:** extend `inject-agent-context.sh` test suite to assert
   default mode is `mitigated` for non-cr archetypes; add regression
   tests for the override paths (env var + flag + kill-switch).

## Consequences

### Positive

- Production qa/pe/se/devops dispatches use the empirically-validated
  full-tool-grant path by default. No more silent fabrication risk
  on the dominant code path.
- Operator cognitive load drops: no manual flag.
- ADR-080 rail anomaly is mitigated by default for the 4 affected
  archetypes; only `code-reviewer` continues on native rail (where
  it works correctly).
- Empirical falsification posture is preserved: a sonnet companion
  experiment can still flip individual archetypes to native via
  `--mode=native` for direct comparison.

### Negative

- ADR-052 VETO-floor model assignment becomes advisory rather than
  enforced for non-cr archetypes (general-purpose inherits CEO model
  unless explicitly overridden in the mitigated dispatch).
- Tool over-grant: general-purpose has Edit/Write/Skill that most
  archetypes don't need. Mitigation accepts this as the cost of
  Bash availability.
- Persona drift: documented in L7c experiments (one Exp8 dispatch
  added a bonus haiku). Soak window will measure rate; if drift
  exceeds 5% (FPR threshold per ADR-057), revert to opt-in.
- If Anthropic ships a role-mismatch heuristic (`subagent_type=
  general-purpose` but persona claims to be qa), the framework
  loses its working dispatch path for non-cr archetypes. Currently
  unobserved; mitigation: monitor + soft-roll-back via
  `CEO_MITIGATION_DISABLE=1`.

### Neutral

- `code-reviewer` continues on native rail. No behavior change for
  the only archetype where native works.
- Adopter projects need to update their `.claude/team.md` ROUTING
  TABLE if they extended it with custom archetypes; default
  inheritance applies unless explicitly opted out.

## Alternatives considered

### A. Continue opt-in, document harder (REJECTED)

Adopter would still need to remember the flag every dispatch.
Empirically confirmed in L7c that the flag works; making it default
removes the manual gate. Documentation alone does not fix the
silent-fabrication exposure.

### B. Wait for Anthropic upstream fix (REJECTED)

Owner directive ("Close → Optimize → Dogfood → Benchmark → External")
prioritizes Optimize over External. Upstream resolution is in
External territory; we should ship the optimizer-side fix in the
meantime.

### C. Ship sonnet companion 2×2 first, then decide (DEFERRED — not
blocking)

The Sonnet 2×2 (Cell E + F, queued for Session 66 via PLAN-060
follow-up) would isolate model-as-discriminator definitively. But
the L7c mitigation is empirically validated regardless of whether
the discriminator is exactly model-only or model+something else;
either way, mitigated dispatch works. Sonnet 2×2 informs **why**;
this ADR is about **what to do** while waiting for the why.

### D. Pin all archetypes to opus-4-7 (REJECTED at ADR-080 §B)

Cost-prohibitive (3-4× per-token cost of sonnet) + does not address
the security-engineer residual datum (which is opus-4-7 yet may
also fall in the rail-anomaly bucket). Better to bypass the rail
entirely via mitigation.

## Owner ceremony — implementation procedure

This ADR's edits land in fresh CLI Session 66 after the Owner has:

1. GPG-signed `.claude/plans/PLAN-061/architect/round-1/approved.md`
   (this signs the sentinel scope including the canonical paths
   listed under Decision §1-3).
2. Run `OWNER-A-PLUS-B-MEGA-CEREMONY.sh` (stages Cells E+F for the
   Sonnet 2×2 companion experiment in parallel — independent of A).
3. Closed + relaunched the Claude CLI process so the registry
   bootstraps with the staged cells.

In the fresh Session 66, CEO autonomous flow:

- `git mv .claude/plans/PLAN-061/architect/round-1/adr-082-draft.md
  .claude/adr/ADR-082-l7c-mitigation-default-on.md`
- Edit `.claude/team.md` (sentinel allows)
- Edit `PROTOCOL.md` (sentinel allows)
- Edit `.claude/scripts/inject-agent-context.sh` (non-canonical)
- Edit `.claude/commands/spawn.md` (non-canonical)
- Update test suite
- Commit + push

Owner final action: run `OWNER-SONNET-CLEANUP.sh && git push`.

## Soak window + rollback

Per ADR-057 FPR observation discipline:

- **7-day soak window** post-implementation. Audit log monitors
  `subagent_dispatch` events for `dispatch_mode=mitigated` rate +
  any `fabrication` detector hits.
- **Rollback trigger:** if fabrication rate >5% across 100+ dispatches
  in soak window, revert via `CEO_MITIGATION_DISABLE=1` env var
  globally + reopen this ADR with empirical data.
- **Acceptance trigger:** if soak completes with fabrication rate
  ≤1% AND zero role-mismatch heuristic flags, mark ADR ACCEPTED
  + close PLAN-061.

## Enforcement commit

To be filled in at Session 66 closeout (this ADR's promotion to
canonical path + the wire-up edits land in a single commit).

## References

- ADR-080 — Rail anomaly H4 defense-in-depth (root cause + L7c
  mitigation discovery)
- ADR-052 — VETO-floor model assignment (canonical-5 model policy)
- ADR-057 — FPR observation window (BLOCK mode escalation criterion)
- ADR-058 — Adversarial framing (code-reviewer's discriminator section)
- PLAN-060 — Layer 4 mini-matrix + sec-p0-04 + token-as-time unit (closed)
- PLAN-061 — L7c default-on wire-up (this ADR's parent plan)
- Memory `project_plan_060_layer7_h8_confirmed.md` — full empirical record
- `docs/CEO-MITIGATION-DISPATCH.md` — adopter guide for the mitigation
