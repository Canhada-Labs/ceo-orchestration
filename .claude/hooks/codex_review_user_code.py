#!/usr/bin/env python3
"""PLAN-128 Wave-1 #3 — cross-model Codex review of the ADOPTER's code (Stop / pre-commit gate).

"Don't grade your own homework": Claude writes, OpenAI Codex reviews. The framework pair-rail only guards
the framework's OWN files; this extends cross-model review to the USER's app code — but ONLY when the diff
is risky (auth / money / migrations / crypto / big diff, via route.py), and ONLY when that risky diff has
CHANGED since the last review (dedupe by hash), so it costs one Codex run per distinct risky diff, not one
per assistant turn.

Hardened per Codex pair-rail 019e8db2 batch review:
  1. per-file diff passed to route.classify so content/large-diff rules actually fire.
  2. staged + unstaged + untracked changes all considered (fresh-repo safe).
  3. untracked file content included in the review input (not just the name).
  4. Codex STDOUT only is the verdict; stderr/timeout/nonzero → infra fail-open ("review skipped"), never a
     finding (Codex emits a PATH warning on stderr in this env — that must not make CLEAN look dirty).
  5. dedupe: a diff-hash state file suppresses re-review of an unchanged risky diff.

E2-F1 wiring (PLAN-134 W0): a CLEAN AUTO verdict also approves the current diff in review_loop's opt-in
CEO_REVIEW_LOOP Stop-gate state (this hook runs BEFORE review_loop in the settings.json Stop array, so the
approval is visible on the same Stop event). See _approve_review_loop for the TOCTOU guard.

Advisory by default; CEO_CODEX_USER_REVIEW_BLOCK=1 hard-blocks; CEO_CODEX_USER_REVIEW=0 disables. Fail-open.
Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route  # noqa: E402

DIFF_CAP = 16000
PER_FILE_CAP = 8000          # one untracked file can't eat the whole review budget (Codex residual #3)
CODEX_TIMEOUT_S = 120


def _git(args: List[str], cwd: str) -> Tuple[int, str]:
    try:
        p = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=20)
        return p.returncode, p.stdout
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""


def _has_head(cwd: str) -> bool:
    rc, _ = _git(["rev-parse", "--verify", "HEAD"], cwd)
    return rc == 0


def changed_files(cwd: str) -> List[str]:
    """staged + unstaged + untracked, deduped, fresh-repo safe (Codex fix #2)."""
    files: List[str] = []
    head = _has_head(cwd)
    if head:
        files += _git(["diff", "--name-only", "HEAD"], cwd)[1].splitlines()
    else:
        files += _git(["diff", "--name-only"], cwd)[1].splitlines()
    files += _git(["diff", "--cached", "--name-only"], cwd)[1].splitlines()
    files += _git(["ls-files", "--others", "--exclude-standard"], cwd)[1].splitlines()
    seen, out = set(), []
    for f in (x.strip() for x in files):
        if f and f not in seen:
            seen.add(f); out.append(f)
    return out


def _file_diff(path: str, cwd: str, tracked: bool) -> str:
    """Diff for one file; for an untracked/new file, show its content as an added block (Codex fix #3)."""
    if tracked:
        base = ["diff", "HEAD", "--", path] if _has_head(cwd) else ["diff", "--", path]
        rc, out = _git(base, cwd)
        if out.strip():
            return out
        rc, out = _git(["diff", "--cached", "--", path], cwd)   # staged-only
        if out.strip():
            return out
    full = os.path.join(cwd, path)
    try:
        if os.path.isfile(full):
            content = open(full, encoding="utf-8").read()[:PER_FILE_CAP]   # per-file cap (residual #3)
            return "+++ NEW FILE %s\n" % path + "".join("+" + ln + "\n" for ln in content.splitlines())
    except Exception:
        pass
    return ""


def risky_diff(cwd: str) -> Tuple[List[str], str]:
    """Return (risky_files, assembled_diff) — per-file diff fed to route.classify (Codex fix #1)."""
    tracked = set(_git(["ls-files"], cwd)[1].splitlines())
    chunks, files = [], []
    for f in changed_files(cwd):
        d = _file_diff(f, cwd, f in tracked)
        if route.classify(f, d or None)["recommend"]["codex_review"]:
            files.append(f)
            if d:
                chunks.append(d)
    return files, ("\n".join(chunks))[:DIFF_CAP]


def run_codex_review(diff: str, cwd: str) -> Tuple[bool, Optional[str]]:
    """(codex_available, verdict_from_STDOUT). stderr/timeout/nonzero → (True, None) = infra skip, never a
    finding (Codex fix #4)."""
    if not shutil.which("codex"):
        return (False, None)
    prompt = ("You are a strict code reviewer. Review ONLY this git diff for correctness bugs and security "
              "issues (auth, money, injection, data loss). Be terse: list concrete findings as "
              "'- <file>: <issue>', or output exactly CLEAN if none.\n\n" + diff)
    try:
        # `--` ends option parsing so a diff that happens to start with `-`/`--sandbox=...` can never be
        # mis-read as a codex flag (passed as a single argv element; no shell). Defence-in-depth (rite S5).
        p = subprocess.run(["codex", "exec", "--sandbox", "read-only", "--", prompt],
                           cwd=cwd, capture_output=True, text=True, timeout=CODEX_TIMEOUT_S)
        if p.returncode != 0 or not p.stdout.strip():
            return (True, None)                    # infra issue → skip, not a finding
        return (True, p.stdout.strip())            # STDOUT only
    except (subprocess.TimeoutExpired, OSError):
        return (True, None)


def _state_path(cwd: str) -> str:
    gitdir = os.path.join(cwd, ".git")
    base = gitdir if os.path.isdir(gitdir) else cwd
    return os.path.join(base, ".ceo_codex_review_state.json")


def _h(diff: str) -> str:
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def _status(cwd: str, diff: str) -> str:
    try:
        return json.load(open(_state_path(cwd))).get(_h(diff), "")
    except Exception:
        return ""


def _mark(cwd: str, diff: str, status: str) -> None:
    try:
        st = json.load(open(_state_path(cwd)))
    except Exception:
        st = {}
    st[_h(diff)] = status
    if len(st) > 50:
        st = dict(list(st.items())[-25:])
    try:
        json.dump(st, open(_state_path(cwd), "w"))
    except Exception:
        pass


def _allow(extra: Optional[str] = None) -> Dict:
    if extra:
        return {"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": extra}}
    return {}


