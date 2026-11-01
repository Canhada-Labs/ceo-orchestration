"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



def cached_load() -> Tuple[bool, Any]:
    """Per-key cache load. Returns (hit, payload).

    Hit semantics: cache file exists for current key, mtime within TTL,
    file size within cap, JSON parses cleanly. Otherwise miss (fail-open).
    Atime is touched on hit (LRU signal).
    """
    key = _cache_key()
    path = _cache_path_for_key(key)
    if not path.exists():
        return False, None
    try:
        st = path.stat()
        if st.st_size > CACHE_FILE_SIZE_CAP_BYTES:
            return False, None  # corrupt / oversized — treat as miss
        if (time.time() - st.st_mtime) > CACHE_TTL_S:
            return False, None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, None
    # Defense-in-depth: validate cache_key matches (mtime alone could
    # collide if filesystem is restored from backup).
    if data.get("cache_key") != key:
        return False, None
    # Touch atime for LRU signal (best-effort; ignore filesystem refusal).
    try:
        os.utime(path, None)
    except OSError:
        pass
    return True, data


def cached_store(results: List[CheckResult]) -> None:
    """Write digest to per-key cache. Atomic (temp + rename); fail-open.

    Codex S82 P1 fix: previous impl had unguarded mkdir + write_text;
    permission/lock/filesystem errors aborted boot post-checks pre-output.
    Now wraps all I/O in try/except; on failure emits stderr breadcrumb
    and returns silently (cache miss next boot, main path unaffected).

    Schema parity: payload includes gate_pass / checks_total / checks_failed
    / recommendations / results — identical shape to the live --json output
    so adopters get the same payload from cache-hit and fresh dispatch.
    """
    cdir = _cache_dir()
    key = _cache_key()
    target = _cache_path_for_key(key)
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        failed = sum(1 for r in results if r.status in ("red", "error", "timeout"))
        gate_pass = (failed == 0)
        payload = {
            "cache_key": key,
            "ts": time.time(),
            "gate_pass": gate_pass,
            "checks_total": len(results),
            "checks_failed": failed,
            "recommendations": _make_recommendations(results),
            "results": [
                {"name": r.name, "status": r.status, "summary": r.summary, "duration_ms": r.duration_ms}
                for r in results
            ],
        }
        body = json.dumps(payload)
        if len(body.encode("utf-8")) > CACHE_FILE_SIZE_CAP_BYTES:
            # Drop the recommendations + heavy detail to fit the cap.
            payload["recommendations"] = []
            body = json.dumps(payload)
        # Atomic write: temp file + rename.
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(body, encoding="utf-8")
        os.replace(tmp, target)
        # Best-effort LRU eviction (post-write, never blocks).
        cache_lru_evict()
    except (OSError, PermissionError, json.JSONDecodeError) as e:
        sys.stderr.write(f"# ceo-boot cache-store failed (fail-open): {type(e).__name__}\n")


# ---- Recommendations engine (PLAN-065 §4.3 Phase 3-D) ---------------------

