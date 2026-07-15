"""Tests for SQUAD_GRANDFATHER cap enforcement (PLAN-080 Phase 1b).

Asserts that the current grandfather domain list does not exceed the
documented_max from the grandfather-cap.policy.yaml policy file.

These tests are mechanical / observability checks. They do NOT enforce the cap
programmatically (the cap is an Owner-controlled governance gate); they assert
that the current state is documented correctly and within the declared limit.

Uses TestEnvContext for env isolation per hook test conventions.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Path bootstrapping
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_STAGING_DIR = _THIS_DIR.parent
# Test file may live at either the legacy staging location
# `.claude/plans/PLAN-080/staging/phase-1/tests/<this>.py` (walk-up of 5 levels)
# or the canonical location `.claude/scripts/tests/<this>.py` (walk-up of 3
# levels). Detect by probing for `.claude/policies/` until found.
def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".claude" / "policies").is_dir():
            return candidate
    # Fallback to legacy 5-level walk-up (pre-Phase-1b staging context).
    return start.parent.parent.parent.parent.parent

_REPO_ROOT = _find_repo_root(_STAGING_DIR)
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib.testing import TestEnvContext  # noqa: E402
except ImportError:
    import shutil
    import tempfile

    class TestEnvContext(unittest.TestCase):  # type: ignore[no-redef]
        def setUp(self) -> None:
            super().setUp()
            self._tmp = tempfile.mkdtemp(prefix="test-cap-")
            self._env_snap: Dict[str, Optional[str]] = {}
            for k in list(os.environ):
                if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                    self._env_snap[k] = os.environ.get(k)
            self.home_dir = Path(self._tmp) / "home"
            self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
            self.audit_dir.mkdir(parents=True, exist_ok=True)
            self.project_dir = Path(self._tmp) / "project"
            self.project_dir.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(self.home_dir)
            os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
            os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
            os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_dir / "audit-log.jsonl")
            os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
            os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")

        def tearDown(self) -> None:
            for k in list(os.environ):
                if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                    if k not in self._env_snap:
                        del os.environ[k]
            for k, v in self._env_snap.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(self._tmp, ignore_errors=True)
            super().tearDown()


# ---------------------------------------------------------------------------
# Helpers — minimal YAML policy parser (stdlib-only)
# ---------------------------------------------------------------------------

def _parse_policy_cap(path: Path) -> Dict[str, int]:
    """Extract cap + current counts from grandfather-cap.policy.yaml.

    Returns dict with keys:
      - individual_cap, individual_current
      - domain_cap, domain_current
    Values are -1 when not found.
    """
    result = {
        "individual_cap": -1,
        "individual_current": -1,
        "domain_cap": -1,
        "domain_current": -1,
    }
    if not path.is_file():
        return result
    text = path.read_text(encoding="utf-8")

    in_individual = False
    in_domain = False

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "individual_skills:":
            in_individual = True
            in_domain = False
            continue
        if stripped == "domain_bundles:":
            in_domain = True
            in_individual = False
            continue
        if stripped and not line.startswith(" ") and not line.startswith("\t"):
            in_individual = False
            in_domain = False
            continue
        if in_individual:
            if stripped.startswith("cap:"):
                try:
                    result["individual_cap"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif stripped.startswith("current:"):
                try:
                    result["individual_current"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
        elif in_domain:
            if stripped.startswith("cap:"):
                try:
                    result["domain_cap"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif stripped.startswith("current:"):
                try:
                    result["domain_current"] = int(stripped.split(":", 1)[1].strip())
                except ValueError:
                    pass
    return result


def _parse_policy_members(path: Path, section: str) -> List[str]:
    """Extract member list from individual_skills or domain_bundles section."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")

    target_section = f"{section}:"
    in_section = False
    in_members = False
    members: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == target_section:
            in_section = True
            in_members = False
            continue
        if in_section:
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_section = False
                in_members = False
                continue
            if stripped == "members:":
                in_members = True
                continue
            if in_members:
                if stripped.startswith("- "):
                    m = stripped[2:].strip()
                    if m:
                        members.append(m)
                elif stripped and not stripped.startswith("-"):
                    in_members = False
    return members


