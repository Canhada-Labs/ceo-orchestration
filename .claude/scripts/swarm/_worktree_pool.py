"""PLAN-050 Phase 7b (C4) — worktree pool for swarm-coordinator isolation.

Allocates N=max_parallel git worktrees at swarm init; loops reuse them
via ``git reset --hard HEAD`` instead of creating+destroying per-iter.
Cuts git overhead from ~1207ms/iter to ~50ms per C4 measurement.

## Lifecycle

1. ``init(n, base_repo)`` — creates N worktrees at
   ``<base_repo>/.claude/swarm-worktrees/loop-<i>``. Fail-closed on
   disk-full, path collision, or git error.
2. ``acquire(loop_id)`` — returns the next free worktree Path; blocks
   (fail-fast with TimeoutError) if all are busy.
3. ``release(path, *, prune=False)`` — resets HEAD hard. Per C4
   guidance, ``git worktree prune`` is NOT called per-release (it's a
   global-scan operation — expensive in tight loops); ``prune=True``
   is reserved for teardown.
4. ``teardown()`` — prunes orphan worktrees + removes allocated dirs.

## Invariants

- Pool size is FIXED after init (no dynamic resize).
- Acquire/release pairs are matched; unmatched release = no-op + log.
- Concurrent acquires are serialized under ``threading.Lock``.
- Resets never cross branch boundaries (HEAD only).
- Portability: POSIX only (git worktree available since 2.5). Windows
  runs via git-for-windows are known to work but not covered here.

This module is stdlib-only. `subprocess` + `pathlib` + `threading`.
"""
from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


_DEFAULT_POOL_DIR = ".claude" / Path("swarm-worktrees")


class WorktreePoolError(RuntimeError):
    """Raised by WorktreePool on git failure or state invariant breach."""


@dataclass
class WorktreeSlot:
    """One slot in the pool.

    ``path`` is the absolute worktree directory. ``busy_with`` is the
    loop_id currently holding the slot, or ``None`` when free.
    """

    path: Path
    busy_with: Optional[str] = None


