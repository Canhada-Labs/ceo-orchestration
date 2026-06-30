"""PLAN-045 Wave 2 P0-07/08 — audit_emit rotation wire tests.

Validates that `_lib.audit_emit._write_event` now rotates the audit log
at the threshold (via the shared `_lib.audit_rotation` primitive) and
resets the HMAC chain on rotation.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import audit_emit  # noqa: E402
from _lib import audit_hmac  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class AuditEmitRotationTests(TestEnvContext):
    """Exercise the Wave-2 rotation wire end-to-end.

    Inherits TestEnvContext (which is itself a unittest.TestCase) so
    the isolated HOME / CLAUDE_PROJECT_DIR / CEO_AUDIT_LOG_* env is
    set up in super().setUp() and torn down in super().tearDown().
    """

    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_HMAC_ENABLE"] = "1"
        # Reload audit_emit so module-level path helpers pick up the
        # isolated CEO_AUDIT_LOG_* env set by TestEnvContext.setUp().
        importlib.reload(audit_emit)

    def tearDown(self) -> None:
        # Clean any rotate-bytes env we set in individual tests so it
        # doesn't leak through super().tearDown()'s snapshot-based restore.
        os.environ.pop("CEO_AUDIT_LOG_ROTATE_BYTES", None)
        super().tearDown()

    def _emit(self, action: str = "debate_event") -> None:
        """Emit a minimal valid event of the given action."""
        # Use debate_event — action registered in _KNOWN_ACTIONS.
        if action == "debate_event":
            audit_emit.emit_debate_event(
                plan_id="PLAN-TEST",
                round_num=1,
                phase="start",
                agent="test-archetype",
            )
        else:
            # Generic raw _write_event path for other actions.
            audit_emit._write_event({
                "action": action,
                "project": "ceo-orchestration",
            })

    def test_no_rotate_under_threshold(self) -> None:
        """Default 10 MiB threshold not reached → no rotation."""
        self._emit()
        log = audit_emit._log_path()
        self.assertTrue(log.exists())
        # Only the active log file present (plus sidecars).
        jsonl_files = sorted(p.name for p in self.audit_dir.glob("*.jsonl"))
        self.assertEqual(jsonl_files, ["audit-log.jsonl"])

    def test_rotate_at_custom_threshold(self) -> None:
        """Env override threshold triggers rotation on next emit.

        Observable invariants (both hold only with the Wave-2 wire):
        - exactly 1 rotated archive file appears after the 2nd write;
        - the active log contains exactly 1 line post-rotation (the
          fresh entry), not 2.
        """
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "100"  # 100 bytes
        importlib.reload(audit_emit)
        # First emit — creates active log (> 100 bytes after write).
        self._emit()
        self.assertGreater(audit_emit._log_path().stat().st_size, 100)
        # Second emit — rotates the first log, then appends fresh.
        self._emit()
        archives = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertEqual(
            len(archives), 1,
            f"expected 1 rotated archive, got {[p.name for p in archives]}",
        )
        active_lines = sum(
            1 for _ in audit_emit._log_path().open(encoding="utf-8")
        )
        # PLAN-112-FOLLOWUP Wave B.3: post-rotation log contains
        # chain_reset_marker (line 1) + fresh entry (line 2) = 2
        self.assertEqual(
            active_lines, 2,
            "active log post-rotation should hold marker + 1 fresh entry = 2",
        )

    def test_chain_reset_on_rotation(self) -> None:
        """After rotation, HMAC chain restarts from genesis.

        Observable (PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3): the active
        log post-rotation contains chain_reset_marker (line 1) + the
        triggering event (line 2). Pre-fix behavior was 1 entry; the
        new chain_reset_marker per ADR-055-AMEND-2 makes it 2.

        Threshold tuned so rotation triggers between write 2 and 3:
        - write 1 → log has 1 entry (< threshold)
        - write 2 → log has 2 entries (> threshold)
        - write 3 → pre-write rotation → archive with 2 entries;
                    active log now contains chain_reset_marker + write-3
                    (2 entries total).
        """
        # ~380 bytes per event → threshold 400 fits 1 entry but not 2.
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "400"
        importlib.reload(audit_emit)
        self._emit()  # write 1 (log ~380 B, below threshold)
        self._emit()  # write 2 (log ~760 B, above threshold — rotate on next)
        self._emit()  # write 3 → rotate + marker + write into fresh log
        log = audit_emit._log_path()
        active_lines = sum(1 for _ in log.open(encoding="utf-8"))
        # Post-PLAN-112-FOLLOWUP Wave B.3: 1 marker + 1 triggering event = 2
        self.assertEqual(
            active_lines, 2,
            f"active log post-rotate should hold marker + 1 entry = 2, got {active_lines}",
        )
        # Verify line 1 is chain_reset_marker
        import json as _json
        with log.open(encoding="utf-8") as f:
            line_1 = _json.loads(f.readline())
            self.assertEqual(
                line_1.get("action"),
                "chain_reset_marker",
                f"line 1 should be chain_reset_marker, got {line_1.get('action')}",
            )
        archives = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertGreaterEqual(
            len(archives), 1,
            f"expected >=1 archive, got {[p.name for p in archives]}",
        )

    def test_threshold_env_override_respected(self) -> None:
        """Non-integer / negative env values fall back to default."""
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "not-a-number"
        importlib.reload(audit_emit)
        self.assertEqual(
            audit_emit._rotate_threshold(),
            audit_emit._DEFAULT_ROTATE_AT_BYTES,
        )
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "-100"
        self.assertEqual(
            audit_emit._rotate_threshold(),
            audit_emit._DEFAULT_ROTATE_AT_BYTES,
        )
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "50000"
        self.assertEqual(audit_emit._rotate_threshold(), 50000)

    def test_month_slug_format(self) -> None:
        """_now_month_slug returns YYYY-MM."""
        import re
        slug = audit_emit._now_month_slug()
        self.assertRegex(slug, r"^\d{4}-\d{2}$")


if __name__ == "__main__":
    unittest.main()


class RotationTriggerEnumTests(TestEnvContext):
    """PLAN-120-FOLLOWUP WS-D (E4-F4) — the rotation_trigger closed enum
    MUST be enforced symmetrically across the public helper and the
    internal under-lock helper, both via _normalize_rotation_trigger.
    """

    def test_valid_triggers_pass_through(self) -> None:
        for ok in (
            "size_threshold", "manual", "owner_rotation", "quarantine_pre_fix",
        ):
            self.assertEqual(
                audit_emit._normalize_rotation_trigger(ok), ok
            )

    def test_off_enum_free_text_normalizes_to_size_threshold(self) -> None:
        for bad in (
            "", "bogus", "manual; rm -rf /", "OWNER_ROTATION",
            "a" * 200, "\n\tinjected", "size_threshold ",
        ):
            self.assertEqual(
                audit_emit._normalize_rotation_trigger(bad),
                "size_threshold",
                msg="off-enum trigger must fail-open to size_threshold: "
                    + repr(bad),
            )

    def test_non_str_input_does_not_raise(self) -> None:
        for weird in (None, 123, ["manual"], {"x": 1}):
            self.assertEqual(
                audit_emit._normalize_rotation_trigger(weird),
                "size_threshold",
            )

    def test_internal_helper_uses_the_shared_normalizer(self) -> None:
        # Static guarantee that the internal under-lock helper routes the
        # trigger through the shared normalizer rather than a bare
        # str(...)[:32]. Guards against the asymmetric-contract regression
        # E4-F4 identified (internal path bypassing the enum check).
        import inspect
        src = inspect.getsource(
            audit_emit._emit_chain_reset_marker_under_lock
        )
        self.assertIn("_normalize_rotation_trigger(rotation_trigger)", src)
        self.assertNotIn('str(rotation_trigger)[:32]', src)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
