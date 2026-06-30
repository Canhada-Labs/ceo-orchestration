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

_SPOOL_PREFIX = "audit-spool"
_JOURNAL_PREFIX = "audit-pending"
_DRAINING_SUFFIX_TOKEN = ".draining."
_MALFORMED_SUFFIX_TOKEN = ".malformed."
_QUARANTINED_SUFFIX_TOKEN = ".quarantined."
_TMP_SUFFIX_TOKEN = ".tmp."
# PLAN-119 WS-D1 — test-origin spool quarantine suffix. A spool minted under a
# test signal is stamped ``_origin:"test"`` in its header; if such a spool is
# ever drained while the canonical destination IS the live chain, it is renamed
# out of the drain path with this token so its entries never reach the live
# canonical append.
_TEST_ORIGIN_SUFFIX_TOKEN = ".test-origin."
# PLAN-119 WS-D1 — the live-log path snapshot env var. Set by the WS-A session
# fixture (``_lib/test_isolation``) BEFORE it redirects the env, so the drainer —
# which post-redirect cannot infer the real live path from the environment — can
# compare the canonical destination against it. The literal is DUPLICATED here
# (NOT imported) because this kernel module must not depend on the test helper;
# the two MUST stay in sync (see ``_lib/test_isolation.LIVE_LOG_SNAPSHOT_VAR``).
_LIVE_LOG_SNAPSHOT_VAR = "CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT"

_SPOOL_UUID_HEX_LEN = 16   # secrets.token_hex(8) -> 16 hex chars
_DRAIN_EPOCH_HEX_LEN = 8   # secrets.token_hex(4) -> 8 hex chars


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DrainStats:
    """Summary of a single drain_now() invocation.

    iter3-P2-1: `intentionally_deleted` counts entries silently removed from
    spool during drain (duplicate-tuple rejection — paired with the
    audit_spool_intentionally_deleted forensic emit). Surfaced into
    JournalReconciliation.intentionally_deleted for AC10 visibility.
    """

    appended: int = 0
    skipped_idempotent: int = 0
    rejected_duplicate_tuple: int = 0
    intentionally_deleted: int = 0
    quarantined_files: int = 0
    # PLAN-119 WS-D1 — count of _origin:"test" spools refused at a live-chain drain.
    test_origin_quarantined: int = 0
    partial_lines_discarded: int = 0
    files_consumed_fully: int = 0
    files_split_remainder: int = 0
    in_recovery_mode: bool = False
    drain_epoch: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
    # (ADR-055-AMEND-3) — True when an OPPORTUNISTIC (force=False)
    # drain yielded the canonical lock to another drainer without blocking.
    # `ok` stays True (not an error): the lock holder's global sweep plus the
    # yielding process's own later drain cover its events. NEVER persisted to
    # the audit log (in-process DrainStats only; no Sec MF-3 surface).
    contended_skip: bool = False


@dataclass
class JournalReconciliation:
    """Counters emitted to audit_flush_dropped_count at session-start."""

    begin_no_commit: int = 0
    commit_no_drained: int = 0
    recovered: int = 0
    truly_lost: int = 0
    tamper_rejected: int = 0
    intentionally_deleted: int = 0


# ---------------------------------------------------------------------------
# Path helpers — mirror audit_emit conventions
# ---------------------------------------------------------------------------


# PLAN-111 Wave A — single-slot cache for _project_dir_from_env + _state_dir.
# Keyed on env-tuple (CEO_AUDIT_LOG_DIR, HOME); replace-on-miss; explicit
# reset via _reset_caches_for_test() bound to TestEnvContext.setUp/tearDown.
# Single-threaded contract: concurrent os.environ mutation = UB; future
# threading plans must add per-thread cache or thread-local env snapshot.
# Debate Round 1: SA-K1 (single-slot), SA-K7 (single-threaded), SA-K10
# (permission re-assertion on cache MISS), AC-A2a (store-on-mkdir-success
# only; no cached-as-unusable Path).
_PROJECT_DIR_CACHE: "Optional[Tuple[Tuple[Optional[str], Optional[str]], Path]]" = None
_STATE_DIR_CACHE: "Optional[Tuple[Tuple[Optional[str], Optional[str]], Path]]" = None


def _reset_caches_for_test() -> None:
    """Clear _project_dir_from_env + _state_dir caches.

    PLAN-111 Wave A.5: bound to TestEnvContext.setUp/tearDown to avoid
    cross-test leakage when CEO_AUDIT_LOG_DIR or HOME mutate. Also bound
    via unittest.addModuleCleanup in test_lifecycle_edge_cases.py for
    bare-TestCase classes that don't inherit TestEnvContext.

    PRODUCTION CODE MUST NOT CALL THIS — it's a test-only API. Calling
    mid-flight flushes the cache and re-pays the mkdir + lstat cost on
    next emit (correctness preserved; perf regressed for one call).
    """
    global _PROJECT_DIR_CACHE, _STATE_DIR_CACHE
    _PROJECT_DIR_CACHE = None
    _STATE_DIR_CACHE = None


def _project_dir_from_env() -> Path:
    """Return the audit project dir (BYTE-IDENTICAL to audit_emit._audit_dir).

    P1-5: must mirror audit_emit._audit_dir() exactly — only CEO_AUDIT_LOG_DIR
    + HOME. CEO_AUDIT_LOG_PATH is the FILE path, not the dir path, so we do
    NOT derive the dir from it (audit_emit doesn't either).

    PLAN-111 Wave A: single-slot cache keyed on (CEO_AUDIT_LOG_DIR, HOME).
    Cache HIT skips re-construction of Path object (saves ~7us/call x
    5.7x/emit cumulative). Cache MISS replaces the slot atomically.

    Single-threaded contract: concurrent os.environ mutation = UB.
    """
    global _PROJECT_DIR_CACHE
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    env_home = os.environ.get("HOME")
    env_key = (env_dir, env_home)
    cached = _PROJECT_DIR_CACHE
    if cached is not None and cached[0] == env_key:
        return cached[1]
    if env_dir:
        p = Path(env_dir)
    else:
        home = env_home or str(Path.home())
        p = Path(home) / ".claude" / "projects" / "ceo-orchestration"
    _PROJECT_DIR_CACHE = (env_key, p)
    return p


