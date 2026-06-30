"""PLAN-090 Wave A.5 — CEO_GODMODE_ENFORCING=0 kill-switch tests.

R1 security-engineer P0 fold: truthiness footgun discipline. Kill-switch
must fire ONLY on EXACT MATCH `=0`. Any other value (including =false,
=no, ='', =FALSE, =, unset, =1) keeps ENFORCING active.

R1 TDE P0 fold: kill_switch_invoked audit event registered with
FPR-budget tracking (rate-cap 1 per session, summary at session end).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


_TRUTHINESS_MATRIX = (
    # (env_value, kill_switch_armed)
    ("0", True),       # EXACT MATCH only
    ("false", False),  # ignored — ENFORCING stays
    ("no", False),     # ignored
    ("FALSE", False),  # case-sensitive — ignored
    ("", False),       # empty string — ignored
    ("1", False),      # ignored (truthy by Python but not =0)
    ("yes", False),    # ignored
    (" 0", False),     # whitespace prefix — ignored
    ("0 ", False),     # whitespace suffix — ignored
    ("00", False),     # not =0 — ignored
)


class TestKillSwitchGodmodeEnforcing(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        # Force-reload to reset module-level _killswitch_emitted_this_session
        import importlib
        from _lib import persona_routing as _pr
        importlib.reload(_pr)
        self.persona_routing = _pr

    def test_truthiness_matrix(self) -> None:
        for value, armed in _TRUTHINESS_MATRIX:
            with self.subTest(value=repr(value), armed=armed):
                os.environ["CEO_GODMODE_ENFORCING"] = value
                try:
                    mode = self.persona_routing.get_mode("vibecoder", "AUTO-01")
                    if armed:
                        self.assertEqual(
                            mode, "advisory",
                            f"kill-switch should be ARMED for value {value!r}",
                        )
                    else:
                        self.assertEqual(
                            mode, "enforcing",
                            f"kill-switch should be INACTIVE for value {value!r}",
                        )
                finally:
                    os.environ.pop("CEO_GODMODE_ENFORCING", None)

    def test_unset_env_is_enforcing(self) -> None:
        os.environ.pop("CEO_GODMODE_ENFORCING", None)
        mode = self.persona_routing.get_mode("vibecoder", "AUTO-05")
        self.assertEqual(mode, "enforcing")

    def test_killswitch_armed_emits_audit_event(self) -> None:
        from _lib import audit_emit
        os.environ["CEO_GODMODE_ENFORCING"] = "0"
        try:
            # The kill-switch consult fires emit_kill_switch_invoked.
            self.persona_routing.is_killswitch_active()
            log = self.read_audit_log()
            self.assertIn('"kill_switch_invoked"', log)
        finally:
            os.environ.pop("CEO_GODMODE_ENFORCING", None)

    def test_killswitch_emits_once_per_session(self) -> None:
        # FPR-budget tracking: rate-cap to 1 emit per session.
        os.environ["CEO_GODMODE_ENFORCING"] = "0"
        try:
            for _ in range(5):
                self.persona_routing.is_killswitch_active()
            log = self.read_audit_log()
            count = log.count('"kill_switch_invoked"')
            self.assertEqual(
                count, 1,
                f"expected exactly 1 kill_switch_invoked emit (rate-cap), got {count}",
            )
        finally:
            os.environ.pop("CEO_GODMODE_ENFORCING", None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
