"""PLAN-122 WS2-T3 (ADR-136-AMEND-2 §4.6 FIX-1) — per-child spawn gate.

The "most important invariant" of write-path fan-out: EVERY prospective
fan-out child MUST pass spawn-governance compliance BEFORE any dispatch
happens. A coordinator that fans out to N children must be able to
pre-screen each child payload and refuse the whole batch if any single
child would be blocked — WITHOUT actually dispatching, and WITHOUT
touching the live audit chain.

## Side-effect-free by construction (recon open-q #7)

This gate is a *pure* structural compliance check. It performs NO I/O,
emits NO audit events, and NEVER imports the live hook entrypoint
``check_agent_spawn.decide`` (which fires PostToolUse advisory emits via
``_lib.audit_emit`` — those would pollute the live audit-log chain).

The hook's only public entrypoint, ``decide()``, is NOT side-effect-free
(it calls ``_emit_model_routing_advisory`` /
``_consult_model_routing_mode`` / ``_emit_*_advisory`` etc., all of which
write to the audit log). The pure structural predicates inside the hook
(``_has_skill_content`` / ``_PERSONA_HEADER_RE`` /
``_SKILL_REFERENCE_HEADER_RE``) are private and importing them drags the
whole ``_lib`` import graph. So — per the WS2-T3 instruction — we
REPLICATE ONLY the structural compliance check here, faithful to the
hook's contract (PROTOCOL.md §Spawn Protocol Step 3 + CLAUDE.md §5):

    every named spawn MUST contain
        ## AGENT PROFILE     (persona header — PERSONA:/## PERSONA accepted)
      + ## SKILL CONTENT      (inline, >=256 non-ws bytes)
        OR ## SKILL REFERENCE (the additive sentinel; presence-only here)
      + ## FILE ASSIGNMENT    (anti-collision contract)

The marker forms + the 256-non-ws-byte skill-content floor are mirrored
verbatim from ``check_agent_spawn.py`` so this gate stays in lock-step
with the live hook. This is the MECHANISM only — no behavioural claim
beyond structural compliance is made.

stdlib-only · Python >=3.9 · fail-conservative (a malformed payload is
BLOCKED, never raises on the happy path).
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Structural markers — MIRRORED from check_agent_spawn.py.
# Kept byte-identical to the live hook so the gate's verdict matches the
# hook's verdict on the same payload.
# ---------------------------------------------------------------------------

# Persona header — must appear at the START of a line. Mirrors
# check_agent_spawn._PERSONA_HEADER_RE. ``## AGENT PROFILE`` is the
# canonical form (CLAUDE.md §Spawn protocol); ``PERSONA:`` / ``## PERSONA``
# are the legacy-accepted equivalents (PROTOCOL.md Format A/B).
_PERSONA_HEADER_RE = re.compile(
    r"^(?:PERSONA:|## AGENT PROFILE|## PERSONA)",
    flags=re.MULTILINE,
)

# ``## SKILL CONTENT`` marker on its OWN line (trailing ws tolerated).
# Mirrors check_agent_spawn._SKILL_CONTENT_MARKER_RE.
_SKILL_CONTENT_MARKER_RE = re.compile(
    r"^## SKILL CONTENT[ \t]*$",
    flags=re.MULTILINE,
)

# ``## SKILL REFERENCE`` header on its own line (any inner whitespace).
# Mirrors check_agent_spawn._SKILL_REFERENCE_HEADER_RE.
_SKILL_REFERENCE_HEADER_RE = re.compile(
    r"^##[ \t]+SKILL[ \t]+REFERENCE[ \t]*$",
    flags=re.MULTILINE,
)

# ``## FILE ASSIGNMENT`` header on its own line (any inner whitespace).
_FILE_ASSIGNMENT_HEADER_RE = re.compile(
    r"^##[ \t]+FILE[ \t]+ASSIGNMENT[ \t]*$",
    flags=re.MULTILINE,
)

# Next ``##``-level heading — bounds the SKILL CONTENT body extraction.
# Mirrors check_agent_spawn._NEXT_H2_RE.
_NEXT_H2_RE = re.compile(r"^##[ \t]", flags=re.MULTILINE)

# Minimum non-whitespace bytes between ``## SKILL CONTENT`` and the next
# ``##`` heading / EOF for the marker to count as a real section. Mirrors
# check_agent_spawn._SKILL_CONTENT_MIN_BYTES (rejects empty-body /
# "see file X" stub shells; P1-SEC-B floor).
_SKILL_CONTENT_MIN_BYTES = 256


# ---------------------------------------------------------------------------
# Block reason codes — closed enum, no caller payload echoed back.
# ---------------------------------------------------------------------------

REASON_OK = "ok"
REASON_NOT_A_DICT = "payload_not_a_dict"
REASON_MISSING_AGENT_PROFILE = "missing_agent_profile"
REASON_MISSING_SKILL = "missing_skill_section"
REASON_SKILL_CONTENT_TOO_SHORT = "skill_content_below_floor"
REASON_MISSING_FILE_ASSIGNMENT = "missing_file_assignment"
REASON_EMPTY_GOAL = "empty_goal"


def _has_agent_profile(prompt: str) -> bool:
    """True iff ``prompt`` carries a persona header on its own line.

    Accepts the canonical ``## AGENT PROFILE`` plus the legacy-equivalent
    ``PERSONA:`` / ``## PERSONA`` forms (parity with the live hook).
    """
    if not prompt:
        return False
    return bool(_PERSONA_HEADER_RE.search(prompt))


def _has_inline_skill_content(prompt: str) -> bool:
    """True iff ``prompt`` has a ``## SKILL CONTENT`` section with a real
    body (>=``_SKILL_CONTENT_MIN_BYTES`` non-ws bytes before the next ``##``).

    NOTE: this gate is the *structural* floor only — it intentionally does
    NOT re-implement the hook's fenced-code / HTML-comment stripping
    (``_strip_fenced_and_comments``). A coordinator builds its own child
    payloads (they are not attacker-authored prose), so the bypass-
    hardening that the live hook needs against adversarial user prompts is
    out of scope here. The live PreToolUse hook remains the authoritative
    bypass-resistant gate at actual dispatch time; this is a pre-flight
    structural screen.
    """
    if not prompt:
        return False
    match = _SKILL_CONTENT_MARKER_RE.search(prompt)
    if match is None:
        return False
    body_start = match.end()
    next_heading = _NEXT_H2_RE.search(prompt, body_start)
    body_end = next_heading.start() if next_heading else len(prompt)
    body = prompt[body_start:body_end]
    non_ws_bytes = sum(1 for c in body if not c.isspace())
    return non_ws_bytes >= _SKILL_CONTENT_MIN_BYTES


def _has_skill_reference(prompt: str) -> bool:
    """True iff ``prompt`` has a ``## SKILL REFERENCE`` header.

    Presence-only — the gate does NOT perform the hook's full 11-sub-check
    sha256 / path / redaction validation (that requires filesystem reads
    and is therefore not side-effect-free in the I/O sense). For a
    pre-flight structural screen the header presence is the right altitude:
    the authoritative reference validation still runs in the live hook at
    dispatch time.
    """
    if not prompt:
        return False
    return bool(_SKILL_REFERENCE_HEADER_RE.search(prompt))


def _has_file_assignment(prompt: str) -> bool:
    """True iff ``prompt`` has a ``## FILE ASSIGNMENT`` header on its own line."""
    if not prompt:
        return False
    return bool(_FILE_ASSIGNMENT_HEADER_RE.search(prompt))


def build_child_spawn_payload(
    goal: str,
    skill_ref_or_content: str,
    file_assignment: str,
    agent_profile: str,
) -> Dict[str, str]:
    """Assemble a prospective fan-out child's spawn payload.

    The payload is a plain dict (no dispatch, no I/O). The coordinator
    passes the result straight to ``verify_child_spawn_allowed`` to
    pre-screen the child BEFORE any dispatch (ADR-136-AMEND-2 §4.6 FIX-1).

    Args:
        goal: The child's task / goal text (becomes the ``## TASK`` body).
            Must be non-empty for the child to be allowed.
        skill_ref_or_content: Either an inline ``## SKILL CONTENT`` block
            body (>=256 non-ws bytes) OR a ``## SKILL REFERENCE`` block.
            The caller supplies the section heading inline; this function
            does not invent it — it embeds the string verbatim so the
            coordinator stays in control of which format (A or B) it uses.
        file_assignment: The ``## FILE ASSIGNMENT`` body (the CAN/CANNOT
            edit lists). The heading is added by this builder.
        agent_profile: The persona header + body (``## AGENT PROFILE`` /
            ``PERSONA:`` ...). The heading is supplied by the caller so
            both Format-A and Format-B personas pass through verbatim.

    Returns:
        A dict with keys:
            ``goal``    — the raw goal string (echoed for the coordinator)
            ``prompt``  — the assembled spawn prompt (the thing the gate +
                          the live hook both inspect)

    The assembled ``prompt`` is deliberately structured to mirror the
    PROTOCOL.md §Step-3 layout so the same string passes both this gate
    and the live ``check_agent_spawn.decide`` at dispatch.
    """
    # Normalize to strings (a None slips through as "" — the verify step
    # will then BLOCK on the missing section, never raise).
    goal_s = goal if isinstance(goal, str) else ""
    skill_s = skill_ref_or_content if isinstance(skill_ref_or_content, str) else ""
    file_s = file_assignment if isinstance(file_assignment, str) else ""
    profile_s = agent_profile if isinstance(agent_profile, str) else ""

    # The skill block is embedded verbatim — the caller owns whether it is
    # a ``## SKILL CONTENT`` or ``## SKILL REFERENCE`` block. The persona
    # block is likewise verbatim (caller owns ## AGENT PROFILE vs PERSONA:).
    prompt_parts = [
        profile_s.rstrip(),
        "",
        skill_s.rstrip(),
        "",
        "## FILE ASSIGNMENT",
        file_s.rstrip(),
        "",
        "## TASK",
        goal_s.rstrip(),
    ]
    prompt = "\n".join(prompt_parts)

    return {
        "goal": goal_s,
        "prompt": prompt,
    }


def verify_child_spawn_allowed(
    payload: Dict[str, str],
) -> Tuple[bool, str]:
    """Pure structural spawn-governance verdict for one prospective child.

    SIDE-EFFECT-FREE: no audit emit, no file I/O, no import of the live
    emitting hook entrypoint. The coordinator calls this for EVERY child
    in a prospective fan-out batch and refuses to dispatch the batch if
    any single child returns ``allowed=False`` (ADR-136-AMEND-2 §4.6
    FIX-1: spawn-governance BEFORE any dispatch).

    Compliance contract (mirrors ``check_agent_spawn`` structural check):
        ## AGENT PROFILE  (persona header)
      + (## SKILL CONTENT inline >=256 non-ws bytes  OR  ## SKILL REFERENCE)
      + ## FILE ASSIGNMENT
      + non-empty goal

    Args:
        payload: The dict produced by ``build_child_spawn_payload`` (or an
            equivalently-shaped dict with ``goal`` + ``prompt`` keys).

    Returns:
        ``(allowed, reason)`` — ``allowed`` is True only when every
        required section is present and the goal is non-empty. ``reason``
        is a closed-enum reason code (``REASON_*``); on allow it is
        ``REASON_OK``. The reason NEVER echoes caller payload content
        (closed-enum discipline — no value laundering into a return string).

    Never raises on the happy path: a non-dict / malformed payload is
    BLOCKED (fail-conservative), not an exception.
    """
    if not isinstance(payload, dict):
        return False, REASON_NOT_A_DICT

    prompt = payload.get("prompt")
    if not isinstance(prompt, str):
        prompt = ""
    goal = payload.get("goal")
    if not isinstance(goal, str):
        goal = ""

    # Required: persona header (## AGENT PROFILE / PERSONA: / ## PERSONA).
    if not _has_agent_profile(prompt):
        return False, REASON_MISSING_AGENT_PROFILE

    # Required: a skill section — inline content OR reference sentinel.
    has_ref = _has_skill_reference(prompt)
    has_inline_marker = _SKILL_CONTENT_MARKER_RE.search(prompt) is not None
    if not has_ref and not has_inline_marker:
        return False, REASON_MISSING_SKILL
    # If it's the inline form, the body must clear the 256-non-ws-byte floor.
    if not has_ref and not _has_inline_skill_content(prompt):
        return False, REASON_SKILL_CONTENT_TOO_SHORT

    # Required: file-assignment (anti-collision) section.
    if not _has_file_assignment(prompt):
        return False, REASON_MISSING_FILE_ASSIGNMENT

    # Required: a non-empty goal — a child with no task is not dispatchable.
    if not goal.strip():
        return False, REASON_EMPTY_GOAL

    return True, REASON_OK
