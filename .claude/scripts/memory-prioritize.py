#!/usr/bin/env python3
"""PLAN-046 Cluster 1.3 — Bayesian memory prioritization.

Reads the auto-memory directory under
``~/.claude/projects/<slug>/memory/`` and annotates each topic file
with a ``priority_score`` computed from three signals:

1. **Recency** — hours since last modification. More recent = higher.
2. **Access count** — how many times the file has been git-touched
   recently. Proxied via ``git log --since=`` count if the memory dir
   lives inside a git repo; otherwise falls back to mtime slot.
3. **Topic centrality** — number of times the file is cross-linked
   from ``MEMORY.md`` plus references inside other topic files.

The Bayesian framing: each signal contributes to a Beta-distribution
posterior with uniform prior ``Beta(1, 1)``; scores are the posterior
mean. Output is a sorted list (highest priority first) suitable for
auto-prune decisions or context-window budgeting.

Stdlib-only (`statistics`, `math`, `pathlib`, `re`). Fail-open: on
read/parse errors emit a row with priority_score 0 and a reason
field; never raise.

CLI
---
::

    python3 memory-prioritize.py
        [--memory-dir ~/.claude/projects/<slug>/memory]
        [--format markdown|jsonl]
        [--limit N]
        [--prune --keep N [--apply] [--archive-dir DIR]]

Default output is markdown sorted descending. `--format jsonl` emits
one JSON object per line for downstream tooling.

Retention / rotation (PLAN-113 W7 — finding F-6-6.7)
----------------------------------------------------

The auto-memory directory is otherwise unbounded — this module *scored*
files but never pruned them. ``--prune --keep N`` provides a
**conservative, reversible, default-OFF** retention policy:

- **Default-OFF**: without ``--prune`` the tool only reports (legacy
  behaviour is byte-for-byte unchanged).
- **Dry-run by default**: ``--prune`` previews what *would* be archived
  and writes nothing. You must add ``--apply`` to actually move files.
- **Archive, never delete**: pruned files are *moved* into an
  ``archive/`` subdirectory (override with ``--archive-dir``), never
  hard-deleted. Restoring is a ``mv`` back.
- **Keeps the highest-scored ``N``**: the lowest-scored files beyond the
  cap are the archive candidates. ``MEMORY.md`` and anything already
  under the archive dir are never touched.
- **No-clobber**: an existing target in the archive dir is never
  overwritten; the move is skipped and reported as ``skipped`` so no
  prior archived version is lost.

Example (preview, then apply)::

    python3 memory-prioritize.py --prune --keep 250
    python3 memory-prioritize.py --prune --keep 250 --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import re
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

def _resolve_default_memory_dir() -> Path:
    """Derive memory dir from $CLAUDE_PROJECT_DIR (or cwd as fallback).

    Claude Code memory convention is `~/.claude/projects/<slug>/memory/`
    where `<slug>` is the absolute project path with `/` replaced by `-`
    (leading `-` preserved). This avoids hardcoding any specific Owner's
    home path.
    """
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    project_abs = os.path.abspath(project)
    slug = project_abs.replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug / "memory"


_DEFAULT_MEMORY_DIR = _resolve_default_memory_dir()
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", flags=re.DOTALL)
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+\.md)\)")
_PRIOR_ALPHA = 1.0  # uniform Beta prior
_PRIOR_BETA = 1.0


# --------------------------------------------------------------------------
# Signal computations
# --------------------------------------------------------------------------


def _hours_since(path: Path) -> float:
    """Hours between now (UTC) and the file's mtime."""
    try:
        mtime = _dt.datetime.fromtimestamp(
            path.stat().st_mtime, tz=_dt.timezone.utc
        )
    except OSError:
        return math.inf
    delta = _dt.datetime.now(_dt.timezone.utc) - mtime
    return max(0.0, delta.total_seconds() / 3600.0)


def _recency_signal(hours: float, half_life_hours: float = 168.0) -> float:
    """Exponential decay: score in [0, 1]. Half-life default = 1 week."""
    if not math.isfinite(hours):
        return 0.0
    return math.exp(-math.log(2.0) * hours / half_life_hours)


def _access_signal(access_count: int, saturation: int = 10) -> float:
    """Saturating access score in [0, 1]."""
    if access_count <= 0:
        return 0.0
    return min(1.0, access_count / float(saturation))


