"""First-event batching must retain the synchronous durability boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from unittest import mock

from _lib import spool_writer as spool
from _lib.testing import TestEnvContext


class TestFirstAppendDurability(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        spool._reset_for_test()

    def tearDown(self) -> None:
        spool._reset_for_test()
        super().tearDown()

    def test_header_and_event_are_synced_together_before_commit(self) -> None:
        real_sync = os.fsync
        snapshots = []

        def sync(fd):
            path = spool._spool_path(os.getpid())
            self.assertEqual(os.fstat(fd).st_ino, path.stat().st_ino)
            rows = [json.loads(s) for s in path.read_text().splitlines()]
            self.assertTrue(rows[0]["_spool_header"])
            self.assertEqual(rows[-1]["marker"], "durable")
            self.assertEqual(rows[0]["_spool_uuid"], rows[-1]["spool_uuid"])
            self.assertFalse(spool._LAST_APPEND_SUCCEEDED)
            ops = [json.loads(s)["op"] for s in spool._JOURNAL_BUFFER[os.getpid()]]
            self.assertEqual(ops, ["begin"])
            real_sync(fd)
            snapshots.append(rows)

        with mock.patch.object(spool.os, "fsync", side_effect=sync):
            spool.spool_append({"action": "agent_spawn", "marker": "durable"})
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(len(snapshots[0]), 2)
        self.assertTrue(spool._LAST_APPEND_SUCCEEDED)
        self.assertEqual([json.loads(s)["op"] for s in spool._JOURNAL_BUFFER[os.getpid()]],
                         ["begin", "commit"])

    def test_sync_failure_never_commits_or_acknowledges_event(self) -> None:
        with mock.patch.object(spool.os, "fsync", side_effect=OSError("disk failure")):
            spool.spool_append({"action": "agent_spawn", "marker": "uncommitted"})
        self.assertFalse(spool._LAST_APPEND_SUCCEEDED)
        self.assertEqual([json.loads(s)["op"] for s in spool._JOURNAL_BUFFER[os.getpid()]],
                         ["begin"])

    def test_standalone_header_still_syncs(self) -> None:
        with mock.patch.object(spool.os, "fsync", wraps=os.fsync) as sync:
            header = spool._ensure_spool_header(os.getpid())
        self.assertEqual(sync.call_count, 1)
        self.assertTrue(header["_spool_header"])

    def test_existing_header_does_not_remove_later_event_syncs(self) -> None:
        with mock.patch.object(spool.os, "fsync", wraps=os.fsync) as sync:
            for n in range(3):
                spool.spool_append({"action": "agent_spawn", "n": n})
                self.assertTrue(spool._LAST_APPEND_SUCCEEDED)
                self.assertEqual(sync.call_count, n + 1)
        rows = [json.loads(s) for s in spool._spool_path(os.getpid()).read_text().splitlines()]
        self.assertEqual([r["n"] for r in rows[1:]], [0, 1, 2])

    def test_crash_after_sync_before_commit_recovers_event_exactly_once(self) -> None:
        self._check_crash_recovery(crash_at_sync=True)

    def test_acknowledged_event_survives_exit_without_exit_handlers(self) -> None:
        self._check_crash_recovery(crash_at_sync=False)

    def _check_crash_recovery(self, *, crash_at_sync: bool) -> None:
        from _lib import audit_hmac
        self.audit_dir.chmod(0o700)
        audit_hmac._reset_key_cache_for_test()
        self.addCleanup(audit_hmac._reset_key_cache_for_test)
        audit_hmac.get_or_create_key()
        hooks = Path(__file__).resolve().parents[1]
        script = """
import os, sys
sys.path.insert(0, sys.argv[1])
from _lib import spool_writer as spool
if sys.argv[2] == 'sync':
    real_sync = os.fsync
    def sync(fd):
        real_sync(fd)
        os._exit(71)
    spool.os.fsync = sync
spool.spool_append({'action': 'agent_spawn', 'marker': 'crash-survivor'})
os._exit(72 if spool._LAST_APPEND_SUCCEEDED else 73)
"""
        child = subprocess.run([sys.executable, "-c", script, str(hooks),
                                "sync" if crash_at_sync else "ack"],
                               capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 71 if crash_at_sync else 72, child.stderr)
        first = spool.drain_now(force=True)
        second = spool.drain_now(force=True)
        self.assertTrue(first.ok, first.error)
        self.assertTrue(second.ok, second.error)
        rows = [json.loads(s) for s in spool._canonical_log_path().read_text().splitlines()]
        matches = [r for r in rows if r.get("marker") == "crash-survivor"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(len(matches[0]["hmac"]), 64)
        verified = audit_hmac.verify_chain(spool._canonical_log_path())
        self.assertTrue(verified.is_intact, verified)
