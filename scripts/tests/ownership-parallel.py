#!/usr/bin/env python3
"""Run disjoint ownership cells concurrently; retain the existing gate verdict.

Each harness invocation owns a separate mktemp fixture/cache. This adapter
checks complete, unique coverage before emitting one map and summary for
ownership-nightly-gate.sh; it never uses the reporting-only --map option.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

SUMMARY = re.compile(r"GREEN=(\d+)\s+RED=(\d+)\s+AMBIG=(\d+)\s+HARNESS-ERR=(\d+)")


def checked_rows(ids, result):
    """Reject missing/duplicate cells, partial output and incoherent exits."""
    if result.returncode not in (0, 1):
        raise ValueError("harness/infra exit %s" % result.returncode)
    rows = [line for line in result.stdout.splitlines() if re.match(r"^OWN-\d+\s", line)]
    if sorted(line.split()[0] for line in rows) != sorted(ids):
        raise ValueError("observed cell set differs from assigned cells")
    summaries = [SUMMARY.fullmatch(line) for line in result.stdout.splitlines()]
    summaries = [m for m in summaries if m is not None]
    if len(summaries) != 1:
        raise ValueError("expected exactly one complete summary")
    counts = tuple(map(int, summaries[0].groups()))
    statuses = [line.split()[1] for line in rows]
    if any(s not in ("GREEN", "RED") for s in statuses):
        raise ValueError("unexpected cell status (timeout/escape/ambiguity)")
    if counts != (statuses.count("GREEN"), statuses.count("RED"), 0, 0):
        raise ValueError("summary does not match observed rows")
    if result.returncode != int(counts[1] > 0):
        raise ValueError("harness exit does not match RED count")
    return rows


def run_chunk(harness, ids, timeout):
    proc = subprocess.Popen(["bash", str(harness), "--only", ",".join(ids)],
                            text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
        raise ValueError("ownership chunk timed out")
    result = subprocess.CompletedProcess(proc.args, proc.returncode, out, err)
    return checked_rows(ids, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8, choices=range(1, 17))
    parser.add_argument("--chunk-timeout", type=int, default=7200)
    args = parser.parse_args()
    if args.chunk_timeout < 1:
        parser.error("chunk timeout must be positive")
    harness = Path(__file__).with_name("test-ownership-table.sh")
    try:
        listed = subprocess.run(["bash", str(harness), "--list"], check=True,
                                text=True, capture_output=True, timeout=60)
        ids = [line.split()[0] for line in listed.stdout.splitlines() if line.strip()]
        if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r"OWN-\d+", i) for i in ids):
            raise ValueError("invalid or empty harness cell inventory")
        workers = min(args.workers, len(ids))
        chunks = [ids[i::workers] for i in range(workers)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_chunk, harness, chunk, args.chunk_timeout) for chunk in chunks]
            rows = [row for future in futures for row in future.result()]
        if sorted(row.split()[0] for row in rows) != sorted(ids):
            raise ValueError("aggregate cell inventory mismatch")
        for row in sorted(rows):
            print(row)
        reds = sum(row.split()[1] == "RED" for row in rows)
        print("GREEN=%d  RED=%d  AMBIG=0  HARNESS-ERR=0" % (len(rows) - reds, reds))
        return int(reds > 0)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("HARNESS-ERR: parallel ownership: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
