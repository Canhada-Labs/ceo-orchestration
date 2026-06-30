"""Tests for validate-squad-contract.py.

PLAN-010 Phase 7a (debate C4): programmatic assertion of ADR-009
minimum-count contract. Exercises happy path (using fintech as the
reference "known good" fixture shape — post-PLAN-080 Phase 0a the
former lgpd-heavy-saas fixture was deprecated when its 3 PII skills
were promoted to core and the squad became a grandfathered 0-skill
placeholder per ADR-111/112) + the failure modes called out in the
PLAN-010 task spec: missing pitfalls file, < 12 pitfalls, < 2 task
chains, task-chain references non-existent skill, < 2 VETO holders.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))

_SCRIPT = _SCRIPTS / "validate-squad-contract.py"
_spec = importlib.util.spec_from_file_location("validate_squad_contract", _SCRIPT)
vsc = importlib.util.module_from_spec(_spec)
sys.modules["validate_squad_contract"] = vsc
_spec.loader.exec_module(vsc)


# Real squads reused as "known good" fixture input (each has skills/ + the
# ADR-009 5-artifact bundle). PLAN-080 Phase 0a deprecated lgpd-heavy-saas
# for this purpose: its 3 PII skills were promoted to core (ADR-111), the
# squad is now a 0-skill grandfathered placeholder (ADR-112). edtech +
# trading-hft cover the happy-path regression role.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_EDTECH_SQUAD = _REPO_ROOT / ".claude" / "skills" / "domains" / "edtech"
_TRADING_SQUAD = _REPO_ROOT / ".claude" / "skills" / "domains" / "trading-hft"


def _mkpitfalls(n: int) -> str:
    lines = ["pitfalls:"]
    for i in range(n):
        lines.append(f"  - id: TEST-{i:03d}")
        lines.append(f"    rule: \"Test pitfall number {i}.\"")
        lines.append(f"    whenToUse: \"test context {i}\"")
        lines.append(f"    agents: [Alice Tester]")
    return "\n".join(lines) + "\n"


def _mkchains(n: int, skill_refs=None) -> str:
    lines = ["task_chains:"]
    for i in range(n):
        lines.append(f"  - id: chain-{i}")
        lines.append(f"    title: \"Test chain {i}\"")
        lines.append(f"    whenToUse: \"test\"")
        lines.append(f"    steps:")
        lines.append(f"      - id: 1")
        lines.append(f"        owner: \"Alice Tester\"")
        lines.append(f"        action: \"do a thing\"")
        if skill_refs and i < len(skill_refs):
            lines.append(f"        skill: {skill_refs[i]}")
    return "\n".join(lines) + "\n"


_VALID_TEAM_MD = """\
# Team Personas — Test Squad

## Squad vetoes

| Persona | VETO scope |
|---|---|
| **Alice Tester** (Privacy Engineer) | Any change that touches privacy |
| **Bob Builder** (Security Engineer) | Any cryptographic / access-control change |

---

### 1. Alice Tester — Privacy Engineer

Background.

### 2. Bob Builder — Security Engineer

Background.

### 3. Carol Checker — QA

Background.

### 4. Dan Dev — Engineer

Background.

### 5. Eve Eng — Engineer

