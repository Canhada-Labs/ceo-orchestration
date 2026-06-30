"""test_ceo_boot_enhanced.py — PLAN-065 §4.3 Phase 2 enhancement tests.

Extends test_ceo_boot.py (S82 MVP — 30 tests covering registry, dispatcher,
sanitization, recommendations engine, renderer, --short, --json) with the
post-MVP §4.3 acceptance suite:

- §4.3.2 real per-key cache (cold/warm/stale TTL/corrupted/wrong-key/LRU)
- §4.3 --bench mode (N=5, p50/p95 ordering, RSS delta, markdown table)
- §4.3.3 --verbose mode (10 Tier-A checks discovery + budget + ordering)
- §4.3 Sec MF-4 sanitization (NFKC + 200-cap + 5-item cap + scan + homoglyph
  + NUL + path-traversal + deterministic order)
- §4.3.4 audit emit telemetry (emitted called / fields whitelisted /
  DENIED absent / check_skipped on timeout / hasattr-guard / payload schema)
- CR-MF6 idempotency (back-to-back identical / transient failure recovery)
- Integration end-to-end (default / --short / --cached / --json / --bench / --verbose)

All tests use TestEnvContext (S79 hygiene) for env isolation; no real $HOME
or $CLAUDE_PROJECT_DIR mutation. Cache dir is overridden via the
CEO_BOOT_CACHE_DIR env var that ceo-boot resolves at call time.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import unicodedata
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"


def _load_module():
    """Load ceo-boot.py as importable module. Re-loads on each call to ensure
    test isolation when a previous test mutated module-level state."""
    spec = importlib.util.spec_from_file_location("ceo_boot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ceo_boot"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


# ----------------------------------------------------------------------------
# §4.3.2 Real per-key cache — cold/warm/stale-TTL/corrupted/wrong-key/LRU
# ----------------------------------------------------------------------------


class TestRealCache(TestEnvContext):
    """PLAN-065 §4.3.2 — real per-key cache file under state/ceo-boot-cache/."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="ceo-boot-cache-test-")
        os.environ["CEO_BOOT_CACHE_DIR"] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        super().tearDown()

    def _ck(self, name: str, status: str = "green", summary: str = "ok"):
        return _mod.CheckResult(name, status, summary, 1.0, None)

    def test_cache_cold_miss(self):
        """Cold start: empty cache dir → cached_load returns (False, None)."""
        hit, payload = _mod.cached_load()
        self.assertFalse(hit)
        self.assertIsNone(payload)

    def test_cache_warm_hit(self):
        """Store + immediate load → hit with same payload."""
        results = [self._ck(name) for name, _ in _mod.TIER_S_CHECKS]
        _mod.cached_store(results)
        hit, payload = _mod.cached_load()
        self.assertTrue(hit)
        self.assertIsNotNone(payload)
        # PLAN-091 Wave A.1: bumped 15 → 16.
        # S127 cadence-amendment + PLAN-106 Wave F: 16 → 20 (drift absorbed).
        # PLAN-135 W1 S3: 20 → 21 (settings_tamper_tripwires).
        self.assertEqual(payload["checks_total"], 21)  # PLAN-135 W1 S3
        self.assertEqual(payload["checks_failed"], 0)
        self.assertTrue(payload["gate_pass"])

    def test_cache_stale_ttl_miss(self):
        """Cache file > 1h old → miss (TTL invalidation)."""
        results = [self._ck(name) for name, _ in _mod.TIER_S_CHECKS]
        _mod.cached_store(results)
        # Backdate the file mtime to 2 hours ago
        key = _mod._cache_key()
        path = _mod._cache_path_for_key(key)
        old = time.time() - 7200
        os.utime(path, (old, old))
        hit, payload = _mod.cached_load()
        self.assertFalse(hit)
        self.assertIsNone(payload)

    def test_cache_corrupted_file_miss(self):
        """Cache file with malformed JSON → graceful miss (fail-open)."""
        cdir = Path(self.tmpdir)
        cdir.mkdir(parents=True, exist_ok=True)
        # Write garbage at the expected key path
        key = _mod._cache_key()
        path = cdir / f"{key}.json"
        path.write_text("{not json{{{", encoding="utf-8")
        hit, payload = _mod.cached_load()
        self.assertFalse(hit)
        self.assertIsNone(payload)

    def test_cache_wrong_key_miss(self):
        """File present but cache_key field doesn't match current → miss."""
        cdir = Path(self.tmpdir)
        cdir.mkdir(parents=True, exist_ok=True)
        key = _mod._cache_key()
        path = cdir / f"{key}.json"
        # Write payload with wrong cache_key value
        path.write_text(
            json.dumps({"cache_key": "DIFFERENT_KEY", "results": [], "ts": time.time()}),
            encoding="utf-8",
        )
        hit, payload = _mod.cached_load()
        self.assertFalse(hit)

    def test_cache_lru_eviction(self):
        """Dir size > 10 MB cap triggers LRU eviction (oldest first)."""
        cdir = Path(self.tmpdir)
        cdir.mkdir(parents=True, exist_ok=True)
        # Force cap small so we can exercise without 10MB of writes
        original_cap = _mod.CACHE_DIR_SIZE_CAP_BYTES
        try:
            _mod.CACHE_DIR_SIZE_CAP_BYTES = 1024  # 1 KB cap for the test
            # Create 10 dummy cache files of 200 bytes each → 2 KB total
            now = time.time()
            for i in range(10):
                p = cdir / f"key{i:02d}.json"
                p.write_text("x" * 200, encoding="utf-8")
                # Spread atimes so eviction order is predictable
                atime = now - (10 - i) * 60  # older for lower indices
                os.utime(p, (atime, atime))
            # Trigger eviction
            _mod.cache_lru_evict()
            remaining = list(cdir.glob("*.json"))
            # Some files must have been evicted — total now under cap
            total = sum(p.stat().st_size for p in remaining)
            self.assertLessEqual(total, _mod.CACHE_DIR_SIZE_CAP_BYTES)
            # The oldest (key00) must be gone before key09
            names = {p.name for p in remaining}
            self.assertNotIn("key00.json", names)
        finally:
            _mod.CACHE_DIR_SIZE_CAP_BYTES = original_cap

    def test_cache_hit_under_200ms_budget(self):
        """Cache-hit cached_load() must complete under 200ms budget."""
        results = [self._ck(name) for name, _ in _mod.TIER_S_CHECKS]
        _mod.cached_store(results)
        # Measure 5 cache loads, take p95
        durations = []
        for _ in range(5):
            t0 = time.perf_counter()
            hit, _ = _mod.cached_load()
            d = (time.perf_counter() - t0) * 1000
            self.assertTrue(hit)
            durations.append(d)
        p95 = sorted(durations)[int(0.95 * len(durations))]
        self.assertLess(p95, _mod.CACHE_HIT_BUDGET_MS,
                        f"p95={p95:.1f}ms > budget {_mod.CACHE_HIT_BUDGET_MS}ms")


