"""Mutation M07 (parser): tab indentation silently tolerated.

Original: ``_indent`` raises ``parse_error`` on tab characters.
Mutated: tabs counted as two spaces.

Property: tab indentation MUST be rejected (SPEC §3.1).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser._indent",
    "category": "parser",
    "description": "tab indent tolerated: \\t treated as two spaces",
    "original_snippet": "raise PolicyLoadError('parse_error', 'tab indentation not allowed', ...)",
    "mutated_snippet": "n += 2  # treat tab as two spaces",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_tab_indent_rejected",
]


def apply(policy_mod):
    orig_indent = policy_mod._YamlParser._indent
    orig_load = policy_mod.load

    def mutated_indent(self, line):
        n = 0
        for ch in line:
            if ch == " ":
                n += 1
            elif ch == "\t":
                n += 2
            else:
                break
        return n

    # Pre-expand tabs in the source so downstream `line[indent:]` slicing
    # stays consistent — this is the "tolerance" we want to simulate.
    def mutated_load(path):
        import pathlib
        p = pathlib.Path(path)
        text = p.read_text(encoding="utf-8")
        if "\t" in text:
            p.write_text(text.expandtabs(2), encoding="utf-8")
        return orig_load(p)

    policy_mod._YamlParser._indent = mutated_indent
    policy_mod.load = mutated_load

    def revert():
        policy_mod._YamlParser._indent = orig_indent
        policy_mod.load = orig_load

    return revert
