#!/usr/bin/env python3
"""Governance Hook: DirectoryAdded observer-WRITER (PLAN-163 T3.1).

Registered in `.claude/settings.json` under `hooks.DirectoryAdded`
(matcher on `source`), invoked via `_python-hook.sh`. Kill-switch:
``CEO_DIRECTORY_ADDED_GUARD=0``.

## What this hook IS (and is honestly NOT)

The T3.1 blockability probe (`PLAN-163/probes/diradd-blockability.md`,
CC 2.1.220) established three hard facts this hook is designed around:

1. **DirectoryAdded is NOTIFICATION-ONLY.** The event executor collects
   only ``systemMessage``; ``decision: "block"`` is structurally ignored
   (the event is absent from the blocking-capable set). This hook is an
   OBSERVER, never a gate.
2. **The event is POST-FACTO.** Permission/sandbox state already
   includes the added directory BEFORE the hook fires (fire-and-forget
   dispatch). By the time we run, reads AND writes into the added tree
   are already authorized for the rest of the session. Nothing here
   closes that window — enforcement lives in the PreToolUse write-guard
   family (Edit|Write|MultiEdit), which CONSUMES the registry this hook
   writes (deny of writes under a registered, non-allowlisted root,
   absolute-path + realpath matching, fail-CLOSED canonicalization in
   the consumer).
3. **Launch-time ``--add-dir`` fires NO DirectoryAdded event at all**
   (probe Run B). Roots added at launch are INVISIBLE to this registry —
   a documented residual blind spot. Follow-up mitigation candidate (NOT
   implemented here; this hook is wired only for DirectoryAdded): a
   SessionStart-side snapshot of the effective working-root set, if the
   harness exposes it cheaply. Until then the registry only covers roots
   added mid-session via `/add-dir` (``source: slash_command``) or the
   SDK control request (``source: register_repo_root``).

## Registry contract — `.claude/state/session-roots.json`

Versioned schema (consumers must check ``schema``)::

    {
      "schema": 1,
      "sessions": {
        "<session_id>": {
          "transcript_path": "<abs path or ''>",
          "roots": [
            {
              "directory": "<os.path.realpath abs path>",
              "source": "slash_command" | "register_repo_root",
              "ts": "<UTC ISO-8601>"
            },
            {"directory": "<raw, truncated>", "unparseable": true, ...}
          ]
        }
      }
    }

- **Scope:** per ``session_id``. One entry per canonical directory per
  session (re-adds refresh ``ts``/``source`` in place).
- **TTL = session (prune-on-write policy):** every write prunes OTHER
  sessions that are provably dead or stale: a session is dropped when
  (a) its recorded ``transcript_path`` no longer exists on disk, OR
  (b) the newest ``ts`` among its roots is older than 48 hours (or
  unparseable — counted as stale so corrupt timestamps cannot pin an
  entry forever). The 48h backstop exists because (a) alone cannot see
  sessions recorded by writers that had no transcript_path. The session
  being written is always retained.
- **Raw paths live ONLY here.** This file is local, non-commit
  (`.claude/state/` is gitignored — declared non-commit policy). The
  audit trail never carries the raw path (see below).
- **Bound:** roots per session are capped (oldest dropped, breadcrumb
  emitted) so a runaway caller cannot grow the file without bound.

## Unparseable input — observer posture

This hook is NOT a security matcher; it is fail-OPEN on input it cannot
parse (breadcrumb to stderr, ``{}`` to stdout, exit 0). ONE carve-out:
when the payload's ``directory`` field is present but cannot be
canonicalized to an absolute real path, we still record an entry marked
``"unparseable": true`` (raw value truncated). The fail-CLOSED
treatment of that marker belongs to the CONSUMER write-guard (an
unparseable registered root is a deny) — the fail-closed posture lives
in the matcher, not the observer, per CLAUDE.md §4.

## Failure envelope (ADR-002 fail-open on INFRA)

- Registry unreadable (OSError) or lock timeout: breadcrumb + ``{}``
  exit 0 — the event is dropped, the session is never blocked.
- Registry JSON corrupt: breadcrumb + self-heal (rebuild from the fresh
  versioned schema and record the current event) — a one-time poisoned
  file must not kill the observer for the rest of time. Consumers lose
  previously recorded roots in that case; the corruption breadcrumb is
  the operator's signal.
- Any unexpected exception: breadcrumb + ``{}`` exit 0.

## Audit emission — no-value-echo

If the typed emitter is registered in ``_lib.audit_emit`` (thread B3
registers the action; ``hasattr``-guarded here so this hook works with
or without it), we emit a typed event with the CLOSED field set:
``source``, ``directory_hash_prefix`` (sha256 hex of the canonical —
or, for unparseable entries, raw — directory string, first 12 chars),
``session_id``. The raw path is NEVER emitted to the audit log
(no-value-echo; raw paths persist only in the local gitignored
registry).

## Output contract

Always a single-line ``{}`` on stdout, exit 0. DirectoryAdded consumes
no decision arm; emitting anything else would be theater.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402

_HOOK_NAME = "check_directory_added"

# Registry schema version — bump on any breaking layout change.
_SCHEMA_VERSION = 1

# Prune backstop: sessions whose newest root ts is older than this are
# dropped on write (see module docstring, "TTL = session").
_STALE_AFTER = timedelta(hours=48)

# Bound on roots recorded per session (oldest dropped past this).
_MAX_ROOTS_PER_SESSION = 512

# Bound on the raw value persisted for unparseable directory fields.
_MAX_RAW_LEN = 1024

_LOCK_TIMEOUT_S = 2.5


def _breadcrumb(message: str) -> None:
    """Best-effort stderr breadcrumb. Never raises."""
    try:
        print(f"[{_HOOK_NAME}] {message}", file=sys.stderr)
    except Exception:
        pass


def _emit_empty() -> None:
    """Schema-compliant allow/no-op output for a notification-only event."""
    print("{}")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(raw: object) -> Optional[datetime]:
    """Parse a registry ``ts`` value. None on any failure (caller treats
    unparseable as stale — corrupt timestamps must not pin entries)."""
    if not isinstance(raw, str) or not raw:
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _registry_path() -> Path:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(project_dir) / ".claude" / "state" / "session-roots.json"


def _canonicalize(directory: object) -> Tuple[Optional[str], Optional[str]]:
    """Return (canonical_abs_path, None) or (None, raw_truncated).

    Canonical means: a str field that is ABSOLUTE **as received**, then
    resolved with ``os.path.realpath``. On any failure the truncated raw
    representation is returned so the caller can persist an
    ``unparseable: true`` entry (the consumer write-guard treats that
    marker as deny — fail-closed lives THERE).
    """
    raw_repr = repr(directory)[:_MAX_RAW_LEN]
    if not isinstance(directory, str) or not directory:
        return None, raw_repr
    # R2-M1 (MED): reject a RELATIVE directory BEFORE realpath. Calling
    # os.path.realpath on a relative value (e.g. "../evil") launders it
    # into a CWD-relative ABSOLUTE path — which then passes the isabs
    # check below AND the consumer write-guard's absolute-path test
    # (check_canonical_edit.py M2), mis-scoping the write boundary to an
    # attacker-influenced, CWD-dependent root. A directory that is not
    # absolute AS RECEIVED is not a trustworthy root: record it
    # unparseable=true so the consumer denies it fail-closed.
    if not os.path.isabs(directory):
        return None, directory[:_MAX_RAW_LEN]
    try:
        real = os.path.realpath(directory)
    except (OSError, ValueError):
        return None, directory[:_MAX_RAW_LEN]
    if not os.path.isabs(real):
        # Defensive: an absolute input whose realpath is somehow not
        # absolute is not a trustworthy root either.
        return None, directory[:_MAX_RAW_LEN]
    return real, None


def _hash_prefix(value: str) -> str:
    """sha256 hex prefix (12 chars) — the ONLY path derivative that may
    leave this process toward the audit log (no-value-echo)."""
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]


def _audit_fields(
    *, source: str, directory_repr: str, session_id: str
) -> Dict[str, str]:
    """CLOSED field set for the typed audit event. Pure — unit-testable.

    ``directory_repr`` is the canonical path when parseable, else the
    truncated raw value; either way only its hash prefix is returned.
    """
    return {
        "source": source,
        "directory_hash_prefix": _hash_prefix(directory_repr),
        "session_id": session_id,
    }


def _safe_audit_emit(fields: Dict[str, str]) -> None:
    """Emit the typed audit event IF thread B3's emitter is registered.

    hasattr-guarded against the lazy dispatch shim: an unregistered name
    raises AttributeError inside ``__getattr__`` so ``hasattr`` is a
    clean capability probe. Best-effort — audit emission failures never
    affect the observer.
    """
    try:
        from _lib import audit_emit_dispatch as _audit_emit
        # B3-merge: `emit_directory_added_recorded` is the emitter thread B3
        # actually registered (action `directory_added_recorded`,
        # _DIRECTORY_ADDED_RECORDED_ALLOWLIST; kwargs contract = exactly
        # `source` + `directory_hash_prefix` (12-hex) + `session_id`). The
        # two legacy names are kept as fallbacks only.
        for name in (
            "emit_directory_added_recorded",
            "emit_directory_added",
            "emit_directory_added_observed",
        ):
            if hasattr(_audit_emit, name):
                getattr(_audit_emit, name)(**fields)
                return
    except Exception as exc:
        _breadcrumb(f"WARN: audit emit skipped: {exc.__class__.__name__}: {exc}")


def _load_registry(path: Path) -> Dict[str, Any]:
    """Load the registry, returning a fresh versioned skeleton when the
    file is absent or corrupt (self-heal; breadcrumb on corruption).

    OSError propagates — the caller maps it to the infra fail-open path.
    """
    fresh: Dict[str, Any] = {"schema": _SCHEMA_VERSION, "sessions": {}}
    if not path.is_file():
        return fresh
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return fresh
    try:
        data = json.loads(raw)
    except ValueError:
        _breadcrumb("WARN: registry JSON corrupt — rebuilding fresh (self-heal)")
        return fresh
    if not isinstance(data, dict) or not isinstance(data.get("sessions"), dict):
        _breadcrumb("WARN: registry shape invalid — rebuilding fresh (self-heal)")
        return fresh
    if data.get("schema") != _SCHEMA_VERSION:
        _breadcrumb(
            f"WARN: registry schema {data.get('schema')!r} != {_SCHEMA_VERSION} "
            "— rebuilding fresh (self-heal)"
        )
        return fresh
    return data


def _session_is_stale(entry: Any, now: datetime) -> bool:
    """Prune predicate for a session entry OTHER than the current one.

    Stale when the recorded transcript is gone, or when the newest root
    ts is older than the 48h backstop (or unparseable).
    """
    if not isinstance(entry, dict):
        return True
    transcript = entry.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        if not os.path.exists(transcript):
            return True
    roots = entry.get("roots")
    if not isinstance(roots, list) or not roots:
        return True
    newest: Optional[datetime] = None
    for root in roots:
        if not isinstance(root, dict):
            continue
        parsed = _parse_ts(root.get("ts"))
        if parsed is not None and (newest is None or parsed > newest):
            newest = parsed
    if newest is None:
        return True  # no parseable ts at all — corrupt entries cannot pin
    return (now - newest) > _STALE_AFTER


def _prune_sessions(
    registry: Dict[str, Any], *, keep_session_id: str, now: datetime
) -> None:
    sessions = registry.get("sessions")
    if not isinstance(sessions, dict):
        registry["sessions"] = {}
        return
    for sid in list(sessions.keys()):
        if sid == keep_session_id:
            continue
        if _session_is_stale(sessions.get(sid), now):
            del sessions[sid]


def _record_root(
    registry: Dict[str, Any],
    *,
    session_id: str,
    transcript_path: str,
    directory_key: str,
    source: str,
    unparseable: bool,
    now_iso: str,
) -> None:
    """Insert/refresh a root entry for the session (dedup by directory)."""
    sessions = registry.setdefault("sessions", {})
    entry = sessions.get(session_id)
    if not isinstance(entry, dict):
        entry = {}
        sessions[session_id] = entry
    entry["transcript_path"] = transcript_path
    roots = entry.get("roots")
    if not isinstance(roots, list):
        roots = []
        entry["roots"] = roots

    new_root: Dict[str, Any] = {
        "directory": directory_key,
        "source": source,
        "ts": now_iso,
    }
    if unparseable:
        new_root["unparseable"] = True

    for i, root in enumerate(roots):
        if isinstance(root, dict) and root.get("directory") == directory_key:
            roots[i] = new_root  # re-add refreshes in place
            break
    else:
        roots.append(new_root)

    if len(roots) > _MAX_ROOTS_PER_SESSION:
        dropped = len(roots) - _MAX_ROOTS_PER_SESSION
        del roots[:dropped]
        _breadcrumb(
            f"WARN: session {session_id!r} exceeded {_MAX_ROOTS_PER_SESSION} "
            f"roots — dropped {dropped} oldest"
        )


def _atomic_write(path: Path, registry: Dict[str, Any]) -> None:
    """Write the registry atomically (tmp + os.replace), 0o600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".session-roots-", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(registry, f, sort_keys=True, separators=(",", ":"))
            f.write("\n")
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def process_event(payload: Dict[str, Any]) -> None:
    """Validate the DirectoryAdded payload and persist the root.

    Raises nothing that matters: infra failures (OSError / lock timeout)
    propagate to main()'s fail-open envelope; shape mismatches return
    after a breadcrumb.
    """
    event_name = payload.get("hook_event_name")
    if event_name != "DirectoryAdded":
        _breadcrumb(
            f"WARN: unexpected hook_event_name {event_name!r} — observer "
            "no-op (wired for DirectoryAdded only)"
        )
        return

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        _breadcrumb("WARN: missing/invalid session_id — event dropped")
        return

    if "directory" not in payload:
        _breadcrumb("WARN: payload has no directory field — event dropped")
        return

    source_raw = payload.get("source")
    source = source_raw if isinstance(source_raw, str) and source_raw else "unknown"

    transcript_raw = payload.get("transcript_path")
    transcript_path = (
        transcript_raw if isinstance(transcript_raw, str) else ""
    )

    canonical, raw_fallback = _canonicalize(payload.get("directory"))
    unparseable = canonical is None
    directory_key = canonical if canonical is not None else (raw_fallback or "")
    if unparseable:
        _breadcrumb(
            "WARN: directory field did not canonicalize — recording entry "
            "with unparseable=true (consumer write-guard treats as deny)"
        )

    registry_path = _registry_path()
    lock_path = registry_path.with_name(registry_path.name + ".lock")
    now = _utc_now()

    with FileLock(lock_path, timeout=_LOCK_TIMEOUT_S):
        registry = _load_registry(registry_path)
        _prune_sessions(registry, keep_session_id=session_id, now=now)
        _record_root(
            registry,
            session_id=session_id,
            transcript_path=transcript_path,
            directory_key=directory_key,
            source=source,
            unparseable=unparseable,
            now_iso=_utc_now_iso(),
        )
        _atomic_write(registry_path, registry)

    _safe_audit_emit(
        _audit_fields(
            source=source, directory_repr=directory_key, session_id=session_id
        )
    )


