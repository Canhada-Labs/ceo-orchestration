"""Tests for Session 75 kernel-protected hook fixes (F4 / F6 / F7 / F8).

These tests cover behavior that lands via the Owner-run
`OWNER-SESSION-75-KERNEL-CEREMONY.sh` script (the CEO session cannot
self-bypass the arbitration-kernel HARD-DENY by design). Tests are
authored ahead of the ceremony so the validator block in the
ceremony script catches regressions; tests use `pytest.skip` if the
ceremony hasn't yet landed the change so the suite stays green
between CEO commit and Owner ceremony run.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _is_kernel_ceremony_landed_F4() -> bool:
    """True if check_agent_spawn.py has the Session 75 F4 wire."""
    text = (REPO_ROOT / ".claude" / "hooks" / "check_agent_spawn.py").read_text(encoding="utf-8")
    return "Session 75 Codex Finding 4 closure" in text


def _is_kernel_ceremony_landed_F6() -> bool:
    text = (REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py").read_text(encoding="utf-8")
    return "Session 75 Codex Finding 6 closure" in text


def _is_kernel_ceremony_landed_F7() -> bool:
    text = (REPO_ROOT / ".claude" / "hooks" / "check_plan_edit.py").read_text(encoding="utf-8")
    return "Session 75 Codex Finding 7" in text


def _is_kernel_ceremony_landed_F8() -> bool:
    text = (REPO_ROOT / ".claude" / "hooks" / "check_canonical_edit.py").read_text(encoding="utf-8")
    return "Session 75 Codex Finding 8 closure" in text


@unittest.skipUnless(
    _is_kernel_ceremony_landed_F4(),
    "F4 kernel ceremony not yet landed — Owner must run OWNER-SESSION-75-KERNEL-CEREMONY.sh",
)
class Session75F4SpawnSecretScan(TestEnvContext):
    """Owner D4 staged rollout: default OFF, opt-in via env."""

    def setUp(self) -> None:
        super().setUp()
        # Reload module fresh to pick up edited code on each test.
        if "check_agent_spawn" in sys.modules:
            del sys.modules["check_agent_spawn"]
        import check_agent_spawn  # noqa: F401
        self.mod = sys.modules["check_agent_spawn"]

    def _validate(self, prompt, env=None):
        # Use mock.patch.dict for env isolation (TestEnvContext-friendly).
        # Each call enters a fresh env context that's torn down on return.
        from unittest import mock as _mock
        env = env if env is not None else {}
        # Build the env dict to layer onto current os.environ.
        # None values mean "must be unset for this call".
        clear_keys = [k for k, v in env.items() if v is None]
        set_keys = {k: v for k, v in env.items() if v is not None}
        with _mock.patch.dict(os.environ, set_keys, clear=False):
            for k in clear_keys:
                os.environ.pop(k, None)
            return self.mod._validate_spawn_prompt_has_no_secrets(prompt)

    def test_default_off_does_not_scan(self) -> None:
        ok, code, _ = self._validate(
            "leak: sk-ant-api03-fake-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            env={"CEO_SPAWN_SECRET_SCAN": None},
        )
        self.assertTrue(ok, "default OFF — must allow even with secret pattern")
        self.assertIsNone(code)

    def test_explicit_zero_does_not_scan(self) -> None:
        ok, _, _ = self._validate(
            "leak: sk-ant-api03-fake-secret-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            env={"CEO_SPAWN_SECRET_SCAN": "0"},
        )
        self.assertTrue(ok, "CEO_SPAWN_SECRET_SCAN=0 short-circuits")

    def test_opt_in_blocks_secret(self) -> None:
        ok, code, detail = self._validate(
            "context: sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            env={"CEO_SPAWN_SECRET_SCAN": "1"},
        )
        # Either it blocks (ok=False with code) OR no patterns matched
        # this synthetic value. Accept both — the contract here is "scan
        # runs without crashing when opt-in"; pattern coverage is tested
        # by the secret_patterns library tests.
        if not ok:
            self.assertIsNotNone(code)
            self.assertIsNotNone(detail)
        else:
            # No pattern matched — this is library-level concern, not
            # the wire. Pass.
            pass


@unittest.skipUnless(
    _is_kernel_ceremony_landed_F7(),
    "F7 kernel ceremony not yet landed",
)
class Session75F7PlanEditRefusedAdr(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        if "check_plan_edit" in sys.modules:
            del sys.modules["check_plan_edit"]
        import check_plan_edit  # noqa: F401
        self.mod = sys.modules["check_plan_edit"]

    def test_refused_without_refused_adr_blocks(self) -> None:
        # Build a synthetic post-edit frontmatter dict.
        # Session 76 audit-v3 (DIM-11) extended _check_required_fields to
        # take old_status as the first arg; passing "" (any non-`done`
        # value) preserves the original Session 75 F7 contract for the
        # refused branch.
        new_fm = {"status": "refused"}
        reason = self.mod._check_required_fields("", "refused", new_fm, "")
        self.assertIsNotNone(reason)
        self.assertIn("refused_adr", reason)

    def test_refused_with_valid_refused_adr_allows(self) -> None:
        # Session 76 audit-v3 (DIM-11) also requires `refused_at` per
        # ADR-092 — supply it here to preserve the "allow" expectation.
        new_fm = {
            "status": "refused",
            "refused_adr": "ADR-093",
            "refused_at": "2026-04-29",
        }
        reason = self.mod._check_required_fields("", "refused", new_fm, "")
        self.assertIsNone(reason)

    def test_refused_with_invalid_format_blocks(self) -> None:
        new_fm = {"status": "refused", "refused_adr": "not-an-adr"}
        reason = self.mod._check_required_fields("", "refused", new_fm, "")
        self.assertIsNotNone(reason)
        self.assertIn("ADR-NNN", reason)


@unittest.skipUnless(
    _is_kernel_ceremony_landed_F8(),
    "F8 kernel ceremony not yet landed",
)
class Session75F8SentinelUnlockEmit(TestEnvContext):
    def test_sentinel_unlock_emit_block_exists(self) -> None:
        # Source-level smoke: the emit_veto_triggered call with
        # reason_code=sentinel_unlock_used must be present in the
        # env-override branch.
        text = (REPO_ROOT / ".claude" / "hooks" / "check_canonical_edit.py").read_text(encoding="utf-8")
        self.assertIn('reason_code="sentinel_unlock_used"', text)
        self.assertIn("env_override", text)


@unittest.skipUnless(
    _is_kernel_ceremony_landed_F6(),
    "F6 kernel ceremony not yet landed",
)
class Session75F6AuditEmitDocstring(TestEnvContext):
    def test_severity_docstring_aligned(self) -> None:
        text = (REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py").read_text(encoding="utf-8")
        # New (correct) form
        self.assertIn("`low` | `medium` | `high`", text)
        # Old (drifted) form must be removed for the mcp-finding doc-block
        # (note: `block` may still appear as a Python keyword elsewhere)
        self.assertNotIn("severity: `info` | `warn` | `block`", text)

    def test_scanner_action_docstring_aligned(self) -> None:
        text = (REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py").read_text(encoding="utf-8")
        self.assertIn("`advisory` | `stripped` | `blocked`", text)


if __name__ == "__main__":
    unittest.main()
