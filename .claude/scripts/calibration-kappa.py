#!/usr/bin/env python3
"""Cohen's kappa calculator for human-vs-judge calibration (PLAN-011 Phase 3).

Stdlib-only. Computes unweighted + linear-weighted κ on paired integer
ratings, plus a confusion matrix and refusal precision/recall.

## Input format

Newline-delimited JSON (`.claude/benchmarks/calibration-grades.jsonl`):

    {"id": "g-001", "date": "2026-04-14", "benchmark": "owasp-basics",
     "skill": "security-and-auth", "human": 8, "judge_fwd": 7,
     "judge_rev": 8, "refused_human": false, "refused_judge": false,
     "note": "initial seed"}

Each line is one pair. Append-only; corrections are new rows with the
same `id` — this tool uses the LAST occurrence per id.

## CLI

    python3 calibration-kappa.py [--grades <path>] [--json] [--min-n 20]

Exit codes:
    0 — report printed (regardless of κ value)
    2 — fewer than --min-n pairs (preliminary or unreportable)
    3 — input malformed

## Output

Plain text report with headline κ (weighted), unweighted κ, confusion
matrix, refusal precision/recall, and the comparison against the
0.7 Sprint-12 flip threshold (ADR-030 §9).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_GRADES = Path(__file__).resolve().parent.parent / "benchmarks" / "calibration-grades.jsonl"
MAX_SCORE = 10  # 0-10 Likert


def _load_grades(path: Path) -> List[Dict[str, Any]]:
    """Load paired grades; dedupe by id (last occurrence wins)."""
    if not path.is_file():
        return []
    by_id: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    with path.open("r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as e:
                sys.stderr.write(f"WARNING: line {line_num} skipped ({e})\n")
                continue
            rid = row.get("id")
            if not rid:
                sys.stderr.write(f"WARNING: line {line_num} missing id\n")
                continue
            by_id[rid] = row
    return list(by_id.values())


def _split_scorable(rows: List[Dict[str, Any]]) -> Tuple[List[int], List[int], List[Dict[str, Any]]]:
    """Filter to rows where both human and judge_fwd are ints in [0, MAX_SCORE].

    Returns (human_scores, judge_scores, refusal_rows). Refusal rows are
    those where either side set refused_{human|judge}=true; they are
    reported separately via precision/recall.
    """
    humans: List[int] = []
    judges: List[int] = []
    refusals: List[Dict[str, Any]] = []
    for row in rows:
        rh = row.get("refused_human", False)
        rj = row.get("refused_judge", False)
        if rh or rj:
            refusals.append(row)
            continue
        h = row.get("human")
        j = row.get("judge_fwd")
        if not isinstance(h, int) or not isinstance(j, int):
            continue
        if h < 0 or h > MAX_SCORE or j < 0 or j > MAX_SCORE:
            continue
        humans.append(h)
        judges.append(j)
    return humans, judges, refusals


def _confusion_matrix(humans: List[int], judges: List[int]) -> List[List[int]]:
    k = MAX_SCORE + 1
    m = [[0] * k for _ in range(k)]
    for h, j in zip(humans, judges):
        m[h][j] += 1
    return m


def _unweighted_kappa(humans: List[int], judges: List[int]) -> Optional[float]:
    """Cohen's unweighted κ."""
    n = len(humans)
    if n == 0:
        return None
    observed_agreement = sum(1 for h, j in zip(humans, judges) if h == j) / n
    # Expected agreement under independence.
    k = MAX_SCORE + 1
    h_dist = [0.0] * k
    j_dist = [0.0] * k
    for h in humans:
        h_dist[h] += 1
    for jj in judges:
        j_dist[jj] += 1
    h_dist = [x / n for x in h_dist]
    j_dist = [x / n for x in j_dist]
    expected_agreement = sum(h_dist[i] * j_dist[i] for i in range(k))
    if expected_agreement >= 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def _linear_weighted_kappa(humans: List[int], judges: List[int]) -> Optional[float]:
    """Weighted κ with linear weights w_ij = 1 - |i-j|/(k-1).

    κ_w = 1 - sum(w_ij * O_ij) / sum(w_ij * E_ij)
    where w_ij here is the DISAGREEMENT weight (|i-j|/(k-1)).
    """
    n = len(humans)
    if n == 0:
        return None
    k = MAX_SCORE + 1
    denom = k - 1  # max distance
    observed = _confusion_matrix(humans, judges)
    # Marginals
    row_margin = [sum(observed[i]) for i in range(k)]
    col_margin = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    # Expected under independence
    expected = [
        [row_margin[i] * col_margin[j] / n for j in range(k)] for i in range(k)
    ]
    # Linear disagreement weights
    num = 0.0
    den = 0.0
    for i in range(k):
        for j in range(k):
            w = abs(i - j) / denom
            num += w * observed[i][j]
            den += w * expected[i][j]
    if den <= 0:
        return 1.0 if num <= 0 else None
    return 1 - (num / den)


