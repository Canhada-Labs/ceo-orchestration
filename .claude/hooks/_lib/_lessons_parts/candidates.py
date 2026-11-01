# Implementation section: globals belong to the lessons facade.

from __future__ import annotations

__all__ = ['_candidates_dir', 'candidate_content_sha256', '_validate_candidate_fields', '_load_injection_scanner', '_scan_candidate_fail_closed', '_write_candidate', '_load_candidate', 'list_candidates', 'add_candidate', '_chain_created_at', '_quarantine_candidate', 'approve_candidate', 'expire_pending_candidates', 'pending_expiry_warning_count', 'count_pending_expiring']

def _candidates_dir(base_dir: Optional[str] = None) -> Path:
    """Candidate namespace, SIBLING to live lessons.

    Deliberately a subdirectory: ``list_lessons`` iterates only the
    top level and skips non-``.json`` entries, so legacy readers
    (get_top_k / build_index / prune-lessons / lesson_ranker) can never
    surface a candidate — approved or not — through the unverified path.
    """
    return _lessons_dir(base_dir) / "candidates"


def candidate_content_sha256(trigger: str, advisory_text: str) -> str:
    """A6 content hash: ``sha256(trigger + "\\n" + advisory_text)``.

    The ``"\\n"`` separator is deliberate (the consensus text says
    ``sha256(trigger + advisory_text)``): both fields exclude newlines
    by bounded vocabulary, so the separator makes the concatenation
    boundary unambiguous — no (trigger, text) pair can collide with a
    shifted split of another pair.
    """
    raw = f"{trigger}\n{advisory_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validate_candidate_fields(
    trigger: Any,
    advisory_text: Any,
    scope_tags: Any,
) -> Optional[str]:
    """Bounded-vocabulary validation (A5). Returns a reason code or None.

    Closed reason codes (metadata-only; safe for audit fields and
    breadcrumbs): trigger_invalid, text_type, text_empty, text_too_long,
    text_backtick, text_newline, text_control_char, tags_type,
    tags_too_many, tag_invalid.
    """
    if not isinstance(trigger, str) or not _CANDIDATE_TOKEN_RE.match(trigger):
        return "trigger_invalid"
    if not isinstance(advisory_text, str):
        return "text_type"
    if not advisory_text.strip():
        return "text_empty"
    if len(advisory_text) > CANDIDATE_TEXT_MAX_CHARS:
        return "text_too_long"
    if "`" in advisory_text:
        return "text_backtick"
    if "\n" in advisory_text or "\r" in advisory_text:
        return "text_newline"
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in advisory_text):
        return "text_control_char"
    if not isinstance(scope_tags, (list, tuple)):
        return "tags_type"
    if len(scope_tags) > _MAX_CANDIDATE_TAGS:
        return "tags_too_many"
    for tag in scope_tags:
        if not isinstance(tag, str) or not _CANDIDATE_TOKEN_RE.match(tag):
            return "tag_invalid"
    return None


def _load_injection_scanner() -> Any:
    """Load the sibling ``scan-injection.py`` corpus module. RAISES on
    any failure — the caller's fail-CLOSED posture depends on it (A4).

    The module is registered in ``sys.modules`` BEFORE exec: on Python
    3.9, dataclass processing under ``from __future__ import
    annotations`` resolves ``cls.__module__`` through ``sys.modules``
    and hard-fails for anonymous spec-loaded modules (the advisory
    ``_scan_lesson_for_injection`` path above silently swallowed this
    same failure — here it would wrongly quarantine every candidate as
    ``scanner_unavailable``).
    """
    import importlib.util as _iutil
    module_name = "scan_injection_for_candidates"
    cached = sys.modules.get(module_name)
    if cached is not None and hasattr(cached, "scan_text"):
        return cached
    spec = _iutil.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parent / "scan-injection.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError("scan-injection.py not loadable")
    mod = _iutil.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    if not hasattr(mod, "scan_text"):
        sys.modules.pop(module_name, None)
        raise ImportError("scan-injection.py exposes no scan_text")
    return mod


