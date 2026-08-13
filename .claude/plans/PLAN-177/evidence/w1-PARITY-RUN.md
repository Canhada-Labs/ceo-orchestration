# PARITY-RUN — `scripts/tests/test-install-upgrade-parity-e2e.sh`

The gate that AC-3 turns on. It really ran; nothing here is inferred.

Invocation is the CI one (`smoke-install.yml:240-270`): plain gate first, then
`--positive-control`, in that order — the header is explicit that the control
proves nothing if the un-planted run was already fatal.

Fixture: `PIN=v1.2.0`, `PROFILE=core`, modes `maintainer user`. The pin is a
**local tag**, resolved from the clone's own git objects — the script is
network-free, so nothing was skipped for lack of connectivity. `git tag -l
v1.2.0` confirmed present in every clone before running.

## Runs

| # | tree | change set | rc | meaning |
|---|---|---|---|---|
| 1 | `clone` | full cure (6 patches) | **0** | PASS, both modes |
| 2 | `clone` | full cure, `--positive-control` | **1** | gate is alive |
| 3 | `clone-verify` | allowlist removed, **upgrade cure absent** | **1** | the green in #1 is not vacuous |
| 4 | `clone-final` | the six emitted patches on a **clean clone** | **0** | PASS, both modes |
| 5 | `clone-final` | `--positive-control` | **1** | control on the emitted pack |

Run #4 is the load-bearing one: `clone-final` is a fresh clone of the canonical
repo with exactly the six `.patch` files applied — not the working clone. Its
`git diff` is byte-identical to the working clone's.

## Run #1 / #4 — PASS

    per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:0 user:0
    RESULT: PASS — install and upgrade converge on the same framework
            content in every ceremony mode tested (maintainer user).

`.gitignore` does not appear anywhere in the log: with the cure it lands in
IDENTICAL, so the classifier has nothing to report about it.

## Run #2 — positive control of the e2e itself

    PLANTED: dropped backup_and_replace ".claude/commands" from a COPY of
    per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:1 user:1
    positive control: FIRED in every mode (rc=1 each) — the gate is alive.

rc is exactly 1, and the log carries the `PLANTED` / per-mode-verdict evidence
that `smoke-install.yml` demands as its second, anti-vacuity factor.

## Run #3 — the control that matters for THIS cure

Allowlist removed, `install.sh` + generator patched, **`upgrade.sh` untouched**
— i.e. the "correct the text, skip the mechanism" version of this change:

    FATAL [UNCLASSIFIED] — diverges and matches NEITHER source generation …
        - .gitignore

    per-mode verdicts: maintainer:1 user:0
    RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above.

Side by side, `mode=maintainer`, everything else equal:

| count | run #3 (no upgrade cure) | run #4 (full cure) |
|---|---|---|
| IDENTICAL | 519 | **520** |
| UNCLASSIFIED (FATAL if ≠0) | **1** (`.gitignore`) | **0** |

Exactly one path moved from FATAL to IDENTICAL, and it is the one the P1 names.
That is what makes runs #1/#4 a measurement rather than a claim.

`user:0` in run #3 is also the AC-3 ceremony assertion, from the opposite
direction: with install delivering and upgrade not, `user` mode still shows no
divergence — because **neither** route delivers under `--ceremony user`. The
gate stays clean in that mode whether or not the cure is present, which is the
correct behaviour and is why `BYTE-PROOF.md` asserts the ceremony gate directly
as well.

## Run #5 — positive control on the emitted pack

Run against `clone-final` after run #4 came back green (CI ordering).
`FINAL_CONTROL_RC=1`, with both anti-vacuity markers present:

    PLANTED: dropped backup_and_replace ".claude/commands" from a COPY of
    positive control: FIRED in every mode (rc=1 each) — the gate is alive.

So on the exact emitted pack, the gate passes clean and still goes red on a
planted divergence.

## What did NOT run, and why

* **CI itself.** These are local runs on darwin. The e2e is the same script CI
  invokes with the same arguments, but the runner is Ubuntu; a platform-specific
  divergence would not be visible here. First real signal is the rc.4 PR.
* **`scripts/` shellcheck in CI.** `validate.yml:296-314` walks only
  `.claude/scripts` and `.claude/hooks`. `scripts/install.sh`, `upgrade.sh`,
  `_framework_manifest_set.sh` and `install-npm.sh` are outside that find, so CI
  will not shellcheck them. Run by hand instead: 0 findings at `-S warning` and
  no delta at `-S style`, before and after.
* **The wider test suite.** Out of scope for this pack; the W0 surfaces (P1-2 /
  P1-3 / P1-4 tests) are a different agent's assignment and are not in these
  patches.

## Logs

`parity-plain.log`, `parity-control.log`, `parity-nocure.log`,
`parity-final.log`, `parity-final-control.log` (+ matching `.rc` files) in this
directory.
