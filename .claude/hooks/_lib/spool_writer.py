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
K_MAX = 100
K_TAIL_WINDOW = 200
SPOOL_HEADER_VERSION = 1
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
_TEST_ORIGIN_SUFFIX_TOKEN = ".test-origin."
_LIVE_LOG_SNAPSHOT_VAR = "CEO_AUDIT_LIVE_LOG_PATH_SNAPSHOT"
_SPOOL_UUID_HEX_LEN = 16   # secrets.token_hex(8) -> 16 hex chars
_DRAIN_EPOCH_HEX_LEN = 8   # secrets.token_hex(4) -> 8 hex chars
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
    test_origin_quarantined: int = 0
    partial_lines_discarded: int = 0
    files_consumed_fully: int = 0
    files_split_remainder: int = 0
    in_recovery_mode: bool = False
    drain_epoch: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
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


def _project_dir_cache_key() -> Tuple[Optional[str], ...]:
    """Cache key for the declared environment and conditional cwd inputs.
    PLAN-182 W1 cure: the Wave-A key was (CEO_AUDIT_LOG_DIR, HOME) — a
    process that switched project mid-run (CLAUDE_PROJECT_DIR / cwd /
    CLAUDE_PROJECT_DIR_NATIVE changed) kept being served the PREVIOUS
    project's dir from cache, so the cross-project leak survived any
    resolver cure. cwd participates when none of the directory candidates
    is absolute. A lower-priority absolute candidate can still mask the
    cwd dependency of a relative override; rc.1 condition 24 requires an
    absolute CEO_AUDIT_LOG_DIR and records the remaining cache limitation.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    env_home = os.environ.get("HOME")
    env_native = os.environ.get("CLAUDE_PROJECT_DIR_NATIVE")
    env_proj = os.environ.get("CLAUDE_PROJECT_DIR")
    cwd: Optional[str] = None
    # rail r15 P2-3: o cwd entra na chave quando NENHUM override absoluto
    # decide o dir — inclui o caso de um override RELATIVO, que
    # `project_dir()` resolve CONTRA o cwd. Sem isso, um processo longo
    # que muda de cwd com CLAUDE_PROJECT_DIR relativo continuaria servindo
    # o dir do projeto anterior (e pularia a invalidacao dos caches).
    def _abs(v):
        return bool(v) and os.path.isabs(v)
    if not (_abs(env_dir) or _abs(env_native) or _abs(env_proj)):
        cwd = os.getcwd()
    return (env_dir, env_home, env_native, env_proj, cwd)


def _project_dir_from_env() -> Path:
    """Return the audit project dir (BYTE-IDENTICAL to audit_emit._audit_dir).
    P1-5: must mirror audit_emit._audit_dir() exactly — CEO_AUDIT_LOG_DIR
    precedence, then the SAME single resolver (_lib/runtime_paths,
    PLAN-182 W1) audit_emit delegates to. CEO_AUDIT_LOG_PATH is the FILE
    path, not the dir path, so we do NOT derive the dir from it
    (audit_emit doesn't either).
    PLAN-111 Wave A cache, PLAN-182 W1 key: single-slot, keyed on
    _project_dir_cache_key() (all resolver inputs). Cache HIT skips
    re-construction of Path object. Cache MISS replaces the slot
    atomically.
    Single-threaded contract: concurrent os.environ mutation = UB.
    """
    global _PROJECT_DIR_CACHE
    env_key = _project_dir_cache_key()
    cached = _PROJECT_DIR_CACHE
    if cached is not None and cached[0] == env_key:
        return cached[1]
    env_dir = env_key[0]
    if env_dir:
        p = Path(env_dir)
    else:
        p = _runtime_paths.runtime_state_dir()
    _PROJECT_DIR_CACHE = (env_key, p)
    return p


def _invalidate_per_pid_caches_on_project_switch(old_dir: Path) -> None:
    """Drop per-PID spool state when the resolved project changes.
    rail r13 P1-1 (cura) + rail r14 (cura da cura): o flush do buffer
    pendente e feito contra ``old_dir`` — o dir do projeto ANTERIOR, que
    o chamador ja tem em cache. A primeira versao chamava
    ``_flush_journal_buffer()``, que resolve o caminho por
    ``_state_dir()``: como o cache ainda nao tinha sido trocado, aquilo
    RE-ENTRAVA neste mesmo branch ate ``RecursionError`` e, pior,
    reescrevia o payload antigo sob o dir do projeto NOVO — a
    contaminacao cruzada que a invalidacao existe para impedir.
    Fail-open: qualquer erro no flush apenas descarta os caches.
    """
    pid = os.getpid()
    buf = _JOURNAL_BUFFER.get(pid)
    if buf:
        try:
            target = old_dir / "{0}.{1}.journal".format(_JOURNAL_PREFIX, pid)
            with target.open("ab") as fh:
                for line in buf:
                    fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
        except Exception:  # pragma: no cover — nunca bloqueia a troca
            pass
    _SPOOL_HEADER_CACHE.pop(pid, None)
    _ORDINAL_COUNTER.pop(pid, None)
    _JOURNAL_BUFFER.pop(pid, None)


# QDSAA-FUNCAO-LONGA: resolução segura combina isolamento de projeto, permissões e invalidação de cache.
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
    # PLAN-182 W1: key covers ALL resolver inputs (see
    # _project_dir_cache_key) — a mid-process project switch must not be
    # served the previous project's state dir.
    env_key = _project_dir_cache_key()
    cached = _STATE_DIR_CACHE
    if cached is not None and cached[0] == env_key:
        return cached[1]
    # rail r13 P1-1: os caches POR PID (header/ordinal/journal) nao sao
    # cobertos pela chave acima. Num processo longo A -> B -> A, o header
    # de B seria reusado em A (UUID errado no corpo => o drain estrito
    # QUARENTENA o spool de A) e o journal bufferizado poderia ir para o
    # projeto errado. Uma transicao de projeto invalida os tres.
    if cached is not None and cached[0] != env_key:
        # passa o dir ANTIGO (cached[1]) — nunca re-resolve aqui.
        _invalidate_per_pid_caches_on_project_switch(cached[1])
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
            if (mismatch_reason is not None
                    and not _stat_mod.S_ISLNK(st.st_mode)
                    and st.st_uid == os.getuid()):
                healed = False
                fd = None
                try:
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


def _log_family_dir() -> Path:
    """Dir the lock/errors sidecars must share with the LOG.
    PLAN-182 W1 rail r1 P1-2: mirrors audit_emit._log_family_dir()
    byte-for-byte — when CEO_AUDIT_LOG_PATH moves the log, EVERY writer
    of that log locks the moved parent (two writers on one HMAC log
    under different locks = interleaved appends).
    """
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env).resolve().parent
    return _project_dir_from_env()


def _canonical_log_lock() -> Path:
    """Mirror audit_emit._lock_path() — sibling .lock file."""
    env = os.environ.get("CEO_AUDIT_LOG_LOCK")
    if env:
        return Path(env)
    return _log_family_dir() / "audit-log.lock"
def _errors_path() -> Path:
    """Breadcrumb file for fail-open infra errors."""
    env = os.environ.get("CEO_AUDIT_LOG_ERR")
    if env:
        return Path(env)
    return _log_family_dir() / "audit-log.errors"


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
_EXIT_DEADLINE_MONOTONIC: Optional[float] = None
def set_exit_deadline(deadline_monotonic: Optional[float]) -> None:
    """Arm no-drain exit context; hook entrypoints own the monotonic deadline."""
    global _EXIT_DEADLINE_MONOTONIC
    if deadline_monotonic is None:
        _EXIT_DEADLINE_MONOTONIC = None
        return
    try:
        _EXIT_DEADLINE_MONOTONIC = float(deadline_monotonic)
    except (TypeError, ValueError):
        _EXIT_DEADLINE_MONOTONIC = None
        _breadcrumb("exit deadline ignored: invalid monotonic value")


def _exit_deadline_active() -> bool:
    """Whether this process is running under a hook-owned deadline."""
    return _EXIT_DEADLINE_MONOTONIC is not None or os.environ.get("CEO_HOOK_BOUNDED_EXIT") == "1"
def _record_exit_deadline_skip(source: str) -> None:
    _breadcrumb(f"exit_deadline_skip source={source}")
_SPOOL_HEADER_CACHE: Dict[int, Dict[str, Any]] = {}
_ORDINAL_COUNTER: Dict[int, int] = {}
_FORENSIC_EMIT: Optional[Callable[[str, Dict[str, Any]], None]] = None
_IN_FORENSIC_EMIT = False
_IN_SPOOL_APPEND = False
_LAST_APPEND_SUCCEEDED = True
def last_append_succeeded() -> bool:
    """Whether the last spool_append persisted durably."""
    return _LAST_APPEND_SUCCEEDED

# Per-PID journal buffer; flush at drain boundaries or every ten writes.
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

from _lib._spool_writer_parts import install as _install_parts

_install_parts(globals(), ("writer", "prepare", "drain", "lifecycle"))
