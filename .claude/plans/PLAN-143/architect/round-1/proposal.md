---
plan: PLAN-143
round: 1
created_at: 2026-06-20
note: "Written post-hoc — the anti-CEO-overhead hook blocked the original pre-spawn write; the round-1 critics read the full PLAN-143-repo-hygiene-debt.md draft directly. This captures the PRE-FOLD thesis they critiqued (the plan has since been adjusted per consensus.md)."
---

# PLAN-143 proposal — repo-hygiene debt (2026-06-20 nightly sweep)

Full plan: `.claude/plans/PLAN-143-repo-hygiene-debt.md`. Distillation of the
PRE-FOLD draft the round-1 critics evaluated.

## Thesis

The post-PLAN-142 `nightly-hygiene` sweep (over merge `8a1fc68`) returned RED.
PLAN-142 itself is clean. The RED is **repo debt the general sweep exposed** —
3 of 4 items pre-date PLAN-142. This plan collects those 4 items so they are
*governed* (reviewed + sequenced) rather than fixed ad-hoc. It executes nothing;
it is a draft seeking a design-coherence verdict.

## Scope — the 4 items (as critiqued, pre-fold)

1. **env-var inventory drift (P1)** — 25 NEW consumed env names absent from the
   2026-06-13 inventory, framed as spanning model-routing + "governance
   kill-switches" + lifecycle vars; proposed remediation = review + regen.
2. **spool_writer rotation-probe AttributeError (P1)** on the `_EmitCapture`
   shim → rotation silently skipped; canonical-guarded file.
3. **codex_invoke_dispatched drops exit_code (P2)** — not in the audit_emit
   allowlist (ADR-153 class); PLAN-142's restored rail made it observable.
4. **INSTALL.md tests-floor stale (P2)** — `12000+` vs live ~11.7k; not CI-gated.

## Decisions proposed (pre-fold)

- D1: batch items 2+3 under one canonical ceremony; 1+4 independent.
- D2: prefer canonical `audit_emit.py` over kernel `check_pair_rail.py` for item 3.
- D3: whether the kill-switches warrant an ADR.

## Open questions put to critics

- OQ1: batching 2+3 correct, or split by kernel/canonical locus?
- OQ2: do the kill-switches need an ADR?
- OQ3: is re-touching the pair-rail inputs-hash manifest acceptable while
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` is in transition?
- OQ4: scope creep, or a missing debt dimension?

(Outcome: all 3 critics ADJUST, 0 VETO → PROCEED; 7 adjustments folded. The
biggest correction: OQ2/D3's "kill-switch" premise was factually wrong — see
`consensus.md` CF-1.)
