#!/usr/bin/env python3
"""Parser-aware destructive Bash safety hook facade.

The executable declarations live in installable `_lib` fragments so that the
installer copies them with the `.claude/hooks` library. Each fragment is compiled into
this module's namespace: private names, dataclasses, mutable state and calls
through monkeypatched globals therefore retain the historical behavior.

# Source-surface compatibility marker: def _rewrite_git_push_force is loaded
# into this facade from ``_bash_safety_parts.rewrite_citation``.
# Historical staged-test loaders also select this entry point by these names:
# def _apply_destructive_citation_gate — implementation in rewrite_citation.py.
# def _apply_fact_gate — implementation in fact_canonical.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

_PARTS: Tuple[str, ...] = (
    "normalization", "rewrite_citation", "fact_state", "fact_canonical",
    "posture_tables", "posture_parser", "posture_scan", "decisions_cli",
)


def _install_parts() -> None:
    """Execute ordered, inspectable source fragments in this namespace.

    The fragments contain ordinary Python declarations, not proxy exports.
    Compiling them once with this dictionary preserves historical lookup of
    helpers and constants through the facade, including test monkeypatches.
    Their own filenames stay in code objects for ``inspect.getsource``.
    """
    namespace = globals()
    parts_dir = Path(__file__).resolve().parent / "_lib" / "_bash_safety_parts"
    for part_name in _PARTS:
        part_path = parts_dir / (part_name + ".py")
        source = part_path.read_text(encoding="utf-8")
        exec(compile(source, str(part_path), "exec"), namespace, namespace)


_install_parts()
