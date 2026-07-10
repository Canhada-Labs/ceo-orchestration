"""Advisory-output dampening with ordinal — PLAN-154 item 5 (A10 contract).

Condenses REPEATED human-facing ADVISORY prose so a session is not flooded
with byte-identical advisory lines, while guaranteeing that no blocking
guard ever loses legibility.

## The A10 contract (binding, PLAN-154 constraint 4)

1. **Dampening keys on a schema DECISION field, never a text heuristic.**
   ``dampen(...)`` takes an explicit ``decision`` argument; only the closed
   value ``"advisory"`` is dampenable. ``"deny"`` / ``"block"`` — and any
   UNRECOGNIZED value, fail-closed toward legibility — are returned
   verbatim, untouched, uncounted.
2. **A blocking reason is byte-identical at N=1 vs N=100.** The exempt
   path returns the input ``text`` object unchanged and performs no state
   I/O at all (CI positive control lives in
   ``tests/test_advisory_dampen.py``).
3. **A condensed advisory ALWAYS retains {advisory ID, ordinal count,
   pointer-to-full-text}.** See :func:`_condense`.
4. **Counters are session-scoped** in a per-session 0600 JSON state file
   (the ``tool_lifecycle.py`` per-session record pattern: atomic replace,
   best-effort lock, traversal-safe session component), OFF the audit hot
   path — state lives under ``<audit_dir>/advisory-dampen/``, never inside
   the HMAC chain.
5. **<= 1 condensation audit event per advisory ID per session** — the
   first condensation of an ID emits ``advisory_dampened`` (a NEW action;
   until the integrator lands the 4-file registration,
   ``audit_emit.emit_generic`` treats it as a breadcrumbed no-op — the
   sanctioned pre-registration posture). Emit is fail-open.

## Dampenable channel — EXEMPT BY NAME (ADR-160 enumeration)

The ONLY dampenable channel is human-facing PROSE (v1: the ``stderr_prose``
channel). The following are EXEMPT BY NAME and must never be routed
through :func:`dampen`:

  * structured events (any machine-parsed hook output, decision JSON),
  * audit emissions (everything written to the HMAC audit chain),
  * ``additionalContext`` (model-facing context injection),
  * ALL block reasons / deny reasons (any text attached to a blocking
    decision) — these are additionally protected by contract point 1:
    ``decision="block"`` / ``decision="deny"`` input is returned verbatim.

## Fail posture

INFRASTRUCTURE fail-open toward FULL TEXT: any state-file / lock / clock /
emit failure returns the undampened input (legibility is never lost to a
bug). There is no fail-closed direction here by design — this module never
gates anything.

## Kill switches (A12)

  * ``CEO_ADVISORY_DAMPEN=0`` — emergency off (full text always; counters
    untouched). Default unset = dampening enabled (display-only rail).
  * ``CEO_SOTA_DISABLE=1``    — master kill, same effect (documented
    precedence: master kill wins over everything).

Both are read from the ``_lib.trusted_env`` import-time snapshot when
available (live ``os.environ`` fallback if the snapshot module is
unimportable — this rail is display-only, not a security gate).

## Clock seam (A9)

Every time-consuming function takes an injectable ``now_fn`` defaulting to
the wall clock (``time.time``). Timestamps are used only for first-seen
bookkeeping, never for policy.

Stdlib-only. Python >= 3.9. No new hook registrations (this is a library
consumed by already-registered hooks; v1 wired consumer: the fact-gate
shadow advisory in ``check_bash_safety.py``, PLAN-154 item 6).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# ---------------------------------------------------------------------------
# Closed enums / bounds
# ---------------------------------------------------------------------------

#: The ONLY decision value that may be condensed (A10 point 1).
DAMPENABLE_DECISIONS = frozenset({"advisory"})

#: Explicitly exempt decision values (documented; any OTHER unknown value
#: is treated identically — exempt, fail-closed toward legibility).
EXEMPT_DECISIONS = frozenset({"deny", "block"})

#: v1 dampenable channel enum (single value; audit field ``channel``).
CHANNEL_STDERR_PROSE = "stderr_prose"

_DAMPEN_KILL_VAR = "CEO_ADVISORY_DAMPEN"
_MASTER_KILL_VAR = "CEO_SOTA_DISABLE"

_STATE_SUBDIR = "advisory-dampen"
_MAX_TRACKED_IDS = 256          # per-session advisory-ID bound
_ID_MAX_LEN = 64                # bounded opaque ID (A2 posture)
_POINTER_PREVIEW_CHARS = 120    # first-line preview inside the condensed form
_LOCK_TIMEOUT_S = 0.2           # tool_lifecycle MaybeLock budget


@dataclass(frozen=True)
class DampenResult:
    """Return value of :func:`dampen`.

    ``text``      — what the caller should surface (full or condensed).
    ``ordinal``   — 1-based occurrence count for this advisory ID this
                    session (1 on the exempt / disabled / failure paths).
    ``condensed`` — True iff ``text`` is the condensed form.
    ``exempt``    — True iff the decision field exempted the input
                    (deny/block/unknown — returned verbatim, uncounted).
    """

    text: str
    ordinal: int
    condensed: bool
    exempt: bool


# ---------------------------------------------------------------------------
# Kill switches
# ---------------------------------------------------------------------------


def _env_value(key: str) -> Optional[str]:
    """trusted_env snapshot first (house pattern), live env fallback."""
    try:
        from _lib import trusted_env as _trusted_env
        return _trusted_env.get_trusted(key)
    except Exception:
        try:
            return os.environ.get(key)
        except Exception:  # pragma: no cover
            return None


def _dampen_enabled() -> bool:
    """Default ON; ``CEO_ADVISORY_DAMPEN=0`` or ``CEO_SOTA_DISABLE=1``
    disables (full text always). Never raises."""
    try:
        if str(_env_value(_MASTER_KILL_VAR) or "").strip() == "1":
            return False
        raw = _env_value(_DAMPEN_KILL_VAR)
        return (str(raw).strip() != "0") if raw is not None else True
    except Exception:  # pragma: no cover
        return True


# ---------------------------------------------------------------------------
# Per-session 0600 state file (tool_lifecycle pattern)
# ---------------------------------------------------------------------------


def _state_base_dir() -> Path:
    """``CEO_AUDIT_LOG_DIR`` (live env — swarm children inherit a per-slot
    value) else ``$HOME/.claude/projects/ceo-orchestration``. This is state
    ADJACENT to the audit dir, never the audit chain itself."""
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration"


def _safe_component(raw: str, empty: str) -> str:
    """Sanitize an attacker-influenceable string into one safe path/ID
    component (tool_lifecycle ``_safe_session_component`` clone)."""
    s = (raw or "").strip()
    if not s:
        return empty
    out = "".join(
        c if (c.isalnum() or c in ("-", "_", ".", ":")) else "_" for c in s
    )
    if set(out) <= {"."}:
        return empty
    return out


def _safe_session_component(session_id: str) -> str:
    return _safe_component(session_id, "_nosession").replace(":", "_")[:200]


def _sanitize_advisory_id(advisory_id: str) -> str:
    """Bounded opaque ID: keep ``[A-Za-z0-9._:-]``, collapse the rest,
    truncate to 64 chars. Empty → ``_advisory``."""
    return _safe_component(advisory_id, "_advisory")[:_ID_MAX_LEN]


def _state_path(session_id: str, state_dir: Optional[Path] = None) -> Path:
    base = Path(state_dir) if state_dir is not None else _state_base_dir()
    return base / _STATE_SUBDIR / (_safe_session_component(session_id) + ".json")


def _load_state(path: Path) -> Dict[str, Any]:
    """Fail-open empty on any error (an unreadable state means ordinal 1 /
    full text — degradation preserves legibility)."""
    try:
        if not path.is_file():
            return {}
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    counters = data.get("counters")
    if not isinstance(counters, dict):
        data["counters"] = {}
    else:
        data["counters"] = {
            k: v for k, v in counters.items() if isinstance(v, dict)
        }
    return data


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    """Atomic 0600 write; dir 0700. Fail-open (a write failure only costs
    dampening, never text)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError:
        pass
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        fd = os.open(str(tmp), os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False)
        os.replace(str(tmp), str(path))
        try:
            os.chmod(str(path), 0o600)
        except OSError:
            pass
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


