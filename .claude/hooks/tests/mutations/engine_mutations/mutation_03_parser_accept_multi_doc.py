"""Mutation M03 (parser): accept multi-document stream.

Original: ``parse_document`` rejects ``---`` / ``...`` lines as multi-doc.
Mutated: the sentinel lines are silently skipped so a multi-doc file loads.

Property: multi-doc YAML streams MUST be rejected (SPEC §3.2).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser.parse_document",
    "category": "parser",
    "description": "multi-doc acceptance: --- / ... separators silently skipped",
    "original_snippet": "if stripped.strip() == '---': raise PolicyLoadError('parse_error', ...)",
    "mutated_snippet": "# --- / ... separators tolerated",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_multi_doc",
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_directive_yaml",
]


def apply(policy_mod):
    orig = policy_mod._YamlParser.parse_document

    def mutated(self):
        # Strip multi-doc markers AND directive lines before delegating.
        filtered = []
        for ln in self._lines:
            s = ln.rstrip("\r\n").strip()
            if s in ("---", "..."):
                continue
            if s.startswith("%YAML") or s.startswith("%TAG"):
                continue
            filtered.append(ln)
        self._lines = filtered
        self._n = len(self._lines)
        return orig(self)

    policy_mod._YamlParser.parse_document = mutated

    def revert():
        policy_mod._YamlParser.parse_document = orig

    return revert
