"""Policy mutation PLAN-06: remove ``missing_abandonment_reason`` rule."""
from __future__ import annotations

MUTATION = {
    "policy": "plan-edit",
    "category": "remove-rule",
    "description": "missing_abandonment_reason rule deleted",
}

FIXTURE_FILE = "plan-edit.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: plan-edit
description: "plan lifecycle (missing_abandonment_reason removed)"
kind: mixed
defaults:
  decision: allow
rules:
  - id: scope_skip_non_plan
    description: "not a plan file"
    decision: allow
    predicate:
      eq: {field: _derived_plan.is_plan_file, value: false}
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
error_model:
  reasons:
    illegal_status_value: "LIFECYCLE."
    illegal_transition: "LIFECYCLE."
    missing_reviewed_at: "LIFECYCLE."
    missing_completed_at: "LIFECYCLE."
    missing_related_commits: "LIFECYCLE."
    missing_abandonment_reason: "LIFECYCLE."
"""
