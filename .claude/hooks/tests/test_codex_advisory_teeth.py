#!/usr/bin/env python3
"""PLAN-155 Wave 6 — codex-advisory-teeth chain-scan backstop tests.

Proves the two BACKSTOP checks for the ADVISORY Codex rails:

- **A (RED):** a session with tool activity but no ``session_start`` boot
  breadcrumb is flagged RED (config-tripwire backstop, RED-on-absence) and
  the process exits non-zero. A mutation control (add the boot breadcrumb)
  clears it — proving the RED assertion has teeth.
- **B (ADVISORY):** a spawn-class tool record with no matching
  ``SubagentStart`` lifecycle entry is flagged advisory (spawn-governance
  backstop) and does NOT on its own fail the run.

Synthetic chains + sidecar written under an isolated tmp dir; no repo-tree
writes, no real ``$HOME``.
"""

from __future__ import annotations

import importlib.util as _ilu
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_THIS = Path(__file__).resolve()


def _repo_root() -> Path:
    p = _THIS
    for _ in range(12):
        if (p / ".git").exists():
            return p
        p = p.parent
    return _THIS.parents[8]


REPO = _repo_root()
SCRIPT = REPO / ".claude" / "plans" / "PLAN-155" / "staged" / "wave-6" / "scripts" / "codex-advisory-teeth.py"


def _load():
    spec = _ilu.spec_from_file_location("codex_advisory_teeth_w6", str(SCRIPT))
    assert spec and spec.loader
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


MOD = _load()


def _entry(action: str, session_id: str, **extra):
    d = {"action": action, "session_id": session_id, "ts": "2026-07-10T00:00:00Z"}
    d.update(extra)
    return d


class ScanUnitTests(unittest.TestCase):
    def test_activity_without_boot_is_red(self):
        entries = [_entry("codex_tool_recorded", "s1", tool_name_enum="Edit")]
        out = MOD.scan(entries, subagent_sessions=set())
        self.assertEqual(len(out["red"]), 1)
        self.assertEqual(out["red"][0]["check"], "boot_breadcrumb_absence")

    def test_boot_breadcrumb_clears_red(self):
        entries = [
            _entry("session_start", "s1"),
            _entry("codex_tool_recorded", "s1", tool_name_enum="Edit"),
        ]
        out = MOD.scan(entries, subagent_sessions=set())
        self.assertEqual(out["red"], [])

    def test_spawn_without_subagent_start_is_advisory(self):
        entries = [
            _entry("session_start", "s1"),
            _entry("codex_tool_recorded", "s1", tool_name_enum="Task"),
        ]
        out = MOD.scan(entries, subagent_sessions=set())
        self.assertEqual(out["red"], [])
        self.assertEqual(len(out["advisory"]), 1)
        self.assertEqual(out["advisory"][0]["check"], "spawn_without_subagent_start")

    def test_spawn_with_subagent_start_is_clean(self):
        entries = [
            _entry("session_start", "s1"),
            _entry("codex_tool_recorded", "s1", tool_name_enum="Task"),
        ]
        out = MOD.scan(entries, subagent_sessions={"s1"})
        self.assertEqual(out["advisory"], [])

    def test_session_filter(self):
        entries = [
            _entry("codex_tool_recorded", "s1", tool_name_enum="Edit"),
            _entry("codex_tool_recorded", "s2", tool_name_enum="Edit"),
        ]
        out = MOD.scan(entries, subagent_sessions=set(), session_filter="s1")
        self.assertEqual([f["session_id"] for f in out["red"]], ["s1"])


class SubprocessExitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="w6-teeth-"))
        self.log = self._tmp / "audit-log.jsonl"
        self.sidecar = self._tmp / "subagent-lifecycle.json"

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_log(self, entries):
        self.log.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
        )

    def _run(self, *args):
        env = dict(os.environ)
        env["CEO_AUDIT_LOG_PATH"] = str(self.log)
        # Point lifecycle sidecar resolution at our tmp (via state dir env).
        env["CEO_SUBAGENT_LIFECYCLE_STATE_DIR"] = str(self._tmp)
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--log", str(self.log)] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=30,
        )

    def test_red_finding_exits_nonzero(self):
        self._write_log([_entry("codex_tool_recorded", "s1", tool_name_enum="Edit")])
        proc = self._run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"RED", proc.stdout)

    def test_clean_exits_zero(self):
        self._write_log(
            [
                _entry("session_start", "s1"),
                _entry("codex_tool_recorded", "s1", tool_name_enum="Edit"),
            ]
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0)

    def test_advisory_only_never_fails(self):
        self._write_log([_entry("codex_tool_recorded", "s1", tool_name_enum="Edit")])
        proc = self._run("--advisory-only")
        self.assertEqual(proc.returncode, 0)

    def test_json_output(self):
        self._write_log([_entry("codex_tool_recorded", "s1", tool_name_enum="Edit")])
        proc = self._run("--json", "--advisory-only")
        data = json.loads(proc.stdout.decode("utf-8"))
        self.assertEqual(data["red_count"], 1)

    def test_spawn_advisory_does_not_fail_run(self):
        # A spawn without a SubagentStart record is advisory-only; with a boot
        # breadcrumb present there is no RED, so the run must exit 0.
        self._write_log(
            [
                _entry("session_start", "s1"),
                _entry("codex_tool_recorded", "s1", tool_name_enum="Task"),
            ]
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0)
        self.assertIn(b"ADV", proc.stdout)

    def test_spawn_with_sidecar_is_clean(self):
        self.sidecar.write_text(
            json.dumps({"entries": {"k": {"session_id": "s1", "start_ts": 1}}}),
            encoding="utf-8",
        )
        self._write_log(
            [
                _entry("session_start", "s1"),
                _entry("codex_tool_recorded", "s1", tool_name_enum="Task"),
            ]
        )
        proc = self._run()
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn(b"ADV", proc.stdout)


if __name__ == "__main__":
    unittest.main()
