"""PLAN-125 WS-1 — per-tool-call lifecycle telemetry (BUILD).

Pairs a tool call's ``PreToolUse`` stamp with its ``PostToolUse`` /
``PostToolUseFailure`` completion by the per-call ``tool_use_id``, then emits
a single deny-by-default audit action ``tool_call_lifecycle_recorded`` carrying
ONLY four coarse fields:

  * ``tool_name_enum``  — a CLOSED enum (``mcp__*`` → ``"mcp_other"``; unknown
    → ``"other"``). The raw ``mcp__<server>__<tool>`` string MUST NEVER reach
    the wire (MF-SEC-1).
  * ``duration_bucket`` — a coarse enum bucket; the raw ``duration_ms`` integer
    is NEVER emitted (timing side-channel — MF-SEC-3).
  * ``success``         — bool (``PostToolUseFailure`` → ``False``).
  * ``orphan``          — bool (sweeper sets ``True`` when no Post/Failure
    arrives within ``T=30s`` — MF-PERF-3).

## Design contract (the binding must-fixes)

- **MF-SEC-5 (hard KILL).** :func:`record_pre` writes ONLY to a dedicated 0600
  per-session file under the process's isolated audit dir — it NEVER calls
  ``audit_emit``, so the PreToolUse hot path emits NO audit-chain event. The
  PostToolUse emit (:func:`record_post`) is fail-OPEN: a chain-write failure
  NEVER blocks the tool.
- **MF-PERF-1.** No new subprocess beyond the one cheap PreToolUse write; the
  Post emit is co-located in an already-running PostToolUse hook.
- **MF-PERF-2.** One file per ``session_id``, evicted on completion and deleted
  at SessionEnd → ``n_entries`` ≈ concurrent in-flight calls (≈1 steady state).
- **MF-PERF-3 / MF-QA-B.** Orphan timeout ``T=30s`` (configurable) with an
  INJECTABLE clock (``now_fn``) — tests never ``time.sleep``.
- **Not ``state_store``** — that is plan-scoped, emits ``state_store_*`` per op
  (hot-path audit noise), and redacts strings. Wrong tool for an opaque
  ``tool_use_id`` + coarse enum.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
    _FILELOCK_AVAILABLE = True
except Exception:  # pragma: no cover — fail-open if _lib unavailable
    FileLock = None  # type: ignore[assignment]
    FileLockTimeout = Exception  # type: ignore[assignment]
    _FILELOCK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Closed enums (MF-SEC-1 / MF-SEC-3)
# ---------------------------------------------------------------------------

# Recognized standard Claude Code tool names. The live framework spawns
# sub-agents through the ``Agent`` token (every spawn-governance matcher is
# ``matcher:"Agent"``) while newer Claude-Code docs name the spawn tool
# ``Task`` — BOTH are listed so a spawn maps to a real bucket rather than
# collapsing to ``"other"``. The two synthetic values produced by the mapper
# (``"mcp_other"`` / ``"other"``) are NOT members of this set, so an attacker
# cannot smuggle a literal ``"mcp_other"`` tool name through a different path:
# the mapper always recomputes from the raw name.
_RECOGNIZED_TOOL_NAMES = frozenset({
    "Agent",
    "Task",
    "Bash",
    "Edit",
    "MultiEdit",
    "Write",
    "Read",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "TodoWrite",
})

# Closed set of duration buckets — the ONLY duration representation that may
# reach the wire (MF-SEC-3). The raw duration_ms integer is forbidden.
DURATION_BUCKETS = (
    "lt_100ms",
    "b_100ms_1s",
    "b_1_10s",
    "b_10_60s",
    "gt_60s",
)

# Orphan timeout (MF-PERF-3). Configurable via the env override; falls back to
# the 30s default. A tool that ran longer than this with no Post/Failure is
# treated as orphaned (agent killed / hung) by the bounded sweeper.
DEFAULT_ORPHAN_TIMEOUT_S = 30.0
_ORPHAN_TIMEOUT_ENV = "CEO_TOOL_LIFECYCLE_ORPHAN_TIMEOUT_S"


def orphan_timeout_s() -> float:
    """Return the configured orphan timeout in seconds (default 30s)."""
    raw = os.environ.get(_ORPHAN_TIMEOUT_ENV, "").strip()
    if raw:
        try:
            val = float(raw)
            if val > 0:
                return val
        except (ValueError, TypeError):
            pass
    return DEFAULT_ORPHAN_TIMEOUT_S


def to_tool_name_enum(raw: Any) -> str:
    """Map a raw tool name to the CLOSED ``tool_name_enum`` (MF-SEC-1).

    ``mcp__*`` → ``"mcp_other"`` (the raw ``mcp__<server>__<tool>`` string is
    NEVER returned); a recognized standard tool → itself; anything else →
    ``"other"``. Non-str / empty → ``"other"``.
    """
    if not isinstance(raw, str) or not raw:
        return "other"
    # Idempotent: the two synthetic values pass through unchanged so re-mapping
    # an already-bucketed name (e.g. the enum stored in the per-session record
    # file) does NOT collapse "mcp_other" → "other".
    if raw in ("mcp_other", "other"):
        return raw
    if raw.startswith("mcp__"):
        return "mcp_other"
    return raw if raw in _RECOGNIZED_TOOL_NAMES else "other"


def to_duration_bucket(duration_ms: Optional[int]) -> str:
    """Map a native ``duration_ms`` to the CLOSED ``duration_bucket`` (MF-SEC-3).

    ``None`` (missing-Pre / absent) → ``"lt_100ms"`` (the conservative
    floor bucket — the absence of a measured duration must NOT widen the
    closed enum nor leak a raw value). Callers that need to distinguish the
    absent case do so on the upstream ``duration_ms is None`` BEFORE bucketing.
    """
    if duration_ms is None:
        return "lt_100ms"
    try:
        d = int(duration_ms)
    except (ValueError, TypeError):
        return "lt_100ms"
    if d < 100:
        return "lt_100ms"
    if d < 1000:
        return "b_100ms_1s"
    if d < 10000:
        return "b_1_10s"
    if d < 60000:
        return "b_10_60s"
    return "gt_60s"


# ---------------------------------------------------------------------------
# Per-session record file (NOT state_store) — MF-PERF-2 / MF-SEC-5
# ---------------------------------------------------------------------------


def _audit_dir() -> Path:
    """Return the process's isolated audit dir (matches audit_emit/audit_log).

    Swarm children inherit a per-slot ``CEO_AUDIT_LOG_DIR`` via
    ``_child_isolation.child_audit_env``, so their record file is automatically
    distinct — no extra work here.
    """
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _safe_session_component(session_id: str) -> str:
    """Sanitize a session_id into a single safe path component.

    Defends against ``../`` / absolute-path traversal in an
    attacker-influenceable id. Keep alnum + dash/dot/underscore; collapse
    everything else to ``_``. Empty → ``_nosession``.
    """
    sid = (session_id or "").strip()
    if not sid:
        return "_nosession"
    out = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in sid)
    # Reject pure-dot components (``.`` / ``..``) defensively.
    if set(out) <= {"."}:
        return "_nosession"
    return out[:200]


def _record_path(session_id: str, audit_dir: Optional[Path] = None) -> Path:
    """Return ``<audit_dir>/tool-lifecycle/<session_id>.json``."""
    base = audit_dir if audit_dir is not None else _audit_dir()
    return base / "tool-lifecycle" / (_safe_session_component(session_id) + ".json")


def _lock_path(record_path: Path) -> Path:
    return record_path.with_suffix(record_path.suffix + ".lock")


def _load_records(record_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load the per-session record map. Fail-open empty on any error.

    Shape: ``{tool_use_id: {"tool_name": str, "t_start_s": float}}``.
    """
    if not record_path.is_file():
        return {}
    try:
        with record_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    recs = data.get("records")
    if not isinstance(recs, dict):
        return {}
    # Defensive shape filter — only keep dict values.
    return {k: v for k, v in recs.items() if isinstance(v, dict)}


