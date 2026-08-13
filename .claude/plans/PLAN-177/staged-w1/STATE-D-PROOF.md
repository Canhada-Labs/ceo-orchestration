# STATE-D-PROOF — the two halves of CF-2, exercised

AC-3 asks for state D "exercitado uma vez em clone scratch com transcript
FATAL anexado". This is that run, plus the reason it is not optional.

## Why a human has to see this red

The `.gitignore` tuple this pack deletes lives in `ACCEPTED`, **not** in
`KNOWN_OPEN`. Only `KNOWN_OPEN` entries are MANDATORY-FIRE (an entry that
matches nothing is fatal — "the bug you named is closed, delete the entry").
An orphan `ACCEPTED` entry is a WARNING, printed and survivable. So nothing in
CI would have complained if the allowlist removal had landed *without* the
upgrade delivery, or the delivery *without* the removal. The atomicity of CF-2
is enforced by this proof and by landing both in one commit — not by a gate.

## The state

Fresh `git clone --local` of the canonical repo at `ba19bcc`, then exactly
three of the nine patches applied:

    w1-generator.patch          the shared generator
    w1-install.patch            install.sh delegates + delivers .claude/.gitignore
    w1-parity-allowlist.patch   the ^\.gitignore$ tuple REMOVED

`scripts/upgrade.sh` deliberately left at HEAD — `grep -c PLAN-177
scripts/upgrade.sh` returns 0. That is "correct the text, skip the mechanism":
the shape this change would have if someone declared it done after the
allowlist edit.

Command (the CI one, no flags):

    bash scripts/tests/test-install-upgrade-parity-e2e.sh     # rc = 1

## Transcript — mode=maintainer

    counts (UNDECLARED residue — declared paths are broken out below):
      IDENTICAL                    519
      PERSONALIZED                  31
      STALE                          0   <-- FATAL if non-zero
      MISSING_IN_B                   1   <-- FATAL if non-zero
      UNCLASSIFIED                   1   <-- FATAL if non-zero
      ONLY_IN_B                    390
      ONLY_IN_B_OUTSIDE_CLAUDE       0   <-- FATAL if non-zero
      MODE_DIFF                      0   <-- FATAL if non-zero

    FATAL [MISSING_IN_B] — install delivered these; the upgrade never did —
    an upgraded adopter simply does not have them
      - .claude/.gitignore

    FATAL [UNCLASSIFIED] — diverges and matches NEITHER source generation —
    if this is a generated or adopter-owned path, DECLARE it in ACCEPTED with
    its authority; do not widen a pattern to make it disappear
      - .gitignore

    verdict(mode=maintainer): FAIL

## Transcript — mode=user

    MISSING_IN_B                   1   <-- FATAL if non-zero
    UNCLASSIFIED                   0   <-- FATAL if non-zero

    FATAL [MISSING_IN_B] — install delivered these; the upgrade never did
      - .claude/.gitignore

    verdict(mode=user): FAIL

    per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:1 user:1
    RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above.

`user` mode shows only the `.claude/.gitignore` half, and that is the point of
the CF-9 widening: the root blocks are skipped in `user` ceremony on **both**
routes, so a root-only cure leaves that population invisible to this gate
forever. The new file is the first thing the gate can see there.

## Side by side with the full cure

| count (mode=maintainer) | state D | full cure |
|---|---|---|
| IDENTICAL | 519 | **521** |
| MISSING_IN_B (FATAL if ≠0) | **1** (`.claude/.gitignore`) | **0** |
| UNCLASSIFIED (FATAL if ≠0) | **1** (`.gitignore`) | **0** |

| count (mode=user) | state D | full cure |
|---|---|---|
| IDENTICAL | 478 | **479** |
| MISSING_IN_B (FATAL if ≠0) | **1** | **0** |

Exactly two paths moved from FATAL to IDENTICAL in `maintainer` and one in
`user`, and they are the paths the P1 names. That is what makes the green in
`PARITY-RUN.md` a measurement rather than a claim.

## The other half of state D — efficacy, not parity

The same tree also carries the new efficacy e2e (`w1-nightmode-e2e.patch`
applied on top), and it reproduces the ORIGINAL DAMAGE verbatim:

    --> [A] install @ v1.2.0 (maintainer) -> upgrade (working tree)
      FAIL: [A] the upgrade did NOT deliver the root posture block
            (entries: 0 -> 0, expected 2)
      FAIL: [A] upgrade/maintainer: night-mode artifacts are VISIBLE to git:
            ?? .claude/settings.local.json
            ?? .claude/state/night-mode.json

    --> [B] install @ v1.2.0 (user) -> upgrade (working tree)
      FAIL: [B] upgrade/user: night-mode artifacts are VISIBLE to git:
            ?? .claude/settings.local.json
            ?? .claude/state/night-mode.json

    --> [C] install (working tree) --ceremony user
      [C] fresh/user: clean — git -uall sees no night-mode artifacts

    RESULT: FAIL (exit 1)

Scenario C is GREEN in state D because `install.sh` there already carries the
cure — so the transcript also shows *which half fixes which population*: the
fresh user install is repaired by `install.sh` alone, while both upgrade routes
stay broken until `upgrade.sh` delivers. Full log: `nightmode-stateD.log`.

## Logs

`parity-stateD.log` (+ `.rc` = 1), `nightmode-stateD.log`. The tree is
`stateD/` beside them.
