"""Mutation M22 (evaluator): ``length_le`` off-by-one.

Original: ``len(val) <= node.length``.
Mutated: ``len(val) < node.length`` (strict less-than).

Property: ``length_le`` is inclusive (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "length_le off-by-one: uses < instead of <=",
    "original_snippet": "return len(val) <= int(node.length or 0)",
    "mutated_snippet": "return len(val) < int(node.length or 0)",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_length_le_match",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "length_le":
            # Off-by-one flipped to strict-greater — so `length_le: 5` with
            # len("ls")=2 returns False (broken: should be True inclusive).
            val = policy_mod._get_field(event, node.field_path or "")
            if val is None:
                return False
            try:
                return len(val) > int(node.length or 0)
            except TypeError:
                return False
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
