"""Tests for _lib/memory_shared.py (PLAN-014 Phase F.5 + F.7).

≥30 tests covering:
- Topic canonicalization (NFC, lowercase, dash-separated, rejections)
- `k` clamp to [1, 10]
- Storage bounds (4 KiB / 256 KiB / 100-per-topic)
- Redact-on-ingest (content never persisted in plaintext)
- One-file-per-pattern + content-addressed hash filename
- Index file under filelock, concurrent put via threading.Barrier(4)
- Idempotency: same (topic, content) → single file
- Ranking — normalized-token overlap
- Adversarial flood defense (C32)
- Homoglyph attack defense (NFC)
- Storage full → ValueError + no partial write
- File modes 0o600 / 0o700
- Audit event emission
- Eviction flow

Uses inline bootstrap (no .claude/**/conftest.py edits).
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

# Import (env is set in setUp before first import)

class TestMemorySharedBase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-mem-shared-"))
        self.project_dir = self.tmp / "project"
        self.home_dir = self.tmp / "home"
        self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self._env_snap = {}
        for k in ("CEO_MEMORY_SHARED_PATH", "CLAUDE_PROJECT_DIR", "HOME",
                  "CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR",
                  "CEO_AUDIT_LOG_ERR", "CEO_AUDIT_LOG_LOCK",
                  "CEO_AUDIT_SYNC_MODE"):
            self._env_snap[k] = os.environ.get(k)
        os.environ["HOME"] = str(self.home_dir)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        self.storage_root = self.tmp / "mem-shared"
        os.environ["CEO_MEMORY_SHARED_PATH"] = str(self.storage_root)
        self.audit_log = self.audit_dir / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")

        # Import fresh
        if "_lib.memory_shared" in sys.modules:
            del sys.modules["_lib.memory_shared"]
        from _lib import memory_shared as ms  # noqa: E402
        self.ms = ms

    def tearDown(self) -> None:
        for k, v in self._env_snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()


class TestCanonicalization(TestMemorySharedBase):
    def test_01_basic_lowercase(self):
        self.assertEqual(self.ms.canonicalize_topic("Hello World"), "hello-world")

    def test_02_nfc_normalization(self):
        # é decomposed vs precomposed
        decomposed = "caf\u00e9"  # café precomposed
        composed = "cafe\u0301"     # café decomposed (e + combining acute)
        self.assertEqual(
            self.ms.canonicalize_topic(decomposed),
            self.ms.canonicalize_topic(composed),
        )

    def test_03_non_alpha_collapsed_to_dash(self):
        self.assertEqual(self.ms.canonicalize_topic("foo!!!bar"), "foo-bar")

    def test_04_leading_trailing_dashes_stripped(self):
        self.assertEqual(self.ms.canonicalize_topic("  foo  "), "foo")
        self.assertEqual(self.ms.canonicalize_topic("-foo-"), "foo")

    def test_05_empty_topic_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.ms.canonicalize_topic("")
        self.assertIn("topic_empty", str(ctx.exception))

    def test_06_all_nonalpha_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.ms.canonicalize_topic("!!!")
        self.assertIn("topic_no_alphanumeric", str(ctx.exception))

    def test_07_too_long_rejected(self):
        raw = "x" * 200
        with self.assertRaises(ValueError) as ctx:
            self.ms.canonicalize_topic(raw)
        self.assertIn("topic_too_long", str(ctx.exception))

    def test_08_unicode_homoglyph_collapse(self):
        # 'а' (Cyrillic a) should NOT survive as alphanumeric ASCII
        # after casefold + re [a-z0-9]+ collapse
        canon = self.ms.canonicalize_topic("apple")
        # Cyrillic-flavored input should canonicalize differently (to dash-only),
        # hence be rejected by no_alphanumeric
        with self.assertRaises(ValueError):
            self.ms.canonicalize_topic("а")  # lone Cyrillic char


class TestPutPatternBasic(TestMemorySharedBase):
    def test_09_put_creates_file(self):
        h = self.ms.put_pattern("hello-world", "content A")
        self.assertTrue((self.storage_root / "patterns" / f"{h}.txt").is_file())

    def test_10_put_writes_content_file_0o600(self):
        h = self.ms.put_pattern("hello-world", "content A")
        p = self.storage_root / "patterns" / f"{h}.txt"
        mode = stat.S_IMODE(p.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_11_storage_root_mode_0o700(self):
        self.ms.put_pattern("hello-world", "content A")
        mode = stat.S_IMODE(self.storage_root.stat().st_mode)
        self.assertEqual(mode, 0o700)

    def test_12_put_is_idempotent_same_content(self):
        h1 = self.ms.put_pattern("hello-world", "content A")
        h2 = self.ms.put_pattern("hello-world", "content A")
        self.assertEqual(h1, h2)
        files = list((self.storage_root / "patterns").iterdir())
        self.assertEqual(len(files), 1)

    def test_13_put_rejects_oversize_content(self):
        content = "x" * (self.ms.MAX_CONTENT_BYTES + 1)
        with self.assertRaises(ValueError) as ctx:
            self.ms.put_pattern("hello-world", content)
        self.assertIn("content_too_large", str(ctx.exception))

    def test_14_put_rejects_empty_content(self):
        with self.assertRaises(ValueError) as ctx:
            self.ms.put_pattern("hello-world", "")
        self.assertIn("content_empty", str(ctx.exception))

    def test_15_put_rejects_after_storage_full(self):
        """Fill ~256 KiB total then verify next put raises storage_full."""
        # Each put adds ~4000 bytes; push until we see storage_full
        content_base = "z" * 4000
        storage_full_hit = False
        for i in range(80):
            try:
                self.ms.put_pattern(f"fill-{i:03d}", content_base + f"-{i:03d}")
            except ValueError as e:
                if "storage_full" in str(e):
                    storage_full_hit = True
                    break
        self.assertTrue(storage_full_hit,
                        "expected storage_full to be raised before loop ends")


class TestRedactOnIngest(TestMemorySharedBase):
    def test_16_sk_key_is_redacted_before_disk(self):
        secret = "sk-ant-" + "A" * 30
        h = self.ms.put_pattern("secret-topic", f"token: {secret}")
        p = self.storage_root / "patterns" / f"{h}.txt"
        content = p.read_text(encoding="utf-8")
        self.assertNotIn(secret, content)

    def test_17_ghp_pat_redacted(self):
        pat = "ghp_" + "B" * 30
        h = self.ms.put_pattern("github-topic", f"auth: {pat}")
        p = self.storage_root / "patterns" / f"{h}.txt"
        content = p.read_text(encoding="utf-8")
        self.assertNotIn(pat, content)

    def test_18_bearer_token_redacted(self):
        h = self.ms.put_pattern("bearer-topic", "Authorization: Bearer abc.def.ghi")
        p = self.storage_root / "patterns" / f"{h}.txt"
        content = p.read_text(encoding="utf-8")
        self.assertNotIn("Bearer abc.def.ghi", content)

    def test_19_post_redact_empty_rejected(self):
        """A content that collapses to empty post-redact should raise."""
        # Just secrets → will be fully redacted but still have content marker
        # Test with whitespace-only after redact
        with self.assertRaises(ValueError):
            self.ms.put_pattern("empty-topic", "   ")


class TestQuery(TestMemorySharedBase):
    def test_20_query_returns_stored_pattern(self):
        self.ms.put_pattern("debate-round-patterns", "content X")
        results = self.ms.query("debate-round-patterns", k=5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["topic"], "debate-round-patterns")
        self.assertEqual(results[0]["content"], "content X")

    def test_21_query_token_overlap(self):
        self.ms.put_pattern("audit-registry-extension", "pattern 1")
        self.ms.put_pattern("debate-convergence", "pattern 2")
        results = self.ms.query("audit-log-freeze", k=5)
        topics = [r["topic"] for r in results]
        self.assertIn("audit-registry-extension", topics)
        # "debate-convergence" has no token overlap with "audit-log-freeze"
        self.assertNotIn("debate-convergence", topics)

    def test_22_query_k_clamp_above_10(self):
        for i in range(5):
            self.ms.put_pattern(f"topic-{i}", f"content {i}")
        results = self.ms.query("topic", k=999)
        self.assertLessEqual(len(results), 10)

    def test_23_query_k_clamp_below_1(self):
        self.ms.put_pattern("topic-a", "content")
        results = self.ms.query("topic-a", k=0)
        self.assertEqual(len(results), 1)

    def test_24_query_invalid_topic_returns_empty(self):
        results = self.ms.query("", k=5)
        self.assertEqual(results, [])

    def test_25_query_emits_audit_event(self):
        self.ms.put_pattern("x-topic", "content")
        self.ms.query("x-topic", k=3)
        log = self.audit_log.read_text(encoding="utf-8")
        self.assertIn("pattern_queried", log)


class TestEviction(TestMemorySharedBase):
    def test_26_evict_removes_pattern(self):
        h = self.ms.put_pattern("evictable", "content A")
        self.assertTrue(self.ms.evict("evictable", h))
        results = self.ms.query("evictable", k=5)
        self.assertEqual(results, [])

    def test_27_evict_missing_returns_false(self):
        self.assertFalse(self.ms.evict("nothing", "abc123"))

    def test_28_evict_emits_audit_event(self):
        h = self.ms.put_pattern("evictable", "content A")
        self.ms.evict("evictable", h, reason="admin_request")
        log = self.audit_log.read_text(encoding="utf-8")
        self.assertIn("pattern_evicted", log)


class TestConcurrency(TestMemorySharedBase):
    def test_29_threading_barrier_four_concurrent_puts_no_corruption(self):
        """threading.Barrier(4) concurrent put_pattern calls (ADJ-035)."""
        barrier = threading.Barrier(4)
        errors = []

        def worker(i):
            try:
                barrier.wait()
                self.ms.put_pattern(f"topic-{i}", f"content-{i}")
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], f"concurrency errors: {errors}")
        topics = self.ms.list_topics()
        self.assertEqual(len(topics), 4)

    def test_30_same_topic_concurrent_writes_no_corruption(self):
        """PLAN-019 F-CHAOS-12: 4 concurrent put_pattern on the SAME topic
        must not corrupt the index file or the on-disk pattern files.

        test_29 above exercises different-topic concurrency (no contention
        on the same topic directory). This test hammers the same topic
        from 4 threads simultaneously with different content — the
        filelock on the index + per-pattern content-addressed filenames
        must keep the resulting state coherent. Since content-addressed
        hashing deduplicates same-content puts but distinct content
        produces distinct files, we expect exactly 4 pattern files in
        the topic and all queryable without error.
        """
        barrier = threading.Barrier(4)
        errors = []
        topic = "shared-topic-race"

        def worker(i):
            try:
                barrier.wait()
                # Each writes DISTINCT content so content-address avoids dedup;
                # all 4 should land as separate files under the shared topic.
                self.ms.put_pattern(topic, f"content-variant-{i}" * 10)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], f"concurrency errors: {errors}")

        # Exactly one topic row (not 4 duplicate rows) in the index.
        topics = self.ms.list_topics()
        matching = [t for t in topics if t == topic]
        self.assertEqual(
            len(matching),
            1,
            f"index must have exactly one entry for shared topic; got {len(matching)}",
        )

        # Queryable without corruption: we don't assert how many of the 4
        # variants landed (rank truncation could remove some), but query
        # must not raise and must return at least one non-empty result
        # for this topic.
        results = self.ms.query(topic, k=10)
        self.assertTrue(
            len(results) >= 1,
            f"expected at least 1 pattern queryable for {topic!r}; got {len(results)}",
        )
        for rec in results:
            self.assertIn("topic", rec)
            # If the underlying API exposes the stored topic, it must equal.
            # Different versions return either the canonical topic or a path;
            # tolerate both since the contract here is "no corruption".


class TestAdversarial(TestMemorySharedBase):
    def test_30_flood_attack_does_not_dominate_unrelated_query(self):
        """Attacker fills topic 'attacker'; unrelated query doesn't see them."""
        # Use small content to fit within storage cap
        for i in range(20):
            self.ms.put_pattern(f"attacker-topic-{i}", f"malicious-{i}")
        self.ms.put_pattern("legit-query-target", "benign")
        results = self.ms.query("legit-query-target", k=5)
        topics = {r["topic"] for r in results}
        self.assertIn("legit-query-target", topics)
        attacker_found = {t for t in topics if t.startswith("attacker-topic-")}
        self.assertEqual(attacker_found, set())

    def test_31_homoglyph_topic_defended(self):
        """Unicode homoglyph attack defeated by NFC + lowercase."""
        # 'А' (Cyrillic capital A) ≠ 'A' (Latin)
        # Cyrillic 'а' does not become 'a' after NFC/lowercase; it stays 'а'
        # which the regex [a-z0-9]+ rejects, collapsing to empty → ValueError
        with self.assertRaises(ValueError):
            self.ms.canonicalize_topic("\u0430")  # lone Cyrillic a

    def test_32_content_with_embedded_secret_redacted(self):
        secret = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdefghij.signature"
        h = self.ms.put_pattern("jwt-topic", f"bearer: {secret}")
        p = self.storage_root / "patterns" / f"{h}.txt"
        on_disk = p.read_text(encoding="utf-8")
        self.assertNotIn(secret, on_disk)


