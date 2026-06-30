"""Policy mutation BASH-05: reorder rules so a vacuous ALLOW rule precedes blocks.

Insert a precedence-shadowing rule at position 0 that matches any Bash
invocation and decides ALLOW, making every downstream deny rule ineffective.
"""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "reorder",
    "description": "shadow allow-all rule placed at position 0",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Block destructive Bash commands and credential leaks (mutated)"
kind: mixed
defaults:
  decision: allow
rules:
  - id: shadow_allow_all_bash
    description: "SHADOW: allow every Bash command"
    decision: allow
    predicate:
      eq: {field: tool, value: "Bash"}
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
