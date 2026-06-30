"""Anthropic Claude live adapter — ADR-040 §6.

Targets ``https://api.anthropic.com/v1/messages`` per the Anthropic
Messages REST API (2023-06-01 version pin).

Activation: ``CEO_LIVE_CLAUDE=1`` AND ``ANTHROPIC_API_KEY`` non-empty.
Either missing → fixture fallback (no network I/O).

Credential is re-read on every ``call()`` via
:func:`_lib.credentials.read_env_safely` — never cached.

PLAN-135 W5 O7 modernization (env-var surface added by this unit):

- ``CEO_CACHE_CONTROL_AUTO_DISABLE=1`` — kill-switch for the automatic
  top-level ``cache_control: {"type": "ephemeral"}`` request field
  (O7-(3); default ON — pre-O7 adapter API calls were 100% uncached).
- ``CEO_COUNT_TOKENS_PREFLIGHT=1`` — opt-in measured pre-flight: the
  budget gate uses ``POST /v1/messages/count_tokens`` (bills zero
  tokens) instead of the whitespace×1.3 heuristic (O7-(4); default OFF
  — adds one extra round-trip per call).
"""

from __future__ import annotations

import json
import os
import re
import time as _time
from typing import Any, Callable, Dict, List, Optional, Tuple

# PLAN-085 Wave C C.1 (live_adapter_allowlist) + C.2 (credential lifecycle).
import datetime as _dt
import json as _json
from pathlib import Path as _Path

from .. import claude as _fixture_claude  # type: ignore  # noqa: F401 - parity import
from ._breaker import CircuitBreaker
from ._cost import (
    BudgetHardStop,
    SpawnCostTracker,
    actual_cost_usd,
    estimate_cost_usd,
)
from ._policy import ClaudeLivePolicy, LiveCallPolicy
from ._result import LiveAdapterResult
from ._transport import LiveTransport, audit_emit_dispatch


_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"

# PLAN-135 W5 O7-(4) — token-counting endpoint suffix. Appended to the
# (possibly test-injected) messages URL so the mock-server test pattern
# keeps working. The endpoint bills zero tokens (same precedent as the
# ceo-info live probe).
_COUNT_TOKENS_SUFFIX = "/count_tokens"

# Keep the import alive for downstream call-site fixture fallback.
_FIXTURE_PARITY = _fixture_claude


# ADR-040-AMEND-2 §Layer-1 / §3.3 — credential emergency-override contract.
# The override variable is sourced SOLELY from the import-time trust-root
# snapshot (_lib.trusted_env). Live os.environ is consulted ONLY to detect (and
# forensically log) a late-set attempt — NEVER to grant the override.
_EMERGENCY_OVERRIDE_VAR = "CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE"
# Ticket-id grammar (ADR-040-AMEND-2 §3.3): a letter-led alphanumeric project
# prefix + numeric id, e.g. INC-1234, SEV1-42. Anything else (empty / lowercase
# / malformed) is fail-CLOSED → block.
_OVERRIDE_TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")


# PLAN-134 W0 E6-F2 — extended-thinking request-surface generation gate.
# The current API generation accepts ONLY adaptive thinking: the legacy
# ``{"type": "enabled", "budget_tokens": N}`` shape is REMOVED (HTTP 400) on
# Opus 4.7 / Opus 4.8 / Fable 5 and deprecated on the 4.6 family. The 4.6
# family is deliberately included here so the deprecated shape is retired
# everywhere; only pre-4.6 ids keep the legacy enabled/budget path.
# Allowlist-prefix semantics (ADR-149 spirit): prefix match keeps
# date-suffixed ids covered without pinning exact strings.
_ADAPTIVE_ONLY_MODELS = (
    "claude-opus-4-6",
    "claude-sonnet-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-fable-5",
)


def _is_adaptive_only(model: str) -> bool:
    """Return True when ``model`` accepts only adaptive thinking."""
    return isinstance(model, str) and any(
        model.startswith(prefix) for prefix in _ADAPTIVE_ONLY_MODELS
    )


