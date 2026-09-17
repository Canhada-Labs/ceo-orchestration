#!/usr/bin/env python3
"""PLAN-190 W1 — derivator: register ``check_workflow_launch.py`` on the
``Workflow`` tool in the framework's own settings and in the base template
that ``upgrade.sh`` delivers to consumers, then regenerate the derived
``user`` template.

Study/ceremony artifact: it is run against a DISPOSABLE worktree (shadow) and
its output diff is the pack payload; the live tree only changes through the
Owner-signed ceremony. Idempotent: a second run is a no-op (rc 0, "already
registered"). Upsert by identity: ONE entry in ``hooks.PreToolUse`` and ONE in
``hooks.PostToolUse`` whose matcher is ``Workflow`` and whose command runs this
hook - appended when absent, rewritten IN PLACE when present with another shape
(so a revised comment re-derives to the same bytes on a fresh tree); refuses
(rc 3) only when more than one such entry exists. The ``user`` template's
``_derivation.blocking_inclusions`` entry for this hook is upserted the same way.

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
BLOCKING_INCLUSION: Dict[str, Any] = {
    "hook": "check_workflow_launch.py",
    "route": "CEO_WORKFLOW_LEDGER=0 desliga o hook; CEO_WORKFLOW_RESUME_GUARD=0 poe o guard em advisory mantendo o ledger; na propria chamada, description comecando com 'CEO_WORKFLOW_RESUME_FORCE: <motivo>' libera aquela chamada (registrado e anunciado); ou CEO_WORKFLOW_RESUME_FORCE=1 no ambiente do harness",
    "evidence": ".claude/hooks/_lib/launch_ledger.py _guard - bloqueia SO retomada (resumeFromRunId) com args diferentes do manifesto vinculado por tool_use_id/manual e VALIDADO (manifest_problem); script diferente e advisory por padrao; com args iguais, hash indisponivel e inconclusivo; registro inconsistente ou excecao no guard sao inconclusivos (nunca bloqueiam); args diferentes seguem bloqueando; falha de infraestrutura devolve {}",
}
COMMAND = "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" " + HOOK_BASENAME

PRE_ENTRY: Dict[str, Any] = {
    "_comment": (
        "PLAN-190 W1: Workflow launch ledger + resume guard. Records script sha256 + snapshot, LITERAL args "
        "and code revision under <state-dir>/launches/ BEFORE dispatch; blocks a resumeFromRunId whose args differ "
        "from the strongly bound, validated manifest (script change: advisory unless CEO_WORKFLOW_SCRIPT_GUARD=enforce). "
        "Recovery: `ceo-launches.py relaunch <run>`. Override, recorded: a call description starting with "
        "'CEO_WORKFLOW_RESUME_FORCE: <why>' or CEO_WORKFLOW_RESUME_FORCE=1; advisory CEO_WORKFLOW_RESUME_GUARD=0; "
        "off CEO_WORKFLOW_LEDGER=0. Fail-open on infrastructure."
    ),
    "matcher": "Workflow",
    "hooks": [{"type": "command", "command": COMMAND, "timeout": 5, "statusMessage": "Recording Workflow launch..."}],
}
POST_ENTRY: Dict[str, Any] = {
    "_comment": (
        "PLAN-190 W1: binds the run id (wf_<id>) the runner returned to its launch manifest "
        "(by tool_use_id; without one, only when exactly one non-blocked unbound launch exists in the session; "
        "anything else is an orphan line). Silent; fail-open."
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
        if len(idx) > 1:
            return ("%s: %s has %d Workflow/%s entries - refusing" % (path, event, len(idx), HOOK_BASENAME), False)
        if idx:
            if entries[idx[0]] != entry:
                entries[idx[0]] = entry
                changed = True
            continue
        entries.append(entry)
        changed = True
    if changed and not check_only:
        out = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        path.write_text(out, encoding="utf-8")
    state = ("would change" if check_only else "registered/updated") if changed else "already registered"
    return ("%s: %s" % (path.name, state), True)


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
        mine = [i for i, e in enumerate(bi) if e.get("hook") == HOOK_BASENAME]
        if len(mine) > 1:
            print("settings.user.json: %d blocking_inclusions entries for the hook - refusing" % len(mine), file=sys.stderr)
            return 3
        if mine and bi[mine[0]] == BLOCKING_INCLUSION:
            print("settings.user.json: blocking_inclusions already present")
        elif check_only:
            print("settings.user.json: blocking_inclusions entry would be added/updated")
        else:
            if mine:
                bi[mine[0]] = BLOCKING_INCLUSION
            else:
                bi.append(BLOCKING_INCLUSION)
            user_tpl.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("settings.user.json: blocking_inclusions entry added/updated")
    if rc == 0 and not check_only:
        gen = root / ".claude" / "scripts" / "gen-settings-user-template.py"
        r = subprocess.run([sys.executable, str(gen), "--write", "--repo-root", str(root)], capture_output=True, text=True)
        print("gen-settings-user-template --write rc=%d %s" % (r.returncode, (r.stdout or r.stderr).strip()[:200]))
        if r.returncode != 0:
            rc = 4
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
