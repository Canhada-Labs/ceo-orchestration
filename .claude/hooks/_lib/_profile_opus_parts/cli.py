"""Extracted implementation: cli."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple



def main() -> int:
    """CLI entrypoint — profile Opus 4.7 token/latency under the Gate-1 load."""
    parser = argparse.ArgumentParser(
        description="Opus 4.7 framework optimization profiler (PLAN-020)"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Synthetic CI-safe mode (no API). ≤30s budget.",
    )
    parser.add_argument(
        "--floor",
        action="store_true",
        help="Re-measure python3 subprocess startup floor (Phase 0 item 8).",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Full baseline capture (requires API + audit log; deferred).",
    )
    parser.add_argument(
        "--hook-latency",
        dest="hook_latency",
        action="store_true",
        help=(
            "Measure warm p95/p99 latency of the hook corpus (N=200 default): "
            "check_agent_spawn + the PLAN-154 observe-rail host hooks "
            "(check_anti_ceo_overhead record_pre carrier, check_output_secrets "
            "record_post path) in BOTH CEO_LEARNING_OBSERVE states, with "
            "anti-vacuity store controls. Exits non-zero if any entry's p95 "
            "exceeds --p95-ceiling-ms / p99 exceeds --p99-ceiling-ms, or a "
            "control fails. Fixes E12-F4 + PLAN-154 constraint 8."
        ),
    )
    parser.add_argument(
        "--latency-iterations",
        dest="latency_iterations",
        type=int,
        default=200,
        help="Warm iteration count for --hook-latency (default 200; ADR-163 percentile-stability standard, minimum 22).",
    )
    parser.add_argument(
        "--p95-ceiling-ms",
        dest="p95_ceiling_ms",
        type=float,
        default=180.0,
        help=(
            "p95 failure ceiling in ms for --hook-latency (default 180ms; "
            "ADR-163 S318 recalibration — was 120ms)."
        ),
    )
    parser.add_argument(
        "--p99-ceiling-ms",
        dest="p99_ceiling_ms",
        type=float,
        default=160.0,
        help="p99 ceiling in ms for --hook-latency (default 160ms).",
    )
    parser.add_argument(
        "--p99-advisory",
        dest="p99_advisory",
        action="store_true",
        help=(
            "Report p99 breaches per entry (p99_within=false + WARN on "
            "stderr) WITHOUT failing the gate (ADR-163 S318 amendment: on "
            "a shared runner the extreme tail prices the runner, not the "
            "code). Default off — p99 stays a hard ceiling for back-compat."
        ),
    )
    parser.add_argument(
        "--exec-reference",
        dest="exec_reference",
        action="store_true",
        help=(
            "ADR-163 Amendment (PLAN-169 S328): also sample a FROZEN, "
            "stdlib-only 3-term EXECUTION reference (cold imports + fixed "
            "re.compile set; fixed CPU hash loop; open/append/flock/fsync/"
            "rename on the audit dir's filesystem), round-robin-interleaved "
            "inside each corpus entry's own loop. Publishes ref_p50_ms / "
            "ref_p95_ms / ref_split_half_drift per entry and a global "
            "ref_source_sha256. The spawn probe (python3 -c pass) prices "
            "process CREATION and is blind to a slow-but-uncontended runner; "
            "this prices EXECUTION."
        ),
    )
    parser.add_argument(
        "--relative-advisory",
        dest="relative_advisory",
        action="store_true",
        help=(
            "Publish the runner-normalized second key per entry: R_e = "
            "hook_p50/ref_p50 and verdict_label in {pass, "
            "advisory_slow_runner, real_regression, "
            "infrastructure_contended}. PHASE 1 — the labels are "
            "INFORMATION used to derive K_e later; exit codes stay "
            "byte-identical to the absolute-key contract."
        ),
    )
    parser.add_argument(
        "--relative-k-source",
        dest="relative_k_source",
        type=str,
        default=None,
        help=(
            "PHASE 2 (inert without this file): JSON of the form "
            '{\"entries\": {\"<entry>\": {\"K\": <float>, '
            '\"admissibility_max_K\": <float>}}}. With a usable K_e the '
            "relative key DECIDES the exit (0 pass / 0 advisory_slow_runner "
            "/ 1 real_regression / 5 infrastructure_contended). An entry "
            "with no usable K stays on phase 1 and is WARNed about."
        ),
    )
    parser.add_argument(
        "--wall-budget-seconds",
        dest="wall_budget_seconds",
        type=float,
        default=420.0,
        help=(
            "Self-cap for --hook-latency when the second key is enabled "
            "(default 420s, matching the CI wrapper's `timeout 420`). "
            "Measurement stops at 0.9x this budget and the run is labelled "
            "infrastructure_contended, so the wrapper's opaque rc 124 stays "
            "unreachable. Inert without the second-key flags."
        ),
    )
    parser.add_argument(
        "--budget-seconds",
        type=float,
        default=30.0,
        help="Smoke mode wall-clock budget (default 30s).",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()),
        help="Repo root (default: $CLAUDE_PROJECT_DIR or cwd).",
    )

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    modes = sum([args.smoke, args.floor, args.baseline, args.hook_latency])
    if modes != 1:
        print(
            "ERROR: pass exactly one of --smoke / --floor / --baseline / --hook-latency",
            file=sys.stderr,
        )
        return 1

    if args.baseline:
        print(
            "ERROR: --baseline requires Owner sentinel for hook modifications "
            "(audit_log.py v2.7). Deferred to next session.",
            file=sys.stderr,
        )
        return 1

    try:
        if args.smoke:
            result = run_smoke(repo_root, args.budget_seconds)
            json.dump(result, sys.stdout, indent=2)
            print()
            if not result["within_budget"]:
                print(
                    f"WARN: smoke exceeded budget {args.budget_seconds}s "
                    f"(actual {result['elapsed_ms']}ms)",
                    file=sys.stderr,
                )
                return 2
            failed = [
                c["name"] for c in result.get("checks", []) if not c.get("passed")
            ]
            if failed:
                print(
                    f"FAIL: {len(failed)} smoke check(s) failed: {failed}",
                    file=sys.stderr,
                )
                return 1
            return 0
        elif args.floor:
            result = run_floor()
            json.dump(result, sys.stdout, indent=2)
            print()
            return 0
        elif args.hook_latency:
            result = run_hook_latency(
                repo_root,
                iterations=args.latency_iterations,
                p95_ceiling_ms=args.p95_ceiling_ms,
                p99_ceiling_ms=args.p99_ceiling_ms,
                p99_advisory=args.p99_advisory,
                exec_reference=args.exec_reference,
                relative_advisory=args.relative_advisory,
                relative_k_source=args.relative_k_source,
                wall_budget_seconds=args.wall_budget_seconds,
            )
            json.dump(result, sys.stdout, indent=2)
            print()
            # ADR-163 Amendment (PLAN-169 S328): every relative-key line goes
            # to STDERR. stdout carries the JSON report (the CI wrapper
            # redirects it to a file), so a `::warning::` written there would
            # be swallowed into the report instead of annotating the run —
            # the workflow's publish() step is the step-summary channel.
            for warn_line in result.get("relative_warnings", []) or []:
                print("WARN: %s" % warn_line, file=sys.stderr)
            advisory_entries = [
                name
                for name, stats in sorted(result.get("hooks", {}).items())
                if isinstance(stats, dict)
                and stats.get("verdict_label") == "advisory_slow_runner"
            ]
            if advisory_entries:
                print(
                    "::warning::hook latency AMNESTY (advisory_slow_runner) — "
                    + "; ".join(
                        "%s p50=%.1fms ref_p50=%.1fms R=%s K=%s"
                        % (
                            name,
                            result["hooks"][name].get("p50_ms", 0.0),
                            result["hooks"][name].get("ref_p50_ms", 0.0),
                            result["hooks"][name].get("R_e"),
                            result["hooks"][name].get("K_e"),
                        )
                        for name in advisory_entries
                    ),
                    file=sys.stderr,
                )
                print(
                    "SUMMARY: %d/%d corpus entries breached the absolute p95 "
                    "ceiling but held the relative key against the execution "
                    "reference measured in the SAME window — the runner "
                    "moved, not the hooks (ADR-163 Amendment PLAN-169 S328)."
                    % (len(advisory_entries), len(result.get("hooks", {}))),
                    file=sys.stderr,
                )
            if args.p99_advisory:
                # ADR-163 S318: advisory p99 — breaches are ECHOED so the
                # drift stays visible in the CI log / step summary, but the
                # exit code never keys on them.
                p99_breaches = [
                    f"{name} p99={stats['p99_ms']:.1f}ms"
                    for name, stats in sorted(result.get("hooks", {}).items())
                    if isinstance(stats, dict)
                    and stats.get("p99_within") is False
                ]
                if p99_breaches:
                    print(
                        "WARN: hook latency p99 advisory breach — "
                        + "; ".join(p99_breaches)
                        + f" (advisory ceiling p99<"
                        f"{result.get('p99_ceiling_ms')}ms; exit unchanged)",
                        file=sys.stderr,
                    )
            # PHASE 1 keeps `exit_class == (0 if passed else 1)` by
            # construction, so this reduces to today's contract; PHASE 2 is
            # the only state that can return 5.
            final_rc = result.get("exit_class")
            if not isinstance(final_rc, int) or isinstance(final_rc, bool):
                final_rc = 0 if result["passed"] else 1
            if final_rc != 0:
                failures: List[str] = []
                for hook_name, stats in sorted(
                    result.get("hooks", {}).items()
                ):
                    if not stats.get("passed", True):
                        failures.append(
                            f"{hook_name} p95={stats['p95_ms']:.1f}ms "
                            f"p99={stats['p99_ms']:.1f}ms"
                        )
                for ctrl_name, ctrl in sorted(
                    result.get("controls", {}).items()
                ):
                    if isinstance(ctrl, dict) and not ctrl.get("passed", True):
                        failures.append(f"control:{ctrl_name}")
                p99_label = (
                    "p99 advisory"
                    if result.get("p99_advisory")
                    else f"p99<{result.get('p99_ceiling_ms')}ms"
                )
                verdict = result.get("verdict_label")
                print(
                    "FAIL: hook latency gate — "
                    + ("; ".join(failures) or result.get("error", "unknown"))
                    + f" (ceilings p95<{result.get('p95_ceiling_ms')}ms / "
                    f"{p99_label})"
                    + (f" [verdict={verdict} rc={final_rc}]" if verdict else ""),
                    file=sys.stderr,
                )
                return final_rc
            return 0
    except Exception as exc:  # noqa: BLE001 — top-level safety net
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


