"""PLAN-086 Wave B — model_routing.resolve() STUB contract tests.

28 cases: 7 task classes × 4 archetypes. The STUB is archetype-blind
(archetype overlay owned by PLAN-088 W2.2); these tests pin the
contract shape so PLAN-088 can inherit cleanly.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import model_routing  # noqa: E402


_TASK_CLASSES = (
    "file_read", "line_audit", "debate", "arch",
    "code_gen", "finops", "digest",
)

_FOUR_ARCHETYPES = (
    "incident-commander", "identity-trust-architect",
    "threat-detection-engineer", "llm-finops-architect",
)

_EXPECTED_FLOOR = {
    "file_read": "claude-haiku-4-5",
    "line_audit": "claude-haiku-4-5",
    "debate": "claude-opus-4-8",
    "arch": "claude-opus-4-8",
    "code_gen": "claude-sonnet-4-6",
    "finops": "claude-sonnet-4-6",
    "digest": "claude-haiku-4-5",
}


class TestTaskClassesFrozen(unittest.TestCase):
    def test_count_is_seven(self) -> None:
        self.assertEqual(len(model_routing.TASK_CLASSES), 7)

    def test_canonical_membership_and_order(self) -> None:
        self.assertEqual(model_routing.TASK_CLASSES, _TASK_CLASSES)


class TestResolveReturnsNonNull(unittest.TestCase):
    def test_all_seven_non_null(self) -> None:
        for tc in _TASK_CLASSES:
            self.assertIsNotNone(model_routing.resolve(tc))

    def test_all_seven_valid_floor(self) -> None:
        valid = {"claude-opus-4-8", "claude-sonnet-4-6", "claude-haiku-4-5"}
        for tc in _TASK_CLASSES:
            self.assertIn(model_routing.resolve(tc), valid)


class TestResolveMatrix(unittest.TestCase):
    pass


def _make_test(tc, arch):
    def _t(self):
        self.assertEqual(model_routing.resolve(tc), _EXPECTED_FLOOR[tc])
    _t.__name__ = f"test_{tc}_for_{arch.replace('-', '_')}"
    return _t


for _tc in _TASK_CLASSES:
    for _arch in _FOUR_ARCHETYPES:
        _method = _make_test(_tc, _arch)
        setattr(TestResolveMatrix, _method.__name__, _method)
del _tc, _arch, _method


class TestUnknownReturnsNone(unittest.TestCase):
    def test_unknown_string(self) -> None:
        self.assertIsNone(model_routing.resolve("totally_unknown"))

    def test_empty_string(self) -> None:
        self.assertIsNone(model_routing.resolve(""))

    def test_non_str(self) -> None:
        self.assertIsNone(model_routing.resolve(None))  # type: ignore
        self.assertIsNone(model_routing.resolve(42))  # type: ignore


class TestRouteAlias(unittest.TestCase):
    def test_route_is_resolve(self) -> None:
        self.assertIs(model_routing.route, model_routing.resolve)


if __name__ == "__main__":
    unittest.main()
