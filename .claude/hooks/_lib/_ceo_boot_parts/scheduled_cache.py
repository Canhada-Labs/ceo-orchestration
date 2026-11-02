"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



def _sched_red_fetch_workflow_rows(
    basename: str, timeout_s: float
) -> Tuple[Optional[List[Any]], str]:
    """Newest runs of ONE workflow, ALL events and statuses (no server filter).

    Returns ``(rows, "")`` or ``(None, reason)``. History: S293 asked one
    repo-wide window; S317 asked per workflow but kept server filters
    (``status=completed``); S361 drops every server filter (measured
    non-deterministic, see the section header) and filters in the client.
    """
    if not _SCHED_RED_WF_NAME_RE.match(basename or ""):
        # Fail-closed on input: a basename this guard cannot vouch for never
        # reaches the URL (the path stays "no data", never "cured").
        return None, "unvouchable name"
    try:
        proc = subprocess.run(
            [
                "gh", "api",
                "repos/{owner}/{repo}/actions/workflows/"
                + basename
                + "/runs?per_page="
                + str(_SCHED_RED_PER_PAGE),
                "--jq",
                "[.workflow_runs[] | {path: .path, event: .event, "
                "status: .status, conclusion: .conclusion, "
                "created_at: .created_at}]",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(REPO_ROOT),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError:
        return None, "gh CLI unavailable"
    if proc.returncode != 0:
        first = next(
            (l.strip() for l in (proc.stderr or "").splitlines() if l.strip()),
            "",
        )
        return None, f"gh rc={proc.returncode}" + (f": {first}" if first else "")
    try:
        rows = json.loads(proc.stdout or "[]")
    except ValueError:
        return None, "unparseable gh payload"
    if not isinstance(rows, list):
        return None, "unparseable gh payload"
    return rows, ""


def _sched_red_fetch_all(
    paths: List[str], budget_s: float
) -> Dict[str, Tuple[Optional[List[Any]], str]]:
    """One fetch per workflow, in parallel, all inside ONE deadline."""
    deadline = time.monotonic() + budget_s

    def _one(path: str) -> Tuple[Optional[List[Any]], str]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "deadline"
        return _sched_red_fetch_workflow_rows(path.rsplit("/", 1)[-1], remaining)

    out: Dict[str, Tuple[Optional[List[Any]], str]] = {}
    pool = ThreadPoolExecutor(
        max_workers=max(1, min(_SCHED_RED_MAX_PARALLEL, len(paths)))
    )
    try:
        futs = {pool.submit(_one, p): p for p in paths}
        done, _pending = futures_wait(
            futs, timeout=max(0.0, deadline - time.monotonic())
        )
        for fut, p in futs.items():
            if fut not in done:
                out[p] = (None, "deadline")
                continue
            try:
                out[p] = fut.result()
            except Exception:  # noqa: BLE001 — a dead fetch is "no data"
                out[p] = (None, "error")
    finally:
        # Non-blocking: a gh process still running past the deadline is
        # killed by its own timeout; the check does not wait for it.
        pool.shutdown(wait=False, cancel_futures=True)
    return out


def _sched_red_classify(
    path: str, rows: List[Any], period_s: float, now: float
) -> Dict[str, Any]:
    """Detection AND cure out of ONE newest-first page of one workflow.

    state: ``uncovered`` (no completed scheduled run in the page) /
    ``stale`` (newest completed scheduled run older than FACTOR × period, or
    undated) / ``green`` / ``red`` / ``cured`` (red scheduled run followed by
    a newer completed run that is not red — S293 semantics, any event).
    """
    page = [
        r for r in rows
        if isinstance(r, dict) and str(r.get("path") or "") == path
    ]  # a mis-scoped row never decides anything
    idx = next(
        (
            i for i, r in enumerate(page)
            if r.get("event") == "schedule" and r.get("status") == "completed"
        ),
        None,
    )
    if idx is None:
        return {"state": "uncovered"}
    conclusion = str(page[idx].get("conclusion") or "")
    ts = _sched_red_parse_ts(page[idx].get("created_at"))
    limit_s = _SCHED_RED_STALE_FACTOR * period_s
    age_s = None if ts is None else max(0.0, now - ts)
    out: Dict[str, Any] = {
        "conclusion": conclusion,
        "age_days": None if age_s is None else round(age_s / _SCHED_RED_DAY_S, 1),
        "stale_after_days": round(limit_s / _SCHED_RED_DAY_S, 1),
    }
    if age_s is None or age_s > limit_s:
        out["state"] = "stale"
        return out
    if conclusion not in _SCHED_RED_BAD_CONCLUSIONS:
        out["state"] = "green"
        return out
    newer = page[:idx]
    for r in newer:  # newest-first: the newest COMPLETED newer run decides
        if r.get("status") != "completed":
            continue
        c = str(r.get("conclusion") or "")
        if c not in _SCHED_RED_BAD_CONCLUSIONS:
            out["state"] = "cured"
            out["cured_by"] = c
            return out
        break
    out["state"] = "red"
    out["newer_not_completed"] = sum(
        1 for r in newer if r.get("status") != "completed"
    )
    return out


def check_scheduled_workflows_red() -> Tuple[str, str, Any]:
    """S292 — 24th Tier-S check: latest scheduled-run conclusion per workflow.

    red    — ≥1 scheduled workflow whose newest COMPLETED scheduled run is
             FRESH (cron-derived guard) and concluded failure/timed_out/
             startup_failure, with no newer completed non-red run in the
             SAME page (S293 cure semantics, any event); a red whose cure
             cannot be verified (newer runs still in progress) says so;
    yellow — no data for some workflow (gh missing/timeout/error/
             unparseable), no scheduled run in its page, or stale data —
             never green on missing data, never red on old data;
    green  — every scheduled workflow green (or cured) at a fresh latest
             scheduled run, no scheduled workflows at all, or explicit
             operator disable.
    ADVISORY — never blocks the session.
    """
    if os.environ.get("CEO_BOOT_SCHED_RED", "") == "0":
        return (
            "green",
            "scheduled-red check disabled (CEO_BOOT_SCHED_RED=0)",
            {"disabled": True},
        )
    workflows = _scheduled_workflows()
    scheduled = list(workflows)
    if not scheduled:
        return "green", "no scheduled workflows", {"scheduled": []}
    budget_s = _sched_red_budget_s()
    fetched = _sched_red_fetch_all(scheduled, budget_s)
    now = _sched_red_now()

    no_data: Dict[str, str] = {}
    states: Dict[str, Dict[str, Any]] = {}
    for path in scheduled:
        rows, reason = fetched.get(path, (None, "deadline"))
        if rows is None:
            no_data[path] = _sanitize_for_recs(reason)[:120]
            continue
        states[path] = _sched_red_classify(
            path, rows, _sched_red_period_s(workflows[path]), now
        )
    if any(r in ("timeout", "deadline") for r in no_data.values()):
        _emit_ceo_boot_check_skipped_safe(
            check_name="scheduled_workflows_red",
            timeout_ms=int(budget_s * 1000),
        )

    def _of(state: str) -> List[str]:
        return sorted(p for p, s in states.items() if s["state"] == state)

    def _names(paths: List[str]) -> str:
        return ", ".join(p.rsplit("/", 1)[-1] for p in paths)

    red, uncovered, stale = _of("red"), _of("uncovered"), _of("stale")
    cured = {p: states[p]["cured_by"] for p in _of("cured")}
    unverified = [p for p in red if states[p].get("newer_not_completed")]
    detail = {
        "scheduled": scheduled,
        "mode": "per_workflow_unfiltered",
        "per_page": _SCHED_RED_PER_PAGE,
        "budget_s": budget_s,
        "latest": {
            p: s["conclusion"] for p, s in states.items() if "conclusion" in s
        },
        "red": red,
        "cure_unverified": unverified,
        "cured_pending_cron": cured,
        "stale": {p: states[p] for p in stale},
        "no_recent_scheduled_run": uncovered,
        "no_data": no_data,
    }
    cured_note = (
        " ({0} cured post-red by a newer completed run; awaiting next "
        "cron)".format(len(cured))
        if cured
        else ""
    )
    gaps: List[str] = []
    if stale:
        gaps.append(
            "{0} stale (latest scheduled run older than the cron allows): "
            "{1}".format(len(stale), ", ".join(
                "{0} {1}d ago {2}".format(
                    p.rsplit("/", 1)[-1],
                    states[p]["age_days"] if states[p]["age_days"] is not None
                    else "?",
                    states[p]["conclusion"] or "?",
                )
                for p in stale
            ))
        )
    if uncovered:
        gaps.append("{0} with no scheduled run in the last {1} runs: {2}".format(
            len(uncovered), _SCHED_RED_PER_PAGE, _names(uncovered)))
    if no_data:
        gaps.append("{0} without data: {1}".format(
            len(no_data), _names(sorted(no_data))))
    if red:
        # (f) the cure check is part of the SAME response; when it cannot be
        # concluded (newer runs not finished) the summary SAYS so, first.
        verified = (
            "cure NOT verified for {0} (newer run still in progress)".format(
                _names(unverified))
            if unverified
            else "no newer completed run"
        )
        return (
            "red",
            _sanitize_for_recs(
                f"{len(red)} scheduled workflow(s) red at latest run "
                f"({verified}): {_names(red)}"
                + "".join("; " + g for g in gaps) + cured_note
            )[:200],
            detail,
        )
    if no_data and not states:
        reasons = sorted(set(no_data.values()))
        why = reasons[0] if len(reasons) == 1 else "mixed errors"
        if why in ("timeout", "deadline"):
            why = f"gh timeout >{budget_s:.1f}s"
        return (
            "yellow",
            _sanitize_for_recs(
                f"no data — {why} ({len(scheduled)} scheduled workflow(s) "
                f"unwatched; set CEO_BOOT_SCHED_RED=0 to silence)"
            )[:200],
            detail,
        )
    ok = len(scheduled) - len(stale) - len(uncovered) - len(no_data)
    if gaps:
        return (
            "yellow",
            _sanitize_for_recs(
                f"{ok}/{len(scheduled)} green at a fresh latest run; "
                + "; ".join(gaps) + cured_note
            )[:200],
            detail,
        )
    if cured:
        return (
            "green",
            _sanitize_for_recs(
                f"{len(scheduled)}/{len(scheduled)} scheduled workflows "
                f"healthy{cured_note}"
            )[:200],
            detail,
        )
    return (
        "green",
        f"{len(scheduled)}/{len(scheduled)} scheduled workflows green at "
        f"latest run",
        detail,
    )


TIER_S_CHECKS: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = [
    ("plans_executing", check_plans_executing),
    ("plans_reviewed_pending", check_plans_reviewed_pending),
    ("plans_stranded_executing", check_plans_stranded_executing),
    ("plans_draft", check_plans_draft),
    ("audit_log_freshness", check_audit_log_freshness),
    ("dispatch_count_24h", check_dispatch_count_24h),
    ("skill_unknown_ratio", check_skill_unknown_ratio),
    ("governance_validate", check_governance_validate),
    # PLAN-082 Codex Item D: `hook_test_baseline` renamed to `hook_live_smoke`
    # — the check now performs a live hook smoke (settings.json parse + file
    # existence + py_compile) rather than reading a pytest-baseline cache that
    # was never populated. Old function symbol preserved as alias for tests.
    ("hook_live_smoke", check_hook_live_smoke),
    ("audit_v3_backlog", check_audit_v3_backlog),
    ("sentinels_pending_gpg", check_sentinels_pending_gpg),
    ("rc_hold_aged", check_rc_hold_aged),
    ("cost_24h_usd", check_cost_24h_usd),
    ("active_plan_burn_ratio", check_active_plan_burn_ratio),
    ("adrs_stale_proposed", check_adrs_stale_proposed),
    # PLAN-091 Wave A.1 — 16th Tier-S check. Delegates to standalone hook
    # module `.claude/hooks/check_tier_policy_misrouting_24h.py` per the
    # PLAN-088 §AC11 18-check target.
    ("tier_policy_misrouting_24h", check_tier_policy_misrouting_24h),
    # PLAN-093 Wave C.2 — 17th Tier-S check: prompt-cache hit-rate
    # detection emitting `cache_discipline_alerted` on threshold breach.
    ("cache_discipline_alerted", check_cache_discipline_alerted),
    # PLAN-093 Wave C.5/C.6 — 18th Tier-S check: 4-persona × 4-task coverage
    # matrix at 24h cadence (session-smoke). S127 cadence-amendment (Codex R2
    # `019e33a3` AMEND): demoted to permanent observability, never red.
    ("ceo_boot_persona_coverage_score", check_ceo_boot_persona_coverage_score),
    # S127 cadence-amendment — 19th Tier-S check: same matrix at 168h cadence
    # (trend / chronic-atrophy signal). Phase 1: observability-only, never red.
    # Phase 2 (PLAN-104-persona-demand-ledger): RED authority activated once
    # `eligible_demand_events` is populated from the demand ledger.
    ("persona_atrophy_7d", check_persona_atrophy_7d),
    # PLAN-106 Wave F.2 — 20th Tier-S check. Wires the standalone
    # `.claude/scripts/check-confidence-gate-drift.py` module's
    # `detect_drift_7d()` importable into the parallel registry per
    # ADR-019-AMEND-1 §6 (7d rolling FPR > 2% advisory). Read-only;
    # the underlying script's `--emit` flag remains the canonical
    # emission surface for `confidence_gate_fp_drift_detected`.
    ("confidence_gate_drift_7d", check_confidence_gate_drift_7d),
    # PLAN-135 W1 S3 — 21st Tier-S check: settings/env tamper tripwires
    # over the RESOLVED multi-layer settings (shared _lib/effective_config;
    # user/project/local/managed incl. the sentinel-blind
    # settings.local.json) + the import-time env snapshot (trusted_env
    # pattern). Classes (a)-(e) per THREAT-MODEL-WORKSHEET.md §2; closed-
    # enum `settings_tamper_detected` emit per class. ADVISORY fail-open:
    # infra error → yellow + stderr breadcrumb, never crashes, never blocks.
    ("settings_tamper_tripwires", check_settings_tamper_tripwires),
    # PLAN-153 Wave E item 2 — 22nd Tier-S check: fail-open rail liveness
    # over a 7d audit-log window (S254 lesson: silence from a fail-open
    # rail is not health; all-fail-open window → red, no signal → yellow).
    ("failopen_rail_liveness_7d", check_failopen_rail_liveness_7d),
    # PLAN-153 Wave E item 1 wire — 23rd Tier-S check: static harness-config
    # gate subprocess (file-existence guarded; green "not installed" until
    # the SENT-E ceremony lands check_harness_config.py canonical).
    ("harness_config_gate", check_harness_config_gate),
    # S292 — 24th Tier-S check: scheduled workflows whose latest scheduled
    # run is red (6th occurrence of the invisible-scheduled-red class).
    ("scheduled_workflows_red", check_scheduled_workflows_red),
    # Item 14 (c) of the 1.4.4 backlog — 25th Tier-S check: the main checkout off its
    # default branch or with a detached HEAD (2 occurrences in S363).
    ("main_checkout_state", check_main_checkout_state),
]

assert len(TIER_S_CHECKS) == 25, f"Expected 25 Tier-S checks, got {len(TIER_S_CHECKS)}"


TIER_A_CHECKS: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = [
    ("tier_a_debate_transcripts", check_tier_a_debate_transcripts),
    ("tier_a_lessons_30d", check_tier_a_lessons_30d),
    ("tier_a_spec_version_drift", check_tier_a_spec_version_drift),
    ("tier_a_npm_version_match", check_tier_a_npm_version_match),
    ("tier_a_waivers_count", check_tier_a_waivers_count),
    ("tier_a_adrs_recent_status", check_tier_a_adrs_recent_status),
    ("tier_a_cache_hit_rate_24h", check_tier_a_cache_hit_rate_24h),
    ("tier_a_hook_test_baseline_age", check_tier_a_hook_test_baseline_age),
    ("tier_a_sentinel_signers_tracked", check_tier_a_sentinel_signers_tracked),
    ("tier_a_gitignore_state_excluded", check_tier_a_gitignore_state_excluded),
    ("tier_a_model_currency", check_tier_a_model_currency),  # PLAN-176 W3a
]

assert len(TIER_A_CHECKS) == 11, f"Expected 11 Tier-A checks, got {len(TIER_A_CHECKS)}"


# Verbose-mode aggregate budget: extends Tier-S 5s window to 10s when
# Tier-A is dispatched alongside (PLAN-065 §4.3.3).
AGGREGATE_TIMEOUT_VERBOSE_S = 10.0


# ---- Dispatcher ------------------------------------------------------------

def _wrap_check(name: str, fn: Callable[[], Tuple[str, str, Any]]) -> CheckResult:
    t0 = time.perf_counter()
    try:
        status, summary, detail = fn()
        dur = (time.perf_counter() - t0) * 1000
        return CheckResult(name, status, summary, dur, detail)
    except Exception as e:  # noqa: BLE001 (PoC fail-soft)
        dur = (time.perf_counter() - t0) * 1000
        return CheckResult(name, "error", f"{type(e).__name__}: {e}", dur, None)


def dispatch_parallel(
    *,
    include_tier_a: bool = False,
    aggregate_timeout_s: Optional[float] = None,
) -> List[CheckResult]:
    """Dispatch Tier-S (and optionally Tier-A) checks in parallel via as_completed.

    Codex S82 P0 #2 fix: previous impl iterated future_to_name.items() and
    called fut.result(timeout=PER_CHECK_TIMEOUT_S) sequentially — so the
    500ms started counting when each future was *observed*, not when it
    started running. Timeouts cascaded and the per-check budget was
    fictional under load. New impl uses as_completed() with the AGGREGATE
    budget; per-check budget becomes a soft annotation (subprocess timeouts
    inside each check enforce real CPU/IO ceilings, e.g. governance_validate
    has subprocess timeout=4.0).

    Tier-A extension (PLAN-065 §4.3.3): when ``include_tier_a=True``,
    dispatcher also enqueues TIER_A_CHECKS and the aggregate budget
    defaults to AGGREGATE_TIMEOUT_VERBOSE_S (10s).

    Pool lifecycle (per PLAN-087 A.6 / `F-A-CR-D0012` P2): the
    ``ThreadPoolExecutor`` is NOT used as a context manager because
    ``with`` exit calls ``shutdown(wait=True)`` which blocks on
    long-running futures past the aggregate timeout. The explicit
    ``shutdown(wait=False, cancel_futures=True)`` in the ``finally``
    block releases the pool immediately and cancels any futures that
    have not yet started; in-flight futures continue to run on their
    daemon threads but their results are dropped (the aggregate
    timeout has already produced their `AGG_TIMEOUT` rows). Python
    3.9+ ``cancel_futures`` parameter required; the project min
    Python is 3.9 per ADR-002.
    """
    registry: List[Tuple[str, Callable[[], Tuple[str, str, Any]]]] = list(TIER_S_CHECKS)
    if include_tier_a:
        registry = registry + list(TIER_A_CHECKS)
    if aggregate_timeout_s is None:
        aggregate_timeout_s = (
            AGGREGATE_TIMEOUT_VERBOSE_S if include_tier_a else AGGREGATE_TIMEOUT_S
        )

    results_by_name: Dict[str, CheckResult] = {}
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        future_to_name = {
            pool.submit(_wrap_check, name, fn): name for name, fn in registry
        }
        try:
            for fut in as_completed(future_to_name, timeout=aggregate_timeout_s):
                name = future_to_name[fut]
                try:
                    res = fut.result()  # already done, instant
                except Exception as e:  # noqa: BLE001
                    res = CheckResult(name, "error", f"{type(e).__name__}: {e}", 0.0, None)
                # Soft per-check ceiling: annotate slow but green checks.
                budget_s = PER_CHECK_TIMEOUT_OVERRIDES_S.get(name, PER_CHECK_TIMEOUT_S)
                if res.duration_ms > budget_s * 1000 and res.status == "green":
                    res.summary = (
                        f"{res.summary} (slow {res.duration_ms:.0f}ms > "
                        f"budget {int(budget_s * 1000)}ms)"
                    )
                results_by_name[name] = res
        except FuturesTimeout:
            pass  # aggregate exceeded — handled below

        # Mark non-completed as aggregate-timeout (Codex P0 #2: explicit, not silent)
        for fut, name in future_to_name.items():
            if name not in results_by_name:
                ms = int(aggregate_timeout_s * 1000)
                results_by_name[name] = CheckResult(
                    name, "timeout",
                    f"AGG_TIMEOUT (>{ms}ms aggregate)",
                    aggregate_timeout_s * 1000, None,
                )
                _emit_ceo_boot_check_skipped_safe(
                    check_name=name,
                    timeout_ms=ms,
                )
    finally:
        # See docstring "Pool lifecycle" — non-blocking shutdown is
        # required to honor the aggregate timeout.
        pool.shutdown(wait=False, cancel_futures=True)

    # Codex S82 post-patch fix: emit results in registry order for CR-N7
    # stability across runs (was completion-order, non-deterministic).
    return [results_by_name[name] for name, _ in registry if name in results_by_name]


# ---- Cached path (PLAN-065 §4.3.2 real per-key cache) -------------------

def _cache_key_raw() -> str:
    """Compose raw cache key string from (HEAD + audit-log mtime + size).

    Per Codex S82 P1 #5 the sub-second precision is NOT required; we use
    integer seconds + size-in-bytes which together provide collision-safe
    invalidation when the audit-log is appended.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=1.0,
        )
        head = proc.stdout.strip() or "nogit"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        head = "nogit"
    try:
        st = AUDIT_LOG_DEFAULT.stat()
        mtime = int(st.st_mtime)
        size = int(st.st_size)
    except OSError:
        mtime, size = 0, 0
    return f"{head}:{mtime}:{size}"


def _cache_key() -> str:
    """SHA-256 short-hash of raw cache key (filename-safe + bounded length)."""
    raw = _cache_key_raw()
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:32]


def _cache_path_for_key(key: str) -> Path:
    """Resolve cache file path for a given key under the active cache dir."""
    return _cache_dir() / f"{key}.json"


def cache_lru_evict() -> None:
    """LRU-evict oldest cache files when dir size exceeds CACHE_DIR_SIZE_CAP_BYTES.

    Fail-open: any OSError silently breadcrumbs to stderr and returns.
    Atime-aware where supported; mtime fallback (atime is updated by reads
    on most filesystems but POSIX `relatime` may suppress it).
    """
    cdir = _cache_dir()
    if not cdir.exists():
        return
    try:
        entries: List[Tuple[float, int, Path]] = []
        total = 0
        for f in cdir.glob("*.json"):
            try:
                st = f.stat()
            except OSError:
                continue
            entries.append((st.st_atime, st.st_size, f))
            total += st.st_size
        if total <= CACHE_DIR_SIZE_CAP_BYTES:
            return
        # Evict oldest-first until under cap.
        entries.sort(key=lambda e: e[0])
        for atime, size, path in entries:
            if total <= CACHE_DIR_SIZE_CAP_BYTES:
                break
            try:
                path.unlink()
                total -= size
            except OSError:
                continue
    except OSError as e:
        sys.stderr.write(f"# ceo-boot cache LRU evict failed: {type(e).__name__}\n")
