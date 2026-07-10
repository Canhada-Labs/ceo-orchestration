"""Tests for distill-lessons.py — PLAN-154 item 2 (hermetic; no live model).

Covers the mandatory A4 fixture pair (planted hostile observation rejected
pre-candidate; benign observation survives to PENDING) plus the fail-CLOSED
posture map: schema reject, scanner unavailable, store unavailable, token
ceiling, cursor semantics, closed-enum read boundary, model pin + override.

The read surface is the OPT-IN observe store
(``<audit_dir>/tool-lifecycle/*.observe.jsonl``), NEVER the always-on
``tool_call_lifecycle_recorded`` audit action — ``TestKillSwitchNegativeControl``
is the certifying negative control for that A12 coupling (Codex S265 P2#4).

Env mutation happens ONLY via ``mock.patch.dict`` (repo test-hygiene gate).
All filesystem inputs are per-test temp dirs — no env-dependent paths are
exercised (``run_distill`` takes ``audit_dir`` explicitly).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_TESTS_DIR = Path(__file__).resolve().parent
_SCRIPTS_DIR = _TESTS_DIR.parent
_FIXTURES = _TESTS_DIR / "fixtures" / "distiller"

# Load distill-lessons.py (hyphenated filename) as a module.
_spec = importlib.util.spec_from_file_location(
    "distill_lessons", _SCRIPTS_DIR / "distill-lessons.py"
)
_distill = importlib.util.module_from_spec(_spec)
sys.modules["distill_lessons"] = _distill
_spec.loader.exec_module(_distill)

# distill-lessons.py inserts .claude/hooks on sys.path at import, so the shared
# TestEnvContext base (env/HOME/CLAUDE_PROJECT_DIR isolation) resolves here.
from _lib.testing import TestEnvContext  # noqa: E402

# Per-session observe-store basename used by the fixtures/tests below.
_STORE_NAME = "s-test.observe.jsonl"


def _load_tool_lifecycle():
    """Return the real observe-rail module, or None if _lib is unavailable.

    ``distill-lessons.py`` already inserts ``.claude/hooks`` on ``sys.path``
    at import, so this resolves in a full worktree; overlay-only runs (partial
    ``_lib``) return None and the rail-coupling tests skip.
    """
    try:
        import _lib.tool_lifecycle as tl  # noqa: WPS433
        return tl
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Local closed-enum surface (contract mirror; pin-sync asserted below)
# ---------------------------------------------------------------------------

_RECOGNIZED = frozenset({
    "Agent", "Task", "TaskCreate", "TaskUpdate", "TaskGet", "TaskList",
    "Bash", "Edit", "MultiEdit", "Write", "Read", "Glob", "Grep",
    "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite",
})
_BUCKETS = ("lt_100ms", "b_100ms_1s", "b_1_10s", "b_10_60s", "gt_60s")


def _to_enum(raw):
    if not isinstance(raw, str) or not raw:
        return "other"
    if raw in ("mcp_other", "other"):
        return raw
    if raw.startswith("mcp__"):
        return "mcp_other"
    return raw if raw in _RECOGNIZED else "other"


_SURFACE = (_to_enum, _BUCKETS)


class _ScanResultStub:
    def __init__(self, matched):
        self.matched = matched
        self.matches = [object()] if matched else []


def _scan_no_hit(_text):
    return _ScanResultStub(False)


def _scan_like_corpus(text):
    """Fallback scanner mirroring the direct_override family (overlay runs)."""
    low = " ".join(text.lower().split())
    return _ScanResultStub("ignore all previous instructions" in low)


def _real_or_fallback_scanner():
    real = _distill._load_scanner()
    return real if real is not None else _scan_like_corpus


class _AddCandidateRecorder:
    """Stub for the wave-0 ``lessons.add_candidate`` contract."""

    def __init__(self, status="PENDING"):
        self.calls = []
        self.status = status

    def __call__(self, *, trigger, advisory_text, scope_tags):
        self.calls.append({
            "trigger": trigger,
            "advisory_text": advisory_text,
            "scope_tags": list(scope_tags),
        })
        return ("cand%03d" % len(self.calls), self.status)


class _DistillBase(TestEnvContext):
    def setUp(self):
        super().setUp()  # env/HOME/CLAUDE_PROJECT_DIR isolation
        self.tmpdir = Path(tempfile.mkdtemp(prefix="distill-test-"))
        # Dedicated distiller audit dir (independent of TestEnvContext's own),
        # always passed explicitly to run_distill/read_new_observations.
        self.audit_dir = self.tmpdir / "audit"
        self.audit_dir.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        super().tearDown()

    def _store_path(self, session="s-test"):
        return self.audit_dir / "tool-lifecycle" / (session + ".observe.jsonl")

    def _seed_store(self, fixture_name, session="s-test"):
        """Copy an observe-store fixture into <audit>/tool-lifecycle/<s>.observe.jsonl."""
        dest = self._store_path(session)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(_FIXTURES / fixture_name, dest)
        return dest

    def _seed_always_on_audit_log(
        self, fixture_name="killswitch_always_on_audit_log.jsonl"
    ):
        """Seed the ALWAYS-ON audit log (the trap for the kill-switch control).

        These ``tool_call_lifecycle_recorded`` rows fire regardless of the
        opt-in. A correct distiller (reads the observe store) must NEVER read
        them; a regressed one (reads the audit action) would mint candidates.
        """
        shutil.copy(_FIXTURES / fixture_name, self.audit_dir / "audit-log.jsonl")

    def _run(self, **kwargs):
        defaults = dict(
            add_candidate_fn=_AddCandidateRecorder(),
            scan_fn=_scan_no_hit,
            enum_surface=_SURFACE,
        )
        defaults.update(kwargs)
        return _distill.run_distill(self.audit_dir, **defaults)


# ---------------------------------------------------------------------------
# Closed-enum read boundary (hostile OBSERVATION rejected pre-candidate)
# ---------------------------------------------------------------------------


class TestObservationReadBoundary(_DistillBase):
    def test_benign_observations_all_consumed(self):
        self._seed_store("benign_observations.jsonl")
        obs, offsets, rejected = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        # 6 observe-store rows; a real store carries only observation rows
        # (no foreign action lines exist in the opt-in store).
        self.assertEqual(len(obs), 6)
        self.assertEqual(rejected, 0)
        self.assertGreater(offsets[_STORE_NAME], 0)

    def test_hostile_observation_dropped_at_read(self):
        """Planted hostile observation is rejected PRE-candidate (A4).

        Defense-in-depth: the real observe writer coerces every field, but
        the distiller re-validates each store row and never trusts it.
        """
        self._seed_store("hostile_observations.jsonl")
        obs, _, rejected = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        # Rows 2 (free-text tool_name_enum), 3 (bad bucket), 4 (non-bool
        # success) are dropped; rows 1, 5, 6 survive (row 5's extra free-text
        # field is never read).
        self.assertEqual(rejected, 3)
        self.assertEqual(len(obs), 3)
        for record in obs:
            self.assertEqual(
                set(record.keys()),
                {"tool_name_enum", "duration_bucket", "success", "orphan"},
            )

    def test_hostile_payload_never_reaches_prompt(self):
        self._seed_store("hostile_observations.jsonl")
        obs, _, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        prompt = _distill.build_prompt(_distill.aggregate(obs))
        for payload in (
            "IGNORE ALL PREVIOUS INSTRUCTIONS",
            "SMUGGLED-FREE-TEXT",
            "evil@example.invalid",
            "not_a_real_bucket",
        ):
            self.assertNotIn(payload, prompt)

    def test_prompt_deterministic_twice_run_identical(self):
        self._seed_store("benign_observations.jsonl")
        obs, _, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        p1 = _distill.build_prompt(_distill.aggregate(obs))
        p2 = _distill.build_prompt(_distill.aggregate(list(obs)))
        self.assertEqual(p1, p2)

    def test_enum_pin_sync_with_real_surface(self):
        """Local test mirror must match the rail's real closed enums."""
        real = _distill._load_enum_surface()
        if real is None:
            self.skipTest("_lib.tool_lifecycle unavailable (overlay run)")
        real_to_enum, real_buckets = real
        self.assertEqual(tuple(real_buckets), _BUCKETS)
        for name in sorted(_RECOGNIZED) + ["mcp_other", "other"]:
            self.assertEqual(real_to_enum(name), _to_enum(name))
        self.assertEqual(real_to_enum("totally-unknown"), "other")
        self.assertEqual(real_to_enum("mcp__srv__tool"), "mcp_other")


