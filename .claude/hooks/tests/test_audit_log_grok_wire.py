"""Tests for the grok host-wire audit dispatch in audit_log.py (PLAN-156 W4).

Coverage-truth (ADR-139): a6d1632 added `_grok_tool_enum` + `_grok_audit_main`
to the Tier-1 module audit_log.py with no test exercising the grok path — the
Tier-1 per-module gate sat red (84.98% < 86.0) from 2026-07-21 until these
landed. The tests drive `audit_log.main()` under `CEO_HOOK_ADAPTER=grok`
exactly as the harness does (host envelope on stdin, HMAC append out):

- `_grok_tool_enum` mapping (empty / non-str -> other, mcp__* -> mcp_other,
  internal-vocabulary passthrough)
- PostToolUse happy path -> `grok_tool_recorded` appended with closed-enum
  fields (harness / tool_name_enum / hook_event_name)
- off-enum native tool -> emitter coerces tool_name_enum to "other"
- Stop / SubagentStop -> `grok_turn_ended` (source stop / subagent_stop,
  plus the CEO_GROK_TURN_SOURCE override)
- stdin parse error -> fail-open (rc 0, no append)
- non-audited phase (pre_tool_use) -> rc 0, no append
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import audit_log as al  # noqa: E402


def _grok_envelope(hook_event="post_tool_use", tool="run_terminal_command", **over):
    """Minimal grok host-wire envelope (SPEC §3.1: `hookEventName` is the wire key)."""
    d = {
        "hookEventName": hook_event,
        "toolName": tool,
        "toolInput": {"command": "echo hi"},
        "sessionId": "sess-grok-wire-test",
    }
    d.update(over)
    return d


def _run_grok_main(payload, extra_env=None):
    """Run audit_log.main() under CEO_HOOK_ADAPTER=grok with `payload` on stdin."""
    env = {"CEO_HOOK_ADAPTER": "grok"}
    if extra_env:
        env.update(extra_env)
    data = payload if isinstance(payload, str) else json.dumps(payload)
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(data)
    sys.stdout = io.StringIO()
    try:
        with mock.patch.dict(os.environ, env):
            rc = al.main()
        out = sys.stdout.getvalue()
    finally:
        sys.stdin = old_stdin
        sys.stdout = old_stdout
    return rc, out


class _LogReader:
    """Reads the audit log written during a TestEnvContext session."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def _last_event(self):
        events = self._read_log()
        self.assertGreater(len(events), 0, "audit log must have >=1 event")
        return events[-1]


class TestGrokToolEnum(TestEnvContext):
    """`_grok_tool_enum` — pure mapping, never raises."""

    def test_empty_and_non_str_fold_to_other(self):
        self.assertEqual(al._grok_tool_enum(""), "other")
        self.assertEqual(al._grok_tool_enum(None), "other")
        self.assertEqual(al._grok_tool_enum(42), "other")

    def test_mcp_names_fold_to_mcp_other(self):
        self.assertEqual(al._grok_tool_enum("mcp__foo__bar"), "mcp_other")

    def test_internal_vocabulary_passes_through(self):
        self.assertEqual(al._grok_tool_enum("Bash"), "Bash")
        self.assertEqual(al._grok_tool_enum("Edit"), "Edit")


class TestGrokPostToolUse(TestEnvContext, _LogReader):
    """PostToolUse envelope -> grok_tool_recorded on the chain."""

    def test_happy_path_appends_grok_tool_recorded(self):
        rc, out = _run_grok_main(_grok_envelope())
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        ev = self._last_event()
        self.assertEqual(ev["action"], "grok_tool_recorded")
        self.assertEqual(ev["harness"], "grok")
        # run_terminal_command aliases to Bash before the enum fold.
        self.assertEqual(ev["tool_name_enum"], "Bash")
        self.assertEqual(ev["hook_event_name"], "PostToolUse")

    def test_mcp_tool_folds_to_mcp_other(self):
        rc, _ = _run_grok_main(_grok_envelope(tool="mcp__grok__thing"))
        self.assertEqual(rc, 0)
        self.assertEqual(self._last_event()["tool_name_enum"], "mcp_other")

    def test_off_enum_tool_coerced_to_other_by_emitter(self):
        rc, _ = _run_grok_main(_grok_envelope(tool="weird_native_tool_xyz"))
        self.assertEqual(rc, 0)
        self.assertEqual(self._last_event()["tool_name_enum"], "other")


class TestGrokTurnEnded(TestEnvContext, _LogReader):
    """Stop / SubagentStop envelopes -> grok_turn_ended accounting."""

    def test_stop_appends_turn_ended_source_stop(self):
        rc, _ = _run_grok_main(_grok_envelope(hook_event="stop"))
        self.assertEqual(rc, 0)
        ev = self._last_event()
        self.assertEqual(ev["action"], "grok_turn_ended")
        self.assertEqual(ev["harness"], "grok")
        self.assertEqual(ev["source"], "stop")

    def test_subagent_stop_appends_source_subagent_stop(self):
        rc, _ = _run_grok_main(_grok_envelope(hook_event="subagent_stop"))
        self.assertEqual(rc, 0)
        self.assertEqual(self._last_event()["source"], "subagent_stop")

    def test_turn_source_env_override_wins(self):
        rc, _ = _run_grok_main(
            _grok_envelope(hook_event="stop"),
            extra_env={"CEO_GROK_TURN_SOURCE": "other"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(self._last_event()["source"], "other")


class TestGrokFailOpenPaths(TestEnvContext, _LogReader):
    """Fail-open contract: rc 0 + no append on non-auditable input."""

    def test_parse_error_is_fail_open_no_append(self):
        rc, out = _run_grok_main("{this is not json")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual(self._read_log(), [])

    def test_non_audited_phase_is_noop(self):
        rc, out = _run_grok_main(_grok_envelope(hook_event="pre_tool_use"))
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertEqual(self._read_log(), [])


if __name__ == "__main__":
    unittest.main()
