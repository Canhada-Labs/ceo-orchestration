"""Mutation M10 (compiler): unknown predicate form silently accepted.

Original: ``_compile_predicate`` raises ``predicate_missing`` when ``form``
is not in ``_PREDICATE_FORMS``.
Mutated: unknown forms treated as always-false no-ops.

Property: unknown predicate forms MUST fail at load time (SPEC §3.5).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_compile_predicate",
    "category": "compiler",
    "description": "unknown predicate form silently accepted",
    "original_snippet": "if form not in _PREDICATE_FORMS: raise PolicyLoadError('predicate_missing', ...)",
    "mutated_snippet": "# unknown form silently tolerated",
}

TARGETS = [
    "test_policy_engine.py::TestErrorModel::test_predicate_missing_unknown_form",
]


def apply(policy_mod):
    orig = policy_mod._PREDICATE_FORMS
    # Add ANY string to the set by swapping to a frozenset-like permissive sentinel.
    class _AlwaysIn(frozenset):
        def __contains__(self, item):
            return True
    policy_mod._PREDICATE_FORMS = _AlwaysIn(orig)

    # We also need _compile_predicate to behave when it sees unknowns --
    # the original code would fall through to the leaf-form dispatch which
    # requires a 'field' key; tests with unknown form use `nope_not_a_form:`
    # as key with `all:` body (a mapping). So leaf-path runs but there's no
    # 'field' → raises parse_error. That still fails the original test
    # (which asserts predicate_missing specifically). OK.
    def revert():
        policy_mod._PREDICATE_FORMS = orig

    return revert
