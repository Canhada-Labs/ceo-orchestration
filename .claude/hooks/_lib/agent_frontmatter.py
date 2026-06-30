"""VETO-floor model validation for `.claude/agents/*.md` frontmatter.

PLAN-045 Wave 1 P0-03. Closes PLAN-044 F-01-03: the
``CEO_MULTIMODEL_ENABLE`` kill-switch was documented in ADR-052 but
never wired at runtime — the framework's VETO floor (security-engineer
and code-reviewer MUST run on Opus) was enforced only by a frontmatter
field any sentinel-unlocker could edit.

This module ships a two-tier defense:

1. **Parse agent frontmatter.** ``parse_agent_file`` returns the
   ``{name, model, ...}`` map for any ``.claude/agents/*.md`` using the
   shared ``_lib.frontmatter`` primitive (ADR-002 stdlib-only).

2. **Validate VETO floor.** ``validate_veto_floor_models`` enforces
   the hardcoded invariant. Post-PLAN-074 Wave 1c (S93) the floor
   covers 5 roles:

       role ∈ {code-reviewer, security-engineer,
               incident-commander, identity-trust-architect,
               threat-detection-engineer}
           ⇒ frontmatter["model"] ∈ VETO_FLOOR_ALLOWED

   ``VETO_FLOOR_ALLOWED`` is the Owner-signed allowlist of model IDs
   that satisfy the floor (ADR-149). It is ADDITIVE across generation
   bumps: the previous flagship stays valid, so a bump is a one-site
   data change instead of a 4-site synchronized equality edit
   (PLAN-134 W0, finding E1-F1).

   The 4th Wave 1c security-domain candidate ``llm-finops-architect``
   is **explicitly excluded** per the Wave 1c VETO-floor matrix +
   ADR-052 amendment: cost governance is operational doctrine +
   mechanical enforcement (ADR-064), not a sub-domain trust boundary
   that justifies a dedicated VETO authority. The agent file ships
   with ``veto_floor: false`` to make the exclusion explicit +
   bidirectionally verifiable via ``test_veto_floor_bijection.py``.

   Any deviation (missing frontmatter, missing ``model:``, wrong
   model, drift between ``VETO_FLOOR_ROLES`` and deployed agents
   declaring ``veto_floor: true``) surfaces a violation with the
   exact file:line-number equivalent field for forensics. Caller
   blocks the spawn + emits
   ``veto_triggered(reason_code=veto_floor_demoted)``.

## Integration point

The arbitration-kernel hook (``check_arbitration_kernel.py``) adds
``.claude/agents/*.md`` to its ``_KERNEL_PATHS`` so that frontmatter
mutations require ``CEO_KERNEL_OVERRIDE + ACK``. ``check_agent_spawn.py``
invokes this validator at every spawn; on violation the spawn is
blocked. Both integrations are **kernel-scope edits** — deployment of
this library is Phase 1a, hook wiring is Phase 1b (Owner physical-shell
kernel batch).

## Hardcoded invariants (defense in depth)

``_VETO_FLOOR_ROLES``, ``_VETO_FLOOR_MODEL`` and
``_VETO_FLOOR_ALLOWED`` are module-level frozensets/strings to prevent
mutation at runtime. PLAN-043 ADR-064
precedent: policy-relevant constants are frozen at source so a kernel-
override on this file is forensically visible in diffs.

## Stdlib-only (ADR-002)

Uses ``pathlib`` and ``_lib.frontmatter``. No YAML library.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.frontmatter import parse_frontmatter  # noqa: E402

__all__ = [
    "VETO_FLOOR_ROLES",
    "VETO_FLOOR_MODEL",
    "VETO_FLOOR_ALLOWED",
    "AgentFrontmatterError",
    "parse_agent_file",
    "resolve_agent_file",
    "check_veto_floor_for_role",
    "validate_veto_floor_models",
]


# Hardcoded VETO floor (defense-in-depth; matches PLAN-043 pattern).
# Mutating these requires a kernel-override edit to this file — which
# leaves a diff in git history that any reviewer can detect. Without
# this frozen baseline, the floor would depend entirely on the
# ``.claude/agents/*.md`` files being correct, which F-01-03
# demonstrated is an insufficient invariant.
#
# History:
# - Wave 0 ADJ-B3 BLOCKER 6 (S90): pre-registered 4 VETO-adjacent slugs
#   without agent files. ROLLED BACK per S90 fork-b Codex MCP gate
#   P0-01: keeping extra slugs here without their agent files caused
#   check_agent_spawn.py to fail-close on ``file_missing`` for every
#   dispatch that mentioned those archetype names in description/prompt
#   — blocking legitimate Wave 1c authoring work.
# - Wave 1c (S93): the 3 security-domain VETO-adjacent slugs (incident-
#   commander, identity-trust-architect, threat-detection-engineer) are
#   added HERE atomically with their corresponding ``.claude/agents/
#   <slug>.md`` files in a single GPG sentinel commit, satisfying both
#   halves of the S90 P0-01 invariant. The 4th slug from the original
#   Wave 0 set (``llm-finops-architect``) is EXCLUDED from this
#   frozenset per the Wave 1c VETO-floor matrix and ADR-052 amendment:
#   cost governance is operational doctrine + mechanical enforcement
#   (ADR-064), NOT a sub-domain trust boundary that justifies a
#   dedicated VETO authority. The agent file ships with
#   ``veto_floor: false`` to make the exclusion explicit + bidirectionally
#   verifiable via ``test_veto_floor_bijection.py``.
VETO_FLOOR_ROLES: FrozenSet[str] = frozenset({
    "code-reviewer",
    "security-engineer",
    "incident-commander",          # PLAN-074 Wave 1c — incident-management VETO-floor (sev-N escalation)
    "identity-trust-architect",    # PLAN-074 Wave 1c — identity/trust VETO-floor (ADR-052 amendment)
    "threat-detection-engineer",   # PLAN-074 Wave 1c — SIEM/ATT&CK VETO-floor (security domain)
})

VETO_FLOOR_MODEL: str = "claude-opus-4-8"

# ADR-149 (PLAN-134 W0, E1-F1): Owner-signed allowlist of model IDs that
# satisfy the VETO floor. Replaces the exact-equality pin so a
# generation bump becomes a one-site data change. ADDITIVE by doctrine:
# the previous flagship stays valid during migration (intentional N-1
# tolerance window). ``VETO_FLOOR_MODEL`` is retained unchanged as the
# legacy preferred-pin constant for existing importers + tests; the
# enforcement comparison below uses MEMBERSHIP in this set.
VETO_FLOOR_ALLOWED: FrozenSet[str] = frozenset({
    "claude-opus-4-8",
    "claude-fable-5",
})


class AgentFrontmatterError(RuntimeError):
    """Raised on unrecoverable parse errors (bad path, unreadable file).

    Recoverable conditions (missing ``model:`` field, wrong model,
    missing file for a given role) return structured violations from
    ``validate_veto_floor_models`` rather than raising.
    """


def resolve_agent_file(agent_name: str, agents_dir: Path) -> Path:
    """Return ``<agents_dir>/<agent_name>.md``.

    Does NOT verify the file exists — callers decide whether a missing
    file is a violation (e.g. spawn-time check should treat missing
    VETO-role file as fail-CLOSED).
    """
    if not agent_name or "/" in agent_name or ".." in agent_name:
        raise AgentFrontmatterError(
            f"invalid agent name: {agent_name!r}"
        )
    return agents_dir / f"{agent_name}.md"


def parse_agent_file(
    path: Path,
) -> Dict[str, str]:
    """Parse ``.claude/agents/<name>.md`` and return its frontmatter.

    Reads the file, delegates to ``_lib.frontmatter.parse_frontmatter``,
    and returns the ``Dict[str, str]`` key/value map. Returns an empty
    dict if the file has no frontmatter or is unreadable.

    Symlink rejection: if the target file (or its parent directory) is
    a symlink, parsing refuses and returns an empty dict with
    ``__symlink_rejected__: 1`` marker for the caller. The check mirrors
    the pattern in ``_lib.gpg_verify.load_allowlist`` and the sentinel
    symlink-reject requirement (PLAN-044 F-01-04).
    """
    try:
        if path.is_symlink():
            return {"__symlink_rejected__": "leaf"}
        if path.parent.is_symlink():
            return {"__symlink_rejected__": "parent"}
        if not path.is_file():
            return {}
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    metadata, _body = parse_frontmatter(raw)
    return metadata


def check_veto_floor_for_role(
    role: str,
    agents_dir: Path,
    *,
    veto_roles: Optional[Iterable[str]] = None,
    expected_model: Optional[str] = None,
) -> Tuple[bool, str]:
    """Validate one VETO role's agent frontmatter.

    Returns ``(ok, reason)``:

    - ``(True, "")`` — role is in the VETO floor AND frontmatter
      ``model:`` is in the allowed set (``VETO_FLOOR_ALLOWED`` by
      default; exactly ``{expected_model}`` when the kwarg is passed).
    - ``(True, "not_veto_role")`` — role is NOT in the VETO floor; no
      constraint applies. Caller treats as pass-through.
    - ``(False, "<reason>")`` — violation. Reasons:

      - ``file_missing`` — ``<agents_dir>/<role>.md`` not present
      - ``file_symlink_rejected`` / ``parent_symlink_rejected``
      - ``frontmatter_missing`` — file has no ``---`` block or is empty
      - ``model_field_missing`` — frontmatter parses but ``model:`` absent
      - ``model_mismatch:<actual>`` — frontmatter has ``model: X`` but X
        ∉ the allowed set (``X`` is echoed unredacted; callers MUST
        audit this string for forensics; reason-string shape is
        UNCHANGED from the pre-ADR-149 equality implementation)

    The ``veto_roles`` / ``expected_model`` kwargs exist for testing
    only — production code path uses the frozen defaults above. Passing
    override values does NOT disable the floor; it replaces it with the
    provided set for scoped validation (``expected_model`` narrows the
    allowlist to exactly that single ID).
    """
    roles = frozenset(veto_roles) if veto_roles is not None else VETO_FLOOR_ROLES
    allowed = (
        frozenset({expected_model})
        if expected_model is not None
        else VETO_FLOOR_ALLOWED
    )
    if role not in roles:
        return True, "not_veto_role"
    try:
        path = resolve_agent_file(role, agents_dir)
    except AgentFrontmatterError:
        return False, "invalid_role_name"
    metadata = parse_agent_file(path)
    if metadata.get("__symlink_rejected__") == "leaf":
        return False, "file_symlink_rejected"
    if metadata.get("__symlink_rejected__") == "parent":
        return False, "parent_symlink_rejected"
    if not path.is_file():
        return False, "file_missing"
    if not metadata:
        return False, "frontmatter_missing"
    actual = metadata.get("model", "").strip()
    if not actual:
        return False, "model_field_missing"
    if actual not in allowed:
        return False, f"model_mismatch:{actual}"
    return True, ""


def validate_veto_floor_models(
    agents_dir: Path,
    *,
    veto_roles: Optional[Iterable[str]] = None,
    expected_model: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """Check every VETO-floor role's agent file in one call.

    Iterates through ``veto_roles`` (default ``VETO_FLOOR_ROLES``) and
    runs ``check_veto_floor_for_role`` on each. Aggregates violations
    into a list of ``"<role>: <reason>"`` strings.

    Returns ``(ok, violations)``:

    - ``(True, [])`` if every role's frontmatter complies.
    - ``(False, [...])`` with one or more lines describing the first
      violation per role. Callers can emit each line as a separate
      ``veto_triggered`` audit event.

    Use at: (a) framework install-time smoke test, (b) CI validation,
    (c) hook-driven spawn gate (``check_agent_spawn.py``). The
    function is side-effect-free; the caller decides block-vs-log.
    """
    roles = frozenset(veto_roles) if veto_roles is not None else VETO_FLOOR_ROLES
    violations: List[str] = []
    for role in sorted(roles):
        ok, reason = check_veto_floor_for_role(
            role, agents_dir,
            veto_roles=roles,
            expected_model=expected_model,
        )
        if not ok:
            violations.append(f"{role}: {reason}")
    return (len(violations) == 0), violations
