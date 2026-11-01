from __future__ import annotations

import re

__all__ = ('_GOAP_RENDER_LOOKBACK_S', '_audit_log_path', '_parse_event_ts', '_tail_recent_rendered', '_resolve_session_id_from_env', '_resolve_project_from_env', '_emit_persona_coverage_synthesized', '_emit_goap_deferred_outcome', '_GOAP_PLAN_ID_RE', '_GOAP_CONFIRM_HEADER_RE', '_GOAP_PLAN_ID_VALUE_RE', '_GOAP_ACTION_ID_VALUE_RE', '_BLOCK_REASON_MARKERS')

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
    which diverged from audit_emit's `~/.claude/projects/<native-slug>`
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
    # PLAN-178 C1 / ADR-191 - FILE ASSIGNMENT grammar (measure-first flip).
    ("GOVERNANCE: spawn_file_assignment_missing", "spawn_file_assignment_missing"),
    ("GOVERNANCE: spawn_file_assignment_unparseable", "spawn_file_assignment_unparseable"),
    # PLAN-153 Wave E item 7 (ADR-175) — Prompt Defense Baseline gate.
    ("GOVERNANCE: spawn_prompt_defense_missing", "spawn_prompt_defense_missing"),
    # NAMED-spawn-without-skill is the historical default — keep last.
    ("GOVERNANCE: Agent spawn detected as NAMED", "missing_skill_content"),
)
