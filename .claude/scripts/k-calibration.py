#!/usr/bin/env python3
"""k-calibration.py — Cohen's κ + bootstrap CI + Landis-Koch band report.

PLAN-012 Phase 4 D2 companion tool. Sibling to `calibration-kappa.py`
(Sprint 11 ordinal/weighted). This tool focuses on the flip-gate
question: is the **bootstrap 95% CI lower bound** for Cohen's κ ≥
threshold (default 0.7)?

Stdlib only (no numpy / scipy). Unweighted κ on nominal labels with
percentile bootstrap CI (Efron 1979) because the parametric SE
`√((1−κ)/N)` assumes asymptotic normality that breaks at moderate N.

Refs: Cohen (1960) EPM 20(1) 37-46; Landis & Koch (1977) Biometrics
33(1) 159-174; Efron (1979) Ann. Stat. 7(1) 1-26; Efron & Tibshirani
(1993) §13.3 for 10k-resample tail stability.

CLI:
    python3 .claude/scripts/k-calibration.py \\
        --rater1 grades/rater1.csv --rater2 grades/rater2.csv \\
        --bootstrap-iterations 10000 --ci-level 0.95 --threshold 0.7

CSV: columns `item_id,label` required. Additional columns
(timestamp, duration_s, rater_id) ignored.

Exit codes: 0 flip-gate pass (CI_lower ≥ threshold); 1 fail;
2 input error. Intra-rater mode (--first-pass/--second-pass) exits
0 iff κ_intra point estimate ≥ --intra-threshold (default 0.8).
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_grades(csv_path: Path) -> List[Tuple[str, str]]:
    """Return (item_id, label) pairs from a CSV file.

    Required columns: item_id, label. Extra columns ignored (timestamp,
    duration_s, etc.). Empty rows skipped. Whitespace trimmed.

    Raises:
        FileNotFoundError if path missing.
        ValueError if required columns absent or file empty.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"grades file not found: {csv_path}")
    rows: List[Tuple[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"empty CSV: {csv_path}")
        missing = {"item_id", "label"} - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"{csv_path} missing required columns: {sorted(missing)}"
            )
        for row in reader:
            iid = (row.get("item_id") or "").strip()
            lbl = (row.get("label") or "").strip()
            if not iid or not lbl:
                continue
            rows.append((iid, lbl))
    if not rows:
        raise ValueError(f"no labelled rows in {csv_path}")
    return rows


def pair_graders(
    r1: List[Tuple[str, str]],
    r2: List[Tuple[str, str]],
) -> Tuple[List[str], List[str]]:
    """Align two rater lists on item_id. Errors if any id mismatch.

    Returns (labels_r1, labels_r2) indexed in the same order. The order
    is determined by rater1's file order (deterministic given fixed
    input). Mismatched id set → ValueError with the symmetric diff.
    """
    ids1 = [i for i, _ in r1]
    ids2_set = {i for i, _ in r2}
    ids1_set = set(ids1)
    if len(ids1) != len(ids1_set):
        raise ValueError("rater1 CSV has duplicate item_ids")
    if ids1_set != ids2_set:
        missing = sorted(ids1_set - ids2_set) + sorted(ids2_set - ids1_set)
        raise ValueError(f"rater id sets differ: {missing[:5]}...")
    by_id2 = dict(r2)
    labels1 = [lbl for _, lbl in r1]
    labels2 = [by_id2[iid] for iid in ids1]
    return labels1, labels2


# ---------------------------------------------------------------------------
# Cohen's κ (unweighted, nominal)
# ---------------------------------------------------------------------------


def compute_kappa(rater1: List[str], rater2: List[str]) -> float:
    """Unweighted Cohen's κ for two nominal rating vectors.

    κ = (p_o − p_e) / (1 − p_e), where p_o is observed agreement rate
    and p_e is the chance-agreement rate from marginals.

    Edge cases:
        N = 0         → raises ValueError
        p_e == 1.0    → returns 1.0 if p_o == 1.0, else 0.0 (Cohen 1960 §4)
        length mismatch → ValueError
    """
    if len(rater1) != len(rater2):
        raise ValueError(
            f"rater lists differ in length: {len(rater1)} vs {len(rater2)}"
        )
    n = len(rater1)
    if n == 0:
        raise ValueError("cannot compute κ on empty rater lists")

    categories = sorted(set(rater1) | set(rater2))
    idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    confusion = [[0] * k for _ in range(k)]
    for a, b in zip(rater1, rater2):
        confusion[idx[a]][idx[b]] += 1

    p_o = sum(confusion[i][i] for i in range(k)) / n
    marg_r1 = [sum(confusion[i]) / n for i in range(k)]
    marg_r2 = [sum(confusion[i][j] for i in range(k)) / n for j in range(k)]
    p_e = sum(marg_r1[i] * marg_r2[i] for i in range(k))

    if math.isclose(p_e, 1.0):
        # Degenerate marginals: both raters used one category everywhere.
        return 1.0 if math.isclose(p_o, 1.0) else 0.0
    return (p_o - p_e) / (1.0 - p_e)


