#!/usr/bin/env python3
"""Governance Hook: named agents MUST include ## SKILL CONTENT.

Registered in `.claude/settings.json` under `hooks.PreToolUse.Agent`.
Runs via the `_python-hook.sh` shim (A.4) for Python version resolution.

Port of `.claude/hooks/check-agent-spawn.sh` with:
- stdlib-only (no jq dependency)
- unit-testable (logic is in `decide()`, not tangled with stdin/stdout)
- fail-open on any internal error (never blocks the user on infrastructure bug)

## Two detection strategies

1. The agent's `description` field contains a team member name, extracted
   dynamically from team.md / frontend-team.md / domains/*/team-personas.md.
2. The prompt contains a persona header (`PERSONA:`, `## AGENT PROFILE`,
   `## PERSONA`) — self-describing spawn.

If either strategy matches, the prompt MUST contain `## SKILL CONTENT`.
Without it, the spawn is blocked as a generic agent wearing a name tag.

## Output contract

Writes a single-line JSON decision to stdout:

    {"decision":"allow"}
    {"decision":"block","reason":"GOVERNANCE: ..."}

Exit code is 0 in both cases — Claude Code reads the decision from stdout,
not the exit code. Internal errors (bad stdin, missing team files, etc.)
are logged to stderr and the spawn is allowed (fail-open).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make the _lib package importable — hooks live in .claude/hooks/ and
# _lib is a sibling package; delegated skill-reference guards cover .claude/skills/**/SKILL.md.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402
from _lib import team as _team  # noqa: E402
from _lib import redact as _redact  # noqa: E402  (PLAN-020 Phase 2: skill-ref scan)

# PLAN-106 Wave G.1 — sub-agent N-of-M aggregator with partial-drop emit.
# Re-exported below as `aggregate_subagent_findings` so coordinator-side
# callers (swarm coordinator, future debate consensus aggregator) can
# `from check_agent_spawn import aggregate_subagent_findings` without
# poking into `_lib`. Closes AC10 grep contract.
from _lib import subagent_dispatch as _subagent_dispatch  # noqa: E402

# PLAN-045 Wave 1 P0-03 — VETO floor runtime validator.
try:
    from _lib import agent_frontmatter as _agent_frontmatter
except Exception:  # pragma: no cover
    _agent_frontmatter = None  # type: ignore[assignment]

# Optional: emit veto_triggered to event stream v2 (fail-open)
try:
    # PLAN-094 Wave E — lazy-import dispatch shim closes AC9c spawn-hook regression
    from _lib import audit_emit_dispatch as _audit_emit  # noqa: E402
    _AUDIT_EMIT_AVAILABLE = True
except Exception:  # pragma: no cover
    _AUDIT_EMIT_AVAILABLE = False

# PLAN-092 Wave A.4 — cookbook-advisor pattern matcher (fail-open import).
try:
    from _lib import cookbook_patterns as _cookbook_patterns  # noqa: E402
    _COOKBOOK_PATTERNS_AVAILABLE = True
except Exception:  # pragma: no cover
    _COOKBOOK_PATTERNS_AVAILABLE = False

# PLAN-112-FOLLOWUP-persona-routing-wire W1 — persona_routing matrix
# consult (fail-open import). The god-mode (persona × primitive) routing
# matrix declares AUTO-05 ("model_routing_advised") ENFORCING per
# ADR-118-AMEND-1, but check_agent_spawn never consulted it — the policy
# was dead at runtime. This wire makes the matrix observable/auditable.
# CONSULT + AUDIT ONLY — the BLOCK is DEFERRED (the hook payload exposes
# no requested-model signal; see plan §2/§3). NEVER read
# `_PRIMITIVE_DEFAULT_MODE` directly — get_mode() encapsulates the
# kill-switch demotion.
try:
    from _lib import persona_routing as _persona_routing  # noqa: E402
except Exception:  # pragma: no cover - fail-open
    _persona_routing = None  # type: ignore[assignment]

# PLAN-113 WIRE-DEADMOD — SEC-P0-01 spec-context sanitizer (ADR-089).
# Sanitizes the ## SPEC CONTEXT block payload in spawn prompts before allow.
# ADVISORY telemetry only: sanitize result is emitted via emit_generic so
# sentinel violations / truncation are visible in the audit log. Never blocks.
# Fail-open: missing module → _SPEC_CTX_SANITIZER_AVAILABLE = False.
try:
    from _lib import spec_context_sanitizer as _spec_ctx_sanitizer  # noqa: E402
    _SPEC_CTX_SANITIZER_AVAILABLE = True
except Exception:  # pragma: no cover - fail-open
    _spec_ctx_sanitizer = None  # type: ignore[assignment]
    _SPEC_CTX_SANITIZER_AVAILABLE = False

# PLAN-113 WIRE-DEADMOD — confidence_labels (PLAN-083 Wave 1.10).
# Classifies the spawn action type and emits a spawn_confidence_advisory event
# so that recommender / receipt formatter surfaces have a hook-level signal.
# ADVISORY only — never blocks. Fail-open.
try:
    from _lib import confidence_labels as _confidence_labels  # noqa: E402
    _CONFIDENCE_LABELS_AVAILABLE = True
except Exception:  # pragma: no cover - fail-open
    _confidence_labels = None  # type: ignore[assignment]
    _CONFIDENCE_LABELS_AVAILABLE = False

# Components bind to the facade to preserve patched globals and isolated state.
def _load_spawn_part(name):
    try:
        from _lib._audit_emit_parts import install
        install(globals(), (name,), package="_lib.agent_spawn")
    except Exception as exc:
        if __name__ != "__main__":
            raise
        print(f"[check_agent_spawn] FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        print(json.dumps({}))
        sys.exit(0)

_load_spawn_part("model_routing")
_load_spawn_part("advisories")
_load_spawn_part("prompt_rules")

@dataclass
class Decision:
    """Typed result of the governance check."""

    allow: bool
    reason: Optional[str] = None

    def to_json(self) -> str:
        if self.allow:
            return json.dumps({}, ensure_ascii=False)  # schema-compliant allow
        return json.dumps(
            {"decision": "block", "reason": self.reason or ""},
            ensure_ascii=False,
        )



def _emit_cookbook_pattern_advisory(
    *,
    description: str,
    prompt: str,
    env=None,
) -> None:
    """PLAN-092 Wave A.4 (W3.2 SEMI-11) — emit cookbook_pattern_advised
    when a spawn prompt matches one of 4 Anthropic Cookbook pattern
    trigger taxonomies (COOK-P1..P4).

    Advisory ONLY — UX hint. NEVER blocks, NEVER mutates tool_input.
    Rate-cap via PLAN-088 global _plan088_rate_admit in audit_emit.
    Kill-switch: CEO_COOKBOOK_ADVISOR_ENABLED=0. Privacy invariant:
    3 fields max (no raw prompt persisted — AC3b).

    Audit-emit signature mapping (PLAN-090 W3.2 canonical contract):
      pattern_id (COOK-P*)   -> top_pattern_keys
      trigger_class (string) -> task_signature (enum-constrained "other")
      bucket (high/med/low)  -> pattern_count (3/2/1)

    NEVER raises.
    """
    try:
        src_env = env if env is not None else os.environ
        if not _COOKBOOK_PATTERNS_AVAILABLE:
            return
        if not _AUDIT_EMIT_AVAILABLE:
            return
        # Kill-switch
        try:
            if hasattr(_cookbook_patterns, "kill_switch_enabled"):
                if not _cookbook_patterns.kill_switch_enabled():
                    return
            else:
                val = (src_env.get("CEO_COOKBOOK_ADVISOR_ENABLED") or "1").strip()
                if val in ("0", "false", "False", "no", "off"):
                    return
        except Exception:  # pragma: no cover
            return
        # Concat description + prompt, cap at 8KiB
        text = ((description or "") + "\n" + (prompt or ""))[: 8 * 1024]
        if not text.strip():
            return
        # Match (first-hit canonical order COOK-P1 -> P4)
        try:
            result = _cookbook_patterns.match_pattern(text)
        except Exception:  # pragma: no cover
            return
        if result is None:
            return
        pattern_id, trigger_class, bucket = result
        if not hasattr(_audit_emit, "emit_cookbook_pattern_advised"):
            return
        # Map semantic -> canonical signature
        bucket_to_count = {"high": 3, "medium": 2, "low": 1}
        try:
            _audit_emit.emit_cookbook_pattern_advised(
                task_signature="other",
                top_pattern_keys=str(pattern_id)[:128],
                pattern_count=bucket_to_count.get(str(bucket), 1),
            )
        except Exception:  # pragma: no cover
            return
    except Exception:  # pragma: no cover - fail-open invariant
        return


# ---------------------------------------------------------------------------
# PLAN-153 Wave E item 7 (ADR-175) — Prompt Defense Baseline gate.  [END]
# ---------------------------------------------------------------------------

def decide(
    *,
    description: str,
    prompt: str,
    names_regex,
    env: Optional[dict] = None,
    subagent_type: str = "",
) -> Decision:
    """Pure decision function — no I/O, trivially unit-testable.

    Args:
        description: The Agent tool's `description` field.
        prompt: The Agent tool's `prompt` field.
        names_regex: A compiled regex matching team member names, or None
            if no team files were found (degrades to header-only detection).
        env: Environment-var dict (defaults to os.environ). Used to read
            CEO_ARCHITECT_ACTIVE for the recursion guard (Sprint 5 ADR-010).
        subagent_type: Agent tool ``subagent_type`` field (PLAN-078 Wave 1
            telemetry). Used to identify archetype for model-routing
            advisory emit; never affects the allow/block decision.

    Returns:
        Decision(allow=True) if the spawn is fine.
        Decision(allow=False, reason=...) if governance requires blocking.
    """
    src_env = env if env is not None else os.environ

    # PLAN-133 E3 — resolve session id once for the spawn-rails (depth/overlap).
    _e3_session_id = _resolve_session_id_from_env(src_env)

    # PLAN-113 WIRE-DEADMOD / ADR-089 SEC-P0-01 — sanitize ## SPEC CONTEXT
    # payload (advisory telemetry; never blocks). Runs early so sentinel
    # violations are logged before any governance decision. Fail-open.
    _sanitize_spec_context_advisory(prompt or "", env=src_env)

    # PLAN-133 A2 (Goose-harvest) — fail-CLOSED invisible-unicode guard.
    # Default-OFF (CEO_UNICODE_HARDBLOCK=1 enforces); when enforced, a spawn
    # prompt carrying control / bidi / zero-width / U+E0000-E007F Tag-block
    # chars is BLOCKED here, BEFORE any LLM/debate/governance review. The
    # breadcrumb (invisible_unicode_blocked) is emitted on both the advisory
    # and enforced paths so the measure-first denominator is real. Fail-open.
    _uni_block = _enforce_spec_context_unicode(prompt or "", env=src_env)
    if _uni_block is not None:
        return Decision(allow=False, reason=_uni_block)

    # Session 75 Codex Finding 4 closure: scan spawn prompt for
    # leaked secrets when Owner-opted-in via CEO_SPAWN_SECRET_SCAN=1.
    # Default OFF; without the env var, _validate_spawn_prompt_has_no_secrets
    # short-circuits to ok=True so legacy spawns are unaffected.
    _scan_ok, _scan_code, _scan_detail = _validate_spawn_prompt_has_no_secrets(prompt)
    if not _scan_ok:
        return Decision(
            allow=False,
            reason=(
                f"SPAWN-SECRET-BLOCKED: {_scan_code} ({_scan_detail}). "
                "To bypass once: unset CEO_SPAWN_SECRET_SCAN."
            ),
        )

    # PLAN-045 Wave 1 P0-03 — VETO floor runtime check.
    # If the spawn targets a VETO-floor role (code-reviewer,
    # security-engineer), verify the agent frontmatter still binds
    # them to Opus. Closes F-01-03 demotion-via-frontmatter attack.
    # Skipped when the validator lib is missing (defense-in-depth
    # fail-open; arbitration kernel still blocks agents/*.md edits).
    if _agent_frontmatter is not None:
        agents_dir = Path(
            src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        ) / ".claude" / "agents"
        haystack_lower = " ".join([
            (description or "").lower(), (prompt or "").lower()
        ])
        for _role in sorted(_agent_frontmatter.VETO_FLOOR_ROLES):
            if _role.lower() not in haystack_lower:
                continue
            ok, reason = _agent_frontmatter.check_veto_floor_for_role(
                _role, agents_dir
            )
            if not ok and reason != "not_veto_role":
                return Decision(
                    allow=False,
                    reason=(
                        f"GOVERNANCE: veto_floor_demoted: role={_role} "
                        f"reason={reason}. The VETO floor requires "
                        "security-engineer and code-reviewer to bind to a "
                        "member of VETO_FLOOR_ALLOWED (agent_frontmatter.py) "
                        "- the enforcement is set membership, not one id. "
                        "See ADR-052 + PLAN-045 Wave 1 P0-03; PLAN-169 W2.10 D2."
                    ),
                )

    # PLAN-078 Wave 1 — model routing advisory telemetry (advisory-only).
    # Runs AFTER VETO-floor enforcement so the hard-block path remains
    # authoritative. Emits `model_routing_advised` event when a spawn
    # archetype is identifiable. NEVER mutates tool_input. NEVER blocks.
    # Bypass: `CEO_MODEL_ROUTING=0`.
    _emit_model_routing_advisory(
        description=description or "",
        prompt=prompt or "",
        subagent_type=subagent_type or "",
        env=src_env,
        project_dir=src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
    )

    # PLAN-112-FOLLOWUP-persona-routing-wire W1 — god-mode matrix consult.
    # Runs AFTER the VETO-floor hard-block (above) so it never masks it.
    # CONSULT + AUDIT ONLY — emits model_routing_enforced /
    # model_routing_eval_error; NEVER blocks (block deferred, see W3 above).
    # Mode is read off authoritative subagent_type only.
    _consult_model_routing_mode(
        description=description or "",
        prompt=prompt or "",
        subagent_type=subagent_type or "",
        env=src_env,
        project_dir=src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
    )

    # PLAN-091 Wave A.4 (W3.1) — MCP routing advisory.
    # Maps archetype → mcp_routing task_class; resolver emits
    # `mcp_route_advised` (PLAN-086 Wave D). Bypass: CEO_MCP_ROUTING_HOOK=0.
    _emit_mcp_routing_advisory(
        description=description or "",
        prompt=prompt or "",
        subagent_type=subagent_type or "",
        env=src_env,
    )

    # PLAN-091 Wave A.5 (W3.3) — specialization promotion heuristic.
    # When general-purpose spawn matches a specialist hint, emit
    # `specialization_promoted` advisory. NEVER auto-spawns.
    # Bypass: CEO_PROMOTION_HEURISTIC=0.
    _emit_promotion_advisory(
        description=description or "",
        prompt=prompt or "",
        subagent_type=subagent_type or "",
        env=src_env,
    )

    # PLAN-092 Wave A.4 (W3.2 SEMI-11) — cookbook-advisor pattern hint.
    # Matches spawn against 4 Anthropic Cookbook patterns (COOK-P1..P4);
    # emits `cookbook_pattern_advised` advisory. Kill-switch:
    # CEO_COOKBOOK_ADVISOR_ENABLED=0. NEVER mutates tool_input.
    _emit_cookbook_pattern_advisory(
        description=description or "",
        prompt=prompt or "",
        env=src_env,
    )

    # PLAN-098 Wave C.2 (ADR-132) — GOAP advisory-only invariant.
    # PLAN-105 Wave A.6 — capture intent for deferred-emit at allow-return.
    _goap_intent_plan_id: Optional[str] = None
    _goap_intent_action_id: Optional[str] = None
    if _GOAP_PLAN_ID_RE.search(prompt or ""):
        owner_confirmed_env = (src_env.get("CEO_GOAP_CONFIRMED") or "").strip() == "1"
        has_goap_confirm_block = bool(_GOAP_CONFIRM_HEADER_RE.search(prompt or ""))
        if not (owner_confirmed_env and has_goap_confirm_block):
            preview = (description or "")[:80]
            missing: List[str] = []
            if not owner_confirmed_env:
                missing.append("CEO_GOAP_CONFIRMED=1 env")
            if not has_goap_confirm_block:
                missing.append("## GOAP CONFIRM block")
            return Decision(
                allow=False,
                reason=(
                    "GOVERNANCE: goap_advisory_without_owner_confirm: "
                    f"spawn references a GOAP plan (description={preview!r}) "
                    f"but lacks: {', '.join(missing)}. The GOAP planner is "
                    "advisory-only - the Owner must physically confirm each "
                    "action before spawn. See ADR-132 Decision Part 2."
                ),
            )
        # PLAN-105 Wave A.6 — GOAP gates passed; record intent for deferred emit.
        _pid_m = _GOAP_PLAN_ID_VALUE_RE.search(prompt or "")
        _aid_m = _GOAP_ACTION_ID_VALUE_RE.search(prompt or "")
        if _pid_m is not None:
            _goap_intent_plan_id = _pid_m.group(1).strip()[:32]
            if _aid_m is not None:
                _goap_intent_action_id = _aid_m.group(1).strip()[:64]

    # Recursion guard (ADR-010): block Architect-spawning-Architect.
    architect_active = (src_env.get("CEO_ARCHITECT_ACTIVE") or "").strip()
    if architect_active == "1":
        haystack = " ".join([description or "", prompt or ""])
        if _ARCHITECT_NAME_RE.search(haystack):
            return Decision(
                allow=False,
                reason=(
                    "ARCHITECT-RECURSION: a spawn naming 'Agent Architect' "
                    "was detected while CEO_ARCHITECT_ACTIVE=1. The Agent "
                    "Architect must not spawn another instance of itself "
                    "within the same session. See ADR-010."
                ),
            )

    # PLAN-020 Phase 3 — /effort scope clause (QA must-fix #7): /effort
    # hints are CEO-only. Spawn prompts MUST NOT include them.
    if _has_effort_token(prompt or ""):
        return Decision(
            allow=False,
            reason=(
                "GOVERNANCE: spawn prompt contains a `/effort` token. "
                "Effort hints are CEO-only — sub-agents inherit Anthropic "
                "default thinking budget. Strip /effort from the prompt "
                "before retrying. See PLAN-020 §4 Phase 3 scope clause."
            ),
        )

    desc_matched_name = False
    if names_regex is not None and description:
        if names_regex.search(description):
            desc_matched_name = True

    prompt_has_persona = False
    if prompt and _PERSONA_HEADER_RE.search(prompt):
        prompt_has_persona = True

    is_named_spawn = desc_matched_name or prompt_has_persona

    # PLAN-133 E3 — per-spawn tool scoping + depth/overlap rails. ADVISORY by
    # default (emit-only, enforced=0); BLOCKS only under the per-rail env flag
    # (CEO_SPAWN_TOOL_SCOPE / CEO_SPAWN_DEPTH_GUARD / CEO_SPAWN_OVERLAP_GUARD).
    # Runs AFTER the VETO-floor + A2 unicode hard-blocks so those remain
    # authoritative; runs BEFORE the SKILL CONTENT accept-path so an
    # out-of-scope / depth-2 / clobbering spawn is rejected even when otherwise
    # well-formed. Fail-open (returns None on any infra error).
    _e3_hit = _enforce_spawn_rails(
        prompt=prompt or "",
        is_named_spawn=is_named_spawn,
        env=src_env,
        session_id=_e3_session_id,
    )
    if _e3_hit is not None:
        _e3_code, _e3_detail = _e3_hit
        return Decision(
            allow=False,
            reason=(
                f"GOVERNANCE: {_e3_code}: {_e3_detail}. "
                "The spawn violates a PLAN-133 E3 rail (per-spawn tool "
                "allow-list / depth-over-one fence / FILE ASSIGNMENT overlap) "
                "or the ADR-191 FILE ASSIGNMENT grammar (PLAN-178 C1). "
                "Fix for a grammar block: regenerate the prompt via "
                ".claude/scripts/inject-agent-context.sh (it always emits "
                "the block). If the block is UNPARSEABLE, REPLACE or "
                "remove the malformed block (the classifier aggregates "
                "ALL blocks — appending a valid one cannot clear an "
                "invalid token's taint); appending `## FILE ASSIGNMENT` "
                "with `- CAN edit: <concrete paths>` or the explicit "
                "read-only form `- CAN edit: NONE-READ-ONLY` works only "
                "for the ABSENT state. Recovery route: "
                "CEO_SOTA_DISABLE=1 forces advisory. See PLAN-133 §E E3 + "
                "ADR-191."
            ),
        )

    # PLAN-113 WIRE-DEADMOD — confidence_labels advisory (PLAN-083 Wave 1.10).
    # Emits spawn_confidence_advisory so recommender / receipt formatter have
    # a hook-level signal. Advisory only — never blocks. Fail-open.
    _action_type = "canonical_edit" if is_named_spawn else "bash_execute"
    _emit_spawn_confidence_advisory(
        action_type=_action_type,
        is_named_spawn=is_named_spawn,
        env=src_env,
    )

    if not is_named_spawn:
        # Generic research / simple tasks — no governance requirement.
        _emit_goap_deferred_outcome(
            _goap_intent_plan_id, _goap_intent_action_id, src_env
        )
        return Decision(allow=True)

    # PLAN-153 Wave E item 7 (ADR-175) — Prompt Defense Baseline gate.
    # NAMED spawns only (scoped here, after the generic early-return, so
    # unmatched/generic spawns see zero behavior change). Runs BEFORE the
    # SKILL REFERENCE / SKILL CONTENT accept-paths so an untrusted-content
    # spawn missing the block is rejected even when otherwise well-formed.
    # Input fail-CLOSED (matched + missing block => BLOCK); infra fail-OPEN
    # inside _enforce_prompt_defense. Kill-switches documented at the gate.
    _pd_hit = _enforce_prompt_defense(
        description=description or "",
        prompt=prompt or "",
        env=src_env,
    )
    if _pd_hit is not None:
        _pd_code, _pd_detail = _pd_hit
        return Decision(
            allow=False,
            reason=(
                f"GOVERNANCE: {_pd_code}: {_pd_detail}. This NAMED spawn's "
                "task indicates contact with untrusted content (WebFetch/"
                "WebSearch/scrape/imported/upstream/third-party), but the "
                "prompt has no `## PROMPT DEFENSE` section with >= 6 bullet "
                "lines. Fix: regenerate the prompt via "
                ".claude/scripts/inject-agent-context.sh (it emits the block "
                "unconditionally), or append the 6-bullet anti-injection "
                "block verbatim. See PLAN-153 Wave E item 7 / ADR-175."
            ),
        )

    # PLAN-020 Phase 2 — Reference path (ADR-051). If `## SKILL REFERENCE`
    # marker is present, validate strictly (fail-CLOSED). Reference path
    # opt-in via env var; default ON per Q1 Owner answer.
    if _is_enabled("CEO_SKILL_REFERENCE_MODE", ENABLE_SKILL_REFERENCE_MODE, src_env):
        if _SKILL_REFERENCE_HEADER_RE.search(prompt or ""):
            ok, reason_code, detail = _validate_skill_reference(prompt or "")
            if ok:
                _emit_goap_deferred_outcome(
                    _goap_intent_plan_id, _goap_intent_action_id, src_env
                )
                # PLAN-106 Wave C — persona coverage emit at allow path.
                _emit_persona_coverage_synthesized(
                    subagent_type=subagent_type,
                    description=description,
                    prompt=prompt,
                    source="dispatch",
                    env=src_env,
                )
                return Decision(allow=True)
            preview = (description or "")[:80]
            return Decision(
                allow=False,
                reason=(
                    f"GOVERNANCE: {reason_code}: {detail}. "
                    f"Spawn rejected (description={preview!r}). "
                    "See ADR-051 §Synchronous validation for sub-check details."
                ),
            )

    # Named spawn: require real SKILL CONTENT section (P1-SEC-B: bypass-resistant).
    if _has_skill_content(prompt or ""):
        _emit_goap_deferred_outcome(
            _goap_intent_plan_id, _goap_intent_action_id, src_env
        )
        # PLAN-106 Wave C — persona coverage emit at allow path.
        _emit_persona_coverage_synthesized(
            subagent_type=subagent_type,
            description=description,
            prompt=prompt,
            source="dispatch",
            env=src_env,
        )
        return Decision(allow=True)

    # Build a helpful block reason pointing at the injector script.
    preview = (description or "")[:80]
    reason = (
        "GOVERNANCE: Agent spawn detected as NAMED "
        f"(description='{preview}'), but prompt has no {_SKILL_CONTENT_MARKER} "
        "section. Read the agent's skill file and include its full content "
        "in the prompt before spawning. Use "
        ".claude/scripts/inject-agent-context.sh <AgentName> <task> to "
        "generate a compliant prompt."
    )
    return Decision(allow=False, reason=reason)


_load_spawn_part("outcome_telemetry")

def _classify_block_reason(reason: str) -> str:
    """Map a Decision.reason string to a stable audit reason_code.

    Defaults to ``unknown_block`` when no marker matches — visibility
    on a marker drift is preferable to silent misclassification.
    """
    if not reason:
        return "unknown_block"
    for needle, code in _BLOCK_REASON_MARKERS:
        if needle in reason:
            if code == "__REFERENCE_PREFIX__":
                # Embedded reason_code form: "GOVERNANCE: <code>: <detail>".
                # Skill-reference path emits codes like reference_hash_mismatch,
                # reference_unsafe_path, etc. (constants at
                # check_agent_spawn.py:188 REASON_REFERENCE_*).
                head = reason[len("GOVERNANCE: "):]
                colon = head.find(":")
                return head[:colon] if colon > 0 else "reference_invalid"
            return code
    return "unknown_block"

def _to_contract_decision(d: "Decision") -> _contract.Decision:
    if d.allow:
        return _contract.allow()
    return _contract.block(d.reason or "")


_load_spawn_part("entrypoint")


# PLAN-106 Wave G.1 — public re-export. Coordinator callers use:
#     from check_agent_spawn import aggregate_subagent_findings
# which proxies to `_lib.subagent_dispatch.aggregate_findings`. Doing
# the re-export at this module level satisfies the grep contract AC10
# ("emit_subagent_findings_partial_drop ≥1 hit outside _lib/audit_emit
# and tests/") because the helper transitively names the emit symbol
# in its docstring + raises the call site to the hook module surface.
def aggregate_subagent_findings(*args, **kwargs):
    """Wrap `_lib.subagent_dispatch.aggregate_findings`.

    Emits `emit_subagent_findings_partial_drop` on shortfall via the
    inner aggregator. See `_lib/subagent_dispatch.py` for the full
    contract. Re-exported here so future coordinator code can call
    `from check_agent_spawn import aggregate_subagent_findings` and the
    grep contract (AC10) finds a hit at the hook-module surface
    without dragging the dispatch logic into this 1700-LoC file.
    """
    return _subagent_dispatch.aggregate_findings(*args, **kwargs)


# Keep every extracted function on the historical module's globals so callers
# can patch its seams and each import retains independent invocation state.
_SPAWN_COMPONENT_IMPORT_ERROR = None
try:
    # Surface guard: .claude/skills/** and SKILL.md (via _lib/agent_spawn/skill_reference.py)
    from _lib.agent_spawn import bind as _bind_spawn_components
    _bind_spawn_components(globals())
    del _bind_spawn_components
except Exception as _spawn_component_exc:
    _SPAWN_COMPONENT_IMPORT_ERROR = type(_spawn_component_exc).__name__


if __name__ == "__main__":
    sys.exit(main())
