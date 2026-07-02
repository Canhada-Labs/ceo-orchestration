"""test_loader.py — coverage for tier_policy.loader.

Targets the staged module at
``.claude/plans/PLAN-071/staging/tier_policy/loader.py``.

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1            — symbol path is ``tier_policy.loader.load_policy``.
* R-CR Unseen #1   — module-level cache deterministic; mtime-keyed.
* R-CR Unseen #2   — advisory-only contract: ``load_policy`` NEVER raises.
* R-SEC U2         — size + depth caps enforced before deserialisation.
* R-SEC U4         — concurrent loaders coordinate without exception.
* R-CR R2-2        — schema migration v1 → v2 (additive only).
* P2-12            — outer ``try`` wraps ``Path()`` construction;
                     ``default_model`` validated against ``MODEL_ID``.

Stdlib-only. Python ≥ 3.9.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from _lib.tier_policy import loader as L
from _lib.tier_policy._constants import FROZEN_BASELINE


def _write_json(p: Path, payload) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        p.write_text(payload, encoding="utf-8")
    else:
        p.write_text(json.dumps(payload), encoding="utf-8")


class _FsBase(unittest.TestCase):
    """unittest.TestCase variant with ``self.tmp`` (Path) per test."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp_dir = tempfile.TemporaryDirectory(prefix="tier-loader-")
        self.tmp = Path(self._tmp_dir.name)
        self.policy = self.tmp / ".claude" / "policy" / "tier-policy.json"
        L.clear_cache()

    def tearDown(self) -> None:
        L.clear_cache()
        self._tmp_dir.cleanup()
        super().tearDown()


# ---------------------------------------------------------------------------
# Advisory-only contract — load_policy MUST never raise
# ---------------------------------------------------------------------------


class TestNeverRaises(_FsBase):
    """R-CR Unseen #2 — every error path returns FROZEN_BASELINE."""

    def test_missing_file_returns_fallback(self):
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.reason.startswith("fallback:"))
        self.assertIn("missing", result.reason)

    def test_corrupted_json_returns_fallback(self):
        _write_json(self.policy, "not-json{{{")
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("parse_error", result.reason)

    def test_empty_file_returns_fallback(self):
        _write_json(self.policy, "")
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)

    def test_array_json_returns_fallback(self):
        _write_json(self.policy, [1, 2, 3])
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("not_object", result.reason)

    def test_oversize_returns_fallback(self):
        # Just over 64 KiB so the size guard trips.
        oversized = {"name": "x" * (66 * 1024)}
        _write_json(self.policy, oversized)
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("oversize", result.reason)

    def test_bad_mode_returns_fallback(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "XS",
                "default_model": "claude-opus-4-8",
            },
        )
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("bad_mode", result.reason)

    def test_schema_mismatch_returns_fallback(self):
        _write_json(
            self.policy,
            {"schema_version": 99, "default_mode": "M"},
        )
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("schema_mismatch", result.reason)


# ---------------------------------------------------------------------------
# P2-12 — advisory safety net + unknown_model
# ---------------------------------------------------------------------------


class TestAdvisorySafetyNet(_FsBase):
    """P2-12 — NOTHING escapes load_policy, including malformed paths."""

    def test_non_stringifiable_path_returns_fallback(self):
        """Object whose ``str()`` raises must NOT escape."""

        class Boom:
            def __str__(self) -> str:
                raise RuntimeError("intentional")

            def __fspath__(self) -> str:
                raise RuntimeError("intentional")

        # Must not raise. Must return a fallback ClassificationResult.
        result = L.load_policy(Boom())  # type: ignore[arg-type]
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.reason.startswith("fallback:"))

    def test_none_path_uses_default(self):
        """``path=None`` → default path resolution; never raises."""
        # Default path almost certainly doesn't exist in the test env.
        result = L.load_policy(None)
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.reason.startswith("fallback:"))

    def test_non_string_path_does_not_escape(self):
        """Random non-Path argument must not surface its TypeError."""
        result = L.load_policy(12345)  # type: ignore[arg-type]
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.reason.startswith("fallback:"))

    def test_outer_try_catches_anything(self):
        """Even a contrived TypeError inside the inner body must not escape."""
        # Pass an object that breaks ``Path()`` construction subtly.
        result = L.load_policy(object())  # type: ignore[arg-type]
        self.assertEqual(result.confidence, 0.0)
        self.assertTrue(result.reason.startswith("fallback:"))


