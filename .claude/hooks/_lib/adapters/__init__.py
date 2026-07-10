"""Hook adapter package.

Each adapter module in this package translates a provider-specific hook
wire shape into the canonical `NormalizedEvent` from
`.claude/hooks/_lib/contract.py`, and serializes `Decision` back to
the provider's expected stdout shape.

Adapter ABI: `SPEC/v1/adapters.schema.md`.
Canonical envelope: `SPEC/v1/normalized_envelope.schema.md`.

## Registered adapters

- `claude` — Claude Code (production).
- `codex` — DUAL ROLE (see `codex.py`'s role map): Codex-as-HOST
  adapter (PLAN-155 Wave 1 — codex-cli runs our hooks and this adapter
  speaks its wire) AND the Pair-Rail reviewer-egress helpers
  (PLAN-081 Phase 1-full, v1.13.0).

## Dispatch seam (PLAN-155 Wave 1, debate A1 option (b))

`resolve()` below is THE single runtime seam hooks call to obtain the
adapter module for this invocation (`CEO_HOOK_ADAPTER` env-driven,
default `claude`). Its failure contract implements the debate-A2
coherence gate under the PLAN-152 C4 taxonomy:

- env var unset/empty → the `claude` default (normal path; an import
  failure THERE is an infrastructure bug and raises to the harness
  shim, which fails open per SPEC/v1 §4).
- env var EXPLICITLY set but unresolvable (unknown name, or a
  registered module that fails to import) → INPUT/mis-configuration →
  fail-CLOSED: a `_FailClosedAdapter` is returned whose egress ALWAYS
  denies (dual-vocabulary envelope readable by both harnesses), never
  a silent fallback to the claude adapter.

ADR-084 §Decision item 1 (Claude-only thesis, 2026-04-27) deferred
multi-adapter support pending demand. PLAN-075 (v5, 2026-05-09) +
PLAN-081 (R1 5/5 ADJUST PROCEED, 2026-05-09 S98) escalated demand:
the Pair-Rail Multi-LLM architecture requires a Codex adapter for
cross-review. Phase 1-full of PLAN-081 ships the Codex adapter +
egress redactor + ingress sanitization PostToolUse hook. Future
provider adapters (Gemini, local-LLM via Ollama) require their own
PLAN-NNN with explicit ADAPTER_REGISTRY extension via this file.

## Registry

`ADAPTER_REGISTRY` is the authoritative list of shipped adapter names,
mirrored by `_lib.contract.KNOWN_ADAPTERS`. The env var
`CEO_HOOK_ADAPTER` selects at runtime (default `claude`). NOTE the
deliberate asymmetry (PLAN-155 A2): the string-level
`contract.resolve_adapter()` keeps its historical silent fallback for
observability consumers, but the MODULE-level `resolve()` seam here —
the one enforcement hooks call — fails CLOSED on an explicitly-set-but-
unresolvable value.
"""

from __future__ import annotations

from typing import List

# Mirror of _lib.contract.KNOWN_ADAPTERS. Duplicated intentionally so
# that downstream tools can import the list without pulling in the
# contract module. Keep in sync with KNOWN_ADAPTERS; drift detector
# will flag if they diverge.
#
# PLAN-081 Phase 1-full extension: ["claude"] → ["claude", "codex"].
# Codex adapter implements SPEC/v1/adapters.schema.md ABI in full
# (read_event / read_post_event / write_decision / emit_decision)
# plus Pair-Rail-specific helpers (_classify_prompt_complexity,
# parse_verdict, make_invoke_command, compute_redaction_inputs).
ADAPTER_REGISTRY: List[str] = ["claude", "codex"]


# ---------------------------------------------------------------------------
# PLAN-155 Wave 1 — dispatch seam (debate A1 option (b)) + A2 fail-CLOSED.
# ---------------------------------------------------------------------------
#
# Before this seam existed, `CEO_HOOK_ADAPTER` had ZERO consumers in the
# enforcement hooks (PLAN-155 dispatch-surface inventory, artifact
# `PLAN-155/artifacts/dispatch-surface-inventory-A1.md`): every ENFORCED
# hook hard-imported the claude adapter, so setting the env var changed
# nothing and every "ENFORCED under codex" claim would have been the
# S254 silently-ABSENT class. The four ENFORCED hooks
# (check_canonical_edit / check_bash_safety / check_plan_edit /
# check_arbitration_kernel) migrate to `resolve()` in this same wave;
# the subprocess positive controls prove the dispatch actually happens.

