"""PLAN-125 WS-1 (kooky-harvest) — per-tool-call lifecycle telemetry tests.

Covers the falsifiable WIN gate (§4 / §9 MF-QA-A..F):

* exact Pre/Post pairing on the golden fixture (Bash);
* two concurrent DISTINCT tools, interleaved (pairing by tool_use_id, not order);
* orphan via an INJECTED clock (MF-QA-B — never time.sleep);
* missing-Pre → duration absent (no crash, bucket floor);
* PostToolUseFailure → success=false;
* Sec-MF-3 deny-field-absent AND no raw "mcp__" string on any emitted row (MF-QA-D);
* fail-open (a chain-write/emit failure does not raise);
* ghost-action guard classifies tool_call_lifecycle_recorded as scrub-branch (MF-SEC-2).

All audit-chain-touching tests isolate via ``TestEnvContext`` (pins
``CEO_AUDIT_LOG_DIR`` → a per-test temp dir). NEVER touches the real audit log.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import ast
import inspect
import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from _lib import audit_emit  # noqa: E402
from _lib import tool_lifecycle  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "lifecycle"


# ---------------------------------------------------------------------------
# Minimal NormalizedEvent-shaped carriers (record_pre / record_post read
# only these attributes).
# ---------------------------------------------------------------------------


class _PreEvent:
    def __init__(self, *, session_id: str, tool_use_id: str, tool_name: str) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name


class _PostEvent:
    def __init__(
        self, *, session_id: str, tool_use_id: str, tool_name: str,
        duration_ms: Optional[int],
    ) -> None:
        self.session_id = session_id
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.duration_ms = duration_ms


def _pre_from_payload(p: Dict[str, Any]) -> _PreEvent:
    return _PreEvent(
        session_id=str(p.get("session_id") or ""),
        tool_use_id=str(p.get("tool_use_id") or ""),
        tool_name=str(p.get("tool_name") or ""),
    )


def _post_from_payload(p: Dict[str, Any]) -> _PostEvent:
    dur = p.get("duration_ms")
    return _PostEvent(
        session_id=str(p.get("session_id") or ""),
        tool_use_id=str(p.get("tool_use_id") or ""),
        tool_name=str(p.get("tool_name") or ""),
        duration_ms=dur if isinstance(dur, int) else None,
    )


def _load_fixture(name: str) -> Dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Base — isolated audit log + reader
# ---------------------------------------------------------------------------


class _LifecycleBase(TestEnvContext):
    def _read_events(self) -> List[Dict[str, Any]]:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        out: List[Dict[str, Any]] = []
        if log.exists():
            for line in log.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def _lifecycle_rows(self) -> List[Dict[str, Any]]:
        return [
            e for e in self._read_events()
            if e.get("action") == "tool_call_lifecycle_recorded"
        ]

    def _raw_log_text(self) -> str:
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        return log.read_text(encoding="utf-8") if log.exists() else ""

    def _audit_dir(self) -> Path:
        return Path(os.environ["CEO_AUDIT_LOG_DIR"])


# ---------------------------------------------------------------------------
# 1. Exact pairing on the golden Bash fixture
# ---------------------------------------------------------------------------


class TestExactPairing(_LifecycleBase):
    def test_paired_bash_pre_post_golden_fixture(self):
        pre = _load_fixture("paired_bash_pre.json")
        post = _load_fixture("paired_bash_post.json")
        # Same tool_use_id across Pre + Post (the pairing key).
        self.assertEqual(pre["tool_use_id"], post["tool_use_id"])

        tool_lifecycle.record_pre(_pre_from_payload(pre))
        tool_lifecycle.record_post(_post_from_payload(post), failure=False)

        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1, f"expected 1 lifecycle row, got {rows!r}")
        ev = rows[0]
        self.assertEqual(ev["tool_name_enum"], "Bash")
        # 2500ms → b_1_10s
        self.assertEqual(ev["duration_bucket"], "b_1_10s")
        self.assertIs(ev["success"], True)
        self.assertIs(ev["orphan"], False)

    def test_post_evicts_record_no_double_emit_on_sweep(self):
        pre = _load_fixture("paired_bash_pre.json")
        post = _load_fixture("paired_bash_post.json")
        tool_lifecycle.record_pre(_pre_from_payload(pre))
        tool_lifecycle.record_post(_post_from_payload(post), failure=False)
        # A subsequent sweep must find nothing (record was evicted on Post).
        n = tool_lifecycle.sweep_orphans(
            pre["session_id"], now_fn=lambda: 10 ** 9, timeout_s=30
        )
        self.assertEqual(n, 0)
        self.assertEqual(len(self._lifecycle_rows()), 1)


# ---------------------------------------------------------------------------
# 2. Concurrent distinct tools, interleaved (pairing by id, not order)
# ---------------------------------------------------------------------------


class TestConcurrentDistinctTools(_LifecycleBase):
    def test_interleaved_two_tools_pair_by_id(self):
        seq = _load_fixture("concurrent_interleaved.json")["sequence"]
        for p in seq:
            phase = p.get("hook_event_name")
            if phase == "PreToolUse":
                tool_lifecycle.record_pre(_pre_from_payload(p))
            elif phase == "PostToolUse":
                tool_lifecycle.record_post(_post_from_payload(p), failure=False)

        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 2, f"expected 2 rows, got {rows!r}")
        by_tool = {r["tool_name_enum"]: r for r in rows}
        # Read finished at 40ms → lt_100ms; Bash finished at 5200ms → b_1_10s.
        self.assertIn("Read", by_tool)
        self.assertIn("Bash", by_tool)
        self.assertEqual(by_tool["Read"]["duration_bucket"], "lt_100ms")
        self.assertEqual(by_tool["Bash"]["duration_bucket"], "b_1_10s")
        for r in rows:
            self.assertIs(r["success"], True)
            self.assertIs(r["orphan"], False)


# ---------------------------------------------------------------------------
# 3. Orphan via INJECTED clock (MF-QA-B — never time.sleep)
# ---------------------------------------------------------------------------


class TestOrphanSweep(_LifecycleBase):
    def test_orphan_fires_after_timeout_via_injected_clock(self):
        pre = _load_fixture("orphaned_pre.json")
        sid = pre["session_id"]
        # Stamp the Pre at t=1000.0 (injected).
        tool_lifecycle.record_pre(_pre_from_payload(pre), now_fn=lambda: 1000.0)
        # No Post ever arrives. Sweep at t=1000+31 (> T=30s) → orphan.
        n = tool_lifecycle.sweep_orphans(sid, now_fn=lambda: 1031.0, timeout_s=30)
        self.assertEqual(n, 1)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        self.assertEqual(ev["tool_name_enum"], "WebFetch")
        self.assertIs(ev["orphan"], True)
        self.assertIs(ev["success"], False)
        # No raw duration — orphan never knew when it finished → bucket floor.
        self.assertEqual(ev["duration_bucket"], "lt_100ms")

    def test_not_orphan_before_timeout(self):
        pre = _load_fixture("orphaned_pre.json")
        sid = pre["session_id"]
        tool_lifecycle.record_pre(_pre_from_payload(pre), now_fn=lambda: 1000.0)
        # Sweep at t=1000+10 (< T=30s) → still in-flight, no orphan.
        n = tool_lifecycle.sweep_orphans(sid, now_fn=lambda: 1010.0, timeout_s=30)
        self.assertEqual(n, 0)
        self.assertEqual(len(self._lifecycle_rows()), 0)

    def test_sessionend_clear_prevents_false_orphan(self):
        pre = _load_fixture("orphaned_pre.json")
        sid = pre["session_id"]
        tool_lifecycle.record_pre(_pre_from_payload(pre), now_fn=lambda: 1000.0)
        # SessionEnd deletes the record file BEFORE the sweeper would fire.
        tool_lifecycle.cleanup_session(sid)
        n = tool_lifecycle.sweep_orphans(sid, now_fn=lambda: 9999.0, timeout_s=30)
        self.assertEqual(n, 0)
        self.assertEqual(len(self._lifecycle_rows()), 0)

    def test_record_missing_t_start_is_never_orphaned(self):
        # Coverage gap (qa review): a record with no / non-numeric t_start_s
        # yields age=None → the conservative branch keeps it as a survivor and
        # never wrongly orphans it. Use timeout_s=0.0 so the only thing keeping
        # it from being orphaned is the age=None guard.
        sid = "sess-no-tstart"
        path = tool_lifecycle._record_path(sid, self._audit_dir())
        tool_lifecycle._save_records(path, {"u-bad": {"tool_name": "Bash"}})
        n = tool_lifecycle.sweep_orphans(
            sid, audit_dir=self._audit_dir(), now_fn=lambda: 9999.0, timeout_s=0.0
        )
        self.assertEqual(n, 0)
        self.assertEqual(len(self._lifecycle_rows()), 0)


# ---------------------------------------------------------------------------
# 4. Missing-Pre → duration absent (no crash)
# ---------------------------------------------------------------------------


class TestMissingPre(_LifecycleBase):
    def test_post_without_pre_does_not_crash_and_uses_post_tool_name(self):
        # No record_pre call at all — Post arrives orphaned-of-its-Pre.
        post = _PostEvent(
            session_id="sess-nopre", tool_use_id="toolu_nopre",
            tool_name="Edit", duration_ms=120,
        )
        # Must not raise.
        tool_lifecycle.record_post(post, failure=False)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        # Tool name falls back to the Post event's tool name.
        self.assertEqual(ev["tool_name_enum"], "Edit")
        # 120ms → b_100ms_1s (native duration still present on the Post).
        self.assertEqual(ev["duration_bucket"], "b_100ms_1s")

    def test_post_without_pre_and_no_duration_uses_floor_bucket(self):
        post = _PostEvent(
            session_id="sess-nopre2", tool_use_id="toolu_nopre2",
            tool_name="Read", duration_ms=None,
        )
        tool_lifecycle.record_post(post, failure=False)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["duration_bucket"], "lt_100ms")


# ---------------------------------------------------------------------------
# 5. PostToolUseFailure → success=false
# ---------------------------------------------------------------------------


class TestFailurePhase(_LifecycleBase):
    def test_failure_sets_success_false(self):
        pre = _PreEvent(session_id="sess-fail", tool_use_id="u1", tool_name="Bash")
        post = _PostEvent(
            session_id="sess-fail", tool_use_id="u1",
            tool_name="Bash", duration_ms=300,
        )
        tool_lifecycle.record_pre(pre)
        tool_lifecycle.record_post(post, failure=True)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["success"], False)
        self.assertIs(rows[0]["orphan"], False)


# ---------------------------------------------------------------------------
# 6. Sec-MF-3 — deny-field-absent AND no raw mcp__ string (MF-QA-D)
# ---------------------------------------------------------------------------


class TestDenyByDefault(_LifecycleBase):
    def test_mcp_tool_collapses_to_mcp_other_no_raw_string(self):
        pre = _PreEvent(
            session_id="sess-mcp", tool_use_id="m1",
            tool_name="mcp__codex__codex",
        )
        post = _PostEvent(
            session_id="sess-mcp", tool_use_id="m1",
            tool_name="mcp__codex__codex", duration_ms=70,
        )
        tool_lifecycle.record_pre(pre)
        tool_lifecycle.record_post(post, failure=False)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tool_name_enum"], "mcp_other")
        # MF-SEC-1: no raw mcp__ string anywhere in the emitted log.
        self.assertNotIn("mcp__", self._raw_log_text())

    def test_unknown_tool_collapses_to_other(self):
        post = _PostEvent(
            session_id="sess-unk", tool_use_id="x1",
            tool_name="SomeFutureTool", duration_ms=10,
        )
        tool_lifecycle.record_post(post, failure=False)
        rows = self._lifecycle_rows()
        self.assertEqual(rows[0]["tool_name_enum"], "other")

    def test_raw_duration_ms_never_on_wire(self):
        post = _PostEvent(
            session_id="sess-dur", tool_use_id="d1",
            tool_name="Bash", duration_ms=4242,
        )
        tool_lifecycle.record_post(post, failure=False)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        # The raw integer must NOT appear as a field.
        self.assertNotIn("duration_ms", ev)
        # And the raw value 4242 must not appear in any SEMANTIC field. The
        # hmac hex digest is excluded: a hash can coincidentally contain any
        # digit run (this assertion flaked in CI when the hmac contained
        # "4242") — the guarantee is about semantic fields, not the digest.
        ev_semantic = {k: v for k, v in ev.items() if k not in ("hmac", "hmac_error")}
        self.assertNotIn("4242", json.dumps(ev_semantic))
        self.assertEqual(ev["duration_bucket"], "b_1_10s")

    def test_typed_emitter_drops_forbidden_smuggled_fields(self):
        # A direct emit_generic call attempting to smuggle forbidden fields:
        # the scrub branch must drop them; only the 4 closed fields survive.
        audit_emit.emit_generic(
            "tool_call_lifecycle_recorded",
            session_id="sess-smuggle",
            tool_name_enum="Bash",
            duration_bucket="b_1_10s",
            success=True,
            orphan=False,
            # forbidden smuggled fields:
            raw_tool_name="mcp__evil__exfil",
            duration_ms=99999,
            command="rm -rf /",
            secret_path="/home/me/.ssh/id_rsa",
        )
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        for forbidden in ("raw_tool_name", "duration_ms", "command", "secret_path"):
            self.assertNotIn(forbidden, ev)
        self.assertNotIn("mcp__", self._raw_log_text())
        self.assertNotIn("rm -rf", self._raw_log_text())

    def test_direct_emitter_coerces_smuggled_raw_mcp_tool_name(self):
        # Even a direct typed-emitter call that bypassed the mapper must NOT
        # let a raw mcp__ string reach the wire (defense-in-depth coercion).
        audit_emit.emit_tool_call_lifecycle_recorded(
            session_id="sess-coerce",
            tool_name_enum="mcp__attacker__tool",
            duration_bucket="b_1_10s",
            success=True,
            orphan=False,
        )
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tool_name_enum"], "other")
        self.assertNotIn("mcp__", self._raw_log_text())

    def test_emit_generic_coerces_smuggled_values_in_allowed_fields(self):
        # Regression for the security-review BLOCK: a DIRECT emit_generic call
        # (bypassing the typed emitter) puts the smuggled value in the ALLOWED
        # tool_name_enum / duration_bucket fields — the field-name scrub keeps
        # those keys, so the emit_generic branch MUST re-coerce the VALUES by
        # closed-set membership, else a raw mcp__* tool name (MCP-server
        # controlled) or a raw duration token enters the signed HMAC chain
        # (MF-SEC-1 / MF-SEC-3). The two pre-existing tests miss this path: one
        # uses the typed emitter, the other smuggles into a DROPPED field.
        audit_emit.emit_generic(
            "tool_call_lifecycle_recorded",
            session_id="sess-generic-smuggle",
            tool_name_enum="mcp__attacker__write_chain",
            duration_bucket="raw_77777_ms",
            success=True,
            orphan=False,
        )
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        self.assertEqual(ev["tool_name_enum"], "other")
        self.assertEqual(ev["duration_bucket"], "lt_100ms")
        self.assertNotIn("mcp__", self._raw_log_text())
        # Smuggled '77777' must not leak into any SEMANTIC field; the hmac
        # hex digest is excluded (a hash can coincidentally contain the run).
        ev_semantic = {k: v for k, v in ev.items() if k not in ("hmac", "hmac_error")}
        self.assertNotIn("77777", json.dumps(ev_semantic))

    def test_emit_generic_coerces_smuggled_success_orphan_to_bool(self):
        # Regression for the Codex pair-rail P0: success / orphan are ALSO in
        # the allowlist, so the emit_generic branch must coerce THEIR values to
        # bool — else a direct caller smuggles a free-form string/dict (signed
        # verbatim into the HMAC chain) or a float (breaks canonical JSON →
        # unsigned hmac_error row).
        audit_emit.emit_generic(
            "tool_call_lifecycle_recorded",
            session_id="sess-bool-smuggle",
            tool_name_enum="Bash",
            duration_bucket="b_1_10s",
            success="evil-free-form-string",
            orphan={"nested": "dict"},
        )
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        ev = rows[0]
        self.assertIsInstance(ev["success"], bool)
        self.assertIsInstance(ev["orphan"], bool)
        self.assertNotIn("evil-free-form-string", self._raw_log_text())
        self.assertNotIn("nested", self._raw_log_text())


# ---------------------------------------------------------------------------
# 7. Fail-open — emit failure does not raise
# ---------------------------------------------------------------------------


class TestFailOpen(_LifecycleBase):
    def test_record_post_swallows_emit_exception(self):
        orig = audit_emit.emit_tool_call_lifecycle_recorded

        def _boom(*a, **k):
            raise RuntimeError("simulated chain-write failure")

        audit_emit.emit_tool_call_lifecycle_recorded = _boom  # type: ignore[assignment]
        try:
            post = _PostEvent(
                session_id="s", tool_use_id="u", tool_name="Bash", duration_ms=10,
            )
            # Must NOT raise (fail-open — never blocks the tool).
            tool_lifecycle.record_post(post, failure=False)
        finally:
            audit_emit.emit_tool_call_lifecycle_recorded = orig  # type: ignore[assignment]

    def test_record_pre_swallows_save_exception(self):
        # Point the audit dir at a path that cannot be created (a file, not a
        # dir) so the per-session save fails; record_pre must not raise AND
        # must not emit any audit-chain event.
        bad_dir = self._audit_dir() / "not-a-dir"
        bad_dir.write_text("x", encoding="utf-8")
        pre = _PreEvent(session_id="s2", tool_use_id="u2", tool_name="Bash")
        # Must not raise.
        tool_lifecycle.record_pre(pre, audit_dir=bad_dir)
        # MF-SEC-5: the Pre stamp emits NO audit-chain event regardless.
        self.assertEqual(len(self._lifecycle_rows()), 0)

    def test_record_pre_emits_no_audit_chain_event(self):
        # Positive case: a successful Pre stamp writes the record file but
        # emits ZERO audit-chain events (MF-SEC-5 hard KILL).
        pre = _PreEvent(session_id="s3", tool_use_id="u3", tool_name="Bash")
        tool_lifecycle.record_pre(pre)
        self.assertEqual(self._read_events(), [])
        # The dedicated per-session record file DOES exist.
        rec = (
            self._audit_dir() / "tool-lifecycle" / "s3.json"
        )
        self.assertTrue(rec.is_file(), "Pre stamp must write the per-session file")

    def test_record_pre_empty_tool_use_id_is_noop(self):
        # Coverage gap (qa review) + MF-SEC-5 boundary: an empty tool_use_id has
        # no pairing key, so record_pre must NOT write a per-session file AND
        # must NOT emit any audit-chain event.
        pre = _PreEvent(session_id="s-empty", tool_use_id="", tool_name="Bash")
        tool_lifecycle.record_pre(pre)
        self.assertEqual(self._read_events(), [])
        rec = self._audit_dir() / "tool-lifecycle" / "s-empty.json"
        self.assertFalse(
            rec.exists(), "empty tool_use_id must not write a record file"
        )


# ---------------------------------------------------------------------------
# 7b. SessionEnd production wiring — orphan sweep is reachable (MF-PERF-3)
# ---------------------------------------------------------------------------


class TestSessionEndOrphanFlush(_LifecycleBase):
    def test_sessionend_flushes_inflight_as_orphan_then_evicts(self):
        # MF-PERF-3 production wiring (perf-review must-fix): SessionEnd must
        # sweep orphans BEFORE deleting the record file, so an in-flight
        # (unpaired) Pre at session end is emitted as orphan=true rather than
        # silently dropped. Without the wiring the affirmative orphan branch is
        # dead in production.
        import SessionEnd  # hook module on sys.path via the _lib import above
        sid = "sess-end-flush"
        tool_lifecycle.record_pre(
            _PreEvent(session_id=sid, tool_use_id="u-end", tool_name="Bash")
        )
        # No Post ever arrives → in-flight at session end.
        SessionEnd._cleanup_tool_lifecycle(sid)
        rows = self._lifecycle_rows()
        self.assertEqual(len(rows), 1)
        self.assertIs(rows[0]["orphan"], True)
        self.assertIs(rows[0]["success"], False)
        # The per-session record file is evicted afterwards.
        rec = self._audit_dir() / "tool-lifecycle" / (sid + ".json")
        self.assertFalse(rec.exists())


# ---------------------------------------------------------------------------
# 8. Ghost-action guard — classified as scrub-branch (MF-SEC-2)
# ---------------------------------------------------------------------------


class TestGhostActionClassification(unittest.TestCase):
    def _branched_actions(self):
        src = inspect.getsource(audit_emit.emit_generic)
        tree = ast.parse(src)
        out = set()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "action"
            ):
                for comp in node.comparators:
                    if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                        out.add(comp.value)
        return out

    def test_action_is_registered_in_known_actions(self):
        self.assertIn(
            "tool_call_lifecycle_recorded", audit_emit._KNOWN_ACTIONS
        )

    def test_action_classified_as_scrub_branch_not_passthrough(self):
        branched = self._branched_actions()
        self.assertIn("tool_call_lifecycle_recorded", branched)
        self.assertNotIn(
            "tool_call_lifecycle_recorded",
            audit_emit._EMIT_GENERIC_PASSTHROUGH,
        )
        self.assertNotIn(
            "tool_call_lifecycle_recorded",
            set(audit_emit._RESERVED_ACTIONS),
        )

    def test_typed_emitter_exists(self):
        self.assertTrue(
            hasattr(audit_emit, "emit_tool_call_lifecycle_recorded")
        )


# ---------------------------------------------------------------------------
# 9. Enum mappers (unit)
# ---------------------------------------------------------------------------


class TestEnumMappers(unittest.TestCase):
    def test_tool_name_enum_mapping(self):
        self.assertEqual(tool_lifecycle.to_tool_name_enum("Bash"), "Bash")
        self.assertEqual(tool_lifecycle.to_tool_name_enum("Agent"), "Agent")
        self.assertEqual(tool_lifecycle.to_tool_name_enum("Task"), "Task")
        self.assertEqual(
            tool_lifecycle.to_tool_name_enum("mcp__codex__codex"), "mcp_other"
        )
        self.assertEqual(tool_lifecycle.to_tool_name_enum("Whatever"), "other")
        self.assertEqual(tool_lifecycle.to_tool_name_enum(""), "other")
        self.assertEqual(tool_lifecycle.to_tool_name_enum(None), "other")
        # The two synthetic buckets are IDEMPOTENT (pass through unchanged) so
        # the enum stored in the per-session record file re-maps cleanly in
        # record_post (Codex pair-rail P2). A raw mcp__* string still collapses
        # to mcp_other above, so no raw tool name ever reaches the wire.
        self.assertEqual(tool_lifecycle.to_tool_name_enum("mcp_other"), "mcp_other")
        self.assertEqual(tool_lifecycle.to_tool_name_enum("other"), "other")

    def test_duration_bucket_mapping(self):
        self.assertEqual(tool_lifecycle.to_duration_bucket(None), "lt_100ms")
        self.assertEqual(tool_lifecycle.to_duration_bucket(0), "lt_100ms")
        self.assertEqual(tool_lifecycle.to_duration_bucket(99), "lt_100ms")
        self.assertEqual(tool_lifecycle.to_duration_bucket(100), "b_100ms_1s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(999), "b_100ms_1s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(1000), "b_1_10s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(9999), "b_1_10s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(10000), "b_10_60s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(59999), "b_10_60s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(60000), "gt_60s")
        self.assertEqual(tool_lifecycle.to_duration_bucket(600000), "gt_60s")
        # Every produced value is in the closed set.
        for v in (None, 0, 100, 1000, 10000, 60000):
            self.assertIn(
                tool_lifecycle.to_duration_bucket(v),
                tool_lifecycle.DURATION_BUCKETS,
            )


if __name__ == "__main__":
    unittest.main()
