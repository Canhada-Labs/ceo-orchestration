from __future__ import annotations

__all__ = ('_TASK_ROUTE_MODULE', '_TASK_ROUTE_LOAD_FAILED', '_FRONTMATTER_MODEL_CACHE', '_FRONTMATTER_CACHE_MAX', '_resolve_task_route', '_read_archetype_model_frontmatter', '_extract_archetype_from_payload', '_emit_model_routing_advisory')

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
