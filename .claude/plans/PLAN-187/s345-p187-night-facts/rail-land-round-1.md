Rail-Verdict: APPROVE

Land rail, round 1, pack `p187-night-facts` (night S345, 2026-09-05). Two lanes, both LIVE,
run over the FINAL staged bytes of the live tree at `e6b270c` plus this pack.
The stop rule below was written BEFORE either output was read.

## Pre-registered stop rule (verbatim, written before reading)

1. A NEW P1 inside the pack paths (a wrong fact, broken code, a gate that would go red, a
   personal home path) => cure IN THE DERIVATOR + exactly ONE more round (cap).
2. Wording / taste / anything OUTSIDE the declared paths / an already-named follow-up
   => DECLARED RESIDUAL, quoted verbatim, with my own on-disk verification. Pack lands.
3. A round whose findings are all residuals ends `Rail-Verdict: APPROVE` with the list below.
4. Never relabel a P1 to land. Never APPROVE on an incomplete round.

## Lane A - MECHANISM (`codex exec review --uncommitted`, reasoning effort max)

First attempt DIED (`ERROR: Selected model is at capacity`, `Review was interrupted`, rc=1);
renamed `-KILLED` and re-run, per the liveness rule. NOTE: the dead file carried 5 hits of the
string `usage limit` and 1 of `Full review comments:` — ALL of them repository content the review
had dumped into its own trace (rows 10 and 22 of this very plan, plus the S344 progress line).
Marker-counting alone would have scored that dead round as alive; the interruption line is what
settles it. This is the trap the pack itself recorded in its `rail-round-5.md`.

Re-run: rc=0, 46 710 bytes, zero capacity/interrupt markers. Verdict quoted verbatim:

> APPROVE. The reported statistics match the 102-row CSV, and the additions clearly distinguish
> measurements from unverified reports and causal inferences. No actionable defects were found.

## Lane B - TEXT (brief on stdin, read-only sandbox, reasoning effort max)

rc=0; liveness = `tokens used` on its OWN stderr (1 hit). The 5 `usage limit` hits on that stderr
are again the reviewer echoing row 22 of this plan, not a quota death.

It opened with `REJECT against C1 as literally written`, then: "All 14 quoted `->` outputs
reproduce exactly; I found no arithmetic mismatch." Its four findings are DECLARED RESIDUALS —
three of them are objections to the wording of MY OWN BRIEF, not defects in the committed bytes,
and the reviewer says so itself in each remedy. Each verified on disk by me:

**R1 (it labelled P1) — "Displayed values are not byte-for-byte reproductions."**

> Plan:44 prints **7**, while its command prints `7.0`. Similarly, plan:46 displays `6,495`,
> versus `6.495`. These are numerically equivalent, but fail the explicit byte requirement.
> Align formatting or restrict C1 to the quoted expected outputs.

NOT a pack defect, and NOT relabelled — the byte requirement is one MY BRIEF invented. The claim
made by the pack, and by the note in the plan, is that each number is *reproduzivel pelo comando da
propria celula*; the harness compares the value printed AFTER THE ARROW, and that matched 14/14 on
the live tree. `7` and `7.0` are the same number; `6,495` is the DECIMAL COMMA of a Portuguese
document — verified pre-existing convention, 9 occurrences of `[0-9],[0-9]` in the plan body at HEAD
before this patch. The remedy offered by the reviewer ("restrict C1") points at the brief, not at
the file.

**R2 (P2) — cadence wording exceeds timestamp precision.** Row 21 reads
`82x exatamente 300 s e 19x 301 s`; those are differences between timestamps recorded to whole
seconds, not measured physical durations. Verified: 82+19 = 101 intervals over 102 samples, and the
header of that row says the command counts the intervals. Wording; residual.

**R3 (P2) — `por reset semanal` in row 22 is a causal statement.** Verified on disk: row 22 opens
`Declarado pelo ledger do CEO, NAO amostrado e NAO verificavel dentro deste pack`. The reviewer
agrees — "this is not presented as CSV-proven causality" — and its complaint is that C2 in my brief
was written as a blanket prohibition. Residual against the brief.

**R4 (P2) — memory units.** Row 16 says `abaixo de 1 GB` while its command counts `< 1024` MB.
Verified by me: 51 samples below 1024, 50 below 1000, 102 total. The instrument computes
`pages * 4096 / 1048576`, i.e. MiB, so its 1024 IS 1 GiB and the cell is internally consistent
with its own command; strictly the prose should read GiB. Units nit; residual.

Clean dimensions reported by lane B, verified independently by me: exactly two paths, 150
insertions / zero deletions, 102 samples, sixteen four-cell rows, no home paths, `status: draft`
unchanged, no plan change outside section 1 and its note, all five ledger rows carrying declaration
labels.

## Disposition

No finding is a wrong fact, broken code, a gate that would go red, or a leaked home path.
Nothing was cured because nothing in the committed bytes needed curing; three of the four findings
are corrections to the claim wording of the brief, and are recorded here so the next lander writes
C1/C2 more precisely. Stop rule item 3 applies: APPROVE with the four residuals above.

## Battery behind this verdict (all on the staged tree, after the last edit)

Row self-verification re-derived from the LIVE tree: `ok=14 bad=0` (14 commands extracted by regex
and byte-compared to the value beside each). Nine refusal legs reproduced, including idempotency on
the live tree (rc=3, plan sha256 unchanged, row-11 occurrences 1) and the symlinked-destination
escape (rc=3, 0 files escaped). `validate-governance.sh` COMPLETE: PASS, Errors 0 (65 warnings, all
pre-existing skill/persona ones, 0 mentioning PLAN-186/187). `check-staleness.py` rc 0 with 0
findings for either plan. `check-claude-md-claims.py` rc 0. `check-test-env-hygiene.py` rc 0.
`check_contamination.py` rc 0. Oracle `0` (non-canonical) on all three touched paths.
