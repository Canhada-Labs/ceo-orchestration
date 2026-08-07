---
round: 1
archetype: Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (auth/crypto VETO holder)
generated_at: 2026-08-07T00:55:00Z
---

## Verdict

ADJUST

VETO NOT exercised. Nothing in the proposal breaks the trust boundary or
reverses the ADR-155-AMEND-1 §3 fail direction; every must-fix below is a
condition the debate can absorb into the model before W2. If must-fix 1
(the C2 hash-source-inheritance clause) or must-fix 3 (the harness
out-of-tree blind spot) were to ship UNFIXED into W2, that would become a
BLOCK — the literal lifting condition for each is stated inline.

## Summary (≤ 3 bullets)

- The plan converts a branch-scattered 9-dimensional ownership decision
  into a table + pure function + generated suite, and points the review
  rail at the table. The direction is sound and, in every cell I could
  verify, preserves the ADR-155-AMEND-1 §3 fail direction (under-claim
  recoverable / over-claim is the delete-class).
- Strongest parts: the orthogonal (verdict, hash_source) pair — §3.2 is
  literally the delete-class mechanism made visible as a column; the
  §5.8 dead-code deletion (verified correct on disk); and the
  required-parameter argument in §3.4 (verified: the generator default
  IS target-hashing — `_framework_manifest_set.sh:309` — and no TSV row
  expects `HASH_TARGET`).
- Weakest parts: the C2 failure-mode wording creates a record/reality
  divergence in the over-claim direction; the harness cannot see writes
  that escape the target tree through a symlink (verified: the tripwire
  file is written and never re-read); and the table has no completeness
  oracle — a legal cell absent from the TSV is undebated behavior, which
  is exactly where the next over-claim hides.

## Risks

1. R-SEC1 — HIGH — the C2 clause `inherits their hash_source` records a
   delivery that never happened. Proposal §5/C2: `ABORT_SURFACE` becomes
   the failure mode of `REFRESH`/`DELIVER` and inherits their
   `hash_source`. Taken literally, a REFRESH whose backup fails
   (OWN-0024, OWN-0027) would record `HASH_SOURCE` — the digest of bytes
   that never landed — while the target still holds the old/edited
   bytes. The record then asserts a delivery that did not occur:
   record/reality divergence in the over-claim direction, the exact
   inconsistency the delivery-record model exists to prevent. The TSV
   today pins the truthful answer (`HASH_PRIOR_RECORD` on both fault
   rows). Mitigation: accept the decision/execution split but ratify an
   explicit execution-failure invariant (INV-3): a failed execution
   never advances the record; the record after a failed execution equals
   the record before it — and for the `spec` tree, record advancement is
   atomic per surface (all files or prior state, never records for the
   subset that landed).
2. R-SEC2 — HIGH — the observation contract is blind to out-of-tree
   writes through symlinks. Verified: the fixture writes the foreign
   target at `scripts/tests/test-ownership-table.sh:291` and NO line of
   the harness ever re-reads it (grep for the word foreign yields only
   lines 290-292); `_state_digest` (line 122) reads only
   link:readlink-value for a symlink, so a write THROUGH the leaf leaves
   the observed target state byte-identical. OWN-0034 is RED today only
   via the record-side mismatch (`HASH_UNCLASSIFIED`). Once W2 fixes the
   record side to `HASH_NONE`, a still-unguarded `cat >` at
   `upgrade.sh:1624` (the `-f` test at :1592 follows the link) would
   clobber the adopter-owned out-of-tree file on every upgrade while the
   row reads GREEN — a false-green in the delete-the-adopter-file class.
   Mitigation: tripwire assertions (foreign leaf bytes + ancestor-real
   tree unchanged) on every symlink / ancestor_symlink row.
3. R-SEC3 — HIGH — OWN-0018 vs OWN-0020: identical dimensions, opposite
   outcomes, disambiguated only by prose. A pure function facing two
   identical inputs returns ONE answer; if it returns the OWN-0018 pair
   (`REFRESH`/`HASH_SOURCE`) for the OWN-0020 fixture, a tree the
   fingerprint could not fully inventory gets claimed and refreshed —
   over-claim on precisely the case ADR-155-AMEND-1 §4 pins to fail
   toward preserve (a partial/unhashable tree never produces a
   fingerprint). The C3 value `legacy_pristine_partial` is the correct
   cure; the default for any unhashable/partial tree must be the
   preserve side.