def _state_dir() -> Path:
    """Return <audit_dir>/state/ ensuring parents exist (0700).

    P1-5: state dir is unconditionally a child of audit_emit._audit_dir();
    no CEO_PROJECT_STATE_DIR override (audit_emit doesn't expose one).

    PLAN-111 Wave A: single-slot cache keyed on (CEO_AUDIT_LOG_DIR, HOME).
    Cache HIT skips mkdir syscall + Path construction (saves ~17us/call x
    5.7x/emit cumulative ~= 100us/emit recovery).

    Cache MISS semantics (AC-A2a + SA-K10 permission re-assertion +
    PLAN-113 W4-SEC mode-mismatch self-heal):
      1. Resolve target Path (uses _project_dir_from_env cache implicitly).
      2. Attempt mkdir(parents=True, exist_ok=True, mode=0o700).
      3. If mkdir FAILS: breadcrumb + DO NOT cache (next call retries).
      4. If mkdir SUCCEEDS: validate via lstat() that dir is not a symlink,
         is owned by os.getuid(), and has mode 0o700.
         - symlink / wrong-owner mismatch: FAIL-CLOSED (raise) — we never
           chmod-and-trust an attacker-controlled or other-owned dir.
         - mode-only mismatch (e.g. a pre-existing state/ at 0o755 created
           by an older path; exist_ok=True does NOT relax perms): attempt
           SELF-HEAL via os.chmod(d, 0o700) then RE-lstat + re-validate the
           full invariant. If it is now a non-symlink, owned by os.getuid(),
           AND 0o700 → PROCEED (cache + return). Otherwise keep the SA-K10
           fail-CLOSED.
      5. Only if validation (incl. any self-heal) succeeds: cache the Path.

    Single-threaded contract: concurrent os.environ mutation = UB.
    """
    global _STATE_DIR_CACHE
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    env_home = os.environ.get("HOME")
    env_key = (env_dir, env_home)
    cached = _STATE_DIR_CACHE
    if cached is not None and cached[0] == env_key:
        return cached[1]
    d = _project_dir_from_env() / "state"
    mkdir_ok = False
    try:
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        mkdir_ok = True
    except OSError as e:
        _breadcrumb(f"_state_dir mkdir failed (no cache): "
                    f"{type(e).__name__}: {e}")
    if mkdir_ok:
        try:
            import stat as _stat_mod

            def _classify(st_mode: int, st_uid: int) -> "Optional[str]":
                """Return a mismatch reason, or None when state/ is healthy."""
                if _stat_mod.S_ISLNK(st_mode):
                    return f"is_symlink: {d}"
                if st_uid != os.getuid():
                    return f"uid_mismatch: {st_uid} != {os.getuid()}"
                if (st_mode & 0o777) != 0o700:
                    return f"mode_mismatch: {oct(st_mode & 0o777)} != 0o700"
                return None

            st = os.lstat(str(d))
            mismatch_reason: "Optional[str]" = _classify(st.st_mode, st.st_uid)

            # PLAN-113 W4-SEC self-heal: a pre-existing state/ dir at a mode
            # other than 0o700 (most commonly 0o755 from an older code path —
            # exist_ok=True does NOT relax perms on an existing dir)
            # previously fail-CLOSED on EVERY call, dropping the audit event
            # and flooding the spool. Self-heal ONLY the mode-mismatch case
            # (NEVER symlink / wrong-owner — chmod-and-trusting those is
            # exactly the attack we fail closed on): chmod 0o700, then
            # RE-lstat and re-validate the FULL invariant from scratch.
            if (mismatch_reason is not None
                    and not _stat_mod.S_ISLNK(st.st_mode)
                    and st.st_uid == os.getuid()):
                healed = False
                fd = None
                try:
                    # PLAN-113 Codex B3 P2 — close the chmod TOCTOU: a path-based
                    # os.chmod follows a symlink if state/ is swapped between the
                    # initial lstat and the chmod, applying 0o700 to the attacker's
                    # target. Open with O_NOFOLLOW (refuse a symlinked final
                    # component) | O_DIRECTORY (refuse a non-dir), then fchmod +
                    # fstat the FD — no path re-resolution, so no race window.
                    fd = os.open(
                        str(d), os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY
                    )
                    os.fchmod(fd, 0o700)
                    fst = os.fstat(fd)
                    mismatch_reason = _classify(fst.st_mode, fst.st_uid)
                    if mismatch_reason is None:
                        st = fst
                        healed = True
                except OSError as e:
                    _breadcrumb(
                        f"_state_dir self-heal (O_NOFOLLOW fchmod) failed "
                        f"(FAIL-CLOSED): {type(e).__name__}: {e}"
                    )
                finally:
                    if fd is not None:
                        try:
                            os.close(fd)
                        except OSError:
                            pass
                if healed:
                    _breadcrumb(
                        f"_state_dir mode self-healed to 0o700: {d}"
                    )

            if mismatch_reason is not None:
                # PLAN-111 Wave A SA-K10 fail-CLOSED (Codex R2 P0 fix):
                # detecting + not-caching is fake-security; caller would
                # still write to the attacker-controlled symlink target.
                # Raise OSError so callers' fail-open path catches it
                # (matches existing _state_dir fail-open semantics) and
                # diverts the write to fallback path. PLAN-113 W4-SEC: we
                # only reach here for symlink / wrong-owner, OR a mode
                # mismatch the chmod self-heal could not resolve.
                _breadcrumb(
                    f"_state_dir SECURITY mismatch (FAIL-CLOSED): "
                    f"{mismatch_reason}"
                )
                raise PermissionError(
                    f"_state_dir permission re-assertion failed: "
                    f"{mismatch_reason}"
                )
            _STATE_DIR_CACHE = (env_key, d)
        except PermissionError:
            # Re-raise the SA-K10 fail-CLOSED so caller handles.
            raise
        except OSError as e:
            _breadcrumb(f"_state_dir lstat failed (no cache): "
                        f"{type(e).__name__}: {e}")
    return d


def _canonical_log_path() -> Path:
    """Mirror audit_emit._log_path() — canonical audit-log.jsonl."""
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    return _project_dir_from_env() / "audit-log.jsonl"


def _canonical_log_lock() -> Path:
    """Mirror audit_emit._lock_path() — sibling .lock file."""
    env = os.environ.get("CEO_AUDIT_LOG_LOCK")
    if env:
        return Path(env)
    return _project_dir_from_env() / "audit-log.lock"


