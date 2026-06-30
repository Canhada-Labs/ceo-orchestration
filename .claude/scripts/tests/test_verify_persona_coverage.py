"""Tests for verify-persona-coverage.py — PLAN-088 W5.1 / AC1-AC4 closure."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_THIS = Path(__file__).resolve()
_SCRIPT = _THIS.parent.parent / "verify-persona-coverage.py"


def _load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_persona_coverage", str(_SCRIPT)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verifier = _load_verifier_module()


def _build_fixture_pass() -> str:
    """All 4 personas meet thresholds (12/13 for vibecoder; 11/13 others)."""
    return """axes: [B.1, B.10, B.14, B.13, B.11, B.12, B.2, B.6, B.7, B.3, B.4, B.5, B.8]
personas:
  vibecoder:
    B.1: AUTO
    B.10: AUTO
    B.14: SEMI
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: AUTO
    B.6: SEMI
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: AUTO
    B.8: MANUAL
  junior_dev:
    B.1: AUTO
    B.10: AUTO
    B.14: SEMI
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: AUTO
    B.6: SEMI
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: MANUAL
    B.8: MANUAL
  skeptical_cto:
    B.1: AUTO
    B.10: AUTO
    B.14: AUTO
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: SEMI
    B.6: SEMI
    B.7: MANUAL
    B.3: AUTO
    B.4: AUTO
    B.5: AUTO
    B.8: MANUAL
  team_member:
    B.1: AUTO
    B.10: AUTO
    B.14: SEMI
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: AUTO
    B.6: SEMI
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: MANUAL
    B.8: MANUAL
"""


def _build_fixture_vibe_fail() -> str:
    """vibecoder has only 10/13 AUTO+SEMI (below 12/13 threshold)."""
    return """axes: [B.1, B.10, B.14, B.13, B.11, B.12, B.2, B.6, B.7, B.3, B.4, B.5, B.8]
personas:
  vibecoder:
    B.1: AUTO
    B.10: AUTO
    B.14: MANUAL
    B.13: AUTO
    B.11: AUTO
    B.12: MANUAL
    B.2: AUTO
    B.6: MANUAL
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: AUTO
    B.8: AUTO
  junior_dev:
    B.1: AUTO
    B.10: AUTO
    B.14: SEMI
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: AUTO
    B.6: SEMI
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: MANUAL
    B.8: MANUAL
  skeptical_cto:
    B.1: AUTO
    B.10: AUTO
    B.14: AUTO
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: SEMI
    B.6: SEMI
    B.7: MANUAL
    B.3: AUTO
    B.4: AUTO
    B.5: AUTO
    B.8: MANUAL
  team_member:
    B.1: AUTO
    B.10: AUTO
    B.14: SEMI
    B.13: AUTO
    B.11: AUTO
    B.12: AUTO
    B.2: AUTO
    B.6: SEMI
    B.7: SEMI
    B.3: AUTO
    B.4: SEMI
    B.5: MANUAL
    B.8: MANUAL
"""


def _build_thresholds() -> str:
    return """thresholds:
  vibecoder:
    min_auto_semi: 12
    target_pct: 92.3
  junior_dev:
    min_auto_semi: 11
    target_pct: 84.6
  skeptical_cto:
    min_auto_semi: 11
    target_pct: 84.6
  team_member:
    min_auto_semi: 11
    target_pct: 84.6