def main() -> int:
    """Hook entry point — kill-switch first, fail-open on everything."""
    if os.environ.get("CEO_DIRECTORY_ADDED_GUARD", "1").strip() == "0":
        _emit_empty()
        return 0

    try:
        raw = sys.stdin.read()
    except Exception as exc:
        _breadcrumb(f"WARN: stdin read failed: {exc.__class__.__name__}: {exc}")
        _emit_empty()
        return 0

    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError as exc:
        # Observer, not a gate: unparseable input is fail-open here; the
        # fail-closed posture for unparseable DATA lives in the consumer.
        _breadcrumb(f"WARN: stdin parse error: {exc}")
        _emit_empty()
        return 0

    if not isinstance(payload, dict):
        _breadcrumb("WARN: payload is not a JSON object — event dropped")
        _emit_empty()
        return 0

    try:
        process_event(payload)
    except FileLockTimeout:
        _breadcrumb("WARN: registry lock timeout — event dropped (fail-open)")
    except OSError as exc:
        _breadcrumb(
            f"WARN: registry I/O failure: {exc.__class__.__name__}: {exc} "
            "— event dropped (fail-open)"
        )
    except Exception as exc:  # pragma: no cover — defensive envelope
        _breadcrumb(f"FATAL: {exc.__class__.__name__}: {exc} — fail-open")

    _emit_empty()
    return 0


if __name__ == "__main__":
    sys.exit(main())
