# W1 staged pack — NOTES

Base: `3842d4f` (canonical HEAD at build time — confirmed unchanged before and
after). All work done in throwaway clones under this directory; the canonical
repo was never written to.

## Patches (one per surface — cerimônia precisa de granularidade)

| patch | surface | +/- | sha256 |
|---|---|---|---|
| `w1-generator.patch` | `scripts/_framework_manifest_set.sh` | +56 | `be1e6fce…` |
| `w1-install.patch` | `scripts/install.sh` | +19/−14 | `b3afa833…` |
| `w1-upgrade.patch` | `scripts/upgrade.sh` | +38 | `966222ee…` |
| `w1-parity-allowlist.patch` | `scripts/tests/_parity_classify.py` | −10 | `87eb795e…` |
| `w1-install-npm-comment.patch` | `scripts/install-npm.sh` | +9/−3 | `1d7ba944…` |
| `w1-tournament.patch` | `.github/workflows/tournament.yml` | +6 | `1644387f…` |

`git apply --check` passes individually AND as one combined invocation against
a **fresh clone of the canonical repo**; applying all six to that clean clone
yields a diff byte-identical to the working clone's (`diff` of the two `git
diff` outputs is empty). Recompute the shas after any edit — do not trust the
table.

**Ordering:** all six are independent hunks in six different files; any order
applies. They must land in ONE commit — see "Atomicity" below.

## What each patch does

### 1. `w1-generator.patch` — the ONE text
Appends two functions at the end of `_framework_manifest_set.sh`, immediately
after the `_render_protocol_pointer` family (the plan says "~:646, perto de
`_render_protocol_pointer`"; end-of-file is line 721+, directly after that
family, and keeps the pointer block contiguous):

* `_posture_state_ignore_entries` — the entry list, one line, space-separated.
  Both callers word-split it AND print it verbatim, so the single-line shape is
  part of the contract.
* `_apply_posture_state_ignores GITIGNORE` — the per-entry `grep -Fxq` check,
  the append of the missing ones, and the progress lines.

House style of the file is followed: no `local`, no `[[ ]]`, `_psi_`-prefixed
globals, POSIX test — matching `_render_protocol_pointer_degraded` /
`_protocol_pointer_is_degraded` (the file declares itself bash-3.2-safe and
uses zero `local` / zero `[[`).

A comment block in the generator states the byte-compatibility constraint
explicitly: **the header comment is emitted per APPENDED entry, inside the
loop.** That is the shipped install.sh behaviour, and hoisting it is the exact
"tidy-up" that would break parity. The positive control in `BYTE-PROOF.md`
plants that mutation and demands the harness go red.

### 2. `w1-install.patch` — delegate, keep bytes
`install_posture_state_ignores` keeps its shape (dry-run branch, `==>` header,
`_state_record_op`), and swaps the hardcoded entry string + inline loop for the
generator. Two `command -v` fail-loud guards precede everything, each in the
literal shape of `install.sh:1898` (`… || { echo "    ERROR: …" >&2; return 1; }`),
one per function so the diagnostic names which one is missing. Under `set -e`
a `return 1` from this function aborts the install — the same posture
`install_protocol_pointer` already has for the same library.

The caller gate is untouched: `if [[ "$CEREMONY" != "user" ]]; then
install_posture_state_ignores; fi` (now at :1865, was :1860 — see "Stale line
numbers" below).

### 3. `w1-upgrade.patch` — the delivery that never existed
Inserted between `_refresh_framework_marker` and the PLAN-161 U3 purge scan, as
specified. Structure: `==>` header, ceremony gate, two `command -v` guards,
dry-run branch, `_up_record_op`, generator call.

Two deliberate deviations from the task text, both documented here:

* **Gate shape.** The task wrote `[[ "$CEREMONY_EFFECTIVE" != "user" ]]`; the
  patch uses `if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then <SKIP message>;
  else …`. That is the *literal* mirror of `:3084` the task also asked for, and
  it prints a SKIP line matching the surrounding sections' style. Same gate.
* **Fail-loud at top level.** `return 1` is illegal outside a function, so the
  guards `exit 1`. This is the install.sh posture for this library (a missing
  shared generator is a broken checkout), NOT the preserve-the-surface posture
  of `_refresh_protocol_pointer` — nothing here overwrites an adopter file, the
  operation is a pure append, so there is no surface to preserve by degrading.
  Worth an explicit Owner look, since it aborts an upgrade at ~95% completion
  (before the baseline-manifest rewrite). The alternative — warn and continue —
  would reinstate silent non-delivery, which is the P1 class itself.

Journals the same op name install does (`ensure_posture_state_ignores`) with
the same detail string; `BYTE-PROOF.md` compares the two journals with `cmp`.

### 4. `w1-parity-allowlist.patch` — the entry must die with the bug
Removes the whole `^\.gitignore$` tuple from `ACCEPTED`. Verified after removal:
zero `gitignore` entries in `ACCEPTED` **and** zero in `KNOWN_OPEN` (a leftover
there would be MANDATORY-FIRE and turn the gate fatal for the opposite reason).

### 5. `w1-install-npm-comment.patch` — the false comment
The old text claimed "CI verification (npm-publish.yml) computes the checksum of
the tarball it publishes and appends to the release notes." **Verified false
first-hand, not taken from the plan:** `grep -ni 'sha256|checksum|shasum|npm
pack' .github/workflows/npm-publish.yml` returns only the `#
CEO-INSTALL-SHA256:` trailer machinery over the install.sh *body* (:336-366) and
`npm pack --dry-run` (:378, materialises nothing). `npm/package.json` `files` is
`['bin/','scripts/','templates/','.claude/','SPEC/','VERSION','LICENSE',
'README.md','PROTOCOL.md']` — `SHA256SUMS.txt` is not in it. The replacement
says what actually happens, names the trailer sha256 so a future reader who
greps `sha256sum` in that workflow is not confused into thinking the comment is
wrong again, and defers automation to the v1.4.0 train.

### 6. `w1-tournament.patch` — T-1 verbatim
`~/canhada-labs/s303-night-artifacts/triagem-1-tournament.patch` applied
unmodified (`git apply --check` clean at HEAD); re-emitted from the clone so the
pack is self-contained. Adds `working-directory: .claude/scripts` to the summary
step.

## Atomicity (why one commit)

The parity allowlist and the upgrade delivery are two halves of one change:

* allowlist removed **without** the upgrade cure ⇒ the gate goes FATAL
  (`UNCLASSIFIED — .gitignore`, rc=1). Measured, see `PARITY-RUN.md`.
* upgrade cure **without** the allowlist removal ⇒ the gate keeps allowlisting
  a defect that no longer exists; the entry is dead and CI stays incapable of
  failing on the class.

## Stale line numbers — caught in-flight

The cure shifts `install.sh`'s ceremony gate from `:1860` to `:1865`. The first
draft of the upgrade.sh comment and its SKIP message both cited `install.sh:1860`
— stale the moment the sibling patch applies (the S302e "cura no corpo ≠ cura
nas REFERÊNCIAS" class, three instances in one rail). Both now name the *guard
expression* instead of a line number. `PLAN-177` itself still cites `:1830-1857`
and `:1860`; those are pre-cure coordinates in a plan document and stay correct
as a description of the bug.

## ⚠️ Out-of-scope finding the Owner needs before landing W3/PLAN-169

`.claude/plans/PLAN-169/staged-w3/scripts/` contains **whole-file copies** of
all three surfaces this pack touches:

    .claude/plans/PLAN-169/staged-w3/scripts/install.sh                (pre-cure)
    .claude/plans/PLAN-169/staged-w3/scripts/upgrade.sh                (pre-cure)
    .claude/plans/PLAN-169/staged-w3/scripts/_framework_manifest_set.sh (pre-cure)

`staged-w3/scripts/install.sh:1841` still carries the OLD
`install_posture_state_ignores` with the inline entry string and loop. Per the
S303 lesson recorded in memory, the W3 LAND applies staged files with a **blind
`cp`**. Landing W3 after rc.4 without re-staging would therefore **revert the
entire P1-1 cure** — all three files, not just the two hashes named in the
plan's rider R-2 (`gate-scripts-manifest.txt`). R-2 as written understates the
blast radius. Re-stage those three from post-cure disk before signing W3.

## Verification summary

* `bash -n`: install.sh, upgrade.sh, _framework_manifest_set.sh, install-npm.sh — clean.
* `python3 ast.parse` on `_parity_classify.py` + import + assertion that the
  `.gitignore` tuple is gone from both `ACCEPTED` and `KNOWN_OPEN`.
* `shellcheck -S warning`: 0 findings on all four scripts, **before and after**
  (also 0 delta at `-S style`: 1/10/9/0 findings identical on both sides). Note
  the CI shellcheck step (`validate.yml:296-314`) only walks
  `.claude/scripts` + `.claude/hooks`, so `scripts/` at repo root is NOT covered
  by CI — this was run by hand.
* `BYTE-PROOF.md` — 16 scenario/dry-run cells, install-vs-upgrade parity,
  ceremony gate, idempotence, and two planted mutations the harness must catch.
* `PARITY-RUN.md` — the e2e, its own positive control, and a third run that
  proves the green is not vacuous.
