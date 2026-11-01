from __future__ import annotations

def _bench_pass_rate(r: Dict[str, Any]) -> float:
    """Per-run pass-rate. Prefers int-encoded ``pass_rate_bps`` (÷1000);
    falls back to legacy float ``pass_rate``."""
    bps = r.get("pass_rate_bps")
    if bps is not None:
        try:
            return int(bps) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("pass_rate") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_turns(r: Dict[str, Any]) -> int:
    """Per-run scenario count (the harbor 'turns' column). Tolerant."""
    try:
        return int(r.get("pass_count") or 0) + int(r.get("fail_count") or 0)
    except (TypeError, ValueError):
        return 0


def benchmark_rollup(
    *,
    audit_dir: Optional[Path] = None,
    since: Optional[timedelta] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Co-report cost + compute + turns alongside pass-rate per benchmark
    skill (PLAN-133 C4, harbor-style row). Read-only; fail-open on infra.

    Returns a JSON-serializable dict with a per-skill list. Each row carries
    the latest pass-rate plus the cumulative + latest cost/compute/turns so
    an operator sees both the marginal and trend cost of a benchmark.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = (now - since) if since is not None else None

    log_paths = discover_logs(audit_dir)
    by_skill: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for ev in iter_unique_events(log_paths):
            if ev.get("action") != "benchmark_run":
                continue
            ts = _parse_ts(ev.get("ts"))
            if cutoff is not None and ts is not None and ts < cutoff:
                continue
            skill = str(ev.get("skill") or "?")
            by_skill.setdefault(skill, []).append(ev)
    except Exception:
        # fail-open-on-infra: a malformed log never crashes the rollup.
        by_skill = {}

    rows: List[Dict[str, Any]] = []
    tot_cost = 0.0
    tot_compute = 0.0
    tot_turns = 0
    for skill in sorted(by_skill.keys()):
        runs = sorted(by_skill[skill], key=lambda r: r.get("ts") or "")
        latest = runs[-1]
        s_cost = sum(_bench_cost_usd(r) for r in runs)
        s_compute = sum(_bench_duration_s(r) for r in runs)
        s_turns = sum(_bench_turns(r) for r in runs)
        tot_cost += s_cost
        tot_compute += s_compute
        tot_turns += s_turns
        rows.append({
            "skill": skill,
            "runs": len(runs),
            "latest_pass_rate": round(_bench_pass_rate(latest), 3),
            "latest_cost_usd": round(_bench_cost_usd(latest), 6),
            "total_cost_usd": round(s_cost, 6),
            "latest_compute_s": round(_bench_duration_s(latest), 3),
            "total_compute_s": round(s_compute, 3),
            "latest_turns": _bench_turns(latest),
            "total_turns": s_turns,
            "latest_ts": latest.get("ts"),
        })
    return {
        "per_skill": rows,
        "total_cost_usd": round(tot_cost, 6),
        "total_compute_s": round(tot_compute, 3),
        "total_turns": tot_turns,
        "skill_count": len(rows),
    }


def _extract_wave_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract a wave-id from an event if present.

    Heuristic: check ``wave_id``, ``wave``, then scan
    ``desc_preview``/``description`` for a ``wave-X`` substring.
    """
    for key in ("wave_id", "wave"):
        v = event.get(key)
        if isinstance(v, str) and _WAVE_ID_RE.match(v):
            return v
    for key in ("desc_preview", "description", "task_description"):
        v = event.get(key)
        if isinstance(v, str):
            m = re.search(r"\b(wave-[a-z0-9-]{1,16})\b", v)
            if m and _WAVE_ID_RE.match(m.group(1)):
                return m.group(1)
    return None


def default_native_root() -> Path:
    """Root of the harness-native transcript corpus for THIS project.

    Honors ``CEO_NATIVE_USAGE_DIR`` env override (used by tests).
    Otherwise ``~/.claude/projects/<cwd-slug>/`` where ``<cwd-slug>`` is
    the absolute project path (``$CLAUDE_PROJECT_DIR``, else cwd) with
    ``/`` replaced by ``-`` (probe §1.1).
    """
    env_dir = os.environ.get("CEO_NATIVE_USAGE_DIR")
    if env_dir:
        return Path(env_dir)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = _rp.project_slug(project_dir)  # PLAN-182 W3 (S321): slug via resolvedor unico, nunca re-derivado
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / slug


def _native_transcript_paths(
    native_root: Optional[Path],
) -> List[Tuple[Path, str, str]]:
    """Discover native agent transcripts under ``native_root``.

    Returns ``(path, rail, session_id)`` triples. Rail is derived from
    the PATH shape (probe §3 blocker: the corpus has no field for it):
    ``*/subagents/agent-a*.jsonl`` ⇒ ``task``;
    ``*/subagents/workflows/wf_*/agent-a*.jsonl`` ⇒ ``workflow``.
    ``journal.jsonl`` never matches (``agent-a*`` prefix). The
    SESSION-UUID is the first path component under the root.
    """
    out: List[Tuple[Path, str, str]] = []
    if native_root is None or not native_root.is_dir():
        return out
    root = str(native_root)
    task_glob = os.path.join(root, "*", "subagents", "agent-a*.jsonl")
    wf_glob = os.path.join(
        root, "*", "subagents", "workflows", "wf_*", "agent-a*.jsonl"
    )
    for pattern, rail in ((task_glob, "task"), (wf_glob, "workflow")):
        for raw in sorted(glob.glob(pattern)):
            p = Path(raw)
            try:
                session_id = p.relative_to(native_root).parts[0]
            except (ValueError, IndexError):
                session_id = "(unknown)"
            out.append((p, rail, session_id))
    return out


def _cache_read_multiplier(model_id: str) -> float:
    """Cache-read multiplier for ``model_id`` (0.10x unless overridden)."""
    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(
        model_id, _CACHE_READ_MULTIPLIER_DEFAULT
    )


def _cache_read_exceptions_text() -> str:
    """The per-model cache-read exceptions, rendered FROM the table above.

    ADR-149 Amendment 3 (S357): the report text is DERIVED, never
    re-listed by hand — the hand-written "0.025x on Fable 5.1" went stale
    on the next model with its own cache-read rate.
    """
    return ", ".join(
        "%gx on %s" % (mult, model_id)
        for model_id, mult in sorted(_CACHE_READ_MULTIPLIER_OVERRIDES.items())
    )



