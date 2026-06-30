#!/usr/bin/env python3
"""PLAN-135 W2 H8 — Setup hook: post-install self-verification + env persistence.

Fires on the harness `Setup` event (`init` matcher) — the standard
`claude --init` post-install entry point. Closes the S217 "hook on disk but
not registered" / "exec-bit dropped" class by having the installation
SELF-VERIFY through the harness's own bootstrap, instead of trusting that the
operator ran a separate check.

ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing files /
timeouts / subprocess failures → stderr breadcrumb + emit `{}`). NEVER blocks
a Setup. On a small internal time budget it runs THREE cheap self-checks
against the freshly-installed tree:

  (i)   validate-governance.sh --fast    — structural governance health
  (ii)  verify-counts.sh --quiet --no-tests — derived-count / doc-drift
  (iii) hook exec-bits — every `.claude/hooks/*.py` registered in settings.json
        carries the owner exec bit (the EXACT S228 exec-bit regression class)

Each check is best-effort and capped; a non-zero result becomes an advisory
line, never a block. The aggregated result is surfaced as `additionalContext`
on the Setup hook output (informational, fail-open).

CLAUDE_ENV_FILE PERSISTENCE (constraint a — debate R1)
------------------------------------------------------
If the harness provides a `CLAUDE_ENV_FILE` path (the file the harness sources
to seed the session env), this hook appends ONLY the persistable subset of the
current `CEO_*` environment — defined by the explicit include-list in
`_lib/env_persist_allowlist.py`. Every override / escape-hatch / kill-switch /
enforcement-toggle var (CEO_KERNEL_OVERRIDE, CEO_GIT_BYPASS_ALLOW{,_ACK},
CEO_TURBO, every CEO_*_DISABLE/_ENFORCE/_ACK, every credential/endpoint) is
EXCLUDED BY CONSTRUCTION (fail-closed include-list). This prevents the
S185/S197 stale-override class: a bypass armed in one session can never be
silently re-armed in the next via the env file.

NO audit actions are emitted (closed-enum `_KNOWN_ACTIONS` discipline — adding
one requires BOTH `_KNOWN_ACTIONS` and SPEC; this hook uses stderr breadcrumbs
+ `additionalContext` only). Kill-switch: `CEO_SETUP_VERIFICATION=0`. Stdlib
only, Python >= 3.9.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Per-check subprocess timeout (seconds) and a soft total budget.
CHECK_TIMEOUT_S = 8.0
TIME_BUDGET_S = 12.0

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _load_allowlist():
    """Resolve the persistence allowlist co-located in this hook's `_lib/`.

    Loaded by FILE PATH relative to `__file__` (not `from _lib import …`) so it
    works whether the module is the installed sibling `_lib/` OR a staged copy
    under a PLAN-135 bundle — the live `_lib` package may not yet carry the
    submodule pre-ceremony. Import failure is an infra condition → None
    (persistence is then skipped; a missing allowlist must NEVER read as
    'persist everything')."""
    path = _HOOKS_DIR / "_lib" / "env_persist_allowlist.py"
    try:
        if not path.is_file():
            return None
        spec = importlib.util.spec_from_file_location(
            "ceo_env_persist_allowlist", path
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # pragma: no cover - import-time infra guard
        return None


_allowlist = _load_allowlist()

_REGISTERED_HOOK_RE = re.compile(r"_python-hook\.sh\"?\s+([A-Za-z0-9_./-]+\.py)")


def _sanitize(text: str) -> str:
    """Disk/env-sourced strings rendered into additionalContext are an
    injection surface (Codex S228 P0 on check_closeout_guard): a value with
    newlines / control chars could forge extra context lines. Keep printable
    ASCII only, clamp length."""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in text)
    return cleaned[:160]


def _run(cmd: List[str], cwd: str) -> Tuple[int, str]:
    """(returncode, short-stderr-or-stdout). 124 on timeout, 127 on OSError —
    both treated as advisory-inconclusive by callers (fail-open)."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=CHECK_TIMEOUT_S
        )
        tail = (p.stderr or p.stdout or "").strip()
        return p.returncode, tail[-200:]
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as exc:
        return 127, str(exc)[:120]


def _check_validate_governance(cwd: str, deadline: float) -> Optional[str]:
    if time.monotonic() > deadline:
        return None
    script = os.path.join(cwd, ".claude", "scripts", "validate-governance.sh")
    if not os.path.isfile(script):
        return None  # not installed here → nothing to assert (fail-open)
    rc, _tail = _run(["bash", script, "--fast"], cwd)
    if rc == 0:
        return None
    if rc in (124, 127):
        return "validate-governance: inconclusive (advisory only)"
    return "validate-governance --fast reported %d issue(s) — run it for detail" % rc


def _check_verify_counts(cwd: str, deadline: float) -> Optional[str]:
    if time.monotonic() > deadline:
        return None
    script = os.path.join(cwd, ".claude", "scripts", "local", "verify-counts.sh")
    if not os.path.isfile(script):
        return None
    rc, _tail = _run(["bash", script, "--quiet", "--no-tests"], cwd)
    if rc == 0:
        return None
    if rc in (124, 127):
        return "verify-counts: inconclusive (advisory only)"
    return "verify-counts reported derived-count drift — run verify-counts.sh"