def _save_records(record_path: Path, records: Dict[str, Dict[str, Any]]) -> None:
    """Write the record map atomically with 0600. Fail-open on any error."""
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        pass
    tmp = record_path.with_suffix(record_path.suffix + ".tmp")
    try:
        # 0600 owner-only — mirrors spool_writer / filelock create idiom.
        fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"records": records}, fh, ensure_ascii=False)
        finally:
            pass
        os.replace(str(tmp), str(record_path))
        try:
            os.chmod(record_path, 0o600)
        except OSError:
            pass
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return


class _MaybeLock:
    """Context manager that acquires the FileLock when available, else no-op.

    Lock hold is O(1) (a single read-modify-write of a tiny JSON file —
    MF-SEC-5 "lock-cheap"). On lock unavailability / timeout we proceed
    best-effort: the worst case is a benign last-writer-wins on the record
    file, never a blocked tool.
    """

    def __init__(self, record_path: Path, timeout: float = 0.2) -> None:
        self._lock = None
        if _FILELOCK_AVAILABLE and FileLock is not None:
            try:
                self._lock = FileLock(
                    _lock_path(record_path), timeout=timeout, poll_interval=0.02
                )
            except Exception:
                self._lock = None

    def __enter__(self) -> "_MaybeLock":
        if self._lock is not None:
            try:
                self._lock.acquire()
            except Exception:
                self._lock = None  # proceed without the lock (best-effort)
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._lock is not None:
            try:
                self._lock.release()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def record_pre(
    event: Any,
    *,
    now_fn: Callable[[], float] = time.time,
    audit_dir: Optional[Path] = None,
) -> None:
    """PreToolUse stamp — write ``{tool_use_id, tool_name, t_start_s}``.

    MF-SEC-5 (hard KILL): this NEVER calls ``audit_emit`` — it only writes the
    dedicated per-session record file. O(1), lock-cheap. Fail-open: any error
    is swallowed (the tool is NEVER blocked by a telemetry write).

    ``event`` is a NormalizedEvent-like object exposing ``session_id``,
    ``tool_use_id`` and ``tool_name``. A missing ``tool_use_id`` is a no-op
    (nothing to pair later).
    """
    try:
        tool_use_id = getattr(event, "tool_use_id", "") or ""
        if not tool_use_id:
            return  # no pairing key → nothing to stamp
        session_id = getattr(event, "session_id", "") or ""
        tool_name = getattr(event, "tool_name", "") or ""
        record_path = _record_path(session_id, audit_dir)
        with _MaybeLock(record_path):
            records = _load_records(record_path)
            records[tool_use_id] = {
                # Store the CLOSED enum, never the raw tool name — so even this
                # transient 0600 off-wire file never holds a raw mcp__* string
                # (defense-in-depth; Codex pair-rail P2). to_tool_name_enum is
                # idempotent on the synthetic values, so record_post re-mapping
                # is a no-op.
                "tool_name": to_tool_name_enum(tool_name),
                "t_start_s": float(now_fn()),
            }
            _save_records(record_path, records)
    except Exception:
        # Fail-open — a stamp failure must never block the tool (MF-SEC-5).
        return


