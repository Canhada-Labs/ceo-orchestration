"""Context-pressure and sidecar accounting."""
from __future__ import annotations

def _progress_floor_tokens() -> Optional[int]:
    """The progress-guard floor in tokens, or None when the guard is OFF.

    PLAN-179 W0 US2b. Read from ``CEO_CONTEXT_PROGRESS_FLOOR_TOKENS``; there is
    deliberately NO default — the plan requires the measured ``F`` before the
    floor has an honest value, so an unset (or non-positive / non-integer) env
    var leaves the guard a no-op instead of shipping a magic number."""
    raw = os.environ.get(PROGRESS_FLOOR_ENV, "").strip()
    if not raw:
        return None
    try:
        floor = int(raw)
    except ValueError:
        _breadcrumb("%s is not an integer — progress guard off" % PROGRESS_FLOOR_ENV)
        return None
    if floor <= 0:
        return None
    return floor


def _num(val: Any) -> Optional[float]:
    """Numeric coercion for harness-supplied accounting fields, or None.

    ``bool`` is rejected explicitly: it is an ``int`` subclass and ``True``
    would otherwise sail through as the number 1."""
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def _used_tokens_from_event(event: Dict[str, Any]) -> Optional[int]:
    """Context tokens already used, as reported BY THE HARNESS, or None.

    PLAN-179 W0 US2b. The documented PreCompact hook input carries no token
    accounting, so this reads OPTIONAL numeric fields and returns None when
    absent — the guard then no-ops. We do NOT estimate the number from the
    transcript: an invented measurement is exactly what W0 exists to prevent
    ([[feedback-measurement-must-list-its-inputs]]).

    PLAN-179 W0/W1 cross-file pass: also looks inside the nested
    context-window object, using the SAME candidate keys
    ``.claude/scripts/statusline-ceo.py:context_pct()`` already established for
    this harness. Reading only the top level made the floor guard a no-op on
    every shape that repo has actually observed."""
    for key in ("used_tokens", "usedTokens"):
        val = event.get(key)
        if isinstance(val, bool):  # bool is an int subclass — never a token count
            continue
        if isinstance(val, int):
            return val if val >= 0 else None
    for key in _CONTEXT_WINDOW_KEYS:
        window = event.get(key)
        if not isinstance(window, dict):
            continue
        for used_key in _CONTEXT_USED_KEYS:
            used = _num(window.get(used_key))
            if used is not None:
                return int(used) if used >= 0 else None
    return None


def _sidecar_override_safe(raw: str, target: Path) -> bool:
    """True iff the CEO_STATUSLINE_SIDECAR override is NOT a symlink target,
    has no symlinked immediate parent, and no '..' traversal segment.

    Rail round-7 [P2]: byte-mirrors ``statusline-ceo.py:_sidecar_override_safe``
    — reader and WRITER must accept and reject the SAME overrides, or the
    reader can consume a path the writer refused (crafted data with matching
    identity) while real telemetry lands on the default path unread."""
    try:
        if ".." in raw.replace("\\", os.sep).split(os.sep):
            return False
        if os.path.islink(str(target)):
            return False
        parent = target.parent
        if parent.exists() and os.path.islink(str(parent)):
            return False
    except OSError:
        return False
    return True


