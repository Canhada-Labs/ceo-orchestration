#!/usr/bin/env python3
"""lesson_evolve.py — deterministic lesson clustering → SP-NNN drafts.

PLAN-154 item 7 (``/lesson-evolve``). Clusters the LIVE lessons store by
Jaccard similarity over ``scope_tags`` (deterministic v1 — $0 model spend,
consensus A15), resolves each cluster to a target skill, and — only under
``--propose`` — hands each cluster to the EXISTING ADR-031 pipeline
(``skill-patch-propose.py``) so its CR1 scans (injection, bidi/zero-width,
homoglyph, long-line, fenced-code, diff-size) run unchanged. The output of
a propose run is an inert ``SP-NNN-*.md`` draft under ``.claude/proposals/``
that ONLY the Owner can activate via ``/skill-review`` (approve → shadow →
7d soak → promote). Nothing self-activates (constraint 5).

## Determinism contract (A15)

Given the same lessons store and flags, the dry-run report is byte-identical
across runs: no timestamps, all iteration orders sorted, cluster ids derived
from member lesson ids.

## What is read

Raw ``<lessons_dir>/*.json`` records (top level only — subdirectories such
as an ``archive/`` or a candidate ``pending/`` tree are never scanned).
Records carrying a ``status`` field with a non-live value (e.g. ``PENDING``,
``QUARANTINED``, ``EXPIRED`` — the PLAN-154 item-2/3 candidate states) are
SKIPPED: pre-approval candidate text must never reach a skill-patch draft.

## Kill switches

``CEO_SOTA_DISABLE=1`` → no-op exit 0 (same posture as
``skill-patch-propose.py``, which this script shells out to).

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Make _lib importable (audit emission) — lessons.py pattern.
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_SCRIPTS_DIR = Path(__file__).resolve().parent
_SKILL_PATCH_PROPOSE = _SCRIPTS_DIR / "skill-patch-propose.py"

# Bound directory scans (same posture as lessons.py _MAX_SCAN).
_MAX_SCAN = 1000

#: status values considered LIVE (absent status = legacy live lesson).
_LIVE_STATUSES = frozenset({"", "live", "approved"})

#: default clustering knobs
DEFAULT_THRESHOLD = 0.5
DEFAULT_MIN_CLUSTER = 2

_SP_ID_RE = re.compile(r"\bSP-\d{3}\b")


# ---------------------------------------------------------------------------
# Store read (raw JSON — status-aware, unlike Lesson dataclass round-trip)
# ---------------------------------------------------------------------------


def _lessons_dir(base_dir: Optional[str] = None) -> Path:
    """Resolve the lessons dir with the SAME priority chain as lessons.py."""
    if base_dir:
        return Path(base_dir)
    env = os.environ.get("CEO_LESSONS_DIR")
    if env:
        return Path(env)
    home_env = os.environ.get("HOME")
    if not home_env:
        raise RuntimeError(
            "CEO_LESSONS_DIR is unset AND $HOME is empty; set one before "
            "calling lesson_evolve.py."
        )
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    slug = project_dir.replace("/", "-").lstrip("-") if project_dir else "default"
    return Path(home_env) / ".claude" / "projects" / slug / "lessons"


def load_live_lessons(base_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load LIVE lesson records (sorted by lesson_id; deterministic).

    Skips: non-``.json`` entries, ``index.json``, records without a
    ``lesson_id``, and records whose ``status`` is not live (PENDING /
    QUARANTINED / EXPIRED candidates never feed a skill patch).
    """
    d = _lessons_dir(base_dir)
    if not d.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    count = 0
    for path in sorted(d.iterdir()):
        if count >= _MAX_SCAN:
            break
        if not path.is_file() or path.suffix != ".json":
            continue
        if path.name == "index.json":
            continue
        count += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        lesson_id = data.get("lesson_id")
        if not isinstance(lesson_id, str) or not lesson_id:
            continue
        status = str(data.get("status") or "").strip().lower()
        if status not in _LIVE_STATUSES:
            continue
        tags = data.get("scope_tags")
        if not isinstance(tags, list):
            tags = []
        out.append({
            "lesson_id": lesson_id,
            "archetype": str(data.get("archetype") or ""),
            "scope_tags": sorted({str(t).strip().lower() for t in tags if str(t).strip()}),
            "remember_this": str(data.get("remember_this") or "")[:200],
        })
    out.sort(key=lambda r: r["lesson_id"])
    return out


