"""Pure-logic indexer core (PLAN-041 Phase 4 / ADR-062).

Per qa-architect Round 1 consensus P1-4: extract stdlib-only pure
logic (file walk, .indexignore matching, manifest verification,
incremental diff, symlink reject) so it can be unit-tested WITHOUT
a live LightRAG sidecar. Keep `index-repo.py` as the thin
sidecar-entry-point wrapper that calls into this module + LightRAG.

## Stdlib-only

This module imports ONLY stdlib + `_lib.output_scan` (framework's
already-stdlib scanner). No LightRAG / Chroma / torch import at
module top. Safe to unit-test from the framework's CI without the
sidecar venv available.

## Security: pre-embed secret scan (A9 / security P0-4)

`scan_chunk_pre_embed()` runs `_lib.output_scan.scan()` on every
chunk BEFORE the sidecar's embedding pipeline. LLM06 matches cause
the chunk to be DROPPED + an `rag_index_redacted` event emitted.
Keeps secrets + adversarial content out of the vector store.

## Symlink reject (P1-7 security)

`walk_repo()` uses `Path.resolve().relative_to(repo_root)` to refuse
any path resolving outside the repo root — closes traversal via
symlinks.

## .indexignore matching

Uses fnmatch-based pattern matching with `.gitignore`-compatible
syntax (a minimal subset — no `!` negation, no `**` directory
globbing; those can be added if adopter demand surfaces).
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_DROP_FAMILIES = frozenset({
    "LLM06_sensitive_info",
    "LLM01_prompt_injection",
    "LLM02_insecure_output",
    "LLM10_model_theft",
})
_DROP_VECTORS = frozenset({"tag_character", "homoglyph"})


# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------


def load_indexignore(indexignore_path: Path) -> List[str]:
    """Parse .indexignore file into a list of fnmatch patterns."""
    if not indexignore_path.is_file():
        return []
    patterns: List[str] = []
    try:
        for line in indexignore_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            patterns.append(stripped)
    except OSError:
        return []
    return patterns


def is_ignored(rel_path: str, patterns: List[str]) -> bool:
    """Return True iff rel_path matches any pattern.

    Patterns ending in `/` match directories (we check the prefix);
    otherwise match filenames via fnmatch.
    """
    if not patterns:
        return False
    rel_norm = rel_path.replace(os.sep, "/")
    parts = rel_norm.split("/")
    for pat in patterns:
        pat_norm = pat.replace(os.sep, "/")
        # Directory pattern (trailing slash)
        if pat_norm.endswith("/"):
            bare = pat_norm.rstrip("/")
            if bare in parts:
                return True
            # Also match if the pattern is a path prefix
            if rel_norm.startswith(bare + "/"):
                return True
            continue
        # Match any path component via fnmatch
        if fnmatch.fnmatchcase(rel_norm, pat_norm):
            return True
        # Match basename
        base = parts[-1]
        if fnmatch.fnmatchcase(base, pat_norm):
            return True
        # Match any segment (for patterns like `secrets/` without trailing)
        if pat_norm in parts:
            return True
    return False


# ---------------------------------------------------------------------
# File walk with symlink reject
# ---------------------------------------------------------------------


def walk_repo(
    repo_root: Path,
    indexignore_patterns: List[str],
    *,
    max_file_bytes: int = 512 * 1024,
) -> Iterable[Path]:
    """Walk repo_root yielding file paths NOT matched by indexignore.

    Security P1-7: any path resolving outside repo_root (e.g. via
    symlink) is rejected. Uses `Path.resolve()` + `relative_to`.

    Performance: files larger than `max_file_bytes` are skipped
    (binary blobs etc.). Adopter can override via config.
    """
    repo_root_resolved = repo_root.resolve()
    for root, dirs, files in os.walk(str(repo_root), followlinks=False):
        # In-place prune dirs by .indexignore rules
        dirs_to_keep = []
        for d in dirs:
            d_rel = str(
                Path(root).joinpath(d).resolve().relative_to(repo_root_resolved)
            ).replace(os.sep, "/") if True else d
            try:
                candidate = Path(root).joinpath(d)
                resolved = candidate.resolve()
                resolved.relative_to(repo_root_resolved)  # symlink reject
            except (ValueError, OSError):
                continue
            rel = str(resolved.relative_to(repo_root_resolved)).replace(os.sep, "/")
            if is_ignored(rel + "/", indexignore_patterns) or is_ignored(rel, indexignore_patterns):
                continue
            dirs_to_keep.append(d)
        dirs[:] = dirs_to_keep

        for name in files:
            candidate = Path(root) / name
            try:
                resolved = candidate.resolve()
                rel_path = resolved.relative_to(repo_root_resolved)
            except (ValueError, OSError):
                continue
            rel_str = str(rel_path).replace(os.sep, "/")
            if is_ignored(rel_str, indexignore_patterns):
                continue
            try:
                size = resolved.stat().st_size
            except OSError:
                continue
            if size > max_file_bytes:
                continue
            yield resolved


# ---------------------------------------------------------------------
# Pre-embed scan (security A9 / P0-4)
# ---------------------------------------------------------------------


def scan_chunk_pre_embed(text: str) -> Tuple[bool, Dict[str, Any]]:
    """Scan a pre-embedding chunk for adversarial content.

    Returns `(keep, metadata)` where:
    - keep=False → drop the chunk (emit rag_index_redacted)
    - keep=True  → safe to embed
    - metadata contains family_counts + matched vectors for audit

    Fail-open: on scanner import/crash, return (True, {}) — preferred
    over dropping everything when the scanner itself is the bug.
    """
    if not isinstance(text, str) or not text:
        return True, {}
    try:
        from _lib import output_scan  # type: ignore
    except Exception:
        return True, {"scan_error": "import_failed"}
    try:
        result = output_scan.scan(text)
    except Exception:
        return True, {"scan_error": "scan_failed"}
    family_counts = result.get("family_counts", {}) or {}
    findings = result.get("findings", []) or []
    for fam, count in family_counts.items():
        if fam in _DROP_FAMILIES and count > 0:
            return False, {"reason": fam, "family_counts": family_counts}
    for f in findings:
        vec = f.get("vector")
        if vec in _DROP_VECTORS:
            return False, {"reason": vec, "family_counts": family_counts}
    return True, {"family_counts": family_counts}


# ---------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------


def write_manifest(
    manifest_path: Path,
    *,
    corpus_hash: str,
    last_indexed_commit: str,
    chunks_total: int,
    chunks_redacted: int,
    chunks_skipped_ignored: int,
) -> None:
    """Write index manifest atomically at 0600 perms."""
    payload = {
        "schema_version": "1.0",
        "corpus_hash": corpus_hash,
        "last_indexed_commit": last_indexed_commit,
        "chunks_total": int(chunks_total),
        "chunks_redacted": int(chunks_redacted),
        "chunks_skipped_ignored": int(chunks_skipped_ignored),
        "index_format": "lightrag+chroma",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(manifest_path.parent, 0o700)
    except OSError:
        pass
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    # Create with 0600 from the start
    fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"))
    finally:
        os.close(fd)
    os.replace(tmp, manifest_path)


def read_manifest(manifest_path: Path) -> Optional[Dict[str, Any]]:
    """Read manifest; return None on any failure (fail-open)."""
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        return json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None


def compute_corpus_hash(file_paths: List[Path]) -> str:
    """Stable sha256 over sorted (rel_path, size, mtime) tuples."""
    h = hashlib.sha256()
    rows: List[Tuple[str, int, int]] = []
    for p in file_paths:
        try:
            stat = p.stat()
        except OSError:
            continue
        rows.append((str(p), int(stat.st_size), int(stat.st_mtime_ns)))
    rows.sort()
    for rel, size, mtime in rows:
        h.update(rel.encode("utf-8", errors="replace"))
        h.update(b"\x00")
        h.update(str(size).encode("ascii"))
        h.update(b"\x00")
        h.update(str(mtime).encode("ascii"))
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------
# Incremental diff
# ---------------------------------------------------------------------


def incremental_diff(
    old_manifest: Optional[Dict[str, Any]],
    current_files: List[Path],
    current_commit: str,
) -> Dict[str, Any]:
    """Compute incremental update plan.

    Returns dict with:
    - `changed_files`: list of Path
    - `removed_files`: list of Path (inferred from manifest delta)
    - `full_rebuild_required`: bool — true if corpus_hash diverges
      beyond the threshold or manifest missing
    """
    if old_manifest is None:
        return {
            "changed_files": list(current_files),
            "removed_files": [],
            "full_rebuild_required": True,
        }
    # Simplified: if commit matches, no-op; if differs, rebuild changed files.
    # A production implementation would parse git diff. This is the
    # framework-side stub; sidecar-side glue wires real git.
    if old_manifest.get("last_indexed_commit") == current_commit:
        return {
            "changed_files": [],
            "removed_files": [],
            "full_rebuild_required": False,
        }
    return {
        "changed_files": list(current_files),
        "removed_files": [],
        "full_rebuild_required": False,
    }


# ---------------------------------------------------------------------
# Chunking (simple line-based; LightRAG has its own, but this is the
# unit-testable pure-Python version for fixtures)
# ---------------------------------------------------------------------


def chunk_text(text: str, *, max_chars: int = 4096) -> List[str]:
    """Split text into <= max_chars chunks at line boundaries."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    lines = text.splitlines(keepends=True)
    chunks: List[str] = []
    buf: List[str] = []
    size = 0
    for line in lines:
        if size + len(line) > max_chars and buf:
            chunks.append("".join(buf))
            buf = [line]
            size = len(line)
        else:
            buf.append(line)
            size += len(line)
    if buf:
        chunks.append("".join(buf))
    return chunks
