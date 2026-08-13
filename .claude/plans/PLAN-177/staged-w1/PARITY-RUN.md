# PARITY-RUN — what ran, with which command, and what it returned

Everything below was executed on darwin arm64 on 2026-08-13 against clones of
the canonical repo at `ba19bcc`. Nothing here is inferred.

## 1. The gate AC-3 turns on

`scripts/tests/test-install-upgrade-parity-e2e.sh`, invoked exactly as
`smoke-install.yml:240-270` does: plain gate first, then `--positive-control`.
The order is load-bearing — a control that fires after an already-fatal plain
run proves nothing.

Fixture: `PIN=v1.2.0` (a LOCAL tag, resolved from the clone's own objects — the
script is network-free), `PROFILE=core`, modes `maintainer user`.

| # | tree | change set | command | rc |
|---|---|---|---|---|
| 1 | `repo` | full cure (9 patches, working clone) | `bash scripts/tests/test-install-upgrade-parity-e2e.sh` | **0** |
| 2 | `repo` | full cure | `… --positive-control` | **1** |
| 3 | `stateD` | allowlist removed, **upgrade delivery absent** | `bash …parity-e2e.sh` | **1** |
| 4 | `final` | the 9 EMITTED patches on a **clean clone** | `bash …parity-e2e.sh` | **0** |
| 5 | `final` | idem | `… --positive-control` | **1** |

Run 4 is the load-bearing one: `final/` is a fresh `git clone --local` with
exactly the nine emitted `.patch` files applied, and its `git diff` is
byte-identical to the working clone's (`cmp` of the two `git diff` outputs —
empty). Logs: `parity-plain.log`, `parity-control.log`, `parity-stateD.log`,
`parity-final.log`, `parity-final-control.log`, each with a `.rc` sibling.

### Runs 1 / 4 — PASS

    per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:0 user:0
    RESULT: PASS — install and upgrade converge on the same framework
            content in every ceremony mode tested (maintainer user).

Neither `.gitignore` nor `.claude/.gitignore` appears anywhere in the log: with
the cure both land in IDENTICAL, so the classifier has nothing to say about
them. Counts: `IDENTICAL 521` (maintainer) / `479` (user), every FATAL bucket 0.

### Runs 2 / 5 — positive control of the e2e itself

    PLANTED: dropped backup_and_replace ".claude/commands" from a COPY of
    per-mode verdicts: maintainer:1 user:1
    positive control: FIRED in every mode (rc=1 each) — the gate is alive.

rc is exactly 1 (rc 0/2 = the gate went blind, rc 9 = the plant stopped biting;
`smoke-install.yml` fails on all three).

### Run 3 — state D

Its own document: `STATE-D-PROOF.md`. Two FATAL classes, both named there.

## 2. Efficacy — the e2e that byte-parity cannot replace

`scripts/tests/test-night-mode-ignore-effect.sh` (new). Byte-parity proves the
two routes converge; it cannot prove the delivered bytes WORK — an ineffective
ignore is equally ineffective on both routes, so it is byte-identical and every
parity gate stays green.

    cd final && bash scripts/tests/test-night-mode-ignore-effect.sh   # rc = 0
    wall: 2m05s / 2m10s over two runs (darwin arm64, 16 cores)

    --> [A] install @ v1.2.0 (maintainer) -> upgrade (working tree)
      [A] root .gitignore: posture entries 0 -> 2 across the upgrade — the P1-1 delivery
      [A] upgrade/maintainer: clean — git -uall sees no night-mode artifacts
      [A] upgrade/maintainer: rule -> .claude/.gitignore:15:/state/
      [A] upgrade/maintainer: control fired — without the ignores git reports both artifacts
    --> [B] install @ v1.2.0 (user) -> upgrade (working tree)
      [B] root .gitignore: still 0 posture entries — user ceremony skipped on BOTH routes
      [B] upgrade/user: clean …  control fired
    --> [C] install (working tree) --ceremony user
      [C] fresh/user: clean …  control fired

    RESULT: PASS

Three assertions per scenario, each with an inline control that cannot be
switched off. Its own positive control at the product level is state D
(`STATE-D-PROOF.md` §"the other half"): rc=1, with `?? .claude/state/
night-mode.json` and `?? .claude/settings.local.json` printed — the original
damage, reproduced.

