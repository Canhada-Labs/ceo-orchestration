"""POSIX advisory file lock via fcntl.flock.

Replaces the mkdir-based lock primitive in `audit-log.sh`. fcntl.flock is
more robust than mkdir for several reasons:

1. **Kernel-managed release** — if the process dies, the OS releases the
   lock automatically. The mkdir version requires a stale-detection loop
   that looks at directory mtime.
2. **Non-busy-wait blocking** — `LOCK_EX | LOCK_NB` combined with a sleep
   retry loop gives predictable timeout behavior.
3. **Same-process correctness** — `fcntl.flock` on the *same file* shared
   between `multiprocessing.Process` workers gives real mutual exclusion.
   (Threading does NOT — see PLAN-002 §8 finding #10: the concurrent-write
   test uses multiprocessing, not threading, precisely because threads
   share the lock.)

## Windows support

fcntl is POSIX-only. On Windows, importing this module will raise
`ImportError`. That is acceptable for ceo-orchestration — the framework
targets macOS and Linux. Documented in ADR-002.

## Usage

    from _lib.filelock import FileLock

    with FileLock("/path/to/audit.jsonl.lock", timeout=2.5):
        # critical section
        ...

## Safety properties

- Timeout is a wallclock budget — if not acquired within `timeout` seconds,
  raises `FileLockTimeout`. Default timeout is 2.5 seconds (matching the
  bash `50 tries × 50ms` budget).
- The lock file is created on demand (owner-only permissions).
- Stale lock detection is automatic (kernel releases on process exit).
- The file descriptor is closed on context exit, releasing the lock.

## Single-instance-per-process contract (PLAN-025 F-sec-008)

Callers MUST NOT nest two `FileLock` instances for the same path from
the same process. `fcntl.flock` is advisory on a per-process basis —
if process P already holds `LOCK_EX` via fd-A and then opens fd-B and
calls `flock(fd-B, LOCK_EX)`, the kernel MAY return success (the
process already owns the lock) OR block waiting, depending on platform
and fcntl implementation. Both outcomes are non-deterministic and
neither matches the intended cross-process mutual-exclusion semantics.

**Correct usage:** acquire once per path per process, release at
context exit. If a callee needs the lock, pass the `FileLock` instance
down, do not re-instantiate.

**Incorrect usage:** ::

    with FileLock(path):
        with FileLock(path):  # SAME PROCESS — undefined behaviour
            ...

This contract is not mechanically enforced (a cross-process lock
manager would need shared state). Callers are trusted to observe it;
the PLAN-025 F-sec-008 finding tightens the docstring to make the
contract explicit for future maintainers.
"""

from __future__ import annotations

import errno
import os
import time
from pathlib import Path
from types import TracebackType
from typing import Optional, Set, Type

try:
    import fcntl
except ImportError as exc:  # pragma: no cover — Windows
    raise ImportError(
        "_lib.filelock requires POSIX fcntl; this platform is not supported. "
        "ceo-orchestration targets macOS and Linux (ADR-002)."
    ) from exc


class FileLockTimeout(Exception):
    """Raised when a FileLock could not be acquired within its timeout."""


# PLAN-087 Wave C.7 — mkdir-done cache.
# Set of str(parent_dir) values where mkdir(exist_ok=True) has already been
# attempted in this process. Avoids redundant syscalls on the hot path —
# audit-log writers acquire/release this lock 50+ times per session and the
# parent directory mtime never changes between acquisitions in practice.
# Module-scope (process-lifetime). CPython set.add() of a scalar is
# GIL-protected; mkdir itself is idempotent so a race between two threads
# is safe (both succeed; the slow path is taken once).
_MKDIR_DONE: Set[str] = set()


class FileLock:
    """Context manager for exclusive access to a file path via fcntl.flock.

    The lock path is separate from the protected file — we create a sibling
    `.lock` file so we don't have to open the real log file in write mode
    just to acquire the lock.

    Args:
        path: A string or Path pointing to the lock file (NOT the file
            being protected). Caller convention: `audit-log.jsonl.lock`.
        timeout: Maximum seconds to wait for the lock. Float. Default 2.5.
        poll_interval: Seconds between non-blocking acquire attempts.
            Default 0.05 (50ms).

    Raises:
        FileLockTimeout: If the lock was not acquired within `timeout`.
    """

    def __init__(
        self,
        path,
        timeout: float = 2.5,
        poll_interval: float = 0.05,
    ) -> None:
        self.path = Path(path)
        self.timeout = float(timeout)
        self.poll_interval = float(poll_interval)
        self._fd: Optional[int] = None

    def acquire(self) -> None:
        """Acquire the lock or raise FileLockTimeout."""
        # PLAN-087 Wave C.7 — call mkdir(exist_ok=True) only once per parent
        # path per process. Best-effort (ignore errors — if the parent can't
        # be created the open() below will surface it). Subsequent acquires
        # on the same parent dir skip the syscall entirely.
        parent_str = str(self.path.parent)
        if parent_str not in _MKDIR_DONE:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                _MKDIR_DONE.add(parent_str)
            except OSError:
                pass

        # O_CREAT | O_RDWR — we just need any fd pointing at the lock file.
        # Mode 0o600 so only the owner can touch it.
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)

        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._fd = fd
                return
            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                    # Unexpected error — close fd and re-raise
                    os.close(fd)
                    raise
                # Contention: sleep and retry until deadline
                if time.monotonic() >= deadline:
                    os.close(fd)
                    raise FileLockTimeout(
                        f"Could not acquire lock on {self.path} within "
                        f"{self.timeout}s"
                    )
                time.sleep(self.poll_interval)

    def release(self) -> None:
        """Release the lock if held. Idempotent."""
        if self._fd is None:
            return
        fd = self._fd
        self._fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:  # pragma: no cover — unlock failures are rare
            pass
        try:
            os.close(fd)
        except OSError:  # pragma: no cover
            pass

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()
