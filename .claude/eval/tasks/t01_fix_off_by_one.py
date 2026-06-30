"""Task: fix an off-by-one bug in a range-sum function.

The starting file sums ``range(1, n)`` (excludes ``n``); the spec wants the
inclusive sum ``1 + 2 + ... + n``. The verifier execs the candidate's
``sum_to_n`` and checks several inputs, with partial credit.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_BUGGY = '''\
def sum_to_n(n):
    """Return 1 + 2 + ... + n (inclusive)."""
    total = 0
    for i in range(1, n):  # BUG: excludes n
        total += i
    return total
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_BUGGY, encoding="utf-8")


def verify(workdir: Path) -> float:
    cases = [(1, 1), (5, 15), (10, 55), (100, 5050)]
    hits = 0
    for n, expected in cases:
        got = run_python(workdir, "solution.py", func="sum_to_n", args=(n,))
        if got is _VERIFY_ERROR:
            return 0.0
        if got == expected:
            hits += 1
    return clamp_reward(hits / len(cases))


TASK = {
    "id": "t01-fix-off-by-one",
    "title": "Fix off-by-one in inclusive range sum",
    "category": "bugfix",
    "difficulty": "easy",
    "setup": setup,
    "instruction": (
        "The function sum_to_n in solution.py should return the inclusive sum "
        "1 + 2 + ... + n but currently excludes n. Fix the bug. Keep the "
        "function name and signature."
    ),
    "verify": verify,
}