# ---------------------------------------------------------------------------
# Delta cursor
# ---------------------------------------------------------------------------


class TestDeltaCursor(_DistillBase):
    def test_second_read_consumes_nothing(self):
        self._seed_store("benign_observations.jsonl")
        _, offsets, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        obs2, offsets2, _ = _distill.read_new_observations(
            self.audit_dir, offsets, _to_enum, _BUCKETS
        )
        self.assertEqual(obs2, [])
        self.assertEqual(offsets2, offsets)

    def test_appended_line_is_picked_up(self):
        self._seed_store("benign_observations.jsonl")
        _, offsets, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        extra = {
            "v": 1,
            "tool_name_enum": "Write",
            "duration_bucket": "lt_100ms",
            "success": True,
            "orphan": False,
            "paired": True,
            "tool_use_hash": "abcd0123",
        }
        with open(self._store_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(extra) + "\n")
        obs2, _, _ = _distill.read_new_observations(
            self.audit_dir, offsets, _to_enum, _BUCKETS
        )
        self.assertEqual(len(obs2), 1)
        self.assertEqual(obs2[0]["tool_name_enum"], "Write")

    def test_partial_trailing_line_not_consumed(self):
        self._seed_store("benign_observations.jsonl")
        with open(self._store_path(), "a", encoding="utf-8") as fh:
            fh.write('{"v": 1, "tool_name_enum": "Wri')
        _, offsets, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        size = self._store_path().stat().st_size
        self.assertLess(offsets[_STORE_NAME], size)

    def test_shrunk_file_resets_offset(self):
        self._seed_store("benign_observations.jsonl")
        _, offsets, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        # Simulate pruning/rotation reuse: truncate to a single valid row.
        line = json.dumps({
            "v": 1,
            "tool_name_enum": "Bash",
            "duration_bucket": "lt_100ms",
            "success": True,
            "orphan": False,
            "paired": True,
            "tool_use_hash": "0f0f",
        }) + "\n"
        self._store_path().write_text(line, encoding="utf-8")
        obs, offsets2, _ = _distill.read_new_observations(
            self.audit_dir, offsets, _to_enum, _BUCKETS
        )
        self.assertEqual(len(obs), 1)
        self.assertEqual(offsets2[_STORE_NAME], len(line.encode("utf-8")))

    def test_cursor_round_trip_and_0600_mode(self):
        ok = _distill.save_cursor(
            self.audit_dir, {_STORE_NAME: 42}, now_fn=lambda: 1700000000.0
        )
        self.assertTrue(ok)
        self.assertEqual(
            _distill.load_cursor(self.audit_dir), {_STORE_NAME: 42}
        )
        mode = stat.S_IMODE(os.stat(_distill._cursor_path(self.audit_dir)).st_mode)
        self.assertEqual(mode, 0o600)
        # Injectable clock (A9): last_run_at derives from now_fn.
        payload = json.loads(
            _distill._cursor_path(self.audit_dir).read_text(encoding="utf-8")
        )
        self.assertTrue(payload["last_run_at"].startswith("2023-11-14T22:13:20"))

    def test_malformed_cursor_treated_as_empty(self):
        sdir = _distill._state_dir(self.audit_dir)
        sdir.mkdir(parents=True)
        (sdir / "cursor.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(_distill.load_cursor(self.audit_dir), {})

    def test_traversal_cursor_keys_ignored(self):
        sdir = _distill._state_dir(self.audit_dir)
        sdir.mkdir(parents=True)
        (sdir / "cursor.json").write_text(json.dumps({
            "schema": 1,
            "files": {"../../etc/passwd.observe.jsonl": 10, _STORE_NAME: 5},
        }), encoding="utf-8")
        self.assertEqual(
            _distill.load_cursor(self.audit_dir), {_STORE_NAME: 5}
        )

    def test_audit_log_names_are_not_tracked(self):
        """Legacy audit-log cursor keys are ignored by the observe-store regex."""
        sdir = _distill._state_dir(self.audit_dir)
        sdir.mkdir(parents=True)
        (sdir / "cursor.json").write_text(json.dumps({
            "schema": 1,
            "files": {"audit-log.jsonl": 99, _STORE_NAME: 5},
        }), encoding="utf-8")
        self.assertEqual(
            _distill.load_cursor(self.audit_dir), {_STORE_NAME: 5}
        )


# ---------------------------------------------------------------------------
# A12 kill-switch negative control (the certifying artifact — Codex S265 P2#4)
# ---------------------------------------------------------------------------


class TestKillSwitchNegativeControl(_DistillBase):
    """An un-opted-in session mints ZERO candidates.

    The distiller reads the OPT-IN observe store, never the always-on
    ``tool_call_lifecycle_recorded`` audit action. With ``CEO_LEARNING_OBSERVE``
    never set, no ``*.observe.jsonl`` file exists, so the distiller has zero
    input EVEN WHEN the always-on audit log is full of lifecycle events. If
    this test is reverted to read the audit action, these assertions fail —
    that is the intended teeth.
    """

    def test_no_observe_store_means_zero_observations(self):
        # Always-on audit log present (sessions ran) but NO observe store
        # (nobody opted in). The read surface must yield ZERO observations.
        self._seed_always_on_audit_log()
        obs, offsets, rejected = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        self.assertEqual(obs, [])
        self.assertEqual(rejected, 0)
        self.assertEqual(offsets, {})  # no observe-store files → nothing tracked

    def test_killswitch_unset_yields_zero_candidates(self):
        # Teeth: a benign model fixture that WOULD mint a candidate if any
        # observation were seen. Observe unset → no store → no_new_events →
        # zero candidates, and the model is never even consulted.
        self._seed_always_on_audit_log()
        recorder = _AddCandidateRecorder(status="PENDING")
        result = self._run(
            fixture_path=_FIXTURES / "model_output_benign.json",
            add_candidate_fn=recorder,
            scan_fn=_real_or_fallback_scanner(),
        )
        self.assertEqual(result.outcome, "no_new_events")
        self.assertEqual(result.events_consumed, 0)
        self.assertEqual(result.candidates_written, 0)
        self.assertEqual(recorder.calls, [])

    def test_real_rail_writes_no_store_when_unset(self):
        """Genuine rail coupling: the observe rail writes NO store when unset."""
        tl = _load_tool_lifecycle()
        if tl is None:
            self.skipTest("_lib.tool_lifecycle unavailable (overlay run)")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_LEARNING_OBSERVE", None)
            os.environ.pop("CEO_SOTA_DISABLE", None)
            tl._observe_post(
                session_id="s-neg",
                raw_tool_name="Bash",
                duration_ms=200,
                success=True,
                orphan=False,
                paired=True,
                tool_use_id="t1",
                audit_dir=self.audit_dir,
            )
        self.assertFalse(
            tl.observation_store_path("s-neg", self.audit_dir).exists()
        )
        # And so the distiller sees nothing.
        obs, _, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        self.assertEqual(obs, [])

    def test_opt_in_rail_write_is_read_by_distiller(self):
        """Positive coupling: an observe=1 rail write is picked up here."""
        tl = _load_tool_lifecycle()
        if tl is None:
            self.skipTest("_lib.tool_lifecycle unavailable (overlay run)")
        with mock.patch.dict(os.environ, {"CEO_LEARNING_OBSERVE": "1"}):
            os.environ.pop("CEO_SOTA_DISABLE", None)
            tl._observe_post(
                session_id="s-pos",
                raw_tool_name="Bash",
                duration_ms=5000,
                success=False,
                orphan=False,
                paired=True,
                tool_use_id="t9",
                audit_dir=self.audit_dir,
            )
        store = tl.observation_store_path("s-pos", self.audit_dir)
        self.assertTrue(store.exists())
        obs, _, _ = _distill.read_new_observations(
            self.audit_dir, {}, _to_enum, _BUCKETS
        )
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["tool_name_enum"], "Bash")
        self.assertFalse(obs[0]["success"])


