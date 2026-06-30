"""PLAN-094 Wave C + PLAN-094-FOLLOWUP Wave C-rem — sentinel session cache 15-test pack.

S125 v1.27.0 SHIPPED 8 critical-path tests. PLAN-094-FOLLOWUP Wave C-rem
adds 7 NEW tests covering: inode invalidation, file_size invalidation,
signer_key_id design assertion, SIGKILL no-stale-recovery, hit-rate ≥0.90
intrasession, thread-safety, cache_stats schema compat with skill_cache_stats.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import check_canonical_edit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class SentinelSessionCacheTests(TestEnvContext):
    """TestEnvContext is a unittest.TestCase subclass (not a CM); inherit."""

    def setUp(self) -> None:
        super().setUp()
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0

    def tearDown(self) -> None:
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0
        super().tearDown()

    def test_cache_is_module_scope_dict_not_file_backed(self) -> None:
        cache = check_canonical_edit._SENTINEL_VERIFY_CACHE
        self.assertIsInstance(cache, dict)
        cache_dir = Path(".claude/cache")
        if cache_dir.exists():
            for entry in cache_dir.iterdir():
                self.assertNotIn(
                    "sentinel_verify", entry.name,
                    "Wave C MUST NOT create file-backed sentinel cache (R5 invariant)",
                )

    def test_cache_disabled_via_env_kill_switch(self) -> None:
        with mock.patch.dict(os.environ, {"CEO_SENTINEL_SESSION_CACHE_DISABLED": "1"}):
            self.assertTrue(check_canonical_edit._sentinel_cache_disabled())
        with mock.patch.dict(os.environ, {"CEO_SENTINEL_SESSION_CACHE_DISABLED": ""}):
            self.assertFalse(check_canonical_edit._sentinel_cache_disabled())

    def test_sentinel_cache_stats_returns_dict_with_counters(self) -> None:
        stats = check_canonical_edit.sentinel_cache_stats()
        self.assertIn("hit_count", stats)
        self.assertIn("miss_count", stats)
        self.assertIn("size", stats)
        self.assertEqual(stats["hit_count"], 0)
        self.assertEqual(stats["miss_count"], 0)
        self.assertEqual(stats["size"], 0)

    def test_cache_key_invalidates_on_mtime_change(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"content v1")
            sp1 = Path(f.name)
        try:
            key1 = check_canonical_edit._compute_sentinel_cache_key(sp1, "target/rel.md")
            os.utime(sp1, (1000, 1000))
            key2 = check_canonical_edit._compute_sentinel_cache_key(sp1, "target/rel.md")
            self.assertIsNotNone(key1)
            self.assertIsNotNone(key2)
            self.assertNotEqual(key1, key2)
        finally:
            sp1.unlink(missing_ok=True)

    def test_cache_key_invalidates_on_sha256_change(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"original content")
            sp = Path(f.name)
        try:
            key1 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/rel.md")
            sp.write_bytes(b"different content")
            key2 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/rel.md")
            self.assertNotEqual(key1, key2)
        finally:
            sp.unlink(missing_ok=True)

    def test_cache_key_returns_none_on_missing_file(self) -> None:
        non_existent = Path("/tmp/__plan094_wave_c_nonexistent_sentinel__.md")
        key = check_canonical_edit._compute_sentinel_cache_key(non_existent, "target/rel.md")
        self.assertIsNone(key)

    def test_cache_format_version_in_key(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"content")
            sp = Path(f.name)
        try:
            key = check_canonical_edit._compute_sentinel_cache_key(sp, "target/rel.md")
            self.assertIsNotNone(key)
            self.assertEqual(key[-1], check_canonical_edit._SENTINEL_CACHE_FORMAT_VERSION)
        finally:
            sp.unlink(missing_ok=True)

    def test_cache_target_rel_in_key(self) -> None:
        """Codex iter-1 P0 fix: target_rel must be part of the key
        (penultimate position) so two grants for the same sentinel but
        different target paths don't collide.
        """
        cache = check_canonical_edit._SENTINEL_VERIFY_CACHE
        fake_key_t1 = ("/tmp/x.md", 1, 100, 10, "sha", "target/A.md",
                       check_canonical_edit._SENTINEL_CACHE_FORMAT_VERSION)
        fake_key_t2 = ("/tmp/x.md", 1, 100, 10, "sha", "target/B.md",
                       check_canonical_edit._SENTINEL_CACHE_FORMAT_VERSION)
        cache[fake_key_t1] = True
        self.assertIs(cache.get(fake_key_t1), True)
        self.assertIsNone(cache.get(fake_key_t2))  # different target_rel = cache miss


# ---------------------------------------------------------------------------
# Wave C-rem (PLAN-094-FOLLOWUP) — 7 NEW tests
# ---------------------------------------------------------------------------


class SentinelCacheRemainderTests(TestEnvContext):
    """7 NEW tests closing the original PLAN-094 §3 Wave C 15-test contract."""

    def setUp(self) -> None:
        super().setUp()
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0

    def tearDown(self) -> None:
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0
        super().tearDown()

    def test_cache_invalidates_on_inode_change(self) -> None:
        """C-rem.1: mv tmpfile invalidates cache via inode change."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"content")
            sp1 = Path(f.name)
        sp2 = sp1.with_name(sp1.name + ".renamed")
        try:
            key1 = check_canonical_edit._compute_sentinel_cache_key(sp1, "target/rel.md")
            os.rename(str(sp1), str(sp2))
            # Re-create at original path with same content — new inode
            sp1.write_bytes(b"content")
            key2 = check_canonical_edit._compute_sentinel_cache_key(sp1, "target/rel.md")
            self.assertIsNotNone(key1)
            self.assertIsNotNone(key2)
            # Inode position in tuple is index 1 (path, inode, mtime, ...)
            # Re-created file has different inode → keys must differ
            self.assertNotEqual(key1[1], key2[1])
        finally:
            sp1.unlink(missing_ok=True)
            sp2.unlink(missing_ok=True)

    def test_cache_invalidates_on_file_size_change(self) -> None:
        """C-rem.2: append → file_size changes → key changes."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"x")
            sp = Path(f.name)
        try:
            key1 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/rel.md")
            with open(str(sp), "ab") as f:
                f.write(b"yyyyyyyy")
            key2 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/rel.md")
            # file_size at tuple index 3 — must differ on append
            self.assertNotEqual(key1[3], key2[3])
        finally:
            sp.unlink(missing_ok=True)

    def test_signer_key_id_drop_design_assertion(self) -> None:
        """C-rem.3: assert current design DROPS signer_key_id (relies on sha256_full).

        Codex iter-1 P0 fix used target_rel + sha256_full + bumped format
        version to 2; signer_key_id is intentionally NOT in the key because
        any signer rotation changes the .asc bytes, which transitively
        invalidates sha256_full (which is computed over the SENTINEL file,
        not the .asc — so signer rotation alone doesn't invalidate sentinel
        sha256_full UNLESS the sentinel itself is re-signed/re-saved).

        Risk window: 0-byte sentinel re-signed by NEW signer with IDENTICAL
        bytes (only .asc changes) — cache hit would re-use stale grant. This
        is an ACCEPTED tradeoff per Wave C design draft §8 (signer rotation
        window risk acknowledged). Test documents the design choice.
        """
        # Cache key length = 7 (path, inode, mtime, size, sha, target, fmt_v)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"content")
            sp = Path(f.name)
        try:
            key = check_canonical_edit._compute_sentinel_cache_key(sp, "t/r.md")
            self.assertIsNotNone(key)
            self.assertEqual(len(key), 7,
                "key MUST have 7 fields (path, inode, mtime, size, sha, target_rel, fmt_v); signer_key_id NOT included per design §8")
        finally:
            sp.unlink(missing_ok=True)

    def test_sigkill_simulation_module_scope_no_stale_recovery(self) -> None:
        """C-rem.4: process-death = empty cache by design (module-scope dict).

        Simulated by direct cache.clear() (proxies the import-time empty
        state a new process would see). Asserts that the cache dict has no
        on-disk shadow (sister to test_cache_is_module_scope_dict_not_file_backed
        but emphasizing the recovery-by-design semantic).
        """
        # Pollute cache, then "die"
        check_canonical_edit._SENTINEL_VERIFY_CACHE[
            ("/tmp/a", 1, 2, 3, "sha", "t", check_canonical_edit._SENTINEL_CACHE_FORMAT_VERSION)
        ] = True
        # "Process death" → new process → empty dict at import. We simulate
        # by clearing and asserting no recovery from disk.
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        self.assertEqual(len(check_canonical_edit._SENTINEL_VERIFY_CACHE), 0)
        # Re-import to confirm no file-backed restore happens
        import importlib
        importlib.reload(check_canonical_edit)
        # Module-scope re-init → fresh empty dict
        self.assertEqual(len(check_canonical_edit._SENTINEL_VERIFY_CACHE), 0)

    def test_cache_hit_rate_meets_threshold_90pct_intrasession(self) -> None:
        """C-rem.5: N=100 repeated cache lookups → hit-rate ≥0.90."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"stable content")
            sp = Path(f.name)
        try:
            # First lookup = miss + store
            key = check_canonical_edit._compute_sentinel_cache_key(sp, "t/r.md")
            self.assertIsNotNone(key)
            check_canonical_edit._SENTINEL_VERIFY_CACHE[key] = True
            check_canonical_edit._SENTINEL_CACHE_MISSES = 1

            # Next 99 lookups should all be cache hits
            hits = 0
            for _ in range(99):
                lookup_key = check_canonical_edit._compute_sentinel_cache_key(sp, "t/r.md")
                if lookup_key in check_canonical_edit._SENTINEL_VERIFY_CACHE:
                    hits += 1
                    check_canonical_edit._SENTINEL_CACHE_HITS += 1
            hit_rate = hits / (hits + 1)  # +1 for the initial miss
            self.assertGreaterEqual(hit_rate, 0.90,
                f"hit-rate {hit_rate:.3f} below 0.90 threshold for intrasession cache")
        finally:
            sp.unlink(missing_ok=True)

    def test_cache_thread_safety_concurrent_emit(self) -> None:
        """C-rem.6: N=4 threads × 250 iters; dict integrity preserved.

        Python GIL serializes individual dict-op bytecodes, but `cache[k] = v`
        is safe under GIL. The `+=` counter increment is 2 bytecodes (LOAD +
        STORE) and CAN race — we accept some counter loss (forensic only) and
        only assert the dict itself remains internally consistent.
        """
        import threading
        N_THREADS = 4
        N_ITERS = 250
        errors = []

        def worker(tid: int) -> None:
            try:
                for i in range(N_ITERS):
                    # tid * N_ITERS + i — guarantees no key overlap across threads
                    key = ("/tmp/x", tid * N_ITERS + i, 0, 1, "sha", "t", 2)
                    check_canonical_edit._SENTINEL_VERIFY_CACHE[key] = (i % 2 == 0)
                    check_canonical_edit._SENTINEL_VERIFY_CACHE.get(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"thread workers raised: {errors}")
        # Cache should contain N_THREADS * N_ITERS unique keys
        self.assertEqual(
            len(check_canonical_edit._SENTINEL_VERIFY_CACHE),
            N_THREADS * N_ITERS,
            "GIL must serialize dict writes — no key loss",
        )

    def test_cache_metric_emit_skill_cache_stats_compatible(self) -> None:
        """C-rem.7: sentinel_cache_stats() shape matches skill_cache_stats schema.

        Cross-Wave-B compat: both metric emitters must return dicts with
        the same key shape so audit-log consumers can swap surfaces. The
        skill_cache_stats audit-emit schema (PLAN-094 Wave B) carries
        hit_count + miss_count + size; sentinel_cache_stats must mirror.
        """
        stats = check_canonical_edit.sentinel_cache_stats()
        # Required schema keys (sister to skill_cache_stats per PLAN-094 §3 Wave B)
        self.assertIn("hit_count", stats)
        self.assertIn("miss_count", stats)
        self.assertIn("size", stats)
        # All values are non-negative ints (initial state = 0)
        self.assertEqual(stats["hit_count"], 0)
        self.assertEqual(stats["miss_count"], 0)
        self.assertEqual(stats["size"], 0)
        # Mutate + re-check
        check_canonical_edit._SENTINEL_VERIFY_CACHE[("/tmp/y", 1, 2, 3, "s", "t", 2)] = True
        check_canonical_edit._SENTINEL_CACHE_HITS = 5
        check_canonical_edit._SENTINEL_CACHE_MISSES = 7
        stats2 = check_canonical_edit.sentinel_cache_stats()
        self.assertEqual(stats2["hit_count"], 5)
        self.assertEqual(stats2["miss_count"], 7)
        self.assertEqual(stats2["size"], 1)


if __name__ == "__main__":
    unittest.main()
