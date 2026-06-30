#!/usr/bin/env python3
"""skill-index-build.py — build a lexical tf-idf index over SKILL.md files.

PLAN-011 Phase 2. Scans ``.claude/skills/**/SKILL.md`` across all tiers
(core, frontend, domains/*), extracts each skill's description +
first-body-chunk, computes a tf-idf vector per skill, and stores the
index in a single sqlite file.

## Path convention (global, not plan-scoped)

```
${CEO_SKILL_INDEX_PATH:-$HOME/.claude/projects/<project>/skill-index.sqlite}
```

Unlike ``_lib.state_store`` (plan-scoped by design), the skill index is
global — skills themselves live at the repo level, not the plan level.
A separate sqlite file keeps the index lifecycle independent of any
specific plan and avoids mixing retrieval metadata with plan state.

## Schema

```sql
CREATE TABLE skills (
    slug       TEXT PRIMARY KEY,      -- collision-resolved id ("tier:name" if dup)
    raw_slug   TEXT NOT NULL,         -- directory name (not unique across tiers)
    tier       TEXT NOT NULL,         -- "core" | "frontend" | "domain:<name>"
    path       TEXT NOT NULL,         -- repo-relative path to SKILL.md
    mtime      REAL NOT NULL,         -- float epoch seconds, os.stat.st_mtime
    content_sha TEXT NOT NULL,        -- sha256 of the indexed text
    vector_json TEXT NOT NULL         -- JSON object {term: weight}
);

CREATE TABLE idf (
    term       TEXT PRIMARY KEY,
    idf_value  REAL NOT NULL
);

CREATE TABLE meta (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
-- meta keys: "total_docs", "built_at", "spec_version"
```

## Staleness semantics

After every build, the script recomputes the per-skill ``mtime``. On
subsequent CLI runs with ``--check-stale``, the script compares the
live filesystem mtimes with the stored ones and emits a WARNING line
per stale skill to stderr. Exit code remains 0 (advisory); callers use
``--strict`` to escalate.

## Advisory uncommitted-changes check

``skill-index-build.py --strict`` refuses to build if
``git status --porcelain .claude/skills/`` returns any non-empty line.
The index needs to be reproducible: if the working tree has
uncommitted skill changes, two checkouts of the same commit would
produce different indexes. Non-strict mode emits a WARNING but builds
anyway.

## Feature flag

``CEO_SOTA_DISABLE=1`` -> exit 0 no-op. Prints "skill-index-build
disabled via CEO_SOTA_DISABLE=1" to stdout.

## Exit codes

- 0 — success, or disabled, or --check-stale found no stale entries
- 1 — build failure (sqlite error, no skills found)
- 2 — argument / validation error
- 3 — --strict mode found uncommitted skill changes

Stdlib only: sqlite3, subprocess (for git-status), hashlib, json, math, re.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

_REPO_ROOT_GUESS = Path(__file__).resolve().parent.parent.parent

# Import _lib.embeddings from the hooks package
_HOOKS_LIB = _REPO_ROOT_GUESS / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

from _lib.embeddings import (  # noqa: E402
    cosine,
    idf as compute_idf,
    tfidf_vector,
    tokenize,
)

# SPEC version for this index layout — bumped on breaking schema change.
SPEC_VERSION = "1.0.0"

# Max body characters to fold into the indexed text (after the description).
# Keeps the index small and matches the H4-referenced "first 2000 chars" rule.
BODY_EXTRACT_CHARS = 2000


# ---------------------------------------------------------------------------
# Frontmatter + body extraction
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Minimal YAML frontmatter parser. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text
    try:
        end = text.index("\n---", 3)
    except ValueError:
        return {}, text
    block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    out: Dict[str, str] = {}
    current_key: Optional[str] = None
    for line in block.splitlines():
        if not line.strip():
            current_key = None
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if current_key is not None:
                out[current_key] = (out[current_key] + " " + line.strip()).strip()
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            out[key] = val
            current_key = key
        else:
            current_key = None
    return out, body


def _extract_indexed_text(skill_md_text: str) -> Tuple[str, str]:
    """Extract the text to index: description + body first N chars.

    Returns:
        (name, indexed_text) tuple.
    """
    fm, body = _parse_frontmatter(skill_md_text)
    name = fm.get("name", "").strip()
    description = fm.get("description", "").strip()
    body_chunk = body[:BODY_EXTRACT_CHARS]
    parts = []
    if name:
        parts.append(name)
    if description:
        parts.append(description)
    if body_chunk:
        parts.append(body_chunk)
    return name, "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Skill walker
# ---------------------------------------------------------------------------


def _resolve_tier(skill_md_path: Path, repo_root: Path) -> str:
    rel = skill_md_path.relative_to(repo_root)
    parts = rel.parts
    if len(parts) < 5 or parts[0] != ".claude" or parts[1] != "skills":
        return "unknown"
    bucket = parts[2]
    if bucket in {"core", "frontend"}:
        return bucket
    if bucket == "domains" and len(parts) >= 6:
        return f"domain:{parts[3]}"
    return "unknown"


def _iter_skill_md(repo_root: Path) -> "Iterator[Path]":
    """Yield all SKILL.md paths under .claude/skills/."""
    skills_root = repo_root / ".claude" / "skills"
    if not skills_root.is_dir():
        return
    for tier_dir in ("core", "frontend"):
        root = skills_root / tier_dir
        if root.is_dir():
            for skill_dir in sorted(root.iterdir()):
                f = skill_dir / "SKILL.md"
                if f.is_file():
                    yield f
    domains_root = skills_root / "domains"
    if domains_root.is_dir():
        for domain_dir in sorted(domains_root.iterdir()):
            sk_root = domain_dir / "skills"
            if sk_root.is_dir():
                for skill_dir in sorted(sk_root.iterdir()):
                    f = skill_dir / "SKILL.md"
                    if f.is_file():
                        yield f


# ---------------------------------------------------------------------------
# Index path
# ---------------------------------------------------------------------------


def resolve_index_path() -> Path:
    """Return the path to the skill index sqlite file.

    Env override: ``CEO_SKILL_INDEX_PATH``.
    Default: ``$HOME/.claude/projects/<project>/skill-index.sqlite``.
    """
    env = os.environ.get("CEO_SKILL_INDEX_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    project = os.environ.get("CEO_PROJECT_NAME", "ceo-orchestration")
    return Path(home) / ".claude" / "projects" / project / "skill-index.sqlite"


# ---------------------------------------------------------------------------
# Uncommitted-changes check
# ---------------------------------------------------------------------------


def check_uncommitted_skills(repo_root: Path) -> List[str]:
    """Return list of uncommitted skill paths (empty if clean).

    Uses ``git status --porcelain`` scoped to ``.claude/skills/``.
    Swallows non-zero exit (not a git repo -> returns empty list).
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", ".claude/skills/"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    return lines


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------


