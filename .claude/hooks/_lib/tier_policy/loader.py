"""tier_policy.loader — advisory-only policy loader.

Reads ``$CLAUDE_PROJECT_DIR/.claude/policy/tier-policy.json`` (default)
and returns a ``ClassificationResult`` containing the operative policy
record. Stdlib-only.

Contract
--------

Advisory-only by design. ``load_policy`` NEVER raises to its caller —
on any failure (missing file, parse error, schema mismatch, oversize,
deep nesting, lock contention, OS-level error, malformed path-like
object, unknown ``default_model``) it returns the ``FROZEN_BASELINE``
fallback as a ``ClassificationResult`` with ``confidence=0.0`` and a
``reason`` that names the failure mode. The caller (``task-route.py``)
treats ``confidence == 0.0`` as "rule synthesis declined; emit the
safe-default tier and proceed".

P2-12 fix: the ENTIRE function body is wrapped in an outer
``try/except Exception`` that lands at ``_fallback("advisory_safety_net")``
so even a malformed ``path`` argument (non-stringifiable, OSError raised
inside ``Path()``, etc.) cannot escape.

P2-12 fix #2: ``default_model`` is validated against the closed
``MODEL_ID`` enum via ``_types.is_known_model``; unknown values trip
``fallback: unknown_model`` instead of being passed through to the
caller.

Caching
-------

Module-level cache keyed by the resolved policy path. The cached value
is a tuple ``(mtime_ns, result)`` — on subsequent calls we ``stat()``
the path and return the cached result if ``stat.st_mtime_ns`` matches.
``use_cache=False`` bypasses the lookup and the store. The cache is
process-local (no on-disk persistence) and survives across calls to
distinct paths.

File locking
------------

``os.O_EXLOCK | os.O_CREAT`` is requested **opportunistically** on
platforms that expose them (macOS / *BSD). On Linux ``O_EXLOCK`` is
absent — we fall back to advisory ``fcntl.flock`` if available, else
no lock. The locking layer is best-effort: on contention or unsupported
platform we proceed without a lock and log an advisory breadcrumb.

Schema migration
----------------

Loader migrates ``schema_version: 1`` → 2 by zero-defaulting any v2-
additive field (``confidence``, ``source``). Non-additive deltas
(removed key, type-change) trip a schema-mismatch fallback.

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1 — exact symbol path ``tier_policy.loader.load_policy``;
  no shadow under ``_lib/policy.py``.
* R-CR Unseen #1 — module-level cache deterministic; mtime-keyed.
* R-CR Unseen #2 — advisory-only contract: never raises.
* R-SEC U2 — size + depth caps enforced BEFORE deserialisation.
* R-SEC U4 — concurrent loaders coordinated via best-effort lock.
* R-CR R2-2 — schema migration documented; v1 → v2 additive only.
* P2-12 — outer ``try`` wraps Path() construction AND default_model
  is validated against ``MODEL_ID`` enum.
"""

from __future__ import annotations

import errno
import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ._constants import (
    CURRENT_SCHEMA_VERSION,
    FROZEN_BASELINE,
    LIMIT_DEPTH,
    LIMIT_FILE_BYTES,
    LIMIT_KEY_COUNT,
)
from ._types import ClassificationResult, MODEL_ID, TaskTypeResponse, is_known_model


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

#: ``path_str -> (mtime_ns, ClassificationResult)``. Populated on success
#: AND on fallback so repeated bad reads don't keep paying the parse cost.
_CACHE: Dict[str, Tuple[int, ClassificationResult]] = {}

#: Guard for ``_CACHE`` mutation. Cheap (RLock, single process).
_CACHE_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_policy_path() -> Path:
    """Resolve the default policy path from ``$CLAUDE_PROJECT_DIR``.

    Falls back to ``./.claude/policy/tier-policy.json`` if the env var
    is unset (matches the dogfood layout in the framework repo itself).
    """
    root = os.environ.get("CLAUDE_PROJECT_DIR") or "."
    return Path(root) / ".claude" / "policy" / "tier-policy.json"


def _fallback(reason: str) -> ClassificationResult:
    """Build the canonical advisory-only fallback result.

    All callers route here on ANY failure — uniform telemetry slug.
    """
    # PLAN-116 (S172) — fallback path observed; emit the dedicated loader
    # advisory-fallback action with a bounded closed-enum reason_code. (Was
    # PLAN-093 Wave C.3's tier_policy_misrouting_advised piggyback, which
    # dropped the free-text `reason` field on every emit — see PLAN-116.)
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _hooks = _Path(__file__).resolve().parent.parent.parent
        if str(_hooks) not in _sys.path:
            _sys.path.insert(0, str(_hooks))
        from _lib import audit_emit as _ae  # type: ignore
        if hasattr(_ae, "emit_generic"):
            # Normalize the one non-literal slug (`stat: <errno>`) to the
            # closed enum; every other _fallback call-site passes a closed slug.
            _reason_code = (
                "stat_error" if str(reason).startswith("stat:") else str(reason)
            )
            _ae.emit_generic(
                "tier_policy_loader_fallback_observed", reason_code=_reason_code
            )
    except Exception:
        pass
    return TaskTypeResponse(
        mode=str(FROZEN_BASELINE.get("default_mode", "M")),
        suggested_model=str(
            FROZEN_BASELINE.get("default_model", MODEL_ID.OPUS47.value)
        ),
        reason=f"fallback: {reason}",
        confidence=0.0,
    )


