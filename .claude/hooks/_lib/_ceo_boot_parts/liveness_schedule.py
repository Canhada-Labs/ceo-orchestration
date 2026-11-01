"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations


# PLAN-161 C5 r6 F2 — the ONLY shape accepted as an invocation-exact
# pairing key: EXACTLY 16 lowercase hex (`os.urandom(8).hex()` as minted
# by check_pair_rail.py `_decide()`). Mirrors audit_emit's
# `_PAIR_RAIL_REVIEW_ID_RE` (`^([0-9a-f]{16})?$`) on the consumer side:
# any other nonempty value on a log row (forged / version-skewed
# producer) is coerced to the "" legacy bucket by `_review_id` below and
# can never act as a unique pairing token.
_REVIEW_ID_EXACT_RE = re.compile(r"^[0-9a-f]{16}$")


def _classify_stop_review_event(ev: Dict[str, Any]) -> Optional[str]:
    """Classify one `codex_review_verdict` event for the stop_review sub-rail.

    PLAN-161 C5 (r2 F3 — sub-rails split, NOT merged): the Stop-hook
    cross-review (`codex_review_user_code.py`) gets its OWN row so a healthy
    Stop review can never MASK a silent canonical pair-rail (and vice versa).

    Returns "healthy" | "failopen" | "neutral" | "unclassified" | None:

      clean / findings   -> "healthy"   (a strictly PARSED verdict ran)
      skipped_failopen   -> "failopen"  (infra skip OR malformed verdict)
      detected_only      -> "neutral"   (r3 F3: DETECT-ONLY mode nudged a
                            review that never ran — neither health nor
                            failopen; visible in counts, never
                            green-contributing, never red-contributing)
      anything else      -> "unclassified" (hand-forged log line — the typed
                            emitter coerces off-enum to skipped_failopen;
                            never green)
    """
    if ev.get("action") != "codex_review_verdict":
        return None
    outcome = ev.get("outcome")
    if outcome in ("clean", "findings"):
        return "healthy"
    if outcome == "skipped_failopen":
        return "failopen"
    if outcome == "detected_only":
        return "neutral"
    return "unclassified"


# Deterministic rail registry (list order == render order). Future fail-open
# rails append (name, classifier) here; the check aggregates worst-of.
# PLAN-161 C5: `stop_review` observes the Stop-hook cross-review of the
# ADOPTER's code; `pair_rail` keeps observing check_pair_rail.py (canonical
# framework edits) and is additionally ACTIVITY-CONDITIONED on the
# `pair_rail_review_expected` denominator (handled in the check function —
# it is a denominator signal, not an outcome, so it does NOT go through a
# classifier).
FAILOPEN_RAIL_CLASSIFIERS: List[
    Tuple[str, Callable[[Dict[str, Any]], Optional[str]]]
] = [
    ("pair_rail", _classify_pair_rail_event),
    ("stop_review", _classify_stop_review_event),
]

_STATUS_RANK = {"green": 0, "yellow": 1, "red": 2}


