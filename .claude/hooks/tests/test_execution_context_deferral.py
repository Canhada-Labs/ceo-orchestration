"""PLAN-112-FOLLOWUP-execution-context-wire (W4) — deferral regression guard.

This module is the FIRST test coverage for `_lib/execution_context.py`.
The audit finding F-1.2-execution_context-e33bc901 confirmed the module had
**zero callers anywhere**, including tests. PLAN-112-FOLLOWUP-execution-
context-wire is an HONEST-DEFERRAL plan: the original goal (wire `sign()`
into the coordinator and `validate()` into the spawn-validator hook) is
**cryptographically infeasible cross-process** because the HMAC key
(`ExecutionContext._coordinator_key = secrets.token_bytes(32)`) is a
class-level, in-memory, per-process value, NEVER persisted to disk
(execution_context.py doctrine lines 18-21). A PreToolUse hook
(`check_agent_spawn`) runs as a fresh ephemeral process where the key is
`None`, so `validate()` short-circuits to `(False, "no_key")` BEFORE any
HMAC comparison (execution_context.py:156-157).

These tests therefore encode TWO things:

1. The primitive WORKS intra-process (sign -> validate roundtrip; tamper is
   rejected with the specific reason ``bad_signature``, not merely
   ``ok == False``). This is the value retained by the deferral.
2. The cross-process limitation is real and is a REGRESSION GUARD: a fresh
   process / cleared ``_coordinator_key`` makes ``validate()`` return
   ``(False, "no_key")``. If a future "just wire it" attempt naively calls
   ``validate()`` from a hook process, this test documents that the result
   is vacuously-False (NO security), so the gap cannot be silently
   re-introduced as a fake gate (plan §5 R2).

NO runtime wiring is asserted here — wiring is blocked until (a) the
coordinator exits scaffold AND (b) a cross-process key design lands via
ADR-133-AMEND-1 (plan §2, §4 AC5).

Runs under both ``unittest discover`` and ``pytest`` (conftest provides the
``.claude/hooks`` sys.path entry; the explicit insert below is the
unittest-discover fallback used across the hook test tree). Stdlib only.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# `.claude/hooks/` on sys.path so `from _lib import execution_context` works
# under plain `unittest discover` (pytest gets it from conftest.py, but the
# fallback is harmless + matches the convention in 97 sibling test files).
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.execution_context import ExecutionContext  # noqa: E402


def _fresh_context() -> ExecutionContext:
    """Build a context with a freshly-initialized coordinator key.

    `regenerate_key()` also clears the nonce-replay state, guaranteeing the
    nonce minted by `__init__` has NOT been observed by a prior clean
    `validate()`. This ordering matters: the nonce-replay check in
    `validate()` runs BEFORE the HMAC check, so a tamper assertion must be
    made against a payload whose nonce is still unseen — otherwise a prior
    clean validate would record the nonce and a re-validate would surface
    `nonce_replay`, masking the `bad_signature` we intend to assert.
    """
    ExecutionContext.regenerate_key()
    return ExecutionContext(
        swarm_id="swarm-deferral",
        plan_id="PLAN-102",
        class_tier="C",
        parent_session_id="sess-deferral",
    )


class TestExecutionContextIntraProcess(unittest.TestCase):
    """(a) The primitive works intra-process — value retained by deferral."""

    def setUp(self) -> None:
        # Isolate class-level state across tests (key + nonce LRU).
        ExecutionContext.regenerate_key()

    def tearDown(self) -> None:
        # Leave no key/nonce state behind for sibling test modules.
        ExecutionContext._coordinator_key = None
        ExecutionContext._nonce_counter = 0
        ExecutionContext._seen_nonces = {}

    def test_sign_then_validate_roundtrip_ok(self) -> None:
        """AC4 (a): intra-process sign -> validate roundtrip is fully valid."""
        ctx = _fresh_context()
        payload = ctx.to_payload()
        signature = ctx.sign()

        ok, reason = ExecutionContext.validate(payload, signature)

        self.assertTrue(ok, "intra-process roundtrip should validate")
        self.assertEqual(reason, "ok")


class TestExecutionContextTamperRejected(unittest.TestCase):
    """(b) Tampered payload -> reason == "bad_signature" (not just ok==False)."""

    def setUp(self) -> None:
        ExecutionContext.regenerate_key()

    def tearDown(self) -> None:
        ExecutionContext._coordinator_key = None
        ExecutionContext._nonce_counter = 0
        ExecutionContext._seen_nonces = {}

    def test_tampered_payload_field_yields_bad_signature(self) -> None:
        """AC4 (b): mutating a signed field surfaces the SPECIFIC reason.

        Assert the EXACT reason, not merely `ok is False`. A bare
        `ok==False` would also pass for `no_key` / `disabled` / `stale_nonce`
        / `nonce_replay`, hiding whether the HMAC actually detected the
        tamper. The fresh-nonce ordering (see `_fresh_context`) guarantees
        the failure is `bad_signature` and not `nonce_replay`.
        """
        ctx = _fresh_context()
        payload = ctx.to_payload()
        signature = ctx.sign()

        tampered = dict(payload)
        tampered["plan_id"] = "PLAN-999-EVIL"  # mutate a signed field

        ok, reason = ExecutionContext.validate(tampered, signature)

        self.assertFalse(ok)
        self.assertEqual(
            reason,
            "bad_signature",
            "tamper must be detected by the HMAC compare, not another gate",
        )

    def test_tampered_signature_yields_bad_signature(self) -> None:
        """AC4 (b) corollary: flipping the signature also yields bad_signature."""
        ctx = _fresh_context()
        payload = ctx.to_payload()
        signature = ctx.sign()

        # Flip the first hex nibble to produce a structurally-valid but wrong
        # signature (still ascii-encodable, so we reach the compare_digest).
        flipped = ("0" if signature[0] != "0" else "1") + signature[1:]

        ok, reason = ExecutionContext.validate(payload, flipped)

        self.assertFalse(ok)
        self.assertEqual(reason, "bad_signature")


class TestExecutionContextCrossProcessLimitation(unittest.TestCase):
    """(c) Cross-process simulation -> (False, "no_key") — the deferral guard.

    A fresh hook process has `_coordinator_key is None`. We simulate that by
    signing with a live key, then clearing the class-level key (the exact
    state of a separate ephemeral process that imported the module but never
    ran the coordinator's `regenerate_key()`). `validate()` MUST return
    `(False, "no_key")` BEFORE any HMAC comparison.

    This is the load-bearing regression guard: it documents WHY the original
    cross-process wiring is infeasible, and ensures a future naive
    "wire validate() into check_agent_spawn" change is caught as producing a
    vacuous always-False gate rather than real tamper-evidence (plan R2).
    """

    def tearDown(self) -> None:
        ExecutionContext._coordinator_key = None
        ExecutionContext._nonce_counter = 0
        ExecutionContext._seen_nonces = {}

    def test_cleared_key_simulates_fresh_process_returns_no_key(self) -> None:
        """AC4 (c): cleared `_coordinator_key` -> validate() == (False, "no_key")."""
        # Coordinator process: key live, payload signed.
        ExecutionContext.regenerate_key()
        ctx = ExecutionContext(
            swarm_id="swarm-xproc",
            plan_id="PLAN-102",
            class_tier="C",
            parent_session_id="sess-xproc",
        )
        payload = ctx.to_payload()
        signature = ctx.sign()

        # Simulate the receiving hook process: key was never initialized
        # there (in-memory, per-process, NEVER persisted).
        ExecutionContext._coordinator_key = None

        ok, reason = ExecutionContext.validate(payload, signature)

        self.assertFalse(ok)
        self.assertEqual(
            reason,
            "no_key",
            "fresh/cleared-key process must short-circuit before HMAC; "
            "cross-process validate is infeasible until ADR-133-AMEND-1",
        )

    def test_no_key_short_circuits_before_signature_check(self) -> None:
        """The `no_key` path must win even for a payload that WOULD verify.

        Proves the short-circuit is the key-presence gate, not a downstream
        bad_signature — i.e. the cross-process gap is structural, not a
        coincidence of an invalid signature.
        """
        ExecutionContext.regenerate_key()
        ctx = ExecutionContext(
            swarm_id="swarm-xproc2",
            plan_id="PLAN-102",
            class_tier="C",
            parent_session_id="sess-xproc2",
        )
        payload = ctx.to_payload()
        good_signature = ctx.sign()  # a signature that WOULD validate in-process

        ExecutionContext._coordinator_key = None

        ok, reason = ExecutionContext.validate(payload, good_signature)

        self.assertFalse(ok)
        self.assertEqual(reason, "no_key")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
