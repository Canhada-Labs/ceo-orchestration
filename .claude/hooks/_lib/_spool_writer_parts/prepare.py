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
    'should_drain',
    '_read_canonical_tail',
    '_DrainingFile',
    '_is_alive_pid',
    '_parse_spool_pid',
    '_phase2_sweep_and_rename',
    '_quarantine',
    '_should_quarantine_test_origin',
    '_quarantine_test_origin',
    '_phase2_validate_header',
    '_phase3_collect_and_sort',
)

def should_drain() -> bool:
    """Return True if current spool meets event-count or staleness trigger.

    P2-1: event-count trigger uses an actual newline-count over the spool
    body (capped at DRAIN_TRIGGER_SIZE + 2 to keep the probe cheap), NOT
    a byte-size proxy. Header is 1 line; we trigger when body lines >=
    DRAIN_TRIGGER_SIZE.
    """
    try:
        pid = os.getpid()
        p = _spool_path(pid)
        if not p.exists():
            return False
        st = p.stat()
        if st.st_size == 0:
            return False
        # Staleness trigger first (cheap)
        age_ms = (time.time() - st.st_mtime) * 1000.0
        if age_ms > DRAIN_TRIGGER_MTIME_MS:
            return True
        # P2-1: honest newline count, capped at DRAIN_TRIGGER_SIZE + 2
        # (1 for header + 1 to early-exit once we cross the threshold).
        cap = DRAIN_TRIGGER_SIZE + 2
        count = 0
        try:
            with p.open("rb") as f:
                while count < cap:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    count += chunk.count(b"\n")
                    if count >= cap:
                        break
        except OSError:
            return False
        # Body lines = count - 1 (header is line 1). Trigger when
        # body_lines >= DRAIN_TRIGGER_SIZE → count >= DRAIN_TRIGGER_SIZE+1.
        return count >= (DRAIN_TRIGGER_SIZE + 1)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tail read of canonical log (Phase 4 prev_hmac + _drain_sha256 set)
# ---------------------------------------------------------------------------


def _read_canonical_tail(
    log_path: Path, k_lines: int
) -> Tuple[Optional[bytes], List[Dict[str, Any]]]:
    """Return (prev_hmac_bytes_or_None, last_k_entries) from canonical log.

    Reads up to k_lines from EOF using a backward chunked scan. Returns the
    last entry's hmac (raw bytes) plus the parsed dicts for the last K
    well-formed JSON lines. Empty / missing log → (None, []).
    """
    if not log_path.exists():
        return None, []
    try:
        size = log_path.stat().st_size
    except OSError:
        return None, []
    if size == 0:
        return None, []

    chunk = 8192
    buf = b""
    lines: List[bytes] = []
    try:
        with log_path.open("rb") as f:
            pos = size
            while pos > 0 and len(lines) <= k_lines:
                read = min(chunk, pos)
                pos -= read
                f.seek(pos)
                buf = f.read(read) + buf
                parts = buf.split(b"\n")
                # First element may be a partial fragment until we read
                # further; keep it in buf, take the tail-complete lines.
                buf = parts[0]
                # parts[1:] are complete lines (after the first newline).
                # Reverse so we accumulate newest-first.
                for ln in reversed(parts[1:]):
                    if ln:
                        lines.append(ln)
                    if len(lines) >= k_lines:
                        break
            if pos == 0 and buf:
                if len(lines) < k_lines:
                    lines.append(buf)
    except OSError as e:
        _breadcrumb(f"canonical tail read failed: {type(e).__name__}: {e}")
        return None, []

    # lines is newest-first; reverse to chronological order
    lines.reverse()
    entries: List[Dict[str, Any]] = []
    for raw in lines[-k_lines:]:
        try:
            obj = json.loads(raw.decode("utf-8"))
            if isinstance(obj, dict):
                entries.append(obj)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

    prev_hmac: Optional[bytes] = None
    for obj in reversed(entries):
        hx = obj.get("hmac")
        if isinstance(hx, str) and len(hx) == 64:
            try:
                prev_hmac = bytes.fromhex(hx)
                break
            except ValueError:
                continue
    return prev_hmac, entries


# ---------------------------------------------------------------------------
# Phase 2 — sweep + atomic rename + header validation
# ---------------------------------------------------------------------------


