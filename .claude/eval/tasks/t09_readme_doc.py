"""Task: write a README documenting a small module's public API.

Docs task — the verifier scans the produced README for the required sections +
mentions of the module's public functions (deterministic checks). PLAN-191
W0-pre: every part is scored BELOW the title line and by its own shape (a prose
description, a fenced example that uses the API), so a title line that merely
lists the keywords (``# add subtract multiply usage``) no longer scores 1.0.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from . import clamp_reward, read_text

_FUNCS = ("add", "subtract", "multiply")
# Words that never count toward the description (API names + section words).
_NOT_PROSE = set(_FUNCS) | {"usage", "example", "examples", "calc", "py", "python"}
# A usage example imports the module or calls one of its functions.
_USES_API = re.compile(
    r"\b(?:from\s+calc\s+import|import\s+calc)\b|\b(?:add|subtract|multiply)\s*\("
)

_MODULE = '''\
def add(a, b):
    """Return a + b."""
    return a + b


def subtract(a, b):
    """Return a - b."""
    return a - b


def multiply(a, b):
    """Return a * b."""
    return a * b
'''


def setup(workdir: Path) -> None:
    (workdir / "calc.py").write_text(_MODULE, encoding="utf-8")


def _split_fences(lines: List[str]) -> Tuple[List[str], List[str]]:
    """Return (lines outside ``` fences, text of each CLOSED fenced block)."""
    prose: List[str] = []
    fences: List[str] = []
    block = None
    for line in lines:
        if line.strip().startswith("```"):
            if block is None:
                block = []
            else:
                fences.append("\n".join(block))
                block = None
            continue
        (prose if block is None else block).append(line)
    return prose, fences


def verify(workdir: Path) -> float:
    lines = read_text(workdir, "README.md").lower().splitlines()
    filled = [i for i, line in enumerate(lines) if line.strip()]
    if not filled:
        return 0.0
    score = 0.0
    # Title (0.15): the first non-blank line is a heading.
    if lines[filled[0]].lstrip().startswith("#"):
        score += 0.15
    body = lines[filled[0] + 1:]  # everything below the title line
    prose, fences = _split_fences(body)
    # Description (0.15): a prose line with >= 3 words besides API/section names.
    for line in prose:
        if line.strip() and not line.lstrip().startswith("#"):
            words = [w for w in re.findall(r"[a-z]+", line) if w not in _NOT_PROSE]
            if len(words) >= 3:
                score += 0.15
                break
    # Usage example (0.25): a fenced block that imports calc or calls a function.
    if any(_USES_API.search(block) for block in fences):
        score += 0.25
    # Each public function named below the title, as a word (0.15 each).
    text = "\n".join(body)
    for fn in _FUNCS:
        if re.search(r"\b%s\b" % fn, text):
            score += 0.15
    return clamp_reward(min(1.0, score))


TASK = {
    "id": "t09-readme-doc",
    "title": "Document calc.py public API in a README",
    "category": "docs",
    "difficulty": "easy",
    "setup": setup,
    "instruction": (
        "calc.py exposes add, subtract, multiply. Write a README.md with a title "
        "heading, a short description, a usage example, and a mention of each of "
        "the three public functions."
    ),
    "verify": verify,
}