def _centrality_signal(inbound_links: int, saturation: int = 5) -> float:
    """Centrality score in [0, 1] based on inbound cross-links."""
    if inbound_links <= 0:
        return 0.0
    return min(1.0, inbound_links / float(saturation))


def _bayes_posterior_mean(
    signals: List[float],
    alpha: float = _PRIOR_ALPHA,
    beta: float = _PRIOR_BETA,
) -> float:
    """Posterior mean of Beta(alpha, beta) updated by signal evidence.

    Each signal in ``[0, 1]`` contributes as pseudo-success = s,
    pseudo-failure = (1 - s). Returns ``(alpha + sum_success) /
    (alpha + beta + N)``.
    """
    n = len(signals)
    if n == 0:
        return alpha / (alpha + beta)
    successes = sum(signals)
    return (alpha + successes) / (alpha + beta + n)


# --------------------------------------------------------------------------
# Cross-link graph
# --------------------------------------------------------------------------


def _collect_inbound_links(memory_dir: Path) -> Dict[str, int]:
    """Return ``{filename: inbound_count}`` across all .md files."""
    counts: Dict[str, int] = {}
    for entry in memory_dir.glob("*.md"):
        try:
            text = entry.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _LINK_RE.finditer(text):
            target = match.group(1).strip()
            # Normalize: take basename only (references from MEMORY.md et al)
            target = target.split("/")[-1]
            counts[target] = counts.get(target, 0) + 1
    return counts


# --------------------------------------------------------------------------
# Access count (git-aware with fallback)
# --------------------------------------------------------------------------


def _access_count(path: Path, since_days: int = 30) -> int:
    """Count times the file was git-touched in the window, or 1 on fallback.

    Memory files aren't always inside a git repo; fall back to a
    coarse ``1`` when ``git log`` can't be consulted. Never raises.
    """
    try:
        import subprocess
        since = f"{since_days}.days.ago"
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since}", "--", str(path)],
            capture_output=True, text=True, timeout=5.0,
        )
        if result.returncode != 0:
            return 1
        return max(0, len([l for l in result.stdout.splitlines() if l.strip()]))
    except Exception:
        return 1


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def _score_one(
    path: Path, inbound_links: Dict[str, int],
) -> Tuple[float, Dict[str, float]]:
    """Compute priority score + signal breakdown for one memory file."""
    hours = _hours_since(path)
    rec = _recency_signal(hours)
    acc = _access_signal(_access_count(path))
    cen = _centrality_signal(inbound_links.get(path.name, 0))
    score = _bayes_posterior_mean([rec, acc, cen])
    return score, {
        "recency": rec,
        "access": acc,
        "centrality": cen,
        "hours_since_mtime": hours,
        "inbound_links": float(inbound_links.get(path.name, 0)),
    }


def prioritize(memory_dir: Path) -> List[Dict[str, object]]:
    """Return a list of ``{name, score, signals}`` sorted desc by score."""
    if not memory_dir.is_dir():
        return []
    inbound = _collect_inbound_links(memory_dir)
    rows: List[Dict[str, object]] = []
    for entry in sorted(memory_dir.glob("*.md")):
        if entry.name == "MEMORY.md":
            continue  # the index itself is never evicted
        try:
            score, signals = _score_one(entry, inbound)
        except Exception as e:  # pragma: no cover — fail-open breadcrumb
            rows.append({
                "name": entry.name, "score": 0.0,
                "reason": f"scoring-error:{type(e).__name__}",
            })
            continue
        rows.append({
            "name": entry.name, "score": round(score, 4),
            "signals": {k: round(v, 4) for k, v in signals.items()},
        })
    rows.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
    return rows


def render_markdown(rows: List[Dict[str, object]], limit: Optional[int]) -> str:
    lines = [
        "# Memory prioritization report",
        "",
        "| # | File | Score | Recency | Access | Centrality | Links |",
        "|---|------|-------|---------|--------|------------|-------|",
    ]
    for i, row in enumerate(rows if limit is None else rows[:limit], start=1):
        name = row.get("name", "?")
        score = row.get("score", 0.0)
        signals = row.get("signals", {}) or {}
        if not isinstance(signals, dict):
            signals = {}
        lines.append(
            f"| {i} | `{name}` | {score:.4f} | "
            f"{signals.get('recency', 0):.3f} | "
            f"{signals.get('access', 0):.3f} | "
            f"{signals.get('centrality', 0):.3f} | "
            f"{int(signals.get('inbound_links', 0))} |"
        )
    return "\n".join(lines)