#: Name of the env var consumed by `resolve()` (mirror of
#: `_lib.contract.ADAPTER_ENV_VAR`; duplicated so downstream tools can
#: import it without pulling in the contract module).
ADAPTER_ENV_VAR: str = "CEO_HOOK_ADAPTER"

_DEFAULT_ADAPTER_NAME: str = "claude"


class _FailClosedAdapter:
    """Adapter-shaped object whose egress ALWAYS denies (PLAN-155 A2).

    Returned by `resolve()` when `CEO_HOOK_ADAPTER` is explicitly set
    but cannot be honored — an INPUT/mis-configuration failure per the
    PLAN-152 C4 taxonomy, so the session must NOT silently fall back to
    the claude adapter (the operator believes a different harness's
    rails are armed).

    Implements the SPEC/v1 §3 ABI surface (`read_event` /
    `read_post_event` / `write_decision` / `emit_decision`). The deny
    envelope speaks BOTH harness vocabularies — top-level
    `{"decision": "block", "reason"}` (Claude Code / codex Stop family)
    AND `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}`
    (codex PreToolUse) — because under a mis-configuration we cannot
    know which harness is reading.
    """

    FAIL_CLOSED: bool = True
    ADAPTER_VERSION: str = "fail-closed"

    def __init__(self, resolution_error: str) -> None:
        self.resolution_error = resolution_error

    # -- ingress ----------------------------------------------------------
    def read_event(self, stream=None, phase: str = "PreToolUse"):
        from .. import contract as _contract
        import sys as _sys

        if stream is None:
            stream = _sys.stdin
        try:  # drain stdin so the host never sees a broken pipe
            stream.read()
        except Exception:
            pass
        if phase not in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
            phase = "PreToolUse"
        return _contract.NormalizedEvent(
            phase=phase,
            raw_payload={
                "ceo_adapter_resolution_error": self.resolution_error,
                "ceo_coherence_error": self.resolution_error,
            },
        )

    def read_post_event(self, stream=None):
        return self.read_event(stream=stream, phase="PostToolUse")

    # -- egress (unconditional deny) ---------------------------------------
    def write_decision(self, decision=None, event=None) -> str:
        import json as _json

        reason = (
            "[adapter coherence gate] " + self.resolution_error
            + " — explicitly-configured adapter unavailable; failing CLOSED "
            "per PLAN-152 C4 / PLAN-155 debate A2 (no silent fallback)"
        )
        return _json.dumps(
            {
                "decision": "block",
                "reason": reason,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                },
            },
            ensure_ascii=False,
        )

    def emit_decision(self, decision=None, stream=None, event=None) -> None:
        import sys as _sys

        if stream is None:
            stream = _sys.stdout
        stream.write(self.write_decision(decision, event=event) + "\n")


def _seam_breadcrumb(message: str) -> None:
    """stderr breadcrumb for degraded seam paths (effective_config precedent)."""
    try:
        import sys as _sys

        _sys.stderr.write("[adapters.resolve] {0}\n".format(message))
    except Exception:  # pragma: no cover (defensive)
        pass


