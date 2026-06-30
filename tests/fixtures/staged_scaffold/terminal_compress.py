"""PLAN-046 Cluster 1.5 — rtk terminal compression passthrough.

**Staged scaffold**. Destination path
``.claude/hooks/_lib/terminal_compress.py`` is canonical-guarded by
``check_canonical_edit.py``; Owner-signed sentinel (future round) is
required to promote this file there.

Compresses terminal output capture before it is fed back to an LLM
as tool-result context. Three passes: ANSI escape strip, whitespace
normalization, and repeated-prefix collapse (for `ls -l`, `ps ax`,
numbered lists, etc.).

Contract
--------
``compress(text: str) -> str`` — returns a smaller, LLM-friendly
version of the input; operation is lossy by design but preserves
semantic information (paths, identifiers, numbers).

Config (env)
------------
``CEO_TERMINAL_COMPRESS`` in {``on`` (default), ``off``}.
``CEO_TERMINAL_COMPRESS_COLLAPSE`` in {``on`` (default), ``off``}
— controls the repeated-prefix collapse pass specifically (more
aggressive).

Kill-switch: ``CEO_TERMINAL_COMPRESS=off``.

Clean-room declaration
----------------------
No code is lifted from rtk or any other upstream library. The
implementation is a handful of regex rules around stdlib `re` +
`collections`. The concept of "ANSI-strip + prefix-collapse" is
general and attribution-free.
"""
from __future__ import annotations

import os
import re
from typing import List, Tuple

_ENV_VAR = "CEO_TERMINAL_COMPRESS"
_ENV_VAR_COLLAPSE = "CEO_TERMINAL_COMPRESS_COLLAPSE"
_ANSI_ESCAPE_RE = re.compile(r"\x1B(?:\[[0-?]*[ -/]*[@-~]|[@-Z\\-_])")
_TRAILING_WS_RE = re.compile(r"[ \t]+$", flags=re.MULTILINE)
_REPEATED_BLANK_RE = re.compile(r"\n{3,}")
_BOX_DRAWING_RE = re.compile(r"[─-╿]+")

# Prefix-collapse: group lines that share a long common prefix, replace
# the middle block with a summary row. Used for `ls -l` like output.
_COLLAPSE_MIN_GROUP = 4
_COLLAPSE_MIN_PREFIX_LEN = 6


def _enabled() -> bool:
    return os.environ.get(_ENV_VAR, "on").lower().strip() != "off"


def _collapse_enabled() -> bool:
    return os.environ.get(_ENV_VAR_COLLAPSE, "on").lower().strip() != "off"


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences and box-drawing runs."""
    no_ansi = _ANSI_ESCAPE_RE.sub("", text)
    return _BOX_DRAWING_RE.sub(" ", no_ansi)


def _normalize_whitespace(text: str) -> str:
    """Trim trailing spaces per line and collapse 3+ blank lines to 2."""
    text = _TRAILING_WS_RE.sub("", text)
    text = _REPEATED_BLANK_RE.sub("\n\n", text)
    return text


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def _collapse_prefix_groups(text: str) -> str:
    """Replace long runs of lines sharing a common prefix with a summary.

    Example input (one group, 6 lines):
        -rw-r--r--  1 u  staff    1 Apr 21  file1.py
        -rw-r--r--  1 u  staff    2 Apr 21  file2.py
        ... (4 more) ...

    Becomes:
        -rw-r--r--  1 u  staff    1 Apr 21  file1.py
        [...4 lines with similar prefix elided by terminal_compress...]
        -rw-r--r--  1 u  staff    7 Apr 21  file7.py
    """
    if not _collapse_enabled():
        return text
    lines = text.split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        # Look ahead for a run of lines that share a long common prefix.
        j = i
        prefix = lines[i]
        while j + 1 < len(lines):
            shared = _common_prefix_len(prefix, lines[j + 1])
            if shared < _COLLAPSE_MIN_PREFIX_LEN:
                break
            prefix = prefix[:shared]
            j += 1
        group_size = j - i + 1
        if group_size >= _COLLAPSE_MIN_GROUP and len(prefix) >= _COLLAPSE_MIN_PREFIX_LEN:
            out.append(lines[i])
            elided = group_size - 2
            out.append(
                f"[...{elided} lines with similar prefix elided by "
                f"terminal_compress...]"
            )
            out.append(lines[j])
            i = j + 1
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)


def compress(text: str) -> str:
    """Run all passes. Returns ``text`` unchanged when disabled."""
    if not isinstance(text, str):
        raise TypeError("compress() requires str input")
    if not _enabled():
        return text
    if not text:
        return ""
    stripped = _strip_ansi(text)
    normalized = _normalize_whitespace(stripped)
    collapsed = _collapse_prefix_groups(normalized)
    return collapsed


def ratio(original: str, compressed: str) -> float:
    """Return the savings ratio in [0, 1]. Helpful for tests + telemetry."""
    if not original:
        return 0.0
    return max(0.0, 1.0 - (len(compressed) / len(original)))