@dataclass(eq=False)
class _DrainingFile:
    """One file under drain in the current cycle.

    P0-2: declared eq=False so default object identity hash applies —
    instances are usable as Dict keys without TypeError. (We still key
    per_file_consumed on str(path) per Option B in the review for
    clarity; the eq=False guard is defense-in-depth.)

    P2-4: header_raw stores the verbatim bytes (incl. trailing newline)
    of the header line, so Phase 5 atomic-split writes the byte-identical
    header to the new .draining.<new_epoch> file (no re-encode drift).

    iter2-P0-3: `quarantined` flag — set by `_quarantine()` after mid-file
    tamper rename so Phase 5 cleanup SKIPS the entry (the file is already
    moved aside as .malformed.<epoch>; trying to split would touch a
    non-existent path or re-sweep the quarantined file).
    """

    path: Path
    pid: int
    drain_epoch: str
    header: Optional[Dict[str, Any]] = None
    header_raw: bytes = b""
    body_lines: List[bytes] = field(default_factory=list)
    consumed_count: int = 0
    quarantined: bool = False


def _is_alive_pid(pid: int) -> bool:
    """Return True if a process with PID is alive in current namespace."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _parse_spool_pid(name: str) -> Optional[int]:
    """Extract PID from audit-spool.<pid>.* filename forms."""
    if not name.startswith(_SPOOL_PREFIX + "."):
        return None
    rest = name[len(_SPOOL_PREFIX) + 1:]
    pid_str, _, _ = rest.partition(".")
    try:
        return int(pid_str)
    except ValueError:
        return None


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _phase2_sweep_and_rename(
    state_dir: Path, drain_epoch: str, our_pid: int
) -> Tuple[List[_DrainingFile], bool]:
    """Sweep state dir for spool/draining files; atomic-rename into batch.

    Returns (list of draining files to process, in_recovery_mode_flag).
    in_recovery_mode is True iff any pre-existing .draining.* was swept
    (severity branching for unexpected_skip — ADR-055-AMEND-1 Phase 4).
    """
    files: List[_DrainingFile] = []
    in_recovery = False

    try:
        names = sorted(os.listdir(str(state_dir)))
    except OSError:
        return [], False

    # 1) Pre-existing .draining.* — these are stale from prior crashed drains
    # iter3-P2-2: wire STALE_SPOOL_TTL_DAYS into the sweep. A .draining file
    # owned by a dead PID (or even a live one) whose mtime is older than
    # the TTL is forensically interesting — emit an audit_spool_stale_recovered
    # advisory BEFORE processing so SOC has trace of the long-deferred
    # recovery. Processing still proceeds; the TTL is advisory-only.
    stale_ttl_ns = STALE_SPOOL_TTL_DAYS * 86400 * 1_000_000_000
    now_ns = time.time_ns()
    for name in names:
        if _DRAINING_SUFFIX_TOKEN not in name:
            continue
        if not name.startswith(_SPOOL_PREFIX + "."):
            continue
        pid = _parse_spool_pid(name)
        if pid is None:
            continue
        # Parse the existing drain_epoch from the suffix; merge in as-is.
        try:
            old_epoch = name.rsplit(_DRAINING_SUFFIX_TOKEN, 1)[1]
        except IndexError:
            old_epoch = drain_epoch
        full_path = state_dir / name
        # iter3-P2-2: stale-recovery advisory if age > TTL.
        try:
            st_mtime_ns = full_path.stat().st_mtime_ns
            file_age_ns = now_ns - st_mtime_ns
            if file_age_ns > stale_ttl_ns:
                file_age_hours = file_age_ns // (3600 * 1_000_000_000)
                _forensic("audit_spool_stale_recovered", {
                    "original_pid": pid,
                    "file_age_hours": int(file_age_hours),
                    "stale_ttl_days": STALE_SPOOL_TTL_DAYS,
                    "drain_epoch": drain_epoch,
                    "prior_drain_epoch": old_epoch,
                })
        except OSError:
            pass
        files.append(_DrainingFile(
            path=full_path, pid=pid, drain_epoch=old_epoch,
        ))
        in_recovery = True

    # 2) Active spool files — atomically rename to .draining.<drain_epoch>.
    #    Skip our own active spool (we hold it open for writes); also skip
    #    spools of live PIDs other than ours when force-drain is not set —
    #    let the owning process drain them. (Conservative: live-PID spools
    #    of OTHER processes will be reaped on next aggregate sweep.)
    for name in names:
        if not name.startswith(_SPOOL_PREFIX + "."):
            continue
        if not name.endswith(".jsonl"):
            continue
        pid = _parse_spool_pid(name)
        if pid is None:
            continue
        src = state_dir / name
        try:
            src_stat = src.stat()
        except OSError:
            continue
        if src_stat.st_size == 0:
            continue
        # Only rename our own spool OR clearly-dead PID spools. Live-PID
        # spools belong to peers — leave them for their own drain trigger
        # to avoid stealing in-flight writes (writer flock would block us
        # anyway; explicit check is the cheap path).
        if pid != our_pid and _is_alive_pid(pid):
            continue
        # iter4-P2-1: stale-recovery advisory ALSO covers active spool files
        # whose owning PID is dead AND mtime is older than TTL (ADR-055-
        # AMEND-1 §A.4.5 covers both .draining.* AND orphaned active
        # spools). Emit BEFORE the rename so SOC trace carries the
        # forensic correlation between the orphan and the drain epoch.
        if pid != our_pid:
            try:
                file_age_ns = now_ns - src_stat.st_mtime_ns
                if file_age_ns > stale_ttl_ns:
                    file_age_hours = file_age_ns // (3600 * 1_000_000_000)
                    _forensic("audit_spool_stale_recovered", {
                        "original_pid": pid,
                        "file_age_hours": int(file_age_hours),
                        "stale_ttl_days": STALE_SPOOL_TTL_DAYS,
                        "drain_epoch": drain_epoch,
                        "source": "active_spool_orphan",
                    })
            except OSError:
                pass
        # P0-1: use _draining_path helper (was: missing dot before draining)
        dst = _draining_path(src, drain_epoch)
        # iter3-P1-2: acquire the per-PID spool flock around rename so a
        # concurrent writer mid-spool_append in the same PID (e.g. signal-
        # handler-triggered drain racing the writer's own fd) is forced to
        # complete before we steal the file. Writers hold the flock for
        # ~10µs per emit; a short timeout (0.5s) is sufficient. If we time
        # out, we skip this PID this cycle — the spool gets picked up at
        # next drain trigger. Either path is correctness-preserving.
        try:
            with FileLock(_spool_flock_path(pid), timeout=0.5):
                # Re-check existence under lock (writer may have unlinked
                # during contention, or another concurrent drain in our PID
                # could have renamed it first).
                try:
                    if not src.exists() or src.stat().st_size == 0:
                        continue
                except OSError:
                    continue
                try:
                    os.rename(str(src), str(dst))
                except OSError as e:
                    _breadcrumb(
                        f"phase2 rename failed for {name}: "
                        f"{type(e).__name__}: {e}"
                    )
                    continue
        except FileLockTimeout:
            # Writer is mid-append on this spool; defer to next drain
            # cycle. The spool size/mtime trigger will catch it.
            _breadcrumb(
                f"phase2 spool flock timeout pid={pid} (writer mid-append)"
            )
            continue
        files.append(_DrainingFile(
            path=dst, pid=pid, drain_epoch=drain_epoch,
        ))
        # If the renamed-away spool belonged to our pid, reset our header
        # cache so subsequent spool_append mints a fresh _spool_uuid.
        if pid == our_pid:
            _SPOOL_HEADER_CACHE.pop(pid, None)
            _ORDINAL_COUNTER.pop(pid, None)

    return files, in_recovery


def _quarantine(
    file: _DrainingFile, mismatch_kind: str, drain_epoch: str
) -> None:
    """Rename a malformed/tampered spool to .malformed.<drain_epoch>; emit.

    iter2-P0-3: sets `file.quarantined = True` so Phase 5 cleanup skips the
    entry (the source .draining.<epoch> no longer exists at its original
    path — trying to split or unlink would either fail or, worse, re-sweep
    the renamed .malformed.<epoch> file on a subsequent drain.
    """
    try:
        new_name = file.path.name.replace(
            _DRAINING_SUFFIX_TOKEN[1:] + file.drain_epoch,
            _MALFORMED_SUFFIX_TOKEN[1:] + drain_epoch,
            1,
        )
        new_path = file.path.with_name(new_name)
        os.rename(str(file.path), str(new_path))
    except OSError as e:
        _breadcrumb(f"quarantine rename failed: {type(e).__name__}: {e}")
    # iter2-P0-3: latch quarantined flag for Phase 5 cleanup skip.
    file.quarantined = True
    _forensic("audit_spool_tamper_detected", {
        "mismatch_kind": mismatch_kind,
        "spool_pid": file.pid,
        "drain_epoch": drain_epoch,
    })


def _should_quarantine_test_origin(
    file: "_DrainingFile", canonical_log_path: Path
) -> bool:
    """PLAN-119 WS-D1 — True iff this spool is ``_origin:"test"`` AND the
    canonical drain destination IS the live chain.

    Conjunction-gated (Codex R2 P0-1): a redirected pytest/session tmp dir is
    NOT the live chain, so a ``"test"`` spool drains NORMALLY there (isolated
    drain-behavior tests keep working). Fail-SAFE to NO quarantine (Codex R3
    P1-1) when the live-log snapshot is absent/unreadable — never risk dropping a
    real event. Legacy spool with no ``_origin`` (or ``_origin:"live"``) is never
    quarantined.
    """
    header = file.header
    if not isinstance(header, dict) or header.get("_origin") != "test":
        return False
    snapshot = os.environ.get(_LIVE_LOG_SNAPSHOT_VAR)
    if not snapshot:
        return False  # cannot confirm destination is live → drain normally
    try:
        return Path(canonical_log_path).resolve() == Path(snapshot).resolve()
    except (OSError, ValueError):
        return False


def _quarantine_test_origin(file: "_DrainingFile", drain_epoch: str) -> None:
    """PLAN-119 WS-D1 — rename an ``_origin:"test"`` spool out of the drain path
    so its entries never reach the live canonical append.

    Breadcrumb-only — no new audit action (the canonical ``_KNOWN_ACTIONS`` is a
    kernel-HARD-DENY surface; the rename + the ``DrainStats`` counter are the
    durable trace). Mirrors ``_quarantine``'s rename discipline (latches
    ``file.quarantined`` so Phase 5 cleanup skips the moved file).
    """
    try:
        new_name = file.path.name.replace(
            _DRAINING_SUFFIX_TOKEN[1:] + file.drain_epoch,
            _TEST_ORIGIN_SUFFIX_TOKEN[1:] + drain_epoch,
            1,
        )
        new_path = file.path.with_name(new_name)
        os.rename(str(file.path), str(new_path))
    except OSError as e:
        _breadcrumb(
            f"test-origin quarantine rename failed: {type(e).__name__}: {e}"
        )
    file.quarantined = True
    # Codex P1 — compact the quarantined spool's journal records so session-start
    # reconciliation does NOT later count them as inflight/lost and emit a spurious
    # ``audit_flush_dropped_count``. A deliberate test-origin quarantine is a
    # COMPLETION (the entries are intentionally not drained to the live chain),
    # not a real-event loss. ``file.body_lines`` is populated by Phase 2.
    try:
        rec_ids = []
        for raw in (file.body_lines or []):
            try:
                entry = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            rid = entry.get("record_id") if isinstance(entry, dict) else None
            if isinstance(rid, str) and rid:
                rec_ids.append(rid)
        if rec_ids:
            _journal_compact_drained(file.pid, rec_ids, drain_epoch)
    except Exception as e:  # pragma: no cover — journal hygiene, never blocks
        _breadcrumb(
            f"test-origin journal compaction failed: {type(e).__name__}: {e}"
        )
    _breadcrumb(
        f"test-origin spool refused at live-chain drain: pid={file.pid} "
        f"epoch={drain_epoch}"
    )


def _phase2_validate_header(
    file: _DrainingFile, drain_epoch: str
) -> bool:
    """Read header + first body line; validate body[0].spool_uuid sentinel.

    Returns True iff header is well-formed AND header._spool_uuid matches
    body[0].spool_uuid (when body is non-empty). Quarantines on mismatch.
    Loads body_lines into file as a side effect.
    """
    try:
        raw_lines = file.path.read_bytes().split(b"\n")
    except OSError as e:
        _breadcrumb(f"phase2 read failed: {type(e).__name__}: {e}")
        return False

    # Strip trailing empty fragment from final newline
    if raw_lines and raw_lines[-1] == b"":
        raw_lines = raw_lines[:-1]

    if not raw_lines:
        # Empty file; nothing to do — caller treats as fully-consumed
        file.header = None
        file.body_lines = []
        return True

    # Parse header
    try:
        header = json.loads(raw_lines[0].decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        _quarantine(file, "malformed_spool_header", drain_epoch)
        return False
    # iter5-P1: use the shared strict predicate (same one used by
    # _ensure_spool_header for writer-side reuse) so writer and drainer
    # validation are byte-equivalent.
    if not _validate_spool_header_strict(header):
        _quarantine(file, "malformed_spool_header", drain_epoch)
        return False

    file.header = header
    # P2-4: verbatim header bytes for Phase 5 atomic split
    file.header_raw = raw_lines[0] + b"\n"
    file.body_lines = raw_lines[1:]

    if not file.body_lines:
        return True

    # body[0] sentinel
    body0_raw = file.body_lines[0]
    try:
        body0 = json.loads(body0_raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # body[0] malformed → if it's the ONLY body line, treat as partial-
        # line crash (Phase 3 discard). Otherwise quarantine (mid-file
        # malformed is suspicious).
        if len(file.body_lines) == 1:
            return True
        _quarantine(file, "malformed_spool_header", drain_epoch)
        return False
    # PLAN-094-FOLLOWUP bug fix: extract spool_uuid from validated header
    # (was UnboundLocalError NameError — refactor regression from
    # _validate_spool_header_strict extraction; caught by Wave A.7r.1 test).
    spool_uuid = header["_spool_uuid"]
    if not isinstance(body0, dict) or body0.get("spool_uuid") != spool_uuid:
        _quarantine(file, "header_body_uuid_mismatch", drain_epoch)
        return False
    return True


# ---------------------------------------------------------------------------
# Phase 3 — sort + 4-tuple uniqueness
# ---------------------------------------------------------------------------


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def _phase3_collect_and_sort(
    files: List[_DrainingFile], drain_epoch: str, stats: DrainStats,
) -> Tuple[
    List[Tuple[Tuple[int, int, str, int], Dict[str, Any], _DrainingFile, int]],
    Dict[str, Set[int]],
    int,
]:
    """Parse body lines from each draining file; sort by 4-tuple; de-dup.

    Returns (deduped, partial_discard_consumed_indices_by_path,
    duplicate_consumed_count).

    iter4-P2-2: returns the count of duplicate-tuple entries marked
    consumed in this cycle so Phase 4 can carry it as the starting
    `processed` value. Without this, a duplicate storm (e.g. corrupted
    spool with N identical 4-tuples) consumes/deletes more than K_MAX
    entries in one drain cycle, softening the K_MAX hard-cap perf
    contract (correctness preserved — duplicates ARE discarded).

    iter2-P0-1: partial-discard tracking is now a Set[int] of body indices
    (not a prefix-count). Phase 5 splits the file using the COMPLEMENT of
    the set, so out-of-order index consumption (later index handled before
    earlier index) is safe.

    iter2-P0-2: duplicate 4-tuple is marked CONSUMED (added to the per-file
    set) so Phase 5 cleanup actually removes it from disk; without this,
    the rejected entry survives split → re-detected as duplicate forever
    (livelock). audit_spool_intentionally_deleted advisory emits.

    iter2-P2-2: per-file ordinal monotonicity check — within each spool
    file, `ordinal_within_file` of entry N+1 must be > entry N (the writer
    issues strictly-monotonic ordinals via _next_ordinal()). Violation →
    quarantine source with mismatch_kind="ordinal_monotonicity_violation".

    Tamper / malformed handling:
    - JSON-parse fail on the LAST line of a file → partial-line discard
      (writer SIGKILL mid-write); emit audit_spool_partial_line_discarded
    - JSON-parse fail on any OTHER line → tamper; quarantine the file and
      drop ALL its remaining unconsumed body entries.
    - Duplicate full 4-tuple → reject with audit_spool_duplicate_tuple_rejected;
      mark consumed (iter2-P0-2).
    - Ordinal monotonicity violation → quarantine (iter2-P2-2).
    """
    collected: List[Tuple[Tuple[int, int, str, int], Dict[str, Any], _DrainingFile, int]] = []
    partial_consumed: Dict[str, Set[int]] = {}

    def _mark(path_str: str, idx: int) -> None:
        partial_consumed.setdefault(path_str, set()).add(idx)

    for f in files:
        if not f.body_lines:
            continue
        last_idx = len(f.body_lines) - 1
        path_key = str(f.path)
        # iter2-P2-2: per-file ordinal monotonicity tracking.
        prev_ordinal: Optional[int] = None
        for idx, raw in enumerate(f.body_lines):
            if not raw:
                # Empty line (double-newline) — discard silently but mark
                # consumed so Phase 5 doesn't perpetually re-split it.
                _mark(path_key, idx)
                continue
            try:
                obj = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                if idx == last_idx:
                    stats.partial_lines_discarded += 1
                    _forensic("audit_spool_partial_line_discarded", {
                        "spool_pid": f.pid,
                        "drain_epoch": drain_epoch,
                        "body_index": idx,
                    })
                    # iter2-P0-1: mark this index consumed so Phase 5
                    # split treats the partial line as handled.
                    _mark(path_key, idx)
                    continue
                # Mid-file malformed — quarantine file and stop collecting
                # from it (subsequent entries are suspect)
                _quarantine(f, "malformed_spool_header", drain_epoch)
                stats.quarantined_files += 1
                # Drop any entries already collected from this file:
                collected = [c for c in collected if c[2] is not f]
                partial_consumed.pop(path_key, None)
                break
            if not isinstance(obj, dict):
                if idx == last_idx:
                    stats.partial_lines_discarded += 1
                    _mark(path_key, idx)  # iter2-P0-1
                    continue
                _quarantine(f, "malformed_spool_header", drain_epoch)
                stats.quarantined_files += 1
                collected = [c for c in collected if c[2] is not f]
                partial_consumed.pop(path_key, None)
                break
            try:
                wall_ns = int(obj["wall_ns"])
                pid = int(obj["pid"])
                spool_uuid = str(obj["spool_uuid"])
                ordinal = int(obj["ordinal_within_file"])
            except (KeyError, TypeError, ValueError):
                # Missing 4-tuple field — treat as tamper (would also break
                # HMAC since spool_uuid participates in canonical_json)
                _quarantine(f, "malformed_spool_header", drain_epoch)
                stats.quarantined_files += 1
                collected = [c for c in collected if c[2] is not f]
                partial_consumed.pop(path_key, None)
                break
            # iter2-P2-2: per-file ordinal monotonicity (strictly increasing).
            if prev_ordinal is not None and ordinal <= prev_ordinal:
                _quarantine(f, "ordinal_monotonicity_violation", drain_epoch)
                stats.quarantined_files += 1
                collected = [c for c in collected if c[2] is not f]
                partial_consumed.pop(path_key, None)
                break
            prev_ordinal = ordinal
            key = (wall_ns, pid, spool_uuid, ordinal)
            collected.append((key, obj, f, idx))

    collected.sort(key=lambda x: x[0])

    deduped: List[Tuple[Tuple[int, int, str, int], Dict[str, Any], _DrainingFile, int]] = []
    seen: set = set()
    # iter4-P2-2: bound duplicate-cleanup to K_MAX so a storm can't exceed
    # the per-cycle perf cap. Unmarked duplicates survive split → next
    # drain re-detects → bounded amortization (correctness preserved; no
    # canonical append happens for duplicates either way).
    duplicate_consumed = 0
    for key, obj, f, idx in collected:
        if key in seen:
            if duplicate_consumed >= K_MAX:
                # Still record the forensic so SOC sees the rejection,
                # but DO NOT _mark() consumed (defer to next cycle).
                stats.rejected_duplicate_tuple += 1
                _forensic("audit_spool_duplicate_tuple_rejected", {
                    "wall_ns": key[0],
                    "pid": key[1],
                    "spool_uuid": key[2],
                    "ordinal_within_file": key[3],
                    "drain_epoch": drain_epoch,
                    "deferred_to_next_cycle": True,
                })
                continue
            stats.rejected_duplicate_tuple += 1
            _forensic("audit_spool_duplicate_tuple_rejected", {
                "wall_ns": key[0],
                "pid": key[1],
                "spool_uuid": key[2],
                "ordinal_within_file": key[3],
                "drain_epoch": drain_epoch,
            })
            # iter2-P0-2: mark the duplicate's body index CONSUMED so Phase 5
            # actually removes it from disk (otherwise the rejected entry
            # survives split → re-detected forever = livelock). Emit a
            # paired advisory so SOC has trace of the silent deletion.
            _mark(str(f.path), idx)
            # iter3-P2-1: surface count into DrainStats for AC10 visibility
            # (JournalReconciliation aggregates this at session-start).
            stats.intentionally_deleted += 1
            duplicate_consumed += 1
            _forensic("audit_spool_intentionally_deleted", {
                "reason": "duplicate_tuple",
                "spool_pid": key[1],
                "spool_uuid": key[2],
                "ordinal_within_file": key[3],
                "drain_epoch": drain_epoch,
            })
            continue
        seen.add(key)
        deduped.append((key, obj, f, idx))
    return deduped, partial_consumed, duplicate_consumed


# ---------------------------------------------------------------------------
# Phase 4 — idempotent chain reconstruction
# ---------------------------------------------------------------------------
