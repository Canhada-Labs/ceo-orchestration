"""Byte-preserving inventory for the Rule 1 contamination scanner.

Git is the authority for both the tracked name and its mode.  Keeping its
NUL-delimited output as bytes prevents an undecodable path from becoming a
different, non-existent pathname before the policy has inspected it.
"""
from __future__ import annotations

import errno
import os
import stat
import subprocess
import unicodedata
from pathlib import Path
from typing import Callable, List, Pattern, Tuple


_BLOB_MODES = frozenset({"100644", "100755", "120000"})
_GITLINK_MODE = "160000"
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_NONBLOCK = getattr(os, "O_NONBLOCK", 0)


class RuleOneInputError(Exception):
    """An indexed Rule 1 subject could not be verified."""


def _index(repo_root: Path) -> List[Tuple[str, bytes]]:
    """Return strict UTF-8 paths and index modes, refusing malformed names."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", "-z"], cwd=str(repo_root),
            capture_output=True, check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuleOneInputError("cannot enumerate the git index") from exc
    if result.returncode != 0:
        raise RuleOneInputError("git ls-files -s failed")
    entries = []
    for row in result.stdout.split(b"\0"):
        if not row:
            continue
        head, separator, raw_name = row.partition(b"\t")
        if not separator:
            raise RuleOneInputError("malformed git index entry")
        try:
            name = raw_name.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuleOneInputError(
                "a tracked Rule 1 path is not valid UTF-8") from None
        mode = head.split(b" ", 1)[0].decode("ascii")
        entries.append((mode, name.encode("utf-8")))
    return entries


def _read_regular(path: Path) -> bytes:
    """Read a regular blob without following a link swapped in after git."""
    fd = os.open(str(path), os.O_RDONLY | _NOFOLLOW | _NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(errno.EINVAL, "tracked blob is not a regular file")
        chunks = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                return b"".join(chunks)
            chunks.append(block)
    finally:
        os.close(fd)


def _blob(path: Path, mode: str) -> bytes:
    """Read link payloads as payloads; never follow a tracked symlink."""
    if mode == "120000":
        try:
            return os.fsencode(os.readlink(path))
        except OSError as exc:
            raise RuleOneInputError(
                "cannot read a tracked symlink payload") from exc
    try:
        return _read_regular(path)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            try:
                return os.fsencode(os.readlink(path))
            except OSError as link_error:
                raise RuleOneInputError(
                    "cannot read a tracked symlink payload") from link_error
        raise RuleOneInputError("cannot read a tracked Rule 1 blob") from exc


def scan_rule_one(
    repo_root: Path,
    pattern: Pattern[str],
    allowlisted: Callable[[Path], bool],
    never_allowlisted: Callable[[str], bool],
) -> List[Path]:
    """Scan tracked Rule 1 blobs, with gitlinks as the sole mode exemption."""
    violations = []
    for mode, raw_name in _index(repo_root):
        name = raw_name.decode("utf-8")
        if mode == _GITLINK_MODE:
            continue
        if mode not in _BLOB_MODES:
            raise RuleOneInputError(
                "tracked Rule 1 entry has an unsupported mode")
        path = repo_root / name
        if allowlisted(path) and not never_allowlisted(name):
            continue
        raw = _blob(path, mode)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            if never_allowlisted(name):
                violations.append(path)
            continue
        if pattern.search(unicodedata.normalize("NFKC", text)):
            violations.append(path)
    return violations
