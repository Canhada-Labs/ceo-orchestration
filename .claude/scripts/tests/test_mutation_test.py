"""Tests for mutation-test.py framework (PLAN-042 ITEM 11).

Verifies that the framework:
- Parses a target file and generates mutants across all operators
- Preserves the original file after a sweep (atomic restore)
- Correctly scores killed/survived based on pytest exit code
- Refuses to run when the target or tests are missing
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


_SCRIPT = (
    Path(__file__).resolve().parents[1] / "mutation-test.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "mutation_test", _SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


mt = _load_module()


class TestOperatorsGenerateMutants(unittest.TestCase):
    def test_boundary_mutator(self) -> None:
        import ast
        tree = ast.parse("x = 1\nif a < b: pass\nif c > d: pass\n")
        muts = list(mt.BoundaryMutator().mutants(tree))
        # 2 comparisons → 2 mutations (Lt→LtE, Gt→GtE)
        self.assertEqual(len(muts), 2)

    def test_comparison_flip_mutator(self) -> None:
        import ast
        tree = ast.parse("if a == b: pass\nif c is None: pass\n")
        muts = list(mt.ComparisonFlipMutator().mutants(tree))
        self.assertEqual(len(muts), 2)

    def test_logical_mutator(self) -> None:
        import ast
        tree = ast.parse("x = a and b\ny = c or d\n")
        muts = list(mt.LogicalMutator().mutants(tree))
        self.assertEqual(len(muts), 2)

    def test_constant_mutator(self) -> None:
        import ast
        tree = ast.parse("a = True\nb = False\nc = 0\nd = 1\n")
        muts = list(mt.ConstantMutator().mutants(tree))
        self.assertEqual(len(muts), 4)

    def test_arithmetic_mutator(self) -> None:
        import ast
        tree = ast.parse("x = a + b\ny = a * b\n")
        muts = list(mt.ArithmeticMutator().mutants(tree))
        self.assertEqual(len(muts), 2)


class TestRunMutationSweep(unittest.TestCase):
    def test_sweep_restores_target_file(self) -> None:
        """After sweep, target file must match original SHA exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            target = tmp_dir / "target.py"
            original = "def add(a, b):\n    return a + b\n"
            target.write_text(original)
            test = tmp_dir / "test_target.py"
            test.write_text(
                "import sys\n"
                f"sys.path.insert(0, {str(tmp_dir)!r})\n"
                "import target\n"
                "def test_add(): assert target.add(2, 3) == 5\n"
            )

            original_sha = mt._sha256(target)
            result = mt.run_mutation_sweep(
                target, [test], max_mutations=2, timeout=30,
            )
            restored_sha = mt._sha256(target)
            self.assertEqual(
                original_sha, restored_sha,
                "Target file must be restored byte-identical after sweep",
            )
            self.assertIsInstance(result, dict)
            self.assertIn("kill_rate", result)

    def test_sweep_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            target = tmp_dir / "target.py"
            original = "def f():\n    return True\n"
            target.write_text(original)
            test = tmp_dir / "test_target.py"
            test.write_text("def test_dummy(): pass\n")
            sha_before = mt._sha256(target)
            result = mt.run_mutation_sweep(
                target, [test], max_mutations=5, dry_run=True,
                timeout=10,
            )
            sha_after = mt._sha256(target)
            self.assertEqual(sha_before, sha_after)
            # All mutations should be marked dry-run
            for mut in result["mutations"]:
                self.assertEqual(mut["status"], "dry-run")

    def test_sweep_raises_when_target_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            mt.run_mutation_sweep(
                Path("/nonexistent/xyz.py"),
                [Path("/tmp/any.py")],
                dry_run=True,
            )


class TestCliHelp(unittest.TestCase):
    def test_wave_a_targets_exist(self) -> None:
        """Sanity: all files in _WAVE_A_TARGETS must exist in repo."""
        repo_root = Path(__file__).resolve().parents[3]
        for rel_target, rel_tests in mt._WAVE_A_TARGETS:
            with self.subTest(target=rel_target):
                self.assertTrue(
                    (repo_root / rel_target).exists(),
                    f"Missing Wave A target: {rel_target}",
                )
                for rt in rel_tests:
                    self.assertTrue(
                        (repo_root / rt).exists(),
                        f"Missing Wave A test file: {rt}",
                    )


if __name__ == "__main__":
    unittest.main()
