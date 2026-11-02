"""FU144 regression contract for deadline-bounded spool exits."""
from __future__ import annotations

import os
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import signal
import sys
import time
from unittest import mock

from _subprocess_helpers import run_in_process_group
from _lib import spool_writer
from _lib.testing import TestEnvContext


def _deadline_probe_source() -> str:
    """Synthetic hook that makes any exit drain/flush leave a tripwire."""
    return """
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ[\"REAL_HOOKS\"])
from _lib import spool_writer

tripwire = Path(os.environ[\"TRIPWIRE\"])
def trip(*args, **kwargs):
    tripwire.write_text(\"exit-work\", encoding=\"utf-8\")

spool_writer.drain_now = trip
spool_writer._flush_journal_buffer = trip
spool_writer.install_exit_handlers()
"""


class TestSpoolStateAmend4(TestEnvContext):
    """An armed hook deadline records pending work without draining it."""

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_for_test()

    def tearDown(self) -> None:
        spool_writer._reset_for_test()
        super().tearDown()

    def test_atexit_deadline_fu144_skips_drain_and_journal_flush(self) -> None:
        """ADR-055-AMEND-4: an active deadline has a zero-drain exit path."""
        with mock.patch.dict(os.environ, {"CEO_AUDIT_SYNC_MODE": ""}):
            spool_writer.set_exit_deadline(time.monotonic() + 1.0)
            with mock.patch.object(spool_writer, "drain_now") as drain, \
                 mock.patch.object(spool_writer, "_flush_journal_buffer") as flush:
                spool_writer._atexit_drain()
        drain.assert_not_called()
        flush.assert_not_called()
        self.assertIn("exit_deadline_skip source=atexit", self.read_audit_errors())

    def test_untimed_atexit_fu144_keeps_existing_drain_contract(self) -> None:
        """No armed deadline preserves the compatibility path for old callers."""
        with mock.patch.dict(os.environ, {"CEO_AUDIT_SYNC_MODE": ""}):
            with mock.patch.object(spool_writer, "drain_now") as drain, \
                 mock.patch.object(spool_writer, "_flush_journal_buffer") as flush:
                spool_writer._atexit_drain()
        drain.assert_called_once_with(force=True)
        flush.assert_called_once_with(os.getpid())

    def test_python_shim_deadline_fu144_skips_exit_work(self) -> None:
        """The real shim arms zero-drain for a normal synthetic hook exit."""
        real_hooks = Path(__file__).resolve().parents[1]
        hooks_dir = self.project_dir / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True)
        shim = hooks_dir / "_python-hook.sh"
        shutil.copy2(real_hooks / "_python-hook.sh", shim)
        (hooks_dir / "deadline_probe.py").write_text(
            _deadline_probe_source(), encoding="utf-8",
        )
        tripwire = self.project_dir / "exit-work.tripwire"
        with mock.patch.dict(os.environ, {
            "CEO_AUDIT_SYNC_MODE": "1", "CEO_HOOK_BOUNDED_EXIT": "",
        }):
            child = run_in_process_group(
                ["bash", str(shim), "deadline_probe.py"],
                capture_output=True,
                cwd=self.project_dir,
                env=self.subprocess_env(
                    REAL_HOOKS=str(real_hooks), TRIPWIRE=str(tripwire),
                ),
                timeout=10,
            )
        self.assertEqual(child.returncode, 0, child.stderr.decode())
        self.assertFalse(tripwire.exists())
        self.assertNotIn(b"Fatal Python error", child.stderr)


