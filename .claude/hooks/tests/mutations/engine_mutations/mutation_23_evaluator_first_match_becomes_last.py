"""Mutation M23 (evaluator): first-match-wins flipped to last-match-wins.

Original: ``Policy.decide`` iterates rules in declared order and returns the
FIRST matching rule's decision.
Mutated: iterates all rules and keeps the LAST match.

Property: first-match-wins (SPEC §4.1).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "Policy.decide",
    "category": "evaluator",
    "description": "first-match-wins flipped to last-match-wins",
    "original_snippet": "for rule in self.rules: if _evaluate(...): matched = rule; break",
    "mutated_snippet": "for rule in self.rules: if _evaluate(...): matched = rule  # no break",
}

TARGETS = [
    "test_policy_engine.py::TestDecide::test_first_match_wins",
]


def apply(policy_mod):
    orig = policy_mod.Policy.decide
    import time
    from typing import Optional, Dict, Any

    def mutated(self, event):
        start = time.monotonic()
        matched = None
        for rule in self.rules:
            if policy_mod._evaluate(rule.predicate, event):
                matched = rule  # no break -> last wins
        duration_ms = int((time.monotonic() - start) * 1000)
        if matched is None:
            decision = str(self.defaults.get("decision", "allow"))
            reason = self.defaults.get("reason")
            out = {"decision": decision}
            if decision == "block" and reason:
                out["reason"] = reason
                msg = self.error_reasons.get(str(reason))
                if msg:
                    out["message"] = msg
            self._emit_evaluated("<default>", decision, duration_ms)
            if decision == "block":
                self._emit_denied("<default>", str(reason or ""))
            return out
        out2 = {"decision": matched.decision}
        if matched.decision == "block" and matched.reason:
            out2["reason"] = matched.reason
            msg = self.error_reasons.get(matched.reason)
            if msg:
                out2["message"] = msg
        self._emit_evaluated(matched.rule_id, matched.decision, duration_ms)
        if matched.decision == "block":
            self._emit_denied(matched.rule_id, matched.reason or "")
        return out2

    policy_mod.Policy.decide = mutated

    def revert():
        policy_mod.Policy.decide = orig

    return revert
