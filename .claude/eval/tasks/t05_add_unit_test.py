"""Task: write a unit test that exercises a given function.

The task ships a correct ``parse_csv_line`` and asks for a ``test_solution.py``
that asserts its behavior. The verifier RUNS the candidate's test file against
the reference implementation and rewards based on how much it asserts (it must
pass, and it must actually contain assertions about edge cases).

PLAN-191 W0-pre: coverage is measured by BEHAVIOR, never by substrings (a
keyword in a comment used to score 1.0 with ``assert True``): the candidate
tests run against the REFERENCE ``_IMPL`` (a rewritten ``solution.py`` cannot
make a wrong assertion pass), every call to ``parse_csv_line`` is recorded at
runtime, and the assertion credit needs an ``assert`` whose expression calls it
or reads a name bound to its result in the same test function.
"""

from __future__ import annotations

import ast
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


def _calls_target(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name == "parse_csv_line":
                return True
    return False


def _asserts_on_target(test_src: str) -> bool:
    """True if some ``assert`` calls parse_csv_line, directly or through a name
    bound to its result in the same function (``result = parse_csv_line(...)``;
    one step of dataflow). AST: comments never count."""
    try:
        tree = ast.parse(test_src)
    except SyntaxError:
        return False
    if any(isinstance(n, ast.Assert) and _calls_target(n.test) for n in ast.walk(tree)):
        return True
    for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
        bound = {t.id for n in ast.walk(fn) if isinstance(n, ast.Assign) and _calls_target(n.value)
                 for tgt in n.targets for t in ast.walk(tgt) if isinstance(t, ast.Name)}
        for n in ast.walk(fn):
            if isinstance(n, ast.Assert) and any(
                    isinstance(s, ast.Name) and s.id in bound for s in ast.walk(n.test)):
                return True
    return False


def verify(workdir: Path) -> float:
    test_src = read_text(workdir, "test_solution.py")
    if not test_src.strip():
        return 0.0
    # Run the candidate test file in a namespace that has the reference impl.
    ns = {"__name__": "__cand_test__"}
    try:
        exec(compile(_IMPL, "solution.py", "exec"), ns)  # noqa: S102
        reference = ns["parse_csv_line"]
        exec(compile(test_src, "test_solution.py", "exec"), ns)  # noqa: S102
    except Exception:
        return 0.0
    calls = []

    def _recording(line, *args, **kwargs):
        calls.append(line)
        return reference(line, *args, **kwargs)

    # Installed AFTER the test module ran, so a shadowing definition loses.
    ns["parse_csv_line"] = _recording
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
    # Reward scales with what the tests actually exercised at runtime.
    coverage = 0.5  # base for a passing test
    if calls:
        coverage += 0.2  # parse_csv_line was really called
    if any(isinstance(c, str) and not c.strip() for c in calls):
        coverage += 0.15  # empty-line edge case was really exercised
    if _asserts_on_target(test_src):
        coverage += 0.15  # an assertion is about parse_csv_line's result
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
