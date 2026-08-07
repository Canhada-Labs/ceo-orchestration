---
round: 1
archetype: Principal QA Architect
skill: testing-strategy
agent_persona: QA Architect (Principal)
generated_at: 2026-08-07T18:30:00Z
---

## Verdict

ADJUST

## Summary (3 bullets)

- PLAN-168 closes three real gaps (unwired CI tests, the INV-4 pointer regression,
  a missing ADR) that the PLAN-167 debate and rail already diagnosed with
  evidence on disk.
- The plan's strongest choice (set-equality gating for the 4 known reds, with a
  baseline file as the release valve) is architecturally sound, but the
  implementation of the nightly comparison step is unspecified, leaving a
  concrete vacuous-gate path open via the harness's --map flag (exits 0
  regardless of FAIL count, test-ownership-table.sh line 683).
- One blocking misclassification: OWN-0074 is a product defect caused directly
  by the INV-4 bug (upgrade.sh computes its "canonical pointer hash" from the
  unsubstituted heredoc), not a test instrument defect. This changes what W2
  must deliver, what the baseline map must say, and what ADR-190 must record.

## Risks

### R-QA1 -- CRITICAL: OWN-0074 is a product defect, not a test defect

The plan section 0 states "2 sao defeito do TESTE" and later the ADR-190 content
specification repeats this claim for OWN-0074. Running the cell with --keep and
tracing the manifest generation refutes the classification.

Verification method: bash scripts/tests/test-ownership-table.sh --only OWN-0074 --keep

Result:
  OWN-0074  RED  exp=PRESERVE_OWNED/HASH_CANONICAL_POINTER
                 got=PRESERVE_OWNED/HASH_UNCLASSIFIED  rc=0

After the run, the manifest records hash 00c5c640dffd173d280e1843d896d3526ecf86ed35a20ad3162a7e20ed6d2823 for PROTOCOL.md. The harness four candidates:
  c_prior (pre-run manifest)        = 6231918efb...
  c_pointer (CANON_POINTER_HASH)    = 6231918efb...  (from base install)
  c_source (src-next/PROTOCOL.md)   = 16a619d077...
  c_target (customised file on disk) = ecf4e177d0...

None match 00c5c640df, hence HASH_UNCLASSIFIED.

Cause: _refresh_protocol_pointer (upgrade.sh:1568-1571) computes
_REFRESH_PROTOCOL_CANON_HASH from the heredoc with {{PROTOCOL_SOURCE}} as a
LITERAL (the case takes the *) branch when SOURCE_DIR is not inside TARGET/).
install.sh SUBSTITUTES the placeholder before writing. The two scripts produce
different hashes for the "same" canonical pointer. The harness captures
CANON_POINTER_HASH from the install output; the upgrade records a different
canonical hash that the harness cannot recognise.

This is the INV-4 bug (docs/ownership-decision-table.md section 5.4e)
manifesting at the hash-record level. W2's shared-function fix will cure
OWN-0074: once both writers substitute the placeholder, they agree on the
canonical hash, and the harness's c_pointer candidate matches.

Consequence for AC-5: W2 will shrink the red set from
{OWN-0016, OWN-0024, OWN-0027, OWN-0074} to {OWN-0016, OWN-0024, OWN-0027}.
The baseline map MUST be updated as part of the same W2 pack, or AC-5 (fail if
the set changes, including shrinking) blocks W2's first CI run.

Consequence for ADR-190: the proposed ADR content says "4 known-open cells,
2 are test defects." That claim is wrong today (OWN-0074 is a product defect)
and will be vacuous after W2 (OWN-0074 will be closed). The ADR must reflect
the state AT LANDING: 3 known-open cells, 2 of which (OWN-0024/0027) are
test-instrument defects.

### R-QA2 -- HIGH: AC-5 baseline-comparison implementation is unspecified

The plan says the nightly CI step should "compare against ownership-baseline-map.txt
and fail if the set of reds changes." Neither the comparison script nor the CI
step body is written anywhere in the plan.

The harness has an explicit vacuous-gate path. test-ownership-table.sh line 683:
  [[ "$MAP_ONLY" -eq 1 ]] && exit 0

If the nightly step runs with --map to capture the row output, the harness
exits 0 regardless of FAIL count. A broken grep pattern or an empty comparison
expression then silently passes the gate. This is the "gate that never gates"
class the plan section 1 W1 item 3 correctly names for HARNESS-SKIP -- the
same class applies to --map misuse.

Required minimum: the CI step must (a) run the full harness WITHOUT --map,
(b) extract the set of RED cell IDs from the standard output lines, (c) compare
that set against the IDs recorded in ownership-baseline-map.txt, and (d) fail
(exit 1) if the two sets differ in either direction. The plan must supply this
implementation, not just describe the intent.

### R-QA3 -- MEDIUM: OWN-0024/0027 assert an unverified safety property

The plan correctly characterises OWN-0024/0027 as fixture defects -- the
chmod 000 "$T/$rel" approach may not simulate a backup failure the way the
spec expects (both cells show rc=0 with got=REFRESH, implying the backup step
either succeeded despite the chmod or silently continued after failure).

