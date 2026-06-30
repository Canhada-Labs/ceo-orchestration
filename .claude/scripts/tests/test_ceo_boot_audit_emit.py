"""test_ceo_boot_audit_emit.py — PLAN-065 Phase 2 audit_emit wire tests.

Asserts:
- ceo-boot.py loads `_lib.audit_emit` without crashing pre + post canonical
  ceremony (hasattr() guard).
- The wire helpers `_emit_ceo_boot_emitted_safe` / `_emit_ceo_boot_check_skipped_safe`
  short-circuit safely when the emit functions are absent (pre-ceremony).
- Field allowlist (Sec MF-3) — emit on the canonical side denies forbidden
  fields. This test only runs against the in-memory monkeypatched audit_emit
  to validate caller-side discipline; the canonical side is asserted in
  `.claude/hooks/tests/test_audit_emit.py` once the diff lands.
- Reality-Ledger fixture #4 closure verification — search ceo-boot.py
  source for the deferred-comment marker; assert it's GONE in this
  worktree (proves the wire materialized).

Stdlib only. TestEnvContext for env hygiene.
"""
from __future__ import annotations

import importlib.util
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

# Hygiene: TestEnvContext (S79 lesson)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"


def _load_module():
    """Load ceo-boot.py as importable module (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location("ceo_boot_phase2", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ceo_boot_phase2"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Section 1 — Source-level Reality-Ledger fixture #4 verification
# ---------------------------------------------------------------------------


class TestRealityLedgerClosure(TestEnvContext):
    """Reality-Ledger fixture #4 (declared-but-not-wired) MUST be closed.

    Pre-Phase-2, ceo-boot.py shipped two emit comments (line ~644 cached
    path + ~676 uncached path) saying ``# ceo_boot_emitted emit deferred``.
    Phase 2 wire materializes the call. This test asserts the deferred
    comments are GONE and replaced with actual call sites.
    """

    def test_deferred_comments_absent(self):
        src = SCRIPT.read_text(encoding="utf-8")
        # Original deferred-comment shape
        forbidden = "# ceo_boot_emitted emit deferred to v1.12.0 ceremony."
        self.assertNotIn(
            forbidden, src,
            "Reality-Ledger fixture #4 not closed: deferred comment "
            "still in ceo-boot.py. Phase 2 wire incomplete.",
        )

    def test_check_skipped_deferred_comment_absent(self):
        src = SCRIPT.read_text(encoding="utf-8")
        forbidden = (
            "# ceo_boot_check_skipped emit deferred to v1.12.0 ceremony"
        )
        self.assertNotIn(
            forbidden, src,
            "Reality-Ledger fixture #4 not closed: ceo_boot_check_skipped "
            "deferred comment still present.",
        )

    def test_wire_helpers_present(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("_emit_ceo_boot_emitted_safe", src)
        self.assertIn("_emit_ceo_boot_check_skipped_safe", src)

    def test_wire_section_delimiter_present(self):
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("# === PLAN-065 Phase 2 audit_emit wire ===", src)


# ---------------------------------------------------------------------------
# Section 2 — Pre-canonical-ceremony fail-soft semantics
# ---------------------------------------------------------------------------


class TestPreCeremonyFailSoft(TestEnvContext):
    """Before canonical ceremony, the emit functions are absent.

    The wire helper MUST detect via hasattr() and short-circuit.
    No exception, no audit-log write, no stderr noise unless CEO_BOOT_DEBUG=1.
    """

    def setUp(self):
        super().setUp()
        # Load fresh module instance
        if "ceo_boot_phase2" in sys.modules:
            del sys.modules["ceo_boot_phase2"]
        self.mod = _load_module()

    def test_emit_safe_no_audit_emit_module(self):
        # Force _audit_emit = None branch
        original = self.mod._audit_emit
        self.mod._audit_emit = None
        try:
            # Should not raise
            self.mod._emit_ceo_boot_emitted_safe(
                gate_pass=True, duration_ms=100,
                checks_total=15, checks_failed=0, cache_hit=False,
            )
            self.mod._emit_ceo_boot_check_skipped_safe(
                check_name="x", timeout_ms=500,
            )
        finally:
            self.mod._audit_emit = original

    def test_emit_safe_function_absent_silent(self):
        """When emit_ceo_boot_emitted is missing, helper is silent."""
        # Build a fake audit_emit module that lacks the new symbols
        fake = MagicMock()
        # Configure: the new symbols aren't real attributes
        del fake.emit_ceo_boot_emitted
        del fake.emit_ceo_boot_check_skipped
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.mod._emit_ceo_boot_emitted_safe(
                    gate_pass=True, duration_ms=100,
                    checks_total=15, checks_failed=0, cache_hit=False,
                )
                self.mod._emit_ceo_boot_check_skipped_safe(
                    check_name="x", timeout_ms=500,
                )
            # No stderr noise without CEO_BOOT_DEBUG=1
            self.assertEqual(buf.getvalue(), "")
        finally:
            self.mod._audit_emit = original

    def test_emit_safe_function_absent_debug_logs_to_stderr(self):
        """With CEO_BOOT_DEBUG=1, missing symbol logs once to stderr."""
        fake = MagicMock()
        del fake.emit_ceo_boot_emitted
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        os.environ["CEO_BOOT_DEBUG"] = "1"
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.mod._emit_ceo_boot_emitted_safe(
                    gate_pass=True, duration_ms=100,
                    checks_total=15, checks_failed=0, cache_hit=False,
                )
            self.assertIn("not registered", buf.getvalue())
            self.assertIn("ceremony pending", buf.getvalue())
        finally:
            os.environ.pop("CEO_BOOT_DEBUG", None)
            self.mod._audit_emit = original


# ---------------------------------------------------------------------------
# Section 3 — Post-ceremony emit-wire happy path (monkeypatched audit_emit)
# ---------------------------------------------------------------------------


class TestPostCeremonyEmit(TestEnvContext):
    """Simulate post-ceremony state: emit_ceo_boot_* functions exist.

    Captures the call args + asserts only allowlisted fields were passed.
    Real audit-log write is exercised by `.claude/hooks/tests/test_audit_emit.py`
    once the diff lands.
    """

    def setUp(self):
        super().setUp()
        if "ceo_boot_phase2" in sys.modules:
            del sys.modules["ceo_boot_phase2"]
        self.mod = _load_module()
        # Prepare capture lists
        self.captured_emitted: List[Dict[str, Any]] = []
        self.captured_skipped: List[Dict[str, Any]] = []

        def _fake_emit_emitted(**kwargs):
            self.captured_emitted.append(kwargs)

        def _fake_emit_skipped(**kwargs):
            self.captured_skipped.append(kwargs)

        self._fake = type(
            "FakeAuditEmit", (),
            {
                "emit_ceo_boot_emitted": staticmethod(_fake_emit_emitted),
                "emit_ceo_boot_check_skipped": staticmethod(_fake_emit_skipped),
            },
        )()
        self._original = self.mod._audit_emit
        self.mod._audit_emit = self._fake

    def tearDown(self):
        self.mod._audit_emit = self._original
        super().tearDown()

    def test_emit_emitted_payload_shape(self):
        self.mod._emit_ceo_boot_emitted_safe(
            gate_pass=True, duration_ms=234,
            checks_total=15, checks_failed=2, cache_hit=False,
        )
        self.assertEqual(len(self.captured_emitted), 1)
        ev = self.captured_emitted[0]
        self.assertEqual(ev["gate_pass"], True)
        self.assertEqual(ev["duration_ms"], 234)
        self.assertEqual(ev["checks_total"], 15)
        self.assertEqual(ev["checks_failed"], 2)
        self.assertEqual(ev["cache_hit"], False)
        self.assertIn("session_id", ev)

    def test_emit_emitted_only_passes_allowlisted_fields(self):
        """Caller-side discipline: only Sec MF-3 allowlisted fields."""
        self.mod._emit_ceo_boot_emitted_safe(
            gate_pass=True, duration_ms=100,
            checks_total=15, checks_failed=0, cache_hit=False,
        )
        ev = self.captured_emitted[0]
        # ALLOWED keys (matches _CEO_BOOT_EMITTED_ALLOWLIST minus
        # framework-injected ts/event_schema/hmac which the emit fn adds)
        allowed_caller = {
            "session_id", "project", "gate_pass", "duration_ms",
            "checks_total", "checks_failed", "cache_hit",
        }
        actual = set(ev.keys())
        # Caller passes only allowed keys (subset of full allowlist)
        self.assertTrue(
            actual.issubset(allowed_caller),
            f"Caller leaked non-allowlisted keys: {actual - allowed_caller}",
        )
        # Forbidden fields must NEVER appear in caller payload
        forbidden = {
            "tokens_in", "tokens_out", "tokens_total", "cost_usd",
            "prompt", "skill_content", "env", "paths",
            "recommendation_text", "stack_trace",
        }
        leaked = actual & forbidden
        self.assertEqual(
            leaked, set(),
            f"Caller leaked Sec MF-3 forbidden field(s): {leaked}",
        )

    def test_emit_check_skipped_payload(self):
        self.mod._emit_ceo_boot_check_skipped_safe(
            check_name="plans_executing", timeout_ms=500,
        )
        self.assertEqual(len(self.captured_skipped), 1)
        ev = self.captured_skipped[0]
        self.assertEqual(ev["check_name"], "plans_executing")
        self.assertEqual(ev["timeout_ms"], 500)
        self.assertIn("session_id", ev)

    def test_emit_check_skipped_no_forbidden_fields(self):
        self.mod._emit_ceo_boot_check_skipped_safe(
            check_name="audit_v3_backlog", timeout_ms=500,
        )
        ev = self.captured_skipped[0]
        forbidden = {
            "tokens_in", "tokens_out", "cost_usd", "stack_trace",
            "error_message", "detail", "exception",
        }
        leaked = set(ev.keys()) & forbidden
        self.assertEqual(leaked, set())

    def test_emit_safe_swallows_exception(self):
        """If the canonical emit fn raises, helper MUST NOT propagate."""
        def _boom(**kwargs):
            raise RuntimeError("audit-log filelock contended")

        original_fn = self._fake.emit_ceo_boot_emitted
        self._fake.emit_ceo_boot_emitted = _boom
        try:
            # Must not raise
            self.mod._emit_ceo_boot_emitted_safe(
                gate_pass=True, duration_ms=100,
                checks_total=15, checks_failed=0, cache_hit=False,
            )
        finally:
            self._fake.emit_ceo_boot_emitted = original_fn

    def test_session_id_truncated_to_64(self):
        """Defense-in-depth: hostile env doesn't bloat session_id."""
        os.environ["CLAUDE_SESSION_ID"] = "x" * 200
        try:
            self.mod._emit_ceo_boot_emitted_safe(
                gate_pass=True, duration_ms=100,
                checks_total=15, checks_failed=0, cache_hit=False,
            )
            ev = self.captured_emitted[-1]
            self.assertLessEqual(len(ev["session_id"]), 64)
        finally:
            os.environ.pop("CLAUDE_SESSION_ID", None)

    def test_gate_pass_coerced_bool(self):
        """Caller-side type discipline (no None/string leaks through)."""
        self.mod._emit_ceo_boot_emitted_safe(
            gate_pass="yes",  # type: ignore[arg-type]
            duration_ms=1.5,  # type: ignore[arg-type]
            checks_total=15.0,  # type: ignore[arg-type]
            checks_failed=0,
            cache_hit=1,  # type: ignore[arg-type]
        )
        ev = self.captured_emitted[-1]
        self.assertIs(type(ev["gate_pass"]), bool)
        self.assertEqual(ev["gate_pass"], True)
        self.assertIs(type(ev["duration_ms"]), int)
        self.assertEqual(ev["duration_ms"], 1)
        self.assertIs(type(ev["checks_total"]), int)
        self.assertIs(type(ev["cache_hit"]), bool)