def _context_pct_from_sidecar(
    session_id: Optional[str] = None, cwd: Optional[str] = None
) -> Optional[int]:
    """Context-usage percent read from the statusline sidecar, or None.

    PLAN-179 rail round-5 [P2] — IDENTITY IS CHECKED BEFORE THE VALUE IS USED.
    This repo's own W0 measurement recorded the finding
    (`PLAN-179/w0-measurement.md`): the sidecar is SHARED and gets rewritten
    with another repository's `project_dir` while a session runs. Reading
    `context_pct` blind would therefore let one session's pressure be reported
    as another's AND re-arm the wrong hysteresis marker, suppressing the next
    genuine transition — a wrong measurement that looks like a right one,
    which is worse than none. So the sidecar's `session_id` and `project_dir`
    must match this invocation, and a mismatch (or a missing identity field)
    returns None: the guard degrades to silence rather than to fiction.

    PLAN-179 rail round-4 [P2] — THE fix for a dead instrument. The documented
    PreCompact input carries ONLY ``trigger`` and ``custom_instructions``
    (`.claude/data/hook-schema-2.1.220.json`), so reading token accounting from
    the event can never succeed in production: with the floor armed, every real
    PreCompact took the "no measurement" skip path and the sole producer of
    ``context_pressure_observed`` could not emit. The integration test passed
    only because it injected a statusline-shaped payload the hook never
    receives — a test feeding its subject something production does not send.

    There IS a real source: ``statusline-ceo.py`` writes
    ``<audit-dir>/state/statusline-snapshot.json`` with a ``context_pct``
    field, refreshed as the session runs. This reads THAT, read-only and
    fail-soft: unreadable, absent, malformed or non-numeric all yield None and
    the guard stays a no-op. Nothing is estimated from the transcript.

    Freshness is deliberately NOT checked here: a stale percent is still a
    measurement someone took, and the alternative (inventing one) is the thing
    W0 exists to prevent. The row it produces is a bucket transition, not a
    precise reading."""
    # PLAN-179 rail round-6 [P2]: resolve the sidecar the SAME way the writer
    # does, override included. `statusline-ceo.py` honours a full-path override
    # in CEO_STATUSLINE_SIDECAR and only falls back to
    # `<audit-dir>/state/statusline-snapshot.json`. Reading just the fallback
    # meant that any adopter using the override got silence instead of
    # telemetry — a reader and a writer disagreeing about where the file is.
    _override = os.environ.get("CEO_STATUSLINE_SIDECAR", "").strip()
    snap = None
    if _override:
        # Rail round-7 [P2]: resolve AND validate exactly like the writer
        # (`statusline-ceo.py:_sidecar_path`): expanduser first, then the
        # symlink/traversal rejection. A rejected override falls through to
        # the default — that is where the writer actually wrote.
        _target = Path(os.path.expanduser(_override))
        if _sidecar_override_safe(_override, _target):
            snap = _target
    if snap is None:
        try:
            # Reuse the ONE resolver the audit rail already uses, so the
            # fallback path is looked up where the writer put it — including
            # under test isolation, which redirects it.
            from _lib import audit_emit as _ae  # noqa: E402
            base = _ae._audit_dir()
        except Exception:
            return None
        snap = Path(base) / "state" / "statusline-snapshot.json"
    try:
        if not snap.is_file():
            return None
        with snap.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        # --- identity gate (round-5 [P2]) -------------------------------
        # Both sides must be present AND equal. An absent identity field is a
        # MISMATCH, not a pass: a sidecar that cannot say whose it is cannot
        # be attributed, and attributing it anyway is the defect.
        snap_sid = data.get("session_id")
        if session_id:
            if not isinstance(snap_sid, str) or snap_sid != session_id:
                return None
        elif snap_sid:
            # No trusted id on this side: refuse rather than accept a value
            # that demonstrably belongs to SOME session we cannot match.
            return None
        snap_proj = data.get("project_dir")
        if cwd:
            try:
                # Rail round-8 [P2]: o escritor grava workspace.project_dir
                # (o ROOT do projeto); o cwd do hook pode ser um SUBDIRETÓRIO
                # dele (CwdChanged). Igualdade estrita rejeitava sidecar
                # válido e o evento de pressão ficava mudo em produção.
                # Aceita se cwd É o root ou vive DENTRO dele — outro repo
                # continua sendo mismatch.
                _cwd_r = Path(cwd).resolve()
                _proj_r = (
                    Path(snap_proj).resolve()
                    if isinstance(snap_proj, str) and snap_proj else None
                )
                same = _proj_r is not None and (
                    _cwd_r == _proj_r or _proj_r in _cwd_r.parents
                )
            except Exception:
                same = False
            if not same:
                return None
        elif snap_proj:
            return None
        # ----------------------------------------------------------------
        pct = data.get("context_pct")
        if isinstance(pct, bool) or not isinstance(pct, (int, float)):
            return None
        return max(0, min(100, int(pct)))
    except Exception:
        return None


