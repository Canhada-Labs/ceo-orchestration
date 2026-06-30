"""test_ceo_boot_task_candidate.py — PLAN-078 Wave 5 marker emit + dedup.

Asserts:
- ``_emit_task_candidate_markers`` writes the 3-line ``<!-- TASKCREATE-CANDIDATE -->``
  block to stdout when ``gate_pass=False`` AND severity≥medium AND not
  --short / --cached / --json AND env CEO_BOOT_AUTO_TASK!=0.
- Top-3 cap respected.
- Dedup state file (24h TTL) prevents same subject re-emit; corrupt JSON
  is self-healing (fail-open); concurrent writes are filelock'd.
- ``_subject_hash`` is NFKC-stable + 12 hex chars.
- ``_recommendations_with_severity`` mirrors ``_make_recommendations``
  ordering and assigns the documented severity buckets.
- audit_emit wrapper short-circuits pre-canonical-ceremony.
- Layer A bypass paths: --short / --cached / --json / env=0 / gate_pass=True.

Stdlib only. TestEnvContext for env hygiene + tmpdir scoping.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"


def _load_module():
    """Load ceo-boot.py as importable module (hyphenated filename)."""
    if "ceo_boot_w5" in sys.modules:
        del sys.modules["ceo_boot_w5"]
    spec = importlib.util.spec_from_file_location("ceo_boot_w5", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ceo_boot_w5"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_check_result(mod, name: str, status: str, summary: str = "", detail=None):
    """Construct a CheckResult shim from the live module's class."""
    return mod.CheckResult(name, status, summary, 0.0, detail)


class _W5TestBase(TestEnvContext):
    """Shared setup: per-test tmpdir for state file, fresh module load.

    Env hygiene (Sec ADR-018): CEO_* env mutations go through the parent
    ``TestEnvContext`` snapshot/restore. We previously used
    ``mock.patch.dict`` to set per-test env, but mock.patch.dict snapshots
    the FULL ``os.environ`` at ``.start()`` and restores to that snapshot at
    ``.stop()``. With ``addCleanup`` (which runs AFTER ``tearDown``), the
    mock.stop() would OVERWRITE the env that TestEnvContext.tearDown had
    just restored — re-injecting the per-test tmpdir CLAUDE_PROJECT_DIR
    into the parent environment and breaking sibling tests that subprocess
    ``generate-dispatch.py`` etc. We assign env vars directly; the parent
    TestEnvContext.tearDown removes any ``CEO_*``/``CLAUDE_*`` key not in
    its snapshot, which covers our CEO_BOOT_TASK_STATE_PATH.
    """

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="ceo_boot_w5_")
        self._state_path = Path(self._tmp) / "ceo-boot-tasks-emitted.json"
        # CEO_-prefixed env: TestEnvContext.tearDown removes any CEO_/CLAUDE_
        # key not in its setUp snapshot, so direct assignment is safe here.
        os.environ["CEO_BOOT_TASK_STATE_PATH"] = str(self._state_path)
        self.mod = _load_module()

    def _set_env(self, key: str, value: str) -> None:
        """Add an env-var for the duration of this test.

        Direct assignment; the parent TestEnvContext.tearDown restores
        env state on teardown (removes CEO_/CLAUDE_/HOME keys not in
        the setUp snapshot, restores snapshot values for keys that were).
        """
        os.environ[key] = value

    def tearDown(self):
        try:
            for p in Path(self._tmp).rglob("*"):
                if p.is_file():
                    p.unlink()
            Path(self._tmp).rmdir()
        except OSError:
            pass
        super().tearDown()


# ---------------------------------------------------------------------------
# Section 1 — _subject_hash determinism + NFKC normalization
# ---------------------------------------------------------------------------


