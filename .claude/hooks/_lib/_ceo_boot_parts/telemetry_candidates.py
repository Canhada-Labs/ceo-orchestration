"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



# ---- Bench harness ---------------------------------------------------------

def _percentile(xs: List[float], p: float) -> float:
    """Stdlib percentile via sorted index. p in [0,100]. Empty → 0.0.

    Spec (PLAN-065 §4.3 + S82 brief): use ``sorted(arr)[int(0.95 * len(arr))]``
    style indexing — NOT numpy. With small N the index can hit an off-by-one
    near the upper bound; we use ``int(round((len(s)-1) * p/100))`` which is
    monotonic-correct for both N=5 and N=10.
    """
    if not xs:
        return 0.0
    s = sorted(xs)
    k = int(round((len(s) - 1) * p / 100.0))
    return s[k]


def _rss_kb_current() -> float:
    """Return current process RSS in KiB.

    Codex S82 P1 fix: ``resource.getrusage(RUSAGE_SELF).ru_maxrss`` returns
    BYTES on macOS but KiB on Linux. We normalize to KiB by detecting the
    platform. This is high-water mark for the process; deltas across runs
    are still meaningful as long as the platform's unit is consistent.
    """
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        # macOS: bytes → KiB
        return rss / 1024.0
    # Linux + most BSDs: already KiB
    return float(rss)


def bench(n_runs: int = 5, *, include_tier_a: bool = False) -> Dict[str, Any]:
    """Run the dispatcher N times. Report p50/p95 wall-clock, per-iter RSS, deltas.

    Output schema includes the legacy fields (``wall_clock_ms`` map, per-check
    p50/p95, tracemalloc current/peak) PLUS the PLAN-065 §4.3 spec fields
    (per-iter ``iterations`` list with ``iter``, ``duration_ms``, ``rss_kb``
    + summary dict with ``p50_ms``, ``p95_ms``, ``min_ms``, ``max_ms``,
    ``rss_delta_kb``).
    """
    wall_clocks: List[float] = []
    rss_per_iter: List[float] = []
    iterations: List[Dict[str, Any]] = []
    registry = list(TIER_S_CHECKS) + (list(TIER_A_CHECKS) if include_tier_a else [])
    per_check_durations: Dict[str, List[float]] = {name: [] for name, _ in registry}

    rss_before = _rss_kb_current()
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()
    for i in range(n_runs):
        t0 = time.perf_counter()
        results = dispatch_parallel(include_tier_a=include_tier_a)
        wc = (time.perf_counter() - t0) * 1000
        rss_now = _rss_kb_current()
        wall_clocks.append(wc)
        rss_per_iter.append(rss_now)
        iterations.append({
            "iter": i + 1,
            "duration_ms": round(wc, 2),
            "rss_kb": round(rss_now, 2),
        })
        for r in results:
            per_check_durations.setdefault(r.name, []).append(r.duration_ms)
    snap_after = tracemalloc.take_snapshot()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = _rss_kb_current()

    diff_stats = snap_after.compare_to(snap_before, "filename")
    py_delta_kb = sum(stat.size_diff for stat in diff_stats) / 1024.0

    return {
        "n_runs": n_runs,
        "include_tier_a": include_tier_a,
        "iterations": iterations,
        "wall_clock_ms": {
            "p50": _percentile(wall_clocks, 50),
            "p95": _percentile(wall_clocks, 95),
            "min": min(wall_clocks) if wall_clocks else 0.0,
            "max": max(wall_clocks) if wall_clocks else 0.0,
        },
        "summary": {
            "p50_ms": round(_percentile(wall_clocks, 50), 2),
            "p95_ms": round(_percentile(wall_clocks, 95), 2),
            "min_ms": round(min(wall_clocks), 2) if wall_clocks else 0.0,
            "max_ms": round(max(wall_clocks), 2) if wall_clocks else 0.0,
            "rss_delta_kb": round(rss_after - rss_before, 2),
        },
        "per_check_p95_ms": {name: _percentile(durs, 95) for name, durs in per_check_durations.items()},
        "per_check_p50_ms": {name: _percentile(durs, 50) for name, durs in per_check_durations.items()},
        "memory_python_delta_kb": round(py_delta_kb, 2),
        "tracemalloc_peak_kb": round(peak / 1024.0, 2),
        "tracemalloc_current_kb": round(current / 1024.0, 2),
    }


