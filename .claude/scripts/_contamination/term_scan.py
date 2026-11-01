"""Term-rule implementation shared by the contamination command facade.

Dependencies are arguments rather than imports from the facade.  This keeps
the historical module-level patch points (notably ``FileWalker``) effective.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Callable, List, Set, Type


def find_violations(
    repo_root: Path,
    pattern,
    walker_type: Type[object],
    allowlist_exact: Set[str],
    allowlist_globs: Set[str],
    skip_suffixes: Set[str],
    never_allowlisted: Callable[[str], bool],
) -> List[Path]:
    """Apply the term rule and return tracked files that violate it.

    ``walker_type`` is injected on every call so a consumer patching the
    public facade sees the same behaviour it saw before this extraction.
    """
    walker = walker_type(
        repo_root=repo_root,
        mode="git",
        path_allowlist_exact=allowlist_exact,
        path_allowlist_globs=allowlist_globs,
    )
    violations: List[Path] = []
    for path in walker.iter_files():
        if path.suffix.lower() in skip_suffixes:
            continue
        try:
            rel = path.relative_to(walker.repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        if walker.is_allowlisted(path) and not never_allowlisted(rel):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            if never_allowlisted(rel):
                violations.append(path)
            continue
        if pattern.search(unicodedata.normalize("NFKC", text)):
            violations.append(path)
    return violations
