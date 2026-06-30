"""Mutation M25 (error-model): PolicyLoadError enum-clamping removed.

Original: ``PolicyLoadError.__init__`` clamps unknown error_kind values to
``parse_error`` as a defensive fallback.
Mutated: the clamping is skipped — arbitrary error_kind strings persist.

Property: the error_kind attribute MUST always be a member of the closed
SPEC §5 enum, even when callers pass a typo (SPEC §5 defensive clamp).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "PolicyLoadError.__init__",
    "category": "error-model",
    "description": "enum-clamping removed: unknown error_kind strings persist",
    "original_snippet": "if error_kind not in _ERROR_KINDS: error_kind = 'parse_error'",
    "mutated_snippet": "# clamp removed",
}

TARGETS = [
    "test_policy_engine.py::TestLoadFailures::test_policy_load_error_unknown_kind_falls_back",
]


def apply(policy_mod):
    orig_init = policy_mod.PolicyLoadError.__init__

    def mutated_init(self, error_kind, detail, policy_id=""):
        # Skip defensive clamp — unknown strings persist.
        self.error_kind = error_kind
        self.detail = detail
        self.policy_id = policy_id
        # Skip super().__init__ deliberately — but BaseException requires init.
        Exception.__init__(self, f"{error_kind}: {detail}")

    policy_mod.PolicyLoadError.__init__ = mutated_init

    def revert():
        policy_mod.PolicyLoadError.__init__ = orig_init

    return revert
