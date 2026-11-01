"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



def _emit_task_candidate_markers(
    results: List[CheckResult],
    *,
    gate_pass: bool,
    short: bool,
    cached: bool,
) -> List[Dict[str, Any]]:
    """Write `<!-- TASKCREATE-CANDIDATE -->` blocks to stdout for top-3 recs.

    Layer A of PLAN-078 Wave 5. Bypass paths (return [] without emit):
        * `gate_pass` is True (no actionable failure)
        * `short` mode (≤2s budget — skip per Perf table)
        * `cached` mode (handled by uncached path on next non-cached boot)
        * Env `CEO_BOOT_AUTO_TASK=0` (operator opt-out)
        * No medium/high recommendations after dedup

    Returns the list of marker payloads emitted (used by tests + future
    JSON renderer). Each payload carries `rank`, `severity`,
    `subject_hash`, `subject` (not persisted — only stdout), and
    `awaiting_confirm`.

    Sec MF-3 closure: `subject` text passes through `_sanitize_for_recs`
    (already applied by `_recommendations_with_severity` callee) before
    rendering; only the 12-hex `subject_hash` is persisted to the
    audit-log + dedup state. Raw stderr / check detail NEVER appears in
    the marker block.
    """
    if gate_pass:
        return []
    if short or cached:
        return []
    if os.environ.get("CEO_BOOT_AUTO_TASK") == "0":
        return []

    triples = _recommendations_with_severity(results)
    # Codex CDX-W5-P1-01 closure: do NOT pre-slice to TASK_EMIT_TOP_N
    # before dedup. Iterate the full medium+/high actionable list and
    # break only after we've emitted TOP_N markers — otherwise three
    # already-deduped subjects at the head of the list would silently
    # block any 4th candidate from ever surfacing.
    actionable = [(t, s) for (_, t, s) in triples if s in ("medium", "high")]
    if not actionable:
        return []

    state_path = _task_emit_state_path()
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")

    # Acquire filelock for read-modify-write of dedup state. Codex
    # CDX-W5-P1-02 closure: on FileLockTimeout we still emit markers
    # (fail-open — better to over-task once than silently drop) but we
    # do NOT persist the new state. Persisting unlocked state can
    # clobber a sibling process that just acquired the lock and wrote
    # different entries (lost-update). Operator pays the price of one
    # duplicate marker on the next boot in exchange for not corrupting
    # the audit-bookkeeping channel.
    #
    # Codex CDX-W5-iter3-P1 closure: any exception during lock acquisition
    # (OSError on bad path, PermissionError, NotImplementedError on
    # non-POSIX, etc.) used to fall through the OUTER except and silently
    # suppress every marker. We now narrow the lock-acquire try/except to
    # just lock setup; the marker-emit loop runs unconditionally with
    # `lock_acquired = False` if anything went wrong.
    emitted: List[Dict[str, Any]] = []
    rank = 0
    lock_acquired = False
    state: Dict[str, Any] = {"entries": []}
    lock_ctx = None

    # --- Phase 1: try to acquire the lock + load state ---
    try:
        try:
            from _lib.filelock import FileLock, FileLockTimeout
        except Exception:  # noqa: BLE001 — pre-canonical or import-broken
            FileLock = None  # type: ignore[assignment]
            FileLockTimeout = Exception  # type: ignore[assignment]

        if FileLock is None:
            # No filelock available (pre-canonical / non-POSIX). Read
            # state opportunistically; allow persistence (best-effort).
            state = _load_task_emit_state(state_path)
            lock_acquired = True  # treat as "owned" for save semantics
        else:
            try:
                lock_ctx = FileLock(str(lock_path), timeout=2.5)
                lock_ctx.__enter__()
                state = _load_task_emit_state(state_path)
                lock_acquired = True
            except FileLockTimeout:
                # Lock contended — emit unlocked, skip persist.
                state = _load_task_emit_state(state_path)
                lock_ctx = None
                lock_acquired = False
            except Exception:  # noqa: BLE001 — invalid path, perm err, etc.
                # Any other error during lock acquisition — emit
                # unlocked, skip persist. Empty state means we may
                # over-emit (no dedup), but that's better than silent
                # suppression.
                state = {"entries": []}
                lock_ctx = None
                lock_acquired = False
                if os.environ.get("CEO_BOOT_DEBUG") == "1":
                    import traceback
                    traceback.print_exc(file=sys.stderr)
    except Exception:  # noqa: BLE001 — never let phase-1 abort markers
        state = {"entries": []}
        lock_ctx = None
        lock_acquired = False
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)

    # --- Phase 2: emit markers + persist (always runs, even after
    # phase-1 failure). Wrapped in its own try/except so any state-file
    # bug NEVER blocks the user session. ---
    try:
        now = time.time()
        for text, severity in actionable:
            # Codex CDX-W5-P1-05 closure: collapse interior whitespace
            # so the `Subject:` line stays single-line — newlines in a
            # recommendation summary would otherwise ambiguate the
            # closing marker for the orchestrator parser.
            safe_subject = _collapse_marker_subject(text)
            # Codex CDX-W5-iter2-P1 closure: hash the COLLAPSED subject
            # (the bytes the orchestrator actually parses + re-hashes
            # for dedup against the live task list). Hashing the raw
            # pre-collapse text would break the contract documented in
            # `commands/ceo-boot.md:Step 4.5` where the orchestrator
            # computes `sha256(NFKC(visible Subject))[:12]`.
            sh = _subject_hash(safe_subject)
            if _is_subject_recent(state, sh):
                continue
            rank += 1
            payload = {
                "rank": rank,
                "severity": severity,
                "subject_hash": sh,
                "subject": safe_subject,
                "awaiting_confirm": False,
            }
            sys.stdout.write(
                f"\n<!-- TASKCREATE-CANDIDATE rank={rank} "
                f"severity={severity} awaiting_confirm=false -->\n"
            )
            sys.stdout.write(f"Subject: {safe_subject}\n")
            sys.stdout.write("<!-- /TASKCREATE-CANDIDATE -->\n")
            state["entries"].append({"subject_hash": sh, "ts": now})
            emitted.append(payload)
            _emit_task_candidate_safe(
                rank=rank,
                severity=severity,
                subject_hash=sh,
                awaiting_confirm=False,
            )
            if rank >= TASK_EMIT_TOP_N:
                break
        # Codex CDX-W5-iter3 P2: keep state size bound after the post-load
        # append (load trims to MAX_ENTRIES, but we just added up to TOP_N
        # entries on top — re-cap before save so persisted state never
        # exceeds the documented MAX). LRU keep most-recent.
        entries = state.get("entries", [])
        if isinstance(entries, list) and len(entries) > TASK_EMIT_STATE_MAX_ENTRIES:
            entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
            state["entries"] = entries[:TASK_EMIT_STATE_MAX_ENTRIES]
        if emitted and lock_acquired:
            _save_task_emit_state(state_path, state)
    except Exception:  # noqa: BLE001 — fail-open: a state-file bug must
        # NEVER block the user session
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)
    finally:
        if lock_ctx is not None:
            try:
                lock_ctx.__exit__(None, None, None)
            except Exception:  # pragma: no cover — fail-open
                pass
    return emitted