def render_jsonl(rows: List[Dict[str, object]], limit: Optional[int]) -> str:
    out = rows if limit is None else rows[:limit]
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in out)


# --------------------------------------------------------------------------
# Retention / rotation (PLAN-113 W7 — finding F-6-6.7)
# --------------------------------------------------------------------------

#: Default archive subdirectory name (relative to the memory dir).
_ARCHIVE_DIRNAME = "archive"


def select_prune_candidates(
    rows: List[Dict[str, object]], keep: int,
) -> List[Dict[str, object]]:
    """Return the archive candidates: lowest-scored rows beyond ``keep``.

    ``rows`` MUST already be sorted descending by score (as produced by
    :func:`prioritize`). The top ``keep`` highest-scored files are
    retained; everything past the cap is a candidate. ``keep`` is floored
    at 0; a non-positive ``keep`` would select every row, so callers should
    validate ``keep`` before invoking (the CLI requires ``keep >= 1``).

    Returns the candidates ordered lowest-score-first (eviction order),
    which is the natural reverse of the retained head.
    """
    if keep < 0:
        keep = 0
    candidates = list(rows[keep:])
    # rows is desc by score; candidates are the tail, already
    # lowest-score-last within the tail — reverse so the very lowest comes
    # first (clear eviction order in reports).
    candidates.reverse()
    return candidates


def prune(
    memory_dir: Path,
    keep: int,
    apply: bool = False,
    archive_dirname: str = _ARCHIVE_DIRNAME,
) -> Dict[str, object]:
    """Archive the lowest-scored memory files beyond a ``keep`` cap.

    Conservative + reversible (PLAN-113 W7):

    - **Never deletes** — files are *moved* into ``memory_dir /
      archive_dirname``. Restore = move back.
    - **Dry-run unless ``apply``** — with ``apply=False`` (default) nothing
      is written; the return value lists what *would* move.
    - **Never touches** ``MEMORY.md`` (excluded by :func:`prioritize`) nor
      any file already under the archive dir.
    - **No-clobber** — an existing archive target is not overwritten; that
      candidate is reported under ``skipped`` and left in place.

    Returns a summary dict::

        {
          "memory_dir": str, "archive_dir": str, "keep": int,
          "apply": bool, "total_scored": int, "kept": int,
          "archived": [ {name, score, dest}, ... ],
          "skipped": [ {name, reason}, ... ],
        }

    Fail-open: filesystem errors on an individual move are caught and the
    file is reported under ``skipped`` with the error reason; never raises
    for a single-file failure.
    """
    archive_dir = memory_dir / archive_dirname
    summary: Dict[str, object] = {
        "memory_dir": str(memory_dir),
        "archive_dir": str(archive_dir),
        "keep": keep,
        "apply": bool(apply),
        "total_scored": 0,
        "kept": 0,
        "archived": [],
        "skipped": [],
    }
    if not memory_dir.is_dir():
        return summary

    rows = prioritize(memory_dir)
    summary["total_scored"] = len(rows)
    summary["kept"] = min(keep, len(rows))

    candidates = select_prune_candidates(rows, keep)
    if not candidates:
        return summary

    archived: List[Dict[str, object]] = []
    skipped: List[Dict[str, object]] = []

    # Only create the archive dir when we actually apply a move.
    archive_ready = archive_dir.is_dir()

    for row in candidates:
        name = str(row.get("name", ""))
        score = row.get("score", 0.0)
        src = memory_dir / name
        if not src.is_file():
            skipped.append({"name": name, "reason": "source-missing"})
            continue
        # Defensive: never touch files inside the archive dir itself.
        try:
            if archive_dir in src.resolve().parents:
                skipped.append({"name": name, "reason": "already-archived"})
                continue
        except OSError:
            pass
        dest = archive_dir / name
        if dest.exists():
            # No-clobber: do not overwrite a previously archived version.
            skipped.append({"name": name, "reason": "archive-target-exists"})
            continue

        if not apply:
            archived.append({"name": name, "score": score, "dest": str(dest)})
            continue

        # Apply: create archive dir lazily, then move (rename) the file.
        try:
            if not archive_ready:
                archive_dir.mkdir(parents=True, exist_ok=True)
                try:
                    os.chmod(archive_dir, 0o700)
                except OSError:
                    pass
                archive_ready = True
            os.replace(str(src), str(dest))
            archived.append({"name": name, "score": score, "dest": str(dest)})
        except OSError as e:  # pragma: no cover — per-file fail-open
            skipped.append({"name": name, "reason": f"move-error:{type(e).__name__}"})

    summary["archived"] = archived
    summary["skipped"] = skipped
    return summary


