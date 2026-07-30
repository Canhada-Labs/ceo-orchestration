I'll verify the r2 closures in current bytes: prior verdicts first, then the suffix-newest / revert-aware land scripts and related docs.Prior verdicts loaded. Next I'll inspect the staged pin/land scripts and the docs that claim the suffix-newest and revert-aware fixes.Reading `resolve_anchor`, the revert-aware land guard, and the upgrade/statusMessage changes next.Probing the suffix-newest rule and the remaining claimed closures next.Manifest format needs a custom checker; locating upgrade tests and plan prose next.Manifests are 8/8 and 43/43. Re-running the recovery probe with better error handling.VERDICT: APPROVE

## Closure table (codex r2 + open grok r1 LOWs → current bytes)

| ID | Source | Severity | Status | Evidence |
|---|---|---|---|---|
| **HIGH-1** post-revert deadlock under canonical-oldest | Codex r2 | HIGH | **CLOSED** | Staged `land-plan163-pin.sh` `resolve_anchor()` is **suffix-newest**: ceremony = subject **ends with** `[SENT-PLAN163-PIN]`/`[SENT-PLAN164-RAIL]` (`case *"[TAG]"`); absent-file fallback = first suffix match on newest-first `git log` (`:104-154`). `land-plan164-rail.sh` already-landed guard uses the same suffix rule (`:197-224`); after a real `git revert` (body `This reverts commit <sha>`), real re-run **dies** without `--rerun-after-revert` and **warns/accepts** with the flag; usage + rollback text document it (`:82-85`, `:99`, `:589`). |
| **MED-2** prose authenticates superseded algorithm | Codex r2 | MED | **CLOSED** | Sentinel `approved.body.md:80-89` = suffix + newest fallback. Plan W2 `PLAN-164-pair-rail-timeout-uplift.md:167-176` matches. `w1-delta-bundle.md` headed **SNAPSHOT DO ROUND 1 (SUPERSEDED)** with note that manifests are authoritative. |
| **LOW-3** upgrade omits `statusMessage` | Grok r1 | LOW | **CLOSED** | Main-pack `upgrade.sh:2043-2047` imports template `statusMessage` **IFF absent** on the 60→template migrate path; adopter custom preserved. Tests `test_migration_brings_template_status_message_iff_absent` + `test_adopter_custom_status_message_is_preserved` present. Overlay run: **38/38 passed**. |
| **LOW-4** `die` inside `$(resolve_anchor)` | Grok r1 | LOW | **CLOSED** | No command-sub call site; `resolve_anchor` sets `ANCHOR_SHA_OUT`/`ANCHOR_TS_OUT`; `gate_v2` calls it directly (`:157-165`). Specific FATAL reaches the terminal. |
| Manifests / twins | packaging | — | **OK** | Rail MANIFEST **8/8** digests match staged paths; twin `inputs-rail.sha256` **byte-identical**. Main-pack **43/43** digests match; twin `inputs-pack.sha256` **byte-identical**. Rail header notes r2 suffix-newest; main header notes PLAN-164 W1 re-hash. Dest-clean preflight present (`land-plan164-rail.sh:277+`). |

## Adversarial suffix-newest probe (isolated harness + clean git history)

| Probe | Result |
|---|---|
| Ceremony subject ending in `[SENT-PLAN164-RAIL]` | **anchors** |
| Closeout subject (no tag) | **rejected** as pointer |
| Mid-subject tag mention (`… [SENT-PLAN164-RAIL] …`) | **rejected** (r1 launder vector stays closed) |
| Default `git revert` subject `Revert "…[SENT-PLAN164-RAIL]"` (ends with `"`) | **not** a ceremony subject |
| Absent file after c1→revert→c2 | fallback = **newest** ceremony (c2), not c1 |
| File rewritten to c2 after recovery | `resolve_anchor` **accepts** |
| End-to-end: c1 land → already-landed DIE → `git revert` → NEED_FLAG → `--rerun-after-revert` ACCEPT → new ceremony → rewrite anchor → resolve OK | **works** |

## New findings

| ID | Severity | Finding |
|---|---|---|
| **N1** | **LOW** (residual, non-blocking) | Closeout anti-reuse comment still says `resolve_anchor greps for it; a reused tag would move the cutoff` (`land-plan164-rail.sh:573-576`). Under **suffix** match, mid-message reuse does **not** move the cutoff; only a subject that **ends** with the tag becomes a ceremony (and newest-wins can then prefer it if the pointer is absent/rewritten). Operational rule (“never put the bracketed tag in closeout”) remains correct defense-in-depth. |
| **N2** | **LOW** (residual, non-blocking) | Pin-pack retirement still uses plain `git log --grep='\[SENT-PLAN164-RAIL\]' -n 1` without the suffix filter (`land-plan163-pin.sh:333`). A revert (or any mid-subject mention) still counts as “rail landed” and blocks pin re-apply. Fail-closed / over-restrictive only; recovery path is the rail `--rerun-after-revert`, not pin re-apply. Pre-existed the r2 fix shape; not a laundering hole. |

## Net

All codex r2 HIGH/MED and the two open grok r1 LOWs are closed in current staged/ceremony bytes with mechanical proof (manifest 8/8 + 43/43, twin identity, 38/38 migration tests, bash suffix probes, clean revert→flag→re-ceremony→anchor rewrite path). No new HIGH/MED defect. Residual LOWs are wording/consistency only and do not block W2 rail ceremony.
