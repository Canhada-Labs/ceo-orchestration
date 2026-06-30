---
status: experimental
spec_version: 1.0.0-rc.1
created: 2026-04-16
plan: PLAN-014
phase: F.5a
supersedes: none
---

# SPEC/v1/memory-shared.schema.md — Cross-Plan Shared Memory Contract

**Version:** 1.0.0-rc.1 (PLAN-014 Phase F.5a, Sprint 14)
**Status:** experimental (per ADJ-003 + ADJ-035 until Sprint 15 adopter signal)
**Authoritative source:** `.claude/hooks/_lib/memory_shared.py` — this SPEC is the grep-able API + storage contract the module is tested against.

## 0. Purpose

ADR-048 §Decision establishes WHY cross-plan shared memory exists (knowledge transfer across plans; canonical-edit guard required if repo-committed; redact-on-ingest). This document is the normative companion: API surface, storage layout, topic canonicalization, collision policy, size caps, retention, versioning.

**Scope:** per-topic key-value storage with top-k retrieval. One file per pattern with hash-of-content filename for no-same-file-concurrent-writes.

**Non-scope:** cross-adopter memory sync, real-time index rebuild, semantic search (only normalized-token overlap), automatic retention pruning.

Companion documents:
- ADR-048 — Cross-plan Memory decision (options + ranking + security + blast radius)
- ADR-010 — Canonical-edit sentinel (pattern for §F.5.a guard if repo-committed)
- `audit-log.schema.md` v2.6 — 3 events registered (`pattern_stored`, `pattern_queried`, `pattern_evicted`)
- `_lib/redact.py` — `redact_secrets()` used on ingest
- `_lib/filelock.py` — index file locking
- PLAN-014 §Phase F.5 / §F.6

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | `1.0.0-rc.1` |
| Schema status | `experimental` (frontmatter) |
| Spec lifetime | v1.x.y — additive only per §8 Versioning |
| Authoritative source | `.claude/hooks/_lib/memory_shared.py` |
| Default storage | `~/.claude/projects/<project-slug>/memory-shared/` (Q4=local-only default) |
| Alt storage (if Q4 flipped) | `.claude/memory-shared/` (repo-committed; requires canonical-edit guard) |

SemVer-shaped. Within v1 every API-method addition is MINOR-bump additive only. Method removal or semantics change is MAJOR bump (forbidden in v1 without new SPEC file).

---

## 2. Surface

### 2.1 Python API

Public exports from `_lib.memory_shared`:

```python
def put_pattern(topic: str, content: str) -> str
    """Store one pattern. Returns content_hash (sha256 hex, 16-char prefix).

    Caller is protected against:
    - same-file concurrent-writes (hash-of-content filename; unique per content)
    - secrets in content (redact_secrets() on ingest)
    - size-cap bypass (4 KiB per pattern, 256 KiB total)

    Raises:
    - ValueError on bad topic / oversized content (after redact)
    - OSError on FS failure
    """

def query(topic: str, k: int = 5) -> List[Dict[str, Any]]
    """Retrieve top-k patterns by normalized-token overlap with topic.

    k is clamped to [1, 10] per §3.3.

    Returns list of {topic, content, content_hash, size_bytes, score}.
    """

def evict(topic: str, content_hash: str, reason: str = "admin_request") -> bool
    """Manual-only eviction. Returns True if removed, False if not found.

    reason ∈ {admin_request, size_cap_breach, redact_violation}.
    """

def list_topics() -> List[str]
    """Enumerate stored canonical topic strings (sorted)."""

def stats() -> Dict[str, Any]
    """Storage usage + pattern counts. No secrets; safe to log."""
```

### 2.2 Invariants

- **Redact on ingest (mandatory).** `put_pattern()` passes `content` through `_lib.redact.redact_secrets()` before any write. The pre-redact form is NEVER persisted to disk. Any leak of recognizable secret tokens is a P0 bug.
- **One file per pattern, hash-of-content filename.** Prevents same-file concurrent-write corruption (ADJ-035). Two identical-content writes coalesce to the same file.
- **Index file is a separate JSONL under filelock.** Index entries map `topic → [content_hash, ...]`. Concurrent puts acquire `_lib.filelock.FileLock` on `index.jsonl.lock`.
- **Retention is unbounded by default.** No TTL, no LRU. Operator eviction only via `evict()`.
- **Size caps enforced** (§4.2). Violation ⇒ ValueError + no write.

---

## 3. Topic canonicalization