def _errors_path() -> Path:
    """Breadcrumb file for fail-open infra errors."""
    env = os.environ.get("CEO_AUDIT_LOG_ERR")
    if env:
        return Path(env)
    return _project_dir_from_env() / "audit-log.errors"


def _spool_path(pid: int) -> Path:
    """Active spool path for a given PID (header + body)."""
    return _state_dir() / f"{_SPOOL_PREFIX}.{pid}.jsonl"


def _journal_path(pid: int) -> Path:
    """Per-PID journal path."""
    return _state_dir() / f"{_JOURNAL_PREFIX}.{pid}.journal"


def _aggregate_journal_path() -> Path:
    """Aggregate journal for swept dead-PID envelopes."""
    return _state_dir() / f"{_JOURNAL_PREFIX}.journal"


def _aggregate_journal_lock_path() -> Path:
    """flock for aggregation sweep at session-start."""
    return _state_dir() / f"{_JOURNAL_PREFIX}.journal.aggregation.lock"


def _spool_flock_path(pid: int) -> Path:
    """Per-PID spool flock sibling (NOT same fd as the spool file)."""
    return _state_dir() / f"{_SPOOL_PREFIX}.{pid}.jsonl.lock"


def _journal_flock_path(pid: int) -> Path:
    """Per-PID journal flock sibling."""
    return _state_dir() / f"{_JOURNAL_PREFIX}.{pid}.journal.lock"


# P0-1: single helper for the .draining.<epoch> filename construction.
# Bug fix — old code did `f"{spool_path}draining.{epoch}"` (missing dot)
# producing audit-spool.<pid>.jsonldraining.<epoch>; glob sweep failed.
def _draining_path(spool_path: Path, epoch: str) -> Path:
    """audit-spool.<pid>.jsonl → audit-spool.<pid>.draining.<epoch>."""
    stem = spool_path.stem  # 'audit-spool.<pid>' (strips trailing .jsonl)
    return spool_path.with_name(f"{stem}.draining.{epoch}")


# P2-2: validated _spool_uuid regex (16 lowercase hex chars, secrets.token_hex(8))
_SPOOL_UUID_RE = re.compile(r"^[0-9a-f]{16}$")


def _validate_spool_header_strict(header: Any) -> bool:
    """Strict 4-field header invariant — same predicate used by Phase 2
    quarantine and `_ensure_spool_header` PID-reuse path.

    iter5-P1 closure: factored out so writer-side reuse cannot accept a
    header that the drainer will later reject. Mismatch between writer
    and drainer validation = silent data loss for events appended after
    the lax reuse but before Phase 2 quarantine.

    Returns True only when ALL of:
      - dict with `_spool_header: True`
      - `_spool_uuid: str` of length 16 and matching `^[0-9a-f]{16}$`
      - `_pid: int`
      - `_created_wall_ns: int`
      - `_created_monotonic_ns: int`
    """
    if not isinstance(header, dict):
        return False
    if header.get("_spool_header") is not True:
        return False
    spool_uuid = header.get("_spool_uuid")
    if (not isinstance(spool_uuid, str)
            or len(spool_uuid) != _SPOOL_UUID_HEX_LEN
            or _SPOOL_UUID_RE.match(spool_uuid) is None):
        return False
    if not isinstance(header.get("_pid"), int):
        return False
    if not isinstance(header.get("_created_wall_ns"), int):
        return False
    if not isinstance(header.get("_created_monotonic_ns"), int):
        return False
    return True


def _recover_ordinal_counter(spool_path: Path) -> int:
    """Return ordinal_within_file counter from existing spool body.

    iter4-P1-1: replaces prior `\n`-counting approach. A complete body
    line WITHOUT trailing `\n` (writer fsync'd then crashed before
    terminator) was previously counted as zero entries → ordinal 0
    re-issued → Phase 3 monotonicity quarantine. Now: parse each line
    (terminated or not), return max(ordinal)+1. Returns 0 on missing/
    empty/header-only/no-valid-ordinals.
    """
    try:
        with open(str(spool_path), "rb") as f:
            content = f.read()
    except OSError:
        return 0
    if b"\n" not in content:
        return 0
    _header, body = content.split(b"\n", 1)
    if not body:
        return 0
    max_ord = -1
    for line_bytes in body.split(b"\n"):
        if not line_bytes.strip():
            continue
        try:
            entry = json.loads(line_bytes)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(entry, dict):
            continue
        o = entry.get("ordinal_within_file")
        if isinstance(o, int) and o > max_ord:
            max_ord = o
    return max_ord + 1 if max_ord >= 0 else 0


class _SpoolHeaderUnrecoverable(OSError):
    """Raised when an existing spool has an invalid header AND quarantine
    rename fails. Caller (`spool_append`) MUST abort fail-open — minting
    a fresh header over the still-present corrupt file would silently
    lose the new event (Phase 2 quarantines the whole file later).
    iter6-P1 closure.
    """


def _quarantine_corrupt_active_spool(spool_path: Path, pid: int) -> bool:
    """Rename malformed-header active spool aside; forensic emit.

    iter4-P1-2: caller MUST hold `_spool_flock_path(pid)`. We must NOT
    call drain_now() here (Phase 2 re-acquires this same flock →
    self-timeout). _forensic() has its own re-entry guard so the emit
    path won't recurse into spool_append.

    iter6-P1: returns True on successful rename, False on rename failure.
    Caller MUST honor False by aborting the current append fail-open
    (NOT minting a fresh header over the still-present corrupt file —
    that would let new events land behind a header Phase 2 will quarantine).
    """
    epoch = secrets.token_hex(4)
    corrupt_path = spool_path.with_name(
        f"{spool_path.stem}.corrupt-header.{epoch}"
    )
    try:
        os.rename(str(spool_path), str(corrupt_path))
    except OSError as e:
        _breadcrumb(
            f"quarantine_corrupt_active_spool rename failed pid={pid}: "
            f"{type(e).__name__}: {e}"
        )
        return False
    _forensic("audit_spool_tamper_detected", {
        "mismatch_kind": "malformed_active_spool_header",
        "spool_pid": pid,
        "corrupt_path": str(corrupt_path),
        "drain_epoch": epoch,
    })
    return True


# ---------------------------------------------------------------------------
# Fail-open breadcrumb
# ---------------------------------------------------------------------------