# === END PLAN-078 Wave 5 marker emit + dedup ===============================


# ---- Main ------------------------------------------------------------------

# === PLAN-134 W4 — Morning Ledger renderer ================================
# Renders the proposal-queue ledger (sign / don't sign / why, founder
# language) as an extra default-mode section — same pattern as the Wave 5
# TASKCREATE markers: NOT a Tier-S check (the registry is pinned at 20),
# never affects gate_pass, fail-open on any error. Fast mode only
# (manifest-level Merkle re-derivation); byte-level verification belongs to
# morning-ceremony.py. Kill switch: CEO_BOOT_LEDGER=0.
def _render_morning_ledger_safe() -> str:
    if os.environ.get("CEO_BOOT_LEDGER", "1") == "0":
        return ""
    try:
        import importlib.util as _ilu
        _ml_path = Path(__file__).resolve().parent / "morning_ledger.py"
        if not _ml_path.is_file():
            return ""
        _ml = sys.modules.get("morning_ledger")
        if _ml is None:
            _spec = _ilu.spec_from_file_location("morning_ledger", _ml_path)
            _ml = _ilu.module_from_spec(_spec)
            # py3.9 dataclasses + `from __future__ import annotations`
            # resolve field types via sys.modules[cls.__module__] — the
            # module MUST be registered before exec_module.
            sys.modules["morning_ledger"] = _ml
            _spec.loader.exec_module(_ml)  # type: ignore[union-attr]
        if not _ml.pending_bundles():
            return ""
        rendered = _ml.render_ledger(deep=False)
        # Defense-in-depth: ledger text is disk-sourced — pass each line
        # through the same sanitizer the recommendations use (Sec MF-4).
        safe_lines = [_sanitize_for_recs(ln) if ln.strip() else ln for ln in rendered.splitlines()]
        return "\n" + "\n".join(safe_lines) + "\n"
    except Exception:  # noqa: BLE001 — advisory section, never block boot
        if os.environ.get("CEO_BOOT_DEBUG") == "1":
            import traceback
            traceback.print_exc(file=sys.stderr)
        return ""