def _context_used_pct(event: Dict[str, Any]) -> Optional[int]:
    """Share of the context window already consumed, as an INTEGER percent.

    PLAN-179 W0/W1 cross-file pass — this is the input the wire actually wants.
    ``audit_emit`` validates ``used_bucket`` as an integer PERCENT rung, so a
    percent (not a token count) has to be derived before the emit; the previous
    token-count bucket could never match a rung and was dropped by the scrub.

    Candidate shapes mirror ``statusline-ceo.py:context_pct()`` — the direct
    percentage first, then used/size — so the two surfaces read the same
    harness payload rather than each guessing. Returns None when the input
    carries no context-window accounting at all; NOTHING is estimated from the
    transcript. Integer-only by construction: the value ends up in an
    HMAC-covered field and a float there discards the whole event
    ([[feedback-float-in-hmac-field-drops-whole-event]])."""
    for key in _CONTEXT_WINDOW_KEYS:
        window = event.get(key)
        if not isinstance(window, dict):
            continue
        for pct_key in _CONTEXT_PCT_KEYS:
            pct = _num(window.get(pct_key))
            if pct is not None:
                return max(0, min(100, int(pct)))
        used = None  # type: Optional[float]
        for used_key in _CONTEXT_USED_KEYS:
            used = _num(window.get(used_key))
            if used is not None:
                break
        size = None  # type: Optional[float]
        for size_key in _CONTEXT_SIZE_KEYS:
            size = _num(window.get(size_key))
            if size is not None:
                break
        if used is not None and size is not None and size > 0:
            return max(0, min(100, int(used * 100.0 / size)))
    return None


def _pressure_bucket(used_pct: Optional[int], rungs: Any) -> int:
    """Highest closed rung the observed percent reached, or the 0 sentinel.

    ``rungs`` is ``audit_emit._CONTEXT_PRESSURE_USED_BUCKETS_PCT`` — passed in
    rather than re-declared so the caller owns the "derive, never recall"
    property. Below the lowest rung (or no measurement at all) returns
    :data:`_PRESSURE_BUCKET_UNKNOWN`, which audit_emit documents as
    "unrecognized / absent bucket" and keeps deliberately outside the enum."""
    if used_pct is None:
        return _PRESSURE_BUCKET_UNKNOWN
    reached = [int(r) for r in rungs if isinstance(r, int) and used_pct >= r]
    return max(reached) if reached else _PRESSURE_BUCKET_UNKNOWN


