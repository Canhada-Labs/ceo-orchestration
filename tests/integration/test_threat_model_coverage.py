"""Threat-model coverage test — PLAN-014 Phase C.3.

Parses the STRIDE scenario table from docs/threat-model.md, validates
that every mitigation reference (file path, ADR, section) resolves to a
real artifact, and enforces structural invariants (RR count, STRIDE
category distribution, per-ADR table completeness).

Dead-reference = hard fail. This is NOT advisory.

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Repo root discovery
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# ---------------------------------------------------------------------------
# Parser functions (tested in TestParser below)
# ---------------------------------------------------------------------------

THREAT_MODEL_REL = Path("docs/threat-model.md")


def _read_threat_model(repo_root: Path) -> str:
    """Read the threat-model.md file content."""
    path = repo_root / THREAT_MODEL_REL
    if not path.is_file():
        raise FileNotFoundError(f"threat-model.md not found at {path}")
    return path.read_text(encoding="utf-8")


def parse_status(content: str) -> str:
    """Extract the Status field from frontmatter."""
    m = re.search(r"^\*\*Status:\*\*\s+(\S+)", content, re.MULTILINE)
    return m.group(1).rstrip() if m else ""


def parse_residual_risks(content: str) -> List[str]:
    """Extract RR-N identifiers from the Residual risks section.

    Looks for '### RR-N' headers in the '## Residual risks' section.
    """
    rr_ids: List[str] = []
    in_section = False
    for line in content.splitlines():
        if line.strip().startswith("## Residual risks"):
            in_section = True
            continue
        if in_section and line.strip().startswith("## ") and "Residual" not in line:
            break
        if in_section:
            m = re.match(r"^###\s+(RR-\d+)", line)
            if m:
                rr_ids.append(m.group(1))
    return rr_ids


def parse_stride_scenarios(content: str) -> List[Dict[str, str]]:
    """Extract STRIDE scenarios from the numbered lists.

    Returns list of dicts with keys: id, title, category.
    Each scenario is a numbered bold header like '1. **S-001: ...**'.
    """
    scenarios: List[Dict[str, str]] = []
    current_category = ""
    for line in content.splitlines():
        # Detect STRIDE category headers like '### Spoofing (5)'
        cat_m = re.match(
            r"^###\s+(Spoofing|Tampering|Repudiation|Information Disclosure|Denial of Service|Elevation of Privilege)\s*\(",
            line,
        )
        if cat_m:
            current_category = cat_m.group(1)
            continue
        # Detect scenario headers
        sc_m = re.match(
            r"^\d+\.\s+\*\*([A-Z]+-\d+):\s+(.+?)\*\*", line
        )
        if sc_m and current_category:
            scenarios.append(
                {
                    "id": sc_m.group(1),
                    "title": sc_m.group(2).rstrip(),
                    "category": current_category,
                }
            )
    return scenarios


def parse_mitigation_file_refs(content: str) -> List[str]:
    """Extract file path references from **Evidence:** and **Mitigations:** lines.

    Looks for backtick-quoted paths that look like file references:
    `.claude/...`, `docs/...`, `SPEC/...`, `tests/...`, `.github/...`, `scripts/...`.

    Skips lines in the Residual risks section (RR-N descriptions reference
    future/planned artifacts that may not exist yet).
    """
    refs: List[str] = []
    in_residual_risks = False
    for line in content.splitlines():
        # Track section to skip residual risks (future refs)
        if line.strip().startswith("## Residual risks"):
            in_residual_risks = True
            continue
        if in_residual_risks and line.strip().startswith("## ") and "Residual" not in line:
            in_residual_risks = False
        if in_residual_risks:
            continue
        # Only scan evidence/mitigation lines (or reference section)
        if not any(
            kw in line
            for kw in ("**Evidence:**", "**Mitigations:**", "**Mitigation:**", "- `.")
        ):
            continue
        # Extract backtick-quoted paths
        for m in re.finditer(r"`([^`]+)`", line):
            path = m.group(1)
            # Filter to file-like references (not inline code snippets)
            if any(
                path.startswith(prefix)
                for prefix in (
                    ".claude/",
                    "docs/",
                    "SPEC/",
                    "tests/",
                    ".github/",
                    "scripts/",
                    "benchmarks/",
                )
            ):
                # Strip trailing wildcards for directory references
                clean = path.rstrip("*").rstrip("/")
                if clean:
                    refs.append(clean)
    return refs


def parse_per_adr_table(content: str) -> List[Dict[str, str]]:
    """Parse the per-ADR threat table rows.

    Returns list of dicts with keys: adr, scope, stride_vector, scenarios, residual.
    """
    rows: List[Dict[str, str]] = []
    in_table = False
    header_seen = False
    for line in content.splitlines():
        if "## Per-ADR threat table" in line:
            in_table = True
            continue
        if not in_table:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            if header_seen and stripped and not stripped.startswith("**"):
                break
            continue
        # Skip separator lines
        if re.match(r"^\|[-\s|]+\|$", stripped):
            header_seen = True
            continue
        # Skip header row
        if "ADR" in stripped and "Security scope" in stripped:
            continue
        cells = [c.strip() for c in stripped.split("|")]
        # Remove empty first/last cells from leading/trailing pipes
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if len(cells) >= 5:
            rows.append(
                {
                    "adr": cells[0],
                    "scope": cells[1],
                    "stride_vector": cells[2],
                    "scenarios": cells[3],
                    "residual": cells[4],
                }
            )
    return rows


def validate_file_ref(repo_root: Path, ref: str) -> bool:
    """Check that a file reference resolves to an existing path.

    Handles both exact files and directory prefixes.
    """
    target = repo_root / ref
    if target.is_file() or target.is_dir():
        return True
    # Try as a prefix (e.g., '.claude/hooks/_lib/adapters/live/' is a dir)
    parent = target.parent
    if parent.is_dir():
        # Check if any file matches the prefix
        name = target.name
        for child in parent.iterdir():
            if child.name.startswith(name):
                return True
    return False


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestThreatModelParser(unittest.TestCase):
    """Unit tests for the parser functions themselves (>=8 required)."""

    def test_parse_status_accepted(self) -> None:
        content = "# Title\n\n**Status:** accepted\n**Date:** 2026-04-15"
        self.assertEqual(parse_status(content), "accepted")

    def test_parse_status_draft(self) -> None:
        content = "**Status:** draft (PLAN-013)\n"
        self.assertEqual(parse_status(content), "draft")

    def test_parse_status_missing(self) -> None:
        content = "# No status here\nJust text."
        self.assertEqual(parse_status(content), "")

    def test_parse_residual_risks_extracts_ids(self) -> None:
        content = (
            "## Residual risks (RR-1 through RR-3)\n\n"
            "### RR-1 — Sentinel bypass\nText.\n\n"
            "### RR-2 — TLS compromise\nText.\n\n"
            "### RR-3 — MCP lateral\nText.\n\n"
            "## Per-ADR threat table\n"
        )
        self.assertEqual(parse_residual_risks(content), ["RR-1", "RR-2", "RR-3"])

    def test_parse_residual_risks_empty_section(self) -> None:
        content = "## Residual risks\n\n## Per-ADR threat table\n"
        self.assertEqual(parse_residual_risks(content), [])

    def test_parse_stride_scenarios(self) -> None:
        content = (
            "### Spoofing (2)\n\n"
            "1. **S-001: Forged token**\n"
            "   - Details\n\n"
            "2. **S-002: Sentinel spoof**\n"
            "   - Details\n\n"
            "### Tampering (1)\n\n"
            "1. **T-001: State poisoning**\n"
        )
        scenarios = parse_stride_scenarios(content)
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(scenarios[0]["id"], "S-001")
        self.assertEqual(scenarios[0]["category"], "Spoofing")
        self.assertEqual(scenarios[2]["category"], "Tampering")

    def test_parse_mitigation_file_refs(self) -> None:
        content = (
            "   - **Evidence:** `.claude/hooks/check_agent_spawn.py::decide()` line 98+;\n"
            "   - **Mitigations:** `.claude/adr/ADR-010-canonical-edit-sentinel.md`;\n"
        )
        refs = parse_mitigation_file_refs(content)
        # Should extract the path portions
        self.assertTrue(len(refs) >= 2)

    def test_parse_per_adr_table(self) -> None:
        content = (
            "## Per-ADR threat table\n\n"
            "| ADR | Security scope | Primary STRIDE vector | Scenarios referencing | Residual risk |\n"
            "|---|---|---|---|---|\n"
            "| ADR-001 | Runtime state dir | Information Disclosure | ID-001 | Shared-host root |\n"
            "| ADR-002 | Hooks layout | — | N/A: layout | — |\n"
            "\n**Coverage statistics:**\n"
        )
        rows = parse_per_adr_table(content)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["adr"], "ADR-001")
        self.assertEqual(rows[1]["adr"], "ADR-002")

    def test_parse_per_adr_table_empty(self) -> None:
        content = "## Per-ADR threat table\n\n**Coverage statistics:**\n"
        rows = parse_per_adr_table(content)
        self.assertEqual(len(rows), 0)

    def test_validate_file_ref_existing_file(self) -> None:
        # CLAUDE.md always exists at repo root
        self.assertTrue(validate_file_ref(_REPO_ROOT, "CLAUDE.md"))

    def test_validate_file_ref_existing_dir(self) -> None:
        self.assertTrue(validate_file_ref(_REPO_ROOT, "docs"))

    def test_validate_file_ref_nonexistent(self) -> None:
        self.assertFalse(
            validate_file_ref(_REPO_ROOT, "nonexistent/path/file.xyz")
        )


class TestThreatModelStructure(unittest.TestCase):
    """Structural assertions on the real threat-model.md."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read_threat_model(_REPO_ROOT)

    def test_status_is_accepted(self) -> None:
        """C.1 acceptance: status must be 'accepted'."""
        self.assertEqual(parse_status(self.content), "accepted")

    def test_accepted_by_line_present(self) -> None:
        """C.1 acceptance: mechanical sign-off line must exist."""
        self.assertIn("Accepted-By:", self.content)

    def test_residual_risk_count_at_least_8(self) -> None:
        """C.2 acceptance: RR-1 through RR-8 must exist."""
        rr_ids = parse_residual_risks(self.content)
        self.assertGreaterEqual(len(rr_ids), 8)
        for i in range(1, 9):
            self.assertIn(f"RR-{i}", rr_ids)

    def test_stride_scenario_count_at_least_33(self) -> None:
        """Original 33 scenarios must be preserved."""
        scenarios = parse_stride_scenarios(self.content)
        self.assertGreaterEqual(len(scenarios), 33)

    def test_stride_categories_covered(self) -> None:
        """All 6 STRIDE categories must have >=5 scenarios each."""
        scenarios = parse_stride_scenarios(self.content)
        cats: Dict[str, int] = {}
        for s in scenarios:
            cats[s["category"]] = cats.get(s["category"], 0) + 1
        for expected_cat in [
            "Spoofing",
            "Tampering",
            "Repudiation",
            "Information Disclosure",
            "Denial of Service",
            "Elevation of Privilege",
        ]:
            self.assertIn(expected_cat, cats, f"Missing category: {expected_cat}")
            self.assertGreaterEqual(
                cats[expected_cat], 5, f"{expected_cat} has < 5 scenarios"
            )

    def test_per_adr_table_has_045_through_048(self) -> None:
        """C.5 acceptance: per-ADR rows for ADR-045/046/047/048."""
        rows = parse_per_adr_table(self.content)
        adr_ids = {r["adr"] for r in rows}
        for adr in ["ADR-045", "ADR-046", "ADR-047", "ADR-048"]:
            self.assertIn(adr, adr_ids, f"Missing per-ADR row: {adr}")

    def test_per_adr_045_048_have_nonempty_residual(self) -> None:
        """Each new ADR row must have a non-trivial residual risk analysis."""
        rows = parse_per_adr_table(self.content)
        for row in rows:
            if row["adr"] in ("ADR-045", "ADR-046", "ADR-047", "ADR-048"):
                self.assertTrue(
                    len(row["residual"]) > 20,
                    f"{row['adr']} residual risk too short: {row['residual']!r}",
                )


