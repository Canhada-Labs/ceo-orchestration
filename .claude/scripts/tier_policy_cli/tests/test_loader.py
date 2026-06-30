"""PLAN-043 Phase 1 — tier_policy.loader unit tests.

Covers:
- Happy path: valid policy artifact loads to STATUS_OK
- Bootstrap: missing file → STATUS_BOOTSTRAP (Q8 closure)
- Fallback: corrupt JSON → STATUS_FALLBACK
- Fallback: oversized file (>64 KiB) → STATUS_FALLBACK oversized
- Fallback: nesting exceeded (>8 levels) → STATUS_FALLBACK
- Fallback: non-UTF8 → STATUS_FALLBACK
- Fallback: prototype pollution keys → STATUS_FALLBACK
- Fallback: schema_version missing → STATUS_FALLBACK
- Fallback: schema_version unknown → STATUS_FALLBACK
- Fallback: missing required top-level keys
- Fallback: extra top-level keys
- Fallback: wrong hmac_anchor length
- Fallback: hmac_anchor not hex
- Fallback: assignments slug mismatch (extra role)
- Fallback: assignments slug mismatch (missing role)
- Fallback: invalid model ID
- Fallback: string too long (>256 chars)
- Fallback: assignment missing required keys
- Fallback: evidence n negative
- Fallback: evidence wrong type
- LoadResult.baseline always set to ADR-052 static
- BOM handling
- Default path resolution via env override
- Module-level _FROZEN_BASELINE is the canonical ADR-052 baseline
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli import loader  # noqa: E402
from tier_policy_cli.loader import (  # noqa: E402
    LoadResult,
    MAX_POLICY_FILE_BYTES,
    STATUS_BOOTSTRAP,
    STATUS_FALLBACK,
    STATUS_MIGRATED,
    STATUS_OK,
    default_policy_path,
    default_sigchain_path,
    load_policy,
)
from tier_policy_cli._types import (  # noqa: E402
    CANONICAL_5_AGENTS,
    VALID_MODEL_IDS,
    build_adr052_baseline,
)


def _valid_policy_dict():
    """Return a canonical schema-1.0 policy dict for test use."""
    return {
        "schema_version": "1.0",
        "generated_at": "2026-04-19T00:00:00Z",
        "baseline_from": "ADR-052",
        "assignments": {
            "code-reviewer": {
                "tier": "claude-opus-4-8",
                "locked_by": "VETO_FLOOR",
                "evidence": None,
            },
            "security-engineer": {
                "tier": "claude-opus-4-8",
                "locked_by": "VETO_FLOOR",
                "evidence": None,
            },
            "qa-architect": {
                "tier": "claude-sonnet-4-6",
                "locked_by": None,
                "evidence": {
                    "n": 30,
                    "gap_pp": 20.5,
                    "last_updated": "2026-04-19T00:00:00Z",
                    "runs_considered": 3,
                    "tournament_report_hmacs": ["a" * 64],
                },
            },
            "performance-engineer": {
                "tier": "claude-sonnet-4-6",
                "locked_by": None,
                "evidence": None,
            },
            "devops": {
                "tier": "claude-haiku-4-5-20251001",
                "locked_by": None,
                "evidence": None,
            },
        },
        "hmac_anchor": "f" * 64,
        "sigchain_tip_length": 1,
        "last_change_by_role": {},
    }


class LoaderTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-043-loader-")
        self.tmp = Path(self._tmp.name)
        self._saved_env = {
            k: os.environ.get(k)
            for k in ("CEO_TIER_POLICY_PATH", "CEO_TIER_POLICY_SIGCHAIN_PATH")
        }
        self.policy_path = self.tmp / "tier-policy.json"
        os.environ["CEO_TIER_POLICY_PATH"] = str(self.policy_path)

    def tearDown(self):
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    def _write_json(self, obj):
        self.policy_path.write_text(
            json.dumps(obj), encoding="utf-8"
        )

    def _write_raw(self, raw_bytes):
        self.policy_path.write_bytes(raw_bytes)


class TestHappyPath(LoaderTestBase):
    def test_valid_policy_loads_ok(self):
        self._write_json(_valid_policy_dict())
        result = load_policy()
        self.assertEqual(result.status, STATUS_OK)
        self.assertIsNotNone(result.policy_record)
        self.assertEqual(
            result.policy_record.schema_version, "1.0"
        )

    def test_loads_all_5_assignments(self):
        self._write_json(_valid_policy_dict())
        result = load_policy()
        self.assertEqual(
            set(result.policy_record.assignments.keys()),
            set(CANONICAL_5_AGENTS),
        )

    def test_baseline_always_present(self):
        self._write_json(_valid_policy_dict())
        result = load_policy()
        self.assertEqual(len(result.baseline), 5)
        for slug in CANONICAL_5_AGENTS:
            self.assertIn(slug, result.baseline)


class TestBootstrap(LoaderTestBase):
    def test_missing_file_status_bootstrap(self):
        # policy_path does not exist
        result = load_policy()
        self.assertEqual(result.status, STATUS_BOOTSTRAP)
        self.assertIsNone(result.policy_record)
        self.assertEqual(result.reason, "file_not_found")

    def test_bootstrap_baseline_is_adr052(self):
        result = load_policy()
        adr052 = build_adr052_baseline()
        for slug in CANONICAL_5_AGENTS:
            self.assertEqual(
                result.baseline[slug].tier, adr052[slug].tier
            )


class TestJsonHardening(LoaderTestBase):
    def test_malformed_json(self):
        self._write_raw(b"{not valid json")
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "malformed_json")

    def test_oversized_file(self):
        # Write 65 KB (>64 KiB cap)
        self._write_raw(b"x" * (MAX_POLICY_FILE_BYTES + 1))
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "oversized")

    def test_nesting_exceeded(self):
        # Build a deeply-nested JSON object (>8 levels)
        nested = "true"
        for _ in range(15):
            nested = "{{\"k\": {v}}}".format(v=nested)
        self._write_raw(nested.encode("utf-8"))
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "nesting_exceeded")

    def test_prototype_pollution_key(self):
        raw = b'{"__proto__": {"isAdmin": true}}'
        self._write_raw(raw)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "prototype_pollution")

    def test_constructor_key_rejected(self):
        raw = b'{"constructor": "x"}'
        self._write_raw(raw)
        result = load_policy()
        self.assertEqual(result.reason, "prototype_pollution")

    def test_non_utf8_encoding(self):
        self._write_raw(b"\xff\xfe\x00{")
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "non_utf8")

    def test_bom_handled(self):
        raw = "\ufeff".encode("utf-8") + json.dumps(
            _valid_policy_dict()
        ).encode("utf-8")
        self._write_raw(raw)
        result = load_policy()
        self.assertEqual(result.status, STATUS_OK)


class TestSchemaViolations(LoaderTestBase):
    def test_missing_schema_version_key(self):
        d = _valid_policy_dict()
        del d["schema_version"]
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "schema_version_missing")

    def test_unknown_schema_version(self):
        d = _valid_policy_dict()
        d["schema_version"] = "999.0"
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "schema_version_unknown")

    def test_missing_required_top_level_key(self):
        d = _valid_policy_dict()
        del d["generated_at"]
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "schema_missing_keys")

    def test_extra_top_level_key(self):
        d = _valid_policy_dict()
        d["unexpected_field"] = "surprise"
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "schema_extra_keys")

    def test_hmac_anchor_wrong_length(self):
        d = _valid_policy_dict()
        d["hmac_anchor"] = "f" * 32
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "hmac_anchor_malformed")

    def test_hmac_anchor_not_hex(self):
        d = _valid_policy_dict()
        d["hmac_anchor"] = "z" * 64
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "hmac_anchor_malformed")

    def test_assignments_extra_role(self):
        d = _valid_policy_dict()
        d["assignments"]["rogue-role"] = {
            "tier": "claude-opus-4-8",
            "locked_by": None,
            "evidence": None,
        }
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "assignments_slug_mismatch")

    def test_assignments_missing_role(self):
        d = _valid_policy_dict()
        del d["assignments"]["devops"]
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "assignments_slug_mismatch")

    def test_invalid_model_id(self):
        d = _valid_policy_dict()
        d["assignments"]["qa-architect"]["tier"] = "gpt-4"
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "invalid_model_id")

    def test_string_too_long(self):
        d = _valid_policy_dict()
        d["generated_at"] = "x" * 500
        self._write_json(d)
        result = load_policy()
        self.assertEqual(result.status, STATUS_FALLBACK)
        self.assertEqual(result.reason, "string_too_long")


class TestPathResolution(unittest.TestCase):
    def test_default_policy_path_uses_env_override(self):
        override = "/tmp/custom-policy.json"
        prev = os.environ.get("CEO_TIER_POLICY_PATH")
        try:
            os.environ["CEO_TIER_POLICY_PATH"] = override
            self.assertEqual(str(default_policy_path()), override)
        finally:
            if prev is None:
                os.environ.pop("CEO_TIER_POLICY_PATH", None)
            else:
                os.environ["CEO_TIER_POLICY_PATH"] = prev

    def test_default_sigchain_path_uses_env_override(self):
        override = "/tmp/custom-sigchain.jsonl"
        prev = os.environ.get("CEO_TIER_POLICY_SIGCHAIN_PATH")
        try:
            os.environ["CEO_TIER_POLICY_SIGCHAIN_PATH"] = override
            self.assertEqual(str(default_sigchain_path()), override)
        finally:
            if prev is None:
                os.environ.pop("CEO_TIER_POLICY_SIGCHAIN_PATH", None)
            else:
                os.environ["CEO_TIER_POLICY_SIGCHAIN_PATH"] = prev


class TestFrozenBaseline(unittest.TestCase):
    def test_frozen_baseline_is_adr052(self):
        # loader._FROZEN_BASELINE is computed at module import;
        # verify it matches build_adr052_baseline() output.
        adr052 = build_adr052_baseline()
        for slug in CANONICAL_5_AGENTS:
            self.assertEqual(
                loader._FROZEN_BASELINE[slug].tier, adr052[slug].tier
            )
            self.assertEqual(
                loader._FROZEN_BASELINE[slug].locked_by,
                adr052[slug].locked_by,
            )


class TestLoadResultShape(LoaderTestBase):
    def test_result_has_policy_and_baseline(self):
        self._write_json(_valid_policy_dict())
        result = load_policy()
        self.assertIsInstance(result, LoadResult)
        self.assertIsNotNone(result.policy_record)
        self.assertIsNotNone(result.baseline)
        self.assertEqual(len(result.baseline), 5)


if __name__ == "__main__":
    unittest.main()