total_axes: 13
"""


class _Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="ppc-")
        self.fixture_path = Path(self.tmp) / "fixture.yaml"
        self.thresholds_path = Path(self.tmp) / "thresholds.yaml"
        self.thresholds_path.write_text(_build_thresholds(), encoding="utf-8")
        self.last_stdout = ""
        self.last_stderr = ""

    def write_fixture(self, text: str) -> None:
        self.fixture_path.write_text(text, encoding="utf-8")

    def run(self, persona=None) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = verifier.verify_all(
                self.fixture_path, self.thresholds_path,
                selected_persona=persona,
            )
        self.last_stdout = out.getvalue()
        self.last_stderr = err.getvalue()
        return rc

    def cleanup(self) -> None:
        try:
            for p in [self.fixture_path, self.thresholds_path]:
                if p.exists():
                    p.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass


class TestVerifyPersonaCoverage(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()

    def tearDown(self) -> None:
        self.fx.cleanup()

    def test_all_4_personas_meet_thresholds(self) -> None:
        self.fx.write_fixture(_build_fixture_pass())
        rc = self.fx.run()
        self.assertEqual(rc, 0,
                         "expected PASS; stderr=%r stdout=%r"
                         % (self.fx.last_stderr, self.fx.last_stdout))
        self.assertIn("PASS", self.fx.last_stdout)

    def test_vibecoder_below_threshold_fails(self) -> None:
        self.fx.write_fixture(_build_fixture_vibe_fail())
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("vibecoder", self.fx.last_stdout)
        self.assertIn("FAIL", self.fx.last_stdout)

    def test_selected_persona_only(self) -> None:
        self.fx.write_fixture(_build_fixture_pass())
        rc = self.fx.run(persona="vibecoder")
        self.assertEqual(rc, 0)
        self.assertIn("vibecoder", self.fx.last_stdout)
        # Other personas should NOT appear in output
        self.assertNotIn("junior_dev", self.fx.last_stdout)

    def test_missing_fixture_returns_2(self) -> None:
        # Run with non-existent fixture path
        rc = verifier.verify_all(
            Path("/nonexistent/fixture.yaml"),
            self.fx.thresholds_path,
        )
        self.assertEqual(rc, 2)

    def test_unknown_persona_returns_2(self) -> None:
        self.fx.write_fixture(_build_fixture_pass())
        rc = self.fx.run(persona="cto")  # unknown alias
        self.assertEqual(rc, 2)


def _evt(action: str, persona: str, cell: str) -> str:
    return json.dumps({
        "action": action,
        "expected_persona": persona,
        "demand_event_type": cell,
        "session_id": "s-test",
        "project": "ceo-orchestration",
    })


class TestVerifyPersonaCoverageLiveMode(unittest.TestCase):
    """PLAN-136 F2 — live mode aggregates audit-log persona demand events."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="ppc-live-")
        self.audit_log = Path(self.tmp) / "audit-log.jsonl"
        self.thresholds_path = Path(self.tmp) / "thresholds.yaml"
        # Single-persona threshold so a small fixture can pass: vibecoder
        # needs >= 2 AUTO+SEMI cells in this test threshold file.
        self.thresholds_path.write_text(
            "thresholds:\n"
            "  vibecoder:\n"
            "    min_auto_semi: 2\n"
            "    target_pct: 100.0\n"
            "total_axes: 3\n",
            encoding="utf-8",
        )
        # Reuse the CI fixture/thresholds for fallback-path assertions.
        self.fixture_path = Path(self.tmp) / "fixture.yaml"
        self.fixture_path.write_text(_build_fixture_pass(), encoding="utf-8")
        self.last_stdout = ""
        self.last_stderr = ""

    def tearDown(self) -> None:
        try:
            for p in [self.audit_log, self.thresholds_path, self.fixture_path]:
                if p.exists():
                    p.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass

    def _run_live(self, persona=None, audit_log=None, fixture=None,
                  thresholds=None) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = verifier.verify_all_live(
                audit_log if audit_log is not None else self.audit_log,
                thresholds if thresholds is not None else self.thresholds_path,
                fixture if fixture is not None else self.fixture_path,
                selected_persona=persona,
            )
        self.last_stdout = out.getvalue()
        self.last_stderr = err.getvalue()
        return rc

    def test_live_aggregation_matched_is_auto(self) -> None:
        # 2 matched cells -> 2 AUTO >= threshold(2) -> PASS for vibecoder.
        self.audit_log.write_text(
            "\n".join([
                _evt("persona_demand_opened", "vibecoder", "branch_ahead"),
                _evt("persona_demand_matched", "vibecoder", "branch_ahead"),
                _evt("persona_demand_opened", "vibecoder", "plan_draft"),
                _evt("persona_demand_matched", "vibecoder", "plan_draft"),
            ]) + "\n",
            encoding="utf-8",
        )
        rc = self._run_live(persona="vibecoder")
        self.assertEqual(rc, 0,
                         "expected PASS; stderr=%r stdout=%r"
                         % (self.last_stderr, self.last_stdout))
        self.assertIn("LIVE mode", self.last_stdout)
        self.assertIn("AUTO=2", self.last_stdout)

    def test_live_opened_only_is_semi(self) -> None:
        # opened-but-never-matched -> SEMI; still counts toward AUTO+SEMI.
        self.audit_log.write_text(
            "\n".join([
                _evt("persona_demand_opened", "vibecoder", "branch_ahead"),
                _evt("persona_demand_opened", "vibecoder", "plan_draft"),
            ]) + "\n",
            encoding="utf-8",
        )
        rc = self._run_live(persona="vibecoder")
        self.assertEqual(rc, 0,
                         "expected PASS; stderr=%r stdout=%r"
                         % (self.last_stderr, self.last_stdout))
        self.assertIn("SEMI=2", self.last_stdout)

    def test_live_below_threshold_fails(self) -> None:
        # Only 1 matched cell -> AUTO=1 < threshold(2) -> FAIL.
        self.audit_log.write_text(
            _evt("persona_demand_matched", "vibecoder", "branch_ahead") + "\n",
            encoding="utf-8",
        )
        rc = self._run_live(persona="vibecoder")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", self.last_stdout)

    def test_live_missing_audit_log_falls_back_to_fixture(self) -> None:
        missing = Path(self.tmp) / "does-not-exist.jsonl"
        # Use CI fixture + its matching thresholds for the fallback path.
        ci_thresholds = Path(self.tmp) / "ci-thresholds.yaml"
        ci_thresholds.write_text(_build_thresholds(), encoding="utf-8")
        rc = self._run_live(audit_log=missing, thresholds=ci_thresholds)
        self.assertEqual(rc, 0,
                         "expected fixture-fallback PASS; stderr=%r"
                         % self.last_stderr)
        self.assertIn("falling back to fixture", self.last_stderr)

    def test_live_empty_audit_log_falls_back(self) -> None:
        self.audit_log.write_text("", encoding="utf-8")
        ci_thresholds = Path(self.tmp) / "ci-thresholds.yaml"
        ci_thresholds.write_text(_build_thresholds(), encoding="utf-8")
        rc = self._run_live(thresholds=ci_thresholds)
        self.assertEqual(rc, 0)
        self.assertIn("falling back to fixture", self.last_stderr)

    def test_live_malformed_line_skipped(self) -> None:
        # A truncated/garbage line must not crash aggregation (fail-open).
        self.audit_log.write_text(
            _evt("persona_demand_matched", "vibecoder", "branch_ahead") + "\n"
            + "{not valid json\n"
            + _evt("persona_demand_matched", "vibecoder", "plan_draft") + "\n",
            encoding="utf-8",
        )
        rc = self._run_live(persona="vibecoder")
        self.assertEqual(rc, 0,
                         "expected PASS despite malformed line; stderr=%r"
                         % self.last_stderr)
        self.assertIn("AUTO=2", self.last_stdout)

    def test_live_unobserved_persona_returns_2(self) -> None:
        self.audit_log.write_text(
            _evt("persona_demand_matched", "vibecoder", "branch_ahead") + "\n",
            encoding="utf-8",
        )
        rc = self._run_live(persona="junior_dev")
        self.assertEqual(rc, 2)

    def test_aggregate_observed_state_shape(self) -> None:
        # The aggregated dict must match the fixture observed-state shape.
        self.audit_log.write_text(
            "\n".join([
                _evt("persona_demand_opened", "vibecoder", "branch_ahead"),
                _evt("persona_demand_matched", "vibecoder", "branch_ahead"),
                _evt("persona_demand_opened", "vibecoder", "plan_draft"),
            ]) + "\n",
            encoding="utf-8",
        )
        observed = verifier._aggregate_live_observed_state(self.audit_log)
        self.assertIsNotNone(observed)
        self.assertIn("axes", observed)
        self.assertIn("personas", observed)
        self.assertIn("vibecoder", observed["personas"])
        cells = observed["personas"]["vibecoder"]
        self.assertEqual(cells["branch_ahead"], "AUTO")
        self.assertEqual(cells["plan_draft"], "SEMI")


