"""S363 (2026-10-12): the root conftest marks ``budget`` serial by test NAME, not by FILE name.

S220 auto-marks timing tests ``serial`` (root ``conftest.py``,
``pytest_collection_modifyitems``) so the xdist pass (``-m 'not serial'``)
skips them and a separate serial pass runs them. ``budget`` used to match the
WHOLE nodeid, so every test in a file named ``*budget*.py`` (token and char
budgets, no wall clock) ran in the slower serial pass. The cure matches
``budget`` against the name part only (``nodeid.split("::", 1)[-1]``, which
keeps the class name): file-level token-budget suites go to the parallel pass,
and every function-level or class-level wall-clock budget
(``test_dispatch_verbose_budget_10s``) stays serial.

The checks run against the hook pytest REALLY calls: the root ``conftest.py``
module as this session's plugin manager loaded it, not a copy of its regex.

1. ``test_x_budget.py::test_a`` -> NOT serial;
2. ``test_y.py::test_dispatch_budget_10s`` -> serial;
3. the other S220 tokens still match the whole nodeid, path included;
4. red control: the S220 shape (``budget`` on the whole nodeid) breaks 1.,
   so this guard can tell the two shapes apart;
5. end to end: this file is itself named ``*budget*.py`` and its items went
   through the live hook. The test names below avoid every S220 token, so
   none of them may carry ``serial``.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Iterable, List, Set, Tuple

_REPO = Path(__file__).resolve().parents[3]
_ROOT_CONFTEST = (_REPO / "conftest.py").resolve()

# The S220 regex as it stood before S363, byte for byte. Used ONLY as the red
# control: it is the shape the live hook must no longer have.
_S220_SERIAL_NODEID_RE = re.compile(
    r"(latency|p99|p95|perf|performance|redos|budget|under_\d+m?s|completes|within_tolerance|largepayload|_1mb|_1kb|throughput|elapsed|concurren|producers|async_flush|spool_append|spool_drain|stale_lock|times_out|timeout|timing)",
    re.IGNORECASE,
)

# (nodeid, must the hook mark it serial?)
_CASES: List[Tuple[str, bool]] = [
    # the two cases of the contract
    ("test_x_budget.py::test_a", False),
    ("test_y.py::test_dispatch_budget_10s", True),
    # the three real wall-clock budgets found by the S363 refuter
    (".claude/scripts/tests/test_ceo_boot_enhanced.py::TestVerboseMode::"
     "test_dispatch_verbose_budget_10s", True),
    (".claude/scripts/tests/test_ceo_boot.py::TestDispatcher::"
     "test_dispatch_fits_aggregate_budget", True),
    (".claude/hooks/tests/test_adversary_rules_live.py::LiveRegexBudgetTests::"
     "test_catastrophic_regex_fails_open_within_budget_and_continues", True),
    # a class named *Budget* keeps its tests serial (the name part keeps the class)
    ("tests/test_federation/test_ac20_handshake_budget.py::AC20HandshakeBudgetTest::"
     "test_subprocess_count_assertion_destructive", True),
    # file-level and directory-level token budgets with plain test names (real nodeids)
    (".claude/hooks/tests/test_check_budget.py::TestDecidePure::test_at_cap_exact_no_warning", False),
    (".claude/scripts/tests/test_context_budget.py::TestHeavyFileFlagBoundaries::"
     "test_command_boundary_100_lines", False),
    (".claude/scripts/predict-budget/tests/test_predict_plan_cost.py::TestPredictPlanCost::"
     "test_01_plan_id_from_frontmatter", False),
    # ... while a test in the same file whose NAME says budget stays serial
    (".claude/hooks/tests/test_check_budget.py::TestDecidePure::test_bypass_consumes_budget", True),
    # the other S220 tokens still match the whole nodeid, path included
    (".claude/hooks/tests/test_hook_latency_relative_gate.py::test_a", True),
    ("tests/load/test_perf_probe.py::test_a", True),
    ("test_y.py::test_spool_drain_order", True),
    ("test_y.py::test_a", False),
]


class _FakeItem:
    """The two attributes the hook touches: ``nodeid`` and ``add_marker``."""

    def __init__(self, nodeid: str) -> None:
        self.nodeid = nodeid
        self.marker_names: List[str] = []

    def add_marker(self, marker: object) -> None:
        self.marker_names.append(str(getattr(marker, "name", marker)))


def _root_conftest_module(config: object) -> object:
    for plugin in config.pluginmanager.get_plugins():  # type: ignore[attr-defined]
        source = getattr(plugin, "__file__", None)
        if source and Path(source).resolve() == _ROOT_CONFTEST:
            return plugin
    raise AssertionError("root conftest.py is not loaded as a pytest plugin in this session")


def _live_marker(config: object) -> Callable[[Iterable[str]], Set[str]]:
    hook = getattr(_root_conftest_module(config), "pytest_collection_modifyitems")

    def serial_ids(nodeids: Iterable[str]) -> Set[str]:
        items = [_FakeItem(n) for n in nodeids]
        hook(config, items)
        return {i.nodeid for i in items if "serial" in i.marker_names}

    return serial_ids


def _s220_marker(nodeids: Iterable[str]) -> Set[str]:
    return {n for n in nodeids if _S220_SERIAL_NODEID_RE.search(n)}


def _contract_violations(serial_ids: Callable[[Iterable[str]], Set[str]]) -> List[str]:
    marked = serial_ids([n for n, _ in _CASES])
    return [
        "%s: expected serial=%s, got serial=%s" % (n, want, n in marked)
        for n, want in _CASES
        if (n in marked) != want
    ]


def test_live_hook_marks_by_test_name(pytestconfig) -> None:
    assert _contract_violations(_live_marker(pytestconfig)) == []


def test_red_control_s220_shape_breaks_the_contract() -> None:
    violations = _contract_violations(_s220_marker)
    # The S220 shape fails exactly where the file or directory name carries
    # "budget" and the test name does not.
    assert violations == [
        "test_x_budget.py::test_a: expected serial=False, got serial=True",
        ".claude/hooks/tests/test_check_budget.py::TestDecidePure::test_at_cap_exact_no_warning: "
        "expected serial=False, got serial=True",
        ".claude/scripts/tests/test_context_budget.py::TestHeavyFileFlagBoundaries::"
        "test_command_boundary_100_lines: expected serial=False, got serial=True",
        ".claude/scripts/predict-budget/tests/test_predict_plan_cost.py::TestPredictPlanCost::"
        "test_01_plan_id_from_frontmatter: expected serial=False, got serial=True",
    ]


def test_this_file_collected_without_serial(request) -> None:
    # This file is named *budget*.py; under the S220 shape the live hook would
    # have marked this item serial.
    assert "budget" in request.node.nodeid.split("::", 1)[0]
    assert request.node.get_closest_marker("serial") is None
