I'll verify the N1/N2 closures in the current tree and re-probe the mid-rollback, recovery, and false-positive cases against the staged scripts.Reading the rollback instructions and `_is_reverted` / `resolve_anchor` implementation next.Probing mid-rollback fail-closed, recovery anchoring, and false-positive / `set -e` edge cases in an isolated git harness.Checking whether the ceremony rewrites the anchor file, and scanning for other N1/N2 edge cases.One more check: `git revert` bodies end with a period — confirming the grep still matches, and scanning `_is_reverted` call sites.VERDICT: APPROVE

## Closure table (codex r3 → current bytes)

| ID | Source | Severity | Status | Evidence |
|---|---|---|---|---|
| **HIGH-N1** post-push rollback leaves CI red | Codex r3 | HIGH | **CLOSED** | `land-plan164-rail.sh:589-598` prints **BOTH** commits in reverse order: (1) `git revert <closeout-sha>` (docs → 181), (2) `git revert $CEREMONY_SHA`, (3) push + `gh run watch` until Validate **GREEN**, (4) `--rerun-after-revert`. Explains why ceremony-only revert yields 181 vs closeout-182 permanent red and blocks the recovery rerun at origin/Validate gates. Also states `--gate-v2` fails CLOSED while reverted. |
| **MED-N2** reverted ceremony still anchors | Codex r3 | MED | **CLOSED** | Staged `land-plan163-pin.sh` `resolve_anchor()` (`:125-155`): `_is_reverted` greps body `This reverts commit <full-sha>`; file pointer at a reverted ceremony → **die** with recovery instructions; `_newest_ceremony_sha` skips reverted subjects and picks newest non-reverted. |
| Manifests / twins | packaging | — | **OK** | Rail MANIFEST **8/8** digests match staged paths; `inputs-rail.sha256` **byte-identical**. Header notes r3 remanifest (`fail-closed sob revert`). `bash -n` clean on pin + land. |

## Re-probes (isolated clean git history; logic byte-mirrored from staged pin)

| Case | Result |
|---|---|
| **(a)** Mid-rollback: c1 ceremony + closeout + anchor→c1, then `git revert` **ceremony only** | **DIE** — `anchor ceremony … has been REVERTED` (fail-closed). |
| **(a2)** Same window, anchor file removed | **DIE** — `no anchor` (fallback finds no non-reverted ceremony). |
| **(b1)** Recovery: dual revert + new c2 ceremony; file→c2 | **PASS** — anchors c2. |
| **(b2)** Same, file absent | **PASS** — fallback selects c2 (not c1). |
| **(b3)** Recovery done but file still→c1 | **DIE** — stale pointer stays fail-closed until re-anchor rewrite. |
| **(c1)** Unrelated `git revert` of a non-ceremony commit | **No FP** — c2 still anchors. |
| **(c)** `set -e` + empty `_is_reverted` match | **OK** — `|| true` in command-sub; call sites only in `if` / `!` conditions (`:135`, `:153`). |
| Real `git revert --no-edit` body ends with `.<nl>` | **Matched** (substring grep of full 40-char sha). |
| Default revert subject `Revert "…[SENT-PLAN164-RAIL]"` | **Not** a ceremony subject (ends with `"`). |
| Closeout subject | **Rejected** as non-ceremony. |

## New findings

| ID | Severity | Finding |
|---|---|---|
| **R4-L1** | **LOW** (residual, non-blocking) | `_is_reverted` is body-text grep, not `git rev-list --ancestry-path` / first-parent edge detection. A **docs** commit whose body quotes the exact string `This reverts commit <full-40-sha>` will mark that ceremony “reverted” (fail-closed over-restrictive). Unrelated real reverts of *other* commits do **not** poison the ceremony (probe c1). Operator recovery docs should avoid pasting that full template with a live ceremony SHA; true `git revert` remains the intended true-positive. Not a laundering hole. |

## Net

Both codex r3 findings are closed in current staged/land bytes with mechanical proof (manifest 8/8 + twin identity, `bash -n`, mid-rollback die, recovery file+fallback, set -e / unrelated-revert probes). No new HIGH/MED defect. Residual LOW is fail-closed prose sensitivity only and does not block W1 land / W2.
