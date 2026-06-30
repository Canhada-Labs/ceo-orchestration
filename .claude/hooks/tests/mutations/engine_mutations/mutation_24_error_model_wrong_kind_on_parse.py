"""Mutation M24 (error-model): parse_error kind misclassified as predicate_missing.

Original: parse failures raise PolicyLoadError with error_kind='parse_error'.
Mutated: all parse_error raises are relabeled as predicate_missing (wrong enum).

Property: error_kind must match closed enum classifications per SPEC §5.
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "PolicyLoadError.__init__",
    "category": "error-model",
    "description": "parse_error silently rewritten to predicate_missing",
    "original_snippet": "self.error_kind = error_kind",
    "mutated_snippet": "if error_kind == 'parse_error': error_kind = 'predicate_missing'",
}

TARGETS = [
    "test_policy_engine.py::TestErrorModel::test_parse_error",
    "test_policy_engine.py::TestLoadFailures::test_missing_id",
    "test_policy_engine.py::TestLoadFailures::test_bad_kind_enum",
]


def apply(policy_mod):
    orig_init = policy_mod.PolicyLoadError.__init__

    def mutated_init(self, error_kind, detail, policy_id=""):
        if error_kind == "parse_error":
            error_kind = "predicate_missing"
        orig_init(self, error_kind, detail, policy_id)

    policy_mod.PolicyLoadError.__init__ = mutated_init

    def revert():
        policy_mod.PolicyLoadError.__init__ = orig_init

    return revert