# ----------------------------------------------------------------------------
# §4.3 --bench mode tests
# ----------------------------------------------------------------------------


class TestBenchMode(TestEnvContext):
    """PLAN-065 §4.3 bench harness contract (N=5 + p50/p95 + RSS delta)."""

    def test_bench_basic_run(self):
        """N=2 basic invocation produces well-formed report."""
        report = _mod.bench(n_runs=2)
        self.assertEqual(report["n_runs"], 2)
        self.assertIn("iterations", report)
        self.assertEqual(len(report["iterations"]), 2)
        self.assertIn("summary", report)

    def test_bench_p50_le_p95(self):
        """p50 ≤ p95 (percentile monotonicity)."""
        report = _mod.bench(n_runs=5)
        s = report["summary"]
        self.assertLessEqual(s["p50_ms"], s["p95_ms"])
        self.assertLessEqual(s["min_ms"], s["p50_ms"])
        self.assertLessEqual(s["p95_ms"], s["max_ms"])

    def test_bench_rss_delta_sane(self):
        """RSS delta should be a finite number (positive or near-zero)."""
        report = _mod.bench(n_runs=2)
        rss = report["summary"]["rss_delta_kb"]
        self.assertIsInstance(rss, float)
        # RSS may shrink slightly between calls due to GC; bounded magnitude
        self.assertLess(abs(rss), 10 * 1024 * 1024)  # < 10 GB sanity

    def test_bench_n5_default(self):
        """Default N=5 iterations when bench-n not specified."""
        report = _mod.bench()  # default
        self.assertEqual(report["n_runs"], 5)
        self.assertEqual(len(report["iterations"]), 5)

    def test_bench_iterations_have_iter_duration_rss(self):
        """Each iteration row must have iter, duration_ms, rss_kb keys."""
        report = _mod.bench(n_runs=2)
        for it in report["iterations"]:
            self.assertIn("iter", it)
            self.assertIn("duration_ms", it)
            self.assertIn("rss_kb", it)
            self.assertGreater(it["duration_ms"], 0)

    def test_bench_markdown_renderer(self):
        """render_bench_markdown produces table with expected columns."""
        report = _mod.bench(n_runs=2)
        md = _mod.render_bench_markdown(report)
        self.assertIn("| iter | duration_ms | RSS_kb |", md)
        self.assertIn("**summary**", md)
        self.assertIn("p50=", md)
        self.assertIn("p95=", md)

    def test_percentile_helper_indexing(self):
        """_percentile uses sorted-index method (not interpolation)."""
        # Known case: [1,2,3,4,5] p50 = 3, p95 = 5
        self.assertEqual(_mod._percentile([1, 2, 3, 4, 5], 50), 3)
        self.assertEqual(_mod._percentile([1, 2, 3, 4, 5], 95), 5)
        # Empty list → 0
        self.assertEqual(_mod._percentile([], 50), 0.0)


