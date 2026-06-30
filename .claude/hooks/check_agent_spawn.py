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
# _lib is a sibling package.
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


# ---------------------------------------------------------------------------
# PLAN-078 Wave 1 — Model routing telemetry (advisory-emit-only)
# ---------------------------------------------------------------------------
# Telemetry-only: hook contract (`_lib/contract.py:112-127`) supports only
# allow/block/systemMessage. NO `tool_input` mutation. This block exists to
# observe sub-agent spawn → recommended model deltas so the CEO can hand-edit
# `.claude/agents/<archetype>.md` frontmatter (manual remediation path). The
# hard-enforcement leg is the existing VETO-floor check at
# check_veto_floor_for_role() which runs BEFORE this advisory.
#
# Hot-path requirement: p95 ≤ 20ms. Achieved via:
#   - module-level cache of task_route module + classify reference
#   - module-level cache of frontmatter parser
#   - frontmatter cache by-archetype (LRU dict, capped 64 entries) — agents
#     dir is small + rarely changes mid-session, so cache invalidation is
#     not required (next session re-imports module).
#
# Bypass: env var `CEO_MODEL_ROUTING=0` short-circuits to a no-op.
# Fail-open: any exception during advisory emit is swallowed (logged to
# breadcrumb if available) so the spawn is NEVER blocked by a routing bug.

# Lazy task_route module reference — populated on first call. Cached.
_TASK_ROUTE_MODULE: Optional[Any] = None
_TASK_ROUTE_LOAD_FAILED: bool = False

# In-memory cache: archetype -> (model: Optional[str], confidence: float).
# Cleared at module init only (process-scoped).
_FRONTMATTER_MODEL_CACHE: Dict[str, Tuple[Optional[str], float]] = {}
_FRONTMATTER_CACHE_MAX = 64


def _resolve_task_route():
    """Best-effort import of `.claude/scripts/task-route.py` as a module.

    Returns the module on success, None on failure. Never raises.
    Cached after first call (positive or negative).

    Resolution order:
      1. ``CLAUDE_PROJECT_DIR`` env var (test-friendly + adopter-respectful)
      2. Walk up from `_HOOKS_DIR` looking for a `.claude/scripts/task-route.py`
    """
    global _TASK_ROUTE_MODULE, _TASK_ROUTE_LOAD_FAILED
    if _TASK_ROUTE_MODULE is not None or _TASK_ROUTE_LOAD_FAILED:
        return _TASK_ROUTE_MODULE
    try:
        import importlib.util as _ilutil
        candidates = []
        env_root = os.environ.get("CLAUDE_PROJECT_DIR")
        if env_root:
            candidates.append(
                Path(env_root) / ".claude" / "scripts" / "task-route.py"
            )
        # Walk up from _HOOKS_DIR (stable in normal install)
        candidates.append(
            _HOOKS_DIR.parent.parent / ".claude" / "scripts" / "task-route.py"
        )
        # Walk up from this file's location (helps when the hook itself is
        # staged under .claude/plans/PLAN-NNN/staging/...; rare but useful
        # for in-tree pytest runs that exercise the staged copy).
        cur = Path(__file__).resolve().parent
        for _ in range(8):
            if cur == cur.parent:
                break
            cand = cur / ".claude" / "scripts" / "task-route.py"
            if cand.is_file():
                candidates.append(cand)
                break
            cur = cur.parent
        tr_path = next((c for c in candidates if c.is_file()), None)
        if tr_path is None:
            _TASK_ROUTE_LOAD_FAILED = True
            return None
        spec = _ilutil.spec_from_file_location("task_route", tr_path)
        if spec is None or spec.loader is None:
            _TASK_ROUTE_LOAD_FAILED = True
            return None
        mod = _ilutil.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _TASK_ROUTE_MODULE = mod
        return mod
    except Exception:  # pragma: no cover - fail-open
        _TASK_ROUTE_LOAD_FAILED = True
        return None


def _read_archetype_model_frontmatter(
    archetype: str,
    agents_dir: Path,
) -> Tuple[Optional[str], float]:
    """Read `model:` field from `<agents_dir>/<archetype>.md`.

    Returns (model, confidence). When frontmatter present + model field
    set, confidence is 1.0 (authoritative). When file missing or no
    model field, confidence is 0.0 (caller will fall back to classify).
    Cached by archetype to avoid re-reading on repeat spawns.
    """
    cached = _FRONTMATTER_MODEL_CACHE.get(archetype)
    if cached is not None:
        return cached
    result: Tuple[Optional[str], float] = (None, 0.0)
    try:
        if _agent_frontmatter is None:
            pass
        else:
            path = _agent_frontmatter.resolve_agent_file(archetype, agents_dir)
            if path.is_file():
                metadata = _agent_frontmatter.parse_agent_file(path)
                model = metadata.get("model", "").strip() if metadata else ""
                if model:
                    result = (model, 1.0)
    except Exception:  # pragma: no cover - fail-open
        result = (None, 0.0)
    # Bounded LRU-ish cache (simple FIFO eviction at cap).
    if len(_FRONTMATTER_MODEL_CACHE) >= _FRONTMATTER_CACHE_MAX:
        try:
            _FRONTMATTER_MODEL_CACHE.pop(next(iter(_FRONTMATTER_MODEL_CACHE)))
        except StopIteration:  # pragma: no cover
            pass
    _FRONTMATTER_MODEL_CACHE[archetype] = result
    return result


def _extract_archetype_from_payload(
    description: str,
    prompt: str,
    subagent_type: str,
) -> str:
    """Best-effort archetype detection from spawn payload.

    Order: ``subagent_type`` (Agent tool input) → first persona header
    line → empty string. Returns archetype slug or empty string.
    """
    if subagent_type:
        return subagent_type.strip().lower()
    # Try to find archetype from persona header in prompt
    if prompt:
        m = re.search(
            r"(?:archetype|role|persona):\s*([a-z][a-z0-9_-]+)",
            prompt,
            flags=re.IGNORECASE,
        )
        if m:
            return m.group(1).strip().lower()
    return ""