def _registered_hook_basenames(cwd: str) -> List[str]:
    """Distinct `*.py` basenames registered in settings.json command lines."""
    settings = os.path.join(cwd, ".claude", "settings.json")
    names: List[str] = []
    try:
        with open(settings, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return names
    for blocks in (data.get("hooks") or {}).values():
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            for hook in (block.get("hooks") or []):
                cmd = hook.get("command", "") or ""
                m = _REGISTERED_HOOK_RE.search(cmd)
                if m:
                    names.append(os.path.basename(m.group(1)))
    return sorted(set(names))


def _check_hook_exec_bits(cwd: str, deadline: float) -> Optional[str]:
    """Every registered `.claude/hooks/*.py` must carry the owner exec bit
    (S228 exec-bit class). Missing-file or non-exec → advisory line."""
    hooks_dir = os.path.join(cwd, ".claude", "hooks")
    if not os.path.isdir(hooks_dir):
        return None
    bad: List[str] = []
    for name in _registered_hook_basenames(cwd):
        if time.monotonic() > deadline:
            break
        path = os.path.join(hooks_dir, name)
        try:
            st = os.stat(path)
        except OSError:
            continue  # registered-but-absent is verify-counts' job, not this
        if not (st.st_mode & 0o100):  # S_IXUSR
            bad.append(_sanitize(name))
    if not bad:
        return None
    return "hook exec-bit MISSING on %d file(s): %s — chmod +x .claude/hooks/<name>" % (
        len(bad), ", ".join(sorted(bad)[:8])
    )


def _persist_env(env: Dict[str, str]) -> Optional[str]:
    """Append the persistable CEO_* subset to CLAUDE_ENV_FILE, if the harness
    provided one. Returns an informational line (count persisted) or None.
    Constraint (a): ONLY the explicit allowlist is ever written; everything
    else — every override/escape-hatch/kill-switch — is excluded by the
    fail-closed include-list. Best-effort + fail-open: any I/O / import error
    skips persistence silently (it must NEVER read as 'persist everything')."""
    env_file = env.get("CLAUDE_ENV_FILE", "").strip()
    if not env_file or _allowlist is None:
        return None
    persistable = _allowlist.filter_persistable(env)
    if not persistable:
        return None
    try:
        # KEY=value lines, one per persistable var. Values are env strings;
        # we drop any value with a newline/control char (cannot be safely
        # represented as a single env-file line and is an injection surface).
        lines = []
        for key in sorted(persistable):
            value = persistable[key]
            if any(ord(ch) < 0x20 for ch in value):
                continue
            # CLAUDE_ENV_FILE is SOURCED by the harness, so a value with
            # spaces / shell metacharacters MUST be single-quoted or it sets
            # the wrong value and may execute a word (Codex V2 P2). POSIX
            # single-quote escape — no shell can re-interpret the result.
            quoted = "'" + value.replace("'", "'\\''") + "'"
            lines.append("%s=%s" % (key, quoted))
        if not lines:
            return None
        with open(env_file, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as exc:
        sys.stderr.write(
            "# check_setup_verification env-persist skip: %s\n" % str(exc)[:120]
        )
        return None
    return "persisted %d allowlisted CEO_* var(s) to the session env file" % len(lines)


def gate(payload: Optional[Dict] = None) -> Dict:
    payload = payload or {}
    if os.environ.get("CEO_SETUP_VERIFICATION", "1") == "0":
        return {}
    deadline = time.monotonic() + TIME_BUDGET_S
    cwd = os.path.realpath(
        payload.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    messages: List[str] = []
    for check in (
        _check_validate_governance,
        _check_verify_counts,
        _check_hook_exec_bits,
    ):
        try:
            line = check(cwd, deadline)
        except Exception as exc:  # one check's infra bug must not sink the rest
            sys.stderr.write(
                "# check_setup_verification check fail-open: %s\n" % str(exc)[:120]
            )
            line = None
        if line:
            messages.append(_sanitize(line))

    # CLAUDE_ENV_FILE persistence (constraint a). Snapshot os.environ once.
    try:
        persist_line = _persist_env(dict(os.environ))
    except Exception as exc:  # pragma: no cover - belt-and-suspenders
        sys.stderr.write(
            "# check_setup_verification env-persist fail-open: %s\n" % str(exc)[:120]
        )
        persist_line = None
    if persist_line:
        messages.append(_sanitize(persist_line))

    if not messages:
        return {}
    context = "CEO setup self-verification:\n- " + "\n- ".join(messages)
    return {
        "hookSpecificOutput": {
            "hookEventName": "Setup",
            "additionalContext": context,
        }
    }


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: parse error is an infra condition → breadcrumb + allow.
        sys.stderr.write(
            "# check_setup_verification fail-open (stdin): %s\n" % str(exc)[:120]
        )
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input)))
    except Exception as exc:
        sys.stderr.write("# check_setup_verification fail-open: %s\n" % str(exc)[:120])
        print("{}")


if __name__ == "__main__":
    main()
