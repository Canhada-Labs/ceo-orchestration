"""Unit tests for check_confidence_gate.py (PLAN-009 C1.1).

Covers:
- Decision function (advisory, enforce, bypass, timeout, infra-fail)
- Agent text extraction from tool_response variants
- End-to-end via adapter fixtures (claude + gemini stub)
- Byte-identical fixture harness (PLAN-006 ADR-014)
- Fail-open contract
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import contract as _contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

import check_confidence_gate as hk  # noqa: E402


# ---------------------------------------------------------------------------
# decide() — pure function, no subprocess
# ---------------------------------------------------------------------------


class TestDecide(unittest.TestCase):
    def test_bypass_always_allows(self):
        payload = {"exit_code": 1, "fail_count": 3, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=True)
        self.assertTrue(d.allow)

    def test_none_payload_allows(self):
        # Infrastructure failure — fail-open
        d = hk.decide(payload=None, enforce=True, bypass=False)
        self.assertTrue(d.allow)

    def test_timeout_always_allows(self):
        payload = {"outcome": "timeout", "exit_code": None}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertTrue(d.allow)

    def test_pass_allows(self):
        payload = {"exit_code": 0, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertTrue(d.allow)

    def test_usage_error_allows(self):
        payload = {"exit_code": 2, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertTrue(d.allow)

    def test_zero_claims_allows(self):
        payload = {"exit_code": 3, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertTrue(d.allow)

    @unittest.skip("ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py")
    def test_fail_with_enforce_blocks(self):
        payload = {"exit_code": 1, "fail_count": 2, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertFalse(d.allow)
        self.assertIn("CONFIDENCE-GATE-BLOCKED", d.reason)
        self.assertIn("2 claim(s)", d.reason)

    def test_fail_without_enforce_allows(self):
        """C1.1 default — advisory only."""
        payload = {"exit_code": 1, "fail_count": 3, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=False, bypass=False)
        self.assertTrue(d.allow)

    def test_unknown_exit_code_allows(self):
        """Defense-in-depth fail-open."""
        payload = {"exit_code": 99, "outcome": "verified"}
        d = hk.decide(payload=payload, enforce=True, bypass=False)
        self.assertTrue(d.allow)


# ---------------------------------------------------------------------------
# _extract_agent_text — tool_response shape variants
# ---------------------------------------------------------------------------


class TestAgentTextExtraction(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        self.assertEqual(hk._extract_agent_text({}), "")
        self.assertEqual(hk._extract_agent_text(None), "")

    def test_text_key(self):
        tr = {"text": "hello world"}
        self.assertEqual(hk._extract_agent_text(tr), "hello world")

    def test_response_key(self):
        tr = {"response": "agent said so"}
        self.assertEqual(hk._extract_agent_text(tr), "agent said so")

    def test_output_key(self):
        tr = {"output": "out"}
        self.assertEqual(hk._extract_agent_text(tr), "out")

    def test_content_list_of_blocks(self):
        tr = {"content": [{"text": "block1"}, {"text": "block2"}]}
        self.assertEqual(hk._extract_agent_text(tr), "block1\nblock2")

    def test_content_list_of_strings(self):
        tr = {"content": ["raw a", "raw b"]}
        self.assertEqual(hk._extract_agent_text(tr), "raw a\nraw b")

    def test_text_wins_over_content(self):
        tr = {"text": "top", "content": [{"text": "nested"}]}
        self.assertEqual(hk._extract_agent_text(tr), "top")

    def test_fallback_to_json_blob(self):
        tr = {"weird": "shape", "nested": {"a": 1}}
        out = hk._extract_agent_text(tr)
        self.assertIn("weird", out)


# ---------------------------------------------------------------------------
# _run_gate_cli — actual subprocess; uses the real confidence_gate.py
# ---------------------------------------------------------------------------


class TestRunGateCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        # Mirror the script into the temp root so the CLI is discoverable
        (self.root / ".claude" / "scripts").mkdir(parents=True)
        real_script = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts"
            / "confidence_gate.py"
        )
        dest = self.root / ".claude" / "scripts" / "confidence_gate.py"
        dest.write_text(real_script.read_text(encoding="utf-8"))
        dest.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pass_exit_code_0(self):
        # Create a real file the CLAIM points at
        (self.root / "target.py").write_text("x = 1\n")
        out = hk._run_gate_cli(
            "CLAIM:path_exists:target.py",
            agent_name="Test",
            repo_root=self.root,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out["exit_code"], 0)
        self.assertEqual(out["outcome"], "verified")
        self.assertEqual(out["claim_count"], 1)

    def test_fail_exit_code_1(self):
        out = hk._run_gate_cli(
            "CLAIM:path_exists:nowhere.py",
            agent_name="Test",
            repo_root=self.root,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out["exit_code"], 1)
        self.assertEqual(out["fail_count"], 1)

    def test_zero_claims_exit_code_3(self):
        out = hk._run_gate_cli(
            "prose with no CLAIM tokens",
            agent_name="Test",
            repo_root=self.root,
        )
        self.assertIsNotNone(out)
        self.assertEqual(out["exit_code"], 3)

    def test_missing_cli_returns_none(self):
        with tempfile.TemporaryDirectory() as bare:
            # No .claude/scripts/confidence_gate.py in this root
            out = hk._run_gate_cli(
                "CLAIM:path_exists:x.py",
                agent_name="Test",
                repo_root=Path(bare).resolve(),
            )
            self.assertIsNone(out)


# ---------------------------------------------------------------------------
# End-to-end via main() — reads from stdin, writes decision to stdout
# ---------------------------------------------------------------------------


class TestMainEndToEnd(TestEnvContext):
    def _run_with_payload(self, payload: dict) -> str:
        """Drive main() with a PostToolUse payload; return stdout line."""
        stdin_text = json.dumps(payload)
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with patch.object(sys, "stdout", stdout_buf):
                hk.main()
        return stdout_buf.getvalue().strip()

    def test_non_agent_tool_allows_silently(self):
        out = self._run_with_payload({
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": {"text": "file.txt"},
        })
        self.assertEqual(json.loads(out), {})

    def test_empty_response_allows(self):
        out = self._run_with_payload({
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "general-purpose"},
            "tool_response": {},
        })
        self.assertEqual(json.loads(out), {})

    def test_zero_claims_in_response_allows(self):
        out = self._run_with_payload({
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "general-purpose"},
            "tool_response": {"text": "Did the work. No claims embedded."},
        })
        self.assertEqual(json.loads(out), {})

    def test_bad_stdin_allows(self):
        """Fail-open contract: malformed stdin → allow."""
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO("not json")):
            with patch.object(sys, "stdout", stdout_buf):
                hk.main()
        self.assertEqual(json.loads(stdout_buf.getvalue().strip()), {})


# ---------------------------------------------------------------------------
# Env gate helpers
# ---------------------------------------------------------------------------


class TestEnvGates(unittest.TestCase):
    def test_is_truthy_env_variants(self):
        for val in ("1", "true", "TRUE", "yes", "on", " true "):
            with patch.dict(os.environ, {"X_TEST_FLAG": val}, clear=False):
                self.assertTrue(hk._is_truthy_env("X_TEST_FLAG"), f"failed: {val!r}")

    def test_is_truthy_env_falsy(self):
        for val in ("", "0", "false", "no", "off", "random"):
            with patch.dict(os.environ, {"X_TEST_FLAG": val}, clear=False):
                self.assertFalse(hk._is_truthy_env("X_TEST_FLAG"), f"failed: {val!r}")


# ---------------------------------------------------------------------------
# PLAN-009 C1.3 — ADR-019 exit-code translation matrix
# ---------------------------------------------------------------------------


class TestEnforcementTranslationMatrix(unittest.TestCase):
    """ADR-019 §3 table — every cell verified via decide()."""

    def _dec(self, *, exit_code, enforce=False, bypass=False, fail_count=0):
        payload = {"exit_code": exit_code, "outcome": "verified",
                   "fail_count": fail_count}
        return hk.decide(payload=payload, enforce=enforce, bypass=bypass)

    # exit 0 (pass) — always allow
    def test_exit0_enforce0(self):
        self.assertTrue(self._dec(exit_code=0, enforce=False).allow)
    def test_exit0_enforce1(self):
        self.assertTrue(self._dec(exit_code=0, enforce=True).allow)

    # exit 1 (fail) — asymmetric on enforce
    def test_exit1_enforce0_allows(self):
        self.assertTrue(self._dec(exit_code=1, enforce=False, fail_count=2).allow)
    @unittest.skip("ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py")
    def test_exit1_enforce1_blocks(self):
        d = self._dec(exit_code=1, enforce=True, fail_count=2)
        self.assertFalse(d.allow)
        self.assertIn("ADR-019", d.reason)
    def test_exit1_enforce1_bypass_allows(self):
        self.assertTrue(self._dec(exit_code=1, enforce=True, bypass=True, fail_count=2).allow)

    # exit 2 (usage) — always allow
    def test_exit2_enforce0(self):
        self.assertTrue(self._dec(exit_code=2, enforce=False).allow)
    def test_exit2_enforce1(self):
        self.assertTrue(self._dec(exit_code=2, enforce=True).allow)

    # exit 3 (zero claims) — always allow
    def test_exit3_enforce0(self):
        self.assertTrue(self._dec(exit_code=3, enforce=False).allow)
    def test_exit3_enforce1(self):
        self.assertTrue(self._dec(exit_code=3, enforce=True).allow)

    # timeout — always allow
    def test_timeout_any_state(self):
        p = {"outcome": "timeout", "exit_code": None}
        self.assertTrue(hk.decide(payload=p, enforce=True, bypass=False).allow)

    # unknown exit — fail-open
    def test_unknown_exit_fails_open(self):
        self.assertTrue(self._dec(exit_code=42, enforce=True).allow)

    # block reason template (ADR-019 §3)
    @unittest.skip("ADR-019-AMEND-1 retired broad enforce — see test_confidence_gate_class_block.py")
    def test_block_reason_template(self):
        d = self._dec(exit_code=1, enforce=True, fail_count=5)
        self.assertIn("CONFIDENCE-GATE-BLOCKED", d.reason)
        self.assertIn("5 claim(s)", d.reason)
        self.assertIn("CEO_CONFIDENCE_ENFORCE=0", d.reason)
        self.assertIn("CEO_CONFIDENCE_BYPASS=1", d.reason)


if __name__ == "__main__":
    unittest.main()