# === PLAN-154 item 4 — Past-lessons fenced one-liners ======================
# Renders the top-3 APPROVED lesson one-liners as a fenced untrusted-data
# section in the default full digest. Same integration pattern as the
# PLAN-134 W4 Morning Ledger: NOT a Tier-S check (registry pinned at 23),
# never affects gate_pass, fail-open on any INFRASTRUCTURE error (boot must
# never break), rendered ONLY in default full markdown mode — never under
# --short / --cached / --json, and never written to the boot cache. That
# structural exclusion is how lesson text joins the `/ceo-boot --json`
# DENIED fields (LLM06 side-channel guard, PLAN-154 A5).
#
# Security posture (PLAN-154 A5/A6/A9 + PLAN-152 C4 fail-closed-on-input):
#   * Source of truth = `lessons.get_boot_lessons_verified(project_dir,
#     now_fn=None)` (PLAN-154 wave-0 interface contract): lessons.py owns
#     bounded-vocab validation, TTL/decay, and the A6 sha256
#     verify-before-render against the HMAC chain's approval events
#     (mismatch → dropped upstream + integrity breadcrumb). Imported
#     DEFENSIVELY: function missing (pre-B2 landing) → render nothing +
#     fail-open stderr breadcrumb.
#   * The renderer is an INDEPENDENT fail-CLOSED gate (defense-in-depth,
#     applied per lesson, any failure → DROP that lesson):
#       shape    — dict with bounded lesson_id + 64-hex content_sha256;
#       vocab    — no backticks (fence escape impossible by construction),
#                  no newlines / CR / NUL (A5 bounded vocabulary);
#       cap      — ≤3 lessons × ≤200 chars post-NFKC, ASSERTED not
#                  truncated (the lessons.py schema cap guarantees length;
#                  no new truncation code — an oversize lesson is dropped);
#                  cap-then-fence ordering (cap applies before fencing);
#       validate — fail-CLOSED `_lib.guardrail_validator.validate_text`
#                  (G1/MOIM posture per check_read_injection.py — NOT the
#                  advisory scanner). Validator import failure or a raise
#                  inside the call is treated as scanner-unavailable →
#                  lessons DROPPED (the module itself allows on internal
#                  exception, so THIS caller enforces the fail-closed
#                  direction);
#       scan     — the EXISTING `_sanitize_for_recs` bound+scan pipeline
#                  (NFKC + harness-mimicry scan); a redaction hit → the
#                  lesson is DROPPED, never rendered redacted.
#   * Drops surface count-only in the section (A6 integrity flag) and emit
#     `lesson_boot_render_dropped` audit events with closed fields only
#     (silent no-op until the integrator registers the action).
#   * The A9 pending-expiry warning is COUNT-ONLY — zero candidate text
#     can reach boot through the warning side door.
#
# Kill-switch story (PLAN-154 constraint 9 / A12): opt-in
# CEO_LEARNING_BOOT_LESSONS=1 (unset = structurally OFF, cost_envelope
# posture — zero lesson-store I/O when off); CEO_SOTA_DISABLE=1 master
# precedence. An EXPLICIT disable (switch set to a non-"1" value, or SOTA
# master kill while opted in) emits one `learning_rail_disabled` breadcrumb
# per invocation (rail=boot_render) for Wave-E liveness; merely-unset emits
# nothing (structurally off is not an operator disable).