class TestUnknownModelValidation(_FsBase):
    """P2-12 — ``default_model`` must be a member of ``MODEL_ID`` enum."""

    def test_unknown_model_string_returns_fallback(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "claude-opus-4-1",  # legacy slug, not in enum
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("unknown_model", result.reason)

    def test_gpt_model_returns_fallback(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "gpt-4o",
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("unknown_model", result.reason)

    def test_random_string_model_returns_fallback(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "definitely-not-a-model",
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("unknown_model", result.reason)

    def test_all_known_models_pass(self):
        """EVERY ``MODEL_ID`` value passes the validation.

        Iterates the enum itself (not a hardcoded list) so a new member —
        e.g. SONNET5, ADR-157 — is pinned automatically: an on-disk policy
        naming it must load cleanly, never trip the ``unknown_model``
        fallback (Codex pair-rail, PLAN-152 Wave F review).
        """
        from _lib.tier_policy import _types as _T
        for model in (m.value for m in _T.MODEL_ID):
            _write_json(
                self.policy,
                {
                    "schema_version": 2,
                    "default_mode": "M",
                    "default_model": model,
                    "confidence": 0.7,
                },
            )
            L.clear_cache()
            result = L.load_policy(str(self.policy), use_cache=False)
            self.assertEqual(
                result.suggested_model,
                model,
                msg=f"valid model {model!r} did not load cleanly",
            )


# ---------------------------------------------------------------------------
# Happy path — valid v2 returns mode + confidence
# ---------------------------------------------------------------------------


class TestHappyPath(_FsBase):
    def test_valid_v2_loads(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "L",
                "default_model": "claude-opus-4-8",
                "confidence": 0.9,
                "source": "on_disk_v2",
                "reason": "fixture",
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.mode, "L")
        self.assertEqual(result.suggested_model, "claude-opus-4-8")
        self.assertEqual(result.confidence, 0.9)

    def test_all_four_modes_parse(self):
        for mode in ("S", "M", "L", "XL"):
            _write_json(
                self.policy,
                {
                    "schema_version": 2,
                    "default_mode": mode,
                    "default_model": "claude-opus-4-8",
                    "confidence": 0.5,
                },
            )
            L.clear_cache()
            result = L.load_policy(str(self.policy), use_cache=False)
            self.assertEqual(result.mode, mode)


# ---------------------------------------------------------------------------
# Confidence clamping
# ---------------------------------------------------------------------------


class TestConfidenceClamping(_FsBase):
    """Out-of-range confidence collapses to 0.0 (advisory-only safe)."""

    def test_too_high_clamps_to_zero(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "claude-opus-4-8",
                "confidence": 1.5,
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)

    def test_negative_clamps_to_zero(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "claude-opus-4-8",
                "confidence": -0.1,
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)

    def test_non_numeric_falls_to_zero(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "claude-opus-4-8",
                "confidence": "high",
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)


# ---------------------------------------------------------------------------
# Schema migration v1 → v2
# ---------------------------------------------------------------------------


class TestSchemaMigration(_FsBase):
    """R-CR R2-2 — additive v1 → v2 silently; defaults documented."""

    def test_v1_migrated_default_confidence(self):
        _write_json(
            self.policy,
            {
                "schema_version": 1,
                "default_mode": "M",
                "default_model": "claude-sonnet-4-6",
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        # confidence default = 0.5 per loader._migrate
        self.assertEqual(result.confidence, 0.5)
        self.assertEqual(result.mode, "M")
        self.assertEqual(result.suggested_model, "claude-sonnet-4-6")

    def test_v1_migrated_does_not_raise(self):
        _write_json(
            self.policy,
            {
                "schema_version": 1,
                "default_mode": "S",
                "default_model": "claude-haiku-4-5",
            },
        )
        # Must complete without exception.
        L.load_policy(str(self.policy), use_cache=False)


# ---------------------------------------------------------------------------
# Cache semantics — R-CR Unseen #1
# ---------------------------------------------------------------------------


class TestCache(_FsBase):
    def test_mtime_cache_hit(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "L",
                "default_model": "claude-opus-4-8",
                "confidence": 0.7,
            },
        )
        a = L.load_policy(str(self.policy))
        b = L.load_policy(str(self.policy))
        # Same instance returned from the cache.
        self.assertIs(a, b)

    def test_use_cache_false_forces_reload(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "L",
                "default_model": "claude-opus-4-8",
                "confidence": 0.7,
            },
        )
        a = L.load_policy(str(self.policy))
        b = L.load_policy(str(self.policy), use_cache=False)
        # Different instance because cache bypassed.
        self.assertIsNot(a, b)
        # But equal field-by-field.
        self.assertEqual(a.mode, b.mode)
        self.assertEqual(a.suggested_model, b.suggested_model)
        self.assertEqual(a.confidence, b.confidence)

    def test_clear_cache_drops_entries(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "L",
                "default_model": "claude-opus-4-8",
                "confidence": 0.7,
            },
        )
        a = L.load_policy(str(self.policy))
        L.clear_cache()
        b = L.load_policy(str(self.policy))
        self.assertIsNot(a, b)

    def test_mtime_change_invalidates_cache(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "S",
                "default_model": "claude-opus-4-8",
                "confidence": 0.5,
            },
        )
        a = L.load_policy(str(self.policy))
        # Force mtime to change (some filesystems have 1-second resolution).
        time.sleep(0.01)
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "XL",
                "default_model": "claude-opus-4-8",
                "confidence": 0.95,
            },
        )
        # Bump mtime explicitly to defeat low-resolution clocks.
        future = time.time() + 5
        os.utime(self.policy, (future, future))
        b = L.load_policy(str(self.policy))
        self.assertEqual(b.mode, "XL")
        self.assertNotEqual(a.mode, b.mode)


