#!/usr/bin/env python3
"""Lesson pruning CLI — dry-run by default, --execute gated (Sprint 8 / 9).

PLAN-008 Phase 4 amends ADR-017. Sprint 6 shipped dry-run only.
Sprint 8 enables `--execute` behind safeguards (debate consensus C1):

- Opt-in env var `CEO_PRUNE_EXECUTE=1` required
- `--max-archive N` (default 3) caps archivals per invocation
- `--execute --plan-only` preview mode (no side effects; debate C9)
- Archive (never delete): lessons/archive/<YYYY-MM-DD>/<id>.json
- Per-batch `prune-receipt-<ISO>.json` in archive dir
- `lesson_archived` audit event per archive
- `lesson-restore.py` companion reverses the move

PLAN-009 Phase 2 C2.1 (ADR-020 supersedes ADR-017) exposes thresholds
as flags while preserving current behavior by default:

- `--min-miss-ratio FLOAT` (default 0.7 = previous `hit_rate < 0.3`)
- `--min-age-days INT` (default 0 = no age filter)
- `--min-archive-age-days INT` (default 0 = no archive-age filter)
- `--force-dangerous-threshold` required for `--min-miss-ratio < 0.1`

AND semantics: ALL filters must be true for a candidate to prune
(ADR-020 §Filter composition).

## Exit codes

- 0 — success (candidates listed for dry-run; archives performed for execute)
- 2 — invalid args
- 10 — --execute attempted without CEO_PRUNE_EXECUTE=1
- 11 — dangerous threshold without --force-dangerous-threshold (ADR-020)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import lessons as _lessons  # noqa: E402

_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.audit_emit import emit_lesson_archived as _emit_lesson_archived
    _AUDIT_EMIT_AVAILABLE = True
except ImportError:
    _AUDIT_EMIT_AVAILABLE = False


MIN_SAMPLE_SIZE = 5
MAX_HIT_RATE_FOR_PRUNE = 0.3
DEFAULT_MIN_MISS_RATIO = 0.7  # ADR-020 — equivalent to previous hit_rate < 0.3
DEFAULT_MIN_AGE_DAYS = 0  # ADR-020 — 0 = no filter (Sprint 9 back-compat)
DEFAULT_MIN_ARCHIVE_AGE_DAYS = 0  # ADR-020 — 0 = no filter
DANGEROUS_MIN_MISS_RATIO = 0.1  # ADR-020 safety guard threshold
DEFAULT_MAX_ARCHIVE = 3


def _parse_iso_utc(s: str) -> Optional[datetime]:
    """Parse an ISO 8601 UTC timestamp, returning None on any error."""
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _age_days(iso_ts: str, now: datetime) -> Optional[float]:
    """Age in days between `now` and an ISO 8601 timestamp.

    Returns None if the timestamp is unparseable — callers treat None
    as "age unknown" and apply the filter defensively (fail-open: don't
    prune if we can't date it).
    """
    dt = _parse_iso_utc(iso_ts)
    if dt is None:
        return None
    return (now - dt).total_seconds() / 86400.0


def find_candidates(
    base_dir: str = None,
    *,
    min_miss_ratio: float = DEFAULT_MIN_MISS_RATIO,
    min_age_days: int = DEFAULT_MIN_AGE_DAYS,
    min_archive_age_days: int = DEFAULT_MIN_ARCHIVE_AGE_DAYS,
    now: Optional[datetime] = None,
) -> List[Tuple[Any, float, int]]:
    """Return list of (Lesson, hit_rate, sample_size) meeting prune criteria.

    ADR-020 §Filter composition (PLAN-009 P2.1): all of the following
    must hold for a lesson to become a candidate:

    1. ``n >= MIN_SAMPLE_SIZE`` (5)
    2. ``miss_ratio >= min_miss_ratio``
    3. ``now - created_at >= min_age_days`` (if min_age_days > 0)
    4. ``now - last_outcome_at >= min_archive_age_days`` (if > 0)

    Conjunction — NOT disjunction. All filters must vote yes.

    `now` is injectable for testability.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    candidates = []
    for lesson in _lessons.list_lessons(base_dir):
        n = lesson.hit_count + lesson.miss_count
        if n < MIN_SAMPLE_SIZE:
            continue
        miss_ratio = lesson.miss_count / n if n > 0 else 0.0
        if miss_ratio < min_miss_ratio:
            continue
        # Age filter (created_at)
        if min_age_days > 0:
            age = _age_days(lesson.created_at, now)
            if age is None or age < min_age_days:
                continue
        # Archive-age filter (last_outcome_at)
        if min_archive_age_days > 0:
            outcome_age = _age_days(lesson.last_outcome_at, now)
            if outcome_age is None or outcome_age < min_archive_age_days:
                continue
        hit_rate = lesson.hit_count / n
        candidates.append((lesson, hit_rate, n))
    return candidates


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _archive_dir(base_dir: str = None) -> Path:
    """Return lessons/archive/<YYYY-MM-DD>/ ."""
    d = _lessons._lessons_dir(base_dir)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return d / "archive" / today


def _source_path(lesson, base_dir: str = None) -> Path:
    return _lessons._lessons_dir(base_dir) / f"{lesson.lesson_id}.json"


def archive_one(lesson, base_dir: str = None) -> Path:
    """Move a lesson JSON into the archive directory.

    Adds `archived_at` + `original_path` fields to the archived copy.
    Returns the destination path.
    """
    src = _source_path(lesson, base_dir)
    dst_dir = _archive_dir(base_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{lesson.lesson_id}.json"

    # Load, annotate, write-atomic
    data = json.loads(src.read_text(encoding="utf-8"))
    data["archived_at"] = _utc_now_iso()
    data["original_path"] = str(src)
    tmp = dst.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(dst)

    # Remove source only after archive write succeeds
    src.unlink()
    return dst


def write_receipt(archived: List[dict], base_dir: str = None) -> Path:
    """Write prune-receipt-<ISO>.json in the archive dir."""
    dst_dir = _archive_dir(base_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = _utc_now_iso().replace(":", "-")
    receipt = dst_dir / f"prune-receipt-{ts}.json"
    payload = {
        "created_at": _utc_now_iso(),
        "batch_size": len(archived),
        "archived": archived,
    }
    receipt.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return receipt


def _print_candidates(candidates, mode: str) -> None:
    print(f"Prune criteria: n >= {MIN_SAMPLE_SIZE} AND hit_rate < {MAX_HIT_RATE_FOR_PRUNE}")
    print(f"Mode: {mode}")
    print(f"Candidates: {len(candidates)}")
    print()
    for lesson, rate, n in candidates:
        print(f"  {lesson.lesson_id}  archetype={lesson.archetype}  "
              f"n={n}  hit_rate={rate:.2f}  "
              f"tags={','.join(lesson.scope_tags)}")
    if not candidates:
        print("  (none)")


def _build_arg_parser() -> argparse.ArgumentParser:
    """Construct the prune-lessons argparse tree (PLAN-023 Phase E split)."""
    parser = argparse.ArgumentParser(
        description=(
            "Lesson pruning CLI — dry-run by default; --execute gated. "
            "Thresholds flag-controlled per ADR-020 (supersedes ADR-017)."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="Identify candidates without archiving (default)")
    mode.add_argument("--execute", action="store_true",
                      help="Archive candidates (requires CEO_PRUNE_EXECUTE=1)")
    parser.add_argument("--plan-only", action="store_true",
                        help="With --execute: preview what would be archived, no side effects")
    parser.add_argument("--max-archive", type=int, default=DEFAULT_MAX_ARCHIVE,
                        help=f"Max archivals per invocation (default {DEFAULT_MAX_ARCHIVE})")
    # ADR-020 (PLAN-009 P2.1) — threshold flags
    parser.add_argument(
        "--min-miss-ratio", type=float, default=DEFAULT_MIN_MISS_RATIO,
        help=(
            f"Minimum miss/(hit+miss) ratio required to prune "
            f"(default {DEFAULT_MIN_MISS_RATIO} = previous hit_rate<0.3 "
            "threshold). See ADR-020."
        ),
    )
    parser.add_argument(
        "--min-age-days", type=int, default=DEFAULT_MIN_AGE_DAYS,
        help=(
            f"Minimum days since created_at (default "
            f"{DEFAULT_MIN_AGE_DAYS}; 0 = no filter). AND'd with other "
            "filters. See ADR-020."
        ),
    )
    parser.add_argument(
        "--min-archive-age-days", type=int, default=DEFAULT_MIN_ARCHIVE_AGE_DAYS,
        help=(
            f"Minimum days since last_outcome_at (default "
            f"{DEFAULT_MIN_ARCHIVE_AGE_DAYS}; 0 = no filter). AND'd "
            "with other filters. See ADR-020."
        ),
    )
    parser.add_argument(
        "--force-dangerous-threshold", action="store_true",
        help=(
            "Override the safety guard that rejects --min-miss-ratio "
            f"< {DANGEROUS_MIN_MISS_RATIO}. Use only when you understand "
            "that you are about to prune almost everything. ADR-020 §Guard."
        ),
    )
    parser.add_argument("--base-dir", default=None,
                        help="Override lessons directory (testing)")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of human-readable")
    return parser


def _check_safety_guard(args) -> int:
    """Return 0 if threshold is safe, or 11 if the dangerous guard fires."""
    if (
        args.min_miss_ratio < DANGEROUS_MIN_MISS_RATIO
        and not args.force_dangerous_threshold
    ):
        print(
            f"ERROR: --min-miss-ratio={args.min_miss_ratio} is below the "
            f"safety guard ({DANGEROUS_MIN_MISS_RATIO}). Pruning at this "
            "threshold removes lessons with any meaningful miss rate, "
            "which almost certainly includes healthy lessons. "
            "If you truly want this, pass --force-dangerous-threshold. "
            "See ADR-020 §Guard.",
            file=sys.stderr,
        )
        return 11
    return 0


def _render_dry_run(candidates, json_mode: bool) -> int:
    """Render dry-run output and return exit code 0."""
    if json_mode:
        out = _json_payload(candidates, mode="dry-run", archived=[], receipt=None)
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        _print_candidates(candidates, mode="dry-run (no changes)")
    return 0


def _check_execute_preconditions(args) -> int:
    """Validate CEO_PRUNE_EXECUTE env var + --max-archive. Return 0/2/10."""
    if os.environ.get("CEO_PRUNE_EXECUTE") != "1":
        print(
            "ERROR: --execute requires CEO_PRUNE_EXECUTE=1 environment variable.\n"
            "ADR-017 (amended Sprint 8) gates execute mode behind this opt-in\n"
            "to prevent unintended pruning. To enable for one invocation:\n"
            "    CEO_PRUNE_EXECUTE=1 python3 prune-lessons.py --execute --max-archive 3",
            file=sys.stderr,
        )
        return 10
    if args.max_archive < 0:
        print("ERROR: --max-archive must be >= 0", file=sys.stderr)
        return 2
    return 0


def _render_plan_only(to_process, candidates, args) -> int:
    """Render --plan-only preview and return exit code 0."""
    if args.json:
        print(json.dumps(
            _json_payload(to_process, mode="execute --plan-only", archived=[], receipt=None),
            indent=2, ensure_ascii=False,
        ))
    else:
        print(f"Plan: would archive {len(to_process)} of {len(candidates)} candidate(s)")
        print(f"Max-archive cap: {args.max_archive}")
        _print_candidates(to_process, mode="execute --plan-only (no changes)")
    return 0


def _archive_batch(to_process, base_dir) -> List[Dict[str, Any]]:
    """Archive each candidate; return the list of archived records."""
    archived = []
    for lesson, rate, n in to_process:
        try:
            dst = archive_one(lesson, base_dir)
        except OSError as e:
            print(f"ERROR archiving {lesson.lesson_id}: {e}", file=sys.stderr)
            continue
        archived.append({
            "lesson_id": lesson.lesson_id,
            "archetype": lesson.archetype,
            "archive_path": str(dst),
            "hit_count": lesson.hit_count,
            "miss_count": lesson.miss_count,
            "hit_rate": rate,
            "sample_size": n,
        })
        if _AUDIT_EMIT_AVAILABLE:
            try:
                _emit_lesson_archived(
                    lesson_id=lesson.lesson_id,
                    archetype=lesson.archetype,
                    hit_count=lesson.hit_count,
                    miss_count=lesson.miss_count,
                    hit_rate=rate,
                    archive_path=str(dst),
                    reason="low_hit_rate",
                )
            except Exception:
                pass
    return archived


def _render_execute(to_process, archived, receipt_path, json_mode: bool) -> int:
    """Render final execute output and return exit code 0."""
    if json_mode:
        print(json.dumps(
            _json_payload(
                to_process, mode="execute", archived=archived,
                receipt=str(receipt_path) if receipt_path else None,
            ),
            indent=2, ensure_ascii=False,
        ))
    else:
        print(f"Mode: execute")
        print(f"Archived: {len(archived)}")
        for a in archived:
            print(f"  {a['lesson_id']} -> {a['archive_path']}")
        if receipt_path:
            print(f"Receipt: {receipt_path}")
    return 0


def main(argv=None) -> int:
    """CLI orchestrator — dispatches to the phase helpers above.

    PLAN-023 Phase E decomposition: the original 165-LoC monolith is
    now a thin 30-line orchestrator over six single-purpose helpers
    (``_build_arg_parser``, ``_check_safety_guard``,
    ``_render_dry_run``, ``_check_execute_preconditions``,
    ``_render_plan_only``, ``_archive_batch``, ``_render_execute``).
    Behavior preserved byte-identical — same argparse shape, same
    error messages, same exit codes, same audit-emit ordering.
    """
    args = _build_arg_parser().parse_args(argv)

    # ADR-020 safety guard
    guard = _check_safety_guard(args)
    if guard:
        return guard

    candidates = find_candidates(
        args.base_dir,
        min_miss_ratio=args.min_miss_ratio,
        min_age_days=args.min_age_days,
        min_archive_age_days=args.min_archive_age_days,
    )

    if not args.execute:
        return _render_dry_run(candidates, args.json)

    # --execute path
    pre = _check_execute_preconditions(args)
    if pre:
        return pre

    to_process = candidates[: args.max_archive]

    if args.plan_only:
        return _render_plan_only(to_process, candidates, args)

    archived = _archive_batch(to_process, args.base_dir)
    receipt_path = write_receipt(archived, args.base_dir) if archived else None
    return _render_execute(to_process, archived, receipt_path, args.json)


def _json_payload(candidates, mode, archived, receipt) -> Dict[str, Any]:
    return {
        "criteria": {
            "min_sample_size": MIN_SAMPLE_SIZE,
            "max_hit_rate_for_prune": MAX_HIT_RATE_FOR_PRUNE,
        },
        "candidate_count": len(candidates),
        "mode": mode,
        "candidates": [
            {
                "lesson_id": l.lesson_id,
                "archetype": l.archetype,
                "hit_count": l.hit_count,
                "miss_count": l.miss_count,
                "hit_rate": rate,
                "sample_size": n,
                "scope_tags": l.scope_tags,
            }
            for l, rate, n in candidates
        ],
        "archived": archived,
        "receipt_path": receipt,
    }


if __name__ == "__main__":
    sys.exit(main())
