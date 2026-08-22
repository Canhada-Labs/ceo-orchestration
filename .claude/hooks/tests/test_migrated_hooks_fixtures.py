"""Fixture-corpus tests for migrated hook policies (PLAN-014 Phase A.4).

Loads each ``.fixtures.jsonl`` under ``.claude/policies/fixtures/``, pushes
the pre-enriched event through the policy engine, and asserts that both
the ``decision`` and ``reason`` outputs match the recorded expectation.

This is the semantic half of the drift guard (SPEC §6.2). A semantically
equivalent YAML rewrite MAY change the canonical hash, but MUST NOT
change any fixture outcome. When a new rule is added, add fixtures
BEFORE the rule and watch them fail in CI.

Covers ≥60 assertions (30 bash + 30 plan-edit minimum, actual 32 + 31 =
63 as of 2026-04-17).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.policy import load  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


_REPO_ROOT = Path(__file__).resolve().parents[3]
_POLICIES_DIR = _REPO_ROOT / ".claude" / "policies"
_FIXTURES_DIR = _POLICIES_DIR / "fixtures"


def _load_fixtures(slug: str):
    path = _FIXTURES_DIR / f"{slug}.fixtures.jsonl"
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            yield i, json.loads(line)


class TestBashSafetyFixtures(TestEnvContext):
    """Each fixture is a separate assertion — mismatch fails the test.

    PLAN-182 W2 (S321): `policy.decide()` emits `policy_evaluated` /
    `policy_denied` per fixture, so an unisolated run writes signed links
    into the LIVE HMAC chain — measured at 156 processes x 124 events
    (82 fixtures + 42 expected-block) = 19,344 non-attributable events,
    99.5% of the post-W1 non-attributable flow. The policy load moved from
    `setUpClass` to `setUp` on purpose: TestEnvContext isolates per
    INSTANCE, so anything left in `setUpClass` runs before the sandbox
    exists. Positive control: with HOME redirected, a pre-cure run creates
    `audit-log.lock` + `state/audit-pending.<pid>.journal` under it.
    """

    def setUp(self):
        super().setUp()
        self.policy = load(_POLICIES_DIR / "bash-safety.policy.yaml")

    def test_all_fixtures_match_expected(self):
        count = 0
        failures = []
        for line_no, fixture in _load_fixtures("bash-safety"):
            count += 1
            got = self.policy.decide(fixture["input"])
            exp_dec = fixture["expected_decision"]
            exp_rsn = fixture["expected_reason"]
            got_dec = got.get("decision")
            got_rsn = got.get("reason")
            if got_dec != exp_dec or got_rsn != exp_rsn:
                cmd = fixture["input"].get("tool_input", {}).get("command", "")
                failures.append(
                    f"line {line_no}: cmd={cmd[:60]!r} got=({got_dec},{got_rsn}) "
                    f"expected=({exp_dec},{exp_rsn})"
                )
        self.assertGreaterEqual(count, 30,
                                f"bash-safety fixtures must have ≥30 entries, got {count}")
        self.assertEqual(failures, [], f"{len(failures)} fixture mismatches:\n" +
                         "\n".join(failures))


class TestPlanEditFixtures(TestEnvContext):

    def setUp(self):
        super().setUp()
        self.policy = load(_POLICIES_DIR / "plan-edit.policy.yaml")

    def test_all_fixtures_match_expected(self):
        count = 0
        failures = []
        for line_no, fixture in _load_fixtures("plan-edit"):
            count += 1
            got = self.policy.decide(fixture["input"])
            exp_dec = fixture["expected_decision"]
            exp_rsn = fixture["expected_reason"]
            got_dec = got.get("decision")
            got_rsn = got.get("reason")
            if got_dec != exp_dec or got_rsn != exp_rsn:
                fp = fixture["input"].get("tool_input", {}).get("file_path", "")
                failures.append(
                    f"line {line_no}: path={fp!r} got=({got_dec},{got_rsn}) "
                    f"expected=({exp_dec},{exp_rsn})"
                )
        self.assertGreaterEqual(count, 30,
                                f"plan-edit fixtures must have ≥30 entries, got {count}")
        self.assertEqual(failures, [], f"{len(failures)} fixture mismatches:\n" +
                         "\n".join(failures))


class TestDriftManifestMatchesComputedHashes(TestEnvContext):
    """The pinned canonical hashes in .drift-manifest.json must match the
    live engine output — otherwise the manifest is stale."""

    def test_manifest_hashes_match(self):
        manifest_path = _POLICIES_DIR / ".drift-manifest.json"
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        for slug, entry in manifest["policies"].items():
            policy_path = _POLICIES_DIR / f"{slug}.policy.yaml"
            policy = load(policy_path)
            self.assertEqual(
                entry["sha256"], policy.canonical_hash,
                f"drift manifest sha256 for {slug!r} is stale. "
                f"Manifest says {entry['sha256'][:12]}..., "
                f"engine computes {policy.canonical_hash[:12]}... "
                f"Re-pin after intentional semantic change."
            )


if __name__ == "__main__":
    unittest.main()
