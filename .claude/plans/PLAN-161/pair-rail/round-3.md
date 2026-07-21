Round-2 fixes F4 and F6–F9 are substantively present. F1–F3 remain incomplete, and F5’s proof contract lacks a necessary classifier boundary.

1. **P1 — U3 adds a public CLI flag without updating the normative CLI contract.**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:328-338` introduces `--purge-misinstalled`, while `SPEC/v1/install-cli.md:8-10` declares every flag part of the public API and its upgrade flag table at `SPEC/v1/install-cli.md:107-115` omits it. The frozen scope includes only the audit-log SPEC at `.claude/plans/PLAN-161-maintenance-sweep.md:174`.  
   Change: add `SPEC/v1/install-cli.md` to the W2 scope and document the flag’s opt-in default, preview behavior, hash authorization, backup semantics, and exit behavior.

2. **P1 — The activity-conditioned `pair_rail` classifier has no defined durable activity signal, so it cannot detect the silent-rail case it claims to catch.**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:445-455` requires distinguishing “no canonical activity” from “activity without reviews,” but the scope at `:171-180` excludes `check_pair_rail.py` and `check_canonical_edit.py`. Current non-review pair-rail breadcrumbs only reach a test sink/stderr (`.claude/hooks/check_pair_rail.py:725-749`), while durable `pair_rail_case` emission occurs only after a classified outcome (`.claude/hooks/check_pair_rail.py:1491-1504`). It also passes no session identifier, leaving the typed emitter’s default empty (`.claude/hooks/_lib/audit_emit.py:9628-9629`).  
   Change: define an independently durable, session-correlated “review expected/invoked” signal emitted before the review outcome, exclude sentinel-bypass/out-of-scope calls, add its producer and registration cascade to scope, and test activity-without-outcome escalation.

3. **P1 — Detect-only mode has no valid mapping in the new closed outcome schema.**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:421-426` permits only `{clean, findings, skipped_failopen}`; `:427-433` assigns `skipped_failopen` to malformed/infrastructure failure; yet `:433-437` requires detect-only mode to emit an observation. Detect-only performs no review (`.claude/hooks/codex_review_user_code.py:201-211`), so it is neither a parsed verdict nor an infrastructure failure. Mapping it to `skipped_failopen` also risks defeating L4’s `failopen == 0` oracle at `.claude/plans/PLAN-161-maintenance-sweep.md:498-502`.  
   Change: explicitly add a `detected_only` outcome or a separate typed action, define its classifier behavior, and cover detect-only followed by a real clean/findings review in the window-count tests.

4. **P1 — C4 never defines how a valid floor report becomes “contended” versus “uncontended.”**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:390-408` specifies malformed/timeout handling but no valid-report threshold. `profile-opus-4-7.py --floor` always exits zero after producing metrics (`.claude/scripts/profile-opus-4-7.py:812-816`); the existing workflow separately applies a 200 ms p50 threshold at `.github/workflows/validate.yml:1290-1304`. An exit-code-only implementation would therefore always allow attempt 3 and make the “still-contended” branch unreachable.  
   Change: pin the JSON schema and numeric threshold—presumably p50 ≤200 ms means uncontended—and make the proof exercise the real parser at below/equal/above-threshold boundaries.

5. **P1 — The frozen W2 scope is not executable as an exact touched-file allowlist.**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:146-147` and `:286-291` require a predeclared touched subset, but row 29 at `:179` says only “audit-registry golden,” not its path. The canonical path is `.claude/data/audit-registry.golden.txt` (`.claude/scripts/check-audit-registry-coverage.py:109`). C5 also mandates producer/classifier regression tests at `.claude/plans/PLAN-161-maintenance-sweep.md:437-444` without declaring their exact test paths.  
   Change: replace row 29 with the exact golden path and predeclare the producer/classifier test files, likely `.claude/hooks/tests/test_codex_review_user_code.py` and `.claude/scripts/tests/test_ceo_boot_liveness.py`.

6. **P2 — Round-2 history retains a stale table count.**  
   Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:225-226` says the “24-row table arithmetic” was confirmed, but the scope table at `:149-180` now contains 30 rows.  
   Change: update it to 30 or remove the count.

7. **P2 — The optional two-lane fallback conflicts with the unconditional Wave-3 oracle.**  
   Evidence: Wave 3 requires a three-lane report at `.claude/plans/PLAN-161-maintenance-sweep.md:470-474`, while success permits an Owner-ratified fallback at `:604-606`; OQ3 currently defaults to holding at `reviewed` at `:529-534`.  
   Change: either remove fallback from success until ratified or make the Wave-3 check conditional on the recorded OQ3 decision.

VERDICT: REJECT