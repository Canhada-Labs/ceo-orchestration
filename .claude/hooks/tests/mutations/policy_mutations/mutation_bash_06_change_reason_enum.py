"""Policy mutation BASH-06: change ``rm_rf_destructive`` reason enum key.

Rule emits ``reason: rm_rf_destructive_v2`` while the fixture expects
``rm_rf_destructive``.
"""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "reason-enum-change",
    "description": "rm_rf_destructive reason key renamed to rm_rf_destructive_v2",
}

FIXTURE_FILE = "bash-safety.fixtures.jsonl"

POLICY_YAML = """\
schema: "policy-dsl/v1"
id: bash-safety
description: "Block destructive Bash commands (reason enum renamed)"
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
    reason: rm_rf_destructive_v2
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
    rm_rf_destructive_v2: "BLOCKED (renamed)."
    git_reset_hard: "BLOCKED."
    git_push_force: "BLOCKED."
"""
