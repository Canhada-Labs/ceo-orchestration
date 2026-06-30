"""Mutation M19 (evaluator): regex uses ``match`` instead of ``search``.

Original: ``node.compiled_regex.search(val) is not None``.
Mutated: ``node.compiled_regex.match(val) is not None`` — anchored at start.

Property: regex predicate uses unanchored ``search`` (SPEC §3.5).

Effect: ``regex: "rm -rf"`` must match ``"sudo rm -rf /tmp"``; under ``match``
the anchored match fails because the subject starts with ``sudo``.
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "regex match vs search (anchored at start)",
    "original_snippet": "return node.compiled_regex.search(val) is not None",
    "mutated_snippet": "return node.compiled_regex.match(val) is not None",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_regex_matches",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "regex":
            val = policy_mod._get_field(event, node.field_path or "")
            if val is None or not isinstance(val, str):
                return False
            return node.compiled_regex.match(val) is not None
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
