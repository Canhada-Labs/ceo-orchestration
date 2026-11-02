"""Audit-entry construction and usage metadata declarations."""
from __future__ import annotations

def build_entry(
    *,
    event: "_contract.NormalizedEvent | _payload.HookPayload",
    project_dir: str,
    hook_duration_ms: int,
) -> Optional[Dict[str, Any]]:
    """Construct a JSONL row from a NormalizedEvent (or legacy HookPayload).

    Accepts either type for backward compatibility with older tests.
    Returns None if the event indicates a non-Agent tool (defensive — the
    matcher should already filter to Agent).
    """
    tool_name = getattr(event, "tool_name", "")
    if tool_name and tool_name not in ("Agent", "unknown"):
        return None

    description = getattr(event, "description", "") or ""
    prompt = getattr(event, "prompt", "") or ""
    session_id = getattr(event, "session_id", "") or ""
    subagent_type = getattr(event, "subagent_type", "") or ""
    tool_response = getattr(event, "tool_response", {}) or {}

    desc_preview = _redact.redact_secrets(description)
    desc_hash = _redact.hash_description(description)
    # PLAN-079: pass subagent_type for Path D archetype-mapping fallback.
    skill = extract_skill(prompt, subagent_type)

    # PLAN-006 Phase 5b (ADR-016): extract token counts from tool_response.
    # Always emit the keys (even if None) so consumers can distinguish
    # "post-ADR-016 emitter with unknown shape" from "pre-ADR-016 emitter".
    tin, tout = _tokens.extract_tokens(tool_response)
    ttotal = _tokens.total_tokens(tool_response)

    # PLAN-020 Phase 0 item 1: capture Anthropic usage_metadata for cache
    # coverage analysis. Additive v2.7 fields. Null-safe for emitters that
    # don't provide usage_metadata (legacy + non-Anthropic adapters).
    usage_metadata = _extract_usage_metadata(tool_response)
    # PLAN-118 WS-E (S181): the derived ratio is a FLOAT, which
    # ``canonical_json.encode()`` forbids in HMAC-covered payloads
    # (``CanonicalJsonError`` → fail-open ``hmac:null`` → chain one-way-rule
    # break → whole-chain ``tamper``). Encode as integer basis-points
    # (ratio × 10000, clamped 0..10000) BEFORE it reaches the entry dict.
    # Mirrors the S164 ``hit_rate`` → ``hit_rate_bps`` class fix; closes the
    # last live float-in-HMAC leak (the agent_spawn observer path that the
    # S164 emit_* introspection guard never covered).
    cache_coverage = _compute_cache_coverage(usage_metadata)
    cache_coverage_bps = (
        max(0, min(10000, int(round(cache_coverage * 10000))))
        if cache_coverage is not None
        else None
    )

    # PLAN-020 Phase 1: dual-rail discriminator. Detect from prompt
    # structure (## SKILL REFERENCE = native rail; ## SKILL CONTENT =
    # custom inline rail) OR from subagent_type matching canonical-5.
    rail = _detect_rail(prompt, subagent_type)

    # PLAN-021 ADR-052: model discriminator. Captured from Anthropic
    # API response when present. Null-safe for non-Anthropic adapters.
    # PLAN-044 audit-v2 C3-P0-01 (Wave B): fall back to ADR-052
    # role-to-model policy when tool_response.model is null (default
    # behavior of Task tool response shape at v1.11.0).
    model = _extract_model(tool_response, subagent_type=subagent_type)

    # PLAN-044 audit-v2 C3-P0-08 (Wave B): archetype + dispatch_mode
    # fields. Audit-telemetry.py per-archetype rollups depend on these
    # being non-null. ADR-082 per-archetype dispatch claim was undone
    # at v1.11.0 because no emitter wrote them. Wave B closes the gap.
    archetype = subagent_type if (
        isinstance(subagent_type, str) and subagent_type
    ) else None
    dispatch_mode = _resolve_dispatch_mode(subagent_type or "", rail)

    # PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2): capture dispatch_archetype_hint
    # from the IN-PROMPT marker emitted by inject-agent-context.sh:
    #   `<!-- ceo-dispatch-archetype-hint: <slug> -->`
    # The marker propagates cross-process via the recorded `prompt` payload —
    # env vars do NOT survive the inject-agent-context.sh subprocess → Agent
    # tool dispatch → audit hook subprocess chain (Codex iter 2 finding).
    #
    # Validated via the same NFKC + ≤64 char + charset `^[a-z][a-z0-9-]*$` +
    # control/JSON-meta rejection contract as `_lib.audit_emit._validate_dispatch_archetype_hint`.
    # On rejection (or marker absent): returns None (fail-open). The field is
    # always emitted in the audit row — null when no hint is set/validated,
    # validated string otherwise.
    dispatch_archetype_hint = _extract_dispatch_archetype_hint(prompt)

    entry: Dict[str, Any] = {
        "ts": now_iso_utc(),
        "action": "agent_spawn",
        "session_id": session_id,
        "project": project_dir,
        "tool": tool_name or "Agent",
        "subagent_type": subagent_type,
        "desc_preview": desc_preview,
        "desc_hash": desc_hash,
        "skill": skill,
        "has_profile": has_profile(prompt),
        "has_file_assignment": has_file_assignment(prompt),
        "prompt_len_bucket": bucket_prompt_length(len(prompt)),
        "response_kind": _payload.response_kind(tool_response),
        "hook_duration_ms": int(hook_duration_ms),
        # Tokens (ADR-016): optional nullable, always-present.
        "tokens_in": tin,
        "tokens_out": tout,
        "tokens_total": ttotal,
        # PLAN-020 v2.7 additions (ADDITIVE — older consumers ignore).
        "usage_metadata": usage_metadata,
        # PLAN-118 WS-E (S181): integer basis-points (ratio × 10000) — the
        # legacy float ``cache_coverage`` field is REMOVED (it caused
        # CanonicalJsonError + fail-open hmac:null on every real spawn).
        "cache_coverage_bps": cache_coverage_bps,
        "rail": rail,
        # PLAN-021 v2.8 addition (ADDITIVE — ADR-052 multi-model).
        "model": model,
        # PLAN-044 audit-v2 v2.14 additions (Wave B C3-P0-08).
        "archetype": archetype,
        "dispatch_mode": dispatch_mode,
        # PLAN-080 Phase 1 v2.24 addition (M2-C3 + M2-CDX-1) —
        # dispatch_archetype_hint captured pre-ADR-082-mitigation.
        # Validated via _lib.audit_emit redaction contract.
        # Always-present (null when env unset or validation rejected).
        "dispatch_archetype_hint": dispatch_archetype_hint,
    }
    return entry


