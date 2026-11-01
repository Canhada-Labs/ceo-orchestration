"""PreCompact hook dispatch and command-line entry point."""
from __future__ import annotations

def gate(event: Dict[str, Any], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Build + persist the snapshot; emit the closed-enum event. Always allows.

    Returns ``{}`` (PreCompact hooks have no governance output channel — the
    snapshot is the side effect; PostCompact does the reinjection). This is
    also why the PLAN-179 W0 US2b progress guard is observe+notify: there is
    no value of the return that could stop the compaction."""
    if os.environ.get("CEO_COMPACTION_CONTINUITY", "1") == "0":
        return {}
    deadline = time.monotonic() + TIME_BUDGET_S
    # Rail round-9 [P2]: TODO path derivado daqui usa o ROOT do projeto,
    # não o cwd literal do hook-input (que segue CwdChanged) — um único
    # ponto de resolução cura a família inteira (plan lookup, ceremony
    # flags, marker de pressão, identidade do sidecar).
    cwd = _resolve_project_root(os.path.realpath(cwd or os.getcwd()))
    trigger = _trigger_class(event)
    plan_id = _resolve_plan_id(event)
    # PLAN-179 W1 US3 — resolved BEFORE the write so an unresolved plan falls
    # back to the session scope instead of dropping the snapshot on the floor.
    session_id = _session_scope_id(event)
    plan_path = _plan_file_for(plan_id, cwd)
    blob: Dict[str, Any] = {
        "schema": "compaction-continuity/v1",
        "ts": time.time(),
        "trigger": trigger,
        "plan_id": plan_id,
        "execution_unit": _execution_unit(plan_path, cwd, deadline),
        # PLAN-179 W2 US7 — the ledger INDEX: derived from commit PATHS
        # (never _resolve_plan_id), pointing at PLAN-NNN/LEDGER.md +
        # sections + last commit instead of copying state.
        "ledger_index": _ledger_index(cwd, deadline),
        "ceremony_flags": _ceremony_flags(cwd, deadline),
        "hmac_chain": _hmac_chain_breadcrumb(deadline),
    }
    chain_length = 0
    try:
        chain_length = int(blob["hmac_chain"].get("chain_length", 0))
    except (TypeError, ValueError, AttributeError):
        chain_length = 0
    outcome = _write_snapshot(plan_id, blob, session_id)
    _emit_snapshot_event(trigger, plan_id, chain_length, outcome)
    # PLAN-179 US2b-valve — advisory only, AFTER the snapshot + its
    # event: the valve must never delay or endanger the snapshot.
    _eta_advisory()
    # PLAN-179 W0 US2b — last, and only when the operator armed a floor: the
    # guard must never delay or endanger the snapshot above it.
    floor_tokens = _progress_floor_tokens()
    if floor_tokens is not None:
        used_tokens = _used_tokens_from_event(event)
        # PLAN-179 rail round-4 [P2]: the PreCompact input documented by the
        # harness carries NO token accounting, so `used_tokens` is None on
        # every real invocation and the guard was dead by construction — the
        # test only passed because it fed a shape production never sends. The
        # statusline sidecar DOES carry a measured `context_pct`, so fall back
        # to it. Order matters: the event stays PREFERRED (if a future harness
        # version ships accounting inline, that is the fresher number); the
        # sidecar is what makes the guard work TODAY.
        pct = _context_used_pct(event)
        if pct is None:
            # Identity of THIS invocation is passed in: the sidecar is shared
            # across projects (round-5 [P2]) and a value that belongs to
            # someone else must be refused, not consumed.
            pct = _context_pct_from_sidecar(session_id, cwd)
        if used_tokens is None and pct is None:
            _breadcrumb(
                "%s is set but neither the hook input nor the statusline "
                "sidecar carries context accounting — progress guard skipped "
                "(no measurement is invented)" % PROGRESS_FLOOR_ENV
            )
        else:
            # PLAN-179 W0/W1 cross-file pass: the guard now needs the repo root
            # (for should_emit_context_pressure's `<project>/.claude/state`
            # marker), the resolved plan_id (an allowlisted wire field) and the
            # context PERCENT (the wire's actual unit).
            # PLAN-179 rail finding A: also the TRUSTED session id (hook input
            # only — `_session_scope_id` refuses the env-sourced one), which
            # keys the hysteresis marker and attributes the wire row.
            # `pct` above, NOT a second `_context_used_pct(event)` call: the
            # sidecar fallback lives in that variable, and recomputing here
            # would silently drop back to the event-only value that production
            # never carries — re-introducing the dead instrument this round
            # exists to fix.
            _progress_guard(
                used_tokens,
                floor_tokens,
                pct,
                plan_id,
                cwd,
                session_id,
            )
    # PLAN-179 rail finding C (round-1 REJECT) — the PRODUCTION CALLER for the
    # session-store file GC. `set_session_value`'s TTL expires ROWS; nothing
    # removed the `session-<uuid>.sqlite` / `.lock` / `-wal` / `-shm` files, so
    # the W1 US3 fallback still grew one store per unresolved-plan session
    # forever while ADR-153 claimed file-level GC shipped with it.
    #
    # This hook is the natural site because it is what CREATES those stores.
    # Placed LAST, after the snapshot, the audit emit and the progress guard,
    # and fail-open inside `_gc_session_stores`: no snapshot outcome may depend
    # on housekeeping succeeding.
    _gc_session_stores(deadline)
    return {}


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: parse error is infra → breadcrumb + schema-compliant allow.
        sys.stderr.write(
            "# check_precompact_continuity fail-open (stdin): %s\n" % str(exc)[:120]
        )
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input, hook_input.get("cwd"))))
    except Exception as exc:
        sys.stderr.write(
            "# check_precompact_continuity fail-open: %s\n" % str(exc)[:120]
        )
        print("{}")
