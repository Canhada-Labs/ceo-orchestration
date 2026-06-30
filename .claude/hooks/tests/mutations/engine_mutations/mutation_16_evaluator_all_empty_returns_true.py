"""Mutation M16 (evaluator): ``all`` returns True on any non-empty children.

Original: ``all`` returns False on first false child.
Mutated: ``all`` returns True as soon as it finds at least one child; short-circuits positive.

Property: ``all:`` must be False when any child is False (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "all always-true short-circuit",
    "original_snippet": "for c in node.children: if not _evaluate(c, event): return False",
    "mutated_snippet": "return True  # broken short-circuit",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_all_short_circuits",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "all":
            return True
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