# ---------------------------------------------------------------------------
# Output schema validation (fail-CLOSED)
# ---------------------------------------------------------------------------


class TestOutputSchema(TestEnvContext):
    def _cand(self, **overrides):
        cand = {
            "trigger": "repeat_tool_failure",
            "advisory_text": "Prefer dry-run flags before stateful commands.",
            "scope_tags": ["bash"],
        }
        cand.update(overrides)
        return cand

    def test_valid_output_accepted(self):
        text = json.dumps({"candidates": [self._cand()]})
        candidates, reason = _distill.validate_model_output(text)
        self.assertEqual(reason, "")
        self.assertEqual(len(candidates), 1)

    def test_empty_candidates_valid(self):
        candidates, reason = _distill.validate_model_output('{"candidates": []}')
        self.assertEqual(candidates, [])
        self.assertEqual(reason, "")

    def test_non_json_rejected(self):
        candidates, _ = _distill.validate_model_output("not json at all")
        self.assertIsNone(candidates)

    def test_over_schema_top_level_key_rejected(self):
        text = json.dumps({"candidates": [], "notes": "free text"})
        candidates, reason = _distill.validate_model_output(text)
        self.assertIsNone(candidates)
        self.assertIn("over-schema", reason)

    def test_too_many_candidates_rejected(self):
        text = json.dumps({
            "candidates": [self._cand() for _ in range(
                _distill.MAX_CANDIDATES_PER_RUN + 1
            )]
        })
        candidates, _ = _distill.validate_model_output(text)
        self.assertIsNone(candidates)

    def test_unknown_trigger_rejected(self):
        self.assertIsNotNone(
            _distill.validate_candidate(self._cand(trigger="be_evil"))
        )

    def test_backtick_rejected(self):
        self.assertIsNotNone(_distill.validate_candidate(
            self._cand(advisory_text="run `rm -rf` now")
        ))

    def test_newline_rejected(self):
        self.assertIsNotNone(_distill.validate_candidate(
            self._cand(advisory_text="line one\nline two")
        ))

    def test_zero_width_rejected(self):
        self.assertIsNotNone(_distill.validate_candidate(
            self._cand(advisory_text="benign" + "\u200b" + "text")
        ))

    def test_over_200_chars_rejected(self):
        self.assertIsNotNone(_distill.validate_candidate(
            self._cand(advisory_text="x" * (_distill.MAX_ADVISORY_CHARS + 1))
        ))

    def test_exactly_200_chars_accepted(self):
        self.assertIsNone(_distill.validate_candidate(
            self._cand(advisory_text="x" * _distill.MAX_ADVISORY_CHARS)
        ))

    def test_bad_scope_tag_rejected(self):
        self.assertIsNotNone(_distill.validate_candidate(
            self._cand(scope_tags=["UPPER CASE TAG"])
        ))

    def test_extra_candidate_key_rejected(self):
        cand = self._cand()
        cand["confidence"] = 0.9
        self.assertIsNotNone(_distill.validate_candidate(cand))