All topics are normalized before storage + query:

```python
def canonicalize_topic(raw: str) -> str:
    nfc = unicodedata.normalize("NFC", raw)
    lowered = nfc.lower()
    dashed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return dashed
```

### 3.1 Normalization steps

1. **Unicode NFC** (canonical composition — `é` vs `e\u0301` collapse to one form)
2. **Lowercase** (ASCII fold)
3. **Dash-separated** (non-alphanumeric → single dash; strip leading/trailing dashes)

### 3.2 Rejected topics

Topics are rejected (ValueError) if:
- Empty after canonicalization
- Canonical length > 128 chars
- Canonical contains no alphanumeric character

### 3.3 `k` range

`k` is clamped to `[1, 10]` inclusive. Values outside the range are coerced:
- `k < 1` → `k = 1`
- `k > 10` → `k = 10`

No error; the clamp is silent per ADJ-039 (ergonomic UX).

---

## 4. Storage layout

### 4.1 Directory structure

```
<storage-root>/
├── index.jsonl                 # topic → [content_hash, ...] lookup
├── index.jsonl.lock            # FileLock target
└── patterns/
    ├── <sha256-hex[:16]>.txt   # one file per pattern
    ├── <sha256-hex[:16]>.txt
    └── ...
```

All files mode 0o600. Directory mode 0o700.

### 4.2 Size caps

| Cap | Value | Enforcement |
|---|---|---|
| Single pattern content (post-redact) | 4 KiB (4096 bytes) | `put_pattern` pre-write |
| Total storage across all patterns | 256 KiB (262144 bytes) | `put_pattern` pre-write aggregate |
| Single topic string (canonical) | 128 chars | `canonicalize_topic` |
| Patterns per topic | 100 | `put_pattern` pre-write (index check) |

Overflow ⇒ ValueError + no write. **No automatic eviction on overflow.** Operator must `evict()` manually to free space.

### 4.3 Collision policy (append-only index)

Two puts with the SAME `(topic, content)` ⇒ same `content_hash` → single file, index unchanged (idempotent).

Two puts with SAME topic DIFFERENT content ⇒ two files, index has two entries for that topic. Query returns top-k ranked.

Two puts with DIFFERENT topics SAME content ⇒ one file (content-addressed), index has entry in each topic's list.

### 4.4 Index file format (JSONL)

One line per canonical topic:

```jsonl
{"topic": "<canonical>", "hashes": ["<hex16>", "<hex16>"], "updated": "<utc-iso>"}
```

Append-only: new topic → new line; new hash on existing topic → line rewritten under lock.

---

## 5. Ranking

### 5.1 Algorithm — normalized-token overlap

For query topic `q` and stored topic `t`:

```python
score = |tokens(q) ∩ tokens(t)| / max(|tokens(q)|, |tokens(t)|)
```

Where `tokens(s)` is the set of dash-separated segments of the canonical topic.

### 5.2 Tie-breaking

When scores are equal, fall back to:
1. Most recently stored (`updated` in index)
2. Lower content_hash hex (deterministic last resort)

### 5.3 Adversarial flood defense (C32)

An attacker that puts many patterns under a single topic cannot dominate query results for UNRELATED topics — score requires token overlap. For the topic they flood, `per-topic cap` (100; §4.2) bounds the flood.

---

## 6. Error model (closed enum)

Python exceptions raised from public API:

| Exception | Trigger |
|---|---|
| `ValueError("topic_empty")` | canonicalize produced empty string |
| `ValueError("topic_too_long")` | canonical > 128 chars |
| `ValueError("topic_no_alphanumeric")` | canonical contains only dashes |
| `ValueError("content_empty")` | content empty after redact |
| `ValueError("content_too_large")` | content > 4 KiB post-redact |
| `ValueError("storage_full")` | total > 256 KiB |
| `ValueError("too_many_per_topic")` | per-topic > 100 |
| `OSError(...)` | FS failure (bubble up) |

All errors are fail-fast; partial writes are never committed (write-to-temp + rename pattern under filelock).

---

## 7. Audit events

Three events registered in `audit-log.schema.md` v2.6:

### 7.1 `pattern_stored`
```json
{
  "action": "pattern_stored",
  "topic": "<canonical>",
  "content_hash": "<hex16>",
  "size_bytes": <int>,
  "session_id": "<sid>",
  "project": "<slug>",
  "ts": "<utc-iso>"
}
```

