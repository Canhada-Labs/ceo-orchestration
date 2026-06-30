#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAN-068 v2 Phase 1 production — aggregate-changesets.py.

Promotes the validated PoC at
``.claude/plans/PLAN-068/phase-0-5-poc/aggregate-changesets.py`` (verdict
GO, 9/9 tests pass) to a production helper under ``.claude/scripts/``.

LOCAL_ONLY: true
    The aggregator runs LOCAL-ONLY at closeout. CI does NOT run this in
    write mode; ``release.yml`` reads CHANGELOG.md via the inline grep at
    ``release.yml:133`` (``^## \\[VERSION\\]``). CI may invoke
    ``--check`` to guard against orphaned ``.changeset/*.md`` accumulation
    pre-tag (advisory; non-blocking unless wired by separate ceremony).

Stdlib only. Python >= 3.9. fail-CLOSED on any malformed input.

CLI:
  aggregate-changesets.py --version <X.Y.Z> --date <YYYY-MM-DD>
                          [--dry-run] [--changeset-dir <path>]
                          [--changelog <path>]
  aggregate-changesets.py --check [--changeset-dir <path>]

Exit codes:
  0  success / no-op / idempotent / no orphans
  1  --check found `.changeset/*.md` (orphans present without --version)
  2  invalid CLI arguments
  3  malformed changeset (fail-CLOSED)
  4  reserved (no current use; previously planned for orphan-pre-tag)

Hardenings vs the PoC (per bench-results.md §5):

  1. Stable secondary sort key (``p.name``) AFTER ``mtime`` so output is
     deterministic on coarse-mtime filesystems.
  2. ``--check`` mode for CI/closeout orphan-guard (returns rc=1 if any
     ``.changeset/*.md`` exist without ``--version``).
  3. ``LOCAL_ONLY: true`` notice in module docstring + soft warning on
     stderr if ``CI=true``. Does NOT block; just informs.
  4. Reuses the ``make_version_regex()`` helper verbatim from PoC. The
     regex matches the literal grep at ``release.yml:133``.
  5. Idempotency preserved: if CHANGELOG already contains ``## [VERSION]``
     exit 0 without re-inserting or deleting consumed files.

Behavior:
  1. List ``<changeset-dir>/*.md`` excluding ``README.md`` and
     ``config.json``.
  2. Parse YAML-frontmatter (a single ``--- ... ---`` block at top).
     Required: ``type: <patch|minor|major>``. Body: lines after the
     closing ``---``.
     Fail-CLOSED on: missing frontmatter, missing ``type``, illegal
     ``type`` value, multi-doc YAML, empty body.
  3. Aggregate into ``## [<version>] - <date>`` block with one bullet
     per changeset (sorted by ``(mtime, name)`` ascending → deterministic
     order even on coarse-mtime FS).
  4. Insert new block at the FIRST occurrence of
     ``^## \\[<digit>`` in the CHANGELOG (above the latest tagged
     version block).
  5. Delete consumed ``.changeset/*.md`` files (unless ``--dry-run``).
  6. Empty changeset dir → exit 0 (no-op idempotent).
  7. Idempotency: if CHANGELOG already contains ``## [<version>]``,
     exit 0 (no-op) without re-inserting or deleting.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

ALLOWED_TYPES = frozenset({"patch", "minor", "major"})
ALLOWED_FRONTMATTER_KEYS = frozenset({"type"})
SKIP_FILENAMES = frozenset({"README.md", "config.json"})


def make_version_regex(version: str) -> "re.Pattern[str]":
    """Return a regex equivalent to ``release.yml:133`` ``grep -qE "^## \\[VERSION\\]"``.

    Literal ``[`` / ``]`` are escaped via ``re.escape``; the ``\\.``
    escape on the dots in ``X.Y.Z`` is implicit in ``re.escape``.
    """
    return re.compile(r"^## \[" + re.escape(version) + r"\]", re.MULTILINE)


# Matches any tagged version block: ## [X.Y.Z] or ## [X.Y.Z-rc.N]
ANY_VERSION_BLOCK_RE = re.compile(
    r"^## \[\d+\.\d+\.\d+(?:-rc\.\d+)?\]", re.MULTILINE
)


class ChangesetError(Exception):
    """Fail-CLOSED on any invalid changeset input."""


def parse_changeset(path: Path) -> Tuple[str, str]:
    """Return ``(type, body)``. Fail-CLOSED on any malformed input."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ChangesetError(
            f"{path.name}: missing leading frontmatter delimiter `---`"
        )
    rest = text[4:]
    end_idx = rest.find("\n---\n")
    if end_idx < 0:
        # Maybe file ends with `---` on the last line (no trailing newline).
        end_idx = rest.find("\n---")
        if end_idx < 0 or rest[end_idx + 4 :].strip() not in ("", "\n"):
            raise ChangesetError(
                f"{path.name}: missing closing frontmatter delimiter `---`"
            )
    fm_block = rest[:end_idx]
    body = rest[end_idx + len("\n---\n") :].strip()

    # Multi-doc detection: any additional `---` on its own line inside the body.
    if re.search(r"^---\s*$", body, re.MULTILINE):
        raise ChangesetError(
            f"{path.name}: multi-doc frontmatter not permitted"
        )

    # Parse frontmatter as `key: value` pairs (no nesting in PoC scope).
    fm: dict = {}
    for line in fm_block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ChangesetError(
                f"{path.name}: malformed frontmatter line: {line!r}"
            )
        key, _, value = stripped.partition(":")
        fm[key.strip()] = value.strip()

    if "type" not in fm:
        raise ChangesetError(
            f"{path.name}: required `type` field missing from frontmatter"
        )
    type_val = fm["type"]
    if type_val not in ALLOWED_TYPES:
        raise ChangesetError(
            f"{path.name}: type={type_val!r} not in {sorted(ALLOWED_TYPES)}"
        )
    # Exact-key check (Codex re-pass P2): contract says no extra keys.
    # `.changeset/README.md` documents `type:` as the ONLY frontmatter key.
    extra_keys = sorted(set(fm) - ALLOWED_FRONTMATTER_KEYS)
    if extra_keys:
        raise ChangesetError(
            f"{path.name}: unknown frontmatter key(s) {extra_keys}; "
            f"only {sorted(ALLOWED_FRONTMATTER_KEYS)} permitted"
        )
    if not body:
        raise ChangesetError(f"{path.name}: empty body")

    return type_val, body


def list_changesets(changeset_dir: Path) -> List[Path]:
    """Return changeset files sorted by ``(mtime, name)`` ascending.

    Hardening #1: secondary sort key ``p.name`` after ``mtime`` to
    guarantee deterministic ordering on coarse-mtime filesystems where
    two files created in the same second would otherwise collapse to
    insertion order.
    """
    if not changeset_dir.is_dir():
        return []
    out: List[Path] = []
    for entry in sorted(changeset_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if entry.name in SKIP_FILENAMES:
            continue
        out.append(entry)
    # Tuple sort: primary key mtime, secondary key name (deterministic
    # tie-break on coarse-mtime FS).
    out.sort(key=lambda p: (p.stat().st_mtime, p.name))
    return out


def render_block(version: str, date: str, entries: List[Tuple[str, str]]) -> str:
    """Render a ``## [version] - date`` block with one bullet per entry."""
    lines: List[str] = [f"## [{version}] - {date}", ""]
    # Group by type so output reads predictably for review.
    for tp in ("major", "minor", "patch"):
        bucket = [body for (t, body) in entries if t == tp]
        if not bucket:
            continue
        lines.append(f"### {tp.capitalize()}")
        lines.append("")
        for body in bucket:
            first_line = body.splitlines()[0]
            lines.append(f"- {first_line}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n\n"


def insert_block(changelog_text: str, block: str) -> str:
    """Insert ``block`` ABOVE the first existing ``## [<version>]`` heading.

    If no version heading exists at all, append to end (defensive — should
    never happen in real CHANGELOG).
    """
    m = ANY_VERSION_BLOCK_RE.search(changelog_text)
    if m is None:
        return changelog_text.rstrip() + "\n\n" + block
    insert_at = m.start()
    return changelog_text[:insert_at] + block + changelog_text[insert_at:]


def _maybe_warn_ci() -> None:
    """Hardening #3: soft stderr warning if running under CI.

    Does NOT block. Just informs the operator that this aggregator is
    LOCAL-ONLY by design and CI workflows should call ``--check`` only.
    """
    if os.environ.get("CI") == "true":
        print(
            "WARNING: aggregate-changesets.py runs LOCAL-ONLY by design; "
            "CI is for --check only",
            file=sys.stderr,
        )


def _run_check(changeset_dir: Path) -> int:
    """Hardening #2: ``--check`` mode.

    Returns 0 if no orphan changesets present, 1 if any are present.
    Used by CI/closeout to guard against forgetting to aggregate before
    a tag cut.
    """
    files = list_changesets(changeset_dir)
    if files:
        print(
            f"::error::{len(files)} orphan changeset(s) in {changeset_dir} "
            f"(run aggregate-changesets.py --version <X.Y.Z> --date <YYYY-MM-DD>)",
            file=sys.stderr,
        )
        for f in files:
            print(f"  - {f.name}", file=sys.stderr)
        return 1
    print(f"OK: no orphan changesets in {changeset_dir}.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="PLAN-068 production aggregate-changesets (LOCAL-ONLY)"
    )
    parser.add_argument(
        "--version", help="X.Y.Z target version (required unless --check)"
    )
    parser.add_argument(
        "--date", help="YYYY-MM-DD (required unless --check)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if `.changeset/*.md` orphans are present",
    )
    parser.add_argument(
        "--changeset-dir", default=".changeset", help="path to .changeset/"
    )
    parser.add_argument(
        "--changelog", default="CHANGELOG.md", help="path to CHANGELOG.md"
    )
    args = parser.parse_args(argv)

    _maybe_warn_ci()

    changeset_dir = Path(args.changeset_dir)

    # Hardening #2: --check short-circuit (no version/date required).
    if args.check:
        return _run_check(changeset_dir)

    # Aggregate-mode argument validation
    if not args.version:
        print("::error::--version is required (unless --check)", file=sys.stderr)
        return 2
    if not args.date:
        print("::error::--date is required (unless --check)", file=sys.stderr)
        return 2

    if not re.match(r"^\d+\.\d+\.\d+(?:-rc\.\d+)?$", args.version):
        print(f"::error::invalid --version: {args.version!r}", file=sys.stderr)
        return 2
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        print(f"::error::invalid --date: {args.date!r}", file=sys.stderr)
        return 2

    changelog = Path(args.changelog)
    if not changelog.is_file():
        print(f"::error::CHANGELOG not found: {changelog}", file=sys.stderr)
        return 2

    files = list_changesets(changeset_dir)
    changelog_text = changelog.read_text(encoding="utf-8")

    # Hardening #5: idempotency gate. Already-aggregated → no-op.
    if make_version_regex(args.version).search(changelog_text):
        print(
            f"OK: CHANGELOG already contains '## [{args.version}]'; "
            f"no-op (idempotent)."
        )
        return 0

    if not files:
        print(
            f"OK: {changeset_dir} empty; no-op."
            if changeset_dir.exists()
            else f"OK: {changeset_dir} absent; no-op."
        )
        return 0

    # Parse all (fail-CLOSED on any malformed input).
    entries: List[Tuple[str, str]] = []
    for f in files:
        try:
            tp, body = parse_changeset(f)
        except ChangesetError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 3
        entries.append((tp, body))

    block = render_block(args.version, args.date, entries)
    new_text = insert_block(changelog_text, block)

    if args.dry_run:
        print(f"OK: dry-run; would insert {len(entries)} entries:")
        print("---BEGIN BLOCK---")
        sys.stdout.write(block)
        print("---END BLOCK---")
        return 0

    changelog.write_text(new_text, encoding="utf-8")
    for f in files:
        f.unlink()

    print(
        f"OK: aggregated {len(entries)} changeset(s) into "
        f"{changelog} as ## [{args.version}]; deleted consumed files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
