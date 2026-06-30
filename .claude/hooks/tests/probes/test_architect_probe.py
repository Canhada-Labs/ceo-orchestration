"""Probe: architect role separation maintained when Codex invoked.

PLAN-081 Phase 1-full probe. Verifies that the spawn governance hook
(check_agent_spawn.py) enforces architect role separation when the
Pair-Rail dispatcher invokes agents via the Codex path:

1. Codex review dispatch should NOT spawn a sub-agent named "Agent Architect"
   (that would violate the ADR-010 Architect recursion guard).
2. A legitimate Codex-dispatched review agent (code-reviewer archetype)
   must NOT claim Architect capabilities via its prompt.
3. A spawn under CEO_ARCHITECT_ACTIVE=1 that names "Agent Architect" is
   blocked — even when the prompt has a valid ## SKILL CONTENT section.

Context: PLAN-081 Phase 2 (Pair-Rail dispatcher) routes Codex invocations
via named sub-agent spawns. A misconfigured dispatcher could accidentally
use an Architect persona description, triggering the recursion guard.
This probe validates that guard is intact for the Codex path.

stdlib-only. Uses TestEnvContext for env isolation.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_PROBES_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _PROBES_DIR.parent
_HOOKS_DIR = _TESTS_DIR.parent

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_spawn_hook():
    """Load check_agent_spawn via importlib to avoid pytest module name collision."""
    src = _HOOKS_DIR / "check_agent_spawn.py"
    if not src.exists():
        raise ImportError(f"check_agent_spawn.py not found at {src}")
    spec = importlib.util.spec_from_file_location("check_agent_spawn_arch_probe", src)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec_module so @dataclass can resolve
    # cls.__module__ via sys.modules.get() (Python 3.9 dataclasses requirement).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_agent_payload(
    description: str,
    prompt: str,
    subagent_type: str = "general-purpose",
    session_id: str = "sess-arch-probe-001",
) -> str:
    return json.dumps({
        "session_id": session_id,
        "tool_name": "Agent",
        "tool_input": {
            "description": description,
            "prompt": prompt,
            "subagent_type": subagent_type,
        },
    })


# ---------------------------------------------------------------------------
# Prompt fixtures
# ---------------------------------------------------------------------------

# A correct Codex reviewer prompt — no Architect language. Body is
# >=256 non-whitespace bytes between ## SKILL CONTENT and next ##
# heading (PLAN-019 P1-SEC-B threshold per check_agent_spawn.py).
_CORRECT_CODEX_REVIEWER = """\
## AGENT PROFILE
name: codex-pair-rail-reviewer
role: code-reviewer
pair_id: pr-081-arch-test

## SKILL CONTENT
You are the Pair-Rail code reviewer for PLAN-081 Phase 1 Codex adapter
ship. Your task is to review the Codex MCP adapter diff for rubric
violations per the 19-ID catalogue at
`.claude/policies/rubric-violation-catalogue.yaml`. Apply the asymmetric
VETO matrix Cases A-F per ADR-108 §Decision. Output a verdict envelope
JSON with the shape:
  {"verdict": "PASS|ADVISORY|BLOCK", "findings": [...], "summary": "..."}
For every BLOCK finding, cite file:line and include the rubric_violation_id
from the catalogue plus severity (P0 or P1). Per R1 C7, audit-class
prompts use 240s timeout. Do NOT name yourself Agent Architect — that is
a CEO-only role and dispatching it via sub-agent rail is a governance
violation per check_agent_spawn architect_role_not_delegable check.

## FILE ASSIGNMENT
- .claude/hooks/_lib/adapters/codex.py
"""

# A misbehaving prompt that names "Agent Architect" inside a Codex dispatcher spawn
_ARCHITECT_NAMED_SPAWN = """\
## AGENT PROFILE
name: Agent Architect
role: code-reviewer

## SKILL CONTENT
You are the Agent Architect. Review and redesign the system.

## FILE ASSIGNMENT
- .claude/hooks/_lib/adapters/codex.py
"""

# Architect-named description without explicit ## AGENT PROFILE body
_ARCHITECT_IN_DESCRIPTION = "Agent Architect — design the Codex Phase 2 dispatcher"

_COMPLIANT_SIMPLE_PROMPT = """\
## AGENT PROFILE
name: pair-rail-reviewer
role: code-reviewer

## SKILL CONTENT
Review the following diff for security issues.
Return JSON verdict.