# ----------------------------------------------------------------------------
# §4.3.3 --verbose mode (10 Tier-A checks)
# ----------------------------------------------------------------------------


class TestVerboseMode(TestEnvContext):
    """PLAN-065 §4.3.3 — Tier-A check registry + dispatch."""

    def test_tier_a_registry_has_10_checks(self):
        self.assertEqual(len(_mod.TIER_A_CHECKS), 10)

    def test_tier_a_names_unique(self):
        names = [name for name, _ in _mod.TIER_A_CHECKS]
        self.assertEqual(len(names), len(set(names)))

    def test_tier_a_all_callables(self):
        for name, fn in _mod.TIER_A_CHECKS:
            self.assertTrue(callable(fn), f"{name} not callable")

    def test_tier_a_names_prefixed(self):
        """All Tier-A check names start with 'tier_a_' for easy grep."""
        for name, _ in _mod.TIER_A_CHECKS:
            self.assertTrue(name.startswith("tier_a_"),
                            f"Tier-A name {name!r} missing prefix")

    def test_dispatch_with_tier_a_returns_31_results(self):
        """include_tier_a=True dispatches all 31 checks (21+10).

        PLAN-091 Wave A.1: Tier-S bumped 15 → 16.
        S127 + PLAN-106 Wave F: Tier-S bumped 16 → 20 (drift absorbed).
        PLAN-135 W1 S3: Tier-S bumped 20 → 21 (settings_tamper_tripwires).
        """
        results = _mod.dispatch_parallel(include_tier_a=True)
        self.assertEqual(len(results), 31)  # PLAN-135 W1 S3: 21+10

    def test_dispatch_without_tier_a_returns_21(self):
        """Default dispatch (Tier-S only) returns 21 post-PLAN-135 W1 S3."""
        results = _mod.dispatch_parallel()
        self.assertEqual(len(results), 21)  # PLAN-135 W1 S3

    def test_dispatch_verbose_budget_10s(self):
        """Verbose dispatch fits in 10s aggregate (CI cold-start slack: 12s)."""
        t0 = time.perf_counter()
        _mod.dispatch_parallel(include_tier_a=True)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 12.0)

    def test_dispatch_verbose_results_in_registry_order(self):
        """Verbose results emitted Tier-S first then Tier-A (CR-N7 stable)."""
        results = _mod.dispatch_parallel(include_tier_a=True)
        names = [r.name for r in results]
        expected = [n for n, _ in _mod.TIER_S_CHECKS] + [n for n, _ in _mod.TIER_A_CHECKS]
        # Filter expected by which actually completed (in case any timed out)
        filtered_expected = [n for n in expected if n in {r.name for r in results}]
        self.assertEqual(names, filtered_expected)

    def test_check_tier_a_debate_transcripts_runs(self):
        status, summary, _ = _mod.check_tier_a_debate_transcripts()
        self.assertIn(status, ("green", "yellow"))

    def test_check_tier_a_lessons_30d_runs(self):
        status, summary, detail = _mod.check_tier_a_lessons_30d()
        self.assertIn(status, ("green", "yellow"))
        self.assertIsInstance(detail, int)

    def test_check_tier_a_npm_version_match_runs(self):
        status, summary, _ = _mod.check_tier_a_npm_version_match()
        self.assertIn(status, ("green", "yellow", "red"))

    def test_check_tier_a_adrs_recent_status_runs(self):
        status, summary, detail = _mod.check_tier_a_adrs_recent_status()
        self.assertEqual(status, "green")
        # Detail dict should have all 7 reserved slots
        self.assertEqual(len(detail), 7)