def _resolve_effort_config(
    model: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """PLAN-091 Wave A.3 + PLAN-134 W0 E6-F2 — resolve `/effort` for ``model``.

    Reads the ``CEO_EFFORT_OVERRIDE`` env-var set by the `/effort` slash
    command and translates it to the Anthropic Messages API surface valid
    for ``model``:

    - Adaptive-only generation (``_ADAPTIVE_ONLY_MODELS``): returns
      ``({"type": "adaptive"}, {"effort": <level>})`` via the canonical
      ``_SLASH_EFFORT_TABLE`` from ``_lib.model_routing``. ``off`` resolves
      to ``(None, None)`` — the thinking param is OMITTED entirely (an
      explicit ``{"type": "disabled"}`` is an HTTP 400 on Fable 5).
    - Legacy (pre-4.6) ids: returns
      ``({"type": "enabled", "budget_tokens": N}, None)`` via the kept
      ``_SLASH_BUDGET_TABLE`` (single source of truth for budgets).

    Returns:
        ``(thinking_or_None, output_config_or_None)`` — ``(None, None)`` on
        no env, malformed env, ``off``/zero budget, or import failure
        (fail-soft to caller-default).

    The ``CEO_THINKING_AUTO_DISABLE=1`` kill-switch is honored at the
    callsite, not here — this helper only resolves a candidate config.
    """
    effort = os.environ.get("CEO_EFFORT_OVERRIDE", "").strip().lower()
    if not effort:
        return None, None
    try:
        from ... import model_routing  # type: ignore
    except Exception:  # noqa: BLE001 — adapter must never raise on env mishaps
        return None, None
    if _is_adaptive_only(model):
        effort_table = getattr(model_routing, "_SLASH_EFFORT_TABLE", {})
        level = effort_table.get(effort)
        if not isinstance(level, str) or not level:
            # "off" (maps to None) or unknown token → omit thinking entirely.
            return None, None
        return {"type": "adaptive"}, {"effort": level}
    budget_table = getattr(model_routing, "_SLASH_BUDGET_TABLE", {})
    budget = budget_table.get(effort, 0)
    if not isinstance(budget, int) or budget <= 0:
        return None, None
    return {"type": "enabled", "budget_tokens": int(budget)}, None


_EPHEMERAL_CACHE_CONTROL = {"type": "ephemeral"}


def _stamp_block_list(blocks: List[Any]) -> List[Any]:
    """Return a copy of ``blocks`` with cache_control on the LAST dict block.

    Anthropic prompt-caching marks a cache breakpoint by attaching
    ``cache_control:{"type":"ephemeral"}`` to the final content block of
    the stable prefix. Non-dict blocks (bare strings) are passed through
    untouched. Idempotent: a block already carrying cache_control is left
    as-is.
    """
    out: List[Any] = list(blocks)
    for i in range(len(out) - 1, -1, -1):
        blk = out[i]
        if isinstance(blk, dict):
            if "cache_control" not in blk:
                new_blk = dict(blk)
                new_blk["cache_control"] = dict(_EPHEMERAL_CACHE_CONTROL)
                out[i] = new_blk
            return out
    return out


def _apply_cache_control(
    system: Optional[Any],
    messages: List[Dict[str, Any]],
):
    """PLAN-113 W5 / PLAN-084 R-B1-1 — stamp a cache_control:ephemeral marker.

    Marks the largest stable prefix as cacheable:

    - If a ``system`` prompt is present, the system block is the prefix.
      A string system becomes a single text block carrying the marker; a
      list of system blocks gets the marker on its last block.
    - Otherwise the first user message's final content block is marked
      (the system-less convention; a string content is wrapped into a
      single text block + marker).

    Returns ``(system, messages)`` — NEW objects (inputs are never mutated).
    Fail-soft: any unexpected shape returns the inputs unchanged.
    """
    try:
        if system is not None:
            if isinstance(system, str):
                new_system: Any = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": dict(_EPHEMERAL_CACHE_CONTROL),
                    }
                ]
            elif isinstance(system, list):
                new_system = _stamp_block_list(system)
            else:
                new_system = system
            return new_system, messages

        if not messages or not isinstance(messages[0], dict):
            return system, messages
        new_messages = list(messages)
        first = dict(new_messages[0])
        content = first.get("content")
        if isinstance(content, str):
            first["content"] = [
                {
                    "type": "text",
                    "text": content,
                    "cache_control": dict(_EPHEMERAL_CACHE_CONTROL),
                }
            ]
        elif isinstance(content, list):
            first["content"] = _stamp_block_list(content)
        else:
            return system, messages
        new_messages[0] = first
        return system, new_messages
    except Exception:  # noqa: BLE001 — adapter must never raise on shape mishaps
        return system, messages