# ---------------------------------------------------------------------------
# End-to-end fixture runs (the mandatory A4 pair + posture map)
# ---------------------------------------------------------------------------


class TestRunDistillFixtures(_DistillBase):
    def test_benign_survives_to_pending(self):
        """Benign observation window -> candidate written as PENDING."""
        self._seed_store("benign_observations.jsonl")
        recorder = _AddCandidateRecorder(status="PENDING")
        result = self._run(
            fixture_path=_FIXTURES / "model_output_benign.json",
            add_candidate_fn=recorder,
            scan_fn=_real_or_fallback_scanner(),
        )
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.candidates_written, 1)
        self.assertEqual(result.rejected_pre_candidate, 0)
        self.assertEqual(len(recorder.calls), 1)
        self.assertEqual(recorder.calls[0]["trigger"], "repeat_tool_failure")
        self.assertTrue(result.cursor_advanced)
        self.assertEqual(result.tokens_in, 512)
        self.assertEqual(result.tokens_out, 96)
        self.assertTrue(result.fixture_mode)

    def test_hostile_model_output_rejected_pre_candidate(self):
        """Injection payload in a candidate never reaches add_candidate."""
        self._seed_store("benign_observations.jsonl")
        recorder = _AddCandidateRecorder()
        result = self._run(
            fixture_path=_FIXTURES / "model_output_hostile.json",
            add_candidate_fn=recorder,
            scan_fn=_real_or_fallback_scanner(),
        )
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.rejected_pre_candidate, 1)
        self.assertEqual(result.candidates_written, 0)
        self.assertEqual(recorder.calls, [])

    def test_malformed_output_fail_closed_no_cursor_advance(self):
        self._seed_store("benign_observations.jsonl")
        recorder = _AddCandidateRecorder()
        result = self._run(
            fixture_path=_FIXTURES / "model_output_malformed.json",
            add_candidate_fn=recorder,
        )
        self.assertEqual(result.outcome, "schema_reject")
        self.assertEqual(recorder.calls, [])
        self.assertFalse(result.cursor_advanced)
        self.assertFalse(_distill._cursor_path(self.audit_dir).exists())

    def test_over_schema_output_fail_closed(self):
        self._seed_store("benign_observations.jsonl")
        recorder = _AddCandidateRecorder()
        result = self._run(
            fixture_path=_FIXTURES / "model_output_over_schema.json",
            add_candidate_fn=recorder,
        )
        self.assertEqual(result.outcome, "schema_reject")
        self.assertEqual(recorder.calls, [])
        self.assertFalse(result.cursor_advanced)

    def test_empty_candidates_run_is_success_and_advances_cursor(self):
        self._seed_store("benign_observations.jsonl")
        result = self._run(fixture_path=_FIXTURES / "model_output_empty.json")
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.candidates_written, 0)
        self.assertTrue(result.cursor_advanced)

    def test_quarantined_status_counted(self):
        self._seed_store("benign_observations.jsonl")
        recorder = _AddCandidateRecorder(status="QUARANTINED")
        result = self._run(
            fixture_path=_FIXTURES / "model_output_benign.json",
            add_candidate_fn=recorder,
        )
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.candidates_quarantined, 1)
        self.assertEqual(result.candidates_written, 0)

    def test_scanner_unavailable_refuses_before_spend(self):
        self._seed_store("benign_observations.jsonl")
        invoked = []

        def _invoke(prompt, model):
            invoked.append(model)
            return '{"candidates": []}', 1, 1

        # scan_fn=None falls back to _load_scanner(); force the unavailable
        # branch explicitly for determinism across layouts:
        with mock.patch.object(_distill, "_load_scanner", return_value=None):
            result = _distill.run_distill(
                self.audit_dir,
                invoke_fn=_invoke,
                add_candidate_fn=_AddCandidateRecorder(),
                enum_surface=_SURFACE,
            )
        self.assertEqual(result.outcome, "scan_unavailable")
        self.assertEqual(result.tokens_in, 0)

    def test_scanner_exception_treats_candidate_as_hit(self):
        def _raiser(_text):
            raise RuntimeError("scanner exploded")

        self.assertTrue(_distill.scan_candidate_blob(
            {"trigger": "repeat_tool_failure", "advisory_text": "x",
             "scope_tags": ["a"]},
            _raiser,
        ))

    def test_store_unavailable_refuses(self):
        self._seed_store("benign_observations.jsonl")
        with mock.patch.object(_distill, "_resolve_add_candidate", return_value=None):
            result = _distill.run_distill(
                self.audit_dir,
                fixture_path=_FIXTURES / "model_output_benign.json",
                scan_fn=_scan_no_hit,
                enum_surface=_SURFACE,
            )
        self.assertEqual(result.outcome, "store_unavailable")
        self.assertFalse(result.cursor_advanced)

    def test_add_candidate_raising_no_cursor_advance(self):
        self._seed_store("benign_observations.jsonl")

        def _boom(**_kwargs):
            raise OSError("disk full")

        result = self._run(
            fixture_path=_FIXTURES / "model_output_benign.json",
            add_candidate_fn=_boom,
        )
        self.assertEqual(result.outcome, "store_unavailable")
        self.assertFalse(result.cursor_advanced)

    def test_add_candidate_valueerror_is_boundary_reject(self):
        """lessons.add_candidate ValueError = per-candidate reject, run ok."""
        self._seed_store("benign_observations.jsonl")

        def _vocab_reject(**_kwargs):
            raise ValueError("bounded-vocabulary violation (trigger_invalid)")

        result = self._run(
            fixture_path=_FIXTURES / "model_output_benign.json",
            add_candidate_fn=_vocab_reject,
        )
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.rejected_pre_candidate, 1)
        self.assertEqual(result.candidates_written, 0)
        self.assertTrue(result.cursor_advanced)

    def test_enum_surface_unavailable_refuses(self):
        self._seed_store("benign_observations.jsonl")
        with mock.patch.object(_distill, "_load_enum_surface", return_value=None):
            result = _distill.run_distill(
                self.audit_dir,
                fixture_path=_FIXTURES / "model_output_benign.json",
                add_candidate_fn=_AddCandidateRecorder(),
                scan_fn=_scan_no_hit,
            )
        self.assertEqual(result.outcome, "input_surface_unavailable")

    def test_token_ceiling_refuses_before_model_call(self):
        self._seed_store("benign_observations.jsonl")
        invoked = []

        def _invoke(prompt, model):
            invoked.append(model)
            return '{"candidates": []}', 1, 1

        result = self._run(invoke_fn=_invoke, max_input_tokens=1)
        self.assertEqual(result.outcome, "token_ceiling")
        self.assertEqual(invoked, [])
        self.assertFalse(result.cursor_advanced)

    def test_no_new_events_after_full_consumption(self):
        self._seed_store("benign_observations.jsonl")
        first = self._run(fixture_path=_FIXTURES / "model_output_empty.json")
        self.assertEqual(first.outcome, "ok")
        second = self._run(fixture_path=_FIXTURES / "model_output_empty.json")
        self.assertEqual(second.outcome, "no_new_events")
        self.assertEqual(second.events_consumed, 0)


