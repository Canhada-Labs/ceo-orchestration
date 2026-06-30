"""MCP routing resolver — PLAN-086 Wave D (R-015).

Maps ``task_class`` strings to MCP server names for the 12-server
``auto-activate-mcp-v1`` bundle. Advisory only: callers MAY ignore
the recommendation; the resolver never blocks.

References:
  ADR-042 §Cost.4  — kill-switch parity (CEO_SOTA_DISABLE + per-server
                     CEO_MCP_<SERVER>_DISABLE env vars).
  handoff §3       — file-ownership matrix; BatchClaudeLiveAdapter and
                     full model_routing.py:resolve() are PLAN-088 W4.2/
                     W2.2 canonical owners; this module is MCP-only.

Stdlib-only. Python >= 3.9. NO third-party deps.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Optional


#: All MCP server names in the bundle. Order is canonical.
BUNDLE_SERVERS = (
    "claude-in-chrome",
    "Supabase",
    "Vercel",
    "Stripe",
    "Gmail",
    "Google_Calendar",
    "Google_Drive",
    "Sentry",
    "Cloudflare_Developer_Platform",
    "Ahrefs",
    "Similarweb",
    "LunarCrush",
)


def _kill_switch_env(server_name: str) -> str:
    """Return the per-server kill-switch env var name."""
    normalized = server_name.upper().replace("-", "_").replace(" ", "_")
    return f"CEO_MCP_{normalized}_DISABLE"


_SERVER_KILL_SWITCHES: Dict[str, str] = {
    s: _kill_switch_env(s) for s in BUNDLE_SERVERS
}


# Conservative routing: only map when capability is clearly superior.
_ROUTING_TABLE: Dict[str, str] = {
    "arch": "Vercel",
    "finops": "Stripe",
    "seo_research": "Ahrefs",
    "crypto_research": "LunarCrush",
}


_audit_emit_mod = None
_audit_emit_tried = False


def _lazy_audit_emit():
    global _audit_emit_mod, _audit_emit_tried
    if _audit_emit_tried:
        return _audit_emit_mod
    _audit_emit_tried = True
    try:
        from _lib import audit_emit  # type: ignore
        _audit_emit_mod = audit_emit
    except Exception:
        _audit_emit_mod = None
    return _audit_emit_mod


def _emit_advisory(
    task_class: str,
    suggested_servers: str,
    kill_switch_overrides: str,
) -> None:
    """Best-effort emit of mcp_route_advised (AC D.4).

    Field names + caps mirror the canonical ``_MCP_ROUTE_ADVISED_ALLOWLIST``
    schema (PLAN-086 Wave D) and the sibling producer in
    ``check_agent_spawn.py``. ``signal_source`` is fixed to the task-class
    routing discriminator.

    Prior field names (``server`` / ``kill_switch_active`` /
    ``global_disable``) were NOT in the allowlist and were silently scrubbed
    on every emit, so the recorded events lost their whole AML.T0050 payload
    (which MCP server, kill-switch state). ``kill_switch_overrides`` now
    carries the active override env-var name(s) for real forensic value.
    See the S169 audit-log.errors triage.
    """
    ae = _lazy_audit_emit()
    if ae is None:
        return
    known = getattr(ae, "_KNOWN_ACTIONS", None)
    if known is not None and "mcp_route_advised" not in known:
        sys.stderr.write(
            "[mcp_routing] 'mcp_route_advised' not in _KNOWN_ACTIONS; "
            "emit will be dropped until sentinel ceremony lands.\n"
        )
        return
    try:
        if hasattr(ae, "emit_generic"):
            ae.emit_generic(
                "mcp_route_advised",
                task_class=str(task_class)[:32],
                suggested_servers=str(suggested_servers)[:128],
                kill_switch_overrides=str(kill_switch_overrides)[:128],
                signal_source="mcp_task_class",
            )
    except Exception:
        pass


def resolve(task_class: str) -> Optional[str]:
    """Return the recommended MCP server name for ``task_class``, or None.

    Returns None when:
      - task_class has no MCP server mapping (use local tooling)
      - The recommended server's kill-switch env var is set to "1"
      - CEO_SOTA_DISABLE=1 is set (global kill-switch, ADR-042 §Cost.4)

    Emits ``mcp_route_advised`` audit event (best-effort, AC D.4).
    """
    global_disable = os.environ.get("CEO_SOTA_DISABLE", "0") == "1"
    if global_disable:
        _emit_advisory(task_class, "", "CEO_SOTA_DISABLE")
        return None

    server = _ROUTING_TABLE.get(task_class)
    if server is None:
        _emit_advisory(task_class, "", "")
        return None

    ks_env = _SERVER_KILL_SWITCHES.get(server, _kill_switch_env(server))
    kill_switch_active = os.environ.get(ks_env, "0") == "1"
    if kill_switch_active:
        _emit_advisory(task_class, "", ks_env)
        return None

    _emit_advisory(task_class, server, "")
    return server


#: Public alias.
route = resolve
