#!/usr/bin/env python3
"""Cross-adopter metrics comparison — Phase 0.3 of PLAN-015.

Consumes weekly-report JSON files from two or more adopter projects
(produced by `adopter-metrics.py --json`) and emits a markdown
side-by-side table with deltas computed against a chosen baseline.

## Input schema (per adopter)

Each input file is a JSON object of the shape:

    {
      "adopter_name": "adopter-1",
      "window": "7d",
      "window_start": "2026-04-20T00:00:00Z",
      "window_end":   "2026-04-27T00:00:00Z",
      "generated_at": "2026-04-27T18:05:00Z",
      "sessions": 15,
      "spawns_total": 87,
      "veto": {"vetoes": 3, "spawns_plus_vetoes": 90, "rate": 0.033},
      "completion": {"done": 12, "abandoned": 2, "denom": 14, "ratio": 0.857},
      "tokens": {"actual_total": 125000, "predicted_total": 110000, "ratio": 1.136},
      "custom_skills": {"count": 2, "names": ["skill-a", "skill-b"]},
      "adrs": {"total_mentions": 14, "distinct_count": 4,
               "names": ["ADR-023", "ADR-040", "ADR-045", "ADR-048"]}
    }

Any field may be null where the underlying denominator is zero.

## Usage

    python3 .claude/scripts/compare-adopters.py \\
      --input adopter-1=.claude/plans/PLAN-015/metrics/week-3.json \\
      --input adopter-2=.claude/plans/PLAN-016/metrics/week-3.json \\
      --output docs/case-studies/internal-validation-summary.md \\
      --baseline adopter-1

## Exit codes

- 0: success
- 1: bad arguments (< 2 inputs, bad syntax, missing file, bad baseline)
- 2: unreadable/bad-JSON input
- 3: --window-check active and window values differ between inputs

## Stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


EM_DASH = "\u2014"


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------


def _parse_input_spec(spec: str) -> Tuple[Optional[str], str]:
    """Parse a --input value.

    Returns (name_override_or_None, path). Name is taken from the
    ``NAME=PATH`` form; bare paths return ``(None, path)``.

    Raises ValueError on bad syntax (empty name, empty path, multiple ``=``).
    """
    if spec is None or spec == "":
        raise ValueError("empty --input value")
    if "=" not in spec:
        return None, spec
    # Split on first '=' only; paths may legitimately contain '=' but name must not.
    name, _, path = spec.partition("=")
    name = name.strip()
    path = path.strip()
    if not name:
        raise ValueError("--input: name cannot be empty in NAME=PATH")
    if not path:
        raise ValueError("--input: path cannot be empty in NAME=PATH")
    if "=" in name:
        # Defensive; partition already caught this.
        raise ValueError("--input: name cannot contain '='")
    return name, path


def _load_report(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("cannot read {0}: {1}".format(path, exc))
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("bad JSON in {0}: {1}".format(path, exc))
    if not isinstance(data, dict):
        raise RuntimeError("{0}: top-level JSON must be an object".format(path))
    return _unwrap_envelope(data)


def _unwrap_envelope(data: Dict[str, Any]) -> Dict[str, Any]:
    """Tolerate adopter-metrics.py envelope form.

    adopter-metrics.py --json emits ``{"adopter_name", "window", "metrics": {...}}``
    while this script's flat input spec puts metric keys at the top level.
    If an envelope is detected (``metrics`` key whose value is a dict), merge
    the nested metrics up to the top level without clobbering envelope
    identity fields (``adopter_name``, ``window``).
    """
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        return data
    merged: Dict[str, Any] = {}
    merged.update(metrics)
    for k, v in data.items():
        if k == "metrics":
            continue
        merged[k] = v
    return merged


# ---------------------------------------------------------------------------
# Field extraction (tolerant of missing keys)
# ---------------------------------------------------------------------------


def _get_nested(d: Dict[str, Any], *keys: str) -> Any:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _coerce_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        out: List[str] = []
        for item in v:
            if item is None:
                continue
            out.append(str(item))
        return out
    return []


def _extract_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
    """Return a flat dict of metric values (may be None)."""
    return {
        "sessions": report.get("sessions"),
        "spawns_total": report.get("spawns_total"),
        "veto_rate": _get_nested(report, "veto", "rate"),
        "completion_ratio": _get_nested(report, "completion", "ratio"),
        "tokens_ratio": _get_nested(report, "tokens", "ratio"),
        "custom_skills_count": _get_nested(report, "custom_skills", "count"),
        "adrs_distinct_count": _get_nested(report, "adrs", "distinct_count"),
        "adrs_total_mentions": _get_nested(report, "adrs", "total_mentions"),
    }


# ---------------------------------------------------------------------------
# Rendering primitives
# ---------------------------------------------------------------------------


def _fmt_count(v: Any) -> str:
    """Render a count metric value (int) or N/A for None."""
    if v is None:
        return "N/A"
    try:
        return str(int(v))
    except (TypeError, ValueError):
        return "N/A"


def _fmt_pct(v: Any) -> str:
    """Render a rate (0..1 float) as percentage; N/A for None."""
    if v is None:
        return "N/A"
    try:
        return "{0:.1f}%".format(float(v) * 100.0)
    except (TypeError, ValueError):
        return "N/A"


def _fmt_ratio(v: Any) -> str:
    """Render a token ratio as 3-decimal float; N/A for None."""
    if v is None:
        return "N/A"
    try:
        return "{0:.3f}".format(float(v))
    except (TypeError, ValueError):
        return "N/A"


def _delta_count(base: Any, adopter: Any) -> str:
    if base is None or adopter is None:
        return EM_DASH
    try:
        d = int(adopter) - int(base)
    except (TypeError, ValueError):
        return EM_DASH
    return "{0:+d}".format(d)


def _delta_pp(base: Any, adopter: Any) -> str:
    if base is None or adopter is None:
        return EM_DASH
    try:
        d = (float(adopter) - float(base)) * 100.0
    except (TypeError, ValueError):
        return EM_DASH
    return "{0:+.1f} pp".format(d)


def _delta_ratio(base: Any, adopter: Any) -> str:
    if base is None or adopter is None:
        return EM_DASH
    try:
        d = float(adopter) - float(base)
    except (TypeError, ValueError):
        return EM_DASH
    return "{0:+.3f}".format(d)


# ---------------------------------------------------------------------------
# Table assembly
# ---------------------------------------------------------------------------


# Rows: (label, metric_key, value_formatter, delta_formatter)
_ROWS = [
    ("Sessions", "sessions", _fmt_count, _delta_count),
    ("Spawns", "spawns_total", _fmt_count, _delta_count),
    ("Veto rate", "veto_rate", _fmt_pct, _delta_pp),
    ("Completion ratio", "completion_ratio", _fmt_pct, _delta_pp),
    ("Tokens actual vs predicted", "tokens_ratio", _fmt_ratio, _delta_ratio),
    ("Custom skills count", "custom_skills_count", _fmt_count, _delta_count),
    ("ADRs distinct", "adrs_distinct_count", _fmt_count, _delta_count),
    ("ADRs total mentions", "adrs_total_mentions", _fmt_count, _delta_count),
]


def _build_comparison(
    adopters: List[Tuple[str, Dict[str, Any]]],
    baseline_name: str,
) -> Dict[str, Any]:
    """Build the internal comparison structure used by both markdown
    and JSON renderers.

    ``adopters`` is an ordered list of (name, report) pairs; the order
    is preserved in the output. ``baseline_name`` identifies which entry
    to treat as baseline.
    """
    baseline_metrics: Optional[Dict[str, Any]] = None
    for name, report in adopters:
        if name == baseline_name:
            baseline_metrics = _extract_metrics(report)
            break
    if baseline_metrics is None:
        raise RuntimeError(
            "baseline '{0}' not found among adopters".format(baseline_name)
        )

    result_adopters: List[Dict[str, Any]] = []
    for name, report in adopters:
        metrics = _extract_metrics(report)
        is_baseline = name == baseline_name
        deltas: Dict[str, str] = {}
        if not is_baseline:
            for _, key, _val_fmt, delta_fmt in _ROWS:
                deltas[key] = delta_fmt(baseline_metrics.get(key), metrics.get(key))
        result_adopters.append({
            "name": name,
            "is_baseline": is_baseline,
            "window": report.get("window"),
            "metrics": metrics,
            "deltas": deltas,
            "custom_skills": sorted(_coerce_list(_get_nested(report, "custom_skills", "names"))),
            "custom_skills_count": _get_nested(report, "custom_skills", "count"),
            "adrs": sorted(_coerce_list(_get_nested(report, "adrs", "names"))),
            "adrs_count": _get_nested(report, "adrs", "distinct_count"),
        })

    windows = [a["window"] for a in result_adopters]
    uniform_window = all(w == windows[0] for w in windows) and windows[0] is not None

    return {
        "baseline": baseline_name,
        "adopters": result_adopters,
        "windows": windows,
        "uniform_window": uniform_window,
    }


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_markdown(comparison: Dict[str, Any], now: Optional[str] = None) -> str:
    baseline_name: str = comparison["baseline"]
    adopters: List[Dict[str, Any]] = comparison["adopters"]
    windows: List[Optional[str]] = comparison["windows"]
    uniform: bool = comparison["uniform_window"]
    generated_at = now if now is not None else _now_iso()

    # Ordered names: baseline first (per spec), then others in input order.
    ordered: List[Dict[str, Any]] = [a for a in adopters if a["is_baseline"]]
    ordered.extend(a for a in adopters if not a["is_baseline"])
    non_baseline = [a for a in ordered if not a["is_baseline"]]

    # Header lines
    names_csv = ", ".join(a["name"] for a in ordered)
    if uniform:
        window_str = str(windows[0])
    else:
        window_str = "mixed (see notes)"

    out: List[str] = []
    out.append("# Cross-adopter metrics comparison")
    out.append("")
    out.append("**Generated:** {0}".format(generated_at))
    out.append("**Baseline:** {0}".format(baseline_name))
    out.append("**Adopters:** {0}".format(names_csv))
    out.append("**Window:** {0}".format(window_str))
    out.append("")
    out.append("## Summary table")
    out.append("")

    # Build header row: Metric | baseline (baseline) | adopter_2 | delta | adopter_3 | delta | ...
    header_cells: List[str] = ["Metric", "{0} (baseline)".format(baseline_name)]
    for a in non_baseline:
        header_cells.append(a["name"])
        header_cells.append("Delta vs baseline")
    out.append("| " + " | ".join(header_cells) + " |")
    out.append("|" + "|".join(["--------"] * len(header_cells)) + "|")

    baseline_entry = next(a for a in adopters if a["is_baseline"])
    for label, key, val_fmt, _delta_fmt in _ROWS:
        row: List[str] = [label, val_fmt(baseline_entry["metrics"].get(key))]
        for a in non_baseline:
            row.append(val_fmt(a["metrics"].get(key)))
            row.append(a["deltas"].get(key, EM_DASH))
        out.append("| " + " | ".join(row) + " |")

    out.append("")
    out.append("## Custom skills by adopter")
    out.append("")
    baseline_skills = set(baseline_entry["custom_skills"])
    for a in ordered:
        count_str = _fmt_count(a.get("custom_skills_count"))
        if a["custom_skills"]:
            names = ", ".join(a["custom_skills"])
        else:
            names = "none"
        out.append("- **{0}** ({1}): {2}".format(a["name"], count_str, names))
        if not a["is_baseline"]:
            unique = sorted(set(a["custom_skills"]) - baseline_skills)
            if unique:
                out.append("  - Unique to {0}: {1}".format(a["name"], ", ".join(unique)))

    out.append("")
    out.append("## ADRs cited by adopter")
    out.append("")
    baseline_adrs = set(baseline_entry["adrs"])
    for a in ordered:
        count_str = _fmt_count(a.get("adrs_count"))
        if a["adrs"]:
            names = ", ".join(a["adrs"])
        else:
            names = "none"
        out.append("- **{0}** ({1}): {2}".format(a["name"], count_str, names))
        if not a["is_baseline"]:
            unique = sorted(set(a["adrs"]) - baseline_adrs)
            if unique:
                out.append("  - Unique to {0}: {1}".format(a["name"], ", ".join(unique)))

    out.append("")
    out.append("## Notes")
    out.append("")
    out.append("- Delta values for rates use **percentage points** (pp), not percent-of-percent")
    out.append("- `N/A` entries mean the metric was null in that adopter's source (denominator zero)")
    out.append("- Delta against a baseline with `N/A` is reported as `{0}` (em-dash, no comparison possible)".format(EM_DASH))
    if not uniform:
        out.append("- **Window mismatch detected:** adopters have different windows. Comparisons may not be meaningful.")

    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# JSON renderer
# ---------------------------------------------------------------------------


def _render_json(comparison: Dict[str, Any], now: Optional[str] = None) -> str:
    generated_at = now if now is not None else _now_iso()
    payload = {
        "generated_at": generated_at,
        "baseline": comparison["baseline"],
        "uniform_window": comparison["uniform_window"],
        "adopters": [
            {
                "name": a["name"],
                "is_baseline": a["is_baseline"],
                "window": a["window"],
                "metrics": a["metrics"],
                "deltas": a["deltas"],
                "custom_skills": a["custom_skills"],
                "adrs": a["adrs"],
            }
            for a in comparison["adopters"]
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI orchestration
# ---------------------------------------------------------------------------


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="compare-adopters.py",
        description="Diff weekly adopter-metrics JSON reports and emit a "
                    "side-by-side markdown comparison. At least two --input "
                    "entries are required.",
    )
    p.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="Adopter label and JSON report path. Repeat for each adopter "
             "(>=2 required). Bare PATH is allowed; NAME is then pulled "
             "from the JSON adopter_name field.",
    )
    p.add_argument("--output", metavar="PATH",
                   help="Write markdown (or JSON with --json) to PATH. "
                        "Parent dirs are created. Default: stdout.")
    p.add_argument("--baseline", metavar="NAME",
                   help="Adopter label to treat as baseline; deltas are "
                        "computed against it. Default: first --input.")
    p.add_argument("--json", action="store_true",
                   help="Emit JSON instead of markdown.")
    p.add_argument("--window-check", action="store_true",
                   help="Fail with exit 3 if adopter windows differ.")
    return p


def _run(argv: List[str], now: Optional[str] = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)

    raw_inputs: List[str] = list(args.input or [])
    if len(raw_inputs) < 2:
        sys.stderr.write("error: --input must be given at least twice (>=2 adopters required)\n")
        return 1

    adopters: List[Tuple[str, Dict[str, Any]]] = []
    seen_names: List[str] = []
    for spec in raw_inputs:
        try:
            name_override, path_str = _parse_input_spec(spec)
        except ValueError as exc:
            sys.stderr.write("error: {0}\n".format(exc))
            return 1
        path = Path(path_str)
        if not path.is_file():
            sys.stderr.write("error: --input file not found: {0}\n".format(path))
            return 1
        try:
            report = _load_report(path)
        except RuntimeError as exc:
            sys.stderr.write("error: {0}\n".format(exc))
            return 2
        if name_override is not None:
            name = name_override
        else:
            derived = report.get("adopter_name")
            if not isinstance(derived, str) or not derived:
                sys.stderr.write(
                    "error: --input {0}: no adopter_name in JSON; use NAME=PATH form\n".format(path)
                )
                return 1
            name = derived
        if name in seen_names:
            sys.stderr.write("error: duplicate adopter name: {0}\n".format(name))
            return 1
        seen_names.append(name)
        adopters.append((name, report))

    baseline_name: str = args.baseline if args.baseline else adopters[0][0]
    if baseline_name not in seen_names:
        sys.stderr.write(
            "error: --baseline '{0}' is not among --input names {1}\n".format(
                baseline_name, seen_names
            )
        )
        return 1

    if args.window_check:
        windows = [r.get("window") for _, r in adopters]
        if not all(w == windows[0] for w in windows):
            sys.stderr.write(
                "error: --window-check: windows differ across adopters: {0}\n".format(windows)
            )
            return 3

    try:
        comparison = _build_comparison(adopters, baseline_name)
    except RuntimeError as exc:
        sys.stderr.write("error: {0}\n".format(exc))
        return 1

    if args.json:
        rendered = _render_json(comparison, now=now) + "\n"
    else:
        rendered = _render_markdown(comparison, now=now)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    return 0


def main() -> int:
    return _run(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
