"""Mutation M09 (compiler): regex pattern-length cap disabled.

Original: patterns longer than _LIMIT_REGEX_PATTERN (512) raise regex_compile_error.
Mutated: cap bumped to effectively disabled.

Property: regex patterns > 512 chars MUST fail at load time (SPEC §3.3).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_compile_predicate",
    "category": "compiler",
    "description": "regex pattern cap effectively removed",
    "original_snippet": "if len(pat) > _LIMIT_REGEX_PATTERN: raise PolicyLoadError('regex_compile_error', ...)",
    "mutated_snippet": "# cap removed",
}

TARGETS = [
    "test_policy_engine.py::TestLoadFailures::test_regex_pattern_too_long",
]


def apply(policy_mod):
    orig = policy_mod._LIMIT_REGEX_PATTERN
    policy_mod._LIMIT_REGEX_PATTERN = 10_000_000

    def revert():
        policy_mod._LIMIT_REGEX_PATTERN = orig

    return revert