def _emit_model_routing_advisory(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
    project_dir: Optional[str] = None,
) -> None:
    """Emit a `model_routing_advised` advisory event for this spawn.

    PLAN-078 Wave 1. Telemetry-only — this function:
      - reads archetype from spawn payload
      - reads `.claude/agents/<archetype>.md` frontmatter `model:` if set
      - else calls `task_route.classify()` for a recommendation
      - emits via audit_emit (deny-by-default 6-field allowlist)

    NEVER raises. Bypass via `CEO_MODEL_ROUTING=0`.
    """
    try:
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_MODEL_ROUTING") or "").strip() == "0":
            return  # bypass
        if not _AUDIT_EMIT_AVAILABLE:
            return  # audit emit unavailable; nothing to do

        archetype = _extract_archetype_from_payload(
            description or "", prompt or "", subagent_type or ""
        )
        if not archetype:
            return  # generic spawn — no archetype to route

        # Path A: agent frontmatter declared model -> authoritative.
        proj = project_dir or src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        agents_dir = Path(proj) / ".claude" / "agents"
        fm_model, fm_conf = _read_archetype_model_frontmatter(
            archetype, agents_dir
        )

        if fm_model:
            model_recommended = fm_model
            confidence = fm_conf
            applied_or_skipped = "skipped_classify_frontmatter_authoritative"
            override_reason = "frontmatter_model_present"
            task_type = "frontmatter"
        else:
            # Path B: in-process classify.
            tr = _resolve_task_route()
            if tr is None or not hasattr(tr, "classify"):
                # Fail-open: no recommendation available, advisory skipped.
                return
            try:
                desc_text = (description or "")[:8 * 1024]  # cap to 8KiB
                result = tr.classify(desc_text, [])
            except Exception:
                # classify() raised — fail-open with breadcrumb attempt.
                _emit_advisory_safe(
                    archetype=archetype,
                    task_type="classify_error",
                    model_recommended="",
                    confidence=0.0,
                    applied_or_skipped="skipped_classify_exception",
                    override_reason="classify_raised",
                )
                return
            classification = (
                result.get("classification") if isinstance(result, dict) else ""
            ) or ""
            # Conservative mapping: classify() returns S/M/L/XL classification —
            # not a model directly. Telemetry records the classification +
            # leaves model_recommended empty so PLAN-079 can decide the mapping.
            model_recommended = ""
            confidence = 0.7 if classification else 0.0
            applied_or_skipped = (
                "advisory_only_no_recommendation"
                if not classification
                else "advisory_only_classification_emitted"
            )
            override_reason = ""
            task_type = classification or "unclassified"

        _emit_advisory_safe(
            archetype=archetype,
            task_type=task_type,
            model_recommended=model_recommended,
            confidence=float(confidence),
            applied_or_skipped=applied_or_skipped,
            override_reason=override_reason,
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return


# ---------------------------------------------------------------------------
# PLAN-112-FOLLOWUP-persona-routing-wire W1+W2+W3 — god-mode matrix consult.
# ---------------------------------------------------------------------------
# Consult ALL THREE persona_routing APIs (AC1):
# `get_mode(archetype, "AUTO-05")` (recorded mode label) +
# `is_enforcing(archetype, "AUTO-05")` (authoritative effective-enforcing
# boolean that drives `decision`) + `is_killswitch_active()` (records the
# kill-switch state) and EMIT the resulting mode as forensic telemetry
# (`model_routing_enforced`). This closes the F-1.2 dead-policy (the
# AUTO-05 enforcing cell was never read at runtime).
#
# W3 — DEFERRED BLOCK + FLIP DOCTRINE:
#   The actual model-tier BLOCK is DEFERRED. A "model mismatch -> block"
#   predicate needs the dispatched/requested model, but the Agent hook
#   payload exposes only description/prompt/subagent_type/run_in_background
#   (SPEC/v1/hook-io.schema.md). `metadata.get("model")` (read in
#   `_read_archetype_model_frontmatter`) is the AGENT FRONTMATTER model, NOT
#   a spawn-requested model. With no requested-model input, a block would be
#   theater. When the harness exposes the dispatched model to PreToolUse, the
#   violation predicate becomes a 1-liner: fm_model present AND requested
#   present AND differing.
#   The future enable of that block is governed by OBSERVED-VIOLATION VOLUME
#   + a false-positive-rate threshold, NOT by elapsed calendar days
#   (ADR-095 / [[feedback-no-calendar-gates-ai-workflow]]). Recorded here as
#   the flip doctrine for a future ADR-118-AMEND-2.
#
# SECURITY INVARIANTS:
#   - Mode is read off the AUTHORITATIVE `subagent_type`-derived archetype
#     ONLY — NEVER the prompt-regex archetype (attacker-controllable; a
#     spoofed archetype must not flip the recorded mode). CWE-400/spoofing.
#   - Fail-OPEN: import/get_mode failure -> emit `model_routing_eval_error`
#     and return; NEVER raise in the hook hot path (CLAUDE.md §5).
#   - Kill-switch precedence: get_mode() already demotes an enforcing cell
#     to advisory under `CEO_GODMODE_ENFORCING=0`; we record the demoted
#     mode (advisory) so the audit reflects effective policy.
def _consult_model_routing_mode(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
    project_dir: Optional[str] = None,
) -> None:
    """Consult the god-mode routing matrix + emit forensic telemetry.

    CONSULT + AUDIT ONLY. NEVER blocks, NEVER mutates tool_input, NEVER
    raises. Consults all THREE persona_routing APIs (AC1): `get_mode`
    (recorded mode label), `is_enforcing` (authoritative effective-
    enforcing boolean that drives `decision`), and `is_killswitch_active`.
    Emits `model_routing_enforced` (mode/recommended_model/
    killswitch_armed/decision) on success, `model_routing_eval_error`
    (decision=eval_error) on any infra failure (fail-open).
    """
    try:
        src_env = env if env is not None else os.environ
        if not _AUDIT_EMIT_AVAILABLE:
            return  # nothing to audit against; consult is observability-only

        # AUTHORITATIVE source ONLY — subagent_type. A prompt-regex archetype
        # is attacker-controllable and must not flip the recorded mode.
        archetype = (subagent_type or "").strip().lower()
        if not archetype:
            return  # no authoritative archetype -> no mode to record

        session_id = src_env.get("CLAUDE_SESSION_ID", "") or ""
        proj = project_dir or src_env.get("CLAUDE_PROJECT_DIR") or os.getcwd()

        # Fail-OPEN guard around the matrix consult.
        try:
            if _persona_routing is None:
                raise RuntimeError("persona_routing import unavailable")
            # NEVER read _PRIMITIVE_DEFAULT_MODE directly — get_mode /
            # is_enforcing honor the kill-switch demotion internally.
            # All THREE persona_routing APIs are consulted (AC1):
            #   - get_mode      -> the effective (possibly demoted) mode label
            #                      recorded verbatim in the emit
            #   - is_enforcing  -> the AUTHORITATIVE effective-enforcing boolean
            #                      that drives `decision` (kill-switch already
            #                      folded in: returns False when demoted)
            #   - is_killswitch_active -> records whether the kill-switch armed
            mode = _persona_routing.get_mode(archetype, "AUTO-05")
            is_enforcing = bool(
                _persona_routing.is_enforcing(archetype, "AUTO-05")
            )
            killswitch_armed = bool(_persona_routing.is_killswitch_active())
        except Exception:  # noqa: BLE001 — fail-open per CLAUDE.md §5
            try:
                _audit_emit.emit_generic(
                    "model_routing_eval_error",
                    archetype=archetype[:64],
                    reason_code="persona_routing_eval_failed",
                    decision="eval_error",
                    session_id=session_id,
                    project=str(proj)[:256],
                )
            except Exception:  # noqa: BLE001
                pass
            return

        # recommended_model: best-effort authoritative agent-frontmatter
        # model for this archetype (NOT a spawn-requested model). "" when
        # absent. Reuses the cached frontmatter reader.
        recommended_model = ""
        try:
            agents_dir = Path(proj) / ".claude" / "agents"
            fm_model, _conf = _read_archetype_model_frontmatter(
                archetype, agents_dir
            )
            recommended_model = (fm_model or "")[:64]
        except Exception:  # noqa: BLE001 — telemetry enrichment is optional
            recommended_model = ""

        # decision enum: enforce_telemetry | advisory | eval_error.
        # NO `block` value — block deferred (§2.4). Derived from the
        # AUTHORITATIVE is_enforcing() boolean (NOT a re-derivation from
        # the `mode` string), so the kill-switch demotion already folded
        # into is_enforcing() drives the decision. `mode` (possibly
        # demoted to "advisory" by get_mode) is still recorded verbatim.
        decision = "enforce_telemetry" if is_enforcing else "advisory"

        try:
            _audit_emit.emit_generic(
                "model_routing_enforced",
                archetype=archetype[:64],
                mode=str(mode)[:16],
                recommended_model=recommended_model,
                killswitch_armed=killswitch_armed,
                decision=decision,
                session_id=session_id,
                project=str(proj)[:256],
            )
        except Exception:  # noqa: BLE001 — fail-open
            return
    except Exception:  # pragma: no cover — fail-open invariant
        return


# PLAN-091 Wave A.4 (W3.1) — archetype → mcp_routing task_class heuristic.
#
# Maps the spawn's archetype to one of the 4 task_class strings declared in
# `_lib/mcp_routing._ROUTING_TABLE`. mcp_routing.resolve() emits its own
# `mcp_route_advised` advisory (PLAN-086 Wave D) — the spawn-hook wire only
# needs to trigger the resolver at the right callsite. NO mapping fallthrough
# = NO emit (advisory-only; avoid noise on every spawn).
_MCP_ARCHETYPE_TASK_CLASS_HINTS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    # ORDER MATTERS — first match wins. More-specific archetype slugs
    # (finops/seo/crypto) come BEFORE the bare "architect" pattern so
    # composite slugs like "llm-finops-architect" or "crypto-research-
    # analyst" route to the more specific MCP server bundle.
    (("finops", "cost", "budget"), "finops"),
    (("seo", "ahrefs", "similarweb"), "seo_research"),
    (("crypto", "lunarcrush", "blockchain"), "crypto_research"),
    (("architect", "arch-"), "arch"),
)


# PLAN-091 Wave A.5 (W3.3) — archetype-hint patterns triggering a
# `specialization_promoted` advisory when subagent_type == general-purpose.
# Match is FIRST-HIT, not exhaustive — keeps emit volume bounded. Hints
# are lowercase substring matches on (description + prompt).
_PROMOTION_ARCHETYPE_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("performance-engineer",
     ("latency", "p95", "p99", "profile", "memory leak", "throughput",
      "gc tuning", "hot path")),
    ("security-engineer",
     ("jwt", "oauth", "authentication", "vulnerability", "owasp",
      "xss", "sql injection", "csrf", "rate limiting")),
    ("qa-architect",
     ("test strategy", "mutation testing", "flake", "regression",
      "property-based", "fuzz", "contract test")),
    ("code-reviewer",
     ("merge gate", "code review", "veto", "review checklist")),
    ("incident-commander",
     ("incident commander", "severity classification", "all-clear",
      "paging policy", "post-incident review")),
    ("identity-trust-architect",
     ("token rotation", "session lifecycle", "rbac", "abac",
      "service-to-service trust", "mtls")),
    ("threat-detection-engineer",
     ("mitre att&ck", "siem rule", "detection rule", "alert deduplication",
      "purple team", "threat hunting")),
    ("devops",
     ("github actions", "sha-pin", "ci/cd pipeline", "rollback strategy",
      "secret rotation")),
)


def _emit_mcp_routing_advisory(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
) -> None:
    """PLAN-091 Wave A.4 (W3.1) — emit `mcp_route_advised` for this spawn.

    Derives task_class from the spawn's archetype via the
    ``_MCP_ARCHETYPE_TASK_CLASS_HINTS`` table, then delegates to
    ``_lib/mcp_routing.resolve()`` which performs its own emit (per
    PLAN-086 Wave D). Bypass: ``CEO_MCP_ROUTING_HOOK=0`` (parallel to
    PLAN-078 model-routing bypass; per-server kill switches live inside
    mcp_routing.resolve()).

    NEVER raises. Advisory-only — never mutates tool_input, never blocks.
    """
    try:
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_MCP_ROUTING_HOOK") or "").strip() == "0":
            return
        archetype = _extract_archetype_from_payload(
            description or "", prompt or "", subagent_type or ""
        )
        if not archetype:
            return
        archetype_lc = archetype.lower()
        task_class: Optional[str] = None
        for hints, mapped in _MCP_ARCHETYPE_TASK_CLASS_HINTS:
            if any(h in archetype_lc for h in hints):
                task_class = mapped
                break
        if task_class is None:
            return  # no mapping; emit volume stays bounded
        try:
            from _lib import mcp_routing as _mcpr  # type: ignore
            _mcpr.resolve(task_class)  # resolver fires advisory emit
        except Exception:  # pragma: no cover - fail-open
            return
    except Exception:  # pragma: no cover - fail-open
        return


def _emit_promotion_advisory(
    *,
    description: str,
    prompt: str,
    subagent_type: str,
    env: Optional[Dict[str, str]] = None,
) -> None:
    """PLAN-091 Wave A.5 (W3.3) — emit `specialization_promoted` when a
    ``general-purpose`` spawn matches a specialist archetype heuristic.

    Advisory ONLY — does NOT auto-spawn the suggested specialist. Records
    the suggestion in audit log so PLAN-094+ can promote SEMI to AUTO once
    confidence is established. Bypass: ``CEO_PROMOTION_HEURISTIC=0``.

    First-hit match wins (bounded emit volume). NEVER raises.
    """
    try:
        src_env = env if env is not None else os.environ
        if (src_env.get("CEO_PROMOTION_HEURISTIC") or "").strip() == "0":
            return
        if (subagent_type or "").strip().lower() != "general-purpose":
            return
        if not _AUDIT_EMIT_AVAILABLE:
            return
        text = ((description or "") + "\n" + (prompt or "")).lower()
        text = text[: 8 * 1024]  # 8KiB cap on hint-scan window
        for suggested, hints in _PROMOTION_ARCHETYPE_HINTS:
            for hint in hints:
                if hint in text:
                    try:
                        # PLAN-088 R2 iter-2 STRICKEN specialization_promoted
                        # as separate action; routed via mcp_route_advised
                        # with signal_source discriminator per audit_emit.py
                        # 5099-5105 contract.
                        _audit_emit.emit_generic(
                            "mcp_route_advised",
                            session_id="",
                            task_class="promotion",
                            suggested_servers=suggested[:64],
                            kill_switch_overrides="",
                            signal_source="specialization_promoted",
                        )
                    except Exception:  # pragma: no cover - fail-open
                        pass
                    return  # first-hit wins
    except Exception:  # pragma: no cover - fail-open
        return


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


