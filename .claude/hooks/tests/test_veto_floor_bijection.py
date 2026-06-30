"""Bidirectional invariant test: VETO_FLOOR_ROLES ⇔ deployed agents with veto_floor:true.

PLAN-074 Wave 1c — atomic-add invariant enforcement.

Closes both half-states of the S90 P0-01 lesson:

(a) **Forward**: every entry in ``VETO_FLOOR_ROLES`` MUST have a
    corresponding ``.claude/agents/<role>.md`` file. Without this
    half, ``check_agent_spawn.py`` fail-CLOSES with ``file_missing``
    on every dispatch that mentions the role — framework-wide
    breakage. The S90 Wave 0 ADJ-B3 incident manifested exactly this
    way and was rolled back.

(b) **Reverse**: every ``.claude/agents/<role>.md`` file with
    ``veto_floor: true`` in frontmatter MUST be in ``VETO_FLOOR_ROLES``.
    Without this half, an Owner-merged agent file silently slips past
    the frozenset, declares VETO authority in its frontmatter, but
    the runtime model-floor enforcement in ``validate_veto_floor_models``
    skips the check — silent under-enforcement.

(c) **Model floor**: every agent declaring ``veto_floor: true`` MUST
    use the canonical Opus model (``claude-opus-4-8`` per ADR-052).
    A non-Opus agent with ``veto_floor: true`` would silently downgrade
    VETO authority — must fail loudly so the contradiction is visible.

The set-equality form (``VETO_FLOOR_ROLES == deployed``) is the
strong invariant the Wave 1c matrix demands. The two directional
asserts above precede it to give precise error messages on either
half failing in isolation.

Wave 1c-staged note: this test ships in the Wave 1c GPG ceremony
alongside the 4 NEW agent files + 2 frontmatter additions (code-
reviewer + security-engineer) + frozenset expansion. Pre-Wave-1c
the test would FAIL because deployed VETO agents lack the
``veto_floor: true`` frontmatter — that failure shape IS the
contract: the test exists to enforce the post-Wave-1c invariant
and detect any silent drift afterward.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Set

# ``.claude`` is not a Python package — it has no ``__init__.py`` and
# the leading dot would be parsed as a relative import. Tests must
# extend ``sys.path`` to include ``.claude/hooks/`` and import
# ``_lib.agent_frontmatter`` without the ``.claude.hooks.`` prefix.
#
# This file lives at ``.claude/hooks/tests/test_veto_floor_bijection.py``
# so ``parents[3]`` is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib.agent_frontmatter import (  # noqa: E402  (sys.path manipulation precedes import by design)
    VETO_FLOOR_ROLES,
    VETO_FLOOR_ALLOWED,
    parse_agent_file,
)


def _is_truthy(value: object) -> bool:
    """Coerce frontmatter value to bool.

    ``parse_agent_file`` returns ``Dict[str, str]``, so YAML
    ``veto_floor: true`` arrives as the string ``"true"`` — direct
    ``is True`` comparison would always be False. Wave 1c may add a
    typed accessor to ``_lib/agent_frontmatter`` later; until then,
    normalize here.
    """
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("true", "yes", "1")


def _agents_with_veto_frontmatter() -> Set[str]:
    """Derive the deployed VETO-marked agent set from frontmatter.

    Collects every agent that declares ``veto_floor: true`` REGARDLESS
    of model. Caller separately asserts these agents use the expected
    Opus model — that way a non-Opus agent incorrectly declaring
    ``veto_floor: true`` is detected as BOTH an orphan-from-frozenset
    (if absent from ``VETO_FLOOR_ROLES``) AND a model-floor violation,
    instead of being silently ignored.
    """
    agents_dir = REPO_ROOT / ".claude" / "agents"
    deployed: Set[str] = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        # Skip ``_dispatch.md`` and any non-agent helpers (no ``model:`` field
        # OR malformed frontmatter)
        try:
            fm = parse_agent_file(agent_file)
        except Exception:
            continue
        if fm.get("__symlink_rejected__"):
            continue
        if _is_truthy(fm.get("veto_floor")):
            deployed.add(agent_file.stem)
    return deployed


def _veto_agents_with_wrong_model() -> Set[str]:
    """Find agents declaring ``veto_floor: true`` but NOT using the canonical Opus model."""
    agents_dir = REPO_ROOT / ".claude" / "agents"
    wrong: Set[str] = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            fm = parse_agent_file(agent_file)
        except Exception:
            continue
        if fm.get("__symlink_rejected__"):
            continue
        if _is_truthy(fm.get("veto_floor")) and fm.get("model") not in VETO_FLOOR_ALLOWED:
            wrong.add(agent_file.stem)
    return wrong


def test_veto_floor_roles_bijection_with_deployed_agents():
    """Bidirectional invariant: VETO_FLOOR_ROLES == deployed-VETO-frontmatter agents.

    Closes both half-states:
    (a) frozenset role without agent file → fail-CLOSE on dispatch (S90 P0-01 incident),
    (b) deployed VETO-marked agent file NOT in frozenset → silent under-enforcement.
    """
    agents_dir = REPO_ROOT / ".claude" / "agents"

    # Forward: every frozenset role has its agent file
    missing_files = {
        role for role in VETO_FLOOR_ROLES
        if not (agents_dir / f"{role}.md").exists()
    }
    assert not missing_files, (
        f"VETO-floor roles missing agent files: {missing_files} "
        "— atomic-add invariant violated; the frozenset entry was added "
        "without its corresponding `.claude/agents/<role>.md` file. "
        "Re-run the Wave 1c-style sentinel ceremony to land both halves."
    )

    # Reverse: every VETO-marked deployed agent is in the frozenset
    deployed = _agents_with_veto_frontmatter()
    orphans = deployed - VETO_FLOOR_ROLES
    assert not orphans, (
        f"Agents declare veto_floor:true but absent from VETO_FLOOR_ROLES: {orphans} "
        "— atomic-add invariant violated; the agent file was added "
        "without its corresponding frozenset entry. "
        "Re-run the Wave 1c-style sentinel ceremony to land both halves."
    )

    # Equality (the strong invariant the Wave 1c matrix demands)
    assert VETO_FLOOR_ROLES == deployed, (
        f"Set-equality invariant broken: frozenset={set(VETO_FLOOR_ROLES)} "
        f"deployed={deployed}"
    )


def test_veto_floor_agents_use_floor_allowlist_model():
    """Model floor: every veto_floor:true agent uses an allowlisted floor model.

    An agent declaring ``veto_floor: true`` with ``model=claude-sonnet-4-6``
    (etc.) would silently downgrade VETO authority — must fail loudly per
    ADR-052 + ADR-149 ``VETO_FLOOR_ALLOWED`` (Owner-signed allowlist; the
    PLAN-134 W0 generation unlock replaced the exact-equality opus pin —
    REPORT-S225 E1-F1).
    """
    wrong_model = _veto_agents_with_wrong_model()
    assert not wrong_model, (
        f"Agents declare veto_floor:true but use a non-allowlisted model: "
        f"{wrong_model} — VETO_FLOOR_ALLOWED is {sorted(VETO_FLOOR_ALLOWED)} "
        "per ADR-052/ADR-149. Either change `model:` to an allowlisted floor "
        "model OR remove `veto_floor: true`."
    )
