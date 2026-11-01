"""Term-rule implementation shared by the contamination command facade.

Dependencies are arguments rather than imports from the facade.  This keeps
the historical module-level patch points (notably ``FileWalker``) effective.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Set, Type

from _contamination_inventory import scan_rule_one


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
    return scan_rule_one(
        repo_root=walker.repo_root,
        pattern=pattern,
        allowlisted=walker.is_allowlisted,
        never_allowlisted=never_allowlisted,
    )