class TestSubjectHash(_W5TestBase):
    def test_returns_12_hex_chars(self):
        h = self.mod._subject_hash("Owner GPG sign pending: 3 sentinels")
        self.assertEqual(len(h), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_deterministic_across_calls(self):
        h1 = self.mod._subject_hash("Stranded plans: PLAN-074")
        h2 = self.mod._subject_hash("Stranded plans: PLAN-074")
        self.assertEqual(h1, h2)

    def test_nfkc_homoglyph_collapses(self):
        # Fullwidth digits → ASCII digits should hash identically
        h_ascii = self.mod._subject_hash("PLAN-074")
        h_fullwidth = self.mod._subject_hash("PLAN-０７４")
        self.assertEqual(h_ascii, h_fullwidth)

    def test_distinct_subjects_distinct_hashes(self):
        h_a = self.mod._subject_hash("Stranded: PLAN-074")
        h_b = self.mod._subject_hash("Stranded: PLAN-075")
        self.assertNotEqual(h_a, h_b)


# ---------------------------------------------------------------------------
# Section 2 — _recommendations_with_severity ordering + buckets
# ---------------------------------------------------------------------------


class TestSeverityMapping(_W5TestBase):
    def test_owner_sentinels_is_high(self):
        results = [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1", "s2", "s3"],
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(len(triples), 1)
        sort_key, _, severity = triples[0]
        self.assertEqual(sort_key, "01-owner-sentinels")
        self.assertEqual(severity, "high")

    def test_stranded_plans_is_high(self):
        results = [
            _make_check_result(
                self.mod, "plans_stranded_executing", "red",
                "1 stranded", detail=["PLAN-074"],
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(triples[0][2], "high")

    def test_skill_unknown_is_medium(self):
        results = [
            _make_check_result(
                self.mod, "skill_unknown_ratio", "red",
                "ratio 60%",
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(triples[0][2], "medium")

    def test_audit_v3_backlog_is_medium(self):
        results = [
            _make_check_result(
                self.mod, "audit_v3_backlog", "yellow",
                "5 open", detail=["DIM-01"],
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(triples[0][2], "medium")

    def test_adrs_stale_is_low(self):
        results = [
            _make_check_result(
                self.mod, "adrs_stale_proposed", "yellow",
                "2 stale", detail=["ADR-099"],
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(triples[0][2], "low")

    def test_ordering_matches_make_recommendations(self):
        results = [
            _make_check_result(
                self.mod, "adrs_stale_proposed", "yellow",
                "2 stale", detail=["ADR-099"],
            ),
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1"],
            ),
            _make_check_result(
                self.mod, "skill_unknown_ratio", "red",
                "ratio 60%",
            ),
        ]
        flat = self.mod._make_recommendations(results)
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual([t[1] for t in triples], flat)


# ---------------------------------------------------------------------------
# Section 3 — Marker emit (Layer A) happy path + bypass branches
# ---------------------------------------------------------------------------


class TestMarkerEmit(_W5TestBase):
    def _high_sev_results(self):
        return [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1", "s2", "s3"],
            ),
            _make_check_result(
                self.mod, "plans_stranded_executing", "red",
                "1 stranded", detail=["PLAN-074"],
            ),
            _make_check_result(
                self.mod, "skill_unknown_ratio", "red",
                "ratio 60%",
            ),
        ]

    def test_emit_high_severity_marker(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            emitted = self.mod._emit_task_candidate_markers(
                self._high_sev_results(),
                gate_pass=False, short=False, cached=False,
            )
        self.assertEqual(len(emitted), 3)  # 2 high + 1 medium = 3 total
        out = buf.getvalue()
        self.assertEqual(out.count("<!-- TASKCREATE-CANDIDATE"), 3)
        self.assertEqual(out.count("<!-- /TASKCREATE-CANDIDATE -->"), 3)
        self.assertIn("severity=high", out)
        self.assertIn("severity=medium", out)
        self.assertIn("rank=1", out)
        self.assertIn("rank=3", out)

    def test_top_n_cap(self):
        # Manufacture 5 medium+/high recs by combining high + medium rules.
        # Severity bucket mapping puts 2 highs (sentinels + stranded) and 2
        # mediums (skill-unknown + audit-v3); the 5th rec (adrs-stale) is
        # low and must be filtered out before the top-3 cap. So even with
        # 4 medium+/high recs, only 3 markers should emit.
        results = self._high_sev_results() + [
            _make_check_result(
                self.mod, "audit_v3_backlog", "yellow",
                "2 open", detail=["DIM-01"],
            ),
            _make_check_result(
                self.mod, "adrs_stale_proposed", "yellow",
                "1 stale", detail=["ADR-099"],
            ),
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            emitted = self.mod._emit_task_candidate_markers(
                results, gate_pass=False, short=False, cached=False,
            )
        self.assertEqual(len(emitted), 3)
        # Low-severity adrs-stale must NOT appear in stdout
        self.assertNotIn("ADR-099", buf.getvalue())

    def test_bypass_gate_pass_true(self):
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=True, short=False, cached=False,
        )
        self.assertEqual(emitted, [])

    def test_bypass_short_mode(self):
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=True, cached=False,
        )
        self.assertEqual(emitted, [])

    def test_bypass_cached_mode(self):
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=True,
        )
        self.assertEqual(emitted, [])

    def test_bypass_env_auto_task_zero(self):
        self._set_env("CEO_BOOT_AUTO_TASK", "0")
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        self.assertEqual(emitted, [])

    def test_no_actionable_recs_no_emit(self):
        # Only low-severity rec → no marker
        results = [
            _make_check_result(
                self.mod, "adrs_stale_proposed", "yellow",
                "1 stale", detail=["ADR-099"],
            ),
        ]
        emitted = self.mod._emit_task_candidate_markers(
            results, gate_pass=False, short=False, cached=False,
        )
        self.assertEqual(emitted, [])


# ---------------------------------------------------------------------------
# Section 4 — Dedup state file: TTL, persistence, corruption recovery
# ---------------------------------------------------------------------------


class TestDedupStateFile(_W5TestBase):
    def _high_sev_results(self):
        return [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1"],
            ),
        ]

    def test_first_emit_persists_state(self):
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        self.assertEqual(len(emitted), 1)
        self.assertTrue(self._state_path.exists())
        data = json.loads(self._state_path.read_text())
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(len(data["entries"][0]["subject_hash"]), 12)

    def test_second_emit_dedupd(self):
        # First call emits + persists
        self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        # Second call should dedup
        buf = io.StringIO()
        with redirect_stdout(buf):
            emitted2 = self.mod._emit_task_candidate_markers(
                self._high_sev_results(),
                gate_pass=False, short=False, cached=False,
            )
        self.assertEqual(emitted2, [])
        self.assertNotIn("TASKCREATE-CANDIDATE", buf.getvalue())

    def test_ttl_expired_re_emits(self):
        # Seed state file with a ts older than TASK_EMIT_TTL_S (24h)
        sub = "Owner GPG sign pending: 1 sentinels (s1)"
        sh = self.mod._subject_hash(sub)
        ancient_ts = time.time() - (self.mod.TASK_EMIT_TTL_S + 100)
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps({"entries": [{"subject_hash": sh, "ts": ancient_ts}]})
        )
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        self.assertEqual(len(emitted), 1)

    def test_corrupt_state_self_heals(self):
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text("{not valid json")
        emitted = self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        self.assertEqual(len(emitted), 1)
        # State file should now be well-formed
        data = json.loads(self._state_path.read_text())
        self.assertEqual(len(data["entries"]), 1)

    def test_state_file_size_bound(self):
        # Seed >256 stale entries — load should LRU-trim before emit
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        entries = [
            {"subject_hash": f"{i:012x}"[:12], "ts": now - i * 100}
            for i in range(self.mod.TASK_EMIT_STATE_MAX_ENTRIES + 50)
        ]
        self._state_path.write_text(json.dumps({"entries": entries}))
        # Drive a real emit so the load+save cycle runs
        self.mod._emit_task_candidate_markers(
            self._high_sev_results(),
            gate_pass=False, short=False, cached=False,
        )
        data = json.loads(self._state_path.read_text())
        # New entry adds 1 → still bounded by MAX (the LRU-trim happens at
        # load time so the post-save count is MAX_ENTRIES at most + 1 new).
        self.assertLessEqual(
            len(data["entries"]),
            self.mod.TASK_EMIT_STATE_MAX_ENTRIES + 1,
        )


# ---------------------------------------------------------------------------
# Section 5 — Concurrent write filelock
# ---------------------------------------------------------------------------


class TestConcurrentWrite(_W5TestBase):
    def test_two_threads_no_corruption(self):
        # Two threads each emit a distinct subject; final state must
        # contain BOTH subject_hashes (filelock prevents lost-update).
        results_a = [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["sa"],
            ),
        ]
        results_b = [
            _make_check_result(
                self.mod, "plans_stranded_executing", "red",
                "1 stranded", detail=["PLAN-X"],
            ),
        ]

        def _worker(results):
            self.mod._emit_task_candidate_markers(
                results, gate_pass=False, short=False, cached=False,
            )

        ta = threading.Thread(target=_worker, args=(results_a,))
        tb = threading.Thread(target=_worker, args=(results_b,))
        ta.start(); tb.start()
        ta.join(); tb.join()
        data = json.loads(self._state_path.read_text())
        self.assertEqual(len(data["entries"]), 2)


# ---------------------------------------------------------------------------
# Section 6 — Audit emit wrapper fail-soft (pre-canonical-ceremony)
# ---------------------------------------------------------------------------


class TestEmitWrapper(_W5TestBase):
    def test_emit_safe_audit_emit_none_silent(self):
        original = self.mod._audit_emit
        self.mod._audit_emit = None
        try:
            # Should not raise
            self.mod._emit_task_candidate_safe(
                rank=1, severity="high",
                subject_hash="aaaaaaaaaaaa", awaiting_confirm=False,
            )
        finally:
            self.mod._audit_emit = original

    def test_emit_safe_function_absent_silent(self):
        fake = MagicMock(spec=[])  # no attributes
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        try:
            buf = io.StringIO()
            with redirect_stderr(buf):
                self.mod._emit_task_candidate_safe(
                    rank=1, severity="high",
                    subject_hash="aaaaaaaaaaaa", awaiting_confirm=False,
                )
            self.assertEqual(buf.getvalue(), "")
        finally:
            self.mod._audit_emit = original

    def test_emit_safe_post_ceremony_calls_through(self):
        captured: List[Dict[str, Any]] = []

        def _fake_emit(**kwargs):
            captured.append(kwargs)

        fake = MagicMock(spec=["emit_ceo_boot_task_candidate_emitted"])
        fake.emit_ceo_boot_task_candidate_emitted = _fake_emit
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        try:
            self.mod._emit_task_candidate_safe(
                rank=2, severity="medium",
                subject_hash="abcdef012345", awaiting_confirm=False,
            )
        finally:
            self.mod._audit_emit = original
        self.assertEqual(len(captured), 1)
        kwargs = captured[0]
        self.assertEqual(kwargs["rank"], 2)
        self.assertEqual(kwargs["severity"], "medium")
        self.assertEqual(kwargs["subject_hash"], "abcdef012345")
        self.assertFalse(kwargs["awaiting_confirm"])
        # Sanity: no subject text leaks through
        self.assertNotIn("subject", kwargs)


# ---------------------------------------------------------------------------
# Section 7 — Sec MF-3: subject text never enters audit emit kwargs
# ---------------------------------------------------------------------------


class TestSanitization(_W5TestBase):
    def test_subject_text_never_in_emit_kwargs(self):
        captured: List[Dict[str, Any]] = []

        def _fake_emit(**kwargs):
            captured.append(kwargs)

        fake = MagicMock(spec=["emit_ceo_boot_task_candidate_emitted"])
        fake.emit_ceo_boot_task_candidate_emitted = _fake_emit
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.mod._emit_task_candidate_markers(
                    [
                        _make_check_result(
                            self.mod, "sentinels_pending_gpg", "yellow",
                            "3 pending", detail=["secret-token-leaks"],
                        ),
                    ],
                    gate_pass=False, short=False, cached=False,
                )
        finally:
            self.mod._audit_emit = original
        self.assertGreaterEqual(len(captured), 1)
        for kwargs in captured:
            for v in kwargs.values():
                self.assertNotIn("secret-token-leaks", str(v))


# ---------------------------------------------------------------------------
# Section 8 — Codex CDX-W5 closures: adversarial inputs + parser robustness
# ---------------------------------------------------------------------------


class TestAdversarialTimestamps(_W5TestBase):
    """Codex CDX-W5-P1-04 closure — future / NaN / inf timestamps."""

    def test_future_timestamp_dropped(self):
        # Seed a state-file with a far-future ts (NTP jump back, deliberate
        # tampering, etc.). Must NOT survive load + must NOT mask new emits.
        sh = "deadbeef0001"
        future_ts = time.time() + (30 * 24 * 60 * 60)  # +30d
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps({"entries": [{"subject_hash": sh, "ts": future_ts}]})
        )
        state = self.mod._load_task_emit_state(self._state_path)
        self.assertEqual(state["entries"], [])

    def test_inf_and_nan_timestamps_dropped(self):
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        # JSON disallows NaN/inf in standard mode but custom encoders /
        # corrupt files can produce them; test the loader handles them.
        # Use Python's `allow_nan=True` default — emit "Infinity" / "NaN"
        # via a hand-crafted JSON string.
        self._state_path.write_text(
            '{"entries":['
            '{"subject_hash":"a000","ts":Infinity},'
            '{"subject_hash":"a001","ts":-Infinity},'
            '{"subject_hash":"a002","ts":NaN}'
            "]}"
        )
        state = self.mod._load_task_emit_state(self._state_path)
        self.assertEqual(state["entries"], [])


class TestSubjectCollapse(_W5TestBase):
    """Codex CDX-W5-P1-05 closure — Subject line is single-line + bounded."""

    def _multiline_results(self):
        # Synthesize a check whose summary contains a literal newline +
        # tab + multi-space; recommendations engine inherits the summary
        # for the "00-* timeout/error" rules.
        cr = _make_check_result(
            self.mod, "future_check", "timeout",
            "line1\nline2\twith\t\ttabs   and  spaces",
        )
        return [cr]

    def test_collapse_marker_subject_strips_newlines(self):
        out = self.mod._collapse_marker_subject(
            "line1\nline2\twith\t\ttabs   and  spaces"
        )
        self.assertNotIn("\n", out)
        self.assertNotIn("\t", out)
        # Multi-space collapsed to single space
        self.assertNotIn("  ", out)

    def test_collapse_marker_subject_length_bounded(self):
        out = self.mod._collapse_marker_subject("a" * 500)
        self.assertEqual(len(out), 200)

    def test_marker_block_is_single_line_subject(self):
        # Even with a multiline summary, the Subject: line must be one line.
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod._emit_task_candidate_markers(
                self._multiline_results(),
                gate_pass=False, short=False, cached=False,
            )
        out = buf.getvalue()
        if "TASKCREATE-CANDIDATE" in out:
            # Find the Subject: line and assert it ends at the next newline
            for line in out.splitlines():
                if line.startswith("Subject:"):
                    # Must NOT contain \t and must not have nested \n
                    self.assertNotIn("\t", line)


class TestEmitGenericDispatchGate(_W5TestBase):
    """Codex CDX-W5-P2 closure — emit_generic strips forbidden fields.

    Verifies the dispatch-gate behavior using the STAGED audit_emit.py
    (loaded fresh from the staging path) so the test runs pre-ceremony
    on the candidate diff. Post-ceremony, the same test in
    `.claude/hooks/tests/test_audit_emit.py` covers the canonical path.
    """

    def test_subject_field_dropped_by_emit_generic(self):
        staged_audit_emit_path = (
            REPO_ROOT
            / ".claude" / "plans" / "PLAN-078" / "staging" / "wave-5"
            / "audit_emit.py"
        )
        if not staged_audit_emit_path.exists():
            self.skipTest("staged audit_emit.py not found — ceremony complete?")
        spec = importlib.util.spec_from_file_location(
            "audit_emit_w5_staged", staged_audit_emit_path,
        )
        ae_mod = importlib.util.module_from_spec(spec)
        sys.modules["audit_emit_w5_staged"] = ae_mod
        # Codex iter2-P2 closure: clean up sys.modules so a sibling test
        # never sees the staged module bleeding through.
        self.addCleanup(sys.modules.pop, "audit_emit_w5_staged", None)
        spec.loader.exec_module(ae_mod)

        # Capture _write_event invocations
        captured: List[Dict[str, Any]] = []
        original = ae_mod._write_event

        def _fake_write(event):
            captured.append(dict(event))

        ae_mod._write_event = _fake_write
        try:
            ae_mod.emit_generic(
                "ceo_boot_task_candidate_emitted",
                rank=1, severity="high",
                subject_hash="aaaaaaaaaaaa",
                awaiting_confirm=False,
                # Forbidden fields — must be scrubbed
                subject="SECRET TOPIC",
                recommendation_body="leaked",
                env_value="HOME=/secret",
            )
        finally:
            ae_mod._write_event = original

        self.assertEqual(len(captured), 1)
        event = captured[0]
        # Allowlisted fields present
        self.assertEqual(event["rank"], 1)
        self.assertEqual(event["severity"], "high")
        self.assertEqual(event["subject_hash"], "aaaaaaaaaaaa")
        # Forbidden fields scrubbed
        self.assertNotIn("subject", event)
        self.assertNotIn("recommendation_body", event)
        self.assertNotIn("env_value", event)


# ---------------------------------------------------------------------------
# Section 9 — Codex iter2 P1 closure: subject_hash matches collapsed subject
# ---------------------------------------------------------------------------


class TestNamedCheckTimeoutCoverage(_W5TestBase):
    """Codex CDX-W5-iter3-P1 closure — named check that times out emits.

    Pre-fix: a check named `sentinels_pending_gpg` (in `_NAMED_RULES`)
    with `status="timeout"` matched neither the `00-*` failing branch
    (skipped by `_NAMED_RULES`) nor the `01-owner-sentinels` branch
    (gated on `status=="yellow"`), producing zero recommendations even
    though gate_pass would be False.
    """

    def test_named_check_timeout_produces_high_rec(self):
        results = [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "timeout",
                "validate timeout",
            ),
        ]
        triples = self.mod._recommendations_with_severity(results)
        self.assertEqual(len(triples), 1)
        sort_key, _, severity = triples[0]
        self.assertTrue(sort_key.startswith("00-sentinels_pending_gpg"))
        self.assertEqual(severity, "high")

    def test_named_check_timeout_emits_marker(self):
        results = [
            _make_check_result(
                self.mod, "plans_stranded_executing", "error",
                "git unavailable",
            ),
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            emitted = self.mod._emit_task_candidate_markers(
                results, gate_pass=False, short=False, cached=False,
            )
        self.assertEqual(len(emitted), 1)
        self.assertIn("severity=high", buf.getvalue())

    def test_make_recommendations_parity(self):
        # Both helpers must emit the 00-* row for named-check timeout.
        results = [
            _make_check_result(
                self.mod, "skill_unknown_ratio", "timeout",
                "audit-log read timeout",
            ),
        ]
        flat = self.mod._make_recommendations(results)
        self.assertEqual(len(flat), 1)
        self.assertIn("'skill_unknown_ratio' timeout", flat[0])


class TestLockAcquireFailureFallthrough(_W5TestBase):
    """Codex CDX-W5-iter3-P1 closure — non-FileLockTimeout lock errors.

    Pre-fix: an arbitrary exception during `FileLock.__enter__()`
    (e.g. `OSError` on a bad state-file path, `PermissionError` on a
    read-only filesystem) fell through the OUTER except, returning
    `emitted=[]` and silently suppressing every marker.

    Post-fix: lock acquisition failure leaves `lock_acquired=False`
    and an empty `state`; markers still emit (operator pays one
    duplicate next boot, but never silent).
    """

    def test_invalid_state_path_still_emits_marker(self):
        # Point CEO_BOOT_TASK_STATE_PATH at a path under a non-writable
        # parent directory. macOS reliably refuses to create the lock.
        bad_dir = Path(self._tmp) / "no" / "such" / "dir"
        # Ensure the parent does not exist
        bad_state_path = bad_dir / "tasks.json"
        # Re-patch the env var
        self._set_env("CEO_BOOT_TASK_STATE_PATH", str(bad_state_path))
        # Force the dir to be a file so mkdir+open both fail
        unmakeable_parent = Path(self._tmp) / "blockfile"
        unmakeable_parent.write_text("not a dir")
        bad_state_path = unmakeable_parent / "tasks.json"
        self._set_env("CEO_BOOT_TASK_STATE_PATH", str(bad_state_path))

        results = [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1"],
            ),
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            emitted = self.mod._emit_task_candidate_markers(
                results, gate_pass=False, short=False, cached=False,
            )
        # Marker MUST still appear despite the lock acquisition failure
        self.assertEqual(len(emitted), 1)
        self.assertIn("TASKCREATE-CANDIDATE", buf.getvalue())


class TestStateBoundOnSave(_W5TestBase):
    """Codex CDX-W5-iter3-P2 closure — state size capped post-append.

    Pre-fix: load trimmed to 256 entries, then up to 3 new entries
    appended before save → persisted state could be 259. Post-fix:
    re-cap before persist so on-disk state is never > MAX.
    """

    def test_state_size_after_save_within_bound(self):
        # Seed state at the cap with stale (but in-TTL) entries
        max_n = self.mod.TASK_EMIT_STATE_MAX_ENTRIES
        now = time.time()
        entries = [
            {"subject_hash": f"{i:012x}"[:12], "ts": now - i}
            for i in range(max_n)
        ]
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"entries": entries}))
        # Drive an emit so 1 new entry is appended
        results = [
            _make_check_result(
                self.mod, "sentinels_pending_gpg", "yellow",
                "3 pending", detail=["s1"],
            ),
        ]
        self.mod._emit_task_candidate_markers(
            results, gate_pass=False, short=False, cached=False,
        )
        data = json.loads(self._state_path.read_text())
        self.assertLessEqual(len(data["entries"]), max_n)


