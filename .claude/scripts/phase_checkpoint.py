#!/usr/bin/env python3
"""phase_checkpoint.py — verifiable checkpoints INSIDE a long phase (PLAN-190 W2).

Why
---
The runner caches a whole ``agent()`` result; a phase that dies at 400k of
500k tokens restarts from zero — nine phases were lost that way in one night
on a consumer. There is no checkpoint inside ``agent()`` (substrate limit).
The alternative the framework can offer: an append-only ledger the PHASE
PROMPT tells the agent to read before starting and to write after each
completed step, bound to the code revision, so a re-run of the same phase
skips the steps already proven for that revision.

Contract
--------
``mark``:   append ``{run, phase, step, rev, evidence, ts}`` (idempotent per (run, phase, step, rev)).
``status``: print the steps DONE for ``(run, phase)`` at ``rev``; steps recorded under
            another revision are listed as ``stale`` and never count ("prompt idêntico com
            arquivos modificados não torna um resultado antigo válido").
``done``:   append a phase-complete marker for ``(run, phase, rev)``.
Exit codes: 0 ok · 4 nothing recorded (status) · 2 bad input.

Stdlib only, Python >= 3.9. Never edits or deletes records.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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


def _append(path: Path, rec: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def mark(ledger: Path, run: str, phase: str, step: str, rev: str, evidence: str) -> int:
    for rec in _read(ledger):
        if rec.get("kind") == "step" and (rec.get("run"), rec.get("phase"), rec.get("step"), rec.get("rev")) == (run, phase, step, rev):
            print("already recorded: %s/%s/%s @ %s" % (run, phase, step, rev[:12]))
            return 0
    _append(ledger, {"kind": "step", "run": run, "phase": phase, "step": step, "rev": rev, "evidence": evidence, "ts": _now()})
    print("recorded: %s/%s/%s @ %s" % (run, phase, step, rev[:12]))
    return 0


def done(ledger: Path, run: str, phase: str, rev: str) -> int:
    _append(ledger, {"kind": "phase_done", "run": run, "phase": phase, "rev": rev, "ts": _now()})
    print("phase done: %s/%s @ %s" % (run, phase, rev[:12]))
    return 0


def status(ledger: Path, run: str, phase: str, rev: str, as_json: bool) -> int:
    recs = [r for r in _read(ledger) if r.get("run") == run and r.get("phase") == phase]
    valid: List[Dict[str, Any]] = []
    stale: List[Dict[str, Any]] = []
    complete = False
    for r in recs:
        if r.get("kind") == "step":
            (valid if r.get("rev") == rev else stale).append(r)
        elif r.get("kind") == "phase_done" and r.get("rev") == rev:
            complete = True
    seen = set()
    steps = []
    for r in valid:
        if r["step"] not in seen:
            seen.add(r["step"])
            steps.append({"step": r["step"], "evidence": r.get("evidence"), "ts": r.get("ts")})
    out = {"run": run, "phase": phase, "rev": rev, "done_steps": steps, "phase_complete": complete, "stale_steps_other_rev": len(stale)}
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print("phase %s/%s @ %s: %d step(s) done%s; %d stale (other rev, ignored)" % (run, phase, rev[:12], len(steps), " — COMPLETE" if complete else "", len(stale)))
        for s in steps:
            print("  done: %s (%s)" % (s["step"], (s.get("evidence") or "")[:60]))
    return 0 if (steps or complete) else 4


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("mark", "status", "done"):
        p = sub.add_parser(name)
        p.add_argument("--ledger", required=True)
        p.add_argument("--run", required=True)
        p.add_argument("--phase", required=True)
        p.add_argument("--rev", required=True, help="git sha of the tree the step was proven on")
        if name == "mark":
            p.add_argument("--step", required=True)
            p.add_argument("--evidence", default="", help="short binding: test node id, mutant key, sha of an artifact")
        if name == "status":
            p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    ledger = Path(os.path.expanduser(args.ledger))
    if not args.rev.strip():
        print("--rev must be a non-empty git sha", file=sys.stderr)
        return 2
    if args.cmd == "mark":
        return mark(ledger, args.run, args.phase, args.step, args.rev, args.evidence)
    if args.cmd == "done":
        return done(ledger, args.run, args.phase, args.rev)
    return status(ledger, args.run, args.phase, args.rev, args.json)


if __name__ == "__main__":
    sys.exit(main())
