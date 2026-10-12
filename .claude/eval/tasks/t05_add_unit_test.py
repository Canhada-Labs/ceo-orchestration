"""Task: write a unit test that exercises a given function.

The task ships a correct ``parse_csv_line`` and asks for a ``test_solution.py``
that asserts its behavior. The verifier RUNS the candidate's test file and
scores it by MUTATION, never by its text.

PLAN-191 W0-pre (pack 191-A2): three rounds of AST/dataflow rules over the
test code never converged (each cure had an escape: rebinding by for, with or
walrus, a binding in a nested def or a dead branch, two statements on one line;
and legitimate forms were under-scored). The rule is now behavioral:

* the candidate tests run against the REFERENCE ``_IMPL`` (a rewritten
  ``solution.py`` is never used), before and after the mutants; a file that
  does not load, has no ``test*`` function or fails there scores 0.0;
* each entry of ``_MUTANTS`` breaks ONE documented behavior; it is KILLED
  when the candidate file does not pass against it;
* reward = 0.5 + 0.5 * killed / len(_MUTANTS). An assert that reads nothing
  from the function, or a tautology, kills nothing and stays at 0.5.

The implementation under test is installed in the namespace AFTER the test
module runs (a shadowing definition loses) and as module ``solution`` while it
runs (``from solution import parse_csv_line`` gets it too).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Optional

from . import clamp_reward, read_text

_IMPL = '''\
def parse_csv_line(line):
    """Split a simple CSV line on commas, stripping each field. Empty line -> []."""
    line = line.strip()
    if not line:
        return []
    return [field.strip() for field in line.split(",")]
'''

# One wrong behavior each, derived from the docstring and the instruction.
_MUTANTS = (
    # empty line -> [''] instead of []
    "def parse_csv_line(line):\n"
    "    return [f.strip() for f in line.strip().split(',')]\n",
    # fields are not stripped
    "def parse_csv_line(line):\n"
    "    line = line.strip()\n"
    "    return line.split(',') if line else []\n",
    # splits on the wrong delimiter
    "def parse_csv_line(line):\n"
    "    line = line.strip()\n"
    "    return [f.strip() for f in line.split(';')] if line else []\n",
    # drops the last field
    "def parse_csv_line(line):\n"
    "    line = line.strip()\n"
    "    return [f.strip() for f in line.split(',')][:-1] if line else []\n",
)


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_IMPL, encoding="utf-8")


def _passes(test_src: str, impl_src: str) -> Optional[bool]:
    """Run every ``test*`` callable of the candidate against ``impl_src``.
    True = all pass; False = one fails; None = the file does not load or
    has no test."""
    ns = {"__name__": "__cand_test__"}
    exec(compile(impl_src, "solution.py", "exec"), ns)  # noqa: S102
    impl = ns["parse_csv_line"]

    def _under_test(line, *args, **kwargs):
        return impl(line, *args, **kwargs)

    module = types.ModuleType("solution")
    module.parse_csv_line = _under_test
    ns["parse_csv_line"] = _under_test
    saved = sys.modules.get("solution")
    sys.modules["solution"] = module
    try:
        try:
            exec(compile(test_src, "test_solution.py", "exec"), ns)  # noqa: S102
        except Exception:
            return None
        # Installed AFTER the test module ran, so a shadowing definition loses.
        ns["parse_csv_line"] = _under_test
        tests = [v for k, v in ns.items() if k.startswith("test") and callable(v)]
        if not tests:
            return None
        for fn in tests:
            try:
                fn()
            except Exception:
                return False
        return True
    finally:
        if saved is None:
            sys.modules.pop("solution", None)
        else:
            sys.modules["solution"] = saved


def verify(workdir: Path) -> float:
    test_src = read_text(workdir, "test_solution.py")
    if not test_src.strip():
        return 0.0
    try:
        if _passes(test_src, _IMPL) is not True:
            return 0.0  # a failing assertion against the correct impl = bad test
        killed = sum(1 for m in _MUTANTS if _passes(test_src, m) is not True)
        # The reference again AFTER the mutants: a test that keeps state across
        # runs to fail only the later ones fails here too.
        if _passes(test_src, _IMPL) is not True:
            return 0.0
    except Exception:
        return 0.0
    return clamp_reward(0.5 + 0.5 * killed / len(_MUTANTS))


TASK = {
    "id": "t05-add-unit-test",
    "title": "Write a passing unit test for parse_csv_line",
    "category": "test",
    "difficulty": "medium",
    "setup": setup,
    "instruction": (
        "solution.py defines parse_csv_line(line). Write test_solution.py with "
        "one or more test_* functions using plain assert statements that verify "
        "its behavior, including the empty-line edge case (returns []). The tests "
        "must pass against the given implementation."
    ),
    "verify": verify,
}
