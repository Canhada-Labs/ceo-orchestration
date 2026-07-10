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

## PLAN-154 item 1 — opt-in metadata OBSERVE rail (A2/A3/A12)

An OPT-IN extension rides the existing ``record_post`` / ``sweep_orphans``
paths (ZERO new hook registrations — constraint 8/A3). When
``CEO_LEARNING_OBSERVE=1`` (and ``CEO_SOTA_DISABLE`` != ``"1"`` — master
precedence), each completed/orphaned tool call appends ONE row of allowlisted
metadata to a per-session append-only JSONL observation store next to the
per-session pairing state file
(``<audit_dir>/tool-lifecycle/<session>.observe.jsonl``, 0600).

- **A2 (metadata is normative, not prose).** The row schema is CLOSED and
  deny-by-default: :data:`OBSERVATION_SCHEMA_V1` enumerates every field —
  closed enums, booleans, and one bounded opaque hash ONLY. The writer
  (:func:`_append_observation`) builds the row FROM the allowlist (it never
  iterates caller input), re-coerces every value by closed-set membership,
  and drops anything else. No free-text field exists; adding one requires an
  ADR-160 amendment + a conscious re-pin of the frozen schema digest
  (:func:`observation_schema_digest`).
- **A12 (kill-switch story).** ``CEO_LEARNING_OBSERVE`` unset/empty →
  structurally OFF: the added code path is a single dict lookup and produces
  ZERO filesystem delta. Set to anything other than ``"1"``, or overridden by
  ``CEO_SOTA_DISABLE=1``, → explicitly OFF: a single
  ``learning_rail_disabled`` breadcrumb per session (marker-file deduped,
  wired to Wave-E liveness) and no store writes.