def record_post(
    event: Any,
    *,
    failure: bool,
    audit_dir: Optional[Path] = None,
) -> None:
    """PostToolUse / PostToolUseFailure — pair, bucket, emit, evict.

    Looks up the Pre record by ``tool_use_id``, reads the NATIVE
    ``event.duration_ms`` (not a self-measured value), buckets it, sets
    ``success = not failure``, emits ``tool_call_lifecycle_recorded`` via the
    typed scrub-branch emitter, and evicts the record.

    Fail-OPEN (MF-SEC-5): an emit / chain-write failure NEVER raises. A
    missing Pre record is tolerated — the duration is then treated as absent
    (bucket floor) and the recognized tool name is taken from the Post event.
    """
    try:
        tool_use_id = getattr(event, "tool_use_id", "") or ""
        session_id = getattr(event, "session_id", "") or ""
        post_tool_name = getattr(event, "tool_name", "") or ""
        duration_ms = getattr(event, "duration_ms", None)

        pre_tool_name = ""
        if tool_use_id:
            record_path = _record_path(session_id, audit_dir)
            with _MaybeLock(record_path):
                records = _load_records(record_path)
                rec = records.pop(tool_use_id, None)
                if rec is not None:
                    pre_tool_name = str(rec.get("tool_name", "") or "")
                    _save_records(record_path, records)

        # Prefer the Pre-stamped tool name (authoritative — captured at
        # call time); fall back to the Post event's tool name.
        raw_tool_name = pre_tool_name or post_tool_name
        _emit_lifecycle(
            session_id=session_id,
            raw_tool_name=raw_tool_name,
            duration_ms=duration_ms if isinstance(duration_ms, int) else None,
            success=(not failure),
            orphan=False,
        )
    except Exception:
        # Fail-open — never block the tool on a telemetry emit failure.
        return


