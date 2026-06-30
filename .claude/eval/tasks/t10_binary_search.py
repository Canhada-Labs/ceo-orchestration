"""Task: implement an iterative binary search returning the index or -1.

Verifier checks found/not-found across sorted inputs + boundary cases.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_STUB = '''\
def binary_search(arr, target):
    """Return the index of target in the sorted list arr, or -1 if absent.
    Must run in O(log n) (iterative or recursive bisection).
    """
    raise NotImplementedError
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_STUB, encoding="utf-8")


def verify(workdir: Path) -> float:
    arr = [1, 3, 5, 7, 9, 11, 13]
    cases = [
        (arr, 1, 0),
        (arr, 13, 6),
        (arr, 7, 3),
        (arr, 8, -1),
        (arr, 0, -1),
        ([], 5, -1),
        ([42], 42, 0),
    ]
    hits = 0
    for a, target, expected in cases:
        got = run_python(workdir, "solution.py", func="binary_search",
                         args=(a, target))
        if got is _VERIFY_ERROR:
            return 0.0
        if got == expected:
            hits += 1
    return clamp_reward(hits / len(cases))


TASK = {
    "id": "t10-binary-search",
    "title": "Iterative binary search returning index or -1",
    "category": "feature",
    "difficulty": "medium",
    "setup": setup,
    "instruction": (
        "Implement binary_search(arr, target) in solution.py per its docstring: "
        "return the index of target in the sorted list arr, or -1 if absent."
    ),
    "verify": verify,
}
