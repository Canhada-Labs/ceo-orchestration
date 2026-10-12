"""Task: refactor to remove duplication while preserving behavior.

The stub has two near-identical functions; the spec wants a single helper used
by both. The verifier checks observable behavior plus a source-level signal
that the duplication is gone. PLAN-191 W0-pre: the signal is "both public
functions still defined AND exactly ONE ``raise`` left" (the shared negative
check, AST-counted) — deleting only the 9 chars `` or s < 0`` keeps two checks
and used to score 1.0.
"""

from __future__ import annotations

import ast
from pathlib import Path

from . import clamp_reward, read_text, run_python, _VERIFY_ERROR

_DUP = '''\
def area_rectangle(w, h):
    if w < 0 or h < 0:
        raise ValueError("negative")
    return w * h


def area_square(s):
    if s < 0 or s < 0:
        raise ValueError("negative")
    return s * s
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_DUP, encoding="utf-8")


def _single_negative_check(src: str) -> bool:
    """Both public functions defined at module level and exactly one ``raise``."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return False
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    names |= {
        t.id for n in tree.body if isinstance(n, ast.Assign)
        for t in n.targets if isinstance(t, ast.Name)
    }
    raises = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Raise))
    return {"area_rectangle", "area_square"} <= names and raises == 1


def verify(workdir: Path) -> float:
    # Behavior must be preserved (primary signal — 0.8 of the reward).
    behavior = []
    for func, args, expected in (
        ("area_rectangle", (3, 4), 12),
        ("area_square", (5,), 25),
        ("area_rectangle", (0, 9), 0),
    ):
        got = run_python(workdir, "solution.py", func=func, args=args)
        behavior.append(got == expected)
    # Negative must raise (verifier catches the sentinel == it raised).
    neg = run_python(workdir, "solution.py", func="area_square", args=(-2,))
    behavior.append(neg is _VERIFY_ERROR)

    behavior_score = sum(1 for b in behavior if b) / len(behavior)

    # Refactor signal (0.2): ONE negative check shared by both functions (a
    # helper, or one function delegating to the other). Source-level, AST.
    src = read_text(workdir, "solution.py")
    refactor_signal = (
        "s < 0 or s < 0" not in src  # the obvious duplication is gone
        and _single_negative_check(src)
    )
    return clamp_reward(0.8 * behavior_score + 0.2 * (1.0 if refactor_signal else 0.0))


TASK = {
    "id": "t04-refactor-dedupe",
    "title": "Refactor duplicated area helpers, preserve behavior",
    "category": "refactor",
    "difficulty": "medium",
    "setup": setup,
    "instruction": (
        "Refactor solution.py to remove the duplicated negative-check logic "
        "(note area_square has a redundant `s < 0 or s < 0`). Keep both "
        "functions and their public behavior: negatives raise ValueError, "
        "valid inputs return the area."
    ),
    "verify": verify,
}