# ---------------------------------------------------------------------------
# Section 4 — Adversarial: try to emit denied field → must fail-CLOSED
# ---------------------------------------------------------------------------


class TestAdversarialDeniedField(TestEnvContext):
    """If a future-CEO drift adds a forbidden kwarg to the wire helper,
    the canonical-side allowlist (in _lib/audit_emit.py) MUST strip it.

    This test exercises the canonical scrub function directly using the
    AST-loaded snapshot of audit_emit IF the new symbols are present;
    otherwise SKIPS so the test is forward-portable across pre + post
    canonical ceremony.
    """

    def setUp(self):
        super().setUp()
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        from _lib import audit_emit as _ae  # noqa: E402
        self._ae = _ae

    def test_scrub_function_present_post_ceremony(self):
        """Existence smoke — runs only post-canonical-ceremony."""
        if not hasattr(self._ae, "_scrub_ceo_boot_event"):
            self.skipTest("Canonical ceremony pending; _scrub_ceo_boot_event not yet registered")
        fn = getattr(self._ae, "_scrub_ceo_boot_event")
        self.assertTrue(callable(fn))

    def test_scrub_strips_forbidden_field(self):
        if not hasattr(self._ae, "_scrub_ceo_boot_event"):
            self.skipTest("Canonical ceremony pending")
        fn = self._ae._scrub_ceo_boot_event
        allowlist = self._ae._CEO_BOOT_EMITTED_ALLOWLIST
        raw = {
            "action": "ceo_boot_emitted",
            "session_id": "s1",
            "gate_pass": True,
            "duration_ms": 100,
            "checks_total": 15,
            "checks_failed": 0,
            "cache_hit": False,
            # Forbidden:
            "tokens_in_total": 50000,
            "cost_usd": 5.50,
            "prompt": "secret-prompt-content",
            "env": {"OPENAI_API_KEY": "sk-..."},
        }
        cleaned, dropped = fn(raw, allowlist)
        self.assertNotIn("tokens_in_total", cleaned)
        self.assertNotIn("cost_usd", cleaned)
        self.assertNotIn("prompt", cleaned)
        self.assertNotIn("env", cleaned)
        self.assertEqual(
            set(dropped),
            {"tokens_in_total", "cost_usd", "prompt", "env"},
        )
        # Allowed fields preserved
        self.assertEqual(cleaned["gate_pass"], True)
        self.assertEqual(cleaned["checks_total"], 15)

    def test_scrub_check_skipped_strips_forbidden(self):
        if not hasattr(self._ae, "_scrub_ceo_boot_event"):
            self.skipTest("Canonical ceremony pending")
        fn = self._ae._scrub_ceo_boot_event
        allowlist = self._ae._CEO_BOOT_CHECK_SKIPPED_ALLOWLIST
        raw = {
            "action": "ceo_boot_check_skipped",
            "session_id": "s1",
            "check_name": "plans_executing",
            "timeout_ms": 500,
            # Forbidden:
            "stack_trace": "Traceback (most recent call)...",
            "error_message": "TimeoutError: deadline exceeded",
            "tokens_in_total": 0,
        }
        cleaned, dropped = fn(raw, allowlist)
        self.assertNotIn("stack_trace", cleaned)
        self.assertNotIn("error_message", cleaned)
        self.assertNotIn("tokens_in_total", cleaned)
        self.assertEqual(
            set(dropped),
            {"stack_trace", "error_message", "tokens_in_total"},
        )

    def test_known_actions_registered_post_ceremony(self):
        """ceo_boot_emitted + ceo_boot_check_skipped present in registry."""
        if "ceo_boot_emitted" not in self._ae._KNOWN_ACTIONS:
            self.skipTest("Canonical ceremony pending; actions not yet in _KNOWN_ACTIONS")
        self.assertIn("ceo_boot_emitted", self._ae._KNOWN_ACTIONS)
        self.assertIn("ceo_boot_check_skipped", self._ae._KNOWN_ACTIONS)

    def test_emit_functions_exist_post_ceremony(self):
        """Typed wrappers callable post-ceremony."""
        if not hasattr(self._ae, "emit_ceo_boot_emitted"):
            self.skipTest("Canonical ceremony pending")
        self.assertTrue(callable(self._ae.emit_ceo_boot_emitted))
        self.assertTrue(callable(self._ae.emit_ceo_boot_check_skipped))

    def test_emit_generic_bypass_blocked_post_ceremony(self):
        """Codex S82 P1 #1 closure — emit_generic("ceo_boot_emitted", forbidden=...)
        MUST scrub via the same allowlist (defense-in-depth boundary).

        Asserts the source pattern is in place. Runtime assertion deferred
        to byte-identity tests that ship with the canonical ceremony PR.
        """
        if "ceo_boot_emitted" not in self._ae._KNOWN_ACTIONS:
            self.skipTest("Canonical ceremony pending")
        # Source-level check: emit_generic must reference _scrub_ceo_boot_event
        # for the new actions (regression guard).
        import inspect
        src = inspect.getsource(self._ae.emit_generic)
        self.assertIn("_scrub_ceo_boot_event", src,
                      "emit_generic must route ceo_boot_* through scrub")
        self.assertIn("ceo_boot_emitted", src)
        self.assertIn("ceo_boot_check_skipped", src)


# ---------------------------------------------------------------------------
# Section 5 — End-to-end: ceo-boot.py CLI doesn't crash post-Phase-2 wire
# ---------------------------------------------------------------------------


class TestEndToEnd(TestEnvContext):
    """Full subprocess invocation of ceo-boot.py with --bench / --json /
    --short / --cached. Pre-canonical-ceremony, the wire helpers are no-op.
    Post-ceremony, audit-log gains 1 ceo_boot_emitted event per invocation
    + N ceo_boot_check_skipped events per timeout."""

    def test_ceo_boot_short_does_not_crash(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--short"],
            capture_output=True, text=True, timeout=15,
            cwd=str(REPO_ROOT),
            env={**os.environ, "CEO_BOOT_DEBUG": "0"},
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("/ceo-boot digest", proc.stdout)

    def test_ceo_boot_json_emits_parseable(self):
        import json
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            capture_output=True, text=True, timeout=15,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(proc.returncode, 0)
        # Subprocess must produce valid JSON despite the wire calls
        # (which are silent fail-open in pre-ceremony state)
        out = json.loads(proc.stdout)
        self.assertIn("gate_pass", out)
        self.assertIn("checks_total", out)


if __name__ == "__main__":
    unittest.main()
