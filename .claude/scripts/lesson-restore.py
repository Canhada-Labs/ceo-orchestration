#!/usr/bin/env python3
"""lesson-restore — restore a previously archived lesson (PLAN-008 Phase 4b).

Companion to `prune-lessons.py --execute`. Moves a lesson JSON from
`lessons/archive/<date>/` back to the active lessons directory, strips
the `archived_at`/`original_path` metadata, and emits `lesson_restored`.

## Usage

    python3 .claude/scripts/lesson-restore.py <lesson_id> [--base-dir DIR]
    python3 .claude/scripts/lesson-restore.py --list
    python3 .claude/scripts/lesson-restore.py --list --json

## Exit codes

- 0 — restored (or listed) successfully
- 2 — invalid args
- 3 — lesson not found in any archive date dir
- 4 — a live lesson with that id already exists (refuse to overwrite)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import lessons as _lessons  # noqa: E402

_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.audit_emit import emit_lesson_restored as _emit_lesson_restored
    _AUDIT_EMIT_AVAILABLE = True
except ImportError:
    _AUDIT_EMIT_AVAILABLE = False


def _archive_root(base_dir: Optional[str]) -> Path:
    return _lessons._lessons_dir(base_dir) / "archive"


def _find_archived(lesson_id: str, base_dir: Optional[str]) -> Optional[Path]:
    """Search across all date subdirectories for <lesson_id>.json."""
    root = _archive_root(base_dir)
    if not root.is_dir():
        return None
    for date_dir in sorted(root.iterdir()):
        if not date_dir.is_dir():
            continue
        candidate = date_dir / f"{lesson_id}.json"
        if candidate.is_file():
            return candidate
    return None


def list_archived(base_dir: Optional[str] = None) -> List[dict]:
    """Return a flat list of {lesson_id, archetype, date, archive_path}."""
    root = _archive_root(base_dir)
    out: List[dict] = []
    if not root.is_dir():
        return out
    for date_dir in sorted(root.iterdir()):
        if not date_dir.is_dir():
            continue
        for f in sorted(date_dir.iterdir()):
            if f.suffix != ".json":
                continue
            if f.name.startswith("prune-receipt-"):
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            out.append({
                "lesson_id": data.get("lesson_id", f.stem),
                "archetype": data.get("archetype", ""),
                "archived_at": data.get("archived_at", ""),
                "archive_date": date_dir.name,
                "archive_path": str(f),
            })
    return out


def restore_one(lesson_id: str, base_dir: Optional[str] = None) -> int:
    """Perform the restore. Returns exit code."""
    archived = _find_archived(lesson_id, base_dir)
    if archived is None:
        print(f"ERROR: no archived lesson with id {lesson_id!r}", file=sys.stderr)
        return 3

    dst = _lessons._lessons_dir(base_dir) / f"{lesson_id}.json"
    if dst.exists():
        print(
            f"ERROR: live lesson {lesson_id!r} already exists at {dst}\n"
            f"Restore refuses to overwrite. Remove or rename the live copy first.",
            file=sys.stderr,
        )
        return 4

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Strip archive metadata before restoring
    data = json.loads(archived.read_text(encoding="utf-8"))
    archetype = data.get("archetype", "")
    data.pop("archived_at", None)
    data.pop("original_path", None)
    tmp = dst.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dst)
    archived.unlink()

    if _AUDIT_EMIT_AVAILABLE:
        try:
            _emit_lesson_restored(
                lesson_id=lesson_id,
                archetype=archetype,
                restored_from=str(archived),
                restored_to=str(dst),
            )
        except Exception:
            pass

    print(f"Restored {lesson_id} -> {dst}")
    return 0


def main(argv=None) -> int:
    """CLI entrypoint — restore an archived lesson from the pruning bin."""
    parser = argparse.ArgumentParser(
        description="Restore an archived lesson back to active lessons/.",
    )
    parser.add_argument("lesson_id", nargs="?", default=None,
                        help="Lesson ID to restore (omit with --list)")
    parser.add_argument("--list", action="store_true",
                        help="List all archived lessons instead of restoring")
    parser.add_argument("--base-dir", default=None,
                        help="Override lessons directory (testing)")
    parser.add_argument("--json", action="store_true",
                        help="JSON output for --list")
    args = parser.parse_args(argv)

    if args.list:
        entries = list_archived(args.base_dir)
        if args.json:
            print(json.dumps({"archived": entries}, indent=2, ensure_ascii=False))
        else:
            if not entries:
                print("No archived lessons.")
                return 0
            print(f"Archived lessons: {len(entries)}")
            for e in entries:
                print(f"  {e['lesson_id']}  archetype={e['archetype']}  "
                      f"date={e['archive_date']}")
        return 0

    if not args.lesson_id:
        parser.error("lesson_id required unless --list")

    return restore_one(args.lesson_id, args.base_dir)


if __name__ == "__main__":
    sys.exit(main())
