"""Task: write a README documenting a small module's public API.

Docs task — the verifier scans the produced README for the required sections +
mentions of the module's public functions (deterministic substring checks).
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, read_text

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


def verify(workdir: Path) -> float:
    readme = read_text(workdir, "README.md").lower()
    if not readme.strip():
        return 0.0
    score = 0.0
    # Required: a title/heading.
    if readme.lstrip().startswith("#"):
        score += 0.2
    # Required: mentions each public function.
    for fn in ("add", "subtract", "multiply"):
        if fn in readme:
            score += 0.2
    # Required: a usage section keyword.
    if "usage" in readme or "example" in readme or "```" in readme:
        score += 0.2
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
