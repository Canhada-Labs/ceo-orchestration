"""Task: write a unit test that exercises a given function.

The task ships a correct ``parse_csv_line`` and asks for a ``test_solution.py``
that asserts its behavior. The verifier RUNS the candidate's test file against
the reference implementation and rewards based on how much it asserts (it must
pass, and it must actually contain assertions about edge cases).
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, read_text

_IMPL = '''\
def parse_csv_line(line):
    """Split a simple CSV line on commas, stripping each field. Empty line -> []."""
    line = line.strip()
    if not line:
        return []
    return [field.strip() for field in line.split(",")]
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_IMPL, encoding="utf-8")


def verify(workdir: Path) -> float:
    test_src = read_text(workdir, "test_solution.py")
    if not test_src.strip():
        return 0.0
    impl_src = read_text(workdir, "solution.py")
    # Run the candidate test file in a namespace that has the reference impl.
    ns = {"__name__": "__cand_test__"}
    try:
        exec(compile(impl_src, "solution.py", "exec"), ns)  # noqa: S102
        exec(compile(test_src, "test_solution.py", "exec"), ns)  # noqa: S102
    except Exception:
        return 0.0
    # Collect + run every test_* callable. All must pass.
    test_funcs = [v for k, v in ns.items() if k.startswith("test") and callable(v)]
    if not test_funcs:
        return 0.0
    ran = 0
    for fn in test_funcs:
        try:
            fn()
            ran += 1
        except Exception:
            return 0.0  # a failing assertion against the correct impl = bad test
    # Reward scales with assertion coverage signal: did the test touch the
    # empty-line edge case and the strip behavior?
    coverage = 0.5  # base for a passing test
    if "parse_csv_line" in test_src:
        coverage += 0.2
    if '""' in test_src or "''" in test_src or "[]" in test_src:
        coverage += 0.15  # empty-line edge case
    if "assert" in test_src:
        coverage += 0.15
    return clamp_reward(min(1.0, coverage))


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