def _scan_candidate_fail_closed(text_blob: str) -> Tuple[bool, str]:
    """Fail-CLOSED injection scan for the promotion boundary (A4).

    Contrast with ``_scan_lesson_for_injection`` above, which is
    ADVISORY fail-open and acceptable only for the legacy raw-write /
    telemetry side. Here — per the C4/``_e3`` precedent — content the
    scanner cannot examine is refused, not waved through:

    - scanner import/exec failure → ``(False, "scanner_unavailable")``
    - any corpus match            → ``(False, "injection_pattern")``
    - clean                       → ``(True, "clean")``
    """
    try:
        mod = _load_injection_scanner()
        result = mod.scan_text(text_blob)
        matched = bool(getattr(result, "matched", False)) or bool(
            getattr(result, "matches", None)
        )
    except Exception:
        return (False, "scanner_unavailable")
    if matched:
        return (False, "injection_pattern")
    return (True, "clean")


def _write_candidate(record: Dict[str, Any], base_dir: Optional[str] = None) -> Path:
    """Persist a candidate record under the shared lessons lock."""
    d = _candidates_dir(base_dir)
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(d), 0o700)
    except OSError:
        pass
    path = d / f"{record['lesson_id']}.json"
    payload = json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    lock_dir = _lessons_dir(base_dir)
    if _FILELOCK_AVAILABLE:
        try:
            with FileLock(str(lock_dir / ".lessons.lock"), timeout=2.5):
                path.write_text(payload, encoding="utf-8")
        except FileLockTimeout:
            path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(payload, encoding="utf-8")
    return path


