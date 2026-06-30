"""PLAN-102 Wave B — tests for execution_context HMAC tamper-evidence.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/tests/test_execution_context.py`.

Covers PLAN-102 AC B.2b: HMAC sign/validate roundtrip, replay rejection,
stale-nonce rejection, tampered-payload rejection, coordinator key
lifecycle, env-flag kill-switch, canonical serialization invariants.

Stdlib only. pytest-compatible (unittest.TestCase subclass).
Python >= 3.9.
"""

from __future__ import annotations

import hmac
import importlib
import importlib.util
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
# Path resolution works in both contexts:
#   Staged   .claude/plans/PLAN-102/wave-b-test-execution-context.py — parents[1]=plans → repo at parents[2]
#   Canonical .claude/hooks/_lib/tests/test_execution_context.py     — parents[1]=_lib → hooks at parents[2]
if _HERE.name == "PLAN-102":
    _HOOKS = _HERE.parents[1] / ".claude" / "hooks"
elif _HERE.name == "tests":
    _HOOKS = _HERE.parents[1]
else:
    _HOOKS = _HERE.parents[2] / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

_lib_testing = importlib.import_module("_lib.testing")
TestEnvContext = _lib_testing.TestEnvContext

# Import target: canonical _lib path post-ceremony; staged path pre-ceremony.
try:
    _ec_mod = importlib.import_module("_lib.execution_context")
except ImportError:
    # Pre-ceremony: load directly from staged file in plan dir
    _staged = Path(__file__).resolve().parent / "wave-b-execution-context.py"
    _spec = importlib.util.spec_from_file_location("_staged_execution_context", _staged)
    _ec_mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_ec_mod)
ExecutionContext = _ec_mod.ExecutionContext


def _fresh_module() -> None:
    """Reset class-level state between tests (no shared coordinator key)."""
    ExecutionContext._coordinator_key = None
    ExecutionContext._nonce_counter = 0
    ExecutionContext._seen_nonces = {}


class TestExecutionContext(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        _fresh_module()

    def tearDown(self) -> None:
        _fresh_module()
        super().tearDown()

    def _make(self, **kw) -> ExecutionContext:
        defaults = dict(
            swarm_id="swarm-001",
            plan_id="PLAN-102",
            class_tier="C",
            parent_session_id="sess-abc",
        )
        defaults.update(kw)
        return ExecutionContext(**defaults)

    def test_key_not_initialized_validate_returns_no_key(self):
        ctx = self._make()
        # Cannot sign without key — must initialize first to construct payload
        ExecutionContext.regenerate_key()
        sig = ctx.sign()
        payload = ctx.to_payload()
        # Now drop the key to simulate uninitialized state at validate time
        ExecutionContext._coordinator_key = None
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "no_key")

    def test_regenerate_key_initializes_class_state(self):
        self.assertFalse(ExecutionContext.is_key_initialized())
        ExecutionContext.regenerate_key()
        self.assertTrue(ExecutionContext.is_key_initialized())
        self.assertIsNotNone(ExecutionContext._coordinator_key)
        self.assertEqual(len(ExecutionContext._coordinator_key), 32)
        self.assertEqual(ExecutionContext._nonce_counter, 0)
        self.assertEqual(ExecutionContext._seen_nonces, {})

    def test_sign_then_validate_roundtrip_ok(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_tampered_payload_validate_bad_signature(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        payload["plan_id"] = "PLAN-999"  # tamper
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "bad_signature")

    def test_stale_nonce_60s_validate_stale_nonce(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        # Backdate issued_ts by 120 seconds
        payload["issued_ts"] = int((time.time() - 120) * 1000)
        # Resign with the tampered timestamp so signature would be valid
        msg = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        new_sig = hmac.new(ExecutionContext._coordinator_key, msg, __import__("hashlib").sha256).hexdigest()
        ok, reason = ExecutionContext.validate(payload, new_sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "stale_nonce")

    def test_nonce_replay_detected(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        ok1, _ = ExecutionContext.validate(payload, sig)
        self.assertTrue(ok1)
        ok2, reason2 = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok2)
        self.assertEqual(reason2, "nonce_replay")

    def test_missing_required_field_validate_missing_field(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        del payload["plan_id"]
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_field")

    def test_hmac_constant_time_comparison_uses_compare_digest(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        with patch("hmac.compare_digest", wraps=hmac.compare_digest) as spy:
            ExecutionContext.validate(payload, sig)
            self.assertTrue(spy.called, "validate() must use hmac.compare_digest")

    def test_canonical_serialization_sort_keys_no_spaces(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        payload = ctx.to_payload()
        canonical = _ec_mod._canonical(payload)
        text = canonical.decode("utf-8")
        self.assertNotIn(" ", text, "canonical form must have no spaces")
        # Reparse must equal sorted-keys form
        roundtrip = json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
        self.assertEqual(text, roundtrip)

    def test_disabled_via_env_flag_short_circuits(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        os.environ["CEO_EXECUTION_CONTEXT_HOOKS_DISABLE"] = "1"
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "disabled")

    def test_key_rotation_invalidates_old_signatures(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        sig = ctx.sign()
        payload = ctx.to_payload()
        ExecutionContext.regenerate_key()  # rotate
        ok, reason = ExecutionContext.validate(payload, sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "bad_signature")

    def test_multi_instance_distinct_nonces(self):
        ExecutionContext.regenerate_key()
        a = self._make()
        b = self._make()
        c = self._make()
        nonces = {a._nonce, b._nonce, c._nonce}
        self.assertEqual(len(nonces), 3)

    def test_nonce_lru_prune_at_1000(self):
        ExecutionContext.regenerate_key()
        # Inject 1500 synthetic-seen nonces with monotonically newer ts
        base = time.time()
        for i in range(1500):
            ExecutionContext._seen_nonces[i] = base + i * 0.001
        ExecutionContext._prune_nonce_lru()
        self.assertLessEqual(len(ExecutionContext._seen_nonces), 1000)
        # Oldest entries should have been pruned
        self.assertNotIn(0, ExecutionContext._seen_nonces)
        self.assertIn(1499, ExecutionContext._seen_nonces)

    def test_signature_type_mismatch_bad_signature(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        payload = ctx.to_payload()
        # Non-hex non-ascii signature
        ok, reason = ExecutionContext.validate(payload, "ÿ" * 64)
        self.assertFalse(ok)
        self.assertEqual(reason, "bad_signature")

    def test_payload_not_dict_missing_field(self):
        ExecutionContext.regenerate_key()
        ok, reason = ExecutionContext.validate(["not", "a", "dict"], "deadbeef" * 8)
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_field")

    def test_future_timestamp_beyond_window_stale(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        payload = ctx.to_payload()
        payload["issued_ts"] = int((time.time() + 300) * 1000)
        msg = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        new_sig = hmac.new(ExecutionContext._coordinator_key, msg, __import__("hashlib").sha256).hexdigest()
        ok, reason = ExecutionContext.validate(payload, new_sig)
        self.assertFalse(ok)
        self.assertEqual(reason, "stale_nonce")

    def test_issued_ts_non_int_missing_field(self):
        ExecutionContext.regenerate_key()
        ctx = self._make()
        payload = ctx.to_payload()
        payload["issued_ts"] = "not-an-int"
        ok, reason = ExecutionContext.validate(payload, "x" * 64)
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_field")


if __name__ == "__main__":
    unittest.main()
