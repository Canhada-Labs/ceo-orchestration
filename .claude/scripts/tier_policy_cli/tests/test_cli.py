"""PLAN-043 Phase 4 — tier_policy.cli unit tests (~20 tests).

Covers derive / apply / verify / show / enable / owner-sign / migrate /
rotate-key / sigchain-rotate subcommands. Focus on entry-point
correctness + argument parsing + error paths + Owner allowlist gate.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from unittest import mock

_SCRIPTS = Path(__file__).resolve().parent.parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from tier_policy_cli import cli  # noqa: E402


_OPUS = "claude-opus-4-8"
_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"


def _valid_policy_dict():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-04-19T00:00:00Z",
        "baseline_from": "ADR-052",
        "assignments": {
            "code-reviewer": {
                "tier": _OPUS, "locked_by": "VETO_FLOOR",
                "evidence": None,
            },
            "security-engineer": {
                "tier": _OPUS, "locked_by": "VETO_FLOOR",
                "evidence": None,
            },
            "qa-architect": {
                "tier": _SONNET, "locked_by": None, "evidence": None,
            },
            "performance-engineer": {
                "tier": _SONNET, "locked_by": None, "evidence": None,
            },
            "devops": {
                "tier": _HAIKU, "locked_by": None, "evidence": None,
            },
        },
        "hmac_anchor": "f" * 64,
        "sigchain_tip_length": 1,
        "last_change_by_role": {},
    }


class CliTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-043-cli-")
        self.tmp = Path(self._tmp.name)
        self.policy_path = self.tmp / "tier-policy.json"
        self.sigchain_path = self.tmp / "tier-policy.json.sigchain"
        self.reports_dir = self.tmp / "reports"
        self.owners_file = self.tmp / "owners.txt"
        self.reports_dir.mkdir()
        self._stdout = io.StringIO()
        self._stderr = io.StringIO()
        self._stdout_patch = mock.patch("sys.stdout", self._stdout)
        self._stderr_patch = mock.patch("sys.stderr", self._stderr)
        self._stdout_patch.start()
        self._stderr_patch.start()

    def tearDown(self):
        self._stdout_patch.stop()
        self._stderr_patch.stop()
        self._tmp.cleanup()


# ---------------------------------------------------------------------
# Group A — Parser + basic dispatch
# ---------------------------------------------------------------------

class ParserTests(unittest.TestCase):
    def test_parser_has_all_required_subcommands(self):
        p = cli.build_parser()
        subs = sorted(
            p._subparsers._group_actions[0].choices.keys()
        )
        expected = sorted([
            "derive", "apply", "owner-sign", "verify", "show",
            "enable", "migrate", "rotate-key", "sigchain-rotate",
        ])
        self.assertEqual(subs, expected)

    def test_parser_missing_command_errors(self):
        p = cli.build_parser()
        with self.assertRaises(SystemExit):
            p.parse_args([])


# ---------------------------------------------------------------------
# Group B — Show
# ---------------------------------------------------------------------

class ShowTests(CliTestBase):
    def test_show_falls_back_to_baseline_when_artifact_absent(self):
        rc = cli.main(["show", "--policy", str(self.policy_path)])
        self.assertEqual(rc, 0)
        out = self._stdout.getvalue()
        self.assertIn("ADR-052", out)
        # ADR-149 (W0 variant A): baseline VETO tier = claude-fable-5.
        self.assertIn("claude-fable-5", out)

    def test_show_prints_assignments_when_artifact_present(self):
        self.policy_path.write_text(
            json.dumps(_valid_policy_dict()), encoding="utf-8"
        )
        rc = cli.main(["show", "--policy", str(self.policy_path)])
        self.assertEqual(rc, 0)
        out = self._stdout.getvalue()
        self.assertIn("qa-architect", out)
        self.assertIn("claude-sonnet-4-6", out)
        self.assertIn("[LOCKED:VETO_FLOOR]", out)


# ---------------------------------------------------------------------
# Group C — Derive
# ---------------------------------------------------------------------

class DeriveTests(CliTestBase):
    def test_derive_emits_empty_json_array_on_no_reports(self):
        self.policy_path.write_text(
            json.dumps(_valid_policy_dict()), encoding="utf-8"
        )
        rc = cli.main([
            "derive",
            "--policy", str(self.policy_path),
            "--reports", str(self.reports_dir),
        ])
        self.assertEqual(rc, 0)
        out = self._stdout.getvalue().strip()
        self.assertEqual(json.loads(out), [])

    def test_derive_without_policy_artifact_uses_baseline(self):
        # Missing artifact → cli synthesizes ADR-052 record for learn.
        rc = cli.main([
            "derive",
            "--policy", str(self.policy_path),  # doesn't exist
            "--reports", str(self.reports_dir),
        ])
        self.assertEqual(rc, 0)


# ---------------------------------------------------------------------
# Group D — Verify
# ---------------------------------------------------------------------

class VerifyTests(CliTestBase):
    def test_verify_bootstrap_when_sigchain_absent(self):
        rc = cli.main([
            "verify", "--sigchain", str(self.sigchain_path),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("bootstrap", self._stdout.getvalue())

    def test_verify_tamper_detection_on_malformed(self):
        self.sigchain_path.write_text(
            "not-json-line\n", encoding="utf-8"
        )
        rc = cli.main([
            "verify", "--sigchain", str(self.sigchain_path),
        ])
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------
# Group E — Migrate
# ---------------------------------------------------------------------

class MigrateTests(CliTestBase):
    def test_migrate_no_op_when_current(self):
        self.policy_path.write_text(
            json.dumps(_valid_policy_dict()), encoding="utf-8"
        )
        rc = cli.main([
            "migrate", "--policy", str(self.policy_path),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("current", self._stdout.getvalue())


# ---------------------------------------------------------------------
# Group F — Owner allowlist gate
# ---------------------------------------------------------------------

class OwnerAllowlistTests(CliTestBase):
    def test_owner_sign_missing_allowlist_file_aborts(self):
        # Mock the git user.email lookup so the test passes the
        # earlier `git user.email unset` guard and reaches the
        # allowlist-file check (which is what this test asserts).
        # CI runners typically have no global git user.email
        # configured; without the mock, the CLI aborts at the
        # earlier guard with a different error message and the
        # `assertIn("allowlist", ...)` assertion fails.
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", _SONNET,
                "--to-tier", _HAIKU,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertNotEqual(rc, 0)
        self.assertIn("allowlist", self._stderr.getvalue())

    def test_owner_sign_bad_sp_chain_id_rejected(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", _SONNET,
                "--to-tier", _HAIKU,
                "--sp-chain-id", "not-a-valid-id",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertEqual(rc, 2)

    def test_owner_sign_invalid_from_tier_rejected(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", "unknown-model-id",
                "--to-tier", _HAIKU,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertEqual(rc, 2)

    def test_owner_sign_non_canonical_agent_rejected(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "fake-agent",
                "--from-tier", _SONNET,
                "--to-tier", _HAIKU,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertEqual(rc, 2)

    def test_owner_sign_non_allowlisted_email_rejected(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email",
            return_value="attacker@example.com",
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", _SONNET,
                "--to-tier", _HAIKU,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertNotEqual(rc, 0)
        self.assertIn("not in allowlist", self._stderr.getvalue())

    def test_owner_sign_no_git_email_rejected(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email", return_value=None
        ):
            rc = cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", _SONNET,
                "--to-tier", _HAIKU,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(self.sigchain_path),
                "--skip-commit",
            ])
        self.assertNotEqual(rc, 0)
        self.assertIn("git user.email unset", self._stderr.getvalue())


# ---------------------------------------------------------------------
# Group G — rotate-key + sigchain-rotate stubs
# ---------------------------------------------------------------------

class RotateKeyStubTests(CliTestBase):
    def test_rotate_key_requires_confirm(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ):
            rc = cli.main([
                "rotate-key",
                "--owners-file", str(self.owners_file),
            ])
        self.assertEqual(rc, 2)
        self.assertIn("--confirm", self._stderr.getvalue())


class SigchainRotateTests(CliTestBase):
    def test_sigchain_rotate_refuses_when_absent(self):
        rc = cli.main([
            "sigchain-rotate",
            "--sigchain", str(self.sigchain_path),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("nothing to rotate", self._stdout.getvalue())

    def test_sigchain_rotate_refuses_under_threshold_without_force(self):
        # Write small sigchain (< 1000 entries).
        with self.sigchain_path.open("w", encoding="utf-8") as f:
            for i in range(3):
                f.write(json.dumps({"chain_length": i + 1}) + "\n")
        rc = cli.main([
            "sigchain-rotate",
            "--sigchain", str(self.sigchain_path),
        ])
        self.assertEqual(rc, 2)
        self.assertIn("refusing without --force", self._stderr.getvalue())


# ---------------------------------------------------------------------
# Group H — Enable
# ---------------------------------------------------------------------

class EnableTests(CliTestBase):
    def test_enable_rejects_non_allowlisted_email(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        sentinel = self.tmp / "sentinel"
        with mock.patch.object(
            cli, "_git_config_email",
            return_value="attacker@example.com",
        ):
            rc = cli.main([
                "enable",
                "--sentinel", str(sentinel),
                "--owners-file", str(self.owners_file),
                "--skip-commit",
            ])
        self.assertNotEqual(rc, 0)

    def test_enable_writes_sentinel_when_allowlisted(self):
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        sentinel = self.tmp / "sentinel_enabled"
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com",
        ), mock.patch.object(
            cli, "_git_head_sha", return_value="a" * 40,
        ):
            rc = cli.main([
                "enable",
                "--sentinel", str(sentinel),
                "--owners-file", str(self.owners_file),
                "--skip-commit",
            ])
        self.assertEqual(rc, 0)
        self.assertTrue(sentinel.exists())
        # Check mode 0600.
        mode = sentinel.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        # Owner-signed content: digest + commit sha.
        content = sentinel.read_text(encoding="utf-8")
        self.assertIn("a" * 40, content)


# ---------------------------------------------------------------------
# Group I — Apply without policy
# ---------------------------------------------------------------------

class ApplyCliTests(CliTestBase):
    def test_apply_without_policy_artifact_errors(self):
        # No policy on disk + apply requires valid record.
        rc = cli.main([
            "apply",
            "--policy", str(self.policy_path),
            "--sigchain", str(self.sigchain_path),
            "--reports", str(self.reports_dir),
        ])
        self.assertEqual(rc, 1)
        self.assertIn("no valid policy artifact", self._stderr.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
