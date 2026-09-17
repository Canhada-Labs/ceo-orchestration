#!/usr/bin/env python3
"""worktree_lock.py — one writer per worktree (PLAN-190 W2, CLI half).

Why
---
A consumer observed two agent instances writing the same worktree (a
``SendMessage`` to a Workflow agent forked a copy outside the runner) and
recovery rites that could not tell who owned a tree. The order (2026-09-17):
"Garantir exclusividade de escrita por worktree durante execução e recuperação."

Model
-----
Lock file ``<worktree>/.claude/state/writer.lock`` (JSON: ``owner``, ``kind``,
``pid``, ``host``, ``since``, ``heartbeat``, ``ttl_minutes``), created with
``O_EXCL`` (atomic). ``acquire`` by the same owner refreshes the heartbeat;
by a different owner it fails (rc 3) naming the holder — unless the holder's
heartbeat is older than its ``ttl_minutes`` (stale), in which case ``steal``
may take it (never ``acquire``). ``release`` only by the owner (``--force``
for the recovery rite, recorded). Every transition is appended to
``writer.lock.log`` next to the lock.

The enforcing hook (PreToolUse Edit/Write in the worktree) is the canonical
half of this wave; this CLI is what a workflow phase, a recovery rite or a
human calls. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LOCK_REL = Path(".claude") / "state" / "writer.lock"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _parse(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        return None


def lock_path(worktree: Path) -> Path:
    return worktree / LOCK_REL


def read_lock(worktree: Path) -> Optional[Dict[str, Any]]:
    p = lock_path(worktree)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_stale(lock: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    now = now or _now()
    hb = _parse(str(lock.get("heartbeat") or lock.get("since") or ""))
    ttl = lock.get("ttl_minutes")
    if hb is None or not isinstance(ttl, (int, float)):
        return True
    return (now - hb).total_seconds() > float(ttl) * 60.0


def _log(worktree: Path, event: str, lock: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> None:
    p = Path(str(lock_path(worktree)) + ".log")
    rec = {"ts": _iso(_now()), "event": event, "owner": lock.get("owner"), "kind": lock.get("kind")}
    if extra:
        rec.update(extra)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")


def _write_new(p: Path, lock: Dict[str, Any]) -> bool:
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=1) + "\n")
    return True


def _rewrite(p: Path, lock: Dict[str, Any]) -> None:
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(lock, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def acquire(worktree: Path, owner: str, kind: str, ttl_minutes: int) -> int:
    p = lock_path(worktree)
    now = _now()
    fresh = {"owner": owner, "kind": kind, "pid": os.getpid(), "host": socket.gethostname(), "since": _iso(now), "heartbeat": _iso(now), "ttl_minutes": ttl_minutes}
    if _write_new(p, fresh):
        _log(worktree, "acquired", fresh)
        print("ACQUIRED %s by %s" % (worktree, owner))
        return 0
    cur = read_lock(worktree)
    if cur is None:
        print("HELD by an unreadable lock at %s — run `status`/`steal --stale-minutes`" % p, file=sys.stderr)
        return 3
    if cur.get("owner") == owner:
        cur["heartbeat"] = _iso(now)
        cur["pid"] = os.getpid()
        _rewrite(p, cur)
        _log(worktree, "heartbeat", cur)
        print("HELD (refreshed) %s by %s" % (worktree, owner))
        return 0
    print("HELD by %s (%s) since %s%s — a second writer is refused; release or steal when stale" % (
        cur.get("owner"), cur.get("kind"), cur.get("since"), " [STALE]" if is_stale(cur, now) else ""), file=sys.stderr)
    return 3


def release(worktree: Path, owner: str, force: bool) -> int:
    p = lock_path(worktree)
    cur = read_lock(worktree)
    if cur is None:
        if p.exists():
            if not force:
                print("unreadable lock; use --force", file=sys.stderr)
                return 3
            p.unlink()
            print("RELEASED (forced, unreadable)")
            return 0
        print("no lock")
        return 0
    if cur.get("owner") != owner and not force:
        print("HELD by %s — not yours; use --force only in the recovery rite" % cur.get("owner"), file=sys.stderr)
        return 3
    p.unlink()
    _log(worktree, "released" if cur.get("owner") == owner else "force-released", cur, {"by": owner})
    print("RELEASED %s (%s)" % (worktree, "forced by %s" % owner if cur.get("owner") != owner else owner))
    return 0


def steal(worktree: Path, owner: str, kind: str, stale_minutes: float, ttl_minutes: int) -> int:
    p = lock_path(worktree)
    cur = read_lock(worktree)
    now = _now()
    if cur is None and not p.exists():
        return acquire(worktree, owner, kind, ttl_minutes)
    hb = _parse(str((cur or {}).get("heartbeat") or (cur or {}).get("since") or ""))
    age_min = (now - hb).total_seconds() / 60.0 if hb else float("inf")
    if age_min < stale_minutes:
        print("REFUSED: holder %s heartbeat is %.1f min old (< %.1f)" % ((cur or {}).get("owner"), age_min, stale_minutes), file=sys.stderr)
        return 3
    fresh = {"owner": owner, "kind": kind, "pid": os.getpid(), "host": socket.gethostname(), "since": _iso(now), "heartbeat": _iso(now), "ttl_minutes": ttl_minutes, "stolen_from": (cur or {}).get("owner")}
    _rewrite(p, fresh)
    _log(worktree, "stolen", fresh, {"from": (cur or {}).get("owner"), "age_min": round(age_min, 1)})
    print("STOLEN %s from %s (heartbeat %.1f min old)" % (worktree, (cur or {}).get("owner"), age_min))
    return 0


def status(worktree: Path) -> int:
    cur = read_lock(worktree)
    if cur is None:
        print("FREE" if not lock_path(worktree).exists() else "UNREADABLE")
        return 0
    print(json.dumps({"held_by": cur.get("owner"), "kind": cur.get("kind"), "since": cur.get("since"), "heartbeat": cur.get("heartbeat"), "stale": is_stale(cur)}, ensure_ascii=False))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("acquire", "release", "steal", "status"):
        p = sub.add_parser(name)
        p.add_argument("--worktree", required=True)
        if name != "status":
            p.add_argument("--owner", required=True, help="stable identity: agent id, run id, or a human handle")
        if name in ("acquire", "steal"):
            p.add_argument("--kind", default="agent", choices=["agent", "human", "runner"])
            p.add_argument("--ttl-minutes", type=int, default=30)
        if name == "release":
            p.add_argument("--force", action="store_true")
        if name == "steal":
            p.add_argument("--stale-minutes", type=float, required=True)
    args = ap.parse_args(argv)
    wt = Path(os.path.expanduser(args.worktree)).resolve()
    if not wt.is_dir():
        print("worktree not found: %s" % wt, file=sys.stderr)
        return 2
    if args.cmd == "acquire":
        return acquire(wt, args.owner, args.kind, args.ttl_minutes)
    if args.cmd == "release":
        return release(wt, args.owner, args.force)
    if args.cmd == "steal":
        return steal(wt, args.owner, args.kind, args.stale_minutes, args.ttl_minutes)
    return status(wt)


if __name__ == "__main__":
    sys.exit(main())
