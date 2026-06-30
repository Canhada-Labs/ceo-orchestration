"""Mutation M01 (parser): accept YAML anchor instead of raising alias_rejected.

Original: ``_YamlParser._parse_inline_value`` raises ``PolicyLoadError(alias_rejected)``
when a scalar starts with ``&`` (anchor declaration).
Mutated: anchor prefix is stripped and the remainder is parsed as a plain scalar,
so ``&x Test`` becomes the string ``x Test``.

Property: YAML anchors MUST be rejected (SPEC §3.2).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser._parse_inline_value",
    "category": "parser",
    "description": "anchor acceptance: strip '&' prefix and parse as scalar",
    "original_snippet": "if raw.startswith('&') or raw.startswith('*'): raise PolicyLoadError('alias_rejected', ...)",
    "mutated_snippet": "if raw.startswith('&'): raw = raw[1:].lstrip(); # accept",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_anchor",
    "test_policy_engine.py::TestErrorModel::test_alias_rejected",
]


def apply(policy_mod):
    """Monkey-patch parser to accept anchors. Returns a revert callable."""
    orig = policy_mod._YamlParser._parse_inline_value

    def mutated(self, raw):
        r = policy_mod._YamlParser._strip_inline_comment(self, raw).strip()
        if not r:
            return None
        if r[0] == "&":
            # Strip anchor prefix and re-parse rest.
            rest = r[1:].lstrip()
            # Find space separator -> drop the anchor name.
            parts = rest.split(None, 1)
            remainder = parts[1] if len(parts) == 2 else (parts[0] if parts else "")
            return orig(self, remainder)
        if r[0] == "*":
            return orig(self, r)  # still reject alias
        return orig(self, raw)

    policy_mod._YamlParser._parse_inline_value = mutated

    def revert():
        policy_mod._YamlParser._parse_inline_value = orig

    return revert
