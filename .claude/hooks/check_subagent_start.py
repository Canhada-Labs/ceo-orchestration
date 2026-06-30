#!/usr/bin/env python3
"""PLAN-135 W2 H3 — SubagentStart lifecycle recorder (sidecar half of the
per-agent accounting bracket).

SubagentStart observer that records the spawn instant + spawn context
(agent_type, session binding) into a local state sidecar, keyed by a
sha256 prefix of the harness-supplied ``agent_id``. The matching
SubagentStop hook (``check_fluency_nudge.py``, H3 extension) CONSUMES
the entry to compute per-agent wall-time and emits ONE
``subagent_lifecycle_observed`` audit event per agent — the S227
forensic ``modelUsage`` reconstruction becomes a live hook emit.

## Contract

- ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing
  files / lock timeouts → stderr breadcrumb + emit ``{}``). NEVER blocks.
- NO audit actions are emitted from THIS hook — the single per-agent
  emit happens at SubagentStop (closed-enum ``subagent_lifecycle_observed``,
  registered in BOTH ``_KNOWN_ACTIONS`` and SPEC v2.43). This hook writes
  only the local sidecar + stderr breadcrumbs.
- Sidecar privacy: the raw ``agent_id`` is NEVER persisted — the entry
  key is ``sha256(agent_id)[:16]``. Values stored: ``start_ts`` (epoch
  float), ``agent_type`` (clamped 64 chars), ``session_id`` (clamped
  64 chars). No prompt, no description, no paths.
- TTL 24h + 512-entry cap pruned on every write (orphaned starts from
  crashed agents cannot grow the file unboundedly).
- Kill-switch: ``CEO_SUBAGENT_LIFECYCLE=0`` (shared with the
  SubagentStop consumption half).
- Stdlib only, Python >= 3.9.

## Sidecar location (output_scan_dedup.py precedent)

1. ``$CEO_SUBAGENT_LIFECYCLE_STATE_DIR`` (test override)
2. ``$CEO_AUDIT_LOG_DIR`` (test isolation via TestEnvContext)
3. ``$HOME/.claude/projects/ceo-orchestration/state/``

PARITY NOTE: ``_state_dir`` / ``_sidecar_path`` / ``_agent_key`` /
``_load_sidecar`` / ``_save_sidecar`` / ``_prune_entries`` are duplicated
in ``check_fluency_nudge.py`` (the stop half) BY DESIGN — a shared
``_lib`` module would move the CLAUDE.md ``_lib`` count gate for ~40
lines of pure stdlib helpers. Keep the two copies byte-equivalent
(staged test ``test_check_subagent_start.py::SidecarParityTests``
asserts it mechanically).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Make the local `_lib` importable (matches the pattern of existing hooks).
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# Best-effort lock (concurrent parallel spawns race the sidecar write).
# Import-guarded: lock unavailability degrades to lockless atomic
# tmp+rename (worst case one racing start entry is lost → that agent's
# wall_source resolves to "unknown" at stop — advisory data, never a block).
try:
    from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
    _FILELOCK_AVAILABLE = True
except Exception:  # pragma: no cover
    FileLock = None  # type: ignore[assignment]
    FileLockTimeout = Exception  # type: ignore[assignment, misc]
    _FILELOCK_AVAILABLE = False


# --- BEGIN sidecar helpers (PARITY block — mirrored in check_fluency_nudge.py)
_SIDECAR_FILENAME = "subagent-lifecycle.json"
_SIDECAR_LOCK_FILENAME = "subagent-lifecycle.json.lock"
_SIDECAR_TTL_S = 24 * 3600       # orphaned-start retention
_SIDECAR_MAX_ENTRIES = 512       # hard cap (newest win)
_LOCK_TIMEOUT_S = 0.5            # never stall a spawn on the sidecar


def _state_dir() -> Path:
    """Sidecar directory (output_scan_dedup.py resolution precedent)."""
    override = os.environ.get("CEO_SUBAGENT_LIFECYCLE_STATE_DIR")
    if override:
        return Path(override)
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        return Path(audit_dir)
    home = os.environ.get("HOME") or "/tmp"
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state"


def _sidecar_path() -> Path:
    return _state_dir() / _SIDECAR_FILENAME


def _sidecar_lock_path() -> Path:
    return _state_dir() / _SIDECAR_LOCK_FILENAME


def _agent_key(agent_id: str) -> str:
    """Opaque sidecar key — raw agent_id never lands on disk."""
    return hashlib.sha256(
        agent_id.encode("utf-8", errors="replace")
    ).hexdigest()[:16]


def _load_sidecar(path: Path) -> Dict[str, Any]:
    """Read the sidecar. Returns empty state on any I/O / parse error."""
    if not path.is_file():
        return {"entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"entries": {}}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        return {"entries": {}}
    return data


def _save_sidecar(path: Path, state: Dict[str, Any]) -> bool:
    """Atomic write via temp-file + rename. Best-effort; never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
        tmp.write_text(
            json.dumps(state, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(str(tmp), str(path))
        return True
    except Exception:
        return False


def _prune_entries(entries: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Drop entries past TTL; keep at most _SIDECAR_MAX_ENTRIES newest."""
    fresh: Dict[str, Any] = {}
    for key, val in entries.items():
        if not isinstance(val, dict):
            continue
        try:
            start_ts = float(val.get("start_ts", 0))
        except (TypeError, ValueError):
            continue
        if now - start_ts <= _SIDECAR_TTL_S:
            fresh[key] = val
    if len(fresh) > _SIDECAR_MAX_ENTRIES:
        ordered = sorted(
            fresh.items(),
            key=lambda kv: float(kv[1].get("start_ts", 0)),
            reverse=True,
        )
        fresh = dict(ordered[:_SIDECAR_MAX_ENTRIES])
    return fresh
# --- END sidecar helpers (PARITY block)


def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_subagent_start: %s\n" % msg[:160])


def _first_str(event: Dict[str, Any], *keys: str) -> str:
    """First present string value among payload key variants (clamped)."""
    for key in keys:
        val = event.get(key)
        if isinstance(val, str) and val:
            return val[:256]
    return ""


def _record_start(event: Dict[str, Any]) -> None:
    """Record the spawn instant; lock-guarded, fail-open."""
    agent_id = _first_str(event, "agent_id", "agentId")
    if not agent_id:
        # No join key — the stop half will emit wall_source="unknown".
        _breadcrumb("no agent_id in SubagentStart payload — skipping record")
        return
    agent_type = _first_str(event, "agent_type", "agentType", "subagent_type")
    session_id = _first_str(event, "session_id", "sessionId")
    now = time.time()
    entry = {
        "start_ts": now,
        "agent_type": agent_type[:64],
        "session_id": session_id[:64],
    }

    def _write() -> None:
        state = _load_sidecar(_sidecar_path())
        entries = _prune_entries(state.get("entries", {}), now)
        entries[_agent_key(agent_id)] = entry
        state["entries"] = entries
        if not _save_sidecar(_sidecar_path(), state):
            _breadcrumb("sidecar write failed (fail-open)")

    if _FILELOCK_AVAILABLE and FileLock is not None:
        try:
            with FileLock(_sidecar_lock_path(), timeout=_LOCK_TIMEOUT_S):
                _write()
            return
        except FileLockTimeout:
            _breadcrumb("sidecar lock timeout — lockless best-effort write")
        except Exception as exc:
            _breadcrumb("sidecar lock error (%s) — lockless write" % str(exc)[:60])
    _write()


def main() -> int:
    """Hook entrypoint. Reads SubagentStart payload from stdin; always allows."""
    # Kill-switch (shared with the SubagentStop consumption half).
    if os.environ.get("CEO_SUBAGENT_LIFECYCLE") == "0":
        print("{}")
        return 0
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw else {}
        if not isinstance(event, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        _breadcrumb("fail-open (stdin): %s" % str(exc)[:120])
        print("{}")
        return 0
    try:
        _record_start(event)
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("fail-open (record): %s" % str(exc)[:120])
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
