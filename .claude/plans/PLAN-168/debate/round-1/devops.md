---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps Engineer (Principal)
generated_at: 2026-08-07T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- W1 corrects a real gate gap: four paths that govern the ownership oracles are
  absent from both path filters in `smoke-install.yml`, so a PR touching only
  the table or the harness skips the gate. The diagnosis is accurate.
- The plan has two provably false claims: `scripts/_hash_lib.sh` is already in
  both filters (smoke-install.yml:15 and :54); and the nightly e2e it mandates
  (AC-4) has no infrastructure path — there is no `schedule:` trigger in
  `smoke-install.yml` and no new nightly workflow specified.
- The v1.2.0 tag fetch deviates from the established `--print-pin` pattern
  without justification, and the AC-5 baseline comparison mechanism is
  underspecified: the baseline file carries machine-specific paths in its header
  that make a literal `diff` always fail in CI.

## Risks

- R-DO1 [HIGH] No nightly trigger exists — AC-4 is unsatisfiable as written.
  `smoke-install.yml` has only `pull_request:` and `push:` triggers (verified).
  No other workflow covers the e2e. Adding path filters for the ownership
  oracles does not create the nightly execution. The plan says "o job nightly
  roda o e2e" but never specifies what YAML creates that job.

- R-DO2 [MEDIUM] `scripts/_hash_lib.sh` is already in both path filters.
  smoke-install.yml:15 (pull_request) and smoke-install.yml:54 (push) both list
  it. The plan's W1 §1 lists five paths to add; only four are genuinely absent.
  If the implementer follows the plan literally they add a duplicate entry
  (harmless in GHA YAML but reveals the plan was written from memory, exactly
  the pattern PLAN-168 §5, rule 3 warns against).

- R-DO3 [MEDIUM] Hardcoded `v1.2.0` in the proposed YAML step creates a second
  source of truth. `test-ownership-table.sh:355` and `:372` already check for
  the tag internally. The established pattern (smoke-install.yml:112–115) uses
  `--print-pin` to read the pin from the test so the YAML never needs updating.
  `test-ownership-table.sh` has no `--print-pin` flag. When the test is updated
  to need `v1.3.0`, the YAML step will silently fetch the wrong tag.

- R-DO4 [MEDIUM] AC-5 baseline comparison mechanism is unspecified. The file
  `scripts/tests/ownership-baseline-map.txt:2–4` contains machine-specific
  scratchpad paths in its header. A naive `diff` against this committed file
  always fails in CI (different machine, different session path). The CI step
  must extract only the RED cell IDs (OWN-0016, OWN-0024, OWN-0027, OWN-0074)
  and compare those, not the full file. The plan says "comparar contra
  ownership-baseline-map.txt" without specifying HOW.

- R-DO5 [LOW] A `schedule:` trigger on `smoke-install.yml` runs ALL steps, not
  just the ownership e2e. The existing parity e2e (~25 min) would also run
  nightly, roughly doubling the nightly CI budget for this workflow. The
  `timeout-minutes: 25` constraint (smoke-install.yml:93) would likely be
  breached. A separate `ownership-nightly.yml` workflow avoids this.

## Must-fix (blocking)

1. **Specify the nightly trigger mechanism.** W1 touches only `smoke-install.yml`.
   AC-4 requires the e2e to run nightly. Two concrete options:

   Option A — add a `schedule:` trigger and a conditional second job to
   `smoke-install.yml`:
   ```yaml
   on:
     schedule:
       - cron: "0 5 * * *"   # 05:00 UTC; stagger with coverage (07:00), chaos (03:00)
     pull_request:
       paths: [...]
     push:
       branches: [main]
       paths: [...]

   jobs:
     smoke:      # existing job; add unit oracle step; leave e2e OUT
       if: github.event_name != 'schedule'
       ...
     ownership-e2e:
       if: github.event_name == 'schedule'
       timeout-minutes: 45   # headroom for 62 real installs on 2-core CI runner
       ...
   ```
   Path filters are ignored for `schedule` events; the per-PR path filter still
   scopes `smoke` correctly.

   Option B — add a new standalone `ownership-nightly.yml` with `schedule:` and
   `workflow_dispatch:` triggers. Cleaner isolation; lower blast radius.

   The plan must specify which option W1 implements. Without this, AC-4 is
   architecturally unsatisfiable.

2. **Correct the false `_hash_lib.sh` claim.** Remove it from the §W1 §1 addition
   list. The four real additions are:
   ```
   scripts/tests/test-ownership-table.sh
   scripts/tests/test-ownership-verdict-unit.sh
   scripts/tests/ownership_table.tsv
   docs/ownership-decision-table.md
   ```
   Leaving the false claim risks a duplicate entry or a wasted verification pass
   by the implementer.

