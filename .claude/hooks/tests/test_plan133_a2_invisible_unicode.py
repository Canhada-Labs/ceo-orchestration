#!/usr/bin/env python3
"""PLAN-133 A2 — invisible-unicode hard-block: detection + no-value-echo tests.

Env / HOME isolation via ``TestEnvContext`` (never the real $HOME / audit log).
Asserts:
  - the Tag-block U+E0000–E007F is detected + counted separately (tag_chars_stripped);
  - bidi/zero-width detection + count is UNCHANGED for non-Tag inputs (backward compat);
  - has_invisible_unicode() is the single force-block predicate;
  - default-OFF: CEO_UNICODE_HARDBLOCK unset → advisory (no block, enforced=0 emit);
  - CEO_UNICODE_HARDBLOCK=1 → fail-CLOSED block at spawn;
  - the emitted invisible_unicode_blocked event carries ONLY closed-enum
    surface + unicode_class + bounded char_count + enforced — never the prompt
    text, never the matched characters;
  - the audit_emit closed set mirrors the sanitizer's (no drift);
  - an out-of-set unicode_class / surface is coerced; char_count is clamped.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import spec_context_sanitizer as scs  # noqa: E402
from _lib import audit_emit  # noqa: E402
from _lib import trusted_env  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

# A Tag-block char (U+E0041 = TAG LATIN CAPITAL LETTER A) and a bidi RLO.
TAG_A = "\U000E0041"
RLO = "‮"
ZWSP = "​"


def _load_spawn_module():
    """Import check_agent_spawn.py (dash-free name) as a module."""
    path = _HOOKS_DIR / "check_agent_spawn.py"
    spec = importlib.util.spec_from_file_location("check_agent_spawn_a2", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_agent_spawn_a2"] = mod
    spec.loader.exec_module(mod)
    return mod


class TagBlockDetectionTests(TestEnvContext):
    def test_tag_block_detected_and_counted_separately(self):
        r = scs.sanitize("hello" + TAG_A + TAG_A + "world")
        self.assertEqual(r.tag_chars_stripped, 2)
        # Tag chars are NOT double-counted into bidi_zw.
        self.assertEqual(r.bidi_zw_chars_stripped, 0)
        # And they ARE stripped from the cleaned text.
        self.assertNotIn(TAG_A, r.text)

    def test_bidi_zw_unchanged_for_non_tag_input(self):
        r = scs.sanitize("a" + RLO + "b" + ZWSP + "c")
        self.assertEqual(r.bidi_zw_chars_stripped, 2)
        self.assertEqual(r.tag_chars_stripped, 0)

    def test_mixed_classes_counted_independently(self):
        r = scs.sanitize(RLO + TAG_A + "\x07")  # bidi + tag + BEL control
        self.assertEqual(r.bidi_zw_chars_stripped, 1)
        self.assertEqual(r.tag_chars_stripped, 1)
        self.assertEqual(r.control_chars_stripped, 1)

    def test_has_invisible_unicode_predicate(self):
        self.assertTrue(scs.has_invisible_unicode("x" + TAG_A))
        self.assertTrue(scs.has_invisible_unicode("x" + RLO))
        self.assertFalse(scs.has_invisible_unicode("clean ascii text"))

    def test_invisible_unicode_count_sums_all_classes(self):
        r = scs.sanitize(RLO + TAG_A + "\x07")
        self.assertEqual(scs.invisible_unicode_count(r), 3)

    def test_classify_priority(self):
        self.assertEqual(
            scs.classify_invisible_unicode(scs.sanitize(TAG_A + RLO)),
            "tag_block",  # tag_block > bidi_zw
        )
        self.assertEqual(
            scs.classify_invisible_unicode(scs.sanitize(RLO)),
            "bidi_zw",
        )
        self.assertEqual(
            scs.classify_invisible_unicode(scs.sanitize("clean")),
            "none",
        )


class SpawnHardBlockTests(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.spawn = _load_spawn_module()
        # S225 order-dependency fix: trusted_env freezes its CEO_* snapshot at
        # FIRST import in the process. When this file runs solo, that first
        # import can happen inside a sibling test's patch.dict with
        # CEO_UNICODE_HARDBLOCK=1, freezing enforcement ON and failing
        # test_default_off_is_advisory_no_block. Pin the snapshot empty so
        # each test's os.environ patch is the only enforcement channel.
        patcher = mock.patch.dict(trusted_env.ORIGINAL_CEO_ENV, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_default_off_is_advisory_no_block(self):
        # CEO_UNICODE_HARDBLOCK unset → no block (None), advisory emit only.
        with mock.patch.dict("os.environ", {}, clear=False):
            self.assertIsNone(
                self.spawn._enforce_spec_context_unicode("hi " + TAG_A)
            )

    def test_flag_on_blocks_tag_block(self):
        with mock.patch.dict(
            "os.environ", {"CEO_UNICODE_HARDBLOCK": "1"}, clear=False
        ):
            reason = self.spawn._enforce_spec_context_unicode("hi " + TAG_A)
            self.assertIsNotNone(reason)
            self.assertIn("invisible_unicode_blocked", reason)
            # No-value-echo: the matched char is never in the reason string.
            self.assertNotIn(TAG_A, reason)

    def test_flag_on_blocks_bidi(self):
        with mock.patch.dict(
            "os.environ", {"CEO_UNICODE_HARDBLOCK": "1"}, clear=False
        ):
            reason = self.spawn._enforce_spec_context_unicode("a" + RLO + "b")
            self.assertIsNotNone(reason)
            self.assertNotIn(RLO, reason)

    def test_clean_prompt_never_blocks_even_when_enforced(self):
        with mock.patch.dict(
            "os.environ", {"CEO_UNICODE_HARDBLOCK": "1"}, clear=False
        ):
            self.assertIsNone(
                self.spawn._enforce_spec_context_unicode("clean ascii prompt")
            )

    def test_master_kill_forces_advisory(self):
        with mock.patch.dict(
            "os.environ",
            {"CEO_UNICODE_HARDBLOCK": "1", "CEO_SOTA_DISABLE": "1"},
            clear=False,
        ):
            self.assertIsNone(
                self.spawn._enforce_spec_context_unicode("hi " + TAG_A)
            )


class InvisibleUnicodeNoValueEchoTests(TestEnvContext):
    """The emitted audit event must NEVER contain the prompt text or matched chars."""

    def _read_audit_events(self):
        # TestEnvContext sets CEO_AUDIT_SYNC_MODE=1 → event is on disk immediately.
        path = self.audit_dir / "audit-log.jsonl"
        out = []
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def test_emitted_event_has_only_closed_enums(self):
        audit_emit.emit_generic(
            "invisible_unicode_blocked",
            surface="spawn",
            unicode_class="tag_block",
            char_count=3,
            enforced=1,
        )
        e = self._read_audit_events()[-1]
        self.assertEqual(e["action"], "invisible_unicode_blocked")
        self.assertEqual(e["unicode_class"], "tag_block")
        self.assertEqual(e["surface"], "spawn")
        self.assertEqual(e["char_count"], 3)
        self.assertEqual(e["enforced"], 1)
        blob = json.dumps(e)
        # No leak of the matched chars or any prompt text.
        for forbidden in (TAG_A, RLO, ZWSP, "secret", "payload"):
            self.assertNotIn(forbidden, blob)
        # No forbidden field names.
        for k in ("prompt", "content", "text", "chars", "command", "reason"):
            self.assertNotIn(k, e)

    def test_out_of_set_class_coerced_to_control(self):
        audit_emit.emit_generic(
            "invisible_unicode_blocked",
            surface="spawn",
            unicode_class="\U000E0041-SMUGGLED",  # raw value smuggle attempt
            char_count=1,
            enforced=0,
        )
        e = self._read_audit_events()[-1]
        self.assertEqual(e["unicode_class"], "control")
        self.assertNotIn("SMUGGLED", json.dumps(e))

    def test_out_of_set_surface_coerced(self):
        audit_emit.emit_generic(
            "invisible_unicode_blocked",
            surface="../../etc/passwd",
            unicode_class="bidi_zw",
            char_count=1,
            enforced=0,
        )
        e = self._read_audit_events()[-1]
        self.assertEqual(e["surface"], "spawn")
        self.assertNotIn("passwd", json.dumps(e))

    def test_char_count_clamped_and_forbidden_field_dropped(self):
        audit_emit.emit_generic(
            "invisible_unicode_blocked",
            surface="skill_write",
            unicode_class="tag_block",
            char_count=10 ** 9,  # absurd → clamped
            enforced=1,
            prompt="LD_PRELOAD=/tmp/evil.so" + TAG_A,  # forbidden field
        )
        e = self._read_audit_events()[-1]
        self.assertEqual(e["char_count"], 1_000_000)
        self.assertNotIn("prompt", e)
        self.assertNotIn("evil.so", json.dumps(e))


class InvisibleUnicodeAuditDriftTests(TestEnvContext):
    def test_closed_set_mirrors_audit_emit(self):
        self.assertEqual(
            scs.INVISIBLE_UNICODE_CLASSES,
            audit_emit._INVISIBLE_UNICODE_CLASSES,
            "sanitizer and audit_emit closed unicode_class sets drifted",
        )


if __name__ == "__main__":
    unittest.main()
