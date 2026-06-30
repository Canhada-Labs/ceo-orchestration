# PLAN-143 — VP Engineering critique (round 1)

> Lens: architectural coherence, scope discipline, sequencing, plan-as-vehicle.
> Grounded in the live tree (manifest, guard registry, CI workflow, env allowlist, ADR-143).

## 1. Verdict

ADJUST

## 2. Summary

PLAN-143 is a well-scoped, honestly-framed debt-collection plan: four small,
mostly-independent hygiene fixes with accurate provenance and correctly
identified governance entanglements. The architecture is sound — the diagnosis,
the D1/D2 loci, and the CI-gate claims all check out against the tree. The
adjustments are about **sequencing and one false premise in D3**, not about
direction: item 4 should ship independently *now* rather than ride the canonical
ceremony, and the D3 "kill-switches are unreviewed surfaces" framing is
factually wrong — they are already governed.

## 3. Risks

- **R1 — Coupling a trivial doc fix to a canonical/kernel ceremony (sequencing).**
  If items 2+3+4 ride as one plan/one merge, the `INSTALL.md` number fix (a
  10-second edit, zero guard) is held hostage to a GPG sentinel ceremony + a
  pair-rail manifest re-coupling. A debate that stalls on item 3's manifest cost
  blocks a doc accuracy fix that has no reason to wait. This is the classic
  "fix vs refactor" altitude error from my own rubric: 1-3 fixes solve item 4,
  so don't entangle it.

