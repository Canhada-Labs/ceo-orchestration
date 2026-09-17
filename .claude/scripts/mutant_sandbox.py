#!/usr/bin/env python3
"""mutant_sandbox.py — run a mutant against a DISPOSABLE copy of an identified revision (PLAN-190 W2).

Why
---
A consumer's skeptic/recheck phases planted mutants IN the implementation
worktree and restored them by copying a backup; a quota death or a pause in
the middle left 13 live mutants in the tree, and one restore reintroduced
old code because the backup predated a fix. The order (2026-09-17): "Mutantes
devem ser executados em cópias descartáveis de uma revisão identificada.
Interrupção não pode deixar mutação na árvore de implementação. Registrar
resultados por mutante para reaproveitar verificações válidas."

What it does
------------
``run``: ``git worktree add --detach`` a scratch copy of ``--rev`` (default
``HEAD``) of ``--repo``; ``git apply`` the mutant (a unified diff) INSIDE the
copy; run ``--cmd`` there with a timeout; record ONE JSONL line in
``--ledger`` keyed by ``(rev, mutant_sha256, cmd)``; remove the copy in
``finally`` (also on KeyboardInterrupt / timeout). The implementation tree is
never written to; ``git status --porcelain`` of ``--repo`` is captured before
and after and any difference is reported as an ERROR outcome.

Outcomes: ``killed`` (the command failed under the mutant — the tests caught
it), ``survived`` (the command passed — the mutant was NOT caught), ``error``
(patch did not apply / timeout / command missing / tree changed).

``query``: print the recorded outcome for the same key (reuse a valid
verification instead of re-running); rc 0 found, rc 4 not found.
``gc``: remove sandbox copies left by a crashed run (listed in
``<ledger>.sandboxes.jsonl``).

Stdlib only, Python >= 3.9. Requires ``git``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _git(repo: Path, *args: str, timeout: float = 60.0) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=timeout)


def _append(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def _read(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def key_of(rev: str, mutant_sha: str, cmd: str) -> str:
    return hashlib.sha256(("%s|%s|%s" % (rev, mutant_sha, cmd)).encode("utf-8")).hexdigest()


def resolve_rev(repo: Path, rev: str) -> str:
    r = _git(repo, "rev-parse", "--verify", rev + "^{commit}")
    if r.returncode != 0:
        raise SystemExit("cannot resolve rev %r in %s: %s" % (rev, repo, r.stderr.strip()[:120]))
    return r.stdout.strip()


def tree_state(repo: Path) -> str:
    r = _git(repo, "status", "--porcelain")
    return r.stdout if r.returncode == 0 else "<unavailable>"


def query(ledger: Path, rev: str, mutant_sha: str, cmd: str) -> Optional[Dict[str, Any]]:
    k = key_of(rev, mutant_sha, cmd)
    for rec in reversed(_read(ledger)):
        if rec.get("key") == k and rec.get("outcome") in ("killed", "survived"):
            return rec
    return None


def run(repo: Path, rev: str, mutant: Path, cmd: str, ledger: Path, timeout: float, keep: bool, scratch_root: Optional[Path]) -> Dict[str, Any]:
    full_rev = resolve_rev(repo, rev)
    mutant_bytes = mutant.read_bytes()
    mutant_sha = hashlib.sha256(mutant_bytes).hexdigest()
    before = tree_state(repo)
    sandboxes = Path(str(ledger) + ".sandboxes.jsonl")
    root = scratch_root or Path(tempfile.gettempdir()) / "ceo-mutants"
    root.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="mut-%s-" % mutant_sha[:8], dir=str(root)))
    # mkdtemp created the dir; git worktree add wants a non-existing path
    os.rmdir(sandbox)
    _append(sandboxes, {"ts": _now(), "sandbox": str(sandbox), "repo": str(repo), "state": "creating"})
    rec: Dict[str, Any] = {
        "ts": _now(), "key": key_of(full_rev, mutant_sha, cmd), "repo": str(repo), "rev": full_rev,
        "mutant_sha256": mutant_sha, "mutant_file": str(mutant), "cmd": cmd, "outcome": "error", "rc": None,
        "duration_ms": None, "sandbox": str(sandbox), "detail": "",
    }
    t0 = time.time()
    try:
        wt = _git(repo, "worktree", "add", "--detach", str(sandbox), full_rev, timeout=120)
        if wt.returncode != 0:
            rec["detail"] = "worktree add failed: " + wt.stderr.strip()[:200]
            return rec
        ap = subprocess.run(["git", "apply", "--whitespace=nowarn", str(mutant.resolve())], cwd=str(sandbox), capture_output=True, text=True, timeout=60)
        if ap.returncode != 0:
            rec["detail"] = "mutant does not apply: " + (ap.stderr or ap.stdout).strip()[:200]
            return rec
        try:
            proc = subprocess.run(shlex.split(cmd), cwd=str(sandbox), capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            rec["detail"] = "command timed out after %ss" % timeout
            return rec
        except FileNotFoundError as exc:
            rec["detail"] = "command not found: %s" % exc
            return rec
        rec["rc"] = proc.returncode
        rec["outcome"] = "killed" if proc.returncode != 0 else "survived"
        rec["detail"] = (proc.stdout + proc.stderr)[-400:].strip()
        return rec
    finally:
        rec["duration_ms"] = int((time.time() - t0) * 1000)
        if not keep:
            rm = _git(repo, "worktree", "remove", "--force", str(sandbox), timeout=120)
            if rm.returncode != 0 or sandbox.exists():
                _append(sandboxes, {"ts": _now(), "sandbox": str(sandbox), "repo": str(repo), "state": "orphan", "detail": rm.stderr.strip()[:200]})
            else:
                _append(sandboxes, {"ts": _now(), "sandbox": str(sandbox), "repo": str(repo), "state": "removed"})
            _git(repo, "worktree", "prune")
        after = tree_state(repo)
        if after != before:
            rec["outcome"] = "error"
            rec["detail"] = ("IMPLEMENTATION TREE CHANGED during the run — investigate; " + rec["detail"])[:400]
        _append(ledger, rec)


def gc(ledger: Path, repo: Optional[Path]) -> int:
    sandboxes = Path(str(ledger) + ".sandboxes.jsonl")
    state: Dict[str, str] = {}
    repos: Dict[str, str] = {}
    for rec in _read(sandboxes):
        state[rec.get("sandbox", "")] = rec.get("state", "")
        repos[rec.get("sandbox", "")] = rec.get("repo", "")
    removed = 0
    for sb, st in state.items():
        if st in ("creating", "orphan") and sb and Path(sb).exists():
            r = repo or Path(repos.get(sb) or ".")
            _git(r, "worktree", "remove", "--force", sb, timeout=120)
            if not Path(sb).exists():
                removed += 1
                _append(sandboxes, {"ts": _now(), "sandbox": sb, "repo": str(r), "state": "removed"})
            _git(r, "worktree", "prune")
    print("gc: %d sandbox(es) removed" % removed)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="sub", required=True)  # not "cmd": --cmd is the test command
    r = sub.add_parser("run")
    r.add_argument("--repo", required=True)
    r.add_argument("--rev", default="HEAD")
    r.add_argument("--mutant", required=True, help="unified diff to apply inside the copy")
    r.add_argument("--cmd", required=True, help="test command (shlex-split, run inside the copy)")
    r.add_argument("--ledger", required=True)
    r.add_argument("--timeout", type=float, default=600.0)
    r.add_argument("--keep", action="store_true", help="keep the sandbox (debugging); it is then listed as orphan for gc")
    r.add_argument("--scratch-root", default=None)
    r.add_argument("--json", action="store_true")
    q = sub.add_parser("query")
    q.add_argument("--repo", required=True)
    q.add_argument("--rev", default="HEAD")
    q.add_argument("--mutant", required=True)
    q.add_argument("--cmd", required=True)
    q.add_argument("--ledger", required=True)
    g = sub.add_parser("gc")
    g.add_argument("--ledger", required=True)
    g.add_argument("--repo", default=None)
    args = ap.parse_args(argv)
    if args.sub == "gc":
        return gc(Path(args.ledger), Path(args.repo) if args.repo else None)
    repo = Path(os.path.expanduser(args.repo)).resolve()
    ledger = Path(os.path.expanduser(args.ledger))
    mutant = Path(os.path.expanduser(args.mutant))
    if args.sub == "query":
        rec = query(ledger, resolve_rev(repo, args.rev), hashlib.sha256(mutant.read_bytes()).hexdigest(), args.cmd)
        if rec is None:
            print("NOT-RECORDED")
            return 4
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    rec = run(repo, args.rev, mutant, args.cmd, ledger, args.timeout, args.keep, Path(args.scratch_root) if args.scratch_root else None)
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=1))
    else:
        print("%s rc=%s %sms %s" % (rec["outcome"].upper(), rec["rc"], rec["duration_ms"], rec["detail"][:120]))
    return {"killed": 0, "survived": 1, "error": 2}[rec["outcome"]]


if __name__ == "__main__":
    sys.exit(main())
