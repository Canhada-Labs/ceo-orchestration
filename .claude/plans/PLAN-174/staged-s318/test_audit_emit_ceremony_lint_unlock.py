"""SENT-S318 pack — `ceremony_lint_unlock_used` scrub-branch enforcement.

PLAN-174 W1 shipped the ceremony-lint ADR-186 escape-hatch emitter
(`check-ceremony-script.py::_emit_unlock_audit`) WITHOUT its canonical
registration half; `check-audit-registry-coverage` flagged the orphan and
the emit was PARKED in `908707e`. The SENT-S318 pack registers the action
(`_KNOWN_ACTIONS` 325 -> 326 + SPEC v2.57 row) and restores the emitter.
These tests pin the registered wire contract:

  (1) the action is a member of ``_KNOWN_ACTIONS`` (the parking trigger
      can never silently reopen);
  (2) a smuggled non-allowlisted field — the unlock REASON text being the
      one that matters — is DROPPED on the wire;
  (3) the legit producer shape (``file_sha256`` 16-hex prefix +
      ``reason_len`` int) survives the scrub intact;
  (4) malformed values are coerced to safe sentinels, never echoed:
      non-16-hex ``file_sha256`` -> ``"invalid"``; ``bool``/``float``/
      non-int ``reason_len`` -> ``0``; negatives clamp to ``0`` and
      oversized to ``9999``.

COUPLING: imports the canonical ``_lib.audit_emit``, which carries the
branch only AFTER the SENT-S318 ceremony applies the staged tree. The
test is collected only from the applied tree (pytest ``testpaths``
exclude the staged source), so it always runs against materialized code.

Env hygiene: derives from ``TestEnvContext`` (isolated ``$HOME`` + audit
log); reads ``CEO_AUDIT_LOG_PATH`` set by the context, never writes
``os.environ`` directly.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

ACTION = "ceremony_lint_unlock_used"


class _Base(TestEnvContext):
    def _events(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        out: List[Dict[str, Any]] = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out

    def _one(self) -> Dict[str, Any]:
        evs = [e for e in self._events() if e.get("action") == ACTION]
        self.assertEqual(
            len(evs), 1,
            "expected exactly 1 %s event, got %d: %r" % (ACTION, len(evs), evs),
        )
        return evs[0]


class TestRegistration(_Base):
    def test_action_is_known(self):
        self.assertIn(ACTION, audit_emit._KNOWN_ACTIONS)

    def test_action_is_not_passthrough(self):
        self.assertNotIn(ACTION, audit_emit._EMIT_GENERIC_PASSTHROUGH)

    def test_allowlist_exists_and_is_metadata_only(self):
        allow = audit_emit._CEREMONY_LINT_UNLOCK_USED_ALLOWLIST
        self.assertIn("file_sha256", allow)
        self.assertIn("reason_len", allow)
        # The reason TEXT must be structurally impossible on the wire:
        for forbidden in ("reason", "reason_text", "path", "script_body"):
            self.assertNotIn(forbidden, allow)


class TestScrub(_Base):
    def test_smuggled_reason_text_is_dropped(self):
        # emit_generic takes **kwargs as TOP-LEVEL fields (the 7d467a8
        # `fields={...}` nesting is the bug the clone-sim caught).
        audit_emit.emit_generic(
            action=ACTION,
            file_sha256="a" * 16,
            reason_len=12,
            reason_text="SECRET unlock justification text",
            path="/tmp/x.sh",
        )
        ev = self._one()
        self.assertNotIn("reason_text", ev)
        self.assertNotIn("path", ev)
        self.assertNotIn("SECRET", json.dumps(ev))

    def test_legit_producer_shape_survives(self):
        sha16 = "0123456789abcdef"
        audit_emit.emit_generic(
            action=ACTION, file_sha256=sha16, reason_len=42
        )
        ev = self._one()
        self.assertEqual(ev["file_sha256"], sha16)
        self.assertEqual(ev["reason_len"], 42)


class TestValueCoercion(_Base):
    def _emit_and_read(self, **fields: Any) -> Dict[str, Any]:
        audit_emit.emit_generic(action=ACTION, **fields)
        return self._one()

    def test_malformed_sha_coerces_to_sentinel_never_echoed(self):
        ev = self._emit_and_read(
            file_sha256="NOT-a-sha ../../etc", reason_len=1
        )
        self.assertEqual(ev["file_sha256"], "invalid")
        self.assertNotIn("etc", json.dumps(ev))

    def test_uppercase_hex_is_rejected(self):
        ev = self._emit_and_read(file_sha256="A" * 16, reason_len=1)
        self.assertEqual(ev["file_sha256"], "invalid")

    def test_wrong_length_hex_is_rejected(self):
        ev = self._emit_and_read(file_sha256="ab" * 16, reason_len=1)
        self.assertEqual(ev["file_sha256"], "invalid")

    def test_bool_reason_len_is_zeroed(self):
        # bool is an int subclass — the S181 float/bool wire class.
        ev = self._emit_and_read(file_sha256="a" * 16, reason_len=True)
        self.assertEqual(ev["reason_len"], 0)
        self.assertIsInstance(ev["reason_len"], int)

    def test_float_reason_len_is_zeroed_not_dropped(self):
        # A float reaching canonical_json would drop the WHOLE event —
        # the branch must coerce BEFORE the wire.
        ev = self._emit_and_read(file_sha256="a" * 16, reason_len=3.5)
        self.assertEqual(ev["reason_len"], 0)

    def test_negative_clamps_to_zero_and_oversize_to_cap(self):
        ev = self._emit_and_read(file_sha256="a" * 16, reason_len=-7)
        self.assertEqual(ev["reason_len"], 0)

    def test_oversize_clamps_to_cap(self):
        ev = self._emit_and_read(file_sha256="a" * 16, reason_len=123456)
        self.assertEqual(ev["reason_len"], 9999)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
