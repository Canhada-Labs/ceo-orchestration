"""PLAN-171 W0 closing control — the BLOCK path of ``check_cost_envelope.py``.

The W0 gate census (``.claude/plans/PLAN-171/w0/lote-3-S347.md``, Achado 2
and Apêndice E) left exactly one row of 52 without a positive control:
``check_cost_envelope.py``. The 59 tests in
``_lib/tests/test_cost_envelope.py`` exercise either the arithmetic LIBRARY
(53) or ``_looks_like_swarm_dispatch`` (6); none of them runs the HOOK all
the way to its ``{"decision": "block", ...}`` line. Deleting that line broke
nothing that survived scrutiny.

This file is that control. It runs the hook the way the harness does — a
SUBPROCESS fed a PreToolUse payload on stdin, one process per dispatch, the
spend state carried between dispatches ONLY by the state file the hook writes
under the isolated ``HOME`` — and asserts the decision the harness would act
on:

* a swarm dispatch that would cross the daily cap is BLOCKED, with the window,
  class and counters named in the reason;
* a blocked dispatch records nothing (the next, smaller one still fits);
* the cap is the class tier's, not a constant;
* the block is NOT unconditional — the same over-cap state lets a non-swarm
  command, a non-Bash tool, and an engaged kill-switch through;
* an infrastructure failure (state directory unusable) fails OPEN, never
  closed — CLAUDE.md §4, fail-open on infrastructure.

Every negative first re-proves that the gate IS armed (the swarm dispatch in
the very same state is blocked), so none of them can pass vacuously.

Red/green provenance (S361, PLAN-171 W0 close). Each behaviour above was
measured RED against a one-anchor mutation in a disposable clone, and GREEN
again after ``git restore`` (the restoration control):

* ``{"decision": "block", ...}`` emission replaced by ``{}``
  (``check_cost_envelope.py:281``)   -> every test in this file goes red;
* Bash + swarm-signature guard removed -> the non-swarm and non-Bash tests;
* that guard AND both kill-switch checks removed -> the two kill-switch tests
  as well;
* ``CEO_SWARM_CLASS`` resolver pinned to ``vibecoder`` -> the class-tier test;
* the library's block path also writes the refused spend -> the no-spend test;
* the ``(None, -1, -1)`` lock-unavailable sentinel treated as a breach -> the
  fail-open test.

NOT covered here, deliberately: the ``cost_envelope_capped`` audit event. As
of this writing ``_safe_emit_capped`` passes ``action=`` twice to
``emit_generic`` (positional + keyword), so the call raises ``TypeError``, is
swallowed by the fail-open ``except`` and the event is never written; the fix
is a canonical-file change. Pinning the broken behaviour here would turn a
defect into a contract, so this file asserts only the decision.

Known residual: the daily counter lives in a UTC-date-keyed state file and the
hook has no clock seam, so a dispatch sequence that straddles 00:00 UTC would
start a fresh daily counter mid-test (about a second of exposure per day; a
re-run clears it).

Env discipline: ``TestEnvContext`` isolation; the child env is built by
``subprocess_env`` (HOME + audit dir inside this test's tmp tree) and every
steering variable the hook reads is popped before being set, so an ambient
``CEO_SWARM_CLASS`` / ``CEO_PLAN_ID`` cannot leak in.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = Path(__file__).resolve().parent.parent / "check_cost_envelope.py"

# A command carrying one of the hook's real swarm-coordinator signatures.
_SWARM_CMD = "python3 .claude/scripts/swarm/coordinator.py --dispatch"

# Every variable the hook (or the library it loads) reads. Popped from the
# child env before the test's own values are applied.
_STEERING_VARS = (
    "CEO_SWARM",
    "CEO_SWARM_CLASS",
    "CEO_SWARM_ESTIMATED_SPAWN_CENTS",
    "CEO_SWARM_ESTIMATE_CENTS",
    "CEO_PLAN_ID",
    "CEO_USER_ID",
)

# vibecoder caps (cents) the assertions below are written against; the
# matrix itself is pinned by test_cost_envelope.py::TestMatrix.
_VIBECODER_DAILY = 500
_CTO_DAILY = 1500


class CostEnvelopeBlockPathTests(TestEnvContext):
    """The hook, as a subprocess, from payload to decision."""

    # -- helpers ----------------------------------------------------------

    def _child_env(
        self,
        *,
        estimate: int,
        plan_id: str,
        swarm: Optional[str] = "1",
        tier: Optional[str] = None,
        home: Optional[Path] = None,
    ) -> Dict[str, str]:
        overrides: Dict[str, str] = {
            "CLAUDE_PROJECT_DIR": str(self.project_dir),
        }
        if home is not None:
            overrides["HOME"] = str(home)
        env = self.subprocess_env(**overrides)
        for var in _STEERING_VARS:
            env.pop(var, None)
        env["CEO_USER_ID"] = "cost-envelope-block-control"
        env["CEO_PLAN_ID"] = plan_id
        env["CEO_SWARM_ESTIMATED_SPAWN_CENTS"] = str(estimate)
        if swarm is not None:
            env["CEO_SWARM"] = swarm
        if tier is not None:
            env["CEO_SWARM_CLASS"] = tier
        return env

    def _dispatch(
        self,
        *,
        estimate: int = 300,
        plan_id: str = "PLAN-A",
        command: str = _SWARM_CMD,
        tool_name: str = "Bash",
        swarm: Optional[str] = "1",
        tier: Optional[str] = None,
        home: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Run the hook once; return the single decision object it printed.

        Asserts the wire contract on the way: exit 0 and exactly one JSON
        object on stdout (a block is a decision, not a crash).
        """
        payload = {
            "tool_name": tool_name,
            "tool_input": {"command": command},
            "session_id": "cost-envelope-block-control",
        }
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            env=self._child_env(
                estimate=estimate, plan_id=plan_id, swarm=swarm, tier=tier,
                home=home,
            ),
        )
        self.assertEqual(
            proc.returncode, 0,
            f"hook must exit 0 on every path; rc={proc.returncode} "
            f"stderr={proc.stderr[:400]!r}",
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(
            len(lines), 1,
            f"hook must print exactly one decision line; got {proc.stdout!r}",
        )
        decision = json.loads(lines[0])
        self.assertIsInstance(decision, dict)
        return decision

    def _assert_allowed(self, decision: Dict[str, Any], msg: str = "") -> None:
        self.assertEqual(decision, {}, msg or "expected a pass-through allow ({})")

    def _assert_blocked_at(
        self,
        decision: Dict[str, Any],
        window: str,
        *,
        tier: str = "vibecoder",
        cap: int,
        current: int,
    ) -> None:
        self.assertEqual(decision.get("decision"), "block", decision)
        reason = decision.get("reason", "")
        self.assertTrue(
            reason.startswith(f"GOVERNANCE: cost_envelope_capped_at_{window}: "),
            reason,
        )
        self.assertIn(f"class={tier}", reason)
        self.assertIn(f"cap_cents={cap}", reason)
        self.assertIn(f"current_cents={current}", reason)

    def _arm_over_the_daily_cap(self) -> None:
        """Bring the vibecoder state to 300/500 cents, then PROVE the gate is
        armed: a further 300-cent swarm dispatch in the same state is blocked.
        The negatives call this first so they cannot pass on a gate that was
        never going to fire."""
        self._assert_allowed(self._dispatch(estimate=300, plan_id="PLAN-A"))
        armed = self._dispatch(estimate=300, plan_id="PLAN-B")
        self._assert_blocked_at(
            armed, "daily", cap=_VIBECODER_DAILY, current=300,
        )

    # -- the block path ---------------------------------------------------

    def test_dispatch_crossing_the_daily_cap_is_blocked(self) -> None:
        first = self._dispatch(estimate=300, plan_id="PLAN-A")
        self._assert_allowed(first, "300 of 500 daily cents fits; must pass")
        second = self._dispatch(estimate=300, plan_id="PLAN-B")
        # 300 already spent + 300 requested = 600 > 500: the daily window
        # trips, and the reason carries the PRE-check counter (300).
        self._assert_blocked_at(
            second, "daily", cap=_VIBECODER_DAILY, current=300,
        )

    def test_blocked_dispatch_records_no_spend(self) -> None:
        self._assert_allowed(self._dispatch(estimate=300, plan_id="PLAN-A"))
        self._assert_blocked_at(
            self._dispatch(estimate=300, plan_id="PLAN-B"),
            "daily", cap=_VIBECODER_DAILY, current=300,
        )
        # If the block had recorded its 300 cents the daily counter would
        # read 600 and this 200-cent dispatch (-> exactly 500) would trip.
        self._assert_allowed(
            self._dispatch(estimate=200, plan_id="PLAN-C"),
            "a blocked dispatch must not consume budget",
        )
        # ... and the edge is real: one more cent is over.
        self._assert_blocked_at(
            self._dispatch(estimate=1, plan_id="PLAN-D"),
            "daily", cap=_VIBECODER_DAILY, current=500,
        )

    def test_cap_is_the_class_tiers_not_a_constant(self) -> None:
        # CTO daily cap is 1500: five 300-cent dispatches fit (distinct plan
        # ids so the per-plan window never fires first), the sixth does not.
        for i in range(5):
            self._assert_allowed(
                self._dispatch(estimate=300, plan_id=f"PLAN-{i}", tier="CTO"),
                f"dispatch {i + 1}/5 of class CTO must fit under 1500",
            )
        sixth = self._dispatch(estimate=300, plan_id="PLAN-5", tier="CTO")
        self._assert_blocked_at(
            sixth, "daily", tier="CTO", cap=_CTO_DAILY, current=1500,
        )

    # -- the block is not unconditional ------------------------------------

    def test_non_swarm_command_passes_over_the_cap(self) -> None:
        self._arm_over_the_daily_cap()
        self._assert_allowed(
            self._dispatch(estimate=300, plan_id="PLAN-B", command="git status"),
            "an ordinary command must never be capped",
        )

    def test_non_bash_tool_passes_over_the_cap(self) -> None:
        self._arm_over_the_daily_cap()
        self._assert_allowed(
            self._dispatch(estimate=300, plan_id="PLAN-B", tool_name="Write"),
            "only the Bash tool is capped",
        )

    def test_kill_switch_unset_passes_over_the_cap(self) -> None:
        self._arm_over_the_daily_cap()
        self._assert_allowed(
            self._dispatch(estimate=300, plan_id="PLAN-B", swarm=None),
            "CEO_SWARM unset is the default-off master kill",
        )

    def test_kill_switch_zero_passes_over_the_cap(self) -> None:
        self._arm_over_the_daily_cap()
        self._assert_allowed(
            self._dispatch(estimate=300, plan_id="PLAN-B", swarm="0"),
            "CEO_SWARM=0 is the master kill",
        )

    # -- fail-open on infrastructure ----------------------------------------

    def test_unusable_state_dir_fails_open_not_closed(self) -> None:
        # A 600-cent request is over the 500-cent daily cap on a fresh state:
        # with a working state dir the hook blocks it (armed contrast).
        self._assert_blocked_at(
            self._dispatch(estimate=600, plan_id="PLAN-A"),
            "daily", cap=_VIBECODER_DAILY, current=0,
        )
        # Same request, but HOME is a regular file: the state directory under
        # it can never be created, so the envelope cannot read or write its
        # counters. That is an infrastructure fault, not a breach — the hook
        # must allow.
        broken_home = self._tmp_root / "home-is-a-file"
        broken_home.write_text("not a directory\n", encoding="utf-8")
        self._assert_allowed(
            self._dispatch(estimate=600, plan_id="PLAN-A", home=broken_home),
            "a lock/IO failure must fail OPEN (CLAUDE.md §4), never block",
        )


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
