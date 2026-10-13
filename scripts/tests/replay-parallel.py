#!/usr/bin/env python3
"""Run every independent replay fixture group; fail closed on lost results.

The shell harness still supports its original serial execution. Each child gets
its own mktemp fixture and install caches. Dependent assertions remain together.
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
import time

SUMMARY = re.compile(r"^== RESULT: PASS=(\d+) FAIL=(\d+) ==$", re.MULTILINE)
EXPECTED_ASSERTIONS = 73
EXPECTED_GROUPS = ("profile", "fallback", "ceremony", "schema",
                   "schema-refusal", "ownership", "tracked")


def checked_result(group, result):
    out = result.stdout
    summaries = SUMMARY.findall(out)
    markers = re.findall(r"^REPLAY-GROUP: (.*)$", out, re.MULTILINE)
    if len(summaries) != 1 or markers != [group]:
        raise ValueError("%s: missing/duplicate summary or wrong group" % group)
    passed, failed = map(int, summaries[0])
    observed = (len(re.findall(r"^  ok   ", out, re.MULTILINE)),
                len(re.findall(r"^  FAIL ", out, re.MULTILINE)))
    if observed != (passed, failed) or passed + failed == 0:
        raise ValueError("%s: assertion rows disagree with summary" % group)
    if result.returncode != int(failed > 0):
        raise ValueError("%s: incomplete execution (exit %s)" % (group, result.returncode))
    return passed, failed


def run_group(harness, group, timeout):
    start = time.monotonic()
    proc = subprocess.Popen(["bash", str(harness), "--group", group],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
        raise ValueError("%s: group timed out" % group)
    result = subprocess.CompletedProcess(proc.args, proc.returncode, out)
    return result, time.monotonic() - start


def execute(harness, workers, timeout):
    listed = subprocess.run(["bash", str(harness), "--list-groups"],
                            check=True, capture_output=True, text=True, timeout=30)
    groups = listed.stdout.splitlines()
    if (set(groups) != set(EXPECTED_GROUPS) or len(groups) != len(set(groups))
            or any(not re.fullmatch(r"[a-z][a-z-]*", g) for g in groups)):
        raise ValueError("invalid replay group inventory")
    passed = failed = 0
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_group, harness, g, timeout): g for g in groups}
        for future in concurrent.futures.as_completed(futures):
            group = futures[future]
            try:
                result, elapsed = future.result()
                print("=== %s (%.3fs) ===" % (group, elapsed), flush=True)
                print(result.stdout, end="", flush=True)
                p, f = checked_result(group, result)
                passed += p
                failed += f
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                errors.append(str(exc))
    if errors or passed + failed != EXPECTED_ASSERTIONS:
        raise ValueError("; ".join(errors + ["complete inventory: %d/%d assertions" %
                                             (passed + failed, EXPECTED_ASSERTIONS)]))
    print("REPLAY-TOTAL: %d passed, %d failed; %d groups" % (passed, failed, len(groups)))
    return int(failed > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=7, choices=range(1, 33))
    parser.add_argument("--group-timeout", type=int, default=7200)
    args = parser.parse_args()
    if args.group_timeout < 1:
        parser.error("group timeout must be positive")
    try:
        return execute(Path(__file__).with_name("test_install_state_replay.sh"),
                       args.workers, args.group_timeout)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print("HARNESS-ERROR: replay parallel: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
