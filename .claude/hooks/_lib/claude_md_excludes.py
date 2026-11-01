"""Conservative checks for ``claudeMdExcludes`` and root instruction state.

Claude Code applies ``claudeMdExcludes`` globs to absolute paths.  This module
models path segments, including ``**`` as zero or more segments, rather than
inferring safety from a pattern's spelling: a checkout can itself live below a
staged-plan directory.  It does not claim full picomatch support (notably
braces, extglobs and negation); those forms are conservatively treated as a
possible root exclusion.

``root_instruction_load_state`` accepts a *complete, observed* collection of
loaded instruction paths.  It cannot infer an absent root from a static glob
or from one incremental hook event; callers without such a collection receive
``LOAD_STATE_UNOBSERVABLE``.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Iterable, Optional, Union


LOAD_STATE_LOADED = "root_loaded"
LOAD_STATE_ABSENT = "root_absent"
LOAD_STATE_UNOBSERVABLE = "root_load_unobservable"

_PathLike = Union[str, "Path"]


def _root_claude_md(project_dir: _PathLike) -> Path:
    return (Path(project_dir) / "CLAUDE.md").resolve()


def _has_unmodelled_syntax(pattern: str) -> bool:
    return any(token in pattern for token in ("{", "}", "(", ")", "!"))


def _segments_match(path: tuple, pattern: tuple) -> bool:
    """Match ``*`` within one segment and ``**`` across zero or more."""
    if not pattern:
        return not path
    head, tail = pattern[0], pattern[1:]
    if head == "**":
        return _segments_match(path, tail) or bool(path) and _segments_match(
            path[1:], pattern
        )
    return bool(path) and fnmatch.fnmatchcase(path[0], head) and _segments_match(
        path[1:], tail
    )


def root_claude_md_excluded(patterns: Any, project_dir: _PathLike) -> bool:
    """Whether an effective excludes array matches the real root CLAUDE.md.

    Non-list values are malformed settings, not evidence of an exclusion.
    A relative ``CLAUDE.md`` does not match, matching the documented absolute
    evaluation surface.  Unsupported glob syntax is flagged rather than
    treated as harmless.
    """
    if not isinstance(patterns, (list, tuple)):
        return False
    root_path = tuple(_root_claude_md(project_dir).as_posix().split("/"))
    for pattern in patterns:
        if isinstance(pattern, str) and pattern:
            normalized = pattern.replace("\\", "/")
            if _has_unmodelled_syntax(normalized) or _segments_match(
                root_path, tuple(normalized.split("/"))
            ):
                return True
    return False


def root_instruction_load_state(
    loaded_instruction_paths: Optional[Iterable[Any]], project_dir: _PathLike,
) -> str:
    """Classify root loading from a complete observed path collection.

    ``None``, a stream/iterator, malformed collections, or non-absolute
    entries are explicitly unobservable.  All entries are validated before a
    loaded result is returned, preventing a partial event stream from becoming
    false proof that the root was loaded or skipped.
    """
    if not isinstance(loaded_instruction_paths, (list, tuple, set, frozenset)):
        return LOAD_STATE_UNOBSERVABLE
    root_path = _root_claude_md(project_dir)
    root_loaded = False
    for entry in loaded_instruction_paths:
        if not isinstance(entry, (str, Path)):
            return LOAD_STATE_UNOBSERVABLE
        candidate = Path(entry)
        if not candidate.is_absolute():
            return LOAD_STATE_UNOBSERVABLE
        if candidate.resolve() == root_path:
            root_loaded = True
    return LOAD_STATE_LOADED if root_loaded else LOAD_STATE_ABSENT