def _load_candidate(
    lesson_id: str, base_dir: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Load one candidate record; None on missing/unparseable."""
    path = _candidates_dir(base_dir) / f"{lesson_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def list_candidates(
    base_dir: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List candidate records (all states — /lesson-review's view).

    QUARANTINED candidates are deliberately VISIBLE here (A4: terminal,
    never rendered anywhere, but reviewable) while remaining invisible
    to every render path. Bounded at ``_MAX_SCAN`` files; deterministic
    filename order.
    """
    d = _candidates_dir(base_dir)
    if not d.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    count = 0
    for f in sorted(d.iterdir()):
        if count >= _MAX_SCAN:
            break
        if f.suffix != ".json":
            continue
        count += 1
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if status is not None and data.get("status") != status:
            continue
        out.append(data)
    return out


def add_candidate(
    trigger: str,
    advisory_text: str,
    scope_tags: List[str],
    now_fn: Optional[Callable[[], Any]] = None,
    base_dir: Optional[str] = None,
    session_id: str = "",
    project: str = "",
) -> Tuple[str, str]:
    """Write a distiller-proposed lesson CANDIDATE (PLAN-154 item 2/3).

    Wave-0 interface contract. Returns ``(lesson_id, status)`` with
    status ∈ {PENDING, QUARANTINED}. Nothing written here is ever
    rendered without a subsequent hash-pinned approval event (A6) —
    the /lesson-review human gate filters for usefulness; THIS boundary
    filters for injection (A4, fail-CLOSED):

    - bounded-vocabulary violation → ``ValueError`` (reject at add);
    - scanner unavailable OR scan hit → QUARANTINED (terminal);
    - clean → PENDING (30d TTL, constraint 5).
    """
    violation = _validate_candidate_fields(trigger, advisory_text, scope_tags)
    if violation:
        raise ValueError(
            f"add_candidate: bounded-vocabulary violation ({violation})"
        )
    # Belt: a candidate whose text would be altered by secret-redaction
    # carries secret-shaped content — reject loudly rather than let the
    # hash pin diverge from what redaction would store.
    try:
        redacted = redact_secrets(advisory_text)
    except Exception:
        redacted = advisory_text
    if redacted != advisory_text:
        raise ValueError(
            "add_candidate: advisory_text contains redactable secret content"
        )

    now = _now_utc(now_fn)
    created_at = now.isoformat()
    lesson_id = hashlib.sha256(
        f"candidate:{trigger}\n{advisory_text}\n{created_at}".encode("utf-8")
    ).hexdigest()[:16]

    scan_blob = "\n".join([trigger, advisory_text, " ".join(scope_tags)])
    ok, scan_outcome = _scan_candidate_fail_closed(scan_blob)
    status = STATUS_PENDING if ok else STATUS_QUARANTINED
    content_sha = candidate_content_sha256(trigger, advisory_text)

    record: Dict[str, Any] = {
        "schema": "candidate_v1",
        "lesson_id": lesson_id,
        "created_at": created_at,
        "trigger": trigger,
        "advisory_text": advisory_text,
        "scope_tags": list(scope_tags),
        "status": status,
        "status_reason": scan_outcome,
        "status_changed_at": created_at,
        "content_sha256": content_sha,
    }
    _write_candidate(record, base_dir)

    _emit_lesson_event(_ACTION_CANDIDATE_WRITTEN, {
        "lesson_id": lesson_id,
        "trigger": trigger,
        "status": status,
        "scan_outcome": scan_outcome,
        "content_sha256": content_sha,
        "scope_tags": list(scope_tags),
        "session_id": session_id,
        "project": project,
    })
    return (lesson_id, status)


def _chain_created_at(
    lesson_id: str,
    record: Dict[str, Any],
) -> Tuple[Optional[datetime], str, Optional[Dict[str, Any]]]:
    """Authoritative created_at for TTL math (A9).

    The chain's ``lesson_candidate_written`` event — not the mutable
    ``$HOME`` file — is the authority when present (an attacker who can
    edit the store cannot extend a pending's life). Returns
    ``(created_at, source, chain_event)`` with source ∈
    {"chain", "file", "none"}.
    """
    events = _chain_latest_events({_ACTION_CANDIDATE_WRITTEN}, {lesson_id})
    ev = events.get((lesson_id, _ACTION_CANDIDATE_WRITTEN))
    if ev is not None:
        dt = _parse_iso_ts(ev.get("ts"))
        if dt is not None:
            return (dt, "chain", ev)
    dt = _parse_iso_ts(record.get("created_at"))
    if dt is not None:
        return (dt, "file", ev)
    return (None, "none", ev)


def _quarantine_candidate(
    record: Dict[str, Any],
    reason: str,
    now: datetime,
    base_dir: Optional[str],
    session_id: str,
    project: str,
) -> None:
    """Transition a candidate to terminal QUARANTINED + audit event."""
    prior = str(record.get("status") or "")
    record["status"] = STATUS_QUARANTINED
    record["status_reason"] = reason
    record["status_changed_at"] = now.isoformat()
    _write_candidate(record, base_dir)
    _emit_lesson_event(_ACTION_QUARANTINED, {
        "lesson_id": str(record.get("lesson_id") or ""),
        "reason": reason,
        "prior_status": prior,
        "session_id": session_id,
        "project": project,
    })


def approve_candidate(
    lesson_id: str,
    base_dir: Optional[str] = None,
    now_fn: Optional[Callable[[], Any]] = None,
    session_id: str = "",
    project: str = "",
) -> Tuple[str, str]:
    """Approve a PENDING candidate (the /lesson-review human-gate backend).

    Returns ``(status_after, reason)``. Approval is a PROMOTION BOUNDARY
    and therefore fail-CLOSED (A4), with INFRASTRUCTURE failures refused
    retryably (no state change) and INPUT failures quarantined terminally:

    - not found                      → ("NOT_FOUND", "not_found")
    - QUARANTINED / EXPIRED          → (status, "terminal_state")
    - already APPROVED               → ("APPROVED", "already_approved")
    - no chain write event (A9)      → ("PENDING", "chain_event_missing")
    - scanner unavailable            → ("PENDING", "scanner_unavailable")
    - file hash ≠ chain write event  → ("QUARANTINED", "content_hash_mismatch")
    - bounded-vocab violation        → ("QUARANTINED", "vocab_violation")
    - re-scan hit                    → ("QUARANTINED", "injection_pattern")
    - TTL exceeded (chain clock)     → ("EXPIRED", "ttl_expired")
    - success → ("APPROVED", "approved") + hash-pinned ``lesson_approved``
      chain event carrying ``content_sha256`` (A6 integrity anchor).
    """
    record = _load_candidate(lesson_id, base_dir)
    if record is None:
        return ("NOT_FOUND", "not_found")
    status = str(record.get("status") or "")
    if status in TERMINAL_STATUSES:
        return (status, "terminal_state")
    if status == STATUS_APPROVED:
        return (STATUS_APPROVED, "already_approved")
    if status != STATUS_PENDING:
        return (status or "UNKNOWN", "unknown_status")

    now = _now_utc(now_fn)
    trigger = record.get("trigger")
    advisory_text = record.get("advisory_text")
    scope_tags = record.get("scope_tags") or []

    # INPUT check 1 — stored fields still inside the bounded vocabulary.
    violation = _validate_candidate_fields(trigger, advisory_text, scope_tags)
    if violation:
        _quarantine_candidate(
            record, "vocab_violation", now, base_dir, session_id, project,
        )
        return (STATUS_QUARANTINED, "vocab_violation")

    # A9 — created_at is verified against the chain's candidate-write
    # event, NOT the $HOME file. No chain event → refuse (fail-CLOSED,
    # retryable: re-add the candidate to mint a fresh chain anchor).
    created_at, source, chain_ev = _chain_created_at(lesson_id, record)
    if source != "chain" or created_at is None or chain_ev is None:
        return (STATUS_PENDING, "chain_event_missing")

    # INPUT check 2 — file content unchanged since the chain-write pin.
    recomputed = candidate_content_sha256(str(trigger), str(advisory_text))
    chain_sha = str(chain_ev.get("content_sha256") or "")
    if not chain_sha or chain_sha != recomputed:
        _quarantine_candidate(
            record, "content_hash_mismatch", now, base_dir, session_id, project,
        )
        return (STATUS_QUARANTINED, "content_hash_mismatch")

    # A16 — an expired pending cannot be approved (strict > TTL).
    age_s = (now - created_at).total_seconds()
    if age_s > CANDIDATE_TTL_DAYS * 86400.0:
        record["status"] = STATUS_EXPIRED
        record["status_reason"] = "ttl_expired"
        record["status_changed_at"] = now.isoformat()
        _write_candidate(record, base_dir)
        _emit_lesson_event(_ACTION_EXPIRED, {
            "lesson_id": lesson_id,
            "age_days": int(age_s // 86400),
            "created_at_source": source,
            "session_id": session_id,
            "project": project,
        })
        return (STATUS_EXPIRED, "ttl_expired")

    # Promotion-boundary re-scan: INFRA failure refuses (retryable),
    # INPUT hit quarantines (terminal).
    scan_blob = "\n".join(
        [str(trigger), str(advisory_text), " ".join(scope_tags)]
    )
    ok, scan_outcome = _scan_candidate_fail_closed(scan_blob)
    if not ok:
        if scan_outcome == "scanner_unavailable":
            return (STATUS_PENDING, "scanner_unavailable")
        _quarantine_candidate(
            record, scan_outcome, now, base_dir, session_id, project,
        )
        return (STATUS_QUARANTINED, scan_outcome)

    record["status"] = STATUS_APPROVED
    record["status_reason"] = "approved"
    record["status_changed_at"] = now.isoformat()
    record["approved_at"] = now.isoformat()
    _write_candidate(record, base_dir)
    _emit_lesson_event(_ACTION_APPROVED, {
        "lesson_id": lesson_id,
        "trigger": str(trigger),
        "content_sha256": recomputed,
        "scope_tags": list(scope_tags),
        "session_id": session_id,
        "project": project,
    })
    return (STATUS_APPROVED, "approved")


def expire_pending_candidates(
    base_dir: Optional[str] = None,
    now_fn: Optional[Callable[[], Any]] = None,
    session_id: str = "",
    project: str = "",
) -> List[str]:
    """TTL sweep: PENDING candidates older than 30d → terminal EXPIRED.

    Deterministic under an injected ``now_fn`` (A9): strict ``age > TTL``
    boundary, chain-authoritative created_at (file value only as
    fallback when no chain event exists — such candidates can never be
    approved anyway, see ``approve_candidate``). Idempotent: a second
    run under the same clock returns ``[]``. Emits one
    ``lesson_expired`` audit event per transition. Never any default
    disposition toward activation.
    """
    now = _now_utc(now_fn)
    pendings = [
        r for r in list_candidates(base_dir) if r.get("status") == STATUS_PENDING
    ]
    if not pendings:
        return []
    ids = {str(r.get("lesson_id") or "") for r in pendings}
    chain = _chain_latest_events({_ACTION_CANDIDATE_WRITTEN}, ids)

    expired: List[str] = []
    for record in pendings:
        lid = str(record.get("lesson_id") or "")
        ev = chain.get((lid, _ACTION_CANDIDATE_WRITTEN))
        created_at = _parse_iso_ts(ev.get("ts")) if ev else None
        source = "chain"
        if created_at is None:
            created_at = _parse_iso_ts(record.get("created_at"))
            source = "file"
        if created_at is None:
            # Unparseable everywhere: cannot compute age. Skip — the
            # candidate stays PENDING (inert; approval separately
            # refuses on chain_event_missing).
            continue
        age_s = (now - created_at).total_seconds()
        if age_s <= CANDIDATE_TTL_DAYS * 86400.0:
            continue
        record["status"] = STATUS_EXPIRED
        record["status_reason"] = "ttl_expired"
        record["status_changed_at"] = now.isoformat()
        _write_candidate(record, base_dir)
        _emit_lesson_event(_ACTION_EXPIRED, {
            "lesson_id": lid,
            "age_days": int(age_s // 86400),
            "created_at_source": source,
            "session_id": session_id,
            "project": project,
        })
        expired.append(lid)
    return expired


def pending_expiry_warning_count(
    base_dir: Optional[str] = None,
    now_fn: Optional[Callable[[], Any]] = None,
) -> int:
    """COUNT of PENDING candidates expiring within the 7d warning window.

    A9: this is COUNT-ONLY data — "N pendings expire in <7d". ZERO
    candidate text travels through this function; no pre-approval text
    can reach boot through the warning side door. Callers should run
    ``expire_pending_candidates`` first so overdue-but-unswept pendings
    don't inflate the count.
    """
    now = _now_utc(now_fn)
    pendings = [
        r for r in list_candidates(base_dir) if r.get("status") == STATUS_PENDING
    ]
    if not pendings:
        return 0
    ids = {str(r.get("lesson_id") or "") for r in pendings}
    chain = _chain_latest_events({_ACTION_CANDIDATE_WRITTEN}, ids)

    ttl_s = CANDIDATE_TTL_DAYS * 86400.0
    warn_s = CANDIDATE_WARN_DAYS * 86400.0
    count = 0
    for record in pendings:
        lid = str(record.get("lesson_id") or "")
        ev = chain.get((lid, _ACTION_CANDIDATE_WRITTEN))
        created_at = _parse_iso_ts(ev.get("ts")) if ev else None
        if created_at is None:
            created_at = _parse_iso_ts(record.get("created_at"))
        if created_at is None:
            continue
        age_s = (now - created_at).total_seconds()
        if age_s <= ttl_s and (ttl_s - age_s) <= warn_s:
            count += 1
    return count


def count_pending_expiring(
    project_dir: str,
    now_fn: Optional[Callable[[], Any]] = None,
    base_dir: Optional[str] = None,
) -> int:
    """Sweep-then-count boot warning input (PLAN-154 item 4 / A9 / A16).

    The exact API the ``/ceo-boot`` renderer consumes
    (``_lessons_pending_expiry_count`` → ``lessons.count_pending_expiring
    (project_dir, now_fn=None)``): runs the terminal TTL sweep
    (``expire_pending_candidates`` — wiring the item-4 documented
    sweep-then-warn ordering into the boot path) and then returns the
    COUNT-ONLY 7d warning number (``pending_expiry_warning_count``). ZERO
    candidate text travels through this function.

    ``project_dir`` resolves the store exactly like
    ``get_boot_lessons_verified`` (``base_dir`` arg > ``CEO_LESSONS_DIR``
    env > ``$HOME/.claude/projects/<slug>/lessons``). The sweep is
    best-effort (an infrastructure failure inside it degrades to
    count-without-sweep — boot must never break); the count itself
    propagates exceptions to the caller, which is fail-open → 0 in the
    renderer.
    """
    if base_dir is None and not os.environ.get("CEO_LESSONS_DIR"):
        slug = (_rp.project_slug(str(project_dir)) if project_dir
                else "default")  # PLAN-182 W3 (S321): slug via resolvedor unico
        home = os.environ.get("HOME") or str(Path.home())
        base_dir = str(
            Path(home) / ".claude" / "projects" / slug / "lessons"
        )
    try:
        expire_pending_candidates(base_dir=base_dir, now_fn=now_fn)
    except Exception:  # noqa: BLE001 — sweep is best-effort at boot
        pass
    return pending_expiry_warning_count(base_dir=base_dir, now_fn=now_fn)
