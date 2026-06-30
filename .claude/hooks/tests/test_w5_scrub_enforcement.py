"""PLAN-135-FOLLOWUP (Codex R5 P1-2) — W5 ops actions scrub-branch enforcement.

The three W5 ops actions (admin_key_lifecycle_event / statusline_sidecar_write /
model_refusal_observed) moved OFF ``_EMIT_GENERIC_PASSTHROUGH`` into dedicated
deny-by-default ``_scrub_*`` branches in ``emit_generic``. For EACH action these
tests assert:
  (1) a smuggled non-allowlisted field (``secret=...``) is DROPPED;
  (2) a full legit producer-field emit keeps EVERY declared field (no forensic
      regression — a scrub that silently drops a real field would blind the
      breadcrumb);
  (3) a minimal-subset producer emit (the per-call-site shape) keeps its fields;
  (4) a bad enum/int VALUE is coerced to the safe sentinel (not just key-drop —
      the value-coercion path is the one most likely to regress silently).

COUPLING: imports the canonical ``_lib.audit_emit``, which carries the P1-2 scrub
branches only AFTER the PLAN-135-FOLLOWUP ceremony applies the staged tree. The
test is collected only from the applied / sandbox tree (pytest ``testpaths``
exclude the staged source), so it always runs against the materialized code.

Env hygiene: every emitting class derives from ``TestEnvContext`` (isolated
``$HOME`` + audit log); the test only READS ``CEO_AUDIT_LOG_PATH`` (set by the
context), never writes ``os.environ`` directly.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class _W5Base(TestEnvContext):
    """Isolated audit dir + a per-action single-event reader."""

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

    def _one(self, action: str) -> Dict[str, Any]:
        evs = [e for e in self._events() if e.get("action") == action]
        self.assertEqual(
            len(evs), 1, "expected exactly 1 %s event, got %d: %r" % (action, len(evs), evs)
        )
        return evs[0]


class TestW5OffPassthrough(TestEnvContext):
    """The 3 actions are branched, NOT passthrough, and the count is unchanged."""

    def test_moved_off_passthrough_and_still_known(self):
        for a in (
            "admin_key_lifecycle_event",
            "statusline_sidecar_write",
            "model_refusal_observed",
        ):
            self.assertNotIn(
                a, audit_emit._EMIT_GENERIC_PASSTHROUGH,
                "%s must NOT be in _EMIT_GENERIC_PASSTHROUGH after P1-2" % a,
            )
            self.assertIn(a, audit_emit._KNOWN_ACTIONS)

    def test_known_actions_count_unchanged(self):
        # Move, not add — the count is still 302.
        self.assertEqual(len(audit_emit._KNOWN_ACTIONS), 302)


class TestAdminKeyScrub(_W5Base):
    ACTION = "admin_key_lifecycle_event"

    def test_drops_smuggled_secret(self):
        audit_emit.emit_generic(
            self.ACTION, operation="deactivate", key_id="apikey_abc",
            reason="compromise", rotation_log_appended=True, secret="leak-me",
        )
        e = self._one(self.ACTION)
        self.assertNotIn("secret", e)
        self.assertEqual(e["operation"], "deactivate")
        self.assertEqual(e["key_id"], "apikey_abc")
        self.assertEqual(e["reason"], "compromise")

    def test_full_mutation_fields_survive(self):
        audit_emit.emit_generic(
            self.ACTION, operation="incident", key_count=4,
            reason="suspicion", rotation_log_appended=True,
        )
        e = self._one(self.ACTION)
        self.assertEqual(e["operation"], "incident")
        self.assertEqual(e["key_count"], 4)
        self.assertEqual(e["reason"], "suspicion")
        # SPEC declares this a BOOL (Codex R5-R1 P1) — real bool, not 0/1.
        self.assertIs(e["rotation_log_appended"], True)

    def test_minimal_list_subset_survives(self):
        # key-hygiene 'list' call site sends only operation + key_count.
        audit_emit.emit_generic(self.ACTION, operation="list", key_count=7)
        e = self._one(self.ACTION)
        self.assertEqual(e["operation"], "list")
        self.assertEqual(e["key_count"], 7)

    def test_bad_operation_and_reason_coerced(self):
        audit_emit.emit_generic(self.ACTION, operation="EVIL", reason="../etc/passwd")
        e = self._one(self.ACTION)
        self.assertEqual(e["operation"], "other")
        self.assertEqual(e["reason"], "other")

    def test_key_count_non_int_coerced(self):
        audit_emit.emit_generic(self.ACTION, operation="list", key_count="not-a-number")
        e = self._one(self.ACTION)
        self.assertEqual(e["key_count"], 0)


class TestStatuslineSidecarScrub(_W5Base):
    ACTION = "statusline_sidecar_write"

    def test_drops_secret_keeps_bps_fields(self):
        # PLAN-135-FOLLOWUP-2: pct fields are integer basis-points, never float.
        # The scrub is contracted to receive basis-points (producer owns *100).
        audit_emit.emit_generic(
            self.ACTION, sidecar_path="/tmp/state/x.json", plan_id="PLAN-135",
            context_pct_bps=800, bucket_count=2, buckets_used_pct_max_bps=4120,
            digest="abc123def456", secret="leak",
        )
        e = self._one(self.ACTION)
        self.assertNotIn("secret", e)
        # the old float field names are gone (allowlist deny-by-default drops them)
        self.assertNotIn("context_pct", e)
        self.assertNotIn("buckets_used_pct_max", e)
        self.assertEqual(e["plan_id"], "PLAN-135")
        # both renamed fields SURVIVE the scrub (atomic allowlist+scrub rename)
        self.assertEqual(e["context_pct_bps"], 800)
        self.assertIsInstance(e["context_pct_bps"], int)
        self.assertNotIsInstance(e["context_pct_bps"], bool)  # S233 bool-is-int trap
        self.assertEqual(e["bucket_count"], 2)
        self.assertEqual(e["buckets_used_pct_max_bps"], 4120)
        self.assertIsInstance(e["buckets_used_pct_max_bps"], int)
        self.assertNotIsInstance(e["buckets_used_pct_max_bps"], bool)
        self.assertEqual(e["digest"], "abc123def456")

    def test_sidecar_path_length_capped(self):
        audit_emit.emit_generic(self.ACTION, sidecar_path="/" + ("a" * 2000))
        e = self._one(self.ACTION)
        self.assertLessEqual(len(e["sidecar_path"]), 512)

    def test_context_pct_bps_clamped_to_10000(self):
        # context_pct is 0..100% -> 0..10000 bps; over-range clamps to 10000
        audit_emit.emit_generic(self.ACTION, context_pct_bps=99999)
        self.assertEqual(self._one(self.ACTION)["context_pct_bps"], 10000)

    def test_buckets_bps_not_floored_at_100pct(self):
        # buckets used_pct is capped at 999% upstream -> 0..99900 bps; an
        # over-quota burst (250% = 25000 bps) MUST survive, not floor to 10000.
        audit_emit.emit_generic(self.ACTION, buckets_used_pct_max_bps=25000)
        self.assertEqual(self._one(self.ACTION)["buckets_used_pct_max_bps"], 25000)

    def test_buckets_bps_clamped_to_99900(self):
        audit_emit.emit_generic(self.ACTION, buckets_used_pct_max_bps=10 ** 9)
        self.assertEqual(self._one(self.ACTION)["buckets_used_pct_max_bps"], 99900)

    def test_negative_bps_clamped_to_zero(self):
        audit_emit.emit_generic(
            self.ACTION, context_pct_bps=-5, buckets_used_pct_max_bps=-1,
        )
        e = self._one(self.ACTION)
        self.assertEqual(e["context_pct_bps"], 0)
        self.assertEqual(e["buckets_used_pct_max_bps"], 0)

    def test_inf_and_nan_coerce_to_none_not_raise(self):
        # security MF-1: int(round(float('inf'))) raises OverflowError, which is
        # NOT a ValueError — the scrub must catch it so a direct caller cannot
        # crash the emit or smuggle a non-finite into the chain.
        audit_emit.emit_generic(
            self.ACTION, context_pct_bps=float("inf"),
            buckets_used_pct_max_bps=float("nan"),
        )
        e = self._one(self.ACTION)
        self.assertIsNone(e["context_pct_bps"])
        self.assertIsNone(e["buckets_used_pct_max_bps"])

    def test_bad_numeric_values_coerced(self):
        audit_emit.emit_generic(
            self.ACTION, context_pct_bps="evil", buckets_used_pct_max_bps="x",
            bucket_count="NaN",
        )
        e = self._one(self.ACTION)
        self.assertIsNone(e["context_pct_bps"])
        self.assertIsNone(e["buckets_used_pct_max_bps"])
        self.assertEqual(e["bucket_count"], 0)


class TestW5EventsCanonicalEncodable(_W5Base):
    """PLAN-135-FOLLOWUP-2 (S234) regression — the coverage that was MISSING.

    Every W5 scrub-branch action must produce an event the HMAC canonical encoder
    ACCEPTS (no float / NaN / Inf). The float `context_pct` was written with
    hmac=null on every emit since v2.44 precisely because NO test ever carried an
    emitted event through ``canonical_json.encode`` — the scrub-only tests inspect
    the output dict and never cross the encoder the spool_writer uses to sign the
    chain. This class closes that gap for the whole bug-class: it re-reads the
    WRITTEN event and runs it through the real encoder (a json round-trip
    preserves int-vs-float, so a float field would still raise here)."""

    def _assert_in_signed_chain(self, action: str) -> None:
        from _lib import canonical_json

        e = self._one(action)
        # hard gate: the written event must be canonical-encodable (a float field
        # would raise CanonicalJsonError here — exactly what hid the born bug).
        try:
            canonical_json.encode(e)
        except canonical_json.CanonicalJsonError as exc:  # pragma: no cover
            self.fail("%s event is NOT HMAC-encodable: %s" % (action, exc))
        # positive-chain: the float bug set hmac_error (fail-open); the fix must not
        self.assertFalse(
            e.get("hmac_error"),
            "%s landed in the .errors path: %r" % (action, e.get("hmac_error")),
        )

    def test_statusline_event_is_canonical_encodable(self):
        audit_emit.emit_generic(
            "statusline_sidecar_write", sidecar_path="/tmp/x.json",
            plan_id="PLAN-135", context_pct_bps=8634, bucket_count=2,
            buckets_used_pct_max_bps=4120, digest="abc123def456",
        )
        self._assert_in_signed_chain("statusline_sidecar_write")

    def test_admin_key_event_is_canonical_encodable(self):
        audit_emit.emit_generic(
            "admin_key_lifecycle_event", operation="rotate", reason="scheduled",
            key_id="k1", key_count=3, rotation_log_appended=True,
        )
        self._assert_in_signed_chain("admin_key_lifecycle_event")

    def test_model_refusal_event_is_canonical_encodable(self):
        audit_emit.emit_generic(
            "model_refusal_observed", provider="anthropic",
            model="claude-opus-4-8", stop_reason="refusal", stop_category="bio",
            http_status=200, duration_ms=12,
        )
        self._assert_in_signed_chain("model_refusal_observed")


class TestW5NumericOverflowSafe(_W5Base):
    """Codex R1 P1 (S234): EVERY int-coerced numeric field on a W5 scrub branch
    must catch OverflowError — int(float('inf')) raises it and it is NOT a
    ValueError, so a direct emit_generic caller could otherwise make the boundary
    raise before _write_event. emit_generic is contracted to never raise."""

    def test_statusline_bucket_count_inf_coerces_to_zero(self):
        audit_emit.emit_generic("statusline_sidecar_write", bucket_count=float("inf"))
        self.assertEqual(self._one("statusline_sidecar_write")["bucket_count"], 0)

    def test_admin_key_count_inf_coerces_to_zero(self):
        audit_emit.emit_generic(
            "admin_key_lifecycle_event", operation="rotate", reason="scheduled",
            key_count=float("inf"),
        )
        self.assertEqual(self._one("admin_key_lifecycle_event")["key_count"], 0)

    def test_model_refusal_status_inf_coerces_to_zero(self):
        audit_emit.emit_generic(
            "model_refusal_observed", http_status=float("inf"),
            duration_ms=float("inf"),
        )
        e = self._one("model_refusal_observed")
        self.assertEqual(e["http_status"], 0)
        self.assertEqual(e["duration_ms"], 0)


class TestModelRefusalScrub(_W5Base):
    ACTION = "model_refusal_observed"

    def test_drops_secret_keeps_fields(self):
        audit_emit.emit_generic(
            self.ACTION, provider="anthropic", model="claude-opus-4-8",
            stop_reason="refusal", stop_category="bio", http_status=200,
            duration_ms=1234, secret="x",
        )
        e = self._one(self.ACTION)
        self.assertNotIn("secret", e)
        self.assertEqual(e["provider"], "anthropic")
        self.assertEqual(e["model"], "claude-opus-4-8")
        self.assertEqual(e["stop_category"], "bio")
        self.assertEqual(e["http_status"], 200)
        self.assertEqual(e["duration_ms"], 1234)

    def test_stop_reason_const_coerced(self):
        audit_emit.emit_generic(self.ACTION, stop_reason="not-a-refusal")
        e = self._one(self.ACTION)
        self.assertEqual(e["stop_reason"], "refusal")

    def test_stop_category_nonstr_and_ints_bounded(self):
        audit_emit.emit_generic(
            self.ACTION, stop_reason="refusal", stop_category=12345,
            http_status="bad", duration_ms=-5,
        )
        e = self._one(self.ACTION)
        self.assertEqual(e["stop_category"], "")
        self.assertEqual(e["http_status"], 0)
        self.assertEqual(e["duration_ms"], 0)


class TestSwarmPausedScrub(_W5Base):
    """PLAN-136 W3 (S3) — defense-in-depth int coercion of the bucketed
    ``loop_duration_hours`` field on the ``swarm_paused_owner_absent`` scrub
    branch (same class as PLAN-135-FOLLOWUP-2 / S234 — the HMAC canonical encoder
    rejects float, S181). The live producer emits an int >=1h bucket, so the
    live path is safe; these tests pin the boundary against a DIRECT caller that
    smuggles a non-int / float / non-finite value, and the floor sentinel."""

    ACTION = "swarm_paused_owner_absent"

    def test_drops_smuggled_secret_keeps_fields(self):
        audit_emit.emit_generic(
            self.ACTION, loop_duration_hours=6, last_owner_read_iso="2026-06-15T00:00:00Z",
            swarm_pid=4242, secret="leak-me",
        )
        e = self._one(self.ACTION)
        self.assertNotIn("secret", e)
        self.assertEqual(e["last_owner_read_iso"], "2026-06-15T00:00:00Z")
        self.assertEqual(e["swarm_pid"], 4242)
        # the legit int bucket survives unchanged AND is a real int, never a bool
        # (S233 bool-is-int trap: assertIsInstance(True, int) is True).
        self.assertEqual(e["loop_duration_hours"], 6)
        self.assertIsInstance(e["loop_duration_hours"], int)
        self.assertNotIsInstance(e["loop_duration_hours"], bool)

    def test_float_loop_duration_coerced_to_int(self):
        # a direct caller passing a float MUST be int-coerced (round) so the
        # HMAC canonical encoder never sees a float (the S234 born-bug class).
        audit_emit.emit_generic(self.ACTION, loop_duration_hours=7.8)
        e = self._one(self.ACTION)
        self.assertEqual(e["loop_duration_hours"], 8)
        self.assertIsInstance(e["loop_duration_hours"], int)
        self.assertNotIsInstance(e["loop_duration_hours"], bool)

    def test_sub_floor_and_negative_collapse_to_one(self):
        # the producer floor is >=1h; a 0 / negative value collapses to the
        # smallest legit bucket (1), never 0.
        audit_emit.emit_generic(self.ACTION, loop_duration_hours=0)
        self.assertEqual(self._one(self.ACTION)["loop_duration_hours"], 1)

    def test_large_value_clamped(self):
        audit_emit.emit_generic(self.ACTION, loop_duration_hours=10 ** 9)
        self.assertEqual(self._one(self.ACTION)["loop_duration_hours"], 100000)

    def test_bad_value_coerced_to_floor_sentinel(self):
        audit_emit.emit_generic(self.ACTION, loop_duration_hours="not-a-number")
        self.assertEqual(self._one(self.ACTION)["loop_duration_hours"], 1)

    def test_inf_coerces_to_floor_not_raise(self):
        # int(round(float('inf'))) raises OverflowError (NOT a ValueError) — the
        # boundary must catch it so emit_generic never raises and no non-finite
        # value reaches the signed chain.
        audit_emit.emit_generic(self.ACTION, loop_duration_hours=float("inf"))
        self.assertEqual(self._one(self.ACTION)["loop_duration_hours"], 1)


if __name__ == "__main__":
    unittest.main()
