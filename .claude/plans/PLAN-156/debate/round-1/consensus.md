---
plan: PLAN-156
round: 1
created_at: 2026-07-10
outcome: design-coherent-with-adjustments
verdicts: {vp-engineering: ADJUST, security-engineer: ADJUST, devops-engineer: ADJUST}
---

# PLAN-156 round-1 consensus — design-coherent (ADJUST_PROCEED)

> Synthesized at the close of round 1 (proposal + 3 archetype critiques).
> All three verdicts were ADJUST with convergent, bounded adjustments and
> no residual disagreement → no round 2 was needed.

Three archetypes, three ADJUST, zero REJECT. The seam-reuse thesis is
endorsed by all three; every objection is a bounded pin-down, not a
redesign. Convergent findings across ≥2 reviewers are promoted to
blocking must-fixes and applied to the plan text before the pair-rail R2.

## Convergence map (who raised what)

| # | Adjustment | Raised by | Severity |
|---|---|---|---|
| C1 | Exit-2 chokepoint = shared shim, **decision-derived** (emitted-deny→2/emitted-allow→0/**no-decision-crash→fail-open-0 [infra]**); input-parse failure EMITS a deny→2; UNCONDITIONAL not env-gated | VP-Eng (critical), Sec R-SEC1/2, DevOps R-OPS-2, codex-R1 (implicit) | BLOCKING |
| C2 | Exit-2 has **CI teeth**: hermetic meta-test — a security matcher fed UNPARSEABLE INPUT emits deny→exit-2 (NOT a bare crash, which is infra→fail-open), reddens CI; paired infra-crash→allow case; not a W7-only local artifact | Sec must-fix 2, DevOps R-OPS-2 | BLOCKING |
| C3 | Matcher **tool-name mismatch** is a dead-gate upstream of our Python; W0 fixture (a) gates the ENFORCED claim; W7 positive-control drives a **native** name (`run_terminal_cmd` for `rm -rf`) | Sec R-SEC3, VP-Eng (split vocab) | BLOCKING |
| C4 | Council external lanes (codex+grok) route through the **ADR-114 egress redactor**; repo-content→xAI/OpenAI HONEST-LIMITATION; OQ5 becomes a privacy decision | Sec R-SEC4 | BLOCKING |
| C5 | Council grok lane containment = **OS-level**, hard-depends on the C2 exit-2 proof; hooks profile is defense-in-depth only | Sec R-SEC6, VP-Eng, codex-R1 P2 | BLOCKING (already applied) |
| C6 | **Double-fire**: pick ONE hook surface at W0; assert with an invocation-**count** control — total==1 (chosen==1, non-chosen==0), not deny-observed (pair-rail R2 refined ==1→the split) | Sec R-SEC5, VP-Eng | BLOCKING |
| C7 | Grok **CI hermeticity** = acceptance criterion: fixture/recorded-wire replay, ZERO grok binary, ZERO xAI secret on any runner; live-fire = local T2 tier | DevOps R-OPS-1 | BLOCKING |
| C8 | **Council fenced OUT of CI**: no CI job invokes a live lane; CI tests only degradation logic against fixture lane outputs; per-lane budget = hard kill | DevOps R-OPS-3, Sec nice-to-have 4 | BLOCKING |
| C9 | **validate.yml anchor**: extend the existing `for adapter in claude codex` loop → `claude codex grok` (grok takes fixture path); no adjacent steps; consolidate grok yml edits into ONE signed patch | DevOps R-OPS-4 | BLOCKING |
| C10 | Pin bump only **WIDENS** upper bound (keep `>=0.128.0`); binary-SHA is the real gate; consumer is release.yml step-15; never bump in an open release window | DevOps R-OPS-5 | BLOCKING |
| C11 | **Arming refuse-on-drift**: `grok --version == pin` or harness SETUP fails closed (not the user session); auto-update = substrate-watch trigger re-running the matrix controls | Sec R-SEC7, DevOps | BLOCKING |
| C12 | Enroll `grok-cli-pin.txt` + binary-SHA in `_KERNEL_PATHS` in the SAME wave they're created (else Wave-4 registry edit trips a surprise kernel block) | DevOps unseen-3 | ADVISORY→applied |
| C13 | Treat external-lane RESPONSE as untrusted: size-cap, schema-conform, fail-closed-to-ADVISORY (`parse_verdict_strict` pattern), FENCE shard text in the synthesizer prompt; add `council_lane_invoked` audit action | Sec nice-to-have 1/2 | ADVISORY→applied |
| C14 | W0 adds fixture question: is `exit 2` inert on Codex? (gates whether the C1 mapping can be UNCONDITIONAL vs adapter-aware) | Sec unseen-4 | BLOCKING |

## Preserved (all three said: do NOT "improve" these)

- Honest ADVISORY labels for grok's non-blocking Stop/UserPromptSubmit/
  SubagentStart; push-time is the enforcement point. No fake blocking Stop.
- Fail-loud council (`STATUS: unavailable`, never silent vendor
  substitution) — the cross-vendor-disagreement signal is the raison d'être.
- Council is advisory evidence; V0-V3 verification cascade unchanged.
- ENFORCED cells certified by behavioral positive-control, never config.
- Exact-version grok pin + substrate watch (not a semver range).
- Wave 1 (codex 5.6) decoupled from grok waves — correct risk sequencing.
- Hermetic-CI / local-live-fire tiering inherited from codex.

## Disposition

`design-coherent`. All 14 adjustments applied to the plan text (C1-C11,
C14 as plan edits; C12-C13 folded into the relevant waves). No open
disagreement remains among the three archetypes → no round 3 needed;
proceed to pair-rail R2 over the adjusted plan, then `draft → reviewed`.
The Council (Wave 6) survives with its own mini threat model + the
CONCEDED escape hatch (slips to a follow-up plan without blocking
Waves 0-5 if the pair-rail R2 still objects to the egress surface).
