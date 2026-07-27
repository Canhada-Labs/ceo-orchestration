# PLAN-161 W2 pack — codex pair-rail round 6 (2026-07-27)

## Verdict

REJECT

1. **[P1] Invocation-ID validation can still alias reviews and false-green F2.** The regex accepts any 0–16 hex characters, while both typed emitters truncate before validation. Thus two off-shape IDs sharing their first 16 characters collapse to one ID; `ceo-boot` treats every nonempty value as valid and set-difference pairing lets an older terminal offset a later dead review. Accept only `""` for legacy or exactly 16 lowercase hex, validating before truncation. `.claude/plans/PLAN-161/staged/.claude/hooks/_lib/audit_emit.py:7505`, `:8788`, `:9936`; `.claude/plans/PLAN-161/staged/.claude/scripts/ceo-boot.py:1961`, `:1981`, `:2013`.

2. **[P2] Round 6 reintroduces the F9 environment-isolation violation.** The new matrix regressions remain under plain `unittest.TestCase`, directly write `os.environ`, and invoke the real expected-event emitter. That emitter deliberately ignores `CEO_PAIR_RAIL_AUDIT_SINK`, so tests can write audit rows through inherited real `$HOME`/audit paths. Use `TestEnvContext` plus `mock.patch.dict`, or stub the durable emitter. `.claude/plans/PLAN-161/staged/.claude/hooks/tests/test_check_pair_rail_matrix.py:520`, `:569`, `:610`, `:613`, `:615`; `.claude/plans/PLAN-161/staged/.claude/hooks/check_pair_rail.py:1497`; `AGENTS.md:24`.
## CEO triage — 2 findings ACCEPTED (both narrow C5 hardening; r5+r6 substance confirmed):
- F2 [P1] review_id shape gate too loose: ^[0-9a-f]{0,16}$ + truncate-before-validate lets off-shape ids alias. Fix: validate RAW before truncation, accept only "" OR exactly 16 lowercase hex; ceo-boot uses only exact-16 as a pairing key, else legacy bucket.
- F9 [P2] the r6-added test_check_pair_rail_matrix.py writes real os.environ + real audit sink. Fix: TestEnvContext isolation + mock.patch.dict and/or stub the durable emitter.