The concern is not about classifying them but about what the ADR-190 says.
ADR-190 must NOT state that backup-before-replace is enforced as of v1.3.0.
The safety property is aspirational until a green test proves it. A future plan
that repairs the fixture must simultaneously verify the production behaviour.

### R-QA4 -- LOW: scripts/_hash_lib.sh is already in both path filters

Verified: grep of .github/workflows/smoke-install.yml shows _hash_lib.sh at
lines 15 (pull_request filter) and 54 (push filter), added in PLAN-166. The
plan's W1 item 1 lists it as needing to be added. Adding it a second time is
harmless but creates spurious diff noise. The implementer should check before
editing.

### R-QA5 -- LOW: INV-4 test needs a non-substitution assertion

The plan requires W2 to produce "a test that installs, upgrades, and requires
the pointer to be byte-identical in both paths." Byte-identity is necessary but
not sufficient: a symmetric breakage where both paths produce the same wrong
output (both literal) would pass the equality check while the pointer remains
non-functional.

The existing probe (PLAN-167/evidence/probe-INV4-pointer-substitution.sh) already
asserts grep -c 'PROTOCOL_SOURCE' "$P" == 0 after each operation. The new test
must inherit this positive assertion.

## Must-fix (blocking)

1. Correct OWN-0074's classification. Plan section 0 and the ADR-190 content
   specification must replace "2 sao defeito do TESTE" with the accurate split:
   OWN-0024/0027 are test-instrument defects; OWN-0074 is a product defect
   caused by the INV-4 bug and will be resolved by W2. The baseline map update
   in W2 must explicitly reduce the expected red set to {OWN-0016, OWN-0024,
   OWN-0027}. Without this correction, AC-5 blocks W2's first CI run after
   W1 is landed.

2. Specify the AC-5 baseline-comparison implementation. W1 must deliver the
   exact nightly CI step body that: (a) runs the full harness without --map,
   (b) extracts the RED cell IDs from stdout, (c) compares the set against
   ownership-baseline-map.txt, and (d) fails on any set difference. Describing
   intent is not a gate; a script is.

## Nice-to-have (advisory)

1. INV-4 test: assert zero literal {{PROTOCOL_SOURCE}} in the pointer after both
   install and upgrade (not just byte-equality between the two). The existing
   probe's assertion is the right model.

2. Note in the W1 implementation runbook that _hash_lib.sh is already wired, so
   the implementer does not add a duplicate line.

3. ADR-190 ABORT_SURFACE clarity: the decision function emits 4 verdicts;
   ABORT_SURFACE is the harness's observation of an execution failure -- a fifth
   outcome in the harness vocabulary, not in the decision enum. State this
   distinction explicitly so the next maintainer does not "fix" ABORT_SURFACE
   into the 4-verdict enum and break the harness.

## Unseen by the original plan

1. W2 delivery must update the baseline map. The plan correctly states AC-5
   "fails if the set changes, including shrinking." But neither the runbook nor
   the acceptance criteria mention that the baseline file itself must be updated
   as part of the W2 pack when OWN-0074 goes green. The answer is: same pack,
   Owner sign-off, stated explicitly in the W2 delivery checklist.

2. OWN-0034 green status may warrant a note. docs section 5.4b says this row
   (protocol surface as a leaf symlink) should report ESCAPE because cat > follows
   the link outside the target. The current baseline-map shows OWN-0034 GREEN
   with exp=PRESERVE_UNOWNED/HASH_NONE. Either the guard was added during
   PLAN-167 W3 (making the escape-detection note in the docs stale) or the
   tripwire fixture drifted. This is outside PLAN-168 scope but should be
   verified before ADR-190 cites the ESCAPE mechanism as an enforcement example.

## What I would NOT change

- Nightly/per-PR split (AC-4). The e2e runs at ~25 min ceiling; putting it on
  the PR path would break the existing job. The unit oracle at milliseconds
  covers the decision function per-PR; the e2e covers the full execution path
  nightly. Both are needed and they fail for different reasons.

- Rejection of HARNESS-SKIP as a fallback (W1 item 3). Debated in PLAN-167
  round 1 and correctly rejected. A test that exits 0 when it cannot run cells
  is a dead gate. The plan's explicit rejection must stand.

- Route (b) for W2 (shared function over per-script fix). Fixing only the
  upgrade path closes INV-4 for today and leaves the class open. A shared
  function that both install and upgrade call is the correct closure per
  ADR-155 decision (i), and it is the only fix that will also close OWN-0074.

- Three-wave structure: W1 (CI wiring) before W2 (code fix) before W3 (ADR).
  Wiring the gate before fixing the defect means the fix's first CI run is the
  first live proof. Reversing the order leaves the gate dark during the
  highest-risk window.

- Set-equality gating principle. The architecture is sound: a set that shrinks
  without a corresponding baseline update IS a signal that something changed
  outside the sanctioned path. The release valve (update the baseline in the
  same PR as the fix, with Owner sign-off) is correct; it just needs to be
  written into the runbook explicitly.