4. R-SEC4 — MEDIUM — permissive default + override-removal ordering.
   The generator defaults to target-hashing when no override is supplied
   (verified `_framework_manifest_set.sh:309`, and :247 — unset
   `FMS_HASH_ROOT_PATHS` means the override applies to ALL paths). Plan
   §W2.3 removes `FMS_HASH_ROOT_PATHS`/`FMS_LINK_PATHS` — the two
   narrowing overrides. If removal lands before (or without) the
   explicit required-hash_source mechanism, exposure WIDENS back to the
   pre-r8/r10 posture. Mitigation: required parameter (Must-fix 4)
   landing in the SAME change that removes the overrides — an ordering
   constraint W2.3 must state.
5. R-SEC5 — MEDIUM — no completeness oracle over the pruned space.
   Nothing maps every legal post-R-01..R-11 tuple to a TSV row; a legal
   cell absent from the table is silent, undebated behavior. Concrete
   unmapped cell found: skip_requested=self with live_content=edited
   (both spec and marker) — the REALISTIC skip (target holds the bytes
   of the last delivery, which are edited w.r.t. THIS source; rows
   0060/0064 cover only pristine). Wildcard-overlap detection is also
   absent (two rows matching one tuple is the OWN-0018/0020 problem
   generalized). Mitigation: with the pure function this check costs
   milliseconds — enumerate the product, apply the pruning rules
   mechanically, assert every legal tuple resolves to exactly one row.
6. R-SEC6 — MEDIUM — undeclared cross-surface asymmetry OWN-0025 vs
   OWN-0029, and the record it keeps plants future hangs. Same cell
   (prior=hash, live=special, upgrade): spec expects
   `ABORT_SURFACE`/`HASH_PRIOR_RECORD`, marker expects
   `PRESERVE_UNOWNED`/`HASH_NONE`. The standard the doc itself sets
   (§5.1: the same cell, on each surface, must have a declared answer)
   is met — but the DIFFERENCE between the two answers is nowhere
   justified. Security note: keeping `HASH_PRIOR_RECORD` on a path now
   occupied by a FIFO means every later digest-verifying reader of that
   record (doctor.sh drift scan, uninstall.sh hash-match, the classified
   walk) will open the FIFO to hash it — the same unbounded-block class,
   exported downstream. Mitigation: declare the reason for the asymmetry
   or unify the pair; sweep lstat-before-open across every reader of
   recorded paths (feeds OQ-8).
7. R-SEC7 — LOW — OWN-0017 broadens an ADR-accepted risk silently.
   Current-source takeover (prior_record=none, dir pristine ⇒
   `REFRESH`/`HASH_SOURCE`) claims a tree with NO delivery record based
   on content equality with the CURRENT source. The ADR-155-AMEND-1
   tilde-clause accepts this shape for the three pinned LEGACY
   fingerprints only. Content-preserving and backup-taken, so acceptable
   — but ADR-190 must name it as an extension of the accepted risk, not
   inherit it silently.
8. R-SEC8 — LOW — `ABORT_SURFACE` is observed by grepping English
   prose. `_ABORT_MARKERS` (test-ownership-table.sh:182) matches the
   REFUSING-to / could-not-back-up / unsupported-special-file wording.
   Doc §5.6 declares the coupling — good — but a stable structured token
   (one greppable machine marker per refusal) would make the
   operator-visible contract enforceable rather than wording-fragile.

## Must-fix (blocking)

1. Strike/replace the C2 clause `inherits their hash_source`. Adopt the
   split, but ratify INV-3 alongside it: execution failure never
   advances the record (record-after-failure == record-before;
   per-surface atomic for trees). The two fault rows (OWN-0024,
   OWN-0027) keep `HASH_PRIOR_RECORD` as the pinned observable. Lifting
   condition: consensus text (and later ADR-190) carries INV-3 verbatim.
