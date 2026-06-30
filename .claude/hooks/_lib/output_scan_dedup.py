"""24h TTL composite-key dedup for output_scan findings.

PLAN-106 Wave H.1 (absorption of PLAN-095-FOLLOWUP).

## Contract

Composite key `(repo_path_hash, command_sha, pattern_id)` deduplicates
output_scan findings within a 24-hour rolling window. The same
finding-tuple fired again within 24h emits an
`output_scan_finding_suppressed` event instead of a duplicate
`output_scan_finding` event.

## Atomic API (S128 Codex R2 P1 #10 carryover fold)

The legacy split-phase API (`should_suppress` + `record_emit`) had a
race where two parallel emitters could BOTH observe "not suppressed"
and BOTH fire the first-emit. The atomic API combines both into:

    check_and_record(repo_path_hash, command_sha, pattern_id) \\
        -> Tuple[bool, int]
            # (suppressed?, ttl_hours_remaining)

This runs under ONE `FileLock` acquire — the suppression decision and
the state update are atomic.

## Hash strength (AC13b, identity-trust R1 P1 fold)

- `hash_repo_path()`: returns sha256 full 64-hex digest, no truncation.
- `hash_command()`: returns sha256 full 64-hex digest, no truncation.

Adversarial-collision unit test (N=10⁴) confirms zero spurious
composite-key matches.

## Fail-open contract

Any filelock acquisition failure, JSON parse error, or filesystem
error degrades to "not suppressed" (the finding emits as a fresh
first-fire). This preserves the "advisory hook never blocks" guarantee
of ADR-057.

## State file location

State persists at `<state_root>/output-scan-dedup.json` where
`state_root` is derived from `$CLAUDE_PROJECT_DIR` or, if unset,
`$HOME/.claude/projects/ceo-orchestration/state/`. Schema:

    {
        "entries": {
            "<repo_path_hash>:<command_sha>:<pattern_id>": {
                "first_seen_ts": 1715900000.0,
                "last_seen_ts": 1715900050.0,
                "fire_count": 2
            },
            ...
        }
    }

Garbage-collection: entries with `last_seen_ts < now - 24h` are pruned
on every write (cheap; state file capped at a few hundred entries in
realistic workloads).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

_TTL_HOURS = 24
_TTL_SECONDS = _TTL_HOURS * 3600

# Test/diagnostic override — let tests fast-forward the clock so they
# don't need to wait 24h. Set to a float by tests; production reads None.
_CLOCK_OVERRIDE: Optional[float] = None


def _now() -> float:
    """Wall-clock seconds; tests can override via `_set_clock_override`."""
    if _CLOCK_OVERRIDE is not None:
        return _CLOCK_OVERRIDE
    return time.time()


def _set_clock_override(t: Optional[float]) -> None:
    """Tests use this to fast-forward / freeze the clock. Production: None."""
    global _CLOCK_OVERRIDE
    _CLOCK_OVERRIDE = t


# ---------------------------------------------------------------------
# Hash helpers (AC13b)
# ---------------------------------------------------------------------

def hash_repo_path(repo_path: str) -> str:
    """sha256 full 64-hex digest of the repo path. No truncation.

    Always returns a 64-character lowercase hex string. Identity-trust
    R1 P1 fold (PLAN-106 §3 Wave H.1.a) mandates full digest — partial
    digests admit collision attacks at adversarial N≥2^32.
    """
    s = "" if repo_path is None else str(repo_path)
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def hash_command(command_snippet: str) -> str:
    """sha256 full 64-hex digest of the command snippet. No truncation.

    Caller passes the tool-input snippet (Bash command body, Edit
    target+content snippet, etc.). The hash is opaque — auditor reads
    it as an opaque identifier, not a reconstructable source. Sec MF-3
    persistence safety: no raw command body lands in the audit log.
    """
    s = "" if command_snippet is None else str(command_snippet)
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def derive_repo_path_hash_from_env() -> str:
    """Best-effort repo-path hash from `$CLAUDE_PROJECT_DIR` (fallback: cwd).

    Always returns a 64-hex string. Never raises.
    """
    try:
        repo = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        return hash_repo_path(repo)
    except Exception:
        return hash_repo_path("")


# ---------------------------------------------------------------------
# State file path resolution
# ---------------------------------------------------------------------

def _resolve_state_dir() -> Path:
    """Where the dedup state file lives.

    Priority:
        1. $CEO_OUTPUT_SCAN_DEDUP_STATE_DIR (test override)
        2. $CEO_AUDIT_LOG_DIR (test isolation via TestEnvContext)
        3. $HOME/.claude/projects/ceo-orchestration/state/
    """
    override = os.environ.get("CEO_OUTPUT_SCAN_DEDUP_STATE_DIR")
    if override:
        return Path(override)
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        return Path(audit_dir)
    home = os.environ.get("HOME") or "/tmp"
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state"


def _state_file_path() -> Path:
    return _resolve_state_dir() / "output-scan-dedup.json"


def _lock_file_path() -> Path:
    return _resolve_state_dir() / "output-scan-dedup.lock"


# ---------------------------------------------------------------------
# State (de)serialization
# ---------------------------------------------------------------------

def _load_state(path: Path) -> Dict[str, Any]:
    """Read the state file. Returns empty state on any I/O / parse error."""
    if not path.is_file():
        return {"entries": {}}
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {"entries": {}}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {"entries": {}}
    if not isinstance(data, dict) or "entries" not in data:
        return {"entries": {}}
    if not isinstance(data["entries"], dict):
        return {"entries": {}}
    return data


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    """Atomic write via temp-file + rename. Best-effort; never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
        os.replace(str(tmp), str(path))
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def _prune_expired(state: Dict[str, Any], now: float) -> Dict[str, Any]:
    """Drop entries whose last_seen_ts is older than 24h. Returns NEW dict."""
    cutoff = now - _TTL_SECONDS
    entries_in = state.get("entries", {})
    pruned: Dict[str, Any] = {}
    for k, v in entries_in.items():
        if not isinstance(v, dict):
            continue
        last = v.get("last_seen_ts", 0)
        try:
            last_f = float(last)
        except (TypeError, ValueError):
            continue
        if last_f >= cutoff:
            pruned[k] = v
    return {"entries": pruned}


