#!/usr/bin/env python3
"""Verify every Python hook activated in settings.json is executable.

Closes Session 75 Codex Finding 9: the prior validate.yml step
hardcoded 4 hook files (`check_agent_spawn.py`, `audit_log.py`,
`check_bash_safety.py`, `check_plan_edit.py`) while
`.claude/settings.json` activates ~26 hooks total. The remaining 22
were unvalidated — a hook missing exec-bit silently fails open in
Claude Code's hook chain.

Strategy: parse the dogfood `.claude/settings.json` and the template
`templates/settings/settings.base.json`, extract every hook command,
resolve the Python script path (commonly invoked via the
`_python-hook.sh` shim), then assert each script exists and is
executable.

Exit codes:
- 0 — all active hooks present + executable
- 1 — one or more hooks missing or not executable
- 2 — settings.json malformed / unreadable
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SETTINGS_FILES = (
    REPO_ROOT / ".claude" / "settings.json",
    REPO_ROOT / "templates" / "settings" / "settings.base.json",
)

# Hook command commonly looks like:
#   bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" check_X.py
#   python3 .claude/hooks/check_X.py
#   bash .claude/hooks/_python-hook.sh check_X.py
# We capture both:
#   - direct paths matching `.claude/hooks/*.py`
#   - bare hook script names that follow `_python-hook.sh`
_PY_HOOK_DIRECT_RE = re.compile(r"(\.claude/hooks/[A-Za-z0-9_./-]+\.py)")
_PY_HOOK_VIA_SHIM_RE = re.compile(r"_python-hook\.sh[\"']?\s+([A-Za-z0-9_/-]+\.py)")


def _iter_hook_paths(settings_path: Path) -> Iterable[str]:
    if not settings_path.is_file():
        return
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error::cannot parse {settings_path}: {exc}", file=sys.stderr)
        sys.exit(2)
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    for matcher_block in hooks.values():
        if not isinstance(matcher_block, list):
            continue
        for entry in matcher_block:
            if not isinstance(entry, dict):
                continue
            for hook in entry.get("hooks", []) or []:
                if not isinstance(hook, dict):
                    continue
                cmd = hook.get("command", "") or ""
                for match in _PY_HOOK_DIRECT_RE.finditer(cmd):
                    yield match.group(1)
                for match in _PY_HOOK_VIA_SHIM_RE.finditer(cmd):
                    name = match.group(1)
                    # Bare hook script — resolve to .claude/hooks/<name>
                    yield f".claude/hooks/{name}"


def main() -> int:
    seen: Set[Tuple[str, str]] = set()
    missing: List[str] = []
    not_exec: List[str] = []

    for settings_path in SETTINGS_FILES:
        for hook_rel in _iter_hook_paths(settings_path):
            key = (settings_path.name, hook_rel)
            if key in seen:
                continue
            seen.add(key)
            full = (REPO_ROOT / hook_rel).resolve()
            if not full.is_file():
                missing.append(f"{settings_path.name}: {hook_rel}")
                continue
            if not os.access(full, os.X_OK):
                not_exec.append(f"{settings_path.name}: {hook_rel}")

    if missing or not_exec:
        if missing:
            print("MISSING hook files:")
            for m in missing:
                print(f"  - {m}")
        if not_exec:
            print("NOT EXECUTABLE hook files:")
            for n in not_exec:
                print(f"  - {n}")
        print()
        print("Run: chmod +x <file>")
        return 1

    if not seen:
        print("WARN: no hook references found in settings — possible parse drift", file=sys.stderr)

    print(f"OK: {len(seen)} active hook reference(s) across "
          f"{sum(1 for s in SETTINGS_FILES if s.is_file())} settings file(s) "
          f"are present and executable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
