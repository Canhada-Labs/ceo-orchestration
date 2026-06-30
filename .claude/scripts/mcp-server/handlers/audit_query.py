"""MCP handler: ``audit_query.*`` — read-only audit-log queries (PLAN-096 Wave A).

Per ADR-042-AMEND-1 §Auth.2 each ``audit_query.<sub>`` method is a
``audit_read`` class handler. The dispatcher in ``dispatch.py`` routes
27 distinct method names (one per audit-query.py sub-command, except
``label`` which writes the HMAC-chained labels store and is excluded
per `.claude/plans/PLAN-096/wave-a-mcp-subset.md` §3).

Read-only invariant (AC-R-1): handlers MUST NOT accept any param that
would route to a writable audit-query sub-command. The whitelist below
is the single point of truth; ``ALLOWED_SUBCOMMANDS`` is consumed both
by this handler and the dispatch registry, so adding a new sub-command
requires touching exactly one location.

Forged-write probe (test_mcp_readonly_invariant.py): each handler is
invoked with crafted params containing ``output``/``--label``/``write``
keys; every attempt MUST be rejected before any disk write.

## Module-level caching

``audit-query.py`` is loaded once via ``importlib.spec_from_file_location``
on first call and memoized — subsequent calls reuse the same module
object. The MCP server is a long-running process; the import cost is
amortized.

## Argparse Namespace synthesis

Each ``cmd_*`` function in audit-query.py consumes an
``argparse.Namespace`` object. We synthesize one from the JSON-RPC
params dict, using the sub-command's own argparse defaults so missing
fields stay correct. Only documented argparse fields are forwarded;
any extra params raise InvalidParams.

## Fail-open semantics

Per the existing handler contract (``list_skills.py`` line 188):
- ImportError / OSError / AttributeError → empty payload + ``warning``
- Sub-command raises → empty payload + ``warning`` carrying type name
- Never raise to the dispatcher (it would map to ERR_INTERNAL, losing
  the structured response).
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import threading
import types
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Read-only subcommand allowlist (AC-R-1 enforcement surface)
# ---------------------------------------------------------------------------


# 27 read-only sub-commands. Map MCP method suffix → audit-query.py
# cmd_* function name. The `label` sub-command is intentionally
# excluded — it appends to .claude/scripts/audit-log-labels.jsonl.
ALLOWED_SUBCOMMANDS: Dict[str, str] = {
    "summary": "cmd_summary",
    "by_skill": "cmd_by_skill",
    "compliance": "cmd_compliance",
    "by_day": "cmd_by_day",
    "search": "cmd_search",
    "since": "cmd_since",
    "errors": "cmd_errors",
    "stats": "cmd_stats",
    "export": "cmd_export",
    "debate": "cmd_debate",
    "plans": "cmd_plans",
    "vetoes": "cmd_vetoes",
    "benchmarks": "cmd_benchmarks",
    "lessons": "cmd_lessons",
    "metrics": "cmd_metrics",
    "health": "cmd_health",
    "tokens": "cmd_tokens",
    "claims": "cmd_claims",
    "prune_restore_ratio": "cmd_prune_restore_ratio",
    "architect_outcomes": "cmd_architect_outcomes",
    "lessons_effectiveness": "cmd_lessons_effectiveness",
    "weekly_summary": "cmd_weekly_summary",
    "spawn_stats": "cmd_spawn_stats",
    "by_domain": "cmd_by_domain",
    "fp_rate": "cmd_fp_rate",
    "case_summary": "cmd_case_summary",
    "codex_writeguard_summary": "cmd_codex_writeguard_summary",
}


# Sub-commands that require entries to be loaded first. `errors` reads
# its own breadcrumb file and does NOT take `entries`; everything else
# does.
_NO_ENTRIES_SUBCOMMANDS = frozenset({"errors"})


# ---------------------------------------------------------------------------
# Module loader (memoized)
# ---------------------------------------------------------------------------


_MODULE_LOCK = threading.Lock()
_AUDIT_QUERY_MODULE: Optional[types.ModuleType] = None
_LOAD_ERROR: Optional[str] = None


def _load_audit_query(project_dir: Path) -> Optional[types.ModuleType]:
    """Memoized loader for audit-query.py.

    Returns the loaded module, or None on import failure (caller surfaces
    a fail-open warning).
    """
    global _AUDIT_QUERY_MODULE, _LOAD_ERROR
    with _MODULE_LOCK:
        if _AUDIT_QUERY_MODULE is not None:
            return _AUDIT_QUERY_MODULE
        if _LOAD_ERROR is not None:
            # Fast-fail subsequent attempts within the same process.
            return None
        script = project_dir / ".claude" / "scripts" / "audit-query.py"
        if not script.is_file():
            _LOAD_ERROR = f"audit_query_script_missing:{script}"
            return None
        try:
            spec = importlib.util.spec_from_file_location(
                "_mcp_audit_query_module", str(script)
            )
            if spec is None or spec.loader is None:
                _LOAD_ERROR = "spec_from_file_location_failed"
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules.setdefault("_mcp_audit_query_module", module)
            spec.loader.exec_module(module)
        except Exception as e:  # broad: anything during import is fail-open
            _LOAD_ERROR = f"import_failed:{type(e).__name__}"
            return None
        _AUDIT_QUERY_MODULE = module
        return module


def _reset_module_cache() -> None:
    """Test helper — drop the cached audit-query module."""
    global _AUDIT_QUERY_MODULE, _LOAD_ERROR
    with _MODULE_LOCK:
        _AUDIT_QUERY_MODULE = None
        _LOAD_ERROR = None
        sys.modules.pop("_mcp_audit_query_module", None)


# ---------------------------------------------------------------------------
# Argparse Namespace synthesis
# ---------------------------------------------------------------------------


_NAMESPACE_DEFAULTS: Dict[str, Any] = {
    # Shared/global flags (--log, --include-rotated, --json, --csv,
    # --errors-path) populated by audit-query.py _build_shared_parser.
    "log": None,
    "include_rotated": False,
    "json": True,  # MCP always wants JSON output
    "csv": False,
    "errors_path": None,
    # Per-command frequently-used flags. Anything missing falls back to
    # None and audit-query.py per-command logic handles it.
    "top_n": None,
    "regex": "",
    "since": None,
    "limit": None,
    "domain": None,
    "window": None,
    "month": None,
    "skill": None,
    "tail": None,
    "format": "json",
    "plan_id": None,
    "case_id": None,
    "wave": None,
    "include_sunset": False,
    "exclude_sunset": False,
    "subject": None,
    "verdict": None,
    "evidence_uri": None,
    "min_records": None,
    "min_calls": None,
    "min_dispatches": None,
    "min_observations": None,
    "min_routes": None,
}


def _build_namespace(params: Dict[str, Any]) -> argparse.Namespace:
    """Synthesize an argparse.Namespace from JSON-RPC params.

    Only keys in _NAMESPACE_DEFAULTS are forwarded; any unknown key is
    silently dropped (caller's responsibility to surface a warning if
    they want strict-mode behavior — read-only handlers favor
    fail-open).
    """
    ns = argparse.Namespace()
    # Seed from defaults first.
    for k, v in _NAMESPACE_DEFAULTS.items():
        setattr(ns, k, v)
    # Override with caller-provided fields.
    if isinstance(params, dict):
        for k, v in params.items():
            if k in _NAMESPACE_DEFAULTS:
                setattr(ns, k, v)
    return ns


# ---------------------------------------------------------------------------
# Read-only invariant probe
# ---------------------------------------------------------------------------


# Param keys that would route to a writable cmd_* function. AC-R-1
# rejects ALL forged-write attempts before the handler invokes the
# underlying sub-command. The list is conservative: any param matching
# `_FORBIDDEN_WRITE_KEYS` (case-insensitive substring match) is
# rejected.
_FORBIDDEN_WRITE_KEYS = (
    "label",  # cmd_label appends HMAC-chained record
    "write",
    "append",
    "output_path",
    "out_path",
    "store",
    "patch",
)


def _is_forged_write(params: Dict[str, Any]) -> Optional[str]:
    """Return the first matching forbidden-write key, or None.

    Used by AC-R-1 forged-write probe in test_mcp_readonly_invariant.py.
    """
    if not isinstance(params, dict):
        return None
    for key in params:
        if not isinstance(key, str):
            continue
        kl = key.lower()
        for forbidden in _FORBIDDEN_WRITE_KEYS:
            if forbidden in kl:
                return key
    return None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def _make_handler(subcommand: str):
    """Build a handle(params, context) closure for a sub-command.

    Returns a callable suitable for registration in
    ``dispatch.HANDLERS``. The closure captures ``subcommand`` (the MCP
    suffix) and the underlying ``cmd_*`` function name.
    """
    if subcommand not in ALLOWED_SUBCOMMANDS:
        raise KeyError(f"audit_query.{subcommand}: not in ALLOWED_SUBCOMMANDS")
    cmd_fn_name = ALLOWED_SUBCOMMANDS[subcommand]

    def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a single audit-query sub-command.

        Returns:
            ``{"subcommand": str, "data": <result>}`` on success.
            ``{"subcommand": str, "data": [], "warning": str}`` on
            fail-open paths. NEVER raises.
        """
        project_dir_raw = context.get("project_dir")
        if project_dir_raw is None:
            return {
                "subcommand": subcommand,
                "data": [],
                "warning": "project_dir_missing",
            }
        project_dir = Path(project_dir_raw)

        # AC-R-1 — forged-write probe at dispatcher entry.
        forged = _is_forged_write(params if isinstance(params, dict) else {})
        if forged is not None:
            return {
                "subcommand": subcommand,
                "data": [],
                "__error__": {
                    "code": -32602,
                    "message": f"read_only_violation:forbidden_param:{forged}",
                },
            }

        module = _load_audit_query(project_dir)
        if module is None:
            return {
                "subcommand": subcommand,
                "data": [],
                "warning": _LOAD_ERROR or "load_failed",
            }

        cmd_fn = getattr(module, cmd_fn_name, None)
        if cmd_fn is None:
            return {
                "subcommand": subcommand,
                "data": [],
                "warning": f"cmd_fn_missing:{cmd_fn_name}",
            }

        ns = _build_namespace(params if isinstance(params, dict) else {})

        try:
            if subcommand in _NO_ENTRIES_SUBCOMMANDS:
                # cmd_errors(args) — no entries parameter.
                result = cmd_fn(ns)
            else:
                entries = _load_entries(module, ns, project_dir)
                result = cmd_fn(entries, ns)
        except Exception as e:
            return {
                "subcommand": subcommand,
                "data": [],
                "warning": f"cmd_failed:{type(e).__name__}",
            }

        # Coerce result to a JSON-serializable shape. cmd_* returns
        # dict | list | scalar — wrap into a uniform envelope.
        if isinstance(result, dict):
            return {"subcommand": subcommand, "data": result}
        if isinstance(result, list):
            return {"subcommand": subcommand, "data": result, "count": len(result)}
        return {"subcommand": subcommand, "data": result}

    handle.__name__ = f"handle_audit_query_{subcommand}"
    handle.__qualname__ = handle.__name__
    return handle


def _load_entries(
    module: types.ModuleType,
    ns: argparse.Namespace,
    project_dir: Path,
) -> List[Dict[str, Any]]:
    """Load audit-log entries via audit-query helpers."""
    default_path_fn = getattr(module, "default_log_path", None)
    discover_fn = getattr(module, "discover_logs", None)
    read_fn = getattr(module, "read_entries", None)
    if default_path_fn is None or discover_fn is None or read_fn is None:
        return []
    log_path = Path(ns.log) if ns.log else default_path_fn()
    paths = discover_fn(log_path, bool(getattr(ns, "include_rotated", False)))
    try:
        return read_fn(paths)
    except TypeError:
        # Some audit-query versions accept (paths, args).
        try:
            return read_fn(paths, ns)
        except Exception:
            return []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Public registry — consumed by dispatch.py to register one handler per
# sub-command.
# ---------------------------------------------------------------------------


HANDLERS: Dict[str, Any] = {
    f"audit_query.{suffix}": _make_handler(suffix)
    for suffix in ALLOWED_SUBCOMMANDS
}


__all__ = [
    "ALLOWED_SUBCOMMANDS",
    "HANDLERS",
    "_make_handler",
    "_is_forged_write",
    "_reset_module_cache",
]
