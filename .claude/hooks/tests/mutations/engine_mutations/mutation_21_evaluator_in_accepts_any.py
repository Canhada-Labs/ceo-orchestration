"""Mutation M21 (evaluator): ``in`` always returns True.

Original: ``val in (node.values or ())``.
Mutated: always True.

Property: ``in:`` must return False when val not in values list (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "in-predicate always matches",
    "original_snippet": "return val in (node.values or ())",
    "mutated_snippet": "return True",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_in_miss",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "in":
            return True
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
