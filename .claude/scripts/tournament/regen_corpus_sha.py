#!/usr/bin/env python3
"""PLAN-045 F-10-06 — Regenerate the tournament fixture corpus SHA256 anchor.

Produces/updates ``.claude/scripts/tournament/fixtures/CORPUS_SHA256.txt``
with one ``<sha256>  <relpath>`` line per fixture, sorted by path so the
file is byte-deterministic.

The manifest is consumed by ``tier_policy_cli/learn.py::_verify_fixture_corpus``
on every run of the learner — any tamper in the training corpus produces
a fail-CLOSED ``sys.exit(1)`` with stderr explanation.

Usage::

    python3 .claude/scripts/tournament/regen_corpus_sha.py

Idempotent: running twice on unchanged fixtures yields byte-identical
output. Uses stdlib only (``hashlib.sha256`` + streaming 64 KiB reads).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import List, Tuple

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_MANIFEST_FILE = _FIXTURES_DIR / "CORPUS_SHA256.txt"

# File-types considered part of the corpus. `.txt` + `.md` are intentionally
# NOT tracked (README-like docs whose hash should not gate the learner).
_CORPUS_SUFFIXES = frozenset({".yaml", ".yml", ".json", ".jsonl"})

# Manifest filename itself must be skipped (don't hash-itself).
_MANIFEST_NAME = "CORPUS_SHA256.txt"


def sha256_file(path: Path, block_size: int = 64 * 1024) -> str:
    """Return lowercase-hex sha256 of *path* via streaming reads."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(block_size), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_corpus(fixtures_dir: Path) -> List[Tuple[str, str]]:
    """Return sorted list of ``(sha256_hex, relpath)`` for every corpus file."""
    if not fixtures_dir.is_dir():
        raise FileNotFoundError(f"fixtures dir not found: {fixtures_dir}")
    entries: List[Tuple[str, str]] = []
    for p in sorted(fixtures_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name == _MANIFEST_NAME:
            continue
        if p.suffix.lower() not in _CORPUS_SUFFIXES:
            continue
        rel = p.relative_to(fixtures_dir).as_posix()
        entries.append((sha256_file(p), rel))
    entries.sort(key=lambda e: e[1])
    return entries


def render_manifest(entries: List[Tuple[str, str]]) -> str:
    """Format the ``shasum -a 256 -c``-compatible manifest body."""
    lines = [
        "# PLAN-045 F-10-06 — tournament fixture corpus SHA256 anchor.",
        "# Regenerate via: python3 .claude/scripts/tournament/regen_corpus_sha.py",
        "# Consumed by tier_policy_cli/learn.py::_verify_fixture_corpus (fail-CLOSED on mismatch).",
        "# Compatible with `shasum -a 256 -c CORPUS_SHA256.txt` for manual checking.",
        "",
    ]
    for sha, rel in entries:
        lines.append(f"{sha}  {rel}")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    entries = collect_corpus(_FIXTURES_DIR)
    if not entries:
        print(
            f"No corpus files found under {_FIXTURES_DIR}",
            file=sys.stderr,
        )
        return 1
    body = render_manifest(entries)
    _MANIFEST_FILE.write_text(body, encoding="utf-8")
    print(f"wrote {_MANIFEST_FILE} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