def _breadcrumb(message: str) -> None:
    """Append a one-line forensic crumb; NEVER raise."""
    try:
        p = _errors_path()
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with p.open("a", encoding="utf-8") as f:
            f.write(f"{ts} spool_writer: {message}\n")
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Kill-switch + exit-handler state
# ---------------------------------------------------------------------------


def is_sync_mode() -> bool:
    """CEO_AUDIT_SYNC_MODE=1 reverts to pre-Wave-A synchronous behavior."""
    return os.environ.get("CEO_AUDIT_SYNC_MODE", "") == "1"


_EXIT_HANDLER_INSTALLED = False
_PREV_SIGTERM_HANDLER: Any = None
_PREV_SIGINT_HANDLER: Any = None

# Per-PID spool header cache — populated on first append; mirrors what the
# spool file's header line carries. We keep an in-process counter for the
# strictly-monotonic ordinal_within_file.
_SPOOL_HEADER_CACHE: Dict[int, Dict[str, Any]] = {}
_ORDINAL_COUNTER: Dict[int, int] = {}

# Callback wired by audit_emit so we can emit forensic events without
# importing audit_emit (circular dep). audit_emit.install() passes a
# function with signature (action: str, fields: Dict[str, Any]) -> None.
_FORENSIC_EMIT: Optional[Callable[[str, Dict[str, Any]], None]] = None

# P1-4 reentrancy guard: prevent the cycle
#   spool_append → drain → _forensic → emit_generic → spool_append → ...
# Module-level flag set during _forensic() execution; if re-entered, write
# a breadcrumb and bail (no spool, no canonical).
_IN_FORENSIC_EMIT = False

# P1-1 reentrancy guard: prevent signal handler calling drain_now() from
# deadlocking against a writer mid-spool_append in the same PID. The signal
# handler checks this and bails (the partial spool entry is picked up by
# next-session reconciliation).
_IN_SPOOL_APPEND = False

# PLAN-094-FOLLOWUP Wave A.3-fail-open (option B) — module-level durability
# indicator for the last `spool_append()` call. audit_emit wire-in checks
# `last_append_succeeded()` after each call; on False, falls through to the
# sync canonical write path. Preserves the existing fail-open invariant
# (`spool_append` never raises to caller) while restoring durability defense
# depth on per-PID spool flock alloc / encode / OSError / unexpected paths.
_LAST_APPEND_SUCCEEDED = True


def last_append_succeeded() -> bool:
    """Return True if the most recent spool_append() persisted durably.

    audit_emit wire-in uses this to decide whether to fall back to the
    sync canonical write path (False = silent-drop on spool side; sync
    is now responsible for durability of THIS event).
    """
    return _LAST_APPEND_SUCCEEDED

# P1-2 journal buffer state (per-PID amortized fsync).
# Buffer envelopes in memory; flush + fsync at: drain boundary, signal,
# atexit, or every _JOURNAL_FLUSH_EVERY writes. ADR-055-AMEND-1 §3 line 96:
# "journal fsync every 100ms OR 10 emits".
_JOURNAL_FLUSH_EVERY = 10
_JOURNAL_BUFFER: Dict[int, List[bytes]] = {}


def set_forensic_emitter(emit_fn: Callable[[str, Dict[str, Any]], None]) -> None:
    """Wire the forensic emit callback (called by audit_emit on import)."""
    global _FORENSIC_EMIT
    _FORENSIC_EMIT = emit_fn


def _forensic(action: str, fields: Dict[str, Any]) -> None:
    """Emit a forensic audit event via wired callback; swallow errors.

    P1-4: recursion guard — if we're already inside a _forensic() emit,
    write a breadcrumb and return without re-entering spool_append.
    """
    global _IN_FORENSIC_EMIT
    cb = _FORENSIC_EMIT
    if cb is None:
        return
    if _IN_FORENSIC_EMIT:
        _breadcrumb(f"forensic re-entry blocked: {action}")
        return
    _IN_FORENSIC_EMIT = True
    try:
        cb(action, fields)
    except Exception as e:  # pragma: no cover
        _breadcrumb(f"forensic emit failed: {action}: {type(e).__name__}: {e}")
    finally:
        _IN_FORENSIC_EMIT = False


# ---------------------------------------------------------------------------
# Spool header / append (Phase 0 — writer-side)
# ---------------------------------------------------------------------------


def _origin_for_new_spool() -> str:
    """PLAN-119 WS-D1 — write-time origin stamp for a freshly-minted spool header.

    Returns ``"test"`` when a test signal is present AT WRITE TIME
    (``CEO_TEST_HARNESS=1`` or ``PYTEST_CURRENT_TEST`` set), else ``"live"``.
    The writer knows the truth; the drainer cannot infer it later, so the stamp
    is minted ONCE per spool (header) and is sticky to that PID's file. A real
    session writes ``"live"`` and is never quarantined; legacy spool with no
    ``_origin`` defaults to ``"live"`` at drain time (fail-safe toward never
    dropping a real event).
    """
    if (os.environ.get("CEO_TEST_HARNESS") == "1"
            or os.environ.get("PYTEST_CURRENT_TEST")):
        return "test"
    return "live"


def _ensure_spool_header(pid: int, _retry_depth: int = 0) -> Dict[str, Any]:
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
                    return _ensure_spool_header(pid, _retry_depth=_retry_depth + 1)
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
                    header = _ensure_spool_header(pid)
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