@dataclass
class WorktreePool:
    """Fixed-size pool of git worktrees.

    Use as a context manager OR manage lifecycle explicitly via
    ``init()`` + ``teardown()``.
    """

    base_repo: Path
    size: int
    pool_dir: Path = field(default_factory=lambda: _DEFAULT_POOL_DIR)
    _slots: List[WorktreeSlot] = field(default_factory=list, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _initialized: bool = field(default=False, init=False)
    _prev_sigterm: object = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError(f"size must be > 0; got {self.size}")
        if not isinstance(self.base_repo, Path):
            self.base_repo = Path(self.base_repo)
        if not self.pool_dir.is_absolute():
            self.pool_dir = self.base_repo / self.pool_dir

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------
    def __enter__(self) -> "WorktreePool":
        self.init()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.teardown()

    # ------------------------------------------------------------------
    # Init / teardown
    # ------------------------------------------------------------------
    def init(self) -> None:
        """Create N worktrees on disk. Idempotent if already initialized."""
        if self._initialized:
            return
        self._ensure_base_repo()
        self.pool_dir.mkdir(parents=True, exist_ok=True)
        for i in range(self.size):
            worktree_path = self.pool_dir / f"loop-{i}"
            self._add_worktree(worktree_path)
            self._slots.append(WorktreeSlot(path=worktree_path))
        self._initialized = True

        # Register cleanup on abnormal exit (SIGTERM / interpreter shutdown).
        import atexit as _atexit
        _atexit.register(self._cleanup_on_exit)

        import signal as _signal
        try:
            _prev = _signal.signal(_signal.SIGTERM, self._sigterm_handler)
            self._prev_sigterm = _prev
        except (OSError, ValueError):
            # Not in main thread or signal not available — skip.
            self._prev_sigterm = None

    def _cleanup_on_exit(self) -> None:
        """Called by atexit on interpreter shutdown; idempotent teardown."""
        try:
            self.teardown()
        except Exception:  # pragma: no cover — best-effort
            pass

    def _sigterm_handler(self, signum: int, frame: object) -> None:  # type: ignore[type-arg]
        """Catch SIGTERM, run teardown, then defer to the handler that was
        installed BEFORE this pool hooked SIGTERM — so a caller's existing
        SIGTERM policy (custom handler / SIG_IGN / SIG_DFL) is preserved rather
        than clobbered to default (PLAN-114 F-11-11-4 / Codex P2)."""
        self._cleanup_on_exit()
        import signal as _signal
        prev = self._prev_sigterm
        # Restore whatever was installed before us (None is not a valid arg to
        # signal.signal — fall back to SIG_DFL in that case).
        try:
            _signal.signal(
                _signal.SIGTERM,
                prev if prev is not None else _signal.SIG_DFL,
            )
        except (OSError, ValueError, TypeError):  # pragma: no cover — defensive
            _signal.signal(_signal.SIGTERM, _signal.SIG_DFL)
        if callable(prev):
            # Chain to the caller's handler; it decides the final disposition.
            prev(signum, frame)
        elif prev == _signal.SIG_IGN:
            # Caller asked to ignore SIGTERM — honour it, do not terminate.
            return
        else:
            # SIG_DFL or None → re-raise so the default disposition applies.
            _signal.raise_signal(signum)

    def teardown(self) -> None:
        """Remove all allocated worktrees + prune orphans."""
        if not self._initialized:
            return
        for slot in self._slots:
            self._remove_worktree(slot.path)
        self._run_git(["worktree", "prune"], check=False)
        self._slots.clear()
        self._initialized = False

    # ------------------------------------------------------------------
    # Acquire / release
    # ------------------------------------------------------------------
    def acquire(self, loop_id: str) -> Path:
        """Reserve the next free slot for ``loop_id``.

        Raises ``WorktreePoolError`` if no slot is free (pool is
        exhausted).
        """
        if not self._initialized:
            raise WorktreePoolError("pool not initialized; call init() first")
        with self._lock:
            for slot in self._slots:
                if slot.busy_with is None:
                    slot.busy_with = loop_id
                    return slot.path
            busy_ids = [s.busy_with for s in self._slots]
            raise WorktreePoolError(
                f"pool exhausted ({self.size} slots busy: {busy_ids})"
            )

    def release(self, path: Path, *, prune: bool = False) -> None:
        """Return a slot to the pool + ``git reset --hard HEAD``.

        Per C4: ``git worktree prune`` is NOT called per release;
        pass ``prune=True`` only during teardown or adopter escape
        hatch for recovery after a crash.
        """
        if not self._initialized:
            raise WorktreePoolError("pool not initialized")
        with self._lock:
            slot = next((s for s in self._slots if s.path == path), None)
            if slot is None:
                raise WorktreePoolError(f"unknown worktree path {path}")
            if slot.busy_with is None:
                # Double-release — no-op but flag.
                return
            slot.busy_with = None
        self._reset_hard(path)
        if prune:
            self._run_git(["worktree", "prune"], check=False)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def free_slots(self) -> int:
        with self._lock:
            return sum(1 for s in self._slots if s.busy_with is None)

    def busy_slots(self) -> Dict[str, Path]:
        """Return mapping of loop_id → worktree path for busy slots."""
        with self._lock:
            return {
                s.busy_with: s.path
                for s in self._slots
                if s.busy_with is not None
            }

    # ------------------------------------------------------------------
    # Git primitives
    # ------------------------------------------------------------------
    def _ensure_base_repo(self) -> None:
        if not (self.base_repo / ".git").exists():
            raise WorktreePoolError(
                f"base_repo {self.base_repo} is not a git worktree/repo"
            )

    def _add_worktree(self, path: Path) -> None:
        if path.exists():
            # Already present — validate it's a worktree.
            rc = self._run_git(
                ["worktree", "list", "--porcelain"], check=False
            )
            if str(path) in (rc.stdout or ""):
                return
            # Stale directory left over from a crash — remove first.
            self._remove_worktree(path)
        self._run_git(
            ["worktree", "add", "--detach", str(path), "HEAD"],
            check=True,
        )

    def _remove_worktree(self, path: Path) -> None:
        if path.exists():
            # --force handles dirty state; OK because pool owns the path.
            self._run_git(["worktree", "remove", "--force", str(path)], check=False)
        if path.exists():
            # Fallback — git refused; direct filesystem cleanup.
            import shutil
            shutil.rmtree(path, ignore_errors=True)

    def _reset_hard(self, path: Path) -> None:
        self._run_git(["reset", "--hard", "HEAD"], cwd=path, check=False)
        self._run_git(["clean", "-fd"], cwd=path, check=False)

    def _run_git(
        self,
        args: List[str],
        *,
        cwd: Optional[Path] = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        cmd = ["git", "-C", str(cwd or self.base_repo), *args] if cwd else \
              ["git", "-C", str(self.base_repo), *args]
        r = subprocess.run(
            cmd, capture_output=True, text=True, check=False,
        )
        if check and r.returncode != 0:
            raise WorktreePoolError(
                f"git {args[0]} failed: rc={r.returncode}\n"
                f"stderr={r.stderr[:500]}"
            )
        return r
