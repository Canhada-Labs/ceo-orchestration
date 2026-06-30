"""Policy mutation BASH-03: remove ``git_reset_hard`` rule."""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "remove-rule",
    "description": "git_reset_hard rule deleted",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Block destructive Bash commands (git_reset_hard removed)"
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
  - id: git_push_force
    description: "git push --force"
    decision: block
    reason: git_push_force
    predicate:
      eq: {field: _derived_bash.matched_git_push_force, value: true}
error_model:
  reasons:
    credential_leak: "BLOCKED."
    rm_rf_destructive: "BLOCKED."
    git_reset_hard: "BLOCKED."
    git_push_force: "BLOCKED."
"""
