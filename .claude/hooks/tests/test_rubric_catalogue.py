"""PLAN-081 Phase 3 — rubric-violation-catalogue.yaml integrity tests.

Tests the LIVE catalogue at:
  .claude/plans/PLAN-081/staging/phase-3/policies/rubric-violation-catalogue.yaml

All assertions are derived from spec.md §11 + ADR-107 + ADR-108 requirements.
The loader used is the one from check_pair_rail.py (staging copy) so that
the same parsing path exercised in production is validated here.

Path-setup note (staging position):
  <repo>/.claude/plans/PLAN-081/staging/phase-3/tests/<this>.py
  parents[0] = .../tests
  parents[1] = .../phase-3
  parents[2] = .../staging
  parents[3] = .../PLAN-081
  parents[4] = .../plans
  parents[5] = .../.claude
  parents[6] = <repo>         <- repo root

The catalogue file lives at parents[1] / "policies" / "rubric-violation-catalogue.yaml".
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
import types
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution — staging OR canonical position
# Staging:   .../staging/phase-3/tests/<this>.py → hook at parents[1]/hooks/
# Canonical: .../.claude/hooks/tests/<this>.py → hook at parents[1]/
# Catalogue (live YAML): staging parents[1]/policies/ vs
#                       canonical parents[2]/policies/
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_IS_STAGING = "staging" in _THIS_FILE.parts and "phase-3" in _THIS_FILE.parts

if _IS_STAGING:
    _STAGING_DIR = _THIS_FILE.parents[1]
    _STAGING_HOOKS = _STAGING_DIR / "hooks"
    _CATALOGUE_DIR = _STAGING_DIR / "policies"
else:
    # Canonical position: hook is at .claude/hooks/ (= parents[1])
    _STAGING_DIR = _THIS_FILE.parents[1]  # .claude/hooks/
    _STAGING_HOOKS = _STAGING_DIR  # hook dir same as hooks
    _CATALOGUE_DIR = _THIS_FILE.parents[2] / "policies"  # .claude/policies/

if str(_STAGING_HOOKS) not in sys.path:
    sys.path.insert(0, str(_STAGING_HOOKS))
if str(_STAGING_DIR) not in sys.path:
    sys.path.insert(0, str(_STAGING_DIR))

# ---------------------------------------------------------------------------
# Load check_pair_rail for its catalogue loader (staging or canonical)
# ---------------------------------------------------------------------------
_HOOK_PATH = _STAGING_HOOKS / "check_pair_rail.py"


def _load_hook() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_pair_rail_phase3_rc",
        str(_HOOK_PATH),
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


try:
    _CPR = _load_hook()
except Exception as exc:
    raise ImportError(
        f"Failed to load staging check_pair_rail.py from {_HOOK_PATH}: {exc}"
    ) from exc

# ---------------------------------------------------------------------------
# The catalogue lives in the staging policies directory.  We point the loader
# at the staging phase-3 directory (which IS NOT the canonical repo root but
# contains the same sub-tree structure: .claude/policies/...).
#
# The loader calls:
#   repo_root / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
#
# So we construct a synthetic root such that the relative path resolves.
# The staging structure is:
#   <repo>/.claude/plans/PLAN-081/staging/phase-3/policies/rubric-violation-catalogue.yaml
#
# We synthesise a "staging repo root" by creating a symlink or using the
# actual file path via a wrapper.  The cleanest approach: copy the file into
# a temp tree matching the expected path.  But since the loader is pure Python
# and just does path arithmetic, we can instead pass the staging directory
# minus ".claude/policies" as a "fake repo root":
#
#   fake_root / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
#   = _STAGING_DIR / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
#   ...but the file lives at _STAGING_DIR / "policies" / "..."
#
# To avoid the mismatch, we create a tmp directory with the canonical sub-path
# pointing to the real file (symlink or copy).  Since stdlib has no symlink
# on all platforms, we copy the YAML into a tmpdir with the canonical path.
# ---------------------------------------------------------------------------

import tempfile
import shutil

def _build_staging_repo_root() -> Path:
    """Build a tmp dir that mimics repo structure for the catalogue loader."""
    td = Path(tempfile.mkdtemp(prefix="rubric_cat_test_"))
    policies_dir = td / ".claude" / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    src = _CATALOGUE_DIR / "rubric-violation-catalogue.yaml"
    shutil.copy2(str(src), str(policies_dir / "rubric-violation-catalogue.yaml"))
    return td


_STAGING_REPO_ROOT: Path = _build_staging_repo_root()


def _load_live_catalogue() -> dict:
    """Load the live staging catalogue via the hook's loader."""
    # Reset module-level cache so tests always get a fresh parse
    _CPR._RUBRIC_CATALOGUE_CACHE = None  # type: ignore[attr-defined]
    cat = _CPR._load_rubric_catalogue(_STAGING_REPO_ROOT)
    return cat


