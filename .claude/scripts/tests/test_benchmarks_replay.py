"""PLAN-020 Phase 6 — benchmarks/replay.py acceptance tests.

PLAN-133 C2 extension: spawn→tool-call JSON-stream record/playback
structural-equality tests (TestStreamRecordPlayback). These exercise the
same hermetic, $0, no-Anthropic-client convention that the rail benchmark
already follows.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / "benchmarks" / "replay.py"
FIXTURE = REPO_ROOT / "replay-fixtures" / "plan-019-wave-2a.jsonl"

# PLAN-133 C2 stream fixtures.
STREAM_SAMPLE = REPO_ROOT / "replay-fixtures" / "spawn-tool-stream-sample.jsonl"
STREAM_REPLAY = (
    REPO_ROOT / "replay-fixtures" / "spawn-tool-stream-sample-replay.jsonl"
)
STREAM_DIVERGENT = (
    REPO_ROOT / "replay-fixtures" / "spawn-tool-stream-sample-divergent.jsonl"
)
STREAM_GOLDEN = (
    REPO_ROOT
    / "replay-fixtures"
    / "golden"
    / "spawn-tool-stream-sample.golden.json"
)


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(REPO_ROOT),
    )


def _load_replay_module():
    """Import benchmarks/replay.py as a module for pure-function unit tests."""
    spec = importlib.util.spec_from_file_location("benchmarks_replay", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ReplayBenchmarkTest(unittest.TestCase):

    def test_replay_both_rails_default(self):
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["rail"], "both")
        self.assertIn("inline", data["results"])
        self.assertIn("reference", data["results"])

    def test_inline_rail_only(self):
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)), "--rail", "inline")
        data = json.loads(result.stdout)
        self.assertEqual(data["rail"], "inline")
        self.assertIn("inline", data["results"])
        self.assertNotIn("reference", data["results"])

    def test_reference_rail_only(self):
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)), "--rail", "reference")
        data = json.loads(result.stdout)
        self.assertEqual(data["rail"], "reference")
        self.assertIn("reference", data["results"])

    def test_a4_acceptance_passes_on_wave_2a_fixture(self):
        # A4 sub-target from PLAN-020 §6: ≥20% reduction on reference rail
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)))
        data = json.loads(result.stdout)
        self.assertIn("delta_pct_savings", data)
        self.assertGreaterEqual(
            data["delta_pct_savings"],
            20.0,
            msg=f"A4 acceptance failed: {data['delta_pct_savings']}% < 20% target",
        )
        self.assertTrue(data["a4_acceptance_pass"])

    def test_n_spawns_matches_fixture(self):
        # Fixture has 12 spawn entries
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)))
        data = json.loads(result.stdout)
        self.assertEqual(data["n_spawns"], 12)

    def test_reference_avg_smaller_than_inline_avg(self):
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)))
        data = json.loads(result.stdout)
        inline_avg = data["results"]["inline"]["avg_per_spawn_tokens"]
        ref_avg = data["results"]["reference"]["avg_per_spawn_tokens"]
        self.assertLess(ref_avg, inline_avg)


class TestStreamRecordPlayback(unittest.TestCase):
    """PLAN-133 C2 — spawn→tool-call JSON-stream record/playback."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_replay_module()

    # ---- pure-function unit tests (no subprocess) --------------------

    def test_canonical_event_drops_volatile_keys(self):
        ev = {
            "event": "agent_spawn",
            "spawn_id": 1,
            "tool": "Read",
            "ts": "2026-06-08T10:00:00Z",
            "session_id": "s1",
            "request_id": "r1",
            "tokens_in": 100,
            "tokens_out": 50,
            "tokens_total": 150,
            "duration_ms": 42,
            "cost_usd_cents": 3,
            "pid": 999,
        }
        canon = self.mod.canonical_event(ev)
        for vol in (
            "ts",
            "session_id",
            "request_id",
            "tokens_in",
            "tokens_out",
            "tokens_total",
            "duration_ms",
            "cost_usd_cents",
            "pid",
        ):
            self.assertNotIn(vol, canon)
        # Structural fields survive.
        self.assertEqual(canon["event"], "agent_spawn")
        self.assertEqual(canon["spawn_id"], 1)
        self.assertEqual(canon["tool"], "Read")

    def test_canonical_event_recurses_into_nested_dicts(self):
        ev = {
            "tool": "Edit",
            "args": {"file_path": "x.py", "request_id": "nested-req"},
        }
        canon = self.mod.canonical_event(ev)
        # request_id is volatile even nested.
        self.assertNotIn("request_id", canon["args"])
        self.assertEqual(canon["args"]["file_path"], "x.py")

    def test_stream_digest_stable_across_key_order(self):
        a = [{"event": "x", "spawn_id": 1, "tool": "Read"}]
        b = [{"tool": "Read", "spawn_id": 1, "event": "x"}]
        self.assertEqual(
            self.mod.stream_digest(a), self.mod.stream_digest(b)
        )

    def test_stream_digest_invariant_to_volatile_fields(self):
        a = [{"event": "x", "spawn_id": 1, "ts": "t1", "tokens_in": 1}]
        b = [{"event": "x", "spawn_id": 1, "ts": "t9", "tokens_in": 999}]
        self.assertEqual(
            self.mod.stream_digest(a), self.mod.stream_digest(b)
        )

    def test_stream_digest_sensitive_to_structural_change(self):
        a = [{"event": "x", "spawn_id": 1, "tool": "Read"}]
        b = [{"event": "x", "spawn_id": 1, "tool": "Write"}]
        self.assertNotEqual(
            self.mod.stream_digest(a), self.mod.stream_digest(b)
        )

    def test_stream_digest_sensitive_to_order(self):
        a = [{"event": "a"}, {"event": "b"}]
        b = [{"event": "b"}, {"event": "a"}]
        # Event ORDER is the contract — reordering must change the digest.
        self.assertNotEqual(
            self.mod.stream_digest(a), self.mod.stream_digest(b)
        )

    def test_playback_pure_match_on_volatile_only_diff(self):
        golden_events = [{"event": "x", "spawn_id": 1, "ts": "t1"}]
        cand_events = [{"event": "x", "spawn_id": 1, "ts": "t2"}]
        golden = self.mod.build_golden(golden_events)
        report = self.mod.playback(cand_events, golden)
        self.assertTrue(report["match"])

    def test_playback_pure_reports_first_divergence(self):
        golden_events = [
            {"event": "a", "tool": "Read"},
            {"event": "b", "tool": "Bash"},
        ]
        cand_events = [
            {"event": "a", "tool": "Read"},
            {"event": "b", "tool": "Write"},
        ]
        golden = self.mod.build_golden(golden_events)
        report = self.mod.playback(cand_events, golden)
        self.assertFalse(report["match"])
        self.assertEqual(report["divergence"]["kind"], "event_mismatch")
        self.assertEqual(report["divergence"]["index"], 1)

    def test_playback_pure_reports_length_mismatch(self):
        golden = self.mod.build_golden([{"event": "a"}])
        report = self.mod.playback(
            [{"event": "a"}, {"event": "b"}], golden
        )
        self.assertFalse(report["match"])
        self.assertEqual(report["divergence"]["kind"], "length_mismatch")

    # ---- end-to-end subprocess tests (CLI contract) -----------------

    def test_record_then_playback_self_matches(self):
        with tempfile.TemporaryDirectory() as td:
            golden = Path(td) / "g.json"
            rec = _run(
                "record",
                str(STREAM_SAMPLE.relative_to(REPO_ROOT)),
                "--golden",
                str(golden),
            )
            self.assertEqual(rec.returncode, 0, msg=rec.stderr)
            self.assertTrue(golden.is_file())
            pb = _run(
                "playback",
                str(STREAM_SAMPLE.relative_to(REPO_ROOT)),
                "--golden",
                str(golden),
            )
            self.assertEqual(pb.returncode, 0, msg=pb.stderr)
            self.assertTrue(json.loads(pb.stdout)["match"])

    def test_playback_replay_candidate_matches_committed_golden(self):
        # The committed golden + a volatile-only-different replay candidate
        # must compare equal (the C2 acceptance signal).
        self.assertTrue(STREAM_GOLDEN.is_file(), "committed golden missing")
        pb = _run(
            "playback",
            str(STREAM_REPLAY.relative_to(REPO_ROOT)),
            "--golden",
            str(STREAM_GOLDEN.relative_to(REPO_ROOT)),
        )
        self.assertEqual(pb.returncode, 0, msg=pb.stderr)
        self.assertTrue(json.loads(pb.stdout)["match"])

    def test_playback_divergent_candidate_fails_exit_2(self):
        pb = _run(
            "playback",
            str(STREAM_DIVERGENT.relative_to(REPO_ROOT)),
            "--golden",
            str(STREAM_GOLDEN.relative_to(REPO_ROOT)),
        )
        self.assertEqual(pb.returncode, 2, msg=pb.stdout)
        report = json.loads(pb.stdout)
        self.assertFalse(report["match"])
        self.assertEqual(report["divergence"]["index"], 4)

    def test_committed_golden_is_in_sync_with_sample_fixture(self):
        # Regression guard: if someone edits the sample fixture's STRUCTURE
        # without re-recording, this reddens (the golden is the contract).
        pb = _run(
            "playback",
            str(STREAM_SAMPLE.relative_to(REPO_ROOT)),
            "--golden",
            str(STREAM_GOLDEN.relative_to(REPO_ROOT)),
        )
        self.assertEqual(pb.returncode, 0, msg=pb.stdout)

    def test_playback_missing_fixture_is_infra_error_exit_1(self):
        # Fail-open-on-infra: a missing fixture is exit 1 (infra), NOT exit 2
        # (a structural failure) — it must not masquerade as a real regression.
        pb = _run(
            "playback",
            "replay-fixtures/does-not-exist.jsonl",
            "--golden",
            str(STREAM_GOLDEN.relative_to(REPO_ROOT)),
        )
        self.assertEqual(pb.returncode, 1)

    def test_playback_missing_golden_is_infra_error_exit_1(self):
        pb = _run(
            "playback",
            str(STREAM_SAMPLE.relative_to(REPO_ROOT)),
            "--golden",
            "replay-fixtures/golden/nope.golden.json",
        )
        self.assertEqual(pb.returncode, 1)

    def test_no_anthropic_client_constructed(self):
        # C2 is $0 hermetic: the module must not import or construct any
        # Anthropic client. Assert the source carries no such dependency.
        src = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("import anthropic", src)
        self.assertNotIn("Anthropic(", src)

    def test_legacy_rail_benchmark_still_default(self):
        # The C2 subcommand must NOT change the legacy invocation: a bare
        # fixture path still runs the rail benchmark.
        result = _run(str(FIXTURE.relative_to(REPO_ROOT)))
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["schema"], "benchmarks-replay.v1")


if __name__ == "__main__":
    unittest.main()
