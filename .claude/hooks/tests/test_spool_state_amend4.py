"""FU144 regression contract for deadline-bounded spool exits."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
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