# ---------------------------------------------------------------------------
# Deterministic clustering (Jaccard over scope_tags, single-link)
# ---------------------------------------------------------------------------


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    if union == 0:
        return 0.0
    return len(a & b) / union


def cluster_lessons(
    lessons: List[Dict[str, Any]],
    threshold: float = DEFAULT_THRESHOLD,
) -> List[List[Dict[str, Any]]]:
    """Single-link clustering: connect pairs with tag-Jaccard >= threshold.

    Deterministic: input is processed in lesson_id order; clusters are
    returned sorted by (size desc, smallest member lesson_id asc).
    """
    n = len(lessons)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            # Deterministic: smaller root index wins.
            if rx < ry:
                parent[ry] = rx
            else:
                parent[rx] = ry

    tag_sets = [set(l["scope_tags"]) for l in lessons]
    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(tag_sets[i], tag_sets[j]) >= threshold:
                union(i, j)

    groups: Dict[int, List[Dict[str, Any]]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(lessons[i])
    clusters = [
        sorted(members, key=lambda r: r["lesson_id"])
        for members in groups.values()
    ]
    clusters.sort(key=lambda c: (-len(c), c[0]["lesson_id"]))
    return clusters


def cluster_key(cluster: List[Dict[str, Any]]) -> str:
    """Stable 12-hex id derived from the member lesson ids."""
    joined = ",".join(sorted(r["lesson_id"] for r in cluster))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]


def cluster_tag_union(cluster: List[Dict[str, Any]]) -> List[str]:
    tags: Set[str] = set()
    for r in cluster:
        tags.update(r["scope_tags"])
    return sorted(tags)