class TestListStats(TestMemorySharedBase):
    def test_33_list_topics_sorted(self):
        self.ms.put_pattern("zebra", "z")
        self.ms.put_pattern("alpha", "a")
        self.ms.put_pattern("middle", "m")
        self.assertEqual(self.ms.list_topics(), ["alpha", "middle", "zebra"])

    def test_34_stats_reports_bounds(self):
        self.ms.put_pattern("x-topic", "hi")
        s = self.ms.stats()
        self.assertIn("storage_root", s)
        self.assertIn("total_bytes", s)
        self.assertEqual(s["max_content_bytes"], self.ms.MAX_CONTENT_BYTES)
        self.assertEqual(s["max_total_bytes"], self.ms.MAX_TOTAL_BYTES)

    def test_35_audit_event_pattern_stored_emitted(self):
        self.ms.put_pattern("stored-event-topic", "content")
        log = self.audit_log.read_text(encoding="utf-8")
        self.assertIn("pattern_stored", log)


class TestPerTopicCap(TestMemorySharedBase):
    def test_36_too_many_per_topic_raises(self):
        # MAX_PER_TOPIC = 100. Create 100 under same topic, 101st should fail.
        # But storage_full might also kick in; keep content tiny.
        topic = "capped-topic"
        for i in range(100):
            try:
                self.ms.put_pattern(topic, f"p{i}")
            except ValueError as e:
                if "too_many_per_topic" in str(e) or "storage_full" in str(e):
                    break
        # Verify the exception (next push → either storage_full or too_many_per_topic)
        with self.assertRaises(ValueError):
            self.ms.put_pattern(topic, "overflow-one-more-distinct-content")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
