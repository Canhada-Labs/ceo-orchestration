I'll verify the four prose consistency sites on HEAD and confirm the r5→HEAD delta is prose-only.Next I'll read the r5 REJECT details and inspect the four prose sites on HEAD.Checking all four sites and scanning for residual contradictory phrasing.Confirming residual phrases are gone from the two live files (only historical r5 review text still describes the old wording). Emitting the r6 verdict.VERDICT: APPROVE

## Scope of this pass

Prose-only delta-confirm at HEAD `9787695` vs r5 base `10e0bd1`. Codex r5 MED (signing payload / provenance vs structural split) is the only open item; r5 already closed all executable / structural points.

## A. `git diff 10e0bd1..HEAD` is prose-only

| Probe | Result |
|---|---|
| Path set | **Exactly 2 files**: `architect/round-1/approved.body.md`, `land-plan164-rail.sh` |
| Commits in range | Single: `9787695` (*docs(PLAN-164): consistência do payload de assinatura pós-split…*) |
| Executable surface of `land-plan164-rail.sh` | **Identical** r5→HEAD: comments + `<<'MSG'` commit-body prose only; shell after stripping `#` lines and heredoc body hashes the same (`d8f114e65d7833d9…`, 22805 bytes) |
| `bash -n land-plan164-rail.sh` | OK |

No hooks, kernel, templates, PLAN-163 scripts, or rail manifest/twin in the delta.

## B. Four codex-r5 MED sites — now consistent

| # | Site | HEAD claim | Consistent with split? |
|---|---|---|---|
| 1 | **Sentinel item 5** `approved.body.md:55-63` | ADR 181→182 count-gate bump landed in **PRE-ceremony `8f21b25`, NOT in this pack** | Yes — no longer “ALSO stages `land-plan163-pack.sh`” |
| 2 | **Sentinel split rationale** `approved.body.md:78-97` | Two PLAN-163 scripts are **NOT Scope entries**; pre-ceremony so validator survives rollback | Yes — aligns with item 5 |
| 3 | **Ceremony header** `land-plan164-rail.sh:14-17` | Gate tooling (anchor validator + retirement guard + 182/184) **PRE-ceremony in `8f21b25` — NOT in this pack** | Yes |
| 4a | **Index-guard comment** `land-plan164-rail.sh:480` | “only the **6** scope paths” (was 8) | Yes |
| 4b | **Signed-commit body** `land-plan164-rail.sh:508-518` | Count gates bumped in **pre-ceremony tooling commit, not in this pack**; tooling paragraph restates PRE-ceremony land for r4 HIGH | Yes — no “this pack also stages” |

**Residual contradiction scan** on the two live files: no `also stages` / `ALSO stages` / `8 scope` / `stages land-plan163` (those strings remain only in historical r5 review text).

**Scope list** (`approved.body.md:116-124`): still exactly the 6 dests:

```
.claude/adr/ADR-110-AMEND-1-rail-timeout-contract.md
.claude/hooks/check_pair_rail.py
.claude/hooks/tests/test_pair_rail_timeout_invariant.py
.claude/settings.json
scripts/doctor.sh
templates/settings/settings.base.json
```

## C. What closed

Codex r5 MED is closed at HEAD: authorization / provenance prose (sentinel item 5, ceremony header, signed-commit body, index-guard “6 scope paths”) all state the same story as the structural split — PLAN-163 gate tooling is pre-ceremony `8f21b25`, not this 6-file rail pack. Executable bytes unchanged since r5. No new HIGH/MED.
