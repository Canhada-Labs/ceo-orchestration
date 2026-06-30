"""Mutation M08 (compiler): regex compile skipped.

Original: ``_compile_predicate`` for ``regex`` form calls ``re.compile`` and
raises ``regex_compile_error`` on failure.
Mutated: compile skipped; invalid patterns stored but never compiled.

Property: invalid regex patterns MUST raise ``regex_compile_error`` at load
time (SPEC §5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_compile_predicate",
    "category": "compiler",
    "description": "regex compile skipped: invalid patterns silently accepted",
    "original_snippet": "try: node.compiled_regex = re.compile(pat) except re.error as e: raise PolicyLoadError('regex_compile_error', ...)",
    "mutated_snippet": "node.compiled_regex = None  # skip compile",
}

TARGETS = [
    "test_policy_engine.py::TestErrorModel::test_regex_compile_error",
]


def apply(policy_mod):
    import re as _re
    orig = _re.compile

    def mutated_compile(pat, *a, **kw):
        # Swallow re.error into a success with a never-matching regex
        # so the load-time gate passes when the source had invalid regex.
        try:
            return orig(pat, *a, **kw)
        except _re.error:
            return orig(r"(?!x)x")  # always-fail regex, no exception

    _re.compile = mutated_compile
    policy_mod.re.compile = mutated_compile

    def revert():
        _re.compile = orig
        policy_mod.re.compile = orig

    return revert