def render_prune_summary(summary: Dict[str, object]) -> str:
    """Human-readable prune report (markdown-ish)."""
    apply = bool(summary.get("apply"))
    mode = "APPLIED" if apply else "DRY-RUN (no files moved; pass --apply to act)"
    archived = summary.get("archived", []) or []
    skipped = summary.get("skipped", []) or []
    if not isinstance(archived, list):
        archived = []
    if not isinstance(skipped, list):
        skipped = []
    lines = [
        "# Memory prune report",
        "",
        f"- mode: **{mode}**",
        f"- memory_dir: `{summary.get('memory_dir', '?')}`",
        f"- archive_dir: `{summary.get('archive_dir', '?')}`",
        f"- keep (highest-scored retained): {summary.get('keep', '?')}",
        f"- total scored: {summary.get('total_scored', 0)}",
        f"- kept: {summary.get('kept', 0)}",
        f"- {'archived' if apply else 'would archive'}: {len(archived)}",
        f"- skipped: {len(skipped)}",
    ]
    if archived:
        verb = "Archived" if apply else "Would archive"
        lines += ["", f"## {verb} (lowest-score first)", ""]
        for row in archived:
            if not isinstance(row, dict):
                continue
            score = row.get("score", 0.0)
            try:
                score_s = f"{float(score):.4f}"
            except (TypeError, ValueError):
                score_s = str(score)
            lines.append(f"- `{row.get('name', '?')}` (score {score_s})")
    if skipped:
        lines += ["", "## Skipped", ""]
        for row in skipped:
            if not isinstance(row, dict):
                continue
            lines.append(f"- `{row.get('name', '?')}` — {row.get('reason', '?')}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="PLAN-046 C1.3 Bayesian memory prioritization.",
    )
    parser.add_argument("--memory-dir", type=Path, default=_DEFAULT_MEMORY_DIR)
    parser.add_argument("--format", choices=("markdown", "jsonl"), default="markdown")
    parser.add_argument("--limit", type=int, default=None)
    # --- retention / rotation (PLAN-113 W7; default-OFF, dry-run, reversible)
    parser.add_argument(
        "--prune", action="store_true",
        help="Enable retention prune (archive lowest-scored files beyond "
             "--keep). DEFAULT-OFF. Dry-run unless --apply is also given.",
    )
    parser.add_argument(
        "--keep", type=int, default=None,
        help="With --prune: number of highest-scored files to retain. "
             "Required when --prune is set; must be >= 1.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="With --prune: actually move files into the archive dir. "
             "Without it, --prune is a dry-run.",
    )
    parser.add_argument(
        "--archive-dir", default=_ARCHIVE_DIRNAME,
        help="With --prune: archive subdir name under --memory-dir "
             f"(default: {_ARCHIVE_DIRNAME!r}). Files are MOVED here, "
             "never deleted.",
    )
    args = parser.parse_args(argv)

    if args.prune:
        if args.keep is None or args.keep < 1:
            sys.stderr.write(
                "error: --prune requires --keep N with N >= 1 "
                "(refusing to archive everything)\n"
            )
            return 2
        summary = prune(
            args.memory_dir,
            keep=args.keep,
            apply=args.apply,
            archive_dirname=args.archive_dir,
        )
        if args.format == "jsonl":
            sys.stdout.write(json.dumps(summary, ensure_ascii=False) + "\n")
        else:
            sys.stdout.write(render_prune_summary(summary) + "\n")
        return 0

    rows = prioritize(args.memory_dir)
    if args.format == "jsonl":
        sys.stdout.write(render_jsonl(rows, args.limit) + "\n")
    else:
        sys.stdout.write(render_markdown(rows, args.limit) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
