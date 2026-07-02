"""Tests for docs/benchmarks/manifest.schema.json

PLAN-051 Phase 5 pre-registration — schema pin for
`_benchmark_replay.py` manifest format. Consensus Cluster 4 + QA
Missing item: "JSON Schema pin locks manifest format; otherwise
Phase 5 adapters drift silently."

Stdlib-only (per CLAUDE.md §Critical Rules). Parses schema via
`json` module; runs validity assertions manually (no third-party
jsonschema lib).

Run:
  python3 -m pytest .claude/scripts/swarm/tests/test_benchmark_manifest_schema.py -v
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent.parent  # scripts/swarm/tests → repo root

_SCHEMA_PATH = _REPO_ROOT / "docs" / "benchmarks" / "manifest.schema.json"
_EXAMPLE_PATH = _REPO_ROOT / "docs" / "benchmarks" / "swarm-replay-example.json"

_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_schema():
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


class TestSchemaValidity(TestEnvContext):
    """The schema document itself must be valid JSON and self-consistent."""

    def test_schema_file_exists(self):
        self.assertTrue(
            _SCHEMA_PATH.exists(),
            f"manifest schema missing: {_SCHEMA_PATH}",
        )

    def test_schema_is_valid_json(self):
        # If this raises, pytest reports a clear failure.
        _load_schema()

    def test_schema_declares_draft(self):
        schema = _load_schema()
        self.assertIn("$schema", schema)
        self.assertIn("json-schema.org", schema["$schema"])

    def test_schema_has_title_and_description(self):
        schema = _load_schema()
        self.assertIn("title", schema)
        self.assertIn("description", schema)
        self.assertIn("ceo-orchestration", schema["title"])

    def test_required_top_level_fields(self):
        schema = _load_schema()
        required = schema.get("required", [])
        # Per ADR-071 + fairness-protocol.md §3-4.
        for field in (
            "schema_version",
            "fairness_protocol_ref",
            "tasks",
            "sandbox",
        ):
            self.assertIn(field, required, f"top-level `{field}` must be required")

    def test_additional_properties_strict(self):
        """Top-level and sub-objects should reject unknown keys to prevent
        silent manifest drift (QA Missing item)."""
        schema = _load_schema()
        self.assertFalse(
            schema.get("additionalProperties", True),
            "top-level additionalProperties must be false",
        )
        # Sub-objects must also be strict.
        for subobject_name in (
            "competitor_context",
            "sandbox",
            "measurement",
            "independent_verifier",
            "budget",
        ):
            subobj = schema["properties"][subobject_name]
            self.assertFalse(
                subobj.get("additionalProperties", True),
                f"`{subobject_name}` must have additionalProperties: false",
            )


class TestSchemaFairnessConstraints(TestEnvContext):
    """Test that the schema encodes the fairness protocol §3-5 constraints."""

    def test_sandbox_network_mode_enum(self):
        schema = _load_schema()
        network_mode = schema["properties"]["sandbox"]["properties"]["network_mode"]
        self.assertEqual(
            set(network_mode["enum"]),
            {"none", "host-allowlist"},
            "sandbox.network_mode must be {none, host-allowlist} per Security Risk #3",
        )

    def test_sandbox_requires_digest_pin(self):
        schema = _load_schema()
        digest = schema["properties"]["sandbox"]["properties"]["container_image_digest"]
        self.assertIn("pattern", digest)
        # Must include @sha256: to enforce digest pin, not tag.
        self.assertIn("sha256:", digest["pattern"])

    def test_measurement_default_n_runs_is_10_or_more(self):
        schema = _load_schema()
        n_runs = schema["properties"]["measurement"]["properties"]["n_runs_per_task"]
        self.assertGreaterEqual(
            n_runs.get("minimum", 0),
            10,
            "n_runs_per_task minimum must be ≥10 per fairness protocol §3.1",
        )
        self.assertGreaterEqual(n_runs.get("default", 0), 10)

    def test_measurement_stats_forbid_mean_only(self):
        """Schema must allow percentile reporting, mean permitted but
        protocol §3.2 forbids mean-ALONE. Default MUST include
        percentiles."""
        schema = _load_schema()
        stats = schema["properties"]["measurement"]["properties"][
            "statistics_required"
        ]
        default = set(stats.get("default", []))
        self.assertIn("median", default)
        self.assertIn("p95", default)
        self.assertIn("p99", default)

    def test_independent_verifier_required_key(self):
        schema = _load_schema()
        verifier = schema["properties"]["independent_verifier"]
        required = verifier.get("required", [])
        self.assertIn(
            "required",
            required,
            "independent_verifier.required must be a mandatory key per ADR-071",
        )

    def test_independent_verifier_tolerance_default_5pct(self):
        schema = _load_schema()
        tol = schema["properties"]["independent_verifier"]["properties"][
            "tolerance_p95_pct"
        ]
        self.assertEqual(
            tol.get("default"),
            5.0,
            "default tolerance must be ±5% per fairness protocol §5",
        )

    def test_budget_ceiling_is_1000_usd(self):
        schema = _load_schema()
        budget = schema["properties"]["budget"]["properties"]["max_total_usd"]
        self.assertLessEqual(
            budget.get("maximum", float("inf")),
            1000.0,
            "max_total_usd ceiling must be ≤$1000 per fairness protocol §6",
        )

    def test_fairness_protocol_ref_pattern(self):
        schema = _load_schema()
        ref = schema["properties"]["fairness_protocol_ref"]
        self.assertIn("pattern", ref)
        # Must require docs/benchmarks/ prefix + -fairness-protocol.md suffix.
        self.assertIn("fairness-protocol", ref["pattern"])


class TestSchemaWithExample(TestEnvContext):
    """If the example manifest exists, verify it parses under the schema."""

    def test_example_manifest_loadable(self):
        """Sanity: existing swarm-replay-example.json parses as JSON.

        Note: swarm-replay-example.json predates this schema (Session
        54 Phase 7b) and uses a DIFFERENT format optimized for
        coordinator replay. This test ONLY checks JSON validity,
        not schema conformance — the schema governs Phase 5 benchmarks
        specifically, not the coordinator-replay example.
        """
        if not _EXAMPLE_PATH.exists():
            self.skipTest(f"example manifest not present: {_EXAMPLE_PATH}")
        with _EXAMPLE_PATH.open() as f:
            json.load(f)  # must not raise


class TestSchemaDocumentation(TestEnvContext):
    """The schema must be self-documenting — every field has description."""

    def _walk_schema(self, schema_fragment, path="<root>"):
        """Collect paths to properties without a description."""
        missing = []
        if not isinstance(schema_fragment, dict):
            return missing
        if "properties" in schema_fragment:
            for prop_name, prop_def in schema_fragment["properties"].items():
                if isinstance(prop_def, dict):
                    if "description" not in prop_def:
                        missing.append(f"{path}.{prop_name}")
                    missing.extend(
                        self._walk_schema(prop_def, f"{path}.{prop_name}")
                    )
        if "items" in schema_fragment and isinstance(
            schema_fragment["items"], dict
        ):
            missing.extend(
                self._walk_schema(schema_fragment["items"], f"{path}[]")
            )
        return missing

    def test_every_property_has_description(self):
        schema = _load_schema()
        missing = self._walk_schema(schema)
        self.assertEqual(
            missing,
            [],
            f"schema properties missing description: {missing}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