def _review_loop_sig(cwd: str) -> str:
    """E2-F1 wiring: review_loop's OWN diff signature for cwd, "" on any failure. Snapshot this BEFORE the
    Codex run so _approve_review_loop's TOCTOU guard can verify the worktree did not move under the review."""
    try:
        import review_loop as _rl  # lazy; hooks dir already on sys.path (line 35)
        return _rl._diff_signature(cwd)
    except Exception:
        return ""


def _approve_review_loop(cwd: str, sig0: str) -> None:
    """E2-F1 wiring: a real CLEAN Codex outcome approves the CURRENT diff in review_loop's state, so the
    opt-in CEO_REVIEW_LOOP Stop-gate unblocks on the same Stop event (settings.json runs this hook before
    review_loop). TOCTOU guard: only approve if the signature still equals the pre-review snapshot sig0 —
    files changed during the (up to 120s) Codex run were NOT reviewed, so skip the approval (fail-open: the
    gate just blocks one more iter). Shares review_loop's own _diff_signature + state-dir derivation
    (mirrors review_loop.main()) — never re-implement the hash or the path here."""
    try:
        import review_loop as _rl  # lazy; hooks dir already on sys.path (line 35)
        if not sig0:
            return
        sig = _rl._diff_signature(cwd)
        if sig != sig0:
            return                                 # worktree moved under the review → no approval
        state_dir = (os.environ.get("CEO_REVIEW_LOOP_STATE")
                     or os.path.join(cwd, ".claude", "state", "review-loop"))
        _rl.mark_approved(state_dir, sig)
    except Exception:
        pass


def gate(cwd: Optional[str] = None) -> Dict:
    if os.environ.get("CEO_CODEX_USER_REVIEW", "1") == "0":
        return _allow()
    cwd = os.path.realpath(cwd or os.getcwd())
    files, diff = risky_diff(cwd)
    if not files or not diff.strip():
        return _allow()
    auto = os.environ.get("CEO_CODEX_USER_REVIEW_AUTO") == "1"
    status = _status(cwd, diff)
    # DEFAULT-ON (Codex residual #2): cheap DETECT-only — never launch a 120s Codex run unasked. Dedupe so
    # the advisory fires once per distinct risky diff, not every turn.
    if not auto:
        if status in ("detected", "reviewed"):
            return _allow()
        _mark(cwd, diff, "detected")
        return _allow("RISKY DIFF in %s — get a cross-model review before committing: run "
                      "`codex review --uncommitted` (or set CEO_CODEX_USER_REVIEW_AUTO=1 to auto-run it "
                      "here)." % ", ".join(files))
    # AUTO mode: actually run Codex. Only suppress an already-REVIEWED diff (not an infra-skip — residual #1).
    if status == "reviewed":
        return _allow()
    rl_sig0 = _review_loop_sig(cwd)                # E2-F1: TOCTOU snapshot BEFORE the Codex run
    available, verdict = run_codex_review(diff, cwd)
    if not available:
        return _allow("CROSS-MODEL REVIEW SKIPPED — Codex CLI not found for risky change in: %s." % ", ".join(files))
    if verdict is None:
        return _allow("CROSS-MODEL REVIEW SKIPPED (codex returned no clean result) for risky change in: %s "
                      "— re-run before committing." % ", ".join(files))
    _mark(cwd, diff, "reviewed")                   # mark ONLY on a real Codex outcome
    try:  # PLAN-128 §7 — fail-open catch telemetry (never blocks the hook)
        _clib = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_lib")
        if _clib not in sys.path:
            sys.path.insert(0, _clib)
        import audit_emit as _ae
        _ae.emit_generic("codex_review_invoked", review_status="invoked",
                         violations_found_count=0 if verdict.upper().strip() == "CLEAN" else 1)
    except Exception:
        pass
    if verdict.upper().strip() != "CLEAN":
        msg = ("CODEX CROSS-REVIEW of your risky change (%s) found:\n\n%s\n\nAddress these before committing."
               % (", ".join(files), verdict[:6000]))
        if os.environ.get("CEO_CODEX_USER_REVIEW_BLOCK") == "1":
            return {"decision": "block", "reason": msg}
        return _allow(msg)
    _approve_review_loop(cwd, rl_sig0)             # E2-F1: CLEAN unblocks the review_loop Stop-gate
    return _allow("Codex cross-review of the risky change (%s): CLEAN." % ", ".join(files))