def _progress_guard(
    used_tokens: Optional[int],
    floor_tokens: int,
    used_pct: Optional[int],
    plan_id: str,
    cwd: str,
    session_id: Optional[str] = None,
) -> None:
    """OBSERVE + NOTIFY the context-pressure crossing (PLAN-179 W0 US2b).

    The plan's wording is "HALTAR a tentativa automática". This hook CANNOT
    halt anything and saying otherwise would be a false claim on a governance
    surface: ``gate()`` returns ``{}`` by contract, PreCompact has no deny
    channel, and by the time the hook fires the harness has already decided to
    compact. So the guard is implemented honestly as its observable half — a
    stderr breadcrumb for the operator plus one closed-enum audit event — and
    the valve question CLOSED by ratification (2026-08-31, US2b-valve):
    eta advisory + doctrine via ``_eta_advisory``; deny is a documented
    substrate limit owned by no surface (PreCompact has no deny channel).

    Emits ``context_pressure_observed`` with ``event_source="precompact"``, the
    strict ``plan_id`` and the crossed integer PERCENT rung in ``used_bucket``.

    ``session_id`` (PLAN-179 rail finding A, round-1 REJECT) is the TRUSTED
    hook-input id — the same value ``_session_scope_id`` derives through
    ``scratchpad_lib.session_id_from_event``, which REFUSES the env-sourced
    ``CLAUDE_SESSION_ID`` (agent-spoofable, consensus M2). It does two things:
    it KEYS the hysteresis marker, so two sessions compacting in the same repo
    no longer suppress and re-arm each other's rung transitions; and it rides
    the event (an allowlisted field), so the wire rows can be attributed back
    to a session and the true transitions recovered.

    When there is no trusted id the guard DEGRADES rather than inventing one:
    the marker falls back to the project-wide file (cross-session interference
    possible, exactly the pre-fix behaviour) and ``session_id`` is OMITTED from
    the event. Omitting is the honest option — an event whose session_id came
    from the environment would be an attributable-looking row that an agent
    chose, which is worse than a row that admits it is unattributed. Skipping
    the emit outright was rejected: this pressure rail is the measurement W0
    exists to make, and dropping the observation to protect a bookkeeping
    field would lose the signal to save the label.

    PLAN-179 W0/W1 cross-file pass — three integration defects closed here,
    all of the same class (an instrument that runs but cannot fire):

    1. The edge trigger was probed as ``audit_emit.edge_trigger_should_emit``,
       a name that does not exist. The probe therefore matched None on EVERY
       run and the guard returned before emitting — a silent dead instrument.
       The shipped symbol is ``should_emit_context_pressure(used_bucket,
       state_dir)``, and ``state_dir`` is ``<project>/.claude/state``, so the
       call needs the repo root the guard previously never received.
    2. The emitted fields were ``used_tokens_bucket`` and ``floor_tokens``.
       Neither is in ``_CONTEXT_PRESSURE_OBSERVED_ALLOWLIST``, whose scrub is
       deny-by-default, so both were dropped and the wire carried a coerced
       ``used_bucket=0`` forever. The allowlisted trio is ``used_bucket`` /
       ``event_source`` / ``plan_id``.
    3. The bucket was a TOKEN-COUNT rung (``used_tokens // 10000``), which can
       never satisfy the type-strict percent check ``used_bucket in
       {40,60,80,90,95}``. It is now the percent rung derived by
       ``_context_used_pct`` + ``_pressure_bucket``.

    Amendment 8.1 properties preserved: integers with the unit in the name
    (never a float under HMAC —
    [[feedback-float-in-hmac-field-drops-whole-event]]) and EDGE-TRIGGERED, so
    a session that sits in the same rung does not spam the log (OQ-4). The
    breadcrumb is NOT edge-gated: it is the operator notification and fires at
    most once per compaction anyway. ``floor_tokens`` stays in the breadcrumb —
    it is operator context, and the wire deliberately refuses raw token
    counts."""
    # PLAN-179 rail round-4 [P2]: `used_tokens` is None whenever the only
    # available measurement is the statusline sidecar's PERCENT — which, given
    # the documented PreCompact input, is the normal production case. The floor
    # comparison needs an absolute count, so it is SKIPPED then; the pressure
    # OBSERVATION still happens, because that observation is the entire
    # deliverable of W0 US2b and dropping it to protect a comparison would
    # discard the measurement to preserve a threshold nobody can evaluate.
    if used_tokens is not None and used_tokens < floor_tokens:
        return
    try:
        from _lib import audit_emit  # noqa: E402
    except Exception:
        _breadcrumb("audit_emit import failed — pressure emit suppressed")
        return
    # Derive the closed rung set from its owner. Absent ⇒ this adopter predates
    # PLAN-179 W0 US2 and the `context_pressure_observed` action is not
    # registered either, so the emit would be dropped whatever we sent: suppress
    # honestly instead of writing into a void.
    rungs = getattr(audit_emit, _PRESSURE_RUNGS_ATTR, None)
    if not rungs:
        _breadcrumb(
            "audit_emit.%s missing — this build predates PLAN-179 W0 US2; "
            "pressure emit suppressed" % _PRESSURE_RUNGS_ATTR
        )
        return
    bucket = _pressure_bucket(used_pct, rungs)
    _breadcrumb(
        "context pressure observed: used_bucket_pct=%d floor_tokens=%d "
        "used_tokens=%s (observe+notify only — this hook cannot halt a "
        "compaction)"
        % (
            bucket,
            floor_tokens,
            # "none (percent-only source)" rather than a fabricated 0: the
            # operator must be able to tell "no absolute count was available"
            # from "the count was zero".
            used_tokens if used_tokens is not None else "none (percent-only source)",
        )
    )
    if bucket == _PRESSURE_BUCKET_UNKNOWN:
        _breadcrumb(
            "no context-window accounting in the hook input (or below the "
            "lowest rung) — emitting used_bucket=0, the audit_emit sentinel "
            "for an absent rung; no percent is invented"
        )
    # Edge trigger lives in audit_emit (amendment 8.1) and is fail-OPEN by its
    # own contract (state I/O errors mean "emit"), so any exception escaping it
    # is a genuine surprise: breadcrumb and suppress rather than double-emit.
    should_emit = getattr(audit_emit, "should_emit_context_pressure", None)
    if should_emit is None:
        _breadcrumb(
            "audit_emit.should_emit_context_pressure missing — this build "
            "predates PLAN-179 W0 US2; pressure emit suppressed"
        )
        return
    state_dir = os.path.join(cwd, *_PRESSURE_STATE_SUBPATH)
    trusted_sid = session_id.strip() if isinstance(session_id, str) else ""
    try:
        # PLAN-179 rail finding A — pass the trusted session id so the marker
        # is keyed per session. TypeError is handled SEPARATELY from the
        # general failure below: it is the signature of an adopter whose
        # `_lib/audit_emit.py` predates this fix (2-parameter helper). That is
        # a cross-version DEGRADATION (project-wide marker), not a reason to
        # suppress the observation, so we say so and retry the old shape.
        try:
            _emit_allowed = should_emit(bucket, state_dir, trusted_sid or None)
        except TypeError:
            _breadcrumb(
                "audit_emit.should_emit_context_pressure does not accept a "
                "session id — this build predates PLAN-179 finding A; falling "
                "back to the PROJECT-WIDE marker (concurrent sessions in this "
                "repo can suppress each other's transitions)"
            )
            _emit_allowed = should_emit(bucket, state_dir)
        if not _emit_allowed:
            return
    except Exception as exc:
        _breadcrumb("edge trigger failed (%s) — emit suppressed" % str(exc)[:60])
        return
    # PLAN-179 rail finding A — session_id is an ALLOWLISTED wire field, but
    # only a trusted one may travel. Absent ⇒ the key is omitted entirely: the
    # row is honestly unattributed instead of carrying an env-sourced id.
    # PLAN-179 rail round-2 [P2]: `project` is an allowlisted field the SPEC
    # declares required, and `emit_generic`/`_write_event` do NOT synthesize it
    # — a row without it cannot be correlated per-project by a consumer reading
    # a shared log. Resolved by the same precedence every other hook uses
    # (`check_agent_spawn.py:301`), and bounded like the sibling call sites.
    fields: Dict[str, Any] = {
        "event_source": _PRESSURE_EVENT_SOURCE,
        "used_bucket": bucket,
        "plan_id": plan_id,
        "project": str(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())[:256],
    }
    if trusted_sid:
        fields["session_id"] = trusted_sid
    else:
        _breadcrumb(
            "no hook-input session id — pressure row emitted UNATTRIBUTED and "
            "the hysteresis marker is project-wide for this run"
        )
    try:
        audit_emit.emit_generic(
            action="context_pressure_observed",
            **fields
        )
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("pressure emit failed (%s)" % str(exc)[:80])


