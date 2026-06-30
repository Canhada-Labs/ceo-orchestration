"""Mutation M15 (evaluator): ``any`` / ``all`` short-circuit semantics inverted.

Original: ``all`` returns False on any child false; ``any`` returns True on any child true.
Mutated: ``any`` returns True on NO children (vacuously true bug); ``all`` returns True even
when children disagree — wrong semantics.

Here we specifically break ``any`` so that it matches even when no child matches.

Property: ``any:`` must be False when all children are False (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "any/all semantics inverted: any->True if no match found",
    "original_snippet": "if form == 'any': ... return False",
    "mutated_snippet": "if form == 'any': return True",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_any_short_circuits",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "any":
            # Always True (broken).
            return True
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
