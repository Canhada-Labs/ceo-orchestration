"""Mutation M04 (parser): UTF-8 BOM silently accepted.

Original: ``load()`` raises ``parse_error`` if raw bytes start with ``\\xef\\xbb\\xbf``.
Mutated: BOM stripped before decode.

Property: UTF-8 BOM MUST be rejected (SPEC §3.2).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "load",
    "category": "parser",
    "description": "BOM acceptance: UTF-8 BOM silently consumed",
    "original_snippet": "if raw.startswith(b'\\xef\\xbb\\xbf'): raise PolicyLoadError('parse_error', 'UTF-8 BOM not allowed', ...)",
    "mutated_snippet": "raw = raw.lstrip(b'\\xef\\xbb\\xbf')",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_utf8_bom",
]


def apply(policy_mod):
    orig_load = policy_mod.load
    from pathlib import Path as _P

    def mutated(path):
        p = _P(path)
        raw_bytes = p.read_bytes()
        if raw_bytes.startswith(b"\xef\xbb\xbf"):
            # Rewrite the file without the BOM then delegate.
            p.write_bytes(raw_bytes[3:])
        return orig_load(path)

    policy_mod.load = mutated

    def revert():
        policy_mod.load = orig_load

    return revert
