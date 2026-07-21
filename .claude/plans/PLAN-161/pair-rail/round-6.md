Findings:

- **P1** — The Wave-1 command only negates each test’s exit status; it never performs the promised marker validation. Any scaffolding failure would therefore satisfy the check despite the prose claiming otherwise. Evidence: `.claude/plans/PLAN-161-maintenance-sweep.md:276-284`. Change the executable check to capture each test’s output, require a nonzero exit plus `REPRO-CONFIRMED`, and reject `SCAFFOLD-ERROR`, independently for both upgrade tests.

VERDICT: REJECT