**The `0 -> 2` line is a v2 addition and it matters.** `.claude/.gitignore`
alone makes every scenario report "clean", and `git check-ignore` reports only
the WINNING rule (which is the `.claude` one). Without measuring the root block
directly, an upgrade whose root delivery silently did nothing would have passed
this test. Verified by the state-D run, where that exact assertion is what goes
red first.

The 2m05s measurement is the basis for the `timeout-minutes: 25 → 32` bump in
`w1-smoke-install-wiring.patch`: 3 installs + 2 upgrades at the 2-3x runner
factor this workflow already sizes with.

## 3. Structural assert for T-1

    cd final && python3 -m pytest .claude/scripts/tests/test_tournament_projection_workdir.py -q
    8 passed in 0.17s

Positive control, product level — a separate clone with the TEST applied and
`tournament.yml` left at HEAD (i.e. T-1 absent):

    2 failed, 6 passed   (rc=1)
    FAILED … ::test_every_relative_step_declares_working_directory

with the diagnostic naming the step: `['Emit step summary']`. The gate would
have caught the original bug. (The second red is the control-of-control
assertion, which counts differently when only one `working-directory` exists in
the file at all — expected pre-patch, not a defect.) Log:
`tournament-control.log`.

## 4. Byte-parity of the generator

`BYTE-PROOF.md` — run twice, once against the working clone (`bp-out/`) and
once against `final/` (the emitted pack, `bp-final/`). The two reports differ
only in the scratch path echoed by `install_mcp_secrets_dir`. 18 A-rows
(9 scenarios × dry-run 0/1), 9 B-rows, both root blocks, `.claude/.gitignore`,
idempotence on both routes, and 5 planted mutations the harness must catch —
all detected.

## 5. Sibling suites re-run because these files moved

| suite | command | rc |
|---|---|---|
| ownership unit oracle | `bash scripts/tests/test-ownership-verdict-unit.sh` | **0** |
| protocol pointer render (INV-4 sibling) | `bash scripts/tests/test-protocol-pointer-render.sh` | **0** |
| upgrade exclusions | `bash scripts/tests/test-upgrade-exclusions.sh` | **0** |
| install-state replay (the journal this pack adds a record to) | `bash scripts/tests/test_install_state_replay.sh` | **0** — `PASS=34 FAIL=0` |
| parity classifier import + no orphan tuple | `python3 -c "…exec_module…"` | ACCEPTED-with-gitignore **0**, KNOWN_OPEN-with-gitignore **0**, total ACCEPTED 7 |

## 6. Static checks

* `bash -n`: `install.sh`, `upgrade.sh`, `_framework_manifest_set.sh`,
  `install-npm.sh`, `test-night-mode-ignore-effect.sh` — all clean.
* `shellcheck -S warning` on the same five: **0 findings**. Note the CI
  shellcheck step (`validate.yml:296-314`) walks only `.claude/scripts` and
  `.claude/hooks`, so `scripts/` at the repo root is NOT covered by CI — this
  was run by hand and has to be re-run by hand.
* Canonicality of every touched path measured by calling
  `check_canonical_edit._is_canonical(path, Path(repo))` directly, with a
  positive control (`.claude/team.md` → CANONICAL) and a negative one
  (`README.md` → free). Result table in `NOTES.md` §2.

## What did NOT run, and why

* **CI itself.** These are local darwin runs. The e2e scripts are the same ones
  CI invokes with the same arguments, but the runner is Ubuntu; a
  platform-specific divergence would not be visible here. First real signal is
  the rc.4 PR. Two known asymmetries were handled in advance: the night-mode
  e2e neutralises `GIT_CONFIG_GLOBAL`/`SYSTEM` + `core.excludesFile` (this
  maintainer's `~/.config/git/ignore` contains
  `**/.claude/settings.local.json`, which would make the control half-blind
  locally and full-sighted on a clean runner), and the `sha256sum` /
  `shasum -a 256` fallback in `install-npm.sh` is exercised on both.
* **The full pytest suite.** Out of scope for this pack and unaffected by these
  paths; the W0 surfaces are a different agent's assignment.
* **`--positive-control` on run 3.** State D is already red; a control on top
  of a red run measures nothing.
