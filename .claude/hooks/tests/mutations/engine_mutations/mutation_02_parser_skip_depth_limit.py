"""Mutation M02 (parser): skip the depth-limit check.

Original: ``_parse_block_node`` raises ``PolicyLoadError(depth_limit)`` when
``depth > _LIMIT_DEPTH``.
Mutated: depth check removed — nesting allowed to any depth until stack overflow.

Property: depth > 8 MUST be rejected with ``depth_limit`` (SPEC §3.3).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser._parse_block_node",
    "category": "parser",
    "description": "depth-limit omission: nesting depth ceiling never enforced",
    "original_snippet": "if depth > _LIMIT_DEPTH: raise PolicyLoadError('depth_limit', ...)",
    "mutated_snippet": "# depth check removed",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_depth_beyond_limit",
    "test_policy_engine.py::TestErrorModel::test_depth_limit",
]


def apply(policy_mod):
    orig = policy_mod._YamlParser._parse_block_node

    def mutated(self, indent, depth):
        # Clamp depth artificially so the limit never fires but we still recurse safely.
        return orig(self, indent, 1)

    policy_mod._YamlParser._parse_block_node = mutated

    def revert():
        policy_mod._YamlParser._parse_block_node = orig

    return revert