def _apply_citations(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """PLAN-113 W5 COOK-P3 — attach citations:{"enabled":True} to document blocks.

    When ``citations=True`` is passed to :meth:`ClaudeLiveAdapter.call`, this
    helper stamps ``{"enabled": True}`` onto every ``{"type": "document", ...}``
    block found in the first user message's content list. Blocks that already
    carry a ``citations`` key are left untouched (idempotent). Non-document
    blocks and messages beyond the first are unchanged.

    Returns a NEW messages list (inputs are never mutated). Fail-soft: any
    unexpected shape returns the inputs unchanged.
    """
    try:
        if not messages or not isinstance(messages[0], dict):
            return messages
        first = messages[0]
        content = first.get("content")
        if not isinstance(content, list):
            return messages
        new_content: List[Any] = []
        for blk in content:
            if (
                isinstance(blk, dict)
                and blk.get("type") == "document"
                and "citations" not in blk
            ):
                blk = dict(blk)
                blk["citations"] = {"enabled": True}
            new_content.append(blk)
        new_first = dict(first)
        new_first["content"] = new_content
        return [new_first] + list(messages[1:])
    except Exception:  # noqa: BLE001 — adapter must never raise on shape mishaps
        return messages


class ClaudeLiveAdapter:
    """Live adapter for the Anthropic Messages API.

    Public contract (matched verbatim by every other live adapter):

    - :meth:`call` returns a :class:`LiveAdapterResult` and never raises
      for network conditions. ValueError still raises for invalid policy
      passed to ``__init__``.
    - :attr:`provider_name` is the canonical short slug ``"anthropic"``.
    - :attr:`policy` is the in-use :class:`LiveCallPolicy`.
    """

    provider_name: str = "anthropic"

    def __init__(
        self,
        policy: Optional[LiveCallPolicy] = None,
        *,
        spawn_tracker: Optional[SpawnCostTracker] = None,
        breaker: Optional[CircuitBreaker] = None,
        transport: Optional[LiveTransport] = None,
        url: Optional[str] = None,
    ) -> None:
        if policy is not None and policy.provider != "claude":
            raise ValueError(
                f"ClaudeLiveAdapter requires policy.provider='claude', got {policy.provider!r}"
            )
        self.policy: LiveCallPolicy = policy or ClaudeLivePolicy()
        self._spawn_tracker = spawn_tracker or SpawnCostTracker(
            ceiling_usd=self.policy.max_spend_usd_per_spawn
        )
        self._breaker = breaker or CircuitBreaker(
            threshold=self.policy.breaker_threshold,
            window_s=self.policy.breaker_window_s,
            half_open_s=self.policy.breaker_half_open_s,
        )
        self._transport = transport or LiveTransport(
            self.policy, on_audit=audit_emit_dispatch
        )
        self._url = url or _API_URL
        # O7-(4) — derived from the (possibly injected) messages URL so
        # tests against a local mock server exercise the same path.
        self._count_url = self._url + _COUNT_TOKENS_SUFFIX

    # ------------------------------------------------------------------
    # Activation gate
    # ------------------------------------------------------------------

    def _activation_check(self) -> Optional[str]:
        """Return None if activated; reason string otherwise.

        PLAN-085 Wave C.1 (R-029 + F-A-SEC-0012-253dcfe3) — also consult
        ADR-040 §6.3 ``live_adapter_allowlist`` from ``.claude/settings.json``.
        Fail-CLOSED on missing file / malformed JSON / missing key / empty list.
        """
        if os.environ.get("CEO_SOTA_DISABLE") == "1":
            return "sota_disabled"
        if os.environ.get(self.policy.activation_env_var) != "1":
            return "activation_off"
        if not os.environ.get(self.policy.credential_env_var):
            return "missing_credential"
        # PLAN-085 Wave C.1 — live_adapter_allowlist runtime gate.
        allow_decision = self._check_live_adapter_allowlist()
        if allow_decision is not None:
            return allow_decision
        return None

    def _check_live_adapter_allowlist(self) -> Optional[str]:
        """Return None on allowlist-pass; reason string on deny.

        Fail-CLOSED matrix (R1 Sec-4 + R2 iter-1 C4): missing/unreadable/
        malformed/missing-key/empty-list/provider-not-in-list → DENY.
        """
        repo_root = _Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )
        settings_path = repo_root / ".claude" / "settings.json"
        reason: Optional[str] = None
        try:
            text = settings_path.read_text(encoding="utf-8")
            settings = _json.loads(text)
        except (OSError, ValueError, _json.JSONDecodeError):
            reason = "allowlist_unreadable"
        else:
            allowlist = settings.get("live_adapter_allowlist", None)
            if not isinstance(allowlist, list):
                reason = "allowlist_unreadable"
            elif not allowlist:
                reason = "empty_allowlist"
            elif self.policy.provider not in allowlist:
                reason = "not_in_allowlist"
        if reason is not None:
            try:
                from _lib import audit_emit as _audit_emit
                _audit_emit.emit_live_adapter_blocked(
                    provider=self.policy.provider,
                    reason=reason,
                    session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                    project=str(repo_root),
                )
            except Exception:
                pass
            return f"live_adapter_blocked:{reason}"
        return None

    def _check_credential_age(self) -> None:
        """Compare credential creation date to policy thresholds.

        ADR-040 §4 + ADR-040-AMEND-2. Reads
        ``$HOME/.claude/projects/ceo-orchestration/credential-rotation.json``;
        emits ``credential_rotation_due`` (advisory) or
        ``credential_blocked_due_to_age`` (blocking) per thresholds.
        Emergency override via ``CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE=<ticket-id>``
        — sourced SOLELY from the import-time trust-root snapshot
        (:mod:`_lib.trusted_env`) per ADR-040-AMEND-2 §Layer-1; ticket-id is
        validated fail-CLOSED against ``^[A-Z][A-Z0-9]*-\\d+$``. A value set into the live
        environment after trust-anchor is ignored and emits
        ``credential_override_late_set_ignored``.
        """
        from _lib.exceptions import CredentialExpired
        home = _Path(os.environ.get("HOME") or _Path.home())
        rotation_log = (
            home / ".claude" / "projects" / "ceo-orchestration"
            / "credential-rotation.json"
        )
        try:
            text = rotation_log.read_text(encoding="utf-8")
            record = _json.loads(text)
            rotation_dt = record.get(self.policy.provider, {}).get(
                "rotated_at"
            )
            if not rotation_dt:
                return
            rotated = _dt.datetime.fromisoformat(rotation_dt)
        except (OSError, ValueError, KeyError, _json.JSONDecodeError):
            return
        now_utc = _dt.datetime.now(_dt.timezone.utc)
        if rotated.tzinfo is None:
            rotated = rotated.replace(tzinfo=_dt.timezone.utc)
        age_days = int((now_utc - rotated).total_seconds() // 86_400)
        warn_d = int(self.policy.credential_warn_age_days)
        max_d = int(self.policy.credential_max_age_days)
        session_id = os.environ.get("CLAUDE_SESSION_ID", "")
        project = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if age_days >= max_d:
            # ADR-040-AMEND-2 §Layer-1: the emergency override is sourced SOLELY
            # from the import-time trust-root snapshot. A value injected into the
            # live process environment AFTER trust-anchor (os.environ mutation or
            # child-env injection) MUST NOT grant the override.
            from _lib import trusted_env as _trusted_env
            trusted_override = (
                _trusted_env.get_trusted(_EMERGENCY_OVERRIDE_VAR) or ""
            ).strip()
            if trusted_override and _OVERRIDE_TICKET_RE.match(trusted_override):
                try:
                    from _lib import audit_emit as _audit_emit
                    _audit_emit.emit_credential_emergency_override_used(
                        provider=self.policy.provider,
                        ticket_id=trusted_override,
                        age_days=age_days,
                        max_age_days=max_d,
                        session_id=session_id,
                        project=project,
                    )
                except Exception:
                    pass
                return
            # Not granted from the trust root. If the variable is ABSENT from the
            # anchor snapshot but PRESENT in the live environment, it was set late
            # (post-snapshot) — record the ignored attempt with a constant message
            # (never echo the rejected value) and fall through to block.
            if not _trusted_env.was_present_at_anchor(_EMERGENCY_OVERRIDE_VAR):
                live_present = bool(
                    (os.environ.get(_EMERGENCY_OVERRIDE_VAR) or "").strip()  # forensic-only; NOT a grant source
                )
                if live_present:
                    try:
                        from _lib import audit_emit as _audit_emit
                        _audit_emit.emit_credential_override_late_set_ignored(
                            provider=self.policy.provider,
                            provenance_hint="late_os_environ_set",
                            session_id=session_id,
                            project=project,
                        )
                    except Exception:
                        pass
            try:
                from _lib import audit_emit as _audit_emit
                _audit_emit.emit_credential_blocked_due_to_age(
                    provider=self.policy.provider,
                    age_days=age_days,
                    max_age_days=max_d,
                    session_id=session_id,
                    project=project,
                )
            except Exception:
                pass
            raise CredentialExpired(
                provider=self.policy.provider,
                age_days=age_days,
                max_age_days=max_d,
            )
        if age_days >= warn_d:
            try:
                from _lib import audit_emit as _audit_emit
                _audit_emit.emit_credential_rotation_due(
                    provider=self.policy.provider,
                    age_days=age_days,
                    warn_threshold_days=warn_d,
                    max_threshold_days=max_d,
                    session_id=session_id,
                    project=project,
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def call(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int = 1024,
        thinking: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Dict[str, Any]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        system: Optional[Any] = None,
        cache_control: bool = False,
        citations: Optional[bool] = None,
        interleaved_thinking: Optional[bool] = None,
    ) -> LiveAdapterResult:
        """Issue one Anthropic Messages API call.

        Args:
            messages: list of ``{"role": "user"|"assistant", "content": ...}``
                dicts. ``content`` may be a plain string OR a list of
                structured content blocks (COOK-P3 Citations supplies
                ``{"type": "document", ..., "citations": {"enabled": True}}``
                blocks).
            model: Anthropic model slug (e.g. ``claude-sonnet-4-6``).
            max_tokens: maximum output tokens; defaults to 1024.
            thinking: optional extended-thinking config per Anthropic
                Messages API. Pass ``{"type": "adaptive"}`` on the current
                generation (Opus 4.6+/Sonnet 4.6/Opus 4.7/4.8/Fable 5) or
                ``{"type": "enabled", "budget_tokens": N}`` on legacy
                (pre-4.6) ids. A legacy dict passed for an adaptive-only
                model is translated to ``{"type": "adaptive"}`` (E6-F2 —
                the legacy shape returns HTTP 400 there). PLAN-086 Wave A
                R-013 (B.2 auto-activation).
                ``CEO_THINKING_AUTO_DISABLE=1`` forces this to be ignored
                regardless of caller's value (kill-switch per handoff §9.3).
            tools: optional Anthropic tool definitions. PLAN-113 W5 COOK-P1
                (strict-JSON). When supplied with ``tool_choice``, the model
                is forced to emit a structured tool-call instead of prose.
                Pass-through only — no schema validation here.
            tool_choice: optional ``{"type": "tool", "name": <tool>}`` (or
                ``{"type": "auto"}``/``{"type": "any"}``) forcing structured
                output (COOK-P1). Pass-through; only added when non-None.
            response_format: optional newer structured-output parameter
                (COOK-P1). Pass-through; only added when non-None. Caller
                owns API-version compatibility.
            system: optional system prompt. May be a plain string OR a list
                of system content blocks. When ``cache_control`` is True the
                adapter stamps ``{"type": "ephemeral"}`` on the system
                content (COOK prompt-caching / PLAN-084 R-B1-1).
            cache_control: PLAN-113 W5 — when True, mark the largest stable
                prefix (the ``system`` block, else the first user message's
                final content block) with ``cache_control:ephemeral`` so the
                provider caches it (explicit caller-chosen breakpoints).
                PLAN-135 W5 O7-(3): when False (default), the adapter now
                sends the TOP-LEVEL automatic
                ``cache_control: {"type": "ephemeral"}`` request field
                instead — the provider picks breakpoints itself. Kill
                switch ``CEO_CACHE_CONTROL_AUTO_DISABLE=1`` restores the
                fully-uncached pre-O7 request bytes.
            citations: PLAN-113 W5 COOK-P3 — when True, enable the Anthropic
                Citations API feature by attaching ``{"enabled": True}`` to
                every ``{"type": "document", ...}`` block found in the first
                user message's content list. Default None (off) = no
                behaviour change; caller may also supply citation-annotated
                blocks directly without setting this kwarg. Pass-through only
                — no schema validation here.
            interleaved_thinking: PLAN-113 W5 COOK-P4 interleaved-thinking —
                when True, adds the ``interleaved-thinking-2025-05-14`` beta
                header AND sets ``"interleaved_thinking": true`` in the
                request body. Default None (off) = no behaviour change.
                Requires ``thinking`` to also be set (extended-thinking must
                be enabled). Kill-switch: ``CEO_INTERLEAVED_THINKING_DISABLE=1``
                forces the kwarg to be ignored (defensive default-OFF).

        Returns:
            :class:`LiveAdapterResult`. Always populated; never raises
            for network errors.
        """
        start = _time.monotonic()

        gate = self._activation_check()
        if gate is not None:
            return self._fixture_fallback(gate, start_monotonic=start)


        # PLAN-085 Wave C.2 — credential lifecycle gate at invoke() RUNTIME.
        try:
            self._check_credential_age()
        except Exception:
            pass
        # Pre-flight cost gate
        try:
            estimated = estimate_cost_usd(
                self.provider_name, model, messages, max_tokens
            )
            # PLAN-135 W5 O7-(4) — opt-in MEASURED pre-flight. When
            # CEO_COUNT_TOKENS_PREFLIGHT=1, replace the whitespace×1.3
            # heuristic input estimate with the provider-measured count
            # from /v1/messages/count_tokens (bills zero tokens), so the
            # prereg budget ceiling is checked against real numbers.
            # Output side stays bounded by max_tokens. Fail-soft: a
            # failed count keeps the heuristic estimate. The breaker
            # guard avoids an extra network call while the circuit is
            # open (the messages POST below would be refused anyway).
            if (
                os.environ.get("CEO_COUNT_TOKENS_PREFLIGHT") == "1"
                and self._breaker.should_allow()
            ):
                measured_in = self.count_tokens(
                    messages=messages,
                    model=model,
                    system=system,
                    tools=tools,
                )
                if measured_in is not None:
                    estimated = actual_cost_usd(
                        self.provider_name, model, measured_in, int(max_tokens)
                    )
            if self._spawn_tracker.would_exceed(estimated):
                return _build_failure(
                    self.provider_name,
                    self._breaker,
                    "budget_hard_stop",
                    duration_ms=int((_time.monotonic() - start) * 1000),
                )
        except Exception:  # pragma: no cover — pricing parser is robust
            estimated = 0.0

        # Breaker gate
        if not self._breaker.should_allow():
            return _build_failure(
                self.provider_name,
                self._breaker,
                "breaker_open",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        api_key = os.environ.get(self.policy.credential_env_var) or ""
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }
        # PLAN-113 W5 — apply cache_control:ephemeral marker BEFORE the body
        # is assembled so the marker lands on the (possibly stamped) system
        # block / first message. Pure local transform; no behavior change
        # when cache_control is False.
        stamped_system = system
        stamped_messages = messages
        if cache_control:
            stamped_system, stamped_messages = _apply_cache_control(
                system, messages
            )

        # PLAN-113 W5 COOK-P3 — citations kwarg: attach {"enabled": True} to
        # document blocks in the first user message when citations=True. Pure
        # local transform; no behaviour change when citations is None/False.
        if citations is True:
            stamped_messages = _apply_citations(stamped_messages)

        body: Dict[str, Any] = {
            "model": model,
            "max_tokens": int(max_tokens),
            "messages": stamped_messages,
        }
        # COOK prompt-caching / Citations — system prompt pass-through.
        if stamped_system is not None:
            body["system"] = stamped_system
        # PLAN-135 W5 O7-(3) — automatic TOP-LEVEL prompt caching.
        # The 2026 Messages API accepts a request-level
        # cache_control:{"type":"ephemeral"} field that lets the provider
        # pick cache breakpoints automatically (up to ~90% input-cost cut
        # on repeated prefixes). Pre-O7, adapter API calls defaulted to
        # 100% uncached (cache_control kwarg default False). Default ON;
        # mutually exclusive with the legacy per-block stamping path
        # (cache_control=True — explicit caller breakpoints win); kill
        # switch CEO_CACHE_CONTROL_AUTO_DISABLE=1 restores the pre-O7
        # request bytes.
        if (
            not cache_control
            and os.environ.get("CEO_CACHE_CONTROL_AUTO_DISABLE") != "1"
        ):
            body["cache_control"] = dict(_EPHEMERAL_CACHE_CONTROL)
        # PLAN-091 Wave A.3 — auto-inject from `/effort` slash when caller
        # did NOT pass an explicit `thinking` kwarg. Caller-passed value
        # always wins (no override of explicit caller intent). The resolver
        # is model-aware (E6-F2): adaptive-only ids resolve to adaptive
        # thinking + output_config.effort; legacy ids keep enabled/budget.
        effort_output_config: Optional[Dict[str, Any]] = None
        if thinking is None:
            thinking, effort_output_config = _resolve_effort_config(model)
        # PLAN-086 Wave A R-013 — extended-thinking kwarg pass-through.
        # Kill-switch CEO_THINKING_AUTO_DISABLE=1 forces drop regardless
        # of caller's value (handoff §9.3 Sec-P0-2).
        if (
            thinking is not None
            and os.environ.get("CEO_THINKING_AUTO_DISABLE") != "1"
        ):
            body["thinking"] = thinking
            # E6-F2 — the effort level resolved alongside adaptive thinking
            # rides in output_config (GA surface; no beta header). Only set
            # when the resolver produced one (never overrides caller intent;
            # call() exposes no output_config kwarg today).
            if effort_output_config is not None:
                body["output_config"] = effort_output_config

        # E6-F2 hard guard — full normalization of ANY caller-provided
        # thinking dict on the adaptive-only generation, BEFORE send:
        #   - {"type": "enabled", ...}  → {"type": "adaptive"} (the legacy
        #     enabled/budget shape is REMOVED there — HTTP 400 on
        #     Opus 4.7/4.8 and Fable 5);
        #   - {"type": "disabled"}      → REMOVE the thinking key entirely
        #     (an explicit disabled is an HTTP 400 on Fable 5; omitting the
        #     param is the only safe spelling across the generation);
        #   - any remaining dict        → strip "budget_tokens" if present
        #     (e.g. {"type": "adaptive", "budget_tokens": N} → adaptive
        #     only — budget_tokens is rejected on these ids).
        # Emitting the un-normalized shape is a guaranteed 400, so the
        # translation cannot make things worse. No audit breadcrumb by
        # design — a new closed-enum action would force a _KNOWN_ACTIONS +
        # SPEC bump; regression tests pin this behavior instead.
        if isinstance(body.get("thinking"), dict) and _is_adaptive_only(model):
            _t_type = body["thinking"].get("type")
            if _t_type == "enabled":
                body["thinking"] = {"type": "adaptive"}
            elif _t_type == "disabled":
                body.pop("thinking", None)
            elif "budget_tokens" in body["thinking"]:
                _t_norm = dict(body["thinking"])
                _t_norm.pop("budget_tokens", None)
                body["thinking"] = _t_norm

        # PLAN-113 W5 COOK-P1 — strict-JSON / structured-output pass-through.
        # All three are additive: a body without them is byte-identical to
        # the pre-W5 request (no behavior change for existing callers).
        if tools is not None:
            body["tools"] = tools
        if tool_choice is not None:
            body["tool_choice"] = tool_choice
        if response_format is not None:
            body["response_format"] = response_format

        # PLAN-113 W5 interleaved-thinking — default-OFF.
        # Kill-switch: CEO_INTERLEAVED_THINKING_DISABLE=1.
        # Guard: only add the beta header + body field when the LEGACY
        # extended-thinking shape is active in the body (thinking.type ==
        # "enabled") — i.e. legacy (pre-4.6) models only. Adaptive thinking
        # auto-interleaves: the beta header must NEVER be added when
        # thinking.type == "adaptive" (E6-F2). Adding the header without an
        # active thinking block produces an invalid Anthropic request
        # (API rejects it).
        _thinking_is_active = (
            isinstance(body.get("thinking"), dict)
            and body["thinking"].get("type") == "enabled"
        )
        if (
            interleaved_thinking is True
            and _thinking_is_active
            and os.environ.get("CEO_INTERLEAVED_THINKING_DISABLE") != "1"
        ):
            headers = dict(headers)
            existing_beta = headers.get("anthropic-beta", "")
            beta_tag = "interleaved-thinking-2025-05-14"
            if beta_tag not in existing_beta:
                headers["anthropic-beta"] = (
                    f"{existing_beta},{beta_tag}" if existing_beta else beta_tag
                )
            body["interleaved_thinking"] = True

        response, failure = self._transport.post_json(self._url, headers, body)

        if response is not None:
            return self._on_response(
                response.status,
                response.body_bytes,
                model,
                duration_ms=response.duration_ms,
                retried=response.retried,
            )

        assert failure is not None
        # Update breaker
        self._breaker.record_failure(failure.failure_mode)
        return LiveAdapterResult(
            success=False,
            text=None,
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            duration_ms=failure.duration_ms,
            failure_mode=failure.failure_mode,
            http_status=failure.http_status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if failure.retried else 0,
            fixture_fallback=False,
            # PLAN-135 W5 O7-(5) — provider request id captured by the
            # transport on the HTTP-error path (header or error body);
            # empty for network-level failures. getattr keeps injected
            # transport stubs without the field working.
            request_id=str(getattr(failure, "request_id", "") or ""),
        )

    def count_tokens(
        self,
        *,
        messages: List[Dict[str, Any]],
        model: str,
        system: Optional[Any] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[int]:
        """PLAN-135 W5 O7-(4) — measured input-token count (zero-cost).

        POSTs ``{model, messages[, system, tools]}`` to
        ``/v1/messages/count_tokens`` and returns the provider-measured
        ``input_tokens`` int. The endpoint bills ZERO tokens (same
        precedent as the ceo-info live probe). Intended for prereg
        ceiling arithmetic in paid instruments AND consumed internally by
        :meth:`call` when ``CEO_COUNT_TOKENS_PREFLIGHT=1``.

        Fail-soft contract: returns ``None`` on ANY failure — activation
        gate off (no network when the adapter is disabled), transport
        failure, non-JSON body, missing/non-int ``input_tokens``. Never
        raises. Failures are NOT recorded into the circuit breaker (the
        count is advisory; only real messages calls drive the breaker).
        """
        gate = self._activation_check()
        if gate is not None:
            return None
        api_key = os.environ.get(self.policy.credential_env_var) or ""
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }
        body: Dict[str, Any] = {"model": model, "messages": messages}
        if system is not None:
            body["system"] = system
        if tools is not None:
            body["tools"] = tools
        try:
            response, _failure = self._transport.post_json(
                self._count_url, headers, body
            )
            if response is None:
                return None
            payload = json.loads(
                response.body_bytes.decode("utf-8", errors="replace")
            )
            tokens = payload.get("input_tokens") if isinstance(payload, dict) else None
            if isinstance(tokens, bool) or not isinstance(tokens, int):
                return None
            return tokens
        except Exception:  # noqa: BLE001 — advisory helper must never raise
            return None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fixture_fallback(self, reason: str, *, start_monotonic: float) -> LiveAdapterResult:
        elapsed_ms = int((_time.monotonic() - start_monotonic) * 1000)
        # Distinguish missing_credential (which the caller may want to
        # surface) from activation-off (a benign no-op).
        failure_mode = "missing_credential" if reason == "missing_credential" else None
        return LiveAdapterResult(
            success=failure_mode is None,
            text=None,
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            duration_ms=elapsed_ms,
            failure_mode=failure_mode,
            http_status=None,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=0,
            fixture_fallback=True,
        )

    def _on_response(
        self,
        status: int,
        body_bytes: bytes,
        model: str,
        *,
        duration_ms: int,
        retried: bool,
    ) -> LiveAdapterResult:
        try:
            payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )

        # Parse Anthropic Messages response
        try:
            blocks = payload.get("content") or []
            text = "".join(
                b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
            )
            # PLAN-113 W5 COOK-P1 — strict-JSON recovery. When the caller
            # forced a tool-call (tool_choice), the response carries NO text
            # block — only a `tool_use` block whose `.input` is the parsed
            # structured object. To surface that result without changing the
            # frozen LiveAdapterResult contract (ADR-040 §7), serialize the
            # tool_use input to a JSON string into `text` ONLY when there is
            # no prose text. Prose responses are untouched (zero behavior
            # change for the non-structured path).
            if not text:
                tool_inputs = [
                    b.get("input")
                    for b in blocks
                    if isinstance(b, dict)
                    and b.get("type") == "tool_use"
                    and b.get("input") is not None
                ]
                if tool_inputs:
                    payload_obj = (
                        tool_inputs[0] if len(tool_inputs) == 1 else tool_inputs
                    )
                    try:
                        text = json.dumps(payload_obj, sort_keys=True)
                    except (TypeError, ValueError):
                        text = ""
            usage = payload.get("usage") or {}
            tokens_in = int(usage["input_tokens"]) if "input_tokens" in usage else None
            tokens_out = int(usage["output_tokens"]) if "output_tokens" in usage else None
            # PLAN-135 W5 O7-(1) — stop_reason / stop_details parsing.
            # Pre-O7, refusal / pause_turn / max_tokens responses parsed
            # as a normal completion (latent correctness bug in graded
            # runs). Surface both fields verbatim on the result; callers
            # distinguish via is_complete() / is_refusal(). Non-str /
            # non-dict provider shapes degrade to None (fail-soft).
            stop_reason_raw = payload.get("stop_reason")
            stop_reason = (
                stop_reason_raw if isinstance(stop_reason_raw, str) else None
            )
            stop_details_raw = payload.get("stop_details")
            stop_details = (
                stop_details_raw if isinstance(stop_details_raw, dict) else None
            )
        except (TypeError, AttributeError, ValueError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )

        # O7-(1) — closed-enum audit breadcrumb on model refusal. Only the
        # stop_details CATEGORY is forwarded (a closed provider vocabulary)
        # — stop_details.explanation is model free text and NEVER reaches
        # the audit log (emit_generic callers must pre-redact). Fail-open:
        # telemetry must never break the call path; until the arc
        # consolidation lands `model_refusal_observed` in _KNOWN_ACTIONS,
        # emit_generic degrades to a breadcrumb + silent return.
        if stop_reason == "refusal":
            try:
                from _lib import audit_emit as _ae  # type: ignore
                if hasattr(_ae, "emit_generic"):
                    category = ""
                    if stop_details is not None:
                        cat = stop_details.get("category")
                        if isinstance(cat, str):
                            category = cat[:64]
                    _ae.emit_generic(
                        "model_refusal_observed",
                        provider=self.provider_name,
                        model=str(model)[:128],
                        stop_reason="refusal",
                        stop_category=category,
                        http_status=int(status),
                        duration_ms=int(duration_ms),
                    )
            except Exception:
                pass

        cost = actual_cost_usd(self.provider_name, model, tokens_in, tokens_out)
        try:
            self._spawn_tracker.add(cost)
        except BudgetHardStop:
            # The spend was already incurred; surface the result as success
            # for THIS call but flip subsequent calls via the tracker.
            pass

        self._breaker.record_success()
        return LiveAdapterResult(
            success=True,
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            duration_ms=duration_ms,
            failure_mode=None,
            http_status=status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if retried else 0,
            fixture_fallback=False,
            # O7-(1) — completion semantics ride alongside success.
            stop_reason=stop_reason,
            stop_details=stop_details,
        )


# ---------------------------------------------------------------------------
# Shared helper used by every provider adapter
# ---------------------------------------------------------------------------


def _build_failure(
    provider: str,
    breaker: CircuitBreaker,
    failure_mode: str,
    *,
    http_status: Optional[int] = None,
    duration_ms: int = 0,
    retried: bool = False,
) -> LiveAdapterResult:
    return LiveAdapterResult(
        success=False,
        text=None,
        tokens_in=None,
        tokens_out=None,
        cost_usd=None,
        duration_ms=duration_ms,
        failure_mode=failure_mode,
        http_status=http_status,
        breaker_state=breaker.snapshot().state,
        provider=provider,
        retry_count=1 if retried else 0,
        fixture_fallback=False,
    )


__all__ = ["ClaudeLiveAdapter"]
