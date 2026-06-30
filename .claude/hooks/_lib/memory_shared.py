"""Cross-plan shared memory (pattern library).

Module contract — SPEC/v1/memory-shared.schema.md v1.0.0-rc.1 (experimental).
ADR-048 §Decision: local-only default (Q4), per-user storage at
``~/.claude/projects/<project-slug>/memory-shared/``, redact-on-ingest,
4 KiB / 256 KiB caps, normalized-token overlap ranking.

## Public API

    put_pattern(topic, content) -> content_hash (hex16)
    query(topic, k=5) -> List[{topic, content, content_hash, size_bytes, score}]
    evict(topic, content_hash, reason="admin_request") -> bool
    list_topics() -> List[str]
    stats() -> Dict

## Invariants

- Redact-on-ingest (mandatory via `_lib.redact.redact_secrets`)
- One file per pattern, hash-of-content filename (no same-file concurrent writes)
- Index file under `_lib.filelock.FileLock`
- Storage dir 0o700, files 0o600
- Tier 2 sensitive (same as audit log)

## Storage layout

    <storage-root>/
    ├── index.jsonl                 # topic → [content_hash, ...]
    ├── index.jsonl.lock
    └── patterns/
        ├── <sha256-hex[:16]>.txt
        └── ...

## Env overrides

- ``CEO_MEMORY_SHARED_PATH`` — storage root override (default:
  ``~/.claude/projects/<slug>/memory-shared/``)
- ``CLAUDE_PROJECT_DIR`` — determines project slug for default path

Stdlib-only. Python >= 3.9 compatible.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_LIB_DIR = Path(__file__).resolve().parent
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

from _lib import audit_emit as _audit_emit  # noqa: E402
from _lib import redact as _redact  # noqa: E402
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402


# -----------------------------------------------------------------------------
# Bounds (SPEC §4.2 + §10)
# -----------------------------------------------------------------------------
MAX_CONTENT_BYTES = 4 * 1024  # 4 KiB per pattern
MAX_TOTAL_BYTES = 256 * 1024  # 256 KiB total
MAX_TOPIC_LEN = 128  # canonical chars
MAX_PER_TOPIC = 100  # patterns per topic
K_MIN = 1
K_MAX = 10
LOCK_TIMEOUT = 2.5  # seconds


# -----------------------------------------------------------------------------
# Storage path resolution
# -----------------------------------------------------------------------------


def _project_slug() -> str:
    """Derive project slug from $CLAUDE_PROJECT_DIR or fallback."""
    env = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if env:
        # Take basename of project dir; normalize dashes
        name = Path(env).name or "ceo-orchestration"
        return name.replace("_", "-").lower() or "ceo-orchestration"
    return "ceo-orchestration"


def _storage_root() -> Path:
    """Return storage root (env-overridable)."""
    override = os.environ.get("CEO_MEMORY_SHARED_PATH")
    if override:
        return Path(override)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / _project_slug() / "memory-shared"


def _patterns_dir() -> Path:
    return _storage_root() / "patterns"


def _index_path() -> Path:
    return _storage_root() / "index.jsonl"


def _lock_path() -> Path:
    return _storage_root() / "index.jsonl.lock"


def _ensure_storage() -> None:
    """Create storage dirs with correct modes. Idempotent."""
    root = _storage_root()
    root.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(root, 0o700)
    except OSError:
        pass
    pd = _patterns_dir()
    pd.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(pd, 0o700)
    except OSError:
        pass


# -----------------------------------------------------------------------------
# Topic canonicalization (SPEC §3)
# -----------------------------------------------------------------------------


def canonicalize_topic(raw: str) -> str:
    """Canonicalize a topic string.

    Steps:
    1. Unicode NFC
    2. Lowercase
    3. Non-alphanumeric → single dash; strip leading/trailing dashes

    Empty / no-alphanumeric / too-long → ValueError.
    """
    if raw is None or not isinstance(raw, str):
        raise ValueError("topic_empty")
    nfc = unicodedata.normalize("NFC", raw)
    lowered = nfc.lower()
    dashed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not dashed:
        # After stripping, could be all-dashes originally; distinguish
        # "empty" vs "no-alphanumeric"
        stripped = raw.strip()
        if not stripped:
            raise ValueError("topic_empty")
        raise ValueError("topic_no_alphanumeric")
    if len(dashed) > MAX_TOPIC_LEN:
        raise ValueError("topic_too_long")
    return dashed


def _tokenize(canonical: str) -> set:
    """Split a canonical topic into its token set (dash-separated)."""
    if not canonical:
        return set()
    return {t for t in canonical.split("-") if t}


# -----------------------------------------------------------------------------
# Hashing
# -----------------------------------------------------------------------------


def _hash_content(content: str) -> str:
    """Return sha256 hex[:16] of redacted content."""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]


# -----------------------------------------------------------------------------
# Index read/write (under filelock)
# -----------------------------------------------------------------------------


def _read_index_unlocked() -> Dict[str, Dict[str, Any]]:
    """Read index.jsonl into dict keyed by topic. Caller must hold lock."""
    idx: Dict[str, Dict[str, Any]] = {}
    p = _index_path()
    if not p.is_file():
        return idx
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                topic = row.get("topic")
                if isinstance(topic, str) and topic:
                    idx[topic] = {
                        "hashes": list(row.get("hashes", [])),
                        "updated": row.get("updated", ""),
                    }
    except OSError:
        return idx
    return idx


def _write_index_unlocked(idx: Dict[str, Dict[str, Any]]) -> None:
    """Rewrite the index file atomically. Caller must hold lock."""
    p = _index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".jsonl.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            for topic in sorted(idx.keys()):
                rec = {
                    "topic": topic,
                    "hashes": list(idx[topic].get("hashes", [])),
                    "updated": idx[topic].get("updated", _utc_iso()),
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(str(tmp), str(p))
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -----------------------------------------------------------------------------
# Total-size computation
# -----------------------------------------------------------------------------


def _total_size_bytes() -> int:
    """Sum of all pattern file sizes. Lock-free (file sizes only; transient)."""
    pd = _patterns_dir()
    if not pd.is_dir():
        return 0
    total = 0
    try:
        for p in pd.iterdir():
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def put_pattern(topic: str, content: str) -> str:
    """Store a pattern. Returns content_hash (hex16).

    Invariants:
    - Redacts content via `_lib.redact.redact_secrets` BEFORE write
    - Rejects oversize / empty content
    - Rejects when total storage would exceed MAX_TOTAL_BYTES
    - Rejects when per-topic count would exceed MAX_PER_TOPIC
    - File-per-pattern with hash-of-content filename (collision = idempotent)

    Raises:
        ValueError: on bounds/validation failure (closed enum reasons)
        OSError: on FS failure (bubbled)
    """
    if content is None or not isinstance(content, str):
        raise ValueError("content_empty")

    canon = canonicalize_topic(topic)
    # Redact BEFORE any size check — redact shrinks content, post-redact size
    # is what lands on disk.
    redacted = _redact.redact_secrets(content, max_chars=0)  # no truncation
    if not redacted.strip():
        raise ValueError("content_empty")
    data_bytes = redacted.encode("utf-8", errors="replace")
    if len(data_bytes) > MAX_CONTENT_BYTES:
        raise ValueError("content_too_large")

    _ensure_storage()

    h = _hash_content(redacted)
    fpath = _patterns_dir() / f"{h}.txt"

    try:
        with FileLock(str(_lock_path()), timeout=LOCK_TIMEOUT):
            idx = _read_index_unlocked()
            # Per-topic cap check
            existing = idx.get(canon, {"hashes": [], "updated": ""})
            existing_hashes = list(existing.get("hashes", []))

            # If this exact content is already stored under this topic,
            # it's idempotent — no write needed, no error.
            if h in existing_hashes:
                _emit_stored(canon, h, len(data_bytes))
                return h

            if len(existing_hashes) >= MAX_PER_TOPIC:
                raise ValueError("too_many_per_topic")

            # Total size check (against post-write projection)
            current_total = _total_size_bytes()
            if not fpath.exists():
                if current_total + len(data_bytes) > MAX_TOTAL_BYTES:
                    raise ValueError("storage_full")

            # Write pattern file atomically
            tmp = fpath.with_suffix(".tmp")
            try:
                with tmp.open("w", encoding="utf-8") as f:
                    f.write(redacted)
                os.replace(str(tmp), str(fpath))
                try:
                    os.chmod(fpath, 0o600)
                except OSError:
                    pass
            finally:
                if tmp.exists():
                    try:
                        tmp.unlink()
                    except OSError:
                        pass

            # Update index
            existing_hashes.append(h)
            idx[canon] = {"hashes": existing_hashes, "updated": _utc_iso()}
            _write_index_unlocked(idx)

            _emit_stored(canon, h, len(data_bytes))
            return h
    except FileLockTimeout as e:
        raise OSError("memory_shared: lock timeout") from e


def _emit_stored(topic: str, h: str, size_bytes: int) -> None:
    try:
        _audit_emit.emit_pattern_stored(
            topic=topic,
            content_hash=h,
            size_bytes=size_bytes,
        )
    except Exception:  # noqa: BLE001 — audit MUST NOT break the API
        pass


def query(topic: str, k: int = 5) -> List[Dict[str, Any]]:
    """Return top-k patterns by normalized-token overlap.

    ``k`` is silently clamped to ``[1, 10]``.

    Each result is a dict:
        {topic, content, content_hash, size_bytes, score}

    Empty query / no matches → empty list (no raise).
    """
    # Clamp k silently per SPEC §3.3
    if not isinstance(k, int):
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = 5
    if k < K_MIN:
        k = K_MIN
    if k > K_MAX:
        k = K_MAX

    try:
        canon = canonicalize_topic(topic)
    except ValueError:
        # Invalid query topic → emit and return empty
        try:
            _audit_emit.emit_pattern_queried(topic=str(topic)[:64], k=k, match_count=0)
        except Exception:  # noqa: BLE001
            pass
        return []

    _ensure_storage()

    q_tokens = _tokenize(canon)
    results: List[Tuple[float, str, str, str, int]] = []

    try:
        with FileLock(str(_lock_path()), timeout=LOCK_TIMEOUT):
            idx = _read_index_unlocked()
            for stored_topic, entry in idx.items():
                t_tokens = _tokenize(stored_topic)
                if not q_tokens or not t_tokens:
                    s = 0.0
                else:
                    inter = len(q_tokens & t_tokens)
                    s = inter / max(len(q_tokens), len(t_tokens))
                if s <= 0.0:
                    continue
                hashes = list(entry.get("hashes", []))
                updated = str(entry.get("updated", ""))
                for h in hashes:
                    results.append((s, stored_topic, h, updated, 0))
    except FileLockTimeout:
        try:
            _audit_emit.emit_pattern_queried(topic=canon, k=k, match_count=0)
        except Exception:  # noqa: BLE001
            pass
        return []

    # Resolve content + size per result; drop missing files.
    enriched: List[Dict[str, Any]] = []
    for s, t, h, updated, _ in results:
        p = _patterns_dir() / f"{h}.txt"
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            size_bytes = p.stat().st_size
        except OSError:
            size_bytes = len(content.encode("utf-8", errors="replace"))
        enriched.append({
            "topic": t,
            "content": content,
            "content_hash": h,
            "size_bytes": size_bytes,
            "score": s,
            "updated": updated,
        })

    # Tie-break per SPEC §5.2: score DESC, updated DESC, hash ASC
    enriched.sort(key=lambda r: (-r["score"], -_ts_sort_key(r.get("updated", "")), r["content_hash"]))

    out = enriched[:k]

    try:
        _audit_emit.emit_pattern_queried(topic=canon, k=k, match_count=len(out))
    except Exception:  # noqa: BLE001
        pass

    return out


def _ts_sort_key(ts: str) -> float:
    """Map utc-iso string to numeric sort key. Empty -> 0."""
    if not ts:
        return 0.0
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        return dt.replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


def evict(topic: str, content_hash: str, reason: str = "admin_request") -> bool:
    """Remove one pattern. Returns True if removed, False if not found.

    ``reason`` ∈ {admin_request, size_cap_breach, redact_violation}.
    """
    allowed_reasons = {"admin_request", "size_cap_breach", "redact_violation"}
    if reason not in allowed_reasons:
        reason = "admin_request"

    try:
        canon = canonicalize_topic(topic)
    except ValueError:
        return False

    _ensure_storage()

    removed = False
    try:
        with FileLock(str(_lock_path()), timeout=LOCK_TIMEOUT):
            idx = _read_index_unlocked()
            entry = idx.get(canon)
            if entry is None:
                return False
            hashes = list(entry.get("hashes", []))
            if content_hash not in hashes:
                return False
            hashes.remove(content_hash)
            if hashes:
                idx[canon] = {"hashes": hashes, "updated": _utc_iso()}
            else:
                del idx[canon]
            _write_index_unlocked(idx)

            # Only remove the content file if no other topic references it.
            still_referenced = any(
                content_hash in list(e.get("hashes", []))
                for t, e in idx.items()
                if t != canon
            )
            if not still_referenced:
                p = _patterns_dir() / f"{content_hash}.txt"
                if p.is_file():
                    try:
                        p.unlink()
                    except OSError:
                        pass
            removed = True
    except FileLockTimeout:
        return False

    if removed:
        try:
            _audit_emit.emit_pattern_evicted(
                topic=canon,
                content_hash=content_hash,
                reason=reason,
            )
        except Exception:  # noqa: BLE001
            pass

    return removed


def list_topics() -> List[str]:
    """Enumerate stored canonical topic strings (sorted)."""
    _ensure_storage()
    try:
        with FileLock(str(_lock_path()), timeout=LOCK_TIMEOUT):
            idx = _read_index_unlocked()
            return sorted(idx.keys())
    except FileLockTimeout:
        return []


def stats() -> Dict[str, Any]:
    """Storage usage + pattern counts. Safe to log.

    Returns:
        {
          "storage_root": "<path>",
          "total_bytes": <int>,
          "max_total_bytes": <int>,
          "pattern_count": <int>,
          "topic_count": <int>,
          "max_per_topic": <int>,
          "max_content_bytes": <int>,
        }
    """
    _ensure_storage()
    topic_count = 0
    pattern_count = 0
    try:
        with FileLock(str(_lock_path()), timeout=LOCK_TIMEOUT):
            idx = _read_index_unlocked()
            topic_count = len(idx)
            # patterns_dir may contain orphan files not in index; count files
            pd = _patterns_dir()
            if pd.is_dir():
                pattern_count = sum(1 for p in pd.iterdir() if p.is_file() and p.suffix == ".txt")
    except FileLockTimeout:
        pass

    return {
        "storage_root": str(_storage_root()),
        "total_bytes": _total_size_bytes(),
        "max_total_bytes": MAX_TOTAL_BYTES,
        "pattern_count": pattern_count,
        "topic_count": topic_count,
        "max_per_topic": MAX_PER_TOPIC,
        "max_content_bytes": MAX_CONTENT_BYTES,
    }


__all__ = [
    "put_pattern",
    "query",
    "evict",
    "list_topics",
    "stats",
    "canonicalize_topic",
    "MAX_CONTENT_BYTES",
    "MAX_TOTAL_BYTES",
    "MAX_TOPIC_LEN",
    "MAX_PER_TOPIC",
    "K_MIN",
    "K_MAX",
]
