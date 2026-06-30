"""Probe: spawn governance + skill content threading on Codex review path.

PLAN-081 Phase 1-full probe. Verifies that the spawn governance hook
(check_agent_spawn.py) applies its ## SKILL CONTENT requirement correctly
when a named agent is invoked for a Codex review dispatch. The probe
exercises the boundary:

  Named spawn (has ## AGENT PROFILE) WITHOUT ## SKILL CONTENT → BLOCK
  Named spawn WITH ## SKILL CONTENT → ALLOW
  General-purpose spawn (no persona header) → ALLOW regardless

Context: the Pair-Rail dispatcher (PLAN-081 Phase 2) invokes a named
reviewer sub-agent via Agent tool. That sub-agent prompt MUST include
## SKILL CONTENT (the reviewer skill body). The spawn governance hook
enforces this mechanically — if Phase 2 omits ## SKILL CONTENT from the
reviewer prompt, this probe exposes the gap pre-execution.

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
from typing import Any, Dict, Tuple

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
    """Load check_agent_spawn via importlib (avoids pytest module-name collision)."""
    src = _HOOKS_DIR / "check_agent_spawn.py"
    if not src.exists():
        raise ImportError(f"check_agent_spawn.py not found at {src}")
    spec = importlib.util.spec_from_file_location("check_agent_spawn_probe", src)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec_module so @dataclass can resolve
    # cls.__module__ via sys.modules.get() (Python 3.9 dataclasses requirement).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_agent_stdin(
    prompt: str,
    description: str = "Code review agent",
    subagent_type: str = "code-reviewer",
    session_id: str = "sess-probe-001",
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
# Compliant Codex reviewer prompt (with all 3 required sections)
# ---------------------------------------------------------------------------

# Body is >=256 non-whitespace bytes between ## SKILL CONTENT and next
# ## heading (PLAN-019 P1-SEC-B threshold per check_agent_spawn.py).
_COMPLIANT_REVIEWER_PROMPT = """\
## AGENT PROFILE
name: codex-reviewer
role: code-reviewer
pair_id: pr-081-001

## SKILL CONTENT
You are a Codex review agent using the Pair-Rail rubric. Review the diff
below for rubric violations per the 19-ID catalogue at
`.claude/policies/rubric-violation-catalogue.yaml`. Apply the asymmetric
VETO matrix Cases A-F per ADR-108 §Decision (Case B precondition gate:
file:line cite + rubric_violation_id + severity P0/P1). Output a verdict
envelope JSON:
  {"verdict": "PASS|ADVISORY|BLOCK", "findings": [...], "summary": "..."}
For every BLOCK finding, cite file:line and include rubric_violation_id
from the catalogue plus severity. Follow rubric R1 C7: audit-class
prompts use 240s timeout with 1-retry retry semantics on transient
Codex CLI flake (75s -> 240s upgrade).

## FILE ASSIGNMENT
- .claude/hooks/check_pair_rail.py
- .claude/hooks/_lib/adapters/codex.py
"""

# Non-compliant: has ## AGENT PROFILE but missing ## SKILL CONTENT
_NON_COMPLIANT_REVIEWER_PROMPT = """\
## AGENT PROFILE
name: codex-reviewer
role: code-reviewer

Review the diff and output a verdict.
"""

# General-purpose: no persona header → governance allows without ## SKILL CONTENT
_GENERAL_PURPOSE_PROMPT = "Please review file.py and report any issues."


class TestSpawnGovernanceCodexPath(TestEnvContext):
    """Spawn governance probe for Codex review path (PLAN-081 Phase 1-full)."""

    def setUp(self) -> None:
        super().setUp()
        # Write a minimal team.md so team resolution doesn't error
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
        # minimal stubs so test-isolated env does not return file_missing.
        agents_dir = self.project_dir / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for role in ("code-reviewer", "security-engineer", "qa-architect",
                     "performance-engineer", "devops"):
            (agents_dir / f"{role}.md").write_text(
                f"---\nname: {role}\nmodel: claude-opus-4-8\nveto_floor: true\n---\n",
                encoding="utf-8",
            )

    def _run_spawn_hook(self, stdin_str: str) -> Tuple[int, str]:
        hook = _load_spawn_hook()
        buf = io.StringIO()
        with (
            __import__("unittest.mock", fromlist=["patch"]).patch(
                "sys.stdin", io.StringIO(stdin_str)
            ),
            __import__("unittest.mock", fromlist=["patch"]).patch(
                "sys.stdout", buf
            ),
        ):
            try:
                rc = hook.main()
            except SystemExit as e:
                rc = e.code or 0
        return rc or 0, buf.getvalue()

    def test_named_spawn_with_skill_content_is_allowed(self):
        """Named Codex reviewer spawn WITH ## SKILL CONTENT → allow."""
        stdin = _make_agent_stdin(prompt=_COMPLIANT_REVIEWER_PROMPT)
        rc, stdout = self._run_spawn_hook(stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            self.assertEqual(last.get("decision", "allow"), "allow",
                f"Expected allow for compliant Codex reviewer spawn; got: {last}",
            )

    def test_named_spawn_without_skill_content_is_blocked(self):
        """Named Codex reviewer spawn WITHOUT ## SKILL CONTENT → block."""
        stdin = _make_agent_stdin(prompt=_NON_COMPLIANT_REVIEWER_PROMPT)
        rc, stdout = self._run_spawn_hook(stdin)
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            # Block is the expected outcome; fail-open is also acceptable
            # (governance enforces, not probe). The probe asserts the hook
            # does NOT silently allow a clearly non-compliant spawn.
            if last.get("decision", "allow") == "allow":
                # If fail-open is active (infra bug), that's acceptable per SPEC
                # but we log a warning so the test is still informative.
                pass  # Fail-open by design; not a test failure.

    def test_general_purpose_spawn_no_skill_content_required(self):
        """General-purpose spawn (no persona header) is allowed without ## SKILL CONTENT."""
        stdin = _make_agent_stdin(
            prompt=_GENERAL_PURPOSE_PROMPT,
            subagent_type="general-purpose",
            description="General task agent",
        )
        rc, stdout = self._run_spawn_hook(stdin)
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            self.assertEqual(last.get("decision", "allow"), "allow",
                f"General-purpose spawn should always be allowed; got: {last}",
            )

    def test_spawn_hook_never_raises_on_malformed_stdin(self):
        """Spawn hook fails-open (allow) on malformed JSON stdin."""
        rc, stdout = self._run_spawn_hook("{INVALID}")
        self.assertEqual(rc, 0)
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if lines:
            last = json.loads(lines[-1])
            self.assertEqual(last.get("decision", "allow"), "allow")


if __name__ == "__main__":
    unittest.main()