Background.
"""


class ValidateSquadContractTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="squad-contract-test-"))
        self.squad = self.tmp / "testsquad"
        self.squad.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_valid_squad(self):
        (self.squad / "team-personas.md").write_text(_VALID_TEAM_MD, encoding="utf-8")
        (self.squad / "pitfalls.yaml").write_text(_mkpitfalls(12), encoding="utf-8")
        (self.squad / "task-chains.yaml").write_text(_mkchains(2), encoding="utf-8")
        skills = self.squad / "skills"
        skills.mkdir()
        for name in ("skill-alpha", "skill-beta", "skill-gamma"):
            d = skills / name
            d.mkdir()
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: test\n---\n# {name}\n", encoding="utf-8"
            )

    # --- happy-path ---

    def test_real_grandfathered_lgpd_squad_excluded(self):
        """Regression: lgpd-heavy-saas — a 0-skill grandfathered placeholder
        post PLAN-080 Phase 0a (PII skills promoted to core per ADR-111) —
        legitimately FAILS the squad contract. It is exempted from
        validate-governance.sh via SQUAD_GRANDFATHER, not by passing the
        contract. The edtech + trading-hft happy-path tests below cover
        the positive regression role this test used to fill.
        """
        lgpd_squad = _REPO_ROOT / ".claude" / "skills" / "domains" / "lgpd-heavy-saas"
        self.assertTrue(lgpd_squad.is_dir(), "lgpd-heavy-saas dir not found on disk")
        ok, reasons = vsc.validate_squad(lgpd_squad)
        self.assertFalse(ok, "lgpd-heavy-saas should fail squad contract post-PLAN-080")
        self.assertTrue(
            any("skills/" in r for r in reasons),
            f"expected missing-skills failure, got reasons={reasons}",
        )

    def test_real_edtech_squad_passes(self):
        """PLAN-010 Phase 7a: the new edtech squad must satisfy the contract."""
        self.assertTrue(_EDTECH_SQUAD.is_dir(), "edtech squad not found on disk")
        ok, reasons = vsc.validate_squad(_EDTECH_SQUAD)
        self.assertTrue(ok, f"edtech must pass; reasons={reasons}")

    def test_real_trading_hft_squad_passes(self):
        """Regression: trading-hft squad passes despite different VETO declaration style."""
        self.assertTrue(_TRADING_SQUAD.is_dir(), "trading-hft squad not found on disk")
        ok, reasons = vsc.validate_squad(_TRADING_SQUAD)
        self.assertTrue(ok, f"trading-hft must pass; reasons={reasons}")

    def test_synthetic_valid_squad_passes(self):
        self._write_valid_squad()
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertTrue(ok, f"valid synthetic squad must pass; reasons={reasons}")

    # --- failure modes per PLAN-010 spec ---

    def test_missing_pitfalls_file(self):
        self._write_valid_squad()
        (self.squad / "pitfalls.yaml").unlink()
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertFalse(ok)
        self.assertTrue(any("pitfalls" in r for r in reasons))

    def test_fewer_than_12_pitfalls(self):
        self._write_valid_squad()
        (self.squad / "pitfalls.yaml").write_text(_mkpitfalls(11), encoding="utf-8")
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertFalse(ok)
        self.assertTrue(any("12" in r and "pitfalls" in r for r in reasons))

    def test_fewer_than_2_task_chains(self):
        self._write_valid_squad()
        (self.squad / "task-chains.yaml").write_text(_mkchains(1), encoding="utf-8")
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertFalse(ok)
        self.assertTrue(any("chains" in r.lower() for r in reasons))

    def test_task_chain_references_unknown_skill(self):
        self._write_valid_squad()
        (self.squad / "task-chains.yaml").write_text(
            _mkchains(2, skill_refs=["nonexistent-skill-xyz", "also-missing"]),
            encoding="utf-8",
        )
        ok, reasons = vsc.validate_squad(self.squad, core_skills_dir=self.tmp / "no-core")
        self.assertFalse(ok)
        self.assertTrue(
            any("unknown skill" in r or "nonexistent" in r for r in reasons),
            f"expected unknown-skill reason; got {reasons}",
        )

    def test_fewer_than_2_veto_holders(self):
        self._write_valid_squad()
        trimmed = _VALID_TEAM_MD.replace(
            "| **Bob Builder** (Security Engineer) | Any cryptographic / access-control change |\n",
            "",
        )
        (self.squad / "team-personas.md").write_text(trimmed, encoding="utf-8")
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertFalse(ok)
        self.assertTrue(any("VETO" in r for r in reasons))

    def test_fewer_than_3_skills(self):
        self._write_valid_squad()
        shutil.rmtree(self.squad / "skills" / "skill-gamma")
        ok, reasons = vsc.validate_squad(self.squad)
        self.assertFalse(ok)
        self.assertTrue(any("SKILL.md subdirs" in r for r in reasons))

    def test_squad_path_does_not_exist(self):
        ok, reasons = vsc.validate_squad(self.tmp / "does-not-exist")
        self.assertFalse(ok)
        self.assertTrue(any("does not exist" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
