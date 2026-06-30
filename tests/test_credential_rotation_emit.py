"""PLAN-085 Wave C.2 + PLAN-117 WS-A — credential lifecycle blocking + override.

Covers ADR-040 §4 + ADR-040-AMEND-2 (blocking enforcement, PLAN-085 Wave 0
SHIPPED S109) AND the §Layer-1 trust-root contract repair (PLAN-117 WS-A S176):
the emergency override is sourced SOLELY from the import-time trust-root
snapshot (``_lib.trusted_env``), validated fail-CLOSED against
``^[A-Z][A-Z0-9]*-\\d+$``, and a late-set (post-anchor) value is recorded
forensically, never honored.

Tests drive the snapshot via ``self._set_snapshot(...)`` (NOT live os.environ).

  - test_warn_emit_at_warn_threshold          — 75d emits rotation_due, no block
  - test_block_emit_at_max_threshold          — 90d emits blocked_due_to_age + raises
  - test_emergency_override_with_ticket        — valid ticket in snapshot grants pass
  - test_emergency_override_empty_fails        — empty value at anchor → block
  - test_override_grant_sourced_from_snapshot_not_live_env — live env irrelevant to grant
  - test_override_audit_emits_ticket_id        — override event carries ticket_id
  - test_invoke_time_not_import_time           — age check at call() not import
  - test_fresh_credential_passes_silently      — 10d emits nothing
  - test_credential_block_override_uses_trust_root_snapshot — AC-A2(i) late-set ignored
  - test_late_set_forensic_payload_omits_value — forensic emit never echoes the value
  - test_malformed_ticket_id_rejected_fail_closed — AC-A2(iii) regex fail-CLOSED
  - test_get_trusted_immutable_to_post_import_mutation — AC-A2(ii) snapshot read-only
  - test_consumer_sources_override_from_snapshot_not_live_environ — regression grep-guard

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402

# ADR-040-AMEND-2 §Layer-1: the emergency override is sourced SOLELY from the
# import-time trust-root snapshot (_lib.trusted_env.ORIGINAL_CEO_ENV). Tests
# drive that snapshot via ``self._set_snapshot(...)`` — NOT live os.environ.
_OVERRIDE_VAR = "CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE"


def _iso_n_days_ago(days: int) -> str:
    return (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    ).isoformat()


class _EmitCapture:
    """Stand-in for _lib.audit_emit that records calls instead of writing."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def emit_credential_rotation_due(self, **kw: Any) -> None:
        self.calls.append({"action": "credential_rotation_due", **kw})

    def emit_credential_blocked_due_to_age(self, **kw: Any) -> None:
        self.calls.append({"action": "credential_blocked_due_to_age", **kw})

    def emit_credential_emergency_override_used(self, **kw: Any) -> None:
        self.calls.append({
            "action": "credential_emergency_override_used", **kw,
        })

    def emit_credential_override_late_set_ignored(self, **kw: Any) -> None:
        self.calls.append({
            "action": "credential_override_late_set_ignored", **kw,
        })

    def emit_live_adapter_blocked(self, **kw: Any) -> None:
        self.calls.append({"action": "live_adapter_blocked", **kw})


