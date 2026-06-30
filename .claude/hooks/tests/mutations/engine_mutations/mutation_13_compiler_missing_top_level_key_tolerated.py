"""Mutation M13 (compiler): missing top-level ``id`` tolerated.

Original: ``load()`` raises ``parse_error`` on any missing top-level required key.
Mutated: missing ``id`` synthesized from filename stem.

Property: all SPEC §3.4 required top-level keys MUST be present.
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "load",
    "category": "compiler",
    "description": "missing top-level 'id' defaulted from filename",
    "original_snippet": "for key in _TOP_LEVEL_REQUIRED: if key not in data: raise PolicyLoadError('parse_error', ...)",
    "mutated_snippet": "if 'id' not in data: data['id'] = path.stem",
}

TARGETS = [
    "test_policy_engine.py::TestLoadFailures::test_missing_id",
]


def apply(policy_mod):
    orig = policy_mod._TOP_LEVEL_REQUIRED
    # Drop "id" from required set
    policy_mod._TOP_LEVEL_REQUIRED = tuple(k for k in orig if k != "id")
    orig_load = policy_mod.load

    def mutated(path):
        import pathlib
        p = pathlib.Path(path)
        # Add a synthetic id line if missing, BEFORE parsing.
        text = p.read_text(encoding="utf-8")
        if "\nid:" not in ("\n" + text) and not text.startswith("id:"):
            text = f"id: synthetic-{p.stem}\n" + text
            p.write_text(text, encoding="utf-8")
        return orig_load(p)

    policy_mod.load = mutated

    def revert():
        policy_mod._TOP_LEVEL_REQUIRED = orig
        policy_mod.load = orig_load

    return revert
