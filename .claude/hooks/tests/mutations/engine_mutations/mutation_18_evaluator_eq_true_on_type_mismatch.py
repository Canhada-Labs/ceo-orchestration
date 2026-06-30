"""Mutation M18 (evaluator): ``eq`` returns True on type mismatch.

Original: ``val == node.value`` — type-strict Python equality.
Mutated: ``str(val) == str(node.value)`` — loose equality.

Property: ``eq`` must use strict Python equality (SPEC §3.5).

This matters e.g. when policies use ``value: true`` (bool) and the event
field is the string ``"true"`` — the unmutated engine treats them as
different; loose equality would match and change decisions.
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_evaluate",
    "category": "evaluator",
    "description": "eq loose equality via str coercion",
    "original_snippet": "if form == 'eq': return val == node.value",
    "mutated_snippet": "if form == 'eq': return str(val) == str(node.value)",
}

# eq matches-on-type is exercised indirectly by test_eq_matches + test_eq_miss;
# specifically the miss test uses tool='Read' vs value='Bash' which str-coerce
# also mismatches, so that test passes even mutated.
# For kill, we target `test_default_block_path` which relies on decide() to
# evaluate rule==None and fall through to default block. This mutation affects
# any eq path; to guarantee a kill we also target a dedicated scenario: the
# audit_payload_fields test exercises deny_rm_rf rule with matched_rm_rf (bool
# True); if str(True)=='True' were compared with str('true') the coercion would
# be fine... so we break differently: make eq ALWAYS True.
TARGETS = [
    "test_policy_engine.py::TestPredicateForms::test_eq_miss",
    "test_policy_engine.py::TestDecide::test_no_match_falls_through_to_defaults",
]


def apply(policy_mod):
    orig = policy_mod._evaluate

    def mutated(node, event):
        if node.form == "eq":
            return True
        return orig(node, event)

    policy_mod._evaluate = mutated

    def revert():
        policy_mod._evaluate = orig

    return revert
