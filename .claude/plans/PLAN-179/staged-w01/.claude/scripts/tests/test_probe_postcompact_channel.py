"""PLAN-179 W0 US1 (amendment 8.6) — POSITIVE CONTROL for the channel probe.

A probe that cannot fail is a dead probe ([[feedback-probe-needs-neutral-
user-layer]], [[feedback-livefire-catches-what-fixtures-miss]]). These tests
exist to prove the three things that make the W0 verdict falsifiable:

1. text WITHOUT the canaries yields ``(False, False)`` AND a non-zero CLI
   exit — the probe reports NEITHER, it does not rubber-stamp;
2. exactly ONE canary is a distinct, named outcome (exit 3), never rounded
   up to success nor down to failure — the whole point of two canaries in
   one paid compaction;
3. BOTH canaries is the only exit 0;
4. the operator/local-only refusal has teeth (``$CI`` => ``SystemExit`` 2).

Env hygiene: ``TestEnvContext`` isolates ``$HOME`` / ``$CLAUDE_PROJECT_DIR``
(so every run writes its state into a temp tree, never the real
``.claude/state/``) and ``mock.patch.dict`` handles the non-``CEO_`` vars
``CI`` / ``GITHUB_ACTIONS``. Nothing here touches the live audit log or
performs a compaction — this file costs nothing to run.

The suite itself runs in CI, where ``$CI``/``$GITHUB_ACTIONS`` ARE set; every
non-refusal test therefore clears them explicitly through ``_operator_env()``.
That clearing is deliberate and local to the test process: the probe's guard
stays unconditional (no override env var by design).
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


def _repo_root() -> Path:
    """Nearest ``.git`` ancestor — NOT a fixed number of ``.parent`` hops.

    This file ships STAGED (``PLAN-179/staged-w01/.claude/scripts/tests/``)
    and will later land at ``.claude/scripts/tests/``; the hop count differs
    between the two, so anchor on ``.git`` like the repo's other root
    resolvers do (``check-hook-stdout-schema.py:_find_repo_root``).
    """
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / ".git").exists():
            return cand
    return here.parents[-1]


REPO_ROOT = _repo_root()
# Resolve the probe relative to THIS file, not to the landed path — the
# landed copy may not exist yet. Both layouts put it at ../probes/.
PROBE = Path(__file__).resolve().parent.parent / "probes" / \
    "probe_postcompact_channel.py"

for _p in (
    str(REPO_ROOT / ".claude" / "hooks"),
    str(REPO_ROOT / ".claude" / "scripts"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_probe():
    spec = importlib.util.spec_from_file_location(
        "probe_postcompact_channel", PROBE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


probe = _load_probe()


def _operator_env(**extra):
    """Env with the CI markers CLEARED (operator context), plus overrides."""
    env = {"CI": "", "GITHUB_ACTIONS": ""}
    env.update(extra)
    return mock.patch.dict("os.environ", env, clear=False)


class ProbeChannelTestBase(TestEnvContext):
    """Arms one run inside the isolated project dir and keeps its tokens."""

    def setUp(self):
        super().setUp()
        with _operator_env():
            self.state_path, self.run = probe.arm(self.project_dir)
        self.canary_post = self.run["canary_post"]
        self.canary_ss = self.run["canary_ss"]
        self.obs = self.project_dir / "observation.txt"

    def _verify_cli(self, text: str) -> int:
        """Run the CLI --verify path over ``text``; return its exit code."""
        self.obs.write_text(text, encoding="utf-8")
        with _operator_env(), self.assertRaises(SystemExit) as ctx:
            probe.main(["--verify", str(self.obs), "--state",
                        str(self.state_path)])
        code = ctx.exception.code
        return 0 if code is None else int(code)


class TestVerifyDetector(ProbeChannelTestBase):
    """The three outcomes of ONE paid compaction (amendment 8.6)."""

    def test_verify_fails_without_canary(self):
        """NEITHER: detector False on both AND CLI exit != 0.

        This is THE positive control — if this ever passes with exit 0 the
        probe has stopped being able to report a negative, and the W0
        verdict it produces is worthless.
        """
        text = (
            "Compaction summary: we were working on PLAN-179 and the model "
            "reported no CANARY- lines at all in its context."
        )
        found_post, found_ss = probe.detect(text, self.run)
        self.assertFalse(found_post)
        self.assertFalse(found_ss)
        verdict, code = probe.verdict_for(found_post, found_ss)
        self.assertEqual(verdict, probe.VERDICT_NEITHER)
        self.assertEqual(code, probe.EXIT_NEITHER)

        cli_code = self._verify_cli(text)
        self.assertNotEqual(cli_code, 0)
        self.assertEqual(cli_code, probe.EXIT_NEITHER)

    def test_verify_partial_is_exit_3(self):
        """Exactly one canary is its OWN outcome, and names which channel."""
        # PostCompact delivered, SessionStart(compact) did not.
        post_only = "model echoed: %s" % self.canary_post
        self.assertEqual(probe.detect(post_only, self.run), (True, False))
        self.assertEqual(
            probe.verdict_for(True, False),
            (probe.VERDICT_POST_ONLY, probe.EXIT_PARTIAL),
        )
        self.assertEqual(self._verify_cli(post_only), probe.EXIT_PARTIAL)

        # …and the mirror case, so a hardcoded "post" answer cannot pass.
        ss_only = "model echoed: %s" % self.canary_ss
        self.assertEqual(probe.detect(ss_only, self.run), (False, True))
        self.assertEqual(
            probe.verdict_for(False, True),
            (probe.VERDICT_SS_ONLY, probe.EXIT_PARTIAL),
        )
        self.assertEqual(self._verify_cli(ss_only), probe.EXIT_PARTIAL)

    def test_verify_both_is_exit_0(self):
        both = "I can see %s and also %s in my context." % (
            self.canary_post, self.canary_ss
        )
        self.assertEqual(probe.detect(both, self.run), (True, True))
        self.assertEqual(self._verify_cli(both), probe.EXIT_OK)

    def test_verdict_is_written_down(self):
        """The verdict must be recorded, naming the delivering channel."""
        self._verify_cli("saw %s only" % self.canary_ss)
        run = probe.load_run(self.state_path)
        verdicts = [r for r in run["records"] if r.get("kind") == "verdict"]
        self.assertEqual(len(verdicts), 1)
        self.assertEqual(verdicts[0]["verdict"], probe.VERDICT_SS_ONLY)
        self.assertFalse(verdicts[0]["found_postcompact"])
        self.assertTrue(verdicts[0]["found_sessionstart_compact"])


class TestArmAccounting(ProbeChannelTestBase):
    """Idempotency requirement of 8.6 — arms are countable and subtractable."""

    def test_arm_appends_never_overwrites(self):
        with _operator_env():
            second_path, second_run = probe.arm(self.project_dir)
        self.assertNotEqual(second_path, self.state_path)
        self.assertNotEqual(second_run["canary_post"], self.canary_post)
        # The first run file survived the second arm.
        self.assertTrue(self.state_path.is_file())
        ledger = (self.project_dir / probe.STATE_REL / probe.LEDGER_NAME)
        arms = [ln for ln in ledger.read_text(encoding="utf-8").splitlines()
                if '"kind": "arm"' in ln]
        self.assertEqual(len(arms), 2)

    def test_state_lives_under_project_dir_not_real_repo(self):
        self.assertTrue(
            str(self.state_path).startswith(str(self.project_dir)),
            "probe state escaped the isolated project dir",
        )


class TestHookIsNoOpUnlessArmed(ProbeChannelTestBase):
    """The probe must not change production behaviour by existing."""

    def test_unarmed_hook_emits_nothing(self):
        with _operator_env(), mock.patch.dict("os.environ", {}, clear=False):
            os.environ.pop(probe.CANARY_ENV, None)
            self.assertEqual(probe.hook_payload(probe.CHANNEL_POST), {})
            self.assertEqual(probe.canary_text(probe.CHANNEL_SS), "")

    def test_armed_hook_injects_only_its_own_canary(self):
        payload = probe.hook_payload(probe.CHANNEL_POST, str(self.state_path))
        injected = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn(self.canary_post, injected)
        self.assertNotIn(self.canary_ss, injected)
        self.assertEqual(
            payload["hookSpecificOutput"]["hookEventName"], "PostCompact"
        )

    def test_unreadable_state_is_a_no_op_not_a_crash(self):
        missing = self.project_dir / "does-not-exist.json"
        self.assertEqual(probe.canary_text(probe.CHANNEL_POST, str(missing)), "")


class TestOperatorOnlyRefusal(TestEnvContext):
    """Amendment 8.6 — OPERATOR/LOCAL ONLY, never CI."""

    def test_probe_refuses_in_ci(self):
        with mock.patch.dict("os.environ", {"CI": "true"}, clear=False):
            with self.assertRaises(SystemExit) as ctx:
                probe.main(["--status"])
            self.assertEqual(ctx.exception.code, probe.EXIT_REFUSED)

    def test_probe_refuses_under_github_actions(self):
        env = {"CI": "", "GITHUB_ACTIONS": "true"}
        with mock.patch.dict("os.environ", env, clear=False):
            with self.assertRaises(SystemExit) as ctx:
                probe.main(["--arm"])
            self.assertEqual(ctx.exception.code, probe.EXIT_REFUSED)

    def test_hook_mode_no_ops_in_ci_instead_of_erroring(self):
        """A wired hook must never exit non-zero (harness reads it as error)."""
        with mock.patch.dict("os.environ", {"CI": "true"}, clear=False):
            with self.assertRaises(SystemExit) as ctx:
                probe.main(["--hook", probe.CHANNEL_POST])
            self.assertEqual(ctx.exception.code, probe.EXIT_OK)

    def test_ci_reason_names_the_variable(self):
        with mock.patch.dict("os.environ", {"CI": "", "GITHUB_ACTIONS": ""},
                             clear=False):
            self.assertIsNone(probe.ci_reason())
        with mock.patch.dict("os.environ", {"CI": "0", "GITHUB_ACTIONS": ""},
                             clear=False):
            self.assertIsNone(probe.ci_reason())  # CI=0 is not a CI context
        with mock.patch.dict("os.environ", {"CI": "true"}, clear=False):
            self.assertEqual(probe.ci_reason(), "CI")


class TestSelfObservationGuard(ProbeChannelTestBase):
    """Verifying against the state file itself would always say 'both'."""

    def test_verify_refuses_the_state_file_as_observation(self):
        with _operator_env(), self.assertRaises(SystemExit) as ctx:
            probe.main(["--verify", str(self.state_path), "--state",
                        str(self.state_path)])
        self.assertEqual(ctx.exception.code, probe.EXIT_REFUSED)


class TestSelfTestMode(TestEnvContext):
    def test_self_test_passes_and_is_hermetic(self):
        with _operator_env():
            self.assertEqual(probe.cmd_self_test(), probe.EXIT_OK)
        state = self.project_dir / probe.STATE_REL
        self.assertFalse(
            state.exists(), "--self-test wrote into the project state dir"
        )


if __name__ == "__main__":
    unittest.main()
