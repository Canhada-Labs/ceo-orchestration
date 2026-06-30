"""Unit tests for PLAN-083 Wave 0b sub-0.8 budget-summary.py.

Covers ≥18 behaviors:

  1.  ``parse_since`` valid units (m/h/d) + invalid
  2.  ``parse_since`` negative rejected
  3.  ``_parse_ts`` round-trip
  4.  ``canonical_event_sha256`` strips hmac+hmac_error+hook_duration_ms
  5.  ``canonical_event_sha256`` same payload across rotations → same hash
  6.  ``iter_unique_events`` dedups across 2 files with 50% overlap
  7.  ``discover_logs`` orders backups before active
  8.  ``build_plan_attribution`` honors explicit plan_id
  9.  ``build_plan_attribution`` infers from plan_status_transition
  10. ``build_plan_attribution`` orphan (no transition) returns None
  11. ``rollup`` cumulative USD across 5 rotation files + active
  12. ``rollup`` ``--plan-id PLAN-081`` filter respects attribution
  13. ``rollup`` includes ``pair_rail_case`` Codex tokens
  14. ``rollup`` ``--by-wave`` aggregates correctly
  15. ``rollup --since`` filters by timestamp
  16. ``validate_memory_claim`` pass when in band
  17. ``validate_memory_claim`` warn when far outside
  18. ``validate_memory_claim`` unknown when no cost
  19. JSON output schema validates structurally
  20. ``compute_cost_usd`` returns None for unknown model
  21. ``_safe_plan_id`` rejects non-canonical strings (Sec MF-3 boundary)
  22. CLI bad ``--plan-id`` → exit 2
  23. CLI bad ``--since`` → exit 2
  24. ``_extract_wave_id`` heuristic from desc_preview

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch


# Load the staging budget-summary.py module.
_HERE = Path(__file__).resolve().parent
_STAGING_DIR = _HERE.parent
_FIXTURES_DIR = _HERE / "fixtures" / "budget_summary"

_spec = importlib.util.spec_from_file_location(
    "budget_summary_staging", _STAGING_DIR / "budget-summary.py"
)
budget_summary = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(budget_summary)  # type: ignore[union-attr]

# Load the fixture generator.
_gen_spec = importlib.util.spec_from_file_location(
    "generate_fixtures", _FIXTURES_DIR / "generate_fixtures.py"
)
generate_fixtures = importlib.util.module_from_spec(_gen_spec)  # type: ignore[arg-type]
assert _gen_spec.loader is not None
_gen_spec.loader.exec_module(generate_fixtures)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(action: str, **fields: Any) -> Dict[str, Any]:
    ev = {"action": action, "ts": "2026-05-01T10:00:00Z"}
    ev.update(fields)
    return ev


def _write_jsonl(path: Path, events: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestParseSince(unittest.TestCase):
    def test_minutes_hours_days_parse(self) -> None:
        self.assertEqual(budget_summary.parse_since("30m"), timedelta(minutes=30))
        self.assertEqual(budget_summary.parse_since("12h"), timedelta(hours=12))
        self.assertEqual(budget_summary.parse_since("30d"), timedelta(days=30))

    def test_invalid_rejected(self) -> None:
        with self.assertRaises(ValueError):
            budget_summary.parse_since("zzz")
        with self.assertRaises(ValueError):
            budget_summary.parse_since("1y")

    def test_negative_rejected(self) -> None:
        with self.assertRaises(ValueError):
            budget_summary.parse_since("-5h")


class TestParseTs(unittest.TestCase):
    def test_round_trip(self) -> None:
        ts = "2026-05-11T13:00:00Z"
        dt = budget_summary._parse_ts(ts)
        self.assertIsNotNone(dt)
        assert dt is not None  # for mypy
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 13)

    def test_non_string_returns_none(self) -> None:
        self.assertIsNone(budget_summary._parse_ts(None))
        self.assertIsNone(budget_summary._parse_ts(12345))


class TestCanonicalDedup(unittest.TestCase):
    def test_strips_hmac_and_friends(self) -> None:
        ev1 = {"action": "x", "ts": "T", "tokens_in": 10, "hmac": "deadbeef",
               "hmac_error": None, "hook_duration_ms": 42}
        ev2 = {"action": "x", "ts": "T", "tokens_in": 10, "hmac": "cafef00d",
               "hmac_error": "boom", "hook_duration_ms": 99}
        self.assertEqual(
            budget_summary.canonical_event_sha256(ev1),
            budget_summary.canonical_event_sha256(ev2),
        )

    def test_different_payload_different_hash(self) -> None:
        ev1 = {"action": "x", "tokens_in": 10}
        ev2 = {"action": "x", "tokens_in": 11}
        self.assertNotEqual(
            budget_summary.canonical_event_sha256(ev1),
            budget_summary.canonical_event_sha256(ev2),
        )


class TestIterUniqueEvents(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-unique-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_dedup_50pct_overlap(self) -> None:
        shared = [_make_event("a", n=i) for i in range(10)]
        f1 = shared + [_make_event("a", n=100 + i) for i in range(10)]
        f2 = shared + [_make_event("a", n=200 + i) for i in range(10)]
        # Tag with rotation-specific hmac so canonical drops it.
        for i, ev in enumerate(f1):
            ev["hmac"] = f"f1-{i}"
        for i, ev in enumerate(f2):
            ev["hmac"] = f"f2-{i}"
        _write_jsonl(self.tmp / "audit-log-001.jsonl", f1)
        _write_jsonl(self.tmp / "audit-log-002.jsonl", f2)

        events = list(budget_summary.iter_unique_events(
            [self.tmp / "audit-log-001.jsonl", self.tmp / "audit-log-002.jsonl"]
        ))
        # 10 shared + 10 unique-f1 + 10 unique-f2 = 30 (NOT 40)
        self.assertEqual(len(events), 30)

    def test_malformed_lines_skipped(self) -> None:
        path = self.tmp / "audit-log.jsonl"
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"action": "ok", "n": 1}) + "\n")
            f.write("not json garbage\n")
            f.write(json.dumps({"action": "ok", "n": 2}) + "\n")
        events = list(budget_summary.iter_unique_events([path]))
        self.assertEqual(len(events), 2)


class TestDiscoverLogs(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-discover-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_ordering_backups_first_active_last(self) -> None:
        (self.tmp / "audit-log.jsonl").write_text("")
        (self.tmp / "audit-log-2026-04-1.jsonl").write_text("")
        (self.tmp / "audit-log-2026-04-2.jsonl").write_text("")
        paths = budget_summary.discover_logs(self.tmp)
        names = [p.name for p in paths]
        # Active is last.
        self.assertEqual(names[-1], "audit-log.jsonl")
        # Backups sorted lex.
        self.assertEqual(names[0], "audit-log-2026-04-1.jsonl")
        self.assertEqual(names[1], "audit-log-2026-04-2.jsonl")

    def test_missing_dir_returns_empty(self) -> None:
        self.assertEqual(budget_summary.discover_logs(self.tmp / "nope"), [])


class TestPlanAttribution(unittest.TestCase):
    def test_explicit_plan_id_wins(self) -> None:
        events = [
            _make_event("agent_spawn", plan_id="PLAN-077", session_id="s1",
                        tokens_in=100, tokens_out=50, model="claude-opus-4-7"),
        ]
        attr = budget_summary.build_plan_attribution(events)
        self.assertEqual(attr[0], "PLAN-077")

    def test_inference_from_transition(self) -> None:
        events = [
            _make_event("plan_status_transition", plan_id="PLAN-081",
                        to_status="executing", session_id="s1"),
            _make_event("agent_spawn", session_id="s1",
                        tokens_in=100, tokens_out=50, model="claude-opus-4-7"),
        ]
        attr = budget_summary.build_plan_attribution(events)
        self.assertEqual(attr[1], "PLAN-081")

    def test_orphan_returns_none(self) -> None:
        events = [
            _make_event("agent_spawn", session_id="orphan",
                        tokens_in=100, tokens_out=50, model="claude-opus-4-7"),
        ]
        attr = budget_summary.build_plan_attribution(events)
        self.assertIsNone(attr[0])

    def test_plan_done_clears_executing(self) -> None:
        events = [
            _make_event("plan_status_transition", plan_id="PLAN-081",
                        to_status="executing", session_id="s1"),
            _make_event("agent_spawn", session_id="s1",
                        tokens_in=100, tokens_out=50, model="claude-opus-4-7"),
            _make_event("plan_status_transition", plan_id="PLAN-081",
                        to_status="done", session_id="s1"),
            _make_event("agent_spawn", session_id="s1",
                        tokens_in=100, tokens_out=50, model="claude-opus-4-7"),
        ]
        attr = budget_summary.build_plan_attribution(events)
        self.assertEqual(attr[1], "PLAN-081")
        self.assertIsNone(attr[3])

    def test_safe_plan_id_boundary(self) -> None:
        # Sec MF-3 — only canonical PLAN-NNN syntax accepted.
        self.assertEqual(budget_summary._safe_plan_id("PLAN-077"), "PLAN-077")
        self.assertIsNone(budget_summary._safe_plan_id("plan-77"))
        self.assertIsNone(budget_summary._safe_plan_id("../../etc/passwd"))
        self.assertIsNone(budget_summary._safe_plan_id(None))
        self.assertIsNone(budget_summary._safe_plan_id("PLAN-1234"))


class TestRollupAgainstFixtures(unittest.TestCase):
    """End-to-end tests against the 5-rotation fixture set.

    These are the load-bearing tests: they assert that ``budget-summary``
    reports a cumulative USD figure within the memory-claim band, that
    the dedup actually drops the 5 overlap events, and that Codex
    pair_rail_case tokens contribute.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="ceo-fixture-"))
        generate_fixtures.build_fixture_set(cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_total_cost_within_memory_band(self) -> None:
        """The headline assertion — fixture sums must land in [$1003, $1543]."""
        data = budget_summary.rollup(audit_dir=self.tmp)
        cost = data["total_cost_usd"]
        self.assertIsNotNone(cost)
        assert cost is not None
        self.assertGreaterEqual(cost, budget_summary.MEMORY_CLAIM_LOW_USD)
        self.assertLessEqual(cost, budget_summary.MEMORY_CLAIM_HIGH_USD)

    def test_validate_memory_claim_passes(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp)
        verdict = budget_summary.validate_memory_claim(data["total_cost_usd"])
        self.assertEqual(verdict["status"], "pass")

    def test_codex_events_counted(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp)
        # Fixture has 5 + 8 + 3 = 16 unique pair_rail_case events
        # (3 of the 8 in r002 are duplicated into r003, then deduped).
        self.assertEqual(data["codex_event_count"], 16)

    def test_dedup_removes_overlap_events(self) -> None:
        """Raw lines = 114; after dedup unique events = 109."""
        log_paths = budget_summary.discover_logs(self.tmp)
        # Raw line count
        raw_lines = 0
        for p in log_paths:
            with p.open("r") as f:
                raw_lines += sum(1 for _ in f)
        # Unique events
        unique = list(budget_summary.iter_unique_events(log_paths))
        # Drop exactly overlap_event_count duplicates (=5)
        self.assertEqual(raw_lines - len(unique), 5)

    def test_plan_filter_attribution(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp, plan_filter="PLAN-081")
        # PLAN-081 = 25 spawns + 8 codex = 33 events
        self.assertEqual(data["total_events"], 33)
        # No unknown contributions when filtered.
        self.assertEqual(data["unknown_plan_count"], 0)

    def test_inference_attributes_to_plan_083(self) -> None:
        """Events in r004 carry no explicit plan_id but session has
        a plan_status_transition → executing PLAN-083."""
        data = budget_summary.rollup(audit_dir=self.tmp, plan_filter="PLAN-083")
        # 10 inferred spawns (r004) + 5 active spawns + 3 active codex = 18
        self.assertEqual(data["total_events"], 18)

    def test_unknown_plan_id_minimal(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp)
        # Only the 1 deliberate orphan spawn should be unattributed.
        self.assertEqual(data["unknown_plan_count"], 1)

    def test_by_wave_aggregates(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp, by_wave=True)
        self.assertIn("per_wave", data)
        waves = {r["wave"]: r for r in data["per_wave"]}
        # Fixture has wave-0a (r001 spawns only), wave-0b, wave-1, wave-2.
        self.assertIn("wave-0a", waves)
        self.assertIn("wave-0b", waves)
        self.assertIn("wave-1", waves)
        self.assertIn("wave-2", waves)

    def test_since_filter_excludes_old(self) -> None:
        # All fixture events are in 2026-04 — using now-of-2030 returns 0.
        future = datetime(2030, 1, 1, tzinfo=timezone.utc)
        data = budget_summary.rollup(
            audit_dir=self.tmp, since=timedelta(days=1), now=future,
        )
        self.assertEqual(data["total_events"], 0)

    def test_pair_rail_case_contributes_tokens(self) -> None:
        """Codex MCP token wiring assertion (post-patch)."""
        data = budget_summary.rollup(audit_dir=self.tmp, plan_filter="PLAN-080")
        # r001 has 5 codex events of (tokens_in=80k, tokens_out=30k) each.
        # PLAN-080 has 20 spawns (tokens_in=400k) + 5 codex (tokens_in=80k).
        # 20*400k + 5*80k = 8,400k = 8.4M
        self.assertEqual(data["total_tokens_in"], 20 * 400_000 + 5 * 80_000)
        self.assertEqual(data["total_tokens_out"], 20 * 120_000 + 5 * 30_000)


class TestValidateMemoryClaim(unittest.TestCase):
    def test_pass_when_in_band(self) -> None:
        v = budget_summary.validate_memory_claim(1200.0)
        self.assertEqual(v["status"], "pass")

    def test_warn_when_far_outside(self) -> None:
        v = budget_summary.validate_memory_claim(0.28)  # the prior broken value
        self.assertEqual(v["status"], "warn")
        self.assertIn("OUTSIDE", v["message"])

    def test_unknown_when_no_cost(self) -> None:
        v = budget_summary.validate_memory_claim(None)
        self.assertEqual(v["status"], "unknown")


class TestComputeCost(unittest.TestCase):
    def test_unknown_model_returns_none(self) -> None:
        self.assertIsNone(
            budget_summary.compute_cost_usd("not-a-model", 1000, 500)
        )

    def test_opus_pricing_math(self) -> None:
        # 1000 in @ $0.015/k + 1000 out @ $0.075/k = 0.015 + 0.075 = $0.090
        cost = budget_summary.compute_cost_usd("claude-opus-4-7", 1000, 1000)
        self.assertAlmostEqual(cost, 0.090, places=4)


class TestExtractWaveId(unittest.TestCase):
    def test_explicit_field(self) -> None:
        ev = {"wave_id": "wave-0a"}
        self.assertEqual(budget_summary._extract_wave_id(ev), "wave-0a")

    def test_heuristic_from_desc_preview(self) -> None:
        ev = {"desc_preview": "PLAN-083 spawn #1 wave-0b"}
        self.assertEqual(budget_summary._extract_wave_id(ev), "wave-0b")

    def test_missing_returns_none(self) -> None:
        self.assertIsNone(budget_summary._extract_wave_id({"foo": "bar"}))


class TestJsonOutputShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="ceo-json-"))
        generate_fixtures.build_fixture_set(cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_json_output_validates_structurally(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp)
        s = budget_summary.format_json(data)
        decoded = json.loads(s)
        for key in (
            "total_tokens_in", "total_tokens_out", "total_tokens",
            "total_cost_usd", "per_plan", "per_session",
            "total_events", "codex_event_count",
        ):
            self.assertIn(key, decoded)
        self.assertIsInstance(decoded["per_plan"], list)

    def test_json_with_memory_claim_includes_validation(self) -> None:
        data = budget_summary.rollup(audit_dir=self.tmp)
        verdict = budget_summary.validate_memory_claim(data["total_cost_usd"])
        s = budget_summary.format_json(data, verdict)
        decoded = json.loads(s)
        self.assertIn("memory_claim_validation", decoded)
        self.assertEqual(decoded["memory_claim_validation"]["status"], "pass")


class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="ceo-cli-"))
        generate_fixtures.build_fixture_set(cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _silence_streams(self):
        # Helper context manager that captures stdout+stderr.
        from contextlib import redirect_stdout, redirect_stderr
        class _Both:
            def __init__(self):
                self.out = io.StringIO()
                self.err = io.StringIO()
                self._a = redirect_stdout(self.out)
                self._b = redirect_stderr(self.err)
            def __enter__(self):
                self._a.__enter__()
                self._b.__enter__()
                return self
            def __exit__(self, *a):
                self._b.__exit__(*a)
                self._a.__exit__(*a)
        return _Both()

    def test_bad_plan_id_exits_2(self) -> None:
        with self._silence_streams():
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--plan-id", "garbage",
            ])
        self.assertEqual(rc, 2)

    def test_bad_since_exits_2(self) -> None:
        with self._silence_streams():
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--since", "5z",
            ])
        self.assertEqual(rc, 2)

    def test_summary_runs_clean(self) -> None:
        with self._silence_streams() as s:
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--json",
            ])
        self.assertEqual(rc, 0)
        # JSON parses
        decoded = json.loads(s.out.getvalue())
        self.assertGreater(decoded["total_events"], 0)