def render_bench_markdown(report: Dict[str, Any]) -> str:
    """Render bench report as a markdown table (PLAN-065 §4.3 spec).

    Header columns: iter # | duration_ms | RSS_kb. Summary row appended
    with p50/p95/min/max/RSS_delta. Returns the rendered string (caller
    writes to stdout).
    """
    lines = ["", "## /ceo-boot --bench", ""]
    lines.append(f"N={report['n_runs']}  include_tier_a={report.get('include_tier_a', False)}")
    lines.append("")
    lines.append("| iter | duration_ms | RSS_kb |")
    lines.append("|---|---|---|")
    for it in report.get("iterations", []):
        lines.append(f"| {it['iter']} | {it['duration_ms']:.1f} | {it['rss_kb']:.1f} |")
    s = report.get("summary", {})
    lines.append(
        f"| **summary** | p50={s.get('p50_ms', 0):.1f} / p95={s.get('p95_ms', 0):.1f}"
        f" / min={s.get('min_ms', 0):.1f} / max={s.get('max_ms', 0):.1f}"
        f" | rss_delta={s.get('rss_delta_kb', 0):.1f} |"
    )
    lines.append("")
    return "\n".join(lines)


# === PLAN-065 Phase 2 audit_emit wire =====================================
# Reality-Ledger fixture #4 closure (declared-but-not-wired). Pre-S82,
# ceo-boot.py shipped emit comments only. Phase 2 wires the actual call.
# Sec MF-3 field allowlist enforced ON THE EMIT SIDE (_lib/audit_emit.py).
# Caller passes only allowlisted fields; never raises on emit failure.
# Pre-canonical-ceremony the symbol is missing → hasattr() guard short-
# circuits silently (advisory log to stderr only when CEO_BOOT_DEBUG=1).


def _ceo_boot_session_id() -> str:
    """Derive session id from harness env or a stable fallback.

    Defense-in-depth: never raises. The session_id is used as a forensic
    correlator across the 15 Tier-S checks; it does NOT need to be
    cryptographically unique.
    """
    sid = os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CEO_SESSION_ID")
    if sid:
        return sid[:64]  # bound length defense-in-depth
    # Fallback: parent shell PID + start of audit-log mtime. Stable
    # within a session, advisory across sessions.
    try:
        return f"pid-{os.getppid()}-{int(AUDIT_LOG_DEFAULT.stat().st_mtime)}"
    except OSError:
        return f"pid-{os.getppid()}"


def _emit_ceo_boot_emitted_safe(
    *,
    gate_pass: bool,
    duration_ms: int,
    checks_total: int,
    checks_failed: int,
    cache_hit: bool = False,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_emitted. Fail-open contract.

    Pre-canonical-ceremony: hasattr() returns False, function is a no-op.
    Post-ceremony: emits the telemetry event with Sec MF-3 field allowlist
    enforced on the emit side.
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_emitted", None)
    if not callable(fn):
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "# ceo-boot: audit_emit.emit_ceo_boot_emitted not registered "
                "(canonical ceremony pending v1.12.0)\n"
            )
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            gate_pass=bool(gate_pass),
            duration_ms=int(duration_ms),
            checks_total=int(checks_total),
            checks_failed=int(checks_failed),
            cache_hit=bool(cache_hit),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)


