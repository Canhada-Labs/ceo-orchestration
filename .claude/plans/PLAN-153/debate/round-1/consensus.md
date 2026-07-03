---
plan: PLAN-153
round: 1
round_verdict: PROCEED
critiques: 3
verdicts: [ADJUST_PROCEED, ADJUST_PROCEED, ADJUST_PROCEED]
adjustments: 13
created_at: 2026-07-03
---

# PLAN-153 — round-1 consensus

Three critiques, three ADJUST_PROCEED, zero REJECT/VETO. All must-fixes were
accepted; the round verdict is **PROCEED** (design-coherent after the 13
adjustments below are applied to the plan file). Per PLAN-134 W1: this
certifies internal coherence across forced perspectives — shipping authority
remains with the verification cascade (V2 Codex pair-rail + V3 Owner GPG).

## Consensus findings (2+ critics flagged)

1. **Wave L-levels contradict the canonical-guard surface** (Critic-A CRITICAL;
   Critic-B ceremony-scope). `install.sh` (:187), `upgrade.sh` (:189), ALL
   `.github/workflows/*.yml` (:182), `SKILL.md` namespace (:118-122),
   `lessons.py` (:129) are guarded; waves B/C/D/G were labeled "L2 proceed
   directly" and Wave 0 minted only SENT-E/SENT-F. The plan also asserted
   "lessons.py is not canonical-guarded" — factually FALSE.
2. **The static gate as written is false-green on the exact S254 class**
   (Critic-B + Critic-C, independently, both evidence-grounded). Existing
   `check-active-hooks-executable.py` already does exists+exec-bit and the S254
   P0 PASSED it; the shim resolves via `$CLAUDE_PROJECT_DIR` at runtime, not
   `REPO_ROOT`; a by-design infra fail-open (pair-rail on Codex-unavailable) is
   statically indistinguishable from a dead rail. Fix: behavioral
   positive-control per blocking hook (planted violation → assert BLOCK,
   CI-replayed, dependency mocked-present) + runtime-resolution modeling +
   runtime-unresolvable planted fixture + extension (not duplicate) of the
   existing script.
3. **Wave F is the danger zone and must leave this plan** (Critic-A: 3-4 plans
   in a trenchcoat; denial-dampening makes blocking security guards quieter
   under repeated blocks — attacker-probing anti-pattern. Critic-B: lesson
   pipeline is an injection path into /ceo-boot gated by a usefulness filter;
   observe store is a PII/PHI surface for exactly the installs Wave D targets).
   Fix: carve to PLAN-154; dampening may condense ADVISORY output only;
   injection-scan payload+distiller output; bounded lesson schema; fenced
   one-liners; metadata-only v1 (resolves OQ2).
4. **Third-party import needs per-file license verification + a mechanical
   gate + a pull-back path** (Critic-A per-file provenance + no-exit-path;
   Critic-B `check-imported-skill.py` gate + NOTICE ledger stronger than 40
   frontmatter blocks). Resolves OQ1 → NOTICE ledger at pinned SHA.
5. **New gate scripts must not ship CI-dark** (Critic-C hard checklist item —
   validate.yml pins explicit pytest paths, new test files are not
   auto-discovered; Critic-B CI-replayed fixtures). Same-commit CI wiring is a
   per-execution-unit rule.

## Single-critic insights kept (all accepted)

- Critic-A: 7-day SKILL.md soak is wall-clock not tokens → soak posture is a
  new Owner OQ3; publish token budget and calendar schedule separately.
- Critic-A: C→D telemetry gate is theater for greenfield domains → reframe
  what /skill-health authorizes (existing-151 retire/merge/discovery); D gated
  on C-complete + Owner per-batch go/no-go ranked by consumer-plausibility.
- Critic-A: budget ~35% under → re-budget bottom-up (2.0-2.8M for 153 minus F).
- Critic-A: E's gate flags F's intentional opt-in no-op hooks → annotation/
  allowlist + fixtures in both directions.
- Critic-A: ADR-173 scope creep → ADR-175 allocated for citation gate +
  prompt-defense contract.
- Critic-A: record the 72 unmerged ADAPTs as defer-pointers; C→G coupling on
  security-and-auth/testing-strategy (merge after restructure).
- Critic-B: destructive-Bash citation verification is fail-CLOSED (C4/_e3
  mirror); redact + mark-as-data before HMAC write; liveness/heartbeat for
  fail-open rails RED in /ceo-boot; audit-log-as-data binds Wave C readers;
  pre-commit `touched − SIGNED SCOPE = ∅` assert on guard-surface edits;
  deny-baseline expansion + env-glob precision + honest coarse-backstop framing.
- Critic-C: drop `next` dist-tag (contradicts PLAN-013 anti-goals #3/#16);
  supply-chain-watch on ubuntu-latest, schedule-only, never fork-PR;
  idempotency covers BOTH tag workflows (`gh release view || create` +
  `already_published`); upgrade-replay back-compat → ADR-155 drift-classifier
  fallback; CEO_SOTA_DISABLE inheritance; manifest regen+diff idempotency gate;
  /plugin update is Owner-initiated only; AGENTS.md gets a freshness check.

## Single-critic insights rejected / deferred

- None rejected. Critic-B advisory "prompt-defense on the distiller spawn" and
  all Wave-F mechanics move to PLAN-154 (deferred with the wave, not dropped).

## Plan adjustments (applied to PLAN-153 file)

A1 budget/frontmatter; A2 Wave-0 sentinels (SENT-B; install.sh into SENT-E;
lessons.py falsehood removed with Wave F; SKILL.md ceremony = SP-NNN +
/skill-review; OQ3 soak posture); A3 B/C/D/G reclassified L3; A4 C→D gate
reframed; A5 Wave E rewritten (positive-control core + runtime-resolution +
liveness + deny expansion + fail-closed citation + ADR-175 split + CI-wiring +
kill-switch + fork-PR posture); A6 Wave B corrections (RC/dist-tag removal,
dual-workflow idempotency, replay back-compat, manifest idempotency); A7 Wave C
audit-log-as-data; A8 Wave D mechanical import gate + quarantine + NOTICE +
two-batch Owner go/no-go; A9 Wave G sequencing after C; A10 Wave F carved to
PLAN-154; A11 §Deferred (72 ADAPTs + batch-2); A12 OQ1/OQ2 resolved, OQ3
added; A13 ADR-173/174/175 allocation.

## Round verdict

**PROCEED** — apply A1-A13, then `status: reviewed`. No round 2 needed:
zero cross-critic contradictions (all three endorse ordering, human-gate red
line, clean-room ports, C-before-D intent); every must-fix is additive.
