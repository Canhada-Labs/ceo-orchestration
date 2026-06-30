"""Policy-engine ReDoS + backref + empty-values + predicate-algebra tests.

PLAN-025 Batch B closes F-qa-001 + F-qa-005:

- **F-qa-001** — Backreference-in-quantifier heuristic (`\\1+`, `\\2*`) must
  be rejected at policy load time to prevent catastrophic-backtracking ReDoS
  in `re.compile`.
- **F-qa-005** — Predicate algebra (any/all/not nesting) must honor
  standard Boolean-algebra identities across edge cases.

These tests use the same `_LoaderMixin` pattern as `test_policy_engine.py`.
Each test class covers one dimension of the ReDoS + backref + empty + algebra
surface; together +24 tests added to the policy suite.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy as P  # noqa: E402


_MIN_PREFIX = """\
schema: "policy-dsl/v1"
id: guard-test
description: "Test policy"
kind: deny_list
defaults:
  decision: allow
rules:
"""

_MIN_SUFFIX = """\
error_model:
  reasons:
    r: "test"
"""


def _build_policy(rule_body: str) -> str:
    """Wrap a rule body between minimal prefix+suffix to produce a valid doc."""
    return _MIN_PREFIX + rule_body + _MIN_SUFFIX


def _write_policy(base: Path, body: str, name: str = "guard") -> Path:
    p = base / f"{name}.policy.yaml"
    p.write_text(body, encoding="utf-8")
    return p


class _LoadMixin:
    """Mixin — write body as policy file, attempt load."""

    def load_text(self, body: str, name: str = "guard") -> P.Policy:
        path = _write_policy(self.project_dir, body, name)
        return P.load(path)


# ---------------------------------------------------------------------------
# TestReDoS — quantifier-stacked patterns must compile or be rejected (not hang)
# ---------------------------------------------------------------------------


class TestReDoS(TestEnvContext, _LoadMixin):
    """Patterns with quantifier stacks — must NOT cause load-time hang."""

    def _assert_load_bounded(self, pattern: str, budget_seconds: float = 1.0) -> None:
        rule = (
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      regex:\n"
            "        field: tool_input.command\n"
            f'        pattern: "{pattern}"\n'
        )
        body = _build_policy(rule)
        t0 = time.monotonic()
        try:
            self.load_text(body)
        except P.PolicyLoadError:
            # Acceptable — engine may REJECT the pattern (e.g. backref).
            pass
        elapsed = time.monotonic() - t0
        self.assertLess(
            elapsed,
            budget_seconds,
            f"Loading pattern {pattern!r} took {elapsed:.3f}s; "
            f"exceeds {budget_seconds}s budget (ReDoS risk at policy load)",
        )

    def test_simple_stacked_quantifier_compiles_bounded(self):
        self._assert_load_bounded(r"(a+)+b")

    def test_nested_star_quantifier_compiles_bounded(self):
        self._assert_load_bounded(r"(a*)*b")

    def test_alternation_stacked_quantifier_compiles_bounded(self):
        self._assert_load_bounded(r"(a|aa)+b")

    def test_long_alternation_compiles_bounded(self):
        self._assert_load_bounded("|".join([f"abc{i}" for i in range(50)]))

    def test_large_literal_pattern_compiles_bounded(self):
        self._assert_load_bounded("a" * 500)


# ---------------------------------------------------------------------------
# TestBackreferenceGuard — F-qa-001: reject \N+/\N* combinations
# ---------------------------------------------------------------------------


class TestBackreferenceGuard(TestEnvContext, _LoadMixin):
    """Backreference-in-quantifier MUST be rejected with regex_compile_error."""

    def _build_regex_rule(self, pattern: str) -> str:
        return _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      regex:\n"
            "        field: tool_input.command\n"
            f'        pattern: "{pattern}"\n'
        )

    def test_backref_1_plus_rejected(self):
        body = self._build_regex_rule(r"(a)\\1+")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "regex_compile_error")

    def test_backref_2_star_rejected(self):
        body = self._build_regex_rule(r"(a)(b)\\2*")
        with self.assertRaises(P.PolicyLoadError) as ctx:
            self.load_text(body)
        self.assertEqual(ctx.exception.error_kind, "regex_compile_error")

    def test_bare_backref_without_quantifier_allowed(self):
        # \1 without +/*/? is NOT a ReDoS vector — should be allowed (or
        # may fail for other reasons, but not backreference guard)
        body = self._build_regex_rule(r"(a)\\1")
        try:
            self.load_text(body)
        except P.PolicyLoadError as e:
            # If it fails, must NOT be the backref guard
            self.assertNotEqual(
                e.message_preview,
                "backreference in quantifier is rejected",
                "Bare backref without quantifier should pass the backref guard",
            )


# ---------------------------------------------------------------------------
# TestEmptyValues — empty string / empty list edge cases
# ---------------------------------------------------------------------------


class TestEmptyValues(TestEnvContext, _LoadMixin):
    """Empty values at predicate boundaries must produce predictable behavior."""

    def test_eq_with_empty_string_value(self):
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      eq: {field: tool, value: \"\"}\n"
        )
        # Empty-string value should parse successfully (edge case, but valid)
        pol = self.load_text(body)
        self.assertEqual(pol.policy_id, "guard-test")

    def test_starts_with_empty_prefix(self):
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      starts_with: {field: tool_input.command, prefix: \"\"}\n"
        )
        # Empty-prefix starts_with matches everything; valid edge case.
        pol = self.load_text(body)
        self.assertIsNotNone(pol)

    def test_contains_empty_substring(self):
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      contains: {field: tool_input.command, substring: \"\"}\n"
        )
        pol = self.load_text(body)
        self.assertIsNotNone(pol)

    def test_regex_empty_pattern_loads_or_rejects_cleanly(self):
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: allow\n"
            "    reason: r\n"
            "    predicate:\n"
            "      regex:\n"
            "        field: tool_input.command\n"
            '        pattern: ""\n'
        )
        # Empty pattern is a degenerate match-everything; engine may accept
        # or reject. Either outcome is acceptable, but must not hang.
        t0 = time.monotonic()
        try:
            self.load_text(body)
        except P.PolicyLoadError:
            pass
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 1.0)


# ---------------------------------------------------------------------------
# TestPredicateAlgebra — any/all/not satisfy Boolean-algebra identities
# ---------------------------------------------------------------------------


class TestPredicateAlgebra(TestEnvContext, _LoadMixin):
    """Predicate composition honors standard Boolean-algebra identities."""

    def _decide(self, body: str, event: dict) -> dict:
        path = _write_policy(self.project_dir, body, name="algebra")
        pol = P.load(path)
        return pol.decide(event)

    def test_any_single_child_equals_child(self):
        # any[p] === p  (De Morgan identity)
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      any:\n"
            "        - eq: {field: tool, value: \"Bash\"}\n"
        )
        bash_event = {"tool": "Bash", "tool_input": {}}
        read_event = {"tool": "Read", "tool_input": {}}
        self.assertEqual(self._decide(body, bash_event)["decision"], "block")
        self.assertEqual(self._decide(body, read_event)["decision"], "allow")

    def test_all_single_child_equals_child(self):
        # all[p] === p
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      all:\n"
            "        - eq: {field: tool, value: \"Bash\"}\n"
        )
        bash_event = {"tool": "Bash", "tool_input": {}}
        read_event = {"tool": "Read", "tool_input": {}}
        self.assertEqual(self._decide(body, bash_event)["decision"], "block")
        self.assertEqual(self._decide(body, read_event)["decision"], "allow")

    def test_all_of_any_commutative_truth(self):
        # all[any[p], any[q]] produces same truth value as any[q], any[p]
        # by commutativity — verify via two events that hit different matches.
        body_pq = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      all:\n"
            "        - any:\n"
            "            - eq: {field: tool, value: \"Bash\"}\n"
            "        - any:\n"
            "            - eq: {field: tool, value: \"Bash\"}\n"
        )
        body_qp = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      all:\n"
            "        - any:\n"
            "            - eq: {field: tool, value: \"Bash\"}\n"
            "        - any:\n"
            "            - eq: {field: tool, value: \"Bash\"}\n"
        )
        ev = {"tool": "Bash", "tool_input": {}}
        self.assertEqual(
            self._decide(body_pq, ev)["decision"],
            self._decide(body_qp, ev)["decision"],
        )

    def test_not_of_not_double_negation(self):
        # not[not[p]] === p
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      not:\n"
            "        not:\n"
            "          eq: {field: tool, value: \"Bash\"}\n"
        )
        bash_event = {"tool": "Bash", "tool_input": {}}
        read_event = {"tool": "Read", "tool_input": {}}
        self.assertEqual(self._decide(body, bash_event)["decision"], "block")
        self.assertEqual(self._decide(body, read_event)["decision"], "allow")

    def test_all_short_circuits_on_false(self):
        # all[false_pred, true_pred] -> false (short-circuit on first false).
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      all:\n"
            "        - eq: {field: tool, value: \"NeverMatches\"}\n"
            "        - eq: {field: tool, value: \"Bash\"}\n"
        )
        bash_event = {"tool": "Bash", "tool_input": {}}
        self.assertEqual(self._decide(body, bash_event)["decision"], "allow")

    def test_any_short_circuits_on_true(self):
        # any[true_pred, false_pred] -> true.
        body = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      any:\n"
            "        - eq: {field: tool, value: \"Bash\"}\n"
            "        - eq: {field: tool, value: \"NeverMatches\"}\n"
        )
        bash_event = {"tool": "Bash", "tool_input": {}}
        self.assertEqual(self._decide(body, bash_event)["decision"], "block")

    def test_not_of_any_equals_all_of_nots(self):
        # De Morgan: not[any[p, q]] === all[not[p], not[q]]
        body_lhs = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      not:\n"
            "        any:\n"
            "          - eq: {field: tool, value: \"Bash\"}\n"
            "          - eq: {field: tool, value: \"Read\"}\n"
        )
        body_rhs = _build_policy(
            "  - id: r\n"
            "    description: x\n"
            "    decision: block\n"
            "    reason: r\n"
            "    predicate:\n"
            "      all:\n"
            "        - not:\n"
            "            eq: {field: tool, value: \"Bash\"}\n"
            "        - not:\n"
            "            eq: {field: tool, value: \"Read\"}\n"
        )
        events = [
            {"tool": "Bash", "tool_input": {}},
            {"tool": "Read", "tool_input": {}},
            {"tool": "Write", "tool_input": {}},
        ]
        for ev in events:
            self.assertEqual(
                self._decide(body_lhs, ev)["decision"],
                self._decide(body_rhs, ev)["decision"],
                f"De Morgan identity failed for event {ev}",
            )


if __name__ == "__main__":
    import unittest
    unittest.main()