# ----------------------------------------------------------------------------
# §4.3 Sec MF-4 sanitization expanded suite
# ----------------------------------------------------------------------------


class TestSanitizationExpanded(TestEnvContext):
    """Sec MF-4: NFKC + length + scan + homoglyph + NUL + path-traversal."""

    def test_sanitize_nfkc_fullwidth(self):
        """Fullwidth chars normalized to ASCII via NFKC."""
        # Fullwidth 'P' (U+FF30) + 'L' + 'A' + 'N'
        fw = "ＰＬＡＮ-073"
        out = _mod._sanitize_for_recs(fw)
        # NFKC should yield ASCII PLAN
        self.assertIn("PLAN", out)

    def test_sanitize_nfkc_ligature(self):
        """Ligature ﬁ (U+FB01) normalized to 'fi'."""
        out = _mod._sanitize_for_recs("PLAN-ﬁle")
        self.assertIn("file", out.lower())

    def test_sanitize_200_char_cap_strict(self):
        """Output never exceeds 200 chars for any input length."""
        for length in (200, 201, 500, 5000, 50000):
            out = _mod._sanitize_for_recs("X" * length)
            self.assertLessEqual(len(out), 200)

    def test_sanitize_strips_nul_bytes(self):
        """NUL bytes (\\x00) stripped; rest preserved."""
        out = _mod._sanitize_for_recs("safe\x00\x00text")
        self.assertNotIn("\x00", out)
        self.assertIn("safe", out)
        self.assertIn("text", out)

    def test_sanitize_homoglyph_cyrillic_a(self):
        """Cyrillic 'а' (U+0430) is NOT collapsed by NFKC (different script);
        but mathematical alphanumerics DO collapse.

        We assert behavior is deterministic (same input → same output)
        rather than asserting collapse, since NFKC is script-aware."""
        c = "PLAа"  # Cyrillic 'a'
        out1 = _mod._sanitize_for_recs(c)
        out2 = _mod._sanitize_for_recs(c)
        self.assertEqual(out1, out2)
        # NFKC does NOT change cyrillic-a; the string passes through
        self.assertEqual(out1, unicodedata.normalize("NFKC", c))

    def test_sanitize_path_traversal_neutralized(self):
        """Path-traversal sequences pass through harmlessly (no eval/exec)."""
        out = _mod._sanitize_for_recs("../../../../etc/passwd")
        # The string content is preserved (sanitizer doesn't fix paths;
        # it only prevents injection patterns + HTML/markdown rendering).
        # The contract is: the output is plain text safe for terminal echo.
        self.assertIsInstance(out, str)
        # No backticks, no angles
        self.assertNotIn("`", out)
        self.assertNotIn("<", out)

    def test_sanitize_deterministic(self):
        """Same input → same output across calls (CR-N7)."""
        s = "PLAN-073<x>`cmd`"
        a = _mod._sanitize_for_recs(s)
        b = _mod._sanitize_for_recs(s)
        c = _mod._sanitize_for_recs(s)
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_recs_max_5_items_strict(self):
        """Even with 10 distinct triggering checks, recs cap at 5."""
        ck = lambda name, status, detail: _mod.CheckResult(  # noqa: E731
            name, status, "summary", 1.0, detail
        )
        # Build 10 disparate triggering inputs
        results = [
            ck("sentinels_pending_gpg", "yellow", ["s1.md", "s2.md"]),
            ck("plans_stranded_executing", "red", ["P1", "P2"]),
            ck("skill_unknown_ratio", "red", None),
            ck("audit_v3_backlog", "yellow", ["X1", "X2"]),
            ck("adrs_stale_proposed", "yellow", ["A1", "A2"]),
            # plus extras to potentially flood
            ck("extra1", "timeout", None),
            ck("extra2", "error", None),
            ck("extra3", "error", None),
            ck("extra4", "error", None),
            ck("extra5", "error", None),
        ]
        recs = _mod._make_recommendations(results)
        self.assertLessEqual(len(recs), 5)