def sweep_orphans(
    session_id: str,
    audit_dir: Optional[Path] = None,
    *,
    now_fn: Callable[[], float] = time.time,
    timeout_s: Optional[float] = None,
) -> int:
    """Flag + emit + evict records with no Post/Failure after ``timeout_s``.

    Returns the number of orphan records emitted. Bounded by construction:
    ``n_entries`` ≈ concurrent in-flight calls (MF-PERF-2). The clock is
    INJECTABLE (``now_fn``) so tests never ``time.sleep`` (MF-QA-B). Fail-open.
    """
    if timeout_s is None:
        timeout_s = orphan_timeout_s()
    emitted = 0
    try:
        record_path = _record_path(session_id, audit_dir)
        with _MaybeLock(record_path):
            records = _load_records(record_path)
            if not records:
                return 0
            now = float(now_fn())
            survivors: Dict[str, Dict[str, Any]] = {}
            orphans: List[Dict[str, Any]] = []
            for tool_use_id, rec in records.items():
                t_start = rec.get("t_start_s")
                age = None
                if isinstance(t_start, (int, float)):
                    age = now - float(t_start)
                if age is not None and age >= timeout_s:
                    orphans.append(rec)
                else:
                    survivors[tool_use_id] = rec
            if orphans:
                _save_records(record_path, survivors)
        # Emit OUTSIDE the lock hold (keep the lock O(1) / lock-cheap).
        for rec in orphans:
            _emit_lifecycle(
                session_id=session_id,
                raw_tool_name=str(rec.get("tool_name", "") or ""),
                duration_ms=None,  # never knew when it finished
                success=False,
                orphan=True,
            )
            emitted += 1
    except Exception:
        return emitted
    return emitted


def cleanup_session(session_id: str, audit_dir: Optional[Path] = None) -> None:
    """Delete the per-session record file + lock at SessionEnd. Fail-open.

    MF-PERF-2 — bounds the file lifecycle to a single session.
    """
    try:
        record_path = _record_path(session_id, audit_dir)
        for p in (record_path, _lock_path(record_path),
                  record_path.with_suffix(record_path.suffix + ".tmp")):
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
    except Exception:
        return


# ---------------------------------------------------------------------------
# Emit (typed scrub-branch path — MF-SEC-2)
# ---------------------------------------------------------------------------


def _emit_lifecycle(
    *,
    session_id: str,
    raw_tool_name: str,
    duration_ms: Optional[int],
    success: bool,
    orphan: bool,
) -> None:
    """Compute the 4 closed fields + emit via the typed scrub-branch emitter.

    Fail-OPEN: import / emit failure NEVER raises (MF-SEC-5).
    """
    try:
        from _lib import audit_emit  # noqa: E402
    except Exception:
        return
    emit = getattr(audit_emit, "emit_tool_call_lifecycle_recorded", None)
    if emit is None:
        return
    try:
        emit(
            session_id=session_id,
            tool_name_enum=to_tool_name_enum(raw_tool_name),
            duration_bucket=to_duration_bucket(duration_ms),
            success=bool(success),
            orphan=bool(orphan),
            project=os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:
        return
