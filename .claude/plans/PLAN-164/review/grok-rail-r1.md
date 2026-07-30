I'll start with the W1 delta bundle and the plan/context docs, then verify the staged rail-pack and main-pack bytes against the checklist.Next I'll verify the staged files and ceremony artifacts against the checklist items.Verifying staged bytes against live baselines and the four main-pack delta files.Inspecting pin-script structure, settings surgical diffs, and the upgrade migration in detail.Checking one more potential issue: whether the pack closeout ADR arithmetic and the invariant’s “any unilateral flip” claim hold under mutation.VERDICT: REJECT

## Findings

1. **HIGH** — Frozen PLAN-163 main-pack is not on “final bytes”: the 4-file delta is on disk, but `MANIFEST.sha256` / tracked twin still pin R6 digests.  
   **Evidence:** `shasum -a 256 -c` against `.claude/plans/PLAN-163/staged/main-pack/MANIFEST.sha256` fails on exactly:
   - `.claude/settings.json` (disk `4c82e41b…` vs pinned `df2f7748…`)
   - `templates/settings/settings.base.json` (disk `bf13c731…` vs pinned `cf72041e…`)
   - `scripts/upgrade.sh` (disk `3c69f804…` vs pinned `3b7abd73…`)
   - `.claude/scripts/tests/test_upgrade_settings_migration.py` (disk `7a253506…` vs pinned `fece6496…`)  
   `inputs-pack.sha256` matches the stale MANIFEST (not the staged content). This breaks consensus C3 / PLAN-164 W1 (“recompute MANIFEST → delta-review of **final** bytes → twin regenerates”). Ceremony would fail-closed (good), but this is not an approvable final pack state.

2. **MED** — Invariant test does **not** redden on every unilateral internal-default flip (docs overclaim).  
   **Evidence:** Live mutation of staged trio:  
   - base 120/150/statusMessage → **PASS**  
   - kernel `timeout` 150→100 → **FAIL** (equality + margin)  
   - internal `"120"`→`"130"` → **FAIL** (margin)  
   - internal `"120"`→`"50"` → **PASS** (`150 >= 50+30`)  
   Files: `test_pair_rail_timeout_invariant.py:146-166`, ADR claim at `ADR-110-AMEND-1-…md:336-337` / sentinel `approved.body.md:41` (“any unilateral flip … goes RED”). Absolute 120 is enforced by ceremony `assert_rail_values` (`land-plan164-rail.sh:163-169`), not by the invariant suite. Fix claim language or pin absolute floors if that was intended.

3. **LOW** — Adopter `upgrade.sh` migrates timeout only; does not add `statusMessage`.  
   **Evidence:** migration loop only writes `h["timeout"]` (`upgrade.sh` staged ~2035-2038). IFF-60 / custom preserve / template-derived cap / fail-open skip are otherwise correct (`OLD_PAIR_RAIL_CAP = 60`, `type(tpl_caps[0]) is int`, `new_cap is None` → NOTE + skip).

4. **LOW** — `resolve_anchor` uses `die` inside `$(…)` subshell.  
   **Evidence:** `land-plan163-pin.sh` staged ~153-188 vs call site ~`if ! pair="$(resolve_anchor)"`. Still fail-closed (subshell exit 1 → outer die), but specific FATAL text can be followed by the generic “no anchor” message. Prefer `return 1` + structured error, or invoke without subshell.

---

## Checklist (1)–(9)

| # | Result |
|---|--------|
| **(1) 30→120 hook-only** | **PASS.** Diff is exactly docstring + three literals (`"120"`, `120.0`×2). Clamp `>600` unchanged. No other logic. |
| **(2) kernel==template 150 + statusMessage** | **PASS.** Both staged: `timeout: 150`, same `statusMessage`, `_comment` 30s→120s/150s. Surgical pair-rail entry only. |
| **(3) invariant correctness** | **PASS with MED claim gap.** Detects kernel≠template, margin breach, missing statusMessage. Does **not** pin absolute 120 (see finding 2). |
| **(4) resolve_anchor + pin retirement** | **PASS.** File present+bad → die (no fallback); `ts` from git only; tags `[SENT-PLAN163-PIN]`/`[SENT-PLAN164-RAIL]`; guard after `--gate-v2` exit, exempts `--preflight-only`; pin-pack still has default 30. `bash -n` clean. |
| **(5) ADR gates 182/184** | **PASS.** AMEND is new `ADR-*.md` file → count +1; pack still +2 ADRs → 182→184; all gate/expect/closeout strings consistent. |
| **(6) upgrade.sh migration** | **PASS** (content). Cap from template; IFF `==60`; custom preserved; idempotent; fail-open on underviable template; tests cover migrate/unrelated/idempotent/custom. **Blocked by finding 1** for pack packaging. |
| **(7) sentinel Scope == MANIFEST** | **PASS** (rail). 8 dests set-equal; rail `shasum -c` all OK; twin `inputs-rail.sha256` matches. |
| **(8) ceremony script** | **PASS.** Dry-run trap restore (worktree+index); touched⊆scope; apply via `cp` + `CEO_KERNEL_OVERRIDE`; no Edit/Write; closeout 181→182 sed list matches live claim sites (9/6 docs). |
| **(9) fail-open/closed inversion** | **PASS.** Timeout still fail-OPEN (unchanged); doctor advisory-only (no exit); upgrade leaf fail-open; anchor validation fail-closed; pin re-apply fail-closed. No security regression; longer budget reduces structural case-F fail-open. |

---

## What is solid

- Rail-pack content and packaging are coherent (8 files, MANIFEST verified, Scope match).  
- Timeout uplift matches ratified OQ1/OQ2 (120/150).  
- Cross-pack split is sound: `doctor.sh` in rail; `upgrade.sh` migration in main-pack (avoids S284 clobber).  
- Pin-pack retirement guard is necessary (pin still ships default 30).  
- ADR-count bump matches house “AMEND as separate file” reality.

## Required for re-review → APPROVE

1. Remanifest main-pack (`MANIFEST.sha256` from on-disk staged bytes), prove `shasum -c` green, and show twin diff limited to the 4 intended rows (C3).  
2. Soften or tighten the “any unilateral flip goes red” claim (docs and/or test) so it matches real invariant semantics.

After (1)–(2), content as reviewed is otherwise landable for the rail ceremony path.