# ---------------------------------------------------------------------------
# Model pin + env override + kill switch
# ---------------------------------------------------------------------------


class TestModelPinAndSwitches(_DistillBase):
    def test_default_model_is_pinned_haiku_tier(self):
        self.assertEqual(
            _distill.DEFAULT_DISTILL_MODEL, "claude-haiku-4-5-20251001"
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CEO_LEARNING_DISTILL_MODEL", None)
            self.assertEqual(
                _distill.resolve_model(), "claude-haiku-4-5-20251001"
            )

    def test_env_override_wins(self):
        with mock.patch.dict(
            os.environ, {"CEO_LEARNING_DISTILL_MODEL": "claude-haiku-4-5"}
        ):
            self.assertEqual(_distill.resolve_model(), "claude-haiku-4-5")

    def test_sota_disable_is_noop(self):
        self._seed_store("benign_observations.jsonl")
        with mock.patch.dict(os.environ, {"CEO_SOTA_DISABLE": "1"}):
            rc = _distill.main(["--audit-dir", str(self.audit_dir)])
        self.assertEqual(rc, 0)
        self.assertFalse(_distill._cursor_path(self.audit_dir).exists())

    def test_fixture_model_id_reported(self):
        self._seed_store("benign_observations.jsonl")
        result = self._run(fixture_path=_FIXTURES / "model_output_benign.json")
        self.assertEqual(result.model_id, "claude-haiku-4-5-20251001")


# ---------------------------------------------------------------------------
# CLI exit codes + audit-event field contract
# ---------------------------------------------------------------------------


class TestCliAndEmission(_DistillBase):
    def _main(self, argv):
        with mock.patch.object(
            _distill, "_load_enum_surface", return_value=_SURFACE
        ), mock.patch.object(
            _distill, "_load_scanner", return_value=_scan_no_hit
        ), mock.patch.object(
            _distill, "_resolve_add_candidate",
            return_value=_AddCandidateRecorder(),
        ):
            return _distill.main(argv)

    def test_cli_ok_run(self):
        self._seed_store("benign_observations.jsonl")
        rc = self._main([
            "--audit-dir", str(self.audit_dir),
            "--from-fixture", str(_FIXTURES / "model_output_benign.json"),
        ])
        self.assertEqual(rc, 0)

    def test_cli_schema_reject_exit_4(self):
        self._seed_store("benign_observations.jsonl")
        rc = self._main([
            "--audit-dir", str(self.audit_dir),
            "--from-fixture", str(_FIXTURES / "model_output_malformed.json"),
        ])
        self.assertEqual(rc, 4)

    def test_cli_store_unavailable_exit_2(self):
        self._seed_store("benign_observations.jsonl")
        with mock.patch.object(
            _distill, "_load_enum_surface", return_value=_SURFACE
        ), mock.patch.object(
            _distill, "_load_scanner", return_value=_scan_no_hit
        ), mock.patch.object(
            _distill, "_resolve_add_candidate", return_value=None
        ):
            rc = _distill.main([
                "--audit-dir", str(self.audit_dir),
                "--from-fixture", str(_FIXTURES / "model_output_benign.json"),
            ])
        self.assertEqual(rc, 2)

    def test_print_prompt_writes_nothing(self):
        self._seed_store("benign_observations.jsonl")
        import contextlib
        import io
        out = io.StringIO()
        with mock.patch.object(
            _distill, "_load_enum_surface", return_value=_SURFACE
        ), contextlib.redirect_stdout(out):
            rc = _distill.main([
                "--audit-dir", str(self.audit_dir), "--print-prompt",
            ])
        self.assertEqual(rc, 0)
        self.assertIn("## Digest", out.getvalue())
        self.assertFalse(_distill._cursor_path(self.audit_dir).exists())

    def test_run_event_field_contract(self):
        captured = {}

        def _recorder(action, **fields):
            captured["action"] = action
            captured["fields"] = fields

        result = _distill.DistillResult(
            outcome="ok", model_id="claude-haiku-4-5-20251001",
            fixture_mode=True, events_consumed=6, candidates_proposed=1,
            candidates_written=1, tokens_in=512, tokens_out=96,
            cursor_advanced=True,
        )
        _distill._emit_run_event(result, emit_fn=_recorder)
        self.assertEqual(captured["action"], "distiller_run_completed")
        self.assertEqual(
            set(captured["fields"].keys()),
            {
                "outcome", "model_id", "fixture_mode", "events_consumed",
                "observations_rejected", "candidates_proposed",
                "candidates_written", "candidates_quarantined",
                "rejected_pre_candidate", "tokens_in", "tokens_out",
                "cursor_advanced", "session_id", "project",
            },
        )
        self.assertIn(captured["fields"]["outcome"], _distill.OUTCOMES)
        self.assertEqual(captured["fields"]["tokens_in"], 512)
        self.assertEqual(captured["fields"]["tokens_out"], 96)

    def test_run_event_emitter_failure_swallowed(self):
        def _boom(_action, **_fields):
            raise RuntimeError("audit down")

        # Must not raise (audit-emit is the only fail-open edge).
        _distill._emit_run_event(_distill.DistillResult(), emit_fn=_boom)


if __name__ == "__main__":
    unittest.main()
