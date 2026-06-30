"""Mutation M06 (parser): custom tags accepted instead of rejected.

Original: ``_parse_inline_value`` raises ``tag_rejected`` when a scalar
starts with ``!``.
Mutated: tag prefix stripped; remainder returned as plain string.

Property: ``!!python/name:`` + other custom tags MUST be rejected (SPEC §3.2).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser._parse_inline_value",
    "category": "parser",
    "description": "tag acceptance: '!'-prefixed scalars treated as plain",
    "original_snippet": "if raw.startswith('!'): raise PolicyLoadError('tag_rejected', ...)",
    "mutated_snippet": "raw = raw.lstrip('!')",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_python_tag",
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_custom_tag",
    "test_policy_engine.py::TestErrorModel::test_tag_rejected",
]


def apply(policy_mod):
    orig_inline = policy_mod._YamlParser._parse_inline_value
    orig_scalar = policy_mod._YamlParser._parse_scalar

    def mutated_inline(self, raw):
        r = raw.strip()
        if r.startswith("!"):
            return r.lstrip("!").strip() or None
        return orig_inline(self, raw)

    def mutated_scalar(self, raw):
        r = raw.strip()
        if r.startswith("!"):
            return r.lstrip("!").strip() or None
        return orig_scalar(self, raw)

    policy_mod._YamlParser._parse_inline_value = mutated_inline
    policy_mod._YamlParser._parse_scalar = mutated_scalar

    def revert():
        policy_mod._YamlParser._parse_inline_value = orig_inline
        policy_mod._YamlParser._parse_scalar = orig_scalar

    return revert
