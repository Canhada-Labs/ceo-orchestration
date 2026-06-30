"""Mutation M14 (compiler): schema-version mismatch silently tolerated.

Original: ``load()`` raises ``schema_version_mismatch`` when schema != "policy-dsl/v1".
Mutated: any schema string accepted.

Property: ``schema`` MUST equal ``"policy-dsl/v1"`` (SPEC §3.4).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "load",
    "category": "compiler",
    "description": "schema-version mismatch silently passed",
    "original_snippet": "if schema_version != 'policy-dsl/v1': raise PolicyLoadError('schema_version_mismatch', ...)",
    "mutated_snippet": "# version check removed",
}

TARGETS = [
    "test_policy_engine.py::TestErrorModel::test_schema_version_mismatch",
]


def apply(policy_mod):
    orig_load = policy_mod.load

    def mutated(path):
        import pathlib
        p = pathlib.Path(path)
        text = p.read_text(encoding="utf-8")
        # Normalize any policy-dsl/* to policy-dsl/v1 pre-parse.
        new = text.replace('"policy-dsl/v2"', '"policy-dsl/v1"')
        new = new.replace('"policy-dsl/v3"', '"policy-dsl/v1"')
        if new != text:
            p.write_text(new, encoding="utf-8")
        return orig_load(p)

    policy_mod.load = mutated

    def revert():
        policy_mod.load = orig_load

    return revert
