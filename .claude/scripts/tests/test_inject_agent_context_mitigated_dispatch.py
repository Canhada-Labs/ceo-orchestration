"""PLAN-060 Layer 7c + PLAN-061 / ADR-082 — inject-agent-context.sh dispatch tests.

Layer 7c (PLAN-060): the `--dispatch=mitigated` flag emits a header
instructing the caller to dispatch via the BUILT-IN subagent_type
"general-purpose" instead of the original custom archetype, bypassing
the H4 rail anomaly (custom subagent_types qa/pe/se/devops receive only
Grep+Glob from the Claude Code runtime despite frontmatter declaring
full tools).

PLAN-061 (ADR-082): the dispatch mode now resolves per archetype.
Default `native` for `code-reviewer` (full tool grant works empirically;
preserves ADR-052 VETO floor). Default `mitigated` for non-`code-reviewer`
archetypes. Resolution precedence (highest first):
    kill-switch > --dispatch flag > CEO_DISPATCHER_MODE env > archetype default

Documented in:
    .claude/plans/PLAN-060/audit/round-2/h4-layer7c-mitigation-via-general-purpose.md
    .claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md §Layer 7c
    .claude/adr/ADR-082-l7c-mitigation-default-on.md
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "inject-agent-context.sh"

MITIGATION_HEADER_MARKER = "## DISPATCH MITIGATION — PLAN-060 Layer 7c"
GP_DISPATCH_INSTRUCTION = 'Task(subagent_type="general-purpose"'


def _run(*args, env_extra=None):
    env = {**os.environ}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


class MitigatedDispatchTest(unittest.TestCase):

    def test_default_dispatch_is_native(self):
        result = _run("Staff Code Reviewer", "review")
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn("## AGENT PROFILE", result.stdout)

    def test_mitigated_flag_emits_header(self):
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn(GP_DISPATCH_INSTRUCTION, result.stdout)

    def test_mitigated_header_appears_before_agent_profile(self):
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        header_idx = result.stdout.find(MITIGATION_HEADER_MARKER)
        profile_idx = result.stdout.find("## AGENT PROFILE")
        self.assertGreater(header_idx, -1)
        self.assertGreater(profile_idx, -1)
        self.assertLess(header_idx, profile_idx)

    def test_native_flag_explicit_no_header(self):
        result = _run("--dispatch=native", "Staff Code Reviewer", "review")
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_env_var_dispatcher_mode_mitigated_activates(self):
        result = _run(
            "Staff Code Reviewer", "review",
            env_extra={"CEO_DISPATCHER_MODE": "mitigated"},
        )
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn(GP_DISPATCH_INSTRUCTION, result.stdout)

    def test_kill_switch_overrides_env_var(self):
        result = _run(
            "Staff Code Reviewer", "review",
            env_extra={
                "CEO_DISPATCHER_MODE": "mitigated",
                "CEO_MITIGATION_DISABLE": "1",
            },
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_kill_switch_overrides_explicit_flag(self):
        # Even when caller passes --dispatch=mitigated, kill-switch wins.
        result = _run(
            "--dispatch=mitigated", "Staff Code Reviewer", "review",
            env_extra={"CEO_MITIGATION_DISABLE": "1"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_mitigated_combines_with_skill_reference_mode(self):
        # --dispatch=mitigated is orthogonal to --mode=reference.
        result = _run(
            "--mode=reference", "--dispatch=mitigated",
            "Staff Code Reviewer", "review",
        )
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn("## SKILL REFERENCE", result.stdout)

    def test_mitigated_combines_with_inline_mode(self):
        result = _run(
            "--mode=inline", "--dispatch=mitigated",
            "Staff Code Reviewer", "review",
        )
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn("## SKILL CONTENT", result.stdout)

    def test_mitigated_flag_order_independent(self):
        # --dispatch=mitigated before --mode=reference works.
        result_a = _run(
            "--dispatch=mitigated", "--mode=reference",
            "Staff Code Reviewer", "review",
        )
        # --mode=reference before --dispatch=mitigated also works.
        result_b = _run(
            "--mode=reference", "--dispatch=mitigated",
            "Staff Code Reviewer", "review",
        )
        self.assertIn(MITIGATION_HEADER_MARKER, result_a.stdout)
        self.assertIn(MITIGATION_HEADER_MARKER, result_b.stdout)

    def test_mitigation_header_references_plan_and_adr(self):
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        self.assertIn("PLAN-060", result.stdout)
        self.assertIn("ADR-080", result.stdout)

    def test_mitigation_header_documents_kill_switch(self):
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        self.assertIn("CEO_MITIGATION_DISABLE", result.stdout)

    def test_mitigated_header_appears_only_once(self):
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        count = result.stdout.count(MITIGATION_HEADER_MARKER)
        self.assertEqual(count, 1)

    def test_unrecognized_dispatch_value_falls_through_as_arg(self):
        # --dispatch=foo is not a recognized flag → treated as positional
        # AGENT_NAME, which fails whitelist (contains '=').
        result = _run("--dispatch=foo", "Staff Code Reviewer", "review")
        # The script will reject AGENT_NAME validation with exit 2 OR
        # treat it as Agent Name not found. Either way, no mitigation
        # header should appear (since flag wasn't recognized).
        # We just assert script doesn't crash with non-zero exit due to
        # bash unbound-variable error.
        self.assertIn(result.returncode, [0, 1, 2])


class ArchetypeDefaultTest(unittest.TestCase):
    """PLAN-061 / ADR-082 — per-archetype default-on resolution.

    Without flag/env override, dispatch mode is resolved per archetype:
    - `code-reviewer` archetype (skill `code-review-checklist`) → native
    - all other archetypes → mitigated
    - unknown archetype → mitigated (safer prod posture)

    Precedence: kill-switch > --dispatch flag > env var > archetype default.
    """

    def test_code_reviewer_default_remains_native(self):
        # Staff Code Reviewer maps to skill code-review-checklist in the
        # SKILL MAP → archetype default native → no mitigation header.
        result = _run("Staff Code Reviewer", "review")
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_qa_architect_default_is_mitigated(self):
        # Principal QA Architect maps to skill testing-strategy →
        # archetype default mitigated → mitigation header emitted.
        result = _run("Principal QA Architect", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)
        self.assertIn(GP_DISPATCH_INSTRUCTION, result.stdout)

    def test_security_engineer_default_is_mitigated(self):
        # Security Engineer maps to skill security-and-auth →
        # archetype default mitigated.
        result = _run("Security Engineer", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_performance_engineer_default_is_mitigated(self):
        # Principal Performance Engineer → performance-engineering →
        # archetype default mitigated.
        result = _run("Principal Performance Engineer", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_devops_engineer_default_is_mitigated(self):
        # DevOps Engineer → devops-ci-cd → archetype default mitigated.
        result = _run("DevOps Engineer", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_unknown_archetype_default_is_mitigated(self):
        # Unknown archetype name (no SKILL MAP entry) → safer prod posture
        # of mitigated. AGENT_NAME passes whitelist (letters + spaces +
        # max 61 chars) but no skill is found.
        result = _run("Totally Unknown Persona", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_explicit_native_flag_overrides_qa_default(self):
        # --dispatch=native > archetype default mitigated for QA.
        result = _run("--dispatch=native", "Principal QA Architect", "review")
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_explicit_mitigated_flag_overrides_cr_default(self):
        # --dispatch=mitigated > archetype default native for cr.
        result = _run("--dispatch=mitigated", "Staff Code Reviewer", "review")
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_env_native_overrides_qa_default(self):
        # CEO_DISPATCHER_MODE=native > archetype default mitigated.
        result = _run(
            "Principal QA Architect", "review",
            env_extra={"CEO_DISPATCHER_MODE": "native"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_env_mitigated_overrides_cr_default(self):
        # CEO_DISPATCHER_MODE=mitigated > archetype default native for cr.
        result = _run(
            "Staff Code Reviewer", "review",
            env_extra={"CEO_DISPATCHER_MODE": "mitigated"},
        )
        self.assertIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_kill_switch_universal_for_qa(self):
        # Kill-switch wins over archetype default for non-cr archetypes.
        result = _run(
            "Principal QA Architect", "review",
            env_extra={"CEO_MITIGATION_DISABLE": "1"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_flag_beats_env_for_qa(self):
        # Precedence: flag > env. flag=native + env=mitigated → native.
        result = _run(
            "--dispatch=native", "Principal QA Architect", "review",
            env_extra={"CEO_DISPATCHER_MODE": "mitigated"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_env_beats_archetype_default_for_qa(self):
        # Precedence: env > archetype default. env=native + qa archetype
        # default mitigated → native.
        result = _run(
            "Principal QA Architect", "review",
            env_extra={"CEO_DISPATCHER_MODE": "native"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)

    def test_kill_switch_beats_flag_for_qa(self):
        # Precedence: kill-switch > flag. Even --dispatch=mitigated yields
        # native when kill-switch is set.
        result = _run(
            "--dispatch=mitigated", "Principal QA Architect", "review",
            env_extra={"CEO_MITIGATION_DISABLE": "1"},
        )
        self.assertNotIn(MITIGATION_HEADER_MARKER, result.stdout)


if __name__ == "__main__":
    unittest.main()
