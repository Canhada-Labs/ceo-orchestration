"""Unit tests for _lib/state_store.py — unified plan-scoped KV backend.

Covers ADR-027: envelope, redaction, TTL, filelock isolation, audit
events. Each test asserts ≥1 behavior beyond exit code (consensus S5
hard gate) — file on disk, sqlite row, audit JSON field.
"""

from __future__ import annotations

import json
import os
import sys
import time
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402
from _lib import state_store  # noqa: E402
from _lib.state_store import (  # noqa: E402
    SqliteStateStore,
    StateStoreInvalidName,
    StateStoreValueTooLarge,
    open_store,
)


class TestStateStore(TestEnvContext):
    """Behavior tests for SqliteStateStore — contract from ADR-027."""

    def setUp(self) -> None:
        super().setUp()
        # Point state_root at the isolated temp home
        os.environ["CEO_STATE_ROOT"] = str(self.home_dir / ".claude" / "state")

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]

    # --- round trip ------------------------------------------------------

    def test_set_get_string_round_trip(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("key1", "hello world")
            self.assertEqual(s.get("key1"), b"hello world")

    def test_set_get_bytes_round_trip(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("binary", b"\x00\x01\x02")
            self.assertEqual(s.get("binary"), b"\x00\x01\x02")

    def test_get_missing_key_returns_none(self):
        with open_store("scratchpad", "PLAN-011") as s:
            self.assertIsNone(s.get("nope"))

    def test_set_overwrites_existing(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("k", "v1")
            s.set("k", "v2")
            self.assertEqual(s.get("k"), b"v2")

    # --- redaction -------------------------------------------------------

    def test_string_with_secret_is_redacted_before_store(self):
        # sk- pattern -> [API_KEY]; password= -> [REDACTED] — either label is fine,
        # the invariant under test is "raw secret does not reach sqlite".
        secret = "sk-abcdef1234567890abcdef"
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("token", f"auth={secret}")
            value = s.get("token")
            self.assertIsNotNone(value)
            self.assertNotIn(secret.encode(), value)
            # Expect the sk- redactor label; sentinel any of the known labels
            self.assertTrue(
                b"[API_KEY]" in value or b"[REDACTED]" in value,
                f"redacted value unexpectedly lacks a known label: {value!r}",
            )

    def test_bytes_value_is_never_redacted(self):
        # Pass a bytes payload that would match the redactor as a string
        payload = b"sk-abcdef1234567890abcdef"
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("opaque", payload)
            self.assertEqual(s.get("opaque"), payload)

    def test_audit_records_redaction_applied_when_changed(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("has_secret", "password=supersecret123")
        events = [e for e in self._read_log() if e["action"] == "state_store_write"]
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["redaction_applied"])

    def test_audit_records_no_redaction_for_clean_string(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("clean", "just some text with no secrets")
        events = [e for e in self._read_log() if e["action"] == "state_store_write"]
        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["redaction_applied"])

    # --- size cap --------------------------------------------------------

    def test_value_over_cap_raises(self):
        with open_store("scratchpad", "PLAN-011", value_max_bytes=128) as s:
            with self.assertRaises(StateStoreValueTooLarge):
                s.set("big", b"x" * 200)

    def test_value_at_cap_boundary_accepted(self):
        with open_store("scratchpad", "PLAN-011", value_max_bytes=128) as s:
            s.set("edge", b"x" * 128)
            self.assertEqual(len(s.get("edge")), 128)

    # --- name validation -------------------------------------------------

    def test_reject_store_name_with_slash(self):
        with self.assertRaises(StateStoreInvalidName):
            SqliteStateStore("scratch/pad", "PLAN-011")

    def test_reject_plan_id_double_dot(self):
        with self.assertRaises(StateStoreInvalidName):
            SqliteStateStore("scratchpad", "PLAN-..")

    def test_reject_plan_id_leading_dot(self):
        with self.assertRaises(StateStoreInvalidName):
            SqliteStateStore("scratchpad", ".hidden")

    def test_reject_empty_store_name(self):
        with self.assertRaises(StateStoreInvalidName):
            SqliteStateStore("", "PLAN-011")

    def test_reject_empty_plan_id(self):
        with self.assertRaises(StateStoreInvalidName):
            SqliteStateStore("scratchpad", "")

    # --- TTL -------------------------------------------------------------

    def test_ttl_expired_get_returns_none(self):
        # PLAN-045 Wave 2 F-03-04: injectable clock replaces time.sleep(1.2).
        clk = [1000.0]
        with open_store("scratchpad", "PLAN-011", clock=lambda: clk[0]) as s:
            s.set("stale", "temp", ttl_seconds=1)
            clk[0] += 2  # fast-forward past the 1-second TTL
            self.assertIsNone(s.get("stale"))

    def test_ttl_none_never_expires(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("persistent", "forever")
            self.assertEqual(s.get("persistent"), b"forever")

    def test_negative_ttl_raises(self):
        with open_store("scratchpad", "PLAN-011") as s:
            with self.assertRaises(ValueError):
                s.set("bad", "v", ttl_seconds=-5)

    def test_zero_ttl_raises(self):
        with open_store("scratchpad", "PLAN-011") as s:
            with self.assertRaises(ValueError):
                s.set("bad", "v", ttl_seconds=0)

    # --- prune -----------------------------------------------------------

    def test_prune_expired_removes_and_reports_count(self):
        clk = [1000.0]
        with open_store("scratchpad", "PLAN-011", clock=lambda: clk[0]) as s:
            s.set("a", "1", ttl_seconds=1)
            s.set("b", "2", ttl_seconds=1)
            s.set("c", "3")  # no expiry
            clk[0] += 2
            pruned = s.prune_expired()
            self.assertEqual(pruned, 2)
            # c survives
            self.assertEqual(s.get("c"), b"3")

    def test_prune_emits_audit_event(self):
        clk = [1000.0]
        with open_store("scratchpad", "PLAN-011", clock=lambda: clk[0]) as s:
            s.set("expiring", "x", ttl_seconds=1)
            clk[0] += 2
            s.prune_expired()
        prune_events = [e for e in self._read_log() if e["action"] == "state_store_pruned"]
        self.assertEqual(len(prune_events), 1)
        self.assertEqual(prune_events[0]["keys_pruned_count"], 1)
        self.assertEqual(prune_events[0]["store_name"], "scratchpad")

    # --- list_keys -------------------------------------------------------

    def test_list_keys_skips_expired_by_default(self):
        clk = [1000.0]
        with open_store("scratchpad", "PLAN-011", clock=lambda: clk[0]) as s:
            s.set("live", "a")
            s.set("dead", "b", ttl_seconds=1)
            clk[0] += 2
            self.assertEqual(s.list_keys(), ["live"])

    def test_list_keys_include_expired_shows_all(self):
        clk = [1000.0]
        with open_store("scratchpad", "PLAN-011", clock=lambda: clk[0]) as s:
            s.set("live", "a")
            s.set("dead", "b", ttl_seconds=1)
            clk[0] += 2
            self.assertEqual(set(s.list_keys(include_expired=True)), {"live", "dead"})

    # --- delete ----------------------------------------------------------

    def test_delete_existing_returns_true(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("k", "v")
            self.assertTrue(s.delete("k"))
            self.assertIsNone(s.get("k"))

    def test_delete_missing_returns_false(self):
        with open_store("scratchpad", "PLAN-011") as s:
            self.assertFalse(s.delete("never-existed"))

    # --- clear_plan ------------------------------------------------------

    def test_clear_plan_drops_every_key(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("a", "1")
            s.set("b", "2")
            s.set("c", "3")
            cleared = s.clear_plan()
            self.assertEqual(cleared, 3)
            self.assertEqual(s.list_keys(), [])

    def test_clear_plan_emits_pruned_event(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("a", "1")
            s.clear_plan()
        events = [e for e in self._read_log() if e["action"] == "state_store_pruned"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["keys_pruned_count"], 1)

    # --- isolation -------------------------------------------------------

    def test_two_plans_do_not_leak(self):
        with open_store("scratchpad", "PLAN-011") as a:
            a.set("shared-key", "from-plan-011")
        with open_store("scratchpad", "PLAN-012") as b:
            self.assertIsNone(b.get("shared-key"))
            b.set("shared-key", "from-plan-012")
        with open_store("scratchpad", "PLAN-011") as a:
            self.assertEqual(a.get("shared-key"), b"from-plan-011")

    def test_two_stores_same_plan_do_not_leak(self):
        with open_store("scratchpad", "PLAN-011") as a:
            a.set("k", "scratch-val")
        with open_store("skill_proposals", "PLAN-011") as b:
            self.assertIsNone(b.get("k"))

    # --- audit envelope --------------------------------------------------

    def test_write_event_has_hashed_ids_not_plaintext(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("my-secret-key", "value")
        events = [e for e in self._read_log() if e["action"] == "state_store_write"]
        self.assertEqual(len(events), 1)
        evt = events[0]
        # plaintext plan_id and key MUST NOT appear
        self.assertNotIn("PLAN-011", json.dumps(evt))
        self.assertNotIn("my-secret-key", json.dumps(evt))
        # hashes are 16-char sha256 prefixes
        self.assertEqual(len(evt["plan_id_hash"]), 16)
        self.assertEqual(len(evt["key_hash"]), 16)

    def test_read_event_records_hit_and_miss(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("present", "v")
            s.get("present")
            s.get("absent")
        events = [e for e in self._read_log() if e["action"] == "state_store_read"]
        self.assertEqual(len(events), 2)
        # Order is write + read_present_hit + read_absent_miss
        self.assertTrue(events[0]["found"])
        self.assertFalse(events[1]["found"])

    def test_write_event_records_value_bytes_and_ttl(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("sized", "1234567890", ttl_seconds=60)
        events = [e for e in self._read_log() if e["action"] == "state_store_write"]
        self.assertEqual(events[0]["value_bytes"], 10)
        self.assertEqual(events[0]["ttl_seconds"], 60)

    # --- filesystem layout ----------------------------------------------

    def test_sqlite_file_created_in_store_plan_path(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("k", "v")
        expected = Path(os.environ["CEO_STATE_ROOT"]) / "scratchpad" / "PLAN-011.sqlite"
        self.assertTrue(expected.is_file())

    def test_sqlite_file_permissions_owner_only(self):
        with open_store("scratchpad", "PLAN-011") as s:
            s.set("k", "v")
        db = Path(os.environ["CEO_STATE_ROOT"]) / "scratchpad" / "PLAN-011.sqlite"
        mode = os.stat(db).st_mode & 0o777
        self.assertEqual(mode, 0o600)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
