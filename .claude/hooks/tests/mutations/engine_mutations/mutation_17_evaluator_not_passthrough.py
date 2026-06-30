"""Mutation M17 (evaluator): ``not`` passthrough (inversion removed).

Original: ``not`` returns ``not _evaluate(child, event)``.
Mutated: ``not`` returns ``_evaluate(child, event)`` (forgot to invert).

Property: ``not:`` must invert the child's truth value (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "not passthrough: inversion dropped",
    "original_snippet": "if form == 'not': return not _evaluate(node.children[0], event)",
    "mutated_snippet": "if form == 'not': return _evaluate(node.children[0], event)",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_not_inverts",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "not":
            return orig(node.children[0], event)
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
