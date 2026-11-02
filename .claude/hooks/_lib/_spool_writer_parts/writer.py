# PLAN-094 Wave A — spool_writer (canonical promotion of spool_writer_DRAFT.py)
"""_lib/spool_writer.py — durable spool + drain-on-next-invoke (PLAN-094 Wave A).

Implements ADR-055-AMEND-1: 5-phase atomic drain protocol, 4-tuple total
order across concurrent producers, K_MAX/K_TAIL_WINDOW idempotent skip,
canonical-tail prev_hmac reconstruction, per-PID spool + per-PID journal,
atomic split-and-delete for K_MAX deferral, header/body uuid sentinel.

Stdlib-only (ADR-002). Fail-open invariant — never raise to caller; any
infra failure emits a breadcrumb and returns safely.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import secrets
import signal
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
from _lib import runtime_paths as _runtime_paths  # noqa: E402  # PLAN-182 W1 single resolver (ADR-001 S318)

try:
    from _lib import audit_hmac as _audit_hmac  # noqa: E402
    _HMAC_AVAILABLE = True
except Exception:  # pragma: no cover
    _audit_hmac = None  # type: ignore[assignment]
    _HMAC_AVAILABLE = False

try:
    from _lib import canonical_json as _canonical_json  # noqa: E402
except Exception:  # pragma: no cover
    _canonical_json = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants (ADR-055-AMEND-1 §3 wave A spec)
# ---------------------------------------------------------------------------

K_MAX = 100
K_TAIL_WINDOW = 200
SPOOL_HEADER_VERSION = 1
# PLAN-111 Wave B-alt4 (debate consensus + cProfile data-driven): trigger
# raised 50 -> 100. Halves drain cascade count (40 -> 20 across 5-trial
# emit_pair benchmark, confirmed by cprofile-post-b-darwin.txt). Per-trial
# wall-clock 174ms -> 170ms (-2%); cumulative drain_now cumtime 364ms -> 307ms.
# Combined with Wave A cache: per-emit 580us -> 425us (-27%). AC-C1 strict
# <=360us NOT hit alone; Wave C.1 RELAX path engaged (200->300ms test
# budget) with ubuntu projection ~255ms still well under.
DRAIN_TRIGGER_SIZE = 100
DRAIN_TRIGGER_MTIME_MS = 100
STALE_SPOOL_TTL_DAYS = 7
SPOOL_LOCK_TIMEOUT = 2.5


__all__ = (
    '_ensure_spool_header',
    '_next_ordinal',
    '_ensure_spool_ready_for_append',
    '_sha256_of_canonical_json',
    '_write_journal_envelope',
    '_flush_journal_buffer',
    'spool_append',
)

# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _ensure_spool_header(
    pid: int, _retry_depth: int = 0, *, sync_header: bool = True,
) -> Dict[str, Any]:
    """Return the header dict for the current spool, creating it if absent.

    Header is written exactly once per spool file (first line). Fresh
    _spool_uuid minted on creation so body[i].spool_uuid sentinel matches.

    iter2-P1-4: existing nonempty spool with empty header cache (PID reuse,
    module reload, pytest reset) → parse existing header + reuse uuid;
    minting a new one would produce header_body_uuid_mismatch quarantine.
    iter4-P1-1: ordinal recovery via body-line parse (max(ordinal)+1), NOT
    `\n` count — robust against unterminated final line from crashed writer.
    iter4-P1-2: malformed-header → quarantine active spool via direct
    rename (NOT drain_now() — Phase 2 self-deadlocks on our flock) +
    fresh-mint retry (bounded depth=1).

    Only spool_append may defer the header fsync: it holds the spool lock
    and fsyncs the SAME file after writing the first event, before commit
    or acknowledging success. That sync persists both header and body.
    Standalone callers keep the durable-header default.
    """
    header = _SPOOL_HEADER_CACHE.get(pid)
    spool_p = _spool_path(pid)

    if header is not None and spool_p.exists():
        return header

    # iter2-P1-4: existing nonempty spool with no in-process header cache.
    # Read the existing header instead of minting a colliding new one.
    # iter5-P1: header reuse MUST apply the same strict 4-field validation
    # that Phase 2 applies (_validate_spool_header_strict). Accepting a
    # semantically incomplete header here lets new appends ride a file
    # that Phase 2 will later quarantine → silent loss of the new events.
    if spool_p.exists():
        try:
            st = spool_p.stat()
        except OSError:
            st = None
        if st is not None and st.st_size > 0:
            header_parsed_ok = False
            try:
                with spool_p.open("rb") as fh:
                    first = fh.readline()
                existing: Any = json.loads(first.decode("utf-8"))
                if _validate_spool_header_strict(existing):
                    _SPOOL_HEADER_CACHE[pid] = existing
                    # iter4-P1-1: ordinal recovery via body parse (NOT
                    # `\n`-count) — robust against unterminated final line.
                    _ORDINAL_COUNTER[pid] = _recover_ordinal_counter(spool_p)
                    header_parsed_ok = True
                    return existing
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                _breadcrumb(
                    f"existing spool header unparsable pid={pid}: "
                    f"{type(e).__name__}: {e}"
                )
            if not header_parsed_ok:
                # iter4-P1-2: do NOT call drain_now from inside the spool
                # flock (Phase 2 re-acquires this flock → self-timeout →
                # bail → caller appends to malformed spool → quarantine
                # silently loses the new event). Quarantine the file
                # directly (rename to `.corrupt-header.<epoch>`) and mint
                # a fresh header. Bounded retry depth = 1.
                #
                # iter6-P1: if quarantine FAILS (rename OSError), we MUST
                # NOT mint over the still-present corrupt file — that
                # lets new events land behind a header Phase 2 will
                # quarantine (silent data loss). Raise a specific
                # exception so caller (`spool_append`) aborts fail-open.
                quarantined = _quarantine_corrupt_active_spool(spool_p, pid)
                # Drop any stale in-memory state for this pid.
                _SPOOL_HEADER_CACHE.pop(pid, None)
                _ORDINAL_COUNTER.pop(pid, None)
                if not quarantined:
                    if _retry_depth >= 1:
                        # iter6-P1: exhausted retry AND quarantine still
                        # failing → abort current append fail-open.
                        # spool_append's outer try/except catches OSError
                        # and breadcrumbs. The corrupt file remains on
                        # disk for operator forensic recovery; Phase 2
                        # may eventually quarantine via its own path
                        # (header still fails _validate_spool_header_strict).
                        raise _SpoolHeaderUnrecoverable(
                            f"pid={pid}: quarantine of corrupt active spool "
                            f"failed after {_retry_depth + 1} attempt(s); "
                            f"aborting append fail-open"
                        )
                    return _ensure_spool_header(
                        pid, _retry_depth=_retry_depth + 1,
                        sync_header=sync_header,
                    )
                # Quarantine succeeded → fall through to fresh-mint path.

    header = {
        "_spool_header": True,
        "_spool_uuid": secrets.token_hex(8),
        "_pid": pid,
        "_created_wall_ns": time.time_ns(),
        "_created_monotonic_ns": time.monotonic_ns(),
        "_version": SPOOL_HEADER_VERSION,
        # PLAN-119 WS-D1 — sticky write-time origin stamp (minted once per PID
        # file). The drainer refuses to drain "test" spool into the LIVE chain.
        "_origin": _origin_for_new_spool(),
    }
    spool_p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    needs_header = (not spool_p.exists()) or spool_p.stat().st_size == 0
    if needs_header:
        line = json.dumps(header, separators=(",", ":"), ensure_ascii=False) + "\n"
        # O_CREAT|O_WRONLY|O_APPEND with 0600 perms — owner-only.
        fd = os.open(str(spool_p), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
            if sync_header:
                os.fsync(fd)
        finally:
            os.close(fd)
    _SPOOL_HEADER_CACHE[pid] = header
    _ORDINAL_COUNTER.setdefault(pid, 0)
    return header


def _next_ordinal(pid: int) -> int:
    """Return the next strictly-monotonic ordinal for a given pid."""
    n = _ORDINAL_COUNTER.get(pid, 0)
    _ORDINAL_COUNTER[pid] = n + 1
    return n


def _ensure_spool_ready_for_append(pid: int) -> None:
    """iter3-P1-1: isolate any unterminated final line before appending.

    If a prior writer died mid-write leaving no trailing newline, the next
    append concatenates onto the partial line and the new event is lost.
    Append a separator newline under the held spool flock to isolate the
    partial fragment (Phase 3 will discard it). No-op when missing/empty/
    already-newline-terminated. Caller MUST hold _spool_flock_path(pid).
    Fail-open: breadcrumb on any OSError.
    """
    spool_p = _spool_path(pid)
    try:
        if not spool_p.exists():
            return
        st = spool_p.stat()
        if st.st_size == 0:
            return
        with open(str(spool_p), "rb") as f:
            f.seek(-1, os.SEEK_END)
            last = f.read(1)
        if last == b"\n":
            return
        fd = os.open(str(spool_p), os.O_WRONLY | os.O_APPEND, 0o600)
        try:
            os.write(fd, b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
        _breadcrumb(
            f"spool partial-final-line isolated pid={pid} size={st.st_size}"
        )
    except OSError as e:  # pragma: no cover
        _breadcrumb(
            f"spool ready-for-append check failed pid={pid}: "
            f"{type(e).__name__}: {e}"
        )


def _sha256_of_canonical_json(entry_clean: Dict[str, Any]) -> str:
    """sha256 over the canonical_json bytes (deterministic idempotence marker).

    entry_clean MUST exclude internal _drain_* metadata + hmac field. The
    canonical_json encoder is the same one ADR-055 HMAC chain uses, so the
    digest is reproducible across re-drains.
    """
    if _canonical_json is None:
        raw = json.dumps(entry_clean, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    else:
        raw = _canonical_json.encode(entry_clean)
    return hashlib.sha256(raw).hexdigest()


def _write_journal_envelope(
    pid: int,
    record_id: str,
    spool_uuid: str,
    ordinal: int,
    sha256_of_line: str,
    op: str,
    drain_epoch: Optional[str] = None,
) -> None:
    """Buffer + amortized-fsync journal envelope. Best-effort fail-open.

    P1-2: NOT a hot-path fsync. Envelopes are buffered in
    _JOURNAL_BUFFER[pid]; flushed + fsync'd at drain boundary, signal
    handler, atexit, or every _JOURNAL_FLUSH_EVERY writes (per ADR-055-
    AMEND-1 §3 line 96: "journal fsync every 100ms OR 10 emits").
    """
    env: Dict[str, Any] = {
        "record_id": record_id,
        "spool_uuid": spool_uuid,
        "ordinal_within_file": ordinal,
        "sha256_of_line": sha256_of_line,
        "op": op,
        "wall_ns": time.time_ns(),
    }
    if drain_epoch is not None:
        env["drain_epoch_at_commit"] = drain_epoch
    try:
        line = (json.dumps(env, separators=(",", ":"), ensure_ascii=False)
                + "\n").encode("utf-8")
    except (TypeError, ValueError) as e:
        _breadcrumb(f"journal encode failed: {type(e).__name__}: {e}")
        return
    buf = _JOURNAL_BUFFER.setdefault(pid, [])
    buf.append(line)
    if len(buf) >= _JOURNAL_FLUSH_EVERY:
        _flush_journal_buffer(pid)


def _flush_journal_buffer(pid: int) -> None:
    """Flush buffered journal envelopes for PID with a single fsync.

    P1-2: invoked at drain boundary, signal handler, atexit, or when
    buffer hits _JOURNAL_FLUSH_EVERY. Best-effort fail-open. Acquires
    the per-PID journal flock around the append+fsync window.
    """
    buf = _JOURNAL_BUFFER.get(pid)
    if not buf:
        return
    p = _journal_path(pid)
    try:
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as e:
        _breadcrumb(f"journal mkdir failed: {type(e).__name__}: {e}")
        return
    payload = b"".join(buf)
    try:
        with FileLock(_journal_flock_path(pid), timeout=SPOOL_LOCK_TIMEOUT):
            fd = os.open(
                str(p), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600,
            )
            try:
                os.write(fd, payload)
                os.fsync(fd)
            finally:
                os.close(fd)
        # Only clear on successful write; on failure the buffer retains
        # the envelopes for the next flush attempt (best-effort durability).
        _JOURNAL_BUFFER[pid] = []
    except FileLockTimeout:
        _breadcrumb(f"journal flock timeout pid={pid}")
    except OSError as e:
        _breadcrumb(f"journal flush failed: {type(e).__name__}: {e}")


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def spool_append(entry: Dict[str, Any]) -> None:
    """Write entry to per-PID spool with 4-tuple metadata + fsync.

    Stamps wall_ns, pid, spool_uuid, ordinal_within_file, record_id.
    Wraps spool write in begin/commit journal envelopes for crash
    forensics. Fail-open: any infra error writes a breadcrumb and
    returns silently.

    P1-1: acquires per-PID spool flock for the header-ensure + body
    append window so same-PID concurrent emit and signal-triggered drain
    don't race. Module-level _IN_SPOOL_APPEND latch lets signal handler
    detect a writer in progress and bail.

    P1-3: stamps `record_id` onto the spool entry so the drain Phase 5
    `op:"drained"` envelope can carry it for session-start reconciliation.
    """
    global _IN_SPOOL_APPEND, _LAST_APPEND_SUCCEEDED
    _LAST_APPEND_SUCCEEDED = False
    try:
        pid = os.getpid()
        record_id = uuid.uuid4().hex
        spool_p = _spool_path(pid)
        # Per-PID spool flock — ADR-055-AMEND-1 §4 Phase 1: writers acquire
        # only their own spool's flock + journal's flock (never canonical).
        try:
            spool_flock = FileLock(
                _spool_flock_path(pid), timeout=SPOOL_LOCK_TIMEOUT,
            )
        except OSError as e:
            _breadcrumb(f"spool flock alloc failed: {type(e).__name__}: {e}")
            return
        try:
            with spool_flock:
                _IN_SPOOL_APPEND = True
                try:
                    # The body fsync below covers the new header on this same
                    # inode too. Do not acknowledge or journal a commit until
                    # that fsync succeeds. No event durability is deferred.
                    header = _ensure_spool_header(pid, sync_header=False)
                    # iter3-P1-1: isolate any unterminated final line from a
                    # prior crashed writer BEFORE we mint our ordinal so the
                    # new entry can't be silently lost via concatenation.
                    _ensure_spool_ready_for_append(pid)
                    spool_uuid = header["_spool_uuid"]
                    ordinal = _next_ordinal(pid)

                    stamped: Dict[str, Any] = dict(entry)
                    stamped.setdefault("wall_ns", time.time_ns())
                    stamped["pid"] = pid
                    stamped["spool_uuid"] = spool_uuid
                    stamped["ordinal_within_file"] = ordinal
                    # P1-3: carry record_id through the spool so Phase 5
                    # can emit op:"drained" with matching id.
                    stamped["record_id"] = record_id

                    try:
                        line_bytes = json.dumps(
                            stamped, separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode("utf-8") + b"\n"
                    except (TypeError, ValueError) as e:
                        _breadcrumb(
                            f"spool encode failed: {type(e).__name__}: {e}"
                        )
                        return

                    sha = hashlib.sha256(line_bytes).hexdigest()

                    _write_journal_envelope(
                        pid, record_id, spool_uuid, ordinal, sha, "begin",
                    )

                    try:
                        fd = os.open(
                            str(spool_p),
                            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                            0o600,
                        )
                        try:
                            os.write(fd, line_bytes)
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                    except OSError as e:
                        _breadcrumb(
                            f"spool append failed: {type(e).__name__}: {e}"
                        )
                        return

                    _write_journal_envelope(
                        pid, record_id, spool_uuid, ordinal, sha, "commit",
                    )
                    _LAST_APPEND_SUCCEEDED = True
                finally:
                    _IN_SPOOL_APPEND = False
        except FileLockTimeout:
            _IN_SPOOL_APPEND = False
            _breadcrumb(f"spool flock timeout pid={pid}")
            return
    except Exception as e:  # fail-open invariant
        _IN_SPOOL_APPEND = False
        _breadcrumb(f"spool_append unexpected: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Drain trigger
# ---------------------------------------------------------------------------
