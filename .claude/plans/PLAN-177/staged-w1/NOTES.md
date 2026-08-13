# W1 staged pack (v2) — NOTES

Base: canonical `ba19bcc` (W0 already landed). All work in throwaway clones
under this directory; the canonical repo was never written to.

The canonical HEAD advanced to `7c09544` (docs-only, the W2 runbook) while this
pack was being built. Re-checked rather than assumed: all nine patches
`git apply --check` clean at `7c09544`, individually and combined, on a fresh
clone. No rebase needed.

This is the **v2** of the pack. It starts from the v1/v4 drafts under
`../w1-staged/` and `../w1v4/`, rebases them onto `ba19bcc`, **re-runs every
verification from scratch** (nothing here is inherited as a claim), and closes
the gaps the mandate named. Deltas are listed in §7.

## 1. Patches — 9, one per surface

| patch | surface | canonicality | change |
|---|---|---|---|
| `w1-generator.patch` | `scripts/_framework_manifest_set.sh` | **CANONICAL** | +6 functions (the ONE text) |
| `w1-install.patch` | `scripts/install.sh` | **CANONICAL** | 2 delegations + new delivery |
| `w1-upgrade.patch` | `scripts/upgrade.sh` | **CANONICAL** | 2 new delivery blocks |
| `w1-install-npm.patch` | `scripts/install-npm.sh` | **CANONICAL** | comment block `:176-190` |
| `w1-tournament.patch` | `.github/workflows/tournament.yml` | **CANONICAL** | T-1 `working-directory` |
| `w1-smoke-install-wiring.patch` | `.github/workflows/smoke-install.yml` | **CANONICAL** | 2 path filters + step + timeout 25→32 |
| `w1-parity-allowlist.patch` | `scripts/tests/_parity_classify.py` | free | −10 (the allowlist tuple) |
| `w1-nightmode-e2e.patch` | `scripts/tests/test-night-mode-ignore-effect.sh` | free | new file, **mode 100755** |
| `w1-tournament-assert.patch` | `.claude/scripts/tests/test_tournament_projection_workdir.py` | free | new file |

All nine `git apply --check` clean **individually and as one invocation**
against a fresh clone of the canonical repo; applied there, the resulting
`git diff` is byte-identical to the working clone's (`cmp` — empty).
Any order applies (nine hunks in nine files). They must land in ONE commit —
§4.

**`w1-claude-gitignore.patch` was NOT emitted, deliberately.** The mandate asks
for it "se separável" and it is not: the `.claude/.gitignore` body lives in the
same generator file as the other two blocks, and its delivery is a hunk inside
each of `install.sh` / `upgrade.sh`. Splitting it out means hand-editing three
`.patch` files, which this repo has a rule against for exactly this reason. It
is delivered by `w1-generator` + `w1-install` + `w1-upgrade`.

## 2. Sentinel scope — measured, not recalled

The commit touches **nine** paths. The sentinel `## Scope` must enumerate all
of them, including the three free ones, or `touched − scope = ∅` fails:

    scripts/_framework_manifest_set.sh                              CANONICAL
    scripts/install.sh                                              CANONICAL
    scripts/upgrade.sh                                              CANONICAL
    scripts/install-npm.sh                                          CANONICAL
    .github/workflows/tournament.yml                                CANONICAL
    .github/workflows/smoke-install.yml                             CANONICAL
    scripts/tests/_parity_classify.py                               free
    scripts/tests/test-night-mode-ignore-effect.sh                  free (mode 100755)
    .claude/scripts/tests/test_tournament_projection_workdir.py     free

Produced by calling `check_canonical_edit._is_canonical(path, Path(repo))` on
each path, with a positive control (`.claude/team.md` → CANONICAL) and a
negative one (`README.md` → free). Passing `repo_root` as a **`str`** makes
every path come back "free" — a silent wrong answer that would yield a sentinel
scope missing every canonical file. Worth repeating if anyone re-derives this.

**Preserve the exec bit** on `test-night-mode-ignore-effect.sh`: the patch
carries `new file mode 100755`, but a `cp`-based land drops it (the verified
S286 failure mode).

## 3. CF-9 — the generator owns every .gitignore surface

`_framework_manifest_set.sh` gains six functions after the
`_render_protocol_pointer` family:

* `_mcp_secrets_ignore_entry` / `_apply_mcp_secrets_ignore` — PLAN-019 P2-SEC-H
  block (`state/mcp_client_secrets/`), create-or-append.
* `_posture_state_ignore_entries` / `_apply_posture_state_ignores` — PLAN-165
  CX-3 block, append-only.
* `_claude_dir_gitignore_body` / `_apply_claude_dir_gitignore` — the new file.

