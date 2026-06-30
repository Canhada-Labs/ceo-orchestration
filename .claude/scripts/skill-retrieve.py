#!/usr/bin/env python3
"""skill-retrieve.py — query the lexical tf-idf skill index.

PLAN-011 Phase 2. Companion to ``skill-index-build.py``. Takes a task
description, computes its tf-idf vector against the stored idf map, and
returns the top-K most similar skills by cosine similarity.

## Usage

```
# Basic query
python3 .claude/scripts/skill-retrieve.py --task "fix a financial display bug"

# Top-3 JSON
python3 .claude/scripts/skill-retrieve.py --task "add tests for state graph" --top-k 3 --json

# Boost skills owned by a specific archetype (+0.1 cosine)
python3 .claude/scripts/skill-retrieve.py --task "database migration" --archetype "Principal Data Engineer"
```

## Output format

Default text: one line per result, ``<slug>\t<score>\t<tier>``.
JSON: ``{"task": "...", "results": [{"slug": ..., "score": ..., "tier": ..., ...}]}``.

## Feature flag

``CEO_SOTA_DISABLE=1`` -> falls back to the static SKILL MAP lookup
from ``team.md`` (substring match on skill name). Does NOT touch the
sqlite index. Useful for disaster-recovery or when the index is broken.

## Exit codes

- 0 — success
- 1 — index missing or malformed
- 2 — argument / validation error

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT_GUESS = Path(__file__).resolve().parent.parent.parent
_HOOKS_LIB = _REPO_ROOT_GUESS / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from _lib.embeddings import cosine, get_embedder, tokenize  # noqa: E402


# ---------------------------------------------------------------------------
# RAG-augmented retrieval (C2 sidecar / default-OFF / graceful-degrade)
# ---------------------------------------------------------------------------


def _rag_retrieve(
    task: str,
    repo_root: Path,
    top_k: int = 5,
) -> Optional[List[Dict[str, object]]]:
    """Attempt vector retrieval via the C2 RAG sidecar.

    Returns a list of result dicts (same schema as ``rank()``) when the
    sidecar is healthy and the router decides AUTO_WIRE, or ``None`` when
    the sidecar is absent / kill-switched / health-probe failed (caller
    MUST fall back to tf-idf / static retrieval).

    The two-step design matches ADR-062-AMEND-1 kill-switch precedence:
      1. ``rag_router.route_query()`` evaluates the routing predicate and
         emits the appropriate audit event (``rag_query_routed`` on
         AUTO_WIRE, ``rag_auto_wire_skipped_sidecar_down`` on sidecar
         down).
      2. ``rag_bridge.rag_retrieve_skills()`` does the actual IPC call.
      3. ``rag_router.emit_cascade_quality()`` fires AC10/AC11 demotion
         signals at the real result decision point.

    Fail-open: any import error or exception returns None.
    """
    try:
        from _lib import rag_router  # type: ignore
        from _lib import rag_bridge  # type: ignore
    except Exception:
        return None

    try:
        decision, _reason = rag_router.route_query(
            repo_root=repo_root,
            query_class="semantic",
        )
    except Exception:
        return None

    if decision != rag_router.AUTO_WIRE:
        return None

    try:
        chunks = rag_bridge.rag_retrieve_skills(task=task, top_k=top_k)
    except Exception:
        return None

    # Emit AC10/AC11 quality signals now that we have the concrete results.
    try:
        profile_size = "LARGE"  # We only reach here on AUTO_WIRE (profile=LARGE)
        rag_router.emit_cascade_quality(
            chunks_requested=top_k,
            chunks_returned=len(chunks) if chunks is not None else 0,
            repo_profile_size=profile_size,
        )
    except Exception:
        pass

    return chunks  # May be None (sidecar absent) or [] (no results) or list


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------


def resolve_index_path() -> Path:
    """Mirror skill-index-build.resolve_index_path (importless copy).

    Env override: ``CEO_SKILL_INDEX_PATH``.
    Default: ``$HOME/.claude/projects/<project>/skill-index.sqlite``.
    """
    env = os.environ.get("CEO_SKILL_INDEX_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    project = os.environ.get("CEO_PROJECT_NAME", "ceo-orchestration")
    return Path(home) / ".claude" / "projects" / project / "skill-index.sqlite"


class IndexView:
    """In-memory view of the skill index."""

    def __init__(
        self,
        skills: List[Dict[str, object]],
        idf_map: Dict[str, float],
        total_docs: int,
    ) -> None:
        self.skills = skills  # list of dicts with vector (parsed)
        self.idf_map = idf_map
        self.total_docs = total_docs


def load_index(index_path: Path) -> IndexView:
    """Load the full index into memory. Small enough (48 skills -> a few hundred KB).

    Raises FileNotFoundError if the index isn't built yet.
    """
    if not index_path.is_file():
        raise FileNotFoundError(
            f"skill index not found at {index_path}. "
            f"Run `python3 .claude/scripts/skill-index-build.py` first."
        )
    conn = sqlite3.connect(str(index_path))
    try:
        # Use pragma_table_info to detect schema — raw_slug column was
        # added during the build-phase collision fix; older indexes won't
        # have it. Keep backwards-compat by selecting what exists.
        cols = [row[1] for row in conn.execute("PRAGMA table_info(skills)").fetchall()]
        has_raw = "raw_slug" in cols
        if has_raw:
            rows = conn.execute(
                "SELECT slug, raw_slug, tier, path, mtime, content_sha, vector_json FROM skills"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT slug, slug, tier, path, mtime, content_sha, vector_json FROM skills"
            ).fetchall()
        idf_rows = conn.execute("SELECT term, idf_value FROM idf").fetchall()
        meta_rows = conn.execute("SELECT k, v FROM meta").fetchall()
    finally:
        conn.close()
    skills: List[Dict[str, object]] = []
    for slug, raw_slug, tier, path, mtime, content_sha, vector_json in rows:
        try:
            vector = json.loads(vector_json)
        except json.JSONDecodeError:
            continue
        skills.append({
            "slug": slug,
            "raw_slug": raw_slug,
            "tier": tier,
            "path": path,
            "mtime": float(mtime),
            "content_sha": content_sha,
            "vector": vector,
        })
    idf_map = {term: float(val) for term, val in idf_rows}
    meta = {k: v for k, v in meta_rows}
    total_docs = int(meta.get("total_docs", len(skills)))
    return IndexView(skills=skills, idf_map=idf_map, total_docs=total_docs)


# ---------------------------------------------------------------------------
# Query-time tf-idf (uses stored idf_map, does NOT re-index)
# ---------------------------------------------------------------------------


def query_vector(task: str, idf_map: Dict[str, float], total_docs: int) -> Dict[str, float]:
    """Compute the tf-idf vector of a query against the stored idf.

    Uses ``get_embedder()`` so ``CEO_REAL_EMBEDDINGS=1`` can swap it.
    Unseen query terms get the smoothed idf for a never-seen term.
    """
    embedder = get_embedder()
    return embedder(task, idf_map)


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


def rank(
    query_vec: Dict[str, float],
    skills: List[Dict[str, object]],
    *,
    top_k: int = 5,
    archetype_skills: Optional[List[str]] = None,
    archetype_boost: float = 0.1,
) -> List[Dict[str, object]]:
    """Rank skills by cosine similarity against the query vector.

    Args:
        query_vec: the tf-idf vector of the query.
        skills: list of skill dicts with "vector" key.
        top_k: max results.
        archetype_skills: list of skill slugs the caller's archetype
            owns. If provided, matching skills get ``archetype_boost``
            added to their cosine score.
        archetype_boost: additive boost applied per-match (default 0.1).

    Returns:
        List of dicts with {slug, tier, score, base_cosine, boosted}.
        Empty list if ``query_vec`` is empty.
    """
    if not query_vec:
        return []
    boost_set = set(archetype_skills or [])
    ranked: List[Dict[str, object]] = []
    for sk in skills:
        base = cosine(query_vec, sk["vector"])  # type: ignore[arg-type]
        score = base
        boosted = False
        # Match boost against BOTH slug and raw_slug — team.md uses raw
        # kebab-case ids but the index may have collision-prefixed ids.
        if sk["slug"] in boost_set or sk.get("raw_slug") in boost_set:
            score = base + archetype_boost
            boosted = True
        ranked.append({
            "slug": sk["slug"],
            "tier": sk["tier"],
            "path": sk["path"],
            "score": score,
            "base_cosine": base,
            "boosted": boosted,
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[: max(1, int(top_k))]


# ---------------------------------------------------------------------------
# Static SKILL MAP fallback (CEO_SOTA_DISABLE=1)
# ---------------------------------------------------------------------------


# Match team.md SKILL MAP rows of the form:
#   | **Archetype Title** | `primary-skill` | `secondary-skill` |
# The PRIMARY skill is the FIRST backticked token after the bold title. The
# old pattern `\|(.+?)\|\s*`(...)`` skipped to the LAST `|`-then-backtick and
# captured the SECONDARY skill (W6 F-11.14 — duplicate of the registry.py bug).
# We now consume any non-backtick run after the title column and stop at the
# FIRST backtick — capture group 2 is the primary skill id.
_ARCHETYPE_ROW_RE = re.compile(
    r"^\|\s*\*\*([^|*]+?)\*\*\s*\|[^`\n]*?`([a-z0-9\-]+)`",
    re.MULTILINE,
)


def static_skill_map_lookup(
    task: str,
    repo_root: Path,
    *,
    top_k: int = 5,
    archetype: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Simple keyword match against the SKILL MAP in team.md + frontend-team.md.

    Used when ``CEO_SOTA_DISABLE=1`` or when no index is present. Not a
    real retrieval — just "does the skill id contain any token of the
    task"? Scores are token-overlap counts.
    """
    team_files = [
        repo_root / ".claude" / "team.md",
        repo_root / ".claude" / "frontend-team.md",
    ]
    domains_dir = repo_root / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for dom in sorted(domains_dir.iterdir()):
            for fname in ("team-personas.md", "frontend-team-personas.md"):
                f = dom / fname
                if f.is_file():
                    team_files.append(f)
    # Collect (archetype, skill_slug) tuples
    pairs: List[Tuple[str, str]] = []
    for tf_path in team_files:
        if not tf_path.is_file():
            continue
        try:
            text = tf_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _ARCHETYPE_ROW_RE.finditer(text):
            title = m.group(1).strip()
            skill = m.group(2).strip()  # group 2 = FIRST backtick = primary skill
            if not title or title.lower() in {"role", "archetype"}:
                continue
            pairs.append((title, skill))
    # Score each skill by token overlap with the task
    task_tokens = set(tokenize(task))
    # Optional archetype match boost
    arch_lc = (archetype or "").lower().strip()
    results: Dict[str, Dict[str, object]] = {}
    for title, skill in pairs:
        skill_tokens = set(tokenize(skill.replace("-", " ")))
        overlap = len(task_tokens & skill_tokens)
        score = float(overlap)
        if arch_lc and arch_lc in title.lower():
            score += 0.5
        prev = results.get(skill)
        if prev is None or score > float(prev["score"]):
            results[skill] = {
                "slug": skill,
                "tier": "static",
                "path": "",
                "score": score,
                "base_cosine": 0.0,
                "boosted": False,
                "archetype": title,
            }
    ranked = sorted(results.values(), key=lambda r: r["score"], reverse=True)
    return ranked[: max(1, int(top_k))]


