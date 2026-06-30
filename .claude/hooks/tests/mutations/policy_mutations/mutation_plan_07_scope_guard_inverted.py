"""Policy mutation PLAN-07: scope guard inverted (is_plan_file=true skip).

Inverts the non-plan-file short-circuit so plan files are skipped and
non-plan files are evaluated. Every fixture with ``is_plan_file: true``
now short-circuits to allow, bypassing all downstream lifecycle rules.
"""
from __future__ import annotations

MUTATION = {
    "policy": "plan-edit",
    "category": "scope-inversion",
    "description": "scope_skip_non_plan inverted (skip plan files instead)",
}

FIXTURE_FILE = "plan-edit.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: plan-edit
description: "plan lifecycle (scope inverted)"
kind: mixed
defaults:
  decision: allow
rules:
  - id: scope_skip_non_plan
    description: "BUG: skip plan files (inverted)"
    decision: allow
    predicate:
      eq: {field: _derived_plan.is_plan_file, value: true}
  - id: scope_skip_no_change
    description: "no status change"
    decision: allow
    predicate:
      eq: {field: _derived_plan.status_changed, value: false}
  - id: illegal_status
    description: "illegal status"
    decision: block
    reason: illegal_status_value
    predicate:
      all:
        - eq: {field: _derived_plan.status_changed, value: true}
        - eq: {field: _derived_plan.new_status_legal, value: false}
  - id: illegal_transition
    description: "illegal transition"
    decision: block
    reason: illegal_transition
    predicate:
      all:
        - eq: {field: _derived_plan.status_changed, value: true}
        - eq: {field: _derived_plan.new_status_legal, value: true}
        - eq: {field: _derived_plan.transition_legal, value: false}
  - id: missing_reviewed_at
    description: "missing reviewed_at"
    decision: block
    reason: missing_reviewed_at
    predicate:
      all:
        - eq: {field: _derived_plan.new_status, value: "reviewed"}
        - eq: {field: _derived_plan.reviewed_at_present, value: false}
  - id: missing_completed_at
    description: "missing completed_at"
    decision: block
    reason: missing_completed_at
    predicate:
      all:
        - eq: {field: _derived_plan.new_status, value: "done"}
        - eq: {field: _derived_plan.completed_at_present, value: false}
  - id: missing_related_commits
    description: "missing related_commits"
    decision: block
    reason: missing_related_commits
    predicate:
      all:
        - eq: {field: _derived_plan.new_status, value: "done"}
        - eq: {field: _derived_plan.completed_at_present, value: true}
        - eq: {field: _derived_plan.related_commits_nonempty, value: false}
  - id: missing_abandonment_reason
    description: "missing abandonment reason"
    decision: block
    reason: missing_abandonment_reason
    predicate:
      all:
        - eq: {field: _derived_plan.new_status, value: "abandoned"}
        - eq: {field: _derived_plan.abandonment_reason_present, value: false}
error_model:
  reasons:
    illegal_status_value: "LIFECYCLE."
    illegal_transition: "LIFECYCLE."
    missing_reviewed_at: "LIFECYCLE."
    missing_completed_at: "LIFECYCLE."
    missing_related_commits: "LIFECYCLE."
    missing_abandonment_reason: "LIFECYCLE."
"""
