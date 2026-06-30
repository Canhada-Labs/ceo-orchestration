"""PLAN-100 Wave B — staged tests for per-class block-mode.

Copies to `.claude/hooks/_lib/tests/test_confidence_gate_class_block.py`
during v1.34.0 ceremony Phase A1.

Covers PLAN-100 AC2/AC8/AC9/AC10/AC11 + ADR-019-AMEND-1 §3 (per-class
kill-switch), §4 (initial tier assignment), §5 (legacy flag interaction),
§9 (failure modes).

Stdlib only. pytest-compatible. Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

# Make hook module importable
_HOOKS = Path(__file__).resolve().parents[2] if "/_lib/tests/" in str(Path(__file__)) else Path(__file__).resolve().parents[3] / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

# Import target module — late import after sys.path tweak
import importlib  # noqa: E402

_ccg = importlib.import_module("check_confidence_gate")
_contract = importlib.import_module("_lib.contract")


def _build_payload(claims, *, exit_code=1, fail_count=None):
    """Build a synthetic confidence_gate JSON payload."""
    fail = fail_count if fail_count is not None else sum(
        1 for c in claims if c.get("verdict") == "fail"
    )
    return {
        "outcome": "verified",
        "exit_code": exit_code,
        "claim_count": len(claims),
        "raw_claim_count": len(claims),
        "truncated": False,
        "pass_count": len(claims) - fail,
        "fail_count": fail,
        "claims": claims,
    }


def _claim(kind, verdict="fail"):
    return {
        "claim_id": f"{kind}:abc123def456",
        "claim_type": kind,
        "verifier_kind": kind,
        "verdict": verdict,
        "was_false_positive": False,
        "kind_supported": True,
        "severity": "info",
        "payload_hash": "abc123def456",
        "line_num": 1,
    }


class TestLoadClassTiers(unittest.TestCase):
    """AC9 — tier-config load + fail-OPEN on missing/malformed."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_missing_config_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tiers = _ccg._load_class_tiers(root)
            self.assertEqual(tiers, {})

    def test_malformed_json_returns_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude" / "data").mkdir(parents=True)
            (root / ".claude" / "data" / "confidence-gate-class-tiers.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            tiers = _ccg._load_class_tiers(root)
            self.assertEqual(tiers, {})

    def test_valid_config_returns_tier_map(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude" / "data").mkdir(parents=True)
            cfg = {"tiers": {"sha_exists": "HIGH_CONFIDENCE_BLOCK",
                             "path_exists": "MED_CONFIDENCE_ADVISORY"}}
            (root / ".claude" / "data" / "confidence-gate-class-tiers.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )
            tiers = _ccg._load_class_tiers(root)
            self.assertEqual(tiers, {
                "sha_exists": "HIGH_CONFIDENCE_BLOCK",
                "path_exists": "MED_CONFIDENCE_ADVISORY",
            })

    def test_unknown_tier_value_filtered_out(self):
        """Defense-in-depth: only valid tier values pass through."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude" / "data").mkdir(parents=True)
            cfg = {"tiers": {"sha_exists": "HIGH_CONFIDENCE_BLOCK",
                             "weird_tier": "TYPO_NOT_A_TIER"}}
            (root / ".claude" / "data" / "confidence-gate-class-tiers.json").write_text(
                json.dumps(cfg), encoding="utf-8"
            )
            tiers = _ccg._load_class_tiers(root)
            self.assertEqual(tiers, {"sha_exists": "HIGH_CONFIDENCE_BLOCK"})


class TestKillSwitch(unittest.TestCase):
    """AC2 — per-class kill-switch EXACT-match discipline."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_exact_match_kills_specific_class(self):
        os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = "0"
        self.assertTrue(_ccg._is_class_killed("sha_exists"))

    def test_other_class_not_killed_by_specific_env(self):
        os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = "0"
        self.assertFalse(_ccg._is_class_killed("path_exists"))

    def test_partial_match_does_not_kill(self):
        """CEO_CONFIDENCE_BLOCK=0 (no _<CLASS> suffix) MUST be IGNORED."""
        os.environ["CEO_CONFIDENCE_BLOCK"] = "0"
        self.assertFalse(_ccg._is_class_killed("sha_exists"))
        self.assertFalse(_ccg._is_class_killed("path_exists"))

    def test_falsy_variants(self):
        for val in ("0", "false", "no", "off"):
            os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = val
            self.assertTrue(_ccg._is_class_killed("sha_exists"))

    def test_truthy_values_dont_kill(self):
        for val in ("1", "true", "yes", "on"):
            os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = val
            self.assertFalse(_ccg._is_class_killed("sha_exists"))


class TestClassifyBlockingClaims(unittest.TestCase):
    """Helper that lists HIGH_CONFIDENCE_BLOCK classes with failed verdicts."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_high_block_failure_listed(self):
        payload = _build_payload([_claim("sha_exists", "fail")])
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers),
                         ["sha_exists"])

    def test_med_adv_failure_not_listed(self):
        payload = _build_payload([_claim("path_exists", "fail")])
        tiers = {"path_exists": "MED_CONFIDENCE_ADVISORY"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers), [])

    def test_pass_verdict_not_listed(self):
        payload = _build_payload([_claim("sha_exists", "pass")], exit_code=0)
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers), [])

    def test_killed_class_not_listed(self):
        os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = "0"
        payload = _build_payload([_claim("sha_exists", "fail")])
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers), [])

    def test_dedup_sorted(self):
        payload = _build_payload([
            _claim("sha_exists", "fail"),
            _claim("sha_exists", "fail"),
            _claim("foo_kind", "fail"),
        ])
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK",
                 "foo_kind": "HIGH_CONFIDENCE_BLOCK"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers),
                         ["foo_kind", "sha_exists"])

    def test_unknown_class_skipped(self):
        payload = _build_payload([_claim("unknown_kind", "fail")])
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK"}
        self.assertEqual(_ccg._classify_blocking_claims(payload, tiers), [])


class TestDecideEnforce(unittest.TestCase):
    """AC8 — decide() honors enforce + class_tiers."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_bypass_always_allows(self):
        payload = _build_payload([_claim("sha_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=True,
                        class_tiers={"sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertTrue(d.allow)

    def test_no_enforce_allows(self):
        payload = _build_payload([_claim("sha_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=False, bypass=False,
                        class_tiers={"sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertTrue(d.allow)

    def test_enforce_blocks_high_class(self):
        payload = _build_payload([_claim("sha_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertFalse(d.allow)
        self.assertIn("sha_exists", d.reason)

    def test_enforce_allows_med_class(self):
        payload = _build_payload([_claim("path_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"path_exists": "MED_CONFIDENCE_ADVISORY"})
        self.assertTrue(d.allow)

    def test_enforce_with_no_tiers_fails_open(self):
        """AC9 — missing tier config = fail-OPEN, not legacy broad enforce."""
        payload = _build_payload([_claim("sha_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={})
        self.assertTrue(d.allow)

    def test_pass_exit_code_allows(self):
        payload = _build_payload([], exit_code=0)
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertTrue(d.allow)

    def test_timeout_allows(self):
        payload = {"outcome": "timeout", "exit_code": None}
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertTrue(d.allow)


class TestLegacyFlagInteraction(unittest.TestCase):
    """AC10 — CEO_CONFIDENCE_ENFORCE=1 applies HIGH-only post-amendment."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_legacy_enforce_blocks_high_class_only(self):
        """A test_passes failure under legacy flag should NOT block when
        test_passes is LOW_CONFIDENCE_ADVISORY."""
        payload = _build_payload([_claim("test_passes", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"test_passes": "LOW_CONFIDENCE_ADVISORY",
                                     "sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertTrue(d.allow)

    def test_legacy_enforce_blocks_sha_exists(self):
        payload = _build_payload([_claim("sha_exists", "fail")])
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers={"test_passes": "LOW_CONFIDENCE_ADVISORY",
                                     "sha_exists": "HIGH_CONFIDENCE_BLOCK"})
        self.assertFalse(d.allow)


class TestEnvBleed(unittest.TestCase):
    """AC8 (a) — env isolation via TestEnvContext-like discipline."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    def test_class_kill_does_not_bleed_to_other_class(self):
        os.environ["CEO_CONFIDENCE_BLOCK_SHA_EXISTS"] = "0"
        payload = _build_payload([_claim("sha_exists", "fail"),
                                  _claim("path_exists_alt", "fail")])
        tiers = {"sha_exists": "HIGH_CONFIDENCE_BLOCK",
                 "path_exists_alt": "HIGH_CONFIDENCE_BLOCK"}
        d = _ccg.decide(payload=payload, enforce=True, bypass=False,
                        class_tiers=tiers)
        # sha_exists killed; path_exists_alt still triggers block
        self.assertFalse(d.allow)
        self.assertIn("path_exists_alt", d.reason)
        self.assertNotIn("sha_exists", d.reason)


if __name__ == "__main__":
    unittest.main()