# PLAN-165 W2 T2.1 (design decision D3) — night-mode posture advisory.
#
# The advisory derives from the RESOLVER (`_lib/effective_config.
# resolve_settings`), never from the night-mode marker: marker and
# settings are two sources of truth that can desync (crash between the
# two writes, Owner hand-editing the overlay). The marker at
# `.claude/state/night-mode.json` is DECORATION only — it enriches the
# text iff it parses; a missing/corrupt marker never changes whether the
# line renders.
#
# Advisory contract: this is a recommendation entry, NEVER a check row —
# it can never go red, never flips gate_pass, never blocks boot. It is
# fail-OPEN end to end: any exception skips the line silently (stderr
# breadcrumb only under CEO_BOOT_DEBUG=1).
#
# Sort key "008-*" lands after the 005/006/007 rail-integrity rules and
# before 01-owner-sentinels (lexicographic "007" < "008" < "01-"), so a
# non-ratified posture survives the recs[:5] cap without restructuring
# the cap. Shared helper (single source of the sort key + text) so the
# two hand-mirrored pipelines — `_make_recommendations` and
# `_recommendations_with_severity` — cannot drift on this rule.
#
# "Ratified" (NM-06, round-2 security review): the ratified posture is
# what the Owner tracked in git — the PROJECT layer's own
# ``permissions.defaultMode`` — never a hardcoded literal. The constant
# below is only the FALLBACK for when the tracked project settings do
# not declare a defaultMode (the harness default posture). The advisory
# renders ONLY when an OVERLAY layer ("local" or "user") wins the
# ``permissions`` key AND its value differs from the project-ratified
# value; if the project (or managed) layer itself wins, its value IS the
# ratified posture and nothing renders — a repo whose tracked
# settings.json ratifies acceptEdits/plan must never burn a rec slot on
# a false "not the ratified" claim about the Owner's own choice.
_NIGHT_MODE_RATIFIED_FALLBACK_MODE = "manual"
_NIGHT_MODE_OVERLAY_LAYERS = ("local", "user")
_NIGHT_MODE_REC_SORT_KEY = "008-night-mode"


def _night_mode_project_root() -> Path:
    """Project root for the posture advisory, resolved at CALL time.

    Prefers ``CLAUDE_PROJECT_DIR`` (same pattern as ``main()``'s
    project_dir resolution) and falls back to ``REPO_ROOT``. Call-time
    resolution — never an import-time constant — is what keeps this rule
    hermetic under ``TestEnvContext`` (which points CLAUDE_PROJECT_DIR at
    a sandbox project): the recommendations pipelines are exercised by
    many unrelated suites, and an import-time anchor on the live repo
    would make their exact-output assertions depend on whether night-mode
    happens to be armed on the developer machine (PLAN-165 T1.3 class).
    """
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env_root) if env_root else REPO_ROOT


