#!/usr/bin/env python3
"""PLAN-134 W1 #5 (E5-F2) — closeout-guard Stop hook: closeout + Owner-GPG-pending reminder.

ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing files / timeouts → stderr
breadcrumb + emit {}). NEVER blocks. On Stop it cheaply detects, on a 2s internal time budget:

  (i)  substantive session work — git HEAD differs from the session-start HEAD when one was
       recorded (CEO_SESSION_START_HEAD env or `.claude/state/session-start-head`); fallback:
       any `.claude/plans/*.md` modified more recently than CLAUDE.md (CLAUDE.md is only
       touched at the closeout ceremony, so a fresh closeout silences the reminder);
  (ii) a pending Owner ceremony — executable `finish-*.sh` under
       `.claude/plans/PLAN-*/staged/**` or `scripts/local/` newer than the last git tag.

(i) → systemMessage reminding the closeout rite (CLAUDE.md §Current Work + CHANGELOG + memory).
(ii) → systemMessage listing the pending finish script path(s). Both combined when both fire.

NO audit actions are emitted (closed-enum _KNOWN_ACTIONS discipline — adding one requires BOTH
_KNOWN_ACTIONS and SPEC; this hook uses stderr breadcrumbs + systemMessage only).

Kill-switch: CEO_CLOSEOUT_GUARD=0. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional

TIME_BUDGET_S = 2.0


def _git(args: List[str], cwd: str) -> str:
    """stdout on success, '' on any failure (fail-open)."""
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=2)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def _session_start_head(cwd: str) -> str:
    """Session-start HEAD if recorded (env wins over state file); '' when unavailable."""
    env = os.environ.get("CEO_SESSION_START_HEAD", "").strip()
    if env:
        return env
    try:
        with open(os.path.join(cwd, ".claude", "state", "session-start-head"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _did_substantive_work(cwd: str, deadline: float) -> bool:
    start = _session_start_head(cwd)
    if start:
        head = _git(["rev-parse", "HEAD"], cwd)
        return bool(head) and head != start
    # Fallback: any plan file newer than CLAUDE.md (closeout touches CLAUDE.md last).
    try:
        claude_mtime = os.path.getmtime(os.path.join(cwd, "CLAUDE.md"))
    except OSError:
        return False
    for path in glob.glob(os.path.join(cwd, ".claude", "plans", "*.md")):
        if time.monotonic() > deadline:
            return False  # budget blown → fail toward silence, never toward noise
        try:
            if os.path.getmtime(path) > claude_mtime:
                return True
        except OSError:
            continue
    return False


def _last_tag_time(cwd: str) -> float:
    """Creation time (unix) of the newest tag; 0.0 when no tags / no git (everything counts)."""
    out = _git(["for-each-ref", "--sort=-creatordate", "--count=1",
                "--format=%(creatordate:unix)", "refs/tags"], cwd)
    try:
        return float(out)
    except ValueError:
        return 0.0


def _sanitize_path(rel: str) -> str:
    """Disk-sourced strings rendered into systemMessage are an injection
    surface (Codex S228 P0): a filename containing newlines/control chars
    could forge extra system-message lines. Keep printable ASCII only,
    replace everything else, clamp length."""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in rel)
    return cleaned[:120]


def _pending_finish_scripts(cwd: str, deadline: float) -> List[str]:
    """Executable finish-*.sh newer than the last git tag, repo-relative,
    sorted, sanitized for rendering, bounded to 5 entries."""
    tag_time = _last_tag_time(cwd)
    found = set()
    patterns = (
        os.path.join(cwd, ".claude", "plans", "PLAN-*", "staged", "**", "finish-*.sh"),
        os.path.join(cwd, "scripts", "local", "finish-*.sh"),
    )
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            if time.monotonic() > deadline:
                break
            try:
                if os.access(path, os.X_OK) and os.path.getmtime(path) > tag_time:
                    found.add(_sanitize_path(os.path.relpath(path, cwd)))
            except OSError:
                continue
    return sorted(found)[:5]


def gate(cwd: Optional[str] = None) -> Dict:
    if os.environ.get("CEO_CLOSEOUT_GUARD", "1") == "0":
        return {}
    deadline = time.monotonic() + TIME_BUDGET_S
    cwd = os.path.realpath(cwd or os.getcwd())
    messages: List[str] = []
    if _did_substantive_work(cwd, deadline):
        messages.append(
            "Closeout reminder: this session did substantive work — run the closeout ceremony "
            "before ending (CLAUDE.md §Current Work + CHANGELOG entry + memory update)."
        )
    pending = _pending_finish_scripts(cwd, deadline)
    if pending:
        messages.append("Owner GPG ceremony pending: " + ", ".join(pending))
    if not messages:
        return {}
    return {"systemMessage": "\n".join(messages)}


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: parse error is an infra condition → breadcrumb + schema-compliant allow.
        sys.stderr.write("# check_closeout_guard fail-open (stdin): %s\n" % str(exc)[:120])
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input.get("cwd"))))
    except Exception as exc:
        sys.stderr.write("# check_closeout_guard fail-open: %s\n" % str(exc)[:120])
        print("{}")


if __name__ == "__main__":
    main()
