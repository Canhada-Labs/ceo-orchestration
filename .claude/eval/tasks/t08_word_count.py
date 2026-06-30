"""Task: implement a case-insensitive word frequency counter.

Verifier checks ordering-independent frequency dicts on a few inputs.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, run_python, _VERIFY_ERROR

_STUB = '''\
def word_count(text):
    """Return a dict mapping each lowercased word to its count. Words are
    maximal runs of alphanumeric characters; everything else is a separator.
    """
    raise NotImplementedError
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_STUB, encoding="utf-8")


def verify(workdir: Path) -> float:
    cases = [
        ("the cat the dog", {"the": 2, "cat": 1, "dog": 1}),
        ("Hello, hello! HELLO?", {"hello": 3}),
        ("", {}),
        ("a-b a b", {"a": 2, "b": 2}),
    ]
    hits = 0
    for text, expected in cases:
        got = run_python(workdir, "solution.py", func="word_count", args=(text,))
        if got is _VERIFY_ERROR:
            return 0.0
        if isinstance(got, dict) and got == expected:
            hits += 1
    return clamp_reward(hits / len(cases))


TASK = {
    "id": "t08-word-count",
    "title": "Case-insensitive word frequency counter",
    "category": "feature",
    "difficulty": "medium",
    "setup": setup,
    "instruction": (
        "Implement word_count(text) in solution.py per its docstring: lowercase, "
        "split on non-alphanumeric runs, return a dict of word->count."
    ),
    "verify": verify,
}