def _emit_ceo_boot_check_skipped_safe(
    *,
    check_name: str,
    timeout_ms: int,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_check_skipped. Fail-open contract."""
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_check_skipped", None)
    if not callable(fn):
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            check_name=check_name,
            timeout_ms=int(timeout_ms),
        )
    except Exception:  # noqa: BLE001 — fail-open
        pass


# === END PLAN-065 Phase 2 audit_emit wire =================================


# === PLAN-078 Wave 5 — TaskCreate-candidate marker emit + dedup ============
# Layer A of the Wave 5 closure (per PLAN-078 §4 + Codex CDX-UNIQUE-02 +
# CDX-P0-03 + CDX-P1-04 + Perf PERF-P1-03). Writes a structured stdout
# marker block per top-3 high/medium recommendation when gate_pass=False,
# dedup'd by 12-hex subject_hash via a 24h TTL state file under
# `_lib/filelock`. The Claude orchestrator running /ceo-boot reads the
# marker blocks and invokes TaskCreate when the session offers it, or
# renders the candidates inline when it does not (the task tools are
# model-dependent since Claude Code 2.1.233 — commands/ceo-boot.md
# Step 4.5); this script never touches the TaskCreate harness primitive
# directly, so the marker format is the same either way. Audit emit goes through
# `audit_emit.emit_ceo_boot_task_candidate_emitted` (hasattr-guarded
# pre-canonical-ceremony per the W5 staging→canonical model).

# Default state path lives under the same project state dir as the cache
# (parity with audit-log.jsonl). Override `CEO_BOOT_TASK_STATE_PATH` for
# tests. Format: {"entries": [{"subject_hash": "...", "ts": <epoch>}, ...]}
# bounded to 256 entries (LRU evict on overflow).
TASK_EMIT_STATE_PATH_DEFAULT = (
    _rp.runtime_state_dir() / "state" / "ceo-boot-tasks-emitted.json"
)
TASK_EMIT_TTL_S = 24 * 60 * 60          # 24h dedup window
TASK_EMIT_TOP_N = 3                     # emit at most 3 markers per boot
TASK_EMIT_STATE_MAX_ENTRIES = 256       # bounded state size


def _task_emit_state_path() -> Path:
    """Resolve dedup state-file path at call time (env override-aware)."""
    override = os.environ.get("CEO_BOOT_TASK_STATE_PATH")
    if override:
        return Path(override)
    return TASK_EMIT_STATE_PATH_DEFAULT


def _subject_hash(subject: str) -> str:
    """Return a 12-hex-char prefix of sha256(subject) for dedup bookkeeping.

    The full subject text is NEVER persisted (Sec MF-3); the hash is the
    only stable identifier shared between the audit event and the state
    file. NFKC-normalize first so homoglyph variants collapse to the
    same dedup key (parity with `_sanitize_for_recs`).
    """
    safe = subject if isinstance(subject, str) else str(subject)
    try:
        safe = unicodedata.normalize("NFKC", safe)
    except (TypeError, ValueError):  # pragma: no cover — defensive
        pass
    digest = hashlib.sha256(safe.encode("utf-8", errors="replace")).hexdigest()
    return digest[:12]


def _load_task_emit_state(path: Path) -> Dict[str, Any]:
    """Load dedup state, prune entries older than TASK_EMIT_TTL_S.

    Fail-open: corrupt JSON / unreadable file → returns empty state. The
    caller persists the pruned state on next write so corruption is
    self-healing across boots.

    Codex CDX-W5-P1-04 closure: drop entries with non-finite timestamps
    (NaN / inf) and entries with timestamps in the future (NTP jump
    backward, deliberate clock skew). The TTL window is `[0, TTL)` —
    age must be a finite non-negative number strictly less than the
    TTL bound.
    """
    if not path.exists():
        return {"entries": []}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return {"entries": []}
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return {"entries": []}
    now = time.time()
    pruned: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        sh = entry.get("subject_hash")
        if not isinstance(sh, str) or not isinstance(ts, (int, float)):
            continue
        # Reject NaN / inf — float comparison NaN!=NaN always; inf age
        # would otherwise be retained as TTL-current.
        ts_f = float(ts)
        if ts_f != ts_f or ts_f in (float("inf"), float("-inf")):
            continue
        age = now - ts_f
        if 0 <= age < TASK_EMIT_TTL_S:
            pruned.append({"subject_hash": sh[:12], "ts": ts_f})
    # Bound state size — LRU keep most-recent.
    if len(pruned) > TASK_EMIT_STATE_MAX_ENTRIES:
        pruned.sort(key=lambda e: e["ts"], reverse=True)
        pruned = pruned[:TASK_EMIT_STATE_MAX_ENTRIES]
    return {"entries": pruned}


def _save_task_emit_state(path: Path, state: Dict[str, Any]) -> None:
    """Persist state atomically via temp-file + rename. Fail-open.

    Codex CDX-W5-P1-03 closure: `os.replace` is atomic but not
    crash-durable on macOS — if the box loses power between the rename
    and the buffer flush, the dedup record is lost. We `fsync(tmp_fd)`
    before the rename and best-effort `fsync` the parent directory after.
    Both fsyncs are wrapped — fsync failure must NOT block the user
    session (the dedup is advisory; over-emitting once on crash is
    acceptable, lost-update is not).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(state, separators=(",", ":")).encode("utf-8")
    try:
        # Write + fsync the data file before atomic rename.
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, payload)
            try:
                os.fsync(fd)
            except OSError:  # pragma: no cover — fsync best-effort
                pass
        finally:
            os.close(fd)
        os.replace(str(tmp), str(path))
        # Best-effort fsync of the parent directory so the rename
        # itself is durable. POSIX-only; NotImplementedError on win.
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            except OSError:  # pragma: no cover
                pass
            finally:
                os.close(dir_fd)
        except OSError:  # pragma: no cover — directory fsync optional
            pass
    except OSError:
        # Best-effort cleanup of the tmp file
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:  # pragma: no cover
            pass