def _refusal_metrics(refusals: List[Dict[str, Any]], all_rows: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    """Precision + recall of judge refusal vs human refusal."""
    h_refused = {r["id"] for r in all_rows if r.get("refused_human")}
    j_refused = {r["id"] for r in all_rows if r.get("refused_judge")}
    if not h_refused and not j_refused:
        return {"precision": None, "recall": None, "n_human_refused": 0, "n_judge_refused": 0}
    tp = len(h_refused & j_refused)
    precision = tp / len(j_refused) if j_refused else None
    recall = tp / len(h_refused) if h_refused else None
    return {
        "precision": precision,
        "recall": recall,
        "n_human_refused": len(h_refused),
        "n_judge_refused": len(j_refused),
    }


def compute_report(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute the full calibration report."""
    humans, judges, refusals = _split_scorable(rows)
    report: Dict[str, Any] = {
        "n_pairs": len(humans),
        "n_refusals": len(refusals),
        "kappa_unweighted": _unweighted_kappa(humans, judges),
        "kappa_linear_weighted": _linear_weighted_kappa(humans, judges),
        "confusion_matrix": _confusion_matrix(humans, judges),
        "refusal_metrics": _refusal_metrics(refusals, rows),
    }
    # Snapshot methodology
    report["threshold_flip"] = 0.7
    report["min_n_flip"] = 50
    report["min_n_preliminary"] = 20
    return report


def format_report(report: Dict[str, Any]) -> str:
    """Format inter-rater kappa + calibration stats as human-readable text."""
    lines = ["# Calibration κ report", ""]
    n = report["n_pairs"]
    lines.append(f"Pairs (scorable): {n}")
    lines.append(f"Pairs (refused):  {report['n_refusals']}")
    if n == 0:
        lines.append("")
        lines.append("No scorable pairs yet. Populate `calibration-grades.jsonl` with human+judge pairs.")
        return "\n".join(lines)
    k_u = report["kappa_unweighted"]
    k_w = report["kappa_linear_weighted"]
    lines.append("")
    lines.append(f"κ (linear weighted, HEADLINE): {k_w:.4f}" if k_w is not None else "κ (weighted): N/A")
    lines.append(f"κ (unweighted):                {k_u:.4f}" if k_u is not None else "κ (unweighted): N/A")
    lines.append("")
    # Status vs threshold
    if n < report["min_n_preliminary"]:
        status = f"UNREPORTABLE (need ≥{report['min_n_preliminary']} for preliminary)"
    elif n < report["min_n_flip"]:
        status = f"PRELIMINARY (need ≥{report['min_n_flip']} for flip decision)"
    elif k_w is not None and k_w >= report["threshold_flip"]:
        status = f"FLIP-READY (κ ≥ {report['threshold_flip']}); Owner decides"
    else:
        status = f"FLIP-BLOCKED (κ < {report['threshold_flip']}); open a debate round per ADR-030 §9"
    lines.append(f"Status: {status}")
    lines.append("")
    rm = report["refusal_metrics"]
    if rm["n_human_refused"] or rm["n_judge_refused"]:
        lines.append("Refusal metrics:")
        p = rm["precision"]; r = rm["recall"]
        lines.append(f"  precision: {p:.4f}" if p is not None else "  precision: N/A")
        lines.append(f"  recall:    {r:.4f}" if r is not None else "  recall:    N/A")
        lines.append(f"  n_human_refused: {rm['n_human_refused']}")
        lines.append(f"  n_judge_refused: {rm['n_judge_refused']}")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — compute inter-rater kappa across reviewer samples."""
    ap = argparse.ArgumentParser(description="Compute Cohen's κ for human-vs-judge calibration")
    ap.add_argument("--grades", type=Path, default=DEFAULT_GRADES,
                    help="Path to calibration-grades.jsonl (default: .claude/benchmarks/calibration-grades.jsonl)")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of text")
    ap.add_argument("--min-n", type=int, default=20,
                    help="Minimum N for exit code 0; below this exits 2 (default 20)")
    ns = ap.parse_args(argv)

    try:
        rows = _load_grades(ns.grades)
    except OSError as e:
        sys.stderr.write(f"ERROR: cannot read grades file: {e}\n")
        return 3

    report = compute_report(rows)
    if ns.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))

    n = report["n_pairs"]
    if n < ns.min_n:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
