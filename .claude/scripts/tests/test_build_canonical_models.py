"""Tests for build-canonical-models.py — PLAN-133 B1.

Stdlib-only unittest. Imports the script via importlib (its filename has a dash
→ not importable as a normal module). Covers: provenance checksum fail-CLOSED,
seed-sentinel fail-open, staleness advisory, reconcile-flagging (never
overwrites), S220 unknown=0 fallback, default-OFF env flag, and the cache
multiplier pins (5m=1.25x / 1h=2.0x / read=0.1x).

Run::

    python3 -m unittest .claude.scripts.tests.test_build_canonical_models -v
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

_THIS_DIR = Path(__file__).resolve().parent
_SCRIPT_PATH = _THIS_DIR.parent / "build-canonical-models.py"
_DATA_PATH = _THIS_DIR.parent.parent / "data" / "canonical_models.json"
_COST_TABLE_PATH = _THIS_DIR.parent / "cost-table.yaml"

# _lib is at .claude/hooks/_lib relative to repo root; import TestEnvContext so
# these tests get per-test env isolation (env-hygiene mandate) instead of bare
# unittest.TestCase.
_REPO_ROOT = _THIS_DIR.parent.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("build_canonical_models", _SCRIPT_PATH)
bcm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bcm)  # type: ignore[union-attr]


def _sample_models():
    return {
        "claude-opus-4-8": {
            "input_per_mtok": 5.0,
            "cache_write_5m_per_mtok": 6.25,
            "cache_write_1h_per_mtok": 10.0,
            "cache_read_per_mtok": 0.5,
            "output_per_mtok": 25.0,
            "tier": "opus",
            "tier_class": "opus_new",
        },
    }


def _sample_data(models=None, sha=None, valid_until="2099-01-01"):
    models = models if models is not None else _sample_models()
    return {
        "schema_version": "1.0",
        "provenance": {
            "source_url": "https://models.dev/api.json",
            "fetched_at": "2026-05-29",
            "sha256": sha if sha is not None else bcm._PENDING_SENTINEL,
        },
        "staleness": {"valid_until": valid_until, "refresh_cadence_days": 90,
                      "advisory_only": True},
        "unknown_model_fallback": {
            "input_per_mtok": 0.0, "cache_write_5m_per_mtok": 0.0,
            "cache_write_1h_per_mtok": 0.0, "cache_read_per_mtok": 0.0,
            "output_per_mtok": 0.0,
        },
        "cache_multipliers": {"cache_write_5m": 1.25, "cache_write_1h": 2.0,
                              "cache_read": 0.1},
        "models": models,
    }


class TestShippedDataFile(TestEnvContext):
    def test_shipped_file_loads(self):
        data = bcm.load_canonical_models(_DATA_PATH)
        self.assertIn("models", data)
        self.assertIn("claude-opus-4-8", data["models"])

    def test_shipped_file_verify_checksum(self):
        # Post-OQ1 (Owner fetch 2026-06-10): the shipped file carries a REAL
        # provenance checksum -> verify must pass fail-CLOSED semantics.
        # (The PENDING fail-open path stays covered by the synthetic-data tests.)
        data = bcm.load_canonical_models(_DATA_PATH)
        ok, msg = bcm.verify_checksum(data)
        self.assertTrue(ok)
        self.assertNotIn("pending", msg.lower())
        self.assertIn("ok", msg.lower())

    def test_shipped_file_has_unknown_fallback_all_zero(self):
        data = bcm.load_canonical_models(_DATA_PATH)
        fb = data["unknown_model_fallback"]
        for k in ("input_per_mtok", "output_per_mtok", "cache_read_per_mtok"):
            self.assertEqual(fb[k], 0.0)


class TestChecksumFailClosed(TestEnvContext):
    def test_matching_checksum_ok(self):
        models = _sample_models()
        sha = bcm.compute_models_sha256(models)
        data = _sample_data(models=models, sha=sha)
        ok, msg = bcm.verify_checksum(data)
        self.assertTrue(ok)
        self.assertIn("checksum OK", msg)

    def test_tampered_models_fail_closed(self):
        models = _sample_models()
        sha = bcm.compute_models_sha256(models)
        data = _sample_data(models=models, sha=sha)
        # Tamper a rate WITHOUT re-stamping the sha → must fail-CLOSED.
        data["models"]["claude-opus-4-8"]["input_per_mtok"] = 0.01
        ok, msg = bcm.verify_checksum(data)
        self.assertFalse(ok)
        self.assertIn("MISMATCH", msg)

    def test_seed_sentinel_is_fail_open(self):
        data = _sample_data(sha=bcm._PENDING_SENTINEL)
        ok, _ = bcm.verify_checksum(data)
        self.assertTrue(ok)

    def test_checksum_byte_stable_across_key_order(self):
        a = {"z": {"input_per_mtok": 1.0}, "a": {"input_per_mtok": 2.0}}
        b = {"a": {"input_per_mtok": 2.0}, "z": {"input_per_mtok": 1.0}}
        self.assertEqual(bcm.compute_models_sha256(a), bcm.compute_models_sha256(b))


class TestStaleness(TestEnvContext):
    def test_fresh(self):
        data = _sample_data(valid_until="2099-01-01")
        stale, msg = bcm.check_staleness(data, today=date(2026, 6, 8))
        self.assertFalse(stale)
        self.assertEqual(msg, "")

    def test_stale(self):
        data = _sample_data(valid_until="2026-01-01")
        stale, msg = bcm.check_staleness(data, today=date(2026, 6, 8))
        self.assertTrue(stale)
        self.assertIn("expired", msg)

    def test_unparseable_valid_until_is_stale(self):
        data = _sample_data(valid_until="not-a-date")
        stale, _ = bcm.check_staleness(data, today=date(2026, 6, 8))
        self.assertTrue(stale)

    def test_staleness_is_advisory_exit0(self):
        # The CLI returns 0 on a stale table unless --strict.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps(_sample_data(valid_until="2000-01-01")))
            rc = bcm.main(["--canonical", str(p), "--check-staleness"])
            self.assertEqual(rc, 0)
            rc_strict = bcm.main(["--canonical", str(p), "--check-staleness", "--strict"])
            self.assertEqual(rc_strict, 1)


class TestReconcile(TestEnvContext):
    def test_agreeing_rows_no_findings(self):
        # opus-4-8 row matches both cost-table.yaml AND the opus_new tier.
        models = {"claude-opus-4-8": {
            "input_per_mtok": 5.0, "cache_write_5m_per_mtok": 6.25,
            "cache_write_1h_per_mtok": 10.0, "cache_read_per_mtok": 0.5,
            "output_per_mtok": 25.0}}
        data = _sample_data(models=models)
        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)
        self.assertEqual(findings, [])

    def test_divergence_is_flagged_not_overwritten(self):
        before = _COST_TABLE_PATH.read_text()
        models = {"claude-opus-4-8": {
            "input_per_mtok": 999.0, "cache_write_5m_per_mtok": 6.25,
            "cache_write_1h_per_mtok": 10.0, "cache_read_per_mtok": 0.5,
            "output_per_mtok": 25.0}}
        data = _sample_data(models=models)
        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)
        self.assertTrue(any(f["field"] == "input_per_mtok" and f["canonical"] == 999.0
                            for f in findings))
        # cost-table.yaml MUST be untouched (reconcile never writes).
        self.assertEqual(before, _COST_TABLE_PATH.read_text())

    def test_reconcile_advisory_exit0_strict_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            models = {"claude-opus-4-8": {
                "input_per_mtok": 999.0, "output_per_mtok": 25.0}}
            p.write_text(json.dumps(_sample_data(models=models)))
            self.assertEqual(bcm.main(["--canonical", str(p), "--reconcile"]), 0)
            self.assertEqual(
                bcm.main(["--canonical", str(p), "--reconcile", "--strict"]), 1)


class TestPriceFor(TestEnvContext):
    def test_known_model(self):
        data = _sample_data()
        price, known = bcm.price_for("claude-opus-4-8", data=data)
        self.assertTrue(known)
        self.assertEqual(price["input_per_mtok"], 5.0)
        self.assertEqual(price["output_per_mtok"], 25.0)

    def test_unknown_model_zero_and_flagged_S220(self):
        data = _sample_data()
        price, known = bcm.price_for("gpt-9-turbo", data=data)
        self.assertFalse(known)
        self.assertEqual(price["input_per_mtok"], 0.0)
        self.assertEqual(price["output_per_mtok"], 0.0)

    def test_case_insensitive_and_whitespace(self):
        data = _sample_data()
        price, known = bcm.price_for("  CLAUDE-OPUS-4-8 ", data=data)
        self.assertTrue(known)
        self.assertEqual(price["input_per_mtok"], 5.0)

    def test_dated_suffix_resolves_via_prefix(self):
        data = _sample_data()
        price, known = bcm.price_for("claude-opus-4-8-20260101", data=data)
        self.assertTrue(known)
        self.assertEqual(price["input_per_mtok"], 5.0)

    def test_sibling_prefix_does_not_false_match(self):
        # Codex pair-rail #2: prefix match must anchor on `mid + "-"`, NOT a bare
        # `startswith(mid)`. A sibling id `claude-opus-4-80` shares the `claude-opus-4-8`
        # string prefix but is a DIFFERENT model → must resolve unknown, not steal the
        # 4-8 price. The dated-suffix and exact cases must still resolve known.
        data = _sample_data()
        sibling_price, sibling_known = bcm.price_for("claude-opus-4-80", data=data)
        self.assertFalse(sibling_known)
        self.assertEqual(sibling_price["input_per_mtok"], 0.0)  # unknown fallback, NOT 5.0
        # the legitimate dated-suffix case keeps resolving to the base 4-8 row
        dated_price, dated_known = bcm.price_for("claude-opus-4-8-20260101", data=data)
        self.assertTrue(dated_known)
        self.assertEqual(dated_price["input_per_mtok"], 5.0)
        # exact still resolves
        exact_price, exact_known = bcm.price_for("claude-opus-4-8", data=data)
        self.assertTrue(exact_known)
        self.assertEqual(exact_price["input_per_mtok"], 5.0)

    def test_fail_open_on_missing_data(self):
        # When the data file is unreadable, price_for degrades to the all-zero
        # fallback and never raises (fail-open contract).
        with mock.patch.object(bcm, "load_canonical_models_safe", return_value=None):
            price, known = bcm.price_for("claude-opus-4-8")
        self.assertFalse(known)
        self.assertEqual(price["input_per_mtok"], 0.0)


class TestCacheMultiplierPins(TestEnvContext):
    """PLAN-133 B3 regression contract: 5m=1.25x / 1h=2.0x / read=0.1x."""

    def test_shipped_multipliers(self):
        data = bcm.load_canonical_models(_DATA_PATH)
        mult = data["cache_multipliers"]
        self.assertEqual(mult["cache_write_5m"], 1.25)
        self.assertEqual(mult["cache_write_1h"], 2.0)
        self.assertEqual(mult["cache_read"], 0.1)

    def test_opus48_row_obeys_multipliers(self):
        data = bcm.load_canonical_models(_DATA_PATH)
        row = data["models"]["claude-opus-4-8"]
        inp = row["input_per_mtok"]
        self.assertAlmostEqual(row["cache_write_5m_per_mtok"], inp * 1.25, places=6)
        self.assertAlmostEqual(row["cache_write_1h_per_mtok"], inp * 2.0, places=6)
        self.assertAlmostEqual(row["cache_read_per_mtok"], inp * 0.1, places=6)


class TestEnvFlagDefaultOff(TestEnvContext):
    def test_default_off(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(bcm.canonical_price_source_enabled())

    def test_on_when_set(self):
        with mock.patch.dict("os.environ", {bcm._ENABLE_FLAG: "1"}, clear=True):
            self.assertTrue(bcm.canonical_price_source_enabled())

    def test_off_for_garbage_value(self):
        with mock.patch.dict("os.environ", {bcm._ENABLE_FLAG: "maybe"}, clear=True):
            self.assertFalse(bcm.canonical_price_source_enabled())


class TestBuildFromModelsDev(TestEnvContext):
    def test_build_stamps_sha_and_drops_non_claude(self):
        raw = {
            "anthropic": {"models": {
                "claude-opus-4-8": {"cost": {"input": 5.0, "output": 25.0},
                                    "limit": {"context": 200000, "output": 64000}},
            }},
            "openai": {"models": {"gpt-9": {"cost": {"input": 1.0, "output": 2.0}}}},
        }
        built = bcm.build_from_models_dev(raw, today=date(2026, 6, 8))
        self.assertIn("claude-opus-4-8", built["models"])
        self.assertNotIn("gpt-9", built["models"])
        # provenance sha must verify against the built models.
        ok, _ = bcm.verify_checksum(built)
        self.assertTrue(ok)
        # cache columns derived from the multipliers.
        row = built["models"]["claude-opus-4-8"]
        self.assertAlmostEqual(row["cache_write_5m_per_mtok"], 5.0 * 1.25, places=6)

    def test_empty_claude_rows_fail_closed(self):
        with self.assertRaises(bcm.CanonicalModelsError):
            bcm.build_from_models_dev({"openai": {"models": {"gpt-9": {}}}})


class TestNoNetworkImport(TestEnvContext):
    """Provenance §2: agents must not fetch. The module must not import any
    network client."""

    def test_no_urllib_or_requests_in_source(self):
        # Inspect the parsed AST so docstring prose ("opens a network socket")
        # cannot trip the guard — only real imports count.
        import ast
        tree = ast.parse(_SCRIPT_PATH.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for banned in ("urllib", "requests", "http", "socket", "httpx", "aiohttp"):
            self.assertNotIn(banned, imported,
                             f"network client {banned!r} must not be imported")


class TestVerifyCLI(TestEnvContext):
    def test_verify_seed_exit0(self):
        rc = bcm.main(["--verify"])
        self.assertEqual(rc, 0)

    def test_verify_tampered_exit1(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            models = _sample_models()
            data = _sample_data(models=models, sha=bcm.compute_models_sha256(models))
            data["models"]["claude-opus-4-8"]["input_per_mtok"] = 0.01
            p.write_text(json.dumps(data))
            err = io.StringIO()
            with mock.patch("sys.stderr", err):
                rc = bcm.main(["--canonical", str(p), "--verify"])
            self.assertEqual(rc, 1)
            self.assertIn("MISMATCH", err.getvalue())


if __name__ == "__main__":
    unittest.main()