class TestCredentialRotationEmit(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        # Set up a fake credential-rotation.json in the isolated HOME.
        self.rotation_log = (
            self.home_dir / ".claude" / "projects"
            / "ceo-orchestration" / "credential-rotation.json"
        )
        self.rotation_log.parent.mkdir(parents=True, exist_ok=True)
        # Activate live adapter + credential env var so _activation_check
        # passes through to _check_credential_age.
        import os
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-fixture-not-real"
        # Tests assert on audit emits — pin sync mode so emits are not left
        # unflushed in the async spool (feedback-test-set-ceo-audit-sync-mode).
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

        # Provide a passing live_adapter_allowlist so C.1 doesn't trip.
        settings = self.project_dir / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True, exist_ok=True)
        settings.write_text(
            json.dumps({"live_adapter_allowlist": ["claude"]}),
            encoding="utf-8",
        )

        # Deterministic baseline: empty trust-root snapshot regardless of the
        # ambient shell. Tests that exercise the override set it explicitly.
        self._set_snapshot({})

    def _write_rotation(self, age_days: int) -> None:
        record = {"claude": {"rotated_at": _iso_n_days_ago(age_days)}}
        self.rotation_log.write_text(json.dumps(record), encoding="utf-8")

    def _build_adapter_with_capture(self) -> tuple:
        """Construct ClaudeLiveAdapter with _lib.audit_emit emit_X functions
        replaced by capture stand-ins.

        Returns (adapter, capture). The adapter's _check_credential_age
        loads `from _lib import audit_emit` lazily; we override the
        relevant emit_* function attributes on the real module so the
        capture is invoked regardless of import shape.
        """
        from _lib.adapters.live.claude import ClaudeLiveAdapter
        from _lib import audit_emit as _real
        capture = _EmitCapture()
        self._restore_emits: Dict[str, Any] = {}
        for name in (
            "emit_credential_rotation_due",
            "emit_credential_blocked_due_to_age",
            "emit_credential_emergency_override_used",
            "emit_credential_override_late_set_ignored",
            "emit_live_adapter_blocked",
        ):
            self._restore_emits[name] = getattr(_real, name, None)
            setattr(_real, name, getattr(capture, name))
        return ClaudeLiveAdapter(), capture

    def tearDown(self) -> None:
        try:
            from _lib import audit_emit as _real
            for name, orig in getattr(self, "_restore_emits", {}).items():
                if orig is None:
                    try:
                        delattr(_real, name)
                    except AttributeError:
                        pass
                else:
                    setattr(_real, name, orig)
        finally:
            super().tearDown()

    def _invoke_age_check(self, adapter: Any) -> Optional[Exception]:
        """Invoke _check_credential_age, returning the raised exception
        (if any) or None on pass-through."""
        try:
            adapter._check_credential_age()
            return None
        except Exception as e:
            return e

    def _set_snapshot(self, mapping: Dict[str, str]) -> None:
        """Replace the trust-root snapshot (_lib.trusted_env.ORIGINAL_CEO_ENV)
        for the test duration; restored on cleanup (LIFO). This is the SOLE
        source of the emergency override per ADR-040-AMEND-2 §Layer-1.
        """
        from _lib import trusted_env
        patcher = mock.patch.dict(
            trusted_env.ORIGINAL_CEO_ENV, mapping, clear=True
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # ------------------------------------------------------------------
    # Cases 1-8
    # ------------------------------------------------------------------

    def test_warn_emit_at_warn_threshold(self) -> None:
        """75d age emits credential_rotation_due, no block."""
        self._write_rotation(76)  # > warn_threshold (75), < max (90)
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        self.assertIsNone(exc)
        actions = [c["action"] for c in capture.calls]
        self.assertIn("credential_rotation_due", actions)
        self.assertNotIn("credential_blocked_due_to_age", actions)

    def test_block_emit_at_max_threshold(self) -> None:
        """90d age emits credential_blocked_due_to_age + raises CredentialExpired."""
        self._write_rotation(91)
        adapter, capture = self._build_adapter_with_capture()
        # No override env set → must block.
        import os
        os.environ.pop("CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE", None)
        exc = self._invoke_age_check(adapter)
        self.assertIsNotNone(exc)
        from _lib.exceptions import CredentialExpired
        self.assertIsInstance(exc, CredentialExpired)
        self.assertEqual(getattr(exc, "provider", None), "claude")
        actions = [c["action"] for c in capture.calls]
        self.assertIn("credential_blocked_due_to_age", actions)

    def test_emergency_override_with_ticket(self) -> None:
        """90d + valid ticket in the trust-root snapshot grants pass."""
        self._write_rotation(95)
        self._set_snapshot({_OVERRIDE_VAR: "OPS-1234"})
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        self.assertIsNone(exc, msg="override must grant pass")
        actions = [c["action"] for c in capture.calls]
        self.assertIn("credential_emergency_override_used", actions)
        self.assertNotIn("credential_blocked_due_to_age", actions)

    def test_severity_style_ticket_id_accepted(self) -> None:
        """A letter-led alphanumeric prefix (e.g. SEV1-42) is a valid ticket.

        Regression for the ADR-040-AMEND-2 §3.3 self-contradiction (the §200
        example ``SEV1-42`` was rejected by the original ``^[A-Z]+-\\d+$``); the
        validator is ``^[A-Z][A-Z0-9]*-\\d+$`` so both documented examples match.
        """
        self._write_rotation(95)
        self._set_snapshot({_OVERRIDE_VAR: "SEV1-42"})
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        self.assertIsNone(exc, msg="SEV1-42 must be a valid override ticket")
        actions = [c["action"] for c in capture.calls]
        self.assertIn("credential_emergency_override_used", actions)

    def test_emergency_override_empty_fails(self) -> None:
        """90d + empty override value at anchor falls through to block."""
        self._write_rotation(95)
        self._set_snapshot({_OVERRIDE_VAR: ""})
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        from _lib.exceptions import CredentialExpired
        self.assertIsInstance(exc, CredentialExpired)

    def test_override_grant_sourced_from_snapshot_not_live_env(self) -> None:
        """The grant is sourced from the trust-root snapshot, so mutating the
        LIVE environment between calls does NOT change the verdict.

        Replaces the pre-PLAN-117 ``test_emergency_override_after_24h_fails``,
        whose premise (clearing live env re-blocks) is void under the
        snapshot-as-SOLE-source contract. The 24h window is a tracked WS-A
        follow-up, not enforced at this layer.
        """
        self._write_rotation(95)
        self._set_snapshot({_OVERRIDE_VAR: "OPS-1234"})
        import os
        os.environ[_OVERRIDE_VAR] = "OPS-1234"
        adapter, capture = self._build_adapter_with_capture()
        # Call #1: snapshot grants → pass.
        exc1 = self._invoke_age_check(adapter)
        self.assertIsNone(exc1)
        # Clearing the LIVE env leaves the snapshot intact → still granted.
        os.environ.pop(_OVERRIDE_VAR, None)
        exc2 = self._invoke_age_check(adapter)
        self.assertIsNone(
            exc2, msg="snapshot grant must be independent of live env"
        )

    def test_override_audit_emits_ticket_id(self) -> None:
        """Override event payload carries the ticket-id (from the snapshot)."""
        self._write_rotation(100)
        self._set_snapshot({_OVERRIDE_VAR: "INC-99887"})
        adapter, capture = self._build_adapter_with_capture()
        self._invoke_age_check(adapter)
        override_events = [
            c for c in capture.calls
            if c["action"] == "credential_emergency_override_used"
        ]
        self.assertEqual(len(override_events), 1)
        self.assertEqual(override_events[0]["ticket_id"], "INC-99887")
        self.assertEqual(override_events[0]["age_days"], 100)
        self.assertEqual(override_events[0]["max_age_days"], 90)

    def test_invoke_time_not_import_time(self) -> None:
        """Age check runs at call()-path, NOT module-import.

        Imports the adapter module without triggering any rotation
        event; the rotation log is set up with a stale credential,
        but no _check_credential_age call is made.
        """
        self._write_rotation(95)
        capture = _EmitCapture()
        import importlib
        from _lib.adapters.live import claude as claude_mod
        # Swap the module-table slot for the capture instance ONLY for the
        # duration of the reload, then restore. Leaking this binding pollutes
        # sys.modules["_lib.audit_emit"] process-wide: later lazy importers
        # (e.g. spool_writer Phase 4/5 rotation probes that call
        # _audit_emit_lazy._rotate_if_needed_safe) would receive this shim
        # instead of the real module and raise AttributeError.
        _saved_ae = sys.modules.get("_lib.audit_emit")
        sys.modules["_lib.audit_emit"] = capture  # type: ignore
        try:
            # Re-import the adapter module — this would trigger emit if
            # the check were at import-time.
            importlib.reload(claude_mod)
            self.assertEqual(
                capture.calls, [],
                msg="rotation event emitted at import — must be invoke-only",
            )
        finally:
            if _saved_ae is not None:
                sys.modules["_lib.audit_emit"] = _saved_ae
            else:
                sys.modules.pop("_lib.audit_emit", None)
            # Re-bind the adapter module against the restored real module so
            # no later test inherits a reload anchored on the shim.
            importlib.reload(claude_mod)

    def test_fresh_credential_passes_silently(self) -> None:
        """10d age does NOT emit any rotation event."""
        self._write_rotation(10)
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        self.assertIsNone(exc)
        rotation_events = [
            c for c in capture.calls
            if c["action"] in {
                "credential_rotation_due",
                "credential_blocked_due_to_age",
                "credential_emergency_override_used",
            }
        ]
        self.assertEqual(rotation_events, [])

    # ------------------------------------------------------------------
    # PLAN-117 WS-A — ADR-040-AMEND-2 §Layer-1 trust-root override contract
    # ------------------------------------------------------------------

    def test_credential_block_override_uses_trust_root_snapshot(self) -> None:
        """AC-A2(i) — a late-set os.environ mutation is IGNORED.

        The override var is ABSENT from the trust-root snapshot but set in the
        live environment after trust-anchor. It must NOT grant the override:
        the call blocks (CredentialExpired) and the late-set is recorded
        forensically, NOT honored as ``credential_emergency_override_used``.
        """
        self._write_rotation(95)
        self._set_snapshot({})  # override absent at anchor
        import os
        os.environ[_OVERRIDE_VAR] = "INC-1234"  # late-set, valid format
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        from _lib.exceptions import CredentialExpired
        self.assertIsInstance(
            exc, CredentialExpired,
            msg="late-set override must be ignored → block",
        )
        actions = [c["action"] for c in capture.calls]
        self.assertIn("credential_override_late_set_ignored", actions)
        self.assertNotIn("credential_emergency_override_used", actions)

    def test_late_set_forensic_payload_omits_value(self) -> None:
        """The adapter emits the forensic action with a safe provenance hint and
        NEVER the rejected override value. (The adapter passes no
        ``attempted_var_name`` — the dispatch gate forces it; see
        ``test_real_emit_gate_forces_var_name_and_coerces_provenance``.)"""
        self._write_rotation(95)
        self._set_snapshot({})
        import os
        os.environ[_OVERRIDE_VAR] = "INC-1234"
        adapter, capture = self._build_adapter_with_capture()
        self._invoke_age_check(adapter)
        ev = [
            c for c in capture.calls
            if c["action"] == "credential_override_late_set_ignored"
        ]
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["provenance_hint"], "late_os_environ_set")
        # The rejected value must not appear anywhere in the payload.
        self.assertNotIn("INC-1234", json.dumps(ev[0]))

    def test_malformed_ticket_id_rejected_fail_closed(self) -> None:
        """AC-A2(iii) — a malformed ticket-id in the snapshot is fail-CLOSED.

        Present at anchor (so NOT a late-set) but not matching
        ``^[A-Z][A-Z0-9]*-\\d+$`` → blocked, never honored, and no spurious
        late-set forensic emit.
        """
        self._write_rotation(95)
        self._set_snapshot({_OVERRIDE_VAR: "not-a-ticket"})
        adapter, capture = self._build_adapter_with_capture()
        exc = self._invoke_age_check(adapter)
        from _lib.exceptions import CredentialExpired
        self.assertIsInstance(exc, CredentialExpired)
        actions = [c["action"] for c in capture.calls]
        self.assertNotIn("credential_emergency_override_used", actions)
        self.assertNotIn("credential_override_late_set_ignored", actions)
        self.assertIn("credential_blocked_due_to_age", actions)

    def test_get_trusted_immutable_to_post_import_mutation(self) -> None:
        """AC-A2(ii) — trusted_env.get_trusted ignores post-import os.environ
        mutation; the snapshot is process-scoped and read-only."""
        from _lib import trusted_env
        import os
        probe = "CEO_TRUSTED_ENV_PROBE_X"
        self.assertIsNone(trusted_env.get_trusted(probe))
        self.assertFalse(trusted_env.was_present_at_anchor(probe))
        os.environ[probe] = "set-after-import"
        try:
            self.assertIsNone(
                trusted_env.get_trusted(probe),
                msg="post-import mutation must not appear in the snapshot",
            )
            self.assertFalse(trusted_env.was_present_at_anchor(probe))
        finally:
            os.environ.pop(probe, None)

    def test_consumer_sources_override_from_snapshot_not_live_environ(self) -> None:
        """Regression grep-guard (WS-A task 4): the live adapter must source the
        override from the trust-root snapshot, never live os.environ as a grant.
        """
        from _lib.adapters.live import claude as claude_mod
        src = Path(claude_mod.__file__).read_text(encoding="utf-8")
        # The snapshot accessor IS consulted.
        self.assertIn(
            "get_trusted(_EMERGENCY_OVERRIDE_VAR)", src,
            msg="override must be read from the trust-root snapshot",
        )
        # The exact pre-repair live-read literal must NOT reappear.
        self.assertNotIn(
            'os.environ.get("CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE")', src,
            msg="live os.environ read of the override literal is the regression",
        )
        # Any live read of the override var must be forensic-only (annotated).
        for line in src.splitlines():
            if "os.environ.get(_EMERGENCY_OVERRIDE_VAR)" in line:
                self.assertIn(
                    "forensic-only", line,
                    msg=f"un-annotated live override read: {line.strip()!r}",
                )

    def test_real_emit_gate_forces_var_name_and_coerces_provenance(self) -> None:
        """The emit_generic dispatch gate self-enforces the no-value-echo
        contract on the REAL path, independent of the caller: an adversarial
        direct call that smuggles the rejected value via BOTH
        ``attempted_var_name`` and ``provenance_hint`` has the var name FORCED to
        the constant and the out-of-enum hint COERCED to ``unspecified`` — neither
        leak string reaches the persisted event.
        """
        from _lib import audit_emit
        captured: Dict[str, Any] = {}
        orig = audit_emit._write_event
        audit_emit._write_event = lambda event: captured.update(event)
        try:
            audit_emit.emit_generic(
                "credential_override_late_set_ignored",
                provider="claude",
                attempted_var_name="INC-9999-LEAKED",   # adversarial smuggle
                provenance_hint="SECRET-VALUE-LEAK",     # adversarial smuggle
            )
        finally:
            audit_emit._write_event = orig
        self.assertEqual(captured.get("action"), "credential_override_late_set_ignored")
        self.assertEqual(captured.get("attempted_var_name"), _OVERRIDE_VAR)
        self.assertEqual(captured.get("provenance_hint"), "unspecified")
        blob = json.dumps(captured)
        self.assertNotIn("INC-9999-LEAKED", blob)
        self.assertNotIn("SECRET-VALUE-LEAK", blob)

    def test_real_emit_gate_passes_valid_provenance(self) -> None:
        """A valid in-enum provenance_hint passes through unchanged; the typed
        emitter never lets a caller set attempted_var_name."""
        from _lib import audit_emit
        captured: Dict[str, Any] = {}
        orig = audit_emit._write_event
        audit_emit._write_event = lambda event: captured.update(event)
        try:
            audit_emit.emit_credential_override_late_set_ignored(
                provider="claude", provenance_hint="subprocess_inherited",
            )
        finally:
            audit_emit._write_event = orig
        self.assertEqual(captured.get("provenance_hint"), "subprocess_inherited")
        self.assertEqual(captured.get("attempted_var_name"), _OVERRIDE_VAR)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
