"""PLAN-035 tests — ui-ux-pro-max reference YAML imports.

Validates:
- All 4 reference YAML files exist + are readable.
- Declared `count:` matches the plan-expected row count AND matches the
  number of `- "No":` entry markers.
- Entry structure contains expected columns for each file type.
- NOTICE.md exists with MIT attribution boilerplate.
- charts-accessibility grades are within the known rubric set.
- import_ui_ux_pro_max.py re-generates byte-identically from the same
  CSV inputs (determinism guard — catches hand-edits).

Stdlib-only test harness; runs under pytest.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_ROOT = REPO_ROOT / ".claude" / "skills" / "frontend"
NOTICE_PATH = FRONTEND_ROOT / "NOTICE.md"
IMPORT_SCRIPT = REPO_ROOT / ".claude" / "scripts" / "import_ui_ux_pro_max.py"

# (relative path, expected entry count, required column names in row 1)
REFERENCES: List[Tuple[str, int, List[str]]] = [
    (
        "design-system-and-components/reference/palettes.yaml",
        161,
        ["Product Type", "Primary", "Background", "Foreground"],
    ),
    (
        "design-system-and-components/reference/fonts.yaml",
        73,
        ["Font Pairing Name", "Heading Font", "Body Font"],
    ),
    (
        "accessibility-and-wcag/reference/charts-accessibility.yaml",
        25,
        ["Data Type", "Best Chart Type", "Accessibility Grade"],
    ),
    (
        "ux-and-user-journeys/reference/guidelines.yaml",
        99,
        ["Category", "Issue", "Platform", "Severity"],
    ),
]
REFERENCE_IDS = [rel.rsplit("/", 1)[-1] for rel, _, _ in REFERENCES]


@pytest.mark.parametrize("rel,expected,_cols", REFERENCES, ids=REFERENCE_IDS)
def test_reference_file_exists_and_nonempty(rel: str, expected: int, _cols: List[str]) -> None:
    p = FRONTEND_ROOT / rel
    assert p.is_file(), f"missing reference file: {p}"
    assert p.stat().st_size > 1024, f"suspiciously small reference: {p}"


@pytest.mark.parametrize("rel,expected,_cols", REFERENCES, ids=REFERENCE_IDS)
def test_declared_count_matches_plan_expected(rel: str, expected: int, _cols: List[str]) -> None:
    content = (FRONTEND_ROOT / rel).read_text(encoding="utf-8")
    m = re.search(r"^count:\s*(\d+)\s*$", content, re.MULTILINE)
    assert m is not None, f"{rel}: missing count declaration"
    declared = int(m.group(1))
    assert declared == expected, (
        f"{rel}: declared count={declared} != plan-expected {expected}"
    )


@pytest.mark.parametrize("rel,expected,_cols", REFERENCES, ids=REFERENCE_IDS)
def test_entry_marker_count_matches_declared(rel: str, expected: int, _cols: List[str]) -> None:
    content = (FRONTEND_ROOT / rel).read_text(encoding="utf-8")
    entry_markers = content.count('- "No":')
    assert entry_markers == expected, (
        f'{rel}: {entry_markers} entry markers found != expected {expected}'
    )


@pytest.mark.parametrize("rel,_expected,required_cols", REFERENCES, ids=REFERENCE_IDS)
def test_required_columns_present_in_row_one(
    rel: str, _expected: int, required_cols: List[str]
) -> None:
    content = (FRONTEND_ROOT / rel).read_text(encoding="utf-8")
    head = "\n".join(content.splitlines()[:80])
    for col in required_cols:
        expected_token = f'"{col}":'
        assert expected_token in head, (
            f'{rel}: required column {col!r} not found in first entry'
        )


@pytest.mark.parametrize("rel,_expected,_cols", REFERENCES, ids=REFERENCE_IDS)
def test_yaml_header_has_license_banner(rel: str, _expected: int, _cols: List[str]) -> None:
    content = (FRONTEND_ROOT / rel).read_text(encoding="utf-8")
    assert "License: MIT" in content, f"{rel}: missing MIT banner"
    assert "Next Level Builder" in content, (
        f"{rel}: missing upstream attribution"
    )
    assert "nextlevelbuilder/ui-ux-pro-max-skill" in content, (
        f"{rel}: missing upstream repo reference"
    )


@pytest.mark.parametrize("rel,_expected,_cols", REFERENCES, ids=REFERENCE_IDS)
def test_yaml_header_marks_auto_generated(rel: str, _expected: int, _cols: List[str]) -> None:
    content = (FRONTEND_ROOT / rel).read_text(encoding="utf-8")
    assert "AUTO-GENERATED" in content, (
        f"{rel}: header must flag AUTO-GENERATED so hand-edits are discouraged"
    )
    assert "import_ui_ux_pro_max.py" in content, (
        f"{rel}: header must reference the regen script path"
    )


def test_notice_md_present() -> None:
    assert NOTICE_PATH.is_file(), f"missing {NOTICE_PATH}"


def test_notice_md_has_mit_license_section() -> None:
    content = NOTICE_PATH.read_text(encoding="utf-8")
    assert "MIT License" in content, "NOTICE.md missing MIT License section"
    assert "Permission is hereby granted" in content, (
        "NOTICE.md missing MIT boilerplate"
    )


def test_notice_md_names_upstream() -> None:
    content = NOTICE_PATH.read_text(encoding="utf-8")
    assert "nextlevelbuilder/ui-ux-pro-max-skill" in content, (
        "NOTICE.md missing upstream repo"
    )
    assert "Next Level Builder" in content, "NOTICE.md missing copyright holder"


def test_notice_md_documents_all_four_imports() -> None:
    content = NOTICE_PATH.read_text(encoding="utf-8")
    for rel, _, _ in REFERENCES:
        assert rel in content, f"NOTICE.md missing import mapping for {rel}"


def test_charts_accessibility_all_25_grades_valid() -> None:
    p = FRONTEND_ROOT / "accessibility-and-wcag/reference/charts-accessibility.yaml"
    content = p.read_text(encoding="utf-8")
    grade_lines = re.findall(r'"Accessibility Grade":\s*"([^"]+)"', content)
    assert len(grade_lines) == 25, (
        f"expected 25 accessibility grade rows, got {len(grade_lines)}"
    )
    valid = {"A", "AA", "AAA", "B", "C", "D"}
    for i, g in enumerate(grade_lines, 1):
        assert g in valid, f"row {i}: unknown grade {g!r} (valid: {sorted(valid)})"


def test_palettes_all_hex_colors_well_formed() -> None:
    p = FRONTEND_ROOT / "design-system-and-components/reference/palettes.yaml"
    content = p.read_text(encoding="utf-8")
    # Primary colors live under the "Primary" key — sample 10 rows.
    primaries = re.findall(r'"Primary":\s*"([^"]+)"', content)
    assert len(primaries) == 161, (
        f"expected 161 Primary colors, found {len(primaries)}"
    )
    hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
    malformed = [c for c in primaries if not hex_re.match(c)]
    assert not malformed, f"malformed Primary colors: {malformed[:5]}"


def test_guidelines_severity_within_rubric() -> None:
    p = FRONTEND_ROOT / "ux-and-user-journeys/reference/guidelines.yaml"
    content = p.read_text(encoding="utf-8")
    severities = re.findall(r'"Severity":\s*"([^"]+)"', content)
    assert len(severities) == 99, (
        f"expected 99 severity entries, found {len(severities)}"
    )
    valid = {"Critical", "High", "Medium", "Low"}
    unknown = [s for s in severities if s not in valid]
    assert not unknown, f"unknown severities: {set(unknown)}"


def test_import_script_runs_offline() -> None:
    """Smoke test: offline mode (--offline <csv dir>) should exit 0 given
    staged inputs. Skipped if inputs are not staged."""
    csv_dir = Path("/tmp/plan035")
    required = ("colors.csv", "typography.csv", "charts.csv", "ux-guidelines.csv")
    if not all((csv_dir / f).is_file() for f in required):
        pytest.skip("offline CSV fixtures not staged at /tmp/plan035")
    result = subprocess.run(
        [sys.executable, str(IMPORT_SCRIPT), "--offline", str(csv_dir)],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


def test_regenerate_is_byte_identical() -> None:
    """Ensure the regen script reproduces the committed YAMLs byte-for-
    byte when fed the same CSV inputs. Hand-edits will trip this test.
    Skipped if `/tmp/plan035/*.csv` is not present."""
    csv_dir = Path("/tmp/plan035")
    required = ("colors.csv", "typography.csv", "charts.csv", "ux-guidelines.csv")
    if not all((csv_dir / f).is_file() for f in required):
        pytest.skip("offline CSV fixtures not staged at /tmp/plan035")

    before = {
        rel: hashlib.sha256((FRONTEND_ROOT / rel).read_bytes()).hexdigest()
        for rel, _, _ in REFERENCES
    }
    subprocess.run(
        [sys.executable, str(IMPORT_SCRIPT), "--offline", str(csv_dir)],
        check=True,
        capture_output=True,
    )
    after = {
        rel: hashlib.sha256((FRONTEND_ROOT / rel).read_bytes()).hexdigest()
        for rel, _, _ in REFERENCES
    }
    for rel in before:
        assert before[rel] == after[rel], (
            f"{rel}: regen produced different bytes (non-deterministic "
            f"or file was hand-edited after last import)"
        )