# ---------------------------------------------------------------------------
# Depth cap — R-SEC U2
# ---------------------------------------------------------------------------


class TestDepthLimit(_FsBase):
    def test_excess_depth_returns_fallback(self):
        # Nest dict deeper than LIMIT_DEPTH (=8).
        deep = "leaf"
        for _ in range(15):
            deep = {"k": deep}  # type: ignore[assignment]
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "M",
                "default_model": "claude-opus-4-8",
                "extras": deep,
            },
        )
        result = L.load_policy(str(self.policy), use_cache=False)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("depth_limit", result.reason)


# ---------------------------------------------------------------------------
# Concurrency — R-SEC U4
# ---------------------------------------------------------------------------


class TestConcurrentLoaders(_FsBase):
    """16 threads call load_policy in parallel; no exception, consistent results."""

    def test_concurrent_load(self):
        _write_json(
            self.policy,
            {
                "schema_version": 2,
                "default_mode": "L",
                "default_model": "claude-opus-4-8",
                "confidence": 0.8,
            },
        )
        results = []
        errors = []

        def worker():
            try:
                results.append(L.load_policy(str(self.policy)))
            except Exception as exc:  # pragma: no cover — must not happen
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(errors), 0, msg=f"errors={errors}")
        self.assertEqual(len(results), 16)
        for r in results:
            self.assertEqual(r.mode, "L")
            self.assertEqual(r.confidence, 0.8)


# ---------------------------------------------------------------------------
# Default-path resolution
# ---------------------------------------------------------------------------


class TestDefaultPath(_FsBase):
    def test_default_path_with_claude_project_dir(self):
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.tmp)
        try:
            # File doesn't exist → fallback (NOT a raise).
            result = L.load_policy()
            self.assertEqual(result.confidence, 0.0)
        finally:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)


# ---------------------------------------------------------------------------
# Fallback content sanity
# ---------------------------------------------------------------------------


class TestFallbackContent(_FsBase):
    """Fallback uses FROZEN_BASELINE projection — verify shape."""

    def test_fallback_mode_from_baseline(self):
        result = L.load_policy(str(self.policy))
        self.assertEqual(result.mode, FROZEN_BASELINE["default_mode"])

    def test_fallback_model_from_baseline(self):
        result = L.load_policy(str(self.policy))
        self.assertEqual(
            result.suggested_model, FROZEN_BASELINE["default_model"]
        )

    def test_fallback_reason_has_prefix(self):
        result = L.load_policy(str(self.policy))
        self.assertTrue(result.reason.startswith("fallback:"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
