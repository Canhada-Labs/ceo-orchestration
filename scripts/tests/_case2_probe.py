#!/usr/bin/env python3
"""PLAN-155 Wave 5 — case-2 runtime-resolution probe for the INSTALLED bundle.

Given an installed target dir (argv[1]) that has a rendered
``.codex/hooks.json`` + a real ``.claude/hooks/`` tree, assert — the PLAN-153
Wave E lesson, now on the installed (post-substitution) file — that EVERY
registered command resolves at the harness's real runtime resolution:

  * the ``env`` argv-split form (codex argv-splits; a bare ``K=V prog`` prefix
    would not work);
  * ``CEO_HOOK_ADAPTER=codex`` present in the env prefix;
  * ``CLAUDE_PROJECT_DIR=`` present (codex never sets it — S265 P2#5);
  * the shim is an ABSOLUTE path, exists, and is executable;
  * the hook script is a BARE name (resolved by the shim's dirname logic),
    and the file exists under ``<target>/.claude/hooks/``;
  * running the command as a SUBPROCESS from a FOREIGN cwd with a benign
    codex-wire envelope on stdin does NOT print the shim's ERROR breadcrumb
    (fail-open ``{}`` on a missing hook would be the S254 vacuous green), and
    exits 0 or 2.

Exit 0 = all commands OK; exit 1 = a failure (message on stderr). Stdlib only,
py>=3.9, ``from __future__ import annotations``.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple


def _iter_commands(doc: dict):
    for event, groups in doc.get("hooks", {}).items():
        for group in groups:
            for entry in group.get("hooks", []):
                yield event, entry.get("command", "")


_ENVELOPES: Dict[str, dict] = {
    "PreToolUse": {"tool_name": "Bash", "tool_input": {"command": "echo ok"},
                   "tool_use_id": "call_probe1"},
    "PostToolUse": {"tool_name": "Bash", "tool_input": {"command": "echo ok"},
                    "tool_use_id": "call_probe1", "tool_response": "ok\n"},
    "SessionStart": {"source": "startup"},
    "UserPromptSubmit": {"prompt": "hello"},
    "Stop": {"stop_hook_active": False, "last_assistant_message": "done"},
    "SubagentStart": {"agent_id": "agent-1", "agent_type": "default"},
}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _case2_probe.py <installed-target-dir>", file=sys.stderr)
        return 1
    target = Path(sys.argv[1]).resolve()
    hooks_json = target / ".codex" / "hooks.json"
    hooks_dir = target / ".claude" / "hooks"
    if not hooks_json.is_file():
        print("MISSING: %s" % hooks_json, file=sys.stderr)
        return 1

    doc = json.loads(hooks_json.read_text(encoding="utf-8"))
    foreign = Path(tempfile.mkdtemp(prefix="ceo-foreign-cwd."))
    failures: List[str] = []
    seen: set = set()
    common = {
        "session_id": "00000000-0000-0000-0000-000000000001",
        "transcript_path": str(target / "transcript.jsonl"),
        "cwd": str(foreign),
        "model": "gpt-5.5",
        "permission_mode": "bypassPermissions",
        "turn_id": "00000000-0000-0000-0000-000000000002",
    }
    n = 0
    for event, cmd in _iter_commands(doc):
        if not cmd or (event, cmd) in seen:
            continue
        seen.add((event, cmd))
        n += 1
        if "{{" in cmd:
            failures.append("unsubstituted placeholder in command: %r" % cmd)
            continue
        argv = shlex.split(cmd)
        if not argv or argv[0] != "env":
            failures.append("command does not use the env argv form: %r" % cmd)
            continue
        if not any(a == "CEO_HOOK_ADAPTER=codex" for a in argv):
            failures.append("missing CEO_HOOK_ADAPTER=codex: %r" % cmd)
        if not any(a.startswith("CLAUDE_PROJECT_DIR=") for a in argv):
            failures.append("missing CLAUDE_PROJECT_DIR= assignment: %r" % cmd)
        shim_toks = [t for t in argv if t.endswith("_python-hook.sh")]
        script_toks = [t for t in argv if t.endswith(".py")]
        if len(shim_toks) != 1:
            failures.append("expected exactly one shim token: %r" % cmd)
            continue
        if len(script_toks) != 1:
            failures.append("expected exactly one hook script token: %r" % cmd)
            continue
        shim = shim_toks[0]
        script = script_toks[0]
        if not os.path.isabs(shim):
            failures.append("shim path is not absolute (cwd-relative = S254 class): %r" % cmd)
        if not os.path.isfile(shim):
            failures.append("shim missing on disk: %s" % shim)
        elif not os.access(shim, os.X_OK):
            failures.append("shim not executable: %s" % shim)
        if "/" in script:
            failures.append("hook script must be a bare name (shim resolves it): %r" % script)
        elif not (hooks_dir / script).is_file():
            failures.append("registered hook %s missing from %s" % (script, hooks_dir))

        # Subprocess execution from a foreign cwd with a benign envelope.
        payload = dict(common)
        payload["hook_event_name"] = event
        payload.update(_ENVELOPES.get(event, {}))
        env = dict(os.environ)
        try:
            proc = subprocess.run(
                argv,
                input=json.dumps(payload),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(foreign),
                env=env,
                timeout=60,
                universal_newlines=True,
            )
        except Exception as exc:  # noqa: BLE001
            failures.append("subprocess raised for %r: %s" % (cmd, exc))
            continue
        if "[_python-hook.sh] ERROR" in proc.stderr:
            failures.append("shim ERROR breadcrumb (could not resolve hook) for %r:\n%s"
                            % (cmd, proc.stderr.strip()))
        if proc.returncode not in (0, 2):
            failures.append("unexpected exit %s for %r\nstderr:\n%s"
                            % (proc.returncode, cmd, proc.stderr.strip()))

    if n == 0:
        print("no commands found in hooks.json (vacuous)", file=sys.stderr)
        return 1
    if failures:
        for f in failures:
            print("FAIL: " + f, file=sys.stderr)
        return 1
    print("OK: %d registered commands resolved + ran clean" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
