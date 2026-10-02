#!/usr/bin/env python3
"""audit_spool_state.py — read-only verifiers of the audit spool state dir.

PLAN-194 W2 / ADR-055-AMEND-4 (§4.8 names, §6.3 hygiene criteria, §8.2 G3).
One method of counting: ONE listing of the state dir, ``re.fullmatch`` of the
names below, ``lstat`` only where the category needs it.

Modes (exactly one):

``--flux`` (H1)
    ``F = |{p in D : p dead AND audit-pending.<p>.journal is a 0-byte regular
    file with mtime >= since}| / |D|``, where D = the distinct ``pid`` of the
    spool-era entries (``_drain_epoch`` present) of the canonical log and of the
    rotated archives with ``wall_ns`` in ``[since, until)``. Exit 1 when
    ``|D| < --d-min`` (no load, nothing proven) or ``F > --epsilon``. An archive
    whose mtime is older than ``since`` minus one hour is not read: every line in
    it was appended before ``since``, and a line is appended after its ``wall_ns``.
``--residue`` (H2, H3, G3)
    H2: 0-byte journals in the WHOLE state dir (exit 1 above ``--h2-max``).
    H3: lock files counted by NAME, no ``stat`` (``>= --h3-recommend`` only sets
    ``recommend_w2_6``; never the exit). G3: a ``.draining.*``, or an active spool
    with content of a dead PID, older than ``--g3-hours`` (exit 1). A regular file
    counts whatever its ``st_nlink`` (§4.9 forbids DELETING a hardlink, not seeing
    it); hardlinks and non-regular entries are reported apart.

A listed name can vanish or be renamed before it is read (drain, quarantine,
compaction, retention). Every such point is handled, never silent: a rotated
archive that vanishes makes the H1 pass unstable — it is retried up to
``MAX_ATTEMPTS`` and then reported ``inconclusive`` (exit 2); a journal or
a G3 file that vanishes no longer exists, so it is counted in its own cell
(``dead_journal_vanished``, ``vanished``) and not as a residue.

The ``RE_*`` block below is THE name contract shared, byte for byte, with the
amendment text, the W2.6 cleanup script and the ``/ceo-boot`` check: change it
only together with them. ``_parse_spool_pid`` is never reused (``int()`` takes
``_``, spaces, ``+`` and non-ASCII digits).

Read-only by construction: the dirs are opened ``O_RDONLY|O_DIRECTORY|O_NOFOLLOW``,
every file ``O_RDONLY|O_NOFOLLOW`` relative to them; nothing is created, renamed
or removed. The state dir comes ONLY from ``_lib/runtime_paths`` (ADR-001): with
``CEO_AUDIT_LOG_DIR``/``_PATH``/``_ERR`` set the hooks write elsewhere, so the
script refuses. Exit: 0 green, 1 red, 2 usage / refusal / unreadable input.
Datetimes are compared as UTC instants, never as text. Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Set, Tuple

for _anc in Path(__file__).resolve().parents:
    if (_anc / ".claude" / "hooks" / "_lib").is_dir():
        if str(_anc / ".claude" / "hooks") not in sys.path:
            sys.path.insert(0, str(_anc / ".claude" / "hooks"))
        break
from _lib import runtime_paths as _rp  # noqa: E402  # ADR-001 single resolver

# ADR-055-AMEND-4 §4.8 — keep these five lines byte-identical to the amendment.
RE_SPOOL_LOCK   = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl\.lock"
RE_JOURNAL      = r"audit-pending\.([1-9][0-9]{0,9})\.journal"
RE_JOURNAL_LOCK = r"audit-pending\.([1-9][0-9]{0,9})\.journal\.lock"
RE_DRAINING     = r"audit-spool\.([1-9][0-9]{0,9})\.draining\.([0-9a-f]{8})"
RE_ACTIVE_SPOOL = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl"

NAME_PATTERNS: Dict[str, "re.Pattern[str]"] = {
    "spool_lock": re.compile(RE_SPOOL_LOCK, re.ASCII),
    "journal": re.compile(RE_JOURNAL, re.ASCII),
    "journal_lock": re.compile(RE_JOURNAL_LOCK, re.ASCII),
    "draining": re.compile(RE_DRAINING, re.ASCII),
    "active_spool": re.compile(RE_ACTIVE_SPOOL, re.ASCII),
}
LOCK_KINDS = ("spool_lock", "journal_lock")
CANONICAL_LOG = "audit-log.jsonl"
_ROTATED_RX = re.compile(r"audit-log-[0-9]{4}-[0-9]{2}(?:-[1-9][0-9]*)?\.jsonl", re.ASCII)
_ROTATED_SLACK_NS = 3600 * 10 ** 9
MAX_ATTEMPTS = 3
_REFUSED_ENV = ("CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_ERR")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class Refused(Exception):
    """The verifier cannot answer for the resolved state dir (exit 2)."""


def classify(name: str) -> Tuple[Optional[str], Optional[int]]:
    """(kind, pid) of a state-dir name, or (None, None). fullmatch only."""
    for kind, rx in NAME_PATTERNS.items():
        m = rx.fullmatch(name)
        if m:
            return kind, int(m.group(1))
    return None, None


def pid_alive(pid: int) -> bool:
    """Signal-0 probe (spool_writer semantics); a PID that cannot exist is dead."""
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except (OSError, OverflowError, ValueError):
        return False
    return True


def parse_iso_utc(text: str) -> datetime:
    """Timezone-aware ISO 8601 -> UTC; a naive or malformed stamp raises ValueError."""
    t = text.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        raise ValueError("timestamp without timezone: %r" % text)
    return dt.astimezone(timezone.utc)


def to_ns(dt: datetime) -> int:
    return (dt - _EPOCH) // timedelta(microseconds=1) * 1000


class ReadOnlyDir:
    """A resolved dir held by an O_NOFOLLOW fd; every access is relative to it."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd = os.open(str(path), _DIR_FLAGS)

    def close(self) -> None:
        os.close(self.fd)

    def names(self) -> List[str]:
        return os.listdir(self.fd)

    def lstat(self, name: str) -> Optional[os.stat_result]:
        try:
            return os.stat(name, dir_fd=self.fd, follow_symlinks=False)
        except FileNotFoundError:
            return None

    def read(self, name: str) -> Optional[bytes]:
        try:
            fd = os.open(name, _FILE_FLAGS, dir_fd=self.fd)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as fh:
            return fh.read()


