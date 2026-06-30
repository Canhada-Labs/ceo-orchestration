"""Policy mutation BASH-01: remove ``credential_leak`` rule.

Fixtures with a non-empty ``credential_leak_provider`` expect decision=block
reason=credential_leak. With the rule removed they fall through to default
allow. At least one fixture must produce a differing decision.
"""
from __future__ import annotations

MUTATION = {
    "policy": "bash-safety",
    "category": "remove-rule",
    "description": "credential_leak rule deleted",
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
  - id: rm_rf_destructive
    description: "rm with both -r and -f across any subcommand"
    decision: block
    reason: rm_rf_destructive
    predicate:
      eq: {field: _derived_bash.matched_rm_rf, value: true}
  - id: git_reset_hard
    description: "git reset --hard across any subcommand"
    decision: block
    reason: git_reset_hard
    predicate:
      eq: {field: _derived_bash.matched_git_reset_hard, value: true}
  - id: git_push_force
    description: "git push --force or -f (not --force-with-lease)"
    decision: block
    reason: git_push_force
    predicate:
      eq: {field: _derived_bash.matched_git_push_force, value: true}
error_model:
  reasons:
    credential_leak: "GOVERNANCE: bash command contains what appears to be a live API credential. Redact before executing. Export via env var (never inline)."
    rm_rf_destructive: "BLOCKED: `rm` with -r and -f is destructive."
    git_reset_hard: "BLOCKED: `git reset --hard` is destructive."
    git_push_force: "BLOCKED: `git push --force` is destructive."
"""
