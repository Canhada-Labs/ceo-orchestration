"""Unit tests for debate-emit.py CLI.

Sprint 5 A.1. The CLI is a thin wrapper around
`_lib.audit_emit.emit_debate_event` called from .claude/commands/debate.md.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Import the script via importlib (filename has a dash)
import importlib.util

_SCRIPTS = Path(__file__).resolve().parent.parent
_SCRIPT = _SCRIPTS / "debate-emit.py"
sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location("debate_emit", _SCRIPT)
debate_emit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(debate_emit)


class DebateEmitTest(unittest.TestCase):

    def setUp(self):
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmp = Path(tempfile.mkdtemp(prefix="debate-emit-test-"))
        self.log_path = self.tmp / "audit-log.jsonl"
        self._snap = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_LOG_LOCK",
                "CEO_AUDIT_LOG_ERR",
                "CEO_AUDIT_LOG_DIR",
                "CEO_AUDIT_SYNC_MODE",
            )
        }
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.log_path)
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.tmp / "audit-log.lock")
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.tmp / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.tmp)

    def tearDown(self):
        for k, v in self._snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_events(self):
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_phase_start_emits_event(self):
        rc = debate_emit.main(
            ["start", "PLAN-005", "1", "--artifact", "/tmp/proposal.md"]
        )
        self.assertEqual(rc, 0)
        events = self._read_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "debate_event")
        self.assertEqual(events[0]["plan_id"], "PLAN-005")
        self.assertEqual(events[0]["round"], 1)
        self.assertEqual(events[0]["phase"], "start")
        self.assertEqual(events[0]["artifact_path"], "/tmp/proposal.md")

    def test_phase_agent_done_requires_agent(self):
        rc = debate_emit.main(["agent-done", "PLAN-005", "1"])
        self.assertEqual(rc, 1)
        events = self._read_events()
        self.assertEqual(events, [])

    def test_phase_agent_done_emits_event(self):
        rc = debate_emit.main(
            [
                "agent-done",
                "PLAN-005",
                "1",
                "--agent",
                "vp-engineering",
                "--artifact",
                "/tmp/vp-engineering.md",
            ]
        )
        self.assertEqual(rc, 0)
        events = self._read_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["agent"], "vp-engineering")
        self.assertEqual(events[0]["phase"], "agent-done")

    def test_phase_consensus_defaults_agent(self):
        rc = debate_emit.main(
            [
                "consensus",
                "PLAN-005",
                "1",
                "--artifact",
                "/tmp/consensus.md",
                "--consensus-adjustments",
                "6",
            ]
        )
        self.assertEqual(rc, 0)
        events = self._read_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["agent"], "consensus")
        self.assertEqual(events[0]["consensus_adjustments_count"], 6)

    def test_round_out_of_range_rejected(self):
        rc = debate_emit.main(["start", "PLAN-005", "4"])
        self.assertEqual(rc, 1)
        self.assertEqual(self._read_events(), [])

        rc = debate_emit.main(["start", "PLAN-005", "0"])
        self.assertEqual(rc, 1)

    def test_bad_phase_rejected(self):
        # argparse prints to stderr + raises SystemExit with rc=2
        with self.assertRaises(SystemExit) as cm:
            debate_emit.main(["kickoff", "PLAN-005", "1"])
        self.assertEqual(cm.exception.code, 2)

    def test_emit_is_fail_open_when_lib_missing(self):
        """If audit_emit import fails, main() still exits 0 (fail-open)."""
        # Simulate by pointing CEO_AUDIT_LOG_PATH at a read-only dir.
        # audit_emit is still importable; its write silently fails to breadcrumb.
        # The CLI still returns 0 — contract is "never block the debate".
        readonly = self.tmp / "ro"
        readonly.mkdir(mode=0o500)
        try:
            os.environ["CEO_AUDIT_LOG_PATH"] = str(readonly / "log.jsonl")
            rc = debate_emit.main(["start", "PLAN-005", "1"])
            self.assertEqual(rc, 0)
        finally:
            readonly.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