def _seam_audit_breadcrumb(message: str) -> None:
    """Best-effort AUDIT breadcrumb for the fail-CLOSED branches.

    Debate A2 names three consequences for an
    explicitly-set-but-unresolvable ``CEO_HOOK_ADAPTER``: fail-CLOSED deny
    (the `_FailClosedAdapter`), an audit breadcrumb (this), and a
    SessionStart boot-check surface (Wave 3b). The emit reuses the
    registered ``veto_triggered`` action — no new `_KNOWN_ACTIONS` row —
    and NEVER raises: a broken audit pipe must not turn the deny into a
    crash (the deny itself is carried by the returned adapter object).
    """
    try:
        import os as _os

        from .. import audit_emit as _audit_emit

        _audit_emit.emit_veto_triggered(
            hook="adapters.resolve",
            reason_code="adapter_resolution_failed",
            reason_preview=message,
            blocked_tool="*",
            project=_os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:  # pragma: no cover (defensive; audit is best-effort)
        pass


def resolve(env=None):
    """Return the adapter MODULE for this invocation (PLAN-155 seam).

    Args:
        env: optional mapping to read `CEO_HOOK_ADAPTER` from
            (defaults to `os.environ`; tests pass a dict).

    Contract (debate A2 / PLAN-152 C4 — see the module docstring):

    - unset/empty → the `claude` module (default). ImportError here is
      an INFRASTRUCTURE bug and propagates (the harness shim fails
      open per SPEC/v1 §4).
    - set to a registered name → that module. If the module import
      FAILS despite registration, the explicit request cannot be
      honored → `_FailClosedAdapter`.
    - set to an unregistered name → `_FailClosedAdapter`.

    The fail-CLOSED branches emit a stderr breadcrumb; hooks need no
    special handling — the returned object satisfies the same ABI and
    denies at egress.
    """
    import os as _os

    src = env if env is not None else _os.environ
    requested = (src.get(ADAPTER_ENV_VAR) or "").strip()

    if not requested:
        from . import claude as _claude  # infrastructure failure → raise

        return _claude

    if requested not in ADAPTER_REGISTRY:
        msg = (
            "CEO_HOOK_ADAPTER={0!r} is not a registered adapter "
            "(registry: {1})".format(requested, ADAPTER_REGISTRY)
        )
        _seam_breadcrumb(msg + " — failing CLOSED")
        _seam_audit_breadcrumb(msg)
        return _FailClosedAdapter(msg)

    try:
        import importlib

        return importlib.import_module(__name__ + "." + requested)
    except Exception as e:
        msg = (
            "CEO_HOOK_ADAPTER={0!r} is registered but failed to import "
            "({1})".format(requested, type(e).__name__)
        )
        _seam_breadcrumb(msg + " — failing CLOSED")
        _seam_audit_breadcrumb(msg)
        return _FailClosedAdapter(msg)

# PLAN-090 Wave B — BatchClaudeLiveAdapter re-export (ADR-123).
# PERF: import is LAZY to avoid paying the ~44ms ssl/socket/urllib.request
# import tax on every hook subprocess that only needs `_lib.adapters.claude`.
# The live transport chain (live/__init__.py → _transport.py) eagerly imports
# ssl + socket + urllib.request; those modules add ~32ms to subprocess startup
# on macOS/ubuntu over the python3 baseline (~12ms). This lazy wrapper defers
# the import to the first call-site that actually instantiates BatchClaudeLiveAdapter
# (always a CEO_LIVE_CLAUDE=1 live-adapter path, never a governance hook path).
# See PLAN-120 WS-J check_agent_spawn p99 regression diagnosis.
_BatchClaudeLiveAdapter = None  # type: ignore[assignment]


def _get_batch_claude_live_adapter():
    """Lazy accessor for BatchClaudeLiveAdapter — defers ssl/socket import.

    Call-sites that previously imported BatchClaudeLiveAdapter at module level
    MUST migrate to calling _get_batch_claude_live_adapter() instead.  The
    returned class is identical; the deferred import is the only difference.
    Returns None if the live adapter package is unavailable (fail-open).
    """
    global _BatchClaudeLiveAdapter
    if _BatchClaudeLiveAdapter is None:
        try:
            from .live.claude_batch import BatchClaudeLiveAdapter  # noqa: PLC0415
            _BatchClaudeLiveAdapter = BatchClaudeLiveAdapter
        except Exception:  # pragma: no cover — defensive
            pass
    return _BatchClaudeLiveAdapter


# Backward-compat attribute access via __getattr__ so existing
# `from _lib.adapters import BatchClaudeLiveAdapter` call-sites continue to
# work without modification (they just pay the import cost at their own call
# time rather than at package init time).
def __getattr__(name: str):
    if name == "BatchClaudeLiveAdapter":
        return _get_batch_claude_live_adapter()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