- **R2 — Item 3's manifest re-coupling is real and recurring.** I verified
  `.claude/governance/pair-rail-inputs-hash-manifest.txt` line 22 lists
  `.claude/hooks/_lib/audit_emit.py`. Editing it changes `inputs_hash`, so
  `validate-pair-rail-verdict.py` (release.yml step 15) BLOCKS the next release
  unless a fresh verdict artifact is regenerated OR the release ships under
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`. This is exactly the R-OPS-1 entanglement
  PLAN-142 already paid. The plan names it (D2/§2) but understates that this is
  a **second draw on the same one-shot transition window** — if PLAN-142's first
  post-edit release already consumed `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`, item 3
  needs its own fresh verdict, not a free ride.

- **R3 — Item 2 fix-locus is under-decided and risk-asymmetric.** The three
  options (hasattr-guard the probe / give `_EmitCapture` the method / skip on
  shim) have very different blast radii. The probe is fail-open already
  (`try/except` breadcrumb at `spool_writer.py:1729/1967`), so the AttributeError
  is *cosmetic noise in `audit-log.errors`*, not a rotation-correctness bug —
  rotation under the real object path is unaffected. The plan should say so; it
  currently reads as if rotation is "silently skipped" in production, which
  overstates severity and could justify a heavier fix than warranted.

- **R4 — "GREEN regression" AC depends on a network refresh the plan excludes.**
  AC-P2-regression asks for a GREEN nightly run but carves out substrate-watch
  yellow. That carve-out is correct, but it means "GREEN" is really "GREEN on
  4 of N dimensions" — the AC should state the exact expected dimension set so
  the closeout isn't argued later.

## 4. Must-fix (blocking)

- **MF-1 — Peel item 4 (INSTALL.md) off into an immediate standalone fix; do
  not gate it behind the debate or the canonical ceremony.** Verified: CI runs
  `verify-counts.sh --no-tests --quiet` (`validate.yml:96`), so the floor number
  is genuinely not CI-gated and the fix is a non-guarded doc edit. There is no
  architectural reason for it to share a vehicle with the guarded items.
  Resolve D1 in the plan text now: **1 and 4 independent; 2+3 batched.** Stop
  leaving D1 "to ratify" when the tree already answers it.

- **MF-2 — Correct the D3 premise: the kill-switches are NOT unreviewed
  surfaces.** I verified `CEO_TRUST_BYPASS`, `CEO_CANONICAL_GUARD_DISABLE`,
  `CEO_HOOKS_DISABLE`, `CEO_SKIP_HOOKS`, `CEO_ALLOW_NO_VERIFY` are already
  enumerated and governed in `_lib/env_persist_allowlist.py` (lines 33/36/40/41/103),
  and the bypass *class* already has an ACCEPTED ADR: **ADR-143 (git
  hook-bypass guard)**, which roots `CEO_*` escape-hatch reads in the ADR-040
  `trusted_env` snapshot. So D3's "several are security-relevant bypasses [that
  may need] an ADR documenting the kill-switch surface" is mostly already done.
  The plan must reframe item 1 from "review 25 unreviewed surfaces" to
  "**reconcile inventory drift**: cross-check each of the 25 against the existing
  governed allowlists (env_persist_allowlist, ADR-143, ADR-059 env-knob), flag
  ONLY the genuinely-new and un-governed ones, regen the inventory." That is a
  much smaller, more honest unit of work and it kills the spurious new-ADR.

- **MF-3 — State the item-3 manifest-window decision explicitly, do not defer
  it.** Decide in the plan: either (a) item 3's `audit_emit.py` edit regenerates
  a fresh `pair-rail-verdict-<tag>.md` as part of the ceremony, or (b) it
  explicitly piggybacks the still-open `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` window
  AND the plan first confirms that window is still open (not already consumed by
  PLAN-142's release). "Fold into the existing transition window" (D2) is an
  assumption, not a verified fact — verify it or make (a) the default.

## 5. Nice-to-have

- **NH-1 — Add a one-line "fix-locus decision" to item 2** picking
  hasattr/getattr-guard as the default (smallest blast radius, keeps the shim a
  pure test double, doesn't grow `_EmitCapture`'s API surface). Naming the
  default shortens the debate.
- **NH-2 — Reorder §3 ACs by independence, not by priority** — list the two
  independent shippable units (item 4, then item 1) first, then the batched
  guarded pair (2+3), so the execution graph reads off the AC list directly.
- **NH-3 — Record the inventory-generated date delta** (2026-06-13 → now) as
  the drift cause so the closeout can assert "regenerated at <date>" cleanly.

## 6. Unseen (what the plan misses)

- **U1 — The real root cause of item 1 is a missing CI gate, not 25 stale
  names.** `env-inventory-check.py` drift recurs because nothing fails CI when
  new env consumers land — same structural gap as item 4 (counts floor not
  CI-gated full). The plan treats both as one-time data fixes. It should at
  least *note* the option (defer is fine) of a periodic `--json status=current`
  assertion so this is the **last** manual inventory reconciliation, not a
  recurring chore. This is the 10x-rule question: at 10x the env surface, does
  manual reconciliation scale? No. Flag it; don't necessarily fix it here.

- **U2 — No mention of whether items 2+3 can share ONE sentinel/anchor-sha or
  need two.** Both edit canonical `_lib/*.py`, but a sentinel is keyed to a
  scope/anchor. If "one ceremony" means one sentinel covering two files, the
  plan must say the sentinel scope spans both `spool_writer.py` and
  `audit_emit.py`; otherwise "shared ceremony" is just "two ceremonies in one
  sitting" and the batching saving is smaller than implied.

- **U3 — Item-3 test obligation is ambiguous.** AC-P2-04 says a test asserts the
  field "survives (or is intentionally absent)". Those are opposite outcomes.
  The plan must pick the intended end-state (field SHOULD survive → allowlist
  extension is the fix) before execution, or the test is unfalsifiable.

## 7. What I would NOT change

- **The decision to govern this debt via a plan at all.** Collecting four
  sweep-surfaced items into one governed plan (rather than four ad-hoc fixes) is
  correct — it gives the canonical edits a debate trail, which is the whole
  point of the framework. Keep it.
- **D2's locus choice (canonical `audit_emit.py` allowlist over kernel
  `check_pair_rail.py`).** Avoiding a second KERNEL-HARD-DENY ceremony is the
  right call; the manifest re-coupling is the cheaper of the two costs and is a
  known, paved path from PLAN-142.
- **The honest provenance framing** (3 of 4 pre-date PLAN-142; PLAN-142 stays
  `done` and clean; substrate-watch yellow + lock-timeout noise explicitly
  ruled out of scope). This is exactly the altitude discipline I want in a
  hygiene plan — no scope creep into the benign fail-open noise.
- **Risk tier B.** Canonical-guarded edits with one possible kernel touch is a
  correct B classification; not L3-heavy, not trivially L1.

---

### OQ1 — batching items 2+3

**Support batching 2+3; reject batching 4 (and 1) with them.** 2+3 are both
canonical `_lib/*.py` ADR-153-class emit-infra edits and genuinely share a guard
and a likely sentinel sitting — batching them is real ceremony savings (MF-3 /
U2 must confirm one-sentinel scope). Item 4 is a non-guarded, non-CI-gated doc
edit and item 1 is a generated-data regen with zero guard; coupling either to
the canonical ceremony only imports the ceremony's latency for no governance
benefit. **Verdict on OQ1: batch 2+3, ship 1 and 4 independently (4 first,
immediately).**

### OQ4 — scope creep / missing dimension

No scope creep in the *items* — all four trace directly to the sweep, framing is
honest. The scope risk is **inverted**: D3 risks *inventing* scope (a
kill-switch ADR) that the tree shows is already covered (MF-2). The genuinely
missing dimension is **durability/recurrence** (U1): two of the four items
(env-inventory drift, counts floor) recur precisely because neither is
CI-gated, and the plan fixes the symptom without naming the structural gap. A
hygiene plan that doesn't ask "why did this drift, and will it drift again next
sweep?" is treating a refactor signal as a one-off fix. Name the gate gap;
deferring the gate itself is acceptable.

VERDICT: ADJUST