class _MaybeLock:
    """Best-effort FileLock (tool_lifecycle pattern): O(1) hold; timeout or
    unavailability → proceed, worst case benign last-writer-wins."""

    def __init__(self, path: Path, timeout: float = _LOCK_TIMEOUT_S) -> None:
        self._lock = None
        try:
            from _lib.filelock import FileLock as _FileLock
            try:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            except OSError:
                pass
            self._lock = _FileLock(str(path) + ".lock", timeout=timeout)
        except Exception:
            self._lock = None

    def __enter__(self) -> "_MaybeLock":
        if self._lock is not None:
            try:
                self._lock.acquire()
            except Exception:
                self._lock = None
        return self

    def __exit__(self, *exc: Any) -> None:
        if self._lock is not None:
            try:
                self._lock.release()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Condensation + audit event
# ---------------------------------------------------------------------------


def _condense(advisory_id: str, ordinal: int, text: str) -> str:
    """The condensed form. ALWAYS retains (A10 point 3):

      * the advisory ID (stable lookup key),
      * the ordinal count (``xN`` this session),
      * a pointer to the full text (first occurrence this session + the
        first-line preview + the disable switch).
    """
    first_line = ""
    if text:
        for line in text.splitlines():
            if line.strip():
                first_line = line.strip()[:_POINTER_PREVIEW_CHARS]
                break
    return (
        "[advisory %s | x%d | condensed] %s ... (repeat advisory condensed; "
        "full text was printed at its first occurrence this session under "
        "advisory ID %s; set CEO_ADVISORY_DAMPEN=0 for full repeats)"
        % (advisory_id, ordinal, first_line, advisory_id)
    )