def resolve_dirs(project: Optional[str] = None) -> Tuple[Path, Path]:
    """(log family dir, spool state dir), ONLY through the runtime_paths resolver."""
    for var in _REFUSED_ENV:
        if os.environ.get(var):
            raise Refused("%s is set: the hooks' state dir is not the resolver's" % var)
    family = _rp.runtime_state_dir(project)
    return family, family / "state"


def read_listed(d: ReadOnlyDir, name: str, vanished: List[str]) -> bytes:
    """Content of a LISTED regular file; a name gone before lstat or read is
    appended to ``vanished`` (the caller decides what that means)."""
    s = d.lstat(name)
    if s is None:
        vanished.append(name)
        return b""
    if not stat.S_ISREG(s.st_mode) or s.st_size == 0:
        return b""
    data = d.read(name)
    if data is None:
        vanished.append(name)
        return b""
    return data


def read_logs(fam: ReadOnlyDir, since_ns: int, vanished: List[str]) -> Iterator[Tuple[str, bytes]]:
    """Canonical log first (one descriptor; absent while a rotation renames it, and
    then its lines are in the archive listed next), then the rotated archives
    listed AFTER it was read (§8.2). A listed archive that vanishes goes to
    ``vanished``."""
    data = fam.read(CANONICAL_LOG)
    if data:
        yield CANONICAL_LOG, data
    for name in sorted(fam.names()):
        if not _ROTATED_RX.fullmatch(name):
            continue
        s = fam.lstat(name)
        if s is None:
            vanished.append(name)
        elif stat.S_ISREG(s.st_mode) and s.st_mtime_ns >= since_ns - _ROTATED_SLACK_NS:
            yield name, read_listed(fam, name, vanished)


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def spool_era_pids(fam: ReadOnlyDir, since_ns: int, until_ns: int) -> Tuple[Set[int], Dict[str, int]]:
    pids: Set[int] = set()
    seen = {"files_read": 0, "malformed_lines": 0}
    vanished: List[str] = []
    for _name, data in read_logs(fam, since_ns, vanished):
        seen["files_read"] += 1
        for line in data.split(b"\n"):
            if b'"_drain_epoch"' not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                seen["malformed_lines"] += 1
                continue
            if not isinstance(e, dict) or not isinstance(e.get("_drain_epoch"), str):
                continue
            pid, wall = e.get("pid"), e.get("wall_ns")
            if _is_int(pid) and pid > 0 and _is_int(wall) and since_ns <= wall < until_ns:
                pids.add(pid)
    seen["vanished"] = len(vanished)
    return pids, seen


