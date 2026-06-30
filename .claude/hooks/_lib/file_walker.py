"""Shared file walker — iteration + allowlist for governance checks.

Sprint 3 Item E. Consolidates the divergent file-walking logic in
`check-tier-boundaries.py` (filesystem rglob) and `check-contamination.sh`
(git ls-files), exposing a single API:

    walker = FileWalker(
        repo_root=Path("."),
        mode="filesystem" | "git",
        suffixes={".md", ".yaml"},
        skip_subdir_names={"benchmarks"},
        path_allowlist_exact={"LICENSE"},
        path_allowlist_globs={".claude/skills/domains/*"},
        path_allowlist_tokens={"frontend/frontend-data-layer/SKILL.md"},
    )
    for path in walker.iter_files():
        ...
    if walker.is_allowlisted(path):
        ...

## Design principles

1. **stdlib only** — Python >= 3.9, no external deps.
2. **Fail-safe** — a git command failure does not crash the walker;
   the caller handles empty iteration.
3. **Unified allowlist** — three styles of allowlist entry (exact
   path, glob pattern, substring token) can be mixed. `is_allowlisted`
   returns True if ANY style matches.
4. **Mode-specific collection, mode-agnostic filtering** — the walker
   gathers candidate paths differently in git vs filesystem mode, but
   applies the same filtering pipeline.

## Modes

- `"filesystem"` — uses `Path.rglob()` starting from `repo_root`.
  Respects `suffixes` and `skip_subdir_names`. Used by tier-boundaries.
- `"git"` — runs `git ls-files -z` from `repo_root`. Returns all
  tracked files; `.gitignore` is honored by git itself. Used by
  contamination check.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Iterable, Iterator, Optional, Set


class FileWalker:
    """Unified file iterator + allowlist applier."""

    def __init__(
        self,
        repo_root: Path,
        mode: str = "filesystem",
        suffixes: Optional[Set[str]] = None,
        skip_subdir_names: Optional[Set[str]] = None,
        path_allowlist_exact: Optional[Set[str]] = None,
        path_allowlist_globs: Optional[Set[str]] = None,
        path_allowlist_tokens: Optional[Set[str]] = None,
    ) -> None:
        if mode not in {"filesystem", "git"}:
            raise ValueError(f"unknown walker mode: {mode!r}")
        self.repo_root = repo_root.resolve()
        self.mode = mode
        self.suffixes = suffixes or set()
        self.skip_subdir_names = skip_subdir_names or set()
        self.path_allowlist_exact = path_allowlist_exact or set()
        self.path_allowlist_globs = path_allowlist_globs or set()
        self.path_allowlist_tokens = path_allowlist_tokens or set()

    def iter_files(self) -> Iterator[Path]:
        """Yield candidate file paths (absolute). Honors mode + filters."""
        if self.mode == "git":
            yield from self._iter_git_tracked()
        else:
            yield from self._iter_filesystem()

    def _iter_git_tracked(self) -> Iterator[Path]:
        """Enumerate `git ls-files` output. Safe on missing git / bad repo."""
        try:
            proc = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=str(self.repo_root),
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return
        if proc.returncode != 0:
            return
        # -z emits NUL-separated paths
        raw = proc.stdout.decode("utf-8", errors="replace")
        for rel in raw.split("\x00"):
            if not rel:
                continue
            p = self.repo_root / rel
            if self.suffixes and p.suffix not in self.suffixes:
                continue
            yield p

    def _iter_filesystem(self) -> Iterator[Path]:
        """Walk repo_root via rglob. Skips subdirs in skip_subdir_names."""
        for p in self.repo_root.rglob("*"):
            if not p.is_file():
                continue
            if self.suffixes and p.suffix not in self.suffixes:
                continue
            # Skip if any ancestor directory name is in skip_subdir_names
            parts = set(p.relative_to(self.repo_root).parts[:-1])
            if self.skip_subdir_names and parts & self.skip_subdir_names:
                continue
            yield p

    def is_allowlisted(self, path: Path) -> bool:
        """Return True if `path` matches any allowlist style.

        Supports:
        - exact relative path match
        - glob against relative path (fnmatch)
        - substring token anywhere in the absolute path string
        """
        try:
            rel = str(path.relative_to(self.repo_root))
        except ValueError:
            rel = str(path)

        if rel in self.path_allowlist_exact:
            return True
        for pattern in self.path_allowlist_globs:
            if fnmatch.fnmatch(rel, pattern):
                return True
        abs_str = str(path)
        for token in self.path_allowlist_tokens:
            if token in abs_str:
                return True
        return False

    def iter_non_allowlisted(self) -> Iterable[Path]:
        """Convenience: iterate files that are NOT allowlisted."""
        for p in self.iter_files():
            if not self.is_allowlisted(p):
                yield p
