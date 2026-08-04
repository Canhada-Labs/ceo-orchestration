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
import re
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


# The rotated-archive name shape, mirroring the retention authority
# (`.claude/scripts/audit-log-retain.py:_ARCHIVE_RE`) with the fields
# captured. The ROTATION authority is `_lib/audit_rotation.py`: the BASE
# name `audit-log-<YYYY-MM>.jsonl` is claimed FIRST and the `-N` counters
# are collision suffixes, so the base file is the OLDEST of its month.
_ARCHIVE_RE = re.compile(r"^audit-log-(\d{4})-(\d{2})(?:-(\d+))?\.jsonl$")


def _archive_sort_key(path: str) -> Tuple[int, int, int, int, str]:
    """Chronological sort key for a rotated archive.

    CODEX S292 REVIEW ROUND 3 (P2). `sorted(glob(...))` is LEXICOGRAPHIC,
    which is not the rotation sequence, in two ways at once:

        audit-log-2026-08-1.jsonl  < audit-log-2026-08.jsonl    ('-' < '.')
        audit-log-2026-08-10.jsonl < audit-log-2026-08-2.jsonl  ('1' < '2')

    The first one is live in this repo's audit dir TODAY: audit-log-2026-08
    .jsonl carries an mtime two days OLDER than -1..-4 and sorted last. The
    second arrives at the tenth rotation of any month.

    A pair whose ``review_expected`` and ``pair_rail_case`` straddled such a
    boundary was destroyed by the misordering — the case arrived first, found
    no expected row, and was dropped; the expected row was then reported as
    an ORPHAN. That corrupts the latency samples AND the censoring rate, i.e.
    exactly the numbers ADR-110-AMEND-2 §3 is decided on. An instrument that
    silently reports the wrong number is the vacuous-gate class this script
    was written to retire, so it may not carry an instance of it.

    Names that do NOT match the convention (e.g. the hand-made
    ``audit-log-2026-05-21-pre-fix-tampered.jsonl`` referenced in
    audit_hmac.py) sort AFTER every conforming archive, deterministically by
    name. Their true vintage is unknowable from the filename, so this is a
    presentation choice, not a correctness one: `collect()` sorts EVENTS by
    timestamp, so the join no longer depends on file order at all. The input
    SET is deliberately unchanged — dropping a file would change the
    measurement, which is the operator's call and not this fix's.
    """
    m = _ARCHIVE_RE.match(os.path.basename(path))
    if not m:
        return (1, 0, 0, 0, os.path.basename(path))
    return (0, int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), "")


def _log_files(audit_dir: str) -> List[str]:
    """Rotated archives + the live log. The union is the whole point."""
    rotated = sorted(
        glob.glob(os.path.join(audit_dir, "audit-log-*.jsonl")),
        key=_archive_sort_key,
    )
    live = os.path.join(audit_dir, "audit-log.jsonl")
    files = [f for f in rotated if os.path.isfile(f)]
    if os.path.isfile(live):
        files.append(live)
    return files