def main() -> None:
    try:
        hi = json.loads(sys.stdin.read() or "{}")
    except Exception:
        hi = {}
    try:
        print(json.dumps(gate(hi.get("cwd"))))
    except Exception as exc:
        sys.stderr.write("# codex_review_user_code fail-open: %s\n" % str(exc)[:120])
        print("{}")


# ------------------------------------------------------------------------------------------------
def _selftest() -> None:
    import tempfile
    g = sys.modules[__name__]
    orig = (g.risky_diff, g.run_codex_review)
    try:
        # no risky files → silent
        g.risky_diff = lambda cwd: ([], "")
        d0 = tempfile.mkdtemp(); os.makedirs(os.path.join(d0, ".git"))
        assert gate(d0) == {}, "no risky → silent"
        # DEFAULT (detect-only): risky → advisory recommending review, NO codex call; 2nd call dedupes.
        def boom(diff, cwd):
            raise AssertionError("Codex must NOT run in default detect-only mode")
        g.run_codex_review = boom
        g.risky_diff = lambda cwd: (["src/auth/login.py"], "+ password == x\n")
        d1 = tempfile.mkdtemp(); os.makedirs(os.path.join(d1, ".git"))
        r = gate(d1); assert "RISKY DIFF" in json.dumps(r), r
        assert gate(d1) == {}, "detect-only should dedupe the second call"
        # AUTO mode: now Codex actually runs.
        os.environ["CEO_CODEX_USER_REVIEW_AUTO"] = "1"
        d2 = tempfile.mkdtemp(); os.makedirs(os.path.join(d2, ".git"))
        # infra-skip (None) → 'SKIPPED', and NOT marked → a later real run still happens (residual #1)
        g.run_codex_review = lambda diff, cwd: (True, None)
        assert "SKIPPED" in json.dumps(gate(d2))
        g.run_codex_review = lambda diff, cwd: (True, "- login.py: timing-unsafe compare")
        assert "timing-unsafe" in json.dumps(gate(d2)), "after a skip, a real review must still run"
        assert gate(d2) == {}, "after a real review, same diff dedupes"
        # CLEAN
        d3 = tempfile.mkdtemp(); os.makedirs(os.path.join(d3, ".git"))
        g.run_codex_review = lambda diff, cwd: (True, "CLEAN")
        assert "CLEAN" in json.dumps(gate(d3))
        # block mode
        d4 = tempfile.mkdtemp(); os.makedirs(os.path.join(d4, ".git"))
        os.environ["CEO_CODEX_USER_REVIEW_BLOCK"] = "1"
        g.run_codex_review = lambda diff, cwd: (True, "- x: SQL injection")
        assert gate(d4).get("decision") == "block"
        os.environ.pop("CEO_CODEX_USER_REVIEW_BLOCK")
        os.environ.pop("CEO_CODEX_USER_REVIEW_AUTO")
        # kill-switch
        os.environ["CEO_CODEX_USER_REVIEW"] = "0"; assert gate(d1) == {}; os.environ.pop("CEO_CODEX_USER_REVIEW")
        import shutil as _sh
        for d in (d0, d1, d2, d3, d4):
            _sh.rmtree(d, ignore_errors=True)
    finally:
        g.risky_diff, g.run_codex_review = orig
    print("codex_review_user_code.py selftest PASS (no-risky-silent / detect-only-default+dedupe / "
          "auto-skip-not-marked / auto-finding / clean / block / kill-switch)")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
