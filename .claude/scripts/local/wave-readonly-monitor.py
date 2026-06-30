#!/usr/bin/env python3
"""PLAN-084 Wave 0.4-bis — Layer 3 real-time watchdog.

Tails audit-log.jsonl during Wave A/B/C/D windows. Trips
WAVE-ABORTED-CANONICAL-WRITE or WAVE-ABORTED-STAGING-VIOLATION
sentinel file on first matching event. CEO downstream dispatchers
MUST poll for these sentinels between batches and halt.

Stdlib only. Polling-based (5s sleep). On SIGTERM or Owner closing
terminal, writes final state file gracefully.

Usage:
  python3 .claude/scripts/local/wave-readonly-monitor.py \
    --audit-log ~/.claude/projects/ceo-orchestration/audit-log.jsonl \
    --plan-dir .claude/plans/PLAN-084 \
    --staging-policy .claude/plans/PLAN-084/staging-write-policy.yaml \
    --start-iso 2026-05-12T04:15:24Z \
    --end-iso 2026-05-12T12:00:00Z

Exit codes:
  0 — window closed cleanly with no violations
  1 — Layer 3a canonical write detected
  2 — Layer 3b staging violation detected
  3 — argument / setup error
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Layer 3a — canonical/sentinel/GPG/wave_readonly events
_LAYER_3A_ACTION_PREFIXES = (
    "canonical_edit_",
    "sentinel_",
    "gpg_",
    "wave_readonly_",
)
_LAYER_3A_REASON_CODES = {
    "canonical_edit_unsigned",
    "canonical_edit_hook_fault",
    "sentinel_unlock_used",
}

# Layer 3b — staging-write-policy validation
_STAGING_ACTION = "wave_artifact_written"


def parse_yaml_minimal(path: Path) -> List[Dict]:
    """Minimal YAML parser for staging-write-policy.yaml (stdlib only).

    Parses a specific structure: top-level `allowed_writes:` list of
    dicts with keys (wave, archetype, session_id_pattern, path_globs).
    """
    entries: List[Dict] = []
    current: Optional[Dict] = None
    in_path_globs = False
    in_allowed_writes = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        if stripped.startswith("allowed_writes:"):
            in_allowed_writes = True
            continue
        if not in_allowed_writes:
            continue
        if stripped.startswith("  - wave:"):
            if current is not None:
                entries.append(current)
            current = {"path_globs": []}
            in_path_globs = False
            current["wave"] = stripped.split("wave:", 1)[1].strip().strip('"')
        elif current is not None:
            if stripped.startswith("    archetype:"):
                current["archetype"] = stripped.split("archetype:", 1)[1].strip()
                in_path_globs = False
            elif stripped.startswith("    session_id_pattern:"):
                current["session_id_pattern"] = stripped.split("session_id_pattern:", 1)[1].strip().strip('"')
                in_path_globs = False
            elif stripped.startswith("    path_globs:"):
                in_path_globs = True
            elif in_path_globs and stripped.startswith("      - "):
                glob_value = stripped[8:].strip()
                current["path_globs"].append(glob_value)
            else:
                # End of current entry section (a non-matching line)
                pass
    if current is not None:
        entries.append(current)
    return entries


def match_staging_policy(
    policy: List[Dict],
    wave_id: str,
    archetype: str,
    session_id: str,
    path: str,
) -> Tuple[bool, str]:
    """Return (allowed, reason)."""
    import re as _re
    for entry in policy:
        if entry.get("wave") != wave_id:
            continue
        if entry.get("archetype") != archetype:
            continue
        try:
            if not _re.match(entry.get("session_id_pattern", ".*"), session_id):
                continue
        except _re.error:
            continue
        for glob in entry.get("path_globs", []):
            if fnmatch.fnmatch(path, glob):
                return True, "policy_match"
    return False, "no_policy_match"


def read_new_events(
    log_path: Path,
    last_offset: int,
) -> Tuple[List[Dict], int]:
    """Read events appended since last_offset. Returns (events, new_offset)."""
    new_offset = last_offset
    events: List[Dict] = []
    try:
        with log_path.open("rb") as f:
            f.seek(last_offset)
            data = f.read()
            new_offset = f.tell()
        for line in data.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except FileNotFoundError:
        pass
    return events, new_offset


def check_layer_3a(event: Dict) -> Optional[str]:
    """Return reason if event triggers Layer 3a canonical-write trip."""
    action = event.get("action", "")
    if any(action.startswith(p) for p in _LAYER_3A_ACTION_PREFIXES):
        return f"canonical_event:{action}"
    reason_code = event.get("reason_code", "")
    if reason_code in _LAYER_3A_REASON_CODES:
        return f"reason_code:{reason_code}"
    return None


def check_layer_3b(event: Dict, policy: List[Dict]) -> Optional[str]:
    """Return reason if event triggers Layer 3b staging-violation trip."""
    if event.get("action") != _STAGING_ACTION:
        return None
    wave_id = event.get("wave_id", "")
    archetype = event.get("archetype", "")
    session_id = event.get("session_id", "")
    path = event.get("path", "")
    if not path.startswith(".claude/plans/PLAN-084/"):
        return None  # only enforce within PLAN-084 staging area
    allowed, reason = match_staging_policy(policy, wave_id, archetype, session_id, path)
    if not allowed:
        return f"staging_violation:{wave_id}/{archetype} → {path} ({reason})"
    return None


def write_sentinel(plan_dir: Path, name: str, reason: str) -> None:
    sentinel_path = plan_dir / name
    sentinel_path.write_text(
        f"WAVE ABORTED\nreason: {reason}\nts: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-log", required=True, type=Path)
    parser.add_argument("--plan-dir", required=True, type=Path)
    parser.add_argument("--staging-policy", required=True, type=Path)
    parser.add_argument("--start-iso", required=True)
    parser.add_argument("--end-iso", required=True)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--state-file", type=Path, default=None)
    args = parser.parse_args()

    if not args.audit_log.exists():
        print(f"audit-log not found: {args.audit_log}", file=sys.stderr)
        return 3
    if not args.plan_dir.exists():
        print(f"plan-dir not found: {args.plan_dir}", file=sys.stderr)
        return 3
    if not args.staging_policy.exists():
        print(f"staging-policy not found: {args.staging_policy}", file=sys.stderr)
        return 3

    policy = parse_yaml_minimal(args.staging_policy)
    if not policy:
        print(f"staging-policy parsed 0 entries — check format", file=sys.stderr)
        return 3

    # Seek to end of audit-log at start (only watch new events from start_iso)
    state_path = args.state_file or args.plan_dir / "wave-readonly-monitor.state"
    if state_path.exists():
        last_offset = int(state_path.read_text().strip() or "0")
    else:
        last_offset = args.audit_log.stat().st_size

    halt = False
    sigterm_received = False

    def _on_sigterm(signum, frame):  # noqa: ARG001
        nonlocal sigterm_received
        sigterm_received = True

    signal.signal(signal.SIGTERM, _on_sigterm)
    signal.signal(signal.SIGINT, _on_sigterm)

    start_ts = time.time()
    print(f"[monitor] window {args.start_iso} → {args.end_iso}; polling {args.poll_interval}s", flush=True)

    end_epoch = None
    try:
        # Parse end-iso as epoch
        from datetime import datetime, timezone
        end_dt = datetime.strptime(args.end_iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        end_epoch = end_dt.timestamp()
    except Exception:
        pass

    while not sigterm_received and not halt:
        events, last_offset = read_new_events(args.audit_log, last_offset)
        state_path.write_text(str(last_offset))
        for event in events:
            event_ts = event.get("ts", "")
            if event_ts < args.start_iso:
                continue
            if event_ts > args.end_iso:
                continue
            reason3a = check_layer_3a(event)
            if reason3a:
                write_sentinel(args.plan_dir, "WAVE-ABORTED-CANONICAL-WRITE", reason3a)
                print(f"[monitor] Layer 3a trip: {reason3a}", flush=True)
                return 1
            reason3b = check_layer_3b(event, policy)
            if reason3b:
                write_sentinel(args.plan_dir, "WAVE-ABORTED-STAGING-VIOLATION", reason3b)
                print(f"[monitor] Layer 3b trip: {reason3b}", flush=True)
                return 2
        if end_epoch and time.time() > end_epoch:
            print(f"[monitor] window closed cleanly", flush=True)
            return 0
        time.sleep(args.poll_interval)

    print(f"[monitor] received SIGTERM, exiting cleanly", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