Owning only the posture block would leave the mcp-secrets block as a second
unowned copy of the same kind of text on the same file — a ceremony granting
ownership of half a surface — and would leave the pre-v1.2.0 adopter, who never
got the secrets entry from an upgrade either.

House style followed exactly: no `local`, no `[[ ]]`, `_prefix_`-scoped
globals, POSIX test (the file declares itself bash-3.2-safe and contains zero
`local` and zero `[[`).

**Two byte-level idiosyncrasies are preserved deliberately**, and the generator
says so in a comment: (1) the posture header comment is emitted *inside* the
loop, once per appended entry; (2) the mcp CREATE branch writes its header with
**no** leading blank line while the APPEND branch writes one. Both are planted
as mutations in `BYTE-PROOF.md` §F and the harness goes red on each.

### `.claude/.gitignore` — the new delivered file

Body: provenance header + `/state/` + `/settings.local.json`, leading-slash
anchored so they bind to `.claude/` only.

* Delivered in **every** ceremony on **both** routes. It lives inside
  `.claude/`, so it does not violate the `--ceremony user` invariant — asserted
  by the e2e's scenario C, which runs the exact top-level check
  `smoke-install.yml:220-232` performs and finds only `.claude` and `.git`.
* **Create-if-missing, never rewritten.** `BYTE-PROOF.md` §D writes an adopter
  edit into it and re-runs the upgrade block: preserved byte-for-byte.
* **Not in the baseline manifest, by construction** — so no later upgrade can
  classify it as framework-owned and clobber it. Verified on a REAL install:
  `grep -c gitignore <target>/.claude/.install-manifest.sha256` → **0**, while
  the install-state journal carries all three ops
  (`ensure_mcp_secrets_dir`, `ensure_posture_state_ignores`,
  `ensure_claude_dir_gitignore`, one each).
* `uninstall.sh` only removes manifest-listed files, so it leaves this file
  alone. Verified: `uninstall.sh --dry-run` on that target →
  `grep -ci gitignore` = **0**, 513 removals, none of them a `.gitignore`.

### The two new test files do not reach the npm tarball

Both live under a `tests/` directory, and the npm packlist gate
(`validate.yml:1030-1069`) stages with `--exclude='**/tests/'` over the same
`for src in scripts templates .claude …` loop that would otherwise carry them.
So `scripts/tests/test-night-mode-ignore-effect.sh` and
`.claude/scripts/tests/test_tournament_projection_workdir.py` are excluded by
the existing rule — no packlist change needed, and none was made. Read from the
workflow, not assumed.

## 4. Atomicity (why ONE commit) — and why a human has to check it

The allowlist removal and the upgrade delivery are two halves of one change:

* allowlist removed **without** the upgrade cure ⇒ the gate goes FATAL
  (measured: `STATE-D-PROOF.md`).
* upgrade cure **without** the allowlist removal ⇒ the gate keeps allowlisting a
  defect that no longer exists.

Nothing enforces this. The `^\.gitignore$` tuple lives in `ACCEPTED`, not
`KNOWN_OPEN`, and only `KNOWN_OPEN` entries are MANDATORY-FIRE; an orphan
`ACCEPTED` entry is a WARNING. `git show --stat` before the push is the check.

## 5. Deliberate posture, stated so it is a decision and not a surprise

Idempotence is **per line** (`grep -Fxq`), not per block. An adopter who
deliberately deletes one entry gets it re-appended on the next install/upgrade,
with a fresh header comment. That is intentional — these entries keep secrets
and per-machine permission posture out of VCS, and the framework cannot
distinguish a deliberate deletion from an accident. `BYTE-PROOF.md` §E asserts
the re-append so a future change to this posture is a visible test failure
rather than silent drift. An adopter who really wants the path tracked should
use `.git/info/exclude` or a nested `.gitignore`. Release notes should say so.

