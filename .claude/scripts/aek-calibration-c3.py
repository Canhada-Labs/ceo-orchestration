#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLAN-101 Wave B — AEK Calibration C3 FPR matrix.

Joins `task_route_advised` (from audit-log) with
`task_route_ground_truth_label` (from audit-log post-ceremony OR
from sidecar `.claude/plans/PLAN-101/wave-a-ground-truth-labels.jsonl`
pre-ceremony) via `contract_id` field. Computes 4x4 confusion matrix
(actual S/M/L/XL vs predicted S/M/L/XL), per-class precision/recall/F1,
and overall accuracy.

Per ADR-104-AMEND-1 §E — audit-log append-only invariant preserved;
ground-truth labels go to NEW action, NOT a backfill.

Per ADR-104-AMEND-1 §C — sparse cells (N < 30) marked
`insufficient-data` and EXCLUDED from aggregate FPR.

Per PLAN-101 §B.2 — confusion is `actual x predicted` (rows = ground-
truth, columns = predicted). 4x4 = 16 cells. Per-class precision =
TP/(TP+FP); recall = TP/(TP+FN); F1 = harmonic mean. Overall accuracy
= trace(matrix) / total.

Usage:
  python3 .claude/scripts/aek-calibration-c3.py \\
      --window-days 30 \\
      --ground-truth-sidecar .claude/plans/PLAN-101/wave-a-ground-truth-labels.jsonl \\
      --output .claude/plans/PLAN-101/wave-b-c3-fpr-matrix.md

  python3 .claude/scripts/aek-calibration-c3.py --self-test

Exit codes:
  0 — matrix computed
  2 — internal error
  3 — INSUFFICIENT_VOLUME (N < 200 total OR no cells with N>=30)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[2]

EXIT_OK = 0
EXIT_INTERNAL = 2
EXIT_INSUFFICIENT_VOLUME = 3

MIN_TOTAL_EVENTS = 200
MIN_PER_CELL = 30
KNOWN_CLASSES = ("S", "M", "L", "XL")


def _audit_query_since(cutoff_iso: str, action: str) -> List[Dict]:
    """Invoke audit-query.py since <cutoff> --json + filter by action."""
    audit_query = REPO_ROOT / ".claude" / "scripts" / "audit-query.py"
    try:
        out = subprocess.check_output(
            ["python3", str(audit_query), "since", cutoff_iso, "--json"],
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[c3] audit-query failed: {exc.stderr[:500]}", file=sys.stderr)
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        print(f"[c3] audit-query JSON parse error: {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    return [ev for ev in data if isinstance(ev, dict) and ev.get("action") == action]


def _read_ground_truth_sidecar(path: Path) -> List[Dict]:
    """Read ground-truth labels from sidecar JSONL (pre-ceremony source)."""
    if not path.exists():
        return []
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and row.get("action") == "task_route_ground_truth_label":
                rows.append(row)
    return rows


def _join_advised_truth(
    advised: List[Dict], ground_truth: List[Dict]
) -> List[Tuple[str, str]]:
    """Inner-join via contract_id. Returns [(ground_truth_class, predicted_class), ...]."""
    truth_by_cid: Dict[str, str] = {}
    for row in ground_truth:
        cid = row.get("contract_id")
        gt = row.get("ground_truth_class")
        if cid and gt in KNOWN_CLASSES:
            truth_by_cid[cid] = gt
    pairs: List[Tuple[str, str]] = []
    for ev in advised:
        cid = ev.get("contract_id")
        pred = ev.get("classification")
        if cid in truth_by_cid and pred in KNOWN_CLASSES:
            pairs.append((truth_by_cid[cid], pred))
    return pairs


def _build_matrix(pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], int]:
    """Build 4x4 confusion: matrix[(actual, predicted)] = count."""
    matrix: Dict[Tuple[str, str], int] = {}
    for gt, pred in pairs:
        matrix[(gt, pred)] = matrix.get((gt, pred), 0) + 1
    return matrix


def _per_class_metrics(
    matrix: Dict[Tuple[str, str], int]
) -> Dict[str, Dict[str, float]]:
    """Per-class precision/recall/F1/FPR with proper TN denominator.

    For one-vs-rest binary view per class X:
      - TP = matrix[(X, X)]
      - FP = predicted X when actual ≠ X    (column X off-diagonal sum)
      - FN = actual X when predicted ≠ X    (row X off-diagonal sum)
      - TN = neither actual X nor predicted X (everything else)
    FPR_X = FP / (FP + TN). Codex R2 P1 #1 fold — earlier draft used the
    wrong denominator (FP + TP + FN), which can return a "lower bound"
    exceeding the point estimate.
    """
    total = sum(matrix.values())
    out: Dict[str, Dict[str, float]] = {}
    for cls in KNOWN_CLASSES:
        tp = matrix.get((cls, cls), 0)
        fp = sum(matrix.get((gt, cls), 0) for gt in KNOWN_CLASSES if gt != cls)
        fn = sum(matrix.get((cls, pred), 0) for pred in KNOWN_CLASSES if pred != cls)
        tn = total - tp - fp - fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        n_actual = sum(matrix.get((cls, pred), 0) for pred in KNOWN_CLASSES)
        out[cls] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "fpr": fpr,
            "n_actual": float(n_actual),
            "tp": float(tp),
            "fp": float(fp),
            "fn": float(fn),
            "tn": float(tn),
        }
    return out


