"""Task: implement classic FizzBuzz from a stub.

Verifier checks the canonical FizzBuzz output for n in 1..20, with partial
credit per correct entry.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_STUB = '''\
def fizzbuzz(n):
    """Return a list of length n. For i in 1..n:
       - "FizzBuzz" if divisible by 15
       - "Fizz" if divisible by 3
       - "Buzz" if divisible by 5
       - str(i) otherwise
    """
    raise NotImplementedError
'''


def _expected(n: int):
    out = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_STUB, encoding="utf-8")


def verify(workdir: Path) -> float:
    got = run_python(workdir, "solution.py", func="fizzbuzz", args=(20,))
    if got is _VERIFY_ERROR or not isinstance(got, list):
        return 0.0
    expected = _expected(20)
    if len(got) != len(expected):
        return 0.0
    hits = sum(1 for a, b in zip(got, expected) if str(a) == b)
    return clamp_reward(hits / len(expected))


TASK = {
    "id": "t02-implement-fizzbuzz",
    "title": "Implement FizzBuzz returning a list",
    "category": "feature",
    "difficulty": "easy",
    "setup": setup,
    "instruction": (
        "Implement the fizzbuzz(n) function in solution.py per its docstring. "
        "Return a list of n entries."
    ),
    "verify": verify,
}