# ----------------------------------------------------------------------------
# §4.3.4 Audit emit telemetry (Sec MF-3 field allowlist)
# ----------------------------------------------------------------------------


class TestAuditEmitTelemetry(TestEnvContext):
    """PLAN-065 Phase 2 audit_emit wire — Reality-Ledger fixture #4 closure."""

    def test_emit_ceo_boot_emitted_callable(self):
        """Post-S82 ceremony, the symbol must exist in audit_emit."""
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        from _lib import audit_emit  # type: ignore
        self.assertTrue(hasattr(audit_emit, "emit_ceo_boot_emitted"))
        self.assertTrue(callable(audit_emit.emit_ceo_boot_emitted))

    def test_emit_ceo_boot_check_skipped_callable(self):
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        from _lib import audit_emit  # type: ignore
        self.assertTrue(hasattr(audit_emit, "emit_ceo_boot_check_skipped"))

    def test_known_actions_extended(self):
        """audit_emit._KNOWN_ACTIONS contains the 2 ceo_boot actions."""
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        from _lib import audit_emit  # type: ignore
        self.assertIn("ceo_boot_emitted", audit_emit._KNOWN_ACTIONS)
        self.assertIn("ceo_boot_check_skipped", audit_emit._KNOWN_ACTIONS)

    def test_emitted_safe_no_op_when_audit_module_absent(self):
        """Fail-open contract: monkey-patch _audit_emit=None → no exception."""
        original = _mod._audit_emit
        try:
            _mod._audit_emit = None  # type: ignore[assignment]
            # Should not raise:
            _mod._emit_ceo_boot_emitted_safe(
                gate_pass=True, duration_ms=100, checks_total=15,
                checks_failed=0, cache_hit=False,
            )
            _mod._emit_ceo_boot_check_skipped_safe(check_name="x", timeout_ms=500)
        finally:
            _mod._audit_emit = original

    def test_emitted_safe_does_not_pass_denied_fields(self):
        """The wrapper passes ONLY allowlisted kwargs to emit_ceo_boot_emitted.

        Test-isolation discipline (S83 fix): patch on `_mod._audit_emit`
        directly (the module reference ceo-boot.py uses) rather than on
        `audit_emit` global module. This sidesteps test pollution from
        other test files that may reload `_lib.audit_emit` between
        runs and cause `_mod._audit_emit` to point at a stale module.
        """
        captured_kwargs: list = []

        def _fake_emit(**kwargs):
            captured_kwargs.append(kwargs)

        # Use _mod._audit_emit directly — it's the module reference
        # ceo-boot.py imported at line 127. Patch the attribute on
        # that reference so getattr() inside the wrapper resolves to
        # our fake function.
        original_audit_emit = _mod._audit_emit
        if original_audit_emit is None:
            self.skipTest("_audit_emit module not loaded — pre-canonical")
        original_fn = getattr(original_audit_emit, "emit_ceo_boot_emitted", None)
        if original_fn is None:
            self.skipTest("emit_ceo_boot_emitted not registered yet")
        try:
            original_audit_emit.emit_ceo_boot_emitted = _fake_emit
            _mod._emit_ceo_boot_emitted_safe(
                gate_pass=True, duration_ms=100, checks_total=15,
                checks_failed=0, cache_hit=False,
            )
            self.assertEqual(len(captured_kwargs), 1)
            kwargs = captured_kwargs[0]
            allowed = {
                "session_id", "gate_pass", "duration_ms",
                "checks_total", "checks_failed", "cache_hit",
            }
            denied = {"tokens", "cost_usd", "prompt", "skill_content",
                      "file_paths", "recommendations", "env"}
            for k in kwargs:
                self.assertIn(k, allowed, f"unexpected kwarg {k}")
                self.assertNotIn(k, denied, f"DENIED field leaked: {k}")
        finally:
            original_audit_emit.emit_ceo_boot_emitted = original_fn

    def test_check_skipped_safe_field_allowlist(self):
        """check_skipped wrapper: only check_name + timeout_ms (+ session_id).

        Same test-isolation pattern as test_emitted_safe_does_not_pass_denied_fields.
        """
        captured: list = []

        def _fake(**kwargs):
            captured.append(kwargs)

        original_audit_emit = _mod._audit_emit
        if original_audit_emit is None:
            self.skipTest("_audit_emit module not loaded — pre-canonical")
        original_fn = getattr(
            original_audit_emit, "emit_ceo_boot_check_skipped", None
        )
        if original_fn is None:
            self.skipTest("emit_ceo_boot_check_skipped not registered yet")
        try:
            original_audit_emit.emit_ceo_boot_check_skipped = _fake
            _mod._emit_ceo_boot_check_skipped_safe(
                check_name="plans_executing", timeout_ms=500,
            )
            self.assertEqual(len(captured), 1)
            allowed = {"session_id", "check_name", "timeout_ms"}
            for k in captured[0]:
                self.assertIn(k, allowed)
        finally:
            original_audit_emit.emit_ceo_boot_check_skipped = original_fn