# -----------------------------------------------------------------------------
# PLAN-020 v2.7 cache-header capture helpers (Phase 0 item 1)
# -----------------------------------------------------------------------------

# Canonical-5 archetypes that ship with native subagent files (ADR-050).
# Rail discrimination: archetype is "native" IFF its name matches AND
# subagent_type is non-empty. Else "custom" if classic spawn signal is
# present. Else null (legacy / unknown).
_CANONICAL_5 = frozenset({
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "devops",
})

# Native rail spawn-prompt sentinel (additive ADR-051; co-exists with
# the legacy "## SKILL CONTENT" inline sentinel).
_SKILL_REFERENCE_RE = re.compile(
    r"^##\s+SKILL\s+REFERENCE\s*$", re.MULTILINE
)
_SKILL_CONTENT_RE = re.compile(
    r"^##\s+SKILL\s+CONTENT\s*$", re.MULTILINE
)


def _extract_usage_metadata(tool_response: Any) -> Optional[Dict[str, Any]]:
    """Extract Anthropic usage_metadata from a tool_response payload.

    Returns a dict with `cache_creation_input_tokens`,
    `cache_read_input_tokens`, `uncached_input_tokens`, `output_tokens`,
    `thinking_tokens` — each int or None. Returns None if the payload
    has no `usage_metadata` field at all (legacy / non-Anthropic).

    Defensive: never raises; returns None on any unexpected shape.
    """
    if not isinstance(tool_response, dict):
        return None
    usage = tool_response.get("usage_metadata")
    if not isinstance(usage, dict):
        # Some emitters may put it under "usage" or in nested response.
        usage = tool_response.get("usage")
        if not isinstance(usage, dict):
            return None

    def _coerce_int(value: Any) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    return {
        "cache_creation_input_tokens": _coerce_int(
            usage.get("cache_creation_input_tokens")
        ),
        "cache_read_input_tokens": _coerce_int(
            usage.get("cache_read_input_tokens")
        ),
        "uncached_input_tokens": _coerce_int(usage.get("uncached_input_tokens")),
        "output_tokens": _coerce_int(usage.get("output_tokens")),
        "thinking_tokens": _coerce_int(usage.get("thinking_tokens")),
    }


