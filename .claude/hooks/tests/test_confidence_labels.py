"""Unit tests for confidence_labels.py — designed for ≥80% mutation kill-rate.

Test strategy (per PLAN-083 QA P0-3):

- Each classification rule exercised with positive + negative cases so
  operator mutations (e.g. `==` → `!=`, `>` → `>=`) get killed.
- Boundary conditions at _BULK_FILE_THRESHOLD (10): test 10 (NEEDS_CONFIRM),
  11 (RISKY), and 0 (NEEDS_CONFIRM).
- Env-var override contract: exact-value vs truthy alias tested
  separately to kill string-literal mutations.
- Idempotence + no-leak invariants asserted as properties.
- prompt_for_confirmation: all three branches (SAFE / NEEDS_CONFIRM /
  RISKY) plus EOF, no-match, env-auto-confirm, env-bypass.

Total: 30 tests (well above ≥20 minimum).
"""

from __future__ import annotations

import io
import os
import sys
import unittest
from pathlib import Path

# Make the staging module importable without modifying canonical sys.path.
_HERE = Path(__file__).resolve().parent
_MODULE_DIR = _HERE.parent / "_lib"
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

import confidence_labels as cl  # noqa: E402


# ---------------------------------------------------------------------------
# classify() — read-only / SAFE rules
# ---------------------------------------------------------------------------


class TestClassifySafe(unittest.TestCase):
    def test_read_is_safe(self) -> None:
        c = cl.classify("read", {})
        self.assertEqual(c.level, cl.SAFE)
        self.assertEqual(c.reason_code, "read_only")

    def test_read_file_is_safe(self) -> None:
        self.assertEqual(cl.classify("read_file", {}).level, cl.SAFE)

    def test_audit_query_read_is_safe(self) -> None:
        self.assertEqual(cl.classify("audit_query_read", {}).level, cl.SAFE)

    def test_status_check_is_safe(self) -> None:
        self.assertEqual(cl.classify("status_check", {}).level, cl.SAFE)

    def test_help_me_is_safe(self) -> None:
        self.assertEqual(cl.classify("help_me", {}).level, cl.SAFE)

    def test_safe_with_none_context(self) -> None:
        # Defensive: context=None must not crash.
        c = cl.classify("read", None)
        self.assertEqual(c.level, cl.SAFE)


# ---------------------------------------------------------------------------
# classify() — always-RISKY rules
# ---------------------------------------------------------------------------


class TestClassifyRisky(unittest.TestCase):
    def test_canonical_edit_is_risky(self) -> None:
        c = cl.classify("canonical_edit", {})
        self.assertEqual(c.level, cl.RISKY)
        self.assertEqual(c.reason_code, "canonical_edit")

    def test_settings_json_edit_is_risky(self) -> None:
        self.assertEqual(cl.classify("settings_json_edit", {}).level, cl.RISKY)

    def test_sentinel_modify_is_risky(self) -> None:
        self.assertEqual(cl.classify("sentinel_modify", {}).level, cl.RISKY)

    def test_git_push_main_is_risky(self) -> None:
        self.assertEqual(cl.classify("git_push_main", {}).level, cl.RISKY)

    def test_git_force_push_is_risky(self) -> None:
        self.assertEqual(cl.classify("git_force_push", {}).level, cl.RISKY)

    def test_kernel_override_is_risky(self) -> None:
        self.assertEqual(cl.classify("kernel_override", {}).level, cl.RISKY)

    def test_canonical_flag_overrides_safe_action(self) -> None:
        # Even a normally-safe read becomes RISKY if canonical=True is set
        # (rule precedence — canonical signal wins).
        c = cl.classify("read", {"canonical": True})
        self.assertEqual(c.level, cl.RISKY)
        self.assertEqual(c.reason_code, "canonical_path")

    def test_canonical_false_does_not_escalate(self) -> None:
        # Explicit False must NOT escalate (kills literal-value mutations
        # like `is True` → `is not None`).
        c = cl.classify("read", {"canonical": False})
        self.assertEqual(c.level, cl.SAFE)


# ---------------------------------------------------------------------------
# classify() — NEEDS_CONFIRM rules
# ---------------------------------------------------------------------------