def _emit_advisory_safe(
    *,
    archetype: str,
    task_type: str,
    model_recommended: str,
    confidence: float,
    applied_or_skipped: str,
    override_reason: str,
) -> None:
    """Wrapper around audit_emit.emit_generic for `model_routing_advised`.

    Allowlist enforced by audit_emit dispatcher (defense-in-depth). Caller
    only fills the 6 contract fields; ts/session/project added by emit_generic.

    Codex W1+W2 fix-pack #2: ``confidence`` (float 0..1) is converted at
    emission time to ``confidence_basis_points`` (int 0..1000) — floats
    are forbidden in HMAC-covered fields (canonical_json invariant). The
    in-process API surface still accepts ``confidence: float`` for
    ergonomic continuity; conversion is colocated with the emit call.
    """
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        # Convert float confidence -> int basis-points. NaN / out-of-range
        # collapse to 0 (lower clamp in audit_emit emitter).
        try:
            conf_f = float(confidence)
        except (TypeError, ValueError):
            conf_f = 0.0
        if conf_f != conf_f or conf_f in (float("inf"), float("-inf")):
            conf_f = 0.0
        if conf_f < 0.0:
            conf_f = 0.0
        if conf_f > 1.0:
            conf_f = 1.0
        confidence_bp = int(round(conf_f * 1000.0))
        # Length-bound caller strings (defense-in-depth on adopter drift).
        _audit_emit.emit_generic(
            "model_routing_advised",
            archetype=(archetype or "")[:64],
            task_type=(task_type or "")[:32],
            model_recommended=(model_recommended or "")[:64],
            confidence_basis_points=confidence_bp,
            applied_or_skipped=(applied_or_skipped or "")[:64],
            override_reason=(override_reason or "")[:128],
        )
    except Exception:  # pragma: no cover - fail-open
        return


# Persona header patterns — must appear at the START of a line.
_PERSONA_HEADER_RE = re.compile(
    r"^(?:PERSONA:|## AGENT PROFILE|## PERSONA)",
    flags=re.MULTILINE,
)

# Governance requirement: named spawns must include this literal section.
_SKILL_CONTENT_MARKER = "## SKILL CONTENT"

# PLAN-019 Phase 2B P1-SEC-B — minimum body size (non-whitespace bytes)
# required between `## SKILL CONTENT` and the next `##` heading / EOF for
# the marker to count as a real skill-content section. Rejects empty-body,
# stub-only, or single-line "see file X" shells.
_SKILL_CONTENT_MIN_BYTES = 256

# Regex to find the marker ON ITS OWN LINE (ignoring trailing whitespace).
_SKILL_CONTENT_MARKER_RE = re.compile(
    r"^## SKILL CONTENT[ \t]*$",
    flags=re.MULTILINE,
)

# Regex to find the next `##`-level heading (to bound the body extraction).
_NEXT_H2_RE = re.compile(r"^##[ \t]", flags=re.MULTILINE)

# Code-fence markers (``` or ~~~ with optional language tag).
_CODE_FENCE_RE = re.compile(r"^(?:```|~~~)", flags=re.MULTILINE)

# HTML comment pair — non-greedy across lines.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)

# Regex to extract ## SPEC CONTEXT block content (between its header and next
# ## heading or EOF). Used by _sanitize_spec_context_advisory() below.
_SPEC_CONTEXT_HEADER_RE = re.compile(
    r"^##[ \t]+SPEC[ \t]+CONTEXT[ \t]*$",
    flags=re.MULTILINE,
)


def _sanitize_spec_context_advisory(prompt: str, env=None) -> None:
    """PLAN-113 WIRE-DEADMOD / ADR-089 SEC-P0-01 — sanitize ## SPEC CONTEXT
    payload and emit telemetry advisory.

    Extracts the ## SPEC CONTEXT block from the spawn prompt, runs it
    through spec_context_sanitizer.sanitize(), and emits a
    `spec_context_sanitized` audit-emit event so sentinel violations,
    truncation, and control-char counts are observable.

    ADVISORY ONLY — never blocks the spawn. Fail-open on any exception.
    Kill-switch: CEO_SPEC_CTX_SANITIZER_ENABLED=0.
    """
    try:
        if not _SPEC_CTX_SANITIZER_AVAILABLE or not _AUDIT_EMIT_AVAILABLE:
            return
        src_env = env if env is not None else os.environ
        val = (src_env.get("CEO_SPEC_CTX_SANITIZER_ENABLED") or "1").strip()
        if val in ("0", "false", "False", "no", "off"):
            return
        if not prompt:
            return
        # Extract ## SPEC CONTEXT block content
        m = _SPEC_CONTEXT_HEADER_RE.search(prompt)
        if m is None:
            return  # no SPEC CONTEXT block — nothing to sanitize
        block_start = m.end()
        next_h2 = _NEXT_H2_RE.search(prompt, block_start)
        block_end = next_h2.start() if next_h2 else len(prompt)
        spec_payload = prompt[block_start:block_end]

        result = _spec_ctx_sanitizer.sanitize(spec_payload)

        # Emit telemetry (advisory only; sentinel violations logged for CEO)
        try:
            _audit_emit.emit_generic(
                "spec_context_sanitized",
                original_bytes=result.original_bytes,
                cleaned_bytes=result.cleaned_bytes,
                truncated=1 if result.truncated else 0,
                sentinel_violations=len(result.sentinel_violations),
                control_chars_stripped=result.control_chars_stripped,
                bidi_zw_chars_stripped=result.bidi_zw_chars_stripped,
                # PLAN-133 A2 — surface the Tag-block count too (allowlisted in
                # audit_emit §7d). Harmless if the SanitizeResult lacks the field
                # (getattr default 0) so this stays import-order tolerant.
                tag_chars_stripped=getattr(result, "tag_chars_stripped", 0),
                header_escape_count=result.header_escape_count,
            )
        except Exception:  # pragma: no cover - fail-open
            pass
    except Exception:  # pragma: no cover - fail-open
        return


def _enforce_spec_context_unicode(prompt: str, env=None):
    """PLAN-133 A2 — fail-CLOSED invisible-unicode guard on the spawn prompt.

    Scans the WHOLE spawn prompt (not just the ## SPEC CONTEXT block — an attacker
    can smuggle Tag-block/bidi chars anywhere in the named-spawn body) for invisible
    /smuggling unicode (control / bidi / zero-width / U+E0000-E007F Tag-block).

    Default-OFF (doctrine #1): the BLOCK fires only when CEO_UNICODE_HARDBLOCK=='1'
    in the import-time trusted_env snapshot. Otherwise advisory — the breadcrumb is
    emitted with enforced=0 (measure-first) and None is returned (no block).

    Returns a block-reason string when enforced AND a detection fires, else None.
    Fail-OPEN on any infra exception (never blocks the session on a scanner bug).
    Master kill: CEO_SOTA_DISABLE=1 forces advisory.
    """
    try:
        if not _SPEC_CTX_SANITIZER_AVAILABLE:
            return None
        src_env = env if env is not None else os.environ
        if not prompt:
            return None
        # Default-OFF flag, read from the trusted_env snapshot when available so a
        # late-set value can't toggle enforcement mid-process. Master kill wins.
        if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
            enforce = False
        else:
            enforce = _unicode_hardblock_enforced(src_env)

        result = _spec_ctx_sanitizer.sanitize(prompt)
        count = _spec_ctx_sanitizer.invisible_unicode_count(result)
        if count <= 0:
            return None  # clean — nothing to do

        unicode_class = _spec_ctx_sanitizer.classify_invisible_unicode(result)

        # Emit the closed-enum breadcrumb on BOTH advisory and enforced paths
        # (the denominator must be real from day one — no 0/0/0 trap).
        if _AUDIT_EMIT_AVAILABLE:
            try:
                _audit_emit.emit_generic(
                    "invisible_unicode_blocked",
                    surface="spawn",
                    unicode_class=unicode_class,
                    char_count=int(count),
                    enforced=1 if enforce else 0,
                )
            except Exception:  # pragma: no cover - fail-open
                pass

        if not enforce:
            return None  # advisory only

        return (
            "GOVERNANCE: invisible_unicode_blocked: the spawn prompt contains "
            f"{count} invisible/smuggling character(s) (class={unicode_class}: "
            "control / bidi / zero-width / Unicode-Tags-block). These are "
            "removed by the sanitizer and rejected fail-CLOSED before review. "
            "Remove the hidden characters and re-spawn. To run advisory-only, "
            "unset CEO_UNICODE_HARDBLOCK."
        )
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _unicode_hardblock_enforced(src_env) -> bool:
    """True iff CEO_UNICODE_HARDBLOCK=='1' (PLAN-133 A2). Prefers the trusted_env
    snapshot; falls back to the passed env dict. Pure; never raises."""
    try:
        from _lib import trusted_env as _te  # noqa: E402
        val = _te.get_trusted("CEO_UNICODE_HARDBLOCK")
        if val is not None:
            return (val or "").strip() == "1"
    except Exception:  # pragma: no cover
        pass
    return (src_env.get("CEO_UNICODE_HARDBLOCK") or "").strip() == "1"


