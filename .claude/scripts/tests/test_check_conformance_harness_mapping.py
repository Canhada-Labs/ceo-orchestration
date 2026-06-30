"""Unit tests for check-conformance-harness-mapping.py — PLAN-013 Phase D.8.

Subclasses `TestEnvContext` per CLAUDE.md §5 + PLAN-013 consensus §S11.

Covers 8 scenarios:

1. clean_repo_exits_zero — fully populated mapping + tests + mutations → exit 0
2. missing_test_method_fails — mapping references non-existent test method
3. missing_mutation_files_fails — mapping declares count but files absent
4. offcount_mutations_fails — declared count mismatches actual on-disk count
5. stale_impl_reference_fails — mapping references non-existent impl file
6. malformed_mapping_fails — mapping file empty / no property rows
7. missing_mapping_file_errors — no mapping file at path (internal error, exit 2)
8. verbose_output_renders_human_summary — --verbose renders per-row lines
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = SCRIPT_ROOT / "scripts" / "check-conformance-harness-mapping.py"


# A minimal but COMPLETE mapping stanza: 4 property rows with all 6 columns.
# Each row uses standard pytest-node-id test refs and repo-relative impl paths.
_CLEAN_MAPPING = """\
# Stub properties-proved.md §2 mapping

| ID | TLA+ | Conformance test | Impl | Log | Mutations |
|----|------|------------------|------|-----|-----------|
| **S1** | `[](_)` | `tests/formal_verification/test_breaker_conformance.py::test_s1_breaker_opens_on_threshold` | `.claude/hooks/_lib/adapters/live/_breaker.py:176-211` | `<pending>` | **6** |
| **S2** | `[](a \\| b)` | `tests/formal_verification/test_breaker_conformance.py::test_s2_half_open_singleton` | `.claude/hooks/_lib/adapters/live/_breaker.py:154-174` | `<pending>` | **5** |
| **S3** | `[](a)` | `tests/formal_verification/test_breaker_conformance.py::test_s3_open_emits_audit` | `.claude/hooks/_lib/adapters/live/_breaker.py:246-250` + `.claude/hooks/_lib/audit_emit.py:977` | `<pending>` | **5** |
| **L1** | `[](<>)` | `tests/formal_verification/test_breaker_conformance.py::test_l1_eventually_heal` | `.claude/hooks/_lib/adapters/live/_breaker.py:257-266` | `<pending>` | **5** |
"""


def _write_mapping(tmpdir: Path, content: str) -> Path:
    docs = tmpdir / "docs" / "formal-verification"
    docs.mkdir(parents=True, exist_ok=True)
    path = docs / "properties-proved.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_tests_file(
    tmpdir: Path,
    methods: tuple = (
        "test_s1_breaker_opens_on_threshold",
        "test_s2_half_open_singleton",
        "test_s3_open_emits_audit",
        "test_l1_eventually_heal",
    ),
) -> Path:
    tests_dir = tmpdir / "tests" / "formal_verification"
    tests_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "from __future__ import annotations",
        "import unittest",
        "",
        "class T(unittest.TestCase):",
    ]
    for m in methods:
        lines.append(f"    def {m}(self):")
        lines.append("        pass")
    lines.append("")
    path = tests_dir / "test_breaker_conformance.py"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_mutation(
    tmpdir: Path,
    property_id: str,
    nn: int,
) -> Path:
    mut_dir = tmpdir / "tests" / "formal_verification" / "mutation_fixtures" / "breaker"
    mut_dir.mkdir(parents=True, exist_ok=True)
    name = f"mut_{property_id.lower()}_{nn:02d}_stub.py"
    path = mut_dir / name
    path.write_text(
        f'from __future__ import annotations\nPROPERTY = "{property_id}"\n'
        f'DESCRIPTION = "stub mutation #{nn}"\n'
        "def apply(cb_cls):\n"
        "    return cb_cls\n",
        encoding="utf-8",
    )
    return path


def _populate_mutations(tmpdir: Path, counts: dict) -> None:
    for prop, n in counts.items():
        for i in range(1, n + 1):
            _write_mutation(tmpdir, prop, i)


def _write_impl_files(tmpdir: Path) -> None:
    """Create the impl paths referenced in the clean mapping."""
    hooks = tmpdir / ".claude" / "hooks" / "_lib"
    live = hooks / "adapters" / "live"
    live.mkdir(parents=True, exist_ok=True)
    (live / "_breaker.py").write_text(
        "# stub impl\nclass CircuitBreaker: pass\n", encoding="utf-8"
    )
    (hooks / "audit_emit.py").write_text(
        "# stub audit\n", encoding="utf-8"
    )


def _run(tmpdir: Path, json_out: bool = False, verbose: bool = False):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(tmpdir),
    ]
    if json_out:
        cmd.append("--json")
    if verbose:
        cmd.append("--verbose")
    return subprocess.run(cmd, capture_output=True, text=True)


class TestConformanceHarnessMapping(TestEnvContext):

    def _setup_clean(self) -> None:
        # Root dirs must exist under self.project_dir
        self.project_dir.mkdir(parents=True, exist_ok=True)
        (self.project_dir / ".claude").mkdir(parents=True, exist_ok=True)
        (self.project_dir / "tests").mkdir(parents=True, exist_ok=True)
        _write_mapping(self.project_dir, _CLEAN_MAPPING)
        _write_tests_file(self.project_dir)
        _populate_mutations(self.project_dir, {"S1": 6, "S2": 5, "S3": 5, "L1": 5})
        _write_impl_files(self.project_dir)

    # 1
    def test_1_clean_repo_exits_zero(self) -> None:
        self._setup_clean()
        result = _run(self.project_dir)
        self.assertEqual(
            result.returncode,
            0,
            msg=(
                "clean repo expected exit 0; got "
                f"{result.returncode}\nSTDOUT:\n{result.stdout}\n"
                f"STDERR:\n{result.stderr}"
            ),
        )
        self.assertIn("OK", result.stdout)

    # 2
    def test_2_missing_test_method_fails(self) -> None:
        self._setup_clean()
        # Overwrite tests file with only 3 methods (drop S2).
        _write_tests_file(
            self.project_dir,
            methods=(
                "test_s1_breaker_opens_on_threshold",
                "test_s3_open_emits_audit",
                "test_l1_eventually_heal",
            ),
        )
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("test_s2_half_open_singleton", result.stdout)

    # 3
    def test_3_missing_mutation_files_fails(self) -> None:
        self._setup_clean()
        # Delete all S1 mutations.
        mut_dir = self.project_dir / "tests" / "formal_verification" / "mutation_fixtures" / "breaker"
        for f in mut_dir.glob("mut_s1_*.py"):
            f.unlink()
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("S1", result.stdout)

    # 4
    def test_4_offcount_mutations_fails(self) -> None:
        self._setup_clean()
        # Add an EXTRA S2 mutation so declared (5) != actual (6).
        _write_mutation(self.project_dir, "S2", 99)
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("declared", result.stdout)

    # 5
    def test_5_stale_impl_reference_fails(self) -> None:
        self._setup_clean()
        # Delete the impl file that S1 references.
        (self.project_dir / ".claude" / "hooks" / "_lib" / "adapters" / "live" / "_breaker.py").unlink()
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing file", result.stdout)

    # 6
    def test_6_malformed_mapping_fails(self) -> None:
        self._setup_clean()
        # Replace mapping with one that has NO property rows.
        _write_mapping(
            self.project_dir,
            "# empty mapping\n\nNo property rows here at all.\n",
        )
        result = _run(self.project_dir, verbose=True)
        # no rows parsed → exit 2 (internal error / malformed)
        self.assertEqual(result.returncode, 2)

    # 7
    def test_7_missing_mapping_file_errors(self) -> None:
        self._setup_clean()
        # Delete the mapping entirely.
        (self.project_dir / "docs" / "formal-verification" / "properties-proved.md").unlink()
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 2)

    # 8
    def test_8_verbose_output_renders_human_summary(self) -> None:
        self._setup_clean()
        result = _run(self.project_dir, verbose=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Verbose shows per-property status lines.
        for prop in ("S1", "S2", "S3", "L1"):
            self.assertIn(f"[{prop}]", result.stdout)
        # JSON output is different contract — probe separately.
        result_json = _run(self.project_dir, json_out=True)
        self.assertEqual(result_json.returncode, 0)
        payload = json.loads(result_json.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["rows"]), 4)


if __name__ == "__main__":
    import unittest

    unittest.main()
