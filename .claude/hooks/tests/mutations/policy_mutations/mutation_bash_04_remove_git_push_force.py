"""Policy mutation BASH-04: remove ``git_push_force`` rule."""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "remove-rule",
    "description": "git_push_force rule deleted",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Block destructive Bash commands (git_push_force removed)"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: credential_leak
    description: "credential leak"
    decision: block
    reason: credential_leak
    predicate:
      neq: {field: _derived_bash.credential_leak_provider, value: ""}
  - id: rm_rf_destructive
    description: "rm -rf"
    decision: block
    reason: rm_rf_destructive
    predicate:
      eq: {field: _derived_bash.matched_rm_rf, value: true}
  - id: git_reset_hard
    description: "git reset --hard"
    decision: block
    reason: git_reset_hard
    predicate:
      eq: {field: _derived_bash.matched_git_reset_hard, value: true}
error_model:
  reasons:
    credential_leak: "BLOCKED."
    rm_rf_destructive: "BLOCKED."
    git_reset_hard: "BLOCKED."
    git_push_force: "BLOCKED."
"""