- **MF-SEC-5 preserved.** The observe rail hangs ONLY off the Post/sweep
  side; :func:`record_pre` remains byte-for-byte audit-silent (its stamp
  already feeds the row's ``paired`` bit and pairing data).
- The store PERSISTS across sessions (it is the PLAN-154 item-2 distiller's
  v1 read surface; ``cleanup_session`` deletes the pairing state + the
  disabled-marker but NEVER the observation store). Retention/pruning is the
  distiller pipeline's concern.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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
#
# PLAN-153 wave-backlog (Anthropic ADOPT, Claude Code 2.1.x): ``TodoWrite``
# is deprecated upstream in favor of the four Task tools —
# ``TaskCreate`` / ``TaskUpdate`` / ``TaskGet`` / ``TaskList``. All four get
# FIRST-CLASS enum members (they are the dominant plan-tracking surface going
# forward; collapsing them to ``"other"`` would blind the telemetry).
# ``TodoWrite`` STAYS for back-compat (older harnesses still emit it) —
# ADDITIVE-only per SPEC/v1 rules. COUPLING (3-way pin): this set must stay
# in sync with ``_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM`` in ``_lib/audit_emit.py``
# (which re-coerces out-of-enum values to ``"other"`` at BOTH emit paths —
# the typed emitter AND the emit_generic scrub branch) and with the closed
# enum documented on the ``tool_call_lifecycle_recorded`` row of
# ``SPEC/v1/audit-log.schema.md`` (v2.48 amendment). The pin-sync is
# regression-guarded by ``hooks/tests/test_tool_lifecycle_enum_pin_sync.py``.
_RECOGNIZED_TOOL_NAMES = frozenset({
    "Agent",
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskGet",
    "TaskList",
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
# PLAN-154 item 1 — observe-rail closed schema + kill-switch gate (A2/A12)
# ---------------------------------------------------------------------------

# Opt-in ENABLE flag (A12): unset/empty = structurally OFF (zero filesystem
# delta — `cost_envelope.py` posture); ONLY the literal "1" enables; any other
# set value = explicitly OFF (recorded operator choice → one breadcrumb per
# session). CEO_SOTA_DISABLE=1 takes master precedence over an enabled flag.
_OBSERVE_ENV = "CEO_LEARNING_OBSERVE"
_SOTA_DISABLE_ENV = "CEO_SOTA_DISABLE"

# Frozen observation schema version. Bumping it (or touching ANY field below)
# changes observation_schema_digest() and REDs the pinned CI fixture in
# hooks/tests/test_tool_lifecycle_observe.py until consciously re-pinned in
# review (A2 CI assertion a).
OBSERVATION_SCHEMA_VERSION = 1

# Defense-in-depth per-row byte ceiling (A18). With the closed schema a row is
# ~120 bytes; anything larger is structurally impossible unless the schema is
# widened, in which case this ceiling is re-reviewed with it.
_MAX_OBSERVATION_LINE_BYTES = 512

# Bounded opaque ID: sha256(tool_use_id) truncated to 16 hex chars. The raw
# tool_use_id (attacker-influenceable, unbounded) NEVER enters the store.
_TOOL_USE_HASH_HEX_LEN = 16
_TOOL_USE_HASH_RE = re.compile(r"^[0-9a-f]{0,16}$")

# THE deny-by-default capture-time field allowlist (A2). Every observation row
# carries EXACTLY these fields — closed enums, booleans, and one bounded
# opaque hash. There is NO free-text field; adding any field (or widening any
# enum) requires an ADR-160 amendment and re-pins the frozen schema digest.
# NOTE the deliberate coupling: widening _RECOGNIZED_TOOL_NAMES (already a
# 3-way pin with audit_emit + SPEC) also changes this digest — a conscious
# review touch, by design.
OBSERVATION_SCHEMA_V1: Tuple[Tuple[str, str], ...] = (
    ("v", "int_const:1"),
    ("tool_name_enum", "enum:" + ",".join(
        sorted(_RECOGNIZED_TOOL_NAMES | {"mcp_other", "other"}))),
    ("duration_bucket", "enum:" + ",".join(DURATION_BUCKETS)),
    ("success", "bool"),
    ("orphan", "bool"),
    ("paired", "bool"),
    ("tool_use_hash", "hex:0-16"),
)


def observation_schema_digest() -> str:
    """Return the sha256 hex digest of the canonical schema serialization.

    Pinned by the frozen schema-hash CI fixture (A2 assertion a): ANY field
    addition/removal/reorder, type change, or enum widening changes this
    digest and REDs the pin until consciously updated in review.
    """
    payload = json.dumps(
        [list(pair) for pair in OBSERVATION_SCHEMA_V1],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _observe_state() -> Tuple[str, str]:
    """Resolve the observe-rail gate → ``(state, switch)``.

    ``state`` ∈ {``"on"``, ``"off_unset"``, ``"off_explicit"``}; ``switch`` is
    the env var that recorded the explicit-off choice (breadcrumb payload),
    else ``""``. Read per-invocation from ``os.environ`` (hooks are
    per-invocation processes — matches this module's existing env style).
    """
    raw = (os.environ.get(_OBSERVE_ENV) or "").strip()
    if not raw:
        return ("off_unset", "")
    if (os.environ.get(_SOTA_DISABLE_ENV) or "").strip() == "1":
        # Master precedence (A12): SOTA kill beats an enabled opt-in.
        return ("off_explicit", _SOTA_DISABLE_ENV)
    if raw == "1":
        return ("on", "")
    # Set to any non-"1" value = recorded operator choice to keep it off.
    return ("off_explicit", _OBSERVE_ENV)


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


def observation_store_path(session_id: str, audit_dir: Optional[Path] = None) -> Path:
    """Return the per-session observation store path (PLAN-154 item 1).

    ``<audit_dir>/tool-lifecycle/<session>.observe.jsonl`` — next to the
    pairing state file, 0600, append-only JSONL. Public: this is the item-2
    distiller's v1 read surface. The file PERSISTS across sessions
    (``cleanup_session`` never deletes it).
    """
    base = audit_dir if audit_dir is not None else _audit_dir()
    return base / "tool-lifecycle" / (
        _safe_session_component(session_id) + ".observe.jsonl"
    )


def _observe_disabled_marker_path(
    session_id: str, audit_dir: Optional[Path] = None
) -> Path:
    """Per-session once-guard marker for the disabled-rail breadcrumb (A12)."""
    base = audit_dir if audit_dir is not None else _audit_dir()
    return base / "tool-lifecycle" / (
        _safe_session_component(session_id) + ".observe-disabled"
    )


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
# PLAN-154 item 1 — observe-rail writer (post/sweep side ONLY; MF-SEC-5 keeps
# record_pre audit-silent and untouched)
# ---------------------------------------------------------------------------


def _tool_use_hash(tool_use_id: str) -> str:
    """Bounded opaque ID: sha256(tool_use_id)[:16]; empty in → empty out."""
    if not tool_use_id:
        return ""
    try:
        return hashlib.sha256(
            tool_use_id.encode("utf-8", "replace")
        ).hexdigest()[:_TOOL_USE_HASH_HEX_LEN]
    except Exception:
        return ""


def _coerce_observation(fields: Dict[str, Any]) -> Dict[str, Any]:
    """Closed-type gate (A2 CI assertion b) — deny-by-default coercion.

    Builds the row FROM :data:`OBSERVATION_SCHEMA_V1`'s field list (never by
    iterating caller input, so un-allowlisted keys can never pass), and
    re-coerces every value by closed-set membership:

    * ``tool_name_enum``  → :func:`to_tool_name_enum` (out-of-enum → "other")
    * ``duration_bucket`` → membership in :data:`DURATION_BUCKETS`, else floor
    * ``success``/``orphan``/``paired`` → ``bool(...)``
    * ``tool_use_hash``   → must match ``^[0-9a-f]{0,16}$``, else ``""``

    No free-form string can survive: every string field is either
    enum-membership-checked or regex-bounded lowercase hex.
    """
    out: Dict[str, Any] = {}
    out["v"] = OBSERVATION_SCHEMA_VERSION
    out["tool_name_enum"] = to_tool_name_enum(fields.get("tool_name_enum"))
    bucket = fields.get("duration_bucket")
    out["duration_bucket"] = (
        bucket if bucket in DURATION_BUCKETS else DURATION_BUCKETS[0]
    )
    out["success"] = bool(fields.get("success"))
    out["orphan"] = bool(fields.get("orphan"))
    out["paired"] = bool(fields.get("paired"))
    tuh = fields.get("tool_use_hash")
    if not (isinstance(tuh, str) and _TOOL_USE_HASH_RE.match(tuh)):
        tuh = ""
    out["tool_use_hash"] = tuh
    return out


def _append_observation(
    session_id: str,
    fields: Dict[str, Any],
    audit_dir: Optional[Path] = None,
) -> bool:
    """Coerce + append ONE observation row. Fail-open; no lock; no subprocess.

    Hot-path shape: a single ``open(O_APPEND)`` + one small ``write`` + close
    (rows are ~120 bytes ≪ PIPE_BUF, so concurrent appenders interleave at
    line granularity). The per-row byte ceiling is defense-in-depth (A18).
    Returns True iff a row was written (telemetry only — callers ignore it).
    """
    try:
        row = _coerce_observation(fields if isinstance(fields, dict) else {})
        data = (
            json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n"
        ).encode("utf-8")
        if len(data) > _MAX_OBSERVATION_LINE_BYTES:
            return False
        path = observation_store_path(session_id, audit_dir)
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError:
            pass
        fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        try:
            os.write(fd, data)
        finally:
            os.close(fd)
        return True
    except Exception:
        # Fail-open — a telemetry write failure must never block the tool.
        return False


def _emit_observe_disabled_breadcrumb(session_id: str, switch: str) -> None:
    """Emit the once-per-session ``learning_rail_disabled`` breadcrumb (A12).

    Typed emitter preferred via the house hasattr/getattr guard (pre-
    registration no-op); falls back to ``emit_generic`` — which is itself a
    silent no-op breadcrumb until the integrator lands the 4-file action
    registration. Fail-OPEN on every path.
    """
    try:
        from _lib import audit_emit  # noqa: E402
    except Exception:
        return
    project = os.environ.get("CLAUDE_PROJECT_DIR") or ""
    try:
        emit = getattr(audit_emit, "emit_learning_rail_disabled", None)
        if emit is not None:
            emit(
                rail="observe",
                switch=switch,
                session_id=session_id,
                project=project,
            )
            return
        emit_generic = getattr(audit_emit, "emit_generic", None)
        if emit_generic is not None:
            emit_generic(
                "learning_rail_disabled",
                rail="observe",
                switch=switch,
                session_id=session_id,
                project=project,
            )
    except Exception:
        return


def _observe_disabled_once(
    session_id: str, switch: str, audit_dir: Optional[Path] = None
) -> None:
    """Record the explicit-off choice ≤1× per session (marker-file dedupe).

    Marker-first ordering guarantees the ≤1 contract even across concurrent
    hook invocations (``O_EXCL`` is the race arbiter); a crash between marker
    and emit loses the breadcrumb — acceptable, fail-open. Only reached when
    the operator EXPLICITLY disabled the rail (the unset path returns before
    any filesystem touch — zero-delta negative control, A2/A12).
    """
    try:
        marker = _observe_disabled_marker_path(session_id, audit_dir)
        try:
            marker.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError:
            pass
        try:
            fd = os.open(
                str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
        except FileExistsError:
            return  # already recorded this session
        os.close(fd)
        _emit_observe_disabled_breadcrumb(session_id, switch)
    except Exception:
        return


def _observe_post(
    *,
    session_id: str,
    raw_tool_name: str,
    duration_ms: Optional[int],
    success: bool,
    orphan: bool,
    paired: bool,
    tool_use_id: str,
    audit_dir: Optional[Path] = None,
) -> None:
    """Observe-rail entry for the Post/sweep side. Fail-open, gate-first.

    Callers guard with the cheap inline ``os.environ.get(_OBSERVE_ENV)``
    lookup, so when the opt-in is unset this function is never even called.
    """
    try:
        state, switch = _observe_state()
        if state == "off_unset":
            return  # structurally OFF — zero filesystem delta
        if state == "off_explicit":
            _observe_disabled_once(session_id, switch, audit_dir)
            return
        _append_observation(
            session_id,
            {
                "tool_name_enum": to_tool_name_enum(raw_tool_name),
                "duration_bucket": to_duration_bucket(duration_ms),
                "success": success,
                "orphan": orphan,
                "paired": paired,
                "tool_use_hash": _tool_use_hash(tool_use_id),
            },
            audit_dir,
        )
    except Exception:
        return


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
        # PLAN-154 item 1 — opt-in observe rail (A2/A3/A12). The inline env
        # lookup is the ENTIRE added cost when the opt-in is unset (a single
        # dict get — never a call, never a filesystem touch).
        if os.environ.get(_OBSERVE_ENV):
            _observe_post(
                session_id=session_id,
                raw_tool_name=raw_tool_name,
                duration_ms=(
                    duration_ms if isinstance(duration_ms, int) else None
                ),
                success=(not failure),
                orphan=False,
                paired=bool(pre_tool_name),
                tool_use_id=tool_use_id,
                audit_dir=audit_dir,
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
            orphans: List[Tuple[str, Dict[str, Any]]] = []
            for tool_use_id, rec in records.items():
                t_start = rec.get("t_start_s")
                age = None
                if isinstance(t_start, (int, float)):
                    age = now - float(t_start)
                if age is not None and age >= timeout_s:
                    orphans.append((tool_use_id, rec))
                else:
                    survivors[tool_use_id] = rec
            if orphans:
                _save_records(record_path, survivors)
        # Emit OUTSIDE the lock hold (keep the lock O(1) / lock-cheap).
        for tool_use_id, rec in orphans:
            _emit_lifecycle(
                session_id=session_id,
                raw_tool_name=str(rec.get("tool_name", "") or ""),
                duration_ms=None,  # never knew when it finished
                success=False,
                orphan=True,
            )
            # PLAN-154 item 1 — observe rail mirrors the orphan signal (same
            # cheap inline gate as record_post; a stamped record implies the
            # Pre side ran, so paired=True).
            if os.environ.get(_OBSERVE_ENV):
                _observe_post(
                    session_id=session_id,
                    raw_tool_name=str(rec.get("tool_name", "") or ""),
                    duration_ms=None,
                    success=False,
                    orphan=True,
                    paired=True,
                    tool_use_id=tool_use_id,
                    audit_dir=audit_dir,
                )
            emitted += 1
    except Exception:
        return emitted
    return emitted


def cleanup_session(session_id: str, audit_dir: Optional[Path] = None) -> None:
    """Delete the per-session record file + lock at SessionEnd. Fail-open.

    MF-PERF-2 — bounds the file lifecycle to a single session. PLAN-154: the
    per-session disabled-marker is session-scoped junk and is deleted too; the
    OBSERVATION STORE (``*.observe.jsonl``) is deliberately NOT deleted — it
    persists as the item-2 distiller's read surface.
    """
    try:
        record_path = _record_path(session_id, audit_dir)
        for p in (record_path, _lock_path(record_path),
                  record_path.with_suffix(record_path.suffix + ".tmp"),
                  _observe_disabled_marker_path(session_id, audit_dir)):
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