class TestBenchmarkCoReport(unittest.TestCase):
    """PLAN-133 C4 — harbor-style benchmark co-report: cost + compute +
    turns alongside pass-rate. Default-OFF; --benchmarks / env opt-in."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-c4-"))
        # patch.dict restores os.environ on teardown (env-hygiene mandate); we
        # remove CEO_BUDGET_BENCHMARKS so the default-OFF path is exercised, and
        # individual tests overlay it via a nested patch.dict.
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        self.addCleanup(self._env_patch.stop)
        os.environ.pop("CEO_BUDGET_BENCHMARKS", None)
        # int-encoded (live emitter) form
        self._int_events = [
            _make_event(
                "benchmark_run", ts="2026-05-01T10:00:00Z",
                benchmark_id="owasp-basics@v1", skill="owasp-basics",
                pass_count=7, fail_count=3,
                pass_rate_bps=700, median_score_bps=720, floor_bps=600,
                cost_usd_cents=250, duration_ms=8000, lessons_written=0,
            ),
            _make_event(
                "benchmark_run", ts="2026-05-02T10:00:00Z",
                benchmark_id="owasp-basics@v1", skill="owasp-basics",
                pass_count=9, fail_count=1,
                pass_rate_bps=900, median_score_bps=910, floor_bps=600,
                cost_usd_cents=175, duration_ms=6500, lessons_written=1,
            ),
            # legacy float form (pre-migration row) — different skill
            _make_event(
                "benchmark_run", ts="2026-05-03T10:00:00Z",
                benchmark_id="testing-strategy@v1", skill="testing-strategy",
                pass_count=8, fail_count=2,
                pass_rate=0.8, median_score=0.85, floor=0.6,
                duration_s=12.5, lessons_written=2,
            ),
        ]
        _write_jsonl(self.tmp / "audit-log.jsonl", self._int_events)

    def tearDown(self) -> None:
        # os.environ is restored by the patch.dict cleanup registered in setUp.
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _silence(self):
        from contextlib import redirect_stdout, redirect_stderr

        class _Both:
            def __init__(self):
                self.out = io.StringIO()
                self.err = io.StringIO()
                self._a = redirect_stdout(self.out)
                self._b = redirect_stderr(self.err)

            def __enter__(self):
                self._a.__enter__()
                self._b.__enter__()
                return self

            def __exit__(self, *a):
                self._b.__exit__(*a)
                self._a.__exit__(*a)

        return _Both()

    # --- benchmark_rollup() unit ---

    def test_benchmark_rollup_int_encoded_cost_compute_turns(self) -> None:
        data = budget_summary.benchmark_rollup(audit_dir=self.tmp)
        rows = {r["skill"]: r for r in data["per_skill"]}
        owasp = rows["owasp-basics"]
        # cost: 250c + 175c = $4.25; latest 175c = $1.75
        self.assertAlmostEqual(owasp["total_cost_usd"], 4.25, places=6)
        self.assertAlmostEqual(owasp["latest_cost_usd"], 1.75, places=6)
        # compute: 8.0 + 6.5 = 14.5s; latest 6.5s
        self.assertAlmostEqual(owasp["total_compute_s"], 14.5, places=3)
        self.assertAlmostEqual(owasp["latest_compute_s"], 6.5, places=3)
        # turns: (7+3)+(9+1)=20; latest 10
        self.assertEqual(owasp["total_turns"], 20)
        self.assertEqual(owasp["latest_turns"], 10)
        # pass-rate co-reported (the scalar it sits alongside)
        self.assertAlmostEqual(owasp["latest_pass_rate"], 0.9, places=3)

    def test_benchmark_rollup_legacy_float_fallback(self) -> None:
        data = budget_summary.benchmark_rollup(audit_dir=self.tmp)
        rows = {r["skill"]: r for r in data["per_skill"]}
        ts = rows["testing-strategy"]
        # legacy float duration_s 12.5; no cost field → 0
        self.assertAlmostEqual(ts["total_compute_s"], 12.5, places=3)
        self.assertAlmostEqual(ts["total_cost_usd"], 0.0, places=6)
        self.assertAlmostEqual(ts["latest_pass_rate"], 0.8, places=3)
        self.assertEqual(ts["total_turns"], 10)

    def test_benchmark_rollup_totals(self) -> None:
        data = budget_summary.benchmark_rollup(audit_dir=self.tmp)
        self.assertEqual(data["skill_count"], 2)
        # $4.25 + $0 = $4.25 ; 14.5 + 12.5 = 27.0s ; 20 + 10 = 30 turns
        self.assertAlmostEqual(data["total_cost_usd"], 4.25, places=6)
        self.assertAlmostEqual(data["total_compute_s"], 27.0, places=3)
        self.assertEqual(data["total_turns"], 30)

    def test_benchmark_rollup_fail_open_on_empty(self) -> None:
        empty = Path(tempfile.mkdtemp(prefix="ceo-c4-empty-"))
        try:
            data = budget_summary.benchmark_rollup(audit_dir=empty)
            self.assertEqual(data["per_skill"], [])
            self.assertEqual(data["total_turns"], 0)
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    # --- CLI default-OFF / opt-in wiring ---

    def test_default_off_no_benchmarks_key(self) -> None:
        """Without --benchmarks the JSON output is unchanged (no key)."""
        with self._silence() as s:
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--json",
            ])
        self.assertEqual(rc, 0)
        decoded = json.loads(s.out.getvalue())
        self.assertNotIn("benchmarks", decoded)

    def test_flag_enables_benchmarks_block(self) -> None:
        with self._silence() as s:
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--json",
                "--benchmarks",
            ])
        self.assertEqual(rc, 0)
        decoded = json.loads(s.out.getvalue())
        self.assertIn("benchmarks", decoded)
        self.assertEqual(decoded["benchmarks"]["skill_count"], 2)

    def test_env_opt_in_enables_benchmarks_block(self) -> None:
        with patch.dict(os.environ, {"CEO_BUDGET_BENCHMARKS": "1"}, clear=False):
            with self._silence() as s:
                rc = budget_summary.main([
                    "summary", "--audit-dir", str(self.tmp), "--json",
                ])
        self.assertEqual(rc, 0)
        decoded = json.loads(s.out.getvalue())
        self.assertIn("benchmarks", decoded)

    def test_human_table_renders_harbor_columns(self) -> None:
        with self._silence() as s:
            rc = budget_summary.main([
                "summary", "--audit-dir", str(self.tmp), "--benchmarks",
            ])
        self.assertEqual(rc, 0)
        out = s.out.getvalue()
        self.assertIn("Benchmarks (harbor-style", out)
        for col in ("pass_rate", "cost_usd", "compute_s", "turns"):
            self.assertIn(col, out)
        self.assertIn("owasp-basics", out)


if __name__ == "__main__":
    unittest.main()
