"""PLAN-116 (S172) — tier_policy_loader_fallback_observed audit action.

Discharges the PLAN-116 acceptance criteria:

* AC1 / AC3 — closed-enum ``reason_code`` (deny-by-default), every emitted
  kwarg is a subset of the allowlist, an out-of-enum ``reason_code`` drops the
  whole event (mirrors ``persona_coverage_synthesized``).
* AC2 / AC5 — ``loader._fallback`` emits the dedicated action with a bounded
  ``reason_code`` (NOT the old ``tier_policy_misrouting_advised`` piggyback that
  dropped a free-text ``reason`` field on every emit). The ``stat: <errno>``
  call-site is normalized to ``stat_error``. This closes the
  ``['reason']``-dropped noise class.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from _lib import audit_emit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


# The 14 closed reason_code slugs derived from the live loader._fallback
# call-sites (loader.py:307,338-434; `stat: <errno>` normalized to stat_error).
_EXPECTED_SLUGS = {
    "advisory_safety_net", "bad_mode", "depth_limit", "key_count", "missing",
    "not_object", "open_failed", "oversize", "parse_error", "read_failed",
    "schema_mismatch", "stat_error", "type_mismatch", "unknown_model",
}


class _Base(TestEnvContext):
    def _read_events(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        events = []
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def _emit_and_read(self, action, **kwargs):
        audit_emit.emit_generic(action, **kwargs)
        return self._read_events()


class TestReasonCodeEnum(_Base):
    def test_all_14_callsite_slugs_accepted(self) -> None:
        # Append-only log: assert each emit adds exactly ONE event (delta) and
        # the newest event carries the slug — never truncate (would break the
        # HMAC chain) nor read cumulatively (off-by-N).
        prev = 0
        for slug in sorted(_EXPECTED_SLUGS):
            audit_emit.emit_generic(
                "tier_policy_loader_fallback_observed", reason_code=slug
            )
            events = self._read_events()
            self.assertEqual(
                len(events), prev + 1, f"{slug}: expected exactly +1 event"
            )
            self.assertEqual(events[-1]["reason_code"], slug)
            self.assertEqual(
                events[-1]["action"], "tier_policy_loader_fallback_observed"
            )
            prev = len(events)

    def test_out_of_enum_reason_code_dropped(self) -> None:
        events = self._emit_and_read(
            "tier_policy_loader_fallback_observed",
            reason_code="totally-bogus-not-in-enum",
        )
        self.assertEqual(
            events, [], "out-of-enum reason_code must drop the whole event"
        )

    def test_emitted_kwargs_subset_of_allowlist(self) -> None:
        events = self._emit_and_read(
            "tier_policy_loader_fallback_observed",
            reason_code="parse_error",
            _ghost_secret="LEAK-should-never-persist",  # forbidden → scrubbed
            reason="free-text-should-not-survive",       # the old leak field
        )
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertNotIn("_ghost_secret", ev)
        self.assertNotIn("reason", ev)
        allow = set(audit_emit._TIER_POLICY_LOADER_FALLBACK_OBSERVED_ALLOWLIST)
        for key in ev:
            self.assertIn(
                key, allow,
                f"emitted field {key!r} not in allowlist {sorted(allow)}",
            )

    def test_enum_matches_expected_callsite_slugs(self) -> None:
        # Drift detector: the audit_emit closed enum must equal the set of slugs
        # the loader's _fallback call-sites pass.
        self.assertEqual(
            set(audit_emit._TIER_POLICY_LOADER_FALLBACK_REASON_CODES),
            _EXPECTED_SLUGS,
        )


class TestTypedEmitter(_Base):
    def test_typed_emitter_writes_clean_event(self) -> None:
        audit_emit.emit_tier_policy_loader_fallback_observed(
            reason_code="unknown_model", session_id="s", project="p"
        )
        events = self._read_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reason_code"], "unknown_model")
        self.assertEqual(
            events[0]["action"], "tier_policy_loader_fallback_observed"
        )

    def test_typed_emitter_drops_out_of_enum(self) -> None:
        audit_emit.emit_tier_policy_loader_fallback_observed(reason_code="nope")
        self.assertEqual(self._read_events(), [])


class TestLoaderIntegration(_Base):
    """AC2 / AC5 — the loader emits the new action, not the old piggyback."""

    def test_loader_fallback_emits_new_action_not_misrouting(self) -> None:
        from _lib.tier_policy import loader

        loader._fallback("parse_error")
        events = self._read_events()
        actions = [e["action"] for e in events]
        self.assertIn("tier_policy_loader_fallback_observed", actions)
        self.assertNotIn(
            "tier_policy_misrouting_advised", actions,
            "loader must no longer piggyback the misrouting action",
        )
        ev = next(
            e for e in events
            if e["action"] == "tier_policy_loader_fallback_observed"
        )
        self.assertEqual(ev["reason_code"], "parse_error")

    def test_loader_stat_errno_normalized_to_stat_error(self) -> None:
        from _lib.tier_policy import loader

        loader._fallback("stat: 2")
        events = self._read_events()
        ev = next(
            e for e in events
            if e["action"] == "tier_policy_loader_fallback_observed"
        )
        self.assertEqual(ev["reason_code"], "stat_error")

    def test_loader_unknown_slug_drops_event_not_misrouting(self) -> None:
        # An unexpected (future) slug must NOT silently fall back to the old
        # noisy action — it drops via the closed-enum deny-by-default.
        from _lib.tier_policy import loader

        loader._fallback("some_future_unlisted_reason")
        actions = [e["action"] for e in self._read_events()]
        self.assertNotIn("tier_policy_misrouting_advised", actions)
        self.assertNotIn("tier_policy_loader_fallback_observed", actions)


if __name__ == "__main__":
    unittest.main()