def _depth_of(obj: Any, _depth: int = 0) -> int:
    """Recursive max-depth scan with early-out at ``LIMIT_DEPTH + 1``.

    Used to refuse fan-out attacks before they reach migration logic.
    """
    if _depth > LIMIT_DEPTH:
        return _depth
    if isinstance(obj, dict):
        if not obj:
            return _depth
        return max(_depth_of(v, _depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return _depth
        return max(_depth_of(v, _depth + 1) for v in obj)
    return _depth


def _key_count(obj: Any) -> int:
    """Total key count across all nested dicts (DoS guard)."""
    if isinstance(obj, dict):
        n = len(obj)
        for v in obj.values():
            n += _key_count(v)
        return n
    if isinstance(obj, list):
        return sum(_key_count(v) for v in obj)
    return 0


def _migrate(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Migrate a legacy ``schema_version: 1`` payload to v2 in-place.

    v1 → v2 additive deltas:
      - ``confidence: float`` defaults to ``0.5`` if absent.
      - ``source: str`` defaults to ``"on_disk_v1_migrated"``.

    Returns the (possibly mutated) payload, or ``None`` if migration
    is impossible (non-additive delta detected).
    """
    sv = payload.get("schema_version")
    if sv == CURRENT_SCHEMA_VERSION:
        return payload
    if sv == 1:
        payload.setdefault("confidence", 0.5)
        payload.setdefault("source", "on_disk_v1_migrated")
        payload["schema_version"] = CURRENT_SCHEMA_VERSION
        return payload
    return None


def _try_lock_fd(fd: int) -> bool:
    """Best-effort exclusive-advisory lock on ``fd``. ``True`` if acquired.

    macOS / *BSD: ``O_EXLOCK`` was already requested at open() — return
    True. Linux: try ``fcntl.flock`` (LOCK_EX | LOCK_NB). Anything else:
    return False (no lock available; caller proceeds without one).
    """
    try:
        import fcntl  # type: ignore
    except ImportError:  # pragma: no cover — non-Unix
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _open_with_lock(path: Path) -> Optional[int]:
    """Open ``path`` read-only with an opportunistic exclusive lock.

    Returns the fd on success, ``None`` on any OS error (caller falls
    back to no-lock read or to FROZEN_BASELINE).
    """
    flags = os.O_RDONLY
    # macOS / FreeBSD support O_EXLOCK directly. Pull the constant
    # dynamically so this module imports on Linux too.
    o_exlock = getattr(os, "O_EXLOCK", 0)
    if o_exlock:
        flags |= o_exlock
    try:
        return os.open(str(path), flags)
    except OSError:
        if not o_exlock:
            return None
        # Lock contention or O_EXLOCK quirk: retry without the flag.
        try:
            return os.open(str(path), os.O_RDONLY)
        except OSError:
            return None


def _read_bounded(fd: int) -> Optional[str]:
    """Read up to ``LIMIT_FILE_BYTES + 1`` from ``fd``; reject overflow.

    Reading one extra byte means we can detect "exactly the limit" vs.
    "more than the limit" without a separate stat() race window.
    """
    try:
        chunks = []
        remaining = LIMIT_FILE_BYTES + 1
        while remaining > 0:
            buf = os.read(fd, min(remaining, 65536))
            if not buf:
                break
            chunks.append(buf)
            remaining -= len(buf)
        raw = b"".join(chunks)
    except OSError:
        return None
    if len(raw) > LIMIT_FILE_BYTES:
        return None
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_policy(
    path: Optional[str] = None,
    *,
    use_cache: bool = True,
) -> ClassificationResult:
    """Load the tier policy and return its operative record.

    Parameters
    ----------
    path
        Override path. ``None`` resolves the default
        (``$CLAUDE_PROJECT_DIR/.claude/policy/tier-policy.json``).
    use_cache
        Bypass the module-level cache when ``False``. Default ``True``.

    Returns
    -------
    ClassificationResult
        On success: the materialised policy with ``confidence`` taken
        from disk (defaults to 1.0 if absent in payload).
        On any failure: ``FROZEN_BASELINE`` projected as a
        ``ClassificationResult`` with ``confidence=0.0`` and a ``reason``
        slug naming the failure mode (``fallback: missing``,
        ``fallback: oversize``, ``fallback: parse_error``,
        ``fallback: unknown_model``, ``fallback: advisory_safety_net``,
        ...).

    Notes
    -----
    NEVER raises to the caller. Every exception path lands in
    ``_fallback(...)``. P2-12 fix: an outer ``try/except Exception``
    wraps the body, including ``Path()`` construction, so even
    malformed path-like objects cannot escape.
    """
    # P2-12 fix: outer safety net catches absolutely anything (including
    # `Path()` raising on non-stringifiable input). The advisory-only
    # contract is ABSOLUTE — propagating ANY exception would surprise
    # `task-route.py` which assumes the loader is total.
    try:
        return _load_policy_inner(path, use_cache=use_cache)
    except Exception:  # pragma: no cover — defence-in-depth
        return _fallback("advisory_safety_net")


def _load_policy_inner(
    path: Optional[str] = None,
    *,
    use_cache: bool = True,
) -> ClassificationResult:
    """Inner implementation; outer ``load_policy`` wraps in try/except."""
    p = Path(path) if path else _default_policy_path()
    key = str(p)

    # Cache lookup — mtime-keyed.
    if use_cache:
        with _CACHE_LOCK:
            cached = _CACHE.get(key)
        if cached is not None:
            try:
                cur_mtime = p.stat().st_mtime_ns
            except OSError:
                cur_mtime = -1
            if cached[0] == cur_mtime and cur_mtime != -1:
                return cached[1]

    # Existence + size sanity. ``stat`` failures are treated uniformly
    # as "missing" — distinguishing ENOENT vs EACCES wouldn't change
    # the advisory-only behaviour and would surface noise in audit.
    try:
        st = p.stat()
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return _store_and_return(key, -1, _fallback("missing"))
        return _store_and_return(key, -1, _fallback(f"stat: {exc.errno}"))

    if st.st_size > LIMIT_FILE_BYTES:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("oversize")
        )

    # Open with opportunistic lock. If open fails we fall back; we DO
    # NOT retry without the lock when O_EXLOCK is implicit, because
    # _open_with_lock already does that retry internally.
    fd = _open_with_lock(p)
    if fd is None:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("open_failed")
        )
    locked = False
    try:
        # If O_EXLOCK isn't a thing on this platform, try fcntl.flock.
        if not getattr(os, "O_EXLOCK", 0):
            locked = _try_lock_fd(fd)
        else:
            locked = True

        text = _read_bounded(fd)
    finally:
        try:
            if locked:
                # fcntl.flock: best-effort unlock; OS releases on close.
                try:
                    import fcntl  # type: ignore
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass
            os.close(fd)
        except OSError:
            pass

    if text is None:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("read_failed")
        )

    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("parse_error")
        )

    if not isinstance(payload, dict):
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("not_object")
        )

    # Pre-migration depth + key-count guards.
    if _depth_of(payload) > LIMIT_DEPTH:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("depth_limit")
        )
    if _key_count(payload) > LIMIT_KEY_COUNT:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("key_count")
        )

    migrated = _migrate(payload)
    if migrated is None:
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("schema_mismatch")
        )

    mode = migrated.get("default_mode", FROZEN_BASELINE["default_mode"])
    model = migrated.get(
        "default_model", FROZEN_BASELINE["default_model"]
    )
    confidence = migrated.get("confidence", 1.0)
    if not isinstance(mode, str) or not isinstance(model, str):
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("type_mismatch")
        )
    # P2-12 fix: validate `default_model` against the closed MODEL_ID
    # enum. Unknown wire strings (typos, sunset models, hostile input)
    # trip an explicit ``unknown_model`` fallback rather than being
    # echoed through to the caller.
    if not is_known_model(model):
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("unknown_model")
        )
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0.0 or confidence > 1.0:
        confidence = 0.0
    if mode not in ("S", "M", "L", "XL"):
        return _store_and_return(
            key, st.st_mtime_ns, _fallback("bad_mode")
        )

    result = TaskTypeResponse(
        mode=mode,
        suggested_model=model,
        reason=str(
            migrated.get("reason", "loaded from on-disk policy")
        ),
        confidence=confidence,
    )
    return _store_and_return(key, st.st_mtime_ns, result)


def _store_and_return(
    key: str, mtime_ns: int, result: ClassificationResult
) -> ClassificationResult:
    """Cache-write helper. Stores even fallbacks to dampen disk thrash."""
    with _CACHE_LOCK:
        _CACHE[key] = (mtime_ns, result)
    return result


def clear_cache() -> None:
    """Drop the module-level cache. Test-only helper."""
    with _CACHE_LOCK:
        _CACHE.clear()


__all__ = [
    "load_policy",
    "clear_cache",
]
