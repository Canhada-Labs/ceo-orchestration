"""Smoke tests for .claude/scripts/red-team-eval.py.

PLAN-013 Phase D.8 PARTIAL. Full +40 property-based conformance
tests are DEFERRED — see sibling `DEFERRED.md`. This file ships
framework-self-test smoke coverage: loader, CLI, idempotent issue
logic, flake budget, fork-PR guard.

PLAN-013 consensus §S11: `TestEnvContext` mandatory for env
isolation. Every test subclasses it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

_HOOK_LIB = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOK_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOK_LIB))

from _lib.testing import TestEnvContext  # noqa: E402

_SCRIPT = Path(__file__).resolve().parent.parent / "red-team-eval.py"

spec = importlib.util.spec_from_file_location("red_team_eval", str(_SCRIPT))
assert spec is not None and spec.loader is not None
rte = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rte
spec.loader.exec_module(rte)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_fixture(
    dir_path: Path,
    fixture_id: str,
    target: str,
    payload: str,
    expected: str = "MUST_BLOCK",
    category: str = "smoke-test",
) -> Path:
    """Write a minimal fixture file for tests."""
    dir_path.mkdir(parents=True, exist_ok=True)
    doc = {
        "id": fixture_id,
        "target": target,
        "category": category,
        "input": payload,
        "expected_behavior": expected,
        "reference": "test-only fixture",
        "severity": "LOW",
    }
    path = dir_path / f"{fixture_id}.jsonl"
    path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test 1 — Loader: load_fixtures + schema validation
# ---------------------------------------------------------------------------


class TestFixtureLoader(TestEnvContext):

    def test_load_valid_fixtures(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        _write_fixture(
            fixture_dir, "SMK-001", "skill_patch_sentinel",
            "\u202etext\u202c",  # bidi payload
        )
        _write_fixture(
            fixture_dir, "SMK-002", "output_safety_evasion",
            "API_TOKEN=secret_XXXXXXXX",
            expected="MUST_SANITIZE",
        )
        fixtures = rte.load_fixtures(fixture_dir)
        self.assertEqual(len(fixtures), 2)
        ids = sorted(f["id"] for f in fixtures)
        self.assertEqual(ids, ["SMK-001", "SMK-002"])

    def test_load_rejects_missing_fields(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        fixture_dir.mkdir(parents=True)
        bad_path = fixture_dir / "BAD-001.jsonl"
        bad_path.write_text(
            json.dumps({"id": "BAD-001"}) + "\n", encoding="utf-8"
        )
        with self.assertRaises(ValueError) as ctx:
            rte.load_fixtures(fixture_dir)
        self.assertIn("missing fields", str(ctx.exception))

    def test_load_rejects_unknown_target(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        fixture_dir.mkdir(parents=True)
        (fixture_dir / "BAD-002.jsonl").write_text(
            json.dumps({
                "id": "BAD-002",
                "target": "not_a_real_target",
                "category": "invalid",
                "input": "x",
                "expected_behavior": "MUST_BLOCK",
                "reference": "none",
            }) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as ctx:
            rte.load_fixtures(fixture_dir)
        self.assertIn("unknown target", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test 2 — Evaluator: adapters return sane shapes
# ---------------------------------------------------------------------------


class TestEvaluator(TestEnvContext):

    def test_evaluate_bidi_payload_passes(self):
        fixture = {
            "id": "EVAL-001",
            "target": "skill_patch_sentinel",
            "category": "unicode-bidi",
            "input": "text with \u202e override",
            "expected_behavior": "MUST_BLOCK",
            "reference": "test",
        }
        result = rte.evaluate_fixture(fixture)
        self.assertEqual(result["outcome"], "pass")
        self.assertTrue(result["actual"].startswith("BLOCKED:"))

    def test_evaluate_mcp_handler_is_deferred(self):
        fixture = {
            "id": "EVAL-002",
            "target": "mcp_handler",
            "category": "mcp",
            "input": "probe",
            "expected_behavior": "MUST_BLOCK",
            "reference": "test",
        }
        result = rte.evaluate_fixture(fixture)
        self.assertEqual(result["outcome"], "skip_deferred")
        self.assertTrue(result["actual"].startswith("DEFERRED:"))

    def test_evaluate_clean_payload_fails(self):
        # A fixture claiming MUST_BLOCK on a payload that our simulated
        # defense wouldn't catch — verifies "fail" path.
        fixture = {
            "id": "EVAL-003",
            "target": "skill_patch_sentinel",
            "category": "noop",
            "input": "harmless content",
            "expected_behavior": "MUST_BLOCK",
            "reference": "test",
        }
        result = rte.evaluate_fixture(fixture)
        self.assertEqual(result["outcome"], "fail")


# ---------------------------------------------------------------------------
# Test 3 — Byte-identity ledger loading + drift detection
# ---------------------------------------------------------------------------


class TestByteIdentity(TestEnvContext):

    def test_ledger_detects_drift(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        corpus_root = self.project_dir / "corpus"
        fx = _write_fixture(
            fixture_dir, "SMK-100", "audit_log_tamper", "x",
            expected="MUST_EMIT_AUDIT",
        )
        # Ledger has a wrong hash → drift
        ledger = corpus_root / ".byte-identity-check.txt"
        ledger.write_text(
            "0000000000000000000000000000000000000000000000000000000000000000  "
            "synthetic/SMK-100.jsonl\n",
            encoding="utf-8",
        )
        loaded = rte.load_byte_identity_ledger(ledger)
        drifts = rte.check_byte_identity(corpus_root, loaded)
        self.assertEqual(len(drifts), 1)
        self.assertEqual(drifts[0][0], "synthetic/SMK-100.jsonl")
        self.assertNotEqual(drifts[0][1], drifts[0][2])

    def test_ledger_accepts_correct_hash(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        corpus_root = self.project_dir / "corpus"
        fx = _write_fixture(
            fixture_dir, "SMK-101", "audit_log_tamper", "x",
            expected="MUST_EMIT_AUDIT",
        )
        sha = hashlib.sha256(fx.read_bytes()).hexdigest()
        ledger = corpus_root / ".byte-identity-check.txt"
        ledger.write_text(
            f"{sha}  synthetic/SMK-101.jsonl\n",
            encoding="utf-8",
        )
        loaded = rte.load_byte_identity_ledger(ledger)
        drifts = rte.check_byte_identity(corpus_root, loaded)
        self.assertEqual(drifts, [])


# ---------------------------------------------------------------------------
# Test 4 — Idempotent issue payload (hash-based)
# ---------------------------------------------------------------------------


class TestIssueIdempotence(TestEnvContext):

    def test_same_fingerprint_same_title(self):
        result = {
            "id": "SMK-200",
            "target": "sandbox_escape",
            "expected": "MUST_BLOCK",
            "actual": "ALLOWED",
            "fingerprint": "abcd1234" * 8,
            "source_file": "SMK-200.jsonl",
        }
        payload_a = rte.issue_payload_for_failure(
            result, "Flake: {fixture_id} ({fingerprint})", ["red-team-eval"],
        )
        payload_b = rte.issue_payload_for_failure(
            result, "Flake: {fixture_id} ({fingerprint})", ["red-team-eval"],
        )
        self.assertEqual(payload_a["title"], payload_b["title"])
        self.assertIn("SMK-200", payload_a["title"])

    def test_different_fingerprint_different_title(self):
        result_a = {
            "id": "SMK-201",
            "target": "sandbox_escape",
            "expected": "MUST_BLOCK",
            "actual": "ALLOWED",
            "fingerprint": "aaaaaaaa",
            "source_file": "SMK-201.jsonl",
        }
        result_b = dict(result_a, fingerprint="bbbbbbbb")
        a = rte.issue_payload_for_failure(
            result_a, "F: {fixture_id} ({fingerprint})", [],
        )
        b = rte.issue_payload_for_failure(
            result_b, "F: {fixture_id} ({fingerprint})", [],
        )
        self.assertNotEqual(a["title"], b["title"])


# ---------------------------------------------------------------------------
# Test 5 — Flake budget quarantines after 2+ failures
# ---------------------------------------------------------------------------


class TestFlakeBudget(TestEnvContext):

    def _seed_ledger(self) -> Path:
        path = self.project_dir / "flake.yaml"
        path.write_text(
            "schema_version: 1\n"
            "updated_at: \"2026-04-16\"\n"
            "policy:\n"
            "  allowance_per_fixture: 1\n"
            "  window_days: 7\n"
            "  quarantine_threshold: 2\n"
            "  reset_after_clean_days: 7\n"
            "ledger:\n"
            "  entries: []\n"
            "quarantined:\n"
            "  entries: []\n",
            encoding="utf-8",
        )
        return path

    def test_first_failure_does_not_quarantine(self):
        path = self._seed_ledger()
        failure = {
            "id": "SMK-300",
            "target": "audit_log_tamper",
            "expected": "MUST_EMIT_AUDIT",
            "actual": "ALLOWED",
            "fingerprint": "a" * 16,
        }
        newly_q, skipped = rte.check_and_update_flake_budget(
            path, [failure], dry_run=True,
        )
        self.assertEqual(newly_q, [])
        self.assertEqual(skipped, [])

    def test_second_failure_quarantines(self):
        path = self._seed_ledger()
        failure = {
            "id": "SMK-301",
            "target": "audit_log_tamper",
            "expected": "MUST_EMIT_AUDIT",
            "actual": "ALLOWED",
            "fingerprint": "b" * 16,
        }
        # First call persists one entry.
        rte.check_and_update_flake_budget(path, [failure], dry_run=False)
        # Second call should cross the threshold.
        newly_q, skipped = rte.check_and_update_flake_budget(
            path, [failure], dry_run=False,
        )
        self.assertIn("SMK-301", newly_q)

    def test_quarantined_fixture_is_skipped_on_next_run(self):
        path = self._seed_ledger()
        failure = {
            "id": "SMK-302",
            "target": "audit_log_tamper",
            "expected": "MUST_EMIT_AUDIT",
            "actual": "ALLOWED",
            "fingerprint": "c" * 16,
        }
        # Trigger quarantine
        rte.check_and_update_flake_budget(path, [failure], dry_run=False)
        rte.check_and_update_flake_budget(path, [failure], dry_run=False)
        # Now a fresh call with no new failures should report skipped set
        _, skipped = rte.check_and_update_flake_budget(path, [], dry_run=True)
        self.assertIn("SMK-302", skipped)


# ---------------------------------------------------------------------------
# Test 6 — Fork-PR guard logic
# ---------------------------------------------------------------------------


class TestForkPRGuard(TestEnvContext):

    def test_non_pr_events_are_always_safe(self):
        self.assertTrue(rte.fork_pr_guard("schedule", "", ""))
        self.assertTrue(rte.fork_pr_guard("push", "", ""))
        self.assertTrue(rte.fork_pr_guard("workflow_dispatch", "", ""))

    def test_same_repo_pr_is_safe(self):
        self.assertTrue(rte.fork_pr_guard(
            "pull_request", "owner/repo", "owner/repo"
        ))

    def test_fork_pr_is_unsafe(self):
        self.assertFalse(rte.fork_pr_guard(
            "pull_request", "attacker/fork", "owner/repo"
        ))


# ---------------------------------------------------------------------------
# Test 7 — CLI dry-run produces expected summary
# ---------------------------------------------------------------------------


class TestDryRunCLI(TestEnvContext):

    def test_dry_run_counts_fixtures(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        _write_fixture(
            fixture_dir, "SMK-400", "skill_patch_sentinel",
            "\u202e bidi",
        )
        _write_fixture(
            fixture_dir, "SMK-401", "output_safety_evasion",
            "API_TOKEN=secret",
            expected="MUST_SANITIZE",
        )
        # Capture stdout via output_file
        out_file = self.project_dir / "result.json"
        exit_code = rte.main([
            "--fixture-dir", str(fixture_dir),
            "--output", "json",
            "--output-file", str(out_file),
            "--quarantine-ledger", str(self.project_dir / "does-not-exist.yaml"),
            "--dry-run",
        ])
        self.assertIn(exit_code, (0, 1))
        data = json.loads(out_file.read_text())
        self.assertEqual(data["summary"]["total"], 2)

    def test_kill_switch_short_circuits(self):
        exit_code = rte.main([
            "--fixture-dir", str(self.project_dir),
            "--kill-switch", "1",
        ])
        self.assertEqual(exit_code, 0)

    def test_target_filter_restricts_set(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        _write_fixture(
            fixture_dir, "SMK-500", "skill_patch_sentinel",
            "\u202e bidi",
        )
        _write_fixture(
            fixture_dir, "SMK-501", "npm_tamper",
            "install ceo-orchestraton",
            expected="MUST_BLOCK",
        )
        out_file = self.project_dir / "filtered.json"
        exit_code = rte.main([
            "--fixture-dir", str(fixture_dir),
            "--target", "skill_patch_sentinel",
            "--output", "json",
            "--output-file", str(out_file),
            "--quarantine-ledger", str(self.project_dir / "nope.yaml"),
            "--dry-run",
        ])
        self.assertIn(exit_code, (0, 1))
        data = json.loads(out_file.read_text())
        self.assertEqual(data["summary"]["total"], 1)


# ---------------------------------------------------------------------------
# Test 8 — Minimal YAML parser round-trip (flake-budget format)
# ---------------------------------------------------------------------------


class TestMinimalYAML(TestEnvContext):

    def test_parse_and_dump_roundtrip(self):
        src = (
            "schema_version: 1\n"
            "policy:\n"
            "  allowance_per_fixture: 1\n"
            "  window_days: 7\n"
            "ledger:\n"
            "  entries: []\n"
        )
        parsed = rte._parse_minimal_yaml(src)
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["policy"]["window_days"], 7)
        self.assertEqual(parsed["ledger"]["entries"], [])

    def test_parse_list_of_mappings(self):
        src = (
            "ledger:\n"
            "  entries:\n"
            "    - fixture_id: A\n"
            "      ts: \"2026-04-16T00:00:00+00:00\"\n"
            "    - fixture_id: B\n"
            "      ts: \"2026-04-16T01:00:00+00:00\"\n"
        )
        parsed = rte._parse_minimal_yaml(src)
        entries = parsed["ledger"]["entries"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["fixture_id"], "A")
        self.assertEqual(entries[1]["fixture_id"], "B")


# ---------------------------------------------------------------------------
# Test 9 — JUnit XML output shape
# ---------------------------------------------------------------------------


class TestJUnitOutput(TestEnvContext):

    def test_junit_contains_testcase_per_result(self):
        results = [
            {
                "id": "U-001", "target": "skill_patch_sentinel",
                "expected": "MUST_BLOCK", "actual": "BLOCKED:unicode-bidi",
                "outcome": "pass", "fingerprint": "a" * 16,
                "source_file": "U-001.jsonl",
            },
            {
                "id": "U-002", "target": "mcp_handler",
                "expected": "MUST_BLOCK", "actual": "DEFERRED:phase-a-pending",
                "outcome": "skip_deferred", "fingerprint": "b" * 16,
                "source_file": "U-002.jsonl",
            },
            {
                "id": "U-003", "target": "audit_log_tamper",
                "expected": "MUST_EMIT_AUDIT", "actual": "ALLOWED",
                "outcome": "fail", "fingerprint": "c" * 16,
                "source_file": "U-003.jsonl",
            },
        ]
        xml = rte.format_junit(results)
        self.assertIn("tests=\"3\"", xml)
        self.assertIn("failures=\"1\"", xml)
        self.assertIn("skipped=\"1\"", xml)
        self.assertIn("name=\"U-001\"", xml)
        self.assertIn("name=\"U-002\"", xml)
        self.assertIn("name=\"U-003\"", xml)


# ---------------------------------------------------------------------------
# Test 10 — Behavior matcher handles all expected codes
# ---------------------------------------------------------------------------


class TestBehaviorMatcher(TestEnvContext):

    def test_must_block_matches_blocked(self):
        self.assertTrue(rte._behavior_matches("MUST_BLOCK", "BLOCKED:x"))

    def test_must_sanitize_matches_sanitized(self):
        self.assertTrue(rte._behavior_matches("MUST_SANITIZE", "SANITIZED:y"))

    def test_must_reject_accepts_blocked_or_rejected(self):
        self.assertTrue(rte._behavior_matches("MUST_REJECT", "BLOCKED:z"))
        self.assertTrue(rte._behavior_matches("MUST_REJECT", "REJECTED:z"))

    def test_deferred_never_matches(self):
        self.assertFalse(rte._behavior_matches(
            "MUST_BLOCK", "DEFERRED:phase-a-pending"))

    def test_allowed_never_matches_block(self):
        self.assertFalse(rte._behavior_matches("MUST_BLOCK", "ALLOWED"))


# ---------------------------------------------------------------------------
# Test 11 — Quarantine-scope: already-quarantined fixtures skipped
# ---------------------------------------------------------------------------


class TestQuarantineSkip(TestEnvContext):

    def test_cli_skips_quarantined_fixtures(self):
        fixture_dir = self.project_dir / "corpus" / "synthetic"
        _write_fixture(
            fixture_dir, "SMK-Q1", "skill_patch_sentinel",
            "\u202e bidi",
        )
        # Create ledger with SMK-Q1 already quarantined.
        ledger = self.project_dir / "flake.yaml"
        ledger.write_text(
            "schema_version: 1\n"
            "policy:\n"
            "  allowance_per_fixture: 1\n"
            "  window_days: 7\n"
            "  quarantine_threshold: 2\n"
            "  reset_after_clean_days: 7\n"
            "ledger:\n"
            "  entries: []\n"
            "quarantined:\n"
            "  entries:\n"
            "    - fixture_id: SMK-Q1\n"
            "      since: \"2026-04-01\"\n"
            "      reason: \"pre-seeded for test\"\n",
            encoding="utf-8",
        )
        out_file = self.project_dir / "result.json"
        rte.main([
            "--fixture-dir", str(fixture_dir),
            "--output", "json",
            "--output-file", str(out_file),
            "--quarantine-ledger", str(ledger),
            "--dry-run",
        ])
        data = json.loads(out_file.read_text())
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["outcome"], "skip_deferred")
        self.assertTrue(
            data["results"][0]["actual"].startswith("QUARANTINED:")
        )


if __name__ == "__main__":
    unittest.main()