def _phase4_build_batch(
    deduped: List[Tuple[Tuple[int, int, str, int], Dict[str, Any], _DrainingFile, int]],
    drain_epoch: str,
    in_recovery: bool,
    stats: DrainStats,
    starting_processed: int = 0,
) -> Tuple[List[bytes], List[_DrainingFile], Dict[str, Set[int]], Optional[bytes], List[Tuple[str, int]]]:
    """Compute HMAC chain; produce canonical-log batch lines.

    Returns (batch_line_bytes, fully_consumed_files,
    per_file_consumed_indices, last_hmac_bytes, drained_record_ids_by_pid).

    iter2-P0-1: per_file_consumed is now Dict[str, Set[int]] (body indices,
    not a prefix-count). Phase 5 splits the remainder using the COMPLEMENT
    of the set — out-of-order index consumption (e.g. clock-skew rollback
    where a LATER body index sorts ahead of an EARLIER one and is cut by
    K_MAX) no longer trashes unprocessed earlier lines.

    iter2-P1-1: idempotent-skip branch now ALSO appends (record_id, pid)
    to drained_ids and marks the index consumed — without this, the matching
    journal `commit` envelope stays as commit_no_drained forever (phantom
    inflight count in AC10).

    iter2-P2-1: canonical output honors the SOURCE file's drain_epoch
    (src_file.drain_epoch) — important for forensic correlation when an
    in-recovery drain re-emits entries from a prior-cycle .draining file.

    iter3-P0-1: K_MAX counts TOTAL PROCESSED entries (appended + idempotent
    skipped + intentionally consumed via tamper/duplicate paths), NOT just
    appended. Without this, repeated partial-crash cycles where each crash
    leaves K_MAX entries in .draining and the next drain hits all K_MAX as
    skipped + processes K_MAX fresh can accumulate >K_TAIL_WINDOW processed
    entries per cycle → entries fall out of the skip-guard tail window on
    a subsequent crash cycle → re-appended duplicates in canonical log.
    Capping TOTAL processed bounds disk-write + idempotent work per drain
    cycle so window-overflow cannot occur.

    Honors K_MAX cap; remaining un-consumed entries are left for the next
    drain cycle via Phase 5 atomic split.
    """
    log_path = _canonical_log_path()

    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.1 — Path B variant 1 hoist.
    # Probe rotation BEFORE reading canonical tail (and therefore before
    # computing prev_hmac), so this batch always anchors against the
    # CURRENT canonical file (post-rotation if applicable).
    #
    # Prior bug: Phase 4 read prev_hmac from the about-to-rotate file;
    # Phase 5 detected rotation but batch_lines were already HMAC-chained
    # against the old chain → verifier (resets at file boundary per
    # ADR-055 §2) saw STATUS_TAMPER at line 1 of the new file.
    # Per F-7.7 (PLAN-112 wave-c-bundles/C10) + D3 confirmation.
    # Fail-open: any rotation exception is breadcrumbed and the read
    # proceeds against whatever log path is current.
    try:
        from _lib import audit_emit as _audit_emit_lazy
        from _lib import audit_hmac as _audit_hmac_lazy
        # PLAN-143 item-2 (audit-errors-02): guard the rotation probe.
        # Under test/shim wiring the lazily-imported object can be an
        # _EmitCapture double that lacks _rotate_if_needed_safe; calling
        # it raised AttributeError into the fail-open except below, which
        # breadcrumbed cosmetic audit-log.errors noise and silently
        # skipped the probe. getattr-guard -> no attribute means "no
        # rotation" (None), taking the same intended branch without noise.
        _rotate_probe = getattr(
            _audit_emit_lazy, "_rotate_if_needed_safe", None
        )
        rotated_to_phase4 = (
            _rotate_probe(log_path) if callable(_rotate_probe) else None
        )
        if rotated_to_phase4 is not None and not _audit_hmac_lazy.is_disabled():
            try:
                _audit_hmac_lazy.reset_chain_on_rotation()
            except Exception as re:
                _breadcrumb(
                    f"phase4 rotation HMAC reset failed: "
                    f"{type(re).__name__}: {re}"
                )
            # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — emit
            # chain_reset_marker as line 1 of new file + manifest. Fail-open
            # (marker absence → verifier legacy mode, not tamper signal).
            try:
                _audit_emit_lazy._emit_chain_reset_marker_under_lock(
                    log=log_path,
                    previous_archive_path=str(rotated_to_phase4),
                    rotation_trigger="size_threshold",
                )
            except Exception as me:
                _breadcrumb(
                    f"phase4 chain_reset_marker emit failed: "
                    f"{type(me).__name__}: {me}"
                )
    except Exception as e:
        # Fail-open: rotation probe never blocks the canonical read.
        _breadcrumb(f"phase4 rotation probe failed: {type(e).__name__}: {e}")

    # AFTER rotation probe: read tail from (now-current) file.
    prev_hmac, tail_entries = _read_canonical_tail(log_path, K_TAIL_WINDOW)
    drain_sha_set: set = set()
    for e in tail_entries:
        ds = e.get("_drain_sha256")
        if isinstance(ds, str) and len(ds) == 64:
            drain_sha_set.add(ds)

    if _HMAC_AVAILABLE and _audit_hmac is not None and prev_hmac is None:
        # Empty log + HMAC available → genesis (which is correct
        # post-rotation since the new file is empty).
        prev_hmac = _audit_hmac.GENESIS_PREV

    batch_lines: List[bytes] = []
    # iter2-P0-1: set-of-indices, not prefix-count.
    per_file_consumed: Dict[str, Set[int]] = {}
    drained_ids: List[Tuple[str, int]] = []  # P1-3: (record_id, pid)
    last_hmac: Optional[bytes] = prev_hmac

    def _mark(path_str: str, idx: int) -> None:
        per_file_consumed.setdefault(path_str, set()).add(idx)

    # iter3-P0-1: cap on TOTAL processed (appended + idempotent_skipped +
    # tamper-consumed); breaking on appended-only allowed cumulative
    # processed > K_TAIL_WINDOW across recovery cycles → window overflow.
    # iter4-P2-2: `starting_processed` carries duplicate-cleanup count from
    # Phase 3 so combined Phase-3 + Phase-4 work ≤ K_MAX per drain cycle.
    processed = starting_processed
    for key, entry, src_file, body_idx in deduped:
        if processed >= K_MAX:
            break
        path_key = str(src_file.path)

        # P1-3: pull record_id off the spool entry BEFORE stripping internal
        # fields so we can emit op:"drained" with the matching id.
        rec_id = entry.get("record_id")

        entry_clean = {
            k: v for k, v in entry.items()
            if not (isinstance(k, str) and k.startswith("_drain_"))
            and k != "hmac" and k != "hmac_error"
        }
        try:
            sha = _sha256_of_canonical_json(entry_clean)
        except Exception as e:
            _breadcrumb(f"sha compute failed: {type(e).__name__}: {e}")
            # Treat unencodable entry like a tamper — skip + count
            stats.partial_lines_discarded += 1
            _mark(path_key, body_idx)
            # iter3-P0-1: tamper-consumed counts toward K_MAX budget
            processed += 1
            continue

        if sha in drain_sha_set:
            stats.skipped_idempotent += 1
            severity = "INFORMATIONAL" if in_recovery else "ALARM"
            _forensic("audit_spool_unexpected_skip", {
                "drain_epoch": drain_epoch,
                "spool_uuid": key[2],
                "ordinal_within_file": key[3],
                "skipped_sha256": sha,
                "drain_in_recovery_mode": in_recovery,
                "severity": severity,
            })
            _mark(path_key, body_idx)
            # iter2-P1-1: also commit drained_id so the journal compactor
            # emits op:"drained" for this record. Without this, the matching
            # `commit` envelope stays as commit_no_drained forever in the
            # journal (AC10 phantom inflight). The canonical batch line was
            # already appended on the prior crashed drain — this entry is
            # "drained" from the journal's perspective even though we are
            # not re-appending the bytes this cycle.
            if isinstance(rec_id, str) and rec_id:
                drained_ids.append((rec_id, src_file.pid))
            # iter3-P0-1: idempotent-skip counts toward K_MAX budget so
            # window-overflow on multi-crash cycles is structurally
            # impossible (processed ≤ K_MAX < K_TAIL_WINDOW).
            processed += 1
            continue

        chained = dict(entry_clean)
        chained["_drain_sha256"] = sha
        # iter2-P2-1: honor source file's drain_epoch for forensic
        # correlation (this entry was first staged in that cycle).
        chained["_drain_epoch"] = src_file.drain_epoch

        if (_HMAC_AVAILABLE and _audit_hmac is not None
                and not _audit_hmac.is_disabled()):
            try:
                key_bytes = _audit_hmac.get_or_create_key()
                digest = _audit_hmac.compute_entry_hmac(
                    key_bytes,
                    last_hmac if last_hmac is not None else _audit_hmac.GENESIS_PREV,
                    chained,
                )
                chained["hmac"] = digest.hex()
                last_hmac = digest
            except _audit_hmac.AuditProducerPathPollutionError as ppe:
                # PLAN-118 AC-B4 chokepoint 4 / recursion-safety case 5 —
                # the spool fast-path (audit_emit._write_event line 1760)
                # appends to spool BEFORE local HMAC computation; the
                # HMAC is then computed HERE at drain time. On
                # canonical-resolution mismatch at drain: refuse to
                # compute HMAC for the batch entry; normalize the entry
                # to hmac:null + closed-enum hmac_error BEFORE the entry
                # is appended to the chain (so polluted HMACs never enter
                # the chain at all). Emit AC-B5 breadcrumb with
                # chokepoint=spool_drain (safe — the typed emitter's own
                # _write_event call will also trigger this same
                # exception and recurse-fail-OPEN through the same
                # channel; the breadcrumb's purpose is exactly that
                # forensic signal).
                chained["hmac"] = None
                chained["hmac_error"] = "producer_path_pollution_detected"
                _breadcrumb(
                    f"hmac_error: producer_path_pollution_detected "
                    f"(chokepoint=spool_drain): {ppe}"
                )
                # Parse the exception payload for the AC-B5 breadcrumb.
                try:
                    _msg = str(ppe)
                    _rc = "audit_emit_path_pollution"
                    _psp = "00000000"
                    _ecp = "00000000"
                    _valid_rcs = (
                        "audit_emit_path_pollution",
                        "canonical_json_path_pollution",
                        "audit_hmac_path_pollution",
                    )
                    for _tok in _msg.split():
                        if _tok.startswith("reason_code="):
                            _cand = _tok.split("=", 1)[1]
                            if _cand in _valid_rcs:
                                _rc = _cand
                        elif _tok.startswith("path_sha256_prefix="):
                            _cand = _tok.split("=", 1)[1]
                            if len(_cand) == 8 and all(c in "0123456789abcdef" for c in _cand):
                                _psp = _cand
                        elif _tok.startswith("expected_canonical_prefix="):
                            _cand = _tok.split("=", 1)[1]
                            if len(_cand) == 8 and all(c in "0123456789abcdef" for c in _cand):
                                _ecp = _cand
                    # Lazy-import the typed emitter to avoid circular import
                    # at module load (spool_writer is imported from audit_emit).
                    from _lib import audit_emit as _audit_emit
                    _audit_emit.emit_audit_producer_path_pollution_detected(
                        chokepoint="spool_drain",
                        reason_code=_rc,
                        path_sha256_prefix=_psp,
                        expected_canonical_prefix=_ecp,
                    )
                except Exception as _be:  # pragma: no cover
                    _breadcrumb(
                        f"AC-B5 spool_drain breadcrumb emit failed: "
                        f"{type(_be).__name__}: {_be}"
                    )
            except Exception as e:
                chained["hmac"] = None
                chained["hmac_error"] = f"{type(e).__name__}: {e}"
                _breadcrumb(f"hmac compute failed: {type(e).__name__}: {e}")

        try:
            line = json.dumps(
                chained, separators=(",", ":"), ensure_ascii=False,
            ).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as e:
            _breadcrumb(f"phase4 encode failed: {type(e).__name__}: {e}")
            _mark(path_key, body_idx)
            # iter3-P0-1: encode-failure consumed counts toward K_MAX.
            processed += 1
            continue
        batch_lines.append(line)
        _mark(path_key, body_idx)
        # P1-3: track for op:"drained" envelope emission
        if isinstance(rec_id, str) and rec_id:
            drained_ids.append((rec_id, src_file.pid))
        # iter3-P0-1: append counts toward K_MAX (was: `appended += 1`).
        processed += 1

    fully_consumed: List[_DrainingFile] = []
    return batch_lines, fully_consumed, per_file_consumed, last_hmac, drained_ids