def check_failopen_rail_liveness_7d() -> Tuple[str, str, Any]:
    """PLAN-153 Wave E item 2 — 22nd Tier-S check: fail-open rail liveness.

    Single streaming pass over the canonical audit-log window; per-rail
    verdicts (deterministic registry order), overall = worst-of. Base
    bucket-ladder per rail (unchanged from PLAN-153, PLUS the C5 `neutral`
    bucket):

      failopen > 0 and healthy == 0 → red    (fail-opened on EVERY
                                              classified invocation)
      failopen > 0 and healthy > 0  → yellow (partial fail-open — the
                                              mixed-window rule)
      healthy > 0                   → green
      unclassified only             → yellow (signal present, unparseable)
      neutral only                  → yellow (C5: detected_only nudges —
                                      review never RAN; never green)
      zero events                   → yellow "no signal" (silence from a
                                      fail-open rail is not health)

    PLAN-161 C5 overrides for the `pair_rail` row only (r3 F2 + r4 F1 +
    codex r1 F2 → r4 F2, terminal fix r5 F2 — ACTIVITY-CONDITIONED on
    `pair_rail_review_expected` with INVOCATION-ID-EXACT pairing: the
    producer mints one 16-hex `review_id` per entered review and stamps
    it on BOTH that review's expected emit and its own `pair_rail_case`,
    so a specific expected pairs only with its OWN case. An EXPECTED
    `review_id` with no matching case in-window = an OUTSTANDING (dead)
    review → deficit. This is what COUNTING could not do: neither a
    healthy outcome from session B (r4 F1), nor one early healthy outcome
    in the SAME session (r1 F2), nor an older completed case for a
    DIFFERENT file (r4 F2), nor — the r5 interleaving — an older
    completed case for the SAME (session, file) can satisfy a different
    review's expected. FALLBACK for empty `review_id` ONLY (legacy
    pre-land events, or a fail-open no-id emit): the r4 (session,
    file-hash) bucket-count heuristic, applied to the "" review_id
    subset (best-effort — post-land every review carries an id, so the
    exact path dominates). Terminal
    signals = PAIR_RAIL_TERMINAL_ACTIONS (`pair_rail_case` ONLY — codex
    r2 F2: `pair_rail_codex_unavailable` is shared with codex_invoke.py
    and must not consume a terminal count. r3 F2 correction: a mid-review
    Codex OUTAGE is NOT a deficit — Case F still emits `pair_rail_case`
    carrying the same review_id, so the outage invocation pairs
    expected==case and is laddered by its failopen bucket; a deficit
    means the hook died BETWEEN the expected emit and the case emit —
    zero `pair_rail_case` for that invocation):

      any outstanding expected review_id, OR (id-less subset) any
      (session, file-hash) bucket with expected_count >
      terminal_count               → RED escalation
                                      (the S254 dead-rail class — a review
                                      path was ENTERED and NO pair_rail_case
                                      came back for it; flat yellow
                                      understates it; subsumes the
                                      zero-outcome case)
      zero expected AND zero outcomes → GREEN (vacuous-but-true: no
                                      canonical-edit review activity was
                                      expected in the window)
      matched pairs / outcomes present (no deficit) → the base ladder
                                      above (laddered by the case verdict)

    The `stop_review` row (codex_review_verdict) uses the base ladder only:
    healthy>=1 AND failopen==0 in-window → green; any mixture stays yellow;
    silence stays yellow (its healthy signal arrives with the first
    post-land Stop review of a risky diff — L4).

    ADVISORY fail-open on infra: missing/unreadable log degrades to the
    no-signal yellow via `_iter_audit_events_since`; any internal error is
    caught by the `_wrap_check` fail-soft floor. Never blocks the session.
    """
    window_h = _failopen_rail_window_hours()
    counts: Dict[str, Dict[str, int]] = {
        rail: {"healthy": 0, "failopen": 0, "unclassified": 0, "neutral": 0}
        for rail, _ in FAILOPEN_RAIL_CLASSIFIERS
    }
    # PLAN-161 C5 — pair_rail activity correlation ledgers. Pairing is
    # INVOCATION-ID-EXACT (codex r1 F2 → r4 F2 → terminal fix r5 F2):
    # the producer mints one 16-hex `review_id` per entered review and
    # stamps it on BOTH that review's `pair_rail_review_expected` and its
    # own `pair_rail_case`, so a specific expected can only be satisfied
    # by its OWN case. Counting — even the r4 (session, file-hash)
    # BUCKET counting — cannot pair a specific expected with its own
    # case: an old completed case for the SAME (session, file) in the
    # same session balanced a later dead expected 1:1 and false-greened
    # the row (the r5 interleaving). The id ledgers key per
    # (session_id, review_id) — the id is random per invocation, the
    # session axis is kept so a forged same-id event from another
    # session can never satisfy an expected (conservative direction).
    expected_ids: set = set()   # {(session_id, review_id)} — id-ful only
    terminal_ids: set = set()   # {(session_id, review_id)} — id-ful only
    expected_events_total = 0
    # LEGACY fallback ledgers (r4 F2 heuristic), fed ONLY by id-less
    # events ("" review_id — pre-land emits, or a fail-open no-id emit):
    # best-effort bucket-count pairing per (session, file-hash). Post-land
    # every review carries an id, so the exact path dominates.
    expected_by_bucket: Dict[Tuple[str, str], int] = {}
    terminal_by_bucket: Dict[Tuple[str, str], int] = {}

    def _pair_bucket(ev: Dict[str, Any]) -> Tuple[str, str]:
        # "" is itself a correlation key on BOTH axes: an unattributed /
        # legacy event still pairs with its unattributed sibling instead
        # of going blind.
        return (
            str(ev.get("session_id") or ""),
            str(ev.get("file_path_hash_prefix") or ""),
        )

    def _review_id(ev: Dict[str, Any]) -> str:
        # r5 F2 — the invocation correlation key. "" (or absent) routes
        # the event to the legacy bucket-count fallback.
        # r6 F2 — HARD shape gate: only EXACTLY 16 lowercase hex is a
        # valid pairing key. Any other nonempty value (short/partial,
        # oversize, uppercase, non-hex — a forged row or a
        # version-skewed producer) is coerced to the "" legacy bucket
        # and can NEVER act as a unique pairing token: the r5 "no shape
        # gate here" stance let an off-shape id serve as an exact key,
        # and combined with the emitters' then truncate-before-validate
        # two distinct oversize ids sharing a 16-hex prefix ALIASED to
        # one key — an older terminal could offset a later dead review
        # again (the F2 false-green). The producer + audit_emit gates
        # coerce off-shape to "" on the wire; this mirrors the same
        # exact-16 gate at the consumer so a row that BYPASSED the
        # emitters (forged/legacy) gets identical treatment.
        # r7 F1 — reject non-STRING raw values BEFORE the regex: a JSON
        # number like 1234567890123456 would str() into a 16-digit token
        # that matches ^[0-9a-f]{16}$ and alias a real string id. Only a
        # genuine str is eligible; anything else routes to the "" legacy
        # bucket.
        raw = ev.get("review_id")
        rid = raw if isinstance(raw, str) else ""
        return rid if _REVIEW_ID_EXACT_RE.fullmatch(rid) else ""

    for ev in _iter_audit_events_since(window_h):
        if not isinstance(ev, dict) or _is_test_pollution_event(ev):
            continue
        if ev.get("action") == "pair_rail_review_expected":
            # Denominator signal, not an outcome — never enters a bucket.
            expected_events_total += 1
            rid = _review_id(ev)
            if rid:
                expected_ids.add((str(ev.get("session_id") or ""), rid))
            else:
                key = _pair_bucket(ev)
                expected_by_bucket[key] = expected_by_bucket.get(key, 0) + 1
            continue
        for rail, classify in FAILOPEN_RAIL_CLASSIFIERS:
            bucket = classify(ev)
            if bucket is not None:
                counts[rail][bucket] += 1
                if (
                    rail == "pair_rail"
                    and ev.get("action") in PAIR_RAIL_TERMINAL_ACTIONS
                ):
                    # codex r1 F2 + r5 F2 — only the paired producer's
                    # terminal actions count, and an id-ful case can only
                    # satisfy the expected carrying the SAME review_id;
                    # id-less cases fall back to their (session,
                    # file-hash) bucket.
                    rid = _review_id(ev)
                    if rid:
                        terminal_ids.add(
                            (str(ev.get("session_id") or ""), rid)
                        )
                    else:
                        key = _pair_bucket(ev)
                        terminal_by_bucket[key] = (
                            terminal_by_bucket.get(key, 0) + 1
                        )
                break

    worst = "green"
    parts: List[str] = []
    detail: Dict[str, Any] = {"window_hours": window_h, "rails": {}}
    for rail, _ in FAILOPEN_RAIL_CLASSIFIERS:
        c = counts[rail]
        rail_status: Optional[str] = None
        msg = ""
        extra: Dict[str, Any] = {}
        if rail == "pair_rail":
            # C5 activity-conditioning — pairing is invocation-id-EXACT
            # (r5 F2): an expected (session, review_id) with no matching
            # case tuple is an OUTSTANDING (dead) review. An old case
            # with a DIFFERENT review_id can never satisfy a new dead
            # expected — not cross-session (r4 F1), not an early healthy
            # outcome in the same session (r1 F2), not another file
            # (r4 F2), not even the SAME (session, file) (r5 F2 — the
            # interleaving bucket-counting false-greened). The r4
            # (session, file-hash) bucket-count heuristic survives ONLY
            # for the id-less ("" review_id) legacy subset, where "" is
            # itself a correlation key on both axes so unattributed
            # events still pair up instead of going blind.
            outstanding_ids = expected_ids - terminal_ids
            deficit_buckets = [
                b for b, n in expected_by_bucket.items()
                if n > terminal_by_bucket.get(b, 0)
            ]
            deficit_sessions = (
                {s for s, _ in outstanding_ids}
                | {b[0] for b in deficit_buckets}
            )
            total_outcomes = (
                c["healthy"] + c["failopen"] + c["unclassified"]
            )
            extra = {
                "expected": expected_events_total,
                "expected_without_outcome_sessions": len(deficit_sessions),
            }
            if outstanding_ids or deficit_buckets:
                rail_status = "red"
                msg = (
                    f"{rail}: {len(deficit_sessions)} session(s) entered "
                    f"review with missing terminal outcome(s) in "
                    f"{window_h:.0f}h (S254 class)"
                )
            elif total_outcomes == 0:
                rail_status = "green"
                msg = (
                    f"{rail}: no review activity expected or observed in "
                    f"{window_h:.0f}h (vacuously green)"
                )
            # else: outcomes present, no deficit → base ladder below.
        if rail_status is None:
            if c["failopen"] > 0 and c["healthy"] == 0:
                rail_status = "red"
                msg = (
                    f"{rail}: fail-opened on ALL {c['failopen']} classified "
                    f"invocation(s) in {window_h:.0f}h"
                )
            elif c["failopen"] > 0:
                rail_status = "yellow"
                msg = (
                    f"{rail}: partial fail-open ({c['failopen']} fail-open / "
                    f"{c['healthy']} healthy in {window_h:.0f}h)"
                )
            elif c["healthy"] > 0:
                rail_status = "green"
                msg = f"{rail}: {c['healthy']} healthy invocation(s) in {window_h:.0f}h"
            elif c["unclassified"] > 0:
                rail_status = "yellow"
                msg = (
                    f"{rail}: {c['unclassified']} unclassified event(s), no "
                    f"classified signal in {window_h:.0f}h"
                )
            elif c["neutral"] > 0:
                rail_status = "yellow"
                msg = (
                    f"{rail}: {c['neutral']} nudge-only event(s) (review "
                    f"never ran), no classified signal in {window_h:.0f}h"
                )
            else:
                rail_status = "yellow"
                msg = (
                    f"{rail}: no signal in {window_h:.0f}h (silence from a "
                    f"fail-open rail is not health)"
                )
        parts.append(msg)
        detail["rails"][rail] = {"status": rail_status, **c, **extra}
        if _STATUS_RANK[rail_status] > _STATUS_RANK[worst]:
            worst = rail_status
    return worst, _sanitize_for_recs("; ".join(parts)), detail


