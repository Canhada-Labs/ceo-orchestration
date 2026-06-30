"""Policy mutation BASH-07: default flipped from allow to block.

Every fixture that expects decision=allow now receives decision=block
with reason=default_blocked.
"""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "defaults-flipped",
    "description": "defaults.decision allow -> block",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Default-block variant"
kind: mixed
defaults:
  decision: block
  reason: default_blocked
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
  - id: git_push_force
    description: "git push --force"
    decision: block
    reason: git_push_force
    predicate:
      eq: {field: _derived_bash.matched_git_push_force, value: true}
error_model:
  reasons:
    default_blocked: "BLOCKED by default."
    credential_leak: "BLOCKED."
    rm_rf_destructive: "BLOCKED."
    git_reset_hard: "BLOCKED."
    git_push_force: "BLOCKED."
"""