def _is_subject_recent(state: Dict[str, Any], subject_hash: str) -> bool:
    """Return True if `subject_hash` is in state within TTL (already pruned by load)."""
    for entry in state.get("entries", []):
        if isinstance(entry, dict) and entry.get("subject_hash") == subject_hash:
            return True
    return False


# Codex CDX-W5-P1-05 closure: collapse interior whitespace in a marker
# subject so the `Subject:` line stays single-line. `_sanitize_for_recs`
# strips angle brackets + backticks but preserves `\n` / `\t` / multi-
# space, which can ambiguate the `<!-- /TASKCREATE-CANDIDATE -->`
# closing marker if a recommendation summary contains a literal newline.
# Bound to 200 chars (parity with `_sanitize_for_recs` length cap).
def _collapse_marker_subject(text: str) -> str:
    """Single-line, length-bounded subject for `Subject:` marker line.

    Python `re.sub(r"\\s+", " ", ...)` on a `str` matches Unicode
    whitespace (NBSP / em-space / narrow NBSP / line-tab / vertical-tab /
    form-feed in addition to ASCII), so the collapse is locale-safe.
    """
    if not isinstance(text, str):
        text = str(text)
    # Replace ALL whitespace runs (Unicode-aware) with a single space.
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]


def _emit_task_candidate_safe(
    *,
    rank: int,
    severity: str,
    subject_hash: str,
    awaiting_confirm: bool = False,
) -> None:
    """Wire-up to audit_emit.emit_ceo_boot_task_candidate_emitted. Fail-open.

    Pre-canonical-ceremony: hasattr() returns False, function is a no-op.
    Post-ceremony: emits the telemetry event with Sec MF-3 field allowlist
    enforced on the emit side (subject text NEVER leaves this script).
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_ceo_boot_task_candidate_emitted", None)
    if not callable(fn):
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            sys.stderr.write(
                "# ceo-boot: audit_emit.emit_ceo_boot_task_candidate_emitted "
                "not registered (canonical ceremony pending)\n"
            )
        return
    try:
        fn(
            session_id=_ceo_boot_session_id(),
            rank=int(rank),
            severity=str(severity),
            subject_hash=str(subject_hash),
            awaiting_confirm=bool(awaiting_confirm),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)