# === PLAN-153 Wave E item 1 wire — static harness-config gate at boot ======
# The E1 gate (`.claude/hooks/check_harness_config.py`, ADR-173) lands via
# the SENT-E canonical ceremony (staged under PLAN-153/staged/wave-E until
# signed). This Tier-S check invokes it as a subprocess ONLY when the file
# exists — pre-landing, boot stays green with an explicit "not installed"
# summary. Contract assumed: CLI run with no args from REPO_ROOT, stdin
# closed, exit 0 == pass / non-zero == fail (the same contract validate.yml
# will consume). Fail-open on infra: timeout → yellow + a
# `ceo_boot_check_skipped` audit event (never a session block); spawn error
# → yellow. Local static check — no network, CEO_SOTA_DISABLE n/a.

HARNESS_CONFIG_GATE_DEFAULT = (
    REPO_ROOT / ".claude" / "hooks" / "check_harness_config.py"
)
HARNESS_CONFIG_GATE_TIMEOUT_S_DEFAULT = 2.5


def _harness_config_gate_path() -> Path:
    """Resolve the E1 gate script path (env override for tests)."""
    override = os.environ.get("CEO_HARNESS_CONFIG_GATE", "")
    if override:
        return Path(override)
    return HARNESS_CONFIG_GATE_DEFAULT