# ---------------------------------------------------------------------------
# Archetype -> primary skill map (for --archetype boost)
# ---------------------------------------------------------------------------


def archetype_primary_skill(repo_root: Path, archetype: str) -> List[str]:
    """Return the primary skill(s) owned by an archetype name, per SKILL MAP.

    Used to apply the archetype-boost in rank(). Substring match on the
    archetype title. Returns a list because an archetype may own
    multiple skills (primary + secondary).
    """
    team_files = [
        repo_root / ".claude" / "team.md",
        repo_root / ".claude" / "frontend-team.md",
    ]
    domains_dir = repo_root / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for dom in sorted(domains_dir.iterdir()):
            for fname in ("team-personas.md", "frontend-team-personas.md"):
                f = dom / fname
                if f.is_file():
                    team_files.append(f)
    arch_lc = archetype.lower().strip()
    skills: List[str] = []
    for tf_path in team_files:
        if not tf_path.is_file():
            continue
        try:
            text = tf_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _ARCHETYPE_ROW_RE.finditer(text):
            title = m.group(1).strip()
            skill = m.group(2).strip()  # group 2 = FIRST backtick = primary skill
            if arch_lc in title.lower():
                if skill not in skills:
                    skills.append(skill)
    return skills


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Query the lexical skill index for top-K matches.",
    )
    parser.add_argument("--task", required=True, help="task description (query)")
    parser.add_argument("--top-k", type=int, default=5, help="max results (default 5)")
    parser.add_argument(
        "--archetype",
        default=None,
        help="archetype name — matching primary skill(s) get +0.1 boost",
    )
    parser.add_argument(
        "--archetype-boost",
        type=float,
        default=0.1,
        help="additive cosine boost for archetype-owned skills (default 0.1)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="project root (for static fallback + archetype lookup)",
    )
    parser.add_argument(
        "--index-path",
        default=None,
        help="override index sqlite path",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if not args.task.strip():
        print("ERROR: --task must be non-empty", file=sys.stderr)
        return 2
    if args.top_k <= 0:
        print("ERROR: --top-k must be positive", file=sys.stderr)
        return 2

    repo_root = Path(args.repo_root).resolve()

    # Feature flag: fall back to static SKILL MAP
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        results = static_skill_map_lookup(
            args.task, repo_root, top_k=args.top_k, archetype=args.archetype
        )
        _emit(args, results, mode="static")
        return 0

    index_path = Path(args.index_path) if args.index_path else resolve_index_path()
    try:
        view = load_index(index_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("HINT: falling back to static SKILL MAP lookup.", file=sys.stderr)
        results = static_skill_map_lookup(
            args.task, repo_root, top_k=args.top_k, archetype=args.archetype
        )
        _emit(args, results, mode="static-fallback")
        return 0
    except sqlite3.DatabaseError as e:
        print(f"ERROR: index sqlite malformed: {e}", file=sys.stderr)
        return 1

    q_vec = query_vector(args.task, view.idf_map, view.total_docs)
    if not q_vec:
        # Empty query vector — all tokens were stopwords or OOV
        print("WARNING: query produced an empty vector (all stopwords?)", file=sys.stderr)
        _emit(args, [], mode="tfidf-empty")
        return 0

    archetype_skills: List[str] = []
    if args.archetype:
        archetype_skills = archetype_primary_skill(repo_root, args.archetype)

    tfidf_results = rank(
        q_vec,
        view.skills,
        top_k=args.top_k,
        archetype_skills=archetype_skills,
        archetype_boost=args.archetype_boost,
    )

    # --- RAG augmentation (default-OFF / graceful-degrade) ----------------
    # Attempt vector retrieval via the C2 sidecar.  When the sidecar is
    # absent / kill-switched, ``_rag_retrieve`` returns None and we fall
    # back to the pure tf-idf results with zero regression.
    rag_results = _rag_retrieve(args.task, repo_root, top_k=args.top_k)
    if rag_results is not None and len(rag_results) > 0:
        # Merge: deduplicate by slug, preferring the higher score.
        merged: Dict[str, Dict[str, object]] = {}
        for r in tfidf_results:
            slug = str(r.get("slug", ""))
            merged[slug] = r
        for r in rag_results:
            slug = str(r.get("slug", ""))
            existing = merged.get(slug)
            if existing is None or float(r.get("score", 0.0)) > float(existing.get("score", 0.0)):
                merged[slug] = r
        results = sorted(merged.values(), key=lambda r: r.get("score", 0.0), reverse=True)[: max(1, args.top_k)]
        _emit(args, results, mode="rag+tfidf")
    else:
        results = tfidf_results
        _emit(args, results, mode="tfidf")
    return 0


def _emit(args, results: List[Dict[str, object]], *, mode: str) -> None:
    if args.json:
        print(json.dumps({"task": args.task, "mode": mode, "results": results}, indent=2))
        return
    for r in results:
        score = float(r.get("score", 0.0))
        tier = str(r.get("tier", ""))
        slug = str(r.get("slug", ""))
        print(f"{slug}\t{score:.4f}\t{tier}")


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