LESSONS_BOOT_MAX_ITEMS = 3
LESSONS_BOOT_MAX_CHARS = 200
# Defensive processing bound on the upstream list (contract says ≤3; a
# misbehaving provider cannot make the renderer O(huge)).
_LESSONS_BOOT_SCAN_BOUND = 16
# Bounded identifier charsets (fail-closed shape gate).
_LESSON_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")
_LESSON_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# Closed drop-reason enum (mirrored in the `lesson_boot_render_dropped`
# audit action registration owned by the integrator).
_LESSON_BOOT_DROP_REASONS = frozenset({
    "bad_shape", "hash_malformed", "vocab", "oversize",
    "validator_unavailable", "validator_block", "scan_redacted",
    "excess", "other",
})
# Sentinel: distinguishes "use the default loader" from an explicit
# None (= validator unavailable) in test seams.
_UNSET = object()


def _lessons_boot_rail_state() -> Tuple[bool, str]:
    """Resolve the boot_render rail switch state.

    Returns ``(enabled, disabled_switch)``. ``disabled_switch`` is the
    non-empty switch name ONLY for an explicit operator disable (recorded
    choice — feeds the A12 disabled-this-session breadcrumb); merely-unset
    returns ``(False, "")`` (structurally off, no breadcrumb, no I/O).
    """
    opt_in = os.environ.get("CEO_LEARNING_BOOT_LESSONS")
    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        # Master kill. Breadcrumb only when the operator had opted in
        # (a rail that WOULD be live is disabled — liveness-relevant).
        return False, ("CEO_SOTA_DISABLE" if opt_in == "1" else "")
    if opt_in == "1":
        return True, ""
    if opt_in is None or opt_in == "":
        return False, ""
    return False, "CEO_LEARNING_BOOT_LESSONS"


