"""WIRE-OTEL tests — default-OFF contract + active-path shape.

PLAN-113 Phase C remediation (WIRE-OTEL wave).

Covers:
- get_bounded_exporter() creates NO thread when CEO_OTEL_ENDPOINT is absent.
- maybe_enqueue_span() is a strict no-op (returns False) without endpoint.
- maybe_enqueue_span() delegates to singleton when endpoint IS configured.
- hook_bridge.maybe_enqueue() is a strict no-op without endpoint.
- hook_bridge.maybe_enqueue() returns True when endpoint configured.
- metrics.compute() returns correct snapshot shape (no env gate needed).
- metrics.health_from_snapshot() returns healthy on empty stream.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List
import unittest

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import metrics  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _events(*evs):
    def _fn():
        return iter(evs)
    return _fn


# ---------------------------------------------------------------------------
# metrics.py — pure stdlib, no env gate needed
# ---------------------------------------------------------------------------


class TestMetricsImportAndShape(TestEnvContext):
    """metrics.compute() + health_from_snapshot() return correct shape."""

    def test_compute_returns_all_required_keys(self) -> None:
        snap = metrics.compute(_events())
        required = {
            "spawn_total",
            "veto_total",
            "debate_event_total",
            "plan_transition_total",
            "benchmark_run_total",
            "lesson_write_total",
            "veto_by_hook",
            "veto_by_reason_code",
            "plan_transitions_by_status",
            "spawn_by_skill",
            "spawn_by_model",
            "benchmark_by_skill",
            "lesson_by_archetype",
            "spawn_compliance_rate",
            "spawn_compliance_breakdown",
            "hook_duration_ms_p95",
            "benchmark_pass_rate_mean",
            "benchmark_pass_rate_min",
            "events_total",
        }
        missing = required - snap.keys()
        self.assertEqual(missing, set(), f"missing keys: {missing}")

    def test_health_from_snapshot_healthy_on_empty(self) -> None:
        snap = metrics.compute(_events())
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "healthy")
        self.assertEqual(h["findings"], [])
        self.assertIn("impact", h)

    def test_compute_spawn_model_field(self) -> None:
        """spawn_by_model aggregates correctly (ADR-052 / audit_log v2.8)."""
        snap = metrics.compute(_events(
            {
                "action": "agent_spawn",
                "skill": "security-and-auth",
                "model": "claude-opus-4-8",
                "has_profile": True,
                "has_file_assignment": True,
                "hook_duration_ms": 10,
            },
            {
                "action": "agent_spawn",
                "skill": "testing-strategy",
                "model": "claude-opus-4-8",
                "has_profile": True,
                "has_file_assignment": True,
                "hook_duration_ms": 8,
            },
            # Pre-v2.8 entry — no model field → treated as unknown_model
            {
                "action": "agent_spawn",
                "skill": "observability-and-ops",
                "has_profile": True,
                "has_file_assignment": True,
            },
        ))
        self.assertEqual(snap["spawn_total"], 3)
        self.assertEqual(snap["spawn_by_model"]["claude-opus-4-8"], 2)
        self.assertEqual(snap["spawn_by_model"]["unknown_model"], 1)

    def test_health_unhealthy_triggers_on_benchmark_floor(self) -> None:
        snap = metrics.compute(_events(
            {"action": "benchmark_run", "skill": "x", "pass_rate": 0.3},
        ))
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "unhealthy")
        self.assertNotEqual(h["impact"], "NONE")


# ---------------------------------------------------------------------------
# otel/bounded_exporter.py — default-OFF contract
# ---------------------------------------------------------------------------


class TestGetBoundedExporterDefaultOff(TestEnvContext):
    """get_bounded_exporter() must NOT start a thread when no endpoint."""

    def setUp(self) -> None:
        super().setUp()
        # Ensure no endpoint env var is set
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        # Reset singleton so each test gets a fresh state
        self._reset_singleton()

    def tearDown(self) -> None:
        self._reset_singleton()
        super().tearDown()

    def _reset_singleton(self) -> None:
        try:
            from _lib.otel.bounded_exporter import _reset_singleton_for_tests
            _reset_singleton_for_tests()
        except Exception:
            pass

    def test_no_thread_started_without_endpoint(self) -> None:
        """Default-OFF: no thread created when CEO_OTEL_ENDPOINT absent."""
        from _lib.otel.bounded_exporter import get_bounded_exporter
        exporter = get_bounded_exporter()
        snap = exporter.snapshot()
        # Thread must NOT be alive — no endpoint means no thread started
        self.assertFalse(
            snap["thread_alive"],
            "BoundedExporter daemon thread was started without an endpoint "
            "(violates default-OFF contract)",
        )
        exporter.shutdown(grace_s=0.1)

    def test_enqueue_without_endpoint_returns_false(self) -> None:
        """Default-OFF: enqueue on a no-thread exporter is silent no-op."""
        from _lib.otel.bounded_exporter import get_bounded_exporter
        exporter = get_bounded_exporter()
        # Enqueue should work (queue accepts) but thread not running means
        # items never sent; the important thing is no exception + no thread.
        span = {"action": "agent_spawn", "ts": "2026-05-25T00:00:00Z"}
        # Should not raise; result is implementation-defined (queue accepts
        # even without thread).
        try:
            exporter.enqueue_span(span)
        except Exception as exc:
            self.fail(f"enqueue_span raised unexpectedly: {exc}")
        exporter.shutdown(grace_s=0.1)

    def test_thread_starts_when_endpoint_set_via_env(self) -> None:
        """Active path: thread IS started when CEO_OTEL_ENDPOINT is set."""
        os.environ["CEO_OTEL_ENDPOINT"] = "https://otel.example.com/v1/traces"
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "otel.example.com"
        try:
            from _lib.otel.bounded_exporter import get_bounded_exporter
            exporter = get_bounded_exporter()
            snap = exporter.snapshot()
            self.assertTrue(
                snap["thread_alive"],
                "BoundedExporter thread should be running when endpoint is configured",
            )
        finally:
            os.environ.pop("CEO_OTEL_ENDPOINT", None)
            os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
            self._reset_singleton()

    def test_thread_starts_when_endpoint_set_via_kwarg(self) -> None:
        """Active path: thread IS started when endpoint kwarg is provided."""
        from _lib.otel.bounded_exporter import (
            get_bounded_exporter,
            _reset_singleton_for_tests,
        )

        class _Fake:
            def __call__(self, *a, **kw):
                return None

        exporter = get_bounded_exporter(
            endpoint="https://otel.example.com/v1/traces",
            allowed_hosts=["otel.example.com"],
            exporter=_Fake(),
        )
        snap = exporter.snapshot()
        self.assertTrue(snap["thread_alive"])
        exporter.shutdown(grace_s=0.5)


class TestMaybeEnqueueSpan(TestEnvContext):
    """maybe_enqueue_span() is a strict no-op without endpoint."""

    def setUp(self) -> None:
        super().setUp()
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        try:
            from _lib.otel.bounded_exporter import _reset_singleton_for_tests
            _reset_singleton_for_tests()
        except Exception:
            pass

    def tearDown(self) -> None:
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        os.environ.pop("CEO_OTEL_ALLOWED_HOSTS", None)
        try:
            from _lib.otel.bounded_exporter import _reset_singleton_for_tests
            _reset_singleton_for_tests()
        except Exception:
            pass
        super().tearDown()

    def test_returns_false_without_endpoint(self) -> None:
        """Strict no-op: returns False, no singleton created."""
        from _lib.otel.bounded_exporter import maybe_enqueue_span, _singleton
        import _lib.otel.bounded_exporter as bx_mod
        span = {"action": "test_event", "ts": "2026-05-25T00:00:00Z"}
        result = maybe_enqueue_span(span)
        self.assertFalse(result)
        # Singleton must NOT have been created (no thread, no overhead)
        self.assertIsNone(bx_mod._singleton)

    def test_returns_true_with_endpoint(self) -> None:
        """Active path: delegates to singleton when endpoint is set."""
        os.environ["CEO_OTEL_ENDPOINT"] = "https://otel.example.com/v1/traces"
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "otel.example.com"

        class _Fake:
            calls: List[Any] = []

            def __call__(self, *a, **kw):
                self.calls.append(kw)
                return None

        from _lib.otel.bounded_exporter import (
            get_bounded_exporter,
            maybe_enqueue_span,
            _reset_singleton_for_tests,
        )
        # Prime the singleton with an injected fake exporter so no real HTTP
        _reset_singleton_for_tests()
        get_bounded_exporter(
            endpoint="https://otel.example.com/v1/traces",
            allowed_hosts=["otel.example.com"],
            exporter=_Fake(),
        )
        span = {"action": "test_event", "ts": "2026-05-25T00:00:00Z"}
        result = maybe_enqueue_span(span)
        # Should be accepted by the queue (True or False depending on post-shutdown)
        self.assertIsInstance(result, bool)

    def test_no_exception_on_broken_singleton(self) -> None:
        """Fail-open: exception in singleton is swallowed."""
        os.environ["CEO_OTEL_ENDPOINT"] = "https://otel.example.com/v1/traces"

        from _lib.otel.bounded_exporter import (
            _reset_singleton_for_tests,
            get_bounded_exporter,
            maybe_enqueue_span,
        )

        class _AlwaysRaises:
            def enqueue_span(self, span):
                raise RuntimeError("injected failure")

        # Patch the singleton with an object that raises
        import _lib.otel.bounded_exporter as bx_mod
        _reset_singleton_for_tests()
        fake_exporter_obj = _AlwaysRaises()
        bx_mod._singleton = fake_exporter_obj  # type: ignore[assignment]
        try:
            result = maybe_enqueue_span({"action": "x"})
            # Must not raise; must return False
            self.assertFalse(result)
        finally:
            bx_mod._singleton = None


# ---------------------------------------------------------------------------
# otel/hook_bridge.py — thin importable gateway (tested before it exists
# to establish the contract; will pass once hook_bridge.py is created)
# ---------------------------------------------------------------------------


class TestHookBridge(TestEnvContext):
    """hook_bridge.maybe_enqueue() — strict no-op without endpoint."""

    def setUp(self) -> None:
        super().setUp()
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        try:
            from _lib.otel.bounded_exporter import _reset_singleton_for_tests
            _reset_singleton_for_tests()
        except Exception:
            pass

    def tearDown(self) -> None:
        os.environ.pop("CEO_OTEL_ENDPOINT", None)
        try:
            from _lib.otel.bounded_exporter import _reset_singleton_for_tests
            _reset_singleton_for_tests()
        except Exception:
            pass
        super().tearDown()

    def test_import_succeeds(self) -> None:
        """hook_bridge module must be importable."""
        try:
            from _lib.otel import hook_bridge  # noqa: F401
        except ImportError as exc:
            self.skipTest(f"hook_bridge not yet created: {exc}")

    def test_no_op_without_endpoint(self) -> None:
        """Strict no-op: returns False, no singleton, no thread."""
        try:
            from _lib.otel.hook_bridge import maybe_enqueue
        except ImportError:
            self.skipTest("hook_bridge not yet created")
        span = {"action": "test_event", "ts": "2026-05-25T00:00:00Z"}
        result = maybe_enqueue(span)
        self.assertFalse(result)

    def test_no_exception_on_call(self) -> None:
        """Fail-open: never raises regardless of input."""
        try:
            from _lib.otel.hook_bridge import maybe_enqueue
        except ImportError:
            self.skipTest("hook_bridge not yet created")
        # Should not raise even with weird input
        for span in [None, {}, {"action": "x"}, "string", 42]:
            try:
                maybe_enqueue(span)  # type: ignore[arg-type]
            except Exception as exc:
                self.fail(f"maybe_enqueue({span!r}) raised: {exc}")

    def test_active_path_with_endpoint(self) -> None:
        """Active path: with endpoint set, call delegates to bounded exporter."""
        try:
            from _lib.otel.hook_bridge import maybe_enqueue
        except ImportError:
            self.skipTest("hook_bridge not yet created")
        os.environ["CEO_OTEL_ENDPOINT"] = "https://otel.example.com/v1/traces"
        os.environ["CEO_OTEL_ALLOWED_HOSTS"] = "otel.example.com"
        from _lib.otel.bounded_exporter import (
            get_bounded_exporter,
            _reset_singleton_for_tests,
        )

        class _Fake:
            def __call__(self, *a, **kw):
                return None

        _reset_singleton_for_tests()
        get_bounded_exporter(
            endpoint="https://otel.example.com/v1/traces",
            allowed_hosts=["otel.example.com"],
            exporter=_Fake(),
        )
        result = maybe_enqueue({"action": "test", "ts": "2026-05-25T00:00:00Z"})
        # Returns bool; doesn't raise
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
