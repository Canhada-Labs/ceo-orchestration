"""PLAN-102-FOLLOWUP — gate enforcement tests for LoopRunner.step().

Created by apply-patches.py (Codex R2 iter-1 P0 #3 fold) — covers AC6
(gate path coverage) and AC17 (history invariant on BOTH gate-allow +
gate-block paths). Uses stdlib unittest + unittest.mock.patch; no
pytest fixtures (matches PLAN-107 TestEnvContext discipline).
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

# Bootstrap sys.path so `_lib.testing` resolves regardless of CWD.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks" / "_lib"
if str(_HOOKS_LIB.parent) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB.parent))
if str(_REPO_ROOT / ".claude" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))

from _lib.testing import TestEnvContext  # noqa: E402

from swarm.coordinator import LoopState  # noqa: E402
from swarm.loop_runner import (  # noqa: E402
    DIRECTION_MINIMIZE,
    IterationResult,
    LoopRunner,
)


def _green_iterate(_state: LoopState) -> IterationResult:
    return IterationResult(
        metric=1.0, tokens_delta=10, files_touched=[], kept=True, error=None,
    )


@contextlib.contextmanager
def _install_fake_audit_emit(fake: types.SimpleNamespace):
    """Install `fake` as BOTH sys.modules["_lib.audit_emit"] AND the
    `audit_emit` attribute on the `_lib` package object — loop_runner's
    lazy `from _lib import audit_emit` resolves via the package
    attribute when the package is already imported (_handle_fromlist
    getattr path). The attribute MUST be restored on exit:
    mock.patch.dict only restores sys.modules, and a leaked fake
    attribute makes every later `from _lib import audit_emit` in the
    same process bind the fake — PR #15 residue E3-F2 cross-suite
    pollution that silently swallowed replay/tests audit emits
    (replay-session.py wraps emits in fail-open try/except). Mirrors
    _FakeEmitContext in test_loop_runner_circuit_breaker.py.
    """
    placeholder = None
    lib_mod = sys.modules.get("_lib")
    if lib_mod is None:
        placeholder = types.ModuleType("_lib")
        sys.modules["_lib"] = placeholder
        lib_mod = placeholder
    had_attr = hasattr(lib_mod, "audit_emit")
    saved_attr = getattr(lib_mod, "audit_emit", None)
    lib_mod.audit_emit = fake  # type: ignore[attr-defined]
    try:
        with mock.patch.dict(
            sys.modules, {"_lib.audit_emit": fake}, clear=False,
        ):
            yield fake
    finally:
        if placeholder is not None:
            if sys.modules.get("_lib") is placeholder:
                del sys.modules["_lib"]
        elif had_attr:
            lib_mod.audit_emit = saved_attr  # type: ignore[attr-defined]
        else:
            try:
                delattr(lib_mod, "audit_emit")
            except AttributeError:
                pass


def _install_fake_gate(enabled: bool, reason: str = "") -> mock._patch:
    """Inject a fake `_lib.swarm_enable_gate` module so loop_runner's
    lazy import returns our stub `is_class_enabled` regardless of which
    of the two import paths the helper takes (`.._lib...` or `_lib...`).
    """
    fake_mod = types.ModuleType("_lib.swarm_enable_gate")

    def _stub(_class_tier: str):
        return (enabled, reason)

    fake_mod.is_class_enabled = _stub  # type: ignore[attr-defined]
    return mock.patch.dict(
        sys.modules,
        {"_lib.swarm_enable_gate": fake_mod},
        clear=False,
    )


class _BaseGateTest(TestEnvContext):
    """Shared LoopRunner factory; TestEnvContext gives env-isolation."""

    def setUp(self):
        super().setUp()
        # PLAN-102-FOLLOWUP S145 Fix #2 (Codex triage 019e42fc): Layer-1
        # swarm-on env must be set so the gate is actually exercised after
        # Fix #1 made _gate_step_check early-return when CEO_SWARM != "1".
        # Pre-existing test_loop_runner.py tests do NOT set this, so they
        # bypass the gate and run iterate() exactly as before (regression-
        # safety guarantee for the autonomous-loop opt-in invariant).
        # Set via patch.dict started here and stopped in tearDown BEFORE
        # super().tearDown(), so the base-class env restore (original
        # snapshot) stays the last write and is never re-clobbered.
        self._swarm_env_patch = mock.patch.dict(os.environ, {"CEO_SWARM": "1"})
        self._swarm_env_patch.start()

    def tearDown(self):
        self._swarm_env_patch.stop()
        super().tearDown()

    def _make_runner(self, class_tier: str = "vibecoder") -> LoopRunner:
        return LoopRunner(
            loop_id="L_test",
            goal="g",
            max_iterations=5,
            max_strikes=3,
            budget_tokens=1000,
            direction=DIRECTION_MINIMIZE,
            iterate=_green_iterate,
            class_tier=class_tier,
        )


class TestGateBlockEarlyReturn(_BaseGateTest):
    """AC6 — gate False -> emit called + synthetic IterationResult
    appended to history BEFORE early return."""

    def test_gate_block_sentinel_absent_appends_history_and_returns_killed(self):
        with _install_fake_gate(False, "sentinel_absent"):
            with mock.patch(
                "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
            ) as emit_mock:
                runner = self._make_runner()
                pre = len(runner.history)
                result = runner.step()
                self.assertEqual(len(runner.history), pre + 1)
                self.assertIs(runner.history[-1], result)
                self.assertTrue(math.isnan(result.metric))
                self.assertEqual(result.tokens_delta, 0)
                self.assertEqual(runner.state.status, "killed")
                self.assertIsNotNone(result.error)
                self.assertTrue(result.error.startswith("layer_3_4_"))
                emit_mock.assert_called_once()
                kwargs = emit_mock.call_args.kwargs
                self.assertEqual(kwargs.get("class_tier"), "vibecoder")
                self.assertEqual(kwargs.get("reason_code"), "layer_3_unavailable")
                self.assertEqual(kwargs.get("loop_id"), "L_test")

    def test_gate_block_env_flag_unset_collapses_reason(self):
        with _install_fake_gate(False, "env_flag_unset"):
            with mock.patch(
                "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
            ) as emit_mock:
                runner = self._make_runner()
                runner.step()
                self.assertEqual(
                    emit_mock.call_args.kwargs.get("reason_code"),
                    "layer_4_unset",
                )

    def test_gate_block_unknown_reason_falls_to_unknown(self):
        with _install_fake_gate(False, "exotic_unmapped_reason"):
            with mock.patch(
                "swarm.loop_runner._emit_swarm_layer_3_4_blocked"
            ) as emit_mock:
                runner = self._make_runner()
                runner.step()
                self.assertEqual(
                    emit_mock.call_args.kwargs.get("reason_code"),
                    "unknown",
                )


class TestGateAllowHappyPath(_BaseGateTest):
    """AC7 + AC17 happy-path — gate True -> iterate callable invoked
    and history advances normally."""

    def test_gate_allow_invokes_iterate_and_advances_history(self):
        captured = []

        def _spy_iterate(state: LoopState) -> IterationResult:
            captured.append(state.iteration)
            return IterationResult(
                metric=2.5, tokens_delta=20, files_touched=["f.py"],
                kept=True, error=None,
            )

        with _install_fake_gate(True, ""):
            runner = LoopRunner(
                loop_id="L_test",
                goal="g",
                max_iterations=5,
                max_strikes=3,
                budget_tokens=1000,
                direction=DIRECTION_MINIMIZE,
                iterate=_spy_iterate,
                class_tier="vibecoder",
            )
            pre = len(runner.history)
            result = runner.step()
            self.assertEqual(len(captured), 1, "iterate spy NOT called once")
            self.assertEqual(len(runner.history), pre + 1)
            self.assertEqual(result.metric, 2.5)
            self.assertIsNone(result.error)
            self.assertEqual(runner.state.status, "running")


class TestGateUnavailableFailsOpen(_BaseGateTest):
    """AC9 partial — when the gate primitive is unimportable
    (`_lib.swarm_enable_gate` missing), `_gate_step_check` fails open
    (returns None) and step() proceeds normally."""

    def test_missing_gate_module_fails_open_to_allow(self):
        # PLAN-102-FOLLOWUP S145 Fix #4 (Codex triage 019e42fc): just
        # popping from sys.modules is INSUFFICIENT — the lazy import in
        # _gate_step_check would re-import from .claude/hooks/_lib/ which
        # is still on sys.path. To truly test the fail-open import path,
        # we must: (a) remove .claude/hooks dir entries from sys.path
        # AND (b) purge all `_lib*` modules from sys.modules so the next
        # import actually raises ImportError → _gate_step_check returns
        # None (fail-open) → step() proceeds and iterate() runs.
        saved_path = list(sys.path)
        saved_modules = {
            k: v for k, v in list(sys.modules.items())
            if k == "_lib" or k.startswith("_lib.")
        }
        try:
            # Strip every sys.path entry that exposes ".claude/hooks" or
            # ".claude/hooks/_lib" (apply-patches injects ".claude/hooks"
            # earlier — its parent is on the path).
            sys.path[:] = [
                p for p in sys.path
                if "/.claude/hooks" not in p
                and not p.endswith("/.claude")  # parent that exposes hooks/
            ]
            for k in list(sys.modules):
                if k == "_lib" or k.startswith("_lib."):
                    sys.modules.pop(k, None)
            runner = self._make_runner()
            pre = len(runner.history)
            result = runner.step()
            # Gate primitive unimportable -> fail-open -> iterate ran.
            self.assertEqual(len(runner.history), pre + 1)
            self.assertEqual(result.metric, 1.0)
            self.assertIsNone(result.error)
        finally:
            sys.path[:] = saved_path
            for k, v in saved_modules.items():
                sys.modules[k] = v


class TestLLM06ProducerBoundary(TestEnvContext):
    """AC19a — `_emit_swarm_layer_3_4_blocked` drops adversarial
    loop_id values (fail-open) and forwards valid ones."""

    def test_adversarial_loop_ids_drop_silently(self):
        from swarm import loop_runner as lr
        adversarial = [
            "../etc/passwd",
            "a; rm -rf /",
            "x" * 65,
            "",
            "x y",
            "x\ny",
            "../../foo",
            '"; cat /etc/shadow; #',
        ]
        captured = []
        fake = types.SimpleNamespace(
            emit_generic=lambda *a, **kw: captured.append((a, kw)),
        )
        with _install_fake_audit_emit(fake):
            for bad in adversarial:
                lr._emit_swarm_layer_3_4_blocked(
                    class_tier="vibecoder",
                    reason_code="layer_3_unavailable",
                    loop_id=bad,
                )
            self.assertEqual(
                captured, [],
                f"adversarial loop_ids should drop (got emits: {captured})",
            )

    def test_valid_loop_id_passes_through(self):
        from swarm import loop_runner as lr
        captured = []
        fake = types.SimpleNamespace(
            emit_generic=lambda *a, **kw: captured.append((a, kw)),
        )
        with _install_fake_audit_emit(fake):
            lr._emit_swarm_layer_3_4_blocked(
                class_tier="vibecoder",
                reason_code="kill_switch",
                loop_id="loop_abc-123_OK",
            )
        self.assertEqual(len(captured), 1)


if __name__ == "__main__":
    unittest.main()