class TestClassifyNeedsConfirm(unittest.TestCase):
    def test_write_is_needs_confirm(self) -> None:
        c = cl.classify("write", {})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)
        self.assertEqual(c.reason_code, "write")

    def test_edit_is_needs_confirm(self) -> None:
        self.assertEqual(cl.classify("edit", {}).level, cl.NEEDS_CONFIRM)

    def test_bash_execute_is_needs_confirm(self) -> None:
        self.assertEqual(cl.classify("bash_execute", {}).level, cl.NEEDS_CONFIRM)

    def test_unknown_action_is_needs_confirm(self) -> None:
        # Fail-medium invariant.
        c = cl.classify("totally_unknown_xyz", {})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)
        self.assertEqual(c.reason_code, "unknown_action")

    def test_empty_action_type_is_needs_confirm(self) -> None:
        c = cl.classify("", {})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)
        self.assertEqual(c.reason_code, "empty_action_type")

    def test_non_string_action_type_is_needs_confirm(self) -> None:
        # Defensive: caller passes wrong type → fail-medium not crash.
        c = cl.classify(None, {})  # type: ignore[arg-type]
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)


# ---------------------------------------------------------------------------
# classify() — context-driven escalation
# ---------------------------------------------------------------------------


class TestClassifyContextEscalation(unittest.TestCase):
    def test_trading_profile_escalates_write_to_risky(self) -> None:
        c = cl.classify("write", {"profile": "trading-readonly"})
        self.assertEqual(c.level, cl.RISKY)
        self.assertEqual(c.reason_code, "trading_profile_write")

    def test_non_trading_profile_does_not_escalate(self) -> None:
        c = cl.classify("write", {"profile": "fintech"})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)

    def test_bulk_threshold_boundary_below(self) -> None:
        # file_count == threshold (10) → still NEEDS_CONFIRM (kills `>` vs `>=`).
        c = cl.classify("write", {"file_count": 10})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)

    def test_bulk_threshold_boundary_above(self) -> None:
        c = cl.classify("write", {"file_count": 11})
        self.assertEqual(c.level, cl.RISKY)
        self.assertEqual(c.reason_code, "bulk_op")

    def test_bulk_zero_files_stays_confirm(self) -> None:
        c = cl.classify("write", {"file_count": 0})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)

    def test_bulk_count_non_int_ignored(self) -> None:
        # Defensive: non-int file_count must not escalate.
        c = cl.classify("write", {"file_count": "many"})
        self.assertEqual(c.level, cl.NEEDS_CONFIRM)


# ---------------------------------------------------------------------------
# Marker / display
# ---------------------------------------------------------------------------


class TestEmojiFreeMarker(unittest.TestCase):
    def test_safe_marker(self) -> None:
        self.assertEqual(
            cl.as_emoji_free_marker(cl.Confidence(level=cl.SAFE, reason_code="x")),
            "[SAFE]",
        )

    def test_needs_confirm_marker(self) -> None:
        self.assertEqual(
            cl.as_emoji_free_marker(
                cl.Confidence(level=cl.NEEDS_CONFIRM, reason_code="x")
            ),
            "[NEEDS-CONFIRM]",
        )

    def test_risky_marker(self) -> None:
        self.assertEqual(
            cl.as_emoji_free_marker(cl.Confidence(level=cl.RISKY, reason_code="x")),
            "[RISKY]",
        )

    def test_marker_rejects_non_confidence(self) -> None:
        with self.assertRaises(TypeError):
            cl.as_emoji_free_marker("safe")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# prompt_for_confirmation
# ---------------------------------------------------------------------------


