#!/usr/bin/env python3
"""Chain-scan BACKSTOPS for the two ADVISORY Codex rails (PLAN-155 Wave 6).

## What this is (and is NOT)

The Codex capability matrix has exactly two ADVISORY rails:

1. **Spawn governance** — `SubagentStart` injects the spawn-protocol
   `additionalContext`, but codex 0.139 parses `continue:false` without
   stopping the subagent (``PLAN-155/artifacts/subagentstart-transcript.md``).
2. **Config tripwire** — codex has no `ConfigChange` event, so the
   settings/kill-switch hash re-check degrades to boot-time only
   (`SessionStart`).

This script is a read-only chain-scan that BACKSTOPS both. It NEVER makes
them ENFORCED — enforcement of a Stop/PreToolUse deny is upstream harness
behavior, not something a log scan can create. It exists to make the
ADVISORY rails' silence auditable: a fail-open rail that went quiet looks
identical to a healthy one at runtime (the S254 dead-gate class), and this
scan is the RED-on-absence detector for that.

## The two checks

**A. Boot-breadcrumb per session window (config-tripwire backstop) — RED.**
Every session that shows tool activity in the chain MUST also carry a
`session_start` boot breadcrumb (the SessionStart hash re-check ran and was
recorded). A session with tool records but NO `session_start` is RED-on-
absence: the boot tripwire did not run / was not recorded = silent fail-open.

**B. Spawn instrumentation cross-reference (spawn-governance backstop) —
ADVISORY.** For each spawn-class tool record (`Task`/`spawn_agent`) in a
session, assert a matching `SubagentStart` entry exists in the local
lifecycle sidecar (`subagent-lifecycle.json`, written by
check_subagent_start.py) — proving the SubagentStart hook fired and thus the
protocol `additionalContext` was injected. A spawn with no SubagentStart
record is flagged as a possible **Bash-bypassed spawn** (`claude -p` /
`codex exec` smuggled through the `^Bash$` matcher) — advisory, because the
metadata-only chain cannot see command content (named residual).

## Exit semantics (CI / pre-push teeth)

- Default: exit 1 if any **A** (RED) finding, else 0. **B** findings are
  advisory and never fail the run on their own.
- `--advisory-only`: never exit non-zero (report only).
- `--json`: machine-readable findings on stdout.

Renders audit-log + sidecar content as UNTRUSTED DATA (never executes it).
Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Actions that count as "tool activity" for a session window (codex path).
_TOOL_ACTIVITY_ACTIONS = frozenset(
    {"codex_tool_recorded", "codex_turn_ended", "agent_spawn"}
)
_BOOT_ACTIONS = frozenset({"session_start"})
# Spawn-class tool enums (codex host adapter aliases spawn_agent -> Task).
_SPAWN_TOOL_ENUMS = frozenset({"Task", "spawn_agent"})


# ---------------------------------------------------------------------------
# path resolution (mirror audit_log.audit_paths + check_subagent_start dirs)
# ---------------------------------------------------------------------------

def _audit_log_path(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    p = os.environ.get("CEO_AUDIT_LOG_PATH")
    if p:
        return Path(p)
    d = os.environ.get("CEO_AUDIT_LOG_DIR")
    if d:
        return Path(d) / "audit-log.jsonl"
    home = os.environ.get("HOME") or "/tmp"
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _lifecycle_sidecar_path() -> Path:
    override = os.environ.get("CEO_SUBAGENT_LIFECYCLE_STATE_DIR")
    if override:
        return Path(override) / "subagent-lifecycle.json"
    d = os.environ.get("CEO_AUDIT_LOG_DIR")
    if d:
        return Path(d) / "subagent-lifecycle.json"
    home = os.environ.get("HOME") or "/tmp"
    return (
        Path(home)
        / ".claude"
        / "projects"
        / "ceo-orchestration"
        / "state"
        / "subagent-lifecycle.json"
    )


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------

def read_chain(log_path: Path) -> List[Dict[str, Any]]:
    """Read audit-log JSONL into a list of dict entries. Untrusted data."""
    if not log_path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except Exception:
        return out
    return out


def _lifecycle_session_ids(sidecar_path: Path) -> Set[str]:
    """Session ids that fired at least one SubagentStart (from the sidecar).

    The sidecar stores session_id per recorded start (clamped). We only need
    the SET of sessions that produced any SubagentStart record."""
    if not sidecar_path.is_file():
        return set()
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if not isinstance(data, dict):
        return set()
    entries = data.get("entries")
    if not isinstance(entries, dict):
        return set()
    out: Set[str] = set()
    for val in entries.values():
        if isinstance(val, dict):
            sid = val.get("session_id")
            if isinstance(sid, str) and sid:
                out.add(sid)
    return out


# ---------------------------------------------------------------------------
# scans
# ---------------------------------------------------------------------------

def scan(
    entries: List[Dict[str, Any]],
    subagent_sessions: Set[str],
    session_filter: Optional[str] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return {"red": [...], "advisory": [...]} findings."""
    # Group by session.
    by_session: Dict[str, Dict[str, Any]] = {}
    for e in entries:
        sid = str(e.get("session_id") or "")
        if not sid:
            continue
        if session_filter and sid != session_filter:
            continue
        rec = by_session.setdefault(
            sid, {"has_boot": False, "has_activity": False, "spawns": 0}
        )
        action = str(e.get("action") or "")
        if action in _BOOT_ACTIONS:
            rec["has_boot"] = True
        if action in _TOOL_ACTIVITY_ACTIONS:
            rec["has_activity"] = True
        if action == "codex_tool_recorded":
            tool_enum = str(e.get("tool_name_enum") or e.get("tool") or "")
            if tool_enum in _SPAWN_TOOL_ENUMS:
                rec["spawns"] = int(rec["spawns"]) + 1

    red: List[Dict[str, Any]] = []
    advisory: List[Dict[str, Any]] = []

    for sid, rec in sorted(by_session.items()):
        # A. Config-tripwire backstop: activity without a boot breadcrumb.
        if rec["has_activity"] and not rec["has_boot"]:
            red.append(
                {
                    "check": "boot_breadcrumb_absence",
                    "rail": "config-tripwire (ADVISORY)",
                    "session_id": sid,
                    "detail": (
                        "session has tool activity but NO session_start boot "
                        "breadcrumb -- the boot-time config/kill-switch hash "
                        "re-check did not run or was not recorded (silent "
                        "fail-open, RED-on-absence)"
                    ),
                }
            )
        # B. Spawn-governance backstop: spawn without a SubagentStart record.
        if int(rec["spawns"]) > 0 and sid not in subagent_sessions:
            advisory.append(
                {
                    "check": "spawn_without_subagent_start",
                    "rail": "spawn-governance (ADVISORY)",
                    "session_id": sid,
                    "detail": (
                        "%d spawn-class tool record(s) but no SubagentStart "
                        "lifecycle entry for this session -- possible "
                        "Bash-bypassed spawn (claude -p / codex exec); the "
                        "protocol additionalContext injection cannot be "
                        "confirmed. ADVISORY (metadata-only chain cannot see "
                        "command content)." % int(rec["spawns"])
                    ),
                }
            )

    return {"red": red, "advisory": advisory}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chain-scan backstops for the two ADVISORY Codex rails."
    )
    parser.add_argument("--log", default=None, help="audit-log.jsonl path")
    parser.add_argument("--session", default=None, help="limit to one session id")
    parser.add_argument(
        "--advisory-only",
        action="store_true",
        help="never exit non-zero (report only)",
    )
    parser.add_argument("--json", action="store_true", help="machine output")
    args = parser.parse_args(argv)

    log_path = _audit_log_path(args.log)
    entries = read_chain(log_path)
    subagent_sessions = _lifecycle_session_ids(_lifecycle_sidecar_path())

    findings = scan(entries, subagent_sessions, session_filter=args.session)
    red = findings["red"]
    advisory = findings["advisory"]

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "log": str(log_path),
                    "red": red,
                    "advisory": advisory,
                    "red_count": len(red),
                    "advisory_count": len(advisory),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            "codex-advisory-teeth: scanned %s (%d entries)\n"
            % (log_path, len(entries))
        )
        if not red and not advisory:
            sys.stdout.write("  OK: no RED or advisory findings.\n")
        for f in red:
            sys.stdout.write(
                "  RED   [%s] session=%s: %s\n"
                % (f["check"], f["session_id"], f["detail"])
            )
        for f in advisory:
            sys.stdout.write(
                "  ADV   [%s] session=%s: %s\n"
                % (f["check"], f["session_id"], f["detail"])
            )

    if args.advisory_only:
        return 0
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