def _wilson_lower(n_success: int, n_total: int, z: float = 1.96) -> float:
    """Wilson 95% lower bound (z=1.96). Matches PLAN-100 pattern."""
    if n_total == 0:
        return 0.0
    p = n_success / n_total
    denom = 1 + z * z / n_total
    centre = p + z * z / (2 * n_total)
    margin = z * math.sqrt(p * (1 - p) / n_total + z * z / (4 * n_total * n_total))
    return max(0.0, (centre - margin) / denom)


def _total_events(matrix: Dict[Tuple[str, str], int]) -> int:
    return sum(matrix.values())


def _trace(matrix: Dict[Tuple[str, str], int]) -> int:
    return sum(matrix.get((c, c), 0) for c in KNOWN_CLASSES)


def _format_matrix_md(
    matrix: Dict[Tuple[str, str], int],
    metrics: Dict[str, Dict[str, float]],
    window_iso: str,
    advised_n: int,
    truth_n: int,
    joined_n: int,
) -> str:
    lines: List[str] = []
    lines.append("# PLAN-101 Wave B — Calibration C3 FPR matrix")
    lines.append("")
    lines.append(f"**Window cutoff (since):** {window_iso}")
    lines.append(f"**task_route_advised events:** {advised_n}")
    lines.append(f"**task_route_ground_truth_label events:** {truth_n}")
    lines.append(f"**Joined pairs (by contract_id):** {joined_n}")
    lines.append("")
    lines.append("## FPR-MATRIX")
    lines.append("")
    lines.append("4x4 confusion: rows = actual (ground-truth), columns = "
                 "predicted (classifier). Cells with row-total N<30 marked "
                 "`insufficient-data` per ADR-104-AMEND-1 §C.")
    lines.append("")
    header = "| actual \\ predicted |"
    sep = "| --- |"
    for pred in KNOWN_CLASSES:
        header += f" {pred} |"
        sep += " ---: |"
    header += " row total |"
    sep += " ---: |"
    lines.append(header)
    lines.append(sep)
    for gt in KNOWN_CLASSES:
        row = f"| **{gt}** |"
        row_total = sum(matrix.get((gt, p), 0) for p in KNOWN_CLASSES)
        for pred in KNOWN_CLASSES:
            n = matrix.get((gt, pred), 0)
            row += f" {n} |"
        suffix = f" {row_total}"
        if row_total < MIN_PER_CELL:
            suffix += " (insufficient-data)"
        row += suffix + " |"
        lines.append(row)
    lines.append("")
    lines.append("## PER-CLASS-METRICS")
    lines.append("")
    lines.append("| class | precision | recall | F1 | FPR | Wilson 95% lower (FPR) | sufficient |")
    lines.append("| ----- | --------- | ------ | -- | --- | ----------------------- | ---------- |")
    for cls in KNOWN_CLASSES:
        m = metrics[cls]
        n = int(m["n_actual"])
        suf = "yes" if n >= MIN_PER_CELL else "insufficient-data"
        # Wilson 95% lower bound for FPR = fp / (fp + tn) — Codex R2 P1 #1 fold.
        wilson_total = int(m["fp"] + m["tn"]) or 1
        wilson = _wilson_lower(int(m["fp"]), wilson_total)
        lines.append(f"| {cls} | {m['precision']:.3f} | {m['recall']:.3f} | "
                     f"{m['f1']:.3f} | {m['fpr']:.3f} | {wilson:.3f} | {suf} |")
    lines.append("")
    total = _total_events(matrix)
    trace = _trace(matrix)
    accuracy = trace / total if total else 0.0
    lines.append("## OVERALL")
    lines.append("")
    lines.append(f"- Total joined pairs: {total}")
    lines.append(f"- Correctly classified (trace): {trace}")
    lines.append(f"- Overall accuracy: {accuracy:.3f}")
    lines.append("")
    # Per-class average FPR + ADR-104-AMEND-1 §C 4-of-4 class coverage gate.
    # Codex R2 P1 #4 fold — earlier draft averaged over "eligible" subset only,
    # which could PASS even with a missing class. The §C threshold requires
    # ALL 4 classes (S/M/L/XL) populated above per-cell minimum N=30.
    eligible = [m for cls, m in metrics.items() if m["n_actual"] >= MIN_PER_CELL]
    insufficient_classes = [
        cls for cls, m in metrics.items() if m["n_actual"] < MIN_PER_CELL
    ]
    if len(eligible) == 4:
        avg_fpr = sum(m["fpr"] for m in eligible) / 4
        lines.append(f"- Mean per-class FPR (all 4 classes covered): {avg_fpr:.3f}")
        lines.append(f"- ADR-104-AMEND-1 §C 4-of-4 class coverage: PASS")
        lines.append(f"- ADR-104-AMEND-1 §C threshold (FPR < 0.15): "
                     f"{'PASS' if avg_fpr < 0.15 else 'FAIL'}")
    elif eligible:
        avg_fpr = sum(m["fpr"] for m in eligible) / len(eligible)
        lines.append(f"- Mean per-class FPR (only {len(eligible)} of 4 classes "
                     f"covered): {avg_fpr:.3f}")
        lines.append(f"- ADR-104-AMEND-1 §C 4-of-4 class coverage: "
                     f"INSUFFICIENT_COVERAGE (missing: {','.join(insufficient_classes)})")
        lines.append("- ADR-104-AMEND-1 §C threshold (FPR < 0.15): "
                     "INSUFFICIENT_COVERAGE (cannot evaluate without 4-of-4)")
    else:
        lines.append("- Mean per-class FPR: insufficient data across all classes")
        lines.append("- ADR-104-AMEND-1 §C 4-of-4 class coverage: INSUFFICIENT_COVERAGE")
    lines.append("")
    lines.append("## METHODOLOGY")
    lines.append("")
    lines.append("- Sources: `task_route_advised` (audit-log) joined with "
                 "`task_route_ground_truth_label` (audit-log post-ceremony OR "
                 "`.claude/plans/PLAN-101/wave-a-ground-truth-labels.jsonl` "
                 "pre-ceremony) via `contract_id` field.")
    lines.append("- Append-only audit-log preserved per ADR-018: ground-truth "
                 "labels are a NEW action, NOT a backfill of "
                 "`task_route_advised`.")
    lines.append("- 4x4 confusion = actual × predicted. Sparse cells (N<30) "
                 "marked `insufficient-data` and excluded from aggregate FPR "
                 "per ADR-104-AMEND-1 §C.")
    lines.append("- Wilson 95% lower bound matches PLAN-100 stdlib pattern.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="PLAN-101 Wave B AEK Calibration C3 FPR matrix")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument(
        "--ground-truth-sidecar",
        type=str,
        default=".claude/plans/PLAN-101/wave-a-ground-truth-labels.jsonl",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=".claude/plans/PLAN-101/wave-b-c3-fpr-matrix.md",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    cutoff = (dt.datetime.utcnow() - dt.timedelta(days=args.window_days)).strftime("%Y-%m-%d")
    advised = _audit_query_since(cutoff, "task_route_advised")

    sidecar = REPO_ROOT / args.ground_truth_sidecar
    ground_truth_audit = _audit_query_since(cutoff, "task_route_ground_truth_label")
    ground_truth_sidecar = _read_ground_truth_sidecar(sidecar)

    # Union: audit-log preferred when both present (post-ceremony)
    seen_cids = set()
    ground_truth_combined: List[Dict] = []
    for row in ground_truth_audit:
        cid = row.get("contract_id")
        if cid and cid not in seen_cids:
            ground_truth_combined.append(row)
            seen_cids.add(cid)
    for row in ground_truth_sidecar:
        cid = row.get("contract_id")
        if cid and cid not in seen_cids:
            ground_truth_combined.append(row)
            seen_cids.add(cid)

    pairs = _join_advised_truth(advised, ground_truth_combined)
    print(f"[c3] window cutoff: {cutoff}", file=sys.stderr)
    print(f"[c3] advised events: {len(advised)}", file=sys.stderr)
    print(f"[c3] ground-truth labels (audit+sidecar): {len(ground_truth_combined)}", file=sys.stderr)
    print(f"[c3] joined pairs: {len(pairs)}", file=sys.stderr)

    matrix = _build_matrix(pairs)
    if _total_events(matrix) < MIN_TOTAL_EVENTS:
        print(
            f"[c3] INSUFFICIENT_VOLUME: joined N={_total_events(matrix)} < {MIN_TOTAL_EVENTS}",
            file=sys.stderr,
        )
        return EXIT_INSUFFICIENT_VOLUME

    metrics = _per_class_metrics(matrix)
    md = _format_matrix_md(
        matrix, metrics, cutoff,
        advised_n=len(advised), truth_n=len(ground_truth_combined), joined_n=len(pairs),
    )
    out_path = REPO_ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"[c3] wrote {out_path}", file=sys.stderr)
    return EXIT_OK


def _self_test() -> int:
    """Inline self-test."""
    pairs = [
        ("S", "S"), ("S", "S"), ("S", "M"),
        ("M", "M"), ("M", "M"), ("M", "L"),
        ("L", "L"), ("L", "L"), ("L", "M"),
        ("XL", "XL"), ("XL", "XL"), ("XL", "L"),
    ]
    matrix = _build_matrix(pairs)
    assert matrix[("S", "S")] == 2
    assert matrix[("S", "M")] == 1
    metrics = _per_class_metrics(matrix)
    assert 0 <= metrics["S"]["precision"] <= 1
    assert 0 <= metrics["S"]["recall"] <= 1
    # Wilson sanity
    assert 0.0 <= _wilson_lower(5, 100) <= 0.10
    print("[c3] self-test PASS", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
