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

## No rotation — with exactly ONE sanctioned, REGISTERED exception

Salt is generated once per PROJECT (ADR-079 S318 amendment: the salt
unit is the project, resolved via ``_lib/runtime_paths`` — the
per-``$HOME`` reading made ``prompt_sha256`` correlate ACROSS projects,
the exact oracle this module exists to close) and never rotated.
Rotating the salt would invalidate ``prompt_sha256`` correlations
across all historical audit events (the chief use of the field).

The one exception is the PLAN-182 migration itself: the project that
inherits the historical chain (W2 custody decision) inherits the
legacy ``.salt`` byte-for-byte; every OTHER project mints fresh — and
that minting is OBSERVABLE, never silent (the pre-S318 code minted
with no error, no log, no signal — silent rotation against this very
section). Every mint now (a) writes a ``salt-minted.json`` marker
sidecar next to the salt (forensic ground truth) and (b) best-effort
emits the registered ``salt_rotation_registered`` chain event.

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

Per hook discipline (ADR-002): stdlib only. The only intra-``_lib``
import is ``runtime_paths`` (itself a stdlib-only leaf), so the module
stays loadable from any hook; ``audit_emit`` is imported LAZILY inside
the mint branch only (mint happens at most once per project lifetime).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

try:  # loaded as package member (_lib.injection_salt)
    from . import runtime_paths as _runtime_paths
except ImportError:  # loaded bare (sys.path -> _lib/)
    import runtime_paths as _runtime_paths  # type: ignore[no-redef]


_SALT_FILENAME = ".salt"
_SALT_BYTES = 32
_SALT_MODE = 0o600
_DIR_MODE = 0o700


_MINT_MARKER_FILENAME = "salt-minted.json"


def _slug_dir() -> Path:
    """Return the per-PROJECT state directory (ADR-079 S318 amendment).

    Delegates to the single family resolver (``runtime_paths``,
    ADR-001 S318) so the salt sits next to the audit log it protects —
    per project, no longer per ``$HOME``. Still avoids importing
    ``audit_emit`` at module load to stay loadable from any hook
    (including hooks that emit no audit events).
    """
    return _runtime_paths.runtime_state_dir()


def _salt_path() -> Path:
    return _slug_dir() / _SALT_FILENAME


# PLAN-182 W1 rail r2 B2: keyed pelo _salt_path() resolvido — a troca de
# projeto mid-process re-resolve; o salt do A nunca vaza para o B (a
# garantia por-projeto do ADR-079 S318 vale SEM reset manual de teste).
_CACHED_SALT = None  # type: Optional[tuple]  # (path_str, salt_bytes)


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
        # rail r2 F + r5: cria e aperta SO no caminho default — um dir
        # inteiro escolhido via CLAUDE_PROJECT_DIR_NATIVE preserva o modo
        # que o operador definiu.
        _native = bool(os.environ.get("CLAUDE_PROJECT_DIR_NATIVE"))
        _runtime_paths.ensure_state_dir(path.parent, tighten=not _native)
    except Exception:
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
    path = _salt_path()
    # rail r6: identidade ABSOLUTA (override relativo + chdir nao pode
    # servir o salt do projeto anterior).
    path_id = os.path.abspath(str(path))
    cached = _CACHED_SALT
    if cached is not None and cached[0] == path_id:
        return cached[1]

    existing = _read_existing(path)
    if existing is not None:
        _CACHED_SALT = (path_id, existing)
        return existing

    salt = _generate_and_persist(path)
    if salt:
        _CACHED_SALT = (path_id, salt)
        _register_mint(path)
    return salt


def _register_mint(salt_path: Path) -> None:
    """Make the mint OBSERVABLE (ADR-079 S318 amendment §2). Fail-open.

    (a) Marker sidecar next to the salt — forensic ground truth that
        survives even when no emitter ever runs in this project.
    (b) Best-effort lazy chain event ``salt_rotation_registered``
        (kwargs top-level; the slug travels only as a 16-hex sha256
        prefix — the path text never reaches the wire).
    Neither arm may raise: salt availability is invariant (ADR-005).
    """
    slug = ""
    try:
        slug = _runtime_paths.project_slug()
    except Exception:
        pass
    slug_sha16 = (
        hashlib.sha256(slug.encode("utf-8")).hexdigest()[:16] if slug else ""
    )
    try:
        marker = {
            "minted_at_epoch": int(time.time()),
            "reason": "first_mint",
            "salt_scope": "project",
            "slug_sha256": slug_sha16,
            "pid": os.getpid(),
        }
        marker_path = salt_path.parent / _MINT_MARKER_FILENAME
        marker_path.write_text(
            json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8"
        )
        try:
            os.chmod(marker_path, _SALT_MODE)
        except OSError:
            pass
    except Exception:
        pass
    try:
        # Lazy, one-shot, mint-time only: no module-load coupling on the
        # emit stack for the 99.999% of calls that never mint.
        try:  # package member first, bare fallback (mirrors header import)
            from . import audit_emit as _audit_emit  # type: ignore
        except ImportError:
            import audit_emit as _audit_emit  # type: ignore
        _audit_emit.emit_generic(
            "salt_rotation_registered",
            reason="first_mint",
            salt_scope="project",
            slug_sha256=slug_sha16 or "invalid",
        )
    except Exception:
        pass


def reset_cache_for_test() -> None:
    """Test-only: clear the module-level salt cache.

    Production code MUST NOT call this. The cache invariant —
    salt is loaded at most once per process — is part of the
    fail-open guarantee (filesystem failures after the first
    successful load do not affect subsequent calls).
    """
    global _CACHED_SALT
    _CACHED_SALT = None