2. C3 lands BEFORE any function is written. `legacy_pristine_partial`
   becomes a real live_content value and `fault` becomes a real column
   (15th) or its rows leave scope — a dimension the harness parses out
   of prose is a dimension nothing validates, and the fault rows are
   exactly the backup-failure safety cells. Default for
   unhashable/partial trees = preserve side (ADR-155-AMEND-1 §4).
3. Close the harness out-of-tree blind spot. Every symlink and
   ancestor_symlink row asserts, post-run, that the foreign leaf and the
   ancestor-real tree are byte-identical to their pre-run state. Lifting
   condition: OWN-0034 cannot go GREEN while any byte outside the target
   changed.
4. hash_source becomes a required, explicit input for the three
   conditional surfaces — fail-closed: a conditional-surface record with
   no declared hash_source is NOT emitted (plus a named NOTE), i.e.
   failure falls toward under-claiming. Scope it precisely: the
   rendered-template target-hashing on the broader install tree is
   LEGITIMATE (the codex-r8 P1 regression came from over-widening
   exactly here) and stays. W2.3 states the ordering constraint of
   R-SEC4.
5. Declare or unify OWN-0025 vs OWN-0029 (OQ-1/OQ-2 material), and
   record the downstream-reader consequence of keeping a digest record
   on a special path (R-SEC6).
6. Add the completeness/uniqueness oracle and the missing skip=self ×
   edited cells (or a named §4 rule pruning them — silent absence is
   what the doc itself forbids).

## Nice-to-have (advisory)

1. Structured refusal token for `ABORT_SURFACE` (R-SEC8).
2. ADR-190 names the OWN-0017 current-source takeover as an explicit
   extension of the ADR-155-AMEND-1 tilde-clause accepted risk (R-SEC7).
3. On C1 (merge `OMIT_RECORD` into `PRESERVE_UNOWNED`): ACCEPT from this
   lens — both are the under-claim direction, and the merge mechanically
   resolves declared inconsistency #1 (e.g. OWN-0028 vs OWN-0029, both
   at prior=hash). Condition: de-registration (prior_record not none AND
   the record leaves the manifest) stays OPERATOR-VISIBLE via a
   caller-emitted message — the adopter should learn the framework
   dropped its claim on SPEC/v1, because that surface silently stops
   being refreshed forever after.
4. Family-sweep the FIFO guard across every tree-walking reader invoked
   during an upgrade AND across doctor.sh / uninstall.sh digest walks
   (lstat-before-open), not just the scanner behind
   `_emit_deprecation_warnings`.

## Unseen by the original plan

1. The harness cannot observe the highest-severity failure class (writes
   escaping the target through a symlink) — see R-SEC2. The doc itself
   preaches that the instrument needs the same adversarial scrutiny as
   the subject (§5.6), and this is the largest remaining instrument gap.
2. No completeness oracle (R-SEC5) — the model has legality rules for
   REMOVING cells but no mechanism proving the KEPT space is covered;
   skip=self × edited is a live example.
3. The 0025/0029 asymmetry and its downstream-reader hang consequence
   (R-SEC6) — evidence that OQ-8 (readers) is not optional scope.
4. W2.3 ordering hazard (R-SEC4): removing the narrowing overrides
   before the explicit mechanism exists would transiently restore the
   round-8/round-10 exposure.
5. Severity classification asked of me on §5.7 (FIFO scanner): NOT
   availability-only, but the integrity component fails safe. Verified:
   `_emit_deprecation_warnings` is invoked at `upgrade.sh:2122`, BEFORE
   the backup_and_replace batch (:2850-2875) and the three conditional
   refreshes (:3001, :3014) — so the CURRENT hang strands the run with
   the tree essentially unmutated and the old manifest intact
   (availability: HIGH — unbounded block, rc=137 only under an external
   timeout; adopter FIFOs occur innocently, e.g. runtime sockets/pipes,
   so this is not adversarial-only). Once the scanner is guarded, the
   residual refresh-route hangs (the r2-F3/r9-F3 guards — currently
   MASKED and therefore unverifiable, which is itself a finding of
   vacuous controls) would hang AFTER the :2850 replacements and BEFORE
   the C.7 manifest rewrite (:3082): surfaces mutated, record stale.
   That window fails safe by construction (C.7 never runs so no new
   ownership is claimed; the next run classifies refreshed files
   H_dst==H_src, both differing from H_base, so CONFLICT and per-file
   refuse; backups sit in BAK_DIR) — integrity: MEDIUM,
   spurious-conflict noise and a stranded partial upgrade, never the
   delete-class.
