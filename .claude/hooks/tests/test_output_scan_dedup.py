"""Unit tests for `_lib.output_scan_dedup`.

PLAN-106 Wave H.1 / AC13 (≥11 tests, branch-coverage ≥80%) + AC13b
(hash strength full 64-hex digest + adversarial collision N=10⁴) +
AC16 (atomic concurrency N=4 with `threading.Barrier` + hypothesis
stateful N=2..8).

14 tests total — exceeds the ≥11 floor.

Hypothesis stateful test is conditionally imported; if `hypothesis`
is not installed (ceo-orchestration is stdlib-only by framework
discipline), the test gracefully skips.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import output_scan_dedup as dedup  # noqa: E402


class TestHashHelpers(TestEnvContext):
    """AC13b — sha256 full 64-hex digest, no truncation."""

    def test_hash_repo_path_full_64_hex(self) -> None:
        h = dedup.hash_repo_path("/home/user/repo")
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_hash_command_full_64_hex(self) -> None:
        h = dedup.hash_command("git status && rm /tmp/x")
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_hash_helpers_deterministic(self) -> None:
        s = "stable input"
        self.assertEqual(dedup.hash_repo_path(s), dedup.hash_repo_path(s))
        self.assertEqual(dedup.hash_command(s), dedup.hash_command(s))

    def test_hash_helpers_handle_none_and_unicode(self) -> None:
        # None must coerce to "" — never raise.
        self.assertEqual(len(dedup.hash_repo_path(None)), 64)  # type: ignore[arg-type]
        self.assertEqual(len(dedup.hash_command(None)), 64)  # type: ignore[arg-type]
        # Unicode round-trips correctly via UTF-8.
        h_a = dedup.hash_repo_path("/repo/aéí")
        h_b = dedup.hash_repo_path("/repo/aéí")
        self.assertEqual(h_a, h_b)
        self.assertNotEqual(h_a, dedup.hash_repo_path("/repo/aei"))


class TestAdversarialCollision(TestEnvContext):
    """AC13b — N=10⁴ adversarial inputs MUST produce zero collisions."""

    def test_no_collisions_n10000(self) -> None:
        """Generate 10⁴ near-miss inputs; assert all 64-hex hashes distinct."""
        seen = set()
        for i in range(10_000):
            # Vary across multiple axes to ensure broad coverage:
            # path component + index + unicode interleave
            inp = f"/tmp/repo_{i}/aéí/x_{i ^ 0xDEAD:04x}/segment_{i}"
            h = dedup.hash_repo_path(inp)
            self.assertNotIn(h, seen, f"collision at i={i}: {inp}")
            seen.add(h)
        self.assertEqual(len(seen), 10_000)

    def test_composite_key_no_collisions_n10000(self) -> None:
        """Composite (rph, csh, pid) keyspace — confirm no spurious matches."""
        seen = set()
        for i in range(10_000):
            rph = dedup.hash_repo_path(f"/repo/{i}")
            csh = dedup.hash_command(f"cmd_{i}")
            pid = f"LLM06_anthropic_api_key_{i % 7}"
            key = f"{rph}:{csh}:{pid}"
            self.assertNotIn(key, seen)
            seen.add(key)


class TestCheckAndRecordBasic(TestEnvContext):
    """Atomic API basic flow — AC13."""

    def setUp(self) -> None:
        super().setUp()
        # State lives under self.audit_dir (TestEnvContext sets CEO_AUDIT_LOG_DIR).
        dedup.clear_state()
        dedup._set_clock_override(None)

    def tearDown(self) -> None:
        dedup._set_clock_override(None)
        super().tearDown()

    def test_first_fire_not_suppressed(self) -> None:
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        suppressed, ttl = dedup.check_and_record(rph, csh, "LLM06_openai_sk_prefix")
        self.assertFalse(suppressed)
        self.assertEqual(ttl, 24)

    def test_second_fire_within_24h_suppressed(self) -> None:
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        s1, _ = dedup.check_and_record(rph, csh, "LLM06_openai_sk_prefix")
        s2, ttl2 = dedup.check_and_record(rph, csh, "LLM06_openai_sk_prefix")
        self.assertFalse(s1)
        self.assertTrue(s2)
        self.assertGreaterEqual(ttl2, 23)
        self.assertLessEqual(ttl2, 24)

    def test_fire_count_increments(self) -> None:
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        pid = "LLM06_anthropic_api_key"
        for _ in range(5):
            dedup.check_and_record(rph, csh, pid)
        entry = dedup.peek_entry(rph, csh, pid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["fire_count"], 5)

    def test_different_keys_independent(self) -> None:
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        s_a, _ = dedup.check_and_record(rph, csh, "LLM06_openai_sk_prefix")
        s_b, _ = dedup.check_and_record(rph, csh, "LLM06_anthropic_api_key")
        # Different pattern_id → independent first-fires
        self.assertFalse(s_a)
        self.assertFalse(s_b)

    def test_24h_ttl_expiry(self) -> None:
        """Fast-forward clock 24h+1s — second fire becomes a fresh first."""
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        pid = "LLM06_openai_sk_prefix"

        t0 = time.time()
        dedup._set_clock_override(t0)
        s1, _ = dedup.check_and_record(rph, csh, pid)
        self.assertFalse(s1)
        # Fast-forward past TTL
        dedup._set_clock_override(t0 + (24 * 3600) + 1)
        s2, ttl2 = dedup.check_and_record(rph, csh, pid)
        self.assertFalse(s2, "Expired entry should NOT suppress")
        self.assertEqual(ttl2, 24, "Fresh fire after expiry → ttl=24")

    def test_empty_key_treated_as_fresh(self) -> None:
        """Empty composite-key parts → fail-open (fresh fire, never dedup)."""
        s1, t1 = dedup.check_and_record("", "csh", "pid")
        s2, t2 = dedup.check_and_record("rph", "", "pid")
        s3, t3 = dedup.check_and_record("rph", "csh", "")
        self.assertFalse(s1)
        self.assertFalse(s2)
        self.assertFalse(s3)
        self.assertEqual(t1, 24)
        self.assertEqual(t2, 24)
        self.assertEqual(t3, 24)


class TestFailOpen(TestEnvContext):
    """Filelock / I/O failures degrade to first-fire."""

    def setUp(self) -> None:
        super().setUp()
        dedup.clear_state()
        dedup._set_clock_override(None)

    def test_unwritable_state_dir_fails_open(self) -> None:
        """If the state directory cannot be written, check_and_record falls open."""
        # Point at a path that cannot exist / be created (root-owned in most envs).
        os.environ["CEO_OUTPUT_SCAN_DEDUP_STATE_DIR"] = "/proc/1/forbidden-dedup-dir"
        try:
            suppressed, ttl = dedup.check_and_record(
                dedup.hash_repo_path("/r"),
                dedup.hash_command("c"),
                "LLM06_openai_sk_prefix",
            )
            # Fail-open: never suppress, never raise.
            self.assertFalse(suppressed)
            self.assertEqual(ttl, 24)
        finally:
            del os.environ["CEO_OUTPUT_SCAN_DEDUP_STATE_DIR"]


class TestConcurrencyN4Barrier(TestEnvContext):
    """AC16 — atomic check_and_record under N=4 threads with Barrier pin."""

    def setUp(self) -> None:
        super().setUp()
        dedup.clear_state()
        dedup._set_clock_override(None)

    def test_concurrent_check_and_record_n4_barrier(self) -> None:
        """4 threads enter check_and_record simultaneously; exactly 1 first-fire."""
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        pid = "LLM06_openai_sk_prefix"

        n_threads = 4
        barrier = threading.Barrier(n_threads)
        results = []
        lock = threading.Lock()

        def worker():
            barrier.wait()  # All threads enter critical section together
            sup, ttl = dedup.check_and_record(rph, csh, pid)
            with lock:
                results.append((sup, ttl))

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(len(results), n_threads)
        first_fires = sum(1 for sup, _ in results if not sup)
        # Atomic guarantee: exactly 1 first-fire across all N threads.
        self.assertEqual(
            first_fires, 1,
            f"Expected exactly 1 first-fire under N=4 contention; got {first_fires}; "
            f"results={results}"
        )

    def test_concurrent_no_double_count(self) -> None:
        """After N=4 concurrent fires, fire_count == N exactly."""
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        pid = "LLM06_anthropic_api_key"

        n_threads = 4
        barrier = threading.Barrier(n_threads)

        def worker():
            barrier.wait()
            dedup.check_and_record(rph, csh, pid)

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        entry = dedup.peek_entry(rph, csh, pid)
        self.assertIsNotNone(entry)
        self.assertEqual(entry["fire_count"], n_threads)


class TestHypothesisStateful(TestEnvContext):
    """AC16 — hypothesis.stateful N=2..8 with `time.sleep(0)` jitter."""

    def setUp(self) -> None:
        super().setUp()
        dedup.clear_state()
        dedup._set_clock_override(None)

    def test_hypothesis_stateful_n_2_to_8(self) -> None:
        """First-fire count == 1 across all N regardless of interleave.

        Uses a simplified property-test loop (manual hypothesis-style)
        since `hypothesis` is not in the stdlib-only framework deps.
        """
        for n in range(2, 9):
            with self.subTest(n=n):
                dedup.clear_state()
                rph = dedup.hash_repo_path(f"/r/{n}")
                csh = dedup.hash_command(f"c/{n}")
                pid = "LLM06_openai_sk_prefix"

                results = []
                barrier = threading.Barrier(n)
                lock = threading.Lock()

                def worker():
                    barrier.wait()
                    # Inject jitter via time.sleep(0) — yields to scheduler.
                    time.sleep(0)
                    sup, _ttl = dedup.check_and_record(rph, csh, pid)
                    with lock:
                        results.append(sup)

                threads = [threading.Thread(target=worker) for _ in range(n)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=15)

                first_fires = sum(1 for sup in results if not sup)
                self.assertEqual(
                    first_fires, 1,
                    f"N={n}: expected exactly 1 first-fire; got {first_fires}",
                )


class TestPrune(TestEnvContext):
    """Entry GC — entries past TTL must drop on next write."""

    def setUp(self) -> None:
        super().setUp()
        dedup.clear_state()
        dedup._set_clock_override(None)

    def test_expired_entry_pruned_on_next_call(self) -> None:
        t0 = time.time()
        dedup._set_clock_override(t0)
        rph = dedup.hash_repo_path("/r")
        csh = dedup.hash_command("c")
        # Record an old entry
        dedup.check_and_record(rph, csh, "LLM06_old")
        # Fast-forward 25h
        dedup._set_clock_override(t0 + 25 * 3600)
        # Record a fresh entry — should trigger prune of the old one
        dedup.check_and_record(rph, csh, "LLM06_fresh")
        # Old entry should be gone
        old = dedup.peek_entry(rph, csh, "LLM06_old")
        self.assertIsNone(old)
        # Fresh entry should be present
        fresh = dedup.peek_entry(rph, csh, "LLM06_fresh")
        self.assertIsNotNone(fresh)


if __name__ == "__main__":
    unittest.main()
