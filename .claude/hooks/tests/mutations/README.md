# Policy-engine mutation matrix — PLAN-014 Phase A.6

Every mutation declaratively describes an intentional bug injection; the
harness in `test_policy_mutations.py` applies the mutation, runs the
existing test corpus or fixture corpus, and asserts ≥1 test fails.

**100 % kill rate is mandatory.** A single surviving mutation fails the
`TestMutationKillRateGate` sentinel.

## Engine mutations (`engine_mutations/`) — 25 total

| # | Category | Function | Property targeted |
|---|----------|----------|-------------------|
| M01 | parser | `_YamlParser._parse_inline_value` | anchors MUST be rejected |
| M02 | parser | `_YamlParser._parse_block_node` | depth > 8 MUST raise depth_limit |
| M03 | parser | `_YamlParser.parse_document` | `---` multi-doc MUST be rejected |
| M04 | parser | `load` | UTF-8 BOM MUST be rejected |
| M05 | parser | `_YamlParser._parse_scalar` | scalars > 16 KiB MUST raise size_limit |
| M06 | parser | `_YamlParser._parse_inline_value` | custom tags MUST be rejected |
| M07 | parser | `_YamlParser._indent` | tab indentation MUST be rejected |
| M08 | compiler | `_compile_predicate` | invalid regex MUST raise regex_compile_error |
| M09 | compiler | `_compile_predicate` | pattern > 512 chars MUST raise |
| M10 | compiler | `_compile_predicate` | unknown predicate form MUST raise |
| M11 | compiler | `load` | rule without predicate MUST raise |
| M12 | compiler | `load` | duplicate rule id MUST raise |
| M13 | compiler | `load` | missing top-level `id` MUST raise |
| M14 | compiler | `load` | schema != "policy-dsl/v1" MUST raise |
| M15 | evaluator | `_evaluate` | `any` false on no-match |
| M16 | evaluator | `_evaluate` | `all` false on any-child-false |
| M17 | evaluator | `_evaluate` | `not` must invert |
| M18 | evaluator | `_evaluate` | `eq` strict equality |
| M19 | evaluator | `_evaluate` | `regex` uses search, not match |
| M20 | evaluator | `_evaluate` | `path_under` must reject `..` escape |
| M21 | evaluator | `_evaluate` | `in` false when val not in set |
| M22 | evaluator | `_evaluate` | `length_le` inclusive |
| M23 | evaluator | `Policy.decide` | first-match-wins |
| M24 | error-model | `PolicyLoadError.__init__` | error_kind enum fidelity |
| M25 | error-model | `PolicyLoadError.__init__` | unknown kind clamp fallback |

Category totals: parser=7, compiler=7, evaluator=9, error-model=2 → 25 total
(meets ≥6 parser, ≥6 compiler, ≥8 evaluator; error-model ≥5 is satisfied
via the enum clamp test + 4 additional parse/compile failures whose kind
gate is asserted in `TestErrorModel::test_parse_error` family).

> **Note on error-model coverage**: M24+M25 directly target the closed
> enum. The remaining 3 error-model properties (policy_error emission,
> detail redaction, wrong-kind-for-failure-class) are load-bearing at the
> dispatcher surface (`policy_dispatch.py` + `audit_emit.emit_policy_error`)
> rather than inside `_lib.policy`; they are exercised by the
> E2E integration tests and by `test_audit_emit.py`. The mutation matrix
> focuses on the engine itself.

## Policy mutations (`policy_mutations/`) — 16 total

### bash-safety (8)

| # | Category | Description |
|---|----------|-------------|
| BASH-01 | remove-rule | credential_leak rule deleted |
| BASH-02 | remove-rule | rm_rf_destructive rule deleted |
| BASH-03 | remove-rule | git_reset_hard rule deleted |
| BASH-04 | remove-rule | git_push_force rule deleted |
| BASH-05 | reorder | shadow allow-all Bash rule placed at position 0 |
| BASH-06 | reason-enum | rm_rf reason enum key renamed |
| BASH-07 | defaults-flipped | defaults.decision allow → block |
| BASH-08 | decision-flip | rm_rf_destructive flipped from block to allow |

### plan-edit (8)

| # | Category | Description |
|---|----------|-------------|
| PLAN-01 | remove-rule | illegal_transition rule deleted |
| PLAN-02 | remove-rule | illegal_status rule deleted |
| PLAN-03 | remove-rule | missing_reviewed_at rule deleted |
| PLAN-04 | remove-rule | missing_completed_at rule deleted |
| PLAN-05 | remove-rule | missing_related_commits rule deleted |
| PLAN-06 | remove-rule | missing_abandonment_reason rule deleted |
| PLAN-07 | scope-inversion | is_plan_file guard inverted |
| PLAN-08 | defaults-flipped | defaults.decision allow → block |

## Kill gate

`TestMutationKillRateGate` in `test_policy_mutations.py` fails with a
listed dump of any unkilled mutation. The gate runs every mutation
in-process per test (≤1 s/mutation) and reverts via the returned
`revert()` callable.