def _compute_cache_coverage(
    usage_metadata: Optional[Dict[str, Any]],
) -> Optional[float]:
    """Derived metric: cache_read / (cache_read + cache_creation + uncached).

    Returns None if the inputs are missing or the denominator is zero
    (defensive against synthetic / mocked payloads).
    """
    if not usage_metadata:
        return None
    cache_read = usage_metadata.get("cache_read_input_tokens") or 0
    cache_creation = usage_metadata.get("cache_creation_input_tokens") or 0
    uncached = usage_metadata.get("uncached_input_tokens") or 0
    denom = cache_read + cache_creation + uncached
    if denom <= 0:
        return None
    return round(cache_read / denom, 4)


# PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2) — in-prompt hint marker pattern.
# inject-agent-context.sh emits this marker once near the top of every spawn
# prompt; audit_log.py extracts the slug at PostToolUse audit time. The
# regex captures the slug into group 1 and validates the charset inline.
_DISPATCH_HINT_MARKER_RE = re.compile(
    r"<!--\s*ceo-dispatch-archetype-hint:\s*([a-z][a-z0-9-]{0,63})\s*-->",
    re.IGNORECASE,
)


def _extract_dispatch_archetype_hint(prompt: str) -> Optional[str]:
    """PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2) — extract validated hint.

    Searches `prompt` for the in-prompt marker:
      `<!-- ceo-dispatch-archetype-hint: <slug> -->`

    Falls back to `CEO_DISPATCH_ARCHETYPE_HINT` env var ONLY if the marker
    is absent (advisory path; env vars do not reliably propagate across the
    /spawn subprocess → Agent tool dispatch → audit hook subprocess chain
    per Codex Phase 1 iter 2 finding).

    Validation contract (mirrors `_lib.audit_emit._validate_dispatch_archetype_hint`):
      1. NFKC normalize
      2. Length ≤ 64 chars post-NFKC
      3. Charset `^[a-z][a-z0-9-]*$` (lowercase prefix; hyphens + digits)
      4. Reject control bytes (0x00-0x1f, 0x7f-0x9f), null, JSON-meta `{}[]:",\\`

    On rejection: return None (fail-open per audit hook contract; never blocks).
    On marker absent + env unset: return None.
    On accept: return normalized lowercase slug.
    """
    raw: Optional[str] = None
    # Primary path: in-prompt marker
    if isinstance(prompt, str) and prompt:
        m = _DISPATCH_HINT_MARKER_RE.search(prompt)
        if m:
            raw = m.group(1)
    # Fallback path: env var (advisory; may be set by future direct callers)
    if not raw:
        raw = os.environ.get("CEO_DISPATCH_ARCHETYPE_HINT")
    if not raw:
        return None
    # Defensive try/except — must NEVER throw under fail-open contract.
    try:
        # NFKC normalize then lowercase (regex was case-insensitive)
        norm = unicodedata.normalize("NFKC", raw).lower()
        # Length cap (post-NFKC)
        if len(norm) > 64 or len(norm) == 0:
            return None
        # Charset: ^[a-z][a-z0-9-]*$
        if not re.match(r"^[a-z][a-z0-9-]*$", norm):
            return None
        # Defensive: reject if any control byte slipped through
        if any(ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f for c in norm):
            return None
        # Defensive: JSON-meta chars
        if any(c in '{}[]:,"\\' for c in norm):
            return None
        return norm
    except Exception:  # pragma: no cover (defensive — extraction never throws)
        return None


