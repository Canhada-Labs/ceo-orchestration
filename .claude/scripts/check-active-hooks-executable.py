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
- 2 — settings.json malformed / unreadable / not a regular file, or a hook file
  whose stat fails for a reason other than absence
"""
from __future__ import annotations

import json
import os
import re
import stat
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

# Hook type -> required string fields, the same table as the loader replica in
# tests/test_settings_guard_loadability.py (``_TYPE_FIELDS``; parity is asserted by
# test_fu144_required_fields_of_each_type_follow_the_replica_table).
_REQUIRED_FIELDS = {
    "command": ("command",),
    "prompt": ("prompt",),
    "agent": ("prompt",),
    "http": ("url",),
    "mcp_tool": ("server", "tool"),
}


def _refuse_constant(name: str):
    """parse_constant: NaN/Infinity are not JSON (JSON.parse rejects them), so a
    settings file carrying them is malformed — exit 2, never read as valid."""
    raise ValueError(f"non-standard JSON constant {name}")


def _settings_absent(settings_path: Path) -> bool:
    """True only for real absence. Anything else that is not a regular file (a
    directory, a dangling symlink, a FIFO, a forbidden parent) is an input this gate
    cannot read: exit 2 named, never a silent skip and never a blocking read."""
    try:
        os.lstat(settings_path)
    except FileNotFoundError:
        return True
    except (OSError, ValueError) as exc:
        print(f"::error::cannot stat {settings_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
    try:
        mode = os.stat(settings_path).st_mode
    except (OSError, ValueError) as exc:
        print(f"::error::cannot stat {settings_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not stat.S_ISREG(mode):
        print(f"::error::cannot parse {settings_path}: not a regular file", file=sys.stderr)
        sys.exit(2)
    return False


def _iter_hook_paths(settings_path: Path) -> Iterable[str]:
    if _settings_absent(settings_path):
        return
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"), parse_constant=_refuse_constant)
    except (OSError, ValueError, RecursionError) as exc:  # ValueError: + UnicodeDecodeError
        print(f"::error::cannot parse {settings_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict):
        # null / [] / 1 / "s" / true used to raise AttributeError below, which the
        # delegating check_harness_config.py downgraded to a WARN — rc 0.
        print(f"::error::cannot parse {settings_path}: top-level JSON is not an object", file=sys.stderr)
        sys.exit(2)
    # Layer 1 — the shape, by FORM, before any walk: a malformed `hooks` used to be
    # skipped (rc 0) or to raise mid-walk (WARN-green through the delegation).
    bad = _hooks_shape_error(data)
    if bad:
        print(f"::error::malformed settings: {bad} ({settings_path})", file=sys.stderr)
        sys.exit(2)
    # Layer 2 — any exception while walking the settings is INPUT this gate cannot
    # consume (never infrastructure): exit 2 named, so a form layer 1 does not
    # foresee closes too.
    found: List[str] = []
    try:
        for entries in data.get("hooks", {}).values():
            for entry in entries:
                for hook in entry["hooks"]:
                    # The loader discards `command` on any other type (item 6a.2).
                    if hook["type"] != "command":
                        continue
                    cmd = hook["command"]
                    found +=[m.group(1) for m in _PY_HOOK_DIRECT_RE.finditer(cmd)]
                    # Bare hook script — resolve to .claude/hooks/<name>
                    found += [f".claude/hooks/{m.group(1)}" for m in _PY_HOOK_VIA_SHIM_RE.finditer(cmd)]
    except Exception as exc:
        print(f"::error::malformed settings: {type(exc).__name__} while reading {settings_path}: {exc}",
              file=sys.stderr)
        sys.exit(2)
    yield from found


def _hooks_shape_error(data: dict) -> str:
    """'<JSON path> <expected type>' of the first deviation of ``hooks`` from the
    settings shape, or '' — settings without a ``hooks`` key are valid (0 refs)."""
    if "hooks" not in data:
        return ""
    if not isinstance(data["hooks"], dict):
        return "hooks: expected object"
    for event, entries in data["hooks"].items():
        at = f"hooks[{json.dumps(event)[:80]}]"
        if not isinstance(entries, list):
            return f"{at}: expected array"
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                return f"{at}[{i}]: expected object"
            if not isinstance(entry.get("hooks"), list):
                return f"{at}[{i}].hooks: expected array"
            if "matcher" in entry and not isinstance(entry["matcher"], str):
                return f"{at}[{i}].matcher: expected string"
            for j, hook in enumerate(entry["hooks"]):
                if not isinstance(hook, dict):
                    return f"{at}[{i}].hooks[{j}]: expected object"
                bad = _hook_shape_error(hook)
                if bad:
                    return f"{at}[{i}].hooks[{j}].{bad}"
    return ""


def _hook_shape_error(hook: dict) -> str:
    """'<field>: <expected>' of the first deviation of one hook entry, or ''."""
    if "type" not in hook:
        return "type: required"
    hook_type = hook["type"]
    if not isinstance(hook_type, str):
        return "type: expected string"
    if hook_type not in _REQUIRED_FIELDS:
        return f"type: unknown hook type {json.dumps(hook_type)[:80]}"
    for field in _REQUIRED_FIELDS[hook_type]:
        if not isinstance(hook.get(field), str):
            return f"{field}: expected string"
    return ""


def _hook_problem(hook_rel: str) -> str:
    """'missing', 'not_exec' or ''. A stat that fails for any other reason than
    absence raises: it is input this gate cannot consume (main() names it, exit 2)."""
    full = REPO_ROOT / hook_rel
    try:
        mode = os.stat(full).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    if not stat.S_ISREG(mode):
        return "missing"
    return "" if os.access(full, os.X_OK) else "not_exec"


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
            try:
                problem = _hook_problem(hook_rel)
            except (OSError, ValueError) as exc:
                print(f"::error::cannot stat hook file {hook_rel} ({settings_path.name}): "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)
                return 2
            if problem == "missing":
                missing.append(f"{settings_path.name}: {hook_rel}")
            elif problem == "not_exec":
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
