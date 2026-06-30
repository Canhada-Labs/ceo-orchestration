"""Unified state backend for plan-scoped, redaction-enforced key/value stores.

Phase 0 of PLAN-011 (Sprint 11). See ADR-027.

## Why

Four Sprint-11 surfaces need persistent state scoped to a specific plan:

- Phase 7: shared scratchpad (agent → agent within the same plan)
- Phase 4: self-improving skill proposals (pending SP-NNN records)
- Phase 2: skill-retrieval index metadata (mtime, checksum)
- Phase 11: session graph snapshots

Each one would otherwise invent its own file layout, filelock strategy,
redaction path, and audit-log event. Consolidating the mechanics here
keeps invariants consistent across surfaces:

1. Plan-scoped — writes/reads in one plan can't bleed into another.
2. Redacted — every value goes through `_lib.redact.redact_secrets` on
   the way in; secrets never reach the sqlite file.
3. TTL + prune — stale values age out without manual intervention.
4. Audit-logged — every write / read / prune emits a typed event so
   `audit-query.py` can surface what each plan is doing.
5. Filelock-safe — concurrent writers across processes get kernel-level
   mutual exclusion via `_lib.filelock.FileLock`.

## Path convention

```
${CEO_STATE_ROOT:-$HOME/.claude/projects/ceo-orchestration/state}/
    <store_name>/
        <plan_id>.sqlite        # the key/value db
        <plan_id>.sqlite.lock   # the filelock sibling
```

`store_name` is a short slug chosen by the caller (`scratchpad`,
`skill_proposals`, `skill_index`, `session_graph`). `plan_id` is the
canonical `PLAN-NNN` string.

## Value size cap

Default 64 KiB per key. Over-cap writes raise `StateStoreValueTooLarge`
(NOT fail-open — the caller asked for an impossible guarantee). The
cap exists because state stores are not designed for blob storage;
bulk data belongs in a separate file with its own retention policy.

## Mandatory redaction

`set()` always calls `redact_secrets()` on string values before writing.
Bytes are accepted but NOT redacted (the caller is saying "I know what
this is"). Audit event records whether redaction mutated the value.

## Fail-mode

Unlike audit_emit (fail-open on observability), state_store is a
first-class correctness surface. Exceptions propagate — callers decide
whether to proceed degraded or abort. Audit emission inside
state_store is still fail-open (per ADR-005).

## Public API

    from _lib.state_store import SqliteStateStore, open_store

    with open_store("scratchpad", "PLAN-011") as store:
        store.set("phase-1-complete", "true", ttl_seconds=86400)
        value = store.get("phase-1-complete")   # -> b"true"
        pruned = store.prune_expired()          # -> int
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import time
from pathlib import Path
from types import TracebackType
from typing import Callable, List, Optional, Type, Union

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import redact as _redact  # noqa: E402
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402


# Value size cap: per-key payload in bytes
DEFAULT_VALUE_MAX_BYTES = 64 * 1024

# Max plan_id length (PLAN-NNN plus slack for suffixes)
_PLAN_ID_MAX_LEN = 64

# Max store name length (slug conventions)
_STORE_NAME_MAX_LEN = 32

# Default filelock timeout — generous because sqlite itself is fast
_LOCK_TIMEOUT_SEC = 5.0


class StateStoreError(Exception):
    """Base exception for all state_store errors."""


class StateStoreValueTooLarge(StateStoreError):
    """Raised when a set() value exceeds the per-key cap."""


class StateStoreInvalidName(StateStoreError):
    """Raised when store_name or plan_id fails validation."""


def _state_root() -> Path:
    """Return the base dir for all plan-scoped state stores.

    Env-overridable via ``CEO_STATE_ROOT``. Default mirrors the audit
    log convention (ADR-001): ``$HOME/.claude/projects/<project>/state``.
    """
    env = os.environ.get("CEO_STATE_ROOT")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    # Project name follows ADR-001: match audit-log siblings
    project = os.environ.get("CEO_PROJECT_NAME", "ceo-orchestration")
    return Path(home) / ".claude" / "projects" / project / "state"


def _validate_store_name(store_name: str) -> None:
    """Reject store names that could escape the state root."""
    if not store_name:
        raise StateStoreInvalidName("store_name must be non-empty")
    if len(store_name) > _STORE_NAME_MAX_LEN:
        raise StateStoreInvalidName(
            f"store_name too long ({len(store_name)} > {_STORE_NAME_MAX_LEN})"
        )
    # Allow kebab-case + underscore slugs only
    for ch in store_name:
        if not (ch.isalnum() or ch in "-_"):
            raise StateStoreInvalidName(
                f"store_name contains illegal char {ch!r}; allowed: [A-Za-z0-9_-]"
            )


def _validate_plan_id(plan_id: str) -> None:
    """Reject plan_ids that could escape the store dir."""
    if not plan_id:
        raise StateStoreInvalidName("plan_id must be non-empty")
    if len(plan_id) > _PLAN_ID_MAX_LEN:
        raise StateStoreInvalidName(
            f"plan_id too long ({len(plan_id)} > {_PLAN_ID_MAX_LEN})"
        )
    for ch in plan_id:
        if not (ch.isalnum() or ch in "-_."):
            raise StateStoreInvalidName(
                f"plan_id contains illegal char {ch!r}; allowed: [A-Za-z0-9_.-]"
            )
    if plan_id.startswith(".") or ".." in plan_id:
        raise StateStoreInvalidName(f"plan_id {plan_id!r} attempts path escape")


def _plan_id_hash(plan_id: str) -> str:
    """Short, stable hash for plan_id — used in audit events without leaking the raw id."""
    return hashlib.sha256(plan_id.encode("utf-8", errors="replace")).hexdigest()[:16]


def _key_hash(key: str) -> str:
    """Short, stable hash for key — audit-safe."""
    return hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()[:16]


class SqliteStateStore:
    """Plan-scoped key/value store backed by a single sqlite file.

    Not thread-safe within a process (callers should open one store per
    thread). Cross-process safety is provided by the sibling filelock.

    Args:
        store_name: short slug identifying the store (e.g. "scratchpad").
        plan_id: canonical PLAN-NNN string scoping the data.
        value_max_bytes: per-key cap. Default 64 KiB.
        lock_timeout: filelock wallclock budget. Default 5.0s.

    Raises:
        StateStoreInvalidName: if store_name or plan_id fail validation.
    """

    def __init__(
        self,
        store_name: str,
        plan_id: str,
        value_max_bytes: int = DEFAULT_VALUE_MAX_BYTES,
        lock_timeout: float = _LOCK_TIMEOUT_SEC,
        *,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        _validate_store_name(store_name)
        _validate_plan_id(plan_id)
        self.store_name = store_name
        self.plan_id = plan_id
        self.value_max_bytes = int(value_max_bytes)
        self.lock_timeout = float(lock_timeout)
        # PLAN-045 Wave 2 F-03-04: injectable clock so TTL tests can
        # fast-forward instead of sleeping. Default: wall clock.
        self._clock: Callable[[], float] = clock if clock is not None else time.time

        self._store_dir = _state_root() / store_name
        self._db_path = self._store_dir / f"{plan_id}.sqlite"
        self._lock_path = self._store_dir / f"{plan_id}.sqlite.lock"

        self._conn: Optional[sqlite3.Connection] = None
        self._opened = False

    def _ensure_open(self) -> None:
        if self._opened:
            return
        self._store_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        # sqlite connect will create the file if absent
        self._conn = sqlite3.connect(
            str(self._db_path),
            timeout=self.lock_timeout,
            isolation_level=None,  # autocommit; we manage transactions via BEGIN/COMMIT
        )
        # Tight file perms — owner-only
        try:
            os.chmod(self._db_path, 0o600)
        except OSError:
            pass
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value BLOB NOT NULL,
                expires_at INTEGER,           -- epoch seconds, NULL = no expiry
                created_at INTEGER NOT NULL,  -- epoch seconds
                redacted INTEGER NOT NULL     -- 1 if redact_secrets changed the value
            )
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_kv_expires ON kv(expires_at)")
        self._opened = True

    # --- context manager --------------------------------------------------

    def __enter__(self) -> "SqliteStateStore":
        self._ensure_open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the connection. Idempotent."""
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None
        self._opened = False

    # --- primary operations -----------------------------------------------

    def set(
        self,
        key: str,
        value: Union[str, bytes],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Write a key/value pair with optional TTL.

        Args:
            key: free-form string key. No length cap enforced at this layer;
                sqlite TEXT PK handles it.
            value: str (redacted before write) or bytes (stored as-is).
            ttl_seconds: None = no expiry; positive int = seconds from now.

        Raises:
            StateStoreValueTooLarge: if value exceeds ``value_max_bytes``.
            ValueError: if ttl_seconds is negative or zero.
        """
        self._ensure_open()
        assert self._conn is not None  # for type-checker

        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be positive, got {ttl_seconds}")

        # Redaction: strings go through the regex redactor; bytes are trusted.
        redacted = 0
        if isinstance(value, str):
            # Use max_chars=0 so full string survives — the cap below
            # still enforces size.
            redacted_text = _redact.redact_secrets(value, max_chars=0)
            if redacted_text != value:
                redacted = 1
            value_bytes = redacted_text.encode("utf-8", errors="replace")
        elif isinstance(value, (bytes, bytearray)):
            value_bytes = bytes(value)
        else:
            raise TypeError(f"value must be str or bytes, got {type(value).__name__}")

        if len(value_bytes) > self.value_max_bytes:
            raise StateStoreValueTooLarge(
                f"value is {len(value_bytes)} bytes, cap is {self.value_max_bytes}"
            )

        now = int(self._clock())
        expires_at: Optional[int] = None
        if ttl_seconds is not None:
            expires_at = now + int(ttl_seconds)

        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            self._conn.execute(
                """
                INSERT INTO kv(key, value, expires_at, created_at, redacted)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    expires_at = excluded.expires_at,
                    created_at = excluded.created_at,
                    redacted = excluded.redacted
                """,
                (key, value_bytes, expires_at, now, redacted),
            )

        # Audit emit (fail-open inside)
        self._emit_audit(
            "state_store_write",
            key_hash=_key_hash(key),
            value_bytes=len(value_bytes),
            ttl_seconds=ttl_seconds,
            redaction_applied=bool(redacted),
        )

    def get(self, key: str) -> Optional[bytes]:
        """Read a key; returns None if missing or expired.

        Expired entries are NOT automatically pruned — call
        :meth:`prune_expired` on a schedule. This keeps get() side-effect
        free for observability.
        """
        self._ensure_open()
        assert self._conn is not None

        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            row = self._conn.execute(
                "SELECT value, expires_at FROM kv WHERE key = ?", (key,)
            ).fetchone()

        found = False
        value: Optional[bytes] = None
        if row is not None:
            raw_value, expires_at = row
            now = int(self._clock())
            if expires_at is None or expires_at > now:
                value = bytes(raw_value)
                found = True

        self._emit_audit(
            "state_store_read",
            key_hash=_key_hash(key),
            found=found,
        )
        return value

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if the key existed."""
        self._ensure_open()
        assert self._conn is not None
        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            cur = self._conn.execute("DELETE FROM kv WHERE key = ?", (key,))
            return cur.rowcount > 0

    def list_keys(self, *, include_expired: bool = False) -> List[str]:
        """List keys in the store. Expired entries are skipped by default."""
        self._ensure_open()
        assert self._conn is not None
        now = int(self._clock())
        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            if include_expired:
                rows = self._conn.execute("SELECT key FROM kv ORDER BY key").fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT key FROM kv WHERE expires_at IS NULL OR expires_at > ? ORDER BY key",
                    (now,),
                ).fetchall()
        return [r[0] for r in rows]

    def prune_expired(self) -> int:
        """Delete expired keys. Returns the count pruned."""
        self._ensure_open()
        assert self._conn is not None
        now = int(self._clock())
        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            cur = self._conn.execute(
                "DELETE FROM kv WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
            pruned = cur.rowcount

        if pruned:
            self._emit_audit("state_store_pruned", keys_pruned_count=pruned)
        return int(pruned)

    def clear_plan(self) -> int:
        """Drop every key for this plan_id. Returns the count deleted.

        Used on plan status `executing → draft` rollback (consensus M2).
        """
        self._ensure_open()
        assert self._conn is not None
        with FileLock(str(self._lock_path), timeout=self.lock_timeout):
            cur = self._conn.execute("DELETE FROM kv")
            cleared = cur.rowcount
        if cleared:
            self._emit_audit("state_store_pruned", keys_pruned_count=cleared)
        return int(cleared)

    # --- audit ------------------------------------------------------------

    def _emit_audit(self, action: str, **fields) -> None:
        """Dispatch to audit_emit — fail-open."""
        try:
            from _lib import audit_emit  # local import to avoid cycle

            emit_fn = getattr(audit_emit, f"emit_{action}", None)
            if emit_fn is None:
                return
            emit_fn(
                store_name=self.store_name,
                plan_id_hash=_plan_id_hash(self.plan_id),
                **fields,
            )
        except Exception:  # pragma: no cover — fail-open per ADR-005
            pass


def open_store(
    store_name: str,
    plan_id: str,
    value_max_bytes: int = DEFAULT_VALUE_MAX_BYTES,
    lock_timeout: float = _LOCK_TIMEOUT_SEC,
    *,
    clock: Optional[Callable[[], float]] = None,
) -> SqliteStateStore:
    """Factory — returns a :class:`SqliteStateStore` ready for use via ``with``.

    PLAN-045 Wave 2 F-03-04: ``clock`` kwarg forwards to the constructor
    so tests can fast-forward TTL boundaries without ``time.sleep``.
    Production callers omit the kwarg and get the wall-clock default.
    """
    return SqliteStateStore(
        store_name=store_name,
        plan_id=plan_id,
        value_max_bytes=value_max_bytes,
        lock_timeout=lock_timeout,
        clock=clock,
    )


__all__ = [
    "SqliteStateStore",
    "StateStoreError",
    "StateStoreValueTooLarge",
    "StateStoreInvalidName",
    "DEFAULT_VALUE_MAX_BYTES",
    "open_store",
]
