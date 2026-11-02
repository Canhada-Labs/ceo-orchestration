#!/usr/bin/env python3
"""Validate ceo-restore archive members before shell extraction."""
from __future__ import annotations

import sys
import tarfile
from typing import Iterable


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


def validate(members: Iterable[tarfile.TarInfo]) -> None:
    """Reject every non-data member and every name outside the restore layout."""
    for member in members:
        try:
            name = _normalized(member.name)
        except ValueError:
            raise ValueError("refused path: {0}".format(member.name))
        if not name:
            if member.isdir():
                continue
            raise ValueError("refused member type: {0}".format(member.name))
        if not _allowed(name):
            raise ValueError("refused path: {0}".format(member.name))
        if not (member.isfile() or member.isdir()):
            raise ValueError("refused member type: {0}".format(member.name))
        if name in ("audit/audit-key", "audit/.salt"):
            raise ValueError("refused path: {0}".format(member.name))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: _restore_archive.py <tarball>", file=sys.stderr)
        return 2
    try:
        with tarfile.open(argv[1], "r:gz") as archive:
            validate(archive.getmembers())
    except (OSError, tarfile.TarError, ValueError) as exc:
        print("fatal: archive {0}".format(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
