"""Unit tests for k-calibration.py — Cohen's κ + bootstrap CI."""

from __future__ import annotations

import importlib.util
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _SCRIPTS_DIR / "k-calibration.py"

spec = importlib.util.spec_from_file_location(
    "k_calibration", str(_SCRIPT_PATH)
)
assert spec is not None and spec.loader is not None
kc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kc)


def _write_csv(path: Path, rows: list[tuple[str, str]]) -> None:
    lines = ["item_id,label"]
    for iid, lbl in rows:
        lines.append(f"{iid},{lbl}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestKappaMath(unittest.TestCase):
    """Point-estimate invariants on compute_kappa."""

    def test_kappa_perfect_agreement(self):
        labels = ["pos", "neg", "pos", "pos", "neg", "neg"]
        self.assertAlmostEqual(kc.compute_kappa(labels, labels), 1.0)

    def test_kappa_no_agreement_above_chance(self):
        # Random independent labels → κ ≈ 0 in expectation. We seed a
        # generator and assert |κ| is in a narrow-ish envelope; we do
        # NOT require exactly zero because a single 1000-sample draw
        # has finite variance.
        rng = random.Random(42)
        choices = ["a", "b", "c"]
        r1 = [rng.choice(choices) for _ in range(1000)]
        r2 = [rng.choice(choices) for _ in range(1000)]
        kappa = kc.compute_kappa(r1, r2)
        self.assertLess(abs(kappa), 0.10, f"|κ|={kappa:.3f} not near 0")

    def test_kappa_example_from_paper(self):
        # Cohen (1960) §3, Table 1 (psychiatrist example, 2×2):
        #   r2=+ r2=-
        # r1=+  25   10   (row total 35)
        # r1=-  15   50   (row total 65)
        # cols:  40   60   (N = 100)
        #
        # p_o = (25+50)/100 = 0.75
        # p_e = (0.35·0.40) + (0.65·0.60) = 0.14 + 0.39 = 0.53
        # κ  = (0.75 − 0.53) / (1 − 0.53) = 0.22 / 0.47 ≈ 0.468
        r1, r2 = [], []
        for _ in range(25):
            r1.append("+"); r2.append("+")
        for _ in range(10):
            r1.append("+"); r2.append("-")
        for _ in range(15):
            r1.append("-"); r2.append("+")
        for _ in range(50):
            r1.append("-"); r2.append("-")
        kappa = kc.compute_kappa(r1, r2)
        self.assertAlmostEqual(kappa, 0.468, places=2)

    def test_kappa_empty_raises(self):
        with self.assertRaises(ValueError):
            kc.compute_kappa([], [])

    def test_kappa_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            kc.compute_kappa(["a"], ["a", "b"])

    def test_kappa_degenerate_marginals(self):
        # Both raters use one category → p_e=1. If agreement is
        # perfect (same category) → κ=1. Per Cohen (1960) §4 we
        # return 1.0 / 0.0 not NaN for this degenerate case.
        self.assertEqual(kc.compute_kappa(["a"] * 20, ["a"] * 20), 1.0)


class TestLandisKoch(unittest.TestCase):
    """Landis-Koch (1977) band boundaries — strict > rule."""

    def test_landis_koch_bands_boundaries(self):
        self.assertEqual(kc.landis_koch_band(-0.1), "no_agreement")
        self.assertEqual(kc.landis_koch_band(0.0), "poor")
        self.assertEqual(kc.landis_koch_band(0.20), "poor")
        self.assertEqual(kc.landis_koch_band(0.21), "fair")
        self.assertEqual(kc.landis_koch_band(0.40), "fair")
        self.assertEqual(kc.landis_koch_band(0.41), "moderate")
        self.assertEqual(kc.landis_koch_band(0.60), "moderate")
        self.assertEqual(kc.landis_koch_band(0.61), "substantial")
        self.assertEqual(kc.landis_koch_band(0.80), "substantial")
        self.assertEqual(kc.landis_koch_band(0.81), "almost_perfect")
        self.assertEqual(kc.landis_koch_band(1.00), "almost_perfect")


class TestBootstrap(unittest.TestCase):
    """Bootstrap CI behaviour."""

    def test_bootstrap_ci_narrows_with_n(self):
        # Identical agreement structure at N=10 vs N=1000 → CI narrows.
        # Use a mixed (imperfect) pattern so κ < 1 and CI is actually
        # computable (perfect agreement gives degenerate bootstrap).
        def make(n: int) -> tuple[list[str], list[str]]:
            rng = random.Random(13)
            labels = []
            matches = []
            for _ in range(n):
                base = rng.choice(["a", "b", "c"])
                labels.append(base)
                # 80% agreement, 20% disagreement
                if rng.random() < 0.8:
                    matches.append(base)
                else:
                    matches.append(
                        rng.choice([c for c in ["a", "b", "c"] if c != base])
                    )
            return labels, matches

        r1_small, r2_small = make(20)
        r1_big, r2_big = make(1000)
        lo_s, hi_s = kc.bootstrap_kappa_ci(
            r1_small, r2_small, n_iters=500, seed=1
        )
        lo_b, hi_b = kc.bootstrap_kappa_ci(
            r1_big, r2_big, n_iters=500, seed=1
        )
        width_small = hi_s - lo_s
        width_big = hi_b - lo_b
        self.assertGreater(
            width_small,
            width_big,
            f"CI should narrow with N: small={width_small:.3f} vs "
            f"big={width_big:.3f}",
        )

    def test_ci_deterministic_with_seed(self):
        r1 = ["a", "b", "a", "b"] * 10
        r2 = ["a", "b", "a", "a"] * 10
        a1 = kc.bootstrap_kappa_ci(r1, r2, n_iters=500, seed=99)
        a2 = kc.bootstrap_kappa_ci(r1, r2, n_iters=500, seed=99)
        self.assertEqual(a1, a2)

    def test_ci_bounds_ordered(self):
        r1 = ["a", "b"] * 50
        r2 = ["a", "b"] * 50
        # Perfect agreement bootstraps to 1.0 across all resamples
        # except those where resampling makes the set degenerate. We
        # just check lower ≤ upper and both are in [0, 1].
        lo, hi = kc.bootstrap_kappa_ci(r1, r2, n_iters=500, seed=5)
        self.assertLessEqual(lo, hi)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_ci_invalid_ci_level(self):
        with self.assertRaises(ValueError):
            kc.bootstrap_kappa_ci(["a", "b"], ["a", "b"], ci=1.5)

    def test_ci_too_few_iters(self):
        with self.assertRaises(ValueError):
            kc.bootstrap_kappa_ci(["a"] * 10, ["a"] * 10, n_iters=5)


class TestIntraRater(unittest.TestCase):
    def test_intra_rater_detects_drift(self):
        # Perfect first pass; 40% noisy second pass → κ meaningfully < 1.
        first = ["pos"] * 40 + ["neg"] * 40
        rng = random.Random(2025)
        second = []
        for v in first:
            if rng.random() < 0.4:
                second.append("neg" if v == "pos" else "pos")
            else:
                second.append(v)
        result = kc.intra_rater_kappa(first, second, n_iters=500, seed=1)
        self.assertLess(result["kappa"], 0.8)
        self.assertIn("band", result)
        self.assertEqual(result["n"], 80)

    def test_intra_rater_perfect(self):
        first = ["a", "b", "c", "a", "b", "c"] * 5
        result = kc.intra_rater_kappa(first, first, n_iters=200, seed=1)
        self.assertAlmostEqual(result["kappa"], 1.0)


class TestLoadGrades(unittest.TestCase):
    def test_load_basic(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "g.csv"
            _write_csv(p, [("g-1", "pos"), ("g-2", "neg")])
            rows = kc.load_grades(p)
            self.assertEqual(rows, [("g-1", "pos"), ("g-2", "neg")])

    def test_load_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            kc.load_grades(Path("/nonexistent/xyz.csv"))

    def test_load_missing_columns(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.csv"
            p.write_text("id,grade\n1,good\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                kc.load_grades(p)

    def test_load_empty_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "empty.csv"
            p.write_text("", encoding="utf-8")
            with self.assertRaises(ValueError):
                kc.load_grades(p)

    def test_pair_graders_mismatched_ids(self):
        r1 = [("g-1", "a"), ("g-2", "b")]
        r2 = [("g-1", "a"), ("g-3", "b")]
        with self.assertRaises(ValueError):
            kc.pair_graders(r1, r2)

    def test_pair_graders_duplicate_ids(self):
        r1 = [("g-1", "a"), ("g-1", "b")]
        r2 = [("g-1", "a")]
        with self.assertRaises(ValueError):
            kc.pair_graders(r1, r2)


class TestCLI(unittest.TestCase):
    """End-to-end CLI — subprocess tests against the script."""

    @staticmethod
    def _run(args: list[str]) -> tuple[int, str, str]:
        proc = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH)] + args,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def test_cli_help(self):
        code, out, _ = self._run(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("k-calibration", out)

    def test_cli_exit_0_on_pass(self):
        # High agreement → CI_lower well above threshold 0.7.
        with tempfile.TemporaryDirectory() as td:
            r1 = Path(td) / "r1.csv"
            r2 = Path(td) / "r2.csv"
            # 100 items, 95 agreements on a balanced 2-class set
            rows_r1 = []
            rows_r2 = []
            for i in range(50):
                rows_r1.append((f"g-{i:03d}", "pos"))
                rows_r2.append((f"g-{i:03d}", "pos"))
            for i in range(50, 95):
                rows_r1.append((f"g-{i:03d}", "neg"))
                rows_r2.append((f"g-{i:03d}", "neg"))
            # 5 disagreements
            for i in range(95, 100):
                rows_r1.append((f"g-{i:03d}", "pos"))
                rows_r2.append((f"g-{i:03d}", "neg"))
            _write_csv(r1, rows_r1)
            _write_csv(r2, rows_r2)
            code, out, _ = self._run([
                "--rater1", str(r1),
                "--rater2", str(r2),
                "--bootstrap-iterations", "500",
                "--seed", "7",
                "--threshold", "0.7",
            ])
            self.assertIn("Landis-Koch band:", out)
            self.assertIn("Flip-gate:", out)
            self.assertEqual(code, 0, f"expected pass; stdout={out}")
            self.assertIn("PASS", out)

    def test_cli_exit_1_on_fail(self):
        # Low agreement → CI_lower below threshold 0.7.
        with tempfile.TemporaryDirectory() as td:
            r1 = Path(td) / "r1.csv"
            r2 = Path(td) / "r2.csv"
            # 100 items, ~60% agreement → κ well below 0.7
            rows_r1 = []
            rows_r2 = []
            rng = random.Random(0)
            for i in range(100):
                base = "pos" if rng.random() < 0.5 else "neg"
                rows_r1.append((f"g-{i:03d}", base))
                if rng.random() < 0.6:
                    rows_r2.append((f"g-{i:03d}", base))
                else:
                    rows_r2.append(
                        (f"g-{i:03d}", "neg" if base == "pos" else "pos")
                    )
            _write_csv(r1, rows_r1)
            _write_csv(r2, rows_r2)
            code, out, _ = self._run([
                "--rater1", str(r1),
                "--rater2", str(r2),
                "--bootstrap-iterations", "500",
                "--seed", "7",
                "--threshold", "0.7",
            ])
            self.assertEqual(code, 1, f"expected fail; stdout={out}")
            self.assertIn("FAIL", out)

    def test_cli_handles_missing_file(self):
        code, _, err = self._run([
            "--rater1", "/nonexistent/a.csv",
            "--rater2", "/nonexistent/b.csv",
        ])
        self.assertEqual(code, 2)
        self.assertIn("ERROR", err)

    def test_cli_handles_empty_csv(self):
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "empty.csv"
            empty.write_text("", encoding="utf-8")
            other = Path(td) / "other.csv"
            _write_csv(other, [("g-1", "a")])
            code, _, err = self._run([
                "--rater1", str(empty),
                "--rater2", str(other),
            ])
            self.assertEqual(code, 2)
            self.assertIn("ERROR", err)

    def test_cli_output_contains_landis_band(self):
        with tempfile.TemporaryDirectory() as td:
            r1 = Path(td) / "r1.csv"
            r2 = Path(td) / "r2.csv"
            _write_csv(r1, [(f"g-{i}", "a") for i in range(20)])
            _write_csv(r2, [(f"g-{i}", "a") for i in range(20)])
            code, out, _ = self._run([
                "--rater1", str(r1),
                "--rater2", str(r2),
                "--bootstrap-iterations", "200",
                "--seed", "1",
            ])
            self.assertIn("Landis-Koch band:", out)

    def test_cli_rejects_mixed_modes(self):
        code, _, err = self._run([
            "--rater1", "/tmp/a.csv",
            "--rater2", "/tmp/b.csv",
            "--first-pass", "/tmp/c.csv",
            "--second-pass", "/tmp/d.csv",
        ])
        self.assertNotEqual(code, 0)
        self.assertIn("inter-rater", err.lower() + err)

    def test_cli_intra_rater_mode(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "p1.csv"
            p2 = Path(td) / "p2.csv"
            _write_csv(p1, [(f"g-{i}", "pos") for i in range(15)])
            _write_csv(p2, [(f"g-{i}", "pos") for i in range(15)])
            code, out, _ = self._run([
                "--first-pass", str(p1),
                "--second-pass", str(p2),
                "--bootstrap-iterations", "200",
                "--seed", "1",
                "--intra-threshold", "0.8",
            ])
            self.assertEqual(code, 0, f"perfect retest should pass; {out}")
            self.assertIn("Intra-rater", out)
            self.assertIn("Drift-gate: PASS", out)

    def test_cli_unknown_flag_errors(self):
        code, _, err = self._run(["--rater1", "/tmp/a", "--not-a-flag"])
        self.assertNotEqual(code, 0)


class TestNWarning(unittest.TestCase):
    def test_n_less_than_10_warning(self):
        with tempfile.TemporaryDirectory() as td:
            r1 = Path(td) / "r1.csv"
            r2 = Path(td) / "r2.csv"
            _write_csv(r1, [(f"g-{i}", "a") for i in range(5)])
            _write_csv(r2, [(f"g-{i}", "a") for i in range(5)])
            code, out, _ = TestCLI._run([
                "--rater1", str(r1),
                "--rater2", str(r2),
                "--bootstrap-iterations", "200",
                "--seed", "1",
            ])
            self.assertIn("N<10", out)


class TestUnknownLabels(unittest.TestCase):
    def test_unknown_label_values_same_set_ok(self):
        # Both raters use the same custom label vocabulary: fine.
        r1 = ["green", "red", "blue"] * 10
        r2 = ["green", "red", "blue"] * 10
        k = kc.compute_kappa(r1, r2)
        self.assertAlmostEqual(k, 1.0)

    def test_mismatched_vocabularies_ok_as_disagreement(self):
        # Different labels on same item = treated as disagreement.
        # This is expected; κ formula handles k>2 naturally.
        r1 = ["yes"] * 10
        r2 = ["no"] * 10
        # With only one category per rater, p_e = 1, p_o = 0, we
        # return 0.0 per the Cohen (1960) degenerate-marginal rule.
        k = kc.compute_kappa(r1, r2)
        self.assertEqual(k, 0.0)


if __name__ == "__main__":
    unittest.main()