def flux(fam: ReadOnlyDir, st: ReadOnlyDir, since_ns: int, until_ns: int, d_min: int,
         epsilon: float, is_alive: Callable[[int], bool] = pid_alive) -> Dict[str, object]:
    """H1. Liveness is probed AFTER the listing and the reads."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        pids, seen = spool_era_pids(fam, since_ns, until_ns)
        if not seen["vanished"]:
            break
    else:
        return {"mode": "flux", "inconclusive": True, "attempts": MAX_ATTEMPTS, "logs": seen,
                "red": True}
    journals: Dict[int, str] = {}
    for name in st.names():
        m = NAME_PATTERNS["journal"].fullmatch(name)
        if m:
            journals[int(m.group(1))] = name
    cells = {"alive": 0, "dead_zero_in_window": 0, "dead_zero_before_window": 0,
             "dead_with_content": 0, "dead_no_journal": 0, "dead_journal_vanished": 0}
    for pid in sorted(pids):
        s = st.lstat(journals[pid]) if pid in journals else None
        if is_alive(pid):
            cells["alive"] += 1
        elif s is None and pid in journals:
            cells["dead_journal_vanished"] += 1
        elif s is None or not stat.S_ISREG(s.st_mode):
            cells["dead_no_journal"] += 1
        elif s.st_size > 0:
            cells["dead_with_content"] += 1
        elif s.st_mtime_ns >= since_ns:
            cells["dead_zero_in_window"] += 1
        else:
            cells["dead_zero_before_window"] += 1
    n = len(pids)
    f = cells["dead_zero_in_window"] / n if n else None
    return {"mode": "flux", "D": n, "F": f, "cells": cells, "d_min": d_min, "epsilon": epsilon,
            "logs": seen, "attempts": attempt, "inconclusive": False,
            "red": n < d_min or f is None or f > epsilon}


def residue(st: ReadOnlyDir, now_ns: int, g3_hours: float, h2_max: int, h3_recommend: int,
            is_alive: Callable[[int], bool] = pid_alive) -> Dict[str, object]:
    """H2 + H3 + G3 over ONE listing; locks are never stat'ed."""
    counts = {k: 0 for k in NAME_PATTERNS}
    counts.update(journal_zero=0, journal_content=0, hardlinked=0, not_regular=0,
                  vanished=0, orphan_spool_with_content=0)
    g3: List[str] = []
    oldest_s = 0.0
    limit_ns = int(g3_hours * 3600 * 10 ** 9)
    for name in st.names():
        kind, pid = classify(name)
        if kind is None:
            continue
        counts[kind] += 1
        if kind in LOCK_KINDS:
            continue
        s = st.lstat(name)
        if s is None:
            counts["vanished"] += 1
            continue
        if not stat.S_ISREG(s.st_mode):
            counts["not_regular"] += 1
            continue
        counts["hardlinked"] += 1 if s.st_nlink > 1 else 0
        age_ns = now_ns - s.st_mtime_ns
        if kind == "journal":
            counts["journal_zero" if s.st_size == 0 else "journal_content"] += 1
            continue
        if kind == "active_spool":
            if s.st_size == 0 or is_alive(pid or 0):
                continue
            counts["orphan_spool_with_content"] += 1
        oldest_s = max(oldest_s, age_ns / 1e9)
        if age_ns > limit_ns:
            g3.append(name)
    h3 = counts["spool_lock"] + counts["journal_lock"]
    return {"mode": "residue", "counts": counts, "H2": counts["journal_zero"], "h2_max": h2_max,
            "H3": h3, "recommend_w2_6": h3 >= h3_recommend, "G3": sorted(g3),
            "oldest_draining_or_orphan_s": round(oldest_s, 1), "inconclusive": False,
            "red": counts["journal_zero"] > h2_max or bool(g3)}


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="audit_spool_state.py", description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--flux", action="store_true", help="H1 (flux of 0-byte journals)")
    mode.add_argument("--residue", action="store_true", help="H2, H3 and G3")
    ap.add_argument("--since", help="window start, ISO 8601 with timezone (default: now-24h)")
    ap.add_argument("--until", help="window end, ISO 8601 with timezone (default: now)")
    ap.add_argument("--d-min", type=int, default=200)
    ap.add_argument("--epsilon", type=float, default=0.01)
    ap.add_argument("--h2-max", type=int, default=1000)
    ap.add_argument("--h3-recommend", type=int, default=100000)
    ap.add_argument("--g3-hours", type=float, default=24.0)
    ap.add_argument("--project", help="slug input for the resolver (default: CLAUDE_PROJECT_DIR / cwd)")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = _parser().parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        until = parse_iso_utc(args.until) if args.until else now
        since = parse_iso_utc(args.since) if args.since else until - timedelta(hours=24)
        if since >= until:
            raise ValueError("--since must be before --until")
        family, state = resolve_dirs(args.project)
        fam, st = ReadOnlyDir(family), ReadOnlyDir(state)
        try:
            if args.flux:
                rep = flux(fam, st, to_ns(since), to_ns(until), args.d_min, args.epsilon)
                rep.update(since=since.isoformat(), until=until.isoformat())
            else:
                rep = residue(st, time.time_ns(), args.g3_hours, args.h2_max, args.h3_recommend)
        finally:
            fam.close()
            st.close()
    except (Refused, ValueError, OSError) as e:
        sys.stderr.write("audit_spool_state: %s: %s\n" % (type(e).__name__, e))
        return 2
    rep["state_dir"] = str(state)
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 2 if rep["inconclusive"] else (1 if rep["red"] else 0)


if __name__ == "__main__":
    sys.exit(main())