# ----------------------------------------------------------------------------
# CR-MF6 idempotency
# ----------------------------------------------------------------------------


class TestIdempotency(TestEnvContext):
    """CR-MF6 — back-to-back runs deterministic; transient failures recover."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="ceo-boot-idem-")
        os.environ["CEO_BOOT_CACHE_DIR"] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        super().tearDown()

    def test_back_to_back_identical_results(self):
        """Running dispatch twice in quick succession yields same status set."""
        r1 = _mod.dispatch_parallel()
        r2 = _mod.dispatch_parallel()
        names1 = [r.name for r in r1]
        names2 = [r.name for r in r2]
        self.assertEqual(names1, names2)
        # Status set should be identical (durations may differ slightly)
        s1 = {r.name: r.status for r in r1}
        s2 = {r.name: r.status for r in r2}
        self.assertEqual(s1, s2)

    def test_recs_back_to_back_same(self):
        """Recommendations are stable across back-to-back dispatch."""
        r1 = _mod.dispatch_parallel()
        recs1 = _mod._make_recommendations(r1)
        r2 = _mod.dispatch_parallel()
        recs2 = _mod._make_recommendations(r2)
        # Identical or near-identical (timestamps may shift status slightly,
        # but rec list itself shouldn't grow/shrink unpredictably)
        self.assertEqual(len(recs1), len(recs2))

    def test_cached_store_recovers_from_oserror(self):
        """If write fails (e.g. permission), main path still emits digest."""
        results = [_mod.CheckResult(n, "green", "ok", 1.0, None)
                   for n, _ in _mod.TIER_S_CHECKS]
        # Override mkdir to raise — fail-open contract verified by no-raise
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("deny")):
            err_io = io.StringIO()
            with redirect_stderr(err_io):
                _mod.cached_store(results)  # MUST NOT raise
            self.assertIn("cache-store failed", err_io.getvalue())


# ----------------------------------------------------------------------------
# Integration end-to-end CLI tests
# ----------------------------------------------------------------------------


class TestIntegrationCLI(TestEnvContext):
    """End-to-end main() with real flag combinations."""

    def setUp(self):
        super().setUp()
        self.tmpdir = tempfile.mkdtemp(prefix="ceo-boot-int-")
        os.environ["CEO_BOOT_CACHE_DIR"] = self.tmpdir

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        super().tearDown()

    def test_main_default(self):
        """Default invocation → table + wall-clock summary."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main([])
        self.assertEqual(rc, 0)
        body = out.getvalue()
        self.assertIn("/ceo-boot digest", body)
        self.assertIn("Wall-clock:", body)

    def test_main_short(self):
        """--short → counts header + non-green surfaces."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main(["--short"])
        self.assertEqual(rc, 0)

    def test_main_cached(self):
        """--cached: cold miss → run, then warm hit."""
        # First run: cold miss; full digest path
        out1 = io.StringIO()
        with redirect_stdout(out1), redirect_stderr(io.StringIO()):
            rc1 = _mod.main(["--cached"])
        self.assertEqual(rc1, 0)
        # Second run: should hit
        out2 = io.StringIO()
        with redirect_stdout(out2), redirect_stderr(io.StringIO()):
            rc2 = _mod.main(["--cached"])
        self.assertEqual(rc2, 0)
        body2 = out2.getvalue()
        self.assertIn("--cached HIT", body2)

    def test_main_json_payload_schema(self):
        """--json output includes all required keys."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main(["--json"])
        self.assertEqual(rc, 0)
        body = out.getvalue().strip()
        idx = body.find("{")
        self.assertGreaterEqual(idx, 0)
        payload = json.loads(body[idx:])
        for k in ("elapsed_ms", "gate_pass", "checks_total",
                  "checks_failed", "recommendations", "results"):
            self.assertIn(k, payload, f"--json missing key {k}")

    def test_main_bench_renders_markdown(self):
        """--bench → markdown table by default."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main(["--bench", "--bench-n", "2"])
        self.assertEqual(rc, 0)
        body = out.getvalue()
        self.assertIn("/ceo-boot --bench", body)
        self.assertIn("| iter |", body)

    def test_main_bench_json(self):
        """--bench --bench-json → JSON report."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main(["--bench", "--bench-n", "2", "--bench-json"])
        self.assertEqual(rc, 0)
        body = out.getvalue().strip()
        idx = body.find("{")
        self.assertGreaterEqual(idx, 0)
        payload = json.loads(body[idx:])
        self.assertIn("iterations", payload)
        self.assertIn("summary", payload)

    def test_main_verbose_includes_tier_a(self):
        """--verbose → digest table contains Tier-A check rows."""
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            rc = _mod.main(["--verbose"])
        self.assertEqual(rc, 0)
        body = out.getvalue()
        self.assertIn("/ceo-boot digest", body)
        # At least one Tier-A name should appear
        tier_a_present = any(
            name in body for name, _ in _mod.TIER_A_CHECKS
        )
        self.assertTrue(tier_a_present, "Expected Tier-A check name in output")


# ----------------------------------------------------------------------------
# Sanity counts (helps gate floor of 30→75+ cumulative)
# ----------------------------------------------------------------------------


class TestSanityCounts(TestEnvContext):
    """Module-level invariants asserted as tests for visibility."""

    def test_aggregate_timeout_verbose_10s(self):
        self.assertEqual(_mod.AGGREGATE_TIMEOUT_VERBOSE_S, 10.0)

    def test_cache_hit_budget_200ms(self):
        self.assertEqual(_mod.CACHE_HIT_BUDGET_MS, 200.0)

    def test_cache_ttl_3600s(self):
        self.assertEqual(_mod.CACHE_TTL_S, 3600.0)

    def test_cache_file_size_cap_100kb(self):
        self.assertEqual(_mod.CACHE_FILE_SIZE_CAP_BYTES, 100 * 1024)

    def test_cache_dir_size_cap_10mb(self):
        self.assertEqual(_mod.CACHE_DIR_SIZE_CAP_BYTES, 10 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
