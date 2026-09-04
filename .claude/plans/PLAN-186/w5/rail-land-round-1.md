Rail-Verdict: CHANGES-REQUESTED (1 P2 — REAL, reproduced on disk by the lander, cured in the pack derivator)

# Pair-rail round 1 — land of `ac14-classifier-v2` (S343, autonomous night run)

* **Instrument:** `codex exec review --uncommitted --skip-git-repo-check`
  (`gpt-5.6-sol`, reasoning effort xhigh), run from the repository root against
  the applied-and-staged live tree at base `685868a`.
* **Surface:** the six paths the pack writes — 2338 insertions, 1 deletion.
* **Note on the round:** a first invocation was killed mid-review by the host
  before it emitted a verdict (partial transcript kept as
  `codex-r1-killed-partial.txt`); the round below is a complete re-run. A
  killed run proves nothing and was not counted.

## Finding — [P2] section 5 of `AC14-CLOSEOUT-EDITS-S340.md` offered two options that violate its own invariant

The reviewer's claim, verified by the lander ON DISK before any cure:

| what the shipped text said | what disk says |
|---|---|
| "one of them lands in a file the installer SHIPS" | **both** do |
| option (c): keep the pointer "only in `PROTOCOL.md`, which is staged" | `PROTOCOL.md` is staged by `scripts/install-npm.sh` **and** listed in the `files` whitelist of `npm/package.json`; `docs/` is in neither |

So the section closed with "the one thing it may not do is leave an installed
file pointing at a path adopters do not receive", and then offered, three lines
above, an option that does exactly that — it did not remove the dangling
reference, it relocated it into the more widely installed of the two surfaces.
Option (b) had the same shape one step smaller: it re-phrased only the
`effort.md` insertion and left the one in the shipped `PROTOCOL.md` dangling.

This is an instruction document for a future closeout. A wrong instruction here
is the pack's own dominant defect class — a surface that reads as a guarantee
and is not one — so it was cured rather than declared.

**Cure (in the derivator, never by hand in the live tree):** a fifth anchored
replacement in `_derive_payload_v2.py` (`closeout/npm-reach`, expected count 1,
anchored on the existing `CLO_TAIL_NEW` constant so no replaced byte is
retyped). Section 5 now states the measured reach of BOTH surfaces, quotes the
refuted option and says why it was wrong, and offers **two** options: ship the
classifier through all three install surfaces, or phrase both references as
explicitly framework-internal.

**Verification after the cure:** oracle `check-classifier-cases.py` rc 0
CONSISTENT; the shipped rc-contract test 13 passed; the staged set unchanged at
six paths; zero personal-path/handle hits in the rewritten file.