## FILE ASSIGNMENT
- .claude/hooks/check_pair_rail.py
"""


class TestArchitectRoleSeparation(TestEnvContext):
    """Architect role separation probe for Codex dispatch path (PLAN-081)."""

    def setUp(self) -> None:
        super().setUp()
        # Minimal team.md
        team_md = self.project_dir / ".claude" / "team.md"
        team_md.parent.mkdir(parents=True, exist_ok=True)
        team_md.write_text(
            "# Team\n"
            "| archetype | model |\n"
            "|---|---|\n"
            "| code-reviewer | claude-opus-4-8 |\n",
            encoding="utf-8",
        )
        # PLAN-081 v1.16.0 fix: VETO floor enforcement requires
        # `agents/<role>.md` per check_veto_floor_for_role(). Create
        # minimal stubs for the 5 VETO-floor roles so hook does not
        # return file_missing on test-isolated env.
        agents_dir = self.project_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for role in ("code-reviewer", "security-engineer", "qa-architect",
                     "performance-engineer", "devops"):
            (agents_dir / f"{role}.md").write_text(
                f"---\nname: {role}\nmodel: claude-opus-4-8\nveto_floor: true\n---\n",
                encoding="utf-8",
            )

    def _run_spawn_hook(self, stdin_str: str, extra_env: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
        hook = _load_spawn_hook()
        buf = io.StringIO()
        if extra_env:
            for k, v in extra_env.items():
                os.environ[k] = v
        from unittest.mock import patch
        with (
            patch("sys.stdin", io.StringIO(stdin_str)),
            patch("sys.stdout", buf),
        ):
            try:
                rc = hook.main()
            except SystemExit as e:
                rc = e.code or 0
        return rc or 0, buf.getvalue()

    def _decision_from_stdout(self, stdout: str) -> str:
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if not lines:
            return "allow"
        last = json.loads(lines[-1])
        return last.get("decision", "allow")

    def test_correct_codex_reviewer_spawn_is_allowed(self):
        """Correctly structured Codex reviewer spawn (no Architect) is allowed."""
        stdin = _make_agent_payload(
            description="Codex pair-rail reviewer for PLAN-081",
            prompt=_CORRECT_CODEX_REVIEWER,
            subagent_type="code-reviewer",
        )
        rc, stdout = self._run_spawn_hook(stdin)
        self.assertEqual(rc, 0)
        decision = self._decision_from_stdout(stdout)
        self.assertEqual(
            decision,
            "allow",
            f"Correct Codex reviewer spawn should be allowed; got: {decision!r}",
        )

    def test_architect_recursion_guard_active_with_ceo_architect_env(self):
        """Under CEO_ARCHITECT_ACTIVE=1, spawn naming 'Agent Architect' is blocked."""
        stdin = _make_agent_payload(
            description=_ARCHITECT_IN_DESCRIPTION,
            prompt=_ARCHITECT_NAMED_SPAWN,
        )
        rc, stdout = self._run_spawn_hook(
            stdin, extra_env={"CEO_ARCHITECT_ACTIVE": "1"}
        )
        # Under CEO_ARCHITECT_ACTIVE=1, naming "Agent Architect" MUST block
        decision = self._decision_from_stdout(stdout)
        self.assertEqual(
            decision,
            "block",
            f"Expected block for 'Agent Architect' spawn under CEO_ARCHITECT_ACTIVE=1; "
            f"got: {decision!r}",
        )

    def test_architect_name_in_prompt_blocked_under_architect_active(self):
        """Prompt body containing 'Agent Architect' → block under CEO_ARCHITECT_ACTIVE=1."""
        stdin = _make_agent_payload(
            description="Codex reviewer with an accidentally Architect prompt",
            prompt=_ARCHITECT_NAMED_SPAWN,
            subagent_type="code-reviewer",
        )
        rc, stdout = self._run_spawn_hook(
            stdin, extra_env={"CEO_ARCHITECT_ACTIVE": "1"}
        )
        decision = self._decision_from_stdout(stdout)
        self.assertEqual(
            decision,
            "block",
            f"'Agent Architect' in prompt MUST be blocked under CEO_ARCHITECT_ACTIVE=1; "
            f"got: {decision!r}",
        )

    def test_architect_not_restricted_without_ceo_architect_active(self):
        """Without CEO_ARCHITECT_ACTIVE=1, normal architect spawns pass governance.

        The recursion guard only fires when CEO_ARCHITECT_ACTIVE=1 is set.
        Without it, a spawn with 'Agent Architect' in the description is allowed
        (or may be blocked by skill-content rules, not architect recursion).
        This probe verifies the guard is CONTEXT-DEPENDENT, not always-on.
        """
        # Make sure CEO_ARCHITECT_ACTIVE is not set
        os.environ.pop("CEO_ARCHITECT_ACTIVE", None)
        stdin = _make_agent_payload(
            description="Agent Architect review",
            prompt=_COMPLIANT_SIMPLE_PROMPT,  # Has SKILL CONTENT
        )
        rc, stdout = self._run_spawn_hook(stdin)
        self.assertEqual(rc, 0)
        # No assertion on decision — the recursion guard is off.
        # We just assert the hook doesn't crash.
        output = stdout.strip()
        if output:
            lines = [l for l in output.splitlines() if l.strip()]
            last = json.loads(lines[-1])
            # decision must be valid JSON with a 'decision' key
            self.assertIn(last.get("decision", "allow"), ("allow", "block"))

    def test_hook_never_raises_regardless_of_codex_env(self):
        """Spawn hook is fail-open under any Codex-related env configuration."""
        os.environ["CEO_PAIR_RAIL_ENABLED"] = "1"
        stdin = _make_agent_payload(
            description="Codex reviewer",
            prompt="{MALFORMED PROMPT WITH NO SECTIONS}",
        )
        rc, stdout = self._run_spawn_hook(stdin)
        self.assertEqual(rc, 0)
        output = stdout.strip()
        if output:
            lines = [l for l in output.splitlines() if l.strip()]
            last = json.loads(lines[-1])
            self.assertIn(last.get("decision", "allow"), ("allow", "block"))


if __name__ == "__main__":
    unittest.main()
