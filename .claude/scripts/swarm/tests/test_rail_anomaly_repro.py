"""PLAN-059 Phase 0 — rail anomaly repro harness analysis tests."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Make swarm package importable
_SWARM_DIR = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _SWARM_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from swarm import test_rail_anomaly_repro as ra  # noqa: E402


# =============================================================================
# Manifest parsing
# =============================================================================


class TestManifestParsing(unittest.TestCase):

    def test_parse_minimal_row(self) -> None:
        raw = {
            "dispatch_id": "qa-001",
            "archetype": "qa-architect",
            "fixture_path": "/tmp/h4_repro_qa_001.txt",
            "expected_marker": "MARKER_001",
        }
        row = ra.parse_manifest_row(raw)
        self.assertEqual(row.dispatch_id, "qa-001")
        self.assertEqual(row.archetype, "qa-architect")
        self.assertEqual(row.fixture_path, Path("/tmp/h4_repro_qa_001.txt"))
        self.assertEqual(row.expected_marker, "MARKER_001")
        self.assertEqual(row.condition, {})
        self.assertEqual(row.dispatched_at, "")
        self.assertIsNone(row.tool_uses_reported)
        self.assertIsNone(row.duration_ms)

    def test_parse_full_row(self) -> None:
        raw = {
            "dispatch_id": "qa-002",
            "archetype": "qa-architect",
            "fixture_path": "/tmp/h4_repro_qa_002.txt",
            "expected_marker": "MARKER_002",
            "condition": {
                "model": "claude-sonnet-4-6",
                "prompt_form": "trivial",
                "parallelism": "serial",
            },
            "dispatched_at": "2026-04-25T13:00:00Z",
            "tool_uses_reported": 0,
            "duration_ms": 4027,
            "notes": "post-fix retest",
        }
        row = ra.parse_manifest_row(raw)
        self.assertEqual(row.condition["model"], "claude-sonnet-4-6")
        self.assertEqual(row.tool_uses_reported, 0)
        self.assertEqual(row.duration_ms, 4027)
        self.assertEqual(row.notes, "post-fix retest")

    def test_parse_missing_required_key_raises(self) -> None:
        raw = {
            "dispatch_id": "x",
            "archetype": "qa-architect",
            # missing fixture_path + expected_marker
        }
        with self.assertRaises(ValueError) as cm:
            ra.parse_manifest_row(raw)
        self.assertIn("fixture_path", str(cm.exception))

    def test_load_manifest_skips_blank_and_comment_lines(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write(json.dumps({
                "dispatch_id": "a",
                "archetype": "qa-architect",
                "fixture_path": "/tmp/x",
                "expected_marker": "M",
            }) + "\n")
            f.write("# another comment\n")
            f.write(json.dumps({
                "dispatch_id": "b",
                "archetype": "code-reviewer",
                "fixture_path": "/tmp/y",
                "expected_marker": "N",
            }) + "\n")
            path = Path(f.name)
        try:
            rows = ra.load_manifest(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0].dispatch_id, "a")
            self.assertEqual(rows[1].dispatch_id, "b")
        finally:
            path.unlink()

    def test_load_manifest_malformed_json_reports_line_number(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            f.write(json.dumps({
                "dispatch_id": "a",
                "archetype": "qa-architect",
                "fixture_path": "/tmp/x",
                "expected_marker": "M",
            }) + "\n")
            f.write("not valid json {{\n")
            path = Path(f.name)
        try:
            with self.assertRaises(ValueError) as cm:
                ra.load_manifest(path)
            self.assertIn("line 2", str(cm.exception))
        finally:
            path.unlink()

    def test_load_manifest_non_object_row_rejected(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            f.write('["array", "not", "object"]\n')
            path = Path(f.name)
        try:
            with self.assertRaises(ValueError) as cm:
                ra.load_manifest(path)
            self.assertIn("JSON object", str(cm.exception))
        finally:
            path.unlink()


# =============================================================================
# Scoring
# =============================================================================


class TestScoring(unittest.TestCase):

    def test_success_when_fixture_contains_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / "f.txt"
            fixture.write_text("MARKER_X here", encoding="utf-8")
            row = ra.DispatchManifestRow(
                dispatch_id="d1",
                archetype="qa-architect",
                fixture_path=fixture,
                expected_marker="MARKER_X",
            )
            result = ra.score_dispatch(row)
            self.assertTrue(result.success)
            self.assertEqual(result.failure_reason, "")

    def test_fail_fixture_missing(self) -> None:
        row = ra.DispatchManifestRow(
            dispatch_id="d1",
            archetype="qa-architect",
            fixture_path=Path("/tmp/definitely-does-not-exist-xyz123"),
            expected_marker="M",
        )
        result = ra.score_dispatch(row)
        self.assertFalse(result.success)
        self.assertEqual(result.failure_reason, "fixture_missing")

    def test_fail_marker_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / "f.txt"
            fixture.write_text("totally different content", encoding="utf-8")
            row = ra.DispatchManifestRow(
                dispatch_id="d1",
                archetype="qa-architect",
                fixture_path=fixture,
                expected_marker="MISSING_MARKER",
            )
            result = ra.score_dispatch(row)
            self.assertFalse(result.success)
            self.assertEqual(result.failure_reason, "marker_absent")

    def test_score_preserves_metadata(self) -> None:
        row = ra.DispatchManifestRow(
            dispatch_id="d1",
            archetype="qa-architect",
            fixture_path=Path("/tmp/missing-xyz"),
            expected_marker="M",
            tool_uses_reported=0,
            duration_ms=4000,
            condition={"model": "x"},
        )
        result = ra.score_dispatch(row)
        self.assertEqual(result.tool_uses_reported, 0)
        self.assertEqual(result.duration_ms, 4000)
        self.assertEqual(result.condition, {"model": "x"})

    def test_score_all_returns_one_per_row(self) -> None:
        rows = [
            ra.DispatchManifestRow(
                dispatch_id=f"d{i}",
                archetype="qa-architect",
                fixture_path=Path(f"/tmp/missing-{i}"),
                expected_marker="M",
            )
            for i in range(5)
        ]
        results = ra.score_all(rows)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(not r.success for r in results))


# =============================================================================
# Aggregation
# =============================================================================


class TestAggregation(unittest.TestCase):

    def _mk_result(
        self,
        archetype: str,
        success: bool,
        condition: dict = None,
        duration_ms: int = None,
    ) -> ra.DispatchScoreResult:
        return ra.DispatchScoreResult(
            dispatch_id=f"{archetype}-{success}",
            archetype=archetype,
            condition=condition or {},
            success=success,
            failure_reason="" if success else "fixture_missing",
            duration_ms=duration_ms,
        )

    def test_aggregate_by_cell_simple(self) -> None:
        results = [
            self._mk_result("qa-architect", True),
            self._mk_result("qa-architect", True),
            self._mk_result("qa-architect", False),
        ]
        cells = ra.aggregate_by_cell(results)
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0].archetype, "qa-architect")
        self.assertEqual(cells[0].n_total, 3)
        self.assertEqual(cells[0].n_success, 2)
        self.assertAlmostEqual(cells[0].success_rate, 2 / 3)

    def test_aggregate_by_cell_separates_conditions(self) -> None:
        results = [
            self._mk_result(
                "qa-architect", True,
                condition={"model": "claude-opus-4-7"},
            ),
            self._mk_result(
                "qa-architect", False,
                condition={"model": "claude-sonnet-4-6"},
            ),
        ]
        cells = ra.aggregate_by_cell(results)
        self.assertEqual(len(cells), 2)
        labels = {c.condition_label for c in cells}
        self.assertIn("model=opus47", labels)
        self.assertIn("model=sonnet46", labels)

    def test_aggregate_by_archetype(self) -> None:
        results = [
            self._mk_result("qa-architect", False),
            self._mk_result("qa-architect", False),
            self._mk_result("code-reviewer", True),
            self._mk_result("code-reviewer", True),
            self._mk_result("code-reviewer", True),
        ]
        agg = ra.aggregate_by_archetype(results)
        self.assertEqual(agg["qa-architect"], (2, 0, 0.0))
        self.assertEqual(agg["code-reviewer"], (3, 3, 1.0))

    def test_aggregate_by_condition_dim(self) -> None:
        results = [
            self._mk_result(
                "qa-architect", True, condition={"model": "opus-4-7"}
            ),
            self._mk_result(
                "qa-architect", False, condition={"model": "sonnet-4-6"}
            ),
            self._mk_result(
                "qa-architect", False, condition={"model": "sonnet-4-6"}
            ),
        ]
        agg = ra.aggregate_by_condition_dim(results, "model")
        self.assertEqual(agg["opus-4-7"], (1, 1, 1.0))
        self.assertEqual(agg["sonnet-4-6"], (2, 0, 0.0))

    def test_aggregate_by_condition_dim_missing_dim_bucket(self) -> None:
        results = [
            self._mk_result("qa-architect", True),
            self._mk_result(
                "qa-architect", False, condition={"model": "x"}
            ),
        ]
        agg = ra.aggregate_by_condition_dim(results, "model")
        self.assertIn("<unset>", agg)
        self.assertIn("x", agg)

    def test_median_duration_in_cell(self) -> None:
        results = [
            self._mk_result("qa-architect", True, duration_ms=100),
            self._mk_result("qa-architect", True, duration_ms=200),
            self._mk_result("qa-architect", False, duration_ms=300),
        ]
        cells = ra.aggregate_by_cell(results)
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0].median_duration_ms, 200)


# =============================================================================
# Reporting
# =============================================================================


class TestReporting(unittest.TestCase):

    def test_render_markdown_table_empty(self) -> None:
        out = ra.render_markdown_table([])
        self.assertIn("(no data)", out)

    def test_render_markdown_table_includes_archetype_and_rate(self) -> None:
        agg = [
            ra.CellAggregate(
                archetype="qa-architect",
                condition_label="default",
                n_total=2,
                n_success=1,
                success_rate=0.5,
                failure_reasons={"fixture_missing": 1},
                median_duration_ms=4000.0,
            )
        ]
        out = ra.render_markdown_table(agg)
        self.assertIn("qa-architect", out)
        self.assertIn("50%", out)
        self.assertIn("fixture_missing", out)
        self.assertIn("4000", out)

    def test_render_summary_json_structure(self) -> None:
        results = [
            ra.DispatchScoreResult(
                dispatch_id="a",
                archetype="qa-architect",
                condition={"model": "opus"},
                success=True,
            ),
            ra.DispatchScoreResult(
                dispatch_id="b",
                archetype="qa-architect",
                condition={"model": "opus"},
                success=False,
                failure_reason="fixture_missing",
            ),
        ]
        agg = ra.aggregate_by_cell(results)
        json_out = ra.render_summary_json(results, agg)
        data = json.loads(json_out)
        self.assertEqual(data["total_dispatches"], 2)
        self.assertEqual(data["total_success"], 1)
        self.assertEqual(data["total_failure"], 1)
        self.assertAlmostEqual(data["overall_success_rate"], 0.5)
        self.assertIn("by_archetype", data)
        self.assertIn("by_cell", data)


# =============================================================================
# Hypothesis discrimination
# =============================================================================


class TestHypothesisDiscrimination(unittest.TestCase):

    def _mk(self, arch: str, ok: bool, **cond) -> ra.DispatchScoreResult:
        return ra.DispatchScoreResult(
            dispatch_id=f"{arch}-{ok}",
            archetype=arch,
            condition=cond,
            success=ok,
        )

    def test_reliable_archetype_signal(self) -> None:
        """100% success rate → RELIABLE."""
        results = [
            self._mk("code-reviewer", True) for _ in range(10)
        ]
        signals = ra.discriminate_hypotheses(results)
        self.assertTrue(any(
            "code-reviewer" in s and "RELIABLE" in s
            for s in signals
        ))

    def test_degraded_archetype_signal(self) -> None:
        """0% success rate → DEGRADED."""
        results = [
            self._mk("qa-architect", False) for _ in range(10)
        ]
        signals = ra.discriminate_hypotheses(results)
        self.assertTrue(any(
            "qa-architect" in s and "DEGRADED" in s
            for s in signals
        ))

    def test_intermittent_archetype_signal(self) -> None:
        """50% success rate → INTERMITTENT."""
        results = (
            [self._mk("perf", True) for _ in range(5)]
            + [self._mk("perf", False) for _ in range(5)]
        )
        signals = ra.discriminate_hypotheses(results)
        self.assertTrue(any(
            "perf" in s and "INTERMITTENT" in s
            for s in signals
        ))

    def test_model_robustness_signal(self) -> None:
        results = (
            [self._mk("x", True, model="claude-opus-4-7") for _ in range(5)]
            + [self._mk("x", False, model="claude-sonnet-4-6") for _ in range(5)]
        )
        signals = ra.discriminate_hypotheses(results)
        opus_signals = [s for s in signals if "claude-opus" in s]
        sonnet_signals = [s for s in signals if "claude-sonnet" in s]
        self.assertTrue(any("robust" in s for s in opus_signals))
        self.assertTrue(any("exhibits-H4" in s for s in sonnet_signals))


# =============================================================================
# CLI
# =============================================================================


class TestCLI(unittest.TestCase):

    def _capture(self, argv: list) -> tuple:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            try:
                exit_code = ra._cli_main(argv)
            except SystemExit as e:
                exit_code = e.code
            stdout_val = sys.stdout.getvalue()
            stderr_val = sys.stderr.getvalue()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return exit_code, stdout_val, stderr_val

    def test_cli_missing_manifest_exits_2(self) -> None:
        exit_code, _, stderr = self._capture(["/nonexistent/manifest.jsonl"])
        self.assertEqual(exit_code, 2)
        self.assertIn("not found", stderr)

    def test_cli_empty_manifest_emits_message(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            f.write("# only comments\n")
            path = f.name
        try:
            exit_code, stdout, _ = self._capture([path])
            self.assertEqual(exit_code, 0)
            self.assertIn("empty", stdout.lower())
        finally:
            Path(path).unlink()

    def test_cli_basic_markdown_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture = Path(tmpdir) / "f.txt"
            fixture.write_text("MARKER_X", encoding="utf-8")
            manifest = Path(tmpdir) / "m.jsonl"
            manifest.write_text(json.dumps({
                "dispatch_id": "qa-001",
                "archetype": "qa-architect",
                "fixture_path": str(fixture),
                "expected_marker": "MARKER_X",
                "condition": {"model": "claude-sonnet-4-6"},
            }) + "\n", encoding="utf-8")

            exit_code, stdout, _ = self._capture([str(manifest)])
            self.assertEqual(exit_code, 0)
            self.assertIn("Rail Anomaly Empirical Results", stdout)
            self.assertIn("qa-architect", stdout)
            self.assertIn("100%", stdout)
            self.assertIn("RELIABLE", stdout)

    def test_cli_json_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = Path(tmpdir) / "m.jsonl"
            manifest.write_text(json.dumps({
                "dispatch_id": "qa-001",
                "archetype": "qa-architect",
                "fixture_path": str(Path(tmpdir) / "missing"),
                "expected_marker": "M",
            }) + "\n", encoding="utf-8")

            exit_code, stdout, _ = self._capture([
                str(manifest), "--format", "json",
            ])
            self.assertEqual(exit_code, 0)
            data = json.loads(stdout)
            self.assertEqual(data["total_dispatches"], 1)
            self.assertEqual(data["total_failure"], 1)


if __name__ == "__main__":
    unittest.main()
