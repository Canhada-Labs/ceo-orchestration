"""HMAC chain helpers for audit-log integrity (ADR-055 / PLAN-023 Phase B).

Per-entry chain::

    hmac = hmac_sha256(key, prev_hmac || canonical_json(entry_sans_hmac))

where:

- ``key`` — 32 random bytes at ``~/.claude/projects/<slug>/audit-key``
  (0600 perms, owned by effective UID).
- ``prev_hmac`` — 32 raw bytes (not hex). Genesis = ``b'\\x00' * 32``.
- canonical_json — see :mod:`._lib.canonical_json`.

## Guarantees (detection-only)

- **Forgery** — any bit flip in a covered field breaks the chain forward.
- **Reorder** — swapping entries recomputes to a different HMAC.
- **Deletion** of interior entries — next-entry HMAC reference breaks.

## Does NOT guarantee

- **Prevention** of tamper (only detection post-facto).
- **Tail truncation** — attacker deletes last N entries; head remains
  internally consistent. Post-v1.6.0 mitigation: external OTEL anchor
  or remote append-only sink.
- **Key theft** — attacker with ``$HOME`` read access can forge.
- **Rollback** — attacker restores older log+key pair; verifies clean.

See ``.claude/adr/ADR-055-audit-log-hmac-chain.md`` §Threat Model
§Out-of-scope for the complete residual list.

## Fail-open invariant

All functions raise :class:`AuditHmacError` on precondition violation
(key absent, wrong perms, sidecar corrupt). Callers (audit_emit.py)
MUST catch + continue with ``hmac: null`` + ``hmac_error: <reason>``
per the fail-open invariant (hook never blocks the user session).

## Concurrency model

This module does NOT take the audit-log FileLock; callers hold the
lock before calling :func:`read_prev_hmac` or :func:`write_last_hmac`.
Only the read-modify-write sequence under that lock is safe against
concurrent subprocess writes (chain-fork defect if unlocked; see
performance-engineer review §3b).

## Kill-switch

``CEO_AUDIT_HMAC_DISABLE=1`` short-circuits the HMAC path.
:func:`is_disabled` exposes the check.
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
import os
import secrets
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from . import canonical_json
except ImportError:  # pragma: no cover
    import canonical_json  # type: ignore[no-redef]


# Size constants
KEY_BYTES = 32
HMAC_BYTES = 32
HMAC_HEX_LEN = HMAC_BYTES * 2  # 64
GENESIS_PREV = b"\x00" * HMAC_BYTES

# Sidecar filename for the last-HMAC (simpler/faster than seek-from-end
# per performance-engineer review §5). Written without fsync inside the
# same lock as the log append; reconstructible from log tail if lost.
LAST_HMAC_FILENAME = "audit-log.last-hmac"
KEY_FILENAME = "audit-key"

# PLAN-045 Wave 1 F-01-05 — chain-length canary sidecar.
# Monotonic counter of HMAC-bearing entries written to the log. Each
# successful write increments by 1. ``verify_chain(strict_against_counter=True)``
# fails if the chain walk counts fewer entries than this counter —
# detects bulk tail deletion (a valid chain can still be valid after
# the tail is cut off, because the head is internally consistent; the
# counter is the canary that "N entries were previously written").
CHAIN_LENGTH_FILENAME = "audit-log.chain-length"

# PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 / ADR-055-AMEND-2 — rotation
# manifest sidecar. Written by producer on rotation (or by Wave B.2
# quarantine ceremony); verifier reads to scope chain_reset_marker
# enforcement to rotation-created fresh logs only (NOT first-install logs
# that legitimately have no marker). Manifest schema:
#   {
#     "rotated_at": "2026-05-21T14:38:00Z",  # ISO-8601 UTC
#     "previous_archive_filename": "audit-log-2026-05-21-pre-fix-tampered.jsonl",
#     "marker_line_count": 1,  # always 1 (marker is single line)
#     "schema_version": "v1"
#   }
ROTATION_MANIFEST_FILENAME = "audit-log.rotation-manifest.json"


class AuditHmacError(Exception):
    """Raised on HMAC precondition violation (key/sidecar/perm issue)."""


class AuditProducerPathPollutionError(AuditHmacError):
    """PLAN-118 AC-B4 — producer-side canonical-resolution mismatch.

    Raised by :func:`compute_entry_hmac` (or the helper it calls) when
    any of ``_lib.audit_emit`` / ``_lib.canonical_json`` / ``_lib.audit_hmac``
    in :data:`sys.modules` resolves to a non-canonical ``_lib/`` parent
    on disk — i.e. a stale `_lib` copy has been injected onto
    :data:`sys.path`. Subclasses :class:`AuditHmacError` so existing
    fail-open ``except AuditHmacError`` patterns in ``audit_emit`` +
    ``spool_writer`` catch this transparently and route the entry to the
    ``hmac:null`` + ``hmac_error=producer_path_pollution_detected``
    channel (fail-CLOSED for the chain; fail-OPEN for the host hook —
    user session NEVER blocked).
    """


# PLAN-118 AC-B4 — canonical `_lib/` self-locator for producer-side
# canonical-resolution mismatch detection in :func:`compute_entry_hmac`.
# Resolves the directory containing THIS module (audit_hmac.py) at
# import time. Used as the reference parent against which producer
# modules' resolved ``__file__`` is compared.
#
# Threat coverage:
#   - stale audit_emit.py on sys.path → resolved_parent != canonical → CATCH
#   - stale canonical_json.py on sys.path → CATCH
#   - fully-stale `_lib/` tree (audit_hmac + audit_emit + canonical_json
#     all in the SAME stale dir) → _CANONICAL_LIB_DIR resolves to the
#     stale dir → FALSE-OK at this layer. Defense-in-depth: the
#     WS-B conftest snapshot guard + the in-tree pytest regression
#     (`.claude/hooks/tests/test_lib_canonical_import.py`) catch the
#     fully-stale case at test-collection time.
_CANONICAL_LIB_DIR = Path(__file__).resolve().parent


# Process-level cache (single subprocess invocation lifetime).
# The audit-key does not rotate mid-invocation so caching is safe.
_KEY_CACHE: Optional[bytes] = None


def is_disabled() -> bool:
    """Return True if ``CEO_AUDIT_HMAC_DISABLE=1``."""
    return os.environ.get("CEO_AUDIT_HMAC_DISABLE", "") == "1"


def _audit_dir_from_env() -> Path:
    """Resolve the audit dir, aligned with audit_emit._audit_dir().

    Precedence mirrors audit_emit + spool_writer so the HMAC sidecars
    (key, last-hmac, chain-length) co-locate with the audit log + its
    FileLock under the coherent-env contract (processes writing one log
    share the same CEO_AUDIT_LOG_DIR, or all run pure-$HOME):

      ``CEO_AUDIT_LOG_DIR`` (primary — matches audit_emit._audit_dir) ->
      ``CEO_AUDIT_LOG_PATH`` parent -> ``CEO_PROJECT_STATE_DIR`` ->
      ``$HOME/.claude/projects/ceo-orchestration/``.

    Honoring CEO_AUDIT_LOG_DIR closes a latent split (S168): a LOG_DIR-only
    process resolved its FileLock under LOG_DIR but its chain-length counter
    under $HOME, so two such processes (same $HOME, different LOG_DIR)
    shared one counter while holding different locks — a lost counter
    increment that weakens tail-truncation detection.
    """
    log_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if log_dir:
        return Path(log_dir)
    p = os.environ.get("CEO_AUDIT_LOG_PATH")
    if p:
        return Path(p).resolve().parent
    state = os.environ.get("CEO_PROJECT_STATE_DIR")
    if state:
        return Path(state)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def key_path() -> Path:
    """Return the resolved audit-key path (sibling of audit-log.jsonl)."""
    override = os.environ.get("CEO_AUDIT_KEY_PATH")
    if override:
        return Path(override)
    return _audit_dir_from_env() / KEY_FILENAME


def last_hmac_path() -> Path:
    """Return the sidecar path carrying the last HMAC hex string."""
    override = os.environ.get("CEO_AUDIT_LAST_HMAC_PATH")
    if override:
        return Path(override)
    return _audit_dir_from_env() / LAST_HMAC_FILENAME


def chain_length_path() -> Path:
    """Return the chain-length canary sidecar path.

    PLAN-045 Wave 1 F-01-05: monotonic counter of HMAC-bearing entries
    written to the log. Allows ``verify_chain`` ``--strict`` mode to
    detect tail truncation even when the remaining log + sidecar are
    internally consistent.

    ``CEO_AUDIT_CHAIN_LENGTH_PATH`` env override mirrors the other
    audit-log sidecar path helpers for test isolation.
    """
    override = os.environ.get("CEO_AUDIT_CHAIN_LENGTH_PATH")
    if override:
        return Path(override)
    return _audit_dir_from_env() / CHAIN_LENGTH_FILENAME


def _check_perm_0600(p: Path) -> None:
    """Raise AuditHmacError on unsafe permissions, ownership, or symlinks.

    PLAN-045 Wave 1 F-01-06 hardening:

    1. **Symlink reject.** A 0600 symlink pointing to an attacker file
       passes a naive mode check; reject any symlink leaf outright.
    2. **Ownership check.** ``st_uid == os.getuid()``. On a multi-user
       host, a 0600 file owned by a different user (e.g. inherited via
       ``chown`` after a hostile ``git stash pop``) previously passed
       this check; now it fails.
    3. **Group/world bits.** Retained from the existing check
       (security-engineer review §2): ``mode & 0o077 != 0`` fails.

    Parent-dir perms are validated at the caller in
    :func:`get_or_create_key` via ``parent.mkdir(mode=0o700)``; a parent
    created with different perms will be re-mkdir'd (mkdir is idempotent
    only on existence, not perms — the mode arg has no effect once the
    dir exists). The belt-and-suspenders parent-dir check is in
    :func:`_check_parent_dir_owned_0700` for callers that want it.
    """
    try:
        if p.is_symlink():
            raise AuditHmacError(
                "refusing to use symlinked audit-key at {p}".format(p=p)
            )
    except OSError as e:
        raise AuditHmacError(
            "is_symlink check failed on {p}: {e}".format(p=p, e=e)
        ) from e
    try:
        st = p.stat()
    except OSError as e:
        raise AuditHmacError("stat failed on {p}: {e}".format(p=p, e=e)) from e
    if st.st_uid != os.getuid():
        raise AuditHmacError(
            "audit-key ownership mismatch at {p}: owned by uid {u} "
            "(expected {e})".format(p=p, u=st.st_uid, e=os.getuid())
        )
    if st.st_mode & 0o077 != 0:
        raise AuditHmacError(
            "unsafe perms on {p}: {m} "
            "(must be owner-only 0600; group/world bits present)".format(
                p=p, m=stat.filemode(st.st_mode)
            )
        )


def _check_parent_dir_owned_0700(p: Path) -> None:
    """PLAN-045 Wave 1 F-01-06: optional parent-dir hardening check.

    Not called from :func:`_check_perm_0600` automatically because the
    parent-dir is created via ``mkdir(mode=0o700)`` on key creation
    path, and enforcing it on every :func:`read_prev_hmac` or
    :func:`write_last_hmac` would be overly strict on hosts with
    historically-created state dirs. Callers that want the strictest
    invariant (e.g. :func:`verify_chain` in ``--strict`` mode) invoke
    this explicitly.

    Raises AuditHmacError on: parent missing / symlinked / not owned
    by us / mode not 0700.
    """
    parent = p.parent
    try:
        if parent.is_symlink():
            raise AuditHmacError(
                "audit-key parent is a symlink: {p}".format(p=parent)
            )
        if not parent.is_dir():
            raise AuditHmacError(
                "audit-key parent is not a directory: {p}".format(p=parent)
            )
        st = parent.stat()
    except OSError as e:
        raise AuditHmacError(
            "parent-dir stat failed on {p}: {e}".format(p=parent, e=e)
        ) from e
    if st.st_uid != os.getuid():
        raise AuditHmacError(
            "audit-key parent ownership mismatch at {p}: owned by uid {u}".format(
                p=parent, u=st.st_uid
            )
        )
    if (st.st_mode & 0o777) != 0o700:
        raise AuditHmacError(
            "audit-key parent perms on {p}: {m} "
            "(must be 0700)".format(p=parent, m=stat.filemode(st.st_mode))
        )


def get_or_create_key() -> bytes:
    """Return the 32-byte audit-key, generating it atomically if absent.

    Process-level cache: first call reads or generates + validates perms
    + caches; subsequent calls return the cached value.

    :raises AuditHmacError: on filesystem error or perm violation.
    """
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE

    p = key_path()
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    if not p.exists():
        # Atomic create: write to tempfile with O_EXCL → rename.
        # Race-safe against parallel audit_log invocations because we
        # check existence after write and prefer the already-existing
        # key.
        tmp = p.with_name(p.name + ".tmp.{pid}".format(pid=os.getpid()))
        try:
            fd = os.open(
                str(tmp),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            try:
                os.write(fd, secrets.token_bytes(KEY_BYTES))
            finally:
                os.close(fd)
            if p.exists():
                # Another process created the real key; discard ours.
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            else:
                os.replace(str(tmp), str(p))
        except FileExistsError:
            # tmp existed (stale). Remove + fall through to the read.
            try:
                if tmp.exists():
                    os.unlink(tmp)
            except OSError:
                pass
        except OSError as e:
            try:
                if tmp.exists():
                    os.unlink(tmp)
            except OSError:
                pass
            raise AuditHmacError(
                "could not create {p}: {e}".format(p=p, e=e)
            ) from e

    _check_perm_0600(p)

    try:
        data = p.read_bytes()
    except OSError as e:
        raise AuditHmacError(
            "could not read {p}: {e}".format(p=p, e=e)
        ) from e

    if len(data) != KEY_BYTES:
        raise AuditHmacError(
            "{p} is {n} bytes, expected {k}".format(
                p=p, n=len(data), k=KEY_BYTES
            )
        )

    _KEY_CACHE = data
    return data


def _reset_key_cache_for_test() -> None:
    """Test helper: drop the process-level key cache."""
    global _KEY_CACHE
    _KEY_CACHE = None


def read_prev_hmac() -> bytes:
    """Return the binary previous-HMAC or the genesis value.

    Reads the sidecar ``audit-log.last-hmac`` (hex-encoded 64 chars +
    optional trailing newline). If absent or malformed → genesis.
    Fail-open invariant: a corrupted sidecar must not block writes.
    The log tail itself remains the source of truth; verify-chain
    re-reads from the log, not the sidecar.

    MUST be called WITH the audit-log FileLock held.
    """
    p = last_hmac_path()
    if not p.exists():
        return GENESIS_PREV
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except OSError:
        return GENESIS_PREV
    if len(raw) != HMAC_HEX_LEN:
        return GENESIS_PREV
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return GENESIS_PREV


def write_last_hmac(digest: bytes) -> None:
    """Persist the last HMAC to the sidecar (best-effort, no fsync).

    Performance-engineer review §10 red flag #1: a second fsync under
    the lock doubles variance. The sidecar is reconstructible from
    log tail so skipping fsync is the right trade-off. If the sidecar
    is corrupt or absent after a crash, :func:`read_prev_hmac` returns
    genesis and the chain reseals on next write (operator sees a
    one-line break in verify-chain, distinguishable from tamper via
    monotonic ``ts``).

    MUST be called WITH the audit-log FileLock held.
    """
    if len(digest) != HMAC_BYTES:
        raise AuditHmacError(
            "digest is {n} bytes, expected {k}".format(
                n=len(digest), k=HMAC_BYTES
            )
        )
    p = last_hmac_path()
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = p.with_name(p.name + ".tmp.{pid}".format(pid=os.getpid()))
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(digest.hex())
        os.replace(str(tmp), str(p))
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    except OSError as e:
        try:
            if tmp.exists():
                os.unlink(tmp)
        except OSError:
            pass
        raise AuditHmacError(
            "could not write {p}: {e}".format(p=p, e=e)
        ) from e


def reset_chain_on_rotation() -> None:
    """Clear the sidecars so the new file starts with a genesis chain.

    PLAN-045 Wave 1 F-01-05 extension: also clears the chain-length
    canary sidecar. Rotation renames the log to an archive file; the
    new log starts at genesis + chain-length 0. Historical archive
    files retain the canary value at time of rotation (verification of
    archives falls back to walking each archive independently — the
    current live chain has no memory of archived counters).

    MUST be called WITH the audit-log FileLock held, after the log
    rename but before the new file's first write.
    """
    for p in (last_hmac_path(), chain_length_path()):
        try:
            if p.exists():
                p.unlink()
        except OSError:
            # Best-effort: next read falls back to genesis / 0 if the
            # sidecar is corrupt or absent.
            pass


# ---------------------------------------------------------------------------
# Chain-length canary (PLAN-045 Wave 1 F-01-05) — ACTIVE since v1.11.x
# ---------------------------------------------------------------------------
# audit-v2 (2026-04-27) C6-P0-03 closed Wave D-2 (2026-04-28):
# `audit_emit._write_event` now calls `write_chain_length(n+1)` under
# the same FileLock as `write_last_hmac`, gate-guarded on
# (`_HMAC_AVAILABLE` AND `event["hmac"]` AND `not is_disabled()`).
#
# Tail-truncation detection is now active:
#   - `read_chain_length()` returns the persisted counter
#   - `verify_chain(strict_against_counter=True)` compares walker-count
#     vs counter; counter > walker -> STATUS_TAMPER with
#     reason="chain_length_truncation"
#
# Forensic limitation (forward-only): tail-truncation detection is
# active for entries written AFTER the canary-wire commit. Pre-wire
# entries rely solely on the per-entry HMAC chain. See
# `docs/STATE-RECOVERY.md` ("Chain-length canary forward-only").
#
# Threat-model limitation (deferred to C6-P0-03b): the counter sidecar
# is plaintext, defending only against truncate-only attackers. An
# attacker with audit-dir write access can rewrite the counter to match
# a truncated walker count. Hardening (HMAC-protected counter) is
# tracked as follow-up.
#
# Active defenses for chain integrity:
#   - Per-entry HMAC chain (verified by verify_chain at audit-time)
#   - HMAC chain reset on log rotation (reset_chain_on_rotation)
#   - Per-event hash salting (UserPromptSubmit.py:182)
#   - Chain-length canary (this section, wired Wave D-2)
# ---------------------------------------------------------------------------


def read_chain_length() -> int:
    """Return the persisted chain-length counter, or 0 if absent/malformed.

    Fail-open: a missing or corrupt sidecar returns 0 (the genesis
    value). ``verify_chain(strict_against_counter=True)`` treats any
    walker-count >= returned-counter as pass; counter > walker indicates
    tail truncation and fails-closed.

    MUST be called WITH the audit-log FileLock held.
    """
    p = chain_length_path()
    if not p.exists():
        return 0
    try:
        raw = p.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    if not raw:
        return 0
    try:
        n = int(raw)
    except ValueError:
        return 0
    if n < 0:
        return 0
    return n


def write_chain_length(n: int) -> None:
    """Persist the chain-length counter (atomic rename, 0600 perms).

    Called by ``audit_emit._write_event`` after each successful HMAC
    entry write. Monotonic; caller is responsible for incrementing
    against ``read_chain_length() + 1``.

    Fail-open: raises ``AuditHmacError`` so the caller can decide
    whether to skip the canary update (fail-open) or propagate. The
    canary is a detection aid, not a correctness requirement.

    MUST be called WITH the audit-log FileLock held.
    """
    if n < 0:
        raise AuditHmacError(
            "chain-length must be non-negative, got {n}".format(n=n)
        )
    p = chain_length_path()
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = p.with_name(p.name + ".tmp.{pid}".format(pid=os.getpid()))
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(str(n))
        os.replace(str(tmp), str(p))
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    except OSError as e:
        try:
            if tmp.exists():
                os.unlink(tmp)
        except OSError:
            pass
        raise AuditHmacError(
            "could not write {p}: {e}".format(p=p, e=e)
        ) from e


def rotation_manifest_path() -> Path:
    """Return path to audit-log.rotation-manifest.json sidecar."""
    return _audit_dir_from_env() / ROTATION_MANIFEST_FILENAME


def write_rotation_manifest(
    previous_archive_filename: str,
    rotated_at: str,
) -> None:
    """Write rotation manifest sidecar per ADR-055-AMEND-2.

    Called by producer rotation paths + Wave B.2 quarantine ceremony.
    MUST be called WITH the audit-log FileLock held.

    Fail-open: raises AuditHmacError on I/O failure; caller chooses
    whether to abort the rotation (fail-closed) or proceed without the
    manifest (fail-open; verifier falls back to legacy mode).
    """
    import json as _json
    manifest = {
        "schema_version": "v1",
        "rotated_at": str(rotated_at)[:32],
        "previous_archive_filename": str(previous_archive_filename)[:256],
        "marker_line_count": 1,
    }
    p = rotation_manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = p.with_name(p.name + ".tmp.{pid}".format(pid=os.getpid()))
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            _json.dump(manifest, f, separators=(",", ":"), ensure_ascii=False)
        os.replace(str(tmp), str(p))
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    except OSError as e:
        try:
            if tmp.exists():
                os.unlink(tmp)
        except OSError:
            pass
        raise AuditHmacError(
            "could not write rotation manifest {p}: {e}".format(p=p, e=e)
        ) from e


def read_rotation_manifest() -> Optional[Dict[str, Any]]:
    """Read rotation manifest sidecar if present.

    Returns the parsed manifest dict, or None if the sidecar is absent
    (legacy mode — no marker enforcement). Returns None on parse failure
    (fail-open; verifier falls back to legacy mode for malformed manifest;
    caller may distinguish absent vs malformed if needed).
    """
    import json as _json
    p = rotation_manifest_path()
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = _json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    return None


def delete_rotation_manifest() -> None:
    """Delete rotation manifest sidecar if present (fail-open).

    Used when manually resetting or for testing. Production rotation
    overwrites the manifest atomically via write_rotation_manifest;
    explicit deletion is for cleanup paths only.
    """
    p = rotation_manifest_path()
    if p.exists():
        try:
            p.unlink()
        except OSError:
            pass


_CANONICAL_LIB_MODULES = ("_lib.audit_emit", "_lib.canonical_json", "_lib.audit_hmac")


def path_sha256_prefix(p: "Path | str") -> str:
    """PLAN-118 AC-B5 — 8-hex-char sha256 prefix of a path's str form.

    Used by :class:`AuditProducerPathPollutionError` + AC-B5 closed-enum
    breadcrumb payload (no raw path echo per
    [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    """
    return hashlib.sha256(str(p).encode("utf-8")).hexdigest()[:8]


def _ensure_canonical_lib_modules() -> Optional[str]:
    """PLAN-118 AC-B4 — canonical-resolution check for producer modules.

    Walks :data:`sys.modules` for ``_lib.audit_emit`` / ``_lib.canonical_json``
    / ``_lib.audit_hmac``; for each module present, resolves its
    ``__file__`` to absolute and asserts the parent matches
    :data:`_CANONICAL_LIB_DIR`. On mismatch raises
    :class:`AuditProducerPathPollutionError` with an 8-hex-prefix payload
    (NO raw path echo). On clean state returns the matched ``reason_code``
    for the producer (callers use this for AC-B5 breadcrumb emission).

    Bounded ~5us per call (3 dict lookups + ≤3 :meth:`Path.resolve` calls).
    Called from chokepoints 1/3 in ``audit_emit.py``, chokepoint 4 in
    ``spool_writer.py`` _phase4_build_batch, and chokepoint 5 here at
    :func:`compute_entry_hmac` entry.
    """
    import sys as _sys
    for mod_name in _CANONICAL_LIB_MODULES:
        mod = _sys.modules.get(mod_name)
        if mod is None:
            # Module not yet imported by this process. compute_entry_hmac
            # may be invoked from a probe before the producer is loaded;
            # the producer-side chokepoints catch the emit-time case.
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            continue  # builtins / frozen / namespace package
        try:
            resolved_parent = Path(mod_file).resolve().parent
        except (OSError, ValueError):
            continue  # symlink loop / weird path — fail-open at this layer
        if resolved_parent != _CANONICAL_LIB_DIR:
            # PLAN-118 AC-B4 + AC-B5: refuse to compute HMAC; payload
            # carries sha256[:8] prefixes only (no path echo).
            reason_code = {
                "_lib.audit_emit": "audit_emit_path_pollution",
                "_lib.canonical_json": "canonical_json_path_pollution",
                "_lib.audit_hmac": "audit_hmac_path_pollution",
            }[mod_name]
            raise AuditProducerPathPollutionError(
                "non_canonical_lib_resolution: "
                f"reason_code={reason_code} "
                f"path_sha256_prefix={path_sha256_prefix(resolved_parent)} "
                f"expected_canonical_prefix={path_sha256_prefix(_CANONICAL_LIB_DIR)}"
            )
    return None


def compute_entry_hmac(
    key: bytes,
    prev_hmac: bytes,
    entry_without_hmac: Dict[str, Any],
) -> bytes:
    """Compute ``hmac_sha256(key, prev_hmac || canonical_json(entry))``.

    ``entry_without_hmac`` MUST NOT contain an ``hmac`` field; strip
    it before calling. The canonical encoding routes through
    :func:`_lib.canonical_json.encode`, which pins all serialization
    kwargs and enforces the no-float + NFC invariants.

    PLAN-118 AC-B4 — entry-side canonical-resolution check
    (:func:`_ensure_canonical_lib_modules`) refuses to produce the HMAC
    if a stale `_lib` copy is on :data:`sys.path`. Raises
    :class:`AuditProducerPathPollutionError` (subclass of
    :class:`AuditHmacError`) — callers' fail-open patterns transparently
    route to ``hmac:null`` + ``hmac_error=producer_path_pollution_detected``.

    :return: 32 raw bytes (not hex).
    """
    _ensure_canonical_lib_modules()  # PLAN-118 AC-B4 chokepoint 5
    if len(key) != KEY_BYTES:
        raise AuditHmacError(
            "key is {n} bytes, expected {k}".format(n=len(key), k=KEY_BYTES)
        )
    if len(prev_hmac) != HMAC_BYTES:
        raise AuditHmacError(
            "prev_hmac is {n} bytes, expected {k}".format(
                n=len(prev_hmac), k=HMAC_BYTES
            )
        )
    canon = canonical_json.encode(entry_without_hmac)
    msg = prev_hmac + canon
    return _hmac.new(key, msg, hashlib.sha256).digest()


def hex_digest(digest: bytes) -> str:
    """Return the 64-hex-char form of a 32-byte HMAC."""
    if len(digest) != HMAC_BYTES:
        raise AuditHmacError(
            "digest is {n} bytes, expected {k}".format(
                n=len(digest), k=HMAC_BYTES
            )
        )
    return digest.hex()


def from_hex(s: str) -> bytes:
    """Parse a 64-hex-char string into 32 raw bytes."""
    if len(s) != HMAC_HEX_LEN:
        raise AuditHmacError(
            "hex string is {n} chars, expected {k}".format(
                n=len(s), k=HMAC_HEX_LEN
            )
        )
    try:
        out = bytes.fromhex(s)
    except ValueError as e:
        raise AuditHmacError(
            "not a hex string: {e}".format(e=e)
        ) from e
    if len(out) != HMAC_BYTES:
        raise AuditHmacError(
            "decoded {n} bytes, expected {k}".format(
                n=len(out), k=HMAC_BYTES
            )
        )
    return out


# ---------------------------------------------------------------------------
# Chain verification — library API (PLAN-043 Phase 0.5 / C-P0-7 closure)
# ---------------------------------------------------------------------------
#
# Extracted from `.claude/scripts/audit-verify-chain.py::verify()` per
# PLAN-043 Round 1 debate convergent finding C-P0-7: PLAN-043/ADR-064
# referenced `verify_chain()` / `compute_chain()` library functions that
# did NOT exist in this module. Chain-walk logic lived only in the CLI.
#
# This library function:
# - Accepts explicit `key` (bytes) OR `key_path_override` (Path) OR
#   defaults to :func:`key_path`. Supports PLAN-043 use of separate
#   tier-policy key (F-SEC-P0-2 key isolation).
# - Returns a structured :class:`VerifyResult` dataclass; caller decides
#   exit-code mapping / report formatting.
# - Does NOT call sys.exit, does NOT write stderr, does NOT depend on
#   argparse. Pure function of (log_path, key, since) → result.
# - Preserves the chain state machine exactly: genesis = zero bytes;
#   CHAIN_START tolerates pre-v2.9 entries without hmac field;
#   CHAIN_ACTIVE rejects hmac-less entries (transition-entry rule).
# - Additive API; zero behavior change for existing audit-verify-chain.py
#   callers (CLI now imports + adapts output).

STATUS_INTACT = "intact"
STATUS_TAMPER = "tamper"
STATUS_MALFORMED = "malformed"
STATUS_KEY_MISSING = "key_missing"
STATUS_PERM_ERROR = "perm_error"


@dataclass
class VerifyResult:
    """Structured result of :func:`verify_chain`.
    # F-13-08 forensic fields — populated on verify failure
    prev_hmac: Optional[str] = None
    session_id: Optional[str] = None
    entry_snippet: Optional[str] = None
    chain_boundary: Optional[str] = None
    total_lines_seen: int = 0

    ``status`` is one of the STATUS_* constants. On ``intact``, all
    other fields describe counts / None; on failure statuses, ``line``
    points at the offending 1-indexed line and ``reason`` is a short
    stable tag.

    Fields:
        status: outcome tag (intact|tamper|malformed|key_missing|perm_error)
        line: 1-indexed line where failure detected (None on intact)
        reason: short stable reason tag (transition_violation,
            hmac_field_malformed, hmac_mismatch, key_not_found,
            key_bad_perms, log_not_found, line_not_json,
            line_not_object, hmac_compute_failed, hmac_parse_failed)
        verified_count: number of CHAIN_ACTIVE entries successfully
            verified
        pre_v29_count: number of CHAIN_START entries tolerated
            (no hmac field)
        entry_ts: timestamp of offending entry (None on intact)
        entry_action: action of offending entry (None on intact)
        expected_hmac: recomputed hex HMAC at offending entry (None
            on intact or non-hmac-mismatch failures)
        actual_hmac: recorded hex HMAC at offending entry (None on
            intact or non-hmac-mismatch failures)
    """

    status: str
    line: Optional[int] = None
    reason: Optional[str] = None
    verified_count: int = 0
    pre_v29_count: int = 0
    entry_ts: Optional[str] = None
    entry_action: Optional[str] = None
    expected_hmac: Optional[str] = None
    actual_hmac: Optional[str] = None

    @property
    def is_intact(self) -> bool:
        """Convenience: True iff chain is fully verified."""
        return self.status == STATUS_INTACT


def _read_key_file(p: Path) -> bytes:
    """Read + validate a 32-byte key file with 0600 perms, uid, no symlink.

    Unlike :func:`get_or_create_key`, this does NOT generate if absent
    (verify should not mutate state). Raises :class:`AuditHmacError`
    with a stable short message on any failure.

    PLAN-045 Wave 1 F-01-06: symlink reject + uid check mirrored from
    :func:`_check_perm_0600`.
    """
    if not p.exists():
        raise AuditHmacError("key_not_found: {p}".format(p=p))
    try:
        if p.is_symlink():
            raise AuditHmacError(
                "key_bad_perms: {p} is a symlink".format(p=p)
            )
    except OSError as e:
        raise AuditHmacError(
            "key_perm_error: is_symlink check failed on {p}: {e}".format(p=p, e=e)
        ) from e
    try:
        st = p.stat()
    except OSError as e:
        raise AuditHmacError(
            "key_perm_error: stat failed on {p}: {e}".format(p=p, e=e)
        ) from e
    if st.st_uid != os.getuid():
        raise AuditHmacError(
            "key_bad_perms: {p} owned by uid {u} (expected {e})".format(
                p=p, u=st.st_uid, e=os.getuid()
            )
        )
    if st.st_mode & 0o077 != 0:
        raise AuditHmacError(
            "key_bad_perms: {p} has group/world bits set".format(p=p)
        )
    try:
        data = p.read_bytes()
    except OSError as e:
        raise AuditHmacError(
            "key_perm_error: cannot read {p}: {e}".format(p=p, e=e)
        ) from e
    if len(data) != KEY_BYTES:
        raise AuditHmacError(
            "key_bad_length: {p} is {n} bytes (expected {k})".format(
                p=p, n=len(data), k=KEY_BYTES
            )
        )
    return data


def verify_chain(
    log_path: Path,
    *,
    key: Optional[bytes] = None,
    key_path_override: Optional[Path] = None,
    since: int = 1,
    strict_against_counter: bool = False,
    counter_override: Optional[int] = None,
) -> VerifyResult:
    """Walk a JSONL log file and verify the HMAC chain.

    Pure function: reads file, computes, returns structured result.
    Does NOT mutate state, does NOT generate keys, does NOT exit the
    process. Caller (CLI, hook, PLAN-043 loader, sigchain verifier)
    maps the result to its own output/exit convention.

    Args:
        log_path: Path to the JSONL log file (audit-log.jsonl,
            tier-policy.json.sigchain, or any other HMAC-chained file).
        key: Explicit 32-byte key. If provided, ``key_path_override``
            is ignored. PLAN-043 passes its tier-policy-specific key
            via this parameter.
        key_path_override: Path to key file (alternative to passing
            bytes). If None and ``key`` is None, defaults to
            :func:`key_path` (audit-log key).
        since: 1-indexed line number to start verification from. All
            lines before are skipped. Default 1 (verify from genesis).

    Returns:
        :class:`VerifyResult`. ``result.is_intact`` is True on success.

    Edge cases:
        - Log file missing → status=malformed, reason=log_not_found
        - Empty log → status=intact, verified_count=0
        - Empty lines within log → skipped silently (matches CLI)
        - Pre-v2.9 entries (no hmac field) at head → tolerated and
          counted in ``pre_v29_count``
        - Key file missing → status=key_missing, reason=key_not_found
        - Key file 0644 or similar → status=perm_error,
          reason=key_bad_perms
    """
    # Resolve key.
    if key is None:
        p = key_path_override if key_path_override is not None else key_path()
        try:
            key = _read_key_file(p)
        except AuditHmacError as e:
            msg = str(e)
            if msg.startswith("key_not_found"):
                return VerifyResult(
                    status=STATUS_KEY_MISSING, reason="key_not_found"
                )
            if msg.startswith("key_bad_perms"):
                return VerifyResult(
                    status=STATUS_PERM_ERROR, reason="key_bad_perms"
                )
            return VerifyResult(status=STATUS_PERM_ERROR, reason=msg)

    if len(key) != KEY_BYTES:
        return VerifyResult(
            status=STATUS_PERM_ERROR, reason="key_bad_length"
        )

    # Resolve log lines.
    if not log_path.exists():
        return VerifyResult(
            status=STATUS_MALFORMED, reason="log_not_found"
        )

    state = "CHAIN_START"
    prev_hmac = GENESIS_PREV
    verified_count = 0
    pre_v29_count = 0

    try:
        with log_path.open("r", encoding="utf-8") as f:
            for line_num, raw in enumerate(f, start=1):
                if line_num < since:
                    continue

                stripped = raw.strip()
                if not stripped:
                    continue

                try:
                    entry = json.loads(stripped)
                except json.JSONDecodeError:
                    return VerifyResult(
                        status=STATUS_MALFORMED,
                        line=line_num,
                        reason="line_not_json",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                    )

                if not isinstance(entry, dict):
                    return VerifyResult(
                        status=STATUS_MALFORMED,
                        line=line_num,
                        reason="line_not_object",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                    )

                hmac_hex = entry.get("hmac")

                if hmac_hex is None:
                    if state == "CHAIN_START":
                        pre_v29_count += 1
                        continue
                    # Transition-entry rule violation.
                    return VerifyResult(
                        status=STATUS_TAMPER,
                        line=line_num,
                        reason="transition_violation",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                        entry_ts=entry.get("ts"),
                        entry_action=entry.get("action"),
                    )

                if (
                    not isinstance(hmac_hex, str)
                    or len(hmac_hex) != HMAC_HEX_LEN
                ):
                    return VerifyResult(
                        status=STATUS_MALFORMED,
                        line=line_num,
                        reason="hmac_field_malformed",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                        entry_ts=entry.get("ts"),
                        entry_action=entry.get("action"),
                        actual_hmac=str(hmac_hex),
                    )

                if state == "CHAIN_START":
                    state = "CHAIN_ACTIVE"
                    prev_hmac = GENESIS_PREV

                # Recompute.
                entry_sans = {
                    k: v for k, v in entry.items()
                    if k != "hmac" and k != "hmac_error"
                }
                try:
                    expected = compute_entry_hmac(
                        key, prev_hmac, entry_sans
                    )
                except AuditHmacError:
                    return VerifyResult(
                        status=STATUS_MALFORMED,
                        line=line_num,
                        reason="hmac_compute_failed",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                        entry_ts=entry.get("ts"),
                        entry_action=entry.get("action"),
                    )

                try:
                    actual = from_hex(hmac_hex)
                except AuditHmacError:
                    return VerifyResult(
                        status=STATUS_MALFORMED,
                        line=line_num,
                        reason="hmac_parse_failed",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                        entry_ts=entry.get("ts"),
                        entry_action=entry.get("action"),
                        actual_hmac=hmac_hex,
                    )

                # Constant-time compare.
                if not _hmac.compare_digest(expected, actual):
                    return VerifyResult(
                        status=STATUS_TAMPER,
                        line=line_num,
                        reason="hmac_mismatch",
                        verified_count=verified_count,
                        pre_v29_count=pre_v29_count,
                        entry_ts=entry.get("ts"),
                        entry_action=entry.get("action"),
                        expected_hmac=expected.hex(),
                        actual_hmac=hmac_hex,
                    )

                prev_hmac = actual
                verified_count += 1
    except OSError:
        return VerifyResult(
            status=STATUS_PERM_ERROR, reason="log_perm_error"
        )

    # PLAN-045 Wave 1 F-01-05: optional chain-length canary check.
    # The persisted counter is the monotonic number of HMAC-bearing
    # entries ever written. If the walker saw FEWER than the counter,
    # the tail has been truncated — flag as tamper even though the
    # surviving prefix is internally consistent.
    if strict_against_counter:
        expected_length = counter_override
        if expected_length is None:
            expected_length = read_chain_length()
        if verified_count < expected_length:
            return VerifyResult(
                status=STATUS_TAMPER,
                reason="chain_length_truncation",
                verified_count=verified_count,
                pre_v29_count=pre_v29_count,
                actual_hmac=str(verified_count),
                expected_hmac=str(expected_length),
            )

    return VerifyResult(
        status=STATUS_INTACT,
        verified_count=verified_count,
        pre_v29_count=pre_v29_count,
    )
