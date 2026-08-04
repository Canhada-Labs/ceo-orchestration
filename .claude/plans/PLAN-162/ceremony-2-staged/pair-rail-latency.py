#!/usr/bin/env python3
"""pair-rail-latency.py — the ADR-110-AMEND-2 §3 recalibration query, as a
versioned, reproducible instrument.

WHY THIS IS A SCRIPT AND NOT A DOC SNIPPET (AMEND-2 §3, AQ2 resolved):
the AMEND-1 §3 query was normative TEXT pointing at a single ``LOG`` file.
It failed twice, in two different ways, and both failures were silent:

1. after the monthly rotation it returns ``n=0`` (the file it names holds
   no pair-rail events any more) — the bug this amendment fixes;
2. worse, on 2026-08-03 a hand-run union glob read 7 of 8 files and
   returned a SUBSET (n=14) whose p95 supported the desired conclusion
   where the full set (n=20) did not. A gate that answers with the wrong
   number is the vacuous-gate class in its worst form.

So the instrument prints its INPUTS, not just its result: every file read
with its mtime, the case histogram, how many F events were dropped for
lacking ``review_id`` (pre-PLAN-161 schema), the true orphan count, the
censoring rate, and the ``ts`` cutoff. A governance verdict has to be
reproducible by a third party.

Stdlib only, Python >= 3.9.

Usage:
    python3 .claude/scripts/local/pair-rail-latency.py [--json]
    python3 .claude/scripts/local/pair-rail-latency.py --since 2026-07-29
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_HEALTHY_CASES = ("A", "B", "C", "D", "E")


def _dt(ts: str) -> datetime:
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _audit_dir() -> str:
    override = os.environ.get("CEO_AUDIT_LOG_PATH")
    if override:
        return os.path.dirname(override)
    return os.path.expanduser("~/.claude/projects/ceo-orchestration")


def _log_files(audit_dir: str) -> List[str]:
    """Rotated archives + the live log. The union is the whole point."""
    rotated = sorted(glob.glob(os.path.join(audit_dir, "audit-log-*.jsonl")))
    live = os.path.join(audit_dir, "audit-log.jsonl")
    files = [f for f in rotated if os.path.isfile(f)]
    if os.path.isfile(live):
        files.append(live)
    return files


def collect(files: List[str], since: Optional[datetime]) -> Dict:
    expected: Dict[Tuple[str, str], datetime] = {}
    healthy: List[Tuple[float, datetime]] = []
    censored: List[Tuple[float, datetime]] = []
    cases: Dict[str, int] = {}
    dropped_no_review_id = 0

    for path in files:
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = ev.get("action")
                if action not in ("pair_rail_review_expected", "pair_rail_case"):
                    continue
                review_id = str(ev.get("review_id") or "")
                ts = ev.get("ts") or ev.get("timestamp")
                if action == "pair_rail_case":
                    case = str(ev.get("case") or "?")
                    cases[case] = cases.get(case, 0) + 1
                    if not review_id:
                        dropped_no_review_id += 1
                if not review_id or not ts:
                    continue
                key = (str(ev.get("session_id") or ""), review_id)
                if action == "pair_rail_review_expected":
                    expected[key] = _dt(ts)
                    continue
                start = expected.pop(key, None)
                if start is None:
                    continue
                end = _dt(ts)
                delta = (end - start).total_seconds()
                bucket = healthy if ev.get("case") in _HEALTHY_CASES else censored
                bucket.append((delta, end))

    def _filt(rows):
        return sorted(d for d, when in rows if since is None or when >= since)

    h, c = _filt(healthy), _filt(censored)
    all_ts = [when for _, when in healthy + censored]
    total = len(h) + len(c)
    out = {
        "files": [
            {"path": p, "mtime": datetime.fromtimestamp(
                os.path.getmtime(p), timezone.utc).isoformat()}
            for p in files
        ],
        "since": since.isoformat() if since else None,
        "case_histogram": dict(sorted(cases.items())),
        "dropped_no_review_id": dropped_no_review_id,
        "true_orphans": len(expected),
        "n_healthy": len(h),
        "n_censored": len(c),
        "healthy_latencies_s": [int(x) for x in h],
        "censored_latencies_s": [int(x) for x in c],
        "ts_cutoff": max(all_ts).isoformat() if all_ts else None,
    }
    if h:
        out["median_s"] = round(statistics.median(h), 1)
        out["max_observed_s"] = int(max(h))
        if len(h) >= 2:
            out["p95_interpolated_s"] = round(statistics.quantiles(h, n=20)[18], 1)
        idx = int(-(-0.95 * len(h)) // 1) - 1
        out["p95_empirical_s"] = int(h[idx])
    if total:
        out["censoring_rate_pct"] = round(100.0 * len(c) / total, 1)
        budget = float(os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "120") or 120)
        at_or_over = len([x for x in h if x >= budget]) + len(
            [x for x in c if x >= budget])
        out["budget_s"] = budget
        out["at_or_over_budget_pct"] = round(100.0 * at_or_over / total, 1)
        # The counting argument: if more than 5% of reviews sit at or above
        # the budget, the TRUE p95 is >= the budget by count — no
        # interpolation, no extrapolation above the observed maximum.
        out["p95_ge_budget_by_count"] = (at_or_over / total) > 0.05
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable")
    ap.add_argument("--since", default=None,
                    help="ISO date; restrict to cases ending at/after it "
                         "(e.g. the uplift ceremony date)")
    args = ap.parse_args()
    since = _dt(args.since) if args.since else None
    data = collect(_log_files(_audit_dir()), since)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("=== pair-rail latency (ADR-110-AMEND-2 §3 instrument) ===")
    print("inputs read (union of rotated archives + live log):")
    for f in data["files"]:
        print("  %s  (mtime %s)" % (os.path.basename(f["path"]), f["mtime"]))
    if data["since"]:
        print("since: %s" % data["since"])
    print("")
    print("case histogram (all pair_rail_case on disk): %s" % data["case_histogram"])
    print("F/other dropped from the join (no review_id, pre-PLAN-161): %d"
          % data["dropped_no_review_id"])
    print("true orphans (review_expected with NO case at all): %d"
          % data["true_orphans"])
    print("")
    print("n healthy  = %d   %s" % (data["n_healthy"], data["healthy_latencies_s"]))
    print("n censored = %d   %s" % (data["n_censored"], data["censored_latencies_s"]))
    if "median_s" in data:
        print("median = %.1fs | p95 interp = %s | p95 empirical = %ds | max = %ds"
              % (data["median_s"], data.get("p95_interpolated_s", "n/a"),
                 data["p95_empirical_s"], data["max_observed_s"]))
    if "censoring_rate_pct" in data:
        print("censoring rate = %.1f%%   (>= budget %.0fs: %.1f%%)"
              % (data["censoring_rate_pct"], data["budget_s"],
                 data["at_or_over_budget_pct"]))
        print("p95 >= budget BY COUNT: %s" % data["p95_ge_budget_by_count"])
    print("ts cutoff (newest event used): %s" % data["ts_cutoff"])
    print("")
    print("NOTE: the dataset moves while it is measured — an active session")
    print("generates samples AND can rotate the log mid-run. Freeze the")
    print("cutoff above into any amendment that cites these numbers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
