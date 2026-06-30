"""Unit tests for tests/synthetic/generate_flip_metrics.py (PLAN-012 D9).

Stdlib + pytest only. Python >=3.9.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest


# Locate `generate_flip_metrics.py` next to this test file's parent-parent.
_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "generate_flip_metrics.py"
)


def _load():
    """Import the generator module by absolute path.

    We use importlib rather than adjusting sys.path so the module name
    stays unique per process and doesn't collide with any other
    ``generate_flip_metrics`` that might be on the path.
    """
    spec = importlib.util.spec_from_file_location(
        "generate_flip_metrics", _MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # allow pickling etc.
    spec.loader.exec_module(mod)
    return mod


GFM = _load()


# ---------------------------------------------------------------------------
# Per-event kind: JSON-schema-compatible rows
# ---------------------------------------------------------------------------

def _row_has_common_fields(row: Dict[str, Any]) -> None:
    """Every synthetic row has the documented shared audit-log fields."""
    for field in ("action", "ts", "project", "session_id", "plan_id"):
        assert field in row, f"row missing required field {field!r}: {row}"
    assert row["synthetic"] is True
    assert row["project"] == "ceo-orchestration"
    assert row["plan_id"].startswith("PLAN-")


class TestPerEventShape:
    """All four event kinds emit rows with documented fields."""

    @pytest.mark.parametrize("event", GFM.SUPPORTED_EVENTS)
    def test_each_event_kind_emits_valid_rows(self, event: str) -> None:
        rows = GFM.generate_records(event=event, n=5, fp_rate=0.1, seed=0)
        assert len(rows) == 5
        for row in rows:
            _row_has_common_fields(row)
            assert row["action"] == event
            # Each emitter tags its owning ADR so drift detection is trivial.
            assert row["adr"].startswith("ADR-")
            # ts is ISO-8601 with Z suffix by convention.
            assert row["ts"].endswith("Z")

    def test_output_safety_reason_family(self) -> None:
        """output_safety_flag.reason_code is in the 7-family list."""
        rows = GFM.generate_records(
            event="output_safety_flag", n=100, fp_rate=0.0, seed=42
        )
        for row in rows:
            assert row["reason_code"] in GFM.OUTPUT_SAFETY_FAMILIES
            # fp_rate=0.0 means no false positives.
            assert row["is_false_positive"] is False

    def test_budget_exceeded_over_cap(self) -> None:
        """Tokens observed always exceed the cap — documented by the ADR."""
        rows = GFM.generate_records(
            event="budget_exceeded", n=50, fp_rate=0.0, seed=7
        )
        for row in rows:
            assert row["tokens_observed"] > row["cap"]
            assert row["scope"] in ("per_spawn", "per_plan")
            # fp_rate=0.0 ⇒ zero legitimate=True (all TP)
            assert row["legitimate"] is False

    def test_confidence_gate_claim_kind(self) -> None:
        rows = GFM.generate_records(
            event="confidence_gate_claim", n=30, fp_rate=0.0, seed=1
        )
        for row in rows:
            assert row["claim_kind"] in GFM.CLAIM_KINDS
            # fp_rate=0.0 rows skew high-confidence per emitter logic.
            assert 0.6 <= row["confidence"] <= 0.95


# ---------------------------------------------------------------------------
# FP-rate boundaries
# ---------------------------------------------------------------------------

class TestFPRateBoundaries:

    def test_fp_rate_zero_gives_zero_fps_output_safety(self) -> None:
        rows = GFM.generate_records(
            event="output_safety_flag", n=200, fp_rate=0.0, seed=0
        )
        assert all(row["is_false_positive"] is False for row in rows)

    def test_fp_rate_one_gives_all_fps_output_safety(self) -> None:
        rows = GFM.generate_records(
            event="output_safety_flag", n=200, fp_rate=1.0, seed=0
        )
        assert all(row["is_false_positive"] is True for row in rows)

    def test_fp_rate_zero_gives_zero_legit_budget(self) -> None:
        rows = GFM.generate_records(
            event="budget_exceeded", n=200, fp_rate=0.0, seed=0
        )
        # legitimate==True would be an FP; fp_rate=0 ⇒ zero.
        assert all(row["legitimate"] is False for row in rows)

    def test_fp_rate_one_gives_all_legit_budget(self) -> None:
        rows = GFM.generate_records(
            event="budget_exceeded", n=200, fp_rate=1.0, seed=0
        )
        assert all(row["legitimate"] is True for row in rows)


# ---------------------------------------------------------------------------
# Exact-count contract
# ---------------------------------------------------------------------------

class TestRecordCount:

    @pytest.mark.parametrize("n", [0, 1, 100, 1000])
    def test_record_count_exact(self, n: int) -> None:
        for event in GFM.SUPPORTED_EVENTS:
            rows = GFM.generate_records(event=event, n=n, fp_rate=0.5, seed=0)
            assert len(rows) == n


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_invalid_event_name_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported event"):
            GFM.generate_records(event="nonsense", n=10, fp_rate=0.1, seed=0)

    def test_negative_n_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            GFM.generate_records(
                event="output_safety_flag", n=-5, fp_rate=0.1, seed=0
            )

    @pytest.mark.parametrize("bad", [-0.01, 1.01, 42.0, -1.0])
    def test_fp_rate_out_of_range_raises(self, bad: float) -> None:
        with pytest.raises(ValueError, match=r"\[0.0, 1.0\]"):
            GFM.generate_records(
                event="output_safety_flag", n=10, fp_rate=bad, seed=0
            )


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:

    def test_same_seed_same_output(self) -> None:
        a = GFM.generate_records(
            event="output_safety_flag", n=50, fp_rate=0.3, seed=12345
        )
        b = GFM.generate_records(
            event="output_safety_flag", n=50, fp_rate=0.3, seed=12345
        )
        # JSON-encode for structural equality.
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    def test_different_seed_different_output(self) -> None:
        a = GFM.generate_records(
            event="output_safety_flag", n=50, fp_rate=0.3, seed=1
        )
        b = GFM.generate_records(
            event="output_safety_flag", n=50, fp_rate=0.3, seed=2
        )
        # Extremely unlikely to collide on 50 records; if it does, the
        # RNG is broken and this is the canary.
        assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------------------
# End-to-end: write → read → parse
# ---------------------------------------------------------------------------

class TestEndToEnd:

    def test_write_jsonl_and_parse(self, tmp_path: Path) -> None:
        out = tmp_path / "synth.jsonl"
        rows = GFM.generate_records(
            event="output_safety_flag", n=25, fp_rate=0.1, seed=99
        )
        written = GFM.write_jsonl(rows, out)
        assert written > 0
        assert out.is_file()
        # Every line round-trips as valid JSON with expected fields.
        lines = out.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 25
        for line in lines:
            parsed = json.loads(line)
            assert parsed["action"] == "output_safety_flag"
            assert parsed["synthetic"] is True

    def test_cli_main_entry(self, tmp_path: Path) -> None:
        out = tmp_path / "cli.jsonl"
        rc = GFM.main(
            [
                "--event", "budget_exceeded",
                "--n", "10",
                "--fp-rate", "0.2",
                "--out", str(out),
                "--seed", "11",
            ]
        )
        assert rc == 0
        assert out.is_file()
        rows = [json.loads(line) for line in out.read_text().splitlines()]
        assert len(rows) == 10
        for row in rows:
            assert row["action"] == "budget_exceeded"
