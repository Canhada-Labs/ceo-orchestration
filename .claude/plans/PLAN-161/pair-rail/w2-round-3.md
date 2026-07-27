# PLAN-161 W2 pack — codex pair-rail round 3 (2026-07-27)

Input: r2 dispositions + fresh HEAD->staged diff, redacted via ADR-114.

## Verdict

REJECT

1. **[P1] F2 does not produce the claimed RED deficit.** A real Codex outage is converted into Case F and emits `pair_rail_case` at [check_pair_rail.py:1743](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/.claude/hooks/check_pair_rail.py:1743). Because every `pair_rail_case` counts as terminal at [ceo-boot.py:1764](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/.claude/scripts/ceo-boot.py:1764), expected and terminal counts balance. The new outage test omits the Case-F event the real producer emits, so it proves an impossible trace. A healthy case plus an outage remains YELLOW, not the promised RED deficit.

2. **[P1] F11 can delete adopter data through a preserved excluded symlink.** The delete pass preserves an excluded symlink, but the later prune uses `-f`/`-d` on its descendants and then `rm -f`/`rmdir` at [upgrade.sh:1242](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/scripts/upgrade.sh:1242) and [upgrade.sh:1257](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/scripts/upgrade.sh:1257). Those tests follow ancestor symlinks, allowing deletion in the symlink target. The claimed no-manifest survivor probe is also absent: [test-upgrade-exclusions.sh:128](/Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-exclusions.sh:128) seeds no pre-existing excluded content.

3. **[P1] C3 introduces shell injection through `scope`.** The operator-controlled scope is interpolated directly inside single-quoted shell source at [council-audit.js:203](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/.claude/workflows/council-audit.js:203). A scope containing `'` can break the command or inject commands into the conductor block, defeating its read-only/redacted-egress guarantees. It must be transported as safely encoded data or an argv value.

4. **[P2] The C4 worst-case timeout proof still assumes an unenforced 30-second floor cap.** The final floor-sanity step invokes Python without `timeout 30` at [validate.yml:1353](/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-161/staged/.github/workflows/validate.yml:1353), while the 28-minute calculation budgets exactly 30 seconds for it. Only the contention pre-probe is capped.

F12, F13, and F14 are verified fixed.
## CEO triage — all 4 ACCEPTED + fixed in fix-round-3 (7c-series):
- F2: outage IS Case F (emits pair_rail_case) → not a deficit; comment+tests corrected to true deficit = zero-case (hook died between emits). terminal={pair_rail_case} unchanged.
- F11: legacy delete+prune made symlink-safe (leaf-treat, never recurse); real survivor+symlink assertions folded into tracked test-upgrade-exclusions.sh E.2b (RED on HEAD).
- F3/C3: POSIX shq() shell-quote helper on operator scope; injection probe proves closed.
- F4/C4: floor-sanity step now timeout-30 capped with distinct infra label.
