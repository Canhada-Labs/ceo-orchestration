"""PLAN-122 WS2-T3 — tests for the per-child spawn-governance gate.

Covers:
  - a fully-compliant payload is ALLOWED (Format A inline + Format B ref)
  - each missing required section is BLOCKED with a specific reason code
  - the inline-skill 256-non-ws-byte floor is enforced
  - malformed / non-dict / empty-goal payloads fail conservative (BLOCK)
  - **the live audit chain is UNTOUCHED**: pointing CEO_AUDIT_LOG_DIR at a
    tmp dir and exercising the whole gate leaves that dir empty (recon
    open-q #7 — the gate must be side-effect-free).

stdlib + pytest only (matches the rest of swarm/tests/).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure .claude/scripts is on sys.path so ``swarm._spawn_gate`` imports
# whether pytest collects from the repo root or from within scripts/.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from swarm import _spawn_gate as gate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A skill-content body comfortably over the 256-non-ws-byte floor.
_LONG_SKILL_BODY = "## SKILL CONTENT\n" + ("rule line. " * 60)

# A standard agent profile / persona block.
_PROFILE = "## AGENT PROFILE\nPersona: backend-engineer\nFOCUS: correctness"

# A standard file-assignment body.
_FILE_BODY = "- CAN edit: src/foo.py\n- CANNOT edit: src/bar.py"


def _compliant_payload_inline():
    return gate.build_child_spawn_payload(
        goal="Refactor the auth module for clarity.",
        skill_ref_or_content=_LONG_SKILL_BODY,
        file_assignment=_FILE_BODY,
        agent_profile=_PROFILE,
    )


def _compliant_payload_reference():
    skill_ref = (
        "## SKILL REFERENCE\n\n"
        "@.claude/skills/core/example/SKILL.md "
        "sha256=" + ("a" * 64) + "\n\n"
        "(summary of the skill's key rules for the sub-agent)"
    )
    return gate.build_child_spawn_payload(
        goal="Audit the payment flow.",
        skill_ref_or_content=skill_ref,
        file_assignment=_FILE_BODY,
        agent_profile="PERSONA: security-engineer — auditor",
    )


# ---------------------------------------------------------------------------
# Allow-path
# ---------------------------------------------------------------------------

def test_compliant_inline_payload_allowed():
    allowed, reason = gate.verify_child_spawn_allowed(_compliant_payload_inline())
    assert allowed is True
    assert reason == gate.REASON_OK


def test_compliant_reference_payload_allowed():
    allowed, reason = gate.verify_child_spawn_allowed(
        _compliant_payload_reference()
    )
    assert allowed is True
    assert reason == gate.REASON_OK


def test_build_child_spawn_payload_shape():
    payload = _compliant_payload_inline()
    assert set(payload.keys()) == {"goal", "prompt"}
    assert "## AGENT PROFILE" in payload["prompt"]
    assert "## SKILL CONTENT" in payload["prompt"]
    assert "## FILE ASSIGNMENT" in payload["prompt"]
    assert "## TASK" in payload["prompt"]


# ---------------------------------------------------------------------------
# Block-path — each missing section gets a specific reason
# ---------------------------------------------------------------------------

def test_missing_agent_profile_blocked():
    # Skill block carries its own heading; profile omitted entirely.
    payload = {
        "goal": "do the thing",
        "prompt": _LONG_SKILL_BODY + "\n\n## FILE ASSIGNMENT\n" + _FILE_BODY,
    }
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_MISSING_AGENT_PROFILE


def test_missing_skill_section_blocked():
    payload = {
        "goal": "do the thing",
        "prompt": _PROFILE + "\n\n## FILE ASSIGNMENT\n" + _FILE_BODY,
    }
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_MISSING_SKILL


def test_skill_content_below_floor_blocked():
    # Has the ## SKILL CONTENT marker but a body under the 256-byte floor.
    short_skill = "## SKILL CONTENT\ntoo short"
    payload = {
        "goal": "do the thing",
        "prompt": (
            _PROFILE + "\n\n" + short_skill
            + "\n\n## FILE ASSIGNMENT\n" + _FILE_BODY
        ),
    }
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_SKILL_CONTENT_TOO_SHORT


def test_skill_reference_satisfies_skill_requirement():
    # Reference present (no inline content) → skill requirement met; the
    # only thing missing is FILE ASSIGNMENT, so that's the reason we get.
    payload = {
        "goal": "do the thing",
        "prompt": (
            _PROFILE + "\n\n## SKILL REFERENCE\n\n"
            "@.claude/skills/core/x/SKILL.md sha256=" + ("b" * 64)
        ),
    }
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_MISSING_FILE_ASSIGNMENT


def test_missing_file_assignment_blocked():
    payload = {
        "goal": "do the thing",
        "prompt": _PROFILE + "\n\n" + _LONG_SKILL_BODY,
    }
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_MISSING_FILE_ASSIGNMENT


def test_empty_goal_blocked():
    payload = gate.build_child_spawn_payload(
        goal="   ",  # whitespace-only goal
        skill_ref_or_content=_LONG_SKILL_BODY,
        file_assignment=_FILE_BODY,
        agent_profile=_PROFILE,
    )
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert reason == gate.REASON_EMPTY_GOAL


# ---------------------------------------------------------------------------
# Fail-conservative — malformed payloads BLOCK, never raise
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad",
    [None, "a string", 42, ["list"], 3.14],
)
def test_non_dict_payload_blocked(bad):
    allowed, reason = gate.verify_child_spawn_allowed(bad)
    assert allowed is False
    assert reason == gate.REASON_NOT_A_DICT


def test_empty_dict_blocked_not_raised():
    allowed, reason = gate.verify_child_spawn_allowed({})
    assert allowed is False
    # Empty dict → no prompt → first failing section is the persona header.
    assert reason == gate.REASON_MISSING_AGENT_PROFILE


def test_build_with_none_args_does_not_raise():
    # None args normalize to "" — the verify step BLOCKs, never raises.
    payload = gate.build_child_spawn_payload(
        goal=None,  # type: ignore[arg-type]
        skill_ref_or_content=None,  # type: ignore[arg-type]
        file_assignment=None,  # type: ignore[arg-type]
        agent_profile=None,  # type: ignore[arg-type]
    )
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False


def test_reason_never_echoes_payload_content():
    # The block reason must be a closed-enum code, never the caller's text.
    secret = "SUPER-SECRET-TASK-TEXT-12345"
    payload = {"goal": secret, "prompt": secret}
    allowed, reason = gate.verify_child_spawn_allowed(payload)
    assert allowed is False
    assert secret not in reason
    assert reason in {
        gate.REASON_MISSING_AGENT_PROFILE,
        gate.REASON_MISSING_SKILL,
        gate.REASON_SKILL_CONTENT_TOO_SHORT,
        gate.REASON_MISSING_FILE_ASSIGNMENT,
        gate.REASON_EMPTY_GOAL,
    }


# ---------------------------------------------------------------------------
# THE invariant (recon open-q #7): the gate is side-effect-free.
# Point CEO_AUDIT_LOG_DIR at a tmp dir, exercise the WHOLE gate (allow +
# every block path), and assert the dir is still EMPTY — no audit-log
# write occurred, the live chain is untouched.
# ---------------------------------------------------------------------------

def test_gate_does_not_write_audit_log(tmp_path, monkeypatch):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    # Redirect every audit-log path env the framework might honor.
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(audit_dir))
    monkeypatch.setenv("CEO_AUDIT_LOG_PATH", str(audit_dir / "audit-log.jsonl"))

    # Exercise the allow path + a representative slice of block paths.
    gate.verify_child_spawn_allowed(_compliant_payload_inline())
    gate.verify_child_spawn_allowed(_compliant_payload_reference())
    gate.verify_child_spawn_allowed({})
    gate.verify_child_spawn_allowed(None)
    gate.verify_child_spawn_allowed(
        {"goal": "g", "prompt": _PROFILE + "\n## FILE ASSIGNMENT\nx"}
    )
    gate.build_child_spawn_payload("g", _LONG_SKILL_BODY, _FILE_BODY, _PROFILE)

    # The redirected audit dir must be completely empty — the gate wrote
    # nothing, so the live audit chain is provably untouched.
    leftovers = list(audit_dir.rglob("*"))
    assert leftovers == [], (
        "spawn gate must be side-effect-free, but it wrote to the "
        f"redirected audit dir: {leftovers!r}"
    )


def test_full_batch_pre_screen_refuses_on_single_bad_child():
    # ADR-136-AMEND-2 §4.6 FIX-1: a coordinator pre-screens EVERY child
    # and refuses the whole batch if any single child is blocked.
    good = _compliant_payload_inline()
    bad = {"goal": "x", "prompt": "no sections here"}
    batch = [good, good, bad, good]
    verdicts = [gate.verify_child_spawn_allowed(c) for c in batch]
    batch_allowed = all(allowed for allowed, _ in verdicts)
    assert batch_allowed is False
    # And the failing child carries a specific, actionable reason.
    assert verdicts[2][1] == gate.REASON_MISSING_AGENT_PROFILE