def _night_mode_marker_note() -> str:
    """Decoration-only marker suffix; empty on ANY failure (fail-open)."""
    try:
        marker_file = (
            _night_mode_project_root() / ".claude" / "state" / "night-mode.json"
        )
        marker = json.loads(marker_file.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            return ""
        ts = marker.get("ts")
        armed = (
            f", armed {_sanitize_for_recs(str(ts))}"
            if isinstance(ts, str) and ts else ""
        )
        return f" [night-mode marker present{armed}]"
    except Exception:
        return ""


def _night_mode_ratified_mode(resolved: Dict[str, Any]) -> str:
    """The Owner-ratified posture: PROJECT layer's ``permissions.defaultMode``.

    NM-06: "ratified" is derived from the tracked project layer of the
    ``resolve_settings`` payload, never from a hardcoded literal. Falls
    back to ``_NIGHT_MODE_RATIFIED_FALLBACK_MODE`` (the harness default)
    when the project layer does not declare a string defaultMode.
    """
    layers = resolved.get("layers")
    if isinstance(layers, list):
        for layer in layers:
            if not isinstance(layer, dict) or layer.get("name") != "project":
                continue
            data = layer.get("data")
            perms = data.get("permissions") if isinstance(data, dict) else None
            value = perms.get("defaultMode") if isinstance(perms, dict) else None
            if isinstance(value, str) and value:
                return value
    return _NIGHT_MODE_RATIFIED_FALLBACK_MODE


def _night_mode_advisory_rec() -> Optional[Tuple[str, str]]:
    """Return the ("008-night-mode", text) rec pair, or None.

    Renders iff an OVERLAY layer ("local"/"user") wins the resolver's
    ``permissions`` key with a string ``defaultMode`` that differs from
    the project-layer-ratified value (``_night_mode_ratified_mode``). A
    winning project (or managed) layer never renders: its value IS the
    ratified posture (NM-06). Fail-OPEN: any exception (resolver import
    gap, resolver blow-up, filesystem error) returns None so the boot
    digest is never blocked by this advisory.
    """
    try:
        if _effective_config is None:
            return None
        resolved = _effective_config.resolve_settings(_night_mode_project_root())
        effective = resolved.get("effective")
        perms = (
            effective.get("permissions") if isinstance(effective, dict) else None
        )
        mode = perms.get("defaultMode") if isinstance(perms, dict) else None
        if not isinstance(mode, str):
            return None
        sources = resolved.get("sources")
        layer = sources.get("permissions") if isinstance(sources, dict) else None
        # NM-06: only an overlay layer can contradict the ratified
        # posture. Project/managed winner (or no winner at all) ⇒ silent.
        if layer not in _NIGHT_MODE_OVERLAY_LAYERS:
            return None
        ratified = _night_mode_ratified_mode(resolved)
        if mode == ratified:
            return None
        layer_note = f" (layer: {_sanitize_for_recs(str(layer))})"
        return (
            _NIGHT_MODE_REC_SORT_KEY,
            f"Session permission posture is "
            f"'{_sanitize_for_recs(mode)}'{layer_note}, not the ratified "
            f"'{_sanitize_for_recs(ratified)}'"
            f"{_night_mode_marker_note()} — run /night-mode status "
            f"(or /night-mode off) if autonomy is no longer intended",
        )
    except Exception as exc:  # fail-OPEN: advisory must never block boot
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            print(
                "[ceo-boot] night-mode advisory skipped (fail-open): "
                f"{type(exc).__name__}",
                file=sys.stderr,
            )
        return None


def _make_recommendations(results: List[CheckResult]) -> List[str]:
    """Rule-based prioritizer ≤5 actionable items (Sec MF-4 sanitized).

    Deterministic ordering (CR-N7): lex-sort by category prefix so ``--json``
    is stable across runs.
    """
    recs: List[Tuple[str, str]] = []  # (sort_key, formatted)
    by_name: Dict[str, CheckResult] = {r.name: r for r in results}

    # Codex S82 P1 fix: recs engine ignored timeout/error checks. Since those
    # flip gate_pass=False, they MUST surface as top-priority recommendations.
    #
    # Codex CDX-W5-iter3-P1 closure: the original `_NAMED_RULES` skip
    # was over-engineered defense against duplicate emit — but the named
    # rule branches below only fire on `status in {yellow, red}`. A named
    # check that times out (status "timeout"/"error") therefore matched
    # NEITHER branch, producing a silent gap where gate_pass=False but
    # zero recommendation surfaced. We now emit the 00-* row for every
    # failing check; the named branches can never co-fire (their `status`
    # gate is incompatible with timeout/error), so dedup is moot.
    failing = sorted(
        (r for r in results if r.status in ("timeout", "error")),
        key=lambda r: r.name,
    )
    for r in failing[:3]:  # cap at 3 to leave room for named rules
        recs.append((
            f"00-{r.name}-{r.status}",  # sort BEFORE 01-owner-sentinels
            f"Check '{r.name}' {r.status}: {_sanitize_for_recs(r.summary)} "
            f"(blocks gate_pass)",
        ))

    # PLAN-135 W1 S3 — settings/env tamper tripwires (rail integrity).
    # Sort key "005-*" lands AFTER the 00-* gate-blockers and BEFORE
    # 01-owner-sentinels (lexicographic: "00-" < "005" < "01-"): a fired
    # tripwire means every other signal on this digest may already be
    # produced by a disarmed/redirected rail. Only closed-enum class
    # names reach the rendered text (finding detail can embed env values).
    tamper = by_name.get("settings_tamper_tripwires")
    if tamper and tamper.status == "red" and tamper.detail:
        items = tamper.detail if isinstance(tamper.detail, list) else []
        classes = sorted({
            str(f.get("class", ""))
            for f in items
            if isinstance(f, dict) and f.get("class")
        })
        if classes:
            preview = _sanitize_for_recs(", ".join(classes[:3]))
            recs.append((
                "005-settings-tamper",
                f"Settings/env tamper tripwire(s) fired ({len(items)}): "
                f"{preview}{'...' if len(classes) > 3 else ''} — inspect "
                f"settings layers + env before trusting this session",
            ))

    # PLAN-153 Wave E item 2 — fail-open rail liveness (S254 class).
    # Sort key "006-*": after 005-settings-tamper, before 01-owner-sentinels
    # (a rail that fail-opened all window means its guarantees were absent
    # for every edit it should have reviewed).
    liveness = by_name.get("failopen_rail_liveness_7d")
    if liveness and liveness.status == "red":
        recs.append((
            "006-failopen-rail",
            f"Fail-open security rail fail-opened on EVERY invocation in "
            f"window: {_sanitize_for_recs(liveness.summary)} — restore the "
            f"rail dependency (S254 class) before trusting its silence",
        ))

    # PLAN-153 Wave E item 1 wire — static harness-config gate red.
    gate = by_name.get("harness_config_gate")
    if gate and gate.status == "red":
        recs.append((
            "007-harness-config",
            f"Harness-config gate FAIL: {_sanitize_for_recs(gate.summary)} "
            f"— a registered hook may not resolve at runtime (dead rail)",
        ))

    # S292 — scheduled workflows red at latest run (invisible-red class).
    sched = by_name.get("scheduled_workflows_red")
    if sched and sched.status == "red":
        recs.append((
            "008-scheduled-red",
            f"Scheduled workflow(s) red: {_sanitize_for_recs(sched.summary)} "
            f"— schedule-only gates never surface in push CI; triage now",
        ))

    # PLAN-165 W2 T2.1 — night-mode posture advisory (resolver-derived,
    # D3). Shared helper = same sort key + same text as the
    # `_recommendations_with_severity` mirror below, so the two pipelines
    # never drift on this rule. Fail-open: helper returns None on any
    # exception; advisory only, never a check row, never blocks boot.
    night_mode_rec = _night_mode_advisory_rec()
    if night_mode_rec:
        recs.append(night_mode_rec)

    # Owner-pending GPG sentinels — highest priority (HARD blocker for ceremony)
    sent = by_name.get("sentinels_pending_gpg")
    if sent and sent.status == "yellow" and sent.detail:
        items = sent.detail if isinstance(sent.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "01-owner-sentinels",
                f"Owner GPG sign pending: {len(items)} sentinels ({preview}{'...' if len(items) > 3 else ''})",
            ))

    # Stranded executing plans (no commits in 24h)
    stranded = by_name.get("plans_stranded_executing")
    if stranded and stranded.status == "red" and stranded.detail:
        items = stranded.detail if isinstance(stranded.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "02-stranded-plans",
                f"Stranded executing plans (>24h no commits): {preview}",
            ))

    # Skill-unknown ratio > threshold
    skill = by_name.get("skill_unknown_ratio")
    if skill and skill.status == "red":
        recs.append((
            "03-skill-unknown",
            f"Spawn dispatch skill=unknown ratio elevated: {_sanitize_for_recs(skill.summary)}",
        ))

    # Audit-v3 backlog open
    av3 = by_name.get("audit_v3_backlog")
    if av3 and av3.status == "yellow" and av3.detail:
        items = av3.detail if isinstance(av3.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "04-audit-v3-backlog",
                f"Audit-v3 backlog open ({len(items)}): {preview}",
            ))

    # ADRs stale-proposed >30d
    adrs = by_name.get("adrs_stale_proposed")
    if adrs and adrs.status == "yellow" and adrs.detail:
        items = adrs.detail if isinstance(adrs.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "05-adrs-stale",
                f"ADRs PROPOSED >30d ({len(items)}): {preview} — promote or retract",
            ))

    # Sort by deterministic key (CR-N7) and cap at 5
    recs.sort(key=lambda x: x[0])
    return [text for _, text in recs[:5]]