The root `.gitignore` blocks also survive `uninstall.sh` (it removes only
manifest-listed files, and the adopter's `.gitignore` is not one). That was
already true of the mcp block before this change; it is not new, and it is the
safe direction.

## 6. Fail-loud on a missing generator

`install.sh` guards each call with `command -v … || { echo "    ERROR: …" >&2;
return 1; }` in the literal shape of `install.sh:1898`; under `set -e` that
aborts the install. `upgrade.sh` cannot `return` at top level, so it `exit 1`s.

That is install.sh's posture for this library, NOT the preserve-the-surface
posture of `_refresh_protocol_pointer`: nothing here overwrites an adopter
file, the operation is a pure append, so there is no surface a silent degrade
would be protecting. It does abort an upgrade at ~95% completion (before the
baseline-manifest rewrite) — worth an explicit Owner look. The alternative,
warn-and-continue, would reinstate silent non-delivery, which is the P1 class
itself.

## 7. What v2 changed relative to the v1/v4 drafts

1. **Rebased and re-verified at `ba19bcc`.** Every run in `PARITY-RUN.md`,
   `BYTE-PROOF.md` and `STATE-D-PROOF.md` is a fresh execution at this base;
   no result was carried over.
2. **`install-npm.sh`: a new half-false claim removed.** The v4 draft replaced
   the impossible consumer recipe with "a maintainer can re-verify a locally
   built artifact with `sha256sum -c SHA256SUMS.txt` from NPM_DIR". Measured:
   that also fails. `npm/*.tgz` is git-ignored, the manifest keeps one line per
   tarball NAME across versions, and a bulk check therefore exits **1** with
   `ceo-orchestration-1.0.0.tgz: FAILED open or read` (reproduced with the
   repo's own tracked manifest plus a freshly built tarball). The comment now
   says which of the two artifacts actually verifies — the per-tarball
   `<tarball>.sha256` sidecar, measured rc=0 — and why the cumulative manifest
   does not. Curing a false promise with a slightly less false promise is the
   class this P1 is about.
   The forbidden literal `sha256sum -c SHA256SUMS.txt` (blocked in
   `npm/INTEGRITY.md` by the landed
   `test_integrity_doc_makes_no_enforced_claim_for_the_tarball_checksum`)
   survives in the pack in exactly one place — the REMOVAL side of
   `w1-install-npm.patch` (`-#   sha256sum -c SHA256SUMS.txt`, one line, with a
   `-` sign). In the resulting tree it is gone: `grep -rn` over
   `scripts/ npm/ .github/ docs/` in the patched clone returns **0** hits.
3. **BYTE-PROOF §A/§B: new scenario `s9_adopter_edited_comment`** — the adopter
   kept the entries but rewrote the header comments the framework appended. The
   mandate named this case; `grep -Fxq` keys on the ENTRY, so nothing may be
   re-appended. Verified: comments preserved, zero framework headers
   re-introduced, entry counts 1/1/1.
4. **BYTE-PROOF §E2 (new): idempotence on the INSTALL route and across routes.**
   v1/v4 tested `upgrade` twice only. Now: install ×2 then upgrade, over four
   scenarios — no-op after the first, counts 1/1/1.
5. **Night-mode e2e: the root block is measured directly, BEFORE and AFTER.**
   `.claude/.gitignore` alone makes every scenario report "clean", and
   `git check-ignore` reports only the winning rule — so an upgrade whose root
   delivery silently did nothing would have passed the v4 test. Scenario A now
   asserts posture entries go `0 → 2` across the upgrade (and scaffold-errors if
   the pin ever stops reproducing the gap: `git show v1.2.0:scripts/install.sh
   | grep -c install_posture_state_ignores` = **0**, `install_mcp_secrets_dir`
   = 2, so the pin is still the right fixture). Scenario B asserts the mirror:
   still `0` under `--ceremony user`. Both assertions go red in state D.
   A `grep -c … || echo 0` in the first draft of that helper emitted `"0\n0"`
   and produced `integer expression expected`; the fixed helper carries the
   explanation.
6. **Product-level positive control for the tournament assert**: a separate
   clone with the TEST applied and `tournament.yml` at HEAD → `2 failed`,
   naming `['Emit step summary']`. v4 relied on the in-memory mutations only.

## 8. Riders the Owner needs before signing

* **`.claude/plans/PLAN-169/staged-w3/scripts/` still carries whole-file
  PRE-CURE copies of all three scripts this pack touches** (`install.sh`,
  `upgrade.sh`, `_framework_manifest_set.sh`). Per the S303 lesson, the W3 LAND
  applies staged files with a blind `cp`. Landing W3 after rc.4 without
  re-staging would **revert the entire P1-1 cure** — all three files, not just
  the two hashes named in rider R-2. Re-stage from post-cure disk before
  signing W3. (Rider R-2 was widened for this in `867560a`; this is the
  confirmation that the situation is unchanged at `ba19bcc`.)
* **`scripts/` at repo root is not shellchecked by CI** (`validate.yml:296-314`
  walks only `.claude/scripts` and `.claude/hooks`). Four of the six canonical
  files in this pack live there. Run by hand: 0 findings at `-S warning`.
* **The install-state journal gains a record** (`ensure_claude_dir_gitignore`).
  The suite that exercises that journal, `test_install_state_replay.sh`, was
  re-run to completion: rc=0, `PASS=34 FAIL=0`. No open sibling suite remains.