6. §5.8 assessment asked of me (dead continuity line): the reasoning
   holds — delete it. Verified literally: the sanitizer runs at manifest
   LOAD (`_load_baseline_manifest`, `upgrade.sh:953` and :989 both call
   `_baseline_relpath_unsafe`, which rejects any EXISTING symlinked
   parent component, :881-:897); `_baseline_has_spec_record` (:1642)
   greps only the SANITIZED file; therefore the continuity lines at
   :1806 and :2007 can never see the record they test for. Making the
   line fire would honour a record whose path traverses a symlink — a
   breach of the ADR-155 decision-(v) provenance fence at a
   symlink-traversal boundary. Deletion is fail-safe in BOTH worlds:
   today the observable is `OMIT_RECORD` (under-claim, recoverable per
   AMEND-1 §3), and even if a future maintainer relaxes the sanitizer,
   an absent line still yields `OMIT_RECORD`, never a through-symlink
   claim. The live lstat guard at :1804 (and :2005) also holds across
   the load-to-refresh TOCTOU window, so the fence does not depend on
   the deleted line. Conditions: OWN-0030/OWN-0031 stay in the TSV as
   the regression pin, and the deletion comment names the non-local
   invariant it relies on (sanitizer-at-load).
7. Trust-class check asked of me: the plan does NOT escalate the
   unsigned-manifest trust class. prior_record is read from the same
   sanitized, decision-(v)-fenced load; the proposed home of the
   function is an already-canonical-guarded file (no new unguarded
   surface, no midnight kernel path — the OQ-5 preference is
   security-sound); the manifest still never nominates a deletion (the
   PLAN-161 amendment constraint stays intact); the fail direction on a
   MISSING record remains preserve/fallback. The one adjacent item is
   R-SEC7 (accepted-risk broadening), which is a documentation
   obligation, not an escalation.
8. `FMS_PROTOCOL_HASH` dual meaning confirmed on disk (supports OQ-4):
   `install.sh:2398` exports a PRIOR-RECORD digest
   (`_PRIOR_PROTOCOL_HASH`), `upgrade.sh:3082` exports the CANONICAL
   pointer hash (`_REFRESH_PROTOCOL_CANON_HASH`) — two semantics, one
   channel. Splitting into `HASH_PRIOR_RECORD` /
   `HASH_CANONICAL_POINTER` is the model-faithful move.

## What I would NOT change

1. The pair (verdict, hash_source) as the cell outcome. The example in
   §3.2 — `PRESERVE_OWNED` + `HASH_TARGET` records adopter bytes as the
   framework baseline, so a later upgrade clobbers and uninstall deletes
   — is the delete-class mechanism stated as a column choice. Keep it
   orthogonal.
2. The fail-direction discipline already in the TSV. Every expected
   `OMIT_RECORD`/`PRESERVE_UNOWNED` pair is the under-claim direction;
   the open rows OWN-0052/0053 correctly pin the live OVER-claim of
   today (an arbitrary live symlink recorded as a trusted LINK delivery)
   to the fail-safe answer. Do not fix those rows toward the live
   behavior.
3. The §5.8 deletion decision (with the regression-pin rows) — see
   Unseen 6.
4. The OQ-5 home preference (`_framework_manifest_set.sh`, already
   canonical-guarded) and the rule that a veto escalates to the Owner
   rather than becoming an overnight kernel ceremony.
5. R-08 pruning verdicts, not cells — the user-ceremony residue cells
   are where two real defects lived; keeping them in the space is
   correct.
6. The purity of `_ownership_verdict()` — no filesystem access keeps
   observation at the trust boundary in ONE place (the callers) and
   makes the decision auditable and cheaply exhaustively testable.
7. Committing the two inconsistencies openly instead of resolving them
   unilaterally — that is what the debate is for, and pre-deciding them
   in code is how contradictory branches were born in the first place.
