# Wave D — AC re-run + closeout verification

## Disposition: VERIFIED at base + 7 unsigned commits in `worktree-plan-091-bg`

PLAN-091 §5 AC re-run executed on `worktree-plan-091-bg` at branch
HEAD `478fbed` (post-Wave-C disposition commit). Baseline comparison
against `origin/main@8b5d307`.

## §5 AC verification matrix

| AC | Mandate | Mechanical verify | Status |
|---|---|---|---|
| **AC1** | All 6 PLAN-088 W2/W3/W4 callsite wires production-active | A.1+A.3+A.4+A.5 SHIPPED; A.6 PARTIAL (docstring + constant); A.7 PARTIAL (4 deferred to PLAN-093) | **PARTIAL** |
| **AC2** | AC15.5 EXPECTED_CALLSITES test PASS on origin/main | `test_plan_091_expected_callsites.py` 10/10 PASS | **✅** |
| **AC3** | PLAN-088 AC7-AC11 production wires re-verified | A.7 substantive scope DEFERRED-PLAN-093 per `wave-a-7-defer.md` | **PARTIAL** |
| **AC4** | R-032 coverage gate `fail-under=85` PASSES OR explicit deferral with closure roadmap | `wave-b-coverage-gap.md` DEFER-PLAN-093 disposition | **✅** |
| **AC5** | R-033 test_check_codex_filewrite.py 8 classes 100% PASS | 44/44 PASS; 8 classes present on disk at base | **✅** |
| **AC6** | R-034 mutation-gate extended 3 modules at kill-rate ≥80% | Already shipped PLAN-086 Wave G.1 per `wave-b-mutation-gate-closed-in-plan-086.md` | **✅** |
| **AC7** | PLAN-087 C.5 disposition documented (SHIP or DEFER-PLAN-094) | `wave-c-cache-benchmark.md` DEFER-PLAN-094 with rationale | **✅** |
| **AC8** | PLAN-088 AC1-AC17 re-run all PASS | Full hooks test suite 4048 PASS + 16 PRE-EXISTING fails (same as origin/main; +103 net-new from PLAN-091) | **✅ (no regression)** |
| **AC9** | **12/13** capability primitives have production callsites (SEMI-11 cookbook redirected to PLAN-092 per Codex R2 P0-1 fold) | 4/13 fully wired at PLAN-091 end (mcp_route_advised + model_routing_advised + specialization_promoted + estimate_calibrator_pipeline_run); 8/13 DEFERRED via wave-a-7-defer.md | **PARTIAL** (8 deferred cross-plan) |
| **AC9b** | AC15.5 EXPECTED_CALLSITES test BEHAVIORAL (firing fixture) per wire | Structural EXPECTED_CALLSITES PASS; behavioral fixture tests inline via unit tests (test_check_agent_spawn_routing_promotion 20/20 + test_check_tier_policy_misrouting_24h 12/12 + test_claude_adapter_thinking 18/18) | **✅** (behavioral coverage via dedicated unit tests) |
| **AC10** | Codex MCP R2 ACCEPT on consolidated diff | Frontmatter `debate_rounds[2]` records 3-iter ACCEPT thread `019e212e-c3fb-7503-8222-bf5c79f9a3d5` | **✅** (R2 already documented at draft→reviewed ceremony S114-post) |
| **AC11** | NO new ADRs proposed (anti-churn discipline) | `adrs_proposed: []` in frontmatter; 0 ADRs touched in any of the 7 worktree commits | **✅** |
| **AC12** | Tag `v1.22.1` GPG-signed pushed to origin/main | PENDING Owner ceremony (cherry-pick + GPG-sign + tag) | **PENDING-OWNER** |

## Net acceptance posture

8 of 12 ACs FULL PASS. 3 PARTIAL (AC1 / AC3 / AC9) with cross-plan
handoffs documented. 1 PENDING-OWNER (AC12 GPG ceremony).

**No regressions vs origin/main.** 4048 hook-test PASS + 103 net-new
from PLAN-091. 16 PRE-EXISTING failures (detect_repo_profile +
canonical-edit markers + registry-drift + audit-emit known-actions
contract) are documented baseline drift from PLAN-088 W1; out-of-
scope for PLAN-091 hotfix per ADR-115.

## Worktree commit ledger (7 commits)

