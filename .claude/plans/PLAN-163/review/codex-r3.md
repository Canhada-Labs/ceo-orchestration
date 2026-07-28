VERDICT: REJECT

1. **P1 — The per-architecture pin remains a proposed schema, not a defined contract.**

   **Claim:** v4 closes native-payload attestation end-to-end.

   **Evidence:** `.claude/plans/PLAN-163-substrate-uplift.md:284-296` mandates a “versioned per-arch manifest” but defines neither its fields, target-triple selector, nor mapping to the scalar verdict field currently consumed at `.github/scripts/validate-pair-rail-verdict.py:338-380`. The “all consumers” inventory also omits the obsolete ceremony and runtime claims in `docs/CROSS-LLM-THREAT-MODEL.md:349-356`. Finally, the plan requires hashing before subprocess but does not explicitly require invoking that same verified native path; current invocation remains `cmd = [codex_bin]` at `.claude/hooks/check_pair_rail.py:545-557`.

   **Fix:** define the manifest’s concrete serialization and required fields, platform-selection algorithm, and verdict-envelope representation; include the threat model/governance documentation consumers; require `_resolve_codex_bin` to return the verified native executable and pass that exact path to `subprocess.run`—or attest both launcher and payload with an equivalently binding design.

2. **P1 — The upgrade migration is three-state in prose but not genuinely specified per key.**

   **Claim:** every relevant key has absent/baseline/customized behavior and branch fixtures.

   **Evidence:** `.claude/plans/PLAN-163-substrate-uplift.md:311-320` never enumerates the leaf keys or their old/new baselines. `.claude/plans/PLAN-163-substrate-uplift.md:321-325` names only `availableModels`, `defaultMode`, and registration counts; it omits `fallbackModel` ordering and lists only baseline/customized upgrade assertions, not the absent branch. It also writes `defaultMode` ambiguously, while the live settings contract is `permissions.defaultMode` at `.claude/hooks/_lib/effective_config.py:178-180,534-542`.

   **Fix:** enumerate `availableModels`, `fallbackModel`, `permissions.defaultMode`, and the new hook-registration leaves. For each, state the exact old baseline, new baseline, absent/baseline/customized action, warning, idempotence oracle, and mixed-state fixtures. Preserve unrelated customized hook registrations while adding canonical registrations.

3. **P2 — Two round-2 contract errors remain in normative decision/check text.**

   **Claim:** the fallback identifier and shim contract are consistently corrected.

   **Evidence:** OQ1 still names nonexistent `FALLBACK_CHAIN` at `.claude/plans/PLAN-163-substrate-uplift.md:352-354`, despite the correct `FALLBACK_MODEL_CHAIN` at `:127-137`. The Check and Success criteria still require “shim-mapping” at `:203-205,374-376`, contradicting the pure-`exec` contract correctly stated at `:179-189`.

   **Fix:** replace `FALLBACK_CHAIN` with `FALLBACK_MODEL_CHAIN` and remove “shim-mapping” from both completion criteria.

Resolution trace: #1, #6, #7 and Grok’s ADR/T3 findings are resolved. #2 and #3 are correct in their main sections but retain contradictory normative text. #4 and #5 remain incomplete for the reasons above.