class TestHashOfCollapsedSubject(_W5TestBase):
    """Hash MUST be computed on the post-collapse subject so the
    orchestrator (which only sees the collapsed `Subject:` line) can
    reconstruct the same 12-hex digest for dedup against the live task
    list. Hashing the pre-collapse text would silently break the
    contract documented in `commands/ceo-boot.md:Step 4.5`.
    """

    def test_subject_hash_matches_visible_subject(self):
        # Construct a check whose summary contains a newline + tabs.
        # The "00-* timeout/error" rule path inherits the summary, so a
        # `failure_check.timeout` row produces a recommendation whose
        # text contains a multiline string we can detect post-collapse.
        cr = _make_check_result(
            self.mod, "future_check", "timeout",
            "line A\n\nline B  with  spaces",
        )
        captured: List[Dict[str, Any]] = []

        def _fake_emit(**kwargs):
            captured.append(kwargs)

        fake = MagicMock(spec=["emit_ceo_boot_task_candidate_emitted"])
        fake.emit_ceo_boot_task_candidate_emitted = _fake_emit
        original = self.mod._audit_emit
        self.mod._audit_emit = fake
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.mod._emit_task_candidate_markers(
                    [cr], gate_pass=False, short=False, cached=False,
                )
        finally:
            self.mod._audit_emit = original

        # Extract the visible Subject: line from stdout
        out = buf.getvalue()
        self.assertIn("TASKCREATE-CANDIDATE", out)
        subject_line = None
        for line in out.splitlines():
            if line.startswith("Subject: "):
                subject_line = line[len("Subject: "):]
                break
        self.assertIsNotNone(subject_line)

        # The audit emit kwargs must carry the hash of THIS visible subject
        self.assertGreaterEqual(len(captured), 1)
        emitted_hash = captured[0]["subject_hash"]
        # Recompute via the public helper — must match
        recomputed = self.mod._subject_hash(subject_line)
        self.assertEqual(emitted_hash, recomputed)

        # Sanity: the state-file entry is keyed by the same hash
        data = json.loads(self._state_path.read_text())
        self.assertEqual(data["entries"][0]["subject_hash"], emitted_hash)


if __name__ == "__main__":
    unittest.main()
