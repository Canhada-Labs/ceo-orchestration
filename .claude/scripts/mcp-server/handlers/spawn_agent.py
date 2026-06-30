"""MCP handler: ``spawn_agent`` — governance-preserving spawn request.

THIS IS THE CRITICAL HANDLER. Per ADR-042 Context §1 (CRITICAL-1),
external MCP clients calling ``spawn_agent`` MUST re-enter the
EXACT SAME governance decision function that a Claude-native Agent
tool call hits (``check_agent_spawn.decide()``). Without this, Sprint
15 adoption ships a production-unsafe open door.

## Contract

Params:

- ``agent_name`` (str, required): the team archetype / persona name
  to spawn (e.g. ``"Staff Backend Engineer"``).
- ``description`` (str, required): the description that Claude's
  Agent tool would receive. Feeds the governance detector.
- ``prompt`` (str, required): the full prompt including
  ``## AGENT PROFILE`` / ``## SKILL CONTENT`` / ``## FILE ASSIGNMENT``
  sections (per Spawn Protocol).
- ``plan_id`` (str, optional): ``PLAN-NNN`` identifier for
  plan-scoped cost accounting. Server derives from audit tail if
  absent (per ADR-042 §Cost.1 M2 precedent; deferred to Sprint 14+).

Returns a ``result`` dict (NOT a JSON-RPC error):

    {
      "allowed": bool,
      "block_reason": str | None,  # present iff allowed=False
      "result": str | None         # "spawn_queued" iff allowed=True
    }

The governance deny is a SUCCESSFUL RPC call that happens to have
``allowed=False``. The JSON-RPC error envelope is reserved for
transport-level failures (malformed params, internal errors).

## Byte-identity contract (PLAN-013 consensus §C2)

The ``block_reason`` returned here MUST be byte-identical to what
``check_agent_spawn.decide()`` returns for an equivalent Claude-native
invocation with the same ``description`` + ``prompt``. Wave 2 Agent D
writes a test fixture asserting this parity: same inputs → same block
reason string.

## Budget check (ADR-042 §Cost.1)

After governance passes, the handler runs the LiveCallPolicy cost
check via ``cost.check_spawn_budget()``. Denies with:

- ``budget_hard_stop_per_spawn`` — per-spawn $0.50 ceiling.
- ``budget_hard_stop_per_plan_5min`` — per-plan 5-min $2.00 ceiling.

Breaker check (``breaker_open``) is handled by the transport-layer
adapter when the real spawn dispatches; at the MCP handler layer we
only run governance + budget. (Sprint 14+ wires the full adapter.)

## No real spawn (Sprint 13 scope)

This handler is a GOVERNANCE PASSTHROUGH ONLY — it does not actually
invoke an LLM spawn. On allow, it returns ``{"allowed": True,
"result": "spawn_queued"}`` and that's it. The real dispatch happens
in Sprint 14+ when the framework wires live adapters to the MCP
server.

This intentional scoping isolates the governance-identity contract
(the risk) from the live-spawn complexity (not the risk). The ADR-042
Transition Log will record the Sprint 14 wiring as a distinct
transition.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Make _lib + hooks importable.
_HOOKS_DIR = Path(__file__).resolve().parents[3] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import team as _team  # noqa: E402
from _lib.adapters.live._cost import (  # noqa: E402
    PlanCostTracker,
    SpawnCostTracker,
    estimate_cost_usd,
)

# Explicit, LOAD-BEARING import — PLAN-013 consensus §C2 CRITICAL.
# The spawn_agent handler MUST use the SAME governance decision
# function as Claude-native PreToolUse hooks. Do not swap this to
# a re-implementation; the byte-identity test fails if so.
import check_agent_spawn  # noqa: E402  (imported from hooks/ via sys.path)


# Module-level tracker instances. Per-process, not per-client — the
# ceiling is plan-scoped and spawn-scoped, not client-scoped (clients
# cannot launder cost by rotating tokens).
# Tests inject fresh instances via ``context["trackers"]``.
_default_spawn_tracker: Optional[SpawnCostTracker] = None
_default_plan_tracker: Optional[PlanCostTracker] = None


def _get_default_trackers() -> Dict[str, Any]:
    """Return the module-level tracker pair, initializing once."""
    global _default_spawn_tracker, _default_plan_tracker
    if _default_spawn_tracker is None:
        _default_spawn_tracker = SpawnCostTracker()  # default 0.50
    if _default_plan_tracker is None:
        _default_plan_tracker = PlanCostTracker()  # default 2.00 / 5 min
    return {
        "spawn": _default_spawn_tracker,
        "plan": _default_plan_tracker,
    }


def _resolve_trackers(context: Dict[str, Any]) -> Dict[str, Any]:
    """Return trackers from context or module-level default."""
    ctx_trackers = context.get("trackers")
    if isinstance(ctx_trackers, dict):
        spawn_t = ctx_trackers.get("spawn")
        plan_t = ctx_trackers.get("plan")
        if isinstance(spawn_t, SpawnCostTracker) and isinstance(
            plan_t, PlanCostTracker
        ):
            return {"spawn": spawn_t, "plan": plan_t}
    return _get_default_trackers()


def _run_governance(
    *,
    description: str,
    prompt: str,
    project_dir: Path,
) -> "check_agent_spawn.Decision":
    """Invoke ``check_agent_spawn.decide()`` with the full governance envelope.

    Mirrors the invocation shape in ``check_agent_spawn.main()``:
    builds the team names regex via ``_team.load_names`` on the given
    project_dir, then calls ``decide()``.
    """
    try:
        names_regex = _team.load_names(project_dir)
    except Exception:
        # Fail-open on team-load: decide() tolerates None regex.
        names_regex = None

    # Using the exact signature the hook uses for byte-identity.
    return check_agent_spawn.decide(
        description=description,
        prompt=prompt,
        names_regex=names_regex,
    )


def _estimate_spawn_cost_usd(prompt: str) -> float:
    """Rough pre-flight cost estimate for a spawn.

    We don't know the provider + model at the MCP layer — adapter
    binding is deferred to Sprint 14+. For the guard we use the
    conservative default from _cost.py's fallback rates against the
    prompt text treated as a single chat message.

    Local provider would be 0.0; we do NOT return 0 here because we
    don't know yet. The fallback over-estimates (safer for the budget
    guard — denies earlier).
    """
    # Use "anthropic" + "claude-sonnet" — the fallback rates kick in
    # if the pricing row is TBD (expected at Sprint 13 time), and the
    # conservative defaults ensure the hard stop trips sooner rather
    # than later.
    messages = [{"role": "user", "content": prompt or ""}]
    return estimate_cost_usd(
        provider="anthropic",
        model="claude-sonnet-4",
        messages=messages,
        max_tokens=4096,
    )


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Returns a result dict with ``allowed`` / ``block_reason`` / ``result``
    keys. Governance denies and budget denies are both SUCCESSFUL RPC
    calls with ``allowed=False``; only malformed params return a
    JSON-RPC error sentinel (``{"__error__": ...}``).

    The ``block_reason`` field on denial carries the EXACT string
    returned by ``check_agent_spawn.decide()`` — byte-identity parity
    with Claude-native PreToolUse behavior (PLAN-013 §C2).
    """
    if not isinstance(params, dict):
        return {"__error__": {"code": -32602, "message": "invalid_params"}}

    description = params.get("description")
    prompt = params.get("prompt")
    if not isinstance(description, str) or not description:
        return {"__error__": {"code": -32602, "message": "invalid_params"}}
    if not isinstance(prompt, str):
        return {"__error__": {"code": -32602, "message": "invalid_params"}}

    # agent_name is advisory — description / prompt drive governance.
    # We accept missing agent_name without failing.
    _agent_name = params.get("agent_name", "")

    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"__error__": {"code": -32603, "message": "internal_error"}}
    project_dir = Path(project_dir_raw)

    # ---- Governance passthrough (PLAN-013 §C2 CRITICAL) ----
    try:
        decision = _run_governance(
            description=description,
            prompt=prompt,
            project_dir=project_dir,
        )
    except Exception:
        # Fail-closed on governance internal error — deny with a
        # generic reason. This diverges from the hook's fail-open
        # posture because at the MCP layer we CAN deny safely (the
        # client can retry), whereas in-session Claude-native hooks
        # must not block their own user. Sprint 13 conservative
        # default; amend if false-positives become a problem.
        return {
            "allowed": False,
            "block_reason": "GOVERNANCE: internal_error during decision; contact operator.",
            "result": None,
        }

    if not decision.allow:
        return {
            "allowed": False,
            "block_reason": decision.reason or "",
            "result": None,
        }

    # ---- Budget check (ADR-042 §Cost.1) ----
    trackers = _resolve_trackers(context)
    estimated_usd = _estimate_spawn_cost_usd(prompt)

    # Import lazily and path-robustly. The handler module may be
    # imported as ``mcp_server.handlers.spawn_agent`` (package form)
    # OR loaded directly by sys.path insertion (server.py does the
    # latter). In both cases, ensure the ``cost`` module is importable
    # as a top-level name after the mcp-server/ dir is on sys.path.
    _mcp_server_dir = Path(__file__).resolve().parents[1]
    if str(_mcp_server_dir) not in sys.path:
        sys.path.insert(0, str(_mcp_server_dir))
    import cost as _mcp_cost  # type: ignore[import-not-found]
    allow, reason = _mcp_cost.check_spawn_budget(
        estimated_usd=estimated_usd,
        spawn_tracker=trackers["spawn"],
        plan_tracker=trackers["plan"],
    )
    if not allow:
        # Budget block reasons start with BUDGET: prefix so they are
        # grep-distinguishable from GOVERNANCE: reasons in the audit log.
        block_reason = f"BUDGET: {reason}"
        return {
            "allowed": False,
            "block_reason": block_reason,
            "result": None,
            "_budget_reason": reason,  # picked up by server.py for audit
        }

    return {
        "allowed": True,
        "block_reason": None,
        "result": "spawn_queued",
    }


__all__ = ["handle"]