def build_index(repo_root: Path, index_path: Path) -> Dict[str, int]:
    """Scan repo, compute tf-idf, write sqlite. Returns summary dict."""
    skill_records: List[Dict[str, object]] = []
    doc_token_sets: List[Set[str]] = []

    seen_slugs: Set[str] = set()
    for skill_md in _iter_skill_md(repo_root):
        try:
            text = skill_md.read_text(encoding="utf-8")
        except OSError as e:
            print(f"WARNING: could not read {skill_md}: {e}", file=sys.stderr)
            continue
        name, indexed_text = _extract_indexed_text(text)
        raw_slug = skill_md.parent.name
        tier = _resolve_tier(skill_md, repo_root)
        if tier == "unknown":
            print(f"WARNING: skipping {skill_md} (could not resolve tier)", file=sys.stderr)
            continue
        tokens = tokenize(indexed_text)
        if not tokens:
            print(f"WARNING: skipping {raw_slug} (no tokens after tokenize)", file=sys.stderr)
            continue
        # Collision resolution: if the same raw_slug exists in multiple
        # tiers (e.g. `frontend-data-layer` in frontend/ AND in
        # domains/fintech/skills/), the second one gets a tier-prefixed id.
        slug = raw_slug
        if slug in seen_slugs:
            slug = f"{tier}:{raw_slug}"
        seen_slugs.add(slug)
        token_set: Set[str] = set(tokens)
        try:
            mtime = skill_md.stat().st_mtime
        except OSError:
            mtime = 0.0
        content_sha = hashlib.sha256(indexed_text.encode("utf-8", errors="replace")).hexdigest()
        skill_records.append({
            "slug": slug,
            "raw_slug": raw_slug,
            "tier": tier,
            "path": str(skill_md.relative_to(repo_root)),
            "mtime": mtime,
            "content_sha": content_sha,
            "indexed_text": indexed_text,
        })
        doc_token_sets.append(token_set)

    if not skill_records:
        raise RuntimeError("no SKILL.md files found in .claude/skills/ — nothing to index")

    # Compute idf once over the full corpus, then tf-idf per doc
    idf_map = compute_idf(doc_token_sets)
    total_docs = len(skill_records)

    # Compute each skill's vector
    for rec in skill_records:
        vec = tfidf_vector(
            str(rec["indexed_text"]),
            idf_map,
            total_docs=total_docs,
        )
        rec["vector_json"] = json.dumps(vec, sort_keys=True, separators=(",", ":"))
        # Drop the indexed_text before write (keep db small)
        del rec["indexed_text"]

    # Write to sqlite
    index_path.parent.mkdir(parents=True, exist_ok=True)
    # Overwrite: atomic enough for single-writer CLI
    if index_path.exists():
        index_path.unlink()
    conn = sqlite3.connect(str(index_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE skills (
                slug TEXT PRIMARY KEY,
                raw_slug TEXT NOT NULL,
                tier TEXT NOT NULL,
                path TEXT NOT NULL,
                mtime REAL NOT NULL,
                content_sha TEXT NOT NULL,
                vector_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE idf (
                term TEXT PRIMARY KEY,
                idf_value REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE meta (
                k TEXT PRIMARY KEY,
                v TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO skills(slug, raw_slug, tier, path, mtime, content_sha, vector_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    rec["slug"],
                    rec["raw_slug"],
                    rec["tier"],
                    rec["path"],
                    float(rec["mtime"]),
                    rec["content_sha"],
                    rec["vector_json"],
                )
                for rec in skill_records
            ],
        )
        conn.executemany(
            "INSERT INTO idf(term, idf_value) VALUES (?, ?)",
            [(t, float(v)) for t, v in idf_map.items()],
        )
        conn.executemany(
            "INSERT INTO meta(k, v) VALUES (?, ?)",
            [
                ("total_docs", str(total_docs)),
                ("built_at", str(int(time.time()))),
                ("spec_version", SPEC_VERSION),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    try:
        os.chmod(index_path, 0o600)
    except OSError:
        pass

    return {
        "skills_indexed": total_docs,
        "idf_terms": len(idf_map),
    }


def check_stale(repo_root: Path, index_path: Path) -> List[Dict[str, object]]:
    """Compare live SKILL.md mtimes vs the stored ones.

    Returns list of stale entries: [{"slug": ..., "stored_mtime": ..., "live_mtime": ...}].
    Live mtime greater than stored means the file changed since index-build.
    """
    if not index_path.exists():
        return []
    conn = sqlite3.connect(str(index_path))
    try:
        rows = conn.execute("SELECT slug, path, mtime FROM skills").fetchall()
    finally:
        conn.close()
    stale: List[Dict[str, object]] = []
    for slug, path, stored_mtime in rows:
        full_path = repo_root / str(path)
        if not full_path.is_file():
            stale.append({
                "slug": slug,
                "stored_mtime": float(stored_mtime),
                "live_mtime": None,
                "reason": "missing",
            })
            continue
        live_mtime = full_path.stat().st_mtime
        if live_mtime > float(stored_mtime) + 0.001:
            stale.append({
                "slug": slug,
                "stored_mtime": float(stored_mtime),
                "live_mtime": live_mtime,
                "reason": "changed",
            })
    return stale


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Build or check a lexical tf-idf index over SKILL.md files.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="project root (default: cwd)",
    )
    parser.add_argument(
        "--index-path",
        default=None,
        help="override index sqlite path (defaults to CEO_SKILL_INDEX_PATH or HOME-derived)",
    )
    parser.add_argument(
        "--check-stale",
        action="store_true",
        help="do not rebuild — just compare live mtimes against stored ones",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 3 if working tree has uncommitted skill changes",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable summary on stdout",
    )
    args = parser.parse_args(argv)

    # Kill-switch
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        print("skill-index-build disabled via CEO_SOTA_DISABLE=1")
        return 0

    repo_root = Path(args.repo_root).resolve()
    index_path = Path(args.index_path) if args.index_path else resolve_index_path()

    # Stale check mode
    if args.check_stale:
        stale = check_stale(repo_root, index_path)
        if args.json:
            print(json.dumps({"stale_count": len(stale), "stale": stale}, indent=2))
        else:
            if not stale:
                print(f"OK: index at {index_path} is fresh")
            else:
                print(f"WARNING: {len(stale)} stale skill(s) in {index_path}", file=sys.stderr)
                for entry in stale:
                    print(
                        f"  {entry['slug']}: stored_mtime={entry['stored_mtime']} "
                        f"live_mtime={entry['live_mtime']} reason={entry['reason']}",
                        file=sys.stderr,
                    )
        # Stale is advisory — exit 0 either way
        return 0

    # Uncommitted-changes check
    uncommitted = check_uncommitted_skills(repo_root)
    if uncommitted:
        msg = (
            f"WARNING: {len(uncommitted)} uncommitted file(s) under .claude/skills/; "
            f"index would not be reproducible from commit HEAD"
        )
        if args.strict:
            print(msg, file=sys.stderr)
            for ln in uncommitted[:10]:
                print(f"  {ln}", file=sys.stderr)
            print("ERROR: --strict mode refuses to build with uncommitted skill changes", file=sys.stderr)
            return 3
        print(msg, file=sys.stderr)

    try:
        summary = build_index(repo_root, index_path)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: build failed: {exc}", file=sys.stderr)
        return 1

    summary["index_path"] = str(index_path)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(
            f"OK: indexed {summary['skills_indexed']} skills, "
            f"{summary['idf_terms']} idf terms -> {index_path}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
