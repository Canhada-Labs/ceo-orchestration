"""FU144 regressions for spool exit-handler chaining and reset behavior."""
from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
from unittest import mock

from _lib import spool_writer
from _lib.testing import TestEnvContext


class TestSpoolWriterSignalChain(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        spool_writer._reset_for_test()

    def tearDown(self) -> None:
        spool_writer._reset_for_test()
        super().tearDown()

    def test_callable_signal_chain_fu144_is_preserved_without_drain(self) -> None:
        """A deadline skips work but still invokes the user SIGTERM handler."""
        original = signal.getsignal(signal.SIGTERM)
        called = []

        def user_handler(signum, frame):
            called.append((signum, frame))

        try:
            signal.signal(signal.SIGTERM, user_handler)
            spool_writer.install_exit_handlers()
            spool_writer.set_exit_deadline(1.0)
            with mock.patch.object(spool_writer, "drain_now") as drain, \
                 mock.patch.object(spool_writer, "_flush_journal_buffer") as flush:
                spool_writer._signal_drain_handler(signal.SIGTERM, None)
            drain.assert_not_called()
            flush.assert_not_called()
            self.assertEqual(called, [(signal.SIGTERM, None)])
            self.assertIs(signal.getsignal(signal.SIGTERM), user_handler)
        finally:
            spool_writer._reset_for_test()
            signal.signal(signal.SIGTERM, original)

    def test_ignored_signal_fu144_remains_ignored_without_drain(self) -> None:
        """SIG_IGN is a user disposition, including on the deadline path."""
        original = signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            spool_writer.install_exit_handlers()
            spool_writer.set_exit_deadline(1.0)
            with mock.patch.object(spool_writer, "drain_now") as drain, \
                 mock.patch.object(spool_writer, "_flush_journal_buffer") as flush:
                spool_writer._signal_drain_handler(signal.SIGTERM, None)
            drain.assert_not_called()
            flush.assert_not_called()
            self.assertIs(signal.getsignal(signal.SIGTERM), signal.SIG_IGN)
        finally:
            spool_writer._reset_for_test()
            signal.signal(signal.SIGTERM, original)

    def test_reset_fu144_restores_previous_signal_dispositions(self) -> None:
        """Reset restores callable SIGTERM and ignored SIGINT dispositions."""
        original_term = signal.getsignal(signal.SIGTERM)
        original_int = signal.getsignal(signal.SIGINT)

        def term_handler(signum, frame):
            return None

        try:
            signal.signal(signal.SIGTERM, term_handler)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            spool_writer.install_exit_handlers()
            spool_writer._reset_for_test()
            self.assertIs(signal.getsignal(signal.SIGTERM), term_handler)
            self.assertIs(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
        finally:
            spool_writer._reset_for_test()
            signal.signal(signal.SIGTERM, original_term)
            signal.signal(signal.SIGINT, original_int)

    def test_sigterm_after_reset_fu144_uses_default_without_recursion(self) -> None:
        """Literal reset flow and a stale self-handler both terminate cleanly."""
        hooks_dir = Path(__file__).resolve().parents[1]
        literal = (
            "import os, signal, sys;"
            "sys.path.insert(0, sys.argv[1]);"
            "from _lib import spool_writer as spool;"
            "spool.install_exit_handlers();"
            "spool._reset_for_test();"
            "spool.install_exit_handlers();"
            "os.kill(os.getpid(), signal.SIGTERM);"
            "raise SystemExit(99)"
        )
        stale_self = literal.replace(
            "spool.install_exit_handlers();os.kill",
            "signal.signal(signal.SIGTERM, spool._signal_drain_handler);"
            "spool.install_exit_handlers();os.kill",
        )
        with mock.patch.dict(os.environ, {"CEO_AUDIT_SYNC_MODE": "1"}):
            for script in (literal, stale_self):
                child = subprocess.run(
                    [sys.executable, "-c", script, str(hooks_dir)],
                    capture_output=True,
                    env=self.subprocess_env(),
                    timeout=10,
                )
                self.assertEqual(child.returncode, -signal.SIGTERM, child.stderr.decode())
                self.assertNotIn(b"Fatal Python error", child.stderr)