def dominant_archetype(cluster: List[Dict[str, Any]]) -> str:
    """Most frequent archetype; ties broken lexicographically."""
    counts: Dict[str, int] = {}
    for r in cluster:
        arch = r["archetype"] or "(none)"
        counts[arch] = counts.get(arch, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


# ---------------------------------------------------------------------------
# Target-skill resolution (deterministic slug match)
# ---------------------------------------------------------------------------


def discover_skill_slugs(repo_root: Path) -> List[str]:
    """Enumerate installed skill slugs (core, frontend, domains)."""
    slugs: Set[str] = set()
    skills_root = repo_root / ".claude" / "skills"
    for tier in ("core", "frontend"):
        tier_dir = skills_root / tier
        if tier_dir.is_dir():
            for entry in sorted(tier_dir.iterdir()):
                if entry.is_dir() and (entry / "SKILL.md").is_file():
                    slugs.add(entry.name)
    domains_dir = skills_root / "domains"
    if domains_dir.is_dir():
        for domain in sorted(domains_dir.iterdir()):
            sdir = domain / "skills"
            if not sdir.is_dir():
                continue
            for entry in sorted(sdir.iterdir()):
                if entry.is_dir() and (entry / "SKILL.md").is_file():
                    slugs.add(entry.name)
    return sorted(slugs)


def resolve_target_skill(
    cluster_tags: List[str], slugs: List[str]
) -> Optional[str]:
    """Best slug by Jaccard(cluster tags, slug tokens); None when no overlap.

    Slug tokens split on ``-``/``_``. Ties broken lexicographically —
    deterministic by construction.
    """
    tag_set = set(cluster_tags)
    best: Optional[Tuple[float, str]] = None
    for slug in sorted(slugs):
        tokens = set(t for t in re.split(r"[-_]", slug.lower()) if t)
        score = jaccard(tag_set, tokens)
        if score <= 0.0:
            continue
        if best is None or score > best[0] or (score == best[0] and slug < best[1]):
            best = (score, slug)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Propose path — staging files + skill-patch-propose subprocess
# ---------------------------------------------------------------------------


def stage_cluster_lessons(
    cluster: List[Dict[str, Any]], staging_dir: Path
) -> List[Path]:
    """Write one ``lesson-<id>.md`` per member for the ADR-031 pipeline.

    Content is limited to the bounded ``remember_this`` line + metadata —
    ``skill-patch-propose.py`` re-runs its full CR1 scan set over these
    files, so hostile remember-text is rejected there (defense in depth).
    """
    staging_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for record in cluster:
        path = staging_dir / "lesson-{0}.md".format(record["lesson_id"])
        body = (
            "remember: {0}\n\n"
            "tags: {1}\n"
            "archetype: {2}\n"
            "source_lesson: {3}\n".format(
                record["remember_this"],
                ", ".join(record["scope_tags"]),
                record["archetype"],
                record["lesson_id"],
            )
        )
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def propose_cluster(
    *,
    archetype: str,
    skill_slug: str,
    staging_dir: Path,
    repo_root: Path,
) -> Tuple[int, Optional[str], str]:
    """Invoke skill-patch-propose.py; return (rc, sp_id, output_tail)."""
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(_SKILL_PATCH_PROPOSE),
                "--archetype", archetype,
                "--skill", skill_slug,
                "--lessons", str(staging_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            cwd=str(repo_root),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, None, "subprocess error: {0}".format(exc)
    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    sp_id: Optional[str] = None
    if proc.returncode == 0:
        m = _SP_ID_RE.search(proc.stdout or "")
        if m:
            sp_id = m.group(0)
    return proc.returncode, sp_id, combined[-400:]


# ---------------------------------------------------------------------------
# Report rendering (deterministic — NO timestamps)
# ---------------------------------------------------------------------------


def build_cluster_views(
    lessons: List[Dict[str, Any]],
    *,
    threshold: float,
    min_cluster: int,
    slugs: List[str],
) -> List[Dict[str, Any]]:
    """Cluster + resolve; only clusters of size >= min_cluster survive."""
    views: List[Dict[str, Any]] = []
    for cluster in cluster_lessons(lessons, threshold=threshold):
        if len(cluster) < min_cluster:
            continue
        tags = cluster_tag_union(cluster)
        views.append({
            "cluster_id": cluster_key(cluster),
            "size": len(cluster),
            "archetype": dominant_archetype(cluster),
            "tags": tags,
            "target_skill": resolve_target_skill(tags, slugs),
            "members": cluster,
        })
    return views


def render_report(
    views: List[Dict[str, Any]],
    *,
    lessons_scanned: int,
    threshold: float,
    min_cluster: int,
) -> str:
    lines = [
        "# /lesson-evolve — trigger-cluster report",
        "",
        "lessons_scanned: {0}".format(lessons_scanned),
        "threshold: {0}".format(threshold),
        "min_cluster: {0}".format(min_cluster),
        "clusters: {0}".format(len(views)),
        "",
    ]
    for i, view in enumerate(views, 1):
        target = view["target_skill"] or "(unresolved — pick a skill manually)"
        lines.append(
            "## Cluster {0} (id={1}, size={2}, archetype={3})".format(
                i, view["cluster_id"], view["size"], view["archetype"]
            )
        )
        lines.append("target_skill: {0}".format(target))
        lines.append("tags: {0}".format(", ".join(view["tags"])))
        for record in view["members"]:
            lines.append(
                "- {0}  {1}".format(
                    record["lesson_id"], record["remember_this"][:60]
                )
            )
        lines.append("")
    if not views:
        lines.append("(no clusters at this threshold/min-cluster)")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit emission (fail-open; pre-registration = silent no-op)
# ---------------------------------------------------------------------------


def _emit_evolve_event(
    *,
    lessons_scanned: int,
    clusters_found: int,
    clusters_resolved: int,
    proposals_written: int,
    proposals_failed: int,
    dry_run: bool,
) -> None:
    try:
        from _lib import audit_emit  # noqa: WPS433
        audit_emit.emit_generic(
            "lesson_evolve_run",
            lessons_scanned=int(lessons_scanned),
            clusters_found=int(clusters_found),
            clusters_resolved=int(clusters_resolved),
            proposals_written=int(proposals_written),
            proposals_failed=int(proposals_failed),
            dry_run=bool(dry_run),
            session_id="",
            project="",
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic lesson clustering -> SP-NNN skill-patch drafts "
            "(PLAN-154 item 7; $0 model spend). Dry-run by default."
        ),
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_THRESHOLD,
        help="Jaccard threshold over scope_tags (default {0}).".format(
            DEFAULT_THRESHOLD
        ),
    )
    parser.add_argument(
        "--min-cluster", type=int, default=DEFAULT_MIN_CLUSTER,
        help="Minimum cluster size to report (default {0}).".format(
            DEFAULT_MIN_CLUSTER
        ),
    )
    parser.add_argument(
        "--dir", default=None, help="Override the lessons directory."
    )
    parser.add_argument(
        "--repo-root", default=None,
        help="Repo root for skill discovery + proposal writes "
             "(default: CLAUDE_PROJECT_DIR or cwd).",
    )
    parser.add_argument(
        "--propose", action="store_true",
        help="Actually draft SP-NNN proposals via skill-patch-propose.py "
             "(default: dry-run report only — writes NOTHING).",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="Emit the report as JSON (deterministic).",
    )
    return parser


def _run_propose_pass(
    views: List[Dict[str, Any]],
    *,
    lessons_dir_arg: Optional[str],
    repo_root: Path,
) -> Tuple[List[str], int, List[str]]:
    """Stage + propose every resolved cluster.

    Returns ``(proposals_written, proposals_failed, notes)``.
    """
    proposals_written: List[str] = []
    proposals_failed = 0
    notes: List[str] = []
    lessons_root = _lessons_dir(lessons_dir_arg)
    for view in views:
        if not view["target_skill"]:
            notes.append(
                "cluster {0}: unresolved target skill — skipped".format(
                    view["cluster_id"]
                )
            )
            continue
        staging = lessons_root / "evolve-staging" / view["cluster_id"]
        stage_cluster_lessons(view["members"], staging)
        rc, sp_id, tail = propose_cluster(
            archetype=view["archetype"],
            skill_slug=view["target_skill"],
            staging_dir=staging,
            repo_root=repo_root,
        )
        if rc == 0 and sp_id:
            proposals_written.append(sp_id)
            notes.append(
                "cluster {0}: drafted {1} -> {2}".format(
                    view["cluster_id"], sp_id, view["target_skill"]
                )
            )
        else:
            proposals_failed += 1
            last_line = tail.strip().splitlines()[-1] if tail.strip() else ""
            notes.append(
                "cluster {0}: propose FAILED (rc={1}) {2}".format(
                    view["cluster_id"], rc, last_line
                )
            )
    return proposals_written, proposals_failed, notes


def _print_json_output(
    args: Any,
    lessons: List[Dict[str, Any]],
    views: List[Dict[str, Any]],
    proposals_written: List[str],
    proposals_failed: int,
) -> None:
    print(json.dumps(
        {
            "lessons_scanned": len(lessons),
            "threshold": args.threshold,
            "min_cluster": args.min_cluster,
            "clusters": [
                {k: v for k, v in view.items() if k != "members"}
                for view in views
            ],
            "proposals_written": proposals_written,
            "proposals_failed": proposals_failed,
            "dry_run": not args.propose,
        },
        indent=2,
        sort_keys=True,
    ))


def _print_text_output(
    args: Any,
    lessons: List[Dict[str, Any]],
    views: List[Dict[str, Any]],
    proposals_written: List[str],
    propose_notes: List[str],
) -> None:
    print(render_report(
        views,
        lessons_scanned=len(lessons),
        threshold=args.threshold,
        min_cluster=args.min_cluster,
    ))
    for note in propose_notes:
        print("[lesson-evolve] " + note)
    if args.propose and proposals_written:
        print("")
        print("Hand-off — proposals are INERT until Owner approval:")
        print("  /skill-review list")
        for sp_id in proposals_written:
            print(
                "  /skill-review approve {0} --confirm \"I have read {0}\""
                " --signature <path>".format(sp_id)
            )
    elif not args.propose:
        print(
            "(dry-run — nothing written. Re-run with --propose to draft "
            "SP-NNN proposals for the clusters above.)"
        )


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stderr.write("[lesson-evolve] CEO_SOTA_DISABLE=1 — no-op\n")
        return 0

    repo_root = Path(
        args.repo_root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ).resolve()

    lessons = load_live_lessons(args.dir)
    slugs = discover_skill_slugs(repo_root)
    views = build_cluster_views(
        lessons,
        threshold=args.threshold,
        min_cluster=args.min_cluster,
        slugs=slugs,
    )

    proposals_written: List[str] = []
    proposals_failed = 0
    propose_notes: List[str] = []
    if args.propose:
        proposals_written, proposals_failed, propose_notes = _run_propose_pass(
            views, lessons_dir_arg=args.dir, repo_root=repo_root,
        )

    if args.as_json:
        _print_json_output(
            args, lessons, views, proposals_written, proposals_failed
        )
    else:
        _print_text_output(
            args, lessons, views, proposals_written, propose_notes
        )

    _emit_evolve_event(
        lessons_scanned=len(lessons),
        clusters_found=len(views),
        clusters_resolved=sum(1 for v in views if v["target_skill"]),
        proposals_written=len(proposals_written),
        proposals_failed=proposals_failed,
        dry_run=not args.propose,
    )
    return 1 if proposals_failed else 0


if __name__ == "__main__":
    sys.exit(main())
