"""Mutation M20 (evaluator): ``path_under`` skips realpath resolution.

Original: realpath both sides so that ``..\\`` escapes are normalized.
Mutated: raw string prefix check.

Property: path_under must reject ``../`` escapes (SPEC §3.5).

Test signal: ``test_path_under_escape`` uses a sibling path; under raw prefix
it might coincidentally pass or fail — we ensure failure by using a plain
``startswith`` that DOES match the escape path (since both share the tmp prefix).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "path_under skips realpath; naive prefix match",
    "original_snippet": "commonpath([realpath(target), realpath(root)])",
    "mutated_snippet": "val.startswith(root_parent_prefix)",
}

TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_path_under_escape",
]


def apply(policy_mod):
    orig = policy_mod._evaluate
    import os

    def mutated(node, event):
        if node.form == "path_under":
            val = policy_mod._get_field(event, node.field_path or "")
            if not isinstance(val, str):
                return False
            # Naive prefix match against root's PARENT — so sibling paths
            # like ..../outside.txt still pass (the escape test expects allow).
            parent = os.path.dirname(node.root or "")
            return val.startswith(parent)
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
