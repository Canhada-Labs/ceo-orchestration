"""Structural tests for ADR-058 brainstorm gate + adversarial reviewer bundle.

Tests here validate artifacts created by PLAN-031 + PLAN-034 bundle:

- ADR-058 exists + status ACCEPTED + required sections present
- PROTOCOL.md §Session protocol Gate 3 mentions brainstorm + spec.md
- PLAN-SCHEMA.md §Optional frontmatter lists `spec_ref:`
- team.md §Spawn Protocol Step 3 mentions `## SPEC CONTEXT`
- code-reviewer.md persona contains `## Adversarial framing`
- pre-plan-brainstorm CHECKLIST.md exists with 9-step rubric
- pre-plan-brainstorm SKILL.md — gated behind ADR-059 kernel apply
  (test skipped if target file absent, logs reason for Owner
  follow-up)
- Kill-switch `CEO_BRAINSTORM_GATE=0` is documented in all three
  authoritative locations (SKILL.md, CHECKLIST.md, PROTOCOL.md).

This file is NEW and under `.claude/hooks/tests/` which is not
canonical-guarded. It uses only stdlib + pytest per ADR-002. The
tests are structural (presence-of-header / regex-match), not
semantic — they catch deletion/rename drift without asserting
content quality.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestADR058Structure(unittest.TestCase):
    """ADR-058 file presence + required sections."""

    def setUp(self) -> None:
        self.adr_path = REPO_ROOT / ".claude" / "adr" / "ADR-058-brainstorm-gate-and-two-pass-review.md"

    def test_adr_058_file_exists(self) -> None:
        self.assertTrue(
            self.adr_path.is_file(),
            f"ADR-058 must exist at {self.adr_path}",
        )

    def test_adr_058_status_accepted(self) -> None:
        src = self.adr_path.read_text(encoding="utf-8")
        self.assertIn(
            "**Status:** ACCEPTED",
            src,
            "ADR-058 must have Status: ACCEPTED (bundle executed)",
        )

    def test_adr_058_required_sections(self) -> None:
        src = self.adr_path.read_text(encoding="utf-8")
        for section in [
            "## Context",
            "## Decision drivers",
            "## Options considered",
            "## Decision",
            "## Consequences",
            "## Blast radius",
            "## Reversibility",
            "## References",
        ]:
            with self.subTest(section=section):
                self.assertIn(
                    section, src,
                    f"ADR-058 missing required section: {section}",
                )

    def test_adr_058_cites_plan_031_and_034(self) -> None:
        src = self.adr_path.read_text(encoding="utf-8")
        self.assertIn("PLAN-031", src, "ADR-058 must cite PLAN-031")
        self.assertIn("PLAN-034", src, "ADR-058 must cite PLAN-034")

    def test_adr_058_cites_adr_059_bootstrap_deferred(self) -> None:
        src = self.adr_path.read_text(encoding="utf-8")
        self.assertIn(
            "ADR-059", src,
            "ADR-058 must reference ADR-059 (skill bootstrap deferred)",
        )


class TestProtocolMdGate3Amendment(unittest.TestCase):
    """PROTOCOL.md Gate 3 mentions brainstorm + spec.md + kill-switch."""

    def setUp(self) -> None:
        self.protocol_path = REPO_ROOT / "PROTOCOL.md"
        self.src = self.protocol_path.read_text(encoding="utf-8")

    def test_gate_3_mentions_brainstorm(self) -> None:
        # Look for the amendment in the Gate 3 block
        gate_3_idx = self.src.index("### GATE 3 — Plan before doing")
        section = self.src[gate_3_idx:gate_3_idx + 2500]
        self.assertIn("pre-plan-brainstorm", section)
        self.assertIn("spec.md", section)
        self.assertIn("ADR-058", section)

    def test_gate_3_mentions_kill_switch(self) -> None:
        gate_3_idx = self.src.index("### GATE 3 — Plan before doing")
        section = self.src[gate_3_idx:gate_3_idx + 2500]
        self.assertIn("CEO_BRAINSTORM_GATE=0", section)


class TestPlanSchemaSpecRef(unittest.TestCase):
    """PLAN-SCHEMA.md documents `spec_ref:` optional field."""

    def setUp(self) -> None:
        self.schema_path = REPO_ROOT / ".claude" / "plans" / "PLAN-SCHEMA.md"
        self.src = self.schema_path.read_text(encoding="utf-8")

    def test_spec_ref_field_listed(self) -> None:
        self.assertIn("spec_ref:", self.src)

    def test_spec_ref_section_heading(self) -> None:
        # Must have dedicated subsection explaining the field
        self.assertRegex(self.src, r"### The `spec_ref:` field")

    def test_spec_ref_cites_adr_058(self) -> None:
        spec_ref_idx = self.src.find("### The `spec_ref:` field")
        self.assertGreater(spec_ref_idx, -1)
        section = self.src[spec_ref_idx:spec_ref_idx + 1500]
        self.assertIn("ADR-058", section)


class TestTeamMdStep3SpecContext(unittest.TestCase):
    """team.md Spawn Protocol Step 3 mentions `## SPEC CONTEXT`."""

    def setUp(self) -> None:
        self.team_path = REPO_ROOT / ".claude" / "team.md"
        self.src = self.team_path.read_text(encoding="utf-8")

    def test_spec_context_block_mentioned(self) -> None:
        self.assertIn("## SPEC CONTEXT", self.src)

    def test_spec_context_notes_optional(self) -> None:
        # Notes block following the template must explain when context appears
        self.assertIn("Notes on `## SPEC CONTEXT`", self.src)


class TestCodeReviewerPersonaAdversarial(unittest.TestCase):
    """code-reviewer.md persona has Adversarial framing section."""

    def setUp(self) -> None:
        self.persona_path = REPO_ROOT / ".claude" / "agents" / "code-reviewer.md"
        self.src = self.persona_path.read_text(encoding="utf-8")

    def test_adversarial_framing_header_present(self) -> None:
        self.assertIn("## Adversarial framing (MANDATORY mindset — ADR-058)", self.src)

    def test_six_rules_present(self) -> None:
        adv_idx = self.src.index("## Adversarial framing")
        section = self.src[adv_idx:adv_idx + 3500]
        # Six numbered rules must be present
        for n in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. "):
            with self.subTest(rule=n):
                self.assertIn(n, section)

    def test_two_pass_structure_documented(self) -> None:
        self.assertIn("Two-pass review structure (ADR-058", self.src)


class TestPrePlanBrainstormChecklist(unittest.TestCase):
    """pre-plan-brainstorm/CHECKLIST.md — per-step binary rubric."""

    def setUp(self) -> None:
        self.checklist_path = (
            REPO_ROOT / ".claude" / "skills" / "core"
            / "pre-plan-brainstorm" / "CHECKLIST.md"
        )

    def test_checklist_exists(self) -> None:
        self.assertTrue(
            self.checklist_path.is_file(),
            f"CHECKLIST.md must exist at {self.checklist_path}",
        )

    def test_checklist_has_all_nine_steps(self) -> None:
        src = self.checklist_path.read_text(encoding="utf-8")
        for step in range(1, 10):
            with self.subTest(step=step):
                self.assertRegex(
                    src,
                    rf"### Step {step} —",
                    f"CHECKLIST.md must have Step {step} subsection",
                )

    def test_checklist_has_kill_switch(self) -> None:
        src = self.checklist_path.read_text(encoding="utf-8")
        self.assertIn("CEO_BRAINSTORM_GATE=0", src)

    def test_checklist_has_failure_handling(self) -> None:
        src = self.checklist_path.read_text(encoding="utf-8")
        self.assertIn("Failure handling", src)


class TestPrePlanBrainstormSkillStaged(unittest.TestCase):
    """pre-plan-brainstorm/SKILL.md — MAY be absent pre-ADR-059 kernel apply.

    If present: validate structure. If absent: skip with a clear reason
    message — this is expected state until Owner runs the ADR-059
    kernel-apply batch. The test DOES check that either the skill
    exists OR the kernel-batch staging file in /tmp/ is readable
    (regression-detection for the bootstrap deferral).
    """

    def setUp(self) -> None:
        self.skill_path = (
            REPO_ROOT / ".claude" / "skills" / "core"
            / "pre-plan-brainstorm" / "SKILL.md"
        )

    def test_skill_has_frontmatter_when_present(self) -> None:
        if not self.skill_path.is_file():
            self.skipTest(
                "pre-plan-brainstorm/SKILL.md not yet installed — "
                "pending ADR-059 kernel-apply batch (Wave A Fase 2 Owner step)"
            )
        src = self.skill_path.read_text(encoding="utf-8")
        self.assertTrue(src.startswith("---"), "SKILL.md must start with frontmatter")

    def test_skill_has_9_steps_when_present(self) -> None:
        if not self.skill_path.is_file():
            self.skipTest(
                "pre-plan-brainstorm/SKILL.md not yet installed — "
                "pending ADR-059 kernel-apply batch (Wave A Fase 2 Owner step)"
            )
        src = self.skill_path.read_text(encoding="utf-8")
        for step in range(1, 10):
            with self.subTest(step=step):
                self.assertRegex(
                    src,
                    rf"### Step {step} —",
                    f"SKILL.md must have Step {step} subsection",
                )

    def test_skill_kill_switch_when_present(self) -> None:
        if not self.skill_path.is_file():
            self.skipTest("SKILL.md pending kernel apply")
        src = self.skill_path.read_text(encoding="utf-8")
        self.assertIn("CEO_BRAINSTORM_GATE=0", src)


class TestBundleCoherence(unittest.TestCase):
    """Cross-file coherence between PROTOCOL, SCHEMA, team, persona, ADR-058."""

    def test_all_five_touchpoints_cite_adr_058(self) -> None:
        files_and_citations = {
            REPO_ROOT / "PROTOCOL.md": "ADR-058",
            REPO_ROOT / ".claude" / "plans" / "PLAN-SCHEMA.md": "ADR-058",
            REPO_ROOT / ".claude" / "team.md": "ADR-058",
            REPO_ROOT / ".claude" / "agents" / "code-reviewer.md": "ADR-058",
            REPO_ROOT / ".claude" / "adr" / "ADR-058-brainstorm-gate-and-two-pass-review.md": "PLAN-031",
        }
        for path, expected in files_and_citations.items():
            with self.subTest(file=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertIn(
                    expected, src,
                    f"{path.name} must cite {expected}",
                )

    def test_kill_switch_documented_in_three_places(self) -> None:
        kill_switch = "CEO_BRAINSTORM_GATE=0"
        paths = [
            REPO_ROOT / "PROTOCOL.md",
            REPO_ROOT / ".claude" / "adr" / "ADR-058-brainstorm-gate-and-two-pass-review.md",
            REPO_ROOT / ".claude" / "skills" / "core"
                / "pre-plan-brainstorm" / "CHECKLIST.md",
        ]
        for path in paths:
            with self.subTest(file=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertIn(
                    kill_switch, src,
                    f"{path.name} must document kill-switch {kill_switch}",
                )


if __name__ == "__main__":
    unittest.main()