def _write_canonical_axes_fixture(path) -> None:
    """Fixture whose `axes` is the canonical 13-axis list (B.1..B.8).

    Live mode seeds its matrix from these axes + the 4 threshold
    personas; we only need a valid `axes` + `personas` shape so
    _load_fixture accepts it.
    """
    path.write_text(_build_fixture_pass(), encoding="utf-8")


def _evt_match(persona: str, cell: str) -> str:
    return _evt("persona_demand_matched", persona, cell)


class TestVerifyPersonaCoveragePartialMatrix(unittest.TestCase):
    """PLAN-136 F2 Codex P1 — live mode must NOT false-pass when the
    audit-log covers only some of the canonical 4-persona / N-axis
    contract. Absent personas/cells are seeded MANUAL and counted, so
    incomplete coverage FAILS exactly like fixture mode would.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="ppc-partial-")
        self.audit_log = Path(self.tmp) / "audit-log.jsonl"
        # Canonical 4-persona thresholds (12/13 + 11/13 x3).
        self.thresholds_path = Path(self.tmp) / "thresholds.yaml"
        self.thresholds_path.write_text(_build_thresholds(), encoding="utf-8")
        # Canonical 13-axis fixture (seeds the live axis columns).
        self.fixture_path = Path(self.tmp) / "fixture.yaml"
        _write_canonical_axes_fixture(self.fixture_path)
        # Canonical axes (matches the fixture axes list).
        self.axes = ["B.1", "B.10", "B.14", "B.13", "B.11", "B.12",
                     "B.2", "B.6", "B.7", "B.3", "B.4", "B.5", "B.8"]
        self.last_stdout = ""
        self.last_stderr = ""

    def tearDown(self) -> None:
        try:
            for p in [self.audit_log, self.thresholds_path, self.fixture_path]:
                if p.exists():
                    p.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass

    def _run_live(self, persona=None) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = verifier.verify_all_live(
                self.audit_log,
                self.thresholds_path,
                self.fixture_path,
                selected_persona=persona,
            )
        self.last_stdout = out.getvalue()
        self.last_stderr = err.getvalue()
        return rc

    def _full_matrix_events(self):
        """All 4 personas, all 13 axes matched (AUTO) -> every persona at
        13/13 >= its threshold."""
        lines = []
        for persona in ("vibecoder", "junior_dev", "skeptical_cto",
                        "team_member"):
            for cell in self.axes:
                lines.append(_evt_match(persona, cell))
        return "\n".join(lines) + "\n"

    def test_partial_coverage_one_persona_fails_not_passes(self) -> None:
        # Only vibecoder appears in the log, fully covered (13 AUTO).
        # The other 3 canonical personas never appear. WITHOUT seeding,
        # the verifier would report PASS "all 1 persona(s)" (false-pass).
        # WITH the fix, the absent personas are scored all-MANUAL and the
        # contract FAILS (exit 1).
        lines = [_evt_match("vibecoder", cell) for cell in self.axes]
        self.audit_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = self._run_live()
        self.assertEqual(
            rc, 1,
            "partial coverage (1/4 personas) must FAIL, not false-pass; "
            "stdout=%r stderr=%r" % (self.last_stdout, self.last_stderr),
        )
        # The 3 unobserved canonical personas must appear as FAILs.
        for absent in ("junior_dev", "skeptical_cto", "team_member"):
            self.assertIn(absent, self.last_stdout)
        self.assertIn("FAIL", self.last_stdout)
        # And it must NOT claim "all 1 persona(s)".
        self.assertNotIn("all 1 persona", self.last_stdout)

    def test_full_coverage_all_personas_passes(self) -> None:
        # All 4 personas fully covered -> exit 0.
        self.audit_log.write_text(self._full_matrix_events(), encoding="utf-8")
        rc = self._run_live()
        self.assertEqual(
            rc, 0,
            "full coverage must PASS; stdout=%r stderr=%r"
            % (self.last_stdout, self.last_stderr),
        )
        self.assertIn("PASS", self.last_stdout)
        for persona in ("vibecoder", "junior_dev", "skeptical_cto",
                        "team_member"):
            self.assertIn(persona, self.last_stdout)

    def test_partial_axis_coverage_one_persona_fails(self) -> None:
        # All 4 personas appear, but only 2 of 13 axes are matched for
        # each -> 2/13 << threshold -> every persona FAILS (exit 1).
        lines = []
        for persona in ("vibecoder", "junior_dev", "skeptical_cto",
                        "team_member"):
            lines.append(_evt_match(persona, "B.1"))
            lines.append(_evt_match(persona, "B.2"))
        self.audit_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = self._run_live()
        self.assertEqual(rc, 1,
                         "partial AXIS coverage must FAIL; stdout=%r"
                         % self.last_stdout)
        # Each persona row reports total=2 of the canonical 13 axes.
        self.assertIn("/13", self.last_stdout)

    def test_selected_canonical_persona_absent_fails_not_config_error(self) -> None:
        # --persona junior_dev, but the log only has vibecoder. junior_dev
        # is in the canonical threshold contract, so it must FAIL as an
        # all-MANUAL row (exit 1), NOT a config error (exit 2).
        lines = [_evt_match("vibecoder", cell) for cell in self.axes]
        self.audit_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        rc = self._run_live(persona="junior_dev")
        self.assertEqual(
            rc, 1,
            "absent canonical persona must FAIL (1), not config-error (2); "
            "stdout=%r stderr=%r" % (self.last_stdout, self.last_stderr),
        )
        self.assertIn("junior_dev", self.last_stdout)
        self.assertIn("FAIL", self.last_stdout)


class TestCanonicalAxesFromRealFixture(unittest.TestCase):
    """Codex R2 P1 regression guard: the canonical axis set MUST be recovered
    from the SHIPPED fixture, whose `axes:` is a YAML block-sequence the basic
    parser does not surface as a Python list. Before the fix, axes seeded
    EMPTY and a partial live matrix could FALSE-PASS by omission. The agent's
    own tests used INLINE `axes: [..]` fixtures (which the parser does read),
    so they missed this — only the real fixture exercises the block path."""

    def test_real_fixture_block_sequence_axes_recovered(self) -> None:
        repo_root = _THIS.parents[3]
        fixture = repo_root / "tests" / "fixtures" / "persona-scenario-suite.yaml"
        if not fixture.exists():
            self.skipTest("shipped fixture not found: %s" % fixture)
        thresholds = verifier._load_thresholds(
            repo_root / ".claude" / "scripts" / "fixtures"
            / "persona-coverage-expected-thresholds.yaml"
        )
        axes, personas = verifier._canonical_axes_and_personas(fixture, thresholds)
        self.assertGreaterEqual(
            len(axes), 13,
            "canonical axes empty/short — block-sequence `axes:` not recovered "
            "(the Codex R2 P1 regression); got %r" % axes,
        )
        self.assertEqual(
            len(personas), 4, "expected 4 canonical personas, got %r" % personas
        )


if __name__ == "__main__":
    unittest.main()