# PLAN-179 US2b-valve (Owner-ratified 2026-08-31) — MEASURED constants from
# `PLAN-179/w0-measurement.md` §C/§E. F+S is the re-paid gate-boot floor at a
# real compaction boundary (TOTAL_IN 112638 − postTokens 15346, decomposed as
# cache_read 68980 + cache_creation 28310); T is the context-window total the
# same measurement derived. Integers only — η travels as permille.
_ETA_FLOOR_REPAID_TOKENS = 112638  # F+S, measured
_ETA_WINDOW_TOKENS = 998043        # T, measured


def _eta_advisory() -> None:
    """The US2b VALVE, as ratified (2026-08-31): η advisory + doctrine.

    η = (T − F − S)/T with the measured constants above — the usable-context
    ratio kept after paying the compaction's re-boot floor. TWO stderr lines
    per compaction (the breadcrumb clamps at 160 chars), ADVISORY by
    doctrine. The two halves the original valve item named resolve as:
    (i) "a channel able to DENY" — does not exist: PreCompact has no deny
    channel and ``gate()`` returns ``{}`` by contract, so refusal is
    documented as a SUBSTRATE limit (the same honest route as US9c's
    eviction verdict), never claimed as hook behaviour; (ii) "η computed,
    not a token threshold" — computed here, integer permille, no floats."""
    eta_permille = (
        (_ETA_WINDOW_TOKENS - _ETA_FLOOR_REPAID_TOKENS) * 1000
    ) // _ETA_WINDOW_TOKENS
    # Rail r2 P1-e: the constants are THIS framework repo's measured trace
    # (w0-measurement §C/§E), not a property of every installation — F
    # varies with the governance surface, T with the model. The advisory
    # SAYS so (no cross-repo efficiency claim; AGENTS no-claim rule).
    _breadcrumb(
        "valve (advisory; framework-trace numbers, measure your own — "
        "guide sec.5): re-pays F+S=%d on T=%d — eta=(T-F-S)/T = %d "
        "permille (%d.%d%%)"
        % (
            _ETA_FLOOR_REPAID_TOKENS,
            _ETA_WINDOW_TOKENS,
            eta_permille,
            eta_permille // 10,
            eta_permille % 10,
        )
    )
    _breadcrumb(
        "valve doctrine: PreCompact has NO deny channel — refusing a "
        "compaction is a substrate limit (US2b-valve, ratified 2026-08-31)"
    )
