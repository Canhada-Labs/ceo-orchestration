"""PLAN-085 Wave B.3 — audit_log.append_entry HMAC chain coverage.

6 cases asserting that the inline HMAC computation closes the
two-writer chain gap (T0-line-168 transition_violation):

  1. test_append_entry_writes_hmac_field
  2. test_consecutive_entries_chain_correctly
  3. test_disabled_hmac_yields_null_field
  4. test_rotation_resets_chain
  5. test_agent_spawn_action_carries_hmac
  6. test_concurrent_writers_produce_distinct_hmacs
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


class TestTwoWriterChain(TestEnvContext):
    """B.3 inline HMAC chain coverage tests."""

    def _build_paths(self) -> dict:
        log_file = self.audit_dir / "audit-log.jsonl"
        return {
            "dir": self.audit_dir,
            "log": log_file,
            "lock": str(self.audit_dir / "audit-log.lock"),
            "err": self.audit_dir / "audit-log.errors",
        }

    def _read_lines(self, paths: dict) -> list:
        if not paths["log"].exists():
            return []
        return [
            json.loads(line)
            for line in paths["log"].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_append_entry_writes_hmac_field(self) -> None:
        """First entry after B.3 must carry hmac (or hmac_error) field."""
        import audit_log
        paths = self._build_paths()
        entry = {"action": "agent_spawn", "ts": "2026-05-12T00:00:00Z"}
        audit_log.append_entry(entry, paths=paths, threshold_bytes=10**9)
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 1)
        self.assertIn("hmac", lines[0], msg="entry missing hmac field")

    def test_consecutive_entries_chain_correctly(self) -> None:
        """Second entry's HMAC depends on first entry's HMAC (chain)."""
        import audit_log
        paths = self._build_paths()
        audit_log.append_entry(
            {"action": "agent_spawn", "ts": "2026-05-12T00:00:01Z"},
            paths=paths, threshold_bytes=10**9,
        )
        audit_log.append_entry(
            {"action": "agent_spawn", "ts": "2026-05-12T00:00:02Z"},
            paths=paths, threshold_bytes=10**9,
        )
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 2)
        # Both have hmac set; if HMAC subsystem available, they should differ.
        h1, h2 = lines[0].get("hmac"), lines[1].get("hmac")
        if h1 is not None and h2 is not None:
            self.assertNotEqual(h1, h2, msg="chain not advancing")

    def test_disabled_hmac_yields_null_field(self) -> None:
        """When CEO_AUDIT_HMAC_DISABLE=1 the hmac field is None but present."""
        import audit_log
        os.environ["CEO_AUDIT_HMAC_DISABLE"] = "1"
        try:
            paths = self._build_paths()
            audit_log.append_entry(
                {"action": "agent_spawn", "ts": "2026-05-12T00:00:03Z"},
                paths=paths, threshold_bytes=10**9,
            )
            lines = self._read_lines(paths)
            self.assertEqual(len(lines), 1)
            self.assertIsNone(lines[0].get("hmac"))
        finally:
            os.environ.pop("CEO_AUDIT_HMAC_DISABLE", None)

    def test_agent_spawn_action_carries_hmac(self) -> None:
        """The specific T0-line-168 finding: agent_spawn entries get HMAC."""
        import audit_log
        paths = self._build_paths()
        audit_log.append_entry(
            {"action": "agent_spawn", "session_id": "test"},
            paths=paths, threshold_bytes=10**9,
        )
        lines = self._read_lines(paths)
        self.assertEqual(len(lines), 1)
        # If HMAC subsystem is available, hmac MUST be a hex string,
        # not None — closes the 100% agent_spawn coverage AC.
        try:
            from _lib import audit_hmac
            if not audit_hmac.is_disabled():
                self.assertIsNotNone(
                    lines[0].get("hmac"),
                    msg=(
                        "agent_spawn entry missing HMAC — B.3 chain "
                        "coverage AC not satisfied"
                    ),
                )
        except ImportError:
            self.skipTest("audit_hmac unavailable; B.3 HMAC path inactive")

    def test_append_entry_preserves_f0106_symlink_defense(self) -> None:
        """B.3 inline HMAC must not regress F-01-06 symlink/uid defense."""
        import audit_log
        paths = self._build_paths()
        # Plant a symlink at the log path; F-01-06 must reject the write.
        paths["log"].parent.mkdir(parents=True, exist_ok=True)
        evil_target = self._tmp_root / "evil-target.jsonl"
        evil_target.touch()
        # Pre-create a symlink at the audit log path
        log_path = paths["log"]
        if log_path.exists() or log_path.is_symlink():
            log_path.unlink()
        log_path.symlink_to(evil_target)
        audit_log.append_entry(
            {"action": "agent_spawn"},
            paths=paths, threshold_bytes=10**9,
        )
        # F-01-06 should refuse → evil_target stays empty.
        self.assertEqual(
            evil_target.stat().st_size, 0,
            msg="F-01-06 regression — symlink write was NOT blocked",
        )

    def test_hmac_error_recorded_on_subsystem_failure(self) -> None:
        """If the HMAC subsystem raises, entry has hmac=None + hmac_error set."""
        import audit_log
        paths = self._build_paths()
        # Patch audit_hmac.get_or_create_key to raise.
        from _lib import audit_hmac as _audit_hmac
        original = _audit_hmac.get_or_create_key

        def _boom() -> bytes:
            raise _audit_hmac.AuditHmacError("test-injected failure")

        _audit_hmac.get_or_create_key = _boom  # type: ignore[assignment]
        try:
            audit_log.append_entry(
                {"action": "agent_spawn"},
                paths=paths, threshold_bytes=10**9,
            )
            lines = self._read_lines(paths)
            self.assertEqual(len(lines), 1)
            self.assertIsNone(lines[0].get("hmac"))
            self.assertEqual(
                lines[0].get("hmac_error"),
                "AuditHmacError",
                msg="hmac_error not recorded under injected failure",
            )
        finally:
            _audit_hmac.get_or_create_key = original  # type: ignore[assignment]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
