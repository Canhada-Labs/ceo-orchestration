"""Unit tests for compare-adopters.py.

Covers CLI parsing, schema tolerance, window-check gate, delta
semantics for count/rate/ratio metrics, null propagation, markdown
table rendering, custom-skills and ADR diffs, and JSON output.

All tests are self-contained (tempfile-scoped) and deterministic.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPT = Path(__file__).resolve().parent.parent / "compare-adopters.py"
_spec = importlib.util.spec_from_file_location("compare_adopters", _SCRIPT)
cmp_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmp_mod)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_report(
    adopter_name: str = "adopter-1",
    window: str = "7d",
    sessions: Optional[int] = 15,
    spawns_total: Optional[int] = 87,
    veto_rate: Optional[float] = 0.033,
    completion_ratio: Optional[float] = 0.857,
    tokens_ratio: Optional[float] = 1.136,
    custom_skills_count: Optional[int] = 2,
    custom_skills_names: Optional[List[str]] = None,
    adrs_distinct: Optional[int] = 4,
    adrs_total: Optional[int] = 14,
    adrs_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if custom_skills_names is None:
        custom_skills_names = ["ledger-specific-skill", "adopter-1-audit-patterns"]
    if adrs_names is None:
        adrs_names = ["ADR-023", "ADR-040", "ADR-045", "ADR-048"]
    return {
        "adopter_name": adopter_name,
        "window": window,
        "window_start": "2026-04-20T00:00:00Z",
        "window_end": "2026-04-27T00:00:00Z",
        "generated_at": "2026-04-27T18:05:00Z",
        "sessions": sessions,
        "spawns_total": spawns_total,
        "veto": {
            "vetoes": 3,
            "spawns_plus_vetoes": 90,
            "rate": veto_rate,
        },
        "completion": {
            "done": 12,
            "abandoned": 2,
            "denom": 14,
            "ratio": completion_ratio,
        },
        "tokens": {
            "actual_total": 125000,
            "predicted_total": 110000,
            "ratio": tokens_ratio,
        },
        "custom_skills": {
            "count": custom_skills_count,
            "names": custom_skills_names,
        },
        "adrs": {
            "total_mentions": adrs_total,
            "distinct_count": adrs_distinct,
            "names": adrs_names,
        },
    }


class _TmpCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="cmp-adopters-"))

    def _write_json(self, filename: str, payload: Dict[str, Any]) -> Path:
        p = self.tmp / filename
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def _run(self, argv: List[str], now: str = "2026-04-27T19:00:00Z") -> int:
        return cmp_mod._run(argv, now=now)

    def _capture(self, argv: List[str], now: str = "2026-04-27T19:00:00Z"):
        out_buf = io.StringIO()
        err_buf = io.StringIO()
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            rc = self._run(argv, now=now)
        return rc, out_buf.getvalue(), err_buf.getvalue()


# ---------------------------------------------------------------------------
# 1. CLI parsing (3 tests)
# ---------------------------------------------------------------------------


class TestCLIParsing(_TmpCase):
    def test_rejects_fewer_than_two_inputs(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        rc, _, err = self._capture(["--input", "a={0}".format(a)])
        self.assertEqual(rc, 1)
        self.assertIn("at least twice", err)

    def test_rejects_bad_name_equals_path_syntax(self):
        # NAME=PATH with empty name.
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, _, err = self._capture([
            "--input", "=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 1)
        self.assertIn("name cannot be empty", err)

    def test_rejects_baseline_not_in_inputs(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--baseline", "nonexistent",
        ])
        self.assertEqual(rc, 1)
        self.assertIn("not among --input names", err)


# ---------------------------------------------------------------------------
# 2. JSON schema tolerance (2 tests)
# ---------------------------------------------------------------------------


class TestSchemaTolerance(_TmpCase):
    def test_missing_optional_fields_graceful(self):
        # Drop 'names' in ADRs and veto.rate entirely.
        report_a = _sample_report(adopter_name="a")
        report_a["adrs"].pop("names", None)
        report_a["veto"].pop("rate", None)
        report_b = _sample_report(adopter_name="b")
        a = self._write_json("a.json", report_a)
        b = self._write_json("b.json", report_b)
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        # Missing veto.rate surfaces as N/A in baseline column.
        self.assertIn("Veto rate", out)
        self.assertIn("N/A", out)

    def test_extra_unknown_fields_ignored(self):
        # Add extras at several nesting levels.
        report_a = _sample_report(adopter_name="a")
        report_a["unknown_top"] = {"deep": 42}
        report_a["veto"]["unknown_nested"] = "noise"
        report_b = _sample_report(adopter_name="b")
        a = self._write_json("a.json", report_a)
        b = self._write_json("b.json", report_b)
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertNotIn("unknown_top", out)
        self.assertNotIn("unknown_nested", out)


# ---------------------------------------------------------------------------
# 3. Window-check gate (2 tests)
# ---------------------------------------------------------------------------


class TestWindowCheck(_TmpCase):
    def test_window_check_fails_on_mismatch(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a", window="7d"))
        b = self._write_json("b.json", _sample_report(adopter_name="b", window="14d"))
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--window-check",
        ])
        self.assertEqual(rc, 3)
        self.assertIn("windows differ", err)

    def test_window_check_passes_on_uniform(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a", window="7d"))
        b = self._write_json("b.json", _sample_report(adopter_name="b", window="7d"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--window-check",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("**Window:** 7d", out)


# ---------------------------------------------------------------------------
# 4. Count delta (2 tests)
# ---------------------------------------------------------------------------


class TestCountDelta(unittest.TestCase):
    def test_positive_delta_signed(self):
        self.assertEqual(cmp_mod._delta_count(10, 15), "+5")

    def test_negative_and_zero_delta(self):
        self.assertEqual(cmp_mod._delta_count(10, 7), "-3")
        self.assertEqual(cmp_mod._delta_count(5, 5), "+0")


# ---------------------------------------------------------------------------
# 5. Rate delta (pp) (2 tests)
# ---------------------------------------------------------------------------


class TestRateDelta(unittest.TestCase):
    def test_rate_delta_percentage_points(self):
        # 0.033 -> 0.078 = +4.5 pp
        self.assertEqual(cmp_mod._delta_pp(0.033, 0.078), "+4.5 pp")
        # 0.100 -> 0.050 = -5.0 pp
        self.assertEqual(cmp_mod._delta_pp(0.100, 0.050), "-5.0 pp")

    def test_rate_delta_null_baseline_yields_em_dash(self):
        self.assertEqual(cmp_mod._delta_pp(None, 0.050), cmp_mod.EM_DASH)


# ---------------------------------------------------------------------------
# 6. Ratio delta (1 test)
# ---------------------------------------------------------------------------


class TestRatioDelta(unittest.TestCase):
    def test_ratio_delta_three_decimals(self):
        # 1.136 -> 1.012 = -0.124
        self.assertEqual(cmp_mod._delta_ratio(1.136, 1.012), "-0.124")
        # 1.000 -> 1.050 = +0.050
        self.assertEqual(cmp_mod._delta_ratio(1.000, 1.050), "+0.050")


# ---------------------------------------------------------------------------
# 7. Null propagation (3 tests)
# ---------------------------------------------------------------------------


class TestNullPropagation(unittest.TestCase):
    def test_baseline_null_yields_em_dash(self):
        self.assertEqual(cmp_mod._delta_count(None, 10), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_pp(None, 0.5), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_ratio(None, 1.2), cmp_mod.EM_DASH)

    def test_adopter_null_yields_em_dash(self):
        self.assertEqual(cmp_mod._delta_count(10, None), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_pp(0.1, None), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_ratio(1.0, None), cmp_mod.EM_DASH)

    def test_both_null_yield_em_dash(self):
        self.assertEqual(cmp_mod._delta_count(None, None), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_pp(None, None), cmp_mod.EM_DASH)
        self.assertEqual(cmp_mod._delta_ratio(None, None), cmp_mod.EM_DASH)


# ---------------------------------------------------------------------------
# 8. Table rendering (2 tests)
# ---------------------------------------------------------------------------


class TestTableRendering(_TmpCase):
    def test_two_adopter_has_single_delta_column(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        # Header row contains 4 cells: Metric | a (baseline) | b | Delta vs baseline
        header_line = [ln for ln in out.splitlines() if ln.startswith("| Metric")][0]
        cells = [c.strip() for c in header_line.strip("|").split("|")]
        self.assertEqual(cells, ["Metric", "a (baseline)", "b", "Delta vs baseline"])

    def test_three_adopter_preserves_input_order_for_delta_columns(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b", sessions=20))
        c = self._write_json("c.json", _sample_report(adopter_name="c", sessions=30))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--input", "c=" + str(c),
        ])
        self.assertEqual(rc, 0)
        header_line = [ln for ln in out.splitlines() if ln.startswith("| Metric")][0]
        cells = [c.strip() for c in header_line.strip("|").split("|")]
        # Metric | a (baseline) | b | Delta | c | Delta   -> 6 cells
        self.assertEqual(cells, [
            "Metric", "a (baseline)", "b", "Delta vs baseline",
            "c", "Delta vs baseline",
        ])
        # Sessions row: a=15 baseline, b=20 (+5), c=30 (+15)
        sessions_line = [ln for ln in out.splitlines() if ln.startswith("| Sessions ")][0]
        sess_cells = [x.strip() for x in sessions_line.strip("|").split("|")]
        self.assertEqual(sess_cells, ["Sessions", "15", "20", "+5", "30", "+15"])


# ---------------------------------------------------------------------------
# 9. Custom skills diff (2 tests)
# ---------------------------------------------------------------------------


class TestCustomSkillsDiff(_TmpCase):
    def test_unique_skills_listed_under_adopter(self):
        a = self._write_json("a.json", _sample_report(
            adopter_name="a", custom_skills_names=["shared-skill"], custom_skills_count=1))
        b = self._write_json("b.json", _sample_report(
            adopter_name="b",
            custom_skills_names=["shared-skill", "b-only-skill", "another-b-skill"],
            custom_skills_count=3))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Unique to b: another-b-skill, b-only-skill", out)

    def test_no_unique_skills_no_line_printed(self):
        a = self._write_json("a.json", _sample_report(
            adopter_name="a", custom_skills_names=["x", "y"], custom_skills_count=2))
        b = self._write_json("b.json", _sample_report(
            adopter_name="b", custom_skills_names=["x", "y"], custom_skills_count=2))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertNotIn("Unique to b:", out)


# ---------------------------------------------------------------------------
# 10. ADR diff (1 test)
# ---------------------------------------------------------------------------


class TestADRDiff(_TmpCase):
    def test_unique_adrs_surface_under_adopter(self):
        a = self._write_json("a.json", _sample_report(
            adopter_name="a", adrs_names=["ADR-001"], adrs_distinct=1))
        b = self._write_json("b.json", _sample_report(
            adopter_name="b", adrs_names=["ADR-001", "ADR-042", "ADR-045"], adrs_distinct=3))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Unique to b: ADR-042, ADR-045", out)


# ---------------------------------------------------------------------------
# 11. JSON output (1 test)
# ---------------------------------------------------------------------------


class TestJSONOutput(_TmpCase):
    def test_json_flag_emits_structured_payload(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b", sessions=20))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--json",
        ])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["baseline"], "a")
        self.assertIn("adopters", payload)
        self.assertEqual(len(payload["adopters"]), 2)
        names = sorted(a["name"] for a in payload["adopters"])
        self.assertEqual(names, ["a", "b"])
        # Deltas present for non-baseline, empty for baseline.
        b_entry = [x for x in payload["adopters"] if x["name"] == "b"][0]
        self.assertIn("sessions", b_entry["deltas"])
        self.assertEqual(b_entry["deltas"]["sessions"], "+5")


# ---------------------------------------------------------------------------
# Extra coverage — CLI plumbing, file I/O, and edge cases
# ---------------------------------------------------------------------------


class TestInputSpecParser(unittest.TestCase):
    def test_bare_path_returns_none_name(self):
        self.assertEqual(cmp_mod._parse_input_spec("./foo.json"), (None, "./foo.json"))

    def test_name_equals_path(self):
        self.assertEqual(cmp_mod._parse_input_spec("n=/p/x.json"), ("n", "/p/x.json"))

    def test_empty_path_after_equals_rejected(self):
        with self.assertRaises(ValueError):
            cmp_mod._parse_input_spec("name=")


class TestFileErrors(_TmpCase):
    def test_missing_input_file_exit_1(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(self.tmp / "nope.json"),
        ])
        self.assertEqual(rc, 1)
        self.assertIn("file not found", err)

    def test_malformed_json_exit_2(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        bad = self.tmp / "bad.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(bad),
        ])
        self.assertEqual(rc, 2)
        self.assertIn("bad JSON", err)

    def test_non_object_json_rejected(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        arr = self.tmp / "arr.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(arr),
        ])
        self.assertEqual(rc, 2)
        self.assertIn("must be an object", err)

    def test_bare_path_without_adopter_name_in_json_rejected(self):
        bad = _sample_report(adopter_name="a")
        bad.pop("adopter_name")
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", bad)
        rc, _, err = self._capture([
            "--input", "a=" + str(a),
            "--input", str(b),   # bare path, no name in JSON
        ])
        self.assertEqual(rc, 1)
        self.assertIn("no adopter_name", err)

    def test_duplicate_adopter_name_rejected(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        rc, _, err = self._capture([
            "--input", "x=" + str(a),
            "--input", "x=" + str(a),
        ])
        self.assertEqual(rc, 1)
        self.assertIn("duplicate", err)


class TestOutputPath(_TmpCase):
    def test_output_writes_to_file_and_creates_parent(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        out_path = self.tmp / "nested" / "deep" / "out.md"
        rc, stdout, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--output", str(out_path),
        ])
        self.assertEqual(rc, 0)
        # Stdout is empty when --output is used.
        self.assertEqual(stdout, "")
        self.assertTrue(out_path.is_file())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("# Cross-adopter metrics comparison", content)


class TestBaselineDefaultAndExplicit(_TmpCase):
    def test_default_baseline_is_first_input(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("**Baseline:** a", out)

    def test_explicit_baseline_override(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a"))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
            "--baseline", "b",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("**Baseline:** b", out)


class TestMixedWindowNote(_TmpCase):
    def test_mixed_windows_without_check_adds_note(self):
        a = self._write_json("a.json", _sample_report(adopter_name="a", window="7d"))
        b = self._write_json("b.json", _sample_report(adopter_name="b", window="14d"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Window mismatch detected", out)
        self.assertIn("mixed (see notes)", out)


class TestDeterminism(_TmpCase):
    def test_skill_and_adr_lists_sorted_lexicographically(self):
        a = self._write_json("a.json", _sample_report(
            adopter_name="a",
            custom_skills_names=["zeta-skill", "alpha-skill", "mu-skill"],
            custom_skills_count=3,
            adrs_names=["ADR-099", "ADR-001", "ADR-050"],
            adrs_distinct=3,
        ))
        b = self._write_json("b.json", _sample_report(adopter_name="b"))
        rc, out, _ = self._capture([
            "--input", "a=" + str(a),
            "--input", "b=" + str(b),
        ])
        self.assertEqual(rc, 0)
        # Baseline skills rendered: alpha, mu, zeta (sorted).
        self.assertIn("alpha-skill, mu-skill, zeta-skill", out)
        self.assertIn("ADR-001, ADR-050, ADR-099", out)


class TestFormatters(unittest.TestCase):
    def test_fmt_count_handles_none_and_ints(self):
        self.assertEqual(cmp_mod._fmt_count(None), "N/A")
        self.assertEqual(cmp_mod._fmt_count(0), "0")
        self.assertEqual(cmp_mod._fmt_count(42), "42")

    def test_fmt_pct_handles_none_and_values(self):
        self.assertEqual(cmp_mod._fmt_pct(None), "N/A")
        self.assertEqual(cmp_mod._fmt_pct(0.033), "3.3%")
        self.assertEqual(cmp_mod._fmt_pct(1.0), "100.0%")

    def test_fmt_ratio_handles_none_and_values(self):
        self.assertEqual(cmp_mod._fmt_ratio(None), "N/A")
        self.assertEqual(cmp_mod._fmt_ratio(1.136), "1.136")
        self.assertEqual(cmp_mod._fmt_ratio(0.5), "0.500")


class TestAdopterMetricsEnvelopeIntegration(_TmpCase):
    """Integration: adopter-metrics.py --json emits envelope {metrics: {...}}.

    This script must accept that shape in addition to the flat form. PLAN-015
    Phase 0.3 integration guard — Agent 1 and Agent 2 agreed different JSON
    layouts; compare-adopters now unwraps adopter-metrics' envelope so the
    two scripts compose without a manual reshape step.
    """

    def test_envelope_form_is_unwrapped_at_load_time(self):
        envelope = {
            "adopter_name": "adopter-1",
            "window": "7d",
            "window_start": "2026-04-10T00:00:00Z",
            "window_end": "2026-04-17T00:00:00Z",
            "generated_at": "2026-04-17T12:00:00Z",
            "audit_log_path": "/tmp/audit.jsonl",
            "metrics": {
                "sessions": 15,
                "spawns_total": 87,
                "veto": {"vetoes": 3, "spawns_plus_vetoes": 90, "rate": 0.033},
                "completion": {"done": 12, "abandoned": 2, "denom": 14, "ratio": 0.857},
                "tokens": {"actual_total": 125000, "predicted_total": 110000, "ratio": 1.136},
                "custom_skills": {"count": 2, "names": ["a", "b"]},
                "adrs": {"total_mentions": 14, "distinct_count": 4,
                         "names": ["ADR-023", "ADR-040", "ADR-045", "ADR-048"]},
            },
        }
        unwrapped = cmp_mod._unwrap_envelope(envelope)
        self.assertEqual(unwrapped["sessions"], 15)
        self.assertEqual(unwrapped["spawns_total"], 87)
        self.assertEqual(unwrapped["veto"]["rate"], 0.033)
        self.assertEqual(unwrapped["completion"]["ratio"], 0.857)
        self.assertEqual(unwrapped["tokens"]["ratio"], 1.136)
        self.assertEqual(unwrapped["custom_skills"]["count"], 2)
        self.assertEqual(unwrapped["adrs"]["distinct_count"], 4)
        self.assertEqual(unwrapped["adopter_name"], "adopter-1")
        self.assertEqual(unwrapped["window"], "7d")
        self.assertNotIn("metrics", unwrapped)

    def test_flat_form_passes_through_unchanged(self):
        flat = {"adopter_name": "foo", "window": "7d", "sessions": 5}
        self.assertEqual(cmp_mod._unwrap_envelope(flat), flat)

    def test_metrics_key_non_dict_passes_through(self):
        weird = {"adopter_name": "foo", "metrics": "not-a-dict"}
        self.assertEqual(cmp_mod._unwrap_envelope(weird), weird)

    def test_end_to_end_with_envelope_inputs(self):
        a = self._write_json("a.json", {
            "adopter_name": "A",
            "window": "7d",
            "metrics": {
                "sessions": 10, "spawns_total": 50,
                "veto": {"rate": 0.10},
                "completion": {"ratio": 0.80},
                "tokens": {"ratio": 1.0},
                "custom_skills": {"count": 1, "names": ["x"]},
                "adrs": {"total_mentions": 5, "distinct_count": 2,
                         "names": ["ADR-001", "ADR-002"]},
            },
        })
        b = self._write_json("b.json", {
            "adopter_name": "B",
            "window": "7d",
            "metrics": {
                "sessions": 20, "spawns_total": 100,
                "veto": {"rate": 0.05},
                "completion": {"ratio": 0.90},
                "tokens": {"ratio": 1.2},
                "custom_skills": {"count": 3, "names": ["x", "y", "z"]},
                "adrs": {"total_mentions": 12, "distinct_count": 4,
                         "names": ["ADR-001", "ADR-003", "ADR-004", "ADR-005"]},
            },
        })
        rc, out, _ = self._capture([
            "--input", "A={0}".format(a),
            "--input", "B={0}".format(b),
            "--baseline", "A",
        ])
        self.assertEqual(rc, 0)
        self.assertIn("Sessions", out)
        self.assertIn("+10", out)  # 20 - 10
        self.assertIn("+10.0 pp", out)  # completion 0.90 - 0.80


if __name__ == "__main__":
    unittest.main()