def asymptotic_se_kappa(kappa: float, n: int) -> float:
    """Fleiss-Cohen-Everitt large-sample SE approximation.

    SE(κ) ≈ √((1−κ)·(1−2κ+κ²·something)/N). The simpler upper-bound
    form `√((1−κ) / N)` is used here as a sanity check only; the
    authoritative CI comes from the bootstrap.
    """
    if n <= 0:
        return float("inf")
    return math.sqrt(max(0.0, (1.0 - kappa) / n))


# ---------------------------------------------------------------------------
# Bootstrap 95% CI
# ---------------------------------------------------------------------------


def bootstrap_kappa_ci(
    rater1: List[str],
    rater2: List[str],
    n_iters: int = 10_000,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> Tuple[float, float]:
    """Percentile bootstrap CI for Cohen's κ.

    Resamples N item-pairs with replacement n_iters times, computes κ
    per resample, returns the (α/2, 1−α/2) percentile bounds.

    Args:
        rater1, rater2: paired label lists.
        n_iters: bootstrap resamples (10k is the conventional floor for
            stable tail quantiles per Efron & Tibshirani 1993 §13.3).
        ci: confidence level (0.95 default).
        seed: RNG seed for determinism (None = system entropy).

    Returns:
        (lower, upper) percentile bounds.
    """
    if not 0.0 < ci < 1.0:
        raise ValueError(f"ci must be in (0, 1); got {ci}")
    if n_iters < 100:
        raise ValueError(f"n_iters must be ≥100; got {n_iters}")
    if len(rater1) != len(rater2):
        raise ValueError("rater lists differ in length")
    n = len(rater1)
    if n == 0:
        raise ValueError("cannot bootstrap on empty rater lists")

    rng = random.Random(seed)
    alpha = 1.0 - ci
    samples: List[float] = []
    for _ in range(n_iters):
        # Resample indices with replacement (paired bootstrap —
        # preserves rater-pair correlation structure).
        idxs = [rng.randint(0, n - 1) for _ in range(n)]
        r1_boot = [rater1[i] for i in idxs]
        r2_boot = [rater2[i] for i in idxs]
        try:
            k = compute_kappa(r1_boot, r2_boot)
        except ValueError:
            continue
        samples.append(k)

    if not samples:
        raise RuntimeError("all bootstrap resamples degenerate")
    samples.sort()
    lo_idx = int(math.floor((alpha / 2) * len(samples)))
    hi_idx = int(math.ceil((1.0 - alpha / 2) * len(samples))) - 1
    lo_idx = max(0, min(lo_idx, len(samples) - 1))
    hi_idx = max(0, min(hi_idx, len(samples) - 1))
    return (samples[lo_idx], samples[hi_idx])


# ---------------------------------------------------------------------------
# Landis-Koch bands
# ---------------------------------------------------------------------------


def landis_koch_band(kappa: float) -> str:
    """Landis-Koch (1977) interpretive band for κ.

    Bands (boundary rule: strict `>` for upper, so exact 0.20 → "poor",
    0.21 → "fair"):
        κ < 0.00       → "no_agreement"
        0.00 ≤ κ ≤ 0.20 → "poor"
        0.20 < κ ≤ 0.40 → "fair"
        0.40 < κ ≤ 0.60 → "moderate"
        0.60 < κ ≤ 0.80 → "substantial"
        0.80 < κ ≤ 1.00 → "almost_perfect"
    """
    if kappa < 0.0:
        return "no_agreement"
    if kappa <= 0.20:
        return "poor"
    if kappa <= 0.40:
        return "fair"
    if kappa <= 0.60:
        return "moderate"
    if kappa <= 0.80:
        return "substantial"
    return "almost_perfect"


# ---------------------------------------------------------------------------
# Intra-rater drift
# ---------------------------------------------------------------------------


def intra_rater_kappa(
    first_pass: List[str],
    second_pass: List[str],
    n_iters: int = 5_000,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> dict:
    """κ between two passes by the SAME rater (test-retest) with CI.

    PLAN-012 D2 gate: κ_intra ≥ 0.8 on 10+ items regraded after ≥14d
    blind (the blinding is enforced by protocol, not by code).
    """
    point = compute_kappa(first_pass, second_pass)
    lo, hi = bootstrap_kappa_ci(
        first_pass, second_pass, n_iters=n_iters, ci=ci, seed=seed
    )
    return {
        "kappa": point,
        "ci_lower": lo,
        "ci_upper": hi,
        "n": len(first_pass),
        "band": landis_koch_band(point),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_report(result: dict) -> str:
    lines: List[str] = []
    lines.append(f"Cohen's κ: {result['kappa']:.3f}")
    lines.append(
        f"{int(result['ci_level']*100)}% CI (bootstrap, "
        f"{result['n_iters']} iters): "
        f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]"
    )
    lines.append(f"Landis-Koch band: {result['band'].upper()}")
    lines.append(f"SE (asymptotic): {result['se_asymptotic']:.3f}")
    lines.append(f"N: {result['n']}")
    lines.append(f"N agreements: {result['agreements']}")
    lines.append(f"N disagreements: {result['disagreements']}")
    if result["n"] < 10:
        lines.append("WARNING: N<10, κ estimate is unstable (wide CI)")
    gate_pass = result["ci_lower"] >= result["threshold"]
    status = "PASS" if gate_pass else "FAIL"
    relation = "≥" if gate_pass else "<"
    lines.append(
        f"Flip-gate: {status} (CI_lower={result['ci_lower']:.3f} "
        f"{relation} threshold {result['threshold']:.3f})"
    )
    return "\n".join(lines)


def _run_inter_rater(args: argparse.Namespace) -> int:
    try:
        r1 = load_grades(Path(args.rater1))
        r2 = load_grades(Path(args.rater2))
        labels1, labels2 = pair_graders(r1, r2)
    except FileNotFoundError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2
    except ValueError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2

    kappa = compute_kappa(labels1, labels2)
    lo, hi = bootstrap_kappa_ci(
        labels1,
        labels2,
        n_iters=args.bootstrap_iterations,
        ci=args.ci_level,
        seed=args.seed,
    )
    agreements = sum(1 for a, b in zip(labels1, labels2) if a == b)
    result = {
        "kappa": kappa,
        "ci_lower": lo,
        "ci_upper": hi,
        "ci_level": args.ci_level,
        "n_iters": args.bootstrap_iterations,
        "band": landis_koch_band(kappa),
        "se_asymptotic": asymptotic_se_kappa(kappa, len(labels1)),
        "n": len(labels1),
        "agreements": agreements,
        "disagreements": len(labels1) - agreements,
        "threshold": args.threshold,
    }
    print(_format_report(result))
    return 0 if result["ci_lower"] >= args.threshold else 1


def _run_intra_rater(args: argparse.Namespace) -> int:
    try:
        r1 = load_grades(Path(args.first_pass))
        r2 = load_grades(Path(args.second_pass))
        labels1, labels2 = pair_graders(r1, r2)
    except FileNotFoundError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2
    except ValueError as e:
        sys.stderr.write(f"ERROR: {e}\n")
        return 2

    result = intra_rater_kappa(
        labels1,
        labels2,
        n_iters=args.bootstrap_iterations,
        ci=args.ci_level,
        seed=args.seed,
    )
    print(f"Intra-rater κ (test-retest): {result['kappa']:.3f}")
    print(
        f"{int(args.ci_level*100)}% CI: "
        f"[{result['ci_lower']:.3f}, {result['ci_upper']:.3f}]"
    )
    print(f"Landis-Koch band: {result['band'].upper()}")
    print(f"N paired retests: {result['n']}")
    gate_pass = result["kappa"] >= args.intra_threshold
    status = "PASS" if gate_pass else "FAIL"
    relation = "≥" if gate_pass else "<"
    print(
        f"Drift-gate: {status} (κ_intra={result['kappa']:.3f} "
        f"{relation} threshold {args.intra_threshold:.3f})"
    )
    return 0 if gate_pass else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="k-calibration.py",
        description=(
            "Cohen's κ + bootstrap 95% CI + Landis-Koch band report. "
            "Stdlib-only. Flip-gate exits 0 iff CI_lower ≥ threshold."
        ),
    )
    parser.add_argument("--rater1", help="CSV of first rater (inter-rater mode)")
    parser.add_argument("--rater2", help="CSV of second rater (inter-rater mode)")
    parser.add_argument(
        "--first-pass",
        help="CSV of initial grading pass (intra-rater mode)",
    )
    parser.add_argument(
        "--second-pass",
        help="CSV of retest pass by SAME rater (intra-rater mode)",
    )
    parser.add_argument(
        "--bootstrap-iterations",
        type=int,
        default=10_000,
        help="Bootstrap resamples (default 10000; Efron & Tibshirani floor)",
    )
    parser.add_argument(
        "--ci-level",
        type=float,
        default=0.95,
        help="Confidence level for percentile bootstrap (default 0.95)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Inter-rater flip-gate threshold on CI_lower (default 0.7)",
    )
    parser.add_argument(
        "--intra-threshold",
        type=float,
        default=0.8,
        help="Intra-rater point-estimate threshold (default 0.8)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for bootstrap (default system entropy)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — run k-fold calibration across reviewer samples."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    inter = bool(args.rater1 and args.rater2)
    intra = bool(args.first_pass and args.second_pass)
    if inter == intra:
        parser.error(
            "specify EITHER --rater1/--rater2 (inter-rater) "
            "OR --first-pass/--second-pass (intra-rater)"
        )
    if args.bootstrap_iterations < 100:
        parser.error("--bootstrap-iterations must be ≥100")
    if not 0.0 < args.ci_level < 1.0:
        parser.error("--ci-level must be in (0, 1)")

    if inter:
        return _run_inter_rater(args)
    return _run_intra_rater(args)


if __name__ == "__main__":
    sys.exit(main())