3. **Add `--print-pin` to `test-ownership-table.sh` or document the hardcoding
   contract.** The existing parity e2e (smoke-install.yml:112) uses:
   ```yaml
   PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
   git fetch --no-tags --depth 1 origin "+refs/tags/$PIN:refs/tags/$PIN"
   ```
   If W1 hardcodes `v1.2.0` in the YAML instead, the plan must explicitly state
   this is a one-time decision with a documented update procedure. Diverging from
   the established pattern without explanation is a maintenance debt the next
   maintainer will pay.

4. **Specify the AC-5 comparison implementation.** The CI step that compares
   against `ownership-baseline-map.txt` must:
   (a) Extract only the RED-column cell IDs from the harness output;
   (b) Extract only the RED-column cell IDs from the committed baseline;
   (c) Fail if (a) ≠ (b) — set equality, not subset.
   The baseline header lines (absolute scratchpad paths from the session that
   produced it) must be excluded. Propose the concrete comparison snippet or a
   helper script path; "comparar contra o arquivo" is not implementable as
   written.

## Nice-to-have (advisory)

- Document the baseline update procedure. When a red cell is fixed (e.g., W2
  closes OWN-0016), the AC-5 gate will deliberately fail until the baseline is
  committed with the new set. This is intentional but will surprise the next
  person. A one-line comment in `ownership-baseline-map.txt` or a `README` in
  `scripts/tests/` explaining how to regenerate it avoids a false alarm.

- Raise `timeout-minutes` on the nightly job to 45. The current budget (25 min)
  was set for the parity e2e. The ownership e2e has 62 cells with a 60s
  per-cell timeout. On a 2-core ubuntu-latest runner (2–3× slower than local
  arm64), worst case is ~12 min. But FIFO-class hangs reach the per-cell
  timeout, so 25 min has no headroom for 4 deliberate-timeout rows.

- Consider a `workflow_dispatch:` trigger alongside `schedule:` on the nightly
  job. Allows manual re-trigger without waiting for the cron window, which is
  useful during the first week after W1 lands to verify the gate fires correctly.

## Unseen by the original plan

1. **Schedule events bypass path filters.** GitHub Actions ignores the `paths:`
   block for `schedule:` events. If W1 adds a schedule trigger to the SAME job
   as the path-filtered per-PR smoke, the per-PR path scoping evaporates on
   scheduled runs: every nightly run would execute the full job regardless of
   what changed. The plan's two-tier design (per-PR unit oracle, nightly e2e)
   requires two JOBS (or two workflows), not two entries in a path filter.

2. **Budget blowout on shared nightly job.** If the `schedule:` trigger is
   added to the existing `smoke` job, nightly runs will execute ALL current
   steps (smoke, upgrade oracle U1/U2/U3, user-ceremony leg, parity e2e and its
   positive control, spec-ownership e2e) PLUS the new ownership e2e. At 2–3×
   local speed, this nightly run can exceed 60 min — more than double the
   current `timeout-minutes: 25` cap. The concurrency group
   (`smoke-install-${{ github.ref }}`) does not protect against a nightly run
   colliding with a push trigger on main.

3. **`test-ownership-verdict-unit.sh` is a no-op gate until W2 lands.** The
   unit oracle exits 2 (HARNESS-ERR) if `_ownership_verdict` is not defined in
   `_framework_manifest_set.sh`. Currently it IS defined (line 472, confirmed).
   But the script at lines 51–55 explicitly says "W2 has not landed the
   function yet" in its error message, implying the function may be stripped if
   W2 is reverted. The CI step must document this dependency.

4. **The cron schedule must be registered in `.github/workflows/_README.md`.** 
   That file tracks the collision-avoidance schedule for all timed workflows
   (chaos 03:00 Monday, coverage 07:00 daily, perf-profile 06:00 Monday,
   tournament 04:00 1st). A new nightly or weekly cron must be staggered and
   registered there. The plan does not mention this.

## What I would NOT change

- The four genuinely missing path filter entries (test-ownership-table.sh,
  test-ownership-verdict-unit.sh, ownership_table.tsv,
  docs/ownership-decision-table.md) are correct. Absent these, the gate is
  exactly the "red gate nobody runs" class identified in r10-F4 — a PR that
  refactors only the decision table skips the gate entirely.

- The decision NOT to accept `HARNESS-SKIP` on tag-absent rows (W1 §1 item 2,
  final paragraph). Exiting 0 when the tag is unavailable reinstates the vacuous
  gate class. The tag fetch must fail-closed.

- The baseline-set comparison for AC-5 is correct design. Failing when the RED
  set shrinks (not just grows) prevents "fixing" the wrong tests to silence CI.
  This is the lesson from S296 and it must not be softened.

- The unit-oracle-per-PR / e2e-nightly split is architecturally sound. The 25
  min job limit has already been raised four times; running 62 real installs
  on every PR is not viable. The split is the right call; only the implementation
  path is underspecified.
