#!/usr/bin/env python3
"""Validate ceo-restore archive members and extract the accepted ones.

``<tarball>`` checks every member (exit 2 on the first refused one);
``<tarball> <stage-dir>`` also writes ONLY the accepted members there, so the
preview and the apply of ceo-restore.sh share one rule and one extraction.

The archive must parse to its end: tarfile stops listing members, with no
error, at a truncated or invalid header, so the member list must end on an
end-of-archive (all-zero) block and the compressed stream must read cleanly
to its end.  Two members with the same name are refused, and so are the key
files ``audit/audit-key`` and ``audit/.salt`` in any letter case (the default
macOS disk, APFS, ignores case).  Every sparse member is refused, an
AppleDouble one included, before anything is written.

macOS tar writes an AppleDouble member ``._<name>`` (extended-attribute
metadata) before each entry that carries extended attributes.  It is SKIPPED
-- checked, never written -- only when it is a regular file whose companion
(same directory, basename without ``._``; the companion of ``._.`` is the
directory itself) is an accepted member.  Every other ``._`` member is refused.
"""
from __future__ import annotations

import os
import shutil
import sys
import tarfile
import zlib
from typing import Iterable, List, Optional, Tuple

_APPLEDOUBLE_PREFIX = "._"
_KEY_FILES = ("audit/audit-key", "audit/.salt")
_CHUNK = 1 << 16


def _normalized(name: str) -> str:
    """Return an archive-relative name or raise for an alias/traversal."""
    if name == ".":
        return ""
    if name.startswith("./"):
        name = name[2:]
    if not name or name.startswith("/") or "//" in name:
        raise ValueError("unsafe path")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("unsafe path")
    return name.rstrip("/")


def _allowed(name: str) -> bool:
    if name in ("agent-metrics.md", "MANIFEST.txt"):
        return True
    return name in ("audit", "memory", "plans") or any(
        name.startswith(prefix) for prefix in ("audit/", "memory/", "plans/")
    )


def _appledouble_companion(name: str) -> Optional[str]:
    """Return the companion of an AppleDouble name, None for any other name.

    Raises ValueError when the basename carries the prefix but cannot name a
    companion (``._`` alone, ``._..``).
    """
    head, _, base = name.rpartition("/")
    if not base.startswith(_APPLEDOUBLE_PREFIX):
        return None
    target = base[len(_APPLEDOUBLE_PREFIX):]
    if target == ".":
        return head
    if target in ("", ".."):
        raise ValueError("no companion")
    return head + "/" + target if head else target


def validate(members: Iterable[tarfile.TarInfo]) -> List[tarfile.TarInfo]:
    """Reject every non-data member and every name outside the restore layout.

    Returns the members to extract, in archive order.  AppleDouble members
    that pass the companion rule are left out of the result.
    """
    accepted: List[tarfile.TarInfo] = []
    accepted_names = set()
    seen = set()
    appledouble: List[Tuple[tarfile.TarInfo, str]] = []
    for member in members:
        try:
            name = _normalized(member.name)
        except ValueError:
            raise ValueError("refused path: {0}".format(member.name))
        if name in seen:
            raise ValueError("refused duplicate path: {0}".format(member.name))
        seen.add(name)
        if member.issparse():
            raise ValueError("refused sparse member: {0}".format(member.name))
        try:
            companion = _appledouble_companion(name) if name else None
        except ValueError:
            raise ValueError("refused AppleDouble name: {0}".format(member.name))
        if companion is not None:
            if not member.isfile():
                raise ValueError("refused member type: {0}".format(member.name))
            appledouble.append((member, companion))
            continue
        if not name:
            if member.isdir():
                accepted.append(member)
                accepted_names.add(name)
                continue
            raise ValueError("refused member type: {0}".format(member.name))
        if not _allowed(name):
            raise ValueError("refused path: {0}".format(member.name))
        if not (member.isfile() or member.isdir()):
            raise ValueError("refused member type: {0}".format(member.name))
        if name.casefold() in _KEY_FILES:
            raise ValueError("refused path: {0}".format(member.name))
        accepted.append(member)
        accepted_names.add(name)
    for member, companion in appledouble:
        if companion not in accepted_names:
            raise ValueError("refused path: {0}".format(member.name))
    return accepted


def complete_members(archive: tarfile.TarFile) -> List[tarfile.TarInfo]:
    """Return every member, or raise unless the archive parsed to its end.

    The member walk must stop on a full all-zero block (the end-of-archive
    marker) and the rest of the compressed stream must decompress with a
    valid checksum; otherwise members after the cut would vanish silently.
    """
    stream = archive.fileobj
    try:
        members = archive.getmembers()
        stream.seek(archive.offset)
        block = stream.read(tarfile.BLOCKSIZE)
        while stream.read(_CHUNK):
            pass
    except (EOFError, OSError, tarfile.ReadError, zlib.error) as exc:
        raise ValueError("refused truncated or corrupt archive: {0}".format(exc))
    if len(block) != tarfile.BLOCKSIZE or block.count(b"\0") != tarfile.BLOCKSIZE:
        raise ValueError("refused truncated or corrupt archive: no end-of-archive "
                         "block at byte {0}".format(archive.offset))
    return members


def extract(archive: tarfile.TarFile, members: Iterable[tarfile.TarInfo],
            stage: str) -> None:
    """Write the given (already validated) members under ``stage``."""
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    for member in members:
        name = _normalized(member.name)
        if not name:
            continue
        path = os.path.join(stage, *name.split("/"))
        if member.isdir():
            os.makedirs(path, exist_ok=True)
            continue
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise ValueError("refused member type: {0}".format(member.name))
        # O_EXCL: a name that lands on a file already written (two members
        # whose names differ only in letter case, on the default macOS disk,
        # APFS) is refused, never merged into the earlier file with the
        # earlier mode.
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                         member.mode & 0o777)
        except FileExistsError:
            source.close()
            raise ValueError("refused duplicate path: {0}".format(member.name))
        with os.fdopen(fd, "wb") as target, source:
            shutil.copyfileobj(source, target)
        os.utime(path, (member.mtime, member.mtime))


def main(argv: List[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: _restore_archive.py <tarball> [<stage-dir>]", file=sys.stderr)
        return 2
    stage = argv[2] if len(argv) == 3 else None
    if stage is not None and (os.path.islink(stage) or not os.path.isdir(stage)):
        print("fatal: stage must be a real directory", file=sys.stderr)
        return 2
    try:
        with tarfile.open(argv[1], "r:gz") as archive:
            members = validate(complete_members(archive))
            if stage is not None:
                extract(archive, members, stage)
    except (EOFError, OSError, OverflowError, tarfile.TarError, ValueError,
            zlib.error) as exc:
        print("fatal: archive {0}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