# ---------------------------------------------------------------------------
# Locate the policy files — prefer staged version, fall back to canonical
# ---------------------------------------------------------------------------

_CANONICAL_POLICY = _REPO_ROOT / ".claude" / "policies" / "grandfather-cap.policy.yaml"
_STAGED_POLICY_LEGACY = _STAGING_DIR / "grandfather-cap.policy.yaml"

# Post-PLAN-080 Phase 1b ceremony the policy file is canonical at
# .claude/policies/grandfather-cap.policy.yaml. The legacy staging path is
# kept only as a fallback for pre-ceremony test runs (which no longer exist
# in the canonical tree).
_STAGED_POLICY = (
    _STAGED_POLICY_LEGACY if _STAGED_POLICY_LEGACY.is_file() else _CANONICAL_POLICY
)


# ---------------------------------------------------------------------------
# Mock constants for unit tests (so tests pass independent of actual counts)
# ---------------------------------------------------------------------------

# These match the values declared in the staged grandfather-cap.policy.yaml
_EXPECTED_INDIVIDUAL_CAP = 5
# PLAN-157 W2 graduation (jvm): cap 28→27 (OQ3 cap := current).
# PLAN-157 W2 graduation (cpp): cap 27→26 (OQ3 cap := current).
# PLAN-157 W3 graduation (golang): cap 26→25 (OQ3 cap := current).
_EXPECTED_DOMAIN_CAP = 25  # PLAN-157 W1 sunset: 32 - 4 (desktop, dotnet,
                           # architecture, agents-meta removed from roster;
                           # OQ3 ratified cap := current, so cap drops with
                           # the trim). No headroom by design. Phase 4 lowers
                           # to 15 (target_cap = §6 Q4 default) via further
                           # sunset trim of zero-traffic domains.
_EXPECTED_DOMAIN_TARGET_CAP = 15  # PLAN-080 §6 Q4 long-term target
_EXPECTED_DOMAIN_CURRENT = 25  # post-PLAN-074 W4-W10 grandfather (sunset target)
_EXPECTED_INDIVIDUAL_CURRENT = 5


