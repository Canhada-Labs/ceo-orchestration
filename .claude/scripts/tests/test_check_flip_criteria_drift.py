"""Unit tests for .claude/scripts/check-flip-criteria-drift.py.

PLAN-012 Phase 2 deliverable. Stdlib + pytest only. Python >=3.9.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import List

try:
    import pytest
except ImportError:  # pragma: no cover - unittest-discover without pytest
    raise unittest.SkipTest(
        "pytest not available; this test module uses pytest-native "
        "features (fixtures, tmp_path, capsys, pytest.raises) and is "
        "skipped when unittest discover runs without pytest. Local dev "
        "runs it via `pytest` in the usual suite."
    )

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "check-flip-criteria-drift.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_flip_criteria_drift", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


CDD = _load()


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _plan_with_graph(body: str) -> str:
    """Build a plan file body with YAML frontmatter + a graph section."""
    return (
        "---\n"
        "id: PLAN-999\n"
        "title: Fixture plan\n"
        "---\n\n"
        "# PLAN-999\n\n"
        f"## Dependency Graph\n\n{body}\n\n## Next Section\n\nEND\n"
    )


def _write_adr(adr_dir: Path, number: str, body: str) -> Path:
    """Write a minimal ADR fixture ``ADR-<number>-test.md`` and return path."""
    path = adr_dir / f"ADR-{number}-test.md"
    path.write_text(body, encoding="utf-8")
    return path


def _graph_rows(*rows: str) -> str:
    header = (
        "| Flip/Item | Blocks | Blocked-by | Owning ADR(s) | Execute in |\n"
        "|-----------|--------|------------|---------------|------------|\n"
    )
    return header + "\n".join(rows) + "\n"


# ---------------------------------------------------------------------------
# Test 1: no drift → exit 0
# ---------------------------------------------------------------------------

class TestNoDrift:

    def test_clean_run_exits_zero(self, tmp_path: Path) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        _write_adr(
            adr_dir, "200",
            "# ADR-200\n## Flip criteria\n| 0 → 1 | N≥100 events |\n"
        )
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #1** (widget) | — | N≥100 events | ADR-200 | Phase 5 |"
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 0


# ---------------------------------------------------------------------------
# Test 2: drift → exit 1
# ---------------------------------------------------------------------------

class TestDriftDetected:

    def test_numeric_token_missing_from_adr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        # ADR says N≥30; plan says N≥100 → drift.
        _write_adr(
            adr_dir, "300",
            "# ADR-300\n| 0 → 1 | N≥30 events |\n"
        )
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #2** (budget) | — | N≥100 events | ADR-300 | Phase 5 |"
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 1
        captured = capsys.readouterr()
        # DRIFT message goes to stderr.
        assert "DRIFT: Flip #2" in captured.err
        assert "N≥100" in captured.err
        assert "ADR-300" in captured.err

    def test_multiple_flip_mismatches(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        _write_adr(adr_dir, "301", "# ADR-301\n")
        _write_adr(adr_dir, "302", "# ADR-302\n")
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #3** (a) | — | 5 weeks stable | ADR-301 | Phase 5 |",
                    "| **Flip #4** (b) | — | κ≥0.8 rater | ADR-302 | Phase 5 |",
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "Flip #3" in err
        assert "Flip #4" in err


# ---------------------------------------------------------------------------
# Test 3: missing plan or ADR → exit 2
# ---------------------------------------------------------------------------

class TestParseError:

    def test_missing_plan_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        rc = CDD.main(
            [
                "--plan", str(tmp_path / "does-not-exist.md"),
                "--adr-dir", str(tmp_path),
                "--no-allowlist",
            ]
        )
        assert rc == 2
        assert "PARSE-ERROR" in capsys.readouterr().err

    def test_plan_without_dependency_graph(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text(
            "---\nid: PLAN-999\n---\n\n# Plan\nNo graph here.\n",
            encoding="utf-8",
        )
        rc = CDD.main(
            [
                "--plan", str(plan),
                "--adr-dir", str(tmp_path),
                "--no-allowlist",
            ]
        )
        assert rc == 2
        assert "Dependency Graph" in capsys.readouterr().err

    def test_plan_references_missing_adr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        # No ADR files present. Plan references ADR-999.
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #5** (x) | — | N≥50 | ADR-999 | Phase 5 |"
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 2
        assert "no ADR file matches ADR-999" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Test 4: multi-flip with some clean + some drift
# ---------------------------------------------------------------------------

class TestMultiFlipScenarios:

    def test_some_clean_some_drift(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        _write_adr(adr_dir, "400", "# ADR-400\nkey: N≥100 spawns\n")
        _write_adr(adr_dir, "401", "# ADR-401\nkey: N≥50 pairs\n")  # drift
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #6** (ok) | — | N≥100 spawns | ADR-400 | Phase 5 |",
                    "| **Flip #7** (bad) | — | N≥200 pairs | ADR-401 | Phase 5 |",
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 1
        err = capsys.readouterr().err
        # Clean flip not mentioned; failing flip mentioned once.
        assert "Flip #6" not in err
        assert "Flip #7" in err
        assert "N≥200" in err

    def test_deferred_flip_is_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        _write_adr(adr_dir, "500", "# ADR-500\n(nothing relevant)\n")
        plan = tmp_path / "plan.md"
        # Execute cell contains "DEFER" → drift-checker skips silently.
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #8** (x) | — | N≥3000 labelled | ADR-500 | **DEFER Sprint 15/16** |"
                )
            ),
            encoding="utf-8",
        )
        rc = CDD.main(["--plan", str(plan), "--adr-dir", str(adr_dir), "--no-allowlist"])
        assert rc == 0


# ---------------------------------------------------------------------------
# Test 5: regex-escaped token matching
# ---------------------------------------------------------------------------

class TestTokenExtraction:

    def test_extract_various_threshold_forms(self) -> None:
        prose = (
            "N≥100 events, κ≥0.6 inter-rater, ≤0.2%, 6 weekly runs, "
            "≥200 pairs, p99 stable"
        )
        tokens = CDD.extract_threshold_tokens(prose)
        # Spot-check the canonical normalized forms we expect.
        assert "N≥100" in tokens
        assert "κ≥0.6" in tokens
        assert "≤0.2%" in tokens
        assert "6weeklyruns" in tokens
        assert "≥200pairs" in tokens
        assert "p99" in tokens

    def test_whitespace_normalisation(self) -> None:
        # The ADR side collapses whitespace too, so `N ≥ 100` matches
        # against `N≥100` in the plan.
        plan_tokens = CDD.extract_threshold_tokens("N≥100 events")
        adr_text = "The threshold is N ≥ 100 events"
        missing = CDD.compare_tokens_against_adr(plan_tokens, adr_text)
        assert missing == []


# ---------------------------------------------------------------------------
# Test 6: allowlist
# ---------------------------------------------------------------------------

class TestAllowlist:

    def test_allowlisted_mismatch_exits_zero(
        self, tmp_path: Path
    ) -> None:
        adr_dir = tmp_path / "adr"
        adr_dir.mkdir()
        _write_adr(adr_dir, "600", "# ADR-600\nN≥30 events (original)\n")
        plan = tmp_path / "plan.md"
        plan.write_text(
            _plan_with_graph(
                _graph_rows(
                    "| **Flip #9** (y) | — | N≥100 events | ADR-600 | Phase 5 |"
                )
            ),
            encoding="utf-8",
        )
        allowlist = tmp_path / "allow.txt"
        allowlist.write_text(
            "# doc comment\n"
            "Flip #9\tADR-600\tN≥100\n"
            "Flip #9\tADR-600\t≥100events\n",
            encoding="utf-8",
        )
        rc = CDD.main(
            [
                "--plan", str(plan),
                "--adr-dir", str(adr_dir),
                "--allowlist", str(allowlist),
            ]
        )
        assert rc == 0

    def test_allowlist_malformed_line_errors(
        self, tmp_path: Path
    ) -> None:
        allowlist = tmp_path / "bad.txt"
        allowlist.write_text("only one column\n", encoding="utf-8")
        with pytest.raises(CDD.ParseError, match="allowlist"):
            CDD.parse_allowlist(allowlist)

    def test_allowlist_missing_file_is_empty(self, tmp_path: Path) -> None:
        # Non-existent file ⇒ empty allowlist, not an error.
        entries = CDD.parse_allowlist(tmp_path / "nope.txt")
        assert entries == set()
