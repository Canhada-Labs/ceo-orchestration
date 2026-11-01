"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



def _score_persona_coverage(hours: float) -> Dict[str, int]:
    """Compute 4×4 persona × task coverage over a rolling audit-log window.

    Returns canonical metrics dict suitable for both the 24h session-smoke
    check and the 7d trend check. Phase 1 (S127): `eligible_demand_events`
    is unconditionally 0 — that signal is produced by the demand ledger
    scheduled for Phase 2 (`PLAN-104-persona-demand-ledger`).
    """
    canonical_by_lower = {p.lower(): p for p in _VETO_FLOOR_PERSONAS}
    seen: Dict[str, set] = {p: set() for p in _VETO_FLOOR_PERSONAS}
    events_with_target = 0
    for ev in _iter_audit_events_since(hours=hours):
        # PLAN-112-FOLLOWUP-persona-routing-wire W4 — F-5.4 task_type
        # pollution fix. Only genuine persona-dispatch events contribute to
        # coverage; unrelated emitters carrying a VETO-floor archetype +
        # a bogus task_type are excluded entirely.
        if not _is_persona_dispatch_event(ev):
            continue
        role = _normalize_persona_role(ev)
        if role not in _VETO_FLOOR_PERSONAS_LOWER:
            continue
        events_with_target += 1
        task_type = ev.get("task_type") or ev.get("phase") or ""
        if not isinstance(task_type, str) or not task_type:
            continue
        task_lower = task_type.lower()
        for t in _PERSONA_TASK_TYPES:
            if t in task_lower:
                seen[canonical_by_lower[role]].add(t)
                break
    cells_covered = sum(len(v) for v in seen.values())
    total_cells = len(_VETO_FLOOR_PERSONAS) * len(_PERSONA_TASK_TYPES)
    score_pct = (cells_covered / total_cells * 100.0) if total_cells else 0.0
    return {
        "cells_covered": cells_covered,
        "total_cells": total_cells,
        "events_with_target_archetype": events_with_target,
        "score_x100": int(round(score_pct * 100)),
    }


def _persona_coverage_status(
    metrics: Dict[str, int],
    *,
    window_hours: int,
) -> Tuple[str, str]:
    """Decide status + summary for a persona-coverage check window.

    Phase 1 (S127) semantic — pure observability, never red:

      ``events_with_target_archetype == 0`` → green "no VETO-floor
      dispatches in <h>h" (mirrors demand-driven empty-green pattern of
      the other 17 Tier-S checks — Codex R2 AMEND #1).

      ``events_with_target_archetype > 0`` → yellow "M/16 cells covered
      in <h>h" (matrix demoted to max-yellow forever per Codex R2 AMEND
      #2 — RED authority reserved for Phase 2 demand-driven gate).
    """
    events_target = metrics["events_with_target_archetype"]
    cells = metrics["cells_covered"]
    total = metrics["total_cells"]
    if events_target == 0:
        return "green", f"no VETO-floor dispatches in {window_hours}h"
    return "yellow", f"{cells}/{total} cells covered in {window_hours}h"


def _emit_persona_coverage(
    metrics: Dict[str, int],
    *,
    window_hours: int,
) -> None:
    """Emit ``ceo_boot_persona_coverage_score`` audit event (shared by 24h+7d).

    S127 Phase 1 scope-(b) — emits only the 3 fields already in the kernel
    allowlist (`score_x100`, `cells_covered`, `total_cells`). The new fields
    (`window_hours`, `events_with_target_archetype`, `eligible_demand_events`)
    surface in the /ceo-boot result dict + summary text but are NOT persisted
    in the audit-log under Phase 1. Deferring the
    ``_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST`` kernel amendment to an Owner
    ceremony — bundle with the Phase 2 demand-ledger ship (which needs more
    kernel surface anyway), avoiding two separate kernel-override events.

    The `window_hours` value is consumed by `_persona_coverage_status` for
    the summary string; downstream audit-log consumers reconstructing
    cadence from emitted events would need to infer it (or wait for
    Phase 2 ship).
    """
    del window_hours  # See docstring; not emitted under Phase 1 scope-(b).
    try:
        if _audit_emit is not None and hasattr(_audit_emit, "emit_generic"):
            # score_x100 is integer basis-points (0-10000); floats break
            # canonical JSON HMAC chain — Codex S123 iter-2 P1.
            _audit_emit.emit_generic(
                "ceo_boot_persona_coverage_score",
                score_x100=metrics["score_x100"],
                cells_covered=metrics["cells_covered"],
                total_cells=metrics["total_cells"],
            )
    except Exception:  # noqa: BLE001 (Tier-S fail-soft)
        pass