def collect(files: List[str], since: Optional[datetime],
            args_budget: Optional[float] = None) -> Dict:
    expected: Dict[Tuple[str, str], datetime] = {}
    healthy: List[Tuple[float, datetime]] = []
    censored: List[Tuple[float, datetime]] = []
    cases: Dict[str, int] = {}
    dropped_no_review_id = 0
    dropped_bad_ts = 0

    # READ, then JOIN — deliberately two phases (codex S292 r3 P2).
    #
    # The join is a stream fold: a `pair_rail_case` pops the `review_expected`
    # it belongs to, so an out-of-order read DESTROYS the pair (the case finds
    # nothing and is dropped; the expected row is later counted as an orphan).
    # Sorting the FILES correctly is necessary but not sufficient — a
    # non-conforming archive name, a restored backup, or a future change to
    # the rotation convention would each re-open it silently.
    #
    # So the events are collected first and the fold runs over them in
    # TIMESTAMP order. File order then only affects the printed input list,
    # and the measurement stops depending on a filename convention it does not
    # own. Cost: the two pair-rail actions are held in memory — 41 joinable
    # events across 11 files in the live dataset.
    #
    # Tiebreak (file index, line number) keeps append order for events sharing
    # a timestamp, and `rank` puts `review_expected` ahead of a `pair_rail_case`
    # stamped the same second — otherwise a sub-second review would pop nothing.
    rows: List[Tuple[datetime, int, int, int, str, str, dict]] = []

    for file_index, path in enumerate(files):
        try:
            fh = open(path, encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for line_no, line in enumerate(fh):
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
                try:
                    when = _dt(ts)
                except ValueError:
                    # An unparseable timestamp cannot be ordered. Dropped
                    # rather than crashing the whole measurement — but in its
                    # OWN counter: folding it into `dropped_no_review_id`
                    # labelled timestamp corruption as a legacy missing-id
                    # event and hid a real input defect behind a benign
                    # hygiene number (Codex r4 P3).
                    dropped_bad_ts += 1
                    continue
                rank = 0 if action == "pair_rail_review_expected" else 1
                rows.append((when, rank, file_index, line_no,
                             str(ev.get("session_id") or ""), review_id, ev))

    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3]))

    for when, rank, _fi, _ln, session_id, review_id, ev in rows:
        key = (session_id, review_id)
        if rank == 0:
            expected[key] = when
            continue
        start = expected.pop(key, None)
        if start is None:
            continue
        delta = (when - start).total_seconds()
        bucket = healthy if ev.get("case") in _HEALTHY_CASES else censored
        # Codex r6 P2: cada review é pontuada contra O SEU PRÓPRIO budget.
        # `timeout_ms` (ADR-110-AMEND-2 §1.6) existe justamente para
        # desambiguar a sessão que exportou um CEO_PAIR_RAIL_TIMEOUT_S
        # baixo de um outage real; descartá-lo e comparar tudo contra um
        # `--budget-s` global reintroduz a ambiguidade que o campo fecha —
        # e erra exatamente nas linhas sub-floor. O `--budget-s` passa a
        # valer só para as linhas LEGADAS (pré-campo).
        ev_ms = ev.get("timeout_ms")
        try:
            ev_budget = (float(ev_ms) / 1000.0) if ev_ms is not None else None
        except (TypeError, ValueError):
            ev_budget = None
        # `timeout_ms == 0` é a SENTINELA documentada de "budget desconhecido"
        # do emissor tipado — não um orçamento de zero segundo. Tratá-lo como
        # número faria toda latência >= 0 contar como at-or-over e inflaria a
        # taxa de censura (codex r7 P2). Cai no budget do CLI, como legado.
        if ev_budget is not None and ev_budget <= 0:
            ev_budget = None
        bucket.append((delta, when, ev_budget))

    def _filt(rows):
        return sorted(r[0] for r in rows if since is None or r[1] >= since)

    def _filt_pairs(rows):
        """(latency, budget-em-vigor) — budget do evento, senão o do CLI."""
        return [(r[0], r[2]) for r in rows if since is None or r[1] >= since]

    h, c = _filt(healthy), _filt(censored)
    hp, cp = _filt_pairs(healthy), _filt_pairs(censored)
    all_ts = [r[1] for r in healthy + censored]
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
        "dropped_bad_timestamp": dropped_bad_ts,
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
        # The budget a sample must be compared against is the one that was
        # IN FORCE WHEN THE SAMPLE WAS TAKEN — it is a property of the
        # dataset, not of the current tree. Two failure modes, both real:
        #   * a stale default (120 after the ratification) measures new data
        #     against a retired budget (amend2 NOTES §6.2);
        #   * a "current" default (180) silently re-scores the FROZEN
        #     historical evidence of ADR-110-AMEND-2 §2 — collected under
        #     120 — and turns the cited 7/27 at-or-over into 0/27, making
        #     the amendment's own evidence irreproducible (Codex r4 P2).
        # So the budget is an EXPLICIT argument with no silent default:
        # `--budget-s`, else CEO_PAIR_RAIL_TIMEOUT_S, else fail loudly. Any
        # command that cites a number must therefore state the budget that
        # produced it.
        budget = float(args_budget) if args_budget is not None else None
        if budget is None:
            env_budget = os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S")
            if env_budget:
                budget = float(env_budget)
        if budget is not None and not (budget > 0 and budget == budget
                                       and budget != float("inf")):
            # Codex r5 P2: NaN/inf/<=0 produziriam comparações silenciosamente
            # sem sentido (`x >= nan` é sempre False -> censoring 0%).
            raise SystemExit(
                "pair-rail-latency: --budget-s must be a finite positive "
                "number (got %r)." % (budget,)
            )
        if budget is None:
            raise SystemExit(
                "pair-rail-latency: --budget-s is REQUIRED (no default).\n"
                "  Historical evidence of ADR-110-AMEND-2 §2 (frozen cutoff "
                "2026-08-03T19:16:53Z): --since 2026-07-29 --budget-s 120\n"
                "  Post-amendment measurements:                --budget-s 180\n"
                "A percentile/censoring number without its budget is "
                "uninterpretable."
            )
        # Por-evento quando o log traz `timeout_ms`; `budget` (CLI) só para
        # as linhas legadas. Contabiliza quantas usaram cada rota, para que
        # o número venha com a procedência (Codex r6 P2).
        legacy_rows = 0
        at_or_over = 0
        for _lat, _b in (hp + cp):
            if _b is None:
                legacy_rows += 1
                _b = budget
            if _lat >= _b:
                at_or_over += 1
        out["rows_scored_by_event_budget"] = len(hp + cp) - legacy_rows
        out["rows_scored_by_cli_budget"] = legacy_rows
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
    ap.add_argument("--budget-s", type=float, default=None,
                    help="REQUIRED: the budget in force WHEN THE DATA WAS "
                         "TAKEN (120 for the frozen ADR-110-AMEND-2 §2 "
                         "evidence; 180 post-amendment). No default — a "
                         "censoring rate without its budget is "
                         "uninterpretable (Codex r4 P2).")
    ap.add_argument("--since", default=None,
                    help="ISO date; restrict to cases ending at/after it "
                         "(e.g. the uplift ceremony date)")
    args = ap.parse_args()
    since = _dt(args.since) if args.since else None
    data = collect(_log_files(_audit_dir()), since, args.budget_s)

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
    print("  dropped (unparseable ts):    %d"
          % data.get("dropped_bad_timestamp", 0))
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
