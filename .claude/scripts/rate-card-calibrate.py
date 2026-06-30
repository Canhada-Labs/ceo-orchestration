#!/usr/bin/env python3
"""rate-card-calibrate.py — periodic rate-card drift calibrator (PLAN-135 O8).

S227 found exactly TWO stale price pins (opus-4-7 still at $15/$75 after the
ratified drop to $5/$25) in the rate-card pair — and the only thing that caught
them was a live W0b reconciliation run. This calibrator turns that into a cheap
recurring check: it diffs BOTH on-disk rate-card files

  - ``.claude/scripts/cost-table.yaml``   (input/output ``_per_mtok``)
  - ``docs/provider-pricing.md``          (``Input $/1k`` / ``Output $/1k``)

against a human-ratified fixtures file (``rate-card-fixtures.json``, the same
ground truth S227 propagated in ``e3b179bf``). Any model whose on-disk price
disagrees with the fixture beyond tolerance is a stale pin — surfaced HERE
(static, $0, no network) instead of in a future paid run.

Unit bridge: the fixture + cost-table are per-Mtok; provider-pricing is per-1k.
The calibrator converts ($/Mtok == $/1k * 1000) before comparing, so a
unit-confusion drift (a real failure class) is caught too.

``--live`` is PENDING-OWNER: the authoritative drift source for *actually
billed* rates is the Anthropic Usage/Cost API (admin-scoped, read-only). This
script NEVER calls it — ``--live`` prints the Owner-run recipe and exits. No
paid spend, no network, ever, from this script.

Exit codes:
  0 — report mode (always), or --check with zero drift, or infra fail-open
      (missing/corrupt fixtures: advisory + exit 0)
  1 — --check only: at least one stale pin (price drift) or a fixture model
      ABSENT from a rate-card file (a coverage gap is a calibration miss)
  2 — CLI usage error (argparse)

Stdlib-only. Python >= 3.9. Read-only (never writes). Emits NO audit events.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))
DEFAULT_FIXTURES = os.path.join(SCRIPT_DIR, "rate-card-fixtures.json")
DEFAULT_COST_TABLE = os.path.join(SCRIPT_DIR, "cost-table.yaml")
DEFAULT_PRICING = os.path.join(REPO_ROOT, "docs", "provider-pricing.md")

_DEFAULT_TOL_PER_MTOK = 0.005
_MODEL_KEY_RE = re.compile(r"^  ([A-Za-z0-9.\-]+):\s*$")
_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


# --------------------------------------------------------------------------- #
# Parsers (fail-soft — a missing/garbled file yields {} not a traceback).
# --------------------------------------------------------------------------- #
def load_fixtures(path: str) -> Optional[Dict[str, Any]]:
    """Read the ratified fixtures JSON. None on any failure (fail-open)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("rates"), dict):
            return None
        return data
    except (OSError, ValueError):
        return None


def parse_cost_table(path: str) -> Dict[str, Dict[str, float]]:
    """Model -> {input_per_mtok, output_per_mtok} from cost-table.yaml.

    Mini-YAML subset: a ``models:`` top-level key, then 2-space model rows,
    each with 4-space ``input_per_mtok``/``output_per_mtok`` scalars.
    """
    out: Dict[str, Dict[str, float]] = {}
    try:
        in_models = False
        current: Optional[str] = None
        for raw in _read_lines(path):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" "):
                in_models = line.split(":", 1)[0].strip() == "models"
                current = None
                continue
            if not in_models:
                continue
            m = _MODEL_KEY_RE.match(line)
            if m:
                current = m.group(1)
                out.setdefault(current, {})
                continue
            if current is not None and line.startswith("    "):
                key, _, val = line.strip().partition(":")
                val = val.strip().split("#", 1)[0].strip().strip('"')
                if key in ("input_per_mtok", "output_per_mtok") and _NUM_RE.match(val):
                    out[current][key] = float(val)
    except OSError:
        return {}
    return out


def parse_provider_pricing(path: str) -> Dict[str, Dict[str, float]]:
    """Model -> {input_per_mtok, output_per_mtok} from provider-pricing.md.

    The markdown table is per-1k; values are converted to per-Mtok (* 1000)
    so they compare directly against the fixtures + cost-table.
    """
    out: Dict[str, Dict[str, float]] = {}
    try:
        for raw in _read_lines(path):
            line = raw.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            if set(cells[0]) <= {"-", " ", ":"}:  # separator row
                continue
            if cells[0].lower() == "provider":  # header row
                continue
            model = cells[1].lower()
            if not _NUM_RE.match(cells[2]) or not _NUM_RE.match(cells[3]):
                continue
            out[model] = {
                "input_per_mtok": float(cells[2]) * 1000.0,
                "output_per_mtok": float(cells[3]) * 1000.0,
            }
    except OSError:
        return {}
    return out


def _read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.readlines()


# --------------------------------------------------------------------------- #
# Calibration
# --------------------------------------------------------------------------- #
def _cmp(fixture: float, actual: Optional[float], tol: float) -> Tuple[str, Optional[float]]:
    """('match'|'drift'|'absent', delta) for one price field."""
    if actual is None:
        return "absent", None
    delta = round(actual - fixture, 6)
    return ("match" if abs(delta) <= tol else "drift"), delta