def check_ceo_boot_persona_coverage_score() -> Tuple[str, str, Any]:
    """18th Tier-S check — persona × task coverage at 24h cadence (session-smoke).

    Originally PLAN-093 Wave C.5/C.6 AC10 — sourced 24h of audit-log and
    scored a 4×4 matrix with `<50% red` thresholds. S127 cadence-amendment
    (Codex R2 thread `019e33a3` AMEND `PHASE-1+2-WITH-(c)`): demoted to
    permanent observability. Never red, never gate-failing. RED authority
    moves to `PLAN-104-persona-demand-ledger` (Phase 2 event-driven gate).

    Companion: `check_persona_atrophy_7d` at 168h cadence for trend signal.

    Emits ``ceo_boot_persona_coverage_score`` with `window_hours=24` and
    `eligible_demand_events=0` (PLAN-104 demand ledger live; observability-only here per AC4).
    """
    try:
        metrics = _score_persona_coverage(hours=24.0)
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"persona_coverage error: {exc}", None
    status, summary = _persona_coverage_status(metrics, window_hours=24)
    _emit_persona_coverage(metrics, window_hours=24)
    return status, summary, {
        **metrics,
        "window_hours": 24,
        "eligible_demand_events": 0,
    }


def check_persona_atrophy_7d() -> Tuple[str, str, Any]:
    """19th Tier-S check — demand-normalized persona-atrophy at 168h.

    PLAN-104 Wave D activated the demand-driven RED branch (S134 Codex R2
    thread `019e37e3` ACCEPT). Set-algebra in
    `persona_demand_resolver.atrophy_7d_status` (Codex iter-1 P0 #2 +
    iter-2 P1 #1 folds — adds defense-in-depth effective_unmet
    computation inline):

      satisfied         = opened & matched
      unmet_recorded    = (opened & unmet) - matched - waived
      effective_unmet   = opened where opened_ts + 24h < now AND
                          no terminal AND no in-window dispatch-match
      unmet_total       = unmet_recorded | (effective_unmet - waived)
      waived            = (opened & waived) - matched
      still_open        = opened where window NOT expired and no terminal
      eligible_settled  = satisfied | unmet_total | waived

      not opened           -> green "no eligible persona demand in 168h"
      not eligible_settled -> green "<N> demand(s) still inside window"
      not unmet_total      -> green "<S>/<E> demands matched (<W> waived)"
      else                 -> red   "<U> persona demand(s) unmet in 168h ..."

    Side-effect: this check runs scan + waive-emit + resolve before
    computing status (Codex iter-1 P0 #1). Ordering per Codex iter-2
    P1 #2: scan -> emit_opened -> emit_waives_for_scanned -> resolve
    -> emit_resolutions (waive precedes unmet emit).

    Kill-switch CEO_PERSONA_DEMAND_LEDGER_DISABLED=1 reverts to
    pre-PLAN-104 observability-only semantic (max-yellow). The 18th check
    `check_ceo_boot_persona_coverage_score` stays observability-only
    forever per S127 AMEND option-(c).
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        try:
            metrics = _score_persona_coverage(hours=168.0)
        except Exception as exc:  # noqa: BLE001
            return "yellow", f"persona_atrophy_7d error: {exc}", None
        status, summary = _persona_coverage_status(metrics, window_hours=168)
        _emit_persona_coverage(metrics, window_hours=168)
        return status, summary, {
            **metrics,
            "window_hours": 168,
            "eligible_demand_events": 0,
        }

    try:
        import importlib.util
        scripts_dir = Path(__file__).resolve().parent
        spec_path = scripts_dir / "persona_demand_resolver.py"
        spec = importlib.util.spec_from_file_location(
            "persona_demand_resolver", spec_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError("resolver spec load failed")
        resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolver)
        scan_spec = importlib.util.spec_from_file_location(
            "persona_demand_scan", scripts_dir / "persona_demand_scan.py",
        )
        if scan_spec is None or scan_spec.loader is None:
            raise ImportError("scan spec load failed")
        scanner = importlib.util.module_from_spec(scan_spec)
        scan_spec.loader.exec_module(scanner)
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"persona_atrophy_7d module import error: {exc}", None

    # Codex iter-1 P0 #1 fold: actually run scan + waive-emit + resolve
    # before computing status. Without this the 19th check only reads
    # ledger state that nothing ever populates -> never reaches RED in
    # real use. Each step is best-effort; any IO error is swallowed and
    # the status path's defense-in-depth expiry computation still works.
    #
    # Codex iter-2 P1 #2 fold: waives MUST fire BEFORE emit_resolutions.
    # Codex iter-4 P1 #1 fold: detect_all() is called ONCE here and
    # both scoped operations re-use it (avoids git-subprocess duplication).
    # Order:
    #   1. detect_all() -> full candidate set with target_ref cleartext
    #   2. emit_opened() dedups via audit-log
    #   3. emit_waives_for_scanned(all_candidates) scoped to commits
    #   4. resolve() / emit_resolutions() catches non-waived expired demands
    repo_root = Path(__file__).resolve().parents[2]
    all_candidates: List = []
    try:
        all_candidates = scanner.detect_all(repo_root)
        # Local dedup against audit-log (avoids 2nd git subprocess pass).
        already = scanner._existing_demand_ids(
            AUDIT_LOG_DEFAULT, scanner.SCAN_HORIZON_HOURS,
        )
        new_only = [ev for ev in all_candidates if ev.demand_id not in already]
        scanner.emit_opened(new_only)
    except Exception:  # noqa: BLE001 (Tier-S fail-soft)
        pass
    try:
        resolver.emit_waives_for_scanned(all_candidates, AUDIT_LOG_DEFAULT, repo_root)
    except Exception:  # noqa: BLE001
        pass
    try:
        summary_resolve = resolver.resolve(AUDIT_LOG_DEFAULT)
        resolver.emit_resolutions(summary_resolve)
    except Exception:  # noqa: BLE001
        pass

    try:
        status, summary, demand_metrics = resolver.atrophy_7d_status(AUDIT_LOG_DEFAULT)
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"persona_atrophy_7d resolver error: {exc}", None

    try:
        score_metrics = _score_persona_coverage(hours=168.0)
        _emit_persona_coverage(score_metrics, window_hours=168)
    except Exception:  # noqa: BLE001
        score_metrics = {"score_x100": 0, "cells_covered": 0, "total_cells": 16}

    return status, summary, {
        **score_metrics,
        **demand_metrics,
        "window_hours": 168,
    }


def check_confidence_gate_drift_7d() -> Tuple[str, str, Any]:
    """PLAN-106 Wave F.2 — 20th Tier-S check.

    Detects HIGH_CONFIDENCE_BLOCK classes whose 7d FPR > 2% per
    ADR-019-AMEND-1 §6. Wraps the side-effect-free `detect_drift_7d`
    function from `.claude/scripts/check-confidence-gate-drift.py`
    (refactored per Wave F.1).

    Status mapping:
        - drift NOT detected, valid config + log → green
        - drift NOT detected, missing config/log → green (fail-OPEN
          per ADR-095 doctrine — no calendar gates, but also no
          spurious RED on fresh installs)
        - drift detected → yellow (advisory; auto-demote is the
          underlying script's responsibility, not the ceo-boot check)
        - exception → yellow with error message
    """
    try:
        import importlib.util
        scripts_dir = Path(__file__).resolve().parent
        spec = importlib.util.spec_from_file_location(
            "check_confidence_gate_drift",
            scripts_dir / "check-confidence-gate-drift.py",
        )
        if spec is None or spec.loader is None:
            return "yellow", "drift detector module spec load failed", None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"drift detector import error: {exc}", None

    try:
        drift, summary, detail = mod.detect_drift_7d()
    except Exception as exc:  # noqa: BLE001
        return "yellow", f"detect_drift_7d error: {exc}", None

    if not drift:
        return "green", summary, detail
    return "yellow", summary, detail


def _emit_settings_tamper_detected_safe(findings: List[Dict[str, str]]) -> None:
    """Emit ONE closed-enum ``settings_tamper_detected`` event per class.

    PLAN-135 W1 S3. Field contract (Sec MF-3, enforced emit-side by
    ``_SETTINGS_TAMPER_DETECTED_ALLOWLIST`` in ``_lib/audit_emit.py``):

      tamper_class  — closed enum (the 5 ``effective_config.TAMPER_*``
                      members; off-enum values are COERCED emit-side)
      layer         — closed enum (user/project/local/managed/env/disk;
                      first layer seen for the class)
      finding_count — int, clamped 0..99

    The finding DETAIL string is NEVER emitted — it can carry endpoint
    URLs, model ids, helper paths or flag values (mcp_routing.py
    breadcrumb precedent +
    [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

    Fail-open contract: pre-ceremony (action not yet in ``_KNOWN_ACTIONS``)
    writes a stderr breadcrumb instead of emitting; any emit failure is
    swallowed. NEVER raises, NEVER blocks boot.
    """
    if _audit_emit is None or not findings:
        return
    try:
        emit_fn = getattr(_audit_emit, "emit_generic", None)
        if not callable(emit_fn):
            return
        known = getattr(_audit_emit, "_KNOWN_ACTIONS", None)
        if known is not None and "settings_tamper_detected" not in known:
            sys.stderr.write(
                "[ceo-boot] 'settings_tamper_detected' not in _KNOWN_ACTIONS; "
                "emit dropped until the PLAN-135 W1 kernel ceremony lands.\n"
            )
            return
        by_class: Dict[str, Dict[str, Any]] = {}
        for f in findings:
            if not isinstance(f, dict):
                continue
            klass = str(f.get("class", ""))[:64]
            if not klass:
                continue
            slot = by_class.setdefault(
                klass, {"layer": str(f.get("layer", ""))[:16], "count": 0}
            )
            slot["count"] += 1
        for klass in sorted(by_class):  # deterministic order (CR-N7)
            slot = by_class[klass]
            emit_fn(
                "settings_tamper_detected",
                session_id=_ceo_boot_session_id(),
                tamper_class=klass,
                layer=slot["layer"],
                finding_count=max(0, min(99, int(slot["count"]))),
            )
    except Exception:  # noqa: BLE001 — advisory fail-open
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)


def check_settings_tamper_tripwires() -> Tuple[str, str, Any]:
    """PLAN-135 W1 S3 — 21st Tier-S check: settings/env tamper tripwires.

    Scans the RESOLVED multi-layer settings (user / project / local /
    managed — including the gitignored, sentinel-blind
    ``settings.local.json``) plus the import-time env snapshot for the
    five tamper classes of THREAT-MODEL-WORKSHEET.md §2, via the shared
    ``_lib/effective_config`` module:

      (a) ``disableAllHooks`` truthy in ANY settings layer
      (b) ``ANTHROPIC_MODEL`` / ``ANTHROPIC_DEFAULT_*`` /
          ``ANTHROPIC_SMALL_FAST_MODEL`` remap outside the ADR-149
          allowlist (skipped fail-open when the allowlist is unreadable)
      (c) ``ANTHROPIC_BASE_URL`` / ``ANTHROPIC_AUTH_TOKEN`` /
          ``apiKeyHelper`` endpoint remap (model substitution AND
          transcript egress outside check (b) entirely)
      (d) ``permissions.defaultMode: bypassPermissions`` or
          dangerously-skip flags in any layer (nullifies the S2 floor)
      (e) effective hook count == registered count (registered-but-
          missing-on-disk census; a missing hook fails open = allow)

    Env reads come EXCLUSIVELY from the module-import-time snapshot
    (``_TAMPER_ENV_SNAPSHOT``, trusted_env pattern) — never live
    ``os.environ``. Settings reads come from the RESOLVED multi-layer
    config (``effective_config.resolve_settings``).

    Status mapping (ADVISORY — /ceo-boot never blocks the session):

      findings present           → red    (rail integrity is suspect)
      no findings, layer errors  → yellow (a corrupt PRESENT layer is
                                   itself an anomaly worth eyes)
      no findings, clean         → green
      module missing / internal  → yellow (advisory fail-open +
                                   stderr breadcrumb, never crash)

    Side-effect: one closed-enum ``settings_tamper_detected`` audit emit
    per detected class via ``_emit_settings_tamper_detected_safe``
    (``_KNOWN_ACTIONS``-guarded pre-ceremony).
    """
    if _effective_config is None:
        sys.stderr.write(
            "[ceo-boot] effective_config unavailable — settings tamper "
            "tripwires inactive (fail-open).\n"
        )
        return (
            "yellow",
            "effective_config unavailable — tamper tripwires inactive",
            None,
        )
    try:
        resolved = _effective_config.resolve_settings(REPO_ROOT)
        findings = _effective_config.classify_tampering(
            resolved, _TAMPER_ENV_SNAPSHOT
        )
        _emit_settings_tamper_detected_safe(findings)
        if findings:
            classes = sorted({
                str(f.get("class", ""))
                for f in findings
                if isinstance(f, dict) and f.get("class")
            })
            # Summary carries ONLY closed-enum class names (never the
            # finding detail — it can embed env values / endpoints).
            return (
                "red",
                f"{len(findings)} tamper finding(s): "
                f"{','.join(classes)[:160]}",
                findings,
            )
        errors = resolved.get("errors") or []
        if errors:
            return (
                "yellow",
                f"no tamper indicators; {len(errors)} unparseable "
                f"settings layer(s)",
                {"errors": [str(e)[:160] for e in errors[:4]]},
            )
        registered: set = set()
        for layer in resolved.get("layers", []):
            if isinstance(layer, dict) and layer.get("name") in (
                "project", "local",
            ):
                registered.update(
                    _effective_config.registered_hook_basenames(
                        layer.get("data") or {}
                    )
                )
        effective = _effective_config.count_effective_hooks(REPO_ROOT)
        return (
            "green",
            f"no tamper indicators ({effective}/{len(registered)} "
            f"registered hooks effective)",
            {"registered": len(registered), "effective_on_disk": effective},
        )
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft floor)
        return "yellow", f"tamper tripwires error: {type(exc).__name__}", None


# === PLAN-153 Wave E item 2 — fail-open rail LIVENESS (debate B unseen-1) ===
# S254 root cause codified: `check_pair_rail.py` fail-opens BY DESIGN when
# Codex is absent, so a dead pair-rail is INDISTINGUISHABLE from a quiet one
# unless something counts outcomes over a window. Doctrine: silence from a
# fail-open security rail is NOT health — a window where every classified
# invocation fail-opened is RED; a window with no signal at all is YELLOW
# (never green; the S254 dead-registration failure mode produces exactly
# zero on-disk events, so "no signal" must stay visible).
#
# Data source (canonical audit-log.jsonl typed events only):
#   - `pair_rail_case` (check_pair_rail.py `_decide_with_matrix` case
#     arms via _lib/audit_emit.emit_pair_rail_case): closed-enum `case`
#     A-F. A/B/C/D/E == a COMPLETED Codex review (rail demonstrably
#     alive; B is a block — the strongest liveness proof). F == the
#     ADR-106 fail-open path (Codex unavailable / timeout / malformed)
#     — still an EMITTED, accounted outcome (r3 F2: an outage is not
#     silence).
#   - Legacy/typed labels `pair_rail_review_passed` /
#     `pair_rail_codex_unavailable` (emitted by codex_invoke.py:366-390;
#     check_pair_rail's own copies go to a local sink + stderr only).
#   - `pair_rail_fatal_failopen` (pending _KNOWN_ACTIONS registration —
#     included forward-compatibly; costs nothing while absent).
# NOT derivable from disk (honest gap, stated in PLAN-153 Wave E report):
# sentinel-bypass / kill-switch / out-of-scope invocations emit NO canonical
# event (check_pair_rail.py:1644-1647), and the audit-log.errors sidecar
# attributes lines to infra writers (spool_writer/check_budget/audit_emit),
# not to security rails. Those windows degrade to the yellow "no signal"
# verdict — never to green.
#
# PLAN-161 C5 (CF-9) — the signal was broken, not the rail: the Stop-hook
# cross-review that actually runs in this repo is codex_review_user_code.py,
# which emitted only a GENERIC event this check never observed → permanent
# yellow. Two typed actions close the gap:
#   - `codex_review_verdict` (outcome enum clean/findings/skipped_failopen/
#     detected_only) feeds the NEW `stop_review` sub-rail row (sub-rails
#     SPLIT, not merged — a healthy Stop review must never mask a silent
#     canonical pair-rail, r2 F3).
#   - `pair_rail_review_expected` (check_pair_rail.py `_decide()` after the
#     sentinel-bypass arm) is the durable DENOMINATOR that makes the
#     `pair_rail` row ACTIVITY-CONDITIONED with INVOCATION-ID-EXACT
#     pairing (codex r1 F2 → r4 F2 → terminal fix r5 F2): both the
#     expected emit and the same invocation's `pair_rail_case` carry one
#     freshly minted 16-hex `review_id`, so a specific expected pairs
#     ONLY with its OWN case. Counting — even (session, file-hash)
#     BUCKET counting — fundamentally cannot do that: an old completed
#     case for the SAME (session, file) offset a later dead expected 1:1
#     (the r5 interleaving false-green). Semantics: zero expected + zero
#     outcomes → vacuous green; any EXPECTED `review_id` with no matching
#     `pair_rail_case` in-window (terminal set = `pair_rail_case` ONLY —
#     codex r2 F2; see PAIR_RAIL_TERMINAL_ACTIONS) → an OUTSTANDING
#     (dead) review → RED escalation (the S254 class); id-less events
#     (legacy pre-land emits, or a fail-open no-id emit) fall back to the
#     r4 (session, file-hash) bucket-count heuristic applied ONLY to the
#     "" review_id subset (best-effort — post-land every review carries
#     an id, so the exact path dominates); outcomes present with no
#     deficit → the original ladder. The liveness signal is exactly as
#     trustworthy as the review path it observes — no new authority.

FAILOPEN_RAIL_WINDOW_HOURS_DEFAULT = 168.0  # 7d


def _failopen_rail_window_hours() -> float:
    """Resolve the liveness window (hours). Env override for tests/tuning.

    ``CEO_FAILOPEN_LIVENESS_WINDOW_H`` clamped to [1, 2160] (1h..90d);
    unparseable input falls back to the 168h default (fail-open on infra —
    this is a tuning knob, not a security matcher input).
    """
    raw = os.environ.get("CEO_FAILOPEN_LIVENESS_WINDOW_H", "")
    if raw:
        try:
            return max(1.0, min(2160.0, float(raw)))
        except (TypeError, ValueError):
            pass
    return FAILOPEN_RAIL_WINDOW_HOURS_DEFAULT


def _classify_pair_rail_event(ev: Dict[str, Any]) -> Optional[str]:
    """Classify one audit event for the pair-rail liveness ledger.

    Returns "healthy" | "failopen" | "unclassified" | None (not a
    pair-rail event). An out-of-enum `case` value can only appear via a
    hand-forged log line (the producer coerces unknowns to "F",
    audit_emit.emit_pair_rail_case) — it is counted "unclassified" and can
    NEVER contribute to a green verdict (no false-green on unparseable
    input; observability sibling of the _e3 fail-closed precedent).
    """
    action = ev.get("action")
    if action == "pair_rail_case":
        case = ev.get("case")
        if case == "F":
            return "failopen"
        if case in ("A", "B", "C", "D", "E"):
            return "healthy"
        return "unclassified"
    if action in ("pair_rail_codex_unavailable", "pair_rail_fatal_failopen"):
        return "failopen"
    if action in ("pair_rail_review_passed", "pair_rail_codex_violation"):
        return "healthy"
    return None


# PLAN-161 C5 (codex r1 F2, tightened by codex r2 F2) — actions that count
# as a TERMINAL, accounted signal for the expected/terminal count-deficit
# pairing. The terminal set is EXACTLY `pair_rail_case`: the per-decision
# completion signal emitted by the SAME producer (check_pair_rail.py) that
# emits the `pair_rail_review_expected` denominator. `pair_rail_codex_unavailable`
# is deliberately NOT terminal (r2 F2): it is also emitted by a DIFFERENT
# rail (codex_invoke.py, e.g. on parse_error), so counting it here would
# let an unrelated outage in the same session consume a terminal count and
# MASK a genuinely missing `pair_rail_case` — defeating the deficit
# escalation.
#
# What a DEFICIT means (r3 F2, pairing made invocation-id-exact by r5
# F2): an EXPECTED `review_id` with no matching `pair_rail_case` carrying
# the SAME id in-window (or, for id-less legacy events only, an
# expected_count > case count inside a (session, file-hash) bucket of the
# "" review_id subset — the r4 fallback) means the review path was
# ENTERED but produced NO `pair_rail_case` of its own — the hook died /
# was killed BETWEEN the `pair_rail_review_expected` emit and the case
# emit. That is the genuine S254 dead-rail signal. A Codex OUTAGE is
# NOT a deficit: an outage during an entered review is Case F, and the
# `_decide_with_matrix` Case-F arm STILL emits a `pair_rail_case`
# (case=F), so the outage session pairs expected==terminal and is
# laddered normally by its `failopen` bucket; the outage also remains
# separately visible via the dispatcher `codex_outage_minutes` metric
# (disable_predicate_eval.py). (check_pair_rail's own
# `pair_rail_codex_unavailable` copy goes to a local test sink + stderr
# only — it never reaches the canonical log, so Case F IS the canonical
# outage record.) The legacy labels (`pair_rail_review_passed` /
# `pair_rail_codex_violation` / `pair_rail_fatal_failopen`) come from
# producers that never emit the `pair_rail_review_expected` denominator —
# they still classify into buckets but do not pair.
PAIR_RAIL_TERMINAL_ACTIONS = (
    "pair_rail_case",
)