# PLAN-078 Wave 5 — severity-aware view of the recommendations engine.
# Mirrors `_make_recommendations` ordering exactly (same sort key + ≤5 cap)
# but exposes the (sort_key, text, severity) triple so the marker emitter
# can filter by severity≥medium without re-classifying. Severity buckets
# track the rule rank assigned in `_make_recommendations`:
#
#   00-* (timeout/error gate-blockers) → high
#   005-settings-tamper                → high (PLAN-135 W1 S3 rail integrity)
#   008-night-mode                     → high (PLAN-165 W2 T2.1 posture advisory)
#   01-owner-sentinels                 → high
#   02-stranded-plans                  → high
#   03-skill-unknown                   → medium
#   04-audit-v3-backlog                → medium
#   05-adrs-stale                      → low
#
# Anything else (future rules) defaults to "low" — caller policy is to
# only emit markers for medium/high, so unknown future rules are silent
# until the mapping is updated. Codex CDX-P1-04 closure: this helper is
# deterministic + side-effect-free; the marker emitter consumes the
# triple and never mutates `_make_recommendations` output.
def _recommendations_with_severity(
    results: List[CheckResult],
) -> List[Tuple[str, str, str]]:
    """Return (sort_key, text, severity) triples mirroring _make_recommendations.

    Re-runs the rule pipeline (cheap — already O(N) over results) so this
    helper is safe to call after `_make_recommendations` without ordering
    drift. Severity is derived from the sort_key prefix (deterministic).
    """
    recs: List[Tuple[str, str]] = []
    by_name: Dict[str, CheckResult] = {r.name: r for r in results}

    # Mirror `_make_recommendations` exactly (Codex CDX-W5-iter3-P1):
    # named-rule skip removed because timeout/error never overlaps with
    # the yellow/red gates of the named branches.
    failing = sorted(
        (r for r in results if r.status in ("timeout", "error")),
        key=lambda r: r.name,
    )
    for r in failing[:3]:
        recs.append((
            f"00-{r.name}-{r.status}",
            f"Check '{r.name}' {r.status}: {_sanitize_for_recs(r.summary)} "
            f"(blocks gate_pass)",
        ))

    # PLAN-135 W1 S3 — mirror of the _make_recommendations tamper rule
    # (same sort key + same text so the two pipelines never drift).
    tamper = by_name.get("settings_tamper_tripwires")
    if tamper and tamper.status == "red" and tamper.detail:
        items = tamper.detail if isinstance(tamper.detail, list) else []
        classes = sorted({
            str(f.get("class", ""))
            for f in items
            if isinstance(f, dict) and f.get("class")
        })
        if classes:
            preview = _sanitize_for_recs(", ".join(classes[:3]))
            recs.append((
                "005-settings-tamper",
                f"Settings/env tamper tripwire(s) fired ({len(items)}): "
                f"{preview}{'...' if len(classes) > 3 else ''} — inspect "
                f"settings layers + env before trusting this session",
            ))

    # PLAN-153 Wave E — mirrors of the _make_recommendations rules 006/007
    # (same sort keys + same text so the two pipelines never drift).
    liveness = by_name.get("failopen_rail_liveness_7d")
    if liveness and liveness.status == "red":
        recs.append((
            "006-failopen-rail",
            f"Fail-open security rail fail-opened on EVERY invocation in "
            f"window: {_sanitize_for_recs(liveness.summary)} — restore the "
            f"rail dependency (S254 class) before trusting its silence",
        ))

    gate = by_name.get("harness_config_gate")
    if gate and gate.status == "red":
        recs.append((
            "007-harness-config",
            f"Harness-config gate FAIL: {_sanitize_for_recs(gate.summary)} "
            f"— a registered hook may not resolve at runtime (dead rail)",
        ))

    # S292 — mirror of the _make_recommendations 008 rule (same sort key +
    # same text so the two pipelines never drift).
    sched = by_name.get("scheduled_workflows_red")
    if sched and sched.status == "red":
        recs.append((
            "008-scheduled-red",
            f"Scheduled workflow(s) red: {_sanitize_for_recs(sched.summary)} "
            f"— schedule-only gates never surface in push CI; triage now",
        ))

    # PLAN-165 W2 T2.1 — mirror of the _make_recommendations night-mode
    # rule (SAME shared helper → same sort key + same text by
    # construction, so the two pipelines cannot drift on this rule).
    night_mode_rec = _night_mode_advisory_rec()
    if night_mode_rec:
        recs.append(night_mode_rec)

    sent = by_name.get("sentinels_pending_gpg")
    if sent and sent.status == "yellow" and sent.detail:
        items = sent.detail if isinstance(sent.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "01-owner-sentinels",
                f"Owner GPG sign pending: {len(items)} sentinels ({preview}{'...' if len(items) > 3 else ''})",
            ))

    stranded = by_name.get("plans_stranded_executing")
    if stranded and stranded.status == "red" and stranded.detail:
        items = stranded.detail if isinstance(stranded.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "02-stranded-plans",
                f"Stranded executing plans (>24h no commits): {preview}",
            ))

    skill = by_name.get("skill_unknown_ratio")
    if skill and skill.status == "red":
        recs.append((
            "03-skill-unknown",
            f"Spawn dispatch skill=unknown ratio elevated: {_sanitize_for_recs(skill.summary)}",
        ))

    av3 = by_name.get("audit_v3_backlog")
    if av3 and av3.status == "yellow" and av3.detail:
        items = av3.detail if isinstance(av3.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "04-audit-v3-backlog",
                f"Audit-v3 backlog open ({len(items)}): {preview}",
            ))

    adrs = by_name.get("adrs_stale_proposed")
    if adrs and adrs.status == "yellow" and adrs.detail:
        items = adrs.detail if isinstance(adrs.detail, list) else []
        if items:
            preview = _sanitize_for_recs(", ".join(items[:3]))
            recs.append((
                "05-adrs-stale",
                f"ADRs PROPOSED >30d ({len(items)}): {preview} — promote or retract",
            ))

    recs.sort(key=lambda x: x[0])
    triples: List[Tuple[str, str, str]] = []
    for sort_key, text in recs[:5]:
        if sort_key.startswith("00-") or sort_key in (
            "005-settings-tamper",  # PLAN-135 W1 S3 — rail-integrity = high
            "006-failopen-rail",    # PLAN-153 Wave E item 2 — S254 class = high
            "007-harness-config",   # PLAN-153 Wave E item 1 wire — dead rail = high
            "008-night-mode",       # PLAN-165 W2 T2.1 — non-ratified posture = high
            "008-scheduled-red",    # S292 — invisible-scheduled-red class = high
            "01-owner-sentinels", "02-stranded-plans"
        ):
            severity = "high"
        elif sort_key in ("03-skill-unknown", "04-audit-v3-backlog"):
            severity = "medium"
        elif sort_key == "05-adrs-stale":
            severity = "low"
        else:  # pragma: no cover — defensive default for future rules
            severity = "low"
        triples.append((sort_key, text, severity))
    return triples


# ---- Renderer ---------------------------------------------------------------

def render_digest(results: List[CheckResult], short: bool = False) -> str:
    lines = ["", "## /ceo-boot digest", ""]
    if short:
        red = sum(1 for r in results if r.status == "red")
        yellow = sum(1 for r in results if r.status == "yellow")
        timeout = sum(1 for r in results if r.status == "timeout")
        error = sum(1 for r in results if r.status == "error")
        green = sum(1 for r in results if r.status == "green")
        lines.append(
            f"- {green} green / {yellow} yellow / {red} red / "
            f"{timeout} timeout / {error} error"
        )
        # Surface non-green checks one-line for situational awareness
        for r in results:
            if r.status != "green":
                lines.append(f"  - {r.name}: {r.status} — {r.summary}")
    else:
        lines.append("| Check | Status | Summary | Duration ms |")
        lines.append("|---|---|---|---|")
        for r in results:
            lines.append(f"| {r.name} | {r.status} | {r.summary} | {r.duration_ms:.0f} |")

    # Recommendations engine output
    recs = _make_recommendations(results)
    if recs:
        lines.append("")
        lines.append("### Recommendations")
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")

    lines.append("")
    return "\n".join(lines)
