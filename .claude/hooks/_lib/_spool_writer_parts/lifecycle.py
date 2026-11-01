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
    '_own_spool_stale_past_trigger',
    'drain_now',
    'reconcile_journal_at_session_start',
    '_journal_rec_dict',
    '_atexit_drain',
    '_signal_drain_handler',
    'install_exit_handlers',
    '_reset_for_test',
)

def _own_spool_stale_past_trigger(pid: int) -> bool:
    """True iff our own spool's mtime age exceeds DRAIN_TRIGGER_MTIME_MS.

    (ADR-055-AMEND-3) SEC veto-floor MF-1 gate. When an opportunistic
    (force=False) drain yields the canonical lock AND our own spool is already
    stale past the staleness trigger, the lock holder is not keeping up — that
    is genuine drain starvation (a wedged/contended holder), distinct from
    benign single-winner contention (a fresh spool). OSError-safe: a missing or
    unreadable spool returns False (fail-quiet, never raises).
    """
    try:
        st = _spool_path(pid).stat()
    except OSError:
        return False
    if st.st_size == 0:
        return False
    age_ms = (time.time() - st.st_mtime) * 1000.0
    return age_ms > DRAIN_TRIGGER_MTIME_MS


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def drain_now(*, force: bool = False) -> DrainStats:
    """Execute 5-phase atomic drain. Bounded ≤K_MAX entries per call.

    Fail-open invariant — any error sets stats.ok=False and is captured in
    stats.error. NEVER raises to caller.
    """
    stats = DrainStats()
    if is_sync_mode() and not force:
        return stats
    try:
        if not force and not should_drain():
            return stats

        drain_epoch = secrets.token_hex(4)
        stats.drain_epoch = drain_epoch
        state_dir = _state_dir()
        our_pid = os.getpid()
        log_path = _canonical_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock_path = _canonical_log_lock()

        # P1-2: flush any buffered journal envelopes BEFORE drain begins so
        # the journal reflects all begin/commit events up to this point
        # (op:"drained" envelopes are appended after canonical append).
        _flush_journal_buffer(our_pid)

        # Phase 1 — canonical lock (deadlock-free; writers hold only their
        # own per-PID flocks, never the canonical lock).
        #
        # (ADR-055-AMEND-3) — opportunistic/forced split. A FORCED
        # drain (recovery / exit-handler / session-start) must complete, so it
        # blocks up to SPOOL_LOCK_TIMEOUT and a timeout there is anomalous. An
        # OPPORTUNISTIC drain (force=False, the per-emit hot path) is
        # best-effort: the lock holder plus the loser's own later drain cover
        # its events, so it acquires NON-BLOCKING (timeout=0 — a clean one-shot
        # try-lock, one flock(LOCK_NB) with no sleep) and yields silently on
        # contention instead of blocking the hook subprocess for 2.5s.
        canonical_timeout = SPOOL_LOCK_TIMEOUT if force else 0.0
        try:
            with FileLock(lock_path, timeout=canonical_timeout):
                files, in_recovery = _phase2_sweep_and_rename(
                    state_dir, drain_epoch, our_pid,
                )
                stats.in_recovery_mode = in_recovery

                valid_files: List[_DrainingFile] = []
                for f in files:
                    if _phase2_validate_header(f, drain_epoch):
                        # PLAN-119 WS-D1 — refuse _origin:"test" spool ONLY when
                        # the canonical destination IS the live chain; applied
                        # AFTER header validation and BEFORE phase 3, so test
                        # entries never reach batch_lines / the canonical append.
                        if _should_quarantine_test_origin(f, log_path):
                            _quarantine_test_origin(f, drain_epoch)
                            stats.test_origin_quarantined += 1
                        else:
                            valid_files.append(f)
                    else:
                        stats.quarantined_files += 1

                # iter2-P0-1 + iter4-P2-2: phase 3 returns
                # (deduped, Dict[str, Set[int]], duplicate_consumed_count)
                deduped, partial_consumed, dup_consumed = (
                    _phase3_collect_and_sort(
                        valid_files, drain_epoch, stats,
                    )
                )

                # P0-2 + P1-3 + iter2-P0-1: phase 4 returns
                # (batch_lines, _, per_file_consumed_set, last_hmac, ids)
                # iter4-P2-2: pass dup_consumed as starting_processed so
                # combined Phase-3 + Phase-4 work bounded by K_MAX.
                (batch_lines, _, per_file_consumed, last_hmac,
                 drained_ids) = _phase4_build_batch(
                    deduped, drain_epoch, in_recovery, stats,
                    starting_processed=dup_consumed,
                )

                # iter2-P0-1: merge partial/duplicate-rejection consumed
                # indices (Set[int] union) into the Phase-4 per-file map so
                # Phase 5 split honors the COMPLEMENT for remainder lines.
                for path_key, idx_set in partial_consumed.items():
                    if path_key in per_file_consumed:
                        per_file_consumed[path_key] |= idx_set
                    else:
                        per_file_consumed[path_key] = set(idx_set)

                stats.appended = _phase5_append_canonical(batch_lines, last_hmac)

                # P1-3: emit op:"drained" envelopes grouped by pid + flush.
                drained_by_pid: Dict[int, List[str]] = {}
                for rec_id, pid in drained_ids:
                    drained_by_pid.setdefault(pid, []).append(rec_id)
                for pid, ids in drained_by_pid.items():
                    _journal_compact_drained(pid, ids, drain_epoch)

                _phase5_split_and_cleanup(
                    valid_files, per_file_consumed, drain_epoch, stats,
                )

                # P1-2: drain-boundary journal flush for our own PID
                _flush_journal_buffer(our_pid)
        except FileLockTimeout:
            if force:
                # Forced drain could not complete — genuinely anomalous.
                stats.ok = False
                stats.error = "canonical_lock_timeout"
                _breadcrumb("drain canonical lock timeout")
            else:
                # Opportunistic yield — expected under concurrency, NOT an
                # error. Another drainer holds the lock; its global sweep plus
                # our own later drain cover our events, so ok stays True.
                stats.contended_skip = True
                # SEC veto-floor MF-1 (ADR-052): keep a genuinely wedged holder
                # observable. Emit a DISTINCT, gated breadcrumb ONLY when our
                # own spool is already stale past the staleness trigger (holder
                # not keeping up = real starvation). Benign single-winner
                # contention (fresh spool) stays silent, so the existing
                # audit-log.errors line-count detectors (ceo-diagnose.py /
                # status.py) still surface a wedge without the benign volume.
                if _own_spool_stale_past_trigger(our_pid):
                    _breadcrumb(
                        "drain canonical lock STARVED: own spool stale past "
                        "trigger while opportunistic drain yielded"
                    )
            return stats
    except Exception as e:
        stats.ok = False
        stats.error = f"{type(e).__name__}: {e}"
        _breadcrumb(f"drain_now unexpected: {type(e).__name__}: {e}")
    return stats


