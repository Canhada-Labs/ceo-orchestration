"""Dynamic-lookup contracts for the modular spool-writer facade."""
from __future__ import annotations

import json
import os
from unittest import mock

from _lib import spool_writer as spool
from _lib.testing import TestEnvContext


class TestSpoolWriterModularFacade(TestEnvContext):
    def setUp(self):
        super().setUp()
        spool._reset_for_test()
        self.addCleanup(spool._reset_for_test)

    def test_append_uses_facade_header_helper(self):
        seen = []
        original = spool._ensure_spool_header

        def wrapped(pid, *args, **kwargs):
            seen.append(pid)
            return original(pid, *args, **kwargs)

        with mock.patch.object(spool, "_ensure_spool_header", wrapped):
            spool.spool_append({"action": "facade_header"})
        self.assertEqual(seen, [os.getpid()])
        self.assertTrue(spool.last_append_succeeded())
        rows = [json.loads(line) for line in spool._spool_path(os.getpid()).read_text().splitlines()]
        self.assertEqual(rows[-1]["action"], "facade_header")

    def test_reset_mutates_facade_owned_caches(self):
        spool._SPOOL_HEADER_CACHE[999] = {"_spool_uuid": "0" * 16}
        spool._ORDINAL_COUNTER[999] = 3
        spool._reset_for_test()
        self.assertEqual(spool._SPOOL_HEADER_CACHE, {})
        self.assertEqual(spool._ORDINAL_COUNTER, {})

    def test_append_then_drain_preserves_effect(self):
        spool.spool_append({"action": "facade_drain", "probe": 1})
        stats = spool.drain_now(force=True)
        self.assertTrue(stats.ok)
        self.assertEqual(stats.appended, 1)
        rows = [json.loads(line) for line in spool._canonical_log_path().read_text().splitlines()]
        self.assertEqual([(row["action"], row["probe"]) for row in rows], [("facade_drain", 1)])
