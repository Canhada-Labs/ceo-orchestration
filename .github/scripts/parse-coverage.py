#!/usr/bin/env python3
"""PLAN-093 Wave A.2 — branch + line coverage gate.

Reads `coverage.json` (post `coverage json`) and asserts both:
  - totals.percent_covered_branches >= --branch-min (default 86)
  - totals.percent_covered          >= --line-min   (default 85)

Optionally compares branch% against a numeric baseline snapshot in a
markdown file and fails if the drop exceeds --max-drop percentage points.

Kill-switch: env `CEO_BRANCH_COVERAGE_ENFORCING=0` flips this script
to advisory mode (warns to stderr; exit 0 regardless of threshold).

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 — Tier-1
per-module mode:
  parse-coverage.py --tier1-modules 'a.py,b.py' --tier1-min 86
reads `coverage.json` `files[].summary.percent_covered` and fails if ANY
listed Tier-1 module is below --tier1-min. Modules are matched by path
suffix against production files (test-tree paths excluded). A listed
module that matches no production file is itself a failure (guards against
silently passing a typo'd module name). When --tier1-modules is set, ONLY
the Tier-1 check runs (the branch/line/baseline gate is a separate,
advisory invocation). Kill-switch: env `CEO_TIER1_COVERAGE_ENFORCING=0`
flips the Tier-1 check to advisory (warns; exit 0).
Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def _load_data(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_totals(path: Path) -> dict:
    return _load_data(path).get("totals") or {}


def _is_production(file_key: str) -> bool:
    """A coverage.json file key that is live code, not a test or staging copy."""
    return "/tests/" not in file_key and "/plans/" not in file_key


def tier1_failures(data: dict, modules: list, min_pct: float) -> list:
    """Return human-readable failures for Tier-1 per-module coverage.

    `modules` is a list of path suffixes (e.g. 'check_read_injection.py').
    A module is matched against production file keys by suffix; a module
    matching no production file is itself a failure.
    """
    files = data.get("files") or {}
    failures = []
    for mod in modules:
        mod = mod.strip()
        if not mod:
            continue
        matched = [
            (k, v) for k, v in files.items()
            if _is_production(k) and (k == mod or k.endswith("/" + mod) or k.endswith(mod))
        ]
        if not matched:
            failures.append(f"Tier-1 module '{mod}' not found in coverage.json (production files)")
            continue
        # Most-specific match wins if several (shortest path suffix delta).
        key, val = min(matched, key=lambda kv: len(kv[0]))
        pct = float(val.get("summary", {}).get("percent_covered", 0.0))
        status = "OK" if pct >= min_pct else "BELOW"
        print(f"  TIER1 {status}: {key} = {pct:.2f}% (min {min_pct})")
        if pct < min_pct:
            failures.append(f"Tier-1 module {key} {pct:.2f}% < min {min_pct}")
    return failures


def _branch_pct(totals: dict) -> float:
    if "percent_covered_branches" in totals:
        return float(totals["percent_covered_branches"])
    nb = int(totals.get("num_branches", 0))
    cb = int(totals.get("covered_branches", 0))
    return (cb / nb * 100.0) if nb else 0.0


def _line_pct(totals: dict) -> float:
    return float(totals.get("percent_covered", 0.0))


_BASELINE_BRANCH_RE = re.compile(r"^\s*-\s*BRANCH\s*[:=]\s*([0-9.]+)\s*%", re.IGNORECASE | re.MULTILINE)


def _baseline_branch(md: Path) -> float:
    text = md.read_text(encoding="utf-8")
    m = _BASELINE_BRANCH_RE.search(text)
    if not m:
        raise ValueError(f"baseline branch% not found in {md}")
    return float(m.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-json", default="coverage.json")
    parser.add_argument("--branch-min", type=float, default=86.0)
    parser.add_argument("--line-min", type=float, default=85.0)
    parser.add_argument("--baseline-md", default=None)
    parser.add_argument("--max-drop", type=float, default=2.0)
    parser.add_argument(
        "--tier1-modules", default="",
        help="comma-separated path suffixes for the Tier-1 per-module gate "
             "(ADR-139). When set, ONLY the Tier-1 check runs.",
    )
    parser.add_argument("--tier1-min", type=float, default=86.0)
    args = parser.parse_args()

    cov_path = Path(args.coverage_json)
    if not cov_path.exists():
        sys.stderr.write(f"parse-coverage: {cov_path} not found\n")
        return 1

    # ADR-139 Tier-1 per-module mode — independent of the branch/line gate.
    if args.tier1_modules.strip():
        modules = [m for m in args.tier1_modules.split(",") if m.strip()]
        t1_enforcing = os.environ.get("CEO_TIER1_COVERAGE_ENFORCING", "1") != "0"
        data = _load_data(cov_path)
        print(f"Tier-1 per-module gate (min {args.tier1_min}%) — {len(modules)} module(s)")
        failures = tier1_failures(data, modules, args.tier1_min)
        if failures:
            msg = "parse-coverage TIER1 FAILED: " + "; ".join(failures)
            if t1_enforcing:
                sys.stderr.write(msg + "\n")
                return 1
            sys.stderr.write(
                f"parse-coverage TIER1 ADVISORY (CEO_TIER1_COVERAGE_ENFORCING=0): {msg}\n"
            )
            return 0
        print("parse-coverage TIER1 OK")
        return 0

    enforcing = os.environ.get("CEO_BRANCH_COVERAGE_ENFORCING", "1") != "0"

    totals = _load_totals(cov_path)
    branch = _branch_pct(totals)
    line = _line_pct(totals)

    print(f"BRANCH = {branch:.2f}% (min {args.branch_min})")
    print(f"LINE   = {line:.2f}% (min {args.line_min})")

    failures = []
    if line < args.line_min:
        failures.append(f"line {line:.2f}% < min {args.line_min}")
    if branch < args.branch_min:
        failures.append(f"branch {branch:.2f}% < min {args.branch_min}")

    if args.baseline_md:
        md = Path(args.baseline_md)
        if md.exists():
            try:
                base = _baseline_branch(md)
                drop = base - branch
                print(f"BASELINE branch = {base:.2f}% (current drop = {drop:.2f}pp; max {args.max_drop})")
                if drop > args.max_drop:
                    failures.append(
                        f"branch dropped {drop:.2f}pp vs baseline {base:.2f}% (max {args.max_drop})"
                    )
            except ValueError as exc:
                sys.stderr.write(f"parse-coverage: {exc}\n")
        else:
            sys.stderr.write(f"parse-coverage: baseline-md {md} not found (skipping drop check)\n")

    if failures:
        msg = "parse-coverage FAILED: " + "; ".join(failures)
        if enforcing:
            sys.stderr.write(msg + "\n")
            return 1
        sys.stderr.write(
            f"parse-coverage ADVISORY (CEO_BRANCH_COVERAGE_ENFORCING=0): {msg}\n"
        )
        return 0

    print("parse-coverage OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