# ---------------------------------------------------------------------------
# Session-start reconciliation
# ---------------------------------------------------------------------------


# QDSAA-FUNCAO-LONGA: protocolo de durabilidade atomica; separar altera invariantes de lock e recuperacao.
def reconcile_journal_at_session_start() -> JournalReconciliation:
    """Walk audit-pending.*.journal entries; classify counts; emit forensic.

    Returns the JournalReconciliation populated with counts. Emits
    audit_flush_dropped_count via wired forensic callback (caller in
    audit_emit wires the callback before invoking this).
    """
    rec = JournalReconciliation()
    state_dir = _state_dir()
    try:
        if not state_dir.exists():
            _forensic("audit_flush_dropped_count", _journal_rec_dict(rec))
            return rec
        names = sorted(os.listdir(str(state_dir)))
    except OSError:
        _forensic("audit_flush_dropped_count", _journal_rec_dict(rec))
        return rec

    by_record: Dict[str, Dict[str, bool]] = {}
    for name in names:
        if not name.startswith(_JOURNAL_PREFIX + "."):
            continue
        if not name.endswith(".journal"):
            continue
        if name == _aggregate_journal_path().name:
            continue
        # Parse <pid> from "audit-pending.<pid>.journal"
        rest = name[len(_JOURNAL_PREFIX) + 1:]
        pid_str = rest[:-len(".journal")]
        try:
            pid = int(pid_str)
        except ValueError:
            continue
        if pid == os.getpid():
            continue
        if _is_alive_pid(pid):
            continue
        path = state_dir / name
        try:
            with path.open("r", encoding="utf-8") as f:
                for raw in f:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    try:
                        env = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(env, dict):
                        continue
                    rid = env.get("record_id")
                    op = env.get("op")
                    if not isinstance(rid, str) or not isinstance(op, str):
                        continue
                    slot = by_record.setdefault(
                        rid, {"begin": False, "commit": False, "drained": False},
                    )
                    if op in slot:
                        slot[op] = True
        except OSError:
            continue

    for rid, ops in by_record.items():
        if ops["begin"] and not ops["commit"]:
            rec.begin_no_commit += 1
        elif ops["commit"] and not ops["drained"]:
            rec.commit_no_drained += 1
        elif ops["commit"] and ops["drained"]:
            rec.recovered += 1

    # Trigger a recovery drain to sweep commit_no_drained envelopes.
    if rec.commit_no_drained > 0:
        recov = drain_now(force=True)
        if recov.ok:
            # iter2-P1-2: canonical-append-before-unlink crash recovery
            # produces mostly `skipped_idempotent` (the entries are already
            # in the canonical log; next drain reads same bytes from
            # .draining, sees them in K_TAIL_WINDOW, skips). Sum both
            # counters so AC10 reports actual recovery count, not just the
            # rare appended-on-recovery subset.
            rec.recovered += recov.appended + recov.skipped_idempotent
            # iter3-P2-1: surface intentionally_deleted (duplicate-tuple
            # rejections during recovery) into the reconciliation counter
            # so the audit_flush_dropped_count emit carries it.
            rec.intentionally_deleted += recov.intentionally_deleted

    _forensic("audit_flush_dropped_count", _journal_rec_dict(rec))
    return rec


