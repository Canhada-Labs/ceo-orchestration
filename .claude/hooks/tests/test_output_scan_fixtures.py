"""Fixture-driven tests for _lib/output_scan.py (PLAN-029 / ADR-057).

Reads `.claude/hooks/tests/fixtures/output_scan/scenarios.jsonl` and
exercises each scenario. Fixtures are byte-identity (content survives
format changes); the test harness decodes unicode escape sequences.

Each fixture line:
    {
      "name": "<human-readable>",
      "input": "<text>",
      "expected_total": N,           # exact count
      OR
      "expected_total_min": N,       # at least N
      "expected_families": {family: count, ...},
      "note": "optional annotation"
    }
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]

from _lib import output_scan  # type: ignore  # noqa: E402

_FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures" / "output_scan" / "scenarios.jsonl"
)


def _load_scenarios() -> list:
    scenarios = []
    with _FIXTURE_PATH.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                scenarios.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Fixture parse error at line {i}: {e} -- content: {line[:80]!r}"
                )
    return scenarios


class TestOutputScanFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = _load_scenarios()
        assert len(cls.scenarios) >= 20, (
            f"Expected ≥20 fixtures, found {len(cls.scenarios)}"
        )

    def test_fixture_file_valid_jsonl(self) -> None:
        """Parse-test already happens in setUpClass; this test formalizes it."""
        self.assertGreaterEqual(len(self.scenarios), 20)

    def test_fixture_count_min(self) -> None:
        """Acceptance: 20+ byte-identity fixtures."""
        self.assertGreaterEqual(len(self.scenarios), 20)

    def test_each_fixture_scans_without_raising(self) -> None:
        for scen in self.scenarios:
            with self.subTest(name=scen["name"]):
                try:
                    result = output_scan.scan(scen["input"])
                except Exception as e:
                    self.fail(
                        f"scan raised on fixture '{scen['name']}': "
                        f"{type(e).__name__}: {e}"
                    )
                self.assertIsInstance(result, dict)

    def test_each_fixture_matches_expected(self) -> None:
        for scen in self.scenarios:
            with self.subTest(name=scen["name"]):
                result = output_scan.scan(scen["input"])

                # Exact total check
                if "expected_total" in scen:
                    self.assertEqual(
                        result["total_findings"],
                        scen["expected_total"],
                        f"{scen['name']}: total mismatch",
                    )

                # Minimum total check
                if "expected_total_min" in scen:
                    self.assertGreaterEqual(
                        result["total_findings"],
                        scen["expected_total_min"],
                        f"{scen['name']}: expected at least {scen['expected_total_min']}",
                    )

                # Family check — each family in expected must appear in result
                for family, min_count in scen.get("expected_families", {}).items():
                    actual = result["family_counts"].get(family, 0)
                    self.assertGreaterEqual(
                        actual, min_count,
                        f"{scen['name']}: family '{family}' expected ≥{min_count}, got {actual}",
                    )


class TestClassicFixtureCoverage(unittest.TestCase):
    """Spot-check specific classic fixtures we rely on."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = {s["name"]: s for s in _load_scenarios()}

    def test_force_with_lease_is_false_positive_safe(self) -> None:
        scen = self.scenarios["llm08_force_with_lease_safe"]
        result = output_scan.scan(scen["input"])
        self.assertEqual(result["total_findings"], 0)

    def test_clean_markdown_passes(self) -> None:
        scen = self.scenarios["clean_markdown_no_findings"]
        result = output_scan.scan(scen["input"])
        self.assertEqual(result["total_findings"], 0)

    def test_combined_scenario_hits_three_families(self) -> None:
        scen = self.scenarios["combined_unicode_telemetry_sensitive"]
        result = output_scan.scan(scen["input"])
        self.assertGreaterEqual(
            len(result["family_counts"]), 3,
            "Combined scenario must hit at least 3 families",
        )


if __name__ == "__main__":
    unittest.main()
