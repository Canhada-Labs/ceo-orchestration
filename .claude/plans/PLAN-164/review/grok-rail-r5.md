I'll verify the r4 HIGH closure against committed bytes at HEAD `10e0bd1`: prior verdicts, the pre-ceremony validator commit, rail-pack/ceremony surfaces, and sentinel scope.Confirming HEAD `10e0bd1`. Next I'll inspect commit `8f21b25`, the rail-pack manifest, ceremony git-adds, and the sentinel Scope.Shell PATH looks broken; fixing it and continuing structural verification.Structural checks all hold. Writing the r5 review artifact and finalizing the verdict.VERDICT: APPROVE

## Closure of codex-rail-r4 HIGH

| Probe | Result | Evidence |
|---|---|---|
| **(a)** `git show 8f21b25` carries the validator | **PASS** | `8f21b25` is on `origin/main`, parent of HEAD `10e0bd1`. Diff is only `.claude/plans/PLAN-163/land-plan163-pin.sh` (suffix-newest + `_is_reverted` fail-closed + retirement guard) and `land-plan163-pack.sh` (ADR gates 182/184). HEAD pin blob == `8f21b25` pin (`f8a3e08a…`); parent blob `79cfc3cf…` is the old file-trusting resolver (reads `sha`/`ts` from the anchor file with no ceremony/revert checks). |
| **(b)** Ceremony revert cannot restore old resolver | **PASS** | Rail-pack MANIFEST / twin: **6 rows**, no `land-plan163*`. Ceremony `git add` is dests-from-manifest + `PLAN_DIR` (PLAN-164 only) + optional PLAN-164 plan md; explicit non-add of pin tooling (`land-plan164-rail.sh:468-470`). Index ⊆ scope+materials **BLOCKs** both PLAN-163 scripts. `git revert <ceremony-sha>` therefore cannot touch `land-plan163-pin.sh`. |
| **(c)** Sentinel Scope == 6-row dest-set | **PASS** | `architect/round-1/approved.body.md` Scope (6 paths) is set-equal to manifest dests. Body declares the pre-ceremony split and the r4 HIGH rationale (`:76-95`). Twin `inputs-rail.sha256` is **byte-identical** to staged `MANIFEST.sha256`; all 6 digests match staged bytes. |
| **(d)** No new structural defect from the split | **PASS** | Core-surface assert still requires hook + kernel + template + invariant test (`land-plan164-rail.sh:285-294`). Live tree runs the new resolver: `--gate-v2` resolves current anchor `a4371c7` (`[SENT-PLAN163-PIN]`, not reverted) and recomputes `ts` from git. GATE-V2 **FAIL (not yet satisfied)** is the expected pre-rail-land liveness result (post-anchor F), not a resolver break. `bash -n` clean on pin/pack/rail. Preflight path reported **scope matches (6 files)** + core surfaces present before env-local GPG/signer checks. |

## Dest-set / Scope (exact)

```
.claude/adr/ADR-110-AMEND-1-rail-timeout-contract.md
.claude/hooks/check_pair_rail.py
.claude/hooks/tests/test_pair_rail_timeout_invariant.py
.claude/settings.json
scripts/doctor.sh
templates/settings/settings.base.json
```

## Residual (non-blocking)

| ID | Severity | Note |
|---|---|---|
| **R5-L1** | **LOW** | Stale prose still claims the pack “also stages `land-plan163-pack.sh`” / “8 scope paths” in `land-plan164-rail.sh` header (`:15-16`), index comment (`:478`), and ceremony commit-message template (`:507-508`). Mechanical paths (manifest, Scope, git-add, index filter) are correct; the same commit message later states the pre-ceremony land (`:511-515`). Docs drift only — does **not** re-open the r4 HIGH. |

## Net

Codex r4 HIGH is **CLOSED STRUCTURALLY** at HEAD `10e0bd1`: the fail-closed validator lives in pre-ceremony `8f21b25` (already on main); the rail ceremony is a 6-file timeout pack only; sentinel/manifest/git-add agree; live `--gate-v2` still resolves `a4371c7`. No new HIGH/MED. Residual LOW docs only.
