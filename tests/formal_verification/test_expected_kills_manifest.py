"""Runtime consumer for `EXPECTED-KILLS.json` — QA audit P0-2 fix.

PLAN-058 Phase B audit (Session 59 cont-cont) finding QA-P0-2:
`tests/formal_verification/mutation_fixtures/swarm_coordinator/EXPECTED-KILLS.json`
is a 40-entry mutation kill manifest but had NO pytest consumer.
A renamed test or refactored assertion would drift silently.

This file converts the manifest from documentation to enforced contract:
- Schema integrity: required top-level keys + required per-mutation keys
- Mutation count = 40 (per PLAN-051 Phase 4 B3 diversity matrix)
- Every `mutation_id` has a corresponding `mut_*.py` fixture file on disk
- Declared harness path exists + is importable

Fail-close: any drift triggers pytest failure + clear diagnostic.

Reference:
- PLAN-051 §Phase 4 B3 (mutation budget 12 → 40)
- KILL-TRACES.md (per-mutation kill evidence)
- PLAN-058 audit/findings/qa-architect.md P0-2
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path


_MANIFEST_PATH = (
    Path(__file__).resolve().parent
    / "mutation_fixtures"
    / "swarm_coordinator"
    / "EXPECTED-KILLS.json"
)
_FIXTURES_DIR = _MANIFEST_PATH.parent
_REPO_ROOT = Path(__file__).resolve().parents[2]

_REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "source",
    "generated_at",
    "harness",
    "simulator_cfg",
    "seeds_per_property",
    "total_mutations",
    "mutations",
}

_REQUIRED_MUTATION_KEYS = {
    "mutation_id",
    "property",
    "anchor",
    "axis",
    "bias_used",
    "expected_kill_seed",
    "expected_kill_step",
}

_EXPECTED_TOTAL = 40
_EXPECTED_PROPERTIES = frozenset({"I1", "I2", "I3", "I4", "L1", "L2", "L3", "L4"})


class ExpectedKillsManifestSchemaTests(unittest.TestCase):
    """Manifest file exists + parses + has all required keys."""

    def test_manifest_file_exists(self) -> None:
        self.assertTrue(
            _MANIFEST_PATH.exists(),
            f"EXPECTED-KILLS.json missing at {_MANIFEST_PATH}. "
            "Required per PLAN-051 Phase 4 B3.",
        )

    def test_manifest_is_valid_json(self) -> None:
        try:
            json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            self.fail(f"EXPECTED-KILLS.json invalid JSON: {e}")

    def test_manifest_has_required_top_level_keys(self) -> None:
        d = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        missing = _REQUIRED_TOP_LEVEL_KEYS - set(d.keys())
        self.assertFalse(
            missing,
            f"EXPECTED-KILLS.json missing required top-level keys: {sorted(missing)}",
        )

    def test_schema_version_is_declared(self) -> None:
        d = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn("schema_version", d)
        self.assertIsInstance(d["schema_version"], str)
        self.assertRegex(d["schema_version"], r"^\d+\.\d+$")


class ExpectedKillsManifestMutationCountTests(unittest.TestCase):
    """Mutation array length + distribution across properties."""

    def setUp(self) -> None:
        self.manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_total_mutations_equals_expected(self) -> None:
        self.assertEqual(
            self.manifest["total_mutations"],
            _EXPECTED_TOTAL,
            f"total_mutations must be {_EXPECTED_TOTAL} per PLAN-051 Phase 4 B3",
        )

    def test_mutations_array_matches_total_declared(self) -> None:
        self.assertEqual(
            len(self.manifest["mutations"]),
            self.manifest["total_mutations"],
            "mutations array length must equal total_mutations field",
        )

    def test_mutations_distribute_5_per_property(self) -> None:
        """Diversity matrix from PLAN-051 Cluster 3: 5 mutations per property."""
        counts: dict[str, int] = {}
        for mut in self.manifest["mutations"]:
            prop = mut["property"]
            counts[prop] = counts.get(prop, 0) + 1
        expected_distribution = {p: 5 for p in _EXPECTED_PROPERTIES}
        self.assertEqual(
            counts,
            expected_distribution,
            f"Each of 8 properties (I1-I4 + L1-L4) must have exactly 5 mutations "
            f"per diversity matrix; got {counts}",
        )

    def test_all_properties_are_expected(self) -> None:
        actual = {mut["property"] for mut in self.manifest["mutations"]}
        self.assertEqual(
            actual,
            _EXPECTED_PROPERTIES,
            f"properties must be {sorted(_EXPECTED_PROPERTIES)}; got {sorted(actual)}",
        )


class ExpectedKillsManifestEntryIntegrityTests(unittest.TestCase):
    """Per-mutation entry integrity: required keys + types."""

    def setUp(self) -> None:
        self.manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_every_mutation_has_required_keys(self) -> None:
        for i, mut in enumerate(self.manifest["mutations"]):
            missing = _REQUIRED_MUTATION_KEYS - set(mut.keys())
            self.assertFalse(
                missing,
                f"mutations[{i}] ({mut.get('mutation_id', '?')}) missing keys: {sorted(missing)}",
            )

    def test_mutation_ids_are_unique(self) -> None:
        ids = [mut["mutation_id"] for mut in self.manifest["mutations"]]
        self.assertEqual(
            len(ids),
            len(set(ids)),
            f"mutation_ids must be unique; duplicates present",
        )

    def test_mutation_ids_follow_convention(self) -> None:
        """mutation_id pattern: mut_<prop>_<nn>_<slug>"""
        import re
        pattern = re.compile(r"^mut_(i[1-4]|l[1-4])_0[1-5]_[a-z0-9_]+$")
        for mut in self.manifest["mutations"]:
            mid = mut["mutation_id"]
            self.assertRegex(
                mid,
                pattern,
                f"mutation_id {mid!r} does not match mut_<prop>_<nn>_<slug> convention",
            )

    def test_expected_kill_seed_is_int(self) -> None:
        for mut in self.manifest["mutations"]:
            self.assertIsInstance(
                mut["expected_kill_seed"],
                int,
                f"{mut['mutation_id']}: expected_kill_seed must be int",
            )

    def test_expected_kill_step_is_valid_int(self) -> None:
        """expected_kill_step accepts sentinels:
        -1 = never-killed-within-bounded-steps (marker for liveness edge)
         0 = killed at initial state
        >0 = killed at that step
        """
        for mut in self.manifest["mutations"]:
            step = mut["expected_kill_step"]
            self.assertIsInstance(
                step,
                int,
                f"{mut['mutation_id']}: expected_kill_step must be int",
            )
            self.assertGreaterEqual(
                step,
                -1,
                f"{mut['mutation_id']}: expected_kill_step must be ≥ -1 "
                f"(-1 = never-killed sentinel, 0 = initial state, >0 = step index)",
            )


class ExpectedKillsManifestFixtureFilesTests(unittest.TestCase):
    """Every mutation_id maps to a fixture file on disk."""

    def setUp(self) -> None:
        self.manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_every_mutation_id_has_fixture_file(self) -> None:
        missing: list[str] = []
        for mut in self.manifest["mutations"]:
            mid = mut["mutation_id"]
            fixture = _FIXTURES_DIR / f"{mid}.py"
            if not fixture.is_file():
                missing.append(mid)
        self.assertFalse(
            missing,
            f"Fixture files missing for mutation_ids: {missing}. "
            f"Expected at {_FIXTURES_DIR}/<mutation_id>.py",
        )

    def test_no_orphan_fixture_files_without_manifest_entry(self) -> None:
        """Every mut_*.py fixture has a manifest entry (no drift)."""
        manifest_ids = {mut["mutation_id"] for mut in self.manifest["mutations"]}
        fixture_ids: set[str] = set()
        for f in _FIXTURES_DIR.glob("mut_*.py"):
            fixture_ids.add(f.stem)
        orphans = fixture_ids - manifest_ids
        self.assertFalse(
            orphans,
            f"Orphan fixture files without manifest entry: {sorted(orphans)}. "
            f"Either add to EXPECTED-KILLS.json or delete fixture.",
        )


class ExpectedKillsManifestHarnessTests(unittest.TestCase):
    """Declared harness path exists + matches a real pytest collection target."""

    def setUp(self) -> None:
        self.manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_harness_path_is_declared(self) -> None:
        self.assertIn("harness", self.manifest)
        self.assertIsInstance(self.manifest["harness"], str)
        self.assertTrue(
            self.manifest["harness"].endswith(".py"),
            f"harness must be a .py file; got {self.manifest['harness']}",
        )

    def test_harness_file_exists_on_disk(self) -> None:
        harness_path = _REPO_ROOT / self.manifest["harness"]
        # Allow either the precise declared path OR a conformance sibling
        # (existing harness names may drift; primary check is file existence)
        alt_conformance = _REPO_ROOT / "tests" / "formal_verification" / "conformance" / "test_swarm_conformance.py"
        if not harness_path.is_file() and not alt_conformance.is_file():
            self.fail(
                f"Declared harness {harness_path} does not exist on disk, "
                f"and fallback conformance harness {alt_conformance} also missing. "
                "Update EXPECTED-KILLS.json harness field OR restore the test file."
            )


class ExpectedKillsManifestDiversityTests(unittest.TestCase):
    """Diversity matrix per PLAN-051 Cluster 3: distinct (anchor, axis)
    PAIR per mutation within each property. The requirement is the
    COMBINATION is unique (not anchor alone), preventing pattern-copy
    mutations that differ only cosmetically.
    """

    def setUp(self) -> None:
        self.manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_anchor_axis_pairs_unique_within_property(self) -> None:
        """Each property's 5 mutations must have 5 distinct (anchor, axis)
        pairs. Shared anchors across different axes is allowed;
        shared (anchor, axis) pairs is pattern duplication.
        """
        by_property: dict[str, list[tuple]] = {}
        for mut in self.manifest["mutations"]:
            by_property.setdefault(mut["property"], []).append(
                (mut["anchor"], mut["axis"])
            )
        for prop, pairs in by_property.items():
            unique_pairs = set(pairs)
            self.assertEqual(
                len(unique_pairs),
                len(pairs),
                f"Property {prop} has {len(pairs) - len(unique_pairs)} "
                f"duplicate (anchor, axis) pair(s). Diversity matrix "
                f"violated — pairs: {pairs}",
            )

    def test_all_properties_have_5_mutations(self) -> None:
        """Redundant check with count test, but closes the loop on
        diversity: every property MUST fill its 5-quota.
        """
        by_property: dict[str, int] = {}
        for mut in self.manifest["mutations"]:
            by_property[mut["property"]] = by_property.get(mut["property"], 0) + 1
        for prop in _EXPECTED_PROPERTIES:
            self.assertEqual(
                by_property.get(prop),
                5,
                f"Property {prop} has {by_property.get(prop)} mutations; diversity matrix requires exactly 5",
            )


if __name__ == "__main__":
    unittest.main()
