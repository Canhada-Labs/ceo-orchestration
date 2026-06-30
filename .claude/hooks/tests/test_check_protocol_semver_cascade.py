"""tests for check_protocol_semver_cascade.py (PLAN-110 Wave D)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / ".claude/hooks/check_protocol_semver_cascade.py"


def _run_hook(payload: Dict) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CEO_AUDIT_SYNC_MODE"] = "1"
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


class TestProtocolSemverCascadeHook(unittest.TestCase):
    """8 fixture cases per PLAN-110 Wave D AC P1."""

    def test_a_edit_protocol_with_adr_amend_session_no_warning(self):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [
                    {"file_path": ".claude/adr/ADR-115-AMEND-1.md",
                     "content_excerpt": "AMEND text"},
                ],
            },
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        # PLAN-138 Wave D (ADR-156): the paired-amend path now STILL ships the
        # Sync Impact Report (was bare {}). The missing-amend WARN must NOT
        # appear (the amend IS paired) — that is the real "no_warning" invariant.
        out = json.loads(res.stdout or "{}")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Sync Impact Report", ctx)
        self.assertNotIn("without paired ADR", ctx)

    def test_b_edit_protocol_without_adr_amend_warns(self):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout or "{}")
        self.assertIn("hookSpecificOutput", out)
        self.assertIn("PROTOCOL.md", out["hookSpecificOutput"]["additionalContext"])

    def test_c_multiple_amends_no_warning(self):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [
                    {"file_path": ".claude/adr/ADR-100-AMEND-1.md"},
                    {"file_path": ".claude/adr/ADR-115-AMEND-2.md"},
                ],
            },
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        # PLAN-138 Wave D (ADR-156): paired-amend path ships the Sync Impact
        # Report; the missing-amend WARN must NOT appear.
        out = json.loads(res.stdout or "{}")
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        self.assertIn("Sync Impact Report", ctx)
        self.assertNotIn("without paired ADR", ctx)

    def test_d_no_protocol_edit_no_warning(self):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "README.md"},
            "context": {"session_edits": []},
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "{}")

    def test_e_adr_not_amend_format_warns(self):
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {
                "session_edits": [
                    {"file_path": "docs/notes.md",
                     "content_excerpt": "see ADR-123 (not AMEND)"},
                ],
            },
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        # Heuristic requires explicit ADR-NNN-AMEND-M in path OR content.
        # docs/notes.md mentions ADR-123 but not AMEND-M -> warn.
        out = json.loads(res.stdout or "{}")
        self.assertIn("hookSpecificOutput", out)

    def test_f_write_tool_targets_protocol_warns(self):
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "PROTOCOL.md"},
            "context": {"session_edits": []},
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout or "{}")
        self.assertIn("hookSpecificOutput", out)

    def test_g_non_edit_tool_passes_through(self):
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": "PROTOCOL.md"},
        }
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "{}")

    def test_h_empty_payload_passes_through(self):
        payload = {}
        res = _run_hook(payload)
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "{}")


if __name__ == "__main__":
    unittest.main()