def calibrate(
    fixtures: Optional[Dict[str, Any]],
    cost_table: Dict[str, Dict[str, float]],
    pricing: Dict[str, Dict[str, float]],
    *,
    tol: Optional[float] = None,
) -> Dict[str, Any]:
    """Compare both rate-card files to the ratified fixtures. NEVER raises."""
    if fixtures is None:
        return {
            "schema": 1, "fail_open": True, "status": "clean",
            "summary": "rate-card fixtures missing/corrupt — advisory, treated "
            "as no-drift (the fixtures ship at .claude/scripts/rate-card-fixtures.json)",
            "models": [], "drift_count": 0, "absent_count": 0,
        }
    if tol is None:
        meta = fixtures.get("_meta") if isinstance(fixtures.get("_meta"), dict) else {}
        tol = float(meta.get("tolerance_per_mtok", _DEFAULT_TOL_PER_MTOK))

    rows: List[Dict[str, Any]] = []
    drift_count = 0
    absent_count = 0
    for model, want in sorted(fixtures.get("rates", {}).items()):
        if not isinstance(want, dict):
            continue
        model_row: Dict[str, Any] = {"model": model, "fields": []}
        has_drift = False
        has_absent = False
        for field in ("input_per_mtok", "output_per_mtok"):
            fixture_val = float(want.get(field, 0.0))
            for source_name, table in (("cost_table", cost_table),
                                       ("provider_pricing", pricing)):
                actual = table.get(model, {}).get(field)
                state, delta = _cmp(fixture_val, actual, tol)
                if state == "drift":
                    drift_count += 1
                    has_drift = True
                elif state == "absent":
                    absent_count += 1
                    has_absent = True
                model_row["fields"].append({
                    "field": field, "source": source_name,
                    "fixture": fixture_val, "actual": actual,
                    "state": state, "delta_per_mtok": delta,
                })
        # Drift dominates absent dominates match (drift = a wrong price now on
        # disk; absent = a fixture model with no row to compare against).
        model_row["status"] = "drift" if has_drift else ("absent" if has_absent else "match")
        rows.append(model_row)

    if drift_count:
        status = "drift"
        drifted = sorted({r["model"] for r in rows if r["status"] == "drift"})
        summary = "STALE PIN(s) — on-disk rate disagrees with the ratified fixtures: %s" % drifted
    elif absent_count:
        status = "absent"
        gap = sorted({r["model"] for r in rows if r["status"] == "absent"})
        summary = "fixture model(s) MISSING from a rate-card file (coverage gap): %s" % gap
    else:
        status = "clean"
        summary = "all %d ratified rates match cost-table.yaml + provider-pricing.md" % len(rows)

    return {
        "schema": 1, "fail_open": False, "status": status, "summary": summary,
        "tolerance_per_mtok": tol, "models": rows,
        "drift_count": drift_count, "absent_count": absent_count,
    }


_LIVE_RECIPE = """\
PENDING-OWNER live rate-card calibration (Anthropic Usage/Cost API):
  The authoritative source for ACTUALLY BILLED rates is the admin-scoped
  Anthropic Cost API (read-only). This script never calls it. Owner-run:
    1. Provision an admin key in the OS keychain/env (NEVER commit it;
       custody per research/THREAT-MODEL-WORKSHEET.md §3 admin-keys).
    2. Pull the cost breakdown by model for a recent window.
    3. Derive the effective $/Mtok per model from cost / tokens.
    4. Diff against rate-card-fixtures.json; update the fixtures (and then
       cost-table.yaml + provider-pricing.md via their own ceremony) on drift.
  The Cost API read bills nothing (no model tokens). It is Owner-run because
  it needs the admin key and reads org-wide usage — agents + CI stay out.
  Record the quota bucket per PLAN-135 W5 accounting axes (no model spend)."""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rate-card drift calibrator vs ratified fixtures (PLAN-135 O8)."
    )
    parser.add_argument("--fixtures", default=DEFAULT_FIXTURES,
                        help="ratified rate fixtures JSON (default: alongside this script)")
    parser.add_argument("--cost-table", default=DEFAULT_COST_TABLE,
                        help="cost-table.yaml path")
    parser.add_argument("--pricing", default=DEFAULT_PRICING,
                        help="docs/provider-pricing.md path")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit the JSON report")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 on any stale pin / coverage gap")
    parser.add_argument("--live", action="store_true",
                        help="PRINT the PENDING-OWNER Usage/Cost API recipe (no network)")
    parser.add_argument("--tol", type=float, default=None,
                        help="override the per-Mtok comparison tolerance")
    args = parser.parse_args(argv)

    if args.live:
        print(_LIVE_RECIPE)
        return 0

    fixtures = load_fixtures(args.fixtures)
    cost_table = parse_cost_table(args.cost_table)
    pricing = parse_provider_pricing(args.pricing)
    report = calibrate(fixtures, cost_table, pricing, tol=args.tol)

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("rate-card-calibrate: %s — %s" % (report["status"], report["summary"]))
        for row in report["models"]:
            if row["status"] != "match":
                for f in row["fields"]:
                    if f["state"] != "match":
                        print("  [%s] %-22s %-16s %-9s fixture=%s actual=%s"
                              % (f["state"].upper(), row["model"], f["field"],
                                 f["source"], f["fixture"], f["actual"]))

    if args.check and report["status"] in ("drift", "absent"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
