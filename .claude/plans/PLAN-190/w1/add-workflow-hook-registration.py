#!/usr/bin/env python3
"""PLAN-190 W1 — derivator: register ``check_workflow_launch.py`` on the
``Workflow`` tool in the framework's own settings and in the base template
that ``upgrade.sh`` delivers to consumers, then regenerate the derived
``user`` template.

Study/ceremony artifact: it is run against a DISPOSABLE worktree (shadow) and
its output diff is the pack payload; the live tree only changes through the
Owner-signed ceremony. Idempotent: a second run is a no-op (rc 0, "already
registered"). Anchor-exact: appends ONE entry to ``hooks.PreToolUse`` and ONE
to ``hooks.PostToolUse`` (matcher ``Workflow``); refuses (rc 3) if an entry
with that matcher and command already exists with a different shape.

Usage: ``python3 add-workflow-hook-registration.py <repo-root> [--check]``
Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HOOK_BASENAME = "check_workflow_launch.py"
COMMAND = "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" " + HOOK_BASENAME

PRE_ENTRY: Dict[str, Any] = {
    "_comment": (
        "PLAN-190 W1: Workflow launch ledger + resume guard. Records script sha256 + LITERAL args + "
        "code revision under <state-dir>/launches/ BEFORE dispatch; blocks a resumeFromRunId whose script "
        "or args differ from the bound manifest (recovery: `ceo-launches.py relaunch <run>`; override "
        "CEO_WORKFLOW_RESUME_FORCE=1, recorded; kill-switch CEO_WORKFLOW_LEDGER=0). Fail-open on infrastructure."
    ),
    "matcher": "Workflow",
    "hooks": [{"type": "command", "command": COMMAND, "timeout": 5, "statusMessage": "Recording Workflow launch..."}],
}
POST_ENTRY: Dict[str, Any] = {
    "_comment": (
        "PLAN-190 W1: binds the run id (wf_<id>) the runner returned to the pending launch manifest "
        "(by tool_use_id, else latest unbound in the session). Silent; fail-open."
    ),
    "matcher": "Workflow",
    "hooks": [{"type": "command", "command": COMMAND, "timeout": 5, "statusMessage": "Binding Workflow run id..."}],
}


def _targets(root: Path) -> List[Path]:
    return [
        root / ".claude" / "settings.json",
        root / "templates" / "settings" / "settings.base.json",
    ]


def _find(entries: List[Dict[str, Any]]) -> List[int]:
    return [i for i, e in enumerate(entries) if e.get("matcher") == "Workflow" and any(h.get("command") == COMMAND for h in e.get("hooks", []))]


def apply(path: Path, check_only: bool) -> Tuple[str, bool]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    hooks = data.setdefault("hooks", {})
    changed = False
    for event, entry in (("PreToolUse", PRE_ENTRY), ("PostToolUse", POST_ENTRY)):
        entries = hooks.setdefault(event, [])
        idx = _find(entries)
        if idx:
            if entries[idx[0]] != entry:
                return ("%s: %s has a Workflow/%s entry with a DIFFERENT shape — refusing" % (path, event, HOOK_BASENAME), False)
            continue
        entries.append(entry)
        changed = True
    if changed and not check_only:
        # preserve the file's existing indentation style (2 spaces is the repo convention)
        out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        path.write_text(out, encoding="utf-8")
    return ("%s: %s" % (path.name, "registered" if changed else "already registered"), True)


def main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    root = Path(argv[0]).resolve()
    check_only = "--check" in argv[1:]
    if not (root / "VERSION").is_file() or not (root / ".claude").is_dir():
        print("not a framework checkout: %s" % root, file=sys.stderr)
        return 2
    rc = 0
    for p in _targets(root):
        if not p.is_file():
            print("missing: %s" % p, file=sys.stderr)
            return 2
        msg, ok = apply(p, check_only)
        print(msg)
        if not ok:
            rc = 3
    # The user profile is DERIVED from the base by subtraction; every hook that can block in
    # that profile must be named in `_derivation.blocking_inclusions` WITH its route (S330
    # criterion (a)). The derivation spec lives inside the user template itself.
    user_tpl = root / "templates" / "settings" / "settings.user.json"
    if rc == 0 and user_tpl.is_file():
        data = json.loads(user_tpl.read_text(encoding="utf-8"))
        bi = data.setdefault("_derivation", {}).setdefault("blocking_inclusions", [])
        if not any(e.get("hook") == HOOK_BASENAME for e in bi):
            if not check_only:
                bi.append({
                    "hook": HOOK_BASENAME,
                    "route": "CEO_WORKFLOW_LEDGER=0 desliga o hook; CEO_WORKFLOW_RESUME_GUARD=0 poe o guard em advisory mantendo o ledger; em sessao, `ceo-launches.py force <run> --reason ...` (token one-shot, registrado) ou CEO_WORKFLOW_RESUME_FORCE=1 no ambiente do harness",
                    "evidence": ".claude/hooks/_lib/launch_ledger.py decide_pre — bloqueia SO retomada (resumeFromRunId) com args diferentes do manifesto vinculado por tool_use_id/manual; script diferente e advisory por padrao; hash indisponivel e inconclusivo (nunca bloqueia); falha de infraestrutura devolve {}",
                })
                user_tpl.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("settings.user.json: blocking_inclusions entry added")
            else:
                print("settings.user.json: blocking_inclusions entry would be added")
        else:
            print("settings.user.json: blocking_inclusions already present")
    if rc == 0 and not check_only:
        gen = root / ".claude" / "scripts" / "gen-settings-user-template.py"
        r = subprocess.run([sys.executable, str(gen), "--write", "--repo-root", str(root)], capture_output=True, text=True)
        print("gen-settings-user-template --write rc=%d %s" % (r.returncode, (r.stdout or r.stderr).strip()[:200]))
        if r.returncode != 0:
            rc = 4
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
