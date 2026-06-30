"""Task: implement a robust palindrome check (alnum-only, case-insensitive).

Verifier checks several phrases including punctuation/space handling.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_STUB = '''\
def is_palindrome(s):
    """Return True if s is a palindrome considering only alphanumeric
    characters and ignoring case. Empty string is a palindrome.
    """
    raise NotImplementedError
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_STUB, encoding="utf-8")


def verify(workdir: Path) -> float:
    cases = [
        ("", True),
        ("a", True),
        ("racecar", True),
        ("RaceCar", True),
        ("A man, a plan, a canal: Panama", True),
        ("hello", False),
        ("Was it a car or a cat I saw?", True),
        ("not a palindrome", False),
    ]
    hits = 0
    for s, expected in cases:
        got = run_python(workdir, "solution.py", func="is_palindrome", args=(s,))
        if got is _VERIFY_ERROR:
            return 0.0
        if bool(got) == expected:
            hits += 1
    return clamp_reward(hits / len(cases))


TASK = {
    "id": "t06-palindrome",
    "title": "Alphanumeric, case-insensitive palindrome check",
    "category": "feature",
    "difficulty": "easy",
    "setup": setup,
    "instruction": (
        "Implement is_palindrome(s) in solution.py per its docstring: consider "
        "only alphanumeric characters, ignore case, treat the empty string as a "
        "palindrome."
    ),
    "verify": verify,
}