def _journal_rec_dict(rec: JournalReconciliation) -> Dict[str, Any]:
    return {
        "begin_no_commit": rec.begin_no_commit,
        "commit_no_drained": rec.commit_no_drained,
        "recovered": rec.recovered,
        "truly_lost": rec.truly_lost,
        "tamper_rejected": rec.tamper_rejected,
        "intentionally_deleted": rec.intentionally_deleted,
    }


# ---------------------------------------------------------------------------
# Exit handlers
# ---------------------------------------------------------------------------


def _atexit_drain() -> None:
    """Best-effort exit drain, except while a hook deadline is armed."""
    if _exit_deadline_active():
        _record_exit_deadline_skip("atexit")
        return
    try:
        drain_now(force=True)
    except Exception:
        pass
    try:
        _flush_journal_buffer(os.getpid())
    except Exception:
        pass


def _signal_drain_handler(signum: int, frame: Any) -> None:
    """Drain when safe, then preserve the previous signal disposition."""
    if _IN_SPOOL_APPEND:
        _breadcrumb(f"signal {signum} arrived during spool_append; bail")
    elif _exit_deadline_active():
        _record_exit_deadline_skip(f"signal-{signum}")
    else:
        try:
            drain_now(force=True)
        except Exception:
            pass
        try:
            _flush_journal_buffer(os.getpid())
        except Exception:
            pass
    if signum == signal.SIGTERM:
        prev = _PREV_SIGTERM_HANDLER
    elif signum == signal.SIGINT:
        prev = _PREV_SIGINT_HANDLER
    else:
        prev = signal.SIG_DFL
    if prev is signal.SIG_IGN:
        try:
            signal.signal(signum, signal.SIG_IGN)
        except (ValueError, OSError):  # pragma: no cover
            pass
        return
    if callable(prev):
        try:
            signal.signal(signum, prev)
        except (ValueError, OSError):  # pragma: no cover
            pass
        try:
            prev(signum, frame)
        except Exception:  # pragma: no cover
            pass
        return
    try:
        signal.signal(signum, signal.SIG_DFL)
    except (ValueError, OSError):  # pragma: no cover
        pass
    try:
        os.kill(os.getpid(), signum)
    except OSError:  # pragma: no cover
        pass


def install_exit_handlers() -> None:
    """Register atexit + SIGTERM/SIGINT drain handlers (idempotent one-shot)."""
    global _EXIT_HANDLER_INSTALLED
    global _PREV_SIGTERM_HANDLER, _PREV_SIGINT_HANDLER
    if _EXIT_HANDLER_INSTALLED:
        return
    try:
        atexit.register(_atexit_drain)
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"atexit register failed: {type(e).__name__}: {e}")
    try:
        _PREV_SIGTERM_HANDLER = signal.signal(
            signal.SIGTERM, _signal_drain_handler,
        )
        if _PREV_SIGTERM_HANDLER is _signal_drain_handler:
            _PREV_SIGTERM_HANDLER = signal.SIG_DFL
    except (ValueError, OSError) as e:
        # Signal handlers only work on main thread; in worker threads
        # signal.signal raises ValueError. Fail-open.
        _breadcrumb(f"SIGTERM install skipped: {type(e).__name__}: {e}")
    try:
        _PREV_SIGINT_HANDLER = signal.signal(
            signal.SIGINT, _signal_drain_handler,
        )
        if _PREV_SIGINT_HANDLER is _signal_drain_handler:
            _PREV_SIGINT_HANDLER = signal.SIG_DFL
    except (ValueError, OSError) as e:
        _breadcrumb(f"SIGINT install skipped: {type(e).__name__}: {e}")
    _EXIT_HANDLER_INSTALLED = True


# ---------------------------------------------------------------------------
# Test helpers (NOT public API — prefixed _; harness uses these)
# ---------------------------------------------------------------------------


def _reset_for_test() -> None:
    """Clear all in-process spool state (caches + handler latch + buffer)."""
    global _EXIT_HANDLER_INSTALLED, _IN_FORENSIC_EMIT, _IN_SPOOL_APPEND
    global _PREV_SIGTERM_HANDLER, _PREV_SIGINT_HANDLER
    global _EXIT_DEADLINE_MONOTONIC
    if _EXIT_HANDLER_INSTALLED:
        for signum, previous in (
            (signal.SIGTERM, _PREV_SIGTERM_HANDLER),
            (signal.SIGINT, _PREV_SIGINT_HANDLER),
        ):
            if previous is None:
                continue
            try:
                if signal.getsignal(signum) is _signal_drain_handler:
                    signal.signal(signum, previous)
            except (ValueError, OSError):  # pragma: no cover
                pass
    _SPOOL_HEADER_CACHE.clear()
    _ORDINAL_COUNTER.clear()
    _JOURNAL_BUFFER.clear()
    _EXIT_HANDLER_INSTALLED = False
    _PREV_SIGTERM_HANDLER = None
    _PREV_SIGINT_HANDLER = None
    _EXIT_DEADLINE_MONOTONIC = None
    _IN_FORENSIC_EMIT = False
    _IN_SPOOL_APPEND = False