class TestF2IntegratedSubset(TestEnvContext):
    """Measured F2 subset; U2-A/B-dependent full stress stays blocked."""

    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_for_test()
        from _lib import audit_hmac
        self.audit_dir.chmod(0o700)
        audit_hmac._reset_key_cache_for_test()
        audit_hmac.get_or_create_key()

    def tearDown(self) -> None:
        spool_writer._reset_for_test()
        super().tearDown()

    def test_f2_wave1_fu144_set_equality_after_100_drains(self) -> None:
        """1,000 durable records reach canonical exactly once in 100 batches."""
        expected = set()
        for batch in range(100):
            for offset in range(10):
                spool_writer.spool_append({
                    "action": "agent_spawn", "f2_wave": 1,
                    "sequence": batch * 10 + offset,
                })
            rows = spool_writer._spool_path(os.getpid()).read_text().splitlines()[1:]
            expected.update(json.loads(row)["record_id"] for row in rows)
            stats = spool_writer.drain_now(force=True)
            self.assertTrue(stats.ok, stats.error)
        log_rows = [json.loads(row) for row in self.read_audit_log().splitlines()]
        matching = [row["record_id"] for row in log_rows if row.get("f2_wave") == 1]
        actual = set(matching)
        self.assertEqual(actual, expected)
        self.assertEqual(len(matching), 1000)
        self.assertEqual(len(actual), 1000)
        from _lib import audit_hmac
        self.assertTrue(audit_hmac.verify_chain(spool_writer._canonical_log_path()).is_intact)

    def test_f2_wave2_fu144_killed_writer_is_recovered_by_next_drain(self) -> None:
        """A killed child leaves durable spool records for a later drainer."""
        hooks = Path(__file__).resolve().parents[1]
        script = (
            "import os,signal,sys;sys.path.insert(0,sys.argv[1]);"
            "from _lib import spool_writer as s;"
            "[s.spool_append({'action':'agent_spawn','f2_wave':2,'i':i}) for i in range(25)];"
            "sys.stdout.write('READY\\n');sys.stdout.flush();os.kill(os.getpid(),signal.SIGKILL)"
        )
        with mock.patch.dict(os.environ, {
            "CEO_PROJECT_STATE_DIR": str(self.audit_dir / "state"),
        }):
            child = run_in_process_group(
                [sys.executable, "-c", script, str(hooks)],
                env=self.subprocess_env(), capture_output=True, timeout=10,
            )
            self.assertEqual(child.stdout, b"READY\n")
            stderr = child.stderr
            self.assertEqual(child.returncode, -signal.SIGKILL, stderr.decode())
            self.assertNotIn(b"Fatal Python error", stderr)
            stats = spool_writer.drain_now(force=True)
        self.assertTrue(stats.ok, stats.error)
        matching = [json.loads(row)["i"] for row in self.read_audit_log().splitlines()
                    if json.loads(row).get("f2_wave") == 2]
        values = set(matching)
        self.assertEqual(values, set(range(25)))
        self.assertEqual(len(matching), 25)

    def test_f2_wave3_fu144_parallel_writers_reach_fixed_point(self) -> None:
        """Four writers produce a set that reaches a drain fixed point."""
        hooks = Path(__file__).resolve().parents[1]
        script = (
            "import os,sys;sys.path.insert(0,sys.argv[1]);"
            "from _lib import spool_writer as s;"
            "base=int(sys.argv[2]);"
            "[s.spool_append({'action':'agent_spawn','f2_wave':3,'i':base+i}) for i in range(25)];"
            "os._exit(0)"
        )
        with mock.patch.dict(os.environ, {
            "CEO_PROJECT_STATE_DIR": str(self.audit_dir / "state"),
        }):
            with ThreadPoolExecutor(max_workers=4) as executor:
                children = [executor.submit(
                    run_in_process_group,
                    [sys.executable, "-c", script, str(hooks), str(base)],
                    env=self.subprocess_env(), capture_output=True, timeout=10,
                ) for base in range(0, 100, 25)]
                stderrs = []
                for future in children:
                    child = future.result()
                    stderr = child.stderr
                    self.assertEqual(child.returncode, 0, stderr.decode())
                    stderrs.append(stderr)
            first = spool_writer.drain_now(force=True)
            second = spool_writer.drain_now(force=True)
        self.assertTrue(first.ok, first.error)
        self.assertTrue(second.ok, second.error)
        self.assertTrue(all(b"Fatal Python error" not in stderr for stderr in stderrs))
        matching = [json.loads(row)["i"] for row in self.read_audit_log().splitlines()
                    if json.loads(row).get("f2_wave") == 3]
        values = set(matching)
        self.assertEqual(values, set(range(100)))
        self.assertEqual(len(matching), 100)
