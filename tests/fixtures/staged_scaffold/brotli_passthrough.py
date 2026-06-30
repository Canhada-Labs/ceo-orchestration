"""PLAN-046 Cluster 1.1 — context sidecar compression passthrough.

**Staged scaffold**. Destination path
``.claude/hooks/_lib/brotli_passthrough.py`` is canonical-guarded by
``check_canonical_edit.py``; Owner-signed sentinel (future round) is
required to promote this file there. Adopters can import directly
from this staged location via sys.path; the scaffold carries no
runtime wiring until a hook calls it.

Opt-in wrapper around context-block compression. Stdlib fallback uses
``zlib`` (DEFLATE, always available). Upgrade backend is ``brotli``
(adopter installs ``pip install brotli==1.1.0``); if ``brotli`` is
missing the implementation silently falls back to zlib.

Contract
--------
``compress(data, level=9) -> bytes`` — returns compressed payload or
the input unchanged when the backend is ``off``.
``decompress(data) -> bytes`` — auto-detects zlib framing; tries
brotli only when the zlib probe fails; returns ``data`` unchanged as
the final fail-open step so no upstream hook is broken by a malformed
payload.

Config (env)
------------
``CEO_CONTEXT_COMPRESS`` in {``zlib`` (default), ``brotli``, ``off``}.

Kill-switch: ``CEO_CONTEXT_COMPRESS=off``.

Clean-room declaration
----------------------
No code is lifted from ``ooples`` or any other upstream compression
library. The stdlib path is a thin ``zlib`` wrapper; the brotli path
is a guarded ``brotli.compress/decompress`` call gated on import.
"""
from __future__ import annotations

import os
import zlib
from typing import Optional

_ENV_VAR = "CEO_CONTEXT_COMPRESS"
_DEFAULT_BACKEND = "zlib"
_VALID_BACKENDS = frozenset({"zlib", "brotli", "off"})


def _backend() -> str:
    """Return the configured backend, defaulting to ``zlib`` on unknown values."""
    raw = os.environ.get(_ENV_VAR, _DEFAULT_BACKEND).lower().strip()
    return raw if raw in _VALID_BACKENDS else _DEFAULT_BACKEND


def _try_brotli_compress(data: bytes, level: int) -> Optional[bytes]:
    """Attempt brotli compression. Returns None if brotli unavailable."""
    try:
        import brotli  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        quality = max(0, min(11, level))
        return brotli.compress(data, quality=quality)
    except Exception:
        return None


def _try_brotli_decompress(data: bytes) -> Optional[bytes]:
    """Attempt brotli decompression. Returns None on any failure."""
    try:
        import brotli  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return brotli.decompress(data)
    except Exception:
        return None


def compress(data: bytes, level: int = 9) -> bytes:
    """Compress ``data`` via the active backend.

    ``off`` returns ``data`` byte-identical. ``brotli`` tries the
    native library; on ImportError or runtime error the call silently
    falls back to zlib so the caller always gets a usable payload.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("compress() requires bytes-like input")
    if len(data) == 0:
        return b""
    backend = _backend()
    if backend == "off":
        return bytes(data)
    if backend == "brotli":
        got = _try_brotli_compress(bytes(data), level)
        if got is not None:
            return got
    zlib_level = max(0, min(9, level))
    return zlib.compress(bytes(data), zlib_level)


def decompress(data: bytes) -> bytes:
    """Decompress ``data``. Fail-open: on unrecognizable framing returns
    ``data`` unchanged so a hook calling this never aborts the user
    session on a corrupt cache payload.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("decompress() requires bytes-like input")
    if len(data) == 0:
        return b""
    backend = _backend()
    if backend == "off":
        return bytes(data)
    try:
        return zlib.decompress(bytes(data))
    except zlib.error:
        pass
    got = _try_brotli_decompress(bytes(data))
    if got is not None:
        return got
    return bytes(data)
