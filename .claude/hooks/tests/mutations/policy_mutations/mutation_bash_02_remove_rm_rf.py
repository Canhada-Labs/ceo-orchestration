"""Policy mutation BASH-02: remove ``rm_rf_destructive`` rule."""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "remove-rule",
    "description": "rm_rf_destructive rule deleted",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Block destructive Bash commands and credential leaks (migrated from check_bash_safety.py)"
kind: deny_list
defaults:
  decision: allow
rules:
  - id: credential_leak
    description: "Bash command contains what appears to be a live API credential"
    decision: block
    reason: credential_leak
    predicate:
      neq: {field: _derived_bash.credential_leak_provider, value: ""}
  - id: git_reset_hard
    description: "git reset --hard"
    decision: block
    reason: git_reset_hard
    predicate:
      eq: {field: _derived_bash.matched_git_reset_hard, value: true}
  - id: git_push_force
    description: "git push --force"
    decision: block
    reason: git_push_force
    predicate:
      eq: {field: _derived_bash.matched_git_push_force, value: true}
error_model:
  reasons:
    credential_leak: "GOVERNANCE: bash command contains what appears to be a live API credential."
    rm_rf_destructive: "BLOCKED."
    git_reset_hard: "BLOCKED."
    git_push_force: "BLOCKED."
"""