def _harness_config_gate_timeout_s() -> float:
    """Subprocess timeout for the E1 gate, clamped to [0.1, 10.0]s."""
    raw = os.environ.get("CEO_HARNESS_CONFIG_GATE_TIMEOUT_S", "")
    if raw:
        try:
            return max(0.1, min(10.0, float(raw)))
        except (TypeError, ValueError):
            pass
    return HARNESS_CONFIG_GATE_TIMEOUT_S_DEFAULT


def check_harness_config_gate() -> Tuple[str, str, Any]:
    """PLAN-153 Wave E item 1 — 23rd Tier-S check: harness-config gate.

    File-existence guarded: green "not installed" until the SENT-E ceremony
    lands `check_harness_config.py` canonical. Once present: subprocess run,
    rc 0 → green, rc != 0 → red carrying the first sanitized output line,
    timeout → yellow (skipped, `ceo_boot_check_skipped` emitted), spawn
    error → yellow. ADVISORY — never blocks the session.
    """
    gate = _harness_config_gate_path()
    if not gate.is_file():
        return (
            "green",
            "harness-config gate not installed (PLAN-153 E1 staged; skipping)",
            {"installed": False},
        )
    timeout_s = _harness_config_gate_timeout_s()
    try:
        proc = subprocess.run(
            [sys.executable, str(gate)],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(REPO_ROOT),
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        _emit_ceo_boot_check_skipped_safe(
            check_name="harness_config_gate",
            timeout_ms=int(timeout_s * 1000),
        )
        return (
            "yellow",
            f"harness-config gate timeout >{timeout_s:.1f}s (skipped, fail-open)",
            {"installed": True, "timeout": True},
        )
    except OSError as exc:
        return (
            "yellow",
            f"harness-config gate spawn error: {type(exc).__name__}",
            {"installed": True},
        )
    if proc.returncode == 0:
        return "green", "harness-config gate pass", {"installed": True, "rc": 0}
    first_line = ""
    for stream in (proc.stdout, proc.stderr):
        for line in (stream or "").splitlines():
            if line.strip():
                first_line = _sanitize_for_recs(line.strip())
                break
        if first_line:
            break
    summary = f"harness-config gate FAIL (rc={proc.returncode})"
    if first_line:
        summary = f"{summary}: {first_line}"
    return "red", summary[:200], {"installed": True, "rc": proc.returncode}


# === S292 — 24th Tier-S check: scheduled workflows whose latest run is red ==
# Closes the recurring "scheduled gate red for weeks, invisible" class — six
# occurrences of the same failure mode (Coverage S283; mutation-gate S290/
# S291; supply-chain-watch S291; tournament + reality-ledger S292): a
# workflow that fires only on `schedule:` never appears in the push-triggered
# CI signal the operator actually looks at, so its red persists unseen.
#
# Design constraints:
# - stdlib-only: the scheduled-workflow set (and each workflow's cron lines)
#   is derived from a line-regex scan of `.github/workflows/*.y*ml` (no yaml
#   parser in the runtime deps). The INPUT LIST is carried verbatim in the
#   detail payload — the instrument prints its inputs (S291 doctrine).
# - S361 (PLAN-194 L2, cure of the CLASS behind the S360 false red, 2nd
#   occurrence): the gh endpoints that FILTER server-side are not
#   deterministic — measured S360: `actions/runs?event=schedule` answered
#   total_count 145 (newest run 2026-09-05) and, seconds later, 419 (newest
#   2026-10-01); `workflows/validate.yml/runs?event=schedule&status=completed`
#   answered 25 → 39. Only the UNFILTERED per-workflow listing answered right.
#   So: ONE unfiltered call per scheduled workflow, all in parallel; the
#   client filters; detection AND cure come out of the SAME response (no
#   second "cure probe" that can run out of budget); ONE budget constant
#   (SCHED_RED_BUDGET_S); a freshness guard derived from the cron turns old
#   data YELLOW, never red; a red whose cure cannot be verified says so in
#   the summary.
# - NO DATA IS NEVER GREEN: gh missing / timeout / rc!=0 / unparseable
#   payload / no scheduled run in the page / stale page → yellow. Only the
#   explicit operator disable (CEO_BOOT_SCHED_RED=0) renders green.
# - no new audit action names (the action registry is canonical); the
#   timeout path reuses the registered `ceo_boot_check_skipped`.

_SCHED_RED_BAD_CONCLUSIONS = frozenset(
    {"failure", "timed_out", "startup_failure"}
)
# Rows per workflow page. Measured S360 (unfiltered): 10 rows 1.13 s, 30
# rows 1.5 s, 100 rows 6.36 s. A busy push lane can bury its scheduled run
# deeper than this — that case is reported (yellow), never guessed.
_SCHED_RED_PER_PAGE = 30
_SCHED_RED_MAX_PARALLEL = 16
_SCHED_RED_WF_NAME_RE = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
_SCHED_RED_DAY_S = 86400.0
# Data older than FACTOR × cron period is stale (one dropped firing is
# tolerated). Unparseable cron ⇒ the longest common period (monthly).
_SCHED_RED_STALE_FACTOR = 2.0
_SCHED_RED_PERIOD_FALLBACK_S = 31 * _SCHED_RED_DAY_S


def _sched_red_budget_s() -> float:
    """The check's single time budget, clamped to [0.5, 8.0]s.

    Every gh call and the check's own deadline derive from this value
    (env override CEO_BOOT_SCHED_RED_TIMEOUT_S, else SCHED_RED_BUDGET_S).
    """
    raw = os.environ.get("CEO_BOOT_SCHED_RED_TIMEOUT_S", "")
    if raw:
        try:
            return max(0.5, min(8.0, float(raw)))
        except (TypeError, ValueError):
            pass
    return SCHED_RED_BUDGET_S


def _sched_red_now() -> float:
    """Wall clock for the freshness guard (patched in tests)."""
    return time.time()


def _scheduled_workflows() -> Dict[str, List[str]]:
    """Repo-relative workflow path → its cron expressions.

    Line-regex derivation (requires BOTH a `schedule:` line and a
    `- cron:` line) — stdlib-only stand-in for a yaml parse. Sorted for
    CR-N7 determinism.
    """
    wf_dir = REPO_ROOT / ".github" / "workflows"
    out: Dict[str, List[str]] = {}
    if not wf_dir.is_dir():
        return out
    for p in sorted(wf_dir.glob("*.y*ml")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        crons = re.findall(
            r"(?m)^\s*-\s*[\"']?cron[\"']?\s*:\s*[\"']?([^\"'#\n]*?)[\"']?\s*(?:#.*)?$",
            text,
        )
        if re.search(r"(?m)^\s*schedule:\s*$", text) and crons:
            out[f".github/workflows/{p.name}"] = [c.strip() for c in crons]
    return out


def _scheduled_workflow_paths() -> List[str]:
    """Repo-relative paths of workflows with a `schedule:` trigger."""
    return list(_scheduled_workflows())


def _sched_red_cron_period_s(expr: str) -> Optional[float]:
    """Approximate firing period of one 5-field cron, floored at one day.

    Conservative on purpose (a weekday list counts as weekly): the guard may
    call stale data fresh, never fresh data stale.
    """
    fields = expr.split()
    if len(fields) != 5:
        return None
    _minute, _hour, dom, month, dow = fields
    if month != "*":
        return 366 * _SCHED_RED_DAY_S
    if dom != "*":
        return 31 * _SCHED_RED_DAY_S
    if dow != "*":
        return 7 * _SCHED_RED_DAY_S
    return _SCHED_RED_DAY_S


def _sched_red_period_s(crons: List[str]) -> float:
    periods = [p for p in (_sched_red_cron_period_s(c) for c in crons) if p]
    return min(periods) if periods else _SCHED_RED_PERIOD_FALLBACK_S


def _sched_red_parse_ts(raw: Any) -> Optional[float]:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None