def _emit_condensation_event(
    advisory_id: str, ordinal: int, session_id: str
) -> None:
    """<= 1 per advisory ID per session (caller gates on the persisted
    ``emitted`` flag). NEW action ``advisory_dampened`` — emitted via
    ``audit_emit.emit_generic``, a breadcrumbed no-op until the integrator
    lands the action registration. METADATA ONLY: bounded ID, int ordinal,
    closed channel enum — never the advisory text. Fail-open."""
    try:
        from _lib import audit_emit as _audit_emit
        _audit_emit.emit_generic(
            "advisory_dampened",
            advisory_id=advisory_id,
            ordinal=int(ordinal),
            channel=CHANNEL_STDERR_PROSE,
            session_id=session_id,
            project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
        )
    except Exception:  # fail-open on emit only
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def dampen(
    advisory_id: str,
    text: str,
    *,
    decision: str,
    session_id: str = "",
    state_dir: Optional[Path] = None,
    now_fn: Optional[Callable[[], float]] = None,
) -> DampenResult:
    """Dampen REPEATED advisory prose; pass everything else through verbatim.

    Parameters
    ----------
    advisory_id : stable bounded ID for this advisory class (sanitized to
        ``[A-Za-z0-9._:-]{1,64}``).
    text : the full human-facing prose.
    decision : REQUIRED keyword — the schema decision field (A10 point 1).
        Only ``"advisory"`` is dampenable; ``"deny"`` / ``"block"`` / any
        unknown value returns ``text`` verbatim (``exempt=True``) with NO
        state I/O.
    session_id : session scope key; defaults to ``$CLAUDE_SESSION_ID``.
    state_dir : test seam — overrides the state base dir.
    now_fn : injectable clock (A9); wall clock only as default.

    Behavior: ordinal 1 → full text; ordinal >= 2 → condensed form
    (ID + ordinal + pointer retained). First condensation of an ID emits
    one ``advisory_dampened`` audit event. Any infrastructure failure →
    full text (legibility never lost).
    """
    if decision not in DAMPENABLE_DECISIONS:
        # deny/block/unknown: verbatim, uncounted, no state I/O (A10).
        return DampenResult(text=text, ordinal=1, condensed=False, exempt=True)
    if not _dampen_enabled():
        return DampenResult(text=text, ordinal=1, condensed=False, exempt=False)
    try:
        aid = _sanitize_advisory_id(advisory_id)
        sid = session_id or os.environ.get("CLAUDE_SESSION_ID", "")
        path = _state_path(sid, state_dir)
        now = (now_fn or time.time)()
        emit_needed = False
        with _MaybeLock(path):
            state = _load_state(path)
            counters = state.setdefault("counters", {})
            rec = counters.get(aid)
            if rec is None:
                if len(counters) >= _MAX_TRACKED_IDS:
                    # Bounded map: an untracked ID is never condensed.
                    return DampenResult(
                        text=text, ordinal=1, condensed=False, exempt=False
                    )
                rec = {"count": 0, "emitted": False, "first_s": now}
            rec["count"] = int(rec.get("count", 0)) + 1
            ordinal = rec["count"]
            condensed = ordinal >= 2
            if condensed and not rec.get("emitted", False):
                emit_needed = True
                rec["emitted"] = True
            counters[aid] = rec
            _save_state(path, state)
        if emit_needed:
            # Off the state-lock hold; <=1 per ID per session by the
            # persisted ``emitted`` flag above.
            _emit_condensation_event(aid, ordinal, sid)
        if condensed:
            return DampenResult(
                text=_condense(aid, ordinal, text),
                ordinal=ordinal,
                condensed=True,
                exempt=False,
            )
        return DampenResult(
            text=text, ordinal=ordinal, condensed=False, exempt=False
        )
    except Exception:
        # INFRASTRUCTURE fail-open toward FULL TEXT.
        return DampenResult(text=text, ordinal=1, condensed=False, exempt=False)


__all__ = [
    "DAMPENABLE_DECISIONS",
    "EXEMPT_DECISIONS",
    "CHANNEL_STDERR_PROSE",
    "DampenResult",
    "dampen",
]
