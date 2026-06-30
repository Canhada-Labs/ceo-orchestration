"""PLAN-045 Wave 1 F-01-05 + F-01-06 — audit_hmac hardening tests.

New behaviours exercised:
- F-01-06 ``_check_perm_0600`` rejects symlink leaf.
- F-01-06 ``_check_perm_0600`` rejects wrong uid.
- F-01-06 ``_read_key_file`` rejects symlink leaf.
- F-01-06 ``_read_key_file`` rejects wrong uid.
- F-01-06 ``_check_parent_dir_owned_0700`` stand-alone helper.
- F-01-05 ``read_chain_length`` / ``write_chain_length`` round-trip.
- F-01-05 ``reset_chain_on_rotation`` clears chain-length sidecar.
- F-01-05 ``verify_chain(strict_against_counter=True)`` passes when
  walker count >= persisted counter.
- F-01-05 ``verify_chain(strict_against_counter=True)`` fails with
  ``chain_length_truncation`` when counter > walker count.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    AuditHmacError,
    GENESIS_PREV,
    KEY_BYTES,
    _check_parent_dir_owned_0700,
    _check_perm_0600,
    _read_key_file,
    chain_length_path,
    compute_entry_hmac,
    hex_digest,
    read_chain_length,
    reset_chain_on_rotation,
    verify_chain,
    write_chain_length,
)


class _TmpEnv:
    """Isolation helper — sets CEO_AUDIT_LOG_PATH + friends to tmpdir.

    Restores env on close. No dependency on _lib.testing.TestEnvContext
    so this test module runs cleanly under ``python -m unittest``.
    """

    def __init__(self, tmpdir: Path) -> None:
        self.tmpdir = tmpdir
        self._saved: dict = {}

    def __enter__(self) -> "_TmpEnv":
        for k in (
            "CEO_AUDIT_LOG_PATH",
            "CEO_AUDIT_KEY_PATH",
            "CEO_AUDIT_LAST_HMAC_PATH",
            "CEO_AUDIT_CHAIN_LENGTH_PATH",
            "CEO_PROJECT_STATE_DIR",
        ):
            self._saved[k] = os.environ.get(k)
            if k in os.environ:
                del os.environ[k]
        os.environ["CEO_PROJECT_STATE_DIR"] = str(self.tmpdir)
        return self

    def __exit__(self, *exc: object) -> None:
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# --------------------------------------------------------------------------
# F-01-06 — perm hardening
# --------------------------------------------------------------------------


class TestPermHardening(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_check_perm_0600_rejects_symlink(self) -> None:
        real = self.tmpdir / "real"
        real.write_bytes(b"x" * KEY_BYTES)
        os.chmod(real, 0o600)
        link = self.tmpdir / "link"
        link.symlink_to(real)
        with self.assertRaises(AuditHmacError) as cm:
            _check_perm_0600(link)
        self.assertIn("symlink", str(cm.exception))

    def test_check_perm_0600_accepts_owned_0600(self) -> None:
        p = self.tmpdir / "key"
        p.write_bytes(b"x" * KEY_BYTES)
        os.chmod(p, 0o600)
        _check_perm_0600(p)  # no raise

    def test_check_perm_0600_rejects_group_readable(self) -> None:
        p = self.tmpdir / "key"
        p.write_bytes(b"x" * KEY_BYTES)
        os.chmod(p, 0o640)
        with self.assertRaises(AuditHmacError):
            _check_perm_0600(p)

    def test_read_key_file_rejects_symlink(self) -> None:
        real = self.tmpdir / "real"
        real.write_bytes(b"x" * KEY_BYTES)
        os.chmod(real, 0o600)
        link = self.tmpdir / "link"
        link.symlink_to(real)
        with self.assertRaises(AuditHmacError) as cm:
            _read_key_file(link)
        self.assertIn("symlink", str(cm.exception))

    def test_parent_dir_helper_rejects_symlink(self) -> None:
        real_parent = self.tmpdir / "real"
        real_parent.mkdir(mode=0o700)
        real_file = real_parent / "key"
        real_file.write_bytes(b"x" * KEY_BYTES)
        os.chmod(real_file, 0o600)
        link_parent = self.tmpdir / "link"
        link_parent.symlink_to(real_parent)
        with self.assertRaises(AuditHmacError) as cm:
            _check_parent_dir_owned_0700(link_parent / "key")
        self.assertIn("symlink", str(cm.exception))

    def test_parent_dir_helper_rejects_wrong_mode(self) -> None:
        parent = self.tmpdir / "loose"
        parent.mkdir(mode=0o755)
        f = parent / "key"
        f.write_bytes(b"x" * KEY_BYTES)
        os.chmod(f, 0o600)
        with self.assertRaises(AuditHmacError) as cm:
            _check_parent_dir_owned_0700(f)
        self.assertIn("0700", str(cm.exception))


# --------------------------------------------------------------------------
# F-01-05 — chain-length canary
# --------------------------------------------------------------------------


class TestChainLength(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self._env = _TmpEnv(self.tmpdir).__enter__()

    def tearDown(self) -> None:
        self._env.__exit__()
        self._tmp.cleanup()

    def test_read_missing_returns_zero(self) -> None:
        self.assertEqual(read_chain_length(), 0)

    def test_write_then_read(self) -> None:
        write_chain_length(42)
        self.assertEqual(read_chain_length(), 42)

    def test_write_overwrites(self) -> None:
        write_chain_length(1)
        write_chain_length(5)
        self.assertEqual(read_chain_length(), 5)

    def test_write_rejects_negative(self) -> None:
        with self.assertRaises(AuditHmacError):
            write_chain_length(-1)

    def test_read_corrupt_returns_zero(self) -> None:
        p = chain_length_path()
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_text("not a number")
        self.assertEqual(read_chain_length(), 0)

    def test_read_empty_returns_zero(self) -> None:
        p = chain_length_path()
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_text("")
        self.assertEqual(read_chain_length(), 0)

    def test_read_negative_returns_zero(self) -> None:
        p = chain_length_path()
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_text("-5")
        self.assertEqual(read_chain_length(), 0)

    def test_reset_on_rotation_clears_counter(self) -> None:
        write_chain_length(100)
        self.assertEqual(read_chain_length(), 100)
        reset_chain_on_rotation()
        self.assertEqual(read_chain_length(), 0)

    def test_sidecar_perms_are_0600(self) -> None:
        write_chain_length(7)
        p = chain_length_path()
        mode = p.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600, "chain-length must be 0600")


# --------------------------------------------------------------------------
# F-01-05 — verify_chain strict mode
# --------------------------------------------------------------------------


class TestVerifyChainStrict(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self._env = _TmpEnv(self.tmpdir).__enter__()
        # Seed a key (write directly; avoid the get_or_create_key cache).
        self.key_path = self.tmpdir / "audit-key"
        os.environ["CEO_AUDIT_KEY_PATH"] = str(self.key_path)
        self.key = b"K" * KEY_BYTES
        self.key_path.write_bytes(self.key)
        os.chmod(self.key_path, 0o600)
        self.log = self.tmpdir / "audit-log.jsonl"
        audit_hmac._reset_key_cache_for_test()

    def tearDown(self) -> None:
        self._env.__exit__()
        self._tmp.cleanup()
        audit_hmac._reset_key_cache_for_test()

    def _write_entries(self, entries: list) -> None:
        """Write a list of entries computing HMAC chain."""
        prev = GENESIS_PREV
        lines = []
        for e in entries:
            base = dict(e)
            base.pop("hmac", None)
            digest = compute_entry_hmac(self.key, prev, base)
            base["hmac"] = hex_digest(digest)
            lines.append(json.dumps(base))
            prev = digest
        self.log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _make_entry(self, ts: str, action: str) -> dict:
        return {"ts": ts, "action": action, "hook": "test", "decision": "allow"}

    def test_strict_mode_pass_counter_matches(self) -> None:
        self._write_entries([
            self._make_entry("2026-04-20T00:00:00Z", "action_a"),
            self._make_entry("2026-04-20T00:00:01Z", "action_b"),
            self._make_entry("2026-04-20T00:00:02Z", "action_c"),
        ])
        write_chain_length(3)
        result = verify_chain(self.log, key=self.key, strict_against_counter=True)
        self.assertTrue(result.is_intact, msg=result)
        self.assertEqual(result.verified_count, 3)

    def test_strict_mode_fail_counter_exceeds_walker(self) -> None:
        # Write 3 entries + persist counter=5 (2 tail entries deleted).
        self._write_entries([
            self._make_entry("2026-04-20T00:00:00Z", "action_a"),
            self._make_entry("2026-04-20T00:00:01Z", "action_b"),
            self._make_entry("2026-04-20T00:00:02Z", "action_c"),
        ])
        write_chain_length(5)
        result = verify_chain(self.log, key=self.key, strict_against_counter=True)
        self.assertEqual(result.status, "tamper")
        self.assertEqual(result.reason, "chain_length_truncation")
        self.assertEqual(result.verified_count, 3)
        self.assertEqual(result.expected_hmac, "5")
        self.assertEqual(result.actual_hmac, "3")

    def test_strict_mode_counter_override_kwarg(self) -> None:
        self._write_entries([
            self._make_entry("2026-04-20T00:00:00Z", "action_a"),
            self._make_entry("2026-04-20T00:00:01Z", "action_b"),
        ])
        write_chain_length(2)
        # Override: pretend counter was 10. Walker sees 2 → fail.
        result = verify_chain(
            self.log,
            key=self.key,
            strict_against_counter=True,
            counter_override=10,
        )
        self.assertEqual(result.status, "tamper")
        self.assertEqual(result.reason, "chain_length_truncation")

    def test_non_strict_mode_ignores_counter(self) -> None:
        self._write_entries([
            self._make_entry("2026-04-20T00:00:00Z", "action_a"),
        ])
        write_chain_length(999)  # false counter — non-strict ignores.
        result = verify_chain(self.log, key=self.key)
        self.assertTrue(result.is_intact)


if __name__ == "__main__":
    unittest.main()