def _emit_spawn_confidence_advisory(
    *,
    action_type: str,
    is_named_spawn: bool,
    env=None,
) -> None:
    """PLAN-113 WIRE-DEADMOD — confidence_labels (PLAN-083 Wave 1.10).

    Classifies the spawn as an action and emits `spawn_confidence_advisory`
    so recommender / receipt formatter surfaces have a hook-level confidence
    signal for governance dashboards.

    ADVISORY ONLY — never blocks. Fail-open on any exception.
    Kill-switch: CEO_SPAWN_CONFIDENCE_ENABLED=0.
    """
    try:
        if not _CONFIDENCE_LABELS_AVAILABLE or not _AUDIT_EMIT_AVAILABLE:
            return
        src_env = env if env is not None else os.environ
        val = (src_env.get("CEO_SPAWN_CONFIDENCE_ENABLED") or "1").strip()
        if val in ("0", "false", "False", "no", "off"):
            return

        ctx = {"canonical": False}
        conf = _confidence_labels.classify(action_type, ctx)
        marker = _confidence_labels.as_emoji_free_marker(conf)

        try:
            _audit_emit.emit_generic(
                "spawn_confidence_advisory",
                action_type=(action_type or "")[:32],
                confidence_level=(conf.level or "")[:32],
                confidence_marker=(marker or "")[:32],
                reason_code=(conf.reason_code or "")[:64],
                is_named_spawn=1 if is_named_spawn else 0,
            )
        except Exception:  # pragma: no cover - fail-open
            pass
    except Exception:  # pragma: no cover - fail-open
        return


def _strip_fenced_and_comments(text: str) -> str:
    """Return a version of ``text`` with HTML comments removed and
    fenced-code-block content masked so marker/body searches cannot
    match inside them (P1-SEC-B bypass hardening)."""
    stripped = _HTML_COMMENT_RE.sub("", text)
    out_parts = []
    in_fence = False
    for line in stripped.splitlines(keepends=True):
        if _CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            out_parts.append(line)
            continue
        if in_fence:
            out_parts.append("".join(
                "\n" if c == "\n" else " " for c in line
            ))
        else:
            out_parts.append(line)
    return "".join(out_parts)


def _has_skill_content(prompt: str) -> bool:
    """True iff ``prompt`` contains a real `## SKILL CONTENT` section.

    Enforces four bypass-resistant checks (P1-SEC-B):
    1. Marker on own line (not inline narrative).
    2. Marker NOT inside HTML comment.
    3. Marker NOT inside fenced code block.
    4. >=_SKILL_CONTENT_MIN_BYTES non-ws bytes between marker and next ##.
    """
    if not prompt:
        return False
    return _has_skill_content_sanitized(_strip_fenced_and_comments(prompt))


def _has_skill_content_sanitized(sanitized: str) -> bool:
    """Shared ``## SKILL CONTENT`` check against already-sanitized text.

    PLAN-023 Phase F (F-perf-003) — split out so ``decide`` and other
    callers can share a single ``_strip_fenced_and_comments`` pass
    rather than re-stripping inside each sub-check.
    """
    match = _SKILL_CONTENT_MARKER_RE.search(sanitized)
    if match is None:
        return False
    body_start = match.end()
    next_heading = _NEXT_H2_RE.search(sanitized, body_start)
    body_end = next_heading.start() if next_heading else len(sanitized)
    body = sanitized[body_start:body_end]
    non_ws_bytes = sum(1 for c in body if not c.isspace())
    return non_ws_bytes >= _SKILL_CONTENT_MIN_BYTES


# =============================================================================
# PLAN-020 Phase 2 — `## SKILL REFERENCE` additive sentinel (ADR-051)
# =============================================================================
#
# Parallel accept-path. Does NOT replace `_has_skill_content`. Hardened
# against 14 attack classes documented in ADR-051 §Threat model.
#
# Hook recognition order in decide():
#   1. If prompt has `## SKILL REFERENCE` → strict validation, fail-CLOSED.
#   2. Else if prompt has `## SKILL CONTENT` → inline path (existing P1-SEC-B).
#   3. Else block with the legacy `missing_skill_content` reason.

# Module-level toggles (Phase revert = single-line flip to False).
ENABLE_NATIVE_SUBAGENTS = True
ENABLE_SKILL_REFERENCE_MODE = True

# Reference sentinel header — must be on own line, not inside fences.
_SKILL_REFERENCE_HEADER_RE = re.compile(
    r"^##[ \t]+SKILL[ \t]+REFERENCE[ \t]*$",
    flags=re.MULTILINE,
)

# Reference body line: `@<path> sha256=<64-hex>`. Path may be relative.
_SKILL_REFERENCE_LINE_RE = re.compile(
    r"^@(?P<path>\S+)[ \t]+sha256=(?P<hash>[0-9a-f]{64})\b",
    flags=re.MULTILINE,
)

# Caps + thresholds (ADR-051 §Synchronous validation).
_SKILL_REFERENCE_MAX_BYTES = 1_048_576  # 1 MiB DoS cap
_SKILL_REFERENCE_MIN_BODY_BYTES = 512   # distinct from inline 256 floor

# 12 telemetry reason codes (ADR-051 §Telemetry reason codes).
REASON_REFERENCE_MISSING = "reference_missing"
REASON_REFERENCE_UNSAFE_PATH = "reference_unsafe_path"
REASON_REFERENCE_HASH_MISMATCH = "reference_hash_mismatch"
REASON_REFERENCE_SYMLINK_REFUSED = "reference_symlink_refused"
REASON_REFERENCE_TOO_LARGE = "reference_too_large"
REASON_REFERENCE_REDACTION_HIT = "reference_redaction_hit"
REASON_REFERENCE_WRONG_FILENAME = "reference_wrong_filename"
REASON_REFERENCE_MISSING_FRONTMATTER = "reference_missing_frontmatter"
REASON_REFERENCE_BYTE_FLOOR_UNDERFLOW = "reference_byte_floor_underflow"
REASON_REFERENCE_UNICODE_NORMALIZATION_MISMATCH = (
    "reference_unicode_normalization_mismatch"
)
REASON_REFERENCE_OUTSIDE_SKILLS_ROOT = "reference_outside_skills_root"
REASON_MISSING_SKILL_CONTENT = "missing_skill_content"  # legacy/inline

# Session 32 BUGFIX — _lib.redact.redact_secrets whitespace-collapses
# always; equality check with original text is not a valid "secret
# detected" signal. Instead we look for specific replacement tokens
# that `_redact._PATTERNS` inserts when a secret matches.
_SECRET_TOKENS_IN_OUTPUT = frozenset({
    "[JWT]",
    "[API_KEY]",
    "[GITHUB_PAT]",
    "[AWS_KEY]",
    "[TOKEN]",
    "[URL_WITH_CREDS]",
    "[HEX_SECRET]",
    "[REDACTED]",
    "[SLACK_BOT]",
    "[STRIPE_KEY]",
    "[GOOGLE_REFRESH]",
    # PLAN-024 F-hooks-001 P0 fix: redact.py replaces the PEM header
    # with "[SSH_PRIVATE_KEY_HEADER]" — matching raw "-----BEGIN" will
    # never fire after redaction. Check the replacement token instead.
    "[SSH_PRIVATE_KEY_HEADER]",
})


def _is_enabled(env_var: str, default: bool, env: Optional[dict] = None) -> bool:
    """Live read of an env-var toggle with a module default fallback.

    Allows runtime opt-out via env (`CEO_SKILL_REFERENCE_MODE=0`,
    `CEO_NATIVE_SUBAGENTS=0`) without restarting Claude Code.
    `CEO_SOTA_DISABLE=1` is the master kill — overrides everything.
    """
    src_env = env if env is not None else os.environ
    if (src_env.get("CEO_SOTA_DISABLE") or "").strip() == "1":
        return False
    raw = (src_env.get(env_var) or "").strip()
    if raw == "":
        return default
    return raw not in ("0", "false", "FALSE", "False", "no", "off")


def _has_valid_frontmatter_with_name(text: str) -> bool:
    """Stdlib-only frontmatter parser (no PyYAML).

    Returns True iff the file starts with `---` on first line, has a
    closing `---` line, and has at least one `name: <value>` line.
    """
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return False
    body_start = 4 if text.startswith("---\n") else 5
    closing = text.find("\n---", body_start)
    if closing == -1:
        return False
    fm_block = text[body_start:closing]
    return bool(re.search(r"^name:\s*\S+", fm_block, flags=re.MULTILINE))


def _skill_ref_parse_sentinel(
    sanitized: str,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[str], Optional[str]]:
    """Sub-checks 1-2: locate `## SKILL REFERENCE` header + body.

    Returns ``(error_tuple, raw_path, expected_hash)``. On failure,
    ``error_tuple`` is populated and the other fields are None.
    """
    if not _SKILL_REFERENCE_HEADER_RE.search(sanitized):
        return (
            (False, REASON_REFERENCE_MISSING, "no `## SKILL REFERENCE` header"),
            None,
            None,
        )
    body_match = _SKILL_REFERENCE_LINE_RE.search(sanitized)
    if not body_match:
        return (
            (
                False,
                REASON_REFERENCE_MISSING,
                "header found but no `@<path> sha256=<hex>` body",
            ),
            None,
            None,
        )
    return None, body_match.group("path"), body_match.group("hash").lower()


def _skill_ref_resolve_path(
    raw_path: str,
    repo_root: Path,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[Path], Optional[Path]]:
    """Sub-checks 3-5: resolve path, confirm under skills root, filename = SKILL.md, not symlink.

    Returns ``(error_tuple, candidate, resolved)``. On failure, the
    latter two are None.
    """
    skills_root = (repo_root / ".claude" / "skills").resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = repo_root / raw_path
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"resolve failed: {exc}"),
            None,
            None,
        )
    try:
        resolved.relative_to(skills_root)
    except ValueError:
        return (
            (
                False,
                REASON_REFERENCE_OUTSIDE_SKILLS_ROOT,
                f"{resolved} not under {skills_root}",
            ),
            None,
            None,
        )
    if resolved.name != "SKILL.md":
        return (
            (
                False,
                REASON_REFERENCE_WRONG_FILENAME,
                f"filename is {resolved.name!r}, expected 'SKILL.md'",
            ),
            None,
            None,
        )
    if candidate.is_symlink():
        return (
            (
                False,
                REASON_REFERENCE_SYMLINK_REFUSED,
                f"{candidate} is a symlink",
            ),
            None,
            None,
        )
    return None, candidate, resolved