def _emit_learning_rail_disabled_safe(switch: str) -> None:
    """A12 disabled-this-session breadcrumb (rail=boot_render). Fail-open.

    Rides `emit_generic` — a silent no-op until the integrator registers
    the `learning_rail_disabled` action (pre-registration no-op contract).
    Closed fields only: rail / switch enums + session_id.
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_generic", None)
    if not callable(fn):
        return
    try:
        fn(
            "learning_rail_disabled",
            rail="boot_render",
            switch=switch if switch in (
                "CEO_LEARNING_BOOT_LESSONS", "CEO_SOTA_DISABLE"
            ) else "other",
            session_id=_ceo_boot_session_id(),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        pass


def _emit_lesson_boot_render_dropped_safe(reason: str, lesson_id: str = "") -> None:
    """Audit breadcrumb for a render-gate drop. Fail-open; closed fields only.

    `lesson_id` is forwarded only when it matches the bounded identifier
    charset (else empty) — no free text can ride this event.
    """
    if _audit_emit is None:
        return
    fn = getattr(_audit_emit, "emit_generic", None)
    if not callable(fn):
        return
    try:
        safe_reason = reason if reason in _LESSON_BOOT_DROP_REASONS else "other"
        safe_id = lesson_id if (
            isinstance(lesson_id, str) and _LESSON_ID_RE.match(lesson_id)
        ) else ""
        fn(
            "lesson_boot_render_dropped",
            reason=safe_reason,
            lesson_id=safe_id,
            session_id=_ceo_boot_session_id(),
        )
    except Exception:  # noqa: BLE001 — fail-open per audit_emit contract
        pass


def _load_lessons_module() -> Any:
    """Load sibling lessons.py (morning_ledger import pattern). Fail-open None."""
    try:
        import importlib.util as _ilu
        path = Path(__file__).resolve().parent / "lessons.py"
        if not path.is_file():
            return None
        mod = sys.modules.get("lessons")
        if mod is None:
            spec = _ilu.spec_from_file_location("lessons", path)
            mod = _ilu.module_from_spec(spec)
            # py3.9 dataclasses + `from __future__ import annotations`
            # resolve field types via sys.modules[cls.__module__].
            sys.modules["lessons"] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    except Exception:  # noqa: BLE001 — fail-open
        return None


def _load_guardrail_validator() -> Any:
    """Import the fail-CLOSED validator module. None on failure.

    The CALLER treats None (or a raise inside validate_text) as
    scanner-unavailable → drop-the-lesson (PLAN-154 A5; the module's own
    outer except returns allow, so the fail-closed direction is enforced
    HERE, mirroring check_read_injection.py's G1 consumption).
    """
    try:
        from _lib import guardrail_validator as _gv  # type: ignore
        return _gv
    except Exception:  # noqa: BLE001
        return None


def _validate_boot_lesson(
    entry: Any,
    validator_mod: Any,
) -> Tuple[Optional[Dict[str, str]], str]:
    """Fail-CLOSED per-lesson render gate.

    Returns ``({"lesson_id": ..., "text": <render-safe text>}, "")`` on
    pass, or ``(None, <closed drop reason>)`` on ANY failure. Never raises.
    """
    try:
        if not isinstance(entry, dict):
            return None, "bad_shape"
        lesson_id = entry.get("lesson_id")
        text = entry.get("text")
        content_sha256 = entry.get("content_sha256")
        if not (
            isinstance(lesson_id, str)
            and isinstance(text, str)
            and isinstance(content_sha256, str)
        ):
            return None, "bad_shape"
        if not _LESSON_ID_RE.match(lesson_id):
            return None, "bad_shape"
        if not _LESSON_SHA256_RE.match(content_sha256):
            return None, "hash_malformed"
        # Bounded vocabulary (A5): backticks are what would let content
        # escape the ``` fence; newlines/CR would let one lesson smuggle
        # extra lines (or a fence close) into the block; NUL is binary
        # garbage. Checked on the RAW text (NFKC preserves all four).
        if ("`" in text) or ("\n" in text) or ("\r" in text) or ("\x00" in text):
            return None, "vocab"
        # NFKC normalize BEFORE the cap check so ligature/fullwidth
        # expansion cannot dodge the 200-char bound (ceo-boot.md pipeline
        # order: post-NFKC bound). Cap is ASSERTED, never truncated.
        try:
            norm = unicodedata.normalize("NFKC", text)
        except (TypeError, ValueError):
            return None, "bad_shape"
        if not norm.strip():
            return None, "bad_shape"
        if len(norm) > LESSONS_BOOT_MAX_CHARS:
            return None, "oversize"
        # Fail-CLOSED validator route (A5) — NOT the advisory scanner.
        if validator_mod is None:
            return None, "validator_unavailable"
        validate_fn = getattr(validator_mod, "validate_text", None)
        if not callable(validate_fn):
            return None, "validator_unavailable"
        try:
            verdict = validate_fn(norm)
            decision = getattr(verdict, "decision", "block")
        except Exception:  # noqa: BLE001 — infra raise at a fail-closed boundary
            return None, "validator_unavailable"
        if decision != "allow":
            return None, "validator_block"
        # Existing bound+scan pipeline (Sec MF-4). Given the asserted
        # ≤200-char post-NFKC input this NEVER truncates; it only
        # NFKC-idempotently re-normalizes, scans for harness mimicry,
        # and strips <> / markdown-link syntax. A redaction hit → DROP
        # (never render the redaction placeholder as a lesson).
        rendered = _sanitize_for_recs(norm)
        if rendered == "[REDACTED-INJECTION-PATTERN]":
            return None, "scan_redacted"
        if not rendered.strip():
            return None, "bad_shape"
        return {"lesson_id": lesson_id, "text": rendered}, ""
    except Exception:  # noqa: BLE001 — any surprise → fail-closed drop
        return None, "other"


def _lessons_pending_expiry_count(mod: Any, project_dir: str, now_fn: Any) -> int:
    """A9 count-only expiry warning input. Optional API; fail-open 0.

    Consumes `lessons.count_pending_expiring(project_dir, now_fn=None)`
    when present (defensive getattr — pre-B2 it does not exist). Returns
    a bounded non-negative int; anything unparseable → 0 (no warning).
    """
    try:
        fn = getattr(mod, "count_pending_expiring", None)
        if not callable(fn):
            return 0
        try:
            raw = fn(project_dir, now_fn=now_fn)
        except TypeError:
            raw = fn(project_dir)
        n = int(raw)
        if n <= 0:
            return 0
        return min(n, 9999)
    except Exception:  # noqa: BLE001 — warning is advisory, fail-open
        return 0