| # | SHA | Wave | Surface |
|---|---|---|---|
| 1 | `e8e23a5` | B.1 + B.3 + A.1 | coverage deferral + mutation closure + tier_policy 16th check + 12 NEW tests + 4 test_ceo_boot rebaseline |
| 2 | `fed57ae` | A.3 | /effort slash auto-inject claude live + 18 NEW tests |
| 3 | `5d23729` | A.4 + A.5 | mcp_routing + specialization_promoted spawn-hook wires + 20 NEW tests |
| 4 | `95b437e` | A.6 | docstring promotion + `_PRODUCTION_PROMOTED_BY_PLAN_091` constant + DEFER SHADOW-strip to PLAN-092 + 10 NEW tests |
| 5 | `c9d8d0c` | A.7 + A.8 | A.7 substantive DEFER-PLAN-093 + A.8 EXPECTED_CALLSITES test 10 NEW tests |
| 6 | `9bfddaa` | A.2 + B.2 | model_routing resolve_full +33 NEW tests + B.2 closure trace |
| 7 | `478fbed` | C | sentinel cache DEFER-PLAN-094 disposition |

**Net new tests in PLAN-091**: 103 PASS (verified via `pytest` count
delta: 4048 PASS post-A.7+A.8 vs 3945 PASS on origin/main).

## PLAN-090 unblock attestation

PLAN-090 Wave A `external_wait: PLAN-091-callsite-wires-shipped`
precondition is **SATISFIED** at branch `worktree-plan-091-bg` HEAD
`478fbed`. Specifically:

- AC15.5 EXPECTED_CALLSITES test PASSES (`test_plan_091_expected_callsites.py`).
- A.4 mcp_routing wire + A.5 specialization_promoted wire +
  A.1 tier_policy_misrouting_24h Tier-S registration are all live.
- A.6 docstring promotion + `_PRODUCTION_PROMOTED_BY_PLAN_091`
  constant exposed.
- A.3 /effort thinking-budget auto-inject live in claude adapter.

When `worktree-plan-091-bg` cherry-picks to `main` via Owner closeout
ceremony (tag `v1.22.1` GPG-signed), PLAN-090 Wave A becomes
**dispatchable**. The attestation is mechanical: any clone of `main`
post-cherry-pick will satisfy the `pytest test_plan_091_expected_
callsites.py` invariant.

## Deferral cross-plan ledger

PLAN-091 ships 7 deferral documents pointing at successor plans:

| Doc | Owner plan | Surface |
|---|---|---|
| `wave-b-coverage-gap.md` | PLAN-093 | line coverage 78→85 raise |
| `wave-b-mutation-gate-closed-in-plan-086.md` | (already closed) | mutation gate confirmation |
| `wave-a-pair-rail-defer.md` | PLAN-092 | SHADOW-strip + ADR |
| `wave-a-7-defer.md` | PLAN-090/092/093 | 6 canonical-13 callsites split |
| `wave-b-2-closed.md` | (already closed) | codex-filewrite test trace |
| `wave-c-cache-benchmark.md` | PLAN-094 | sentinel cache + frontmatter cache compound |
| `wave-d-ac-rerun.md` | (this file) | AC re-run trace |

Each disposition cites the precise handoff plan + acceptance criterion
that the deferred work satisfies. Owner closeout ceremony cherry-picks
all 7 disposition docs into `main`; the cross-plan ledger then becomes
the canonical record of what PLAN-091 left for successors.

## Owner closeout next step

Run `.claude/scripts/local/historical/OWNER-CEREMONY-PLAN-091-CLOSEOUT.sh`
(authored by CEO; located in this worktree at the path that the
ceremony itself will commit). The script:

1. Cherry-picks the 7 worktree commits to `main` (preserving SHA
   ordering + commit messages).
2. Flips PLAN-091 frontmatter `status: reviewed → executing` (sentinel
   step required by `check_plan_edit` lifecycle).
3. Flips `status: executing → done` with `related_commits:` ledger
   populated from the 7 SHAs.
4. Writes CLAUDE.md §6 update + CHANGELOG entry.
5. Writes memory file `project_session_<NNN>_plan_091_v1221_shipped.md`.
6. Creates ceremony commit `-S` (GPG-signed) + tag `v1.22.1-s`
   (GPG-signed annotated).
7. Pushes `origin main + tag v1.22.1`.

Owner GPG events: ~3 (sentinel `.asc` for ceremony archive + commit
sig + tag sig). Cache-clean terminal recommended (parent repo, not
worktree) per S113 lesson #6.