def _extract_model(
    tool_response: Any,
    subagent_type: Optional[str] = None,
) -> Optional[str]:
    """PLAN-021 ADR-052: extract Claude model ID from tool_response.

    Anthropic API responses include a `model` field (e.g. "claude-fable-5",
    "claude-opus-5", "claude-haiku-4-5"; older gens appear in replay). Some adapters nest
    it under `response.model` or `content.model`. Returns the string if
    found, else falls back to ADR-052 role-to-model policy table when
    `subagent_type` is supplied; otherwise None.

    Canonical IDs (PLAN-169 W2.10 D1 — current fleet; the table below is
    the authority, this prose only illustrates):
      - claude-fable-5 / claude-opus-5 → orchestrator + critical VETOs
      - claude-sonnet-5                → mid-complexity workers
      - claude-haiku-4-5               → high-frequency fan-out

    PLAN-044 audit-v2 C3-P0-01 fix (Wave B): the Task tool response
    shape from Claude Code's hook payload omits the `model` field on
    100% of agent_spawn events (verified at audit time: 199/199 events
    had `model: null`). Without an authoritative observation, the
    fallback uses the ADR-052 policy table — adopters reading the
    audit-log get a *policy-derived* model identity, not an
    *observation-derived* one. The two diverge only when an adopter
    overrides ADR-052 (then the audit-log over-reports the policy
    model rather than the actual model — known limitation; downstream
    cost reports re-resolve via subagent_type when present).
    """
    if isinstance(tool_response, dict):
        # Direct top-level (most Anthropic SDK shapes)
        model = tool_response.get("model")
        if isinstance(model, str) and model:
            return model
        # Nested under "response" (some adapter shapes)
        resp = tool_response.get("response")
        if isinstance(resp, dict):
            m = resp.get("model")
            if isinstance(m, str) and m:
                return m
        # Nested under "usage_metadata" sibling-content
        usage = tool_response.get("usage_metadata")
        if isinstance(usage, dict):
            m = usage.get("model")
            if isinstance(m, str) and m:
                return m

    # Wave B fallback — ADR-052 role-to-model policy table.
    if isinstance(subagent_type, str) and subagent_type:
        policy_model = _ADR_052_ROLE_TO_MODEL.get(subagent_type)
        if policy_model:
            return policy_model
    return None


# PLAN-044 audit-v2 C3-P0-01 — ADR-052 §Role-to-model distribution table.
# Used as fallback when tool_response.model is null (which happens on 100%
# of Task-dispatched spawns at v1.11.0). Pinned to canonical IDs from
# ADR-052; if an adopter overrides ADR-052 they should also override
# this table OR pre-populate tool_response.model upstream.
# PLAN-163 T1.4 (ADR-181, OQ1=b + OQ2=migrate-now): ROUTING refresh only —
# Opus-tier fallbacks move claude-opus-4-8 -> claude-opus-5 and the advisory
# (Sonnet) tier moves claude-sonnet-4-6 -> claude-sonnet-5. This table is a
# routing-policy fallback, NOT a pricing surface (grok F11): historical
# pricing/replay tables keep the old ids. Every value MUST stay inside the
# ADR-149 AVAILABLE_MODELS_WORKING_SET (tied by
# test_adr149_validator_parity.py).
_ADR_052_ROLE_TO_MODEL: Dict[str, str] = {
    # Canonical-5 VETO archetypes — Opus floor per ADR-052 + ADR-080
    "code-reviewer": "claude-opus-5",
    "security-engineer": "claude-opus-5",
    "qa-architect": "claude-sonnet-5",
    "performance-engineer": "claude-sonnet-5",
    # PLAN-169 W2.10 F8: bare id — the dated pin is not in availableModels
    # and interacts badly with enforceAvailableModels.
    "devops": "claude-haiku-4-5",
    # Mitigated rail — general-purpose dispatch inherits CEO model.
    # Default-CEO is Opus-tier unless CEO_MODEL_DOWNSHIFT is honored.
    # ADR-149 Amendment 3 (S357): follows the session-default pin, now
    # claude-opus-5-5. A POLICY value, not an observation: when the Task
    # response carries no model (the common case, see _extract_model) the
    # audit log records this row even if a per-call model or alias served
    # the spawn.
    "general-purpose": "claude-opus-5-5",
    # Probe / specialty archetypes
    "growth-engineer": "claude-sonnet-5",
    "billing-engineer": "claude-sonnet-5",
    "compliance-specialist": "claude-sonnet-5",
    "chaos-engineer": "claude-sonnet-5",
    "data-engineer": "claude-sonnet-5",
    "real-time-systems-engineer": "claude-sonnet-5",
    "refactoring-lead": "claude-sonnet-5",
    "vp-engineering": "claude-opus-5",
    "vp-product": "claude-sonnet-5",
    "vp-operations": "claude-sonnet-5",
    # PLAN-074 Wave 1c provenance — see docs/PLAN-086-adr-052-role-extension.md
    # 4 VETO-floor archetypes added per PLAN-086 Wave B (R-019 ROLE_TO_MODEL ext).
    # ADR-052 §Veto-floor expansion (lines 186-210) names these as VETO-floor;
    # llm-finops-architect carries Opus floor for cost-ceiling integrity (see
    # docs §2 §Why llm-finops-architect). ADR-052 bytes NOT mutated (anti-churn).
    "incident-commander": "claude-opus-5",
    "identity-trust-architect": "claude-opus-5",
    "threat-detection-engineer": "claude-opus-5",
    "llm-finops-architect": "claude-opus-5",
}


