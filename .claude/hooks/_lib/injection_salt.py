"""Per-instance salt for hash identifier privacy (ADR-079).

Provides ``get_instance_salt() -> bytes`` returning a 32-byte salt
loaded from ``~/.claude/projects/<slug>/.salt``. Generates the salt
on first call (``os.urandom(32)`` + file mode ``0o600``).

PLAN-058 Round-23 (2026-04-24) — closes the REAL identifier-privacy
issue at ``UserPromptSubmit.py:182`` (``prompt_sha`` is unsalted
SHA-256 of the user prompt; correlation oracle for any party with
audit-log read access). The Phase B audit's F-SEC-03 finding
referenced a phantom ``_hash_injection_prefix`` that does not exist;
the real attack surface is ``prompt_sha256`` published by every
``prompt_submitted`` audit event. See ADR-079 §Phantom rejection
for the full forensic record.

## Fail-open contract (ADR-005, ADR-010)

On any I/O failure (permission denied, disk full, broken symlink)
the function returns ``b""`` instead of raising. Callers compose the
empty salt with their input — the resulting hash degrades to the
pre-fix unsalted form. Confidentiality is best-effort; availability
is invariant.

## No rotation

Salt is generated once per installation and never rotated. Rotating
the salt would invalidate ``prompt_sha256`` correlations across all
historical audit events (the chief use of the field). Per-instance
salt provides the desired property — cross-instance correlation is
impossible for an external observer — without sacrificing single-
instance forensic correlation across time.

## Thread safety

The module-level ``_CACHED_SALT`` is read-once-write-once. Concurrent
readers in the unloaded state may both invoke ``os.urandom`` + write,
but the second writer's ``write_bytes`` is atomic on POSIX (single
``write(2)`` for 32 bytes). The losing writer's bytes are discarded;
the winner's bytes seed the cache for both processes on next call.
This is acceptable because hooks run as short-lived subprocesses;
the race window is sub-millisecond and the salt remains 32 random
bytes either way.

## Stdlib-only

Per hook discipline (ADR-002): ``os`` + ``pathlib`` only.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


_SALT_FILENAME = ".salt"
_SALT_BYTES = 32
_SALT_MODE = 0o600
_DIR_MODE = 0o700


def _slug_dir() -> Path:
    """Return the per-installation state directory.

    Mirrors ``audit_emit._audit_dir`` so the salt sits next to the
    audit log it protects. Avoids importing ``audit_emit`` to keep
    this module loadable from any hook (including hooks that emit
    no audit events).
    """
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _salt_path() -> Path:
    return _slug_dir() / _SALT_FILENAME


_CACHED_SALT: Optional[bytes] = None


def _read_existing(path: Path) -> Optional[bytes]:
    """Read salt file if present and well-formed.

    Returns the bytes if size matches ``_SALT_BYTES``; ``None`` if
    the file is absent, the wrong size, or unreadable. Callers
    treat ``None`` as "regenerate".
    """
    try:
        if not path.exists():
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) != _SALT_BYTES:
        return None
    return data


def _generate_and_persist(path: Path) -> bytes:
    """Generate a new 32-byte salt and write it to ``path``.

    Returns the salt on success; ``b""`` on any I/O failure. Sets
    file mode ``0o600`` and parent dir mode ``0o700`` (best-effort).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=_DIR_MODE)
    except OSError:
        return b""
    try:
        salt = os.urandom(_SALT_BYTES)
        path.write_bytes(salt)
    except OSError:
        return b""
    try:
        os.chmod(path, _SALT_MODE)
    except OSError:
        # Permission failure on chmod is non-fatal — the salt is
        # written but with default umask perms. Caller still gets
        # the salt; future readers may face stricter access but the
        # current process succeeds.
        pass
    return salt


def get_instance_salt() -> bytes:
    """Return the per-installation salt; generate + persist on first call.

    Caches the salt in module memory after first successful read or
    generation. Subsequent calls return the cached bytes without
    touching the filesystem.

    Returns ``b""`` on persistent I/O failure; callers must compose
    the result with their input ``hashlib.sha256(salt + payload)``
    such that an empty salt degrades to the unsalted hash.
    """
    global _CACHED_SALT
    if _CACHED_SALT is not None:
        return _CACHED_SALT

    path = _salt_path()
    existing = _read_existing(path)
    if existing is not None:
        _CACHED_SALT = existing
        return existing

    salt = _generate_and_persist(path)
    if salt:
        _CACHED_SALT = salt
    return salt


def reset_cache_for_test() -> None:
    """Test-only: clear the module-level salt cache.

    Production code MUST NOT call this. The cache invariant —
    salt is loaded at most once per process — is part of the
    fail-open guarantee (filesystem failures after the first
    successful load do not affect subsequent calls).
    """
    global _CACHED_SALT
    _CACHED_SALT = None
