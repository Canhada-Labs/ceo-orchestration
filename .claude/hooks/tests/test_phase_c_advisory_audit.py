"""PLAN-090 Wave A.5 — phase_c_enforcing_flipped idempotent emit.

R1 security-engineer P1 fold: idempotent across multiple ceremony reruns;
pre-flip emit so a crash mid-flip preserves the audit trail. Uses
~/.claude/projects/<project>/state/phase_c_seen.marker as the one-shot
gate file.

R1 TDE P0 fold: behaviour fires under enforcing mode (post-flip) but the
marker check itself runs at session-start in both modes.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


class TestPhaseCAdvisoryAudit(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        # Force-reload to ensure no shared module-level state across tests.
        import importlib
        from _lib import persona_routing as _pr
        importlib.reload(_pr)
        self.persona_routing = _pr

    def _state_dir(self) -> Path:
        return self.home_dir / ".claude" / "projects" / "test" / "state"

    def _marker_path(self) -> Path:
        return self._state_dir() / "phase_c_seen.marker"

    def test_first_call_emits_and_writes_marker(self) -> None:
        self.assertFalse(self._marker_path().is_file())
        self.persona_routing.maybe_emit_phase_c_flipped()
        self.assertTrue(self._marker_path().is_file())
        log = self.read_audit_log()
        self.assertIn('"phase_c_enforcing_flipped"', log)
        # json.dumps default separators include space after colon; tolerate
        # both with-space and no-space formatting.
        self.assertTrue(
            '"migration_phase": "first_session"' in log
            or '"migration_phase":"first_session"' in log,
            f'expected migration_phase=first_session in log; got: {log!r}',
        )

    def test_second_call_is_noop(self) -> None:
        self.persona_routing.maybe_emit_phase_c_flipped()
        # Second call must be a no-op (idempotent).
        self.persona_routing.maybe_emit_phase_c_flipped()
        log = self.read_audit_log()
        count = log.count('"phase_c_enforcing_flipped"')
        self.assertEqual(count, 1, f"expected exactly 1 emit, got {count}")

    def test_marker_corrupted_still_idempotent(self) -> None:
        # If the marker file exists with junk content, we still treat it
        # as "phase C already seen" and skip the emit. This is the
        # crash-mid-flip preservation invariant.
        self._state_dir().mkdir(parents=True, exist_ok=True)
        self._marker_path().write_text("garbage\n", encoding="utf-8")
        self.persona_routing.maybe_emit_phase_c_flipped()
        log = self.read_audit_log()
        self.assertNotIn('"phase_c_enforcing_flipped"', log)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
