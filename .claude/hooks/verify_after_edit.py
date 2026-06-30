#!/usr/bin/env python3
"""PLAN-128 Wave-1 #1 — After-Edit Verification Loop (PostToolUse Edit|Write|MultiEdit hook).

The single highest-ROI accelerator for "no buggy code": after Claude edits a file, AUTO-DETECT the
project's fast checks for that file's language (syntax → lint) and run them on the CHANGED file ONLY
(fast, deterministic, $0). On a real finding, feed the errors back as `additionalContext` so Claude
SELF-REPAIRS before the human sees the bug. Advisory by default; deterministic; fail-OPEN on any infra
error (a verifier bug must never wedge the loop).

Hardened per Codex pair-rail `019e8db2` (5 fixes, before default-on):
  1. Paths are realpath-resolved, required to be a regular file UNDER cwd → no path-escape, no leading-`-`
     argv-flag injection.
  2. `--` end-of-options separators where the tool supports it.
  3. NO whole-tree scans (`go vet ./...` removed) — changed file only; package-scope go vet is opt-in.
  4. Checker INFRA failures (missing module/config/plugin, tool crash, "no files matching") are classified
     as SILENT, never findings — a finding must reference the changed file's basename.
  5. Total feedback capped (files/findings/chars) with a truncation note.

PLAN-135 W2 H6 — `continueOnBlock` (Claude Code 2.1.139, S214 TIER-A top-6 item). When the hard-block
opt-in (CEO_VERIFY_AFTER_EDIT_BLOCK=1) fires, the legacy shape ends the turn; the harness's top-level
`continueOnBlock: true` instead feeds the block's `reason` back to Claude as context and CONTINUES the
turn — turning "block" into "here's the failing checker, self-repair now" without aborting (exactly the
self-repair loop PLAN-128 wanted). Default-ON when blocking is opted in; revert to the legacy hard stop
with CEO_VERIFY_AFTER_EDIT_NO_CONTINUE=1. Advisory mode (no block opt-in) is unchanged — the finding still
rides `additionalContext`, which never ends the turn, so `continueOnBlock` is meaningless there and is NOT
emitted on the advisory path.

Kill-switch CEO_VERIFY_AFTER_EDIT=0; hard-block opt-in CEO_VERIFY_AFTER_EDIT_BLOCK=1; go-vet opt-in
CEO_VERIFY_AFTER_EDIT_GO_PACKAGE=1; continue-on-block revert CEO_VERIFY_AFTER_EDIT_NO_CONTINUE=1. Stdlib
only, Python >= 3.9. Reads PostToolUse JSON on stdin, emits hook JSON on stdout.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

TIMEOUT_S = 12
MAX_FILES = 5
MAX_FINDINGS = 6
MAX_PER_FINDING = 1500
MAX_TOTAL_CHARS = 3500

# Unambiguous "the CHECKER itself failed" markers → never a code finding (fail-open silent). Codex #4.
_INFRA_NOISE = re.compile(
    r"no module named|command not found|cannot find module|could not find|couldn't find|"
    r"failed to load config|cannot read config|no files matching|no such file or directory|"
    r"unknown option|unrecognized arguments|configuration error|invalid config|eslint couldn't find|"
    r"cannot find package|missing script|not found:|importerror|modulenotfounderror",
    re.IGNORECASE,
)


def _allow(extra: Optional[str] = None) -> Dict:
    if extra:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": extra}}
    return {}


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def _run(cmd: List[str], cwd: str) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_S)
        return p.returncode, (p.stdout + p.stderr)
    except (subprocess.TimeoutExpired, OSError):
        return 0, ""   # fail-open: a hanging/missing checker never blocks


def _safe_resolve(path: str, cwd_real: str) -> Optional[str]:
    """realpath the path, require it is a regular file UNDER cwd. Else None (Codex #1)."""
    try:
        p = path if os.path.isabs(path) else os.path.join(cwd_real, path)
        p = os.path.realpath(p)
    except Exception:
        return None
    if not os.path.isfile(p):
        return None
    if not (p == cwd_real or p.startswith(cwd_real + os.sep)):
        return None
    return p


# ---- per-language fast checkers; each returns [(label, rc, output), ...] ----------------------------
def _check_python(abspath: str, cwd: str):
    checks = [("py_compile (syntax)", *_run([sys.executable, "-m", "py_compile", abspath], cwd))]
    if _which("ruff"):
        checks.append(("ruff", *_run(["ruff", "check", "--", abspath], cwd)))
    elif _which("flake8"):
        checks.append(("flake8", *_run(["flake8", "--", abspath], cwd)))
    else:
        rc_imp, _ = _run([sys.executable, "-c", "import pyflakes"], cwd)
        if rc_imp == 0:
            checks.append(("pyflakes", *_run([sys.executable, "-m", "pyflakes", abspath], cwd)))
    return checks


def _check_js_ts(abspath: str, cwd: str):
    checks = []
    local_eslint = os.path.join(cwd, "node_modules", ".bin", "eslint")
    if os.path.exists(local_eslint):
        checks.append(("eslint", *_run([local_eslint, "--", abspath], cwd)))
    if abspath.endswith((".js", ".mjs", ".cjs")) and _which("node"):
        checks.append(("node --check (syntax)", *_run(["node", "--check", abspath], cwd)))
    return checks


def _check_go(abspath: str, cwd: str):
    checks = []
    if _which("gofmt"):
        rc, out = _run(["gofmt", "-l", "--", abspath], cwd)
        checks.append(("gofmt", 1 if out.strip() else 0,
                       (os.path.basename(abspath) + " is not gofmt-formatted") if out.strip() else ""))
    if os.environ.get("CEO_VERIFY_AFTER_EDIT_GO_PACKAGE") == "1" and _which("go"):
        checks.append(("go vet (package)", *_run(["go", "vet", os.path.dirname(abspath)], cwd)))
    return checks


_LANG = {
    (".py",): _check_python,
    (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"): _check_js_ts,
    (".go",): _check_go,
}


def _checker_for(path: str):
    for exts, fn in _LANG.items():
        if path.endswith(exts):
            return fn
    return None


def _changed_paths(tool_input: Dict) -> List[str]:
    paths = []
    fp = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(fp, str):
        paths.append(fp)
    for e in tool_input.get("edits", []) or []:
        p = (e or {}).get("file_path")
        if isinstance(p, str):
            paths.append(p)
    seen, out = set(), []
    for p in paths:
        if p and p not in seen:
            seen.add(p); out.append(p)
    return out


def _is_real_finding(out: str, basename: str) -> bool:
    """A finding is real iff the checker output references THIS changed file and is not infra noise."""
    if not out.strip():
        return False
    if _INFRA_NOISE.search(out):
        return False
    return basename in out


def verify(hook_input: Dict) -> Dict:
    if os.environ.get("CEO_VERIFY_AFTER_EDIT", "1") == "0":
        return _allow()
    tool_input = hook_input.get("tool_input") or {}
    cwd_real = os.path.realpath(hook_input.get("cwd") or os.getcwd())
    findings: List[str] = []
    total = 0
    for path in _changed_paths(tool_input)[:MAX_FILES]:
        if len(findings) >= MAX_FINDINGS or total >= MAX_TOTAL_CHARS:
            break
        abspath = _safe_resolve(path, cwd_real)
        if abspath is None:
            continue
        fn = _checker_for(abspath)
        if fn is None:
            continue
        base = os.path.basename(abspath)
        for label, rc, out in fn(abspath, cwd_real):
            if rc != 0 and _is_real_finding(out, base):
                snippet = out.strip()[:MAX_PER_FINDING]
                block = "• [%s] %s:\n%s" % (label, base, snippet)
                findings.append(block); total += len(block)
                if len(findings) >= MAX_FINDINGS or total >= MAX_TOTAL_CHARS:
                    break
    if not findings:
        return _allow()
    body = "\n\n".join(findings)
    if total >= MAX_TOTAL_CHARS:
        body += "\n\n…(verification output truncated)"
    msg = ("AFTER-EDIT VERIFY found issues in the file(s) you just changed — fix them now before moving "
           "on (self-repair):\n\n" + body)
    try:  # PLAN-128 §7 — fail-open catch telemetry (never blocks the hook)
        _vlib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lib")
        if _vlib not in sys.path:
            sys.path.insert(0, _vlib)
        import audit_emit as _ae
        _t = body.lower()
        _checker = ("py_compile" if "py_compile" in _t else "ruff" if "ruff" in _t
                    else "eslint" if "eslint" in _t else "node_check" if "node" in _t else "other")
        _ex = "".join(_changed_paths(tool_input))
        _lang = ("python" if ".py" in _ex else "js_ts" if any(e in _ex for e in
                 (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")) else "go" if ".go" in _ex else "other")
        _ae.emit_generic("verify_after_edit_finding", checker=_checker, lang=_lang,
                         finding_count=len(findings),
                         session_id=str(hook_input.get("session_id") or ""))
    except Exception:
        pass
    if os.environ.get("CEO_VERIFY_AFTER_EDIT_BLOCK") == "1":
        # H6 (PLAN-135 W2): default-ON `continueOnBlock` — the harness feeds `reason`
        # back to Claude and KEEPS the turn going (self-repair), instead of aborting it.
        # Top-level field per Claude Code 2.1.139 (NOT inside hookSpecificOutput). Revert
        # to the legacy hard stop with CEO_VERIFY_AFTER_EDIT_NO_CONTINUE=1.
        out = {"decision": "block", "reason": msg}
        if os.environ.get("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE") != "1":
            out["continueOnBlock"] = True
        return out
    return _allow(msg)


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}"); return
    try:
        print(json.dumps(verify(hook_input)))
    except Exception as exc:
        sys.stderr.write("# verify_after_edit fail-open: %s\n" % str(exc)[:120])
        print("{}")


# ------------------------------------------------------------------------------------------------
def _selftest() -> None:
    import tempfile
    d = os.path.realpath(tempfile.mkdtemp())
    good = os.path.join(d, "ok.py"); open(good, "w").write("def f(x):\n    return x + 1\n")
    bad = os.path.join(d, "bad.py"); open(bad, "w").write("def f(x):\n    return x +\n")
    # good → silent
    assert verify({"tool_input": {"file_path": good}, "cwd": d}) == {}, "clean file must be silent"
    # bad → surfaced + references basename
    ctx = json.dumps(verify({"tool_input": {"file_path": bad}, "cwd": d}))
    assert "AFTER-EDIT VERIFY" in ctx and "bad.py" in ctx, "syntax error must surface"
    # path escape: a file OUTSIDE cwd is ignored
    outside = os.path.join(os.path.realpath(tempfile.mkdtemp()), "x.py"); open(outside, "w").write("def f(:\n")
    assert verify({"tool_input": {"file_path": outside}, "cwd": d}) == {}, "path outside cwd must be ignored"
    # leading-dash filename neither escapes nor injects (resolved to abs under cwd)
    dash = os.path.join(d, "-rf.py"); open(dash, "w").write("x = (\n")
    rd = verify({"tool_input": {"file_path": dash}, "cwd": d})
    assert rd == {} or "-rf.py" in json.dumps(rd), rd  # either silent or a real finding about that file
    # kill-switch / block / non-source / missing
    os.environ["CEO_VERIFY_AFTER_EDIT"] = "0"
    assert verify({"tool_input": {"file_path": bad}, "cwd": d}) == {}
    os.environ.pop("CEO_VERIFY_AFTER_EDIT")
    os.environ["CEO_VERIFY_AFTER_EDIT_BLOCK"] = "1"
    _blk = verify({"tool_input": {"file_path": bad}, "cwd": d})
    assert _blk.get("decision") == "block"
    # H6: block path is continueOnBlock by default (feed reason back, keep the turn).
    assert _blk.get("continueOnBlock") is True, "block must default to continueOnBlock (H6 self-repair)"
    # H6: legacy hard stop is still reachable via the revert switch (no continueOnBlock key).
    os.environ["CEO_VERIFY_AFTER_EDIT_NO_CONTINUE"] = "1"
    _blk_legacy = verify({"tool_input": {"file_path": bad}, "cwd": d})
    assert _blk_legacy.get("decision") == "block" and "continueOnBlock" not in _blk_legacy, \
        "NO_CONTINUE=1 must restore the legacy hard-block (no continueOnBlock key)"
    os.environ.pop("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE")
    os.environ.pop("CEO_VERIFY_AFTER_EDIT_BLOCK")
    open(os.path.join(d, "n.txt"), "w").write("hi")
    assert verify({"tool_input": {"file_path": os.path.join(d, "n.txt")}, "cwd": d}) == {}
    assert verify({"tool_input": {"file_path": "/nope/x.py"}, "cwd": d}) == {}
    # infra-noise classifier: a fake checker error string is NOT a finding
    assert _is_real_finding("No module named pyflakes", "bad.py") is False
    assert _is_real_finding("bad.py:2: undefined name 'q'", "bad.py") is True
    import shutil as _sh; _sh.rmtree(d, ignore_errors=True)
    print("verify_after_edit.py selftest PASS (clean-silent / surface / path-escape / dash / kill / block / "
          "continueOnBlock-default / no-continue-revert / non-source / missing / infra-noise-classifier)")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