class TestStagedPolicyFileExists(TestEnvContext):
    """Case 1: Staged policy file exists and is valid YAML-ish."""

    def test_staged_policy_file_exists(self) -> None:
        self.assertTrue(
            _STAGED_POLICY.is_file(),
            f"Staged policy file not found at {_STAGED_POLICY}",
        )

    def test_staged_policy_parseable(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        caps = _parse_policy_cap(_STAGED_POLICY)
        # Both cap values should be parseable (not -1)
        self.assertGreater(caps["individual_cap"], 0, "individual_cap missing from policy")
        self.assertGreater(caps["domain_cap"], 0, "domain_cap missing from policy")


class TestIndividualSkillsCap(TestEnvContext):
    """Case 2: individual_skills cap check."""

    def test_individual_cap_matches_expected(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        caps = _parse_policy_cap(_STAGED_POLICY)
        self.assertEqual(
            caps["individual_cap"],
            _EXPECTED_INDIVIDUAL_CAP,
            f"individual_skills.cap should be {_EXPECTED_INDIVIDUAL_CAP}",
        )

    def test_individual_current_at_or_under_cap(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        caps = _parse_policy_cap(_STAGED_POLICY)
        if caps["individual_current"] < 0 or caps["individual_cap"] < 0:
            self.skipTest("individual cap/current not parseable")
        self.assertLessEqual(
            caps["individual_current"],
            caps["individual_cap"],
            f"individual_current ({caps['individual_current']}) exceeds "
            f"individual_cap ({caps['individual_cap']})",
        )

    def test_individual_members_count_matches_current(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        members = _parse_policy_members(_STAGED_POLICY, "individual_skills")
        caps = _parse_policy_cap(_STAGED_POLICY)
        if caps["individual_current"] >= 0:
            self.assertEqual(
                len(members),
                caps["individual_current"],
                f"individual_skills.members count ({len(members)}) != current "
                f"({caps['individual_current']})",
            )


class TestDomainBundlesCap(TestEnvContext):
    """Cases 3-5: domain_bundles cap + current + sunset."""

    def test_domain_cap_declared_correctly(self) -> None:
        """Case 3: domain_cap field is present and matches expected."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        caps = _parse_policy_cap(_STAGED_POLICY)
        self.assertEqual(
            caps["domain_cap"],
            _EXPECTED_DOMAIN_CAP,
            f"domain_bundles.cap should be {_EXPECTED_DOMAIN_CAP}",
        )

    def test_domain_current_documented(self) -> None:
        """Case 4: domain_current is documented (> 0)."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        caps = _parse_policy_cap(_STAGED_POLICY)
        self.assertGreater(caps["domain_current"], 0, "domain_current not documented")

    def test_domain_members_count_matches_current(self) -> None:
        """Case 5: member list count matches current field."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        members = _parse_policy_members(_STAGED_POLICY, "domain_bundles")
        caps = _parse_policy_cap(_STAGED_POLICY)
        if caps["domain_current"] >= 0:
            self.assertEqual(
                len(members),
                caps["domain_current"],
                f"domain_bundles.members count ({len(members)}) != current "
                f"({caps['domain_current']})",
            )


class TestSunsetFields(TestEnvContext):
    """Additional: sunset-related fields present."""

    def test_sunset_reopen_window_days_present(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        text = _STAGED_POLICY.read_text(encoding="utf-8")
        self.assertIn(
            "sunset_reopen_window_days",
            text,
            "sunset_reopen_window_days field missing from policy",
        )

    def test_sunset_reopen_unknown_excluded_flag(self) -> None:
        """M2-CDX-7: sunset_reopen_unknown_excluded: true must be present."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        text = _STAGED_POLICY.read_text(encoding="utf-8")
        self.assertIn(
            "sunset_reopen_unknown_excluded",
            text,
            "sunset_reopen_unknown_excluded flag missing (M2-CDX-7)",
        )
        self.assertIn(
            "sunset_reopen_unknown_excluded: true",
            text,
            "sunset_reopen_unknown_excluded must be true (M2-CDX-7)",
        )

    def test_deprecated_predecessor_documented(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        text = _STAGED_POLICY.read_text(encoding="utf-8")
        self.assertIn(
            "deprecated_predecessor",
            text,
            "deprecated_predecessor field missing from policy",
        )


# ---------------------------------------------------------------------------
# M2-CDX-3 (Codex Phase 1 iter 1) — enforce len(SQUAD_GRANDFATHER) <= cap
# ---------------------------------------------------------------------------

class TestSquadGrandfatherArrayLeqCap(TestEnvContext):
    """The CRITICAL governance gate per PLAN-080 §4 Phase 1b R-SEC-3 + M2-CDX-3.

    Asserts the actual length of SQUAD_GRANDFATHER bash array (in
    `validate-governance.sh:284`) is ≤ `domain_bundles.cap` declared in
    `grandfather-cap.policy.yaml`. This is the mechanical CI gate that
    fails on cap exceedance — the entire reason the policy file exists.
    """

    @staticmethod
    def _parse_squad_grandfather_array(validate_governance_path: Path) -> List[str]:
        """Parse the SQUAD_GRANDFATHER="..." bash array assignment."""
        if not validate_governance_path.is_file():
            return []
        text = validate_governance_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("SQUAD_GRANDFATHER="):
                # Format: SQUAD_GRANDFATHER="entry1 entry2 entry3 ..."
                value = stripped[len("SQUAD_GRANDFATHER="):]
                # Strip surrounding quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                return [e for e in value.split() if e]
        return []

    def _resolve_validate_governance(self) -> Path:
        # Prefer staged Phase 0b version (which drops sales/legal/devrel);
        # fall back to canonical (pre-ship state).
        staged_0b = (
            _REPO_ROOT / ".claude" / "plans" / "PLAN-080" / "staging" /
            "phase-0b" / "scripts" / "validate-governance.sh"
        )
        canonical = _REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
        if staged_0b.is_file():
            return staged_0b
        return canonical

    def test_squad_grandfather_within_policy_cap(self) -> None:
        """The MECHANICAL CAP GATE — fails CI if grandfather array exceeds cap."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        validate_path = self._resolve_validate_governance()
        if not validate_path.is_file():
            self.skipTest(f"validate-governance.sh not found at {validate_path}")
        members = self._parse_squad_grandfather_array(validate_path)
        if not members:
            self.skipTest("Could not parse SQUAD_GRANDFATHER from validate-governance.sh")
        caps = _parse_policy_cap(_STAGED_POLICY)
        cap = caps["domain_cap"]
        self.assertLessEqual(
            len(members),
            cap,
            f"SQUAD_GRANDFATHER count ({len(members)}) exceeds "
            f"domain_bundles.cap ({cap}) declared in {_STAGED_POLICY.name}. "
            f"Either trim the array (Phase 4 sunset) OR raise the cap with Owner approval.",
        )

    def test_squad_grandfather_matches_policy_current(self) -> None:
        """Sanity: SQUAD_GRANDFATHER count matches policy's `current` declaration."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        validate_path = self._resolve_validate_governance()
        if not validate_path.is_file():
            self.skipTest(f"validate-governance.sh not found at {validate_path}")
        members = self._parse_squad_grandfather_array(validate_path)
        if not members:
            self.skipTest("Could not parse SQUAD_GRANDFATHER")
        caps = _parse_policy_cap(_STAGED_POLICY)
        # current may legitimately be > or = len(members) during transitional
        # phases (Phase 1 ships with 22 entries; Phase 4 will lower to 15).
        self.assertEqual(
            len(members),
            caps["domain_current"],
            f"SQUAD_GRANDFATHER count ({len(members)}) != "
            f"domain_bundles.current ({caps['domain_current']}). "
            f"Sync the policy's current field with the actual array.",
        )


class TestSquadGrandfatherSetEqualsPolicyMembers(TestEnvContext):
    """PLAN-157 W0 tamper rider (debate consensus #5) — set-equality by NAME.

    Count-equality (the test above) cannot catch a swap tamper: removing
    squad A from the policy while adding squad B to the bash array keeps
    both counts identical. This gate asserts the two rosters contain the
    SAME names. Also note (recorded in PLAN-157): the reopen gate watches
    `domain_bundles.members` — squads sunset out of the policy leave its
    view, so this set-equality is the last mechanical tie between the two
    surfaces before a sunset lands.
    """

    def test_squad_grandfather_set_equals_policy_members(self) -> None:
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        validate_path = (
            _REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
        )
        if not validate_path.is_file():
            self.skipTest(f"validate-governance.sh not found at {validate_path}")
        array_members = (
            TestSquadGrandfatherArrayLeqCap._parse_squad_grandfather_array(
                validate_path
            )
        )
        if not array_members:
            self.skipTest("Could not parse SQUAD_GRANDFATHER")
        policy_members = _parse_policy_members(_STAGED_POLICY, "domain_bundles")
        if not policy_members:
            self.skipTest("Could not parse domain_bundles.members")
        array_set = set(array_members)
        policy_set = set(policy_members)
        only_in_array = sorted(array_set - policy_set)
        only_in_policy = sorted(policy_set - array_set)
        self.assertEqual(
            array_set,
            policy_set,
            "SQUAD_GRANDFATHER and domain_bundles.members diverge by NAME "
            f"(counts alone cannot catch a swap): only in bash array = "
            f"{only_in_array}; only in policy = {only_in_policy}. Every "
            f"sunset/graduation must remove the squad from BOTH surfaces "
            f"in the same commit (PLAN-157 commit-atomic rule).",
        )

    def test_no_duplicate_entries_either_surface(self) -> None:
        """A duplicated slug would let count-based gates drift silently."""
        if not _STAGED_POLICY.is_file():
            self.skipTest("Staged policy not found")
        validate_path = (
            _REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
        )
        if not validate_path.is_file():
            self.skipTest("validate-governance.sh not found")
        array_members = (
            TestSquadGrandfatherArrayLeqCap._parse_squad_grandfather_array(
                validate_path
            )
        )
        policy_members = _parse_policy_members(_STAGED_POLICY, "domain_bundles")
        self.assertEqual(
            len(array_members),
            len(set(array_members)),
            f"duplicate entries in SQUAD_GRANDFATHER: {array_members}",
        )
        self.assertEqual(
            len(policy_members),
            len(set(policy_members)),
            f"duplicate entries in domain_bundles.members: {policy_members}",
        )


if __name__ == "__main__":
    unittest.main()