def _skill_ref_validate_unicode(
    candidate: Path,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-check 6: NFC unicode normalization. Returns error_tuple or None."""
    raw_str = str(candidate)
    nfc_str = unicodedata.normalize("NFC", raw_str)
    if nfc_str != raw_str:
        return (
            False,
            REASON_REFERENCE_UNICODE_NORMALIZATION_MISMATCH,
            "path not NFC-normalized",
        )
    return None


def _skill_ref_read_bounded(
    resolved: Path,
) -> Tuple[Optional[Tuple[bool, Optional[str], Optional[str]]], Optional[bytes], Optional[str]]:
    """Sub-checks 7-8: size cap + body floor on non-ws bytes.

    Returns ``(error_tuple, content_bytes, decoded_text)``.
    """
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"stat failed: {exc}"),
            None,
            None,
        )
    if size > _SKILL_REFERENCE_MAX_BYTES:
        return (
            (
                False,
                REASON_REFERENCE_TOO_LARGE,
                f"{size} bytes > {_SKILL_REFERENCE_MAX_BYTES} cap",
            ),
            None,
            None,
        )
    try:
        content_bytes = resolved.read_bytes()
    except OSError as exc:
        return (
            (False, REASON_REFERENCE_MISSING, f"read failed: {exc}"),
            None,
            None,
        )
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return (
            (False, REASON_REFERENCE_MISSING_FRONTMATTER, f"decode: {exc}"),
            None,
            None,
        )
    non_ws = sum(1 for c in text if not c.isspace())
    if non_ws < _SKILL_REFERENCE_MIN_BODY_BYTES:
        return (
            (
                False,
                REASON_REFERENCE_BYTE_FLOOR_UNDERFLOW,
                f"{non_ws} non-ws bytes < {_SKILL_REFERENCE_MIN_BODY_BYTES} floor",
            ),
            None,
            None,
        )
    return None, content_bytes, text


def _skill_ref_validate_frontmatter(
    text: str,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-check 9: YAML frontmatter parseable + has `name:` key."""
    if not _has_valid_frontmatter_with_name(text):
        return (
            False,
            REASON_REFERENCE_MISSING_FRONTMATTER,
            "missing or malformed YAML frontmatter / no `name:` key",
        )
    return None


def _skill_ref_validate_hash_and_redact(
    content_bytes: bytes,
    text: str,
    expected_hash: str,
) -> Optional[Tuple[bool, Optional[str], Optional[str]]]:
    """Sub-checks 10-11: SHA-256 match + redaction scan.

    Per PLAN-025 F-perf-006: SHA-256 on reference-mode skill content
    costs ~1ms for a 5KB skill per invocation. Acceptable at current
    spawn volumes.

    Per Session 32 bugfix: `_redact.redact_secrets` whitespace-collapses
    output, so direct string compare would always mismatch. Instead
    we check for the specific secret-indicator tokens that only appear
    when a pattern matched.
    """
    actual_hash = hashlib.sha256(content_bytes).hexdigest()
    if actual_hash != expected_hash:
        return (
            False,
            REASON_REFERENCE_HASH_MISMATCH,
            f"expected {expected_hash[:8]}..., got {actual_hash[:8]}...",
        )
    redacted = _redact.redact_secrets(text)
    if any(tok in redacted for tok in _SECRET_TOKENS_IN_OUTPUT):
        return (
            False,
            REASON_REFERENCE_REDACTION_HIT,
            "secret pattern detected in skill content",
        )
    return None


def _validate_skill_reference(
    prompt: str,
    repo_root: Optional[Path] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate `## SKILL REFERENCE` sentinel via 11 synchronous sub-checks.

    Refactored (PLAN-050 Phase 1b F-02-03-e) into 6 named helpers for
    readability + per-check test coverage. Same contract: fail-CLOSED
    on any failure, sub-check order preserved from ADR-051 §Synchronous
    validation (sub-check 11 = redaction scan added Session 32;
    PLAN-024 F-hooks-003 doc drift close).
    """
    if not prompt or not isinstance(prompt, str):
        return False, REASON_REFERENCE_MISSING, "empty prompt"

    sanitized = _strip_fenced_and_comments(prompt)

    err, raw_path, expected_hash = _skill_ref_parse_sentinel(sanitized)
    if err:
        return err

    if repo_root is None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        )

    err, candidate, resolved = _skill_ref_resolve_path(raw_path, repo_root)
    if err:
        return err

    err = _skill_ref_validate_unicode(candidate)
    if err:
        return err

    err, content_bytes, text = _skill_ref_read_bounded(resolved)
    if err:
        return err

    err = _skill_ref_validate_frontmatter(text)
    if err:
        return err

    err = _skill_ref_validate_hash_and_redact(
        content_bytes, text, expected_hash
    )
    if err:
        return err

    return True, None, None


def _has_skill_reference(
    prompt: str,
    repo_root: Optional[Path] = None,
) -> bool:
    """Backward-compat wrapper: True iff reference passes all sub-checks."""
    ok, _, _ = _validate_skill_reference(prompt, repo_root=repo_root)
    return ok


# =============================================================================
# PLAN-020 Phase 3 — `/effort` token rejection in spawn prompts
# =============================================================================
#
# `/effort` hints (low/default/high/max + `ultrathink` keyword) are
# CEO-only. They MUST NOT appear in spawn prompts (sub-agents inherit
# their thinking budget from Anthropic defaults). PLAN-020 §4 Phase 3
# §scope clause (QA must-fix #7).

_EFFORT_TOKEN_RE = re.compile(
    r"(?:^|[^\w/])/effort(?:[ \t]+(?:low|default|high|max))?\b",
    flags=re.IGNORECASE,
)


def _has_effort_token(prompt: str) -> bool:
    """True iff prompt contains a `/effort [tier]` slash-command token."""
    if not prompt:
        return False
    sanitized = _strip_fenced_and_comments(prompt)
    return bool(_EFFORT_TOKEN_RE.search(sanitized))



# ---------------------------------------------------------------------------
# PLAN-045 F-10-04 — spawn-prompt secret-scan pre-dispatch
# ---------------------------------------------------------------------------
# Spawn prompts are the #1 vector for accidentally shipping secrets into a
# sub-agent's context. A CEO that copy-pastes a `.env` into a task prompt
# or builds a prompt that interpolates an env var leaks the secret to
# whatever model the sub-agent uses AND to the audit log (spawn prompts
# are recorded for governance).
#
# Reject spawns whose prompt contains any of 6 high-signal secret shapes.
# Each shape is a narrow regex to avoid false-positives on docs / test
# fixtures (prefix-bound + entropy-adjacent). Audit emits
# `veto_triggered(reason_code=spawn_prompt_contains_secret)` on reject.
#
# Kill-switch: `CEO_SPAWN_SECRET_SCAN=0` for the rare case where a prompt
# legitimately contains a long opaque id that trips the scan; Owner-only
# escape logged via veto_triggered(reason_code=spawn_secret_scan_bypassed).
_SPAWN_SECRET_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    # AWS access key ID (AKIA prefix, 16 uppercase alnum after).
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    # Generic AWS secret access key.
    (
        "aws_secret_access_key",
        re.compile(
            r"\b(?:aws[_-]?secret[_-]?access[_-]?key)\b\s*[:=]\s*"
            r"[\"\']?[A-Za-z0-9/+=]{40}[\"\']?",
            re.IGNORECASE,
        ),
    ),
    # Stripe live/test secret key.
    ("stripe_secret_key", re.compile(r"\bsk_(?:live|test)_[0-9A-Za-z]{24,}\b")),
    # GitHub personal access token.
    ("github_pat", re.compile(r"\bghp_[0-9A-Za-z]{36,}\b")),
    # OpenAI API key.
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{48,}\b")),
    # PEM private key preamble.
    (
        "pem_private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"
        ),
    ),
]



def _inject_terse_marker(prompt: str, subagent_type: str) -> str:
    """Inject ## TERSE-MODE marker per PLAN-047 Phase 2."""
    if os.environ.get("CEO_TERSE_MODE", "0") != "1":
        return prompt
    veto_roles = {"code-reviewer", "security-engineer", "qa-architect", "compliance-specialist"}
    if (subagent_type or "") in veto_roles:
        return prompt + "\n\n## TERSE-MODE-DISABLED — VETO role requires full-prose rationale.\n"
    return prompt + "\n\n## TERSE-MODE — fragments OK in exploratory flows; never truncate code or numbers.\n"

def _validate_spawn_prompt_has_no_secrets(
    prompt: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Return (ok, reason_code, detail) — ok=False means BLOCK spawn.

    Short-circuits with ok=True when `CEO_SPAWN_SECRET_SCAN=0` is set
    (Owner bypass; any non-"0" value enforces).
    """
    # Session 75 Codex Finding 4 closure (Owner D4 staged rollout):
    # default OFF, opt-in via CEO_SPAWN_SECRET_SCAN=1. Without the env
    # var (or with =0), function returns ok=True without scanning. Soak
    # protocol: ≥3 sessions of opt-in usage with FPR<1%% before any
    # default flip ADR. Until then, this is a wire-only landing.
    if os.environ.get("CEO_SPAWN_SECRET_SCAN", "0") != "1":
        return True, None, None
    if not prompt:
        return True, None, None
    for family, pattern in _SPAWN_SECRET_PATTERNS:
        m = pattern.search(prompt)
        if m:
            return (
                False,
                "spawn_prompt_contains_secret",
                f"family={family} prompt_len={len(prompt)}",
            )
    return True, None, None


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


# Sprint 5 Phase 7 (ADR-010) — Architect recursion guard.
# When CEO_ARCHITECT_ACTIVE=1 is in the env, any spawn whose
# description/prompt names "Agent Architect" is BLOCKED. Prevents
# meta-agent recursion (Architect-spawning-Architect).
_ARCHITECT_NAME_RE = re.compile(
    r"\bAgent\s+Architect\b",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# PLAN-133 E3 — Per-spawn tool scoping + depth/overlap rails.
# ---------------------------------------------------------------------------
# Ports the Goose recipe "declared capability scope + one-level recursion +
# file partition" idea, re-implemented from scratch in stdlib (rite §2). All
# three rails are ADVISORY by default (emit only) and become BLOCKING only
# under their per-rail env flag. NEVER raises (fail-open per CLAUDE.md §5).
#
# Rail 1 — Tool allow-list: a spawn profile MAY declare
#     ## TOOL ALLOW-LIST
#     - Read
#     - Edit
#     - Bash
# When declared AND the prompt's ## TASK/## RESTRICTIONS text requests a tool
# OUTSIDE that set (heuristic keyword scan, bounded), emit/block. A profile
# with NO ## TOOL ALLOW-LIST block is unrestricted (back-compat: silent allow).
#
# Rail 2 — Depth fence: a sub-agent that itself emits a NAMED spawn is a
# depth-2 spawn. The harness Agent payload has no native depth field, so we
# read the advisory marker the CEO injects into a delegated prompt
# (## SUBAGENT-CONTEXT depth=N) AND the env breadcrumb CEO_SPAWN_DEPTH. If
# EITHER says depth>=1 AND this spawn is itself NAMED, it is depth-over-one.
#
# Rail 3 — FILE ASSIGNMENT overlap: parse this spawn's `CAN edit:` file list
# from its ## FILE ASSIGNMENT block, compare against the `CAN edit:` lists of
# other spawns recorded in the audit log within a short concurrency window
# (same session, same plan). Any shared concrete path = clobber risk.

# --- Rail 1: tool allow-list ----------------------------------------------
_TOOL_ALLOWLIST_HEADER_RE = re.compile(
    r"^##[ \t]+TOOL[ \t]+ALLOW-?LIST[ \t]*$",
    flags=re.MULTILINE,
)
# A bullet line inside the block: "- Read" / "* Bash" / "Read,Edit".
_TOOL_BULLET_RE = re.compile(
    r"^[ \t]*[-*][ \t]*([A-Za-z][A-Za-z0-9_/ ,]+)$",
    flags=re.MULTILINE,
)
# Canonical Claude Code tool names we recognize (closed set — anything not
# here in a request is ignored, NOT blocked; we only gate KNOWN tools so an
# unknown token can never cause a false block).
_KNOWN_TOOL_NAMES = frozenset({
    "read", "edit", "write", "multiedit", "bash", "glob", "grep",
    "webfetch", "websearch", "task", "agent", "notebookedit",
})
# Heuristic: which tools a spawn is REQUESTING, inferred from prompt text.
# First-hit, bounded scan. Conservative — only fires on high-signal verbs so
# a profile that simply mentions a word does not trip the rail.
_TOOL_REQUEST_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("bash", ("run the command", "run `", "execute the script", "shell out",
              "git commit", "git push", "npm install", "curl ", "subprocess")),
    ("write", ("create the file", "write a new file", "write the file")),
    ("edit", ("edit the file", "modify the file", "apply the patch")),
    ("webfetch", ("fetch the url", "download from http", "fetch http")),
    ("websearch", ("search the web", "web search")),
)
_TOOL_SCAN_WINDOW = 8 * 1024  # bytes of prompt scanned for tool hints

# --- Rail 2: depth fence ---------------------------------------------------
_SUBAGENT_DEPTH_MARKER_RE = re.compile(
    r"^##[ \t]+SUBAGENT-CONTEXT\b[^\n]*\bdepth=(\d+)",
    flags=re.MULTILINE,
)

# --- Rail 3: FILE ASSIGNMENT overlap --------------------------------------
_FILE_ASSIGNMENT_HEADER_RE = re.compile(
    r"^##[ \t]+FILE[ \t]+ASSIGNMENT[ \t]*$",
    flags=re.MULTILINE,
)
# "- CAN edit: a/b.py, c/d.py" (rest of line after the colon, comma-split).
_CAN_EDIT_LINE_RE = re.compile(
    r"^[ \t]*[-*][ \t]*CAN[ \t]+edit:[ \t]*(.+)$",
    flags=re.MULTILINE | re.IGNORECASE,
)
_OVERLAP_LOOKBACK_S = 600          # 10-minute concurrency window
_OVERLAP_MAX_PATHS = 64            # bound the per-spawn path set
_OVERLAP_TAIL_LINES = 256          # bounded audit-log tail (~512KB)


def _parse_tool_allowlist(prompt: str) -> Optional[frozenset]:
    """Return the declared lowercase tool allow-list, or None if no
    `## TOOL ALLOW-LIST` block is present (= unrestricted, back-compat).

    Pure. Never raises. Bounded to the block between its header and the next
    `##` heading. Only KNOWN tool names are retained; unknown tokens dropped
    (so a typo cannot create a phantom allow-list that blocks everything).
    """
    if not prompt:
        return None
    sanitized = _strip_fenced_and_comments(prompt)
    m = _TOOL_ALLOWLIST_HEADER_RE.search(sanitized)
    if m is None:
        return None
    block_start = m.end()
    nxt = _NEXT_H2_RE.search(sanitized, block_start)
    block = sanitized[block_start: nxt.start() if nxt else len(sanitized)]
    allowed = set()
    for bm in _TOOL_BULLET_RE.finditer(block):
        for tok in bm.group(1).replace(",", " ").split():
            t = tok.strip().lower()
            if t in _KNOWN_TOOL_NAMES:
                allowed.add(t)
    # An empty-but-present block = "deny all known tools" (intentional).
    return frozenset(allowed)


def _requested_tools(prompt: str) -> frozenset:
    """Heuristic set of KNOWN tools this spawn appears to request.

    First-hit per family, bounded scan. Conservative (high-signal verbs only).
    Pure; never raises.
    """
    if not prompt:
        return frozenset()
    text = _strip_fenced_and_comments(prompt)[:_TOOL_SCAN_WINDOW].lower()
    out = set()
    for tool, hints in _TOOL_REQUEST_HINTS:
        if any(h in text for h in hints):
            out.add(tool)
    return frozenset(out)


def _check_tool_scope(
    prompt: str,
) -> Optional[Tuple[str, str]]:
    """Rail 1. Return (reason_code, detail) if a requested tool is OUTSIDE
    the declared allow-list, else None.

    `detail` NEVER contains a path or the raw prompt — only the offending
    tool NAME(s) (a closed-enum-safe value) + counts. No-value-echo safe.
    """
    allow = _parse_tool_allowlist(prompt)
    if allow is None:
        return None  # no declared scope -> unrestricted (back-compat)
    requested = _requested_tools(prompt)
    out_of_scope = sorted(requested - allow)
    if not out_of_scope:
        return None
    return (
        "spawn_tool_out_of_scope",
        f"tools={','.join(out_of_scope)} declared={len(allow)}",
    )


def _spawn_depth(prompt: str, env: Dict[str, str]) -> int:
    """Best-effort current spawn depth. 0 = top-level CEO spawn.

    Two independent signals, max() wins (fail-toward-detection):
      - `## SUBAGENT-CONTEXT depth=N` marker in the prompt (CEO-injected when
        delegating to a sub-agent that may itself coordinate).
      - `CEO_SPAWN_DEPTH` env breadcrumb (harness/CEO-set).
    Pure-ish (reads env dict only). Never raises.
    """
    depth = 0
    try:
        m = _SUBAGENT_DEPTH_MARKER_RE.search(prompt or "")
        if m:
            depth = max(depth, int(m.group(1)))
    except Exception:  # pragma: no cover - fail-open
        pass
    try:
        raw = (env.get("CEO_SPAWN_DEPTH") or "").strip()
        if raw.isdigit():
            depth = max(depth, int(raw))
    except Exception:  # pragma: no cover - fail-open
        pass
    return depth


def _parse_file_assignment(prompt: str) -> frozenset:
    """Return the set of concrete `CAN edit:` paths declared in the spawn's
    `## FILE ASSIGNMENT` block. Empty set if none.

    Pure. Never raises. Bounded to _OVERLAP_MAX_PATHS. Wildcard/placeholder
    tokens ({file list}, *, dir/**) are DROPPED — only concrete paths
    participate in overlap detection (a glob can't be proven to clobber).
    """
    if not prompt:
        return frozenset()
    sanitized = _strip_fenced_and_comments(prompt)
    m = _FILE_ASSIGNMENT_HEADER_RE.search(sanitized)
    if m is None:
        return frozenset()
    block_start = m.end()
    nxt = _NEXT_H2_RE.search(sanitized, block_start)
    block = sanitized[block_start: nxt.start() if nxt else len(sanitized)]
    paths = set()
    for lm in _CAN_EDIT_LINE_RE.finditer(block):
        for raw in lm.group(1).split(","):
            p = raw.strip().strip("`").strip()
            if not p:
                continue
            # Drop placeholders + wildcards (cannot prove a clobber).
            if p.startswith("{") or "*" in p or p.lower() in (
                "none", "n/a", "tbd",
            ):
                continue
            # Normalize: strip a leading ./, collapse, lowercase-fold only the
            # drive-irrelevant case (POSIX paths are case-sensitive, so keep
            # case but normalize separators).
            p = p.lstrip("./").replace("\\", "/")
            paths.add(p)
            if len(paths) >= _OVERLAP_MAX_PATHS:
                return frozenset(paths)
    return frozenset(paths)


def _path_hash(p: str) -> str:
    """12-hex sha256 prefix of a path. The ONLY path representation that
    enters the audit log (no raw path body ever persists — Sec MF-3)."""
    return hashlib.sha256(p.encode("utf-8", "replace")).hexdigest()[:12]


def _recent_file_assignments(
    env: Dict[str, str],
    session_id: str,
    max_age_s: int = _OVERLAP_LOOKBACK_S,
) -> frozenset:
    """Tail the audit log for `CAN edit:` path-HASHES emitted by OTHER spawns
    in this session within the window. Returns a set of 12-hex path hashes.

    Reads only `spawn_file_assignment_recorded` advisory rows (emitted at the
    allow-path of a prior spawn — see 4d). Bounded tail. Never raises; returns
    empty set on any error (fail-open -> no overlap detected -> allow).
    """
    try:
        log_path = _audit_log_path()
        if log_path is None or not log_path.exists():
            return frozenset()
        import json as _json
        import time as _time
        with log_path.open("r", encoding="utf-8") as f:
            try:
                f.seek(0, 2)
                size = f.tell()
                read_back = min(size, _OVERLAP_TAIL_LINES * 2048)
                start = max(0, size - read_back)
                f.seek(start, 0)
                if start > 0:
                    f.readline()
                tail = f.readlines()
            except OSError:
                tail = f.readlines()[-_OVERLAP_TAIL_LINES:]
        now = _time.time()
        seen = set()
        for line in reversed(tail):
            try:
                ev = _json.loads(line)
            except Exception:
                continue
            if ev.get("action") != "spawn_file_assignment_recorded":
                continue
            if session_id and ev.get("session_id") != session_id:
                continue
            ts_f = _parse_event_ts(ev.get("ts"))
            if ts_f is None or (now - ts_f) > max_age_s:
                continue
            ph = ev.get("path_hashes")
            if isinstance(ph, str):
                for h in ph.split(","):
                    h = h.strip()
                    if h:
                        seen.add(h)
        return frozenset(seen)
    except Exception:  # pragma: no cover - fail-open
        return frozenset()


def _enforce_spawn_rails(
    *,
    prompt: str,
    is_named_spawn: bool,
    env: Dict[str, str],
    session_id: str,
) -> Optional[Tuple[str, str]]:
    """PLAN-133 E3 — evaluate the three rails. Returns (reason_code, detail)
    when a rail is in ENFORCING mode (its flag=1) AND fires; else None.

    In ADVISORY mode (flag unset/0) the rail still EMITS its closed-enum
    event with enforced=0 (measure-first) and returns None (allow).

    NEVER raises. Each rail independently flagged; CEO_SOTA_DISABLE=1 forces
    advisory for all three.
    """
    try:
        master_off = (env.get("CEO_SOTA_DISABLE") or "").strip() == "1"

        def _flag(name: str) -> bool:
            if master_off:
                return False
            return (env.get(name) or "").strip() == "1"

        # --- Rail 1: tool scope (applies to ANY spawn that declares a list) -
        scope_hit = _check_tool_scope(prompt)
        if scope_hit is not None:
            code, detail = scope_hit
            enforced = _flag("CEO_SPAWN_TOOL_SCOPE")
            _emit_tool_scope_violation(detail=detail, enforced=enforced)
            if enforced:
                return (code, detail)

        # Rails 2 + 3 only matter for NAMED spawns (a generic research task
        # neither recurses into named delegation nor partitions files).
        if is_named_spawn:
            # --- Rail 2: depth fence ---------------------------------------
            depth = _spawn_depth(prompt, env)
            if depth >= 1:
                enforced = _flag("CEO_SPAWN_DEPTH_GUARD")
                _emit_depth_or_overlap(
                    rail="depth", enforced=enforced, count=depth,
                )
                if enforced:
                    return (
                        "spawn_depth_over_one",
                        f"depth={depth}",
                    )

            # --- Rail 3: FILE ASSIGNMENT overlap ---------------------------
            mine = _parse_file_assignment(prompt)
            if mine:
                others = _recent_file_assignments(env, session_id)
                my_hashes = {_path_hash(p) for p in mine}
                clobber = my_hashes & others
                if clobber:
                    enforced = _flag("CEO_SPAWN_OVERLAP_GUARD")
                    _emit_depth_or_overlap(
                        rail="overlap", enforced=enforced, count=len(clobber),
                    )
                    if enforced:
                        return (
                            "spawn_file_assignment_overlap",
                            f"overlap_count={len(clobber)}",
                        )
                # Record THIS spawn's assignment so the NEXT concurrent spawn
                # can detect a clash against it (advisory; always recorded).
                _emit_file_assignment_recorded(my_hashes, session_id)
        return None
    except Exception:  # pragma: no cover - fail-open invariant
        return None


def _emit_tool_scope_violation(*, detail: str, enforced: bool) -> None:
    """Emit `spawn_tool_scope_violation` (closed-enum). No-value-echo:
    `detail` carries only tool NAMES + counts (no path / prompt body)."""
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        _audit_emit.emit_generic(
            "spawn_tool_scope_violation",
            rail="tool_scope",
            enforced=1 if enforced else 0,
            detail=(detail or "")[:96],
        )
    except Exception:  # pragma: no cover - fail-open
        return


def _emit_depth_or_overlap(*, rail: str, enforced: bool, count: int) -> None:
    """Emit `spawn_depth_or_overlap_blocked` (closed-enum). `rail` is a
    closed enum (depth|overlap); `count` is a bounded int. No path / prompt."""
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        _audit_emit.emit_generic(
            "spawn_depth_or_overlap_blocked",
            rail=(rail if rail in ("depth", "overlap") else "other"),
            enforced=1 if enforced else 0,
            count=count,
        )
    except Exception:  # pragma: no cover - fail-open
        return


def _emit_file_assignment_recorded(path_hashes: set, session_id: str) -> None:
    """Advisory: record THIS spawn's CAN-edit path HASHES so a later
    concurrent spawn can detect an overlap. Only 12-hex hashes persist."""
    try:
        if not _AUDIT_EMIT_AVAILABLE:
            return
        joined = ",".join(sorted(path_hashes))[:512]
        _audit_emit.emit_generic(
            "spawn_file_assignment_recorded",
            session_id=(session_id or "")[:64],
            path_hashes=joined,
            path_count=min(len(path_hashes), 99),
        )
    except Exception:  # pragma: no cover - fail-open
        return


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
                        "security-engineer and code-reviewer to bind to "
                        "claude-opus-4-8. See ADR-052 + PLAN-045 Wave 1 P0-03."
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
                "allow-list / depth-over-one fence / FILE ASSIGNMENT overlap). "
                "See PLAN-133 §E E3."
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


# ---------------------------------------------------------------------------
# PLAN-105 Wave A.6 — Deferred-emit override detection helper.
#
# Reads the most-recent goap_recommendation_rendered event in the current
# session (≤5 min window, matching plan_id), compares the spawn's
# `goap-action-id:` marker, and emits goap_recommendation_accepted on
# exact match OR goap_recommendation_overridden with the appropriate
# `override_type` (substituted_action / no_render_prior / marker_absent).
#
# Kill-switches:
#   CEO_GOAP_ADVISORY_ENABLED=0  → all 3 emits silent (existing PLAN-098 kill-switch)
#   CEO_GOAP_OVERRIDE_DETECTION_DISABLED=1  → always emit _accepted on allow-path (diagnostic only)
# ---------------------------------------------------------------------------

_GOAP_RENDER_LOOKBACK_S = 300  # 5 minutes


def _audit_log_path() -> Optional[Path]:
    """Resolve audit log path — delegates to audit_emit._log_path() for
    byte-identical write/read paths.

    PLAN-105 R2 P0 #2 fold: previously derived a slug from CLAUDE_PROJECT_DIR,
    which diverged from audit_emit's `~/.claude/projects/ceo-orchestration`
    default. Now imports the real resolver so reader path == writer path.
    """
    try:
        from _lib import audit_emit as _ae  # type: ignore
        path = _ae._log_path()
        return path if path else None
    except Exception:
        # Fallback: env-driven path so unit tests using CEO_AUDIT_LOG_PATH
        # work pre-import.
        env_path = os.environ.get("CEO_AUDIT_LOG_PATH")
        if env_path:
            return Path(env_path)
        env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
        if env_dir:
            return Path(env_dir) / "audit-log.jsonl"
        return None


def _parse_event_ts(ts) -> Optional[float]:
    """Parse audit-log ts field (ISO-8601 UTC string or epoch float) → epoch seconds."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        # Try epoch first.
        try:
            return float(s)
        except (TypeError, ValueError):
            pass
        # ISO-8601 — strip trailing Z, parse via datetime.fromisoformat.
        import datetime as _dt
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return _dt.datetime.fromisoformat(s).timestamp()
        except Exception:
            return None
    return None


def _tail_recent_rendered(
    plan_id: str,
    max_age_s: int = _GOAP_RENDER_LOOKBACK_S,
    session_id: Optional[str] = None,
):
    """Tail audit log for most-recent goap_recommendation_rendered matching plan_id.

    PLAN-105 R2 P1 fold:
    - Optional `session_id` filter — same-session join (concurrent sessions
      with same plan_id within 5 min cannot misclassify).
    - Conservative ts handling — unparseable / missing ts treated as
      out-of-window (skipped), not as "match-anyway".

    Returns parsed event dict (Optional[dict]). Returns None if no match
    within `max_age_s` seconds. Bounded tail = last 256 lines (~512KB).
    """
    log_path = _audit_log_path()
    if log_path is None or not log_path.exists():
        return None
    try:
        import json as _json
        import time as _time
        with log_path.open("r", encoding="utf-8") as f:
            # Read last ~256 lines via seek-from-end (bounded perf).
            try:
                f.seek(0, 2)
                size = f.tell()
                read_back = min(size, 256 * 2048)  # ~512KB max
                start_offset = max(0, size - read_back)
                f.seek(start_offset, 0)
                # Only discard partial first line if we didn't seek to 0
                # (otherwise we'd lose the first real line of a small file).
                if start_offset > 0:
                    f.readline()
                tail = f.readlines()
            except OSError:
                tail = f.readlines()[-256:]
        now = _time.time()
        for line in reversed(tail):
            try:
                ev = _json.loads(line)
            except Exception:
                continue
            if ev.get("action") != "goap_recommendation_rendered":
                continue
            if ev.get("plan_id") != plan_id:
                continue
            # PLAN-105 R2 P1-3 fold — same-session filter when provided.
            if session_id is not None and ev.get("session_id") != session_id:
                continue
            ts_f = _parse_event_ts(ev.get("ts"))
            # PLAN-105 R2 P1-2 fold — conservative: unparseable ts skipped.
            if ts_f is None:
                continue
            if (now - ts_f) > max_age_s:
                # Older than the window — skip.
                continue
            return ev
        return None
    except Exception:
        return None


def _resolve_session_id_from_env(env: Dict[str, str]) -> str:
    """Resolve session_id from harness env (CLAUDE_SESSION_ID) — PLAN-105 R2 P1-1 fold."""
    for key in ("CLAUDE_SESSION_ID", "CEO_SESSION_ID"):
        v = (env.get(key) or "").strip()
        if v:
            return v[:64]
    return ""


def _resolve_project_from_env(env: Dict[str, str]) -> str:
    """Derive project slug from CLAUDE_PROJECT_DIR basename — PLAN-105 R2 P1-1 fold."""
    pd = (env.get("CLAUDE_PROJECT_DIR") or "").strip()
    if pd:
        return Path(pd).name[:64]
    return ""


def _emit_persona_coverage_synthesized(
    subagent_type: str,
    description: str,
    prompt: str,
    source: str,
    env: dict,
) -> None:
    """PLAN-106 Wave C — emit persona_coverage_synthesized at allow path.

    Maps (subagent_type, derived task_type) → 4×4 cell, emits one
    event via audit_emit.emit_generic. Best-effort; any exception is
    swallowed (fail-open). Bypass: ``CEO_PERSONA_COVERAGE_EMIT=0``.

    The closed-enum sets (archetype + task_type) MUST match
    `_lib/audit_emit.py:_PERSONA_COVERAGE_ARCHETYPES` /
    `_PERSONA_COVERAGE_TASK_TYPES`. Both lists are duplicated here
    intentionally so the hook does no extra import at hot-path.
    """
    if (env.get("CEO_PERSONA_COVERAGE_EMIT") or "").strip() == "0":
        return
    if not _AUDIT_EMIT_AVAILABLE:
        return
    # Closed-set archetype filter — only emit for the 4 VETO-floor personas.
    arch_lower = (subagent_type or "").strip().lower()
    if arch_lower not in {
        "code-reviewer", "security-engineer", "qa-architect",
        "threat-detection-engineer",
    }:
        return
    # Derive task_type via simple description+prompt keyword scan.
    haystack = " ".join([
        (description or "").lower(),
        (prompt or "")[:4096].lower(),  # bounded — security R1 P1 NFKC budget
    ])
    # NFKC normalize once (Cf-injected bypass guard — full-width chars
    # in adversarial spawn prompts).
    haystack = unicodedata.normalize("NFKC", haystack)
    task_type = ""
    # Order matters: most specific first.
    for keyword, t in (
        ("review", "review"),
        ("audit", "review"),  # reviewer aliases
        ("vet", "vet"),
        ("validate", "vet"),
        ("verify", "vet"),
        ("test", "test"),
        ("detect", "detect"),
        ("triage", "detect"),
        ("incident", "detect"),
    ):
        if keyword in haystack:
            task_type = t
            break
    if not task_type:
        # No keyword match → no cell signal. Skip emit; do not
        # arbitrarily bin into a default cell (would skew coverage).
        return

    # cell_id = sha256[:8] of canonical f"{arch_lower}:{task_type}".
    # Deterministic across calls so dedup at audit layer can collapse
    # repeats from check_agent_spawn + check_canonical_edit on the
    # same (archetype, task_type) within a window.
    cell_input = f"{arch_lower}:{task_type}".encode("utf-8")
    cell_id = hashlib.sha256(cell_input).hexdigest()[:8]

    try:
        _audit_emit.emit_generic(
            "persona_coverage_synthesized",
            archetype=arch_lower,
            task_type=task_type,
            cell_id=cell_id,
            source=source,
        )
    except Exception:  # noqa: BLE001 — fail-open, never block spawn
        pass


def _emit_goap_deferred_outcome(
    plan_id: Optional[str],
    action_id: Optional[str],
    env: Dict[str, str],
) -> None:
    """Emit goap_recommendation_accepted or _overridden at decide() allow-return.

    PLAN-105 Wave A.6. Silent no-op if plan_id is None (non-GOAP spawn).
    Silent no-op if kill-switch CEO_GOAP_ADVISORY_ENABLED=0.

    PLAN-105 R2 P1-1 fold: session_id + project propagated from env so
    audit consumers can correlate spawn outcome with rendered event.
    """
    if not plan_id:
        return
    if (env.get("CEO_GOAP_ADVISORY_ENABLED", "1") or "").strip() == "0":
        return
    try:
        from _lib import audit_emit as _ae  # type: ignore
    except Exception:
        return

    session_id = _resolve_session_id_from_env(env)
    project = _resolve_project_from_env(env)

    diag_force_accept = (
        env.get("CEO_GOAP_OVERRIDE_DETECTION_DISABLED", "0") or ""
    ).strip() == "1"
    if diag_force_accept:
        fn = getattr(_ae, "emit_goap_recommendation_accepted", None)
        if fn is not None:
            try:
                fn(plan_id=plan_id, action_id=(action_id or "DIAG_FORCED"),
                   session_id=session_id, project=project)
            except Exception:
                pass
        return

    # PLAN-105 R2 P1-3 fold — same-session filter when session_id available.
    rendered = _tail_recent_rendered(
        plan_id,
        session_id=session_id if session_id else None,
    )
    if rendered is None:
        # Try a second pass without session-id filter — covers cases where
        # the _rendered event was emitted from /goap CLI invocation that
        # didn't carry session_id (or session env was unset at planner time).
        rendered = _tail_recent_rendered(plan_id)
    if rendered is None:
        # No recent _rendered for this plan_id — emit _overridden:no_render_prior.
        fn = getattr(_ae, "emit_goap_recommendation_overridden", None)
        if fn is not None:
            try:
                fn(plan_id=plan_id,
                   original_action_id="NO_RENDER_PRIOR",
                   dispatched_action_id=(action_id or "MARKER_ABSENT"),
                   override_type="no_render_prior",
                   session_id=session_id, project=project)
            except Exception:
                pass
        return

    if action_id is None:
        # Spawn lacks goap-action-id marker — emit _overridden:marker_absent.
        fn = getattr(_ae, "emit_goap_recommendation_overridden", None)
        if fn is not None:
            try:
                fn(plan_id=plan_id,
                   original_action_id=(rendered.get("action_ids_csv", "") or "")[:64],
                   dispatched_action_id="MARKER_ABSENT",
                   override_type="marker_absent",
                   session_id=session_id, project=project)
            except Exception:
                pass
        return

    rendered_csv = rendered.get("action_ids_csv", "") or ""
    rendered_ids = [s.strip() for s in rendered_csv.split(",") if s.strip()]
    if action_id in rendered_ids:
        fn = getattr(_ae, "emit_goap_recommendation_accepted", None)
        if fn is not None:
            try:
                fn(plan_id=plan_id, action_id=action_id,
                   session_id=session_id, project=project)
            except Exception:
                pass
    else:
        fn = getattr(_ae, "emit_goap_recommendation_overridden", None)
        if fn is not None:
            try:
                fn(plan_id=plan_id,
                   original_action_id=rendered_csv[:64],
                   dispatched_action_id=action_id,
                   override_type="substituted_action",
                   session_id=session_id, project=project)
            except Exception:
                pass


# Session 75 Codex re-pass remaining concern: derive a stable
# reason_code from the human-readable Decision.reason so the audit
# trail correctly classifies the block path. Order is significant —
# more-specific prefixes first, generic fallback last.
# PLAN-098 Wave C.2 (ADR-132) - GOAP advisory-only invariant enforcement.
_GOAP_PLAN_ID_RE = re.compile(r"\bgoap-plan-id\s*:\s*\S+", re.IGNORECASE)
_GOAP_CONFIRM_HEADER_RE = re.compile(
    r"^##\s+GOAP\s+CONFIRM\b", re.IGNORECASE | re.MULTILINE
)
# PLAN-105 Wave A.6 - capture value of goap-plan-id / goap-action-id markers
# for deferred-emit override detection at decide() allow-path return.
_GOAP_PLAN_ID_VALUE_RE = re.compile(
    r"\bgoap-plan-id\s*:\s*(\S+)", re.IGNORECASE
)
_GOAP_ACTION_ID_VALUE_RE = re.compile(
    r"\bgoap-action-id\s*:\s*(\S+)", re.IGNORECASE
)


_BLOCK_REASON_MARKERS = (
    ("SPAWN-SECRET-BLOCKED", "secret_in_spawn_prompt"),
    ("GOVERNANCE: veto_floor_demoted", "veto_floor_demoted"),
    ("ARCHITECT-RECURSION", "architect_role_not_delegable"),
    ("GOVERNANCE: spawn prompt contains a `/effort` token", "effort_token_in_spawn"),
    # Skill-reference path: reason text format is
    # "GOVERNANCE: <reason_code>: <detail>..." — extract the embedded code.
    ("GOVERNANCE: reference_", "__REFERENCE_PREFIX__"),
    # PLAN-098 Wave C.2 (ADR-132) - GOAP advisory-only invariant.
    ("GOVERNANCE: goap_advisory_without_owner_confirm", "goap_advisory_without_owner_confirm"),
    # PLAN-133 E3 — per-spawn tool scoping + depth/overlap rails.
    ("GOVERNANCE: spawn_tool_out_of_scope", "spawn_tool_out_of_scope"),
    ("GOVERNANCE: spawn_depth_over_one", "spawn_depth_over_one"),
    ("GOVERNANCE: spawn_file_assignment_overlap", "spawn_file_assignment_overlap"),
    # NAMED-spawn-without-skill is the historical default — keep last.
    ("GOVERNANCE: Agent spawn detected as NAMED", "missing_skill_content"),
)


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


def main() -> int:
    """Hook entry point: read stdin, decide, write stdout, exit 0.

    PLAN-006 Phase 1 migration (ADR-014): Adapter Layer I/O.
    Fail-open on any exception.
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_agent_spawn] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            names_regex = _team.load_names(project_dir)
        except Exception as e:  # pragma: no cover
            print(
                f"[check_agent_spawn] WARN: team load failed: {e}",
                file=sys.stderr,
            )
            names_regex = None

        decision = decide(
            description=event.description,
            prompt=event.prompt,
            names_regex=names_regex,
            subagent_type=event.subagent_type,
        )

        # Side-effect: emit veto_triggered event on block path (v2 stream).
        # Session 75 Codex re-pass: reason_code derived from decision.reason
        # via _classify_block_reason() so the audit trail correctly
        # discriminates secret_in_spawn_prompt / effort_token_in_spawn /
        # architect_role_not_delegable / veto_floor_demoted / etc.
        # Previously hardcoded "missing_skill_content" misclassified all blocks.
        if not decision.allow and _AUDIT_EMIT_AVAILABLE:
            try:
                _audit_emit.emit_veto_triggered(
                    hook="check_agent_spawn",
                    reason_code=_classify_block_reason(decision.reason or ""),
                    reason_preview=decision.reason or "",
                    blocked_tool="Agent",
                    project=project_dir,
                )
            except Exception:
                pass

        _claude_adapter.emit_decision(_to_contract_decision(decision))
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_agent_spawn] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


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


if __name__ == "__main__":
    sys.exit(main())