# ---------------------------------------------------------------------------
# Phase 5 — atomic append + split + cleanup
# ---------------------------------------------------------------------------


def _phase5_append_canonical(
    batch_lines: List[bytes], last_hmac: Optional[bytes]
) -> int:
    """Append batch to canonical log; single fsync; update sidecar cache.

    iter2-P2-3: chain_length sidecar increment counts HMAC-bearing lines
    only — entries that failed HMAC compute (hmac=null + hmac_error set)
    don't extend the chain even though their bytes are appended. The
    sidecar is a cache for chain-verify performance; counting null-hmac
    lines would diverge from the true HMAC chain length.
    """
    if not batch_lines:
        return 0
    log_path = _canonical_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    # PLAN-094-FOLLOWUP Wave A.3-rotation — probe rotation BEFORE the
    # canonical append so spool-drained writes never accumulate past the
    # configured threshold. Lazy-import audit_emit (circular dep at
    # module load time) + audit_hmac for chain reset.
    try:
        from _lib import audit_emit as _audit_emit_lazy
        from _lib import audit_hmac as _audit_hmac_lazy
        # PLAN-143 item-2 (audit-errors-02): guard the rotation probe — a
        # capture-shim object may lack _rotate_if_needed_safe (see the
        # phase-4 probe above). getattr-guard -> missing attribute means
        # "no rotation" (None), no AttributeError into the fail-open path.
        _rotate_probe = getattr(
            _audit_emit_lazy, "_rotate_if_needed_safe", None
        )
        rotated_to = (
            _rotate_probe(log_path) if callable(_rotate_probe) else None
        )
        if rotated_to is not None and not _audit_hmac_lazy.is_disabled():
            try:
                _audit_hmac_lazy.reset_chain_on_rotation()
                # Reset last_hmac so this batch re-anchors at genesis.
                last_hmac = None
            except Exception as re:
                _breadcrumb(
                    f"phase5 rotation HMAC reset failed: "
                    f"{type(re).__name__}: {re}"
                )
    except Exception as e:
        # Fail-open: rotation probe never blocks the canonical append.
        _breadcrumb(f"phase5 rotation probe failed: {type(e).__name__}: {e}")

    payload = b"".join(batch_lines)
    fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)

    if (_HMAC_AVAILABLE and _audit_hmac is not None
            and not _audit_hmac.is_disabled()
            and last_hmac is not None
            and len(last_hmac) == _audit_hmac.HMAC_BYTES):
        try:
            _audit_hmac.write_last_hmac(last_hmac)
        except Exception as e:
            _breadcrumb(f"write_last_hmac failed: {type(e).__name__}: {e}")
        # iter2-P2-3: count HMAC-bearing lines only.
        hmac_bearing = 0
        for line in batch_lines:
            try:
                obj = json.loads(line.rstrip(b"\n").decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(obj, dict):
                continue
            hx = obj.get("hmac")
            if isinstance(hx, str) and len(hx) == 64:
                hmac_bearing += 1
        try:
            current = _audit_hmac.read_chain_length()
            _audit_hmac.write_chain_length(current + hmac_bearing)
        except Exception as e:
            _breadcrumb(f"chain_length update failed: {type(e).__name__}: {e}")
    return len(batch_lines)


def _phase5_split_and_cleanup(
    files: List[_DrainingFile],
    per_file_consumed: Dict[str, Set[int]],
    drain_epoch: str,
    stats: DrainStats,
) -> None:
    """For each draining file: unlink if fully consumed; else atomic-split.

    iter2-P0-1: per_file_consumed is a Set[int] of body INDICES. The
    remainder file is built from the COMPLEMENT (all body indices NOT in
    the set). This correctly handles out-of-order index consumption (e.g.
    wall_ns clock-skew rollback where a later body index sorts BEFORE an
    earlier one and is cut by K_MAX) — prefix-based cleanup would have
    discarded unprocessed earlier lines.

    iter2-P0-3: SKIP any _DrainingFile whose .quarantined flag is set —
    the file is already renamed to .malformed.<epoch>; trying to split
    or unlink the original path would either fail (ENOENT) or, worse,
    re-sweep the renamed quarantined file on a subsequent drain.

    iter2-P1-3: when splitting, mint a NEW drain_epoch for the destination
    so dst path != src path. This closes the `.split.tmp` two-step window
    (old code reused src epoch → dst==src → os.rename(src,dst) no-op AND
    the temp suffix dance remained). Now: tmp → fsync → rename(tmp,
    new_dst) atomic; unlink(src). Single window if rename succeeds.

    P2-4: header is written VERBATIM from file.header_raw — no JSON
    re-encode (preserves byte identity of _spool_uuid sentinel chain).
    """
    for f in files:
        # iter2-P0-3: skip quarantined files — original path doesn't exist
        # at .draining.<epoch> anymore; it was renamed to .malformed.<epoch>.
        if f.quarantined:
            continue
        path_key = str(f.path)
        if f.header is None and not f.body_lines:
            # Already empty (no body) — just unlink the (header-only) file.
            try:
                if f.path.exists():
                    os.unlink(str(f.path))
            except OSError:
                pass
            continue
        consumed_set = per_file_consumed.get(path_key, set())
        total = len(f.body_lines)
        # iter2-P0-1: fully consumed iff every body index is in the set.
        if total == 0 or all(i in consumed_set for i in range(total)):
            try:
                os.unlink(str(f.path))
                stats.files_consumed_fully += 1
            except OSError as e:
                _breadcrumb(f"phase5 unlink failed: {type(e).__name__}: {e}")
            continue

        # iter2-P1-3: mint a NEW epoch for the split destination so
        # dst_path differs from src_path; this collapses the prior
        # two-step `.split.tmp` rename dance into a single rename+unlink.
        new_epoch = secrets.token_hex(4)
        tmp_token = secrets.token_hex(4)
        # tmp is a sibling .tmp.<token> for atomic create+rename within same dir
        tmp_path = f.path.with_name(f.path.name + _TMP_SUFFIX_TOKEN + tmp_token)
        try:
            # P2-4: verbatim header bytes — no JSON re-encode
            header_line = f.header_raw if f.header_raw else (
                json.dumps(
                    f.header, separators=(",", ":"), ensure_ascii=False,
                ).encode("utf-8") + b"\n"
            )
            # iter2-P0-1: rebuild remainder using COMPLEMENT of consumed_set
            # (NOT a prefix slice). Empty lines are preserved as empty bytes
            # in body_lines and re-emitted with the newline separator below.
            remainder_lines = [
                f.body_lines[i] for i in range(total) if i not in consumed_set
            ]
            body_remainder = b"\n".join(remainder_lines)
            if body_remainder and not body_remainder.endswith(b"\n"):
                body_remainder += b"\n"
            fd = os.open(
                str(tmp_path),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC,
                0o600,
            )
            try:
                os.write(fd, header_line)
                if body_remainder:
                    os.write(fd, body_remainder)
                os.fsync(fd)
            finally:
                os.close(fd)
            # iter2-P1-3: dst is .draining.<new_epoch> — distinct from src.
            dst_path = _draining_path(_spool_path(f.pid), new_epoch)
            # Single atomic rename + unlink source. If rename fails, the
            # tmp file is cleaned up in the except branch.
            os.rename(str(tmp_path), str(dst_path))
            try:
                os.unlink(str(f.path))
            except OSError as e:  # pragma: no cover
                # Source gone (race / already cleaned); rename succeeded so
                # the remainder file is correctly in place.
                _breadcrumb(
                    f"phase5 src unlink after split failed: "
                    f"{type(e).__name__}: {e}"
                )
            stats.files_split_remainder += 1
        except OSError as e:
            _breadcrumb(f"phase5 split failed: {type(e).__name__}: {e}")
            try:
                if tmp_path.exists():
                    os.unlink(str(tmp_path))
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Journal post-drain compaction
# ---------------------------------------------------------------------------


def _journal_compact_drained(
    pid: int,
    drained_record_ids: Iterable[str],
    drain_epoch: str,
) -> None:
    """Append op=drained envelopes; rewrite journal dropping fully-completed triples.

    P1-3: emits op:"drained" envelopes with the actual record_id so
    session-start reconciliation can distinguish recovered from inflight.
    """
    drained_set = {r for r in drained_record_ids if isinstance(r, str) and r}
    if not drained_set:
        return
    # Flush any pending in-memory journal envelopes for this PID FIRST so
    # the compaction read sees a consistent on-disk view.
    _flush_journal_buffer(pid)
    journal = _journal_path(pid)
    if not journal.exists():
        return
    # 1) Append drained envelopes via the buffer (then flush)
    for rid in drained_set:
        _write_journal_envelope(
            pid, rid, "", -1, "", "drained", drain_epoch=drain_epoch,
        )
    _flush_journal_buffer(pid)
    # 2) Rewrite journal under per-PID journal flock dropping rows whose
    # record_id is in drained_set (begin/commit/drained triples collapse).
    try:
        with FileLock(_journal_flock_path(pid), timeout=SPOOL_LOCK_TIMEOUT):
            with journal.open("r", encoding="utf-8") as f:
                keep_lines: List[str] = []
                for raw in f:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    try:
                        env = json.loads(stripped)
                    except json.JSONDecodeError:
                        keep_lines.append(raw)
                        continue
                    if (isinstance(env, dict)
                            and env.get("record_id") in drained_set):
                        continue
                    keep_lines.append(raw)
            tmp = journal.with_name(journal.name + ".compact.tmp")
            with tmp.open("w", encoding="utf-8") as f:
                f.writelines(keep_lines)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp), str(journal))
    except FileLockTimeout:
        _breadcrumb(f"journal compact flock timeout pid={pid}")
    except OSError as e:
        _breadcrumb(f"journal compact failed: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# drain_now — orchestration
# ---------------------------------------------------------------------------


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
    """atexit hook — best-effort final drain. Swallow all errors.

    P1-2: also flushes the in-memory journal buffer for our PID so any
    begin/commit envelopes that hadn't hit the amortization threshold
    are durable before process exit.
    """
    try:
        drain_now(force=True)
    except Exception:
        pass
    try:
        _flush_journal_buffer(os.getpid())
    except Exception:
        pass


def _signal_drain_handler(signum: int, frame: Any) -> None:
    """SIGTERM/SIGINT — force-drain then re-raise to default handler.

    P1-1: if a writer is currently inside spool_append (holding the spool
    flock in our PID), bail without forcing a drain — the in-flight entry
    will be picked up by next-session reconciliation.

    P1-2: flushes the journal buffer for our PID so begin/commit envelopes
    survive signal-driven termination.

    P2-5: if the previous handler was signal.SIG_IGN, preserve it (the
    user explicitly ignored this signal; default termination would be a
    behavior change). atexit does NOT run after default signal termination
    so our drain call here IS the final flush opportunity for SIG_DFL paths.
    """
    if _IN_SPOOL_APPEND:
        # Writer in progress; bail rather than deadlock against ourself.
        _breadcrumb(f"signal {signum} arrived during spool_append; bail")
        return
    try:
        drain_now(force=True)
    except Exception:
        pass
    try:
        _flush_journal_buffer(os.getpid())
    except Exception:
        pass
    # Resolve the previous handler.
    if signum == signal.SIGTERM:
        prev = _PREV_SIGTERM_HANDLER
    elif signum == signal.SIGINT:
        prev = _PREV_SIGINT_HANDLER
    else:
        prev = signal.SIG_DFL

    # P2-5: distinguish SIG_IGN vs SIG_DFL vs callable.
    if prev is signal.SIG_IGN:
        # Restore IGN and do NOT re-raise — the user wanted this signal
        # ignored; honoring that is correctness, not failure.
        try:
            signal.signal(signum, signal.SIG_IGN)
        except (ValueError, OSError):  # pragma: no cover
            pass
        return
    if callable(prev):
        # Chain to user handler.
        try:
            signal.signal(signum, prev)
        except (ValueError, OSError):  # pragma: no cover
            pass
        try:
            prev(signum, frame)
        except Exception:  # pragma: no cover
            pass
        return
    # Default: restore SIG_DFL and re-raise. atexit does NOT run after
    # default-signal termination → the drain_now(force=True) above is the
    # final flush opportunity.
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
    except (ValueError, OSError) as e:
        # Signal handlers only work on main thread; in worker threads
        # signal.signal raises ValueError. Fail-open.
        _breadcrumb(f"SIGTERM install skipped: {type(e).__name__}: {e}")
    try:
        _PREV_SIGINT_HANDLER = signal.signal(
            signal.SIGINT, _signal_drain_handler,
        )
    except (ValueError, OSError) as e:
        _breadcrumb(f"SIGINT install skipped: {type(e).__name__}: {e}")
    _EXIT_HANDLER_INSTALLED = True


# ---------------------------------------------------------------------------
# Test helpers (NOT public API — prefixed _; harness uses these)
# ---------------------------------------------------------------------------


def _reset_for_test() -> None:
    """Clear all in-process spool state (caches + handler latch + buffer)."""
    global _EXIT_HANDLER_INSTALLED, _IN_FORENSIC_EMIT, _IN_SPOOL_APPEND
    _SPOOL_HEADER_CACHE.clear()
    _ORDINAL_COUNTER.clear()
    _JOURNAL_BUFFER.clear()
    _EXIT_HANDLER_INSTALLED = False
    _IN_FORENSIC_EMIT = False
    _IN_SPOOL_APPEND = False
