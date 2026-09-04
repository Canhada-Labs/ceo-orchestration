Rail-Verdict: CHANGES-REQUESTED (2 P2 — both DECLARED, not cured; round cap of 3 reached, both measured unreachable on the shipped bytes)

# Pair-rail round 3 — land of `ac14-classifier-v2` (S343, autonomous night run)

* **Instrument:** `codex exec review --uncommitted --skip-git-repo-check`
  (`gpt-5.6-sol`), run from the repository root against the tree carrying the
  round-1 and round-2 cures, applied and staged.
* Neither earlier finding reappears. Two new P2s; the round cap for this land
  is three, so both are DECLARED here with the measurement that bounds them,
  rather than cured without a round of their own to review the cure. Curve for
  the land: 1, 1, 2 — it is not falling, and that is written down rather than
  smoothed over.

## [P2, DECLARED] `parse_doc_rows` / `parse_doc_case_index` do not skip HTML comments

*Claim:* both parsers take any line whose first non-space character is `|` as a
table row, so a table commented out with `<!-- ... -->` would still bind.

*Measured on the shipped doc:* `docs/task-classifier-2b.md` contains **zero**
`<!--` sequences, so there is no commented table and the finding is LATENT, not
live.

*And the direction is fail-CLOSED.* Every way a commented row can differ from
the live one lands on a RED, not a green: a second copy of a row id is
`DOC-DUP` (rc 1, the round-1 cure of this pack's own build rail); a row id the
fixture does not carry is `DOC-UNBOUND` (rc 1); different cell text is
`2B-DRIFT` (rc 1). The only silent outcome is a commented row whose text
already equals the norm — which asserts the truth. So the residual is a
possible FALSE RED on a doc that comments out a table, never a false green.

*Why not cured here:* the fix is a comment-aware scanner over the doc, i.e. a
change to the parsing ARCHITECTURE of the binding this whole gate rests on, and
the cure would ship without a rail round of its own. It is written down instead.

## [P2, DECLARED] Q3 bullet (a) is unconditional, and can outrank R3

*Claim:* Q3's bullet (a) — "it writes or changes a gate, check, oracle,
assertion or lint whose verdict future runs depend on" — reads YES for a task
that merely IMPLEMENTS a check whose predicate was already fixed elsewhere (for
example, rendering an assertion from a table the Owner already approved). The
*Test* two lines below is narrower ("a rule chosen HERE"), and §2b's R3 assigns
fixed-question code/config derivation to `high`, so the bullet and the test can
disagree, resolving to `xhigh`.

*Status:* this is a NORMATIVE question about the published procedure, not a
mechanical defect. Deciding it changes which row a class of real tasks lands
in, which moves the fixture's coverage and touches the reading of §2b — and
§2b is the plan's norm, which this pack deliberately does not edit (section 4
of `AC14-CLOSEOUT-EDITS-S340.md` says so in as many words). The neighbouring
boundary is already documented at Q4 (the read-only agent that returns a
deriver, this pack's own build rail r1 [P1]), and the two decided boundary
cases in the fixture are where such a call belongs.

*Handed on:* the closeout, or a W5 follow-up, should either narrow bullet (a)
to "chooses the rule the gate enforces" or add a third boundary case deciding
"implements a gate from a fixed predicate" in writing. Until then the *Test*
sentence is the tie-break, and it already says "chosen HERE".

## Battery on these exact bytes

* oracle `check-classifier-cases.py` rc 0 CONSISTENT — 7 rows, 7 terminals over
  6 questions, 10 cases (8 worked, 2 boundary), coverage R1..R7 with R3=2,
  20 citations verified on disk, no line pin;
* `.claude/scripts/tests/test_ac14_classifier_check_rc.py` — 14 passed;
* full `.claude/scripts/tests/` — 5958 passed, 23 skipped, 1 failed;
  the failure is `test_skill_patch_propose.py::test_diff_size_cap_enforced_with_many_lessons`
  (a 30 s subprocess timeout), reproduced at HEAD in a clean worktree WITHOUT
  this pack: pre-existing, not this pack's.
