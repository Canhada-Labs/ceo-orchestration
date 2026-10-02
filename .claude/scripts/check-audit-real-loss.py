#!/usr/bin/env python3
"""check-audit-real-loss.py — G6 (real loss) and G7 (direct-writer loss), read-only.

PLAN-194 W2 / ADR-055-AMEND-4 §8.2. Runs outside any hook (LAND V-block,
nightly, ``/ceo-boot``); ``--since`` is the LAND stamp.

**G6.** A ``record_id`` with a ``commit`` envelope in a per-PID journal (or the
aggregate journal) and ``wall_ns >= since`` that is neither in the canonical log
nor in a rotated archive nor in any spool-side file. Reading order, so a record
in transit is never called lost: (0) the journals; (1) a FRESH listing of the
spool side — active spools and ``.draining.*`` (PENDING) and the quarantine
files ``.malformed.*``/``.quarantined.*``/``.test-origin.*``/``.corrupt-header.*``
(QUARANTINED, never lost); (2) the canonical log through one descriptor; (3) the
rotated archives, listed after it. A record only moves spool -> log (append
before unlink) and rotation renames the log. Every loss candidate is re-checked
by a second full pass of (1)-(3) before it is reported. Lower bound: a ``commit``
that never left the in-memory journal buffer is invisible. Log lines count by
their TOP-LEVEL ``record_id``; a spool-side line that is not JSON (quarantine)
is searched with ``_RID_RX``.

**G7.** ``audit_log`` lines (``[ts]`` stamp) ``lock timeout (stale?)  would-log=``
or ``append failed:`` in ``audit-log.errors`` stamped at or after ``since``. The
line parser reads BOTH stamp formats (``[AAAA-MM-DDTHH:MM:SSZ] ...`` of
``audit_log`` and ``AAAA-MM-DDTHH:MM:SSZ <writer>: ...``, §4.8 — the bare stamp is
shared by ``spool_writer``, ``audit_emit`` and ``check_budget``, so a class is
keyed on the WRITER too) and also reports, never as G7, the ``STARVED`` lines (G8
``(exit)`` and the AMEND-3 opportunistic one) and ``drain canonical lock timeout``
(G2). A line with no stamp, or an impossible date, is counted as ``unparsed``.

Names, resolver, refusal and read-only discipline come from
``audit_spool_state.py``. Exit: 0 clean; 1 G6 loss > 0 or G7 > 0; 2 usage,
refusal or unreadable input. Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_spool_state as ss  # noqa: E402

RE_QUARANTINE = (r"audit-spool\.([1-9][0-9]{0,9})"
                 r"\.(?:malformed|quarantined|test-origin|corrupt-header)\.([0-9a-f]{8})")
_QUARANTINE_RX = re.compile(RE_QUARANTINE, re.ASCII)
AGGREGATE_JOURNAL = "audit-pending.journal"
ERRORS_FILE = "audit-log.errors"
_RID_RX = re.compile(rb'"record_id"\s*:\s*"([0-9a-f]{32})"')
_STAMP = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
RE_ERR_LINE = r"(?:\[(%s)\] |(%s) ([A-Za-z_][A-Za-z0-9_]*): )(.*)" % (_STAMP, _STAMP)
_ERR_LINE_RX = re.compile(RE_ERR_LINE, re.ASCII)
# (class, source, message prefix); first match wins. Only the g7_* classes are G7.
ERR_CLASSES = (
    ("g7_would_log", "audit_log", "lock timeout (stale?)  would-log="),
    ("g7_append_failed", "audit_log", "append failed:"),
    ("g8_starved_exit", "spool_writer", "drain canonical lock STARVED (exit)"),
    ("starved_opportunistic", "spool_writer", "drain canonical lock STARVED:"),
    ("g2_canonical_lock_timeout", "spool_writer", "drain canonical lock timeout"),
)


def _is_int(v: object) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _plain(d: ss.ReadOnlyDir, name: str) -> Optional[bytes]:
    s = d.lstat(name)
    if s is None or not stat.S_ISREG(s.st_mode) or s.st_size == 0:
        return None
    return d.read(name)


def record_ids(data: bytes, top_level_only: bool) -> Set[str]:
    out: Set[str] = set()
    for line in data.split(b"\n"):
        if b'"record_id"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            if not top_level_only:
                out.update(m.decode("ascii") for m in _RID_RX.findall(line))
            continue
        if isinstance(e, dict) and isinstance(e.get("record_id"), str):
            out.add(e["record_id"])
    return out


def journal_commits(st: ss.ReadOnlyDir, since_ns: int) -> Tuple[Set[str], int]:
    commits: Set[str] = set()
    malformed = 0
    for name in st.names():
        if name != AGGREGATE_JOURNAL and not ss.NAME_PATTERNS["journal"].fullmatch(name):
            continue
        for line in (_plain(st, name) or b"").split(b"\n"):
            if not line.strip():
                continue
            try:
                env = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if (isinstance(env, dict) and env.get("op") == "commit"
                    and isinstance(env.get("record_id"), str)
                    and _is_int(env.get("wall_ns")) and env["wall_ns"] >= since_ns):
                commits.add(env["record_id"])
    return commits, malformed


def snapshot(fam: ss.ReadOnlyDir, st: ss.ReadOnlyDir, since_ns: int) -> Dict[str, Set[str]]:
    """Steps (1)-(3) of the reading order, from fresh listings."""
    snap: Dict[str, Set[str]] = {"pending": set(), "quarantined": set(), "logged": set()}
    for name in st.names():
        kind, _ = ss.classify(name)
        if kind in ("active_spool", "draining"):
            key = "pending"
        elif _QUARANTINE_RX.fullmatch(name):
            key = "quarantined"
        else:
            continue
        snap[key] |= record_ids(_plain(st, name) or b"", top_level_only=False)
    for name in ss.log_names(fam, since_ns):
        snap["logged"] |= record_ids(_plain(fam, name) or b"", top_level_only=True)
    return snap


def g6(fam: ss.ReadOnlyDir, st: ss.ReadOnlyDir, since_ns: int) -> Dict[str, object]:
    commits, malformed = journal_commits(st, since_ns)
    lost = set(commits)
    pending: Set[str] = set()
    quarantined: Set[str] = set()
    for _ in range(2):  # the second pass re-checks every candidate
        if not lost:
            break
        snap = snapshot(fam, st, since_ns)
        lost -= snap["logged"]
        quarantined |= lost & snap["quarantined"]
        lost -= snap["quarantined"]
        pending |= lost & snap["pending"]
        lost -= snap["pending"]
    return {"commits": len(commits), "pending": len(pending), "quarantined": len(quarantined),
            "lost": len(lost), "lost_record_ids": sorted(lost)[:50],
            "journal_malformed_lines": malformed}


def g7(fam: ss.ReadOnlyDir, since: datetime) -> Dict[str, object]:
    counts = {cls: 0 for cls, _, _ in ERR_CLASSES}
    counts.update(lines_in_window=0, unparsed=0)
    data = _plain(fam, ERRORS_FILE) or b""
    for raw in data.decode("utf-8", errors="replace").split("\n"):
        m = _ERR_LINE_RX.fullmatch(raw)
        try:
            ts = datetime.strptime(m.group(1) or m.group(2), "%Y-%m-%dT%H:%M:%SZ") if m else None
        except ValueError:
            ts = None
        if ts is None:
            counts["unparsed"] += 1 if raw else 0
            continue
        if ts.replace(tzinfo=timezone.utc) < since:
            continue
        counts["lines_in_window"] += 1
        source = "audit_log" if m.group(1) else m.group(3)
        for cls, src, prefix in ERR_CLASSES:
            if src == source and m.group(4).startswith(prefix):
                counts[cls] += 1
                break
    counts["G7"] = counts["g7_would_log"] + counts["g7_append_failed"]
    return counts


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="check-audit-real-loss.py", description=__doc__.split("\n")[0])
    ap.add_argument("--since", required=True, help="LAND stamp, ISO 8601 with timezone")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--g6", action="store_true", help="only G6 (real loss)")
    which.add_argument("--g7", action="store_true", help="only G7 (would-log / append failed)")
    ap.add_argument("--project", help="slug input for the resolver (default: CLAUDE_PROJECT_DIR / cwd)")
    args = ap.parse_args(argv)
    rep: Dict[str, object] = {}
    try:
        since = ss.parse_iso_utc(args.since)
        family, state = ss.resolve_dirs(args.project)
        fam = ss.ReadOnlyDir(family)
        try:
            if not args.g7:
                st = ss.ReadOnlyDir(state)
                try:
                    rep["g6"] = g6(fam, st, ss.to_ns(since))
                finally:
                    st.close()
            if not args.g6:
                rep["g7"] = g7(fam, since)
        finally:
            fam.close()
    except (ss.Refused, ValueError, OSError) as e:
        sys.stderr.write("check-audit-real-loss: %s: %s\n" % (type(e).__name__, e))
        return 2
    rep.update(since=since.isoformat(), state_dir=str(state))
    red = bool(rep.get("g6", {}).get("lost")) or bool(rep.get("g7", {}).get("G7"))
    rep["red"] = red
    print(json.dumps(rep, indent=1, sort_keys=True))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
