"""Tests for check_output_safety.py — PostToolUse Agent hook.

Sprint 11 Phase 9 / ADR-036. Verifies:
- fail-open contract (parse_error, missing fields, scanner exception → allow)
- clean output → allow, no audit event
- matching output → allow + output_safety_flag audit event
- CEO_SOTA_DISABLE=1 → allow, no event (S4 kill switch)
- CEO_OUTPUT_SAFETY_MODE=flag preserves text; redact attaches redaction_applied
- NFKC / zero-width / bidi attacks caught via hook (pipeline plumbing)
- Multiple tool_response shapes extracted correctly
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_output_safety.py"


class _HookRunnerMixin:
    """Shared helpers for invoking the hook as a subprocess."""

    def _invoke(
        self,
        payload: dict,
        *,
        env_overrides: dict = None,
        timeout: int = 10,
    ):
        env = dict(os.environ)
        if env_overrides:
            env.update(env_overrides)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _read_events(self):
        log_path = self.audit_dir / "audit-log.jsonl"  # type: ignore[attr-defined]
        if not log_path.exists():
            return []
        return [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _safety_events(self):
        return [e for e in self._read_events() if e.get("action") == "output_safety_flag"]


class CheckOutputSafetyBasicTest(TestEnvContext, _HookRunnerMixin):

    # ---- fail-open ----------------------------------------------------------

    def test_empty_payload_allows(self):
        rc, out, _ = self._invoke({})
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")
        self.assertEqual(self._safety_events(), [])

    def test_missing_tool_response_allows(self):
        rc, out, _ = self._invoke({"tool_name": "Agent", "tool_input": {}})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")
        self.assertEqual(self._safety_events(), [])

    def test_malformed_json_allows(self):
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="not-valid-json{{",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ},
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout).get("decision", "allow"), "allow")

    # ---- clean output --------------------------------------------------------

    def test_clean_output_allows_silently(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"text": "All systems nominal, no issues detected."},
        }
        rc, out, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")
        self.assertEqual(self._safety_events(), [])

    # ---- match triggers audit ------------------------------------------------

    def test_api_key_leak_triggers_event(self):
        payload = {
            "tool_name": "Agent",
            "session_id": "sess-1",
            "tool_response": {
                "text": "Debug: the leaked key is sk-abcDEF1234567890xyzABCDEFGHIJKL"
            },
        }
        rc, out, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")
        events = self._safety_events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["triggered_by_tool"], "Agent")
        self.assertIn("api_key", ev["family_counts"])
        self.assertGreaterEqual(ev["match_count"], 1)
        # Default mode is flag → redaction_applied should be False
        self.assertFalse(ev["redaction_applied"])

    def test_jwt_leak_triggers_event(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "message": "token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c expired"
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        events = self._safety_events()
        self.assertEqual(len(events), 1)
        self.assertIn("jwt", events[0]["family_counts"])

    # ---- kill switch ---------------------------------------------------------

    def test_sota_disable_is_noop(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "key sk-abcDEF1234567890xyzABCDEFGHIJKL leaked"
            },
        }
        rc, out, _ = self._invoke(payload, env_overrides={"CEO_SOTA_DISABLE": "1"})
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")
        # No audit event at all under kill switch
        self.assertEqual(self._safety_events(), [])

    # ---- mode flag / redact --------------------------------------------------

    def test_flag_mode_default_redaction_not_applied(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"text": "sk-abcDEF1234567890xyzABCDEFGHIJKL"},
        }
        rc, out, _ = self._invoke(payload)  # default CEO_OUTPUT_SAFETY_MODE=flag
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out).get("decision", "allow"), "allow")
        ev = self._safety_events()[0]
        self.assertFalse(ev["redaction_applied"])

    def test_redact_mode_sets_redaction_applied_true(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"text": "sk-abcDEF1234567890xyzABCDEFGHIJKL leaked"},
        }
        rc, out, _ = self._invoke(
            payload,
            env_overrides={"CEO_OUTPUT_SAFETY_MODE": "redact"},
        )
        self.assertEqual(rc, 0)
        ev = self._safety_events()[0]
        self.assertTrue(ev["redaction_applied"])

    def test_invalid_mode_falls_back_to_flag(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"text": "sk-abcDEF1234567890xyzABCDEFGHIJKL"},
        }
        rc, _, _ = self._invoke(
            payload,
            env_overrides={"CEO_OUTPUT_SAFETY_MODE": "bogus"},
        )
        self.assertEqual(rc, 0)
        ev = self._safety_events()[0]
        self.assertFalse(ev["redaction_applied"])

    # ---- pipeline plumbing: NFKC / ZWSP / bidi -------------------------------

    def test_nfkc_full_width_attack_flagged_via_hook(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "leaked \uff53\uff4b\uff0dabcDEF1234567890xyzABCDEFGHIJKL"
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        events = self._safety_events()
        self.assertEqual(len(events), 1)
        self.assertIn("api_key", events[0]["family_counts"])

    def test_zero_width_evasion_caught_via_hook(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "hidden: s\u200bk-abcDEF1234567890xyzABCDEFGHIJKL"
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        events = self._safety_events()
        self.assertEqual(len(events), 1)
        self.assertIn("api_key", events[0]["family_counts"])

    def test_bidi_override_caught_via_hook(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "tok s\u202ek-abcDEF1234567890xyzABCDEFGHIJKL end"
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        events = self._safety_events()
        self.assertEqual(len(events), 1)


class CheckOutputSafetyShapesTest(TestEnvContext, _HookRunnerMixin):
    """tool_response shape variants should all produce scannable text."""

    def test_content_list_of_blocks(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "content": [
                    {"text": "prefix"},
                    {"text": "key sk-abcDEF1234567890xyzABCDEFGHIJKL"},
                ]
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._safety_events()), 1)

    def test_output_field(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"output": "Bearer abc123XYZ.tok_sample-value-789"},
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._safety_events()), 1)

    def test_concatenates_message_and_text_output(self):
        # Both fields present — both get scanned
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "message": "meta",
                "text_output": "GitHub PAT: ghp_abcDEFghi1234567890XYZ012",
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(len(self._safety_events()), 1)


class CheckOutputSafetyControlsTest(TestEnvContext, _HookRunnerMixin):
    """Control fixtures must NOT trigger the hook."""

    def test_random_hash_log_does_not_fire(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "build sha256=a3b8c1d6e9f20471c2e3fa9b1c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d"
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(self._safety_events(), [])

    def test_docs_email_no_address_does_not_fire(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {
                "text": "Describes how an email header looks without showing any address."
            },
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(self._safety_events(), [])

    def test_raw_digits_no_cpf_context_does_not_fire(self):
        payload = {
            "tool_name": "Agent",
            "tool_response": {"text": "Tracking number 12345678901 routed to Miami."},
        }
        rc, _, _ = self._invoke(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(self._safety_events(), [])


if __name__ == "__main__":
    unittest.main()