### 7.2 `pattern_queried`
```json
{
  "action": "pattern_queried",
  "topic": "<canonical>",
  "k": <int>,
  "match_count": <int>,
  "session_id": "<sid>",
  "project": "<slug>",
  "ts": "<utc-iso>"
}
```

### 7.3 `pattern_evicted`
```json
{
  "action": "pattern_evicted",
  "topic": "<canonical>",
  "content_hash": "<hex16>",
  "reason": "admin_request" | "size_cap_breach" | "redact_violation",
  "session_id": "<sid>",
  "project": "<slug>",
  "ts": "<utc-iso>"
}
```

**Content is NEVER in audit events** (only `content_hash`). The plaintext content is on disk under the storage root, but audit log remains content-free.

---

## 8. Revocation + deprecation

### 8.1 Pattern revocation

- Manual `evict(topic, content_hash)` emits `pattern_evicted(reason=admin_request)`.
- Redact-violation discovered post-hoc → `evict(reason=redact_violation)` + new audit trail.
- Storage-root deletion: operator removes entire directory. Index + files reset. Pattern history LOST.

### 8.2 API deprecation

Within v1, method removal is forbidden. New methods (e.g. `search_tokens(...)`) are MINOR-bump additive.

---

## 9. Security considerations

### 9.1 Redact-on-ingest (mandatory)

`put_pattern()` calls `_redact.redact_secrets(content)` before write. Recognized secret patterns (JWT, `sk-*`, GitHub PAT, AWS key, bearer, hex ≥32, URL-with-creds, `password=` assignments) are replaced with `[REDACTED]`-family labels.

### 9.2 Tampering vector (RR-7)

Per debate C3, if Q4 = repo-committed, `.claude/memory-shared/` MUST be added to `_CANONICAL_GUARDS` in `check_canonical_edit.py` (see `_lib/memory_shared.py` docstring note). Q4 default = local-only (`~/.claude/projects/<slug>/memory-shared/`) keeps the guard optional.

### 9.3 Concurrency safety

Index file access under `_lib.filelock.FileLock` with 2.5s timeout. Multi-process put/evict is race-free. Query is lock-free (reads are immutable per §4.3 content-addressed files).

### 9.4 Tier classification

Memory-shared files are **Tier 2 sensitive** (same tier as audit log). Mode 0o600 file / 0o700 dir.

### 9.5 No network

The module NEVER makes network calls. Pure-local FS + stdlib.

---

## 10. Bounds

| Bound | Value | Enforcement |
|---|---|---|
| Pattern size (post-redact) | 4 KiB | `put_pattern` |
| Total storage | 256 KiB | `put_pattern` |
| Topic canonical length | 128 chars | `canonicalize_topic` |
| Patterns per topic | 100 | `put_pattern` index check |
| `k` clamp | `[1, 10]` | `query` |
| Lock timeout | 2.5s | `FileLock` |

---

## 11. History

| Version | Released | Summary |
|---|---|---|
| 1.0.0-rc.1 | 2026-04-16 | Initial experimental release. Local-only default (Q4), one-file-per-pattern with content-addressed filename, redact-on-ingest, 4 KiB per pattern / 256 KiB total caps, normalized-token overlap ranking. Status: experimental pending Sprint 15 adopter signal. |

---

## 12. Backward compatibility

- **Old patterns** (from v1.0.0-rc.1) remain readable by future module versions (additive-only).
- **Unknown index fields**: module tolerates + skips.
- **Storage-path choice (Q4)** is IRREVERSIBLE once files commit to git — SPEC documents both options but the module defaults to local-only.

---

## 13. Deprecation window

2 MINOR releases minimum for any public API method or storage-format change. No deprecation window for advisory fields (may drop on MINOR).

**Frozen in v1:**
- Redact-on-ingest (§9.1)
- One-file-per-pattern naming (§4.1)
- Local-only default (§0)
- 3 audit event types (§7)

These invariants ARE the point of the module; changing them is a new module, not a version bump.

---

## References

- ADR-048 — Cross-plan Memory decision
- ADR-010 — Canonical-edit sentinel (pattern for §F.5.a if Q4 flipped)
- `_lib/redact.py` — `redact_secrets()`
- `_lib/filelock.py` — index file locking
- `audit-log.schema.md` v2.6 — event registration
- PLAN-014 §Phase F.5 / §F.5a / §F.6
- `.claude/hooks/_lib/memory_shared.py` (authoritative)

---

**End of SPEC/v1/memory-shared.schema.md v1.0.0-rc.1 (experimental).**
