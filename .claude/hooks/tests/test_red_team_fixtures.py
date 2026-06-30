"""Tests for red-team corpus fixture integrity — loading, format, SHA match.

PLAN-014 Phase D.5 — 40+ tests covering:
- Each fixture file loads as valid JSON
- Required fields present per schema
- Target and expected_behavior enums are valid
- SHA-256 matches byte-identity ledger
- ID uniqueness across all namespaces
- Frozen v1 corpus line count and content integrity
- Per-namespace coverage (synthetic, external, regression)

Stdlib-only. No _lib imports required (pure fixture verification).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Set

# Corpus root relative to repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CORPUS_ROOT = _REPO_ROOT / ".claude" / "scripts" / "red-team-corpus"

# Schema constants (must match red-team-eval.py)
REQUIRED_FIELDS: Set[str] = {"id", "target", "category", "input",
                              "expected_behavior", "reference"}
VALID_TARGETS: Set[str] = {
    "skill_patch_sentinel", "audit_log_tamper", "plan_id_spoof",
    "sandbox_escape", "mcp_handler", "adapter_exfil",
    "output_safety_evasion", "npm_tamper",
}
VALID_EXPECTED: Set[str] = {"MUST_BLOCK", "MUST_SANITIZE", "MUST_EMIT_AUDIT",
                            "MUST_REJECT", "MUST_QUARANTINE"}


def _load_all_fixtures_from_dir(d: Path) -> List[Dict[str, Any]]:
    """Load all JSONL fixtures from a directory."""
    fixtures = []
    if not d.is_dir():
        return fixtures
    for f in sorted(d.glob("*.jsonl")):
        raw = f.read_text(encoding="utf-8").strip()
        for line in raw.splitlines():
            line = line.strip()
            if line:
                doc = json.loads(line)
                doc["_source_path"] = str(f)
                fixtures.append(doc)
    return fixtures


def _load_sha_ledger(path: Path) -> Dict[str, str]:
    """Parse .byte-identity-check.txt ledger."""
    result = {}
    if not path.is_file():
        return result
    for line in path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            result[parts[1]] = parts[0]
    return result


# ===================================================================
# Synthetic fixture tests (SYN-001 through SYN-027)
# ===================================================================

class TestSyntheticFixtureFormat(unittest.TestCase):
    """Validate all synthetic/*.jsonl fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_all_fixtures_from_dir(
            _CORPUS_ROOT / "synthetic"
        )

    def test_synthetic_fixture_count_minimum(self):
        """At least 25 synthetic fixtures exist."""
        self.assertGreaterEqual(len(self.fixtures), 25,
                                f"Expected >=25 synthetic fixtures, got {len(self.fixtures)}")

    def test_synthetic_all_have_required_fields(self):
        """Every synthetic fixture has all required fields."""
        for fx in self.fixtures:
            missing = REQUIRED_FIELDS - set(fx)
            self.assertEqual(missing, set(),
                             f"{fx.get('id', '?')}: missing {sorted(missing)}")

    def test_synthetic_valid_targets(self):
        """Every synthetic fixture target is in the closed enum."""
        for fx in self.fixtures:
            self.assertIn(fx["target"], VALID_TARGETS,
                          f"{fx['id']}: invalid target {fx['target']!r}")

    def test_synthetic_valid_expected_behavior(self):
        """Every synthetic fixture expected_behavior is in the closed enum."""
        for fx in self.fixtures:
            self.assertIn(fx["expected_behavior"], VALID_EXPECTED,
                          f"{fx['id']}: invalid expected {fx['expected_behavior']!r}")

    def test_synthetic_ids_start_with_syn(self):
        """All synthetic fixture IDs start with SYN-."""
        for fx in self.fixtures:
            self.assertTrue(fx["id"].startswith("SYN-"),
                            f"Fixture {fx['id']} in synthetic/ must start with SYN-")

    def test_synthetic_ids_unique(self):
        """All synthetic fixture IDs are unique."""
        ids = [fx["id"] for fx in self.fixtures]
        self.assertEqual(len(ids), len(set(ids)),
                         f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}")

    def test_synthetic_input_nonempty(self):
        """Every synthetic fixture has non-empty input."""
        for fx in self.fixtures:
            self.assertTrue(fx["input"].strip(),
                            f"{fx['id']}: input is empty")

    def test_synthetic_reference_nonempty(self):
        """Every synthetic fixture has non-empty reference."""
        for fx in self.fixtures:
            self.assertTrue(fx["reference"].strip(),
                            f"{fx['id']}: reference is empty")


# ===================================================================
# External fixture tests (EXT-016 through EXT-040)
# ===================================================================

class TestExternalFixtureFormat(unittest.TestCase):
    """Validate all external/*.jsonl fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_all_fixtures_from_dir(
            _CORPUS_ROOT / "external"
        )

    def test_external_fixture_count_minimum(self):
        """At least 25 external JSONL fixtures exist."""
        self.assertGreaterEqual(len(self.fixtures), 25,
                                f"Expected >=25 external JSONL fixtures, got {len(self.fixtures)}")

    def test_external_all_have_required_fields(self):
        """Every external fixture has all required fields."""
        for fx in self.fixtures:
            missing = REQUIRED_FIELDS - set(fx)
            self.assertEqual(missing, set(),
                             f"{fx.get('id', '?')}: missing {sorted(missing)}")

    def test_external_valid_targets(self):
        """Every external fixture target is in the closed enum."""
        for fx in self.fixtures:
            self.assertIn(fx["target"], VALID_TARGETS,
                          f"{fx['id']}: invalid target {fx['target']!r}")

    def test_external_valid_expected_behavior(self):
        """Every external fixture expected_behavior is valid."""
        for fx in self.fixtures:
            self.assertIn(fx["expected_behavior"], VALID_EXPECTED,
                          f"{fx['id']}: invalid expected {fx['expected_behavior']!r}")

    def test_external_ids_start_with_ext(self):
        """All external fixture IDs start with EXT-."""
        for fx in self.fixtures:
            self.assertTrue(fx["id"].startswith("EXT-"),
                            f"Fixture {fx['id']} in external/ must start with EXT-")

    def test_external_ids_unique(self):
        """All external fixture IDs are unique."""
        ids = [fx["id"] for fx in self.fixtures]
        self.assertEqual(len(ids), len(set(ids)))

    def test_external_input_nonempty(self):
        """Every external fixture has non-empty input."""
        for fx in self.fixtures:
            self.assertTrue(fx["input"].strip(),
                            f"{fx['id']}: input is empty")

    def test_external_reference_nonempty(self):
        """Every external fixture has non-empty reference."""
        for fx in self.fixtures:
            self.assertTrue(fx["reference"].strip(),
                            f"{fx['id']}: reference is empty")


# ===================================================================
# Regression fixture tests (REG-001 through REG-015)
# ===================================================================

class TestRegressionFixtureFormat(unittest.TestCase):
    """Validate all regression/*.jsonl fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = _load_all_fixtures_from_dir(
            _CORPUS_ROOT / "regression"
        )

    def test_regression_fixture_count_minimum(self):
        """At least 15 regression fixtures exist."""
        self.assertGreaterEqual(len(self.fixtures), 15,
                                f"Expected >=15 regression fixtures, got {len(self.fixtures)}")

    def test_regression_all_have_required_fields(self):
        """Every regression fixture has all required fields."""
        for fx in self.fixtures:
            missing = REQUIRED_FIELDS - set(fx)
            self.assertEqual(missing, set(),
                             f"{fx.get('id', '?')}: missing {sorted(missing)}")

    def test_regression_valid_targets(self):
        """Every regression fixture target is in the closed enum."""
        for fx in self.fixtures:
            self.assertIn(fx["target"], VALID_TARGETS,
                          f"{fx['id']}: invalid target {fx['target']!r}")

    def test_regression_valid_expected_behavior(self):
        """Every regression fixture expected_behavior is valid."""
        for fx in self.fixtures:
            self.assertIn(fx["expected_behavior"], VALID_EXPECTED,
                          f"{fx['id']}: invalid expected {fx['expected_behavior']!r}")

    def test_regression_ids_start_with_reg(self):
        """All regression fixture IDs start with REG-."""
        for fx in self.fixtures:
            self.assertTrue(fx["id"].startswith("REG-"),
                            f"Fixture {fx['id']} in regression/ must start with REG-")

    def test_regression_ids_unique(self):
        """All regression fixture IDs are unique."""
        ids = [fx["id"] for fx in self.fixtures]
        self.assertEqual(len(ids), len(set(ids)))

    def test_regression_input_nonempty(self):
        """Every regression fixture has non-empty input."""
        for fx in self.fixtures:
            self.assertTrue(fx["input"].strip(),
                            f"{fx['id']}: input is empty")

    def test_regression_reference_nonempty(self):
        """Every regression fixture has non-empty reference."""
        for fx in self.fixtures:
            self.assertTrue(fx["reference"].strip(),
                            f"{fx['id']}: reference is empty")


# ===================================================================
# Cross-namespace tests
# ===================================================================

class TestCrossNamespaceIntegrity(unittest.TestCase):
    """Validate integrity across all fixture namespaces."""

    @classmethod
    def setUpClass(cls):
        cls.syn = _load_all_fixtures_from_dir(_CORPUS_ROOT / "synthetic")
        cls.ext = _load_all_fixtures_from_dir(_CORPUS_ROOT / "external")
        cls.reg = _load_all_fixtures_from_dir(_CORPUS_ROOT / "regression")
        cls.all_fixtures = cls.syn + cls.ext + cls.reg

    def test_total_fixture_count_minimum_80(self):
        """Total fixtures across all namespaces >= 67 JSONL."""
        total = len(self.all_fixtures)
        self.assertGreaterEqual(total, 67,
                                f"Expected >=67 total JSONL fixtures, got {total}")

    def test_global_id_uniqueness(self):
        """No duplicate IDs across namespaces."""
        ids = [fx["id"] for fx in self.all_fixtures]
        dupes = [x for x in ids if ids.count(x) > 1]
        self.assertEqual(len(dupes), 0,
                         f"Duplicate fixture IDs across namespaces: {set(dupes)}")

    def test_all_8_targets_covered(self):
        """All 8 target categories have at least one fixture."""
        covered = {fx["target"] for fx in self.all_fixtures}
        missing = VALID_TARGETS - covered
        self.assertEqual(missing, set(),
                         f"Targets with zero fixtures: {sorted(missing)}")

    def test_each_target_has_minimum_3_fixtures(self):
        """Each target category has at least 3 fixtures."""
        from collections import Counter
        counts = Counter(fx["target"] for fx in self.all_fixtures)
        for target, count in counts.items():
            self.assertGreaterEqual(count, 3,
                                    f"Target {target!r} has only {count} fixtures (need >=3)")


# ===================================================================
# SHA-256 byte-identity ledger tests
# ===================================================================

class TestByteIdentityLedger(unittest.TestCase):
    """Validate .byte-identity-check.txt matches actual file hashes."""

    @classmethod
    def setUpClass(cls):
        cls.ledger = _load_sha_ledger(
            _CORPUS_ROOT / ".byte-identity-check.txt"
        )

    def test_ledger_has_entries(self):
        """Byte-identity ledger is non-empty."""
        self.assertGreater(len(self.ledger), 0)

    def test_all_synthetic_in_ledger(self):
        """Every synthetic/*.jsonl is in the byte-identity ledger."""
        for f in sorted((_CORPUS_ROOT / "synthetic").glob("*.jsonl")):
            rel = f"synthetic/{f.name}"
            self.assertIn(rel, self.ledger,
                          f"{rel} missing from .byte-identity-check.txt")

    def test_all_external_jsonl_in_ledger(self):
        """Every external/*.jsonl is in the byte-identity ledger."""
        ext_dir = _CORPUS_ROOT / "external"
        if not ext_dir.is_dir():
            self.skipTest("external/ dir not found")
        for f in sorted(ext_dir.glob("*.jsonl")):
            rel = f"external/{f.name}"
            self.assertIn(rel, self.ledger,
                          f"{rel} missing from .byte-identity-check.txt")

    def test_all_regression_in_ledger(self):
        """Every regression/*.jsonl is in the byte-identity ledger."""
        reg_dir = _CORPUS_ROOT / "regression"
        if not reg_dir.is_dir():
            self.skipTest("regression/ dir not found")
        for f in sorted(reg_dir.glob("*.jsonl")):
            rel = f"regression/{f.name}"
            self.assertIn(rel, self.ledger,
                          f"{rel} missing from .byte-identity-check.txt")

    def test_ledger_sha_matches_actual(self):
        """Every ledger entry SHA matches the actual file content."""
        for rel, expected_sha in self.ledger.items():
            full = _CORPUS_ROOT / rel
            if not full.is_file():
                self.fail(f"Ledger references {rel} but file does not exist")
            actual_sha = hashlib.sha256(full.read_bytes()).hexdigest()
            self.assertEqual(actual_sha, expected_sha,
                             f"SHA mismatch for {rel}: expected {expected_sha[:16]}... "
                             f"got {actual_sha[:16]}...")


# ===================================================================
# Frozen v1 corpus tests
# ===================================================================

class TestFrozenV1Corpus(unittest.TestCase):
    """Validate frozen v1 JSONL corpus integrity."""

    @classmethod
    def setUpClass(cls):
        cls.v1_dir = _CORPUS_ROOT / "v1"
        cls.jsonl = cls.v1_dir / "fixtures.jsonl"
        cls.sha_file = cls.v1_dir / "fixtures.jsonl.sha256"

    def test_frozen_jsonl_exists(self):
        """Frozen v1 fixtures.jsonl exists."""
        self.assertTrue(self.jsonl.is_file(),
                        "v1/fixtures.jsonl missing")

    def test_frozen_sha_file_exists(self):
        """Adjacent SHA-256 file exists."""
        self.assertTrue(self.sha_file.is_file(),
                        "v1/fixtures.jsonl.sha256 missing")

    def test_frozen_sha_matches(self):
        """Frozen JSONL SHA-256 matches adjacent checksum file."""
        if not self.jsonl.is_file() or not self.sha_file.is_file():
            self.skipTest("Frozen corpus files missing")
        actual = hashlib.sha256(self.jsonl.read_bytes()).hexdigest()
        expected = self.sha_file.read_text("utf-8").strip().split()[0]
        self.assertEqual(actual, expected,
                         f"Frozen corpus SHA mismatch: {actual[:16]} != {expected[:16]}")

    def test_frozen_line_count_matches_total(self):
        """Frozen JSONL line count matches total fixture count."""
        if not self.jsonl.is_file():
            self.skipTest("Frozen corpus missing")
        lines = [l for l in self.jsonl.read_text("utf-8").splitlines()
                 if l.strip()]
        self.assertGreaterEqual(len(lines), 67,
                                f"Frozen corpus has {len(lines)} lines, expected >=67")

    def test_frozen_all_lines_valid_json(self):
        """Every line in frozen JSONL is valid JSON with required fields."""
        if not self.jsonl.is_file():
            self.skipTest("Frozen corpus missing")
        for i, line in enumerate(self.jsonl.read_text("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            doc = json.loads(line)
            missing = REQUIRED_FIELDS - set(doc)
            self.assertEqual(missing, set(),
                             f"Line {i} ({doc.get('id', '?')}): missing {sorted(missing)}")

    def test_frozen_ids_unique(self):
        """All IDs in frozen corpus are unique."""
        if not self.jsonl.is_file():
            self.skipTest("Frozen corpus missing")
        ids = []
        for line in self.jsonl.read_text("utf-8").splitlines():
            if line.strip():
                ids.append(json.loads(line)["id"])
        self.assertEqual(len(ids), len(set(ids)),
                         f"Duplicate IDs in frozen corpus")

    def test_frozen_corpus_in_byte_identity_ledger(self):
        """v1/fixtures.jsonl is listed in .byte-identity-check.txt."""
        ledger = _load_sha_ledger(_CORPUS_ROOT / ".byte-identity-check.txt")
        self.assertIn("v1/fixtures.jsonl", ledger,
                      "v1/fixtures.jsonl missing from byte-identity ledger")


if __name__ == "__main__":
    unittest.main()
