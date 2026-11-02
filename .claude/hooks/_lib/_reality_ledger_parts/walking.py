"""Reality ledger: walking."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _is_excluded(path: Path, *, repo_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except (ValueError, OSError):
        return True
    rel_posix = str(rel).replace(os.sep, "/")
    if path.name in SELF_EXCLUDE_BASENAMES:
        return True
    for frag in SELF_EXCLUDE_PATH_FRAGMENTS:
        if frag in ("/" + rel_posix):
            return True
    # Hidden directories beyond .claude / .github should be ignored
    parts = rel.parts
    for p in parts[:-1]:
        if p.startswith(".") and p not in (".claude", ".github"):
            return True
    return False


def _iter_python_files(roots: Iterable[Path], *, repo_root: Path) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.py")):
            if _is_excluded(p, repo_root=repo_root):
                continue
            out.append(p)
    return out


def _iter_md_files(roots: Iterable[Path], *, repo_root: Path) -> List[Path]:
    out: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if _is_excluded(p, repo_root=repo_root):
                continue
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Detector #1 — runtime_read_missing (AST-level)
# ---------------------------------------------------------------------------


__all__ = ['_is_excluded', '_iter_python_files', '_iter_md_files']