class TestPromptForConfirmation(unittest.TestCase):
    def _make(self, level: str) -> cl.Confidence:
        return cl.Confidence(level=level, reason_code="t")

    def test_safe_auto_true(self) -> None:
        out = io.StringIO()
        result = cl.prompt_for_confirmation(
            self._make(cl.SAFE), "do thing",
            stdin=io.StringIO(""), stdout=out, env={},
        )
        self.assertTrue(result)
        # No prompt written for SAFE.
        self.assertEqual(out.getvalue(), "")

    def test_risky_refused_without_env(self) -> None:
        self.assertFalse(
            cl.prompt_for_confirmation(
                self._make(cl.RISKY), "danger",
                stdin=io.StringIO("yes\n"),  # even "yes" must not unblock
                stdout=io.StringIO(),
                env={},
            )
        )

    def test_risky_allowed_with_exact_env(self) -> None:
        env = {cl.ENV_BYPASS_RISKY: cl.ENV_BYPASS_RISKY_VALUE}
        self.assertTrue(
            cl.prompt_for_confirmation(
                self._make(cl.RISKY), "danger",
                stdin=io.StringIO(""), stdout=io.StringIO(),
                env=env,
            )
        )

    def test_risky_refused_with_truthy_alias(self) -> None:
        # Exact-value contract: "1", "true", "yes" must NOT unblock.
        for alias in ("1", "true", "yes", "I-Accept-Consequences"):
            env = {cl.ENV_BYPASS_RISKY: alias}
            self.assertFalse(
                cl.prompt_for_confirmation(
                    self._make(cl.RISKY), "danger",
                    stdin=io.StringIO(""), stdout=io.StringIO(),
                    env=env,
                ),
                msg="alias " + alias + " unexpectedly unblocked RISKY",
            )

    def test_needs_confirm_yes_via_stdin(self) -> None:
        self.assertTrue(
            cl.prompt_for_confirmation(
                self._make(cl.NEEDS_CONFIRM), "edit file",
                stdin=io.StringIO("y\n"), stdout=io.StringIO(),
                env={},
            )
        )

    def test_needs_confirm_yes_word_via_stdin(self) -> None:
        self.assertTrue(
            cl.prompt_for_confirmation(
                self._make(cl.NEEDS_CONFIRM), "edit file",
                stdin=io.StringIO("YES\n"), stdout=io.StringIO(),
                env={},
            )
        )

    def test_needs_confirm_no_via_stdin(self) -> None:
        self.assertFalse(
            cl.prompt_for_confirmation(
                self._make(cl.NEEDS_CONFIRM), "edit file",
                stdin=io.StringIO("n\n"), stdout=io.StringIO(),
                env={},
            )
        )

    def test_needs_confirm_eof_refuses(self) -> None:
        self.assertFalse(
            cl.prompt_for_confirmation(
                self._make(cl.NEEDS_CONFIRM), "edit file",
                stdin=io.StringIO(""), stdout=io.StringIO(),
                env={},
            )
        )

    def test_needs_confirm_auto_via_env(self) -> None:
        env = {cl.ENV_AUTO_CONFIRM: cl.ENV_AUTO_CONFIRM_VALUE}
        self.assertTrue(
            cl.prompt_for_confirmation(
                self._make(cl.NEEDS_CONFIRM), "edit file",
                stdin=io.StringIO(""),  # stdin not consulted
                stdout=io.StringIO(),
                env=env,
            )
        )

    def test_needs_confirm_auto_env_must_be_exact(self) -> None:
        # "yes" / "true" / "0" must NOT auto-confirm.
        for alias in ("yes", "true", "0", "True", " 1 "):
            env = {cl.ENV_AUTO_CONFIRM: alias}
            self.assertFalse(
                cl.prompt_for_confirmation(
                    self._make(cl.NEEDS_CONFIRM), "edit",
                    stdin=io.StringIO(""), stdout=io.StringIO(),
                    env=env,
                ),
                msg="alias " + alias + " unexpectedly auto-confirmed",
            )


# ---------------------------------------------------------------------------
# Invariants — idempotence + no-leak
# ---------------------------------------------------------------------------


class TestInvariants(unittest.TestCase):
    def test_classify_is_idempotent(self) -> None:
        ctx = {"profile": "fintech", "file_count": 3}
        a = cl.classify("write", ctx)
        b = cl.classify("write", ctx)
        c = cl.classify("write", ctx)
        self.assertEqual(a, b)
        self.assertEqual(b, c)

    def test_return_value_does_not_carry_paths_or_content(self) -> None:
        # Sec MF-3 style: caller may include a "path" key in context with
        # a sensitive path; classify() must not echo it back.
        ctx = {
            "path": "/Users/secret/api_key_eyJsensitiveJWT.txt",
            "content": "AKIAIOSFODNN7EXAMPLE",
            "token": "sk-abc123" + "x" * 30,
            "canonical": True,
        }
        c = cl.classify("write", ctx)
        # Reason_code and level should be the only string fields.
        joined = c.level + "|" + c.reason_code
        self.assertNotIn("/Users/", joined)
        self.assertNotIn("AKIA", joined)
        self.assertNotIn("sk-", joined)
        self.assertNotIn("eyJ", joined)
        # Frozen dataclass — no extra attributes.
        with self.assertRaises(AttributeError):
            c.path = "x"  # type: ignore[misc]

    def test_confidence_constructor_rejects_unknown_level(self) -> None:
        with self.assertRaises(ValueError):
            cl.Confidence(level="maybe", reason_code="x")

    def test_all_levels_constant_matches_known_values(self) -> None:
        self.assertEqual(set(cl.ALL_LEVELS), {cl.SAFE, cl.NEEDS_CONFIRM, cl.RISKY})
        # No accidental duplicates.
        self.assertEqual(len(cl.ALL_LEVELS), 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