def _composite_key(
    repo_path_hash: str, command_sha: str, pattern_id: str
) -> str:
    """Deterministic 3-tuple → flat string key for the JSON entries dict."""
    return f"{repo_path_hash}:{command_sha}:{pattern_id}"


def _ttl_hours_remaining(entry: Dict[str, Any], now: float) -> int:
    """Compute the integer hours left on the TTL for this entry."""
    first = entry.get("first_seen_ts", now)
    try:
        first_f = float(first)
    except (TypeError, ValueError):
        first_f = now
    elapsed = now - first_f
    remaining_sec = max(0, _TTL_SECONDS - int(elapsed))
    return max(0, remaining_sec // 3600)


# ---------------------------------------------------------------------
# Atomic API — S128 Codex R2 P1 #10 carryover fold
# ---------------------------------------------------------------------

def check_and_record(
    repo_path_hash: str,
    command_sha: str,
    pattern_id: str,
) -> Tuple[bool, int]:
    """Atomic: decide suppress + record under one FileLock acquire.

    Returns:
        (suppressed, ttl_hours_remaining)

        - suppressed=False: this is the FIRST fire for this key in 24h.
          State recorded so the next call within 24h suppresses.
          ttl_hours_remaining=24 (full window).
        - suppressed=True: this key has fired within the last 24h.
          fire_count incremented; ttl_hours_remaining = hours left.

    Fail-open: any error → (False, 24) so the caller falls through to a
    fresh first-fire emit. The hook never blocks on a dedup-state bug.
    """
    try:
        # Defensive type coercion
        rph = str(repo_path_hash or "")
        csh = str(command_sha or "")
        pid = str(pattern_id or "")
        if not rph or not csh or not pid:
            # Refuse to dedup on empty key — treat as fresh fire.
            return (False, _TTL_HOURS)
    except Exception:
        return (False, _TTL_HOURS)

    state_path = _state_file_path()
    lock_path = _lock_file_path()
    now = _now()
    key = _composite_key(rph, csh, pid)

    try:
        from _lib.filelock import FileLock, FileLockTimeout  # type: ignore
    except Exception:
        # No filelock — fail-open
        return (False, _TTL_HOURS)

    try:
        with FileLock(str(lock_path), timeout=2.5):
            # Atomic critical section: load + decide + write
            state = _load_state(state_path)
            state = _prune_expired(state, now)
            entries = state["entries"]
            existing = entries.get(key)

            if existing is not None:
                # Suppress — within 24h window
                fire_count = int(existing.get("fire_count", 1)) + 1
                first_seen = existing.get("first_seen_ts", now)
                entries[key] = {
                    "first_seen_ts": first_seen,
                    "last_seen_ts": now,
                    "fire_count": fire_count,
                }
                state["entries"] = entries
                _save_state(state_path, state)
                ttl_remaining = _ttl_hours_remaining(entries[key], now)
                return (True, ttl_remaining)
            else:
                # First fire — record
                entries[key] = {
                    "first_seen_ts": now,
                    "last_seen_ts": now,
                    "fire_count": 1,
                }
                state["entries"] = entries
                _save_state(state_path, state)
                return (False, _TTL_HOURS)

    except FileLockTimeout:
        # Filelock contention beyond timeout — fail-open
        return (False, _TTL_HOURS)
    except Exception:
        # Any other unexpected error — fail-open
        return (False, _TTL_HOURS)


# ---------------------------------------------------------------------
# Diagnostic helpers (for tests + audit-query tooling)
# ---------------------------------------------------------------------

def peek_entry(
    repo_path_hash: str,
    command_sha: str,
    pattern_id: str,
) -> Optional[Dict[str, Any]]:
    """Non-mutating read of one entry. Returns None if not present."""
    key = _composite_key(
        str(repo_path_hash or ""),
        str(command_sha or ""),
        str(pattern_id or ""),
    )
    state = _load_state(_state_file_path())
    return state.get("entries", {}).get(key)


def clear_state() -> None:
    """Diagnostic — drop the dedup state file. Tests use between runs."""
    try:
        p = _state_file_path()
        if p.is_file():
            p.unlink()
    except OSError:
        pass


def entry_count() -> int:
    """Diagnostic — return current entry count post-prune."""
    state = _load_state(_state_file_path())
    return len(state.get("entries", {}))


__all__ = [
    "hash_repo_path",
    "hash_command",
    "derive_repo_path_hash_from_env",
    "check_and_record",
    "peek_entry",
    "clear_state",
    "entry_count",
    # Test helpers (not for production callers)
    "_set_clock_override",
]