def _resolve_dispatch_mode(
    subagent_type: str,
    rail: Optional[str],
) -> Optional[str]:
    """PLAN-044 audit-v2 C3-P0-08 — Wave B: derive dispatch_mode field.

    Maps (subagent_type, rail) → "native" | "mitigated" per the
    PLAN-061 / ADR-082 dispatch policy:

      - canonical-5 native rail → "native" (full tool grant per
        ADR-052 floor; H4 anomaly does NOT apply because empirically
        only `code-reviewer` is reliable; PLAN-061 default-on routes
        the other 4 via mitigated).
      - any non-canonical archetype → "mitigated" (general-purpose
        with persona injected via `## SKILL CONTENT`).
      - rail=None or unknown → None (legacy / pre-PLAN-061).

    See ADR-082 §Routing decision and `inject-agent-context.sh` for
    the live override matrix (CEO_DISPATCHER_MODE,
    CEO_MITIGATION_DISABLE).
    """
    if not isinstance(subagent_type, str):
        return None
    # Canonical-5 native rail — only code-reviewer routes natively
    # by default per PLAN-061 / ADR-082. Other 4 are mitigated.
    if subagent_type == "code-reviewer" and rail == "native":
        return "native"
    if subagent_type in _CANONICAL_5 and rail == "custom":
        # Older inline ## SKILL CONTENT prompt — pre-PLAN-061 spawn.
        return "native_legacy"
    if rail is None:
        return None
    # Default mitigated rail for non-canonical-5 + non-cr canonicals
    # under PLAN-061 default-on.
    return "mitigated"


def _detect_rail(prompt: str, subagent_type: str) -> Optional[str]:
    """Detect spawn dispatch rail (native vs custom) from prompt + subagent.

    Heuristic order:
    1. If subagent_type matches a canonical-5 archetype name AND the
       prompt has `## SKILL REFERENCE` sentinel → "native".
    2. Else if prompt has `## SKILL CONTENT` (legacy inline) → "custom".
    3. Else if prompt has `## SKILL REFERENCE` only → "native"
       (subagent_type may be empty for some adapters).
    4. Else None (unknown / pre-PLAN-020 / non-spawn event).
    """
    if not isinstance(prompt, str):
        return None
    has_reference = bool(_SKILL_REFERENCE_RE.search(prompt))
    has_content = bool(_SKILL_CONTENT_RE.search(prompt))
    is_canonical = (
        isinstance(subagent_type, str) and subagent_type in _CANONICAL_5
    )

    if is_canonical and has_reference:
        return "native"
    if has_content:
        return "custom"
    if has_reference:
        return "native"
    return None


# -----------------------------------------------------------------------------
# Rotation
# -----------------------------------------------------------------------------