# ---------------------------------------------------------------------------
# Known valid values (per catalogue header comments)
# ---------------------------------------------------------------------------
_VALID_SEVERITIES = {"P0", "P1"}
_VALID_SCOPES = {
    "code-review",
    "security",
    "qa",
    "performance",
    "threat-detection",
}
_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_OWASP_RE = re.compile(
    r"^(A0\d-\d{4}|A\d{2}-\d{4}|LLM\d{2})",
    re.IGNORECASE,
)
_MITRE_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+")  # loose: x.y.z[-suffix]


class TestRubricCatalogueLive(unittest.TestCase):
    """Live catalogue integrity assertions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogue = _load_live_catalogue()

    def test_catalogue_parses_without_exception(self) -> None:
        """Loader must not raise and must return a dict."""
        self.assertIsInstance(self.catalogue, dict)

    def test_entry_count_in_range(self) -> None:
        """Must have ≥12 and ≤20 entries per spec.md §11 target (12-20)."""
        n = len(self.catalogue)
        self.assertGreaterEqual(
            n, 12,
            f"Only {n} entries; spec.md §11 requires ≥12.",
        )
        self.assertLessEqual(
            n, 20,
            f"{n} entries; spec.md §11 caps at 20.",
        )

    def test_every_entry_has_required_keys(self) -> None:
        """Every entry must carry id, severity_default, description, scope."""
        required = {"id", "severity_default", "description", "scope"}
        missing_map: dict = {}
        for vid, entry in self.catalogue.items():
            missing = required - set(entry.keys())
            if missing:
                missing_map[vid] = sorted(missing)
        self.assertEqual(
            missing_map, {},
            f"Entries missing required keys: {missing_map}",
        )

    def test_every_severity_default_valid(self) -> None:
        """severity_default must be 'P0' or 'P1'."""
        bad: list = []
        for vid, entry in self.catalogue.items():
            sev = entry.get("severity_default", "")
            if sev not in _VALID_SEVERITIES:
                bad.append(f"{vid}: {sev!r}")
        self.assertEqual(bad, [], f"Invalid severity_default values: {bad}")

    def test_every_scope_valid(self) -> None:
        """scope must be one of the five canonical values."""
        bad: list = []
        for vid, entry in self.catalogue.items():
            scope = entry.get("scope", "")
            if scope not in _VALID_SCOPES:
                bad.append(f"{vid}: {scope!r}")
        self.assertEqual(bad, [], f"Invalid scope values: {bad}")

    def test_id_uniqueness(self) -> None:
        """No duplicate IDs (dict construction already dedups — verify via raw count)."""
        # The loader builds a dict keyed by id; re-parse to count raw entries
        _CPR._RUBRIC_CATALOGUE_CACHE = None  # type: ignore[attr-defined]
        raw_ids: list = []
        cat_path = (
            _STAGING_REPO_ROOT / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
        )
        text = cat_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- id:"):
                _, _, val = stripped.partition(":")
                raw_ids.append(val.strip())
        self.assertEqual(
            len(raw_ids), len(set(raw_ids)),
            f"Duplicate IDs detected: "
            f"{[v for v in set(raw_ids) if raw_ids.count(v) > 1]}",
        )

    def test_id_format_kebab_case_max_64(self) -> None:
        """Every ID matches ^[a-z][a-z0-9-]*$ and is ≤64 chars."""
        bad: list = []
        for vid in self.catalogue:
            if not _ID_RE.match(vid):
                bad.append(f"{vid!r}: does not match kebab-case pattern")
            elif len(vid) > 64:
                bad.append(f"{vid!r}: length {len(vid)} > 64")
        self.assertEqual(bad, [], f"Malformed IDs: {bad}")

    def test_p0_distribution_cr_and_sec(self) -> None:
        """At least 4 P0 entries, spanning both code-review and security scopes."""
        p0_entries = [
            e for e in self.catalogue.values()
            if e.get("severity_default") == "P0"
        ]
        self.assertGreaterEqual(
            len(p0_entries), 4,
            f"Only {len(p0_entries)} P0 entries; need ≥4 to cover blast-radius surface.",
        )
        p0_scopes = {e.get("scope") for e in p0_entries}
        self.assertIn(
            "code-review", p0_scopes,
            "No P0 entry in code-review scope.",
        )
        self.assertIn(
            "security", p0_scopes,
            "No P0 entry in security scope.",
        )

    def test_owasp_mapping_format_when_present(self) -> None:
        """owasp_mapping (when non-empty) must match OWASP/LLM reference pattern."""
        bad: list = []
        for vid, entry in self.catalogue.items():
            owasp = entry.get("owasp_mapping", "")
            if owasp and not _OWASP_RE.search(owasp):
                bad.append(f"{vid}: {owasp!r}")
        self.assertEqual(
            bad, [],
            f"Entries with non-standard owasp_mapping: {bad}",
        )

    def test_mitre_attack_id_format_when_present(self) -> None:
        """mitre_attack_id (when non-empty) must match Txxxx[.yyy] or be empty."""
        bad: list = []
        for vid, entry in self.catalogue.items():
            mid = entry.get("mitre_attack_id", "")
            # empty string or absent is fine
            if mid and not _MITRE_RE.match(mid):
                bad.append(f"{vid}: {mid!r}")
        self.assertEqual(
            bad, [],
            f"Entries with malformed mitre_attack_id: {bad}",
        )

    def test_catalogue_version_present_and_semver_shaped(self) -> None:
        """catalogue_version must exist and look like a semver string."""
        # The loader only returns the `violations` dict; read metadata directly
        cat_path = (
            _STAGING_REPO_ROOT / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
        )
        text = cat_path.read_text(encoding="utf-8")
        version_line = next(
            (l for l in text.splitlines() if l.startswith("catalogue_version:")),
            None,
        )
        self.assertIsNotNone(
            version_line, "catalogue_version not found in catalogue header."
        )
        # Extract the value
        _, _, raw_val = version_line.partition(":")
        version = raw_val.strip().strip('"').strip("'")
        self.assertRegex(
            version, _SEMVER_RE,
            f"catalogue_version {version!r} is not semver-shaped.",
        )

    def test_plan_and_phase_metadata(self) -> None:
        """plan: PLAN-081, phase: 3 must be present in catalogue header."""
        cat_path = (
            _STAGING_REPO_ROOT / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
        )
        text = cat_path.read_text(encoding="utf-8")
        self.assertIn("plan: PLAN-081", text, "plan: PLAN-081 not found in catalogue.")
        self.assertIn("phase: 3", text, "phase: 3 not found in catalogue.")

    def test_adr_refs_includes_107_and_108(self) -> None:
        """adr_refs must list ADR-107 and ADR-108."""
        cat_path = (
            _STAGING_REPO_ROOT / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
        )
        text = cat_path.read_text(encoding="utf-8")
        self.assertIn("ADR-107", text, "ADR-107 not found in adr_refs.")
        self.assertIn("ADR-108", text, "ADR-108 not found in adr_refs.")

    def test_spec_ref_present_and_references_plan_075(self) -> None:
        """spec_ref must reference PLAN-075/spec.md §11."""
        cat_path = (
            _STAGING_REPO_ROOT / ".claude" / "policies" / "rubric-violation-catalogue.yaml"
        )
        text = cat_path.read_text(encoding="utf-8")
        self.assertIn(
            "PLAN-075", text,
            "spec_ref does not reference PLAN-075.",
        )
        self.assertIn(
            "spec.md", text,
            "spec_ref does not reference spec.md.",
        )

    def test_at_least_one_entry_per_scope(self) -> None:
        """All five scopes must have at least one entry."""
        found_scopes = {
            entry.get("scope") for entry in self.catalogue.values()
        }
        for scope in _VALID_SCOPES:
            self.assertIn(
                scope, found_scopes,
                f"No entry found for scope {scope!r}.",
            )

    def test_total_count_matches_comment_header(self) -> None:
        """Cross-check: count from loader matches expected 19 (6+6+3+2+2)."""
        # The comment in the YAML says "Total: 19 IDs".
        # This test pins the exact count as a regression guard.
        self.assertEqual(
            len(self.catalogue),
            19,
            f"Expected 19 entries (6 CR + 6 Sec + 3 QA + 2 Perf + 2 TDE); "
            f"got {len(self.catalogue)}.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