class TestThreatModelFileReferences(unittest.TestCase):
    """Dead-reference = hard fail. Every cited file must exist."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read_threat_model(_REPO_ROOT)
        cls.refs = parse_mitigation_file_refs(cls.content)

    def test_has_file_references(self) -> None:
        """Sanity: parser must find at least 10 file references."""
        self.assertGreaterEqual(len(self.refs), 10)

    def test_all_file_references_resolve(self) -> None:
        """Every mitigation file reference must resolve to a real path."""
        missing: List[str] = []
        for ref in self.refs:
            # Normalize: strip method/function references like ::decide()
            clean = ref.split("::")[0].split(" ")[0]
            # Strip trailing line refs like ':186'
            clean = re.sub(r":\d+[+]?$", "", clean)
            if not validate_file_ref(_REPO_ROOT, clean):
                missing.append(ref)
        self.assertEqual(
            missing,
            [],
            f"Dead file references in threat-model.md: {missing}",
        )

    def test_reference_section_cites_adrs(self) -> None:
        """The References section must cite ADR-045 through ADR-048."""
        ref_section = ""
        in_refs = False
        for line in self.content.splitlines():
            if line.strip() == "## References":
                in_refs = True
                continue
            if in_refs:
                if line.strip().startswith("## ") and "References" not in line:
                    break
                ref_section += line + "\n"
        for adr_num in ("045", "046", "047", "048"):
            self.assertIn(
                f"ADR-{adr_num}",
                ref_section,
                f"References section missing ADR-{adr_num}",
            )


if __name__ == "__main__":
    unittest.main()
