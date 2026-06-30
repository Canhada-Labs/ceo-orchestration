"""PLAN-059 Phase 0 — rail anomaly empirical reproduction harness (analysis).

PLAN-059 Sessions 61+62 documented sub-agents emitting tool-call SYNTAX
as literal text (4 fabrication formats). H1/H2/H3 eliminated, H4
confirmed. This harness analyzes the empirical results of CEO-driven
sub-agent dispatches to discriminate root-cause hypotheses across:

- ``archetype``: code-reviewer / security-engineer / qa-architect /
  performance-engineer
- ``model``: claude-opus-4-7 vs claude-sonnet-4-6 (current vs forced)
- ``prompt_form``: trivial vs workflow-shaped
- ``parallelism``: serial vs N-parallel dispatch
- ``priming``: bare PERSONA vs PERSONA + workflow-imperative section

CEO dispatches sub-agents from a live Claude Code session (Python
cannot trigger the Task tool from outside). Each dispatch writes a
fixture file to ``/tmp/h4_repro_<dispatch_id>.txt`` (or fails to write,
which is the failure signal). CEO logs each dispatch to a JSONL
manifest. This harness reads the manifest, scores each dispatch, and
prints a per-cell empirical table.

## Manifest format (JSONL — one dispatch per line)

    {
      "dispatch_id": "qa-trivial-serial-001",
      "archetype": "qa-architect",
      "condition": {
        "model": "claude-sonnet-4-6",
        "prompt_form": "trivial",
        "parallelism": "serial",
        "priming": "bare"
      },
      "fixture_path": "/tmp/h4_repro_qa_trivial_serial_001.txt",
      "expected_marker": "MINIMAL_REPRO_QA_TRIVIAL_SERIAL_001_ALIVE",
      "dispatched_at": "2026-04-25T13:00:00Z",
      "tool_uses_reported": 0,
      "duration_ms": 4027
    }

Required keys per row: ``dispatch_id``, ``archetype``,
``fixture_path``, ``expected_marker``. Optional keys are aggregated
when present.

## Scoring

A dispatch is SUCCESS iff:
1. ``fixture_path`` file exists on disk
2. File contents contain ``expected_marker`` substring

A dispatch is FAILURE otherwise. Optional ``tool_uses_reported == 0``
is a corroborating signal but not the gating criterion (CEO observed
fabricated tool_uses values from notification text itself).

## Output

Markdown table: ``archetype`` × condition cells with success rate
(N=cell_size). JSON summary with per-cell aggregates + overall
hypothesis-discrimination signals (e.g. "model=opus-only N=10
success=10/10 → opus is robust" vs "model=sonnet-only N=10 success=2/10
→ sonnet exhibits H4").

Stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# Data model
# =============================================================================


@dataclass
class DispatchManifestRow:
    """A single CEO-driven dispatch entry, as recorded by the operator."""

    dispatch_id: str
    archetype: str
    fixture_path: Path
    expected_marker: str
    condition: Dict[str, Any] = field(default_factory=dict)
    dispatched_at: str = ""
    tool_uses_reported: Optional[int] = None
    duration_ms: Optional[int] = None
    notes: str = ""


@dataclass
class DispatchScoreResult:
    """Score for a single dispatch."""

    dispatch_id: str
    archetype: str
    condition: Dict[str, Any]
    success: bool
    failure_reason: str = ""  # "fixture_missing" | "marker_absent" | ""
    tool_uses_reported: Optional[int] = None
    duration_ms: Optional[int] = None


@dataclass
class CellAggregate:
    """Aggregate over a single (archetype × condition_key_value) cell."""

    archetype: str
    condition_label: str
    n_total: int
    n_success: int
    success_rate: float
    failure_reasons: Dict[str, int]
    median_duration_ms: Optional[float]


# =============================================================================
# Manifest loading
# =============================================================================


def parse_manifest_row(raw: Dict[str, Any]) -> DispatchManifestRow:
    """Parse one JSONL row into a DispatchManifestRow.

    Raises ValueError if required keys missing or types wrong.
    """
    required = ("dispatch_id", "archetype", "fixture_path", "expected_marker")
    for key in required:
        if key not in raw:
            raise ValueError(f"manifest row missing required key: {key!r}")
    return DispatchManifestRow(
        dispatch_id=str(raw["dispatch_id"]),
        archetype=str(raw["archetype"]),
        fixture_path=Path(str(raw["fixture_path"])),
        expected_marker=str(raw["expected_marker"]),
        condition=dict(raw.get("condition") or {}),
        dispatched_at=str(raw.get("dispatched_at") or ""),
        tool_uses_reported=(
            int(raw["tool_uses_reported"])
            if raw.get("tool_uses_reported") is not None
            else None
        ),
        duration_ms=(
            int(raw["duration_ms"])
            if raw.get("duration_ms") is not None
            else None
        ),
        notes=str(raw.get("notes") or ""),
    )


def load_manifest(path: Path) -> List[DispatchManifestRow]:
    """Read JSONL manifest into a list of DispatchManifestRow.

    Skips empty lines + comment lines (starting with ``#``).
    Raises ValueError on the first malformed row, with line number.
    """
    rows: List[DispatchManifestRow] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"manifest line {lineno}: JSON parse error: {e.msg}"
                ) from e
            if not isinstance(raw, dict):
                raise ValueError(
                    f"manifest line {lineno}: row must be JSON object"
                )
            try:
                rows.append(parse_manifest_row(raw))
            except ValueError as e:
                raise ValueError(f"manifest line {lineno}: {e}") from e
    return rows


# =============================================================================
# Scoring
# =============================================================================


def score_dispatch(row: DispatchManifestRow) -> DispatchScoreResult:
    """Score a single dispatch by checking fixture file + marker.

    Pure function — no logging side effects. Failure reason taxonomy:
      - ``"fixture_missing"``: ``fixture_path`` does not exist on disk.
      - ``"marker_absent"``: file exists but lacks ``expected_marker``.
      - ``""`` (empty): success.
    """
    fixture = row.fixture_path
    if not fixture.is_file():
        return DispatchScoreResult(
            dispatch_id=row.dispatch_id,
            archetype=row.archetype,
            condition=row.condition,
            success=False,
            failure_reason="fixture_missing",
            tool_uses_reported=row.tool_uses_reported,
            duration_ms=row.duration_ms,
        )
    try:
        text = fixture.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return DispatchScoreResult(
            dispatch_id=row.dispatch_id,
            archetype=row.archetype,
            condition=row.condition,
            success=False,
            failure_reason="fixture_unreadable",
            tool_uses_reported=row.tool_uses_reported,
            duration_ms=row.duration_ms,
        )
    if row.expected_marker not in text:
        return DispatchScoreResult(
            dispatch_id=row.dispatch_id,
            archetype=row.archetype,
            condition=row.condition,
            success=False,
            failure_reason="marker_absent",
            tool_uses_reported=row.tool_uses_reported,
            duration_ms=row.duration_ms,
        )
    return DispatchScoreResult(
        dispatch_id=row.dispatch_id,
        archetype=row.archetype,
        condition=row.condition,
        success=True,
        failure_reason="",
        tool_uses_reported=row.tool_uses_reported,
        duration_ms=row.duration_ms,
    )


def score_all(rows: List[DispatchManifestRow]) -> List[DispatchScoreResult]:
    """Score every row in the manifest."""
    return [score_dispatch(r) for r in rows]


# =============================================================================
# Aggregation
# =============================================================================


def _condition_label(condition: Dict[str, Any]) -> str:
    """Stable label like ``"model=sonnet,prompt=trivial,par=serial"``.

    Sorted by key for determinism. Empty condition → "default".
    """
    if not condition:
        return "default"
    parts = []
    for k in sorted(condition.keys()):
        v = condition[k]
        # Compact common values
        v_str = str(v)
        # Trim long model strings
        if k == "model":
            v_str = v_str.replace("claude-", "").replace("-", "")
        parts.append(f"{k}={v_str}")
    return ",".join(parts)


def _median(values: List[float]) -> Optional[float]:
    """Median of values, or None if empty."""
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def aggregate_by_cell(
    results: List[DispatchScoreResult],
) -> List[CellAggregate]:
    """Aggregate results by (archetype, condition_label) cells.

    Returns sorted list (archetype asc, condition_label asc).
    """
    groups: Dict[Tuple[str, str], List[DispatchScoreResult]] = defaultdict(list)
    for r in results:
        key = (r.archetype, _condition_label(r.condition))
        groups[key].append(r)

    aggregates: List[CellAggregate] = []
    for (archetype, cond_label), group in sorted(groups.items()):
        n_total = len(group)
        n_success = sum(1 for r in group if r.success)
        success_rate = (
            n_success / n_total if n_total > 0 else 0.0
        )
        failure_reasons: Dict[str, int] = defaultdict(int)
        for r in group:
            if not r.success and r.failure_reason:
                failure_reasons[r.failure_reason] += 1
        durations = [
            float(r.duration_ms) for r in group
            if r.duration_ms is not None
        ]
        med_dur = _median(durations)
        aggregates.append(CellAggregate(
            archetype=archetype,
            condition_label=cond_label,
            n_total=n_total,
            n_success=n_success,
            success_rate=success_rate,
            failure_reasons=dict(failure_reasons),
            median_duration_ms=med_dur,
        ))
    return aggregates


def aggregate_by_archetype(
    results: List[DispatchScoreResult],
) -> Dict[str, Tuple[int, int, float]]:
    """Per-archetype rollup: ``{archetype: (n_total, n_success, rate)}``."""
    groups: Dict[str, List[DispatchScoreResult]] = defaultdict(list)
    for r in results:
        groups[r.archetype].append(r)
    out: Dict[str, Tuple[int, int, float]] = {}
    for arch, group in groups.items():
        n_total = len(group)
        n_success = sum(1 for r in group if r.success)
        rate = n_success / n_total if n_total > 0 else 0.0
        out[arch] = (n_total, n_success, rate)
    return out


def aggregate_by_condition_dim(
    results: List[DispatchScoreResult],
    dim: str,
) -> Dict[str, Tuple[int, int, float]]:
    """Per-dim rollup: aggregate over a single condition dimension.

    E.g. ``dim="model"`` returns ``{"claude-opus-4-7": (n,s,rate),
    "claude-sonnet-4-6": (n,s,rate)}``. Rows whose condition lacks
    ``dim`` are bucketed under ``"<unset>"``.
    """
    groups: Dict[str, List[DispatchScoreResult]] = defaultdict(list)
    for r in results:
        v = r.condition.get(dim, "<unset>")
        groups[str(v)].append(r)
    out: Dict[str, Tuple[int, int, float]] = {}
    for val, group in groups.items():
        n_total = len(group)
        n_success = sum(1 for r in group if r.success)
        rate = n_success / n_total if n_total > 0 else 0.0
        out[val] = (n_total, n_success, rate)
    return out


# =============================================================================
# Reporting
# =============================================================================


def _fmt_pct(rate: float) -> str:
    return f"{int(round(rate * 100))}%"


def render_markdown_table(
    aggregates: List[CellAggregate],
) -> str:
    """Render aggregates as a markdown table.

    Columns: Archetype | Condition | N | Success | Rate | Median Duration |
             Failure Reasons.
    """
    if not aggregates:
        return "_(no data)_\n"
    lines = [
        "| Archetype | Condition | N | OK | Rate | Median ms | Failures |",
        "|---|---|---|---|---|---|---|",
    ]
    for a in aggregates:
        med = (
            f"{int(a.median_duration_ms)}"
            if a.median_duration_ms is not None
            else "—"
        )
        failures = (
            ", ".join(
                f"{k}×{v}" for k, v in sorted(a.failure_reasons.items())
            ) if a.failure_reasons else "—"
        )
        lines.append(
            f"| {a.archetype} | {a.condition_label} | "
            f"{a.n_total} | {a.n_success} | "
            f"{_fmt_pct(a.success_rate)} | {med} | {failures} |"
        )
    return "\n".join(lines) + "\n"


def render_summary_json(
    results: List[DispatchScoreResult],
    aggregates: List[CellAggregate],
) -> str:
    """JSON summary for machine-consumption / archival."""
    summary = {
        "total_dispatches": len(results),
        "total_success": sum(1 for r in results if r.success),
        "total_failure": sum(1 for r in results if not r.success),
        "overall_success_rate": (
            sum(1 for r in results if r.success) / len(results)
            if results else 0.0
        ),
        "by_archetype": {
            arch: {
                "n_total": n_total,
                "n_success": n_success,
                "success_rate": rate,
            }
            for arch, (n_total, n_success, rate)
            in aggregate_by_archetype(results).items()
        },
        "by_cell": [
            {
                "archetype": a.archetype,
                "condition_label": a.condition_label,
                "n_total": a.n_total,
                "n_success": a.n_success,
                "success_rate": a.success_rate,
                "failure_reasons": a.failure_reasons,
                "median_duration_ms": a.median_duration_ms,
            }
            for a in aggregates
        ],
    }
    return json.dumps(summary, ensure_ascii=False, indent=2)


def discriminate_hypotheses(
    results: List[DispatchScoreResult],
) -> List[str]:
    """Generate human-readable hypothesis-discrimination signals.

    Pure heuristics over the empirical aggregates. Returns a list of
    short statements like ``"model=opus N=10 ok=10/10 → robust"``.
    """
    signals: List[str] = []

    # By archetype
    by_arch = aggregate_by_archetype(results)
    for arch, (n_total, n_success, rate) in sorted(by_arch.items()):
        if n_total < 1:
            continue
        verdict = (
            "RELIABLE" if rate >= 0.95
            else "DEGRADED" if rate < 0.50
            else "INTERMITTENT"
        )
        signals.append(
            f"archetype={arch} N={n_total} ok={n_success}/{n_total} "
            f"({_fmt_pct(rate)}) → {verdict}"
        )

    # By model
    by_model = aggregate_by_condition_dim(results, "model")
    for model, (n_total, n_success, rate) in sorted(by_model.items()):
        if n_total < 1 or model == "<unset>":
            continue
        verdict = (
            "robust" if rate >= 0.95
            else "exhibits-H4" if rate < 0.50
            else "intermittent"
        )
        signals.append(
            f"model={model} N={n_total} ok={n_success}/{n_total} "
            f"({_fmt_pct(rate)}) → {verdict}"
        )

    # By parallelism
    by_par = aggregate_by_condition_dim(results, "parallelism")
    for par, (n_total, n_success, rate) in sorted(by_par.items()):
        if n_total < 1 or par == "<unset>":
            continue
        signals.append(
            f"parallelism={par} N={n_total} ok={n_success}/{n_total} "
            f"({_fmt_pct(rate)})"
        )

    # By prompt_form
    by_prompt = aggregate_by_condition_dim(results, "prompt_form")
    for pf, (n_total, n_success, rate) in sorted(by_prompt.items()):
        if n_total < 1 or pf == "<unset>":
            continue
        signals.append(
            f"prompt_form={pf} N={n_total} ok={n_success}/{n_total} "
            f"({_fmt_pct(rate)})"
        )

    return signals


# =============================================================================
# CLI
# =============================================================================


def _cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PLAN-059 rail anomaly empirical reproduction harness — "
            "analyze CEO-driven dispatch results"
        ),
    )
    parser.add_argument(
        "manifest",
        type=Path,
        help="Path to JSONL dispatch manifest",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "both"),
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--no-discriminate",
        action="store_true",
        help="Skip hypothesis-discrimination signals",
    )
    args = parser.parse_args(argv)

    if not args.manifest.is_file():
        sys.stderr.write(f"manifest not found: {args.manifest}\n")
        return 2

    try:
        rows = load_manifest(args.manifest)
    except ValueError as e:
        sys.stderr.write(f"manifest error: {e}\n")
        return 2

    if not rows:
        sys.stdout.write(
            "_(manifest is empty — no dispatches to score)_\n"
        )
        return 0

    results = score_all(rows)
    aggregates = aggregate_by_cell(results)

    if args.format in ("markdown", "both"):
        sys.stdout.write("# Rail Anomaly Empirical Results\n\n")
        sys.stdout.write(
            f"Total dispatches: **{len(results)}** "
            f"(ok: {sum(1 for r in results if r.success)} / "
            f"fail: {sum(1 for r in results if not r.success)})\n\n"
        )
        sys.stdout.write("## Per-cell breakdown\n\n")
        sys.stdout.write(render_markdown_table(aggregates))
        sys.stdout.write("\n")

        if not args.no_discriminate:
            sys.stdout.write("## Hypothesis-discrimination signals\n\n")
            for sig in discriminate_hypotheses(results):
                sys.stdout.write(f"- {sig}\n")
            sys.stdout.write("\n")

    if args.format in ("json", "both"):
        if args.format == "both":
            sys.stdout.write("## JSON summary\n\n")
            sys.stdout.write("```json\n")
        sys.stdout.write(render_summary_json(results, aggregates))
        sys.stdout.write("\n")
        if args.format == "both":
            sys.stdout.write("```\n")

    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(_cli_main())
